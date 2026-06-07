# Proposal — readers traverse the relationship edge, not duplicated attributes

**Date:** 2026-06-06
**Status:** PROPOSAL / follow-on. **No behavior change made.** Captured per room direction
(verify → propose → capture).
**Cross-refs:** `RULING-DURABLE-OWNERSHIP-VS-CONTEXTUAL-PLACEMENT.md`,
`VERSION-LINKAGE-CORRECTED.md`, `Q4-SEAM-ALLOCATION.md` (#4a freezes the relationship-edge
vocab), reader migration commit `71e3643`.

---

## Principle (the day's distilled outcome)

> **If an edge exists that expresses a relationship, readers should prefer the edge over
> duplicated attributes.** The relationship edge is the durable truth; attributes that
> restate it are projections that drift.

The room started on ownership *hierarchies* and ended rediscovering that the **graph edge is
the canonical link** and attributes (`parent_id`, `shot_id`, …) are denormalized projections.
Applies to `version_of`, ownership, lineage (`derived_from`), consumption (`consumes`/
`produces`), and likely future graph concepts. This is the consumer-side complement of the
durable-ownership ruling (owner link = the `version_of` edge).

## Grounding (live operator DB, 2026-06-06)

Versions cross-tabbed by (`parent_id` attr) × (`shot_id` attr) × (`version_of` edge):

| parent_id | shot_id | version_of edge | count | found by parent_id reader? | found by edge traversal? |
|---|---|---|---|---|---|
| ✓ | ✗ | ✓ | 20 | yes | yes |
| ✗ | ✗ | ✗ | 21 | no | no (truly orphaned) |
| ✗ | ✓ | ✓ | 0 (register_publish-shape) | **no** | yes |

**No version uses `shot_id` as the read key; the only universal link among *linked* versions
is the `version_of` edge.** The recent reader migration (`71e3643`) moved from reading
`shot_id` → `parent_id` — correct for today's 20, but still an *attribute* read. The moment a
producer writes the edge with a different attribute denormalization, attribute-readers miss it.

## register_publish — verified end-to-end (non-destructive capture)

The exact failure mode the principle predicts, in a real producer path:

- Emits version `entity_create` attributes `{shot_id, role, version_number, start_frame,
  end_frame, colour_space, segment_name}` — **`shot_id` present, `parent_id`/`parent_type`
  absent.** → migrated `parent_id` readers would miss its output.
- **BUG (separate, outright):** its `version_of` edge call passes `from_id=/to_id=/
  relationship_type=`; the signature is `relationship_create(source_id, target_id, rel_type)`
  (sibling caller `relate_asset` line 901 is correct). → **throws on every call** (caught by
  try/except → returns `{"error": ...}`). It has never succeeded in the live DB (zero
  `shot_id`-attr versions). The 21 orphans are a *different* population (no edge, no attrs).

## Proposal

1. **Reader change (the principle, applied):** migrate the shot-version readers
   (`get_shot_versions`, `get_shot_lineage`, `list_published_plates`, `list_versions`, and
   register_publish's own next-version count) to **traverse the `version_of` edge** (via
   `query_dependents`/`query_dependencies` or a typed `version_of` traversal) instead of
   filtering `parent_id`/`shot_id` attributes. `parent_id`/`shot_id` become optional
   convenience, never the read key. This is producer-agnostic and aligns with Q4 #4a (the
   `version_of` noun is the freeze-now contracted edge).
2. **register_publish follow-ons:**
   - **2a (correctness bugs) — ✅ FIXED 2026-06-06.** Was a *chain* of stale kwargs, not one
     line (register_publish had drifted from the protocol signatures and was never exercised):
     (i) `relationship_create(from_id/to_id/relationship_type)` → `source_id/target_id/rel_type`;
     (ii) `location_add(location_type="render")` → dropped (signature is
     `location_add(entity_id, path, storage_type="local")`; `"render"` was a media-class value
     leaking onto a location). register_publish now completes end-to-end and emits a correct
     `version_of` (version→shot) edge. Test: `tests/test_register_publish_edge.py`.
   - **2b (alignment) — still open:** rely on the `version_of` edge as the link; drop
     dependence on the `shot_id` attribute (optionally set `parent_id`/`parent_type` as
     convenience only). Folds into the reader-traversal change (#1).
3. **Orphan hygiene (separate):** the 21 edgeless versions are found by neither edge nor
   attribute — a data-cleanup item, not a reader concern.

## Sequencing
2a is FIXED (commit `89252dc`). The reader-change is the architectural follow-on and is the
**immediate next task** (RESUME HERE). It does not block the Q4 freeze cycle; it's the
read-side correlate of Cycle-1 #4a (contract the `version_of` edge).

**Order is forced — #1 must lead, 2b rides on it for free.** 2b means "register_publish stops
relying on the `shot_id` attribute." But readers were migrated to `parent_id` (`71e3643`), and
register_publish writes neither a meaningful `parent_id` nor anything attribute-readers find —
only the correct `version_of` edge (post-2a). So until readers traverse the edge, standalone-2b
is one of two bad shapes: (a) attribute-chasing — make register_publish also write `parent_id`,
throwaway work the migration moots; or (b) invisibility — drop `shot_id` with no edge-reader to
surface the output. Both avoided by doing #1 first; 2b folds in.

---

## Execution brief — edge-traversal reader migration (Orch; ready to pick up)

**Feasibility (bounded swap, not a build):** `query_dependents(entity_id)` already exists
(`protocol.py:368`), is already used by `get_dependents` (`tools.py:1016-1027`, the reference
shape), and is already imported inside `get_shot_lineage` and `list_published_plates` for their
other traversals. The primitive and the model are in place.

1. **Readers traverse the edge.** In `get_shot_versions`, `get_shot_lineage`,
   `list_published_plates`, `list_versions`, and `register_publish`'s own next-version count,
   replace the attribute filter (`_attr(v, "parent_id"|"shot_id") == shot_id`) with
   `query_dependents(shot_id)` filtered to `version_of` edges. Model on `get_dependents`
   (`tools.py:1016-1027`). `parent_id`/`shot_id` become optional convenience, never the read key.
2. **2b folds in.** register_publish already emits the correct `version_of` edge (post-2a) —
   drop the misleading `shot_id` attribute; optionally set `parent_id`/`parent_type` as
   convenience only.
3. **Test the producer-agnostic property (the point).** Each reader must find BOTH (a) the 20
   canonical versions (`parent_id` + edge) AND (b) a `register_publish`-shape version (edge
   only, no `parent_id`) — the cross-tab row that was 0 and that only edge-traversal can
   surface. This test fails under the current `parent_id` readers and passes after #1.
4. **Reference shapes, not rewrite mandates.** Keep each tool's surrounding projection intact;
   change only the linkage step.

**Grounding to re-verify on resume (cheap):** the cross-tab (20 `parent_id`+edge / 21 orphan /
0 `shot_id`), and that `query_dependents` returns the version ids for a shot (it powers
`get_dependents` today). Use the two-probe method correctly — verify any zero against a
known-present instance (the bad-join lesson).
