# SafeNest MR60BHA2 최종 재개 프롬프트

아래 내용을 다음 Codex 작업에 그대로 붙여 넣어 사용한다.

---

너는 SafeNest 프로젝트의 MR60BHA2 mmWave 통합 담당 엔지니어다. 완료된 물리 시험을 다시 시키지 말고, 현재 저장소의 원본과 미커밋 변경을 보존한 채 남은 통합 작업만 끝내라.

## 목표와 완료 기준

목표는 이미 검증된 MR60 firmware/schema/물리 시험 결과를 유지하면서 팀 통합 노드의 실제 ESP USB JSONL 입력을 end-to-end로 확인하고, 필요한 최소 문서 변경을 검증·커밋·푸시하는 것이다.

완료 조건:

1. 팀 통합 노드가 실제 ESP-WROOM-32 USB JSONL을 받아 schema 1.2 패킷을 안전하게 처리한다.
2. `0/null/NaN/timeout/presence=false/gap`이 정상 호흡이나 무호흡으로 치환되지 않는다.
3. 심박은 `heart_verified=false`, 무호흡은 `apnea_verified=false`를 유지한다.
4. 테스트·빌드·해시·문서 검증이 통과한다.
5. 관련 변경만 커밋해 `codex/mmwave-phase-integration`에 push한다.

## 작업 환경

- 저장소: `/Users/kimjinsu/Documents/임베디드 소프트웨어 경진대회`
- 브랜치: `codex/mmwave-phase-integration`
- 구현 기준 커밋: `41af82b89ef8b47a15e380583ea0eac37384406e`
- ESP: ESP-WROOM-32, `esp32dev`, UART2 RX=GPIO16/TX=GPIO17, 115200 8N1
- 직전 포트: `/dev/cu.usbserial-10`; 재연결마다 `find /dev -maxdepth 1 -name 'cu.usb*' -print`로 다시 확인
- ESP firmware: `safenest-mr60-esp/1.2.0`
- schema: `1.2`
- config SHA-256: `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834`
- MR60 센서 자체 firmware: `UNKNOWN`; 승인 없이 업데이트 금지

시작 즉시 다음을 실행하고 기존 변경을 보존한다.

```bash
cd "/Users/kimjinsu/Documents/임베디드 소프트웨어 경진대회"
git status --short --branch
git diff --check
git log -3 --oneline --decorate
```

먼저 다음 파일을 읽는다.

1. `MR60_FINAL_HANDOFF_PROMPT_2026-08-01.md`
2. `MMWAVE_NEXT_SESSION_CHECKLIST.md`
3. `PROJECT_PROGRESS.md`의 마지막 `2026-08-01` 구간
4. `devices/mmwave/firmware/analysis/final/2026-08-01_mr60_final_validation_manifest.json`
5. `docs/ai/MR60_INTEGRATION.md`

## 검증 완료 상태

| 영역 | 상태 | 근거 |
|---|---|---|
| ESP firmware 1.2.0/schema 1.2 | PASS | 75초 healthcheck, config/firmware/hash 일치 |
| PlatformIO build | PASS | RAM 32,356B(9.9%), Flash 268,765B(20.5%) |
| Pi 어댑터·stream/input·manifest | PASS | 관련 unittest 15개 통과 |
| CSV delivery v2 | PASS | 원본·사본·CSV manifest 관리 항목 18개 SHA-256 일치 |
| 빈 공간 30분 | PASS | 17,995패킷, presence·생체·freeze 오탐과 reboot/UART 오류 0 |
| 정지 1인 재실 30분 | PASS | stable presence 98.77%, reboot/checksum/parse 오류 0 |
| 자연호흡 장기 지속성 | FAIL | filtered 유효률 21.58%, 저진폭 58.92% |
| 마지막 5분 제외 25분 | 재실 PASS/호흡 FAIL | presence 98.52%, filtered 유효률 25.90%, 저진폭 69.95% |
| 거리 0.6/0.9/1.2/1.5m | COMPLETE | 기존 6분 원본 4개와 CSV manifest SHA-256 확인 |
| 진입·퇴장 20회 | COMPLETE | 진입 평균 1.134초; 퇴장 평균 15.491초, vendor hysteresis 한계 |
| phase 페이싱 12/15/20rpm | PASS | 12.34/15.01/20.01rpm 재현 |
| vendor 호흡수 | 사용 금지 | 속도별 편향이 달라 고정 보정 불가 |
| 심박 정확도 | UNVERIFIED | 동시 외부 기준기기 없음 |
| 무호흡 | UNVERIFIED | 안전한 정답 데이터 없음 |

정지 1인 최신 원본의 마지막 5분 센서 보고 거리가 97.58cm에서 166.46cm로 바뀌었지만 사용자는 움직이지 않았다고 확인했다. 사람 이동으로 단정하지 말고 MR60 타깃 전환 또는 거리 추적 이상 후보로만 기록한다. 마지막 5분을 제외해도 호흡 저진폭 결론은 바뀌지 않는다.

## 절대 재수집하지 않을 항목

- 빈 공간 30분과 정지 1인 31분
- 위치 진단 3분·3분·1분
- 거리 D06/D09/D12/D15
- 진입→정지→퇴장 20회
- 12/15/20rpm 페이싱 호흡
- 기존 5분/6분 기준선과 필터 비교

새 물리 측정은 새로운 독립 가설, 바뀐 설치 조건, 명확한 통과 기준이 모두 있을 때만 사용자에게 먼저 설명하고 수행한다. 같은 조건의 장기 측정을 반복하지 않는다.

## 핵심 원본과 해시

- healthcheck 1.2: `logs/final/2026-08-01_healthcheck_v120_75s.jsonl`
  - `eb4c57a16ea00d6b4314364f298cac2420a0f9cf3023eed15d02dcdd95835382`
- 빈 공간 30분: `logs/final/2026-08-01_empty_v120_30min.jsonl`
  - `32ee3ae455ccf46029840f71268fdda37a88a963eed7ac7c7f9dfb269d00b3b2`
- 정지 1인 최신 31분: `logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl`
  - `7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34`
- 진입·퇴장 20회: `logs/kpi/2026-07-28_entry_exit_20_v2.jsonl`
  - `f28c41166a0da3104c74b207014aae4ff7be508876175f4881eb72bdb94d5164`
- 전체 증거 manifest: `analysis/final/2026-08-01_mr60_final_validation_manifest.json`

전체 `logs/` 전수 감사 결과는 JSONL 68개·154,413줄, 빈 파일 0개다. 파싱 불가 줄은 정확히 2개다. `2026-07-13_empty_desk_collector_v1_30s.jsonl` 1행은 여는 `{`가 없는 최초 부분 수신 줄이고, 첫 정지 31분 실패본 `2026-08-01_occupied_d09_v120_31min.jsonl` 9,000행은 직렬 1줄 손실이다. 둘 다 원본을 수정하지 말고 분석에서만 제외한다. 모든 원본 JSONL은 수정·삭제·이름 변경 금지다.

## 실제 남은 필수 작업

### 1. 팀 통합 노드 실제 USB JSONL 입력 확인

먼저 포트 점유를 확인하고 대시보드/캡처와 동시에 열지 않는다.

```bash
lsof /dev/cu.usbserial-10
```

`devices/mmwave/src/run_mr60_serial_adapter.py`의 실제 포트 입력과 `ondevice_ai/src/integrated_node/safenest_risk_engine.py`의 소비 경로를 확인한다. replay가 아니라 실제 ESP JSONL을 사용해 다음을 증명한다.

- schema 1.2 레코드를 파싱한다.
- firmware/config hash 불일치를 숨기지 않는다.
- 정상 데이터가 Pi 표준 `mmwave_mr60` 패킷으로 변환된다.
- presence=false, stale, timestamp 중복/역행, 0/null에서 window가 비워지고 UNKNOWN/DEGRADED로 간다.
- `heart_verified=false`, `apnea_verified=false`가 유지된다.
- 실제 통합 노드 상태에서 입력 수신·buffer 상태·최종 안전 metadata를 확인한다.

직접 연결 경로가 없다면 현재 구조를 먼저 설명하고, 가장 작은 bridge만 구현한다. MR60 원본 스키마나 ESP 임계값을 다시 바꾸지 않는다.

### 2. 최종 검증

```bash
git diff --check
cd devices/mmwave/firmware
pio run
.venv/bin/python -m py_compile \
  export_mmwave_csv.py analysis_tools/*.py capture_serial.py analyze_mmwave_log.py
cd ../..
/private/tmp/safenest-pi-regression-venv/bin/python -m unittest \
  tests/test_mr60_esp_adapter.py \
  tests/test_mmwave_stream_adapter.py \
  tests/test_mmwave_input_adapter.py \
  tests/test_mr60_manifest.py -v
```

가상환경이 사라졌다면 전역 Python을 오염시키지 말고 기존 `/opt/anaconda3` 패키지를 사용하는 임시 venv를 다시 만든다.

### 3. Git 완료

관련 변경만 검토한다. 원본 로그가 수정되지 않았는지 SHA-256으로 확인하고, 최종 결과·manifest·문서·필요한 최소 통합 코드만 커밋한다. 브랜치 `codex/mmwave-phase-integration`에 push하고 커밋 SHA를 보고한다.

## 선택 사항이며 완료를 막지 않는 항목

- Apple Watch 또는 의료용 기준기기를 확보한 뒤 심박 동시 측정
- 2인/다인 시험
- 천장형·침상형 설치 일반화
- MR60 센서 firmware 버전 조회 또는 업데이트

외부 심박 기준기기가 없으면 심박 하강 여부만 탐색적으로 볼 수 있으나 정확도·MAE·추종 성능 근거로 사용하지 않는다. MR60 센서 firmware 업데이트는 별도 승인 없이는 금지다.

## 안전·해석 규칙

- 숨참기, 과호흡, 가스 주입, 밀폐공간 시험 금지
- `0/null/NaN/timeout`을 정상 또는 무호흡으로 치환 금지
- 심박 없음으로 사람 없음·심정지 판정 금지
- vendor `breath_rate_raw`에 고정 오프셋 적용 금지
- 거리 `std=0` 단독 freeze 판정 금지
- ESP에서 최종 정상/주의/위험 판정 금지
- 자연호흡 지속성 FAIL을 숨기거나 재실 PASS와 합쳐 전체 생체 정확도 PASS로 발표 금지

최종 보고는 `완료`, `제한`, `남은 작업`, `검증 증거`, `커밋·푸시`를 분리해 간결한 표로 작성한다.

---
