---
adr: 0001
title: Chat mutations delegate to forge-pipeline executors behind the v1.7 ratify chain (Door C) — BRIDGE-SIDE COMPANION
status: companion → defers to forge-pipeline ADR-003 (authoritative, cross-team)
date: 2026-06-01
authoritative_record: /Users/cnoellert/GitHub/forge-pipeline/docs/architecture/ADR-003-CHAT-MUTATION-AUTHORITY.md
deciders: forge-pipeline maintainers + forge-bridge writing-room (DT / Creative / Orch) + operator
grounding: _chat_compile.py:299-327 (run_apply_branch / drift handling) · _step.py:415 (ratified_replay exemption) · graph/commit.py:99-137 (CommitVerification.verify held-vs-fresh) · graph/mutation.py (MutationManifest)
---

# ADR-0001 (bridge-side companion) — Chat-mutation executor delegation, Door C

> **The authoritative cross-team decision is forge-pipeline ADR-003**
> (`Chat Mutation Authority — staged_operations as an Apply-Executor Behind the Ratify
> Chain`). This bridge-side note exists so forge-bridge contributors find the decision
> from their own repo and so the **forge-bridge deliverables** are tracked here. It does
> NOT restate or compete with ADR-003; where they differ, **ADR-003 wins.**
>
> This companion was drafted independently the same day and converged on the identical
> decision (Door C; reject A; B⊂C; work in compile→preview; #3 manifest-participation as
> the crux) — recorded as corroboration, then reduced to a pointer when ADR-003 (the more
> complete version, with the 3a/3b/3c decomposition + C1 recommendation) landed.

## Decision (summary; full text in ADR-003)

**Door C** — forge-pipeline executors (incl. `staged_operations`) become **apply-executors
behind the v1.7 AssentRecord ratify chain**, not a competing chat door. One authority
chain: `Intent → Compile → Preview → AssentRecord → Ratify → Verified Replay → Executor →
Mutation`. Reject Door A (second authority path / DI.1 violation). Door B = the special
case where the executor is a bridge-owned `flame_*` tool; **C subsumes B**. ADR-003
recommends **C1** (direct executor tool, single approval gate) over C2 (proposer-as-executor,
which requires collapsing staged-approval into AssentRecord bookkeeping).

## Forge-bridge deliverables (this repo's half)

1. **`compile_intent()` emits a commit-bearing executor chain** (ADR-003 constraint 2) —
   a mutating intent compiles to a stored chain whose mutation step is `<executor> +
   commit`, so it reaches `run_compile_branch`'s preview branch (→ `AssentRecord`,
   ratifiable) instead of the bare direct-dispatch path DI.1 blocks pre-ratify.
2. **The commit node consumes the executor's manifest contribution** (ADR-003 constraint
   3 / option 3b) — `CommitVerification` must include the delegated executor's effect in
   the held-vs-fresh `MutationManifest` comparison.

## Bridge-side grounding note on #3 (for DT's review — the load-bearing detail)

ADR-003's 3b (executor exposes a manifest contribution the commit node folds into
`CommitVerification`) only preserves the integrity guarantee **if the contribution is
RECOMPUTABLE FRESH at apply, not a frozen declaration carried from preview.** The drift
guarantee is `CommitVerification.verify(held, fresh)` — a comparison of the **held**
(preview-time) manifest against a **freshly recomputed** one (`commit.py:99-137`). If the
forge-pipeline executor merely *declares* "I will touch entities X/Y/Z" once at preview and
that declaration is replayed verbatim, the **fresh** half is hollow — drift on the
delegated entities would not be detected. So 3b's real requirement on the bridge side:
**the executor's manifest contribution must be a recomputable function of current state**
(the commit node can re-derive the delegated effect's manifest from fresh state at apply
and compare to held), not a static snapshot. Otherwise C keeps the `AssentRecord` audit but
silently degrades to 3c (narrowed guarantee). This is the bridge-side acceptance criterion
for #3.

## Status

**Companion, deferring to forge-pipeline ADR-003 (Proposed).** Next: DT reviews ADR-003
against constraints 1–3 (#3 central; the recomputable-fresh requirement above is the
bridge-side test). On ratification → pipeline registers the manifest-participating
apply-executor tool(s); bridge ships deliverables 1 + 2; 26-04 E2E re-spec'd against the
ratify chain and re-run as a gap-closure plan. 26-04 held as a documented gap meanwhile.
