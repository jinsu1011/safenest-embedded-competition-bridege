# mmWave 오프라인 감사 (M-C0)

`jinsu1011/safenest-embedded-competition` 브랜치 `codex/mmwave-m-c0-correspondence`
(PR #21)의 mmWave M-C0 correspondence audit 작업물입니다. Thermal·CO2 연구 워크스페이스와
같은 성격이며 **Pi 런타임의 일부가 아닙니다.**

## 구성

| 경로 | 내용 |
| --- | --- |
| `datasets/mmwave/manifests/M-C0_correspondence_audit/` | M-C0 감사 매니페스트 |
| `scripts/mmwave_m_c0_correspondence_audit.py` | correspondence 감사 실행기 |
| `scripts/mmwave_m_c0_freshness_reaudit.py` | phase freshness 독립 재감사 |
| `tests/test_mmwave_m_c0_freshness_guards.py` | freshness 추정기 가드 테스트 |
| `docs/reports/` | M-C0 실행 로그, standalone 리포트, M-C1 요구사항 초안 |

## 실행

이 디렉터리를 작업 루트로 삼습니다.

```bash
cd research/mmwave_ai
python -m unittest tests.test_mmwave_m_c0_freshness_guards
python scripts/mmwave_m_c0_correspondence_audit.py --help
```

감사 스크립트는 기본 실행 시 `BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`를 반환합니다.
이는 설계된 동작이며, 실제 판정에는 `--evidence-root`로 증거 경로를 명시해야 합니다.

> 감사 스크립트의 기본 `--output-dir`은 매니페스트 폴더입니다. 인자 없이 실행하면
> `m_c0_summary.json`을 덮어쓰므로, 검증 목적이라면 `--output-dir`을 임시 경로로 지정하십시오.

## 증거 데이터 위치

스크립트가 참조하는 `devices/mmwave/...` 후보 경로는 이 저장소에서
`archive/legacy_main_repo/devices/mmwave/` 아래에 있습니다. 기본 실행 경로에는
영향이 없으며(증거 루트는 항상 명시 전달), 실제 감사 시 해당 경로를
`--evidence-root` / `--pilot-evidence-root`로 넘기십시오.
