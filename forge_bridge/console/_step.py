"""PR30 / PR37 — single chain-step execution (no HTTP, no handler globals).

Moved from ``handlers._execute_chain_step`` so engine and CLI can import without
circular imports from ``handlers``.
"""
from __future__ import annotations

import json
from typing import Any

from forge_bridge.console._tool_filter import deterministic_narrow, filter_tools_by_message


def serialize_forced_tool_result(raw: Any) -> str:
    """Serialize a FastMCP ``call_tool`` return into a string for tracing/context.

    Shared with ``handlers._execute_forced_tool`` — behavior unchanged from the
    original implementation.
    """
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        if "result" in raw and isinstance(raw["result"], str):
            return raw["result"]
        return json.dumps(raw, default=str)
    if isinstance(raw, tuple) and len(raw) == 2:
        blocks, structured = raw
        if isinstance(structured, dict) and isinstance(
            structured.get("result"), str
        ):
            return structured["result"]
        raw = blocks
    if isinstance(raw, (list, tuple)):
        parts: list[str] = []
        for block in raw:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
                continue
            dump = getattr(block, "model_dump_json", None)
            if callable(dump):
                try:
                    parts.append(dump())
                    continue
                except Exception:  # noqa: BLE001
                    pass
            parts.append(repr(block))
        return "\n".join(parts) if parts else ""
    return repr(raw)


async def execute_chain_step(
    *,
    step_text: str,
    tools: list,
    mcp: Any,
    inherited_context: dict,
) -> dict:
    """Run a single chain step end-to-end.

    Returns a dict in one of two shapes:

      Success: ``{"result": ..., "extracted_context": dict,
                  "tool": <tool_name>, "params": dict}``
      Failure: ``{"error": {"type": ..., "message": ..., ...}}``

    Inherited context merges with explicit step params (PR28); PR32 context for
    the next step comes only from ``extract_chain_context(parsed result)`` inside
    this function's success path.
    """
    from forge_bridge.console._chain_parse import extract_chain_context
    from forge_bridge.console._name_resolve import resolve_name_from_candidates
    from forge_bridge.console._param_extract import extract_explicit_params
    from forge_bridge.console._tool_chain import (
        DISAMBIGUATION_KEY,
        resolve_required_params,
    )

    user_params = extract_explicit_params(step_text)

    merged: dict = {**(inherited_context or {}), **user_params}
    requested_name = merged.get("project_name")
    resolver_input = {k: v for k, v in merged.items() if k != "project_name"}

    filtered = filter_tools_by_message(tools, step_text)
    if len(filtered) > 1:
        narrowed = deterministic_narrow(filtered, step_text)
        if len(narrowed) < len(filtered):
            filtered = narrowed
    if len(filtered) != 1:
        return {"error": {
            "type": "tool_selection_ambiguous",
            "message": (
                f"Step matched {len(filtered)} tools; chain steps must "
                "select exactly one. Use a more specific verb/noun "
                "(e.g. 'list versions' instead of just 'list')."
            ),
            "candidates": [
                getattr(t, "name", str(t)) for t in filtered[:5]
            ],
        }}
    tool_name = filtered[0].name

    params = await resolve_required_params(tool_name, resolver_input, mcp)

    if DISAMBIGUATION_KEY in params:
        candidates = (params[DISAMBIGUATION_KEY] or {}).get("candidates", []) or []
        resolved_id = (
            resolve_name_from_candidates(requested_name, candidates)
            if requested_name else None
        )
        if not resolved_id:
            return {"error": {
                "type": "MULTIPLE_PROJECTS",
                "message": (
                    "Multiple projects found; specify project_id=<uuid> "
                    "or project_name=<name>."
                ),
                "details": params[DISAMBIGUATION_KEY],
            }}
        params = await resolve_required_params(
            tool_name, {"project_id": resolved_id}, mcp,
        )

    try:
        raw = await mcp.call_tool(tool_name, params)
    except Exception as exc:  # noqa: BLE001
        return {"error": {
            "type": type(exc).__name__,
            "message": str(exc),
        }}

    serialized = serialize_forced_tool_result(raw)

    parsed: Any = serialized
    try:
        decoded = json.loads(serialized)
        parsed = decoded
    except (ValueError, json.JSONDecodeError):
        pass

    return {
        "result": parsed,
        "extracted_context": extract_chain_context(parsed),
        "tool": tool_name,
        "params": params,
    }
