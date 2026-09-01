# SafeNest 보관 영역

이 폴더에는 2026-07-26 디렉터리 정리 때 활성 작업 영역에서 분리한 자료가 있습니다. **파일은 삭제하지 않았으며**, 필요하면 원래 용도에 맞춰 되돌릴 수 있습니다.

| 경로 | 보관 내용 | 분리 이유 |
|---|---|---|
| `reference_documents/` | 기존 계획서, 심사평, 텍스트 추출물 | 이미 역사·참고 문서로 관리되던 묶음 통합 |
| `releases/2026-07-25/v1/` | 초기 팀 배포 폴더와 ZIP | v2·v3에 의해 대체됨 |
| `releases/2026-07-25/v2/` | v2 팀 배포 폴더와 ZIP | mmWave 실모델을 포함한 v3에 의해 대체됨 |
| `releases/2026-07-25/v3_extracted/` | v3 압축 해제 복사본 | 같은 버전 ZIP이 `output/`에 있고 루트가 더 최신임 |
| `reports/2026-07-25/superseded/` | PDF v1·v2 및 보완계획 v1 | 최신 후속 PDF가 `output/pdf/`에 있음 |
| `reports/2026-07-25/test_results/` | 2026-07-25 자동 테스트 원문 로그 | 2026-07-26 재검증 기록으로 대체됨 |
| `legacy/thermal/models/` | 구형·비교용 Thermal TFLite | 공식 모델이 `models/thermal/`로 단일화됨 |
| `legacy/thermal/data/` | 32×24 전처리 NPZ | 현재 런타임·테스트는 80×62 NPZ 사용 |
| `logs/co2/2026-07-13/` | 과거 오류·분석 로그 | 현재 코드 실행에 필요하지 않은 진단 기록 |
| `project_history/2026-07-25/audits/` | 완료 전 2·3차 감사 문서 | 후속 구현과 48개 테스트로 상태가 바뀜 |
| `workfiles/tmp_20260725/` | PDF 생성 코드와 페이지 렌더링 중간물 | 완성 PDF가 별도로 존재함 |
| `system_metadata/` | 활성 폴더에서 수거한 `.DS_Store` | Finder 전용 메타데이터라 소스와 무관함 |
| `version_snapshots/` | V4, V5, 구 V6 및 기존 version archive 전체 스냅샷 | 최상위를 유일한 활성 개발본으로 단일화 |
| `project_history/legacy_active_tests_20260808/` | V4 config/V5 release 전용 테스트 | 현재 최상위 회귀 대상에서 분리 |
| `project_history/legacy_release_tooling_20260808/` | V4/V5 archive builder·legacy V4-named validator·V5 snapshot verifier | 과거 wrapper 폴더 전용 tooling 분리 |
| `project_history/legacy_simulator_20260816/` | 가상 센서 스트리머와 4분할 GUI 시연기 | 현재 AI 실행·Pi 통합 경로가 아닌 과거 simulator |

## 복원 원칙

1. 배포 스냅샷은 폴더 전체를 복원합니다. 내부 파일만 골라 현재 루트에 덮어쓰지 않습니다.
2. 레거시 모델은 공식 `models/model_manifest.json` 경로를 바꾸지 않은 채 비교 목적으로만 사용합니다.
3. 감사 문서는 당시 상태의 기록입니다. 현재 상태 판단에는 `walkthrough/README.md`와 `reports/TEST_RESULTS_20260726.md`를 사용합니다.
4. 원래 루트에서 이동된 계획서 3종은 `reference_documents/`에 바이트 동일하게 보존돼 있습니다.
5. 활성 runtime·test·agent는 `archive/`의 Python module, manifest, model을 자동 선택하지 않습니다.
