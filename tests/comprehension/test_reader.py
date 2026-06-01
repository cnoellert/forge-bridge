from __future__ import annotations

import json

import pytest

from forge_bridge.comprehension import (
    SCHEMA_VERSION,
    SchemaVersionMismatch,
    annotate_comprehension_file,
    read_comprehension_file,
)


def _record(question: str, verdict=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": "2026-05-31T00:00:00+00:00",
        "outcome": "answered",
        "question": question,
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "answer": "No shots were returned.",
        "wall_clock_ms": 12,
        "model": "qwen",
        "verdict": verdict,
    }


def _write_capture(path, records, *, schema_version=SCHEMA_VERSION):
    header = {
        "_header": True,
        "schema_version": schema_version,
        "captured_at": "2026-05-31T00:00:00+00:00",
    }
    payload = [header, *records]
    path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in payload),
        encoding="utf-8",
    )


def test_reader_yields_valid_records(tmp_path):
    path = tmp_path / "comprehension.jsonl"
    _write_capture(path, [_record("first"), _record("second")])

    records = list(read_comprehension_file(path))

    assert [r["question"] for r in records] == ["first", "second"]


def test_reader_rejects_schema_version_mismatch(tmp_path):
    path = tmp_path / "comprehension.jsonl"
    _write_capture(path, [], schema_version="99")

    with pytest.raises(SchemaVersionMismatch, match="upgrade or filter"):
        list(read_comprehension_file(path))


def test_annotate_tags_only_unset_verdicts(tmp_path):
    path = tmp_path / "comprehension.jsonl"
    _write_capture(path, [_record("first"), _record("second", "loved")])
    answers = iter(["overstated"])

    tagged = annotate_comprehension_file(
        path,
        input_func=lambda _prompt: next(answers),
    )

    assert tagged == 1
    records = list(read_comprehension_file(path))
    assert records[0]["verdict"] == "overstated"
    assert records[1]["verdict"] == "loved"
    assert records[0]["question"] == "first"
    assert records[0]["chain"] == [{"step": "forge_list_shots", "result": {
        "shots": [],
    }}]


def test_annotate_second_pass_skips_already_tagged_records(tmp_path):
    path = tmp_path / "comprehension.jsonl"
    _write_capture(path, [_record("first", "loved")])

    tagged = annotate_comprehension_file(
        path,
        input_func=lambda _prompt: (_ for _ in ()).throw(
            AssertionError("should not prompt")
        ),
    )

    assert tagged == 0
    assert list(read_comprehension_file(path))[0]["verdict"] == "loved"
