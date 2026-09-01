#!/usr/bin/env python3
"""Run the V5 node in real mode with only the CO2 provider injected.

The other three providers stay ``MissingExternalSensorProvider``, so the node
reports ``EXTERNAL_SENSOR_PROVIDER_REQUIRED`` for them instead of synthesizing
any value.  Intended for CO2 hardware bring-up and validation capture.

Example::

    python3 devices/co2/src/run_co2_v5_node.py \
        --port /dev/cu.usbserial-110 --seconds 300 \
        --output devices/co2/validation_results/<timestamp>_real_co2/ai_results.jsonl
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
for path in (REPO_ROOT, ONDEVICE_AI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from devices.co2.src.co2_serial_adapter import CO2SerialProvider  # noqa: E402
from integrated_node.run_node import SafeNestIntegratedNode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="ESP USB serial port")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--expected-firmware-version",
        default=None,
        help="reject telemetry from any other firmware build",
    )
    args = parser.parse_args()

    provider = CO2SerialProvider(
        port=args.port,
        baudrate=args.baudrate,
        expected_firmware_version=args.expected_firmware_version,
    )
    node = SafeNestIntegratedNode(mode="real", sensors={"co2": provider})
    node.start()

    sink = None
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        sink = args.output.open("w", encoding="utf-8")

    deadline = time.time() + args.seconds
    try:
        while time.time() < deadline:
            line = node.step().to_json()
            print(line, flush=True)
            if sink is not None:
                sink.write(line + "\n")
                sink.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if sink is not None:
            sink.close()
        node.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
