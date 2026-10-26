"""Synthetic data for the dashboard tests (LOCAL ONLY — never real customer data).

chat_rows()  : chatbot log CSV shape (preset 'chatbot', see reference/chatbot-data.md)
order_rows() : orders CSV (preset 'generic' example)

For a project: copy this file, keep the shape of the project's real export (columns, markers, time format) but
make the values up. Expected numbers in test_template.py are recomputed from these rows, never hard-coded.
"""
import csv
import io
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

BKK = timezone(timedelta(hours=7))
FIXTURE_NOW = datetime(2026, 10, 14, 15, 0, tzinfo=BKK)

CHAT_COLUMNS = ["timestamp", "execution_id", "session", "question", "answer", "sources", "images",
                "images_data", "sources_data", "email"]
ORDER_COLUMNS = ["timestamp", "order_id", "customer", "channel", "product", "qty", "amount", "status", "paid_at"]

# (question, keyword labels the template's example whitelist must count for it)
PRICE, CONTACT, BRANCH, JOBS, IR = "ราคา / ค่าบริการ", "ติดต่อ / ช่องทาง", "สาขา / เวลาทำการ", "สมัครงาน", "นักลงทุนสัมพันธ์"
QUESTIONS = [
    ("ค่าบริการรายเดือนเท่าไหร่", {PRICE}),
    ("What is the price of the premium plan?", {PRICE}),
    ("ขอเบอร์โทรติดต่อฝ่ายขาย", {CONTACT}),
    ("สาขาสีลมเปิดกี่โมง", {BRANCH}),
    ("มีตำแหน่งงานว่างไหม อยากสมัครงาน", {JOBS}),          # สมัครงาน ≠ สมัคร / ลงทะเบียน (คำยาวกินก่อน)
    ("ปันผลปีนี้จ่ายเท่าไหร่", {IR}),
    ("สวัสดีครับ ขอที่อยู่สำนักงานใหญ่", {CONTACT}),         # สวัสดี = กินทิ้ง ไม่ใช่หัวข้อ
    ("promotion this month?", {PRICE}),
    ("อยากรู้เรื่องสินค้าใหม่", set()),
]
GATES = [("สวัสดีครับ", "GREETING", "สวัสดีครับ ยินดีให้ข้อมูลครับ"),
         ("ขอบคุณครับ", "THANKS", "ยินดีครับ"),
         ("ราคาทองวันนี้", "OFFTOPIC", "ขออภัยครับ ผมตอบได้เฉพาะเรื่องของบริษัท"),
         ("asdfgh", "GARBLED", "ขออภัยครับ ผมไม่เข้าใจข้อความ")]


def _ts(dt):
    return dt.astimezone(BKK).strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}+07:00"


def chat_rows(seed=7):
    rnd = random.Random(seed)
    rows, eid = [], 1000
    start = FIXTURE_NOW - timedelta(days=74)
    sessions = []
    for i in range(60):
        sid = str(uuid.UUID(int=rnd.getrandbits(128), version=4))
        t0 = start + timedelta(days=rnd.randint(0, 74), hours=rnd.randint(0, 9), minutes=rnd.randint(0, 59))
        if t0 > FIXTURE_NOW - timedelta(minutes=30):
            t0 = FIXTURE_NOW - timedelta(hours=rnd.randint(1, 5))
        sessions.append((sid, t0, f"user{i:02d}@example.com" if i % 4 == 0 else ""))
    # 00:30 Bangkok today = previous day in Los Angeles → catches pages that use the browser's zone
    sessions.append((str(uuid.UUID(int=rnd.getrandbits(128), version=4)), FIXTURE_NOW.replace(hour=0, minute=30), ""))
    for sid, t0, email in sessions:
        for k in range(rnd.randint(1, 6)):
            eid += 1
            t = t0 + timedelta(minutes=3 * k, seconds=rnd.randint(0, 50))
            r = {"timestamp": _ts(t), "execution_id": str(eid), "session": sid, "email": email,
                 "images": "0", "images_data": "[]", "sources_data": "[]", "sources": ""}
            kind = rnd.choices(["src", "img", "sales", "gate", "other", "empty"], [45, 20, 8, 15, 7, 3])[0]
            if k == 5:
                kind = "capped"   # per-visitor cap reached → widget hands over (GATE_CAPPED)
            if kind == "gate":
                q, g, a = rnd.choice(GATES)
                r.update(question=q, answer=a, sources_data=json.dumps([{"label": f"GATE_{g}", "url": None, "kind": "gate"}]))
            elif kind == "capped":
                q, _ = rnd.choice(QUESTIONS)
                r.update(question=q, answer="ทีมงานยินดีดูแลต่อโดยตรงครับ",
                         sources_data=json.dumps([{"label": "GATE_CAPPED", "url": None, "kind": "gate"}]))
            else:
                q, _ = rnd.choice(QUESTIONS)
                a = f"**{q}** — คำตอบทดสอบ\n- ข้อ 1\n- ข้อ 2"
                sd = [{"label": "Company FAQ", "url": "https://www.example.com/faq", "kind": "page"}]
                src = ["ref FAQ.txt p.1"]
                if kind == "img":
                    r["images_data"] = json.dumps([{"url": f"https://chatbot.example.com/crops/p{rnd.randint(1, 9)}.png", "ref": "FAQ p.1", "doc_url": None}])
                    r["images"] = "1"
                if kind == "sales":
                    sd.append({"label": "SALES_CARD", "url": None, "kind": "sales"})
                if kind == "other":
                    sd, src = [], []
                if kind == "empty":
                    sd, src = [{"label": "EMPTY_LLM_RESPONSE", "url": None, "kind": "error"}], []
                r.update(question=q, answer=a, sources="; ".join(src), sources_data=json.dumps(sd, ensure_ascii=False))
            rows.append(r)
    rows.sort(key=lambda r: r["timestamp"])
    # old-style row: picture as markdown in the answer on an old domain
    real = [r for r in rows if "GATE_" not in r["sources_data"]]
    real[8].update(answer=real[8]["answer"] + "\n\n![FAQ](https://old.example.com/crops/p1.png)", images="1", images_data="[]")
    # formula-looking question → export must neutralise it
    real[3].update(question="=HYPERLINK(\"http://evil.example\",\"x\")")
    # test / eval sessions the dashboard must ignore everywhere
    for n, sid in enumerate(["web_default", "eval-01", "qa-run-xyz"]):
        for k in range(4):
            rows.append({"timestamp": _ts(FIXTURE_NOW - timedelta(days=n, hours=k + 1)), "execution_id": str(9000 + n * 10 + k),
                         "session": sid, "question": "ค่าบริการ test", "answer": "test", "sources": "ref x p.1", "images": "0",
                         "images_data": "[]", "sources_data": "[]", "email": ""})
    rows.sort(key=lambda r: r["timestamp"])
    return rows


PRODUCTS = [("กาแฟคั่ว 250 กรัม", 290), ("ชาเขียว 100 กรัม", 180), ("แก้วเซรามิก", 350), ("ดริปเปอร์", 690), ("เมล็ดกาแฟ 1 กก.", 950)]
CHANNELS = ["เว็บไซต์", "LINE", "หน้าร้าน"]


def order_rows(seed=11):
    rnd = random.Random(seed)
    rows = []
    start = FIXTURE_NOW - timedelta(days=200)
    for i in range(420):
        t = start + timedelta(minutes=rnd.randint(0, 200 * 24 * 60))
        if t > FIXTURE_NOW:
            t = FIXTURE_NOW - timedelta(minutes=rnd.randint(5, 600))
        name, price = rnd.choice(PRODUCTS)
        qty = rnd.randint(1, 4)
        status = rnd.choices(["paid", "pending", "cancelled"], [80, 12, 8])[0]
        # paid_at = เวลาที่สอง (ชำระจริง ช้ากว่าสั่ง 0–5 วัน) ใช้ทดสอบกราฟที่นับตามเวลาอื่น (trend.metrics[].at)
        paid = t + timedelta(hours=rnd.randint(0, 120)) if status == "paid" else None
        rows.append({"timestamp": _ts(t), "order_id": f"SO-{10000 + i}", "customer": f"ลูกค้า {rnd.randint(1, 90):02d}",
                     "channel": rnd.choice(CHANNELS), "product": name, "qty": str(qty), "amount": str(price * qty), "status": status,
                     "paid_at": _ts(min(paid, FIXTURE_NOW)) if paid else ""})
    # big order to exercise compact axis labels and the monthly goal
    rows.append({"timestamp": _ts(FIXTURE_NOW - timedelta(hours=2)), "order_id": "SO-99999", "customer": "ลูกค้าองค์กร",
                 "channel": "หน้าร้าน", "product": "เมล็ดกาแฟ 1 กก.", "qty": "480", "amount": "456000", "status": "paid",
                 "paid_at": _ts(FIXTURE_NOW - timedelta(hours=1))})
    # Excel-style time with no zone = Bangkok → 00:10 today in Bangkok, still yesterday in Los Angeles
    rows.append({"timestamp": FIXTURE_NOW.strftime("%Y-%m-%d") + " 00:10", "order_id": "SO-99997", "customer": "ลูกค้า 02",
                 "channel": "เว็บไซต์", "product": "ชาเขียว 100 กรัม", "qty": "2", "amount": "360", "status": "paid",
                 "paid_at": FIXTURE_NOW.strftime("%Y-%m-%d") + " 00:20"})
    # 00:30 Bangkok today
    rows.append({"timestamp": _ts(FIXTURE_NOW.replace(hour=0, minute=30)), "order_id": "SO-99998", "customer": "ลูกค้า 01",
                 "channel": "LINE", "product": "ดริปเปอร์", "qty": "1", "amount": "690", "status": "paid",
                 "paid_at": _ts(FIXTURE_NOW.replace(hour=0, minute=40))})
    rows.sort(key=lambda r: r["timestamp"])
    return rows


def to_csv(rows, columns):
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(columns)
    for r in rows:
        w.writerow([r.get(c, "") for c in columns])
    return buf.getvalue()


if __name__ == "__main__":
    print(len(chat_rows()), "chat rows ·", len(order_rows()), "orders")
