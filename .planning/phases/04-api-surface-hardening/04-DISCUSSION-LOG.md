# Phase 4: API Surface Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 04-api-surface-hardening
**Areas discussed:** Public API surface scope, LLMRouter config injection, Server lifecycle + post-run guard, SkillSynthesizer shape

---

## Public API surface scope (API-01)

| Option | Description | Selected |
|--------|-------------|----------|
| A. Minimal | Just the 4 names from ROADMAP success criteria: `LLMRouter`, `ExecutionLog`, `register_tools`, `get_mcp` | |
| B. Consumer-oriented | The 4 + `bridge.execute`/`execute_json`/`execute_and_read` + `SkillSynthesizer` + `get_router` + `startup_bridge`/`shutdown_bridge` | ✓ |
| C. Everything | B + re-export all canonical vocabulary types (`Project`, `Shot`, `Registry`, `Role`, `Status`, …) | |

**User's choice:** B
**Notes:** Rationale — Phase 5/6 tell us exactly what projekt-forge will import; exporting those keeps consumer imports short without flattening the canonical vocabulary namespace (which already has its own barrel file at `forge_bridge.core`).

---

## LLMRouter config injection (API-02, PKG-03)

### 2a. Config shape

| Option | Description | Selected |
|--------|-------------|----------|
| A. Individual kwargs + env fallback | `LLMRouter(local_url=None, local_model=None, cloud_model=None, system_prompt=None)` | ✓ |
| B. RouterConfig dataclass | `LLMRouter(config: RouterConfig \| None = None)` | |
| C. Both | kwargs pass-through to an internal dataclass | |

**User's choice:** A (bundled confirm on area 2)

### 2b. Fallback precedence

**Decision:** explicit arg → env var → hardcoded default. Env reads happen inside `__init__` (not at import time).

### 2c. `get_router()` singleton

**Decision:** stays env-only. Ambient zero-config path; consumers wanting injection call `LLMRouter(...)` directly.

### 2d. Generic default system prompt (PKG-03)

| Option | Description | Selected |
|--------|-------------|----------|
| A. Empty default | `system_prompt` defaults to `None`; caller supplies | |
| B. Generic VFX/Flame | Keep Flame 2026, shot-naming, openclip bracket notation, "production-ready Python" tone. Drop all hostnames, project codes, DB creds, machine specs. | ✓ |
| C. Pure minimal | One-liner "VFX pipeline assistant. Concise, production-ready Python." | |

**User's choice:** B
**Notes:** Keeps router useful out of the box for the Flame domain (which is forge-bridge's purpose) while purging every client-specific identifier. projekt-forge overrides with its own enriched prompt in Phase 6.

---

## Server lifecycle + post-run guard (API-04, API-05)

### 3a. `startup_bridge` / `shutdown_bridge` signature

| Option | Description | Selected |
|--------|-------------|----------|
| A. Env-only (just rename) | `async def startup_bridge() -> None` | |
| B. Optional kwargs + env fallback | `async def startup_bridge(server_url=None, client_name=None)` | ✓ |

**User's choice:** B (bundled confirm on area 3)
**Notes:** Matches the LLMRouter injection pattern for consistency.

### 3b. Post-`run()` guard location

| Option | Description | Selected |
|--------|-------------|----------|
| A. Lifespan sets flag | `_server_started = True` inside `_lifespan()` after `startup_bridge()` completes, before `yield` | ✓ |
| B. Wrap `mcp.run()` | Export a `run()` wrapper that sets the flag before delegating | |
| C. Inspect FastMCP internal state | Read some FastMCP attribute on each `register_tools()` call | |

**User's choice:** A
**Notes:** Lifespan is the canonical serving-state boundary we own; fires exactly once. Error message: `RuntimeError("register_tools() cannot be called after the MCP server has started. Register all tools before calling mcp.run().")`

### 3c. Backward-compat shims

**Decision:** Clean break. Rename `_startup` → `startup_bridge`, `_shutdown` → `shutdown_bridge`, update the one call site in `_lifespan()`. No alias. Any test that relied on the private name gets updated in the same commit (planner grep-checks first).

---

## SkillSynthesizer shape (API-03)

| Option | Description | Selected |
|--------|-------------|----------|
| A. Class wrapper | `class SkillSynthesizer` with `__init__(router=None, synthesized_dir=None)` and `async synthesize(...)` method | ✓ |
| B. Kwarg on existing function | Add `router: LLMRouter \| None = None` to module-level `synthesize()` | |
| C. Both | Class exists + module-level `synthesize()` kept as shim | |

**User's choice:** A
**Notes:** Honors the requirement's literal naming. Gives a natural home for Phase 6's `pre_synthesis_hook` (LRN-04) and for injecting `synthesized_dir` in tests. Module-level `synthesize()` is removed — matches the clean-break philosophy from area 3.

---

## Claude's Discretion

- Whether `SkillSynthesizer()` in `bridge.py` is instantiated module-level or per-call.
- Whether to keep module-level `LOCAL_BASE_URL`/`LOCAL_MODEL`/`SYSTEM_PROMPT` constants as named defaults or inline them inside `LLMRouter.__init__`.
- Exact docstring wording on the new public functions.
- Test file organization (new `tests/test_public_api.py` vs. distribute across existing files).
- Exact implementation of `get_mcp()` (function vs. attribute re-export).

---

## Deferred Ideas

- Phase 6's `pre_synthesis_hook` kwarg (LRN-04) — constructor designed to accept it later without breaking shape.
- Phase 6's configurable `ExecutionLog` path and `set_execution_callback()` (LRN-01, LRN-02).
- PyPI publishing — v1.1 uses git-tag or editable install.
- Git tag creation for `1.0.0` — outside phase scope (release workflow owns it).
- Eliminating all module-level env reads across the package — partially addressed; full sweep not in scope.
