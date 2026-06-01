---
milestone: v1.10
phase: DI.1
type: phase-close
status: closed-safety-floor-shipped-verified-modulo-symptom-2
closed: 2026-06-01
honest_scope: "DI.1's authority guarantee SHIPPED and is suite-proven + code-verified + live-no-regression: the three-site dispatch gate (1B/1C hard-block, 1A best-effort strip), fail-closed reader, registration-boundary close, ratified carve-out, capture-seam, baseline, regression-lock. The live mutation-block was NOT demonstrated at runtime — Symptom 2 (resolver paralysis) intercepts every request before it reaches the gate. That is not a DI.1 defect; it is the meta-finding (DI.1's gate sits downstream of Symptom 2, so its live value is latent until DI.2). No artist UAT (carry-forward, as struck for the milestone)."
verification: "suite 2673 passed / 41 skipped; gates read live at handlers.py:725 / _step.py:415 (before call_tool) with ratified_replay sourced from assent_record.status=='ratified'; apply path :796/:852 ungated; T1 capture confirmed live (6 chain_aborted records w/ outcome tag); no read over-blocked (failures are pre-gate tool_selection_ambiguous)."
commits: 2d01d72..5924818 (9)
---

# DI.1 — Close (safety floor shipped; live-verified modulo Symptom 2)

> DI.1 set out to make a mutation unable to execute outside the authority chain
> by *any* routing edge. The code achieves that — proven by the suite and by
> reading the wired gates — and the implementation is more precise than the plan
> (the gate encodes "block a mutation unless authority was granted" directly via
> the `ratified_replay` carve-out). The one thing the live runtime could *not*
> show is the gate firing on a real request, because Symptom 2 kills every
> request before it reaches the gate. Recording that honestly is the point of
> this artifact.

## What shipped (9 commits, `2d01d72..5924818`)

All eight plan tasks, atomic, measure-first preserved:

- **T1** capture-seam extension (`2d01d72`) — capture now fires on the failure
  seams with an `outcome` tag (closes the CR.1 corpus blindspot).
- **T2** pre-enforcement baseline (`8f56df9`).
- **T3** registration-boundary close (`c1eb8bb`) — `registry.py` defaults
  `user-taught` tools to mutating; absent-annotation set → ∅ universally.
- **T4** fail-closed `dispatch_authority` reader (`9f40381`) —
  `console/_authority.py`, read only if `readOnlyHint is True`, no cli import.
- **T5/T6** the **1B** (`a1abf3a`, `handlers.py:725`) and **1C** (`db03ac8`,
  `_step.py:415`) dispatch-edge gates — block before `call_tool`.
- **T8** regression-lock (`4fa6038`) — gate blocks mutation **and** ratified apply
  still executes (the excluded `:796/:852` path).
- **T7** 1A best-effort commit-strip (`9797d20`) + read-path fixtures (`5924818`).

`__all__` == 19; version 1.5.1; scope contained (no store/assent edits).

## Verification (what's proven, and how)

- **Suite-proven:** 2673 passed / 41 skipped, including `4fa6038` (gate blocks a
  mutation; ratified apply executes).
- **Code-verified (read live):** the gates sit *before* `call_tool` at both edges;
  `ratified_replay` is derived from `assent_record.status == "ratified"` (genuine
  A.2 authority, not a spoofable flag); the apply path is ungated; the reader is
  fail-closed; 1A never reaches the narrowing functions.
- **Live no-regression:** on the current-code daemon (`5924818`), reads are not
  over-blocked — every observed failure is pre-gate `tool_selection_ambiguous`,
  never a false `unauthorized_mutation`.
- **T1 live:** 6 `chain_aborted` records captured with `outcome` tags.

## What this close does NOT claim

- **The live mutation-block was not demonstrated.** Symptom 2 (resolver paralysis)
  intercepted every request — chat *and* deterministic `fbridge exec` (the exact
  step `flame_set_start_frames` matched 9 tools and aborted at the resolver) —
  before it reached the gate. The block is proven by the suite, not by a live
  request. Honest, not hand-waved.
- **No artist UAT** (carry-forward; artist UAT was struck for the milestone until
  the compile-layer work lands).

## The meta-finding (load-bearing for DI.2 and the sequencing)

**DI.1's gate sits downstream of Symptom 2.** Until DI.2 (eligibility arbitration)
lands, most requests die at the resolver before they can reach the dispatch edge
to be blocked. Two consequences, both validating the framing:

1. **DI.1's safety value is currently latent in the live runtime** — correct and
   tested, but rarely *reached*. Today's apparent safety is partly *accidental*
   (the resolver kills mutations early), not the guarantee. DI.1 converts it into
   a guarantee for when requests reach dispatch.
2. **DI.2 is what lets requests reach the dispatch edge** — which is exactly when
   DI.1's gate becomes load-bearing. So the **DI.1→DI.2 ordering is right** (the
   guard must exist before arbitration opens traffic to the edge), and **"DI.2
   must follow immediately"** is now empirical, not doctrinal: DI.1's value is
   gated on DI.2.

## Status

**DI.1 CLOSED** — the authority guarantee is shipped, suite-proven, code-verified,
and live-no-regression. The live block is masked by Symptom 2 (the meta-finding),
not demonstrated. **DI.2 opens next** and is now empirically the priority: it is
the wall standing between DI.1's gate and the requests it exists to guard.

---

*Closed 2026-06-01. The guarantee is real and tested; the live demonstration is
honestly owed to a runtime where requests can reach the gate — which is DI.2's
job. No overclaim.*
