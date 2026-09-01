# ESP32-WROOM-32 Arduino IDE setup

## Prerequisites

- ESP32-WROOM-32 / ESP32 Dev Module
- A USB data cable
- Arduino IDE 2.x
- 2.4 GHz Wi-Fi
- MR60BHA2, SCD4x, PIR, and MI48 thermal sensor with common ground

## Board and libraries

1. Install the Espressif Systems ESP32 board package from Boards Manager.
2. Select Tools > Board > esp32 > ESP32 Dev Module.
3. Install Sensirion I2C SCD4x and Seeed Arduino mmWave from Library Manager.
4. Select the serial port and open Serial Monitor at 115200 baud.

WiFi, Wire, SPI, and WiFiUDP are included with the ESP32 board package.

## Sketch and secrets.h

Create secrets.h next to devices/esp32_node/firmware/esp32_sensor_node.ino:

~~~
#pragma once
constexpr char WIFI_SSID[] = "YOUR_2G_SSID";
constexpr char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";
constexpr char RPI_HOST[] = "192.168.0.50";
constexpr uint16_t RPI_PORT = 9000;
~~~

RPI_HOST must be an IP address or DNS host without an HTTP scheme or port suffix. The thermal UDP port is the firmware constant THERMAL_UDP_PORT=5005; do not redeclare it in secrets.h.

## Pin map

- SCD4x: SDA GPIO21, SCL GPIO22
- PIR OUT: GPIO13
- MR60BHA2: sensor TX -> ESP32 GPIO16, sensor RX <- ESP32 GPIO17
- Thermal SPI: SCLK GPIO18, MISO GPIO19, MOSI GPIO23, CS GPIO27, READY GPIO26, RESET GPIO25

## Upload

1. Run Verify.
2. Run Upload.
3. If upload stops at Connecting..., hold the BOOT button while starting upload.
4. Open Serial Monitor at 115200 baud after upload.

Expected startup includes:

~~~
SafeNest ESP32 sensor node starting
[thermal] ready: ...
[co2] ready: first measurement takes about 5 seconds
[wifi] connecting to YOUR_SSID asynchronously
~~~

## Verify both network channels

- TCP 9000: scalar telemetry JSON. Confirm a TCP listener is listening.
- UDP 5005: thermal datagrams. Confirm a UDP listener is bound.

On Raspberry Pi:

~~~
hostname -I
sudo ss -ltnp | grep 9000
sudo ss -lunp | grep 5005
sudo ufw allow 9000/tcp
sudo ufw allow 5005/udp
~~~

In the ESP32 health log, thermal_frames is the capture count and udp_sent/udp_failed are frame send results. If thermal_frames grows while udp_failed grows, check RPI_HOST, listener, firewall, and Wi-Fi subnet before suspecting a camera short.
