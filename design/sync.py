"""ฝัง design/ui.css ลงในไฟล์ dashboard แบบไฟล์เดียว (ระหว่างเครื่องหมาย ui.css) ให้ทุกหน้ามีหน้าตาจากแหล่งเดียว

    python3 design/sync.py                       # อัปเดต template/dashboard.html ของสกิล
    python3 design/sync.py --check               # ตรวจอย่างเดียว (exit 1 ถ้าไม่ตรง) — เทสต์ของสกิลเรียกตัวนี้
    python3 design/sync.py <project>/web/dashboard.html   # พอร์ตหน้าตาใหม่ไปโปรเจกต์ที่สร้างจากแม่แบบ
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "template" / "dashboard.html"
START = "  /* ===== ui.css: สร้างจาก design/ui.css ด้วย design/sync.py — อย่าแก้ส่วนนี้ในไฟล์นี้ ===== */\n"
END = "  /* ===== /ui.css ===== */\n"


def block() -> str:
    css = (HERE / "ui.css").read_text(encoding="utf-8")
    return START + "".join(("  " + l) if l.strip() else l for l in css.splitlines(True)) + END


def synced(text: str) -> str:
    i = text.index(START)
    j = text.index(END, i) + len(END)
    return text[:i] + block() + text[j:]


def main(argv):
    check = "--check" in argv
    targets = [Path(a) for a in argv if not a.startswith("--")] or [TEMPLATE]
    bad = []
    for t in targets:
        text = t.read_text(encoding="utf-8")
        new = synced(text)
        if check:
            if new != text:
                bad.append(t)
        elif new != text:
            t.write_text(new, encoding="utf-8")
            print("synced", t)
    if bad:
        print("ui.css ไม่ตรงกับ:", *bad, "— รัน python3 design/sync.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
