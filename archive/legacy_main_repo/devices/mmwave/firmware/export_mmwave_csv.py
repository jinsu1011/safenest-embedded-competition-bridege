#!/usr/bin/env python3
"""Export SafeNest MR60BHA2 JSONL logs as team-spec CSV per session.

Rules enforced from 한준우 spec (2026-07-25):
  - resp_phase 필드에는 ESP breath_phase 원값을 그대로 저장 (×100, Z-Score 등 금지)
  - 실제 측정 timestamp 보존 (재샘플링 금지)
  - 세션별 session_id 분리 (5분 인체 = 1 세션, 진입퇴장 10회 = 10 세션 개별)
  - 서로 다른 로그를 하나로 합치지 않음
  - presence=0 구간에 resp_phase=0을 임의 생성하지 않음
  - timestamp 중복/역행/NaN/Inf는 진단 리포트에 기록
  - 원본 파일과 CSV 사이 대응 관계는 매니페스트 JSON에 SHA256과 함께 저장

CSV 열: timestamp_s, resp_phase, subject_id, session_id, presence, label,
        breath_rpm, range_m, quality, signal_source, device_id
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CSV_HEADER = [
    "timestamp_s", "resp_phase", "subject_id", "session_id",
    "presence", "label", "breath_rpm", "range_m",
    "quality", "signal_source", "device_id",
]
SIGNAL_SOURCE = "MR60BHA2_breath_phase"
DEFAULT_SUBJECT = "S001"
DEFAULT_DEVICE = "safenest-node-01"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_bad_float(value: Any) -> bool:
    return isinstance(value, float) and (math.isnan(value) or math.isinf(value))


@dataclass
class SessionSpec:
    session_id: str
    label: str
    records: list[dict[str, Any]]
    origin_start_ms: int


def load_all_records(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def load_records(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sensor, beeps = [], []
    for item in load_all_records(path):
        kind = item.get("kind")
        if kind == "beep":
            beeps.append(item)
        elif "seq" in item and item.get("ts_monotonic_ms") is not None:
            sensor.append(item)
    return sensor, beeps


def diagnostics(session: SessionSpec) -> dict[str, Any]:
    ts_ms = [r["ts_monotonic_ms"] for r in session.records]
    phase_values = [float(r["breath_phase"]) for r in session.records
                    if r.get("breath_phase") is not None
                    and not is_bad_float(r.get("breath_phase"))]
    phase_mean = sum(phase_values) / len(phase_values) if phase_values else None
    phase_std = (math.sqrt(sum((v - phase_mean) ** 2 for v in phase_values) /
                           len(phase_values)) if phase_values else None)
    duplicates, backwards, bad_phase = [], [], []
    prev = None
    for idx, r in enumerate(session.records):
        t = r["ts_monotonic_ms"]
        if prev is not None:
            if t == prev:
                duplicates.append({"index": idx, "ts_ms": t})
            elif t < prev:
                backwards.append({"index": idx, "ts_ms": t, "prev_ms": prev})
        prev = t
        phase = r.get("breath_phase")
        if phase is None or is_bad_float(phase):
            bad_phase.append({"index": idx, "ts_ms": t, "value": phase})
    if len(ts_ms) < 2:
        rate = None
        max_gap = None
    else:
        gaps_ms = [b - a for a, b in zip(ts_ms, ts_ms[1:])]
        rate = 1000.0 / (sum(gaps_ms) / len(gaps_ms)) if gaps_ms else None
        max_gap = max(gaps_ms) if gaps_ms else None
    return {
        "session_id": session.session_id,
        "label": session.label,
        "records": len(session.records),
        "duration_s": (ts_ms[-1] - ts_ms[0]) / 1000.0 if len(ts_ms) >= 2 else None,
        "measured_rate_hz": rate,
        "max_gap_ms": max_gap,
        "timestamp_duplicates": duplicates,
        "timestamp_backwards": backwards,
        "bad_or_missing_phase": bad_phase,
        "breath_phase_std": phase_std,
        "presence_true_percent": (
            100.0 * sum(r.get("human_detected_raw") is True
                        for r in session.records) / len(session.records)
            if session.records else None
        ),
    }


def write_csv(session: SessionSpec, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for r in session.records:
            t_s = (int(r["ts_monotonic_ms"]) - session.origin_start_ms) / 1000.0
            resp = r.get("breath_phase")
            presence_raw = r.get("human_detected_raw")
            if presence_raw is True:
                presence = 1
            elif presence_raw is False:
                presence = 0
            else:
                presence = ""
            breath = r.get("breath_rate_raw")
            breath_field = f"{breath:.2f}" if isinstance(breath, (int, float)) and breath > 0 else ""
            dist = r.get("distance_cm_raw")
            range_m = f"{dist / 100.0:.4f}" if isinstance(dist, (int, float)) and dist > 0 else ""
            resp_field = "" if (resp is None or is_bad_float(resp)) else f"{resp:.6f}"
            writer.writerow([
                f"{t_s:.4f}", resp_field, DEFAULT_SUBJECT, session.session_id,
                presence, session.label, breath_field, range_m,
                "", SIGNAL_SOURCE, r.get("device_id", DEFAULT_DEVICE),
            ])


def build_normal_session(sensor: list[dict[str, Any]], session_id: str,
                         label: str, warmup_seconds: float) -> SessionSpec:
    if not sensor:
        return SessionSpec(session_id, label, [], 0)
    origin = int(sensor[0]["ts_monotonic_ms"])
    cutoff = origin + int(warmup_seconds * 1000)
    records = [r for r in sensor if int(r["ts_monotonic_ms"]) >= cutoff]
    if not records:
        return SessionSpec(session_id, label, [], origin)
    return SessionSpec(session_id, label, records, int(records[0]["ts_monotonic_ms"]))


def distance_code(path: Path) -> str:
    match = re.search(r"_d(\d{2})_", path.stem.lower())
    if not match:
        raise ValueError(f"distance code missing from matrix filename: {path}")
    return match.group(1)


def source_interpretation(path: Path) -> dict[str, Any]:
    stem = path.stem.lower()
    if "breath_paced_12rpm" in stem and "explicit" not in stem:
        return {"use": "failure_case", "actual_breath_rpm": 6.06,
                "reason": "절반 호흡 안내 해석 사고; 12rpm 정답 데이터로 사용 금지"}
    if "12rpm_explicit" in stem:
        return {"use": "preferred_validation", "actual_breath_rpm": 12.0,
                "reason": "명시적 들숨/날숨 안내로 재측정한 유효 12rpm 세션"}
    if "20rpm_deep" in stem:
        return {"use": "preferred_validation", "actual_breath_rpm": 20.0,
                "reason": "충분한 흉부 변위; 30초 영교차 ±2rpm 통과율 100%"}
    if "breath_paced_20rpm" in stem:
        return {"use": "failure_case", "actual_breath_rpm": 20.0,
                "reason": "얕은 호흡 저진폭 실패 사례"}
    if "breath_paced_15rpm" in stem:
        return {"use": "preferred_validation", "actual_breath_rpm": 15.0,
                "reason": "30초 영교차 ±2rpm 통과율 100%"}
    if "_d15_" in stem:
        return {"use": "lock_loss_case",
                "reason": "거리 std=0은 원거리 한계가 아니라 lock-loss 시그니처"}
    if "_d12_" in stem:
        return {"use": "range_limit_case",
                "reason": "재실 81.4%로 KPI 미달"}
    return {"use": "normal_validation"}


def build_breath_session(path: Path, sequence: int) -> SessionSpec:
    rows = load_all_records(path)
    cues = [(i, row) for i, row in enumerate(rows) if row.get("kind") == "cue"]
    if not cues:
        raise ValueError(f"paced-breath log has no cue records: {path}")
    measurement = [(i, row) for i, row in cues if row.get("stage") == "measurement"]
    selected = measurement or cues
    first_index, last_index = selected[0][0], selected[-1][0]
    target = selected[0][1].get("target_bpm")
    if target is None:
        match = re.search(r"_(\d+)rpm", path.stem.lower())
        if not match:
            raise ValueError(f"target rpm missing from breath log: {path}")
        target = int(match.group(1))
    target_text = f"{float(target):g}"
    sensor = [
        row for row in rows[first_index:last_index + 1]
        if row.get("kind") not in ("cue", "beep")
        and "seq" in row and row.get("ts_monotonic_ms") is not None
    ]
    if not sensor:
        raise ValueError(f"no sensor records inside paced measurement cues: {path}")
    session_id = f"{DEFAULT_SUBJECT}_BREATH_PACED_{target_text}_{sequence:02d}"
    return SessionSpec(session_id, f"BREATH_PACED_{target_text}", sensor,
                       int(sensor[0]["ts_monotonic_ms"]))


def build_trial_sessions(sensor: list[dict[str, Any]],
                         beeps: list[dict[str, Any]]) -> list[SessionSpec]:
    enters = sorted([b for b in beeps if b.get("event") == "enter"],
                    key=lambda b: b["host_monotonic_ns"])
    if not enters:
        return []
    # Map host_monotonic_ns of enter beeps to nearest ESP ts_monotonic_ms
    # by scanning sensor records with host_monotonic_ns (present in trial log).
    def esp_ts_at(host_ns: int) -> int | None:
        best = None
        best_delta = None
        for r in sensor:
            host = r.get("host_monotonic_ns")
            if host is None:
                continue
            delta = abs(int(host) - int(host_ns))
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best = int(r["ts_monotonic_ms"])
        return best

    enter_esp_ms = [esp_ts_at(b["host_monotonic_ns"]) for b in enters]
    sessions: list[SessionSpec] = []
    for i, enter_ms in enumerate(enter_esp_ms):
        if enter_ms is None:
            continue
        end_ms = enter_esp_ms[i + 1] if i + 1 < len(enter_esp_ms) else None
        trial_no = enters[i]["trial"]
        session_id = f"{DEFAULT_SUBJECT}_ENTRY_EXIT_{trial_no:02d}"
        records = [
            r for r in sensor
            if int(r["ts_monotonic_ms"]) >= enter_ms
            and (end_ms is None or int(r["ts_monotonic_ms"]) < end_ms)
        ]
        if not records:
            continue
        sessions.append(SessionSpec(session_id, "PRESENCE_TRANSITION",
                                    records, int(records[0]["ts_monotonic_ms"])))
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-jsonl", type=Path,
                        help="5-min stationary human log")
    parser.add_argument("--normal-warmup-s", type=float, default=60.0,
                        help="세션 앞의 워밍업/전이 초 (여기서부터 안정 기준선)")
    parser.add_argument("--normal-session-id", type=str,
                        default=f"{DEFAULT_SUBJECT}_NORMAL_5MIN_01")
    parser.add_argument("--trial-jsonl", type=Path,
                        help="Entry/exit trial log with beep markers")
    parser.add_argument("--matrix-jsonl", type=Path, action="append", default=[],
                        help="stationary-human distance log; repeat for each distance")
    parser.add_argument("--breath-jsonl", type=Path, action="append", default=[],
                        help="paced-breath log; repeat for each session")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "exported_at_iso": "2026-08-01",
        "signal_source": SIGNAL_SOURCE,
        "spec_reference": "han-junwoo mmwave csv 인수 조건 2026-07-25",
        "notes": {
            "resp_phase": "ESP breath_phase 원값. ×100, Z-Score, offset 제거 없음.",
            "timestamp_s": "세션 시작 시각을 0으로 리베이스한 초 단위. ESP ts_monotonic_ms 기반.",
            "presence_zero_policy": "presence=0 구간에 resp_phase 임의 생성 없음.",
            "class1": "RAPID_OR_ABNORMAL은 이 배치에 포함되지 않음.",
            "trial_split_rule": "enter 비프의 host_monotonic_ns를 센서 로그에 매핑하여 각 시도별 session_id 분리.",
            "clock_rule": "cue와 센서 monotonic clock은 변환하지 않음. paced 세션은 파일 기록 순서의 measurement cue 범위로 선택.",
            "heart_rate": "절대 bpm은 미검증. heart_raw_valid=true는 사람 존재의 단방향 양성 증거로만 사용.",
            "known_caveats": [
                "2026-07-25 12rpm 로그는 절반 호흡 사고로 실제 약 6rpm.",
                "20rpm 얕은 호흡 로그는 저진폭 실패 사례이며 deep 로그와 구분해야 함.",
                "MR60 breath_rate_raw는 신뢰 불가; resp_phase 원값 기반 모델을 사용할 것.",
                "D15의 거리 std=0은 원거리 한계가 아니라 lock-loss 시그니처.",
            ],
        },
        "sources": [],
        "sessions": [],
        "diagnostics": [],
    }

    source_specs = []
    if args.normal_jsonl:
        source_specs.append(("normal", args.normal_jsonl))
    if args.trial_jsonl:
        source_specs.append(("trial", args.trial_jsonl))
    source_specs.extend(("matrix", p) for p in args.matrix_jsonl)
    source_specs.extend(("breath", p) for p in args.breath_jsonl)
    if not source_specs:
        parser.error("at least one JSONL input is required")

    originals_dir = args.out_dir / "original_jsonl"
    originals_dir.mkdir(parents=True, exist_ok=True)
    for label_name, jsonl_path in source_specs:
        if not jsonl_path.is_file():
            parser.error(f"input not found: {jsonl_path}")
        copied = originals_dir / jsonl_path.name
        if copied.exists() and sha256_of(copied) != sha256_of(jsonl_path):
            parser.error(f"duplicate basename with different content: {jsonl_path.name}")
        shutil.copy2(jsonl_path, copied)
        manifest["sources"].append({
            "role": label_name,
            "path": str(jsonl_path),
            "sha256": sha256_of(jsonl_path),
            "size_bytes": jsonl_path.stat().st_size,
            "copied_path": str(copied),
            "copied_sha256": sha256_of(copied),
        })

    def export_session(session: SessionSpec, origin: Path,
                       warmup_seconds: float | None = None) -> None:
        if not session.records:
            return
        out_path = args.out_dir / f"{origin.stem}__{session.session_id}.csv"
        write_csv(session, out_path)
        item = {
            "session_id": session.session_id,
            "label": session.label,
            "records": len(session.records),
            "csv_path": str(out_path),
            "csv_sha256": sha256_of(out_path),
            "origin_jsonl": str(origin),
            "interpretation": source_interpretation(origin),
        }
        if warmup_seconds is not None:
            item["warmup_skipped_seconds"] = warmup_seconds
        manifest["sessions"].append(item)
        manifest["diagnostics"].append(diagnostics(session))

    if args.normal_jsonl:
        normal_sensor, _ = load_records(args.normal_jsonl)
        export_session(build_normal_session(
            normal_sensor, args.normal_session_id, "NORMAL", args.normal_warmup_s
        ), args.normal_jsonl, args.normal_warmup_s)

    for matrix_path in args.matrix_jsonl:
        code = distance_code(matrix_path)
        matrix_sensor, _ = load_records(matrix_path)
        export_session(build_normal_session(
            matrix_sensor, f"{DEFAULT_SUBJECT}_NORMAL_D{code}",
            f"NORMAL_D{code}", args.normal_warmup_s
        ), matrix_path, args.normal_warmup_s)

    for sequence, breath_path in enumerate(args.breath_jsonl, 1):
        export_session(build_breath_session(breath_path, sequence), breath_path)

    if args.trial_jsonl:
        trial_sensor, trial_beeps = load_records(args.trial_jsonl)
        for session in build_trial_sessions(trial_sensor, trial_beeps):
            export_session(session, args.trial_jsonl)

    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"CSV 세션 수: {len(manifest['sessions'])}")
    print(f"매니페스트: {manifest_path}")


if __name__ == "__main__":
    main()
