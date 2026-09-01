# SafeNest LCD Showcase

라즈베리파이 1024×600 LCD 연출 전용 실행 폴더.

- `display.html`: 기존 실시간 LCD 화면 로직 복사본
- `common.css`: 요청받은 CSS 원본
- `server.py`: 정적 파일 제공 및 `127.0.0.1:8000` API 프록시
- `start_showcase.sh`: 새 Chromium 프로필·100% 배율·1024×600 키오스크 실행
- `stop_showcase.sh`: 연출용 서버와 Chromium만 종료

```bash
cd /home/sandi/safenest-team-main/LCD_Showcase
./start_showcase.sh
```

상태 확인:

```bash
curl http://127.0.0.1:8090/health
curl http://127.0.0.1:8090/api/state
pgrep -af 'chromium.*8090/display.html'
```

## 주의 화면 수동 TTS

LCD가 `주의` 화면일 때 연결된 키보드의 물리 `A`–`I` 키로 기존 녹음 문구를 재생한다.
대소문자와 한/영 입력 상태는 관계없다.
다른 화면의 키 입력은 무시되며, 새 키를 누르면 진행 중인 showcase 음성을 교체한다.

| 키 | 녹음 문구 |
|---|---|
| A | 낙상 위험 |
| B | 무호흡 위험 |
| C | CO₂ 위험 |
| D | 호흡 이상 주의 |
| E | CO₂ 주의 |
| F | 장시간 무움직임 주의 |
| G | 열화상 이상 주의 |
| H | 일반 주의 |
| I | 일반 위험 |

이 기능은 `LCD_Showcase` 서버에서만 동작하며 실시간 센서 TTS의 판정·쿨다운 상태를 변경하지 않는다.
