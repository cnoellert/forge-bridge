---
milestone: v1.10
phase: DI.1
phase_name: The Dispatch-Authority Gate
type: phase-plan
status: cycle-2-draft
drafted: 2026-06-01
derives_from: .planning/phases/DI.1-dispatch-authority-gate/DI.1-FRAMING.md (cycle-3, converged)
artifact_role: executable task breakdown for DI.1. Shape-locks grounded by direct read at draft time ([[feedback-substrate-shape-grounding-at-plan-stage]]).
grounding: live reads 2026-06-01 — registry.py:122-137 (PROV-04 block, exact); cli/discover.py:89 (_annotation_value reader); handlers.py:695-711 (tool_unresolved JSONResponse envelope — the 1B block precedent) + :720-722 (the 1B dispatch); _step.py:407-414 ({error:{type,message}} dict + the 1C dispatch); _chat_compile.py:158/100-112 (1A commit-route + would_mutate-from-token); graph/commit.py:27/77/93 (is_commit_step regex, graph_contains_commit_node)
---

# DI.1 — Plan

> Executable breakdown of the converged DI.1 framing. The safety guarantee is
> carried entirely by **T5/T6** (1B/1C dispatch-edge gates); everything else is
> sequencing, enabling tooling, or the best-effort 1A layer. Shape-locks below are
> read off the code, not assumed.

## Q-DI1.4 — resolved (the framing's one open question)

Regression-lock surface = **both**: a **unit** test (the shared reader is
fail-closed) + an **integration** test (each of 1B/1C blocks a known mutation
tool *at the dispatch edge*, proving it never reaches `call_tool`). The
integration test is the real invariant lock and it targets **1B/1C only** — not
1A (1A owns no safety; see framing).

## Dispatch topology — full enumeration (plan-check, cycle-2)

There are **7** `call_tool` sites, not 3. The plan-check classifies every one so
nothing is silently missed and the authorized path is not broken. **Unifying
principle:** DI.1 gates exactly the edges where **routing** selected the tool —
that is where "authority must not depend on routing" applies. Where the **caller**
chose the tool, or authority was **already granted**, it is not routing's call.

| Site | Disposition | Why |
|---|---|---|
| `handlers.py:722` (1B forced) | **GATE (T5)** | routing chose the tool |
| `_step.py:409` (1C chain) | **GATE (T6)** | routing chose the tool |
| `_step.py:778` (verify), `:834` (apply) | **EXCLUDE — do NOT gate** | post-ratification apply (`manifest.apply_counterpart`, `mode="verify"`) — *carries* authority; gating it **breaks ratified applies** (regression) |
| `registry.py:251` (`invoke_tool`) | out of DI.1 scope (name it) | agentic-loop / MCP-client executor; **not on the chat compile path** A.1 replaced. The MCP *client* owns the `readOnlyHint` decision. *If the agentic loop is still reachable with mutation tools, that's a follow-on candidate, not DI.1.* |
| `cli/run.py:45` (`fbridge run`) | out of DI.1 scope (name it) | operator *explicitly names* the exact tool — not routing |
| `_tool_chain.py:173` | out of scope (infra) | hardcoded read (`forge_list_projects`) for param resolution |

**The regression guard is load-bearing:** T5/T6 add the check *only* at `:722` and
`:409` — never at `:778/:834`. The integration test (T8) must include a positive
case: a **ratified apply still executes** through `:778/:834` unblocked.

## Tasks (ordered; dependencies noted)

### T1 — Capture-seam extension *(enabling; no behavior change)*
Extend the comprehension capture (`forge_bridge/comprehension/`) to also fire on
`preview_emitted` / `chain_aborted` / forced-tool-error, each with an **outcome
tag**. Today capture writes only on successful synthesis, so it is blind to
exactly the failures DI.1 changes. **Why first:** the baseline (T2) and the
acceptance evidence must be captured at these seams.
*Lands first; no dependency.*

### T2 — Baseline *(enabling; measure-first)*
Re-run the 11 dogfood reads on current `main` and record the **failure-shape**
(not just counts) — the contemporaneous control
([[feedback-baseline-drift-invalidates-controls]]) DI.1 is measured against.
Artifact under `UAT/`. *Depends on T1 (so the baseline is captured structurally).*
*Daemon: stdio-held-open bring-up (torn down at CR.1 close).*

### T3 — Registration-boundary close *(substrate-first; Decision 2)*
`registry.py:127` — one line:
`if source == "synthesized":` → `if source in {"synthesized", "user-taught"}:`
(+ update the `:118-121` PROV-04 comment to name both sources). Effect: the
absent-`readOnlyHint` set becomes ∅ universally — consumer `user-taught` tools
default mutating-until-annotated (safe side, consumer-fixable via
`annotations={"readOnlyHint": True}`). **Lands before enforcement** so fail-closed
has no flag-day. *Test:* a `user-taught` tool registered with no annotations →
`readOnlyHint is False`. *No dependency; precedes T5/T6.*

### T4 — The shared reader `dispatch_authority` *(the helper)*
New `dispatch_authority(tool) -> bool` (`is_mutating`), fail-closed:
returns **read only if** `readOnlyHint is True`; **absent / False / unknown ⇒
mutating**. **T4a RESOLVED (grounded):** the reader is `getattr(getattr(tool,
"annotations", None), "readOnlyHint", None) is True` — the exact runtime access
`discover.py:89` (`_annotation_value`) proves works (annotations is an object,
attribute-accessed). `_annotation_value` is pure `getattr` (3 lines, no deps), and
**`forge_bridge/console/` imports nothing from `forge_bridge/cli/`** (verified) —
so importing the cli helper would be a new backwards dependency. Therefore: a
**self-contained `forge_bridge/console/_authority.py`** (no cli import), reader
inlined. *Unit test:* True→read; False/absent/unknown→mutating. *Depends on
nothing; blocks T5/T6/T7.*

### T5 — 1B gate: forced dispatch *(SAFETY FLOOR)*
`handlers.py` — **before** `:721` (`normalize_tool_args` / `call_tool`): if
`dispatch_authority(tool)` is mutating, **short-circuit** — do NOT call the tool.
Return a deterministic block **mirroring the `tool_unresolved` envelope**
(`:695-711`): `status_code=200`, `X-Request-ID`, and a body with a new
`stop_reason="blocked_unratified_mutation"`, `tool`, `classification:"mutating"`,
and the template message (framing item 4). *Integration test:* a known mutation
tool forced → blocked, `call_tool` never invoked. *Depends on T4 (+ T3 landed).*

### T6 — 1C gate: chain dispatch *(SAFETY FLOOR)*
`_step.py` — **before** `:409` (`mcp.call_tool`): same `dispatch_authority`
check; if mutating, return a block **dict matching the existing `{error:{type,
message}}` shape** (`:411-414`) — `{"error":{"type":"unauthorized_mutation",
"message":<template>}, "classification":"mutating", "tool":tool_name}` + the
outcome tag for T1 capture. *Integration test:* a mutation tool in a non-commit
chain → blocked at `:409`, not executed. *Depends on T4 (+ T3).*

### T7 — 1A best-effort strip *(correctness; backstopped by T6/1C)*
`_chat_compile.py:158` — when `graph_contains_commit_node(steps)` AND the
non-commit steps can be **cheaply** confirmed all-reads *without invoking the
narrowing functions* (`_step.py:251/260` are DI.2's — **off-limits**): strip the
commit (`[s for s in steps if not is_commit_step(s)]`) and route to execute → the
read runs the normal pipeline and the **existing** answer-pass answers it for
free. Else: leave the preview (annoying-but-safe). **T7a RESOLVED (grounded):**
"cheaply" = each non-commit step's **first token** is the intended tool name
(`_chat_compile.py:97`, `first_token = step_text.split(maxsplit=1)[0]`, already
used as `tool_name` at `:100`). So exact-match each `first_token` against the
in-scope `tools` list and classify via `dispatch_authority`; strip only if
**every** step exact-matches a single **read** tool, else leave preview. Pure name
lookup — **never** calls `filter_tools_by_message`/`deterministic_narrow`
(`:251/260`, DI.2's region). A wrong strip cannot mutate (T6/1C backstops).
*Depends on T4; lowest priority.*

### T8 — Regression-lock *(the invariant)*
Unit (T4 fail-closed) + integration (T5 + T6 each block a known mutation at the
edge). The integration test is the tested acceptance criterion: **no mutation
tool executes via any *routing* dispatch edge without authority** — AND a
**positive case: a ratified apply still executes** through `_step.py:778/834`
unblocked (the regression guard for the excluded authorized path). *Depends on
T5, T6.*

## Critical path & sequencing

`T1 → T2` (baseline) · `T3` (boundary, before enforcement) · `T4 → {T5, T6} → T8`
(the guarantee) · `T7` rides after T4, off the critical path. **The shippable
non-negotiable is T3 + T4 + T5 + T6 + T8.** T7 is correctness polish; T1/T2 are
measurement. DI.2 follows immediately (framing commitment).

## Shape-locks (grounded, do not re-derive)

- 1B block envelope = `handlers.py:695-711` (`JSONResponse`, `status_code=200`,
  `X-Request-ID`, `stop_reason` body field). New taxon
  `blocked_unratified_mutation`.
- 1C block shape = `_step.py:411-414` `{error:{type,message}}` dict + classification.
- `registry.py:127` literal change above; PROV-04 default is `setdefault`, so an
  explicit consumer `readOnlyHint=True` is preserved.
- `would_mutate`/`requires_ratification` derive from the bare `commit` token
  (`_chat_compile.py:102/112`), **not** tool mutation-ness — so T7's strip-safety
  reads `dispatch_authority`, never commit semantics.

## Constraints (inherited, binding)

`__all__` stays **19**; no new external libs. Mutating path
(preview→ratify→apply, `AssentRecord`) untouched. No new model authority — the
block explanations are deterministic templates; the 1A free-answer is the
existing read pipeline, not a new model call. Fail-closed everywhere.

## Status

**Cycle-2 plan draft, 2026-06-01 (plan-check folded).** Eight tasks; safety floor
= T3+T4+T5+T6+T8. Plan-check results:

- **Full dispatch topology enumerated — 7 sites, not 3** (counts load-bearing).
  New §Dispatch topology classifies every one. **Regression catch:** the
  authorized post-ratification apply path (`_step.py:778/834`) must be **excluded**
  from the gate, with a positive T8 test that ratified apply still executes.
- **Scope principle named:** DI.1 gates where *routing* chose the tool (1B/1C);
  not where the *caller* chose (`fbridge run`, MCP-direct `invoke_tool`) or
  authority was already granted (apply). The two out-of-scope edges are named, not
  silently ignored.
- **T4a RESOLVED:** self-contained `console/_authority.py` reader (`getattr`,
  mirrors `discover.py:89`); console imports nothing from cli (verified) — no cycle.
- **T7a RESOLVED:** "cheaply" = exact first-token name lookup over the tools list;
  never touches the narrowing functions.

No open sub-decisions remain. Shape-locks grounded by direct read. Ready for
execute (safety floor T3→T4→T5/T6→T8 first; T7 after).
