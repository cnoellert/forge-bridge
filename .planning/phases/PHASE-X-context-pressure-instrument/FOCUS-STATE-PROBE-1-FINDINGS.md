# Focus-State Probe #1 — Findings (live Flame 2026.2.2, project 013_13_13…portofino)

**Settles half of Q-focus-2; discovers a handle that reopens the other half. The surface decision (Q-focus-1) and the "Console is selection-blind" lean are HELD pending probe #2 — the discovery could overturn them.**

## Confirmed
- **Flame is 2026.2.2** (the `2025.2.1` in the console path is just the SGTK preset location).
- **Tier A — fully reachable on-demand:** `project`, `workspace`, `desktop`, `current_tab` (="Timeline"), `flame.batch.name` / `.opened` / `.current_iteration`. These snapshot from any surface. ✓
- **`flame.selection` does not exist** (AttributeError); no `select*` attr on the desktop. No *trivial* global selection read.
- **Batch focus is rich:** `flame.batch` exposes `current_iteration`, `current_iteration_number`, `cursor_position` (`[]` now), `select_nodes` (callable). Batch node-focus is partly readable.

## Discovered (the important part)
1. **`flame.timeline` → a live `PyTimeline` object.** The probe found the handle but **did not introspect it.** Playhead / current-frame / the player-loaded sequence almost certainly live here. `flame.players` / `flame.player` / `flame.get_current_sequence` all do NOT exist — `flame.timeline` is the single timeline handle.
2. **`desktop.current_sequence`, `desktop.current_reel`, `ws.current_sequence` are readable attributes** (no error) — all returned **`null`** in this capture (even with `current_tab="Timeline"`). So the *player*-loaded sequence is likely surfaced via `PyTimeline`, not `desktop.current_sequence`.
3. **`dir()` UNDER-REPORTS the Flame API (methodology finding).** `desk.current_sequence` read cleanly via getattr yet was **absent from `dir(desktop)`** (`desktop: {}`). Flame resolves attributes dynamically → introspection-discovery is structurally incomplete. **Switch to targeted getattr on known/guessed names.**
4. **The loaded sequence object carries selection-OPERATING methods** — `copy_selection_to_media_panel`, `extract_selection_to_media_panel`, `lift_selection_to_media_panel`. It *knows* its selected segments (as operations). Whether it also exposes them as a *readable property* is untested.

## Why this holds the surface lean (honest hedge)
My "Python Console is selection-blind" headline rests on selection being callback-only. Findings (1)+(3)+(4) mean there may be an **on-demand selection path** on `PyTimeline` or the loaded sequence that `dir()` never surfaced. **If `flame.timeline.selected_segments` (or similar) reads on demand, the Console is NOT selection-blind and the lean weakens materially.** Per ground-before-asserting, I will not lock "selection-blind" until probe #2 tests the on-demand selection path directly.

## Open → Probe #2 (targeted, with real player + selection state)
Settle three things, via **targeted getattr** (not dir-discovery):
- **`PyTimeline` attributes:** playhead / current-frame / current-time, the loaded sequence, current segment/track, in/out marks.
- **On-demand SELECTION path:** `flame.timeline.selected_segments`, the loaded sequence's selected segments, `flame.batch` selected nodes — does selection read on demand anywhere, or only via `customUIAction(selection)`?
- **`desktop.current_sequence` with a sequence actually loaded** in the player (probe #1 had it null) — confirm whether it populates or stays null (i.e. is the player-sequence on the desktop object or only on `PyTimeline`).

Probe #2 (`focus-state-probe-2.py`) is read-only, targeted-getattr, never invokes unknown callables. **Setup before running:** load a sequence into the Timeline player, select 2–3 segments in it, open a batch and select a node — so selection/playhead state EXISTS to read.
