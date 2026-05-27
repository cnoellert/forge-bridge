---
name: asset-first-class-entity
description: Expand the Forge substrate so `Asset` becomes a true first-class production object — not a placeholder concept in the vocabulary. Lets Bridge and Projekt Forge register, version, locate, relate, and query durable production assets that may or may not be shots or media. UUID is the promise; asset_type is the vocabulary door; the relationship graph is where the asset becomes useful.
type: strategic-framing
planted_during: "2026-05-27 — operator handoff of a written brief during the v1.7 Artist Readiness writing-room cycle, between Thread A framing landing (f559218) and Thread A.1 phase plan opening. Operator framing: 'I think this is going to become critical moving forward.' Audit motion opened in same cycle (.planning/ASSET-SUBSTRATE-AUDIT.md)."
trigger_when: "The audit motion completes and produces a scoping recommendation (Thread C inside v1.7 / v1.8 opening / own milestone). At that point this seed promotes to whichever container the scoping ruling selects. OR a future contributor reaches for Asset operationalization work and needs the converged intent preserved verbatim."
---

# Seed — Asset as first-class Bridge / Projekt Forge entity

> **Operator brief, preserved verbatim.** This seed captures the
> 2026-05-27 written handoff that opened the Asset-substrate motion.
> The brief is reproduced below without paraphrase; the surrounding
> framing in this preamble is the seed's own. Per the substrate /
> consumer pattern this project already follows for Learning and
> Staged ops (see [[project_forge_bridge_substrate_not_producer]]),
> the Bridge side ships the substrate and the Projekt Forge side
> consumes it.

## Why this is captured as a seed

The brief arrived at a clean writing-room seam: Thread A framing
landed (f559218), pushed to origin, no A.1 phase plan yet drafted. The
operator's read was that pausing Thread A to capture this is low-cost
right now and high-value if it does become critical forward. The
writing room agreed.

The first move is **not implementation** — it is an audit. The
substrate already names `Asset` in the canonical vocabulary
(`forge_bridge/core/entities.py:244`, `Asset(Versionable, BridgeEntity)`)
and round-trips `asset_type` through repository serialization
(`forge_bridge/store/repo.py:365` and `:437`). The work is
operationalize-what's-stubbed, not greenfield. The audit produces an
evidence-grounded sizing artifact at `.planning/ASSET-SUBSTRATE-AUDIT.md`
that informs where this work lives (Thread C inside v1.7 vs v1.8
opening vs own milestone).

## Architectural fit

The brief's architectural north star aligns with the project's
existing posture:

- **Substrate, not producer** — Bridge ships the asset registry,
  relationship surfaces, event emission, and read surfaces; the
  consumer (Projekt Forge in production, future endpoints by design)
  drives asset operations and asset-typed workflows. The same pattern
  governs Learning and Staged ops (see
  [[project_forge_bridge_substrate_not_producer]]). On a stock install
  without a consumer wired, the asset table stays empty until
  something feeds it.
- **Endpoint parity** — assets are durable production objects the
  graph needs to recognize regardless of which endpoint authored them.
  Flame-specific behavior belongs in Flame-specific tools, not in the
  generic Asset model. The brief calls this out explicitly.
- **UUID is the promise, asset_type is the vocabulary door** —
  consistent with the canonical-vocabulary topology already in
  `forge_bridge/core/`. The extensibility decision (open registry vs
  closed enum for `asset_type`) is evidence-driven from the existing
  registry pattern, not chosen up front.

## Operator brief — verbatim

> # Brief: Make Asset a First-Class Bridge / Projekt Forge Entity
>
> We need to expand the Forge substrate so `Asset` becomes a true
> first-class production object, not just a placeholder concept in the
> vocabulary.
>
> The goal is to let Bridge and Projekt Forge register, version,
> locate, relate, and query durable production assets that may or may
> not be shots or media. This will support future systems where an
> asset can be a vehicle SPECID, CAD source, USD composition, tree,
> building, environment, material, camera move, lighting setup,
> reference pack, or any other object that needs persistent identity
> in the graph.
>
> ## Core Intent
>
> Bridge already has the right topology: UUID entities, relationships,
> locations, versions, events, and multiple surfaces over the same
> substrate. But assets are not yet operational enough.
>
> We need to make `Asset` usable as a real graph root.
>
> An asset should be:
>
> - identifiable by UUID
> - typed by `asset_type`
> - versionable
> - locatable
> - relational
> - evented
> - queryable
> - extensible through metadata without schema churn
>
> The important principle: `asset_type` should open the system, not
> narrow it. We are not building "3D vehicle assets" only. We are
> building the generic asset substrate that can later hold 3D assets,
> automotive SPECIDs, environments, cameras, materials, style sheets,
> and downstream production objects.
>
> ## Repos
>
> Work across:
>
> - `/Users/cnoellert/GitHub/forge-bridge`
> - `/Users/cnoellert/GitHub/projekt-forge`
>
> Treat both repos carefully. Inspect current git state before
> editing. Do not overwrite unrelated local changes.
>
> ## Bridge Scope
>
> In `forge-bridge`, audit the current `Asset` support across:
>
> - canonical vocabulary
> - core entity model
> - DB entity schema / entity type constraints
> - repository serialization/deserialization
> - relationship support
> - event support
> - MCP / CLI / read surfaces if present
>
> Then implement the missing pieces needed for assets to behave like
> operational graph citizens.
>
> Minimum Bridge deliverables:
>
> 1. `Asset` can be created, persisted, loaded, listed, and queried.
> 2. `asset_type` is preserved as a first-class field or indexed
>    attribute.
> 3. `Asset` supports locations.
> 4. `Asset` supports relationships:
>    - `member_of`
>    - `version_of`
>    - `derived_from`
>    - `references`
>    - `consumes`
>    - `produces`
>    - custom relationship types where already supported
> 5. `Asset` changes emit append-only events.
> 6. Repository tests cover create/read/update/list and relationship
>    traversal basics.
> 7. Public docs explain the asset model.
>
> ## Projekt Forge Scope
>
> In `projekt-forge`, wire the new Bridge asset capability into the
> consumer layer without over-specializing it.
>
> Minimum Projekt Forge deliverables:
>
> 1. Add or update Projekt-side asset registry support.
> 2. Ensure assets can be associated with projects.
> 3. Ensure assets can have locations and versions.
> 4. Ensure assets can participate in relationships with shots,
>    versions, media, and other assets.
> 5. Add CLI or scriptable surface for basic asset operations:
>    - create asset
>    - list assets
>    - show asset
>    - attach location
>    - relate asset to another entity
> 6. Keep Flame-specific behavior out of the generic asset model.
> 7. Add tests around DB persistence and graph relationships.
>
> ## Suggested Asset Shape
>
> ```text
> Asset
>   id: uuid
>   project_id: uuid | null
>   name: string
>   asset_type: string
>   status: string
>   attributes: json
>   created_at
>   updated_at
> ```
>
> Examples of future `asset_type` values:
>
> - vehicle_spec
> - cad_source
> - usd_composition
> - environment
> - location_sheet
> - road_surface
> - tree
> - building
> - material
> - camera_move
> - lighting_setup
> - style_sheet
> - reference_pack
> - otio_edit
> - deliverable
>
> Do not hardcode this list as a closed enum unless the existing
> registry pattern strongly suggests that approach. Prefer
> extensibility.
>
> ## Non-Goals
>
> - Do not build the Diff automotive schema yet.
> - Do not implement SPECID-specific logic yet.
> - Do not build Comfy, USD, OTIO, QC, or render queue orchestration
>   yet.
> - Do not make assets Flame-specific.
> - Do not turn this into a full DAM.
>
> This phase is about making the substrate capable of carrying assets.
>
> ## Acceptance Criteria
>
> - A generic asset can be created in Bridge and stored durably.
> - It can be assigned an `asset_type`.
> - It can be given one or more locations.
> - It can be related to another entity.
> - It can be queried back with its metadata intact.
> - Projekt Forge can consume that capability without duplicating
>   Bridge logic unnecessarily.
> - Tests prove the behavior.
> - Docs describe the mental model clearly.
>
> ## Architectural North Star
>
> An asset is any durable object the production graph needs to
> recognize, version, locate, relate, approve, and invalidate.
>
> - The UUID is the promise.
> - The `asset_type` is the vocabulary door.
> - The relationship graph is where the asset becomes useful.

## Status

Parked as forward-pressure. The audit motion is open
(`.planning/ASSET-SUBSTRATE-AUDIT.md`); it produces the sizing
artifact that decides where the implementation work lives. Thread A
proceeds in parallel — the audit does not block it. Seed promotes to
the chosen container (Thread C in v1.7 / v1.8 opening / own
milestone) when the audit closes.
