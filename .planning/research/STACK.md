# Stack Research

**Domain:** pip-library packaging + cross-repo integration + learning pipeline DB adapter
**Researched:** 2026-04-15
**Scope:** v1.1 ONLY — new capabilities for making forge-bridge consumable as a pip dependency by projekt-forge, and integrating the learning pipeline into projekt-forge's DB/config/LLM infrastructure. Does NOT re-research validated v1.0 stack.
**Confidence:** HIGH (both codebases read directly, patterns drawn from authoritative sources)

---

## Context

forge-bridge v1.0 validated stack (not re-researched):
- FastMCP, Pydantic, asyncio, JSONL persistence, httpx, websockets
- SQLAlchemy 2.0 + asyncpg + alembic for forge-bridge's own store
- pyproject.toml with hatchling, optional [llm] extras, 159 tests passing

This file covers only the **new** capabilities needed for v1.1:
1. Hardening forge-bridge's public API surface for external consumption
2. Rewiring projekt-forge to consume forge-bridge as a pip dependency
3. Integrating the learning pipeline into projekt-forge's existing infrastructure

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python `__init__.py` with `__all__` | stdlib | Public API surface declaration | Standard Python contract — what is in `__all__` is the stable surface. Currently `forge_bridge/__init__.py` is a one-line docstring. Promoting this to a real re-export module lets projekt-forge use `from forge_bridge import LLMRouter` without caring about submodule layout, and signals clearly what is private. |
| `typing.Protocol` | stdlib 3.8+ | DB adapter interface for learning pipeline | Structural typing — projekt-forge defines a `SQLExecutionLogBackend` that satisfies the same Protocol as the existing `ExecutionLog` (JSONL). No import coupling, no inheritance from forge-bridge types. The Protocol lives in `forge_bridge/learning/execution_log.py` and costs zero lines in the consumer. |
| pyproject.toml `[project.optional-dependencies]` | hatchling (existing) | Consumer-facing extras | Already in use for `[llm]`. No new mechanism needed. Add a `[forge]` group only if projekt-forge's integration triggers a new forge-bridge dep that standalone users should not pay for. Current assessment: not needed for v1.1. |
| Semantic versioning (`1.1.0`) | hatchling (existing) | Stability contract with projekt-forge | projekt-forge pins `forge-bridge>=1.0,<2.0` in its pyproject.toml. SemVer means minor additions are backwards-compatible; major bumps signal API breaks. forge-bridge's version currently reads `0.1.0` in pyproject.toml — needs bumping to `1.0.0` as part of v1.0 milestone completion before projekt-forge can sensibly pin it. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyyaml>=6.0` | 6.0 (already in projekt-forge) | Read `/opt/forge/config.yaml` | Do NOT add to forge-bridge. Already in projekt-forge's dependencies. projekt-forge reads its YAML config and translates values to env vars before constructing forge-bridge components. forge-bridge reads configuration exclusively via `os.environ.get()`. |
| `packaging>=23.0` | 23.0+ | Runtime version compatibility guard | Do not add now. Belongs in CI version matrix tests, not runtime code. Add only if a concrete backward-compat check is needed. |
| SQLAlchemy `DeclarativeBase` (separate) | 2.0 (existing in both) | Learning pipeline log table in projekt-forge DB | Each package keeps its own `DeclarativeBase`. Do not share. forge-bridge has `forge_bridge/store/session.py` with its own `Base`; projekt-forge has `forge_bridge/db/engine.py` with its own `Base`. If projekt-forge wants SQL-persisted execution logs it defines its own `DBExecutionLog` ORM model on its `Base` and implements the `ExecutionLogBackend` Protocol. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pip install -e /path/to/forge-bridge[llm]` | Cross-repo editable install for development | Standard editable install from local path. No new tooling. During v1.1 development, projekt-forge's venv installs forge-bridge this way. In production, pin to a PyPI release or a git tag. |
| `pytest` with both repos | Cross-package integration testing | No shared test infrastructure needed for v1.1. Each repo runs its own tests. Integration is validated by projekt-forge's tests importing from `forge_bridge` (the pip package). |

---

## Installation

```bash
# In projekt-forge's virtualenv — install forge-bridge as editable dependency during development
pip install -e /path/to/forge-bridge[llm]

# In projekt-forge's pyproject.toml (after publishing to PyPI or private index)
# forge-bridge>=1.0,<2.0

# forge-bridge itself — no new packages required for v1.1
# The existing dependency set handles all new capabilities
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `typing.Protocol` for ExecutionLogBackend | `abc.ABC` with abstract methods | Use ABC when you need shared default implementations or want to enforce `super().__init__()`. For a pure interface (just a contract), Protocol avoids import coupling entirely — projekt-forge never needs to import anything from forge-bridge to satisfy the interface. |
| Separate `DeclarativeBase` per package | Shared Base class | Share a Base only when two packages are always co-deployed and their Alembic migration histories are jointly managed. projekt-forge has 4 migrations (003 adds users/roles/invites, 004 adds content_hash), forge-bridge has 2 migrations for its vocabulary store. Independent histories, independent `Base` instances. Never share across a pip dependency boundary. |
| Env var configuration pass-through | Config file parsing inside forge-bridge | forge-bridge already reads `FORGE_BRIDGE_URL`, `FORGE_LOCAL_LLM_URL`, `FORGE_SYSTEM_PROMPT`, etc. projekt-forge's `config/forge_config.py` reads `/opt/forge/config.yaml` and should map those values to env vars before constructing forge-bridge components. Keeps forge-bridge stdlib-friendly and runnable without `/opt/forge/config.yaml`. |
| Optional `router=` param on `synthesize()` | Mutating `get_router()` singleton | `get_router()` is a module-level singleton. If projekt-forge calls `get_router()` after forge-bridge sets it up with the wrong system prompt, all subsequent calls use that wrong config. Passing an explicit `LLMRouter` instance to `synthesize()` is the clean path — no shared mutable state. One-line change: `synthesize(..., router: LLMRouter | None = None)` with fallback to `get_router()`. |
| JSONL default, SQL opt-in via Protocol | SQL-only execution log | JSONL is already implemented, tested, and live. Changing the default breaks all current standalone users. Adding SQL as an opt-in via Protocol adds zero breaking changes. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Importing from `forge_bridge.db` or `forge_bridge.store` in projekt-forge | Those are forge-bridge's internal persistence layers for vocabulary entities and the wire protocol store. They are not part of the public API surface. | projekt-forge's own `forge_pipeline.db` (after module rename) for its own models |
| `pydantic.BaseSettings` in forge-bridge for config | Adds `pydantic-settings` as a mandatory dep, breaking the minimal install story. | `os.environ.get()` with defaults — already the consistent pattern throughout forge-bridge |
| Circular imports: forge-bridge importing from forge_pipeline | Breaks the dependency graph. forge-bridge is the library; projekt-forge is the consumer. | One-way only: projekt-forge imports from `forge_bridge`, never the reverse |
| Mutating the `get_router()` singleton from projekt-forge startup | If both forge-bridge's internal tools and projekt-forge's learning pipeline call `get_router()`, and projekt-forge has mutated it, forge-bridge's internal LLM health check resource shows projekt-forge's config, not the canonical one. | projekt-forge instantiates its own `LLMRouter` from env vars set before import, and passes it explicitly to `synthesize()` |
| `importlib.metadata` version guards at runtime | Startup overhead for a check that belongs in CI | Pin `forge-bridge>=1.0,<2.0` in projekt-forge's pyproject.toml and enforce in CI |

---

## Stack Patterns by Variant

**Hardening forge-bridge's public API surface (Phase: API hardening):**

Declare `forge_bridge/__init__.py` as the single stable re-export module:

```python
# forge_bridge/__init__.py
from forge_bridge.bridge import (
    BridgeResponse, BridgeError, BridgeConnectionError,
    configure, execute, execute_json, execute_and_read, ping,
    set_execution_callback,
)
from forge_bridge.llm import LLMRouter, get_router
from forge_bridge.mcp import register_tools, get_mcp
from forge_bridge.learning.execution_log import ExecutionLog
from forge_bridge.learning.synthesizer import synthesize
from forge_bridge.learning.probation import ProbationTracker

__all__ = [
    "BridgeResponse", "BridgeError", "BridgeConnectionError",
    "configure", "execute", "execute_json", "execute_and_read",
    "ping", "set_execution_callback",
    "LLMRouter", "get_router",
    "register_tools", "get_mcp",
    "ExecutionLog", "synthesize", "ProbationTracker",
]
```

Everything not in `__all__` is internal — projekt-forge never imports from submodules directly.

**DB adapter pattern for learning pipeline (Phase: Learning pipeline integration):**

Define a `Protocol` in `forge_bridge/learning/execution_log.py`:

```python
class ExecutionLogBackend(Protocol):
    def record(self, code: str, intent: str | None = None) -> bool: ...
    def mark_promoted(self, code_hash: str) -> None: ...
    def get_code(self, code_hash: str) -> str | None: ...
    def get_count(self, code_hash: str) -> int: ...
```

`ExecutionLog` (JSONL) already satisfies this structurally — no changes to its implementation.

projekt-forge defines `SQLExecutionLogBackend` implementing the same Protocol, backed by its own `DBExecutionLog` ORM model on its `Base`.

Wire-in at projekt-forge startup via the existing hook:

```python
# In projekt-forge startup
from forge_bridge import set_execution_callback
sql_backend = SQLExecutionLogBackend(session_factory)
set_execution_callback(sql_backend.record_from_bridge)
```

**LLM router override in projekt-forge (Phase: LLM integration):**

Do not mutate the singleton. Use env vars + explicit instantiation:

```python
# In projekt-forge startup (before any forge_bridge import triggers LLM init)
import os
os.environ["FORGE_SYSTEM_PROMPT"] = forge_specific_prompt
os.environ["FORGE_LOCAL_LLM_URL"] = config["local_llm_url"]
os.environ["FORGE_LOCAL_MODEL"] = "qwen2.5-coder:32b"

from forge_bridge import LLMRouter
forge_router = LLMRouter()   # picks up env vars at construction time

# Pass explicitly to synthesize instead of relying on singleton
from forge_bridge.learning.synthesizer import synthesize
await synthesize(code, intent=intent, count=count, router=forge_router)
```

Requires one change to `synthesize()`: add `router: LLMRouter | None = None` with `get_router()` fallback.

**projekt-forge module rename (Phase: Rewiring):**

After adding `forge-bridge` to projekt-forge's pyproject.toml:

1. Rename `forge_bridge/` -> `forge_pipeline/` inside projekt-forge repo
2. Update all internal `from forge_bridge.db` -> `from forge_pipeline.db` imports
3. The pip-installed `forge_bridge` package takes that namespace
4. No collision: `forge_bridge` (pip) and `forge_pipeline` (local) are distinct top-level packages

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| forge-bridge `>=1.0,<2.0` | projekt-forge dependency pin | SemVer contract. Minor additions are additive and backwards-compatible. Major bump signals API break. pyproject.toml currently says `0.1.0` — must bump to `1.0.0` as part of closing the v1.0 milestone before projekt-forge can sensibly pin it. |
| SQLAlchemy `2.0` (forge-bridge store/) | SQLAlchemy `2.0` (projekt-forge db/) | Same major version in both. No conflict when co-installed. Both use `asyncpg` driver. Both use separate `DeclarativeBase` instances — metadata is not shared and migrations run independently. |
| alembic `>=1.13` (forge-bridge) | alembic `>=1.13` (projekt-forge) | Each package has its own `alembic.ini` and `versions/` directory, targeting different database schemas. Independent migration histories. |
| `openai>=1.0` (forge-bridge `[llm]` extra) | projekt-forge (no direct openai usage) | forge-bridge uses the openai client as an OpenAI-compatible Ollama adapter. No version conflict with anthropic. |

---

## Key Integration Seams

The four specific code points that v1.1 must address (not just stack, but where the integration attaches):

### 1. `forge_bridge/__init__.py` — Public API declaration
Currently a one-line docstring. Becomes the stable re-export module (see pattern above).
Location: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/__init__.py`

### 2. `forge_bridge/bridge.py:set_execution_callback` — Learning pipeline injection
Already exists and tested. projekt-forge calls this with its `SQLExecutionLogBackend`.
Callback signature: `(code: str, response: BridgeResponse) -> None` — already defined.
No API changes needed on forge-bridge's side.

### 3. `forge_bridge/learning/synthesizer.py:synthesize()` — LLM router injection
Add `router: LLMRouter | None = None` parameter. Fall back to `get_router()` if None.
One-line change. Lets projekt-forge pass its pre-configured router.

### 4. `forge_bridge/mcp/__init__.py:register_tools` — Tool registration
Already public and tested. projekt-forge calls `register_tools(get_mcp(), [...])` to add
`forge_catalog`, `forge_orchestrate`, etc. before `mcp.run()`.
No changes needed. Document in public API.

---

## Sources

- Direct codebase read: forge-bridge `/Users/cnoellert/Documents/GitHub/forge-bridge/` — HIGH confidence
- Direct codebase read: projekt-forge `/Users/cnoellert/Documents/GitHub/projekt-forge/` — HIGH confidence
- [Python packaging optional dependencies](https://www.pyopensci.org/python-package-guide/package-structure-code/declare-dependencies.html) — HIGH confidence
- [Python public API surface — Real Python](https://realpython.com/ref/best-practices/public-api-surface/) — HIGH confidence
- [SQLAlchemy 2.0 multiple declarative bases](https://github.com/sqlalchemy/sqlalchemy/discussions/10519) — MEDIUM confidence (community discussion, consistent with docs)
- [Dependency inversion in Python](https://www.lpld.io/articles/how-to-depend-on-abstractions-rather-than-implementations-in-python/) — HIGH confidence
- [Recursive optional deps — Hynek Schlawack](https://hynek.me/articles/python-recursive-optional-dependencies/) — HIGH confidence
- [PEP 440 version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/) — HIGH confidence

---

*Stack research for: forge-bridge v1.1 projekt-forge integration*
*Researched: 2026-04-15*
