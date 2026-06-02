---
adr: 0001
title: Chat mutations delegate to forge-pipeline executors behind the v1.7 ratify chain (Door C)
status: draft — pending DT review (3 constraints, #3 central) + room
date: 2026-06-01
deciders: writing-room (DT grounding / Creative experience / Orch synthesis) + operator
context_phase: Phase 26 (staged-operation golden path) — 26-04 held as documented gap behind this ADR
supersedes_premise: the spike's original assumption that a `_tool_filter` "prefer proposers" patch would route chat into staged-ops
grounding: live reads 2026-06-01 — _chat_compile.py:299-307 (run_apply_branch → run_chain_steps(steps=record.chain_steps, assent_record=record)) + :308-327 (PLAN_STATE_DRIFT handling, mark_failed/applied); _step.py:415 (ratified_replay exemption); mcp.call_tool resolves against the full registered tool surface incl. consumer tools (same register_tools path proposers use); graph/commit.py:99-137 (CommitVerification.verify(held, fresh) — held vs freshly-recomputed MutationManifest.resolved_plan, item-by-item → PLAN_STATE_DRIFT); graph/mutation.py (MutationManifest)
---

# ADR-0001 — Chat mutations delegate to forge-pipeline executors behind the v1.7 ratify chain

## Context

Two distinct mutation-governance systems exist:

1. **Forge-bridge chat governance (v1.7):** NL mutating intent → compile → preview →
   `AssentRecord` → ratify → **verified replay** → executor → mutation.
2. **Staged-operation governance (consumer):** `forge_stage_*` proposer creates a
   `staged_operation` → bridge approval surface persists/approves/rejects → consumer
   executes after approval.

The Phase 26 golden-path test drives **surface 1** (NL chat) and expects **surface 2's**
artifact (a `staged_operation`). The spike read this as "route chat to proposers"
(a `_tool_filter` patch). That premise is **invalidated**:

- A routing patch presupposes chat *should* enter staged-ops governance — an unmade
  architectural decision — and would create a **second authority path** (Door A).
- `forge_stage_*` are consumer mutating tools; pre-ratify, DI.1's fail-closed gate
  blocks them — "prefer proposer" just **moves the block** (this is also why the live
  rename attempts "aborted before execution": DI.1 blocking bare `flame_rename_shots`
  pre-ratify, not merely routing).
- Most importantly, **apply already delegates.** `run_apply_branch` replays the
  persisted chain through `mcp.call_tool` against the *full registered tool surface*
  (including consumer/forge-pipeline tools) under the `ratified_replay` exemption. The
  v1.7 chain owns **authority + orchestration + replay + drift-verification**; the
  **executor is already pluggable.** Execution is delegated through the shared dispatch
  substrate today.

So the question is not *"should staged-ops become a chat door?"* but *"can staged-ops
(and forge-pipeline executors generally) become the **executor** behind the existing
chat door?"* — radically different questions.

## Decision

**Door C.** Forge-pipeline executors — including staged-ops proposers/listener — become
**executors behind the v1.7 ratify chain**, dispatched via the shared substrate at
apply-time. **One authority chain:**

> Intent → Compile → Preview → `AssentRecord` → Ratify → **Verified Replay** →
> Executor → Mutation

- **Reject Door A** (staged-ops as a second chat door): it splits the governance model —
  an artist would acquire mutation authority via *either* `AssentRecord` *or*
  staged-operation creation. One authority chain, not two.
- **Door B is the special case of C** where the executor happens to be a bridge-owned
  `flame_*` tool (e.g. rename → `flame_rename_shots`, replayed directly). B suffices for
  mutations forge-bridge already ships; **C is required** for mutations it does not
  (publish → forge-pipeline executors). The Phase 26 golden path is mixed
  (rename = B-able, publish = C-needing), so **C is the general answer** and **subsumes
  B**; adopt **C-with-B-as-special-case**.

The integration point becomes *explicit* instead of accidental: **bridge keeps the
authority model; pipeline keeps the execution machinery**; neither throws away what it
built.

## The seam (grounded — no new apply architecture)

`run_apply_branch` (`_chat_compile.py:299-307`) → `run_chain_steps(steps=record.chain_steps,
assent_record=record)` → `mcp.call_tool(tool_name, params)`. `mcp.call_tool` resolves
against the full registered tool surface (consumer tools included). The ratified
`assent_record` exempts the chain's mutation steps from DI.1 at `_step.py:415`. **Apply
already dispatches whatever tool the chain step names.** The seam is the dispatch
substrate; it exists and is general today.

## The work relocates to compile→preview (not apply)

Apply already delegates. What C requires is upstream: **the mutating chat intent must
compile to a commit-bearing chain whose apply-step targets the forge-pipeline executor**,
so it (a) reaches `run_compile_branch`'s **preview** branch (commit token → `AssentRecord`,
stored + ratifiable) rather than the forced/direct-dispatch path DI.1 blocks pre-ratify,
and (b) on ratify, replays into the executor under the exemption. Today "rename" compiles
to a *bare* `flame_rename_shots` (no commit token) → direct dispatch → DI.1 block. **The
routing question relocates to inside the ratify chain as the apply-target** — never as a
second authority door. That is exactly why C preserves DI.1: the executor is a replay
target under ratified assent, not a competing entry.

## Constraints the ADR must nail

### C1 vs C2 — executor reachability (name the variant)

The apply-step must be an MCP tool the replay can dispatch via `mcp.call_tool`:

- **C1 — direct executor tool.** forge-pipeline registers an apply-executor tool; apply
  replays it directly.
- **C2 — proposer-as-executor.** apply replays the proposer (`forge_stage_rename`), which
  creates the `staged_operation`, and the listener applies. C2 is what "proposers/listener
  become the apply mechanism" implies — **but it requires the staged-ops approval
  lifecycle to collapse into bookkeeping under the `AssentRecord`** (the `staged_operation`
  auto-executes because assent already authorized it). Otherwise you have **two approval
  gates** (ratify *and* staged-approval) for one intent.

*Both ride the seam; they have different lifecycle implications.* **OPEN — the room/ADR
must pick.** (Lean: C1 for bridge-shippable mutations; C2 only if the consumer wants the
staged-operation record as a durable artifact, with the approval gate explicitly
collapsed.)

### Compile must emit a commit-bearing executor chain

The real implementation work. Compile/preview must produce a *stored* chain whose mutation
step is **executor + commit token**, so it is previewed and ratifiable rather than
direct-dispatched and DI.1-blocked.

### Drift-manifest participation — THE CENTRAL QUESTION (authority-integrity crux)

Apply is **not** a blind replay. During replay the commit node runs
`CommitVerification.verify(held, fresh)` (`commit.py:99-137`) — comparing the **held**
(previewed) `MutationManifest.resolved_plan` against a **freshly recomputed** one,
item-by-item, aborting on `PLAN_STATE_DRIFT` (`_chat_compile.py:308-327`). That is the
actual authority-integrity property: *the ratified plan still matches fresh state at the
moment of apply.*

**If a delegated forge-pipeline executor applies its mutation outside the
manifest-recomputable plan, the audit (`AssentRecord`) survives but the drift guarantee
is lost** — ratified plan → drift-verified → delegated elsewhere → a different thing
happens. The ADR's central question, which DT will treat as the review crux:

> **How does a delegated executor's effect participate in commit-manifest verification?**
> The executor's planned mutation must be expressible as a `MutationManifest.resolved_plan`
> the commit node can **recompute fresh and compare** at apply-time. If it cannot, C
> silently weakens the very invariant it preserves.

This — not routing, not apply, not authority (all already solved) — is the unsolved
problem C must answer.

## DI.1 interaction

`forge_stage_*` / forge-pipeline executors registered without explicit `readOnlyHint`
default to mutating (correct). Under C this is fine and desired: they are **blocked
pre-ratify** (no direct chat door) and **execute only via ratified replay** under the
`_step.py:415` exemption. C does not require annotating them as reads; it requires they
be reachable *only* through the ratify chain.

## Consequences

- One authority chain; one audit trail; the substrate/consumer split respected.
- 26-04 is **held as a documented gap behind this ADR** — not marked complete against the
  premise the spike invalidated. Wave 1 remains valid downstream work; Wave 2 live
  golden-path verification is blocked at the *governance entrypoint*, not the staged-op
  substrate (which the spike did not exercise and must not be called broken).
- Phase 26's open governance questions resolve: chat does **not** get a second door;
  staged-ops becomes an executor behind ratify (C); direct proposer MCP invocation
  remains valid for *testing the staged-ops lifecycle in isolation* (surface 2 on its
  own).

## Open questions (for DT review + the room)

1. **#3 manifest participation (central):** the mechanism by which a delegated executor's
   effect is recomputable into a fresh `MutationManifest`. **Blocks C.**
2. **C1 vs C2:** direct executor tool vs proposer-as-executor (with approval-gate
   collapse). Different lifecycle.
3. **Drift recompute for consumer executors:** can the commit node recompute fresh state
   for a forge-pipeline mutation (e.g. publish) the way it does for `flame_*` renames?
4. Does C2's "collapse staged-approval into AssentRecord bookkeeping" weaken the consumer's
   own approval semantics, or is the staged_operation purely a durable record under C2?

## Status

**Draft, 2026-06-01.** Door C ratified in principle by the room (reject A; C subsumes B);
seam grounded (dispatch substrate, no new apply architecture); work relocated to
compile-emitting-a-commit-bearing-executor-chain. **The decision is contingent on
answering #3 (manifest participation)** — DT to review against the three constraints with
#3 as the crux. 26-04 held as a gap pending this ADR.
