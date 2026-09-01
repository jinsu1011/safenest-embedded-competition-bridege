# VS Code로 Raspberry Pi SSH 접속하기

## 1. Raspberry Pi에서 SSH 활성화

모니터와 키보드를 연결할 수 있으면 Raspberry Pi 터미널에서 실행합니다.

```bash
sudo raspi-config
```

`Interface Options > SSH > Yes`를 선택한 뒤 다음으로 상태를 확인합니다.

```bash
sudo systemctl enable --now ssh
hostname -I
```

화면 없이 Raspberry Pi Imager로 SD 카드를 만들 때는 고급 설정에서 사용자 이름·비밀번호·Wi-Fi·SSH 활성화를 미리 설정할 수 있습니다.

## 2. 노트북 준비

1. 노트북과 Raspberry Pi를 같은 Wi-Fi `YOUR_2_4_GHZ_WIFI_SSID`에 연결합니다.
2. VS Code를 설치합니다.
3. Extensions에서 Microsoft의 `Remote - SSH` 확장을 설치합니다.

## 3. VS Code에서 접속

1. `Ctrl+Shift+P`를 누릅니다.
2. `Remote-SSH: Connect to Host...`를 선택합니다.
3. `Add New SSH Host...`를 선택합니다.
4. 다음처럼 입력합니다. 사용자 이름과 IP는 실제 값으로 바꿉니다.

```text
ssh sandi@192.168.0.50
```

5. SSH 설정 파일로 Windows의 기본 사용자 설정 파일을 선택합니다.
6. 다시 `Remote-SSH: Connect to Host...`에서 방금 등록한 호스트를 선택합니다.
7. 처음 접속할 때 운영체제는 `Linux`, 호스트 키 확인은 `Continue`를 선택하고 Raspberry Pi 사용자 비밀번호를 입력합니다.

왼쪽 아래에 `SSH: ...`가 표시되면 원격 접속된 상태입니다. `File > Open Folder`에서 `/home/sandi` 또는 프로젝트 폴더를 엽니다.

## 4. 터미널 사용과 파일 복사

VS Code 메뉴에서 `Terminal > New Terminal`을 누르면 Raspberry Pi에서 실행되는 원격 터미널이 열립니다.

저장소를 Raspberry Pi로 가져오는 가장 간단한 방법은 원격 터미널에서 직접 clone하는 것입니다.

```bash
cd ~
git clone https://github.com/jinsu1011/safenest-embedded-competition.git
```

네트워크가 막혀 있다면 노트북에서 ZIP으로 묶어 `scp`로 옮긴 뒤 압축을 풀어도 됩니다.

```powershell
scp safenest-embedded-competition.zip sandi@192.168.0.50:~/
```

실행에 사용하는 두 폴더를 홈으로 복사합니다. 저장소 경로는 `integration/pi_lcd`와 `integration/web`이지만, 실행 환경의 폴더 이름은 실측 검증된 절차를 그대로 유지해 `~/raspberry_pi_lcd`와 `~/SafeNest_Web`을 씁니다.

```bash
cp -a ~/safenest-embedded-competition/integration/pi_lcd ~/raspberry_pi_lcd
cp -a ~/safenest-embedded-competition/integration/web ~/SafeNest_Web
```

## 5. 접속이 안 될 때

- `Connection timed out`: 같은 Wi-Fi인지, IP가 바뀌지 않았는지 확인
- `Connection refused`: Raspberry Pi에서 SSH 서비스 활성화 확인
- `Permission denied`: 사용자 이름과 비밀번호 확인
- 저장된 호스트 키 오류: Raspberry Pi OS를 다시 설치해 키가 바뀐 경우 `ssh-keygen -R 192.168.0.50` 실행 후 재접속
- IP를 모름: 공유기 연결 목록을 보거나 Raspberry Pi에서 `hostname -I` 실행

대회 중 IP 변경을 줄이려면 공유기에서 Raspberry Pi MAC 주소에 DHCP 예약을 설정하는 것이 좋습니다.

