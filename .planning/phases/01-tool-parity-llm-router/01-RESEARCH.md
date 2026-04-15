# Phase 1: Tool Parity & LLM Router - Research

**Researched:** 2026-04-14
**Domain:** Python MCP tool porting, async LLM routing, pyproject.toml optional dependencies
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOOL-01 | Update tools/timeline.py with expanded functions from projekt-forge (disconnect_segments, inspect_sequence_versions, create_version, reconstruct_track, clone_version, replace_segment_media, scan_roles, assign_roles) | Source files read; full function bodies available in projekt-forge |
| TOOL-02 | Update tools/batch.py with projekt-forge additions (inspect_batch_xml, prune_batch_xml) | Source files read; both functions fully available |
| TOOL-03 | Update tools/publish.py with projekt-forge additions (rename_segments) | Source files read; rename_segments already present in standalone — needs reconciliation |
| TOOL-04 | Update tools/project.py with Pydantic models from projekt-forge | Checked; projekt-forge project.py is structurally identical — no new models found |
| TOOL-05 | Update tools/utility.py with Pydantic models from projekt-forge | Checked; standalone already has Pydantic models for all utility tools |
| TOOL-06 | Add tools/reconform.py from projekt-forge | Full source available; has one external dependency (forge_batch_xml) that must be handled |
| TOOL-07 | Add tools/switch_grade.py from projekt-forge | Full source available; depends on forge_openclip_writer (external script) and catalog WebSocket |
| TOOL-08 | Add Pydantic input models for all existing and new MCP tools | Current tools already have Pydantic models; list_batch_nodes() and get_project() are bare — need models added |
| TOOL-09 | Bump bridge.py default timeout from 30s to 60s | Single env-var default change in bridge.py |
| LLM-01 | Promote llm_router.py to forge_bridge/llm/ package with router.py | Source fully read; straightforward structural promotion |
| LLM-02 | Add async acomplete() using AsyncOpenAI for local Ollama and AsyncAnthropic for cloud Claude | Both AsyncOpenAI and AsyncAnthropic confirmed installed (openai 2.29.0 / anthropic 0.86.0) |
| LLM-03 | Keep sync complete() as convenience wrapper | Trivial: wrap acomplete() with asyncio.run() or loop.run_until_complete() |
| LLM-04 | Extract hardcoded system prompt and infrastructure hostnames into env vars | System prompt and hostnames currently hardcoded in llm_router.py; env vars already partially exist |
| LLM-05 | Move openai and anthropic to optional dependencies (pip install forge-bridge[llm]) | pyproject.toml has duplicate declarations; must be moved to [project.optional-dependencies] |
| LLM-06 | Add health check reporting which backends are available (async and sync) | Sync health_check() exists; async version needed; local check requires HTTP probe, not just models.list() |
| LLM-07 | Expose LLM health check as MCP resource (forge://llm/health) | FastMCP supports @mcp.resource() decorator; confirmed in installed mcp SDK |
| LLM-08 | Fix duplicate dependency declarations in pyproject.toml | openai and anthropic each declared twice in [project.dependencies]; confirmed by reading pyproject.toml |
</phase_requirements>

---

## Summary

Phase 1 is a porting and promotion exercise. The dominant work is: (1) copying functions from projekt-forge into the standalone forge-bridge tools, (2) restructuring `llm_router.py` into `forge_bridge/llm/` as an async package, and (3) fixing `pyproject.toml`.

No new patterns or libraries are required. Every needed piece — the Flame Python code, the async LLM clients, the FastMCP resource decorator — is already available either in projekt-forge source or in installed packages. The risk is in the **porting details**: the standalone repo uses `from forge_mcp import bridge` while projekt-forge uses `from forge_bridge import bridge`. The batch.py additions in projekt-forge depend on `forge_batch_xml` and `forge_batch_prune` scripts from the flame_hooks directory. The switch_grade.py tool depends on catalog WebSocket and `forge_openclip_writer` — both of which are projekt-forge-specific infrastructure. These dependencies require scoping decisions before porting.

The LLM router promotion is mechanical but must be done carefully to avoid blocking the async event loop. The sync `complete()` wrapper must use `asyncio.run()` (not `loop.run_until_complete()`) because no event loop is guaranteed to be running at call sites outside the MCP server.

**Primary recommendation:** Port tools file by file, starting with the simplest (TOOL-09, TOOL-08, TOOL-04/05), then porting standalone-compatible tools (TOOL-01 new functions, TOOL-02 clean additions), then resolve the external-dependency tools (TOOL-06, TOOL-07) with scoped stubs, then promote the LLM router.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 (installed) | Input model validation for MCP tools | Already used throughout; FastMCP requires it |
| mcp[cli] | >=1.0 (installed) | FastMCP server and @mcp.resource() decorator | The MCP protocol implementation |
| openai | 2.29.0 (installed) | AsyncOpenAI client for Ollama + cloud models | Already installed; AsyncOpenAI confirmed present |
| anthropic | 0.86.0 (installed) | AsyncAnthropic client for Claude cloud | Already installed; AsyncAnthropic confirmed present |
| httpx | >=0.27 (installed) | HTTP client for Flame bridge | Already used in bridge.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | Python 3.10+ | Event loop, asyncio.run() for sync wrapper | Sync complete() wrapper needs asyncio.run() |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.run() for sync wrapper | loop.run_until_complete() | asyncio.run() is cleaner — creates+destroys its own loop. Use it when no loop is guaranteed to be running. |

**Installation:**
No new packages required. All dependencies are already installed.

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
forge_bridge/
├── llm/                    # NEW: promoted from llm_router.py
│   ├── __init__.py         # re-exports LLMRouter, get_router
│   ├── router.py           # async LLMRouter with acomplete() + sync complete()
│   └── health.py           # async/sync health check; MCP resource registration
├── tools/
│   ├── timeline.py         # UPDATE: add 8 new functions from projekt-forge
│   ├── batch.py            # UPDATE: add inspect_batch_xml, prune_batch_xml
│   ├── publish.py          # CHECK: rename_segments already present; verify identical
│   ├── project.py          # NO CHANGE: identical to projekt-forge
│   ├── utility.py          # NO CHANGE: already has Pydantic models
│   ├── reconform.py        # NEW: ported from projekt-forge
│   └── switch_grade.py     # NEW: ported from projekt-forge (with catalog stub)
└── llm_router.py           # REPLACE: compatibility shim importing from llm/router.py
```

### Pattern 1: Async LLM Router Package Structure

**What:** Promote the flat `llm_router.py` into a proper `llm/` subpackage. Keep the original path as a compatibility shim.
**When to use:** Whenever adding a subpackage with shared state (the singleton router).

```python
# forge_bridge/llm/router.py — new home
import os
from typing import Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import asyncio

LOCAL_BASE_URL = os.environ.get("FORGE_LOCAL_LLM_URL", "http://assist-01:11434/v1")
LOCAL_MODEL    = os.environ.get("FORGE_LOCAL_MODEL",   "qwen2.5-coder:32b")
CLOUD_MODEL    = os.environ.get("FORGE_CLOUD_MODEL",   "claude-opus-4-6")
SYSTEM_PROMPT  = os.environ.get("FORGE_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT)

class LLMRouter:
    def __init__(self):
        self._local_client: Optional[AsyncOpenAI] = None
        self._cloud_client: Optional[AsyncAnthropic] = None

    async def acomplete(
        self, prompt: str, sensitive: bool = True,
        system: Optional[str] = None, temperature: float = 0.1,
    ) -> str:
        if sensitive:
            return await self._async_local(prompt, system, temperature)
        return await self._async_cloud(prompt, system, temperature)

    def complete(self, prompt: str, **kwargs) -> str:
        """Sync convenience wrapper."""
        return asyncio.run(self.acomplete(prompt, **kwargs))

    def _get_local_client(self) -> AsyncOpenAI:
        if self._local_client is None:
            try:
                from openai import AsyncOpenAI as _AO
            except ImportError:
                raise RuntimeError("openai not installed. Run: pip install forge-bridge[llm]")
            self._local_client = _AO(base_url=LOCAL_BASE_URL, api_key="ollama")
        return self._local_client

    def _get_cloud_client(self) -> AsyncAnthropic:
        if self._cloud_client is None:
            try:
                from anthropic import AsyncAnthropic as _AA
            except ImportError:
                raise RuntimeError("anthropic not installed. Run: pip install forge-bridge[llm]")
            self._cloud_client = _AA()
        return self._cloud_client

    async def _async_local(self, prompt: str, system: Optional[str], temperature: float) -> str:
        client = self._get_local_client()
        sys_msg = system if system is not None else SYSTEM_PROMPT
        messages = []
        if sys_msg:
            messages.append({"role": "system", "content": sys_msg})
        messages.append({"role": "user", "content": prompt})
        resp = await client.chat.completions.create(
            model=LOCAL_MODEL, messages=messages, temperature=temperature
        )
        return resp.choices[0].message.content

    async def _async_cloud(self, prompt: str, system: Optional[str], temperature: float) -> str:
        client = self._get_cloud_client()
        sys_msg = system or "You are a VFX pipeline assistant."
        resp = await client.messages.create(
            model=CLOUD_MODEL, max_tokens=4096, system=sys_msg,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
```

```python
# forge_bridge/llm_router.py — compatibility shim (replaces original)
"""Backwards-compatible shim. Import from forge_bridge.llm.router instead."""
from forge_bridge.llm.router import LLMRouter, get_router
__all__ = ["LLMRouter", "get_router"]
```

### Pattern 2: Optional Dependency Import Guard

**What:** Lazy import with clear error message pointing to the extras group.
**When to use:** Any LLM-related code that should not fail at import time for base installs.

```python
# Source: pyproject.toml optional-dependencies pattern
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

### Pattern 3: MCP Resource for Health Check

**What:** Register a `forge://llm/health` resource via FastMCP's `@mcp.resource()` decorator.
**When to use:** Read-only, agent-visible data that doesn't need tool call semantics.

```python
# forge_bridge/llm/health.py
from mcp.server.fastmcp import FastMCP

def register_llm_health_resource(mcp: FastMCP) -> None:
    @mcp.resource("forge://llm/health")
    async def llm_health() -> str:
        """Report which LLM backends are available."""
        router = get_router()
        status = await router.ahealth_check()
        return json.dumps(status, indent=2)
```

### Pattern 4: bridge Import Path for Ported Tools

**What:** Standalone forge-bridge tools use `from forge_mcp import bridge`. Ported projekt-forge tools use `from forge_bridge import bridge`. The standalone package is `forge_bridge`, not `forge_mcp`.

**When porting:** All ported tools must change `from forge_bridge import bridge` to `from forge_mcp import bridge` — or more precisely, to whatever the current standalone import is. Looking at the current standalone tools, the correct import is:

```python
# Current standalone pattern (e.g., tools/batch.py line 8):
from forge_mcp import bridge
```

Wait — this is the critical finding from reading the files. The standalone `forge_bridge/tools/` files import `from forge_mcp import bridge`. The `forge_bridge/server.py` also imports `from forge_mcp.tools import ...`. This means the standalone package is partially wired as `forge_mcp`, not `forge_bridge`. The projekt-forge files import `from forge_bridge import bridge`. **The correct import in the standalone repo's tools is `from forge_mcp import bridge`** — this must be used consistently when porting.

### Pattern 5: pyproject.toml Optional Dependencies Fix

**What:** Move `openai` and `anthropic` from `[project.dependencies]` to `[project.optional-dependencies.llm]`.

```toml
# pyproject.toml — AFTER fix
[project]
dependencies = [
    "httpx>=0.27",
    "websockets>=13.0",
    "mcp[cli]>=1.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
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

This satisfies both LLM-05 and LLM-08 (duplicate removal).

### Anti-Patterns to Avoid

- **`asyncio.get_event_loop().run_until_complete()`** in `complete()` sync wrapper — this fails if a loop is already running (raises RuntimeError). Use `asyncio.run()` instead (creates its own loop, safe when no loop is running).
- **Importing openai/anthropic at module top level in tools** — breaks base install. Always use lazy import inside methods.
- **Calling `client.models.list()` as the local health probe** — this is a synchronous call. Use `await client.models.list()` in the async health check.
- **Using `from forge_bridge import bridge` in ported tools** — wrong package name for this repo. Use `from forge_mcp import bridge`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP to OpenAI/Ollama | Custom httpx async client | `AsyncOpenAI(base_url=..., api_key="ollama")` | OpenAI SDK handles retries, headers, streaming, JSON parsing |
| Async Anthropic calls | Custom httpx async client | `AsyncAnthropic()` | Handles auth headers, response parsing, streaming |
| MCP resource exposure | Custom HTTP endpoint | `@mcp.resource("forge://llm/health")` | FastMCP routes resource fetches automatically |
| Pydantic validation | Manual isinstance checks | `pydantic.BaseModel` subclass as tool param type | FastMCP reads param type annotations and validates automatically |
| Import guards for optional deps | Catching AttributeError | Try/except ImportError with clear message | ImportError is the correct exception; AttributeError means something else |

---

## Common Pitfalls

### Pitfall 1: Wrong bridge import path in ported tools
**What goes wrong:** Ported tools from projekt-forge use `from forge_bridge import bridge`. In the standalone repo this resolves to the package root, not the HTTP bridge client — causing ImportError or wrong module loaded.
**Why it happens:** projekt-forge keeps `bridge.py` at `forge_bridge/bridge.py` but the standalone MCP server wraps it differently.
**How to avoid:** When porting, change `from forge_bridge import bridge` to `from forge_mcp import bridge` (matching the existing standalone tools pattern).
**Warning signs:** `ImportError: cannot import name 'bridge' from 'forge_bridge'` or calls to bridge methods failing.

### Pitfall 2: asyncio.run() called from inside a running event loop
**What goes wrong:** The sync `complete()` wrapper calls `asyncio.run(self.acomplete(...))`. If called from within an async context (e.g., inside an MCP tool), this raises `RuntimeError: This event loop is already running`.
**Why it happens:** `asyncio.run()` creates a new event loop — it cannot be called from inside an existing one.
**How to avoid:** Document that `complete()` is for use outside async contexts only. For use inside async tools (e.g., synthesizer), call `acomplete()` directly. Never call `complete()` from MCP tool implementations.
**Warning signs:** `RuntimeError: This event loop is already running` at runtime.

### Pitfall 3: inspect_batch_xml and prune_batch_xml depend on external scripts
**What goes wrong:** The projekt-forge batch additions (`inspect_batch_xml`, `prune_batch_xml`) import from `forge_batch_xml` and `forge_batch_prune`, which live in `flame_hooks/forge_tools/forge_publish_shots/scripts/`. These scripts are not present in the standalone forge-bridge repo.
**Why it happens:** The projekt-forge batch.py adds the scripts dir to `sys.path` dynamically. The standalone repo doesn't have those hook scripts.
**How to avoid:** Two options: (a) stub the functions with a clear error until the scripts are ported separately, or (b) inline the minimal XML parsing logic needed. Option (a) is safer for this phase.
**Warning signs:** `ModuleNotFoundError: No module named 'forge_batch_xml'` at runtime.

### Pitfall 4: switch_grade.py depends on catalog WebSocket and forge_openclip_writer
**What goes wrong:** `switch_grade.py` calls `_catalog_request()` (catalog WebSocket) and `_write_openclip_server_side()` (forge_openclip_writer). Neither exists in the standalone repo.
**Why it happens:** switch_grade is tightly coupled to projekt-forge infrastructure.
**How to avoid:** Port the Flame-side logic (segment info retrieval, smart_replace_media) and stub the catalog query and openclip writer with `NotImplementedError` or a clear error response. The reconform.py tools which only need Flame-side logic and disk path conventions are cleaner to port completely.
**Warning signs:** `ImportError: cannot import name 'AsyncClient' from 'forge_bridge.client.async_client'` — the client module exists but the catalog server won't be running.

### Pitfall 5: rename_segments already exists in standalone publish.py
**What goes wrong:** TOOL-03 says "add rename_segments to publish.py" but rename_segments is already present in the standalone forge-bridge publish.py (confirmed by reading the file). The projekt-forge version may have minor differences.
**Why it happens:** The standalone publish.py was already updated at some point.
**How to avoid:** Diff the two implementations before assuming either is the definitive one. Verify the standalone version matches projekt-forge behavior; if identical, TOOL-03 is already done.
**Warning signs:** Silent behavioral divergence if the two implementations differ in edge cases.

### Pitfall 6: Async health check for local Ollama needs HTTP probe, not models.list()
**What goes wrong:** The existing sync `health_check()` calls `client.models.list()` which makes a real HTTP request. For the async version this must be `await client.models.list()`. A sync call inside an async function blocks the event loop.
**Why it happens:** The existing router uses sync OpenAI client; the new router uses AsyncOpenAI.
**How to avoid:** Use `await client.models.list()` inside the async health check. Wrap in try/except — if Ollama is offline, this raises a connection error.
**Warning signs:** Health check hangs; other MCP tools timeout during health check execution.

### Pitfall 7: bulk_rename_segments in standalone server.py vs rename_segments function
**What goes wrong:** The current server.py registers `timeline.bulk_rename_segments` but the current `tools/timeline.py` does not have a `bulk_rename_segments` function. The server.py references what appears to be a stale name.
**Why it happens:** Naming diverged between the server registration and the tools module.
**How to avoid:** When updating server.py tool registrations for the new functions, audit all existing registrations for correctness.
**Warning signs:** `AttributeError: module 'forge_mcp.tools.timeline' has no attribute 'bulk_rename_segments'`.

---

## Code Examples

### Async LLMRouter — acomplete with AsyncOpenAI
```python
# Source: openai SDK AsyncOpenAI (confirmed in .venv/lib/python3.13/site-packages/openai/)
async def _async_local(self, prompt: str, system: Optional[str], temperature: float) -> str:
    client = self._get_local_client()  # returns AsyncOpenAI instance
    messages = []
    sys_msg = system if system is not None else SYSTEM_PROMPT
    if sys_msg:
        messages.append({"role": "system", "content": sys_msg})
    messages.append({"role": "user", "content": prompt})
    resp = await client.chat.completions.create(
        model=LOCAL_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content
```

### Async LLMRouter — acomplete with AsyncAnthropic
```python
# Source: anthropic SDK AsyncAnthropic (confirmed in .venv/lib/python3.13/site-packages/anthropic/)
async def _async_cloud(self, prompt: str, system: Optional[str], temperature: float) -> str:
    client = self._get_cloud_client()  # returns AsyncAnthropic instance
    sys_msg = system or "You are a VFX pipeline assistant."
    resp = await client.messages.create(
        model=CLOUD_MODEL,
        max_tokens=4096,
        system=sys_msg,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text
```

### Async Health Check
```python
# Source: openai SDK — AsyncOpenAI.models.list() is a coroutine
async def ahealth_check(self) -> dict:
    status = {"local": False, "cloud": False, "local_model": LOCAL_MODEL, "cloud_model": CLOUD_MODEL}
    try:
        client = self._get_local_client()
        await client.models.list()
        status["local"] = True
    except Exception as e:
        status["local_error"] = str(e)
    try:
        import anthropic as _anthropic  # noqa: F401 — just check importable
        status["cloud"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        status["cloud_error"] = "anthropic not installed"
    return status
```

### FastMCP Resource Registration
```python
# Source: mcp SDK FastMCP — confirmed in .venv/lib/python3.13/site-packages/mcp/server/fastmcp/
from mcp.server.fastmcp import FastMCP
import json

def register_llm_resources(mcp: FastMCP) -> None:
    @mcp.resource("forge://llm/health")
    async def llm_health() -> str:
        """Report available LLM backends for forge-bridge."""
        from forge_bridge.llm.router import get_router
        router = get_router()
        status = await router.ahealth_check()
        return json.dumps(status, indent=2)
```

### pyproject.toml Fix
```toml
# Remove from [project.dependencies]:
#   "openai>=1.0",   (appears twice — remove both)
#   "anthropic>=0.25", (appears twice — remove both)
#
# Add to [project.optional-dependencies]:
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

### Pydantic Input Model for a No-Arg Tool
```python
# For tools currently taking no args (get_project, list_batch_nodes, ping):
# FastMCP accepts async def tool() -> str directly — no Pydantic model needed for zero-arg tools.
# The requirement is to add models for tools that ACCEPT parameters but currently lack them.
# The standalone tools already have Pydantic models for all parameterized tools.
# Remaining gaps: list_batch_nodes() and get_project() have no parameters — no models needed.
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync OpenAI client in llm_router.py | AsyncOpenAI in forge_bridge/llm/router.py | Phase 1 | LLM calls no longer block the MCP event loop |
| openai/anthropic as hard deps | forge-bridge[llm] optional extras | Phase 1 | Base install works without LLM packages |
| llm_router.py as flat module | forge_bridge/llm/ as subpackage | Phase 1 | Extensible: health.py, prompts.py can live alongside router.py |

**Deprecated/outdated:**
- `forge_bridge/llm_router.py`: Replaced by compatibility shim pointing to `forge_bridge/llm/router.py`. Keep shim for backwards compat; do not delete.

---

## Open Questions

1. **inspect_batch_xml / prune_batch_xml external dependency**
   - What we know: These tools import `forge_batch_xml` and `forge_batch_prune` from `flame_hooks/forge_tools/forge_publish_shots/scripts/` — path not present in standalone repo.
   - What's unclear: Should these be stubbed (return NotImplementedError), inlined (copy minimal XML parsing), or deferred?
   - Recommendation: Stub with a clear runtime error message in this phase. The XML parsing logic is non-trivial and belongs in a separate porting effort.

2. **switch_grade.py catalog WebSocket dependency**
   - What we know: `query_alternatives()` requires a running catalog WebSocket server at `ws://127.0.0.1:9998`. The standalone forge-bridge server may or may not be running in all deployments.
   - What's unclear: Can switch_grade be partially ported (Flame-side swap only, no catalog query)?
   - Recommendation: Port the `switch_grade` function (direct media swap) as a standalone tool. Stub `query_alternatives` with a clear error noting catalog server dependency.

3. **rename_segments already present in standalone publish.py**
   - What we know: The standalone `forge_bridge/tools/publish.py` already contains `rename_segments` and the `RenameSegments` Pydantic model.
   - What's unclear: Whether the standalone and projekt-forge versions are behaviorally identical.
   - Recommendation: Diff the two side by side at implementation time. If identical, TOOL-03 is already satisfied.

4. **bulk_rename_segments registration mismatch in server.py**
   - What we know: `server.py` registers `timeline.bulk_rename_segments` but no such function exists in the current `tools/timeline.py`.
   - What's unclear: Whether this is a latent bug that crashes on startup or an unreferenced registration that silently fails.
   - Recommendation: Fix the registration to point to the correct function name during the server.py update.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | timeline.py exports new functions | unit | `pytest tests/test_tools.py::test_timeline_exports -x` | ❌ Wave 0 |
| TOOL-02 | batch.py exports inspect_batch_xml, prune_batch_xml | unit | `pytest tests/test_tools.py::test_batch_exports -x` | ❌ Wave 0 |
| TOOL-03 | publish.py has rename_segments | unit | `pytest tests/test_tools.py::test_publish_exports -x` | ❌ Wave 0 |
| TOOL-04 | project.py Pydantic models present | unit | `pytest tests/test_tools.py::test_project_models -x` | ❌ Wave 0 |
| TOOL-05 | utility.py Pydantic models present | unit | `pytest tests/test_tools.py::test_utility_models -x` | ❌ Wave 0 |
| TOOL-06 | reconform.py importable; tool functions present | unit | `pytest tests/test_tools.py::test_reconform_exports -x` | ❌ Wave 0 |
| TOOL-07 | switch_grade.py importable; tool functions present | unit | `pytest tests/test_tools.py::test_switch_grade_exports -x` | ❌ Wave 0 |
| TOOL-08 | All parameterized tools have Pydantic input models | unit | `pytest tests/test_tools.py::test_pydantic_coverage -x` | ❌ Wave 0 |
| TOOL-09 | bridge.py default timeout is 60s | unit | `pytest tests/test_tools.py::test_bridge_timeout -x` | ❌ Wave 0 |
| LLM-01 | forge_bridge.llm.router importable; LLMRouter present | unit | `pytest tests/test_llm.py::test_llm_package_structure -x` | ❌ Wave 0 |
| LLM-02 | acomplete() is a coroutine | unit | `pytest tests/test_llm.py::test_acomplete_is_coroutine -x` | ❌ Wave 0 |
| LLM-03 | complete() returns string (sync wrapper) | unit | `pytest tests/test_llm.py::test_complete_sync_wrapper -x` | ❌ Wave 0 |
| LLM-04 | FORGE_LOCAL_LLM_URL / FORGE_LOCAL_MODEL / FORGE_SYSTEM_PROMPT env vars respected | unit | `pytest tests/test_llm.py::test_env_var_override -x` | ❌ Wave 0 |
| LLM-05 | `pip install forge-bridge` succeeds without openai/anthropic | unit | `pytest tests/test_llm.py::test_optional_import_guard -x` | ❌ Wave 0 |
| LLM-06 | ahealth_check() returns dict with 'local' and 'cloud' keys | unit | `pytest tests/test_llm.py::test_health_check_shape -x` | ❌ Wave 0 |
| LLM-07 | forge://llm/health resource registered on mcp instance | unit | `pytest tests/test_llm.py::test_health_resource_registered -x` | ❌ Wave 0 |
| LLM-08 | pyproject.toml has no duplicate deps; openai/anthropic in [llm] extra | unit | `pytest tests/test_tools.py::test_pyproject_no_duplicates -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_tools.py tests/test_llm.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tools.py` — covers TOOL-01 through TOOL-09 (import/export/model/timeout assertions)
- [ ] `tests/test_llm.py` — covers LLM-01 through LLM-08 (package structure, coroutine check, env vars, import guards)

None of the phase-specific test files exist yet. The existing `tests/test_core.py` and `tests/test_integration.py` cover the vocabulary/server layers which are not changed in this phase.

---

## Sources

### Primary (HIGH confidence)
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/llm_router.py` — full source read; all sync patterns documented
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/server.py` — full source read; tool registration pattern and import paths confirmed
- `/Users/cnoellert/Documents/GitHub/forge-bridge/pyproject.toml` — full file read; duplicate deps and missing [llm] extra confirmed
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/tools/` — all 5 tool files fully read; Pydantic model coverage verified
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/timeline.py` — full source read (new functions: inspect_sequence_versions, create_version, reconstruct_track, clone_version, disconnect_segments, scan_roles, assign_roles — partially read, offset needed for remaining)
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/batch.py` — full source read; inspect_batch_xml and prune_batch_xml with external deps documented
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/reconform.py` — full source read; standalone-compatible (no catalog dep)
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/switch_grade.py` — full source read; catalog WebSocket dependency documented
- `.venv/lib/python3.13/site-packages/openai/` — AsyncOpenAI confirmed (version 2.29.0)
- `.venv/lib/python3.13/site-packages/anthropic/` — AsyncAnthropic confirmed (version 0.86.0)
- `.planning/research/SUMMARY.md` — project-level research (AsyncOpenAI/AsyncAnthropic patterns, health check, optional deps)

### Secondary (MEDIUM confidence)
- FastMCP `@mcp.resource()` decorator — confirmed in `.venv/lib/python3.13/site-packages/mcp/server/fastmcp/` (project-level research SUMMARY.md)

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages confirmed from installed `.venv`
- Architecture: HIGH — all source files directly read; no inference needed
- Pitfalls: HIGH — pitfalls 1, 3, 4, 5, 7 discovered by direct source reading (not speculation)

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable Python/MCP stack; openai/anthropic API shapes are stable)
