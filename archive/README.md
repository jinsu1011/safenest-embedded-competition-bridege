# archive

과거 구현과 측정 증거를 보존하는 영역입니다.

**활성 런타임은 이 디렉터리를 참조하지 않습니다.** `archive/` 아래의 코드는 import되지 않고, 설정·모델·스크립트도 런타임 탐색 경로에 들어가지 않습니다. 여기 있는 파일을 고쳐도 SafeNest 동작은 바뀌지 않습니다.

## 구성

| 경로 | 내용 | 왜 남겼는가 |
| --- | --- | --- |
| `legacy_main_repo/` | 2026-08-17 canonical 재구성 이전의 메인 저장소 트리 (`devices/`, `display-test/`, `display-test2/`, `docs/`, `integration/`, `ondevice_ai/`, `shared/`) | mmWave·CO₂·Thermal 실측 데이터와 분석 리포트, 대회 문서가 들어 있습니다. 대부분 재현 불가능한 측정 증거입니다. |
| `integration_source_snapshots/` | `yuname121/integration`이 보관하던 `sources/devices`, `sources/display-test`, `sources/docs` 스냅샷 | 통합 판단 근거의 원본 대조용입니다. |
| `ondevice_ai_upstream_history/` | `sheepmeat/test`의 `archive/` (legacy 릴리스 도구, 구 시뮬레이터, 구 테스트) | 상류가 스스로 archive로 옮긴 이력입니다. |
| `legacy_prototypes/` | 초기 risk engine 프로토타입과 legacy risk rule | 현재 V4 risk 계약과의 비교 근거입니다. |

## canonical 대체 경로

| archive의 것 | 현재 canonical |
| --- | --- |
| `legacy_main_repo/ondevice_ai/` | `RaspberryPi/Ondevice_AI/` (상류 `sheepmeat/test`) |
| `legacy_main_repo/display-test2/esp32_sensor_node/` | `ESP32/Arduino/esp32_sensor_node/` |
| `legacy_main_repo/display-test2/raspberry_pi_lcd/` | `RaspberryPi/LCD/` |
| `legacy_main_repo/integration/web/` | `RaspberryPi/Web/` + `RaspberryPi/Runtime/backend/` |
| `legacy_prototypes/pi/risk_engine.py` | `RaspberryPi/Runtime/risk/engine.py` |

## 보안 참고

`legacy_main_repo/` 안의 여러 ESP32 스케치에는 과거 실제 Wi-Fi 자격증명이 하드코딩되어 있었습니다. 작업 트리에서는 placeholder로 치환했지만 **Git 이력에는 원래 값이 그대로 남아 있습니다.** 해당 Wi-Fi 비밀번호는 이미 노출된 것으로 간주하고 교체해야 합니다. 자세한 내용은 통합 리포트를 참조하십시오.

## 삭제 정책

여기 있는 파일은 사용자 승인 없이 영구 삭제하지 않습니다. 삭제 후보 검토 결과는 통합 리포트의 중복 검토 항목에 정리되어 있습니다.
