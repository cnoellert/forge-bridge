**Finding (① temporal vertical live UAT, 2026-06-26): `traffik.flame_sequence.ingest_edit_state` mints non-deterministic segment ids, which blocks graph-authored editorial steps that target a specific segment.**

**Repro:** two ingests of the same live sequence (`FORGE_UAT_HOST_APPLY_20260624`) yield different ids for the same segment — `02491983…` vs `5daafcc5…`.

**Why it blocks the graph:** in the operator-drivable graph `ingest → apply_steps → select_delta → host_resolve → commit`, the `apply_steps` `trim_tail` step is GraphSpec *config* and must name a `segment_id`. But that id only exists after ingest runs, and a fresh in-graph ingest mints a *different* id than any probe ingest used to author the step → `trim_tail` → "segment not found". Generalizes: **any editorial atom that targets a specific segment** (`trim_tail`, `nudge_segment`, `slip_segment`, `move_segment`, segment rename, …) can't be statically authored in a GraphSpec against ingest-minted ids.

**Proven working around it (sequential, same ingest):** `ingest.data` (the EditState) → `apply_steps(trim_tail)` → 1 temporal delta → `select_delta` extracts. The chain is *correct*; only the graph-authoring of the segment reference is blocked.

**Ask — one of:**
1. **Deterministic segment ids** (Bridge lean): mint the segment id as uuid5 from stable content (sequence + track + record position + source/name), so a step authored against a probe ingest matches the in-graph ingest. Smallest change; keeps `trim_tail`'s `segment_id` contract intact.
2. **Stable segment addressing** in editorial atoms: let steps target by a stable key (name / track+record-position / index), resolved to the runtime id at apply time.

I lean **(1)**.

**Context:** C reshape (#51) confirmed live — `ingest.data` IS the EditState, consumed straight as `apply_steps.state`. This is the last gate to a *graph-driven* (not sequential) live temporal vertical.

**Adjacent note (not a Pipeline bug):** ingest reads the heavy Flame hierarchy; that live read must be **main-thread-safe** (I crashed Flame running the extraction off the main thread). Relevant to how ingest's `sequence_data` is sourced in the live graph — wrap the extraction to run on Flame's main thread, or source via the main-thread-safe read path.
