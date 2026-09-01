#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = PROJECT_ROOT / "ondevice_ai/datasets/mmwave/mr60_20260728_manifest.json"


class TestMR60Manifest(unittest.TestCase):
    def test_accepted_sources_exist_and_match_hash(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["sources"]), 6)
        for source in manifest["sources"]:
            with self.subTest(path=source["path"]):
                path = PROJECT_ROOT / source["path"]
                self.assertTrue(source["accepted"])
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, source["bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])

    def test_heart_and_apnea_limitations_are_explicit(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        limits = manifest["reference_limits"]
        self.assertIn("UNVERIFIED", limits["heart"])
        self.assertIn("must not", limits["apnea"])


if __name__ == "__main__":
    unittest.main()
