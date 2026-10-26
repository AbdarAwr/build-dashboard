"""ตรวจ token สีของ dashboard: ตัวหนังสือบนพื้นต้องอ่านออก (WCAG) ทั้งโหมดสว่างและมืด และชุดมืดสองชุดต้องตรงกัน

    python3 design/check_tokens.py <project>/web/dashboard.html      # ไฟล์ html หรือ css ที่มีบล็อก :root
    python3 design/check_tokens.py page.html --all                   # แสดงทุกคู่ ไม่ใช่เฉพาะที่ไม่ผ่าน

อ่านบล็อก `:root {`, `:root:not([data-theme="light"]) {` (ใน media มืด) และ `:root[data-theme="dark"] {`
สีโปร่ง (rgba) ผสมบนพื้นก่อนวัด · gradient วัดทุกจุดสี · exit 1 ถ้ามีคู่ไม่ผ่าน
"""
import re
import sys
from pathlib import Path

# (ตัวหน้า, พื้น, ค่าต่ำสุด, ใช้ทำอะไร[, จุดของ gradient]) — 4.5 = ตัวหนังสือ, 3.0 = ไอคอน/แท่งกราฟ
# จุดของ gradient: ไม่ระบุ = ทุกจุดสี · 'end' = สองจุดท้าย (ของที่อยู่ล่างสุด) · 'mid' = สีกลางระหว่างจุดแรกกับจุดท้าย (ไอคอนกลางวงกลม)
PAIRS = [
    ("ink", "surface", 4.5, "ตัวหนังสือหลักบนการ์ด"),
    ("ink", "page", 4.5, "ตัวหนังสือหลักบนพื้นหน้า"),
    ("ink-2", "surface", 4.5, "ตัวหนังสือรอง"),
    ("ink-2", "plane", 4.5, "หัวตาราง"),
    ("muted", "surface", 4.5, "คำอธิบาย/hint บนการ์ด"),
    ("muted", "page", 4.5, "คำอธิบายบนพื้นหน้า"),
    ("head", "page", 4.5, "ชื่อบนแบนเนอร์/หัวหน้า"),
    ("head", "surface", 4.5, "หัวการ์ด/ตัวเลขใหญ่"),
    ("accent-ink", "surface", 4.5, "ตัวหนังสือสีเน้น"),
    ("accent-ink", "accent-soft", 4.5, "ป้าย info/busy"),
    ("link", "surface", 4.5, "ลิงก์"),
    ("on-primary", "primary", 4.5, "ปุ่มหลัก"),
    ("side-ink", "side", 4.5, "เมนูข้าง"),
    ("side-sub", "side", 4.5, "คำอธิบายท้ายแถบข้าง", "end"),
    ("nav-on-ink", "nav-on", 4.5, "เมนูที่เลือกอยู่"),
    ("pill-on-ink", "pill-on", 4.5, "ปุ่มช่วงเวลาที่เลือก"),
    ("btn-dark-ink", "btn-dark", 4.5, "ปุ่มเข้ม"),
    ("ok", "ok-soft", 4.5, "ป้ายปกติ"),
    ("warn", "warn-soft", 4.5, "ป้ายเตือน"),
    ("crit", "crit-soft", 4.5, "ป้ายวิกฤต"),
    ("warn", "surface", 4.5, "ตัวหนังสือเตือนบนการ์ด"),
    ("crit", "surface", 4.5, "ตัวหนังสือวิกฤตบนการ์ด"),
    ("crit-on", "crit-fill", 4.5, "การ์ดที่ล่มบนจอทีวี (สีทึบ)"),
    ("warn-on", "warn-fill", 4.5, "การ์ดที่ติดขัดบนจอทีวี (สีทึบ)"),
    ("ref-ink", "surface", 4.5, "ป้ายเส้นเป้าในกราฟ"),
    ("ic-ink", "ic-bg", 3.0, "ไอคอนในวงกลมของการ์ด KPI", "mid"),
    ("bar", "surface", 3.0, "แท่งกราฟบนการ์ด"),
]
NAMED = {"white": (255, 255, 255), "black": (0, 0, 0)}


def block(text, head):
    i = text.find(head)
    if i < 0:
        return None
    j = text.index("{", i) + 1
    return dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", text[j:text.index("}", j)]))


def parse(text):
    light = block(text, ":root {") or block(text, ":root{")
    if light is None:
        raise SystemExit("ไม่พบบล็อก ':root {'")
    media = block(text, ':root:not([data-theme="light"]) {')
    forced = block(text, ':root[data-theme="dark"] {')
    return light, media, forced


def colors(val, env, seen=()):
    """คืนรายการสี (r, g, b, a) ของค่า token — gradient ได้หลายสี, ค่าที่ไม่ใช่สีคืน []"""
    val = val.strip()
    m = re.fullmatch(r"var\(--([\w-]+)\s*(?:,\s*(.+))?\)", val)
    if m:
        name = m.group(1)
        if name in env and name not in seen:
            return colors(env[name], env, seen + (name,))
        return colors(m.group(2), env, seen) if m.group(2) else []
    out = []
    for h in re.findall(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", val):
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        out.append((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16) / 255 if len(h) == 8 else 1.0))
    for args in re.findall(r"rgba?\(([^)]+)\)", val):
        p = [x for x in re.split(r"[\s,/]+", args.strip()) if x]
        a = float(p[3].rstrip("%")) / (100 if p[3].endswith("%") else 1) if len(p) > 3 else 1.0
        out.append((float(p[0]), float(p[1]), float(p[2]), a))
    for w in re.findall(r"\b(white|black)\b", val):
        out.append(NAMED[w] + (1.0,))
    if val == "transparent":
        out.append((0, 0, 0, 0.0))
    return out


def over(c, base):
    r, g, b, a = c
    return (r * a + base[0] * (1 - a), g * a + base[1] * (1 - a), b * a + base[2] * (1 - a))


def lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check(env):
    """คืน [(fg, bg, min, ใช้ทำอะไร, ค่าต่ำสุดที่วัดได้ | None)]"""
    page = over(colors(env.get("page", "#fff"), env)[0], (255, 255, 255))
    surface = over((colors(env.get("surface", "#fff"), env) or [(255, 255, 255, 1)])[0], page)
    res = []
    for fg, bg, need, what, *where in PAIRS:
        if fg not in env or bg not in env:
            res.append((fg, bg, need, what, None))
            continue
        bgs = [over(c, surface) for c in colors(env[bg], env)]
        if bgs and where == ["end"]:
            bgs = bgs[-2:]
        elif bgs and where == ["mid"]:
            bgs = [tuple((x + y) / 2 for x, y in zip(bgs[0], bgs[-1]))]
        fgs = colors(env[fg], env)
        if not bgs or not fgs:
            res.append((fg, bg, need, what, None))
            continue
        res.append((fg, bg, need, what, min(ratio(over(f, b), b) for f in fgs for b in bgs)))
    return res


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    text = Path(argv[0]).read_text(encoding="utf-8")
    show_all = "--all" in argv
    light, media, forced = parse(text)
    bad = 0
    if media is not None and forced is not None and media != forced:
        diff = sorted(k for k in set(media) | set(forced) if media.get(k) != forced.get(k))
        print("ไม่ผ่าน  ชุดมืดสองชุด (media กับ [data-theme=dark]) ไม่ตรงกัน:", ", ".join("--" + k for k in diff))
        bad += 1
    modes = [("สว่าง", light)] + ([("มืด", {**light, **(forced or media)})] if (forced or media) else [])
    for mode, env in modes:
        for fg, bg, need, what, r in check(env):
            if r is None:
                if show_all:
                    print(f"ข้าม    [{mode}] --{fg} บน --{bg} (ไม่มี token)")
                continue
            ok = r >= need
            bad += not ok
            if show_all or not ok:
                print(f"{'ผ่าน ' if ok else 'ไม่ผ่าน'} [{mode}] --{fg} บน --{bg}: {r:.2f} (ต้อง ≥ {need}) · {what}")
    print("ผ่านทุกคู่" if not bad else f"ไม่ผ่าน {bad} รายการ — แก้ token แล้วรันใหม่")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
