# TF.4 Post-Gate #2 (post-Slice-2 measure-first gate "A") — PLAN

**Status:** Orch draft, grounded against existing N≥3 postgate data + `compile_raw` machinery. Pending room redline.
**Date:** 2026-06-03. **Base:** `main @ bc15158` (Slice #2 S1–S3 shipped, pushed).
**Purpose:** the measure-first gate the room converged on — re-measure after Slice #2 before picking the next content slice (don't predict; the trap sprang twice this milestone). Decides #3–#5 and gates the desktop-wiring slice (C).

---

## The reshaping finding (grounding moved (A)'s center of gravity)

DT scoped (A) as "bring the stack up, capture, re-rank." Grounding the **existing** N≥3 postgate corpus (`reference/postgate` + `postgate-run1/2/3`, 4 runs @ `d355a88`, `TF.4-POSTGATE-FINDINGS.md`) shows the re-rank is **already substantially banked**:

| rank | defect | evidence | status |
|---|---|---|---|
| #1 | serialization (detached_args) | 0/60 post-clause | fixed (Slice #1) |
| #2 | space-mangle / entity-resolution | stable 4/4 | measured (Slice #2) |
| **#3** | **`list projects` → `invalid_chain_shape`** | **stable 4/4, genuine malformation** | **next content target — the `compile_intent`-raise class** |
| #4 | `non_tool_step` (prose) | intermittent 2/4 | real, not outranked |
| — | `gen_0460` CompileBudgetExceeded | 1/4 | timeout noise, out-of-scope |

Two consequences:
1. **A fresh capture barely moves the ranking.** It's stable across 4 runs, and Prong A (space-bearing-literal clause) targets #2, not the #3 raise-class — so it won't re-order #3. Per the Slice-1 honest ceiling, a fresh capture also **cannot attribute** Prong A's effect (variance vs clause). So "re-measure to firm #3–#5" is mostly *confirmation*, not discovery.
2. **The genuine live value concentrates in `compile_raw`.** The #3 raise-class is **blind today** — `steps` is never bound (`compile_intent` raises before the tuple-unpack), so `observed_graph` is `[]` and `compute_well_formed` only sees "empty + compile_error." Raw is the one signal that reveals *why* a trivial "list the projects" compiles to an unparseable shape. `compile_raw` was the named carry-forward (`TF.4-PLAN.md` design-call #2, `TF.4-POSTGATE-PLAN.md` carry-forward) precisely for this pass.

⇒ **(A) is an instrument pass that cracks the #3 raise-class, not a generic re-measure.** Its headline deliverable is the raise-path `compile_raw` capture + a raise-class-visible re-capture; the re-rank is confirmation that rides along.

**History reads as designed, not reversed (DT).** `compile_raw` was deferred at the Slice-1 post-gate turn with an explicit maturation condition: *"required iff a future pass investigates the `compile_intent`-raise classes."* #3 being the `list projects` raise-class **is that condition firing on schedule** — the parked transitional-naming maturing, not "skip it, now do it" ([[feedback-transitional-structure-naming]]).

**Retires an open flag (DT).** The Slice-#2 S5-close asked: is `invalid_chain_shape` runtime-budget noise or real malformation? Grounded answer — **it isn't monolithic:** the stable one (`list projects`, 4/4, empty graph, same case across postgate+run1/2/3) = a real parse failure on a trivial intent → in-scope, **= #3**; the one-off (`gen_0460`, 1/4) = `CompileBudgetExceeded` runtime noise → ignore. Flag closed.

## What (A) decides — and the honest ceiling
- **Decides:** is #3 (the `invalid_chain_shape` raise-class) confirmed as the next content slice on fresh data, and does `compile_raw` reveal a tractable defect shape to fix? Confirms/kills (C) desktop-wiring (the postgate-15 showed routing + well-formedness residuals, **not** contextual — fresh data either corroborates or refutes).
- **Does NOT decide / claim:** Prong A's efficacy. One capture **ranks, it does not attribute** ([[feedback-baseline-drift-invalidates-controls]]). N≥3 for distribution stability, never for causation. The clause-reverted control stays parked (flips mandatory only if a motion proposes *relying* on Prong A — Slice-1 carried record #3).

## Constraints (binding)
`forge_bridge.__all__` = **19**; `translation_oracle.__all__` = **18** (`compile_raw` is a schema field, not a public symbol — confirm at S1). **`SCHEMA_VERSION` stays `"1"`** (`compile_raw` additive, type-if-present — the validator checks `if field in observed`, so existing rows validate untouched; same pattern as `salvage_applied`/`original_reason`, `TF.4-PLAN.md:84`). Frozen corpus + existing `postgate*` dirs **never mutated** — fresh capture writes a NEW dir. No new external libs.

---

## Steps

### S1 — `compile_raw` RAISE-PATH capture (MODEL-FREE — lands before the stack is up)
**Redlined cheaper (DT+Creative): raise-path only — no `compile_intent` contract change.** Grounding confirmed the raw is **already on the exceptions** the raise-path already catches:
- `CompileInvalidChainShape(raw_response, parse_error)` → `self.raw_response` ✓ (**#3's class — `list projects`**)
- `CompileUnresolvableIntent(raw_response)` → `self.raw_response` ✓
- `CompileToolUnknown` → `self.step_text` (no raw_response)
- `CompileSeamViolation` → `self.offending_step_text` (no raw_response)
- `CompileBudgetExceeded` → no raw payload

So S1 is: in `run_compile_branch`'s `except CompileError as exc` block, capture `compile_raw = getattr(exc, "raw_response", None)` and carry it onto the outcome → trace. **Per-subtype-safe by construction** — `getattr(..., None)` yields `None` for the three subtypes that don't preserve raw (their full raw isn't on the exception — a known, out-of-scope gap; #3 only needs the raw-bearing path). **Do NOT touch the successful `compile_intent -> list[str]` contract; success-path raw is deferred** (no consumer needs it — substrate-before-consumer).
- `_schema.py`: add `"compile_raw": (str, type(None))` to `_OBSERVED_MARKER_TYPES`. **SCHEMA_VERSION stays `"1"`** (additive, type-if-present). `translation_oracle.__all__` stays **18** (field, not symbol).
- Thread `compile_raw` through `CompileBranchOutcome` (default `None`) → `observed_trace_from_compile_outcome` (`_capture.py:75-100`) into the trace dict.
- Tests (`tests/translation_oracle/`): synthetic — a `CompileInvalidChainShape` outcome → trace carries its `raw_response` as `compile_raw`; a `CompileBudgetExceeded` outcome → `compile_raw is None` (no AttributeError — the per-subtype guard); a success outcome → `compile_raw is None` (contract untouched); old corpus still validates (additive). **Model-free; no stack.**

### S2 — N≥3 live re-capture, post-Slice-2, WITH `compile_raw` (NEEDS the stack)
Pre-flight: stack up (Ollama + Flame + daemon; [[project-c2-live-console-operational-topology]] + [[project-daemon-dual-launch-paths]]); confirm daemon serves the S1 HEAD. Run the 15-case set ≥3×, writing to a **NEW** dir (preserve the existing baseline): `run_captures --output reference/postgate-slice2` (×3, or sequential run dirs). **S2's primary job is raise-class raw capture, NOT ranking** (the ranking is already banked — DT) — the new signal vs the existing 4 runs is that **the `list projects` raise-class now carries `compile_raw`** → classifiable + forensically replayable instead of blind. Re-rank is ride-along confirmation; Prong-A attribution is explicitly out (control parked).

### S3 — Re-rank ratification + the #3 decision (`TF.4-POSTGATE2-FINDINGS.md`)
- Confirm the ranking against fresh+existing data: is #3 still the `invalid_chain_shape` raise-class? Is #4 `non_tool_step` still intermittent? Did anything surprise (the measure-first guard against momentum)?
- **Read the `list projects` `compile_raw`** — what shape does the model actually emit that the parser rejects? This scopes the #3 fix slice (is it a parse-tolerance fix, a prompt fix, or a genuine model defect — the routing/impl/reachability lens [[feedback-routing-vs-implementation-vs-reachability]]).
- **(C) verdict:** does fresh data corroborate contextual/desktop-wiring as a ranked defect, or confirm it's uncorroborated (→ stays gated/deprioritized)?
- Ratify the next content slice from measured data — NOT prediction.

---

## Goal-backward verification
(A) achieves its purpose iff: (1) `compile_raw` is threaded and a fresh raise-class case carries non-empty raw (the blind spot is closed); (2) the #3 ranking is confirmed-or-revised on fresh N≥3 data, not asserted; (3) the `list projects` raw is read and the #3 fix is scoped by *observed* malformation shape; (4) the (C) desktop-wiring question is answered by data. **No Prong-A attribution claim is made.**

## Out of scope (parked, named)
The #3 fix itself (this pass scopes it, doesn't build it); Prong-A clause-reverted control (parked trigger, Slice-1 record #3); the example-strip slice (measured-rare); honest-decline-on-gap (measured-present but model-dependent — not this pass); TF.3b shared-label architecture (the S4 deposit).

## Commit cadence
S1 (`compile_raw` threading + synthetic tests) — model-free, lands first · S2 (live re-capture data, new dir) · S3 (`TF.4-POSTGATE2-FINDINGS.md` + re-rank ratification). S1 is the do-now-before-stack item; S2/S3 gate on the stack.
