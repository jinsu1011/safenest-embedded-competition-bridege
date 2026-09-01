#!/usr/bin/env python3
"""Build and verify an additive SHA-256 manifest for Phase 2C-HR artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    missing = [str(path) for path in args.artifact if not path.is_file()]
    if missing:
        raise SystemExit(f"missing artifacts: {missing}")
    document = {
        "manifest_version": "1.0",
        "analysis_id": "mr60_hr_sideband_phase2c_20260801",
        "existing_manifests_modified": False,
        "artifacts": [
            {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in args.artifact
        ],
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for artifact in document["artifacts"]:
        if sha256(Path(artifact["path"])) != artifact["sha256"]:
            raise SystemExit(f"hash verification failed: {artifact['path']}")
    print(f"manifest_artifacts={len(document['artifacts'])}")
    print("manifest_hashes=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
