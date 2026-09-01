# SafeNest 센서 통합 관제

기존 `preview.html`에 관리자 인증, 공간/센서 관리 API, Raspberry Pi 데이터 수신, 실시간 SSE 반영, QR 전용 비회원 화면을 연결한 Node.js 서버입니다.

## 실행

```powershell
Copy-Item .env.example .env
pnpm install
pnpm start
```

브라우저에서 `http://localhost:3000`을 여세요. 개발용 초기 계정은 `admin / SafeNest123!`입니다. 실제 운영 전 `.env`의 `JWT_SECRET`, `ADMIN_PASSWORD`, `SENSOR_API_KEY`, `PUBLIC_BASE_URL`을 반드시 변경해야 합니다.

`preview.html`을 직접 더블클릭해도 개발용 계정으로 Mock 대시보드를 확인할 수 있습니다. 센서 API, 공간 저장, 실시간 갱신과 QR URL을 실제로 사용하려면 서버 방식으로 실행해야 합니다.

## 주요 URL

- `/`: 로그인과 관리자 통합 관제 화면
- `/admin`: 동일한 통합 화면으로 직접 접근
- `/guest/dashboard/A01`: 로그인 없는 A01 조회 전용 화면
- `/api/spaces/A01/qr`: A01 비회원 화면으로 연결되는 QR SVG
- `POST /api/sensor-data`: Raspberry Pi 센서 데이터 수신
- `/api/stream`: 실시간 Server-Sent Events 스트림

## 샘플 QR 이미지

`qr-codes` 폴더에 A01, B02, C03용 PNG와 SVG가 함께 있습니다. `pnpm generate:qr`로 다시 생성할 수 있으며, 외부 기기에서 스캔할 때는 `.env`의 `PUBLIC_BASE_URL`을 Raspberry Pi와 휴대폰에서 접근 가능한 서버 주소로 설정하세요.

## Raspberry Pi 전송 형식

```bash
curl -X POST http://SERVER_IP:3000/api/sensor-data \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_SENSOR_API_KEY" \
  -d '{
    "nodeId":"SN-A01",
    "co2":820,
    "temperature":25.4,
    "bodyTemperature":36.7,
    "breathRate":16,
    "motion":true,
    "occupied":true,
    "motionlessSeconds":0
  }'
```

로컬 테스트는 서버 실행 후 별도 터미널에서 `pnpm simulate`로 할 수 있습니다. `scripts/sensor-simulator.js`가 2초마다 A01 데이터를 전송합니다.

## ESP32 → Raspberry Pi 실시간 브리지

`.env`의 `RPI_BRIDGE_URL`이 Raspberry Pi LCD 서버를 가리키도록 설정합니다. 웹과 LCD 서버를 같은 Raspberry Pi에서 실행하면 기본값 `http://127.0.0.1:8080`을 그대로 사용합니다. 웹을 노트북에서 실행하면 `http://<라즈베리파이-IP>:8080`으로 변경합니다.

웹은 `/api/state`에서 호흡수·심박수·CO₂·PIR을 1초마다 읽고 `/api/thermal`의 80×62 원본 프레임을 관리자 및 QR 방문자 화면에 실시간 표시합니다. 전체 프로젝트를 Raspberry Pi에 복사한 경우 프로젝트 루트의 `SafeNest_대회_전체실행.sh`로 LCD 수신 서버와 웹을 함께 시작할 수 있습니다.

Raspberry Pi가 잠시 `waiting` 또는 `stale`을 반환해도 기본 30초 동안 마지막 정상 센서값과 정상/주의 상태를 유지합니다. `RPI_OFFLINE_GRACE_MS`가 지나도록 정상 패킷이 없을 때만 통신 오류로 전환됩니다.

대회용 QR은 노트북에서 `http://RPI_IP:3000/qr/A01`을 여세요. 이 페이지는 접속에 사용한 Raspberry Pi IP를 QR에 자동으로 넣으므로 예전에 생성한 PNG보다 안전합니다. `localhost`로 QR 페이지를 열면 휴대폰에서 접속할 수 없습니다.

실제 장치 없이 ESP32 TCP 통신과 열화상까지 시험하려면 Raspberry Pi LCD 서버가 실행된 상태에서 다음을 실행하세요.

```bash
npm run simulate:rpi
```

## API 권한

- 관리자 토큰 필요: 공간 목록/등록/수정/삭제, 이벤트 조회, 프로비저닝
- 센서 API 키 필요: 센서 데이터 수신
- 공개: 특정 공간 조회, 공간 QR, 비회원 대시보드, SSE

데이터는 개발 단계에서 `data/store.json`에 원자적으로 저장됩니다. 다중 서버 운영 시 PostgreSQL 같은 외부 DB로 교체하는 것이 좋습니다.
