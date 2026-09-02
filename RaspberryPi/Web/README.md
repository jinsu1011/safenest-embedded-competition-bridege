# RaspberryPi/Web

SafeNest의 **브라우저 화면 3종**이다. 정적 파일만 있고 서버 코드는 없다 —
Raspberry Pi에서 도는 FastAPI 백엔드(`RaspberryPi/Runtime/backend/app.py`)가
이 디렉터리를 그대로 서빙하고, 화면은 백엔드의 REST/WebSocket을 읽어 그린다.

```
브라우저  ──HTTP/WS──▶  FastAPI :8000  ──▶  Sensor State / Risk Formula V1
   ▲                         │
   └──── 이 디렉터리의 정적 자산 ─┘
```

## 화면 3종

| 화면 | 주소 | 진입 파일 | 용도 |
|---|---|---|---|
| **관리자 포털** | `http://<PI_IP>:8000/admin` | `portal/preview.html` + `portal/admin-api.js` + `portal/thermal-client.js` | 로그인, 공간 관리, 실시간 열화상, 비상 조치 |
| **관제 대시보드** | `http://<PI_IP>:8000/dashboard` | `index_final.html` + `app_final.js` + `styles_final.css` | 센서·AI·위험도 종합 관제 |
| **게스트 화면** | `http://<PI_IP>:8000/guest/dashboard/<space_id>` | `guest/index.html` | QR로 접속하는 읽기 전용 요약 |

`index.html` · `app.js` · `styles.css` 는 **데모 모드 전용** 대시보드다.
`SAFENEST_DEMO_MODE=1` 로 기동했을 때만 `/dashboard` 가 이 세트를 서빙하고,
평시(기본값)에는 `index_final.*` 세트가 나간다 (`backend/app.py:160`).

## 관리자 로그인

계정은 파일이 아니라 **환경변수**로 설정한다 (`backend/portal.py:112-113`).
둘 중 하나라도 비어 있으면 `/admin` 로그인은 **항상 거부**된다 (fail-closed).
저장소에는 기본 계정이 없다.

```bash
# Raspberry Pi의 저장소 루트에 .env 를 만든다 (.env 는 git 추적 대상이 아니다)
SAFENEST_ADMIN_ID=admin
SAFENEST_ADMIN_PASSWORD=12341234
SAFENEST_AUTH_SECRET=<임의의 긴 문자열>
```

현재 시연용 Raspberry Pi에는 위 값이 그대로 설정되어 있다 — **ID `admin` / PW `12341234`**.

인증 흐름: `POST /api/auth/login` 에 `{"id", "password"}` 를 보내면 서명 토큰을 받고
(유효기간 12시간), 이후 보호된 API 는 그 토큰으로 인가된다.
`SAFENEST_AUTH_SECRET` 을 비워 두면 프로세스마다 새 서명 키가 생성되어 재기동 시 토큰이 무효가 된다.

## 파일

| 경로 | 역할 |
|---|---|
| `portal/preview.html` | 관리자 포털 단일 페이지 (로그인 폼 포함, 자격증명은 미포함) |
| `portal/admin-api.js` | 포털의 API 호출·토큰 보관·DOM 갱신 |
| `portal/thermal-client.js` | `/api/thermal/` 프레임을 80×62 캔버스로 렌더 |
| `index_final.html` · `app_final.js` · `styles_final.css` | 평시 관제 대시보드 |
| `index.html` · `app.js` · `styles.css` | 데모 모드 전용 대시보드 (119 모의 신고 UI 포함) |
| `guest/index.html` | QR 게스트 요약 화면 |
| `audio/` | 경보 음원과 출처 표기 |
| `vendor/chart.js/` | Chart.js 로컬 사본. **외부 CDN을 쓰지 않는다** — 현장이 오프라인이어도 차트가 뜬다 |

## 알아둘 것

- 화면은 위험도를 **계산하지 않는다.** 백엔드가 게시한 `risk_level` · `reasons` 를 표시만 한다.
  판단 로직은 `RaspberryPi/Runtime/risk/formula_v1.py` 한 곳에 있다.
- 열화상 온도는 **보정 전 값**이다 (`temperature_calibrated: false`). 대시보드는 °C 를 표시하지 않고,
  게스트 화면은 "온도 보정 미적용" 을 함께 표기한다.
- 외부 네트워크 자산 참조가 없다. 폰트·스크립트·스타일 전부 로컬이다.

## 관련 문서

- 상위: [`../../README.md`](../../README.md)
- 운영/기동: [`../../docs/operations/PI_RUNBOOK.md`](../../docs/operations/PI_RUNBOOK.md)
- LCD 패널: [`../LCD/LCD_KIOSK_KO.md`](../LCD/LCD_KIOSK_KO.md)
- 위험도 산식: [`../Runtime/risk/risk_formula_v1.json`](../Runtime/risk/risk_formula_v1.json)
