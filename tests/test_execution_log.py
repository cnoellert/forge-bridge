"""Tests for forge_bridge.learning.execution_log module."""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock

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


# --- bridge.py callback hook tests ---


def test_set_execution_callback_sets_callback():
    """set_execution_callback(fn) sets the module-level callback."""
    import forge_bridge.bridge as bridge_mod
    from forge_bridge.bridge import set_execution_callback

    original = bridge_mod._on_execution_callback
    try:
        def my_fn(code, resp):
            pass

        set_execution_callback(my_fn)
        assert bridge_mod._on_execution_callback is my_fn
    finally:
        bridge_mod._on_execution_callback = original


def test_set_execution_callback_clears_with_none():
    """set_execution_callback(None) clears the callback."""
    import forge_bridge.bridge as bridge_mod
    from forge_bridge.bridge import set_execution_callback

    original = bridge_mod._on_execution_callback
    try:
        set_execution_callback(lambda c, r: None)
        assert bridge_mod._on_execution_callback is not None
        set_execution_callback(None)
        assert bridge_mod._on_execution_callback is None
    finally:
        bridge_mod._on_execution_callback = original


def test_set_execution_callback_default_clears():
    """set_execution_callback() with no args clears callback (default None)."""
    import forge_bridge.bridge as bridge_mod
    from forge_bridge.bridge import set_execution_callback

    original = bridge_mod._on_execution_callback
    try:
        set_execution_callback(lambda c, r: None)
        set_execution_callback()  # no args
        assert bridge_mod._on_execution_callback is None
    finally:
        bridge_mod._on_execution_callback = original


# ---------------------------------------------------------------------------
# Storage callback tests (LRN-02)
# ---------------------------------------------------------------------------


def test_storage_callback_fires_on_record(tmp_path):
    """Sync storage callback is called once per record() with an ExecutionRecord."""
    from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    cb = MagicMock()
    log.set_storage_callback(cb)

    log.record("print('hello')", intent="greeting")

    assert cb.call_count == 1
    arg = cb.call_args.args[0]
    assert isinstance(arg, ExecutionRecord)
    assert arg.raw_code == "print('hello')"
    assert arg.intent == "greeting"
    assert arg.promoted is False


async def test_async_storage_callback_fires_on_record(tmp_path):
    """Async storage callback is awaited once per record() with an ExecutionRecord."""
    import asyncio as _asyncio

    from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    cb = AsyncMock()
    log.set_storage_callback(cb)

    log.record("x = 1")
    # Give the fire-and-forget task a chance to run.
    await _asyncio.sleep(0)

    assert cb.await_count == 1
    arg = cb.await_args.args[0]
    assert isinstance(arg, ExecutionRecord)
    assert arg.raw_code == "x = 1"


def test_storage_callback_error_does_not_break_jsonl_write(tmp_path, caplog):
    """A raising sync callback is isolated — JSONL still written, warning logged."""
    import logging

    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)

    def boom(_rec):
        raise RuntimeError("storage offline")

    log.set_storage_callback(boom)

    with caplog.at_level(logging.WARNING, logger="forge_bridge.learning.execution_log"):
        log.record("x = 1")

    # JSONL line still present.
    assert log_path.exists()
    assert log_path.read_text().strip() != ""
    # Warning logged containing the phrase "storage_callback".
    assert any("storage_callback" in rec.message for rec in caplog.records)


def test_set_storage_callback_none_clears(tmp_path):
    """set_storage_callback(None) clears a previously-registered callback."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    cb = MagicMock()
    log.set_storage_callback(cb)
    log.set_storage_callback(None)

    log.record("y = 2")

    assert cb.call_count == 0


def test_callback_receives_full_execution_record(tmp_path):
    """Callback receives all 5 ExecutionRecord fields."""
    from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    captured: list = []
    log.set_storage_callback(lambda rec: captured.append(rec))

    log.record("z = 3", intent="test")

    assert len(captured) == 1
    rec = captured[0]
    assert isinstance(rec, ExecutionRecord)
    # All 5 locked fields must be populated.
    assert isinstance(rec.code_hash, str) and len(rec.code_hash) == 64
    assert rec.raw_code == "z = 3"
    assert rec.intent == "test"
    assert isinstance(rec.timestamp, str) and rec.timestamp.endswith("+00:00")
    assert rec.promoted is False
