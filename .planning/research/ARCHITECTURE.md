# Architecture Patterns — v1.3 Artist Console

**Domain:** Web UI + CLI console + MCP resource layer on an existing FastMCP + learning pipeline
**Research mode:** Architecture (subsequent milestone, v1.3 scope)
**Researched:** 2026-04-22
**Overall confidence:** HIGH — all integration points derived from direct source reads of the current codebase plus verified FastMCP SDK documentation.

---

## System Topology (As-is, post-v1.3.0)

Before designing additions, the load-bearing topology that v1.3 must not break:

```
[Flame process, port 9999]
    forge_bridge.py HTTP hook — accepts POST /exec, executes Python on main thread

[MCP server process — python -m forge_bridge]
    forge_bridge/mcp/server.py   — FastMCP("forge_bridge"), _lifespan, startup_bridge/shutdown_bridge
    forge_bridge/mcp/registry.py — register_tool / register_tools / register_builtins
    forge_bridge/bridge.py       — HTTP client to :9999 — set_execution_callback hook
    forge_bridge/learning/
        execution_log.py   — JSONL append, in-memory counters, storage callback dispatch
        watcher.py         — asyncio polling loop, sidecar read, register_tool on new files
        manifest.py        — .manifest.json origin validation
        synthesizer.py     — LLM-driven synthesis, .sidecar.json write
        probation.py       — success/failure counters, quarantine (file move + MCP removal)
        storage.py         — StoragePersistence Protocol (docs only)
    forge_bridge/llm/
        router.py          — LLMRouter — async acomplete/ahealth_check
        health.py          — register_llm_resources(mcp) — forge://llm/health resource
    forge_bridge/server/   — standalone WebSocket server (port 9998)

[projekt-forge process — separate]
    Consumes forge-bridge as pip dep
    Registers storage callback → SQL mirror (execution_log PG table)
    Registers pre_synthesis_hook
```

Key runtime facts for v1.3 integration design:
- The MCP process is a single asyncio event loop managed by FastMCP's `mcp.run()`.
- `_lifespan` already owns startup/shutdown for the WS client and watcher task. New services attach here.
- `bridge.py` has a module-level `_on_execution_callback` (single slot). Already wired to `ExecutionLog.record()` in projekt-forge's `init_learning_pipeline`.
- `ExecutionLog` holds in-memory counters (`_counters`, `_promoted`, `_code_by_hash`, `_intent_by_hash`) rebuilt from JSONL on startup. This is the live read surface for execution state — no DB query needed.
- The watcher's `seen: dict[str, str]` (stem → sha256) is the live in-memory manifest of registered synthesized tools. It is local to `watch_synthesized_tools()` and not externally accessible today.
- `.manifest.json` on disk is the authoritative security check for file origin. `.sidecar.json` carries provenance per tool.

---

## What v1.3 Must Add

From PROJECT.md, four new surfaces:

1. **Console HTTP API + Web UI on a new port (`:9996`)** — served from the MCP server process via FastMCP's `@mcp.custom_route()` + Starlette `StaticFiles` mount.
2. **CLI companion (`forge-bridge console <subcommand>`)** — thin client that calls the `:9996` API using `httpx`.
3. **Synthesis manifest as MCP resource** — `forge://manifest/synthesis` — authoritative in-memory manifest owned by a new `ManifestService`, read via MCP resource and HTTP API endpoint.
4. **LLM chat via console** — chat UI calls a `:9996` endpoint → `LLMRouter.acomplete()` → response; system prompt includes live read-side context.

Three architectural questions the roadmapper must answer before planning:
- **Q1:** Where does the authoritative in-memory manifest live — in the watcher's `seen` dict (extended to be injectable) or in a new `ManifestService`?
- **Q2:** How does JSONL execution history reach the console — snapshot read, paginated query layer, or streaming tail?
- **Q3:** Does the LLM chat endpoint need SSE streaming or is request-response sufficient for v1.3?

These are answered below.

---

## Recommended Architecture

### Q1 Answer: ManifestService as a shared singleton

The watcher's `seen: dict[str, str]` (stem → sha256) is a dict local to an async task, invisible outside `watch_synthesized_tools()`. Extending it with an accessor would require threading state out of the coroutine, which is fragile and inverts the ownership model.

**Recommended pattern:** introduce `ManifestService` — a shared singleton that the watcher writes to and the console API + MCP resource both read from.

```
ManifestService (new)
  _tools: dict[str, ToolRecord]   — stem → {name, sha256, sidecar_meta, registered_at, status}
  _lock: asyncio.Lock             — write lock (watcher is the only writer)

  write path:  watcher._scan_once calls manifest_service.register(stem, record) / manifest_service.remove(stem)
  read path:   console API handler calls manifest_service.snapshot() → list[ToolRecord]
               MCP resource handler calls manifest_service.snapshot() → serialized JSON
```

`ToolRecord` is a plain dataclass:
```python
@dataclass
class ToolRecord:
    name: str           # stem (tool name)
    sha256: str         # file hash
    registered_at: str  # ISO timestamp
    status: str         # "active" | "quarantined"
    sidecar_meta: dict  # provenance fields from .sidecar.json (already sanitized)
    observation_count: int  # from ExecutionLog.get_count(sha256) at registration time
```

`ManifestService` is instantiated once in `_lifespan`, injected into `watch_synthesized_tools()` and into the console router. MCP resource handler reads `manifest_service.snapshot()`.

**Consistency invariant maintained by:**
- Single writer (watcher) + asyncio.Lock on writes.
- Snapshot read is a shallow copy — callers get a stable list not affected by subsequent watcher scans.
- Disk `.sidecar.json` is the authority for provenance; watcher reads it at registration time and caches in `ToolRecord.sidecar_meta`. If the sidecar changes on disk, the watcher's hash check catches it on next poll (file content change changes sha256).
- MCP resource `forge://manifest/synthesis` reads the same `ManifestService.snapshot()`. It is always consistent with what the MCP server has actually registered — it is not a separate data structure.

### Q2 Answer: Snapshot read for execution history, paginated in-memory query layer

The `ExecutionLog` instance already holds the full in-memory execution state (`_counters`, `_code_by_hash`, `_intent_by_hash`, `_promoted`). This is the canonical read surface — JSONL is the append-only source of truth; the in-memory state is its materialized view, rebuilt on every startup.

**Recommended approach:** add an `ExecutionLog.snapshot(limit, offset)` method that returns a list of `ExecutionRecord`-like dicts from in-memory state. No JSONL file reads at query time. No streaming tails for v1.3.

Rationale:
- JSONL tail streaming adds a file-descriptor + async generator with backpressure concerns across the HTTP boundary, and the `ExecutionLog` model already gives us the pageable in-memory state without it.
- The `_code_by_hash` dict keys insertion order (Python 3.7+ dicts are ordered) — iteration order approximates chronological order for reasonable log sizes (hundreds to low thousands of entries).
- If the log grows to tens of thousands of entries, the `snapshot()` call will be slow. For v1.3 scope (single-project, single artist) this is not a concern. A SQL-backed query layer (optional `StoragePersistence` mirror) is the v1.4+ path.

**SSE streaming (deferred):** PROJECT.md marks real-time streaming as "open for roadmapper to decide." Defer to post-v1.3. The console HTTP API and CLI are poll-only for this milestone.

### Q3 Answer: Request-response for LLM chat in v1.3

`LLMRouter.acomplete()` is a coroutine that resolves when the model finishes. The Starlette `custom_route` handler can `await` it and return a `JSONResponse`. This is the lowest-friction path and matches the existing `forge://llm/health` pattern.

The Ollama backend supports streaming completions (SSE tokens) but `LLMRouter._async_local()` collects the full response before returning. Streaming would require refactoring `LLMRouter` to expose an `astream()` path and the console endpoint to emit SSE. Defer to post-v1.3.

---

## Component Map: New vs Modified vs Untouched

### New modules

| Module | Purpose |
|--------|---------|
| `forge_bridge/console/__init__.py` | Package init |
| `forge_bridge/console/manifest_service.py` | `ManifestService` singleton + `ToolRecord` dataclass |
| `forge_bridge/console/read_api.py` | Starlette route handlers for the console HTTP API (`:9996` endpoints) |
| `forge_bridge/console/chat.py` | LLM chat endpoint handler — receives prompt, builds context from `ManifestService` + `ExecutionLog`, calls `LLMRouter.acomplete()` |
| `forge_bridge/console/static/` | Web UI static assets (HTML/CSS/JS) — served via `StaticFiles` mount |

### Modified modules

| Module | Change | Impact |
|--------|--------|--------|
| `forge_bridge/mcp/server.py` | `_lifespan`: instantiate `ManifestService`; register console routes on `mcp` via `@mcp.custom_route()`; start console HTTP server on `:9996` | Only file that coordinates new services with the MCP process lifecycle |
| `forge_bridge/learning/watcher.py` | `watch_synthesized_tools()` accepts optional `manifest_service: ManifestService | None = None`; `_scan_once` calls `manifest_service.register()` / `manifest_service.remove()` when provided | Backward-compatible — None default preserves existing callers |
| `forge_bridge/llm/health.py` | Register `forge://manifest/synthesis` resource alongside `forge://llm/health` — OR move resource registration to a new `forge_bridge/console/resources.py` (see note below) | Minimal change either way |
| `forge_bridge/__init__.py` | Re-export `ManifestService`, `ToolRecord`, and console entrypoints as `__all__` grows 16 → ~18-19 | Minor version bump ceremony applies |
| `forge_bridge/learning/execution_log.py` | Add `snapshot(limit: int = 100, offset: int = 0) -> list[dict]` method | Additive; no signature changes on existing methods |

Note on resource registration: The cleanest placement for `forge://manifest/synthesis` is a new `forge_bridge/console/resources.py` with a `register_console_resources(mcp, manifest_service)` function, mirroring `health.py`'s `register_llm_resources(mcp)` pattern. This keeps the console package self-contained and the MCP server's `register_builtins` / `_lifespan` calls minimal.

### Untouched modules

| Module | Why untouched |
|--------|--------------|
| `forge_bridge/bridge.py` | No change — `set_execution_callback` already wired; callback slot is single-use |
| `forge_bridge/learning/execution_log.py` (most of it) | `record()`, `mark_promoted()`, `_replay()`, `set_storage_callback()` unchanged |
| `forge_bridge/learning/synthesizer.py` | No change — synthesis pipeline is not in scope |
| `forge_bridge/learning/manifest.py` | No change — `ManifestService` uses its own in-memory state; the `.manifest.json` file-origin security check is still called by the watcher |
| `forge_bridge/learning/probation.py` | No change — quarantine status is reflected in `ToolRecord.status` but `ProbationTracker` itself is untouched |
| `forge_bridge/learning/storage.py` | No change — `StoragePersistence` Protocol is stable |
| `forge_bridge/mcp/registry.py` | No change — registration API is stable |
| `forge_bridge/server/` | Standalone WS server — not touched by console |
| `forge_bridge/llm/router.py` | No change — `acomplete()` / `ahealth_check()` called as-is |
| `forge_bridge/flame_hooks/` | No change |

---

## Console HTTP API Endpoint Design

Served on `:9996` inside the MCP server process. All endpoints are read-only. No auth (localhost-bound, same posture as `:9999`).

FastMCP's `@mcp.custom_route()` decorator (verified in SDK docs) adds Starlette routes to the ASGI app that FastMCP runs when `transport="streamable_http"` or similar. For `:9996` as a *separate* port from the MCP transport port, the recommended approach is:

**Option A (recommended): Start a second uvicorn server in `_lifespan` as a background asyncio task.**

`mcp.run()` in stdio mode does not bind an HTTP port. The console needs `:9996` regardless of MCP transport mode. Launching a minimal Starlette/uvicorn app in a background `asyncio.create_task()` within `_lifespan` is the same pattern as the watcher task today. This keeps the console decoupled from MCP transport decisions.

```python
# _lifespan pseudocode
async with _lifespan(mcp_server):
    ...
    console_app = build_console_app(manifest_service, execution_log, llm_router)
    console_task = asyncio.create_task(
        serve_uvicorn(console_app, port=9996)
    )
    ...
    # on exit: console_task.cancel()
```

`build_console_app()` returns a Starlette ASGI application with routes for the API and static files. `serve_uvicorn()` uses `uvicorn.Server` with a programmatic `Config` object (this is the documented pattern for embedding uvicorn inside an asyncio task).

**Option B: Use `@mcp.custom_route()` and rely on FastMCP's HTTP transport.**

This only works if the MCP server is run with `--http` transport — it adds routes to the same ASGI app. The console would share the MCP port, not get its own `:9996`. This violates the PROJECT.md scope decision ("new port e.g. `:9996`"). Rejected.

### Endpoint surface

```
GET  /api/v1/manifest          → list of ToolRecord (from ManifestService.snapshot())
GET  /api/v1/manifest/{name}   → single ToolRecord by tool name
GET  /api/v1/executions        → paginated execution list (?limit=&offset=) from ExecutionLog.snapshot()
GET  /api/v1/executions/{hash} → single execution record by code_hash
GET  /api/v1/health            → {bridge_reachable, llm_health, tool_count, log_entry_count}
POST /api/v1/chat              → {prompt: str, context: bool} → {reply: str}
GET  /                         → redirect to /ui/ or serve index.html
GET  /ui/                      → Web UI static files (Starlette StaticFiles mount)
```

All JSON responses. Pagination via `limit` + `offset` query params. No streaming for v1.3.

### Static file serving

Starlette's `StaticFiles` mounts a directory as a route:

```python
from starlette.staticfiles import StaticFiles
from starlette.routing import Mount

routes = [
    Mount("/api/v1", app=api_router),
    Mount("/ui", app=StaticFiles(directory=str(STATIC_DIR), html=True)),
]
```

`STATIC_DIR` points to `forge_bridge/console/static/`. The Web UI is a small single-page app (HTML + vanilla JS or minimal bundled framework) — no separate build step for v1.3. Palette: `#242424` base + `#cc9c00` amber per PROJECT.md design contract.

---

## MCP Resource: `forge://manifest/synthesis`

Registered via `register_console_resources(mcp, manifest_service)` in `forge_bridge/console/resources.py`:

```python
@mcp.resource("forge://manifest/synthesis")
async def synthesis_manifest() -> str:
    snapshot = manifest_service.snapshot()
    return json.dumps([asdict(t) for t in snapshot], indent=2)
```

This is the same pattern as `forge://llm/health`. The `manifest_service` reference is captured in the closure at registration time — this requires `register_console_resources()` to be called after `ManifestService` is instantiated, which happens in `_lifespan`. This means resource registration must move from module import time to lifespan time for the manifest resource.

**Consistency invariant for the MCP resource:** `forge://manifest/synthesis` reads `ManifestService.snapshot()` — the same data structure the console HTTP API reads. A tool that the watcher has registered appears in both surfaces simultaneously. No divergence is possible because both surfaces share the same `ManifestService` instance.

---

## Data Flow Diagrams

### A: Web UI tool list → HTTP response

```
User opens /ui/ → browser fetches /api/v1/manifest
  → Starlette route handler (console/read_api.py)
  → manifest_service.snapshot()         [in-memory, no I/O]
  → [ToolRecord, ToolRecord, ...]
  → JSONResponse([{name, sha256, status, sidecar_meta, ...}, ...])
  → browser renders tool table
```

No database. No JSONL read. Pure in-memory snapshot.

### B: Web UI execution history → HTTP response

```
User opens /ui/executions → browser fetches /api/v1/executions?limit=50&offset=0
  → Starlette route handler
  → execution_log.snapshot(limit=50, offset=0)    [new method, in-memory dict iteration]
  → [{code_hash, raw_code, intent, count, promoted}, ...]
  → JSONResponse
  → browser renders execution table
```

### C: User clicks tool in Web UI → per-tool drilldown

```
User clicks tool row → browser fetches /api/v1/manifest/{name}
  → manifest_service.get(name)           [dict lookup]
  → JSONResponse(asdict(tool_record))

  + browser fetches /api/v1/executions?filter=... (if per-tool exec filter is in scope)
```

### D: LLM chat request

```
User types prompt in chat panel → POST /api/v1/chat {prompt: "show me shots with unverified plates"}
  → console/chat.py handler
  → build context string:
      manifest_service.snapshot() → tool names + observation_count lines
      execution_log.snapshot(limit=5) → recent executions summary
  → LLMRouter.acomplete(
        prompt=prompt,
        system=CONSOLE_SYSTEM_PROMPT.format(context=context_string),
        sensitive=True     # pipeline data stays local
    )
  → await response string
  → JSONResponse({reply: response_string})
  → browser renders reply in chat panel
```

`CONSOLE_SYSTEM_PROMPT` is defined in `console/chat.py`, framing the bridge's read-side data as LLM context. It must NOT include file paths, DB credentials, or other deployment-specific strings — same constraint as `_DEFAULT_SYSTEM_PROMPT` in `router.py`.

### E: Watcher → ManifestService → MCP resource (live update path)

```
New .py file appears in ~/.forge-bridge/synthesized/
  → watcher._scan_once() detects new sha256
  → manifest_verify(path) passes
  → _read_sidecar(path) → provenance dict
  → register_tool(mcp, fn, ...) succeeds
  → manifest_service.register(stem, ToolRecord(...))   [NEW call]
  → next poll of forge://manifest/synthesis returns updated snapshot
```

The MCP resource is not push-notified — it reflects the state at read time. An LLM agent calling `forge://manifest/synthesis` twice gets current state each time.

### F: CLI → console HTTP API

```
$ forge-bridge console tools
  → CLI (forge_bridge/cli/console.py) parses subcommand
  → httpx.get("http://localhost:9996/api/v1/manifest")
  → parse JSON response
  → format table output (Typer + Rich)
```

The CLI is stateless — it makes one HTTP request per subcommand and formats the result. No persistent connection. Uses `httpx` (already a dependency via `forge_bridge/bridge.py`).

---

## Threading / Asyncio Boundaries

All new console code runs in the same asyncio event loop as the MCP server (single process, single loop). This is fine because all operations are:

- `manifest_service.snapshot()` — pure dict copy, O(n) where n = registered tool count (dozens)
- `execution_log.snapshot()` — dict iteration, no I/O
- `LLMRouter.acomplete()` — async HTTP to Ollama, already in-loop
- `uvicorn.Server.serve()` — asyncio-native, runs in-loop

No threads are introduced. No `asyncio.run()` / `run_in_executor` needed for any console path.

**One boundary to watch:** `ExecutionLog.record()` is called from `bridge.py`'s `execute()` coroutine (in-loop, fine) and potentially from Flame thread contexts (out-of-loop, where the storage callback falls through the `RuntimeError` branch). The new `snapshot()` method reads from the same in-memory dicts as `record()` — since Python's GIL prevents torn reads on dict operations and the MCP event loop is single-threaded, this is safe without additional locking. If concurrent `record()` + `snapshot()` is ever a concern, a `threading.RLock` on the ExecutionLog instance (not an asyncio.Lock) is the right mitigation, since `record()` may be called from non-async threads.

**LLM chat streaming (deferred):** If streaming is added in a future phase, the pattern is `LLMRouter.astream()` (new method) + Starlette `StreamingResponse` in the chat handler. This is isolated to `chat.py` and does not affect other components.

---

## Manifest Consistency Invariant (Formal Statement)

At any point in time:

1. **ManifestService ↔ FastMCP tool registry:** Every tool in `ManifestService._tools` corresponds to a live registered tool in the `mcp` FastMCP instance. The watcher calls `register_tool(mcp, ...)` and `manifest_service.register(...)` in sequence before yielding. The watcher calls `mcp.remove_tool(stem)` and `manifest_service.remove(stem)` in sequence on deletion. The asyncio.Lock on `ManifestService` prevents concurrent writes but not the window between `register_tool` and `manifest_service.register` — this two-step is inherently non-atomic. An MCP client that calls `tools/list` in that window sees the tool before the manifest does. This is acceptable: the direction of inconsistency is "tool registered before manifest knows about it" which is safe for read-only manifests. The reverse (manifest knows about a tool that is not registered) must not happen — call `manifest_service.register()` only after `register_tool()` succeeds.

2. **ManifestService ↔ disk .sidecar.json:** `ToolRecord.sidecar_meta` is captured at registration time from the sidecar on disk. If the sidecar changes after registration, `ToolRecord` is stale until the watcher's next poll detects a file hash change (the `.py` file must be modified to trigger re-registration, even if only the sidecar changed). This is acceptable for v1.3's read-only milestone.

3. **MCP resource ↔ HTTP API:** Both read `ManifestService.snapshot()`. Always consistent.

4. **ManifestService ↔ ExecutionLog:** `ToolRecord.observation_count` is set at registration time from `ExecutionLog.get_count(sha256)`. It is a point-in-time snapshot — it does not update as new executions are recorded. The HTTP API `/api/v1/manifest/{name}` returns this snapshotted count; `/api/v1/executions` returns the live count from `ExecutionLog`. This is a known staleness: document it in the API response as `observation_count_at_registration`. For a live count, clients query `/api/v1/executions?filter=code_hash=...` (or add a `GET /api/v1/manifest/{name}/executions` endpoint that joins them).

---

## Build Order

Dependencies determine ordering. The build order below respects the rule: no phase attempts to build a UI before its backing API exists.

### Phase 9: ManifestService + ExecutionLog read API + Console HTTP skeleton

**Deliverables:**
- `forge_bridge/console/manifest_service.py` — `ManifestService`, `ToolRecord`
- `forge_bridge/learning/execution_log.py` — `snapshot()` method added
- `forge_bridge/console/read_api.py` — `/api/v1/manifest`, `/api/v1/executions`, `/api/v1/health` endpoints (no static files yet)
- `forge_bridge/mcp/server.py` — `_lifespan` wires `ManifestService`, injects into watcher, starts console uvicorn task
- `forge_bridge/learning/watcher.py` — `manifest_service` injection
- Tests: `ManifestService` unit tests, `snapshot()` unit tests, route handler tests with a test client

**Why first:** Everything else depends on `ManifestService` and the HTTP API existing. The watcher injection and `ExecutionLog.snapshot()` are the foundational read-side primitives.

### Phase 10: MCP resource `forge://manifest/synthesis`

**Deliverables:**
- `forge_bridge/console/resources.py` — `register_console_resources(mcp, manifest_service)`
- `forge_bridge/mcp/server.py` — call `register_console_resources()` in `_lifespan` after `ManifestService` is ready
- `forge_bridge/__init__.py` — barrel re-export for any new public symbols
- Tests: MCP resource round-trip test (read resource URI, verify JSON shape matches `ManifestService.snapshot()`)
- Release ceremony: `__all__` grows, minor version bump, tag

**Why second:** MCP resource depends on `ManifestService` (Phase 9). It is a small addition and should ship as part of the same minor version bump as the console API to keep the release ceremony count low. If the MCP resource is simple enough (it is — one function), it can merge with Phase 9 into a single phase.

**Merge option:** If Phase 9 and Phase 10 are small, combine into one phase: "Console read API + manifest MCP resource." The roadmapper decides based on estimated complexity.

### Phase 11: LLM chat endpoint

**Deliverables:**
- `forge_bridge/console/chat.py` — `CONSOLE_SYSTEM_PROMPT`, chat handler, context builder
- Console HTTP API: `POST /api/v1/chat` route registered
- Tests: chat handler with mocked `LLMRouter`, context injection test

**Why third:** Depends on `ManifestService` (Phase 9) and `ExecutionLog.snapshot()` (Phase 9) for context building. Independent of Web UI and CLI — can ship before or after them.

### Phase 12: Web UI (static assets + serving)

**Deliverables:**
- `forge_bridge/console/static/` — `index.html`, CSS (LOGIK-PROJEKT dark + amber palette), minimal JS for tool list / exec list / drilldown / chat panel
- Starlette `StaticFiles` mount added to console Starlette app
- Console HTTP API: `GET /ui/` route (redirect or serve index)
- Design contract delivered by `/gsd-ui-phase` tooling for this phase

**Why fourth:** Depends on the HTTP API (Phase 9) being stable. The Web UI is a read-only consumer of the already-built API — it has no coupling to Phase 10 (MCP resource) or Phase 11 (chat, unless the chat panel is in scope for this phase).

**Chat UI in Web UI:** Chat panel in the Web UI can be deferred to Phase 12 (if included in Web UI) or a separate phase. It depends on Phase 11's `POST /api/v1/chat` endpoint. Simplest: include chat panel in Phase 12 after Phase 11 ships.

### Phase 13: CLI companion

**Deliverables:**
- `forge_bridge/cli/console.py` — Typer app with subcommands: `tools`, `executions`, `health`, `chat`
- Entry point: `forge-bridge console <subcommand>` wired in `pyproject.toml` `[project.scripts]`
- Uses `httpx` (already a dependency) for HTTP calls to `:9996`
- Tests: CLI integration tests calling a real (test-instance) console API

**Why last:** CLI depends on the HTTP API (Phase 9) being stable and tested. It is the thinnest layer — pure formatting of JSON responses. Building it last means the API is already verified by Web UI usage in Phase 12, so CLI development has a proven contract.

**Merge option:** Phase 13 is small enough to merge with Phase 12 if the Web UI is lightweight. Roadmapper decides.

### Summary build order

```
Phase 9:  ManifestService + ExecutionLog.snapshot() + Console HTTP API skeleton
Phase 10: MCP resource forge://manifest/synthesis  [may merge with Phase 9]
Phase 11: LLM chat endpoint (POST /api/v1/chat)
Phase 12: Web UI (static assets, design contract, StaticFiles mount)
Phase 13: CLI companion (Typer + httpx)           [may merge with Phase 12]
```

No phase requires parallel work. Each phase has a single integration test checkpoint: "does the console HTTP API return correct data for this surface?" before moving forward.

---

## New vs Modified vs Untouched — Explicit List

### New files

```
forge_bridge/console/__init__.py
forge_bridge/console/manifest_service.py   — ManifestService, ToolRecord
forge_bridge/console/read_api.py           — Starlette route handlers
forge_bridge/console/chat.py               — LLM chat handler + context builder
forge_bridge/console/resources.py          — register_console_resources(mcp, manifest_service)
forge_bridge/console/static/               — Web UI assets (index.html, style.css, app.js)
forge_bridge/cli/console.py                — Typer CLI app (forge-bridge console subcommands)
tests/console/test_manifest_service.py
tests/console/test_read_api.py
tests/console/test_chat.py
tests/console/test_resources.py
tests/cli/test_console_cli.py
```

### Modified files

```
forge_bridge/mcp/server.py         — _lifespan: ManifestService init, watcher injection,
                                     console uvicorn task, register_console_resources()
forge_bridge/learning/watcher.py   — watch_synthesized_tools() + _scan_once() accept
                                     optional manifest_service: ManifestService | None = None
forge_bridge/learning/execution_log.py — add snapshot(limit, offset) method
forge_bridge/__init__.py           — re-export ManifestService, ToolRecord (+ CLI entrypoint?)
                                     __all__ grows 16 → ~18-20
pyproject.toml                     — [project.scripts] forge-bridge console entry point;
                                     add uvicorn + starlette as non-optional deps if not present
```

### Untouched files (confirmed)

```
forge_bridge/bridge.py
forge_bridge/learning/synthesizer.py
forge_bridge/learning/manifest.py
forge_bridge/learning/probation.py
forge_bridge/learning/storage.py
forge_bridge/learning/sanitize.py
forge_bridge/mcp/registry.py
forge_bridge/mcp/tools.py
forge_bridge/mcp/__init__.py
forge_bridge/llm/router.py
forge_bridge/llm/health.py
forge_bridge/server/            — standalone WS server
forge_bridge/core/              — vocabulary layer
forge_bridge/store/             — PG persistence layer
forge_bridge/client/            — async/sync WebSocket clients
forge_bridge/flame/             — Flame endpoint
flame_hooks/                    — runs inside Flame
```

---

## Dependency Additions

| Package | Purpose | Already present | Add as |
|---------|---------|----------------|--------|
| `uvicorn[standard]` | Serve console ASGI app on `:9996` | No | Hard dep (console is core feature) |
| `starlette` | Routing, StaticFiles, JSONResponse | Via `mcp[cli]` (indirect) | Hard dep (explicitly declare) |
| `typer` | CLI subcommand framework | No | Hard dep (or optional `[cli]` extra) |
| `rich` | CLI table formatting | No | Hard dep alongside typer (standard pairing) |
| `httpx` | CLI HTTP calls to `:9996` | Yes (bridge.py) | Already present |

Note: `starlette` is already transitively present via `mcp[cli]`. Declaring it explicitly in `pyproject.toml` ensures version pinning and removes the implicit dependency risk.

---

## Critical Integration Pitfalls

### P-01: uvicorn task startup race in _lifespan

**What goes wrong:** `asyncio.create_task(serve_uvicorn(console_app, port=9996))` starts uvicorn asynchronously. The next line in `_lifespan` (yield, meaning "server is ready") may be reached before uvicorn has bound the port. CLI calls immediately after startup will get connection refused.

**Prevention:** Use a startup event or an `asyncio.Event` that uvicorn's on_startup handler sets. `_lifespan` awaits the event before yielding. Uvicorn's `Server.serve()` with a `Config` that sets `callback_notify` supports this pattern.

### P-02: `@mcp.resource()` registration in `_lifespan` — not at import time

**What goes wrong:** `register_console_resources(mcp, manifest_service)` must be called after `ManifestService` is instantiated (in `_lifespan`), but `register_builtins(mcp)` is called at import time (before lifespan). Registering the manifest resource at import time means `manifest_service` does not exist yet.

**Prevention:** Define `register_console_resources(mcp, manifest_service)` in `console/resources.py` with explicit `manifest_service` parameter injection (not module-level singleton). Call it from `_lifespan` after instantiation. This is exactly how `register_llm_resources(mcp)` works today — called from `register_builtins`, which is called at import time — except the manifest resource needs a parameter that doesn't exist at import time. The fix is to call `register_console_resources` from `_lifespan`, not from `register_builtins`.

### P-03: `ExecutionLog` instance identity

**What goes wrong:** If the console API creates its own `ExecutionLog()` instance to call `snapshot()`, it reads from a *different* JSONL replay — not the same in-memory counters that `bridge.py`'s callback is incrementing in the live instance.

**Prevention:** The `ExecutionLog` instance must be the same object that `set_execution_callback()` registered against. This means the `_lifespan` function or the MCP server startup must hold the canonical `ExecutionLog` reference and pass it to both the callback registration path and the console read API. Today, projekt-forge owns the `ExecutionLog` instance — this is a cross-repo concern. For forge-bridge standalone (no projekt-forge), the `_lifespan` should create a default `ExecutionLog()` instance and expose it to the console read API via the same injection pattern as `ManifestService`.

### P-04: Port conflict on `:9996`

**What goes wrong:** If another process has `:9996` bound (or if forge-bridge is started twice), `uvicorn` will fail to bind. Unlike the graceful degradation on `:9998`, a console port bind failure should be logged as a WARNING (not crash) but the MCP server should continue without the console.

**Prevention:** Wrap the uvicorn task start in try/except `OSError`. Log "Console API unavailable — port 9996 in use." MCP tools continue working; CLI and Web UI are unavailable until port is freed.

### P-05: StaticFiles directory not found

**What goes wrong:** `StaticFiles(directory=str(STATIC_DIR))` raises at app construction time if `STATIC_DIR` does not exist (e.g., editable install without static files copied, or missing in sdist).

**Prevention:** `STATIC_DIR = Path(__file__).parent / "static"`. Guard: `if STATIC_DIR.exists(): mount StaticFiles else: log WARNING "Web UI unavailable"`. In `pyproject.toml`, include `"forge_bridge/console/static/**"` in `[tool.setuptools.package-data]`.

### P-06: CLI connecting to console API when MCP server is not running

**What goes wrong:** `forge-bridge console tools` calls `httpx.get("http://localhost:9996/api/v1/manifest")` — raises `httpx.ConnectError` if the MCP server is not running.

**Prevention:** CLI catches `httpx.ConnectError` and prints "forge-bridge console is not running. Start it with: python -m forge_bridge" then exits with code 1. Same pattern as `BridgeConnectionError` in `bridge.py`.

---

## `__all__` Impact

| Symbol | Phase | Rationale |
|--------|-------|-----------|
| `ManifestService` | 9 | Consumer may want to inject into custom watcher |
| `ToolRecord` | 9 | Consumer may want to deserialize manifest API responses |
| Console entrypoints (TBD) | 13 | CLI entry point wiring — may not need barrel export |

Projected `__all__` growth: 16 → 18 (two new symbols). Minor version bump ceremony applies.

---

## Ports Reference

| Port | Owner | Protocol | Purpose |
|------|-------|----------|---------|
| `:9999` | Flame process | HTTP | Flame Python execution bridge |
| `:9998` | forge-bridge standalone server | WebSocket | Pipeline entity / event pub-sub |
| `:9996` | MCP server process (new) | HTTP | Console API + Web UI |
| stdio | MCP server process | MCP/JSON-RPC | LLM agent tool calls |

`:9997` is intentionally left unassigned as a buffer.

---

## Sources

### Primary (HIGH confidence)

- Direct source reads: `forge_bridge/mcp/server.py`, `forge_bridge/mcp/registry.py`, `forge_bridge/learning/watcher.py`, `forge_bridge/learning/execution_log.py`, `forge_bridge/learning/manifest.py`, `forge_bridge/llm/health.py`, `forge_bridge/bridge.py`, `forge_bridge/__init__.py` — all read from working tree at v1.3.0 tag
- PROJECT.md v1.3 milestone scope (2026-04-22)
- FastMCP `@mcp.custom_route()` decorator — verified in FastMCP docs (gofastmcp.com/deployment/http) and Context7 `/prefecthq/fastmcp`
- FastMCP Starlette mount pattern — verified in MCP Python SDK docs (modelcontextprotocol/python-sdk README, `Mount` + `lifespan` examples)
- `@mcp.resource()` pattern — verified in Context7 `/modelcontextprotocol/python-sdk`
- `uvicorn.Server` programmatic API — standard pattern for embedding uvicorn in asyncio tasks
- Starlette `StaticFiles` — standard Starlette docs
- `httpx` as CLI HTTP client — already present as a forge-bridge dependency (`bridge.py`)
- Typer + Rich — standard Python CLI toolchain (well-established, confirmed current 2026)

### Secondary (MEDIUM confidence)

- WebSearch: FastMCP custom routes + uvicorn programmatic API patterns (2025-2026)
- v1.2 ARCHITECTURE.md (`ARCHITECTURE-v1.2.md`) — v1.2 integration decisions preserved for context

---

*Research completed: 2026-04-22*
*Preceding v1.2 research archived at: `.planning/research/ARCHITECTURE-v1.2.md`*
*Ready for roadmap: yes — 5 phases (9–13), sequential, no cross-repo work for core console surfaces*
