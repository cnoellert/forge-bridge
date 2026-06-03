# TF.4 Quality Fixes — Slice #1 Framing: chain-step serialization / well-formedness

**Status:** framing settled (writer's-room: Orch draft → Creative → DT → Creative). Code-ready.
**Date:** 2026-06-02. **Base:** `main @ f462fcd`.
**Scope of this slice:** the **detached-args** well-formedness defect only. Prose/non-tool-step normalization is **Slice #2** (see Forward-pointers). Content re-ranking (#2–#5) is held until the gate clears.

This slice is the first TF.4 quality fix, and the first v1.13 touch of **runtime** code (compile prompt + compile-output parse) rather than the measurement instrument. It is ranked #1 by the TF.3a live capture — not by archaeology — because chain-step serialization was the dominant live failure (`TF.3a-CAPTURE-FINDINGS.md`).

---

## The defect (grounded)

The compile system prompt (`router.py:426`, `_default_compile_system_prompt`) tells the model to separate ordered steps with `->` but **never says a step's args travel inline with its tool name**. So qwen2.5-coder:14b emits the tool and its args as *two separate steps*:

```
flame_rename_shots
{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}
```

The intent is present, the tool is correct, the values are correct, the ordering is correct. **What is broken is the transport grammar between compile and execution.** This is the protocol-serialization domain — the same family as the existing qwen Bug-D `tool_calls` salvage (`_adapters.py:121-148`), a sibling at a different layer (Bug-D salvages the *provider response* at the adapter; this salvages the *compile-output parse*). The parser (`_parse_compile_output`, `router.py:504`) is **faithful** — it represents exactly what the model emitted; it is not the bug.

### The defect has two manifestations (DT seam #2.1)

The same detached-args defect surfaces differently across the parser's two branches:

| manifestation | branch | what happens | reaches a step-list? |
|---|---|---|---|
| **pass-through** | text `->` (`_top_level_chain_segments` → `parse_chain`) | orphan `{…}` becomes its own segment → reaches dispatch as an argless tool → `UNRESOLVED_REQUIRED_PARAM` | yes |
| **raise** | JSON-list (`_structured_compile_step_text`) | bare-args dict has no `tool_name` → raises `CompileInvalidChainShape` (`router.py:490-493`) | no — dies mid-parse |

Both are the same defect (args detached from their tool). The fix must cover both.

---

## The fix — two prongs, B load-bearing

**Prong A — compile-prompt grammar** (`_default_compile_system_prompt`, the *model* layer). Spec the single-step grammar: each step is `tool_name arg=value arg=value`, args inline; an args object is never a standalone step. This is **prevention**.

**Prong B — `normalize_chain_shape()` salvage pass** (the *dispatch substrate*). Deterministically reattach a bare args step to its tool. This is **recovery**, always-on, model-independent. **B is load-bearing.** Every prompt-layer intervention this milestone-family reached *some* register and not always the targeted one; we do not let the well-formedness gate depend on a model-behavior change we cannot prove sticks. A reduces how often B fires (cheap, worth doing); B is the one that must be correct.

### The salvage invariant (Creative, verbatim — binding)

> **Salvage may only reattach arguments already present in the emitted chain. It may never synthesize, merge, infer, or reorder parameters.**

This keeps the operation firmly in **normalization** territory, not interpretation. The no-synthesis doctrine alarm is correctly silent: it reattaches args the model *did* emit, at compile-time, with the mutation path (preview → ratify → apply, `AssentRecord`) untouched.

### Ambiguity policy (Q1 — settled, conservatism must be *proven*)

Reattach **only** when exactly one attachment interpretation exists:
- a tool-name-only step (no args), **immediately** followed by a bare args object → **reattach**.
- everything else stays malformed and observable (`well_formed=False`).

Negative cases that **must stay malformed** (proven by unit pairs, same positive+negative discipline locked for the Tier-1 detectors):
- orphan args with no preceding tool step → stays malformed.
- a tool step that already has args, followed by a second args object → stays malformed.
- multiple possible attachment targets → stays malformed.

Salvage that over-reaches would manufacture well-formed graphs from genuinely ambiguous output — a quieter failure than leaving them malformed.

### Where salvage lives (Q2 — settled)

A **distinct named pre-pass** — `normalize_chain_shape()` — not embedded in the parser. The parser stays a faithful representation layer; the salvage is independently testable, observable, and removable. Code structure mirrors the doctrine (`[[feedback-wellformedness-precedes-content]]`):

```
raw compile output → decode (JSON-list | text segments) → normalize_chain_shape() → parse → dispatch
```

Two grounded requirements (DT):

1. **The pass must fire before the raise.** A purely post-parse salvage catches the pass-through manifestation and misses the raise manifestation (which dies at `router.py:490-493` before any step-list exists). `normalize_chain_shape()` must operate on the decoded steps/segments in **both** the JSON-list and the text-segment paths, before step-text construction and before the raise.
2. **The pass must emit observability.** Once salvage runs, `compute_well_formed` sees clean input and returns `True` — erasing the evidence the graph was malformed. To keep Prong A and Prong B measurably distinct, the pass records onto `ObservedTrace`:
   - `salvage_applied=True`
   - `original_reason="detached_args"`
   Then `salvage_applied=True` is the substrate-guarantee evidence (B did the work); a falling `salvage_applied` rate across future captures is Prong A's additional win. Without these fields A and B are indistinguishable.

---

## Success criteria — two metrics, never conflated

The milestone criterion is **"the substrate no longer hands malformed graphs to dispatch,"** never "the model learned."

**Metric A — well-formedness recovery rate (load-bearing, deterministic).**
The gate-clearing metric. Decides whether Slice #1 succeeded.

**Metric B — detached-args emission frequency, post-prompt-update (secondary, ecological).**
Measures whether Prong A helped. Earns Prong A credit if it succeeds.

The 2×2 that proves they are separate:
- Prompt fails + salvage succeeds → **slice succeeds.**
- Prompt succeeds + salvage never fires → **slice succeeds.**

Prong B proves correctness; Prong A reduces incidence. One must never be mistaken for the other.

### The deterministic bar (model-free substrate proof)

DT's correction: the bar must **not** ride a fresh qwen run (sampling variance / Prong-A success would let `well_formed` go `True` without salvage firing — confounding the very model-dependence the seam exists to escape, `[[feedback-baseline-drift-invalidates-controls]]`).

**Grounded constraint:** `ObservedTrace` has **no raw field** (confirmed — keys are `observed_graph, observed_resolved_params, outcome, abort_reason, tool_selected, tool_forced, tools_filtered, capture_provenance, well_formed, well_formed_reason`). So "replay raw" cannot run literally. But `observed_graph` preserves the malformed **step-list** for the pass-through manifestation, which is the actual structure the substrate consumed and classified `well_formed=False`. Replaying *that* through `normalize_chain_shape()` is a substrate proof, not weaker evidence than raw replay.

**The bar (Creative wording — coverage of the defect family, not the historical raw-loss accident):**

> All detached-args manifestations proven deterministically:
> - **corpus replay** for preserved malformed graphs (the 4 pass-through cases in `reference/cases.jsonl`) — assert `well_formed` flips `False→True`, `salvage_applied=True`, `original_reason=detached_args`, resulting graph structurally valid.
> - **synthetic fixtures** for malformed graphs the original instrumentation did not preserve (the 1 raise-shape case, whose raw was discarded at the raise) — construct the JSON-list input `["flame_rename_shots", {"params":{…}}]` directly and assert normalize-before-raise yields a well-formed graph, plus the Q1 negative cases.

No Ollama, no daemon, no Flame, no sampling variance.

The **live re-capture is the secondary/ecological win only** (does the in-the-wild rate drop), exactly parallel to how Prong A is "additional win, never the bar." It depends on the live stack; the deterministic bar does not.

---

## Scope boundary (Q3 + the prose-step split)

**In scope (Slice #1):** the **detached-args** defect family — 5 malformed cases (4 pass-through, corpus-replayable + 1 raise-shape, synthetic-fixture-covered). One crisp invariant.

**Out of scope — Slice #2:** the **prose / non-tool-step** defect (1 case: a trailing `"extract currently open batch group name"` step, `well_formed_reason="non_tool_step"`). This is **not** detached args; it is a spurious natural-language step, and "when is a non-tool step safe to drop?" is a *judgment surface*, not a structural repair (junk vs. intended semantic step vs. commentary). Bundling it would force `normalize_chain_shape()` to carry two invariants with two ambiguity surfaces under one banner — the conflation the two-metric discipline exists to prevent. Slice #2 gets its own ambiguity analysis, conservatism rules, and measurement.

**Held (content, post-gate):** L8's grounding-on-contextual-seam re-judgement and the provisional #2–#5 content re-ranking. Content frequencies are only trustworthy *after* the gate clears (they are currently "what survived malformation"). Re-judging now measures behind the very gate this slice closes — repeating the archaeology-first mistake TF.3a exists to prevent.

---

## Instrument touch this slice

- **Add `compile_raw` (str|None) to `ObservedTrace`** (`_schema.py` + `_capture.py`). Cannot retroactively recover the lost raw for the existing raise-shape case, but freezing raw forward makes every future raise-shape case deterministically corpus-replayable (incl. the post-gate re-capture). Stops the recurrence.
- **Add `salvage_applied` (bool) + `original_reason` (str|None) to `ObservedTrace`** (the Q2.2 observability fields).
- Public `forge_bridge.__all__` stays **19**. `translation_oracle.__all__` (currently **18**) absorbs any new symbol; no new external libraries.

---

## Forward-pointers (named, not lost)

- **TF.4 Slice #2 — prose / non-tool-step handling.** Separate ambiguity analysis, conservatism rules, measurement. The 1 `non_tool_step` corpus case is its anchor.
- **Post-gate full-corpus re-capture pass.** The deliverable that converts the roadmap's *provisional* #2–#5 into *measured*: (a) re-judges L8 + the contextual/example-salience coupling, (b) fires the #2–#5 re-ranking firm, (c) confirms the ecological detached-args rate-drop (Metric B). Depends on the live stack (Ollama + Flame + daemon, currently torn down). Its own pass — Slice #1 ships the gate + the deterministic bar.
- **Space-mangling** (`30sec_edit 21` → `30sec_21`) — entity-resolution, TF.1 Phase-4 **defect #2**. Live-confirmed, still parked.
- **(c) honest-decline restoration** — the capability gap produces a mis-route, not a decline; restoring honest decline is a translation-quality objective (TF.1-CONTRACT §5). Cell (c) stays empty until built; do not fabricate a case.
- Standing: bootstrap-console-executor gap (`[[project-bootstrap-console-executor-gap]]`); `/gsd-secure-phase` 26.

---

## Grounding appendix — the 6 malformed cases (corpus @ f462fcd)

From `forge_bridge/translation_oracle/reference/cases.jsonl`, the `well_formed=False` rows decompose as:

| input | `well_formed_reason` | `observed_graph` | family | bar coverage |
|---|---|---|---|---|
| duration in frames of 30sec_edit 21 | `detached_args` | `["flame_preview_start_frames", "{…}"]` | detached-args (pass-through) | corpus replay |
| rename the shots on 30sec_21 prefix tv | `detached_args` | `["flame_rename_shots", "{…}"]` | detached-args (pass-through) | corpus replay |
| rename shots on 30sec_edit 21 prefix noise | `detached_args` | `["flame_rename_shots", "{…}"]` | detached-args (pass-through) | corpus replay |
| set the start frames on 30sec_edit 21 | `detached_args` | `["flame_set_start_frames", "{…}"]` | detached-args (pass-through) | corpus replay |
| list the projects | `invalid_chain_shape` | `[]` (raw lost at raise) | detached-args (raise) | **synthetic fixture** |
| current batch (name) | `non_tool_step` | `["flame_list_batch_groups", "extract …"]` | prose/non-tool | **Slice #2** |

**5 detached-args (4 + 1 raise) → Slice #1. 1 prose → Slice #2.**

### File sites
- compile prompt: `forge_bridge/llm/router.py:426` (`_default_compile_system_prompt`)
- compile-output parse: `forge_bridge/llm/router.py:504` (`_parse_compile_output`); JSON-list raise at `:490-493` (`_structured_compile_step_text`)
- well-formedness detector: `forge_bridge/translation_oracle/_detect.py:18` (`compute_well_formed`)
- capture: `forge_bridge/translation_oracle/_capture.py` (`observed_trace_from_compile_outcome`)
- re-measure harness: `forge_bridge/translation_oracle/run_captures.py`
- Bug-D sibling precedent: `forge_bridge/llm/_adapters.py:121-148`
