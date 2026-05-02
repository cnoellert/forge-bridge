"""Sync wrapper for HTTP-fronted LLM calls — timeout, retry, backoff, reporting.

Deliberately HTTP-layer only: this wraps a single POST to an LLM-backed
endpoint (e.g. ``:9996/api/v1/chat``) without touching ``LLMRouter`` or the
chat handler. Callers pass an optional ``reporter`` callback so the same
wrapper drives both human CLI output and silent JSON mode.

Errors are collapsed into three stable kinds:

* ``timeout`` — wall-clock exceeded; retried automatically per ``retries``.
* ``connection`` — network unreachable; not retried.
* ``invalid_response`` — got a response but it's not usable (non-2xx, not
  JSON, etc.); not retried.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import httpx

# Public symbol — keep stable for tests + downstream callers.
DEFAULT_TIMEOUT_SECONDS = 130.0
DEFAULT_RETRIES = 1
DEFAULT_BACKOFF_SECONDS = 2.0

# HTTP statuses we treat as transient and worth retrying. Each maps to
# error_kind="timeout" so the existing retry / fix / exit-code paths apply
# without introducing a new error enum.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def call_with_retry(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    reporter: Callable[[str], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> CallResult:
    """POST ``payload`` to ``url``; classify errors; retry on timeout only.

    The wrapper takes ``sleep`` as a parameter so tests can pass a no-op.
    Connection errors and invalid responses are NOT retried — only timeouts.
    """
    _report(reporter, "Sending request...")
    start = time.monotonic()
    timeline: list[dict[str, Any]] = []
    last_kind: str | None = None
    last_message: str | None = None

    total_attempts = retries + 1
    for attempt in range(1, total_attempts + 1):
        if attempt > 1:
            _report(
                reporter,
                f"Retrying (attempt {attempt}/{total_attempts})...",
            )
            if backoff_seconds > 0:
                sleep(backoff_seconds)

        attempt_start = time.monotonic()
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)
        except httpx.TimeoutException:
            elapsed = time.monotonic() - attempt_start
            timeline.append(
                {"attempt": attempt, "elapsed": elapsed, "outcome": "timeout"}
            )
            last_kind = "timeout"
            last_message = f"LLM request timed out after {elapsed:.1f}s"
            _report(reporter, last_message)
            continue
        except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            elapsed = time.monotonic() - attempt_start
            timeline.append(
                {"attempt": attempt, "elapsed": elapsed, "outcome": "connection"}
            )
            return _fail(
                "connection",
                f"could not connect to {url} ({type(exc).__name__})",
                attempt, start, timeline,
            )

        elapsed = time.monotonic() - attempt_start
        if response.status_code != 200:
            body = _extract_body(response)
            server_msg = _extract_server_message(body)
            # Transient HTTP statuses — server-signaled "try again later".
            # Mapped to error_kind="timeout" so existing retry / fix-hint /
            # exit-code paths apply without a new error enum (PR4.2).
            if response.status_code in RETRYABLE_STATUS_CODES:
                timeline.append({
                    "attempt": attempt, "elapsed": elapsed,
                    "outcome": "timeout",
                    "status": response.status_code, "body": body,
                })
                last_kind = "timeout"
                last_message = (
                    server_msg
                    or f"LLM request timed out after {elapsed:.1f}s "
                       f"(HTTP {response.status_code})"
                )
                _report(reporter, last_message)
                continue

            timeline.append({
                "attempt": attempt, "elapsed": elapsed,
                "outcome": "http_error", "status": response.status_code,
                "body": body,
            })
            error_message = (
                f"HTTP {response.status_code} from {url}: {server_msg}"
                if server_msg
                else f"HTTP {response.status_code} from {url}"
            )
            return _fail(
                "invalid_response", error_message,
                attempt, start, timeline,
            )

        try:
            data = response.json()
        except ValueError:
            body = _extract_body(response)
            timeline.append({
                "attempt": attempt, "elapsed": elapsed,
                "outcome": "invalid_json", "body": body,
            })
            return _fail(
                "invalid_response",
                f"non-JSON body from {url}",
                attempt, start, timeline,
            )

        timeline.append({"attempt": attempt, "elapsed": elapsed, "outcome": "ok"})
        total_elapsed = time.monotonic() - start
        _report(reporter, f"Response received ({total_elapsed:.1f}s)")
        return CallResult(
            ok=True, data=data,
            error_kind=None, error_message=None, fix=None,
            attempts=attempt, elapsed_seconds=total_elapsed, timeline=timeline,
        )

    # Exhausted retries on timeout.
    return _fail(
        last_kind or "timeout",
        last_message or f"LLM request timed out after {timeout:.1f}s",
        total_attempts, start, timeline,
    )


# ── helpers ───────────────────────────────────────────────────────────────
def _report(reporter: Callable[[str], None] | None, message: str) -> None:
    if reporter is not None:
        reporter(message)


def _fail(
    kind: str,
    message: str,
    attempts: int,
    start: float,
    timeline: list[dict[str, Any]],
) -> CallResult:
    return CallResult(
        ok=False, data=None,
        error_kind=kind, error_message=message,
        fix=_FIX_HINTS.get(kind),
        attempts=attempts,
        elapsed_seconds=time.monotonic() - start,
        timeline=timeline,
    )


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
