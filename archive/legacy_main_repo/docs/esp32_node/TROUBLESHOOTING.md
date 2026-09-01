# ESP32 sensor node troubleshooting

## Health fields

| Log or field | Meaning |
|---|---|
| wifi=down | ESP32 is not connected to the access point |
| connecting to RPI_HOST:9000 repeats | TCP listener, RPI_HOST, firewall, or subnet is wrong |
| resp=nan, heart=nan | MR60 has no fresh valid measurement; check UART wiring, power, and sensor orientation |
| CO2 value updates | SCD4x I2C and periodic measurement are working |
| pir=0 stays constant | No motion, or check PIR OUT/GND/power/GPIO13 wiring |
| thermal_frames increases | Thermal SPI capture is working |
| udp_sent=0, udp_failed increases | UDP 5005 delivery failed or receiver is not running |
| free_heap is stable | Available ESP32 RAM; it is not a sensor state or short-circuit flag |

## TCP checks

On Raspberry Pi:

~~~
hostname -I
sudo ss -ltnp | grep 9000
~~~

RPI_HOST in secrets.h must match the Raspberry Pi Wi-Fi address. A 192.168.137.x address may belong to a Windows hotspot or virtual adapter; confirm that the Raspberry Pi is actually on that subnet.

## UDP checks

~~~
sudo ss -lunp | grep 5005
sudo ufw allow 5005/udp
sudo tcpdump -ni any udp port 5005
~~~

If tcpdump sees nothing, ESP32 and Raspberry Pi are likely on different networks or RPI_HOST is wrong. If datagrams arrive but no frame completes, inspect receiver chunk timeout, duplicate handling, CRC32, and payload_offset validation.

## Sensor checks

- MR60BHA2: sensor TX -> ESP32 RX GPIO16, sensor RX -> ESP32 TX GPIO17, UART 115200, common GND
- PIR: OUT must be GPIO13 with valid power and GND
- SCD4x: SDA/SCL 21/22, I2C address 0x62
- Thermal: CS/READY/RESET 27/26/25, SPI 18/19/23, stable power and short signal wires

If every sensor is simultaneously zero or nan, check power, GND, pin map, and board selection (ESP32 Dev Module) before assuming a short. Suspect power or memory faults when free_heap continuously falls or the ESP32 repeatedly reboots.
