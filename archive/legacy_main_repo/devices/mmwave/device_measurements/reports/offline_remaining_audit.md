# Offline Remaining Audit

기존 raw audit 이후, mmWave 연결 없이 가능한 CSV·adapter·입력 계약 검증을 추가로 수행했다.

## CSV delivery 실제 파일 대조

대상은 `2026-07-26_han_junwoo_delivery_v2`의 9개 CSV다.

| 검사 | 결과 |
|---|---:|
| 실제 CSV 파일 | 9개 |
| manifest SHA-256 일치 | 9/9 |
| manifest record 수 일치 | 9/9 |
| 컬럼 구조 일치 | 9/9 |
| timestamp 역행/중복 | 0/0 |
| `resp_phase` finite | 9/9 |
| 최대 timestamp gap | 0.103 s |
| subject | 전부 `S001` |
| signal source | 전부 `MR60BHA2_breath_phase` |

실제 CSV의 record 수와 timestamp는 기존 manifest 선언을 재현했다. 30초/3초 stride의 현재 `MMWaveCSVAdapter`로도 9개 세션에서 총 **620개 window**가 생성됐다.

- 모든 window shape: `(300,)`
- 모든 window finite
- 모든 window label/session/subject 연결 유지
- window quality 최저값: 약 0.998999
- 최대 보간 비율: 약 0.001001

따라서 기존 CSV delivery 파일은 **파일 무결성·기본 window 생성** 관점에서 재사용 가능하다. 이것은 물리 측정의 formal M-C0 충족을 뜻하지 않는다.

## 실제 MR60 ESP adapter replay

현재 main에서 읽은 `MR60ESPAdapter`를 bundled Python runtime으로 실행해 기존 JSONL을 replay했다. strict provenance를 켠 상태다.

| 결과 | 수치 |
|---|---:|
| 입력 JSONL 파일 | 78개 |
| adapter에 전달된 sensor-like record | 159,368개 |
| 잘못된 JSON 줄 | 3개 skip |
| schema/firmware/config mismatch | 89,618개 |
| 현재 schema 1.2 communication-valid | 69,750개 |
| adapter output `valid=true` | 31,328개 |
| adapter output `breath_valid=true` | 31,328개 |
| adapter output `heart_valid=true` | 31,311개 |
| adapter output `heart_verified=true` | 0개 |

legacy schema 1.0/1.1은 strict mode에서 `MMWAVE_SCHEMA_MISMATCH`로 분리됐다. 현재 schema 1.2는 firmware `safenest-mr60-esp/1.2.0`, config hash `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834`로 provenance를 통과했다.

대표적인 schema 1.2 final attempt02 replay 결과:

- 입력 18,574개
- output valid 14,269개
- warmup 1,200개
- presence unknown 3,105개
- distance invalid 2,884개
- phase FFT window가 실제로 valid이 된 결과만 `breath_valid=true`로 출력
- heart 값이 있어도 config상 `heart_verified=false` 유지
- `apnea=null`, `apnea_verified=false` 유지

이 replay는 현재 adapter의 fail-closed와 warmup/window 동작을 확인한다. 새 장치가 정상이라는 증거가 아니다.

## 모델 입력 계약 대조

현재 main에는 서로 다른 시점의 mmWave preprocessing/model metadata가 함께 있다.

| 출처 | mean | std | 입력 양자화 |
|---|---:|---:|---|
| `ondevice_ai/config/mmwave_input_contract.yaml` | 0.006091984 | 2.501383544 | 별도 명시 없음 |
| M-B11 locked `BPF_ZSCORE` | 0.003116283 | 2.955399435 | int8 scale 0.041720834, zero-point -3 |
| older v0.2 candidate metadata | 0.172122180 | 1.717154145 | int8 scale 0.012282304, zero-point 12 |

공통으로 확인되는 계약은 10 Hz, 30초, 300 samples, `[1,300,1]`, BPF 0.1–0.5 Hz 계열이다. 그러나 scaler와 quantization identity는 같지 않다. 따라서 M-C0에서 장치 raw를 모델에 연결할 때는 M-B11 locked candidate identity를 기준으로 고정해야 하며, older v0.2 metadata를 섞으면 안 된다.

실제 기존 데이터의 raw phase 크기도 확인했다.

- final attempt02 raw `breath_phase`: mean 0.001548, std 0.161531, range -0.88–0.94
- 9개 CSV 전체 `resp_phase`: mean -0.001306, std 0.286537, range -1.02–1.17
- M-B11 locked train z-score std: 2.955399

이후 별도 임시 runtime에 `numpy 2.5.2`와 `scipy 1.18.0`을 설치해 M-B11의 `scipy.signal.filtfilt` BPF를 정확히 재실행했다. 620개 CSV window 모두 shape `(620,300,1)`, finite, quality invalid 0, preprocessing clip 0%, int8 saturation 0%였다. BPF 포함 결과의 std는 약 0.09085936, int8 dequantization MAE는 약 0.00865676이었다. 임시 runtime은 레포나 메인 프로젝트에 저장하지 않았다.

## 경로·계약 정리 결과

- CSV delivery manifest와 실제 9개 CSV의 path basename, record 수, SHA-256은 일치한다.
- current `devices/mmwave/...` 경로와 historical final manifest의 `firmware/esp_wroom32_mr60_monitor/...` 경로는 여전히 lineage가 다르다.
- strict adapter는 legacy 1.0/1.1을 현재 schema 1.2 계약과 섞지 않는다.
- M-B12 handoff 자체도 physical MR60 compatibility, device preprocessing correspondence, domain shift, runtime input identity, Raspberry Pi behavior를 M-C에서 조사해야 한다고 남겨두고 있다.

## 오프라인 작업 종료 판정

센서 없이 가능한 분석 중 다음은 완료했다.

- 기존 raw 전체 inventory 및 재계산
- CSV 실제 파일 hash/record/timestamp 대조
- CSV window adapter replay
- ESP JSONL adapter replay
- strict provenance·fail-closed·warmup/window 결과 확인
- schema 세대 분리
- model preprocessing/scaler/quantization identity 비교
- physical raw phase amplitude와 offline scaler의 정적 domain-gap 비교
- M-B11 locked BPF 및 int8 quantization replay
- synthetic 정상/상수/NaN·Inf/짧은 입력 edge-case 검증
- bundle one-command audit와 strict negative test

이제 남은 것은 물리 장치가 있어야 하는 항목뿐이다: 새 환경 metadata를 붙인 capture, 독립 respiration reference, phase semantics 확인, MR60→ESP32→USB→Pi end-to-end, 그리고 실제 장치 raw를 M-B11 locked preprocessing에 넣은 최종 검증.
