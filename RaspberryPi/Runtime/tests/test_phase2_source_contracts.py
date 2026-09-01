from __future__ import annotations

from pathlib import Path
import re
import unittest


from paths import ESP32_ROOT, ESP32_SKETCH, ESP32_SECRET_TEMPLATE, LCD_ROOT, RUNTIME_ROOT

ROOT = RUNTIME_ROOT
INTEGRATED_FW = ESP32_SKETCH
SECRETS_EXAMPLE = ESP32_SECRET_TEMPLATE
PI_SERVER = LCD_ROOT / "server.py"
PROTOCOL_DOC = ESP32_ROOT / "docs" / "COMMUNICATION_PROTOCOL.md"
MMWAVE_FW = ESP32_ROOT / "reference" / "mmwave_platformio" / "src" / "main.cpp"


class Phase2SourceContracts(unittest.TestCase):
    def test_active_sender_exposes_reboot_safe_sensor_provenance(self) -> None:
        source = INTEGRATED_FW.read_text(encoding="utf-8")
        for token in (
            "boot_id",
            "co2_measurement_event_id",
            "co2_measurement_monotonic_ms",
            "co2_measurement_event_valid",
            "pir_event_id",
            "pir_last_transition_monotonic_ms",
        ):
            self.assertIn(token, source)
        self.assertIn("++co2MeasurementEventId", source)
        self.assertIn("++pirEventId", source)

    @classmethod
    def setUpClass(cls) -> None:
        cls.firmware = INTEGRATED_FW.read_text(encoding="utf-8")
        cls.server = PI_SERVER.read_text(encoding="utf-8")
        cls.protocol = PROTOCOL_DOC.read_text(encoding="utf-8")
        cls.mmwave = MMWAVE_FW.read_text(encoding="utf-8")

    def test_selected_sources_exist(self) -> None:
        for path in (
            INTEGRATED_FW,
            SECRETS_EXAMPLE,
            PI_SERVER,
            PROTOCOL_DOC,
            MMWAVE_FW,
        ):
            self.assertTrue(path.is_file(), path)

    def test_all_four_sensors_are_present_in_integrated_firmware(self) -> None:
        for marker in (
            "Seeed_Arduino_mmWave.h",
            "SensirionI2cScd4x.h",
            "PIN_PIR",
            "thermalSpi",
        ):
            self.assertIn(marker, self.firmware)

    def test_tcp_v1_header_contract_matches(self) -> None:
        self.assertIn('memcpy(header, "SNST", 4)', self.firmware)
        self.assertIn("constexpr size_t PACKET_HEADER_SIZE = 16", self.firmware)
        self.assertIn('PACKET_HEADER = struct.Struct("!4sBBHII")', self.server)
        self.assertIn("SENSOR_PROTOCOL_VERSION = 1", self.server)
        self.assertIn("헤더 크기는 16바이트", self.protocol)

    def test_tcp_receiver_handles_partial_reads(self) -> None:
        self.assertRegex(
            self.server,
            r"def recv_exact\(\s*connection: socket\.socket,\s*size: int",
        )
        self.assertIn("connection.recv(remaining)", self.server)
        self.assertIn("idle_ok=True", self.server)
        self.assertIn("frame_deadline_seconds", self.server)

    def test_thermal_payload_is_9936_bytes_by_contract(self) -> None:
        width = self._constexpr("THERMAL_WIDTH")
        height = self._constexpr("THERMAL_HEIGHT")
        metadata = self._constexpr("THERMAL_META_SIZE")
        self.assertEqual((width, height, metadata), (80, 62, 16))
        self.assertEqual(metadata + width * height * 2, 9_936)
        self.assertIn("9,920", self.protocol)

    def test_sender_has_timeout_and_reconnect_loop(self) -> None:
        self.assertIn("millis() - started) > 3000", self.firmware)
        self.assertIn("client.connect(RPI_HOST, RPI_PORT, 1500)", self.firmware)
        self.assertIn("vTaskDelay(pdMS_TO_TICKS(1000))", self.firmware)

    def test_only_thermal_uses_chunked_udp(self) -> None:
        self.assertIn("void telemetryTcpTask", self.firmware)
        self.assertIn("sendTelemetry(client, telemetry)", self.firmware)
        self.assertIn("void thermalUdpTask", self.firmware)
        self.assertIn("sendThermalUdp(udp, thermalNetworkFrame)", self.firmware)
        self.assertNotIn("sendThermal(client", self.firmware)
        self.assertIn("THERMAL_UDP_DATAGRAM_SIZE = 1200", self.firmware)
        self.assertIn("THERMAL_UDP_PORT = 5005", self.firmware)

    def test_secrets_are_externalized_in_selected_sender(self) -> None:
        """Credentials must live in the ignored secrets.h, never in the sketch.

        Asserting on the *shape* of a credential assignment catches any future
        hardcoded network, instead of only the one pair that leaked before.
        """
        self.assertIn('#include "secrets.h"', self.firmware)
        for symbol in ("WIFI_SSID", "WIFI_PASSWORD", "RPI_HOST"):
            assignment = re.search(
                rf'{symbol}\s*\[\]\s*=\s*"([^"]*)"', self.firmware
            )
            self.assertIsNone(
                assignment,
                f"{symbol} must come from secrets.h, not a literal in the sketch",
            )

    def test_mmwave_reference_is_uart_jsonl_firmware(self) -> None:
        self.assertIn("HardwareSerial radarSerial(2)", self.mmwave)
        self.assertIn("radarSerial.begin", self.mmwave)
        self.assertIn('Serial.println("}")', self.mmwave)

    def _constexpr(self, name: str) -> int:
        match = re.search(
            rf"constexpr\s+size_t\s+{re.escape(name)}\s*=\s*(\d+)",
            self.firmware,
        )
        self.assertIsNotNone(match, name)
        return int(match.group(1))


if __name__ == "__main__":
    unittest.main()
