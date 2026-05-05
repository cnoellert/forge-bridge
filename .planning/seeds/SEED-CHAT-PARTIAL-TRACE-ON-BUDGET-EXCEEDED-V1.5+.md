---
name: SEED-CHAT-PARTIAL-TRACE-ON-BUDGET-EXCEEDED-V1.5+
description: When complete_with_tools() raises LLMLoopBudgetExceeded (or asyncio.TimeoutError) mid-loop, surface the partial tool_trace and partial messages collected so far on the 504 envelope rather than discarding them. Today's 504 returns only error.code + error.message; consumers cannot see what tools fired before the budget cap blew.
type: forward-looking-feature
planted_during: Phase A chat-contract realignment (2026-05-05) — explicit out-of-scope item from the implementation brief, planted as the prerequisite to Phase A.2
trigger_when: Phase A has been in production for >=2 weeks AND a real budget-exceeded incident hides tool activity from a debugging consumer (Ask dialog or schematic) OR post-mortem analysis of a chat hang requires partial-trace visibility OR a dedicated debugging surface (forge doctor chat, schematic event panel) needs incident-time tool history
---

# SEED-CHAT-PARTIAL-TRACE-ON-BUDGET-EXCEEDED-V1.5+: surface partial chat history when the loop budget blows

## Idea

When `complete_with_tools()` exits via `LLMLoopBudgetExceeded` (D-03 max_iterations / D-04 max_seconds) or `asyncio.TimeoutError` (CHAT-02 outer 125s wall-clock), the chat handler currently emits a 504 envelope containing only `{error: {code, message}}` and a request_id. The partial conversation that the router *did* assemble before the cap fired — including any tool calls that completed and the model's intermediate turns — is discarded.

This seed proposes: on budget-exceeded, attach the partial `messages` array and partial `tool_trace` to the 504 response body so consumers can render what happened before the failure.

## Why This Matters

After Phase A lands, the chat contract round-trips full tool history on success. On the failure path (504), we revert to the same information loss Phase A just fixed — but worse, because the consumer now sees ONLY the error, with zero context.

Two surfaces will need this once they exist:

1. **Ask dialog (SEED-FLAME-CHAT-FOUNDRY-V1.6+).** When the foundry hangs at the cap, the artist sees "Response timed out" and nothing else. They can't tell whether the model fired any tools, what those tools returned, or whether the hang was on the model's side or a tool's side. With partial trace, the dialog can render: "Called `forge_list_projects` -> returned 3 projects, then timed out."

2. **Schematic / event panel (SEED-NODE-SCHEMATIC-V1.6+).** Live event rendering of in-flight chat turns wants the same data — a turn that exited via budget-exceeded should still show the tool call nodes that completed, with the failed turn marked. The current 504 strips that.

This is also a debugging affordance for the operator. Today, diagnosing a chat hang requires reading server logs because the API response carries nothing actionable. With partial trace, `fbridge chat --debug` could surface tool activity inline.

## Boundaries

In scope (when this seed activates):
- Modify `complete_with_tools()` (or its caller) so `LLMLoopBudgetExceeded` carries `partial_messages` + `partial_tool_trace` payload — likely as exception attributes, not a return.
- Update chat handler's 504 path (handlers.py around line 1131 and 1144) to attach partial trace to the error envelope when present.
- Same treatment for `asyncio.TimeoutError` (outer wait_for path).
- Define the failure-envelope shape: `{error: {code, message, partial_messages?, partial_tool_trace?}}` — additive, optional fields only.

Out of scope (initial):
- Reflowing partial trace into the success contract (success and failure remain distinct shapes).
- Streaming or progressive emission during the loop.
- UI changes to render partial trace (orthogonal — wire data first, render later).
- Recovery / continuation of an interrupted loop (a fresh chat call must start fresh; this seed is about visibility, not retry).

## Implementation Sketch

The router already holds `state["messages"]` across iterations and (post-Phase A.2) builds `tool_trace` incrementally. When the iteration cap or wall-clock cap fires:

```python
raise LLMLoopBudgetExceeded(
    reason="max_iterations",
    iterations=max_iterations,
    elapsed=time.monotonic() - started,
    partial_messages=adapter.to_chat_messages(state, terminal_text=""),
    partial_tool_trace=list(tool_trace),
)
```

The exception class gains two optional attributes. The handler's 504 path checks for them and attaches to the envelope when present. Backward-compatible: callers that don't read the new fields keep their current behavior.

## Failure-Visibility Invariant Extension

Phase A established: "the system must never collapse a failed tool call into a successful final_text." This seed extends it: "the system must never report a budget-exceeded failure without surfacing the tools that DID complete before the cap fired, when that data exists."

## Breadcrumbs

Code references (current as of 2026-05-05):
- `forge_bridge/llm/router.py` — `complete_with_tools()` raises `LLMLoopBudgetExceeded` at line ~613 (max_iterations) and ~628 (max_seconds via wait_for).
- `forge_bridge/llm/router.py:90` — `LLMLoopBudgetExceeded` class definition; gains `partial_messages` + `partial_tool_trace` attributes.
- `forge_bridge/console/handlers.py:1131-1149` — 504 emission paths for both timeout sources.
- Phase A `tool_trace` construction (post-implementation) — the data this seed surfaces.

## Why Plant Now

The user explicitly carved this out of the Phase A scope ("Out of scope: Partial trace on loop timeout (LLMLoopBudgetExceeded)") AND named it as the gating prerequisite for Phase A.2 implementation. Planting it now closes the loop on the scope boundary and gives v1.5+ planning a concrete artifact to point at when the trigger conditions hit.
