# Thermal model artifact policy

현재 Thermal 선택 기준선은 T-B5의 `FULL_INT8` 후보입니다.

- SHA-256: `fa9730c29535477a3994c11e664474a0ca0116afaaa172889f47446ab2ac46be`
- 파일 크기: 318,280 bytes
- 입력/출력: `[1, 62, 80, 1]` → `[1, 3]`
- 클래스 순서: `NOT_HUMAN`, `HUMAN_NORMAL`, `HUMAN_FALL`

선택 후보는 외부 artifact 저장소에 있으며 Git에는 추가하지 않습니다. 수령
후 SHA-256과 파일 크기를 확인하고, T-C 데이터 계약 검증을 통과한 환경에서만
평가에 사용합니다.

팀 저장소의 기존 `models/model_manifest.json`과 과거 `v0.1.0` binary/runtime은
기존 통합 호환성을 위해 보존된 역사적 기본값입니다. 이 파일들은 T-B5 선택
후보가 아니며, T-C 근거와 명시 승인 없이 새 기준선으로 승격하거나 T-B5
전처리와 혼합하지 않습니다.
