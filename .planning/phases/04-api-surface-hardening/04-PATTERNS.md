# Phase 4: API Surface Hardening — Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 10 (9 modified, 1 new)
**Analogs found:** 10 / 10

---

## File Classification

| File | New / Modified | Role | Data Flow | Closest Analog | Match Quality |
|------|----------------|------|-----------|----------------|---------------|
| `forge_bridge/__init__.py` | Modified | package barrel | — (re-export) | `forge_bridge/core/__init__.py` | exact |
| `forge_bridge/llm/router.py` | Modified | service (LLM client) | request-response (async) | `forge_bridge/learning/execution_log.py` (ExecutionLog ctor env-fallback) + `forge_bridge/bridge.py` (module-level env reads) | role-match |
| `forge_bridge/mcp/server.py` | Modified | server lifecycle | lifespan / pub-sub | (self — lifespan already present; see `_lifespan` + `_startup` / `_shutdown`) | exact |
| `forge_bridge/mcp/registry.py` | Modified | utility (tool registration) | request-response | (self — `_validate_name` + `register_tool` in same file) | exact |
| `forge_bridge/learning/synthesizer.py` | Modified | service (LLM-driven codegen) | async request-response | `forge_bridge/learning/execution_log.py::ExecutionLog` (class wraps prior module-level state) | exact |
| `forge_bridge/tools/publish.py` | Modified | Pydantic model / tool | config-default | `forge_bridge/bridge.py` `_config` module-level env read (lines 32-37) | role-match |
| `pyproject.toml` | Modified | config | n/a | — (one-line version bump) | n/a |
| `tests/test_synthesizer.py` | Modified | test | unit+async | existing `TestSynthesize` class (same file, lines 144-233) | exact |
| `tests/test_llm.py` | Modified | test | unit | `tests/test_execution_log.py::test_env_var_overrides_threshold` (monkeypatch.setenv + fresh instance) | exact |
| `tests/test_public_api.py` | **Created** | test | unit+smoke+integration | `tests/test_mcp_registry.py` (structure, `_fresh_mcp()`, FastMCP imports) + `tests/test_llm.py::test_optional_import_guard` (`sys.modules` manipulation) | role-match |

---

## Pattern Assignments

### `forge_bridge/__init__.py` (package barrel)

**Analog:** `forge_bridge/core/__init__.py`

This is the canonical barrel file shape in the codebase: a docstring documenting the public import, groups of `from … import …` statements organized by source module, and a single explicit `__all__` list at the bottom. Copy this structure verbatim for the root `__init__.py` — replace the `core` modules with the 11 symbols from D-02.

**Module docstring pattern** (`forge_bridge/core/__init__.py:1-22`):
```python
"""
forge-bridge core vocabulary.

    from forge_bridge.core import (
        # Entities
        Project, Sequence, Shot, Asset, Version, Media, Stack, Layer,
        ...
    )
"""
```

**Grouped imports with trailing commas** (`forge_bridge/core/__init__.py:24-65`):
```python
from forge_bridge.core.entities import (
    Asset,
    BridgeEntity,
    Layer,
    Media,
    Project,
    ...
)
from forge_bridge.core.traits import (
    Locatable,
    Location,
    ...
)
```

**Explicit `__all__` at bottom, grouped by logical category with comments** (`forge_bridge/core/__init__.py:67-86`):
```python
__all__ = [
    # Entities
    "BridgeEntity", "Project", "Sequence", "Shot", "Asset",
    "Version", "Media", "Stack", "Layer",
    # Traits
    "Versionable", "Locatable", "Relational",
    # Relationship primitives
    "Relationship", "SYSTEM_REL_KEYS",
    ...
]
```

**Smaller existing barrel to mirror** (`forge_bridge/mcp/__init__.py:1-12` — already matches the D-02 shape for the mcp subpackage):
```python
"""forge_bridge.mcp — MCP server with pluggable tool registry."""

from forge_bridge.mcp.registry import register_tools
from forge_bridge.mcp.server import mcp as _mcp


def get_mcp():
    """Return the FastMCP server instance for tool registration."""
    return _mcp


__all__ = ["register_tools", "get_mcp"]
```

Planner note: core/__init__.py does **not** include `from __future__ import annotations` (it's a pure re-export file with no forward refs). Follow that. `forge_bridge/llm/__init__.py` and `forge_bridge/mcp/__init__.py` also omit it. The root __init__ should follow suit.

---

### `forge_bridge/llm/router.py` (service, request-response async)

**Primary analog:** `forge_bridge/learning/execution_log.py::ExecutionLog.__init__` — the cleanest example in the codebase of "kwarg → env var → hardcoded default" precedence **inside** `__init__`, exactly the shape D-05/D-06 require.

**Env-fallback inside `__init__`** (`forge_bridge/learning/execution_log.py:54-70`):
```python
class ExecutionLog:
    """Append-only JSONL execution log with AST normalization and promotion counters.

    Args:
        log_path: Path to the JSONL file. Defaults to ~/.forge-bridge/executions.jsonl.
        threshold: Number of identical (normalized) executions before promotion signal.
                   Overridden by FORGE_PROMOTION_THRESHOLD env var if set.
    """

    def __init__(self, log_path: Path = LOG_PATH, threshold: int = 3) -> None:
        self._path = log_path
        self._threshold = int(os.environ.get("FORGE_PROMOTION_THRESHOLD", threshold))
        self._counters: dict[str, int] = {}
        self._promoted: set[str] = set()
        ...
```

Note: this is *close* but not quite D-06's exact shape (arg → env → default). `ExecutionLog` treats the arg as the default-if-env-missing. D-06 wants **explicit arg wins**, then env, then hardcoded. Adapt to this shape:

```python
# Template for LLMRouter.__init__ (based on D-06 precedence)
def __init__(
    self,
    local_url: str | None = None,
    local_model: str | None = None,
    cloud_model: str | None = None,
    system_prompt: str | None = None,
) -> None:
    self.local_url = local_url or os.environ.get(
        "FORGE_LOCAL_LLM_URL", "http://localhost:11434/v1"
    )
    self.local_model = local_model or os.environ.get(
        "FORGE_LOCAL_MODEL", "qwen2.5-coder:32b"
    )
    self.cloud_model = cloud_model or os.environ.get(
        "FORGE_CLOUD_MODEL", "claude-opus-4-6"
    )
    self.system_prompt = system_prompt or os.environ.get(
        "FORGE_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT
    )
    self._local_client: Optional["AsyncOpenAI"] = None
    self._cloud_client: Optional["AsyncAnthropic"] = None
```

**Current code to modify** (`forge_bridge/llm/router.py:41-64` — module-level constants to remove or demote):
```python
LOCAL_BASE_URL = os.environ.get("FORGE_LOCAL_LLM_URL", "http://assist-01:11434/v1")
LOCAL_MODEL    = os.environ.get("FORGE_LOCAL_MODEL",   "qwen2.5-coder:32b")
CLOUD_MODEL    = os.environ.get("FORGE_CLOUD_MODEL",   "claude-opus-4-6")

_DEFAULT_SYSTEM_PROMPT = """
You are a VFX pipeline assistant embedded in FORGE, a suite of Autodesk Flame
Python tools for shot management and publishing.

Key context:
- Flame version: 2026, Python API via `import flame`
- Shot naming convention: {project}_{shot}_{layer}_v{version}  e.g. ACM_0010_comp_v003
- Openclip files: XML-based multi-version containers written by Flame's MIO
  reader. Use Flame's native bracket notation [0991-1017] for frame ranges,
  NOT printf %04d notation.
- forge_bridge PostgreSQL on portofino: host=localhost port=7533 user=forge db=forge_bridge
- Desktop: Flame on portofino (MacBook Pro, macOS, Apple Silicon)
- Render: flame-01 (Threadripper, Linux, RTX A5000 Ada) via Backburner / cmdjob
""".strip()

SYSTEM_PROMPT = os.environ.get("FORGE_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT)
```

**D-10 purge target — retained vs. purged tokens** (extracted from CONTEXT.md D-10):

| Keep | Remove |
|------|--------|
| "Flame version: 2026" | "portofino" (hostname AND mount path) |
| "Python API via `import flame`" | "assist-01" (hostname) |
| "{project}_{shot}_{layer}_v{version}" | "ACM_" (client-specific shot prefix) |
| "[0991-1017]" (openclip bracket notation) | "flame-01" (hostname) |
| "concise, production-ready Python" tone | Backburner / cmdjob |
| `%04d` contrast | DB credentials (host / port / user / db) |
|  | machine specs (MacBook / Threadripper / Linux / RTX A5000 Ada) |

**Current `__init__` to replace** (`forge_bridge/llm/router.py:87-89`):
```python
def __init__(self):
    self._local_client: Optional["AsyncOpenAI"] = None  # type: ignore[name-defined]
    self._cloud_client: Optional["AsyncAnthropic"] = None  # type: ignore[name-defined]
```

**Attribute read sites to update** (currently read module constants; must switch to `self.local_url` / `self.local_model` / `self.cloud_model` / `self.system_prompt`):

- `forge_bridge/llm/router.py:153-154` — `ahealth_check()` references `LOCAL_MODEL` / `CLOUD_MODEL`
- `forge_bridge/llm/router.py:188-189` — `_get_local_client()` uses `base_url=LOCAL_BASE_URL`
- `forge_bridge/llm/router.py:213` — `_async_local()` uses `SYSTEM_PROMPT`
- `forge_bridge/llm/router.py:221` — `_async_local()` uses `LOCAL_MODEL`
- `forge_bridge/llm/router.py:227` — error message references `LOCAL_BASE_URL`
- `forge_bridge/llm/router.py:237` — `_async_cloud()` uses `CLOUD_MODEL`

**Existing lazy-import pattern to preserve** (`forge_bridge/llm/router.py:178-203`) — unchanged by Phase 4; the ImportError guard for optional deps stays intact:
```python
def _get_local_client(self):
    if self._local_client is None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError(
                "openai package not installed. "
                "Install LLM support: pip install forge-bridge[llm]"
            )
        ...
```

**Existing singleton pattern to preserve** (`forge_bridge/llm/router.py:247-258`) — D-09 says `get_router()` stays env-only:
```python
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Return the shared LLMRouter singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
```

---

### `forge_bridge/mcp/server.py` (server lifecycle)

**Analog:** Self — the file already has the lifespan pattern in place. The Phase 4 changes are rename + add a flag; the structure stays.

**Lifespan context manager to modify** (`forge_bridge/mcp/server.py:67-86`):
```python
@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    """Server lifespan: connect client, start watcher, clean up on exit."""
    # Connect to forge-bridge
    await _startup()

    # Launch synthesized tool watcher as background task
    from forge_bridge.learning.watcher import watch_synthesized_tools
    watcher_task = asyncio.create_task(watch_synthesized_tools(mcp_server))

    try:
        yield
    finally:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
        await _shutdown()
```

**D-14 flag placement** — set `_server_started = True` after `await startup_bridge(...)` completes and **before** `yield`, so the guard trips during the yielded run phase. Clear it on shutdown if we want idempotent behavior (optional; CONTEXT.md doesn't require it):

```python
# Template
_server_started: bool = False  # module-level, near _client on line 50


@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    global _server_started
    await startup_bridge()
    _server_started = True  # ← D-14 transition here

    from forge_bridge.learning.watcher import watch_synthesized_tools
    watcher_task = asyncio.create_task(watch_synthesized_tools(mcp_server))

    try:
        yield
    finally:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
        await shutdown_bridge()
        _server_started = False  # optional: reset for clean teardown
```

**D-11/D-12/D-13 rename targets** (`forge_bridge/mcp/server.py:110-140`):
```python
async def _startup() -> None:
    """Connect to forge-bridge server before serving MCP requests."""
    global _client

    server_url  = os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")
    client_name = os.environ.get("FORGE_MCP_CLIENT_NAME", "mcp_claude")

    _client = AsyncClient(
        client_name=client_name,
        server_url=server_url,
        endpoint_type="mcp",
        auto_reconnect=True,
    )

    await _client.start()

    try:
        await _client.wait_until_connected(timeout=10.0)
        logger.info(f"Connected to forge-bridge at {server_url}")
    except Exception as e:
        logger.warning(
            f"Could not connect to forge-bridge at {server_url}: {e}\n"
            "forge_* tools will fail. flame_* tools still work if Flame is running."
        )


async def _shutdown() -> None:
    global _client
    if _client:
        await _client.stop()
        _client = None
```

**Target shape after rename** (matches D-12: arg → env → default precedence like `LLMRouter`):
```python
async def startup_bridge(
    server_url: str | None = None,
    client_name: str | None = None,
) -> None:
    """Connect to forge-bridge server before serving MCP requests."""
    global _client

    server_url = server_url or os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")
    client_name = client_name or os.environ.get("FORGE_MCP_CLIENT_NAME", "mcp_claude")
    ...


async def shutdown_bridge() -> None:
    global _client
    if _client:
        await _client.stop()
        _client = None
```

**Call-site to update in the same file** (`forge_bridge/mcp/server.py:71` and `:85`) — rename `_startup()` → `startup_bridge()` and `_shutdown()` → `shutdown_bridge()`.

---

### `forge_bridge/mcp/registry.py` (utility, post-run guard)

**Analog:** Self — the `_validate_name` pattern at the top of `register_tool` (lines 71) is the template for where the new guard lives inside `register_tools`.

**Current validation pattern** (`forge_bridge/mcp/registry.py:33-49`):
```python
def _validate_name(name: str, source: str) -> None:
    """Raise ValueError if *name* violates namespace rules for *source*."""
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
```

**Current `register_tools` to add guard to** (`forge_bridge/mcp/registry.py:75-101`):
```python
def register_tools(
    mcp: FastMCP,
    fns: list[Callable[..., Any]],
    prefix: str = "",
    source: str = "user-taught",
) -> None:
    """Register multiple tools under a shared prefix and source tag.
    ...
    """
    for fn in fns:
        name = f"{prefix}{fn.__name__}" if prefix else fn.__name__
        register_tool(mcp, fn, name=name, source=source)
```

**D-15 guard template** — per R-5 in RESEARCH.md, the import **must be lazy** (inside the function body) to avoid the circular `server.py` → `registry.py` ↔ `registry.py` → `server.py` dependency:
```python
def register_tools(
    mcp: FastMCP,
    fns: list[Callable[..., Any]],
    prefix: str = "",
    source: str = "user-taught",
) -> None:
    """Register multiple tools under a shared prefix and source tag.
    ...
    Raises:
        RuntimeError: If called after mcp.run() has started (post-start registration).
    """
    # Lazy import avoids the server.py → registry.py → server.py cycle.
    # Accessing the attribute through the module captures the *current* value,
    # not a stale snapshot.
    import forge_bridge.mcp.server as _server
    if _server._server_started:
        raise RuntimeError(
            "register_tools() cannot be called after the MCP server has started. "
            "Register all tools before calling mcp.run()."
        )
    for fn in fns:
        name = f"{prefix}{fn.__name__}" if prefix else fn.__name__
        register_tool(mcp, fn, name=name, source=source)
```

**Do NOT** use `from forge_bridge.mcp.server import _server_started` at the function top — per R-5, `from … import name` binds the value at import time, which goes stale if `server.py` mutates `_server_started = True` later. The `import … as _server; if _server._server_started:` pattern re-reads the attribute on every call.

---

### `forge_bridge/learning/synthesizer.py` (service, async request-response)

**Analog:** `forge_bridge/learning/execution_log.py::ExecutionLog` — the same-package precedent for promoting a chunk of module-level logic into a class with an `__init__` that accepts optional config and a `_path`-style attribute.

**ExecutionLog ctor as the shape template** (`forge_bridge/learning/execution_log.py:54-70`):
```python
class ExecutionLog:
    """Append-only JSONL execution log with AST normalization and promotion counters.

    Args:
        log_path: Path to the JSONL file. Defaults to ~/.forge-bridge/executions.jsonl.
        threshold: Number of identical (normalized) executions before promotion signal.
                   Overridden by FORGE_PROMOTION_THRESHOLD env var if set.
    """

    def __init__(self, log_path: Path = LOG_PATH, threshold: int = 3) -> None:
        self._path = log_path
        self._threshold = int(os.environ.get("FORGE_PROMOTION_THRESHOLD", threshold))
        ...
```

**D-17 target ctor shape:**
```python
class SkillSynthesizer:
    """Generates MCP tools from observed code patterns via LLM synthesis.

    Args:
        router: LLMRouter instance. Defaults to the shared `get_router()` singleton.
        synthesized_dir: Directory to write synthesized tools to.
                         Defaults to `forge_bridge.learning.watcher.SYNTHESIZED_DIR`
                         (~/.forge-bridge/synthesized).
    """

    def __init__(
        self,
        router: LLMRouter | None = None,
        synthesized_dir: Path | None = None,
    ) -> None:
        # Lazy default for router — avoids constructing an LLMRouter at import time
        self._router = router if router is not None else get_router()
        self._synthesized_dir = synthesized_dir or SYNTHESIZED_DIR
```

Note: D-17 says `router=None` falls back to `get_router()`. Matching the D-06 pattern exactly (lazy at call time, not at init) means the fallback could also live at `self._router or get_router()` inside `synthesize()`. Planner decides — eager-at-init is cleaner, lazy-at-call matches "don't construct downstream resources early" philosophy. Eager is the recommendation here since `get_router()` is itself lazy.

**Current module-level function body to port** (`forge_bridge/learning/synthesizer.py:195-275`):
```python
async def synthesize(
    raw_code: str,
    intent: Optional[str],
    count: int,
) -> Optional[Path]:
    """Generate a synthesized MCP tool from an observed code pattern."""
    # Lazy import to avoid circular deps at module load time
    from forge_bridge.llm.router import get_router

    # Build prompt
    prompt = SYNTH_PROMPT.format(
        count=count,
        intent=intent or "unknown",
        code=raw_code,
    )

    # Call LLM
    try:
        raw = await get_router().acomplete(  # ← becomes `self._router.acomplete(...)`
            prompt,
            sensitive=True,
            system=SYNTH_SYSTEM,
            temperature=0.1,
        )
    except RuntimeError:
        logger.warning("LLM unavailable — skipping synthesis")
        return None

    # ... stages 1-3 validation unchanged ...

    # Check for name collision
    output_path = SYNTHESIZED_DIR / f"{fn_name}.py"  # ← becomes `self._synthesized_dir / ...`
    ...

    # Write output
    SYNTHESIZED_DIR.mkdir(parents=True, exist_ok=True)  # ← becomes `self._synthesized_dir.mkdir(...)`
    output_path.write_text(fn_code)
    manifest_register(output_path)
    logger.info(f"Synthesized tool written: {output_path}")
    return output_path
```

**Lifted-to-method shape:**
```python
async def synthesize(
    self,
    raw_code: str,
    intent: Optional[str],
    count: int,
) -> Optional[Path]:
    """Generate a synthesized MCP tool from an observed code pattern."""
    prompt = SYNTH_PROMPT.format(
        count=count,
        intent=intent or "unknown",
        code=raw_code,
    )
    try:
        raw = await self._router.acomplete(
            prompt,
            sensitive=True,
            system=SYNTH_SYSTEM,
            temperature=0.1,
        )
    except RuntimeError:
        logger.warning("LLM unavailable — skipping synthesis")
        return None

    # ... stages 1-3 unchanged; references to SYNTHESIZED_DIR → self._synthesized_dir ...
```

**Imports to add at module top** — D-17 needs `LLMRouter` and `get_router` accessible. Avoid circular: `synthesizer.py` already does a lazy `from forge_bridge.llm.router import get_router` inside the function. For D-17 we can hoist to module top because at this point the LLM module is always importable (optional deps gate is inside client methods, not at module load):
```python
from forge_bridge.llm.router import LLMRouter, get_router
```

**D-19: remove the module-level `async def synthesize(...)` function.** The existing lazy-import-of-get_router that lived inside the old function is no longer needed at module scope once `LLMRouter` is top-imported.

---

### `forge_bridge/tools/publish.py` (Pydantic model, config default)

**Analog:** `forge_bridge/bridge.py` `_config` module-level env-read (lines 32-37) — the closest in-codebase example of "env var with sensible generic fallback" for an installation-specific path/config.

**bridge.py env-read template** (`forge_bridge/bridge.py:32-37`):
```python
# Module-level config — read via _config, replaced atomically by configure().
_config = _BridgeConfig(
    host=os.environ.get("FORGE_BRIDGE_HOST", "127.0.0.1"),
    port=int(os.environ.get("FORGE_BRIDGE_PORT", "9999")),
    timeout=int(os.environ.get("FORGE_BRIDGE_TIMEOUT", "60")),
)
```

**Current `output_directory` field to modify** (`forge_bridge/tools/publish.py:65-68`):
```python
output_directory: str = Field(
    default="/mnt/portofino",
    description="Root output directory. Preset namePattern adds subdirs.",
)
```

**R-1 target shape** (option 2 from research — env-var default factory, preserves backward compat for deployments that already set the env, generic fallback for clean-install/CI):
```python
import os  # ← add to imports at top; currently missing from this file

# ...

output_directory: str = Field(
    default_factory=lambda: os.environ.get("FORGE_PUBLISH_ROOT", "/tmp/publish"),
    description=(
        "Root output directory. Preset namePattern adds subdirs. "
        "Defaults to $FORGE_PUBLISH_ROOT or /tmp/publish if unset."
    ),
)
```

**Why `default_factory` not `default`:** Pydantic evaluates `default=` at class-definition time (module import). Using `default_factory=` defers the env read until an instance is created, matching D-06's "env reads happen at construction time, not import time" philosophy from the router refactor. Same principle applied here for consistency.

**Grep-gate verification after edit:**
```bash
grep -rn "portofino\|assist-01\|ACM_" forge_bridge/   # must return exit 1 (zero matches)
```

---

### `pyproject.toml` (config, version bump)

**Target:** Line 7 — change `version = "0.1.0"` → `version = "1.0.0"`. No analog needed; one-line edit.

Current (`pyproject.toml:5-8`):
```toml
[project]
name = "forge-bridge"
version = "0.1.0"
description = "Protocol-agnostic communication middleware for post-production pipelines"
```

---

### `tests/test_synthesizer.py` (test, migration of 7 call sites)

**Analog:** The existing `TestSynthesize` class in the same file (lines 144-233) — the test shape stays, only the call site changes.

**Current call site shape** (`tests/test_synthesizer.py:144-158` — representative of the 6 test methods):
```python
class TestSynthesize:
    @pytest.mark.asyncio
    async def test_returns_path_on_valid_llm_output(self, tmp_path, monkeypatch):
        from forge_bridge.learning import synthesizer
        monkeypatch.setattr(synthesizer, "SYNTHESIZED_DIR", tmp_path)

        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)

        with patch("forge_bridge.llm.router.get_router", return_value=mock_router):
            result = await synthesizer.synthesize("some code", "get shot name", 5)

        assert result is not None
        assert result.exists()
        assert result.name == "synth_get_shot_name.py"
```

**Target migration shape** (D-17/D-18 — instance method; the `monkeypatch.setattr(synthesizer, "SYNTHESIZED_DIR", tmp_path)` stays because `SYNTHESIZED_DIR` is still used as the default inside `SkillSynthesizer.__init__`; alternatively pass `synthesized_dir=tmp_path` directly):
```python
class TestSkillSynthesizer:  # RESEARCH.md recommends renaming the class to match
    @pytest.mark.asyncio
    async def test_returns_path_on_valid_llm_output(self, tmp_path, monkeypatch):
        from forge_bridge.learning import synthesizer

        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)

        # Inject both router and dir directly — cleaner than monkeypatching the constant
        synth = synthesizer.SkillSynthesizer(
            router=mock_router,
            synthesized_dir=tmp_path,
        )
        result = await synth.synthesize("some code", "get shot name", 5)

        assert result is not None
        assert result.exists()
        assert result.name == "synth_get_shot_name.py"
```

**All 7 call sites to update** (per RESEARCH.md test-suite impact audit):

| Line | Current | Target |
|------|---------|--------|
| 147-148 | `monkeypatch.setattr(synthesizer, "SYNTHESIZED_DIR", tmp_path)` | Replace with `synthesized_dir=tmp_path` kwarg to `SkillSynthesizer(...)` |
| 154 | `result = await synthesizer.synthesize("some code", "get shot name", 5)` | `synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path); result = await synth.synthesize(...)` |
| 169 | same pattern | same pattern |
| 182 | same pattern | same pattern |
| 199 | same pattern | same pattern |
| 216 | same pattern | same pattern |
| 229 | same pattern | same pattern |
| 242 | `from forge_bridge.learning.synthesizer import SYNTHESIZED_DIR as synth_dir` | **unchanged** — `SYNTHESIZED_DIR` constant survives as the default |

Atomicity requirement (per R-3): all 7 call-site edits + the D-19 removal of module-level `synthesize()` + the `SkillSynthesizer` class introduction must land **in the same commit/task**. Partial completion breaks the test suite and violates the per-task Nyquist sampling rate.

**Simplification:** since `SkillSynthesizer(synthesized_dir=tmp_path)` makes the `monkeypatch.setattr(synthesizer, "SYNTHESIZED_DIR", tmp_path)` redundant, the monkeypatch line can be deleted from each of the 6 `TestSkillSynthesizer::test_*` methods. `TestPathContract` on line 240-244 stays as-is.

---

### `tests/test_llm.py` (test, rewrite `test_env_var_override`)

**Analog:** `tests/test_execution_log.py::test_env_var_overrides_threshold` (lines 150-159) — same-codebase example of "monkeypatch.setenv + construct a fresh instance + assert on instance attributes."

**Analog test shape** (`tests/test_execution_log.py:150-159`):
```python
def test_env_var_overrides_threshold(tmp_path, monkeypatch):
    """FORGE_PROMOTION_THRESHOLD env var overrides default threshold of 3."""
    from forge_bridge.learning.execution_log import ExecutionLog

    monkeypatch.setenv("FORGE_PROMOTION_THRESHOLD", "2")
    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    log.record("x = 1")
    result = log.record("x = 1")  # 2nd call = threshold of 2
    assert result is True
```

**Current test to rewrite** (`tests/test_llm.py:62-78`):
```python
def test_env_var_override(monkeypatch):
    """Router must read FORGE_LOCAL_LLM_URL, FORGE_LOCAL_MODEL, FORGE_CLOUD_MODEL,
    FORGE_SYSTEM_PROMPT from environment, not hard-coded defaults."""
    monkeypatch.setenv("FORGE_LOCAL_LLM_URL", "http://test-host:11434/v1")
    monkeypatch.setenv("FORGE_LOCAL_MODEL", "test-local-model")
    monkeypatch.setenv("FORGE_CLOUD_MODEL", "test-cloud-model")
    monkeypatch.setenv("FORGE_SYSTEM_PROMPT", "Custom system prompt")

    # Force module reload so env vars are picked up
    import importlib
    import forge_bridge.llm.router as router_mod
    importlib.reload(router_mod)

    assert router_mod.LOCAL_BASE_URL == "http://test-host:11434/v1"
    assert router_mod.LOCAL_MODEL == "test-local-model"
    assert router_mod.CLOUD_MODEL == "test-cloud-model"
    assert router_mod.SYSTEM_PROMPT == "Custom system prompt"
```

**Target rewrite** (matches `test_env_var_overrides_threshold` shape — monkeypatch.setenv, then construct `LLMRouter()`, then assert on instance attributes. Per RESEARCH.md's Nyquist table, this becomes `test_env_fallback_at_init_time`):
```python
def test_env_fallback_at_init_time(monkeypatch):
    """LLMRouter() reads env vars inside __init__, not at module import time.

    After D-06 lands, no importlib.reload is needed — fresh instances pick up
    fresh env values.
    """
    monkeypatch.setenv("FORGE_LOCAL_LLM_URL", "http://test-host:11434/v1")
    monkeypatch.setenv("FORGE_LOCAL_MODEL", "test-local-model")
    monkeypatch.setenv("FORGE_CLOUD_MODEL", "test-cloud-model")
    monkeypatch.setenv("FORGE_SYSTEM_PROMPT", "Custom system prompt")

    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()
    assert router.local_url == "http://test-host:11434/v1"
    assert router.local_model == "test-local-model"
    assert router.cloud_model == "test-cloud-model"
    assert router.system_prompt == "Custom system prompt"
```

**Additional companion tests to add** (per Validation table in RESEARCH.md — `test_injected_arg_beats_env`, `test_default_fallback`, `test_router_accepts_injected_config`, `test_default_prompt_has_generic_flame_context`). These live in `test_llm.py` alongside the rewritten test. Example companion:

```python
def test_injected_arg_beats_env(monkeypatch):
    """Explicit __init__ arg wins over env var (D-06 precedence)."""
    monkeypatch.setenv("FORGE_LOCAL_LLM_URL", "http://env-value:11434/v1")
    from forge_bridge.llm.router import LLMRouter
    router = LLMRouter(local_url="http://injected:11434/v1")
    assert router.local_url == "http://injected:11434/v1"
```

---

### `tests/test_public_api.py` (**NEW** test file)

**Analogs (combined):**

1. `tests/test_mcp_registry.py` — structural template (header comment, `FastMCP` import, fresh-instance helpers, one test per requirement)
2. `tests/test_llm.py::test_optional_import_guard` (lines 83-112) — `sys.modules` manipulation pattern for the clean-import smoke test
3. `tests/test_mcp_registry.py::_fresh_mcp()` (lines 21-23) — fresh `FastMCP("test")` helper pattern for post-run guard test
4. `tests/test_execution_log.py` uses `tomllib` is not present; use `sys.version_info >= (3, 11)` guard, else fallback to `tomli`

**File header pattern** (from `tests/test_mcp_registry.py:1-10`):
```python
"""
Unit tests for forge_bridge.mcp.registry — namespace enforcement and source tagging.

Requirements covered:
    MCP-01  flame_* and forge_* namespace enforcement; synth_* blocked from static path
    MCP-02  Dynamic registration via add_tool / remove_tool roundtrip
    ...
"""

import pytest
from mcp.server.fastmcp import FastMCP

from forge_bridge.mcp.registry import register_tool, register_tools
```

**Target header for `test_public_api.py`:**
```python
"""
Unit tests for forge-bridge's public API surface (Phase 4 API-01..API-05, PKG-02).

Requirements covered:
    API-01  forge_bridge.__all__ exports the 11-name consumer surface
    API-04  startup_bridge / shutdown_bridge public; _startup / _shutdown removed
    API-05  register_tools() raises RuntimeError after mcp.run() has started
    PKG-02  pyproject.toml version is 1.0.0
    PKG-03  grep finds zero portofino / assist-01 / ACM_ matches in forge_bridge/
"""
from __future__ import annotations

import pytest
```

**Smoke-import test** (mirrors `tests/test_llm.py:25-30`'s minimalist import assertion):
```python
def test_public_api_importable():
    """All 11 public symbols import cleanly from forge_bridge root."""
    from forge_bridge import (
        LLMRouter,
        get_router,
        ExecutionLog,
        SkillSynthesizer,
        register_tools,
        get_mcp,
        startup_bridge,
        shutdown_bridge,
        execute,
        execute_json,
        execute_and_read,
    )
    # Sanity: callables are callable
    assert callable(LLMRouter)
    assert callable(SkillSynthesizer)
    assert callable(get_router)
    assert callable(get_mcp)
```

**`__all__` contract test** (no direct analog for this assertion style — set-based contract):
```python
def test_all_contract():
    """forge_bridge.__all__ matches the 11-name Phase 4 surface exactly."""
    import forge_bridge

    expected = {
        "LLMRouter", "get_router",
        "ExecutionLog",
        "SkillSynthesizer",
        "register_tools", "get_mcp",
        "startup_bridge", "shutdown_bridge",
        "execute", "execute_json", "execute_and_read",
    }
    assert set(forge_bridge.__all__) == expected
```

**Core types NOT re-exported** (D-03):
```python
def test_core_types_not_reexported():
    """Project / Registry / Role stay at forge_bridge.core, not root."""
    import forge_bridge
    for name in ("Project", "Registry", "Role", "Shot", "Status"):
        assert name not in forge_bridge.__all__
```

**Lifecycle rename contract** (D-11):
```python
def test_lifecycle_renamed_no_alias():
    """_startup / _shutdown removed; startup_bridge / shutdown_bridge added."""
    import forge_bridge.mcp.server as server_mod
    assert hasattr(server_mod, "startup_bridge")
    assert hasattr(server_mod, "shutdown_bridge")
    assert not hasattr(server_mod, "_startup")
    assert not hasattr(server_mod, "_shutdown")
```

**Post-run guard test** (D-14/D-15, using `_fresh_mcp()` pattern from `tests/test_mcp_registry.py:21-23`):
```python
def test_register_tools_post_run_guard():
    """register_tools raises RuntimeError when _server_started is True."""
    from mcp.server.fastmcp import FastMCP
    from forge_bridge.mcp.registry import register_tools
    import forge_bridge.mcp.server as server_mod

    fresh_mcp = FastMCP("test")
    def fn() -> str: return "ok"
    fn.__name__ = "fn"

    original = server_mod._server_started
    try:
        server_mod._server_started = True
        with pytest.raises(RuntimeError, match="cannot be called after the MCP server has started"):
            register_tools(fresh_mcp, [fn], prefix="forge_")
    finally:
        server_mod._server_started = original


def test_register_tools_pre_run_ok():
    """register_tools succeeds when _server_started is False (default)."""
    from mcp.server.fastmcp import FastMCP
    from forge_bridge.mcp.registry import register_tools
    import forge_bridge.mcp.server as server_mod

    fresh_mcp = FastMCP("test")
    def fn() -> str: return "ok"
    fn.__name__ = "fn"

    original = server_mod._server_started
    try:
        server_mod._server_started = False
        register_tools(fresh_mcp, [fn], prefix="forge_")  # must not raise
        assert "forge_fn" in fresh_mcp._tool_manager._tools
    finally:
        server_mod._server_started = original
```

**Grep-gate test (PKG-03)** — uses `subprocess` (no existing analog; lowest-friction approach):
```python
def test_no_forge_specific_strings():
    """grep -r returns zero matches for forge-specific tokens."""
    import subprocess
    from pathlib import Path

    root = Path(__file__).parent.parent / "forge_bridge"
    result = subprocess.run(
        ["grep", "-r", "-E", "portofino|assist-01|ACM_", str(root)],
        capture_output=True,
        text=True,
    )
    # grep returns 1 when no matches found — that's success
    assert result.returncode == 1, (
        f"Found forge-specific strings:\n{result.stdout}"
    )
```

**Version test (PKG-02)** — Python 3.10 / 3.11+ compat for `tomllib`:
```python
def test_package_version():
    """pyproject.toml version bumped to 1.0.0 for Phase 4."""
    import sys
    from pathlib import Path

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib  # type: ignore[import-not-found]

    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as fp:
        data = tomllib.load(fp)
    assert data["project"]["version"] == "1.0.0"
```

Note: Python 3.10 is the minimum per `pyproject.toml:11` (`requires-python = ">=3.10"`), and `tomllib` is 3.11+ stdlib. The `tomli` fallback adds a test-only runtime dep. Alternative: parse manually with a regex since the pyproject format is simple:
```python
def test_package_version_simple():
    from pathlib import Path
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    assert 'version = "1.0.0"' in pyproject
```
Planner picks between tomllib-with-fallback (cleaner) or regex (zero extra dep). Regex is fine for this single-test use.

**Shutdown signature test (D-13)**:
```python
def test_shutdown_bridge_signature():
    """shutdown_bridge() takes no args and returns None."""
    import inspect
    from forge_bridge.mcp.server import shutdown_bridge
    sig = inspect.signature(shutdown_bridge)
    assert len(sig.parameters) == 0
```

**Startup injection test (D-12)** — needs AsyncClient mocking to avoid an actual WebSocket attempt:
```python
@pytest.mark.asyncio
async def test_startup_bridge_injection(monkeypatch):
    """startup_bridge(server_url=...) uses injected URL over env."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import forge_bridge.mcp.server as server_mod

    monkeypatch.setenv("FORGE_BRIDGE_URL", "ws://should-be-overridden:9998")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.wait_until_connected = AsyncMock()
    mock_client.stop = AsyncMock()

    with patch("forge_bridge.mcp.server.AsyncClient", return_value=mock_client) as mock_cls:
        await server_mod.startup_bridge(server_url="ws://injected:9998")
        # First positional/kwarg: server_url must be the injected value
        ctor_kwargs = mock_cls.call_args.kwargs
        assert ctor_kwargs.get("server_url") == "ws://injected:9998"
        await server_mod.shutdown_bridge()  # cleanup
```

**Bridge-module-clean-import smoke (D-20)** — if Phase 4 introduces the `SkillSynthesizer` call site in `bridge.py`, this catches a bad ctor invocation at module load:
```python
def test_bridge_module_imports_clean():
    """forge_bridge.bridge imports without side-effect errors."""
    # Re-import from scratch to catch eager init bugs
    import importlib
    import sys
    sys.modules.pop("forge_bridge.bridge", None)
    importlib.import_module("forge_bridge.bridge")  # must not raise
```

---

## Shared Patterns

### 1. `arg → env → hardcoded default` precedence inside `__init__`

**Applies to:** `LLMRouter.__init__` (D-05/D-06), `startup_bridge()` (D-12), `SkillSynthesizer.__init__` (D-17)

**Canonical expression:**
```python
self.foo = foo or os.environ.get("FORGE_FOO", "hardcoded-default")
```

**Why it works:** `None or X` → `X`; `"" or X` → `X` — so both `None` and the empty string fall through. For non-string kwargs (ints, Paths), use explicit `is None` check:
```python
self.foo = foo if foo is not None else int(os.environ.get("FORGE_FOO", "42"))
```

**Source of pattern:** `forge_bridge/learning/execution_log.py:63-65` (the existing `threshold` arg treats env as an override of the arg-default, which is one variant of this idiom).

### 2. Lazy optional-dependency imports

**Applies to:** `LLMRouter._get_local_client` / `_get_cloud_client` (preserved unchanged in Phase 4), any new public surface that touches openai/anthropic.

**Canonical expression** (`forge_bridge/llm/router.py:178-191`):
```python
def _get_local_client(self):
    if self._local_client is None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError(
                "openai package not installed. "
                "Install LLM support: pip install forge-bridge[llm]"
            )
        self._local_client = AsyncOpenAI(...)
    return self._local_client
```

**Phase 4 consumer:** the root `__init__.py` must NOT eagerly import anything that drags openai/anthropic in — re-exporting `LLMRouter` the class is safe (the class doesn't import optional deps at class-def time), but do not re-export helpers that would trip the lazy guard.

### 3. Lazy cross-module imports to break cycles

**Applies to:** `register_tools()` reading `_server_started` from `server.py` (D-15 / R-5), `synthesizer.py` currently reading `get_router` lazily (preserved in Phase 4).

**Canonical expression** (from R-5, adapted):
```python
def register_tools(...):
    import forge_bridge.mcp.server as _server  # inside function, runs per call
    if _server._server_started:
        raise RuntimeError(...)
```

**Source of pattern:** `forge_bridge/learning/synthesizer.py:211` (`from forge_bridge.llm.router import get_router` inside `synthesize()`), `forge_bridge/learning/watcher.py:64` (`from forge_bridge.mcp.registry import register_tool` inside `_scan_once`).

### 4. `__init__.py` barrel re-exports with `__all__`

**Applies to:** `forge_bridge/__init__.py` (D-01, D-02)

**Canonical expression:** `forge_bridge/core/__init__.py:24-86` (large barrel with grouped imports and grouped `__all__`) or `forge_bridge/mcp/__init__.py:1-12` (minimal barrel with 2-name `__all__`).

**Convention** (from CONVENTIONS.md §"Module Design"): "Explicit imports in `__init__.py` files define public API."

### 5. Test shape: monkeypatch.setenv + fresh instance + assert on instance attrs

**Applies to:** all new `tests/test_llm.py` tests for D-05..D-10, and the `startup_bridge` injection test in `test_public_api.py`.

**Canonical expression** (`tests/test_execution_log.py:150-159`):
```python
def test_env_var_overrides_threshold(tmp_path, monkeypatch):
    from forge_bridge.learning.execution_log import ExecutionLog
    monkeypatch.setenv("FORGE_PROMOTION_THRESHOLD", "2")
    log = ExecutionLog(log_path=tmp_path / "executions.jsonl")
    ...
```

Replaces the `importlib.reload(router_mod)` anti-pattern in the current `test_env_var_override`.

### 6. AsyncMock + patch for async-dependency isolation

**Applies to:** All `tests/test_synthesizer.py` migrated tests, `test_startup_bridge_injection`.

**Canonical expression** (`tests/test_synthesizer.py:150-154`):
```python
mock_router = MagicMock()
mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)
with patch("forge_bridge.llm.router.get_router", return_value=mock_router):
    result = await synthesizer.synthesize(...)
```

After D-17 lands, prefer direct injection over `patch()`:
```python
synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
result = await synth.synthesize(...)
```

---

## No Analog Found

None. Every Phase 4 edit has at least one role-match analog inside the existing codebase.

---

## Metadata

**Analog search scope:**
- `forge_bridge/` — all subdirectories (core, llm, learning, mcp, client, server, store, flame, tools)
- `tests/` — all 11 test files
- `pyproject.toml`

**Files directly read during mapping:** 15

- `forge_bridge/__init__.py`
- `forge_bridge/bridge.py`
- `forge_bridge/llm/__init__.py`, `forge_bridge/llm/router.py`, `forge_bridge/llm/health.py`
- `forge_bridge/mcp/__init__.py`, `forge_bridge/mcp/server.py`, `forge_bridge/mcp/registry.py`
- `forge_bridge/learning/__init__.py`, `forge_bridge/learning/synthesizer.py`, `forge_bridge/learning/execution_log.py`, `forge_bridge/learning/watcher.py`
- `forge_bridge/core/__init__.py`
- `forge_bridge/tools/publish.py` (first 100 lines)
- `pyproject.toml`
- `tests/conftest.py`, `tests/test_synthesizer.py`, `tests/test_llm.py`, `tests/test_mcp_registry.py`, `tests/test_execution_log.py`

**Key cross-references:**
- CONTEXT.md D-01..D-23 drove the file list
- RESEARCH.md Validation Architecture named each target test location
- RESEARCH.md Risk R-1 surfaced `forge_bridge/tools/publish.py` as an in-scope edit not in CONTEXT.md
- RESEARCH.md Risk R-5 determined the lazy-import shape of the D-15 guard
- CONVENTIONS.md §"Module Design" confirmed `__init__.py` barrel pattern
- CONVENTIONS.md §"Import Organization" confirmed `from __future__ import annotations` is optional (omitted in pure re-export files)

**Pattern extraction date:** 2026-04-16
