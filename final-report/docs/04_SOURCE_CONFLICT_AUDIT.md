# 04_SOURCE_CONFLICT_AUDIT

Priority: ① Official docs ② Canonical source snapshot ③ Actual evidence ④ Team reports ⑤ Initial plan ⑥ External.
Snapshot = `jinsu1011/safenest-embedded-competition` @ `3f22fb145c…`, branch `codex/mmwave-m-c0-correspondence`, archived 2026-08-21 21:59 KST.

| # | Topic | Older / other source | Newer / canonical source | Interpretation | Report wording |
|---|---|---|---|---|---|
| **C1** | **Web/Backend stack** | 중간계획서: "Python(FastAPI) 게이트웨이 · SQLite 로그 DB · Chart.js 대시보드". 강유나 최종본: "Backend FastAPI · WebSocket · SQLite", HTTP 8000, `backend/app.py` | **Snapshot: FastAPI / SQLite3 / WebSocket 문자열이 401개 코드 파일 전체에 0건.** 실제는 `integration/pi_lcd/server.py` (Python **stdlib http.server**, HTTP 8080) + `integration/web` (**Express 5**) | 계획·타 브랜치의 스택이 정본에 병합되지 않음 | 보고서는 **정본 구현만** 기술: stdlib HTTP 서버 + Express. FastAPI/SQLite/WebSocket **언급 금지** |
| **C2** | **강유나 작업 브랜치 미병합** | 강유나 최종본: repo `yuname121/integration`, commit `9e4ddfe770d5…`, 파일 `gateway/protocol.py`, `receiver.py`, `thermal_udp.py`, `backend/`, `web/dashboard/`, `web/portal/`, `services/buzzer.py`, `services/emergency.py`, `deployment/run_pi.sh`. 자체 검증 "Python 153 tests OK" | **정본 스냅샷에 `gateway/`, `backend/`, `web/` 디렉터리 자체가 없음** (확인: `ls` → No such file or directory) | 병렬 개발 브랜치가 정본에 **미병합**. 153 tests는 정본에서 재현 불가 | 정본 기준으로 기술. 강유나 기여는 **정본에 실재하는 산출물**(display-test2 ESP32 노드, `raspberry_pi_lcd` 초기 서버, STL 4종, 설계사양 2종, PIR 어댑터)로 한정. 미병합 사실은 **팀장 확인 필요**로 내부 기록 |
| **C3** | **Thermal 전송 경로** | 중간계획서: XIAO에서 UDP로 Pi 전송. 김태균 v5 검증(2026-08-11): **XIAO-ESP32C6 단독 + UDP 5005 + 1,440 B 청킹**, ~7 FPS. 강유나: **UDP 5005 + SNTU v1 32 B 청크 헤더 + CRC32 + 9개 datagram(≤1,200 B)** | **정본 ESP32 노드: TCP 단일 연결, `PACKET_THERMAL_U16_BE`(type 2) 정의는 있으나 `THERMAL_STREAM_FRAMES = false`로 전송 비활성.** 실제로는 최고온도만 1 s telemetry에 포함 | **3세대 아키텍처가 병존**. 동시 설계가 아님 | 4번 항목(장애요인)에서 **시간 순 진화**로 서술: TCP 전 프레임 스트리밍 → telemetry 침해 확인 → 태스크/큐/청크/분주비/클럭 시도 → 대역폭 문제 잔존 → **정본은 송신측 요약(최고온도)으로 전환**. 별도 열화상 리그는 **UDP 분리 경로**로 검증되었음을 구분 표기 |
| **C4** | **UDP 청크 크기** | 김태균: 1,440 B | 강유나: ≤1,200 B, 9개 | 서로 다른 리그/브랜치 | 수치 단정 금지. "MTU 회피를 위한 청킹" 수준으로 기술하거나 출처를 명시 |
| **C5** | **MCU 보드** | 중간계획서·초기: **XIAO ESP32-C6** (RISC-V) | 정본 `.ino`: **ESP32 Dev Module / ESP-WROOM-32 DevKit V1**, 10개 신호선 단독 핀, RESET D25 | 보드 교체 확정 | "GPIO 자원 제약 → 보드 교체 → 열화상 nRESET 제어 확보 → 30 s 무프레임 자동 복구 가능" 인과로 기술. 단 **유승하 보고서가 인과를 `[검증 필요]`로 표기**했으므로 "기록된 제약 사실 + 결과"로만 서술 |
| **C6** | **열화상 센서 명칭** | 계획·정본: **Thermal-44 Camera** (80×62) | 김태균 최종검증문: "**Thermal-90 모듈**", 동시에 "Thermal-44 V5"도 사용 | 명칭 불일치 | 보고서는 정본 기준 **Thermal-44 (80×62, MI48xx)** 사용. Thermal-90 표기는 인용하지 않음. **팀 확인 필요** |
| **C7** | **AI 모델 검증 등급** | `model_manifest.json` (생성 2026-07-25): thermal·co2 = `CONFIRMED_SYNTHETIC_ONLY` | `03_Evidence/Thermal/*` (2026-08-11): 실 Thermal 프레임 → Pi 5 → 실 INT8 TFLite E2E ALL PASS | **매니페스트가 열화상에 한해 구식** | 열화상은 **실기기 E2E 검증**으로 상향 기술. CO₂·mmWave 모델은 **합성/오프라인 한정** 유지 |
| **C8** | **mmWave 모델 상태** | 계획: 1D-CNN/LSTM으로 무호흡 분류 | v0.1.0 `BLOCKED` (class collapse, acc 0.3996, abnormal/apnea recall 0.0) / v0.2.0 후보 acc 1.0이나 `SYNTHETIC_SMOKE_ONLY`·`NOT_VERIFIABLE` | 배포 가능한 검증 모델 없음 | **"재현성 검증 → 클래스 붕괴 발견 → 배포 차단"**을 공학적 성숙도 근거로 서술. acc 1.0은 **합성 한정**임을 같은 화면에 명시 |
| **C9** | **낙상 감지** | 계획: 낙상 시나리오. 김태균 v5 결론문: "인체 낙상 징후를 명확히 구분해냄" | 동일 문서 시나리오 D = "**안전하게 눕기**" → `HUMAN_FALL`. 김태균 본보고서 L47/490-491: LYING 정적 자세 프록시, 실제 낙상은 자세 전이·충격·지속·회복 실패 필요 | **낙상 사건 검증 아님** | "**눕기(LYING) 자세 기반 위험 후보 상태**", "정적 자세 proxy". `낙상 감지 완료`·`낙상 정확도` **금지** |
| **C10** | **Raspberry Pi AI 지연** | `MISSING_INPUTS.md`: "Actual Raspberry Pi AI latency — MISSING" | `phase11_12_fail_closed_benchmark.md`: Pi 5 실측 E2E mean 167.92 / p50 162.70 / p95 173.90 ms, 4.6 FPS | **열화상 채널 한정 실측은 존재** | "열화상 채널 실기기 E2E 지연"으로 **범위를 명시**하여 사용. 전 시스템 경보 지연으로 일반화 금지 |
| **C11** | **ESP32→Pi 실통신** | `MISSING_INPUTS.md`: NOT VERIFIED | CO₂ 검증 리포트: ESP32 `192.168.1.16` → Pi 5 `192.168.1.44:9000` TCP, 4개 세션 실측 | **CO₂ 단일 채널 실경로는 검증됨**; 4센서 동시는 미검증 | "CO₂ 채널 기준 ESP32→Pi 실경로 검증", "4센서 동시 수신 미검증"으로 분리 서술 |
| **C12** | **CO₂ 임계값** | 유승하 표: NORMAL 400–600 / CAUTION >1,000 / WARNING ≥1,500 / EMERGENCY ≥2,000. 구 스냅샷 `co2_ppm > 1500` 성분 1.0. 08.24 보고서는 별표2를 1,500만 적고 기본 1,000을 빠뜨림 | **현재 정본 `risk_formula_v1.json` 1.2.0**: 절대 주의 ≥1,500 ppm(별표2 비고), 밀실 기준값 \(B\)+700 상대 주의, 2,500 ppm도 주의 플로어, 즉시 위험 ≥5,000 ppm. 별표2 기본 1,000은 트립 아님. occupancy 모델은 점수 제외 | 유승하 2,000 EMERGENCY와 V4 1,500=위험은 **폐기**. 필드 idle ~1,184 ppm을 1,000 주의로 올리면 상시 경보 | 보고서 P10은 v1만 기술. "안전기준 준수" 금지. 출처 표는 `09_SAFETY_CRITERIA_V1.md` |
| **C13** | **LCD 아키텍처** | `display-test/`, `display-test2/raspberry_pi_lcd/` (독립 수신·상태) | 정본 `integration/pi_lcd/server.py` (동일 계보의 최신본, 테스트 13종) | 레거시 2벌 + 정본 1벌 | 정본만 현재 런타임으로 기술. display-test·display-test2는 **초기/레거시**로 구분 |
| **C14** | **테스트 수** | 강유나: "153 tests OK"(자기 브랜치). `INTEGRATION_PROGRESS.md`: "84 tests OK, skipped=2". `PROJECT_PROGRESS.md`: "devices 46 passed, on-device/provider 23 passed" | 저장소 정적 카운트 **1,483 `def test_`** / **본 세션 실행 57 passed, 2 failed** | 시점·범위가 모두 다름 | 숫자를 합치지 않음. 보고서에는 **본 세션 실행값**과 **소스 내 테스트 함수 수**를 분리 표기 |
| **C15** | **응용 범위 드리프트** | 계획: 밀폐공간 + 통학차량. 강유나 최종본: "실내 안전 모니터링", 김태균 자료조사: 독거노인·고령자 | 정본 QR: `밀폐공간_A-01`, `통학차량_B-02`, `창고_C-03` | 1차 범위는 밀폐공간·차량 | 주 적용처 = **밀폐공간**, 부 = **차량 내부**. 고령자·독거 시나리오는 **확장 가능성**으로만 |
| **C16** | **중간계획서 출처** | `01_Initial_Plan` 원본 파일명 = `창의혁신공모전_중간계획서`, 제목 = "제5회 창의혁신 공모전 중간계획서" | 본 대회는 제24회 임베디드SW경진대회 | **타 공모전 제출 계획서** | 대회 보고서에서 계획서를 인용할 때 **본 대회 제출물로 오인될 표현 금지**. 규정 제10조④ 관련 사실은 정확히만 기술 |
| **C17** | **Thermal frame 요청 FPS** | 강유나: "약 6.25 FPS, divider 4 기준" | 정본 `.ino`: `THERMAL_FRAME_RATE_DIVIDER = 8` → 약 3.125 FPS | 강유나는 구(display-test2) 펌웨어 기준 | 정본 값(divider 8, ~3.125 FPS, 1 MHz에서 프레임당 ~81 ms) 사용 |
| **C18** | **display-test2 펌웨어에 CRC 없음** | 유승하 문제#5: CRC-16/CCITT-FALSE 도입 | 정본 `devices/esp32_node` 에 `thermalFrameCrc()` **존재**, `display-test2` 펌웨어에는 **없음** | CRC는 정본에만 반영 | CRC 관련 서술 시 **정본 파일 경로**를 근거로 표기 |

## 처리 원칙

1. 서로 다른 세대의 아키텍처를 **동시 설계인 것처럼 합치지 않는다**.
2. 정본에 없는 구성요소(FastAPI·SQLite·WebSocket·gateway·backend·web/dashboard)는 **보고서에 등장시키지 않는다**.
3. 팀원 보고서의 결론 문장이 같은 문서의 데이터와 충돌하면(**C9**), **데이터를 따른다**.
4. 범위가 다른 실측치(**C10, C11**)는 삭제하지 않고 **범위를 명시**하여 사용한다.
