# Operator Focus State — DISPOSITION & Surface Ruling (Q-focus-1/2/3 settled)

**Settled empirically on live Flame 2026.2.2 (project 013_13_13…portofino) across probes #1–#3. Q-focus-2 closed; Q-focus-1 ruled; Q-focus-3 vocab earns exactly one entry.**

## ⚖️ Surface ruling — the Python Console is selection-capable; my lean is OVERTURNED
Three passes ago I led with "the Console is selection-blind → the surface must be a UI-action hook." **Grounding overturned it.** Every operator focus signal that matters reads **on-demand** from any surface, including the Console. Creative's minimal-burden **Python Console choice stands** — selection is NOT deferred, and no UI-action surface is required for focus completeness. This is measure-first dissolving an architectural preference (the methodology working, not failing — `[[feedback-routing-vs-implementation-vs-reachability]]`, grounding-relocates-the-finding).

## The complete focus-state map (all on-demand readable unless noted)

| signal | accessor | proof |
|---|---|---|
| project / workspace / desktop | `flame.projects.current_project…` (`flame_context`) | probe #1 |
| active tab | `flame.get_current_tab()` → `"Timeline"` | probe #1 |
| open batch + iteration | `flame.batch.name` / `.opened` / `.current_iteration` | probe #1 |
| **batch node selection** | `flame.batch.selected_nodes` | probe #2 (`[]` empty) |
| **loaded sequence** | `flame.timeline.clip` → `PySequence:"30sec_edit 21"` | probe #2/#3 |
| **playhead segment ("this shot"/"current segment")** | `flame.timeline.current_segment` → `.shot_name`=`"tst_020"`, `.start_frame`=`1001`, `.selected`=True, `.type`="Video Segment" | probe #3 |
| current marker / effect / transition | `flame.timeline.current_marker` / `current_effect` / `current_transition` | probe #2 |
| **timeline multi-segment selection** | `flame.timeline.clip.selected_segments` → list of 7 PySegments; per-segment `.selected` also reads | probe #3 (decisive) |
| per-segment identity | `PySegment.shot_name` / `name` / `record_in/out` / `start_frame` / `source_name` / `version_uid` | probe #3 |
| **numeric playhead FRAME** | ❌ NOT reachable — no `current_time`/`current_frame`/`position` on `PyTimeline` | probe #2/#3 |

**The decisive evidence (timeline selection):** `clip.selected_segments` returned **7** selected PySegments; the per-segment walk independently showed exactly **7** segments `True` (tst_020–tst_080). Two paths agree. The probe's own `INCONCLUSIVE` verdict was a **false negative** — `.selected` returns a `PyAttribute` wrapper that the probe stringified to `"PyAttribute:True"` (a truthy string, so `is True` failed). Reading the raw sample past the computed verdict (the `compile_raw` lesson again) settles it: **YES, on-demand.**

## Q-focus-3 — the Tier-C-absence vocab earns exactly one entry
Only **numeric playhead frame** is unreachable, and it is **semantically subsumed** by `current_segment` (+ `.start_frame` / `record_in`). So the corpus records it `null` with reason `unreachable_api` — the SPEC's Tier-C-absence vocab earns its keep on exactly one real signal, and nothing the phase needs is lost (the segment/shot is the unit contextual refs resolve against, not the frame).

## Implementation note for the SPEC/plan (real, grounded)
**Flame scalar attributes return `PyAttribute` wrappers, not raw Python scalars** (`.selected` → `PyAttribute:True`, `.name` → `PyAttribute:30sec_edit 21`). The capture extractor must **unwrap `PyAttribute`** (str-and-parse, or the SDK's value accessor) before storing `extracted` — and `world_state.raw` should store the stringified form so unwrap bugs are recoverable (re-parse from raw). This is exactly why `raw` is the migration-if-wrong surface: a unwrap bug in `extracted` is free to fix; a missing `raw` capture is not.

## The focus-snapshot recipe (resolves the SPEC's first-class dependency)
One out-of-band read on every capture, Console-reachable, never threaded into `compile_intent()`:
```
project/workspace/desktop/tab   ← flame_context + flame.get_current_tab()
batch                           ← flame.batch {name, opened, current_iteration, selected_nodes, current_node}
loaded_sequence                 ← flame.timeline.clip {name, duration, frame_rate}
playhead_segment                ← flame.timeline.current_segment {shot_name, name, start_frame, type, record_in/out}
timeline_selection              ← flame.timeline.clip.selected_segments → [{shot_name, name, record_in/out} …]
current marker/effect/transition← flame.timeline.current_marker / current_effect / current_transition
playhead_frame                  ← null (unreachable_api)
```
All scalars `PyAttribute`-unwrapped; the whole structure stored verbatim in `world_state.raw`.

## Net for the room
- **Q-focus-1 (surface):** RULED — **Python Console is sufficient**; my UI-action-hook lean is withdrawn.
- **Q-focus-2 (reachability):** SETTLED — full focus state reachable on-demand except the (subsumed) numeric playhead frame.
- **Q-focus-3 (absence vocab):** one entry — `playhead_frame: null / unreachable_api`.
- The SPEC's focus-hook "first-class OPEN dependency" is now **resolved** to the recipe above. The discuss is ready to move to PLAN once Creative's capture-surface *ergonomics* pass (typed-prompt UX in the Console) clears.

## DT ratification + the meta-finding (banked — the instrument proved its own design principle on itself)
DT independently confirmed the ruling three ways (clip-level `selected_segments`=7, per-segment `.selected`=7 True on 020–080, `current_segment.selected`=True) and **owns the probe's verdict bug**: the comparisons ran on `_safe()`-stringified values (`"PyAttribute:True"`), so `value is True` and `isinstance(v, list)` both failed → the machine verdict said INCONCLUSIVE while the raw said YES.

The closure worth keeping: **the probe's derived verdict lied; the raw dump (sample + `clip_targeted`) corrected it.** That is the *exact* discipline the capture contract is built on — `raw` is the load-bearing, migration-if-wrong layer; `extracted`/derived views are recomputable and can lie. The instrument accidentally demonstrated its own architecture on itself, and it's the 3rd milestone instance of the same principle (TF.4 `compile_raw` blind-raise; TF.3b well-formedness re-source needing the observed raw; now the probe verdict). **Reuse note:** if this probe is repointed at another signal, unwrap `PyAttribute` *before* `_safe()`; not patched now — this question is answered.

Also falsified in passing: the "console focus clears the Timeline selection" worry — selection survived paste-and-run (7 segments still selected at read-time). Console focus does not drop selection.
