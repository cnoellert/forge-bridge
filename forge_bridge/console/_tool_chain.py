"""PR25 — Deterministic required-parameter resolution (implicit chaining).

The chat handler's PR20 forced-execution path narrows tool selection to a
single tool, then invokes it with empty arguments. For tools that have
required parameters, this either fails Pydantic validation (no contract)
or surfaces a structured ``MISSING_*`` error (PR22 graceful contract).

PR25 closes the gap when the missing parameter is *unambiguous* in the
current system state: if a tool requires ``project_id`` and the registry
holds exactly one project, inject that project's id and run the tool.
The LLM is never invoked. Resolution is a single-step deterministic
pipeline stage owned by the workflow, not a dynamic decision tree —
each step consumes the previous step's output in a fixed sequence.

This module is the home for that resolution. It supersedes the inline
injection that PR24 placed in ``handlers._execute_forced_tool``.

Hard constraints:
  1. **No recursion.** Single-step resolution only. A resolver issues at
     most one upstream tool call; the chain registry intentionally does
     NOT include the upstream tools themselves.
  2. **Fail closed.** Zero matches, two-or-more matches, or any error
     reading the upstream tool → return ``params`` unchanged. The
     downstream tool's PR22 contract surfaces ``MISSING_*`` to the
     caller; never substitute a default.
  3. **No guessing.** Resolution fires only on a deterministic predicate
     (here: ``len(projects) == 1``). Never pick from a list arbitrarily.
  4. **No LLM involvement.** Runs entirely before any model call.
  5. **Trace integrity.** The caller is responsible for serializing the
     post-resolution params into the assistant message's
     ``tool_calls[].function.arguments`` so the trace reflects what the
     tool actually saw.

The chain registry is intentionally tight — it lists only tools whose
PR22 graceful contract surfaces a structured ``MISSING_*`` payload when
called with ``{}``. Extending coverage requires both (a) adding the new
tool to ``_PR25_CHAINS`` and (b) verifying the tool surfaces the contract
gracefully.
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Optional


# ── Structured-payload extraction ─────────────────────────────────────────


def _extract_structured(raw: Any) -> Optional[dict]:
    """Pull a JSON-decoded dict out of FastMCP's ``call_tool`` return shapes.

    FastMCP's ``call_tool(..., convert_result=True)`` returns one of:
      - 2-tuple ``(content_blocks, structured_dict)`` — convert path;
        prefer ``structured_dict["result"]`` (a JSON string).
      - bare dict — sometimes ``{"result": "<json>"}``, sometimes the
        decoded payload itself.
      - ``Sequence[ContentBlock]`` — extract ``.text`` from the first
        block carrying it.
      - bare string — already the JSON payload.

    Returns ``None`` on any shape or parse failure. Callers MUST treat
    ``None`` as "do not inject" and fall through to the contract error.
    """
    text: Optional[str] = None

    if isinstance(raw, str):
        text = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("result"), str):
            text = raw["result"]
        else:
            # Already a decoded payload; return as-is so callers can
            # inspect it without a parse round-trip.
            return raw
    elif isinstance(raw, tuple) and len(raw) == 2:
        blocks, structured = raw
        if isinstance(structured, dict) and isinstance(
            structured.get("result"), str
        ):
            text = structured["result"]
        elif isinstance(blocks, (list, tuple)):
            for block in blocks:
                bt = getattr(block, "text", None)
                if isinstance(bt, str):
                    text = bt
                    break
    elif isinstance(raw, (list, tuple)):
        for block in raw:
            bt = getattr(block, "text", None)
            if isinstance(bt, str):
                text = bt
                break

    if text is None:
        return None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


# ── Resolvers ────────────────────────────────────────────────────────────


async def _resolve_project_id(mcp: Any) -> Optional[str]:
    """Return the lone project's id, or ``None`` if the rule does not
    deterministically fire.

    Single upstream call: ``forge_list_projects({})``. The result must
    be a structured dict with a ``projects`` list of length exactly 1
    whose lone element carries a non-empty string ``id``. Anything else
    — zero projects, two-or-more, transport error, malformed payload —
    returns ``None``.
    """
    try:
        raw = await mcp.call_tool("forge_list_projects", {})
    except Exception:  # noqa: BLE001 — fail closed on any error
        return None

    data = _extract_structured(raw)
    if not isinstance(data, dict):
        return None
    projects = data.get("projects")
    if not isinstance(projects, list) or len(projects) != 1:
        return None
    only = projects[0]
    if not isinstance(only, dict):
        return None
    pid = only.get("id")
    if not isinstance(pid, str) or not pid:
        return None
    return pid


# Resolver dispatch table — keys match ``_PR25_CHAINS[*]["resolver"]``.
# Decoupling the chain entry from the function reference keeps the
# registry data-shaped (easier to extend/inspect) and avoids forward
# references to async functions that the registry has to know about.
_RESOLVERS: dict[str, Callable[[Any], Awaitable[Optional[str]]]] = {
    "_resolve_project_id": _resolve_project_id,
}


# ── Chain registry ────────────────────────────────────────────────────────


# Tools whose missing required params can be resolved deterministically.
# Each entry MUST list (a) the required param keys and (b) the resolver
# name — both consumed by ``resolve_required_params`` below.
#
# This registry is the SINGLE source of truth for chain coverage. To add
# a new tool: confirm its PR22 graceful contract, then append an entry.
_PR25_CHAINS: dict[str, dict] = {
    "forge_list_versions": {
        "requires": frozenset({"project_id"}),
        "resolver": "_resolve_project_id",
    },
    "forge_list_shots": {
        "requires": frozenset({"project_id"}),
        "resolver": "_resolve_project_id",
    },
}


# ── Public API ────────────────────────────────────────────────────────────


async def resolve_required_params(
    tool_name: str,
    params: dict,
    mcp: Any,
) -> dict:
    """Resolve any missing required params for ``tool_name``.

    Behavior:
      - Tool not in ``_PR25_CHAINS`` → return ``params`` unchanged.
      - All required keys already in ``params`` → return ``params``
        unchanged (no upstream call).
      - Resolver returns a value → return a NEW dict with the resolved
        key merged in. ``params`` is not mutated.
      - Resolver returns ``None`` (zero/many matches, error) → return
        ``params`` unchanged. Caller must surface the contract error.

    The returned dict is the canonical post-resolution params and MUST
    be the value the caller passes to ``mcp.call_tool`` AND the value
    serialized into ``tool_calls[].function.arguments`` in the trace.
    """
    chain = _PR25_CHAINS.get(tool_name)
    if not chain:
        return params

    required: frozenset = chain["requires"]
    if all(k in params for k in required):
        return params

    resolver_name = chain["resolver"]
    resolver = _RESOLVERS.get(resolver_name)
    if resolver is None:
        return params

    if resolver_name == "_resolve_project_id":
        project_id = await resolver(mcp)
        if project_id is not None:
            return {**params, "project_id": project_id}

    return params
