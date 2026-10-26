"""ตรวจหน้า dashboard ใดก็ได้ในเบราว์เซอร์จริง: ทุกขนาดจอ × ทั้งสองธีม × ตัวเลือกหน้าตา แล้วถ่ายภาพไว้ให้เปิดดูเอง

    # หน้าแบบไฟล์ static (ทางที่ 2): เสิร์ฟโฟลเดอร์ web/ + ข้อมูลสังเคราะห์ต่อ path (JSON, CSV หรือไฟล์ใดก็ได้)
    python3 page_check.py --web <project>/web --data /api/overview=tests/overview.json --out shots
    python3 page_check.py --web <project>/web --data /api/orders.csv=tests/orders.csv --now 2026-10-14T15:05:00+07:00 --out shots
    # หน้าที่มีเซิร์ฟเวอร์ของตัวเองอยู่แล้ว
    python3 page_check.py --url http://127.0.0.1:8777/ --ready .svc --out shots
    # จอทีวี: ทั้งหน้าต้องอยู่ในจอโดยไม่ต้องเลื่อน
    python3 page_check.py --web web --sizes 1280x720,1920x1080 --schemes dark --fit --out shots

ตรวจ: ไม่มี error ใน console / ไฟล์ที่โหลดไม่ได้, ไม่มี scroll แนวนอน, การ์ดในตาราง (.flow/.tiles/.grid) ไม่ทับกัน,
เนื้อหาในการ์ดไม่ล้นออกข้างหรือล้นลงล่าง, และ (--fit) ไม่มี scroll แนวตั้ง · เบราว์เซอร์ตั้งโซนเวลาเป็น Los Angeles โดยตั้งใจ
exit 1 ถ้ามีกรณีไม่ผ่าน · ใช้ใน pytest ได้ด้วย `from page_check import check`
"""
import argparse
import functools
import json
import mimetypes
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CHECK_JS = """() => {
  const de = document.documentElement, out = [];
  if (de.scrollWidth > de.clientWidth + 1) out.push(`scroll แนวนอน ${de.scrollWidth - de.clientWidth}px`);
  const box = e => e.getBoundingClientRect();
  for (const wrap of document.querySelectorAll('.flow, .tiles, .grid')) {
    const kids = [...wrap.children].filter(k => k.offsetParent !== null);
    for (let i = 0; i < kids.length; i++) for (let j = i + 1; j < kids.length; j++) {
      const a = box(kids[i]), b = box(kids[j]);
      const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left), oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ox > 1 && oy > 1) out.push(`การ์ดทับกัน: ${kids[i].id || kids[i].className} กับ ${kids[j].id || kids[j].className}`);
    }
  }
  for (const card of document.querySelectorAll('.card, .statcard, .tile')) {
    if (!card.checkVisibility({ visibilityProperty: true })) continue;
    const c = box(card);
    for (const el of card.querySelectorAll('*')) {
      // ข้ามของที่มองไม่เห็น (รวมเนื้อหาใน <details> ที่ปิดอยู่ ซึ่ง Chrome ยังจัดวางไว้แต่ไม่แสดง)
      if (!el.checkVisibility({ visibilityProperty: true }) || !el.childNodes.length || getComputedStyle(el).position === 'fixed') continue;
      const r = box(el);
      const side = r.width && (r.right > c.right + 2 || r.left < c.left - 2), down = r.height && (r.bottom > c.bottom + 2 || r.top < c.top - 2);
      if (side || down) {   // ล้นออกข้าง หรือล้นลงล่าง (การ์ดสูงคงที่บนจอทีวี เนื้อหาทับการ์ดแถวถัดไป)
        let p = el.parentElement, clipped = false;
        while (p && p !== card) { const cs = getComputedStyle(p); if ((side ? cs.overflowX : cs.overflowY) !== 'visible') { clipped = true; break; } p = p.parentElement; }
        if (!clipped) { out.push(`ล้นการ์ด${side ? '' : 'ลงล่าง'}: <${el.tagName.toLowerCase()} class="${el.className.baseVal ?? el.className}"> ใน ${card.id || card.className}`); break; }
      }
    }
  }
  return out;
}"""


def serve_static(web, routes=None, headers=None):
    """เสิร์ฟโฟลเดอร์ web (127.0.0.1 พอร์ตสุ่ม) + routes = {path: dict/list (ตอบเป็น JSON) หรือที่อยู่ไฟล์ (อ่านใหม่ทุกครั้ง)}
    headers = {path: {ชื่อ: ค่า}} เพิ่ม header ให้ path นั้น เช่น {'/api/orders.csv': {'X-Generated-At': '...'}}"""
    routes, headers = dict(routes or {}), dict(headers or {})

    class H(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in routes:
                v = routes[path]
                if isinstance(v, (dict, list)):
                    body, ctype = json.dumps(v, ensure_ascii=False).encode(), "application/json; charset=utf-8"
                else:
                    body = Path(v).read_bytes()
                    ctype = (mimetypes.guess_type(str(v))[0] or "application/octet-stream") + "; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                for k, hv in headers.get(path, {}).items():
                    self.send_header(k, hv)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=str(web)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def check(browser, url, sizes=((390, 844), (1440, 900)), schemes=("light", "dark"), queries=("",), ready="body",
          fit=False, out=None, settle_ms=500, now=None):
    """คืน [(ชื่อกรณี, [ปัญหา...])] — ลิสต์ปัญหาว่าง = ผ่าน"""
    results = []
    for q in queries:
        for w, h in sizes:
            for scheme in schemes:
                name = f"{w}x{h}-{scheme}" + (f"-{q.strip('?&').replace('&', '-').replace('=', '_')}" if q else "")
                ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, locale="th-TH",
                                          timezone_id="America/Los_Angeles")
                page = ctx.new_page()
                if now:   # ตรึงนาฬิกาของหน้า ให้ข้อมูลสังเคราะห์ที่มีวันที่ตายตัวตรงกับ "วันนี้/เดือนนี้"
                    page.clock.set_fixed_time(now)
                probs = []
                page.on("pageerror", lambda e: probs.append(f"JS error: {e}"))
                page.on("console", lambda m: probs.append(f"console: {m.text}") if m.type == "error" else None)
                page.on("response", lambda r: probs.append(f"โหลดไม่ได้ {r.status}: {r.url}") if r.status >= 400 else None)
                sep = "&" if "?" in url else "?"
                page.goto(url + (sep + q.lstrip("?&") if q else ""))
                page.wait_for_selector(ready)
                page.wait_for_timeout(settle_ms)
                probs += page.evaluate(CHECK_JS)
                if fit and page.evaluate("document.documentElement.scrollHeight > innerHeight + 1"):
                    probs.append(f"ต้องเลื่อนลง (สูง {page.evaluate('document.documentElement.scrollHeight')}px ในจอ {h}px)")
                if out:   # หน้าที่ย่อ/ขยายด้วย zoom (จอ wall) ถ่ายเต็มหน้าแล้วขนาดเพี้ยน จึงถ่ายเฉพาะจอ
                    zoomed = page.evaluate("(document.documentElement.style.zoom || '1') !== '1'")
                    Path(out).mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(Path(out) / f"{name}.png"), full_page=not (fit or zoomed))
                results.append((name, probs))
                ctx.close()
    return results


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--web", help="โฟลเดอร์หน้า static (เสิร์ฟเองที่ 127.0.0.1)")
    src.add_argument("--url", help="URL ของหน้าที่รันอยู่แล้ว")
    ap.add_argument("--page", default="/", help="path ของหน้าเมื่อใช้ --web (ค่าเริ่มต้น /)")
    ap.add_argument("--data", "--json", action="append", default=[], help="/api/x=ไฟล์ (JSON, CSV, …) ใส่ได้หลายครั้ง")
    ap.add_argument("--now", help="ตรึงนาฬิกาของหน้า เช่น 2026-10-14T15:05:00+07:00")
    ap.add_argument("--sizes", default="390x844,1440x900", help="เช่น 390x844,1440x900,1920x1080")
    ap.add_argument("--schemes", default="light,dark")
    ap.add_argument("--query", action="append", default=None, help="ตัวเลือกเพิ่ม เช่น '?shell=wall' (ใส่ได้หลายครั้ง)")
    ap.add_argument("--ready", default="body", help="selector ที่ต้องขึ้นก่อนตรวจ เช่น .statcard")
    ap.add_argument("--fit", action="store_true", help="ทั้งหน้าต้องอยู่ในจอ (จอทีวี)")
    ap.add_argument("--out", help="โฟลเดอร์เก็บภาพหน้าจอ")
    a = ap.parse_args(argv)
    from playwright.sync_api import sync_playwright
    srv = None
    if a.web:
        srv = serve_static(a.web, dict(x.split("=", 1) for x in a.data))
        url = f"http://127.0.0.1:{srv.server_port}{a.page}"
    else:
        url = a.url
    sizes = [tuple(int(n) for n in s.split("x")) for s in a.sizes.split(",")]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        res = check(b, url, sizes, a.schemes.split(","), a.query or [""], a.ready, a.fit, a.out, now=a.now)
        b.close()
    if srv:
        srv.shutdown()
    bad = 0
    for name, probs in res:
        print(("ผ่าน   " if not probs else "ไม่ผ่าน") + f" {name}" + "".join(f"\n        - {x}" for x in probs))
        bad += bool(probs)
    print(f"{len(res) - bad}/{len(res)} กรณีผ่าน" + (f" · ภาพอยู่ที่ {a.out}" if a.out else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
