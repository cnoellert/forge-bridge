from __future__ import annotations

import json
import logging

from forge_bridge.comprehension import (
    SCHEMA_VERSION,
    comprehension_capture_enabled,
    emit_comprehension_capture,
    validate_comprehension_record,
)
from forge_bridge.comprehension import _capture as capture_module
from forge_bridge.comprehension._schema import SchemaValidationError


def _emit_args(**overrides):
    args = {
        "question": "what shots are in sequence molecule?",
        "chain": [{"step": "forge_list_shots sequence=molecule", "result": {
            "shots": ["010", "020"],
        }}],
        "answer": "Sequence molecule has shots 010 and 020.",
        "wall_clock_ms": 2500,
        "model": "qwen2.5-coder:14b",
    }
    args.update(overrides)
    return args


def _capture_path(tmp_path):
    matches = list(tmp_path.glob("comprehension-*.jsonl"))
    assert len(matches) == 1
    return matches[0]


def test_capture_gate_defaults_off(monkeypatch, tmp_path):
    monkeypatch.delenv("FORGE_BRIDGE_COMPREHENSION_CAPTURE", raising=False)
    monkeypatch.setenv("FORGE_BRIDGE_COMPREHENSION_DIR", str(tmp_path))

    assert comprehension_capture_enabled() is False
    emit_comprehension_capture(**_emit_args())

    assert list(tmp_path.iterdir()) == []


def test_capture_invalid_gate_warns_once(monkeypatch, caplog):
    capture_module._warned_invalid_values.clear()
    monkeypatch.setenv("FORGE_BRIDGE_COMPREHENSION_CAPTURE", "maybe")

    with caplog.at_level(logging.WARNING, logger="forge_bridge.comprehension._capture"):
        assert comprehension_capture_enabled() is False
        assert comprehension_capture_enabled() is False

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "maybe" in warnings[0].message


def test_capture_gate_on_appends_header_and_record(monkeypatch, tmp_path):
    monkeypatch.setenv("FORGE_BRIDGE_COMPREHENSION_CAPTURE", "1")
    monkeypatch.setenv("FORGE_BRIDGE_COMPREHENSION_DIR", str(tmp_path))

    emit_comprehension_capture(**_emit_args())
    emit_comprehension_capture(**_emit_args(question="second question"))

    lines = _capture_path(tmp_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    header = json.loads(lines[0])
    first = json.loads(lines[1])
    second = json.loads(lines[2])

    assert header == {
        "_header": True,
        "schema_version": SCHEMA_VERSION,
        "captured_at": header["captured_at"],
    }
    assert first["question"] == "what shots are in sequence molecule?"
    assert first["verdict"] is None
    assert second["question"] == "second question"
    validate_comprehension_record(first)
    validate_comprehension_record(second)


def test_capture_swallow_write_failures(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("FORGE_BRIDGE_COMPREHENSION_CAPTURE", "1")
    monkeypatch.setenv("FORGE_BRIDGE_COMPREHENSION_DIR", str(tmp_path))
    monkeypatch.setattr(
        capture_module,
        "_build_record",
        lambda **_: {"schema_version": SCHEMA_VERSION},
    )

    with caplog.at_level(logging.WARNING, logger="forge_bridge.comprehension._capture"):
        assert emit_comprehension_capture(**_emit_args()) is None

    assert "comprehension capture write failed" in caplog.text


def test_validate_accepts_null_and_tagged_verdicts():
    record = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": "2026-05-31T00:00:00+00:00",
        "question": "what shots?",
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "answer": "No shots were returned.",
        "wall_clock_ms": 10,
        "model": "qwen",
        "verdict": None,
    }
    validate_comprehension_record(record)
    record["verdict"] = "loved"
    validate_comprehension_record(record)


def test_validate_rejects_missing_required_field_by_name():
    record = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": "2026-05-31T00:00:00+00:00",
        "chain": [],
        "answer": "",
        "wall_clock_ms": 10,
        "model": "qwen",
        "verdict": None,
    }
    try:
        validate_comprehension_record(record)
    except SchemaValidationError as exc:
        assert "question" in str(exc)
    else:
        raise AssertionError("expected SchemaValidationError")
