# Architecture Patterns

**Domain:** Post-production pipeline middleware with learning pipeline and pluggable MCP server
**Researched:** 2026-04-14
**Confidence:** HIGH (based on existing codebase analysis and FlameSavant JS source)

---

## Recommended Architecture

The milestone adds three new subsystems that integrate with the existing middleware:

1. **`forge_bridge/llm/`** — async LLM router with sensitivity-based backend selection
2. **`forge_bridge/learning/`** — execution log + skill synthesizer + registry watcher
3. **MCP server rebuild** — pluggable tool registration API, synthesized tool injection

These subsystems are additive. They wire into the existing `bridge.py` HTTP client and `mcp/server.py` as optional hooks. Nothing in `core/`, `store/`, `server/`, or `client/` changes.

---

## Component Boundaries

### Existing Components (stable, no changes)

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `core/` | Canonical vocabulary (entities, traits, registry) | `store/`, `server/router` |
| `store/` | PostgreSQL persistence via SQLAlchemy | `server/router` |
| `server/` | WebSocket server, message routing, event broadcast | `client/`, `store/` |
| `client/async_client.py` | Async WebSocket client | `server/` |
| `client/sync_client.py` | Sync wrapper for Flame hooks | wraps `async_client` |
| `mcp/server.py` | FastMCP server, tool registration | `client/async_client`, `bridge.py` |
| `bridge.py` | HTTP client to Flame on port 9999 | `mcp/tools.py`, `flame/endpoint.py` |
| `flame/endpoint.py` | Translates Flame events to forge-bridge vocabulary | `client/sync_client`, Flame hooks |

### New Components (this milestone)

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `llm/router.py` | Async completion with sensitivity routing (local Ollama / cloud Claude) | `learning/synthesizer.py`, anything needing generation |
| `llm/health.py` | Health check for both LLM backends; exposed as MCP resource | `llm/router.py`, `mcp/server.py` |
| `learning/log.py` | JSONL execution log; in-memory count table; promotion trigger | `bridge.py` (as hook), `learning/synthesizer.py` |
| `learning/synthesizer.py` | LLM-driven Python MCP tool generation; validates AST; writes to disk | `llm/router.py`, `learning/watcher.py` |
| `learning/watcher.py` | Filesystem watcher on `mcp/synthesized/`; hot-loads new tool files; calls `register_tools()` | `mcp/server.py` (via callback) |
| `mcp/registry.py` | Runtime tool registry; holds static tools + synthesized tools; supports `register_tools()` call | `mcp/server.py`, `learning/watcher.py` |
| `mcp/synthesized/` | Directory of synthesized `*.py` tool files (generated at runtime, not checked in) | `learning/synthesizer.py`, `learning/watcher.py` |

---

## Data Flow

### 1. Execution Log → Promotion

```
User action (Claude calls flame_* or forge_* tool)
  → bridge.py executes Python against Flame
  → On success: learning/log.py.record(code, output)
    → Normalize code (strip literals) → SHA-256 hash
    → Append entry to ~/.forge_bridge/executions.jsonl
    → Increment in-memory count for hash
    → If count == PROMOTION_THRESHOLD:
        return promoted=True, hash, examples[]
  → bridge.py calls synthesizer if promoted=True
```

### 2. Skill Synthesis

```
bridge.py receives promoted=True from log
  → learning/synthesizer.py.synthesize(examples)
    → Build prompt: "given these Python blocks, write an MCP tool function"
    → llm/router.py.complete(prompt, sensitive=True)
      → Ollama (local, free, no egress)
      → Returns Python source string
    → Validate: parse AST, check function signature, check @mcp.tool decorator
    → If invalid: retry up to N times (re-synthesize on failure)
    → Write to forge_bridge/mcp/synthesized/<tool_name>.py
    → Return {name, file_path}
```

### 3. Hot Registration

```
learning/watcher.py detects new/changed .py in mcp/synthesized/
  → importlib.import_module() the file
  → Extract decorated functions (functions with _mcp_tool attr or by convention)
  → Call mcp/registry.py.register_tools([fn, ...])
    → mcp.tool(name=..., annotations=...)(fn) for each
    → FastMCP adds tool to its internal registry
    → Tool immediately available to next LLM request
  → Emit "tool-added" or "tool-updated" log entry
```

### 4. Probation Tracking

```
Each synthesized tool invocation:
  → On success: learning/log.py.record_skill_success(tool_name)
  → On failure: learning/log.py.record_skill_failure(tool_name)
    → If failure_count > FAILURE_THRESHOLD: flag for re-synthesis
    → Log entry includes error traceback for next synthesis prompt
```

### 5. LLM Router

```
Caller: synthesizer.synthesize(...) or any future consumer
  → llm/router.py.acomplete(prompt, sensitive=True, system=None)
    → sensitive=True  → Ollama (openai client, base_url=assist-01:11434)
    → sensitive=False → Anthropic Claude (anthropic client)
    → Returns completion string
    → Raises LLMError on backend failure (not RuntimeError — typed)
```

### 6. Pluggable Tool Registration (downstream consumers)

```
projekt-forge (downstream dependency):
  from forge_bridge.mcp import register_tools
  register_tools(mcp_instance, [tool_fn_1, tool_fn_2, ...])
    → mcp_instance.tool(name=..., annotations=...)(fn) for each
    → Tools available immediately (projekt-forge never patches server.py)
```

---

## Patterns to Follow

### Pattern 1: Bridge Hook (non-invasive integration)

The execution log wires into `bridge.py` via an optional callback, not inheritance or monkey-patching.

```python
# bridge.py
class FlameBridge:
    def __init__(self, ..., on_execution=None):
        self._on_execution = on_execution  # Optional[Callable[[str, str], Awaitable[None]]]

    async def execute(self, code: str) -> BridgeResult:
        result = await self._do_execute(code)
        if result.ok and self._on_execution:
            await self._on_execution(code, result.stdout)
        return result
```

Wire at startup in `mcp/server.py`:

```python
from forge_bridge.learning.log import ExecutionLog
log = ExecutionLog()
bridge = FlameBridge(..., on_execution=log.record_async)
```

This keeps `bridge.py` testable in isolation and the learning pipeline entirely optional.

### Pattern 2: Synthesized Tool File Convention

Synthesized tools are plain Python modules with a top-level async function decorated with `@mcp.tool()` placeholder metadata. The watcher discovers them by a module-level `SYNTHESIZED = True` sentinel.

```python
# mcp/synthesized/create_reel.py
# SYNTHESIZED — generated by forge_bridge.learning.synthesizer
# source: user-taught | auto-synthesized
# generated: 2026-04-14T09:12:33Z

SYNTHESIZED = True
TOOL_NAME = "flame_create_reel"

async def flame_create_reel(library_name: str, reel_name: str) -> str:
    """Creates a new reel inside a named library."""
    from forge_bridge.mcp.server import get_bridge
    bridge = get_bridge()
    code = f"..."
    result = await bridge.execute(code)
    return result.stdout if result.ok else f"Error: {result.error}"
```

The watcher imports the module, finds functions where the module has `SYNTHESIZED = True`, and registers them.

### Pattern 3: Pluggable Tool Registration API

```python
# forge_bridge/mcp/__init__.py
def register_tools(mcp_instance, tool_functions: list) -> None:
    """Register additional tool functions with an existing FastMCP instance.
    
    Usage by downstream consumers (e.g. projekt-forge):
        from forge_bridge.mcp import register_tools
        register_tools(mcp, [my_tool_fn, another_tool_fn])
    """
    for fn in tool_functions:
        name = getattr(fn, "_tool_name", fn.__name__)
        annotations = getattr(fn, "_tool_annotations", {})
        mcp_instance.tool(name=name, annotations=annotations)(fn)
```

### Pattern 4: Async LLM Router with Optional Dependencies

```python
# forge_bridge/llm/router.py
class LLMRouter:
    async def acomplete(self, prompt: str, sensitive: bool = True, ...) -> str:
        ...

    def _get_local_client(self):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise LLMDependencyError("pip install forge-bridge[llm]")
        ...
```

Sync `complete()` kept as compatibility shim wrapping `asyncio.run(acomplete(...))`.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Hardcoded Tool List in server.py

**What goes wrong:** Adding synthesized tools requires editing `server.py` and restarting the MCP server. Downstream consumers (projekt-forge) cannot extend without patching source.

**Why bad:** Breaks hot-registration. Forces version coupling between forge-bridge and projekt-forge. Makes the learning pipeline value disappear (synthesized tools die on restart).

**Instead:** `mcp/registry.py` owns the mutable tool set. `server.py` calls `registry.register_static_tools(mcp)` at startup. `learning/watcher.py` calls `registry.register_tools(mcp, [fn])` at runtime.

### Anti-Pattern 2: LLM Calls Directly in synthesizer.py

**What goes wrong:** Synthesizer imports `anthropic` or `openai` directly. Any consumer of the synthesizer also pulls in those dependencies. Users who only want local synthesis must install cloud SDKs.

**Instead:** Synthesizer calls `llm/router.py.acomplete(prompt, sensitive=True)`. Router handles optional imports lazily. Users install `forge-bridge[llm]` only if they want LLM features.

### Anti-Pattern 3: ExecutionLog Blocking the Async Path

**What goes wrong:** JSONL write is synchronous (`open(LOG_FILE, 'a')`). Called inside `bridge.py.execute()` which is async. Blocks the event loop on disk I/O.

**Instead:** Use `asyncio.to_thread(append_jsonl, entry)` for the disk write. In-memory count update is synchronous (fast, no I/O). Promotion check returns immediately.

### Anti-Pattern 4: Synthesized Tools Importing from synthesizer at Load Time

**What goes wrong:** Circular import: `watcher.py` imports synthesized module, synthesized module imports from `learning/`, `learning/synthesizer.py` imports watcher.

**Instead:** Synthesized tool files import only from `forge_bridge.mcp.server` (for `get_bridge()`, `get_client()`). They never import from `forge_bridge.learning`. The dependency graph is one-way: `learning/ → llm/ → (openai, anthropic)`.

### Anti-Pattern 5: Probation as a Separate Service

**What goes wrong:** Separate process/thread for tracking success/failure of synthesized tools adds operational complexity. Requires IPC. Hard to reason about.

**Instead:** Probation counters live in `ExecutionLog` (same JSONL log, same in-memory table). Skill invocations record `skill_name` in the log entry. `log.get_skill_stats(name)` returns `{success, failure}` from in-memory counters seeded from JSONL on startup.

---

## Component Directory Layout

```
forge_bridge/
├── llm/                        # NEW — LLM router subsystem
│   ├── __init__.py             # Re-exports LLMRouter, get_router
│   ├── router.py               # LLMRouter class (async acomplete, sync complete)
│   ├── health.py               # health_check() → {local: bool, cloud: bool}
│   └── prompts.py              # FORGE_SYSTEM_PROMPT and synthesis prompt builders
│
├── learning/                   # NEW — learning pipeline subsystem
│   ├── __init__.py
│   ├── log.py                  # ExecutionLog (JSONL, in-memory counts, promotion)
│   ├── synthesizer.py          # SkillSynthesizer (LLM → Python → validate → write)
│   └── watcher.py              # RegistryWatcher (fs.watch on mcp/synthesized/, hot-load)
│
├── mcp/
│   ├── __init__.py             # CHANGED — expose register_tools() as public API
│   ├── __main__.py             # unchanged
│   ├── server.py               # CHANGED — lifespan wires in learning pipeline, registry
│   ├── tools.py                # unchanged
│   ├── registry.py             # NEW — mutable tool registry, register_static/dynamic tools
│   └── synthesized/            # NEW — runtime-generated tool files (gitignored)
│       └── .gitkeep
│
├── llm_router.py               # DELETED after promotion to llm/router.py
│                               # (or kept as compatibility shim that imports from llm/)
```

---

## Integration Points with Existing Architecture

### bridge.py → ExecutionLog

`bridge.py` gains an optional `on_execution` callback. This is the only change to `bridge.py`. The callback is wired in `mcp/server.py` startup, not inside `bridge.py` itself.

### mcp/server.py lifespan → learning pipeline startup

```python
@asynccontextmanager
async def lifespan(app):
    # Existing: connect AsyncClient
    await _startup()
    # New: start watcher if learning enabled
    if os.environ.get("FORGE_LEARNING", "1") != "0":
        watcher = RegistryWatcher(mcp)
        watcher.start()
    yield
    # Shutdown
    watcher.stop()
    await _shutdown()
```

### LLM router → health MCP resource

```python
@mcp.resource("forge://llm/health")
async def llm_health() -> str:
    router = get_router()
    return json.dumps(await router.health_check_async())
```

### Downstream consumer (projekt-forge) → register_tools()

projekt-forge creates its own FastMCP instance or imports forge-bridge's `mcp` instance and calls:

```python
from forge_bridge.mcp import mcp, register_tools
register_tools(mcp, [catalog_tool, orchestrate_tool, scan_tool])
```

This is the full plugin API. No subclassing, no monkey-patching.

---

## Dependency Graph Between New Components

```
mcp/server.py
  ├── client/async_client.py     (existing, unchanged)
  ├── bridge.py                  (existing, gains on_execution hook)
  ├── mcp/registry.py            (new, owns tool registry)
  └── learning/watcher.py        (new, optional, started in lifespan)
        └── mcp/registry.py      (calls register_tools on hot-load)

learning/watcher.py
  └── (no LLM deps — only importlib + filesystem)

bridge.py on_execution callback
  └── learning/log.py            (record → may return promoted=True)
        └── (on promoted) → learning/synthesizer.py
              └── llm/router.py  (acomplete)
                    ├── openai   (optional, for Ollama local)
                    └── anthropic (optional, for cloud)
```

Build order follows this graph: `llm/` first, then `learning/log.py`, then `learning/synthesizer.py`, then `learning/watcher.py`, then `mcp/registry.py`, then `mcp/server.py` changes last.

---

## Scalability Considerations

| Concern | Current (local) | Future (multi-machine) |
|---------|----------------|------------------------|
| JSONL execution log | Flat file, append-only, in-memory counts | Replace with PostgreSQL table (EventRepo already handles append-only events) |
| Synthesized tool files | Filesystem in `mcp/synthesized/` | Store in DB + load from DB on startup; filesystem stays as cache |
| LLM router | Two hard-coded tiers | Add routing table in config; weight by latency/cost/availability |
| RegistryWatcher | `asyncio`/`watchdog` on single process | Multiple MCP workers need shared registry; use DB as source of truth |
| Probation counters | In-memory (lost on restart) | Persist to DB `skill_stats` table; restore on startup (same pattern as registry restore) |

---

## Build Order (Phase Implications)

**Phase 0 — LLM router promotion**
Isolated change. No dependencies on learning pipeline. Unblocks everything else.
Files: `llm/__init__.py`, `llm/router.py`, `llm/health.py`, `llm/prompts.py`, delete/shim `llm_router.py`.

**Phase 1 — Flame tool parity + MCP rebuild**
Independent of learning pipeline. Requires new Flame tools from projekt-forge and Pydantic validation. Rebuilds `mcp/server.py` with flame_*/forge_* namespace and introduces `mcp/registry.py` + `register_tools()` API. Does not yet wire learning.

**Phase 2 — Execution log**
Requires `bridge.py` hook point (add `on_execution` callback). Requires `llm/` subsystem exists (for synthesizer in next phase). Log is standalone: write JSONL, count, report promotion. No LLM calls yet.

**Phase 3 — Synthesizer + watcher**
Requires `llm/` (Phase 0), `learning/log.py` (Phase 2), `mcp/registry.py` (Phase 1). Synthesizer calls `llm/router.py`. Watcher calls `mcp/registry.py.register_tools()`. Full pipeline wired in `mcp/server.py` lifespan.

---

## Sources

- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/llm_router.py` — existing router implementation (sync, two-tier, lazy optional imports)
- `/Users/cnoellert/Documents/GitHub/FlameSavant/src/learning/ExecutionLog.js` — JS reference implementation (hash-based promotion, JSONL, threshold=3)
- `/Users/cnoellert/Documents/GitHub/FlameSavant/src/agents/SkillSynthesizer.js` — JS reference (prompt construction, validation, write, tag)
- `/Users/cnoellert/Documents/GitHub/FlameSavant/src/learning/RegistryWatcher.js` — JS reference (fs.watch, cache bust, emit events)
- `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/codebase/ARCHITECTURE.md` — existing system architecture (HIGH confidence, generated 2026-04-14)
- `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/codebase/STRUCTURE.md` — existing directory layout (HIGH confidence, generated 2026-04-14)
- `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/PROJECT.md` — milestone scope and constraints (HIGH confidence)
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/server.py` — current MCP server (static tool registration, no plugin API)

---

*Architecture research: 2026-04-14*
