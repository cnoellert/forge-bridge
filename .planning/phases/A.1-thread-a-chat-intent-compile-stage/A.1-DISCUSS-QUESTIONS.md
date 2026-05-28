---
milestone: v1.7
thread: A
phase: A.1
phase_name: Chat intent-compile stage — the compile + preview surface
status: discuss-converged
opened: 2026-05-27
drafted: 2026-05-27
type: phase-discuss
derives_from: .planning/phases/A.1-thread-a-chat-intent-compile-stage/THREAD-A-FRAMING.md
artifact_role: load-bearing — A.1-PLAN.md drafts from these converged rulings
review_state: awaiting-operator-ratification
---

# A.1 — Phase discuss: five framing-grade questions, room-converged

> **What this artifact is.** The discuss-stage output preceding A.1's
> code-handoff phase plan. Captures the room's convergence on five
> framing-grade ambiguities surfaced by the grounding refresh after
> C.1 closed. Creative provided the architectural transition framing;
> DT provided grounded specific rulings + Stage 1b carve-outs +
> forward-looking caveats. Operator ratification pending; once ratified,
> A.1-PLAN.md drafts cleanly against these rulings and goes to Stage 1b.
>
> **What this artifact is not.** Not a phase plan. The plan derives
> from this; the contracts below are framing-grade rulings, not
> implementation specs.

## Architectural transition (Creative, 2026-05-27)

The load-bearing axis Thread A introduces:

```
NL → Compile → Canonical graph → Execution substrate → Host
```

vs. the pre-Thread-A axis:

```
NL → Agentic improvisation → Host
```

The compile stage is the *transformation*; the canonical graph is what
makes the transformation observable and (in A.2) ratifiable. Pre-Phase-N+
the substrate couldn't have supported this transition; post-Phase-N+
it's the natural completion. *"The correct one for a system that already
crossed the authority boundary in Phase N+."*

This framing is load-bearing — DT's five rulings below flow from it.
The compile/execute distinction, the canonical-graph-as-pivot, the
preview-before-host stratification — all are operationalizations of
this single axis.

## Grounding refresh — anchors verified

All G1/G2/G3 framing anchors hold against current main (post-C.1, verified
2026-05-27). C.1's Stage 2 leakage-watch confirmed at file level: no
Thread A surfaces were touched by C.1's eight implementation commits.

| Site | Status |
|---|---|
| `forge_bridge/llm/router.py:422` — `complete_with_tools()` | ✓ signature unchanged |
| `forge_bridge/console/handlers.py:1206` — `chat_handler` | ✓ router invocation at :1712 |
| `forge_bridge/console/_engine.py:14` — `run_chain_steps` | ✓ sequential list[str] executor |
| `forge_bridge/graph/commit.py:93` — `CommitNode.verify(held, fresh)` | ✓ drift-only, no assent |
| `forge_bridge/graph/mutation.py:28` — `MutationManifest` | ✓ frozen 5-field; sibling `MutationManifestError` family at :73 |

## The five rulings (room-converged 2026-05-27)

### R-A1.1 — Compile mechanism: NEW `router.compile_intent(...)`

**Ruling (DT):** Option (a). New `router.acomplete()`-class method
(name: `router.compile_intent(...)`), text-completion under
`sensitive=True` routing, post-parsed into `list[str]` chain-step text.

**Rationale.** Framing Q1 is binding: *"the router stays the agentic
executor it already is and keeps its Phase 24.4 control-flow authority."*
Option (b) routes compile through `complete_with_tools` (the executor
surface) — collapses the compile/execute distinction Creative explicitly
stratifies. Option (c) adds a new component without justification;
`acomplete()` already exposes the sensitive-routing primitives
(`_async_local`/`_async_cloud` at `router.py:418-420`) compile needs.

Option (a) is additive on the router without touching the executor —
per `[[feedback-orchestrator-control-flow-not-meaning]]`: `compile_intent`
is text-completion (model owns meaning); `complete_with_tools` is
orchestration (router owns control flow). Different responsibilities,
different methods.

### R-A1.2 — Execution path: COMMIT-NODE PRESENCE classifier

**Ruling (DT):** Option (b), refined with substrate-grounded criterion.
Graphs containing **zero commit nodes** execute through
`run_chain_steps`; graphs containing **one or more commit nodes** are
**preview-only** in A.1. Classification criterion is commit-node
presence (substrate-grounded), not a read-only/mutating flag
(philosophical).

**Rationale.** Framing thesis: *"makes it structurally impossible for
inferential compilation to bypass the seam exact compilation already
respects."* That seam is the host-mutation seam — a chain with no
commit nodes touches no host-mutation seam and bypasses nothing.

- Option (a) preview-only-for-everything creates an unnecessarily wide
  chat-degraded-mode window — every read-only chat turn regresses.
- Option (c) auto-execute-everything violates the thesis directly —
  mutating chains execute pre-ratify.
- Option (b) is the substrate-honest middle.

**The A.1 ratification stub.** The "stub" of A.2's ratify gate is a
concrete short-circuit: detect commit nodes in compiled graph-intent →
emit preview only, no execution. When A.2 lands the assent-substrate,
the same commit-node detection becomes the ratify-required gate.
Substrate-derived classification, not new substrate. Honors
`[[feedback-substrate-not-producer]]` and avoids the convenience
aggregation pressure the C.1 close cursor flagged.

### R-A1.3 — Preview surface: BOTH JSON + SSE

**Ruling (DT):** Option (c). JSON envelope carries a `preview` field;
SSE emits `event: graph_intent_preview` taxon. Both transports carry
semantically equivalent terminal state.

**Rationale.** Phase 24.3's binding invariant (`handlers.py:1685-1687`
comment: *"the JSON and SSE paths emit semantically equivalent terminal
state"*). Choosing only one transport for preview means a
transport-class of clients sees no preview — direct Phase 24.3
violation. The easiest of the five rulings.

**Stage 1b carve-out for the plan.** Specify the exact JSON envelope
shape (field name, position relative to existing `messages` /
`stop_reason` / `request_id`) AND the exact SSE event shape (event
name, `data:` payload structure) BEFORE implementation. Deciding
during implementation is a `[[feedback-grep-c-completion-invariant]]`
catch shape.

### R-A1.4 — Insertion point: REPLACE complete_with_tools call site

**Ruling (DT):** Option (a). Compile sits after all existing preamble,
replacing the `router.complete_with_tools(...)` call site at
`handlers.py:1712` with `router.compile_intent(...)` →
`run_chain_steps(...)` (or preview-only short-circuit per R-A1.2).

**Rationale.**

- Option (b) (replace PR14 message-pre-filter) is architecturally
  seductive but operationally wrong. PR14's `filter_tools_by_message`
  at `handlers.py:1529` is upstream of EVERYTHING that talks to the
  model — executor today, compiler tomorrow. PR14 narrows the tool
  space the model sees to reduce paralysis per
  `[[feedback-pre-orchestration-resolution-paralysis]]`. Removing
  PR14 because "compile produces tool selection" forgets that compile
  IS the LLM call that needs PR14's narrowing.
- Option (c) (before all preamble) reorders compile above PR30's
  `->`-chain dispatch (line 1486) and the macros short-circuits
  (`1427-1462`), which are exec-lens deterministic paths — framing
  explicitly says *"Thread A does not modify exec."* Compile must sit
  BELOW the deterministic short-circuits and ABOVE the LLM dispatch.
- Option (a): the LLM-bound call site only.

**Stage 1b carve-outs for the plan (DT-flagged, must be explicit
before implementation):**

1. **PR15 system prompt disposition.**
   `build_enforcement_system_prompt(router.system_prompt, tools_filtered_count)`
   at `handlers.py:1604` is built FOR the executor's tool-call
   enforcement. Compile needs its own system prompt — either
   `compile_intent` takes an override and the handler passes a
   compile-specific one, OR `compile_intent` hardcodes a compile
   system prompt that does NOT inherit PR15's enforcement language.
   Plan must rule which.

2. **PR20 forced-execute disposition.** Lines `1623-1640`: when the
   deterministic narrow collapses to a single tool, today this
   short-circuits to direct tool invocation, bypassing the LLM.
   Under Thread A: does PR20 stay a pre-compile shortcut (no
   graph-intent emitted; direct tool call), OR does it route
   through a "degenerate compile" (one-step graph-intent →
   `run_chain_steps`)? Either is defensible;
   `[[feedback-substrate-before-consumer-landing]]` suggests
   substrate works either way — but the room must rule explicitly
   or implementation-time discretion will choose, and Stage 1b will
   catch it.

3. **SSE/JSON branch integration.** The current branch at
   `handlers.py:1687` splits to `_chat_sse_response` (which calls
   `complete_with_tools`) and the JSON path (which also calls
   `complete_with_tools` at line 1712). BOTH paths must integrate
   with `compile → preview → run_chain_steps`. Non-trivial
   dual-transport plumbing; needs explicit handoff structure in
   the plan.

### R-A1.5 — Phase 24.4 terminal taxa: RE-HOMED at chat-handler level

**Ruling (DT):** Option (c). Phase 24.4's three taxa (`done` /
`orchestration_terminated` / `error`) stay untouched in
`complete_with_tools` (`router.py:988`, `:1018`). Chat's SSE path
under A.1 emits a NEW taxa family at the chat-handler level:

| New chat-side taxon | Fires when |
|---|---|
| `compile_complete` | graph-intent produced from `compile_intent` |
| `preview_emitted` | preview surface emitted (per R-A1.2 short-circuit or pre-A.2 stub) |
| `chain_complete` | `run_chain_steps` finished cleanly (zero commit nodes path) |
| `chain_aborted` | step failed mid-chain |
| `compile_error` | `CompileError` raised |

The `error` taxon name is the only carry-forward — transport/runtime
errors don't change shape under Thread A.

**Rationale.** Phase 24.4 anti-scope §10 binding (*"no orchestrator-side
synthesis, no system message changes, no prompt shaping, no result-hash
normalization, no cross-provider reach"*) is honored BY NOT MODIFYING
`complete_with_tools`. The K=2 trigger and its taxa describe the
EXECUTOR's terminal states. Under A.1, chat no longer calls the
executor for the inferential path — the trigger doesn't fire FROM
CHAT, but the executor's emission code stays intact for any other
caller. Chat's SSE taxa family becomes additive at the chat surface,
not a rename of router-side taxa.

These are different surfaces with different terminal-state semantics —
`[[feedback-description-layer-multi-register-surface]]` shape: distinct
registers reach distinct behaviors.

- Option (a) "retired in chat" is misleading — the taxa aren't retired,
  they just don't fire from chat anymore because the dispatch shape
  changed.
- Option (b) "additive — terminal taxa expand" implies both families
  fire together; they don't, because chat's path no longer reaches
  `complete_with_tools`.
- Option (c) names what actually happens.

**Stage 1b carve-out.** The plan must specify the exact wire-shape of
the new chat-side taxa (event name, `data:` payload schema for each) —
same discipline as R-A1.3.

## Forward-looking caveats for the plan drafter

DT-flagged. Not blocking the rulings; ammo for Stage 1b and the spec.

**FC-1. Substrate-coherence-revealed-in-retrospect candidate.**
Post-A.1, both lenses produce `list[str]` chain-step text: PR30's
`->`-parse (exact-compile) and Thread A's `compile_intent`
(inferential-compile). `run_chain_steps` becomes the **single
dispatch substrate** for both.
`[[feedback-substrate-coherence-revealed-retrospect]]` shape — worth
flagging in the plan as a Phase 24-style "revealed by retrospect"
claim, not an A.1 design choice. The substrate convergence is real
but not engineered.

**FC-2. Compile system prompt + warm-KV-cache shape.**
`compile_intent` under `sensitive=True` (Ollama local) warms a NEW
cache prefix (different system prompt + different message envelope
shape than `complete_with_tools`'). First A.1 chat invocations on a
freshly-restarted daemon will be cold per-prefix. Not blocking;
worth a one-line note + a Phase-24.1-style `ollama-turn` log-line
extension to make it observable per
`[[feedback-provenance-precedes-behavioral-interpretation]]`.

**FC-3. Preview shape: minimum vs operator-useful.**
Minimum is `list[str]` chain-step text. Operator-useful is probably:
`list[{step_text, tool_name, args_preview, would_mutate}]` (would_mutate
flagging maps directly to R-A1.2's commit-node detection). Preview is
the artist-facing surface; UX-philosophy memory applies per
`[[project-forge-bridge-ux-philosophy]]`. Plan must specify the
preview's exact dict shape — operator will dogfood this and a sparse
list-of-strings preview will fail UAT.

**FC-4. CompileError taxon completeness.**
Framing Gap #1 names "seam-violation-at-compile-time as a first-class
taxon" but doesn't enumerate the family. Plan must enumerate the
CompileError sub-types. Candidates:

| CompileError sub-type | Fires when |
|---|---|
| `compile_unresolvable_intent` | LLM produced no recognizable graph-intent |
| `compile_invalid_chain_shape` | output couldn't parse to `list[str]` chain steps |
| `compile_seam_violation` | (hypothetical / future) compile produced host-mutation without commit node — currently substrate-impossible per R-A1.2, but the taxon should exist as architectural anchor |
| `compile_tool_unknown` | graph-intent references a tool name not in the registered set |
| `compile_budget_exceeded` | compile LLM call exceeded its wall-clock budget |

Sweep-completeness at spec time, not at implementation time, per
`[[feedback-grep-c-completion-invariant]]`.

**FC-5. A.2 check-location: AT the commit node, not pre-execute gate.**
For the A.2 framing drafter. The compile->preview->ratify->apply
sequence is right; the check-location matters. Per Q5 + commit.py
topology, the flow is:

`compile_intent -> preview (stable preview-id) -> operator-CLI assent
(writes substrate record against preview-id) -> run_chain_steps
invoked -> assent check happens AT THE COMMIT NODE inside
run_chain_steps`

The assent check lives AT the primitive, not in front of it. Phase
N+'s enforcement-via-composition lineage (which Q3 explicitly cites)
demands the interlock live at the substrate, not as a pre-execute
policy gate. Not blocking A.1; ammo for A.2 framing drafter.

## Stage 1b carve-outs aggregated

The plan must rule explicitly on these before implementation handoff:

1. **R-A1.3** — exact JSON envelope shape + SSE event payload shape
2. **R-A1.4 carve-out 1** — PR15 system prompt disposition (compile-specific override vs hardcoded)
3. **R-A1.4 carve-out 2** — PR20 forced-execute disposition (pre-compile shortcut vs degenerate compile)
4. **R-A1.4 carve-out 3** — SSE/JSON branch dual-transport plumbing
5. **R-A1.5** — exact wire-shape of new chat-side taxa
6. **FC-3** — preview dict shape
7. **FC-4** — CompileError sub-type enumeration
8. **PR14 semantic-role-shift note.** A.1-PLAN's "preamble preservation"
   section must include a one-line note: PR14's code is byte-equivalent
   post-A.1, but its semantic role shifts upstream by one stage. Pre-A.1:
   executor input narrowing (LLM picks tool calls from narrowed space).
   Post-A.1: compiler input narrowing (LLM composes graph from narrowed
   space). Both reduce paralysis per
   `[[feedback-pre-orchestration-resolution-paralysis]]`; the load-bearing
   surface moves. Heads off a Stage 1b catch of "PR14 looks the same but
   means something different now."

## What A.1's plan derives from this

When operator ratifies the five rulings:

- `compile_intent` method on `LLMRouter` — text-completion path, distinct from `complete_with_tools`
- New `CompileError` family in `forge_bridge/llm/` (sibling to `LLMToolError` family)
- Commit-node presence classifier — substrate utility that walks compiled graph-intent
- Preview surface — JSON envelope field + SSE `graph_intent_preview` event taxon
- Insertion point — replaces `complete_with_tools` call at `handlers.py:1712`, preserves all preamble
- New chat-side terminal taxa family (5 events)
- `run_chain_steps` integration for zero-commit-node graphs
- Preview-only short-circuit for graphs with commit nodes
- PR15 / PR20 / SSE-JSON disposition rulings from the Stage 1b carve-outs

A.1's plan opens against these contracts. Stage 1b reviews against them.

## Status

**Room-converged, awaiting operator ratification.** Creative provided
the architectural transition framing (NL → compile → canonical graph →
execution substrate → host); DT provided five grounded rulings + Stage
1b carve-outs + four forward-looking caveats. The two seats converged
without active disagreement; rulings flow from the architectural framing.

Once operator ratifies: A.1-PLAN.md drafts in code-handoff format
against R-A1.1..R-A1.5 + FC-1..FC-4 + Stage 1b carve-outs, then goes
to Stage 1b review before implementation handoff.
