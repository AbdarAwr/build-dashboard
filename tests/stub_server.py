"""Local stub of the dashboard paths (stdlib + Pillow). LOCAL TESTING ONLY — synthetic data from fixture.py.

Mirrors a typical deploy layout (nginx login gate + api behind it):
  /dashboard/          -> <web>/dashboard.html   (cookie required, else 302 /login/?next=...)
                          ?preset=generic           serves the page with PRESET switched (template self-test only)
                          ?const.QUOTA_MONTH=0      rewrites `const QUOTA_MONTH = …;` in the page (test other config values)
                          ?layout=kpis,table,trend  rewrites `layout: [...]` in CONFIG (test section order)
                          ?now=2026-10-14T15:05:00%2B07:00  pins Date in the page (view synthetic data by hand)
  /logs/               -> <web>/logs.html        (cookie required)
  /login/              -> <web>/login.html
  /assets/*            -> <web>/assets/*
  /crops/*             -> a small generated PNG
  GET  <data path>     -> fixture CSV (oldest -> newest, first ?limit=N)   (cookie required)
                          template default: /api/logs.csv (chat) + /api/orders.csv (orders)
                          project: serve_in_thread(data={"/api/sales.csv": (rows, COLUMNS)})
  POST /auth/login     form username/password/next (password = PASSWORD) · GET /auth/logout

    python3 stub_server.py [--web DIR] [--port 8797]   then open http://127.0.0.1:8797/login/
    DIR defaults to ../template inside the skill, or ../web when copied into a project (tests/ next to web/)
"""
import argparse
import io
import mimetypes
import re
import threading
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import fixture as F   # โปรเจกต์ที่เขียน fixture ใหม่จะไม่มี chat_rows/order_rows — ข้อมูลค่าเริ่มต้นจึงสร้างจากสิ่งที่มีเท่านั้น
to_csv = F.to_csv

HERE = Path(__file__).resolve().parent
COOKIE, PASSWORD = "dash_session", "demo-pass"
PAGES = {"/dashboard/": "dashboard.html", "/logs/": "logs.html", "/login/": "login.html"}
PRESET_LINE = "const PRESET = 'chatbot';"


def _png():
    try:
        from PIL import Image
    except ImportError:   # 1x1 PNG
        return bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201a5f2f0b10000000049454e44ae426082")
    buf = io.BytesIO()
    Image.new("RGB", (160, 120), (27, 95, 168)).save(buf, "PNG")
    return buf.getvalue()


def make_handler(web, data, auth=True):
    png = _png()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _authed(self):
            if not auth:   # AUTH = 0: ไม่มี login gate (เครื่องมือในเครื่อง / แอปที่จัดการสิทธิ์เอง)
                return True
            c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            return COOKIE in c and c[COOKIE].value == "ok"

        def _send(self, code, body=b"", ctype="text/plain; charset=utf-8", headers=()):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in headers:
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _redirect(self, loc, headers=()):
            self._send(302, b"", headers=[("Location", loc), *headers])

        def do_GET(self):
            u = urlparse(self.path)
            p, qs = u.path, parse_qs(u.query)
            if not auth and p in ("/login", "/login/"):
                return self._redirect("/dashboard/")
            if p in ("/dashboard", "/logs", "/login"):
                return self._redirect(p + "/")
            if (p in ("/dashboard/", "/logs/") or p in data) and not self._authed():
                return self._redirect("/login/?next=" + quote(p if p not in data else "/dashboard/"))
            if p in data:
                rows, cols = data[p]
                n = int((qs.get("limit") or [str(len(rows))])[0])
                return self._send(200, to_csv(rows[:n], cols).encode("utf-8"), "text/csv; charset=utf-8")
            if p in PAGES:
                body = (web / PAGES[p]).read_text(encoding="utf-8")
                preset = (qs.get("preset") or [""])[0]
                if p == "/dashboard/" and preset in ("chatbot", "generic"):
                    assert PRESET_LINE in body, "template PRESET line changed — update stub_server.PRESET_LINE"
                    body = body.replace(PRESET_LINE, f"const PRESET = '{preset}';")
                lay = (qs.get("layout") or [""])[0]
                if p == "/dashboard/" and re.fullmatch(r"[a-z]+(,[a-z]+)*", lay):   # ?layout=kpis,table,trend (เทสต์ลำดับ section)
                    body, n = re.subn(r"layout: \[[^\]]*\]", "layout: [" + ", ".join(f"'{x}'" for x in lay.split(",")) + "]", body)
                    assert n >= 1, "no `layout: [...]` line in CONFIG"
                now = (qs.get("now") or [""])[0]
                if p == "/dashboard/" and re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+([+-]\d\d:\d\d|Z)", now):   # ?now=ISO ตรึงนาฬิกาไว้ดูข้อมูลสังเคราะห์ด้วยตา
                    pin = ("<script>(()=>{const T=Date.parse('%s'),D=Date;class P extends D{constructor(...a){super(...(a.length?a:[T]))}"
                           "static now(){return T}}window.Date=P;})();</script>") % now
                    body = body.replace("<head>", "<head>\n" + pin, 1)
                for k, v in qs.items():
                    if p == "/dashboard/" and k.startswith("const.") and re.fullmatch(r"[A-Z_]+", k[6:]) and re.fullmatch(r"-?\d+", v[0]):
                        body, n = re.subn(rf"const {k[6:]} = [^;]+;", f"const {k[6:]} = {v[0]};", body)
                        assert n == 1, f"const {k[6:]} not found exactly once"
                return self._send(200, body.encode("utf-8"), "text/html; charset=utf-8")
            if p.startswith("/assets/"):
                f = (web / p.lstrip("/")).resolve()
                if web in f.parents and f.is_file():
                    return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
                return self._send(404, b"not found")
            if p.startswith("/crops/"):
                return self._send(200, png, "image/png")
            if p == "/auth/logout":
                return self._redirect("/login/", [("Set-Cookie", f"{COOKIE}=; Path=/; Max-Age=0")])
            return self._send(404, b"not found")

        def do_POST(self):
            if urlparse(self.path).path != "/auth/login":
                return self._send(404, b"not found")
            form = parse_qs(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8"))
            nxt = (form.get("next") or ["/dashboard/"])[0]
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = "/dashboard/"
            if (form.get("username") or [""])[0] and (form.get("password") or [""])[0] == PASSWORD:
                return self._redirect(nxt, [("Set-Cookie", f"{COOKIE}=ok; Path=/; HttpOnly; SameSite=Lax")])
            return self._redirect("/login/?e=1&next=" + quote(nxt))

    return H


def default_data():
    out = {}
    if hasattr(F, "chat_rows"):
        out["/api/logs.csv"] = (F.chat_rows(), F.CHAT_COLUMNS)
    if hasattr(F, "order_rows"):
        out["/api/orders.csv"] = (F.order_rows(), F.ORDER_COLUMNS)
    return out


def serve_in_thread(web=None, data=None, port=0, auth=True):
    """data = {url path: (rows as dicts, column list)} served as CSV (behind the login cookie unless auth=False)."""
    default = HERE.parent / "template" if (HERE.parent / "template" / "dashboard.html").exists() else HERE.parent / "web"
    web = Path(web or default).resolve()
    if data is None:
        data = default_data()
    h = make_handler(web, data, auth)
    srv = ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default=None)
    ap.add_argument("--port", type=int, default=8797)
    ap.add_argument("--csv", help="เสิร์ฟไฟล์ CSV ของโปรเจกต์แทน fixture (ใช้คู่กับ --path)")
    ap.add_argument("--path", default="/api/data.csv", help="path ที่ CONFIG data.url เรียก เช่น /api/tickets.csv")
    ap.add_argument("--no-auth", action="store_true", help="ไม่มี login gate (AUTH = 0)")
    a = ap.parse_args()
    data = None
    if a.csv:
        import csv as _csv
        with open(a.csv, encoding="utf-8-sig") as fh:
            rd = _csv.DictReader(fh)
            data = {a.path: (list(rd), rd.fieldnames)}
    serve_in_thread(a.web, data=data, port=a.port, auth=not a.no_auth)
    print(f"http://127.0.0.1:{a.port}/" + ("dashboard/" if a.no_auth else f"login/  (any username, password {PASSWORD})") + " · generic: /dashboard/?preset=generic")
    threading.Event().wait()
