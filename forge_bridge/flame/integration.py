"""PR38 — Flame adapter entry for deterministic command execution.

Flame is a thin integration surface: it forwards a canonical command string and
optional explicit context into :mod:`forge_bridge.console._execute` (PR37).
No HTTP, no LLM, no inference — same guarantees as ``fbridge exec``.

**Context contract** (caller supplies explicit values only; no implicit
``current shot`` resolution here)::

    context = {
        "project_id": "<uuid>",
        "shot_id": "<uuid>",
        # optional:
        "frame": "<int>",
        "path": "<string>",
    }

Keys are appended as ``key=value`` tokens **after** the base command text so
PR28 extraction keeps the **first** ``project_id=`` in the message (the one in
the user's command string when present) — PR26 explicit-in-command wins over
suffixes injected from ``context``.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from forge_bridge.console._execute import execute_command


def run_command_from_flame(
    text: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Flame entrypoint for PR37 deterministic execution.

    Injects explicit ``context`` as trailing ``key=value`` pairs, then runs
    :func:`~forge_bridge.console._execute.execute_command` in-process.

    This function is the only integration point Flame UI code should call for
    bridge command execution.

    The command text must be non-empty (whitespace-only counts as empty).
    Context alone cannot substitute for a missing command.
    """
    stripped = text.strip()
    if not stripped:
        return {
            "status": "error",
            "request_id": str(uuid.uuid4()),
            "chain": [],
            "error": {
                "code": "EMPTY_COMMAND",
                "message": "Command is empty",
                "step_index": None,
                "original_error": None,
            },
        }

    parts: list[str] = [stripped]
    if context:
        for key, value in context.items():
            if not isinstance(key, str) or not key.strip():
                continue
            if isinstance(value, str) and value.strip():
                parts.append(f"{key.strip()}={value.strip()}")

    merged = " ".join(parts)
    return asyncio.run(execute_command(merged))
