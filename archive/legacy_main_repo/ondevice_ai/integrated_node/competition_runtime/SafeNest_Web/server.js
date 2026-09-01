"use strict";

const express = require("express");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const QRCode = require("qrcode");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

loadEnv(path.join(__dirname, ".env"));
const app = express();
const PORT = Number(process.env.PORT || 3000);
const JWT_SECRET = process.env.JWT_SECRET || "development-only-secret-change-me";
const SENSOR_API_KEY = process.env.SENSOR_API_KEY || "dev-sensor-key-change-me";
const RPI_BRIDGE_URL = String(process.env.RPI_BRIDGE_URL || "http://127.0.0.1:8080").replace(/\/$/, "");
const RPI_SPACE_ID = process.env.RPI_SPACE_ID || "A01";
const RPI_POLL_MS = Math.max(250, Number(process.env.RPI_POLL_MS || 1000));
const RPI_OFFLINE_GRACE_MS = Math.max(5000, Number(process.env.RPI_OFFLINE_GRACE_MS || 30000));
const STORE_FILE = path.join(__dirname, "data", "store.json");
const clients = new Set();
const bridge = { ok:false, lastSuccessAt:null, lastLiveAt:null, error:"연결 대기", sensorRevision:null, lastMotionAt:Date.now(), waitingNotified:false, timer:null };

const initialSpaces = [
  space("A01", "밀폐공간 A-01", "SN-A01", "192.168.0.21", "normal-occupied", { co2:820, temperature:25.4, bodyTemperature:36.7, breathRate:16, motion:true, occupied:true }),
  space("B02", "통학차량 B-02", "SN-B02", "192.168.0.22", "normal-empty", { co2:610, temperature:25.1, bodyTemperature:null, breathRate:null, motion:false, occupied:false }),
  space("C03", "창고 C-03", "SN-C03", "192.168.0.23", "warning", { co2:1580, temperature:27.2, bodyTemperature:36.5, breathRate:15, motion:true, occupied:true }),
  space("D04", "연구실 D-04", "SN-D04", "192.168.0.24", "emergency", { co2:1210, temperature:29.2, bodyTemperature:39.1, breathRate:8, motion:false, occupied:true })
];
let db = readStore() || { spaces: initialSpaces, events: [], settings: { co2:1500, motion:30, temp:38, breath:10 } };
writeStore();

app.disable("x-powered-by");
app.use(express.json({ limit:"256kb" }));
app.use((req, res, next) => { res.setHeader("X-Content-Type-Options", "nosniff"); next(); });

app.post("/api/auth/login", async (req, res) => {
  const id = String(req.body.id || "");
  const password = String(req.body.password || "");
  const adminId = process.env.ADMIN_ID || "admin";
  const configuredHash = process.env.ADMIN_PASSWORD_HASH;
  const validPassword = configuredHash
    ? await bcrypt.compare(password, configuredHash)
    : password === (process.env.ADMIN_PASSWORD || "SafeNest123!");
  if (id !== adminId || !validPassword) return res.status(401).json({ error:"아이디 또는 비밀번호가 올바르지 않습니다." });
  const token = jwt.sign({ sub:id, role:"admin" }, JWT_SECRET, { expiresIn:"8h" });
  res.json({ token, user:{ id, role:"admin" }, expiresIn:28800 });
});

app.get("/api/spaces", requireAdmin, (req, res) => res.json(db.spaces));
app.get("/api/spaces/:id", optionalAdmin, (req, res) => {
  const item = findSpace(req.params.id);
  if (!item) return res.status(404).json({ error:"공간을 찾을 수 없습니다." });
  res.json(publicSpace(item));
});
app.post("/api/spaces", requireAdmin, async (req, res) => {
  const { name, nodeId, host, macAddress="", port=8000 } = req.body;
  if (!name || !nodeId || !host) return res.status(400).json({ error:"공간 이름, 노드 ID, 주소는 필수입니다." });
  if (db.spaces.some(s => s.nodeId.toLowerCase() === String(nodeId).toLowerCase())) return res.status(409).json({ error:"이미 등록된 노드 ID입니다." });
  const id = uniqueId();
  const item = space(id, String(name), String(nodeId), String(host), "offline", {});
  Object.assign(item, { macAddress:String(macAddress), port:Number(port) || 8000, provisionToken:crypto.randomBytes(18).toString("hex") });
  db.spaces.push(item); addEvent(item, "info", "새 공간 등록", `${host}:${item.port} · ${nodeId}`); commit("space.created", item);
  res.status(201).json({ ...item, guestUrl:guestUrl(req, item.id), qrUrl:`/api/spaces/${item.id}/qr` });
});
app.patch("/api/spaces/:id", requireAdmin, (req, res) => {
  const item = findSpace(req.params.id); if (!item) return res.status(404).json({ error:"공간을 찾을 수 없습니다." });
  for (const key of ["name", "host", "macAddress"]) if (req.body[key] !== undefined) item[key] = String(req.body[key]);
  if (req.body.port !== undefined) item.port = Number(req.body.port);
  commit("space.updated", item); res.json(item);
});
app.delete("/api/spaces/:id", requireAdmin, (req, res) => {
  const index = db.spaces.findIndex(s => s.id === req.params.id); if (index < 0) return res.status(404).json({ error:"공간을 찾을 수 없습니다." });
  const [removed] = db.spaces.splice(index, 1); commit("space.deleted", { id:removed.id }); res.status(204).end();
});
app.get("/api/spaces/:id/qr", async (req, res, next) => {
  try { if (!findSpace(req.params.id)) return res.status(404).end(); const svg = await QRCode.toString(guestUrl(req, req.params.id), { type:"svg", width:360, margin:2 }); res.type("image/svg+xml").send(svg); } catch (e) { next(e); }
});
app.get("/qr/:id", async (req, res, next) => {
  try {
    const item=findSpace(req.params.id); if(!item)return res.status(404).send("공간을 찾을 수 없습니다.");
    const url=guestUrl(req,item.id), svg=await QRCode.toString(url,{type:"svg",width:420,margin:2,errorCorrectionLevel:"H"});
    const localWarning=/^(localhost|127\.0\.0\.1)(:|$)/.test(req.get("host")||"");
    res.type("html").send(`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(item.name)} QR</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f1f5f9;font-family:system-ui;color:#172238}.card{width:min(520px,calc(100% - 32px));padding:28px;text-align:center;background:white;border-radius:20px;box-shadow:0 16px 50px #10264222}.qr svg{width:min(100%,420px);height:auto}.url{padding:12px;background:#f4f7fa;border-radius:10px;overflow-wrap:anywhere}.warn{color:#b45309;background:#fff7df;padding:12px;border-radius:10px}</style><main class="card"><h1>${escapeHtml(item.name)}</h1><p>방문자 실시간 대시보드</p><div class="qr">${svg}</div><p class="url">${escapeHtml(url)}</p>${localWarning?'<p class="warn">localhost로 연 QR은 휴대폰에서 접속할 수 없습니다. 이 페이지를 http://RPI_IP:3000/qr/'+encodeURIComponent(item.id)+' 주소로 다시 여세요.</p>':''}</main></html>`);
  } catch(error){next(error);}
});
app.get("/api/events", requireAdmin, (req, res) => res.json(db.events.slice(0, 500)));
app.get("/api/bridge/status", requireAdmin, (req, res) => res.json({ ...bridge, timer:undefined, url:RPI_BRIDGE_URL, spaceId:RPI_SPACE_ID }));

app.post("/api/sensor-data", sensorAuth, (req, res) => {
  const item = db.spaces.find(s => s.nodeId === req.body.nodeId || s.id === req.body.spaceId);
  if (!item) return res.status(404).json({ error:"등록되지 않은 센서 노드입니다." });
  const reading = normalizeReading(req.body);
  item.reading = reading; item.lastSeen = new Date().toISOString(); item.status = evaluate(reading); item.risk = riskScore(reading);
  addEvent(item, levelFor(item.status), "센서 데이터 수신", `CO₂ ${reading.co2 ?? "-"} ppm · 온도 ${reading.temperature ?? "-"}℃`);
  commit("sensor.updated", publicSpace(item)); res.status(202).json({ accepted:true, spaceId:item.id, status:item.status, risk:item.risk });
});
app.get("/api/thermal/:spaceId", async (req, res) => {
  if (req.params.spaceId !== RPI_SPACE_ID) return res.status(204).end();
  try {
    const headers = {};
    if (req.get("if-none-match")) headers["If-None-Match"] = req.get("if-none-match");
    const upstream = await fetch(`${RPI_BRIDGE_URL}/api/thermal`, { headers, signal:AbortSignal.timeout(1800) });
    if ([204, 304].includes(upstream.status)) return res.status(upstream.status).end();
    if (!upstream.ok) return res.status(502).json({ error:`Raspberry Pi 열화상 HTTP ${upstream.status}` });
    const body = Buffer.from(await upstream.arrayBuffer());
    res.status(200).set({
      "Content-Type":"application/vnd.safenest.thermal-u16be",
      "Cache-Control":"no-store",
      "Content-Length":String(body.length),
      ...(upstream.headers.get("etag") ? { ETag:upstream.headers.get("etag") } : {})
    }).send(body);
  } catch (error) {
    res.status(503).json({ error:"Raspberry Pi 열화상에 연결할 수 없습니다." });
  }
});
app.get("/api/stream", (req, res) => {
  res.writeHead(200, { "Content-Type":"text/event-stream", "Cache-Control":"no-cache", Connection:"keep-alive" });
  res.write(`event: snapshot\ndata: ${JSON.stringify({ spaces:db.spaces.map(publicSpace), events:db.events.slice(0, 20) })}\n\n`);
  clients.add(res); req.on("close", () => clients.delete(res));
});
app.post("/api/provision/:token", requireAdmin, (req, res) => {
  const item = db.spaces.find(s => s.provisionToken === req.params.token);
  if (!item) return res.status(404).json({ error:"유효하지 않은 등록 QR입니다." });
  item.provisionedAt = new Date().toISOString(); commit("space.provisioned", item); res.json(item);
});

app.get("/guest/dashboard/:spaceId", (req, res) => res.sendFile(path.join(__dirname, "guest.html")));
app.get("/login", (req, res) => res.redirect("/"));
app.get("/", (req, res) => res.sendFile(path.join(__dirname, "preview.html")));
app.get("/admin", (req, res) => res.sendFile(path.join(__dirname, "preview.html")));
app.get("/admin-api.js", (req, res) => res.sendFile(path.join(__dirname, "admin-api.js")));
app.get("/thermal-client.js", (req, res) => res.sendFile(path.join(__dirname, "thermal-client.js")));
app.use((err, req, res, next) => { console.error(err); res.status(500).json({ error:"서버 처리 중 오류가 발생했습니다." }); });
app.listen(PORT, () => {
  console.log(`SafeNest: http://localhost:${PORT}`);
  console.log(`Raspberry Pi bridge: ${RPI_BRIDGE_URL} → ${RPI_SPACE_ID}`);
  pollRaspberryPi();
  bridge.timer = setInterval(pollRaspberryPi, RPI_POLL_MS);
});

function requireAdmin(req, res, next) { const token = bearer(req); try { const payload = jwt.verify(token, JWT_SECRET); if (payload.role !== "admin") throw Error(); req.user = payload; next(); } catch { res.status(401).json({ error:"관리자 로그인이 필요합니다." }); } }
function optionalAdmin(req, res, next) { next(); }
function sensorAuth(req, res, next) { if (req.get("x-api-key") !== SENSOR_API_KEY) return res.status(401).json({ error:"센서 API 키가 올바르지 않습니다." }); next(); }
function bearer(req) { return (req.get("authorization") || "").replace(/^Bearer\s+/i, ""); }
function space(id, name, nodeId, host, status, reading) { return { id, name, nodeId, host, port:8000, macAddress:"", status, risk:riskScore(reading), reading:normalizeReading(reading), lastSeen:new Date().toISOString() }; }
function normalizeReading(v={}) { const num = k => v[k] == null || v[k] === "" ? null : Number(v[k]); return { co2:num("co2"), temperature:num("temperature"), bodyTemperature:num("bodyTemperature"), breathRate:num("breathRate"), heartRate:num("heartRate"), motion:Boolean(v.motion), occupied:Boolean(v.occupied), motionlessSeconds:num("motionlessSeconds") || 0, thermal:v.thermal && typeof v.thermal === "object" ? { ...v.thermal } : null, timestamp:v.timestamp || new Date().toISOString() }; }
function evaluate(r) { if ((r.bodyTemperature || 0) >= 38 && (r.breathRate || 99) < 10) return "emergency"; if ((r.breathRate || 99) < 10 || r.motionlessSeconds >= 30) return "danger"; if ((r.co2 || 0) >= 1500 || (r.bodyTemperature || 0) >= 38) return "warning"; return r.occupied ? "normal-occupied" : "normal-empty"; }
function riskScore(r={}) { let n=0; if ((r.co2||0)>=1500) n+=30; if ((r.bodyTemperature||0)>=38) n+=25; if (r.breathRate != null && r.breathRate<10) n+=30; if ((r.motionlessSeconds||0)>=30) n+=25; return Math.min(100, n || (r.occupied ? 12 : 4)); }
function publicSpace(s) { const { provisionToken, ...safe } = s; return safe; }
function levelFor(status) { return status.startsWith("normal") ? "normal" : status; }
function addEvent(s, level, message, detail) { db.events.unshift({ id:crypto.randomUUID(), time:new Date().toISOString(), spaceId:s.id, level, message, detail }); db.events = db.events.slice(0, 2000); }
function findSpace(id) { return db.spaces.find(s => s.id === id); }
function uniqueId() { return `N${Date.now().toString(36).toUpperCase()}`; }
function guestUrl(req, id) { return `${req.protocol}://${req.get("host")}/guest/dashboard/${encodeURIComponent(id)}`; }
function commit(type, payload) { writeStore(); const msg = `event: ${type}\ndata: ${JSON.stringify(payload)}\n\n`; for (const client of clients) client.write(msg); }
function broadcast(type, payload) { const msg = `event: ${type}\ndata: ${JSON.stringify(payload)}\n\n`; for (const client of clients) client.write(msg); }
function readStore() { try { return JSON.parse(fs.readFileSync(STORE_FILE, "utf8")); } catch { return null; } }
function writeStore() { fs.mkdirSync(path.dirname(STORE_FILE), { recursive:true }); const tmp=`${STORE_FILE}.tmp`; fs.writeFileSync(tmp, JSON.stringify(db, null, 2)); fs.renameSync(tmp, STORE_FILE); }
function loadEnv(file) { try { for (const line of fs.readFileSync(file,"utf8").split(/\r?\n/)) { const m=line.match(/^([^#=]+)=(.*)$/); if (m && process.env[m[1]]===undefined) process.env[m[1]]=m[2]; } } catch {} }
function escapeHtml(value) { return String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char])); }

async function pollRaspberryPi() {
  try {
    const response = await fetch(`${RPI_BRIDGE_URL}/api/state`, { cache:"no-store", signal:AbortSignal.timeout(1800) });
    if (!response.ok) throw Error(`HTTP ${response.status}`);
    const state = await response.json();
    const sensors = state.sensors || {};
    const revision = sensors.revision;
    bridge.ok = true;
    bridge.error = null;
    bridge.lastSuccessAt = new Date().toISOString();
    const item = findSpace(RPI_SPACE_ID);
    if (!item) return;
    if (sensors.status !== "live") {
      holdOrMarkOffline(item, `센서 ${sensors.status || "waiting"}`);
      return;
    }
    if (revision === bridge.sensorRevision) return;
    bridge.sensorRevision = revision;
    bridge.lastLiveAt = Date.now();
    bridge.waitingNotified = false;
    const valid = sensors.valid || {};
    if (sensors.pir_motion) bridge.lastMotionAt = Date.now();
    const thermal = sensors.thermal || {};
    const reading = normalizeReading({
      co2:valid.co2 ? sensors.co2_ppm : item.reading?.co2,
      breathRate:valid.respiration ? sensors.resp_rate_bpm : item.reading?.breathRate,
      heartRate:valid.heart ? sensors.heart_rate_bpm : item.reading?.heartRate,
      bodyTemperature:thermal.fresh ? thermal.max_c : item.reading?.bodyTemperature,
      motion:sensors.pir_motion === true,
      occupied:sensors.pir_motion === true || (valid.respiration && sensors.resp_rate_bpm != null),
      motionlessSeconds:sensors.pir_motion ? 0 : Math.floor((Date.now() - bridge.lastMotionAt) / 1000),
      thermal:thermal.fresh ? { available:true, fresh:true, minC:thermal.min_c ?? null, maxC:thermal.max_c ?? null, sequence:thermal.sequence ?? null, ageSeconds:thermal.age_seconds ?? null } : item.reading?.thermal,
      timestamp:new Date().toISOString()
    });
    const previousStatus = item.status;
    item.reading = reading;
    item.lastSeen = sensors.last_received_at ? new Date(sensors.last_received_at * 1000).toISOString() : new Date().toISOString();
    item.status = evaluate(reading);
    item.risk = riskScore(reading);
    item.bridge = { source:"raspberry-pi", deviceId:sensors.device_id || null, peer:sensors.peer || null, fresh:true, waiting:false };
    if (previousStatus !== item.status) {
      addEvent(item, levelFor(item.status), "Raspberry Pi 센서 상태 변경", `${previousStatus} → ${item.status}`);
      writeStore();
    }
    broadcast("sensor.updated", publicSpace(item));
  } catch (error) {
    bridge.ok = false;
    bridge.error = error.message;
    const item = findSpace(RPI_SPACE_ID);
    if (item) holdOrMarkOffline(item, error.message);
  }
}

function holdOrMarkOffline(item, reason) {
  const savedAt=Date.parse(item.lastSeen||"");
  const baseline=bridge.lastLiveAt || (Number.isFinite(savedAt)?savedAt:Date.now());
  if (!bridge.lastLiveAt) bridge.lastLiveAt=baseline;
  const elapsed=Date.now()-baseline;
  item.bridge={ ...item.bridge, source:"raspberry-pi", fresh:false, waiting:true, waitingSeconds:Math.max(0,Math.floor(elapsed/1000)) };
  bridge.error=reason;
  if (elapsed < RPI_OFFLINE_GRACE_MS) {
    if (!bridge.waitingNotified) { bridge.waitingNotified=true; broadcast("sensor.waiting", publicSpace(item)); }
    return;
  }
  if (item.status !== "offline") {
    item.status="offline"; item.risk=null;
    addEvent(item,"offline","Raspberry Pi 연결 중단",`${reason} · ${Math.round(elapsed/1000)}초`);
    writeStore(); broadcast("sensor.updated",publicSpace(item));
  }
}
