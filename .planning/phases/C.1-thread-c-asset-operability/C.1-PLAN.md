---
milestone: v1.7
thread: C
phase: C.1
phase_name: Bridge MCP asset tools — make Asset operationally legible
status: phase-plan
drafted: 2026-05-27
revised: 2026-05-27 (v2 — Stage 1b green-after-revisions; B-1..B-8 grounding fixes + S-1..S-3 substantive rulings + Creative tightenings applied; D1 Path A ratified)
type: phase-plan
derives_from: .planning/phases/C.1-thread-c-asset-operability/THREAD-C-FRAMING.md
governing_rulings: R-3 (C.1 scope), R-7 (Status inheritance), R-8 (dedicated tools), R-9 (no Version-publish), R-2 (no schema philosophy war)
artifact_role: code-handoff — implementation hands off against this spec; Stage 1b cleared
review_state: stage-1b-passed
---

# C.1 — Bridge MCP asset tools

> **What this artifact is.** The code-handoff phase plan for C.1, the
> opening phase of Thread C. It locks the contract surface six new
> MCP tools must adopt, the Status-alias additions, the test plan,
> the doc plan, and the file change manifest. Implementation hands
> off against this spec after Stage 1b review clears (DT seat).
>
> **What this artifact is not.** Not implementation. Not a partial
> draft to be filled in during execution. The contracts below are
> the spec; deviation requires a spec amendment, not
> implementation-time discretion.

## Scope

C.1 ships six dedicated `forge_*_asset` MCP tools, three Status
alias additions to support the brief's operator vocabulary,
behavioral tests for the new tools, and documentation. Per R-9
this phase is **entity-level only** — no
`forge_publish_asset_version`, no Version-publish surface, no
Asset-aware extensions to existing Shot/Version tools.

Per R-2: no schema changes. `asset_type` stays JSONB-backed,
queryable through the existing GIN-on-attributes index. No
alembic migration in C.1. The `entities` table CHECK constraint
already permits `entity_type='asset'`
(`forge_bridge/store/migrations/versions/0001_initial_schema.py:86`);
nothing schema-side moves.

Per R-7: no new Status values. The canonical enum at
`forge_bridge/core/vocabulary.py:21` is inherited unchanged. Three
`from_string()` aliases are added for operator vocabulary parity
with the brief.

Per R-8: dedicated tools, not generic entity surface. The tool
names themselves carry affordance signal.

## Substrate inventory (grounded; do not duplicate)

Verified 2026-05-27 against current `main` (`3020ae9`):

- **Asset entity** — `forge_bridge/core/entities.py:244`,
  `Asset(Versionable, BridgeEntity)`, fields `name`, `asset_type`
  (default `"generic"`), `project_id`, `status`, `id`, `metadata`,
  `created_at`. Constructor at `:255`; `to_dict()` at `:278`. Exports
  cleanly through `forge_bridge.core.__all__` and the public API.
- **Persistence** — `forge_bridge/store/repo.py:364-365` serializes
  `asset_type` to JSONB; `:434-439` reconstructs from JSONB. Generic
  `EntityRepo.save/get/list_by_type/find_by_attribute/delete` all
  work for Asset without modification.
- **DB schema** — `forge_bridge/store/models.py:207-210`,
  `ENTITY_TYPES` includes `"asset"`; CHECK constraint at `:295`;
  GIN-on-attributes index at `:303`; composite `(project_id,
  entity_type)` index at `:298`.
- **WS protocol + server** — `forge_bridge/server/router.py:586-623`
  generic entity_create handler; `:955-961` Asset constructor;
  list/get/update/delete handlers all generic.
- **Wire-level primitives C.1 wraps** —
  `forge_bridge/server/protocol.py:260` `entity_create()`,
  `:278` `entity_update()`, `:294` `entity_get()`,
  `:298` `entity_list()`, `:330` `relationship_create()`,
  `:348` `location_add()`. No new wire types required.
- **Status enum** — `forge_bridge/core/vocabulary.py:21-61`,
  9 values + `from_string()` aliases.

The substrate is ready. C.1 adds operator surfaces over it.

## Locks

Locks are the load-bearing contract anchors Stage 1b reviews. Any
deviation from these requires a spec amendment, not
implementation-time discretion.

### L1 — Tool count and naming

**Six dedicated MCP tools, registered with the names below, no
others, no generic entity surface added.**

| Tool name | Pattern (PR22) | readOnlyHint | idempotentHint |
|---|---|---|---|
| `forge_create_asset` | C (required params) | False | False |
| `forge_list_assets` | B (defaultable params) | True | True |
| `forge_get_asset` | C (required params) | True | True |
| `forge_update_asset` | C (required params) | False | True |
| `forge_attach_asset_location` | C (required params) | False | False |
| `forge_relate_asset` | C (required params) | False | False |

Registration site: `forge_bridge/mcp/registry.py`, in the
`register_builtins()` body (verified at `registry.py:290`),
grouped under a new section header
`# ── Asset operability tools (Thread C / Phase C.1) ──`,
**placed after the existing shot tools and before `list_versions`**
— Asset is an entity, so it sits with the entity-create group
ahead of versioning and workflow surfaces. The L1 placement and
the file change manifest agree on this site; no ambiguity at
handoff.

### L2 — Status semantics

**Inherit `Status` enum unchanged. Aliases-only contribution.**

- No new enum values added.
- No Asset-specific state machine introduced.
- Three aliases added to `Status.from_string()` at
  `forge_bridge/core/vocabulary.py:41-51`:
    - `"proposed"` → `Status.PENDING`
    - `"published"` → `Status.DELIVERED`
    - `"invalidated"` → `Status.ARCHIVED`
- `"invalidate"` (verb form) is **not** added — Path A ratified
  2026-05-27. Constitutional rationale:
    - `"invalidated"` describes **state** (past-participle,
      state-descriptor).
    - `"invalidate"` is an **authority action** (verb, command
      surface).
    - C.1 is operability + state visibility, not authority
      workflow orchestration. A verb-form alias would imply who
      may invalidate, under what ratification, with what
      reversibility / provenance semantics — authority surfaces
      Thread A operates on, not C.1.
- **Convention named, going forward:** state-descriptor /
  past-participle aliases only. The existing `"omit": cls.ARCHIVED`
  alias at `vocabulary.py:50` is inherited inconsistency from
  earlier work; C.1 does not expand it as the new convention.
- `"approved"` requires no alias (direct enum value at
  `vocabulary.py:31`).
- The alias additions are usable by every entity, not Asset-only —
  this is a substrate-wide additive change per R-2's discipline
  that Asset-specific semantics do not belong in shared surfaces.

### L3 — No Version-publish surface

**C.1 does not ship `forge_publish_asset_version` and does not add
asset-awareness to existing Version or publish tools.**

- The Version entity already supports `parent_type="asset"`
  (`forge_bridge/core/entities.py:307`); substrate is sufficient.
- Existing `forge_list_versions` and `forge_register_publish` are
  NOT modified to be asset-aware in C.1.
- If a downstream phase introduces a Version-publish surface, it
  is its own Version-layer motion — not a C.1 amendment.

### Minor locks

- **MOL-1. Tool input contract per PR22.** Every input model
  follows Pattern A/B/C exactly per L1's table. No Pattern-C model
  with all-optional fields (the anti-pattern PR22 closed).
- **MOL-2. Error envelope.** Every tool returns through `_ok(...)`
  or `_err(str(e))` matching the existing shot-tool convention
  (`forge_bridge/mcp/tools.py:579` and `:587` for the
  established shape). Never raise; never return a bare dict
  without envelope.
- **MOL-3. `asset_type` is a required field in `forge_create_asset`.**
  No default of `"generic"` at the MCP layer. The Asset class
  itself defaults to `"generic"`
  (`forge_bridge/core/entities.py:258`); the MCP layer is the
  operator-affordance layer and forces the operator to name the
  type at create-time.

  > **Constitutional rationale.** Substrate defaults preserve
  > internal structural validity; **operator surfaces require
  > explicit ontology selection where affordance semantics
  > depend on it.** The substrate's `"generic"` default exists for
  > programmatic creation paths (tests, repo round-trips, future
  > endpoints) where structural completeness is the only
  > requirement. The MCP affordance layer is a different
  > responsibility: it is where intent enters the system. Letting
  > the MCP layer silently fall back to `"generic"` would mean
  > the operator never specified ontology — discoverability
  > degrades, downstream tooling cannot distinguish intentional
  > genericity from omitted intent, and Thread A would later
  > inherit ambiguity into compile-time affordance selection
  > (the exact layer Thread A is engineered to make structurally
  > observable). MOL-3 names this split as architectural law,
  > not just regression prevention.

  The contract lands at two reinforcing registers per
  `[[feedback-description-layer-multi-register-surface]]`:
  Pydantic `Field(...)` enforces at the schema register;
  description prose ("operator must name the type") reinforces
  at the affordance-selection register.
- **MOL-4. `asset_type` is free-form string.** No enum validation
  in the input model. No allow-list. The brief's example values
  (vehicle_spec, cad_source, usd_composition, environment,
  location_sheet, road_surface, tree, building, material,
  camera_move, lighting_setup, style_sheet, reference_pack,
  otio_edit, deliverable) are documented as examples in the
  description but not enforced. Per R-2.
- **MOL-5. No Console UI in C.1.** The Console Artist UI may grow
  an Assets view in C.2 or later; C.1 ships MCP only.
- **MOL-6. Entity identity class is immutable once instantiated
  in C.1 — doctrined guard via three-layer defense-in-depth.**

  > **Doctrine, named:** entity_type is a constitutional property
  > of the entity, not a mutable field. Omission of `entity_type`
  > from `forge_update_asset`'s `UpdateAssetInput` is the
  > enforcement mechanism for ontology immutability — not
  > accidental absence, **constitutional absence**.
  > `[[feedback-explicitly-unbound-vs-implicitly-rejected]]`
  > applies: absent-by-accident and absent-by-constitutional-lock
  > are operationally different states; this is the latter, and
  > the spec names it so future contributors do not "helpfully"
  > add the field because it looks omitted.

  Defense-in-depth at three layers:
  1. **Schema layer (C.1's responsibility).** No `entity_type`
     field in `UpdateAssetInput`. The caller cannot express the
     intent.
  2. **Wire layer (substrate's responsibility, inherited).**
     `forge_bridge/server/protocol.py:278` `entity_update()`
     accepts `entity_id + name + status + attributes`. No
     `entity_type` parameter.
  3. **DB layer (substrate's responsibility, inherited).** CHECK
     constraint at
     `forge_bridge/store/migrations/versions/0001_initial_schema.py:86`
     would reject any direct table mutation that escaped the
     upper layers.

  The schema-level guard is sufficient at the C.1 surface
  because layers 2 and 3 back it up; even an implementation-time
  mistake (a contributor "helpfully" adding the field) would
  surface at one of the lower layers. C.1 ships the schema-level
  guard with the doctrine named.

  The tool updates `name`, `status`, `asset_type` (intra-asset
  semantic), and `attributes` — but never the entity's identity
  class. Reclassification, if ever needed, is its own future
  motion against a substrate-wide convention, not a C.1
  amendment.
- **MOL-7. Tests run against in-memory store fixture where
  available.** Match the existing test pattern for entity tests
  (e.g. `tests/test_core.py` style) — do not require a live
  Postgres or daemon for the C.1 test suite.

## Deliverables

### D1 — Status alias additions

**File:** `forge_bridge/core/vocabulary.py`

**Change:** Add three keys to the `aliases` dict in
`Status.from_string()` (around line 41-51), preserving the
existing `wip / work_in_progress / ip / pending_review / for_review
/ final / done / complete / omit` aliases unchanged. **Match the
existing grouped-by-target-enum convention** — the existing dict
is grouped (WIP aliases together → IN_PROGRESS, review aliases
together → REVIEW, completion aliases together → DELIVERED).
Insert each new alias adjacent to its existing target group:
`"proposed"` next to no peers in the PENDING group (it is the
first PENDING alias); `"published"` next to `complete`/`done`/`final`
in the DELIVERED group; `"invalidated"` next to `omit` in the
ARCHIVED group.

```python
# In aliases dict, grouped by target enum:
"proposed":         cls.PENDING,        # new — first PENDING alias
"wip":              cls.IN_PROGRESS,
"work_in_progress": cls.IN_PROGRESS,
"ip":               cls.IN_PROGRESS,
"pending_review":   cls.REVIEW,
"for_review":       cls.REVIEW,
"final":            cls.DELIVERED,
"done":             cls.DELIVERED,
"complete":         cls.DELIVERED,
"published":        cls.DELIVERED,      # new
"omit":             cls.ARCHIVED,
"invalidated":      cls.ARCHIVED,       # new
```

**Acceptance:** unit test confirms each new alias resolves to the
expected value; existing aliases continue to resolve unchanged;
unknown values still raise with the canonical error message.

### D2 — `forge_create_asset`

**Input model** (Pattern C):

```python
class CreateAssetInput(BaseModel):
    project_id: str = Field(..., description="Project UUID")
    name:       str = Field(..., description="Asset name (operator-facing)")
    asset_type: str = Field(
        ...,
        description=(
            "Asset type/category. Free-form string — open vocabulary. "
            "Examples: vehicle_spec, cad_source, usd_composition, "
            "environment, location_sheet, material, camera_move, "
            "lighting_setup, style_sheet, reference_pack, "
            "otio_edit, deliverable. New types do not require schema changes."
        )
    )
    status: Optional[str] = Field(
        default=None,
        description="Initial status (default: pending). Accepts canonical Status values + aliases."
    )
    attributes: Optional[dict] = Field(
        default=None,
        description="Optional metadata dict for type-specific or pipeline-specific fields."
    )
```

**Handler** (sync to existing `create_shot` pattern at
`forge_bridge/mcp/tools.py:526`):

```python
async def create_asset(params: CreateAssetInput) -> str:
    """Create a new Asset entity.

    Asset is any durable production object that needs persistent
    identity in the graph — characters, vehicles, environments,
    materials, references, etc. Distinct from Shot.

    Returns the asset_id on success.
    """
    try:
        from forge_bridge.server.protocol import entity_create
        client = _client()
        asset_attrs = dict(params.attributes or {})
        # asset_type lives at the top of the attributes payload —
        # repo.py:365 reads it from there.
        asset_attrs["asset_type"] = params.asset_type
        result = await client.request(entity_create(
            entity_type="asset",
            project_id=params.project_id,
            name=params.name,
            attributes=asset_attrs,
            status=params.status,
        ))
        return _ok({
            "created":   True,
            "asset_id":  result["entity_id"],
            "asset_name": params.name,
            "asset_type": params.asset_type,
        })
    except Exception as e:
        return _err(str(e))
```

**Registration**:

```python
register_tool(
    mcp, tools.create_asset,
    name="forge_create_asset",
    source="builtin",
    annotations={
        "title": "Create an Asset entity",
        "readOnlyHint": False,
        "idempotentHint": False,
    },
)
```

### D3 — `forge_list_assets`

**Input model** (Pattern B — defaultable):

```python
class ListAssetsInput(BaseModel):
    project_id: Optional[str] = Field(default=None, description="Project UUID filter")
    asset_type: Optional[str] = Field(default=None, description="Filter by asset_type (exact match)")
    status:     Optional[str] = Field(default=None, description="Filter by status (canonical value or alias)")
    limit:      int = Field(default=100, description="Max results (silently clamped to 500)")
```

**Handler** (Pattern B — must handle `params is None`):

Calls the underlying `entity_list` protocol message with
`entity_type="asset"` + project_id; if `asset_type` is provided,
filter post-fetch (the wire layer's narrowing kwargs do not yet
include `asset_type`). Returns a list of summary dicts
`{asset_id, name, asset_type, status, created_at}`.

> **Explicit deferral.** D3 filters by `asset_type` post-fetch
> rather than plumbing a new narrowing kwarg into the wire
> protocol. If asset query volume ever exceeds practical
> post-fetch capacity, a future motion either adds `asset_type`
> to `entity_list`'s narrowing kwargs OR exposes a separate
> `find_by_attribute` wire path (the repo-layer support exists at
> `forge_bridge/store/repo.py:307`). Out of C.1 scope per R-2;
> preserves maneuverability per
> `[[feedback-explicitly-unbound-vs-implicitly-rejected]]`.

**Registration**: `name="forge_list_assets"`, `readOnlyHint=True`,
`idempotentHint=True`.

### D4 — `forge_get_asset`

**Input model** (Pattern C):

```python
class GetAssetInput(BaseModel):
    asset_id: str = Field(..., description="Asset UUID")
```

**Handler**: calls `entity_get`, validates the returned entity is
`entity_type == "asset"`, returns the full dict including
locations and relationships (the WS server's entity_get returns
`entity.to_dict()` which includes those — see
`forge_bridge/server/router.py:677`).

**Registration**: `name="forge_get_asset"`, `readOnlyHint=True`,
`idempotentHint=True`.

### D5 — `forge_update_asset`

**Input model** (Pattern C):

```python
class UpdateAssetInput(BaseModel):
    asset_id:   str = Field(..., description="Asset UUID")
    name:       Optional[str] = Field(default=None, description="New name (omit to leave unchanged)")
    status:     Optional[str] = Field(default=None, description="New status (omit to leave unchanged)")
    asset_type: Optional[str] = Field(default=None, description="New asset_type (omit to leave unchanged)")
    attributes: Optional[dict] = Field(default=None, description="Attributes to merge (omit to leave unchanged). Existing keys are overwritten; existing keys not in this dict are preserved.")
```

**Handler**: calls `entity_get` first to load current state,
applies the patch (merging `attributes` rather than replacing the
whole dict — preserves existing JSONB fields like `asset_type`
when only `attributes` is passed), calls `entity_update`. **Does
not change `entity_type`** per MOL-6.

> **Explicit override semantics (S-1 ruling, 2026-05-27).** When
> `params.asset_type is not None`, set
> `merged_attrs["asset_type"] = params.asset_type` **after** the
> `attributes` merge. Explicit top-level fields override merged
> values. Stated explicitly to remove the
> "asset_type-in-attributes-dict-loses-to-top-level" ambiguity at
> implementation time. Operator intent: an explicit
> `asset_type=` argument is authoritative; a `"asset_type"` key
> smuggled in `attributes` does not override it.

**Registration**: `name="forge_update_asset"`, `readOnlyHint=False`,
`idempotentHint=True`.

### D6 — `forge_attach_asset_location`

**Input model** (Pattern C):

```python
class AttachAssetLocationInput(BaseModel):
    asset_id:     str = Field(..., description="Asset UUID")
    path:         str = Field(..., description="Filesystem path or URL")
    storage_type: str = Field(
        default="local",
        description="One of: local, network, cloud, archive, clip"
    )
    priority:     int = Field(default=0, description="Higher = preferred when multiple locations exist")
```

**Handler**: validates that the entity exists and is type
`"asset"` (via `entity_get`), then calls the wire-level
`location_add` (`forge_bridge/server/protocol.py:348`). Returns
`{attached: true, asset_id, path}`.

**Registration**: `name="forge_attach_asset_location"`,
`readOnlyHint=False`, `idempotentHint=False`.

### D7 — `forge_relate_asset`

**Input model** (Pattern C):

```python
class RelateAssetInput(BaseModel):
    asset_id:  str = Field(..., description="Source asset UUID")
    target_id: str = Field(..., description="Target entity UUID (any entity type)")
    rel_type:  str = Field(
        ...,
        description=(
            "Relationship type. System types: member_of, version_of, "
            "derived_from, references, peer_of, consumes, produces. "
            "Custom types may be passed by UUID string."
        )
    )
    attributes: Optional[dict] = Field(default=None, description="Edge attributes (e.g. track_role for consumes/produces)")
```

**Handler**: validates the source entity is type `"asset"` (via
`entity_get`), then calls the wire-level `relationship_create`
(`forge_bridge/server/protocol.py:330`). Returns `{related:
true, asset_id, target_id, rel_type}`.

**Registration**: `name="forge_relate_asset"`,
`readOnlyHint=False`, `idempotentHint=False`.

### D8 — Tests

**File:** `tests/mcp/test_asset_tools.py` (new file). Directory
`tests/mcp/` exists (verified — contains `__init__.py` and
`test_staged_tools.py`); no conditional path logic at
implementation time.

**Fixture grounding (B-3 ruling, ground-specs-in-actual-files).**
Tests use the `session_factory` fixture from `tests/conftest.py`
(real async DB session), exercising the full handler →
`entity_create` → `EntityRepo` → JSONB round-trip path. Use the
`_ResourceSpy` pattern from `tests/test_console_mcp_resources`
for tool-registration assertions; precedent for the combined
shape is `tests/mcp/test_staged_tools.py:29`
(`spy_with_staged_data` fixture). Per
`[[feedback-fixture-shape-mirrors-production]]`: mocking
`entity_create` would mean the JSONB `asset_type` round-trip is
never exercised — the bug we want the tests to catch is exactly
in that path. The fixture grounding is load-bearing, not
stylistic.

**Coverage matrix:**

| Test | Assertion |
|---|---|
| `test_create_asset_round_trip` | create → get returns the entity with `asset_type` and `name` preserved |
| `test_create_asset_requires_asset_type` | Pattern-C contract — `{}` fails Pydantic validation; missing `asset_type` fails Pydantic validation |
| `test_create_asset_accepts_open_asset_type` | create with `asset_type="vehicle_spec"` (or any free-form string) succeeds |
| `test_list_assets_filters_by_project` | list with project_id A returns only that project's assets |
| `test_list_assets_filters_by_asset_type` | list with `asset_type="X"` filters correctly |
| `test_list_assets_empty_args` | Pattern-B contract — `params=None` returns all assets (clamped to limit) |
| `test_get_asset_returns_full_payload` | get returns locations + relationships per `to_dict()` shape |
| `test_get_asset_rejects_non_asset_uuid` | passing a Shot UUID fails with explanatory error |
| `test_update_asset_merges_attributes` | partial attributes patch preserves existing keys |
| `test_update_asset_changes_status_via_alias` | passing `status="proposed"` resolves to PENDING |
| `test_update_asset_preserves_entity_type_against_smuggled_attribute` | MOL-6 behavioral assertion: create asset → call update with `attributes={"entity_type": "shot"}` (or any value) → assert `get_asset` still returns `entity_type="asset"` AND the entity remains queryable as `entity_type="asset"`. Exercises the substrate, not the absence of a field. |
| `test_attach_asset_location_round_trip` | attach → get shows the location in the payload |
| `test_attach_asset_location_rejects_non_asset` | passing a Shot UUID fails |
| `test_relate_asset_creates_edge` | relate with `rel_type="references"` creates a queryable edge |
| `test_relate_asset_rejects_non_asset_source` | passing a Shot UUID as source fails |
| `test_status_alias_proposed_resolves_to_pending` | unit test on `Status.from_string("proposed")` |
| `test_status_alias_published_resolves_to_delivered` | unit test |
| `test_status_alias_invalidated_resolves_to_archived` | unit test |

**Implementation notes for tests:**

- Test harness is the `session_factory` fixture path described
  above (B-3 fixture grounding). The fixture skips gracefully
  when Postgres is unavailable per `tests/conftest.py:188`
  `_phase13_postgres_available()`; when it runs it exercises the
  real wire→repo→JSONB path. No in-memory alternative; no fixture
  swap-out at implementation time.
- The three Status alias unit tests can live in
  `tests/test_core.py` next to existing vocabulary tests, or in a
  new `tests/test_vocabulary.py` — match the existing convention.

### D9 — Docs

**File 1:** `docs/ASSET.md` (new). Sections:

1. What Asset is (canonical-vocabulary statement, ~1 paragraph;
   echoes the seed's North Star).
2. Why Asset is distinct from Shot.
3. The six MCP tools — purpose, input, output, examples.
4. The substrate Asset participates in (locations, relationships,
   events, versions via `parent_type="asset"`). **Document the
   7-relationship-type substrate truth** — `member_of`,
   `version_of`, `derived_from`, `references`, `peer_of`,
   `consumes`, `produces` (per `forge_bridge/core/traits.py:36-49`
   `SYSTEM_REL_KEYS`). The brief enumerates 6; the substrate has 7.
   D7 documents the substrate, not the brief subset; the doc
   matches D7's reality, not the brief.
5. `asset_type` — open vocabulary, examples, JSONB-backed query
   path; explicit pointer to the deferred-promotion follow-on
   motion (per R-2).
6. What's not in C.1 (Version-publish, Console UI, projekt-forge
   consumption — pointers to R-9 and R-5/R-10 respectively).

**File 2:** `docs/VOCABULARY.md` — add an "Asset" subsection or
cross-link `docs/ASSET.md` from the existing entity catalogue.
Locate the convention by reading current VOCABULARY.md before
editing.

> **`docs/TOOL_AUTHORING.md` is not modified.** That doc is the
> durable architectural reference for the PR22 contract; it is
> not a tool inventory. C.1's six new tools obey the contract by
> registration (mechanically enforced via the test cited under
> Test Plan #3) — no doc edit is the right outcome.

## Test plan

Acceptance gate for C.1 implementation:

1. All tests in D8 pass.
2. Existing test suite passes unchanged (no regression to shot,
   version, media, layer, stack, or staged-ops tools).
3. PR22 mechanical compliance test passes with the six new tools
   registered. **This is the load-bearing contract check** — if
   PR22 compliance fails on any new tool, the implementation does
   not ship. Primary test:
   `tests/test_tool_contract_enforcement.py:200`
   (`test_pr22_every_registered_tool_satisfies_canonical_contract`).
   Sibling coverage at
   `tests/test_mcp_registry.py:485` (`test_invoke_tool_wraps_flat_args_for_params_schema`),
   `:539` (`test_invoke_tool_wraps_empty_args_for_params_schema`),
   `:564` (`test_invoke_tool_preserves_flat_args_for_non_wrapper_schema`),
   and `:647`
   (`test_existing_tool_schema_audit_separates_flat_and_wrapped_tools`).
4. `fbridge doctor` passes unchanged (no new daemon-side
   dependencies introduced).

## Doc plan

Acceptance gate for C.1 docs:

1. `docs/ASSET.md` exists and is grep-clean (no broken
   cross-links, no orphaned references).
2. `docs/VOCABULARY.md` cross-link is bidirectional.
3. Each of the six tools has a documented example in
   `docs/ASSET.md` § 3.
4. The "What's not in C.1" section names R-9 and R-5/R-10
   explicitly so a future reader knows where to look.

## File change manifest

**New files:**

- `tests/mcp/test_asset_tools.py`
- `docs/ASSET.md`

**Modified files:**

- `forge_bridge/core/vocabulary.py` — three alias lines added to
  `Status.from_string()` (D1).
- `forge_bridge/mcp/tools.py` — six Input classes + six handler
  functions added in a new section, placed after the existing shot
  tools (around line 627, before `list_versions`).
- `forge_bridge/mcp/registry.py` — six `register_tool(...)` calls
  added in `register_builtins()` (at `registry.py:290`) under a
  new section header.
- `docs/VOCABULARY.md` — Asset subsection or cross-link.

**Files NOT modified (this is intentional per L3 + B-5):**

- `forge_bridge/mcp/tools.py` existing `list_versions`,
  `register_publish`, `list_published_plates`, `get_shot_versions`,
  `snapshot_timeline` — Version-layer surfaces stay shot-flavored.
- `forge_bridge/store/models.py`, `forge_bridge/store/repo.py` — no
  schema or repo changes per R-2.
- `forge_bridge/store/migrations/versions/` — no new migration.
- `forge_bridge/server/router.py`, `forge_bridge/server/protocol.py` —
  the wire protocol already handles Asset generically; C.1 wraps
  what exists.
- `docs/TOOL_AUTHORING.md` — durable architectural reference for
  the PR22 contract, not a tool inventory. C.1's six new tools
  obey the contract by registration (mechanically enforced via
  the test cited under Test Plan #3); no doc edit is the right
  outcome. See D9 § rationale.

## Implementation guidance — ontology-leakage watch

Stage 1b (Creative) flagged the implementation surface where
asset-awareness most commonly spreads sideways: not in the named
deliverables, but in **helper abstractions**. The watch applies
during implementation, with Stage 2 review responsible for
catching any drift.

Surfaces to watch for accidental asset-awareness:

- **Utility functions** — formatters, validators, ID-resolution
  helpers. If `forge_get_asset` reuses a `_resolve_entity_id()`
  utility and that utility grows an `entity_type=` parameter to
  validate type, the ontology leaked into shared infrastructure.
  The right shape: dedicated Asset-side validation lives in the
  asset tool body; shared utilities stay entity-class-agnostic.
- **Serializers** — JSON envelope builders. If `_ok()` or
  `_envelope_json()` gains Asset-specific output shapes
  (e.g. always-include-asset_type), ontology-shape has crossed
  into the response substrate.
- **Shared query surfaces** — if `list_by_type` or `find_by_attribute`
  in `EntityRepo` gets a special case for assets, the repo layer
  knows about Asset semantics. R-2 prohibits this; the repo stays
  generic.
- **Registry helpers** — if `register_tool` grows a kwarg used
  only by Asset tools, the registration substrate knows about
  Asset. Per R-8: tool names carry affordance signal at the
  surface; the registration substrate stays generic.
- **Response envelope conventions** — if Asset tools introduce a
  new envelope key (`{"asset": {...}}` instead of just `{"asset_id":
  "...", ...}`), the envelope shape becomes ontology-aware.

**Stage 2 prompt** *(for the implementation-review pass after
commits land):* re-grep `entity_type`, `asset`, `asset_type`,
`is_asset`, and `Asset` across non-spec files modified or created
by C.1 commits. Any appearance in `forge_bridge/store/`,
`forge_bridge/server/`, `forge_bridge/mcp/registry.py`'s shared
infrastructure (as opposed to the asset-tool registration calls
themselves), or generic console/CLI helpers is a leakage finding.

The discipline: **C.1 surfaces are local; substrate stays
generic.** If a generic abstraction "wants" to learn about Asset,
the answer is to keep the abstraction generic and put the Asset
knowledge in the tool body instead.

## Dependencies and sequencing

- **Blocks:** Nothing in v1.7 milestone is blocked by C.1.
- **Blocked by:** Nothing; the substrate is ready
  (`3020ae9` framing converged).
- **Parallel with:** Thread A (A.1 phase plan, when drafted) —
  no substrate overlap.
- **C.2 depends on C.1** — the CLI surface in C.2 calls the C.1
  MCP tools via the existing client-CLI bridge. C.2 cannot start
  until C.1 lands.
- **C.3 depends on C.1** — the consumer proof investigation needs
  the C.1 surface to evaluate against, but does not need C.2.

## Stage 1b checklist

Items DT (or substitute reviewer) should verify before this spec
clears for implementation handoff:

- [ ] **Locks L1-L3 are mutually consistent and exhaustive.** Any
  scope question that could surface during implementation has an
  answer in a Lock or a Minor Lock — or it's explicitly out of
  scope.
- [ ] **PR22 patterns are correctly assigned.** Walk the L1 table
  and confirm each Input model's field requirements match the
  declared pattern. Pattern-C with all-optional fields is the
  forbidden anti-pattern.
- [ ] **MOL-3 — `asset_type` required at MCP layer.** Confirm
  this is the right discipline at the affordance layer (the
  Asset class default `"generic"` is correctly bypassed by the
  MCP-layer requirement).
- [ ] **No silent surface expansion.** Confirm no minor lock or
  deliverable smuggles in functionality beyond the six tools +
  three aliases + tests + docs. (Particularly: confirm
  `forge_update_asset` does not become a back-door for changing
  entity_type, name uniqueness, or asset_type taxonomy
  enforcement.)
- [ ] **MOL-6 verifiable from the code surface.** The input model
  has no `entity_type` field. Confirm this is sufficient guard;
  no implementation-time creativity required.
- [ ] **Test matrix coverage matches the L/MOL surface.** Each
  Lock and each load-bearing Minor Lock has at least one named
  test row in D8.
- [ ] **File change manifest is complete.** No new file the spec
  forgets; no modified file missing from the list.
- [ ] **`forge_bridge.__all__` stays at 19.** No new public-API
  exports — MCP tools are private to the mcp module and exposed
  through FastMCP registration, not the package `__all__`. C.1
  preserves the v1.4.x → v1.6 → v1.7 invariant.
- [ ] **No new alembic migration.** Confirm zero changes under
  `forge_bridge/store/migrations/versions/`.
- [ ] **Cross-thread coherence with A.** Nothing in C.1 modifies
  surfaces Thread A operates on (`llm/router.py`,
  `console/handlers.py`, `console/_engine.py`,
  `graph/commit.py`, `graph/mutation.py`). Confirm by inspection.
- [ ] **Semantic-coupling check (Creative, Stage 1b).** Does any
  deliverable introduce a semantic dependency where Version
  tooling, publish semantics, version identity, or existing tool
  assumptions must become asset-aware to remain coherent? L3
  prohibits direct modification of Version tools; this check
  catches the subtler shape — accidental incompleteness without
  modification. If a Version tool would now silently behave
  differently for `parent_type="asset"` versions vs `="shot"`,
  C.1 has crossed its boundary even without touching the file.

## Status

**Phase plan, Stage 1b cleared 2026-05-27.** Creative ratified
the four user-flagged points (MOL-3, MOL-6, L3) with three
tightenings (MOL-3 constitutional rationale; MOL-6 doctrined
guard; L3 semantic-coupling Stage 1b checklist item; plus the
ontology-leakage watch under Implementation Guidance). DT gave
green-after-revisions with eight blocking grounding fixes
(B-1..B-8), three substantive room rulings (S-1..S-3 specific
text supplied), and D1 alias choice handed to the room.

**D1 Path A ratified 2026-05-27** — verb form `"invalidate"`
remains excluded; L2 rationale revised with the state-vs-authority
constitutional distinction Creative drew, and the convention is
named going forward (state-descriptor / past-participle only;
existing `omit` alias acknowledged as inherited inconsistency).

**Next motion.** Implementation hands off against this spec.
Commits land in roughly D1..D9 order; the final commit closes
the phase and a brief phase-close cursor lands at
`.planning/phases/C.1-thread-c-asset-operability/C.1-CLOSE.md`.

Stage 2 review applies the ontology-leakage watch to landed
commits per the Implementation Guidance section.
