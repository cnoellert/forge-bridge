# Gap — Version ownership/linkage (producer / data-model concern)

**Date:** 2026-06-06
**Status:** OPEN — tracked. Producer/data-model concern, **not** a read-projection concern.
**Origin:** Surfaced by the wire-shape read-layer sweep (2026-06-06). Distinct from, but
adjacent to, the [durable ownership ruling](RULING-DURABLE-OWNERSHIP-VS-CONTEXTUAL-PLACEMENT.md).

---

## Statement (precise)

> Versions in the live operator catalog (`:7533`) currently carry **no durable
> `version_of → shot` (or `→ asset`) linkage of any kind.**

Read-path tools over versions (`forge_list_versions`, `forge_get_shot_versions`,
`forge_get_shot_lineage`, `forge_list_published_plates`, blast-radius) are
**read-path corrected** as of commits `ccd325c`/`e54be09`. Their current empty
results are caused by **absent version→shot linkage in stored data**, not by a
read-layer defect.

**Do not record this as "the version tools are broken."** The readers are correct.
The data they need is not being written.

## Two orthogonal defects (the sweep proved they are independent)

1. **Schema-consumption defect (read layer)** — CLOSED. Tools read `to_dict`
   entities via the wrong key (`attributes` instead of `metadata`/typed
   top-level). Fixed via shared `_attr` / `_entity_fields` accessors + tests.
2. **Data-population defect (this gap)** — OPEN. The producer does not write a
   durable version→shot relationship.

The first was a consumer correctness fix; it was landed independently rather
than coupled to this producer milestone.

## Evidence (live DB, 2026-06-06)

For every `version` entity sampled:
- `parent_id` — **empty**
- `parent_type` — `"shot"` (the **default** string, with nothing behind it)
- `shot_id` in metadata — **empty**
- `version_number` — `1`
- **version outbound relationship edges — zero** (no `version_of`, no `references`)

That is not "one tool looks wrong." It is a **missing relationship substrate**.

## Secondary finding — read-layer reads the link two ways (reconcile when linkage lands)

The (now key-corrected) read sites are inconsistent about *which field* expresses
the version→shot link:
- some read **`parent_id`** (the canonical `version_of` owner per the ruling) —
  `list_versions`, the versions-by-shot grouping
- others read a denormalized **`shot_id`** from open attributes —
  `get_shot_versions`, `get_shot_lineage`, `list_published_plates`

The sweep deliberately **preserved each site's field** (it corrected *how* the
field is read, never *which* field — a correctness pass must not smuggle a
semantic change). When linkage is implemented, **converge these on the canonical
`version_of` / `parent_id`** per the durable-ownership ruling, and treat
`shot_id`-in-metadata as a removable denormalization.

## Recommended resolution (Version-modeling milestone)

- Producer (forge_core / projekt-forge) writes `version_of(version → shot|asset)`
  at version creation — i.e. set `parent_id` + a validated `parent_type`
  (see the owner-type polymorphism deliverable in the ownership ruling).
- Once written, the corrected read tools light up with no further read-layer
  change; re-prove `get_shot_versions` / lineage end-to-end against linked data.
- Reconcile the `parent_id` vs `shot_id` read inconsistency onto `version_of`.

## Cross-refs
- `.planning/RULING-DURABLE-OWNERSHIP-VS-CONTEXTUAL-PLACEMENT.md` (owner edge = `version_of`; owner-type polymorphism deliverable)
- Read-layer sweep commits: `ccd325c` (tier 1: accessor + media), `e54be09` (tier 2: version sites)
