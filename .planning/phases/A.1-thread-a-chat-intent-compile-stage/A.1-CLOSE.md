---
milestone: v1.7
thread: A
phase: A.1
phase_name: Chat intent-compile stage — the compile + preview surface
status: closed
opened: 2026-05-27
closed: 2026-05-28
type: phase-close
derives_from: .planning/phases/A.1-thread-a-chat-intent-compile-stage/A.1-PLAN.md
implementation_arc: 4055e13..9b30773 (9 commits, D1..D5 substrate + 3 test-disposition closing moves + F-D3-1 grounded PR15 follow-up)
---

# A.1 — Phase close cursor

> **Chat now compiles before it executes.**
> NL → `compile_intent` → graph-intent (`list[str]` chain-step text) →
> preview-or-execute → host. The agentic-loop authority model is fully
> retired from the chat consumer; `complete_with_tools` remains a
> substrate primitive for non-chat callers. The inferential dispatch
> path can no longer bypass the seam exact dispatch already respects.
> A.2 closes the ratification loop at the commit node per FC-5.

## What shipped

**Nine commits in expected order** (D1..D5 substrate + three test-disposition
closing moves interleaved naturally + one grounded-PR15 follow-up after
Stage 1b BLOCK):

```
4055e13  feat(v1.7/A.1): add compile_intent substrate primitive
980e163  feat(v1.7/A.1): add commit-node graph classifier
9d9c863  feat(v1.7/A.1): add chat compile branch helper
e964127  feat(v1.7/A.1): wire chat JSON compile branch
76901ab  test(v1.7/A.1): retire orchestration-model contract tests; migrate handler-contract tests
37df842  feat(v1.7/A.1): wire chat SSE compile branch
f5b6137  test(v1.7/A.1): retire SSE orchestration-model contract tests; migrate transport-contract tests
c32d786  test(v1.7/A.1): add grounded PR15-omission test + fix sibling defect (F-D3-1)
9b30773  test(v1.7/A.1): retire history-handler authority-model contract tests
```

Concrete deliverables landed:

- **`LLMRouter.compile_intent(...)`** — text-completion primitive,
  single LLM call, S-3 Path b local guard against `_in_tool_loop`,
  routes via `_async_local`/`_async_cloud` directly (no `acomplete()`
  delegation per S-3). Returns `list[str]` chain-step text.
- **`CompileError` family — 1 base + 5 concrete taxa = 6 classes**
  (`CompileUnresolvableIntent` / `CompileInvalidChainShape` /
  `CompileToolUnknown` / `CompileSeamViolation` /
  `CompileBudgetExceeded`); placed sibling to `LLMToolError` block in
  `router.py`; mapped to HTTP 422 / 422 / 422 / 500 / 504; not
  exported.
- **`graph_contains_commit_node(steps)` substrate utility** in
  `forge_bridge/graph/commit.py`, folding over the existing
  `is_commit_step` primitive. Load-bearing for R-A1.2's preview-only
  classification.
- **`forge_bridge/console/_chat_compile.py` substrate-helper module**
  (4 exports: `CompileBranchOutcome` frozen dataclass +
  `build_compile_system_prompt` + `run_compile_branch` async +
  `build_preview_from_steps`). Single contract authority for the
  compile branch; called from both JSON and SSE chat paths.
- **JSON path integration** at `handlers.py:1674` —
  `run_compile_branch(...)` replaces `complete_with_tools` call site.
  JSON envelope reshaped to 4 regime-specific shapes
  (`compiled_non_mutating` / `compiled_mutating_preview` /
  `chain_aborted` / `compile_error`) per L9. `final_text` OMITTED
  from regime-2/3 per MOL-3 / B-1.
- **SSE path integration** at `_chat_sse_response:984` — same
  `run_compile_branch` call site; 5 new SSE event taxa
  (`compile_complete` intermediate + `chain_complete` /
  `preview_emitted` / `chain_aborted` / `compile_error` terminals).
  `event: error` transport-error taxon preserved unchanged per L9.
- **D6 telemetry distributed across D1/D4/D5**: `ollama-compile`
  structured log line in `compile_intent` body (D1); `chat_regime=`
  field added to JSON success log (D4) and SSE success log (D5)
  across all 4 regime values. No separate D6 commit needed; work
  absorbed naturally.
- **Authority-model retirement across 3 chat-test surfaces** via
  three test-disposition commits: 23 RETIRE + 14 MIGRATE = 37 tests
  dispositioned. Authority-model contract surface migrated cleanly
  from agentic-loop test files to
  `test_chat_compile_branch.py` (per R-4).
- **F-D3-1 grounded PR15-omission test + sibling defect fix** at
  c32d786, per Stage 1b BLOCK on conjectured forbidden vocabulary.
  Both tests now ground against `_tool_enforcement.py` PR15
  constants directly (Option B per Creative ruling).

**`forge_bridge.__all__` remains at 19** — byte-identical public API
invariant preserved across the v1.4.x → v1.6 → v1.7 arc. No new
exports introduced by A.1's compile / branch helper / classifier
surfaces.

**handlers.py grep-table closure** at end of D5 (held through
Commits A/B/C since they're tests-only):

| Identifier | Pre-A.1 sites | Post-A.1 sites |
|---|---|---|
| `complete_with_tools` | JSON :1712 + SSE :1025 | **0** |
| `_on_message` | :1018-1020 | **0** |
| `message_callback` | :1033 | **0** |
| `event: message` | :1019 | **0** |
| `event: done` | :1159-1168 | **0** |
| `_OrchestrationTerminated` | JSON :1797 + SSE :1109 | **0** |
| `_build_orchestration_terminated_body` | :889-950 | **0** |
| `enforced_system` | :1604 + threading | **0** |
| `is_response_text_malformed_tool` | JSON :1826 + SSE :1100 | **0** |

**9/9 forbidden identifiers at 0.** The deletion contract from
A.1-PLAN.md §"Stage 2 prompt" closed cleanly; the agentic-loop
authority model is gone from the consumer.

## Authority-model retirement cumulative

| Surface | Commit | RETIRE | MIGRATE | Final shape |
|---|---|---|---|---|
| JSON chat-handler (`test_chat_handler.py`) | `76901ab` | 14 | 11 | 55 tests / 100% |
| SSE chat-handler (`test_chat_handler_sse.py`) | `f5b6137` | 7 | 3 | 6 tests / 100% |
| History chat-handler (`test_chat_history_handler.py`) | `9b30773` | 2 | 0 | 1 test / 100% |
| Compile-branch (new authority surface) | D3+D4+D5+F-D3-1 | n/a | n/a | 28 tests / 100% |
| **A.1 chat-test surface total** | | **23** | **14** | **90 tests / 100%** |

**Architectural result:** 3 surfaces / 2 transports / 4 contract shapes
(response envelope / event taxa / top-level keys / cross-path symmetry)
converged onto 1 substrate helper (`_chat_compile.run_compile_branch`).
Authority-model agentic-loop contract fully retired from chat
consumer; preserved at router substrate (`complete_with_tools`) for
test consumers only.

Broader test surface at close: `pytest tests/llm tests/graph tests/console
→ 753 passed, 0 failed`.

## Gate-by-gate disposition

| Gate | Source | Status | Evidence |
|---|---|---|---|
| 1 — D7 tests pass | A.1-PLAN.md §Test plan #1 | ✓ | 107 tests across 6 files (12 D1 + 5 D2 + 28 compile-branch + 55 JSON + 6 SSE + 1 History) — 100% passing |
| 2 — Existing chat test suite passes unchanged | A.1-PLAN.md §Test plan #2 | ✓ with revision | Plan said "passes unchanged"; D4 reshape required test surface migration. Resolved via 3 supersession-marker test-disposition commits per writing-room rulings R-1+R-3+R-4. Architecturally honest: spec self-contradiction at §Test plan #2 was Stage 1b miss I should have caught at v3; writing-room rulings closed cleanly |
| 3 — `tests/llm/test_complete_with_tools.py` passes unchanged | §Test plan #3 | ✓ | Untouched per coexistence-architecture preservation at router substrate level |
| 4 — `tests/console/test_chat_history_handler.py` passes unchanged | §Test plan #4 | ✓ with revision | Same as Gate 2 — 2 RETIRE / 0 MIGRATE / 1 KEEP at `9b30773` |
| 5 — PR22 mechanical compliance | §Test plan #5 | ✓ | No new MCP tools registered; mechanical contract unchanged |
| 6 — `fbridge doctor` passes unchanged | §Test plan #6 | ✓ | No daemon-side surface changes; doctor row health preserved |
| 7 — Live smoke: regime-2 chain_complete | §Test plan #7 | deferred | UAT outside A.1 implementation scope; spec acknowledged S-2 prompt-wording iterability post-landing |
| 8 — Live smoke: regime-3 preview_emitted | §Test plan #8 | deferred | Same — operator UAT post-landing |
| Stage 2 prompt grep table | §"Stage 2 prompt" | ✓ | 9/9 forbidden identifiers at 0 in handlers.py post-D5; held through Commits A/B/C |
| `forge_bridge.__all__` at 19 | MOL-5 | ✓ | Confirmed unchanged |
| Cross-thread isolation | MOL-9 | ✓ | Thread C surfaces (`mcp/tools.py`, `mcp/registry.py`, `core/vocabulary.py`) untouched; phase-4b interleave (`store/*`) also confirmed zero contamination per DT broader sweeps |
| Doc plan — `docs/CHAT.md` | A.1-PLAN.md §Doc plan #1 | deferred | Anticipated as A.1 surface; not authored in this arc. Carry-forward |

## Discoveries

Eight findings worth archaeology beyond the standard close shape.

### D-1. Substrate-coherence-revealed-retrospect — 6 within-A.1 instances

`[[feedback-substrate-coherence-revealed-retrospect]]` fired at 6
distinct surfaces during the arc. None engineered at framing time;
all surfaced retroactively from implementation:

1. `ollama-compile` log line in D1 mirrors Phase 24.1 `ollama-turn`
   taxonomy without spec invocation — observability inheritance.
2. D1 output `list[str]` ↔ D2 input `list[str]` compose without
   adapter — type-shape coherence across independently-specified
   contracts.
3. D2's `is_commit_step` classifier becomes load-bearing for both
   graph-level (`graph_contains_commit_node`) and step-level
   (`build_preview_from_steps`) call shapes in D3 — single source
   of truth across two distinct call patterns.
4. D4's `enforced_system=build_enforcement_system_prompt(...)`
   inline-at-call-site bridging pattern — transitional structure
   spanning the D4→D5 intermediate; matures at D5 when the SSE
   kwarg deletes.
5. D6 telemetry distributed across D1+D4+D5 — work that the plan
   specified as a separate commit landed naturally alongside the
   logic that fires it. Substrate-coherence at the commit-shape
   level.
6. `run_compile_branch` dual-call-site (JSON :1674 + SSE :984) +
   shared `_compile_error_payload` helper — D3's substrate-helper-in-console
   architecture working as designed; JSON path (D4) and SSE path (D5)
   end up structurally near-identical at the call-site level.

**Within-phase density:** 6 instances under different surfaces in a
single implementation arc. The pattern is now well-validated at
distance — D1's helper, D2's classifier, D4's inline pattern, D6's
distribution all exhibited it independently.

### D-2. Failure-shape-stability as disposition discriminator — 3 within-A.1 instances under different test files → promotion-grade

`[[feedback-failure-shape-stability-as-disposition-evidence]]` fired
as the disposition discriminator three times within this arc:

| # | Surface | Failure count | Signature | Disposition |
|---|---|---|---|---|
| 1 | `test_chat_handler.py` JSON | 25 | `TypeError: object MagicMock can't be used in 'await' expression` | 14 RETIRE / 11 MIGRATE → `76901ab` |
| 2 | `test_chat_handler_sse.py` SSE | 10 | Same signature | 7 RETIRE / 3 MIGRATE → `f5b6137` |
| 3 | `test_chat_history_handler.py` | 2 | Same signature | 2 RETIRE / 0 MIGRATE → `9b30773` |

Same root cause (fixture mocked `complete_with_tools` not
`compile_intent`) under 3 different test files / 2 transports /
4 contract shapes. The discrimination principle (authority-model
retire / handler-contract migrate per 2a/2b/2c framework) applied
verbatim in all three commits. Each commit message names the third
within-A.1 instance explicitly.

**Promotion to full memory file ready at A.1 close.** The within-phase
multi-instance evidence under structurally-different test files
constitutes strong second-instance evidence beyond the original 24.7
H0 disposition promotion.

### D-3. Refinement of ground-specs-in-actual-files to negative-assertion layer → promotion-grade

`[[feedback-ground-specs-in-actual-files]]` extended at F-D3-1 dual
ratification (DT + Creative) 2026-05-28. Creative's formalization:

> *"forbidden assertions require the same grounding discipline as
> expected assertions. A negative contract built from inferred
> vocabulary is the same class of error as a positive contract built
> from inferred behavior."*

Two within-A.1 instances of the negative-assertion ungrounded defect:

1. F-D3-1 v1 directive: forbidden list ("HARD-TOOL", "primary
   modality", "deterministic enforcement", "force tool call",
   "hard-tool", "hard_tool_mode") — every term plausible PR15
   vocabulary, none actually present in `_tool_enforcement.py`
   emitted text. **Stage 1b BLOCK by DT.**
2. Sibling at `tests/llm/test_compile_intent.py:147`: identical
   defect — asserted `"HARD-TOOL" not in system_prompt`, ungrounded
   in the same way. **Sibling-check by DT.**

Both fixed in `c32d786` via Option B: import PR15 constants directly +
distinctive-fragment list (5 semantically PR15-unique phrases) +
whole-constant assertion on `PR15_HARD_TOOL_INSTRUCTION`.

**Promotion as refinement of existing memory** — extends grounding
discipline scope from "expected" to "negative" assertions; same
class, both layers.

### D-4. Stage 2 visibility-anchor pattern (my failure mode) — 4 within-A.1 instances → promotion-grade

The discipline gap on the writing-room side: anchoring Stage 2 scope
to the operator's named verification slice instead of running broader
sweep. DT caught the gap at every closing pass through the arc:

| # | Close moment | My anchor | DT's broader catch |
|---|---|---|---|
| 1 | D4 close | `test_chat_compile_branch.py` (18) | `test_chat_handler.py` — 25 failures |
| 2 | D5 close | Operator's 4-file slice (99) | `test_chat_handler_sse.py` — 10 failures |
| 3 | Commit A close | chat surfaces | Phase-4b interleave (3 commits in git log) |
| 4 | Commit B close | F-D3-1 named files (40) | `test_chat_history_handler.py` — 2 failures + 4th phase-4b commit |

**The pattern is structurally stable across 4 instances** within a
single arc. Same shape every time: I run Stage 2 against the named
slice; DT sweeps broader; DT catches the gap. The discipline IS
working as designed (writing room runs fast sweep; DT runs broader
verification) — but my DEFAULT scope is wrong. **Stage 2 should
default to broader sweep at every closing pass, not selectively.**

At Commit C, the operator's verification slice absorbed the
broader-sweep observation (explicit 4-file chat-test surface sweep).
Process feedback loop functioning as designed — see D-5.

**Promotion as new memory file (or extension of existing
leakage-watch discipline)** ready for A.1 close.

### D-5. Process loop: leakage-watch surfaces → writing-room ruling formalizes → operator lands — 3 within-A.1 instances

DT named this explicitly at Commit A archaeology. The loop fired
3 times within A.1:

| # | Surface caught at | Writing-room ruling formalized | Operator landing |
|---|---|---|---|
| 1 | Stage 2 fixture-mismatch (25 failures) | R-1/R-2/R-4 SSE disposition framework | `76901ab` JSON; later generalized at f5b6137 + 9b30773 |
| 2 | Stage 2 conjectured forbidden list BLOCK | R-3 F-D3-1 + dual DT+Creative ratification | `c32d786` |
| 3 | Stage 2 broader-sweep observation | Operator absorbed into Commit C verification cadence (explicit 4-file slice) | `9b30773` |

**Strong promotion candidate** — sibling to the dual-ratification
pattern (DT + Creative) that fired at F-D3-1. Process discipline
working as engineered: writing-room observations become structured
rulings before code lands; operator absorbs feedback into
subsequent verification cycles.

### D-6. Transitional-structure-naming — 2 within-A.1 instances

`[[feedback-transitional-structure-naming]]` fired twice during the
arc:

1. **D4 inline-at-call-site bridging** —
   `enforced_system=build_enforcement_system_prompt(...)` survived
   at `:1702` as an inline arg value (not a JSON-path local
   variable). Maturation condition: D5 deletes the SSE
   `enforced_system` kwarg. **Closed at D5 (9/9 grep table at 0).**
2. **Test-disposition defensive-mock pattern** —
   `mock_router.complete_with_tools = AsyncMock()` survived at
   :64 / :400 / :1317 in `test_chat_handler.py` post-disposition.
   Belt-and-suspenders fixture hygiene; will become moot post-D5
   because handler-side reachability to `complete_with_tools` is 0.
   **Effectively moot post-9b30773.**

Both instances exhibit the canonical pattern: name the larger
pattern (deletion contract closure / authority-model retirement) +
name the maturation condition (D5 substrate completion / full
handler-side reach to 0). The transitional structures were not
ornamental; they were genuine intermediate-state hygiene that the
next commit retired.

### D-7. Distinct-success-criteria-per-adjacent-layer at the spec-layer boundary

`[[feedback-distinct-success-criteria-per-adjacent-layer]]` fired in
a new domain (spec-layer adjacency, not implementation-layer
adjacency) at D3 close. I anchored my D3 Stage 2 to the D7 matrix
(11 D3-tagged rows) and flagged 2 "gaps." DT correctly reframed:
D-body acceptance bullets and D7 matrix are different spec
surfaces with different acceptance-gate timings (per-commit vs
phase-close). My over-strict anchor conflated them.

| Spec surface | Role | Acceptance gate timing |
|---|---|---|
| D-item §Acceptance bullets | Per-deliverable behavioral contract | Per-commit Stage 2 |
| D7 §Coverage matrix | A.1 close coverage instrument | A.1 phase-close |

Sibling instance to D-4 (Stage 2 anchored too narrowly) but at a
different scope (spec layers, not test surfaces). **The principle
is the same memory pattern reaching a new domain.**

### D-8. Phase-4b interleave — out of A.1 scope, archaeology only

5 phase-4b commits landed on `main` between A.1 commits during the
arc:

1. `1c9eb09` docs(phase-4b): design contract for forge-bridge
   orchestration graph + memory
2. `3e6a187` feat(phase-4b): migrations 0004+0005
3. `0f3c01e` feat(phase-4b): migrations 0006+0007+0008
4. `381860b` feat(phase-4b): ContentAddressedRepo base
5. `8dd97cd` feat(phase-4b): remaining DBOrch* models + repos

Co-author tags: 1c9eb09 with Claude Opus 4.7 (separate session),
3e6a187 + 0f3c01e with Cursor. Parallel-track operator-driven work
using different tooling. Architecturally orthogonal to A.1: store
layer (`forge_bridge/store/`), not chat path (`forge_bridge/console/`,
`forge_bridge/llm/`). DT's Stage 2 sweeps at D5 + Commit A + Commit C
confirmed 0 lines of contamination into A.1 surfaces. Worth recording
as archaeology because this is the first sustained instance of
multi-track tool-diverse parallel work landing on `main` during an
A.1-style arc without architectural coordination overhead.

## Methodology — candidate-memory ledger

**Three patterns at promotion-grade evidence ready for memory file:**

### Promotion-grade #1 — Failure-shape-stability as disposition discriminator

Pattern reaching 3 within-A.1 instances under different test files;
discrimination criterion structurally stable, not coincidentally
repeatable. Ready for full memory promotion as the operational
instrument that closed 3 disposition cycles cleanly.

### Promotion-grade #2 — Ground-specs-in-actual-files refinement to negative-assertion layer

Creative's formalization at F-D3-1 dual ratification. Extends
existing memory to cover negative assertions (forbidden lists,
absence assertions). Ready for refinement to the existing memory
body or sibling memory file.

### Promotion-grade #3 — Stage 2 visibility-anchor pattern

4 within-A.1 instances of my anchoring failure mode. Ready for new
memory file naming the discipline: *Stage 2 should default to broader
sweep at every closing pass; anchoring to operator's named slice
catches what's expected but misses what's relevant.*

### Carry as candidates

- **Process loop: leakage-watch surfaces → writing-room ruling
  formalizes → operator lands** — 3 within-A.1 instances. Sibling
  to dual-ratification (DT + Creative). Strong promotion candidate;
  hold pending second-arc evidence (or promote at A.1 close if
  within-phase instance density is judged sufficient).
- **Substrate-coherence density as phase-shape signal** — when
  independently-specified deliverables compose without engineering,
  prior substrate maturity is doing load-bearing work the current
  phase didn't have to name. A.1 generated 6 within-phase instances
  of substrate-coherence-revealed-retrospect; the density is itself
  a signal.
- **Handoff-edge closing-language discipline** — single near-miss
  this arc (D4 close "next motion" framing read like
  implementation-handoff drift). Caught in-flight by DT. Hold as
  candidate; pattern is consistent across two cursors (this one +
  Stage 1b landed earlier same day).
- **Test surface following architectural authority-model shift via
  supersession not deletion** — 3 within-A.1 instances. Commit
  messages name the supersession explicitly per 2c framework; same
  language pattern across all 3 dispositions.
- **Count-decomposition drift across reviewer seats** — DT counted
  9+6+1=16 commits ahead; I counted 9+5+2=16. Same total, different
  breakdown. Per `[[feedback-counts-are-archaeology-grade]]` — both
  total and breakdown load-bearing. Worth noting as a within-A.1
  archaeology observation.

## Closure records

- **Phase-close artifact this file.**
- **A.1 implementation arc cursor in memory store** —
  [[passoff-2026-05-28-v1-7-thread-a-a1-implementation-complete-writing-room-role]]
  preserves fresh implementation-arc context for future writing-room
  sessions before this close cursor's compression.
- **A.1-PLAN.md v3 + A.1-DISCUSS-QUESTIONS.md ratified state**
  remain on disk under the phase directory as the spec-of-record
  for archaeology.
- **No `docs/CHAT.md` landed in this arc.** Anticipated as A.1
  surface per plan §Doc plan; deferred. Carry-forward to A.2 or
  a dedicated docs commit.
- **No `pyproject.toml` version bump.** A.1 is patch-equivalent
  additive surface inside v1.7's milestone arc; version remains
  `1.4.1` (per the v1.4.x baseline preserved through v1.5 + v1.6
  closes).

## Carried forward

### To A.2 framing

- **FC-5 from A.1 discuss artifact**: check-location AT the commit
  node, NOT pre-execute gate. A.1 stubbed the seam (R-A1.2
  preview-only short-circuit on commit-node presence); A.2 closes it
  with substrate-side ratify motion + `commit.verify()` extension
  for assent check + CLI ratify surface. The flow:
  `compile_intent → preview (stable preview-id) → operator-CLI assent
  → run_chain_steps invoked → assent check happens AT THE COMMIT
  NODE inside run_chain_steps`.
- **A.1 substrate primitives ready for A.2 consumption**:
  `compile_intent`, `graph_contains_commit_node`,
  `_chat_compile.run_compile_branch`, `CompileBranchOutcome` regime
  enumeration, `CompileError` family.
- **Preview shape locked at L4**: `kind` / `steps` /
  `summary{total_steps, mutating_steps, requires_ratification}`.
  A.2's ratify motion receives this dict shape.
- **Preview-id contract pending**: A.1 doesn't emit a stable
  preview-id (regime-3 preview is per-turn stateless). A.2 introduces
  the preview-id substrate (stable identifier; operator assent
  attached against it).

### Open within v1.7 Thread A

- **A.3 hardening** — surfaced once A.1/A.2 land.
- **Anti-scope §10 (24.4 framing)** binding continues across A.2 +
  A.3 — no orchestrator-side synthesis / no prompt shaping / no
  cross-provider reach. A.1 honored this throughout; A.2 inherits.

### Within-A.1 deferred items (not blocking close)

- **`docs/CHAT.md`** — A.1 surface per plan §Doc plan; not authored
  in this arc. Land as A.2 sibling commit or standalone docs commit.
- **Live operator UAT** — plan §Test plan #7 + #8 (chat smoke tests)
  deferred per S-2 prompt-wording iterability. UAT happens at
  operator's discretion; no A.1 acceptance dependency.

## Next motion

**A.2 — Ratification + enforced apply.** Substrate-side ratify motion
(operator assent recorded against preview artifact), `commit.verify()`
extended to check both drift validity AND assent validity, CLI
operator surface (`fbridge ratify <preview-id>` or similar). Per
THREAD-A-FRAMING.md §Phase decomposition:

> A.2 — ratification + enforced apply. The substrate ratify motion
> (assent as a substrate record on the preview artifact),
> commit.verify extended to check assent, the CLI ratify surface.
> The authority transition closes end-to-end.

A.2 framing opens against:
- A.1 substrate primitives (above)
- FC-5 check-location ruling at the commit node
- Preview shape L4 lock
- The architectural law inherited: substrate self-views are
  first-class operator surfaces — derived, not reconstructed.
  Ratification surface is derived substrate state per Q5.

## Status

**Closed.** v1.7 Thread A / Phase A.1 ships. Chat now compiles before
it executes; the agentic-loop authority model is fully retired from
the consumer; 90 chat-surface tests pass clean across 4 files /
2 transports / 1 canonical contract authority surface. The room
ratified the writing-room → spec v3 → Stage 1b → implementation arc
(D1..D5) → 3 test-disposition closing moves → F-D3-1 grounded
follow-up → close cadence across a single day-long cycle without
role-distinction violation across 11 within-day phase progressions.
