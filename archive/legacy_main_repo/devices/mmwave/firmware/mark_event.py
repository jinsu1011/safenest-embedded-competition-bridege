#!/usr/bin/env python3
"""Append a host-clock ground-truth marker during a serial capture."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--event", required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "kind": "marker",
        "event": args.event,
        "host_monotonic_ns": time.monotonic_ns(),
        "host_unix_ns": time.time_ns(),
    }
    with args.output.open("a", encoding="utf-8") as output:
        output.write(json.dumps(marker) + "\n")
    print(json.dumps(marker))


if __name__ == "__main__":
    main()
