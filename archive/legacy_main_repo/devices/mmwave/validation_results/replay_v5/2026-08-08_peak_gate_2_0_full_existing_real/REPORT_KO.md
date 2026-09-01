# 기존 MR60 실측 데이터 V5 Replay Benchmark

- 도구 버전: `0.1.0`
- Git commit: `9058af58f1dfb9f0b4360f7e98d83c0f0db41650`
- 모델: `mmwave_resp_int8` v0.1.0
- 모델 SHA-256: `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158`

| Dataset | Scenario | Records | Windows | Success | TFLite | Prediction | Fallback | p95 ms | Result |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| empty_30min_v120 | empty_space_30min | 17995 | 0/0 | - | 0 | `{}` | 0 | - | PASS |
| occupied_31min_v120 | one_stationary_person_long_duration | 17974 | 45/49 | 91.84% | 45 | `{'NORMAL': 45}` | 0 | 0.13949160929769275 | PASS |
| distance_0_6m | stationary_normal_0.6m | 2998 | 9/10 | 90.00% | 9 | `{'NORMAL': 9}` | 0 | 0.14759162440896034 | PASS |
| distance_0_9m | stationary_normal_0.9m | 2998 | 7/10 | 70.00% | 7 | `{'NORMAL': 7}` | 0 | 0.16311255749315023 | PARTIAL |
| distance_1_2m | stationary_normal_1.2m_range_limit | 2998 | 7/9 | 77.78% | 7 | `{'NORMAL': 7}` | 0 | 0.17562507418915624 | PARTIAL |
| distance_1_5m | stationary_normal_1.5m_lock_loss | 2999 | 0/0 | - | 0 | `{}` | 0 | - | PARTIAL |
| paced_12rpm | paced_breathing_12rpm | 1800 | 6/6 | 100.00% | 6 | `{'NORMAL': 6}` | 0 | 0.15470825019292533 | PASS |
| paced_15rpm | paced_breathing_15rpm | 1800 | 6/6 | 100.00% | 6 | `{'NORMAL': 6}` | 0 | 0.16509348643012345 | PASS |
| paced_20rpm | paced_breathing_20rpm | 1800 | 2/6 | 33.33% | 2 | `{'NORMAL': 2}` | 0 | 0.15325205749832094 | PARTIAL |
| entry_exit_20 | entry_still_exit_20_trials | 11354 | 1/22 | 4.55% | 1 | `{'NORMAL': 1}` | 0 | 0.1597920199856162 | PARTIAL |
| accepted_empty_6min_v2 | accepted_empty_room_6min | 3599 | 0/0 | - | 0 | `{}` | 0 | - | PASS |
| accepted_occupied_6min_v2 | accepted_stationary_person_0.8_to_1.0m | 2998 | 9/10 | 90.00% | 9 | `{'NORMAL': 9}` | 0 | 0.15574961435049772 | PASS |

분류 정확도는 명시적인 AI class ground truth가 있는 데이터에서만 계산합니다.
