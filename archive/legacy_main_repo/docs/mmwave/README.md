# `docs/mmwave/`

## 1. 디렉터리 목적
MR60BHA2 mmWave 기기의 인수인계, 설치·튜닝, 검증 보고, 다음 작업 체크리스트 등 **사람이 읽는 문서**를 모은다. 코드와 실측 로그는 `devices/mmwave/`에 있다.

## 2. 시스템에서 담당하는 기능
새로 합류하거나 작업을 이어받는 사람이 이 디렉터리만 읽고 mmWave 작업을 재개할 수 있게 한다. 기존 시험을 반복하지 않도록 무엇이 이미 검증됐는지 기록한다.

## 3. 포함해야 하는 파일 유형
인수인계 문서, 설치·튜닝 계획과 보고서, 세션 체크리스트, 재개 프롬프트, 판정 근거 요약을 포함한다.

## 4. 포함하면 안 되는 파일 유형
펌웨어·어댑터 소스, 원본 JSONL/CSV 로그, 분석 산출 JSON, 기기 설정 파일은 포함하지 않는다. 전부 `devices/mmwave/` 아래에 있다.

## 5. 주요 하위 구성
| 문서 | 역할 |
|---|---|
| [`MMWAVE_MASTER.md`](MMWAVE_MASTER.md) | **먼저 읽을 문서.** 2026-08-01 기준 총정리이며 다른 문서와 충돌하면 이것이 우선한다 |
| [`MMWAVE_HANDOFF.md`](MMWAVE_HANDOFF.md) | MR60BHA2 + ESP-WROOM-32 인수인계 |
| [`MMWAVE_HANDOFF_NEXT.md`](MMWAVE_HANDOFF_NEXT.md) | 후속 작업자용 인수인계 프롬프트 |
| [`MMWAVE_TUNING.md`](MMWAVE_TUNING.md) | 설치·튜닝·검증 계획과 안전 경계 |
| [`MMWAVE_TUNING_REPORT_2026-07-29.md`](MMWAVE_TUNING_REPORT_2026-07-29.md) | 안정화 보고서 (CONDITIONAL PASS) |
| [`MMWAVE_NEXT_SESSION_CHECKLIST.md`](MMWAVE_NEXT_SESSION_CHECKLIST.md) | 남은 물리 검증만 이어가기 위한 체크리스트 |
| [`MR60_FINAL_HANDOFF_PROMPT_2026-08-01.md`](MR60_FINAL_HANDOFF_PROMPT_2026-08-01.md) | 최종 재개 프롬프트 |
| [`MR60BHA2_DEVICE_MEASUREMENT_PROTOCOL_M-C0.md`](MR60BHA2_DEVICE_MEASUREMENT_PROTOCOL_M-C0.md) | M-C0 물리 장치 측정 protocol과 evidence contract |

## 6. 입력과 출력 인터페이스
입력은 `devices/mmwave/firmware/logs/`의 기존 실측과 `devices/mmwave/device_measurements/`의 M-C0 evidence이며, 출력은 사람이 읽고 판단할 수 있는 절차와 판정 근거다.

## 7. 다른 기능 영역과의 관계
코드·로그는 [`devices/mmwave/`](../../devices/mmwave/), 하드웨어 설치는 [`docs/operations/HARDWARE_RUNBOOK.md`](../operations/HARDWARE_RUNBOOK.md), AI 연동은 [`ondevice_ai/docs/MR60_INTEGRATION.md`](../../ondevice_ai/docs/MR60_INTEGRATION.md)를 함께 본다.

## 8. 실행·학습·추론 또는 활용 방법
작업을 이어받을 때는 `MMWAVE_MASTER.md` → `MMWAVE_NEXT_SESSION_CHECKLIST.md` → `MR60BHA2_DEVICE_MEASUREMENT_PROTOCOL_M-C0.md` 순으로 읽는다. 문서 안의 경로는 저장소 루트 기준이며, 명령은 루트 또는 `devices/mmwave/firmware/`에서 실행한다.

## 9. 현재 개발 상태 및 버전
MR60 schema 1.2, 펌웨어 v1.2.0 기준이다. 최종 검증 근거는 `devices/mmwave/firmware/analysis/final/2026-08-01_mr60_final_validation_manifest.json`이다. 의료 수준 정확도, 심박 정확도, 무호흡 검출 완료로 발표하지 않는다.

## 10. 향후 파일 추가 및 관리 규칙
보고서에는 날짜와 대상 펌웨어 버전을 파일명 또는 본문에 넣는다. 기존 보고서를 덮어쓰지 말고 새 날짜로 추가한다. 실패한 실험도 지우지 않고 원인과 다음 방법을 남긴다. 로그·분석 산출물과 M-C0 QA 산출물은 이 디렉터리가 아니라 `devices/mmwave/` 아래에 둔다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Jinsu Kim (`@jinsu1011`) — mmWave 기기 및 통합.
원본 ref는 `origin/main` 계보와 `codex/mmwave-phase-integration` (`b0d3c95`)이다. 2026-08-03 책임 영역 재편(`38274c0`)에서 `devices/mmwave/docs/`로 옮겼고, 팀 문서 규칙에 따라 `f0470c6`에서 현재 경로로 다시 옮겼다. 두 이동 모두 `git mv`만 사용한 순수 이동이다.
