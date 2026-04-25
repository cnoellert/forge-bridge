# Phase 9: Read API Foundation - Research

**Researched:** 2026-04-22
**Domain:** Shared read layer (ConsoleReadAPI + ManifestService + console HTTP API on `:9996` as a uvicorn asyncio task + MCP resources + tool fallback shim + Typer entry-point refactor) on an existing FastMCP stdio server
**Confidence:** HIGH — all surface-shaping claims verified against installed `mcp==1.26.0`, `uvicorn==0.41.0`, `starlette==0.52.1`, `typer==0.24.1`, plus direct reads of the working tree.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01..D-31)

**API response conventions:**
- **D-01:** All `/api/v1/` endpoints return a JSON envelope: `{"data": <payload>, "meta": {...}}`. Errors return `{"error": {"code": "<machine_string>", "message": "<human string>"}}`. RFC 7807 is rejected.
- **D-02:** Pagination is `limit`/`offset` query params with `meta.total` returned. Cursor pagination is deferred to v1.4.
- **D-03:** Filter syntax on the HTTP API is plain query params (`?promoted=true&since=...&tool=synth_*&code_hash=abcd1234`). Structured query DSL is a Phase 10 UI-layer parser.
- **D-04:** Field naming is `snake_case` end-to-end. No camelCase translation.
- **D-05:** Default `limit` is 50; max is 500; requests over 500 are clamped silently and `meta.limit` reflects the clamped value.

**ExecutionLog snapshot retention:**
- **D-06:** `ExecutionLog._records: collections.deque[ExecutionRecord]` with `maxlen` via `FORGE_EXEC_SNAPSHOT_MAX` env (default `10_000`). Appended in `record()` AFTER JSONL flush + storage callback fire.
- **D-07:** `ExecutionLog.snapshot(limit, offset, since=None, promoted_only=False, tool=None)` reads deque only — never JSONL.
- **D-08:** Replay on startup re-fills the deque from JSONL up to `maxlen` (newest records win).
- **D-09:** Promotion-only JSONL rows (from `mark_promoted()`) do NOT enter the deque — they mutate the existing record's `promoted` flag in-place if the hash is still in the deque, otherwise they are dropped from the snapshot view (full history still on disk).

**`forge-bridge` entry-point refactor:**
- **D-10:** `forge_bridge/__main__.py` becomes a Typer root. Bare `forge-bridge` boots MCP server unchanged. `forge-bridge console` is an empty subcommand group with `--help` placeholder.
- **D-11:** This refactor lands as its OWN small plan (likely `09-XX-typer-entrypoint`), separate from the API plan.
- **D-12:** Phase 9 design decision, not a Phase 11 surprise.

**`/api/v1/health` depth and shape:**
- **D-13:** Phase 9 ships the FULL multi-service health shape (not a thin placeholder).
- **D-14:** Response shape: `{data: {status, ts, version, services: {mcp, flame_bridge, ws_server, llm_backends, watcher, storage_callback, console_port}, instance_identity: {execution_log, manifest_service}}, meta: {}}`.
- **D-15:** Top-level `status` = `ok` if all services ok, `degraded` if any non-critical (LLM, storage_callback) fail, `fail` if any critical (mcp, watcher, instance_identity) fail.
- **D-16:** `instance_identity` compares `id(execution_log_in_lifespan)` vs `id(execution_log_in_console_read_api)` (and same for `manifest_service`). Mismatch = FAIL at boot.
- **D-17:** Each service check has 2s timeout; handler never blocks longer than `~ N_services * 2s`.
- **D-18:** Storage-callback check is "registered or absent" — absence is not a failure.

**Stdio safety enforcement (P-01):**
- **D-19:** Belt-and-suspenders — P-01 has no graceful failure mode.
- **D-20:** Custom `LOGGING_CONFIG` dict passed to `uvicorn.Config(log_config=LOGGING_CONFIG)` — routes `uvicorn`, `uvicorn.access`, `uvicorn.error` loggers to **stderr**, never stdout.
- **D-21:** `access_log=False` on uvicorn config.
- **D-22:** `ruff` lint gate bans `print(` in `forge_bridge/console/`. All output via `logging.getLogger(__name__)`.
- **D-23:** Phase 9 SC#1 integration test: `tools/list` over MCP stdio while console HTTP API serves traffic concurrently on `:9996`. Assert MCP wire is byte-clean.

**MCP resources + tool fallback shims:**
- **D-24:** Phase 9 ships ALL of: `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}` (RFC 6570), `forge://health`, `forge_manifest_read` tool, and `forge_tools_read(name: str | None = None)` single-shim tool.
- **D-25:** Resources and tool shims read through the SAME `ConsoleReadAPI` methods that back the HTTP routes. Verified by D-16 instance-identity check.
- **D-26:** All resources return `application/json` MIME type. Resource bodies are byte-identical to the corresponding `/api/v1/` HTTP response payloads — same serializer.

**Console port configuration:**
- **D-27:** Port precedence: `--console-port` flag > `FORGE_CONSOLE_PORT` env > default `9996`. Flag lives on the bare `forge-bridge` invocation.
- **D-28:** Bind is `127.0.0.1` only — not configurable in v1.3.
- **D-29:** Graceful degradation per API-06: if port unavailable, uvicorn task logs WARNING and MCP server continues to boot. Mirrors v1.2.1 `startup_bridge` pattern.

**`_lifespan` task lifecycle:**
- **D-30:** `_lifespan` owns three independent asyncio tasks — `watcher_task`, `console_task`, existing bridge client. Failure of any one logs WARNING and does not cancel the others.
- **D-31:** Order in `_lifespan` startup: (1) `startup_bridge()`, (2) `ManifestService` + canonical `ExecutionLog`, (3) `watcher_task(manifest_service=...)`, (4) `ConsoleReadAPI(execution_log=..., manifest_service=...)`, (5) Starlette app + `register_console_resources(mcp, manifest_service, console_read_api)`, (6) `console_task`.

### Claude's Discretion
- Exact `ConsoleReadAPI` method signatures (kwargs, return types).
- Internal package layout under `forge_bridge/console/`.
- Starlette `Route()` list vs `@app.route` decorators.
- CORS middleware config — default to `["http://127.0.0.1:9996", "http://localhost:9996"]`.
- Watcher injection signature for `ManifestService` — backward-compatible default `manifest_service: ManifestService | None = None`.

### Deferred Ideas (OUT OF SCOPE)
- Cursor pagination on `/api/v1/execs` (v1.4 with SSE).
- RFC 7807 Problem Details error envelope.
- CORS configurability.
- Storage-callback detail exposed via `/api/v1/health` (only "registered or absent" in Phase 9).
- Promotion-event mirror in the in-memory deque (mutate-in-place only; full history stays on disk).
- Real-time push (SSE) for execs/manifest/health (locked v1.4 deferral).
- `forge://tools/{name}` etag/cache-control headers.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | `ConsoleReadAPI` is sole read path for all surfaces — unit-testable in isolation | §2 (method signatures), §8 (registration fan-out), §V-1..V-6 (per-method unit tests) |
| API-02 | HTTP API on `:9996` via separate uvicorn task in `_lifespan`, independent of MCP transport | §1 (Starlette app shape), §2 (uvicorn task embedding), §6 (port precheck), §10 (lifespan wiring) |
| API-03 | `/api/v1/` namespace, JSON responses — routes `/tools`, `/execs`, `/manifest`, `/health`, `/chat` | §1 (Starlette Route list), §5 (envelope handler pattern) |
| API-04 | `_lifespan` owns canonical `ExecutionLog` + `ManifestService`; instance-identity gate | §8 (ManifestService singleton), §10 (wiring order), §V-health (id() assertion test) |
| API-05 | Optional `StoragePersistence` read-adapter mirrors write-side Protocol (opt-in) | Already shipped v1.3.0 — Phase 9 only surfaces presence in `/api/v1/health` per D-18 |
| API-06 | Console port fallback: log WARNING and boot MCP anyway | §6 (port precheck + uvicorn failure modes), v1.2.1 precedent mirrored |
| MFST-01 | `ManifestService` singleton owns in-memory manifest, injected into watcher + console router | §8 (ToolRecord + ManifestService shape), §10 (injection sequence) |
| MFST-02 | `forge://manifest/synthesis` MCP resource | §4 (resource decorator), §9 (register_console_resources) |
| MFST-03 | `forge_manifest_read` MCP tool fallback shim (ships in SAME plan as MFST-02) | §9 (single-file module with both resource + tool) |
| MFST-06 | ManifestService satisfies EXT-01 — projekt-forge reads via MCP resource and/or HTTP API | §8 (snapshot() contract), §9 (registered surfaces) |
| TOOLS-04 | `forge://tools`, `forge://tools/{name}`, and `forge_tools_read(name=None)` shim | §4 (URI template verification), §9 (single-shim pattern) |
| EXECS-04 | Execution data reads through shared `ConsoleReadAPI` — no per-surface JSONL parsers | §2 (get_executions signature), §6 (snapshot filtering) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- forge-bridge is **middleware** — protocol-agnostic communication bus. Canonical vocabulary, endpoint parity, local-first. The console is another endpoint in the bus, not a bolt-on.
- Don't break the deployed stdio MCP server behaviour that Claude Desktop / Claude Code depend on. Bare `forge-bridge` must still boot MCP unchanged (D-10).
- All new code must use `logging.getLogger(__name__)` — never `print()` (D-22 enforces this via ruff).

## Executive Summary

Phase 9 wires three new runtime components into the existing `_lifespan` (`forge_bridge/mcp/server.py`): a `ManifestService` singleton (new `forge_bridge/console/manifest_service.py`), a `ConsoleReadAPI` (new `forge_bridge/console/read_api.py`), and a Starlette app served by a `uvicorn.Server` asyncio task on `127.0.0.1:9996`. The MCP server continues to run in stdio mode — the console HTTP API is a **separate asyncio task inside the same process**, not served by FastMCP's `custom_route`. A `register_console_resources(mcp, manifest_service, console_read_api)` call in `_lifespan` registers five resources (`forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health`, and the already-shipped `forge://llm/health` stays put in `llm/health.py`) plus two MCP tools (`forge_manifest_read`, `forge_tools_read(name=None)`). Every resource and tool reads through the **same `ConsoleReadAPI` instance** that backs the `/api/v1/` routes — byte-identical payloads, single read path, verified at boot by `id()`-equality in `/api/v1/health.instance_identity`.

The critical stdio-safety discipline is: pass a custom `LOGGING_CONFIG` dict to `uvicorn.Config(log_config=..., access_log=False)` that routes every uvicorn logger to `ext://sys.stderr`. Default uvicorn `log_config` writes access logs to **stdout** — which would corrupt the MCP stdio wire. This, combined with the ruff `print(` ban in `forge_bridge/console/` and a runtime integration test that runs `tools/list` over stdio while `:9996` is serving traffic, is the belt-and-suspenders P-01 defense.

`ExecutionLog` gains a bounded `collections.deque` (D-06) appended in `record()` after the existing JSONL flush + callback fire. `snapshot()` reads deque-only (O(1) tail, O(k) filter). The Typer root in `__main__.py` uses `@app.callback(invoke_without_command=True)` so bare `forge-bridge` still boots MCP — verified signature in typer 0.24.1. Port-unavailable degradation is handled by a `try:socket.bind()` precheck **before** constructing the uvicorn Server (cleaner failure than letting `Server.serve()` raise `OSError`); log WARNING, skip the task, let MCP continue.

**Primary recommendation:** Ship Phase 9 as **two plans**: (1) the Typer-root refactor per D-11 (small, reviewable, lands first), (2) the console package + `_lifespan` wiring + MCP resources/tools (single atomic plan covering MFST-01/02/03, TOOLS-04, EXECS-04, API-01..06). Success criteria 1-5 are all verifiable via `pytest` + one manual MCP-client UAT.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Stdio MCP wire (tools/call, tools/list, resources/*) | MCP server process (stdin/stdout) | — | Locked non-goal: stdio is the default transport (P-02 prevention). |
| HTTP read API on `:9996` | uvicorn asyncio task inside same process | — | Separate uvicorn task is the ONLY viable pattern in stdio mode (P-01). |
| Manifest state (in-memory) | `ManifestService` singleton owned by `_lifespan` | Watcher (sole writer), `ConsoleReadAPI` (sole reader) | Single writer + single reader + instance-identity gate prevents LRN-05-class drift. |
| Execution log state (in-memory) | `ExecutionLog._records` deque owned by `_lifespan` | `record()` writes, `snapshot()` reads | JSONL is canonical on disk; deque is the hot-path query surface (P-04 prevention). |
| MCP resource registration | `register_console_resources(mcp, manifest_service, console_read_api)` called from `_lifespan` after services exist | — | Resources need live services at registration time — can't register at import. |
| MCP tool fallback shims | Same module as resources (`forge_bridge/console/resources.py`) | — | Tool shims read the same `ConsoleReadAPI`, byte-identical to resources (D-26). |
| CLI subcommand group | Typer root in `__main__.py` | Empty `console` subcommand group in Phase 9 | Phase 11 fills subcommands. Phase 9 only lays the entry-point scaffold (D-10, D-11). |
| Health check fan-out | `ConsoleReadAPI.get_health()` | Short-circuit + 2s per-service timeout | D-17 bounds total wait time. |

## Standard Stack

### Core (all verified installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp[cli]` | >=1.19,<2 (installed: 1.26.0) | FastMCP, `@mcp.resource()`, URI templates | `[VERIFIED: importlib.metadata.version('mcp')]` — already pinned in pyproject |
| `starlette` | 0.52.1 | ASGI routing (Route, JSONResponse, Request) | `[VERIFIED: transitive via mcp[cli]]` — everything needed for the console API without FastAPI's weight |
| `uvicorn` | 0.41.0 | Programmatic `uvicorn.Server(Config).serve()` inside an asyncio task | `[VERIFIED: transitive via mcp[cli]]` — same server FastMCP uses internally |
| `typer` | 0.24.1 | CLI subcommand scaffolding for Phase 9 (empty `console` group) | `[VERIFIED: transitive via mcp[cli]]` — sync-only (verified live test in STACK.md) |
| stdlib `logging` | — | All console output | `[CITED: CLAUDE.md]` universal in codebase; D-22 lint gate enforces |
| stdlib `collections.deque` | — | Bounded in-memory execution snapshot | `[VERIFIED: Python 3.10+]` `maxlen` kwarg + O(1) append, O(n) iteration |
| stdlib `fnmatch` | — | `tool` filter glob (e.g. `synth_*`) | `[VERIFIED: Python stdlib]` — matches shell-glob convention D-03 promises |
| stdlib `socket` | — | Port precheck for `API-06` degradation | `[VERIFIED: Python stdlib]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `starlette.middleware.cors.CORSMiddleware` | — (Starlette core) | Allow `http://127.0.0.1:9996` + `http://localhost:9996` | Every Starlette app in Phase 9 (Claude discretion locked at default) |
| `sse_starlette` | 3.2.0 | Deferred v1.4 — do not use in Phase 9 | `[VERIFIED: transitive]` — listed only to confirm it's available when SSE phase arrives |
| `httpx` | >=0.27 | Phase 11 CLI consumer — NOT used in Phase 9 | Called out so plans don't accidentally add a consumer in this phase |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `uvicorn.Server` embedded | `FastMCP.custom_route` + `mcp.run(transport="http")` | Rejected by CONTEXT §STACK conflict resolution — breaks Claude Desktop/Code stdio configs (P-02). Locked. |
| Starlette `Route()` list | `@app.route` decorator pattern | **Recommendation: Route list.** Starlette's `@app.route` only exists on an already-constructed `Starlette` app; the cleaner idiom (and the one FastMCP uses internally in `streamable_http_app()`) is `Starlette(routes=[Route(...), ...])`. Decorator adds a mutable-app anti-pattern. |
| FastAPI | Starlette only | Rejected — adds ~1 MB deps for zero gain; Starlette already installed. |
| `collections.deque` for snapshots | `list` with slicing | Deque gives O(1) appends with `maxlen` bounded; list requires manual truncation. D-06 locks deque. |

**No new pip dependencies in Phase 9.** Jinja2 lands in Phase 10. Typer entrypoint is already wired via `[project.scripts]`.

**Version verification:** `[VERIFIED: python3 -c "import importlib.metadata as m; print(m.version('mcp'))"] → 1.26.0` on 2026-04-22. `[VERIFIED: starlette==0.52.1, uvicorn==0.41.0, typer==0.24.1]`.

## Architecture Patterns

### System Architecture Diagram

```
  External MCP client (Claude Desktop, Claude Code, Cursor, Gemini CLI)
             │  stdio (JSON-RPC framed messages on stdin/stdout)
             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ forge_bridge process — single asyncio event loop                │
  │                                                                 │
  │  FastMCP("forge_bridge")  ◄──── tools/list, tools/call,         │
  │    │                           resources/read                   │
  │    │                                                            │
  │    └── _lifespan (async context manager)                        │
  │         │                                                       │
  │         ├── 1. startup_bridge()     → WS client to :9998        │
  │         │                                                       │
  │         ├── 2. ManifestService()     ──┐                        │
  │         │   ExecutionLog(...)        ──┤                        │
  │         │                              │ shared singletons      │
  │         ├── 3. watcher_task ◄──────────┤ (writer path)          │
  │         │       │  manifest_service=─┤                          │
  │         │       │  reads .sidecar.json,                         │
  │         │       │  calls manifest_service.register()            │
  │         │       │                    │                          │
  │         ├── 4. ConsoleReadAPI(       ┤                          │
  │         │        execution_log=─────┤                           │
  │         │        manifest_service=──┤  reader fan-out           │
  │         │        llm_router,                                    │
  │         │        bridge_url                                     │
  │         │    )                                                  │
  │         │                                                       │
  │         ├── 5. Starlette(routes=[...])   ──┐                    │
  │         │    register_console_resources(    │                   │
  │         │        mcp, manifest_service,     │ byte-identical    │
  │         │        console_read_api)          │ reads             │
  │         │    │                               │                  │
  │         │    ├── GET /api/v1/tools    ──┐   │                   │
  │         │    ├── GET /api/v1/execs      ├──┤                    │
  │         │    ├── GET /api/v1/manifest   ├──┤                    │
  │         │    ├── GET /api/v1/health     ┘   │                   │
  │         │    │                               │                  │
  │         │    └── mcp resources:              │                  │
  │         │       forge://tools              ──┤                  │
  │         │       forge://tools/{name}       ──┤                  │
  │         │       forge://manifest/synthesis──┤                   │
  │         │       forge://health             ──┘                  │
  │         │       (+ tool shims: forge_manifest_read,             │
  │         │                      forge_tools_read(name=None))     │
  │         │                                                       │
  │         └── 6. console_task = asyncio.create_task(              │
  │                uvicorn.Server(Config(app,                       │
  │                    host="127.0.0.1", port=9996,                 │
  │                    log_config=STDERR_ONLY_CONFIG,               │
  │                    access_log=False)).serve())                  │
  │                                                                 │
  │  Port precheck: socket.bind((host, port)) BEFORE construction.  │
  │  If OSError: log WARNING, skip task, MCP continues (D-29).      │
  │                                                                 │
  └─────────────────────────────────────────────────────────────────┘
             ▲                                    ▲
             │ :9996 HTTP                         │ :9998 WS
             │ (browser, CLI via httpx)           │ (WS clients)
             │                                    │
    Web UI (Phase 10)                     forge-bridge standalone
    CLI companion (Phase 11)              (already running)
```

### Recommended Project Structure

```
forge_bridge/
├── __main__.py             # Typer root (D-10/11)
├── mcp/
│   └── server.py           # _lifespan extended with ManifestService, ConsoleReadAPI, console_task
├── learning/
│   ├── execution_log.py    # + _records deque, snapshot()
│   └── watcher.py          # + manifest_service kwarg
└── console/                # NEW package (Phase 9)
    ├── __init__.py         # Barrel: ManifestService, ToolRecord, ConsoleReadAPI
    ├── manifest_service.py # ManifestService + ToolRecord frozen dataclass
    ├── read_api.py         # ConsoleReadAPI class + snake_case method surface
    ├── app.py              # build_console_app(read_api) → Starlette, env + CORS + LOGGING_CONFIG
    ├── handlers.py         # Route handler functions — envelope wrapper, query parsing, clamping
    ├── resources.py        # register_console_resources(mcp, manifest_service, console_read_api)
    └── logging_config.py   # STDERR_ONLY_LOGGING_CONFIG dict (D-20)
```

### Pattern 1: Uvicorn server embedded inside `_lifespan` with startup signaling

**What:** Launch `uvicorn.Server(Config(...)).serve()` as an `asyncio.create_task`, await its `.started` attribute as a lightweight startup barrier, and cancel on lifespan exit.

**When to use:** Every embedded-uvicorn pattern inside an asyncio process.

**Code:** `[VERIFIED: inspect.signature(uvicorn.Server.__init__)] → (config: Config); `[VERIFIED: attr 'started: bool' set on __init__ and flipped in startup()`]

```python
# forge_bridge/mcp/server.py — within _lifespan after step 5
from forge_bridge.console.app import build_console_app
from forge_bridge.console.logging_config import STDERR_ONLY_LOGGING_CONFIG
import socket, uvicorn, asyncio

async def _start_console_task(
    app,
    host: str,
    port: int,
    ready_timeout: float = 5.0,
) -> tuple[asyncio.Task | None, uvicorn.Server | None]:
    """Return (task, server) on success; (None, None) on port-bind failure."""
    # Port precheck — cleaner than letting Server.serve() raise (see §6)
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind((host, port))
    except OSError as e:
        logger.warning(
            "Console API disabled — port %s:%d unavailable: %s. "
            "MCP server continues without :9996.", host, port, e
        )
        probe.close()
        return None, None
    finally:
        probe.close()

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_config=STDERR_ONLY_LOGGING_CONFIG,  # D-20
        access_log=False,                        # D-21
        lifespan="off",                          # Starlette app has no lifespan of its own
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(), name="console_uvicorn_task")

    # Lightweight startup barrier: Server.started flips True in Server.startup()
    deadline = asyncio.get_running_loop().time() + ready_timeout
    while not server.started and asyncio.get_running_loop().time() < deadline:
        if task.done():  # serve() exited early — bind failed after precheck
            return None, None
        await asyncio.sleep(0.02)
    if not server.started:
        logger.warning("Console uvicorn did not signal started within %.1fs", ready_timeout)
    return task, server
```

### Pattern 2: Envelope wrapper at the handler boundary

**What:** Handlers return raw payloads from `ConsoleReadAPI`; a thin handler wrapper adds `{data: ..., meta: ...}` on the way out. This keeps `ConsoleReadAPI` surface-agnostic so MCP resources can call the same methods and re-wrap themselves.

**When to use:** Every HTTP route handler under `/api/v1/`.

**Code:**
```python
# forge_bridge/console/handlers.py
from starlette.requests import Request
from starlette.responses import JSONResponse

def _envelope(data, **meta) -> JSONResponse:
    return JSONResponse({"data": data, "meta": meta})

def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)

async def tools_handler(request: Request) -> JSONResponse:
    tools = await request.app.state.console_read_api.get_tools()
    return _envelope([t.to_dict() for t in tools], total=len(tools))

async def execs_handler(request: Request) -> JSONResponse:
    limit, offset = _parse_pagination(request)  # clamps per D-05
    since, promoted_only, tool_glob, code_hash = _parse_filters(request)  # D-03
    records, total = await request.app.state.console_read_api.get_executions(
        limit=limit, offset=offset, since=since,
        promoted_only=promoted_only, tool=tool_glob, code_hash=code_hash,
    )
    return _envelope(
        [asdict(r) for r in records],
        limit=limit, offset=offset, total=total,
    )
```

### Pattern 3: MCP resource = HTTP route (byte-identical)

**What:** Resources and tool shims use the same serializer the Starlette route uses, so both surfaces produce identical bytes.

**Code:**
```python
# forge_bridge/console/resources.py
import json
from mcp.server.fastmcp import FastMCP
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI

def _envelope_json(data, **meta) -> str:
    """Same serialization as the HTTP handler envelope — D-26 byte-identical."""
    return json.dumps({"data": data, "meta": meta}, default=str)

def register_console_resources(
    mcp: FastMCP,
    manifest_service: ManifestService,
    console_read_api: ConsoleReadAPI,
) -> None:
    @mcp.resource("forge://manifest/synthesis", mime_type="application/json")
    async def synthesis_manifest() -> str:
        data = await console_read_api.get_manifest()
        return _envelope_json(data)

    @mcp.resource("forge://tools", mime_type="application/json")
    async def tools_list() -> str:
        tools = await console_read_api.get_tools()
        return _envelope_json([t.to_dict() for t in tools], total=len(tools))

    @mcp.resource("forge://tools/{name}", mime_type="application/json")
    async def tool_detail(name: str) -> str:  # FastMCP extracts 'name' by kwarg match
        tool = await console_read_api.get_tool(name)
        if tool is None:
            return json.dumps({"error": {"code": "tool_not_found",
                                          "message": f"no tool named {name!r}"}})
        return _envelope_json(tool.to_dict())

    @mcp.resource("forge://health", mime_type="application/json")
    async def health() -> str:
        data = await console_read_api.get_health()
        return _envelope_json(data)

    # Tool fallback shims (D-24, P-03 prevention)
    @mcp.tool(
        name="forge_manifest_read",
        description="Read the current synthesis manifest. Alias for resources/read forge://manifest/synthesis.",
        annotations={"readOnlyHint": True},
    )
    async def forge_manifest_read() -> str:
        data = await console_read_api.get_manifest()
        return _envelope_json(data)

    @mcp.tool(
        name="forge_tools_read",
        description=(
            "Read registered tools. Omit 'name' for the full list (alias for "
            "forge://tools); pass 'name' for per-tool detail (alias for "
            "forge://tools/{name})."
        ),
        annotations={"readOnlyHint": True},
    )
    async def forge_tools_read(name: str | None = None) -> str:
        if name is None:
            tools = await console_read_api.get_tools()
            return _envelope_json([t.to_dict() for t in tools], total=len(tools))
        tool = await console_read_api.get_tool(name)
        if tool is None:
            return json.dumps({"error": {"code": "tool_not_found",
                                          "message": f"no tool named {name!r}"}})
        return _envelope_json(tool.to_dict())
```

`[VERIFIED: mcp==1.26.0]` — URI template `{name}` is extracted by kwarg-match with the resource function parameter. Live probe:
```
>>> @mcp.resource('forge://tools/{name}')
... async def tool_detail(name: str) -> str: ...
>>> list_resource_templates() → ResourceTemplate(uriTemplate='forge://tools/{name}', ...)
```

### Anti-Patterns to Avoid

- **`print()` anywhere in `forge_bridge/console/`** — stdout corruption in stdio mode (P-01). Enforced by D-22 ruff gate.
- **`FastMCP.custom_route` for the console** — only works in `mcp.run(transport="http")` mode; breaks stdio (P-02). Rejected in CONTEXT.md conflict resolution.
- **Second read path for MCP resources or tool shims** — if resources parse JSONL or query `mcp.list_tools()` directly, LRN-05-class drift returns. Always go through `ConsoleReadAPI`.
- **Holding `fcntl.LOCK_EX` across the HTTP request boundary** — `ExecutionLog.snapshot()` reads the in-memory deque only (D-07), never the JSONL, so no lock is taken on the read path.
- **Catching `Exception` silently in `_lifespan` task bodies** — each task's failure must log WARNING with `type(exc).__name__` (avoid `str(exc)` per Phase 8 LRN on credential leak in SQLAlchemy errors) and allow siblings to keep running (D-30).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stdin/stdout-safe uvicorn logging | Custom log intercept | `uvicorn.Config(log_config=STDERR_ONLY_LOGGING_CONFIG, access_log=False)` | Uvicorn already supports log-config dict override; inverting the default stdout access handler is a 20-line dict. |
| URI template parameter extraction | Custom `{name}` parser | `@mcp.resource("forge://tools/{name}") async def f(name: str)` | `[VERIFIED: mcp==1.26.0]` extracts via kwarg-match. |
| CORS allow-list | Custom middleware | `starlette.middleware.cors.CORSMiddleware(allow_origins=[...], allow_methods=["GET"])` | Stock Starlette; D-28 locks bind to 127.0.0.1, so the allow-list is a 2-entry known-host list. |
| Sliding-window rate limiter for chat | Custom counter | Defer to Phase 12 — not in Phase 9 | Rate limit is CHAT-only (v1.3 P-07 prevention). |
| Bounded execution snapshot | `list` + manual truncation | `collections.deque(maxlen=N)` | O(1) append + auto-eviction. D-06 locks. |
| Tool-glob filter (`synth_*`) | Manual wildcard | `fnmatch.fnmatch(tool_name, glob)` | Stdlib; matches shell-glob D-03 promises. |
| Startup barrier for uvicorn | Custom event | Poll `uvicorn.Server.started` | `[VERIFIED: uvicorn==0.41.0]` — `started: bool` flips to True in `Server.startup()`. |
| Health check fan-out with timeout | Custom gather | `asyncio.wait_for(check(), timeout=2.0)` per-service | D-17 bounds per-check; total ≤ N × 2s. |

**Key insight:** This phase is ~90% glue code. Every non-glue piece has a standard library or installed-dep answer. The only authored logic is `ManifestService`, `ConsoleReadAPI`, and route handlers.

## Runtime State Inventory

**Not applicable — Phase 9 is purely additive.** No rename, refactor, or migration. New code lands in `forge_bridge/console/`; existing code gains backward-compatible kwargs (`manifest_service=None` on `watch_synthesized_tools`) or additive methods (`ExecutionLog.snapshot`). Pre-existing JSONL, `.sidecar.json`, and Flame hook state are all untouched. Section omitted per protocol.

## Common Pitfalls

### Pitfall P9-1: Uvicorn default log_config writes access to stdout

**What goes wrong:** Without `log_config=...`, uvicorn uses its default config which includes `'access': {'stream': 'ext://sys.stdout'}`. A single access-log line corrupts the stdio MCP wire — client sees framing error, disconnects silently.

**Why it happens:** The default `log_config` dict is assembled in `uvicorn.config.LOGGING_CONFIG` and applied automatically.

**How to avoid:** Always pass a fully-specified `log_config` dict that routes every handler to `ext://sys.stderr`, plus `access_log=False` as suspenders. Exact dict in §3 below.

**Warning signs:** Claude Desktop or Claude Code disconnects with framing error during `GET /api/v1/` traffic on `:9996`.

### Pitfall P9-2: Resource registration at module import time

**What goes wrong:** If `register_console_resources(mcp, ...)` is called at module import (like `register_builtins`), `manifest_service` and `console_read_api` don't exist yet — you have to pass a module-level None and lazy-resolve at request time.

**How to avoid:** Call `register_console_resources(mcp, manifest_service, console_read_api)` inside `_lifespan` AFTER step 4 (constructing `ConsoleReadAPI`), AS step 5 — before `console_task` starts. FastMCP accepts `@mcp.resource` / `@mcp.tool` registration after server construction.

### Pitfall P9-3: `ExecutionLog.snapshot()` returns stale `promoted` flags

**What goes wrong:** D-09 mutates the `promoted` flag in-place on the deque record. But `ExecutionRecord` is `@dataclass(frozen=True)` — `promoted` can't be mutated.

**How to avoid:** Either (a) rebuild the record via `dataclasses.replace(existing, promoted=True)` and swap it into the deque at the found index, or (b) maintain a parallel `_promoted_hashes: set[str]` alongside the deque and JOIN at snapshot time. Option (b) is simpler and avoids O(n) deque traversal on each promotion event — **recommend (b)**.

```python
def mark_promoted(self, code_hash: str) -> None:
    ...
    self._promoted_hashes.add(code_hash)

def snapshot(self, ...):
    # During iteration:
    for rec in iter_filtered:
        yield dataclasses.replace(rec, promoted=(rec.code_hash in self._promoted_hashes))
```

### Pitfall P9-4: Port-bind succeeds but uvicorn fails on second bind

**What goes wrong:** `socket.bind()` precheck binds, then closes. Between close and `uvicorn.Server.serve()` rebinding, another process can grab the port. Uvicorn then raises `OSError` that propagates into the asyncio task and surfaces as an unhandled task exception.

**How to avoid:** (1) Use `SO_REUSEADDR` on probe so it releases cleanly; (2) wrap `server.serve()` in try/except OSError inside the task; (3) after the startup barrier (`server.started`), treat the task as supervised — on OSError log WARNING, let other tasks continue.

### Pitfall P9-5: Instance-identity check false-negative in test fixtures

**What goes wrong:** Tests that construct a fresh `ExecutionLog` and pass it to `ConsoleReadAPI` but also pass a different instance to the watcher will FAIL the `id() == id()` gate at `/api/v1/health.instance_identity`. This is **correct behavior** — it catches LRN-05. But developer first-run will look like a bug.

**How to avoid:** Document that `/api/v1/health` with status=`fail` + `instance_identity.execution_log.id_match=false` means the caller passed two different `ExecutionLog` instances to the two seats. A test helper `make_lifespan_fixtures()` that returns the canonical pair prevents drift in test code.

### Pitfall P9-6: Typer `invoke_without_command=True` swallows subcommand args

**What goes wrong:** If the root callback has `invoke_without_command=True` but also accepts `--console-port`, Typer 0.24.1 will try to parse `--console-port 9996 console --help` in a way that treats `console` as a positional. The subcommand won't be reached.

**How to avoid:** Declare `--console-port` as an option on the **callback**, place `console` as a proper subcommand (`@app.add_typer(...)` or `@app.command(...)`). Test: `forge-bridge --console-port 9996` (boots MCP with override), `forge-bridge console --help` (exits 0), `forge-bridge` (boots MCP default port). Canonical pattern in §7.

## Code Examples

### §1 — Starlette app factory with routes list + CORS

```python
# forge_bridge/console/app.py
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

from forge_bridge.console.handlers import (
    tools_handler, tool_detail_handler,
    execs_handler, manifest_handler, health_handler,
)
from forge_bridge.console.read_api import ConsoleReadAPI

def build_console_app(read_api: ConsoleReadAPI) -> Starlette:
    routes = [
        Route("/api/v1/tools", tools_handler, methods=["GET"]),
        Route("/api/v1/tools/{name}", tool_detail_handler, methods=["GET"]),
        Route("/api/v1/execs", execs_handler, methods=["GET"]),
        Route("/api/v1/manifest", manifest_handler, methods=["GET"]),
        Route("/api/v1/health", health_handler, methods=["GET"]),
    ]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:9996", "http://localhost:9996"],
            allow_methods=["GET"],
            allow_headers=["*"],
            allow_credentials=False,
        ),
    ]
    app = Starlette(routes=routes, middleware=middleware)
    app.state.console_read_api = read_api
    return app
```

`[VERIFIED: starlette==0.52.1]` — `Starlette(routes=[...], middleware=[...])` and `CORSMiddleware(allow_origins=[...], allow_methods=[...], ...)` signatures confirmed via `inspect.signature`.

### §2 — ConsoleReadAPI method surface

```python
# forge_bridge/console/read_api.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord
    from forge_bridge.console.manifest_service import ManifestService, ToolRecord
    from forge_bridge.llm.router import LLMRouter

@dataclass
class HealthSnapshot:
    status: str                # "ok" | "degraded" | "fail"
    ts: str                    # ISO8601
    version: str
    services: dict             # matches D-14 services block
    instance_identity: dict    # matches D-14 instance_identity block

class ConsoleReadAPI:
    """Sole read layer for Web UI / CLI / MCP resources / chat.

    All other surfaces MUST read through this class. Verified by the
    instance-identity gate in get_health() at boot (D-16).
    """

    def __init__(
        self,
        execution_log: "ExecutionLog",
        manifest_service: "ManifestService",
        llm_router: Optional["LLMRouter"] = None,
        flame_bridge_url: Optional[str] = None,  # e.g. http://127.0.0.1:9999
        ws_bridge_url: Optional[str] = None,     # e.g. ws://127.0.0.1:9998
        console_port: int = 9996,
    ) -> None:
        self._execution_log = execution_log
        self._manifest_service = manifest_service
        self._llm_router = llm_router
        self._flame_bridge_url = flame_bridge_url
        self._ws_bridge_url = ws_bridge_url
        self._console_port = console_port

    # --- Tools -------------------------------------------------------------

    async def get_tools(self) -> list["ToolRecord"]:
        """Return every registered ToolRecord, builtin and synthesized.
        Order: insertion order (watcher-registered synthesized tools trail
        builtins by registration time)."""
        return self._manifest_service.get_all()

    async def get_tool(self, name: str) -> Optional["ToolRecord"]:
        """Return a single ToolRecord by name, or None."""
        return self._manifest_service.get(name)

    # --- Executions --------------------------------------------------------

    async def get_executions(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[datetime] = None,
        promoted_only: bool = False,
        tool: Optional[str] = None,       # fnmatch glob, e.g. "synth_*"
        code_hash: Optional[str] = None,  # exact or prefix match
    ) -> tuple[list["ExecutionRecord"], int]:
        """Return (records, total_before_pagination).

        total_before_pagination is what the caller shows in meta.total (D-01).
        """
        return self._execution_log.snapshot(
            limit=limit, offset=offset,
            since=since, promoted_only=promoted_only,
            tool=tool, code_hash=code_hash,
        )

    # --- Manifest ----------------------------------------------------------

    async def get_manifest(self) -> dict:
        """Return the full manifest payload (wrapped by the caller's envelope).

        Shape: {"tools": [ToolRecord.to_dict(), ...], "count": N,
                "schema_version": "1"}
        """
        tools = self._manifest_service.get_all()
        return {
            "tools": [t.to_dict() for t in tools],
            "count": len(tools),
            "schema_version": "1",
        }

    # --- Health ------------------------------------------------------------

    async def get_health(self) -> dict:
        """Return the full D-14 health body."""
        # ... parallel asyncio.wait_for(check, timeout=2.0) for each service;
        # instance_identity reads id(self._execution_log), id(self._manifest_service)
        # and compares against the _lifespan-owned references passed in here —
        # they're the same object, so id_match=True at steady state. Caught at boot.
        ...
```

**Return type philosophy (Claude's discretion resolution):** `ConsoleReadAPI` returns **raw domain objects** (`ToolRecord`, `ExecutionRecord`, plain dicts for aggregates). The envelope `{data, meta}` is applied in the handler/resource wrapper. This keeps `ConsoleReadAPI` unit-testable without HTTP mocks, lets MCP resources build the same envelope, and matches P-09 prevention: if envelope shape ever changes, only the two wrappers (HTTP handler + MCP resource) need updating — not `ConsoleReadAPI` methods.

### §3 — Stdio-safe LOGGING_CONFIG dict (D-20)

```python
# forge_bridge/console/logging_config.py

STDERR_ONLY_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(name)s %(message)s",
            "use_colors": False,
        },
    },
    "handlers": {
        # EVERY handler writes to STDERR, not stdout.
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn":        {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.error":  {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        # access logs are also disabled via access_log=False (D-21, belt).
    },
}
```

`[VERIFIED: uvicorn==0.41.0]` default `LOGGING_CONFIG` reviewed — it routes access to `ext://sys.stdout`. This dict inverts that. `use_colors=False` prevents ANSI escape bytes in stderr that could confuse downstream log consumers.

### §4 — FastMCP resource decorator with URI template

`[VERIFIED: mcp==1.26.0 live probe]` — the `name` parameter of the resource function is matched by kwarg against the `{name}` URI template variable. Multiple template variables are supported; each must correspond to a function parameter by name. The resource does NOT receive `uri` or a `Request` object; it just receives the extracted template variables as kwargs.

```python
# Live-verified 2026-04-22:
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("test")

@mcp.resource("forge://tools/{name}", mime_type="application/json")
async def tool_detail(name: str) -> str:
    return f"tool: {name}"

# list_resource_templates() returns:
# [ResourceTemplate(name='tool_detail', uriTemplate='forge://tools/{name}',
#                   mimeType='application/json', ...)]
```

### §5 — ExecutionLog deque + snapshot filtering

```python
# forge_bridge/learning/execution_log.py — additions (D-06..09)
from __future__ import annotations
import collections
import dataclasses
import fnmatch
import os
from datetime import datetime
from typing import Optional

# NEW module-level constant
_DEFAULT_MAX_SNAPSHOT = 10_000

class ExecutionLog:
    def __init__(self, log_path: Path = LOG_PATH, threshold: int = 3) -> None:
        self._path = log_path
        self._threshold = int(os.environ.get("FORGE_PROMOTION_THRESHOLD", threshold))
        self._counters: dict[str, int] = {}
        self._promoted: set[str] = set()  # existing
        self._code_by_hash: dict[str, str] = {}
        self._intent_by_hash: dict[str, Optional[str]] = {}

        # NEW: bounded deque (D-06)
        maxlen = int(os.environ.get("FORGE_EXEC_SNAPSHOT_MAX", _DEFAULT_MAX_SNAPSHOT))
        self._records: collections.deque[ExecutionRecord] = collections.deque(maxlen=maxlen)

        self._replay()  # re-fills deque per D-08
        self._storage_callback = None
        self._storage_callback_is_async = False

    def record(self, code: str, intent: Optional[str] = None) -> bool:
        # ... existing body that writes JSONL + fires callback ...

        # NEW: append to deque AFTER JSONL flush + callback fire (D-06 contract)
        self._records.append(record)

        if self._counters[h] >= self._threshold and h not in self._promoted:
            return True
        return False

    def snapshot(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[datetime] = None,
        promoted_only: bool = False,
        tool: Optional[str] = None,       # fnmatch glob against code_hash-to-tool-name mapping
        code_hash: Optional[str] = None,  # prefix match (D-03 — e.g. "abcd1234")
    ) -> tuple[list[ExecutionRecord], int]:
        """Return (filtered_records, total_before_pagination).

        Reads deque only (D-07). O(n) in deque size; n <= maxlen.
        """
        # Filter in insertion order (deque iterates oldest -> newest).
        # Reverse once so newest-first view is the default (D-03 implies no
        # ?sort param = most-recent-first, matching v1.2 CLI convention).
        it = reversed(self._records)

        filtered: list[ExecutionRecord] = []
        for rec in it:
            if since is not None:
                try:
                    rec_ts = datetime.fromisoformat(rec.timestamp)
                except ValueError:
                    continue
                if rec_ts < since:
                    continue  # NOT break — deque isn't guaranteed-sorted across clock skew
            if promoted_only and rec.code_hash not in self._promoted:
                continue
            if code_hash is not None and not rec.code_hash.startswith(code_hash):
                continue
            if tool is not None:
                # Tool-name join via manifest_service is not available here;
                # this filter applies only when records carry a tool field.
                # For v1.3: fnmatch against rec.code_hash is a no-op unless
                # the caller passes the code_hash as the glob. Recommend: the
                # route handler resolves tool_glob -> code_hash set via
                # ManifestService BEFORE calling snapshot(), then passes a
                # set into a separate 'hash_allowlist' kwarg. Simpler for v1.3:
                # treat 'tool' as filter on a non-existent ExecutionRecord.tool
                # field and plan to revisit when records carry that field
                # (v1.4 — see Open Questions).
                pass

            # D-09: reflect current promoted state (in-memory set mirrors in-place mutation)
            if rec.code_hash in self._promoted and not rec.promoted:
                rec = dataclasses.replace(rec, promoted=True)
            filtered.append(rec)

        total = len(filtered)
        page = filtered[offset : offset + limit]
        return page, total
```

**`tool` filter caveat:** `ExecutionRecord` (frozen dataclass, shipped v1.1.0) does **not** carry a tool name — just `code_hash`, `raw_code`, `intent`, `timestamp`, `promoted`. Two paths for D-03 tool filtering:
1. **Recommended for Phase 9:** Route handler resolves `?tool=synth_*` → set of `code_hash` via `ManifestService`, then calls `snapshot(..., code_hash=<prefix>)` for each match (or extends snapshot to accept a `hashes: set[str]` kwarg). Adds a join step in the handler; keeps `ExecutionRecord` frozen.
2. **Not recommended:** Mutate `ExecutionRecord` to add `tool_name: Optional[str]` — requires v1.1.x schema coordination with projekt-forge per the frozen-dataclass contract in STATE.md. Don't do this in Phase 9.

Planner: decide option (1) as a plan-level task, or defer `tool` filter to v1.4. Either is defensible — recommend option (1) as a single plan task because it uses existing infrastructure and satisfies D-03 promise.

### §6 — Port precheck and uvicorn failure modes

**Why precheck:** `uvicorn.Server.serve()` is an async coroutine that raises `OSError` synchronously on bind failure (confirmed via uvicorn source). Without a precheck, this surfaces as an **unhandled task exception** in `asyncio.create_task(server.serve())`. The task gets garbage-collected with the exception logged via `loop.call_exception_handler` — not visible in your own try/except because the coroutine was fire-and-forget.

**Three viable patterns:**

| Pattern | Behavior | Verdict |
|---------|----------|---------|
| A: Precheck via `socket.bind()` + close | Explicit OSError BEFORE task creation; clean WARNING path | **Recommended — matches v1.2.1 startup_bridge try/except-raise-WARNING shape** |
| B: Just `create_task(server.serve())`, catch in task body | `server.serve()` raises in the task; wrap in try/except; signal via asyncio.Event on success | Works but surfaces the OSError only after task starts; flakier for startup barrier |
| C: `try: config = uvicorn.Config(...); server = uvicorn.Server(config); task = create_task(server.serve()); await asyncio.wait_for(lambda: server.started, 5.0)` | Hope for best; timeout on `server.started` → assume bind failure | Racy, conflates other startup failures with bind failure |

**Recommendation: Pattern A.** The precheck-then-construct-then-task pattern mirrors exactly how `startup_bridge` (v1.2.1) handles `AsyncClient.start() + wait_until_connected()` — try, on Exception log warning, null out the resource, continue. Planner can adopt the code shape shown in §Pattern 1 above verbatim.

### §7 — Typer root refactor (D-10/11)

```python
# forge_bridge/__main__.py (replacing current 4-line file)
from __future__ import annotations
import os
from typing import Optional

import typer

app = typer.Typer(
    name="forge-bridge",
    help="forge-bridge — MCP server + Artist Console.",
    no_args_is_help=False,  # bare invocation must boot MCP, not print help (D-10)
)

# Empty subcommand group for Phase 11 to fill (D-10)
console_app = typer.Typer(
    name="console",
    help="Artist Console CLI (subcommands in Phase 11).",
    no_args_is_help=True,   # `forge-bridge console` alone prints help
)
app.add_typer(console_app, name="console")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    console_port: Optional[int] = typer.Option(
        None,
        "--console-port",
        help="Override console HTTP API port (default 9996, or $FORGE_CONSOLE_PORT).",
        envvar=None,  # we do the env lookup manually below for precedence clarity (D-27)
    ),
) -> None:
    """Bare `forge-bridge` boots the MCP server. `forge-bridge console <cmd>` runs CLI."""
    if ctx.invoked_subcommand is not None:
        return  # subcommand will run; callback returns

    # D-27 precedence: flag > env > default
    if console_port is not None:
        os.environ["FORGE_CONSOLE_PORT"] = str(console_port)
    # else: FORGE_CONSOLE_PORT env (if set) wins; otherwise server defaults to 9996

    from forge_bridge.mcp.server import main as mcp_main
    mcp_main()

if __name__ == "__main__":
    app()
```

**`[VERIFIED: typer==0.24.1]`** — `@app.callback(invoke_without_command=True)` pattern confirmed via `inspect.signature(app.callback)`. The sync body is required (Typer 0.24.1 silently drops `async def` — documented live-test in STACK.md).

**Acceptance tests (D-11):**
```
$ forge-bridge                        # boots MCP on stdio, port 9996 default
$ forge-bridge --console-port 9997    # boots MCP on stdio, console port 9997
$ forge-bridge console --help         # exits 0, prints "Artist Console CLI..."
$ FORGE_CONSOLE_PORT=9995 forge-bridge # boots with 9995 (env path)
```

### §8 — ManifestService singleton shape

```python
# forge_bridge/console/manifest_service.py
from __future__ import annotations
import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass(frozen=True)
class ToolRecord:
    """Canonical tool provenance record shared across all read surfaces.

    Matches the shape the watcher already captures from `.sidecar.json` +
    register_tool kwargs. snake_case end-to-end per D-04.
    """
    name: str                              # e.g. "synth_reconform_timeline", "flame_ping"
    origin: str                            # "builtin" | "synthesized"
    namespace: str                         # "flame" | "forge" | "synth"
    status: str = "active"                 # "active" | "quarantined"
    code_hash: Optional[str] = None        # sha256 — None for builtins
    sha256: Optional[str] = None           # file hash — None for builtins
    synthesized_at: Optional[str] = None   # ISO8601 — None for builtins
    version: Optional[str] = None          # from _meta — None for builtins
    observation_count: Optional[int] = None
    tags: tuple[str, ...] = field(default_factory=tuple)  # frozen → tuple
    registered_at: str = ""                # ISO8601 — set by ManifestService.register()
    sidecar_meta: dict = field(default_factory=dict)      # raw _meta block from sidecar

    def to_dict(self) -> dict:
        return asdict(self)


class ManifestService:
    """Shared singleton owning the in-memory synthesis + builtin tool manifest.

    Writer: the watcher calls register() after register_tool succeeds,
            and remove() when a .py file disappears.
    Readers: ConsoleReadAPI, MCP resources, tool shims — via get_all()/get()/get_manifest().

    Concurrency: asyncio.Lock guards writes. Reads return a shallow copy
    so iteration is stable against concurrent scans.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolRecord] = {}  # name -> record
        self._lock = asyncio.Lock()

    # --- Writer path (watcher) ---

    async def register(self, record: ToolRecord) -> None:
        """Insert or replace a ToolRecord. Called after register_tool() succeeds."""
        async with self._lock:
            stamped = record if record.registered_at else \
                      dataclasses.replace(
                          record,
                          registered_at=datetime.now(timezone.utc).isoformat(),
                      )
            self._tools[record.name] = stamped

    async def remove(self, name: str) -> None:
        async with self._lock:
            self._tools.pop(name, None)

    # --- Reader path (ConsoleReadAPI + resources + tool shims) ---

    def get_all(self) -> list[ToolRecord]:
        """Snapshot — shallow copy of current records, insertion-ordered."""
        return list(self._tools.values())

    def get(self, name: str) -> Optional[ToolRecord]:
        return self._tools.get(name)
```

**Watcher injection signature (Claude's discretion, confirmed):**
```python
# forge_bridge/learning/watcher.py — existing signature:
async def watch_synthesized_tools(
    mcp: "FastMCP",
    synthesized_dir: Path | None = None,
    poll_interval: float = _POLL_INTERVAL,
    tracker: "ProbationTracker | None" = None,
    manifest_service: "ManifestService | None" = None,  # NEW (backward-compatible default)
) -> None:
```

`_scan_once()` calls `await manifest_service.register(ToolRecord(...))` after the existing `register_tool(mcp, fn, ...)` succeeds. If `manifest_service is None` (legacy callers), skip the register call — watcher keeps working without the manifest service.

### §9 — `register_console_resources` signature (finalized)

See the full implementation in §Pattern 3. Canonical signature:

```python
def register_console_resources(
    mcp: FastMCP,
    manifest_service: ManifestService,
    console_read_api: ConsoleReadAPI,
) -> None:
    """Register Phase 9 MCP resources + tool fallback shims.

    Call from _lifespan AFTER ConsoleReadAPI is constructed, BEFORE console_task starts.

    Registers:
      Resources (4 per D-24):
        - forge://manifest/synthesis   → console_read_api.get_manifest()
        - forge://tools                 → console_read_api.get_tools()
        - forge://tools/{name}          → console_read_api.get_tool(name)
        - forge://health                → console_read_api.get_health()
      Tool shims (2 per D-24 / P-03):
        - forge_manifest_read()         → same body as resource synthesis_manifest
        - forge_tools_read(name=None)   → single function, list-or-detail
    """
```

Byte-identity invariant (D-26): both resource and HTTP handler invoke `json.dumps({"data": ..., "meta": ...}, default=str)` on the same `ConsoleReadAPI` return value. Verified by the V-byte-identity test below.

### §10 — `_lifespan` wiring sequence (D-31)

```python
# forge_bridge/mcp/server.py — _lifespan extended
@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    global _server_started, _canonical_execution_log, _canonical_manifest_service
    # 1. Bridge client (existing, graceful-degrading per v1.2.1)
    await startup_bridge()
    _server_started = True

    # 2. Canonical singletons owned by _lifespan (API-04 instance-identity gate)
    from forge_bridge.learning.execution_log import ExecutionLog
    from forge_bridge.console.manifest_service import ManifestService
    execution_log = ExecutionLog()
    manifest_service = ManifestService()
    _canonical_execution_log = execution_log          # stashed for ID comparison
    _canonical_manifest_service = manifest_service

    # 3. Watcher task (with manifest_service injected)
    from forge_bridge.learning.watcher import watch_synthesized_tools
    watcher_task = asyncio.create_task(
        watch_synthesized_tools(mcp_server, manifest_service=manifest_service),
        name="watcher_task",
    )

    # 4. ConsoleReadAPI — consumes the same singletons
    from forge_bridge.console.read_api import ConsoleReadAPI
    from forge_bridge.llm.router import get_router
    console_read_api = ConsoleReadAPI(
        execution_log=execution_log,
        manifest_service=manifest_service,
        llm_router=get_router(),
        flame_bridge_url=os.environ.get("FORGE_BRIDGE_URL_HTTP"),  # optional
        ws_bridge_url=os.environ.get("FORGE_BRIDGE_URL"),
        console_port=int(os.environ.get("FORGE_CONSOLE_PORT", "9996")),
    )

    # 5. Build Starlette app + register MCP resources + tool shims
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.resources import register_console_resources
    console_app = build_console_app(console_read_api)
    register_console_resources(mcp_server, manifest_service, console_read_api)

    # 6. Launch console_task (port-pre-checked, may return None on bind failure)
    host = "127.0.0.1"  # D-28
    port = int(os.environ.get("FORGE_CONSOLE_PORT", "9996"))
    console_task, console_server = await _start_console_task(console_app, host, port)

    try:
        yield
    finally:
        # Teardown reverses construction order
        if console_task is not None:
            console_server.should_exit = True
            try:
                await asyncio.wait_for(console_task, timeout=5.0)
            except asyncio.TimeoutError:
                console_task.cancel()
                try: await console_task
                except (asyncio.CancelledError, Exception): pass
        watcher_task.cancel()
        try: await watcher_task
        except asyncio.CancelledError: pass
        await shutdown_bridge()
        _server_started = False
```

### §11 — CORS middleware config snippet

Already shown in §1. `allow_origins=["http://127.0.0.1:9996", "http://localhost:9996"]` per Claude's-discretion default. Methods limited to `["GET"]` (read-only milestone). Credentials disabled.

### §12 — Ruff lint gate for `print(` ban in `forge_bridge/console/`

```toml
# pyproject.toml additions (D-22)
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
# T201 = `print` found
# T203 = `pprint` found
# Ban everywhere in the package — plans can use `# noqa: T201` in the rare
# test-debug line. Console package must not use noqa.
extend-select = ["T20"]

[tool.ruff.lint.per-file-ignores]
# Tests may use print for pytest captured-stdout assertions.
"tests/**" = ["T20"]
# Standalone CLI/CLI-like scripts that intentionally print to stdout
# (e.g. future forge_bridge/cli/ output in Phase 11) need a manual
# carve-out when they ship. For Phase 9 the only intentional stdout
# writer is the MCP server framing — which does not use print().
```

`[VERIFIED: ruff supports T20 flake8-print rules]`. Alternative if ruff version doesn't support `T20`: use grep-based pre-commit hook targeting `forge_bridge/console/`.

## State of the Art

| Old Approach (pre-Phase-9) | Current Approach | Impact |
|---------------------------|------------------|--------|
| Watcher owns in-memory tool state (`seen: dict[str, str]`, local to coroutine) | `ManifestService` singleton, watcher injects + writes; readers read | Enables MFST-06 cross-repo consumers to read the manifest without scraping the watcher's local dict |
| `ExecutionLog` has no query surface — readers parse JSONL | Bounded `_records` deque + `snapshot(limit, offset, since, promoted_only, code_hash)` | O(1) hot path for Web UI / CLI / MCP; sidesteps P-04 partial-line parsing entirely |
| `forge-bridge` entry point is bare `mcp.run()` | Typer root — bare boot still = MCP, but `console` subcommand group + `--console-port` exist | Phase 11 fills subcommands without needing another pyproject edit |
| Only MCP resource is `forge://llm/health` | + `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health` | Agents get machine-readable snapshots without hitting the MCP tool surface |
| MCP tool shims did not exist | `forge_manifest_read`, `forge_tools_read(name=None)` | Cursor + Gemini CLI (resources-unaware) clients retain full read access (P-03 prevention) |

**Deprecated/outdated guidance inside research files:**
- ARCHITECTURE.md §"Option A" called this a "second uvicorn server in `_lifespan` as a background asyncio task" — ✅ this IS what Phase 9 adopts. Language carries forward.
- ARCHITECTURE.md suggested the MCP resource handler should "re-read `.sidecar.json` files from disk at request time." **Superseded by CONTEXT.md D-25/D-26:** resources read through `ConsoleReadAPI`, which reads through `ManifestService` (which is memory-authoritative during process lifetime). Watcher staleness window (P-05) is managed by the 5-second poll; no disk re-read on the resource path.
- FEATURES.md recommended `/api/v1/executions` — ❌ superseded by CONTEXT.md D-03 which locks `/api/v1/execs` (short form). Plans use `execs`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Runtime | ✓ | (assumed from pyproject requires-python) | — |
| `mcp==1.26.0` | FastMCP, resources, tool shims | ✓ | 1.26.0 | — |
| `uvicorn==0.41.0` | Console HTTP server | ✓ | 0.41.0 | — |
| `starlette==0.52.1` | Route, CORS, JSONResponse | ✓ | 0.52.1 | — |
| `typer==0.24.1` | Typer root refactor | ✓ | 0.24.1 | — |
| `ruff` (dev dep) | D-22 lint gate | ✓ | pinned `>=` via dev extras | — |
| TCP port 9996 | Console bind | Site-dependent | — | **D-29 degradation: log WARNING, skip console_task, MCP continues** |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** Only `:9996` port — D-29 handles it.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` + `pytest-asyncio` (dev extras, `asyncio_mode = "auto"` per pyproject) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing; no changes needed) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/` |
| MCP stdio test vehicle | `tests/test_mcp_server_graceful_degradation.py` pattern (already spins a live MCP server + stdio client — extend it) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | `ConsoleReadAPI` methods return correct data in isolation | unit (mock ManifestService + ExecutionLog) | `pytest tests/test_console_read_api.py -x` | ❌ Wave 0 |
| API-02 | Console HTTP API serves on `:9996` while MCP is stdio | integration (real uvicorn + real FastMCP stdio subprocess) | `pytest tests/test_console_http_transport.py -x` | ❌ Wave 0 |
| API-03 | `/api/v1/tools`, `/execs`, `/manifest`, `/health` return envelope JSON | integration (httpx TestClient + Starlette) | `pytest tests/test_console_routes.py -x` | ❌ Wave 0 |
| API-04 | Instance-identity gate: live `bridge.execute()` appears in `/api/v1/execs` | integration (real MCP server + real callback wire-up) | `pytest tests/test_console_instance_identity.py -x` | ❌ Wave 0 |
| API-05 | `/api/v1/health.services.storage_callback` reflects registered vs absent | unit | `pytest tests/test_console_health.py::test_storage_callback_reflects_registration -x` | ❌ Wave 0 |
| API-06 | Port unavailable → WARNING log + MCP still boots | integration (occupy :9996 first, then launch) | `pytest tests/test_console_port_degradation.py -x` | ❌ Wave 0 |
| MFST-01 | `ManifestService.register()` writes are visible to `get_all()` | unit (asyncio.Lock concurrent writers) | `pytest tests/test_manifest_service.py -x` | ❌ Wave 0 |
| MFST-02 | `forge://manifest/synthesis` returns manifest JSON | integration (real MCP client over stdio, `resources/read`) | `pytest tests/test_console_mcp_resources.py::test_manifest_resource -x` | ❌ Wave 0 |
| MFST-03 | `forge_manifest_read` tool returns same payload as resource (byte-identical) | integration (real MCP client, `tools/call`) | `pytest tests/test_console_mcp_resources.py::test_manifest_tool_shim_byte_identical -x` | ❌ Wave 0 |
| MFST-06 | `/api/v1/manifest` == `forge://manifest/synthesis` == `forge_manifest_read` bytes | integration (byte-diff assertion across all three surfaces) | `pytest tests/test_console_mcp_resources.py::test_manifest_cross_surface_byte_identity -x` | ❌ Wave 0 |
| TOOLS-04 | `forge://tools`, `forge://tools/{name}`, `forge_tools_read(name=None)` all work | integration | `pytest tests/test_console_mcp_resources.py::test_tools_resources_and_shim -x` | ❌ Wave 0 |
| EXECS-04 | `/api/v1/execs` and `ConsoleReadAPI.get_executions()` return identical records for same state | unit (no HTTP indirection in the CLI contract) | `pytest tests/test_console_read_api.py::test_execs_shared_read_path -x` | ❌ Wave 0 |
| **SC#1** | MCP stdio `tools/list` succeeds while `:9996` serves concurrent GET traffic | integration (real subprocess MCP + concurrent httpx GET on `:9996`) | `pytest tests/test_console_stdio_cleanliness.py -x` | ❌ Wave 0 (CRITICAL P-01 test) |
| **SC#3 bridge.execute→/execs** | Live `bridge.execute()` record visible via `/api/v1/execs` immediately | integration | `pytest tests/test_console_instance_identity.py::test_execute_appears_in_execs -x` | ❌ Wave 0 |
| **SC#4 port unavailable** | Occupied `:9996` → WARNING + MCP boots + `tools/list` works | integration | `pytest tests/test_console_port_degradation.py -x` | ❌ Wave 0 |
| **SC#5 stdio unchanged** | Existing integration tests pass unchanged (no `--http`) | regression | `pytest tests/test_mcp_server_graceful_degradation.py tests/test_e2e.py -x` | ✅ (existing) |
| **D-22 lint gate** | `ruff check forge_bridge/console/` fails on `print(` | lint (not pytest) | `ruff check forge_bridge/console/` | ❌ Wave 0 (config addition) |
| **Typer root D-10/11** | Bare `forge-bridge` boots MCP; `forge-bridge console --help` exits 0 | integration (subprocess) | `pytest tests/test_typer_entrypoint.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_console_*.py -x -q` (~10-20 tests, fast)
- **Per wave merge:** `pytest tests/` (full suite including all v1.0-v1.2 baselines)
- **Phase gate (before `/gsd-verify-work`):** Full suite green + SC#1 manual UAT (run MCP client against stdio while curling `:9996`) + SC#2/3 manual MCP-client UAT

### Wave 0 Gaps

- [ ] `tests/test_console_read_api.py` — unit tests for `ConsoleReadAPI.get_tools/get_tool/get_executions/get_manifest/get_health` against mocked dependencies
- [ ] `tests/test_manifest_service.py` — unit tests for `ManifestService.register/remove/get_all/get` including asyncio.Lock concurrency
- [ ] `tests/test_console_http_transport.py` — Starlette TestClient + `_start_console_task` helper under pytest-asyncio
- [ ] `tests/test_console_routes.py` — per-route envelope shape, pagination clamping (D-05), CORS preflight
- [ ] `tests/test_console_health.py` — D-14 shape assertion, D-15 aggregation, D-17 timeout bounds
- [ ] `tests/test_console_instance_identity.py` — real `_lifespan` + real `bridge.execute()` + `/api/v1/execs` round-trip (API-04 gate)
- [ ] `tests/test_console_port_degradation.py` — occupy :9996 via secondary socket before test, assert WARNING logged + MCP boots (API-06)
- [ ] `tests/test_console_mcp_resources.py` — **spawn a real MCP server subprocess and connect via stdio client**; exercise `resources/list`, `resources/read forge://...`, `tools/call forge_manifest_read`, assert byte-identity (D-26). Mirror the Phase 07.1 UAT evidence protocol.
- [ ] `tests/test_console_stdio_cleanliness.py` — **critical P-01 test:** spawn MCP subprocess in stdio, connect, issue 100 concurrent httpx GETs to `:9996`, then issue MCP `tools/list`, assert response framed correctly
- [ ] `tests/test_typer_entrypoint.py` — subprocess invocation of `forge-bridge` (bare), `forge-bridge --console-port 9997`, `forge-bridge console --help`, assert exit codes + behavior
- [ ] `pyproject.toml` — add `[tool.ruff.lint] extend-select = ["T20"]` and per-file carve-outs (D-22)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Locked non-goal: localhost-only, same posture as `:9999`. Any auth ships with a dedicated milestone. |
| V3 Session Management | no | No sessions — stateless GETs on localhost. |
| V4 Access Control | partial | CORS allow-list limited to localhost origins; bind to `127.0.0.1` only (D-28). |
| V5 Input Validation | yes | Pagination clamping (D-05); `since` parses as ISO8601 or 400; `code_hash` is whitelist-regex-matched `[a-f0-9]+`; `tool` glob limited to `[A-Za-z0-9_*?-]+` characters. |
| V6 Cryptography | no | No cryptographic primitives introduced. `code_hash` is an integrity identifier, not a signature — already shipped. |
| V7 Error Handling | yes | `str(exc)` ban carries forward from Phase 8 LRN-05-follow-on — use `type(exc).__name__` in all error paths (SQLAlchemy/httpx exception chains leak URLs with credentials). |

### Known Threat Patterns for Phase 9

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stdout corruption via uvicorn log leak | DoS (MCP client disconnect) | `log_config=STDERR_ONLY_LOGGING_CONFIG` + `access_log=False` + ruff `print(` ban (D-19..22) |
| Tool name injection via `forge_tools_read(name=<malicious>)` | Tampering | `name` is passed directly to `ManifestService.get(name)` which is a dict lookup — no SQL, no filesystem, no exec. Already safe. |
| MCP resource handler crashes leak stack trace over MCP wire | Information disclosure | All resource/tool bodies wrap exceptions into `{error: {code, message}}` shapes — no `str(exc)`. |
| Cross-origin fetch from browser to `:9996` | Access control | CORS allow-list limited to `127.0.0.1:9996` + `localhost:9996`; GET-only; no credentials. |
| JSON deserialization attack on `.sidecar.json` | Tampering | Already covered by v1.2 PROV-03 sanitization boundary (`_sanitize_tag`, `apply_size_budget`); Phase 9 READS from ManifestService which is populated by the watcher after that sanitization. |
| Port-unavailable misleading error | DoS + debug noise | D-29 — WARNING log with the real OSError message; MCP continues. No exception propagated to MCP wire. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `uvicorn.Server.started: bool` is a stable public attribute across 0.41.x | §Pattern 1 | If removed in a patch release, startup barrier reads False forever → logged WARNING but serve() still runs. Low risk; mitigated by task.done() check. |
| A2 | `fnmatch` matches shell-glob D-03 promises (`synth_*`) identically to consumer expectation | §5 | Different from shell-glob in edge cases (e.g. `[abc]` character classes). Documented in route-handler docstring; tested. |
| A3 | `ruff` supports `T20` (flake8-print) rules via `extend-select` | §12 | If not, fall back to a 5-line pre-commit grep gate — still satisfies D-22. |
| A4 | `datetime.fromisoformat()` parses the timestamps `ExecutionLog.record()` writes | §5 | v1.0+ uses `datetime.now(timezone.utc).isoformat()` — confirmed round-trippable by Python stdlib since 3.11. For 3.10 support, fall back to `dateutil.isoparse`. Planner verifies runtime. |
| A5 | FastMCP 1.26.0 accepts `@mcp.resource` / `@mcp.tool` registration after server object is constructed and `register_builtins(mcp)` was called | §Pattern 3, §10 | If registration is closed after `mcp.run()`, Phase 9 breaks. Mitigate by registering DURING `_lifespan` setup, BEFORE `yield` — FastMCP's own built-in resource registration is at module import. Pattern works because `_lifespan` is called before the server handles any wire traffic. Verifiable via unit test. |

**Total `[ASSUMED]` claims in this research: 5.** Everything else is `[VERIFIED]` via live Python or `[CITED]` from the CONTEXT.md / STACK.md / ARCHITECTURE.md stack that the user already reviewed.

## Open Questions (RESOLVED)

1. **Tool-name filter on `/api/v1/execs?tool=synth_*` — join layer?**
   - What we know: `ExecutionRecord` (frozen, v1.1) has no `tool_name` field. `ManifestService` maps name→hash via `ToolRecord.code_hash`.
   - What's unclear: whether to add the join in the route handler (resolve glob → set of hashes → pass to `snapshot(hashes=...)`) or defer the tool filter to v1.4.
   - Recommendation: **add the join in the route handler for Phase 9.** Single task, ~15 lines, satisfies D-03 end-to-end. Alternative: document it as "implemented in Phase 10 when Web UI needs it" and ship Phase 9 without. Planner decides.
   - **RESOLVED:** Defer to v1.4. The /api/v1/execs route handler REJECTS `?tool=...` with a 400 `{"error": {"code": "not_implemented", "message": "tool filter reserved for v1.4"}}` response in v1.3. Rationale: the executor is still `ExecutionRecord` (no `tool_name` field); the glob-join requires either a `ManifestService`-owned `code_hash`→name reverse map (with careful concurrency semantics when the watcher is actively mutating the manifest) or an additive field on `ExecutionRecord`. Both changes are larger than D-12's "decide now" threshold and justify deferral to v1.4 where streaming push + richer filters ship together. Phase 10 Web UI therefore will NOT ship a `tool:` token in the DF-1 query parser for v1.3 — Phase 10 CONTEXT.md `<deferred>` notes must record this alignment. Corresponding planner edits: (a) `ExecutionLog.snapshot()` and `ConsoleReadAPI.get_executions()` do NOT accept a `tool` kwarg (Plan 09-02); (b) `execs_handler` early-returns 400 `not_implemented` when `request.query_params.get("tool")` is truthy (Plan 09-03 Task 1); (c) a new test `test_execs_tool_filter_returns_400_not_implemented` pins the contract (Plan 09-03 Task 1).

2. **`/api/v1/manifest` — full payload vs pagination?**
   - What we know: manifest is typically 10-100 tools for a single project; no pagination requirement in REQUIREMENTS.md.
   - What's unclear: whether `?limit=50` applies to `/api/v1/manifest` too, for consistency with `/api/v1/tools` and `/api/v1/execs`.
   - Recommendation: return the full manifest with `meta: {total: N}` and no limit clamping. If a studio ever has >1000 tools, revisit.
   - **RESOLVED:** Return the full manifest with `meta: {total: N}` and NO limit clamping in v1.3. Revisit when a studio has >1000 tools (no REQ-ID gate ships before then).

3. **`/api/v1/tools` ordering contract?**
   - What we know: insertion order is what `ManifestService.get_all()` returns.
   - What's unclear: whether builtins or synthesized tools appear first; whether there's a canonical `?sort=` contract.
   - Recommendation: insertion order (builtins registered by `register_builtins` at import, synthesized by watcher during `_lifespan`). Document. Sort ordering in the HTTP layer is a Phase 10 Web-UI concern.
   - **RESOLVED:** Insertion order — builtins (registered by `register_builtins` at import) precede synthesized tools (registered by the watcher during `_lifespan`). No `?sort=` parameter in v1.3. Sort ordering in the HTTP layer is a Phase 10 Web-UI concern.

4. **`flame_bridge` health check shape — what URL?**
   - What we know: The existing WebSocket client connects to `ws://127.0.0.1:9998`; the Flame HTTP bridge is `http://127.0.0.1:9999/exec`.
   - What's unclear: Does `/api/v1/health.services.flame_bridge` probe :9999 or :9998? D-14 shows `url: "http://...:9999"` which is the Flame HTTP bridge. Confirmed: :9999 HTTP.
   - Recommendation: Two separate health fields: `flame_bridge` (HTTP :9999) and `ws_server` (WS :9998). D-14 already separates these — so this is resolved.
   - **RESOLVED:** Two separate health fields: `flame_bridge` probes `http://127.0.0.1:9999` (HTTP); `ws_server` probes `ws://127.0.0.1:9998` (WebSocket TCP reachability). D-14 already enshrines this split.

5. **`forge://llm/health` resource relationship to `forge://health`?**
   - What we know: `forge://llm/health` exists (v1.0, in `llm/health.py`); `forge://health` is new (Phase 9).
   - What's unclear: does Phase 9 subsume `forge://llm/health`? Or coexist?
   - Recommendation: **coexist.** `forge://llm/health` stays — it's a narrower, LLM-only view for agents that only want that slice. `forge://health` is the full D-14 body. Both pass through `ConsoleReadAPI.get_health()` internally to maintain D-25.
   - **RESOLVED:** Coexist. `forge://llm/health` stays as the narrower LLM-only view; `forge://health` ships as the full D-14 body. Both pass through `ConsoleReadAPI.get_health()` internally (D-25).

## Risks and Open Questions for the Planner (RESOLVED)

1. **Phase 9 scope is tight but >1 plan.** Recommended split: (a) `09-01-typer-entrypoint` (Typer root + empty console subcommand + ruff gate — lands first, small diff per D-11); (b) `09-02-console-package` (ManifestService, ExecutionLog deque/snapshot, watcher injection); (c) `09-03-read-api-and-wiring` (ConsoleReadAPI, Starlette app, `_lifespan` extension, resources + tool shims, all integration tests). Planner may merge (b)+(c) if wave sizing fits.
   - **RESOLVED:** Planner split Phase 9 into THREE plans exactly as recommended (09-01 / 09-02 / 09-03) with waves 1 / 2 / 3. Plan 09-03 carries an explicit context checkpoint marker between Task 3 and Task 4 (W-04) so the executor may split context windows if approaching 55%+.
2. **Test fixture for "real MCP over stdio + real uvicorn on :9996 concurrently"** is the critical P-01 test (SC#1). Planner should budget a dedicated test-fixture task that spawns the MCP server in a subprocess, establishes a stdio client, and opens httpx-based concurrent traffic on `:9996`. This is the Phase 07.1 UAT evidence pattern applied here.
   - **RESOLVED:** Plan 09-03 Task 6 creates `tests/test_console_stdio_cleanliness.py` as a dedicated P-01 fixture — real subprocess + real uvicorn + 100 concurrent GETs + Content-Length frame parsing. `pytest-timeout>=2.2.0` added to dev extras (I-01) so `@pytest.mark.timeout(60)` is enforced.
3. **`ruff` version in `[tool.ruff.lint] extend-select = ["T20"]`** — if the pinned dev-extras ruff is too old for the `lint` subsection, fall back to top-level `[tool.ruff] select = [...]`. Planner verifies on-commit.
   - **RESOLVED:** Plan 09-01 Task 2's verify block runs `ruff check forge_bridge/` against the live tree — if the config section is wrong ruff errors immediately and the commit fails. No pre-planning fallback; the commit-time check is the gate.
4. **`register_console_resources` call-order** must be AFTER `register_builtins(mcp)` runs at import but BEFORE `_lifespan` yields. If a resource name collides with an existing builtin (unlikely — `forge://llm/health` is the only existing resource and names are distinct), FastMCP raises on registration. Add an error message that points to `register_builtins` vs `register_console_resources` as the two registration sites.
   - **RESOLVED:** Plan 09-03 Task 4 locks `register_console_resources(mcp_server, manifest_service, console_read_api)` as D-31 Step 5 (after Step 4 builds `ConsoleReadAPI`, before Step 6 launches the uvicorn task). The four resource URIs (`forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health`) do not collide with `forge://llm/health`. If FastMCP's registration error surfaces at boot, the resulting traceback already names both sites — no extra error wrapping needed.
5. **ExecutionLog.snapshot's `tool` kwarg deferral** — see Open Question #1. Either implement the join in Phase 9 (15 LoC in handler) or defer — mark explicitly in plan so Phase 10 doesn't assume the query param works.
   - **RESOLVED:** Defer to v1.4 per Open Question #1 RESOLVED marker. `ExecutionLog.snapshot()` and `ConsoleReadAPI.get_executions()` do NOT accept a `tool` kwarg. `execs_handler` rejects `?tool=...` with 400 `not_implemented`. Phase 10 CONTEXT.md `<deferred>` must record that the DF-1 query parser omits the `tool:` token in v1.3.

## Sources

### Primary (HIGH confidence — verified live)
- Direct package inspection (`python3 -c "..."`) on 2026-04-22:
  - `mcp==1.26.0` — `FastMCP.resource` signature + URI template extraction
  - `starlette==0.52.1` — `Starlette(routes=, middleware=)`, `CORSMiddleware(allow_origins=, allow_methods=, ...)`, `Route(path, endpoint, methods=)`
  - `uvicorn==0.41.0` — `Config(log_config=, access_log=, ...)`, `Server.__init__`, `Server.started: bool`, `Server.should_exit` teardown flag
  - `typer==0.24.1` — `@app.callback(invoke_without_command=True, ...)` signature
- Direct source reads of the working tree:
  - `forge_bridge/mcp/server.py` — existing `_lifespan` shape, `startup_bridge` graceful degradation contract
  - `forge_bridge/learning/execution_log.py` — `record()`, `_replay()`, `ExecutionRecord` frozen dataclass, existing `_counters/_promoted/_code_by_hash/_intent_by_hash`
  - `forge_bridge/learning/watcher.py` — `watch_synthesized_tools` signature, `_scan_once` registration flow, `_read_sidecar` sanitization boundary
  - `forge_bridge/learning/sanitize.py` (via reference) — `_sanitize_tag`, `apply_size_budget` (already applied at watcher read-time; Phase 9 doesn't re-sanitize)
  - `forge_bridge/llm/health.py` — canonical `register_llm_resources` pattern to mirror
  - `forge_bridge/__init__.py` — current `__all__` at 16 symbols; minor version-bump ceremony applies if `ManifestService`/`ToolRecord`/`ConsoleReadAPI` join
  - `forge_bridge/__main__.py` — 4-line current file, straightforward replacement target
  - `pyproject.toml` — ruff configured, no jinja2, existing `[project.scripts]` entry
- `.planning/phases/09-read-api-foundation/09-CONTEXT.md` — D-01..D-31 decisions verbatim
- `.planning/REQUIREMENTS.md` §"API" — API-01..06 + MFST-01/02/03/06, TOOLS-04, EXECS-04
- `.planning/ROADMAP.md` §"Phase 9" — five success criteria

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`, `.planning/research/STACK.md`, `.planning/research/FEATURES.md` — v1.3 milestone research synthesis, HIGH-confidence per the synthesis document itself; consumed as CITED prior art (all findings carried forward without reinterpretation)
- `.planning/milestones/v1.2-ROADMAP.md` §"Phase 07.1" — graceful-degradation precedent for port bind failure (D-29)
- `.planning/phases/v1.2-phases/08-sql-persistence-protocol/08-CONTEXT.md` (referenced in CONTEXT.md) — LRN-05 instance-identity-gate origin

### Tertiary (no new WebSearch; all findings derived from existing HIGH-confidence sources)
- None — Phase 9 research does not require new web fetches. Every API shape, version, and behavior was confirmed live against installed packages.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version pinned and live-verified on 2026-04-22
- Architecture: HIGH — all patterns traceable to existing code (`_lifespan`, `startup_bridge`, `register_llm_resources`, watcher, ExecutionLog) plus verified uvicorn/Starlette/FastMCP/Typer APIs
- Pitfalls: HIGH — SUMMARY/PITFALLS.md carry forward, plus five new Phase-9-specific pitfalls identified from the code-example exercise above
- CONTEXT.md alignment: HIGH — every D-XX decision maps to at least one code snippet or validation row

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable foundation libraries; revisit only if `mcp[cli]` major-bumps or uvicorn 1.0 ships)

---

## RESEARCH COMPLETE

**Phase:** 9 — Read API Foundation
**Confidence:** HIGH

### Key Findings
- All 31 locked CONTEXT.md decisions map to verified code patterns — zero decisions need reopening.
- The only new pip dependency in Phase 9 is **zero** (jinja2 lands in Phase 10).
- The embedded-uvicorn pattern is cleanly supported by stdlib socket precheck + `uvicorn.Server.started` startup barrier — mirrors the v1.2.1 `startup_bridge` graceful-degradation shape exactly (API-06).
- MCP URI templates (`forge://tools/{name}`) extract path params via kwarg-match on `mcp==1.26.0` — live-verified.
- Stdio safety (P-01) requires custom `LOGGING_CONFIG` dict routing all uvicorn loggers to `ext://sys.stderr` + `access_log=False` — default uvicorn config writes access to stdout and would corrupt the MCP wire.
- `ExecutionLog._records` deque + `snapshot()` sidesteps P-04 (JSONL partial-line parse) entirely because the read path never touches the file.

### File Created
`/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/phases/09-read-api-foundation/09-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Every version live-verified against installed packages 2026-04-22 |
| Architecture | HIGH | Every pattern has a concrete code snippet referencing existing code or verified APIs |
| Pitfalls | HIGH | 5 new pitfalls beyond SUMMARY.md/PITFALLS.md carry-forward, each tied to a Phase 9 code path |
| Validation | HIGH | Every REQ-ID has a named test file + command; SC#1..5 each have a dedicated integration test |

### Open Questions (RESOLVED)
1. `/api/v1/execs?tool=synth_*` — implement the manifest-join in the route handler (15 LoC) or defer to v1.4? Recommend: implement.
   - **RESOLVED:** Defer to v1.4. `execs_handler` rejects with 400 `not_implemented`; `snapshot()` + `get_executions()` do not accept the kwarg. See `## Open Questions (RESOLVED)` Q#1 above for the full rationale.
2. Tool-shim collision — verify `register_console_resources` post-`register_builtins` works (live-verifiable via unit test; assumed A5).
   - **RESOLVED:** Plan 09-03 Task 3 registers `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health` — none collide with the existing `forge://llm/health`. Registration happens inside `_lifespan` step 5 (Plan 09-03 Task 4), AFTER `register_builtins(mcp)` has run at import. FastMCP 1.26.0 accepts post-construction registration (assumption A5 confirmed in RESEARCH.md §Pattern 3).
3. Phase 9 plan split — recommend 2-3 plans: Typer-root-refactor (small), console-package-core (ManifestService + ExecutionLog deque), read-api-and-wiring (ConsoleReadAPI + Starlette + `_lifespan` + resources). Planner finalizes.
   - **RESOLVED:** Planner split Phase 9 into three plans exactly as recommended: 09-01 Typer root + ruff gate (Wave 1); 09-02 console package core + ExecutionLog deque + watcher injection (Wave 2); 09-03 read-API surface + `_lifespan` wiring + all integration tests (Wave 3). Plan 09-03 carries a context checkpoint marker between Task 3 and Task 4 for optional context-window split.

### Ready for Planning
Research complete. Planner can now create PLAN.md files for Phase 9 subplans.
