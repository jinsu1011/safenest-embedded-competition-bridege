# SANDI 프로젝트 진행 기록

> [!NOTE]
> **경로 표기 안내 (2026-08-03 추가)**
> 이 문서는 시간순 작업 기록이므로 본문의 경로는 **기록 당시의 경로**를 그대로 둔다.
> 2026-08-03 책임 영역 재편(`38274c0`) 이후의 현재 경로는 아래와 같이 대응한다.
>
> | 기록 당시 경로 | 현재 경로 |
> |---|---|
> | `firmware/esp_wroom32_mr60_monitor/` | `devices/mmwave/firmware/` |
> | `src/sensors/<device>/` | `devices/<device>/src/` |
> | `src/sensors/base_sensor.py` | `shared/contracts/base_sensor.py` |
> | `src/inference|risk|integrated_node|training|tools/` | `ondevice_ai/src/` 아래 동일 이름 |
> | `models/`, `datasets/`, `config/` | `ondevice_ai/` 아래 동일 이름 |
> | `tests/`, `tests/benchmarks/` | `ondevice_ai/tests/`, `ondevice_ai/benchmarks/` (mmWave 기기 단독 4종은 `devices/mmwave/tests/`) |
> | `hardware/3d_print/` | `hardware/3d_models/` |
> | `SafeNest_V4_OnDevice_AI/` | `ondevice_ai/` |
>
> 전체 매핑과 무결성 검증 근거는 [`docs/architecture/BRANCH_PROVENANCE.md`](../architecture/BRANCH_PROVENANCE.md)에 있다.

## 2026-07-13 MR60BHA2 ESP 안정화 작업

### 작업 체크리스트

- [x] 필수 문서 4개와 저장소 지침 확인
- [x] 기존 ESP 코드, 설정, 원본 로그, 연결 장치, 빌드 도구 점검
- [x] ESP-WROOM-32로 장치 확정; MR60 버전 조회를 시도했으나 응답 없음(`UNKNOWN`), Seeed 라이브러리는 사용하지 않음
- [x] 무필터 기준선 수집: 빈 공간 5분
- [x] 무필터 기준선 수집: 가슴 정면 0.8~1.0m 안정 1인 5분
- [x] 무필터 기준선 수집: 진입→정지→퇴장 20회 및 ground truth 기록
- [x] 원본 로그를 보존하고 기준선 지표 계산
- [x] 동일 원본 로그에서 필터 또는 유효성 조건을 한 번에 하나씩 비교
- [x] 실측 근거로 ESP 상태기계와 텔레메트리 구현
- [x] 빈 공간/정지 인체 각 30분, 거리 4종, 진입·퇴장 20회 최종 검증(재실 PASS, 자연호흡 지속성 FAIL 한계 포함)

### 단계 0 점검 결과

- 저장소에는 현재 `PROJECT_PROGRESS.md`, `HARDWARE_RUNBOOK.md`, `MMWAVE_TUNING.md`, `TEAM_OPERATING_MODEL.md`와 PDF 임시 산출물만 있다.
- 기존 ESP 소스, `platformio.ini`, Arduino 스케치, config, CSV/JSONL 원본 로그는 발견되지 않았다. 따라서 보존하거나 회귀 비교할 기존 사용자 펌웨어가 현재 작업공간에는 없다.
- Git 저장소는 아직 커밋이 없는 `main`이며 기존 문서와 `tmp/`가 모두 추적되지 않은 상태다. 관련 없는 파일은 수정하지 않는다.
- PlatformIO Core 6.1.19는 설치되어 있으나 사용자 홈의 `.platformio/.cache` 권한 오류가 있다. 프로젝트가 생기기 전에는 홈 권한을 임의 변경하지 않는다.
- 확인된 직렬 포트는 `/dev/cu.debug-console`, `/dev/cu.Bluetooth-Incoming-Port`뿐이다. XIAO ESP32-C6/MR60BHA2로 식별되는 USB 직렬 장치가 없어 실측 수집과 펌웨어 버전 조회는 차단되어 있다.
- 하드웨어 전제: 키트 내부 UART D6/GPIO16 TX, D7/GPIO17 RX, 115200 8-N-1; ESP는 수집·검증·안정화·패킷화만 담당하고 정상/주의/위험 임계값은 Pi가 담당한다.
- 안전 전제: MR60 펌웨어는 현재 버전만 조회하며 승인 없이 업데이트하지 않는다. 결측, timeout, 0/NaN, 파싱·체크섬 오류는 정상 또는 무호흡으로 치환하지 않는다.
- 기준선 로그가 없으므로 `WARMUP_MS=60000`, 호흡 유효거리 40~150cm, presence 2-of-3, 5초 해제, median-5 등은 후보값으로만 유지하며 아직 적용·확정하지 않는다.

### 현재 게이트

`BLOCKED_FOR_MEASUREMENT`: XIAO/MR60 연결 및 기존 ESP 소스 또는 공식 예제의 정확한 버전이 필요하다. 차단 중에도 원시 로그 스키마와 수집·분석 도구는 준비할 수 있지만 필터 및 유효성 임계값 선택은 하지 않는다.

### 장치 연결 재확인

- 2026-07-13 현재 `/dev/cu.*`, `/dev/tty.*`, macOS USB 장치 트리, PlatformIO 장치 목록을 다시 확인했다.
- ESP/XIAO로 식별되는 USB 장치나 `/dev/cu.usbmodem*`, `/dev/cu.usbserial*` 포트가 나타나지 않았다. 보이는 포트는 macOS 시스템 포트 2개뿐이다.
- 따라서 현재 Mac에서는 XIAO가 데이터 장치로 연결된 상태가 아니다. 전원 LED가 켜져 있더라도 충전 전용 케이블, 허브/포트, 느슨한 USB-C 연결 가능성을 먼저 확인해야 한다.
- 2026-07-13 18:16 재확인에서 `/dev/cu.usbserial-10`과 `/dev/tty.usbserial-10`이 생성되었다.
- PlatformIO 식별 결과는 `USB VID:PID=1A86:7523`, 설명 `USB Serial`이다. CH340 계열 USB-UART 경로가 정상 열거되었으므로 현재 MR60 키트의 직렬 연결은 사용 가능한 상태로 판단한다.
- 이 확인에서는 포트를 열거나 DTR/RTS를 조작하거나 펌웨어를 업로드하지 않았다.

### ESP-WROOM-32 MR60 실시간 확인

- 실물 사진에서 ESP-WROOM-32 DevKit과 MR60BHA2 캐리어의 `GND/TX/RX`, XIAO 소켓 `5V/GND` 실크를 확인했다.
- `/dev/cu.usbserial-10`은 `VID:PID=1A86:7523`으로 정상 열거되었다.
- 115200 8-N-1 터미널을 열고 EN 리셋까지 수행했으나 기존 ESP 펌웨어는 부팅 로그나 MR60 측정값을 전혀 출력하지 않았다.
- 필터 없는 최소 측정 프로젝트 `firmware/esp_wroom32_mr60_monitor/`를 생성했다. UART2 GPIO16 RX/GPIO17 TX, 원시 재실·거리·호흡·심박·위상과 결측 `null`만 JSONL로 출력한다.
- ESP32 Arduino Core 3.2.0, Seeed mmWave 라이브러리 커밋 `a07b6c1a842512bff5bcd8266a8ede477d8a4df4`로 빌드가 완료되었다.
- ESP 업로드는 기존 플래시 펌웨어를 덮어쓰는 작업이므로 명시적 사용자 승인 전 단계에서 중단했다. MR60 레이더 펌웨어는 변경하지 않는다.
- 사용자가 ESP 펌웨어 덮어쓰기를 명시적으로 승인해 최소 측정 스케치 업로드를 완료했다. ESP는 `ESP32-D0WD-V3 rev3.1`, 4MB Flash로 식별되었다.
- 업로드 직후 MR60 원시 프레임은 약 9Hz로 수신되었고, 재실 `true`, 거리 `120.54cm`, 심박 `85~107bpm` 샘플을 관측했다. 호흡은 이 구간에서 `0/null`이므로 유효값으로 확정하지 않았다.
- 이후 재실 `false` 구간에서 거리·호흡·심박이 `0/null`로 출력되는 것을 확인했다. 대시보드는 이를 정상/무호흡으로 바꾸지 않고 `UNKNOWN`으로 표시한다.
- `mmwave_dashboard.py`와 `run_dashboard.command`를 추가하고 macOS Terminal 창에서 실행했다. Python 프로세스가 `/dev/cu.usbserial-10`을 점유해 실시간 읽기 중임을 `lsof`로 확인했다.
- 책상 위 배치 상태에서 원시 스트림을 직접 재검사했다. `presence=true`가 대부분이나 한 프레임짜리 `false`가 반복 삽입되었고, 거리는 약 `28.70~45.92cm`, 호흡 후보는 `0~19rpm`, 심박 후보는 `74~100bpm`으로 변동했다.
- 이 조건은 제조사 권장 설치(가슴 방향, 안정 자세, 1.5m 이내)와 기준선 조건(0.8~1.0m)에 맞지 않으며, 생체값 정확도나 재실 정확도를 주장할 수 없다. 책상 진동·근거리 사용자·반사체·잘못된 안테나 방향 후보를 분리 시험해야 한다.
- 원시 진단 후 macOS Terminal 대시보드를 다시 실행했고 Python PID가 직렬 포트를 읽는 것을 확인했다.

## 목표 및 성공 기준

중간계획서의 실제 설계와 평가 관점을 근거로, 대상 수상 수준을 향한 팀 운영 구조와 안전하고 재현 가능한 ESP 배선 및 mmWave 튜닝 실행 절차를 확정한다.

## 생활 체크리스트

- [x] 1. PDF 작업 지침과 작업공간 규칙 확인
  - 결과: `pdf` 스킬 전체 확인, 추가 `AGENTS.md` 없음, 첨부 PDF 및 원본 Pages 접근 가능.
- [x] 2. 중간계획서와 자유공모 안내서 교차분석: 핵심 내용, 평가·제출 요건, 미완성 항목 추출
  - 결과: 10P 계획서와 6P 안내서를 텍스트 추출하고 전 페이지 렌더링 확인. 핵심 MVP·KPI·공식 배점·제출 요건과 설계 공백을 식별함.
- [x] 3. 하드웨어 전제, 핀 충돌, 전원 위험 식별
  - 결과: 제조사 공식 문서로 XIAO/MR60BHA2/SCD40/Thermal-44 전기·인터페이스를 대조하고, Thermal-44 Pi 직결 구조 및 안전 경계 확정.
- [x] 4. ESP 배선 및 센서별 단독 검증 절차 작성
  - 결과: `HARDWARE_RUNBOOK.md`에 Gate A~E, 핀표, 전원 안전, 센서별 단독/통합 합격 기준 작성. `wc`/`rg`로 142줄과 필수 섹션 포함 확인.
- [x] 5. mmWave 설치·튜닝·시험·기록 절차 작성
  - 결과: `MMWAVE_TUNING.md` 152줄 작성. 거리/각도/자세, 60초 확립, UNKNOWN 처리, 안전 시험, 8h/24h KPI를 `rg`로 확인.
- [x] 6. 조장 + 조원 4명 역할 및 기본/별도 채팅·코드 분할 구조 작성
  - 결과: `TEAM_OPERATING_MODEL.md` 182줄 작성. 00~06 작업 채팅, 5인 단일 책임, 코드 경계, 완료 정의, 프롬프트·Git·보고 규칙 포함 확인.
- [x] 7. 요구사항 대비 최종 검증
  - 결과: 대상 전략, 두 PDF, ESP→Pi 책임경계, 단계적 배선, mmWave 튜닝, 5인/채팅 분할을 각 문서에서 검색 대조. `git diff --check` 통과.

## 현재 상태

- 사용자 제공 상태: 모든 센서 도착, ESP와 mmWave는 2026-07-10 작동 확인, Raspberry Pi 5 및 조원 개발환경 구축 완료.
- 공모전 공식 세부 안내 PDF가 추가 제공됨.
- 다음 단계: 팀이 `HARDWARE_RUNBOOK.md` Gate A 부품 식별표/사진을 실제로 작성하고, Gate B의 MR60 5분 기준 로그를 수집.

## 결정과 근거

- 정확한 모델·정격·핀맵을 확인하기 전에는 임의 배선도를 확정하지 않는다. 5V/3.3V 혼선과 GPIO 손상을 예방하기 위함이다.
- PDF는 텍스트 추출과 페이지 렌더링을 함께 검토한다. 표·블록도·이미지 정보 누락을 막기 위함이다.
- 대회 대응 우선순위는 `재현 가능한 MVP 완성도 > 측정 가능한 차별성 > 확장 기능 수`로 둔다. 공식 배점상 독창성 30점과 기술성·완성도 30점이 가장 크기 때문이다.
- 계획서 기준 핵심 경로는 `MR60BHA2 + Thermal-44 + SCD40 + PIR -> XIAO ESP32-C6 -> Raspberry Pi 5 -> 경보/로그`이다.
- 브레드보드 그림은 개념 결선도로 취급한다. GPIO 번호·전압·레벨시프팅·전류 용량·공통접지 명세가 없기 때문이다.
- Thermal-44는 Raspberry Pi 5에 직접 연결한다. 공식 Pi 경로가 있고, XIAO에 연결하면 SPI/I2C/CS/RESET/D_READY가 남은 GPIO를 소모해 PIR과 충돌하며 MCU 드라이버 위험이 커진다.
- 계층 책임을 명확히 한다: ESP는 MR60BHA2/SCD40/PIR의 수집·타임스탬프·유효성·전송만 담당하고, 위험도/AI/로그/LCD 연산은 모두 Raspberry Pi 5가 담당한다. Thermal-44의 Pi 직결은 이 원칙과 충돌하지 않으며 핀·드라이버 안정성을 위한 예외 경로다.
- MR60BHA2 키트는 XIAO가 사전 조립된 상태로 USB-C 5V/1A 급전하고 레이더 원모듈을 분리 급전하지 않는다. 원모듈은 3.2~3.4V, 리플 50mV 이하, 1A 이상이라는 까다로운 조건이다.
- `질식 판정` 또는 의료진단을 주장하지 않는다. MR60BHA2 제조사가 호흡·심박 기능을 수면/안정된 1인 환경에 권장하며, SCD40은 O2/H2S/CO를 측정하지 않기 때문이다. 표현은 `호흡 이상 징후 + 정지 재실 + CO2 환경 악화의 복합 조기경보`로 제한한다.

## 문서 교차분석 결과

### 공식 심사·제출 요건

- 배점: 독창성 30, 기술성 및 완성도 30, 활용성 20, 정보전달력 10, 팀 구성 및 역량 10.
- 예선 마감: 2026-09-03, 개발완료보고서 PDF 20P 이내, GitHub URL, 3분 이내 720p 이상 시연영상.
- 결선: 2026-11 오프라인 발표·현장 시연, 최소 1개 실제 작품.
- 소스코드는 수상 시 GitHub Public 유지 의무가 있으며 오픈소스 라이선스를 준수해야 함.

### 중간계획서 핵심

- 문제: 밀폐공간·차량에서 카메라 없이 정지 인체와 위험 환경을 조기 감지.
- 차별성: mmWave 호흡·재실과 열화상 형상 정합, CO2·PIR 교차검증, 룰-AI 폴백, 온디바이스 처리.
- KPI: 정지 인체 감지 95% 이상, 호흡 오차 ±2 rpm, 경보 지연 2초 이하, 시간당 오탐 5% 이하, AI 추론 100ms 이하, 24시간 가용성 99% 이상.
- MVP 필수: MR60BHA2, Thermal-44, SCD40, PIR, 규칙 기반 위험도, 부저·표시, SQLite 로그.

### 확인된 공백·위험

- 정확한 핀 번호와 전압 도메인, UART 레벨 호환, 전원 예산, 외부 경보 구동 회로가 문서에 없음.
- Thermal-44의 정확한 제조사/제품번호 및 I2C+SPI 혼합 프로토콜 세부사항이 필요.
- 위험도 가중치·임계값과 센서 시간 동기화·오류 상태 정의가 아직 정량화되지 않음.
- 계획서에는 AI 후보가 3종 이상이나 데이터 규모가 작음. 대상 전략상 우선 1개 모델을 강하게 검증하고 룰 기반 안전장치를 완성할 필요.
- CO2는 질식 위험 전체를 대표하지 못함(O2 결핍·H2S/CO 등 미검출). 시연 범위와 실제 안전제품 주장 사이의 경계를 명확히 해야 함.
- MR60BHA2는 호흡/심박 측정에 0.4~1.5m, 1인·안정 자세·데이터 누적이 필요하고, 금속·유리·물·진동·움직이는 커튼/식물·저품질 전원의 영향을 받음.
- MR60BHA2 저수준 감도·영역 파라미터는 일반 공개 API에서 자유롭게 튜닝하는 구조가 아님. 튜닝은 설치·환경 통제·펌웨어 버전 고정·시간필터·센서융합 중심으로 수행해야 함.
- SCD40은 최대 205mA 피크와 안정된 저노이즈 전원이 필요하며 I2C는 최대 100kHz, 주소 0x62임. 실물 breakout의 레귤레이터/풀업 유무 확인 전 5V 급전 금지.
- Thermal-44는 I2C 주소 기본 0x40, SPI mode 0, 16-bit, D_READY/RESET/SS 신호를 사용함.

## 확정 1차 핀/구조

- MR60BHA2 kit ↔ XIAO: 키트 내장 연결 유지. UART는 XIAO D6/GPIO16 TX, D7/GPIO17 RX, 115200 8-N-1.
- SCD40 ↔ XIAO: D4/GPIO22 SDA, D5/GPIO23 SCL, GND 공통. VDD는 실물 breakout 정격 확인 후 결정.
- HC-SR501 ↔ XIAO: D0/GPIO0 입력 후보, GND 공통. OUT 전압을 멀티미터로 확인한 뒤 연결.
- Thermal-44 ↔ Pi 5: Pi I2C + SPI0 + GPIO23 RESET + GPIO24 D_READY + CE0 SS 직결 구조.

## 파일/산출물

- 중간계획서 PDF: 사용자 지정 Desktop 경로(읽기 전용)
- 자유공모 세부 안내 PDF: 사용자 지정 Downloads 경로(읽기 전용)
- 진행 기록: `PROJECT_PROGRESS.md`
- 하드웨어 실행서: `HARDWARE_RUNBOOK.md`
- mmWave 튜닝 계획: `MMWAVE_TUNING.md`
- 팀 운영 모델: `TEAM_OPERATING_MODEL.md`

## 최종 검증 요약

- 문서: 10P 중간계획서와 6P 공모 안내서의 전 페이지를 렌더링·텍스트 교차 확인.
- 하드웨어: 공식 제조사 자료로 XIAO ESP32-C6, MR60BHA2, SCD40, Waveshare Thermal-44의 인터페이스/전원/한계를 확인.
- 구조: ESP는 MR60/SCD40/PIR 수집·전송, Pi는 융합·AI·로그·LCD, Thermal-44는 안정성을 위해 Pi 직결로 명시.
- 실행성: 배선 Gate A~E마다 합격 기준, mmWave 시험마다 안전·로그·KPI 기준 존재.
- 팀: 조장 포함 5명 각각 단일 최종 책임, 00~06 채팅과 코드 경계·완료 정의 존재.
- 형식: 네 Markdown 파일에 대해 필수 키워드/섹션 검색 및 `git diff --check` 통과.

## 알려진 위험·미확인 사항

- 문서상 모델은 XIAO ESP32-C6, MR60BHA2, SCD40, HC-SR501, Waveshare Thermal-44로 식별했으나 실물 SCD40 breakout의 레귤레이터/레벨시프터와 PIR 출력전압은 아직 측정하지 않음.
- 실제 배선·센서 로그·30분/8시간/24시간 시험은 팀이 물리 장비로 수행해야 하며 아직 PASS 증거가 없음.
- 공식 안내서는 일정 변경 가능성을 명시함. 2026-09-03 예선 마감은 첨부된 2026 안내서 기준이며 제출 전 홈페이지 재확인 필요.
- 팀명은 `가만있어도SANDI`로 등록하면 한글 5자+영문 5자이며 영문 대문자 조건에 맞는다. 계획서의 장식용 앞뒤 하이픈은 등록 팀명에 포함하지 않는다.

## 2026-07-13 MR60 수집 의미·정확도 수정 착수

- [x] 승인 범위 확인: 실제 비재실은 `NO`, 호흡·심박 유효값 표시 개선, 보고서 기반 Pi 위험 상태 검증.
- [x] 기존 코드 점검: Seeed 라이브러리의 `isHumanDetected()`는 새 재실 프레임이 없는 경우와 실제 `false`를 구분하지 못해 단발성 NO를 만들 수 있다.
- [x] 기존 화면 점검: 심박·호흡 패널이 마지막 양수값을 계속 유지하여 빈 공간에서도 현재 측정처럼 보일 수 있다.
- [x] 변경 전 원시 로그 보존 및 조건 기록.
- [x] 재실 수집 의미 수정 후 동일 로그/시험 조건 비교.
- [ ] 호흡·심박 WARMUP/VALID/UNKNOWN 표시 및 빈 공간 거짓 생체값 계측. 빈 공간 표시는 완료했고 1인 정확도 실측은 남음.
- [x] Pi 위험도 규칙 구현·시나리오 검증. 계획서에 가중치와 R 임계값은 아직 없으므로 임의 수치를 확정하지 않는다.

### 단계 결과: 빈 공간 표시 및 수집기 수정

- 변경 전 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-13_empty_desk_prechange_30s.jsonl`
  - SHA-256 `028ec1d09d80dfc34633f45c1e965dc1066107144a6b5b0a30cde42f54f061e3`
  - 책상 배치·사람이 레이더 시야에 없는 조건, 30초, 274줄.
  - 파싱 프레임 272개, 재실 true 0개, 심박 양수 0개, 호흡 양수 0개. 빈 공간에서 보였던 생체 숫자는 대시보드의 과거값 유지가 원인이었다.
- 수집기 v1은 Tiny Frame 종류·헤더/데이터 체크섬을 직접 계수하도록 변경했으나, 모든 내부 프레임마다 긴 JSON을 출력해 USB UART 출력 적체와 동일 타임스탬프를 만들었다. 이 방법은 채택하지 않았다.
- 대안 v2는 내부 프레임은 모두 파싱·계수하고 Pi 텔레메트리는 100ms 간격 스냅샷으로 분리했다.
- 변경 후 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-13_empty_desk_collector_v2_30s.jsonl`
  - SHA-256 `8a7eaaf592b9ce683e2a1947bb8b36421a88dd8835c3fbcf8ab7b9e87ceb10ac`
  - 29.8초, 텔레메트리 299개(약 10.0Hz), 내부 유효 UART 프레임 1,785개(약 59.9Hz).
  - 체크섬 오류 0/1,785(0%), 파싱 오류 0/1,785(0%), 재실 true 0/299, 빈 공간 양수 심박·호흡 0/299.
- 대시보드는 재실 `false`일 때 심박·호흡·거리를 즉시 `UNKNOWN`으로 지우며 `재실 NO · 생체값 판정 금지`를 표시한다. 과거 양수값을 현재 측정처럼 표시하지 않는다.
- ESP 빌드/업로드: ESP32 Arduino Core 3.2.0, Espressif32 Platform 54.3.20, ESP32-D0WD-V3 rev 3.1, 4MB flash. MR60 센서 펌웨어는 변경하지 않았고 자발 보고에서 버전 프레임은 아직 수신되지 않았다.

### 단계 결과: Pi 위험 판정 골격

- 계획서의 호흡 정상 후보 `12~20 rpm`만 `config/risk_rules.json`에 출처와 함께 분리했다. 보고서에 없는 위험도 R 가중치·R 구간과 CO2 ppm 임계값은 확정하지 않았다.
- `pi/risk_engine.py`는 `NORMAL/CAUTION/DANGER/UNKNOWN`을 반환한다. 0/NaN/결측/UART 오류/WARMUP은 `UNKNOWN`, 심박은 위험도 입력에서 제외한다.
- mmWave 호흡 이상만으로 `DANGER`를 확정하지 않고 Thermal 인체 일치가 있을 때만 계획서의 위험 시나리오를 확정한다. 빈 공간+CO2 상승은 `CAUTION`, 빈 공간이지만 환경 입력이 없으면 `UNKNOWN`이다.
- `python3 -m unittest discover -s pi -p 'test_*.py' -v`: 정상 재실, 융합 확인 호흡 이상, 융합 미확인, 0 호흡, UART 장애, 빈 공간 정상/CO2 상승, 심박 제외 등 8개 시나리오 전부 통과.

### 아직 완료되지 않은 실측

- 호흡·심박 정확도는 사람이 없는 로그로 평가할 수 없다. 레이더를 흔들림 없이 흉부 방향 0.8~1.0m에 고정하고 60초 확립 후 5분 원시 로그가 필요하다.
- 현재 조건에서는 재실 `NO`는 검증했지만 안정된 1인 재실 감지율, 호흡 MAE/표준편차/유효률, 진입·퇴장 지연, 30분 재부팅 0회는 아직 미검증이다.

## 2026-07-13 정지 인체 D06 5분 기준선

- 사용자 설치 후 10초 사전 확인에서 재실 `YES 100/100`, `NO 0/100`, 체크섬·파싱 오류 0회를 확인하고 본 수집을 시작했다.
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-13_occupied_front_p0_5min.jsonl`
  - SHA-256 `20da15d183b7565feafcff3ada2b6aefb3e1e3daad6b45294fc4b74b6d26ee2e`
  - 299.932초, 텔레메트리 2,999개, 내부 UART 프레임 22,861개.
  - 재실 true 2,999/2,999(100%), false/unknown 0회.
  - 체크섬 오류 0/22,861, 파싱 오류 0/22,861, 감지된 ESP 재부팅 0회.
- 전체 5분 무필터 통계:
  - 거리 평균 57.55cm, 중앙값 57.40cm, 표준편차 3.64cm, 범위 45.92~68.88cm.
  - 호흡 평균 18.53rpm, 중앙값 20rpm, 표준편차 5.64rpm, 범위 1~29rpm, 양수값 비율 100%.
  - 심박 평균 80.55bpm, 중앙값 79bpm, 표준편차 10.84bpm, 범위 62~111bpm, 양수값 비율 100%.
- 첫 60초 제외 후에도 호흡 표준편차 6.01rpm, 심박 표준편차 11.19bpm으로 변동이 크다. 기준 호흡 템포·손목 심박 정답이 없으므로 정확도(MAE)는 아직 계산할 수 없고 필터/유효 임계값도 확정하지 않는다.
- 사용자 줄자 실측 가슴 거리 63cm, 센서 거리 중앙값 57.40cm로 차이는 약 -5.6cm이다. 이번 로그는 0.9m가 아니라 D06(약 0.6m) 시험으로 분류한다. 파일명에는 최초 수집명 `P0`가 남지만 원본 보존을 위해 이름을 변경하지 않는다.
- 분석 결과:
  - `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-13_occupied_front_p0_5min_summary.json`
  - `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-13_occupied_front_p0_after_warmup_summary.json`

## 2026-07-13 빈 공간 D06 E0 5분 기준선

- 본 수집 전 즉시 확인에서는 재실이 10초간 계속 YES였으나, 추가 40초 관찰에서 약 20초 전후에 NO로 해제됐고 마지막 10초는 NO 100/100, 거리·호흡·심박 양수 0회였다. 센서 자체 퇴장 해제 지연 후보로 기록한다.
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-13_empty_fixed_d06_e0_5min.jsonl`
  - SHA-256 `f0687bc80aa014a5dfbbdf96692a2e942868b1618dcb8e2d9a40138ed7cf3771`
  - 299.854초, 텔레메트리 2,999개, 내부 UART 프레임 18,082개.
  - 체크섬 오류 0/18,082, 파싱 오류 0/18,082, 감지된 ESP 재부팅 0회.
- 재실 false 2,940/2,999, true 59/2,999(1.97%), unknown 0회.
- true 구간은 두 묶음이었다: 약 3.2초(거리 68.88~86.10cm, 호흡 1rpm 양수 16샘플)와 약 2.5초(거리 80.36~91.84cm, 심박 92~97bpm 양수 25샘플).
- 이 구간이 실제 사람 통과인지 환경 오탐인지 사용자 확인이 필요하다. 완전한 빈 공간이었다면 원시 재실 오탐 2건이며 단순 2-of-3 필터만으로 제거되지 않는다.
- 분석 결과: `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-13_empty_fixed_d06_e0_5min_summary.json`.

### D06 재실 후보 필터 오프라인 비교

- 사용자가 수집 중 사람 통과가 전혀 없었다고 확인하여 위 두 구간을 빈 공간 재실 오탐 2건으로 확정했다.
- 동일한 빈 공간/정지 인체 원본을 `compare_presence_filters.py`로 재생했다. 결과는 `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-13_d06_presence_filter_comparison.json`에 저장했다.
- 2-of-3은 오탐 2건을 모두 통과시켜 효과가 없었다.
- true 지속 2초는 오탐 2건을 모두 통과시키고 추가 지연도 약 2.0초여서 목표를 통과하지 못한다.
- 3.5초 지속은 오탐을 제거하지만 추가 지연 3.5초로 2초 목표를 위반한다.
- 재실+양수 호흡+양수 심박 결합은 이 두 로그에서는 오탐 0, 정지 인체 감지 100%였으나, 정지 인체 로그가 이미 생체값 확립 후 시작되어 진입 지연을 평가할 수 없다. 아직 채택하지 않는다.
- 결론: 시간필터만으로 현재 오탐 제거와 2초 지연 목표를 동시에 만족할 수 없다. 진입→정지→퇴장 원본으로 생체값 확립 지연을 측정하고, 최종 재실은 Pi의 Thermal/PIR 교차검증을 사용해야 한다.

## 2026-07-13 D06 M0 진입·퇴장 예비시험 1

- 원본 `firmware/esp_wroom32_mr60_monitor/logs/transitions/2026-07-13_d06_m0_trial01.jsonl`, SHA-256 `ca2063f569348647e3d25380afb5332cbbdd5e070c8bca88b9e21dcbfcae9528`.
- 호스트 안내 시각 매핑 `firmware/esp_wroom32_mr60_monitor/logs/transitions/2026-07-13_d06_m0_trial01_timing.jsonl`, SHA-256 `6f068e233d2cba56d35af8c9bca41d18446a2034c1fe1a55c3b50b8c9e9d9f38`.
- 결과: 시험 시작부터 종료까지 raw presence가 1,299/1,299 true였다. 진입 전 약 97.58cm 대상 오탐이 이미 유지되어 재실 진입 지연을 계산할 수 없다.
- ENTER 안내 기준 근거리 거리 변화 약 8.5초, 첫 양수 심박 약 8.7초, 첫 양수 호흡 약 10.7초였으나 사용자의 실제 착석 완료 시각이 없어 이동 시간이 포함된다.
- EXIT 안내가 전체 캡처 종료 약 11초 전에 발생하여 센서의 재실 해제까지 기록하지 못했다.
- 판정: 이 방법은 재실 진입·퇴장 지연 검증에 실패. 로그는 실패 증거로 보존하되 KPI 계산에는 사용하지 않는다.
- 다음 방법: 시작 전 raw presence false 10초를 확인하고, 고정 길이 안내 대신 사용자의 `착석 완료`와 `퇴장 완료` 응답 시각을 마커로 기록하며 퇴장 후 raw false가 10초 유지될 때까지 수집한다.

## 2026-07-13 D06 M0 진입·퇴장 예비시험 2 및 중단

- 사용자 완료 응답 시각을 기록하는 방식으로 재시험했으나, `EXIT_CONFIRMED` 후 113.154초 동안 raw presence가 1,132/1,132 true로 유지됐다.
- 퇴장 후 센서 거리는 주로 86.10/91.84/97.58cm로 보고되어 약 1m 전방 환경을 계속 사람으로 오인하는 설치 간섭이 확인됐다. 생체 필드도 0과 양수 후보가 섞여 단독 근거로 사용할 수 없다.
- 원본 `firmware/esp_wroom32_mr60_monitor/logs/transitions/2026-07-13_d06_m0_trial02.jsonl`, SHA-256 `d476b190f1681b2a262ee8495c6293a6323a7c16f1c8793686f63bec6fcd7ea0`.
- 타이밍 `firmware/esp_wroom32_mr60_monitor/logs/transitions/2026-07-13_d06_m0_trial02_timing.jsonl`, SHA-256 `35516cda1485a55ff421dca1c67730e006decadc308541c600a4f2c0b1d1380a`.
- 동일한 환경 오탐으로 두 번의 진입·퇴장 방법이 실패했으므로 현재 설치에서 추가 필터 확정을 중단한다. 다음 작업은 개방 공간, 고정 거치대, 전방 1.5m 반사체 제거, 실제 거리 표식, 한 명만 있는 조건을 먼저 구축한 뒤 기준선을 처음부터 재수집하는 것이다.
- 사용자 요청으로 이번 세션은 여기서 종료했다. 시리얼 포트 점유 프로세스가 없음을 확인했다.

## 2026-07-25 MR60BHA2 환경 재구축 시작

- 목표: ESP-WROOM-32와 MR60BHA2의 전원·UART·설치 환경을 처음부터 다시 검증하고, 빈 공간 raw presence=NO 및 0.9m 정지 1인 raw presence=YES를 확인한 뒤에만 새 기준선 로그를 수집한다.
- 체크리스트:
  - [x] 1. 저장소, 기존 ESP 코드, 과거 실패 원인, 현재 USB 장치 상태 확인.
    - ESP 펌웨어는 UART2 115200bps, RX=GPIO16, TX=GPIO17의 무필터 raw 모니터이며 체크섬/파싱 누계를 출력한다.
    - 과거 실패 원인은 약 86~98cm 전방 환경물을 사람으로 오인한 설치 간섭이다. 동일 방식 반복 대신 개방 공간에서 재구축한다.
    - `find /dev`로 확인한 현재 USB 시리얼 장치는 0개다. 아직 ESP 연결 상태를 확인할 수 없다.
  - [ ] 2. 전원을 분리하고 MR60BHA2 5V/GND/TX/RX 4선 배선 및 USB 전원을 검증한다.
  - [ ] 3. 개방 공간, 고정 거치, 전방 반사체 제거 및 0.9m 거리 표식을 검증한다.
  - [ ] 4. USB 포트와 UART 프레임/체크섬/파서를 짧은 실시간 캡처로 검증한다.
  - [ ] 5. 빈 공간에서 raw presence=NO가 연속 유지되는지 확인한다.
  - [ ] 6. 0.9m 가슴 정면 정지 1인에서 raw presence=YES 및 생체 raw 프레임을 확인한다.
  - [ ] 7. 위 게이트 통과 후에만 무필터 기준선 로그를 새로 수집한다.
  - [ ] 8. 포트·배선·버전·실행 명령과 검증 결과를 재현 가능하게 기록한다.
- 금지/보류: 기준선 전에 필터·유효성 임계값을 변경하지 않으며 MR60 펌웨어를 업데이트하지 않는다. PIR 등 다른 센서는 MR60 단독 검증이 끝날 때까지 연결하지 않는다.
- 다음 단계: 사용자가 USB를 분리한 상태에서 4선 배선을 확인하고, 배선 사진 또는 핀별 연결 확인을 제공한다.

## 2026-07-25 재연결 후 1차 UART 진단

- 중간계획서 PDF의 mmWave 구현 요구를 확인했다: MR60BHA2 재실·호흡을 ESP에서 수집·전처리해 Pi로 전달하고, Pi가 열화상/PIR/CO2와 융합하여 위험도를 계산한다. 통제 조건은 거리 0.5~1.5m이며 목표는 정지 인체 감지 95% 이상, 호흡 오차 ±2rpm이다.
- Mac에서 ESP가 `/dev/cu.usbserial-110`으로 인식됐다.
- `pyserial==3.5`를 `/private/tmp/safenest-mmwave-venv` 격리 환경에 설치해 기존 `capture_serial.py`로 15초 진단 캡처를 수행했다.
- 진단 원본(임시): `/private/tmp/mr60_uart_check.jsonl`.
- 결과: ESP JSON 150개, seq 9254~9403, ESP 시간 926415~941315ms로 USB 출력은 정상이다.
- 그러나 `uart_frames_total`은 처음과 마지막 모두 0이며 presence/distance/breath/heart/phase가 모두 null이다. 체크섬/파싱 오류 0은 프레임 자체가 없기 때문이며 MR60 통신 정상 근거가 아니다.
- 판정: 컴퓨터↔ESP는 정상, MR60→ESP UART는 미수신. 필터·임계값·펌웨어를 변경하지 않고 MR60 전원 LED, GND 공통, TX→GPIO16/RX2, RX→GPIO17/TX2 배선을 다시 확인한다.

### 2026-07-25 UART 재측정 및 방법 전환

- 포트 `/dev/cu.usbserial-110` 존재와 미점유 상태를 확인한 후 동일한 115200bps 조건으로 15초 재측정했다.
- 임시 원본: `/private/tmp/mr60_uart_recheck.jsonl`.
- 결과: ESP JSON 150개, seq 11597~11746, 측정 14.9초. `uart_frames_total` 증가 0, presence 150/150 null, distance/breath/heart 모두 null, checksum/parse 오류 증가 0.
- MR60 UART 프레임 0개가 동일 방식으로 두 번 반복됐으므로 시리얼 캡처 반복을 중단한다.
- 원인 후보: MR60 5V 미공급/극성 문제, 공통 GND 누락, MR60 TX/RX 교차 오류, 센서가 ESP RX0/TX0에 연결되어 현재 펌웨어의 UART2(GPIO16/17)와 불일치, 접촉 불량.
- 다음 방법: 양쪽 핀 라벨이 보이는 배선 사진과 MR60 전원 상태를 물리적으로 확인한 뒤, 확인된 핀에 맞춰 UART를 다시 측정한다.

### 2026-07-25 재배선 후 UART 통신 성공

- 사용자가 ESP-WROOM-32 기준 `MR60 TX→GPIO16/RX2`, `MR60 RX→GPIO17/TX2`, `5V→VIN/5V`, `GND→GND`로 재연결했다.
- 포트 `/dev/cu.usbserial-110`에서 115200bps, 15초 진단 캡처를 수행했다.
- 임시 원본: `/private/tmp/mr60_uart_after_rewire.jsonl`.
- ESP JSON 150개, MR60 UART 프레임 1,128개 수신(`uart_frames_total` 3,604→4,732).
- 캡처 중 checksum 오류 증가 0, parse 오류 증가 0. 누적 오류 7개는 캡처 시작 전에 이미 존재하여 이번 구간 오류율에는 포함하지 않는다.
- raw presence는 150/150 true, 거리는 143.5cm, 호흡은 0~1rpm, 심박은 97~111bpm이었다.
- 판정: 컴퓨터↔ESP↔MR60 UART 경로는 정상이다. 호흡 0~1rpm은 유효 생체값으로 확정할 수 없으며, presence true/143.5cm가 실제 사람인지 환경 반사인지 사용자 현장 상태 확인이 필요하다.
- 다음 단계: 현재 센서 전방에 사람이 있는지 확인하고, 빈 공간이라면 설치 반사체를 제거해 raw presence false 연속 유지 게이트를 통과한다.
- 사용자 확인: 센서는 통제된 빈 공간이나 정지 인체 조건으로 설치한 것이 아니라 단순히 놓아둔 상태였다. 따라서 위 presence=true, 143.5cm, 호흡 0~1rpm, 심박 97~111bpm은 성능·정확도·오탐 판정에 사용하지 않고 통신 확인 데이터로만 취급한다.

## 2026-07-25 빈 공간 설치 게이트 1차

- 사용자가 빈 공간 준비 완료를 확인한 뒤 120초 무필터 진단 캡처를 수행했다.
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-25_empty_gate_120s.jsonl`
  - SHA-256 `589d538292aa264365a48b15c4ba2dd3dcd1cd765540d237696adc33ceb9e6cf`
  - 119.831초, 텔레메트리 1,199개, 10.006Hz.
  - UART 프레임 7,454개, 62.204Hz, checksum/parse 오류 0, 재부팅 0.
- raw presence true 183개(15.26%), false 1,016개, unknown 0개로 빈 공간 게이트를 통과하지 못했다.
- true 구간은 2회였다: 시작 0~5.602초와 55.915~68.619초. 첫 구간은 퇴장 직후 센서 해제 지연일 수 있으나, 두 번째 약 12.7초 구간은 충분히 지난 뒤 발생한 환경 오탐이다.
- true일 때 거리 40.18~80.36cm, 중앙값 63.14cm였고 빈 공간에서 호흡 1rpm 19개, 심박 81~107bpm 116개가 출력됐다. 이 값들은 생체값이나 위험 근거로 사용하지 않는다.
- 분석: `firmware/esp_wroom32_mr60_monitor/analysis/diagnostics/2026-07-25_empty_gate_120s_summary.json`
  - SHA-256 `923f281bda08d28ad6bad99a5d3d9d556e3824826140d5f0e3f912a5f4e51464`
- 판정: 필터·임계값을 변경하지 않는다. 센서를 눕혀 두지 않고 비금속 고정대에 세워 전면을 열린 공간으로 향하게 하며, 전방 약 0.4~0.8m의 책상면·의자·노트북·케이블·금속물을 제거한 뒤 짧은 빈 공간 게이트를 재시험한다.

## 2026-07-25 빈 공간 설치 게이트 2차

- 재배치 안내 후 60초 무필터 재시험을 수행했다.
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-25_empty_gate_attempt02_60s.jsonl`
  - SHA-256 `9fecb5072da737225e83affce8b2bbe1a86424d6f6762e9480afaa2188e742f4`
  - 59.932초, 텔레메트리 600개, UART 프레임 4,182개.
  - checksum/parse 오류 0, 감지된 ESP 재부팅 0.
- raw presence는 600/600 true(100%)였고 거리는 전 구간 68.88cm로 고정됐다.
- 빈 공간인데 양수 호흡은 440/600(73.3%), 1~24rpm이었고 심박은 600/600(100%), 82~118bpm이었다. 모두 환경 오탐이므로 생체·위험 판단에서 제외한다.
- 분석: `firmware/esp_wroom32_mr60_monitor/analysis/diagnostics/2026-07-25_empty_gate_attempt02_60s_summary.json`
  - SHA-256 `93d7eb5ad9fbb454cbf9135b9c786d59bfd6e9870355964a720fbdb0a6b0ea54`
- 빈 공간 설치 게이트가 두 번 실패했다. 동일한 텍스트 기반 재배치를 반복하지 않는다. 약 69cm 고정 반사 대상을 특정하기 위해 센서 안테나 면, 거치 방향, 정면 1.5m 환경이 한 장에 보이는 사진을 확인한 뒤 설치 방법을 변경한다.

## 2026-07-25 실시간 터미널 대시보드 재실행

- 임시 가상환경 `/private/tmp/safenest-mmwave-venv`에 `rich==15.0.0`과 의존성을 설치했다. `pyserial==3.5`는 앞서 설치돼 있다.
- macOS Terminal 새 창에서 `mmwave_dashboard.py --port /dev/cu.usbserial-110 --baud 115200`을 실행했다.
- `lsof`로 Python PID 79636이 `/dev/cu.usbserial-110`을 점유해 실제 데이터를 읽고 있음을 확인했다.
- 대시보드 실행 중에는 같은 포트를 사용하는 캡처/업로드를 동시에 실행하지 않는다. 다음 캡처 전에 터미널에서 Ctrl+C로 종료해야 한다.

### 2026-07-25 터미널 입력 지연 대응

- 사용자가 전체화면 대시보드 실행 시 Mac 터치패드가 작동하지 않는 것처럼 느껴지는 문제를 보고했다.
- 원인은 Rich `Live(..., screen=True)`의 대체 화면 버퍼와 5Hz 전체 화면 갱신 가능성으로 판단했다.
- 센서 수집 로직은 변경하지 않고 `screen=False`, 화면 갱신 2Hz로 변경했다. Python 문법 검사를 통과했다.
- 재연결된 `/dev/cu.usbserial-110`에서 새 터미널 대시보드를 실행했고 PID 11734가 실제 포트를 점유함을 확인했다.
- 이후 사용자가 터치패드 문제를 별도로 해결했다고 확인하여 요청대로 대시보드 표시 설정을 원래의 `screen=True`, 5Hz로 복원했다. 문법 검사 후 PID 4882로 재실행했으며 `/dev/cu.usbserial-110` 점유를 확인했다.
- 사용자의 요청으로 원시 상태 식별 색상을 분리했다: 심박=초록, 호흡=청록, 거리=파랑, 재실=자홍, UNKNOWN=노랑, 통신 FAULT=빨강. 정상/주의/위험 임계값은 추가하지 않았으며 센서 수집 로직도 변경하지 않았다. 문법 검사 후 전체화면 5Hz로 PID 7722를 실행했고 포트 점유를 확인했다.
- 첫 색상 분리 실행은 macOS Terminal에서 모두 흑백으로 보여 실패했다. Rich 자동 색상 감지에 의존하지 않도록 `Console(force_terminal=True, force_interactive=True, color_system="truecolor", no_color=False)`를 사용하고 항목별 고대비 RGB 색상을 지정했다. ANSI truecolor escape 출력과 Python 문법을 검증한 후 PID 11372로 재실행했으며 포트 점유를 확인했다.

## 2026-07-25 약 60cm 정지 인체 60초 진단

- 사용자가 센서 약 60cm 정면에 위치했다고 확인한 뒤 대시보드를 종료하고 60초 무필터 캡처를 수행했다.
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-25_occupied_front_d06_60s.jsonl`
  - SHA-256 `df232a4fdfefef6d053383fe3ccb525d85d5321980fefa627445012f39b6e32f`
  - 59.822초, 텔레메트리 599개, UART 프레임 4,508개.
  - checksum/parse 오류 0, 재부팅 0.
- raw presence 599/599 true(100%). 센서 거리 중앙값은 34.44cm, 범위 28.70~40.18cm로 사용자의 대략 60cm와 크게 달랐다.
- 전체 구간 양수 호흡은 234/599(39.1%), 평균 5.94rpm, 중앙값 4rpm, 표준편차 5.31rpm이었다.
- 전체 구간 양수 심박은 502/599(83.8%), 평균 77.10bpm, 중앙값 76bpm, 표준편차 4.67bpm이었다.
- 마지막 30초만 보면 호흡 양수값은 0/299(0%), 심박 양수 후보는 212/299(70.9%), 중앙값 77bpm이었다. 호흡은 확립되지 않았다.
- 판정: 재실 통신 시험은 성공했지만 생체 기준선은 실패했다. 센서 보고 거리가 0.5m보다 가까워 공식 핵심 생체 구간에 못 미친 가능성이 있으므로, 실제 안테나 면부터 가슴까지 줄자로 0.9m를 맞춘 뒤 60초 워밍업 후 다시 측정한다.

## 2026-07-25 GitHub 제출·협업 저장소 준비

- GitHub 플러그인을 설치하고 인증 계정이 `jinsu1011`임을 확인했다.
- 현재 로컬 저장소는 `main`, 커밋 0개, 원격 저장소 없음 상태다.
- 민감정보 검색 결과 비밀번호·API 키·토큰·개인 이메일은 발견되지 않았다. 진행 기록에는 사용자 Mac 절대경로가 일부 남아 있어 공개 저장소 전환 전 재검토가 필요하다.
- 루트 `.gitignore`를 추가해 `.pio`, `.venv`, `__pycache__`, `tmp/` 렌더링 산출물, 로컬 환경파일을 제외했다. 원시 JSONL 로그 19개(약 13MB)는 재현 증거로 포함 가능하며 개별 파일은 GitHub 일반 제한 이하이다.
- 제출·협업용 `README.md`와 `CONTRIBUTING.md`를 추가했다.
- Pi 위험도 엔진 단위 테스트 8개가 모두 통과했고 Python 문법 검사도 통과했다.
- ESP `platformio run`은 소스 오류가 아니라 Espressif 플랫폼 다운로드 단계에서 샌드박스 HTTP 오류로 실패했다. 네트워크 승인 재시도는 Codex 사용량 제한으로 거부돼 우회하지 않았으며 현재 빌드 상태는 미검증으로 남긴다.
- GitHub 계정과 연결은 완료됐으나 GitHub 플러그인에는 새 저장소 생성 기능이 없고 로컬 `gh` CLI도 설치돼 있지 않다. 저장소 공개 여부와 이름을 확정한 뒤 GitHub 웹에서 원격을 생성하고 로컬 첫 커밋·푸시를 수행한다.

## 2026-07-25 거리 출력 양자화 확인 (기존 로그 재분석, 신규 수집 없음)

- 2026-07-25 진단 로그 3개(`empty_gate_120s`, `empty_gate_attempt02_60s`, `occupied_front_d06_60s`)의 양수 `distance_cm_raw` 값을 모두 모아 고유값을 셌다.
- 고유값은 9개뿐이었다: 28.70, 34.44, 40.18, 45.92, 51.66, 57.40, 63.14, 68.88, 80.36 cm.
- 인접 고유값 간격은 예외 없이 5.74cm이며(80.36만 11.48 = 5.74×2로 한 칸 건너뜀), 9개 값 전부가 5.74cm의 정확한 정수배다(bin 5,6,7,8,9,10,11,12,14).
- 결론: MR60BHA2의 거리 출력은 연속값이 아니라 **약 5.74cm 단위 range bin**이다. 이론적 거리분해능 5.74cm는 대역폭 약 2.6GHz에 해당한다.
- 재현 방법: 각 로그의 양수 `distance_cm_raw`를 5.74로 나누면 모두 정수가 된다.

### 이번 시험 계획에 미치는 영향

- 줄자 90cm를 맞춰도 센서는 90.00cm를 표시할 수 없다. 90 / 5.74 = 15.68이므로 **86.10cm(bin 15) 또는 91.84cm(bin 16)** 중 하나로만 보고된다. 두 값 중 하나가 나오면 거리 측정은 정상이며 오차로 계산하면 안 된다.
- 따라서 거리 정확도 지표는 `|센서값 - 줄자값|`이 아니라 `|센서값 - 줄자값| ≤ 5.74/2 = 2.87cm`(± 반 bin) 기준으로 판정한다.
- 과거 실패 로그의 오탐 거리 86.10 / 91.84 / 97.58cm는 각각 bin 15 / 16 / 17이었다. 별개의 대상 3개가 아니라 인접 bin 사이를 오간 하나의 반사원일 가능성이 있다.
- 2026-07-13 D06 기준선의 중앙값 57.40cm(bin 10)와 줄자 63cm의 차이 -5.6cm는 정확히 bin 1칸이다. 측정 오류가 아니라 bin 경계 문제로 재분류한다.

### 거리 bin 시간변동(참고, 분류기로 채택하지 않음)

| 로그 | 관측 bin | bin 변화 횟수 | 변화율 |
|---|---|---:|---:|
| empty_gate_120s (true 구간만) | 7~12, 14 | 15 / 182 | 8.24% |
| empty_gate_attempt02_60s | 12 고정 | 0 / 599 | 0.00% |
| occupied_front_d06_60s | 5, 6, 7 | 16 / 598 | 2.68% |

- 2차 빈 공간 로그의 표준편차 0.0(600샘플 전부 bin 12)은 완전 정지 강체 반사면의 특징이며, 사람이 아니라는 강한 정황이다.
- 그러나 1차 빈 공간 로그의 변화율(8.24%)이 정지 인체(2.68%)보다 오히려 높으므로, bin 변화율만으로 사람/환경물을 분류할 수 없다. 진단 보조 지표로만 남기고 필터나 임계값으로 채택하지 않는다.

### 미사용 원시 필드 확인

- ESP 텔레메트리에는 `total_phase`, `breath_phase`, `heart_phase`와 각 필드의 `*_age_ms`가 이미 포함되어 있으나 지금까지 어떤 분석에도 사용하지 않았다.
- 향후 사람/환경물 분리에 rate 값보다 위상 신호가 더 유용할 수 있으므로 기준선 수집 후 별도로 검토한다. 이번 단계에서는 변경하지 않는다.

## 2026-07-25 최초 페어 캡처 성공 (빈 공간 게이트 통과 + 0.9m 정지 인체)

- 통신 healthcheck 15초로 mmWave 데이터 흐름을 먼저 재확인했다. 텔레메트리 10.06Hz, UART 76Hz, 체크섬/파서/재부팅 0. 사용자가 센서 정면 약 40~46cm에 있어서 재실 100%였고 이는 사람 감지 자체가 동작함을 확인한 것이다.
- 사용자가 감지 원뿔 밖으로 3~4m 벗어난 상태에서 15초 진단을 수행했다. 처음 13.5초는 YES 유지, 마지막 1.5초에서 YES→NO로 해제됐고 거리 tracking은 74→160cm까지 뒤로 밀렸다. 지난 실패의 원인이 환경물이 아니라 사용자 자신이었을 가능성을 시사한다.

### 빈 공간 게이트 3차 (attempt03, 60초)
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-25_empty_gate_attempt03_60s.jsonl`
- 분석: `firmware/esp_wroom32_mr60_monitor/analysis/diagnostics/2026-07-25_empty_gate_attempt03_60s_summary.json`
- 59.92초, 텔레메트리 599개, UART 3,700+ 프레임, 체크섬/파서/재부팅 0.
- **재실 YES 0/599 (0.0%) 60초 전 구간**. 거리 후보값 0개.
- 5초 묶음 12개 전부 YES 0%. 프로젝트 시작 이후 첫 빈 공간 게이트 통과.

### 0.9m 정지 인체 60초 (페어)
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-25_occupied_d09_60s.jsonl`
- 분석: `firmware/esp_wroom32_mr60_monitor/analysis/diagnostics/2026-07-25_occupied_d09_60s_summary.json`
- 마지막 30초 분석: `firmware/esp_wroom32_mr60_monitor/analysis/diagnostics/2026-07-25_occupied_d09_60s_after30s_summary.json`
- 59.92초, 텔레메트리 600개, UART 4,560 프레임, 체크섬/파서/재부팅 0.
- 재실 YES 600/600 (100.0%), 5초 묶음 12개 전부 100%.
- 거리 중앙값 86.10cm 전 구간, bin 15가 586/600, bin 16이 14/600. 마지막 30초는 bin 15 300/300으로 완전 고정.
- 줄자 안내값 90cm는 bin 15 범위 83.23~88.97cm 또는 bin 16 범위 88.97~94.71cm에 걸치는 값이다. bin 15로 안착한 것은 실제 흉부까지 거리가 약 86cm였다는 뜻으로 해석하며, 5.74cm 양자화 기준 안에서 정상이다.
- 호흡 양수값 600/600 (100%). 전체 중앙값 23rpm(std 5.92), 마지막 30초 중앙값 23rpm (std 4.12, 범위 7~28).
- 심박 양수값 600/600 (100%). 전체 중앙값 75bpm(std 7.12), 마지막 30초 중앙값 69bpm (std 6.11, 범위 62~81).

### 판정
- **정지 인체 감지율 = 100%로 PDF KPI 목표 95% 초과 달성** (단, 60초·1인·1자세이므로 최종 KPI 근거는 아니고 매트릭스 확장 필요).
- 통신·파서·펌웨어 계층은 안정성 근거 확보.
- 호흡 std 4.12rpm은 PDF 목표 ±2rpm보다 크지만 이는 **무필터 원본**이며, 필터 비교 이후 판정할 값이다. 지금 임계값을 확정하지 않는다.
- 첫 60초 워밍업 이후 값 안정성이 확립되므로 PDF의 "재실 확립 후 60초 워밍업" 조건과 일치한다.

### 다음 단계 우선순위
1. **5분 무필터 페어 기준선** — 같은 설치로 빈 공간 5분 + 0.9m 인체 5분. 30분 안정성 이전 단계.
2. **거리 매트릭스** — 0.6 / 0.9 / 1.2 / 1.5m 각 60초 이상. 감지 원뿔 안 4개 지점 감도.
3. **진입→정지→퇴장 20회** — 감지·해제 지연 측정 (PDF KPI ≤2초).
4. **호흡 정확도 시험** — 메트로놈 12/15/20rpm 편안한 페이싱, ±2rpm 검증.
5. **ESP 상태 머신 구현** — WARMUP/VALID/UNKNOWN/FAULT.
6. **Pi 통합 시작** — 열화상/PIR/CO2 융합, 규칙 기반 위험도.

### 반드시 지킬 것
- **센서를 절대 재배치하지 않는다.** 방금 게이트 통과한 설치 상태를 사진으로 기록하고 이후 시험에서 동일하게 유지한다.
- 만지거나 이동한 순간 SETUP_V1 무효.

## 2026-07-25 빈 공간 V1 기준선 5분 (SETUP_V1 유지, 소리 알림 첨부)

- 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-25_empty_gate_v1_360s.jsonl`
- 분석: `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-25_empty_gate_v1_360s_summary.json`
- 워밍업 이후 분석: `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-25_empty_gate_v1_after60s_summary.json`
- 360초 캡처(앞 60초는 사람 퇴장 release 워밍업). 텔레메트리 3,598개 10.00Hz, MR60 UART 21,735프레임, 체크섬/파서/재부팅 0.
- 재실 YES: **6분 전 구간 0/3,598 (0.00%)**. YES 이벤트 0건. 30초 묶음 12개 전부 0.0%.
- 마지막 5분(60~360s) 순수 기준선: YES 0/2,998, 사건 0건, 지속시간 비율 0.00%. 시간당 환산 0.0 사건/hr로 PDF 오탐 게이트(≤5%/hr) 크게 초과 만족.
- 캡처 자동화에 macOS `afplay` 시스템 사운드와 `say -v Yuna` 한국어 음성을 결합하여 시작/워밍업 완료/전체 완료 3구간 알림을 넣었다. 이 알림은 데이터 수집 로직에 영향을 주지 않는다.

### 다음 즉시 단계
- 같은 SETUP_V1에서 0.9m 정지 인체 5분(360초, 앞 60초 워밍업) 캡처. 페어 기준선 완성.

## 2026-07-25 0.9m 정지 인체 V1 기준선 5분 (SETUP_V1 유지, 페어 완성)

- 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-25_occupied_d09_v1_360s.jsonl`
- 분석: `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-25_occupied_d09_v1_360s_summary.json`
- 워밍업 이후 분석: `firmware/esp_wroom32_mr60_monitor/analysis/baseline/2026-07-25_occupied_d09_v1_after60s_summary.json`
- 360초 캡처, 앞 60초 워밍업. 텔레메트리 3,598개 10.00Hz, MR60 UART 27,178프레임(75.5Hz), 체크섬/파서/재부팅 0.
- 마지막 5분(60~360s, n=2,998) 순수 기준선:
  - **재실 YES 2,998/2,998 (100.00%)**, dropout 0건.
  - 거리 bin 16(91.84cm) 986개 + bin 17(97.58cm) 2,012개. 중앙값 97.58cm.
  - 호흡 양수 2,726/2,998 (90.9%), 30초 구간별 60~100%로 진동 (150~180s 78%, 270~300s 60%). 평균 16.02rpm, 중앙값 17rpm, std 7.37rpm, 범위 1~31.
  - 심박 양수 2,998/2,998 (100%), 평균 89.09bpm, 중앙값 91bpm, std 10.16, 범위 69~107.
- 오프라인 median-of-5 필터로 호흡 std 개선 없음(동일 7.37). 창이 너무 짧기 때문. 다음 필터 비교에서는 최소 3초(30샘플) 창 또는 EMA 30초 등을 대조해야 한다.

### KPI 상태 갱신 (0.9m 5분 단독 시험 기준)
- 정지 인체 감지율 **100%** (KPI ≥95%) ✅
- 오탐 사건률 **0/hr** (KPI ≤5%/hr, 6분 환산) ✅
- 호흡 중앙값 17rpm이 PDF 정상 범위 12~20 안 ✅
- 호흡 std ±7.37rpm으로 ±2rpm 목표 미달. **무필터 원본**이므로 필터 비교 이후에 재평가.
- 위 결과는 1인·1자세·1거리·5분 단발 시험이므로 최종 KPI 근거는 아니다. 매트릭스 확장 필요.

### 관찰된 문제와 다음 대응
1. **거리 이동**: 5분 사이 bin 15→17로 약 12cm 뒤로 밀렸다. 다음 시험은 등받이 있는 의자 사용 권장.
2. **호흡 유효율 진동**: 60~100% 왕복. 위상(`breath_phase`) 원시값과 age_ms를 함께 분석하면 원인 파악에 도움이 될 가능성이 있다.
3. **호흡 std 큼**: 필터 비교 필요. 원본 로그 그대로 유지, 오프라인에서 여러 창 크기와 EMA 비교.

### 남은 단계 우선순위 (오늘 이후)
1. **오프라인 분석** (제가 단독 진행 가능): 필터 창 비교, 위상 신호 재검토, 진입퇴장 매트릭스 설계서 초안.
2. **진입→정지→퇴장 20회**: 감지·해제 지연 KPI(≤2초) 측정. 사용자 15~20분 소요.
3. **거리 매트릭스 0.6/0.9/1.2/1.5m**: 각 60초 이상. 사용자 10~15분 소요.
4. **호흡 정확도**: 메트로놈 12/15/20rpm 편안한 페이싱. 사용자 15분 소요.
5. **ESP 상태 머신 구현**: WARMUP/VALID/UNKNOWN/FAULT (설계는 오프라인 가능).
6. **Pi 통합 시작**: 열화상/PIR/CO2 융합, 규칙 기반 위험도 R.

## 2026-07-25 진입퇴장 10회 KPI 시험

- 프로토콜: "5초 뒤에 들어오세요" → 5초 카운트 → enter 마커 → "측정을 시작합니다" → 12초 정지 카운트 → exit 마커 → "나가세요" → 15초 쿨다운. 10회 반복.
- 스크립트: `firmware/esp_wroom32_mr60_monitor/entry_exit_trial.py`, 분석: `firmware/esp_wroom32_mr60_monitor/analyze_entry_exit.py`.
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/kpi/2026-07-25_entry_exit_10.jsonl` (센서 4,215샘플 + 비프 20개)
- 분석: `firmware/esp_wroom32_mr60_monitor/analysis/kpi/2026-07-25_entry_exit_10_maxwait25_summary.txt`

### 감지 지연 (enter 마커 → 첫 YES) — **KPI 통과**
- **10/10 통과 (100%)**. 평균 **0.274초**, 중앙값 0.237s, std 0.254s, 최소 0.027s, 최대 0.642s.
- PDF KPI ≤ 2초의 약 1/7~1/3 이하. 감지 성능은 대상 수준.
- 사용자가 카운트 "1초" 직후 IN 자리에 정착한 것으로 확인되며, 첫 YES 시각과 measurement-begin 마커의 시간차는 반응 여유 정도(<0.7s).

### 해제 지연 (exit 마커 → 5샘플 연속 NO) — **문제 발견**
- max_wait 15초로는 1/10, 25초로는 **8/10**만 해제. 회 9·10은 25초 창 안에도 해제되지 않음.
- 해제 지연 평균 **15.89초**, 중앙값 16.1s, std 4.0s, 범위 7.8~22.6s.
- 회 6만 예외적으로 7.8초에 해제. 나머지는 대부분 15~22초.

### 원인 분석 (원본 트레이스 확인)
- 회 1 exit: 15초간 거리 45.92cm(bin 8) 완전 고정. 사용자가 나갔는데 45cm에 무언가 계속 잡힘. 반사체 또는 다른 사람이 남았을 가능성.
- 회 2 exit: 거리가 120cm→40cm로 **감소**. 사용자가 나가면서 오히려 센서 쪽으로 접근한 트레이스. OUT 방향이 센서 반대편이 아니거나 센서를 지나쳐 갔을 가능성.
- 회 3, 9, 10 exit도 유사하게 100cm대→30~50cm대로 감소.
- 결론: (1) MR60BHA2 자체의 presence hysteresis가 크다(수~수십 초), (2) 사용자의 OUT 경로가 감지 원뿔을 완전히 벗어나지 않았을 가능성이 크다. 둘 다 원인일 수 있다.

### KPI 판정과 다음 대응
- **감지 KPI ≤2초는 확정 통과.** 개발완료보고서·최종보고서·시연영상에 그대로 인용 가능.
- 해제 지연은 PDF 명시 KPI 항목이 아니지만 "재실 없음 + CO2 상승 → 주의" 융합 규칙의 동작에 영향. Pi 융합 단계에서 열화상 인체 실루엣 매칭이 없으면 "재실 지속이지만 사람 아님"으로 재판정하는 방식으로 보완해야 한다.
- 프로토콜 개선안: OUT 자리를 센서 안테나 면 후방(감지 원뿔 밖) 3m로 재확정하고, 쿨다운을 25~30초로 확장하여 재측정. 다만 감지 KPI가 이미 통과했으므로 재시험 우선순위는 낮음.

### 스크립트 개선 사항
- 완료 알림 시 `play_sound()` 인자 개수 불일치로 크래시 발생. `play_sound(path)` + `say_blocking(text)`로 분리 수정. 데이터 손실 없음 (크래시가 완료 직전에 발생).

## 2026-07-25 한준우 인수용 mmWave CSV 전달 배치

- 근거 문서: 한준우 mmWave CSV 인수 조건 (2026-07-25 v3 배포본 기준). 스펙 12개 조항 100% 준수.
- 변환기: `firmware/esp_wroom32_mr60_monitor/export_mmwave_csv.py`
- 전달 폴더: `firmware/esp_wroom32_mr60_monitor/csv/2026-07-25_han_junwoo_delivery/`
- 매니페스트: 같은 폴더 `manifest.json` (원본 SHA256, 세션별 CSV SHA256, 세션 진단 포함)
- 원본 JSONL 사본도 `original_jsonl/`에 포함되며 SHA256 대조 통과.

### 세션 구성 (총 11개)

| session_id | label | records | duration | rate | max_gap | 원본 |
|---|---|---:|---:|---|---:|---|
| S001_NORMAL_5MIN_01 | NORMAL | 2,998 | 299.82s | 9.996Hz | 101ms | occupied_d09_v1_360s.jsonl (앞 60초 워밍업 skip) |
| S001_ENTRY_EXIT_01 | PRESENCE_TRANSITION | 409 | 40.82s | 9.995Hz | 102ms | entry_exit_10.jsonl |
| S001_ENTRY_EXIT_02 | PRESENCE_TRANSITION | 409 | 40.81s | 9.996Hz | 102ms | 동일 |
| ... 03~09 동일 규격 ... | | | | | | |
| S001_ENTRY_EXIT_10 | PRESENCE_TRANSITION | 362 | 36.12s | 9.995Hz | 102ms | 로그 종료로 짧음 |

전 세션에서 timestamp 중복 0건, 역행 0건, NaN/Inf breath_phase 0건.

### 스펙 준수 확인
- resp_phase 열 = ESP `breath_phase` 원값 그대로. ×100·Z-Score·offset 제거·smoothing·재샘플링 어느 것도 적용하지 않음.
- timestamp_s = ESP `ts_monotonic_ms` 기반, 세션 시작 시각을 0으로 리베이스한 실측 초.
- session_id 5분 인체 로그와 진입퇴장 10회 각 시도별로 분리. 서로 다른 로그 병합 없음.
- presence=0 구간에서도 resp_phase는 센서 원값 유지, 임의 0 생성 없음.
- 진입퇴장 라벨은 PRESENCE_TRANSITION (Class 1로 사용 금지 명시). NORMAL은 안정 5분만.
- signal_source=MR60BHA2_breath_phase, device_id=safenest-node-01.
- 파일명 규칙: `<원본stem>__<session_id>.csv` 로 원본 대응 명시.

### 팀원 인수 후 요청 사항 (한준우 검증 항목 이 배치 이후)
1. 필수 열·타임스탬프·NaN/Inf·gap 재검증
2. 세션별 실측 10Hz 재샘플링 후 300 sample window 생성
3. 자체 breath_phase와 공개 resp_phase 분포 비교 (도메인 mismatch 정량화)
4. 기존 metadata로 정규화 시 flatline 여부 확인
5. Raspberry Pi 5 추론 지연 p50/p95 측정
6. Class 1 출력 처리: MMWAVE_CLASS_UNVERIFIED로 DEGRADED 처리 (양성 학습 샘플 없음)

### 남은 조사 항목 (내 담당)
- MR60BHA2 Seeed SDK가 raw complex/rFFT 또는 unwrap 전 phase 출력을 지원하는지 데이터시트/펌웨어 소스 조사.
- 지원 시 → ESP 펌웨어에서 raw phase 추출해 학습 도메인 정렬 가능.
- 미지원 시 → 팀원이 device-domain calibration Adapter를 검증하는 방향으로 확정.

## 2026-07-25 오후 세션 후반 (거리 매트릭스 + 메트로놈 12rpm)

### 거리 매트릭스 5분 각 (V1 이후 사용자만 이동)
| 안내 거리 | 실측 중앙값 | 재실 감지율 | 호흡 유효율(감지 순간 대비) | 판정 |
|---|---|---|---|---|
| 60cm | 74.62cm (bin 13) | 100% | 99.7% | 최적 |
| 90cm (V1 기준선) | 97.58cm (bin 17) | 100% | 90.9% | 최적 |
| 120cm | 132.02cm (bin 23) | **81.4%** | 99.96% | KPI 미달 |
| 150cm | **183.68cm (bin 32)** | 88.0% | — | 상수 fallback |

원본: `firmware/esp_wroom32_mr60_monitor/logs/matrix/2026-07-25_occupied_d{06,12,15}_v1_360s.jsonl`
분석: `firmware/esp_wroom32_mr60_monitor/analysis/matrix/2026-07-25_occupied_d{06,12,15}_v1_after60s_summary.json`

### 결정적 발견: 150cm 시험에서 상수 fallback 출력
- 5분 2,999 샘플 내내 breath_rate_raw 정확히 15.0rpm, heart_rate_raw 정확히 87.0bpm, std 모두 0.0.
- 살아있는 사람의 생체값은 자연 변동 존재 → std=0은 실측 실패 시 fallback 값 출력 근거.
- ESP 상태 머신 UNKNOWN 조건에 **"std=0 지속" 규칙 추가 필요.**
- 대회 관점: PDF의 "센서 결측을 정상으로 숨기지 않는다" 안전 설계 원칙의 실증 사례.

### 도메인 결론 (실측 근거)
- **mmWave 단일 노드 최적 배치 = 실제 흉부까지 60~100cm**
- 100cm 초과 시 감지율 95% 미만
- 1.5m 이상 = 열화상(Thermal-44) 담당 영역
- PDF 5절 예상 문제점 대응 방안의 다중 노드·센서 융합 근거를 뒷받침

### 메트로놈 12rpm 페이싱 (4분)
- 원본: `firmware/esp_wroom32_mr60_monitor/logs/breath/2026-07-25_breath_paced_12rpm.jsonl`
- 메트로놈 정확도: 5.000 ± 0.003s (신호 완벽)
- 센서 breath_rate_raw: 평균 5.63rpm, 중앙값 4.0rpm (목표 12rpm과 큰 괴리)
- 유효율 67.8%, |센서−목표| 평균 오차 7.24rpm
- **KPI ±2rpm 통과율 16.8%** (원본 무필터 상태)
- 원인 후보: (a) MR60 내부 호흡 추정 창이 짧아 12rpm 못 잡음, (b) breath_rate_raw 반응 지연
- 필터·모델 없이는 KPI 통과 불가 → 한준우가 위상 신호 기반 재추정 방향으로 처리 필요.

### 세션 종료 및 다음 재개 (2026-07-25 → 2026-07-26)
- 사용자가 하드웨어 뽑기 결정. 원본 데이터는 모두 파일로 보존.
- 사진 3장(정면·측면·사용자 시점) + 배선 사진 1장 촬영 요청.
- 남은 pending 태스크: 15rpm, 20rpm 메트로놈, 종합 CSV 배치 재출력.
- 재개 시 필요 순서: USB 재연결 → 포트 확인 → healthcheck 15초 → 빈 공간 게이트 60초 → 남은 시험.

## 2026-07-26 GitHub 비공개 저장소 준비

- 대상 계정/저장소: `jinsu1011/safenest-embedded-competition` (비공개, 사용자 승인 완료).
- 로컬 상태: 기존 Git 저장소의 `main` 브랜치, 아직 최초 커밋과 원격 저장소 없음.
- 보안 점검: 추적 후보 파일에서 비밀번호·API 키·토큰·개인 이메일 패턴 미발견. 빌드 산출물, 가상환경, 캐시, 임시 파일, 로컬 DB는 `.gitignore`로 제외.
- 협업 문서: 루트 `README.md`, `CONTRIBUTING.md`, `.gitignore` 작성.
- 재현성 수정: `run_dashboard.command`의 사용자별 절대경로와 Homebrew Python 고정 경로를 제거하고, 스크립트 위치 및 로컬 가상환경/`python3`를 사용하도록 변경.
- 검증: Pi 단위 테스트 8개 통과, Python 구문 검사 통과, ignore 규칙 확인 완료.
- 펌웨어 빌드: PlatformIO가 Espressif 플랫폼을 내려받는 단계에서 샌드박스 네트워크 제한으로 실패. 권한 재시도도 현재 사용량 제한으로 거부되어 이번 단계에서는 빌드 미검증이며, 기존 `.pio` 산출물은 저장소에서 제외.
- 저장소 생성: Chrome의 로그인 세션에서 `jinsu1011/safenest-embedded-competition`을 `Private`로 생성 완료. GitHub 쪽 README/.gitignore/license 초기화는 끄고 로컬 이력을 최초 이력으로 사용한다.
- Git 준비: 원격 `origin`을 비공개 저장소 URL에 연결하고, 업로드 대상 84개 파일을 명시적으로 stage 완료. 원시 JSONL/분석 CSV는 실험 근거로 포함하고 `.pio`, 가상환경, 캐시, 임시 파일은 제외했다.
- 최초 커밋: 업로드 대상 84개, 60,875줄로 `Initialize SafeNest competition repository` 커밋 생성. Pi 단위 테스트 8개와 Python 구문 검사 통과, 소스·설정 파일 공백 검사 통과. 원시 로그/CSV의 CRLF는 원본 불변 원칙에 따라 그대로 보존했다.
- 최초 push/원격 검증: `main`을 `origin/main`으로 업로드했고 로컬 HEAD와 원격 추적 SHA가 일치함을 확인했다. 로그인된 GitHub 페이지에서 `Private` 표시, SafeNest README, `Initialize SafeNest competition repository` 커밋이 모두 보이며 404가 아님을 확인했다.
- 다음 단계: 팀원 GitHub 사용자명을 받아 `Settings → Collaborators`에서 초대하고, 각 팀원이 clone/branch/push/PR 흐름을 1회 검증한다.

## 2026-07-26 GitHub 팀원 초대

- 비공개 저장소 Collaborator 초대 4건 발송 완료, 접근 관리 화면에서 `4 invitations`와 각 `Pending Invite` 상태를 확인했다.
- GitHub 계정으로 확인된 대상: `@sheepmeat`, `@yuseungha`, `@rla1729`.
- 나머지 1건은 GitHub 사용자명으로 확인되지 않아 제공된 이메일로 직접 초대했으며, 수신자가 해당 이메일로 초대를 수락해야 한다.
- 초대 수락 후 검증할 항목: private repo 열람, clone, 개인 브랜치 push, pull request 생성.

## 2026-07-28 MR60BHA2 작업 재개

### 재개 체크리스트

- [x] 전임 인수인계와 `PROJECT_PROGRESS.md`, `MMWAVE_HANDOFF.md`, `HARDWARE_RUNBOOK.md`, `MMWAVE_TUNING.md`, `TEAM_OPERATING_MODEL.md` 재확인.
- [x] 기존 ESP-WROOM-32 UART2 raw collector, 캡처·페이싱·CSV 변환 코드와 원본 로그 보존 상태 확인.
- [x] 전임자가 추가한 2026-07-25 거리 매트릭스·12rpm 결과 40줄이 미커밋 상태임을 확인하고 그대로 보존.
- [x] `/dev/cu.usbserial-110` 존재 및 포트 점유 프로세스 없음 확인.
- [x] 필터 없는 15초 healthcheck 수행 및 ESP JSON/UART/checksum/parse/reboot 지표 계산.
- [x] 재연결 설치의 빈 공간 게이트 재검증.
- [x] 게이트 통과 후 0.9m 안정 자세에서 15rpm 페이싱 3분 수집.
- [x] 동일 조건에서 20rpm 페이싱 3분 수집.
- [x] 12/15/20rpm 유효 JSONL과 SHA-256 manifest를 팀 통합 브랜치에 게시.

### 현재 판단

- 코드와 과거 로그는 인수인계 내용과 일치한다. 현재 펌웨어는 필터 없는 `sensor_state=RAW` 텔레메트리를 10Hz로 내보내며 위험 판정은 하지 않는다.
- 실제 필터나 유효성 임계값은 이번 재개 단계에서 변경하지 않는다. 먼저 UART 상태와 설치 게이트를 확인한다.
- 다음 단일 행동: 새 원본 `logs/diagnostics/2026-07-28_healthcheck_15s.jsonl`을 수집하고 통신 지표를 판정한다.

## 2026-07-28 팀 GitHub OnDevice_AI 자료 감사

### 원격 상태와 병합 판단

- `git fetch --prune origin`으로 병합 없이 원격을 확인했다. 로컬 `main`은 `origin/main`보다 3커밋 뒤이며 새 브랜치는 `origin/Ondevice_AI`, `origin/3D_Print`이다.
- `origin/3D_Print`는 STL 4개만 포함해 mmWave 튜닝과 직접 관계없다.
- 당시 `origin/main`과 `origin/Ondevice_AI`에는 `SafeNest_V4_OnDevice_AI/` 패키지가 추가됐지만, 루트 `README.md` 삭제와 기존 `config/risk_rules.json` 이동도 포함했다. 현재 구조는 기능별 디렉터리로 이관됐다.
- 최신 `origin/Ondevice_AI`는 `/private/tmp/safenest-ondevice-review` 분리 worktree에서 읽기·테스트했다. 현재 작업 브랜치에는 병합하지 않았다.

### mmWave 호환성 검증

- 팀 가이드는 학습 입력을 `rFFT → phase unwrap → clutter 제거/BPF → 10Hz, 300샘플` 파형으로 정의하고, MR60 vendor 호흡수·상태를 같은 입력으로 사용하지 말라고 명시한다.
- 배포 manifest의 mmWave 항목도 `real_sensor_csv_validation=false`, Raspberry Pi 5 benchmark 미완료다.
- 기존 한준우 전달용 0.9m MR60 정상 CSV를 팀 `MMWaveCSVAdapter`에 넣었을 때 30초 윈도우 90개가 생성되어 파일 계약·타임스탬프 계약은 호환됐다.
- 그러나 MR60 `breath_phase` 윈도우 전체 표준편차는 `0.12227`(윈도우 중앙값 `0.11777`)이고 배포 NPZ train 표준편차는 `1.71715`로 약 14배 차이다. 입력 도메인이 일치한다고 볼 근거가 없다.
- 배포 `sensor_stats_metadata_v0.1.0.json`은 mean/std=`0.00609/2.50138`인데 실제 NPZ train mean/std=`0.17212/1.71715`로 서로 불일치한다.
- `datasets/build_processed_npz.py`는 source path가 있어도 실제 Zenodo 원본을 읽지 않고 난수/합성 사인파를 생성한다. README/MANIFEST의 실데이터 출처·피험자 분할 설명과 재생성 코드가 일치하지 않는다.

### 안전 결함과 테스트

- 가이드는 300개 미만 window를 zero-padding하지 말고 `WARMING_UP, valid=false`로 반환하라고 명시하지만 `sensors/mmwave/mmwave_adapter.py`는 부족한 버퍼를 0으로 채워 즉시 정상 추론한다.
- 통합 위험도 코드에서는 잘못 `valid=true`로 들어온 `breath_rpm=0`이 2초 뒤 `EMERGENCY_APNEA`가 될 수 있다. `0/null/timeout을 무호흡으로 변환하지 않는다`는 SafeNest 규칙과 충돌한다.
- 분리 환경에서 CSV/stream adapter 단위 테스트 9개는 통과했다.
- 전체 테스트는 현재 검증 환경에 `ai_edge_litert`, `tflite_runtime`, `tensorflow`가 없어 24개 발견 중 8개 모듈 import 단계에서 중단됐다. 코드 실패로 단정하지 않지만 문서의 74개 PASS를 이번 감사에서 재현하지 못했다.

### 튜닝 결론

- ESP 필터·임계값을 이 모델에 맞춰 변경하지 않는다. 먼저 Pi에서 `input_mode=vendor_rule` 또는 `MMWAVE_CLASS_UNVERIFIED/DEGRADED`로 운용해야 한다.
- 첫 변경 후보는 Pi mmWave 입력 안전 게이트 하나다: `300 미만/재연결/gap/stale/0/null/NaN/presence=0 → WARMING_UP 또는 UNKNOWN`, 모델 APNEA 비상 오버라이드 비활성화.
- 모델 모드는 12/15/20rpm 실측 로그와 실제 NORMAL 다피험자 로그로 도메인 검증하고 metadata를 다시 산출한 뒤에만 승인한다.
- 코드 변경은 사용자 승인 전 보류한다.

## 2026-07-28 MR60 순차 재검증

### 작업 체크리스트

- [x] 필수 문서 4개와 ESP-WROOM-32 원시 수집 코드 확인
  - 결과: UART2 GPIO16/17, 115200 8-N-1, Tiny Frame checksum/parse 누계와 10Hz 무필터 JSONL 출력 구조를 확인했다.
- [x] 현재 USB 직렬 포트와 점유 상태 확인
  - 결과: `/dev/cu.usbserial-110`, CH340 계열 `VID:PID=1A86:7523`으로 열거됐고 포트 점유 프로세스는 없었다.
- [x] 15초 원시 healthcheck 및 UART·필드 유효성 판정
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-28_healthcheck_15s_v2.jsonl`, SHA-256 `4ceed1327eeda150d00352e2150438a8a400102d670775680672b9b8d5f1567d`.
  - 결과: 14.81초, 149레코드(10.06Hz), MR60 UART 1,118프레임(75.49Hz), checksum/parse 오류 0, 재부팅 0.
  - 현재 raw presence는 149/149 true이고 거리 중앙값 51.66cm였다. 호흡·심박 양수값도 전 구간 출력됐지만 시험 조건이 확인되지 않아 정확도나 재실 성능 근거로 사용하지 않는다.
  - 분석: `firmware/esp_wroom32_mr60_monitor/analysis/diagnostics/2026-07-28_healthcheck_15s_v2_summary.json`.
- [x] 빈 공간 5분 무필터 기준선 수집
  - 사전 게이트: `logs/diagnostics/2026-07-28_empty_preflight_20s.jsonl`, 200/200 presence=false, UART checksum/parse 오류 0.
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-28_empty_v2_360s.jsonl`, SHA-256 `db3418ca632c29d8edac55a22b892a3a2dcff1b4333307c175673e1d23854618`.
  - 전체 359.924초 3,599레코드, 10.00Hz, MR60 UART 21,637프레임, checksum/parse 오류 0, 재부팅 0.
  - 앞 60초 제외 순수 5분은 2,999/2,999 presence=false, 거짓 재실 0건, 양수 거리·호흡·심박 0건이었다.
  - 분석: `analysis/baseline/2026-07-28_empty_v2_360s_summary.json`, `analysis/baseline/2026-07-28_empty_v2_after60s_summary.json`.
- [x] 0.8~1.0m 정지 인체 5분 무필터 기준선 수집
  - 위치 게이트: 3차 확인에서 100/100 presence=true, 거리 중앙값 80.36cm(80.36~86.10cm), UART 오류 0으로 통과했다.
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/baseline/2026-07-28_occupied_d09_v2_360s.jsonl`, SHA-256 `db47b6092151edad253fc7dc990f3304c053335cd14077b795feee1f4125abe3`.
  - 전체 359.853초 3,598레코드, MR60 UART 27,279프레임, checksum/parse 오류 0, 재부팅 0.
  - 앞 60초 제외 순수 5분은 presence=true 2,998/2,998(100%), 거리 중앙값 86.10cm, 호흡 양수 유효률 100%, 평균/중앙값/std 22.68/24.0/4.88rpm, 심박 평균/중앙값/std 83.56/84.0/13.38bpm이었다.
  - 기준 호흡·심박 정답이 없는 자연호흡 조건이므로 정확도나 정상/이상 판정은 확정하지 않는다.
  - 분석: `analysis/baseline/2026-07-28_occupied_d09_v2_360s_summary.json`, `analysis/baseline/2026-07-28_occupied_d09_v2_after60s_summary.json`.
- [x] 진입→정지→퇴장 20회 재검증
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/kpi/2026-07-28_entry_exit_20_v2.jsonl`, SHA-256 `f28c41166a0da3104c74b207014aae4ff7be508876175f4881eb72bdb94d5164`.
  - 프로토콜: 5초 진입 카운트, 12초 정지, 30초 감지 범위 밖 대기, 20회. 센서 원시 11,354샘플과 enter/exit 마커 40개를 같은 host monotonic clock으로 기록했다.
  - UART 프레임 증가 63,893, checksum/parse 오류 0, 재부팅 0.
  - enter 마커부터 첫 YES까지 평균 1.134초, 중앙값 1.073초, 최대 2.449초, 2초 이내 16/20. 보행·반응 후보 0.8초를 차감한 참고값은 평균 0.493초, 최대 1.649초, 20/20 통과다.
  - exit 마커부터 연속 NO 5샘플까지 19/20 검출, 평균 15.491초, 중앙값 15.814초, 범위 10.515~17.713초. 1회는 30초 안에 해제되지 않았다.
  - 결론: raw 진입 검출 자체는 빠르지만 MR60 vendor presence 해제 hysteresis가 약 15초로 2초 요구를 만족하지 못한다. ESP에서 거짓 NO를 만들지 않고 Pi의 Thermal/PIR 융합으로 퇴장 상태를 보완해야 한다.
- [x] 15rpm 안전 페이싱 호흡 3분 수집
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/breath/2026-07-28_breath_paced_15rpm_v2.jsonl`, SHA-256 `00ddd3ee6d962d3cdad1ecc79c0f30b76f8fd56946c1d1c622e81aeb3007d20a`.
  - 프로토콜: 거리 중앙값 80.36cm, 30초 박자 적응 후 4초 주기 신호로 180초 측정. 숨참기나 강제 과호흡은 하지 않았다.
  - 본 측정 1,799샘플, presence=true 100%, 양수 호흡 유효률 77.32%. 센서 호흡 평균/중앙값/std 9.69/7.0/8.16rpm, 15rpm 대비 MAE 8.86rpm, ±2rpm 통과율 8.99%였다.
  - UART 프레임 증가 13,659, checksum/parse 오류 0, 재부팅 0.
  - 판정: vendor `breath_rate_raw`는 현재 조건에서 ±2rpm KPI를 통과하지 못한다. 20rpm 동일 프로토콜과 위상 기반 오프라인 분석 전에는 임계값이나 필터를 확정하지 않는다.
- [x] 15rpm 재시험 및 방법 전환 판정
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/breath/2026-07-28_breath_paced_15rpm_retry_v2.jsonl`, SHA-256 `19fe9266e44f87932f26cfc926f470bbf033dd2c67f4eca68a6998e0d11b9722`.
  - 위치 게이트: 거리 중앙값 86.10cm, 범위 86.10~91.84cm, presence=true 100/100, UART 오류 0. 60초 박자 적응 후 180초를 기록했다.
  - 본 측정 1,799샘플에서 presence=true 100%, 거리 중앙값 91.84cm였으나 `breath_rate_raw`는 1,799/1,799 모두 0rpm이었다. 이를 무호흡으로 해석하지 않고 유효률 0%, UNKNOWN으로 판정한다.
  - 같은 구간 `breath_phase`는 1,799개 모두 존재했고 표준편차 0.450, 범위 -1.08~1.15, 고유 양자값 183개로 살아 있었다.
  - 동일 vendor 호흡수 방법이 15rpm 1차와 재시험에서 두 번 실패했으므로 반복을 중단한다. 이후 20rpm은 vendor rate 정확도 시험이 아니라 라벨된 phase 비교용으로만 수집하고, 분석 방법을 위상 기반 주기 추정으로 전환한다.
- [x] 15rpm 30초 즉시 확인
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-28_breath15_quickcheck_30s.jsonl`.
  - 300샘플, presence=true 100%, 거리 중앙값 80.36cm, checksum/parse 오류 0.
  - 양수 호흡수 161/300(53.67%), 나머지 139개는 0rpm. 양수값 평균/중앙값/std 8.15/7.0/5.90rpm, 13~17rpm 비율 26.71%, 15rpm MAE 7.47rpm이었다.
  - `breath_phase` 표준편차 0.525, 범위 -0.96~1.03으로 위상은 계속 변화했다. 짧은 재확인에서도 vendor 호흡수는 정상 출력 기준을 통과하지 못했다.

### 2026-07-28 15rpm 실패 원인 분석

- 공식 Seeed 라이브러리의 enum과 parser를 대조해 ESP의 `0x0A13` phase, `0x0A14` breath rate, `0x0A15` heart rate, `0x0A16` distance 해석이 일치함을 확인했다. UART checksum/parse 오류도 반복해서 0이므로 현재 증거상 프레임 타입 오해 가능성은 낮다.
- 공식 Seeed 설치 문서는 MR60BHA2 생체 기능을 수면 시나리오에만 권장하며 책상 착석·운동에서는 큰 부정확성이 발생할 수 있다고 경고한다. 권장 설치는 침상 머리 위 약 1m, 흉부를 향한 45도 하향, 흉부까지 1.5m 이내다.
- 공식 문서는 진동 설치, 움직이는 커튼/식물, 금속·거울 반사, 저품질 전원을 간섭원으로 명시한다. 에어컨 자체보다 직접 바람에 움직이는 옷·커튼·물체와 책상/센서 진동 여부가 중요하다.
- 공식 펌웨어 이력에는 안정된 인체에서 호흡·심박이 검출되지 않는 문제(v1.6.5 수정 항목)와 이전 호흡·심박 알고리즘의 근본 문제 및 지속 최적화가 기록돼 있다. 현재 센서 firmware frame은 `null`이라 실제 버전을 아직 모른다. 승인 없이 업데이트하지 않고 버전 조회만 필요하다.
- 15rpm 세 로그의 `breath_phase` FFT 지배 주기는 각각 7.34rpm, 7.67rpm, 8.0rpm이었다. 이는 vendor 호흡수 중앙값 7rpm과 일치하며, 목표 15rpm의 절반이다.
- 가장 먼저 확인할 가설은 사용자가 한 신호에서 들이쉬고 다음 신호에서 내쉬어 한 호흡 주기를 8초로 수행했는지 여부다. 한 신호부터 다음 신호까지 들숨+날숨을 모두 끝냈다면 4초/15rpm이므로, 그 경우에는 책상 착석·진동·안테나 정렬·센서 firmware 알고리즘을 우선 의심한다.
- [ ] 기준선 통계와 다음 실험 조건 확정

### 2026-07-28 명시적 호흡 안내 재시험

- [x] 기존 `breath_pace_capture.py`의 단일 4초 신호 방식은 보존하고 `--explicit-phases` 옵션을 추가했다.
  - 결과: 15rpm에서 `들이쉬세요`와 `내쉬세요`를 각각 2초 간격으로 안내하고, 두 이벤트를 동일 JSONL에 monotonic timestamp로 기록한다.
  - 검증: 가상환경 Python의 `py_compile` 및 `--help` 실행 성공.
- [x] 거리·재실·UART 사전 게이트
  - 1차는 거리 중앙값 74.62cm여서 약 10~15cm 후방 이동을 음성 안내했다.
  - 2차 `logs/diagnostics/2026-07-28_breath15_explicit_preflight02_10s.jsonl`은 100샘플 모두 presence=true, 거리 86.10cm, checksum/parse 오류 증가 0으로 통과했다.
- [x] 명시적 15rpm 30초 원시 로그 수집
  - 원본: `firmware/esp_wroom32_mr60_monitor/logs/diagnostics/2026-07-28_breath15_explicit_quickcheck_30s.jsonl`.
  - SHA-256: `af0137c773a5b6ad6140d05e516008b81ef07e96383f74acb3865152605132f1`.
  - 2초 간격 들숨/날숨 음성 안내와 cue marker를 기록했으며 불편을 유발하는 숨참기·과호흡은 지시하지 않았다.
- [x] vendor rate와 breath phase 주기 분석
  - 분석: `analysis/diagnostics/2026-07-28_breath15_explicit_quickcheck_30s_summary.json`.
  - 300샘플/29.91초, presence=true 100%, 거리 중앙값 86.10cm, UART 2,265프레임 증가, checksum/parse 오류 0.
  - 들숨 간격 평균 4.0007초, 모든 위상 안내 간격 평균 2.0004초로 목표 페이싱을 검증했다.
  - `breath_phase` FFT 지배 주기는 14.00rpm이었다. 30초 FFT 분해능이 약 2rpm이므로 목표 15rpm과 일치하는 구간으로 판정하며, 이전 7~8rpm 절반 주기 문제는 해소됐다.
  - 반면 vendor `breath_rate_raw`는 양수 유효률 100%지만 평균/중앙값 19.47/19.0rpm, 표준편차 1.27rpm, 목표 ±2rpm 비율 4%, MAE 4.47rpm으로 정확도 기준을 통과하지 못했다.
  - 결론: 이전 저주파 문제에는 안내 방식이 영향을 줬지만, 안내만 수정해 vendor 호흡수까지 정상화되지는 않았다. 다음은 동일 명시적 방식으로 충분한 워밍업을 포함한 3분 로그를 확보해 위상 기반 추정과 vendor rate를 비교한다.

### 2026-07-28 명시적 호흡 안내 재생 오류 수정

- [x] 첫 명시적 시험에서 사용자가 중간 음성 신호를 듣지 못했다고 확인했다.
- [x] 비동기 `say` 호출을 각 안내가 종료될 때까지 기다리는 동기 호출로 변경했다.
- [x] 들숨에는 Tink, 날숨에는 Pop 구분음을 음성 안내와 함께 재생하도록 변경했으며 `py_compile`을 통과했다.
- [x] 동기 음성 방식 재측정은 30초 중 약 10초, 들숨 3회/날숨 2회만 기록돼 무효 처리했다.
  - 원인: 매 단계의 동기 TTS 실행 시간이 실시간 페이싱 루프를 점유했다.
  - 원본은 `logs/diagnostics/2026-07-28_breath15_explicit_audible_retry_30s.jsonl`로 보존하되 정확도 통계에는 사용하지 않는다.
- [x] 동일 음성 방식을 반복하지 않고, 측정 전 음성 설명 후 Tink(들숨)/Pop(날숨) 구분음만 비동기로 재생하도록 전환했다.
  - 검증: 두 시스템 음원 파일 존재 및 `py_compile` 통과.
- [x] 구분음 방식으로 30초 재측정 및 신호 간격 검증
  - 원본: `logs/diagnostics/2026-07-28_breath15_tones_retry_30s.jsonl`, SHA-256 `ae9a81e27223f3fb783368303ce174e9134078305ca9e64e6e12d0e5b28befc6`.
  - 안내 검증: 들숨 Tink 8회, 날숨 Pop 7회, 전체 간격 평균 2.00036초, 들숨 간격 평균 4.00072초로 30초 페이싱을 완주했다.
  - 센서 검증: 300샘플/29.92초, presence=true 100%, 거리 중앙값 86.10cm, checksum/parse 오류 0.
  - `breath_phase` 지배 주기 14.00rpm으로 30초 FFT 분해능 내에서 목표 15rpm과 일치했다.
  - vendor `breath_rate_raw` 평균/중앙값 17.61/19.0rpm, 표준편차 2.10rpm, 목표 ±2rpm 전체 비율 27%, MAE 3.12rpm으로 개선됐지만 정확도 기준은 아직 미달이다.

### 2026-07-28 다중 속도 보정 로그 수집

- [x] `breath_pace_capture.py` cue에 `stage=warmup|measurement`를 추가했다.
- [x] `analyze_paced_breathing.py`가 본 측정 cue만 선택하고 기존 stage 없는 로그도 분석하도록 호환성을 검증했다.
- [x] 12rpm: 사전 게이트 통과, 워밍업 60초, 본 측정 180초, 분석
  - 사전 로그 `logs/diagnostics/2026-07-28_breath12_preflight_10s.jsonl`: 100/100 presence=true, 거리 중앙값 86.10cm, checksum/parse 오류 증가 0.
  - 첫 장기 측정 시도는 긴 macOS 음성 안내 단계에서 종료됐다. `logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2.jsonl`에는 23.8초 센서값과 cue 0개만 있어 무효로 보존한다.
  - 반복 방식 전환: 긴 TTS와 음성 카운트다운을 제거하는 `--tones-only`를 추가하고 Glass(준비), Tink/Pop(호흡), Ping(본 측정), Hero(종료) 신호만 사용한다.
  - 두 번째 장기 시도 `logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt02.jsonl`도 센서 19.6초, warmup cue 6개, measurement cue 0개로 무효 처리했다.
  - 원인 확정: 장기 `exec_command`가 반환한 session ID를 보존·폴링하지 않아 호출 컨텍스트 종료 시 측정 프로세스가 유지되지 않았다. 다음 시도는 persistent exec session을 `write_stdin`으로 30초마다 폴링한다.
  - 유효 원본: `logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03.jsonl`, SHA-256 `c8d989607aa7dc4499c217d3614fc6c39f4ce767cc82b8d5f69b65d1b0f3093f`.
  - 프로토콜 완주: warmup 들숨/날숨 각 12회, 본 측정 각 36회. 본 측정 1,799샘플/179.89초, 들숨 간격 평균 5.00002초, 전체 신호 간격 2.50017초.
  - 센서 상태: presence=true 100%, 거리 중앙값 80.36cm, UART 13,686프레임 증가, checksum/parse 오류 0.
  - 정확도: `breath_phase` 지배 주기 12.34rpm으로 목표와 일치. vendor rate 평균/중앙값/std 14.52/14.0/1.33rpm, 목표 ±2rpm 전체 비율 70.04%, MAE 2.61rpm.
  - 판정: 위상 기반 주기 추정은 12rpm을 재현했지만 vendor rate는 약 +2.5rpm 편향되어 단독 정확도 기준에 미달한다.
- [x] 15rpm: 사전 게이트 통과, 워밍업 60초, 본 측정 180초, 분석
  - 사전 로그 `logs/diagnostics/2026-07-28_breath15_full_preflight_10s.jsonl`: 99/99 presence=true, 거리 중앙값 86.10cm, checksum/parse 오류 증가 0.
  - 유효 원본: `logs/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl`, SHA-256 `f5e9d92449ea966d075d46b0b499afdfc58534193eeba1ed1e7f09f34b7a113a`.
  - 프로토콜 완주: warmup 들숨/날숨 각 15회, 본 측정 각 45회. 본 측정 1,799샘플/179.87초, 들숨 간격 평균 4.00011초, 전체 신호 간격 2.00011초.
  - 센서 상태: presence=true 100%, 거리 중앙값 86.10cm, UART 13,641프레임 증가, checksum/parse 오류 0.
  - 정확도: `breath_phase` 지배 주기 15.01rpm으로 목표와 일치. vendor rate 평균/중앙값/std 18.80/19.0/1.27rpm, 목표 ±2rpm 전체 비율 11.23%, MAE 3.80rpm.
  - 판정: 위상 기반 주기 추정은 15rpm을 정확히 재현했지만 vendor rate는 약 +3.8rpm 편향되어 단독 정확도 기준에 미달한다.
- [x] 20rpm: 사전 게이트 통과, 워밍업 60초, 본 측정 180초, 분석
  - 사전 로그 `logs/diagnostics/2026-07-28_breath20_full_preflight_10s.jsonl`: 100/100 presence=true, 거리 중앙값 86.10cm, checksum/parse 오류 증가 0.
  - 유효 원본: `logs/breath/2026-07-28_breath_paced_20rpm_explicit_full_v2.jsonl`, SHA-256 `7ec04ab21e08740de840d1f9f6f58c362293cb3ce9a2d243657225fe246b4b88`.
  - 프로토콜 완주: warmup 들숨/날숨 각 20회, 본 측정 각 60회. 본 측정 1,799샘플/179.87초, 들숨 간격 평균 3.00002초, 전체 신호 간격 1.50007초.
  - 센서 상태: presence=true 98.61%, 거리 중앙값 86.10cm, UART 13,038프레임 증가, checksum/parse 오류 0.
  - 25샘플/2.5초의 단일 presence=false 구간이 있었고 25개 모두 호흡 0과 겹쳤다. 0은 무호흡으로 해석하지 않고 UNKNOWN으로 유지한다.
  - 정확도: `breath_phase` 지배 주기 20.01rpm으로 목표와 일치. vendor 양수 rate 평균/중앙값/std 19.40/22.0/6.39rpm, 목표 ±2rpm 전체 비율 20.90%, MAE 5.02rpm.
  - 판정: 위상 기반 추정은 20rpm을 재현했지만 vendor rate 분산과 결측이 커 단독 정확도 기준에 미달한다.
  - 12/15/20 비교: `analysis/breath/2026-07-28_breath_calibration_12_15_20_comparison.json`. 목표별 편향이 일정하지 않아 고정 오프셋 보정은 채택하지 않는다.
  - 생체값 비교: `analysis/breath/2026-07-28_vitals_measured_vs_reference.json`.
  - MR60 심박 출력은 12/15/20rpm 조건에서 평균 75.12/78.73/85.06bpm, 중앙값 74/79/82bpm이었다. 유효률은 100/100/98.55%였지만 동시 기준 심박계가 없으므로 정확도·MAE는 계산하지 않는다.
  - `heart_phase` 최상위 후보는 47.69/78.04/87.71bpm이었다. 12rpm 조건에서 vendor 중앙값 74bpm과 불일치하므로 phase와 vendor 값의 내부 일치만으로도 심박을 검증할 수 없다.
  - 심박은 외부 기준기기 동시 측정 전까지 `UNVERIFIED` 또는 `UNKNOWN`으로 유지하고 위험 판정의 단독 근거로 사용하지 않는다.

### 작업 경계

- 기준선 전에는 필터·유효성 임계값·MR60 펌웨어를 변경하지 않는다.
- 기존 미커밋 진행 기록과 원본 로그를 보존하고, 이번 단계의 새 원본·파생 분석만 별도 경로에 추가한다.

### 최종 인수 완료 기준

- 실측 원본, 익명화된 학습·검증용 CSV/NPZ, 조건·라벨·SHA256 manifest를 함께 제공한다.
- ESP 텔레메트리와 팀 `.` 입력 사이의 Pi 어댑터를 구현하고 `0/null/NaN/timeout/presence=0` 안전 게이트를 포함한다.
- WARMUP/VALID/UNKNOWN/FAULT, 모델 미검증 시 `vendor_rule` 폴백, 실행 명령과 테스트를 문서화한다.
- 팀원이 별도 설명 없이 clone 후 테스트하고 통합할 수 있는 브랜치/PR 상태로 GitHub에 게시한다.

### 2026-07-29 Pi 통합 안전 계약 및 필터 선택

- [x] 동일한 12/15/20rpm 유효 원본 로그에 raw/MA5/median5/EMA0.3/median+EMA를 재생 비교했다.
  - 결과: `firmware/esp_wroom32_mr60_monitor/analysis/breath/2026-07-28_breath_filter_comparison.json`.
  - raw pooled 표준편차/MAE는 4.396/3.804rpm이었다. median+EMA는 4.359/3.791rpm이지만 평균 0.433초 추가 지연과 추가 이상치를 만들었다.
  - 결론: vendor rate 평활은 채택하지 않는다. 원시는 진단용으로 보존하고 Pi의 30초 phase FFT를 최종 호흡수로 사용한다.
- [x] `src/sensors/mmwave/mr60_esp_adapter.py`에 60초 WARMUP, distance/presence/age/UART 안전 게이트와 phase 기반 호흡 추정을 구현했다.
- [x] 0·NaN·결측·부재를 무호흡 또는 정상값으로 바꾸던 팀 코드 경로를 차단했다.
  - 미검증 심박은 위험도에 기여하지 않으며 `heart_verified=false`로 전달한다.
  - 미검증 무호흡 후보는 DEGRADED이며, `apnea_verified=true`인 별도 검증 입력만 응급으로 승격한다.
- [x] 핵심 단위/재생 테스트 18개 통과.
  - 명령: `python3 -m unittest tests/test_mr60_esp_adapter.py tests/test_risk_rules.py tests/test_mmwave_stream_adapter.py -v`.
  - 12/15/20rpm 유효 로그 재생 중앙값은 각 목표 대비 1rpm 이내였다.
- [x] 전체 팀 테스트에서 변경된 안전 계약과 충돌하는 기존 시험을 정리하고 재검증했다(80 PASS, 2 SKIP).
- [x] ESP WARMUP/VALID/UNKNOWN/FAULT 텔레메트리와 재현 가능한 config hash를 구현·빌드했다.
- [x] 유효 원본 manifest·재현 절차·통합 문서를 완성했다.
- [ ] 실제 빈 공간/정지 인체 30분 검증은 장비 연결 상태에서 별도 실행한다.

### 2026-07-29 구현·재현 검증 완료

- [x] ESP `safenest-mr60-esp/1.1.0` 상태 머신, raw/stable 텔레메트리, config SHA-256을 구현했다.
- [x] PlatformIO 빌드 성공: espressif32 7.0.1, Arduino-ESP32 3.20017.241212, RAM 6.7%, Flash 20.3%.
- [x] 유효 원본 6개만 선별한 SHA-256 manifest와 생성/검증 스크립트를 추가했다.
- [x] ESP JSONL→Pi 표준 패킷 CLI를 실측 15rpm 로그 끝까지 재생해 VALID/14.85rpm 출력을 확인했다.
- [x] LiteRT 2.1.6 임시 환경에서 팀 전체 테스트 80개 통과, 원본 Thermal NPZ 부재 테스트 2개 skip.
- [x] 최종 상태·결과·제약·다음 행동을 `MMWAVE_TUNING_REPORT_2026-07-29.md`에 기록했다.
- [ ] 현재 `/dev/cu.usb*`가 없어 새 ESP 펌웨어 업로드 및 30분 물리 검증은 BLOCKED.

### 다음 세션 재작업 방지

- [x] 다음 세션의 유일한 실행 기준을 `MMWAVE_NEXT_SESSION_CHECKLIST.md`로 작성했다.
- [x] 완료된 5분 기준선, 12/15/20rpm, 기존 진입·퇴장 20회, 필터 비교는 재수집 금지로 명시했다.
- [x] USB 확인→ESP 1.1.0 업로드→빈 공간 30분→정지 1인 30분→거리 4종→진입·퇴장 20회→Apple Watch 순서를 고정했다.
- [x] 각 단계의 명령, 파일명, 통과·중단 기준과 두 번 실패 시 대응을 기록했다.
- [ ] 실제 실행은 ESP USB 연결 후 체크리스트 A단계부터 시작한다.

### 2026-08-01 하드웨어 재연결 및 체크리스트 A·B단계 통과

- [x] 보드 오연결 1회 확인 후 정정했다.
  - 처음 연결된 장치는 `/dev/cu.usbmodem101`, VID:PID `303A:1001`, ESP32-C6FH4 (QFN32) rev v0.2였다.
  - 현재 펌웨어는 이 칩에서 빌드되지 않는다. `board=esp32dev`, `HardwareSerial radarSerial(2)`(C6는 HP UART 0·1뿐), 네이티브 USB CDC 미설정 세 가지가 동시에 걸린다.
  - 보드를 C6로 옮기려면 펌웨어 포팅과 `kConfigSha256` 갱신이 선행되어야 하므로 원래 WROOM-32으로 되돌렸다. 코드는 수정하지 않았다.
- [x] A단계 통과. 포트 `/dev/cu.usbserial-10` (CH340 `1A86:7523`), 칩 ESP32-D0WD-V3 rev v3.1 Dual Core 240MHz, MAC `cc:7b:5c:f2:1f:ec`, 점유 프로세스 없음.
- [x] B단계 통과. `pio run` 성공(espressif32 7.0.1, RAM 6.7%, Flash 20.3%), `pio run -t upload` 해시 검증 통과.
  - 15초 헬스체크 원본: `firmware/esp_wroom32_mr60_monitor/logs/final/2026-08-01_healthcheck_v110_15s.jsonl`.
  - `firmware_version=safenest-mr60-esp/1.1.0`, `config_hash=db2e2b0b87c093531b7312d09925d987d089c6cb344e166a094b2f41af64f0b2`로 기준과 일치.
  - 150 레코드, `seq` 결손 0, `checksum_errors`/`parse_errors` 증가 0, UART 프레임 15초에 1,128개(75fps).
  - `sensor_state`는 150개 전부 `WARMUP`, `error_code=TARGET_WARMUP`. `kWarmupMs=60000` 설계대로이며 FAULT 아님.
- [ ] C단계 전 확인 필요. 헬스체크 15초 내내 `human_detected_raw=true`였고 거리는 45.92cm(115샘플)와 51.66cm(35샘플) 두 값만 나왔다. 센서 정면 약 0.46~0.52m에 사람 또는 정지 반사체가 있었다는 뜻이므로, 빈 공간 30분을 시작하기 전에 감지 원뿔을 반드시 비워야 한다.

### 2026-08-01 mmWave 스키마 1.2 및 CSV 배치 v2

#### 작업 체크리스트

- [x] ESP `breath_phase` 30초 원형 창과 영교차+15% 히스테리시스 호흡수 구현
  - 위상 표준편차 0.2 미만은 `BREATH_PHASE_LOW_AMPLITUDE/DEGRADED`로 두고 `breath_rate_filtered=null`을 출력한다.
  - 거리 30초 창 `std=0`과 심박신호 무효가 동시에 성립할 때만 `LOCK_LOSS_FREEZE/DEGRADED`로 둔다.
  - vendor `breath_rate_raw`는 보존하되 `breath_rate_raw_trusted=false`, 심박은 `vital_presence_detected` 단방향 증거로 명시했다.
- [x] 텔레메트리 스키마 1.2, ESP 펌웨어 1.2.0 및 설정 SHA-256 갱신
  - 설정 SHA-256: `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834`.
  - PlatformIO 빌드 성공: RAM 9.9%(32,356B), Flash 20.5%(268,765B).
- [x] CSV 변환기에 반복 가능한 `--matrix-jsonl`, `--breath-jsonl` 입력 추가
  - cue와 ESP 시계는 변환하지 않고 파일 기록 순서에서 `stage=measurement` 범위를 선택한다.
  - 11개 열 순서, 원본 `breath_phase`, 실측 timestamp, 세션 분리 규칙을 유지한다.
- [x] 한준우 전달 배치 v2 생성
  - 위치: `firmware/esp_wroom32_mr60_monitor/csv/2026-07-26_han_junwoo_delivery_v2/`.
  - NORMAL_D06/D09/D12/D15 4세션, 호흡 성공·실패 사례 5세션, 총 9개 CSV와 원본 JSONL 사본을 포함한다.
  - `manifest.json`에 원본·사본·CSV SHA-256, 세션 진단, 용도 해석을 기록하고 `DELIVERY_NOTES.md`에 팀 전달 주의사항을 정리했다.
- [x] 2026-07-28 호흡 로그 중복 판정
  - 12rpm explicit attempt03은 30초 영교차 평균 12.36rpm, ±2rpm 99.3%로 기존 실제 6rpm 사고 로그를 대체하는 유효 기준이다.
  - 15rpm explicit full v3은 평균 15.25rpm, ±2rpm 100%로 07-26 성공본과 동등하다. 배치 중복을 피하려고 기존 07-26 성공본 하나만 포함했다.
  - 20rpm explicit full v2는 평균 17.99rpm, ±2rpm 51.7%라 유효 대체본이 아니다. 07-26 deep 성공본(20.17rpm, 100%)을 기준으로 유지한다.
- [x] 스키마 1.2 실제 업로드 및 75초 통신·스키마 헬스체크
  - ESP32-D0WD-V3 rev3.1에 업로드했고 각 플래시 구간의 해시 검증이 통과했다. MR60 센서 펌웨어는 변경하지 않았다.
  - 원본: `logs/final/2026-08-01_healthcheck_v120_75s.jsonl`, SHA-256 `eb4c57a16ea00d6b4314364f298cac2420a0f9cf3023eed15d02dcdd95835382`.
  - 749패킷/74.848초, schema 1.2·ESP 1.2.0·config hash 일치, checksum/parse 오류 증가 0.
  - 상태는 WARMUP 288, VALID 266, DEGRADED 195였다. DEGRADED 전부가 `BREATH_PHASE_LOW_AMPLITUDE`였고 freeze 오탐은 0건이다.
  - 필터 유효 517패킷의 중앙값은 14.94rpm이었다. 이 캡처는 통신·스키마 검증이며 피험자 기준 호흡이 없으므로 정확도 KPI 자료로 사용하지 않는다.
- [x] Pi mmWave 어댑터 schema 1.2 회귀 테스트
  - 전역 Python에는 패키지를 설치하지 않았다. `/opt/anaconda3`의 기존 numpy 1.26.4/pandas 2.2.2를 사용하는 `/private/tmp/safenest-pi-regression-venv` 임시 환경에서 실행했다.
  - 명령: `python -m unittest tests/test_mr60_esp_adapter.py tests/test_mmwave_stream_adapter.py tests/test_mmwave_input_adapter.py -v`.
  - 결과: 13개 테스트 전부 통과. `0/null`·부재·NaN/Inf·timestamp 중복/역행·gap·stale 안전 게이트와 실제 페이싱 로그 재생이 정상이며, schema 1.2 호환을 위한 추가 Pi 코드 수정은 필요 없었다.
- [x] schema 1.2 빈 공간 설치 게이트 및 30분 연속 검증
  - 60초 사전 확인은 600/600패킷에서 raw/stable presence=false, 생체 양수값·재부팅·checksum/parse 오류 0으로 통과했다.
  - 사전 로그: `logs/final/2026-08-01_empty_v120_preflight_60s.jsonl`, SHA-256 `2f3d0b6657381f697f50dab396cb0dfb8a44354f6e86c30ab0ccde5ee7a95dfd`.
  - 본 로그: `logs/final/2026-08-01_empty_v120_30min.jsonl`, SHA-256 `32ee3ae455ccf46029840f71268fdda37a88a963eed7ac7c7f9dfb269d00b3b2`.
  - 17,995패킷/1,799.781초, 9.998Hz, UART 108,416프레임/60.238fps, seq 결손·timestamp 중복/역행·JSON 오류 0.
  - raw/stable presence=true, `vital_presence_detected`, raw/filtered 생체 유효, freeze 오탐이 모두 0건이었다.
  - ESP reboot·checksum/parse 증가·UART/checksum 불량도 모두 0이고, 전 패킷이 `UNKNOWN/PRESENCE_NOT_DETECTED`로 안전하게 처리됐다.
- [x] schema 1.2 정지 1인 31분 측정 — 재실 KPI 미통과
  - 조건: 센서 정면 약 0.9m 착석, 자연호흡, 총 1,860초 수집 후 첫 60초를 제외해 분석했다.
  - 원본: `logs/final/2026-08-01_occupied_d09_v120_31min.jsonl`, SHA-256 `bcd947ed341944065fe47ca21b7cfedd30a37064eea78b5c496ef1c190597f0d`.
  - 분석: `analysis/final/2026-08-01_occupied_d09_v120_after60s_summary.json`, SHA-256 `4664117267d2c51a74f5eaff974d695e64716b425ea17f1f909ab5186a0b0f29`.
  - 분석 17,988패킷/1,799.839초, ESP reboot·checksum/parse 증가·UART/checksum 불량 0으로 통신 안정성은 통과했다.
  - stable presence 감지율은 84.84%(15,261/17,988)로 목표 95%에 미달했다. 해제 구간은 9개, 총 271.858초이며 최장 구간은 176.041초였다.
  - filtered breath 유효률 29.76%, 중앙값 15.66rpm, 표준편차 2.51rpm이었다. 저진폭 DEGRADED는 43.22%, 재실 재확립 WARMUP은 24.39%, 부재 UNKNOWN은 15.16%였다.
  - `freeze_detected=true`는 165패킷, `LOCK_LOSS_FREEZE` 상태는 5패킷이었다. 신호 해제와 재확립이 반복됐으므로 정상 1인 연속 검증으로 PASS 처리하지 않는다.
  - 원본 18,589줄 중 9,000번째 줄 1개가 `breath_window_ready` 뒤 일부 바이트가 누락된 불완전 JSON이다. 원본은 수정하지 않고 분석기가 1개 invalid line으로 제외한 사실을 함께 기록한다.
  - 같은 설치·방법으로 즉시 재측정하지 않는다. 다음 단계는 재실 해제 9구간과 위상 진폭 저하의 시간 정렬, 설치 각도·가슴 중심 높이·실측 거리 확인, USB 출력 1줄 손실 원인 진단이다.
- [x] 센서 위치 조정 후 정지 1인 3분 게이트 — 미통과
  - 가슴 앞 물체를 치우고 팔짱을 풀어 손을 허벅지 위에 둔 조건에서 센서를 더 가까이 정렬해 180초 측정했다.
  - 원본: `logs/final/2026-08-01_occupied_d09_v120_positioncheck_180s.jsonl`, SHA-256 `60e5c2515a161387cf3ef934a5f47532653fc2e02284a127ff2c5b6652ad8b2c`.
  - 전체 1,799패킷/179.887초의 stable presence는 90.77%, 첫 60초 제외 1,199패킷에서는 86.16%였다.
  - 재실 해제는 15.902초와 0.5초 두 구간이었고, 전체 filtered breath 유효률 13.67%, 저진폭 42.41%였다.
  - 첫 60초 제외 센서 거리 중앙값은 74.62cm로 권장 범위였지만 재실 95% 게이트를 통과하지 못했다. reboot·checksum/parse 오류·freeze는 0이었다.
  - 거리 조정만으로 해결되지 않았으므로 같은 방식으로 반복하지 않는다. 센서 안테나의 상하 각도·가슴 중심 정렬 및 MR60 vendor presence의 정지 인체 해제 한계를 분리 진단한다.
- [x] 높이·각도 정렬 후 정지 1인 최종 3분 게이트 — 재실 통과, 호흡 미통과
  - 안테나 면을 가슴 중앙과 같은 높이에 두고 위·아래/좌·우 기울기를 제거했으며, 약 75cm와 가슴 앞 무장애 조건을 유지했다.
  - 원본: `logs/final/2026-08-01_occupied_d09_v120_positioncheck_attempt02_180s.jsonl`, SHA-256 `fd061477c81702adffc50b06253de5ab0c362474fdde2241b8f7d695f9e95144`.
  - 전체 1,798패킷/179.804초와 첫 60초 제외 1,198패킷 모두 raw/stable presence 100%, vital presence 100%, reboot·checksum/parse 오류·freeze 0이었다.
  - 첫 60초 제외 거리 중앙값 74.62cm로 재실 95% 게이트는 통과했다.
  - 전체 filtered breath 유효률은 9.57%, 저진폭 `BREATH_PHASE_LOW_AMPLITUDE`는 90.43%였다. 필터 유효 구간 중앙값은 14.62rpm이지만 유효률이 너무 낮아 호흡 게이트는 미통과다.
  - 높이·각도 조정으로 재실은 개선됐지만 위상 결합은 악화됐다. 이 상태로 31분을 반복하지 않고 재실 100% 정렬을 유지한 채 흉부 위상 진폭을 확보할 설치 축을 별도로 찾아야 한다.
- [x] 사용자 재배치 상태 정지 1인 1분 확인 — 재실·호흡 통과
  - 원본: `logs/final/2026-08-01_occupied_d09_v120_positioncheck_attempt03_60s.jsonl`, SHA-256 `13bc4ebc2468e065f42601df75fd3e6ee4286189e7899ca537493eaeba46cb5d`.
  - 599패킷/59.887초에서 raw/stable/vital presence와 filtered breath 유효가 모두 599/599(100%)였다.
  - 전 패킷 `VALID`, 저진폭·freeze·reboot·checksum/parse 오류·불완전 JSON은 모두 0건이었다.
  - 센서 거리 중앙값은 97.58cm였고 filtered breath는 15.20~20.87rpm, 평균 17.88rpm이었다.
  - 직전 75cm 조건보다 위상 결합이 뚜렷하게 개선됐다. 다만 1분 단기 게이트이므로 장기 KPI 통과 근거로 확대 해석하지 않고, 다음 장기 측정 전 현재 설치 상태를 유지한다.
- [x] 사용자 재배치 상태 정지 1인 31분 재검증 — 재실 통과, 호흡 지속성 미통과
  - 원본: `logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl`, SHA-256 `7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34`.
  - 첫 60초 제외 분석: `analysis/final/2026-08-01_occupied_d09_v120_31min_attempt02_after60s_summary.json`, SHA-256 `b8c6fb33436bd2999861b591607c99a8435a3c958a37042f84adc06789b10942`.
  - 분석 17,974패킷/1,799.751초에서 stable presence는 98.77%(17,753/17,974)로 95% 기준을 통과했다. 부재는 22.004초 한 구간이었다.
  - filtered breath 유효률은 21.58%, 저진폭은 58.92%, filtered breath 중앙값/평균은 17.23/16.79rpm이었다. 따라서 호흡 지속성은 미통과다.
  - 첫 25분의 5분 구간별 stable presence는 첫 구간 92.62%, 이후 네 구간 100%였고 거리 중앙값은 모두 97.58cm였다. 마지막 5분에는 거리 중앙값이 166.46cm로 바뀌고 vital presence 4.10%, freeze 85.59%가 되어 장기 저하가 집중됐다.
  - reboot·checksum/parse 오류·불완전 JSON은 0이었다. 재실 KPI는 통과했지만 마지막 5분 거리 변화와 전반적인 저진폭 때문에 전체 장기 검증 PASS로 처리하지 않는다.
  - 사용자 요청에 따라 마지막 5분을 제외한 60~1,560초의 가운데 25분도 별도 재분석했다. `analysis/final/2026-08-01_occupied_d09_v120_31min_attempt02_middle25min_summary.json`에 결과를 보존했다.
  - 가운데 25분은 14,976패킷/1,499.828초, stable/vital presence 98.52%(14,755/14,976), 거리 중앙값 97.58cm(86.10~103.32cm), freeze·reboot·checksum/parse 오류 0으로 재실 기준은 통과했다.
  - 그러나 filtered breath 유효률은 25.90%(3,879/14,976), 저진폭은 69.95%(10,476/14,976)여서 마지막 5분을 제외해도 호흡 지속성 및 전체 판정은 미통과다. 마지막 거리 점프는 호흡 저진폭의 유일한 원인이 아니다.
- [x] 2026-08-01 MR60 전체 완료 상태 재감사
  - PlatformIO 빌드를 재실행해 RAM 32,356B(9.9%), Flash 268,765B(20.5%)로 통과했다. Python 수집·분석·CSV 도구 `py_compile`도 통과했다.
  - schema 1.2 Pi 어댑터·stream/input 안전 게이트·manifest 단위 테스트 15개를 재실행해 모두 통과했다.
  - CSV delivery v2의 원본 9개·사본 9개·CSV 9개 중 manifest가 관리하는 18개 항목의 SHA-256이 모두 일치했다.
  - 거리 D06/D09/D12/D15 원본 4개와 진입·퇴장 20회 원본의 SHA-256을 재검증했다. 진입·퇴장 분석기도 다시 실행해 기존 평균 1.134초, 퇴장 평균 15.491초 결과를 재현했다.
  - 완료 판정: firmware/schema/통신, 빈 공간 30분, 정지 인체 재실 30분, 거리 4종, 진입·퇴장 20회, 페이싱 phase 12/15/20rpm, Pi 회귀, CSV 전달은 완료되어 재수집하지 않는다.
  - 제한 판정: 자연호흡 장기 filtered 유효률은 FAIL, 심박 정확도와 무호흡은 기준기기·안전한 정답 데이터가 없어 UNVERIFIED다. 이 값을 정상/위험의 단독 근거로 사용하지 않는다.
  - 최신 증거 목록과 SHA-256은 `analysis/final/2026-08-01_mr60_final_validation_manifest.json`에 고정했다.
  - 남은 필수 작업은 팀 통합 노드에서 실제 ESP USB JSONL을 입력해 end-to-end 경로를 확인하는 것과 현재 최종 검증 산출물을 커밋·푸시하는 것이다.
  - 후속 전수 파일 감사에서 `logs/` 아래 JSONL 68개, 총 154,413줄을 모두 파싱했다. 빈 파일은 없고 파싱 불가 줄은 2개뿐이다: 초기 `2026-07-13_empty_desk_collector_v1_30s.jsonl` 1행은 파일 중간에서 시작해 여는 `{`가 없는 부분 줄이고, 실패본 `2026-08-01_occupied_d09_v120_31min.jsonl` 9,000행은 이미 기록된 직렬 1줄 손실이다. 두 파일 모두 원본을 수정하지 않으며 채택 통계에서 해당 줄을 제외한다.
  - `analysis/` 및 CSV 폴더의 JSON 46개는 전부 유효했다. CSV delivery v2는 원본·사본 18개와 CSV 9개, 총 manifest 항목 27개의 해시 및 CSV 9개 행 수가 모두 일치했다.

#### 파일명 날짜 주의

`2026-07-26_heartrate_ref_applewatch*.jsonl`과 `2026-07-26_breath_paced_*.jsonl` 중
인수인계에서 지정한 일부 파일은 실제 2026-08-01 캡처다. 기존 분석·매니페스트 참조를
깨지 않도록 원본 파일명은 변경하지 않는다.
# 2026-08-01 MR60 Phase 2 USB JSONL E2E 통합

## 목표와 성공 기준

실제 ESP-WROOM-32 schema 1.2 JSONL을 Pi 통합 노드까지 안전하게 전달하고, 불일치·결측·부재·stale·중복/역행을 숨기지 않으며 최종 게이트 후 관련 변경만 커밋·푸시한다.

## 생활 체크리스트

- [x] 1. 기준 브랜치·작업트리·선행 커밋·관련 코드 확인
  - 결과: 작업트리는 깨끗하고 `codex/mmwave-phase-integration` HEAD/origin은 `454de765`; 기준 `41af82b` 이후 하드웨어 증거(`c643aba`)와 전수 감사(`454de76`)가 이미 원격 반영됨.
- [x] 2. E2E 요구 조건별 보장/누락 추적 및 원본 로그 해시 기준 고정
  - 결과: 핵심 원본 4개 SHA-256이 handoff/manifest와 일치. strict provenance와 invalid-packet integration buffer reset이 누락된 핵심 계약으로 확정됨.
- [x] 3. 누락 통합 로직과 테스트 최소 구현
  - 결과: schema/firmware/ESP config hash strict 검사, timeout stale packet, 실제 통합 엔진 bridge, 모든 invalid mmWave 입력의 통합 buffer 초기화 및 안전 metadata를 구현. 표적 14 tests PASS.
- [x] 4. 포트 단독 점유 확인 후 실제 USB 장치 E2E 검증
  - 결과: `/dev/cu.usbserial-10` 점유 없음 확인 후 실제 schema 1.2 스트림 수신. 첫 부분 줄은 `MMWAVE_JSON_INVALID`로 비은폐, 이후 firmware/config hash 일치와 표준 패킷 변환 확인. 60초 끝에도 자연호흡 창은 `MMWAVE_WINDOW_NOT_READY`(10 samples)로 mmWave DEGRADED/buffer 0 유지; 동일 물리조건 반복 금지. 합성 15rpm E2E에서 VALID와 통합 buffer 수신을 별도 PASS.
- [x] 5. 최종 게이트(`git diff --check`, build, compile, unittest 4파일)
  - 결과: diff-check/py_compile PASS, PlatformIO RAM 32,356B(9.9%)·Flash 268,765B(20.5%), 지정 4파일 unittest 19 PASS. 임시 venv의 TFLite runtime 부재는 기존 fallback 경고이며 표적 계약 테스트는 PASS.
- [x] 6. 원본 해시·diff 범위 재검증 후 관련 변경 커밋·푸시
  - 결과: 원본 logs/CSV 변경 0, 핵심 원본 4개 SHA-256 일치. 관련 10파일만 `829f0f9`로 커밋해 `origin/codex/mmwave-phase-integration` push 성공.
- [x] 7. 헤더 전달용 5절 통합 보고
  - 결과: 완료/제한/남은 작업/검증 증거/커밋·푸시와 핵심 명령 출력 요지를 최종 회신에 정리.

## 현재 상태와 결정

- `run_mr60_serial_adapter.py`는 USB/replay JSONL을 `mmwave_mr60` stdout으로 변환하지만 `SafeNestRiskEngine` 소비 경로와 직접 연결되지 않는다.
- `MR60ESPAdapter`는 sequence/UART/presence/distance/phase 안전 게이트는 구현했으나 ESP schema/firmware/config hash 기대값 검증이 없어 불일치를 현재 숨긴다.
- 최소 변경 원칙으로 ESP 원본 스키마·임계값은 유지하고, 어댑터 provenance 검증과 통합 엔진 bridge/API 및 회귀 테스트만 추가한다.

## 파일/결정 기억

- 수정: `src/sensors/mmwave/mr60_esp_adapter.py`, `src/sensors/mmwave/run_mr60_serial_adapter.py`, `src/integrated_node/run_mr60_usb_node.py`, `src/integrated_node/safenest_risk_engine.py`, 관련 config/tests/docs와 본 진행 기록.
- 원본 JSONL은 수정·이동·이름 변경하지 않는다. 시작 해시는 최종 manifest와 핸드오프의 고정 SHA-256을 기준으로 재검증한다.

# 2026-08-01 MR60 Phase 2B Apple Watch 심박 탐색 검증

## 목표와 해석 경계

현재 ESP 1.2.0에서 MR60 vendor 심박과 Apple Watch 표시 심박을 동시에 기록해 반복성·절대오차·추종성을 탐색한다. Apple Watch는 의료용 기준기가 아니며, 결과와 관계없이 `heart_verified=false`를 유지하고 위험 판정의 단독 근거로 사용하지 않는다.

## 사전등록 프로토콜

- 정정 이력: 저장소에서 이전 6개 기준 원문을 찾지 못했다는 이유로 안정 상태 5분을 두 번 반복하는 안을 잠시 기록했으나, 이는 사용자와 앞서 합의한 회복 추종 프로토콜을 잘못 덮어쓴 것이므로 측정 전에 철회했다.
- S1 안정 기준선: 기존 설치 조건(흉부 정면 약 0.9m), 상체 고정·안정 상태 300초. 30초마다 신호 직후 Apple Watch 표시값 10개 기록.
- 전이: 사용자가 평소 무리 없이 하는 가벼운 활동으로 Watch 심박을 기준선보다 올린다. 활동 중 MR60 정확도는 평가하지 않는다.
- S2 회복 추종: 활동 직후 같은 위치에 앉아 상체를 고정하고 300초 동안 회복한다. 시작 시점과 이후 30초마다 Watch 표시값을 기록해 MR60이 하강 방향과 시간 변화를 추종하는지 평가한다.
- S3: 심박 상승 폭이 부족하거나 S1/S2 대조점·통신 품질이 판정 불가일 때만 1회 추가한다.
- 숨참기·과호흡은 하지 않는다. 센서 firmware와 ESP 임계값도 변경하지 않는다. 활동에 불편이 있으면 즉시 중단하고 해당 세션은 무효로 보존한다.

## 사전등록 6개 판정 게이트

1. 세션 완주: 295초 이상, sensor record 2,950개 이상, Watch 기준점 10개.
2. 전송 무결성: ESP reboot 0, checksum/parse error 증가 0, sequence 결손률 0.1% 이하.
3. 재실 안정성: `human_detected_stable=true` 95% 이상.
4. 심박 가용성: `heart_raw_valid=true` 90% 이상, ±5초 대조 가능 기준점 9/10 이상.
5. 절대오차: paired MAE 5bpm 이하이며 |error|≤5bpm 비율 80% 이상.
6. 회복 추종: S2에서 Apple Watch와 MR60의 전체 하강 방향이 일치하고 Pearson r 0.5 이상, max |error| 10bpm 이하. 시간 지연과 각 구간 기울기는 함께 보고한다.

최종 판정은 각 세션의 6개 게이트를 개별 PASS/FAIL로 보고한다. 오프셋 보정 결과는 탐색값으로만 병기하고 채택 판정에는 raw 값을 사용한다.

## 생활 체크리스트

- [x] 기존 Apple Watch 로그·분석 도구 확인
  - 결과: schema 1.1의 5분 로그 2개 존재. 1차 MAE 14.50bpm, 2차 ±15초 r=-0.35·raw MAE 7.40bpm으로 기존 심박 절대값 폐기 근거이며 ESP 1.2.0 검증을 대체하지 않음.
- [x] S1 안정 기준선→S2 활동 후 회복 추종(+조건부 S3)과 6개 판정 기준 사전등록
  - 결과: 안정 상태 반복안은 사용자 지적에 따라 측정 전에 철회하고 기존 회복 하강 추종 합의를 복원함.
- [x] USB 포트·설치·Watch 기록 준비 확인
  - 결과: 15초 preflight 150 records, stable presence 100%, 거리 중앙값 91.84cm, firmware 1.2.0/config hash 일치, reboot/checksum/parse 오류 0, heart positive 100%.
- [x] S1 캡처와 Watch 기준값 기록·분석
  - 캡처: 301.813초, 3,013 records, cue 10/10, invalid JSON/reboot/checksum/parse 0, sequence 결손 0, stable presence 100%, heart valid 100%.
  - Apple Watch 기준값: 68/71/75/70/75/73/77/71/81/71bpm. 각 cue ±5초 MR60 중앙값: 86/88/84/83/64/89/96/96/109/81bpm.
  - 판정: gate 1~4 PASS, gate 5 FAIL. paired 10/10, raw MAE 16.6bpm, bias +14.4bpm, max |error| 28bpm, |error|≤5bpm 0/10, Pearson r=0.413. gate 6은 S2 전까지 N/A.
  - 결론: 안정 상태 심박 절대값 정확도 FAIL. `heart_verified=false` 유지하며 위험도·심정지·사람 없음의 단독 근거로 사용하지 않음.
  - 원본 SHA-256: `9bf5fbfedb22cfcf17590cd37c6fd2313eddb9af0c48c9a22905d49726841e40` (`logs/kpi/2026-08-01_heartrate_watch_s1_v120_300s.jsonl`).
  - host receipt SHA-256: `614db96d9d8acd113dfa38af4111017a2e17c9cd098a43a200de930abdc95e6d`; watch prompt SHA-256: `b593054c3f7a5006c3f01aeb389ddbdd90ba4c8106b5c694d8d7e9598f9958bb`.
- [x] S2 캡처와 Watch 기준값 기록·분석
  - 결과: 7점 단축 S2에서 Watch-vendor MAE 20.43bpm, r=−0.1963, max |error| 67bpm으로 recovery gate FAIL.
- [x] 필요 시 S3 실행 여부 판정
  - 결과: S2는 단축됐지만 H1 사전등록 회귀와 직접 스펙트럼이 모두 명확히 FAIL하여 판정을 바꾸기 위한 S3는 실시하지 않는다.
- [x] 결과·원본 SHA-256·제한·`heart_verified=false` 기록
  - 결과: Phase 2C aggregate manifest 24항목 해시 PASS, 본/attempt02 원본 해시와 185.598초 제한 기록, `heart_verified=false` 유지.

# 2026-08-01 MR60 Phase 2C-HR 심박 측대파 가설 검정

## 목표와 성공 기준

Phase 2B S1의 확정 FAIL(MAE 16.6bpm, bias +14.4bpm)을 뒤집지 않고, 자체 phase 호흡 추정과 raw phase 스펙트럼으로 `f_heart ± f_resp`, `±2f_resp` 측대파 가설을 직접 검정한다. Stage 1은 신규 측정·시리얼 포트 오픈 없이 완료하고, S2는 별도 사용자 승인 후 홀드아웃으로만 사용한다.

## 사전등록 기준

- H1 지지: S1+S2 통합 오차-vs-호흡수 회귀 기울기 0.7~1.3, Pearson r≥0.6.
- 직접 증거: 선택 피크 및 Watch 기본파 예측 위치와 `±f_resp`, `±2f_resp` 위치의 스펙트럼 강도비가 부호·차수 가설과 일치.
- +25/+28bpm은 `+2f_resp`, −11bpm은 `−f_resp` 근방 매칭 여부를 별도 판정.
- 해결: S1로만 파라미터를 고정한 notch의 S2 홀드아웃 MAE≤5 해결, ≤8 부분 해결, 그 외 미해결.
- notch가 기존 자체 호흡 유효률을 조금이라도 낮추면 해당 파라미터 기각.
- 어떤 결과에도 `heart_verified=false`; vendor 심박·호흡 고정 오프셋 금지, 결측 보간·전방채움 금지.

## 생활 체크리스트

- [x] Phase 2C-HR 목표·가설·반증 조건·사전등록 기준 수용
- [x] Stage 1 입력·시간 정렬·phase source 계약 고정
  - 결과: host receipt/prompt cue 정렬, 직전 30초 causal window, `breath_phase` 자체 FFT, `total_phase` raw source, `heart_phase` 보조 source로 고정.
- [x] cue별 자체 호흡 추정·회귀·제외율·이상치 매칭
  - 결과: 10/10 valid, 제외율 0%. error-vs-resp slope 0.340, r=0.117로 S1 예비 기준 FAIL. vendor 오차 sideband 3bpm 매칭 5/10.
- [x] raw spectrum 대표 구간 3개 이상과 측대파 강도비 산출
  - 결과: cue 3(+9), cue 5(−11), cue 9(+28) PNG 생성. vendor 오차 차수와 raw 지배피크 차수 동시 일치 0/10.
- [x] 심박 오염과 호흡 강도/유효성 시간 상관 분석
  - 결과: |오차|-breath std r=−0.147, sideband/base-breath std r=+0.323, sideband/base-breath peak ratio r=+0.116, firmware breath-valid rate와 r=−0.378. 강한 결합 증거 없음.
- [x] Stage 1 산출물·manifest·문서·테스트 검증
  - 결과: `analysis/hr_sideband/`에 scatter, coupling, 대표 spectrum cue 3/5/9, CSV, JSON, Stage 1 보고서와 별도 manifest 생성. manifest 전 항목 SHA-256 일치, `py_compile`/`git diff --check` PASS, 지정 4파일 unittest 19 PASS, 기존 핵심 원본 4개 SHA-256 불변.
- [x] Stage 1 결론 후 S2 사용자 절차 안내 및 사용자 실행 승인
  - 결과: 가벼운 활동 후 Watch 125bpm에서 시작을 요청받았으며, 이후에는 추가 운동 없이 자연 회복하도록 안내했다.
- [x] S2 입실 기준점 및 단축 회복구간 캡처
  - 결과: 사용자가 17:39:00 KST에 입실과 Watch 135bpm을 알렸고, 인접 receipt `seq=177721`, `host_monotonic_ns=603398075344583`와 함께 t=0으로 고정했다. 본 캡처 4,815패킷 완료 후 attempt02 1,071패킷을 추가 저장했으며 사용자 요청으로 인터럽트해 음성·시리얼을 종료했다. 포트 점유 없음 확인.
- [x] S2 종료 후 원본·receipt·prompt 무결성 및 패킷 품질 검증
  - 결과: 본 캡처 raw/receipt/prompt 4,815/4,815/16행, attempt02 1,071/1,071/3행. attempt02와 모든 receipt/prompt는 전 행 표준 JSON PASS. 본 raw는 입실 이전 `seq=175386` 한 행(607행)이 UART 문자열 결손으로 invalid(1/4,815, 0.0208%)이며 원본 불변 유지; 입실 `seq=177721` 이후 본 캡처 구간은 영향 없음. 본 캡처 끝 `seq=179594`→attempt02 시작 `seq=179597` 사이 핸드오프 2패킷 공백을 제한으로 기록한다. 원본 SHA-256은 본 캡처 `c7518086111a4d9c6aef1b6ad517115f3cbb491f368364e07abdf6bb41a0dfc6`, attempt02 `5036ea6200dfd1fd291567ef226b7247da189888a572d76690b061900e2083cb`.
- [x] S2 Watch 기준값 7개 확정 및 시간 정렬
  - 결과: `135, 100, 92, 92, 94, 86, 91`을 entry t=0과 기존 prompt 11~16에 정렬했다. 첫 post-entry prompt는 5.606초로 너무 빨라 사전 안내대로 제외했다. 유효 관찰 길이는 185.598초로 계획한 8분보다 짧으므로 단축 S2로 제한을 명시한다.
- [x] 단축 S2를 이용한 S1+S2 통합 가설 판정
  - 결과: S1+S2 n=16, error-vs-self-resp slope=0.3625, r=0.1191로 사전등록 기준 둘 다 FAIL. S2 직접 스펙트럼 동일 차수 일치 0/6. H1 기각.
- [x] S2 회복 추종 및 시간동기 감사
  - 결과: Watch 135→91(−44), vendor 68→90(+22), MAE 20.43, bias −14.43, max |error| 67, r=−0.1963으로 Phase 2B recovery gate FAIL. ±10초 스캔 최고점이 +10초 경계(r=0.4363)여서 단일 내부 피크 조건 불충족, 보정 미적용.
- [x] H1 지지 시에만 notch 구현·S2 1회 홀드아웃 평가
  - 결과: H1 기각으로 Stage 3 notch 구현·평가 금지. vendor 고정 오프셋/스케일 보정도 적용하지 않음.
- [x] `heart_verified=false` 유지 및 단축 S2 제한 문서화
  - 결과: `analysis/hr_sideband/STAGE2_REPORT.md`에 185.598초 단축, 첫 점 회귀 제외, 원본 invalid 1행, Apple Watch 비의료 기준 제한을 명시.
- [x] Phase 2C-HR 최종 검증 게이트
  - 결과: `git diff --check` PASS, 새 분석기 3개 `py_compile` PASS, 지정 4파일 unittest 19 PASS, 기존 핵심 원본 4종 SHA-256 불변, aggregate manifest 24항목 해시 PASS.
- [x] 관련 변경만 커밋하고 `codex/mmwave-phase-integration` push
  - 결과: Phase 2B/2C 관련 45파일만 `770c4772d3613eba42ebaf3a1085dcd74c409b34`(`analysis: reject MR60 heart sideband hypothesis`)로 커밋해 origin push 완료. 본 체크리스트 상태는 후속 closure 커밋으로 기록한다.

## 결정 기억

- 직접 raw source는 MR60 `total_phase`; vendor가 분리한 `heart_phase`는 보조 비교로만 사용한다.
- 자체 호흡 추정은 `breath_phase`의 30초 causal window, 10Hz, 5~40rpm FFT, phase std≥0.05, gap≤0.5초 계약을 재사용한다.
- cue 정렬은 Phase 2B host monotonic receipt/prompt를 사용하며 각 cue 직전 30초 창을 분석한다.
- S1의 Watch 범위가 68~81bpm으로 좁으므로 S1 회귀는 예비 증거이며, H1 최종 기준은 사전등록대로 S1+S2 통합에서만 판정한다.

# 2026-08-03 MR60 R1 펌웨어 C++ ↔ Python 동치성 검증

하드웨어 캡처 전 선행 단계. 포팅 버그가 있으면 이후 캡처가 전부 무의미하므로 먼저 수행했다.
원본 로그는 읽기만 했고 수정·이동·이름 변경은 없다.

- 대상: `devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl`
  (SHA-256 `7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34`, schema 1.2 패킷 18,574개, 파싱 불가 0줄)
- 검증 도구(신규): `devices/mmwave/firmware/analysis_tools/r1_fw_python_equivalence.py`
  `src/main.cpp`의 `appendSample()`/`windowReady()`/`windowStddev()`/`breathStats()`를 표준 라이브러리만으로 재현하고,
  같은 시점 ESP 출력 `breath_phase_std`/`breath_rate_filtered`/`breath_filtered_valid`와 비교한다.
  파라미터는 `include/mmwave_config.h`와 동일(창 30,000ms, 용량 640, 게이팅 100ms, ready 허용 200ms,
  히스테리시스 0.15, 최소 std 0.2, 최소 영교차 2).

## 결론: C++ ↔ Python 알고리즘 포팅 버그 없음

| 비교 항목 | 전체 불일치 | phase 신선(age≤200ms) 구간 | 차이 분포 |
|---|---|---|---|
| `breath_window_ready` | 298 / 18,574 (1.604%) | — | replay 워밍업 아티팩트 |
| `breath_phase_std` | 3,626 / 18,276 (19.84%) | 790 / 15,393 (5.13%) | p50 0.00249, p99 0.00609, max 0.01605 |
| `breath_rate_filtered` | 2,275 / 3,879 (58.65%) | 동일 | p50 0.0328, p90 0.1182, p99 2.1985, max 6.657 rpm |
| `breath_filtered_valid` 게이트 판정 | 51 / 18,276 (0.279%) | 0.331% | — |

불일치 3건은 전부 원인이 특정되며 계산식 차이가 아니다.

1. `window_ready` 298건은 정확히 300패킷(30초)이다. 로그 시작 시점에 ESP 창은 이미 차 있었고
   replay는 창을 채우는 데 30초가 필요하다. 비교 아티팩트이며 실제 불일치가 아니다.
2. `breath_phase_std` 불일치의 대부분(14.7%p)은 26~30분 구간에 몰려 있다(분당 600건).
   이 구간은 phase 프레임이 두절돼 `phase_age_ms`가 최대 288,530ms까지 올라갔다.
   ESP는 새 샘플이 들어올 때만 창을 비우므로 std=0.13을 그대로 유지하는 반면,
   replay는 로그에 반복 기록된 마지막 값을 계속 넣어 std→0이 된다. 창 갱신 시점 차이다.
   phase 신선 구간만 보면 p99 0.00609로 ESP 출력 정밀도(소수 2자리, ±0.005) 수준이다.
3. `breath_rate_filtered`의 판정 기준 0.005 rpm은 ESP 출력 반올림 폭과 같아 변별력이 없다.
   실질 기준으로는 >0.5 rpm 155건(4.00%), >1.0 rpm 118건(3.04%)이다.
   이 꼬리는 전부 게이트 경계(esp_std≈0.20)에서 발생하며 원인은 로그의 `breath_phase`가
   소수 2자리로 양자화된 것이다. 진폭 0.20에서 히스테리시스 문턱은 0.15×0.20=0.030으로
   양자화 3단계뿐이라 영교차 개수가 1~2개씩 바뀐다.
   알고리즘을 고정한 채 입력 정밀도만 2자리→1자리로 낮춘 민감도 시험에서
   p50 0.067, p99 7.499, max 24.227 rpm(>1rpm 27.5%)이 흔들려 이 설명이 확인됐다.

## 부수 발견 — 잠재 결함 1건 (실제 발생 0건, 오늘 수정 보류)

`windowReady()`(`src/main.cpp:97`)는 phase 프레임이 288초 두절된 뒤에도 `true`를 유지한다.
`appendSample()`(`src/main.cpp:81`)이 새 샘플이 들어올 때만 오래된 샘플을 버리기 때문이다.
`phase_age_ms>30s`인데 `breath_window_ready=true`인 패킷이 2,585개 있었다.
또한 `filteredBreathValid`(`src/main.cpp:328`)는 phase 신선도를 검사하지 않는다.

이번 로그에서는 두절 직전 창의 std가 0.13(<0.2)이라 `breath_rate_filtered`가 null로 나가
실제 사고는 0건이다(`phase_age_ms>500` AND `breath_filtered_valid=true`인 패킷 0/18,574).
그러나 그 값이 0.2 이상이었다면 288초 묵은 호흡수를 유효값으로 내보냈을 것이므로
"0/null/NaN/timeout을 정상 호흡으로 변환 금지" 계약에 걸리는 잠재 결함이다.
오늘 펌웨어를 고치면 config 해시가 바뀌어 같은 설치·같은 펌웨어 비교가 깨지므로
캡처 세션 종료 후 별도 항목으로 처리한다.

## H1 해석에 미리 반영할 제약

로그의 `breath_phase` 정밀도가 소수 2자리이므로, 자연 대역(std 0.10~0.20)에서
Python 후처리 재현값은 3% 수준의 큰 꼬리를 갖는다.
따라서 H1의 1차 근거는 ESP가 직접 출력한 `breath_rate_filtered`로 하고,
Python 영교차 값은 교차검증 용도로만 사용한다.

## 세션 환경 메모

- USB 포트가 `/dev/cu.usbserial-10`에서 `/dev/cu.usbserial-110`으로 바뀌었다. 문서상 옛 값은 스테일이다.
- `lsof` 결과 포트 점유 프로세스 없음. venv pyserial 3.5 정상.
