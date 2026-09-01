# SafeNest ESP32 communication protocol v1

This document defines the two transport channels between the ESP32-WROOM-32 firmware and the Raspberry Pi.

## Channels

| Data | Transport | Port | Direction |
|---|---|---:|---|
| Respiration/heart/CO2/PIR JSON | TCP | 9000 | ESP32 -> Raspberry Pi |
| 80 x 62 thermal frame | UDP | 5005 | ESP32 -> Raspberry Pi |
| LCD/API | HTTP | 8080 | Raspberry Pi local |

TCP and UDP use the same Wi-Fi link but independent tasks and sockets. A TCP reconnect does not stop the UDP capture task.

## TCP scalar telemetry

After connecting to the TCP peer, the firmware sends a 16-byte header followed by a JSON payload about once per second. TCP does not preserve message boundaries; the receiver must read exactly 16 header bytes and then exactly payload_length bytes.

| offset | size | field | value |
|---:|---:|---|---|
| 0 | 4 | magic | ASCII SNST |
| 4 | 1 | version | 1 |
| 5 | 1 | type | 1 |
| 6 | 2 | flags | 0 |
| 8 | 4 | sequence | unsigned 32-bit, big-endian |
| 12 | 4 | payload_length | unsigned 32-bit, big-endian |

The JSON schema is safenest.telemetry.v1. Missing sensor data is represented by JSON null and a false valid flag.

## UDP thermal frame v1

### Datagram header

Each UDP datagram contains a 32-byte header followed by chunk bytes.

| offset | size | field | value/validation |
|---:|---:|---|---|
| 0 | 4 | magic | SNTU |
| 4 | 1 | version | 1 |
| 5 | 1 | type | 2 |
| 6 | 2 | header_length | 32 |
| 8 | 4 | frame_sequence | frame identifier |
| 12 | 2 | chunk_index | 0 through chunk_count-1 |
| 14 | 2 | chunk_count | 9 |
| 16 | 4 | payload_length | 9936 |
| 20 | 4 | payload_offset | offset from start of logical payload |
| 24 | 2 | chunk_length | bytes after header |
| 26 | 2 | reserved | 0 |
| 28 | 4 | crc32 | CRC32/IEEE of the complete logical payload |

All integers are big-endian. A 1200-byte datagram stays below a normal 1500-byte MTU after IPv4 and UDP headers, avoiding IP fragmentation.

### Logical payload

The logical payload is 9936 bytes.

| offset | size | field |
|---:|---:|---|
| 0 | 2 | width = 80 |
| 2 | 2 | height = 62 |
| 4 | 4 | frame_sequence |
| 8 | 4 | uptime_ms |
| 12 | 2 | minimum_raw |
| 14 | 2 | maximum_raw |
| 16 | 9920 | 4960 uint16 pixels, big-endian |

9936 bytes split into 1168-byte chunks produce nine datagrams. The final datagram contains the remaining 592 bytes. CRC32 is calculated over metadata followed by all pixel bytes and is repeated in every datagram.

### Receiver reassembly

1. Validate magic, version, type, and header_length.
2. Validate payload_length, chunk_count, chunk_index, payload_offset, and chunk_length.
3. Store each chunk in a pending buffer keyed by frame_sequence and payload_offset. Arrival order is not significant.
4. Detect duplicate offsets and conflicting duplicate data.
5. When every byte range is present, calculate CRC32/IEEE.
6. Pass the 80 x 62 frame downstream only when CRC32 matches.
7. Discard incomplete, conflicting, CRC-invalid, or timed-out frames (recommended timeout: 0.5 seconds).
8. Expose incomplete/dropped state as stale; never present a partial frame as a fresh measurement.

UDP has no handshake, ordering, deduplication, or retransmission. These responsibilities belong to the receiver.

## Operational checks

When thermal_frames increases but udp_sent stays at zero and udp_failed increases, check:

- RPI_HOST is the Raspberry Pi current Wi-Fi address.
- Both devices are on the same 2.4 GHz AP/subnet.
- A listener is bound to UDP 5005 on the Raspberry Pi.
- Firewall rules allow UDP 5005.
- Sender and receiver use the same SNTU magic, version, type, and port.

The legacy integration/pi_lcd/server.py currently receives SNST TCP 9000 only. A UDP receiver implementing the SNTU v1 reassembly above is required to consume thermal frames.
