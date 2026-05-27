# Asset

Asset is the canonical forge-bridge entity for any durable production object
that is not a Shot but still needs persistent identity in the graph. Characters,
vehicles, environments, materials, references, OTIO edits, CAD sources, USD
compositions, lighting setups, and deliverables can all be Assets when the
pipeline needs to track them across locations, relationships, versions, and
events.

See also: [VOCABULARY.md](VOCABULARY.md#asset).

## Asset vs Shot

A Shot is a time-bounded unit of work inside a Sequence. It has editorial
position, cut context, and shot-stack structure.

An Asset is a reusable or durable object that may be used by one shot, many
shots, or no shot yet. It does not imply editorial position. Asset identity is
therefore about production object identity, not sequence placement.

## MCP Tools

### forge_create_asset

Creates an Asset entity in a project. `asset_type` is required at the MCP layer:
the operator must name the type rather than silently falling back to `generic`.

Input:

```json
{
  "project_id": "PROJECT_UUID",
  "name": "Hero Car",
  "asset_type": "vehicle_spec",
  "status": "proposed",
  "attributes": {"department": "art"}
}
```

Output includes `created`, `asset_id`, `asset_name`, and `asset_type`.

### forge_list_assets

Lists Asset summaries. Optional filters: `project_id`, `asset_type`, `status`,
and `limit`.

Example:

```json
{
  "project_id": "PROJECT_UUID",
  "asset_type": "vehicle_spec",
  "status": "published"
}
```

Output contains `count` and `assets`, where each asset summary includes
`asset_id`, `name`, `asset_type`, `status`, and `created_at`.

### forge_get_asset

Gets the full Asset payload by UUID, including locations and relationships.

Example:

```json
{"asset_id": "ASSET_UUID"}
```

### forge_update_asset

Updates Asset fields without changing the entity's identity class. The tool can
update `name`, `status`, `asset_type`, and merge `attributes`. `entity_type` is
not an input field and a smuggled `entity_type` attribute is ignored by the tool.

Example:

```json
{
  "asset_id": "ASSET_UUID",
  "status": "invalidated",
  "attributes": {"review_note": "superseded by vendor v003"}
}
```

### forge_attach_asset_location

Attaches a filesystem path or URL to an Asset.

Example:

```json
{
  "asset_id": "ASSET_UUID",
  "path": "/show/assets/hero_car/model.usd",
  "storage_type": "network",
  "priority": 10
}
```

Output contains `attached`, `asset_id`, and `path`.

### forge_relate_asset

Creates a relationship edge from an Asset to any target entity.

Example:

```json
{
  "asset_id": "ASSET_UUID",
  "target_id": "SHOT_OR_MEDIA_OR_VERSION_UUID",
  "rel_type": "references",
  "attributes": {"note": "lookdev reference"}
}
```

System relationship types are `member_of`, `version_of`, `derived_from`,
`references`, `peer_of`, `consumes`, and `produces`. Custom relationship types
may be passed by UUID string.

## Substrate Participation

Asset inherits the same substrate traits as other canonical entities:

- Locations: an Asset can have local, network, cloud, archive, or clip locations.
- Relationships: an Asset can connect to other entities through the seven system
  relationship types listed above.
- Events: Asset create/update/location/relationship operations flow through the
  existing bridge event substrate.
- Versions: Version already supports `parent_type="asset"`, so Asset can have
  version records without a schema change.

## asset_type

`asset_type` is an open vocabulary string, stored in the entity attributes JSONB
payload and queryable through the existing attributes index. Examples include
`vehicle_spec`, `cad_source`, `usd_composition`, `environment`,
`location_sheet`, `road_surface`, `tree`, `building`, `material`,
`camera_move`, `lighting_setup`, `style_sheet`, `reference_pack`, `otio_edit`,
and `deliverable`.

C.1 deliberately does not promote `asset_type` into a fixed enum or schema
column. A future motion can promote common values once real usage demonstrates
which taxonomy deserves that weight.

## Not In C.1

C.1 does not ship `forge_publish_asset_version` and does not make existing
Version or publish tools asset-aware; that boundary is R-9.

C.1 does not add a Console UI Assets view. CLI and consumer surfaces follow in
later phases, including C.2 and the C.3 projekt-forge consumer proof. R-5 and
R-10 govern that consumer work.
