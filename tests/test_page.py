"""เทสต์ตั้งต้นของหน้าออกแบบเอง (ทาง 2) — ก็อปไปไว้ใน tests/ ข้าง web/ แล้วแก้ค่าที่มี [แก้] ด้านล่าง

    python3 -m pytest tests/test_page.py -q -p no:cacheprovider

เทสต์ชุดนี้ตรวจสิ่งที่ทุกหน้าต้องมี: ทุกขนาดจอและธีมไม่มี error/scroll แนวนอน/การ์ดทับกัน, ทุก section ขึ้นข้อมูล,
โหลดไม่ได้แล้วบอก, ข้อมูลเก่าแล้วบอก · ส่วนที่ต้องเขียนเพิ่มเอง: เทียบตัวเลขบนหน้ากับตัวเลขที่คำนวณจากไฟล์ข้อมูลสังเคราะห์ด้วย Python
(ไม่ใช่เลขที่พิมพ์ตายตัว) และกรณีขอบของข้อมูล (ค่า null, สถานะที่ไม่รู้จัก, รายการว่าง, ข้อความที่มี <)
"""
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from page_check import check, serve_static  # noqa: E402

WEB = HERE.parent / "web"
PAGE = "/"                                       # [แก้] path ของหน้าใน web/
DATA = {"/api/overview": HERE / "data.json"}     # [แก้] endpoint ที่หน้าเรียก → ไฟล์ข้อมูลสังเคราะห์ (JSON หรือ CSV)
READY = "#flow .sec-body > *"                    # [แก้] selector ที่ขึ้นเมื่อวาดข้อมูลเสร็จ
NOW = None                                       # [แก้] ตรึงนาฬิกาเมื่อข้อมูลมีวันที่ตายตัว เช่น datetime(2026, 10, 14, 15, 5, tzinfo=BKK)
SIZES = [(390, 844), (1440, 900)]                # [แก้] ขนาดจอตาม brief · จอทีวี: [(1280, 720), (1920, 1080), (3840, 2160)] และ FIT = True
SCHEMES = ["light", "dark"]
FIT = False


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        yield b
        b.close()


def serve(routes=None, headers=None):
    srv = serve_static(WEB, DATA if routes is None else routes, headers)
    return srv, f"http://127.0.0.1:{srv.server_port}{PAGE}"


def open_page(browser, url, ready=READY):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="th-TH", timezone_id="America/Los_Angeles")
    page = ctx.new_page()
    if NOW:
        page.clock.set_fixed_time(NOW)
    page.goto(url)
    page.wait_for_selector(ready)
    return page


def test_fits_every_size_and_theme(browser):
    srv, url = serve()
    try:
        res = check(browser, url, sizes=SIZES, schemes=SCHEMES, ready=READY, fit=FIT, now=NOW)
    finally:
        srv.shutdown()
    bad = [(n, p) for n, p in res if p]
    assert not bad, bad


def test_every_section_shows_data(browser):
    srv, url = serve()
    try:
        page = open_page(browser, url)
        empty = page.evaluate("""() => LAYOUT.map(s => s.id).filter(id => {
            const b = document.querySelector('#' + id + ' .sec-body');
            return !b || !b.textContent.trim() && !b.querySelector('svg, img, canvas'); })""")
        page.context.close()
    finally:
        srv.shutdown()
    assert not empty, f"section ที่ไม่มีข้อมูล: {empty}"


def test_failed_load_says_so(browser):
    srv, url = serve(routes={})                  # endpoint หายหมด → 404
    try:
        page = open_page(browser, url, ready="#alert .notice")
        expect(page.locator("#alert .notice.crit")).to_contain_text("โหลดข้อมูลไม่ได้")
        page.context.close()
    finally:
        srv.shutdown()


def test_old_data_is_flagged_as_stale(browser):
    """ข้อมูลเก่า 10 วัน (ผ่าน generated_at ในข้อมูล หรือ header X-Generated-At ของไฟล์ที่ไม่ใช่ JSON) ต้องขึ้นแถบแดงและตัวเลขจาง"""
    old = ((NOW or datetime.now(timezone.utc)) - timedelta(days=10)).isoformat()
    path, src = next(iter(DATA.items()))
    routes, headers = dict(DATA), {}
    if str(src).endswith(".json"):
        data = json.loads(Path(src).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = copy.deepcopy(data)
            data["generated_at"] = old
            routes[path] = data
        else:
            headers[path] = {"X-Generated-At": old}
    else:
        headers[path] = {"X-Generated-At": old}
    srv, url = serve(routes, headers)
    try:
        page = open_page(browser, url, ready="#alert .notice")
        expect(page.locator("#alert .notice.crit")).to_contain_text("ไม่อัปเดตมา")
        assert page.evaluate("document.body.classList.contains('stale')")
        page.context.close()
    finally:
        srv.shutdown()
