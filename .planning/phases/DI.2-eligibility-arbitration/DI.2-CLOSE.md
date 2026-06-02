---
milestone: v1.10
phase: DI.2
type: phase-close
status: closed-arbitration-shipped-verified-reachable-class-resolved
closed: 2026-06-01
honest_scope: "DI.2's eligibility-arbitration goal SHIPPED and is suite-proven + code-verified + live-confirmed: exact-name-wins exclusivity (T2), the leak→outcomes surface (T5), and the regression-lock (T6). The reachable resolver-overmatch class (R8/R9/R10) is ELIMINATED at the arbitration layer — verified live (forge_get_shot narrows to a single survivor). DI.2 does NOT make those reads ANSWER: they now abort one seam downstream at parameter resolution (forge_get_shot needs shot_id, derivable from 'shot 10' but unresolved) — explicitly out of scope. Measure-first held: T1 baseline sized the phase, T4 did NOT ship (no stable residual T2 can't reach), T3 minimal/empty. Creative's hidden-context audit returned Outcome A (the corpus does not fail because chat selects tools that can't answer) — DI.1/DI.2 scope confirmed; a dormant context-eligibility seam was named, not built. No artist UAT (carry-forward)."
verification: "suite 2679 passed / 41 skipped (+6 DI.2 acceptance tests); __all__==19; version 1.5.1; ruff clean; diff touches only _tool_filter.py (+3) and _step.py (+26/-6) — no T3/T4 surface built. Live (UAT/DI.2-live-verification.md, daemon @5b17c85): R8/R9/R10 post_pr14 → ['forge_get_shot'] single survivor, no tool_selection_ambiguous; downstream abort is params.shot_id (param seam). Acceptance test locks: exact read→one tool→executes; exact mutation→DI.1 unauthorized_mutation; ambiguous surface→outcomes, no identifier leak."
commits: "code feb4d47,bd7f8af,5b17c85,6113cf7,2fb40a4 (5); docs 45de65e..efbbee4 (framing), e1997c4..0abf377 (discuss), b006e32..5da59cc (plan+T1)"
---

# DI.2 — Close (eligibility arbitration shipped; reachable class resolved; scope confirmed by audit)

> DI.2 set out to make routing **resolve instead of hard-stop**. It does — for the
> reachable class. Exact-name-wins eliminates the resolver-overmatch that aborted
> R8/R9/R10, verified live (`forge_get_shot` → single survivor). The honest part:
> this is an **arbitration-layer** win, not "those reads now answer" — they block
> one seam down at parameter resolution, which DI.2 deliberately did not annex. And
> the hard-won part: Creative's hidden-context audit could have shown the whole
> corpus was contaminated by hidden Flame state and DI.2 was chasing the wrong
> problem. It didn't. It returned **Outcome A** — the system mostly fails on
> questions it should already be able to answer. The path is aimed right.

## What shipped (5 code commits)

Measure-first preserved — the baseline decided the scope, not the plan:

- **T2** exact-name-wins exclusivity (`feb4d47`) — `_tool_filter.py`: `if
  len(exact_matches) == 1: return exact_matches` before the cap-combine. Multi-exact
  still falls through. **Shared substrate** → benefits both the chain and direct paths.
- **T5** leak → outcomes (`bd7f8af`) — `_step.py`: the `tool_selection_ambiguous`
  message loses the tool count / verb-hint, `candidates:[names]` → `outcomes:` derived
  from tool **descriptions** (name stripped out, generic "another available result"
  fallback). No tool identifier reaches the human surface.
- **T6** acceptance-lock (`5b17c85`) + PR9 fixture update (`2fb40a4`) + live-verify
  caveat (`6113cf7`).
- **T3 minimal / T4 NOT shipped** — the T1 baseline's gate condition (a stable
  residual resolver-overmatch T2 can't reach) is **empty**; the acceptance test
  records the skip rationale in-code. The contingent rung was gated by data and
  correctly never built.

`__all__` == 19; version 1.5.1; diff contained to two files.

## The T1 baseline — the measurement that sized everything

`UAT/DI.2-baseline.md`: 33 samples (11 reads × 3, **distribution not replay** per the
stability clause), live post-DI.1 daemon `@82b9062`, `qwen2.5-coder:14b`, divergence
capture sanity-checked. **The framing's predicted split reproduced almost exactly:**

| Class | Reads | Count | % of 9 |
|---|---|---|---|
| (a) resolver-overmatch — **DI.2's class** | R8, R9, R10 | 3 | 33% |
| (b) bad-compile | R2, R5, R6, R11 | 4 | 44% |
| (c) other-seam | R3, R7 | 2 | 22% |

All 3 (a)-class reads compiled to the **bare step `forge_get_shot`** (unique
substring-exact) → T2 resolves the entire reachable class, 3/3 stable. **"≤3/9"
is corpus-confirmed, not ledger-grounded.** R2 was the lone stochastic read (2/3
malformed-compile) — the N=3 clause caught it; a single run would have mis-sized it.

## Verification (what's proven, and how)

- **Suite-proven:** 2679 passed / 41 skipped (+6 DI.2 acceptance tests).
- **Code-verified:** T2/T5 read off the diff match the locked spec; no T3/T4 surface exists.
- **Live-confirmed (`UAT/DI.2-live-verification.md`):** R8/R9/R10 no longer return
  `tool_selection_ambiguous` — `forge_get_shot` narrows to a single survivor.
- **Cross-phase invariant locked:** the acceptance test proves an exact **mutating**
  name still hits DI.1's gate (`unauthorized_mutation`) — **DI.2 did not weaken DI.1.**

## What this close does NOT claim

- **The 3/9 win is arbitration-layer, NOT "working reads."** R8/R9/R10 resolve to one
  tool, then **abort at parameter resolution** (`forge_get_shot` requires `shot_id`,
  derivable from "shot 10 on 30sec_edit 21" but unresolved). DI.2 removed the resolver
  wall and **revealed the parameter wall behind it** — the framing's "make chat useful
  = several milestones" confirmed a second time. The boundary held: DI.2 resisted
  annexing the param fix (the arbitration→compilation drift it exists to prevent).
- **No artist UAT** (carry-forward; struck for the milestone until the compile/param
  layer lands).

## The hidden-context audit (Creative's hypothesis — hard won) → Outcome A

**Hypothesis:** some failures may be the resolver selecting tools that require implicit
Flame context never available — i.e. the corpus accidentally grading *context-contract*
failures, not resolver failures.

**Method (grounded, no re-run):** for each failure, the *selected* tool's class
(`readOnlyHint`) + the question *"could this tool ever answer what was asked, from
prompt + accessible substrate?"*

| Read | Selected tool | Context-dependency | Could it answer? | Cause |
|---|---|---|---|---|
| R1 | flame_list_batch_groups | ctx-dep read (desktop, available) | yes (✓) | success |
| R2 | flame_list_desktop | ctx-dep read (available) | yes (run3 ✓) | compile-shape (malformed) |
| R3 | flame_list_desktop | ctx-dep read (available) | yes (right tool) | answer-pass (field mishandled) |
| R4 | flame_get_batch_reels | ctx-dep read (available) | yes (✓) | success |
| R5 | flame_list_batch_groups **+** flame_open_batch_group | read (had answer) **+ mutation** | step0 yes; mutation appended | compile **over-injection** |
| R6 | forge_get_batch_iterations **+** format_result | ctx-dep read (gen_0460) **+** utility | yes (got `6`) | compile over-injection (broken step) |
| R7 | — (none) | needs project ctx (unavailable) | n/a | missing-context (session scope) |
| R8/R9/R10 | forge_get_shot | ctx-dep read (`shot_id` derivable) | yes, if resolved | resolver-overmatch (DI.2 ✓) → param seam |
| R11 | flame_set_start_frames | **mutation** | **NO** (a setter can't report) | **eligibility — DI.1-owned** |

**Result: Outcome A.** Only **R11** is a clean eligibility failure (sole selected tool
categorically incapable) — and **DI.1 already owns it** (blocked). My earlier
"Outcome C / 2 eligibility cases" **overcounted**: R5's primary tool was a correct
read that *had the answer*; the mutation was an appended probe → R5 is compile
over-injection (a sibling of R6), not eligibility. Every other selected tool was
plausible, often correct, sometimes returned correct data — and the system still
failed. **Hidden context is not the dominant explanation for the observed failures.**

## The dormant seam (named, not built)

The audit's most valuable by-product is an architectural blind spot:

- DI.1 asks *"is this safe?"* · DI.2 asks *"can I choose a tool?"* · **neither asks
  *"is this tool eligible given the context actually available?"***

A context-dependent read whose context is *unavailable* falls through both gates. This
is **context-eligibility** — not authority (DI.1), not arbitration (DI.2). It is
**architecturally real but NOT corpus-evidenced** as a dominant class. Kept sharp from
its sibling: the **param-resolution** seam R8/R9/R10 hit (`shot_id` *is* derivable;
resolution failed) is *observed* and is the nearer hill; context-eligibility is the
*unavailable-context* case, dormant.

**Disposition (Creative's plan, ratified): capture cheap, defer graduation.** The
context-dependency column is recorded above (done, no re-run); the **context-stripped
variant** re-run — the experiment that would *evidence* the seam — is deferred. Let the
data decide whether it earns its own phase.

## Cross-phase win — a measurement-debt item retired

T1 incidentally delivered what DI.1-CLOSE honestly owed: **DI.1's live mutation-block,
demonstrated.** R5 (`flame_open_batch_group` → `unauthorized_mutation`) and R11
(`flame_set_start_frames` → `blocked_unratified_mutation`) both hit the gate live, 3/3.
DI.1-CLOSE could only suite-prove it (Symptom 2 masked it). Mutation-compiles that
resolve to a single tool reach the edge; multi-match reads die at the resolver. The
DI.1→DI.2 ordering is now empirically right.

## Roadmap — SEED-COMPILE-QUALITY decomposed (evidence-ranked)

The over-broad seed splits into grounded successors:

- **compile-shape** (malformed / over-injected chains: R2, R5, R6) — observed.
- **param-resolution** (derivable id/scope unresolved: R7 project, R8/R9/R10 `shot_id`)
  — observed, **the nearest hill** (DI.2 just exposed it).
- **context-eligibility** (tool needs *unavailable* context; falls through DI.1+DI.2)
  — **dormant**, capture-cheap-defer.
- **answer-pass** (field mishandling: R3) — known since CR.1.

## Methodology candidates (for v1.10 close)

- **Measure-first gate firing cleanly → a rung not built.** T1's empty residual gated
  T4 out; the skip rationale is locked in the acceptance test, not just docs. Clean
  instance of contingent-rung-gated-by-data.
- **Audit-before-overfit prevented a wrong turn.** Creative's hypothesis test (Outcome
  A) de-risked the "corpus contaminated by hidden state" fear *before* the close
  hardened a wrong taxonomy — and corrected my own overcount (R5). Conflation-vigilance
  applied recursively (to the auditor's own result).
- **The win must be stated at its native layer.** "Arbitration resolved 3/9" ≠ "3 reads
  now work." Sibling of [[feedback-distinct-success-criteria-per-adjacent-layer]].

## Status

**DI.2 CLOSED** — eligibility arbitration shipped, suite-proven, code-verified, and
live-confirmed; the reachable resolver-overmatch class is resolved at the arbitration
layer; T4 correctly never shipped; the audit confirmed scope and named a dormant seam.
**With DI.1 (trust) and DI.2 (usefulness) both landed, v1.10 Authority Invariance is
substantively complete — v1.10 close opens next.**

---

*Closed 2026-06-01. The arbitration goal is real, tested, and live. The reads it
unblocks still wait on the parameter layer — named, not annexed. The hidden-context
audit came back Outcome A: the system is mostly failing on questions it should already
be able to answer, which means the road ahead is the right one. No overclaim.*
