# Version linkage — corrected storage analysis

**Date:** 2026-06-06
**Status:** CORRECTED ground truth. Supersedes `.planning/GAP-VERSION-OWNERSHIP-LINKAGE.md`
(whose central claim was a bad-join false negative — preserved there as provenance).
**Cross-refs:** `RULING-DURABLE-OWNERSHIP-VS-CONTEXTUAL-PLACEMENT.md`, `SEAM-OBLIGATIONS-Q3.md`,
read-layer sweep commits `ccd325c`/`e54be09`.

---

## The correction

The earlier "versions carry no `version_of` linkage / zero version edges" finding was
**wrong**. It came from a SQL join of `relationships` → `registry_roles`; relationship
**types** live in `registry_relationship_types`, so the join silently returned nothing.
A known-present fact (`forge_get_dependents` had returned a live `member_of` edge) already
contradicted "zero edges" and should have flagged the false negative immediately.

## Corrected ground truth (live operator DB, verified)

- **69 relationship edges total**: `produces` 45, **`version_of` 20**, `derived_from` 2, `member_of` 2.
- **All 20 `version_of` edges point to shots.** The version→shot ownership substrate **exists**
  and matches the durable-ownership ruling (owner link = the `version_of` edge).
- Linked versions carry **`parent_id` populated (typed top-level)** *and* a matching
  `version_of` edge. The earlier "all `parent_id` empty" was a sampling artifact (the 10
  most-recent sampled were this session's unlinked render-probe versions; 20 older versions
  are properly linked).
- **The read-layer fix works against real data:** patched `list_versions(shot=<linked>)`
  returns the linked version (proven live, count=1). The version tools are **not** inert.

## The real (much smaller) findings that remain

1. **Read-mechanism split (the actual read-layer issue).** Tools express the version→shot
   link two ways: `list_versions` reads **`parent_id`** (canonical) and **works**; the
   `shot_id`-metadata readers (`get_shot_versions`, `get_shot_lineage`,
   `list_published_plates`) read a **denormalization that linked versions don't populate**,
   so they can still miss linked versions. **Fix: migrate the `shot_id` readers onto the
   canonical `version_of`/`parent_id`** per the ownership ruling — this is a read-layer
   follow-up against *present* data, NOT a wait on absent data. (This is the
   `parent_id`-vs-`shot_id` inconsistency flagged during the sweep, now confirmed as *the*
   issue.)
2. **Probe-version hygiene.** A subset of recent probe-created versions are unlinked (empty
   `parent_id`, no edge). A small data-hygiene item, not a systemic substrate gap.

## "Missing relationship substrate" theme — walked back

The version case does **not** support a "missing relationship substrate" generalization; the
graph is rich (69 edges, version ownership present). The seam-frontier obligations stand on
their own grounds (Q3); this instance is withdrawn from that theme.

## Impact on the Q4 convergence (decisions unchanged; rationale corrected)

- **#4a (freeze relationship-edge vocab now) — STRENGTHENED.** `version_of`/`member_of`/
  `produces`/`derived_from` are live and in active production use (not aspirational). The
  soft 3-1-override cell is now well-grounded.
- **#4b (defer owner-type enum) — conclusion holds, rationale corrected.** Not "zero owner
  edges / freezing against fiction" but: **all 20 owners are default `shot`-type → no
  owner-type diversity to pressure-test the enum.** Trigger restated: stage-1 ("real
  `version_of` edges exist") is *met*; what's unmet is **non-default `parent_type`** (an
  asset/sequence/etc. owner) plus the ≥3-DCC-case test.
- #3/#5/#6 unaffected.

## Method note (banked)
A raw-storage probe that returns **zero** must be reconciled against any known-present
instance before being trusted — a join returning nothing is suspect until the join is
verified. Amends the two-probe empty-read method: the producer-probe itself needs verifying.
