"""เทสต์ของชุดดีไซน์ (design/): ui.css ตรงกับแม่แบบ, ตัวตรวจ token, หน้าตั้งต้น page.html ทุกตัวเลือกหน้าตา, UI.live, ชิ้นส่วนของ ui.js

    python3 -m pytest ~/.claude/skills/build-dashboard/tests/test_design.py -q -p no:cacheprovider

หน้าตั้งต้นถูกก็อปไปโฟลเดอร์ชั่วคราวแบบเดียวกับที่โปรเจกต์ทำ (page.html → index.html + ui.css + ui.js + assets/)
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
DESIGN = SKILL / "design"
sys.path.insert(0, str(HERE))
from page_check import check, serve_static  # noqa: E402
from stub_server import serve_in_thread  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def make_site(page_text=None):
    d = Path(tempfile.mkdtemp())
    (d / "assets").mkdir()
    (d / "index.html").write_text(page_text or (DESIGN / "page.html").read_text(encoding="utf-8"), encoding="utf-8")
    for f in ("ui.css", "ui.js"):
        shutil.copy(DESIGN / f, d / f)
    for f in (SKILL / "template" / "assets").glob("*"):
        shutil.copy(f, d / "assets" / f.name)
    return d


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture(scope="module")
def site():
    d = make_site()
    srv = serve_static(d)
    yield f"http://127.0.0.1:{srv.server_port}/"
    srv.shutdown()
    shutil.rmtree(d)


def open_page(browser, url, width=1440, height=900, scheme="light", errors=None, ready=".statcard"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme, locale="th-TH",
                              timezone_id="America/Los_Angeles")
    page = ctx.new_page()
    if errors is not None:
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(url)
    if ready:
        page.wait_for_selector(ready)
    return page


# ---------------------------------------------------------------- แหล่งเดียวของหน้าตา + token
def test_ui_css_is_synced_into_template():
    r = run(DESIGN / "sync.py", "--check")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("f", ["design/page.html", "template/dashboard.html", "template/login.html"])
def test_shipped_tokens_pass_contrast(f):
    r = run(DESIGN / "check_tokens.py", SKILL / f)
    assert r.returncode == 0, r.stdout


def test_check_tokens_catches_low_contrast_and_mismatched_dark_sets(tmp_path):
    src = (DESIGN / "page.html").read_text(encoding="utf-8")
    pale = tmp_path / "pale.html"
    pale.write_text(src.replace("--muted: #55687C;", "--muted: #A9B6C4;", 1), encoding="utf-8")
    r = run(DESIGN / "check_tokens.py", pale)
    assert r.returncode == 1 and "--muted บน --surface" in r.stdout
    i = src.index(':root[data-theme="dark"] {')
    split = tmp_path / "split.html"
    split.write_text(src[:i] + src[i:].replace("--muted: #93A7BB;", "--muted: #93A7BC;", 1), encoding="utf-8")
    r = run(DESIGN / "check_tokens.py", split)
    assert r.returncode == 1 and "ชุดมืดสองชุด" in r.stdout and "--muted" in r.stdout


def test_page_check_catches_overflow_and_horizontal_scroll(browser, tmp_path):
    (tmp_path / "index.html").write_text("""<!doctype html><meta charset="utf-8"><body style="margin:0">
      <div class="card" style="width:300px;padding:10px;border:1px solid"><b style="display:inline-block;width:500px">ยาวเกินการ์ด</b></div>
      <div style="width:2000px">กว้างเกินจอ</div>""", encoding="utf-8")
    srv = serve_static(tmp_path)
    try:
        (_, probs), = check(browser, f"http://127.0.0.1:{srv.server_port}/", sizes=[(800, 600)], schemes=["light"])
    finally:
        srv.shutdown()
    assert any("scroll แนวนอน" in p for p in probs) and any("ล้นการ์ด" in p for p in probs), probs


# ---------------------------------------------------------------- หน้าตั้งต้น: ทุกตัวเลือกหน้าตา
def test_page_every_variant_fits_without_errors(browser, site):
    res = check(browser, site, sizes=[(390, 844), (820, 1180), (1440, 900)], schemes=["light", "dark"], ready=".statcard",
                queries=["", "?shell=top&hero=plain&density=compact&cards=outline", "?shell=embed&cards=flat"])
    res += check(browser, site, sizes=[(1280, 720), (1920, 1080)], schemes=["dark"], ready=".statcard",
                 queries=["?shell=wall&hero=plain&cards=flat"])
    bad = [(n, p) for n, p in res if p]
    assert not bad, bad


def test_page_sections_follow_layout_and_nav(browser, site):
    page = open_page(browser, site)
    ids = page.eval_on_selector_all("#flow > *", "els => els.map(e => e.id)")
    assert ids == page.evaluate("LAYOUT.map(s => s.id)")
    navs = page.eval_on_selector_all("#sidenav .nav", "els => els.map(e => e.dataset.sec)")
    assert navs == ["top"] + page.evaluate("LAYOUT.filter(s => s.nav).map(s => s.id)")
    expect(page.locator("#sidenav .nav.on")).to_have_count(1)
    assert page.evaluate("getComputedStyle(document.getElementById('headline')).gridColumnStart") == "span 4"
    page.context.close()


def test_layout_id_clash_is_an_error(browser, tmp_path):
    src = (DESIGN / "page.html").read_text(encoding="utf-8").replace("{ id: 'products',", "{ id: 'top',", 1)
    d = make_site(src)
    srv = serve_static(d)
    errors = []
    try:
        page = open_page(browser, f"http://127.0.0.1:{srv.server_port}/", errors=errors, ready=None)
        page.wait_for_timeout(500)
        page.context.close()
    finally:
        srv.shutdown()
        shutil.rmtree(d)
    assert any("LAYOUT" in e for e in errors), errors


def test_theme_and_side_preferences_persist(browser, site):
    page = open_page(browser, site)
    page.click("#themeBtn")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.click("#burger")
    page.reload()
    page.wait_for_selector(".statcard")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert page.evaluate("document.documentElement.classList.contains('side-mini')")
    page.context.close()


def test_wall_scales_to_screen_and_has_no_controls(browser, site):
    page = open_page(browser, site + "?shell=wall&hero=plain", width=1280, height=720)
    assert page.evaluate("document.documentElement.style.zoom") == "0.667"     # ออกแบบที่ 1920×1080 แล้วย่อตามจอ
    for sel in (".side", "#themeBtn", ".pagehead"):
        assert not page.locator(sel).is_visible(), sel
    assert page.evaluate("getComputedStyle(document.body).cursor") == "none"
    page.context.close()


# ---------------------------------------------------------------- UI.live: ความสดของข้อมูล
@pytest.fixture()
def fed_site(browser, site):
    """หน้าตั้งต้นที่อ่านข้อมูลจาก /data.json (ข้อมูลชุดเดียวกับ demo) — คืน (url, data) ให้เทสต์แก้ data ได้"""
    page = open_page(browser, site)
    data = json.loads(page.evaluate("JSON.stringify(demo())"))
    page.context.close()
    src = (DESIGN / "page.html").read_text(encoding="utf-8").replace("source: null,", "source: 'data.json',", 1)
    d = make_site(src)
    srv = serve_static(d, {"/data.json": data})
    yield f"http://127.0.0.1:{srv.server_port}/", data
    srv.shutdown()
    shutil.rmtree(d)


def test_stale_data_dims_page_and_hides_all_ok_summary(browser, fed_site):
    url, data = fed_site
    data["generated_at"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    page = open_page(browser, url)
    expect(page.locator("#alert .notice.crit")).to_contain_text("ไม่อัปเดตมา")
    assert page.evaluate("document.body.classList.contains('stale')")
    expect(page.locator("#status .chips")).to_have_count(0)
    expect(page.locator("#pulse")).to_have_class(re.compile(r"\berr\b"))
    page.context.close()

    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    page = open_page(browser, url)
    expect(page.locator("#status .chips .pill")).to_have_count(2)                 # ช้า 1 · ปกติ 3
    expect(page.locator("#alert")).to_be_empty()
    assert not page.evaluate("document.body.classList.contains('stale')")
    page.context.close()


def test_failed_first_load_says_so(browser, tmp_path):
    src = (DESIGN / "page.html").read_text(encoding="utf-8").replace("source: null,", "source: 'missing.json',", 1)
    d = make_site(src)
    srv = serve_static(d)
    try:
        page = open_page(browser, f"http://127.0.0.1:{srv.server_port}/", ready="#alert .notice")
        expect(page.locator("#alert .notice.crit")).to_contain_text("โหลดข้อมูลไม่ได้ (HTTP 404)")
        expect(page.locator("#updated")).to_have_text("โหลดไม่ได้")
        page.context.close()
    finally:
        srv.shutdown()
        shutil.rmtree(d)


# ---------------------------------------------------------------- ชิ้นส่วนของ ui.js
def test_bar_chart_has_tooltip_and_table(browser, site):
    page = open_page(browser, site)
    page.locator("#trend .hit").last.hover()
    expect(page.locator(".uitip")).to_be_visible()
    expect(page.locator(".uitip")).to_contain_text("คำสั่งซื้อ")
    assert page.locator("#trend details.tview tbody tr").count() == 30
    expect(page.locator("#trend .refl-t")).to_have_text("เป้า 120/วัน")
    page.context.close()


def test_meter_modes(browser, site):
    page = open_page(browser, site)
    m = lambda o: page.evaluate(f"UI.meter({json.dumps(o)})")
    t = m({"label": "เป้า", "pct": 120, "mode": "target"})
    assert "ถึงเป้า" in t and "120%" in t and 'class="meter "' in t           # เป้าหมายไม่มีสีเตือน
    assert 'class="meter warn"' in m({"label": "ดิสก์", "pct": 85}) and "ใกล้เต็ม" in m({"label": "ดิสก์", "pct": 85})
    assert 'class="meter crit"' in m({"label": "ดิสก์", "pct": 100})
    page.context.close()


def test_html_helpers_escape_data(browser, site):
    page = open_page(browser, site)
    evil = "<img src=x onerror=alert(1)>"
    out = page.evaluate("""e => [UI.statCard({ name: e, state: 'ok', stateText: e, nums: [[e, e]], foot: e }),
        UI.tile({ label: e, value: e, hint: e, status: { tone: 'warn', text: e } }), UI.rankList([[e, 3]]), UI.pill('ok', e),
        UI.meter({ label: e, pct: 50 })].join('')""", evil)
    assert "<img" not in out and out.count("&lt;img") >= 10
    page.context.close()


def test_delta_colours_follow_good_direction(browser, site):
    page = open_page(browser, site)
    assert 'class="delta up"' in page.evaluate("UI.delta(110, 100)")
    assert 'class="delta down"' in page.evaluate("UI.delta(110, 100, { goodWhen: 'down' })")   # ต้นทุนขึ้น = แย่
    assert 'class="delta flat"' in page.evaluate("UI.delta(100, 100)")
    assert page.evaluate("UI.fmtMillion(3184000)") == "3.18 ล้าน" and page.evaluate("UI.fmtMillion(950000)") == "950,000"
    page.context.close()


# ---------------------------------------------------------------- ทางแม่แบบ ENGINE ใช้ตัวเลือกหน้าตาเดียวกันได้
@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("q", ["shell=top&hero=plain&density=compact&cards=outline", "shell=embed"])
def test_engine_template_accepts_layout_variants(browser, width, q):
    srv = serve_in_thread(auth=False)
    try:
        url = f"http://127.0.0.1:{srv.server_port}/dashboard/?const.AUTH=0&{q}"
        res = check(browser, url, sizes=[(width, 900)], schemes=["light"], ready="#logtable tbody tr")
        assert not res[0][1], res
        page = open_page(browser, url, width=width, ready="#logtable tbody tr")
        shell = q.split("&")[0].split("=")[1]
        assert page.evaluate("document.documentElement.dataset.shell") == shell
        if shell == "top":
            assert page.locator(".side").bounding_box()["height"] < 120               # แถบเมนูอยู่บน ไม่ใช่แถบข้าง
        else:
            assert not page.locator(".side").is_visible() and not page.locator(".banner").is_visible()
        page.context.close()
    finally:
        srv.shutdown()


def test_negative_values_draw_no_ranking_bar(browser, site):
    """ค่าติดลบ (การเติบโต −19%) ต้องไม่มีแท่ง — เดิม width ติดลบ = CSS ไม่รับ แล้วแท่งเต็มความกว้าง"""
    page = open_page(browser, site)
    out = page.evaluate("UI.rankList([{ label: 'ภูเก็ต', value: 30, prev: 20 }, { label: 'สีลม', value: -19 }], v => v + '%')")
    assert 'style="width:0%"' in out and 'class="delta up"' in out
    page.context.close()
    srv = serve_in_thread(auth=False)
    try:
        page = open_page(browser, f"http://127.0.0.1:{srv.server_port}/dashboard/?const.AUTH=0", ready="#logtable tbody tr")
        out = page.evaluate("rankList([['a', 10], ['b', -5]], 10, '', String)")      # ENGINE ของแม่แบบ
        assert 'style="width:0%"' in out
        page.context.close()
    finally:
        srv.shutdown()


def test_meter_pace_mark(browser, site):
    page = open_page(browser, site)
    out = page.evaluate("UI.meter({ label: 'เป้า', pct: 42.7, mode: 'target', mark: 44, markLabel: 'เดือนผ่านไปแล้ว' })")
    assert 'class="m-mark" style="left:44%"' in out and "เดือนผ่านไปแล้ว 44%" in out
    expect(page.locator("#headline .m-mark")).to_have_count(1)
    page.context.close()


def test_line_chart_series_gaps_legend_tooltip_and_table(browser, site):
    page = open_page(browser, site)
    page.evaluate("""() => { const d = document.createElement('div'); d.id = 'lc'; d.style.width = '600px';
      document.getElementById('main').prepend(d);
      UI.lineChart(d, { labels: ['1', '2', '3', '4'], titles: ['1 ต.ค.', '2 ต.ค.', '3 ต.ค.', '4 ต.ค.'], unit: 'บาท', area: true,
        series: [{ label: 'ยอดสะสม', values: [10, 25, null, null] }, { label: 'เป้าสะสม', values: [12, 24, 36, 48], dashed: true }] }); }""")
    assert page.locator("#lc .ln").count() == 2 and page.locator("#lc .ln.dash").count() == 1
    assert page.get_attribute("#lc .ln.s0", "d").count("M") == 1                    # ค่า null ท้ายเส้น = เส้นหยุด ไม่ลากลงศูนย์
    expect(page.locator("#lc .ulegend span")).to_have_count(2)
    page.locator("#lc svg").hover(position={"x": 60, "y": 100})
    expect(page.locator(".uitip")).to_contain_text("ยอดสะสม")
    expect(page.locator(".uitip")).to_contain_text("เป้าสะสม")
    assert page.locator("#lc details.tview tbody tr").count() == 4
    page.context.close()


def test_csv_parser_and_month_pace(browser, site):
    page = open_page(browser, site)
    rows = page.evaluate("UI.parseCSV('\\ufeffid,name,note\\r\\n1,\"ร้าน, สาขา 1\",\"บรรทัด\\nสอง\"\\n2,\"ว่า \"\"ดี\"\"\",\\n')")
    assert rows == [{"id": "1", "name": "ร้าน, สาขา 1", "note": "บรรทัด\nสอง"}, {"id": "2", "name": 'ว่า "ดี"', "note": ""}]
    # 14 ต.ค. 15:05 เวลาไทย (เบราว์เซอร์อยู่โซน LA): ผ่านไป 13 วัน 15:05 ชม. จาก 31 วัน, เดือนก่อนช่วงเดียวกัน = 14 ก.ย. 15:05
    mp = page.evaluate("(() => { const m = UI.monthPace('2026-10-14T15:05:00+07:00'); return { pct: m.pct, day: m.day, days: m.days, start: m.start.toISOString(), prevSame: m.prevSame.toISOString() }; })()")
    assert mp["day"] == 14 and mp["days"] == 31 and abs(mp["pct"] - (13 + 15 / 24 + 5 / 1440) / 31 * 100) < 1e-6
    assert mp["start"] == "2026-09-30T17:00:00.000Z" and mp["prevSame"] == "2026-09-14T08:05:00.000Z"
    page.context.close()


# ---------------------------------------------------------------- จอทีวี: พอดีจอทุกขนาด การ์ดที่มีปัญหาเป็นสีทึบ
WALL_ONLY = ("  { id: 'headline',", "  { id: 'trend',", "  { id: 'products',", "  { id: 'events',")


def wall_page():
    """หน้าตั้งต้นที่เหลือแค่ KPI + สถานะ (ขนาดเนื้อหาแบบจอทีวีจริง)"""
    src = (DESIGN / "page.html").read_text(encoding="utf-8")
    keep = [l for l in src.split("\n") if not l.startswith(WALL_ONLY)]
    return "\n".join(keep).replace('data-shell="side" data-hero="banner"', 'data-shell="wall" data-hero="plain" data-theme="dark"', 1)


def test_wall_fits_the_screen_at_720p_1080p_and_4k(browser):
    d = make_site(wall_page())
    srv = serve_static(d)
    try:
        res = check(browser, f"http://127.0.0.1:{srv.server_port}/", sizes=[(1280, 720), (1920, 1080), (3840, 2160)],
                    schemes=["dark"], ready=".statcard", fit=True)
    finally:
        srv.shutdown()
        shutil.rmtree(d)
    bad = [(n, p) for n, p in res if p]
    assert not bad, bad


def test_wall_problem_cards_are_solid_and_text_is_large(browser):
    d = make_site(wall_page())
    srv = serve_static(d)
    try:
        page = open_page(browser, f"http://127.0.0.1:{srv.server_port}/", width=1920, height=1080)
        warn = page.locator(".statcard.warn")
        assert warn.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(242, 169, 59)"        # --warn-fill
        pill = warn.locator(".pill")
        assert pill.evaluate("e => getComputedStyle(e).color") == "rgb(242, 169, 59)"                  # คำในป้ายไม่จมหาย
        smallest = page.evaluate("""() => Math.min(...[...document.querySelectorAll('#flow *, .banner *')]
          .filter(e => e.offsetParent !== null && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
          .map(e => parseFloat(getComputedStyle(e).fontSize)))""")
        assert smallest >= 20, smallest                                                                 # อ่านได้จาก 3–4 เมตร
        page.context.close()
    finally:
        srv.shutdown()
        shutil.rmtree(d)


def test_page_check_catches_content_spilling_down(browser, tmp_path):
    (tmp_path / "index.html").write_text("""<!doctype html><meta charset="utf-8"><body style="margin:0">
      <div class="card" style="height:80px;width:300px;border:1px solid"><p>บรรทัด 1</p><p>บรรทัด 2</p><p>บรรทัด 3</p><p>บรรทัด 4</p></div>""",
                                         encoding="utf-8")
    srv = serve_static(tmp_path)
    try:
        (_, probs), = check(browser, f"http://127.0.0.1:{srv.server_port}/", sizes=[(800, 600)], schemes=["light"])
    finally:
        srv.shutdown()
    assert any("ล้นการ์ดลงล่าง" in p for p in probs), probs


# ---------------------------------------------------------------- ข้อมูล: เวลาของข้อมูล, ได้หน้าเว็บแทนข้อมูล, ตัวช่วยรวมยอด
def test_loaders_read_data_time_and_reject_html(browser, tmp_path):
    d = make_site()
    (tmp_path / "orders.csv").write_text("timestamp,amount\n2026-10-14T10:00:00+07:00,100\n", encoding="utf-8")
    (tmp_path / "login.html").write_text("<!doctype html><title>login</title>", encoding="utf-8")
    srv = serve_static(d, {"/api/orders.csv": tmp_path / "orders.csv", "/api/x.json": tmp_path / "login.html"},
                       {"/api/orders.csv": {"X-Generated-At": "2026-10-14T02:00:00+07:00"}})
    try:
        page = open_page(browser, f"http://127.0.0.1:{srv.server_port}/")
        assert page.evaluate("UI.getCSV('/api/orders.csv').then(UI.dataTime)") == "2026-10-14T02:00:00+07:00"
        assert page.evaluate("UI.getCSV('/api/orders.csv').then(r => r[0].amount)") == "100"
        assert "หน้าเว็บแทนข้อมูล" in page.evaluate("UI.getJSON('/api/x.json').then(() => 'ok', e => e.message)")
        assert page.evaluate("UI.dataTime({ generated_at: null })") is None                    # null ไม่ใช่ 1 ม.ค. 1970
        page.context.close()
    finally:
        srv.shutdown()
        shutil.rmtree(d)


def test_money_format_and_row_helpers(browser, site):
    page = open_page(browser, site)
    e = page.evaluate
    assert e("UI.fmtMillion(12000000)") == "12.00 ล้าน" and e("UI.fmtMillion(399504.87)") == "399,505"
    assert e("UI.fmtMillion(399504.87, { always: true })") == "0.40 ล้าน" and e("UI.fmtMillion(12e6, { digits: 0 })") == "12 ล้าน"
    rows = [{"t": "2026-10-12T00:10:00+07:00", "b": "สยาม", "v": "100"}, {"t": "2026-10-18T23:50:00+07:00", "b": "สีลม", "v": "250"},
            {"t": "2026-10-19T00:05:00+07:00", "b": "สยาม", "v": "200"}, {"t": "2026-10-11T23:59:00+07:00", "b": "", "v": "999"}]
    assert e("r => UI.groupSum(r, x => x.b, x => x.v)", rows) == [["สยาม", 300], ["สีลม", 250]]
    assert e("r => r.map(x => UI.weekKey(x.t))", rows) == ["2026-10-12", "2026-10-12", "2026-10-19", "2026-10-05"]   # จันทร์ต้นสัปดาห์ เวลาไทย
    assert e("r => UI.sum(UI.between(r, x => x.t, '2026-10-12T00:00:00+07:00', '2026-10-19T00:00:00+07:00'), x => x.v)", rows) == 350
    page.context.close()


# ---------------------------------------------------------------- เทสต์ตั้งต้นของโปรเจกต์ทาง 2 ใช้ได้จริง
def test_project_test_template_passes_on_a_sample_project(browser, site, tmp_path):
    page = open_page(browser, site)
    data = json.loads(page.evaluate("JSON.stringify(demo())"))
    page.context.close()
    proj = tmp_path / "proj"
    web = make_site((DESIGN / "page.html").read_text(encoding="utf-8").replace("source: null,", "source: '/api/overview',", 1))
    shutil.copytree(web, proj / "web")
    shutil.rmtree(web)
    (proj / "tests").mkdir()
    for f in ("test_page.py", "page_check.py"):
        shutil.copy(HERE / f, proj / "tests" / f)
    (proj / "tests" / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", str(proj / "tests" / "test_page.py"), "-q", "-p", "no:cacheprovider"],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "4 passed" in r.stdout, r.stdout[-3000:]
