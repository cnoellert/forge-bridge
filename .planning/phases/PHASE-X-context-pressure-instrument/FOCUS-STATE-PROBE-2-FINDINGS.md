# Focus-State Probe #2 — Findings (the lean is overturning, as grounding should)

**Q-focus-2 is now ~90% settled. The remaining 10% is the decisive one (timeline selection on-demand), open only because of a probe-resolver bug — probe #3 closes it.**

## `PyTimeline` is a concrete object — here `dir()` IS reliable
`dir(flame.timeline)` public focus surface = `clip`, `current_effect`, `current_marker`, `current_segment`, `current_transition`, `type`. That is the whole player-focus API. Findings:

| signal | reachable on-demand? | accessor |
|---|---|---|
| **active/loaded sequence** | **YES** | `flame.timeline.clip` → `PySequence:"30sec_edit 21"` |
| **current segment (playhead-over)** | **YES** | `flame.timeline.current_segment` (semantic "this shot"/"current segment" — better than a frame #) |
| current marker / effect / transition | YES | `flame.timeline.current_marker` etc. |
| **numeric playhead frame** | **NO** | no `current_time`/`current_frame`/`position` on PyTimeline — *the frame number is unreachable; the segment is the unit, and it's reachable* |
| **batch node selection** | **YES** | `flame.batch.selected_nodes` (returned `[]`); `batch.current_node`, `batch.cursor_position` also read |
| **timeline multi-segment selection** | **OPEN** | resolver bug (looked for `.sequence`/`.current_sequence`; real name is `.clip`) → per-segment `.selected` test never ran |

## The lean is overturning (and that's correct)
My "Console is selection-blind → must be a UI-action hook" lean is **already partly falsified**: `flame.batch.selected_nodes` reads on-demand, so selection is NOT uniformly callback-only. And `flame.timeline.clip` + `current_segment` mean the loaded sequence and the playhead-segment are on-demand readable — the Console can see most focus state.

The whole surface decision now rests on **one fact**: is timeline multi-segment selection readable on-demand (walk `flame.timeline.clip` → segments → `.selected`)?
- **If YES** → the Python Console is fully selection-capable → **Creative's minimal-burden Console choice stands, and my lean is fully overturned.**
- **If NO** (segment `.selected` is not on-demand and selection only arrives via `customUIAction`) → timeline selection needs a UI-action surface; batch + sequence + playhead-segment still work from the Console.

This is grounding-relocates-the-finding in real time: measure-first is dissolving an architectural preference I held two passes ago. Probe #3 resolves `clip` correctly and walks segments for `.selected`. **Setup: load a sequence and select 2–3 segments before running.**

## Provisional Tier-C disposition for the SPEC (pending #3)
- Reachable on-demand from any surface: project/workspace/desktop/tab/batch(+iteration+selected_nodes)/`timeline.clip`(loaded sequence)/`timeline.current_segment`/markers.
- Unreachable: numeric playhead frame → record as `null` reason `unreachable_api` (the SPEC's Tier-C-absence vocab earns its keep on the first real signal).
- Pending #3: timeline multi-segment selection — on-demand vs callback-only.
