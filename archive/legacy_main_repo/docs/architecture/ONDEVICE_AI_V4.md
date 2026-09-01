# SafeNest V4 On-Device AI 최종 배포 패키지

본 디렉터리는 **SafeNest V4 온디바이스 AI 파이프라인**의 전체 소스 코드, 양자화 TFLite 모델, 전처리 데이터셋, 위험도 융합 엔진, 센서 어댑터 및 유닛 테스트 스위트를 포함하는 최상위 배포 폴더입니다.

---

## 1. 팀원 인수인계 설명서 (통합 프롬프트 모음)

팀원들이 각자 담당하는 센서 및 파트(Thermal, mmWave, CO2, PIR, 라즈베리 파이 5, 웹 UI)에 즉시 복사하여 적용할 수 있는 통합 인수인계 설명서는 아래 단일 문서에 작성되어 있습니다:

👉 **[통합 팀원 인수인계 가이드](../../ondevice_ai/docs/TEAM_HANDOFF_GUIDE.md)**

---

## 2. 디렉터리 구조

```text
./
├── config/                  # 센서, 모델, MR60 처리, 위험도 설정
├── src/
│   ├── inference/           # TFLite 추론기와 모델 레지스트리
│   ├── sensors/             # 센서 드라이버, Mock 및 stream/CSV adapter
│   ├── risk/                # 멀티센서 위험도 융합과 fallback
│   ├── integrated_node/     # JSON Lines 통합 실행 노드
│   ├── training/            # Thermal 학습·전처리 코드
│   └── tools/               # 시각화와 검증 유틸리티
├── models/                  # INT8 TFLite와 model_manifest.json
├── datasets/                # 전처리 NPZ와 데이터 매니페스트
├── docs/                    # 운용·AI·구조·기획 문서
├── tests/                   # unittest 및 benchmarks
├── README.md                # 저장소 안내 문서
├── requirements.txt     # 전체 파이썬 의존성 패키지
├── requirements-pi.txt  # 라즈베리 파이 5 전용 경량 의존성
└── requirements-mac.txt # macOS 테스트 전용 의존성
```

---

## 3. 위험도 융합 수식 & 산출 기준

온디바이스 위험도 점수 $R$은 4개 센서 채널의 가중 합산으로 산출됩니다:

$$R = 100 \times (0.35 S_1 + 0.35 S_2 + 0.15 S_3 + 0.15 S_4)$$

- **$S_1$ (mmWave)**: 호흡 이상 및 무호흡 위험도 $[0.0, 1.0]$
- **$S_2$ (CO2)**: 재실 및 농도 상승 위험도 $[0.0, 1.0]$
- **$S_3$ (PIR)**: 움직임 및 장기 미움직임 위험도 $[0.0, 1.0]$
- **$S_4$ (Thermal-44)**: 열화상 기반 사람 낙상 위험도 $[0.0, 1.0]$

### 비상 오버라이드 (Emergency Overrides)
- **Thermal-44 낙상 감지 ($S_4 = 1.0$)** 또는 별도 기준 장치/검증 경로가 `apnea_verified=true`로 확정한 **검증된 mmWave 무호흡**만 가중 합산을 우회해 **$R = 100.0$ (`DANGER`)** 경보를 발령합니다.
- MR60의 `0`, 결측, timeout, 부재 및 미검증 AI 후보는 무호흡으로 승격하지 않습니다.

---

## 4. 실행 방법

### (1) 실시간 스트리밍 노드 실행 (Mock 모드)
```bash
python3 ondevice_ai/src/integrated_node/run_node.py --mode mock
```

### (2) 실기기 라즈베리 파이 5 센서 연동 실행
```bash
python3 ondevice_ai/src/integrated_node/run_node.py --mode real
```

### (3) 전체 유닛 & 통합 테스트 실행
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

MR60 ESP 실측 연동과 재생 검증은 [MR60 통합 가이드](../../ondevice_ai/docs/MR60_INTEGRATION.md)를 따릅니다.
