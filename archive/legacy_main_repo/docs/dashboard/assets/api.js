/* ==========================================================================
   SafeNest Console - api.js
   --------------------------------------------------------------------------
   백엔드(라즈베리파이 FastAPI 게이트웨이) 연동 계층.

   설계 원칙
   1) 화면 코드(app.js)는 절대 fetch를 직접 호출하지 않는다. 이 파일의
      SafeNest.api 만 호출한다. 따라서 백엔드가 붙어도 UI 코드는 그대로다.
   2) 게이트웨이 응답은 ondevice_ai/src/integrated_node/safenest_risk_engine.py 의
      evaluate_risk() 반환 dict + SafeNestRiskOutput 계약을 그대로 따른다고 가정한다.
      normalizeTelemetry()가 그 원본 dict를 화면용 뷰모델로 1:1 변환한다.
   3) 백엔드가 없을 때는 MockSource가 동일한 원본 dict를 생성한다.
      즉 데모 경로와 실서비스 경로가 같은 파서를 통과한다 (시연용 가짜 UI가 아님).

   전환 방법: 설정 화면에서 "실시간(게이트웨이)" 선택 → api.configure({mode:'live'})
   ========================================================================== */

(function (global) {
  "use strict";

  const SafeNest = (global.SafeNest = global.SafeNest || {});

  /* ---------------------------------------------------------------------- */
  /* 상수: 등급 체계 (백엔드 SafeNestRiskOutput.level 과 동일 어휘)          */
  /* ---------------------------------------------------------------------- */

  const LEVEL = {
    NORMAL: {
      key: "NORMAL", label: "정상", tone: "normal",
      action: "조치 불필요 · 정상 감시 중",
    },
    CAUTION: {
      key: "CAUTION", label: "주의", tone: "caution",
      action: "환기 또는 상태 확인이 필요합니다",
    },
    DANGER: {
      key: "DANGER", label: "위험", tone: "danger",
      action: "작업자 상태를 즉시 확인하세요",
    },
    EMERGENCY: {
      key: "EMERGENCY", label: "긴급", tone: "emergency",
      action: "즉시 구조를 요청하세요",
    },
    FAULT: {
      key: "FAULT", label: "센서 이상", tone: "fault",
      action: "센서·통신 상태를 점검하세요",
    },
  };

  /** 백엔드 reasons[] 코드를 한국어 설명으로 매핑 (미등록 코드는 원문 노출). */
  const REASON_TEXT = {
    APNEA_SUSPECTED: "무호흡 의심",
    LOW_BREATH_RATE: "저호흡",
    HIGH_BREATH_RATE: "과호흡",
    NO_MOTION_TIMEOUT: "장시간 무움직임",
    CO2_ELEVATED: "CO₂ 상승",
    CO2_CRITICAL: "CO₂ 위험 수준",
    CO2_SLOPE_HIGH: "CO₂ 급상승 추세",
    HIGH_BODY_TEMP: "고체온 의심",
    LOW_BODY_TEMP: "저체온 의심",
    HUMAN_FALL: "쓰러짐 자세 추정",
    PRESENCE_CONFIRMED: "재실 확인",
    NO_PRESENCE: "재실 없음",
    SENSOR_STALE: "센서 데이터 지연",
    NO_INPUT_WINDOW: "분석 윈도 미충족",
    TFLITE_MODEL_FILE_MISSING: "AI 모델 파일 없음",
    MMWAVE_MODEL_DISABLED_UNVERIFIED: "mmWave 모델 미검증(규칙 대체)",
    ALL_SENSORS_MISSING: "전체 센서 수신 불가",
  };

  /** 정상 범위/임계 구간 기본값. 설정 화면에서 덮어쓴다. */
  const DEFAULT_THRESHOLDS = {
    breathLow: 10,      // rpm 미만이면 저호흡
    breathHigh: 25,     // rpm 초과면 과호흡
    co2Caution: 1500,   // ppm
    co2Danger: 2500,    // ppm
    tempHigh: 38.0,     // ℃
    tempLow: 34.0,      // ℃
    motionTimeout: 30,  // 초
  };

  /* ---------------------------------------------------------------------- */
  /* 설정                                                                    */
  /* ---------------------------------------------------------------------- */

  const config = {
    mode: "demo",                 // 'demo' | 'live'
    baseUrl: "http://192.168.1.44:8000",
    pollMs: 2000,
    timeoutMs: 3500,
    useStream: true,              // 게이트웨이가 SSE를 제공하면 폴링 대신 사용
  };

  /** 게이트웨이 REST 경로. 백엔드 구현 시 이 목록이 곧 명세다. */
  const ROUTES = {
    health: () => `/health`,
    spaces: () => `/api/v1/spaces`,
    telemetry: (id) => `/api/v1/spaces/${encodeURIComponent(id)}/telemetry`,
    stream: (id) => `/api/v1/spaces/${encodeURIComponent(id)}/stream`,
    thermal: (id) => `/api/v1/spaces/${encodeURIComponent(id)}/thermal`,
    events: () => `/api/v1/events`,
    ackEvent: (id) => `/api/v1/events/${encodeURIComponent(id)}/ack`,
    thresholds: () => `/api/v1/config/thresholds`,
  };

  /* ---------------------------------------------------------------------- */
  /* 유틸                                                                    */
  /* ---------------------------------------------------------------------- */

  function joinUrl(base, path) {
    const b = /^https?:\/\//i.test(base) ? base : `http://${base}`;
    return b.replace(/\/+$/, "") + path;
  }

  function normalizeBaseUrl(host, port) {
    if (!host) return null;
    const raw = /^https?:\/\//i.test(host) ? host : `http://${host}`;
    try {
      const url = new URL(raw);
      if (port) url.port = String(port);
      return url.origin;
    } catch {
      return null;
    }
  }

  async function request(path, options = {}, base = config.baseUrl) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs || config.timeoutMs);
    const started = performance.now();
    try {
      const res = await fetch(joinUrl(base, path), {
        cache: "no-store",
        signal: controller.signal,
        headers: { Accept: "application/json", ...(options.headers || {}) },
        method: options.method || "GET",
        body: options.body ? JSON.stringify(options.body) : undefined,
        ...(options.body ? { headers: { "Content-Type": "application/json", Accept: "application/json" } } : {}),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = res.status === 204 ? null : await res.json();
      return { ok: true, data, latencyMs: performance.now() - started };
    } catch (err) {
      return {
        ok: false,
        error: err.name === "AbortError" ? "TIMEOUT" : String(err.message || err),
        latencyMs: performance.now() - started,
      };
    } finally {
      clearTimeout(timer);
    }
  }

  const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);

  /* ---------------------------------------------------------------------- */
  /* 정규화: 게이트웨이 원본 dict → 화면 뷰모델                              */
  /* ---------------------------------------------------------------------- */

  /**
   * 입력(게이트웨이 응답) 기대 형태 — risk engine 출력 + raw 센서값 블록:
   * {
   *   timestamp_s, risk_score, status_str, status_code, is_emergency,
   *   reasons: [...], sensor_quality: {thermal, co2, mmwave, pir},
   *   system_status: "OK"|"DEGRADED"|"FAULT",
   *   derived_metrics: { breath_rpm, breath_confidence, heart_bpm, heart_valid,
   *                      presence_confirmed, co2_slope_ppm_per_min, mmwave_state, ... },
   *   raw: { co2_ppm, temp_max_c, temp_avg_c, motion, motion_age_sec, occupants },
   *   thermal: { w, h, data: [...], min_c, max_c, box: {x,y,w,h}, hot: {x,y} }
   * }
   */
  function normalizeTelemetry(raw, meta = {}) {
    const d = (raw && raw.derived_metrics) || {};
    const q = (raw && raw.sensor_quality) || {};
    const r = (raw && raw.raw) || {};

    const systemStatus = raw?.system_status || "OK";
    let level = raw?.is_emergency
      ? "EMERGENCY"
      : raw?.status_str || raw?.level || "NORMAL";
    if (systemStatus === "FAULT") level = "FAULT";
    if (!LEVEL[level]) level = "FAULT";

    const tsSec = num(raw?.timestamp_s) ?? num(raw?.timestamp) ?? Date.now() / 1000;

    return {
      ts: tsSec * 1000,
      riskScore: num(raw?.risk_score),
      level,
      levelMeta: LEVEL[level],
      systemStatus,
      isEmergency: !!raw?.is_emergency,
      reasons: Array.isArray(raw?.reasons) ? raw.reasons : [],

      presence: d.presence_confirmed === true,
      occupants: num(r.occupants),

      breathRpm: num(d.breath_rpm),
      breathConfidence: num(d.breath_confidence) ?? 0,
      breathSource: d.breath_source || null,
      mmwaveState: d.mmwave_state || null,
      windowReady: d.mmwave_window_ready !== false,

      heartBpm: num(d.heart_bpm),
      heartValid: d.heart_valid === true,

      co2Ppm: num(r.co2_ppm),
      co2Slope: num(d.co2_slope_ppm_per_min),

      tempMaxC: num(r.temp_max_c),
      tempAvgC: num(r.temp_avg_c),

      motion: r.motion === 1 || r.motion === true,
      motionAgeSec: num(r.motion_age_sec),

      thermal: raw?.thermal || null,

      quality: {
        mmwave: num(q.mmwave) ?? 0,
        thermal: num(q.thermal) ?? 0,
        co2: num(q.co2) ?? 0,
        pir: num(q.pir) ?? 0,
      },

      latencyMs: num(meta.latencyMs),
      source: meta.source || config.mode,
      raw,
    };
  }

  /** 센서 4종의 quality gate 평균을 신뢰도(%)로 환산. */
  function fusionConfidence(t) {
    if (!t) return 0;
    const q = t.quality;
    const avg = (q.mmwave + q.thermal + q.co2 + q.pir) / 4;
    return Math.round(avg * 100);
  }

  function reasonText(code) {
    return REASON_TEXT[code] || code;
  }

  /* ---------------------------------------------------------------------- */
  /* Mock 소스: 백엔드와 동일한 원본 dict를 생성                             */
  /* ---------------------------------------------------------------------- */

  const SCENARIOS = {
    "empty": { label: "정상 · 미재실", presence: false, level: "NORMAL" },
    "occupied": { label: "정상 · 재실", presence: true, level: "NORMAL" },
    "co2": { label: "주의 · CO₂ 상승", presence: true, level: "CAUTION" },
    "apnea": { label: "위험 · 호흡 이상", presence: true, level: "DANGER" },
    "collapse": { label: "긴급 · 복합 위험", presence: true, level: "EMERGENCY" },
    "fault": { label: "센서 이상 · 통신 두절", presence: false, level: "FAULT" },
  };

  const SCEN_BASE = {
    empty: { risk: 4, breath: null, co2: 610, tempMax: 24.3, tempAvg: 23.6, motion: 0, motionAge: 240, reasons: ["NO_PRESENCE"] },
    occupied: { risk: 18, breath: 16, co2: 820, tempMax: 36.7, tempAvg: 31.8, motion: 1, motionAge: 3, reasons: ["PRESENCE_CONFIRMED"] },
    co2: { risk: 52, breath: 17.4, co2: 1620, tempMax: 36.9, tempAvg: 32.2, motion: 1, motionAge: 6, reasons: ["PRESENCE_CONFIRMED", "CO2_ELEVATED", "CO2_SLOPE_HIGH"] },
    apnea: { risk: 76, breath: 7.8, co2: 980, tempMax: 37.2, tempAvg: 32.9, motion: 0, motionAge: 34, reasons: ["PRESENCE_CONFIRMED", "LOW_BREATH_RATE", "NO_MOTION_TIMEOUT"] },
    collapse: { risk: 94, breath: 6.4, co2: 1980, tempMax: 39.2, tempAvg: 34.5, motion: 0, motionAge: 48, reasons: ["PRESENCE_CONFIRMED", "APNEA_SUSPECTED", "HUMAN_FALL", "HIGH_BODY_TEMP", "NO_MOTION_TIMEOUT", "CO2_ELEVATED"] },
    fault: { risk: null, breath: null, co2: null, tempMax: null, tempAvg: null, motion: null, motionAge: null, reasons: ["ALL_SENSORS_MISSING", "SENSOR_STALE"] },
  };

  const THERM_W = 80;
  const THERM_H = 62;

  function makeThermalFrame(scenario, phase) {
    if (scenario === "fault") return null;
    const base = SCEN_BASE[scenario];
    const ambient = scenario === "empty" ? 23.4 : 25.6;
    const data = new Float32Array(THERM_W * THERM_H);
    const hasBody = base.tempMax !== null && scenario !== "empty";

    // 인체 중심 좌표 (긴급 시나리오는 쓰러진 자세라 낮고 넓게)
    const collapsed = scenario === "collapse";
    const cx = collapsed ? 0.5 + Math.sin(phase * 0.4) * 0.01 : 0.48 + Math.sin(phase * 0.6) * 0.012;
    const cy = collapsed ? 0.72 : 0.46;
    const rx = collapsed ? 0.30 : 0.13;
    const ry = collapsed ? 0.13 : 0.30;
    const peak = base.tempMax || ambient;

    for (let y = 0; y < THERM_H; y++) {
      for (let x = 0; x < THERM_W; x++) {
        const nx = x / THERM_W;
        const ny = y / THERM_H;
        // 배경: 완만한 구배 + 잔노이즈
        let v = ambient
          + Math.sin(nx * 3.1 + phase * 0.08) * 0.5
          + Math.cos(ny * 2.4 - phase * 0.05) * 0.4
          + (Math.random() - 0.5) * 0.22;
        if (hasBody) {
          const dx = (nx - cx) / rx;
          const dy = (ny - cy) / ry;
          const dist = dx * dx + dy * dy;
          if (dist < 2.6) {
            const g = Math.exp(-dist * 1.15);
            v += (peak - ambient) * g;
          }
        }
        data[y * THERM_W + x] = v;
      }
    }

    let min = Infinity, max = -Infinity, hotIdx = 0;
    for (let i = 0; i < data.length; i++) {
      if (data[i] < min) min = data[i];
      if (data[i] > max) { max = data[i]; hotIdx = i; }
    }

    return {
      w: THERM_W,
      h: THERM_H,
      data: Array.from(data),
      min_c: min,
      max_c: max,
      hot: { x: (hotIdx % THERM_W) / THERM_W, y: Math.floor(hotIdx / THERM_W) / THERM_H },
      box: hasBody
        ? { x: cx - rx * 1.25, y: cy - ry * 1.25, w: rx * 2.5, h: ry * 2.5 }
        : null,
    };
  }

  const MockSource = {
    scenario: "occupied",
    phase: 0,
    co2Drift: 0,

    setScenario(key) {
      if (!SCENARIOS[key]) return;
      this.scenario = key;
      this.phase = 0;
      this.co2Drift = 0;
    },

    /** 게이트웨이가 반환할 dict와 동일한 형태를 만든다. */
    sample() {
      this.phase += 1;
      const s = this.scenario;
      const b = SCEN_BASE[s];
      const jitter = (amp) => (Math.random() - 0.5) * amp;

      if (s === "fault") {
        return {
          timestamp_s: Date.now() / 1000,
          risk_score: 0,
          status_str: "NORMAL",
          status_code: 0,
          is_emergency: false,
          reasons: b.reasons,
          sensor_quality: { thermal: 0, co2: 0.2, mmwave: 0, pir: 0.5 },
          system_status: "FAULT",
          derived_metrics: {
            presence_confirmed: false,
            breath_rpm: null, breath_confidence: 0, breath_source: null,
            heart_bpm: null, heart_valid: false,
            mmwave_state: "READ_TIMEOUT", mmwave_window_ready: false,
            co2_slope_ppm_per_min: null,
          },
          raw: { co2_ppm: null, temp_max_c: null, temp_avg_c: null, motion: null, motion_age_sec: null, occupants: null },
          thermal: null,
        };
      }

      // CO2는 시나리오별로 서서히 이동시켜 추세 그래프가 살아 있게 한다.
      if (s === "co2") this.co2Drift = Math.min(420, this.co2Drift + 6);
      else if (s === "collapse") this.co2Drift = Math.min(300, this.co2Drift + 4);
      else this.co2Drift *= 0.94;

      const breath = b.breath === null ? null : Math.max(0, b.breath + jitter(1.1));
      const co2 = b.co2 === null ? null : Math.round(b.co2 + this.co2Drift + jitter(28));
      const tempMax = b.tempMax === null ? null : b.tempMax + jitter(0.16);
      const tempAvg = b.tempAvg === null ? null : b.tempAvg + jitter(0.12);
      const motionAge = b.motion === 1 ? Math.max(0, b.motionAge + jitter(2)) : b.motionAge + 2;
      const risk = b.risk === null ? null : Math.max(0, Math.min(100, b.risk + jitter(3.2)));

      const level = SCENARIOS[s].level;
      const isEmergency = level === "EMERGENCY";

      return {
        timestamp_s: Date.now() / 1000,
        risk_score: risk,
        status_str: isEmergency ? "DANGER" : level,
        status_code: level === "DANGER" || isEmergency ? 2 : level === "CAUTION" ? 1 : 0,
        is_emergency: isEmergency,
        reasons: b.reasons,
        sensor_quality: {
          thermal: 1,
          co2: 1,
          mmwave: SCENARIOS[s].presence && breath ? 1 : 0,
          pir: 1,
        },
        system_status: "OK",
        derived_metrics: {
          presence_confirmed: SCENARIOS[s].presence,
          breath_rpm: breath,
          breath_confidence: breath ? 0.86 + Math.random() * 0.1 : 0,
          breath_source: breath ? "phase_zero_crossing" : null,
          heart_bpm: SCENARIOS[s].presence ? 74 + jitter(6) : null,
          heart_valid: SCENARIOS[s].presence,
          mmwave_state: "VALID",
          mmwave_window_ready: true,
          co2_slope_ppm_per_min: s === "co2" ? 41 + jitter(8) : jitter(6),
        },
        raw: {
          co2_ppm: co2,
          temp_max_c: tempMax,
          temp_avg_c: tempAvg,
          motion: b.motion,
          motion_age_sec: motionAge,
          occupants: SCENARIOS[s].presence ? 1 : 0,
        },
        thermal: makeThermalFrame(s, this.phase),
      };
    },
  };

  /* ---------------------------------------------------------------------- */
  /* 구독 루프: 폴링 또는 SSE. 화면은 subscribe()만 알면 된다.               */
  /* ---------------------------------------------------------------------- */

  let timer = null;
  let stream = null;
  let listeners = [];
  let activeSpaceId = null;

  function emit(payload) {
    listeners.forEach((fn) => {
      try { fn(payload); } catch (e) { console.error("[SafeNest] listener error", e); }
    });
  }

  async function pollOnce() {
    if (config.mode === "demo") {
      emit({ ok: true, telemetry: normalizeTelemetry(MockSource.sample(), { latencyMs: 0, source: "demo" }) });
      return;
    }
    const res = await request(ROUTES.telemetry(activeSpaceId));
    if (res.ok) {
      emit({ ok: true, telemetry: normalizeTelemetry(res.data, { latencyMs: res.latencyMs, source: "live" }) });
    } else {
      emit({ ok: false, error: res.error, latencyMs: res.latencyMs });
    }
  }

  function stopLoop() {
    if (timer) { clearInterval(timer); timer = null; }
    if (stream) { stream.close(); stream = null; }
  }

  function startLoop() {
    stopLoop();
    if (config.mode === "live" && config.useStream && "EventSource" in global) {
      try {
        stream = new EventSource(joinUrl(config.baseUrl, ROUTES.stream(activeSpaceId)));
        stream.onmessage = (ev) => {
          try {
            emit({ ok: true, telemetry: normalizeTelemetry(JSON.parse(ev.data), { source: "live" }) });
          } catch (e) {
            emit({ ok: false, error: "PARSE_ERROR" });
          }
        };
        stream.onerror = () => {
          // SSE 실패 시 폴링으로 자동 강등
          stream.close();
          stream = null;
          timer = setInterval(pollOnce, config.pollMs);
        };
        return;
      } catch {
        stream = null;
      }
    }
    pollOnce();
    timer = setInterval(pollOnce, config.pollMs);
  }

  /* ---------------------------------------------------------------------- */
  /* 공개 API                                                                */
  /* ---------------------------------------------------------------------- */

  SafeNest.api = {
    LEVEL,
    SCENARIOS,
    DEFAULT_THRESHOLDS,
    config,
    ROUTES,

    configure(patch = {}) {
      Object.assign(config, patch);
      if (activeSpaceId) startLoop();
    },

    setSpace(spaceId) {
      activeSpaceId = spaceId;
      startLoop();
    },

    subscribe(fn) {
      listeners.push(fn);
      return () => { listeners = listeners.filter((l) => l !== fn); };
    },

    stop: stopLoop,
    refresh: pollOnce,

    setScenario(key) {
      MockSource.setScenario(key);
      if (config.mode === "demo") pollOnce();
    },
    currentScenario: () => MockSource.scenario,

    /**
     * 구독 루프를 건드리지 않고 특정 시나리오의 표본 1개를 얻는다.
     * (공간 관리 화면에서 아직 관측되지 않은 공간의 미리보기를 만들 때 사용)
     */
    sampleScenario(key) {
      const prev = { s: MockSource.scenario, p: MockSource.phase, d: MockSource.co2Drift };
      MockSource.scenario = SCENARIOS[key] ? key : "occupied";
      const raw = MockSource.sample();
      MockSource.scenario = prev.s;
      MockSource.phase = prev.p;
      MockSource.co2Drift = prev.d;
      return normalizeTelemetry(raw, { latencyMs: 0, source: "demo" });
    },

    /** 게이트웨이 헬스체크. 설정 화면의 "연결 테스트"가 사용한다. */
    async checkHealth(host, port) {
      const base = normalizeBaseUrl(host, port);
      if (!base) return { ok: false, error: "INVALID_ADDRESS" };
      return request(ROUTES.health(), { timeoutMs: 3000 }, base);
    },

    /** 아래 4개는 live 모드에서만 실제 호출, demo에서는 로컬 처리로 대체된다. */
    async fetchSpaces() {
      if (config.mode === "demo") return { ok: false, error: "DEMO_MODE" };
      return request(ROUTES.spaces());
    },
    async fetchEvents(params = {}) {
      if (config.mode === "demo") return { ok: false, error: "DEMO_MODE" };
      const qs = new URLSearchParams(params).toString();
      return request(ROUTES.events() + (qs ? `?${qs}` : ""));
    },
    async ackEvent(eventId) {
      if (config.mode === "demo") return { ok: true, data: null };
      return request(ROUTES.ackEvent(eventId), { method: "POST" });
    },
    async pushThresholds(thresholds) {
      if (config.mode === "demo") return { ok: true, data: null };
      return request(ROUTES.thresholds(), { method: "PUT", body: thresholds });
    },

    normalizeTelemetry,
    normalizeBaseUrl,
    fusionConfidence,
    reasonText,
  };
})(window);
