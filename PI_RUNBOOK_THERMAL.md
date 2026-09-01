# SafeNest Thermal V2 Pi 필드 실행 가이드

Raspberry Pi 옆에서 Thermal baseline / Candidate A / Candidate B를 바꿔 켜고 확인하는 **현장 운영 매뉴얼**이다.
일반 SafeNest 기동은 `PI_RUNBOOK.md`. 이 문서는 Thermal 비교만 다룬다.

기준 경로: `/home/sandi/safenest-team-main`
기준 저장소: `jinsu1011/safenest-embedded-competition`
필드 IP(바뀔 수 있음): `192.168.0.3`

**팀 기본 Thermal은 바뀌지 않았다.** `./run_safenest.sh`는 계속 `thermal_public_sdt_fp32_active`다. A를 켠다고 Team default가 바뀌는 것이 아니다.

---

## 0. 가장 빠른 실행 요약

```bash
cd /home/sandi/safenest-team-main
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
```

이미 떠 있는 SafeNest가 있으면 먼저 끈다 (핫 스위칭 없음):

```bash
kill "$(cat .runtime.pid)" 2>/dev/null || true
pkill -f "backend/run_backend.py" || true
ss -ltnp | grep -E ":8000|:9000" || echo "tcp free"
```

**하나만** 고른다.

```bash
# 기존 Team baseline (비교용 런처. 기본 모델과 동일 selector)
bash ./run_safenest_thermal_test.sh baseline

# Candidate A  (offline A_PREFERRED, CONTROLLED_TEAM_TEST, 기본값 아님)
bash ./run_safenest_thermal_test.sh a

# Candidate B  (offline B_NOT_COMPETITIVE, 비교 전용)
bash ./run_safenest_thermal_test.sh b
```

다른 터미널에서 필드 모니터 (스크립트는 하나뿐):

```bash
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py
```

헤더에 아래처럼 보여야 한다.

```text
Thermal: BASELINE | thermal_public_sdt_fp32_active | PUBLIC_SDT_BILINEAR_62X80_FRAME_MINMAX_V1
Thermal: A | thermal_tv2_candidate_a_a0_fp32_v1 | FRAME_ROBUST_P2_P98_V1
Thermal: B | thermal_tv2_candidate_b_seed42_fp32_test_v1 | FRAME_ROBUST_P2_P98_V1
```

이 줄은 **프로세스가 어떤 모델을 들고 기동했는지**다. 센서 LIVE / 추론 성공을 증명하지 않는다.

LCD는 백엔드와 별개다. `/display`가 200인 뒤 Chromium을 Pi 그래픽 세션에서 연다 (4절).

---

## 1. Pi 최신화

```bash
cd /home/sandi/safenest-team-main
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
```

- 실행은 **이 클론만**. `/home/sandi/integration`, `/home/sandi/safenest-runtime` 등 옛 클론은 기동하지 말 것.
- `main`을 Pi에서 직접 고치지 말 것. 변경은 worktree → PR → merge → 여기 `git pull --ff-only`.
- 의존성이 비어 있으면 최초 1회: `bash ./run_safenest.sh --install`

---

## 2. 서버 실행

모델은 **프로세스 기동 시 한 번** 고른다. 실행 중 전환은 없다.

| 상황 | 명령 | selector | 의미 |
|---|---|---|---|
| 평소 SafeNest | `bash ./run_safenest.sh` | `thermal_public_sdt_fp32_active` | Team 기본. 테스트 모드 아님 |
| 비교 baseline | `bash ./run_safenest_thermal_test.sh baseline` | 같은 selector | 비교 런처로 baseline 고정 |
| Candidate A | `bash ./run_safenest_thermal_test.sh a` | `thermal_tv2_candidate_a_a0_fp32_v1` | A_PREFERRED offline / 기본값 아님 |
| Candidate B | `bash ./run_safenest_thermal_test.sh b` | `thermal_tv2_candidate_b_seed42_fp32_test_v1` | B_NOT_COMPETITIVE / 비교만 |

런처는 기존 `run_safenest.sh`를 `exec`한다. 새 런타임 프로그램이 아니다.

기동 전 중복 확인:

```bash
cd /home/sandi/safenest-team-main
pgrep -af run_backend.py || true
ss -ltnp | grep -E ":8000|:9000" || true
ss -lunp | grep 5005 || true
```

### 2-A. baseline (비교 런처)

포그라운드 (디버그용, 로그가 바로 보임):

```bash
cd /home/sandi/safenest-team-main
bash ./run_safenest_thermal_test.sh baseline
```

백그라운드 (LCD / 모니터를 다른 터미널에서 쓸 때):

```bash
cd /home/sandi/safenest-team-main
mkdir -p logs
nohup bash ./run_safenest_thermal_test.sh baseline \
  > logs/runtime-thermal-baseline.log 2>&1 &
echo $! > .runtime.pid
```

### 2-B. Candidate A

```bash
# foreground
bash ./run_safenest_thermal_test.sh a

# background
mkdir -p logs
nohup bash ./run_safenest_thermal_test.sh a \
  > logs/runtime-thermal-a.log 2>&1 &
echo $! > .runtime.pid
```

### 2-C. Candidate B

```bash
# foreground
bash ./run_safenest_thermal_test.sh b

# background
mkdir -p logs
nohup bash ./run_safenest_thermal_test.sh b \
  > logs/runtime-thermal-b.log 2>&1 &
echo $! > .runtime.pid
```

### 2-D. 평소 기동 (비교가 아닐 때)

```bash
# foreground
bash ./run_safenest.sh

# background
mkdir -p logs
nohup bash ./run_safenest.sh > logs/runtime.log 2>&1 &
echo $! > .runtime.pid
```

`./run_safenest.sh`와 `./run_safenest_thermal_test.sh baseline`은 **같은 Thermal selector**다. 차이는 비교 런처가 `SAFENEST_THERMAL_TEST_MODE=1`을 켠다는 점뿐이다. Team default를 바꾸려면 코드/매니페스트를 바꿔야 하며, 이 런처로는 바뀌지 않는다.

포그라운드 = 즉시 로그 확인. 백그라운드 = LCD·모니터용. 둘 다 같은 런처다.

---

## 3. 현재 Thermal 모델 확인

기동 직후:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/status >/tmp/safenest-status.json
curl -s -o /dev/null -w "display:%{http_code}\n" http://127.0.0.1:8000/display
ss -ltnp | grep -E ":8000|:9000"
ss -lunp | grep 5005
```

selector만 읽기 (`jq` 불필요, 표준 Python):

```bash
python3 - <<'PY'
import json, urllib.request
s = json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/status"))
th = s.get("thermal") if isinstance(s.get("thermal"), dict) else {}
rt = th.get("runtime_status") or ((s.get("runtime_status") or {}).get("sensors") or {}).get("thermal") or {}
print("selector:", rt.get("model_selector") or "-")
print("preprocessing:", rt.get("preprocessing_id") or "-")
print("model_id:", rt.get("model_id") or "-")
print("sha256:", rt.get("model_sha256") or "-")
print("ai_status:", rt.get("ai_status") or "-")
print("blocked:", rt.get("blocked_reason") or "-")
PY
```

프레임이 아직 없어도 selector는 나와야 한다. `ai_status=BLOCKED`여도 **선택된 모델**은 맞다. 추론 성공과 섞지 말 것.

---

## 4. LCD 화면 띄우기

서버 기동 ≠ LCD Chromium 기동.

1. 백엔드가 `:8000`을 듣고 있어야 한다.
2. `/display`가 HTTP 200이어야 한다.

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/display
# 기대: 200
```

3. Chromium은 **Pi 그래픽 세션**에서 연다. SSH만으로는 물리 LCD가 안 바뀐다.

```bash
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
[ -f "$HOME/.Xauthority" ] && export XAUTHORITY="$HOME/.Xauthority"

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
```

일반 창:

```bash
DISPLAY=:0 chromium http://127.0.0.1:8000/display &
```

현재 팀 `main`의 `backend/app.py`가 `/display`를 `RaspberryPi/LCD/static/display.html`로 서빙한다.

---

## 5. 필드 모니터

모니터는 **하나**다. baseline / A / B용 별도 스크립트 없음. 실행 중인 프로세스의 `/api/status`를 읽는다.

```bash
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py
python3 hil/pi_field_monitor.py --once
python3 hil/pi_field_monitor.py --interval 2
python3 hil/pi_field_monitor.py --raw-labels
```

원격:

```bash
python3 hil/pi_field_monitor.py --base http://<PI_IP>:8000
```

`Ctrl+C`는 모니터만 종료한다. SafeNest 백엔드는 그대로다.

헤더 예:

```text
SafeNest field monitor  |  2026-08-31 15:10:00  |  Δ window 4.0s
Thermal: A | thermal_tv2_candidate_a_a0_fp32_v1 | FRAME_ROBUST_P2_P98_V1
```

| 헤더 | 의미 |
|---|---|
| `Thermal: BASELINE \| thermal_public_sdt_fp32_active \| …` | 기본/비교 baseline |
| `Thermal: A \| thermal_tv2_candidate_a_a0_fp32_v1 \| …` | Candidate A |
| `Thermal: B \| thermal_tv2_candidate_b_seed42_fp32_test_v1 \| …` | Candidate B |
| `Thermal: UNKNOWN \| <raw>` | 매핑에 없는 selector. 원문을 그대로 둠 |
| `Thermal: UNAVAILABLE \| selector=-` | `/api/status`에 selector가 없음 |

이 줄은 프로세스 선택 결과다. Thermal AI가 유효한 예측을 내고 있는지는 아래 표의 `thermal` 행 (`status`, `ai`, `err`)과 Verdict `UDP flow`를 본다.

짧은 라벨 `FALL_PX` = `HUMAN_FALL_PROXY` (자세 프록시). 실제 낙상 확정이 아니다.

---

## 6. 모델 비교 순서

과학 검증 프로토콜이 아니다. 같은 자리에서 세 모델을 한 번씩 보는 현장 비교다.

1. 카메라/사람 위치를 최대한 고정한다.
2. baseline 기동 → 모니터/LCD 확인 → 서기 / 앉기 / 숙이기 / 웅크리기 / 누운 자세를 가능한 만큼.
3. 런타임 종료. 포트가 비었는지 확인.
4. Candidate A 기동 → 같은 조건 반복.
5. 런타임 종료.
6. Candidate B 기동 → 같은 조건 반복.

볼 것 (짧게):

- 헤더 Thermal 모델이 방금 켠 것과 일치하는가
- UDP thermal frames `Δ`가 증가하는가
- thermal sensor `LIVE`
- Thermal AI 상태 (`WARMUP` / 클래스 / `FALL_PX`)
- `HUMAN_NORMAL` → `HUMAN_FALL_PROXY` 전환이 수상하면 기록만. 실제 낙상으로 쓰지 말 것
- latency가 보이면 참고
- risk는 bounded proxy 유지
- LCD state

환경이 비슷할수록 비교가 쉽다. 기기 도메인 최종 검증은 아니다.

---

## 7. 중지 / 재시작 / 모델 변경

핫 스위칭 없음. 반드시 종료 후 다른 선택으로 다시 기동.

```bash
cd /home/sandi/safenest-team-main

# LCD Chromium (백엔드와 별개)
pkill -f "chromium.*8000/display" 2>/dev/null || true

# 백엔드
kill "$(cat .runtime.pid)" 2>/dev/null || true
pkill -f "backend/run_backend.py" || true

ss -ltnp | grep -E ":8000|:9000" || echo "tcp free"
ss -lunp | grep 5005 || echo "udp free"
```

그다음 2절에서 다른 모델을 기동한다.

---

## 8. 포트 / URL

| 포트 | 용도 |
|---|---|
| TCP `:8000` | FastAPI / Web / LCD `/display` / admin |
| TCP `:9000` | ESP 스칼라 텔레메트리 (mmWave / CO₂ / PIR) |
| UDP `:5005` | ESP 열화상 프레임 |

| 경로 | 용도 |
|---|---|
| `http://<PI_IP>:8000/display` | LCD |
| `http://<PI_IP>:8000/admin` | 관리 |
| `http://<PI_IP>:8000/dashboard` | 대시보드 |
| `http://<PI_IP>:8000/health` | liveness |
| `http://<PI_IP>:8000/api/status` | 센서·AI·risk·Thermal `runtime_status` |
| `http://<PI_IP>:8000/api/state` | LCD 상태 |

---

## 9. 로그 확인

| 파일 | 언제 |
|---|---|
| `logs/runtime.log` | `./run_safenest.sh` 백그라운드 |
| `logs/runtime-thermal-baseline.log` | 비교 런처 baseline 백그라운드 |
| `logs/runtime-thermal-a.log` | Candidate A 백그라운드 |
| `logs/runtime-thermal-b.log` | Candidate B 백그라운드 |
| `/tmp/chromium-display.log` | LCD Chromium |

```bash
tail -f logs/runtime-thermal-a.log
```

기동 직후 아래가 보여야 한다 (백엔드 `ai/runtime.py`):

```text
[SafeNest Thermal]
THERMAL SELECTOR: …
MODEL ID: …
MODEL SHA: …
PREPROCESSING: …
CONTROLLED TEST MODE: 0 또는 1
```

비교 런처는 추가로:

```text
[SafeNest Thermal Test]
choice: a
selector: thermal_tv2_candidate_a_a0_fp32_v1
```

---

## 10. 문제 발생 시 빠른 점검

| 증상 | 볼 것 |
|---|---|
| `:8000` 안 열림 | `pgrep -af run_backend.py`, `ss -ltnp \| grep 8000`, 로그 `tail` |
| `/display` → 404 | 현재 `main`이면 `app.py`에 라우트가 있어야 함. 옛 클론/옛 프로세스가 `:8000`을 잡고 있지 않은지 |
| `/display` 200인데 LCD 검정 | Chromium `DISPLAY=:0`인지, 옛 Chromium이 다른 페이지를 띄웠는지, `/tmp/chromium-display.log` |
| Chromium 프로세스만 있고 화면 없음 | 잘못된 `DISPLAY`, `XDG_RUNTIME_DIR=/run/user/1000`, `XAUTHORITY` |
| 모니터 헤더가 기대한 모델이 아님 | 이전 프로세스가 안 죽었거나, 다른 클론을 기동함. 종료 후 다시 |
| selector는 맞는데 Thermal AI가 BLOCKED | 정상일 수 있음 (UDP 없음 / STALE / WARMUP). 선택과 추론을 분리해서 볼 것 |
| 모델을 바꿨는데 화면이 그대로 | 핫 스위칭 없음. 종료 확인 후 재기동 |

---

## 11. 모델 의미 / 제한사항

| 선택 | selector | 오프라인 상태 | 전처리 |
|---|---|---|---|
| Team 기본 / 비교 baseline | `thermal_public_sdt_fp32_active` | 현재 런타임 기본 | 프레임 min-max (`PUBLIC_SDT_BILINEAR_62X80_FRAME_MINMAX_V1`) |
| A | `thermal_tv2_candidate_a_a0_fp32_v1` | A_PREFERRED, CONTROLLED_TEAM_TEST, 기본값 아님 | `FRAME_ROBUST_P2_P98_V1` |
| B | `thermal_tv2_candidate_b_seed42_fp32_test_v1` | B_NOT_COMPETITIVE, CONTROLLED_COMPARISON_ONLY | 같은 robust 전처리 |

A/B는 프레임 안 2%/98% percentile로 상대 명암을 정규화한다. baseline과 입력이 다르다. 선택기가 모델과 전처리 경로를 같이 고른다.

입력 geometry는 `TEAM_RUNTIME_62X80_AS_RECEIVED_EXPERIMENTAL_BRIDGE`다. 기기/소스 geometry 검증은 아직이다.

공통:

- `HUMAN_FALL_PROXY` = 정적 누운/자세 프록시. **실제 낙상 확정이 아니다.**
- 임상 검증 아님. 기기 도메인 검증 아님. production 승인 아님.
- risk 공식·임계값·CO₂·mmWave는 그대로다. Thermal은 bounded proxy만.
- Candidate A가 오프라인에서 낫다고 해서 Team default가 바뀐 것이 아니다.
- Candidate B는 비교 전용이다. 선호 모델이 아니다.
