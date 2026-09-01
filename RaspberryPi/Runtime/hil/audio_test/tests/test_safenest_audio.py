from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import wave
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from safenest_audio import (  # noqa: E402
    TransitionController,
    generate_alarm_wav,
    load_profiles,
    parse_aplay_devices,
    resolve_profile_from_publication,
)


class DeviceParsingTests(unittest.TestCase):
    def test_usb_playback_device_and_target(self):
        aplay = (
            "**** List of PLAYBACK Hardware Devices ****\n"
            "card 2: Device [USB Audio Device], device 0: USB Audio [USB Audio]\n"
        )
        cards = " 2 [Device ]: USB-Audio - USB Audio Device\n"
        devices = parse_aplay_devices(aplay, cards)
        self.assertEqual(len(devices), 1)
        self.assertTrue(devices[0].usb_audio)
        self.assertEqual(devices[0].target, "plughw:CARD=Device,DEV=0")


class RiskMappingTests(unittest.TestCase):
    def test_canonical_mapping(self):
        self.assertEqual(resolve_profile_from_publication({"risk_level": "NORMAL"}), "normal")
        self.assertEqual(resolve_profile_from_publication({"risk_level": "WARNING"}), "warning")
        self.assertEqual(
            resolve_profile_from_publication({"risk_level": "DANGER", "is_emergency": False}),
            "danger",
        )
        self.assertEqual(
            resolve_profile_from_publication({"risk_level": "DANGER", "is_emergency": True}),
            "emergency",
        )
        self.assertEqual(
            resolve_profile_from_publication(
                {"risk": {"risk_level": "DANGER"}, "emergency": {"active": True}}
            ),
            "emergency",
        )
        self.assertEqual(
            resolve_profile_from_publication(
                {"risk": {"risk_level": None}, "emergency": {"active": True}}
            ),
            "emergency",
        )


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.profiles = load_profiles(ROOT / "audio_profiles.json")

    def test_warning_is_one_shot(self):
        controller = TransitionController(self.profiles)
        self.assertEqual(controller.decide("warning", now=0)["action"], "play")
        self.assertEqual(controller.decide("warning", now=999)["action"], "none")

    def test_danger_and_emergency_use_cooldown(self):
        controller = TransitionController(self.profiles)
        controller.decide("danger", now=0)
        self.assertEqual(controller.decide("danger", now=29)["action"], "none")
        self.assertEqual(controller.decide("danger", now=30)["action"], "play")
        decision = controller.decide("emergency", now=31)
        self.assertEqual(decision["action"], "interrupt_and_play")
        self.assertEqual(controller.decide("emergency", now=45)["action"], "none")
        self.assertEqual(controller.decide("emergency", now=46)["action"], "play")

    def test_normal_requests_silence_after_alert(self):
        controller = TransitionController(self.profiles)
        controller.decide("warning", now=0)
        self.assertEqual(controller.decide("normal", now=1)["action"], "silence")


class WaveSafetyTests(unittest.TestCase):
    def test_all_alarm_waves_are_bounded(self):
        profiles = load_profiles(ROOT / "audio_profiles.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            for name in ("warning", "danger", "emergency"):
                profile = profiles[name]
                path = generate_alarm_wav(
                    Path(temp_dir) / f"{name}.wav",
                    profile["alarm_segments"],
                    amplitude=profile["amplitude"],
                )
                with wave.open(str(path), "rb") as wav_file:
                    duration = wav_file.getnframes() / wav_file.getframerate()
                    self.assertLessEqual(duration, 5.0)
                    self.assertEqual(wav_file.getnchannels(), 2)
                    self.assertEqual(wav_file.getframerate(), 48_000)


if __name__ == "__main__":
    unittest.main()
