# M-N10 측정 프로토콜 공유 (캡처 아직 안 함)

- 날짜: 2026-08-18
- 대상: mmWave 센서 담당 / 팀원
- 상태: **규칙만 공유**. 사람 측정은 시작하지 않음. `CAPTURE_NOT_PERFORMED`

팀 `main`에는 이 규칙이 없었습니다. 원본은 상류 AI 저장소 열린 PR입니다.

```text
https://github.com/sheepmeat/test/pull/110
source SHA  4b3da694df237ca56ff5b58e7dd92df2ad8f633e
```

## 이번 주 할 일 / 하지 말 일

이번 주는 **6명 모집·숨 참기·독립 호흡 센서 구매가 아닙니다.**

이미 되는 MR60 캡처(`breath_phase`, `ts_monotonic_ms`, `phase_age_ms`, presence)를
시스템에 붙이는 일이 먼저입니다. CAP-0~CAP-3 세션은 그 경로의 증거로 쓰면 됩니다.

아래 문서는 **나중에** 정식 다인 측정을 할 때 시험지입니다. 지금 SOP로 맞추지 마십시오.

## 읽을 파일 (모두 `RaspberryPi/Ondevice_AI/` 아래)

| 파일 | 내용 |
| --- | --- |
| `docs/mmwave/20260818_SafeNest_mmWave_M-N10_Targeted_Real_Device_Capture_01.md` | 영어 프로토콜 설명 |
| `config/mmwave/m_n10_capture_protocol_lock.json` | 잠긴 규칙 JSON |
| `datasets/mmwave/manifests/m_n10_capture_manifest.json` | 캡처 안 함 표시 |
| `datasets/mmwave/manifests/m_n10_subject_partition.json` | 사람 나누기 규칙만 (배정 0명) |

나중에 쓸 요지만:

- 조건당 쓸 수 있는 구간 **최소 120초** (지금 4분 세션은 그 이상이라 충분)
- 조건 A 편안한 호흡 / B 조금 빠른 호흡(큐는 정답 아님) / C 자리 옮겨 다시
- 숨 참기 강제 없음. APNEA는 공개 110명 + (별도 승인된 짧은 pause만) 레퍼런스
- 정답 센서는 Movesense 가슴 가속도계가 우선. 레이더 호흡수는 정답 아님
- `SUBJ-001`은 새 사람이 아님. 6명은 나중 성적표 최소값, 목표는 8명
- 빈 방은 무호흡 정답이 아님. presence gate용

원본 raw는 Git에 넣지 않습니다. 로컬 예정 위치는 `datasets/mmwave/raw/m_n10/` 입니다.
