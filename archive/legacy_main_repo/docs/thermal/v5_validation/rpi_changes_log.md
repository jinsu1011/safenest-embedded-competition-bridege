# 라즈베리파이 환경 변경 사항 기록 (RPi Changes Log)

본 문서는 Thermal-44 V5 Real Validation 검증을 진행하며 라즈베리파이 5에 적용된 환경 변화(라이브러리 설치, 폴더 생성 등)를 기록합니다.

## 1. 디렉토리 및 파일 생성
- **생성된 경로:** `~/Thermal_V5_Validation/scripts`
- **추가된 파일:** `01_capture_raw_frames.py` (TCP 포트 9000 열화상 데이터 수신 및 파싱 검증용)

## 2. 파이썬 환경 및 라이브러리 설치
- **설치된 패키지:** `ai-edge-litert` (버전 2.1.6)
- **설치 목적:** 라즈베리파이 최신 OS(Python 3.11+) 환경에서 `tflite-runtime` 지원 중단에 따른 대안 패키지. 구글의 최신 On-Device AI 추론 라이브러리로 설치되었으며, 기존 `thermal_interpreter.py`와 완벽히 호환됩니다.
- **설치 명령어:** `pip install ai-edge-litert`
