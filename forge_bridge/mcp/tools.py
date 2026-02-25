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
