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

Shipped at tag `v1.4.1` (2026-04-30). `pyproject.toml` version is still `1.4.1` — v1.5 + v1.6 work has shipped reader docs (INSTALL.md, GETTING-STARTED.md, RECIPES.md, TROUBLESHOOTING.md), observability extensions (`postgres` + `graph_store` doctor rows, `ollama-turn` log line), chat-layer convergence (default model bump, SSE streaming, K=2 termination trigger), and operator surfaces (`fbridge flame-exec`, `fbridge graph list/show`) — all as patch-equivalent against the 1.4.1 baseline without API surface change. 19 symbols in `forge_bridge.__all__` (byte-identical from v1.4.x close through v1.6 Phase 24.4). The v1.5 Legibility milestone CLOSED 2026-05-14; the v1.6 Operability milestone is ACTIVE (phases 24, 24.1, 24.2, 24.3, 24.4 shipped; 24.5 anticipated) — see `.planning/STATE.md` for the live cursor.

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
   - Model Context Protocol server (FastMCP, streamable-HTTP for daemon mode, stdio for Claude Desktop / Code)
   - Daily launch: `fbridge up` (managed background daemon — starts `mcp_http` with co-hosted Console on `:9996` + `state_ws` on `:9998` in dependency order) or `fbridge mcp http` (direct foreground). For supervised systemd / launchd, `sudo ./scripts/install-bootstrap.sh`.
   - Claude Desktop / stdio MCP clients: `fbridge mcp stdio` (or `python -m forge_bridge mcp stdio`).
   - **Bare `python -m forge_bridge` now prints help and exits 0** — it does NOT start any services. Use the `mcp stdio` / `mcp http` subcommands.
   - Co-hosts the Artist Console + chat endpoint on `:9996` via lifespan
   - Tools: project, timeline, batch, publish, utility — plus staged-ops tools (`forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`), manifest tools (`forge_manifest_read`, `forge_tools_read`), and any LLM-synthesized tools registered by the learning pipeline
   - Resources: `forge://manifest/synthesis`, `forge://staged/pending`, `forge://llm/health`

3. **Artist Console / Web UI** (`forge_bridge/console/app.py`) — Phase 10/10.1
   - Mount: `http://localhost:9996/ui/`
   - Five views: tools, execs, manifest, health, chat
   - Jinja2 + vendored htmx + Alpine.js with SRI; zero JS build step
   - LOGIK-PROJEKT amber-on-dark palette (UI-SPEC.md design contract)
   - Co-hosted with the MCP server on `:9996` via lifespan (NOT FastMCP `custom_route`)

4. **CLI `fbridge` / `forge-bridge`** (`forge_bridge/cli/main.py` is the Typer front door; `__main__.py` is a thin delegate to it) — Phase 11, expanded through v1.4.x + v1.6 Phase 24.x
   - Both `fbridge` (canonical short name) and `forge-bridge` (back-compat alias) resolve to `forge_bridge.cli.main:app` (see `pyproject.toml` `[project.scripts]`)
   - Typer + Rich, sync `httpx` consumer of the `:9996` Read API for read commands; direct calls to the runtime manager / chain engine for write commands
   - Top-level subcommands: `doctor` (runtime doctor — covers Console, MCP, Flame, State WS, **`postgres`** (Phase 23), **`graph_store`** (Phase 24); Flame probe is **daemon-routed** via `POST :9996/api/v1/exec text="flame_ping"` since Phase 24.2), `actions` (browse registered tools), `chat` (exercise the chat endpoint), `exec` (deterministic chain engine via `/api/v1/exec`, no LLM), `run` (execute a registered tool by exact name), **`flame-exec`** (Phase 24 — operator surface onto `_execute_python_core` shared body; same dispatch substrate as the LLM tool-call path; emits `graph_id`), **`graph list / graph show`** (Phase 24 — read-only debug CLI over the JSONL graph store at `~/.forge-bridge/graphs/`), `up` / `down` / `status` (managed background daemon lifecycle)
   - Subgroups: `console` (legacy Phase-11 Read API browser: `tools | execs | manifest | health | doctor`), `mcp` (`stdio | http`), `flame` (`ping`)
   - `--json` short-circuits Rich on every command (P-01 stdout purity)
   - Locked exit codes: 0=ok, 1=fail, 2=unreachable (`flame-exec` adds 1=Flame-error, 2=transport)

5. **Chat endpoint** (`forge_bridge/console/handlers.py:chat_handler`) — Phase 16/16.1/16.2 + v1.6 Phase 24.3 + 24.4
   - `POST http://localhost:9996/api/v1/chat`
   - Agentic tool-call loop via `LLMRouter.complete_with_tools()` (Phase 15 / FB-C); now with K=2 canonical-recurrence termination at the orchestrator-side D-07 site (Phase 24.4)
   - `sensitive=True` hardcoded → routes through local Ollama (default model **`qwen2.5-coder:14b`** — bumped from `32b` in Phase 24.3 per measure-first canonical baseline); `ANTHROPIC_API_KEY` not required for chat
   - **Transport:** JSON response by default; **SSE history-grows streaming** when client sends `Accept: text/event-stream` (Phase 24.3; 4.4ms first-byte vs 120s budget; JSON path preserved byte-equivalent)
   - **Terminal SSE event taxa (Phase 24.4):** `event: done` = model-decided completion / `event: orchestration_terminated` = policy-decided termination (K=2 canonical-recurrence trigger fired; envelope carries distinct `stop_reason` + `trigger=k_fold_canonical` + `k_count` + `result_hash`) / `event: error` = transport / runtime failure
   - Rate limit: 10 req/60s (IP-keyed; SEED-AUTH-V1.5 plants caller-identity migration)
   - Outer wall-clock 125s (FB-C 120s inner + 5s framing buffer); on `orchestration_terminated` the loop ends before budget exhaustion

**Subsystems behind the surfaces:**

- **Canonical vocabulary layer** (`forge_bridge/core/`) — `vocabulary.py`, `entities.py`, `traits.py`, `registry.py`. Project → Sequence → Shot → Version → Media + Stack/Layer/Asset, plus Versionable/Locatable/Relational traits. **Shipped** (was on the "not yet implemented" list in v1.0; corrected here).
- **WebSocket server** (`forge_bridge/server/`) — wire protocol, connection management, event-driven hooks. Standalone WS server on `:9998` (graceful degradation if unreachable per Phase 07.1).
- **Postgres persistence layer** (`forge_bridge/store/` + Alembic migrations in `forge_bridge/store/migrations/`) — entities, relationships, events, registry, and the `staged_operation` table from FB-A.
- **Async/sync client pair** (`forge_bridge/client/`) — `AsyncClient` + `SyncClient` for connecting to the WS server.
- **Learning pipeline** (`forge_bridge/learning/`) — execution log (JSONL source of truth at `~/.forge-bridge/executions.jsonl`), threshold-driven promotion, LLM synthesizer (Ollama backend), registry watcher, probation system. SQL mirror via `StoragePersistence` Protocol (Phase 8) — JSONL-authoritative, SQL eventual. **Substrate, not autonomous producer:** bridge ships the recording machinery, synthesizer, watcher, and manifest, but a *consumer application* (projekt-forge in production) is responsible for calling `ExecutionLog.record(code, intent)` to feed observations. On a stock install without a consumer wired, the pipeline is dormant — the log file exists, the watcher polls, but no patterns ever cross threshold.
- **LLM router** (`forge_bridge/llm/router.py`) — `LLMRouter` with `acomplete()` and `complete_with_tools()`; sensitive routing to local Ollama vs. cloud Anthropic; hard caps (8 iterations, 120s wall-clock, 30s per-tool); `LLMLoopBudgetExceeded` / `RecursiveToolLoopError` / `LLMToolError` exported from the public API. **v1.6 Phase 24.4** added the **K=2 canonical-recurrence termination trigger** at the D-07 site (`router.py:639-662`): when the 2nd identical successful canonical dispatch is observed (matching `tool_name` + `args_hash` + `result_hash`, both `status=ok`), internal `_OrchestrationTerminated` is raised after the K-th iter's streaming emits + state update (deferred-raise per framing §5 + §8.3); the handler catches and emits a distinct `event: orchestration_terminated` SSE taxon. Load-bearing invariant: "orchestrator may terminate but does not impersonate the model" — no orchestrator-side synthesis, no system message changes, no prompt shaping.
- **Staged operations platform** (`forge_bridge/store/staged_operation.py` + console + MCP wiring) — `proposed → approved → executed/rejected/failed` state machine. Approval is bookkeeping; the proposer subscribes to events and executes against its own domain. **Approval surface, not propose-side:** bridge ships only `forge_list_staged` / `forge_get_staged` / `forge_approve_staged` / `forge_reject_staged` — the inspection-and-decision tools. The propose-side MCP tools (`forge_stage_rename`, `forge_stage_publish_shots`, `forge_stage_set_startframes`, …) live in the consumer (projekt-forge in production); on a stock install without a consumer, the `staged_operation` table stays empty until something feeds it. Same substrate/consumer pattern as the Learning pipeline above.
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
│   ├── __main__.py             ← Thin delegate to `forge_bridge.cli.main:app` (bare invocation prints help and exits)
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

forge-bridge is the infrastructure layer; projekt-forge is the first first-party consumer built on top of it.

projekt-forge pins specific forge-bridge versions and builds production workflows against the stable vocabulary and runtime surfaces bridge provides. The split is intentional: forge-bridge stays generic infrastructure, while consumer-specific workflow behavior lives downstream.

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

# 5. Bring up the bridge runtime (mcp_http + co-hosted Console on :9996, state_ws on :9998)
# Option A: ad-hoc managed background daemons (good for dev / single workstation)
fbridge up
# Option B: supervised systemd / launchd daemons (operator-workstation path)
sudo ./scripts/install-bootstrap.sh
# Note: bare `python -m forge_bridge` prints help and exits 0 — it does NOT start any services.

# 6. Smoke-test the surfaces
curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"   # Web UI → 200
curl -s   http://localhost:9999/status                                  # Flame hook → JSON with flame_available
forge-bridge console doctor                                             # CLI + post-install diagnostic
```

`ANTHROPIC_API_KEY` is **optional** — the chat endpoint hardcodes `sensitive=True`, which routes through local Ollama (`qwen2.5-coder:14b` since Phase 24.3). The key is only needed for `sensitive=False` cloud routing (not the daily operator workflow).

**Do not use `qwen3:32b` as the default model.** It exceeds the 60s wall-clock budget due to thinking-mode token verbosity (SEED-DEFAULT-MODEL-BUMP-V1.4.x).

---

## Active Development Context

Milestone: **v1.6 Operability** (opened 2026-05-14; v1.5 Legibility closed same day). See `.planning/STATE.md` for the live cursor; framing at `.planning/milestones/v1.6-FRAMING.md`.

Architectural baseline (v1.6-FRAMING §2.5): forge-bridge is **a low-latency conversational runtime + a graph-native operational runtime sharing a common dispatch substrate**. Three engineering domains are now held separately and named explicitly:

1. **Runtime economics** — token budget, KV cache, model size, prompt prefix length.
2. **Protocol serialization** — provider-native `tool_calls` ingestion + Bug-D salvage normalization (load-bearing on qwen2.5-coder under the 58-tool prefix per Phase 24.1 live measurement).
3. **Dispatch substrate** — `_execute_python_core` shared body across MCP tool-call path + `fbridge flame-exec` CLI + graph_store JSONL append-only event log.

Five v1.6 phases shipped under writer's-room cadence (no formal GSD plan substrate; framing + commits + cursors + STATE.md updates carry archaeology):

- **Phase 24** (substrate work closed on portofino 2026-05-15) — Operational substrate loop. 4-commit operator arc Exists → See → Trust → Drive: `fbridge graph list/show` + `fbridge doctor graph_store` row (tri-state ok/loaded/fail) + Q8 POSIX append atomicity verified dual-platform (portofino macOS + flame-01 Linux) + `fbridge flame-exec` CLI sharing `_execute_python_core` body with the LLM tool-call path. Substrate-discipline encoded structurally — operator surfaces are projections, not parallel execution paths.
- **Phase 24.1** (CLOSED 2026-05-14) — KV-cache work + protocol-path observability. `OllamaToolAdapter.send_turn` instrumented with structured `ollama-turn` log line. Three-domain decomposition folded into framing. Bug-D salvage promoted to first-class normalization layer.
- **Phase 24.2** (CLOSED 2026-05-15) — Doctor probe refactored to daemon-routed dispatch (`POST :9996/api/v1/exec text="flame_ping"`). Architectural invariant: **health surface reflects daemon-observed dispatch truth, not independently reconstructed local truth.** Closes the config-context-divergence class (launchd env vs shell env drift was silent + indefinite pre-24.2).
- **Phase 24.3** (CLOSED 2026-05-16; PR #4 MERGED) — Chat-layer convergence Layer A + Layer C. (A) Default model `qwen2.5-coder:32b → qwen2.5-coder:14b` per measure-first canonical baseline (~1.5–2× per-iter speedup). (C) SSE history-grows streaming for `POST /api/v1/chat` with `Accept: text/event-stream` (4.4ms first-byte vs 120s budget; JSON path preserved).
- **Phase 24.4** (CLOSED 2026-05-18; PR #5 MERGED) — Chat-layer convergence Layer B: orchestrator-side K=2 canonical-recurrence trigger at D-07 site (`router.py:639-662`). Three terminal SSE event taxa (`done` = model-decided / `orchestration_terminated` = policy-decided / `error` = transport/runtime) encode architectural truth. Load-bearing invariant: **"orchestrator may terminate but does not impersonate the model."**

**24.x A/B/C decomposition complete.**

**Next phase (anticipated, not opened): Phase 24.5** — Consumer-side UX of `orchestration_terminated` in Console + CLI. The K-th `event: message` carries the answer that triggered termination; the consumer surfaces this as the user-facing response. Framing constraint per 24.4 §3.1: the chat handler / Console UI / CLI surface the envelope; the orchestrator does NOT synthesize.

**§11 deferral register from 24.4 framing (live "what's next" menu; all explicitly unbound pending evidence, NOT rejected):** (1) affordance-selection regression — iter 1 still picks `flame_find_media` not `flame_execute_python`; (2) orchestrator-side terminal-content surfacing in consumer (24.5); (3) D-07 unification; (4) cross-provider Anthropic termination semantics (production hardcodes `sensitive=True` → Ollama); (5) token-delta streaming (native `tool_calls` reliability unchanged); (6) adaptive / per-tool K; (7) result-hash normalization.

**v1.6 constraints (binding):**

- Public `forge_bridge.__all__` unchanged at 19 through every 24.x phase. No new external libraries. `pyproject.toml` version still `1.4.1`.
- Anti-scope §10 (24.4 framing) binding across all 24.x work: no orchestrator-side synthesis, no prompt injection, no system-message changes, no temperature drift, no tool-list narrowing, no semantic-equivalence result-hashing, no cross-provider reach.
- Per-layer success criteria attached to native layer; UX wins ride as ADDITIONAL, not laundered into convergence success.
- Writer's-room cadence persists; framing + execution commits + cursors + STATE.md updates carry archaeology.

**Don't break:** the Flame hook + MCP server + Artist Console + CLI + chat endpoint are all in production use across portofino + flame-01 + assist-01. v1.6 added: SSE streaming on `/api/v1/chat`, K=2 termination + `event: orchestration_terminated` taxon, graph_store JSONL emission via `_execute_python_core`, `fbridge flame-exec` + `fbridge graph list/show`, daemon-routed doctor probe, `postgres` + `graph_store` doctor rows, default model bump to `qwen2.5-coder:14b`. All preserve existing surfaces byte-equivalently — refactoring beyond what 24.5 framing explicitly scopes is out of scope.

---

## Questions To Come Back To

1. What format should bridge use for inter-service messages? JSON? MessagePack? Something else?
2. Should the bridge core service be a single process or multiple cooperating processes?
3. When is a Unix socket preferable to HTTP for same-machine communication?
4. What does the bridge core service look like from an endpoint's perspective — is it a library you import or a service you connect to?
