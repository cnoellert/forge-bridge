"""TF.3a Step 2 — instrumented capture: real compile/dispatch -> frozen ObservedTrace.

The capture path drives the PRODUCTION compile/dispatch seam — it does NOT
reimplement it. ``run_compile_branch`` (`console/_chat_compile.py`) is the
non-HTTP orchestration the chat handler itself calls ("It does not own HTTP
response shaping"); it returns a structured ``CompileBranchOutcome``. We pair it
with the production ``filter_tools_by_message`` and freeze the result into an
``ObservedTrace``. The freeze is the point (TF.3a plan): capture has model
non-determinism, but a captured trace is frozen ONCE so detectors run
deterministically against it.

Scope (Step 2): the **compile path** (filter -> compile -> classify ->
preview/dispatch) — the dominant translation surface (reads, contextual,
extraction, grounding, non-shadow routing). ``tool_forced`` is the **forced
path** (`_execute_forced_tool`), orchestrated ABOVE ``run_compile_branch`` in
the handler and gated by ``is_tool_enforced``; capturing it is an ADDITIVE
follow-on that reuses the existing ``_execute_forced_tool`` function (no
production change), wired when the routing/shadow cells are authored (Step 4).
On the compile path ``tool_forced`` is False by construction.
"""
from __future__ import annotations

from typing import Any, Optional

from forge_bridge.console._chat_compile import (
    CompileBranchOutcome,
    run_compile_branch,
)
from forge_bridge.console._param_extract import extract_explicit_params
from forge_bridge.console._tool_filter import filter_tools_by_message
from forge_bridge.translation_oracle._detect import compute_well_formed

# regime (CompileBranchOutcome) -> ObservedTrace.outcome
_REGIME_TO_OUTCOME: dict[str, str] = {
    "compile_error": "compile_error",
    "chain_aborted": "chain_aborted",
    "compiled_mutating_preview": "preview_emitted",
    "compiled_non_mutating": "answered",
}


def _first_tool(steps: list[str]) -> Optional[str]:
    if not steps:
        return None
    head = steps[0].strip()
    return head.split(maxsplit=1)[0] if head else None


def _abort_reason(outcome: CompileBranchOutcome) -> Optional[str]:
    """The fine abort signal, where :407 UNRESOLVED_REQUIRED_PARAM surfaces.

    compile_error -> the CompileError type name; chain_aborted -> the dispatch
    error's ``original_error.type`` (the run_chain_steps envelope, _engine.py).
    """
    if outcome.regime == "compile_error" and outcome.compile_error is not None:
        return type(outcome.compile_error).__name__
    if outcome.regime == "chain_aborted" and isinstance(outcome.chain_body, dict):
        err = outcome.chain_body.get("error") or {}
        original = err.get("original_error") or {}
        return original.get("type") or err.get("code")
    return None


def _observed_resolved_params(steps: list[str]) -> dict[str, dict]:
    """Per-step extracted params from the OBSERVED graph.

    Uses the production ``extract_explicit_params`` — the same extractor the
    preview path uses (`_chat_compile.py:125`). This is the observed-param
    signal the extraction detector reads (key-in-step-text vs key-in-params).
    Keyed by step index as a string for JSONL stability.
    """
    return {str(i): extract_explicit_params(step) for i, step in enumerate(steps)}


def observed_trace_from_compile_outcome(
    *,
    outcome: CompileBranchOutcome,
    tools_filtered: int,
    tool_forced: bool = False,
    capture_provenance: str = "instrumented-translation",
) -> dict:
    """Map a CompileBranchOutcome to a frozen ObservedTrace dict (pure)."""
    steps = list(outcome.steps or [])
    mapped_outcome = _REGIME_TO_OUTCOME.get(outcome.regime, outcome.regime)
    well_formed, reason = compute_well_formed(steps, outcome=mapped_outcome)
    trace = {
        "capture_provenance": capture_provenance,
        "observed_graph": steps,
        "observed_resolved_params": _observed_resolved_params(steps),
        "outcome": mapped_outcome,
        "tool_forced": tool_forced,
        "tools_filtered": tools_filtered,
        "abort_reason": _abort_reason(outcome),
        "tool_selected": _first_tool(steps),
        "well_formed": well_formed,
        "well_formed_reason": reason,
        "salvage_applied": bool(getattr(outcome, "salvage_applied", False)),
        "original_reason": getattr(outcome, "salvage_reason", None),
    }
    return trace


async def capture_observed_trace(
    *,
    router: Any,
    tools: list,
    mcp: Any,
    user_prompt: str,
    request_id: str,
    client_ip: str,
    started: float,
    **branch_kwargs: Any,
) -> dict:
    """Run the real compile path for ``user_prompt`` and freeze an ObservedTrace.

    Reuses the production filter + ``run_compile_branch``. Requires a live
    ``router`` (compile calls the model) and ``mcp`` (dispatch); the actual
    running of captures over the authored corpus happens at Step 4 — Step 2
    ships the mechanism, verified deterministically via the pure mapper.
    """
    filtered = filter_tools_by_message(tools, user_prompt)
    outcome = await run_compile_branch(
        router=router,
        user_prompt=user_prompt,
        tools=filtered,
        mcp=mcp,
        request_id=request_id,
        client_ip=client_ip,
        started=started,
        **branch_kwargs,
    )
    return observed_trace_from_compile_outcome(
        outcome=outcome,
        tools_filtered=len(filtered),
    )
