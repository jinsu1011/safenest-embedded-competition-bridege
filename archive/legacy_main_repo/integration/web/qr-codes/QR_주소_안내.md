# QR 연결 주소

- 밀폐공간 A-01: `http://172.21.161.165:3000/guest/dashboard/A01`
- 통학차량 B-02: `http://172.21.161.165:3000/guest/dashboard/B02`
- 창고 C-03: `http://172.21.161.165:3000/guest/dashboard/C03`

휴대폰과 서버 PC가 같은 Wi-Fi에 연결되어 있고 SafeNest 서버가 실행 중이어야 합니다. PC의 Wi-Fi IPv4 주소가 변경되면 `.env`의 `PUBLIC_BASE_URL`을 수정하고 `pnpm generate:qr`로 QR을 다시 생성하세요.
