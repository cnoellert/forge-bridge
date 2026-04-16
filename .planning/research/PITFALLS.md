# Pitfalls Research

**Domain:** Cross-repo pip dependency consumption and learning pipeline integration — adding projekt-forge as a downstream consumer of forge-bridge without breaking either deployed system
**Researched:** 2026-04-15
**Confidence:** HIGH (based on direct codebase analysis of forge-bridge v1.0 source, MIGRATION_PLAN.md, and known patterns from Python packaging and cross-repo integration work)

---

## Critical Pitfalls

### Pitfall 1: Accidentally Breaking the Public API Surface During Hardening

**What goes wrong:**
"Hardening the public API" is understood as an additive step — add `__all__`, tighten docstrings, maybe mark private helpers with underscores. In practice, hardening often involves renaming or removing things that were never meant to be public but that projekt-forge has already started importing from. Any rename in forge-bridge's internals becomes a breaking change for projekt-forge the moment projekt-forge has a `from forge_bridge.mcp.registry import register_tool` anywhere. The forge_mcp → forge_bridge.mcp rename already happened once in v1.0 — the same pattern can repeat.

**Why it happens:**
Without an explicit public API contract, everything is implicitly public. When forge-bridge restructures to make an internal helper private (e.g., moves `_validate_name` from registry.py, renames `mcp/tools.py` to `mcp/_builtins.py`), there is no enforcement that downstream consumers haven't coupled to the internal symbol. The first time projekt-forge installs the new version it gets `ImportError` on a symbol that "wasn't supposed to be public."

**How to avoid:**
- Define the public API contract in `forge_bridge/__init__.py` before writing any projekt-forge integration code. Explicitly re-export every symbol that projekt-forge will need: `register_tools`, `get_mcp`, `BridgeResponse`, `BridgeError`, `LLMRouter`, `ExecutionLog`. Set `__all__` on every public submodule.
- Adopt the rule: if it is not in `__all__` at the package level, it is private. projekt-forge may only import from the public surface.
- Verify the public surface is stable before starting the rewire work in projekt-forge. Write a test that imports every public symbol and confirms it is importable.

**Warning signs:**
`ImportError` appearing in projekt-forge after a forge-bridge version bump. `from forge_bridge.mcp import tools` (importing a private module directly) rather than `from forge_bridge.mcp import register_tools` (importing the declared public API).

**Phase to address:**
Phase 1 — Harden public API surface. Must complete before projekt-forge touches any forge-bridge import.

---

### Pitfall 2: Import Path Migration Leaves Deployed projekt-forge on Stale Imports

**What goes wrong:**
projekt-forge currently has its own `forge_bridge/` directory (the evolved, fork-diverged version). When the rewire happens, `from forge_bridge.db import ...` changes meaning — it used to mean "from projekt-forge's own forge_bridge package" and will now mean "from the pip-installed forge-bridge package." If any module in projekt-forge imports from `forge_bridge` and that import resolves to the local `forge_bridge/` directory (because the package is installed in editable mode or because PYTHONPATH is wrong), the migration is silently broken. Code appears to work locally but fails in deployment.

**Why it happens:**
Python's import system resolves packages by searching `sys.path` in order. If `forge_bridge/` is present as a directory in the current working directory or on `PYTHONPATH`, it will shadow the pip-installed `forge_bridge` package. During a migration where both exist simultaneously (before the local directory is removed), every test run may be using the local stale version without warning.

**How to avoid:**
- Do not rename the local `forge_bridge/` directory in projekt-forge to something else (e.g., `forge_pipeline/`) as an intermediate step — that leaves a period where both `forge_bridge/` (local) and `forge_bridge` (pip) exist. Instead, remove the local directory completely in the same commit that adds the pip dependency.
- Use `python -c "import forge_bridge; print(forge_bridge.__file__)"` as the first step of every CI/CD run to assert the import resolves to the installed package, not a local directory.
- In pytest configuration, add an `importmode = importlib` setting (pytest 6+) to avoid ambiguous path-based imports.

**Warning signs:**
`forge_bridge.__file__` points to a path inside the projekt-forge repo tree rather than to the site-packages directory. Tests pass locally but fail in clean CI environments (or vice versa). A `pip show forge-bridge` shows no version while `python -c "import forge_bridge"` succeeds.

**Phase to address:**
Phase 2 — Rewire projekt-forge. The migration must be atomic: remove local directory and add pip dep in one commit.

---

### Pitfall 3: Version Pinning Traps projekt-forge on a Stale forge-bridge

**What goes wrong:**
projekt-forge pins `forge-bridge==0.1.0` in its pyproject.toml. forge-bridge ships a bug fix or API improvement in `0.2.0`. projekt-forge developers install fresh and get `0.1.0` (pinned). They notice the learning pipeline behaves differently from what they are developing against in the forge-bridge repo. Eventually the pin becomes a maintenance burden: every forge-bridge update requires a manual pin bump in projekt-forge, and the two repos drift.

The opposite failure: using `forge-bridge>=0.1.0` (no upper bound) means a breaking forge-bridge change silently updates into a deployed projekt-forge, breaking the production system without any change to projekt-forge's own codebase.

**Why it happens:**
These two repos are closely coupled and developed by the same person. The pinning discipline that makes sense for third-party dependencies (pin exact, update deliberately) is unnecessarily rigid for a first-party repo pair. But no pinning is too loose.

**How to avoid:**
- Use a compatible-release specifier (`forge-bridge~=0.1.0`, equivalent to `>=0.1.0, <0.2.0`) until a stable API contract exists. This allows patch updates but not minor-version bumps.
- When the public API is stable and both repos are in production, move to `forge-bridge>=0.1.0,<1.0.0` (major version guard).
- Pair each forge-bridge release with a CHANGELOG entry that explicitly tags breaking vs non-breaking changes.
- Do not publish forge-bridge to PyPI until the public API is stable. Use a local editable install (`pip install -e ../forge-bridge`) during development, which eliminates version skew entirely while both repos are evolving together.

**Warning signs:**
`pip install projekt-forge` silently installs a forge-bridge version that doesn't match what's in the forge-bridge repo. Tests pass on the developer's machine (editable install) but fail in CI (pinned install). `forge_bridge.__version__` differs between environments.

**Phase to address:**
Phase 2 — Rewire projekt-forge. Pin strategy must be decided before the first `pip install forge-bridge` in projekt-forge's pyproject.toml.

---

### Pitfall 4: Circular Dependency Risk from forge-bridge Importing forge-specific Concepts

**What goes wrong:**
During the learning pipeline integration in projekt-forge (Phase 3), there is pressure to put convenience helpers in forge-bridge: "it would be nice if forge-bridge's `LLMRouter` knew the project naming convention" or "the synthesizer should support forge's custom roles." These additions get committed to forge-bridge because that's where the code lives. Now forge-bridge imports from forge-specific configuration. projekt-forge depends on forge-bridge. forge-bridge depends on projekt-forge concepts. A circular dependency forms.

At import time this manifests as `ImportError: cannot import name X from partially initialized module`. In practice it is often subtler: config objects that are None until projekt-forge initialises them, or monkey-patching patterns that work on the developer's machine but fail in clean environments.

**Why it happens:**
The boundary between "generic pipeline infrastructure" (forge-bridge) and "forge-specific pipeline logic" (projekt-forge) is clear in the design but erodes under development pressure. The LLM router's default system prompt already contains `portofino`, `assist-01`, and forge naming conventions — this is the exact smell that leads to circular dependency.

**How to avoid:**
- Enforce the constraint defined in PROJECT.md: "forge-bridge must work without projekt-forge. No imports from forge-specific modules." Write a test in forge-bridge's test suite that installs forge-bridge without projekt-forge in a fresh virtualenv and runs the full test suite. This will fail immediately if a circular import is introduced.
- The LLM router's system prompt must be configurable via environment variable, not hardcoded with forge-specific context. `FORGE_SYSTEM_PROMPT` env var or a `configure_router(system_prompt=...)` call.
- Any context enrichment (adding forge roles, naming conventions, project paths to synthesis prompts) must happen in projekt-forge's wrapper, not in forge-bridge's code.

**Warning signs:**
`from forge_bridge.llm.router import _DEFAULT_SYSTEM_PROMPT` shows hostnames or naming conventions that are forge-specific (it already does — `portofino`, `ACM_0010_comp_v003`). A forge-bridge import requires projekt-forge to be installed.

**Phase to address:**
Phase 1 (public API hardening) — clean the router's system prompt before Phase 3 wires in project context. Phase 3 should add context enrichment at the projekt-forge layer only.

---

### Pitfall 5: Learning Pipeline JSONL Log Path Collision Between forge-bridge and projekt-forge Consumers

**What goes wrong:**
The `ExecutionLog` hardcodes its path to `~/.forge-bridge/executions.jsonl`. If projekt-forge runs its own forge-bridge instance (e.g., a separate process, a test runner, a different user session) alongside the original forge-bridge process, both write to the same file. Concurrent writes are guarded by `fcntl.flock`, so data corruption is unlikely — but the two consumers share promotion counts. A Flame execution in projekt-forge's context crosses the promotion threshold, and the learning pipeline in the standalone forge-bridge process attempts to synthesize a tool for a code pattern it has no context for.

Additionally, if projekt-forge wants to persist execution logs to its PostgreSQL database (as specified in PROJECT.md), the JSONL path becomes the wrong storage target entirely — but the `ExecutionLog` class is not designed to be subclassed or injected with a different backend.

**Why it happens:**
The JSONL path was designed for a single consumer. The architecture didn't anticipate two separate processes both using forge-bridge's execution log simultaneously.

**How to avoid:**
- Make the `ExecutionLog` path configurable at instantiation time, not hardcoded as a module-level constant. `ExecutionLog(log_path=Path("~/.projekt-forge/executions.jsonl"))` for the projekt-forge consumer.
- When projekt-forge wants DB persistence, implement `ExecutionLog` as an abstract base with a `record()` and `replay()` interface. The JSONL implementation is the default; projekt-forge provides a DB-backed subclass. The `set_execution_callback()` on `bridge.py` accepts any callable — the callback can be swapped without changing forge-bridge's code.
- As a minimum viable fix: allow the path to be set via an env var `FORGE_EXECUTION_LOG_PATH`. This requires zero API change and prevents the path collision.

**Warning signs:**
Synthesis triggering for code patterns that the forge-bridge process has no context for. `~/.forge-bridge/executions.jsonl` growing at unexpectedly high rate. Two processes both showing promotion events in logs simultaneously.

**Phase to address:**
Phase 3 — Learning pipeline integration in projekt-forge. The configurable path fix should land in forge-bridge before this phase begins.

---

## Moderate Pitfalls

### Pitfall 6: Optional Deps Pattern Silently Breaks When projekt-forge Adds Transitive Dependencies

**What goes wrong:**
forge-bridge uses optional extras: `pip install forge-bridge[llm]` installs openai and anthropic. projekt-forge adds `forge-bridge[llm]` to its own pyproject.toml. This works. Six months later, projekt-forge adds another dependency that pins `openai==1.3.0` (a hypothetical conflict with forge-bridge's `openai>=1.0`). pip silently resolves to the older version. The LLM router starts failing with subtle API incompatibilities that are hard to attribute to a version downgrade.

The reverse: forge-bridge bumps `openai>=1.50` in a patch release. projekt-forge's pinned old version gets silently upgraded on next install. The upgrade changes an async API signature that the router uses.

**Why it happens:**
Optional extras add transitive dependencies that cross-repo. Neither developer is thinking about the other repo's pins when they update their own.

**How to avoid:**
- Add pip-audit or a dependency conflict check to both repos' CI (simple: `pip check` after install — it reports incompatible requirements).
- Keep the `[llm]` extra minimal: only the packages directly called in `router.py`. Do not add convenience packages to extras that might conflict.
- Maintain a test in projekt-forge that does a fresh install of both repos and runs `pip check`. This catches transitive conflicts before they hit production.

**Warning signs:**
`pip check` reports conflicts after installation. `openai.__version__` or `anthropic.__version__` showing a different version than expected in logs.

**Phase to address:**
Phase 2 — Rewire projekt-forge. Add `pip check` to CI at the start of the rewire phase.

---

### Pitfall 7: Database Migration Risk When projekt-forge Shares forge-bridge's PostgreSQL Schema

**What goes wrong:**
forge-bridge has its own PostgreSQL database (`forge_bridge` on portofino, port 7533). projekt-forge has its own database with users, roles, invites, content hashes. These are separate schemas and separate connection strings — the design explicitly keeps them separated.

The risk is in the learning pipeline integration: if execution logs are persisted to "forge DB" (as stated in PROJECT.md), it is ambiguous which DB this means. If projekt-forge adds tables to forge-bridge's Alembic migration chain (because it imports `Base` from `forge_bridge.store.models`), then a `alembic upgrade head` in forge-bridge's context will run projekt-forge's migrations, and vice versa. Two separate Alembic histories pointing at the same SQLAlchemy Base will produce migration conflicts.

**Why it happens:**
Alembic tracks migrations by the `alembic_version` table and by revision IDs. If both repos extend the same `Base` and run against the same database, the first `upgrade head` merges cleanly but the second sees an unexpected revision and either errors or runs stale migrations.

**How to avoid:**
- Do not share the SQLAlchemy `Base` across repos. projekt-forge defines its own `Base` for its own tables. If projekt-forge needs to write execution logs to a database, it defines its own `execution_logs` table in its own migration chain, separate from forge-bridge's schema.
- Never import `forge_bridge.store.models.Base` in projekt-forge and extend it. Use composition, not inheritance.
- The cleanest implementation: projekt-forge's DB-backed execution log writes to its own `forge_pipeline.executions` table. The log path and storage are a projekt-forge concern. forge-bridge's JSONL-backed `ExecutionLog` remains untouched.

**Warning signs:**
`alembic upgrade head` in forge-bridge produces a migration file that references projekt-forge table names. `alembic history` shows revision chains from two repos interleaved.

**Phase to address:**
Phase 3 — Learning pipeline integration in projekt-forge. Explicitly decide which database the execution log writes to before implementing, and confirm the Alembic chains are separate.

---

### Pitfall 8: `register_tools()` Called After `mcp.run()` Silently Drops Tools in projekt-forge

**What goes wrong:**
This pitfall was documented for v1.0 but the risk increases in the v1.1 context. projekt-forge's startup sequence may be: initialise DB, run migrations, seed registry, then call `register_tools()`. By the time projekt-forge completes its startup, `mcp.run()` may already be running (if forge-bridge is started as a subprocess or if projekt-forge's server wraps forge-bridge). projekt-forge's tools are registered but not visible to any connected client because no `tools/list_changed` notification was sent.

The difference from v1.0: in v1.0 the risk was theoretical. In v1.1 there is a real downstream consumer with a real startup sequence that may not call `register_tools()` at the right moment.

**How to avoid:**
- Document in the `register_tools()` docstring that it must be called before `mcp.run()` and add a runtime guard: after `mcp.run()` is called, set a `_server_started` flag, and if `register_tools()` is called after that flag is set, raise `RuntimeError` with a clear message rather than silently succeeding.
- Provide a startup hook pattern: `forge_bridge.mcp.on_startup(callback)` where `callback` receives the mcp instance and calls `register_tools()`. This guarantees ordering.
- Write an integration test in projekt-forge that verifies its tools appear in `tools/list` after startup — not just that `register_tools()` returns without error.

**Warning signs:**
projekt-forge-specific tools not appearing in Claude's `tools/list`. `register_tools()` returns without error but the tools are absent. No `RuntimeError` raised even though `mcp.run()` was already called.

**Phase to address:**
Phase 2 — Rewire projekt-forge (when the first `register_tools()` call is added to projekt-forge). The runtime guard should be added to forge-bridge in Phase 1.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Editable install (`pip install -e`) for both repos during development | No version bumps needed, changes are immediate | Hides version skew bugs; CI will have different behavior than developer's machine | Development only — CI must use release install |
| Using `forge_bridge.store.models.Base` in projekt-forge | Reuse the existing ORM setup | Merged Alembic history, migration conflicts, tight coupling to forge-bridge internals | Never |
| Extending `_DEFAULT_SYSTEM_PROMPT` in router.py for forge context | Single file to edit | forge-bridge imports forge-specific knowledge; violates standalone constraint | Never |
| Keeping projekt-forge's local `forge_bridge/` directory during migration | Incremental migration, easier rollback | Two `forge_bridge` packages on sys.path; import resolution ambiguity | Never — remove atomically |
| Setting `FORGE_EXECUTION_LOG_PATH` as workaround instead of proper DI | Quick fix, no API change | Env var proliferation; not composable for multiple consumers | Acceptable as Phase 3 temporary fix while proper DI is designed |
| Version pinning `forge-bridge==0.1.0` indefinitely | Prevents unexpected breakage | No bug fixes flow through; pin becomes maintenance debt | Acceptable during active v1.1 development only |

---

## Integration Gotchas

Common mistakes when connecting forge-bridge to projekt-forge as a pip dependency.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Import path migration | Renaming local `forge_bridge/` in projekt-forge before removing it | Remove the local directory atomically in the same commit that adds the pip dep |
| `register_tools()` API | Calling after `mcp.run()` in projekt-forge's startup | Call in a pre-startup hook before `mcp.run()`; enforce with runtime guard |
| LLM router system prompt | Adding forge-specific context to `_DEFAULT_SYSTEM_PROMPT` in forge-bridge | Pass context via `configure_router(system_prompt=...)` in projekt-forge's startup |
| Execution log persistence | Writing to forge-bridge's JSONL from projekt-forge | Configure separate log path via env var; defer DB persistence to projekt-forge's own table |
| Alembic migration chain | Importing forge-bridge's `Base` in projekt-forge and adding migrations | Define projekt-forge's own `Base` and migration chain in a separate Alembic env |
| Optional deps | Installing `forge-bridge` without `[llm]` extra and calling synthesis | Check `learning_pipeline_enabled()` before wiring hook; synthesizer must degrade gracefully |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Public API hardening:** `__all__` is set on `forge_bridge/__init__.py` — verify every symbol projekt-forge needs is explicitly listed and importable from the package root, not just a submodule path
- [ ] **Import path migration:** `pip show forge-bridge` succeeds and `forge_bridge.__file__` points to site-packages, not to a local directory in the projekt-forge repo tree
- [ ] **register_tools() contract:** `register_tools()` returns without error — verify tools actually appear in the MCP client's `tools/list` response after calling it
- [ ] **Execution log path:** Learning pipeline initialises without error — verify `FORGE_EXECUTION_LOG_PATH` (or configured path) is distinct between forge-bridge and projekt-forge processes, not both writing to `~/.forge-bridge/executions.jsonl`
- [ ] **LLM router system prompt:** Router passes smoke test — verify `_DEFAULT_SYSTEM_PROMPT` no longer contains `portofino`, `assist-01`, or `ACM_` (forge-specific content). Context enrichment must be applied by projekt-forge, not baked into forge-bridge.
- [ ] **Version pinning:** `pip install projekt-forge` in a clean virtualenv — verify `forge-bridge` resolves to the expected version and `pip check` reports no conflicts
- [ ] **Circular dependency guard:** `pip install forge-bridge` in a clean virtualenv without projekt-forge installed — verify the full test suite passes with no `ImportError` related to missing forge-specific modules

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Public API breakage causes ImportError in deployed projekt-forge | MEDIUM | Revert forge-bridge to last stable tag; publish hotfix release; bump projekt-forge pin. Introduce semver policy before next release. |
| Import path collision (local dir shadows pip package) | LOW | Delete local `forge_bridge/` directory in projekt-forge, reinstall in clean venv, rerun tests |
| Circular dependency introduced | HIGH | Identify the offending import in forge-bridge, extract the forge-specific concept into a configurable parameter, release a new forge-bridge version, update projekt-forge |
| JSONL path collision causes spurious synthesis in forge-bridge | LOW | Set `FORGE_EXECUTION_LOG_PATH` to distinct paths for each process; restart both services |
| Alembic migration conflict from shared Base | HIGH | Do not attempt to merge the migration histories. Define a clean separation: projekt-forge creates a new Alembic environment pointing only at its own tables. forge-bridge's migrations remain independent. |
| `register_tools()` race: tools not visible after startup | LOW | Add the `_server_started` runtime guard to forge-bridge; update projekt-forge to call `register_tools()` earlier in its startup sequence |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Breaking public API accidentally (Pitfall 1) | Phase 1 — Harden public API | All public symbols importable from `forge_bridge` root; `__all__` set; import test passes |
| Import path migration leaves stale imports (Pitfall 2) | Phase 2 — Rewire projekt-forge | `forge_bridge.__file__` resolves to site-packages; `pip show forge-bridge` shows correct version |
| Version pinning traps (Pitfall 3) | Phase 2 — Rewire projekt-forge | Compatible-release specifier in pyproject.toml; `pip check` passes in clean venv |
| Circular dependency (Pitfall 4) | Phase 1 — Public API hardening | forge-bridge installs and tests pass without projekt-forge in venv; router system prompt has no forge-specific content |
| Execution log path collision (Pitfall 5) | Phase 3 — Learning pipeline integration | Two test processes using separate log paths show independent promotion counts |
| Optional deps transitive conflict (Pitfall 6) | Phase 2 — Rewire projekt-forge | `pip check` passes after installing both repos |
| DB migration risk (Pitfall 7) | Phase 3 — Learning pipeline integration | `alembic history` in forge-bridge shows no projekt-forge revisions; separate migration envs confirmed |
| register_tools() race (Pitfall 8) | Phase 2 — Rewire projekt-forge | Runtime guard raises `RuntimeError` if called after `mcp.run()`; integration test verifies tool appears in `tools/list` |

---

## Sources

- Direct codebase analysis: `forge_bridge/bridge.py`, `forge_bridge/mcp/registry.py`, `forge_bridge/learning/execution_log.py`, `forge_bridge/llm/router.py`, `forge_bridge/store/session.py`
- Direct codebase analysis: `.planning/PROJECT.md` (v1.1 requirements and constraints)
- Direct codebase analysis: `MIGRATION_PLAN.md` (explicit Phase 4-5 rewire plan)
- Python packaging documentation: editable installs, sys.path resolution, optional extras behavior
- Alembic documentation: multiple migration environments, separate Base objects
- Confidence: HIGH for Pitfalls 1-5, 7-8 (direct codebase and design evidence); MEDIUM for Pitfall 6 (inferred from transitive dep patterns)

---
*Pitfalls research for: projekt-forge pip dependency integration and learning pipeline cross-repo wiring*
*Researched: 2026-04-15*
