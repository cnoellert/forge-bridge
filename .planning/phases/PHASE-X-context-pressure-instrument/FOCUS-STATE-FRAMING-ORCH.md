# Operator Focus State — Orch Framing (→ DT / Creative redline)

**The question (Creative, the next room energy before PLAN):** *What exactly constitutes operator focus state inside Flame, and how do we guarantee we capture it completely enough that future contextual analysis remains possible?*

**Status:** DISCUSS. **Base:** `main @ 1f3baf7`. **Grounded against:** `tools/utility.py:321`, `tools/project.py:74` (`flame.get_current_tab()`), `tools/batch.py` (`flame.batch`), `tools/timeline.py:259,709`, `flame_hooks/.../forge_bridge.py:482-491` (the `get_*_custom_ui_actions` selection contract).

The framing has one headline finding that **reframes the capture-surface decision** — and it's grounded, not speculative.

---

## The reachability map (grounded — three tiers, not one)

Operator focus state is **not uniformly reachable** from the Flame Python API. Three tiers:

**Tier A — global, on-demand (snapshot-able out-of-band from ANY surface):**
- `project` / `workspace` / `desktop` — `flame.projects.current_project...` (already in `flame_context`).
- `active_tab` — `flame.get_current_tab()` (already read at `utility.py:321`, `project.py:74`). ✓ solved.
- `open_batch` + `batch_iteration` — `flame.batch`, `flame.batch.opened`, `current_iteration` (already read in `batch.py`). ✓ solved.

**Tier B — callback-scoped, NOT a global read (the architectural fork):**
- `selection` / `selected_segments` — Flame delivers selection **only as an argument** to UI-action hooks (`get_custom_ui_actions` / `get_media_panel_custom_ui_actions` → `customUIAction(name, selection)`, scoped to the invoking panel). **There is no `flame.<something>.selection` to read on demand.** A surface that isn't a UI-action callback (e.g. the Python Console) **never receives selection.**

**Tier C — API-limited / possibly unreachable (needs a live Flame probe to settle):**
- `active_sequence` in the player, `playhead` / `current_frame` — `timeline.py:709` already notes the Python API for sequences is limited. Unconfirmed from this dev box (no Flame); **must be verified on a Flame workstation.** If unreachable, contextual refs that resolve against the *player* ("this sequence" = the one loaded in the timeline) may be **fundamentally unmeasurable.**

## The headline finding — the capture surface DETERMINES focus completeness

The brief called the surface "secondary — the contract is primary." That holds for the *schema* but **inverts for focus-completeness:** the surface is the **gate** on which focus signals can be captured at all.

- **Python Console (Creative's candidate, chosen for minimal burden) is selection-blind.** It can capture all of Tier A, **none of Tier B.** It is structurally incapable of seeing the single highest-value focus signal — and `selection` is exactly what the dominant mutation-contextual refs resolve against ("rename the **selected** shots", "publish **these**", and often "**this**").
- **The custom-UI-action hook (media-panel / timeline contextual menu) is the surface Flame hands `selection` to.** It captures Tier A (out-of-band reads) **+ Tier B** (the delivered selection argument).

So choosing the surface for "minimal burden" is, unexamined, a **focus-layer under-capture** — the same CR.1 mistake the schema work fought, relocated from the field layer to the surface layer. *A selection-blind corpus cannot measure the selection-dependent half of contextual failure — likely the dominant half for mutations.*

## How provenance-from-day-one absorbs this (the design already pays off)

`provenance.capture_surface` (Creative's day-one block) tells the analyst **whether a record could have seen selection.** A Console record is honestly tagged selection-blind; a UI-action record carries selection. So the corpus can **mix surfaces** and the analysis knows which records can answer selection-dependent contextual questions — without conflating "selection absent because nothing was selected" with "selection absent because the surface couldn't see it." That distinction is itself load-bearing and provenance makes it legible.

## What "complete enough" means operationally (the CR.1 discipline, applied)
1. **Capture every Tier-A signal out-of-band** on every record (project, tab, batch, iteration, desktop) — cheap, universal.
2. **Capture Tier-B `selection` whenever the surface delivers it**, and tag `capture_surface` so its absence is *attributable*, never silent.
3. **Record Tier-C explicitly as `null` with a reason** (`unreachable_api` vs `not_in_focus`) — absence must be a *known gap*, not silent under-capture. If `world_state.raw` omits a Tier-C signal silently, the corpus looks complete until the counterfactual needs it (CR.1, exactly).

The non-negotiable sharpens: **not just "world_state paired with every record" but "every focus signal is either captured OR recorded-as-explicitly-absent-with-reason."** Silent omission is the failure mode; explicit-null is the fix.

## My lean (for redline)

**The capture surface must be — or include — a custom-UI-action entrypoint, not Console-only.** Selection is too load-bearing to be structurally absent from v1; a selection-blind-only corpus can't evidence the selection-dependent contextual failures, which is most of the mutation half the phase exists to measure. The Console is fine as a **selection-blind secondary** surface for free-typed prompts (honestly tagged), but it cannot be the *only* surface without conceding the measurement.

I hold this as a lean because it trades against real experience cost (a UI-action hook changes the interaction shape — right-click-invoke vs free-type — which is Creative's domain) and against a Tier-C unknown only a Flame probe can close.

## Open questions for the room
- **Q-focus-1 (Creative, experience):** is selection-blindness acceptable for v1 (Console-first, selection deferred to a later UI-action surface), or is selection so central that the surface must deliver it from record one? My lean is the latter; the cost is interaction-shape.
- **Q-focus-2 (DT, grounding — needs a live Flame probe):** what is the API truth on Tier C — is `active_sequence`-in-player / `playhead` readable on demand, or callback-only, or genuinely absent? This bounds what contextual-reference *types* the corpus can ever measure. (Cannot be settled from this dev box — flag for a workstation probe.)
- **Q-focus-3:** the Tier-C-absence vocab (`unreachable_api` vs `not_in_focus`) — confirm it lands in `world_state` capture, so a never-capturable signal is a recorded fact, not a hole.
