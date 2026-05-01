# CLAUDE.md — forge-bridge Context Recovery

This file exists to get an AI assistant (Claude or otherwise) back up to speed on this project quickly when context is lost between sessions. Read this first, then read the docs in order listed below.

---

## What is this project?

forge-bridge is **middleware** — a protocol-agnostic communication bus for post-production pipelines. Any piece of software (Flame, Maya, editorial systems, shot tracking, AI models, custom scripts) can connect to it and communicate through a shared canonical vocabulary.

It is NOT a Flame utility. Flame is one endpoint. Everything is another.

The core ideas:
1. **Canonical vocabulary** — bridge speaks a defined language. Every connected system maps its native terms to this language. See `docs/VOCABULARY.md`.
2. **Automatic dependency graph** — as data flows through bridge, it parses relationships and builds a dependency graph. No manual declaration needed. Change propagation is automatic.
3. **Endpoint parity** — Flame, Maya, an LLM, a shot tracking system are all equal endpoints. Bridge does not prefer any of them.
4. **Local first** — starts as a local service, designed to scale later without architecture changes.

---

## Current State

Shipped at v1.4.1 (2026-04-30). 19 phases across 6 milestones (v1.0 → v1.4.x). ~40,594 LOC. 19 symbols in `forge_bridge.__all__`. The v1.5 Legibility milestone is open (Phases 20-23) — see `.planning/STATE.md` for the live cursor.

### What exists and works

**Five user-facing surfaces, all live:**

1. **Flame HTTP bridge** (`flame_hooks/forge_bridge/scripts/forge_bridge.py`)
   - Runs inside Flame as an HTTP server on port 9999
   - Accepts Python code via `POST /exec`, executes on Flame's main thread via `schedule_idle_event`
   - Returns `{result, stdout, stderr, error, traceback}` as JSON
   - Has an interactive web UI at `http://localhost:9999/`
   - Persistent namespace across requests
   - Installed via `./scripts/install-flame-hook.sh`

2. **MCP server** (`forge_bridge/mcp/server.py`)
   - Model Context Protocol server (FastMCP, stdio default)
   - Entry point: `python -m forge_bridge` (wired through `forge_bridge/__main__.py`)
   - Co-hosts the Artist Console + chat endpoint on `:9996` via lifespan
   - Tools: project, timeline, batch, publish, utility — plus staged-ops tools (`forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`), manifest tools (`forge_manifest_read`, `forge_tools_read`), and any LLM-synthesized tools registered by the learning pipeline
   - Resources: `forge://manifest/synthesis`, `forge://staged/pending`, `forge://llm/health`

3. **Artist Console / Web UI** (`forge_bridge/console/app.py`) — Phase 10/10.1
   - Mount: `http://localhost:9996/ui/`
   - Five views: tools, execs, manifest, health, chat
   - Jinja2 + vendored htmx + Alpine.js with SRI; zero JS build step
   - LOGIK-PROJEKT amber-on-dark palette (UI-SPEC.md design contract)
   - Co-hosted with the MCP server on `:9996` via lifespan (NOT FastMCP `custom_route`)

4. **CLI `forge-bridge`** (`forge_bridge/__main__.py` + `forge_bridge/cli/`) — Phase 11
   - Typer + Rich, sync `httpx` consumer of the `:9996` Read API
   - Subcommands: `forge-bridge console tools | execs | manifest | health | doctor`
   - `--json` short-circuits Rich (P-01 stdout purity)
   - Locked exit codes: 0=ok, 1=fail, 2=unreachable

5. **Chat endpoint** (`forge_bridge/console/handlers.py:chat_handler`) — Phase 16/16.1/16.2
   - `POST http://localhost:9996/api/v1/chat`
   - Agentic tool-call loop via `LLMRouter.complete_with_tools()` (Phase 15 / FB-C)
   - `sensitive=True` hardcoded → routes through local Ollama (`qwen2.5-coder:32b`); `ANTHROPIC_API_KEY` not required for chat
   - Rate limit: 10 req/60s (IP-keyed; SEED-AUTH-V1.5 plants caller-identity migration)
   - Outer wall-clock 125s (FB-C 120s inner + 5s framing buffer)

**Subsystems behind the surfaces:**

- **Canonical vocabulary layer** (`forge_bridge/core/`) — `vocabulary.py`, `entities.py`, `traits.py`, `registry.py`. Project → Sequence → Shot → Version → Media + Stack/Layer/Asset, plus Versionable/Locatable/Relational traits. **Shipped** (was on the "not yet implemented" list in v1.0; corrected here).
- **WebSocket server** (`forge_bridge/server/`) — wire protocol, connection management, event-driven hooks. Standalone WS server on `:9998` (graceful degradation if unreachable per Phase 07.1).
- **Postgres persistence layer** (`forge_bridge/store/` + Alembic migrations in `forge_bridge/store/migrations/`) — entities, relationships, events, registry, and the `staged_operation` table from FB-A.
- **Async/sync client pair** (`forge_bridge/client/`) — `AsyncClient` + `SyncClient` for connecting to the WS server.
- **Learning pipeline** (`forge_bridge/learning/`) — execution log (JSONL source of truth at `~/.forge-bridge/executions.jsonl`), threshold-driven promotion, LLM synthesizer (Ollama backend), registry watcher, probation system. SQL mirror via `StoragePersistence` Protocol (Phase 8) — JSONL-authoritative, SQL eventual.
- **LLM router** (`forge_bridge/llm/router.py`) — `LLMRouter` with `acomplete()` and `complete_with_tools()`; sensitive routing to local Ollama vs. cloud Anthropic; hard caps (8 iterations, 120s wall-clock, 30s per-tool); `LLMLoopBudgetExceeded` / `RecursiveToolLoopError` / `LLMToolError` exported from the public API.
- **Staged operations platform** (`forge_bridge/store/staged_operation.py` + console + MCP wiring) — `proposed → approved → executed/rejected/failed` state machine. Approval is bookkeeping; the proposer subscribes to events and executes against its own domain.
- **Tool provenance** — every synthesized tool carries `_meta.forge-bridge/*` fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`); `annotations.readOnlyHint=False` always; sanitization at the read boundary (single-source `_sanitize_patterns.py` shared across Phase 7 + FB-C).

### What is designed but not yet implemented

- Dependency graph traversal engine (relationships exist in the schema via FK + `DBEvent` rows, but no graph-traversal module)
- Bridge core service as a separate router process
- Canonical event-driven pub/sub abstraction (the WebSocket server ships; the canonical pub/sub layer on top of it does not)
- Maya endpoint
- Editorial / shot-tracking adapters
- Authentication (deferred — SEED-AUTH-V1.5; v1.6+ scope)

---

## Repository Layout

```
forge-bridge/
├── CLAUDE.md               ← YOU ARE HERE
├── README.md               ← Project overview, install quick-start
├── pyproject.toml          ← Package config (version, deps, extras [dev], [llm], [test-e2e])
├── alembic.ini             ← DB migration config (sync URL; reads FORGE_DB_URL or hardcoded forge:forge@localhost)
│
├── forge_bridge/                ← Python package
│   ├── __init__.py             ← Public __all__ (19 symbols)
│   ├── __main__.py             ← Typer app: `forge-bridge` CLI + `python -m forge_bridge` MCP entry
│   ├── bridge.py               ← HTTP client to Flame bridge (`bridge.execute()` etc.)
│   ├── cli/                    ← Typer + Rich subcommands (tools, execs, manifest, health, doctor)
│   ├── client/                 ← Async/sync WS clients
│   ├── console/                ← Artist Console (Web UI on :9996, /api/v1/chat handler, app.py mount)
│   ├── core/                   ← Canonical vocabulary (entities, traits, registry, vocabulary)
│   ├── flame/                  ← Flame-specific helpers shared across tools
│   ├── learning/               ← Execution log, synthesizer, watcher, probation
│   ├── llm/                    ← LLMRouter, tool adapters (Ollama, Anthropic), sanitization
│   ├── mcp/                    ← FastMCP server + tool registry (the canonical MCP server lives HERE, not in server.py)
│   ├── server/                 ← WebSocket server + protocol
│   ├── store/                  ← Postgres entities, sessions, Alembic migrations, staged_operation
│   └── tools/                  ← MCP tool implementations: project, timeline, batch, publish, utility
│
├── flame_hooks/             ← Installs into Flame's Python hooks dir
│   └── forge_bridge/
│       └── scripts/
│           └── forge_bridge.py   ← HTTP server running inside Flame on :9999
│
├── scripts/
│   └── install-flame-hook.sh    ← Deploys the Flame hook (defaults pinned to v1.4.1)
│
├── tests/                   ← pytest suite (test_*.py); see tests/llm/, tests/integration/, tests/console/
│
└── docs/
    ├── INSTALL.md          ← Canonical install guide (Phase 20 ships this)
    ├── VOCABULARY.md       ← The canonical language
    ├── ARCHITECTURE.md     ← Design decisions
    ├── API.md              ← HTTP API for the Flame bridge endpoint
    ├── ENDPOINTS.md        ← How to write new endpoint adapters
    ├── DATA_MODEL.md       ← Domain reference
    └── FLAME_API.md        ← Domain reference
```

**Note:** `forge_bridge/server.py` (top-level file, NOT the `server/` directory) is a pre-Phase-5 orphan — broken imports, not re-exported, not runtime-imported. The canonical MCP server lives at `forge_bridge/mcp/server.py`. Tracked as a follow-up dead-code cleanup.

---

## Key Design Decisions (brief version)

Full reasoning in `docs/ARCHITECTURE.md`.

| Decision | What | Why |
|----------|------|-----|
| HTTP transport | Flame bridge uses HTTP | Universal compatibility, easy debug, web UI free |
| Code execution not RPC | Bridge passes Python strings to Flame | Flame API is large/changing. Structured wrappers on top. |
| Automatic dependency graph | No manual declaration | Manual = always incomplete. Infer from data structure. |
| Traits (Versionable, Locatable, Relational) | Cross-cutting capabilities | Same behavior shared across entity types, not reimplemented per type. |
| Auth deferred | Not implemented yet | Local only for now. Framework accommodates it. |
| Local first | No cloud/network initially | Avoid premature complexity. Swappable later. |

---

## Vocabulary Summary

Entities: Project → Sequence → Shot → Version → Media

Stack = group of Layers that belong to the same Shot, each with a Role
Layer = member of a Stack, carries a Role (primary/reference/matte/etc.)
Asset = non-shot thing used in shots (characters, elements, textures)

Traits (cross-cutting):
- Versionable — can have numbered iterations
- Locatable — has path-based addresses (multiple locations possible)
- Relational — can declare and traverse relationships to other entities

Dependency: Relational + consequences. "If this changes, these are affected."

Full spec: `docs/VOCABULARY.md`

---

## Relationship to projekt-forge

- projekt-forge: project management + pipeline orchestration frontend for Flame
- forge-bridge: the communication infrastructure everything connects to

forge-bridge was extracted from projekt-forge when it became clear it needed to be a standalone platform.

projekt-forge repo: https://github.com/cnoellert/projekt-forge

---

## How to Get Running

See `docs/INSTALL.md` for the canonical operator-workstation install path. Quick reference:

```bash
# 1. conda env (matches the reference deployment)
conda create -n forge python=3.11 -y
conda activate forge

# 2. Install with the LLM extras (mandatory for chat + synthesis)
pip install -e ".[dev,llm]"

# 3. Install the Flame hook
./scripts/install-flame-hook.sh
# or standalone: curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh | bash

# 4. Run migrations (defaults to forge:forge@localhost:5432/forge_bridge — set FORGE_DB_URL to override)
alembic upgrade head

# 5. Run the MCP server + co-hosted Web UI + chat endpoint on :9996
python -m forge_bridge
# On a headless host where stdin closes immediately:
tail -f /dev/null | python -m forge_bridge

# 6. Smoke-test the surfaces
curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"   # Web UI → 200
curl -s   http://localhost:9999/status                                  # Flame hook → JSON with flame_available
forge-bridge console doctor                                             # CLI + post-install diagnostic
```

`ANTHROPIC_API_KEY` is **optional** — the chat endpoint hardcodes `sensitive=True`, which routes through local Ollama (`qwen2.5-coder:32b`). The key is only needed for `sensitive=False` cloud routing (not the daily operator workflow).

**Do not use `qwen3:32b` as the default model.** It exceeds the 60s wall-clock budget due to thinking-mode token verbosity (SEED-DEFAULT-MODEL-BUMP-V1.4.x).

---

## Active Development Context

Milestone: **v1.5 Legibility** (opened 2026-04-30; see `.planning/STATE.md` for the live cursor).

Theme: make forge-bridge usable by its first daily user — close the gap between what's shipped (19 phases, 5 surfaces, ~40k LOC) and what a person can sit down and actually use without re-deriving the deployment topology each time. Four phases:

- **Phase 20** (current) — Reality Audit + Canonical Install: ships `docs/INSTALL.md`, refreshes README install section + this `CLAUDE.md` ground-truth, pins `install-flame-hook.sh` default to `v1.4.1`. Forcing function: a non-author UAT must pass on a fresh conda env.
- **Phase 21** — Surface Map + Concept Docs: ships `docs/GETTING-STARTED.md`, rewrites README "What This Is", documents the projekt-forge consumer relationship.
- **Phase 22** — Daily Workflow Recipes: 6 step-by-step recipes (first-time setup, Claude Desktop wiring, tool synthesis, Flame chat automation, staged-ops approval, manifest inspection).
- **Phase 23** — Diagnostics + Recovery: ships `docs/TROUBLESHOOTING.md`; in-flight `forge doctor` polish if recipe authoring surfaces gaps.

**v1.5 constraints:** Legibility, not features. No new external libraries. Public `forge_bridge.__all__` stays at 19 unless an install audit surfaces a genuine need. All v1.5+ planted seeds (`SEED-OPUS-4-7-TEMPERATURE-V1.5`, `SEED-AUTH-V1.5`, `SEED-DEFAULT-MODEL-BUMP-V1.4.x`, `SEED-CHAT-STREAMING-V1.4.x`, etc.) defer to v1.6+.

**Don't break:** the Flame hook + MCP server + Artist Console + CLI + chat endpoint are all in production use on assist-01. Refactoring during a docs milestone is out of scope unless the install audit explicitly surfaces a code gap that blocks the operator path (CONTEXT.md D-04).

---

## Questions To Come Back To

1. What format should bridge use for inter-service messages? JSON? MessagePack? Something else?
2. Should the bridge core service be a single process or multiple cooperating processes?
3. When is a Unix socket preferable to HTTP for same-machine communication?
4. What does the bridge core service look like from an endpoint's perspective — is it a library you import or a service you connect to?
