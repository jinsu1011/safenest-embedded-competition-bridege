# 기존 MR60 실측 데이터 V5 Replay Benchmark

- 도구 버전: `0.1.0`
- Git commit: `6da2a7141af758ed4eebba61a7f09950022deb7b`
- 모델: `mmwave_resp_int8` v0.1.0
- 모델 SHA-256: `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158`

| Dataset | Scenario | Records | Windows | Success | TFLite | Prediction | Fallback | p95 ms | Result |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| empty_30min_v120 | empty_space_30min | 17995 | 0/0 | - | 0 | `{}` | 0 | - | PASS |
| occupied_31min_v120 | one_stationary_person_long_duration | 17974 | 47/49 | 95.92% | 47 | `{'NORMAL': 47}` | 0 | 0.3623377415351563 | PASS |
| distance_0_6m | stationary_normal_0.6m | 2998 | 9/10 | 90.00% | 9 | `{'NORMAL': 9}` | 0 | 0.19281639251857993 | PASS |
| distance_0_9m | stationary_normal_0.9m | 2998 | 8/10 | 80.00% | 8 | `{'NORMAL': 8}` | 0 | 0.1670391648076474 | PASS |
| distance_1_2m | stationary_normal_1.2m_range_limit | 2998 | 7/9 | 77.78% | 7 | `{'NORMAL': 7}` | 0 | 0.1434375066310167 | PARTIAL |
| distance_1_5m | stationary_normal_1.5m_lock_loss | 2999 | 0/0 | - | 0 | `{}` | 0 | - | PARTIAL |
| paced_12rpm | paced_breathing_12rpm | 1800 | 6/6 | 100.00% | 6 | `{'NORMAL': 6}` | 0 | 0.15131206600926816 | PASS |
| paced_15rpm | paced_breathing_15rpm | 1800 | 6/6 | 100.00% | 6 | `{'NORMAL': 6}` | 0 | 0.1443229557480663 | PASS |
| paced_20rpm | paced_breathing_20rpm | 1800 | 4/6 | 66.67% | 4 | `{'NORMAL': 4}` | 0 | 0.14440183877013624 | PARTIAL |
| entry_exit_20 | entry_still_exit_20_trials | 11354 | 1/22 | 4.55% | 1 | `{'NORMAL': 1}` | 0 | 0.1480410574004054 | PARTIAL |
| accepted_empty_6min_v2 | accepted_empty_room_6min | 3599 | 0/0 | - | 0 | `{}` | 0 | - | PASS |
| accepted_occupied_6min_v2 | accepted_stationary_person_0.8_to_1.0m | 2998 | 9/10 | 90.00% | 9 | `{'NORMAL': 9}` | 0 | 0.15499964356422424 | PASS |

분류 정확도는 명시적인 AI class ground truth가 있는 데이터에서만 계산합니다.
