# 06_SOURCES

## 1. 공식 대회 문서 (Priority 1)
| ID | 문서 | 패키지 경로 | 원본 파일명 |
|---|---|---|---|
| O1 | 제24회 임베디드SW경진대회 개발완료보고서 작성 안내 (2026-05-06, 사무국) | `00_Official/01_2026_개발완료보고서_작성안내.pdf` | (가이드양식) 제24회 임베디드SW경진대회 개발완료보고서 작성 안내.pdf |
| O2 | [제24회 임베디드SW경진대회] 자유공모 부문 세부 안내사항 v2 (2026.05) | `00_Official/02_2026_자유공모_세부안내.pdf` | 1. [제24회…] 자유공모 부문 세부 안내사항_v2 (4).pdf |
| O3 | (2026) 임베디드SW경진대회 규정 v3 (2026.05) | `00_Official/03_2026_임베디드SW경진대회_규정.pdf` | [규정] (2026) 임베디드SW경진대회 규정_v3.pdf |
| O4 | 대회 홈페이지 | eswcontest.or.kr | (O2 p.3에 기재) |

## 2. 공공/정부 통계 — **원문 재확인 필요**
| ID | 인용 내용 | 중간계획서가 밝힌 출처 | 상태 |
|---|---|---|---|
| S1 | 최근 10년(2014~2023) 밀폐공간 질식재해 174건, 재해자 338명, 사망 136명 (치명률 약 42%) | 고용노동부 밀폐공간 질식재해 예방 보도자료(2024) | ⚠ **원문 URL·발행일 미확보 — 최종본 반영 전 고용노동부/안전보건공단 원문 확인 필수** |
| S2 | 검찰 송치 밀폐공간 중대재해의 85.7%가 산소·유해가스 농도 미측정 | 경향신문 밀폐공간 중대재해 분석 보도(2025) | ⚠ 2차 보도 — 원자료 확인 필요 |
| S3 | 산업안전보건법 제619조(밀폐공간 작업 시 농도 측정·감시인 배치), 시행규칙 별표18(밀폐공간 20종) | 법령 | ⚠ 조문 원문 확인 권장 (국가법령정보센터) |
| S4 | 2023년 산재 사망자 중 5인 미만 사업장 40.6% | 중간계획서 (출처 미기재) | ⚠ **출처 불명 — 확인 전 사용 금지** |
| S5 | 중대재해처벌법 2024-01 50인 미만 사업장 확대 적용 | 중간계획서 | ⚠ 법령 원문 확인 권장 |

> 본 DRAFT에서는 S1·S3만 "출처 확인 필요" 각주와 함께 제한적으로 사용하고, S2·S4·S5는 사용하지 않는다.

## 3. 데이터셋 / 외부 모델 (규정 제10조③ 고지 대상)
| ID | 자산 | 기관/식별자 | 라이선스 | 사용 |
|---|---|---|---|---|
| D1 | Zenodo mmWave vital-sign dataset (110명·440rec·530window, 60 GHz FMCW) | Zenodo DOI `10.5281/zenodo.18599983` | **CC BY 4.0** | mmWave 지도학습 backbone |
| D2 | SDT Dataset (32k train / 8k val / 8k real test, FLIR Lepton 3.5) | TU Wien / Zenodo `4124309` | **CC-BY-4.0 메타데이터 vs 비상업 연구 제한 충돌 — 확인 필요** | Thermal T-A/T-B 오프라인 |
| D3 | UCI Occupancy Detection (20,560행) | UCI ML Repository ID 357 / Univ. of Mons | **CC-BY-4.0 (검증됨)** | CO₂ C-A/C-B6 학습 |
| D4 | repository NPZ 합성 468 샘플 | 저장소 내부 테스트 자산 | 내부 | 동작 확인 전용, **실세계 근거 아님** |

## 4. 하드웨어 / 제조사 사양 — **데이터시트 원문 미보유**
| ID | 부품 | 사양(프로젝트 문서 기재) | 상태 |
|---|---|---|---|
| H1 | Seeed **MR60BHA2** 60 GHz mmWave | 재실·호흡, ~1.5 m, UART 115200 | ⚠ 데이터시트 원문 필요 |
| H2 | **Thermal-44** (MI48xx + MI0801/0802) 80×62 | I2C 제어 + SPI 데이터, raw×0.1−273.15 K | ⚠ 데이터시트 원문 필요 |
| H3 | Sensirion **SCD40/SCD4x** NDIR CO₂ | I2C 0x62, 주기측정 약 5 s | ⚠ 데이터시트 원문 필요 |
| H4 | **PIR HC-SR501** | 디지털 출력, 감도·유지시간 가변 | ⚠ |
| H5 | **ESP32 Dev Module / ESP-WROOM-32 DevKit V1** | 30-pin | ⚠ |
| H6 | **Raspberry Pi 5** | — | ⚠ |

## 5. 오픈소스 / 소프트웨어
| ID | 구성요소 | 근거 |
|---|---|---|
| L1 | Arduino core for ESP32, `WiFi.h`, `Wire.h`, `SPI.h`, FreeRTOS | `.ino` include |
| L2 | `SensirionI2cScd4x` (Sensirion Arduino 라이브러리) | `.ino` include |
| L3 | `Seeed_Arduino_mmWave` | `.ino` include |
| L4 | TensorFlow Lite (INT8 추론), TensorFlow 2.19.1 (학습·검증) | `model_manifest.json`, `INTEGRATION_PROGRESS.md` |
| L5 | Python 표준 라이브러리 `http.server`, `socket`, `struct` | `integration/pi_lcd/server.py` |
| L6 | Express 5, bcryptjs, jsonwebtoken, qrcode (Node.js) | `integration/web/package.json` |
| L7 | gpiozero (부저 제어) | `server.py` BuzzerController |
| L8 | numpy | `ondevice_ai/risk/*` |

> **규정 제10조③ 준수**: 위 외부 소프트웨어·데이터셋의 출처, 팀이 개선·추가한 부분, 팀 자체 구현 부분을 보고서 6·9·14페이지에 구분 기재한다.
> **미확인**: 저장소 최상위 `LICENSE` 파일 존재 여부 미확인 → 제출 전 확인 필요.

## 6. 내부 프로젝트 증거
`05_Source_Snapshot/` @ `3f22fb145c49173a93afb0da25910ec4894bda1a` ·
`03_Evidence/CO2_Data/`, `Thermal/`, `Test_Results/`, `Logs/`, `Hardware_Photos/`, `Circuit/`, `Demo_Materials/` ·
팀원 보고서 4종(+ 강유나 최종본 `SafeNest_강유나_통합개발보고서_최종.docx`, SHA-256 `90bdf120…`, 2026-08-22 수령) ·
본 세션 실행 로그 `work/test_runs/EXECUTED_TESTS.md`.
