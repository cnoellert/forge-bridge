"""Flame adapter entry for deterministic command execution (PR42).

Flame is a thin integration surface: it forwards a canonical command string
(with optional explicit context merged as ``key=value`` pairs) to the
forge_bridge console daemon via HTTP (``/api/v1/exec``).

There is no in-process execution, no asyncio, and no direct dependency on
the execution engine. All command resolution and execution occurs in the
daemon.

Empty input is forwarded to the daemon unchanged so that the engine remains
the single source of truth for ``EMPTY_COMMAND`` behavior.

Execution is synchronous and occurs on Flame's UI thread. This may block
the UI for up to the HTTP timeout (default 65s). This behavior is
intentional for PR42 and will be addressed in a future UI-layer improvement.

Transport/protocol failures (daemon unreachable, HTTP errors, invalid JSON)
are caught locally and returned as synthesized PR31-shaped envelopes so
that Flame UI never receives uncaught exceptions.

Engine-originated responses pass through unchanged.
"""
from __future__ import annotations

import json
import os
import socket
import uuid
from typing import Any
from urllib import error, request

_HTTP_TIMEOUT_S = 65.0
_DEFAULT_BASE_URL = "http://127.0.0.1:9996"


def _envelope(code: str, message: str) -> dict[str, Any]:
    # Synthesizes a PR31-shaped envelope for failures that never reach the
    # engine. Engine-originated responses pass through unchanged via
    # json.loads — do NOT route those through here.
    return {
        "status": "error",
        "request_id": str(uuid.uuid4()),
        "chain": [],
        "error": {
            "code": code,
            "message": message,
            "step_index": None,
            "original_error": None,
        },
    }


def run_command_from_flame(
    text: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a Forge command from Flame via HTTP.

    - Merges explicit context as trailing ``key=value`` tokens (PR38 behavior preserved).
    - POSTs the resulting command string to the console daemon (``/api/v1/exec``).
    - Returns the PR31 envelope from the daemon on success.

    For transport/protocol failures (daemon unreachable, HTTP errors,
    invalid JSON), a PR31-shaped error envelope is synthesized locally.
    These envelopes include a locally generated ``request_id`` and do not
    originate from the engine.

    This function intentionally catches broad exceptions to prevent errors
    from propagating into Flame's UI thread, prioritizing stability over
    strict error surfacing.
    """
    command = (text or "").strip()

    # PR38 context merge: drop non-string keys/values and whitespace-only values.
    parts: list[str] = []
    if command:
        parts.append(command)
    if context:
        for k, v in context.items():
            if (
                isinstance(k, str)
                and k.strip()
                and isinstance(v, str)
                and v.strip()
            ):
                parts.append(f"{k.strip()}={v.strip()}")
    merged = " ".join(parts)

    base_url = os.getenv("FORGE_CONSOLE_URL", _DEFAULT_BASE_URL)
    url = f"{base_url}/api/v1/exec"
    payload = json.dumps({"text": merged}).encode("utf-8")

    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
            body = resp.read()

        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return _envelope("INVALID_JSON", "Invalid JSON response from daemon")

    # Order matters: HTTPError is a subclass of URLError, must come first.
    except error.HTTPError as e:
        return _envelope("HTTP_STATUS", f"HTTP {e.code}")

    except (error.URLError, socket.timeout, TimeoutError) as e:
        return _envelope("TRANSPORT_ERROR", str(e))

    # Broad catch is intentional. Flame runs this on the UI thread, and
    # uncaught exceptions can destabilize the host application. We prefer
    # fault-tolerance over strict error surfacing here.
    except Exception as e:  # noqa: BLE001
        return _envelope("UNKNOWN_ERROR", str(e))
