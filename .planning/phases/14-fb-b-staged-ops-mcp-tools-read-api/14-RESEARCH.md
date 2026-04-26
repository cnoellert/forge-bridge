# Phase 14 (FB-B): Staged Ops MCP Tools + Read API — Research

**Researched:** 2026-04-26
**Domain:** MCP tool registration, Starlette HTTP routes, single-facade Read API extension, async DB write paths
**Confidence:** HIGH (every load-bearing pattern verified against in-tree code)

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**List Query Surface (STAGED-06)**
- **D-01:** `forge_list_staged` and `GET /api/v1/staged` adopt Phase 9 pattern verbatim — `?status=<single value>` (proposed/approved/rejected/executed/failed; default None = all), `?limit=N&offset=M` (default 50, max 500, silently clamped per Phase 9 D-05), `?project_id=<uuid>`, default ordering `created_at DESC`. Single-status only; multi-status deferred.
- **D-02:** A new `StagedOpRepo.list(status, limit, offset, project_id) -> tuple[list[StagedOperation], int]` method ships in this phase (single SELECT against `entities` filtered by `entity_type='staged_operation'`).

**Read/Write Facade Shape (Phase 9 D-25 invariant)**
- **D-03:** `ConsoleReadAPI` is **extended** for reads — `session_factory` param added to `__init__`, plus `get_staged_ops(status, limit, offset, project_id) -> tuple[list[StagedOperation], int]` and `get_staged_op(op_id: uuid.UUID) -> StagedOperation | None`. Each method opens a session per call, instantiates `StagedOpRepo`, returns repo result. Preserves Phase 9 single-read-facade invariant.
- **D-04:** **Writes do NOT go through `ConsoleReadAPI`.** HTTP write handlers and MCP write tools call `StagedOpRepo` directly via the same `session_factory`:
  ```python
  async with session_factory() as session:
      repo = StagedOpRepo(session)
      op = await repo.approve(op_id, approver=actor)
      await session.commit()
      return op.to_dict()
  ```
  No `ConsoleWriteAPI` sibling class.
- **D-05:** `session_factory` injection plumbing — the canonical `_lifespan` startup path (Phase 9 P9-2) gains a `session_factory` parameter built from the existing `forge_bridge/store/session.py` module. Also passed into `register_console_resources()` for the resource closure.

**Actor Identity Sourcing (FB-A D-11/D-12 placeholder)**
- **D-06:** HTTP write handlers resolve actor in priority order: (1) `X-Forge-Actor` header, (2) JSON body field `{"actor": "..."}`, (3) fallback `"http:anonymous"`. Empty string in either source rejected with HTTP 400 `bad_actor`.
- **D-07:** MCP tools `forge_approve_staged` / `forge_reject_staged` require `actor` as a **non-defaulted Pydantic field** — no fallback. Empty string raises Pydantic validation error.
- **D-08:** Sample actor strings: `"web-ui:anonymous"`, `"projekt-forge:flame-a"`, `"mcp:claude-code"`, `"http:anonymous"`. v1.5 SEED-AUTH replaces the freeform space with structured form.

**Idempotency on Approve/Reject**
- **D-09:** **Strict 409 on illegal transitions — no idempotent 200.** Re-approving returns:
  ```json
  {"error": {"code": "illegal_transition", "message": "Illegal transition from 'approved' to 'approved' for staged_operation {id}", "current_status": "approved"}}
  ```
  HTTP 409 Conflict. MCP tool error body uses same envelope. The error envelope's `current_status` field is an FB-B addition on top of the standard `{code, message}` shape — same envelope shape, one extra field on the lifecycle case.

**HTTP / MCP Error Code Mapping**
- **D-10:** Locked error mapping table — `illegal_transition` (409, includes `current_status`), `staged_op_not_found` (404), `bad_request` (400, malformed UUID), `invalid_filter` (400, unknown `?status=` value), `bad_actor` (400, structurally impossible given D-06 fallback), `internal_error` (500, generic — log with `type(exc).__name__`, never `str(exc)` per Phase 8 LRN).
- **D-11:** MCP tool / resource error bodies use `_envelope_json` with same `{"error": {"code", "message", ...}}` shape — byte-identical to HTTP. Reuse `_error()` and `_envelope_json()` helpers. No new envelope module.

**Resource Template Scope (STAGED-07)**
- **D-12:** Ship **only** `forge://staged/pending` (proposed-only snapshot) plus `forge_staged_pending_read` tool fallback shim (P-03 prevention).
- **D-13:** Resource body equals `forge_list_staged(status='proposed', limit=500, offset=0)` output verbatim — guarantees byte-identity property between tool result and resource snapshot. Hardcoded `limit=500` (the max).
- **D-14:** **NOT shipping in v1.4:** `forge://staged/{status}` template, `forge://staged/{id}` template.

**Tool Naming & Input Shapes**
- **D-15:** Tool names + Pydantic input model names locked:
  ```python
  class ListStagedInput(BaseModel):
      status: Optional[str] = None
      limit: int = 50
      offset: int = 0
      project_id: Optional[str] = None
  class GetStagedInput(BaseModel):
      id: str
  class ApproveStagedInput(BaseModel):
      id: str
      actor: str  # required, non-empty (D-07)
  class RejectStagedInput(BaseModel):
      id: str
      actor: str  # required, non-empty (D-07)
  ```
  Tool names: `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`.
- **D-16:** MCP tool annotations:
  - `forge_list_staged`, `forge_get_staged`, `forge_staged_pending_read`: `{"readOnlyHint": True, "idempotentHint": True}`
  - `forge_approve_staged`, `forge_reject_staged`: `{"readOnlyHint": False, "idempotentHint": False, "destructiveHint": False}`
- **D-17:** Two registration sites — four `forge_*_staged` tools at `forge_bridge/mcp/registry.py::register_builtins()`; the `forge_staged_pending_read` shim and `forge://staged/pending` resource at `forge_bridge/console/resources.py::register_console_resources()` (so the closure captures `console_read_api` directly).

**Test Strategy**
- **D-18:** STAGED-05 — integration test under `tests/mcp/` boots FastMCP server, calls each of four tools via `mcp.client`, asserts payload matches `StagedOperation.to_dict()` + `status` field.
- **D-19:** STAGED-06 — under `tests/console/`: `test_staged_handlers_list.py`, `test_staged_handlers_writes.py`, `test_staged_zero_divergence.py`. Zero-divergence test calls MCP tool + HTTP route with same input, asserts `json.loads(tool_result) == http_response.json()`.
- **D-20:** STAGED-07 — `tests/test_console_mcp_resources.py` extension: read `forge://staged/pending`, assert payload equals `forge_list_staged(status='proposed', limit=500)` result.
- **D-21:** Approval-does-NOT-execute test — unit test asserting no execution code path is reached during approval; `staged.approved` `DBEvent` emitted with correct payload.

### Claude's Discretion

- Whether the staged-ops handlers live in a new `forge_bridge/console/staged_handlers.py` module or are appended to existing `handlers.py` (planning decides based on file size — `handlers.py` is at 171 lines; appending may be fine).
- Exact filename for the `StagedOpRepo.list()` extension — same module (`forge_bridge/store/staged_operations.py`) per FB-A's single-source-of-truth pattern, no new file.
- Whether the `tests/console/test_staged_*` tests share a fixture file (`conftest.py`) for the in-memory async session + StagedOpRepo setup, or each test bootstraps its own. FB-A's plan 13-04 already shipped a `session_factory` async-DB fixture — planning to reuse.
- Helper function placement for `_resolve_actor(request) -> str` (D-06) — likely a small helper in `forge_bridge/console/handlers.py` since it's HTTP-only and small.
- MCP tool function bodies' implementation pattern (e.g., whether they call into a shared `_handle_staged_action()` internal helper to dedupe HTTP and MCP write paths). Worth considering once the test suite shape is clearer.
- Whether the HTTP write routes use a request body parser (`await request.json()`) or query-string only for `actor` (D-06 covers both; planning picks the one that fits Phase 9 patterns best).

### Deferred Ideas (OUT OF SCOPE)

- `POST /api/v1/staged/{id}/execute` and `POST /api/v1/staged/{id}/fail` routes — v1.5 closure for the lifecycle. Tracking: `SEED-STAGED-CLOSURE-V1.5.md` (plant during planning).
- Approval / reject reason capture (`attributes.approve_reason`/`reject_reason`). Tracking: `SEED-STAGED-REASON-V1.5.md` (plant during planning).
- Multi-status filter (`?status=proposed,approved`) — single-status enough for v1.4.
- Resource templates `forge://staged/{status}` and `forge://staged/{id}` — MCP tools cover equivalent shapes.
- Bulk approve/reject endpoints — out of scope.
- Caller-identity bucketing for actors — SEED-AUTH-V1.5.
- `staged` CLI subcommands — deferred to v1.4.x.
- Pagination cursor / `?after=<id>` keyset pagination — v1.5+.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STAGED-05 | MCP tools `forge_list/get/approve/reject_staged` registered and callable from a real MCP client session; each returns JSON payload matching the entity shape from STAGED-01 + status field. | Findings #1 (FastMCP `register_tool` shape verified at `mcp/registry.py:54-126`), #6 (existing tool body pattern at `mcp/tools.py:31-36, 87-99`), #2 (lifespan injection point identified at `mcp/server.py:127-131`). |
| STAGED-06 | HTTP routes `GET /api/v1/staged?status=...`, `POST /api/v1/staged/{id}/approve`, `POST /api/v1/staged/{id}/reject` transition lifecycle and return updated record — same data shape as MCP tools (zero divergence). | Findings #3 (handler shape at `console/handlers.py:43-101`), #5 (envelope reuse + new error codes), #7 (test infrastructure verified — `session_factory` ready to consume). |
| STAGED-07 | `resources/read forge://staged/pending` returns snapshot identical to `forge_list_staged(status='proposed')`. Approval does NOT execute the operation. | Findings #1 (resource registration at `console/resources.py:51-114`), #8 (byte-identity test idiom at `tests/test_console_mcp_resources.py:148-186`). |

</phase_requirements>

## Phase Summary

Phase 14 (FB-B) is a "wire it up using v1.3's primitives" phase: it extends the existing Phase 9 single-facade Read API (`ConsoleReadAPI`) with two new read methods backing the staged-operations entity that FB-A shipped, plumbs three new Starlette routes through the existing envelope helpers, and registers four MCP tools + one resource + one tool-fallback shim through the existing two-site registration pattern (`mcp/registry.py::register_builtins` for read-API tools, `console/resources.py::register_console_resources` for resource shims). Writes deliberately bypass the read facade and call `StagedOpRepo` directly via the same `session_factory` — no new abstraction. The error envelope, pagination clamp, byte-identity contract, and test fixtures are all reused from Phase 9 / Phase 13.

**Primary recommendation:** Mirror existing patterns exactly. Every byte of new code has a load-bearing analog already shipped — the planner's job is to thread `session_factory` through `_lifespan` → `ConsoleReadAPI` + `register_console_resources`, then add four tool functions, three handlers, three routes, one resource, and one shim, plus the `StagedOpRepo.list()` method. No new modules required (everything fits inside existing files); planning may choose to split `console/handlers.py` if it grows past ~350 lines.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| List staged ops (paginated, filtered) | API / Backend (Starlette `GET /api/v1/staged`) | MCP server (`forge_list_staged` tool) | All reads go through `ConsoleReadAPI.get_staged_ops()` per Phase 9 D-25 single-facade invariant. |
| Get single staged op | API / Backend (Starlette `GET /api/v1/staged/{id}`? No — actually MCP `forge_get_staged` only, no HTTP route per CONTEXT.md scope) | MCP server (`forge_get_staged` tool) | Per phase boundary, only list/approve/reject HTTP routes ship; single-op fetch is MCP-only. |
| Approve staged op | API / Backend (Starlette `POST /api/v1/staged/{id}/approve` writes via `StagedOpRepo.approve` directly per D-04) | MCP server (`forge_approve_staged`) | Both surfaces call `StagedOpRepo` directly through `session_factory` — no facade. |
| Reject staged op | Same as approve | Same as approve | Same as approve. |
| Pending-queue snapshot | MCP resource (`forge://staged/pending`) | MCP tool fallback (`forge_staged_pending_read`) | Resource for clients with resources support; tool shim for Cursor / Gemini CLI per P-03 prevention pattern (MFST-02/03). |
| Database transaction boundary | API / Backend handler (owns `await session.commit()` per FB-A repo contract — `staged_operations.py:108`) | — | `StagedOpRepo` deliberately never commits; handler/test owns the commit boundary. |
| Actor identity resolution | API / Backend (`_resolve_actor(request)` helper, header → body → fallback per D-06) | MCP server (Pydantic field validation per D-07) | HTTP requires a fallback chain because callers may be unattributed; MCP requires explicit identity because the client always has one. |

## Findings

### Finding #1 — FastMCP tool registration via `register_tool()` is the canonical idiom

**Source:** `forge_bridge/mcp/registry.py:54-126, 172-326` [VERIFIED]

The `register_builtins()` function is the single registration site for all `forge_*` and `flame_*` builtin tools. Each tool follows this exact shape (verified at `registry.py:194-203`):

```python
register_tool(
    mcp, tools.list_projects,
    name="forge_list_projects",
    source="builtin",
    annotations={
        "title": "List all pipeline projects",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)
```

The `register_tool()` helper (`registry.py:54-126`) calls `mcp.add_tool(fn, name=name, annotations=effective_annotations, meta=merged_meta)` under the hood. Annotations are passed as a dict — the FastMCP API surface that ships with `mcp[cli]>=1.19,<2` (per `pyproject.toml:15`) accepts annotations directly on `add_tool()`. There is NO decorator-based annotation API for builtin registration; the call-site dict is canonical.

**For Phase 14 the planner adds four registration calls in `register_builtins()`** (alongside the existing `forge_list_*` family at `registry.py:228-303`). Each follows the exact pattern above. Tool functions live in `forge_bridge/mcp/tools.py` (Finding #6).

**Resource registration uses the decorator API** (`console/resources.py:51-76`):

```python
@mcp.resource("forge://manifest/synthesis", mime_type="application/json")
async def synthesis_manifest() -> str:
    data = await console_read_api.get_manifest()
    return _envelope_json(data)

@mcp.resource("forge://tools/{name}", mime_type="application/json")
async def tool_detail(name: str) -> str:
    tool = await console_read_api.get_tool(name)
    if tool is None:
        return json.dumps({
            "error": {"code": "tool_not_found", "message": f"no tool named {name!r}"}
        })
    return _envelope_json(tool.to_dict())
```

**The tool-fallback shim** is registered via `@mcp.tool(name=..., description=..., annotations={...})` from inside `register_console_resources()` so the closure captures `console_read_api` directly (`console/resources.py:80-114`):

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

**The exact analog the planner mirrors** for `forge://staged/pending` + `forge_staged_pending_read`:

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

The two functions are byte-identical — D-13's "resource body equals tool output" property is satisfied by them sharing the same call. Discretion: planning may extract a shared closure-local helper to dedupe; the cost of the duplication is ~6 lines.

**Confidence:** HIGH [VERIFIED via code read]

### Finding #2 — `_lifespan` is the single injection point for `session_factory`

**Source:** `forge_bridge/mcp/server.py:80-172` [VERIFIED]

The 6-step lifespan startup at `mcp/server.py:80-138` constructs `ConsoleReadAPI` at line 127:

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

**For Phase 14, exactly two edits are needed in `_lifespan`:**

1. Build the session factory before Step 4:
   ```python
   from forge_bridge.store.session import get_async_session_factory
   session_factory = get_async_session_factory()  # singleton, env-driven
   ```

2. Pass `session_factory` to `ConsoleReadAPI(...)` and to `register_console_resources(...)`:
   ```python
   console_read_api = ConsoleReadAPI(
       execution_log=execution_log,
       manifest_service=manifest_service,
       session_factory=session_factory,   # NEW (D-05)
       console_port=console_port,
   )
   ...
   register_console_resources(
       mcp_server, manifest_service, console_read_api,
       session_factory=session_factory,   # NEW (D-05) — for write-shim closures, even if v1.4 doesn't use it
   )
   ```

**Sessionmaker pattern verified at `store/session.py:99-103`:**

```python
_async_session_factory = async_sessionmaker(
    _async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

This is `sqlalchemy.ext.asyncio.async_sessionmaker` with `expire_on_commit=False` — it works as `async with session_factory() as session:` per D-04. The factory at `store/session.py:108-113` is the canonical accessor:

```python
def get_async_session_factory(db_url: str | None = None) -> async_sessionmaker:
    """Return the async session factory, initializing if needed."""
    get_async_engine(db_url)
    return _async_session_factory
```

**Note:** `get_async_session_factory()` is already imported by `tests/conftest.py` (Phase 13 conftest) — verified at `tests/conftest.py:100-102`. The factory is environment-driven (`FORGE_DB_URL`); no plumbing concerns. Planning's only decision is whether to handle the "no Postgres available" production-degradation case explicitly (current Phase 9 lifespan already proceeds with degraded surfaces — see `console_task` graceful-degradation at `mcp/server.py:252-313`). Recommendation: a missing DB at the staged-ops layer should result in `internal_error` 500 from the handlers when called, NOT a startup-time crash.

**Confidence:** HIGH [VERIFIED via code read]

### Finding #3 — Existing handler shape (Starlette + envelope helpers)

**Source:** `forge_bridge/console/handlers.py:42-171` [VERIFIED]

Every handler reads through `request.app.state.console_read_api` (attached in `build_console_app()` at `console/app.py:98`). The canonical handler shape (`handlers.py:126-153`):

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

**Patterns to copy verbatim into the staged handlers:**

- Outer `try/except Exception` → `_error("internal_error", ..., status=500)` with `type(exc).__name__` log (never `str(exc)` per Phase 8 LRN).
- `_parse_pagination(request)` reused as-is (clamps to 500 per D-05).
- A NEW thin filter parser for `?status=...` and `?project_id=...` — the existing `_parse_filters()` at `handlers.py:80-100` is execs-specific (parses `since`/`promoted_only`/`code_hash`) and does not apply. Planning ships a parallel `_parse_staged_filters(request) -> tuple[Optional[str], Optional[uuid.UUID]]` helper (or inlines into the handler — six lines).
- `_envelope([r.to_dict() for r in records], limit=..., offset=..., total=...)` — same shape as execs, ToolRecord, etc.

**For write handlers (POST), `await request.json()` is the standard Starlette pattern.** Phase 9 ships zero existing POST handlers — execs/tools/manifest/health are all GET. The planner introduces the body-parsing pattern. The reference shape (per D-06):

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
                # D-09 strict 409 with current_status field on top of standard envelope
                if exc.from_status is None:
                    # Per WR-01 in 13-REVIEW.md, the missing-entity case currently
                    # passes from_status="(missing)" not None. See Open Questions Q1.
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
            await session.commit()
        return _envelope(op.to_dict())
    except Exception as exc:
        logger.warning("staged_approve_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to approve staged operation", status=500)
```

**Actor resolution helper** (per D-06 priority order):

```python
async def _resolve_actor(request: Request) -> str:
    """Resolve actor identity per D-06: header → body → fallback.

    Empty string in header OR body raises ValueError (HTTP 400 bad_actor).
    Missing both → fallback to 'http:anonymous' per D-06.
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
        body = None  # No body or unparseable — fall through to default
    if isinstance(body, dict) and "actor" in body:
        actor = body["actor"]
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("body 'actor' field is empty or non-string")
        return actor

    return "http:anonymous"
```

**`_envelope_json` byte-identity check** — the existing helper at `handlers.py:53-60` is the single serializer:

```python
def _envelope_json(data, **meta) -> str:
    """SAME serialization as _envelope — for MCP resource / tool shim use."""
    return json.dumps({"data": data, "meta": meta}, default=str)
```

The MCP write tools call `_envelope_json(op.to_dict())` for success and `json.dumps({"error": {...}})` for the lifecycle error case (matches the existing `forge_tools_read` not-found pattern at `console/resources.py:106-113`). For the lifecycle error, the planner adds the `current_status` extra field:

```python
return json.dumps({
    "error": {
        "code": "illegal_transition",
        "message": str(exc),
        "current_status": exc.from_status,
    }
})
```

**Note on byte-identity preservation (D-19/D-26):** the `current_status` extra field is on the lifecycle error case ONLY. Other error cases (`staged_op_not_found`, `bad_request`, etc.) emit the standard `{code, message}` shape unchanged. Because the byte-identity test compares MCP tool output to HTTP route output, both surfaces must include the extra field on the lifecycle case AND omit it on all others. This is a thin invariant — plan tests must assert it explicitly.

**Confidence:** HIGH [VERIFIED via code read]

### Finding #4 — `StagedOpLifecycleError.from_status` is wrong sentinel for "not found"

**Source:** `forge_bridge/store/staged_operations.py:286-296`, `13-REVIEW.md` WR-01 [VERIFIED]

The FB-A repo's `_transition()` method (verified at `staged_operations.py:286-296`) uses **two different ways** to raise `StagedOpLifecycleError`:

```python
db_entity = await self.session.get(DBEntity, op_id)
if db_entity is None or db_entity.entity_type != "staged_operation":
    # UUID doesn't resolve to a staged_op — treat as illegal transition.
    raise StagedOpLifecycleError(
        from_status="(missing)", to_status=new_status, op_id=op_id,    # ← string sentinel
    )
old_status = db_entity.status
if (old_status, new_status) not in self._ALLOWED_TRANSITIONS:
    raise StagedOpLifecycleError(
        from_status=old_status, to_status=new_status, op_id=op_id,    # ← real status string
    )
```

The string sentinel `"(missing)"` violates the `from_status: str | None` type contract (`staged_operations.py:73`) — `None` is the documented sentinel meaning "no prior status" (i.e., the initial `propose()` transition).

**This breaks FB-B's HTTP error mapping (D-10):** the handler needs to distinguish "operation does not exist" (404 `staged_op_not_found`) from "illegal transition on existing entity" (409 `illegal_transition`). Checking `exc.from_status is None` silently mis-classifies the not-found case because the value is `"(missing)"`, not `None`.

**Two options for the planner:**

- **Option A (recommended):** Fix the FB-A bug as part of FB-B. One-line change at `staged_operations.py:289` from `from_status="(missing)"` to `from_status=None`. Add a `not_found: bool = False` parameter to `StagedOpLifecycleError` so the handler can distinguish "not found" from "idempotent re-transition where old==None"; the only place `old==None` happens is via `propose()`, which never goes through `_transition` (it goes through the direct insert path at `staged_operations.py:159-167`). So practically: if a `StagedOpLifecycleError` reaches FB-B with `from_status is None`, it MUST be a not-found case.
- **Option B:** Match the string sentinel as-is and check `exc.from_status == "(missing)"` in the handler. Brittle — locks FB-B to a private contract from FB-A.

**Recommendation: Option A.** Cost: one line in `staged_operations.py`, one test update if any STAGED-02 cross-product case asserts on `exc.from_status == "(missing)"` (planner verifies — initial scan of `tests/test_staged_operations.py:120-220` shows the cross-product asserts on the exception type only, not the field).

**Confidence:** HIGH [VERIFIED via code read + cross-referenced 13-REVIEW.md]

### Finding #5 — Error envelope reuse + `current_status` field is byte-safe

**Source:** `forge_bridge/console/handlers.py:42-60`, `forge_bridge/console/resources.py:64-71` [VERIFIED]

The error helper at `handlers.py:48-50`:

```python
def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    """4xx/5xx envelope — applied on every failure path. NEVER leak tracebacks."""
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)
```

Callers using `_error()` get the standard `{code, message}` shape only. For the `illegal_transition` D-09 case with `current_status`, the planner constructs the JSONResponse manually:

```python
return JSONResponse(
    {"error": {
        "code": "illegal_transition",
        "message": str(exc),
        "current_status": exc.from_status,
    }},
    status_code=409,
)
```

**The corresponding MCP tool body** uses `json.dumps(...)` directly (matches the `tool_not_found` pattern at `console/resources.py:64-71`):

```python
return json.dumps({
    "error": {
        "code": "illegal_transition",
        "message": str(exc),
        "current_status": exc.from_status,
    }
})
```

**Byte-identity verification:** because `json.dumps({"error": {...}})` and `JSONResponse({"error": {...}}).body.decode()` both use the standard library `json` module with the same dict, the resulting bytes are identical (modulo `JSONResponse` adding `Content-Type: application/json` to the HTTP response — but the body bytes match). The byte-identity test asserts `json.loads(tool_str) == http_resp.json()` (NOT raw byte equality), so the comparison is robust to trailing-newline / charset differences.

**The `current_status` field does NOT appear on `staged_op_not_found`, `bad_request`, `bad_actor`, `invalid_filter`, or `internal_error`.** It is solely a property of the lifecycle-conflict case. Tests must assert this asymmetry to prevent accidental field leakage.

**`StagedOpLifecycleError` exposes the current status:** `staged_operations.py:71-83` — the exception's `from_status` field IS the current status (the status that was in the DB when the illegal transition was attempted). No re-query needed.

**Confidence:** HIGH [VERIFIED via code read]

### Finding #6 — Existing tool body pattern uses `_ok()` JSON serializer

**Source:** `forge_bridge/mcp/tools.py:31-99, 132-185` [VERIFIED]

The canonical tool function shape (verified at `mcp/tools.py:87-99` for `forge_get_project`):

```python
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
```

The serializers at `mcp/tools.py:31-36`:

```python
def _ok(data) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(message: str, code: str = "ERROR") -> str:
    return json.dumps({"error": message, "code": code}, indent=2)
```

**This is the legacy tool-result pattern that pre-dates Phase 9.** It uses `indent=2` (pretty-printed) and a different error envelope shape (`{"error": message, "code": code}` instead of `{"error": {"code": ..., "message": ...}}`).

**For Phase 14, the planner has a choice:**

- **Mirror the legacy `_ok()`/`_err()` pattern** — matches existing `forge_*` tools, but the resulting bytes will NOT match the HTTP route bytes (different indentation, different error envelope shape). This **breaks D-19 zero-divergence**.
- **Use `_envelope_json()` from `console/handlers.py`** — matches HTTP byte-for-byte. Required by D-19.

**Recommendation:** Use `_envelope_json()` for the four staged tools, NOT `_ok()`. This is the ONLY consistent choice for D-19 byte-identity. The existing `forge_manifest_read` and `forge_tools_read` shims (`console/resources.py:80-114`) already use `_envelope_json()` for exactly this reason. The new four staged tools are NEW Phase 14 surface — they're not bound by the legacy tool-body convention; they're bound by the Phase 9 byte-identity invariant.

**Concrete tool body shape** (mirroring the existing `forge_tools_read` shape at `resources.py:102-114`):

```python
class ListStagedInput(BaseModel):
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0
    project_id: Optional[str] = None


async def list_staged(params: ListStagedInput, console_read_api: ConsoleReadAPI) -> str:
    """List staged operations with optional status / project_id filter and pagination."""
    # Validate status enum
    if params.status is not None and params.status not in _STAGED_STATUSES:
        return json.dumps({
            "error": {
                "code": "invalid_filter",
                "message": f"unknown status {params.status!r}; expected one of {sorted(_STAGED_STATUSES)}",
            }
        })
    # Clamp limit per D-01
    limit = max(1, min(params.limit, 500))
    offset = max(0, params.offset)
    # Validate project_id UUID if present
    project_id_uuid: Optional[uuid.UUID] = None
    if params.project_id is not None:
        try:
            project_id_uuid = uuid.UUID(params.project_id)
        except ValueError:
            return json.dumps({
                "error": {"code": "bad_request", "message": "invalid project_id"}
            })

    records, total = await console_read_api.get_staged_ops(
        status=params.status, limit=limit, offset=offset, project_id=project_id_uuid,
    )
    return _envelope_json(
        [r.to_dict() for r in records],
        limit=limit, offset=offset, total=total,
    )
```

**The key wrinkle:** these four tool functions need access to `console_read_api` (for reads) AND `session_factory` (for writes). The existing `forge_manifest_read` shim at `resources.py:89-91` shows the closure-capture pattern — registered from inside `register_console_resources(mcp, ms, console_read_api)` so the closure has both names in scope.

**For the four `forge_*_staged` tools registered in `register_builtins()`, the closure trick won't work** — `register_builtins(mcp)` doesn't have `console_read_api` or `session_factory` in scope (it runs at import time, before `_lifespan`). Two solutions:

- **Solution A:** Move all four tool registrations into `register_console_resources()` (alongside the resource and shim), where the closure captures `console_read_api` and `session_factory`. CONTEXT.md D-17 specifies "Tool registration site is `forge_bridge/mcp/registry.py::register_builtins()`" — this contradicts the closure constraint.
- **Solution B:** Have the tool functions look up `console_read_api` via a module-level reference set by `_lifespan`. Mirrors the existing `_canonical_execution_log` / `_canonical_manifest_service` pattern at `mcp/server.py:60-63`.
- **Solution C (recommended):** Register the four tools from `register_console_resources()` (where the closures work natively), and have `register_builtins()` either skip them or call into `register_console_resources()`. This trades CONTEXT.md D-17's literal text for a working closure pattern. Planning's call.

**Recommendation:** Solution C. The CONTEXT.md D-17 split between "read-API tools at registry.py" and "console-resource shims at resources.py" was based on the existing `forge_list_*` family being registered at registry.py — but those tools use a different (legacy) closure pattern via `get_client()` (verified at `mcp/tools.py:25-28`). The new tools depend on the v1.3 ConsoleReadAPI singleton whose lifecycle is owned by `_lifespan`; registering them where that singleton is available is the cleaner pattern. The planner should escalate this to discuss-phase if D-17 is treated as truly load-bearing rather than a default.

**Confidence:** HIGH [VERIFIED via code read; the closure-pattern conflict with D-17 is a real architectural finding the planner must resolve]

### Finding #7 — Test infrastructure: `session_factory` fixture is reusable

**Source:** `tests/conftest.py:86-200`, `tests/test_staged_operations.py:1-65` [VERIFIED]

The `session_factory` fixture shipped in Plan 13-04 (`tests/conftest.py:136-199`) provisions a fresh per-test Postgres database, runs `Base.metadata.create_all` (so all schema changes including ENTITY_TYPES extensions land automatically), and yields an `async_sessionmaker`:

```python
@_phase13_pytest_asyncio.fixture
async def session_factory():
    """Yield an async_sessionmaker bound to a freshly-created per-test database."""
    if not _phase13_postgres_available():
        import pytest
        pytest.skip("Postgres at localhost:5432 unreachable — skipping store-layer integration test")

    test_db_name = f"forge_bridge_test_{_phase13_uuid.uuid4().hex[:8]}"
    admin_engine = _phase13_create_async_engine(_phase13_admin_url(), isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(_phase13_text(f'CREATE DATABASE "{test_db_name}"'))
    await admin_engine.dispose()

    base_url = _phase13_os.environ.get(
        "FORGE_DB_URL", "postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge",
    )
    scheme_and_host, _slash, _ = base_url.rpartition("/")
    test_db_url = f"{scheme_and_host}/{test_db_name}"

    engine = _phase13_create_async_engine(test_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(_phase13_Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        yield factory
    finally:
        # ... drop database in teardown ...
```

**Reusable as-is for FB-B tests.** No new fixture work needed for the store-layer integration tests (`tests/console/test_staged_*` and `tests/mcp/test_staged_tools.py` per D-18/D-19). Pattern of consumption is already established at `tests/test_staged_operations.py:36-46`:

```python
async def test_staged_op_round_trip(session_factory):
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(
            operation="flame.publish_sequence",
            proposer="mcp:claude-code",
            parameters={"shot_id": "abc", "frames": 100},
        )
        await session.commit()
```

**For FB-B HTTP handler tests, the planner needs an additional fixture** that wires `session_factory` into a Starlette app for `TestClient` consumption. The existing pattern at `tests/test_console_routes.py:22-36` shows how to assemble a `TestClient` with a `ConsoleReadAPI`:

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

The new fixture composes both — `session_factory` (real DB) + `ConsoleReadAPI(execution_log=MagicMock, ms=ManifestService(), session_factory=session_factory)` + Starlette `TestClient(build_console_app(api))`. Note: planning needs to extend `build_console_app(read_api)` to accept the session_factory or attach it via `app.state.session_factory` (the write handlers need it; the read handlers go through `read_api`).

**For the MCP tool integration test (D-18) — there is currently NO existing test under `tests/mcp/`** (verified — `tests/mcp/` directory does not exist; no MCP-client subprocess tests anywhere in the suite). The closest pattern is `tests/test_mcp_registry.py` which uses `FastMCP("test")` directly and inspects `mcp._tool_manager._tools`:

```python
def _fresh_mcp() -> FastMCP:
    """Return a fresh FastMCP instance for each test (no shared state)."""
    return FastMCP("test")

def test_builtin_namespace():
    mcp = _fresh_mcp()
    fn = _make_fn("flame_foo")
    register_tool(mcp, fn, name="flame_foo", source="builtin")
    assert "flame_foo" in mcp._tool_manager._tools
```

**For D-18, planning has two test-shape options:**

- **Option A:** Boot `FastMCP` in-process, register the four tools, and call them directly via `mcp._tool_manager._tools["forge_list_staged"].fn(params)` — fast, hermetic, but doesn't exercise the MCP wire.
- **Option B:** Use the same in-process `FastMCP` instance and the `_ResourceSpy` pattern from `tests/test_console_mcp_resources.py:50-72` to capture decorated functions and call them — already a known-working pattern; mirrors the byte-identity test shape used for resources.

**Recommendation:** Option B. The existing `_ResourceSpy` (verified at `test_console_mcp_resources.py:50-72`) is the established hermetic-test idiom for the v1.3 read API surface; the new staged tests should follow it. A real-MCP-client subprocess test would add 30s+ per run with no additional defect catch (the FastMCP wire serialization is already tested by upstream `mcp` package).

**Confidence:** HIGH [VERIFIED via code read; the absence of `tests/mcp/` is itself a finding the planner must address — D-18's reference to "tests/mcp/" is aspirational]

### Finding #8 — D-19 byte-identity test idiom (established at Phase 9)

**Source:** `tests/test_console_mcp_resources.py:148-186` [VERIFIED]

The Phase 9 D-26 byte-identity test shape (verified at `test_console_mcp_resources.py:150-163`):

```python
async def test_manifest_resource_body_matches_http_route_bytes(api):
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    resource_body_str = await spy.resources["forge://manifest/synthesis"]()

    client = TestClient(build_console_app(api))
    http_resp = client.get("/api/v1/manifest")
    http_body_str = http_resp.content.decode()

    # Normalize whitespace — JSON byte-identity mod. formatting
    assert json.loads(resource_body_str) == json.loads(http_body_str), (
        f"D-26: resource body must match HTTP route bytes.\n"
        f"Resource: {resource_body_str!r}\nHTTP: {http_body_str!r}"
    )
```

**For D-19 zero-divergence, the staged equivalent looks like:**

```python
async def test_staged_list_tool_matches_http_route_bytes(api_with_staged_data):
    """STAGED-06 zero-divergence — MCP tool output equals HTTP route bytes."""
    # Surface 1 — MCP tool via spy
    spy = _ResourceSpy()
    register_console_resources(spy, api_with_staged_data._manifest_service, api_with_staged_data)
    # NOTE: the four staged tools register from register_console_resources per Finding #6 Solution C
    tool_body_str = await spy.tools["forge_list_staged"](
        ListStagedInput(status="proposed", limit=50, offset=0)
    )

    # Surface 2 — HTTP route via TestClient
    client = TestClient(build_console_app(api_with_staged_data))
    http_resp = client.get("/api/v1/staged?status=proposed&limit=50&offset=0")
    http_body_str = http_resp.content.decode()

    assert json.loads(tool_body_str) == json.loads(http_body_str)


async def test_staged_pending_resource_matches_list_proposed_tool(api_with_staged_data):
    """STAGED-07 D-13 — resource body equals forge_list_staged(status='proposed', limit=500)."""
    spy = _ResourceSpy()
    register_console_resources(spy, api_with_staged_data._manifest_service, api_with_staged_data)

    resource_body = await spy.resources["forge://staged/pending"]()
    tool_body = await spy.tools["forge_list_staged"](
        ListStagedInput(status="proposed", limit=500, offset=0)
    )

    assert json.loads(resource_body) == json.loads(tool_body)
```

**The fixture `api_with_staged_data`** is the new piece — it pre-populates the per-test DB with a few staged ops in known statuses so the queries return non-empty results. Compose `session_factory` + `StagedOpRepo` to seed.

**Confidence:** HIGH [VERIFIED via code read]

### Finding #9 — `StagedOpRepo.list()` extension shape

**Source:** `forge_bridge/store/staged_operations.py:175-180` (existing `get` method), `forge_bridge/store/repo.py:295-332` (existing `list_by_type`/`find_by_attribute`) [VERIFIED]

The new `StagedOpRepo.list(status, limit, offset, project_id)` per D-02. The existing `EntityRepo.list_by_type` at `repo.py:295-305` is the closest analog:

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

**For `StagedOpRepo.list()` per D-02 (returns `(records, total)` per Phase 9 ExecutionLog.snapshot shape):**

```python
async def list(
    self,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    project_id: uuid.UUID | None = None,
) -> tuple[list[StagedOperation], int]:
    """Return (records, total_before_pagination) for FB-B's staged_list handler.

    D-01 default ordering: created_at DESC (newest first, matches Phase 9 execs).
    D-05 pagination clamp is applied by the HANDLER, not here — repo trusts caller.
    """
    from sqlalchemy import select, func
    from forge_bridge.store.models import DBEntity

    base_filter = (DBEntity.entity_type == "staged_operation",)
    if status is not None:
        base_filter += (DBEntity.status == status,)
    if project_id is not None:
        base_filter += (DBEntity.project_id == project_id,)

    # Total count BEFORE pagination
    count_stmt = select(func.count()).select_from(DBEntity).where(*base_filter)
    total = (await self.session.execute(count_stmt)).scalar_one()

    # Paginated fetch
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

**Two SQL queries** (count + fetch). Acceptable for v1.4 staged-ops volume (expected dozens/day per CONTEXT.md). v1.5 cursor pagination is the deferred upgrade if volume grows.

**Index utilization:**

- `WHERE entity_type='staged_operation' AND status='proposed'` uses `ix_entities_status` + filter pushdown (verified at `models.py:300`).
- `WHERE entity_type='staged_operation' AND project_id=<uuid>` uses `ix_entities_project_type` (verified at `models.py:298`).
- `ORDER BY created_at DESC` does a heap sort on the filtered set (no `created_at` index) — acceptable for v1.4 volumes; planning may add `Index("ix_entities_type_status_created", "entity_type", "status", "created_at")` if perf testing surfaces a need.

**`ConsoleReadAPI.get_staged_ops()` shape (D-03):**

```python
async def get_staged_ops(
    self,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    project_id: uuid.UUID | None = None,
) -> tuple[list["StagedOperation"], int]:
    """Return (records, total) — opens session per call, instantiates repo, returns repo result."""
    async with self._session_factory() as session:
        repo = StagedOpRepo(session)
        return await repo.list(
            status=status, limit=limit, offset=offset, project_id=project_id,
        )

async def get_staged_op(self, op_id: uuid.UUID) -> "StagedOperation | None":
    """Return single op by UUID, or None if absent / wrong entity_type."""
    async with self._session_factory() as session:
        repo = StagedOpRepo(session)
        return await repo.get(op_id)
```

**Confidence:** HIGH [VERIFIED via code read]

## Implementation Approach

The planner can decompose Phase 14 into **5 plans across 3 waves**. Wave order is dictated by dependencies; tasks within a wave can run in parallel.

### Wave 1 — Foundation (parallel)

- **Plan 14-01 (Repo + ConsoleReadAPI extension)**
  1. Add `StagedOpRepo.list(status, limit, offset, project_id) -> tuple[list, int]` to `forge_bridge/store/staged_operations.py` per Finding #9.
  2. Extend `ConsoleReadAPI.__init__` with `session_factory: async_sessionmaker | None = None` parameter; default None so existing tests don't break.
  3. Add `ConsoleReadAPI.get_staged_ops(...)` and `ConsoleReadAPI.get_staged_op(op_id)` methods per Finding #9.
  4. Tests: extend `tests/test_staged_operations.py` with `test_staged_op_list_*` cases (status filter, project_id filter, pagination clamp, empty result, ordering by created_at).
- **Plan 14-02 (Lifespan injection + WR-01 fix)**
  1. Edit `forge_bridge/mcp/server.py::_lifespan` (Finding #2): build `session_factory = get_async_session_factory()` before Step 4; pass to `ConsoleReadAPI(...)` and to `register_console_resources(...)`.
  2. Fix WR-01 (Finding #4): one-line change in `forge_bridge/store/staged_operations.py:289` from `from_status="(missing)"` to `from_status=None`. Add a `not_found: bool` field to `StagedOpLifecycleError` if the planner needs explicit disambiguation (per Open Questions Q1 below).
  3. Update existing FB-A tests if any assert on `from_status == "(missing)"` (initial scan: none — `tests/test_staged_operations.py:120-220` cross-product asserts on type only).

### Wave 2 — HTTP + MCP surfaces (parallel; depend on Wave 1)

- **Plan 14-03 (HTTP handlers + routes)**
  1. Add three handlers to `forge_bridge/console/handlers.py`: `staged_list_handler`, `staged_approve_handler`, `staged_reject_handler` per Finding #3. Add `_resolve_actor(request)` helper per D-06.
  2. Add three routes to `forge_bridge/console/app.py::build_console_app` per CONTEXT.md Integration Points. Attach `session_factory` to `app.state.session_factory` (next to `app.state.console_read_api`).
  3. Add `_STAGED_STATUSES` frozenset constant for status validation.
  4. Tests: `tests/console/test_staged_handlers_list.py` and `tests/console/test_staged_handlers_writes.py` — cover all D-10 error mappings, D-09 idempotency, D-06 actor resolution priority order.
- **Plan 14-04 (MCP tools + resource + shim)**
  1. Add four tool functions to `forge_bridge/mcp/tools.py` (or a new `forge_bridge/mcp/staged_tools.py` if planning prefers): `list_staged`, `get_staged`, `approve_staged`, `reject_staged` per Finding #6. Add Pydantic input models per D-15.
  2. Register the four tools per Finding #6 Solution C — register from `forge_bridge/console/resources.py::register_console_resources()` so closures capture `console_read_api` and `session_factory`. Add `forge://staged/pending` resource and `forge_staged_pending_read` shim per Finding #1.
  3. Update `register_console_resources()` signature to accept `session_factory` per D-05.
  4. Tests: `tests/mcp/test_staged_tools.py` (new file; new directory) — use `_ResourceSpy` pattern from `tests/test_console_mcp_resources.py:50-72` to register and call.

### Wave 3 — Integration + byte-identity (depends on Wave 2)

- **Plan 14-05 (Zero-divergence + resource snapshot + execution-not-called regression)**
  1. `tests/console/test_staged_zero_divergence.py` — D-19 byte-identity test per Finding #8: list, get, approve, reject all assert MCP tool output == HTTP route output.
  2. Extend `tests/test_console_mcp_resources.py` with `forge://staged/pending` snapshot test per D-20.
  3. Add D-21 approval-does-NOT-execute regression guard. Implementation choices: assert no module under `forge_bridge.tools` is imported during approval (or mock `flame_*` execution paths and assert `MagicMock.assert_not_called()`).
  4. Plant SEED files: `.planning/seeds/SEED-STAGED-CLOSURE-V1.5.md` (execute/fail HTTP routes) and `.planning/seeds/SEED-STAGED-REASON-V1.5.md` (approve/reject reason capture).

## Validation Architecture

**Validation enabled:** `workflow.nyquist_validation: true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x with `pytest-asyncio` (`asyncio_mode = "auto"`, verified at `pyproject.toml:71`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) — pythonpath includes repo root |
| Quick run command | `pytest tests/test_staged_operations.py tests/console/test_staged_handlers_*.py tests/mcp/test_staged_tools.py -x` |
| Full suite command | `pytest tests/ -x` |
| Postgres requirement | Phase 13 fixture skips cleanly without Postgres (`_phase13_postgres_available()` probe at `conftest.py:120-133`); FB-B handler tests inherit this behavior |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAGED-05 | `forge_list_staged` returns paginated proposed-only set | integration | `pytest tests/mcp/test_staged_tools.py::test_list_staged_filter_status -x` | ❌ Wave 2 |
| STAGED-05 | `forge_get_staged` returns single op or None | integration | `pytest tests/mcp/test_staged_tools.py::test_get_staged_returns_to_dict -x` | ❌ Wave 2 |
| STAGED-05 | `forge_approve_staged` advances status + emits `staged.approved` | integration | `pytest tests/mcp/test_staged_tools.py::test_approve_staged_lifecycle -x` | ❌ Wave 2 |
| STAGED-05 | `forge_reject_staged` advances status + emits `staged.rejected` | integration | `pytest tests/mcp/test_staged_tools.py::test_reject_staged_lifecycle -x` | ❌ Wave 2 |
| STAGED-05 | Re-approve raises `illegal_transition` with `current_status` | integration | `pytest tests/mcp/test_staged_tools.py::test_re_approve_raises_409 -x` | ❌ Wave 2 |
| STAGED-06 | `GET /api/v1/staged?status=proposed&limit=10` returns clamped envelope | unit | `pytest tests/console/test_staged_handlers_list.py::test_list_status_filter -x` | ❌ Wave 2 |
| STAGED-06 | `GET /api/v1/staged?limit=1000` clamps to 500 (D-05) | unit | `pytest tests/console/test_staged_handlers_list.py::test_limit_clamp -x` | ❌ Wave 2 |
| STAGED-06 | `GET /api/v1/staged?project_id=<bad>` returns 400 | unit | `pytest tests/console/test_staged_handlers_list.py::test_bad_project_id -x` | ❌ Wave 2 |
| STAGED-06 | `GET /api/v1/staged?status=invalid` returns 400 `invalid_filter` | unit | `pytest tests/console/test_staged_handlers_list.py::test_unknown_status -x` | ❌ Wave 2 |
| STAGED-06 | `POST /api/v1/staged/{id}/approve` with header actor → 200 | integration | `pytest tests/console/test_staged_handlers_writes.py::test_approve_with_header_actor -x` | ❌ Wave 2 |
| STAGED-06 | `POST /api/v1/staged/{id}/approve` with body actor (no header) → 200 | integration | `pytest tests/console/test_staged_handlers_writes.py::test_approve_with_body_actor -x` | ❌ Wave 2 |
| STAGED-06 | `POST /api/v1/staged/{id}/approve` with no actor → fallback `http:anonymous` | integration | `pytest tests/console/test_staged_handlers_writes.py::test_approve_fallback_actor -x` | ❌ Wave 2 |
| STAGED-06 | Empty header actor → 400 `bad_actor` | integration | `pytest tests/console/test_staged_handlers_writes.py::test_empty_actor_400 -x` | ❌ Wave 2 |
| STAGED-06 | Re-approve → 409 with `current_status='approved'` | integration | `pytest tests/console/test_staged_handlers_writes.py::test_re_approve_409 -x` | ❌ Wave 2 |
| STAGED-06 | Approve unknown UUID → 404 `staged_op_not_found` | integration | `pytest tests/console/test_staged_handlers_writes.py::test_approve_unknown_404 -x` | ❌ Wave 2 |
| STAGED-06 | Approve malformed UUID → 400 `bad_request` | unit | `pytest tests/console/test_staged_handlers_writes.py::test_approve_bad_uuid -x` | ❌ Wave 2 |
| STAGED-06 | MCP tool output == HTTP route output (zero-divergence) | integration | `pytest tests/console/test_staged_zero_divergence.py -x` | ❌ Wave 3 |
| STAGED-07 | `forge://staged/pending` returns same payload as `forge_list_staged(status='proposed', limit=500)` | integration | `pytest tests/test_console_mcp_resources.py::test_staged_pending_resource_matches_list_tool -x` | ❌ Wave 3 |
| STAGED-07 | Approval emits `staged.approved` DBEvent without calling execution code | integration | `pytest tests/console/test_staged_zero_divergence.py::test_approval_does_not_execute -x` | ❌ Wave 3 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_staged_operations.py tests/console/test_staged_handlers_*.py tests/mcp/test_staged_tools.py -x` — runs ~70 cases in <30s on a Postgres-equipped machine; skips cleanly without.
- **Per wave merge:** `pytest tests/ -x` — full suite (~660 cases as of Phase 13 close).
- **Phase gate:** Full suite green BEFORE `/gsd-verify-work` runs. Then human-verification (per Phase 13 precedent): a developer with Postgres at `localhost:5432` runs the staged tests and confirms 0 skipped.

### Wave 0 Gaps

- [ ] `tests/console/` directory must exist (currently flat `tests/`). Create alongside Plan 14-03.
- [ ] `tests/mcp/` directory must exist (currently absent). Create alongside Plan 14-04.
- [ ] `tests/console/test_staged_handlers_list.py` — list/get handlers
- [ ] `tests/console/test_staged_handlers_writes.py` — approve/reject handlers
- [ ] `tests/console/test_staged_zero_divergence.py` — D-19 byte-identity
- [ ] `tests/mcp/test_staged_tools.py` — D-18 MCP tool integration
- [ ] `tests/test_console_mcp_resources.py` — D-20 extension (existing file)

### Failure Modes per Surface (Nyquist Dimension 8)

**`forge_list_staged` / `GET /api/v1/staged`:**
- Bad `status` value (e.g., `?status=foo`) → 400 `invalid_filter` with allowed-values list
- Bad `project_id` UUID → 400 `bad_request`
- Bad `limit`/`offset` non-integer → silently coerced to defaults (matches Phase 9 behavior at `handlers.py:65-77`)
- `limit=1000` → silently clamped to 500
- `offset=-1` → coerced to 0
- Empty result set → returns `{data: [], meta: {limit, offset, total: 0}}` (NOT a 404)
- Ordering: `created_at DESC` — verify with 3+ ops at known timestamps
- Filtering: status + project_id combined narrows correctly

**`forge_get_staged`:**
- Unknown UUID → returns `null` data (NOT 404 from MCP perspective; 404 from HTTP if planner ships single-op route — currently NOT in scope)
- Malformed UUID → Pydantic validation error (`bad_request`)

**`forge_approve_staged` / `POST /api/v1/staged/{id}/approve`:**
- Approve `proposed` → 200 with updated record
- Approve `approved` (idempotent) → 409 with `current_status: "approved"`
- Approve `rejected` → 409 with `current_status: "rejected"`
- Approve `executed` → 409 with `current_status: "executed"`
- Approve `failed` → 409 with `current_status: "failed"`
- Approve unknown UUID → 404 `staged_op_not_found` (depends on Finding #4 fix)
- Approve malformed UUID → 400 `bad_request`
- Approve with empty `X-Forge-Actor` header → 400 `bad_actor`
- Approve with empty body `actor` field (no header) → 400 `bad_actor`
- Approve with no header AND no body → fallback `http:anonymous` (200)
- Approve with body `actor: 123` (non-string) → 400 `bad_actor`
- Approve with malformed JSON body (no header) → fallback `http:anonymous` (200, body parse failure swallowed)

**`forge_reject_staged` / `POST /api/v1/staged/{id}/reject`:**
- Symmetric to approve — same error matrix.
- Approve-then-reject → 409 (op is now `approved`, can only go to `executed` / `failed`)
- Reject-then-approve → 409 (op is now `rejected`, terminal)

**`forge://staged/pending` resource:**
- Empty queue → returns `{data: [], meta: {limit: 500, offset: 0, total: 0}}`
- Queue with 1 item → returns single-element data array
- Queue with >500 items → returns first 500 (clamp); meta.total reports true count
- Mixed-status entities → only `proposed` returned

**`forge_staged_pending_read` shim:**
- Identical output to `forge://staged/pending` (asserted via byte-identity test in Plan 14-05)

**`StagedOpRepo.list()`:**
- Status filter SQL correctness (no JSONB scan — uses `entities.status` column index)
- Project_id filter SQL correctness (uses `ix_entities_project_type`)
- Combined filter (status + project_id) returns correct intersection
- Ordering stable across paginated chunks
- Total count correct with filters applied

### Byte-Identity Invariants (D-19, D-20)

| Surface Pair | Invariant | Guarded By |
|---|---|---|
| `forge_list_staged` MCP tool ↔ `GET /api/v1/staged` HTTP | `json.loads(tool) == http_resp.json()` for any (status, limit, offset, project_id) input | `tests/console/test_staged_zero_divergence.py::test_list_byte_identity` |
| `forge_get_staged` MCP tool ↔ (no HTTP route — assert tool returns `to_dict()` shape only) | Tool returns `_envelope_json(op.to_dict())` for present op, `_envelope_json(None)` for missing | `tests/mcp/test_staged_tools.py::test_get_returns_to_dict` |
| `forge_approve_staged` MCP tool ↔ `POST /api/v1/staged/{id}/approve` | Same on success (200 / data envelope), same on lifecycle error (`{error: {code, message, current_status}}`), same on not-found (`{error: {code, message}}`) | `tests/console/test_staged_zero_divergence.py::test_approve_byte_identity` + `::test_approve_lifecycle_error_byte_identity` |
| `forge_reject_staged` MCP tool ↔ `POST /api/v1/staged/{id}/reject` | Symmetric to approve | `tests/console/test_staged_zero_divergence.py::test_reject_byte_identity` |
| `forge://staged/pending` resource ↔ `forge_list_staged(status='proposed', limit=500)` | `json.loads(resource) == json.loads(tool_with_those_args)` | `tests/test_console_mcp_resources.py::test_staged_pending_matches_list_tool` |

### Approval-Does-NOT-Execute Regression Guard (D-21, success criterion #4)

**Mechanism:** approval transitions the entity status and emits a DBEvent. forge-bridge contains NO code that listens to `staged.approved` and triggers execution — execution is the proposer's domain (projekt-forge subscribes via the existing event bus and runs against Flame).

**Test shape:**
```python
async def test_approval_does_not_execute(session_factory, monkeypatch):
    """STAGED-07 success criterion #4 — approval is bookkeeping only.

    The proposer (projekt-forge) consumes the staged.approved event and
    executes; forge-bridge does not. Regression guard: ensure no Flame
    bridge call is made during approve(), and the only DB side-effects
    are the entity status update + the staged.approved DBEvent.
    """
    # Probe: monkeypatch forge_bridge.bridge.execute to fail loudly if called
    sentinel = {"called": False}
    async def _no_exec(*args, **kwargs):
        sentinel["called"] = True
        raise AssertionError("approval triggered execution — D-21 violated")
    monkeypatch.setattr("forge_bridge.bridge.execute", _no_exec)

    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(operation="flame.publish", proposer="x", parameters={})
        await session.commit()

    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(op.id, approver="artist")
        await session.commit()

    assert not sentinel["called"], "approval must NOT call bridge.execute"

    # Assert the audit trail is correct
    async with session_factory() as session:
        events = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
    event_types = sorted(e.event_type for e in events)
    assert event_types == ["staged.approved", "staged.proposed"]
```

This is a **negative-assertion test** (proves something did NOT happen). It is the right pattern because the codebase has no listener for `staged.approved` — the test fails loudly the day someone adds one.

### Idempotency Contract Test Matrix (D-09)

| Sequence | Expected outcome |
|---|---|
| `propose` → `approve` | 200 / `status=approved` |
| `propose` → `approve` → `approve` | 2nd: 409 `illegal_transition`, `current_status=approved` |
| `propose` → `reject` | 200 / `status=rejected` |
| `propose` → `reject` → `reject` | 2nd: 409 `illegal_transition`, `current_status=rejected` |
| `propose` → `approve` → `reject` | 2nd: 409 `illegal_transition`, `current_status=approved` |
| `propose` → `reject` → `approve` | 2nd: 409 `illegal_transition`, `current_status=rejected` |
| `propose` → `execute` (skip approval) | Not exposed via FB-B HTTP/MCP — repo-only. If called via repo: 409 `illegal_transition`, `current_status=proposed`. |
| `approve` of non-existent UUID | 404 `staged_op_not_found` (depends on Finding #4 fix) |
| `approve` of malformed UUID | 400 `bad_request` |

Each row → one test case in `tests/console/test_staged_handlers_writes.py`. Mirror MCP equivalents in `tests/mcp/test_staged_tools.py`.

## Open Questions

1. **WR-01 fix scope (Finding #4) — does the planner fix `from_status="(missing)"` in this phase, or defer?**
   - **What we know:** The bug is in FB-A code (`staged_operations.py:289`), surfaced by the FB-B handler that needs `from_status is None` to distinguish 404 from 409. 13-REVIEW.md classifies it as Warning, not Critical. FB-B cannot ship clean error mapping without this being addressed somewhere.
   - **What's unclear:** Whether to fix it in `staged_operations.py` (cleanest) OR adapt FB-B handlers to check `exc.from_status == "(missing)"` (couples FB-B to a private FB-A contract).
   - **Recommendation:** Fix in `staged_operations.py` as part of Plan 14-02 (single-line change + add `not_found: bool` field if explicit disambiguation is desired). Cost: <30 minutes; preserves type contract; unblocks the standard 404/409 split.

2. **Tool registration site (Finding #6 Solution C) — does CONTEXT.md D-17 override the closure-pattern need?**
   - **What we know:** D-17 says "Tool registration site is `forge_bridge/mcp/registry.py::register_builtins()` for the four `forge_*_staged` tools." But `register_builtins(mcp)` runs at import time without `console_read_api` or `session_factory` in scope, while the new tool bodies need both.
   - **What's unclear:** Whether CONTEXT.md D-17 was a default architectural choice (mirror `forge_list_*` family location) without considering the closure constraint, or a load-bearing decision.
   - **Recommendation:** The planner brings this to the user via discuss-phase if D-17 is treated as load-bearing, OR proceeds with Solution C (register staged tools from `register_console_resources()`) and documents the deviation. The latter is the cleaner pattern and matches what the existing `forge_manifest_read` shim already does.

3. **Should `forge_get_staged` also have an HTTP route (e.g., `GET /api/v1/staged/{id}`)?**
   - **What we know:** STAGED-06 lists three HTTP routes: `GET /api/v1/staged`, `POST .../approve`, `POST .../reject`. No single-op fetch. CONTEXT.md D-04 states three routes only.
   - **What's unclear:** Whether the omission was intentional or a copy-paste oversight in the requirement. The MCP tool ships, but a Web UI would naturally expect a single-op JSON endpoint.
   - **Recommendation:** Honor REQUIREMENTS.md as written — three routes only. Web UI consumers can call `GET /api/v1/staged?...` and filter client-side, or use the MCP tool. If a v1.4.x consumer asks for it, add then.

4. **`build_console_app(read_api)` signature change — accept `session_factory` or attach via `read_api`?**
   - **What we know:** `build_console_app(read_api)` at `console/app.py:52` currently accepts only the read API. Write handlers need `session_factory`.
   - **What's unclear:** Whether to (A) extend the signature `build_console_app(read_api, session_factory=None)`, (B) attach `session_factory` to `read_api` so handlers read it via `request.app.state.console_read_api._session_factory`, or (C) attach to `app.state.session_factory` directly during `_lifespan`.
   - **Recommendation:** Option C — `app.state.session_factory = session_factory` next to `app.state.console_read_api = read_api` at `console/app.py:98`. Keeps the read API honest to its name (no write infrastructure leaks into it); keeps the signature stable.

5. **Should planning add `Index("ix_entities_type_status_created", "entity_type", "status", "created_at")` for the list query?**
   - **What we know:** `WHERE entity_type='staged_operation' AND status='proposed' ORDER BY created_at DESC` is the hot-path query for the pending-queue resource. With existing indexes (`ix_entities_status`, `ix_entities_project_type`), the query plan does a heap sort.
   - **What's unclear:** Whether v1.4 volumes (dozens/day per CONTEXT.md) make this matter.
   - **Recommendation:** Skip. Add only if perf testing surfaces a need (would require an Alembic migration `0004_staged_pending_index.py`). Low priority.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code | ✓ | 3.10+ (verified `pyproject.toml:11`) | — |
| `mcp[cli]` | FastMCP server, tool registration | ✓ | `>=1.19,<2` (per `pyproject.toml:15`) | — |
| `sqlalchemy[asyncio]` | repo, session factory | ✓ | `>=2.0` (`pyproject.toml:16`) | — |
| `asyncpg` | Postgres async driver | ✓ | `>=0.29` (`pyproject.toml:17`) | — |
| `starlette` | HTTP routes, JSONResponse | ✓ | (via `mcp[cli]` transitive — verified by import in `console/app.py:8`) | — |
| `pydantic` | Tool input models | ✓ | (transitive via mcp + starlette) | — |
| `pytest-asyncio` | Async test runner (`auto` mode) | ✓ | (`pyproject.toml:35`) | — |
| Postgres at `localhost:5432` | Real-DB integration tests | Conditional | — | Tests skip cleanly via `_phase13_postgres_available()` probe (`tests/conftest.py:120-133`) |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** Postgres — graceful degradation already in place (Phase 13 precedent). Human verification required for full pass per Phase 13 VERIFICATION pattern.

## Project Constraints (from CLAUDE.md)

- **forge-bridge is middleware** — protocol-agnostic communication bus with canonical vocabulary; Flame is one endpoint of many. Phase 14 ships staged-ops surface for ALL endpoints (projekt-forge, MCP clients, future Maya/editorial), not Flame-specific code.
- **Endpoint parity** — bridge does not prefer any endpoint. The four staged tools and three HTTP routes serve all consumers identically.
- **Local first** — no cloud/network surface in this phase. Bind is `127.0.0.1:9996` (per Phase 9 D-28).
- **Don't break the working surface** — the Flame hook at `flame_hooks/forge_bridge/scripts/forge_bridge.py` and the MCP server are deployed and working. Phase 14 only ADDS to the registry/handlers; existing tools and routes must stay byte-stable.

## Project Skills

No `.claude/skills/` or `.agents/skills/` directory in the repo (verified via `ls`). No project skills to consult.

## State of the Art (FastMCP `mcp[cli]>=1.19,<2`)

| Feature | Status | Notes |
|---|---|---|
| `@mcp.resource("uri/{template}", mime_type=...)` | Stable | Used at `console/resources.py:51, 56, 61, 73`. Templates supported. |
| `@mcp.tool(name=..., description=..., annotations={...})` | Stable | Used at `console/resources.py:80, 93`. Annotations dict accepted. |
| `mcp.add_tool(fn, name=..., annotations=..., meta=...)` | Stable | Used at `mcp/registry.py:121`. Direct registration without decorator. |
| Tool annotations: `readOnlyHint`, `idempotentHint`, `destructiveHint`, `openWorldHint`, `title` | Stable | Used pervasively at `mcp/registry.py:186-712`. |
| Tool `meta` parameter | Stable | Used for `_source` provenance at `mcp/registry.py:84-127`. |
| Lifespan via `FastMCP(..., lifespan=...)` | Stable | Used at `mcp/server.py:179-187`. |

No deprecated patterns surfaced. The current `mcp[cli]` API matches the patterns the planner needs to replicate.

## Sources

### Primary (HIGH confidence)
- `forge_bridge/mcp/registry.py` — register_builtins, register_tool patterns (verified via Read)
- `forge_bridge/mcp/tools.py` — tool function shape, Pydantic input models (verified via Read)
- `forge_bridge/mcp/server.py` — _lifespan injection point (verified via Read)
- `forge_bridge/console/handlers.py` — envelope helpers, parser helpers, handler shape (verified via Read)
- `forge_bridge/console/app.py` — route registration, app.state attachment (verified via Read)
- `forge_bridge/console/resources.py` — resource decorator + tool shim closure pattern (verified via Read)
- `forge_bridge/console/read_api.py` — ConsoleReadAPI extension point (verified via Read)
- `forge_bridge/store/staged_operations.py` — StagedOpRepo + StagedOpLifecycleError (verified via Read)
- `forge_bridge/store/repo.py` — EntityRepo, EventRepo, _attrs_to_dict, _to_core (verified via Read)
- `forge_bridge/store/session.py` — async_sessionmaker pattern, get_async_session_factory (verified via Read)
- `forge_bridge/store/models.py` — DBEntity columns + indexes (verified via Read)
- `forge_bridge/core/staged.py` — StagedOperation.to_dict() shape (verified via Read)
- `tests/conftest.py` — session_factory fixture (verified via Read)
- `tests/test_console_mcp_resources.py` — _ResourceSpy + byte-identity test idiom (verified via Read)
- `tests/test_console_routes.py` — TestClient handler test pattern (verified via Read)
- `tests/test_mcp_registry.py` — FastMCP test pattern (verified via Read)
- `tests/test_staged_operations.py` — session_factory consumption pattern (verified via Read)
- `pyproject.toml` — dependency versions, pytest config (verified via Read)
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-CONTEXT.md` — FB-A inherited decisions (verified via Read)
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-VERIFICATION.md` — FB-A surface contract (verified via Read)
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-PATTERNS.md` — repo composition + audit-event pattern (verified via Read)
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-REVIEW.md` — WR-01 documentation (verified via Read)
- `.planning/REQUIREMENTS.md` — STAGED-05/06/07 (verified via Read)
- `.planning/ROADMAP.md` — Phase 14 success criteria (verified via Read)
- `.planning/STATE.md` — key constraints (verified via Read)

### Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| (none) | All claims in this research are verified against in-tree code via the Read tool. The only inferred-but-not-tested claim is that the `mcp[cli]>=1.19` version supports the annotations dict on `add_tool()` — this is verified indirectly because every `mcp/registry.py:184-712` call passes `annotations={...}` and the tests at `test_mcp_registry.py:225-247` exercise the parameter path successfully. No `[ASSUMED]` tags on factual claims. | — | — |

## Metadata

**Confidence breakdown:**
- Standard stack (FastMCP, Starlette, Pydantic, SQLAlchemy): HIGH — all in-tree, all exercised by existing code
- Architecture (single-facade extension, write bypass, two-site registration): HIGH — every pattern has a verified analog
- Pitfalls (WR-01 sentinel mismatch, closure capture for tool registration, byte-identity preservation on lifecycle error): HIGH — surfaced via direct code read

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (30 days for stable surfaces; the only fast-moving piece is the FB-A WR-01 fix which the planner addresses as part of this phase regardless)

## RESEARCH COMPLETE
