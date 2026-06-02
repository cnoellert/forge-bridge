---
adr: 0001
title: Chat mutations delegate to forge-pipeline executors behind the v1.7 ratify chain (Door C) — BRIDGE-SIDE COMPANION
status: companion → defers to forge-pipeline ADR-003; constraint #3 CLOSED (grounded); ADR-003 → Accepted on two edits
date: 2026-06-01
authoritative_record: /Users/cnoellert/GitHub/forge-pipeline/docs/architecture/ADR-003-CHAT-MUTATION-AUTHORITY.md
deciders: forge-pipeline maintainers + forge-bridge writing-room (DT / Creative / Orch) + operator
grounding: _step.py:745-869 (commit-node execution — apply_counterpart dispatch :792-793, mode=verify recompute :803-810, CommitNode().verify held-vs-fresh :838, mode=apply :859-866, SYNCHRONOUS verify→apply) · graph/commit.py:99-137 (CommitVerification item-equality on resolved_plan) · graph/mutation.py (MutationManifest / apply_counterpart / ChangeRecord) · _chat_compile.py:299-327 (run_apply_branch / drift handling) · _step.py:415 (ratified_replay exemption)
---

# ADR-0001 (bridge-side companion) — Chat-mutation executor delegation, Door C

> **Authoritative cross-team decision: forge-pipeline ADR-003.** This bridge-side note
> tracks the forge-bridge half and records the grounding that **closed constraint #3**.
> Where they differ, ADR-003 wins.

## Decision (summary; full text in ADR-003)

**Door C** — forge-pipeline executors (incl. `staged_operations`) become **apply-executors
behind the v1.7 AssentRecord ratify chain**, not a competing chat door. One authority
chain: `Intent → Compile → Preview → AssentRecord → Ratify → Verified Replay → Executor →
Mutation`. Reject Door A (second authority path / DI.1 violation). Door B = the special
case where the executor is a bridge-owned `flame_*` tool; **C subsumes B**.

**C1 is REQUIRED (not merely recommended); C2 is integrity-incompatible for the chat apply
path.** (Grounded below.)

## Constraint #3 — CLOSED (the gating question, grounded by DT's commit-node read)

**The manifest-participation interface already exists and is fully generic** — like the
Q-DI1 finding (`readOnlyHint`), the interface the milestone feared it had to build already
ships. The commit node (`_step.py:745-869`) is generic over the `MutationManifest`
contract, zero flame-specific knowledge:

1. prior step result = a validated `MutationManifest` (`:772`) — `resolved_plan`
   (ChangeRecords) + `intent_parameters` + `apply_counterpart: {tool, parameter_overrides}`.
2. commit dispatches `target_tool = manifest.apply_counterpart["tool"]` (`:792`), requiring
   it declared in the surface (`:793`, else `APPLY_COUNTERPART_NOT_DECLARED`).
3. **verify (fresh):** `mcp.call_tool(target_tool, {…, mode:"verify", resolved_plan})`
   (`:803-810`) → the executor **recomputes a fresh manifest from current state.**
4. `CommitNode().verify(held, fresh, assent)` (`:838`) → drift check (item-equality on
   `resolved_plan`) → `PLAN_STATE_DRIFT` on mismatch.
5. on match + ratified assent: **apply:** `mcp.call_tool(target_tool, {…, mode:"apply", …})`
   (`:859-866`).

So 3b's "manifest-contribution surface" **is the existing contract**, and it is the only
way the commit flow works for *any* tool — `flame_rename_shots` is one implementor
(Phase 25.0 dry_run/mode pattern). **My earlier "recomputable-fresh" criterion is literally
the `mode="verify"` recompute (`:803-810`)** — satisfied by construction, not a new
requirement.

**Where the integrity actually lives (the one design requirement):** drift detection is
item-equality on `resolved_plan`, so **`ChangeRecord` granularity must be fine enough that
a relevant state change makes `fresh != held`.** Coarse/opaque records silently weaken the
guard. This is the thing to review on the executor's manifest contract.

## C1 required / C2 integrity-incompatible (grounded)

`verify` (`:838`) and `apply` (`:866`) happen **synchronously within one commit call** — no
gap. **C2's listener applies the mutation asynchronously** (`staged.approved` →
`staged_listener.py`), *outside* that envelope: the drift check runs at commit time but the
host mutation happens later, reopening exactly the drift window the commit node exists to
close, with nothing re-checking. C2 keeps the `AssentRecord` audit but **loses the
"ratified plan still matches fresh state at apply" guarantee** — the precise invariant C
exists to preserve. Making C2 safe would require re-running the full manifest verify inside
the listener, duplicating the commit node and defeating the delegation. **Therefore C1 is
required by constraint 3; C2 is integrity-incompatible as the chat apply mechanism** (C2 is
fine only where a `staged_operation` row is independently valuable as pipeline state
recorded *alongside* a C1 apply).

## Deliverables (narrowed by the #3 closure)

- **forge-bridge — ONE change:** `compile_intent()` emits a **commit-bearing executor
  chain** (constraint 2) — the mutating intent compiles to a stored chain whose mutation
  step is `<executor> + commit`, reaching preview/`AssentRecord` instead of the
  DI.1-blocked direct dispatch. *No new manifest machinery* — the commit node already
  consumes any `apply_counterpart` tool generically.
- **forge-pipeline:** ship a **manifest-participating apply-executor MCP tool** implementing
  the 3-mode protocol (discover/preview → `MutationManifest`; `mode=verify` → recompute
  `resolved_plan` from current state; `mode=apply` → apply synchronously), reference
  `flame_rename_shots`. **C1.** ChangeRecord granularity is the integrity locus.
- then **re-spec 26-04 E2E against the ratify chain and re-run** (gap-closure plan).

## Two edits that move ADR-003 Proposed → Accepted (for the pipeline team / DT)

1. **Reframe #3:** the manifest-participation interface already exists and is generic
   (`_step.py:792-866`); 3b = the consumer implementing the existing 3-mode `MutationManifest`
   protocol (reference `flame_rename_shots`), **not** a new forge-bridge surface.
   forge-bridge's only change is constraint 2.
2. **Upgrade C1 from "recommended" to "required by constraint 3"**, and record **C2 as
   integrity-incompatible** for the chat apply path (async listener outside the synchronous
   `verify→apply` envelope), not merely double-gated.

## Status

**Companion; constraint #3 CLOSED (grounded).** ADR-003 goes to **Accepted** on the two
edits above; #3 lands in forge-pipeline's court (ship the 3-mode executor, C1). DT to
review the executor's manifest contract once forge-pipeline drafts it (ChangeRecord
granularity = where integrity lives). forge-bridge work = `compile_intent()` commit-bearing
chain (constraint 2), verified by the re-spec'd 26-04. 26-04 held as a gap meanwhile.
