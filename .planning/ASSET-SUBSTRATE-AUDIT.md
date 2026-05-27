# Asset Substrate Audit — current state, gap map, sizing

**Date:** 2026-05-27
**Cycle:** v1.7 Artist Readiness (Thread A framing landed at f559218, A.1 plan pending)
**Trigger:** Operator brief 2026-05-27 — "Make Asset a First-Class Bridge / Projekt Forge Entity"
**Seed:** `.planning/seeds/SEED-ASSET-FIRST-CLASS-ENTITY-V1.7+.md`
**Scope:** Evidence-gathering only — no implementation. This artifact produces a sizing artifact and a scoping recommendation.
**Repos in scope:** `/Users/cnoellert/GitHub/forge-bridge`, `/Users/cnoellert/GitHub/projekt-forge`

## Headline

**Asset is not missing from Bridge. Asset is quiet. Thread C makes it
speak.** *(Operator coinage, 2026-05-27; ratified writer's-room
framing.)*

`Asset` is already in the canonical vocabulary; the load-bearing
substrate (entity table, JSONB attributes, relationship graph,
location records, event log, WebSocket protocol, sync/async clients)
is generic enough that Asset already round-trips through it. The gap
is operator-surface work — tools, CLI, tests, docs — that makes the
substrate operationally audible.

**Thread C scope discipline.** The first pass treats `asset_type` as a
required semantic attribute on asset entities, queryable through the
existing JSONB+GIN path. Promotion to a structured column or
registry-backed classifier is **not** in Thread C — it is a follow-on
motion that opens only if repeated operator/API usage produces
evidence that JSONB query guarantees are insufficient. One clean
thread, not a schema philosophy war.

The implementation arc is meaningfully smaller than Phase N+ (the
commit primitive) — most of the brief's checklist is already
mechanically satisfied; the work is making it operator-visible and
operator-driveable.

## Layer-by-layer current state

### Layer 1 — canonical vocabulary (`forge_bridge/core/`)

**Status: COMPLETE for substrate; one design question for type
extensibility.**

- `forge_bridge/core/entities.py:244` — `class Asset(Versionable,
  BridgeEntity)` exists.
- Carries: `name`, `asset_type` (str, default `"generic"`),
  `project_id`, `status`, `id` (UUID auto-gen), `metadata` (open
  key/value store), `created_at`.
- Inherits from `BridgeEntity` which provides `Relational` + `Locatable`
  traits and `Versionable` directly. All 7 brief-required behaviors
  (identifiable, typed, versionable, locatable, relational, evented,
  queryable, extensible) are present at the entity level.
- Auto-declares `member_of` relationship to its Project on
  construction (`entities.py:275`).
- Exported in `forge_bridge/core/__init__.py:25` as part of the public
  surface. Listed in `__all__:70`.

**The 6 brief-required relationship types** (`member_of`, `version_of`,
`derived_from`, `references`, `consumes`, `produces`) are already
system relationship types in `forge_bridge/core/traits.py:36-49` with
stable system UUIDs. Custom types are also supported through the
registry.

**Design question deferred to scoping:** the `asset_type` extensibility
brief instruction ("Do not hardcode this list as a closed enum unless
the existing registry pattern strongly suggests that approach. Prefer
extensibility.") — the existing `Role` pattern uses a registry with
stable UUID keys + renameable display names + path templates. Whether
`asset_type` deserves the same registry treatment, or stays as an open
string field, is a scoping decision, not an audit finding.

### Layer 2 — database schema (`forge_bridge/store/models.py`)

**Status: COMPLETE for substrate; one structural-promotion question.**

- `ENTITY_TYPES = frozenset({...})` at `store/models.py:207` includes
  `"asset"`.
- CHECK constraint at `:295` enforces it.
- `entity_type IN ('asset', ...)` constraint in initial migration
  `0001_initial_schema.py:86`.
- Asset rows live in the single `entities` table; `asset_type` is
  stored in the JSONB `attributes` column (see `store/models.py:232`
  schema doc).
- GIN index on `attributes` (`:303`) makes `WHERE attributes @>
  '{"asset_type": "vehicle_spec"}'` fast.
- `(project_id, entity_type)` composite index (`:298`) makes
  `list_assets_by_project()` fast.
- `name` is a structured column (indexed via `ix_entities_type_name`).
- `status` is a structured column (indexed via `ix_entities_status`).
- `locations` table is generic — Asset locations land there automatically
  (`:314-371`).
- `relationships` table is generic — Asset relationship edges land
  there automatically (`:377-435`).
- `events` table is generic — `entity.created` / `entity.updated` /
  `entity.deleted` / `location.added` / `relationship.created` etc.
  fire for Asset same as anything else (`:470`+).

**Structural-promotion question deferred to scoping:** the brief asks
for `asset_type` to be "preserved as a first-class field or indexed
attribute." It is already indexed via the GIN-on-JSONB path. Whether
to promote `asset_type` to a real structured column (with its own
B-tree index) is an operator-query-pattern decision — if the
predominant query shape is `WHERE asset_type = '...' AND project_id =
'...'`, a structured column with a composite index beats GIN-on-JSONB
materially. Defer to evidence from consumer usage.

### Layer 3 — repository layer (`forge_bridge/store/repo.py`)

**Status: COMPLETE for substrate.**

- `EntityRepo.save()` (`:249`) is generic — Asset round-trips through
  it.
- `_attrs_to_dict()` (`:341`) has explicit handling at `:364-365`
  preserving `asset_type` to JSONB.
- `_to_core()` (`:408`) reconstructs Asset at `:433-439` with
  `asset_type`, project_id, status, name all restored.
- `list_by_type("asset", project_id)` (`:295`) works generically.
- `find_by_attribute("asset", {"asset_type": "..."}, project_id)`
  (`:307`) works via the GIN-on-JSONB index.
- `LocationRepo`, `RelationshipRepo`, `EventRepo` all generic — Asset
  participates in all three by virtue of being a BridgeEntity.

**One observation:** `_to_core()` uses `BridgeEntity.__init__()`
bypass at `:435` — a pattern shared across all entity types in the
repo. Re-instantiating relationships from the DB requires a separate
call path (load_entity_with_relationships pattern) which already
exists for other types and applies to Asset without modification.

### Layer 4 — WebSocket protocol + server (`forge_bridge/server/`)

**Status: COMPLETE for substrate.**

- `server/protocol.py:100` mentions "assets" as one of the entity
  types the protocol handles.
- `server/router.py:_handle_entity_create()` (`:586-623`),
  `_handle_entity_get()` (`:665`), `_handle_entity_list()` (`:679`),
  `_handle_entity_update()` (`:625`), `_handle_entity_delete()` (`:693`)
  are all generic over `entity_type`.
- `_build_entity()` at `:955-961` has explicit handling for
  `entity_type == "asset"`, constructs Asset with `asset_type`,
  `project_id`, `name`, `status` from the wire message.
- Event emission (`entity.created`, `entity.updated`, `entity.deleted`,
  `location.added`, `relationship.created`) fires for Asset the same
  as anything else.

**Wire protocol acceptance:** a client today can already issue
`entity_create` with `entity_type="asset"` and round-trip an asset
through Postgres + the event log. No protocol change required.

### Layer 5 — clients (`forge_bridge/client/`)

**Status: COMPLETE for substrate.**

- `SyncClient.entity_create(entity_type, project_id, attributes,
  name, status)` at `client/sync_client.py:259-274` works for any
  `entity_type` including `"asset"`.
- `entity_get`, `entity_list`, `entity_update`, `entity_delete` all
  generic.
- `relationship_create(source_id, target_id, rel_type)` at `:323-338`
  works for any relationship type including the 6 brief-required ones.
- No Asset-specific convenience methods exist (no `create_asset()`,
  no `list_assets()`). Consumers would call the generic
  `entity_create` / `entity_list` paths.

**Convenience-method question deferred to scoping:** the brief
implies a "create asset / list assets / show asset" CLI surface in
projekt-forge. Whether the bridge clients should ship Asset-specific
convenience methods (analogous to `create_shot_stack()` at `:407`) or
leave consumers to use the generic surface is a scoping question.

### Layer 6 — operator surfaces (MCP / CLI / Console)

**Status: GAP. This is where the implementation work actually lives.**

- **MCP tools:** `forge_bridge/mcp/tools.py` has zero
  `forge_create_asset` / `forge_list_assets` / `forge_get_asset` tools.
  The `asset_name` references at `:1215`, `:1307`, `:1447`, `:1496-1532`,
  `:1588-1600` are a metadata field on Version/Media records (a
  projekt-forge publish-hook convention), NOT an Asset-entity surface.
- **CLI:** `forge_bridge/cli/main.py` and the Typer subcommands have
  zero Asset surface. No `fbridge asset ...` subcommand group.
- **Console:** `forge_bridge/console/` has zero Asset views. The
  `asset` mentions there are about static web assets (CSS/JS), not the
  entity.
- **Tests:** `tests/test_core.py:13` imports `Asset` but never
  instantiates it. `tests/test_public_api.py:83` checks `Asset` is in
  the public API. **Zero behavioral test coverage** for Asset
  lifecycle, persistence, relationship traversal, or query patterns.

**This is the actual implementation surface.** Building the operator
surfaces is what makes Asset operationally real.

### Layer 7 — projekt-forge consumer side

**Status: GAP. Asset is absent from projekt-forge entirely.**

- `projekt_forge/db/models.py` has DBProject, DBShot, DBVersion,
  DBMedia, DBLocation, DBRelationship, DBRegistryRole, DBEvent —
  **no DBAsset.** The consumer's data model is Shot-centric.
- 5 alembic migrations exist in `projekt_forge/db/migrations/versions/`;
  none touch Asset.
- `projekt_forge/cli/` has subcommands for `auth`, `installer`,
  `launcher`, `project`, `reconstruct`, `scan`, `seed`,
  `verify_reconstruction` — no asset subcommand.
- The `asset` mentions in `projekt_forge/` are exclusively about
  `Sdf.AssetPath` USD references (USD's term for "file pointer"), not
  the forge-bridge Asset entity.

**Implication:** projekt-forge would need a new alembic migration
(006_asset_entity_table.py), a DBAsset model, a repo layer for it,
and a CLI surface. This is roughly the same shape as forge-bridge
Layer 6 work but with an additional schema-migration step.

## Gap Map

| Layer | Current | Gap | Effort |
|-------|---------|-----|--------|
| 1 — core vocabulary | Asset class exists with all traits | (extensibility decision on asset_type registry, not a gap) | XS / decision |
| 2 — DB schema | asset in ENTITY_TYPES, JSONB+GIN | structural-promotion of asset_type to column (decision) | XS / decision |
| 3 — repo layer | generic, asset_type round-trips | (none) | — |
| 4 — WS protocol + server | generic, asset constructor wired | (none) | — |
| 5 — clients | generic entity_* ops | optional asset convenience methods | XS |
| 6 — MCP tools | absent | `forge_create_asset`, `forge_list_assets`, `forge_get_asset`, `forge_update_asset`, optionally `forge_attach_location`, `forge_relate_asset` | M |
| 6 — CLI | absent | `fbridge asset create/list/show/locate/relate` (Typer subgroup) | M |
| 6 — Console | absent | optional Assets view in Artist Console | S/M |
| 6 — tests | absent | round-trip, list-by-type, relationship-traversal, location-attach | M |
| 6 — docs | absent | `docs/ASSET.md` + VOCABULARY.md cross-link | S |
| 7 — projekt-forge consume-vs-duplicate | absent | **C.3 proves** whether consumer needs DBAsset, or just commands + project conventions over Bridge's substrate | S (investigation) + S–M (consume-direct CLI) **OR** M (DBAsset+migration+CLI) — depends on C.3 finding |
| 7 — projekt-forge tests | absent | persistence + graph-relationship tests; shape depends on C.3 outcome | M |

Effort symbols: XS = <1 commit / decision-only. S = 1 commit.
M = 2-4 commits. L = 5+ commits / multi-phase.

**Total effort estimate:** the work is dominated by Layer 6 + Layer 7
operator-surface plumbing. Substrate work is XS-grade (mostly
decisions). Cross-repo coordination adds shape (substrate-before-consumer,
versioned dependency pin in projekt-forge), not bulk.

## Scoping Recommendation

**Recommended container: Thread C inside v1.7 Artist Readiness.**

Reasoning:

1. **Architectural fit with v1.7.** The Artist Readiness milestone
   names the substrate-before-consumer pattern explicitly (see
   `.planning/milestones/v1.7-ARTIST-READINESS-FRAMING.md`). Thread B
   (exec discoverability) shipped operator-surface infrastructure
   over generic substrate. Thread A (chat intent-compile) does the
   same on the chat side. Asset operationalization is the same shape:
   build operator surfaces over substrate that is mostly already
   there.

2. **Sizing matches a thread, not a milestone.** The gap map's bulk
   is M-grade per layer (MCP tools, CLI surface, tests, docs in
   bridge; DBAsset + migration + CLI + tests in projekt-forge). That's
   thread-scale (2-6 phases), not milestone-scale (15-30 phases). It
   is meaningfully smaller than Phase N+ which was a full host-mutation
   primitive with constitutional invariants.

3. **No conflict with Thread A.** Thread A is about authority at the
   chat compile boundary. Asset is about durable production-object
   identity. They are orthogonal. Thread A can proceed in parallel
   with Thread C; the two threads do not share substrate-modification
   surface.

4. **Substrate-before-consumer cleanly separable.** The work
   decomposes naturally into a bridge phase (Layer 6 deliverables) and
   a projekt-forge phase (Layer 7 deliverables), each shippable
   atomically. The bridge side can land independently and projekt-forge
   adopts on a pinned version.

5. **Forward-pressure is real.** Operator framing — "this is going to
   become critical moving forward" — indicates downstream production
   surfaces (vehicle SPECIDs, USD compositions, environments) will
   need Asset to be operational. Waiting until v1.8 risks consumer
   workflows building around Asset's current placeholder shape and
   creating retrofit debt later.

**Alternative containers considered:**

- **v1.8 opening.** Defensible if v1.7's two existing threads are at
  capacity; the writing room's read is that Thread A is in framing
  state with no phase plan opened yet, so capacity is available.
- **Own milestone.** Overscoped — Asset is operationalization, not
  a milestone-scale architectural shift. A milestone container
  invites scope creep into "asset DAM features" which the brief
  explicitly bans.

**Decomposition (operator-ratified, 2026-05-27):**

- **C.1 — Bridge MCP asset tools.** Create, list, get/show, update
  (status + attributes), attach location, relate asset. Behavioral
  tests cover create/read/update/list and relationship traversal.
  Docs at `docs/ASSET.md` + VOCABULARY.md cross-link. Ships
  substrate-only; no consumer impact. `asset_type` is a required
  semantic attribute, queryable via JSONB+GIN — no schema promotion
  in this phase.
- **C.2 — Bridge CLI asset surface.** Same operations as C.1,
  operator-friendly Typer subgroup under `fbridge asset`.
  **`--json` mode preserved** (matches the P-01 stdout-purity
  constraint already binding on `fbridge`). Dogfood-tested against
  the C.1 surface (matches Thread B B-2 dogfooding pattern).
- **C.3 — Projekt Forge consumer proof.** **Investigation-first**,
  not implementation-first. The load-bearing question:
  *can projekt-forge consume Bridge's generic entity-asset directly,
  or does it genuinely need its own DBAsset?* Default hypothesis: if
  Bridge already persists generic assets well, projekt-forge needs
  **commands and project conventions** more than storage. The thread
  proves or disproves that. Outcomes:
    - **If consume-directly works:** C.3 ships projekt-forge command
      surfaces + project conventions over the Bridge substrate. No
      DBAsset, no migration, no duplicate table. Substrate-before-
      consumer respected — the consumer drives, doesn't duplicate.
    - **If DBAsset is genuinely required:** C.3 ships DBAsset +
      alembic migration + repo + CLI, but with evidence about *why*
      duplication is warranted (specific query patterns / consistency
      semantics / failure modes that consume-directly can't satisfy).
  Either way, lands after C.1 (substrate-before-consumer discipline).

**Why C.3 is investigation-first.** The audit's first draft defaulted
to "projekt-forge gets DBAsset" because projekt-forge has DBShot /
DBVersion / DBMedia tables and parallel structure looked obvious.
Operator ratification rejected that default — Bridge is the substrate,
projekt-forge is the consumer, and the substrate/consumer pattern
already governs Learning and Staged ops (see
[[project_forge_bridge_substrate_not_producer]]). Whether projekt-forge
extends the duplicate-table convention to Asset, or starts breaking
that pattern in favor of consume-directly, is a real architectural
question worth making the room prove rather than answering by
precedent.

**Open scoping questions (for the writing room when Thread C opens):**

1. **`status` semantics for Asset.** Inherited from `Status` enum
   currently (Pending/InProgress/etc.). Is the Shot-flavored status
   ontology right for assets, or does Asset need its own
   approval/lifecycle states (e.g. `proposed → approved → published →
   invalidated`)? The brief mentions `approve` and `invalidate` in
   its North Star — a hint that Asset status may want its own
   ontology. Resolvable in C.1.
2. **MCP tool granularity.** Six dedicated Asset tools, or extend the
   generic `forge_create_entity` / `forge_list_entities` surface?
   Pattern in current MCP layer leans toward dedicated tools
   (`forge_list_shots`, `forge_get_shot`, `forge_create_shot`).
   Evidence-grounded answer: follow the existing convention unless
   the registry-watcher / sanitization layer breaks for asset_type.
   Resolvable in C.1.
3. **Asset relationships to Version.** The Version entity already
   has `parent_type` field that supports `"shot"` or `"asset"`. Asset
   versioning works substrate-wise. Whether C.1 ships an explicit
   `forge_publish_asset_version` MCP tool, or leaves that to
   consumer-driven publish flows, is a scoping decision.
4. **C.3 investigation criteria — explicit.** What evidence would
   force "needs DBAsset" over "consume directly"? Candidates: query
   patterns Bridge can't serve at projekt-forge's read latency;
   transactional consistency needs that span Bridge + projekt-forge
   data; failure-mode isolation; offline-operation requirements. The
   writing room nails the criteria *before* C.3 starts gathering
   evidence — otherwise C.3 drifts toward "build it anyway."

**Explicitly deferred — not open scoping questions:**

- **`asset_type` extensibility shape.** Stays as an open string
  field with JSONB+GIN query support for v1. Promotion to a
  structured column with B-tree index, or registry-backed treatment
  analogous to Role, is a **follow-on motion** that opens only if
  repeated operator/API usage produces evidence that JSONB query
  guarantees are insufficient. Per
  [[feedback-explicitly-unbound-vs-implicitly-rejected]]: this is
  deferral, not rejection — preserves maneuverability when evidence
  arrives.
- **Cross-repo coordination tactics.** projekt-forge maintainer
  ruling, not a Thread C ruling. Pinning policy, editable-install
  vs tagged-release adoption, etc., live downstream.

## Next Motion

When the writing room opens Thread C:

1. Promote the seed
   (`.planning/seeds/SEED-ASSET-FIRST-CLASS-ENTITY-V1.7+.md`) to a
   thread framing artifact at
   `.planning/phases/C.1-.../THREAD-C-FRAMING.md` (matching Thread A's
   directory convention). The thread framing carries forward the
   operator-ratified headline ("Asset is not missing from Bridge.
   Asset is quiet. Thread C makes it speak.") and the deferral
   discipline on `asset_type` schema work.
2. Draft the C.1 phase plan against this audit's gap map and the 4
   open scoping questions above.
3. Stage 1b review the C.1 plan before any implementation handoff
   (per the active testing discipline).
4. C.1 ships (Bridge MCP). C.2 ships (Bridge CLI, JSON mode
   preserved). C.3 opens as an investigation that proves or disproves
   the consume-directly hypothesis before any projekt-forge
   schema/code lands.

Thread A is unblocked by this audit and proceeds in parallel.

## Audit Notes

- All file paths and line numbers in this artifact were grounded
  against actual files in this session per the ground-specs-in-actual-files
  discipline. No counts or claims about file shapes are
  approximations.
- Cross-repo audit treated `/Users/cnoellert/GitHub/projekt-forge`
  read-only; the projekt-forge working tree had uncommitted
  modifications (`.claude/settings.json`, `.planning/ROADMAP.md`) and
  untracked files (`24-04-PLAN.md`, `AGENTS.md`, etc.) — not touched.
- This audit does not commit to scope. The writing room ratifies the
  recommended container when Thread A reaches a natural pause point
  or when operator forward-pressure indicates Thread C should open.
