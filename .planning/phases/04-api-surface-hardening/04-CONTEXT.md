# Phase 4: API Surface Hardening - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Declare forge-bridge's stable public API so projekt-forge can consume it as a pip package. Scope: rename private names to public, make `LLMRouter` and `SkillSynthesizer` accept injected config, generic the system prompt, add a post-`run()` guard to `register_tools()`, bump package version to `1.0.0`.

Out of scope: projekt-forge-side changes (Phase 5), learning pipeline integration into forge's infrastructure (Phase 6), PyPI publishing (deferred — git-tag or editable install in v1.1).

</domain>

<decisions>
## Implementation Decisions

### Public API surface (API-01)

- **D-01:** `forge_bridge/__init__.py` declares `__all__` with a **consumer-oriented** surface — covers everything projekt-forge will import across Phases 5 and 6, nothing broader.
- **D-02:** Exported names at package root:
  - `LLMRouter`, `get_router` (from `forge_bridge.llm.router`)
  - `ExecutionLog` (from `forge_bridge.learning.execution_log`)
  - `SkillSynthesizer` (from `forge_bridge.learning.synthesizer`)
  - `register_tools`, `get_mcp` (from `forge_bridge.mcp`)
  - `startup_bridge`, `shutdown_bridge` (from `forge_bridge.mcp.server`)
  - `execute`, `execute_json`, `execute_and_read` (from `forge_bridge.bridge`)
- **D-03:** Canonical vocabulary types (`Project`, `Shot`, `Registry`, `Role`, `Status`, etc.) are **not** re-exported at the root. They remain addressable via `forge_bridge.core` (which already has its own barrel file).
- **D-04:** `get_mcp()` returns the existing module-level `mcp` singleton from `forge_bridge/mcp/server.py` — consumers get the same instance that `mcp.run()` will serve.

### LLMRouter configuration injection (API-02, PKG-03)

- **D-05:** `LLMRouter.__init__` signature becomes:
  ```python
  LLMRouter(
      local_url: str | None = None,
      local_model: str | None = None,
      cloud_model: str | None = None,
      system_prompt: str | None = None,
  )
  ```
- **D-06:** Per-arg fallback precedence: **explicit arg → env var → hardcoded default.** Env reads happen inside `__init__` (not at module import time) so late env changes still affect fresh instances.
- **D-07:** Env vars preserved (backward compat for deployment scripts): `FORGE_LOCAL_LLM_URL`, `FORGE_LOCAL_MODEL`, `FORGE_CLOUD_MODEL`, `FORGE_SYSTEM_PROMPT`.
- **D-08:** Module-level constants (`LOCAL_BASE_URL`, `LOCAL_MODEL`, `CLOUD_MODEL`, `SYSTEM_PROMPT`) either become the hardcoded defaults used inside `__init__`, or are removed entirely — planner decides based on test impact. Nothing should read them at import time after this phase.
- **D-09:** `get_router()` singleton **stays env-only** — it is the zero-config ambient path. Consumers that want injected config call `LLMRouter(...)` directly (projekt-forge will do this in Phase 6).
- **D-10:** Generic default system prompt replaces `_DEFAULT_SYSTEM_PROMPT`. Keeps: Flame version, `import flame` note, shot-naming convention `{project}_{shot}_{layer}_v{version}`, openclip bracket notation `[0991-1017]` vs. `%04d`, "concise, production-ready Python" tone. Purges: `portofino`, `assist-01`, `ACM_`, `flame-01`, Backburner/cmdjob, DB credentials, hostnames, machine specs. Must pass `grep -r "portofino\|assist-01\|ACM_" forge_bridge/` with zero matches.

### Server lifecycle + post-run guard (API-04, API-05)

- **D-11:** Rename `_startup()` → `startup_bridge()`, `_shutdown()` → `shutdown_bridge()` in `forge_bridge/mcp/server.py`. Clean rename, **no backward-compat alias**.
- **D-12:** `startup_bridge(server_url: str | None = None, client_name: str | None = None) -> None` uses same arg → env → default pattern as `LLMRouter` (env keys: `FORGE_BRIDGE_URL`, `FORGE_MCP_CLIENT_NAME`).
- **D-13:** `shutdown_bridge() -> None` takes no args — symmetrical with `startup_bridge` but no config needed for teardown.
- **D-14:** Post-`run()` guard: module-level `_server_started: bool = False` in `forge_bridge/mcp/server.py`. `_lifespan()` sets it to `True` after `startup_bridge()` completes and before `yield`.
- **D-15:** `register_tools()` in `forge_bridge/mcp/registry.py` reads `_server_started` (import from server module) and raises:
  ```
  RuntimeError("register_tools() cannot be called after the MCP server has started. Register all tools before calling mcp.run().")
  ```
- **D-16:** Planner must grep forge-bridge's own test suite for uses of `_startup`/`_shutdown` before renaming; any hits get updated in the same commit as the rename.

### SkillSynthesizer class (API-03)

- **D-17:** Introduce `class SkillSynthesizer` in `forge_bridge/learning/synthesizer.py`. Constructor:
  ```python
  SkillSynthesizer(
      router: LLMRouter | None = None,
      synthesized_dir: Path | None = None,
  )
  ```
  `router=None` falls back to `get_router()`. `synthesized_dir=None` uses the existing `SYNTHESIZED_DIR` constant from `forge_bridge.learning.watcher`.
- **D-18:** `async synthesize(self, raw_code, intent, count) -> Path | None` becomes an instance method. Logic identical to the current module-level function.
- **D-19:** The module-level `async def synthesize(...)` function is **removed** — clean break, matches the rename philosophy in D-11.
- **D-20:** Update the call site in `forge_bridge/bridge.py` (promotion hook): construct `SkillSynthesizer()` once at module level (or per-call — planner decides) and invoke `await synthesizer.synthesize(...)`.
- **D-21:** Constructor is extensible: Phase 6's `pre_synthesis_hook` (LRN-04) will land as a new kwarg (`pre_synthesis_hook: Callable | None = None`) without breaking this shape — not implemented in Phase 4.

### Registry & Packaging (PKG-01, PKG-02)

- **D-22:** `register_tools()` already accepts arbitrary `source` strings (`source="user-taught"` default) — PKG-01's "`source="builtin"` from downstream consumers" is satisfied by the existing signature. No code change required; planner verifies with a test that passes `source="builtin"` from an external call site.
- **D-23:** Bump `pyproject.toml` version `0.1.0` → `1.0.0` in this phase. Git tag is deferred — no PyPI publish, projekt-forge will pick up via git dependency or editable install during v1.1.

### Claude's Discretion

- Whether `SkillSynthesizer()` in `bridge.py` is module-level or per-call — planner picks based on state/cost.
- Whether to keep module-level `LOCAL_BASE_URL`/`LOCAL_MODEL`/`SYSTEM_PROMPT` constants as named defaults or inline them in `LLMRouter.__init__` (D-08).
- Exact wording of docstrings on the new public functions.
- Test structure (new `tests/test_public_api.py` vs. distribute across existing test files).
- Whether `get_mcp()` is a function or a simple module-level re-export (`from forge_bridge.mcp.server import mcp as get_mcp` won't work — it needs to be a callable; planner decides between a trivial lambda, a one-line function, or a direct attribute export if naming allows).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements

- `.planning/ROADMAP.md` §Phase 4 — Phase goal, depends-on, requirements list, 5 success criteria
- `.planning/REQUIREMENTS.md` §API Surface — API-01 through API-05 definitions
- `.planning/REQUIREMENTS.md` §Registry & Packaging — PKG-01, PKG-02, PKG-03 definitions
- `.planning/PROJECT.md` §Constraints — backward-compat, standalone independence, optional LLM deps, Python 3.10+

### Current source to refactor

- `forge_bridge/__init__.py` — currently empty docstring only; destination for `__all__` and re-exports
- `forge_bridge/llm/router.py` — `LLMRouter` class, `_DEFAULT_SYSTEM_PROMPT`, `get_router()` singleton, env-var module constants
- `forge_bridge/mcp/server.py` — `_startup`/`_shutdown` to rename; `_lifespan` where `_server_started` flag gets set; `mcp` singleton that `get_mcp()` returns
- `forge_bridge/mcp/registry.py` — `register_tools()` that needs the post-run guard
- `forge_bridge/learning/synthesizer.py` — module-level `synthesize()` to promote into `SkillSynthesizer` class
- `forge_bridge/learning/execution_log.py` — `ExecutionLog` class (re-export; no code change in this phase)
- `forge_bridge/bridge.py` — `execute`/`execute_json`/`execute_and_read` (re-export) and the promotion-hook call site that updates to use `SkillSynthesizer`
- `pyproject.toml` — version bump 0.1.0 → 1.0.0

### Codebase conventions

- `.planning/codebase/CONVENTIONS.md` — ruff config, 100-char lines, Python 3.10+ `|` union syntax, `from __future__ import annotations`, explicit `__init__.py` re-exports as public API
- `.planning/codebase/STRUCTURE.md` §"Where to Add New Code" — module layout reference (note: file was written 2026-04-14, before v1.0 shipped; `llm/`, `learning/`, rebuilt `mcp/` exist in current tree but aren't in that doc)

### Blockers to resolve during research

- `.planning/STATE.md` §Blockers/Concerns — "mcp/server.py lifespan refactor: promoting `_startup`/`_shutdown` to public requires confirming forge-bridge's own test suite does not depend on the private names before Phase 4 planning" (covered by D-16)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `forge_bridge/mcp/registry.py::register_tools()` — already has correct signature `(mcp, fns, prefix, source)`; only needs the run-guard added. PKG-01 already satisfied.
- `forge_bridge/mcp/server.py::mcp` — FastMCP singleton constructed at module load with `lifespan=_lifespan`; `get_mcp()` returns this.
- `forge_bridge/llm/router.py::LLMRouter` — class structure is fine; only `__init__` signature and the `_DEFAULT_SYSTEM_PROMPT` constant change.
- `forge_bridge/learning/synthesizer.py::synthesize()` — current function body is the template for `SkillSynthesizer.synthesize`; lift into a class method, replace `from forge_bridge.llm.router import get_router` with `self._router`.
- `forge_bridge/learning/watcher.py::SYNTHESIZED_DIR` — existing default for the new `synthesized_dir` constructor kwarg.

### Established Patterns

- **Env-var config with module-level constants** — currently read at import time in `router.py` and `server.py`. This phase moves env reads inside `__init__` / `startup_bridge()` so injected args can override.
- **Lazy imports for optional deps** (openai, anthropic) — preserved; `LLMRouter._get_local_client`/`_get_cloud_client` already do this correctly.
- **Namespace enforcement on tool names** — `register_tool()` validates `flame_/forge_/synth_` prefixes; applies equally to downstream `register_tools(source="builtin")` calls.
- **`_` prefix = private** — convention across the codebase; anything renamed to public drops the underscore and gets documented.

### Integration Points

- `forge_bridge/__init__.py` — single touch point for the public surface; every consumer will import from here after Phase 5.
- `forge_bridge/bridge.py` promotion hook — only call site of the old `synthesize()` function; updates once when `SkillSynthesizer` lands.
- `_lifespan()` in `mcp/server.py` — the one place the `_server_started` flag transitions `False → True`.

### Downstream awareness

- Phase 5 will `import forge_bridge` and rely on exactly the names in D-02. Anything missing from `__all__` forces projekt-forge into long import paths or breaks the rewire.
- Phase 6 will construct `LLMRouter(local_url=..., local_model=..., system_prompt=...)` from `forge_config.yaml` values and inject into `SkillSynthesizer(router=...)`. The kwarg shape in D-05 and D-17 is what enables this.

</code_context>

<specifics>
## Specific Ideas

- Clean-break refactor philosophy: when a name becomes public, the old private name goes away (no aliases, no shims). Confirmed for `_startup`/`_shutdown` (D-11), the module-level `synthesize()` function (D-19), and any test that relied on private names (D-16). If backward-compat pressure shows up during research, raise it as a deviation — don't quietly add shims.
- Consistency of injection pattern across the three public constructors/entry points: `LLMRouter`, `SkillSynthesizer`, `startup_bridge`. All use the same "kwarg with env-var fallback; None → env → default" shape so consumers learn it once.
- The generic-Flame default prompt (D-10) is still useful out of the box for bare `LLMRouter()` calls — it's not empty. projekt-forge will override via constructor in Phase 6; the default exists for the standalone-bridge path.

</specifics>

<deferred>
## Deferred Ideas

- Phase 6's `pre_synthesis_hook` kwarg on `SkillSynthesizer.__init__` (LRN-04) — deliberately not implemented in Phase 4; the constructor is designed to accept it later without breaking the shape (D-21).
- Phase 6's `set_execution_callback()` on `ExecutionLog` (LRN-02) and configurable log path (LRN-01) — `ExecutionLog` is only re-exported in Phase 4; behavior changes land in Phase 6.
- PyPI publishing — deferred per REQUIREMENTS.md. v1.1 uses git-tag or editable install.
- Git tag for `1.0.0` — version bump in `pyproject.toml` in this phase, but tag creation is outside phase scope (ship/release workflow decides).
- Eliminating module-level env reads entirely — partially addressed here (moved inside `__init__`/`startup_bridge`), but any remaining module-level env reads elsewhere in the package are not in scope.

</deferred>

---

*Phase: 04-api-surface-hardening*
*Context gathered: 2026-04-16*
