"""Tests for forge_bridge.llm.call_wrapper — timeout, retry, error classes."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from forge_bridge.llm import call_wrapper as cw


class _Resp:
    def __init__(self, status_code=200, body=None, raises_on_json=False, text=None):
        self.status_code = status_code
        self._body = body if body is not None else {"response": "hello"}
        self._raises_on_json = raises_on_json
        # `.text` is consulted by _extract_body when .json() fails. None
        # here triggers the AttributeError-defensive path on real httpx
        # responses; pass an explicit text= to simulate a text-only body.
        if text is not None:
            self.text = text

    def json(self):
        if self._raises_on_json:
            raise ValueError("not json")
        return self._body


class _Client:
    """Sequenced responder; shares its outcome queue across re-constructions."""

    def __init__(self, *, outcomes):
        # IMPORTANT: keep the SAME list reference so each fresh `httpx.Client(...)`
        # built by the wrapper pops from the same queue.
        self._outcomes = outcomes

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def post(self, url, json=None):
        if not self._outcomes:
            raise AssertionError("client called more times than outcomes provided")
        out = self._outcomes.pop(0)
        if isinstance(out, BaseException):
            raise out
        return out


def _patch_client(outcomes):
    """Patch httpx.Client to a sequenced fake whose queue persists across attempts."""
    queue = list(outcomes)
    factory = lambda **kw: _Client(outcomes=queue)  # noqa: E731
    return patch("httpx.Client", factory)


# ── happy path ────────────────────────────────────────────────────────────

def test_success_emits_send_and_response_messages():
    msgs: list[str] = []
    with _patch_client([_Resp(200, {"response": "hi"})]):
        result = cw.call_with_retry(
            "http://x/y", {"messages": [{"role": "user", "content": "hi"}]},
            timeout=5.0, retries=1, backoff_seconds=0,
            reporter=msgs.append, sleep=lambda _s: None,
        )
    assert result.ok is True
    assert result.data == {"response": "hi"}
    assert result.attempts == 1
    assert msgs[0] == "Sending request..."
    assert "Response received" in msgs[-1]


def test_timing_is_reported_in_seconds():
    msgs: list[str] = []
    with _patch_client([_Resp(200)]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            reporter=msgs.append, sleep=lambda _s: None,
        )
    assert result.ok
    assert result.elapsed_seconds >= 0.0
    assert any("Response received" in m and "s)" in m for m in msgs)


# ── timeout + retry ───────────────────────────────────────────────────────

def test_timeout_then_success_retries_once():
    msgs: list[str] = []
    sleeps: list[float] = []
    outcomes = [
        httpx.TimeoutException("first attempt timed out"),
        _Resp(200, {"response": "ok"}),
    ]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=2.0,
            reporter=msgs.append, sleep=sleeps.append,
        )
    assert result.ok is True
    assert result.attempts == 2
    assert any("timed out" in m for m in msgs)
    assert any("Retrying (attempt 2/2)" in m for m in msgs)
    assert sleeps == [2.0]  # backoff applied exactly once before retry


def test_timeout_exhausts_retries_returns_timeout_error():
    msgs: list[str] = []
    outcomes = [httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            reporter=msgs.append, sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    assert "timed out" in result.error_message
    assert "increase --timeout" in result.fix
    assert result.attempts == 2


def test_zero_retries_still_emits_timeout_error():
    with _patch_client([httpx.TimeoutException("t1")]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    assert result.attempts == 1


# ── connection / invalid response (no retry) ──────────────────────────────

def test_connection_error_not_retried():
    outcomes = [httpx.ConnectError("refused"), _Resp(200)]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "connection"
    assert result.attempts == 1
    assert "mcp http" in result.fix


def test_invalid_response_non_200_not_retried():
    """A non-retryable status (e.g. 400) fails immediately, no retry."""
    outcomes = [_Resp(400, {}), _Resp(200)]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "invalid_response"
    assert "HTTP 400" in result.error_message
    assert result.attempts == 1


def test_invalid_response_non_json_body():
    with _patch_client([_Resp(200, raises_on_json=True)]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "invalid_response"
    assert "non-JSON" in result.error_message


# ── timeline shape (verbose / JSON consumers) ─────────────────────────────

def test_timeline_records_each_attempt():
    outcomes = [httpx.TimeoutException("t1"), _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert [t["outcome"] for t in result.timeline] == ["timeout", "ok"]
    assert [t["attempt"] for t in result.timeline] == [1, 2]


def test_to_dict_is_serializable():
    import json
    with _patch_client([_Resp(200)]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    json.dumps(result.to_dict())  # must not raise


# ── PR4.1: HTTP 504 → timeout, body capture, server-message preservation ──

_504_BODY = {"error": {"code": "request_timeout",
                       "message": "Response timed out — try a simpler question."}}


def test_504_with_json_body_classified_as_timeout_and_retried():
    """First 504 retries; second-attempt success returns ok with 2 attempts."""
    outcomes = [_Resp(504, _504_BODY), _Resp(200, {"response": "hi"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is True
    assert result.attempts == 2
    assert result.timeline[0]["outcome"] == "timeout"
    assert result.timeline[0]["status"] == 504
    assert result.timeline[0]["body"] == _504_BODY


def test_504_exhausted_uses_server_message_when_present():
    """When 504 retries exhaust, error_message preserves the server-provided text."""
    outcomes = [_Resp(504, _504_BODY), _Resp(504, _504_BODY)]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    assert "try a simpler question" in result.error_message
    assert result.attempts == 2


def test_504_with_no_body_still_classified_as_timeout():
    """504 with non-JSON / empty body still classifies as timeout, generic message."""
    outcomes = [_Resp(504, raises_on_json=True, text=""), _Resp(504, raises_on_json=True, text="")]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    assert "504" in result.error_message  # generic fallback mentions HTTP 504
    assert all(t["outcome"] == "timeout" for t in result.timeline)


def test_non_200_with_json_body_preserves_server_message():
    """Non-retryable 4xx (e.g. 422) preserves server message + body in timeline."""
    body = {"error": {"code": "validation_error",
                      "message": "messages[0].content must be a string"}}
    with _patch_client([_Resp(422, body)]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "invalid_response"
    assert "messages[0].content" in result.error_message
    assert "HTTP 422" in result.error_message
    # body captured in timeline
    assert result.timeline[0]["body"] == body
    assert result.timeline[0]["status"] == 422


def test_non_retryable_status_does_not_retry():
    """Non-retryable codes (e.g. 400) MUST NOT consume retry attempts."""
    outcomes = [_Resp(400, {"error": {"message": "bad request"}}), _Resp(200, {})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "invalid_response"
    assert result.attempts == 1  # did not retry
    assert "bad request" in result.error_message


def test_504_with_text_body_uses_text_as_server_message():
    """If server returns text/plain, the wrapper still preserves it."""
    outcomes = [
        _Resp(504, raises_on_json=True, text="upstream took too long"),
        _Resp(504, raises_on_json=True, text="upstream took too long"),
    ]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    assert "upstream took too long" in result.error_message


# ── PR4.2: broaden retryable status set to {429, 500, 502, 503, 504} ──────

def test_retryable_status_set_is_canonical():
    assert cw.RETRYABLE_STATUS_CODES == frozenset({429, 500, 502, 503, 504})


def test_503_with_json_body_classified_as_timeout_and_retried():
    """503 with structured body → first attempt timeout-classified, retry succeeds."""
    body = {"error": {"code": "service_unavailable", "message": "backend is restarting"}}
    outcomes = [_Resp(503, body), _Resp(200, {"response": "now ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is True
    assert result.attempts == 2
    assert result.timeline[0]["outcome"] == "timeout"
    assert result.timeline[0]["status"] == 503
    assert result.timeline[0]["body"] == body


def test_500_without_json_classified_as_timeout_with_fallback_message():
    """500 with no body → still timeout, falls back to generic HTTP 500 message."""
    outcomes = [
        _Resp(500, raises_on_json=True, text=""),
        _Resp(500, raises_on_json=True, text=""),
    ]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    assert "HTTP 500" in result.error_message
    assert result.attempts == 2  # retried once
    assert all(t["outcome"] == "timeout" for t in result.timeline)


def test_429_is_retried():
    """Rate-limit 429 → timeout-classified, retried."""
    outcomes = [_Resp(429, {"error": {"message": "slow down"}}),
                _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is True
    assert result.attempts == 2


def test_502_is_retried():
    outcomes = [_Resp(502, {}), _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is True
    assert result.attempts == 2


def test_400_remains_invalid_response_no_retry():
    """Spec: 400 (and other 4xx not in retryable set) must NOT retry."""
    outcomes = [_Resp(400, {"error": {"message": "bad input"}}),
                _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok is False
    assert result.error_kind == "invalid_response"
    assert result.attempts == 1
    assert "bad input" in result.error_message
