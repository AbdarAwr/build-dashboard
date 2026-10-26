/* =====================================================================================================
   ui.js — ตัวช่วยของหน้าออกแบบเอง (ทางที่ 2 ของสกิล build-dashboard) ใช้คู่กับ design/ui.css
   ทุกอย่างอยู่ใต้ window.UI · ค่าที่มาจากข้อมูลต้องผ่าน UI.esc() ก่อนใส่ใน HTML เสมอ (ฟังก์ชันสร้าง HTML ที่นี่ esc ให้แล้ว)
   เวลา: แสดงเป็นเวลาไทย (Asia/Bangkok) และปี พ.ศ. ไม่ขึ้นกับโซนเวลาของเครื่องที่เปิด
   ===================================================================================================== */
(function () {
  "use strict";
  const ICONS = {
    activity: '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    arrowUp: '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    arrowDown: '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    bot: '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
    box: '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    chart: '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    cpu: '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/>',
    gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    grid: '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    list: '<path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M8 6h13"/>',
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    minus: '<circle cx="12" cy="12" r="10"/><path d="M8 12h8"/>',
    money: '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    right: '<path d="m9 18 6-6-6-6"/>',
    server: '<rect width="20" height="8" x="2" y="2" rx="2"/><rect width="20" height="8" x="2" y="14" rx="2"/><path d="M6 6h.01"/><path d="M6 18h.01"/>',
    store: '<path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M2 7h20"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    workflow: '<rect width="8" height="8" x="3" y="3" rx="2"/><path d="M7 11v4a2 2 0 0 0 2 2h4"/><rect width="8" height="8" x="13" y="13" rx="2"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    xcircle: '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
  };
  const icon = (name, cls = "") => `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ICONS.minus}</svg>`;
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------- ตัวเลขและเวลา (ไทย) ---------- */
  const nf = new Intl.NumberFormat("th-TH");
  const fmtN = n => (n == null || isNaN(n) ? "–" : nf.format(Math.round(n * 100) / 100));
  const fmtCompact = n => (n == null || isNaN(n) ? "–" : Math.abs(n) >= 10000
    ? new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n) : fmtN(n));
  // ตัวเลขเงินแบบที่คนไทยอ่าน: 3,184,000 → "3.18 ล้าน" · ต่ำกว่าล้านแสดงเต็มเป็นบาท (950,000)
  //   fmtMillion(n, { digits: 2, always: true }) — ในรายการเดียวกันใช้ digits เท่ากันทุกแถว · always = ต่ำกว่าล้านก็เป็นล้าน (0.40 ล้าน)
  const fmtMillion = (n, o = {}) => (n == null || isNaN(n) ? "–" : Math.abs(n) >= 1e6 || o.always
    ? `${(n / 1e6).toLocaleString("en-US", { minimumFractionDigits: o.digits ?? 2, maximumFractionDigits: o.digits ?? 2 })} ล้าน` : fmtN(Math.round(n)));
  const fmtPct = (n, d = 1) => (n == null || isNaN(n) ? "–" : `${n.toFixed(d)}%`);
  const BKK = { timeZone: "Asia/Bangkok" };
  const dayF = new Intl.DateTimeFormat("th-TH", { ...BKK, day: "numeric", month: "short", year: "numeric" });
  const tsF = new Intl.DateTimeFormat("th-TH", { ...BKK, day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const timeF = new Intl.DateTimeFormat("th-TH", { ...BKK, hour: "2-digit", minute: "2-digit" });
  const toDate = v => { if (v == null || v === "") return null; const d = v instanceof Date ? v : new Date(v); return isNaN(d) ? null : d; };   // null ≠ 1 ม.ค. 1970
  const fmtDay = v => { const d = toDate(v); return d ? dayF.format(d) : "–"; };
  const fmtTs = v => { const d = toDate(v); return d ? tsF.format(d) : "–"; };
  const fmtTime = v => { const d = toDate(v); return d ? timeF.format(d) : "–"; };
  // วันไทยของเวลาใด ๆ เป็น 'YYYY-MM-DD' (ใช้จัดกลุ่มรายวันโดยไม่ขึ้นกับโซนของเครื่อง)
  const dayKey = v => { const d = toDate(v); return d ? new Date(d.getTime() + 7 * 3600e3).toISOString().slice(0, 10) : null; };
  function rel(v) {
    const d = toDate(v);
    if (!d) return "–";
    const s = (Date.now() - d) / 1000;
    if (s < 45) return "เมื่อสักครู่";
    if (s < 3600) return `${Math.round(s / 60)} นาทีที่แล้ว`;
    if (s < 86400) return `${Math.floor(s / 3600)} ชม.ที่แล้ว`;
    return fmtTs(d);
  }
  function dur(sec) {
    if (sec == null || isNaN(sec)) return "–";
    if (sec < 60) return `${Math.round(sec)} วิ`;
    if (sec < 3600) return `${Math.round(sec / 60)} นาที`;
    return `${Math.floor(sec / 3600)} ชม. ${Math.round((sec % 3600) / 60)} นาที`;
  }

  /* ---------- อัปเดต DOM ---------- */
  // ใส่ HTML เฉพาะเมื่อเปลี่ยน และคืนโฟกัสให้ element ที่มี data-key เดิม (หน้าที่รีเฟรชเองจะไม่ทำให้คีย์บอร์ดหลุด)
  function patch(el, html) {
    if (typeof el === "string") el = document.querySelector(el);
    if (!el || el._ui === html) return false;
    const a = document.activeElement, key = el.contains(a) ? a.dataset.key : null;
    el.innerHTML = html; el._ui = html;
    if (key) { const f = el.querySelector(`[data-key="${CSS.escape(key)}"]`); if (f) f.focus({ preventScroll: true }); }
    return true;
  }
  // โหลดข้อมูล: ได้หน้า HTML (เช่น หน้า login ตอนเซสชันหมดอายุ) = error ไม่ใช่ข้อมูล
  //   เวลาของข้อมูลจาก header X-Generated-At หรือ Last-Modified ติดไปกับผลลัพธ์ (UI.dataTime อ่านได้) สำหรับข้อมูลที่ไม่มี generated_at เช่น CSV
  async function fetchData(url) {
    const r = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    if (/text\/html/i.test(r.headers.get("content-type") || "")) throw new Error("ได้หน้าเว็บแทนข้อมูล — เซสชันหมดอายุหรือ URL ผิด");
    return r;
  }
  const withTime = (data, r) => {
    const t = r.headers.get("x-generated-at") || r.headers.get("last-modified");
    if (t && data && typeof data === "object") Object.defineProperty(data, "_at", { value: t, enumerable: false });
    return data;
  };
  async function getJSON(url) { const r = await fetchData(url); return withTime(await r.json(), r); }
  // เวลาของข้อมูล: generated_at ในตัวข้อมูลก่อน แล้วค่อย header (ใช้เป็นค่าเริ่มต้นของ live().at)
  const dataTime = d => (d && (d.generated_at || d._at)) || null;
  // รีเฟรชเป็นรอบ ข้ามรอบที่แท็บถูกซ่อน และรีเฟรชทันทีเมื่อกลับมา (ไม่มีรอบซ้อนกัน) · คืนฟังก์ชันสำหรับสั่งรีเฟรชเอง
  function every(sec, fn) {
    let t = null, busy = false;
    const tick = async () => {
      clearTimeout(t);
      if (busy) return;
      if (!document.hidden) { busy = true; try { await fn(); } finally { busy = false; } }
      t = setTimeout(tick, sec * 1000);
    };
    document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
    tick();
    return tick;
  }

  // live({ load, render, every, staleSec, at }) — โหลด → วาด → บอกความสดของข้อมูล (ใช้กับทุกหน้าที่รีเฟรชเอง)
  //   load() คืนข้อมูล (เช่น () => UI.getJSON('/api/x')) · render(data, { stale, at }) วาดทั้งหน้า
  //   at(data) = เวลาของข้อมูลจากหลังบ้าน เช่น d => d.generated_at (ไม่มี = เวลาที่โหลดสำเร็จ — หลังบ้านค้างแต่ส่งชุดเดิมจะจับไม่ได้)
  //   เก่ากว่า staleSec (ค่าเริ่มต้น 3 รอบ ไม่ต่ำกว่า 3 นาที): body.stale ทำให้ตัวเลขจางเป็นเทา + แถบแดงบอกเวลาของข้อมูล
  //   และ render ได้ stale = true → ให้ซ่อนคำสรุปอย่าง "ปกติทุกระบบ" ไม่ให้จอค้างบอกว่าปกติ
  //   ใช้ #pulse, #updated, #alert, #srStatus ของโครงหน้า (ไม่มีตัวไหนก็ข้าม)
  function live(o) {
    const sec = o.every || 0, staleSec = o.staleSec || Math.max(3 * sec, 180);
    const $ = id => document.getElementById(id);
    let data = null, at = null, wasStale = false, said = "";
    async function tick() {
      let err = null;
      try { data = await o.load(); at = toDate((o.at || dataTime)(data)) || new Date(); } catch (e) { err = e; }
      const age = at ? (Date.now() - at) / 1000 : 0, stale = !!at && age > staleSec;
      if (data && (!err || stale !== wasStale)) o.render(data, { stale, at });
      wasStale = stale;
      document.body.classList.toggle("stale", stale);
      if ($("pulse")) $("pulse").className = "pulse " + (err || stale ? "err" : "on");
      if ($("updated")) $("updated").textContent = at ? fmtTime(at) + " น." : err ? "โหลดไม่ได้" : "กำลังโหลด…";
      const why = err ? `ดึงข้อมูลไม่ได้: ${err.message}` : "หลังบ้านยังส่งข้อมูลชุดเดิม";
      const msg = !at && err ? ["crit", `โหลดข้อมูลไม่ได้ (${err.message})${sec ? ` · ลองใหม่ทุก ${dur(sec)}` : ""}`]
        : stale ? ["crit", `ข้อมูลไม่อัปเดตมา ${dur(age)} · ตัวเลขด้านล่างเป็นของเวลา ${fmtTime(at)} น. (${why})`]
        : err ? ["warn", `ดึงข้อมูลรอบล่าสุดไม่สำเร็จ (${err.message}) · กำลังลองใหม่`] : null;
      if ($("alert")) patch($("alert"), msg ? `<div class="notice ${msg[0]}" role="alert">${icon("alert")}<span>${esc(msg[1])}</span></div>` : "");
      const say = msg ? msg[1] : said ? "ข้อมูลกลับมาเป็นปัจจุบันแล้ว" : "";   // อ่านออกเสียงเฉพาะตอนสถานะเปลี่ยน
      if ($("srStatus") && say && say !== said) $("srStatus").textContent = say;
      said = msg ? say : "";
    }
    return { refresh: sec ? every(sec, tick) : (tick(), tick) };
  }

  /* ---------- ชิ้นส่วน (คืน HTML) ---------- */
  const TONE_ICON = { ok: "check", warn: "alert", crit: "xcircle" };
  const pill = (tone, text, ic) => `<span class="pill ${esc(tone || "")}">${tone === "busy" ? '<span class="dot"></span>' : icon(ic || TONE_ICON[tone] || "minus")}${esc(text)}</span>`;
  // tile: { icon, label, value(ตัวเลข|ข้อความ), hint, tone: ''|'warn'|'crit', status: { tone, text } }
  function tile(k) {
    const v = typeof k.value === "number" ? fmtN(k.value) : esc(k.value == null ? "–" : k.value);
    const st = k.status ? `<span class="status ${esc(k.status.tone || "neutral")}">${icon(TONE_ICON[k.status.tone] || "minus")}${esc(k.status.text)}</span>` : "";
    return `<div class="card tile"><span class="ic">${icon(k.icon || "chart")}</span><div class="tb">
      <div class="label">${esc(k.label)}</div><div class="value">${v}${st}</div>${k.hint ? `<div class="hint">${esc(k.hint)}</div>` : ""}</div></div>`;
  }
  // meter: { label, pct, text, mode: 'limit' (ค่าเริ่มต้น) | 'target', warnAt: 80, critAt: 100, mark, markLabel } — สี + คำ ไม่พึ่งสีอย่างเดียว
  //   limit = เพดาน/ความจุ (ดิสก์, โควตา): ใกล้เต็มเป็นส้ม เต็มเป็นแดง · target = เป้าหมาย (ยอดขาย): ไม่มีสีเตือน ถึงเป้าแล้วขึ้นคำว่า "ถึงเป้า"
  //   mark = ขีดบอกว่า "ควรอยู่ตรงไหนตอนนี้" (เช่น % ของเดือนที่ผ่านไป) — เป้า 42% ตอนเดือนผ่านไป 44% อ่านออกว่าช้ากว่าแผนนิดเดียว
  function meter(m) {
    const raw = m.pct || 0, p = Math.max(0, Math.min(100, raw)), warnAt = m.warnAt ?? 80, critAt = m.critAt ?? 100, target = m.mode === "target";
    const tone = target ? "" : p >= critAt ? "crit" : p >= warnAt ? "warn" : "";
    const word = target ? (raw >= 100 ? " · ถึงเป้า" : "") : tone === "crit" ? " · เต็ม" : tone === "warn" ? " · ใกล้เต็ม" : "";
    const mk = m.mark == null ? null : Math.max(0, Math.min(100, m.mark));
    return `<div class="meter ${tone}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(p)}" aria-label="${esc(m.label)} ${Math.round(p)}%">
      <div class="m-row"><span>${esc(m.label)}</span><b>${Math.round(target ? raw : p)}%${word}</b></div>
      <div class="m-bar"><div class="m-track"><span class="m-fill" style="width:${p}%"></span></div>${mk == null ? "" : `<i class="m-mark" style="left:${mk}%"></i>`}</div>
      ${mk == null ? "" : `<div class="m-note">${esc(m.markLabel || "ควรถึง")} ${Math.round(mk)}%</div>`}${m.text ? `<div class="m-note">${esc(m.text)}</div>` : ""}</div>`;
  }
  // statCard: { name, icon, state: 'ok'|'warn'|'crit', stateText, nums: [[label, value]], meter, foot }
  function statCard(c) {
    return `<article class="statcard ${c.state === "ok" ? "" : esc(c.state || "")}">
      <div class="sc-head">${c.icon ? icon(c.icon) : ""}<span class="sc-name">${esc(c.name)}</span>${pill(c.state, c.stateText || c.state)}</div>
      ${c.nums && c.nums.length ? `<div class="sc-nums">${c.nums.map(([l, v]) => `<div class="sc-num"><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join("")}</div>` : ""}
      ${c.meter ? meter(c.meter) : ""}${c.foot ? `<div class="sc-foot">${esc(c.foot)}</div>` : ""}</article>`;
  }
  // delta(ค่าปัจจุบัน, ค่าก่อนหน้า, { goodWhen: 'up'|'down', label }) → ป้าย ▲ +12.3% (สีตามว่าดีหรือแย่ ไม่ใช่ตามทิศ)
  function delta(cur, prev, o = {}) {
    if (!prev) return `<span class="delta flat">${esc(o.label || "ไม่มีค่าเทียบ")}</span>`;
    const p = (cur - prev) / Math.abs(prev) * 100, up = p >= 0.05, down = p <= -0.05;
    const good = o.goodWhen === "down" ? down : up;
    const cls = !up && !down ? "flat" : good ? "up" : "down";
    return `<span class="delta ${cls}">${up ? icon("arrowUp") : down ? icon("arrowDown") : ""}${p > 0 ? "+" : ""}${p.toFixed(1)}%${o.label ? ` ${esc(o.label)}` : ""}</span>`;
  }
  // rankList(items, fmt, empty) → รายการอันดับพร้อมแท่ง · item = [label, value] หรือ { label, value, prev, goodWhen }
  //   มี prev = แสดงการเปลี่ยนแปลง (UI.delta) ข้างตัวเลขในแถวเดียวกัน (ยอดขายสาขา + โตเท่าไรเทียบเดือนก่อน) · ค่าติดลบไม่มีแท่ง
  function rankList(items, fmt = fmtN, empty = "ยังไม่มีข้อมูล") {
    if (!items.length) return `<span class="sub">${esc(empty)}</span>`;
    const rows = items.map(x => Array.isArray(x) ? { label: x[0], value: x[1] } : x);
    const max = Math.max(1, ...rows.map(r => r.value));
    return `<ol class="rank">${rows.map((r, i) => `<li class="rrow" title="${esc(r.label)}"><span class="rk">${i + 1}</span><span class="rlab">${esc(r.label)}</span>
      <span class="rnum">${esc(fmt(r.value))}${r.prev != null ? " " + delta(r.value, r.prev, { goodWhen: r.goodWhen }) : ""}</span>
      <span class="rbarwrap"><span class="rbar" style="width:${Math.max(0, r.value) / max * 100}%"></span></span></li>`).join("")}</ol>`;
  }
  // sparkline(values) → SVG เส้น + พื้นจาง (ไม่มีแกน ใช้ประกอบตัวเลขใหญ่)
  function sparkline(values, h = 44) {
    if (!values.length) return "";
    const w = 200, max = Math.max(...values, 1), min = Math.min(...values, 0), span = max - min || 1;
    const pts = values.map((v, i) => [values.length < 2 ? w : i / (values.length - 1) * w, h - 3 - (v - min) / span * (h - 6)]);
    const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><path class="area" d="${line} L${w},${h} L0,${h} Z"/><path class="line" d="${line}"/></svg>`;
  }

  /* ---------- กราฟแท่ง (SVG) ---------- */
  // barChart(el, { points: [{ label, title, value, dim }], unit, fmt, axisFmt, ref: { value, label }, height, caption })
  //   dim = ช่วงที่ยังไม่จบ (สัปดาห์/เดือนปัจจุบัน) แท่งจางลง และให้บอกใน caption ว่าแท่งจางคือช่วงที่ยังไม่จบ
  // แท่ง ≤ 24px ปลายมน 4px ชิดฐาน · ชี้แล้วขึ้นค่า · มีตารางให้เปิดดู (ไม่พึ่งการชี้อย่างเดียว)
  let tipEl = null;
  function barChart(el, o) {
    if (typeof el === "string") el = document.querySelector(el);
    const pts = o.points || [], fmt = o.fmt || fmtN, unit = o.unit || "", h = o.height || 220;
    const w = Math.max(280, el.clientWidth || 600), pl = 48, pr = 8, pt = 16, pb = 28, iw = w - pl - pr, ih = h - pt - pb;
    const raw = Math.max(1, ...pts.map(p => p.value || 0), o.ref ? o.ref.value : 0);
    const step = Math.pow(10, Math.floor(Math.log10(raw)));
    const max = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].map(m => m * step).find(m => m >= raw);
    const slot = iw / Math.max(1, pts.length), bw = Math.max(2, Math.min(24, slot - 2)), y = v => pt + ih - v / max * ih;
    const every = Math.max(1, Math.ceil(pts.length / Math.max(2, Math.floor(iw / 64))));
    let s = `<svg viewBox="0 0 ${w} ${h}" height="${h}" role="img" aria-label="${esc(o.caption || "")}"><g class="gl axis">`;
    for (const f of [0, .5, 1]) { const yy = Math.round(y(max * f)) + .5; s += `<line x1="${pl}" x2="${w - pr}" y1="${yy}" y2="${yy}"/><text x="${pl - 8}" y="${yy + 4}" text-anchor="end">${esc((o.axisFmt || fmtCompact)(max * f))}</text>`; }
    s += `</g><g class="axis">`;
    pts.forEach((p, i) => { const last = i === pts.length - 1; if ((pts.length - 1 - i) % every === 0) s += `<text x="${last ? w - pr : pl + i * slot + slot / 2}" y="${h - 8}" text-anchor="${last ? "end" : "middle"}">${esc(p.label)}</text>`; });
    s += `</g><g>`;
    pts.forEach((p, i) => {
      const v = p.value || 0; if (v <= 0) return;
      const x0 = pl + i * slot + (slot - bw) / 2, x1 = x0 + bw, yt = y(v), yb = pt + ih, r = Math.min(4, bw / 2, yb - yt);
      s += `<path class="bar${p.dim ? " dim" : ""}" data-i="${i}" d="M${x0},${yb} L${x0},${yt + r} Q${x0},${yt} ${x0 + r},${yt} L${x1 - r},${yt} Q${x1},${yt} ${x1},${yt + r} L${x1},${yb} Z"/>`;
    });
    s += `</g>`;
    if (o.ref) { const yy = Math.round(y(o.ref.value)) + .5; s += `<line class="refl" x1="${pl}" x2="${w - pr}" y1="${yy}" y2="${yy}"/><text class="refl-t" x="${w - pr}" y="${yy - 5}" text-anchor="end">${esc(o.ref.label || fmt(o.ref.value))}</text>`; }
    s += `<g>${pts.map((p, i) => `<rect class="hit" data-i="${i}" x="${pl + i * slot}" y="${pt}" width="${slot}" height="${ih}"/>`).join("")}</g></svg>`;
    el.classList.add("uichart"); el._uiOpts = o; el._uiW = el.clientWidth; el._uiDraw = barChart;
    el.innerHTML = s + `<details class="tview"><summary>ดูเป็นตาราง</summary><div class="tvwrap"><table><thead><tr><th>ช่วง</th><th style="text-align:right">${esc(unit)}</th></tr></thead><tbody>${
      pts.map(p => `<tr><td>${esc(p.title || p.label)}</td><td style="text-align:right">${esc(fmt(p.value || 0))}</td></tr>`).join("")}</tbody></table></div></details>`;
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "uitip"; tipEl.hidden = true; document.body.appendChild(tipEl); }
    const svg = el.querySelector("svg");
    svg.addEventListener("mousemove", e => {
      const hit = e.target.closest(".hit"); if (!hit) return;
      const p = pts[+hit.dataset.i];
      tipEl.innerHTML = `${esc(p.title || p.label)}<br><b>${esc(fmt(p.value || 0))} ${esc(unit)}</b>`; tipEl.hidden = false;
      tipEl.style.left = Math.min(e.clientX + 14, innerWidth - tipEl.offsetWidth - 8) + "px"; tipEl.style.top = e.clientY + 14 + "px";
      svg.querySelectorAll(".bar.hover").forEach(b => b.classList.remove("hover"));
      const bar = svg.querySelector(`.bar[data-i="${hit.dataset.i}"]`); if (bar) bar.classList.add("hover");
    });
    svg.addEventListener("mouseleave", () => { tipEl.hidden = true; svg.querySelectorAll(".bar.hover").forEach(b => b.classList.remove("hover")); });
    redrawOnResize(el);
  }

  /* ---------- กราฟเส้น (SVG) ---------- */
  // lineChart(el, { labels, titles, series: [{ label, values, dashed }], unit, fmt, axisFmt, ref: { value, label }, area, height, caption })
  //   เส้นแรก = ค่าจริง (--s1) เส้นถัดไป = --s2, --s3 · dashed = เส้นเทียบ เช่น เป้าสะสม/เดือนก่อน (เส้นประสีเทา)
  //   ค่า null = ยังไม่มีข้อมูล (เส้นหยุด เช่น วันที่ยังมาไม่ถึง) · area = แรเงาใต้เส้นแรก (ยอดสะสม)
  //   ชี้แล้วขึ้นเส้นตั้ง + ค่าทุกเส้น · มีคำอธิบายเส้นเมื่อมีตั้งแต่ 2 เส้น · มีตาราง · ห้ามใส่สองหน่วยในกราฟเดียว
  function lineChart(el, o) {
    if (typeof el === "string") el = document.querySelector(el);
    const labels = o.labels || [], titles = o.titles || labels, ser = o.series || [], fmt = o.fmt || fmtN, unit = o.unit || "";
    const n = labels.length, h = o.height || 220, w = Math.max(280, el.clientWidth || 600), pl = 48, pr = 14, pt = 16, pb = 28;
    const iw = w - pl - pr, ih = h - pt - pb;
    const raw = Math.max(1, ...ser.flatMap(x => x.values.filter(v => v != null)), o.ref ? o.ref.value : 0);
    const step = Math.pow(10, Math.floor(Math.log10(raw)));
    const max = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].map(m => m * step).find(m => m >= raw);
    const X = i => pl + (n < 2 ? iw : i / (n - 1) * iw), Y = v => pt + ih - v / max * ih;
    const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(iw / 64))));
    let s = `<svg viewBox="0 0 ${w} ${h}" height="${h}" role="img" aria-label="${esc(o.caption || "")}"><g class="gl axis">`;
    for (const f of [0, .5, 1]) { const yy = Math.round(Y(max * f)) + .5; s += `<line x1="${pl}" x2="${w - pr}" y1="${yy}" y2="${yy}"/><text x="${pl - 8}" y="${yy + 4}" text-anchor="end">${esc((o.axisFmt || fmtCompact)(max * f))}</text>`; }
    s += `</g><g class="axis">`;
    labels.forEach((l, i) => { const last = i === n - 1; if ((n - 1 - i) % every === 0) s += `<text x="${X(i)}" y="${h - 8}" text-anchor="${last ? "end" : i === 0 ? "start" : "middle"}">${esc(l)}</text>`; });
    s += `</g>`;
    const path = vals => { let d = "", pen = false; vals.forEach((v, i) => { if (v == null) { pen = false; return; } d += `${pen ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)} `; pen = true; }); return d; };
    if (o.area && ser[0]) {
      const v = ser[0].values, idx = v.map((x, i) => x == null ? -1 : i).filter(i => i >= 0);
      if (idx.length > 1) s += `<path class="ar" d="${path(v)}L${X(idx[idx.length - 1])},${pt + ih} L${X(idx[0])},${pt + ih} Z"/>`;
    }
    if (o.ref) { const yy = Math.round(Y(o.ref.value)) + .5; s += `<line class="refl" x1="${pl}" x2="${w - pr}" y1="${yy}" y2="${yy}"/><text class="refl-t" x="${w - pr}" y="${yy - 5}" text-anchor="end">${esc(o.ref.label || fmt(o.ref.value))}</text>`; }
    ser.forEach((x, k) => { s += `<path class="ln s${k}${x.dashed ? " dash" : ""}" d="${path(x.values)}"/>`; });
    if (ser[0]) { const v = ser[0].values; let i = v.length - 1; while (i >= 0 && v[i] == null) i--; if (i >= 0) s += `<circle class="pt0" cx="${X(i)}" cy="${Y(v[i])}" r="4.5"/>`; }
    s += `<line class="xh" y1="${pt}" y2="${pt + ih}" x1="-9" x2="-9"/><rect class="hit" x="${pl}" y="${pt}" width="${iw}" height="${ih}"/></svg>`;
    const legend = ser.length > 1 ? `<div class="ulegend">${ser.map((x, k) => `<span><i class="sw s${k}${x.dashed ? " dash" : ""}"></i>${esc(x.label)}</span>`).join("")}</div>` : "";
    el.classList.add("uichart"); el._uiOpts = o; el._uiW = el.clientWidth; el._uiDraw = lineChart;
    el.innerHTML = legend + s + `<details class="tview"><summary>ดูเป็นตาราง</summary><div class="tvwrap"><table><thead><tr><th>ช่วง</th>${
      ser.map(x => `<th style="text-align:right">${esc(x.label)}${unit ? ` (${esc(unit)})` : ""}</th>`).join("")}</tr></thead><tbody>${
      labels.map((l, i) => `<tr><td>${esc(titles[i])}</td>${ser.map(x => `<td style="text-align:right">${x.values[i] == null ? "–" : esc(fmt(x.values[i]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "uitip"; tipEl.hidden = true; document.body.appendChild(tipEl); }
    const svg = el.querySelector("svg"), xh = svg.querySelector(".xh");
    svg.addEventListener("mousemove", e => {
      const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * (w / r.width);
      const i = Math.max(0, Math.min(n - 1, Math.round((px - pl) / (iw / Math.max(1, n - 1)))));
      xh.setAttribute("x1", X(i)); xh.setAttribute("x2", X(i));
      tipEl.innerHTML = `${esc(titles[i])}${ser.map(x => `<br>${esc(x.label)}: <b>${x.values[i] == null ? "–" : esc(fmt(x.values[i]))}</b> ${esc(unit)}`).join("")}`;
      tipEl.hidden = false;
      tipEl.style.left = Math.min(e.clientX + 14, innerWidth - tipEl.offsetWidth - 8) + "px"; tipEl.style.top = e.clientY + 14 + "px";
    });
    svg.addEventListener("mouseleave", () => { tipEl.hidden = true; xh.setAttribute("x1", -9); xh.setAttribute("x2", -9); });
    redrawOnResize(el);
  }
  // วาดกราฟใหม่เมื่อความกว้างเปลี่ยน (ใช้ข้อมูลชุดล่าสุดเสมอ)
  function redrawOnResize(el) {
    if (el._uiRo) return;
    el._uiRo = new ResizeObserver(() => { if (el.clientWidth === el._uiW) return; cancelAnimationFrame(el._uiRaf); el._uiRaf = requestAnimationFrame(() => el._uiDraw(el, el._uiOpts)); });
    el._uiRo.observe(el);
  }

  /* ---------- ข้อมูล: CSV และความคืบหน้าของเดือน (เวลาไทย) ---------- */
  // getCSV(url) → [{ หัวคอลัมน์: ค่า }] รองรับค่าที่มี , " และขึ้นบรรทัดใหม่ในเครื่องหมายคำพูด (ค่าทุกช่องเป็นข้อความ)
  async function getCSV(url) { const r = await fetchData(url); return withTime(parseCSV(await r.text()), r); }
  function parseCSV(text) {
    const rows = []; let row = [], f = "", q = false;
    text = text.replace(/^﻿/, "");
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
      else if (c === '"') q = true;
      else if (c === ",") { row.push(f); f = ""; }
      else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(f); rows.push(row); row = []; f = ""; }
      else f += c;
    }
    if (f || row.length) { row.push(f); rows.push(row); }
    const head = (rows.shift() || []).map(x => x.trim());
    return rows.filter(r => r.length > 1 || r[0]).map(r => Object.fromEntries(head.map((k, i) => [k, r[i] ?? ""])));
  }
  // รวมแถวเอง (ข้อมูลไม่เกินหลักหมื่นแถว ถ้ามากกว่านั้นให้หลังบ้านรวมมาเป็น JSON)
  //   sum(rows, r => +r.amount) · between(rows, r => r.timestamp, from, to) = แถวที่เวลาอยู่ใน [from, to)
  //   groupSum(rows, r => r.branch, r => +r.amount) → [[สาขา, ยอด], ...] มากไปน้อย (key ว่าง/null ข้าม)
  //   weekKey(t) = วันจันทร์ต้นสัปดาห์ของเวลานั้น ('YYYY-MM-DD' เวลาไทย) ใช้จัดกลุ่มรายสัปดาห์คู่กับ dayKey
  const sum = (rows, fn = x => x) => rows.reduce((a, r) => a + (+fn(r) || 0), 0);
  const between = (rows, atFn, from, to) => { const f = +toDate(from), t = +toDate(to); return rows.filter(r => { const x = +toDate(atFn(r)); return x >= f && x < t; }); };
  function groupSum(rows, keyFn, valFn = () => 1) {
    const m = new Map();
    for (const r of rows) { const k = keyFn(r); if (k == null || k === "") continue; m.set(k, (m.get(k) || 0) + (+valFn(r) || 0)); }
    return [...m].sort((a, b) => b[1] - a[1]);
  }
  function weekKey(v) {
    const d = toDate(v); if (!d) return null;
    const b = new Date(d.getTime() + 7 * 3600e3), back = (b.getUTCDay() + 6) % 7;
    return new Date(Date.UTC(b.getUTCFullYear(), b.getUTCMonth(), b.getUTCDate() - back)).toISOString().slice(0, 10);
  }
  // monthPace(now) → { pct, day, days, start, end, prevStart, prevSame } ตามเวลาไทย
  //   pct = % ของเดือนที่ผ่านไปแล้ว (ใส่เป็น mark ของ meter เป้า) · prevSame = จุดเดียวกันของเดือนก่อน (เทียบ "ช่วงวันเดียวกัน")
  function monthPace(now = new Date()) {
    const t = toDate(now).getTime(), B = 7 * 3600e3, b = new Date(t + B), y = b.getUTCFullYear(), m = b.getUTCMonth();
    const start = Date.UTC(y, m, 1) - B, end = Date.UTC(y, m + 1, 1) - B, prevStart = Date.UTC(y, m - 1, 1) - B;
    return { pct: (t - start) / (end - start) * 100, day: b.getUTCDate(), days: new Date(Date.UTC(y, m + 1, 0)).getUTCDate(),
             start: new Date(start), end: new Date(end), prevStart: new Date(prevStart), prevSame: new Date(Math.min(prevStart + (t - start), start)) };
  }

  /* ---------- โครงหน้า: ธีม, แถบข้างย่อ, เมนูตามส่วนที่ดูอยู่ ---------- */
  // initShell({ key: 'myDash', reloadHours: 6 }) — key = คำนำหน้า localStorage ของโปรเจกต์ (ห้ามซ้ำโปรเจกต์อื่นในโดเมนเดียวกัน)
  function initShell(o = {}) {
    const key = o.key || "uiDash", root = document.documentElement;
    const get = k => { try { return localStorage.getItem(key + k); } catch (e) { return null; } };
    const set = (k, v) => { try { localStorage.setItem(key + k, v); } catch (e) { /* ไม่มี storage ก็ใช้ค่าเริ่มต้น */ } };
    const t = get("Theme"); if (t === "dark" || t === "light") root.dataset.theme = t;
    if (get("SideMini") === "1") root.classList.add("side-mini");
    document.querySelectorAll("[data-icon]").forEach(e => { e.outerHTML = icon(e.dataset.icon); });
    const themeBtn = document.getElementById("themeBtn");
    const dark = () => (root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
    const paint = () => { if (themeBtn) { themeBtn.innerHTML = icon(dark() ? "sun" : "moon"); themeBtn.setAttribute("aria-label", dark() ? "เปลี่ยนเป็นโหมดสว่าง" : "เปลี่ยนเป็นโหมดมืด"); } };
    paint();
    if (themeBtn) themeBtn.addEventListener("click", () => { root.dataset.theme = dark() ? "light" : "dark"; set("Theme", root.dataset.theme); paint(); });
    const burger = document.getElementById("burger");
    if (burger) burger.addEventListener("click", () => set("SideMini", root.classList.toggle("side-mini") ? "1" : ""));
    const navs = [...document.querySelectorAll("#sidenav .nav[data-sec]")], secs = navs.map(a => document.getElementById(a.dataset.sec)).filter(Boolean);
    const mark = id => navs.forEach(a => { const on = a.dataset.sec === id; a.classList.toggle("on", on); if (on) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current"); });
    if (navs.length) {
      mark(navs[0].dataset.sec);
      const io = new IntersectionObserver(es => { const v = es.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]; if (v) mark(v.target.id); }, { rootMargin: "-20% 0px -60% 0px" });
      secs.forEach(s => io.observe(s));
      addEventListener("scroll", () => { if (scrollY < 140) mark(navs[0].dataset.sec); }, { passive: true });
    }
    if (root.dataset.shell === "wall") kiosk(o);
  }

  // จอค้าง (data-shell="wall"): ออกแบบที่ 1920×1080 แล้วย่อ/ขยายทั้งหน้าตามจอ (720p/4K หน้าตาเดียวกัน), กันจอดับ (ต้อง HTTPS),
  // และโหลดหน้าใหม่ทุก reloadHours ชม. เพื่อรับเวอร์ชันใหม่ — โหลดเมื่อเช็กแล้วว่าเซิร์ฟเวอร์ตอบ ไม่ให้จอค้างที่หน้า error ของเบราว์เซอร์
  function kiosk(o) {
    const root = document.documentElement;
    const fit = () => { root.style.zoom = innerWidth < 1000 ? "" : Math.min(innerWidth / 1920, innerHeight / 1080).toFixed(3); };
    fit(); addEventListener("resize", fit);
    const lock = () => { if (navigator.wakeLock && !document.hidden) navigator.wakeLock.request("screen").catch(() => {}); };
    lock(); document.addEventListener("visibilitychange", lock);
    const hrs = o.reloadHours ?? 6;
    if (hrs) setInterval(() => fetch(location.href, { method: "HEAD", cache: "no-store" }).then(r => { if (r.ok) location.reload(); }).catch(() => {}), hrs * 3600e3);
  }

  window.UI = { ICONS, icon, esc, fmtN, fmtCompact, fmtMillion, fmtPct, fmtDay, fmtTs, fmtTime, dayKey, rel, dur, patch, getJSON, every, live,
                pill, tile, meter, statCard, delta, rankList, sparkline, barChart, lineChart, getCSV, parseCSV, dataTime, monthPace, sum, between, groupSum, weekKey, initShell };
})();
