#!/usr/bin/env python3
"""Regression tests for ESP32 telemetry ingestion and LCD API state."""

from __future__ import annotations

import json
import socket
import struct
import threading
import unittest
import unittest.mock
import urllib.request

import server


def sample_telemetry() -> dict[str, object]:
    return {
        "schema": "safenest.telemetry.v1",
        "device_id": "safenest-esp32-01",
        "seq": 42,
        "uptime_ms": 12_345,
        "resp_rate_bpm": 16.25,
        "heart_rate_bpm": 72.5,
        "co2_ppm": 820,
        "pir_motion": True,
        "thermal_max_c": 36.4,
        "valid": {
            "respiration": True,
            "heart": True,
            "co2": True,
            "thermal": True,
        },
    }


def sample_thermal(sequence: int = 7) -> bytes:
    """Build one real protocol-v1 80x62 frame at about 25.0 degC."""
    minimum_raw = 2981
    maximum_raw = 2990
    metadata = server.THERMAL_META.pack(
        server.THERMAL_WIDTH,
        server.THERMAL_HEIGHT,
        sequence,
        12_345,
        minimum_raw,
        maximum_raw,
    )
    pixels = b"".join(
        struct.pack("!H", minimum_raw + index % 10)
        for index in range(server.THERMAL_PIXEL_COUNT)
    )
    return metadata + pixels


class SensorStoreTests(unittest.TestCase):
    def test_live_snapshot_contains_latest_sensor_values(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        store.set_connected(True, ("192.168.1.50", 45678))
        store.record_telemetry(sample_telemetry())

        snapshot = store.snapshot()
        self.assertEqual(snapshot["status"], "live")
        self.assertTrue(snapshot["fresh"])
        self.assertEqual(snapshot["device_id"], "safenest-esp32-01")
        self.assertEqual(snapshot["resp_rate_bpm"], 16.25)
        self.assertEqual(snapshot["heart_rate_bpm"], 72.5)
        self.assertEqual(snapshot["co2_ppm"], 820)
        self.assertTrue(snapshot["pir_motion"])
        # The camera's peak reading rides along with the scalar telemetry.
        self.assertEqual(snapshot["thermal"]["max_c"], 36.4)
        self.assertTrue(snapshot["thermal"]["available"])
        self.assertTrue(snapshot["thermal"]["fresh"])

    def test_disconnect_marks_previous_values_stale(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        store.set_connected(True, ("192.168.1.50", 45678))
        store.record_telemetry(sample_telemetry())
        store.set_connected(False)

        snapshot = store.snapshot()
        self.assertEqual(snapshot["status"], "stale")
        self.assertFalse(snapshot["fresh"])
        self.assertEqual(snapshot["co2_ppm"], 820)

    def test_invalid_schema_is_rejected(self) -> None:
        payload = sample_telemetry()
        payload["schema"] = "unknown"
        with self.assertRaises(ValueError):
            server.SensorStore().record_telemetry(payload)

    def test_thermal_frame_is_validated_and_retained(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        store.set_connected(True, ("192.168.1.50", 45678))
        thermal = sample_thermal(sequence=7)
        store.record_thermal_frame(thermal, outer_sequence=7)

        saved, sequence = store.latest_thermal_frame()
        snapshot = store.snapshot()
        self.assertEqual(saved, thermal)
        self.assertEqual(sequence, 7)
        self.assertEqual(snapshot["thermal_frames_received"], 1)
        self.assertTrue(snapshot["thermal"]["available"])
        self.assertTrue(snapshot["thermal"]["fresh"])
        self.assertEqual(snapshot["thermal"]["width"], 80)
        self.assertEqual(snapshot["thermal"]["height"], 62)
        self.assertAlmostEqual(snapshot["thermal"]["min_c"], 24.95, places=2)

    def test_invalid_thermal_frame_is_rejected(self) -> None:
        store = server.SensorStore()
        with self.assertRaisesRegex(ValueError, "length mismatch"):
            store.record_thermal_frame(b"thermal-test", outer_sequence=7)

    def test_all_zero_thermal_frame_is_rejected(self) -> None:
        store = server.SensorStore()
        metadata = server.THERMAL_META.pack(
            server.THERMAL_WIDTH,
            server.THERMAL_HEIGHT,
            8,
            12_345,
            0,
            0,
        )
        frame = metadata + bytes(server.THERMAL_PIXEL_COUNT * 2)
        with self.assertRaisesRegex(ValueError, "too few usable pixels"):
            store.record_thermal_frame(frame, outer_sequence=8)

    def test_peak_temperature_ignores_dead_pixels(self) -> None:
        """A partly dead array still yields the hottest real reading."""
        store = server.SensorStore(stale_seconds=5.0)
        store.set_connected(True, ("192.168.1.50", 45678))

        dead_raw = 2085  # about -64.7 C, the array's fallback value
        warm_raw = 3101  # about 36.95 C
        room_raw = 2981  # about 24.95 C
        live_count = 100
        values = (
            [room_raw] * (live_count - 1)
            + [warm_raw]
            + [dead_raw] * (server.THERMAL_PIXEL_COUNT - live_count)
        )
        metadata = server.THERMAL_META.pack(
            server.THERMAL_WIDTH,
            server.THERMAL_HEIGHT,
            11,
            12_345,
            min(values),
            max(values),
        )
        frame = metadata + b"".join(struct.pack("!H", value) for value in values)
        store.record_thermal_frame(frame, outer_sequence=11)

        thermal = store.snapshot()["thermal"]
        self.assertEqual(thermal["usable_pixels"], live_count)
        # Dead pixels must not become the reported range.
        self.assertAlmostEqual(thermal["max_c"], 36.95, places=2)
        self.assertAlmostEqual(thermal["min_c"], 24.95, places=2)


class SensorProtocolTests(unittest.TestCase):
    def test_receiver_consumes_telemetry_and_thermal_packets(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        receiver = server.SensorReceiver("127.0.0.1", 0, store)
        server_socket, client_socket = socket.socketpair()

        def receive_until_close() -> None:
            try:
                receiver._handle_connection(server_socket, ("127.0.0.1", 40000))
            except ConnectionError:
                pass

        thread = threading.Thread(target=receive_until_close)
        thread.start()
        telemetry = json.dumps(sample_telemetry()).encode("utf-8")
        client_socket.sendall(
            server.PACKET_HEADER.pack(
                server.SENSOR_MAGIC,
                server.SENSOR_PROTOCOL_VERSION,
                server.PACKET_TELEMETRY_JSON,
                0,
                42,
                len(telemetry),
            )
            + telemetry
        )
        thermal = sample_thermal(sequence=7)
        client_socket.sendall(
            server.PACKET_HEADER.pack(
                server.SENSOR_MAGIC,
                server.SENSOR_PROTOCOL_VERSION,
                server.PACKET_THERMAL_U16_BE,
                0,
                7,
                len(thermal),
            )
            + thermal
        )
        client_socket.close()
        thread.join(timeout=2.0)
        server_socket.close()

        self.assertFalse(thread.is_alive())
        snapshot = store.snapshot()
        self.assertEqual(snapshot["seq"], 42)
        self.assertEqual(snapshot["thermal_frames_received"], 1)

    def test_idle_peer_is_dropped_so_a_reset_board_can_reconnect(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        receiver = server.SensorReceiver("127.0.0.1", 0, store)
        server_socket, client_socket = socket.socketpair()
        self.addCleanup(client_socket.close)
        self.addCleanup(server_socket.close)

        with unittest.mock.patch.object(server, "SENSOR_IDLE_TIMEOUT_SECONDS", 0.2):
            server_socket.settimeout(0.05)
            with self.assertRaisesRegex(ConnectionError, "no packet"):
                receiver._handle_connection(server_socket, ("127.0.0.1", 40000))

        self.assertFalse(store.snapshot()["connected"])

    def test_midpacket_stall_drops_the_connection(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        receiver = server.SensorReceiver("127.0.0.1", 0, store)
        server_socket, client_socket = socket.socketpair()
        self.addCleanup(client_socket.close)
        self.addCleanup(server_socket.close)

        # Header promises a payload the board never finishes sending.
        telemetry = json.dumps(sample_telemetry()).encode("utf-8")
        client_socket.sendall(
            server.PACKET_HEADER.pack(
                server.SENSOR_MAGIC,
                server.SENSOR_PROTOCOL_VERSION,
                server.PACKET_TELEMETRY_JSON,
                0,
                42,
                len(telemetry),
            )
            + telemetry[:10]
        )
        server_socket.settimeout(0.05)
        with self.assertRaisesRegex(ConnectionError, "mid-packet"):
            receiver._handle_connection(server_socket, ("127.0.0.1", 40000))

    def test_http_endpoint_returns_latest_binary_thermal_frame(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        thermal = sample_thermal(sequence=19)
        store.record_thermal_frame(thermal, outer_sequence=19)

        httpd = server.ThreadingHTTPServer(
            ("127.0.0.1", 0), server.SafeNestHandler
        )
        httpd.sensor_store = store
        thread = threading.Thread(target=httpd.serve_forever)
        thread.start()
        try:
            host, port = httpd.server_address
            with urllib.request.urlopen(
                f"http://{host}:{port}/api/thermal", timeout=2.0
            ) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(
                    response.headers.get_content_type(),
                    "application/vnd.safenest.thermal-u16be",
                )
                self.assertEqual(response.headers["X-Thermal-Sequence"], "19")
                self.assertEqual(response.read(), thermal)
            with urllib.request.urlopen(
                f"http://{host}:{port}/thermal", timeout=2.0
            ) as response:
                page = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("SafeNest 노트북 열화상", page)
                self.assertIn('fetch("/api/thermal"', page)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2.0)


if __name__ == "__main__":
    unittest.main()
