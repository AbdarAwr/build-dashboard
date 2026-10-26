"""Playwright tests for the dashboard template (both presets) + login + /logs/ redirect.

    python3 -m pytest ~/.claude/skills/build-dashboard/tests/test_template.py -q

Runs against stub_server.py + fixture.py (synthetic rows). The browser clock is pinned to FIXTURE_NOW and the browser
time zone is America/Los_Angeles on purpose: every date must be computed in Asia/Bangkok whatever the viewer's zone.
Expected numbers are recomputed here from the fixture with the rules the page documents — never hard-coded.

For a project: copy tests/ next to the project's web/ (the stub finds ../web), pass the project's endpoints with
serve_in_thread(data={path: (rows, columns)}), rewrite the fixture in the project's real column shape, delete the
section of the preset you removed, and keep the rules below in sync with the project's CONFIG.
"""
import csv
import io
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fixture import BKK, CHAT_COLUMNS, FIXTURE_NOW, ORDER_COLUMNS, QUESTIONS, chat_rows, order_rows  # noqa: E402
from stub_server import COOKIE, PASSWORD, serve_in_thread  # noqa: E402

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
QUOTA, TARGET = 2000, 500000
TODAY = FIXTURE_NOW.date()
CHATS, ORDERS = chat_rows(), order_rows()


def bkk_day(ts):
    d = datetime.fromisoformat(ts)
    return (d.replace(tzinfo=BKK) if d.tzinfo is None else d.astimezone(BKK)).date()   # no zone = Bangkok (page rule)


def classify_chat(r):
    sd = json.loads(r["sources_data"] or "[]")
    labels = [x.get("label") or "" for x in sd] + [s for s in r["sources"].split("; ") if s]
    gm = next((x[5:] for x in labels if x.startswith("GATE_")), "")
    sales = gm == "CAPPED" or "SALES_CARD" in labels
    empty = "EMPTY_LLM_RESPONSE" in labels
    n_img = max(len(json.loads(r["images_data"] or "[]")), int(r["images"] or 0), 1 if "](" in r["answer"] and "![" in r["answer"] else 0)
    real_src = [x for x in labels if x and not re.match(r"^(GATE_|SALES_CARD|EMPTY_LLM_RESPONSE)", x)]
    group = "gate" if gm and gm != "CAPPED" else "sales" if sales else "img" if n_img else "src" if real_src and not empty else "other"
    return dict(r, day=bkk_day(r["timestamp"]), gate=gm, counted=not gm, group=group)


REAL = [classify_chat(r) for r in CHATS if UUID.match(r["session"])]
ORD = [dict(r, day=bkk_day(r["timestamp"]), amount=int(r["amount"]), counted=r["status"] != "cancelled",
            paid_day=bkk_day(r["paid_at"]) if r["paid_at"] else None) for r in ORDERS]
KW_OF = {q: kws for q, kws in QUESTIONS}


def bounds(key):
    return {"today": (TODAY, TODAY), "7": (TODAY - timedelta(days=6), TODAY), "30": (TODAY - timedelta(days=29), TODAY),
            "month": (TODAY.replace(day=1), TODAY), "year": (TODAY.replace(month=1, day=1), TODAY), "all": (None, None)}[key]


def in_range(rows, key):
    f, t = bounds(key)
    return [r for r in rows if (f is None or r["day"] >= f) and (t is None or r["day"] <= t)]


def this_month(rows):
    return [r for r in rows if r["counted"] and (r["day"].year, r["day"].month) == (TODAY.year, TODAY.month)]


def num(text):
    return int(re.sub(r"[^\d]", "", text))


# ---------------------------------------------------------------- browser plumbing
@pytest.fixture(scope="module")
def server():
    srv = serve_in_thread(data={"/api/logs.csv": (CHATS, CHAT_COLUMNS), "/api/orders.csv": (ORDERS, ORDER_COLUMNS)})
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        yield b
        b.close()


def new_page(browser, server, path="/dashboard/", width=1440, height=900, scheme="light", login=True, errors=None, wait=None):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme,
                              timezone_id="America/Los_Angeles", locale="th-TH", accept_downloads=True)
    if login:
        ctx.add_cookies([{"name": COOKIE, "value": "ok", "url": server}])
    page = ctx.new_page()
    page.clock.set_fixed_time(FIXTURE_NOW)
    if errors is not None:
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "404" not in m.text else None)
    page.goto(server + path)
    if wait:
        page.wait_for_selector(wait)
    elif login and path.startswith("/dashboard"):
        page.wait_for_selector(".sess" if "#logs" in path else "#logtable tbody tr")
    return page


GENERIC = "/dashboard/?preset=generic"


# ================================================================ preset: chatbot
@pytest.mark.parametrize("key", ["all", "today", "7", "30", "month", "year"])
def test_chat_kpis_match_fixture(browser, server, key):
    page = new_page(browser, server)
    page.click(f'.preset[data-range="{key}"]')
    rows = in_range(REAL, key)
    counted = [r for r in rows if r["counted"]]
    assert num(page.inner_text("#kpi-questions")) == len(counted)
    assert num(page.inner_text("#kpi-sessions")) == len({r["session"] for r in counted})
    assert num(page.inner_text("#kpi-quota")) == len(this_month(REAL))   # quota ignores the selected range
    assert num(page.inner_text("#logcount")) == len(rows)                # the table lists every real row in range
    page.context.close()


def test_chat_test_sessions_never_counted(browser, server):
    page = new_page(browser, server)
    page.fill("#q", "ค่าบริการ test")
    expect(page.locator("#logcount")).to_have_text("(0 รายการ)")
    page.context.close()


def test_chat_quality_groups_sum_to_100(browser, server):
    page = new_page(browser, server)
    for g in ("src", "img", "sales", "gate", "other"):
        n = sum(1 for r in REAL if r["group"] == g)
        if n or g != "other":
            assert num(page.inner_text(f'#qlegend li[data-g="{g}"] .ln')) == n, g
    pcts = [num(x) for x in page.locator("#qlegend li[data-g] b").all_inner_texts()]
    assert sum(pcts) == 100
    page.context.close()


def test_chat_capped_is_handoff_but_not_counted(browser, server):
    capped = [r for r in REAL if r["gate"] == "CAPPED"]
    assert capped, "fixture must contain CAPPED rows"
    page = new_page(browser, server)
    page.select_option("#ltype", "sales")
    assert num(page.inner_text("#logcount")) == sum(1 for r in REAL if r["group"] == "sales")
    page.fill("#q", "เกินโควตาต่อคน")
    assert num(page.inner_text("#logcount")) == len(capped)
    page.context.close()


def test_chat_keywords_match_whitelist(browser, server):
    expected = {}
    for r in REAL:
        if r["counted"]:
            for k in KW_OF.get(r["question"], set()):
                expected[k] = expected.get(k, 0) + 1
    page = new_page(browser, server)
    card = page.locator('.card[data-rank="1"]')
    labels = card.locator(".rlab").all_inner_texts()
    counts = [num(x) for x in card.locator(".rnum").all_inner_texts()]
    assert len(labels) == min(10, len(expected))
    for label, n in zip(labels, counts):
        assert expected.get(label) == n, (label, n, expected.get(label))
    page.context.close()


def test_chat_pagination_and_search(browser, server):
    page = new_page(browser, server)
    total = len(REAL)
    assert page.locator("#logtable tbody tr").count() == 10
    expect(page.locator("#pinfo")).to_have_text(f"แสดง 1–10 จาก {total} รายการ")
    page.locator('#pager button[aria-label="หน้าถัดไป"]').click()
    expect(page.locator("#pinfo")).to_have_text(f"แสดง 11–20 จาก {total} รายการ")
    email = next(r["email"] for r in REAL if r["email"])
    page.fill("#q", email)
    assert num(page.inner_text("#logcount")) == sum(1 for r in REAL if r["email"] == email)
    page.context.close()


def test_chat_detail_view(browser, server):
    page = new_page(browser, server, "/dashboard/#logs")
    assert page.locator(".sess").count() == len({r["session"] for r in REAL})
    expect(page.locator(".side .nav")).to_have_count(2)
    r = next(r for r in REAL if r["group"] == "img" and r["images_data"] != "[]")
    page.goto(f"{server}/dashboard/#logs/{r['session']}")
    expect(page.locator("#sidcode")).to_have_text(r["session"])
    assert page.locator(".turn").count() == sum(1 for x in REAL if x["session"] == r["session"])
    page.context.close()


def test_chat_images_are_same_origin(browser, server):
    """images_data on the current domain and markdown on an old domain both load from /crops/ of this host."""
    page = new_page(browser, server, "/dashboard/#logs")
    for r in [x for x in REAL if x["group"] == "img"][:6]:
        page.goto(f"{server}/dashboard/#logs/{r['session']}")
        page.wait_for_selector(".turn")
        srcs = page.locator(".ev img").evaluate_all("els => els.map(e => e.getAttribute('src'))")
        assert srcs and all(s.startswith("/crops/") for s in srcs), srcs
    page.context.close()


def test_chat_go_button_opens_conversation(browser, server):
    page = new_page(browser, server)
    page.locator("#logtable tbody tr").first.locator(".gobtn").click()
    page.wait_for_selector(".turn")
    newest = max(REAL, key=lambda r: r["timestamp"])
    expect(page.locator("#sidcode")).to_have_text(newest["session"])
    page.context.close()


def test_chat_csv_export_matches_range_and_blocks_formulas(browser, server):
    page = new_page(browser, server)
    page.click('.preset[data-range="all"]')
    with page.expect_download() as d:
        page.click("#csvbtn")
    text = Path(d.value.path()).read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == CHAT_COLUMNS
    assert len(rows) - 1 == len(REAL)
    qi = CHAT_COLUMNS.index("question")
    assert not any(r[qi].startswith("=") for r in rows[1:]), "formula cell exported unescaped"
    assert any(r[qi].startswith("'=HYPERLINK") for r in rows[1:])
    page.click('.preset[data-range="30"]')
    with page.expect_download() as d:
        page.click("#csvbtn")
    assert len(list(csv.reader(io.StringIO(Path(d.value.path()).read_text(encoding="utf-8-sig"))))) - 1 == len(in_range(REAL, "30"))
    page.context.close()


# ================================================================ preset: generic (orders example)
@pytest.mark.parametrize("key", ["all", "today", "7", "30", "month", "year"])
def test_generic_kpis_match_fixture(browser, server, key):
    page = new_page(browser, server, GENERIC)
    page.click(f'.preset[data-range="{key}"]')
    rows = in_range(ORD, key)
    counted = [r for r in rows if r["counted"]]
    assert num(page.inner_text("#kpi-sales")) == sum(r["amount"] for r in counted)
    assert num(page.inner_text("#kpi-orders")) == len(counted)
    assert num(page.inner_text("#kpi-target")) == sum(r["amount"] for r in this_month(ORD))
    assert num(page.inner_text("#logcount")) == len(rows)
    page.context.close()


def test_generic_goal_meter_and_breakdown(browser, server):
    page = new_page(browser, server, GENERIC)
    month_sales = sum(r["amount"] for r in this_month(ORD))
    tile = page.locator(".tile").first
    if month_sales >= TARGET:
        expect(tile.locator(".status.ok")).to_have_text("ถึงเป้าแล้ว")
    else:
        expect(tile.locator(".status")).to_have_count(0)
    for g in ("paid", "pending", "cancelled"):
        assert num(page.inner_text(f'#qlegend li[data-g="{g}"] .ln')) == sum(1 for r in ORD if r["status"] == g), g
    assert sum(num(x) for x in page.locator("#qlegend li[data-g] b").all_inner_texts()) == 100
    page.context.close()


def test_generic_ranking_by_amount(browser, server):
    totals = {}
    for r in ORD:
        if r["counted"]:
            totals[r["product"]] = totals.get(r["product"], 0) + r["amount"]
    page = new_page(browser, server, GENERIC)
    card = page.locator('.card[data-rank="0"]')
    labels = card.locator(".rlab").all_inner_texts()
    counts = [num(x) for x in card.locator(".rnum").all_inner_texts()]
    assert labels == [k for k, _ in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))][:10]
    assert counts == sorted(totals.values(), reverse=True)[:10]
    page.context.close()


def test_generic_detail_is_record_view(browser, server):
    """non-chat detail: group = customer, each order rendered with recordHtml (no chat bubbles)"""
    page = new_page(browser, server, GENERIC + "#customers", wait=".sess")
    expect(page.locator(".side .nav")).to_have_count(2)
    assert page.locator(".sess").count() == len({r["customer"] for r in ORD})
    cust = max({r["customer"] for r in ORD}, key=lambda c: sum(1 for r in ORD if r["customer"] == c))
    page.goto(f"{server}{GENERIC}#customers/{cust}")
    expect(page.locator("#sidcode")).to_have_text(cust)
    expect(page.locator(".rec")).to_have_count(sum(1 for r in ORD if r["customer"] == cust))
    assert page.locator(".turn, .q").count() == 0
    first = next(r for r in ORD if r["customer"] == cust)
    expect(page.locator(".rec").first.locator(".rec-fields")).to_contain_text("สินค้า")
    expect(page.locator(f'.rec-title:text-is("{first["order_id"]}")')).to_have_count(1)
    page.context.close()


def test_generic_detail_can_be_switched_off(browser, server):
    page = new_page(browser, server, GENERIC + "&const.SHOW_DETAIL=0#customers", wait="#logtable tbody tr")
    expect(page.locator(".side .nav")).to_have_count(1)
    expect(page.locator("#view-detail")).to_be_hidden()
    expect(page.locator("#logtable th")).to_have_count(5)   # เวลา + 4 config columns, no go column
    page.context.close()


def test_generic_trend_metric_toggle(browser, server):
    """trend.metrics: the chart switches between sum (ยอดขาย) and count (จำนวนคำสั่งซื้อ) of counted rows"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="30"]')
    rows = [r for r in in_range(ORD, "30") if r["counted"]]
    page.locator("#tview summary").click()
    tv = lambda: sum(num(x) for x in page.locator("#tview tbody td.num").all_inner_texts())
    expect(page.locator('[data-metric="amount"]')).to_have_attribute("aria-pressed", "true")
    assert tv() == sum(r["amount"] for r in rows)
    page.click('[data-metric="orders"]')
    expect(page.locator('[data-metric="orders"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#chartcap")).to_contain_text("คำสั่งซื้อ")
    assert tv() == len(rows)
    page.click('.preset[data-range="7"]')   # the chosen metric survives a range change
    expect(page.locator('[data-metric="orders"]')).to_have_attribute("aria-pressed", "true")
    page.context.close()


@pytest.mark.parametrize("layout,expect_order", [
    ("kpis,table,trend", ["tiles", "table", "chart"]),
    ("kpis,breakdown,table", ["tiles", "breakdown", "table"]),
    ("trend,kpis,rankings,table", ["chart", "tiles", "rankings", "table"]),
])
def test_layout_orders_and_omits_sections(browser, server, layout, expect_order):
    page = new_page(browser, server, GENERIC + "&layout=" + layout)
    order = page.evaluate("""() => [...document.querySelectorAll('#app > *')].map(el =>
        el.classList.contains('tiles') ? 'tiles' : el.querySelector('#logtable') ? 'table' : el.querySelector('#chart') ? 'chart'
        : el.querySelector('#qstack') ? 'breakdown' : el.querySelector('[data-rank]') ? 'rankings' : '?')""")
    assert order == expect_order, order
    if "trend" in layout and "breakdown" not in layout:
        expect(page.locator(".row.trend #qstack")).to_have_count(1)   # breakdown rides beside the chart by default
    page.context.close()


def test_generic_csv_export(browser, server):
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="month"]')
    with page.expect_download() as d:
        page.click("#csvbtn")
    rows = list(csv.reader(io.StringIO(Path(d.value.path()).read_text(encoding="utf-8-sig"))))
    assert rows[0] == ORDER_COLUMNS
    assert len(rows) - 1 == len(in_range(ORD, "month"))
    assert d.value.suggested_filename.startswith("orders-")
    page.context.close()


def test_chat_no_quota_cap(browser, server):
    """QUOTA_MONTH = 0 → plain monthly count, no meter, no quota alert."""
    page = new_page(browser, server, "/dashboard/?const.QUOTA_MONTH=0")
    expect(page.locator(".tile").first.locator(".label")).to_contain_text("คำถามเดือนนี้")
    expect(page.locator(".qbar")).to_have_count(0)
    assert num(page.inner_text("#kpi-quota")) == len(this_month(REAL))
    page.click("#bellbtn")
    expect(page.locator(".nitem.warn, .nitem.crit")).to_have_count(0)
    page.context.close()


def test_chat_quota_alert_at_80_percent(browser, server):
    used = len(this_month(REAL))
    page = new_page(browser, server, f"/dashboard/?const.QUOTA_MONTH={used}")   # 100% → crit
    expect(page.locator(".tile").first.locator(".status.crit")).to_have_text("ครบโควตาแล้ว")
    page.click("#bellbtn")
    expect(page.locator(".nitem.crit")).to_have_count(1)
    page.context.close()


def test_generic_no_target(browser, server):
    page = new_page(browser, server, GENERIC + "&const.TARGET_MONTH=0")
    expect(page.locator(".qbar")).to_have_count(0)
    assert num(page.inner_text("#kpi-target")) == sum(r["amount"] for r in this_month(ORD))
    page.context.close()


def test_generic_metric_by_second_timestamp(browser, server):
    """trend.metrics[].at: 'ชำระแล้ว' buckets orders by paid_at (not order time) — rows filtered by that time"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="30"]')
    page.locator("#tview summary").click()
    page.click('[data-metric="paid"]')
    f, t = bounds("30")
    expected = sum(1 for r in ORD if r["paid_day"] and f <= r["paid_day"] <= t)
    assert sum(num(x) for x in page.locator("#tview tbody td.num").all_inner_texts()) == expected
    page.context.close()


def test_generic_all_time_ranking_ignores_range(browser, server):
    """rankings[].allTime: 'รอชำระตอนนี้' counts every pending order whatever range is selected"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="today"]')
    card = page.locator('.card[data-rank="3"]')
    expect(card.locator("h2")).to_contain_text("ไม่ขึ้นกับช่วงเวลา")
    pend = {}
    for r in ORD:
        if r["status"] == "pending":
            pend[r["customer"]] = pend.get(r["customer"], 0) + 1
    labels = card.locator(".rlab").all_inner_texts()
    counts = [num(x) for x in card.locator(".rnum").all_inner_texts()]
    assert sum(counts) == sum(sorted(pend.values(), reverse=True)[:10])
    for label, n in zip(labels, counts):
        assert pend[label] == n
    page.context.close()


def test_generic_ranking_agg_average(browser, server):
    """rankings[].agg: average order value per channel (counted rows), highest first"""
    page = new_page(browser, server, GENERIC)
    groups = {}
    for r in ORD:
        if r["counted"]:
            groups.setdefault(r["channel"], []).append(r["amount"])
    avg = {k: int(sum(v) / len(v) + 0.5) for k, v in groups.items() if len(v) >= 3}   # Math.round, min: 3
    card = page.locator('.card[data-rank="2"]')
    labels = card.locator(".rlab").all_inner_texts()
    assert labels == [k for k, _ in sorted(avg.items(), key=lambda kv: -kv[1])]
    assert [num(x) for x in card.locator(".rnum").all_inner_texts()] == [avg[k] for k in labels]
    page.context.close()


def test_ranking_row_opens_exact_filter(browser, server):
    """rankings[].go: a row filters the table to exactly the rows counted for it (no substring search), shown as a removable chip"""
    page = new_page(browser, server, GENERIC)
    row = page.locator('.card[data-rank="1"] .rrow').first
    label, n = row.locator(".rlab").inner_text(), num(row.locator(".rnum").inner_text())
    row.click()
    expect(page.locator("#q")).to_have_value("")
    expect(page.locator(".pickchip")).to_contain_text(label)
    assert num(page.inner_text("#logcount")) == n == sum(1 for r in ORD if r["channel"] == label and r["counted"])
    page.locator(".pickchip").click()                       # clear
    expect(page.locator(".pickchip")).to_have_count(0)
    assert num(page.inner_text("#logcount")) == len(ORD)
    page.context.close()


def test_all_time_ranking_go_switches_table_to_all(browser, server):
    """allTime + go: the table must show the same rows the card counted, whatever range was selected"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="today"]')
    row = page.locator('.card[data-rank="3"] .rrow').first
    label, n = row.locator(".rlab").inner_text(), num(row.locator(".rnum").inner_text())
    row.click()
    expect(page.locator('.preset[data-range="all"]')).to_have_class(re.compile(r"\bon\b"))
    assert num(page.inner_text("#logcount")) == n == sum(1 for r in ORD if r["customer"] == label and r["status"] == "pending")
    page.context.close()


def test_kpi_go_filter_all_time_via_override(browser, server):
    """kpi.go.filter + allTime: 'now' cards open exactly their rows"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="7"]')
    page.evaluate("""() => { CFG.kpis = ctx => [{ icon: 'clock', id: 'kp', label: 'รอชำระตอนนี้',
        value: ctx.all.filter(l => l.status === 'pending').length,
        go: { filter: l => l.status === 'pending', allTime: true, text: 'ดูที่รอชำระ' } }]; render(); }""")
    page.locator(".tile-go").click()
    pend = sum(1 for r in ORD if r["status"] == "pending")
    assert num(page.inner_text("#kp")) == pend
    assert num(page.inner_text("#logcount")) == pend
    expect(page.locator(".pickchip")).to_contain_text("ดูที่รอชำระ")
    page.context.close()


def test_agg_metric_shows_no_data_for_empty_buckets(browser, server):
    """a rate per bucket with no rows is 'no data', not 0"""
    page = new_page(browser, server, GENERIC)
    page.evaluate("""() => { CFG.trend.metrics.unshift({ key: 'r', label: 'อัตรา', unit: '%', agg: rs => 50 }); trendKey = 'r'; }""")
    page.click('.preset[data-range="today"]')                 # hourly buckets
    page.locator("#tview summary").click()
    cells = page.locator("#tview tbody td.num").all_inner_texts()
    assert len(cells) == 24 and "50" in cells and "–" in cells
    assert all(c in ("–", "50") for c in cells)   # ชั่วโมงที่ไม่มีแถว = "–" ไม่ใช่ 0
    page.context.close()


def test_kpi_go_opens_filtered_table(browser, server):
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="all"]')
    page.locator(".tile .tile-go").first.click()
    expect(page.locator("#ltype")).to_have_value("paid")
    assert num(page.inner_text("#logcount")) == sum(1 for r in ORD if r["status"] == "paid")
    page.context.close()


def test_detail_opens_record_outside_range(browser, server):
    """a bookmarked / bell-opened record must show even when the selected range excludes it"""
    today_customers = {r["customer"] for r in ORD if r["day"] == TODAY}
    old = min((r for r in ORD if r["customer"] not in today_customers), key=lambda r: r["timestamp"])
    page = new_page(browser, server, GENERIC + f"#customers/{old['customer']}", wait=".rec")
    page.click('.preset[data-range="today"]')
    expect(page.locator(".rec").first).to_be_visible()
    expect(page.locator("#thread")).to_contain_text("นอกช่วงที่เลือก")
    page.context.close()


def test_engine_options_via_config_override(browser, server):
    """table.sort, tile status badge, ctx.now and Latin-noun labels — exercised by overriding CFG in the page"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="all"]')
    res = page.evaluate("""() => {
        CFG.table.sort = (a, b) => a.ms - b.ms;                      // oldest first
        let now = 0;
        CFG.kpis = ctx => { now = ctx.now; return [{ icon: 'chat', id: 'kx', label: ctx.label('ticket'), value: 5,
                                                     status: { tone: 'crit', text: 'เกินเกณฑ์' } }]; };
        render();
        return { first: document.querySelector('#logtable tbody tr td').textContent, now,
                 label: document.querySelector('.tile .label').textContent,
                 badge: document.querySelector('.tile .status.crit') && document.querySelector('.tile .status.crit').textContent };
    }""")
    oldest = min(ORD, key=lambda r: r["timestamp"])
    assert res["now"] == int(FIXTURE_NOW.timestamp() * 1000)
    assert res["label"] == "ticket ทั้งหมด"
    assert "เกินเกณฑ์" in res["badge"]
    assert res["first"].strip().startswith(str(bkk_day(oldest["timestamp"]).day))
    page.context.close()


def test_breakdown_all_time_and_detail_meta_via_override(browser, server):
    """breakdown.allTime ignores the range · one record per group prints no duplicate count and no 'เริ่ม' · refreshSec"""
    page = new_page(browser, server, GENERIC)
    page.evaluate("() => { CFG.breakdown.allTime = true; CFG.refreshSec = 60; }")
    page.click('.preset[data-range="today"]')
    for g in ("paid", "pending", "cancelled"):
        assert num(page.inner_text(f'#qlegend li[data-g="{g}"] .ln')) == sum(1 for r in ORD if r["status"] == g), g
    expect(page.locator("#meta")).to_contain_text("ทุก 1 นาที")
    page.locator('#qlegend button[data-g="pending"]').click()          # legend → table must show all-time rows too
    assert num(page.inner_text("#logcount")) == sum(1 for r in ORD if r["status"] == "pending")
    page.evaluate("() => { CFG.detail.key = l => l.order; }")
    order = ORD[-1]["order_id"]
    page.goto(f"{server}{GENERIC}#customers/{order}")
    page.evaluate("() => { CFG.detail.key = l => l.order; renderView(); }")
    expect(page.locator(".th-meta")).not_to_contain_text("เริ่ม")
    assert page.inner_text("#meta").count("คำสั่งซื้อ") == 1
    page.context.close()


def test_table_open_button_focuses_that_record(browser, server):
    """detail grouped by customer: the row's open button must land on the clicked order, not just the group"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="all"]')
    tr = page.locator("#logtable tbody tr").nth(3)
    order = tr.locator("td.mono").inner_text().strip()
    tr.locator(".gobtn").click()
    page.wait_for_selector(".recwrap.focus")
    expect(page.locator(".recwrap.focus .rec-title")).to_have_text(order)
    page.context.close()


def test_detail_name_key_is_plain_text(browser, server):
    """copyKey: false — a group key that is a name (customer) is shown as a title, not as a copyable code"""
    page = new_page(browser, server, GENERIC + "#customers/ลูกค้า 01", wait=".rec")
    expect(page.locator(".thead .copybtn")).to_have_count(0)
    expect(page.locator("#sidcode")).to_have_text("ลูกค้า 01")
    assert page.evaluate("document.getElementById('sidcode').tagName") != "CODE"
    page.context.close()


def test_mobile_table_cells_keep_their_column_name(browser, server):
    page = new_page(browser, server, GENERIC, width=390)
    before = page.evaluate("""() => getComputedStyle(document.querySelector('#logtable tbody td.num'), '::before').content""")
    assert "ยอดเงิน" in before, before
    page.context.close()


def test_chart_reference_line(browser, server):
    page = new_page(browser, server, GENERIC)
    page.evaluate("() => { CFG.trend.metrics[1].ref = { value: 120, label: 'เป้า 120' }; trendKey = 'orders'; render(); }")
    expect(page.locator("#chart .refline")).to_have_count(1)
    expect(page.locator("#chart .refline")).to_contain_text("เป้า 120")
    page.context.close()


def test_no_auth_stub_and_profile_without_admin_wording(browser):
    """AUTH = 0 + stub without login gate: data loads with no cookie, profile chip is display settings, no 'ผู้ดูแลระบบ'"""
    srv = serve_in_thread(auth=False)
    try:
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="th-TH")
        page = ctx.new_page()
        page.clock.set_fixed_time(FIXTURE_NOW)
        page.goto(f"http://127.0.0.1:{srv.server_port}/dashboard/?const.AUTH=0")
        page.wait_for_selector("#logtable tbody tr")
        expect(page.locator("#profbtn")).not_to_contain_text("ผู้ดูแลระบบ")
        page.click("#profbtn")
        expect(page.locator("#profpop")).not_to_contain_text("ผู้ดูแล")
        expect(page.locator('#profpop [data-act="theme"]')).to_have_count(1)
        ctx.close()
    finally:
        srv.shutdown()


def test_round4_options_via_override(browser, server):
    """status with empty tone is neutral (not a green check) · notifs go.filter · detail.groupSort · agg metric min/peak"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="all"]')
    page.evaluate("""() => {
        CFG.kpis = ctx => [{ icon: 'chat', id: 'kx', label: 'x', value: 5, status: { tone: '', text: 'ข้อมูลน้อย' } }];
        CFG.notifs = n => [{ icon: 'clock', title: 'รอชำระ', go: { filter: l => l.status === 'pending', text: 'รอชำระทั้งหมด' } }];
        CFG.trend.metrics.unshift({ key: 'r', label: 'อัตรา', unit: '%', agg: rs => rs.length, min: 3, peak: 'min' });
        trendKey = 'r'; render(); updateBell();
    }""")
    expect(page.locator(".tile .status.neutral")).to_have_text("ข้อมูลน้อย")
    expect(page.locator(".tile .status.ok")).to_have_count(0)
    expect(page.locator("#chartcap")).to_contain_text("ต่ำสุด")
    page.locator("#tview summary").click()
    vals = [c for c in page.locator("#tview tbody td.num").all_inner_texts()]
    assert all(c == "–" or num(c) >= 3 for c in vals)          # buckets with < 3 rows are 'no data'
    page.click("#bellbtn")
    page.locator(".nitem").first.click()
    assert num(page.inner_text("#logcount")) == sum(1 for r in ORD if r["status"] == "pending")
    expect(page.locator(".pickchip")).to_contain_text("รอชำระทั้งหมด")
    page.goto(f"{server}{GENERIC}#customers")
    page.wait_for_selector(".sess")
    page.evaluate("() => { CFG.detail.groupSort = (a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0); renderView(); }")
    assert page.locator(".sess .sid").first.inner_text() == min({r["customer"] for r in ORD})
    page.context.close()


def test_stub_now_param_pins_the_clock(browser, server):
    """?now= in the stub pins Date for viewing synthetic data by hand (no Playwright clock)"""
    ctx = browser.new_context(locale="th-TH")
    ctx.add_cookies([{"name": COOKIE, "value": "ok", "url": server}])
    page = ctx.new_page()
    page.goto(server + GENERIC + "&now=2026-10-14T15:05:00%2B07:00")
    page.wait_for_selector("#logtable tbody tr")
    assert page.evaluate("Date.now()") == int(datetime.fromisoformat("2026-10-14T15:05:00+07:00").timestamp() * 1000)
    assert page.evaluate("new Date().getTime()") == page.evaluate("Date.now()")
    ctx.close()


def test_chart_max_caps_outliers_and_name_keys_in_list(browser, server):
    """metric.max: one outlier bucket must not flatten the chart (capped bar, real value in label/tooltip) ·
    copyKey: false also shows names (not ids) in the left list"""
    page = new_page(browser, server, GENERIC)
    page.click('.preset[data-range="all"]')
    monthly = {}
    for r in ORD:
        if r["counted"]:
            monthly[r["day"].strftime("%Y-%m")] = monthly.get(r["day"].strftime("%Y-%m"), 0) + r["amount"]
    cap = 100000
    assert sum(v > cap for v in monthly.values()) == 1                 # fixture: only October (big order) is an outlier
    page.evaluate(f"() => {{ CFG.trend.metrics[0].max = {cap}; trendKey = 'amount'; render(); }}")
    assert num(page.locator(".gridline span").last.inner_text()) <= 100   # axis tops out at the cap (100K)
    over = page.locator(".bar.over")
    expect(over).to_have_count(1)                                       # only October (456,000 big order) exceeds
    big = max(monthly.values())
    expect(over.locator(".top")).to_have_text(page.evaluate(f"fmtCompact({big})"))   # capped bar still shows its real value
    page.goto(f"{server}{GENERIC}#customers")
    page.wait_for_selector(".sess")
    assert page.evaluate("getComputedStyle(document.querySelector('.sess .sid')).fontFamily").find("monospace") == -1
    page.context.close()


# ================================================================ shared: auth / theme / layout
def test_login_flow_and_logs_redirect(browser, server):
    page = new_page(browser, server, "/dashboard/", login=False)
    expect(page).to_have_url(re.compile(r"/login/\?next="))
    page.fill("#u", "admin"); page.fill("#p", "wrong"); page.click("#submit")
    expect(page.locator("#err")).to_be_visible()
    page.fill("#u", "admin"); page.fill("#p", PASSWORD); page.click("#submit")
    page.wait_for_selector("#kpi-questions")
    expect(page.locator("#profname")).to_have_text("admin")
    page.goto(server + "/logs/")
    expect(page).to_have_url(re.compile(r"/dashboard/#logs$"))
    page.wait_for_selector(".sess")
    page.context.close()


def test_expired_session_shows_login_action(browser, server):
    page = new_page(browser, server)
    page.context.clear_cookies()
    page.click("#refreshbtn")
    expect(page.locator(".errcard h2")).to_contain_text("เซสชันหมดอายุ")
    expect(page.locator(".errcard a.btn")).to_have_attribute("href", re.compile(r"^/login/\?next="))
    page.context.close()


def test_auth_false_has_no_login_or_logout(browser, server):
    """local tool / app without login: no logout item, and a failed load offers retry instead of a login link"""
    page = new_page(browser, server, "/dashboard/?const.AUTH=0")
    page.click("#profbtn")
    expect(page.locator('#profpop a[href="/auth/logout"]')).to_have_count(0)
    page.keyboard.press("Escape")
    page.context.clear_cookies()
    page.click("#refreshbtn")
    expect(page.locator(".errcard")).to_be_visible()
    expect(page.locator('.errcard a[href^="/login/"]')).to_have_count(0)
    expect(page.locator('.errcard [data-act="retry"]')).to_have_count(1)
    page.context.close()


@pytest.mark.parametrize("width", [390, 768, 1100, 1440])
def test_long_kpi_values_fit_their_tiles(browser, server, width):
    """4 tiles with 9-digit values must stay inside their cards at every width (no clipped or overflowing numbers)"""
    page = new_page(browser, server, GENERIC, width=width)
    page.evaluate("""() => { const t = document.querySelector('.tiles'), first = t.firstElementChild;
        while (t.children.length < 4) t.appendChild(first.cloneNode(true));
        t.style.setProperty('--n', 4); t.classList.remove('odd');
        t.querySelectorAll('.value > span').forEach(s => (s.textContent = '123,456,789')); }""")
    over = page.evaluate("""() => [...document.querySelectorAll('.tile .value')].filter(v => v.scrollWidth > v.clientWidth + 1).length""")
    assert over == 0
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
    page.context.close()


def test_theme_toggle_persists(browser, server):
    page = new_page(browser, server)
    page.click("#profbtn"); page.click('[data-act="theme"]')
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    key = page.evaluate("DASH_KEY") + "Theme"
    assert page.evaluate(f"localStorage.getItem('{key}')") == "dark"
    page.reload(); page.wait_for_selector("#kpi-questions")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.context.close()


@pytest.mark.parametrize("path", ["/dashboard/", GENERIC])
@pytest.mark.parametrize("width", [390, 768, 1100, 1440])
def test_banner_title_clears_buttons(browser, server, path, width):
    page = new_page(browser, server, path, width=width)
    hello = page.locator(".hello").bounding_box()
    tools = page.locator(".banner-tools").bounding_box()
    assert hello["x"] + hello["width"] <= tools["x"] + 1, (hello, tools)
    page.context.close()


@pytest.mark.parametrize("path", ["/dashboard/", "/dashboard/#logs", GENERIC, "/login/"])
@pytest.mark.parametrize("width", [390, 768, 1440])
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_no_horizontal_scroll_and_no_errors(browser, server, path, width, scheme):
    errors = []
    page = new_page(browser, server, path, width=width, height=900, scheme=scheme, login=path != "/login/", errors=errors)
    page.wait_for_timeout(300)
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
    assert not errors, errors
    page.context.close()
