# TF.2 — The Translation Failure Taxonomy (v1.13 Translation Fidelity)

**Milestone:** v1.13 Translation Fidelity, Phase 2 of 4. **Predecessor:** TF.1 (contract + inventory, closed).
**Status:** room-settled (Q1–Q4, DT/Creative/Orch). **Consumes:** `TF.1-CONTRACT.md`, `TF.1-INVENTORY.md`.
**Produces for:** Phase 3a (which detectors need the labeled corpus) → 3b (run) → Phase 4 (ranked fixes).
**This doc names; it builds no detector, no oracle (3a), no fix (Phase 4).** Counts are archaeology-grade.

---

## 1. Two axes, not one

The taxonomy has **two independent axes** — collapsing them violates
`[[feedback-substrate-pass-translation-open]]` (translation-pass and substrate-pass are independent verdicts):

1. **Translation failure classes** (§3) — *what's wrong with the NL→chain-step-graph translation*. Five
   classes. Populate only the **translation-FAIL** column of the matrix below.
2. **The verdict matrix** (§2) — translation {pass, fail} × substrate {pass, gap}. The oracle emits a verdict
   **pair**; the failure class applies **only when translation actually failed**.

---

## 2. The verdict matrix **[four named cells]**

| | substrate **PASS** (capability present) | substrate **GAP** (capability absent) |
|---|---|---|
| **translation PASS** | **(a) success** — graph correct + executed | **(c) honest decline (R9)** — *rewarded*; capability-gap, see §2.1 |
| **translation FAIL** | **(b) pure translation failure** — 5 classes; substrate would have satisfied a correct graph | **(d) compound** — 5 classes apply, AND substrate can't satisfy even a correct graph |

- **The five classes populate cells (b) and (d)** — the whole translation-FAIL row, regardless of substrate.
- **Cell (c) is a translation *success*** the oracle must reward, never score as failure. This is capability-gap
  (R9) — it stays **out** of the five classes (framing-room ruling; it's substrate work, not translation).
- **Cell (d) is named so Phase-4 ranking stays honest:** fixing the translation tag(s) of a (d) defect yields
  **no end-to-end win** until the substrate capability lands. The substrate-gap acts as an extra **tag** that
  blocks clearance (§4) even after every translation tag is fixed. A (d) defect is a *translation* finding and
  a *substrate* finding at once — do not let a translation fix claim an end-to-end win it can't deliver.
- **The five classes populate both (b) and (d); substrate-gap does NOT pre-empt the translation tags**
  (DT R3 / Creative). *Pre-empt was considered and rejected on independence grounds*
  (`[[feedback-substrate-pass-translation-open]]`): if a substrate-gap erased the translation tags, the
  translation defect would vanish from the record — and the day the capability lands (an R9 gap gets a tool),
  it would resurface as a fresh regression with no prior trace. `create timewarp 100–200` *understood
  correctly but unsupported* (c) and *misrouted AND unsupported* (d) are different facts; collapsing them
  loses exactly the distinction the matrix exists to make. The two verdicts stay independent dimensions.

### 2.1 The decline-vs-misroute discriminator (cell (c) vs cells (b)/(d))

(c) and (b)/(d) both produce "no successful execution" — the oracle must distinguish them:

- **Declined** → the honest-decline net fired (`UNRESOLVED_REQUIRED_PARAM` → "specify the exact sequence
  name", `_step.py:407`). No wrong dispatch happened. → cell (c), rewarded.
- **Dispatched-wrong** → a dispatch occurred with a wrong tool/params. → translation-FAIL (b/d).

This discriminator is itself a **detector** (§5) and is the runtime hook the oracle keys on. Note (TF.1-CONTRACT
§5): example-salience can **defeat** the decline net — a lifted example masquerades as explicit, bypasses `:407`,
and converts a should-be-(c) decline into a silently-wrong (b)/(d) dispatch. So the grounding class (§3.1) is
partly *"a decline that should have happened didn't."*

---

## 3. The translation-failure classes

> **AMENDED 2026-06-02 (TF.3a live-capture ratification): translation-FAIL is TIERED.** The live capture
> surfaced a dominant failure the five classes don't name — **chain-step serialization** (the model emits the
> tool name and its args as separate steps → params never attach). The room ruled it is **not a 6th peer class
> and not a widened "extraction"** (different component: compile-grammar vs `extract_explicit_params`; folding
> would violate the §4 clearance rule). Instead translation-FAIL decomposes into two tiers:
>
> - **Well-formedness tier** (the gate): the graph is *structurally* invalid — detached args, prose steps,
>   invalid chain shape. A malformed graph **short-circuits** content evaluation (you cannot ask "was the tool
>   right?" of a graph whose args never attached). Schema: `ObservedTrace.well_formed` + reason;
>   `Label.expected_well_formed=False` ⟹ translation=fail, content classes empty.
> - **Content tier** (the five classes below): the graph is well-formed but *wrong*.
>
> Consequence (TF.3a): serialization is **Phase-4 slice #1**, and content-class frequencies are only reliable
> **after** the gate clears (current measurements are "what survived malformation"). See `TF.3a-CAPTURE-FINDINGS.md`.

### The five content classes

Multi-tag, **collectively exhaustive but NOT mutually exclusive** (§4). Each maps onto a TF.1-INVENTORY
component. "Detection" rows are specified fully in §5.

### 3.1 grounding / example-salience
- **What goes wrong:** a param is filled from a **tool-description example**, not from operator intent.
- **Grounded instance:** defect #1 (`prefix → "noise"`); the E2E-01 `30sec_21` bake-in (TF.1-CONTRACT §5).
- **Component:** tool descriptions → `compile_intent` (1); the lifted value then rides components 3/4.
- **Boundary:** the value's *provenance* is a docstring example, regardless of whether it looks explicit.
- **Cross-link:** defeats the honest-decline net (§2.1) — false certainty in a *ratifiable* preview.

### 3.2 routing
- **What goes wrong:** wrong tool selected, or compile shadowed by a forced-execution path.
- **Grounded instance:** defect #2-a (PR20 shadows `compile_intent`).
- **Component:** `filter_tools_by_message` / `deterministic_narrow` (2), incl. the PR20 forced path.
- **Boundary — two modes:** *(i) compile shadowed* — the forced-execution path bypassed `compile_intent`
  entirely (defect #2-a); *(ii) wrong tool selected* — compile ran and picked the wrong tool. The two modes
  detect at **different tiers** (§5): shadow is substrate-observable (Tier 1, the `tool_forced` marker);
  wrong-selection needs the labeled correct-tool (Tier 2). 3b must not claim routing coverage on the Tier-1
  half alone.

### 3.3 extraction
- **What goes wrong:** an operator-written `key=value` (or quoted / space-bearing) form is **not captured**.
- **Grounded instance:** defect #2-b (`"prefix 013"` unparsed by `extract_explicit_params`).
- **Component:** `extract_explicit_params` (4).
- **Boundary:** the value **is present in the step text** as an explicit form but is absent from extracted
  params. (TF.1-CONTRACT §3: this is *extraction incompleteness vs the contract boundary* — not a contract
  violation; closing it is Phase-4 / defect #2, done generally, not per-key.)

### 3.4 entity-resolution
- **What goes wrong:** a **named** entity is mis-resolved from text → wrong canonical.
- **Grounded instance:** qualified-name mangle (SR.1 lineage; text → canonical).
- **Component:** `resolve_query_entities` (3).
- **Boundary — referent locus = IN THE TEXT:** the referent is present in the input (`30sec_edit 21_publish`);
  resolution is a text→canonical matching problem. **Text-sufficient.** Fix = resolver hardening.

### 3.5 contextual / stateful
- **What goes wrong:** a **state-reference** ("this" / "last" / "current") is left unresolved.
- **Grounded instance:** defect #3 (open-sequence not injected at dispatch).
- **Component:** `resolve_query_entities` **dispatch** instance (3, `_step.py:568`) + the unwired `desktop`
  (`resolver.py:61`).
- **Boundary — referent locus = IN THE WORLD, not the text:** the input does **not** contain the referent
  ("this sequence"); resolution **requires** desktop/runtime state. **Text-insufficient.** Fix = wire `desktop`
  at the dispatch instance (TF.1-CONTRACT §4 — this is the first concrete Shape-A expression).

> **§3.4 vs §3.5 — the one-line test:** *Is the referent present in the text?* Yes → entity-resolution
> (text-sufficient, resolver hardening). No → contextual (world-referent, desktop-wiring). Both are component 3;
> "needs desktop state" is the *consequence* of §3.5's text-insufficiency, not the defining cause.

---

## 4. Tagging, clearance, and ranking **[the multi-tag rules]**

- **Tagging rule:** a defect carries **all** class-tags it exhibits. Classes are collectively exhaustive, not
  mutually exclusive. *Grounded: defect #2 carries both `routing` (§3.2) and `extraction` (§3.3) — one defect,
  two code sites, two fixes.*
- **A defect's full tag-set = its translation classes (§3) + its substrate-gap status (cell (d), §2).**
- **Ranking unit = the defect, NOT the class.** The defect is *the failing NL input + its observed wrong
  behavior — which may span multiple code sites and carry multiple tags* (defect #2 = one defect, two code
  sites; so "code site" is the wrong dedup key — DT R2). Class-frequency (how often each mechanism appears) is
  a **diagnostic lens**, not the slice-selector, because a multi-class defect would double-count across its
  classes. This is the same commitment as the clearance rule below: Phase 4 ships fixes that clear *defects*,
  and a class-frequency selector would pick the frequent tag, fix it, and leave the defect still failing.
- **Ranking is normative [N]:** *Phase 3b rankings are produced from **deduplicated defect instances**.
  Translation-class frequencies, co-occurrence matrices, and raw tag counts are **explanatory metrics only**
  and MUST NOT be used directly as prioritization scores* (Creative). *(Guards the statistical trap: "extraction
  appeared 43×, grounding 31× → extraction is priority #1" when the 43 came from the same 8 defects.)*
- **Clearance rule:** a multi-class defect is **cleared only when *every* tag is addressed.** A single-class
  fix (e.g. "routing only") does **not** clear a multi-tag defect (defect #2 still shows a wrong param until
  extraction is also fixed). A (d)-cell defect is additionally not end-to-end-cleared until the substrate gap
  closes. **Phase 4 must not claim a defect cleared on a partial tag-set.**

---

## 5. Detection spec — the TF.2 → TF.3a handoff **[two tiers]**

Every class ships a detection signal. Detectors split by what they need to run:

| Class | Detection signal | Tier | Falsification / FP surface |
|---|---|---|---|
| **routing / shadow** (§3.2-i) | `tools_filtered=1` **AND** a `tool_forced` marker present (`handlers.py:845` response field / `tool_forced_*` log family `:633/:666/:696/:764`) — the forced path ran and bypassed compile | **1 — substrate-observable** | a legitimate single-candidate disambiguation that forces correctly (corroborate with the labeled correct-tool when available) |
| **routing / wrong-selection** (§3.2-ii) | compile ran but selected a tool ≠ the correct tool | **2 — ground-truth-dependent** | needs the labeled correct-tool; no label → no "≠" to compute |
| **extraction** (§3.3) | explicit-form key token present in step-text, absent from extracted params | **1 — substrate-observable** | tokenization treats a non-key token as a key (e.g. a value containing `=`) |
| **contextual** (§3.5) | state-ref pattern ("this"/"last"/"current") present **and** `desktop` unavailable | **1 — substrate-observable** | an ambiguous word ("this shot list") that isn't a true state-ref |
| **substrate-gap** (cell (d)/(c)) | no registered tool/capability for the required operation (registry read; the R9-timewarp shape) | **1 — substrate-observable** | the capability exists under a name the matcher didn't recognize (→ that's a routing finding, not a true gap) |
| **decline-vs-misroute** (§2.1) | honest-decline net (`:407`) fired vs a dispatch occurred | **1 — substrate-observable** | — (it's a direct runtime fact) |
| **grounding** (§3.1) | value matches a known liftable example (D3 example inventory = the oracle) | **2 — ground-truth-dependent** | **the milestone's riskiest detector:** a *grounded* value that legitimately equals an example (real `30sec_21`) → false positive. 3a **must measure this FP rate** before 3b scores the class. |
| **entity-resolution** (§3.4) | resolved value ≠ correct canonical | **2 — ground-truth-dependent** | requires the labeled corpus to know the *correct* canonical; with no label there's no "≠" to compute |

> **3a detector-gap note (DT R1):** the routing/shadow signal is a **positive** marker (`tool_forced`), not an
> absence — deliberately. There is **no transport-uniform compile-*success* marker today**: `compile_complete`
> is emitted only on the SSE path (`handlers.py:1210`), and a silently-successful compile otherwise logs
> nothing (only `compile_error` logs, `:1197/:2023`). So "no compile line" cannot discriminate shadow from a
> clean single-tool compile — it's true of both. If 3b ever needs to detect a **non-forced** wrong-route
> beyond the labeled-corpus Tier-2 path, **3a must first add a transport-uniform compile-success line.**

- **Tier 1 (substrate-observable)** detectors are buildable **directly in 3b** from existing log/graph
  structure — no labeled corpus needed.
- **Tier 2 (ground-truth-dependent)** detectors are **blocked on 3a** — the **labeled reference corpus**
  (correct graph + resolved params per NL input; CR.1/E2E are *unlabeled* seeds) and, for grounding, the
  **measured example-fill false-positive rate**. **3a is the milestone keystone** (`[[feedback-audit-before-overfit]]`:
  no measure-first with an unvalidated instrument). 3b cannot gate Phase 4 on any Tier-2 class until 3a lands.
- **One artifact (framing-room reconciliation):** the labeled corpus, the per-param **provenance signal**
  (`grounded-from-intent` / `from-context` / `filled-from-example` / `unresolved`), and the operator-facing
  validation surface are **the same artifact** built once in 3a — it serves measurement (3b), diagnosis
  (class-tagging), and operator feedback (the gate) simultaneously.

---

## 6. What TF.2 does NOT do

Build any detector, build the oracle, the labeled corpus, or the example-fill FP measurement (all 3a); run the
measurement or rank defects (3b); ship any fix (Phase 4). TF.2 **names** the five classes (boundaries +
grounded instances + components), the verdict matrix (four cells), the multi-tag/clearance/ranking rules, the
two-tier detection spec, and the 3a handoff.
