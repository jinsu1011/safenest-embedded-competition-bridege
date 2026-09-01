/* ==========================================================================
   SafeNest Console - app.js
   --------------------------------------------------------------------------
   화면 로직. 데이터는 전부 SafeNest.api 를 통해서만 들어온다.
   외부 CDN 의존성 없음 (차트·열화상 모두 자체 Canvas 렌더러) → 현장 오프라인
   라즈베리파이/LCD 환경에서도 그대로 동작한다.
   ========================================================================== */

(function (global) {
  "use strict";

  const api = global.SafeNest.api;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ====================================================================== */
  /* 저장소                                                                  */
  /* ====================================================================== */

  const KEY = {
    spaces: "safenest.spaces.v3",
    events: "safenest.events.v3",
    current: "safenest.current.v3",
    thresholds: "safenest.thresholds.v3",
    prefs: "safenest.prefs.v3",
  };

  const EVENT_CAP = 500;

  const DEFAULT_SPACES = [
    { id: "A01", name: "밀폐공간 A-01", nodeId: "SN-A01", host: "192.168.1.44", port: "8000", scenario: "occupied" },
    { id: "B02", name: "통학차량 B-02", nodeId: "SN-B02", host: "192.168.1.45", port: "8000", scenario: "empty" },
    { id: "C03", name: "정화조 C-03", nodeId: "SN-C03", host: "192.168.1.46", port: "8000", scenario: "co2" },
    { id: "D04", name: "저장탱크 D-04", nodeId: "SN-D04", host: "192.168.1.47", port: "8000", scenario: "collapse" },
    { id: "E05", name: "집수정 E-05", nodeId: "SN-E05", host: "192.168.1.48", port: "8000", scenario: "fault" },
  ];

  const DEFAULT_PREFS = {
    theme: "dark",
    mode: "demo",
    baseUrl: "http://192.168.1.44:8000",
    pollMs: 2000,
    sound: false,
    autoLog: true,
  };

  function load(key, fallback) {
    try {
      const v = JSON.parse(localStorage.getItem(key));
      if (v === null || v === undefined) return structuredClone(fallback);
      if (Array.isArray(fallback)) return Array.isArray(v) && v.length ? v : structuredClone(fallback);
      return { ...structuredClone(fallback), ...v };
    } catch {
      return structuredClone(fallback);
    }
  }
  const save = (key, v) => localStorage.setItem(key, JSON.stringify(v));

  /* ====================================================================== */
  /* 상태                                                                    */
  /* ====================================================================== */

  const state = {
    spaces: load(KEY.spaces, DEFAULT_SPACES),
    events: load(KEY.events, []),
    thresholds: load(KEY.thresholds, api.DEFAULT_THRESHOLDS),
    prefs: load(KEY.prefs, DEFAULT_PREFS),
    currentId: localStorage.getItem(KEY.current) || "A01",
    telemetry: null,        // 현재 공간의 최신 뷰모델
    snapshots: {},          // spaceId → 최신 뷰모델 (공간 관리 화면용)
    history: [],            // 최근 표본 (차트용)
    view: "dashboard",
    lastLevel: null,
    ackedAt: 0,
    connError: null,
  };

  const HISTORY_CAP = 150;

  /* ====================================================================== */
  /* 아이콘 (인라인 SVG)                                                     */
  /* ====================================================================== */

  const ico = {
    shield: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    gauge: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 14 8.5 9.5"/><path d="M3.5 19a9 9 0 1 1 17 0"/></svg>`,
    grid: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`,
    list: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg>`,
    cog: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.2.5.68.86 1.24 1H21a2 2 0 1 1 0 4h-.09c-.56.14-1.04.5-1.51 1z"/></svg>`,
    lungs: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v10"/><path d="M9 13c0 4-1.5 7-4 7-1.1 0-2-.9-2-2 0-4 1.5-8 3.5-9.5C7.7 8 9 8.9 9 10.4z"/><path d="M15 13c0 4 1.5 7 4 7 1.1 0 2-.9 2-2 0-4-1.5-8-3.5-9.5C16.3 8 15 8.9 15 10.4z"/></svg>`,
    thermo: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>`,
    wind: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h10a3 3 0 1 0-3-3"/><path d="M3 13h14a3 3 0 1 1-3 3"/><path d="M3 18h7"/></svg>`,
    motion: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2.5"/><path d="M6.5 6.5a8 8 0 0 0 0 11M17.5 6.5a8 8 0 0 1 0 11M3.5 3.5a12 12 0 0 0 0 17M20.5 3.5a12 12 0 0 1 0 17"/></svg>`,
    radar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 12 20 6"/><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/></svg>`,
    alert: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v5M12 17h.01"/><circle cx="12" cy="12" r="9.5"/></svg>`,
    check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="m4.5 12.5 5 5 10-11"/></svg>`,
    eyeOff: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.9 5.2A9.6 9.6 0 0 1 12 5c6 0 10 7 10 7a17 17 0 0 1-3 3.7M6.6 6.6A17 17 0 0 0 2 12s4 7 10 7a9.6 9.6 0 0 0 4.3-1"/><path d="M3 3l18 18"/></svg>`,
    chev: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`,
    sun: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>`,
    moon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>`,
    expand: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9V3h6M21 15v6h-6M21 9V3h-6M3 15v6h6"/></svg>`,
    flask: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v6.2L4.6 18A2 2 0 0 0 6.4 21h11.2a2 2 0 0 0 1.8-3L14 8.2V2"/><path d="M8.5 2h7"/></svg>`,
  };

  /* ====================================================================== */
  /* 헬퍼                                                                    */
  /* ====================================================================== */

  const esc = (v) =>
    String(v ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));

  const fmt = (v, digits = 0, dash = "—") =>
    v === null || v === undefined || !Number.isFinite(v) ? dash : v.toFixed(digits);

  const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  function toneColor(tone) {
    return cssVar(`--${tone}`) || cssVar("--fault");
  }

  function timeStr(ms) {
    const d = new Date(ms);
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  function dateTimeStr(ms) {
    const d = new Date(ms);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  function agoStr(ms) {
    const s = Math.max(0, Math.round((Date.now() - ms) / 1000));
    if (s < 60) return `${s}초 전`;
    if (s < 3600) return `${Math.floor(s / 60)}분 전`;
    return `${Math.floor(s / 3600)}시간 전`;
  }

  function toast(msg, kind = "") {
    const stack = $("#toastStack");
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.innerHTML = `<span class="tdot"></span><span>${esc(msg)}</span>`;
    stack.appendChild(el);
    setTimeout(() => {
      el.classList.add("leaving");
      setTimeout(() => el.remove(), 200);
    }, 2600);
  }

  const getSpace = (id) => state.spaces.find((s) => s.id === id);
  const currentSpace = () => getSpace(state.currentId) || state.spaces[0];

  /* ====================================================================== */
  /* 이벤트 로그                                                             */
  /* ====================================================================== */

  const LEVEL_TO_EVENT = {
    NORMAL: "normal", CAUTION: "caution", DANGER: "danger",
    EMERGENCY: "emergency", FAULT: "fault",
  };

  function pushEvent(entry) {
    state.events.unshift({
      id: `E${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`,
      ts: Date.now(),
      acked: false,
      ...entry,
    });
    if (state.events.length > EVENT_CAP) state.events.length = EVENT_CAP;
    save(KEY.events, state.events);
    if (state.view === "events") renderEvents();
    renderRecentEvents();
    updateNavCounts();
  }

  /** 등급이 바뀌는 순간에만 기록한다 (틱마다 기록하면 로그가 무의미해진다). */
  function logLevelTransition(t) {
    if (!state.prefs.autoLog) return;
    if (state.lastLevel === t.level) return;
    state.lastLevel = t.level;
    pushEvent({
      spaceId: state.currentId,
      level: LEVEL_TO_EVENT[t.level] || "fault",
      message: `${t.levelMeta.label} 상태 진입`,
      detail: t.reasons.length ? t.reasons.map(api.reasonText).join(" · ") : "추가 사유 없음",
      risk: t.riskScore,
    });
  }

  /* ====================================================================== */
  /* 열화상 렌더러                                                           */
  /* ====================================================================== */

  // Inferno 계열 컬러맵 (저온 → 고온)
  const COLORMAP = [
    [8, 8, 30], [26, 15, 72], [61, 15, 108], [98, 24, 111],
    [136, 39, 103], [175, 56, 85], [207, 82, 60], [231, 116, 36],
    [246, 155, 17], [251, 199, 39], [246, 236, 130], [255, 252, 224],
  ];

  function heatColor(t) {
    const x = Math.max(0, Math.min(0.9999, t)) * (COLORMAP.length - 1);
    const i = Math.floor(x);
    const f = x - i;
    const a = COLORMAP[i];
    const b = COLORMAP[Math.min(COLORMAP.length - 1, i + 1)];
    return [
      Math.round(a[0] + (b[0] - a[0]) * f),
      Math.round(a[1] + (b[1] - a[1]) * f),
      Math.round(a[2] + (b[2] - a[2]) * f),
    ];
  }

  const thermalScratch = document.createElement("canvas");

  function renderThermal(frame) {
    const wrap = $("#thermalWrap");
    const canvas = $("#thermalCanvas");
    wrap.querySelectorAll(".thermal-box, .thermal-hot").forEach((n) => n.remove());

    if (!frame || !frame.data || !frame.data.length) {
      wrap.classList.add("no-data");
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      $("#thermalRange").textContent = "—";
      return;
    }
    wrap.classList.remove("no-data");

    const { w, h, data } = frame;
    const min = Number.isFinite(frame.min_c) ? frame.min_c : Math.min(...data);
    const max = Number.isFinite(frame.max_c) ? frame.max_c : Math.max(...data);
    const span = Math.max(0.5, max - min);

    thermalScratch.width = w;
    thermalScratch.height = h;
    const sctx = thermalScratch.getContext("2d");
    const img = sctx.createImageData(w, h);
    for (let i = 0; i < w * h; i++) {
      const [r, g, b] = heatColor((data[i] - min) / span);
      img.data[i * 4] = r;
      img.data[i * 4 + 1] = g;
      img.data[i * 4 + 2] = b;
      img.data[i * 4 + 3] = 255;
    }
    sctx.putImageData(img, 0, 0);

    const rect = wrap.getBoundingClientRect();
    const dpr = Math.min(2, global.devicePixelRatio || 1);
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(thermalScratch, 0, 0, canvas.width, canvas.height);

    if (frame.box) {
      const box = document.createElement("div");
      box.className = "thermal-box";
      box.dataset.label = "인체 영역";
      box.style.left = `${Math.max(0, frame.box.x) * 100}%`;
      box.style.top = `${Math.max(0, frame.box.y) * 100}%`;
      box.style.width = `${Math.min(1, frame.box.w) * 100}%`;
      box.style.height = `${Math.min(1, frame.box.h) * 100}%`;
      wrap.appendChild(box);
    }
    if (frame.hot) {
      const hot = document.createElement("span");
      hot.className = "thermal-hot";
      hot.style.left = `${frame.hot.x * 100}%`;
      hot.style.top = `${frame.hot.y * 100}%`;
      wrap.appendChild(hot);
    }

    $("#thermalRange").textContent = `${min.toFixed(1)}℃ – ${max.toFixed(1)}℃`;
    $("#thermalRes").textContent = `${w}×${h}`;
  }

  /* ====================================================================== */
  /* 추세 차트 (자체 Canvas 렌더러 — 외부 라이브러리 없음)                    */
  /* ====================================================================== */

  const SERIES = [
    { key: "breathRpm", label: "호흡수 (rpm)", color: "--accent", axis: "left", on: true },
    { key: "tempMaxC", label: "최고 체표온 (℃)", color: "--danger", axis: "left", on: true },
    { key: "co2Scaled", label: "CO₂ (×100 ppm)", color: "--caution", axis: "left", on: true },
    { key: "riskScore", label: "위험도", color: "--emergency", axis: "right", on: true },
  ];

  const chartState = { hoverIdx: -1 };

  function drawChart() {
    const canvas = $("#trendCanvas");
    if (!canvas) return;
    const wrap = canvas.parentElement;
    const rect = wrap.getBoundingClientRect();
    if (rect.width < 10) return;

    const dpr = Math.min(2, global.devicePixelRatio || 1);
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const pts = state.history;
    $("#chartEmpty").hidden = pts.length >= 2;
    if (pts.length < 2) return;

    const padL = 38, padR = 40, padT = 12, padB = 24;
    const W = rect.width - padL - padR;
    const H = rect.height - padT - padB;
    const line = cssVar("--line-soft");
    const muted = cssVar("--muted");

    // 좌축 범위 (호흡/온도/CO2×0.01 공통 스케일)
    const leftVals = [];
    const active = SERIES.filter((s) => s.on);
    pts.forEach((p) => {
      active.forEach((s) => {
        if (s.axis !== "left") return;
        const v = p[s.key];
        if (Number.isFinite(v)) leftVals.push(v);
      });
    });
    let lo = leftVals.length ? Math.min(...leftVals) : 0;
    let hi = leftVals.length ? Math.max(...leftVals) : 40;
    if (hi - lo < 4) { const m = (hi + lo) / 2; lo = m - 2; hi = m + 2; }
    const pad = (hi - lo) * 0.12;
    lo -= pad; hi += pad;

    const xAt = (i) => padL + (W * i) / (pts.length - 1);
    const yLeft = (v) => padT + H - ((v - lo) / (hi - lo)) * H;
    const yRight = (v) => padT + H - (Math.max(0, Math.min(100, v)) / 100) * H;

    // 그리드 + 좌축 눈금
    ctx.strokeStyle = line;
    ctx.lineWidth = 1;
    ctx.fillStyle = muted;
    ctx.font = "10px " + cssVar("--font").split(",")[0].replace(/"/g, "");
    ctx.textBaseline = "middle";
    for (let i = 0; i <= 4; i++) {
      const y = padT + (H * i) / 4;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + W, y);
      ctx.stroke();
      const v = hi - ((hi - lo) * i) / 4;
      ctx.textAlign = "right";
      ctx.fillText(v.toFixed(0), padL - 7, y);
      ctx.textAlign = "left";
      ctx.fillText(String(100 - i * 25), padL + W + 7, y);
    }

    // 위험도 밴드 (우축 기준 60/85 경계)
    [[85, "--emergency"], [60, "--danger"]].forEach(([v, c]) => {
      ctx.save();
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = cssVar(c);
      ctx.globalAlpha = 0.35;
      const y = yRight(v);
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + W, y);
      ctx.stroke();
      ctx.restore();
    });

    // 시계열
    active.forEach((s) => {
      const color = cssVar(s.color);
      ctx.strokeStyle = color;
      ctx.lineWidth = s.axis === "right" ? 2.2 : 1.8;
      ctx.lineJoin = "round";
      ctx.beginPath();
      let started = false;
      pts.forEach((p, i) => {
        const v = p[s.key];
        if (!Number.isFinite(v)) { started = false; return; }
        const x = xAt(i);
        const y = s.axis === "right" ? yRight(v) : yLeft(v);
        if (!started) { ctx.moveTo(x, y); started = true; }
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // 마지막 값 점
      for (let i = pts.length - 1; i >= 0; i--) {
        const v = pts[i][s.key];
        if (Number.isFinite(v)) {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(xAt(i), s.axis === "right" ? yRight(v) : yLeft(v), 2.6, 0, Math.PI * 2);
          ctx.fill();
          break;
        }
      }
    });

    // x축 라벨
    ctx.fillStyle = muted;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    [0, Math.floor((pts.length - 1) / 2), pts.length - 1].forEach((i) => {
      ctx.fillText(timeStr(pts[i].ts), xAt(i), padT + H + 7);
    });

    // 호버 크로스헤어
    if (chartState.hoverIdx >= 0 && chartState.hoverIdx < pts.length) {
      const i = chartState.hoverIdx;
      const x = xAt(i);
      ctx.save();
      ctx.strokeStyle = cssVar("--muted");
      ctx.globalAlpha = 0.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, padT);
      ctx.lineTo(x, padT + H);
      ctx.stroke();
      ctx.restore();

      const p = pts[i];
      const lines = [timeStr(p.ts)].concat(
        active.map((s) => `${s.label.split(" (")[0]} ${Number.isFinite(p[s.key]) ? p[s.key].toFixed(1) : "—"}`)
      );
      const bw = 132, bh = 16 + lines.length * 14;
      const bx = Math.min(padL + W - bw, Math.max(padL, x + 10));
      const by = padT + 6;
      ctx.fillStyle = cssVar("--surface");
      ctx.strokeStyle = cssVar("--line");
      ctx.lineWidth = 1;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(bx, by, bw, bh, 8);
      else ctx.rect(bx, by, bw, bh);
      ctx.fill();
      ctx.stroke();
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      lines.forEach((t, k) => {
        ctx.fillStyle = k === 0 ? cssVar("--muted") : cssVar(active[k - 1].color);
        ctx.fillText(t, bx + 9, by + 8 + k * 14);
      });
    }
  }

  function renderChartLegend() {
    $("#chartLegend").innerHTML = SERIES.map(
      (s, i) => `<button type="button" data-series="${i}" class="${s.on ? "" : "off"}">
        <span class="sw" style="background:${cssVar(s.color)}"></span>${esc(s.label)}</button>`
    ).join("");
    $$("#chartLegend button").forEach((btn) =>
      btn.addEventListener("click", () => {
        const s = SERIES[Number(btn.dataset.series)];
        s.on = !s.on;
        renderChartLegend();
        drawChart();
      })
    );
  }

  /* ====================================================================== */
  /* 임계 게이지                                                             */
  /* ====================================================================== */

  /**
   * segs: [{ to: number, tone: 'ok'|'caution'|'danger' }] 누적 경계값
   * value 위치를 마커로 표시한다.
   */
  function gaugeHtml(value, min, max, segs) {
    const span = max - min;
    let prev = min;
    const bars = segs.map((s) => {
      const w = ((Math.min(max, s.to) - prev) / span) * 100;
      prev = s.to;
      return `<span class="seg ${s.tone}" style="width:${Math.max(0, w).toFixed(1)}%"></span>`;
    }).join("");
    const hasVal = Number.isFinite(value);
    const pos = hasVal ? Math.max(0, Math.min(100, ((value - min) / span) * 100)) : 0;
    return `<div class="gauge">
      <div class="gauge-track">${bars}${hasVal ? `<span class="gauge-mark" style="left:${pos.toFixed(1)}%"></span>` : ""}</div>
      <div class="gauge-legend"><span>${min}</span><span>${max}</span></div>
    </div>`;
  }

  function qTone(q) {
    return q >= 1 ? "ok" : q >= 0.5 ? "mid" : "bad";
  }

  /* ====================================================================== */
  /* 대시보드 렌더                                                           */
  /* ====================================================================== */

  function renderDashboard(t) {
    const th = state.thresholds;
    const meta = t.levelMeta;
    const color = toneColor(meta.tone);

    /* --- 링 게이지 --- */
    const R = 76;
    const circ = 2 * Math.PI * R;
    const score = Number.isFinite(t.riskScore) ? t.riskScore : 0;
    const ring = $("#ringProg");
    ring.style.strokeDasharray = String(circ);
    ring.style.strokeDashoffset = String(circ * (1 - score / 100));
    ring.style.stroke = color;
    $("#ringValue").textContent = Number.isFinite(t.riskScore) ? Math.round(t.riskScore) : "—";
    $("#ringValue").style.color = color;

    const tag = $("#levelTag");
    tag.textContent = meta.label;
    tag.style.color = color;
    tag.style.background = cssVar(`--${meta.tone}-bg`);
    tag.style.borderColor = color;

    /* --- 헤드라인 --- */
    let headline;
    if (t.level === "FAULT") headline = "센서 상태 확인 필요";
    else if (!t.presence) headline = "재실 인원 없음";
    else headline = `작업자 ${t.occupants || 1}명 감지`;
    $("#heroHeadline").textContent = headline;
    $("#heroSub").textContent =
      t.level === "FAULT"
        ? `시스템 상태 ${t.systemStatus}`
        : `${currentSpace().name} · ${timeStr(t.ts)} 기준`;

    const act = $("#actionLine");
    act.style.color = color;
    act.style.borderColor = color;
    act.style.background = cssVar(`--${meta.tone}-bg`);
    act.innerHTML = `${t.level === "NORMAL" ? ico.check : ico.alert}<span>${esc(meta.action)}</span>`;

    /* --- 판단 근거 --- */
    const hot = new Set(["APNEA_SUSPECTED", "HUMAN_FALL", "NO_MOTION_TIMEOUT", "CO2_CRITICAL", "HIGH_BODY_TEMP", "ALL_SENSORS_MISSING"]);
    $("#reasonList").innerHTML = t.reasons.length
      ? t.reasons.map((r) => `<span class="reason-chip ${hot.has(r) ? "hot" : ""}" title="${esc(r)}">${esc(api.reasonText(r))}</span>`).join("")
      : `<span class="reason-empty">위험 판단에 사용된 이상 신호가 없습니다.</span>`;

    /* --- 요약 팩트 --- */
    $("#factHeart").textContent = t.heartValid && Number.isFinite(t.heartBpm) ? `${fmt(t.heartBpm, 0)} bpm` : "—";
    $("#factConf").textContent = `${api.fusionConfidence(t)}%`;
    $("#factSlope").textContent = Number.isFinite(t.co2Slope) ? `${t.co2Slope > 0 ? "+" : ""}${fmt(t.co2Slope, 0)} ppm/분` : "—";
    $("#factSystem").textContent = { OK: "정상", DEGRADED: "성능 저하", FAULT: "고장" }[t.systemStatus] || t.systemStatus;
    $("#factSystem").style.color = t.systemStatus === "OK" ? cssVar("--normal") : t.systemStatus === "DEGRADED" ? cssVar("--caution") : cssVar("--emergency");

    /* --- 측정 타일 --- */
    // 호흡수
    setMetric("breath", {
      value: Number.isFinite(t.breathRpm) ? fmt(t.breathRpm, 1) : "—",
      unit: "rpm",
      q: t.quality.mmwave,
      gauge: gaugeHtml(t.breathRpm, 0, 40, [
        { to: th.breathLow, tone: "danger" },
        { to: th.breathHigh, tone: "ok" },
        { to: 40, tone: "danger" },
      ]),
      foot: !Number.isFinite(t.breathRpm)
        ? ["재실 미확인 · 호흡 측정 없음", "fault"]
        : t.breathRpm < th.breathLow
        ? [`저호흡 (기준 ${th.breathLow} rpm 미만)`, "emergency"]
        : t.breathRpm > th.breathHigh
        ? [`과호흡 (기준 ${th.breathHigh} rpm 초과)`, "caution"]
        : [`정상 범위 ${th.breathLow}~${th.breathHigh} rpm`, "ok"],
    });

    // 체표온
    setMetric("temp", {
      value: Number.isFinite(t.tempMaxC) ? fmt(t.tempMaxC, 1) : "—",
      unit: "℃",
      q: t.quality.thermal,
      gauge: gaugeHtml(t.tempMaxC, 20, 45, [
        { to: th.tempLow, tone: "caution" },
        { to: th.tempHigh, tone: "ok" },
        { to: 45, tone: "danger" },
      ]),
      foot: !Number.isFinite(t.tempMaxC)
        ? ["열화상 수신 없음", "fault"]
        : t.tempMaxC >= th.tempHigh
        ? [`고체온 의심 (기준 ${th.tempHigh}℃)`, "emergency"]
        : t.presence
        ? [`평균 ${fmt(t.tempAvgC, 1)}℃ · 정상 범위`, "ok"]
        : [`공간 온도 · 인체 미감지`, "ok"],
    });

    // CO2
    setMetric("co2", {
      value: Number.isFinite(t.co2Ppm) ? Math.round(t.co2Ppm).toLocaleString("ko-KR") : "—",
      unit: "ppm",
      q: t.quality.co2,
      gauge: gaugeHtml(t.co2Ppm, 400, 3000, [
        { to: th.co2Caution, tone: "ok" },
        { to: th.co2Danger, tone: "caution" },
        { to: 3000, tone: "danger" },
      ]),
      foot: !Number.isFinite(t.co2Ppm)
        ? ["SCD40 수신 없음", "fault"]
        : t.co2Ppm >= th.co2Danger
        ? ["즉시 환기 필요", "emergency"]
        : t.co2Ppm >= th.co2Caution
        ? [`주의 기준 ${th.co2Caution.toLocaleString("ko-KR")} ppm 초과`, "caution"]
        : ["공기질 정상", "ok"],
    });

    // 움직임
    const age = t.motionAgeSec;
    setMetric("motion", {
      value: t.motion === null ? "—" : t.motion ? "감지됨" : "정지",
      unit: "",
      q: t.quality.pir,
      gauge: gaugeHtml(Number.isFinite(age) ? Math.min(age, 60) : null, 0, 60, [
        { to: th.motionTimeout, tone: "ok" },
        { to: 60, tone: "danger" },
      ]),
      foot: !Number.isFinite(age)
        ? ["PIR 수신 없음", "fault"]
        : age >= th.motionTimeout
        ? [`${Math.round(age)}초간 무움직임 (기준 ${th.motionTimeout}초)`, "emergency"]
        : t.motion
        ? [`${Math.round(age)}초 전 움직임 감지`, "ok"]
        : [`${Math.round(age)}초 경과 · 감시 중`, "caution"],
    });

    /* --- 센서 상태 --- */
    renderSensorRows(t);
    $("#confValue").textContent = `${api.fusionConfidence(t)}%`;
    $("#confText").textContent =
      t.level === "FAULT"
        ? "센서 노드 전원·네트워크 확인이 필요합니다."
        : `mmWave · 열화상 · CO₂ · PIR 교차 검증 (${t.source === "demo" ? "데모 데이터" : "게이트웨이 실측"})`;

    /* --- 열화상 --- */
    renderThermal(t.thermal);
    $("#thermalPeak").textContent = Number.isFinite(t.tempMaxC) ? `최고 ${fmt(t.tempMaxC, 1)}℃` : "—";

    /* --- 경보 배너 --- */
    renderAlert(t);
  }

  function setMetric(id, opt) {
    $(`#${id}Value`).textContent = opt.value;
    $(`#${id}Unit`).textContent = opt.unit;
    $(`#${id}Gauge`).innerHTML = opt.gauge;
    const foot = $(`#${id}Foot`);
    foot.textContent = opt.foot[0];
    foot.className = `metric-foot ${opt.foot[1]}`;
    const dot = $(`#${id}Q`);
    dot.className = `q-dot ${qTone(opt.q)}`;
    dot.title = `센서 품질 q=${opt.q.toFixed(2)}`;
  }

  const SENSOR_ROWS = [
    { key: "mmwave", name: "mmWave MR60BHA2", icon: "radar", desc: (t) => t.mmwaveState || "—" },
    { key: "thermal", name: "열화상 어레이 80×62", icon: "thermo", desc: (t) => (t.thermal ? "프레임 수신 중" : "수신 없음") },
    { key: "co2", name: "CO₂ SCD40", icon: "wind", desc: (t) => (Number.isFinite(t.co2Ppm) ? `${Math.round(t.co2Ppm)} ppm` : "수신 없음") },
    { key: "pir", name: "PIR 모션", icon: "motion", desc: (t) => (t.motion === null ? "수신 없음" : t.motion ? "MOTION" : "IDLE") },
  ];

  function renderSensorRows(t) {
    $("#sensorList").innerHTML = SENSOR_ROWS.map((s) => {
      const q = t.quality[s.key];
      const tone = q >= 1 ? "normal" : q >= 0.5 ? "caution" : "fault";
      const c = cssVar(`--${tone}`);
      return `<div class="sensor-row">
        <span class="sic" style="color:${c}">${ico[s.icon]}</span>
        <div><div class="snm">${esc(s.name)}</div><div class="sst">${esc(s.desc(t))}</div></div>
        <div class="q-bar"><i style="width:${(q * 100).toFixed(0)}%;background:${c}"></i></div>
        <div class="q-num" style="color:${c}">${q.toFixed(2)}</div>
      </div>`;
    }).join("");
  }

  function renderAlert(t) {
    const bar = $("#alertBar");
    const needAlert = ["CAUTION", "DANGER", "EMERGENCY", "FAULT"].includes(t.level);
    if (!needAlert) {
      bar.className = "alert-bar";
      return;
    }
    const meta = t.levelMeta;
    bar.className = `alert-bar show ${meta.tone}`;
    $("#alertTitle").textContent = `${meta.label}: ${headlineFor(t)}`;
    $("#alertDetail").textContent = t.reasons.length
      ? t.reasons.map(api.reasonText).join(" · ")
      : meta.action;
    const acked = Date.now() - state.ackedAt < 60_000;
    $("#alertAck").innerHTML = `<span>${acked ? "확인됨" : "경보 확인"}</span>`;
    $("#alertAck").disabled = acked;
  }

  function headlineFor(t) {
    if (t.level === "FAULT") return "센서 데이터가 수신되지 않습니다";
    const r = t.reasons;
    if (r.includes("APNEA_SUSPECTED")) return "무호흡이 의심됩니다";
    if (r.includes("HUMAN_FALL")) return "작업자 쓰러짐이 추정됩니다";
    if (r.includes("NO_MOTION_TIMEOUT")) return "장시간 움직임이 없습니다";
    if (r.includes("CO2_CRITICAL")) return "CO₂ 농도가 위험 수준입니다";
    if (r.includes("CO2_ELEVATED")) return "CO₂ 농도가 상승했습니다";
    if (r.includes("LOW_BREATH_RATE")) return "호흡수가 기준 이하입니다";
    return t.levelMeta.action;
  }

  function renderRecentEvents() {
    const rows = state.events.slice(0, 5);
    $("#recentEvents").innerHTML = rows.length
      ? rows.map((e) => `<tr>
          <td class="mono">${timeStr(e.ts)}</td>
          <td><span class="badge ${e.level}">${levelLabel(e.level)}</span></td>
          <td>${esc(e.message)}</td>
        </tr>`).join("")
      : `<tr><td colspan="3" class="empty-state" style="padding:26px">기록된 이벤트가 없습니다.</td></tr>`;
  }

  const levelLabel = (l) =>
    ({ normal: "정상", info: "정보", caution: "주의", danger: "위험", emergency: "긴급", fault: "센서 이상" }[l] || l);

  /* ====================================================================== */
  /* 공간 관리                                                               */
  /* ====================================================================== */

  function snapshotOf(space) {
    const snap = state.snapshots[space.id];
    if (snap) return snap;
    // 아직 관측 전인 공간은 시나리오 기반 1회 표본으로 대체 (데모 모드 한정).
    // live 모드에서는 게이트웨이가 응답하기 전까지 null 로 두고 "수신 없음"을 표시한다.
    if (api.config.mode === "demo") {
      const t = api.sampleScenario(space.scenario || "occupied");
      state.snapshots[space.id] = t;
      return t;
    }
    return null;
  }

  function renderSpaces() {
    const snaps = state.spaces.map((s) => ({ space: s, t: snapshotOf(s) }));
    const count = (fn) => snaps.filter(({ t }) => t && fn(t.level)).length;

    $("#kpiGrid").innerHTML = [
      ["전체 공간", state.spaces.length, "--accent"],
      ["정상", count((l) => l === "NORMAL"), "--normal"],
      ["주의", count((l) => l === "CAUTION"), "--caution"],
      ["위험·긴급", count((l) => l === "DANGER" || l === "EMERGENCY"), "--emergency"],
      ["센서 이상", count((l) => l === "FAULT"), "--fault"],
    ].map(([label, value, c]) =>
      `<article class="card kpi"><span class="bar" style="background:${cssVar(c)}"></span>
        <div><span>${label}</span><strong style="color:${cssVar(c)}">${value}</strong></div></article>`
    ).join("");

    $("#spaceGrid").innerHTML = snaps.map(({ space, t }) => {
      const meta = t ? t.levelMeta : api.LEVEL.FAULT;
      const c = toneColor(meta.tone);
      const score = t && Number.isFinite(t.riskScore) ? Math.round(t.riskScore) : null;
      return `<article class="card space-card ${space.id === state.currentId ? "current" : ""}">
        <div class="space-card-head">
          <div><h3>${esc(space.name)}</h3><div class="addr">${esc(space.nodeId)} · ${esc(space.host)}:${esc(space.port)}</div></div>
          <span class="badge ${meta.tone}">${meta.label}</span>
        </div>
        <div>
          <div class="space-score"><b style="color:${c}">${score === null ? "—" : score}</b><span>위험도 / 100</span></div>
          <div class="track" style="margin-top:8px"><i style="width:${score === null ? 100 : Math.max(3, score)}%;background:${c}"></i></div>
        </div>
        <div class="mini-metrics">
          <div class="mini"><span>호흡</span><strong>${t && Number.isFinite(t.breathRpm) ? fmt(t.breathRpm, 1) : "—"}</strong></div>
          <div class="mini"><span>CO₂</span><strong>${t && Number.isFinite(t.co2Ppm) ? Math.round(t.co2Ppm) : "—"}</strong></div>
          <div class="mini"><span>체표온</span><strong>${t && Number.isFinite(t.tempMaxC) ? fmt(t.tempMaxC, 1) : "—"}</strong></div>
        </div>
        <div class="space-foot">
          <span class="last">${t ? agoStr(t.ts) + " 수신" : "수신 없음"}</span>
          <button class="btn sm" data-open-space="${space.id}" type="button">관제 화면 열기</button>
        </div>
      </article>`;
    }).join("");

    $$("[data-open-space]").forEach((b) =>
      b.addEventListener("click", () => selectSpace(b.dataset.openSpace, true))
    );
  }

  /* ====================================================================== */
  /* 이벤트 로그 화면                                                        */
  /* ====================================================================== */

  function filteredEvents() {
    const sp = $("#filterSpace").value;
    const lv = $("#filterLevel").value;
    const q = $("#filterSearch").value.trim().toLowerCase();
    return state.events.filter((e) => {
      const name = getSpace(e.spaceId)?.name || "";
      const text = `${e.message} ${e.detail} ${name}`.toLowerCase();
      return (sp === "all" || e.spaceId === sp) && (lv === "all" || e.level === lv) && (!q || text.includes(q));
    });
  }

  function renderEvents() {
    const sel = $("#filterSpace");
    const keep = sel.value;
    sel.innerHTML = `<option value="all">전체 공간</option>` +
      state.spaces.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("");
    sel.value = state.spaces.some((s) => s.id === keep) ? keep : "all";

    const rows = filteredEvents();
    $("#eventCount").textContent = `조회 ${rows.length}건 / 전체 ${state.events.length}건`;
    $("#eventEmpty").hidden = rows.length > 0;
    $("#eventTable").innerHTML = rows.map((e) => `<tr>
      <td class="mono">${dateTimeStr(e.ts)}</td>
      <td>${esc(getSpace(e.spaceId)?.name || "삭제된 공간")}</td>
      <td><span class="badge ${e.level}">${levelLabel(e.level)}</span></td>
      <td>${Number.isFinite(e.risk) ? Math.round(e.risk) : "—"}</td>
      <td>${esc(e.message)}</td>
      <td style="color:var(--muted)">${esc(e.detail)}</td>
      <td>${e.acked
        ? `<span class="badge normal">확인됨</span>`
        : `<button class="btn sm" data-ack="${e.id}" type="button">확인</button>`}</td>
    </tr>`).join("");

    $$("[data-ack]").forEach((b) =>
      b.addEventListener("click", async () => {
        const ev = state.events.find((e) => e.id === b.dataset.ack);
        if (!ev) return;
        const res = await api.ackEvent(ev.id);
        if (!res.ok && res.error !== "DEMO_MODE") return toast("게이트웨이 확인 처리 실패", "err");
        ev.acked = true;
        save(KEY.events, state.events);
        renderEvents();
        updateNavCounts();
      })
    );
  }

  function exportCsv() {
    const rows = filteredEvents();
    if (!rows.length) return toast("내보낼 이벤트가 없습니다.", "err");
    const head = ["일시", "공간", "등급", "위험도", "내용", "상세", "확인여부"];
    const body = rows.map((e) => [
      dateTimeStr(e.ts),
      getSpace(e.spaceId)?.name || "",
      levelLabel(e.level),
      Number.isFinite(e.risk) ? Math.round(e.risk) : "",
      e.message,
      e.detail,
      e.acked ? "확인" : "미확인",
    ]);
    const csv = "﻿" + [head, ...body]
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
      .join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `safenest_events_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast(`${rows.length}건을 CSV로 내보냈습니다.`, "ok");
  }

  /* ====================================================================== */
  /* 설정 화면                                                               */
  /* ====================================================================== */

  function renderSettings() {
    const sel = $("#renameSelect");
    sel.innerHTML = state.spaces.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("");
    sel.value = state.spaces.some((s) => s.id === state.currentId) ? state.currentId : state.spaces[0]?.id;
    $("#renameInput").value = getSpace(sel.value)?.name || "";

    $("#registeredTable").innerHTML = state.spaces.map((s) => {
      const t = state.snapshots[s.id];
      const meta = t ? t.levelMeta : api.LEVEL.FAULT;
      return `<tr>
        <td>${esc(s.name)}</td>
        <td class="mono">${esc(s.nodeId)}</td>
        <td class="mono">${esc(s.host)}:${esc(s.port)}</td>
        <td><span class="badge ${meta.tone}">${meta.label}</span></td>
        <td><button class="btn sm danger" data-del="${esc(s.id)}" type="button">삭제</button></td>
      </tr>`;
    }).join("");

    $$("[data-del]").forEach((b) => b.addEventListener("click", () => removeSpace(b.dataset.del)));

    const th = state.thresholds;
    $("#thBreathLow").value = th.breathLow;
    $("#thBreathHigh").value = th.breathHigh;
    $("#thCo2Caution").value = th.co2Caution;
    $("#thCo2Danger").value = th.co2Danger;
    $("#thTempHigh").value = th.tempHigh;
    $("#thMotion").value = th.motionTimeout;

    $("#prefMode").value = state.prefs.mode;
    $("#prefBaseUrl").value = state.prefs.baseUrl;
    $("#prefPoll").value = String(state.prefs.pollMs);
    $("#prefSound").checked = state.prefs.sound;
    $("#prefAutoLog").checked = state.prefs.autoLog;
  }

  function removeSpace(id) {
    if (state.spaces.length <= 1) return toast("최소 한 개의 공간은 유지해야 합니다.", "err");
    const s = getSpace(id);
    if (!s || !confirm(`${s.name} 연결 정보를 삭제할까요?`)) return;
    state.spaces = state.spaces.filter((x) => x.id !== id);
    delete state.snapshots[id];
    if (state.currentId === id) selectSpace(state.spaces[0].id, false);
    save(KEY.spaces, state.spaces);
    renderSettings();
    renderPicker();
    updateNavCounts();
    toast("공간을 삭제했습니다.", "ok");
  }

  /* ====================================================================== */
  /* 공간 선택 / 뷰 전환                                                     */
  /* ====================================================================== */

  function renderPicker() {
    const s = currentSpace();
    $("#pickName").textContent = s.name;
    $("#pickAddr").textContent = `${s.nodeId} · ${s.host}:${s.port}`;
    $("#pickerMenu").innerHTML = state.spaces.map((sp) => {
      const t = state.snapshots[sp.id];
      const meta = t ? t.levelMeta : api.LEVEL.FAULT;
      const c = toneColor(meta.tone);
      return `<button type="button" data-pick="${esc(sp.id)}">
        <span class="q-dot" style="background:${c}"></span>
        <span class="nm">${esc(sp.name)}</span>
        <span class="sc" style="color:${c}">${t && Number.isFinite(t.riskScore) ? Math.round(t.riskScore) : "—"}</span>
      </button>`;
    }).join("");
    $$("[data-pick]").forEach((b) =>
      b.addEventListener("click", () => {
        selectSpace(b.dataset.pick, false);
        $("#pickerMenu").classList.remove("open");
      })
    );
  }

  function selectSpace(id, goDashboard) {
    if (!getSpace(id)) return;
    state.currentId = id;
    localStorage.setItem(KEY.current, id);
    state.history = [];
    state.lastLevel = null;
    state.ackedAt = 0;
    if (api.config.mode === "demo") api.setScenario(getSpace(id).scenario || "occupied");
    api.setSpace(id);
    renderPicker();
    renderScenarioBar();
    if (goDashboard) switchView("dashboard");
  }

  const VIEW_META = {
    dashboard: ["통합 관제", "선택한 공간의 센서 융합 판단을 실시간으로 감시합니다."],
    spaces: ["공간 관리", "등록된 모든 공간의 위험도를 한 화면에서 비교합니다."],
    events: ["이벤트 로그", "상태 전이와 경보 이력을 조회하고 CSV로 내보냅니다."],
    settings: ["설정", "게이트웨이 연결, 판단 기준, 알림 방식을 관리합니다."],
  };

  function switchView(view) {
    state.view = view;
    $$("[data-view-panel]").forEach((p) => p.classList.toggle("active", p.dataset.viewPanel === view));
    $$(".rail-nav button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    if (view === "spaces") renderSpaces();
    if (view === "events") renderEvents();
    if (view === "settings") renderSettings();
    if (view === "dashboard") requestAnimationFrame(() => { drawChart(); if (state.telemetry) renderThermal(state.telemetry.thermal); });
    global.scrollTo({ top: 0, behavior: "smooth" });
  }

  function updateNavCounts() {
    const open = state.events.filter((e) => !e.acked && ["caution", "danger", "emergency", "fault"].includes(e.level)).length;
    const el = $("#navEventCount");
    el.textContent = open;
    el.style.display = open ? "" : "none";

    $("#railSource").textContent = api.config.mode === "demo" ? "데모" : "게이트웨이";
    $("#railSpaces").textContent = `${state.spaces.length}개`;
    const railOpen = $("#railOpen");
    railOpen.textContent = `${open}건`;
    railOpen.style.color = open ? cssVar("--caution") : cssVar("--normal");
  }

  /* ====================================================================== */
  /* 데모 시나리오 바                                                        */
  /* ====================================================================== */

  function renderScenarioBar() {
    const bar = $("#demoConsole");
    bar.style.display = api.config.mode === "demo" ? "" : "none";
    const cur = api.currentScenario();
    $("#scenarioBtns").innerHTML = Object.entries(api.SCENARIOS)
      .map(([k, v]) => `<button type="button" data-scen="${k}" class="${k === cur ? "active" : ""}">${esc(v.label)}</button>`)
      .join("");
    $$("[data-scen]").forEach((b) =>
      b.addEventListener("click", () => {
        api.setScenario(b.dataset.scen);
        const s = currentSpace();
        s.scenario = b.dataset.scen;
        save(KEY.spaces, state.spaces);
        state.history = [];
        state.lastLevel = null;
        renderScenarioBar();
      })
    );
  }

  /* ====================================================================== */
  /* 경보음 (WebAudio — 외부 파일 불필요)                                    */
  /* ====================================================================== */

  let audioCtx = null;
  let lastBeep = 0;

  function beep(level) {
    if (!state.prefs.sound) return;
    if (!["DANGER", "EMERGENCY"].includes(level)) return;
    if (Date.now() - lastBeep < 4000) return;
    lastBeep = Date.now();
    try {
      audioCtx = audioCtx || new (global.AudioContext || global.webkitAudioContext)();
      const t0 = audioCtx.currentTime;
      [0, 0.22].forEach((off) => {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.value = level === "EMERGENCY" ? 980 : 720;
        gain.gain.setValueAtTime(0.0001, t0 + off);
        gain.gain.exponentialRampToValueAtTime(0.16, t0 + off + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + off + 0.18);
        osc.connect(gain).connect(audioCtx.destination);
        osc.start(t0 + off);
        osc.stop(t0 + off + 0.2);
      });
    } catch { /* 오디오 미지원 환경은 무시 */ }
  }

  /* ====================================================================== */
  /* 텔레메트리 수신                                                         */
  /* ====================================================================== */

  function onTelemetry(payload) {
    const chip = $("#liveChip");

    if (!payload.ok) {
      state.connError = payload.error;
      chip.className = "live-chip down";
      chip.innerHTML = `<span class="dot"></span>게이트웨이 응답 없음`;
      $("#alertBar").className = "alert-bar show fault";
      $("#alertTitle").textContent = "통신 오류: 게이트웨이에 연결할 수 없습니다";
      $("#alertDetail").textContent = `${api.config.baseUrl} · ${payload.error}`;
      return;
    }

    state.connError = null;
    const t = payload.telemetry;
    state.telemetry = t;
    state.snapshots[state.currentId] = t;

    chip.className = `live-chip ${t.source === "demo" ? "demo" : "live"}`;
    chip.innerHTML = `<span class="dot"></span>${t.source === "demo" ? "데모 데이터" : "실시간 수신"}`;

    // 차트 히스토리
    state.history.push({
      ts: t.ts,
      breathRpm: t.breathRpm,
      tempMaxC: t.tempMaxC,
      co2Scaled: Number.isFinite(t.co2Ppm) ? t.co2Ppm / 100 : null,
      riskScore: t.riskScore,
    });
    if (state.history.length > HISTORY_CAP) state.history.shift();

    logLevelTransition(t);
    beep(t.level);
    renderDashboard(t);
    if (state.view === "dashboard") drawChart();
    if (state.view === "spaces") renderSpaces();
    renderPicker();
    updateAge();
  }

  function updateAge() {
    const el = $("#ageReadout");
    if (!state.telemetry) { el.textContent = "수신 대기"; return; }
    const s = Math.round((Date.now() - state.telemetry.ts) / 1000);
    el.textContent = `${s}초 전 갱신`;
    el.classList.toggle("stale", s > Math.max(6, (api.config.pollMs / 1000) * 3));
  }

  /* ====================================================================== */
  /* 초기화 / 바인딩                                                         */
  /* ====================================================================== */

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    state.prefs.theme = theme;
    save(KEY.prefs, state.prefs);
    $("#themeBtn").innerHTML = theme === "dark" ? ico.sun : ico.moon;
    renderChartLegend();
    if (state.telemetry) renderDashboard(state.telemetry);
    drawChart();
  }

  function bind() {
    // 아이콘 주입
    $("#brandIcon").innerHTML = ico.shield;
    $("#navDashIcon").innerHTML = ico.gauge;
    $("#navSpaceIcon").innerHTML = ico.grid;
    $("#navEventIcon").innerHTML = ico.list;
    $("#navSetIcon").innerHTML = ico.cog;
    $("#breathIcon").innerHTML = ico.lungs;
    $("#tempIcon").innerHTML = ico.thermo;
    $("#co2Icon").innerHTML = ico.wind;
    $("#motionIcon").innerHTML = ico.motion;
    $("#pickChev").innerHTML = ico.chev;
    $("#privacyIcon").innerHTML = ico.eyeOff;
    $("#fullBtn").innerHTML = ico.expand;
    $("#demoIcon").innerHTML = ico.flask;
    $("#alertIcon").innerHTML = ico.alert;

    // 내비게이션
    $$(".rail-nav button").forEach((b) => b.addEventListener("click", () => switchView(b.dataset.view)));
    $$("[data-go]").forEach((b) => b.addEventListener("click", () => switchView(b.dataset.go)));

    // 공간 선택
    $("#pickerBtn").addEventListener("click", (e) => {
      e.stopPropagation();
      $("#pickerMenu").classList.toggle("open");
    });
    document.addEventListener("click", () => $("#pickerMenu").classList.remove("open"));
    $("#pickerMenu").addEventListener("click", (e) => e.stopPropagation());

    // 테마 / 전체화면
    $("#themeBtn").addEventListener("click", () =>
      applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark")
    );
    $("#fullBtn").addEventListener("click", () => {
      document.body.classList.toggle("wall");
      if (document.body.classList.contains("wall") && !document.fullscreenElement) {
        document.documentElement.requestFullscreen?.().catch(() => {});
      } else if (document.fullscreenElement) {
        document.exitFullscreen?.().catch(() => {});
      }
      requestAnimationFrame(() => { drawChart(); if (state.telemetry) renderThermal(state.telemetry.thermal); });
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") document.body.classList.remove("wall");
    });

    // 경보 확인
    $("#alertAck").addEventListener("click", () => {
      state.ackedAt = Date.now();
      const t = state.telemetry;
      pushEvent({
        spaceId: state.currentId,
        level: "info",
        message: "관리자 경보 확인",
        detail: t ? `${t.levelMeta.label} · 위험도 ${Math.round(t.riskScore ?? 0)}` : "",
        risk: t?.riskScore ?? null,
      });
      if (t) renderAlert(t);
      toast("경보를 확인 처리했습니다.", "ok");
    });

    // 차트 호버
    const canvas = $("#trendCanvas");
    canvas.addEventListener("mousemove", (e) => {
      const r = canvas.getBoundingClientRect();
      const padL = 38, padR = 40;
      const W = r.width - padL - padR;
      const ratio = (e.clientX - r.left - padL) / W;
      chartState.hoverIdx = Math.round(ratio * (state.history.length - 1));
      if (chartState.hoverIdx < 0 || chartState.hoverIdx >= state.history.length) chartState.hoverIdx = -1;
      drawChart();
    });
    canvas.addEventListener("mouseleave", () => { chartState.hoverIdx = -1; drawChart(); });

    // 이벤트 필터
    ["filterSpace", "filterLevel"].forEach((id) => $(`#${id}`).addEventListener("change", renderEvents));
    $("#filterSearch").addEventListener("input", renderEvents);
    $("#filterReset").addEventListener("click", () => {
      $("#filterSpace").value = "all";
      $("#filterLevel").value = "all";
      $("#filterSearch").value = "";
      renderEvents();
    });
    $("#exportCsv").addEventListener("click", exportCsv);
    $("#clearEvents").addEventListener("click", () => {
      if (!confirm("저장된 이벤트를 모두 삭제할까요?")) return;
      state.events = [];
      save(KEY.events, state.events);
      renderEvents();
      renderRecentEvents();
      updateNavCounts();
      toast("이벤트를 초기화했습니다.", "ok");
    });

    // 연결 테스트 / 공간 등록
    $("#testConnBtn").addEventListener("click", async () => {
      const line = $("#connResult");
      const host = $("#newHost").value.trim();
      const port = $("#newPort").value.trim();
      line.className = "result-line busy";
      line.textContent = "게이트웨이 응답을 확인하는 중입니다…";
      const res = await api.checkHealth(host, port);
      if (res.ok) {
        line.className = "result-line ok";
        line.textContent = `응답 확인 (${Math.round(res.latencyMs)} ms). 공간을 등록할 수 있습니다.`;
      } else {
        line.className = "result-line err";
        line.textContent = `응답 없음 (${res.error}). 주소·포트·/health 라우트·CORS 설정을 확인하세요.`;
      }
    });

    $("#connectForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const name = $("#newName").value.trim();
      const nodeId = $("#newNodeId").value.trim();
      const host = $("#newHost").value.trim();
      const port = $("#newPort").value.trim() || "8000";
      if (!name || !nodeId || !host) return toast("필수 항목을 모두 입력하세요.", "err");
      if (state.spaces.some((s) => s.nodeId.toLowerCase() === nodeId.toLowerCase()))
        return toast("이미 등록된 노드 ID입니다.", "err");
      const id = `N${Date.now().toString(36).slice(-5).toUpperCase()}`;
      state.spaces.push({ id, name, nodeId, host, port, scenario: "occupied" });
      save(KEY.spaces, state.spaces);
      pushEvent({ spaceId: id, level: "info", message: "새 공간 등록", detail: `${host}:${port} · ${nodeId}`, risk: null });
      e.currentTarget.reset();
      $("#newPort").value = "8000";
      renderSettings();
      renderPicker();
      toast("공간을 등록했습니다.", "ok");
    });

    // 이름 변경
    $("#renameSelect").addEventListener("change", () => {
      $("#renameInput").value = getSpace($("#renameSelect").value)?.name || "";
    });
    $("#renameBtn").addEventListener("click", () => {
      const s = getSpace($("#renameSelect").value);
      const name = $("#renameInput").value.trim();
      if (!s || !name) return toast("공간과 이름을 확인하세요.", "err");
      s.name = name;
      save(KEY.spaces, state.spaces);
      renderSettings();
      renderPicker();
      toast("공간 이름을 변경했습니다.", "ok");
    });
    $("#setCurrentBtn").addEventListener("click", () => {
      selectSpace($("#renameSelect").value, true);
      toast("관제 화면 대상 공간을 변경했습니다.", "ok");
    });

    // 임계값
    $("#saveThresholds").addEventListener("click", async () => {
      const next = {
        breathLow: Number($("#thBreathLow").value),
        breathHigh: Number($("#thBreathHigh").value),
        co2Caution: Number($("#thCo2Caution").value),
        co2Danger: Number($("#thCo2Danger").value),
        tempHigh: Number($("#thTempHigh").value),
        tempLow: state.thresholds.tempLow,
        motionTimeout: Number($("#thMotion").value),
      };
      if (next.breathLow >= next.breathHigh) return toast("저호흡 기준은 과호흡 기준보다 작아야 합니다.", "err");
      if (next.co2Caution >= next.co2Danger) return toast("CO₂ 주의 기준은 위험 기준보다 작아야 합니다.", "err");
      state.thresholds = next;
      save(KEY.thresholds, next);
      const res = await api.pushThresholds(next);
      if (state.telemetry) renderDashboard(state.telemetry);
      toast(res.ok && api.config.mode === "live"
        ? "판단 기준을 게이트웨이에 전송했습니다."
        : "판단 기준을 저장했습니다.", "ok");
    });

    // 연결 모드 / 알림
    $("#savePrefs").addEventListener("click", () => {
      state.prefs.mode = $("#prefMode").value;
      state.prefs.baseUrl = $("#prefBaseUrl").value.trim();
      state.prefs.pollMs = Number($("#prefPoll").value);
      state.prefs.sound = $("#prefSound").checked;
      state.prefs.autoLog = $("#prefAutoLog").checked;
      save(KEY.prefs, state.prefs);
      api.configure({
        mode: state.prefs.mode,
        baseUrl: state.prefs.baseUrl,
        pollMs: state.prefs.pollMs,
      });
      state.history = [];
      state.lastLevel = null;
      state.snapshots = {};
      renderScenarioBar();
      updateNavCounts();
      toast(state.prefs.mode === "live"
        ? "실시간 모드로 전환했습니다. 게이트웨이 응답을 기다립니다."
        : "데모 모드로 전환했습니다.", "ok");
    });

    // 리사이즈
    let rt = null;
    global.addEventListener("resize", () => {
      clearTimeout(rt);
      rt = setTimeout(() => {
        drawChart();
        if (state.telemetry) renderThermal(state.telemetry.thermal);
      }, 120);
    });
  }

  function init() {
    applyTheme(state.prefs.theme || "dark");
    bind();

    api.configure({
      mode: state.prefs.mode,
      baseUrl: state.prefs.baseUrl,
      pollMs: state.prefs.pollMs,
    });
    api.subscribe(onTelemetry);

    renderPicker();
    renderChartLegend();
    renderRecentEvents();
    updateNavCounts();
    renderScenarioBar();

    const sp = currentSpace();
    if (api.config.mode === "demo") api.setScenario(sp.scenario || "occupied");
    api.setSpace(sp.id);

    setInterval(updateAge, 1000);
    switchView("dashboard");
  }

  document.addEventListener("DOMContentLoaded", init);
})(window);
