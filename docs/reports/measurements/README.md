# 현장 측정 기록

2026-08-22 Raspberry Pi 현장 세션에서 수집한 Thermal 검증 기록의 제출용 사본이다.
분석 문서는 [`../20260822_Thermal_NOT_HUMAN_Field_Handoff_KO.md`](../20260822_Thermal_NOT_HUMAN_Field_Handoff_KO.md).

| 파일 | 내용 |
|---|---|
| `20260822_thermal_field_measurement_record.json` | 세션 전체 기록 (통신·저장·라이브 API·NPZ 집계) |
| `20260822_thermal_live_api_snapshot.json` | 측정 시점의 `/api/status` 응답 스냅샷 |
| `20260822_thermal_npz_tally.json` | 저장된 열화상 프레임의 분류 집계 |
| `20260822_thermal_field_measurement_summary.csv` | 위 기록의 요약 지표 |

## 공개용 마스킹

공개가 필요 없는 환경 식별자만 치환했다.

| 원본 | 표기 |
|---|---|
| Raspberry Pi 사설 IP | `<PI_IP>` |
| ESP32 peer 사설 IP | `<ESP_PEER_IP>` |
| 이전 현장 Pi 주소 | `<PREV_PI_IP>` |
| Pi 로컬 저장소 절대경로 | `<REPO_ROOT>` |
| Pi 계정명 | `<PI_USER>` |
| 현장 Wi-Fi SSID | `<REDACTED_SSID>` |

**측정 내용은 변경하지 않았다.** 센서 측정값, CO₂ ppm, 호흡수, 열화상 수치,
timestamp, 프레임 수, 모델 확률·분류 결과, 판정 결과, 성능 수치는 모두 원본
그대로다. 이 파일들은 체크섬으로 고정된 대상이 아니며, 어떤 매니페스트나
테스트도 이 파일들의 해시를 검증하지 않는다.
