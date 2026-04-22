# Project Research Summary

**Project:** forge-bridge v1.3 — Artist Console
**Domain:** Artist-first observability dashboard (Web UI + CLI + MCP resources) layered on an existing FastMCP + asyncio + JSONL-log middleware package
**Researched:** 2026-04-22
**Confidence:** HIGH

## Executive Summary

v1.3 ships an artist-facing console — a Web UI on port `:9996`, a `forge-bridge console` CLI companion, an MCP resource at `forge://manifest/synthesis`, and a shared `ConsoleReadAPI` that backs all surfaces — on top of the fully-deployed v1.3.0 foundation. The milestone is read-only: no mutation, no admin actions, no auth (localhost-only, matching `:9999` posture). The single most important architectural decision — confirmed across ARCHITECTURE.md and PITFALLS.md, and explicitly called out against STACK.md's initial recommendation — is that the console Web UI is served on a separate uvicorn task launched from `_lifespan` on port `:9996`, independent of the MCP transport mode. The alternative (`FastMCP.custom_route`) only functions when the MCP server runs in `--http` transport mode, which would break every existing Claude Desktop and Claude Code configuration that defaults to stdio. Stdio is the locked default; console serves on its own port regardless.

The recommended approach is additive and strictly in-process: one new `forge_bridge/console/` package, one new `forge_bridge/cli/console.py` Typer app, minimal modifications to `server.py` and `watcher.py`, and `jinja2>=3.1` as the only new pip dependency (all other deps — Starlette, uvicorn, sse_starlette, Typer, Rich, httpx — already ship transitively via `mcp[cli]`). The frontend is Jinja2 + htmx 2.x + Alpine.js 3.x, vendored as static files, with zero JavaScript build step. This is the correct choice for a pip-distributed, VFX-studio-deployed package where internet access during package install cannot be assumed and npm has no place in the Python toolchain. Every view in the Web UI and every subcommand in the CLI reads from the same `ConsoleReadAPI` class — single read model, no divergence possible.

The primary risks are transport-related and UX-related, not algorithmic. P-01 (stdout corruption in stdio mode) and P-02 (transport switch breaking Claude Desktop configs) are critical: both are fully mitigated by the separate-uvicorn-task pattern and by preserving stdio as the default. P-03 (MCP resource client incompatibility) is addressed by shipping both `forge://manifest/synthesis` as an MCP resource AND a `forge_manifest_read` tool fallback shim — Cursor and Gemini CLI do not implement resources, and the shim costs one function. P-09 (CLI vs Web UI read-model drift, the same class of bug as LRN-05 from Phase 8) is fully prevented by the `ConsoleReadAPI` singleton before any surface is built. Artist-UX failure modes are explicitly flagged: a 30-second non-developer dogfood check is a required UAT criterion for every UI-touching phase, not a nice-to-have.

---

## Conflict Resolution: Web UI Serving Mechanism

**STACK.md vs ARCHITECTURE.md/PITFALLS.md** — resolved here with explicit rationale.

STACK.md identified `FastMCP.custom_route(path, methods)` as a single-process, single-port option that routes through the same Starlette app as the MCP protocol handler. This is technically correct and verified against `mcp==1.26.0`.

ARCHITECTURE.md and PITFALLS.md (P-01, P-02) identify the critical constraint: `custom_route` ONLY serves traffic when FastMCP runs in `--http` transport mode. The default transport is stdio (required for Claude Desktop and Claude Code compatibility). In stdio mode, `mcp.run()` owns stdout exclusively — any HTTP server started alongside it that writes to stdout corrupts the MCP wire.

**Locked resolution for v1.3:**
- The console uses a separate uvicorn task bound to `:9996`, launched via `asyncio.create_task(serve_uvicorn(console_app, port=9996))` inside `_lifespan`, alongside the existing watcher task.
- Stdio MCP remains the default transport (no `--http` flag = stdio). Claude Desktop and Claude Code configurations are unaffected.
- `custom_route` is viable ONLY if the MCP server is started with `--http` transport. Treat it as a v1.4+ option to consolidate ports when operators explicitly opt into HTTP transport. Do not use it in v1.3.
- PROJECT.md scope description ("served on a new port by the MCP server process") matches the ARCHITECTURE + PITFALLS pattern exactly.

---

## Key Findings

### Recommended Stack

One new pip dependency. Zero new process boundaries. All runtime behavior verified against installed packages.

**Core technologies:**

- **Starlette** (0.52.1, transitive via `mcp[cli]`) — ASGI routing, `StaticFiles`, `JSONResponse`; provides everything needed for the console HTTP API without FastAPI's added weight
- **uvicorn** (0.41.0, transitive via `mcp[cli]`) — programmatic `uvicorn.Server` API used inside an asyncio task; same server FastMCP uses internally, no new dependency
- **Jinja2** (`>=3.1`, NEW — only new pip dep) — server-rendered HTML templates for Web UI; `Starlette.Jinja2Templates` wraps it; not currently installed
- **htmx 2.0.10** (vendored static file, `forge_bridge/console/static/htmx.min.js`) — partial-page HTML swaps, auto-refresh polling, no build step; ~16 KB gzipped
- **Alpine.js 3.x** (vendored static file, `forge_bridge/console/static/alpine.min.js`) — minimal client-side reactive state (tab selection, copy-to-clipboard, collapse panels); ~8 KB gzipped
- **Typer 0.24.1** (transitive via `mcp[cli]`) — CLI subcommand framework; NOTE: async `def` commands are silently dropped — all CLI commands must be sync wrappers calling `httpx.get()` (sync httpx, not asyncio.run)
- **Rich 14.3.3** (transitive via `mcp[cli]`) — terminal tables and panels for CLI output
- **httpx** (already declared in `pyproject.toml`) — CLI HTTP calls to `:9996`; use sync client for simple GETs, no `asyncio.run()` wrapper needed
- **sse_starlette 3.2.0** (transitive via `mcp[cli]`) — `EventSourceResponse` for SSE push if roadmapper scopes it in; zero-cost to add; poll-first recommended for v1.3

**Explicitly rejected:**
- FastAPI — Starlette is already installed; FastAPI adds ~1 MB of dependencies for zero functional gain on a read-only localhost dashboard
- SPA frameworks (React, Svelte, SvelteKit) — require `npm run build` inside a pip package; incompatible with the Python toolchain and offline VFX studio environments
- Tailwind CDN — 3.5 MB unoptimized, "development only" per Tailwind docs, requires internet access
- Second separate process for the console — adds IPC, splits lifespan management, unnecessary complexity

**Palette:** CSS custom properties in `forge-console.css`. `--forge-bg: #242424`, `--forge-amber: #cc9c00`, `--forge-text: #cccccc`. LOGIK-PROJEKT heritage. No Tailwind.

**Key Typer constraint confirmed via live test:** `@app.command()` on an `async def` registers the coroutine but never awaits it (silently returns `RuntimeWarning: coroutine was never awaited`). Use sync outer functions with `httpx.get()` (sync) for all CLI commands that call the console API.

### Expected Features

Five feature categories, each mapping to a Web UI view + CLI subcommand + (for 3 of them) an MCP resource:

| Category | Web UI view | CLI subcommand | MCP resource |
|----------|-------------|----------------|--------------|
| Tools | Tools table | `console tools` | `forge://tools` |
| Executions | Exec history | `console execs` | — |
| Manifest | Manifest browser | `console manifest` | `forge://manifest/synthesis` |
| Health | Health panel | `console health` + `console doctor` | `forge://llm/health` (exists) |
| Chat | Chat surface | — | — |

**Must have (table stakes):**

- **TS-A.1 — Tools table** — filterable list of all registered MCP tools: name, namespace (`flame_*`/`forge_*`/`synth_*`), origin (builtin/synthesized), status (active/quarantined); data from `mcp.list_tools()` + `ProbationTracker`
- **TS-A.2 — Per-tool drilldown** — full description, input schema, provenance fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`), probation history, raw sidecar JSON
- **TS-A.3 — Execution history list** — time-sorted JSONL tail: timestamp, intent, code_hash (truncated), promoted flag; default last 50 rows; filterable by promoted=true and date range
- **TS-A.4 — Health panel** — traffic-light per service: Flame bridge (`:9999`), WebSocket server (`:9998`), LLM backends (Ollama/Anthropic/OpenAI), synthesis watcher
- **TS-A.5 — Manifest view** — tabular view of `.manifest.json`: filename, sha256, loaded/orphaned status, tool name
- **TS-E.1 — Execution drilldown** — full `raw_code`, `intent`, `code_hash`, `promoted` flag, raw JSONL record JSON
- **TS-E.2 — Probation state per tool** — pass/fail counts, quarantine status and reason
- **TS-E.3 — Raw JSONL CLI** — `console execs --raw` outputs NDJSON to stdout for `jq` piping
- **TS-L.1 — `forge://manifest/synthesis`** — JSON manifest of all synthesized tools with full provenance, probation state
- **TS-L.2 — `forge://tools`** — full tool list with `_meta` and annotations as a cacheable MCP resource

**Should have (differentiators):**

- **DF-1 — Structured query console** — input bar accepting `tool:synth_* status:active`, `exec:promoted=true since:7d`; deterministic, no LLM in hot path; preset query chips for artist-friendly access
- **DF-2 — LLM chat layer** — natural-language queries routed through existing `LLMRouter.acomplete()`; manifest + recent exec context injected as system context; graceful degradation when LLM is down
- **DF-3 — `console doctor`** — pre-flight checklist: Flame reachable, WS server reachable, LLM backend healthy, JSONL parseable, manifest valid, synthesized tools loaded, StoragePersistence callback registered; PASS/FAIL/WARN table with actionable fix hints
- **DF-4 — `forge://tools/{name}` resource template** — per-tool detail JSON for single tool by name; trivial once `forge://tools` exists

**Defer to v1.4:**
- DF-5 — Promotion rate sparklines (complex JSONL aggregation by day + tool via code_hash join)
- DF-6 — SSE live updates (poll at 5s is sufficient; SSE infrastructure is zero-cost to add later)
- LLM chat layer (DF-2) may defer to v1.4 depending on roadmapper's phase decision
- `custom_route` consolidation for `--http` transport mode operators

**Locked non-goals (anti-features):**
- No admin/mutation actions in the UI — auth is a prerequisite; deferred to follow-on milestone
- No auth on the console — localhost-bound, same posture as `:9999`
- No ComfyUI-style node graph — dependency graph engine does not exist yet
- No Grafana-style metric cardinality explosion — aggregate aggressively; surface only the 3 artist questions
- No separate DB for the console — reads JSONL + in-memory state directly
- No code editor or synthesis UI — read-only milestone; editing introduces XSS vectors

### Architecture Approach

The console is a single `forge_bridge/console/` package running entirely within the existing MCP server process. A `ManifestService` singleton owns in-memory tool state, injected into the watcher (write path) and the console router (read path). A second uvicorn task on `:9996` serves the console ASGI app, started in `_lifespan` alongside the existing watcher task. The `ConsoleReadAPI` is the exclusive read layer — Web UI handlers, CLI subcommands, and MCP resource functions all call it; zero duplicated query logic across surfaces. This directly prevents the CLI-vs-Web-UI drift pitfall (P-09) and mirrors the LRN-05 lesson from Phase 8 (single read/write path prevents dead seams).

**Major components:**

1. **ManifestService** (`forge_bridge/console/manifest_service.py`) — shared singleton holding `dict[str, ToolRecord]` (stem to provenance record); `asyncio.Lock` for write safety; watcher is the sole writer; console API + MCP resource read via `snapshot()`; instantiated in `_lifespan`, injected into watcher and console router
2. **ConsoleReadAPI** (`forge_bridge/console/read_api.py`) — the ONE read layer; exposes `get_tools()`, `get_executions(limit, since, promoted_only)`, `get_manifest()`, `get_health()`; Web UI HTTP handlers, CLI commands, and MCP resources all call this; never duplicated
3. **Console HTTP app** (Starlette ASGI app, endpoints under `/api/v1/` and static assets at `/ui/`) — served by a background uvicorn task on `:9996` started in `_lifespan`; `StaticFiles` mount for Jinja2 templates + vendored JS/CSS
4. **MCP resources** (`forge_bridge/console/resources.py`) — `register_console_resources(mcp, manifest_service)` called from `_lifespan` after `ManifestService` is ready; registers `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health`; plus `forge_manifest_read` tool fallback shim for clients that do not support resources (P-03)
5. **CLI companion** (`forge_bridge/cli/console.py`) — Typer app registered as `forge-bridge console`; sync commands calling `httpx.get("http://127.0.0.1:9996/api/v1/...")` and formatting with Rich; stateless, no persistent connection
6. **LLM chat endpoint** (`forge_bridge/console/chat.py`) — `POST /api/v1/chat`; builds context from `ManifestService.snapshot()` + `ExecutionLog.snapshot(limit=5)`; calls `LLMRouter.acomplete()` with `asyncio.wait_for(..., timeout=120.0)`; independent sanitization pass strips `raw_code` and injection markers from context

**Modified files (minimal surface):**
- `forge_bridge/mcp/server.py` — `_lifespan`: instantiate `ManifestService`, inject into watcher, start console uvicorn task, call `register_console_resources()`
- `forge_bridge/learning/watcher.py` — `watch_synthesized_tools()` and `_scan_once()` accept `manifest_service: ManifestService | None = None` (backward-compatible, None default)
- `forge_bridge/learning/execution_log.py` — add `snapshot(limit, offset)` method reading from in-memory dicts (no JSONL I/O at query time)
- `forge_bridge/__init__.py` — re-export `ManifestService`, `ToolRecord`; `__all__` grows 16 to ~18-19; minor version bump ceremony applies
- `pyproject.toml` — add `"jinja2>=3.1"`; update `[project.scripts]` for `forge-bridge console` entry point; add `forge_bridge/console/` to `[tool.hatch.build]` includes

**ExecutionLog instance identity gate (Phase 9 precondition):** Confirm the console reads the SAME `ExecutionLog` instance that `bridge.py`'s callback fires against. In the standalone case, `_lifespan` must hold the canonical instance and pass it to both the callback registration path and the console read API. This avoids a repeat of LRN-05.

### Critical Pitfalls

1. **P-01: Stdout corruption in stdio mode** — `mcp.run()` in stdio mode owns stdout exclusively. Any HTTP server started in the same process that writes to stdout corrupts the MCP wire. Prevention: separate uvicorn task on `:9996`; all console output via `logging`, never `print()`. UAT: MCP client completes `tools/list` without errors while Web UI serves traffic on `:9996`.

2. **P-02: Transport switch breaks Claude Desktop configs** — Switching MCP default to `--http` transport silently breaks every `claude_desktop_config.json` entry. Prevention: stdio is the default (no flags = stdio); `--http` is opt-in; Web UI is unavailable in stdio mode. Document this trade-off explicitly.

3. **P-03: MCP resource client incompatibility — no-tool-fallback trap** — Cursor does not support resources; Gemini CLI explicitly excludes resources. If `forge://manifest/synthesis` is the ONLY path to manifest data, these clients have no access. Prevention: ship BOTH `forge://manifest/synthesis` (resource) AND `forge_manifest_read` (tool fallback shim) together in Phase 9.

4. **P-09: CLI vs Web UI read-model drift** — Two surfaces reading the same JSONL and in-memory state via different query paths will produce different numbers on boundary conditions. Artists file "wrong count" bugs that are actually query implementation differences. Prevention: single `ConsoleReadAPI` class is the ONLY path for both surfaces. Implement before any surface. This is the v1.3 architectural invariant.

5. **P-04: JSONL partial-line parse on write boundary** — `fcntl.LOCK_EX` is advisory; a reader that opens the file without the lock can see a partial line. Prevention: `ExecutionLog.snapshot()` reads from in-memory dicts (no file I/O at query time), sidestepping the problem entirely for the hot path. If direct JSONL reads are needed elsewhere, use a position-tracked incremental reader with partial-line carry-over buffer.

6. **P-06/P-07: LLM chat injection + cost runaway** — Context assembled for the chat endpoint must never include `raw_code` from execution records (only `intent` + `code_hash`); tool names and sidecar tags must pass through an independent sanitization pass (separate from `_sanitize_tag()` which covers MCP rendering). Rate limiter: sliding-window 10 RPM per source IP; `asyncio.wait_for(acomplete(), timeout=120.0)`.

7. **Artist-UX failure modes** — Dashboard shows jargon (`promoted=True`, `JSONDecodeError at offset 412`, stats sorted by `code_hash`). Prevention: every UI-touching phase includes a mandatory 30-second non-developer dogfood check. A person who is not the developer must identify the three most recently synthesized tools and their status within 30 seconds of opening the Web UI.

---

## Implications for Roadmap

Based on combined research across all four files, the v1.3 milestone maps to 4-5 phases (numbered Phase 9+ per PROJECT.md continuity from v1.2's Phase 8). The build order is strictly sequential — each phase depends on the HTTP API being stable before UI or CLI surfaces are built on top of it.

### Phase 9: ConsoleReadAPI + ManifestService + MCP Resources + Tool Fallback Shim

**Rationale:** Everything else depends on the read-side API existing and being tested. The MCP resources and tool fallback shim are bundled here because they are small and their data comes directly from `ManifestService.snapshot()`. Building the API and resources together means one release ceremony covers both. This phase also gates on the ExecutionLog instance identity check.

**Delivers:**
- `ManifestService` singleton + `ToolRecord` dataclass
- `ExecutionLog.snapshot(limit, offset)` method (in-memory read, no JSONL I/O)
- `ConsoleReadAPI` — the single read layer for all surfaces
- Console HTTP API skeleton: `/api/v1/manifest`, `/api/v1/executions`, `/api/v1/health`
- `_lifespan` wiring: `ManifestService` instantiation, watcher injection, uvicorn task on `:9996`
- `register_console_resources(mcp, manifest_service)` — `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health`
- `forge_manifest_read` tool fallback shim (P-03 prevention)
- CORS middleware on the console Starlette app

**Addresses:** TS-L.1, TS-L.2, TS-A.4 (health endpoint)
**Avoids:** P-01, P-02, P-03, P-04, P-09, P-10

**UAT criteria:**
- MCP client (`tools/list`) succeeds while console HTTP API is serving traffic on `:9996`
- Existing stdio integration tests pass with no `--http` flag (P-02 check)
- Both `forge_manifest_read` tool path AND `resources/read forge://manifest/synthesis` return correct data from a real MCP session (not mocked)
- `ConsoleReadAPI` and Web UI `/api/v1/manifest` return identical tool counts for the same data
- ExecutionLog instance identity confirmed: live `bridge.execute()` call produces a row visible via `execution_log.snapshot()`

**Research flag:** Standard patterns, no spike needed.

---

### Phase 10: Web UI (Jinja2 Templates + Static Assets + htmx Views)

**Rationale:** The HTTP API from Phase 9 provides the stable contract the Web UI consumes. The Web UI is a read-only consumer — it has no coupling to Phase 11 (chat endpoint) unless the chat panel is included here.

**Delivers:**
- `forge_bridge/console/templates/` — Jinja2 base template + per-view templates
- `forge_bridge/console/static/` — `forge-console.css`, vendored `htmx.min.js`, `alpine.min.js`
- Starlette `StaticFiles` mount and Jinja2 `TemplateResponse` routes at `/ui/`
- View 1: Tools table (TS-A.1) — filterable, namespace color-coded
- View 2: Per-tool drilldown (TS-A.2) — provenance, input schema, probation history, raw sidecar
- View 3: Execution history (TS-A.3) + execution detail drawer (TS-E.1)
- View 4: Manifest browser (TS-A.5) — loaded/orphaned status
- View 5: Health panel (TS-A.4) — traffic-light cards, poll every 10 seconds via htmx
- Structured query console (DF-1) — preset query chips minimum
- `pyproject.toml` package-data includes for templates and static files
- Design contract delivered by `/gsd-ui-phase` tooling

**Uses:** Jinja2, htmx, Alpine.js, LOGIK-PROJEKT palette (`#242424` + `#cc9c00`)
**Avoids:** P-11 (no SPA/npm), P-10 (assets and API co-served from `:9996`)

**UAT criteria:**
- Fresh `pip install forge-bridge` from built wheel + start in HTTP mode + open Web UI in browser — assets load without any npm commands
- Browser `fetch()` calls from Web UI to `/api/v1/` succeed without CORS errors in Chrome and Safari
- Non-developer dogfood: operator identifies three most recently synthesized tools and their status within 30 seconds

**Research flag:** Standard patterns. No spike needed.

---

### Phase 11: CLI Companion (`forge-bridge console <subcommand>`)

**Rationale:** CLI is the thinnest layer — pure formatting of JSON responses from the already-proven console API. Building it after the Web UI means the API contract is tested by real usage before the CLI is written against it. May merge with Phase 10 if the Web UI is lightweight; roadmapper decides.

**Delivers:**
- `forge_bridge/cli/console.py` — Typer app with subcommands: `tools`, `execs`, `manifest`, `health`, `doctor`
- All commands are sync functions calling `httpx.get("http://127.0.0.1:9996/api/v1/...")` (sync httpx)
- Rich table output for all subcommands; `--json` / `--raw` / `--format` flags
- `forge-bridge console doctor` — parallel health checks, PASS/FAIL/WARN table with fix hints (DF-3)
- `pyproject.toml` `[project.scripts]` updated: `forge-bridge` alone starts MCP server; `forge-bridge console <cmd>` runs CLI without starting the server
- `httpx.ConnectError` handling with user-friendly "start the server first" message

**Addresses:** TS-E.3, DF-3
**Avoids:** P-09 (CLI reads from ConsoleReadAPI via HTTP, same data as Web UI)

**UAT criteria:**
- `forge-bridge console tools` output matches `/api/v1/manifest` JSON for same data — zero divergence
- `forge-bridge console doctor` error message is helpful when server is not running
- Non-developer dogfood: operator can answer "what synthesized tools are active?" from the terminal without opening a browser

**Research flag:** Standard patterns. No spike needed.

---

### Phase 12: LLM Chat Endpoint (may defer to v1.4)

**Rationale:** The LLM chat panel depends on Phase 9's `ManifestService` + `ExecutionLog.snapshot()` for context building and Phase 10's Web UI for the chat panel UI. It is the most complex surface and the most likely to be deferred. The rest of the console is fully functional without it. Defer to v1.4 if any earlier phase runs long.

**Delivers (if in scope):**
- `forge_bridge/console/chat.py` — `CONSOLE_SYSTEM_PROMPT`, chat handler, `build_chat_context(records, tool_list, max_bytes=2048)`
- `POST /api/v1/chat` endpoint — `asyncio.wait_for(llm_router.acomplete(), timeout=120.0)`, client-disconnect cancellation
- Independent sanitization pass: injects only `intent` + `code_hash` (never `raw_code`), strips injection markers from tool names and tags
- Sliding-window rate limiter: 10 RPM per source IP, HTTP 429 on breach
- Chat panel in Web UI (htmx form posting to `/api/v1/chat`)
- Graceful degradation: chat panel grayed out when no LLM backend is healthy

**Addresses:** DF-2
**Avoids:** P-06 (injection), P-07 (cost runaway), P-08 (event loop blocking)

**UAT criteria:**
- 11 rapid requests from same IP within 1 minute: 11th returns HTTP 429
- Mocked `LLMRouter.acomplete()` blocked indefinitely: endpoint returns timeout error within 125 seconds
- Tool with injection-marker name does not propagate the marker into LLM context string
- Non-developer dogfood: artist asks "what synthesis tools were created this week?" in plain English and gets a useful answer

**Research flag:** Moderate complexity. Context assembly + sanitization boundary warrants a CONTEXT.md design spike before implementation. Apply the Phase 8 UAT lesson: test the full production call path, not individual seams.

---

### Phase Ordering Rationale

- Phase 9 is the foundation for everything. No UI or CLI surface can be built before the `ConsoleReadAPI`, `ManifestService`, and console HTTP API exist. MCP resources and the tool fallback shim ship here because they are small and their data comes from the same `ManifestService` that Phase 9 creates.
- Phase 10 (Web UI) before Phase 11 (CLI) because the Web UI tests the API contract under real usage. The CLI is the thinnest client and benefits from building against a proven contract.
- Phase 12 (LLM chat) last because it depends on everything else and is the most likely to be deferred. It does not block a functional, artist-usable console.
- Merge options for the roadmapper: Phase 9 + MCP resources may fit in one phase (they share `ManifestService`). Phase 10 + Phase 11 may merge if the Web UI is lightweight.
- Release ceremony timing: `__all__` grows 16 to ~18-19 with `ManifestService` and `ToolRecord`. One minor version bump ceremony at the end of Phase 9 or 10; not one per phase.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 12 (LLM chat):** Context assembly, sanitization boundary, and rate limiter design warrant a CONTEXT.md design spike. The boundary between `_sanitize_tag()` (MCP rendering) and the chat context sanitization pass (different threat model) needs explicit design. Token budget management for the Ollama local model context window also needs a number.
- **Phase 10 (Web UI design contract):** Design contract is owned by `/gsd-ui-phase`. No architecture research needed, but the UI phase agent must be invoked for design deliverables.

Phases with standard patterns (skip research-phase):
- **Phase 9:** `asyncio.create_task` + `uvicorn.Server` programmatic API is documented canonical. `ManifestService` is a simple asyncio-Lock-protected dict. MCP resource registration via `@mcp.resource()` is verified against `mcp==1.26.0`.
- **Phase 11 (CLI):** Typer + httpx + Rich is a well-established stack. The sync-wrapper pattern for Typer 0.24.1 is verified.

---

## Additional Synthesis Notes

Cross-cutting concerns confirmed across multiple research files:

**Shared ConsoleReadAPI is the locked pattern.** All surfaces (Web UI / CLI / MCP resources / LLM chat) read through ONE class. Prevents P-09 and mirrors the LRN-05 lesson from Phase 8 (single read/write path prevents dead seams). Any phase that introduces a second read path is a scope violation.

**Frontend stack: Jinja2 + htmx + Alpine.js, zero-build, vendored static assets.** No npm, no Tailwind CDN. One new pip dep: `jinja2>=3.1`. htmx and Alpine.js are vendored to guarantee offline availability in VFX studio environments.

**CLI: Typer with sync functions calling sync httpx.** Typer 0.24.1 silently drops `async def` commands (verified via live test). Use `httpx.get()` (sync) for CLI to console API calls.

**ManifestService singleton owns in-memory tool state.** Injected into watcher (write path) and console router (read path). Disk `.sidecar.json` is persistent truth; ManifestService is the in-memory consistent view. Watcher calls `manifest_service.register()` AFTER `register_tool()` succeeds — the manifest never contains a tool that is not registered.

**MCP resource + tool fallback shim MUST ship together.** `forge_manifest_read` tool alongside `forge://manifest/synthesis` keeps the surface usable for all MCP clients. These are one deliverable in Phase 9, not two.

**Artist-UX UAT criterion is mandatory, not optional.** Every UI-touching phase must include a 30-second non-developer dogfood check. This captures the failure class that pure engineering tests cannot detect.

**Feature categories locked: TOOLS / EXECS / MANIFEST / HEALTH / CHAT.** Each maps to a Web UI view + CLI subcommand + (for 3 of them) an MCP resource. `forge-bridge console doctor` is table stakes.

**Build order:** Phase 9 (ConsoleReadAPI + MCP resources + tool fallback shim) to Phase 10 (Web UI) to Phase 11 (CLI) to Phase 12 (LLM chat, may defer). Roadmapper may merge Phase 10 + 11 if thin enough.

**ExecutionLog instance identity gate.** Phase 9 precondition: confirm the console reads the SAME `ExecutionLog` instance that `bridge.py`'s callback fires against. `_lifespan` must hold the canonical instance and pass it to both the callback registration path and the console read API. This must be an explicit Phase 9-01 task.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All runtime behavior verified against installed packages (`mcp==1.26.0`, `starlette==0.52.1`, `typer==0.24.1`). Typer async constraint confirmed via live test. One new dep (`jinja2>=3.1`) is straightforward. |
| Features | HIGH | Feature scope from direct codebase analysis + PROJECT.md + reference UI pattern analysis (Temporal, Dagster, Prefect, ComfyUI, Grafana). Artist-vs-engineer split is well-grounded. |
| Architecture | HIGH | Integration points from direct source reads of `server.py`, `watcher.py`, `execution_log.py`, `bridge.py` at v1.3.0. Component boundaries and data flows derived from existing code, not speculation. |
| Pitfalls | HIGH | Conflict between STACK.md and ARCHITECTURE/PITFALLS.md is unambiguous — separate uvicorn task wins. Security pitfalls grounded in Phase 8 UAT lessons (LRN-05) and prior art (CyberArk, MCP injection CVEs). |

**Overall confidence:** HIGH

### Gaps to Address During Planning

- **SSE vs poll scope decision** — PROJECT.md flags this as open. Research recommends poll-first (5s htmx `hx-trigger`); SSE is zero-cost to add if real-time feed is required. Roadmapper must decide before Phase 10 CONTEXT.md.
- **Phase 10 + 11 merge decision** — both may be thin enough to ship as one. Roadmapper evaluates estimated task count once Phase 9 scope is finalized.
- **Phase 12 (LLM chat) scope decision** — defer to v1.4 or include in v1.3? Roadmapper gates this on Phase 9-10-11 execution confidence.
- **`forge-bridge` entry point wiring** — current `pyproject.toml` calls `mcp.run()` directly. Must be refactored to a Typer top-level app: bare `forge-bridge` = start MCP server; `forge-bridge console <cmd>` = CLI without starting server. Phase 9 design decision requiring explicit CONTEXT.md lock.
- **`hatch.build` includes for static assets** — Jinja2 templates and vendored JS/CSS must survive wheel packaging. Verify `[tool.hatch.build.targets.wheel]` glob includes `forge_bridge/console/` subdirs. Phase 10 "looks done but isn't" checklist item.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `forge_bridge/mcp/server.py`, `forge_bridge/learning/watcher.py`, `forge_bridge/learning/execution_log.py`, `forge_bridge/bridge.py`, `forge_bridge/__init__.py` (v1.3.0 working tree)
- Direct package inspection — `mcp==1.26.0` (`FastMCP.custom_route`, `@mcp.resource()`, route merge behavior verified), `starlette==0.52.1`, `typer==0.24.1` async behavior (live test)
- `.planning/PROJECT.md` (v1.3 milestone scope, locked non-goals, design contract)
- FastMCP docs (Context7 `/prefecthq/fastmcp`) — transport protocols, custom routes, HTTP mode vs stdio mode constraints
- MCP Python SDK (Context7 `/modelcontextprotocol/python-sdk`) — resource decorator, URI templates
- MCP Specification 2025-06-18 — Resources section

### Secondary (MEDIUM confidence)
- FastMCP: Running Your Server — gofastmcp.com/deployment/running-server — custom_route only in HTTP transport; stdio owns stdout exclusively
- htmx 2.0.10 release — github.com/bigskysoftware/htmx/releases (2026-04-22)
- Alpine.js 3.x — releasebot.io/updates/alpinejs (April 2026 release)
- Tailwind Play CDN "development only" — tailwindcss.com/docs/installation/play-cdn
- Temporal UI, Dagster asset catalog, Prefect flow runs dashboard, ComfyUI App Mode — reference UI pattern analysis
- Grafana anti-pattern analysis — Tempo dashboard cited
- npm doctor, React Native CLI doctor — `console doctor` pattern precedent
- Gemini CLI resources issue #3816 — resources not supported
- Cursor MCP resources forum — resources not supported
- LLM API cost runaway patterns — $47K incident (tianpan.co/blog)
- sse-starlette heartbeat + proxy patterns — github.com/sysid/sse-starlette
- CyberArk "Poison Everywhere" — injection surfaces in MCP schema fields

---
*Research completed: 2026-04-22*
*Supersedes: SUMMARY-v1.2.md (v1.2 Observability & Provenance milestone)*
*Ready for roadmap: yes — 4-5 phases (9-12), strictly sequential, single-repo milestone*
