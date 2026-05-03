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
import logging
from typing import Any, Awaitable, Callable, Optional, Union

from forge_bridge.console._memory import _MEMORY

logger = logging.getLogger(__name__)


# PR27 — sentinel key for the disambiguation payload returned by
# ``resolve_required_params`` when the resolver finds multiple
# candidates. Centralized here so handler code (and any future
# trace/log consumers) can import the canonical name instead of
# coupling to a string literal across modules. The string value is
# part of the wire contract internally; do NOT rename it casually.
DISAMBIGUATION_KEY = "__disambiguation__"


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


async def _resolve_project_id(
    mcp: Any,
) -> Optional[Union[str, list[dict]]]:
    """Three-valued return: pin the system state to one of three buckets
    so callers can route deterministically without ever guessing.

      - ``str``       — exactly one project; the lone id is returned.
                        Caller path: inject + memory write (PR26).
      - ``list[dict]`` — two-or-more projects; a sanitized candidates
                        list of ``{"id", "name"}`` entries is returned
                        in upstream order. Caller path: PR27
                        disambiguation (no inject, no memory write,
                        handler short-circuits with MULTIPLE_PROJECTS).
      - ``None``      — zero projects, transport error, or any
                        malformed entry. Caller path: existing PR22
                        graceful contract (MISSING_PROJECT_ID surfaces
                        downstream).

    Strict fail-closed on the multi-candidate path: a single malformed
    project entry collapses the entire result to ``None``. Better to
    surface a missing-context error than expose half-validated
    candidates to a caller selecting from them.

    Validation rules:

      - ``id`` is REQUIRED and strictly validated: it must be a
        non-empty string. Any malformed entry collapses the entire
        result to ``None`` (fail-closed). Rationale: the caller will
        use ``id`` as the canonical project handle in a subsequent
        tool call — a missing/empty/non-string id has no recovery
        path downstream, so surface the failure early.

      - ``name`` is OPTIONAL and best-effort: if missing or
        non-string, it is normalized to ``""``. ``name`` is included
        only for display purposes (e.g. the chat UI rendering a
        disambiguation prompt). It is NEVER consumed as a
        disambiguator or fallback identifier, so a missing/blank
        ``name`` must NOT degrade the determinism of selection.

    DO NOT "fix" ``name`` validation by tightening it to require a
    non-empty string. That change would silently start failing
    legitimate multi-project deployments where projects exist with
    blank or non-string names — a regression that would surface only
    in production and only on the disambiguation path.
    """
    try:
        raw = await mcp.call_tool("forge_list_projects", {})
    except Exception:  # noqa: BLE001 — fail closed on any error
        return None

    data = _extract_structured(raw)
    if not isinstance(data, dict):
        return None
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        # Zero projects, or non-list payload — fall through to fail
        # closed. The downstream tool's PR22 contract surfaces
        # MISSING_PROJECT_ID.
        return None

    # Single — the PR25/PR26 single-id path.
    if len(projects) == 1:
        only = projects[0]
        if not isinstance(only, dict):
            return None
        pid = only.get("id")
        if not isinstance(pid, str) or not pid:
            return None
        return pid

    # Multi — build a sanitized candidates list. Strict: any malformed
    # entry collapses the whole result to None (per PR27 constraint #4).
    candidates: list[dict] = []
    for p in projects:
        if not isinstance(p, dict):
            return None
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            return None
        name = p.get("name")
        # ``name`` may be missing/non-string in legitimate data; normalize
        # to an empty string rather than failing the whole list, since
        # ``id`` is the only field a caller actually needs to pick.
        if not isinstance(name, str):
            name = ""
        candidates.append({"id": pid, "name": name})
    return candidates


# Resolver dispatch table — keys match ``_PR25_CHAINS[*]["resolver"]``.
# Decoupling the chain entry from the function reference keeps the
# registry data-shaped (easier to extend/inspect) and avoids forward
# references to async functions that the registry has to know about.
_RESOLVERS: dict[
    str,
    Callable[[Any], Awaitable[Optional[Union[str, list[dict]]]]],
] = {
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

    Resolution order:
      1. **Registry guard (PR25).** Tool not in ``_PR25_CHAINS`` →
         return ``params`` unchanged. No memory read, no upstream call.
      2. **Memory hydration (PR26).** For each required key absent from
         ``params``, consult ``_MEMORY``. Hits merge into a working
         copy; the input ``params`` is not mutated. Memory is read-only
         here — never written without a fresh deterministic resolution.
      3. **Satisfied-via-memory short-circuit (PR26).** If memory
         satisfied every required key, return immediately — NO upstream
         tool call. This is the PR26 UX win: a follow-up request reuses
         an earlier resolution without a probe.
      4. **Resolver dispatch.** Otherwise dispatch to the chain's
         resolver. The resolver's return type is three-valued:

           - ``str``        — single deterministic match (PR25). Write
                              to memory, merge into params, return.
           - ``list[dict]`` — multiple candidates (PR27). Return the
                              ``__disambiguation__`` sentinel; no
                              memory write, no caller params merged
                              (caller path: handler short-circuits to
                              MULTIPLE_PROJECTS).
           - ``None``       — zero candidates or any error. Leave
                              ``params`` untouched; downstream PR22
                              graceful contract surfaces ``MISSING_*``.

    The returned dict is the canonical post-resolution params and MUST
    be the value the caller passes to ``mcp.call_tool`` AND the value
    serialized into ``tool_calls[].function.arguments`` in the trace.
    The disambiguation sentinel is the ONE exception — handler code
    must inspect for ``__disambiguation__`` BEFORE forwarding to the
    tool, since the sentinel is not valid Pydantic input.

    PR27 disambiguation behavior:

      When a resolver returns multiple candidates, this function
      returns a sentinel dict whose only key is ``DISAMBIGUATION_KEY``:

          {DISAMBIGUATION_KEY: {"type": "...", "candidates": [...]}}

      This REPLACES the resolved params entirely. Concretely:

        - Caller-provided params are NOT merged into the sentinel.
          A caller passing ``{"shot_id": "X"}`` will see ``shot_id``
          dropped from the return — the handler short-circuits before
          a tool call would consume it, so preservation buys nothing.
        - Memory values are NOT included. Any keys hydrated from
          ``_MEMORY`` earlier in this function are also dropped.
        - Downstream execution (``mcp.call_tool``) MUST NOT proceed.
          The sentinel is not valid Pydantic input for any tool, and
          forwarding it would surface as an opaque validation error
          instead of the intended structured disambiguation response.

      The handler is responsible for detecting the sentinel via
      ``DISAMBIGUATION_KEY in params`` and short-circuiting to a
      structured error response (today: 400 + ``MULTIPLE_PROJECTS``
      envelope with the candidates list under ``error.details``).
    """
    chain = _PR25_CHAINS.get(tool_name)
    if not chain:
        return params

    required: frozenset = chain["requires"]

    # Treat the caller's `params` as immutable throughout the function.
    # `resolved` is the single working copy that hydration, the
    # short-circuit check, and the resolver-success path all read from
    # and write to. This makes the no-input-mutation contract explicit
    # and removes any dependence on reassignment order — important for
    # future multi-key resolution where intermediate hydration steps
    # might otherwise interleave with resolver writes.
    resolved: dict = dict(params)

    # PR26 — hydrate from memory. Only fill keys that aren't already
    # caller-provided; never overwrite a caller value with a stale
    # memory value (caller-provided wins by virtue of the `not in`
    # guard).
    for key in required:
        if key not in resolved:
            mem_val = _MEMORY.get(key)
            if mem_val:
                resolved[key] = mem_val
                # Debug-only — operators enabling DEBUG on this logger
                # can confirm memory hits without leaking the resolved
                # value into logs/traces. Never log the value itself.
                logger.debug("tool_memory hit key=%s", key)

    if all(k in resolved for k in required):
        # Either the caller supplied everything, or memory did. Either
        # way: no upstream call, deterministic short-circuit.
        return resolved

    resolver_name = chain["resolver"]
    resolver = _RESOLVERS.get(resolver_name)
    if resolver is None:
        return resolved

    if resolver_name == "_resolve_project_id":
        result = await resolver(mcp)

        # PR27 — multiple candidates. Return the disambiguation sentinel;
        # no memory write (ambiguous resolution must NOT poison cache),
        # caller-provided non-required params are NOT merged (the brief
        # specifies a sentinel-only return; the handler short-circuits to
        # MULTIPLE_PROJECTS before any tool would be called anyway).
        if isinstance(result, list):
            return {
                DISAMBIGUATION_KEY: {
                    "type": "project",
                    "candidates": result,
                }
            }

        # PR25/PR26 — single deterministic id. Write to memory, merge
        # into the working copy, return.
        if isinstance(result, str):
            # ``set`` is the ONLY production write site for memory; user
            # input never writes here (no path exists for that today).
            _MEMORY.set("project_id", result)
            # Debug-only — operators see WHEN memory was populated, but
            # never WHAT was stored. Pair with the hit log above to
            # confirm cache behavior under load.
            logger.debug("tool_memory set key=project_id")
            return {**resolved, "project_id": result}

        # ``None`` — zero candidates or error. Fall through to return
        # the un-injected working copy; PR22 contract surfaces
        # MISSING_PROJECT_ID downstream.

    return resolved
