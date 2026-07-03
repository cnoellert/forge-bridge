"""PR37 — Direct deterministic execution (no HTTP, no LLM).

Operator contract: see ``docs/DIRECT_EXECUTION.md``. Summary: deterministic only;
no LLM; PR31 envelope always; PR32 context rules enforced; behavior may differ
from chat for non-deterministic inputs.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from forge_bridge.console._constants import CHAIN_MAX_STEPS
from forge_bridge.console._engine import run_chain_steps_with_shadow


async def execute_command(
    text: str,
    *,
    mcp: Any | None = None,
    session_factory: Any | None = None,
) -> dict:
    """Run expanded/parsed text through the shared chain engine.

    Mirrors chat tool snapshot: ``list_tools`` then
    ``filter_tools_by_reachable_backends`` (same order as ``chat_handler``).

    Parameters
    ----------
    text:
        Canonical command string (macros expanded before chain parse).
    mcp:
        MCP client with ``list_tools`` / ``call_tool``. Defaults to the
        in-process FastMCP singleton.
    session_factory:
        Async session factory threaded to persistence-touching graph nodes
        (e.g. the ``stage`` node, which calls ``StagedOpRepo.propose``). When
        ``None``, such nodes return ``GRAPH_SESSION_UNAVAILABLE`` rather than
        crash — but the deterministic ``/api/v1/exec`` entry point supplies the
        daemon's factory so deterministic chains can stage (see
        ``api_v1_exec_handler``). Non-persisting chains are unaffected.
    """
    from forge_bridge.console._chain_parse import parse_chain
    from forge_bridge.console._macros import expand_macro
    from forge_bridge.console._tool_filter import filter_tools_by_reachable_backends
    from forge_bridge.mcp import server as _mcp_server

    if mcp is None:
        mcp = _mcp_server.mcp

    text_stripped = text.strip()
    expanded = expand_macro(text_stripped)

    try:
        tools = await mcp.list_tools()
    except Exception as exc:  # noqa: BLE001
        rid = str(uuid.uuid4())
        return {
            "status": "error",
            "request_id": rid,
            "chain": [],
            "error": {
                "code": "TOOL_REGISTRY_UNAVAILABLE",
                "message": str(exc),
                "step_index": None,
                "original_error": None,
            },
        }

    if not tools:
        rid = str(uuid.uuid4())
        return {
            "status": "error",
            "request_id": rid,
            "chain": [],
            "error": {
                "code": "NO_TOOLS_REGISTERED",
                "message": "No tools registered.",
                "step_index": None,
                "original_error": None,
            },
        }

    tools = await filter_tools_by_reachable_backends(tools)
    if not tools:
        rid = str(uuid.uuid4())
        return {
            "status": "error",
            "request_id": rid,
            "chain": [],
            "error": {
                "code": "NO_BACKENDS_REACHABLE",
                "message": "No tool backends reachable.",
                "step_index": None,
                "original_error": None,
            },
        }

    chain_steps = parse_chain(expanded)
    if not chain_steps:
        rid = str(uuid.uuid4())
        return {
            "status": "error",
            "request_id": rid,
            "chain": [],
            "error": {
                "code": "EMPTY_COMMAND",
                "message": "Nothing to execute after parsing.",
                "step_index": None,
                "original_error": None,
            },
        }

    if len(chain_steps) > CHAIN_MAX_STEPS:
        rid = str(uuid.uuid4())
        return {
            "status": "error",
            "request_id": rid,
            "chain": [],
            "error": {
                "code": "CHAIN_TOO_LONG",
                "message": (
                    f"Chain hit runaway guard at {CHAIN_MAX_STEPS} steps — "
                    f"chain length is normally unconstrained, this likely "
                    f"indicates a pathological loop. Check for runaway "
                    f"recursion or chain misexpansion."
                ),
                "step_index": None,
                "original_error": None,
            },
        }

    request_id = str(uuid.uuid4())
    started = time.monotonic()
    return await run_chain_steps_with_shadow(
        steps=chain_steps,
        tools=tools,
        mcp=mcp,
        request_id=request_id,
        client_ip="direct-exec",
        started=started,
        session_factory=session_factory,
    )
