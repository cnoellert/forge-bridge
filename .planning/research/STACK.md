# Technology Stack

**Project:** forge-bridge learning pipeline milestone
**Researched:** 2026-04-14
**Scope:** New components only — learning pipeline, LLM router promotion, pluggable MCP server

---

## What This Covers

Three new subsystems added to the existing forge-bridge package:

1. **LLM Router** (`forge_bridge/llm/`) — promote `llm_router.py` from untracked scratch file to supported async module
2. **Learning Pipeline** (`forge_bridge/learning/`) — port FlameSavant ExecutionLog + SkillSynthesizer + RegistryWatcher from JavaScript to Python
3. **Pluggable MCP Server** (`forge_bridge/mcp/`) — expose `register_tools()` API so downstream consumers (projekt-forge) can extend the server

Does NOT cover the existing WebSocket server, PostgreSQL store, vocabulary layer, or Flame endpoint — those are already resolved in `.planning/codebase/STACK.md`.

---

## Recommended Stack

### LLM Router — Async Promotion

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `openai` (AsyncOpenAI) | 2.29.0 (installed) | Local Ollama + any OpenAI-compatible endpoint | `AsyncOpenAI` is a drop-in async counterpart to the existing `OpenAI` client. Verified present in `.venv`. |
| `anthropic` (AsyncAnthropic) | 0.86.0 (installed) | Claude cloud calls | `AsyncAnthropic` is confirmed in `anthropic/_client.py`. Same pattern as AsyncOpenAI. |

**What changes:** `LLMRouter` gets an `async def complete_async(...)` method alongside the existing sync `complete()`. Both delegate to private `_local_complete_async` / `_cloud_complete_async` that instantiate `AsyncOpenAI` / `AsyncAnthropic` lazily (same optional-import guard pattern already in place).

**What does NOT change:** The sync `complete()` method stays. MCP tools call `complete_async()`; any non-async callers use `complete()`. No new packages needed — both async clients are already declared in `pyproject.toml` and installed.

**Optional dependency handling:** `openai` and `anthropic` must move from hard `dependencies` to `[project.optional-dependencies]` under an `llm` extra. Currently both are listed twice as hard deps (bug in `pyproject.toml` line 18 and 22). Fix during promotion.

---

### Learning Pipeline

#### Execution Log

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| stdlib `json` | 3.10+ | JSONL serialization | Sufficient for append-only log records. No external package needed. |
| stdlib `hashlib` | 3.10+ | SHA-256 code fingerprinting | Direct port of FlameSavant's `sha256(normalise(code))` pattern. |
| stdlib `re` | 3.10+ | Code normalization (strip literals) | Port of JS regex normalizer. |
| `asyncio.to_thread` | 3.10+ | Non-blocking file append | Python 3.10 stdlib. Wraps synchronous `open(mode='a')` so disk writes don't block the event loop. Better than adding `aiofiles` for a single use case. |

**Pattern:** `ExecutionLog` is a class with an in-memory `dict[str, PromotionEntry]` plus JSONL append. On startup, replay existing `.jsonl` file to rebuild the count table. Promotion threshold (default 3) returns `promoted=True` from `record()` to trigger synthesis — identical to FlameSavant.

**Storage location:** `~/.forge-bridge/executions.jsonl` (user home, not project dir). Configurable via `FORGE_LEARNING_DIR` env var.

**Why not a database:** The execution log is append-only observational data. JSONL is crash-safe (partial writes don't corrupt earlier records), portable, and requires zero schema. The PostgreSQL store is for canonical pipeline entities; this log is ephemeral instrumentation.

#### Skill Synthesizer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| stdlib `ast` | 3.10+ | Validate LLM-generated Python source | `ast.parse()` catches syntax errors without executing. Safer than `compile()` + `exec()` for a first-pass check. |
| stdlib `types` + `FunctionType` | 3.10+ | Execute and validate synthesized tool function | After AST validation, exec in isolated namespace to confirm the function is callable with expected signature. |
| `pydantic` (BaseModel) | 2.12.5 (installed) | Skill manifest schema | Synthesized skills have a `SkillManifest` (name, description, parameters, source_hash). Pydantic ensures the LLM output matches required shape before writing. Already installed as FastMCP dependency. |
| LLM Router (`forge_bridge/llm/`) | internal | LLM call for synthesis | Synthesizer calls `router.complete_async(prompt, sensitive=True)` — always local because synthesis prompts contain pipeline code. |

**Synthesis output:** Python function files written to `~/.forge-bridge/skills/<skill_name>.py`. Each file contains a `def build_code(**params) -> str` that returns Flame Python code with parameters substituted. No dynamic `importlib` — the synthesizer writes the file and the RegistryWatcher loads it.

**Validation sequence:**
1. Strip markdown fences from LLM output
2. `ast.parse(source)` — syntax check
3. `exec(compile(source, ...), namespace)` — load into isolated dict
4. Confirm `build_code` callable exists in namespace
5. Call `build_code(**{k: "_test_" for k in params})` — runtime shape check
6. If all pass, write to skills dir

**Why not restrict to ast-only:** AST validation catches syntax but not runtime errors (e.g., undefined names inside the function). The exec-into-namespace pattern catches more failure modes without giving the LLM-generated code access to the real process namespace.

#### Probation System

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `sqlalchemy[asyncio]` | 2.0+ (existing) | Probation record persistence | Probation state (success_count, failure_count, status) belongs in the PostgreSQL store alongside other pipeline entities. Reuses existing `AsyncSession`. |
| stdlib `dataclasses` or `pydantic` | 3.10+ / 2.12.5 | In-memory probation entry | Lightweight — no new package. |

**Probation model:** `SkillProbation(skill_name, source_hash, success_count, failure_count, status: probation|promoted|retired)`. Promoted when success_count >= threshold; retired when failure_count exceeds limit. Wired into bridge.py as an optional post-execution hook.

#### Registry Watcher

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| stdlib `asyncio` + polling | 3.10+ | Watch skills directory for new .py files | No external package needed for a small directory. 500ms polling via `asyncio.sleep(0.5)` in a background task. Simpler than `watchfiles` which adds a Rust extension dep. |
| stdlib `importlib` | 3.10+ | Load skill modules | `importlib.util.spec_from_file_location` + `module_from_spec` — standard pattern for dynamic module loading in Python. |
| `FastMCP.add_tool()` / `remove_tool()` | MCP SDK (installed) | Register/deregister synthesized tools | Confirmed in `mcp/server/fastmcp/tools/tool_manager.py` — `add_tool(fn, name=...)` and `remove_tool(name)` exist and work at runtime. |

**Why polling over watchfiles:** The skills directory has at most tens of files and changes rarely (only when the synthesizer runs). `watchfiles` (Rust-backed inotify/FSEvents wrapper) is appropriate for high-frequency watching. For this use case, polling is simpler, dependency-free, and the 500ms latency is unnoticeable for synthesized tool registration.

**Watcher lifecycle:** Started as `asyncio.create_task()` during MCP server lifespan startup. Scans directory mtime, compares against known mtimes, loads new/changed files. Emits log entries on `skill-added` / `skill-updated` / `skill-error` via a simple callback list (no EventEmitter dependency needed in Python — just a `list[Callable]`).

---

### Pluggable MCP Server

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `FastMCP` (`mcp`) | Installed (protocol 2025-11-25) | Server instance shared across register calls | `FastMCP.add_tool()` is a public runtime API confirmed in source. Tools can be registered after server construction, before `mcp.run()`. |
| Python function protocol | stdlib | `register_tools(mcp: FastMCP) -> None` | The pluggable API is a callable convention, not a framework. Downstream consumers (projekt-forge) call `register_tools(mcp)` to inject their tools before the server starts. No abstract base class needed — duck typing is sufficient. |

**Pattern:**
```python
# forge_bridge/mcp/server.py
def create_server() -> FastMCP:
    mcp = FastMCP("forge_bridge", ...)
    _register_builtin_tools(mcp)
    return mcp

# In __main__.py
mcp = create_server()
# Downstream can call mcp.add_tool(...) before mcp.run()
```

**Why not sub-server composition:** FastMCP has no `mount()` or `include_server()` for composing multiple FastMCP instances. The only runtime extension point is `add_tool()` / `remove_tool()` directly on the instance. Confirmed by reading `server.py` source — no composition API exists.

**Synthesized tool registration:** When RegistryWatcher loads a new skill, it calls `mcp.add_tool(build_mcp_tool_fn(skill), name=skill.name)`. When a skill is retired (probation failure), it calls `mcp.remove_tool(skill.name)`. This means synthesized tools appear/disappear in the live MCP tool list without restart — the MCP protocol re-advertises the tool list on each `tools/list` call.

---

## New Package Dependencies

All additions are minimal. The learning pipeline is almost entirely stdlib.

| Package | Extra | Reason | Where to add |
|---------|-------|---------|-------------|
| `pydantic>=2.0` | none | SkillManifest schema, already installed transitively | Make explicit in `dependencies` (it's already there via mcp) |
| `openai>=1.0` | `llm` | LLM router local calls | Move from `dependencies` to `[project.optional-dependencies].llm` |
| `anthropic>=0.25` | `llm` | LLM router cloud calls | Same — move to `llm` extra |

**No new packages** are required for the execution log, skill synthesizer, registry watcher, or probation system. Everything is stdlib + packages already installed.

---

## pyproject.toml Changes

```toml
[project]
dependencies = [
    "httpx>=0.27",
    "websockets>=13.0",
    "mcp[cli]>=1.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
    "pydantic>=2.0",   # make explicit — already installed via mcp
]

[project.optional-dependencies]
llm = [
    "openai>=1.0",
    "anthropic>=0.25",
]
dev = [
    "pytest",
    "pytest-asyncio",
    "ruff",
]
```

**Note:** `openai` and `anthropic` are currently duplicated as hard deps (bug). Moving them to `[llm]` extra makes forge-bridge installable without LLM packages by default — required by the standalone independence constraint.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Async file I/O | `asyncio.to_thread` wrapping sync `open()` | `aiofiles>=23.0` | `aiofiles` is cleaner API but adds a dep for one use case. Python 3.10+ `asyncio.to_thread` is sufficient. |
| Directory watching | stdlib polling | `watchfiles>=0.19` | `watchfiles` is appropriate for high-change directories; skills dir changes at most a few times per session. Polling at 500ms is adequate and dep-free. |
| Skill validation | `ast.parse` + exec in isolated namespace | `RestrictedPython` | `RestrictedPython` is designed for untrusted user code in multi-tenant systems. Skills are LLM-generated but trusted-enough for this pipeline context. Full sandboxing adds complexity without meaningful security benefit here. |
| Probation persistence | PostgreSQL via existing SQLAlchemy | JSONL flat file | Probation state is relational (joins with skill registry, queried by name). SQL is the right tool. JSONL would require manual query logic. |
| LLM routing | Custom `LLMRouter` class | `litellm` | `litellm` provides a unified interface across 100+ LLM providers. Valuable for general-purpose routing, but the sensitivity-based two-tier routing here is bespoke to forge's data-egress policy. `litellm` would add ~50MB of dependencies for a routing pattern that fits in 50 lines. |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| FastMCP `add_tool()` / `remove_tool()` API | HIGH | Read directly from installed source: `mcp/server/fastmcp/tools/tool_manager.py` and `server.py` |
| `AsyncOpenAI` / `AsyncAnthropic` availability | HIGH | Confirmed in `openai/_client.py` (class line 461) and `anthropic/_client.py` (class line 293) |
| openai SDK version | HIGH | Read from `openai/_version.py`: 2.29.0 |
| anthropic SDK version | HIGH | Read from `anthropic/_version.py`: 0.86.0 |
| pydantic version | HIGH | Read from `pydantic/version.py`: 2.12.5 |
| MCP protocol version | HIGH | Read from `mcp/types.py`: LATEST_PROTOCOL_VERSION = "2025-11-25" |
| Stdlib sufficiency for JSONL log | HIGH | Python 3.10+ stdlib — no ambiguity |
| Polling vs watchfiles recommendation | MEDIUM | Based on use-case analysis; watchfiles would also work fine if preference changes |
| No FastMCP server composition API | HIGH | Searched `server.py` for `mount`, `include_server`, `import_server`, `merge`, `compose` — none found |

---

## Sources

- Installed MCP SDK source: `/Users/cnoellert/Documents/GitHub/forge-bridge/.venv/lib/python3.13/site-packages/mcp/`
  - `server/fastmcp/tools/tool_manager.py` — `add_tool()`, `remove_tool()`
  - `server/fastmcp/server.py` — `FastMCP.add_tool()`, `FastMCP.remove_tool()`, no composition API
  - `types.py` — `LATEST_PROTOCOL_VERSION = "2025-11-25"`
  - `shared/version.py` — `SUPPORTED_PROTOCOL_VERSIONS` includes 2025-06-18, 2025-11-25
- Installed OpenAI SDK: `.venv/lib/python3.13/site-packages/openai/_version.py` (2.29.0), `_client.py` (AsyncOpenAI confirmed)
- Installed Anthropic SDK: `.venv/lib/python3.13/site-packages/anthropic/_version.py` (0.86.0), `_client.py` (AsyncAnthropic confirmed)
- Installed Pydantic: `.venv/lib/python3.13/site-packages/pydantic/version.py` (2.12.5)
- FlameSavant source (ported design): `/Users/cnoellert/Documents/GitHub/FlameSavant/src/learning/ExecutionLog.js`, `RegistryWatcher.js`, `src/agents/SkillSynthesizer.js`
- Existing llm_router.py: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/llm_router.py`
- pyproject.toml: `/Users/cnoellert/Documents/GitHub/forge-bridge/pyproject.toml`

---

*Stack research: 2026-04-14*
