# TF.1 — Formalize (CLOSE)

**Status:** `closed` — contract formalized, integrity invariant locked, **genuinely formalize-not-build**
(production code net-zero after the out-of-scope parser revert). **Milestone:** v1.13 Translation Fidelity,
Phase 1 of 4. **Next:** Phase 2 (Taxonomy).

---

## What TF.1 delivered

The contract Phases 2–4 build on — and the one integrity claim that keeps it honest under dispatch-time
resolution, verified and locked.

- **T1 — ratification-integrity audit + lock (CLOSED).** Verdict: the invariant **HOLDS** — *dispatch may
  resolve refs the graph left unresolved; it may never override an explicitly-ratified param* — by merge
  order (`_step.py:261` puts explicit `user_params` last). Locked by a `run_apply_branch` regression test
  pinning four legs (semantic-fills · ratified-executes · unratified-blocks · **explicit-wins-on-same-key-
  collision**), the last via a monkeypatched conflicting `project_id` — **zero production-extraction change**,
  falsifiable (flip `:261` → only the collision case reds). DT sign-off, no reservations.
- **T2 — `TF.1-CONTRACT.md` (CLOSED).** Five normative clauses: the compile-resolved vs context-resolved
  axis; the integrity invariant with the **contract/implementation split** (explicit defined broadly = any
  operator `key=value`; `extract_explicit_params` is the partial implementation; extraction-completeness =
  Phase 4); the Shape-A coupling; the translation-quality objective (preserve honest uncertainty).
- **T3 — `TF.1-INVENTORY.md` (CLOSED).** Six components, the straddle map, the unwired-`desktop` enablement
  gap, the `:407` honest-decline net.

## Honest scope (the close-ceremony's job)

TF.1 is **net-zero production code.** The `5313cfa` `sequence_name=` parser addition — landed mid-phase to
make a test green — was found out-of-scope (a narrow, buggy, ungated Phase-4 extraction change) and
**reverted** (`9e9bc03`); `_param_extract.py` diffs empty against the pre-TF.1 baseline. The invariant is
locked without it. Formalize-not-build held — *after* the room caught the slide. Phase 1 = test + docs only.

---

## Carry-forwards (preserve, don't act)

- **Space-truncation trap → Phase-4 defect #2 extraction slice (DT).** When the parser is broadened to
  recognize `sequence_name=` (and general `key=value`), it MUST handle **space-bearing qualified names**
  (`30sec_edit 21_publish`) — *not* copy the UUID-shaped `split(maxsplit=1)[0]` logic, which truncates at
  the first space (→ `30sec_edit`). This is exactly the SR.1-preserved name shape; it would be re-discovered
  painfully mid-Phase-4. Logged in the v1.13 framing Phase-4 slice notes so it travels with the work.
- **Contextual fix lands at dispatch (component 3-dispatch), wiring `desktop`** — Phase 4 / defect #3.
- **Shape-A coupling recorded** — a future Shape-B motion (ratify concrete target) inherits the
  desktop-at-compile prerequisite.

## Methodology

- **The collision close-gate caught a real enforceability gap — on my own audit.** T1 asserted "explicit ≡
  `extract_explicit_params` output"; the collision test revealed that output was *lossy* (multi-`key=value`
  parse gap), so "explicit wins" was vacuous for multi-param steps. The four-leg test proved *coexistence*,
  not *precedence* — `[[feedback-mock-three-tier]]`. ~9th grounding-flip of the arc; vindicates DT/Creative
  insisting on the same-key collision. (Orch verification miss, owned.)
- **Contracts and implementations don't move in lockstep (Creative).** The contract defines the boundary
  (explicit = any operator `key=value`); the implementation realizes part of it; extraction-completeness is
  a separate, gated axis. Authoring the contract broadly while the parser is partial is *not* retrofitting —
  it's the honest separation. A central Translation Fidelity lesson; candidate methodology memory.
- **Anti-scope discipline held under test pressure** — twice a test was almost made green via a production
  change; the room reverted the second (`[[feedback-anti-scope-discipline-under-pressure]]`). The lock that
  shipped changes zero production behavior.

---

## Verdict

TF.1 closed. The translation/substrate contract is formalized on the compile/context axis, the integrity
invariant is locked + falsifiable, and the phase stayed true to formalize-not-build. → **Phase 2 (Taxonomy):
formalize the five failure classes** (grounding · routing · extraction · entity-resolution · contextual/
stateful), seeded by the D-series, mapped onto the inventory's six components.
