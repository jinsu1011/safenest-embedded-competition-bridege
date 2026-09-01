# ESP32 and LCD runtime integration notes

## Current transport paths

The ESP32 uses two independent paths:

- TCP 9000: scalar telemetry JSON once per second for MR60 respiration/heart rate, SCD4x CO2, and PIR.
- UDP 5005: 80 x 62 thermal raw frames in nine SNTU v1 chunks.

TCP reconnect/write and UDP thermal transmission run in separate FreeRTOS tasks. LCD runtime TCP reconnects cannot stop thermal capture.

## Raspberry Pi receiver requirements

The TCP receiver reads the SNST header and payload_length bytes. The UDP receiver must:

1. Validate SNTU magic, version, type, and header_length.
2. Store chunks by frame_sequence and payload_offset.
3. Calculate CRC32/IEEE after every byte range is present.
4. Forward only complete CRC-valid frames to LCD/API and the logger.
5. Drop missing, conflicting, CRC-invalid, and timed-out frames and expose stale state.

Do not wait for thermal frames on the TCP listener. Run a TCP 9000 listener and a UDP 5005 listener.

## Legacy LCD server compatibility

The legacy integration/pi_lcd/server.py currently receives SNST TCP 9000 only. With that server alone, scalar telemetry can appear but UDP thermal frames are not consumed. Add an SNTU v1 UDP reassembler or use a runtime that includes one before enabling the thermal display.

Use these documents as the source of truth:

- devices/esp32_node/README.md
- docs/esp32_node/COMMUNICATION_PROTOCOL.md
- docs/esp32_node/TROUBLESHOOTING.md

## Value semantics

A null respiration, heart rate, or CO2 field means no valid fresh measurement. Keep it stale/waiting and do not convert it to zero. PIR false can be a normal no-motion state.

Thermal pixels remain raw uint16 until the analysis side converts them to Celsius. Do not repeat an incomplete frame as a new measurement.

## Validation checklist

- thermal_frames increases in the ESP32 health log
- udp_sent increases and udp_failed does not
- TCP 9000 is listening
- UDP 5005 is listening
- RPI_HOST is the current Raspberry Pi Wi-Fi address
- TCP 9000 and UDP 5005 are allowed by the firewall
- UDP frame reassembly passes CRC32 and 80 x 62 shape checks
