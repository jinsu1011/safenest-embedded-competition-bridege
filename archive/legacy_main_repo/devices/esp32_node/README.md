# SafeNest ESP32 sensor node

This firmware runs on an ESP32-WROOM-32 (Arduino IDE board: ESP32 Dev Module). It reads the MR60BHA2 radar, SCD4x CO2 sensor, PIR input, and MI48 thermal camera, then sends sensor data to a Raspberry Pi.

## Change summary

- Synchronized the repository firmware with the tested ESP32-WROOM-32 sketch.
- Split sensor capture from network I/O. Sensor capture stays responsive while network reconnects and writes run in FreeRTOS tasks.
- Respiration, heart rate, CO2, and PIR scalar telemetry use the existing SafeNest packet format over TCP port 9000.
- 80 x 62 thermal frames use a separate UDP port 5005 so a large frame cannot block the scalar TCP stream.
- A 10 KiB thermal frame is split into nine datagrams no larger than 1200 bytes. Each datagram includes frame sequence, chunk index, byte offset, and CRC32.
- The thermal queue has one slot. When the network is slow, an old unsent frame is replaced by the newest frame.
- Unknown respiration, heart rate, and CO2 values are emitted as JSON null with valid flags instead of being changed to zero.
- Wi-Fi credentials and the Raspberry Pi address stay in secrets.h. secrets.h is ignored and must never be committed.

## Hardware wiring

| Device signal | ESP32-WROOM-32 pin |
|---|---|
| SCD4x SDA | GPIO21 |
| SCD4x SCL | GPIO22 |
| PIR OUT | GPIO13 |
| MR60BHA2 TX -> ESP32 RX2 | GPIO16 |
| MR60BHA2 RX <- ESP32 TX2 | GPIO17 |
| Thermal SCLK / MISO / MOSI | GPIO18 / GPIO19 / GPIO23 |
| Thermal CS / READY / RESET | GPIO27 / GPIO26 / GPIO25 |
| Common ground | ESP32 GND |

MR60BHA2 UART speed is 115200 baud. Sensor ground and ESP32 ground must be common. Check voltage levels before connecting a 5 V sensor signal to an ESP32 GPIO.

## Arduino IDE setup

1. Install the Espressif ESP32 board package.
2. Select ESP32 Dev Module and use 115200 baud in Serial Monitor.
3. Install the Sensirion I2C SCD4x and Seeed Arduino mmWave libraries.
4. Copy firmware/secrets.example.h to firmware/secrets.h and set the real values.

Example secrets.h:

~~~
#pragma once
constexpr char WIFI_SSID[] = "YOUR_2G_SSID";
constexpr char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";
constexpr char RPI_HOST[] = "192.168.0.50";
constexpr uint16_t RPI_PORT = 9000;
~~~

RPI_HOST is an IP address or DNS host only. Do not include http:// or a port suffix. ESP32 and Raspberry Pi must be on the same 2.4 GHz network. The real secrets.h is excluded by .gitignore.

## Transport overview

~~~
ESP32
  |-- TCP 9000 --> scalar telemetry JSON --> Raspberry Pi
  |-- UDP 5005 --> thermal frame chunks --> Raspberry Pi
~~~

The two channels use independent FreeRTOS tasks and sockets. A TCP reconnect cannot stop thermal capture or UDP transmission.

### TCP 9000: scalar telemetry

The firmware reconnects to RPI_HOST:RPI_PORT (default port 9000). Every message is a 16-byte SNST header followed by a JSON payload.

- magic: SNST
- version: 1
- type: 1
- flags: 0
- sequence: unsigned 32-bit big-endian
- payload_length: unsigned 32-bit big-endian

Example JSON:

~~~
{"schema":"safenest.telemetry.v1","device_id":"esp32-01",
 "seq":42,"uptime_ms":12345,"resp_rate_bpm":null,
 "heart_rate_bpm":null,"co2_ppm":820,"pir_motion":false,
 "valid":{"respiration":false,"heart":false,"co2":true}}
~~~

A null respiration or heart value means that MR60 has not produced a fresh valid measurement. It must not be interpreted as zero bpm.

### UDP 5005: thermal frames

UDP provides no connection handshake or retransmission. The Raspberry Pi receiver must reassemble and validate complete frames.

- UDP destination port: 5005
- Maximum datagram size: 1200 bytes
- Logical payload: 16-byte metadata plus 80 x 62 uint16 pixels = 9936 bytes
- Chunk payload: 1168 bytes
- Datagrams per frame: 9
- All integers use network byte order (big-endian)
- Every chunk repeats the same frame CRC32

UDP datagram header (32 bytes):

| offset | size | field | description |
|---:|---:|---|---|
| 0 | 4 | magic | ASCII SNTU |
| 4 | 1 | version | 1 |
| 5 | 1 | type | 2 (thermal uint16 big-endian) |
| 6 | 2 | header_length | 32 |
| 8 | 4 | frame_sequence | frame identifier |
| 12 | 2 | chunk_index | zero-based chunk index |
| 14 | 2 | chunk_count | 9 for this firmware |
| 16 | 4 | payload_length | 9936 |
| 20 | 4 | payload_offset | offset in logical payload |
| 24 | 2 | chunk_length | bytes after this header |
| 26 | 2 | reserved | 0 |
| 28 | 4 | crc32 | CRC32/IEEE of metadata plus all pixel bytes |

The 16-byte logical metadata is width=80, height=62, frame_sequence, uptime_ms, minimum_raw, and maximum_raw. The remaining 9920 bytes contain 4960 big-endian uint16 pixels. Raw values are preserved; the receiver converts them to Celsius.

A receiver must validate the header and all ranges, collect chunks by frame_sequence and payload_offset, then calculate CRC32 after every byte range is present. Drop the whole frame if a chunk is missing, a frame does not complete within the timeout (recommended 0.5 seconds), or CRC32 does not match. UDP does not guarantee order, uniqueness, or retransmission, so the receiver must handle reordering and duplicates.

## Health log fields

Example:

~~~
[health] wifi=up rpi=192.168.137.249 resp=nan heart=nan co2=875
pir=0 thermal_frames=52 udp_sent=0 udp_failed=45 free_heap=123792
~~~

- wifi: ESP32 Wi-Fi link state.
- rpi: configured RPI_HOST. A wrong address breaks both TCP and UDP.
- resp / heart: MR60 respiration and heart rate. nan means no valid fresh value.
- co2: latest SCD4x value in ppm.
- pir: GPIO13 input. Zero can be normal when there is no motion.
- thermal_frames: number of thermal frames captured over SPI.
- udp_sent / udp_failed: completed thermal frame send results.
- free_heap: free ESP32 heap bytes. A stable value is not a short-circuit indicator.

If udp_sent stays at zero while udp_failed increases, check RPI_HOST, network/subnet, the UDP receiver, and firewall before suspecting a sensor short.

On the Raspberry Pi:

~~~
hostname -I
sudo ss -lunp | grep 5005
sudo ufw allow 5005/udp
~~~

The receiver must bind UDP 5005 on 0.0.0.0 or the Raspberry Pi Wi-Fi address. The legacy integration/pi_lcd/server.py in this repository is TCP-only; use a runtime with an SNTU UDP reassembler or add one before expecting thermal frames.

## Verification

- Arduino IDE Verify with ESP32 Dev Module
- Serial Monitor at 115200 baud
- Confirm Wi-Fi and health logs
- Check TCP 9000 and UDP 5005 independently on the receiver
- Do not include secrets.h, Wi-Fi passwords, or private credentials in a commit
