# Requirements — v1.3 Artist Console

**Milestone:** v1.3 Artist Console
**Goal:** Make forge-bridge legible to its operator — ship an artist-first Web UI + CLI console that surfaces the synthesis manifest, execution history, provenance, and live tool state, backed by a canonical MCP resource that any consumer can read.
**Opened:** 2026-04-22

---

## v1.3 Requirements

Grouped by category. REQ-ID format: `[CATEGORY]-[NUMBER]`. Numbering restarts per category (v1.3 introduces new category prefixes — `TOOLS`, `EXECS`, `MFST`, `HEALTH`, `API`, `CONSOLE`, `CLI`, `CHAT`).

### API — Shared read-side plumbing (foundation for every surface)

- [ ] **API-01**: A `ConsoleReadAPI` class is the sole read path for Web UI, CLI, MCP resources, and chat — unit-tested in isolation; mirrors the LRN-05 lesson (single path prevents dead seams).
- [ ] **API-02**: HTTP API is served on `:9996` (configurable via env var + flag) via a separate `uvicorn` task launched from `_lifespan`, alongside the MCP server and watcher — independent of MCP transport mode (stdio or `--http`).
- [ ] **API-03**: API routes live under `/api/v1/` namespace and return JSON; route surface: `/api/v1/tools`, `/api/v1/execs`, `/api/v1/manifest`, `/api/v1/health`, `/api/v1/chat`.
- [ ] **API-04**: `_lifespan` owns the canonical `ExecutionLog` and `ManifestService` instances; all surfaces share them (instance-identity gate — no duplicate instances anywhere in the process).
- [ ] **API-05**: Optional `StoragePersistence` read-adapter mirrors the write-side Protocol shape (opt-in); when unregistered, the API reads JSONL only (JSONL is canonical per STORE-06).
- [ ] **API-06**: Console port fallback degrades gracefully — if `:9996` is unavailable, log a WARNING and boot the MCP server anyway (mirrors the v1.2.1 `startup_bridge` degradation pattern).

### TOOLS — Browse registered tools with provenance

- [ ] **TOOLS-01**: User can browse all registered tools (`flame_*`, `forge_*`, `synth_*`) in the Web UI with filters for origin (builtin / synthesized), namespace prefix, and `readOnlyHint`.
- [ ] **TOOLS-02**: User can drill into a single tool and see canonical `_meta` provenance — `origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`, consumer tags — plus raw source for synth tools.
- [ ] **TOOLS-03**: `forge-bridge console tools` subcommand lists tools with the same data and filter flags as the Web UI view.
- [ ] **TOOLS-04**: `forge://tools` and `forge://tools/{name}` MCP resources expose the same data to LLM agents; a `forge_tools_read` tool fallback shim is registered alongside for clients that don't support resources (Cursor, Gemini CLI).

### EXECS — Execution history

- [ ] **EXECS-01**: User can browse execution history in the Web UI with pagination (`limit`/`offset`) and filters (tool name, time range, promoted flag, code_hash prefix).
- [ ] **EXECS-02**: User can drill into a single execution to see `code_hash`, `timestamp`, `raw_code`, `intent`, and (when SQL read-adapter is registered) SQL-mirror row linkage.
- [ ] **EXECS-03**: `forge-bridge console execs` subcommand returns the same view — default last 50 records, `--json` for scripting, `--since` for time-range filtering.
- [ ] **EXECS-04**: Execution data reads through the shared `ConsoleReadAPI` (API-01) — no per-surface JSONL parsers.

### MFST — Synthesis manifest as canonical artifact

- [ ] **MFST-01**: A `ManifestService` singleton owns the in-memory synthesis manifest (tool list + sidecar metadata + probation state); it is injected into the registry watcher and the console router so disk `.sidecar.json` ↔ in-memory ↔ MCP-response stay consistent by construction.
- [ ] **MFST-02**: `forge://manifest/synthesis` MCP resource returns the full manifest as JSON for LLM agents.
- [ ] **MFST-03**: A `forge_manifest_read` MCP tool fallback shim exposes the same manifest for clients that don't support resources — ships in the SAME plan as MFST-02.
- [ ] **MFST-04**: Web UI manifest browser shows the manifest in a sortable, filterable table with per-entry drilldown (raw JSON + pretty view).
- [ ] **MFST-05**: `forge-bridge console manifest` subcommand returns the manifest as JSON or a human-formatted Rich table.
- [ ] **MFST-06**: The `ManifestService` satisfies EXT-01 ("shared synthesis manifest between repos") — projekt-forge and other consumers read the manifest via MCP resource and/or console HTTP API, not by duplicating in-memory state.

### HEALTH — Bridge / router / watcher / storage status

- [ ] **HEALTH-01**: Web UI health panel shows liveness for: MCP server, Flame HTTP bridge (`:9999`), standalone WebSocket (`:9998`), LLM router backends (Ollama + Anthropic/OpenAI per config), storage callback (if attached), registry watcher, console port (`:9996`).
- [ ] **HEALTH-02**: `forge-bridge console health` subcommand returns the same status (human-readable Rich panel or `--json`).
- [ ] **HEALTH-03**: `forge-bridge console doctor` runs an expanded diagnostic — HEALTH-01 checks + manifest validation + JSONL parsability + probation summary + actionable remediation hints. Non-zero exit on any failure for CI gating.
- [ ] **HEALTH-04**: Health surfaces in a persistent compact header strip on every Web UI view so status is visible at a glance.

### CONSOLE — Web UI shell + structured query

- [ ] **CONSOLE-01**: Web UI is served as Jinja2 templates + vendored `htmx` + vendored `Alpine.js` static assets — zero JS build step, offline-capable studio installs supported. Only new pip dep: `jinja2>=3.1`.
- [ ] **CONSOLE-02**: Web UI design follows the `UI-SPEC.md` design contract produced by `/gsd-ui-phase`; palette inherits `#242424` base + `#cc9c00` amber from LOGIK-PROJEKT `modular_dark_theme`, translated to web idioms.
- [ ] **CONSOLE-03**: Primary interaction is a structured query console (command/filter input) that drives the view surface deterministically — no LLM in the hot path.
- [ ] **CONSOLE-04**: Navigation covers all five category views (tools, execs, manifest, health, chat) plus per-entry drilldowns, with URL-addressable state so views are shareable.
- [ ] **CONSOLE-05**: Every UI-touching phase includes a non-developer ("artist") dogfood UAT as part of its verification — catches the artist-UX failure class that unit tests miss (cf. retrospective lesson).

### CLI — Console CLI companion

- [ ] **CLI-01**: `forge-bridge` is wired as a Typer entry-point with `console` subcommand dispatch; subcommands: `tools`, `execs`, `manifest`, `health`, `doctor`.
- [ ] **CLI-02**: CLI calls the console HTTP API on `:9996` via sync `httpx` — all command bodies are sync (Typer 0.24.1 silently drops `async def`).
- [ ] **CLI-03**: Every CLI subcommand supports `--json` (machine-readable) and `--help` with concrete usage examples.
- [ ] **CLI-04**: CLI output uses `rich` for human-readable rendering (tables, panels) when stdout is a TTY; plain text otherwise.

### CHAT — LLM chat surface (last, defer-if-needed)

- [ ] **CHAT-01**: `/api/v1/chat` endpoint accepts user messages and returns LLM responses via `LLMRouter.acomplete()` (streaming optional; poll-over-complete-response is acceptable).
- [ ] **CHAT-02**: Chat system-prompt assembly uses `ConsoleReadAPI` data (recent execs summary, manifest excerpt, health status) as deterministic context; user messages are sanitized at the prompt-boundary.
- [ ] **CHAT-03**: Web UI chat panel is a second surface over the read API — it does not replace the structured query console.
- [ ] **CHAT-04**: Chat has a per-session token budget / cost cap to prevent runaway generation; caller sees a clear "budget exhausted" response rather than silent truncation.

---

## Future Requirements (deferred to v1.4+)

- Real-time streaming push (SSE or WebSocket) for execs, manifest changes, health — poll is sufficient for v1.3.
- Multi-project console view — single-bridge/single-project in v1.3; multi-project is a consumer concern.
- Promotion sparklines / rich historical charts.
- Admin / mutation actions (quarantine, promote, kill) — paired with the auth milestone.
- Maya / editorial manifest producers — Flame stays the only producer in v1.3.
- Consolidating the console onto FastMCP's `custom_route` (only viable when the MCP server runs in `--http` transport; stdio compatibility is the v1.3 default).

---

## Out of Scope (explicit exclusions)

- **Auth** — localhost-bound console, same posture as `:9999`; deferred to a dedicated auth milestone.
- **Admin / mutation actions in the UI** — read-only milestone; pairs with auth.
- **Writing to JSONL from the console** — console is strictly a reader.
- **`LLMRouter` hot-reload** — locked non-goal carried from v1.1.
- **Shared-path JSONL writers across processes** — locked non-goal carried from v1.1.
- **Non-local network access** — console is localhost-bound; cloud/network remains out of scope project-wide.

---

## Traceability

*Filled by the roadmapper once ROADMAP.md is written. Phase numbering continues from v1.2 — v1.3 starts at Phase 9.*

| REQ-ID | Phase | Status |
|--------|-------|--------|
| _(pending roadmap)_ | — | — |

---

*Last updated: 2026-04-22 — v1.3 requirements opened; roadmap pending*
