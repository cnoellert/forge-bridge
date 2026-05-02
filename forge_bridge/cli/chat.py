"""forge-bridge chat — testable CLI surface over the blessed `/api/v1/chat`.

Sends a single user message to ``http://<console_host>:<console_port>/api/v1/chat``
(the same endpoint the Artist Console UI uses) and renders the timeout /
retry / response-timing messaging from ``llm.call_wrapper``.

This is *not* a parallel chat path — it consumes the same shared endpoint
and therefore benefits from any improvements made there.
"""
from __future__ import annotations

import json
import sys
import time
from typing import Annotated, Optional

import typer

from forge_bridge import config
from forge_bridge.llm import call_wrapper

# Exit codes
_EXIT_OK = 0
_EXIT_FAIL = 1
_EXIT_UNREACHABLE = 2
_EXIT_TIMEOUT = 3

_KIND_TO_EXIT = {
    "connection": _EXIT_UNREACHABLE,
    "timeout": _EXIT_TIMEOUT,
    "invalid_response": _EXIT_FAIL,
}


def chat_cmd(
    message: Annotated[
        str,
        typer.Argument(help="Message to send to the LLM."),
    ],
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Per-request timeout in seconds."),
    ] = call_wrapper.DEFAULT_TIMEOUT_SECONDS,
    retries: Annotated[
        int,
        typer.Option("--retries", help="Automatic retries on timeout (0 = none)."),
    ] = call_wrapper.DEFAULT_RETRIES,
    backoff: Annotated[
        float,
        typer.Option("--backoff", help="Seconds to wait before each retry."),
    ] = call_wrapper.DEFAULT_BACKOFF_SECONDS,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show model, provider, and timing."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress messages."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit a stable JSON envelope to stdout."),
    ] = False,
) -> None:
    """Send a message to the chat endpoint with timeout + retry usability."""
    url = f"{config.console_url()}/api/v1/chat"
    payload = {"messages": [{"role": "user", "content": message}]}

    # P-01 stdout purity: progress messages go to stderr; suppressed in --json
    # and --quiet modes.
    reporter = None if (as_json or quiet) else _stderr_reporter

    result = call_wrapper.call_with_retry(
        url, payload,
        timeout=timeout, retries=retries, backoff_seconds=backoff,
        reporter=reporter,
    )

    if as_json:
        sys.stdout.write(
            json.dumps({
                "ok": result.ok,
                "data": result.data,
                "error": None if result.ok else {
                    "kind": result.error_kind,
                    "message": result.error_message,
                    "fix": result.fix,
                },
                "attempts": result.attempts,
                "elapsed_seconds": round(result.elapsed_seconds, 3),
                "timeline": result.timeline,
                "trace": result.trace,
            }) + "\n"
        )
        raise typer.Exit(
            code=_EXIT_OK if result.ok else _KIND_TO_EXIT.get(result.error_kind, _EXIT_FAIL)
        )

    if not result.ok:
        if verbose:
            _write_trace_block(result.trace)
            meta = _extract_metadata(result.data)
            sys.stderr.write(
                f"[chat] FAILED kind={result.error_kind}  "
                f"elapsed={result.elapsed_seconds:.2f}s  "
                f"attempts={result.attempts}/{retries + 1}  "
                f"model={meta.get('model', '?')}  "
                f"tool_calls={meta.get('tool_calls', '?')}\n"
            )
        sys.stderr.write(
            f"forge-bridge chat: {result.error_kind}: {result.error_message}\n"
        )
        if result.fix:
            sys.stderr.write(f"fix: {result.fix}\n")
        raise typer.Exit(code=_KIND_TO_EXIT.get(result.error_kind, _EXIT_FAIL))

    # Success path. Extract reply text defensively — the chat endpoint's
    # response shape is owned by chat_handler; we don't enshrine it here.
    reply = _extract_reply(result.data)
    if verbose:
        _write_trace_block(result.trace)
        meta = _extract_metadata(result.data)
        sys.stderr.write(
            f"[chat] elapsed={result.elapsed_seconds:.2f}s  "
            f"attempts={result.attempts}/{retries + 1}  "
            f"model={meta.get('model', '?')}  "
            f"provider={meta.get('provider', '?')}  "
            f"tool_calls={meta.get('tool_calls', '?')}\n"
        )
    sys.stdout.write(reply + ("\n" if not reply.endswith("\n") else ""))


def _stderr_reporter(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def _write_trace_block(trace: dict) -> None:
    """Render the structured trace as a short, ordered narrative on stderr.

    Reads only the trace shape produced by ``call_wrapper`` (PR11). No
    derivation from ``timeline``.
    """
    if not isinstance(trace, dict):
        return
    events = trace.get("events")
    if not isinstance(events, list) or not events:
        return
    lines = ["[trace]"]
    for ev in events:
        if not isinstance(ev, dict):
            continue
        kind = ev.get("kind")
        if kind == "attempt":
            n = ev.get("attempt", "?")
            res = ev.get("result", "?")
            dur = ev.get("duration", 0.0)
            lines.append(f"attempt {n} → {res} ({_fmt_seconds(dur)})")
        elif kind == "backoff":
            lines.append(f"backoff → {_fmt_seconds(ev.get('duration', 0.0))}")
        # summary is rendered as the closing total line below.
    total = trace.get("total_elapsed", 0.0)
    lines.append(f"total → {_fmt_seconds(total)}")
    sys.stderr.write("\n".join(lines) + "\n")


def _fmt_seconds(value: object) -> str:
    try:
        return f"{float(value):.1f}s"
    except (TypeError, ValueError):
        return "?s"


def _extract_reply(data: Optional[dict]) -> str:
    """Pull a renderable text reply out of the chat response."""
    if not isinstance(data, dict):
        return json.dumps(data)
    for key in ("response", "reply", "text", "content", "message"):
        v = data.get(key)
        if isinstance(v, str) and v:
            return v
    messages = data.get("messages")
    if isinstance(messages, list) and messages:
        last = messages[-1]
        if isinstance(last, dict):
            content = last.get("content")
            if isinstance(content, str):
                return content
    return json.dumps(data)


def _extract_metadata(data: Optional[dict]) -> dict:
    if not isinstance(data, dict):
        return {}
    # PR10 verbose: surface tool_calls if the chat handler reports them.
    # Accept either an explicit count or a list we can len() — the chat
    # endpoint owns the exact shape; we just present what's there.
    tc = data.get("tool_calls")
    if isinstance(tc, list):
        tool_calls = len(tc)
    elif isinstance(tc, int):
        tool_calls = tc
    else:
        tool_calls = data.get("iterations")
    return {
        "model": data.get("model"),
        "provider": data.get("provider") or data.get("backend"),
        "iterations": data.get("iterations"),
        "tool_calls": tool_calls,
    }
