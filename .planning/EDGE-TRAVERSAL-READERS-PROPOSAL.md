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
2. **register_publish follow-ons** (capture; do not fix yet per room direction):
   - **2a (trivial correctness bug):** `from_id/to_id/relationship_type` →
     `source_id/target_id/rel_type`. One-line; restores its ability to create the edge.
   - **2b (alignment):** rely on the `version_of` edge as the link; drop dependence on the
     `shot_id` attribute (optionally set `parent_id`/`parent_type` as convenience only).
3. **Orphan hygiene (separate):** the 21 edgeless versions are found by neither edge nor
   attribute — a data-cleanup item, not a reader concern.

## Sequencing
No behavior change now. Reader-change is the architectural follow-on; 2a is a trivial bug fix
available on request; 2b rides whenever register_publish is next touched. None blocks the Q4
freeze cycle.
