#!/usr/bin/env python3
"""Replay presence candidates against the same empty/occupied raw logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable


def load(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def two_of_three(records: list[dict[str, Any]]) -> list[bool]:
    result: list[bool] = []
    recent: list[bool] = []
    for record in records:
        recent.append(record.get("human_detected_raw") is True)
        recent = recent[-3:]
        result.append(len(recent) >= 3 and sum(recent) >= 2)
    return result


def persistence(records: list[dict[str, Any]], duration_ms: int) -> list[bool]:
    result: list[bool] = []
    true_since: int | None = None
    for record in records:
        now = int(record["ts_monotonic_ms"])
        if record.get("human_detected_raw") is True:
            if true_since is None:
                true_since = now
            result.append(now - true_since >= duration_ms)
        else:
            true_since = None
            result.append(False)
    return result


def vital_corroborated(records: list[dict[str, Any]]) -> list[bool]:
    return [
        record.get("human_detected_raw") is True
        and (record.get("breath_rate_raw") or 0) > 0
        and (record.get("heart_rate_raw") or 0) > 0
        for record in records
    ]


def event_count(values: list[bool]) -> int:
    return sum(value and (index == 0 or not values[index - 1]) for index, value in enumerate(values))


def longest_run(values: list[bool]) -> int:
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def first_delay_ms(records: list[dict[str, Any]], raw: list[bool], filtered: list[bool]) -> int | None:
    try:
        raw_index = raw.index(True)
        filtered_index = filtered.index(True, raw_index)
    except ValueError:
        return None
    return int(records[filtered_index]["ts_monotonic_ms"]) - int(records[raw_index]["ts_monotonic_ms"])


def evaluate(name: str, transform: Callable[[list[dict[str, Any]]], list[bool]],
             empty: list[dict[str, Any]], occupied: list[dict[str, Any]]) -> dict[str, Any]:
    empty_raw = [item.get("human_detected_raw") is True for item in empty]
    occupied_raw = [item.get("human_detected_raw") is True for item in occupied]
    empty_output = transform(empty)
    occupied_output = transform(occupied)
    return {
        "filter": name,
        "empty_false_positive_events": event_count(empty_output),
        "empty_false_positive_records": sum(empty_output),
        "empty_longest_true_records": longest_run(empty_output),
        "occupied_detection_rate": sum(occupied_output) / len(occupied_output),
        "occupied_missed_records": len(occupied_output) - sum(occupied_output),
        "added_entry_delay_ms_in_occupied_log": first_delay_ms(
            occupied, occupied_raw, occupied_output
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--empty", type=Path, required=True)
    parser.add_argument("--occupied", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    empty = load(args.empty)
    occupied = load(args.occupied)
    candidates: list[tuple[str, Callable[[list[dict[str, Any]]], list[bool]]]] = [
        ("raw", lambda rows: [row.get("human_detected_raw") is True for row in rows]),
        ("two_of_three", two_of_three),
        ("true_persistence_1s", lambda rows: persistence(rows, 1000)),
        ("true_persistence_2s", lambda rows: persistence(rows, 2000)),
        ("true_persistence_3s", lambda rows: persistence(rows, 3000)),
        ("true_persistence_3_5s", lambda rows: persistence(rows, 3500)),
        ("presence_and_positive_breath_and_heart", vital_corroborated),
    ]
    result = {
        "empty_source": str(args.empty),
        "occupied_source": str(args.occupied),
        "note": "Occupied log began after presence was already established; transition latency requires a separate entry test.",
        "candidates": [
            evaluate(name, transform, empty, occupied) for name, transform in candidates
        ],
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
