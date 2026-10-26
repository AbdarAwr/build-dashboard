# ที่รันและหลังบ้าน

หน้าเป็นไฟล์ HTML แบบ static ที่โหลดข้อมูล (`data.url` ของ ENGINE หรือ `PAGE.source` ของหน้าออกแบบเอง) จาก origin เดียวกัน ส่วนที่ต้องตัดสินใจมีสามอย่าง: ใครเสิร์ฟหน้า ใครเสิร์ฟข้อมูล และมี login ไหม

| ที่รัน | `AUTH` | ไฟล์ที่ก็อป | สิ่งที่หลังบ้านต้องมี |
|---|---|---|---|
| **VPS ของทีม หลัง nginx login** (บอทลูกค้าหรือเครื่องมือของทีม) | `1` | dashboard + login (+ logs ถ้ามี route `logs`) + assets | login gate ของทีม (auth service + nginx `auth_request`) ใช้ได้กับข้อมูลทุกชนิด สัญญาของหน้า login อยู่ใน `chatbot-data.md` ส่วน "หลังบ้าน" (วิธีติดตั้งของทีมดู `local/team-notes.md`) แล้วเพิ่ม endpoint ข้อมูลของงานนี้ (เช่น `/api/tickets.csv`) เข้าไปในรายการ `auth_request` |
| **ฝังในแอปเดิม** (FastAPI / Flask / Express ที่มีระบบสิทธิ์อยู่แล้ว) | `0` (แอปกันสิทธิ์เอง) หรือ `1` ถ้าแอปใช้ cookie + `/login/` แบบเดียวกัน | dashboard + assets | route หน้า, `/assets/*` และ endpoint ข้อมูล |
| **ในเครื่องคนเดียว** (เครื่องมือภายใน) | `0` | dashboard + assets | เซิร์ฟเวอร์เล็ก ๆ ผูก `127.0.0.1` เท่านั้น (Python `http.server` ก็พอ) |
| **จอทีวีบน VPS ของทีม** (ไม่มีใครพิมพ์รหัสได้) | – (หน้าออกแบบเอง `data-shell="wall"`) | index.html + ui.css + ui.js + assets | ไม่มี login จึงต้องกันด้วย nginx `allow <IP ออฟฟิศ>; deny all;` ทั้งที่ path ของหน้าและ endpoint ข้อมูล (หรือ cookie ประจำเครื่องที่อายุยาว) · ต้องเป็น HTTPS ไม่งั้นกันจอดับ (Wake Lock) ไม่ทำงาน · ถาม user ว่าจะใช้ IP ไหน |

`AUTH = 0` ทำให้หน้าไม่มีเมนูออกจากระบบ และเมื่อโหลดไม่ได้จะแสดงปุ่ม "ลองใหม่" แทน "เข้าสู่ระบบ"
ถ้าหลังบ้านไม่มี `/login/` หรือ `/auth/logout` ให้ redirect สองเส้นนี้ไป `/dashboard/` เพื่อกันบุ๊กมาร์กหรือลิงก์เก่าพัง

## สัญญาของ endpoint ข้อมูล
- อยู่ origin เดียวกับหน้า (หน้าใช้ `credentials: 'same-origin'`) ถ้าอยู่หลัง login ต้องให้ผ่านด่านเดียวกัน
- CSV มีหัวคอลัมน์ (engine แปลงหัวคอลัมน์เป็นตัวพิมพ์เล็ก) หรือ JSON (array หรือ `{ rows | data | logs: [...] }`)
- เวลาเป็น ISO ที่มีโซน (`+07:00` หรือ `Z`) ถ้าไม่มีโซน engine ถือเป็นเวลาไทย
- ถ้าต้องตัดจำนวนแถว ให้ตัด**จากใหม่สุด** (เรียงใหม่ไปเก่าแล้ว LIMIT แล้วค่อยกลับลำดับ) ถ้าใช้ `ORDER BY ts ASC LIMIT` แถวใหม่จะหาย
- ห้ามส่ง HTML แทนข้อมูลเมื่อ error (engine จะเข้าใจว่าเซสชันหมดอายุ) ให้ตอบเป็น status code ที่ถูกต้อง
- **หน้าที่รีเฟรชเอง** (สถานะสด, จอทีวี): บอกเวลาที่หลังบ้านสร้างข้อมูลชุดนี้ (ไม่ใช่เวลาที่ตอบ request) ทางใดทางหนึ่ง
  - JSON: `{ "generated_at": "<ISO มีโซน>", ... }` · ข้อมูลที่เป็น array ล้วน ให้เสนอห่อเป็น `{ generated_at, items }`
  - ไฟล์ (CSV, JSON ที่ cron เขียน): header `X-Generated-At` หรือ `Last-Modified` (nginx ส่ง `Last-Modified` ของไฟล์ static ให้เอง)
  `UI.live` ใช้ค่านี้ตัดสินว่าข้อมูลค้าง ถ้าไม่มี จะจับไม่ได้ว่างานหลังบ้านหยุดแต่ยังส่งชุดเดิมอยู่ แล้วจอจะค้างที่ "ปกติ"
- หน้าทาง 2 ที่อยู่หลัง login ของทีม ใช้ `template/login.html` ได้เลย (ใส่ token และข้อความตาม `branding.md` รวมจุด `[แก้]` ที่บอกว่าหน้านี้สำหรับใคร) และ `UI.getJSON`/`UI.getCSV` จะแจ้ง "ได้หน้าเว็บแทนข้อมูล" เมื่อเซสชันหมดอายุ

## เซิร์ฟเวอร์ในเครื่อง (ไม่มี login) ต้องมี
- ผูก `127.0.0.1` เท่านั้น และปฏิเสธ request ที่ header `Host` ไม่ใช่ `127.0.0.1:<port>` หรือ `localhost:<port>` (กัน DNS rebinding ไม่ให้เว็บอื่นอ่านข้อมูล)
- route: `/dashboard/` → dashboard.html, `/assets/*` → assets (กัน path traversal), endpoint ข้อมูล, และ `/login/` กับ `/auth/logout` → redirect
- เทสต์ route ของเซิร์ฟเวอร์ตัวจริงด้วย (เปิดเซิร์ฟเวอร์ใน thread แล้วยิง request ตรวจ status, redirect และ Host ที่ไม่อนุญาต) เพราะเทสต์ Playwright ใช้ `stub_server.py` (`auth=False`) ไม่ใช่เซิร์ฟเวอร์จริง
