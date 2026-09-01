# SafeNest Pi 실행 절차 (필드용)

이 문서는 **실제 프로토타입 Pi**에서 SafeNest 런타임을 켜고 확인하는 절차만 정리한다.
기준 경로: `/home/sandi/safenest-team-main`
기준 커밋: 팀 `main` (`jinsu1011/safenest-embedded-competition`, Risk V1 / M-N9 포함본)

> Pi IP가 바뀌면 아래 `PI_IP`만 바꿔 읽으면 된다.
> 현재 필드 IP: **`192.168.0.3`**
> USB 이더넷으로 붙는 세션은 **`192.168.137.x`** 일 수 있다. ESP 목표 주소와 모니터 `--base`를 같은 IP로 맞춘다.

---

## 필드 모니터 (바로 실행)

`--once`를 **빼면** 계속 갱신, 넣으면 한 번만 보고 종료.

```bash
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py                 # 계속 보기 (기본 4초)
python3 hil/pi_field_monitor.py --once          # 한 번만
python3 hil/pi_field_monitor.py --interval 2    # 2초 간격 계속
python3 hil/pi_field_monitor.py --raw-labels    # 짧은 라벨 대신 원문 코드
# 종료: Ctrl+C
# 맥에서: python3 hil/pi_field_monitor.py --base http://<PI_IP>:8000
```

맨 위 `Thermal:` 줄은 지금 기동된 프로세스의 Thermal selector다 (`BASELINE` / `A` / `B`). 표 읽는 법 → **3-B**. 짧은 라벨(`PHYS_OK` 등) 의미 → **3-C**.
Thermal baseline/A/B 현장 비교는 `PI_RUNBOOK_THERMAL.md` 참조.

---

## 개발 규칙 (필수)

Pi에 손대기 전에 **로컬 worktree 브랜치 → GitHub PR → merge → Pi pull** 순서로 한다.

- `main` 체크아웃을 직접 수정하지 않는다.
- 팀원과 `main`을 공유하므로 **git worktree**로 작업 트리를 분리한다.
- Pi에서 `app.py` 등을 SSH로 핫패치하지 않는다 (긴급 복구 후 반드시 브랜치에 반영·PR).
- 배포 권한 레포: `jinsu1011/safenest-embedded-competition` (`/home/sandi/safenest-team-main`).


## 0. 이것만 쓴다

| 경로 | 용도 |
|---|---|
| `/home/sandi/safenest-team-main` | **정식 배포** (여기만 실행) |
| `/home/sandi/safenest-runtime` | 예전 클론. 참고용. **기동하지 말 것** |
| `/home/sandi/integration` 등 | 옛 진단/통합 클론. **기동하지 말 것** |

한 번에 하나만 띄운다. 예전 LCD 단독 `RaspberryPi/LCD/server.py` / 옛 `run_backend`를 따로 켜지 않는다.
`:8000`은 **팀 런타임 백엔드만** 소유한다.

**중요:** `./run_safenest.sh`는 백엔드·센서 수신·웹 서빙까지다.
LCD에 Chromium을 **자동으로 띄우지는 않는다** → 아래 **2-B**를 따로 실행한다.

---

## 1. 최초 1회 (이미 끝났으면 생략)

```bash
cd /home/sandi/safenest-team-main
git fetch origin
git checkout main
git pull --ff-only origin main

# 의존성 + preflight
bash ./run_safenest.sh --install
```

확인:

- `.venv/bin/python` 존재
- `RaspberryPi/Runtime/risk/formula_v1.py` 존재
- `.env` 존재 (비밀값 포함 — git에 올리지 말 것)
- `RaspberryPi/LCD/static/display.html` 존재

### mmWave / B23 (필드 현재)

기본 mmWave AI는 **B23 PyTorch 프로토타입** (`M_PROT_B23`)이다. M-N9 INT8 호흡 분류(`NORMAL`/`APNEA`)는 기본 경로가 아니다.

이 Pi에는 추론이 실제로 돌도록 **런타임 어댑터**(재실 래치 + 10Hz 샘플 인덱스)가 들어가 있을 수 있다. 팀 `main` 원본만 있으면 ESP `human_detected_raw=null`에서 `NO_OCC`로 멈추고, 센서 시계가 들쭉날쭉하면 `R1_TIME`으로 막힌다.

- B23 가중치/스케일러는 동결. 다시 학습·TFLite 변환하지 않는다.
- `PHYSIOLOGY_ELIGIBLE`(`PHYS_OK`)는 **병원 진단이 아니다.** 무호흡 판정도 아니다.
- Risk 점수(`RR_OK`/`RR_ABN`)는 아직 **벤더 BPM 룰**이 주이고, B23 RR은 화면에 보이더라도 위험도 공식의 주입력이 아니다.

### `/display` 라우트 (필드 필수)

팀 `main` 원본 `backend/app.py`에는 `/display`가 없을 수 있다.
필드 Pi에는 LCD 정적 파일(`RaspberryPi/LCD/static`)을 `:8000`에서 서빙하도록 **로컬 패치**가 들어가 있다.

기동 후 반드시:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/display
# 기대: 200
```

`404`면 LCD HTML이 안 나온다. `app.py`에 `/display`, `/common.css` 라우트가 있는지 확인하고 백엔드를 재기동한다.
`git pull` / `git reset` 하면 이 패치가 날아갈 수 있으니, pull 후 `/display`가 **200**인지 다시 확인한다.

---

## 2. 평소 기동

### 2-A. 백엔드 (런타임)

```bash
cd /home/sandi/safenest-team-main

# 이미 떠 있으면 중복 기동하지 말 것
pgrep -af run_backend.py || true
ss -ltnp | grep -E ":8000|:9000" || true
ss -lunp | grep 5005 || true

# 백그라운드 기동
mkdir -p logs
nohup bash ./run_safenest.sh > logs/runtime.log 2>&1 &
echo $! > .runtime.pid
```

포그라운드로 보려면:

```bash
cd /home/sandi/safenest-team-main
bash ./run_safenest.sh
```

Thermal V2 후보를 같은 스택에서 바꿔 보려면 (기본 `./run_safenest.sh`는 기존 baseline 유지):

```bash
bash ./run_safenest_thermal_test.sh baseline
bash ./run_safenest_thermal_test.sh a
bash ./run_safenest_thermal_test.sh b
```

Thermal baseline/A/B 현장 비교·LCD·필드 모니터 모델 확인은 **`PI_RUNBOOK_THERMAL.md`** 를 본다. 핫 스위칭 없음. Team default는 바뀌지 않는다.

기동 직후 확인:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -s -o /dev/null -w "display:%{http_code}\n" http://127.0.0.1:8000/display
ss -ltnp | grep -E ":8000|:9000"
ss -lunp | grep 5005
```

기대 포트:

| 포트 | 역할 |
|---|---|
| TCP `:8000` | FastAPI / Web / **LCD `/display`** / admin |
| TCP `:9000` | ESP 스칼라 텔레메트리 (mmWave / CO₂ / PIR) |
| UDP `:5005` | ESP 열화상 프레임 |

URL:

- LCD / display: `http://192.168.0.3:8000/display`
- Admin: `http://192.168.0.3:8000/admin`
- Dashboard: `http://192.168.0.3:8000/dashboard`
- Health: `http://192.168.0.3:8000/health`
- Status: `http://192.168.0.3:8000/api/status`
- LCD state API: `http://192.168.0.3:8000/api/state`

### 2-B. LCD에 화면 띄우기 (Chromium 키오스크)

백엔드가 떠 있고 `/display`가 **200**인 다음, **Pi 본체 디스플레이(seat0 / `:0`)** 에서:

```bash
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
[ -f "$HOME/.Xauthority" ] && export XAUTHORITY="$HOME/.Xauthority"

# 이미 떠 있으면 재실행 전 종료
pkill -f "chromium.*8000/display" 2>/dev/null || true

nohup chromium --kiosk --noerrdialogs --disable-infobars \
  --check-for-update-interval=31536000 \
  --user-data-dir=/tmp/safenest-chromium-display \
  --ozone-platform=x11 \
  http://127.0.0.1:8000/display \
  >/tmp/chromium-display.log 2>&1 &
```

확인:

```bash
pgrep -af "chromium.*8000/display" | head -3
# 물리 LCD에 SafeNest 화면이 보이는지 확인
```

일반 창(키오스크 아님):

```bash
DISPLAY=:0 chromium http://127.0.0.1:8000/display &
```

SSH만으로는 LCD가 안 바뀐다. Chromium은 **Pi의 그래픽 세션(`DISPLAY=:0`)** 으로 띄워야 한다.

---

## 3. 중지 / 재시작

```bash
cd /home/sandi/safenest-team-main

# Chromium LCD
pkill -f "chromium.*8000/display" 2>/dev/null || true

# 백엔드
kill "$(cat .runtime.pid)" 2>/dev/null || true
pkill -f "backend/run_backend.py" || true

# 포트 비었는지 확인
ss -ltnp | grep -E ":8000|:9000" || echo "tcp free"
ss -lunp | grep 5005 || echo "udp free"

# 다시 기동: 2-A → 2-B
```

---

## 3-B. 필드 모니터 (저장 / AI 입력 / 통신 / LCD)

파일: `RaspberryPi/Runtime/hil/pi_field_monitor.py`
실행(계속): `cd …/RaspberryPi/Runtime && python3 hil/pi_field_monitor.py`
실행(한 번): 같은 명령 + `--once` / 종료: `Ctrl+C` / 맥 원격: `--base http://192.168.0.3:8000`

헤더 `Thermal:` 줄은 GET `/api/status`의 `runtime_status.model_selector`다. A/B 전용 모니터 스크립트는 없다.

아래는 **화면에 나오는 표 4개를 읽는 법**이다. 위→아래 순서로 본다.

공통 기호:

| 기호 | 의미 |
|---|---|
| `Δ` | 직전 샘플 대비 **이번 간격(기본 4초) 동안 증가량**. `+12`면 늘었음, `0`이면 그 구간 유입 없음 |
| `-` | 값 없음 / 해당 없음 |
| `…` | 칸이 좁아 잘린 문자열 (중요하면 터미널을 넓히거나 그 행 `detail`/`note`를 본다) |
| 헤더 `Δ window Ns` | 지금 표의 Δ가 몇 초 간격인지 |

ESP 끄기 전: Verdict가 대부분 `NO` / LCD `OFFLINE`인 것이 정상이다.
ESP 켠 뒤: **Δ가 양수인지**를 먼저 보면 된다.

---

### 표 1) `## Verdict` — 한눈에 YES/NO

열:

| 열 | 읽는 법 |
|---|---|
| `check` | 무엇을 판정했는지 |
| `ok?` | 판정 결과. 대부분 `YES`/`NO`. **LCD state 행만** 상태 문자열(`OFFLINE`, `NORMAL-EMPTY` 등) |
| `detail` | 판정에 쓰인 숫자·부가 설명 (`conn=`, `telem=`, `Δ=`, `fail=` …) |

행별로:

| check | ok? 읽는 법 | detail에서 볼 것 |
|---|---|---|
| `TCP flow` | `YES` = 이번 구간에 ESP TCP 패킷 증가 | `conn`, `telem`, `Δ` |
| `UDP flow` | `YES` = 열화상 완성 프레임 증가 | `frames`, `Δ` |
| `Save mmW` / `Save CO2` / `Save thm` | `YES` = 해당 센서가 디스크에 기록됨 | `n`, `Δ` |
| `DB grow` | `YES` = SQLite 스냅샷 증가 | `snap`, `ev`, `Δ` |
| `Log worker` | `YES` = 저장 워커 살아 있음 | `on`, 큐 `q`, `err` |
| `AI input` | `YES` = 센서가 LIVE이고 AI가 `NO_IN`이 아님 (`WARMUP`/`PHYS_OK`도 YES) | `ok=` 또는 `fail=` |
| `Risk` | `YES` = `formula_id`가 `SAFENEST_RISK_V1` | `score`, `level`, `evid` |
| `LCD state` | LCD 상태 문자열 | `room`, `rev` |

읽는 팁: 이상하면 **`ok?`가 NO인 행만** 보고, 그 행 `detail`의 `Δ=0`인지 `conn=0`인지부터 확인한다.

---

### 표 2) `## Link & storage` — 통신·저장 수치

열:

| 열 | 읽는 법 |
|---|---|
| `metric` | 항목 이름 |
| `now` | **지금 누적값** (또는 현재 상태 문자열) |
| `Δ` | 이번 간격 증가량. 흐름 판정의 핵심 |
| `note` | 부가 카운터·경로 |

행별로:

| metric | now | Δ가 의미하는 것 | note에서 볼 것 |
|---|---|---|---|
| `system` | `ONLINE/…` 또는 `OFFLINE/FAILED` | (보통 `-`) | `ready`, `offline` |
| `tcp:9000 conn` | ESP TCP 동시 연결 수 | 연결이 늘/줄었는지 | `disc` 끊김, `gaps` 시퀀스 갭, `proto_err` |
| `telemetry pkts` | 스칼라 텔레메트리 누적 패킷 | 패킷이 들어오는지 | unexpected thermal-on-TCP 등 |
| `udp:5005 frames` | 조립 완료된 열화상 프레임 누적 | 프레임이 들어오는지 | `dgram`, `incomplete`, `fps` |
| `log written mm/co2/thm` | 센서별 파일 기록 누적 | 저장이 도는지 | `accepted` vs `dropped` (드롭 많으면 큐/부하) |
| `db snapshots` | DB 스냅샷 개수 | 런타임이 주기적으로 기록하는지 | DB 경로 |
| `db events` | 이벤트 개수 | 이벤트 적재 | `schema`, `avail` |

읽는 팁:

- **흐름**은 `now`보다 **`Δ`** 를 본다. `now`만 크고 `Δ=0`이면 “예전에 쌓였고 지금은 안 들어옴”.
- `conn≥1`인데 `telemetry Δ=0`이면 소켓만 있고 페이로드가 안 오는 경우.
- `written Δ>0`이면 “AI 입력 전 단계인 저장”은 통과.

---

### 표 3) `## Sensors / AI / risk component` — 센서 한 줄씩

센서마다 한 행 (`mmwave` / `thermal` / `co2` / `pir`).
**이 열에 뜨는 문자열은 코드에 정해진 집합**이다. 아래 “경우별”을 보면 된다.

| 열 | 의미 | 좋은 예 | 나쁜 예 |
|---|---|---|---|
| `sensor` | 센서 ID | — | — |
| `status` | 센서 수신/신선도 | `LIVE` | `NONE`, `STALE`, `DISC`, `BAD` |
| `age_s` | 마지막 데이터 나이(초) | TTL 안쪽 | `-` / 큰 값 |
| `ai` | AI 짧은 라벨 (원문은 `--raw-labels`) | `PHYS_OK` 등 | `NO_IN` |
| `err` | 막힌 이유 짧은 코드 | `-` | `WARMUP`, `NO_OCC`, `R1_TIME` … |
| `score` | mmWave는 B23 **숨 확률**(0~1). 다른 센서는 기존 score | 숫자 | `-` |
| `ms` | 추론 지연 | 작은 숫자 | `-` |
| `risk` | Risk 성분 짧은 라벨 | `RR_OK` 등 | `NA` |
| `rsc` | Risk 성분 점수 | 숫자 | `-` |
| `values` | 힌트. mmWave는 `occ/latch/br/rr/q/vRR/r1` | 아래 3-C | `-` |

읽는 팁: 왼쪽→오른쪽 `status` → `ai_state`/`ai_err` → `risk_st`/`risk_sc` → `values`.

---

#### 표 3 · `status` (모든 센서 공통)

| 값 | 짧은 라벨 | 의미 |
|---|---|---|
| `LIVE` | `LIVE` | 최근 TTL 안 유효 데이터 |
| `NO_DATA` | `NONE` | 아직/전혀 유효 샘플 없음 |
| `STALE` | `STALE` | 예전에 왔지만 TTL 초과 |
| `DISCONNECTED` | `DISC` | 연결 끊김 |
| `INVALID` | `BAD` | 수신은 됐으나 유효성 실패 |
| `DEGRADED` | `DEG` | 시스템 저하 (센서 표보다 시스템 쪽에 흔함) |

---

#### 표 3 · `ai` — **thermal** (모델 `thermal_fall_int8`, 3클래스)

`probabilities` 순서 = `[NOT_HUMAN, HUMAN_NORMAL, HUMAN_FALL]`.

| 원문 | 짧은 라벨 | 의미 | 필드에서 |
|---|---|---|---|
| `NOT_HUMAN` | `NO_HUM` | 배경/비인간 (class 0) | 사람 없음·화각 밖·자주 |
| `HUMAN_NORMAL` | `HUMAN` | 사람 정상 자세 (class 1) | 서 있/앉아 있음 |
| `HUMAN_FALL` | `FALL` | 전도/누움 (class 2) | 낙상·누운 자세로 판단 |
| `INPUT_UNAVAILABLE` | `NO_IN` | 모델 입력 없음 | `status`가 LIVE가 아니거나 프레임 없음 |

---

#### 표 3 · `ai` — **co2** (C-B6, 2클래스)

| 원문 | 짧은 라벨 | 의미 |
|---|---|---|
| `VACANT` | `VACANT` | 공실 쪽 |
| `OCCUPIED` | `OCC` | 재실 쪽 |
| `INPUT_UNAVAILABLE` | `NO_IN` | CO₂ 입력/윈도우 불가 |

---

#### 표 3 · `ai` — **mmwave** (B23 프로토타입, 현재 기본)

M-N9의 `NORMAL` / `RAPID_OR_ABNORMAL` / `APNEA` 는 **기본 경로가 아니다.** 옛 경로가 보이면 런타임이 B23가 아닌 것이다.

B23는 30초 위상 창을 돌려 **숨 있음 여부 + 품질 + 호흡수** 세 헤드를 낸다. 무호흡(APNEA) 클래스를 내지 않는다.

| 원문 | 짧은 라벨 | 한 줄 의미 |
|---|---|---|
| `PHYSIOLOGY_ELIGIBLE` | `PHYS_OK` | B23 추론 성공. 숨 있음 + 품질 통과 + RR 숫자 있음 |
| `ABSENT` | `ABSENT` | 모델이 “숨 약함/없음” 쪽으로 판단. 무호흡 진단 아님 |
| `QUALITY_SUPPRESSED` | `Q_LOW` | 숨은 있다 했지만 품질이 낮아 RR을 안 냄 |
| `RR_UNAVAILABLE` | `NO_RR` | 품질은 됐는데 RR 숫자를 못 디코드 |
| `WINDOW_NOT_READY` | `WARMUP` | 300샘플(약 30초) 창이 아직 안 참 |
| `PRESENCE_UNAVAILABLE` | `NO_OCC` | 재실 bool을 한 번도 못 받음 (`null`만) |
| `PRESENCE_FALSE` | `EMPTY` | 재실=없음(빈 방). 추론 안 함 |
| `WINDOW_UNAVAILABLE` | `NO_WIN` | **옛 M-N9/정규창** 실패 코드. B23 기본 경로면 잘 안 나옴 |
| `INPUT_UNAVAILABLE` | `NO_IN` | 센서 입력 자체 없음 |

`PHYSIOLOGY_ELIGIBLE` 상세는 **3-C**.

---

#### 표 3 · `ai` — **pir** (룰, 모델 없음)

| 원문 | 짧은 라벨 | 의미 |
|---|---|---|
| `MOTION` | `MOVE` | 움직임 감지 |
| `NO_MOTION` | `STILL` | 움직임 없음 |
| `INPUT_UNAVAILABLE` | `NO_IN` | PIR 입력 없음 |

---

#### 표 3 · `risk` — Risk 성분 state (formula_v1)

모니터 `risk` 열은 **성분 state**다. Verdict의 `AI`/`RULE`/`RULE_FALLBACK`과는 별개.

**thermal**

| 원문 | 짧은 라벨 | 의미 |
|---|---|---|
| `NOT_HUMAN` / `HUMAN_NORMAL` / `HUMAN_FALL` | `NO_HUM` / `HUMAN` / `FALL` | 열화상 AI를 그대로 사용 |
| `UNAVAILABLE` | `NA` | 비LIVE 또는 AI 차단 |

**mmwave**

| 원문 | 짧은 라벨 | 의미 |
|---|---|---|
| `RESPIRATION_NORMAL` | `RR_OK` | 벤더 BPM이 정상 구간 |
| `RESPIRATION_ABNORMAL` | `RR_ABN` | 벤더 BPM이 이상 구간 (지속되면 점수↑) |
| `UNAVAILABLE` | `NA` | 호흡 입력 없음 |

중요: 이 열은 **B23 RR이 아니라 MR60 벤더 `breath_rate_raw`(모니터 `vRR`)** 로 계산되는 경우가 많다. `ai=PHYS_OK` 인데 `risk=RR_ABN` 이면 “모델은 돌았고, 위험도 공식은 벤더 BPM을 보고 있다”는 뜻이다. B23 출력은 현재 **관찰용**이다.

**co2**

| 원문 | 짧은 라벨 | 의미 |
|---|---|---|
| `CO2_NORMAL` | `CO2_OK` | ppm·기울기 정상 |
| `CO2_WARNING` | `CO2_WN` | 경고 |
| `CO2_DANGER` | `CO2_DG` | 위험 |
| `CO2_IMMEDIATE_DANGER` | `CO2_NOW` | 즉시 위험 |
| `UNAVAILABLE` | `NA` | CO₂ 입력 없음 |

**pir**

| 원문 | 짧은 라벨 | 의미 |
|---|---|---|
| `MOTION` | `MOVE` | 움직임 있음 |
| `NO_MOTION` | `STILL` | 단시간 무움직임 |
| `NO_MOTION_RISING` | `STILL+` | 무움직임이 위험 점수로 상승 중 |
| `LONG_NO_MOTION` | `STILL++` | 장시간 무움직임 |
| `UNAVAILABLE` | `NA` | PIR 입력 없음 |

---

#### 표 3 · 지금 필드에서 자주 보는 조합

짧은 라벨 기준.

| 행 | status | ai | err | risk | 해석 |
|---|---|---|---|---|---|
| thermal | `LIVE` | `NO_HUM` | `-` | `NO_HUM` | 프레임 OK, 모델이 비인간 |
| thermal | `LIVE` | `HUMAN` | `-` | `HUMAN` | 열화상 재실·정상 |
| thermal | `LIVE` | `FALL` | `-` | `FALL` | 열화상 전도 클래스 |
| thermal | `LIVE` | `NO_IN` | `INT8` | `NA` | 모델 파일은 있는데 INT8 리뷰로 추론 안 함 |
| mmwave | `LIVE` | `WARMUP` | `WARMUP` | `RR_*` | 패킷은 오는데 30초 창 모으는 중 |
| mmwave | `LIVE` | `PHYS_OK` | `-` | `RR_OK` 또는 `RR_ABN` | **B23 추론 중.** risk는 벤더 BPM |
| mmwave | `LIVE` | `NO_OCC` | `NO_OCC` | `RR_*` | 창은 돼도 재실 bool이 한 번도 없음 |
| mmwave | `LIVE` | `EMPTY` | `EMPTY` | `RR_*` | 빈 방으로 래치. 추론 안 함 |
| mmwave | `LIVE` | `-`/`NO_IN` | `R1_TIME` | `RR_*` | 어댑터 없이 센서 시계를 R1에 넣음 → 격자 거절 |
| mmwave | `LIVE` | `NO_WIN` | `GAP` | `RR_*` | 옛 M-N9 창 실패 + 룰 폴백 |
| co2 | `LIVE` | `OCC` | `-` | `CO2_WN` | 재실 AI + ppm 경고 |
| co2 | `BAD` | `NO_IN` | `BAD` | `NA` | CO₂ 값이 유효하지 않음 |
| pir | `LIVE` | `STILL` | `-` | `STILL+` | 무움직임이 점수로 반영 중 |
| * | `NONE` | `NO_IN` | `NO_DATA` | `NA` | ESP/해당 채널 미수신 |

`err=NO_DATA` 이면 모델 버그가 아니라 **센서 미수신**이다.

---

## 3-C. B23 / 짧은 라벨 사전 (지금 런북에 없던 것)

### `PHYSIOLOGY_ELIGIBLE` (`PHYS_OK`)는 무슨 뜻인가

B23가 **이번 30초 위상 창**을 모델에 넣었고, 세 헤드가 전부 통과했다는 뜻이다.

1. **숨 헤드** `br` (breathing_probability) ≥ 임계값 → `PRESENT` (모니터 `br=0.6` 같은 값)
2. **품질 헤드** `q` ≥ 임계값 → 이 창을 RR로 써도 된다고 모델이 봄
3. **RR 헤드**가 숫자로 디코드됨 → 모니터 `rr=15` (B23 호흡수, **벤더 BPM이 아님**)

그래서 이름은 “생리학적으로 쓸 수 있는 출력(physiology eligible)”이다.

**아닌 것**

- 병원/임상 적격이 아니다
- 무호흡(APNEA) 판정이 아니다. B23는 APNEA 클래스를 안 낸다
- 최종 선정 모델이 아니다 (프로토타입, 교체 대상)
- Risk 위험도 공식에 이 숫자가 그대로 들어간다는 뜻이 아니다 (`vRR` 룰이 따로 있음)
- LCD “정상/경고”와 1:1이 아니다

같은 창에서 `ABSENT`가 나오면 숨 확률이 낮다는 뜻이지, “임상 무호흡”이 아니다.

### B23가 돌아가기까지의 문

```
ESP 위상 → 신선도(phase_age) OK → 샘플 300개 모음
        → 재실 래치가 true
        → R1이 10Hz 300개로 받음
        → R2 621벡터
        → B23 PyTorch
        → PHYS_OK / ABSENT / Q_LOW / NO_RR
```

| 짧은 라벨 | 원문 | 언제 | 다음에 볼 것 |
|---|---|---|---|
| `WARMUP` | `WINDOW_NOT_READY` | 기동 후 ~30초, 또는 갭/부트 후 창 리셋 | `r1` 비어 있음. seq가 늘면 기다림 |
| `NO_OCC` | `PRESENCE_UNAVAILABLE` | ESP가 `human_detected_raw`를 계속 `null`만 보냄. **한 번도 true/false가 없음** | values `occ=? latch=?` |
| `EMPTY` | `PRESENCE_FALSE` | 재실=false (빈 방)로 래치됨 | 사람 있으면 ESP true가 나와야 함 |
| `PHYS_OK` | `PHYSIOLOGY_ELIGIBLE` | 위 문 통과 + 세 헤드 통과 | `br` `rr` `q` |
| `ABSENT` | `ABSENT` | 모델이 숨 없음 쪽 | `br`가 낮음. APNEA 아님 |
| `Q_LOW` | `QUALITY_SUPPRESSED` | 숨은 있다 했지만 품질 실패 | RR 없음 |
| `NO_RR` | `RR_UNAVAILABLE` | 품질 OK, RR 디코드 실패 | 창/위상 이상 가능 |
| `R1_TIME` | `R1_TIMESTAMP_GRID_INCONSISTENT` | 물리 `millis()`를 그대로 R1에 넣음. Seeed는 ~9.8Hz 들쭉날쭉 | 샘플 인덱스 어댑터가 없는 빌드 |
| `R1_N` | `R1_SAMPLE_COUNT_MISMATCH` | R1 출력이 300개가 아님 | 창 길이 |
| `SLOW` | `SOURCE_RATE_BELOW_TARGET` | 선언 샘플레이트가 10Hz 미만 (어댑터 없는 옛 경로) | |
| `GAP` | `WINDOW_CONTAINS_LARGE_GAP` / 내부 큰 간격 | 0.5초 넘게 위상 공백이면 창을 이어 붙이지 않음 | |
| `NO_PH` | `PHASE_MISSING` | `breath_phase`가 없음/NaN | UART/펌웨어 |
| `OLD_PH` | `PHASE_STALE` | `phase_age_ms`가 너무 큼 (>1000) | |
| `BOOT` | `BOOT_BOUNDARY` | ESP `boot_id`가 바뀜. 창·재실 래치 리셋 | 다시 30초 |
| `BAD_TS` | `TIMESTAMP_INVALID` | `ts_monotonic_ms` 없음 | |
| `NO_SEQ` | `PHASE_SEQUENCE_MISSING` | nested `mmwave.seq` 없음 | |
| `NO_IN` | `INPUT_UNAVAILABLE` / `SENSOR_*` | 센서 LIVE가 아님 | `status` |
| `NO_DATA` | `SENSOR_NO_DATA` | 미수신 | ESP·`:9000` |
| `BAD` | `SENSOR_INVALID` / `INVALID` | 값 유효성 실패 | |
| `STALE` | `SENSOR_STALE` | TTL 초과 | |
| `DISC` | `SENSOR_DISCONNECTED` | 소켓 끊김 | `TCP flow` |
| `INT8` | `INT8_QUANTIZATION_REVIEW_REQUIRED` | 열화상 INT8 리뷰 게이트 | thermal만 |

### 재실 래치 (지금 필드에서 꼭 필요)

ESP `human_detected_raw`는 삼값이다: `true` / `false` / `null`.

- `null` = 모름. **없다로 바꾸면 안 됨**
- 이 ESP는 `true`가 **한 패킷만** 깜빡이고 대부분은 `null`. `false`는 거의 없음
- 모니터: `occ=Y/N/?` = **지금 패킷**, `latch=Y/N/?` = **B23가 쓰는 유지값**
- `occ=?` 인데 `latch=Y` 이고 `ai=PHYS_OK` 이면 정상 (래치가 펄스를 기억)
- `latch=?` 이면 기동 이후 true/false를 한 번도 못 본 것 → `NO_OCC`, 추론 없음
- `false`가 오면 래치가 풀림(`EMPTY`). ESP 재부팅(`BOOT`)이면 래치도 리셋

### 10Hz 샘플 인덱스 (R1_TIME을 넘는 방법)

B23/R1은 **초당 10개, 간격이 일정한 300개**를 기대한다.
실제 MR60 시계는 대략 초당 9.8개이고 간격이 흔들려, 그대로 넣으면 `R1_TIME`.

필드 어댑터:

- 물리 `ts_monotonic_ms` → 신선도·0.5초 갭·부트 검사용
- R1에 넣는 시각 → 들어온 위상 샘플 번호 × 0.1초
- 창이 차면 `r1=300` (모니터 values)

물리로 0.5초 넘게 끊기면 창을 이어 붙이지 않는다. nested seq가 +1이 아니면 기존처럼 창이 리셋될 수 있다.

### mmWave `values` 칸

| 키 | 의미 |
|---|---|
| `occ` | ESP가 **지금** 보낸 재실 (`Y`/`N`/`?`) |
| `latch` | B23 게이트가 유지 중인 재실 |
| `br` | B23 숨 확률 0~1 |
| `rr` | B23 호흡수 (모델) |
| `q` | B23 품질 확률 |
| `vRR` | 벤더 `breath_rate_raw` (모델 입력 아님, Risk가 이걸 봄) |
| `r1` | R1 샘플 수. 추론 중이면 300 |
| `B23` | 런타임이 `M_PROT_B23` |

게시 주기: 센서 패킷은 ~10Hz, `/api/status`의 AI 숫자는 **약 15초**마다 바뀔 수 있다. 모니터가 4초여도 `br`/`rr`이 몇 번 동일하게 보이는 것이 정상이다.

### 기동 직후 타임라인

1. ESP 붙음 → `TCP flow YES`, mmwave `LIVE`, `ai=WARMUP`
2. ~26–35초, 재실 펄스 1회라도 있으면 `latch=Y`
3. `ai=PHYS_OK`, `r1=300`, `br`/`rr`/`q` 숫자
4. `vRR`와 `rr`이 달라도 버그 아님 (소스가 다름)

재실 펄스가 전혀 없으면 창이 차도 `NO_OCC`에서 멈춘다.

### 옛 코드가 모니터에 남을 때

| 보이면 | 의미 |
|---|---|
| `NORMAL` / `RAPID` / `APNEA` | M-N9 경로. 지금 기본이 아님 |
| `NO_WIN` + `GAP` | 옛 240샘플/정규창 |
| torch 없음 / `NO_MDL` | 가중치는 있는데 런타임이 모델을 못 염 |

긴 원문을 보려면:

```bash
python3 hil/pi_field_monitor.py --raw-labels
```

### 표 4) `## Risk / LCD (display)` — 위험도·LCD 문구

키-값 표. LCD 화면과 맞춰 볼 때 쓴다.

| field | 읽는 법 |
|---|---|
| `formula_id` | `SAFENEST_RISK_V1`이어야 함 |
| `formula_version` | 공식 버전 문자열 |
| `risk_score / level` | 점수 / 레벨(`warning`·`danger` 등). 센서 없으면 `None` |
| `effective_weight` | 가용 성분 가중 합. `0`이면 성분 없음 |
| `evidence_sufficient` | 증거 충분한지 (`True`/`False`) |
| `presence` | 재실 판정과 출처 (`UNCONFIRMED` 등) |
| `degraded_mode` | 저하 모드 여부 |
| `reasons` | Risk가 그렇게 나온 **이유 코드** 나열 (디버그 핵심) |
| `LCD state` | LCD가 쓰는 상태 키 (`offline`, `normal-empty`, `warning` …). 물리 LCD와 같아야 함 |
| `LCD room` | 표시 공간 이름 |
| `LCD revision` | LCD 상태 revision |
| `pub_revision` | 백엔드 publication revision (내부 갱신 카운트) |

읽는 팁:

- LCD에 “통신 오류”면 여기 `LCD state=offline` + `reasons`에 `*_SENSOR_NO_DATA`가 같이 있는 경우가 많다.
- `formula_id`는 YES인데 `risk_score=None`이면 **엔진은 떠 있고 입력만 없는** 상태.

---

### 네 표를 이어서 읽는 짧은 순서

1. **Verdict**에서 NO인 행만 고른다.
2. 통신 NO → **Link & storage**의 `tcp:9000 conn` / `telemetry`·`udp frames`의 **Δ**.
3. 저장 NO → 같은 표의 `log written *` **Δ** / `Logging worker`.
4. AI NO → **Sensors** 표에서 해당 센서 `status`·`err`. mmWave면 **3-C**.
5. LCD 문구 이상 → **Risk / LCD**의 `LCD state` + `reasons`.


## 4. ESP 켜기 전 / 후

### ESP 켜기 전

- Pi 런타임만 먼저 올려 두면 된다 (`:9000` / `:5005` listen).
- 이 상태에서는 `/api/status`가 `NO_DATA` / `OFFLINE`인 것이 정상이다.
- LCD는 `offline` / 센서 연결 대기처럼 보일 수 있다.

### ESP 목표 주소 (필수)

ESP 펌웨어 / 설정의 Pi 주소를 **현재 Pi IP**로 맞춘다.

```text
TCP  → 192.168.0.3:9000
UDP  → 192.168.0.3:5005
```

IP가 또 바뀌면 ESP 쪽도 같이 갱신한다.

### ESP 켠 뒤 (3~4분 warm-up)

```bash
# 연결 여부
ss -Htn state established "( sport = :9000 or dport = :9000 )"

# 상태 스냅샷
curl -fsS http://127.0.0.1:8000/api/status | python3 -m json.tool | less
```

짧게 증가량만 보려면:

```bash
python3 - <<'PY'
import json, time, urllib.request
def get(p):
    return json.load(urllib.request.urlopen("http://127.0.0.1:8000"+p, timeout=5))
a=get("/health"); time.sleep(4); b=get("/health")
ra,rb=a["receiver"],b["receiver"]
print("tcp_conn", ra.get("connections"), "->", rb.get("connections"))
print("telemetry", ra.get("telemetry_packets"), "->", rb.get("telemetry_packets"))
ua,ub=ra.get("thermal_udp") or {}, rb.get("thermal_udp") or {}
print("thermal_frames", ua.get("completed_frames"), "->", ub.get("completed_frames"))
s=get("/api/status")
print("system", s.get("system"), s.get("system_health"))
r=s.get("risk") or {}
print("risk", r.get("formula_id"), r.get("risk_score"), r.get("risk_level"), r.get("component_status"))
for name in ("mmwave","thermal","co2","pir"):
    st=(s.get(name) or {}).get("state") or {}
    print(name, st.get("status"), "age", st.get("age_seconds") or st.get("age_s"))
PY
```

---

## 5. 프로토타입 PASS 기준 (필드)

모두 만족해야 PASS:

1. mmWave / Thermal / CO₂ / PIR → **LIVE** (또는 허용된 DEGRADED만)
2. 저장(`sensor_logging.written`)이 증가
3. Risk가 **`SAFENEST_RISK_V1`**으로 연속 산출
4. **물리 LCD**에 `/display` 화면 + admin / health / status 사용 가능

허용:

- mmWave Risk `RULE_FALLBACK` / `RR_ABN` (벤더 BPM 룰). B23 `PHYS_OK`와 동시에 나올 수 있음
- 일부 `DEGRADED`
- `DEVICE_VALIDATED=false`

B23 `PHYS_OK`는 프로토타입 PASS의 **가산 증거**이지, 임상 PASS가 아니다.

권장 펌웨어:

- ESP ≥ **1.3.0**, 텔레메트리에 `human_detected_raw` 포함 (`true`가 가끔이라도 나와야 래치됨)

---

## 6. 업데이트 (코드만 최신으로)

런타임이 떠 있으면 먼저 중지한 뒤:

```bash
cd /home/sandi/safenest-team-main
git fetch origin
git pull --ff-only origin main
# 의존성이 바뀌었을 때만
bash ./run_safenest.sh --install
# 다시 기동 (2-A) 후 /display 200 확인 → 2-B
```

**주의:**

- `data/` 와 `.env` 는 지우거나 `git reset --hard`로 날리지 않는다.
- pull 후 `/display`가 404면 LCD 라우트 패치를 다시 넣고 백엔드를 재기동한다.
- `git pull`은 Pi에 있는 **B23 런타임 어댑터**(재실 래치·10Hz 인덱스)를 덮어쓸 수 있다. pull 뒤 mmWave가 `NO_OCC`/`R1_TIME`이면 어댑터가 빠진 것이다.

---

## 7. 로그 / 데이터 위치

| 경로 | 내용 |
|---|---|
| `logs/runtime.log` | nohup 기동 로그 |
| `.runtime.pid` | 백그라운드 PID |
| `/tmp/chromium-display.log` | LCD Chromium 로그 |
| `RaspberryPi/Runtime/data/` | SQLite·필드 데이터 (보존) |
| `RaspberryPi/LCD/static/` | LCD HTML/CSS (백엔드가 서빙) |
| `.env` | 로컬 설정 (git 제외) |

---

## 8. 자주 막히는 것

| 증상 | 확인 |
|---|---|
| `:8000` 이미 사용 | 예전 `run_backend` / LCD `server.py` 남아 있음 → `pkill` 후 재기동 |
| `/display` → **404** | `app.py`에 LCD 라우트 없음 / pull로 패치 소실 → 패치 후 재기동 |
| Chromium은 떴는데 LCD 검정/빈 화면 | `curl`로 `/display`·`/common.css`·`/api/state`가 200인지 확인 |
| Chromium이 안 뜸 / 즉시 종료 | `DISPLAY=:0`, `XDG_RUNTIME_DIR=/run/user/1000`, `/tmp/chromium-display.log` |
| ESP 연결 0 | ESP 목표 IP가 옛 주소(`192.168.137.x` 등)인지 확인 |
| 센서 NO_DATA / `NONE` | ESP 전원/와이파이, `:9000` established, warm-up 3~4분 |
| Risk UNAVAILABLE | 센서 유입 없음 → 수신부터 해결 |
| mmWave `ai=WARMUP` | 기동 후 30초 대기. seq가 늘면 정상 |
| mmWave `ai=NO_OCC` | ESP 재실이 계속 `null`. `occ=? latch=?`. 사람이 레이더 앞에 있어야 `true` 펄스라도 옴 |
| mmWave `ai=PHYS_OK` 인데 LCD/Risk가 이상 | B23는 관찰용. Risk는 `vRR` 벤더 BPM. **3-C** |
| mmWave `err=R1_TIME` | 샘플 인덱스 어댑터 없는 빌드. 물리 시계를 R1이 거절 |
| `br`/`rr`이 안 바뀜 | `/api/status` 게시 ~15초. 패킷 age_s가 작으면 통신은 살아 있음 |
| 필드 모니터 글자가 `…`로 잘림 | 짧은 라벨이 기본. 원문은 `--raw-labels`. 의미는 **3-C** |

---

## 9. 한 줄 요약

```bash
cd /home/sandi/safenest-team-main
bash ./run_safenest.sh --install   # 최초만
bash ./run_safenest.sh             # 2-A 백엔드
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/display   # 200이어야 함
# 2-B LCD
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 \
  chromium --kiosk --ozone-platform=x11 \
  --user-data-dir=/tmp/safenest-chromium-display \
  http://127.0.0.1:8000/display &
# ESP → 192.168.0.3:9000 / :5005
```
