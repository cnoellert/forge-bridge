# Phase A.5 — Chain Execution Reliability Audit

**Status:** approved (Path B, decomposed)
**Opened:** 2026-05-06
**Milestone:** v1.5 Legibility (interrupt — daily-usability blocker)
**Predecessors:** Phase A (truthful chat contract), Phase A.4 (startup-path unification)
**Discipline:** smoke-test → classify → fix in dependency order

---

## Architectural framing

- **Phase A** solved observability.
- **Phase A.4** solved startup-path consistency.
- **Phase A.5** solves reliability in the **shared chain execution layer**.
- Future phases address usability: making truthful, reliable execution legible and comfortable for humans to operate.

---

## Why "Chain Execution Reliability," not "Chat Reliability"

Smoke testing demonstrated that two of the three failures reproduce through the deterministic `/api/v1/exec` path as well as `/api/v1/chat`. The failing surface is the shared chain execution layer:

- Router (LLM dispatch)
- Forced-tool wrapper (PR20 short-circuit)
- Narrower (`_tool_filter` / message-based selection)

Naming the phase "chat reliability" would misframe the work. Both surfaces consume the same engine; both are affected.

---

## Smoke-test diagnostic finding (preserved for future readers)

**The failures mask each other.** They are not independent bugs — they form a dependency chain that produces a different symptom depending on which subsystem the request hits first:

```
narrower over-collapse
    → bypasses real LLM loop
    → hides router failure

forced-tool schema mismatch
    → corrupts deterministic / short-circuit path
    → makes narrowed cases appear like tool/runtime failure
```

A flat "list of three bugs" framing would have invited fixing them in arbitrary order. The masking relationship makes order **load-bearing**: until the router is healthy, narrowing correctness cannot be judged; until the forced-call wrapper is fixed, even correctly-narrowed prompts fail with a tool error that obscures whether the rest of the chain works.

This finding was only visible **because** the smoke tests were structured (Test 0 deterministic baseline before Tests 1–5 chat) and treated as observation rather than debugging. Future reliability phases should preserve this discipline.

### Smoke-test results table

| # | Prompt | Expected | Actual | Failure Class | Structural? | Depends On / Blocks |
|---|--------|----------|--------|---------------|-------------|---------------------|
| 0 | `list forge projects` (exec) | `forge_list_projects` success | `forge_list_staged` Pydantic error | narrowing + forced-tool contract | Yes — same engine paths used by chat | Reproduces independent of LLM. Blocks Tests 2/3 root-causing. |
| 1 | "Explain forge-bridge in one sentence." | 200 end_turn, `tool_trace=[]` | 500, 75 s, `tool_loop_error` / `LLMToolError` | router | Yes — LLM path globally non-functional | Blocks Tests 4 (LLM loop) and 5 (degraded). |
| 2 | "List the staged operations." | success, summarized answer | narrowing correct, forced call fails Pydantic, `final_text=""` | forced-tool contract | Yes | Same root cause as Test 0. Mechanical fix. |
| 3 | "List the projects." | `forge_list_projects` | `forge_list_staged` | narrowing | Possibly — depends on reachability finding | Diagnosis blocked until router + forced-call fixed. |
| 4 | "What projects exist and how many staged ops are pending?" | multi-tool LLM loop | PR20 short-circuit fired, single tool, empty `final_text` | narrowing (over-eager) | Yes — narrower hijacks any keyword-matched query before LLM sees it | Hides router brokenness from tool-using queries. |
| 5 | "What Flame projects exist?" | graceful degraded behavior | 500, 75 s, identical to Test 1 | router | Yes | Reachability filter works, but degraded narrowing unjudgeable while router down. Blocked by Test 1. |

---

## Phase decomposition (sequential with one parallel-investigation seam)

Three sub-fixes. Each sub-fix has its **own verification** before the next is considered complete.

### A.5.1 — Router health

**Symptom**
- `LLMToolError` at iter=0
- ~75 s wall-clock delay
- Occurs on every prompt that escapes the narrower

**Diagnostic**
- Bisect what changed since the last known healthy chat session (`2026-05-05 14:25:56`, log: `mcp_http.log`).
- Verify Ollama reachability **from inside the daemon process**, not just the shell.
- Check adapter config / env resolution.
- Inspect blocked event loop / semaphore / connection-pool issues in the router.
- Inspect lifecycle/startup effects from recent runtime unification (Phase A.4).

**Verification**
- Smoke Test 1 passes: `"Explain what forge-bridge is in one sentence."` → 200, `stop_reason=end_turn`, `tool_trace=[]`.
- Smoke Test 5 no longer collapses to router failure (independent of degraded-state correctness).
- Real LLM loop executes.
- No `TimeoutError` / `LLMToolError` at iter=0.

**Hard elevate condition**

If the bisect points at Phase A.4-adjacent runtime code — including `bootstrap_daemon()`, `teardown_daemon()`, `lifespan`, asyncio loop ownership, daemon lifecycle, or startup-path unification — **STOP Phase A.5**.

Do **not** patch around it to keep A.5 moving. Elevate A.5.1 into its own daemon-runtime phase.

Reason: at that point this is no longer "router health"; it is **runtime integrity uncertainty**.

---

### A.5.2 — Forced-tool wrapper schema contract

**Symptom**
- Forced-call wrapper passes `{}` to tools whose Pydantic model requires a `params` field.
- Validation fails before the tool runs.
- Observed with `forge_list_staged`.
- Reproduces through deterministic path, not chat-only.

**Diagnostic**
- Confirm whether the required `params` field is intentional in `forge_bridge/tools/*.py`.
- Check for Pydantic v2 / default-factory contract drift.
- Decide one contract:
  - either the forced wrapper synthesizes `{"params": {}}`,
  - or tools accept truly empty arguments.

**Verification**
- Smoke Test 0 passes.
- Smoke Test 2 passes: `"List the staged operations."` → tool succeeds, `tool_trace[0].error is None`.
- `final_text` non-empty for Test 2 once A.5.1 is healthy (depends on real LLM loop running after the forced tool).

**Parallelization rule**
- A.5.2 **may** be investigated in parallel with A.5.1.
- A.5.2 **may not** be merged or landed if A.5.1 elevates into a daemon-runtime phase.

Reason: if runtime integrity is uncertain, even mechanical contract fixes should not land concurrently against an unstable substrate.

---

### A.5.3 — Narrower correctness + over-eagerness

Two distinct issues bundled here because they share the same code surface.

**Issue 3a — Semantic mismatch**
- `"list projects"` → `forge_list_staged`
- Expected: `forge_list_projects`

**Issue 3b — Over-eager collapse**
- Multi-intent prompts collapse to one tool.
- PR20 short-circuit fires too aggressively.
- LLM is hijacked instead of allowed to plan.

**Diagnostic**
- **Defer until A.5.1 is healthy.** Do not tune narrowing while the LLM path is dead.
- Evaluate the narrower against a working LLM baseline.
- Inspect keyword weights, tool-name matching, reachability filter effects.

**Verification**
- Smoke Test 3 passes: `"List the projects."` → `forge_list_projects`.
- Smoke Test 4 passes: `"What projects exist and how many staged operations are pending?"` does not collapse incorrectly into a single forced tool.
- Real LLM loop gets a chance to plan when intent is multi-tool.

---

## Regression tests

Codify the **smoke-test diagnostic structure**, not just pass/fail outcomes. Tests must preserve:

- prompt
- expected routing path
- whether the short-circuit should fire
- whether the LLM loop should execute
- expected `tool_trace` count
- expected selected tool(s)
- expected failure / success shape

### Required assertion (from Smoke Test 1)

For a purely conversational prompt:

```
"Explain what forge-bridge is in one sentence."
```

It is acceptable for `tools_filtered > 0`. But:

- No tool should be called.
- `tool_trace` must be `[]`.
- `stop_reason` should be `end_turn`.
- The real LLM path must be healthy.

This assertion catches the masking class of bug: candidate tools may exist, but the model must still be able to choose **not** to use them.

---

## Vocabulary learnings requirement

Create one `docs/learnings/` note for the narrowing / vocabulary findings.

**Timing:** write the note **at the moment the first narrowing-fix decision is made**, not after phase close. Append the second narrowing issue/fix when decided.

**Shape:** one note covering both narrowing issues. Must capture:
- What real usage exposed.
- Why `"list projects"` mapped incorrectly to `forge_list_staged`.
- Why multi-intent prompts were over-collapsed.
- What diagnostic evidence drove the fix.
- Why architecture review did not reveal this friction.

This is **not** a seed. It is a learnings artifact for future v1.6 vocabulary work.

---

## Invariants (must hold across all A.5 work)

- PR31 envelope contract preserved on `/api/v1/exec`.
- Phase A truthful chat contract preserved on `/api/v1/chat`.
- `ChatTurnResult` behavior preserved.
- `tool_trace` remains truthful.
- Public `forge_bridge.__all__` stays at 19.
- No new external libraries.
- No UI / Ask / Schematic work absorbed into A.5.

---

## Out of scope (plant seeds, do not absorb)

| Tangent | Seed |
|---------|------|
| Tool-row UI rendering | `SEED-CHAT-UI-TOOL-ROW-RENDERING-V1.5+` |
| Ask / Foundry surface | `SEED-FLAME-CHAT-FOUNDRY-V1.6+` |
| Schematic | `SEED-NODE-SCHEMATIC-V1.6+` |
| Streaming | `SEED-CHAT-STREAMING-V1.4.x` |
| Auth | `SEED-AUTH-V1.5` |
| Full vocabulary phase | defer to v1.6; only write the learnings note now |

---

## Phase-end conditions

| Trigger | Response |
|---------|----------|
| A.5.1 reveals systemic daemon / runtime uncertainty | STOP. Elevate to a daemon-runtime phase. Do not continue A.5 as scoped. |
| A.5.2 reveals broad `tools/*` schema drift across many tools (not just `forge_list_staged`) | Shrink A.5 to A.5.1 + A.5.2. Defer A.5.3 to a vocabulary / reliability follow-up. |
| A.5.3 reveals broader vocabulary / ontology failure | Fix only the confirmed smoke-test prompts. Capture broader issue in learnings + seeds. Do not absorb full vocabulary redesign. |

The phase boundary must respond to evidence.

---

## Execution order

1. **A.5.1** router health (in progress)
2. **A.5.2** forced-tool schema contract (may investigate in parallel; landing gated on A.5.1 staying inside the current phase boundary)
3. Re-smoke-test (Tests 0, 1, 2, 5) before A.5.3
4. **A.5.3** narrowing correctness
5. Write `docs/learnings/` vocabulary note at the moment the first narrowing-fix decision is made
6. Final re-smoke-test (Tests 0–5) before close

---

## Methodology meta-observation (do not formalize yet)

This phase contains reusable reliability-phase methodology:

- smoke-test-first
- classify-before-fixing
- dependency-ordered stabilization
- observability before reliability

When A.5 closes, evaluate whether to extract a durable process artifact (`docs/methodology/reliability-phase.md`). **Not part of this phase.** Promotion requires at least one additional successful reliability phase before consideration. Avoid prematurely calcifying process from a sample size of one.
