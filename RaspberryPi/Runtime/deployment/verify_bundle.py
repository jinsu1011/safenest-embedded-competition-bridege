#!/usr/bin/env python3
"""Verify that a SafeNest folder is complete and safe to distribute."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


# Verification runs against the repository root so every canonical component
# (ESP32 firmware, Ondevice_AI, Web, Runtime) is expressed with one path base.
ROOT = Path(__file__).resolve().parents[3]
RUNTIME = "RaspberryPi/Runtime"
REQUIRED_FILES = (
    "README.md",
    "COMPONENT_SOURCES.json",
    "run_safenest.sh",
    f"{RUNTIME}/PACKAGE_AND_OPERATION_GUIDE.md",
    f"{RUNTIME}/INTEGRATION_PHASE_SUMMARY.md",
    f"{RUNTIME}/SOURCE_MANIFEST.md",
    f"{RUNTIME}/requirements-backend.txt",
    f"{RUNTIME}/paths.py",
    f"{RUNTIME}/backend/run_backend.py",
    f"{RUNTIME}/backend/app.py",
    f"{RUNTIME}/backend/runtime_status.py",
    f"{RUNTIME}/backend/portal.py",
    f"{RUNTIME}/hil/preflight.py",
    f"{RUNTIME}/hil/stage9_smoke.py",
    f"{RUNTIME}/gateway/protocol.py",
    f"{RUNTIME}/gateway/receiver.py",
    f"{RUNTIME}/gateway/thermal_udp.py",
    f"{RUNTIME}/state/manager.py",
    f"{RUNTIME}/ai/pipeline.py",
    f"{RUNTIME}/risk/engine.py",
    f"{RUNTIME}/database/schema.sql",
    f"{RUNTIME}/database/repository.py",
    f"{RUNTIME}/deployment/run_pi.sh",
    f"{RUNTIME}/hil/capture.py",
    f"{RUNTIME}/docs/PHASE1_REPOSITORY_AUDIT.md",
    f"{RUNTIME}/docs/PHASE10_E2E.md",
    f"{RUNTIME}/docs/HIL_ACCEPTANCE.md",
    f"{RUNTIME}/docs/ON_DEVICE_UPDATE_AUDIT.md",
    "RaspberryPi/Web/index.html",
    "RaspberryPi/Web/styles.css",
    "RaspberryPi/Web/app.js",
    "RaspberryPi/Web/index_final.html",
    "RaspberryPi/Web/styles_final.css",
    "RaspberryPi/Web/app_final.js",
    "RaspberryPi/Ondevice_AI/requirements-pi.txt",
    "RaspberryPi/Ondevice_AI/models/model_manifest.json",
    "RaspberryPi/Ondevice_AI/risk/risk_config.json",
    "RaspberryPi/Ondevice_AI/AGENTS.md",
    "ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino",
    "ESP32/secret.h.example",
    "ESP32/docs/COMMUNICATION_PROTOCOL.md",
)
FORBIDDEN_NAMES = {"secrets.h"}
FORBIDDEN_SUFFIXES = {".db", ".db-wal", ".db-shm", ".pyc"}


def verify(root: Path = ROOT) -> dict[str, object]:
    root = root.resolve()
    missing = [relative for relative in REQUIRED_FILES if not (root / relative).is_file()]
    forbidden = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in FORBIDDEN_NAMES or any(path.name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            forbidden.append(str(path.relative_to(root)))
    caches = [str(path.relative_to(root)) for path in root.rglob("__pycache__") if path.is_dir()]
    model_checks = _model_checks(root)
    checks = {
        "required_files_present": not missing,
        "model_hashes_match": bool(model_checks) and all(item["match"] for item in model_checks),
        "no_secrets_or_databases": not forbidden,
        "no_python_caches": not caches,
    }
    return {
        "schema": "safenest.bundle.verification.v1",
        "ok": all(checks.values()),
        "root": str(root),
        "checks": checks,
        "missing": missing,
        "forbidden": forbidden,
        "caches": caches,
        "models": model_checks,
        "file_count": sum(1 for path in root.rglob("*") if path.is_file()),
    }


def _model_checks(root: Path) -> list[dict[str, object]]:
    model_root = root / "RaspberryPi" / "Ondevice_AI"
    manifest_path = model_root / "models" / "model_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    results = []
    for sensor_id, entry in manifest.get("models", {}).items():
        path = model_root / str(entry.get("path", ""))
        expected = str(entry.get("sha256", ""))
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            actual = None
        results.append({
            "sensor_id": sensor_id,
            "path": str(path.relative_to(root)),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "match": bool(expected) and actual == expected,
        })
    return results


def main() -> int:
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
