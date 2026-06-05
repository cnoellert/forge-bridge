# Context Pressure Instrument — Capture-Model Spec (typed context-scoped selection)

**Status:** DRAFT (Orch), 2026-06-04. Produced under ratified room rulings (i)/(ii)/(iii).
**Provenance:** mechanically derived from the production hooks at `~/GitHub/forge-pipeline/flame_hooks/forge_tools/` (source-verified; `projekt-forge` is TCC-blocked from this process). Cross-ref: live cursor `passoff-2026-06-04-phasex-context-pressure-first-capture`, `FOCUS-STATE-DISPOSITION.md`, probes #1–#4.

## 0. What this spec is — and is NOT

This is **the referent ontology + the reachability question for capturing it.** It is the instrument-expansion design that lets us *measure* the typed-selection hypothesis (ruling ii: measure before resolver build).

- It is **NOT the resolver.** The resolver is gated behind the measured narrowed-delta.
- It is **NOT a re-scope of Phase X** (ruling iii). Typed selection is the *dominant hypothesis*, not the new mission. The instrument stays broader than this one signal; loaded/playhead remain supporting signals, and other desktop state (active context, project, loaded sequence, playhead) stays in scope.
- The op→(context, type) map below is, per Creative, **the first draft of the eventual resolver's ontology** — recorded as such, not built upon yet.

## 1. The finding this corrects

The instrument's snapshot is centered on **loaded/playhead** state (`active_sequence = tl.clip.name`, playhead segment). Flame operations are centered on **selected typed objects**: every op declares `(context entry point(s), required selection TYPE, referent = the selected typed object's name)`, framework-enforced via `isVisible = _scope_<type>`. The tool literally does not appear in the menu unless a selection of the required type exists in the context. **Loaded ≠ selected.** *Loaded = operational context; selected typed objects = referential context; the hooks execute against the referential.*

## 2. The referent ontology (DERIVABLE — grounded now)

### 2.1 Context axis
| Context | Selection-bearing | Active-context signal |
|---|---|---|
| `media_panel` | yes (117 action entries) | `flame.get_current_tab()` (already captured as `current_tab`) |
| `timeline` | yes (108) | ″ |
| `batch` | yes (45) | ″ |
| `main_menu` | no (27) | n/a |
| `mediahub` | no (9) | n/a |

Total 306 hook action entries; ~270 in the 3 selection-bearing contexts.

### 2.2 Selection-type vocabulary (6 — finite, enumerable)
`PySequence` (14×, dominant) · `PySegment` · `PyClip` · `PyClipNode` · `PyOFXNode` · `PyWriteFileNode`.
(Excluded: `PyExporter`, `PyTime` — internal API types, not selection guards.)

### 2.3 Tool → (context, required selection type) map
Grounded from `def get_<ctx>_custom_ui_actions` + the `_scope_<type>` guards. "context-only" = `_scope_always`-style guard (no selection-type requirement — the referent axis does **not** apply).

| Tool | Context(s) | Required selection type |
|---|---|---|
| `forge_rename` | media_panel, timeline | `PySequence` |
| `forge_startframe` | media_panel, timeline | `PySequence` |
| `forge_roles` | media_panel, timeline | `PySequence` |
| `forge_reconform` | media_panel, timeline | `PySequence` |
| `forge_colourspace` | media_panel, timeline | `PySequence` |
| `forge_publish_sequence` | media_panel, timeline | `PySequence` |
| `forge_publish_shots` / `_v2` | media_panel (+timeline) | `PySequence` |
| `forge_plate_publish` | media_panel, timeline | `PySequence` |
| `forge_publish_traffik` | media_panel, timeline | `PySequence`, `PySegment` |
| `forge_openclip` | media_panel, batch, main_menu | `PyClip` (`_scope_clip`) **and** context-only (`_scope_always`) |
| `forge_import_write_node` | batch | `PyWriteFileNode` |
| `forge_denoise` | batch | `PyClipNode`, `PyOFXNode` |
| `forge_layout` | media_panel, batch, main_menu | context-only / guard style unverified |
| `forge_stream` | media_panel, timeline, batch | guard style unverified |
| `forge_switch_grade` | timeline | guard style unverified |
| `forge_bridge` | main_menu | none (server toggle) |

**Dominant pattern:** sequence ops on a selected `PySequence` in media_panel/timeline — exactly the `"rename this sequence"` case (R3/R4). Batch ops key off selected batch nodes. Three tools' guard styles are unverified (read their `isVisible` before relying on them).

### 2.4 The referent rule — a selection satisfying an operation-defined GUARD (refined 2026-06-04, DT+Creative)
For a deictic op, **referent = the selected object that satisfies the op's `isVisible` guard, in the active context, `.name`.** The guard is NOT uniformly a type check — **type identification is heterogeneous across the pipeline**:
- **nominal type** — `isinstance(item, flame.PySequence)` (forge_rename, most ops).
- **behavioral / duck-typed** — `hasattr(s, "record_in")` to mean "a timeline segment" (forge_switch_grade, confirmed). `PySegment` is in the vocabulary but identified *behaviorally*, not by class.
- **cardinality-constrained** — some ops require `len(segs) == 1` (single-select).

∴ The fundamental referent is *a selection satisfying an operation-defined predicate*, not merely a selected type. A capture/analysis model that enumerates by `isinstance` alone would mis-type or miss the duck-typed ops. This is what S4 compares the compiled value against — and (see §4) what the snapshot must be able to *reproduce*, not just read.

## 3. What the instrument must capture (capture-side change)

Per active context, capture the **typed selection set**: `[{type, name}]` for each selected object. Minimum viable:
- `selection_typed`: list of `{type: "PySequence", name: "..."}` from the active context's selection.
- Keep `active_sequence`/`current_shot`/`current_segment_name` (loaded/playhead) as **supporting** signals — do not remove (ruling iii: stay broad).

`world_state.raw` keeps the faithful read; `extracted` gains `selection_typed` (the analysis surface). The captured/authored lock is unchanged — capture never authors.

## 4. ⚠ THE REACHABILITY **AND RECONSTRUCTABILITY** QUESTION (the crux — PROBE-GATED)

**The hooks RECEIVE selection (Flame pushes the `selection` param to `isVisible`/`execute`). The instrument snapshot must READ it (pull) standalone (SGTK console / `bridge.execute`) — a fundamentally different access path.** Per the §2.4 refinement there are now TWO independent unknowns (Creative):
1. **Reachability** — can the snapshot ACCESS the current selection per context?
2. **Reconstructability** — can the snapshot REPRODUCE the op's guard predicate outcome (nominal type / duck-typed predicate / cardinality)? i.e. can it determine the selection satisfies the *same guard* the operation would have applied?

The real question is no longer "can we get the selection?" but **"can we determine the selection satisfies the op's guard?"** Reachability is partly unproven, and one path is already known-hard:

| Context | Pull-side read | Status — **updated by Probe #5 (2026-06-04 live)** |
|---|---|---|
| `media_panel` | `flame.media_panel.selected_entries` | **✓✓ PULL CLEAN** — collection returns selected `PySequence` (`'30sec_edit 21'`), count:1; `isinstance` IDs `[PySequence, PyClip]`, `.name` present. Reachable AND reconstructable. **This is the dominant failure case → capture-expansion grounded + low-risk.** |
| `timeline` | segment-walk on `seg.selected` (`_selection()`); `clip.selected_segments` | **⚠ UNVERIFIED / SUSPECT** — not exercised (clip None this run). Shares batch's affliction: `bool(seg.selected)` (`_focus.py:147`) is the IDENTICAL construct to batch's truthy-for-all `bool(n.selected)`; `clip.selected_segments` non-iterable (probe #4). Records #1-8's 31 empty `''` entries are CONSISTENT WITH THE BUG (not proof the filter works). Needs a clean-API hunt or push. |
| `batch` | `batch.selected_nodes`; node-walk `bool(n.selected)` | **⚠ REACHABLE-BUT-MESSY** — `selected_nodes` non-iterable (confirms probe #4), repr holds the right answer `[<PyOFXNode>]`; node-walk returns ALL 11 (`bool(n.selected)` truthy-for-everything = PyAttribute-flag bug). Data present, clean access defeated. `isinstance` reconstructs once you HAVE the node. Not in the failure corpus. |

**Probe #5 + #5b verdict (fork resolved → PULL):** the non-iterable PyAttribute is not opaque — `dir()` exposes `get_value()` (returns the real selection); container paths (`len`/subscript/`list()`/iterate) `TypeError`, `get_value()` works. ⇒ **pull viable ALL THREE: media_panel `selected_entries`; timeline `clip.selected_segments.get_value()`; batch `selected_nodes.get_value()`. The push-at-hook fork is CLOSED (§5).** (Batch returned `[]` the run nothing was selected — confident by mechanism + probe #5 run #5; one batch-nodes-selected run = zero-asterisk, non-blocking, batch not in the failure corpus.) **Also fixes a CURRENT bug:** the timeline capture uses the broken always-truthy `bool(seg.selected)` walk (`_focus.py:147`) → existing 8 records' `selection` field is unreliable; swap to `selected_segments.get_value()`.
**Reconstructability lesson:** `isinstance` is the clean discriminator (prefer it for type-ID); duck-typed `hasattr` is near-universal (true for the sequence AND all 11 nodes) → loose guards are safe ONLY because context-scoped. Capture model: `isinstance` for type-ID; lean on context-scoping for the loose ones.

### 4.1 Required: PROBE #5 (selection reachability **AND classification reconstructability**) BEFORE the capture expansion lands
Mirror the probes #1–#4 discipline (the surface decision and `FOCUS_SNAPSHOT_PY` were settled by probes, not assumption). Probe #5 must, on live Flame, for each selection-bearing context, attempt to pull the current selection and **dump raw + feed through an assembler + self-check** (raw is the truth; a derived verdict can lie):
1. `media_panel`: probe `flame.media_panel.selected_entries` (and alternatives) → typed `{type, name}`.
2. `batch`: find an iterable path (e.g. iterate `batch.nodes` filtering `.selected`) since `batch.selected_nodes` is non-iterable.
3. `timeline`: extend the working segment-walk to capture the selected `PySequence` + the duck-typed `PySegment` (`hasattr(s,"record_in")`).

**Acceptance (BOTH must hold per context):**
- **(a) Reachability** — the selection is pull-readable and unwraps to `{type, name}`.
- **(b) Reconstructability** — for each guard style present (nominal `isinstance`, duck-typed `hasattr(...)`, cardinality `len(...)==1`), the snapshot reproduces the *same predicate outcome* a hook would compute on the same selection. This is the subtly different, now-primary test: not "did we get the selection?" but "can we determine it satisfies the op's guard?"

Either failing → record `unreachable_api` (a) / `unreconstructable_guard` (b) with reason — the honest-absence pattern, never a silent miss.

## 5. Push-at-hook fork — ✅ CLOSED by Probe #5b (2026-06-04)

**Pull is viable across ALL THREE contexts via `get_value()` (media_panel `selected_entries`; timeline `clip.selected_segments.get_value()`; batch `selected_nodes.get_value()`). The push-at-hook fork is CLOSED — the instrument does not need it.** Creative's hooks-as-resolver-ontology insight STILL stands, but it concerns the eventual *resolver* (which may live in hooks), NOT the *capture mechanism* (the instrument pulls standalone). Original fork reasoning kept below as archaeology:

### 5.1 (archaeology) Fallback architecture — was: NOTE for the room, not decided

If probe #5 shows pull is unreliable, the alternative is to **capture selection at the hook (push)** rather than via standalone snapshot — the hook gets `selection` for free. This is *also* how the eventual resolver would operate (it lives in hooks), connecting to Creative's "thinner-resolver / hooks-as-ontology" read.

The §2.4 heterogeneity **strengthens** the push case: the hook already POSSESSES the exact predicate semantics — it *is* the guard — so push inherits Flame's selection AND the op's own classification, sidestepping the snapshot having to re-derive predicates (duck-typed, cardinality) it may not reliably reconstruct.

**But do NOT pre-elevate push over pull** (Creative): Probe #5 tests reachability (a) and reconstructability (b) as *independent* unknowns. If both succeed → pull stays viable. If both fail → push is near-inevitable. If reachability succeeds but reconstructability is messy → *that* is where the real architectural debate is. **The probe decides; the fork stays open until it runs.** Capturing at the hook is also a larger change to the current Console two-round-trip topology and edges toward resolver territory — deferred pending the probe.

## 6. Analysis-side change (S4)

The `_Dimension` focus model gains the selection axis as **primary**, loaded/playhead as **fallback** (extending the four-gap patch's `focus_keys` tuple):
- sequence: `focus_keys = (selected_PySequence_name, active_sequence)` — selected-typed first, loaded fallback.
- shot/segment: `(selected_PySegment_name, current_segment_name, current_shot)`.
- batch-node dimensions: new, keyed on selected `PyClipNode`/`PyOFXNode`/`PyWriteFileNode`.

The four-gap patch is **not reverted** — its compiled-side fixes (#3 `shot_id`, #4 placeholder) and empty-handling (#1) are axis-agnostic and survive; only the focus-*signal* priority changes (selected-typed becomes primary).

## 7. Sequence (under ruling ii — measure first)

1. **This spec** (the ontology) — ✅ done.
2. **Probe #5 + #5b** (reachability + reconstructability) — ✅ DONE: pull viable all three via `get_value()`; push fork closed (§4/§5).
3. **Extend `FOCUS_SNAPSHOT_PY` + `assemble_world_state`** — ✅ UNBLOCKED (greenlight-gated build): 3 `get_value()` paths + `isinstance` typing; project `selection_typed`; **AND fix the current broken `bool(seg.selected)` walk** (`_focus.py:147` → `selected_segments.get_value()`).
4. **Extend S4 dimensions** to selected-type-in-context (§6).
5. **Re-capture** R3/R4-style ops with the corrected axis.
6. **Q3 cost-anchoring (blind) → first MEASURED narrowed-delta** ("how often does typed selection explain failures loaded/playhead cannot?").

The recall-plausibility pass on the existing 8 records (does R3/R4 explain once the selected `PySequence` is treated as referent?) is offline and may run now — **suggestive, NOT the gate number** (the capture never recorded selection).

## 8. Forward-pointer — the resolver's output is an ALREADY-SHIPPED federation contract (added 2026-06-05, DT)

This spec's referent ontology is, in federation terms, the bridge-side knowledge that produces a **`ReferenceResolution`** — a contract that **already exists** in `forge-contracts` v0.1 (`src/forge_contracts/references.py`). When the live re-capture re-opens this spec, build toward the contract, not around it:

- **`ResolutionStatus = Literal["resolved", "unresolved", "ambiguous"]`** maps onto S4's analysis — **partially, not 1:1** (room redline, 2026-06-05): success → `resolved`; flag `wrong_resolution` / authored `wrong_referent` → `resolved`-but-wrong (the ratify-caught case; the two names are a taxonomy drift to reconcile); `unresolved_reference` → `unresolved`; `unreachable_api`/`unreconstructable_guard` → `reason_code` (honest-absence). **The `ambiguous` + `candidates[]` arm has NO S4 path today** — `_selected_value` (`_analysis.py:125`) returns a single scalar referent; the comparison is scalar `compiled != focus` (:186). That arm is a **measurement hole to close** (record `ambiguous`+`candidates` when ≥2 selections of the required type match — collapsing it into `unresolved` loses the signal), not an implemented mapping. The instrument is, unframed, a **measurement pass for bridge's `ReferenceResolution` quality** — which strengthens the federation's **Phase 7 E2E Demonstrator** (reference recording in `plan → invoke → record lineage`). It does **NOT** gate **Phase 5 (Bridge Discovery)** — that is capability-*family* routing (FEDERATION-PROOF-SEQUENCE.md:131-154), orthogonal to deictic referent resolution. (De-inflating this is deliberate: overstating federation-criticality is the lever that would license hurrying the blind Q3 measurement.)
- **Two implications, neither changing the measure-first discipline or the blind Q3 threshold:**
  1. If Q3's R clears BUILD, the resolver **emits `ReferenceResolution`**, not a bridge-internal shape.
  2. The §2.3 op→(context, required-selection-type) map becomes a **pipeline-*declared* referent requirement that bridge consumes** — NOT reverse-engineered from hook source. Reading `~/GitHub/forge-pipeline/flame_hooks/forge_tools/` to derive §2.3 (this spec's provenance) is an interim that violates the ADR-000 no-sibling-internals boundary.
     **✅ CONTRACTS RULING — forge-contracts `44f8488` "docs: clarify reference resolution vocabulary" (2026-06-05).** The contracts group ratified the call (verified green: contracts 8 · vision 4 · pipeline 21+1-unrelated-warn):
       - **v0.1 does NOT define a typed input-side referent-requirement field.** (My earlier "extending `CapabilityDeclaration`" was wrong — no schema extension at v0.1.)
       - **Interim home = provisional declaration in `CapabilityDeclaration.input_schema` or `.metadata`** (`ContractModel` is `extra="allow"`, so it tolerates this without a schema change).
       - **If it graduates to shared vocabulary later it MUST be predicate-shaped, not bare type names** — real guards are nominal (`isinstance`) / duck-typed (`hasattr`) / cardinality (`len==1`) / **AND combinations thereof** (the ruling's explicit addition, beyond the room's §2.4 three).
       - **Directive back to bridge:** *use metadata/input_schema; do NOT reverse-engineer pipeline internals; predicate-not-type if it graduates.*
     **Open transition (gated behind Q3, NOT a now-task):** the declaration does not exist yet — pipeline has not populated referent requirements (which is *why* §2.3 was hook-derived). So §2.3 stays a **named interim** — reverse-engineered, now *governed* (target + forbidden direction set) but not yet *closed* — until pipeline declares provisional requirements in its `CapabilityDeclaration`. The resolver consuming them is itself gated behind the blind Q3 BUILD verdict, so the pipeline-declaration step is forward-guidance for IF/WHEN we build, not urgent. Where a predicate can't be declared/reconstructed, the resolver emits `unresolved` + `reason_code="unreconstructable_guard"` (+ authored `message`) rather than flatten-guess.
     **Also adopted by `44f8488` (Creative's catches, now contract-documented):** `ReferenceResolution.candidates` is preserved as **real, not speculative**; `reason_code` is the machine token and `message` is human-facing text that **should be populated for human-surface unresolved/ambiguous results.**

Full context + cross-voice asks: `CONTEXT-PRESSURE-INSTRUMENT-FEDERATION-SURFACING.md`. Constitution: `forge-contracts/docs/adr/ADR-000-ecosystem-constitution.md` + `FEDERATION-PROOF-SEQUENCE.md`.
