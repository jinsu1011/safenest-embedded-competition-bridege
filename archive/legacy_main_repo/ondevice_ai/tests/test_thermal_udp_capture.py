"""Regression tests for fail-closed Thermal raw UDP V2 reassembly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.thermal_udp_capture import (  # noqa: E402
    CHUNK_COUNT,
    CHUNK_DATAGRAM_BYTES,
    CHUNK_HEADER_BYTES,
    CHUNK_PAYLOAD_BYTES,
    FRAME_BYTES,
    ChunkProtocolError,
    CaptureWriter,
    FramedChunkReassembler,
    SenderStatus,
    decode_framed_chunk,
    decode_sender_status,
    encode_framed_frame,
    encode_sender_status,
    parse_args,
)
from scripts.validate_thermal_real_capture import validate_capture  # noqa: E402


PEER = ("192.0.2.10", 40000)


def _frame(seed: int) -> bytes:
    return bytes(((index * 17) + seed) & 0xFF for index in range(FRAME_BYTES))


def _frame_with_word0(value: int, seed: int = 0) -> bytes:
    frame = bytearray(_frame(seed))
    frame[:2] = int(value).to_bytes(2, "little")
    return bytes(frame)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _refresh_checksums(session_dir: Path) -> None:
    rows = []
    for path in sorted(session_dir.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            relative = path.relative_to(session_dir).as_posix()
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    (session_dir / "checksums.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_v2_contract_stays_mtu_safe_and_preserves_full_raw_frame() -> None:
    payload = _frame(3)
    datagrams = encode_framed_frame(payload, frame_id=42)

    assert CHUNK_HEADER_BYTES == 32
    assert CHUNK_PAYLOAD_BYTES == 1168
    assert CHUNK_COUNT == 9
    assert len(datagrams) == CHUNK_COUNT
    assert all(len(item) <= CHUNK_DATAGRAM_BYTES for item in datagrams)

    reassembler = FramedChunkReassembler()
    completed = None
    for index, datagram in enumerate(datagrams):
        completed = reassembler.accept(datagram, PEER, received_monotonic=index * 0.01)
    assert completed is not None
    rebuilt, metadata = completed
    assert rebuilt == payload
    assert metadata["transport_frame_id"] == 42
    assert metadata["chunk_count"] == 9
    assert reassembler.metrics.completed_frames == 1
    assert reassembler.metrics.incomplete_frames == 0


def test_sender_status_packet_round_trip_preserves_observed_counters() -> None:
    expected = SenderStatus(
        sender_uptime_ms=123456,
        d_ready_events_observed=100,
        dropped_ready_signals=3,
        transport_frames_attempted=97,
        transport_frames_emitted=95,
        send_failures=2,
    )
    assert decode_sender_status(encode_sender_status(expected)) == expected


def test_out_of_order_chunks_are_reassembled_by_explicit_index() -> None:
    payload = _frame(7)
    datagrams = encode_framed_frame(payload, frame_id=100)
    order = [3, 0, 8, 2, 1, 7, 6, 5, 4]
    reassembler = FramedChunkReassembler()

    completed = None
    for tick, index in enumerate(order):
        result = reassembler.accept(datagrams[index], PEER, received_monotonic=tick * 0.01)
        if result is not None:
            completed = result

    assert completed is not None
    assert completed[0] == payload
    assert reassembler.metrics.out_of_order_chunks > 0
    assert reassembler.metrics.incomplete_frames == 0


def test_lost_chunk_cannot_desynchronize_the_following_frame() -> None:
    first = _frame(11)
    second = _frame(19)
    first_datagrams = encode_framed_frame(first, frame_id=200)
    second_datagrams = encode_framed_frame(second, frame_id=201)
    reassembler = FramedChunkReassembler(frame_timeout_seconds=0.5)

    for index, datagram in enumerate(first_datagrams):
        if index != 4:
            assert reassembler.accept(datagram, PEER, received_monotonic=index * 0.01) is None

    completed = None
    for index, datagram in enumerate(second_datagrams):
        result = reassembler.accept(datagram, PEER, received_monotonic=0.20 + index * 0.01)
        if result is not None:
            completed = result

    assert completed is not None
    assert completed[0] == second
    assert completed[1]["transport_frame_id"] == 201
    assert reassembler.evict_expired(now=1.0) == 1
    assert reassembler.metrics.incomplete_frames == 1
    assert reassembler.metrics.completed_frames == 1


def test_duplicate_chunk_is_ignored_without_duplicate_frame() -> None:
    payload = _frame(23)
    datagrams = encode_framed_frame(payload, frame_id=300)
    reassembler = FramedChunkReassembler()

    assert reassembler.accept(datagrams[0], PEER, received_monotonic=0.0) is None
    assert reassembler.accept(datagrams[0], PEER, received_monotonic=0.01) is None
    completed = None
    for index, datagram in enumerate(datagrams[1:], 1):
        completed = reassembler.accept(datagram, PEER, received_monotonic=0.01 + index * 0.01)

    assert completed is not None
    assert completed[0] == payload
    assert reassembler.metrics.duplicate_chunks == 1
    assert reassembler.metrics.completed_frames == 1


def test_conflicting_duplicate_discards_the_pending_frame() -> None:
    datagrams = encode_framed_frame(_frame(29), frame_id=400)
    reassembler = FramedChunkReassembler()
    assert reassembler.accept(datagrams[0], PEER, received_monotonic=0.0) is None

    conflicting = bytearray(datagrams[0])
    conflicting[-1] ^= 0xFF
    assert reassembler.accept(bytes(conflicting), PEER, received_monotonic=0.01) is None
    assert reassembler.metrics.conflicting_duplicates == 1
    assert reassembler.metrics.incomplete_frames == 1
    assert not reassembler.pending


def test_whole_frame_crc_rejects_payload_corruption() -> None:
    datagrams = encode_framed_frame(_frame(31), frame_id=500)
    corrupted = bytearray(datagrams[5])
    corrupted[-1] ^= 0x01
    datagrams[5] = bytes(corrupted)
    reassembler = FramedChunkReassembler()

    assert all(
        reassembler.accept(datagram, PEER, received_monotonic=index * 0.01) is None
        for index, datagram in enumerate(datagrams)
    )
    assert reassembler.metrics.checksum_failures == 1
    assert reassembler.metrics.completed_frames == 0


def test_transport_frame_id_corruption_remains_fail_closed() -> None:
    datagrams = encode_framed_frame(_frame(33), frame_id=800)
    corrupted = bytearray(datagrams[4])
    corrupted[8:12] = (801).to_bytes(4, "big")
    datagrams[4] = bytes(corrupted)
    reassembler = FramedChunkReassembler()
    assert all(
        reassembler.accept(datagram, PEER, received_monotonic=index * 0.01) is None
        for index, datagram in enumerate(datagrams)
    )
    assert reassembler.finalize() == 2
    assert reassembler.metrics.incomplete_frames == 2
    assert reassembler.metrics.completed_frames == 0


def test_decoder_rejects_bad_magic_and_offset() -> None:
    datagram = bytearray(encode_framed_frame(_frame(37), frame_id=600)[0])
    datagram[0:4] = b"BAD!"
    with pytest.raises(ChunkProtocolError):
        decode_framed_chunk(bytes(datagram))

    datagram = bytearray(encode_framed_frame(_frame(37), frame_id=600)[1])
    datagram[20:24] = (0).to_bytes(4, "big")
    with pytest.raises(ChunkProtocolError):
        decode_framed_chunk(bytes(datagram))


def test_legacy_and_v2_reassembly_modes_are_mutually_exclusive() -> None:
    required = [
        "--output", "out",
        "--collection-id", "C001",
        "--subject-id", "S001",
        "--session-id", "session_001",
        "--operator-code", "OP001",
    ]
    with pytest.raises(SystemExit):
        parse_args(required + ["--reassemble-udp-chunks", "--legacy-stream-reassembly"])


def _capture_args(tmp_path: Path, session_id: str):
    return parse_args(
        [
            "--output", str(tmp_path),
            "--collection-id", "collection_v2",
            "--subject-id", "S001",
            "--session-id", session_id,
            "--operator-code", "OP001",
            "--source-label", "EMPTY",
            "--reassemble-udp-chunks",
        ]
    )


def _write_complete_v2_capture(tmp_path: Path, session_id: str = "session_v2_complete") -> CaptureWriter:
    writer = CaptureWriter(_capture_args(tmp_path, session_id))
    writer.prepare()
    reassembler = FramedChunkReassembler()
    completed = None
    for index, datagram in enumerate(encode_framed_frame(_frame_with_word0(10, 41), frame_id=700)):
        writer.record_udp_chunk(datagram, index)
        result = reassembler.accept(datagram, PEER, received_monotonic=index * 0.01)
        if result is not None:
            completed = result
    assert completed is not None
    writer.record_valid_datagram(completed[0], transport_metadata=completed[1])
    status_packet = encode_sender_status(
        SenderStatus(
            sender_uptime_ms=30000,
            d_ready_events_observed=31,
            dropped_ready_signals=1,
            transport_frames_attempted=30,
            transport_frames_emitted=29,
            send_failures=1,
        )
    )
    writer.record_udp_chunk(status_packet, 9)
    writer.record_sender_status(status_packet)
    writer.transport_metrics = reassembler.snapshot()
    writer.close()
    return writer


@pytest.mark.parametrize(
    ("values", "observation_code"),
    [
        ([10, 10], "SENSOR_HEADER_WORD0_DUPLICATE_OBSERVED_SEMANTICS_UNVERIFIED"),
        ([10, 9], "SENSOR_HEADER_WORD0_REVERSAL_OBSERVED_SEMANTICS_UNVERIFIED"),
        ([10, 13], "SENSOR_HEADER_WORD0_GAP_OBSERVED_SEMANTICS_UNVERIFIED"),
    ],
)
def test_unverified_header_word0_patterns_do_not_create_sensor_failures_or_missing_frames(
    tmp_path: Path,
    values: list[int],
    observation_code: str,
) -> None:
    writer = CaptureWriter(_capture_args(tmp_path, "session_word0_" + str(values[-1])))
    writer.prepare()
    for frame_id, value in enumerate(values):
        writer.record_valid_datagram(
            _frame_with_word0(value, frame_id),
            transport_metadata={
                "protocol": "SAFENEST_THERMAL_RAW_UDP_V2",
                "transport_frame_id": frame_id,
                "chunk_count": CHUNK_COUNT,
                "frame_crc32": "00000000",
                "reassembly_seconds": 0.01,
            },
        )
    metrics = FramedChunkReassembler().snapshot()
    metrics["completed_frames"] = len(values)
    writer.transport_metrics = metrics
    writer.close()

    frames = _read_jsonl(writer.frames_path)
    assert len(frames) == len(values)
    assert all(frame["validity_status"] == "VALID" for frame in frames)
    assert all(frame["sensor_frame_counter"] is None for frame in frames)
    assert all(frame["sensor_frame_counter_status"] == "UNKNOWN" for frame in frames)
    assert not any(frame["validity_status"] == "MISSING" for frame in frames)

    result = validate_capture(writer.collection_dir)
    error_codes = {item["code"] for item in result["errors"]}
    warning_codes = {item["code"] for item in result["warnings"]}
    assert not error_codes & {"DUPLICATE_SENSOR_COUNTER", "SENSOR_COUNTER_REVERSAL"}
    assert observation_code in warning_codes


@pytest.mark.parametrize(
    ("counter_values", "expected_code"),
    [
        ([10, 10], "DUPLICATE_SENSOR_COUNTER"),
        ([10, 9], "SENSOR_COUNTER_REVERSAL"),
        ([10, 13], "SENSOR_COUNTER_GAP"),
    ],
)
def test_verified_sensor_counter_rules_remain_active(
    tmp_path: Path,
    counter_values: list[int],
    expected_code: str,
) -> None:
    writer = CaptureWriter(_capture_args(tmp_path, "session_verified_" + str(counter_values[-1])))
    writer.prepare()
    for frame_id, value in enumerate(counter_values):
        writer.record_valid_datagram(_frame_with_word0(value, frame_id))
    writer.close()
    frames = _read_jsonl(writer.frames_path)
    for frame, counter in zip(frames, counter_values):
        frame["sensor_frame_counter"] = counter
        frame["sensor_frame_counter_status"] = "VERIFIED"
    writer.frames_path.write_text(
        "".join(json.dumps(frame, sort_keys=True) + "\n" for frame in frames),
        encoding="utf-8",
    )
    _refresh_checksums(writer.session_dir)
    result = validate_capture(writer.collection_dir)
    assert expected_code in {
        item["code"] for item in result["errors"] + result["warnings"]
    }


def test_v2_artifacts_pass_real_capture_validator(tmp_path: Path) -> None:
    args = _capture_args(tmp_path, "session_v2_valid")
    writer = CaptureWriter(args)
    writer.prepare()
    reassembler = FramedChunkReassembler()
    completed = None
    for index, datagram in enumerate(encode_framed_frame(_frame(41), frame_id=700)):
        writer.record_udp_chunk(datagram, index)
        result = reassembler.accept(datagram, PEER, received_monotonic=index * 0.01)
        if result is not None:
            completed = result
    assert completed is not None
    writer.record_valid_datagram(completed[0], transport_metadata=completed[1])
    writer.transport_metrics = reassembler.snapshot()
    writer.close()

    result = validate_capture(writer.collection_dir)
    assert result["capture_status"] == "CAPTURE_STRUCTURE_VALID_WITH_LIMITATIONS"
    assert result["errors"] == []
    session = result["sessions"][0]
    assert session["valid_frame_count"] == 1


def test_v2_incomplete_frame_is_retained_and_validator_fails_closed(tmp_path: Path) -> None:
    args = _capture_args(tmp_path, "session_v2_incomplete")
    writer = CaptureWriter(args)
    writer.prepare()
    reassembler = FramedChunkReassembler()
    datagrams = encode_framed_frame(_frame(43), frame_id=701)
    for index, datagram in enumerate(datagrams[:-1]):
        writer.record_udp_chunk(datagram, index)
        assert reassembler.accept(datagram, PEER, received_monotonic=index * 0.01) is None
    reassembler.finalize()
    writer.transport_metrics = reassembler.snapshot()
    writer.close()

    result = validate_capture(writer.collection_dir)
    codes = {item["code"] for item in result["errors"]}
    assert result["capture_status"] == "CAPTURE_INVALID"
    assert "FRAMED_UDP_V2_INTEGRITY_FAILED" in codes


def test_complete_raw_chunk_inventory_passes(tmp_path: Path) -> None:
    writer = _write_complete_v2_capture(tmp_path)
    result = validate_capture(writer.collection_dir)
    assert result["errors"] == []
    session_result = result["sessions"][0]
    assert session_result["sender_telemetry"]["status"] == "MACHINE_READABLE_STATUS_RECEIVED"
    assert session_result["sender_telemetry"]["latest"]["d_ready_events_observed"] == 31
    assert len(list(writer.raw_chunks_dir.glob("*.bin"))) == 10
    checksum_paths = {
        line.split("  ", 1)[1]
        for line in writer.checksums_path.read_text(encoding="utf-8").splitlines()
    }
    assert "sender_telemetry.jsonl" in checksum_paths
    assert len([path for path in checksum_paths if path.startswith("raw_chunks/")]) == 10


def test_legacy_sender_status_field_is_accepted_with_semantic_warning(tmp_path: Path) -> None:
    writer = _write_complete_v2_capture(tmp_path, "session_legacy_sender_status")
    record = json.loads(writer.sender_telemetry_path.read_text(encoding="utf-8"))
    record["schema_version"] = "safenest.thermal.sender_status.v1"
    record["ready_signals_generated"] = record.pop("d_ready_events_observed")
    record["semantics"]["ready_signals_generated"] = record["semantics"].pop("d_ready_events_observed")
    writer.sender_telemetry_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    _refresh_checksums(writer.session_dir)

    result = validate_capture(writer.collection_dir)
    assert result["errors"] == []
    assert "LEGACY_D_READY_FIELD_NAME" in {item["code"] for item in result["warnings"]}


def test_deleted_raw_chunk_is_detected(tmp_path: Path) -> None:
    writer = _write_complete_v2_capture(tmp_path, "session_chunk_deleted")
    next(writer.raw_chunks_dir.iterdir()).unlink()
    result = validate_capture(writer.collection_dir)
    assert "RAW_CHUNK_FILE_MISSING" in {item["code"] for item in result["errors"]}


def test_modified_raw_chunk_is_detected(tmp_path: Path) -> None:
    writer = _write_complete_v2_capture(tmp_path, "session_chunk_modified")
    path = next(writer.raw_chunks_dir.iterdir())
    path.write_bytes(path.read_bytes() + b"tampered")
    result = validate_capture(writer.collection_dir)
    assert "RAW_CHUNK_CHECKSUM_MISMATCH" in {item["code"] for item in result["errors"]}


def test_raw_chunk_checksum_entry_removal_is_detected(tmp_path: Path) -> None:
    writer = _write_complete_v2_capture(tmp_path, "session_chunk_registry_missing")
    lines = writer.checksums_path.read_text(encoding="utf-8").splitlines()
    removed = False
    retained = []
    for line in lines:
        if not removed and "  raw_chunks/" in line:
            removed = True
            continue
        retained.append(line)
    assert removed
    writer.checksums_path.write_text("\n".join(retained) + "\n", encoding="utf-8")
    result = validate_capture(writer.collection_dir)
    codes = {item["code"] for item in result["errors"]}
    assert "RAW_CHUNK_CHECKSUM_MISSING" in codes
    assert "EXTRA_UNREGISTERED_RAW_CHUNK" in codes


def test_extra_unregistered_raw_chunk_is_detected(tmp_path: Path) -> None:
    writer = _write_complete_v2_capture(tmp_path, "session_chunk_extra")
    (writer.raw_chunks_dir / "chunk_extra.bin").write_bytes(b"not registered")
    result = validate_capture(writer.collection_dir)
    codes = {item["code"] for item in result["errors"]}
    assert "RAW_CHUNK_CHECKSUM_MISSING" in codes
    assert "EXTRA_UNREGISTERED_RAW_CHUNK" in codes


def test_duplicate_raw_chunk_checksum_entry_is_detected(tmp_path: Path) -> None:
    writer = _write_complete_v2_capture(tmp_path, "session_chunk_duplicate_registry")
    lines = writer.checksums_path.read_text(encoding="utf-8").splitlines()
    raw_chunk_line = next(line for line in lines if "  raw_chunks/" in line)
    writer.checksums_path.write_text("\n".join(lines + [raw_chunk_line]) + "\n", encoding="utf-8")
    result = validate_capture(writer.collection_dir)
    assert "RAW_CHUNK_CHECKSUM_DUPLICATE" in {item["code"] for item in result["errors"]}


def test_absent_sender_telemetry_is_an_explicit_limitation(tmp_path: Path) -> None:
    args = _capture_args(tmp_path, "session_sender_status_absent")
    writer = CaptureWriter(args)
    writer.prepare()
    reassembler = FramedChunkReassembler()
    completed = None
    for index, datagram in enumerate(encode_framed_frame(_frame(47), frame_id=702)):
        writer.record_udp_chunk(datagram, index)
        result = reassembler.accept(datagram, PEER, received_monotonic=index * 0.01)
        if result is not None:
            completed = result
    assert completed is not None
    writer.record_valid_datagram(completed[0], transport_metadata=completed[1])
    writer.transport_metrics = reassembler.snapshot()
    writer.close()
    result = validate_capture(writer.collection_dir)
    session = result["sessions"][0]
    assert "SENDER_SIDE_ACQUISITION_LOSS_NOT_FULLY_OBSERVABLE_FROM_PI_CAPTURE" in session["limitations"]
