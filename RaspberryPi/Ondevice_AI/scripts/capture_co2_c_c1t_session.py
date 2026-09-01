#!/usr/bin/env python3
"""Capture and validate SafeNest CO2 C-C1T acquisition evidence.

The capture path records the Pi health payload before any feature processing.
It distinguishes a producer-side SCD40 measurement event from a new telemetry
packet or a recently received cached value.  The module is intentionally
standard-library only so the same code can run on a Raspberry Pi and in the
standalone evidence repository.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "datasets/co2/manifests/c_c1r_reduced_measurement_protocol/protocol.json"
CANDIDATE_LOCK_PATH = ROOT / "datasets/co2/manifests/c_b6_reduced_feature_candidate/candidate_lock.json"
CAPTURE_SCRIPT_RELPATH = "scripts/capture_co2_c_c1t_session.py"
SESSION_ID_PATTERN = re.compile(r"^CO2C1R-[0-9]{8}-[A-Z0-9]{1,8}-S[0-9]{3}$")
ALLOWED_GT_LABELS = {"VACANT", "OCCUPIED"}
ALLOWED_GT_SOURCES = {
    "CONTROLLED_EMPTY_ROOM",
    "CONTROLLED_PERSON_PRESENT",
    "RECORDED_ENTRY",
    "RECORDED_EXIT",
}
BUNDLE_FILES = (
    "raw_measurements.jsonl",
    "session_manifest.json",
    "ground_truth_events.jsonl",
    "failure_events.jsonl",
    "deviation_events.jsonl",
    "checksums.sha256",
    "operator_notes.md",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_utc_timestamp(value: str) -> dt.datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def utc_timestamp(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_context(root: Path = ROOT) -> dict[str, Any]:
    protocol_path = root / PROTOCOL_PATH.relative_to(ROOT)
    candidate_path = root / CANDIDATE_LOCK_PATH.relative_to(ROOT)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    candidate_lock = json.loads(candidate_path.read_text(encoding="utf-8"))
    target = protocol["target_candidate"]
    return {
        "protocol": protocol,
        "candidate_lock": candidate_lock,
        "protocol_path": protocol_path,
        "candidate_lock_path": candidate_path,
        "candidate_lock_sha256": sha256_file(candidate_path),
        "protocol_sha256": sha256_file(protocol_path),
        "protocol_id": protocol["protocol_id"],
        "protocol_version": protocol["protocol_version"],
        "candidate_id": target["candidate_id"],
        "candidate_lock_content_sha256": target.get("candidate_lock_content_sha256"),
        "feature_order": list(target["feature_order"]),
    }


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _payload_sensor_view(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    sensors = payload.get("sensors")
    return sensors if isinstance(sensors, Mapping) else payload


def _transport_freshness(
    sensors: Mapping[str, Any], source_error: str | None
) -> str:
    if source_error:
        return "UNAVAILABLE"
    if sensors.get("connected") is False:
        return "UNAVAILABLE"
    if sensors.get("fresh") is True:
        return "FRESH"
    if sensors.get("fresh") is False:
        return "STALE"
    if sensors.get("status") in {"stale", "error"}:
        return "STALE"
    if sensors.get("status") == "waiting":
        return "UNAVAILABLE"
    return "UNKNOWN"


def _pi_timestamp(sensors: Mapping[str, Any]) -> str | None:
    value = sensors.get("last_received_at")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return utc_timestamp(dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc))


def _device_id(sensors: Mapping[str, Any], fallback: str | None) -> str:
    value = sensors.get("device_id") or fallback
    return str(value)[:128] if value else "UNKNOWN"


def _parse_gt_event_spec(spec: str, index: int) -> dict[str, Any]:
    parts = spec.split("@", 4)
    if len(parts) < 3:
        raise ValueError(
            "--ground-truth-event format is LABEL@UTC_TIMESTAMP@SOURCE[@NOTE]"
        )
    label, start, source = (part.strip() for part in parts[:3])
    note = parts[3].strip() if len(parts) == 4 else ""
    if label not in ALLOWED_GT_LABELS:
        raise ValueError(f"unsupported ground-truth label: {label}")
    if source not in ALLOWED_GT_SOURCES:
        raise ValueError(f"unsupported ground-truth source: {source}")
    return {
        "ground_truth_event_id": f"gt-{index:04d}",
        "label": label,
        "source": source,
        "start_timestamp": utc_timestamp(parse_utc_timestamp(start)),
        "note": note,
    }


def generate_session_id(output_root: Path, operator_id: str, date: dt.date) -> str:
    operator_code = re.sub(r"[^A-Za-z0-9]", "", operator_id).upper()[:8] or "OPERATOR"
    date_code = date.strftime("%Y%m%d")
    used: set[int] = set()
    if output_root.exists():
        for child in output_root.iterdir():
            match = re.match(
                rf"^CO2C1R-{date_code}-{re.escape(operator_code)}-S([0-9]{{3}})$",
                child.name,
            )
            if match:
                used.add(int(match.group(1)))
    serial = 1
    while serial in used:
        serial += 1
    if serial > 999:
        raise RuntimeError("no available session serial for this operator/date")
    return f"CO2C1R-{date_code}-{operator_code}-S{serial:03d}"


class CaptureSession:
    """Append-only session writer with producer-event freshness classification."""

    def __init__(
        self,
        output_root: Path,
        operator_id: str,
        location_id: str,
        scenario_id: str,
        ground_truth_label: str | None,
        ground_truth_source: str,
        ground_truth_event_specs: Iterable[str] = (),
        session_id: str | None = None,
        device_id: str | None = None,
        source_kind: str = "PI_HEALTH_HTTP",
        source_endpoint: str = "http://127.0.0.1:8080/health",
        capture_interval_sec: float = 1.0,
        duration_sec: float = 60.0,
        dry_run: bool = False,
        notes: str = "",
        start_time: dt.datetime | None = None,
        now_fn: Callable[[], dt.datetime] | None = None,
        monotonic_ns_fn: Callable[[], int] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ground_truth_event_specs = list(ground_truth_event_specs)
        if ground_truth_label is None and not ground_truth_event_specs:
            raise ValueError("an independent ground-truth label or event is required")
        if ground_truth_label is not None and ground_truth_label not in ALLOWED_GT_LABELS:
            raise ValueError(f"unsupported ground-truth label: {ground_truth_label}")
        if ground_truth_source not in ALLOWED_GT_SOURCES:
            raise ValueError(f"unsupported ground-truth source: {ground_truth_source}")
        if capture_interval_sec <= 0 or duration_sec <= 0:
            raise ValueError("capture interval and duration must be positive")

        self.context = context or load_context()
        self.operator_id = operator_id
        self.location_id = location_id
        self.scenario_id = scenario_id
        self.ground_truth_label = ground_truth_label
        self.ground_truth_source = ground_truth_source
        self.device_id_override = device_id
        self.source_kind = source_kind
        self.source_endpoint = source_endpoint
        self.capture_interval_sec = capture_interval_sec
        self.duration_sec = duration_sec
        self.dry_run = dry_run
        self.notes = notes
        self._now_fn = now_fn or (lambda: dt.datetime.now(dt.timezone.utc))
        self._monotonic_ns_fn = monotonic_ns_fn or time.monotonic_ns
        self.capture_start = (start_time or self._now_fn()).astimezone(dt.timezone.utc)
        self.capture_end: dt.datetime | None = None
        self.session_id = session_id or generate_session_id(
            output_root, operator_id, self.capture_start.date()
        )
        if not SESSION_ID_PATTERN.fullmatch(self.session_id):
            raise ValueError(f"invalid generated session ID: {self.session_id}")
        self.bundle_dir = output_root / self.session_id
        if self.bundle_dir.exists():
            raise FileExistsError(f"session bundle already exists: {self.bundle_dir}")
        self.bundle_dir.mkdir(parents=True, exist_ok=False)

        specs = ground_truth_event_specs
        self._explicit_ground_truth = [
            _parse_gt_event_spec(spec, index) for index, spec in enumerate(specs, 1)
        ]
        self._last_event_by_device: dict[str, int] = {}
        self._last_event_time_by_device: dict[str, int] = {}
        self._raw_count = 0
        self._failure_count = 0
        self._deviation_count = 0
        self._fresh_count = 0
        self._cached_count = 0
        self._closed = False
        self._files = {
            "raw": self.bundle_dir / "raw_measurements.jsonl",
            "ground_truth": self.bundle_dir / "ground_truth_events.jsonl",
            "failure": self.bundle_dir / "failure_events.jsonl",
            "deviation": self.bundle_dir / "deviation_events.jsonl",
        }
        self._raw_handle = self._files["raw"].open("w", encoding="utf-8")
        self._failure_handle = self._files["failure"].open("w", encoding="utf-8")
        self._deviation_handle = self._files["deviation"].open("w", encoding="utf-8")
        self._files["ground_truth"].touch()

    def _append_jsonl(self, handle: Any, value: Mapping[str, Any]) -> None:
        handle.write(canonical_json(value) + "\n")
        handle.flush()

    def _ground_truth_at(self, timestamp: dt.datetime) -> tuple[str | None, str | None]:
        if self.ground_truth_label is not None:
            return self.ground_truth_label, "gt-0001"
        current: dict[str, Any] | None = None
        for event in self._explicit_ground_truth:
            if parse_utc_timestamp(event["start_timestamp"]) <= timestamp:
                current = event
        if current is None:
            return None, None
        return current["label"], current["ground_truth_event_id"]

    def _record_failure(
        self,
        timestamp: str,
        failure_type: str,
        raw_record_number: int,
        detail: str,
    ) -> None:
        self._failure_count += 1
        self._append_jsonl(
            self._failure_handle,
            {
                "failure_event_id": f"failure-{self._failure_count:04d}",
                "session_id": self.session_id,
                "timestamp_utc": timestamp,
                "failure_type": failure_type,
                "raw_record_number": raw_record_number,
                "detail": detail,
            },
        )

    def _record_deviation(
        self,
        timestamp: str,
        deviation_type: str,
        raw_record_number: int,
        detail: str,
    ) -> None:
        self._deviation_count += 1
        self._append_jsonl(
            self._deviation_handle,
            {
                "deviation_event_id": f"deviation-{self._deviation_count:04d}",
                "session_id": self.session_id,
                "timestamp_utc": timestamp,
                "deviation_type": deviation_type,
                "raw_record_number": raw_record_number,
                "detail": detail,
                "compliance_effect": "REVIEW_REQUIRED",
            },
        )

    def process_observation(
        self,
        payload: Mapping[str, Any] | None,
        *,
        captured_at: dt.datetime | None = None,
        logger_monotonic_ns: int | None = None,
        source_payload_text: str | None = None,
        source_error: str | None = None,
    ) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("cannot append to a finalized session")
        captured_at = (captured_at or self._now_fn()).astimezone(dt.timezone.utc)
        logger_monotonic_ns = (
            logger_monotonic_ns if logger_monotonic_ns is not None else self._monotonic_ns_fn()
        )
        timestamp = utc_timestamp(captured_at)
        self.capture_end = captured_at
        self._raw_count += 1
        raw_record_number = self._raw_count

        payload_dict = dict(payload) if isinstance(payload, Mapping) else None
        sensors = _payload_sensor_view(payload_dict or {})
        device_id = _device_id(sensors, self.device_id_override)
        transport_freshness = _transport_freshness(sensors, source_error)
        ground_truth_label, ground_truth_ref = self._ground_truth_at(captured_at)
        valid = sensors.get("valid")
        valid_map = valid if isinstance(valid, Mapping) else {}
        co2 = _number(sensors.get("co2_ppm"))
        event_id = _nonnegative_int(sensors.get("co2_measurement_event_id"))
        event_time_ms = _nonnegative_int(sensors.get("co2_measurement_monotonic_ms"))
        event_valid = sensors.get("co2_measurement_event_valid")
        marker_fields_present = all(
            key in sensors
            for key in (
                "co2_measurement_event_id",
                "co2_measurement_monotonic_ms",
                "co2_measurement_event_valid",
            )
        )
        co2_valid = valid_map.get("co2") is True
        freshness = "NO_FRESH_EVENT"
        read_status = "NO_FRESH_EVENT_OBSERVED"
        missing_or_error: str | None = None

        if source_error:
            freshness = "TRANSPORT_UNAVAILABLE"
            read_status = "TRANSPORT_ERROR"
            missing_or_error = "TRANSPORT_ERROR"
        elif not marker_fields_present or event_id is None or event_time_ms is None:
            freshness = "FRESH_EVENT_EVIDENCE_UNAVAILABLE"
            read_status = "FRESH_EVENT_MARKER_MISSING_OR_INVALID"
            missing_or_error = "FRESH_EVENT_MARKER_MISSING_OR_INVALID"
        elif not isinstance(event_valid, bool):
            freshness = "FRESH_EVENT_EVIDENCE_UNAVAILABLE"
            read_status = "FRESH_EVENT_MARKER_INVALID"
            missing_or_error = "FRESH_EVENT_MARKER_INVALID"
        elif not event_valid or event_id == 0:
            freshness = "NO_FRESH_EVENT"
            read_status = "NO_FRESH_EVENT_OBSERVED"
            missing_or_error = "NO_FRESH_EVENT_OBSERVED"
        elif co2 is None or not co2_valid:
            freshness = "INVALID_EVENT_PAYLOAD"
            read_status = "FRESH_EVENT_PAYLOAD_INVALID"
            missing_or_error = "FRESH_EVENT_PAYLOAD_INVALID"
        else:
            previous_id = self._last_event_by_device.get(device_id)
            if previous_id is None:
                freshness = "FRESH_EVENT"
                read_status = "SUCCESSFUL_FRESH_READ"
            elif event_id == previous_id:
                freshness = "CACHED_RETRANSMISSION"
                read_status = "CACHED_LAST_SUCCESSFUL_READ"
            elif event_id > previous_id:
                freshness = "FRESH_EVENT"
                read_status = "SUCCESSFUL_FRESH_READ"
            else:
                freshness = "DEVICE_EVENT_COUNTER_RESET"
                read_status = "FRESH_EVENT_COUNTER_RESET"
                missing_or_error = "DEVICE_EVENT_COUNTER_RESET_REQUIRES_NEW_SESSION"

        if freshness == "FRESH_EVENT":
            self._fresh_count += 1
            self._last_event_by_device[device_id] = event_id  # type: ignore[assignment]
            self._last_event_time_by_device[device_id] = event_time_ms  # type: ignore[assignment]
        elif freshness == "CACHED_RETRANSMISSION":
            self._cached_count += 1

        raw_row: dict[str, Any] = {
            "record_type": "co2_acquisition_observation",
            "raw_record_number": raw_record_number,
            "protocol_id": self.context["protocol_id"],
            "protocol_version": self.context["protocol_version"],
            "session_id": self.session_id,
            "target_candidate_id": self.context["candidate_id"],
            "device_id_or_explicit_unknown": device_id,
            "logger_timestamp_utc": timestamp,
            "logger_monotonic_ns": logger_monotonic_ns,
            "raw_co2_ppm": co2,
            "co2_unit": "ppm",
            "sensor_measurement_freshness": freshness,
            "transport_freshness": transport_freshness,
            "sensor_read_status": read_status,
            "missing_or_error_state": missing_or_error,
            "raw_received_payload": payload_dict,
            "raw_received_payload_text": source_payload_text
            if source_payload_text is not None
            else (canonical_json(payload_dict) if payload_dict is not None else None),
            "software_or_configuration_identity": {
                "capture_script": CAPTURE_SCRIPT_RELPATH,
                "source_kind": self.source_kind,
                "team_telemetry_schema": sensors.get("schema") or (payload_dict or {}).get("schema"),
            },
            "telemetry_sequence": _nonnegative_int(sensors.get("seq")),
            "device_uptime_ms": _nonnegative_int(sensors.get("uptime_ms")),
            "pi_receive_timestamp_utc": _pi_timestamp(sensors),
            "pi_receive_monotonic_ns": None,
            "transport_age_seconds": _number(sensors.get("age_seconds")),
            "transport_connected": sensors.get("connected"),
            "transport_status": sensors.get("status"),
            "sensor_event_id": event_id,
            "sensor_event_monotonic_ms": event_time_ms,
            "sensor_event_valid": event_valid,
            "measurement_event_id": f"{device_id}:{event_id}" if event_id else None,
            "ground_truth_ref": ground_truth_ref,
            "ground_truth_label": ground_truth_label,
        }
        if "temperature_c" in sensors:
            raw_row["temperature_c"] = _number(sensors.get("temperature_c"))
        if "relative_humidity_pct" in sensors:
            raw_row["relative_humidity_pct"] = _number(sensors.get("relative_humidity_pct"))
        self._append_jsonl(self._raw_handle, raw_row)

        if missing_or_error is not None:
            self._record_failure(
                timestamp,
                missing_or_error,
                raw_record_number,
                source_error or read_status,
            )
        if freshness == "DEVICE_EVENT_COUNTER_RESET":
            self._record_deviation(
                timestamp,
                "DEVICE_EVENT_COUNTER_RESET",
                raw_record_number,
                "producer event counter decreased; close this session and start a new one",
            )
        return raw_row

    def _materialize_ground_truth(self, end_time: dt.datetime) -> list[dict[str, Any]]:
        if self.ground_truth_label is not None:
            return [
                {
                    "ground_truth_event_id": "gt-0001",
                    "session_id": self.session_id,
                    "label": self.ground_truth_label,
                    "source": self.ground_truth_source,
                    "start_timestamp": utc_timestamp(self.capture_start),
                    "end_or_transition_timestamp": utc_timestamp(end_time),
                    "ground_truth_status": "COMPLETE_STABLE_SEGMENT",
                    "operator_id": self.operator_id,
                    "location_id": self.location_id,
                    "scenario_id": self.scenario_id,
                    "derived_from_sensor_or_model": False,
                }
            ]
        events: list[dict[str, Any]] = []
        for event in self._explicit_ground_truth:
            events.append(
                {
                    **event,
                    "session_id": self.session_id,
                    "end_or_transition_timestamp": None,
                    "ground_truth_status": "RECORDED_TRANSITION_EVENT",
                    "operator_id": self.operator_id,
                    "location_id": self.location_id,
                    "scenario_id": self.scenario_id,
                    "derived_from_sensor_or_model": False,
                }
            )
        return events

    def finalize(self, end_time: dt.datetime | None = None) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("session is already finalized")
        final_time = (
            end_time
            or self.capture_end
            or self._now_fn()
        ).astimezone(dt.timezone.utc)
        if final_time < self.capture_start:
            raise ValueError("capture end precedes capture start")
        self.capture_end = final_time
        ground_truth_events = self._materialize_ground_truth(final_time)
        gt_path = self._files["ground_truth"]
        with gt_path.open("w", encoding="utf-8") as handle:
            for event in ground_truth_events:
                handle.write(canonical_json(event) + "\n")
        self._raw_handle.close()
        self._failure_handle.close()
        self._deviation_handle.close()

        manifest = {
            "manifest_version": "1.0",
            "phase": "C-C1T",
            "session_id": self.session_id,
            "session_status": "FINALIZED",
            "measurement_protocol_id": self.context["protocol_id"],
            "measurement_protocol_version": self.context["protocol_version"],
            "target_candidate_id": self.context["candidate_id"],
            "candidate_lock_sha256": self.context["candidate_lock_sha256"],
            "candidate_lock_content_sha256": self.context["candidate_lock_content_sha256"],
            "feature_order": self.context["feature_order"],
            "operator_id": self.operator_id,
            "location_id": self.location_id,
            "scenario_id": self.scenario_id,
            "device_identity": self.device_id_override or "RECORDED_PER_ROW_OR_UNKNOWN",
            "capture_start_timestamp_utc": utc_timestamp(self.capture_start),
            "capture_end_timestamp_utc": utc_timestamp(final_time),
            "capture_duration_sec": round((final_time - self.capture_start).total_seconds(), 3),
            "capture_mode": "DRY_RUN_FIXTURE" if self.dry_run else "LIVE_NETWORK_CAPTURE",
            "capture_configuration": {
                "source_kind": self.source_kind,
                "source_endpoint_label": self.source_endpoint,
                "configured_capture_poll_interval_sec": self.capture_interval_sec,
                "requested_duration_sec": self.duration_sec,
                "effective_model_input_interval_sec": 60,
                "effective_model_input_cadence": "NOMINAL",
                "native_sensor_cadence_separate": True,
            },
            "capture_software": {
                "script": CAPTURE_SCRIPT_RELPATH,
                "language": "Python standard library",
                "model_inference_performed": False,
                "preprocessing_performed": False,
            },
            "freshness_contract_applied": {
                "transport_freshness_is_sensor_freshness": False,
                "same_event_id_is_cached_retransmission": True,
                "stale_reuse": False,
                "synthetic_fill": False,
                "missing_event_recording": True,
            },
            "counts": {
                "raw_records": self._raw_count,
                "fresh_events": self._fresh_count,
                "cached_retransmissions": self._cached_count,
                "failure_events": self._failure_count,
                "deviation_events": self._deviation_count,
                "ground_truth_events": len(ground_truth_events),
            },
            "physical_measurement_claim": (
                "NOT_CLAIMED_FOR_DRY_RUN" if self.dry_run else "LIVE_CAPTURE_EVIDENCE_ONLY"
            ),
            "files": {name: name for name in BUNDLE_FILES},
            "operator_notes": self.notes,
        }
        write_json(self.bundle_dir / "session_manifest.json", manifest)
        note_text = (
            "# Operator notes\n\n"
            f"- session_id: `{self.session_id}`\n"
            f"- capture_mode: `{manifest['capture_mode']}`\n"
            f"- physical_measurement_claim: `{manifest['physical_measurement_claim']}`\n"
            f"- notes: {self.notes or 'none'}\n"
            "\nThis file is finalized with the session bundle. Do not edit prior rows.\n"
        )
        (self.bundle_dir / "operator_notes.md").write_text(note_text, encoding="utf-8")
        self._write_checksums()
        self._closed = True
        return manifest

    def _write_checksums(self) -> None:
        checksum_path = self.bundle_dir / "checksums.sha256"
        lines = []
        for filename in sorted(name for name in BUNDLE_FILES if name != "checksums.sha256"):
            path = self.bundle_dir / filename
            lines.append(f"{sha256_file(path)}  {filename}")
        checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.name}:{line_number}: row is not an object")
            continue
        rows.append(value)
    return rows, errors


def validate_session_bundle(bundle_dir: Path, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the immutable session bundle without performing model inference."""

    context = context or load_context()
    errors: list[str] = []
    warnings: list[str] = []
    if not bundle_dir.is_dir():
        return {"status": "FAIL", "errors": [f"missing bundle directory: {bundle_dir}"]}
    for filename in BUNDLE_FILES:
        if not (bundle_dir / filename).is_file():
            errors.append(f"missing bundle file: {filename}")
    if errors:
        return {"status": "FAIL", "errors": errors, "warnings": warnings}

    checksum_entries: dict[str, str] = {}
    for line_number, line in enumerate(
        (bundle_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split(None, 1)
        if len(parts) != 2:
            errors.append(f"checksums.sha256:{line_number}: malformed line")
            continue
        checksum_entries[parts[1].strip()] = parts[0]
    for filename in BUNDLE_FILES:
        if filename == "checksums.sha256":
            continue
        expected = checksum_entries.get(filename)
        if expected is None:
            errors.append(f"checksum missing for {filename}")
        elif sha256_file(bundle_dir / filename) != expected:
            errors.append(f"checksum mismatch for {filename}")

    try:
        manifest = json.loads((bundle_dir / "session_manifest.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"status": "FAIL", "errors": errors + [f"invalid session manifest: {exc}"]}
    session_id = manifest.get("session_id")
    if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(session_id):
        errors.append("session_manifest.session_id is invalid")
    if manifest.get("session_status") != "FINALIZED":
        errors.append("session manifest is not FINALIZED")
    expected_manifest_values = {
        "measurement_protocol_id": context["protocol_id"],
        "measurement_protocol_version": context["protocol_version"],
        "target_candidate_id": context["candidate_id"],
        "candidate_lock_sha256": context["candidate_lock_sha256"],
    }
    for key, expected in expected_manifest_values.items():
        if manifest.get(key) != expected:
            errors.append(f"session manifest {key} does not match live lock")
    config = manifest.get("capture_configuration")
    if not isinstance(config, dict) or config.get("effective_model_input_interval_sec") != 60:
        errors.append("60-second effective model-input cadence is not declared")
    if not isinstance(config, dict) or config.get("native_sensor_cadence_separate") is not True:
        errors.append("native sensor cadence is not separated from effective cadence")

    raw_rows, raw_errors = _read_jsonl(bundle_dir / "raw_measurements.jsonl")
    gt_rows, gt_errors = _read_jsonl(bundle_dir / "ground_truth_events.jsonl")
    failure_rows, failure_errors = _read_jsonl(bundle_dir / "failure_events.jsonl")
    deviation_rows, deviation_errors = _read_jsonl(bundle_dir / "deviation_events.jsonl")
    errors.extend(raw_errors + gt_errors + failure_errors + deviation_errors)
    required_raw_fields = {
        "protocol_id",
        "protocol_version",
        "session_id",
        "target_candidate_id",
        "device_id_or_explicit_unknown",
        "logger_timestamp_utc",
        "logger_monotonic_ns",
        "raw_co2_ppm",
        "co2_unit",
        "sensor_measurement_freshness",
        "transport_freshness",
        "sensor_read_status",
        "missing_or_error_state",
        "raw_received_payload",
        "software_or_configuration_identity",
    }
    previous_monotonic: int | None = None
    previous_event_by_device: dict[str, int] = {}
    previous_event_time_by_device: dict[str, int] = {}
    fresh_rows = 0
    cached_rows = 0
    for row in raw_rows:
        missing = sorted(required_raw_fields - row.keys())
        if missing:
            errors.append(
                f"raw record {row.get('raw_record_number', '?')} missing fields: {', '.join(missing)}"
            )
        if row.get("protocol_id") != context["protocol_id"]:
            errors.append("raw row protocol_id mismatch")
        if row.get("protocol_version") != context["protocol_version"]:
            errors.append("raw row protocol_version mismatch")
        if row.get("session_id") != session_id:
            errors.append("raw row session_id mismatch")
        if row.get("target_candidate_id") != context["candidate_id"]:
            errors.append("raw row target candidate mismatch")
        if "CO2_slope" in row or "co2_slope" in row:
            errors.append("raw layer contains derived CO2_slope")
        monotonic = row.get("logger_monotonic_ns")
        if isinstance(monotonic, int) and not isinstance(monotonic, bool):
            if previous_monotonic is not None and monotonic < previous_monotonic:
                errors.append("logger monotonic chronology decreased")
            previous_monotonic = monotonic
        else:
            errors.append("raw row logger_monotonic_ns is not an integer")
        freshness = row.get("sensor_measurement_freshness")
        device = str(row.get("device_id_or_explicit_unknown"))
        event_id = row.get("sensor_event_id")
        event_time = row.get("sensor_event_monotonic_ms")
        if freshness == "FRESH_EVENT":
            fresh_rows += 1
            if not isinstance(event_id, int) or isinstance(event_id, bool) or event_id <= 0:
                errors.append("FRESH_EVENT row lacks a positive sensor event id")
            if not isinstance(event_time, int) or isinstance(event_time, bool):
                errors.append("FRESH_EVENT row lacks sensor event chronology")
            if row.get("sensor_event_valid") is not True:
                errors.append("FRESH_EVENT row is not marked event-valid")
            if row.get("sensor_read_status") != "SUCCESSFUL_FRESH_READ":
                errors.append("FRESH_EVENT row has an inconsistent sensor_read_status")
            if _number(row.get("raw_co2_ppm")) is None:
                errors.append("FRESH_EVENT row has no numeric CO2 value")
            previous = previous_event_by_device.get(device)
            if previous is not None and event_id <= previous:
                errors.append("fresh event id did not increase")
            previous_time = previous_event_time_by_device.get(device)
            if previous_time is not None and event_time <= previous_time:
                errors.append("fresh event chronology did not increase")
            previous_event_by_device[device] = event_id  # type: ignore[assignment]
            previous_event_time_by_device[device] = event_time  # type: ignore[assignment]
        elif freshness == "CACHED_RETRANSMISSION":
            cached_rows += 1
            if not isinstance(event_id, int) or event_id <= 0:
                errors.append("cached retransmission lacks event identity")
            elif previous_event_by_device.get(device) != event_id:
                errors.append("cached retransmission event identity changed unexpectedly")
        elif freshness == "DEVICE_EVENT_COUNTER_RESET":
            errors.append("device event counter reset requires a new session")
        elif freshness == "FRESH_EVENT_EVIDENCE_UNAVAILABLE":
            if not row.get("missing_or_error_state"):
                errors.append("missing fresh-event evidence has no failure state")
        elif freshness not in {
            "NO_FRESH_EVENT",
            "TRANSPORT_UNAVAILABLE",
            "INVALID_EVENT_PAYLOAD",
        }:
            errors.append(f"unknown sensor freshness classification: {freshness!r}")

    gt_ids: set[str] = set()
    for event in gt_rows:
        event_id = event.get("ground_truth_event_id")
        if not isinstance(event_id, str) or event_id in gt_ids:
            errors.append("ground-truth event ID is missing or duplicated")
        else:
            gt_ids.add(event_id)
        if event.get("session_id") != session_id:
            errors.append("ground-truth session ID mismatch")
        if event.get("label") not in ALLOWED_GT_LABELS:
            errors.append("ground-truth label is not VACANT/OCCUPIED")
        if event.get("source") not in ALLOWED_GT_SOURCES:
            errors.append("ground-truth source is not an allowed controlled source")
        if event.get("derived_from_sensor_or_model") is not False:
            errors.append("ground truth is not explicitly independent")
        for required in (
            "start_timestamp",
            "ground_truth_status",
            "operator_id",
        ):
            if not event.get(required):
                errors.append(f"ground-truth event missing {required}")
    if not gt_rows:
        errors.append("ground-truth event log is empty")
    for row in raw_rows:
        ref = row.get("ground_truth_ref")
        if ref is not None and ref not in gt_ids:
            errors.append(f"raw row references unknown ground truth event: {ref}")
    if fresh_rows == 0:
        errors.append("bundle contains no verified fresh SCD40 measurement event")
    if failure_rows:
        warnings.append(f"bundle preserves {len(failure_rows)} failure event(s)")
    if deviation_rows:
        warnings.append(f"bundle preserves {len(deviation_rows)} deviation event(s)")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "session_id": session_id,
        "counts": {
            "raw_records": len(raw_rows),
            "fresh_events": fresh_rows,
            "cached_retransmissions": cached_rows,
            "ground_truth_events": len(gt_rows),
            "failure_events": len(failure_rows),
            "deviation_events": len(deviation_rows),
        },
    }


def fetch_json(url: str, timeout_sec: float) -> tuple[dict[str, Any], str]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        raw = response.read().decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("source JSON root is not an object")
    return payload, raw


def _fixture_observations(
    path: Path,
) -> Iterable[tuple[dict[str, Any] | None, dt.datetime, int, str | None, str | None]]:
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        envelope = json.loads(line)
        if not isinstance(envelope, dict):
            raise ValueError(f"fixture line {line_number} must contain an object")
        payload = envelope.get("payload")
        source_error = envelope.get("source_error")
        if payload is not None and not isinstance(payload, dict):
            raise ValueError(f"fixture line {line_number} payload must be an object or null")
        if source_error is not None and not isinstance(source_error, str):
            raise ValueError(f"fixture line {line_number} source_error must be a string")
        captured_at = parse_utc_timestamp(str(envelope["captured_at_utc"]))
        monotonic = _nonnegative_int(envelope.get("logger_monotonic_ns"))
        if monotonic is None:
            raise ValueError(f"fixture line {line_number} has invalid logger_monotonic_ns")
        yield (
            payload,
            captured_at,
            monotonic,
            canonical_json(payload) if payload is not None else None,
            source_error,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--location-id", required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--ground-truth", choices=sorted(ALLOWED_GT_LABELS))
    parser.add_argument("--ground-truth-source", default="CONTROLLED_EMPTY_ROOM", choices=sorted(ALLOWED_GT_SOURCES))
    parser.add_argument(
        "--ground-truth-event",
        action="append",
        default=[],
        help="LABEL@UTC_TIMESTAMP@SOURCE[@NOTE]; repeat for transition events",
    )
    parser.add_argument("--device-id")
    parser.add_argument("--session-id")
    parser.add_argument("--source-url", default="http://127.0.0.1:8080/health")
    parser.add_argument("--fixture-jsonl", type=Path)
    parser.add_argument("--duration-sec", type=float, default=60.0)
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=float, default=3.0)
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--start-time-utc",
        help="optional ISO-8601 session start; useful for deterministic fixtures",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if (args.ground_truth is None) == (not args.ground_truth_event):
        print("provide exactly one of --ground-truth or --ground-truth-event", file=sys.stderr)
        return 2
    try:
        session = CaptureSession(
            output_root=args.output_root,
            operator_id=args.operator_id,
            location_id=args.location_id,
            scenario_id=args.scenario_id,
            ground_truth_label=args.ground_truth,
            ground_truth_source=args.ground_truth_source,
            ground_truth_event_specs=args.ground_truth_event,
            session_id=args.session_id,
            device_id=args.device_id,
            source_endpoint=args.source_url,
            capture_interval_sec=args.interval_sec,
            duration_sec=args.duration_sec,
            dry_run=args.fixture_jsonl is not None,
            notes=args.notes,
            start_time=parse_utc_timestamp(args.start_time_utc)
            if args.start_time_utc
            else None,
        )
        last_time: dt.datetime | None = None
        if args.fixture_jsonl is not None:
            for payload, captured_at, monotonic, raw_text, source_error in _fixture_observations(
                args.fixture_jsonl
            ):
                session.process_observation(
                    payload,
                    captured_at=captured_at,
                    logger_monotonic_ns=monotonic,
                    source_payload_text=raw_text,
                    source_error=source_error,
                )
                last_time = captured_at
        else:
            deadline = time.monotonic() + args.duration_sec
            while time.monotonic() < deadline or session._raw_count == 0:
                started = time.monotonic()
                try:
                    payload, raw_text = fetch_json(args.source_url, args.timeout_sec)
                    session.process_observation(
                        payload,
                        source_payload_text=raw_text,
                    )
                except (OSError, ValueError, urllib.error.URLError) as exc:
                    session.process_observation(
                        None,
                        source_error=f"{type(exc).__name__}: {exc}",
                    )
                elapsed = time.monotonic() - started
                remaining = args.interval_sec - elapsed
                if remaining > 0 and time.monotonic() < deadline:
                    time.sleep(remaining)
        manifest = session.finalize(end_time=last_time)
        validation = validate_session_bundle(session.bundle_dir, session.context)
        print(
            json.dumps(
                {"bundle_dir": str(session.bundle_dir), "manifest": manifest, "validation": validation},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if validation["status"] == "PASS" else 1
    except (OSError, ValueError, RuntimeError, FileExistsError) as exc:
        print(f"C-C1T capture failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
