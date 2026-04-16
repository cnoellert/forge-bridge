# Architecture Research

**Domain:** Middleware package integration — forge-bridge v1.1 projekt-forge integration
**Researched:** 2026-04-15
**Confidence:** HIGH (based on direct codebase analysis of both repos)

## Standard Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        projekt-forge                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  forge MCP server (projekt-forge's __main__)                  │  │
│  │  - Imports forge-bridge's get_mcp() + register_tools()        │  │
│  │  - Registers forge-specific tools: catalog, orchestrate, scan │  │
│  │  - Supplies LLM override, enriched system prompt              │  │
│  │  - Supplies DB session factory to learning pipeline           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│       ↑ pip install forge-bridge                                    │
└───────┼────────────────────────────────────────────────────────────┘
        │
┌───────┼────────────────────────────────────────────────────────────┐
│       │              forge-bridge (standalone pip package)          │
│  ┌────┴──────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ mcp/      │  │ llm/     │  │ learning/    │  │ bridge.py    │  │
│  │ server.py │  │ router.py│  │ synthesizer  │  │ HTTP client  │  │
│  │ registry  │  │ health   │  │ watcher      │  │ → port 9999  │  │
│  │ tools     │  │          │  │ execution_log│  │              │  │
│  └─────┬─────┘  └──────────┘  └──────────────┘  └──────────────┘  │
│        │                                                            │
│  ┌─────┴──────────────────────────────────────────────────────┐    │
│  │  store/  client/  server/  core/  flame/                   │    │
│  │  (PostgreSQL, WebSocket, vocabulary, Flame endpoint)        │    │
│  └────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### forge-bridge public API surface (what needs hardening)

| Component | Current State | Required Change |
|-----------|--------------|-----------------|
| `forge_bridge.mcp.register_tools()` | Exists, enforces flame_/forge_/synth_ namespace | Add `forge_*` prefix for projekt-forge tools; document contract |
| `forge_bridge.mcp.get_mcp()` | Exists, returns FastMCP instance | Stable — no change needed |
| `forge_bridge.bridge.configure()` | Exists, atomic config swap | Expose in `__init__.py` for projekt-forge to call at startup |
| `forge_bridge.bridge.set_execution_callback()` | Exists, wires learning pipeline | Expose as public API; must be callable by projekt-forge |
| `forge_bridge.llm.router.LLMRouter` | Exists, env-var configured | Add constructor injection: `LLMRouter(local_url=..., system_prompt=...)` |
| `forge_bridge.learning.ExecutionLog` | JSONL to `~/.forge-bridge/` | Add constructor injection: `ExecutionLog(log_path=..., threshold=...)` |
| `forge_bridge.learning.synthesizer.Synthesizer` | Calls `get_router()` singleton | Add constructor injection: `Synthesizer(router=...)` |
| `forge_bridge.learning.watcher.watch_synthesized_tools()` | `SYNTHESIZED_DIR` hardcoded | Already accepts `synthesized_dir` param — sufficient |

#### projekt-forge integration components (what gets built)

| Component | Where | Responsibility |
|-----------|-------|----------------|
| `forge_mcp/__main__.py` | projekt-forge | MCP server entry point that calls `get_mcp()`, then `register_tools()` for forge-specific tools |
| `forge_mcp/tools/` | projekt-forge | catalog, orchestrate, scan, seed tools moved here from `forge_bridge/tools/` |
| `forge_mcp/learning_config.py` | projekt-forge | Injects forge DB session factory into learning pipeline's persistence layer |
| Updated `forge_bridge/__main__.py` | projekt-forge | Now delegates to forge_mcp or calls forge-bridge standalone |

## Recommended Project Structure

Changes in forge-bridge (what must be added or modified):

```
forge_bridge/
├── __init__.py              # Add public API exports
├── bridge.py                # configure() and set_execution_callback() already exist
├── llm/
│   ├── __init__.py          # CHANGE: export LLMRouter constructor
│   └── router.py            # CHANGE: add constructor injection (local_url, system_prompt)
├── learning/
│   ├── __init__.py          # CHANGE: export ExecutionLog, Synthesizer as public API
│   ├── execution_log.py     # CHANGE: make log_path a constructor param (already is)
│   ├── synthesizer.py       # CHANGE: add router constructor injection
│   └── watcher.py           # No change needed
└── mcp/
    ├── __init__.py          # Already exports register_tools() and get_mcp() — stable
    ├── registry.py          # CHANGE: document forge_ prefix as valid for downstream
    └── server.py            # No change needed for integration
```

Changes in projekt-forge (what gets rewired):

```
forge_bridge/           ← existing, being replaced by imports
├── tools/
│   ├── catalog.py      → keep (forge-specific, not in forge-bridge)
│   ├── orchestrate.py  → keep (forge-specific, traffik dependency)
│   ├── scan.py         → keep (forge-specific, scanner dependency)
│   ├── seed.py         → keep (forge-specific)
│   ├── project.py      → DELETE: import from forge_bridge.tools.project
│   ├── timeline.py     → DELETE: import from forge_bridge.tools.timeline
│   ├── batch.py        → DELETE: import from forge_bridge.tools.batch
│   ├── publish.py      → DELETE: import from forge_bridge.tools.publish
│   ├── reconform.py    → DELETE: import from forge_bridge.tools.reconform
│   ├── switch_grade.py → DELETE: import from forge_bridge.tools.switch_grade
│   └── utility.py      → DELETE: import from forge_bridge.tools.utility
├── bridge.py           → DELETE: import from forge_bridge.bridge
├── client/             → DELETE: import from forge_bridge.client
├── server/mcp.py       → REPLACE: new entry point using forge-bridge's MCP API
└── db/                 → KEEP: forge-specific DB (users, roles, invites, catalog)
```

### Structure Rationale

- **forge-bridge tools stay in forge-bridge**: They are maintained there and tested independently. projekt-forge imports them instead of duplicating.
- **Forge-specific tools stay in projekt-forge**: catalog, orchestrate, scan, seed all have forge-specific dependencies (traffik, scanner, per-project DBs) that don't belong in the standalone package.
- **MCP server moves to projekt-forge's namespace**: projekt-forge gets the full server and adds its tools on top of forge-bridge's builtins via `register_tools()`.
- **DB stays in projekt-forge**: `forge_bridge.db` in projekt-forge is an independent PostgreSQL catalog with per-project databases. forge-bridge has its own `store/` which is for the canonical vocabulary layer. These are different schemas, different purposes.

## Architectural Patterns

### Pattern 1: Constructor Injection for Learning Pipeline Overrides

**What:** projekt-forge passes its own LLM config and DB session factory to forge-bridge's learning pipeline via constructor arguments, not environment variables or monkey-patching.

**When to use:** When the downstream consumer has its own LLM infrastructure (projekt-forge's forge_config.py knows the local Ollama URL, DB credentials, etc.) and needs to override forge-bridge's defaults.

**Trade-offs:** Requires forge-bridge's learning components to accept injected dependencies. Current implementation uses module-level singletons and env vars — needs constructor injection added.

**Example:**
```python
# projekt-forge startup
from forge_bridge.llm.router import LLMRouter
from forge_bridge.learning.execution_log import ExecutionLog
from forge_bridge.learning.synthesizer import Synthesizer
from forge_bridge.bridge import set_execution_callback
from forge_bridge.config.forge_config import load_forge_config

cfg = load_forge_config()
router = LLMRouter(
    local_url=f"http://{cfg['llm_host']}:11434/v1",
    system_prompt=build_forge_system_prompt(cfg),  # enriched with project context
)
log = ExecutionLog(
    log_path=Path(cfg["log_dir"]) / "executions.jsonl",
    threshold=cfg.get("promotion_threshold", 3),
)
synth = Synthesizer(router=router, log=log)

# Wire into bridge
set_execution_callback(log.record_sync_callback)
```

### Pattern 2: Additive Tool Registration via register_tools()

**What:** projekt-forge calls `register_tools()` to add forge-specific tools to the shared FastMCP instance before `mcp.run()`. Builtin tools are already registered by `register_builtins()` at module import time.

**When to use:** Any downstream consumer adding tools to forge-bridge's MCP server.

**Trade-offs:** Tools must follow the flame_/forge_/synth_ namespace convention. The current registry enforces this via `_validate_name()`. projekt-forge's tools are `forge_*` which is already allowed — but the current registry only accepts `forge_` for tools with `source="user-taught"`. The registry needs to allow `forge_` for downstream builtins too.

**Example:**
```python
# projekt-forge's MCP entry point
from forge_bridge.mcp import register_tools, get_mcp
from forge_mcp.tools import catalog, orchestrate, scan, seed

mcp = get_mcp()

register_tools(mcp, [
    catalog.trace_lineage,
    catalog.get_shot_deps,
    orchestrate.publish_pipeline,
    scan.media_scan,
    seed.seed_catalog,
], prefix="forge_", source="builtin")

mcp.run()
```

### Pattern 3: Dual-Entry-Point Strategy

**What:** forge-bridge keeps its standalone `python -m forge_bridge` entry point. projekt-forge gets a separate entry point that wraps forge-bridge and adds forge-specific tools. The two never conflict.

**When to use:** Always — this is the core integration model.

**Trade-offs:** projekt-forge's MCP server must initialize forge-bridge's internal client connection (currently happens in forge-bridge's `mcp/server.py` lifespan). This may require exposing the `_startup()`/`_shutdown()` lifecycle or restructuring the lifespan.

**Example:**
```
# forge-bridge standalone (no projekt-forge)
python -m forge_bridge.mcp

# projekt-forge's augmented server
python -m forge_mcp        # registers builtins via forge-bridge, adds forge-specific tools
```

### Pattern 4: Learning Pipeline Persistence Abstraction

**What:** The execution log currently writes to `~/.forge-bridge/executions.jsonl`. For projekt-forge integration, executions should optionally persist to the forge PostgreSQL DB instead. This is done via an injectable persistence backend, not by rewriting ExecutionLog.

**When to use:** When forge DB is available and the operator wants execution history queryable via SQL rather than grep-ing JSONL.

**Trade-offs:** Adds complexity to ExecutionLog. The JSONL backend remains default (works standalone, no DB required). The DB backend is an optional alternative, not a replacement.

## Data Flow

### Execution → Learning Pipeline (integrated)

```
[projekt-forge MCP server startup]
    ↓
forge_config.py → reads /opt/forge/config.yaml
    ↓
LLMRouter(local_url=..., system_prompt=forge_system_prompt)
ExecutionLog(log_path=forge_log_dir/executions.jsonl)
Synthesizer(router=router, log=log)
    ↓
set_execution_callback(log.record_sync_callback)
    ↓
[User calls flame_* or forge_* tool via Claude]
    ↓
bridge.py executes code against Flame → calls execution callback
    ↓
ExecutionLog.record(code, intent) → JSONL append + in-memory count
    ↓ (if count >= threshold)
Synthesizer.synthesize(code, intent, count)
    → LLMRouter.acomplete(prompt, sensitive=True)
        → Ollama on forge's configured host (not hardcoded assist-01)
    → validate AST → write to synthesized dir
    ↓
watcher picks up new .py → register_tool(mcp, fn, source="synthesized")
```

### LLM System Prompt Enrichment

```
forge_bridge default system prompt:
    "VFX pipeline assistant on Flame 2026..."
    (hardcoded, env-overridable via FORGE_SYSTEM_PROMPT)

projekt-forge override:
    build_forge_system_prompt(cfg) → includes:
    - Active project name from forge DB
    - Shot naming convention specific to this facility
    - DB connection details (projekt-forge's catalog, not forge-bridge's store)
    - Render farm details from forge_config
```

### projekt-forge's MCP Server Tool Set

```
forge-bridge builtins (registered at module import via register_builtins):
    flame_ping, flame_get_project, flame_list_libraries, flame_list_desktop,
    flame_find_media, flame_context, flame_get_sequence_segments, ...
    (all existing flame_* and forge_* tools)

projekt-forge additions (registered via register_tools() before mcp.run()):
    forge_catalog_lineage     → catalog.trace_lineage
    forge_catalog_shot_deps   → catalog.get_shot_deps
    forge_publish_pipeline    → orchestrate.publish_pipeline
    forge_media_scan          → scan.media_scan
    forge_seed_catalog        → seed.seed_catalog
```

### Key Data Flows

1. **Tool registration at startup:** forge-bridge's `register_builtins()` runs at module import of `mcp/server.py`. projekt-forge calls `register_tools()` after importing the module, before `mcp.run()`. Order matters — `register_tools()` must be called before the event loop starts.

2. **Learning pipeline callback:** `set_execution_callback()` must be called before any bridge `execute()` calls. In projekt-forge's MCP server startup, this means calling it in the lifespan before `yield`, not at module import time.

3. **DB session injection:** projekt-forge's learning integration should pass execution data to the forge DB as a secondary write (JSONL remains primary for offline/standalone use). This means `ExecutionLog` needs a `db_session_factory` optional parameter that writes a row to a `forge_executions` table after each JSONL append.

## Integration Points

### Public API Surface — forge-bridge modules that need hardening

| Module | Current API | Required Change | Why |
|--------|------------|-----------------|-----|
| `forge_bridge.mcp` | `register_tools(mcp, fns, prefix, source)` | No change to signature; add `source="builtin"` use case documentation | projekt-forge tools are `source="builtin"`, not `"user-taught"` |
| `forge_bridge.bridge` | `configure()`, `set_execution_callback()` | Export from `__init__.py` | Currently only accessible by knowing the module path |
| `forge_bridge.llm.router` | `LLMRouter()` uses env vars | Add `__init__(local_url, local_model, system_prompt, cloud_model)` params | projekt-forge has its own config source |
| `forge_bridge.learning.execution_log` | `ExecutionLog(log_path, threshold)` | Add `db_session_factory` optional param | Project-forge DB persistence |
| `forge_bridge.learning.synthesizer` | `Synthesizer` calls `get_router()` | Accept `router: LLMRouter` as constructor param | Inject projekt-forge's configured router |
| `forge_bridge.mcp.registry` | Allows `forge_` only for `source="user-taught"` | Allow `source="builtin"` from downstream | projekt-forge's tools are builtins, not user-taught |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| projekt-forge MCP server ↔ forge-bridge MCP | `get_mcp()` returns FastMCP instance; `register_tools()` adds tools | Must happen before `mcp.run()` |
| projekt-forge ↔ forge-bridge learning pipeline | Constructor injection at startup | LLM config, log path, system prompt |
| projekt-forge ↔ forge-bridge bridge.py | `set_execution_callback()` at startup | One callback; projekt-forge supplies it |
| forge-bridge tools ↔ projekt-forge DB | No direct coupling — forge-bridge tools use `get_client()` for forge-bridge's own store | projekt-forge catalog tools use projekt-forge's own `AsyncClient` / DB connection |
| projekt-forge flame_hooks ↔ forge-bridge | Currently copies `forge_bridge.py` verbatim | After integration: flame hook in projekt-forge imports from pip-installed forge-bridge or symlinks the hook file |

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| forge-bridge store (PostgreSQL port 5432) | forge-bridge's own `store/session.py` | Used by forge-bridge's canonical vocabulary layer |
| projekt-forge catalog (PostgreSQL port 7533) | projekt-forge's `db/engine.py` with `FORGE_DB_URL` | Per-project DBs: `forge_catalog_{project_name}` |
| Flame HTTP bridge (port 9999) | `forge_bridge.bridge.execute()` | Shared — both systems call through this |
| forge-bridge WebSocket server (port 9998) | `forge_bridge.client.AsyncClient` | Both systems connect as clients |
| Ollama LLM (assist-01:11434) | `forge_bridge.llm.router.LLMRouter` | URL becomes injectable for projekt-forge config |

## Anti-Patterns

### Anti-Pattern 1: Importing From projekt-forge Inside forge-bridge

**What people do:** Add a conditional `try: from projekt_forge.db import session_factory` inside forge-bridge's learning pipeline to handle the case where it's running inside projekt-forge.

**Why it's wrong:** Violates the one-way dependency. forge-bridge must work without projekt-forge installed. Any import from projekt-forge inside forge-bridge breaks standalone use.

**Do this instead:** Use constructor injection. forge-bridge's `ExecutionLog` accepts an optional `db_session_factory` parameter. When `None` (default), it's JSONL-only. projekt-forge passes its session factory at construction time.

### Anti-Pattern 2: Registering forge-specific Tools Inside forge-bridge

**What people do:** Add `catalog.py`, `orchestrate.py`, and `scan.py` from projekt-forge to forge-bridge's `register_builtins()` to reduce setup code in projekt-forge.

**Why it's wrong:** These tools have hard dependencies on projekt-forge packages (`traffik`, `forge_bridge.scanner`, `forge_bridge.db`). Including them in forge-bridge's builtins would force all forge-bridge users to install projekt-forge. The tools also connect to projekt-forge's catalog server, not forge-bridge's.

**Do this instead:** projekt-forge calls `register_tools()` at its own startup to add these tools. They never enter forge-bridge's codebase.

### Anti-Pattern 3: Sharing the mcp/server.py Lifespan

**What people do:** Have projekt-forge's entry point import and re-use forge-bridge's `_lifespan` context manager, adding forge-specific startup logic by monkey-patching.

**Why it's wrong:** `_lifespan` is a private implementation detail of forge-bridge's standalone server. Patching it creates coupling to internal structure. Breaks on any refactor of `mcp/server.py`.

**Do this instead:** projekt-forge writes its own lifespan that calls `from forge_bridge.mcp.server import _startup, _shutdown` (which need to be promoted to public) or restructures so that `AsyncClient` startup is injectable. The cleanest solution: `mcp/server.py` exposes `async def startup_bridge(url, name)` and `async def shutdown_bridge()` as public functions that projekt-forge's lifespan can call explicitly.

### Anti-Pattern 4: Hardcoding assist-01 in LLM Router

**What people do:** Leave `LOCAL_BASE_URL = "http://assist-01:11434/v1"` hardcoded in `router.py` because "it works for us."

**Why it's wrong:** When projekt-forge reads this from `forge_config.yaml`, the env var `FORGE_LOCAL_LLM_URL` override works — but it requires projekt-forge to set the env var before forge-bridge initializes. Constructor injection is cleaner and doesn't depend on env var timing.

**Do this instead:** `LLMRouter(local_url=cfg["llm_host"])` at projekt-forge startup. The `LLMRouter` constructor uses `local_url` if provided, falls back to `FORGE_LOCAL_LLM_URL` env var, falls back to `"http://assist-01:11434/v1"`.

## Scaling Considerations

This is a local-first, single-machine integration. Scaling is not an immediate concern. The relevant consideration is **operational isolation**: forge-bridge must continue to work standalone (without projekt-forge) after the integration.

| Concern | Current | After Integration |
|---------|---------|-------------------|
| forge-bridge standalone | Works via `python -m forge_bridge.mcp` | Must continue to work — no imports from projekt-forge |
| projekt-forge MCP server | Duplicates tools, has own entry point | Uses forge-bridge's tools + adds forge-specific tools via `register_tools()` |
| Learning pipeline state | JSONL in `~/.forge-bridge/` | JSONL remains default; optional secondary write to forge DB |
| LLM config | Env vars pointing to assist-01 | Constructor injection from forge_config.yaml when running inside projekt-forge |

## Build Order

The build order is determined by dependency graph. Each step must not break standalone forge-bridge operation.

### Step 1: API Hardening in forge-bridge (prerequisite for everything)

Changes only in forge-bridge. No projekt-forge changes yet.

- Promote `_startup()` and `_shutdown()` in `mcp/server.py` to public (`startup_bridge()`, `shutdown_bridge()`)
- Add constructor injection to `LLMRouter.__init__()`: accept `local_url`, `local_model`, `system_prompt`
- Add `router` constructor param to `Synthesizer.__init__()`
- Confirm `ExecutionLog(log_path, threshold)` — constructor injection already exists, verify it's importable cleanly
- Allow `source="builtin"` for `forge_` prefix in `mcp/registry._validate_name()` — currently blocked for non-synthesized sources
- Export `configure` and `set_execution_callback` from `forge_bridge.__init__`
- Write `forge_bridge.mcp` public API docstring

Deliverable: forge-bridge's public API is stable for downstream consumption. All tests pass. Standalone mode unchanged.

### Step 2: Rewire projekt-forge to Import from forge-bridge

Changes only in projekt-forge. forge-bridge is treated as an installed dependency.

- Add `forge-bridge` to projekt-forge's `pyproject.toml` dependencies
- Delete duplicated tool modules in projekt-forge's `forge_bridge/tools/` (project, timeline, batch, publish, reconform, switch_grade, utility)
- Delete duplicated `forge_bridge/bridge.py` and `forge_bridge/client/`
- Update `forge_bridge/server/mcp.py` to use `get_mcp()` + `register_tools()` pattern
- Verify: `python -m forge_bridge` in projekt-forge context works with forge-bridge's tools

Deliverable: projekt-forge no longer duplicates forge-bridge code. The forge-specific tools (catalog, orchestrate, scan, seed) remain in projekt-forge and are registered via `register_tools()`.

### Step 3: Learning Pipeline Integration in projekt-forge

Changes only in projekt-forge. Requires Step 1 (constructor injection) and Step 2 (shared bridge).

- Create `forge_mcp/learning_config.py` in projekt-forge that reads `forge_config.yaml` and constructs `LLMRouter`, `ExecutionLog`, and `Synthesizer` with forge-specific config
- Wire `set_execution_callback()` in projekt-forge's MCP server lifespan
- Add optional `db_session_factory` to `ExecutionLog` if DB persistence is in scope
- Test: confirm synthesis uses Ollama at forge-configured URL, not hardcoded assist-01

Deliverable: Learning pipeline runs inside projekt-forge with forge's LLM config and optionally persists to forge DB.

## Sources

- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/__init__.py` — current public API (`register_tools`, `get_mcp`)
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/registry.py` — namespace enforcement logic, current source validation rules
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/server.py` — lifespan, `_startup`/`_shutdown` currently private
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/bridge.py` — `configure()`, `set_execution_callback()`, module-level callback
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/llm/router.py` — `LLMRouter`, `LOCAL_BASE_URL` hardcoded constant, env var fallbacks
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/learning/execution_log.py` — `ExecutionLog(log_path, threshold)` constructor, JSONL append
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/learning/synthesizer.py` — calls `get_router()` singleton (needs constructor injection)
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/server/mcp.py` — current projekt-forge MCP server, full tool registration pattern to replace
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/config/forge_config.py` — `load_forge_config()`, `get_db_config()`, YAML schema
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/db/engine.py` — `init_db()`, `get_engine()`, per-project DB pool
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/catalog.py` — forge-specific tool, must stay in projekt-forge
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/orchestrate.py` — forge-specific tool with traffik dependency
- `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/PROJECT.md` — v1.1 scope, constraints, out-of-scope items
- `/Users/cnoellert/Documents/GitHub/forge-bridge/pyproject.toml` — current package dependencies, optional extras
- `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` — projekt-forge dependencies (does not yet list forge-bridge)

---
*Architecture research for: forge-bridge v1.1 projekt-forge integration*
*Researched: 2026-04-15*
