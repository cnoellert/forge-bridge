"""Sync wrapper for HTTP-fronted LLM calls — timeout, retry, backoff, reporting.

Deliberately HTTP-layer only: this wraps a single POST to an LLM-backed
endpoint (e.g. ``:9996/api/v1/chat``) without touching ``LLMRouter`` or the
chat handler. Callers pass an optional ``reporter`` callback so the same
wrapper drives both human CLI output and silent JSON mode.

PR10 reliability contract:

* ``timeout`` is the **total** wall-clock budget — combined attempts +
  backoff sleeps must not exceed it. Per-attempt httpx timeout shrinks to
  whatever budget remains.
* Retry classification is fixed: ``timeout``, HTTP 429 / 500 / 502 / 503 /
  504 are retryable; HTTP 4xx (other than 429), invalid JSON, and connection
  errors fast-fail without retry.
* Backoff is exponential with jitter: ``backoff_seconds * 2^(n-2)`` capped
  at 8s plus ``random.uniform(0, 0.5)``. With the default 1.0 base this
  yields ~1s, ~2s, ~4s, …
* A per-URL circuit breaker opens after ``_BREAKER_THRESHOLD`` retryable
  failures inside ``_BREAKER_WINDOW_SECONDS`` and short-circuits further
  calls until the window slides. Connection-class failures count too;
  4xx responses do not (caller bug, not service degradation).

Errors are collapsed into four stable kinds:

* ``timeout`` — wall-clock or per-attempt budget exceeded; retried per
  classification.
* ``connection`` — network unreachable; counted toward the breaker but
  not retried (fast-fail).
* ``invalid_response`` — got a response but it's not usable; not retried,
  does not count toward the breaker.
* ``circuit_open`` — too many recent failures; the call is short-circuited.
"""
from __future__ import annotations

import random
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import httpx

# Public symbols — keep stable for tests + downstream callers.
DEFAULT_TIMEOUT_SECONDS = 130.0
DEFAULT_RETRIES = 1
# PR10: base for exponential backoff (was a constant delay pre-PR10).
DEFAULT_BACKOFF_SECONDS = 1.0

# HTTP statuses we treat as transient and worth retrying. Each maps to
# error_kind="timeout" so the existing retry / fix / exit-code paths apply
# without introducing a new error enum.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# PR10 tuning knobs — module-level so tests can monkeypatch.
_BACKOFF_CAP_SECONDS = 8.0
_BACKOFF_JITTER_MAX = 0.5
_BREAKER_THRESHOLD = 5
_BREAKER_WINDOW_SECONDS = 60.0
# PR10.1: smallest meaningful per-attempt window. If less budget remains we
# don't fire another request — a near-zero httpx timeout would just produce a
# misleading "timeout (0.1s)" event. 1.0s gives the request a real chance.
MIN_REQUEST_TIMEOUT = 1.0
# PR10.1: failures faster than this are not real timeouts — almost always a
# connection reset or fast server error. Reclassify so the user sees the
# truth and we don't spend retries on a bug masquerading as capacity.
_FAST_FAIL_DURATION_SECONDS = 0.5

_FIX_HINTS = {
    "timeout": (
        "increase --timeout, or check that the LLM backend is reachable "
        "(`forge-bridge doctor` shows backend status)."
    ),
    "connection": (
        "the chat endpoint is unreachable — start it with "
        "`python -m forge_bridge mcp http`."
    ),
    "invalid_response": (
        "the chat endpoint returned an unusable response — see "
        "`~/.forge-bridge/logs/mcp_http.log` and `forge-bridge console doctor`."
    ),
    "circuit_open": (
        "too many recent failures for this endpoint — wait for the breaker "
        "to reset (sliding 60s window) or restart the backend."
    ),
}


@dataclass
class CallResult:
    ok: bool
    data: dict[str, Any] | None
    error_kind: str | None
    error_message: str | None
    fix: str | None
    attempts: int
    elapsed_seconds: float
    timeline: list[dict[str, Any]] = field(default_factory=list)
    # PR11: structured execution trace, deterministic + machine-readable.
    # Shape:
    #   {"events": [
    #       {"kind": "attempt", "attempt": int, "duration": float,
    #        "result": "success|timeout|error",
    #        "status_code": int|None,
    #        "tool_calls": int|list[str]|None,    # PR13-B: 0 when skipped
    #        "tool_duration": float|None},        # PR13: aggregate tool-execution time
    #       {"kind": "backoff", "duration": float},
    #       {"kind": "summary", "attempts": int, "total_elapsed": float,
    #        "final_status": "success|failed", "error_kind": str|None},
    #    ],
    #    "total_elapsed": float, "attempts": int}
    # PR13-B: attempt events from short-circuit paths (invalid_response, fast
    # connection failures) report tool_calls=0 to make "no tools executed"
    # explicit. Slow-failure events that may retry stay tool_calls=None
    # (unknown — the request started, but we never saw a usable body).
    # Built during execution — not derived from timeline. `timeline` is the
    # legacy human-debug view; `trace` is the system-observability view.
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── circuit breaker (per-URL) ─────────────────────────────────────────────
# Module-level state, deliberately. The wrapper is process-local; if a
# downstream caller wants per-thread isolation they'll need a different
# abstraction. _reset_breaker_for_tests() clears state between tests.
_breaker_failures: dict[str, deque[float]] = {}


def _record_breaker_failure(url: str, *, now: Callable[[], float] = time.monotonic) -> None:
    dq = _breaker_failures.setdefault(url, deque())
    dq.append(now())


def _circuit_open(url: str, *, now: Callable[[], float] = time.monotonic) -> bool:
    dq = _breaker_failures.get(url)
    if not dq:
        return False
    cutoff = now() - _BREAKER_WINDOW_SECONDS
    while dq and dq[0] < cutoff:
        dq.popleft()
    if not dq:
        return False
    return len(dq) >= _BREAKER_THRESHOLD


def _reset_breaker_for_tests() -> None:
    """Test affordance — clear all per-URL failure history."""
    _breaker_failures.clear()


def _compute_backoff(
    attempt: int,
    base: float,
    *,
    jitter: Callable[[], float] | None = None,
) -> float:
    """Exponential backoff + jitter. ``attempt`` is 1-indexed; first retry
    (attempt=2) returns ~base, second retry (attempt=3) returns ~2*base, etc.
    Capped at ``_BACKOFF_CAP_SECONDS`` before jitter is added."""
    if attempt <= 1 or base <= 0:
        return 0.0
    raw = base * (2 ** (attempt - 2))
    capped = min(raw, _BACKOFF_CAP_SECONDS)
    if jitter is None:
        jitter_value = random.uniform(0.0, _BACKOFF_JITTER_MAX)
    else:
        jitter_value = jitter()
    return capped + jitter_value


def call_with_retry(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    reporter: Callable[[str], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    jitter: Callable[[], float] | None = None,
) -> CallResult:
    """POST ``payload`` to ``url`` honoring the PR10 reliability contract.

    ``timeout`` bounds the **total** wall-clock spend across attempts +
    backoff. Per-attempt httpx timeout shrinks to remaining budget; retries
    stop early when the budget is exhausted. ``sleep``, ``now``, and
    ``jitter`` are injectable for hermetic tests.
    """
    start = now()
    timeline: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    # PR12: retry telemetry surfaced in the trace summary. retry_skipped flips
    # to True iff classification declined a retry that ``retries`` would have
    # otherwise allowed.
    retry_skipped = False

    # Circuit breaker — short-circuit before doing any work.
    if _circuit_open(url, now=now):
        return _fail(
            "circuit_open",
            f"circuit open for {url} "
            f"({_BREAKER_THRESHOLD} failures in {_BREAKER_WINDOW_SECONDS:.0f}s)",
            attempts=0, start=start, timeline=timeline, events=events, now=now,
            retry_skipped=False,
        )

    _report(reporter, "Sending request...")

    last_kind: str | None = None
    last_message: str | None = None
    total_attempts = retries + 1
    attempts_made = 0   # number of httpx.post calls actually fired

    def remaining() -> float:
        return max(0.0, timeout - (now() - start))

    for attempt in range(1, total_attempts + 1):
        if attempt > 1:
            delay = _compute_backoff(attempt, backoff_seconds, jitter=jitter)
            # Bail if backoff alone would blow the budget — leave at least
            # MIN_REQUEST_TIMEOUT for the actual request after sleep.
            if remaining() <= delay + MIN_REQUEST_TIMEOUT:
                last_kind = "timeout"
                last_message = (
                    f"budget exhausted after {now() - start:.1f}s "
                    f"({timeout:.1f}s total, no time for retry)"
                )
                _report(reporter, last_message)
                break
            _report(
                reporter,
                f"Retrying (attempt {attempt}/{total_attempts}, "
                f"sleeping {delay:.1f}s)...",
            )
            if delay > 0:
                events.append({"kind": "backoff", "duration": delay})
                sleep(delay)

        per_attempt_budget = remaining()
        if per_attempt_budget < MIN_REQUEST_TIMEOUT:
            last_kind = "timeout"
            last_message = (
                f"budget exhausted after {now() - start:.1f}s "
                f"({timeout:.1f}s total)"
            )
            _report(reporter, last_message)
            break

        attempts_made = attempt
        attempt_start = now()
        try:
            with httpx.Client(timeout=per_attempt_budget) as client:
                response = client.post(url, json=payload)
        except httpx.TimeoutException:
            elapsed = now() - attempt_start
            # PR10.1: a "timeout" that fires faster than the fast-fail
            # threshold is not a real timeout — usually a connect failure or
            # remote reset. Reclassify so the user sees the truth.
            if elapsed < _FAST_FAIL_DURATION_SECONDS:
                timeline.append({
                    "attempt": attempt, "elapsed": elapsed, "outcome": "connection",
                })
                # PR13-B: fast TimeoutException → connection short-circuit.
                # Skip path → tool_calls=0 (no tools executed).
                events.append({
                    "kind": "attempt", "attempt": attempt, "duration": elapsed,
                    "result": "error", "status_code": None,
                    "tool_calls": 0, "tool_duration": None,
                })
                if retries > 0:
                    retry_skipped = True
                return _emit_failure(
                    url, "connection",
                    f"connection failed in {elapsed:.2f}s (no real timeout)",
                    attempts=attempt, start=start, timeline=timeline,
                    events=events, now=now, count_toward_breaker=True,
                    retry_skipped=retry_skipped,
                )
            timeline.append(
                {"attempt": attempt, "elapsed": elapsed, "outcome": "timeout"}
            )
            events.append({
                "kind": "attempt", "attempt": attempt, "duration": elapsed,
                "result": "timeout", "status_code": None,
                "tool_calls": None, "tool_duration": None,
            })
            last_kind = "timeout"
            last_message = f"LLM request timed out after {elapsed:.1f}s"
            _report(reporter, last_message)
            continue
        except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            elapsed = now() - attempt_start
            timeline.append(
                {"attempt": attempt, "elapsed": elapsed, "outcome": "connection"}
            )
            # PR12: a connection error faster than the fast-fail threshold is
            # almost always deterministic (refused / DNS / firewall) — retrying
            # won't help. Slow connection failures (>=0.5s) may be transient
            # (mid-stream resets, slow handshakes); fall through to the retry
            # path so the existing budget + backoff loop applies.
            # PR13-B: fast path is a skip → tool_calls=0; slow path may retry
            # → tool_calls=None (unknown).
            if elapsed < _FAST_FAIL_DURATION_SECONDS:
                events.append({
                    "kind": "attempt", "attempt": attempt, "duration": elapsed,
                    "result": "error", "status_code": None,
                    "tool_calls": 0, "tool_duration": None,
                })
                if retries > 0:
                    retry_skipped = True
                return _emit_failure(
                    url, "connection",
                    f"could not connect to {url} ({type(exc).__name__})",
                    attempts=attempt, start=start, timeline=timeline,
                    events=events, now=now, count_toward_breaker=True,
                    retry_skipped=retry_skipped,
                )
            events.append({
                "kind": "attempt", "attempt": attempt, "duration": elapsed,
                "result": "error", "status_code": None,
                "tool_calls": None, "tool_duration": None,
            })
            last_kind = "connection"
            last_message = (
                f"connection to {url} dropped after {elapsed:.1f}s "
                f"({type(exc).__name__})"
            )
            _report(reporter, last_message)
            continue

        elapsed = now() - attempt_start
        if response.status_code != 200:
            body = _extract_body(response)
            server_msg = _extract_server_message(body)
            if response.status_code in RETRYABLE_STATUS_CODES:
                # PR10.1: a 5xx (or 429) that returns faster than the fast-fail
                # threshold is a server-side error, not capacity exhaustion.
                # Don't retry — the next attempt will hit the same bug.
                if elapsed < _FAST_FAIL_DURATION_SECONDS:
                    timeline.append({
                        "attempt": attempt, "elapsed": elapsed,
                        "outcome": "http_error",
                        "status": response.status_code, "body": body,
                    })
                    # PR13-B: fast 5xx → invalid_response skip path.
                    events.append({
                        "kind": "attempt", "attempt": attempt, "duration": elapsed,
                        "result": "error",
                        "status_code": response.status_code,
                        "tool_calls": 0, "tool_duration": None,
                    })
                    error_message = (
                        f"HTTP {response.status_code} from {url} "
                        f"(fast-fail in {elapsed:.2f}s): {server_msg}"
                        if server_msg
                        else f"HTTP {response.status_code} from {url} "
                             f"(fast-fail in {elapsed:.2f}s)"
                    )
                    if retries > 0:
                        retry_skipped = True
                    return _emit_failure(
                        url, "invalid_response", error_message,
                        attempts=attempt, start=start, timeline=timeline,
                        events=events, now=now, count_toward_breaker=False,
                        retry_skipped=retry_skipped,
                    )
                timeline.append({
                    "attempt": attempt, "elapsed": elapsed,
                    "outcome": "timeout",
                    "status": response.status_code, "body": body,
                })
                events.append({
                    "kind": "attempt", "attempt": attempt, "duration": elapsed,
                    "result": "timeout",
                    "status_code": response.status_code,
                    "tool_calls": None, "tool_duration": None,
                })
                last_kind = "timeout"
                last_message = (
                    server_msg
                    or f"LLM request returned HTTP {response.status_code}"
                )
                _report(reporter, last_message)
                continue

            # 4xx (other than 429) — caller-side problem. Don't retry,
            # don't count toward the breaker.
            timeline.append({
                "attempt": attempt, "elapsed": elapsed,
                "outcome": "http_error", "status": response.status_code,
                "body": body,
            })
            # PR13-B: 4xx → invalid_response skip path.
            events.append({
                "kind": "attempt", "attempt": attempt, "duration": elapsed,
                "result": "error",
                "status_code": response.status_code,
                "tool_calls": 0, "tool_duration": None,
            })
            error_message = (
                f"HTTP {response.status_code} from {url}: {server_msg}"
                if server_msg
                else f"HTTP {response.status_code} from {url}"
            )
            if retries > 0:
                retry_skipped = True
            return _emit_failure(
                url, "invalid_response", error_message,
                attempts=attempt, start=start, timeline=timeline, events=events,
                now=now, count_toward_breaker=False,
                retry_skipped=retry_skipped,
            )

        try:
            data = response.json()
        except ValueError:
            body = _extract_body(response)
            timeline.append({
                "attempt": attempt, "elapsed": elapsed,
                "outcome": "invalid_json", "body": body,
            })
            # PR13-B: invalid JSON → invalid_response skip path.
            events.append({
                "kind": "attempt", "attempt": attempt, "duration": elapsed,
                "result": "error",
                "status_code": response.status_code,
                "tool_calls": 0, "tool_duration": None,
            })
            if retries > 0:
                retry_skipped = True
            return _emit_failure(
                url, "invalid_response", f"non-JSON body from {url}",
                attempts=attempt, start=start, timeline=timeline, events=events,
                now=now, count_toward_breaker=False,
                retry_skipped=retry_skipped,
            )

        timeline.append({"attempt": attempt, "elapsed": elapsed, "outcome": "ok"})
        events.append({
            "kind": "attempt", "attempt": attempt, "duration": elapsed,
            "result": "success",
            "status_code": response.status_code,
            "tool_calls": _extract_tool_calls(data),
            "tool_duration": _extract_tool_duration(data),
        })
        total_elapsed = now() - start
        _report(reporter, f"Response received ({total_elapsed:.1f}s)")
        trace = _build_trace(
            events, total_elapsed, attempt, "success", None,
            retry_count=max(0, attempt - 1), retry_skipped=False,
        )
        return CallResult(
            ok=True, data=data,
            error_kind=None, error_message=None, fix=None,
            attempts=attempt, elapsed_seconds=total_elapsed, timeline=timeline,
            trace=trace,
        )

    # Exhausted retries / budget on retryable errors (timeouts, 5xx, 429,
    # slow connection drops). Report actual attempts fired, not the configured
    # total — important when the budget cap stops us before we use all retries.
    return _emit_failure(
        url, last_kind or "timeout",
        last_message or f"LLM request timed out after {timeout:.1f}s",
        attempts=max(attempts_made, 1), start=start, timeline=timeline,
        events=events, now=now, count_toward_breaker=True,
        retry_skipped=retry_skipped,
    )


# ── helpers ───────────────────────────────────────────────────────────────
def _report(reporter: Callable[[str], None] | None, message: str) -> None:
    if reporter is not None:
        reporter(message)


def _fail(
    kind: str,
    message: str,
    *,
    attempts: int,
    start: float,
    timeline: list[dict[str, Any]],
    events: list[dict[str, Any]],
    retry_skipped: bool,
    now: Callable[[], float] = time.monotonic,
) -> CallResult:
    total_elapsed = now() - start
    trace = _build_trace(
        events, total_elapsed, attempts, "failed", kind,
        retry_count=max(0, attempts - 1), retry_skipped=retry_skipped,
    )
    return CallResult(
        ok=False, data=None,
        error_kind=kind, error_message=message,
        fix=_FIX_HINTS.get(kind),
        attempts=attempts,
        elapsed_seconds=total_elapsed,
        timeline=timeline,
        trace=trace,
    )


def _emit_failure(
    url: str,
    kind: str,
    message: str,
    *,
    attempts: int,
    start: float,
    timeline: list[dict[str, Any]],
    events: list[dict[str, Any]],
    retry_skipped: bool,
    now: Callable[[], float] = time.monotonic,
    count_toward_breaker: bool,
) -> CallResult:
    """Build a failure CallResult and (optionally) record a breaker tick."""
    if count_toward_breaker:
        _record_breaker_failure(url, now=now)
    return _fail(kind, message, attempts=attempts, start=start,
                 timeline=timeline, events=events,
                 retry_skipped=retry_skipped, now=now)


def _build_trace(
    events: list[dict[str, Any]],
    total_elapsed: float,
    attempts: int,
    final_status: str,
    error_kind: str | None,
    *,
    retry_count: int,
    retry_skipped: bool,
) -> dict[str, Any]:
    """Append the summary event and wrap the events list in the trace envelope.

    PR12: summary carries ``retry_count`` (retries actually performed) and
    ``retry_skipped`` (True iff classification declined a retry the
    ``retries`` setting would have allowed)."""
    finalized = [
        *events,
        {
            "kind": "summary",
            "attempts": attempts,
            "total_elapsed": total_elapsed,
            "final_status": final_status,
            "error_kind": error_kind,
            "retry_count": retry_count,
            "retry_skipped": retry_skipped,
        },
    ]
    return {
        "events": finalized,
        "total_elapsed": total_elapsed,
        "attempts": attempts,
    }


def _extract_tool_calls(data: Any) -> int | list[str] | None:
    """Pull tool-call info off a successful chat response, if reported."""
    if not isinstance(data, dict):
        return None
    tc = data.get("tool_calls")
    if isinstance(tc, int):
        return tc
    if isinstance(tc, list):
        # Surface a list of names when entries carry one; otherwise the count.
        names = [
            entry.get("name") for entry in tc
            if isinstance(entry, dict) and isinstance(entry.get("name"), str)
        ]
        if names and len(names) == len(tc):
            return names
        return len(tc)
    return None


def _extract_tool_duration(data: Any) -> float | None:
    """PR13: pull aggregate server-side tool-execution time off a chat response.

    Returns a non-negative float when the chat endpoint reports
    ``tool_duration`` (seconds, aggregate across all tool calls in the
    response), otherwise ``None``. Negative or non-numeric values are
    rejected so the trace stays clean.
    """
    if not isinstance(data, dict):
        return None
    td = data.get("tool_duration")
    if isinstance(td, bool):  # bool is a subclass of int — never meaningful here
        return None
    if isinstance(td, (int, float)) and td >= 0:
        return float(td)
    return None


_MAX_TEXT_BODY_BYTES = 1024


def _extract_body(response: httpx.Response) -> Any:
    """Best-effort body extraction: JSON if parseable, else clipped text."""
    try:
        return response.json()
    except ValueError:
        pass
    try:
        text = response.text
    except (UnicodeDecodeError, OSError, AttributeError):
        return None
    if not text:
        return None
    if len(text) > _MAX_TEXT_BODY_BYTES:
        return text[:_MAX_TEXT_BODY_BYTES] + "..."
    return text


def _extract_server_message(body: Any) -> str | None:
    """Pull a human-readable error message out of a structured error body."""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            if isinstance(msg, str) and msg:
                return msg
        for key in ("message", "detail", "error"):
            v = body.get(key)
            if isinstance(v, str) and v:
                return v
    if isinstance(body, str) and body:
        clipped = body.strip()
        if clipped:
            return clipped[:200]
    return None
