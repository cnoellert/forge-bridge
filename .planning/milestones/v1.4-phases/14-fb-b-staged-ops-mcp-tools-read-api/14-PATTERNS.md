# Phase 14 (FB-B): Staged Ops MCP Tools + Read API — Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 13 (7 created, 6 modified)
**Analogs found:** 13 / 13 (12 exact / role-match, 1 cross-role pattern reuse)

This phase is a "wire it up using v1.3 primitives" phase — every new file has a load-bearing
analog already shipped in Phase 9 (Read API foundation) or Phase 13 (FB-A staged-op repo).
Per RESEARCH.md Finding #6 (Solution C), all 4 `forge_*_staged` MCP tools register from
`register_console_resources()` (NOT `register_builtins()`) so closures capture
`console_read_api` and `session_factory`.

---

## File Classification

### Created Files

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `tests/console/__init__.py` | test marker | n/a | (empty package marker) | exact (any `__init__.py`) |
| `tests/mcp/__init__.py` | test marker | n/a | (empty package marker) | exact (any `__init__.py`) |
| `tests/console/test_staged_handlers_list.py` | test (HTTP unit) | request-response | `tests/test_console_routes.py` | exact (TestClient pattern) |
| `tests/console/test_staged_handlers_writes.py` | test (HTTP unit) | request-response | `tests/test_console_routes.py` + `tests/test_staged_operations.py` (session_factory) | exact-composed |
| `tests/console/test_staged_zero_divergence.py` | test (byte-identity) | dual-surface | `tests/test_console_mcp_resources.py` (`_ResourceSpy` lines 50-72, byte-identity test lines 150-163) | exact |
| `tests/mcp/test_staged_tools.py` | test (MCP integration) | tool-invocation | `tests/test_console_mcp_resources.py` (no `tests/mcp/` exists yet — Finding #7 confirms gap) | role-match (closest hermetic pattern) |
| `forge_bridge/console/staged_handlers.py` *(if planning splits)* OR appended to `handlers.py` | controller (HTTP handler module) | request-response (read + write) | `forge_bridge/console/handlers.py` (entire file: envelope helpers + handler shape) | exact |

### Modified Files

| Modified File | Role | Data Flow | Closest Pattern Within File | Edit Type |
|---------------|------|-----------|------------------------------|-----------|
| `forge_bridge/store/staged_operations.py` | repository | CRUD (add `list()`) + WR-01 fix | `EntityRepo.list_by_type` (`repo.py:295-305`) for `list()`; existing `_transition` lines 286-296 for the one-line WR-01 fix | additive + 1-line surgical fix |
| `forge_bridge/console/read_api.py` | service facade | request-response | existing `get_executions` method (lines 121-144) for the `get_staged_ops` shape | additive (constructor + 2 methods) |
| `forge_bridge/console/app.py` | route registration / app factory | request-response | existing route block (lines 63-87) and `app.state` attachment (line 98) | additive (3 routes + 1 state attr) |
| `forge_bridge/console/resources.py::register_console_resources` | MCP resource/tool registration | event-driven (resource read) + request-response (tool calls) | existing `forge_manifest_read` + `forge://manifest/synthesis` shim closure (lines 51-91) | additive (1 resource + 5 tools + 1 sig param) |
| `forge_bridge/mcp/server.py::_lifespan` | lifecycle / DI | startup-injection | existing Step 4 `ConsoleReadAPI(...)` construction (lines 125-131) and Step 5 `register_console_resources(...)` call (line 138) | additive (1 import + 1 factory build + 2 kwargs) |
| `tests/test_console_mcp_resources.py` | test (byte-identity) | dual-surface | existing `test_manifest_resource_body_matches_http_route_bytes` (lines 150-163) | additive (1 new test function) |

---

## Pattern Assignments

### `forge_bridge/store/staged_operations.py` — Add `StagedOpRepo.list()` + WR-01 fix

**Analog (for `list()`):** `forge_bridge/store/repo.py::EntityRepo.list_by_type` (lines 295-305)

**Existing pattern to extend** (`repo.py:295-305`):
```python
async def list_by_type(
    self,
    entity_type: str,
    project_id: uuid.UUID | None = None,
) -> list[BridgeEntity]:
    stmt = select(DBEntity).where(DBEntity.entity_type == entity_type)
    if project_id:
        stmt = stmt.where(DBEntity.project_id == project_id)
    stmt = stmt.order_by(DBEntity.name)
    result = await self.session.execute(stmt)
    return [self._to_core(e) for e in result.scalars().all()]
```

**Adapt for D-02** (`(records, total)` shape per Phase 9 `ExecutionLog.snapshot` contract;
order by `created_at DESC` per D-01; status + project_id filters; pagination):
```python
async def list(
    self,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    project_id: uuid.UUID | None = None,
) -> tuple[list[StagedOperation], int]:
    """Return (records, total_before_pagination) for FB-B's staged_list handler.

    D-01 default ordering: created_at DESC. Pagination clamp lives in the handler.
    """
    from sqlalchemy import select, func
    from forge_bridge.store.models import DBEntity

    base_filter = (DBEntity.entity_type == "staged_operation",)
    if status is not None:
        base_filter += (DBEntity.status == status,)
    if project_id is not None:
        base_filter += (DBEntity.project_id == project_id,)

    count_stmt = select(func.count()).select_from(DBEntity).where(*base_filter)
    total = (await self.session.execute(count_stmt)).scalar_one()

    stmt = (
        select(DBEntity)
        .where(*base_filter)
        .order_by(DBEntity.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await self.session.execute(stmt)
    records = [self._to_staged_operation(db) for db in result.scalars().all()]
    return records, total
```

**WR-01 surgical fix** (D-17a — same module, line 289):

Existing buggy code (`staged_operations.py:286-291`):
```python
db_entity = await self.session.get(DBEntity, op_id)
if db_entity is None or db_entity.entity_type != "staged_operation":
    # UUID doesn't resolve to a staged_op — treat as illegal transition.
    raise StagedOpLifecycleError(
        from_status="(missing)", to_status=new_status, op_id=op_id,
    )
```

Replace with (the `from_status is None` discriminator is now load-bearing for FB-B 404
distinction; per Finding #4, `from_status==None` only ever reaches FB-B as not-found
because `propose()` never goes through `_transition()`):
```python
db_entity = await self.session.get(DBEntity, op_id)
if db_entity is None or db_entity.entity_type != "staged_operation":
    # UUID doesn't resolve to a staged_op — distinct from illegal-transition;
    # FB-B handlers map from_status=None to HTTP 404 staged_op_not_found.
    raise StagedOpLifecycleError(
        from_status=None, to_status=new_status, op_id=op_id,
    )
```

(Optional: add `not_found: bool = False` field on `StagedOpLifecycleError` for explicit
discrimination — Finding #4 Option A. Planner's call.)

---

### `forge_bridge/console/read_api.py` — Extend `ConsoleReadAPI` with `session_factory` + 2 methods

**Analog (constructor extension):** existing `__init__` (lines 87-107) — mirror the
optional-with-env-fallback plumbing pattern used by `flame_bridge_url`/`ws_bridge_url`.

**Analog (read methods):** existing `get_executions` (lines 121-144) — same
`(records, total)` tuple return shape, same `async`+kwargs forwarding.

**Existing constructor** (`read_api.py:87-107`):
```python
def __init__(
    self,
    execution_log: "ExecutionLog",
    manifest_service: "ManifestService",
    llm_router: Optional["LLMRouter"] = None,
    flame_bridge_url: Optional[str] = None,
    ws_bridge_url: Optional[str] = None,
    console_port: int = 9996,
) -> None:
    self._execution_log = execution_log
    self._manifest_service = manifest_service
    self._llm_router = llm_router
    ...
    self._console_port = console_port
```

**Adapt — add `session_factory` parameter (default `None` to keep existing tests passing):**
```python
def __init__(
    self,
    execution_log: "ExecutionLog",
    manifest_service: "ManifestService",
    llm_router: Optional["LLMRouter"] = None,
    flame_bridge_url: Optional[str] = None,
    ws_bridge_url: Optional[str] = None,
    console_port: int = 9996,
    session_factory: Optional["async_sessionmaker"] = None,   # NEW (D-03)
) -> None:
    self._execution_log = execution_log
    self._manifest_service = manifest_service
    self._llm_router = llm_router
    ...
    self._console_port = console_port
    self._session_factory = session_factory   # NEW (D-03)
```

**Existing read method pattern** (`read_api.py:121-144`):
```python
async def get_executions(
    self,
    limit: int = 50,
    offset: int = 0,
    since: Optional[datetime] = None,
    promoted_only: bool = False,
    code_hash: Optional[str] = None,
) -> tuple[list["ExecutionRecord"], int]:
    return self._execution_log.snapshot(
        limit=limit, offset=offset, since=since,
        promoted_only=promoted_only, code_hash=code_hash,
    )
```

**Adapt — `get_staged_ops` and `get_staged_op` (D-03; opens session per call):**
```python
async def get_staged_ops(
    self,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    project_id: uuid.UUID | None = None,
) -> tuple[list["StagedOperation"], int]:
    """Return (records, total) — opens session per call, instantiates repo."""
    from forge_bridge.store.staged_operations import StagedOpRepo
    async with self._session_factory() as session:
        repo = StagedOpRepo(session)
        return await repo.list(
            status=status, limit=limit, offset=offset, project_id=project_id,
        )

async def get_staged_op(self, op_id: uuid.UUID) -> "StagedOperation | None":
    """Return single op by UUID, or None if absent / wrong entity_type."""
    from forge_bridge.store.staged_operations import StagedOpRepo
    async with self._session_factory() as session:
        repo = StagedOpRepo(session)
        return await repo.get(op_id)
```

---

### `forge_bridge/console/handlers.py` (or new `staged_handlers.py`) — 3 handlers + 1 helper

**Analog (read handler):** existing `execs_handler` (lines 126-153)
**Analog (single-record not-found):** existing `tool_detail_handler` (lines 114-123)
**Analog (envelope/error helpers — REUSE VERBATIM):** lines 43-60

**Existing read handler pattern to mirror** (`handlers.py:126-153`):
```python
async def execs_handler(request: Request) -> JSONResponse:
    try:
        if request.query_params.get("tool"):
            return _error("not_implemented", "tool filter reserved for v1.4", status=400)
        limit, offset = _parse_pagination(request)
        try:
            since, promoted_only, code_hash = _parse_filters(request)
        except ValueError as ve:
            return _error("bad_request", str(ve), status=400)
        records, total = await request.app.state.console_read_api.get_executions(
            limit=limit, offset=offset, since=since,
            promoted_only=promoted_only, code_hash=code_hash,
        )
        return _envelope(
            [asdict(r) for r in records],
            limit=limit, offset=offset, total=total,
        )
    except Exception as exc:
        logger.warning("execs_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read execs", status=500)
```

**Adapt for `staged_list_handler` (D-01, D-10):**
```python
_STAGED_STATUSES = frozenset({"proposed", "approved", "rejected", "executed", "failed"})

async def staged_list_handler(request: Request) -> JSONResponse:
    try:
        limit, offset = _parse_pagination(request)
        status = request.query_params.get("status")
        if status is not None and status not in _STAGED_STATUSES:
            return _error(
                "invalid_filter",
                f"unknown status {status!r}; expected one of {sorted(_STAGED_STATUSES)}",
                status=400,
            )
        project_id_raw = request.query_params.get("project_id")
        project_id: uuid.UUID | None = None
        if project_id_raw is not None:
            try:
                project_id = uuid.UUID(project_id_raw)
            except ValueError:
                return _error("bad_request", "invalid project_id", status=400)
        records, total = await request.app.state.console_read_api.get_staged_ops(
            status=status, limit=limit, offset=offset, project_id=project_id,
        )
        return _envelope(
            [r.to_dict() for r in records],
            limit=limit, offset=offset, total=total,
        )
    except Exception as exc:
        logger.warning("staged_list_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read staged operations", status=500)
```

**Write handler (no in-tree analog — Phase 9 ships zero POSTs).** Compose the existing
envelope/error patterns with the FB-A `StagedOpRepo` write contract from
`forge_bridge/store/staged_operations.py:182-211` (`approve` / `reject` shapes):

```python
async def staged_approve_handler(request: Request) -> JSONResponse:
    op_id_raw = request.path_params["id"]
    try:
        op_id = uuid.UUID(op_id_raw)
    except ValueError:
        return _error("bad_request", "invalid staged_operation id", status=400)

    try:
        actor = await _resolve_actor(request)
    except ValueError as ve:
        return _error("bad_actor", str(ve), status=400)

    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            repo = StagedOpRepo(session)
            try:
                op = await repo.approve(op_id, approver=actor)
            except StagedOpLifecycleError as exc:
                # D-10 mapping: from_status is None → 404; otherwise 409 + current_status.
                if exc.from_status is None:
                    return _error(
                        "staged_op_not_found",
                        f"no staged_operation with id {op_id}",
                        status=404,
                    )
                return JSONResponse(
                    {"error": {
                        "code": "illegal_transition",
                        "message": str(exc),
                        "current_status": exc.from_status,
                    }},
                    status_code=409,
                )
            await session.commit()
        return _envelope(op.to_dict())
    except Exception as exc:
        logger.warning("staged_approve_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to approve staged operation", status=500)
```

**Actor resolver helper (D-06; no in-tree analog — small new helper):**
```python
async def _resolve_actor(request: Request) -> str:
    """D-06 priority: X-Forge-Actor header → body 'actor' field → 'http:anonymous'.

    Empty string in EITHER explicit source raises ValueError (caller maps to 400 bad_actor).
    Missing both → 'http:anonymous' fallback.
    """
    header_val = request.headers.get("X-Forge-Actor")
    if header_val is not None:
        if not header_val.strip():
            raise ValueError("X-Forge-Actor header is empty")
        return header_val

    body: dict | None = None
    try:
        body = await request.json()
    except Exception:
        body = None
    if isinstance(body, dict) and "actor" in body:
        actor = body["actor"]
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("body 'actor' field is empty or non-string")
        return actor

    return "http:anonymous"
```

---

### `forge_bridge/console/app.py` — Register 3 routes, attach `session_factory`

**Analog:** existing route registration block (`app.py:63-87`) and `app.state` attachment
(`app.py:97-99`).

**Existing route block** (`app.py:63-69`):
```python
routes = [
    # Phase 9 — JSON API (UNCHANGED)
    Route("/api/v1/tools", tools_handler, methods=["GET"]),
    Route("/api/v1/tools/{name}", tool_detail_handler, methods=["GET"]),
    Route("/api/v1/execs", execs_handler, methods=["GET"]),
    Route("/api/v1/manifest", manifest_handler, methods=["GET"]),
    Route("/api/v1/health", health_handler, methods=["GET"]),
    ...
```

**Add (CONTEXT.md Integration Points):**
```python
    # Phase 14 (FB-B) — staged operations
    Route("/api/v1/staged", staged_list_handler, methods=["GET"]),
    Route("/api/v1/staged/{id}/approve", staged_approve_handler, methods=["POST"]),
    Route("/api/v1/staged/{id}/reject", staged_reject_handler, methods=["POST"]),
```

**Existing `app.state` attachment** (`app.py:97-99`):
```python
app = Starlette(routes=routes, middleware=middleware)
app.state.console_read_api = read_api
app.state.templates = templates
return app
```

**Extend signature + state** (Open Question #4 — Option C: attach to `app.state` directly,
keep `read_api` clean):
```python
def build_console_app(
    read_api: "ConsoleReadAPI",
    session_factory: "async_sessionmaker | None" = None,   # NEW (D-05)
) -> Starlette:
    ...
    app = Starlette(routes=routes, middleware=middleware)
    app.state.console_read_api = read_api
    app.state.session_factory = session_factory   # NEW (D-05) — write handlers read this
    app.state.templates = templates
    return app
```

**CORS extension** (`app.py:88-95`) — also extend `allow_methods` to include `POST`:
```python
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=_ALLOW_ORIGINS,
        allow_methods=["GET", "POST"],   # NEW: POST for /staged/{id}/approve|reject
        allow_headers=["*", "X-Forge-Actor"],   # NEW: D-06 header
        allow_credentials=False,
    ),
]
```

---

### `forge_bridge/console/resources.py::register_console_resources` — Add 1 resource + 5 tools + sig param

**Analog (resource closure):** existing `synthesis_manifest` resource (lines 51-54)
**Analog (tool shim closure):** existing `forge_manifest_read` (lines 80-91)
**Analog (resource not-found error pattern):** existing `tool_detail` (lines 61-71)

Per Finding #6 Solution C and CONTEXT.md D-17 revision: ALL FB-B MCP surface
(4 staged tools + 1 resource + 1 fallback shim) registers from this site so closures
capture `console_read_api` and `session_factory` natively.

**Existing signature** (`resources.py:29-33`):
```python
def register_console_resources(
    mcp: "FastMCP",
    manifest_service: "ManifestService",
    console_read_api: "ConsoleReadAPI",
) -> None:
```

**Extend with `session_factory` (D-05) — for write-tool closures:**
```python
def register_console_resources(
    mcp: "FastMCP",
    manifest_service: "ManifestService",
    console_read_api: "ConsoleReadAPI",
    session_factory: "async_sessionmaker | None" = None,   # NEW (D-05)
) -> None:
```

**Existing resource closure** (`resources.py:51-54`):
```python
@mcp.resource("forge://manifest/synthesis", mime_type="application/json")
async def synthesis_manifest() -> str:
    data = await console_read_api.get_manifest()
    return _envelope_json(data)
```

**Adapt for `forge://staged/pending` (D-12, D-13):**
```python
@mcp.resource("forge://staged/pending", mime_type="application/json")
async def staged_pending() -> str:
    records, total = await console_read_api.get_staged_ops(
        status="proposed", limit=500, offset=0, project_id=None,
    )
    return _envelope_json(
        [r.to_dict() for r in records],
        limit=500, offset=0, total=total,
    )
```

**Existing tool-fallback shim closure** (`resources.py:80-91`):
```python
@mcp.tool(
    name="forge_manifest_read",
    description=(
        "Read the current synthesis manifest. Alias for "
        "`resources/read forge://manifest/synthesis` for MCP clients "
        "that don't support resources (Cursor, Gemini CLI)."
    ),
    annotations={"readOnlyHint": True},
)
async def forge_manifest_read() -> str:
    data = await console_read_api.get_manifest()
    return _envelope_json(data)
```

**Adapt for `forge_staged_pending_read` (D-12, D-16):**
```python
@mcp.tool(
    name="forge_staged_pending_read",
    description=(
        "Read the snapshot of pending (proposed) staged operations. "
        "Alias for `resources/read forge://staged/pending` for MCP clients "
        "that don't support resources (Cursor, Gemini CLI)."
    ),
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def forge_staged_pending_read() -> str:
    records, total = await console_read_api.get_staged_ops(
        status="proposed", limit=500, offset=0, project_id=None,
    )
    return _envelope_json(
        [r.to_dict() for r in records],
        limit=500, offset=0, total=total,
    )
```

**Adapt for the 4 `forge_*_staged` tools (D-15, D-16) — same closure-capture pattern.**
Tool functions live in `forge_bridge/mcp/tools.py` (or a new `staged_tools.py`) and
accept `console_read_api` / `session_factory` via the closure when wired here:

```python
# Inside register_console_resources, after the staged_pending_read shim:

@mcp.tool(
    name="forge_list_staged",
    description=(
        "List staged operations with optional status / project_id filter and "
        "pagination. status: proposed|approved|rejected|executed|failed (default: all)."
    ),
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def forge_list_staged(params: ListStagedInput) -> str:
    return await _list_staged_impl(params, console_read_api)

@mcp.tool(
    name="forge_get_staged",
    description="Get a single staged operation by UUID.",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def forge_get_staged(params: GetStagedInput) -> str:
    return await _get_staged_impl(params, console_read_api)

@mcp.tool(
    name="forge_approve_staged",
    description="Approve a staged operation. Requires non-empty actor identity.",
    annotations={
        "readOnlyHint": False,
        "idempotentHint": False,
        "destructiveHint": False,
    },
)
async def forge_approve_staged(params: ApproveStagedInput) -> str:
    return await _approve_staged_impl(params, session_factory)

@mcp.tool(
    name="forge_reject_staged",
    description="Reject a staged operation. Requires non-empty actor identity.",
    annotations={
        "readOnlyHint": False,
        "idempotentHint": False,
        "destructiveHint": False,
    },
)
async def forge_reject_staged(params: RejectStagedInput) -> str:
    return await _reject_staged_impl(params, session_factory)
```

**Existing not-found error pattern in resource** (`resources.py:61-71`) — REUSE for
`forge_get_staged` missing-id case:
```python
@mcp.resource("forge://tools/{name}", mime_type="application/json")
async def tool_detail(name: str) -> str:
    tool = await console_read_api.get_tool(name)
    if tool is None:
        return json.dumps({
            "error": {
                "code": "tool_not_found",
                "message": f"no tool named {name!r}",
            }
        })
    return _envelope_json(tool.to_dict())
```

---

### `forge_bridge/mcp/tools.py` — Add 4 tool functions + Pydantic input models

**Analog (Pydantic input model):** existing `GetProjectInput` (`tools.py:87-88`),
`ListShotsInput` (lines 132-137).

**IMPORTANT byte-identity wrinkle (Finding #6):** the legacy `_ok()` / `_err()` helpers
at `tools.py:31-36` use `indent=2` and a non-D-01 error envelope shape. **The four new
staged tools MUST use `_envelope_json` from `forge_bridge.console.handlers` instead** —
this is required by D-19 zero-divergence (HTTP route output must equal MCP tool output).

**Existing input model pattern** (`tools.py:87-88`):
```python
class GetProjectInput(BaseModel):
    project_id: str = Field(..., description="Project UUID")
```

**Adapt for D-15 (4 input models):**
```python
from typing import Optional
from pydantic import BaseModel, Field

class ListStagedInput(BaseModel):
    status: Optional[str] = Field(default=None, description="proposed|approved|rejected|executed|failed")
    limit: int = Field(default=50, description="Max records (1-500, silently clamped)")
    offset: int = Field(default=0, description="Pagination offset")
    project_id: Optional[str] = Field(default=None, description="Project UUID filter")

class GetStagedInput(BaseModel):
    id: str = Field(..., description="Staged operation UUID")

class ApproveStagedInput(BaseModel):
    id: str = Field(..., description="Staged operation UUID")
    actor: str = Field(..., min_length=1, description="Caller identity (free string, non-empty per D-07)")

class RejectStagedInput(BaseModel):
    id: str = Field(..., description="Staged operation UUID")
    actor: str = Field(..., min_length=1, description="Caller identity (free string, non-empty per D-07)")
```

**Adapt for tool body (using `_envelope_json`, NOT `_ok`):**
```python
import uuid
import json
from forge_bridge.console.handlers import _envelope_json

_STAGED_STATUSES = frozenset({"proposed", "approved", "rejected", "executed", "failed"})

async def _list_staged_impl(params: ListStagedInput, console_read_api) -> str:
    if params.status is not None and params.status not in _STAGED_STATUSES:
        return json.dumps({
            "error": {
                "code": "invalid_filter",
                "message": f"unknown status {params.status!r}; expected one of {sorted(_STAGED_STATUSES)}",
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
```

**Write tool body — uses `session_factory` directly (D-04, mirrors HTTP write handler):**
```python
async def _approve_staged_impl(params: ApproveStagedInput, session_factory) -> str:
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
                    "error": {"code": "staged_op_not_found",
                              "message": f"no staged_operation with id {op_id}"}
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
```

---

### `forge_bridge/mcp/server.py::_lifespan` — Build session_factory + pass through

**Analog:** existing Step 4 + Step 5 lines 125-138.

**Existing code** (`mcp/server.py:125-138`):
```python
# Step 4 — ConsoleReadAPI (sole read layer)
console_port = int(os.environ.get("FORGE_CONSOLE_PORT", "9996"))
console_read_api = ConsoleReadAPI(
    execution_log=execution_log,
    manifest_service=manifest_service,
    console_port=console_port,
)

# Step 5 — Starlette app + MCP resources/tools registration
from forge_bridge.console.app import build_console_app
from forge_bridge.console.resources import register_console_resources

app = build_console_app(console_read_api)
register_console_resources(mcp_server, manifest_service, console_read_api)
```

**Adapt — add `session_factory` build before Step 4, pass to constructor + `register_console_resources` + `build_console_app`:**
```python
# Step 4 — ConsoleReadAPI (sole read layer)
console_port = int(os.environ.get("FORGE_CONSOLE_PORT", "9996"))
from forge_bridge.store.session import get_async_session_factory
session_factory = get_async_session_factory()   # NEW (D-05) — singleton, env-driven
console_read_api = ConsoleReadAPI(
    execution_log=execution_log,
    manifest_service=manifest_service,
    console_port=console_port,
    session_factory=session_factory,   # NEW (D-05)
)

# Step 5 — Starlette app + MCP resources/tools registration
from forge_bridge.console.app import build_console_app
from forge_bridge.console.resources import register_console_resources

app = build_console_app(console_read_api, session_factory=session_factory)   # NEW arg
register_console_resources(
    mcp_server, manifest_service, console_read_api,
    session_factory=session_factory,   # NEW (D-05)
)
```

**Note (Finding #2):** `get_async_session_factory()` is environment-driven (`FORGE_DB_URL`).
A missing DB at startup does NOT crash `_lifespan` — graceful degradation matches the
existing console-task pattern (`mcp/server.py:252-313`); staged handler calls then
surface `internal_error` 500 at request time. Do not add startup-time DB probing.

---

### `tests/test_console_mcp_resources.py` — Add D-20 byte-identity test

**Analog:** existing `test_manifest_resource_body_matches_http_route_bytes`
(`test_console_mcp_resources.py:150-163`) and `_ResourceSpy` (lines 50-72).

**Existing `_ResourceSpy` (REUSE VERBATIM):**
```python
class _ResourceSpy:
    """Mimics FastMCP's decorator API — captures decorated functions by uri/name."""
    def __init__(self):
        self.resources: dict[str, callable] = {}
        self.tools: dict[str, callable] = {}
        self.resource = MagicMock(side_effect=self._resource_decorator_factory)
        self.tool = MagicMock(side_effect=self._tool_decorator_factory)

    def _resource_decorator_factory(self, uri: str, **kwargs):
        def decorator(fn):
            self.resources[uri] = fn
            return fn
        return decorator

    def _tool_decorator_factory(self, **kwargs):
        name = kwargs.get("name", "")
        def decorator(fn):
            self.tools[name] = fn
            return fn
        return decorator
```

**Existing byte-identity test pattern** (`test_console_mcp_resources.py:150-163`):
```python
async def test_manifest_resource_body_matches_http_route_bytes(api):
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    resource_body_str = await spy.resources["forge://manifest/synthesis"]()

    client = TestClient(build_console_app(api))
    http_resp = client.get("/api/v1/manifest")
    http_body_str = http_resp.content.decode()

    assert json.loads(resource_body_str) == json.loads(http_body_str), (
        f"D-26: resource body must match HTTP route bytes.\n"
        f"Resource: {resource_body_str!r}\nHTTP: {http_body_str!r}"
    )
```

**Adapt for D-20 (`forge://staged/pending` ↔ `forge_list_staged(status='proposed', limit=500)`):**
```python
async def test_staged_pending_resource_matches_list_tool(api_with_staged_data):
    """STAGED-07 / D-20 — resource body equals forge_list_staged(status='proposed', limit=500)."""
    spy = _ResourceSpy()
    register_console_resources(
        spy, api_with_staged_data._manifest_service, api_with_staged_data,
        session_factory=api_with_staged_data._session_factory,
    )
    resource_body = await spy.resources["forge://staged/pending"]()
    tool_body = await spy.tools["forge_list_staged"](
        ListStagedInput(status="proposed", limit=500, offset=0)
    )
    assert json.loads(resource_body) == json.loads(tool_body), (
        f"D-20: forge://staged/pending must match forge_list_staged(status='proposed', limit=500).\n"
        f"Resource: {resource_body!r}\nTool: {tool_body!r}"
    )
```

The new fixture `api_with_staged_data` composes the existing `session_factory` fixture
with a populated `ConsoleReadAPI` (seeded with a few proposed/approved/rejected ops).

---

### `tests/console/test_staged_handlers_list.py` — D-19 list handler unit tests

**Analog:** existing `tests/test_console_routes.py` (entire file pattern: TestClient
fixture lines 22-36 + per-route assertions lines 41-120).

**Existing TestClient fixture pattern** (`test_console_routes.py:22-36`):
```python
@pytest.fixture
def client():
    ms = ManifestService()
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(ms.register(_record("a_tool")))
        loop.run_until_complete(ms.register(_record("b_tool")))
    finally:
        loop.close()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms)
    app = build_console_app(api)
    return TestClient(app)
```

**Adapt — compose `session_factory` (Phase 13 fixture) with a `ConsoleReadAPI` that
has it injected, plus pre-seeded staged ops:**
```python
@pytest_asyncio.fixture
async def staged_client(session_factory):
    """TestClient wired to a real session_factory + pre-seeded staged ops."""
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        session_factory=session_factory,
    )
    # Seed: one proposed, one approved
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.propose(operation="flame.publish", proposer="seed", parameters={})
        op2 = await repo.propose(operation="flame.export", proposer="seed", parameters={})
        await session.commit()
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(op2.id, approver="seed")
        await session.commit()
    app = build_console_app(api, session_factory=session_factory)
    return TestClient(app)
```

**Existing per-route assertion pattern** (`test_console_routes.py:41-49, 74-77`) — same shape:
```python
def test_tools_route_returns_envelope(client):
    r = client.get("/api/v1/tools")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["total"] == 2

def test_execs_route_limit_is_clamped_to_500(client):
    r = client.get("/api/v1/execs?limit=1000")
    assert r.status_code == 200
    assert r.json()["meta"]["limit"] == 500  # D-05
```

**Adapt for staged list cases (one per Failure Mode in RESEARCH.md):**
```python
async def test_staged_list_filter_by_status(staged_client):
    r = staged_client.get("/api/v1/staged?status=proposed")
    assert r.status_code == 200
    body = r.json()
    assert all(op["status"] == "proposed" for op in body["data"])

async def test_staged_list_clamps_limit_to_500(staged_client):
    r = staged_client.get("/api/v1/staged?limit=1000")
    assert r.status_code == 200
    assert r.json()["meta"]["limit"] == 500

async def test_staged_list_unknown_status_returns_400(staged_client):
    r = staged_client.get("/api/v1/staged?status=foo")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_filter"
```

---

### `tests/console/test_staged_handlers_writes.py` — D-19 write handler tests

Same pattern as `test_staged_handlers_list.py` — same `staged_client` fixture (or shared
via `tests/console/conftest.py`). Iterate the **Idempotency Contract Test Matrix** in
RESEARCH.md (Open Questions section preceding Sources). Cover D-06 actor priority,
D-09 strict 409 with `current_status`, D-10 error mapping.

```python
async def test_approve_with_header_actor(staged_client, proposed_op_id):
    r = staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "approved"
    assert r.json()["data"]["approver"] == "test-suite"

async def test_re_approve_returns_409_with_current_status(staged_client, approved_op_id):
    r = staged_client.post(
        f"/api/v1/staged/{approved_op_id}/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "illegal_transition"
    assert err["current_status"] == "approved"

async def test_approve_unknown_uuid_returns_404(staged_client):
    bogus = uuid.uuid4()
    r = staged_client.post(
        f"/api/v1/staged/{bogus}/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "staged_op_not_found"

async def test_approve_empty_header_actor_returns_400(staged_client, proposed_op_id):
    r = staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        headers={"X-Forge-Actor": ""},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_actor"
```

---

### `tests/console/test_staged_zero_divergence.py` — D-19 cross-surface byte-identity

**Analog:** `tests/test_console_mcp_resources.py::test_manifest_resource_body_matches_http_route_bytes`
(lines 150-163), reused with the staged tools registered via `_ResourceSpy` (Finding #6
Solution C — staged tools register from `register_console_resources`).

```python
async def test_list_staged_tool_matches_http_route_bytes(staged_api_with_data, session_factory):
    """D-19 — MCP tool output equals HTTP route output (byte-identity mod formatting)."""
    spy = _ResourceSpy()
    register_console_resources(
        spy, staged_api_with_data._manifest_service, staged_api_with_data,
        session_factory=session_factory,
    )
    tool_body = await spy.tools["forge_list_staged"](
        ListStagedInput(status="proposed", limit=50, offset=0)
    )
    client = TestClient(build_console_app(staged_api_with_data, session_factory=session_factory))
    http_body = client.get("/api/v1/staged?status=proposed&limit=50&offset=0").content.decode()
    assert json.loads(tool_body) == json.loads(http_body), (
        f"Tool: {tool_body!r}\nHTTP: {http_body!r}"
    )

async def test_approve_lifecycle_error_byte_identity(staged_api_with_data, session_factory, approved_op_id):
    """The illegal_transition error envelope (with current_status field) must be
    byte-identical between HTTP and MCP."""
    spy = _ResourceSpy()
    register_console_resources(
        spy, staged_api_with_data._manifest_service, staged_api_with_data,
        session_factory=session_factory,
    )
    tool_body = await spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(approved_op_id), actor="test")
    )
    client = TestClient(build_console_app(staged_api_with_data, session_factory=session_factory))
    http_body = client.post(
        f"/api/v1/staged/{approved_op_id}/approve",
        headers={"X-Forge-Actor": "test"},
    ).content.decode()
    tool_decoded = json.loads(tool_body)
    http_decoded = json.loads(http_body)
    assert tool_decoded == http_decoded
    # Verify the lifecycle field is present on BOTH surfaces
    assert tool_decoded["error"]["code"] == "illegal_transition"
    assert tool_decoded["error"]["current_status"] == "approved"
```

D-21 approval-does-NOT-execute regression test goes here too — see RESEARCH.md
"Approval-Does-NOT-Execute Regression Guard" section for the negative-assertion
monkeypatch pattern.

---

### `tests/mcp/test_staged_tools.py` — D-18 MCP tool integration

**Analog gap:** RESEARCH.md Finding #7 confirms `tests/mcp/` directory does not exist.
Closest pattern is `tests/test_console_mcp_resources.py` (`_ResourceSpy` + hermetic
in-process registration — Finding #7 Option B).

**Recommended pattern** (Finding #7 Option B; matches Solution C tool-registration site):
```python
"""STAGED-05 / D-18 — MCP tool integration via _ResourceSpy.

Per RESEARCH.md Finding #7 Option B, we use the established hermetic
test idiom rather than booting a real FastMCP subprocess. Solution C
registers the four staged tools from register_console_resources, so
the spy captures them alongside the resource and shim.
"""
from __future__ import annotations
import json
import pytest
import pytest_asyncio
from unittest.mock import MagicMock

from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.console.resources import register_console_resources
from forge_bridge.store.staged_operations import StagedOpRepo
from forge_bridge.mcp.tools import (
    ListStagedInput, GetStagedInput, ApproveStagedInput, RejectStagedInput,
)
from tests.test_console_mcp_resources import _ResourceSpy


@pytest_asyncio.fixture
async def spy_with_staged_data(session_factory):
    """A _ResourceSpy with the four staged tools + resource + shim registered,
    backed by a session_factory pre-seeded with one proposed op."""
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, session_factory=session_factory,
    )
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(
            operation="flame.publish", proposer="test", parameters={"x": 1},
        )
        await session.commit()
    spy = _ResourceSpy()
    register_console_resources(spy, ms, api, session_factory=session_factory)
    return spy, op.id


async def test_list_staged_returns_proposed_only(spy_with_staged_data):
    spy, _ = spy_with_staged_data
    body = await spy.tools["forge_list_staged"](
        ListStagedInput(status="proposed", limit=50, offset=0)
    )
    decoded = json.loads(body)
    assert all(r["status"] == "proposed" for r in decoded["data"])

async def test_approve_advances_status(spy_with_staged_data):
    spy, op_id = spy_with_staged_data
    body = await spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(op_id), actor="mcp:test")
    )
    decoded = json.loads(body)
    assert decoded["data"]["status"] == "approved"
    assert decoded["data"]["approver"] == "mcp:test"
```

---

## Shared Patterns

### Envelope helpers — REUSE VERBATIM (no copying, just import)

**Source:** `forge_bridge/console/handlers.py:43-60`
**Apply to:** all FB-B HTTP handlers AND all 4 staged MCP tool bodies AND the
resource/shim closures

```python
def _envelope(data, **meta) -> JSONResponse:
    """2xx envelope — applied on every success path (D-01)."""
    return JSONResponse({"data": data, "meta": meta})

def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    """4xx/5xx envelope — applied on every failure path. NEVER leak tracebacks."""
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)

def _envelope_json(data, **meta) -> str:
    """SAME serialization as _envelope — for MCP resource / tool shim use.
    Per D-26, resources/tools return byte-identical payloads to the HTTP route.
    """
    return json.dumps({"data": data, "meta": meta}, default=str)
```

**MCP tools use `_envelope_json` (NOT the legacy `_ok` from `mcp/tools.py:31`)** — this
is required by D-19 zero-divergence. The legacy `_ok` uses `indent=2` and a different
error shape; using it here would silently break byte-identity.

### Pagination clamp — REUSE VERBATIM

**Source:** `forge_bridge/console/handlers.py:65-77`
**Apply to:** `staged_list_handler` (HTTP) AND `_list_staged_impl` (MCP tool)

```python
def _parse_pagination(request: Request) -> tuple[int, int]:
    """Return (limit, offset). limit clamped to [1, 500] per D-05."""
    try:
        limit = int(request.query_params.get("limit", _DEFAULT_LIMIT))
    except ValueError:
        limit = _DEFAULT_LIMIT
    try:
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        offset = 0
    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)
    return limit, offset
```

The MCP tool body re-implements the clamp inline (`limit = max(1, min(params.limit, 500))`)
because it receives a Pydantic model, not a `Request` — but the values are identical.

### Error handling — outer try/except with `type(exc).__name__` log

**Source:** `forge_bridge/console/handlers.py:151-153, 161-162` (Phase 8 LRN — never
leak `str(exc)` because Python tracebacks may include credentials from connection strings)
**Apply to:** all 3 new HTTP handlers, all 4 new MCP tool bodies (with `try/except` at
the outer level, plus inner `try/except StagedOpLifecycleError` for the lifecycle case)

```python
try:
    ...
except Exception as exc:
    logger.warning("staged_X_handler failed: %s", type(exc).__name__, exc_info=True)
    return _error("internal_error", "failed to <verb> staged operation", status=500)
```

### Closure-capture for MCP tool/resource registration

**Source:** `forge_bridge/console/resources.py:51-91` — every `@mcp.resource` and
`@mcp.tool` body inside `register_console_resources()` references `console_read_api`
from the enclosing function's scope, not from a module global.
**Apply to:** all 4 staged tools + 1 resource + 1 shim — they reference
`console_read_api` and `session_factory` from the enclosing
`register_console_resources(..., session_factory=...)` call site.

This is the architectural reason D-17 was revised to Solution C (CONTEXT.md):
`register_builtins(mcp)` runs at import time before `_lifespan` constructs
`ConsoleReadAPI`, so closures cannot capture the singleton there.

### `StagedOpLifecycleError` → HTTP/MCP error mapping (D-10)

**Source:** `forge_bridge/store/staged_operations.py:52-83` (the exception with
`from_status`/`to_status`/`op_id` introspection fields)
**Apply to:** both write handlers AND both write MCP tools

```python
except StagedOpLifecycleError as exc:
    if exc.from_status is None:   # WR-01 fix per D-17a
        return _error("staged_op_not_found",
                      f"no staged_operation with id {op_id}", status=404)
    return JSONResponse(
        {"error": {
            "code": "illegal_transition",
            "message": str(exc),
            "current_status": exc.from_status,
        }},
        status_code=409,
    )
```

The MCP tool equivalent uses `json.dumps({"error": {...}})` directly (no `JSONResponse`)
but the dict shape is identical — the byte-identity test asserts this.

### Repo write contract — handler owns commit boundary

**Source:** `forge_bridge/store/staged_operations.py:106-108` ("None of the public
methods call `await self.session.commit()` — the caller owns transaction boundaries")
**Apply to:** both write handlers AND both write MCP tools

```python
async with session_factory() as session:
    repo = StagedOpRepo(session)
    op = await repo.approve(op_id, approver=actor)
    await session.commit()   # handler owns the txn boundary per FB-A repo contract
    return op.to_dict()
```

The exception-catch pattern wraps the `repo.approve()` call only — the `await
session.commit()` lives AFTER the `try/except StagedOpLifecycleError` block.

### `session_factory` test fixture — REUSE VERBATIM

**Source:** `tests/conftest.py:136-199` (Phase 13 deliverable — `_phase13_postgres_available()`
probe + per-test database provisioning)
**Apply to:** all FB-B store/handler/MCP integration tests

Test files import it directly: `def test_X(session_factory):` — pytest discovers the
fixture from `conftest.py` automatically. Tests skip cleanly without Postgres at
`localhost:5432`.

### `_ResourceSpy` test idiom — REUSE VERBATIM

**Source:** `tests/test_console_mcp_resources.py:50-72`
**Apply to:** D-18 MCP tool tests AND D-19 byte-identity tests AND D-20 resource snapshot test

Either import from `tests/test_console_mcp_resources` directly:
```python
from tests.test_console_mcp_resources import _ResourceSpy
```

…or copy the 22-line class into a `tests/console/conftest.py` if cross-package import
is preferred. Planning's call.

---

## No Analog Found

**None.** Every file in this phase has a load-bearing analog — this phase is
deliberately a "wire it up using v1.3 + Phase 13 primitives" exercise per
RESEARCH.md Phase Summary.

The only structural gap (per Finding #7) is the `tests/mcp/` directory itself
(absent from the tree). The PATTERNS map handles this by mirroring the established
`_ResourceSpy` + hermetic in-process pattern from `tests/test_console_mcp_resources.py`,
NOT by inventing a new MCP-subprocess test harness.

---

## Metadata

**Analog search scope:**
- `forge_bridge/console/` (handlers, resources, read_api, app, manifest_service)
- `forge_bridge/store/` (staged_operations, repo, session, models)
- `forge_bridge/mcp/` (server, registry, tools)
- `forge_bridge/core/` (staged.py for `to_dict()` shape)
- `tests/` (test_console_*, test_staged_operations.py, conftest.py, test_console_mcp_resources.py)

**Files scanned:** 13 source files + 4 test files + 1 conftest

**Key architectural decisions surfaced from pattern-mapping:**
1. **Solution C tool registration** (Finding #6) — all FB-B MCP tools register from
   `register_console_resources()` for closure capture of `console_read_api` and
   `session_factory`. This deviates from CONTEXT.md D-17's literal text but matches
   the closure-pattern constraint and is the reason D-17 was revised on 2026-04-26.
2. **`_envelope_json` not `_ok`** (Finding #6) — the legacy `mcp/tools.py:_ok()` uses
   `indent=2` and a different error envelope; new staged tools must use
   `console.handlers._envelope_json` for D-19 byte-identity.
3. **`from_status=None` discriminator** (Finding #4 / D-17a) — the WR-01 fix in
   `staged_operations.py:289` makes `from_status is None` the load-bearing 404-vs-409
   discriminator for FB-B handlers.
4. **Open Question #4 — Option C** — `session_factory` lives on `app.state.session_factory`
   (not on `ConsoleReadAPI`) for HTTP write handler access; keeps the read API honest
   to its name.

**Pattern extraction date:** 2026-04-26
**Source files referenced are valid as of:** commit `1bf5cc9` (current `main` branch)
