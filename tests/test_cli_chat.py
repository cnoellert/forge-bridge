"""Tests for the `forge-bridge chat` CLI command."""
from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
from typer.testing import CliRunner

from forge_bridge.__main__ import app
from forge_bridge.llm import call_wrapper as cw

# CliRunner needs mix_stderr=False to inspect stderr separately. Recent typer
# versions removed the kw — fall back gracefully.
try:
    runner = CliRunner(mix_stderr=False)
except TypeError:
    runner = CliRunner()


class _Resp:
    def __init__(self, status_code=200, body=None, raises_on_json=False):
        self.status_code = status_code
        self._body = body if body is not None else {"response": "hello"}
        self._raises_on_json = raises_on_json

    def json(self):
        if self._raises_on_json:
            raise ValueError("not json")
        return self._body


class _Client:
    def __init__(self, *, outcomes):
        # Share the SAME list reference across re-constructions so multi-attempt
        # wrappers (one fresh httpx.Client per attempt) pop from one queue.
        self._outcomes = outcomes

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def post(self, url, json=None):
        out = self._outcomes.pop(0)
        if isinstance(out, BaseException):
            raise out
        return out


def _patch_httpx(outcomes):
    queue = list(outcomes)
    return patch("httpx.Client", lambda **kw: _Client(outcomes=queue))


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(cw.time, "sleep", lambda *_a, **_k: None)


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Clear circuit-breaker state between tests so failures from earlier
    tests don't open the breaker and short-circuit later ones."""
    cw._reset_breaker_for_tests()
    yield
    cw._reset_breaker_for_tests()


@pytest.fixture(autouse=True)
def _disable_fast_fail_default(monkeypatch):
    """PR10.1: zero-elapsed mocks in legacy CLI tests would otherwise be
    reclassified as 'connection' by the production 0.5s fast-fail threshold.
    Disable by default; the wrapper-level PR10.1 tests cover the real path."""
    monkeypatch.setattr(cw, "_FAST_FAIL_DURATION_SECONDS", 0.0)


@pytest.fixture
def fast_fail_enabled(monkeypatch):
    """PR12 opt-in: re-arm the production 0.5s fast-fail threshold."""
    monkeypatch.setattr(cw, "_FAST_FAIL_DURATION_SECONDS", 0.5)
    return 0.5


# ── happy path ────────────────────────────────────────────────────────────

def test_chat_success_prints_reply_to_stdout():
    with _patch_httpx([_Resp(200, {"response": "hi from llm"})]):
        result = runner.invoke(app, ["chat", "ping"])
    assert result.exit_code == 0
    assert "hi from llm" in result.stdout


def test_chat_success_progress_messages_go_to_stderr():
    with _patch_httpx([_Resp(200, {"response": "ok"})]):
        result = runner.invoke(app, ["chat", "ping"])
    err = getattr(result, "stderr", "") or ""
    assert "Sending request..." in err
    assert "Response received" in err


def test_chat_quiet_suppresses_progress_messages():
    with _patch_httpx([_Resp(200, {"response": "ok"})]):
        result = runner.invoke(app, ["chat", "--quiet", "ping"])
    err = getattr(result, "stderr", "") or ""
    assert "Sending request" not in err
    assert "ok" in result.stdout


def test_chat_verbose_shows_model_and_timing():
    body = {"response": "hi", "model": "qwen2.5-coder:32b", "provider": "ollama"}
    with _patch_httpx([_Resp(200, body)]):
        result = runner.invoke(app, ["chat", "--verbose", "ping"])
    assert result.exit_code == 0
    err = getattr(result, "stderr", "") or ""
    assert "qwen2.5-coder:32b" in err
    assert "ollama" in err
    assert "elapsed=" in err


# ── timeout + retry behavior ──────────────────────────────────────────────

def test_chat_timeout_then_success_shows_retry_message():
    outcomes = [httpx.TimeoutException("t1"), _Resp(200, {"response": "ok"})]
    with _patch_httpx(outcomes):
        result = runner.invoke(app, ["chat", "--retries", "1", "ping"])
    assert result.exit_code == 0
    err = getattr(result, "stderr", "") or ""
    assert "timed out" in err
    # PR10: reporter line now embeds the sleep duration ("sleeping Xs").
    assert "Retrying (attempt 2/2" in err
    assert "Response received" in err


def test_chat_timeout_exhausted_returns_actionable_fix():
    outcomes = [httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]
    with _patch_httpx(outcomes):
        result = runner.invoke(app, ["chat", "--retries", "1", "--backoff", "0", "ping"])
    assert result.exit_code == 3  # _EXIT_TIMEOUT
    err = getattr(result, "stderr", "") or ""
    assert "timeout:" in err
    assert "increase --timeout" in err


def test_chat_connection_error_returns_unreachable_fix(fast_fail_enabled):
    """PR12: fast (<0.5s) ConnectError → fast-fail with unreachable hint."""
    with _patch_httpx([httpx.ConnectError("no route")]):
        result = runner.invoke(app, ["chat", "ping"])
    assert result.exit_code == 2  # _EXIT_UNREACHABLE
    err = getattr(result, "stderr", "") or ""
    assert "connection:" in err
    assert "mcp http" in err  # fix hint mentions starting mcp http


def test_chat_invalid_response_returns_fix_hint():
    """A non-retryable status (400) → invalid_response with fix hint, exit 1."""
    with _patch_httpx([_Resp(400)]):
        result = runner.invoke(app, ["chat", "ping"])
    assert result.exit_code == 1
    err = getattr(result, "stderr", "") or ""
    assert "invalid_response:" in err
    assert "mcp_http.log" in err


# ── --json envelope ───────────────────────────────────────────────────────

def test_chat_json_success_envelope():
    with _patch_httpx([_Resp(200, {"response": "ok", "model": "m"})]):
        result = runner.invoke(app, ["chat", "--json", "ping"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is True
    assert payload["data"]["response"] == "ok"
    assert payload["error"] is None
    assert payload["attempts"] == 1
    assert "elapsed_seconds" in payload
    assert payload["timeline"][0]["outcome"] == "ok"


def test_chat_json_timeout_envelope_includes_fix():
    outcomes = [httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]
    with _patch_httpx(outcomes):
        result = runner.invoke(app, ["chat", "--json", "--retries", "1", "ping"])
    assert result.exit_code == 3
    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is False
    assert payload["error"]["kind"] == "timeout"
    assert "increase --timeout" in payload["error"]["fix"]
    assert payload["attempts"] == 2


def test_chat_json_does_not_emit_progress_messages():
    """JSON mode must keep stdout pure for parseability."""
    with _patch_httpx([_Resp(200, {"response": "ok"})]):
        result = runner.invoke(app, ["chat", "--json", "ping"])
    err = getattr(result, "stderr", "") or ""
    assert "Sending request" not in err
    json.loads(result.stdout.strip())  # must parse


# ── PR10: verbose output on both success and failure ────────────────────


def test_chat_verbose_success_block_includes_attempts_and_tool_calls():
    payload = {"response": "hi", "model": "qwen2.5-coder:32b",
               "provider": "ollama", "tool_calls": [{"name": "flame_ping"}]}
    with _patch_httpx([_Resp(200, payload)]):
        result = runner.invoke(app, ["chat", "--verbose", "ping"])
    assert result.exit_code == 0
    err = getattr(result, "stderr", "") or ""
    assert "[chat]" in err
    assert "elapsed=" in err
    assert "attempts=" in err
    assert "model=qwen2.5-coder:32b" in err
    assert "tool_calls=1" in err


def test_chat_verbose_failure_block_emitted_on_error_path():
    """PR10: verbose must surface the diagnostic block on failure too."""
    outcomes = [httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]
    with _patch_httpx(outcomes):
        result = runner.invoke(
            app, ["chat", "--verbose", "--retries", "1", "ping"],
        )
    assert result.exit_code == 3  # timeout exit code
    err = getattr(result, "stderr", "") or ""
    assert "[chat] FAILED" in err
    assert "kind=timeout" in err
    assert "elapsed=" in err
    assert "attempts=2" in err


def test_chat_json_failure_envelope_carries_attempts_and_elapsed():
    """PR10: JSON envelope must include attempts + elapsed_seconds on failure."""
    outcomes = [httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]
    with _patch_httpx(outcomes):
        result = runner.invoke(app, ["chat", "--json", "--retries", "1", "ping"])
    assert result.exit_code == 3
    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is False
    assert "attempts" in payload
    assert "elapsed_seconds" in payload
    assert isinstance(payload["elapsed_seconds"], (int, float))
    assert payload["attempts"] == 2


# ── PR11: structured trace in CLI ─────────────────────────────────────────


def test_chat_verbose_prints_trace_block_on_success():
    """--verbose must emit the [trace] block, derived from result.trace."""
    outcomes = [httpx.TimeoutException("t1"), _Resp(200, {"response": "ok"})]
    with _patch_httpx(outcomes):
        result = runner.invoke(
            app, ["chat", "--verbose", "--retries", "1", "ping"],
        )
    assert result.exit_code == 0
    err = getattr(result, "stderr", "") or ""
    assert "[trace]" in err
    assert "attempt 1 → timeout" in err
    assert "backoff →" in err
    assert "attempt 2 → success" in err
    assert "total →" in err


def test_chat_verbose_trace_does_not_dump_timeline_json():
    """The [trace] block is human-readable lines — no raw JSON in human mode."""
    with _patch_httpx([_Resp(200, {"response": "ok"})]):
        result = runner.invoke(app, ["chat", "--verbose", "ping"])
    err = getattr(result, "stderr", "") or ""
    assert "[trace]" in err
    # If we ever dump the trace dict, this would slip in.
    assert '"events"' not in err
    assert '"kind"' not in err


def test_chat_verbose_failure_emits_trace_before_diagnostic():
    """On failure, --verbose still shows the [trace] block."""
    outcomes = [httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]
    with _patch_httpx(outcomes):
        result = runner.invoke(
            app, ["chat", "--verbose", "--retries", "1", "ping"],
        )
    assert result.exit_code == 3
    err = getattr(result, "stderr", "") or ""
    assert "[trace]" in err
    assert "attempt 1 → timeout" in err
    assert "attempt 2 → timeout" in err
    assert "[chat] FAILED" in err


def test_chat_non_verbose_does_not_emit_trace_block():
    """Default mode stays quiet — trace is opt-in via --verbose."""
    with _patch_httpx([_Resp(200, {"response": "ok"})]):
        result = runner.invoke(app, ["chat", "ping"])
    err = getattr(result, "stderr", "") or ""
    assert "[trace]" not in err


def test_chat_json_envelope_includes_trace():
    """JSON envelope must carry the structured trace alongside legacy fields."""
    with _patch_httpx([_Resp(200, {"response": "ok", "model": "m"})]):
        result = runner.invoke(app, ["chat", "--json", "ping"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert "trace" in payload
    trace = payload["trace"]
    assert set(trace) == {"events", "total_elapsed", "attempts"}
    kinds = [e["kind"] for e in trace["events"]]
    assert kinds == ["attempt", "summary"]
    # Legacy keys remain — no renames, no nesting.
    assert "timeline" in payload
    assert payload["attempts"] == 1
    assert "elapsed_seconds" in payload
