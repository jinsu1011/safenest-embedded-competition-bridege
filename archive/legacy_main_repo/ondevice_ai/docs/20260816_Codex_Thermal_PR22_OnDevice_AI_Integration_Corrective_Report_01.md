# 2026-08-16 SafeNest Thermal PR #22
# On-Device AI Integration and Pre-T-C Capture Corrective Report

## 1. Executive Summary

PR #22는 단순 firmware 수정이 아니라 standalone Thermal A/B 결과와 pre-T-C 수집 도구를 팀 저장소의 `ondevice_ai/` 및 `devices/thermal/` 구조에 통합한 작업이다. 이번 corrective review는 SNTR transport identity와 검증되지 않은 센서 header 관찰값을 분리하고, `raw_chunks/` provenance를 exact checksum inventory로 강화하며, sender-side loss telemetry를 machine-readable evidence로 보존하고, Thermal-44와 Thermal-90의 역할 경계를 명시했다.

작업 분류는 `TEAM-THERMAL-INTEGRATION / PRE-T-C DEVICE-CAPTURE PREPARATION`이다. `T_C_EXECUTED = NO`, `T_C_DEVICE_CONTRACT_VERIFIED = NO`다. 실제 센서 검증, 모델 production 교체, 재학습 및 낙상 성능 주장은 이 PR의 결과가 아니다.

## 2. Change Metadata

| Field | Value |
|---|---|
| Date | 2026-08-16 KST |
| Agent / Executor | Codex |
| Agent product/model | Codex; underlying model identity not independently verified in repository evidence |
| Execution mode | Local workspace corrective implementation and GitHub PR update |
| Human owner/reviewer | Repository owner/reviewer; final approval pending |
| Repository | `jinsu1011/safenest-embedded-competition` |
| PR | `#22` |
| Branch | `integration/update-latest-thermal` |
| Base | `main` |
| Starting HEAD | `bc1802dee0348d8218a929d809d5a2fa1b593c06` |
| Final HEAD | PR #22 corrective head; exact SHA is reported by GitHub/final execution result because a commit cannot embed its own SHA without changing it |
| Work Classification | `TEAM-THERMAL-INTEGRATION / PRE-T-C DEVICE-CAPTURE PREPARATION` |
| Formal Thermal Phase | Pre-T-C preparation; not formal T-C |
| Standalone Thermal State | T-A0~T-A6 and T-B0~T-B5 completed separately with recorded limitations |
| T-C Executed | `NO` |
| Primary Scope | Thermal on-device AI synchronization, capture transport, provenance, validator, tests and docs |
| Modified Subsystem | `ondevice_ai/`, `devices/thermal/`, necessary root metadata |
| Target Hardware | Thermal-90 prototype path with Seeed XIAO ESP32-C6 and Raspberry Pi receiver |
| Runtime Target | Raspberry Pi capture/validation preparation; production runtime unchanged |
| Team Repository Base Commit | `0fc2fd5be40f3a5714e738258183676f4adb1109` |
| Status | Corrective implementation validated; owner review required |
| Merge Status | `MERGE = NOT AUTHORIZED` |

## 3. Why PR #22 Was Needed

PR 이전 팀 저장소에는 Thermal-44 이름의 historical runtime/mock/parser 경로와 v0.1.0 모델이 있었지만, 최신 standalone Thermal A/B evidence 및 fail-closed Thermal-90 raw capture transport가 완전히 정렬돼 있지 않았다. PR #22는 최신 Thermal 데이터 계약, validator, tests, handoff 문서와 XIAO/Pi SNTR UDP V2 capture path를 팀 구조에 배치했다.

실제 T-C 전에 full-frame raw bytes, chunk provenance, transport integrity, sender/receiver 관측성 및 UNKNOWN/NOT_VERIFIED 경계를 먼저 고정해야 한다. 이 준비가 없으면 낮은 FPS나 frame 누락이 센서 생성, ESP32 acquisition, SPI, Wi-Fi, Pi receive 또는 disk backlog 중 어디서 발생했는지 구분할 수 없다.

이 PR은 장치 계약을 검증한 것이 아니라, 검증 가능한 방식으로 다음 장치 실험을 수행할 도구와 기록 형식을 준비한 것이다.

## 4. Source / Upstream Provenance

세 저장소 역할을 구분한다.

- Original/upstream repository: `rla1729/safenest-thermal-ai`, observed upstream `main` `294531a0c57c28fe1be88f95755f06851217ac80`
- Actual synchronization source: `yuname121/safenest-thermal-ai`, `main` `db51112bfd02cdda2d41e99cf11acde75f771ecf`
- Merged source PR head included: `71c6d08d8a443f6a50d860d27380ff40a87a860e`
- Team destination: `jinsu1011/safenest-embedded-competition`, base `0fc2fd5be40f3a5714e738258183676f4adb1109`

Sync method는 PR diff만 복사한 것이 아니라 source repository 전체 tracked tree를 팀 구조와 비교한 뒤 동일 파일은 KEEP하고, 최신 파일은 UPDATE/REPLACE/ADD하며, standalone 경로는 팀의 `ondevice_ai/`와 `devices/thermal/` 경계로 ADAPT한 방식이다. 더 오래된 `sheepmeat/test` 및 team architecture reference lineage는 `PROVENANCE.md`에 보존하지만 이번 sync의 exact source SHA로 대체하지 않는다.

## 5. Thermal Phase Context

- Standalone T-A0~T-A6: dataset identity, provenance, safe reader, canonical geometry, label/split 및 전체 변환 closure.
- Standalone T-B0~T-B5: offline candidate 비교, conversion, equivalence, robustness와 candidate lock.
- Latest offline candidate: `FULL_INT8`; offline evidence일 뿐 device-domain 승인 모델이 아니다.
- PR #22: team repository synchronization 및 pre-T-C capture/runtime preparation.
- Formal T-C: 실행하지 않음. A/B를 다시 열거나 재해석하지 않았음.

## 6. Files and Areas Changed

### KEEP

- 기존 team integrated node, TCP, LCD/web, risk/fusion, CO₂, mmWave, PIR 동작.
- 이미 source와 동일한 Thermal A/B dataset, manifests, scripts, tests 및 reports.
- historical runtime model/manifest 경로.

### UPDATE / REPLACE

- Thermal real-capture validator와 T-A/T-B validator/tests.
- corrective review에서 counter semantic gate, sender telemetry validation 및 raw chunk exact inventory를 추가.

### ADD

- SNTR UDP V2 receiver/reassembler와 tests.
- XIAO ESP32-C6 Thermal-90 sender.
- machine-readable SNTR sender status packet과 Pi `sender_telemetry.jsonl`.
- capture/handoff/provenance 문서 및 이 formal corrective report.

### ADAPT

- standalone `firmware/`를 `devices/thermal/`로, AI 자료를 `ondevice_ai/`로 배치.
- `.gitignore`, `.gitattributes`, README, hardware naming 및 source provenance를 팀 규칙에 맞춤.

### REMOVE

- 없음.

## 7. Model State

| Item | State |
|---|---|
| Legacy/current team runtime model | `models/thermal/thermal_fall_int8_v0.1.0.tflite` |
| Legacy SHA-256 | `5b56da8d127ccef85f30b6459cc0cfe2d86490e41f3caa5bd2a7b70bbc46ae84` |
| Latest offline candidate | `FULL_INT8` |
| Offline candidate SHA-256 | `fa9730c29535477a3994c11e664474a0ca0116afaaa172889f47446ab2ac46be` |
| Offline candidate size | 318,280 bytes |
| Production replacement performed | `NO` |
| Hardware/device-domain validation performed | `NO` |

T-B5 artifact는 승인된 외부 artifact 저장소 identity로만 관리되며 Git에 추가하지 않았다. T-C evidence와 별도 승인 전에는 default manifest/model path를 교체하지 않는다.

## 8. SNTR UDP V2 Architecture

```text
Thermal-90 sensor
  -> XIAO ESP32-C6 acquisition
  -> 10,080-byte logical Thermal frame
  -> SNTR V2 9-chunk transport + transport_frame_id + CRC32
  -> UDP
  -> Raspberry Pi receiver
  -> chunk index/count/offset/length validation
  -> fail-closed frame reassembly
  -> frame CRC/length/identity validation
  -> raw_chunks + raw frame + decoded-native + metadata + checksums
```

`transport_frame_id`는 “이 UDP chunk들이 어느 SNTR 논리 프레임에 속하는가?”에 답한다. 검증된 sensor acquisition counter는 “어느 물리 센서 acquisition event가 이 frame을 만들었는가?”에 답해야 한다. 두 identity는 교환할 수 없다.

## 9. Thermal-90 Sender Architecture

Sender는 D_READY event를 관찰하고 SPI로 5,040 uint16 word를 읽어 9개 MTU-safe datagram으로 전송한다. raw frame attempt 30회마다 별도 32-byte SNTR status packet으로 다음 관찰값을 보낸다.

- `d_ready_events_observed`
- `dropped_ready_signals`
- `transport_frames_attempted`
- `transport_frames_emitted`
- `send_failures`
- `sender_uptime_ms`

`d_ready_events_observed`는 ESP32 ISR이 관측한 D_READY rising edge 수일 뿐, 센서 내부에서 생성된 전체 frame 수와 같다고 검증된 값이 아니다. SNTR V2의 32-byte wire layout과 field position은 바뀌지 않았고 machine-readable JSON 이름과 firmware/receiver 용어만 의미에 맞게 고쳤다. 새 writer는 `safenest.thermal.sender_status.v2`를 쓰며 validator는 구형 v1의 `ready_signals_generated`도 `ESP32-observed D_READY events only`로 제한해 읽는다.

Pi는 수신 status 원본 32-byte datagram을 `raw_chunks/`에 보존하고, 그 decoded view를 `sender_telemetry.jsonl`에 기록하며 둘 다 checksum으로 보호한다. status packet 자체가 Pi에 도달하지 않으면 `SENDER_SIDE_ACQUISITION_LOSS_NOT_FULLY_OBSERVABLE_FROM_PI_CAPTURE`를 유지한다. 관찰되지 않은 count를 발명하지 않는다.

## 10. Corrective Findings From Review

1. Thermal header word 0을 sensor frame counter처럼 강하게 사용해 synthetic `MISSING` frame과 hard invalid를 만들 수 있었다.
2. `raw_chunks/`가 보존돼도 validator가 실제 파일 전체와 checksum registry를 양방향 exact inventory로 비교하지 않았다.
3. `droppedReadySignals`, `sendFailures`가 Serial 출력에만 있어 Pi evidence만으로 sender-side loss를 구분하기 어려웠다.
4. Thermal-44 historical runtime naming과 Thermal-90 current capture target의 역할 및 호환성 경계가 충분히 명시되지 않았다.

## 11. Correction A — Unverified Header Word 0 Semantics

교정 구현은 세 identity를 분리한다.

- `transport_frame_id`: SNTR logical frame/chunk reassembly identity.
- `sensor_header_word0_observed`: raw header word 0 관찰값.
- `sensor_frame_counter`: semantics가 실제 hardware evidence로 `VERIFIED`된 경우에만 authoritative counter.

PR #22 sender/collector에서 word 0은 `SEMANTICS_UNVERIFIED`다. duplicate/reversal/gap pattern은 descriptive warning으로 남지만 capture를 단독 hard-fail하지 않고 synthetic `MISSING` sensor frame도 만들지 않는다. Validator의 `DUPLICATE_SENSOR_COUNTER`, `SENSOR_COUNTER_REVERSAL`, `SENSOR_COUNTER_GAP` 규칙은 `sensor_frame_counter_status == VERIFIED`인 evidence에만 적용한다.

## 12. Correction B — raw_chunks Integrity Coverage

`raw_chunks/`는 reassembly mode에서 Pi가 받은 모든 원본 datagram을 보존한다. 여기에는 (A) logical Thermal frame 재조립에 쓰는 SNTR frame-chunk datagram과 (B) SNTR sender status raw datagram이 모두 포함된다. `sender_telemetry.jsonl`은 (B)의 별도 원본이 아니라 decoded machine-readable view다. 원본 status bytes와 decoded JSONL은 모두 `checksums.sha256`에 등록된다.

Validator는 `raw_chunks/` actual files와 `checksums.sha256` registered paths를 양방향 비교한다.

- registered file missing: `RAW_CHUNK_FILE_MISSING`
- content mismatch: `RAW_CHUNK_CHECKSUM_MISMATCH`
- actual file without checksum: `RAW_CHUNK_CHECKSUM_MISSING`
- actual unregistered file: `EXTRA_UNREGISTERED_RAW_CHUNK`
- duplicate registry entry: `RAW_CHUNK_CHECKSUM_DUPLICATE`

디렉터리 존재만으로 PASS하지 않는다. 모든 finalized raw datagram file이 등록되고 checksum-covered되어야 하며, decoded `sender_telemetry.jsonl`도 별도 checksum coverage를 받는다.

## 13. Correction C — Sender-Side Loss Telemetry

다음 단계는 서로 다른 관찰 층이다.

```text
sensor-internal frame generation                         [UNVERIFIED / not independently observed]
  -> ESP32-observed D_READY events                       [OBSERVED]
  -> SPI acquisition attempts / completed logical frame [partly OBSERVED; physical completeness UNVERIFIED]
  -> SNTR transport frames attempted                     [OBSERVED sender counter]
  -> SNTR transport frames emitted                       [DERIVED from sender send results]
  -> UDP datagrams received by Pi                        [OBSERVED at receiver]
  -> logical frames successfully reassembled             [DERIVED from SNTR identity/offset/length/CRC]
```

현재 telemetry는 ESP32-observed D_READY activity, ready-event coalescing/drops, transport attempted/emitted, UDP send failures와 uptime을 제공한다. 센서 내부에서 실제 생성한 frame 수, 모든 내부 frame이 관측 가능한 D_READY를 발생시켰는지, 모든 physical acquisition이 완료됐는지는 독립적으로 증명하지 않는다. status가 없거나 Wi-Fi에서 함께 손실될 수 있으므로 Pi capture만으로 end-to-end completeness를 항상 증명할 수는 없다.

낮은 observed FPS는 sensor generation, ESP32 acquisition latency, ready-signal drops, SPI read time, UDP send failures, Wi-Fi loss, Pi receive loss 또는 disk/write backlog 중 여러 층과 관련될 수 있다. D_READY N회를 관측했다는 사실만으로 센서가 N frame을 생성했다고 표현하거나 generation rate를 계산하지 않는다.

### Evidence-layer authority

| Evidence | Layer | Current authority |
|---|---|---|
| `transport_frame_id` | SNTR transport | logical transport frame identity에 authoritative |
| chunk index/count/offset/length | transport | SNTR V2 내부 구조에 authoritative |
| CRC32 | transport integrity | covered logical frame bytes에 authoritative |
| Thermal header word 0 | sensor payload observation | `SEMANTICS_UNVERIFIED` |
| `d_ready_events_observed` | ESP32 observation | observed interrupt/event count only |
| `dropped_ready_signals` | sender runtime | ESP32-side observed/coalesced loss evidence |
| `send_failures` | UDP sender runtime | sender-side transport attempt evidence |
| Pi reassembled frame | receiver | complete transport frame가 Pi에 도달해 CRC-valid 재조립됐다는 evidence |

## 14. Correction D — Thermal-44 / Thermal-90 Role Separation

- Thermal-44: team runtime의 historical `thermal44` sensor ID, mock/parser, v0.1.0 inference compatibility 경로. 현재 driver도 실제 장치 I/O가 아닌 simulated placeholder를 포함하며 physical verification이 완료되지 않았다.
- Thermal-90: PR #22의 current XIAO ESP32-C6 + SNTR UDP V2 pre-T-C raw capture/pilot target.
- `FINAL_THERMAL_HARDWARE_SELECTION = NOT_YET_FROZEN`.

두 경로의 shape, dtype, temperature unit/encoding, orientation, header semantics, FPS, invalid-pixel representation을 증거 없이 이전하지 않는다. 각각 독립 device contract evidence가 필요하다.

### Thermal-90 known versus unknown hardware contract

| Property | Status |
|---|---|
| Device identity | `PARTIALLY_KNOWN`; prototype path/name은 known, final hardware selection은 미동결 |
| Native frame shape | `UNVERIFIED` on actual device |
| Dtype / byte encoding | `UNVERIFIED` on actual device |
| Temperature encoding | `UNVERIFIED` |
| Physical unit | `UNVERIFIED` |
| Orientation | `UNVERIFIED` |
| Configured FPS | firmware configuration value only; physical behavior authority 없음 |
| Effective FPS | measurement required |
| Header word 0 semantics | `SEMANTICS_UNVERIFIED` |
| Invalid-pixel semantics | `UNVERIFIED` |
| Pi end-to-end latency | not measured |
| FULL_INT8 device compatibility | not validated |

## 15. Historical Pilot Report Review

Branch의 Thermal capture 관련 문서와 session summary를 다시 검색했다. `20260816_Thermal_OnDevice_AI_Handoff_KO.md`의 `session_S000_004` 및 네 static session 표가 header word 0을 authoritative counter로 사용한 과거 해석을 포함했다. 해당 수치와 당시 판정은 역사 evidence로 삭제하지 않았다.

- Earlier interpretation: header word 0 was treated as counter-like sensor evidence.
- Corrected interpretation: header word 0 semantics remain unverified.
- Therefore its discontinuity alone does not prove physical sensor-frame loss, duplicate, reversal, synthetic `MISSING`, or capture invalidity.
- SNTR V2 `transport_frame_id`, chunk completeness, offset/length, CRC32 및 실제 수신 datagram에 독립적으로 근거한 transport findings는 그대로 유효하다.
- 새 PASS를 소급 부여하지 않았고 `PREVIOUS_SENSOR_COUNTER_INTERPRETATION_REQUIRES_RECLASSIFICATION`을 유지했다.

## 16. Validation Performed

| Check | Result | Evidence |
|---|---|---|
| Focused UDP + real-capture validator tests | PASS | `pytest -q tests/test_thermal_udp_capture.py tests/test_thermal_real_capture_validator.py`: 60 passed |
| Corrective counter matrix | PASS | unverified duplicate/reversal/gap non-hard-fail; verified rules active |
| raw_chunks tamper matrix | PASS | delete/modify/checksum removal/extra/valid inventory tests |
| Sender telemetry | PASS | v2 field rename, v1 semantic compatibility warning, raw status + decoded JSON checksum coverage, absent-status limitation tests |
| Thermal broader spot run | PARTIAL / not claimed as full PASS | 202 passed, 3 skipped before an unrelated Windows `cp949` decode failure; the single failing test passed with `PYTHONUTF8=1` |
| TFLite interpreter | NOT RUN in this final pass | runtime dependency was unavailable and additional installation was not authorized; no fabricated PASS |
| XIAO ESP32-C6 compile | PASS | flash 1,001,510 bytes (76%); RAM 55,960 bytes (17%) |
| Compile/import | PASS | Python syntax/import checks; existing unrelated warnings documented |
| `git diff --check` | PASS | final audit |
| Selected cross-track spot regression | PARTIAL with environment/data limits | 38 passed; 3 CO₂ tests could not complete because owner-local raw archive and `python3` executable alias were unavailable; no cross-track files changed |
| Hardware validation | NOT PERFORMED | requires actual T-C hardware work |
| T-C execution | `NO` | this PR is pre-T-C preparation |

Final addendum validation was intentionally kept minimal at the owner's request. Missing owner-local data, unavailable executable/runtime dependencies, partial runs and skipped tests are not reported as PASS. Earlier corrective-head full regression evidence remains historical context, not a substitute for the final focused 60-test result.

## 17. Known Limitations

- actual Thermal hardware contract remains pending.
- sensor header word 0 semantics remain unverified.
- sender status can itself be lost; sender-side acquisition completeness is not always fully observable from Pi capture.
- sensor-internal generation versus ESP32 D_READY observation is not independently verified.
- Thermal-90 shape/dtype physical meaning, unit, encoding, orientation, FPS and invalid-pixel semantics remain unverified.
- device-domain model behavior and FULL_INT8 deployment remain unverified.
- Pi runtime load, long-run stability and latency remain unverified.
- temporal fall-event behavior remains unverified; `LYING` proxy is not a verified fall event.

## 18. What This PR Proves

- Latest tracked Thermal subsystem was synchronized into the team repository structure.
- SNTR V2 logical frame transport and fail-closed chunk identity/offset/length/CRC checks are implemented and software-tested.
- Thermal-90 capture tooling and compile-valid XIAO firmware are prepared.
- unverified header identity is separated from transport and verified sensor-counter identity.
- raw datagram checksum exact inventory and machine-readable sender telemetry are implemented and tested.
- offline model identity and non-production boundary are documented.

## 19. What This PR Does NOT Prove

| Claim | Status |
|---|---|
| Thermal-90 physical unit verified | `NO` |
| Thermal-90 orientation verified | `NO` |
| Thermal-90 actual FPS contract verified | `NO` |
| Header word 0 verified as sensor frame counter | `NO` |
| Sensor acquisition completeness verified | `NO` |
| Pi end-to-end latency validated | `NO` |
| FULL_INT8 production deployment validated | `NO` |
| Actual fall detection validated | `NO` |
| T-C completed | `NO` |

## 20. T-C0 Entry Prerequisites

T-C0는 작은 controlled `DEVICE_CONTRACT_PILOT`이 다음 evidence를 제공하면 시작할 수 있다.

- native/full-frame raw evidence
- session/frame provenance
- capture validator result
- capture source, device path 및 transport를 식별할 충분한 metadata

T-C0 시작 전에 native shape, dtype/byte encoding, temperature encoding/unit, orientation, effective FPS, invalid-pixel semantics, Pi latency 또는 device-domain model behavior가 이미 검증될 필요는 없다. 이것들은 T-C가 조사할 대상이다. Pilot evidence는 결론이 아니라 조사 가능한 진입 자료다.

정확한 다음 hardware action은 owner 승인 후 XIAO에 corrective firmware를 업로드하고 Pi collector를 먼저 실행한 다음, 새 session ID로 짧은 controlled Thermal-90 capture를 수행해 sender status, `raw_chunks/` exact inventory와 device contract fields를 함께 검증하는 것이다. 이 보고서 작성 과정에서는 해당 실험을 시작하지 않았다.

## 21. T-C Overall Validation Targets

T-C 동안 다음을 실제 evidence로 확립하거나 특성화해야 한다.

- actual native shape 및 dtype/byte encoding
- physical temperature meaning/conversion 및 actual orientation
- effective acquisition FPS, frame ordering 및 timing
- invalid-pixel semantics
- sensor → ESP32 → UDP → Pi transport integrity
- sender-side loss와 receiver-side loss의 구분
- Pi receive/decode/preprocess/inference behavior, latency 및 runtime load
- actual-device data를 frozen P1/model input contract에 mapping하는 방법
- FULL_INT8 device-domain behavior

순서는 `pilot evidence → T-C0 시작 → physical/device contract 조사 → frozen candidate compatibility 조사 → 후속 T-C 결론`이다. PR #22는 이 순서의 도구 준비이며 T-C0 완료가 아니다.

## 22. Lifecycle / Hard Boundary

```text
PR #22
TEAM-THERMAL-INTEGRATION
PRE-T-C DEVICE-CAPTURE PREPARATION
  -> owner review / merge
  -> DEVICE_CONTRACT_PILOT
  -> capture validator
  -> T-C0 actual device-contract investigation
  -> T-C device-domain validation
```

현재 위치는 첫 단계이며 `T_C_EXECUTED = NO`다. 이 PR에서 pilot, T-C0, model replacement 또는 hardware claim을 수행하지 않는다.

## 23. Final Git / PR State

- Repository: `jinsu1011/safenest-embedded-competition`
- Base SHA: `0fc2fd5be40f3a5714e738258183676f4adb1109`
- Branch: `integration/update-latest-thermal`
- Initial PR HEAD: `bc1802dee0348d8218a929d809d5a2fa1b593c06`
- Previous corrective HEAD before this addendum: `ec41e8741ee9d6c7ea70397794c806ef77bfb071`
- Corrective commit(s): listed in `git log origin/main..integration/update-latest-thermal` and PR #22 after publication
- Final HEAD: authoritative PR head shown by GitHub after corrective push
- PR: `#22`, retained as Draft pending owner review
- Merge: not performed and not authorized

Terminal classification: `PR22_CORRECTIVE_READY_FOR_OWNER_REVIEW` only after the corrective commit, final diff audit and PR description update. It must never be interpreted as `T_C_COMPLETE`, `THERMAL_DEVICE_VALIDATED` or `PRODUCTION_READY`.
