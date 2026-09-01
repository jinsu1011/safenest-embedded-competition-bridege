#!/usr/bin/env python3
"""Regression tests for ESP32 telemetry ingestion and LCD API state."""

from __future__ import annotations

import json
import socket
import threading
import time
import unittest

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
        "valid": {"respiration": True, "heart": True, "co2": True},
    }


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
        self.assertIsNone(snapshot["co2_measurement_event_id"])
        self.assertIsNone(snapshot["co2_sensor_model"])
        self.assertIsNone(snapshot["co2_preheat_complete"])
        self.assertTrue(snapshot["fresh"])
        self.assertIsInstance(snapshot["age_seconds"], float)

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

    def test_health_snapshot_preserves_mhz19b_event_identity(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        store.set_connected(True, ("192.168.1.50", 45678))
        payload = sample_telemetry()
        payload.update(
            {
                "boot_id": "boot-mhz19b",
                "co2_measurement_event_id": 7,
                "co2_measurement_monotonic_ms": 180_000,
                "co2_measurement_event_valid": True,
                "co2_sensor_model": "MH-Z19B",
                "co2_event_identity_class": "INFERRED_UART_SAMPLE",
                "co2_preheat": True,
                "abc_enabled": False,
                "configured_range_ppm": 5000,
            }
        )
        store.record_telemetry(payload)
        snapshot = store.snapshot()
        self.assertEqual(snapshot["co2_measurement_event_id"], 7)
        self.assertEqual(snapshot["co2_measurement_monotonic_ms"], 180_000)
        self.assertTrue(snapshot["co2_measurement_event_valid"])
        self.assertEqual(snapshot["co2_sensor_model"], "MH-Z19B")
        self.assertEqual(snapshot["co2_event_identity_class"], "INFERRED_UART_SAMPLE")
        self.assertTrue(snapshot["co2_preheat_complete"])
        self.assertFalse(snapshot["abc_enabled"])
        self.assertEqual(snapshot["configured_range_ppm"], 5000)
        self.assertTrue(snapshot["fresh"])
        self.assertIsInstance(snapshot["age_seconds"], float)


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
        thermal = b"thermal-test"
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

    def test_skipped_snapshot_gap_does_not_close_the_socket(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        receiver = server.SensorReceiver("127.0.0.1", 0, store)
        server_socket, client_socket = socket.socketpair()
        finished = threading.Event()

        def receive_until_close() -> None:
            try:
                receiver._handle_connection(server_socket, ("127.0.0.1", 40001))
            except ConnectionError:
                pass
            finally:
                finished.set()

        thread = threading.Thread(target=receive_until_close)
        thread.start()
        first = json.dumps(sample_telemetry()).encode("utf-8")
        client_socket.sendall(
            server.PACKET_HEADER.pack(
                server.SENSOR_MAGIC,
                server.SENSOR_PROTOCOL_VERSION,
                server.PACKET_TELEMETRY_JSON,
                0,
                42,
                len(first),
            )
            + first
        )
        deadline = time.monotonic() + 1.0
        while store.snapshot()["seq"] != 42 and time.monotonic() < deadline:
            time.sleep(0.01)
        time.sleep(2.3)
        self.assertFalse(finished.is_set())
        second = json.dumps({**sample_telemetry(), "seq": 44, "uptime_ms": 14_345}).encode("utf-8")
        client_socket.sendall(
            server.PACKET_HEADER.pack(
                server.SENSOR_MAGIC,
                server.SENSOR_PROTOCOL_VERSION,
                server.PACKET_TELEMETRY_JSON,
                0,
                44,
                len(second),
            )
            + second
        )
        deadline = time.monotonic() + 1.0
        while store.snapshot()["seq"] != 44 and time.monotonic() < deadline:
            time.sleep(0.01)
        client_socket.close()
        thread.join(timeout=2.0)
        server_socket.close()
        self.assertEqual(store.snapshot()["seq"], 44)

    def test_header_then_delayed_payload_stays_on_the_same_socket(self) -> None:
        store = server.SensorStore(stale_seconds=5.0)
        receiver = server.SensorReceiver("127.0.0.1", 0, store)
        server_socket, client_socket = socket.socketpair()
        finished = threading.Event()

        def receive_until_close() -> None:
            try:
                receiver._handle_connection(server_socket, ("127.0.0.1", 40002))
            except ConnectionError:
                pass
            finally:
                finished.set()

        thread = threading.Thread(target=receive_until_close)
        thread.start()
        body = json.dumps(sample_telemetry()).encode("utf-8")
        client_socket.sendall(
            server.PACKET_HEADER.pack(
                server.SENSOR_MAGIC,
                server.SENSOR_PROTOCOL_VERSION,
                server.PACKET_TELEMETRY_JSON,
                0,
                42,
                len(body),
            )
        )
        time.sleep(2.1)
        self.assertFalse(finished.is_set())
        client_socket.sendall(body)
        deadline = time.monotonic() + 1.0
        while store.snapshot().get("seq") != 42 and time.monotonic() < deadline:
            time.sleep(0.01)
        client_socket.close()
        thread.join(timeout=2.0)
        server_socket.close()
        self.assertEqual(store.snapshot()["seq"], 42)


if __name__ == "__main__":
    unittest.main()
