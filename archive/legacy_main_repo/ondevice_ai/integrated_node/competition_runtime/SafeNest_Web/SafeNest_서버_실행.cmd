@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "SAFENEST_NODE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"

if not exist "%SAFENEST_NODE%" (
  echo Node.js를 찾을 수 없습니다.
  echo Node.js를 설치한 뒤 다시 실행하세요.
  pause
  exit /b 1
)

echo SafeNest 서버를 시작합니다.
echo PC: http://localhost:3000
echo QR: http://172.21.161.165:3000
echo 이 창을 닫으면 QR 접속도 종료됩니다.
start "" "http://localhost:3000"
"%SAFENEST_NODE%" server.js
pause
