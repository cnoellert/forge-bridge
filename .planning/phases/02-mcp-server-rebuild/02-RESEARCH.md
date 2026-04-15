# Phase 2: MCP Server Rebuild - Research

**Researched:** 2026-04-14
**Domain:** FastMCP 1.26 pluggable tool registry, asyncio file-watching, MCP protocol notifications
**Confidence:** HIGH

---

## Summary

Phase 2 rebuilds `forge_bridge/mcp/server.py` so that tool registration is namespace-enforced, source-tagged, and open for downstream injection — without breaking the ~30 existing tool registrations that Phase 1 produced.

The current server registers all tools as flat `mcp.tool()` calls at module import time. Phase 2 replaces this with: (a) a `register_tools(mcp, fns)` helper that enforces prefix rules and attaches `_source` metadata, (b) a reserved-name guard that prevents `synth_*` tools from being overwritten by static registrations, and (c) a file-system watcher (`watcher.py`) that hot-loads synthesized Python modules from `mcp/synthesized/` using `importlib` and calls `mcp.add_tool()` / `mcp.remove_tool()` at runtime.

The key verified facts are: FastMCP 1.26 (installed version) exposes `add_tool(fn, name=...)` and `remove_tool(name)` on the live `FastMCP` instance, backed by an in-memory `dict[str, Tool]` in `ToolManager._tools`. The MCP protocol defines `ToolListChangedNotification` and the session has `send_tool_list_changed()`, but FastMCP does NOT call it automatically when `add_tool`/`remove_tool` is invoked — the watcher must call it manually via the active session. Source tagging via `_source` is not a FastMCP native concept; it is implemented as a function attribute set before registration, or via `meta={"_source": "..."}` on `add_tool()`.

**Primary recommendation:** Wrap FastMCP's existing `add_tool`/`remove_tool` with a thin registry layer in a new `forge_bridge/mcp/registry.py`. The watcher lives in `forge_bridge/learning/watcher.py`. The public `register_tools()` entry point lives in `forge_bridge/mcp/__init__.py`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-01 | Rebuild mcp/server.py with flame_*/forge_*/synth_* namespace separation | Registry module enforces prefix allowlist; static registrations route through it |
| MCP-02 | Dynamic tool registration using FastMCP add_tool()/remove_tool() for synthesized tools | Verified: both methods exist on FastMCP 1.26 and mutate `_tool_manager._tools` immediately |
| MCP-03 | Create forge_bridge/learning/watcher.py — asyncio polling on mcp/synthesized/, importlib hot-load | `asyncio.get_event_loop().run_in_executor` or pure `asyncio` sleep loop; `importlib.util.spec_from_file_location` pattern documented below |
| MCP-04 | Expose register_tools(mcp) pluggable API for downstream consumers (projekt-forge) | Thin wrapper over `mcp.add_tool()` that prefixes + source-tags; called before `mcp.run()` |
| MCP-05 | Source tagging on all tools (_source: builtin/synthesized/user-taught) visible to LLM agents | `mcp.add_tool(fn, name=..., meta={"_source": "builtin"})` stores in `Tool.meta`; surfaced in tools/list response |
| MCP-06 | Synthesized tools use synth_* prefix, enforced at synthesis time against reserved name set | Registry raises `ValueError` if `synth_*` is passed via static registration path; only watcher/synthesizer may register under this prefix |
</phase_requirements>

---

## Standard Stack

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mcp[cli] | 1.26.0 (installed) | FastMCP server, Tool, ToolManager, session | Already the project's MCP framework |
| asyncio | stdlib | Event loop for watcher polling | No extra dependency |
| importlib.util | stdlib | `spec_from_file_location` hot-load of synthesized .py files | Standard Python dynamic import |
| watchfiles | NOT installed | Alternative file-watch approach | Rejected — adds C extension dependency; asyncio sleep loop is sufficient for this use case |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path manipulation for synthesized/ directory | Used by watcher to enumerate .py files |
| hashlib | stdlib | SHA-256 of file content to detect changes vs re-imports | Avoid re-loading unchanged files |

**Installation:** No new packages required. All dependencies are stdlib + already-installed `mcp[cli]`.

---

## Architecture Patterns

### Recommended Project Structure

After Phase 2 the MCP package layout becomes:

```
forge_bridge/
├── mcp/
│   ├── __init__.py          # Exports: register_tools(), get_mcp()
│   ├── __main__.py          # Entry: python -m forge_bridge.mcp
│   ├── server.py            # FastMCP instance + lifespan; calls registry.register_builtins()
│   ├── registry.py          # NEW: namespace guard, source tagging, reserved-name set
│   └── tools.py             # Unchanged: forge_bridge WebSocket tool implementations
└── learning/
    └── watcher.py           # NEW: asyncio polling loop, importlib hot-load, synth_ registration
```

Synthesized tools land at:
```
mcp/
└── synthesized/
    ├── synth_my_tool.py     # Each file = one tool function named identically to file stem
    └── synth_other_tool.py
```

### Pattern 1: Registry Module with Namespace Enforcement

**What:** A `registry.py` module wraps `mcp.add_tool()` and enforces prefix rules before delegation.

**When to use:** Every tool registration — static builtins, user-injected, synthesized.

```python
# Source: direct inspection of FastMCP 1.26.0 ToolManager source
# forge_bridge/mcp/registry.py

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

# Prefixes exclusively owned by the synthesis pipeline.
# Static registrations are blocked from using these.
_SYNTH_RESERVED_PREFIXES: frozenset[str] = frozenset({"synth_"})

# All valid prefixes for this server
_VALID_PREFIXES: frozenset[str] = frozenset({"flame_", "forge_", "synth_"})


def _validate_name(name: str, source: str) -> None:
    if not any(name.startswith(p) for p in _VALID_PREFIXES):
        raise ValueError(
            f"Tool name {name!r} must start with flame_, forge_, or synth_. "
            f"Got source={source!r}."
        )
    if source != "synthesized" and any(name.startswith(p) for p in _SYNTH_RESERVED_PREFIXES):
        raise ValueError(
            f"Tool name {name!r} uses a reserved synth_ prefix. "
            "Only the synthesis pipeline may register under synth_."
        )


def register_tool(
    mcp: FastMCP,
    fn: Callable[..., Any],
    name: str,
    source: str,          # "builtin" | "synthesized" | "user-taught"
    annotations: dict[str, Any] | None = None,
) -> None:
    """Register a single tool with namespace enforcement and source tagging."""
    _validate_name(name, source)
    mcp.add_tool(
        fn,
        name=name,
        annotations=annotations,
        meta={"_source": source},
    )


def register_tools(
    mcp: FastMCP,
    fns: list[Callable[..., Any]],
    prefix: str = "",
    source: str = "user-taught",
) -> None:
    """
    Public API for downstream consumers (e.g. projekt-forge).

    Usage before mcp.run():
        from forge_bridge.mcp import register_tools, get_mcp
        register_tools(get_mcp(), [my_fn1, my_fn2], prefix="forge_")
    """
    for fn in fns:
        name = f"{prefix}{fn.__name__}" if prefix else fn.__name__
        register_tool(mcp, fn, name=name, source=source)


def register_builtins(mcp: FastMCP) -> None:
    """Register all builtin flame_* and forge_* tools. Called by server.py at import time."""
    # Existing registrations from Phase 1 are moved here and routed through register_tool()
    ...
```

### Pattern 2: Source Tagging via `meta=`

FastMCP 1.26 `add_tool()` accepts `meta: dict[str, Any] | None`. This dict is stored on the `Tool` object and returned in `tools/list` responses under `_meta`. The `_source` field is therefore a first-class metadata key visible to LLM agents.

```python
# Source: FastMCP 1.26.0 list_tools handler in server.py
# The MCPTool is built with _meta=info.meta — so meta dict is passed through verbatim
mcp.add_tool(fn, name="flame_foo", meta={"_source": "builtin"})
```

### Pattern 3: Asyncio Watcher with importlib Hot-Load

**What:** A background `asyncio` coroutine polls `mcp/synthesized/` every N seconds, detects new/changed .py files by SHA-256 hash, imports them, and registers/re-registers via `mcp.add_tool()` / `mcp.remove_tool()`.

**When to use:** Only invoked during lifespan startup inside `server.py`.

```python
# forge_bridge/learning/watcher.py
import asyncio
import hashlib
import importlib.util
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_SYNTHESIZED_DIR = Path(__file__).parent.parent / "mcp" / "synthesized"
_POLL_INTERVAL = 5.0  # seconds


async def watch_synthesized_tools(mcp: "FastMCP") -> None:
    """Asyncio polling loop: hot-load new/changed synthesized tools."""
    seen: dict[str, str] = {}  # stem -> sha256

    while True:
        await asyncio.sleep(_POLL_INTERVAL)
        try:
            _scan_once(mcp, seen)
        except Exception:
            logger.exception("Error in synthesized tool watcher")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scan_once(mcp: "FastMCP", seen: dict[str, str]) -> None:
    if not _SYNTHESIZED_DIR.exists():
        return

    current_stems = set()
    for path in _SYNTHESIZED_DIR.glob("*.py"):
        if path.stem.startswith("__"):
            continue
        stem = path.stem
        current_stems.add(stem)
        digest = _sha256(path)
        if seen.get(stem) == digest:
            continue
        # New or changed file — (re)load
        if stem in seen:
            try:
                mcp.remove_tool(stem)
            except Exception:
                pass
        fn = _load_fn(path, stem)
        if fn is None:
            continue
        from forge_bridge.mcp.registry import register_tool
        register_tool(mcp, fn, name=stem, source="synthesized")
        seen[stem] = digest
        logger.info(f"Registered synthesized tool: {stem}")

    # Remove tools whose files disappeared
    for stem in list(seen):
        if stem not in current_stems:
            try:
                mcp.remove_tool(stem)
                logger.info(f"Removed synthesized tool: {stem}")
            except Exception:
                pass
            del seen[stem]


def _load_fn(path: Path, stem: str):
    """Load a Python file and return the callable named `stem`."""
    spec = importlib.util.spec_from_file_location(stem, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        logger.exception(f"Failed to load {path}")
        return None
    fn = getattr(module, stem, None)
    if not callable(fn):
        logger.warning(f"{path}: no callable named {stem!r}")
        return None
    return fn
```

### Pattern 4: Lifespan Integration for Watcher

FastMCP 1.26 accepts a `lifespan` context manager at construction time. The watcher task must be launched inside this context so it runs concurrently with the server.

```python
# forge_bridge/mcp/server.py (updated)
from contextlib import asynccontextmanager
import asyncio
from mcp.server.fastmcp import FastMCP
from forge_bridge.learning.watcher import watch_synthesized_tools

@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    task = asyncio.create_task(watch_synthesized_tools(mcp_server))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

mcp = FastMCP("forge_bridge", lifespan=_lifespan, ...)
```

### Pattern 5: ToolListChangedNotification (Manual)

FastMCP does NOT auto-send `ToolListChangedNotification` when `add_tool`/`remove_tool` is called. The session method `send_tool_list_changed()` must be called explicitly. However, in stdio transport (Claude Desktop), the client polls `tools/list` on reconnect — so the notification is a nice-to-have, not required for basic correctness.

For Phase 2, the watcher does NOT need to send the notification (clients re-poll). This avoids coupling the watcher to active session objects. Leave notification as a Phase 3 enhancement if needed.

**Verification:** Searched all mcp 1.26.0 source files for `ToolListChanged` — it is only defined in `types.py` and in `session.py:send_tool_list_changed()`. FastMCP's `add_tool`/`remove_tool` do not call it. (HIGH confidence — source confirmed.)

### Anti-Patterns to Avoid

- **Registering under wrong prefix:** Tools without `flame_`, `forge_`, or `synth_` prefix will be invisible to namespaced queries. Registry must reject them.
- **Allowing synth_ from static path:** If `register_builtins()` calls `register_tool(source="builtin")` with a `synth_` name, the guard must raise `ValueError`.
- **Reloading unchanged files:** Always compare SHA-256 before re-importing; re-importing is slow and resets module state.
- **Creating task outside lifespan:** `asyncio.create_task()` called at module level (before event loop runs) silently fails. Always launch watcher task inside the lifespan context manager.
- **Using `mcp.tool()` decorator for synthesized tools:** `mcp.tool()` returns a decorator and does not accept runtime callables with dynamic names. Use `mcp.add_tool(fn, name=...)` instead.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tool storage | Custom dict wrapper | `mcp._tool_manager._tools` via `add_tool()`/`remove_tool()` | FastMCP already has thread-safe dict + duplicate warning |
| File change detection | inotify/kqueue bindings | SHA-256 hash comparison in polling loop | No C extension, no platform dependency, sufficient for 5s polling interval |
| Module loading | `exec()` of file content | `importlib.util.spec_from_file_location` | Proper module isolation, correct `__name__`, exception propagation |
| Source visibility | Custom tool wrapper class | `meta={"_source": "..."}` on `add_tool()` | FastMCP passes `meta` through to `_meta` field in protocol response |

**Key insight:** FastMCP's internal `ToolManager` is a plain `dict[str, Tool]`. Dynamic registration is supported by design. No monkey-patching or private API abuse is required.

---

## Common Pitfalls

### Pitfall 1: add_tool Does Not Overwrite on Duplicate

**What goes wrong:** `ToolManager.add_tool()` returns the *existing* tool unchanged if the name is already registered (with a warning log). Calling `add_tool()` to update a synthesized tool silently no-ops.

**Why it happens:** `existing = self._tools.get(tool.name); if existing: return existing` — the guard returns early.

**How to avoid:** Always call `mcp.remove_tool(name)` before `mcp.add_tool(fn, name=...)` when hot-reloading a changed synthesized file. The watcher must do this in the correct order.

**Warning signs:** Synthesized tool appears in tool list but still runs old behaviour after file change.

### Pitfall 2: Module-Level Task Creation Fails Silently

**What goes wrong:** `asyncio.create_task(watch_synthesized_tools(mcp))` at module import time raises `RuntimeError: no running event loop` or creates a task that is never awaited.

**Why it happens:** The asyncio event loop is not running during module import — only during `mcp.run()`.

**How to avoid:** Launch the watcher task exclusively inside the `lifespan` context manager, which is called from within the running event loop.

### Pitfall 3: Synthesized Tool Signature Incompatible with FastMCP

**What goes wrong:** FastMCP uses `inspect.signature()` + type hints to build the JSON schema for tool input. A synthesized function with `*args`, `**kwargs`, or missing type annotations will fail at registration or produce an empty input schema.

**Why it happens:** `Tool.from_function()` calls Pydantic's schema builder on the function signature. Untyped params produce `Any` fields; variadic params may raise.

**How to avoid:** Validation in Phase 3 (LEARN-09) must check that synthesized functions have fully annotated, non-variadic signatures. Phase 2 watcher should wrap the registration in a try/except and log the error without crashing the watcher loop.

### Pitfall 4: register_tools() Called After mcp.run()

**What goes wrong:** Downstream consumer (projekt-forge) calls `register_tools()` after the MCP server is running. Tools appear in `_tool_manager._tools` but the client has already received the initial tool list.

**Why it happens:** `register_tools()` is a pre-run API (no notification sent). The MCP spec requires a `tools/list_changed` notification to inform the client.

**How to avoid:** Document in the public API docstring that `register_tools()` must be called before `mcp.run()`. For post-run injection, use the watcher pathway (which can send `send_tool_list_changed()` if needed).

### Pitfall 5: Existing Registration Pattern Breakage

**What goes wrong:** The current `server.py` registers ~30 tools directly via `mcp.tool()` decorators at module level. Moving them through `register_tool()` changes the call signature slightly (annotations dict becomes separate from the `mcp.tool()` annotations kwarg).

**Why it happens:** `mcp.tool(annotations={...})` maps to `add_tool(fn, annotations=ToolAnnotations(...))`. The `meta=` parameter is separate from `annotations=`.

**How to avoid:** In `register_builtins()`, pass existing annotation dicts through the `annotations=` parameter and add `meta={"_source": "builtin"}` separately. Do not conflate them.

---

## Code Examples

### Verified: add_tool with name and meta

```python
# Source: FastMCP 1.26.0 — forge/lib/python3.11/site-packages/mcp/server/fastmcp/__init__.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("forge_bridge")

def flame_ping() -> str:
    """Check Flame connection."""
    return "pong"

mcp.add_tool(
    flame_ping,
    name="flame_ping",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    meta={"_source": "builtin"},
)
```

### Verified: remove_tool before re-registration

```python
# Source: ToolManager.remove_tool — raises ToolError if name unknown
try:
    mcp.remove_tool("synth_my_tool")
except Exception:
    pass  # Tool not yet registered; safe to ignore
mcp.add_tool(new_fn, name="synth_my_tool", meta={"_source": "synthesized"})
```

### Verified: importlib hot-load pattern

```python
# Source: Python 3.11 stdlib importlib.util documentation
import importlib.util
from pathlib import Path

def load_tool_fn(path: Path, fn_name: str):
    spec = importlib.util.spec_from_file_location(fn_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, fn_name)
```

### Verified: ToolManager internal storage

```python
# Source: ToolManager class — _tools is dict[str, Tool]
# Confirmed via: inspect.getsource(ToolManager)
# Tools are stored as: self._tools[tool.name] = tool
# list_tools() returns: list(self._tools.values())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@mcp.tool()` decorator only | `mcp.add_tool(fn, name=...)` for runtime registration | FastMCP >= 1.0 | Enables dynamic tool injection without restart |
| No source metadata | `meta={"_source": "..."}` visible in tool list | FastMCP >= 1.0 (meta param) | LLM agents can filter by source |
| No namespace enforcement | Application-level prefix guard | N/A (not a FastMCP feature) | Must be implemented in registry.py |

**Deprecated/outdated:**
- `server.py` monolithic registration: Phase 1 left all registrations in a single 500-line file. Phase 2 moves them into `registry.py:register_builtins()` for clarity and testability.

---

## Open Questions

1. **ToolListChangedNotification in stdio transport**
   - What we know: `ServerSession.send_tool_list_changed()` exists and sends the notification. FastMCP does not call it automatically. Claude Desktop (stdio) re-polls `tools/list` on each context window.
   - What's unclear: Whether Claude Desktop actually picks up newly registered tools mid-session without a notification, or whether it only re-polls on restart.
   - Recommendation: Defer notification sending to Phase 3 (LEARN-03 watcher). For Phase 2, document the limitation: tools added after `mcp.run()` require client restart to appear. This is acceptable since Phase 2 watcher is for synthesized tools which are a Phase 3 concern.

2. **`mcp/synthesized/` directory location**
   - What we know: MCP-03 says "asyncio polling on mcp/synthesized/". This path is relative to the package.
   - What's unclear: Whether this is `forge_bridge/mcp/synthesized/` (inside the package) or `~/.forge-bridge/synthesized/` (user data dir).
   - Recommendation: Use `~/.forge-bridge/synthesized/` to match the JSONL execution log location (`~/.forge-bridge/executions.jsonl` per LEARN-02). Keeps runtime data out of the installed package.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (already installed) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` asyncio_mode = "auto" |
| Quick run command | `pytest tests/test_mcp_registry.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | flame_* and forge_* tools appear in tool list under correct prefixes | unit | `pytest tests/test_mcp_registry.py::test_builtin_namespace -x` | ❌ Wave 0 |
| MCP-01 | synth_* prefix blocked for non-synthesized source | unit | `pytest tests/test_mcp_registry.py::test_synth_prefix_rejected_from_static -x` | ❌ Wave 0 |
| MCP-02 | add_tool registers tool; remove_tool deregisters it | unit | `pytest tests/test_mcp_registry.py::test_dynamic_registration -x` | ❌ Wave 0 |
| MCP-03 | Watcher loads a new .py file and calls add_tool | unit | `pytest tests/test_watcher.py::test_watcher_loads_new_file -x` | ❌ Wave 0 |
| MCP-03 | Watcher re-registers changed file after SHA256 diff | unit | `pytest tests/test_watcher.py::test_watcher_reloads_changed_file -x` | ❌ Wave 0 |
| MCP-03 | Watcher removes tool when file is deleted | unit | `pytest tests/test_watcher.py::test_watcher_removes_deleted_file -x` | ❌ Wave 0 |
| MCP-04 | register_tools(mcp, [fn1, fn2]) adds tools to live FastMCP instance | unit | `pytest tests/test_mcp_registry.py::test_register_tools_api -x` | ❌ Wave 0 |
| MCP-05 | All tools in list carry _source field with one of: builtin, synthesized, user-taught | unit | `pytest tests/test_mcp_registry.py::test_source_tagging -x` | ❌ Wave 0 |
| MCP-06 | synth_* names accepted from synthesized source, rejected from builtin | unit | `pytest tests/test_mcp_registry.py::test_synth_name_enforcement -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_mcp_registry.py tests/test_watcher.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mcp_registry.py` — covers MCP-01, MCP-02, MCP-04, MCP-05, MCP-06
- [ ] `tests/test_watcher.py` — covers MCP-03
- [ ] `forge_bridge/mcp/registry.py` — new module (Wave 0 stub with stubs that raise NotImplementedError)
- [ ] `forge_bridge/learning/watcher.py` — new module (Wave 0 stub)
- [ ] `forge_bridge/mcp/synthesized/` directory — created during Phase 2 or watcher init

---

## Sources

### Primary (HIGH confidence)

- FastMCP 1.26.0 installed source: `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages/mcp/server/fastmcp/` — `add_tool`, `remove_tool`, `ToolManager`, `_setup_handlers` all inspected directly
- mcp 1.26.0 installed source: `mcp/server/session.py:send_tool_list_changed()` — confirmed notification method exists but is not auto-called
- mcp 1.26.0 types: `mcp/types.py:ToolListChangedNotification` — confirmed protocol type exists
- Python 3.11 stdlib: `importlib.util.spec_from_file_location` — standard hot-load pattern

### Secondary (MEDIUM confidence)

- forge_bridge/mcp/server.py — existing registration patterns, ~30 tool registrations reviewed directly
- MCP-03 requirement spec — "asyncio polling on mcp/synthesized/" wording taken as specification, directory location inferred from LEARN-02 `~/.forge-bridge/` pattern

### Tertiary (LOW confidence)

- Claude Desktop behaviour re: tool list refresh in stdio mode — not verified against Claude Desktop source; based on known MCP protocol behaviour

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already installed, versions verified by `pip show`
- Architecture: HIGH — FastMCP internals inspected from installed source; no guessing
- Pitfalls: HIGH — duplicate-guard and no-overwrite behaviour confirmed from `ToolManager.add_tool` source
- ToolListChangedNotification behaviour: MEDIUM — confirmed the method exists and is not auto-called; Claude Desktop polling behaviour is LOW

**Research date:** 2026-04-14
**Valid until:** 2026-07-14 (mcp is moderately fast-moving; re-verify if mcp version changes)
