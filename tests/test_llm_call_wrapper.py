"""Tests for forge_bridge.llm.call_wrapper — timeout, retry, error classes."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from forge_bridge.llm import call_wrapper as cw


@pytest.fixture(autouse=True)
def _reset_breaker():
    """PR10 — clear circuit-breaker state between tests so retryable failures
    in earlier tests don't open the breaker and short-circuit later ones."""
    cw._reset_breaker_for_tests()
    yield
    cw._reset_breaker_for_tests()


@pytest.fixture(autouse=True)
def _disable_fast_fail_default(monkeypatch):
    """PR10.1: legacy PR10/PR11 tests use zero-elapsed httpx mocks. The
    production fast-fail threshold (0.5s) would reclassify their
    TimeoutExceptions as 'connection' and break the original assertions.
    Disable fast-fail by default; PR10.1-specific tests re-enable it
    explicitly via the ``fast_fail_enabled`` fixture below."""
    monkeypatch.setattr(cw, "_FAST_FAIL_DURATION_SECONDS", 0.0)


@pytest.fixture
def fast_fail_enabled(monkeypatch):
    """PR10.1 opt-in: re-arm the production 0.5s fast-fail threshold."""
    monkeypatch.setattr(cw, "_FAST_FAIL_DURATION_SECONDS", 0.5)
    return 0.5


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
    # PR10: reporter line now includes the sleep duration ("sleeping Xs").
    assert any("Retrying (attempt 2/2" in m for m in msgs)
    # PR10: backoff is exponential + jitter — base 2.0 → first retry ~2.0–2.5s.
    assert len(sleeps) == 1
    assert 2.0 <= sleeps[0] <= 2.5


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


# ── PR10: budget enforcement ─────────────────────────────────────────────


class _ManualClock:
    """Inject monotonic time so we can test budget logic without real waits."""

    def __init__(self):
        self.t = 1000.0

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_budget_caps_total_wall_clock_under_repeated_timeouts():
    """Budget must terminate the loop even if `retries` would otherwise allow more."""
    clock = _ManualClock()
    sleeps: list[float] = []

    # Each httpx.TimeoutException advances the clock by 4s — simulating a
    # request that hit per-attempt timeout. Budget is 10s total.
    def attempt_timeout(_unused):
        clock.advance(4.0)
        return None  # unused — exception raised below

    outcomes = [
        httpx.TimeoutException("t1"),
        httpx.TimeoutException("t2"),
        httpx.TimeoutException("t3"),
        httpx.TimeoutException("t4"),
        httpx.TimeoutException("t5"),
    ]

    # Drive httpx.Client to consume from the queue, advancing the clock each
    # call to simulate per-attempt elapsed time.
    queue = list(outcomes)

    class _AdvancingClient:
        def __enter__(self): return self
        def __exit__(self, *_a): return False
        def post(self, *_a, **_kw):
            clock.advance(4.0)  # each attempt burns 4s
            return queue.pop(0) if queue and not isinstance(queue[0], BaseException) else (_ for _ in ()).throw(queue.pop(0))

    def _client_factory(**_kw):
        return _AdvancingClient()

    def _record_sleep(s):
        sleeps.append(s)
        clock.advance(s)

    with patch("httpx.Client", _client_factory):
        result = cw.call_with_retry(
            "http://x/y", {},
            timeout=10.0, retries=10, backoff_seconds=1.0,
            sleep=_record_sleep, now=clock.now, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    # Total elapsed must not exceed the 10s budget by more than the safety
    # floor (_MIN_ATTEMPT_BUDGET_SECONDS = 0.05).
    assert result.elapsed_seconds <= 10.0 + 1.0  # generous slack for clock granularity
    # We requested 10 retries but the budget should have stopped us well before.
    assert result.attempts < 10


def test_budget_blocks_backoff_that_would_overrun():
    """If remaining budget can't cover the next backoff, return immediately."""
    clock = _ManualClock()
    sleeps: list[float] = []

    queue = [httpx.TimeoutException("t1"), httpx.TimeoutException("t2"),
             httpx.TimeoutException("t3")]

    class _Client:
        def __enter__(self): return self
        def __exit__(self, *_a): return False
        def post(self, *_a, **_kw):
            clock.advance(2.0)  # each attempt burns 2s
            raise queue.pop(0)

    def _record_sleep(s):
        sleeps.append(s)
        clock.advance(s)

    with patch("httpx.Client", lambda **_kw: _Client()):
        result = cw.call_with_retry(
            "http://x/y", {},
            timeout=3.0, retries=5, backoff_seconds=4.0,  # backoff alone > budget
            sleep=_record_sleep, now=clock.now, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    # First attempt only — backoff (4s) > remaining budget (1s after first attempt).
    assert result.attempts == 1
    assert sleeps == []  # never slept


# ── PR10: exponential backoff ────────────────────────────────────────────


def test_exponential_backoff_doubles_each_retry():
    """Sleep deltas must follow base * 2^(n-2): 1s, 2s, 4s with base=1.0."""
    sleeps: list[float] = []
    queue = [
        httpx.TimeoutException("t1"),
        httpx.TimeoutException("t2"),
        httpx.TimeoutException("t3"),
        _Resp(200, {"response": "finally"}),
    ]
    with _patch_client(queue):
        result = cw.call_with_retry(
            "http://x/y", {},
            timeout=600.0, retries=3, backoff_seconds=1.0,
            sleep=sleeps.append, jitter=lambda: 0.0,
        )
    assert result.ok is True
    assert result.attempts == 4
    # Three retries → three backoffs.
    assert sleeps == [1.0, 2.0, 4.0]


def test_backoff_capped_under_high_retry_count():
    """Backoff caps at _BACKOFF_CAP_SECONDS (8s) — never grows unbounded."""
    sleeps: list[float] = []
    # 6 timeouts → 5 retries → backoffs would be 1, 2, 4, 8, 16 uncapped;
    # capped to 1, 2, 4, 8, 8.
    queue = [httpx.TimeoutException(f"t{n}") for n in range(6)] + [
        _Resp(200, {"response": "ok"}),
    ]
    with _patch_client(queue):
        result = cw.call_with_retry(
            "http://x/y", {},
            timeout=600.0, retries=6, backoff_seconds=1.0,
            sleep=sleeps.append, jitter=lambda: 0.0,
        )
    assert result.ok is True
    assert sleeps == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]


def test_backoff_includes_jitter_when_default_random_used():
    """Without injected jitter, backoff must be > base (random adds 0–0.5s)."""
    sleeps: list[float] = []
    queue = [httpx.TimeoutException("t1"), _Resp(200, {"response": "ok"})]
    with _patch_client(queue):
        cw.call_with_retry(
            "http://x/y", {},
            timeout=600.0, retries=1, backoff_seconds=1.0,
            sleep=sleeps.append,
            # `jitter` defaults to random.uniform(0, 0.5).
        )
    assert len(sleeps) == 1
    assert 1.0 <= sleeps[0] <= 1.5


# ── PR10: connection fast-fail ───────────────────────────────────────────


def test_connection_error_does_not_retry_even_with_high_retries():
    """Connection errors must short-circuit regardless of retries setting."""
    queue = [httpx.ConnectError("refused"), _Resp(200, {"response": "ok"})]
    with _patch_client(queue):
        result = cw.call_with_retry(
            "http://x/y", {},
            timeout=10.0, retries=5, backoff_seconds=0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert result.error_kind == "connection"
    assert result.attempts == 1


# ── PR10: circuit breaker ────────────────────────────────────────────────


def test_circuit_breaker_opens_after_threshold_failures():
    """After _BREAKER_THRESHOLD retryable failures, the next call short-circuits."""
    url = "http://breaker-test/y"
    # Fire 5 timeouts → each call exhausts retries=0 → 5 breaker ticks.
    for _ in range(cw._BREAKER_THRESHOLD):
        with _patch_client([httpx.TimeoutException("t")]):
            r = cw.call_with_retry(
                url, {}, timeout=5.0, retries=0, backoff_seconds=0,
                sleep=lambda _s: None, jitter=lambda: 0.0,
            )
            assert r.ok is False

    # Next call must short-circuit with circuit_open without firing httpx.
    sentinel = []
    def _factory(**_kw):
        sentinel.append("called")
        raise AssertionError("breaker should have short-circuited")

    with patch("httpx.Client", _factory):
        result = cw.call_with_retry(
            url, {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert result.error_kind == "circuit_open"
    assert sentinel == []  # httpx.Client was never constructed


def test_circuit_breaker_does_not_count_4xx_failures():
    """4xx responses are caller bugs — the breaker must ignore them."""
    url = "http://4xx-test/y"
    for _ in range(cw._BREAKER_THRESHOLD + 2):  # well past threshold
        with _patch_client([_Resp(400, {"error": {"message": "bad"}})]):
            r = cw.call_with_retry(
                url, {}, timeout=5.0, retries=0, backoff_seconds=0,
                sleep=lambda _s: None, jitter=lambda: 0.0,
            )
            assert r.error_kind == "invalid_response"

    # Breaker should still be closed — the next call goes through.
    with _patch_client([_Resp(200, {"response": "ok"})]):
        result = cw.call_with_retry(
            url, {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert result.ok is True


def test_circuit_breaker_window_slides():
    """Failures outside the rolling window expire — breaker re-closes."""
    url = "http://sliding-window/y"
    clock = _ManualClock()

    # Open the breaker.
    for _ in range(cw._BREAKER_THRESHOLD):
        cw._record_breaker_failure(url, now=clock.now)
    assert cw._circuit_open(url, now=clock.now) is True

    # Advance the clock past the window → breaker closes.
    clock.advance(cw._BREAKER_WINDOW_SECONDS + 1.0)
    assert cw._circuit_open(url, now=clock.now) is False


# ── PR11: structured execution trace ──────────────────────────────────────

def _kinds(trace):
    return [e["kind"] for e in trace["events"]]


def test_trace_envelope_present_on_success():
    """Trace must be a dict with events/total_elapsed/attempts on success."""
    with _patch_client([_Resp(200, {"response": "hi"})]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.ok
    assert isinstance(result.trace, dict)
    assert set(result.trace) == {"events", "total_elapsed", "attempts"}
    assert isinstance(result.trace["events"], list)
    assert result.trace["attempts"] == 1
    assert result.trace["total_elapsed"] >= 0.0


def test_trace_attempt_event_carries_duration_and_result_and_status():
    with _patch_client([_Resp(200, {"response": "hi"})]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    attempt = next(e for e in result.trace["events"] if e["kind"] == "attempt")
    assert attempt["attempt"] == 1
    assert attempt["result"] == "success"
    assert attempt["status_code"] == 200
    assert isinstance(attempt["duration"], float)
    assert "tool_calls" in attempt


def test_trace_orders_attempt_then_backoff_then_attempt_on_retry():
    """Backoff event must sit between the two attempt events, in order."""
    outcomes = [httpx.TimeoutException("t1"), _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=10.0, retries=1, backoff_seconds=1.0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert result.ok
    assert _kinds(result.trace) == ["attempt", "backoff", "attempt", "summary"]
    e = result.trace["events"]
    assert e[0]["result"] == "timeout" and e[0]["status_code"] is None
    assert e[1] == {"kind": "backoff", "duration": 1.0}
    assert e[2]["result"] == "success" and e[2]["status_code"] == 200


def test_trace_summary_event_always_present_on_success_and_failure():
    # success
    with _patch_client([_Resp(200, {"response": "ok"})]):
        ok = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert ok.trace["events"][-1] == {
        "kind": "summary",
        "attempts": 1,
        "total_elapsed": ok.trace["total_elapsed"],
        "final_status": "success",
        "error_kind": None,
    }

    # failure
    with _patch_client([httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]):
        fail = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    summary = fail.trace["events"][-1]
    assert summary["kind"] == "summary"
    assert summary["final_status"] == "failed"
    assert summary["error_kind"] == "timeout"
    assert summary["attempts"] == 2


def test_trace_503_attempt_records_status_code_in_event():
    body = {"error": {"message": "backend restarting"}}
    outcomes = [_Resp(503, body), _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    first = result.trace["events"][0]
    assert first["kind"] == "attempt"
    assert first["status_code"] == 503
    assert first["result"] == "timeout"


def test_trace_circuit_open_short_circuit_has_summary_only():
    """When the breaker fires, no attempt events — just a summary."""
    url = "http://breaker-trace/y"
    for _ in range(cw._BREAKER_THRESHOLD):
        cw._record_breaker_failure(url)

    result = cw.call_with_retry(
        url, {}, timeout=5.0, retries=0, backoff_seconds=0,
        sleep=lambda _s: None,
    )
    assert result.ok is False
    assert result.error_kind == "circuit_open"
    assert _kinds(result.trace) == ["summary"]
    assert result.trace["events"][0]["error_kind"] == "circuit_open"
    assert result.trace["attempts"] == 0


def test_trace_tool_calls_field_extracted_from_response_list_of_dicts():
    body = {"response": "hi", "tool_calls": [{"name": "flame_ping"},
                                              {"name": "forge_get_project"}]}
    with _patch_client([_Resp(200, body)]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    attempt = result.trace["events"][0]
    assert attempt["tool_calls"] == ["flame_ping", "forge_get_project"]


def test_trace_tool_calls_field_falls_back_to_count_when_no_names():
    body = {"response": "hi", "tool_calls": [{"id": "x"}, {"id": "y"}, {"id": "z"}]}
    with _patch_client([_Resp(200, body)]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=0, backoff_seconds=0,
            sleep=lambda _s: None,
        )
    assert result.trace["events"][0]["tool_calls"] == 3


def test_trace_is_serializable_and_to_dict_includes_it():
    import json as _json
    outcomes = [httpx.TimeoutException("t1"), _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    payload = result.to_dict()
    assert "trace" in payload
    _json.dumps(payload)  # must round-trip


def test_trace_does_not_modify_timeline_shape():
    """Existing timeline contract is preserved unchanged alongside trace."""
    outcomes = [httpx.TimeoutException("t1"), _Resp(200, {"response": "ok"})]
    with _patch_client(outcomes):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=5.0, retries=1, backoff_seconds=0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    # legacy timeline keys still exactly what PR10 produced.
    assert [t["outcome"] for t in result.timeline] == ["timeout", "ok"]
    assert all("attempt" in t and "elapsed" in t for t in result.timeline)


def test_trace_no_backoff_event_when_budget_blocks_retry():
    """If the budget skips the sleep, no backoff event should be recorded."""
    outcomes = [httpx.TimeoutException("t1")]
    clock = _ManualClock()

    queue = list(outcomes)

    class _C:
        def __enter__(self): return self
        def __exit__(self, *_a): return False
        def post(self, *_a, **_kw):
            clock.advance(2.5)
            raise queue.pop(0)

    with patch("httpx.Client", lambda **_kw: _C()):
        result = cw.call_with_retry(
            "http://x/y", {},
            timeout=3.0, retries=5, backoff_seconds=4.0,
            sleep=lambda _s: None, now=clock.now, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert "backoff" not in _kinds(result.trace)
    assert _kinds(result.trace) == ["attempt", "summary"]


# ── PR10.1: minimum-attempt-budget guard + fast-fail classification ───────


def _advance_clock_client(queue, clock, advance_per_post):
    """Build an httpx.Client patcher that advances ``clock`` per post call."""
    class _C:
        def __enter__(self): return self
        def __exit__(self, *_a): return False
        def post(self, *_a, **_kw):
            clock.advance(advance_per_post)
            out = queue.pop(0)
            if isinstance(out, BaseException):
                raise out
            return out
    return patch("httpx.Client", lambda **_kw: _C())


def test_pr10_1_min_request_timeout_constant_is_one_second():
    """PR10.1 contract — exposed as a public module constant."""
    assert cw.MIN_REQUEST_TIMEOUT == 1.0


def test_pr10_1_skips_request_when_remaining_below_min_request_timeout(
    fast_fail_enabled,
):
    """If remaining budget < MIN_REQUEST_TIMEOUT, do NOT issue another request."""
    clock = _ManualClock()
    calls = []

    queue = [httpx.TimeoutException("t1")]

    class _Spy:
        def __enter__(self): return self
        def __exit__(self, *_a): return False
        def post(self, *_a, **_kw):
            calls.append("post")
            clock.advance(2.5)  # eat most of the budget on the first call
            raise queue.pop(0)

    with patch("httpx.Client", lambda **_kw: _Spy()):
        result = cw.call_with_retry(
            "http://x/y", {},
            timeout=3.0, retries=5, backoff_seconds=0.0,
            sleep=lambda _s: None, now=clock.now, jitter=lambda: 0.0,
        )
    # Only ONE attempt fired — after it, remaining ≈ 0.5s < MIN_REQUEST_TIMEOUT.
    assert calls == ["post"]
    assert result.ok is False


def test_pr10_1_fast_timeout_classified_as_connection(fast_fail_enabled):
    """PR10.1: a TimeoutException firing in <0.5s is reclassified as connection."""
    with _patch_client([httpx.TimeoutException("instant")]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=10.0, retries=2, backoff_seconds=0.0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert result.error_kind == "connection"  # NOT timeout
    assert result.attempts == 1                # fast-fail, no retry


def test_pr10_1_slow_timeout_still_classified_as_timeout(fast_fail_enabled):
    """A TimeoutException at or above the threshold remains a real timeout."""
    clock = _ManualClock()
    queue = [httpx.TimeoutException("slow"), httpx.TimeoutException("slow")]
    with _advance_clock_client(queue, clock, advance_per_post=2.0):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=20.0, retries=1, backoff_seconds=0.0,
            sleep=lambda _s: None, now=clock.now, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert result.error_kind == "timeout"
    assert result.attempts == 2  # retried once, then exhausted


def test_pr10_1_fast_5xx_classified_as_invalid_response(fast_fail_enabled):
    """PR10.1: a 5xx that returns in <0.5s is server-side, not capacity."""
    with _patch_client([_Resp(504, {"error": {"message": "fast bug"}})]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=10.0, retries=2, backoff_seconds=0.0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert result.ok is False
    assert result.error_kind == "invalid_response"  # NOT timeout
    assert result.attempts == 1                     # fast-fail, no retry
    assert "fast bug" in result.error_message


def test_pr10_1_slow_5xx_still_retries(fast_fail_enabled):
    """A 5xx returning above the threshold remains a retryable timeout."""
    clock = _ManualClock()
    queue = [_Resp(503, {"error": {"message": "real capacity issue"}}),
             _Resp(200, {"response": "ok"})]
    with _advance_clock_client(queue, clock, advance_per_post=1.0):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=20.0, retries=1, backoff_seconds=0.0,
            sleep=lambda _s: None, now=clock.now, jitter=lambda: 0.0,
        )
    assert result.ok is True
    assert result.attempts == 2


def test_pr10_1_trace_records_error_not_timeout_for_fast_failures(
    fast_fail_enabled,
):
    """Trace's attempt event must reflect the corrected classification."""
    with _patch_client([httpx.TimeoutException("instant")]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=10.0, retries=2, backoff_seconds=0.0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    attempt = result.trace["events"][0]
    assert attempt["kind"] == "attempt"
    assert attempt["result"] == "error"  # NOT "timeout"
    assert attempt["duration"] < 0.5


def test_pr10_1_trace_for_fast_5xx_records_error_with_status(fast_fail_enabled):
    """Fast 5xx → trace attempt event has result='error' and the status code."""
    with _patch_client([_Resp(504, {"error": {"message": "fast"}})]):
        result = cw.call_with_retry(
            "http://x/y", {}, timeout=10.0, retries=2, backoff_seconds=0.0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    attempt = result.trace["events"][0]
    assert attempt["result"] == "error"
    assert attempt["status_code"] == 504


def test_pr10_1_fast_5xx_does_not_count_toward_breaker(fast_fail_enabled):
    """A reclassified invalid_response must not tick the circuit breaker."""
    url = "http://pr10-1-breaker/y"
    for _ in range(cw._BREAKER_THRESHOLD + 2):
        with _patch_client([_Resp(504, {"error": {"message": "fast"}})]):
            r = cw.call_with_retry(
                url, {}, timeout=10.0, retries=0, backoff_seconds=0.0,
                sleep=lambda _s: None, jitter=lambda: 0.0,
            )
            assert r.error_kind == "invalid_response"
    # Breaker stayed closed — next call still goes through.
    with _patch_client([_Resp(200, {"response": "ok"})]):
        ok = cw.call_with_retry(
            url, {}, timeout=10.0, retries=0, backoff_seconds=0.0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert ok.ok is True


def test_pr10_1_fast_timeout_counts_toward_breaker(fast_fail_enabled):
    """Reclassified connection failures still count toward the breaker."""
    url = "http://pr10-1-conn-breaker/y"
    for _ in range(cw._BREAKER_THRESHOLD):
        with _patch_client([httpx.TimeoutException("instant")]):
            r = cw.call_with_retry(
                url, {}, timeout=10.0, retries=0, backoff_seconds=0.0,
                sleep=lambda _s: None, jitter=lambda: 0.0,
            )
            assert r.error_kind == "connection"
    # Next call must short-circuit on circuit_open.
    sentinel = []
    with patch("httpx.Client", lambda **_kw: sentinel.append("called") or None):
        result = cw.call_with_retry(
            url, {}, timeout=10.0, retries=0, backoff_seconds=0.0,
            sleep=lambda _s: None, jitter=lambda: 0.0,
        )
    assert result.error_kind == "circuit_open"
    assert sentinel == []
