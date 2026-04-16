# Project Research Summary

**Project:** forge-bridge v1.1 — projekt-forge integration
**Domain:** Cross-repo pip dependency consumption and learning pipeline integration
**Researched:** 2026-04-15
**Confidence:** HIGH

## Executive Summary

forge-bridge v1.1 is an integration milestone, not a product feature release. The goal is to transform forge-bridge from a standalone tool into a consumable pip library that projekt-forge depends on, while simultaneously wiring forge-bridge's learning pipeline into projekt-forge's existing LLM, DB, and config infrastructure. All four research tracks agree on the same execution sequence: harden the public API surface first, rewire projekt-forge second, integrate the learning pipeline third. Nothing in Phase 2 or Phase 3 is safe to start until Phase 1 is complete.

The recommended approach is dependency injection throughout. Every place where forge-bridge currently uses module-level singletons or hardcoded env vars (LLMRouter, ExecutionLog, Synthesizer), projekt-forge needs constructor injection so it can supply its own Ollama URL, log path, system prompt, and DB session factory without mutating global state. The existing callback hook (`set_execution_callback`) and tool registration API (`register_tools`) are already correctly designed — they need only to be promoted to the stable public surface and documented.

The primary risk is the import namespace collision: projekt-forge currently has its own `forge_bridge/` directory (a fork-diverged copy of forge-bridge's code). When forge-bridge is added as a pip dependency, Python's import resolution will silently shadow whichever copy appears later in `sys.path`. The migration must be atomic — remove the local directory and add the pip dependency in a single commit. The secondary risk is scope creep in Phase 1: forge-specific content already baked into forge-bridge's internals (`portofino`, `assist-01`, `ACM_` naming in `_DEFAULT_SYSTEM_PROMPT`) constitutes a latent circular dependency that must be removed before projekt-forge integration begins.

## Key Findings

### Recommended Stack

No new dependencies are required for v1.1. The existing stack (FastMCP, Pydantic, asyncio, SQLAlchemy 2.0, httpx, hatchling) handles all new capabilities. The integration is entirely about Python packaging patterns and API design.

forge-bridge's `pyproject.toml` currently declares version `0.1.0` — this must be bumped to `1.0.0` as part of closing the v1.0 milestone before projekt-forge can sensibly pin against it. projekt-forge should use a compatible-release specifier (`forge-bridge>=1.0,<2.0`) to allow minor-version additions while blocking breaking changes.

**Core technologies:**
- `forge_bridge/__init__.py` with `__all__`: stable public API surface — currently a one-line docstring with no exports; must become the single re-export module
- `typing.Protocol` (stdlib 3.8+): DB adapter interface for execution log backends — structural typing with zero import coupling between repos
- `pip install -e /path/to/forge-bridge[llm]`: cross-repo editable install during development — eliminates version skew while both repos evolve together
- Separate `DeclarativeBase` per package: independent Alembic migration histories — never share a Base across a pip dependency boundary; already the pattern in both repos

### Expected Features

This milestone's "features" are engineering contracts and integration seams, not user-visible capabilities.

**Must have (table stakes):**
- Stable `__init__.py` exports — `configure`, `set_execution_callback`, `register_tools`, `get_mcp`, `BridgeResponse`, `BridgeError`, `LLMRouter`, `ExecutionLog`, `synthesize`, `ProbationTracker` all re-exported from package root with `__all__` declared
- `LLMRouter` constructor injection — `LLMRouter(local_url, local_model, system_prompt)` with env-var fallback; projekt-forge has its own Ollama and must not rely on env var timing or singleton mutation
- `register_tools()` accepting `source="builtin"` from downstream — currently blocked for non-synthesized sources; blocks projekt-forge's forge-specific tools from registering
- projekt-forge import rewiring — delete duplicated `forge_bridge/bridge.py`, `forge_bridge/tools/*.py`, `forge_bridge/client/` from projekt-forge; replace with imports from pip package
- Learning pipeline wired in projekt-forge — startup calls `set_execution_callback()` with projekt-forge's own storage callback

**Should have (integration value-add):**
- Execution log path overridable at construction — prevents log path collision when two processes run simultaneously
- `startup_bridge()` / `shutdown_bridge()` promoted to public in `mcp/server.py` — enables projekt-forge to control lifecycle without monkey-patching `_lifespan`
- Cross-repo integration smoke tests in projekt-forge's test suite
- `_server_started` runtime guard on `register_tools()` — raises `RuntimeError` if called after `mcp.run()`, preventing silent tool drops

**Defer (v1.1.x and beyond):**
- `pre_synthesis_hook` on SkillSynthesizer — highest complexity; depends on all other wiring being confirmed first
- Shared synthesis manifest between repos — complex schema questions, defer
- Tool provenance in MCP annotations — low value-to-effort ratio
- Authentication — explicitly deferred, local-first deployment only

### Architecture Approach

The integration follows a strict one-way dependency graph: projekt-forge imports from forge-bridge; forge-bridge never imports from projekt-forge. forge-bridge exposes a hardened public API; projekt-forge calls that API at startup to configure all injectable components before starting the MCP server. projekt-forge's forge-specific tools (catalog, orchestrate, scan, seed) are registered via `register_tools()` after builtins are loaded, before `mcp.run()`.

**Major components:**
1. `forge_bridge/__init__.py` — single stable re-export module; the only import surface projekt-forge is permitted to touch
2. `forge_bridge.mcp` (register_tools, get_mcp) — additive tool registration; projekt-forge extends the shared FastMCP instance without forking `server.py`
3. `forge_bridge.llm.LLMRouter` — injectable; projekt-forge supplies its own URL, model, and system prompt via constructor args at startup
4. `forge_bridge.learning` (ExecutionLog, Synthesizer, ProbationTracker) — injectable; projekt-forge wires its own storage backend and LLM config
5. `forge_mcp/` in projekt-forge — new module owning the augmented MCP server entry point and all forge-specific tools (catalog, orchestrate, scan, seed)
6. `forge_pipeline/` in projekt-forge — rename of projekt-forge's existing `forge_bridge/` directory to free the namespace for the pip package

### Critical Pitfalls

1. **Accidental public API breakage** — any internal rename in forge-bridge after projekt-forge has started coupling to submodule paths causes silent `ImportError` in deployment. Prevention: declare `__all__` at package root and add an import smoke test for every public symbol before writing any projekt-forge integration code. (Phase 1)

2. **Import namespace collision** — Python's `sys.path` will silently shadow either the local `forge_bridge/` directory or the pip-installed package. Prevention: the migration must be atomic — delete `forge_bridge/` from projekt-forge and add the pip dep in a single commit; assert `forge_bridge.__file__` resolves to site-packages in CI. (Phase 2)

3. **Circular dependency from forge-specific content in forge-bridge** — `_DEFAULT_SYSTEM_PROMPT` in `router.py` already contains `portofino`, `assist-01`, and `ACM_` naming conventions. This is a direct circular dependency smell that will block standalone testing. Prevention: purge forge-specific content from forge-bridge in Phase 1; all context enrichment lives in projekt-forge. (Phase 1)

4. **`register_tools()` called after `mcp.run()`** — tools register silently but are never visible to MCP clients. Prevention: add a `_server_started` flag with `RuntimeError` guard; enforce in forge-bridge Phase 1 so projekt-forge benefits automatically. (Phase 1/2)

5. **Execution log path collision** — two processes sharing `~/.forge-bridge/executions.jsonl` share promotion counts, triggering spurious synthesis. Prevention: make log path configurable at construction and document that projekt-forge must supply a distinct path. (Phase 3)

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Harden Public API Surface
**Rationale:** Every other phase depends on knowing which forge-bridge symbols are stable contracts. Starting projekt-forge integration work before the API is stable guarantees breakage. This phase is entirely within the forge-bridge repo.
**Delivers:** forge-bridge with a declared public surface (`__all__`, re-exports); LLMRouter and Synthesizer accepting constructor injection; `register_tools()` accepting `source="builtin"`; `startup_bridge()`/`shutdown_bridge()` public; `_server_started` guard; forge-specific content purged from `_DEFAULT_SYSTEM_PROMPT`; version bumped to `1.0.0`.
**Addresses:** Stable API exports, LLMRouter constructor injection, register_tools `source="builtin"` support, runtime guard.
**Avoids:** Pitfall 1 (API breakage), Pitfall 4 (circular dependency), Pitfall 8 (register_tools race).
**Changes:** forge-bridge only. projekt-forge is untouched.

### Phase 2: Rewire projekt-forge to Consume forge-bridge as Pip Dependency
**Rationale:** Mechanical rewire that is only safe after Phase 1 because it depends on the stable API. Must be executed as a single atomic commit to avoid import shadowing. Low creative risk, medium file-count effort.
**Delivers:** projekt-forge with no duplicated forge-bridge code; `forge-bridge>=1.0,<2.0` in its pyproject.toml; forge-specific tools registered via `register_tools()`; `pip check` passing in CI.
**Addresses:** Import rewiring, compatible-release version pinning, `pip check` CI gate, `source="builtin"` for forge tools.
**Avoids:** Pitfall 2 (import namespace collision), Pitfall 3 (version pinning traps), Pitfall 6 (transitive dep conflicts).
**Changes:** projekt-forge only. forge-bridge is a read-only pip dependency at this point.

### Phase 3: Wire Learning Pipeline into projekt-forge
**Rationale:** Depends on both Phase 1 (constructor injection available) and Phase 2 (forge-bridge is the sole source of truth, no local fork). Learning pipeline integration is the highest-complexity work and must not start until the integration foundation is confirmed.
**Delivers:** projekt-forge startup constructs and injects LLMRouter, ExecutionLog (with distinct log path), and Synthesizer using `forge_config.yaml` values; execution callback fires into projekt-forge's storage; synthesis uses Ollama at forge's configured URL.
**Addresses:** LLM override via constructor injection, execution log path isolation, DB persistence decision (JSONL default; optional Postgres via separate Alembic chain with projekt-forge's own Base).
**Avoids:** Pitfall 5 (log path collision), Pitfall 7 (Alembic migration conflict), Pitfall 4 (circular dep via system prompt).
**Changes:** projekt-forge primarily; one-line `router` param addition to `synthesize()` in forge-bridge if not already done in Phase 1.

### Phase Ordering Rationale

- Phase 1 is a strict prerequisite for Phase 2: projekt-forge cannot safely import forge-bridge until the public API is declared. Attempting the rewire against an undeclared API means any internal forge-bridge restructuring breaks projekt-forge silently.
- Phase 2 is a strict prerequisite for Phase 3: learning pipeline wiring requires knowing which `set_execution_callback` and `LLMRouter` are canonical. That is only certain after projekt-forge's local `forge_bridge/` directory is removed and the pip package is the sole source of truth.
- The three phases are strictly sequential. Each adds a safety net that the next relies on.

### Research Flags

Phases with standard patterns — no additional research needed:
- **Phase 1:** Public API surface declaration with `__all__` and constructor injection are well-documented Python patterns. Direct implementation, no research phase needed.
- **Phase 2:** Atomic directory removal + pip dep addition is a standard migration. `importmode=importlib` and `pip check` are standard CI practices.

Phases that may benefit from targeted investigation during planning:
- **Phase 3 (if DB persistence is in v1.1 scope):** The optional PostgreSQL backend for `ExecutionLog` via `typing.Protocol` and a separate Alembic chain has nuance in the context of projekt-forge's per-project DB architecture. A focused spike on the `ExecutionLogBackend` Protocol design is warranted before committing to implementation.
- **Phase 3 (if pre_synthesis_hook is pulled into v1.1):** This is new API surface in forge-bridge driven by projekt-forge's needs. Requires a design session before implementation to avoid introducing a dependency inversion.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Both codebases read directly; no new dependencies required; version compatibility confirmed from both pyproject.toml files |
| Features | HIGH | Derived from direct code inspection of what exists vs. what projekt-forge needs; no speculation required |
| Architecture | HIGH | Integration seams identified from actual source files; build order derived from real dependency graph |
| Pitfalls | HIGH | Pitfalls 1-5, 7-8 have direct codebase evidence (forge-specific content in router.py confirmed, namespace collision risk confirmed, Alembic chains confirmed separate); Pitfall 6 is inferred from transitive dep patterns (MEDIUM) |

**Overall confidence:** HIGH

### Gaps to Address

- **Version bump to 1.0.0:** pyproject.toml currently reads `0.1.0`. Must bump to `1.0.0` before projekt-forge can sensibly pin. Decide whether this release goes to PyPI or stays git-tag-only during v1.1 development.
- **projekt-forge import blast radius:** How many internal files in projekt-forge import from `forge_bridge.*` (the local directory) was not measured during research. A one-time grep of projekt-forge before writing the Phase 2 task list is needed to scope the effort accurately.
- **DB persistence scope in v1.1:** PROJECT.md mentions execution log persistence to forge DB, but the research treats it as Phase 3 optional. Needs an explicit decision before Phase 3 task list is written: is SQL persistence in v1.1 or deferred to v1.1.x?
- **`mcp/server.py` lifespan refactor scope:** Promoting `_startup`/`_shutdown` to public requires checking whether forge-bridge's own test suite depends on the private names. Low risk but needs a quick audit before Phase 1 implementation starts.

## Sources

### Primary (HIGH confidence)
- Direct codebase read: `/Users/cnoellert/Documents/GitHub/forge-bridge/` — all modules cited in research files
- Direct codebase read: `/Users/cnoellert/Documents/GitHub/projekt-forge/` — duplicate tools, server, config, and DB modules
- Python Packaging User Guide — public API surface, `__all__`, SemVer: https://packaging.python.org/en/latest/discussions/versioning/
- Real Python — public API surface best practices: https://realpython.com/ref/best-practices/public-api-surface/
- Hynek Schlawack — recursive optional dependencies: https://hynek.me/articles/python-recursive-optional-dependencies/
- PEP 440 version specifiers: https://packaging.python.org/en/latest/specifications/version-specifiers/

### Secondary (MEDIUM confidence)
- SQLAlchemy community discussion — multiple declarative bases across packages: https://github.com/sqlalchemy/sqlalchemy/discussions/10519
- pytest good practices — editable install cross-repo testing: https://docs.pytest.org/en/stable/explanation/goodpractices.html
- setuptools entry_points — plugin/callback registration patterns: https://setuptools.pypa.io/en/latest/userguide/entry_point.html

---
*Research completed: 2026-04-15*
*Ready for roadmap: yes*
