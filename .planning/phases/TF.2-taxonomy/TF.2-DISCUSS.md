# TF.2 (Taxonomy) — DISCUSS: formalize the translation failure taxonomy

**Milestone:** v1.13 Translation Fidelity, Phase 2 of 4. **Predecessor:** TF.1 (contract + inventory, closed).
**Objective:** formalize the failure taxonomy that **Phase 3's oracle measures** — so it must be *detectable*,
not just conceptual. Seeded by the D-series; mapped onto the inventory's six components.
**Deliverable (after this discuss):** `TF.2-TAXONOMY.md`.

---

## The five classes (grounded seed — D-series + inventory)

| Class | What goes wrong | Grounded instance | Component (TF.1-INVENTORY) | Detection sketch (for Phase 3) |
|---|---|---|---|---|
| **grounding / example-salience** | param filled from a tool-description example, not intent | defect #1 (`prefix→noise`) | tool descriptions → `compile_intent` (1) | value matches a known liftable example (D3 inventory = the oracle) |
| **routing** | wrong tool selected / compile shadowed | defect #2-a (PR20-shadows-compile) | filter/narrow (2) | `tools_filtered=1` + no compile line (D1 signal) |
| **extraction** | operator-written `key=value` not captured | defect #2-b (`"prefix 013"` unparsed) | `extract_explicit_params` (4) | key token in step-text but absent from extracted params |
| **entity-resolution** | a *named* entity mis-resolved from text | qualified-name mangle (text→canonical) | `resolve_query_entities` (3) | resolved value ≠ correct canonical (needs labeled corpus) |
| **contextual / stateful** | a *state-reference* ("this"/"last"/"current") unresolved | defect #3 (open-sequence not injected) | `resolve_query_entities` dispatch + unwired `desktop` (3) | ref pattern present + `desktop` unavailable |

---

## Design questions (leads-with-views; → room)

### Q1 — MECE vs multi-tag? **Lean: multi-tag (non-exclusive).**

Defect #2 is *one* defect exhibiting *two* classes (routing **+** extraction). Forcing mutual exclusivity
would lose that. **Lean:** a defect carries **all** class-tags it exhibits; classes are *collectively
exhaustive* but **not** mutually exclusive. Consequence for Phase 3: frequency is counted per-class, so one
defect can increment two classes — and the *ranking* must account for co-occurrence (fixing routing may not
fix a defect that also has an extraction tag). Name the co-occurrence explicitly so Phase 4 doesn't assume a
single-class fix clears a multi-class defect.

### Q2 — capability-gap: verdict-pair, not a sixth class. **Lean: a second axis.**

The room already ruled capability-gap stays out of the *failure* taxonomy (it's substrate work, R9). But the
oracle must recognize it. **Lean: the taxonomy has two axes** —
1. **translation failure classes** (the five above — *what's wrong with translation*), and
2. **the verdict matrix** (translation {pass, fail} × substrate {pass, gap}).

Capability-gap = the **(translation-PASS, substrate-GAP)** cell — *honest decline against an absent
capability* (R9), a translation **success** the oracle must reward, never score as a failure. The five
classes only populate the *translation-FAIL* column. This keeps `[[feedback-substrate-pass-translation-open]]`
literal: the oracle emits a verdict *pair*, and the failure class only applies when translation actually
failed.

### Q3 — detectability is a first-class requirement. **Lean: every class ships a detection signal.**

The taxonomy is only useful to Phase 3 if each class is *detectable* (the right column above). **Lean:** TF.2
specifies, per class, a detection signal + its confidence/cost, and flags which need the **labeled reference
corpus** (entity-resolution + the "correct value" classes can't be detected without ground truth — that's
Phase 3a's keystone work). This is the TF.2→TF.3 handoff: the taxonomy *names* the detectors; 3a *builds +
validates* them (incl. the example-fill detector's false-positive rate).

### Q4 — entity-resolution vs contextual/stateful: keep distinct. **Lean: yes, distinct.**

The boundary is **"does it need runtime/desktop state?"** — entity-resolution = *text → canonical*
("30sec_edit 21_publish" → the sequence; SR.1's qualified-name work, no state); contextual = *state-reference
→ canonical* ("this sequence" → the open sequence; needs `desktop`, only at dispatch). D2/D3 grounded the
distinction; the fixes differ (resolver hardening vs wiring `desktop`). **Lean:** keep them as two classes
with that one-line boundary test.

---

## What TF.2 produces (after the room settles Q1–Q4)

`TF.2-TAXONOMY.md`: the five failure classes (boundaries + grounded instances + detection signals +
component map) **and** the verdict matrix (with capability-gap as the rewarded pass+gap cell), the multi-tag
rule, and the explicit TF.2→TF.3a handoff (which detectors need the labeled corpus). No detection code, no
oracle (that's 3a); no fixes (Phase 4).
