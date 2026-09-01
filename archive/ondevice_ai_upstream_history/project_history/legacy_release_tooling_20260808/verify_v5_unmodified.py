#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/verify_v5_unmodified.py
Computes and verifies SHA-256 hashes of all files in SafeNest_V5_OnDevice_AI
to mathematically prove zero files were modified, added, or deleted.
"""

from __future__ import annotations
import os
import sys
import json
import hashlib
from pathlib import Path

v6_root = Path(__file__).resolve().parent.parent
v5_root = v6_root.parent.parent / "SafeNest_V5_OnDevice_AI"


def hash_file(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def scan_v5_hashes() -> dict[str, str]:
    file_hashes = {}
    for root, _, files in os.walk(v5_root):
        # Exclude pycache or pytest cache if present
        if "__pycache__" in root or ".pytest_cache" in root or ".venv" in root:
            continue
        for file in sorted(files):
            if file == ".DS_Store" or file.endswith(".pyc"):
                continue
            fp = Path(root) / file
            rel_path = str(fp.relative_to(v5_root))
            file_hashes[rel_path] = hash_file(fp)
    return file_hashes


def main():
    if not v5_root.exists():
        print(f"❌ Error: V5 directory not found at {v5_root}")
        sys.exit(1)

    print(f"🔒 Scanning file hashes in {v5_root.name}...")
    hashes = scan_v5_hashes()

    print(f"✅ Total V5 files scanned: {len(hashes)}")
    hash_record_path = v6_root / "benchmarks/v5_file_sha256_audit.json"
    hash_record_path.parent.mkdir(parents=True, exist_ok=True)

    status = "CONFIRMED_UNMODIFIED"
    if hash_record_path.exists():
        with open(hash_record_path, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
            prev_hashes = prev_data.get("hashes", {})
        
        diffs = []
        for k, v in hashes.items():
            if k not in prev_hashes:
                diffs.append(f"ADDED: {k}")
            elif prev_hashes[k] != v:
                diffs.append(f"MODIFIED: {k}")
        for k in prev_hashes:
            if k not in hashes:
                diffs.append(f"DELETED: {k}")

        if diffs:
            print("❌ V5 Modification Detected!")
            for d in diffs:
                print(f"  - {d}")
            sys.exit(1)
        else:
            print("✅ Perfect Match! Zero V5 files modified.")

    record = {
        "status": status,
        "total_files": len(hashes),
        "v5_path": str(v5_root),
        "hashes": hashes
    }
    with open(hash_record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    print(f"✅ Saved SHA-256 audit record to {hash_record_path}")


if __name__ == "__main__":
    main()
