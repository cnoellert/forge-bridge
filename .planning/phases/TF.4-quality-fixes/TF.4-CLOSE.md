# TF.4 Quality Fixes — CLOSE

**Status:** CLOSED 2026-06-03. **Base:** `main @ 2aa8dbf` (Slice #3 shipped). **Ruling:** DT + Creative converged to close; both corrections below strengthen the artifact, neither blocks the decision.

TF.4 was the first v1.13 touch of **runtime** code (compile prompt + compile-output parse), driven entirely by **live measurement, not archaeology** — and three times direct observation overturned the provisional roadmap shape (serialization-was-dominant; frozen-can't-host-the-bar; list-projects-is-well-formedness-not-routing).

---

## Delivered (3 slices + 1 measurement-instrument pass, each close-graded)

| # | defect | slice | mechanism | guarantee | commits |
|---|---|---|---|---|---|
| #1 | detached-args (chain-step serialization) | Slice #1 | A2 loosen-then-normalize; `normalize_chain_shape` reattaches | **deterministic** (Prong B) | `451a847`→`d355a88` |
| #2 | space-mangle / entity value-fidelity | Slice #2 | param-location-blind **detector** + Prong-A prompt (ineffective, measured) | none (content tier) | `a7b26c2`/`e9aefac`/`bc15158`; S4→TF.3b `6bb2af3` |
| — | **measure-first re-rank + `compile_raw`** | (A) Post-Gate #2 | raise-path raw capture instrument; N≥3 re-rank | — | `f345bfd`/`1d54a12`/`bbe984e`/`6eaca91` |
| #3 | trailing-empty-segment | Slice #3 | A2 loosen-then-normalize; preserve-into-steps → `normalize_chain_shape` pops trailing empty observably | **deterministic** (content-free) | `096e8b8`/`493e1f8`/`2aa8dbf` |

The **`compile_raw` instrument is permanent** — raise-class compile failures are no longer blind; the next phase inherits a working forensic surface.

## The durable finding (sharpened — DT Correction 2; survives the off-diagonal case)

Creative's headline — *recoverable-vs-non-recoverable is a **fixability** boundary, not a classification boundary* — is right and durable. But recoverability is **orthogonal to the well-formedness/content tier**, not equal to it. `non_tool_step` (a *malformed* defect that is *non*-recoverable) and `space-mangle` (a *well-formed* defect that is non-recoverable) are the off-diagonal cells that prove the real axis is **faithful-content recoverability**:

|  | recoverable | non-recoverable |
|---|---|---|
| **malformed structure** | `detached_args`, `trailing_empty` → **fixed, guaranteed** | `non_tool_step` → no faithful repair |
| **well-formed structure** | — | `space-mangle` → detector + prevention |

> **Fixability is governed by faithful recoverability — is the correct content present-and-extractable *without synthesis* — which is orthogonal to whether the defect is structural (well-formedness) or semantic (content). Well-formedness defects are not all recoverable (`non_tool_step`); the two that were (`detached_args`, `trailing_empty`) were recoverable because content-free or content-preserved, NOT because structural.**

This tells the next phase how to predict fixability: ask *"is the faithful content present?"* — not *"is it structural?"*

## Deferred (explicit dispositions — no measured class vanishes)

- **`non_tool_step`** (measured: **5 instances / 2 inputs** across frozen + postgate + postgate-slice2; intermittent). **Non-recoverable well-formedness defect** — the prose *carries intent* (can't be faithfully dropped like an empty segment) and can't be faithfully mapped to a tool (that would be synthesis, forbidden). Detector-only/prevention; deprioritized by low/variance frequency. Currently re-raises via `_validate_chain_shape`'s non-tool check (detected, loud, un-repaired).
- **`space-mangle` guarantee** — detector + prevention shipped (Slice #2); the *deterministic guarantee* needs an external ground-truth source (live entity set), blocked on desktop-wiring (gated, uncorroborated per (A) Findings 3).
- **desktop-wiring / contextual resolution (Shape A)** — investigation-gated; not promoted by the postgate-15 (residuals were routing + well-formedness, not contextual).
- **honest-decline-on-capability-gap** — model/routing change (not model-free); the `:407`-class net is param-resolution only.
- **example-strip** — measured-rare (TF.3a demoted example-salience).
- **TF.3b corpus instrument items** — the shared-label / `defect_ref`-per-manifestation representation problem (the S4 deposit: `expected_well_formed`/`defect_ref`/`expected_classes` are per-`(input,observation)` but modeled per-input; flipping frozen labels is schema-invalid), plus class-frequency counting hygiene.

## Methodology (banked)
- **Read-before-scoping** caught a misclassification each time the raw was read (the `compile_raw` instrument earned its keep on #3: routing→well-formedness).
- **Measure-first** killed two prediction-driven slices (example-strip stayed parked; #3 confirmed on data, not momentum) and applied to itself ((A)'s control-skip; the re-rank from existing N≥3).
- **Grounding-relocates-the-finding** recurred: the bar's home moved frozen→postgate; S4 pulled to TF.3b on a consumer/schema read; `compile_raw` scope narrowed to the raise-path; the design seam (parse_chain silently drops) corrected the "extend normalize" instinct into preserve-into-steps.
- **Observability invariant** (Creative, ratified, now tier-general): malformed structure must survive parsing to be observed by `normalize_chain_shape`; silent repair is non-conformant even if the graph ends correct.

## Next → TF.3b
The corpus-instrument phase: the shared-label / per-manifestation representation + counting hygiene (the S4 deposit), the entity-resolution Tier-2 detector's home (built in Slice #2 as `detect_entity_value_fidelity`, internal — export when TF.3b consumes), and the well-formedness-tier coverage now that the recoverable cells are fixed.

**Constraints held throughout:** `forge_bridge.__all__` = 19; `translation_oracle.__all__` = 18; `pyproject` = 1.5.1; `SCHEMA_VERSION` = "1" (every change additive); frozen + postgate corpora never mutated; `parse_chain` untouched; no new external libs.
