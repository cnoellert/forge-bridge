"""Tests for forge_bridge.learning.execution_log module."""
from __future__ import annotations

import json
import os

import pytest


def test_normalize_same_hash_for_different_string_literals(tmp_path):
    """normalize_and_hash strips string literals so shot-name variants produce the same hash."""
    from forge_bridge.learning.execution_log import normalize_and_hash

    _, h1 = normalize_and_hash("seg.name = 'ACM_0010'")
    _, h2 = normalize_and_hash("seg.name = 'ACM_0020'")
    assert h1 == h2


def test_normalize_same_hash_for_different_numeric_literals(tmp_path):
    """normalize_and_hash strips numeric literals so x=42 and x=99 produce the same hash."""
    from forge_bridge.learning.execution_log import normalize_and_hash

    _, h1 = normalize_and_hash("x = 42")
    _, h2 = normalize_and_hash("x = 99")
    assert h1 == h2


def test_normalize_fallback_on_syntax_error():
    """normalize_and_hash returns hash of raw string when code has syntax errors."""
    from forge_bridge.learning.execution_log import normalize_and_hash

    normalized, h = normalize_and_hash("invalid syntax !!!")
    assert isinstance(h, str)
    assert len(h) == 64  # SHA-256 hex digest length


def test_record_appends_jsonl(tmp_path):
    """ExecutionLog.record(code) appends a JSON line to the log file."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    log.record("print('hello')")

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert isinstance(rec, dict)


def test_record_jsonl_keys(tmp_path):
    """Each JSONL line contains keys: code_hash, raw_code, intent, timestamp, promoted."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    log.record("x = 1")

    rec = json.loads(log_path.read_text().strip())
    for key in ("code_hash", "raw_code", "intent", "timestamp", "promoted"):
        assert key in rec, f"Missing key: {key}"


def test_record_returns_false_below_threshold(tmp_path):
    """ExecutionLog.record() returns False when count < threshold."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path, threshold=3)
    assert log.record("x = 1") is False
    assert log.record("x = 1") is False


def test_record_returns_true_at_threshold(tmp_path):
    """ExecutionLog.record() returns True exactly once when count == threshold."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path, threshold=3)
    log.record("x = 1")
    log.record("x = 1")
    result = log.record("x = 1")  # 3rd call = threshold
    assert result is True


def test_record_returns_false_after_mark_promoted(tmp_path):
    """ExecutionLog.record() returns False for same hash after mark_promoted()."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path, threshold=3)
    log.record("x = 1")
    log.record("x = 1")
    assert log.record("x = 1") is True  # threshold hit
    log.mark_promoted(log._counters.copy().popitem()[0])  # promote the hash
    assert log.record("x = 1") is False


def test_replay_rebuilds_counters(tmp_path):
    """New ExecutionLog instance replaying existing JSONL rebuilds counters correctly."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log1 = ExecutionLog(log_path=log_path, threshold=5)
    log1.record("x = 1")
    log1.record("x = 1")
    log1.record("y = 2")

    # New instance replays
    log2 = ExecutionLog(log_path=log_path, threshold=5)
    # x=1 was recorded twice (but normalized: x=0 is the pattern)
    from forge_bridge.learning.execution_log import normalize_and_hash

    _, h = normalize_and_hash("x = 1")
    assert log2.get_count(h) == 2


def test_replay_promoted_does_not_reemit(tmp_path):
    """Replayed log with promoted=True record does not re-emit promote signal."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log1 = ExecutionLog(log_path=log_path, threshold=2)
    log1.record("x = 1")
    result = log1.record("x = 1")  # threshold hit
    assert result is True

    from forge_bridge.learning.execution_log import normalize_and_hash

    _, h = normalize_and_hash("x = 1")
    log1.mark_promoted(h)

    # New instance replays — should see as promoted, not re-emit
    log2 = ExecutionLog(log_path=log_path, threshold=2)
    assert log2.record("x = 1") is False  # already promoted


def test_record_with_intent(tmp_path):
    """ExecutionLog.record(code, intent='rename shots') stores intent in JSONL."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    log.record("x = 1", intent="rename shots")

    rec = json.loads(log_path.read_text().strip())
    assert rec["intent"] == "rename shots"


def test_env_var_overrides_threshold(tmp_path, monkeypatch):
    """FORGE_PROMOTION_THRESHOLD env var overrides default threshold of 3."""
    from forge_bridge.learning.execution_log import ExecutionLog

    monkeypatch.setenv("FORGE_PROMOTION_THRESHOLD", "2")
    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    log.record("x = 1")
    result = log.record("x = 1")  # 2nd call = threshold of 2
    assert result is True


def test_log_directory_created_automatically(tmp_path):
    """Log directory is created automatically if it does not exist."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "subdir" / "deep" / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    log.record("x = 1")
    assert log_path.exists()
