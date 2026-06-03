# TF.3a — Live Capture Findings (the measure-first payoff)

**Run:** 2026-06-02, `qwen2.5-coder:14b` @ localhost, 11 live cases through the real compile path.
**Headline: the capture REFUTED most archaeology-based predictions.** The labels in `_authored.py` were
predictions from the E2E-01 / D-series archaeology; the live measurement shows a **different failure
distribution**. This is exactly why 3a measures before 3b ranks — and the surprise is large enough to go to the
room before relabeling.

---

## The dominant failure was NOT predicted: chain-step serialization

**~5 of 11 live cases** compiled the tool name and its args as **two separate chain steps** —
`["flame_rename_shots", '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}']` — so the params never
attach to the tool → dispatch fails `UNRESOLVED_REQUIRED_PARAM`. **Verified real (not a parse artifact):**
`_parse_compile_output` faithfully represents the model's output; the model emitted them separate (the compile
prompt says "use `->` between ordered steps" but never specifies args go *inline* — so the model treats the
args object as its own step). Cases: **L2, L6, L7, L8, L11**.

**This is a serialization/format failure** (the "protocol serialization" domain — qwen Bug-D family), and **none
of the five taxonomy classes name it cleanly.** It is the single most common failure in the corpus — and the
milestone planned its top Phase-4 work around example-salience, which the capture shows is **rare**.

## Confirmed live: space-mangling (the carry-forward)
`"30sec_edit 21"` → `"30sec_21"` (truncated at the space, dropping `_edit` — L2, L7) or `"30sec_edit_21"`
(space→underscore — L9). The space-bearing qualified-name defect is **real and live** (entity-resolution).

## Grounding RELOCATED — absent where predicted, present where not
- **L6** ("rename … prefix tv"): predicted a `prefix=noise` lift. **Observed `prefix="tv"`** — the operator's
  value. **NO lift.** Grounding REFUTED here.
- **L9** ("set start frames", no value): predicted a `default_frame=1001` lift. **Observed `default_frame=1`** —
  not the `1001` example; an invented default. Manufactured-certainty, but **not example-salience**.
- **L8** ("rename *this sequence*"): predicted pure contextual. **Observed `sequence_name="30sec_21"`** — the
  model **lifted a docstring example value for the contextual ref.** *This* is example-salience (TF.1-CONTRACT
  §5) — but it manifests on the **contextual seam** (no value given → lift), not on explicit-value inputs.

## (c) honest-decline REFUTED
**L10** timewarp: predicted (c) honest-decline against the real capability gap. **Observed
`forge_list_shots → forge_get_shot`** (`tool_selection_ambiguous`) — the system **hallucinated a route** to shot
tools rather than declining. **The capability gap does NOT produce honest decline; it produces a mis-route.**
The (c) cell is currently **unpopulated by real behavior.**

---

## Per-case reconciliation (predicted → observed → verdict)

| case | predicted | observed graph + abort | verdict |
|---|---|---|---|
| A1.1 batch groups | (a) | `flame_list_batch_groups {}` | **HOLDS** (a) |
| A1.2 current desktop | (a) | `flame_list_desktop {}` | **HOLDS** (a) |
| A1.3 reels | routing | `flame_list_desktop` (wrong) | **HOLDS** routing/wrong-selection |
| A1.4 current reels grp | routing | `flame_get_batch_reels` (wrong) | **HOLDS** routing |
| L1 list projects | routing | `compile_error` / `CompileInvalidChainShape`, empty | **FLIP** → compile-shape failure (not mis-select) |
| L2 duration in frames | routing+entity | `flame_preview_start_frames` (wrong) + `30sec_edit 21→30sec_21` + args-split | **HOLDS+** routing+entity, **+serialization** |
| L3 path to shot 10 | routing+entity | `forge_list_shots → forge_get_shot` (wrong family) | **HOLDS** routing+entity |
| L4 duration of shot 10 | routing+entity | `forge_list_shots → forge_get_shot` | **HOLDS** routing+entity |
| L5 gen_0460 iteration | routing+entity | `forge_get_batch_iterations` (non-existent) +`format_result`, ToolError | **HOLDS** routing(tool-unknown)+entity |
| L6 rename prefix tv | grounding | `flame_rename_shots` + `prefix=tv` (no lift) + args-split | **FLIP** → serialization (not grounding) |
| L9 set frames | grounding(1001) | `flame_set_start_frames default_frame=1` + `30sec_edit_21` + unauthorized_mutation | **FLIP** → manufactured-value + entity (not example-lift) |
| L7 rename prefix noise | routing+extraction | `flame_rename_shots` (CORRECT) + `30sec_edit 21→30sec_21` + args-split | **FLIP** → entity + serialization (not routing) |
| L8 rename this sequence | contextual | `…→flame_rename_shots sequence_name="30sec_21"` (lifted for "this") | **HOLDS+** contextual **+grounding** |
| L10 timewarp | (c) decline | `forge_list_shots → forge_get_shot`, ambiguous | **FLIP** → translation-FAIL routing (no decline) |
| L11 current batch | (a) | `flame_list_batch_groups` (correct) + prose step "extract …" | **FLIP** → right tool + spurious prose step (serialization) |

**6 of 11 live cases flipped; L8 gained a tag; the (c) cell emptied.** The coverage report's "green except (d)"
is **invalid** — it counted predicted labels, not observed reality.

---

## Implications (for the room — NOT a silent relabel)

1. **The taxonomy is missing a class.** Chain-step **serialization/format** (args detached, prose steps, invalid
   shape — L1, L2, L6, L7, L8, L11) is the dominant failure and isn't cleanly grounding/routing/extraction/
   entity/contextual. TF.2's five classes need a 6th, or "extraction" must be widened to "params didn't attach"
   (whether unparsed-from-text OR detached-in-serialization).
2. **Phase-4 ranking is empirically inverted.** The archaeology said example-strip is the top slice; the
   measurement says **serialization + space-mangling** dominate and example-salience is rare (and lives on the
   contextual seam). Measure-first just did its job — it stopped a mis-prioritized Phase 4.
3. **The (c) cell needs a real decline.** The system hallucinates routes on capability gaps; restoring honest
   decline is itself a translation-quality objective (TF.1-CONTRACT §5) — and there's now *zero* live (c).
4. **Labels must be relabeled against observed**, then re-validated. The corpus is not yet a valid instrument —
   its labels are refuted predictions. This is the real Step-4 work, and it's interpretation (room/operator
   judgment), not mechanism.

**Recommendation:** take findings 1–3 to the room (DT/Creative) — the taxonomy 6th-class question and the
ranking inversion are room-level. Then relabel `_authored.py` against observed and rebuild.
