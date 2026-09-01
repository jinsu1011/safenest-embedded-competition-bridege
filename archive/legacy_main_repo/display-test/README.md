# SafeNest LCD 원격 제어

Raspberry Pi의 LCD에는 SafeNest 상태 화면을 전체화면으로 표시하고, 같은 Wi-Fi의 노트북에서는 웹 제어 페이지로 6가지 시나리오를 수동 전환합니다.

## 팀원용 문서

- 배선부터 실행·검증·종료까지: [`LCD_BUZZER_TEAM_GUIDE.html`](LCD_BUZZER_TEAM_GUIDE.html)
- Git 업로드 명령과 PR 본문: [`GIT_UPLOAD_GUIDE.md`](GIT_UPLOAD_GUIDE.md)

> 현재 화면의 CO₂·온도·움직임 수치는 실제 센서 입력이 아닌 수동 시연용 예시값입니다.

## 화면 주소

- Raspberry Pi LCD: `http://127.0.0.1:8080/display`
- 노트북 제어: `http://192.168.1.44:8080/control`

## Raspberry Pi로 복사

Windows PowerShell에서 이 프로젝트의 상위 폴더로 이동한 뒤 실행합니다.

```powershell
scp -r .\safenest_lcd_remote sandi@192.168.1.44:~/
```

비밀번호 입력 중에는 문자가 표시되지 않습니다.

## Raspberry Pi에서 실행

```bash
ssh sandi@192.168.1.44
cd ~/safenest_lcd_remote
bash start_lcd.sh
```

## 긴급 피에조 부저

2핀 수동 피에조 부저는 BCM GPIO18을 사용합니다. 사진처럼 USB 포트가 아래쪽일 때 다음과 같이 연결합니다.

| 부저 | 물리 핀 | GPIO 헤더 위치 |
|---|---:|---|
| `+` 긴 다리 | 12번, GPIO18 | 위에서 6행, 바깥쪽 2열 |
| `-` 짧은 다리 | 14번, GND | 위에서 7행, 바깥쪽 2열 |

LCD 상태가 `emergency`가 되면 880 Hz 경보음이 계속 울리고, 다른 상태로 바꾸거나 서버를 종료하면 즉시 꺼집니다. 상태 확인:

```bash
curl -s http://127.0.0.1:8080/health
```

출력의 `buzzer`에서 `"available": true`, `"pin_bcm": 18`을 확인합니다. 실제 연동 시험:

```bash
curl -s -X POST http://127.0.0.1:8080/api/state -H 'Content-Type: application/json' -d '{"state":"emergency"}'
sleep 2
curl -s -X POST http://127.0.0.1:8080/api/state -H 'Content-Type: application/json' -d '{"state":"normal-empty"}'
```

부저를 사용하지 않고 서버만 시험하려면 다음처럼 직접 실행할 수 있습니다.

```bash
python3 server.py --disable-buzzer
```

출력된 노트북 제어 주소를 노트북 브라우저에서 엽니다. 버튼 또는 숫자키 `1`~`6`으로 LCD 상태를 전환할 수 있습니다.

## 종료

```bash
cd ~/safenest_lcd_remote
bash stop_lcd.sh
```

서버 기록은 `logs/server.log`, LCD 브라우저 기록은 `logs/chromium.log`에 저장됩니다.

`start_lcd.sh`는 Raspberry Pi의 `/run/user/<uid>/wayland-0` 소켓을 확인해 Wayland(`labwc`)와 X11 실행 방식을 자동으로 선택합니다. Raspberry Pi 5의 Chromium GPU 프로세스 충돌을 피하기 위해 키오스크는 CPU 소프트웨어 렌더링으로 실행됩니다.

## 문제 확인

LCD가 뜨지 않지만 제어 페이지가 열리는 경우:

```bash
cat ~/safenest_lcd_remote/logs/chromium.log
command -v chromium
echo "$DISPLAY"
```

서버가 열리지 않는 경우:

```bash
cat ~/safenest_lcd_remote/logs/server.log
```
