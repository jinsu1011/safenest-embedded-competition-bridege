# 이어서 작업하기 — Claude Code 프롬프트

다른 PC에서 이어서 할 때 아래 `===` 사이를 그대로 Claude Code 에 붙여넣는다.

## 먼저 할 일

```bash
git clone https://github.com/jinsu1011/safenest-embedded-competition.git
cd safenest-embedded-competition
git checkout report/final-report      # 브랜치명은 실제 푸시된 이름으로
cd final-report/generator && npm install
```

macOS + Keynote 가 있어야 PDF 변환이 된다. 없으면 PPTX 편집·생성까지만 가능하다.

---

===============================================================

너는 내 PC에서 Claude Code로 동작한다.
제24회 임베디드SW경진대회(2026) 자유공모 부문 **SafeNest 개발완료보고서**를 이어서 수정한다.

**새로 만들지 마라.** 이미 완성된 21슬라이드 산출물을 수정하는 작업이다.
`DO NOT rebuild from scratch.`

## 0. 작업 폴더

저장소를 clone 한 뒤 `final-report/` 안에서 작업한다.

```
final-report/
├── README.md               ★ 빌드 방법·편집 규칙. 먼저 읽어라
├── HANDOFF.md              ★ 지금까지 한 일과 남은 일. 먼저 읽어라
├── generator/build.js          ★ 슬라이드 편집 원본 (PptxGenJS). 모든 수정은 여기서
├── generator/rebuild.sh        PPTX 생성 → Keynote PDF export → PNG 렌더
├── generator/charts/make_charts.py   차트 생성 (원본 증거 패키지 필요, 보통 쓸 일 없음)
├── assets/                 보고서 삽입 이미지
├── previews/chart_*.png    P1·P11 삽입 차트
├── previews/pdf/p-01~21.png   페이지별 렌더
├── docs/00~08, 11          근거·감사 문서
└── 2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pptx / .pdf
```

## 1. 수정 전 필독

1. `HANDOFF.md` — 현재 상태, 남은 일
2. `README.md` — 빌드 방법, Keynote 함정, 편집 규칙
3. `docs/04_SOURCE_CONFLICT_AUDIT.md` — 자료 충돌 18건 해소 결과. **이걸 어기면 사실관계가 틀어진다**
4. `docs/03_CLAIM_EVIDENCE_LEDGER.md` — 강한 주장의 허용/금지 표현
5. `generator/build.js` 전체
6. `previews/pdf/p-01.png ~ p-21.png` 전 페이지 육안 확인

## 2. 작업 방식 — 반드시 이 순서

1. **`generator/build.js`만 편집한다.** PPTX/PDF 를 직접 편집하지 마라. 재빌드 때 덮어써진다.
   슬라이드는 `/* ====== P1 ====== */` ~ `P20` 주석으로 구분되어 있다.
   헬퍼: `page(n,title,sub)` · `box()` · `badge()` · `hdr()` · `sub()` · `note()` · `cap()`
2. 재빌드: `bash final-report/generator/rebuild.sh`
3. **재빌드할 때마다 렌더된 PNG를 Read 도구로 열어 눈으로 확인한다.** 텍스트 넘침·겹침이 자주 난다.
4. 슬라이드 21장 / PDF 21페이지 / PNG 21장인지 확인한다.

**Keynote 함정** (README.md 에도 있음)
- 이전 실행의 Keynote 문서가 남아 있으면 export 가 AppleEvent 타임아웃(-1712)으로 실패한다. `killall Keynote` 후 재시도.
- export 는 됐는데 `close`/`quit` 에서 타임아웃 나면 **PDF 는 이미 정상 생성된 것이다.** PNG 렌더만 따로 돌려라:
  `cd final-report/previews/pdf && rm -f p-*.png && pdftoppm -png -r 70 "../../2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf" p`

## 3. 절대 규칙 (어기면 대회 규정 위반)

- **날조 금지**: 정확도·지연·오탐률·가용성·시장규모·매출·테스트 결과·사진·팀 기여를 지어내지 마라.
  증거가 없으면 `미검증` / `[추가 검증 필요]`로 쓴다. (대회 규정 제10조④: 제작 사실 허위 시 수상 취소)
- **콘텐츠 20페이지 초과 금지.** 표지 제외 20p까지만 평가된다. 현재 표지1+본문20 = 21슬라이드로 꽉 차 있다.
  **무언가를 추가하려면 반드시 무언가를 빼야 한다.**
- 공식 분량 배분 유지: 개발개요 3p(P1–3) / 환경·프로그램·장애요인 10p(P4–13) / 차별성·파급력 5p(P14–18) / 일정·업무분장 2p(P19–20)
- **초기 개발 목표(KPI)를 달성 결과로 바꾸지 마라.** (정확도 ≥95%, 경보 ≤2초, 오탐 ≤5%/hr, AI ≤100ms, 가용성 ≥99% — 전부 미달성)
- **합성 데이터 결과를 실센서 성능으로 쓰지 마라.** (mmWave v0.2.0 정확도 1.0은 합성 468샘플 한정)
- 금지 표현: `낙상 감지 완료` `낙상 정확도` `체온 측정` `호흡 질환 진단` `세계 최초` `완벽한` `100% 안전` `의료급` `상용화 완료` `실시간 보장`
- **문체 규칙** (이미 전체 적용됨, 유지할 것):
  제목은 전부 명사형 + 번호 체계(`1.1`). em dash(`—`) 사용 금지. `A가 아니라 B` · `핵심은` · `본질적으로` 같은 패턴 금지.
  컬러 콜아웃 박스는 4개(P6·P9·P16·P17)만 유지하고 늘리지 마라.

## 4. 반드시 알아야 할 사실 관계 (조사 완료 — 다시 조사하지 마라)

**정본 소스 스냅샷** = `jinsu1011/safenest-embedded-competition` @ `3f22fb145c…`, 1,904개 파일.

### 실제 구현된 것 (보고서에 써도 되는 것)
- ESP32 Dev Module 4센서 노드 `devices/esp32_node/firmware/esp32_sensor_node.ino` (741줄)
  - mmWave MR60BHA2 **UART2** 115200 (RX16/TX17) · SCD40 **I2C** 0x62 (SDA21/SCL22) · PIR **GPIO13** · Thermal-44 MI48xx **I2C 0x40·0x41 + SPI 1MHz** (SCLK18/MISO19/MOSI23/CS27/READY26/RESET25)
  - **SafeNest TCP protocol v1**: 16B 헤더 `SNST`+version+type+flags+seq+payload_length, network byte order
  - **`formatNullableFloat()`** — 무효값을 0이 아닌 `null`로 전송 + `valid{}` 블록
  - **CRC-16/CCITT-FALSE** (poly 0x1021, init 0xFFFF) `thermalFrameCrc()`
  - **`recoverThermalIfStale()`** — 30초 무프레임 시 GPIO RESET 재초기화
  - `THERMAL_STREAM_FRAMES = false` — 열화상 전 프레임 전송 **비활성**, 최고온도만 1초 telemetry에 실음
  - staleness: mmWave 5s / CO₂ 15s / Thermal 30s, `delay()` 미사용 + FreeRTOS 태스크 + 1-slot 큐
- Pi 수신·표시 `integration/pi_lcd/server.py` — **Python 표준 http.server**, TCP 9000, HTTP 8080, 상태 6종, 부저 BCM GPIO18 880Hz
- 위험도 `RaspberryPi/Runtime/risk/formula_v1.py` — R = 100×(0.25·mmWave+0.30·CO₂+0.15·PIR+0.30·Thermal), 정상<30/주의 30–65/위험≥65
  - 정책 정본 `final-report/docs/09_SAFETY_CRITERIA_V1.md`
  - **전 센서 무효 → `risk_score=None`, `risk_level=None`, `system_health=FAILED`**
  - 유효 센서만 가중치 재정규화. CO₂ ≥1,500 ppm 또는 밀실 기준값 \(B\)+700 주의. ≥5,000 ppm 즉시 위험. occupancy는 점수 제외
  - 열화상 프록시는 비상 없음. mmWave 신경망 관측 전용, 하드웨어 확인 apnea만 즉시 위험
- 웹 `integration/web/` — **Express 5** (bcryptjs·jsonwebtoken·qrcode), QR 공간코드 3종
- 외함 `hardware/3d_models/` — STL 4종. **출력·조립 완료** (체결·발열 확인은 미검증)

### ⚠ 정본에 **없는** 것 (보고서에 쓰면 안 됨)
- **FastAPI · SQLite3 · WebSocket — 코드 401개 파일 전수 검색 결과 0건.**
- `gateway/`, `backend/`, `web/dashboard/`, `web/portal/`, `services/` 디렉터리 — 존재하지 않음
- 강유나 최종 보고서의 `gateway/`·`backend/`·UDP 5005·FastAPI·"153 tests"는 별도 브랜치 `yuname121/integration`에 있고 **정본 미병합**

### 실측 수치 (전부 원시 증거 기반, 그대로 인용 가능)
- 열화상 Pi 5 실기기 E2E: mean 167.92 / **p50 162.70 / p95 173.90** ms, 4.6 FPS, 유효 135/138 (97.8%), 30.06초 138회
- 열화상 fail-closed 6종(순서위반·NaN/Inf·형식오류·물리적 단선·복구·close후read) 실기기 PASS
- mmWave 라이브: 9.990 Hz, 1,201 레코드, UART/checksum/parser 오류 **0/0/0**, 시퀀스 누락 0, 199/199 파싱
- mmWave 리플레이: presence 1.0@0.6·0.9m, 0.814@1.2m, 0.880@1.5m(lock loss, 유효창 0) / 호흡 MAE 0.270rpm@12, 0.275@15, 0.550@20
- CO₂ 실측 4세션(2026-08-12, ESP32 192.168.1.16 → Pi 192.168.1.44:9000): preflight 30/30 · baseline 최초 277/300(결측 7.67% **FAIL, 원본 보존**) · 재측정 300/300(0%) · 호기 6분 329/360(8.61%), **최고 1,493 ppm, 종료 634 ppm**
- ESP32 빌드: RAM 32,356/327,680 = **9.9%**, Flash 268,765/1,310,720 = **20.5%**
- **직접 실행한 테스트: 57 passed / 2 failed** (실패 2건 = 패키지 내 manifest 파일 부재)
  - 저장소 내 `def test_` 총 1,483개(99파일) — **이건 함수 개수다. "1,483 통과"로 쓰면 안 됨**
- **P10 계산 예시** (`formula_v1.py` 실행): CO₂ 1,500 ppm + 평온 인체 → **R = 9.75 정상, 플로어 `co2_warning` → 주의**, 비상 아님

### AI 모델 3종 상태 (`ondevice_ai/models/model_manifest.json`)
| 모델 | 상태 |
|---|---|
| `thermal_fall_int8_v0.1.0` | 실기기 E2E 검증됨. 단 **HUMAN_FALL = 눕기(LYING) 정적 자세 프록시**. 시간축 낙상 검증 아님 |
| `co2_occupancy_int8_v0.1.0` | 공개 데이터 오프라인 한정, 실센서 평가 없음 |
| `mmwave_resp_int8_v0.1.0` | **배포 차단** — `CLASS_COLLAPSE_ON_REPOSITORY_NPZ`, acc 0.3996, macro-F1 0.19, abnormal/apnea recall 0.0 |
| `mmwave_resp_int8_v0.2.0` 후보 | acc 1.0이지만 **합성 468샘플 한정**, `real_sensor_performance: NOT_VERIFIABLE` |

### 임계값 외부 근거 (조사 완료)
- **CO₂ 1,500 ppm** = 실내공기질 관리법 시행규칙 **별표2** 기계환기 시설 유지기준과 동일한 값. **주의 구간**이지 즉시 위험이 아님
- 법정 적정공기 = 산업안전보건기준에 관한 규칙 **제618조** (CO₂ 1.5 % 미만 = 15,000 ppm, 산소 18~23.5 %)
- **위험도 30/60 과 CO₂ 2,000 ppm 은 팀 내부 실험 기준값** — 공인 기준 아님. P10에 명시되어 있다

### 선행 사례 (P15 반영 완료)
- Vayyar Care (상용) — 60 GHz 4D 레이더 낙상 감지, 카메라·마이크 없음, 1대 약 16 m², 낙상 3단계 구분. 환경 가스 감시 없음
- TI IWR6843 (상용 부품) — 60~64 GHz FMCW 단일칩, 재실·생체신호 레퍼런스 공개
- arXiv 2403.05634 (2024) — TI 레이더 3대, 낙상 감지 정확도 96.3 % 보고
- 세 사례 모두 공개 자료에서 **무효·결측 인지와 판단 보류 정책을 확인할 수 없었다** → `확인 불가` 로 표기

### 데이터셋 라이선스
- mmWave: Zenodo vital-sign, DOI `10.5281/zenodo.18599983`, **CC BY 4.0**
- Thermal: SDT Dataset, TU Wien/Zenodo `4124309`, **라이선스 조건 확인 중**
- CO₂: UCI Occupancy Detection ID 357, **CC-BY-4.0**

### 팀 5인 (근거: `.github/CODEOWNERS`)
- 김진수(팀장, @jinsu1011): mmWave 펌웨어·실측, 저장소 구조, 문서
- 유승하(@yuseungha): CO₂/SCD40, ESP32 4센서 노드 펌웨어, Pi LCD·부저, 회로
- 김태균(@rla1729): Thermal-44 드라이버·파서, 열화상 온디바이스 AI 실기기 검증
- 한준우(@sheepmeat): 데이터셋·모델 학습/재현/배포판단, Pi AI, 위험판단 연계
- 강유나(@yuname121): PIR 어댑터, 3D 하우징 CAD·출력, LCD·Web 초기 골격

## 5. 현재 상태

**보고서는 완성 상태다.** 21장 전 페이지 육안 검수 완료. AI 문체 지문 제거 완료
(em dash 0 / 서술형 제목 0 / `라벨 — 설명문` 0 / 콜아웃 박스 4개 / 금지어 0).

**남은 것은 사용자가 채워야 하는 빈칸 2개뿐이다:**
- **P3 소스코드 (GitHub) 밑줄** — 저장소 URL. 공식 명명규칙은 `2026ESWContest_free_가만있어도SANDI` 이므로 rename 여부 결정 필요
- **P3 시연동영상 (YouTube) 밑줄** — 아직 촬영 전. 예선 필수 제출물

두 칸 모두 지금은 **깨끗한 빈 밑줄**이다(빨간 안내문구 없음). URL이 정해지면 `build.js` 의 P3 블록에서 밑줄 위에 `hyperlink` 텍스트만 추가하면 된다.

**문서로는 못 메우는 갭 (임의로 완료 처리하지 마라):**
4센서 동시 수신 실기기 로그 · 통합 HIL · AI 최종 성능 · 실제 낙상 검증 · 하우징 체결/발열 확인 · 최종 시연영상
→ 새 증거를 받기 전까지 현재 표기(`미착수` / `미검증` / `[추가 검증 필요]`)를 그대로 유지한다.
단 문서 전체를 미완성 프로젝트처럼 보이게 하지도 마라. 실제 완료된 것은 자신 있게 구현 결과로 쓴다.

## 6. 이번에 할 일

<<< 여기에 원하는 수정을 적으세요. 예시:
- "시연영상 올렸어: <YouTube URL> — P3에 넣어줘"
- "저장소 이름 2026ESWContest_free_가만있어도SANDI 로 바꿨어 — P3 GitHub 칸 채워줘"
- "4센서 동시 수신 로그 찍었어: <파일 경로> — P11이랑 P16 업데이트해줘"
- "하우징 발열 테스트 했어: <결과> — P18 반영해줘"
- "P15에 선행 연구 1건 더 추가해줘: <논문 DOI>"
>>>

작업 후에는 반드시 `rebuild.sh`를 돌리고, 바뀐 페이지의 `previews/pdf/p-XX.png`를 열어 레이아웃을 눈으로 확인한 뒤 결과를 한국어로 보고해라.

===============================================================
