# Ruling — Durable Ownership vs. Contextual Placement

**Date:** 2026-06-06
**Status:** SETTLED (durable-ownership model) + OPEN deliverable (owner-type polymorphism)
**Origin:** The Blender/render-role drive (2026-06-05/06). A "where does `role=render` attach?"
question surfaced an ontology seam and a writer's-room convergence (DT grounding /
Creative experience / Pipeline). Reached without forcing either Bridge or Pipeline to
abandon its core model — investigation revealed they were already closer than they appeared.

---

## The principle (SETTLED)

The graph has two strata. Keep them distinct forever.

| | **Durable entities** | **Contextual organizations** |
|---|---|---|
| Members | Asset, Shot, Sequence, Version, Media | Stack, Layer, Timeline, Batch, Node graph |
| Survive if a timeline disappears? | Yes | No — they *are* the timeline view |
| Nature | the data itself | a particular view/projection of the data |

- **Ownership edge (durable):** `version_of` — `Version → Shot | Asset` (the `parent_id` +
  `parent_type` on `Version`). This is the canonical owner of a Version. **Not** Stack/Layer.
- **Placement edge (contextual):** a Layer *references* a Version (`Layer.version_id`) to place
  it in a Stack/timeline. Many placements may reference one durable Version. Disposable.
- **Durable classification:** **media role** (`raw, grade, denoise, prep, roto, comp, render`).
  Travels with the media entity as `media.attributes.role`. Fixed. `role_class="media"`.
- **Contextual classification:** **track role** (`primary, reference, matte, background,
  foreground, color, audio`). Lives on the Layer (`role_key`) per Version/timeline. The source
  itself calls it *contextual* (`vocabulary.py:151-152`). `role_class="track"`.

### Why this is already true in the bridge (not a new proposal)

- `Version.__init__` emits `add_relationship(parent_id, "version_of")`; `parent_type ∈ {shot, asset}`
  (`entities.py:296-329`). Ownership is a flat durable edge, polymorphic over owner type.
- `Layer.version_id` is a *reference*, and `Stack`/`Layer` are documented as editorial
  ("track in a timeline segment stack, L01/L02/L03" — `entities.py:429`, `Stack` docstring 532-540).
- The earlier diagram `Shot ← Stack ← Layer → Version → Media` was the **placement/reference**
  path read backwards; it conflated placement with ownership. The ownership path is
  `Media --references--> Version --version_of--> Shot|Asset`.

### Why the render case proves it

- render = a missing **media classification**, not a missing DCC abstraction. The fix landed in
  **media vocabulary**, not in a Layer/Stack abstraction.
- Live, the published render is `Media --member_of--> Shot` with `role: render` on the media. **No
  Layer in the row.** A Layer would only materialize on conform into a timeline — later,
  contextual, disposable.

### Binding consequences

1. **Do not** make Stack/Layer the canonical owner of a Version anywhere in Forge.
2. **Do not** build write-side Stack/Layer to attach a durable fact (e.g. a published render).
   That inverts the model — a contextual structure carrying a durable fact. (This is why the
   "Layer lift" fork for the render publish was rejected; pipeline's flat
   `member_of(media→shot)` + media role was correct.)
3. Stack/Layer are **derived/materialized** from the durable graph when a timeline view is
   requested. Projections, never foundations.
4. Role placement follows the strata: media role on the media (durable); track role on the
   Layer (contextual).

---

## The open deliverable (Version-modeling milestone)

**The real next question is not Stack, not Layer, not render. It is:**

> **What are the valid durable owners of a Version?**

- Today: `parent_type` is a **free string defaulting to `"shot"`**, documented only as
  `shot | asset`, with **no validation**. That shot-centric default is the one place a
  Flame-shaped worldview leaks into the durable layer.
- Likely future owners: Shot, Asset, Sequence, Library, Project, Package, …
- **Deliverable:** harden `parent_type` into a validated, polymorphic owner reference —
  pressure-tested against real DCC cases (Houdini HIP, USD assemblies, hero/vehicle assets,
  sim caches, material/groom libraries, geometry caches) **before** it ossifies. Many of these
  are durable, publishable, may pre-exist any shot, and may be referenced by multiple shots —
  i.e. owned by an **Asset**, not a Shot.
- This is also **contract guidance**: the owner-type enum is a shared noun and belongs in
  forge-contracts alongside the role vocabularies and wire envelope (the recurrence pattern
  named in the 2026-06-05 passoff).

---

## Related (this session)

- Bridge fix landed: `_to_core` now restores residual open attributes symmetrically with
  `_attrs_to_dict`, so `media.attributes.role` survives the JSONB round-trip (it was silently
  dropped on read-back; the role was already correctly persisted in the DB). Regression test:
  `tests/store/test_entity_metadata_roundtrip.py`.
- Hygiene follow-ups (logged, non-blocking):
  - Off-vocabulary `role: plate` exists on a live media row; `plate` is not a registered media
    role (registry: raw/grade/denoise/prep/roto/comp/render). Media roles are free metadata,
    unvalidated against the registry by design — ties to the contract-vocabulary milestone.
  - Pipeline write shape nests a `metadata` sub-dict inside asset attributes and the typed
    `format` (EXR) disagreed with the nested value (PNG) — pipeline-side write hygiene.
