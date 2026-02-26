"""
MCP tool implementations — all backed by forge-bridge AsyncClient.

Each function is registered with FastMCP via mcp.tool(). Functions
receive Pydantic model inputs (or no input for parameterless tools)
and return JSON strings that the LLM sees as tool results.

Design principles:
  - Tools are thin: validate input, call client, format output
  - Never import from forge_bridge.store or forge_bridge.server directly
  - All pipeline data flows through get_client()
  - Human-readable JSON output — the LLM reads this
  - Errors are returned as JSON with an "error" key, not raised
    (MCP tools should always return something, not crash)
"""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field


def _client():
    """Lazy import to avoid circular at module level."""
    from forge_bridge.mcp.server import get_client
    return get_client()


def _ok(data) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(message: str, code: str = "ERROR") -> str:
    return json.dumps({"error": message, "code": code}, indent=2)


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────

async def ping() -> str:
    """Check forge-bridge server connectivity.

    Returns connection status, session ID, and registry summary
    (role count, relationship type count).
    """
    try:
        from forge_bridge.server.protocol import ping as make_ping
        client = _client()
        await client.request(make_ping())
        return _ok({
            "status":    "connected",
            "session_id": client.session_id,
            "server_url": client.server_url,
            "registry":  {
                "roles":              len(client.registry_summary.get("roles", [])),
                "relationship_types": len(client.registry_summary.get("relationship_types", [])),
            },
        })
    except Exception as e:
        return _err(f"forge-bridge unreachable: {e}", "CONNECTION_ERROR")


# ─────────────────────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────────────────────

async def list_projects() -> str:
    """List all pipeline projects in forge-bridge.

    Returns project IDs, names, codes, and creation times.
    """
    try:
        from forge_bridge.server.protocol import project_list
        result = await _client().request(project_list())
        projects = result.get("projects", [])
        return _ok({
            "count":    len(projects),
            "projects": projects,
        })
    except Exception as e:
        return _err(str(e))


class GetProjectInput(BaseModel):
    project_id: str = Field(..., description="Project UUID")


async def get_project(params: GetProjectInput) -> str:
    """Get details for a specific project by ID."""
    try:
        from forge_bridge.server.protocol import project_get
        result = await _client().request(project_get(params.project_id))
        return _ok(result)
    except Exception as e:
        return _err(str(e))


class CreateProjectInput(BaseModel):
    name: str = Field(..., description="Full project name e.g. 'Epic Sixty'")
    code: str = Field(..., description="Short project code e.g. 'EP60' — must be unique")
    metadata: Optional[dict] = Field(default=None, description="Optional key-value metadata")


async def create_project(params: CreateProjectInput) -> str:
    """Create a new project in forge-bridge.

    The project code must be unique across all projects.
    Returns the new project UUID.
    """
    try:
        from forge_bridge.server.protocol import project_create
        result = await _client().request(
            project_create(params.name, params.code, params.metadata)
        )
        return _ok({
            "created":    True,
            "project_id": result["project_id"],
            "name":       params.name,
            "code":       params.code,
        })
    except Exception as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────
# Shots
# ─────────────────────────────────────────────────────────────

class ListShotsInput(BaseModel):
    project_id: str = Field(..., description="Project UUID")
    status: Optional[str] = Field(
        default=None,
        description="Filter by status: 'pending', 'in_progress', 'review', 'approved', 'on_hold'"
    )


async def list_shots(params: ListShotsInput) -> str:
    """List all shots in a project.

    Returns shot IDs, names, statuses, and cut information.
    Optionally filter by status.
    """
    try:
        from forge_bridge.server.protocol import entity_list
        result = await _client().request(entity_list("shot", params.project_id))
        shots = result.get("entities", [])
        if params.status:
            shots = [s for s in shots if s.get("status") == params.status]
        return _ok({
            "project_id": params.project_id,
            "count":      len(shots),
            "shots":      shots,
        })
    except Exception as e:
        return _err(str(e))


class GetShotInput(BaseModel):
    shot_id: str = Field(..., description="Shot UUID")
    include_stack: bool = Field(
        default=True,
        description="Include the shot's layer stack (primary, matte, reference etc.)"
    )


async def get_shot(params: GetShotInput) -> str:
    """Get details for a specific shot, optionally including its layer stack.

    The stack shows all layers (primary, matte, reference, etc.) with their
    roles, orders, and associated version/media IDs.
    """
    try:
        from forge_bridge.server.protocol import entity_get, query_shot_stack
        client = _client()
        shot = await client.request(entity_get(params.shot_id))
        result = {"shot": shot}
        if params.include_stack:
            stack = await client.request(query_shot_stack(params.shot_id))
            result["stack"] = stack
        return _ok(result)
    except Exception as e:
        return _err(str(e))


class CreateShotInput(BaseModel):
    project_id:  str = Field(..., description="Project UUID")
    sequence_id: str = Field(..., description="Sequence UUID the shot belongs to")
    name:        str = Field(..., description="Shot name/code e.g. 'EP60_010'")
    layers: list[dict] = Field(
        default=[{"role": "primary"}, {"role": "matte"}, {"role": "reference"}],
        description=(
            "Layers to create. Each dict needs 'role' (string) and optionally 'order' (int). "
            "Standard roles: primary, matte, reference, audio, comp. "
            "Layers are created in order and assigned to the shot's stack."
        )
    )
    cut_in:  Optional[str] = Field(default=None, description="Cut in timecode e.g. '01:00:00:00'")
    cut_out: Optional[str] = Field(default=None, description="Cut out timecode e.g. '01:00:08:00'")


async def create_shot(params: CreateShotInput) -> str:
    """Create a new shot with a stack and layers.

    Creates the shot entity, a stack, and all specified layers in one
    operation. Returns IDs for the shot, stack, and each layer by role.

    Example layers: [{"role": "primary"}, {"role": "matte"}, {"role": "reference"}]
    """
    try:
        from forge_bridge.server.protocol import (
            entity_create, relationship_create,
        )
        client = _client()

        # Shot
        shot_attrs = {"sequence_id": params.sequence_id}
        if params.cut_in:
            shot_attrs["cut_in"] = params.cut_in
        if params.cut_out:
            shot_attrs["cut_out"] = params.cut_out

        shot_result = await client.request(entity_create(
            entity_type="shot",
            project_id=params.project_id,
            name=params.name,
            attributes=shot_attrs,
        ))
        shot_id = shot_result["entity_id"]

        # Stack
        stack_result = await client.request(entity_create(
            entity_type="stack",
            project_id=params.project_id,
            attributes={"shot_id": shot_id},
        ))
        stack_id = stack_result["entity_id"]

        # Layers
        layer_ids = {}
        for i, layer_spec in enumerate(params.layers):
            role  = layer_spec.get("role", "primary")
            order = layer_spec.get("order", i)
            layer_result = await client.request(entity_create(
                entity_type="layer",
                project_id=params.project_id,
                attributes={
                    "role":     role,
                    "stack_id": stack_id,
                    "order":    order,
                },
            ))
            layer_ids[role] = layer_result["entity_id"]

        return _ok({
            "created":   True,
            "shot_id":   shot_id,
            "shot_name": params.name,
            "stack_id":  stack_id,
            "layers":    layer_ids,
        })
    except Exception as e:
        return _err(str(e))


class UpdateShotStatusInput(BaseModel):
    shot_id: str = Field(..., description="Shot UUID")
    status: str = Field(
        ...,
        description="New status. One of: pending, in_progress, review, approved, on_hold"
    )
    note: Optional[str] = Field(
        default=None,
        description="Optional note to attach to the status change event"
    )


async def update_shot_status(params: UpdateShotStatusInput) -> str:
    """Update the status of a shot.

    Valid statuses: pending, in_progress, review, approved, on_hold.
    All connected clients (Flame, other MCP sessions) receive the
    status change event immediately.
    """
    try:
        from forge_bridge.server.protocol import entity_update
        await _client().request(entity_update(
            entity_id=params.shot_id,
            status=params.status,
        ))
        return _ok({
            "updated":  True,
            "shot_id":  params.shot_id,
            "status":   params.status,
        })
    except Exception as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────
# Versions
# ─────────────────────────────────────────────────────────────

class ListVersionsInput(BaseModel):
    shot_id:    Optional[str] = Field(default=None, description="Filter by shot UUID")
    project_id: str           = Field(...,          description="Project UUID (required)")


async def list_versions(params: ListVersionsInput) -> str:
    """List versions in a project, optionally filtered by shot.

    Returns version numbers, statuses, and parent shot information.
    """
    try:
        from forge_bridge.server.protocol import entity_list
        result = await _client().request(entity_list("version", params.project_id))
        versions = result.get("entities", [])
        if params.shot_id:
            versions = [
                v for v in versions
                if v.get("attributes", {}).get("parent_id") == params.shot_id
            ]
        return _ok({
            "project_id": params.project_id,
            "shot_id":    params.shot_id,
            "count":      len(versions),
            "versions":   versions,
        })
    except Exception as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────
# Shot stack
# ─────────────────────────────────────────────────────────────

class GetShotStackInput(BaseModel):
    shot_id: str = Field(..., description="Shot UUID")


async def get_shot_stack(params: GetShotStackInput) -> str:
    """Get all layers in a shot's stack, sorted by order.

    Returns the stack ID and a list of layers with their roles, orders,
    and associated version/media IDs. This is the co-selection context
    for Flame timeline operations — all layers that belong together.
    """
    try:
        from forge_bridge.server.protocol import query_shot_stack
        result = await _client().request(query_shot_stack(params.shot_id))
        return _ok(result)
    except Exception as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────
# Dependency graph
# ─────────────────────────────────────────────────────────────

class GetDependentsInput(BaseModel):
    entity_id: str = Field(..., description="Entity UUID to find dependents of")


async def get_dependents(params: GetDependentsInput) -> str:
    """Find all entities that depend on a given entity.

    This is the blast radius query — given an entity ID, returns all
    entities that have a relationship pointing to it. Useful for
    understanding what would be affected if this entity changes.

    Example: if a sequence changes its frame rate, which shots depend on it?
    """
    try:
        from forge_bridge.server.protocol import query_dependents
        result = await _client().request(query_dependents(params.entity_id))
        return _ok(result)
    except Exception as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

async def list_roles() -> str:
    """List all registered roles in the pipeline registry.

    Roles define what layers can exist in a shot stack: primary, matte,
    reference, audio, comp, etc. Each role has a stable UUID key that
    persists across renames.
    """
    try:
        from forge_bridge.server.protocol import role_list
        result = await _client().request(role_list())
        roles = result.get("roles", [])
        return _ok({
            "count": len(roles),
            "roles": roles,
        })
    except Exception as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────────────────────

class GetEventsInput(BaseModel):
    project_id: Optional[str] = Field(default=None, description="Filter by project UUID")
    entity_id:  Optional[str] = Field(default=None, description="Filter by entity UUID")
    limit:      int            = Field(default=20,   description="Max events to return (1-100)", ge=1, le=100)


async def get_events(params: GetEventsInput) -> str:
    """Get recent pipeline events from the audit log.

    Returns events in reverse-chronological order. Events record every
    state change: shots created/updated, versions published, roles
    renamed, clients connected, etc.

    Useful for: understanding recent activity, debugging, auditing.
    """
    try:
        from forge_bridge.server.protocol import query_events
        result = await _client().request(query_events(
            project_id=params.project_id,
            entity_id=params.entity_id,
            limit=params.limit,
        ))
        events = result.get("events", [])
        return _ok({
            "count":  len(events),
            "events": events,
        })
    except Exception as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────
# Flame timeline tools — publish workflow
# ─────────────────────────────────────────────────────────────

LAYER_ROLE_MAP = {
    "L01": "primary",
    "L02": "reference",
    "L03": "matte",
    "L04": "audio",
    "L05": "comp",
}


def _parse_shot_name(segment_name: str) -> tuple[str, str]:
    """Extract (shot_name, role) from a segment name like 'tst_010_graded_L01'.

    Layer suffix (L01/L02/L03...) maps to a role. If no suffix found,
    role defaults to 'primary'.
    """
    parts = segment_name.rsplit("_", 1)
    if len(parts) == 2 and parts[1] in LAYER_ROLE_MAP:
        return parts[0], LAYER_ROLE_MAP[parts[1]]
    return segment_name, "primary"


class CheckShotsInput(BaseModel):
    shot_names: list[str] = Field(
        ...,
        description="List of shot names to check e.g. ['tst_010', 'tst_020']",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Project UUID to scope the check. Uses first project if omitted.",
    )


async def check_shots(params: CheckShotsInput) -> str:
    """Pre-publish preflight — check which shots already exist in forge-bridge.

    For each shot name, reports:
    - exists: whether it's already registered
    - last_version: highest version number published so far
    - next_version: what the next publish should be numbered

    Use this before a Flame publish to know whether you're creating new
    shots or incrementing existing ones, and to catch naming conflicts.
    """
    try:
        client = _client()
        from forge_bridge.server.protocol import project_list, entity_list

        # Resolve project
        project_id = params.project_id
        if not project_id:
            projects = await client.request(project_list())
            proj_list = projects.get("projects", [])
            if not proj_list:
                return _err("No projects found in forge-bridge")
            project_id = proj_list[0]["id"]

        # Fetch all shots and versions in one pass each
        shots_result   = await client.request(entity_list("shot",    project_id))
        versions_result = await client.request(entity_list("version", project_id))

        shots_by_name = {s["name"]: s for s in shots_result.get("entities", [])}

        # Group versions by parent shot id
        versions_by_shot: dict[str, list] = {}
        for v in versions_result.get("entities", []):
            parent = v.get("attributes", {}).get("parent_id", "")
            versions_by_shot.setdefault(parent, []).append(v)

        results = []
        for name in params.shot_names:
            if name in shots_by_name:
                shot = shots_by_name[name]
                shot_id = shot["id"]
                vers = versions_by_shot.get(shot_id, [])
                last_v = max(
                    (v.get("attributes", {}).get("version_number", 0) for v in vers),
                    default=0,
                )
                results.append({
                    "name":          name,
                    "exists":        True,
                    "shot_id":       shot_id,
                    "status":        shot.get("status"),
                    "last_version":  last_v,
                    "next_version":  last_v + 1,
                    "version_count": len(vers),
                })
            else:
                results.append({
                    "name":          name,
                    "exists":        False,
                    "shot_id":       None,
                    "last_version":  0,
                    "next_version":  1,
                    "version_count": 0,
                })

        return _ok({
            "project_id":     project_id,
            "checked":        len(results),
            "new_shots":      sum(1 for r in results if not r["exists"]),
            "existing_shots": sum(1 for r in results if r["exists"]),
            "shots":          results,
        })
    except Exception as e:
        return _err(str(e))


class RegisterPublishInput(BaseModel):
    segment_name:  str            = Field(..., description="Flame segment name e.g. 'tst_010_graded_L01'")
    output_path:   str            = Field(..., description="Full output path on disk")
    start_frame:   int            = Field(..., description="First frame number")
    end_frame:     int            = Field(..., description="Last frame number")
    colour_space:  str            = Field(default="", description="Colour space name e.g. 'ACEScg'")
    project_id:    Optional[str]  = Field(default=None, description="Project UUID")
    sequence_name: Optional[str]  = Field(default=None, description="Sequence name this shot belongs to")


async def register_publish(params: RegisterPublishInput) -> str:
    """Register a single published component in forge-bridge.

    Call this once per exported segment after a Flame publish completes.
    Derives the shot name and role from the segment name automatically:
    - 'tst_010_graded_L01' → shot='tst_010_graded', role='primary'
    - 'tst_010_graded_L02' → shot='tst_010_graded', role='reference'
    - 'tst_010_graded_L03' → shot='tst_010_graded', role='matte'

    Creates the Shot if it doesn't exist, then creates a Version and
    Media record linked to it.
    """
    try:
        client = _client()
        from forge_bridge.server.protocol import (
            project_list, entity_list, entity_create, relationship_create, location_add,
        )

        shot_name, role = _parse_shot_name(params.segment_name)

        # Resolve project
        project_id = params.project_id
        if not project_id:
            projects = await client.request(project_list())
            proj_list = projects.get("projects", [])
            if not proj_list:
                return _err("No projects found in forge-bridge")
            project_id = proj_list[0]["id"]

        # Find or create shot
        shots_result = await client.request(entity_list("shot", project_id))
        shots_by_name = {s["name"]: s for s in shots_result.get("entities", [])}

        if shot_name in shots_by_name:
            shot_id = shots_by_name[shot_name]["id"]
            shot_created = False
        else:
            shot_result = await client.request(entity_create(
                entity_type="shot",
                project_id=project_id,
                name=shot_name,
                attributes={
                    "sequence_name": params.sequence_name or "",
                    "status": "in_progress",
                },
            ))
            shot_id = shot_result["id"]
            shot_created = True

        # Count existing versions for this shot to get next version number
        versions_result = await client.request(entity_list("version", project_id))
        shot_versions = [
            v for v in versions_result.get("entities", [])
            if v.get("attributes", {}).get("shot_id") == shot_id
        ]
        next_version = len(shot_versions) + 1

        # Create version entity
        version_result = await client.request(entity_create(
            entity_type="version",
            project_id=project_id,
            name=f"{shot_name}_v{next_version:03d}",
            attributes={
                "shot_id":        shot_id,
                "role":           role,
                "version_number": next_version,
                "start_frame":    params.start_frame,
                "end_frame":      params.end_frame,
                "colour_space":   params.colour_space,
                "segment_name":   params.segment_name,
            },
        ))
        version_id = version_result["id"]

        # Link version → shot
        await client.request(relationship_create(
            from_id=version_id,
            to_id=shot_id,
            relationship_type="version_of",
        ))

        # Register output path as a location
        if params.output_path:
            await client.request(location_add(
                entity_id=version_id,
                path=params.output_path,
                location_type="render",
            ))

        return _ok({
            "shot_name":      shot_name,
            "shot_id":        shot_id,
            "shot_created":   shot_created,
            "role":           role,
            "version_id":     version_id,
            "version_number": next_version,
            "output_path":    params.output_path,
        })
    except Exception as e:
        return _err(str(e))


async def snapshot_timeline() -> str:
    """Snapshot the current Flame timeline — all sequences and their segments.

    Traverses the correct Flame 2026 hierarchy:
      desktop → reel_groups → reels → sequences → versions → tracks → segments

    Returns a structured view of every sequence on the desktop, with
    all tracks and segment names. Useful for pre-publish review and
    understanding what shots are in the current project.

    Segment names follow the FORGE convention: <shot>_<descriptor>_L01/L02/L03
    """
    code = """
import flame, json

def snap():
    desktop = flame.projects.current_project.current_workspace.desktop
    result = []
    for rg in desktop.reel_groups:
        rg_name = str(rg.name)
        for reel in rg.reels:
            reel_name = str(reel.name)
            seqs = reel.sequences or []
            for seq in seqs:
                seq_name = str(seq.name)
                tracks_data = []
                try:
                    for ver in (seq.versions or []):
                        for track in (ver.tracks or []):
                            segs = []
                            for seg in (track.segments or []):
                                seg_name = str(seg.name) if seg.name else ''
                                if seg_name:
                                    segs.append({
                                        'name':        seg_name,
                                        'start_frame': int(seg.start_frame) if seg.start_frame else None,
                                        'duration':    int(seg.duration) if seg.duration else None,
                                        'tape_name':   str(seg.tape_name) if seg.tape_name else '',
                                        'shot_name':   str(seg.shot_name) if seg.shot_name else '',
                                    })
                            if segs:
                                tracks_data.append({
                                    'name':     str(track.name) if track.name else '',
                                    'segments': segs,
                                })
                except Exception as e:
                    tracks_data.append({'error': str(e)})
                result.append({
                    'reel_group': rg_name,
                    'reel':       reel_name,
                    'sequence':   seq_name,
                    'tracks':     tracks_data,
                    'track_count': len(tracks_data),
                    'segment_count': sum(len(t.get('segments', [])) for t in tracks_data),
                })
    return result

import json
print(json.dumps(snap()))
"""
    try:
        from forge_mcp import bridge
        data = await bridge.execute_json(code)
        sequences = data if isinstance(data, list) else []

        total_segs = sum(s.get("segment_count", 0) for s in sequences)

        # Derive unique shot names from segment names
        shot_names = set()
        for seq in sequences:
            for track in seq.get("tracks", []):
                for seg in track.get("segments", []):
                    name = seg.get("name", "")
                    shot, _ = _parse_shot_name(name)
                    if shot:
                        shot_names.add(shot)

        return _ok({
            "sequence_count": len(sequences),
            "total_segments":  total_segs,
            "unique_shots":    sorted(shot_names),
            "sequences":       sequences,
        })
    except Exception as e:
        return _err(str(e))
