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
import uuid
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from forge_bridge.console.handlers import _envelope_json


# ─────────────────────────────────────────────────────────────────────────────
# Phase 14 (FB-B) — Staged-ops MCP tool input models + impl functions
# ─────────────────────────────────────────────────────────────────────────────

# Valid status values for staged operations (D-01).
# Re-declared here to avoid importing from handlers.py in a circular path;
# the frozenset is identical to _STAGED_STATUSES in console/handlers.py.
_STAGED_STATUSES = frozenset({"proposed", "approved", "rejected", "executed", "failed"})


class ListStagedInput(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="proposed|approved|rejected|executed|failed",
    )
    limit: int = Field(default=50, description="Max records (1-500, silently clamped)")
    offset: int = Field(default=0, description="Pagination offset")
    project_id: Optional[str] = Field(default=None, description="Project UUID filter")


class GetStagedInput(BaseModel):
    id: str = Field(..., description="Staged operation UUID")


class ApproveStagedInput(BaseModel):
    id: str = Field(..., description="Staged operation UUID")
    actor: str = Field(
        ...,
        min_length=1,
        description="Caller identity (free string, non-empty per D-07)",
    )

    @field_validator("actor")
    @classmethod
    def actor_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("actor must not be whitespace-only")
        return v


class RejectStagedInput(BaseModel):
    id: str = Field(..., description="Staged operation UUID")
    actor: str = Field(
        ...,
        min_length=1,
        description="Caller identity (free string, non-empty per D-07)",
    )

    @field_validator("actor")
    @classmethod
    def actor_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("actor must not be whitespace-only")
        return v


# ── Implementation functions ─────────────────────────────────────────────────
# These functions are called from register_console_resources() closures (D-17
# revised, Solution C).  They are intentionally underscore-prefixed to signal
# that they are NOT the registered tool names — they are the bodies the closures
# delegate to so that console_read_api and session_factory are captured at the
# registration site without passing state through module globals.


async def _list_staged_impl(params: "ListStagedInput", console_read_api) -> str:
    """List staged operations with optional status/project_id filter + pagination."""
    if params.status is not None and params.status not in _STAGED_STATUSES:
        return json.dumps({
            "error": {
                "code": "invalid_filter",
                "message": (
                    f"unknown status {params.status!r}; "
                    f"expected one of {sorted(_STAGED_STATUSES)}"
                ),
            }
        })
    limit = max(1, min(params.limit, 500))   # D-05 clamp
    offset = max(0, params.offset)
    project_id_uuid: uuid.UUID | None = None
    if params.project_id is not None:
        try:
            project_id_uuid = uuid.UUID(params.project_id)
        except ValueError:
            return json.dumps({"error": {"code": "bad_request", "message": "invalid project_id"}})
    records, total = await console_read_api.get_staged_ops(
        status=params.status, limit=limit, offset=offset, project_id=project_id_uuid,
    )
    return _envelope_json(
        [r.to_dict() for r in records],
        limit=limit, offset=offset, total=total,
    )


async def _get_staged_impl(params: "GetStagedInput", console_read_api) -> str:
    """Get a single staged operation by UUID."""
    try:
        op_id = uuid.UUID(params.id)
    except ValueError:
        return json.dumps({"error": {"code": "bad_request", "message": "invalid staged_operation id"}})
    op = await console_read_api.get_staged_op(op_id)
    if op is None:
        # Return data=None envelope (NOT an error) per the byte-identity table in
        # RESEARCH.md; there is no HTTP GET single-op route so MCP shape is canonical.
        return _envelope_json(None)
    return _envelope_json(op.to_dict())


async def _approve_staged_impl(params: "ApproveStagedInput", session_factory) -> str:
    """Approve a staged operation — write path via session_factory closure (D-04)."""
    from forge_bridge.store.staged_operations import StagedOpRepo, StagedOpLifecycleError
    try:
        op_id = uuid.UUID(params.id)
    except ValueError:
        return json.dumps({"error": {"code": "bad_request", "message": "invalid staged_operation id"}})
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        try:
            op = await repo.approve(op_id, approver=params.actor)
        except StagedOpLifecycleError as exc:
            if exc.from_status is None:
                return json.dumps({
                    "error": {
                        "code": "staged_op_not_found",
                        "message": f"no staged_operation with id {op_id}",
                    }
                })
            return json.dumps({
                "error": {
                    "code": "illegal_transition",
                    "message": str(exc),
                    "current_status": exc.from_status,
                }
            })
        await session.commit()
    return _envelope_json(op.to_dict())


async def _reject_staged_impl(params: "RejectStagedInput", session_factory) -> str:
    """Reject a staged operation — write path via session_factory closure (D-04)."""
    from forge_bridge.store.staged_operations import StagedOpRepo, StagedOpLifecycleError
    try:
        op_id = uuid.UUID(params.id)
    except ValueError:
        return json.dumps({"error": {"code": "bad_request", "message": "invalid staged_operation id"}})
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        try:
            op = await repo.reject(op_id, actor=params.actor)
        except StagedOpLifecycleError as exc:
            if exc.from_status is None:
                return json.dumps({
                    "error": {
                        "code": "staged_op_not_found",
                        "message": f"no staged_operation with id {op_id}",
                    }
                })
            return json.dumps({
                "error": {
                    "code": "illegal_transition",
                    "message": str(exc),
                    "current_status": exc.from_status,
                }
            })
        await session.commit()
    return _envelope_json(op.to_dict())


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
    """Forge: list all pipeline projects tracked by forge-bridge.

    Reads from the forge-bridge pipeline registry (Postgres). Returns
    every project's UUID, full name, short code, and creation time.

    Use this tool ONLY when:
    - the user asks about pipeline-level *projects* across the studio
    - the user wants project IDs, codes, or a roster of projects

    Do NOT use this tool for:
    - the currently-open Flame project → use flame_get_project
    - Flame libraries inside a project → use flame_list_libraries
    - shots within a project → use forge_list_shots
    - media or plates → use forge_list_media / forge_list_published_plates
    - one specific project by ID → use forge_get_project

    This tool is specific to pipeline projects, NOT Flame libraries or
    Flame's currently-loaded project.
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
    """Forge: get details for one pipeline project by UUID.

    Reads a single project from the forge-bridge pipeline registry. The
    user must already know the project's UUID (use forge_list_projects
    to find one).

    Use this tool ONLY when:
    - the user has a specific project UUID and wants its full record
    - the user wants metadata for one named pipeline project

    Do NOT use this tool for:
    - the currently-open Flame project → use flame_get_project
    - listing all projects → use forge_list_projects
    - shots inside a project → use forge_list_shots
    - the Flame workspace's libraries → use flame_list_libraries

    This tool is for pipeline registry lookup by UUID, not Flame state.
    """
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
    """Forge: list shots in a pipeline project.

    Reads from the forge-bridge pipeline registry. Returns shot IDs,
    names, statuses, and cut info. Requires a project UUID; optional
    status filter.

    Use this tool ONLY when:
    - the user wants the *shots* in a specific pipeline project
    - the user provides (or implies) a project UUID

    Do NOT use this tool for:
    - listing pipeline projects → use forge_list_projects
    - one specific shot by ID → use forge_get_shot
    - shot versions → use forge_list_versions or forge_get_shot_versions
    - Flame's loaded sequences → use flame_get_sequence_segments
    - Flame libraries or media → use flame_list_libraries / flame_find_media

    This tool needs a project_id; without one, ask the user or call
    forge_list_projects first.
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
    """Forge: get one pipeline shot by UUID, optionally with its layer stack.

    Reads a single shot from the forge-bridge pipeline registry. The
    stack (when included) lists all layers — primary, matte, reference,
    etc. — with their roles, ordering, and version/media references.

    Use this tool ONLY when:
    - the user has a specific shot UUID and wants its full record
    - the user wants the layer stack of one named shot

    Do NOT use this tool for:
    - listing all shots in a project → use forge_list_shots
    - shot versions → use forge_get_shot_versions or forge_list_versions
    - Flame's loaded sequences → use flame_get_sequence_segments
    - Flame project / library state → use flame_get_project / flame_list_libraries

    This tool requires a shot_id (UUID); without one, run forge_list_shots first.
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
    """Forge: list versions in a pipeline project, optionally narrowed to one shot.

    Reads version records (numbered iterations) from the forge-bridge
    pipeline registry. Requires a project_id; an optional shot_id narrows
    the result to one shot's versions.

    Use this tool ONLY when:
    - the user asks about *versions* (numbered iterations) in the pipeline
    - the user has a project UUID and (optionally) a shot UUID

    Do NOT use this tool for:
    - listing pipeline shots → use forge_list_shots
    - listing pipeline projects → use forge_list_projects
    - published plates (final delivery media) → use forge_list_published_plates
    - all plate versions for one shot → use forge_get_shot_versions
    - Flame sequence versions in the live session → use flame_inspect_sequence_versions

    This tool is for the pipeline registry's version table; Flame
    sequence versions are a different concept.
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
    """Forge: list registered shot-layer *roles* in the pipeline registry.

    Roles are the controlled vocabulary for layers in a shot stack —
    e.g. primary, matte, reference, audio, comp. Each role has a stable
    UUID key that survives renames.

    Use this tool ONLY when:
    - the user asks about layer *roles* (the role vocabulary)
    - the user wants the list of valid stack-layer types

    Do NOT use this tool for:
    - listing shots → use forge_list_shots
    - the layers in one specific shot → use forge_get_shot_stack
    - listing projects → use forge_list_projects
    - listing libraries (a Flame concept) → use flame_list_libraries

    This tool is the role registry, not a list of layers in a shot.
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

def _parse_shot_name(segment_name: str) -> tuple[str, str, int]:
    """Parse a FORGE segment name into (shot_name, role, layer).

    FORGE naming convention: {shot_name}_{role}_L{track##}
    e.g. 'tst_010_graded_L01'  → ('tst_010', 'graded', 1)
         'data_080_graded_L02' → ('data_080', 'graded', 2)
         'tst_020_raw_L01'     → ('tst_020', 'raw', 1)

    Shot name format: {prefix}_{number} — always prefix_NNN.
    Role: the descriptor between shot number and layer suffix (graded, raw,
          denoised, flat, external, scans, stock, filler).
    Layer: track number from _L## suffix (1-based).

    Returns ('', '', 0) if the name doesn't match the convention.
    """
    import re
    # Match: word_NNN_role_L##  where NNN is digits, ## is digits
    m = re.match(r'^([A-Za-z]\w+_\d+)_(.+)_L(\d+)$', segment_name)
    if m:
        shot_name = m.group(1)
        role      = m.group(2)
        layer     = int(m.group(3))
        return shot_name, role, layer
    return "", "", 0


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

        shot_name, role, layer = _parse_shot_name(params.segment_name)
        if not shot_name:
            return _err(f"Could not parse segment name '{params.segment_name}' — expected format: shot_NNN_role_L##")

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
                                    import re
                                    m = re.match('^([A-Za-z]\\w+_\\d+)_(.+)_L(\\d+)$', seg_name)
                                    segs.append({
                                        'name':        seg_name,
                                        'shot_name':   m.group(1) if m else '',
                                        'role':        m.group(2) if m else '',
                                        'layer':       int(m.group(3)) if m else 0,
                                        'start_frame': int(seg.start_frame) if seg.start_frame else None,
                                        'duration':    int(seg.duration) if seg.duration else None,
                                        'tape_name':   str(seg.tape_name) if seg.tape_name else '',
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
        from forge_bridge import bridge
        data = await bridge.execute_json(code)
        sequences = data if isinstance(data, list) else []

        total_segs = sum(s.get("segment_count", 0) for s in sequences)

        # Derive unique shot names from segment names
        shot_names = set()
        for seq in sequences:
            for track in seq.get("tracks", []):
                for seg in track.get("segments", []):
                    name = seg.get("name", "")
                    shot, role, layer = _parse_shot_name(name)
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



# ─────────────────────────────────────────────────────────────
# Lineage & impact
# ─────────────────────────────────────────────────────────────

class GetShotLineageInput(BaseModel):
    shot_name:  str           = Field(..., description="Shot name e.g. 'ABC_010'")
    project_id: Optional[str] = Field(default=None, description="Project UUID — defaults to first project")


async def get_shot_lineage(params: GetShotLineageInput) -> str:
    """Get the full publish lineage for a shot.

    Traverses the Version → Media graph for the shot, returning every
    published version with its produced media entities, verification
    status, file paths, colour space, and frame range.

    Useful for understanding the current state of a shot's deliverables
    and whether they've been verified on disk.
    """
    try:
        from forge_bridge.server.protocol import project_list, entity_list, entity_get, query_dependents
        client = _client()

        # Resolve project
        project_id = params.project_id
        if not project_id:
            projects = await client.request(project_list())
            proj_list = projects.get("projects", [])
            if not proj_list:
                return _err("No projects in forge-bridge")
            project_id = proj_list[0]["id"]

        # Find shot
        shots = (await client.request(entity_list("shot", project_id))).get("entities", [])
        shot = next((s for s in shots if s.get("name") == params.shot_name), None)
        if not shot:
            return _err(f"Shot '{params.shot_name}' not found")
        shot_id = shot["id"]

        # Get all versions for this shot
        all_versions = (await client.request(entity_list("version", project_id))).get("entities", [])
        shot_versions = [
            v for v in all_versions
            if v.get("attributes", {}).get("shot_id") == shot_id
        ]

        # Get all media for this project
        all_media = (await client.request(entity_list("media", project_id))).get("entities", [])
        media_by_id = {m["id"]: m for m in all_media}

        # For each version, find its produced media via dependents
        lineage = []
        for v in sorted(shot_versions, key=lambda x: x.get("attributes", {}).get("version_number", 0)):
            attrs = v.get("attributes", {})
            deps = await client.request(query_dependents(v["id"]))
            dependent_ids = deps.get("dependents", [])

            produced_media = []
            for mid in dependent_ids:
                m = media_by_id.get(mid)
                if not m:
                    continue
                m_attrs = m.get("attributes", {})
                locs = m.get("locations", [])
                path = next((l["path"] for l in locs if l.get("storage_type") == "local"), "")
                if not path and locs:
                    path = locs[0].get("path", "")
                produced_media.append({
                    "media_id":    m["id"],
                    "name":        m.get("name", ""),
                    "status":      m.get("status", "pending"),
                    "kind":        m_attrs.get("kind", ""),
                    "colour_space": m_attrs.get("colour_space", ""),
                    "resolution":  m.get("resolution", ""),
                    "layer_index": m_attrs.get("layer_index"),
                    "path":        path,
                })

            lineage.append({
                "version_id":     v["id"],
                "version_name":   v.get("name", ""),
                "version_number": attrs.get("version_number", 0),
                "asset_name":     attrs.get("asset_name", ""),
                "sequence_name":  attrs.get("sequence_name", ""),
                "published_by":   attrs.get("published_by", ""),
                "media":          produced_media,
            })

        verified   = sum(1 for v in lineage for m in v["media"] if m["status"] == "verified")
        unverified = sum(1 for v in lineage for m in v["media"] if m["status"] != "verified")

        return _ok({
            "shot_name":        params.shot_name,
            "shot_id":          shot_id,
            "project_id":       project_id,
            "version_count":    len(lineage),
            "media_verified":   verified,
            "media_unverified": unverified,
            "lineage":          lineage,
        })
    except Exception as e:
        return _err(str(e))


class BlastRadiusInput(BaseModel):
    media_id:   Optional[str] = Field(default=None, description="Media entity UUID")
    media_name: Optional[str] = Field(default=None, description="Media name e.g. 'ABC_010_graded_L01' — used if media_id not provided")
    project_id: Optional[str] = Field(default=None, description="Project UUID — defaults to first project")


async def blast_radius(params: BlastRadiusInput) -> str:
    """Find what depends on a media entity — the blast radius of a change.

    Given a media entity (by ID or name), returns all versions that
    produced it and all shots that would be affected if this media
    changed or was republished.

    Useful for impact analysis: 'if I re-deliver this plate, what
    downstream work needs to be revisited?'
    """
    try:
        from forge_bridge.server.protocol import project_list, entity_list, entity_get, query_dependents
        client = _client()

        # Resolve project
        project_id = params.project_id
        if not project_id:
            projects = await client.request(project_list())
            proj_list = projects.get("projects", [])
            if not proj_list:
                return _err("No projects in forge-bridge")
            project_id = proj_list[0]["id"]

        # Resolve media entity
        media_id = params.media_id
        if not media_id:
            if not params.media_name:
                return _err("Provide either media_id or media_name")
            all_media = (await client.request(entity_list("media", project_id))).get("entities", [])
            match = next((m for m in all_media if m.get("name") == params.media_name), None)
            if not match:
                return _err(f"Media '{params.media_name}' not found")
            media_id = match["id"]

        media = await client.request(entity_get(media_id))
        m_attrs = media.get("attributes", {})
        locs = media.get("locations", [])
        path = next((l["path"] for l in locs if l.get("storage_type") == "local"), "")

        # What depends on this media? (what versions produced/consume it)
        deps = await client.request(query_dependents(media_id))
        dependent_ids = deps.get("dependents", [])

        # Resolve each dependent to a version + shot
        shots_by_id = {}
        affected_versions = []
        all_versions = (await client.request(entity_list("version", project_id))).get("entities", [])
        versions_by_id = {v["id"]: v for v in all_versions}
        all_shots = (await client.request(entity_list("shot", project_id))).get("entities", [])
        shots_lookup = {s["id"]: s for s in all_shots}

        for did in dependent_ids:
            v = versions_by_id.get(did)
            if not v:
                continue
            v_attrs = v.get("attributes", {})
            shot_id = v_attrs.get("shot_id", "")
            shot = shots_lookup.get(shot_id, {})
            shot_name = shot.get("name", "unknown")
            if shot_id:
                shots_by_id[shot_id] = shot_name
            affected_versions.append({
                "version_id":    v["id"],
                "version_name":  v.get("name", ""),
                "asset_name":    v_attrs.get("asset_name", ""),
                "shot_id":       shot_id,
                "shot_name":     shot_name,
                "sequence_name": v_attrs.get("sequence_name", ""),
            })

        return _ok({
            "media_id":        media_id,
            "media_name":      media.get("name", ""),
            "media_status":    media.get("status", ""),
            "colour_space":    m_attrs.get("colour_space", ""),
            "path":            path,
            "affected_shots":  list(shots_by_id.values()),
            "affected_count":  len(shots_by_id),
            "dependent_versions": affected_versions,
        })
    except Exception as e:
        return _err(str(e))


class ListMediaInput(BaseModel):
    project_id: Optional[str] = Field(default=None, description="Project UUID — defaults to first project")
    status:     Optional[str] = Field(
        default=None,
        description="Filter by status: 'pending', 'verified', 'failed', 'in_progress'"
    )
    shot_name:  Optional[str] = Field(default=None, description="Filter to a specific shot e.g. 'ABC_010'")
    kind:       Optional[str] = Field(default=None, description="Filter by media kind: 'grade', 'comp', 'raw'")


async def list_media(params: ListMediaInput) -> str:
    """Forge: list media entities (plates, renders) in the pipeline registry.

    Reads from forge-bridge's media table. Returns published plates,
    comp renders, etc. with verification status, file paths, and
    metadata. Useful for auditing deliverables or finding unverified /
    failed plates after a publish run.

    Use this tool ONLY when:
    - the user asks about *registered* media in the pipeline
    - the user wants verification-status / file-path metadata for plates

    Do NOT use this tool for:
    - searching the live Flame session for clips → use flame_find_media
    - listing published plates only → use forge_list_published_plates
    - shots / projects → use forge_list_shots / forge_list_projects
    - Flame libraries → use flame_list_libraries

    This tool reads pipeline-registry media, not what is currently
    loaded in Flame.
    """
    try:
        from forge_bridge.server.protocol import project_list, entity_list
        client = _client()

        # Resolve project
        project_id = params.project_id
        if not project_id:
            projects = await client.request(project_list())
            proj_list = projects.get("projects", [])
            if not proj_list:
                return _err("No projects in forge-bridge")
            project_id = proj_list[0]["id"]

        all_media = (await client.request(entity_list("media", project_id))).get("entities", [])

        # Build shot lookup if needed
        shot_id_filter = None
        if params.shot_name:
            all_shots = (await client.request(entity_list("shot", project_id))).get("entities", [])
            shot = next((s for s in all_shots if s.get("name") == params.shot_name), None)
            if not shot:
                return _err(f"Shot '{params.shot_name}' not found")
            shot_id_filter = shot["id"]

        records = []
        for m in all_media:
            m_attrs = m.get("attributes", {})
            status = m.get("status") or "pending"

            # Filters
            if params.status and status != params.status:
                continue
            if params.kind and m_attrs.get("kind", "") != params.kind:
                continue
            if shot_id_filter:
                # Media links to shot via version — skip if no version_id match
                # (approximation: filter by name prefix if shot_name provided)
                name = m.get("name", "")
                if not name.startswith(params.shot_name):
                    continue

            locs = m.get("locations", [])
            path = next((l["path"] for l in locs if l.get("storage_type") == "local"), "")
            if not path and locs:
                path = locs[0].get("path", "")

            records.append({
                "media_id":     m["id"],
                "name":         m.get("name", ""),
                "status":       status,
                "kind":         m_attrs.get("kind", ""),
                "colour_space": m_attrs.get("colour_space", ""),
                "resolution":   m.get("resolution", ""),
                "layer_index":  m_attrs.get("layer_index"),
                "sequence_name": m_attrs.get("sequence_name", ""),
                "path":         path,
            })

        records.sort(key=lambda r: (r["sequence_name"], r["name"]))

        status_summary = {}
        for r in records:
            status_summary[r["status"]] = status_summary.get(r["status"], 0) + 1

        return _ok({
            "project_id":     project_id,
            "count":          len(records),
            "status_summary": status_summary,
            "filters": {
                "status":    params.status,
                "shot_name": params.shot_name,
                "kind":      params.kind,
            },
            "media": records,
        })
    except Exception as e:
        return _err(str(e))

class ListPublishedPlatesInput(BaseModel):
    project_id:    Optional[str] = Field(default=None, description="Project UUID — defaults to first project")
    shot_name:     Optional[str] = Field(default=None, description="Filter to a specific shot name e.g. 'ABC_010'")
    sequence_name: Optional[str] = Field(default=None, description="Filter to a specific sequence e.g. 'test'")
    colour_space:  Optional[str] = Field(default=None, description="Filter by colour space e.g. 'ACEScct'")


async def list_published_plates(params: ListPublishedPlatesInput) -> str:
    """Forge: list video plates in the forge-bridge publish registry.

    Returns one record per published plate (version entity) with:
    - shot name, asset name, track (L01/L02/…), colour space
    - resolution, fps, frame range
    - full file path on disk (from the location record)
    - version name and number

    Optional filters: shot_name, sequence_name, colour_space.

    Use this tool ONLY when:
    - the user wants the *delivered/published* plates (final media)
    - the user is filtering plates by shot / sequence / colour space

    Do NOT use this tool for:
    - all media in the registry (published or not) → use forge_list_media
    - all plate versions for one specific shot → use forge_get_shot_versions
    - the publish lineage of a shot → use forge_get_shot_lineage
    - searching Flame for loaded clips → use flame_find_media
    - listing libraries / shots / projects → use the matching list_* tool

    This tool reads the publish registry; it does NOT read Flame state.
    """
    try:
        from forge_bridge.server.protocol import project_list, entity_list
        client = _client()

        # Resolve project
        project_id = params.project_id
        if not project_id:
            projects = await client.request(project_list())
            proj_list = projects.get("projects", [])
            if not proj_list:
                return _err("No projects in forge-bridge")
            project_id = proj_list[0]["id"]

        versions = (await client.request(entity_list("version", project_id))).get("entities", [])

        plates = []
        for v in versions:
            attrs = v.get("attributes", {})

            # Apply filters
            if params.shot_name and attrs.get("shot_id"):
                # need shot name — we'll filter after building the shot map
                pass
            if params.colour_space and attrs.get("colour_space", "") != params.colour_space:
                continue
            if params.sequence_name and attrs.get("sequence_name", "") != params.sequence_name:
                continue

            # Only include versions that look like plate registrations
            # (have asset_name and colour_space from the hook)
            if not attrs.get("asset_name") and not attrs.get("colour_space"):
                continue

            path = ""
            locs = v.get("locations", [])
            if locs:
                path = locs[0].get("path", "")

            plates.append({
                "version_id":     v["id"],
                "version_name":   v.get("name", ""),
                "shot_id":        attrs.get("shot_id", ""),
                "asset_name":     attrs.get("asset_name", ""),
                "track":          attrs.get("track", ""),
                "colour_space":   attrs.get("colour_space", ""),
                "width":          attrs.get("width", 0),
                "height":         attrs.get("height", 0),
                "fps":            attrs.get("fps", ""),
                "depth":          attrs.get("depth", ""),
                "start_frame":    attrs.get("start_frame", 0),
                "source_in":      attrs.get("source_in", 0),
                "source_out":     attrs.get("source_out", 0),
                "tape_name":      attrs.get("tape_name", ""),
                "sequence_name":  attrs.get("sequence_name", ""),
                "version_number": attrs.get("version_number", 0),
                "path":           path,
            })

        # Apply shot_name filter — requires shot lookup
        if params.shot_name:
            shots = (await client.request(entity_list("shot", project_id))).get("entities", [])
            shot_ids = {s["id"] for s in shots if s.get("name") == params.shot_name}
            plates = [p for p in plates if p["shot_id"] in shot_ids]

        # Sort: sequence → asset_name → track
        plates.sort(key=lambda p: (p["sequence_name"], p["asset_name"], p["track"]))

        return _ok({
            "project_id": project_id,
            "count":      len(plates),
            "filters":    {
                "shot_name":     params.shot_name,
                "sequence_name": params.sequence_name,
                "colour_space":  params.colour_space,
            },
            "plates": plates,
        })
    except Exception as e:
        return _err(str(e))


class GetShotVersionsInput(BaseModel):
    shot_name:  str           = Field(..., description="Shot name e.g. 'ABC_010'")
    project_id: Optional[str] = Field(default=None, description="Project UUID — defaults to first project")


async def get_shot_versions(params: GetShotVersionsInput) -> str:
    """Get all published plate versions for a specific shot.

    Returns the full publish history for the shot — every registered
    plate across all tracks (L01, L02, …) and all publish rounds.
    Versions are sorted oldest → newest within each track.

    Useful for understanding what has been published, at what colour
    space, and where the files live on disk.
    """
    try:
        from forge_bridge.server.protocol import project_list, entity_list
        client = _client()

        # Resolve project
        project_id = params.project_id
        if not project_id:
            projects = await client.request(project_list())
            proj_list = projects.get("projects", [])
            if not proj_list:
                return _err("No projects in forge-bridge")
            project_id = proj_list[0]["id"]

        # Find shot
        shots = (await client.request(entity_list("shot", project_id))).get("entities", [])
        shot = next((s for s in shots if s.get("name") == params.shot_name), None)
        if not shot:
            return _err(f"Shot '{params.shot_name}' not found in project")
        shot_id = shot["id"]

        # Get all versions for this shot
        all_versions = (await client.request(entity_list("version", project_id))).get("entities", [])
        shot_versions = [
            v for v in all_versions
            if v.get("attributes", {}).get("shot_id") == shot_id
            and (v.get("attributes", {}).get("asset_name") or v.get("attributes", {}).get("colour_space"))
        ]

        # Build output records
        records = []
        for v in shot_versions:
            attrs = v.get("attributes", {})
            locs = v.get("locations", [])
            path = locs[0].get("path", "") if locs else ""
            records.append({
                "version_id":     v["id"],
                "version_name":   v.get("name", ""),
                "asset_name":     attrs.get("asset_name", ""),
                "track":          attrs.get("track", ""),
                "colour_space":   attrs.get("colour_space", ""),
                "width":          attrs.get("width", 0),
                "height":         attrs.get("height", 0),
                "fps":            attrs.get("fps", ""),
                "start_frame":    attrs.get("start_frame", 0),
                "source_in":      attrs.get("source_in", 0),
                "source_out":     attrs.get("source_out", 0),
                "tape_name":      attrs.get("tape_name", ""),
                "version_number": attrs.get("version_number", 0),
                "path":           path,
            })

        # Sort by track then version number
        records.sort(key=lambda r: (r["track"], r["version_number"]))

        return _ok({
            "shot_name":  params.shot_name,
            "shot_id":    shot_id,
            "project_id": project_id,
            "count":      len(records),
            "versions":   records,
        })
    except Exception as e:
        return _err(str(e))
