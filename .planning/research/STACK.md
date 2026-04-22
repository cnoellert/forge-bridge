# Technology Stack — v1.3 Artist Console (Web UI + CLI + MCP Resources)

**Project:** forge-bridge v1.3 — Artist Console
**Researched:** 2026-04-22
**Scope:** ONLY the new capabilities needed for v1.3: web framework, frontend stack, CLI surface, and MCP resources. Does not re-research the validated v1.0–v1.2 stack. See `STACK-v1.2.md` for the prior milestone's research.
**Overall confidence:** HIGH

---

## Foundational discovery: FastMCP 1.26.0 has a built-in HTTP route extension point

Before framework selection, the critical finding that shapes every other decision:

`FastMCP.custom_route(path, methods)` is a public decorator (verified on installed `mcp==1.26.0`) that appends a `starlette.routing.Route` to an internal `_custom_starlette_routes` list. When `FastMCP.streamable_http_app()` builds its `Starlette` application, it includes all custom routes alongside the `/mcp` endpoint. The result is a single `Starlette` application served by a single `uvicorn` process on one port.

```python
@mcp.custom_route('/console/health', methods=['GET'])
async def console_health(request: Request) -> JSONResponse:
    return JSONResponse({'status': 'ok'})
```

Verified route merge output:
```
Route(path='/mcp', name='StreamableHTTPASGIApp', methods=[])
Route(path='/console/health', name='console_health', methods=['GET', 'HEAD'])
```

`Mount` objects (for `StaticFiles`) can also be appended directly to `mcp._custom_starlette_routes` — verified working:
```
Mount(path='/console/static', name='static', app=<StaticFiles>)
```

**Consequence:** There is no need to stand up a second ASGI process or thread for the web API. The console shares the FastMCP event loop, the FastMCP lifespan, and the FastMCP port. No new async primitives, no `asyncio.run()` nesting, no inter-process coordination.

---

## Already-installed transitive dependencies (zero new cost)

Running `mcp[cli]>=1.19,<2` already pulls these into the environment:

| Package | Version (verified) | Relevant capability |
|---------|-------------------|---------------------|
| `starlette` | 0.52.1 | `Route`, `Mount`, `StaticFiles`, `Jinja2Templates`, `Request`, `Response` |
| `uvicorn` | 0.41.0 | ASGI server (FastMCP uses it via `run_streamable_http_async`) |
| `anyio` | 4.12.1 | Async compatibility layer (FastMCP uses it in `mcp.run()`) |
| `sse_starlette` | 3.2.0 | `EventSourceResponse` for SSE push |
| `typer` | 0.24.1 | CLI framework |
| `rich` | 14.3.3 | Rich terminal output for CLI |
| `httpx` | (existing dep) | HTTP client for CLI → console API calls |

These packages require **zero new entries** in `pyproject.toml` for the capabilities they provide.

---

## 1. Web Framework: Starlette via FastMCP's custom_route

**Recommendation: Use Starlette directly via `mcp.custom_route()` and `mcp._custom_starlette_routes.append(Mount(...))`.**

Do NOT add FastAPI as a dependency.

### Rationale

FastAPI is Starlette with a Pydantic-validated routing layer added. For a read-only localhost console with a handful of endpoints, FastAPI's added weight (auto-generated OpenAPI docs, response model validation, dependency injection framework) solves problems this project does not have. Starlette provides everything needed: `Route`, `JSONResponse`, `Request`, `Mount`, `StaticFiles`, `Jinja2Templates`, and `StreamingResponse`. It is already installed.

The integration is single-process, single-port, single-event-loop. `mcp.run(transport="streamable-http")` calls `anyio.run(self.run_streamable_http_async)` which calls `uvicorn.serve()` on `self.streamable_http_app()` — the same `Starlette` instance that carries both MCP and console routes.

### Read API endpoint shape

All console read endpoints live under `/console/`:

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/console/health` | GET | `{status, tools_count, uptime_s}` |
| `/console/tools` | GET | Array of tool summaries (name, origin, tags, observation_count) |
| `/console/tools/{name}` | GET | Full tool detail with provenance meta |
| `/console/manifest` | GET | Synthesis manifest (mirrors MCP resource `forge://manifest/synthesis`) |
| `/console/executions` | GET | Recent JSONL execution records (paginated, last N) |
| `/console/executions/{hash}` | GET | Single execution record by code_hash |

Optional (roadmapper decides scope):
| `/console/stream/executions` | GET | SSE stream of new execution records (see section 5) |

### Port assignment

`FORGE_CONSOLE_PORT` env var, default `:9996` (per PROJECT.md serving model). The port is set via `FastMCP(port=9996)` constructor kwarg (verified: `settings.port` is a field on `FastMCPSettings`).

### Alternatives considered and rejected

| Alternative | Why rejected |
|-------------|-------------|
| FastAPI as wrapper | Starlette is already installed; FastAPI adds ~1MB of dependencies for zero functional gain in this use case |
| Second process on new port | Breaks single-process invariant; adds IPC; splits lifespan management; more surface to break |
| `aiohttp` | Not installed; not compatible with Starlette/anyio event loop; adds a dependency |
| Flask/Quart | Sync-first or separate WSGI server; incompatible with FastMCP's asyncio process |

---

## 2. Frontend Stack: Jinja2 + htmx 2.x + Alpine.js 3.x

**Recommendation: Server-rendered HTML via Starlette's `Jinja2Templates`, enhanced with htmx for partial-page updates, and Alpine.js for the minimal reactive state the dashboard needs.**

Do NOT adopt a SPA framework (React, Svelte, SvelteKit, Solid). Do NOT adopt a Node.js build pipeline.

### Why server-rendered + htmx beats SPA for this use case

The Artist Console is a **read-only dashboard** with these characteristics:
- Data-dense tables (tools list, execution history, manifest viewer)
- Occasional drill-down to detail views
- No complex client-side routing
- Operator audience (VFX TDs, not browser-app users)
- Runs exclusively on localhost over fast LAN

A SPA framework introduces: a Node.js build step in the pip package, a bundler (Vite/webpack), a separate JS module resolution system, and a development server alongside the Python server. None of that complexity is justified by the feature set.

htmx lets the server return HTML fragments that replace DOM subtrees. The pattern is:
- Initial page load: Jinja2 renders the full page with current data
- Drill-down/filter: `hx-get="/console/tools?q=reconform"` swaps the table body in-place
- SSE (if scoped in): htmx SSE extension connects to `/console/stream/executions` and appends rows

Alpine.js handles the UI state that is inherently client-side:
- Tab state (Tools / Executions / Manifest / Health)
- Collapsible detail panels
- Copy-to-clipboard on code_hash values
- Toast notifications

Both are CDN-deliverable via `<script src="...">` embedded in the base Jinja2 template. No build step, no `node_modules`, no bundler. The static assets served from `/console/static/` are: the base template CSS file and any icons/logos.

### Palette implementation

The LOGIK-PROJEKT dark + amber palette is implemented as CSS custom properties in a single `forge-console.css` file (served from `/console/static/forge-console.css`). This file is the only hand-authored CSS; htmx class targets use these variables directly.

```css
:root {
  --forge-bg:        #242424;
  --forge-field-bg:  #3a3f4f;
  --forge-amber:     #cc9c00;
  --forge-text:      #cccccc;
  --forge-border:    #333333;
  --forge-border-hi: #555555;
  --forge-font:      "Segoe UI", "Helvetica Neue", Arial, 11pt;
}
```

No Tailwind. Tailwind's Play CDN is explicitly marked "development only" and ships a 3.5 MB file with no tree-shaking. For a tool that runs in a locked-down VFX studio environment with potentially no internet access, a CDN dependency is a non-starter. The palette is small enough that hand-authored CSS variables + a minimal utility sheet is the correct approach.

### Dependency additions for Jinja2

`Jinja2` is NOT currently installed (verified: `python3 -c "import jinja2"` fails). It is a new dependency:

```toml
"jinja2>=3.1"
```

Starlette's `Jinja2Templates` class already handles the `TemplateResponse` wrapping. Jinja2 3.x is stable; no upper bound needed.

### htmx and Alpine.js delivery

Both are delivered as vendored static files in `forge_bridge/console/static/`:
- `htmx.min.js` — htmx 2.0.x (current: 2.0.10, verified via github.com/bigskysoftware/htmx releases)
- `alpine.min.js` — Alpine.js 3.x (current: 3.x, actively maintained with April 2026 release)

Vendored (not CDN-fetched) because:
1. VFX studio machines have no guaranteed internet access
2. No build step and no external runtime dependency
3. Both files are <50 KB combined (htmx ~16 KB gzipped, Alpine ~8 KB gzipped)

### Alternatives considered and rejected

| Alternative | Why rejected |
|-------------|-------------|
| SPA (React/Svelte/SvelteKit/Solid) | Requires Node.js build pipeline, incompatible with pip package model, zero benefit for a read-only dashboard |
| Tailwind CDN | 3.5 MB unoptimized, requires internet, "development only" per Tailwind docs |
| Tailwind with build step | Introduces Node.js + PostCSS into a Python package — the cure is worse than the disease |
| Plain HTML (no htmx) | Full-page reloads for every filter/sort; acceptable but worse for table-heavy views |
| Vue.js CDN | Alpine.js covers the reactive state needs at 1/10 the size |

---

## 3. CLI Framework: Typer (already installed, sync wrappers required)

**Recommendation: Use `typer` (already installed at 0.24.1) with sync command functions that call `asyncio.run()` internally where async operations are needed.**

### Discovered constraint: Typer 0.24.1 does not natively execute async commands

Verified via live test: `@app.command()` on an `async def` registers the coroutine function but never awaits it — it silently returns with `RuntimeWarning: coroutine was never awaited`. This is a known limitation of Typer's Click foundation.

**Correct pattern for async CLI commands:**

```python
@console_app.command()
def tools(
    format: Annotated[str, typer.Option("--format", "-f")] = "table",
    filter: Annotated[str | None, typer.Option("--filter")] = None,
):
    """List all registered MCP tools with provenance."""
    import asyncio
    data = asyncio.run(_fetch_tools(filter=filter))
    _render_tools(data, format=format)
```

Where `_fetch_tools()` is an `async def` that calls the console read API via `httpx.AsyncClient`. This pattern: sync outer function (Click-compatible) wraps `asyncio.run()` wraps the actual async I/O.

### CLI surface: `forge-bridge console <subcommand>`

Implemented via `typer.Typer()` subapp registered on the main entry point:

```python
# forge_bridge/cli/__init__.py
console_app = typer.Typer(name="console", help="Artist console commands")

@console_app.command("health")
def health(): ...

@console_app.command("tools")
def tools(filter: str | None = None): ...

@console_app.command("manifest")
def manifest(): ...

@console_app.command("executions")
def executions(limit: int = 50): ...
```

The `forge-bridge` entry point in `pyproject.toml` points to the top-level Typer app which has `console_app` added as a subcommand.

### CLI transport: HTTP calls to the console read API

The CLI communicates with the running forge-bridge process via the console read API on `:9996`. This means `forge-bridge console tools` requires a running forge-bridge server — same posture as `forge-bridge console health` in any DevOps tool. The CLI is a thin client; the server owns the data.

`httpx` (already a declared dependency: `httpx>=0.27`) handles the HTTP calls. The CLI uses `httpx.get("http://127.0.0.1:9996/console/tools")` — sync `httpx` (not async), eliminating the `asyncio.run()` wrapper entirely for simple GET requests.

### Rich output

`rich` (installed at 14.3.3 as a transitive dep of `mcp[cli]`) provides tables, panels, and JSON pretty-printing for CLI output. No additional formatting library needed.

```python
from rich.console import Console
from rich.table import Table
console = Console()
table = Table(title="MCP Tools")
# ...
console.print(table)
```

### Alternatives considered and rejected

| Alternative | Why rejected |
|-------------|-------------|
| Click directly | Typer is already installed and provides type annotation DX; no reason to drop to Click |
| `argparse` | Strictly worse DX than Typer, no Rich integration |
| Cyclopts | Not installed, not a transitive dep — adds a dep for no gain |
| Native async Typer support | Does not exist in 0.24.1; would require monkey-patching Click's invoke mechanism |

---

## 4. MCP Resources: FastMCP `@mcp.resource()` with `forge://` scheme

**Recommendation: Expose the synthesis manifest as an MCP resource at `forge://manifest/synthesis` using the `@mcp.resource()` decorator — the same `FastMCP` instance that already hosts all tools.**

### FastMCP resource API (verified on mcp==1.26.0)

```python
@mcp.resource(
    "forge://manifest/synthesis",
    name="synthesis_manifest",
    title="Synthesis Manifest",
    description="Current state of all synthesized MCP tools with provenance.",
    mime_type="application/json",
)
async def synthesis_manifest() -> str:
    """Read synthesis manifest from JSONL + sidecar state."""
    data = await _build_manifest()
    return json.dumps(data, indent=2)
```

The `@mcp.resource()` decorator signature (verified):
```python
FastMCP.resource(
    uri: str,
    *,
    name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    mime_type: str | None = None,
    icons: list[Icon] | None = None,
    annotations: Annotations | None = None,
    meta: dict[str, Any] | None = None,
) -> Callable[[AnyFunction], AnyFunction]
```

Available resource-related methods on the FastMCP instance: `add_resource`, `list_resource_templates`, `list_resources`, `read_resource`, `resource`. The decorator is stable since v1.15.0 (PR #1357, Sep 2025); no version bump needed beyond the existing `mcp[cli]>=1.19,<2` pin.

### URI scheme: `forge://`

The `forge://` scheme follows the MCP convention of reverse-DNS-style custom schemes. It is already established in the codebase for `forge://llm/health` (v1.0 LLM health resource). v1.3 adds:

| URI | Content | Consumer |
|-----|---------|----------|
| `forge://manifest/synthesis` | Full synthesis manifest JSON | LLM agents (MCP) + console API (web/CLI) |
| `forge://llm/health` | LLM router health | LLM agents (already shipped) |

### Resource vs tool: why manifest is a resource

MCP resources are semantically "read-only data that provides context." The synthesis manifest fits exactly: it is a named, stable, URL-addressable document that LLM agents read to understand what tools are available, their provenance, and their state. It is not a function that takes parameters and produces a side effect. Exposing it as a resource lets MCP clients call `resources/read` without going through `tools/call`, which respects the semantic contract and allows future client-side caching.

### Mutable state via resources: the canonical pattern

Resources can read live state. The synthesis manifest resource reads from:
1. The in-process `_synthesis_manifest` dict (built by the watcher during startup)
2. JSONL files (read-only scan at request time for cold data)
3. Tool registry (live `mcp.list_tools()` for current registered state)

The resource function is `async def` — it can do async I/O (file reads) within the single asyncio event loop. The data it returns is a point-in-time snapshot; the resource is inherently stateless (no caching needed at v1.3 — the manifest builds in <10ms for typical tool counts).

### What NOT to add

Do not create a separate resource for each synthesized tool's sidecar — that would be `forge://tool/{name}/provenance` for every tool. That data lives in `Tool._meta` already (shipped in v1.2). The manifest resource is the aggregate view; per-tool provenance is in the tool's own `_meta`. Keep the resource surface minimal.

---

## 5. Real-time Streaming: SSE available, poll-first recommendation

**Recommendation: Implement poll-first for v1.3. SSE is zero-cost to add if roadmapper scopes it in, but poll is simpler to test and reason about for a read-only console with sub-second refresh tolerance.**

### SSE technical feasibility: confirmed, zero new deps

`sse_starlette` 3.2.0 is already installed. The `EventSourceResponse` class wraps an async generator:

```python
from sse_starlette.sse import EventSourceResponse

@mcp.custom_route('/console/stream/executions', methods=['GET'])
async def stream_executions(request: Request) -> EventSourceResponse:
    async def _generator():
        async for record in _tail_execution_log():
            yield {"data": record.to_json(), "event": "execution"}
    return EventSourceResponse(_generator())
```

htmx's SSE extension (`hx-ext="sse"`) connects to this endpoint and appends DOM nodes without a page reload.

### Poll-first rationale

The execution log is append-only JSONL. The console can poll `GET /console/executions?since=<timestamp>` on a 2-second interval with near-zero server cost. The JSONL reader is already locked with `fcntl.LOCK_EX` on writes — concurrent reads from the console HTTP handler and the execution log writer are safe because reads do not require the lock (append is the only write operation, and appended data is immediately readable by subsequent readers on POSIX filesystems).

SSE adds: a long-lived HTTP connection per open browser tab, a server-side async generator that must be cancelled on client disconnect, and a more complex test harness. For v1.3, these costs are not justified given poll works fine.

**Roadmapper gate:** If "live execution feed without polling" is in scope, add `sse_starlette` usage in one endpoint. If not, defer to v1.4. The infrastructure is ready either way.

### WebSocket: explicitly out of scope

The forge-bridge standalone WebSocket server already runs on `:9998` (existing). Adding a second WebSocket surface on `:9996` for the console would mean two WebSocket servers in the same process with overlapping semantics. WebSocket is bidirectional; the console is read-only. SSE is the correct protocol for one-way server-push.

---

## 6. LLM Chat Layer: Reuse LLMRouter, no new LLM client library

**Recommendation: The chat panel in the Web UI calls `POST /console/chat` which internally calls `llm_router.acomplete()`. No new LLM client library. No changes to LLMRouter.**

### Integration point

The LLMRouter instance (`forge_bridge.llm.LLMRouter`) is constructed at server startup and available in the MCP server process. The chat endpoint is a `mcp.custom_route`:

```python
@mcp.custom_route('/console/chat', methods=['POST'])
async def console_chat(request: Request) -> JSONResponse:
    body = await request.json()
    prompt = body.get("prompt", "")
    response = await _llm_router.acomplete(prompt, context=_build_context())
    return JSONResponse({"response": response})
```

The chat panel is a minimal htmx form that posts to this endpoint and swaps the response into a `<div id="chat-output">`. No streaming response needed for v1.3 (the LLMRouter's `acomplete()` returns a complete string).

### What NOT to add

Do not add `langchain`, `llama-index`, or any agent framework. The LLMRouter's `acomplete()` is sufficient for prompt-in, text-out chat. Do not add a second `openai` or `anthropic` client instance — the existing LLMRouter already manages those connections.

---

## Dependency changes summary

| `pyproject.toml` section | Change | Reason |
|--------------------------|--------|--------|
| `dependencies` | Add `"jinja2>=3.1"` | Starlette `Jinja2Templates` requires it at runtime; currently not installed |
| `dependencies` | No change to `mcp[cli]>=1.19,<2` | `custom_route`, `resource`, `starlette`, `uvicorn`, `sse_starlette`, `typer`, `rich` all come with the existing MCP dep |
| `[project.scripts]` | Update `forge-bridge` entry point to top-level Typer app with `console` subapp | CLI surface |
| `[project.optional-dependencies]` | No change | LLMRouter extras are already declared |

**New vendored static files (not pip deps):**
- `forge_bridge/console/static/htmx.min.js` — htmx 2.0.10 (download from github.com/bigskysoftware/htmx/releases)
- `forge_bridge/console/static/alpine.min.js` — Alpine.js 3.x current release
- `forge_bridge/console/static/forge-console.css` — hand-authored palette CSS

---

## Integration map: how everything connects inside one process

```
python -m forge_bridge
  └─ mcp.run(transport="streamable-http")
       └─ anyio.run(mcp.run_streamable_http_async)
            └─ uvicorn.serve(mcp.streamable_http_app())
                 └─ Starlette(routes=[
                        Route('/mcp', MCP protocol handler),
                        Route('/console/health',  console_health),
                        Route('/console/tools',   console_tools),
                        Route('/console/tools/{name}', console_tool_detail),
                        Route('/console/manifest', console_manifest),
                        Route('/console/executions', console_executions),
                        Route('/console/chat',    console_chat),
                        Mount('/console/static',  StaticFiles),
                        Mount('/console',         Jinja2 HTML routes),
                    ], lifespan=mcp._lifespan)
```

All routes share:
- The same asyncio event loop (anyio-managed)
- The same `_lifespan` context (startup_bridge, watcher task)
- The same in-process state (tool registry, execution log, LLMRouter)
- No inter-process communication, no shared memory, no sockets between components

---

## Version pin summary

| Library | Version | Source | Status |
|---------|---------|--------|--------|
| `mcp[cli]` | `>=1.19,<2` (current: 1.26.0) | already in `pyproject.toml` | No change |
| `starlette` | 0.52.1 | transitive via `mcp` | No change, already installed |
| `uvicorn` | 0.41.0 | transitive via `mcp` | No change, already installed |
| `sse_starlette` | 3.2.0 | transitive via `mcp` | No change, already installed |
| `typer` | 0.24.1 | transitive via `mcp[cli]` | No change, already installed |
| `rich` | 14.3.3 | transitive via `mcp[cli]` | No change, already installed |
| `httpx` | `>=0.27` | already in `pyproject.toml` | No change |
| `jinja2` | `>=3.1` | NEW dep | Add to `pyproject.toml` |
| htmx | 2.0.10 | vendored static file | Download to `forge_bridge/console/static/` |
| Alpine.js | 3.x current | vendored static file | Download to `forge_bridge/console/static/` |

---

## Open questions for planning phase

1. **Console port conflict with existing ports.** `:9996` is the proposed default. Confirm no existing service in the VFX studio environment uses this port. `FORGE_CONSOLE_PORT` env var should override.

2. **FastMCP `streamable_http_app()` creates routes at call time.** `_custom_starlette_routes` must be populated before `streamable_http_app()` is called. The console module must register its routes during module import (before `mcp.run()`), not during the lifespan. Confirm registration ordering in `forge_bridge/mcp/server.py`.

3. **Jinja2 template location.** `Jinja2Templates(directory=...)` needs a path. Options: `forge_bridge/console/templates/` (in-package) or a path relative to the package root. In-package is correct — use `importlib.resources` or `pathlib.Path(__file__).parent / "templates"`.

4. **`StaticFiles` with `check_dir=True` (default).** The `static/` directory must exist at server startup. If forge-bridge is installed as a wheel, the static files must be included in `hatch.build` includes. Update `pyproject.toml` `[tool.hatch.build]` to include `forge_bridge/console/`.

5. **SSE scope decision.** Roadmapper gates: is "live execution feed" in v1.3 or v1.4? SSE endpoint is trivial to add; the decision is product scope, not technical risk.

6. **CLI `forge-bridge console` entry point wiring.** The current `pyproject.toml` points `forge-bridge = "forge_bridge.__main__:main"` which calls `mcp.run()` directly. The Typer CLI must coexist: `forge-bridge console health` should NOT start the MCP server. The entry point needs to be updated to a Typer top-level app that dispatches: `forge-bridge` alone starts the MCP server; `forge-bridge console <cmd>` runs CLI commands. This is a design decision for Phase 9.

7. **`hatch.build` includes for static assets.** Current `[tool.hatch.build.targets.wheel] packages = ["forge_bridge"]` will include `forge_bridge/console/` if it exists. But `include` in `[tool.hatch.build]` currently specifies `forge_bridge/**`. Verify that binary/static files in subdirs are included by the glob. The Jinja2 templates (`.html` files) must survive the wheel packaging step.

---

## Sources

### HIGH confidence (verified against installed packages and live runtime)

- Direct inspection: `mcp==1.26.0` installed, `FastMCP.custom_route` source read via `inspect.getsource()`, route merge behavior verified by running Python
- Direct inspection: `starlette==0.52.1` `StaticFiles` and `Mount` verified importable and mountable via `mcp._custom_starlette_routes.append()`
- Direct inspection: `sse_starlette==3.2.0` `EventSourceResponse` verified importable
- Direct inspection: `typer==0.24.1` async command behavior verified — coroutine registered but NOT awaited; sync-wrapper pattern confirmed working
- Direct inspection: `uvicorn==0.41.0`, `anyio==4.12.1`, `rich==14.3.3` all verified installed
- FastMCP `resource` decorator signature verified: `FastMCP.resource(uri, *, name, title, description, mime_type, ...)` — matches SDK docs
- MCP Python SDK Context7 docs — resource decorator examples and URI template patterns
- `pyproject.toml` read directly from forge-bridge repo root

### MEDIUM confidence (web sources, current)

- htmx 2.0.10 current version — github.com/bigskysoftware/htmx/releases (via WebSearch 2026-04-22)
- Alpine.js 3.x active maintenance confirmed — releasebot.io/updates/alpinejs (April 2026 release noted)
- Tailwind Play CDN "development only" limitation — tailwindcss.com/docs/installation/play-cdn (official docs)
- FastMCP `custom_route` console pattern — gofastmcp.com/deployment/running-server (via WebSearch)
- FastMCP `custom_route` mount forwarding known issue — github.com/PrefectHQ/fastmcp/issues/3457 (noted but does not affect `mcp==1.26.0` direct usage pattern verified here)

---

*Research completed: 2026-04-22*
*Ready for roadmap: yes — one new pip dep (jinja2), zero new process boundaries, all runtime behavior verified against installed packages*
