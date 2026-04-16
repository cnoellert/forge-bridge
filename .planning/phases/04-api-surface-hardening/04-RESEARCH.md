# Phase 4: API Surface Hardening - Research

**Researched:** 2026-04-16
**Domain:** Python packaging, API surface definition, dependency injection refactor
**Confidence:** HIGH

## Phase Summary

Phase 4 is a refactor of an already-shipped v1.0 package to harden its public API ahead of projekt-forge consumption. CONTEXT.md's 22 locked decisions name every file, signature, env var, and renamed symbol — this research deliberately does **not** revisit those. Scope is limited to four narrow areas the planner still needs answered: validation architecture for the success gates, a concrete test-suite impact audit (D-16), and two open Claude's-discretion items (`get_mcp()` shape, `SkillSynthesizer()` instantiation). A secondary surprise surfaced: one extra `portofino` occurrence outside router.py that PKG-03's grep gate would catch — documented under Risks.

## User Constraints (from CONTEXT.md)

Constraints are fully captured in `04-CONTEXT.md`. This research honors D-01 through D-23 as locked. The only items still open per CONTEXT.md §"Claude's Discretion" are addressed in §Open-Question Resolutions below. All other decisions are out-of-scope for research.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | `__all__` in `__init__.py` with all public symbols re-exported | D-01, D-02 lock surface; Validation §A covers import-smoke test |
| API-02 | `LLMRouter` accepts injected `local_url`, `local_model`, `system_prompt` with env fallback | D-05, D-06 lock signature; Validation §B covers no-env-read assertion |
| API-03 | `SkillSynthesizer` accepts optional `router=` | D-17 locks ctor; Open-Question §2 resolves instantiation pattern in `bridge.py` |
| API-04 | `startup_bridge()` and `shutdown_bridge()` public in `mcp/server.py` | D-11-D-13; Validation §D covers rename + symmetric arg shape |
| API-05 | `register_tools()` raises `RuntimeError` after `mcp.run()` via `_server_started` guard | D-14, D-15; Validation §E covers guard trip + message contents |
| PKG-01 | `register_tools(source="builtin")` accepts downstream consumer calls | D-22: already satisfied; Validation §F covers a single regression test |
| PKG-02 | `pyproject.toml` version 0.1.0 → 1.0.0 | D-23; Validation §G is a one-line grep |
| PKG-03 | Forge-specific strings (`portofino`, `assist-01`, `ACM_`) purged from `_DEFAULT_SYSTEM_PROMPT` | D-10; Validation §C covers the grep-zero contract — **see Risk R-1** |

## Validation Architecture

Framework is **pytest with `pytest-asyncio` (`asyncio_mode = "auto"`)** per `pyproject.toml:46-47`. Dev extra: `pytest, pytest-asyncio, ruff`. Existing test infrastructure covers all phase requirements; no Wave 0 scaffolding is required. Below is the Nyquist map — one assertion per decision, sampled at the lowest layer that proves the behavior.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio 1.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = auto) |
| Quick run command | `pytest tests/test_public_api.py tests/test_llm.py tests/test_mcp_registry.py tests/test_synthesizer.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

Recommendation: **create `tests/test_public_api.py`** for the API-01/D-01/D-02 surface and the API-05 guard (these are cross-cutting and don't belong in existing files). Modify `tests/test_llm.py` in-place for API-02/D-05..D-10 (the file already targets router.py). Modify `tests/test_synthesizer.py` in-place for API-03/D-17..D-19. Add a single test to `tests/test_mcp_registry.py` for PKG-01 (the file already owns registry behavior). A version-bump grep test belongs in `test_public_api.py`.

| Req / Decision | Behavior Asserted | Test Type | Location | Command |
|----------------|-------------------|-----------|----------|---------|
| API-01 / D-01, D-02 | `from forge_bridge import LLMRouter, ExecutionLog, register_tools, get_mcp, startup_bridge, shutdown_bridge, SkillSynthesizer, get_router, execute, execute_json, execute_and_read` succeeds | smoke | `tests/test_public_api.py::test_public_api_importable` | quick |
| API-01 / D-02 | `forge_bridge.__all__` set matches the 11-name surface exactly (no extras, no missing) | unit | `tests/test_public_api.py::test_all_contract` | quick |
| API-01 / D-03 | `Project`, `Registry`, `Role` are NOT in `forge_bridge.__all__` (only at `forge_bridge.core`) | unit | `tests/test_public_api.py::test_core_types_not_reexported` | quick |
| API-02 / D-05 | `LLMRouter(local_url=..., local_model=..., cloud_model=..., system_prompt=...)` constructs without error and fields are wired to the attributes used by `_async_local`/`_async_cloud` | unit | `tests/test_llm.py::test_router_accepts_injected_config` | quick |
| API-02 / D-06 | With env vars set, `LLMRouter(local_url="http://injected")` uses the injected value, not the env value | unit | `tests/test_llm.py::test_injected_arg_beats_env` | quick |
| API-02 / D-06 | With no args and env set, `LLMRouter()` reads env inside `__init__` (assert on a fresh instance post-`monkeypatch.setenv`; no module reload needed) | unit | `tests/test_llm.py::test_env_fallback_at_init_time` | quick |
| API-02 / D-06 | With no args and no env, `LLMRouter()` uses the hardcoded defaults | unit | `tests/test_llm.py::test_default_fallback` | quick |
| PKG-03 / D-10 | `grep -r "portofino\|assist-01\|ACM_" forge_bridge/` returns exit 1 (no matches) | integration (subprocess) | `tests/test_public_api.py::test_no_forge_specific_strings` | quick |
| PKG-03 / D-10 | Default system prompt contains the retained markers: `"Flame"`, `"import flame"`, `"{project}_{shot}_{layer}_v{version}"`, `"[0991-1017]"` | unit | `tests/test_llm.py::test_default_prompt_has_generic_flame_context` | quick |
| API-04 / D-11 | `forge_bridge.mcp.server.startup_bridge` and `shutdown_bridge` are defined; `_startup` and `_shutdown` are **not** defined (no alias) | unit | `tests/test_public_api.py::test_lifecycle_renamed_no_alias` | quick |
| API-04 / D-12 | `startup_bridge(server_url="ws://injected")` uses injected URL over env | integration (needs AsyncClient mock) | `tests/test_public_api.py::test_startup_bridge_injection` | quick |
| API-04 / D-13 | `shutdown_bridge()` takes no args and returns `None` (inspect.signature has zero params) | unit | `tests/test_public_api.py::test_shutdown_bridge_signature` | quick |
| API-05 / D-14, D-15 | After setting `forge_bridge.mcp.server._server_started = True`, `register_tools(mcp, [fn], prefix="forge_")` raises `RuntimeError` containing `"cannot be called after the MCP server has started"` | unit | `tests/test_public_api.py::test_register_tools_post_run_guard` | quick |
| API-05 / D-14 | With `_server_started = False` (default), `register_tools(...)` succeeds | unit | `tests/test_public_api.py::test_register_tools_pre_run_ok` | quick |
| PKG-01 / D-22 | `register_tools(mcp, [fn], prefix="forge_", source="builtin")` succeeds and the tool's `_source` metadata is `"builtin"` | unit | `tests/test_mcp_registry.py::test_register_tools_builtin_source` | quick |
| API-03 / D-17 | `SkillSynthesizer(router=mock_router)` stores router; `SkillSynthesizer()` falls back to `get_router()` | unit | `tests/test_synthesizer.py::TestSkillSynthesizer::test_router_injection` | quick |
| API-03 / D-17 | `SkillSynthesizer(synthesized_dir=tmp_path)` overrides the default `SYNTHESIZED_DIR` | unit | `tests/test_synthesizer.py::TestSkillSynthesizer::test_synth_dir_injection` | quick |
| API-03 / D-18 | `await synth.synthesize(raw_code, intent, count)` on the **instance** behaves identically to the existing module-level `synthesize()` (port each of the 6 existing `TestSynthesize` tests to call the method) | unit | `tests/test_synthesizer.py::TestSkillSynthesizer::test_*` | quick |
| API-03 / D-19 | `from forge_bridge.learning.synthesizer import synthesize` raises `ImportError` (the module-level function is gone) | unit | `tests/test_synthesizer.py::test_module_level_synthesize_removed` | quick |
| API-03 / D-20 | `forge_bridge.bridge` imports and constructs `SkillSynthesizer` without error at module load time (catches bad instantiation pattern) | smoke | `tests/test_public_api.py::test_bridge_module_imports_clean` | quick |
| PKG-02 / D-23 | `pyproject.toml` version == "1.0.0" (parse with `tomllib`) | unit | `tests/test_public_api.py::test_package_version` | quick |
| D-16 | (meta — not a runtime assertion; verified by the test-suite audit below passing after refactor) | — | whole test suite green | `pytest -x` |

### Sampling Rate

- **Per task commit:** `pytest tests/test_public_api.py tests/test_llm.py tests/test_mcp_registry.py tests/test_synthesizer.py -x` — covers the 21 decision-level assertions above, should complete in under 10 seconds (no I/O beyond tmp_path, no network).
- **Per wave merge:** `pytest -x` — full suite (existing 2600 lines + new additions) must stay green; this catches collateral damage from the `_startup`/`_shutdown` rename if any test grew a dependency between phases.
- **Phase gate:** Full suite green + the CONTEXT.md §Success Criteria grep command (`grep -r "portofino\|assist-01\|ACM_" forge_bridge/`) must return zero matches before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_public_api.py` — new file (doesn't exist). Covers D-01/D-02/D-03/D-11/D-12/D-13/D-14/D-15/D-20/D-23.
- [ ] No framework install gap — pytest + pytest-asyncio already in `[project.optional-dependencies].dev`.
- [ ] No fixture gap — `conftest.py` already provides `monkeypatch_bridge`, `mock_openai`, `mock_anthropic`; that's enough.

### Nyquist Coverage Check

| Decision | Covered by | Decision | Covered by |
|----------|------------|----------|------------|
| D-01 | test_all_contract | D-13 | test_shutdown_bridge_signature |
| D-02 | test_public_api_importable, test_all_contract | D-14 | test_register_tools_pre_run_ok + _post_run_guard |
| D-03 | test_core_types_not_reexported | D-15 | test_register_tools_post_run_guard (message substring) |
| D-04 | test_public_api_importable (calls get_mcp()) | D-16 | meta — full suite green |
| D-05 | test_router_accepts_injected_config | D-17 | test_router_injection + test_synth_dir_injection |
| D-06 | test_injected_arg_beats_env + test_env_fallback_at_init_time + test_default_fallback | D-18 | TestSkillSynthesizer::test_* (method-form tests) |
| D-07 | covered transitively by test_env_fallback_at_init_time | D-19 | test_module_level_synthesize_removed |
| D-08 | covered by test_default_fallback + (see Risk R-2) | D-20 | test_bridge_module_imports_clean |
| D-09 | not directly tested — acceptable, behavior unchanged from current code | D-21 | not tested — deliberately forward-looking for Phase 6 |
| D-10 | test_no_forge_specific_strings + test_default_prompt_has_generic_flame_context | D-22 | test_register_tools_builtin_source |
| D-11 | test_lifecycle_renamed_no_alias | D-23 | test_package_version |
| D-12 | test_startup_bridge_injection | | |

No decision is untested except D-09, D-21 (deliberate — D-09 is a no-op, D-21 is forward-looking). No redundant tests for the same decision.

## Test-Suite Impact Audit (D-16)

CONTEXT.md §D-16 requires verifying forge-bridge's own test suite does not depend on the private names being removed. Results:

### `_startup` / `_shutdown` references in `tests/`

**Zero hits.** `grep -n "_startup\|_shutdown" tests/` returns nothing. No test in forge-bridge imports or references `forge_bridge.mcp.server._startup` or `_shutdown`. Rename is safe — no test edits required.

### Module-level `synthesize()` function references in `tests/`

Seven test-collection sites call the **module-level** `synthesize` (six test cases in `TestSynthesize`, plus one import for path equality):

| File | Line | Context | Required Edit |
|------|------|---------|---------------|
| `tests/test_synthesizer.py` | 147-148 | `from forge_bridge.learning import synthesizer; monkeypatch.setattr(synthesizer, "SYNTHESIZED_DIR", tmp_path)` | Keep module import; retarget `monkeypatch.setattr` at the class module attribute (still `synthesizer.SYNTHESIZED_DIR`) — **no change needed** to the monkeypatch, only to the call site below |
| `tests/test_synthesizer.py` | 154 | `result = await synthesizer.synthesize("some code", "get shot name", 5)` | Convert to `synth = synthesizer.SkillSynthesizer(); result = await synth.synthesize(...)` |
| `tests/test_synthesizer.py` | 169 | `result = await synthesizer.synthesize("some code", "intent", 3)` | Same |
| `tests/test_synthesizer.py` | 182 | `result = await synthesizer.synthesize("some code", "intent", 3)` | Same |
| `tests/test_synthesizer.py` | 199 | `result = await synthesizer.synthesize("some code", "intent", 3)` | Same |
| `tests/test_synthesizer.py` | 216 | `result = await synthesizer.synthesize("some code", "intent", 3)` | Same |
| `tests/test_synthesizer.py` | 229 | `await synthesizer.synthesize("some code", "intent", 3)` | Same |
| `tests/test_synthesizer.py` | 242 | `from forge_bridge.learning.synthesizer import SYNTHESIZED_DIR as synth_dir` | Unaffected — `SYNTHESIZED_DIR` constant stays |

Action: the six calls in `TestSynthesize` must be migrated to use `SkillSynthesizer().synthesize(...)` in the same commit as D-19's removal (otherwise the test run breaks). This is planner table-stakes — call it out as a rename-coupled edit task.

**Plus:** add one new test `test_module_level_synthesize_removed` (see Validation table) asserting the old entry point is gone.

### Module-level constant references in `tests/` (D-08 test impact)

`tests/test_llm.py:65-78` (the `test_env_var_override` test) asserts on `router_mod.LOCAL_BASE_URL`, `router_mod.LOCAL_MODEL`, `router_mod.CLOUD_MODEL`, `router_mod.SYSTEM_PROMPT`:

```python
# tests/test_llm.py:65-78
monkeypatch.setenv("FORGE_LOCAL_LLM_URL", "http://test-host:11434/v1")
monkeypatch.setenv("FORGE_LOCAL_MODEL", "test-local-model")
monkeypatch.setenv("FORGE_CLOUD_MODEL", "test-cloud-model")
monkeypatch.setenv("FORGE_SYSTEM_PROMPT", "Custom system prompt")

import importlib
import forge_bridge.llm.router as router_mod
importlib.reload(router_mod)

assert router_mod.LOCAL_BASE_URL == "http://test-host:11434/v1"
assert router_mod.LOCAL_MODEL == "test-local-model"
assert router_mod.CLOUD_MODEL == "test-cloud-model"
assert router_mod.SYSTEM_PROMPT == "Custom system prompt"
```

This test is **directly contradicted by D-06**: "Env reads happen inside `__init__` (not at module import time)." After D-06 lands, `importlib.reload(router_mod)` is no longer the right mechanism — the env vars are read per-instance.

**Action:** `test_env_var_override` must be rewritten as `test_env_fallback_at_init_time` (see Validation table above) — assert on a fresh `LLMRouter()` instance's attributes after `monkeypatch.setenv`, not on module-level constants. The new shape looks like:

```python
def test_env_fallback_at_init_time(monkeypatch):
    monkeypatch.setenv("FORGE_LOCAL_LLM_URL", "http://test-host:11434/v1")
    monkeypatch.setenv("FORGE_LOCAL_MODEL", "test-local-model")
    # ...
    from forge_bridge.llm.router import LLMRouter
    router = LLMRouter()
    assert router.local_url == "http://test-host:11434/v1"
    assert router.local_model == "test-local-model"
    # ...
```

Whether `LOCAL_BASE_URL` et al. survive as module-level constants (D-08's open choice) does not affect this test — the test should target instance attributes, not module constants.

### Tests that patch/mock env vars at module level

Same answer: only `tests/test_llm.py::test_env_var_override` depends on module-level constant behavior. `tests/test_llm.py::test_optional_import_guard` (lines 81-112) manipulates `sys.modules` to hide `openai`/`anthropic` — that test is unaffected by D-06 because the lazy-import pattern inside `_get_local_client`/`_get_cloud_client` is preserved (CONTEXT.md §"Reusable Assets" confirms).

### `set_execution_callback` tests

`tests/test_execution_log.py:175-217` covers `set_execution_callback()` — **unaffected** by Phase 4. `set_execution_callback` is not renamed, is already public, and is not in the D-02 export list for Phase 4 (deferred to Phase 6 per LRN-02). These tests stay as-is.

### Summary

- **`_startup`/`_shutdown` rename:** zero test-code impact.
- **Module-level `synthesize` removal:** six call-site edits in `tests/test_synthesizer.py`, all co-located in `TestSynthesize`, all mechanical.
- **Module-level constants:** one test (`test_env_var_override`) must be rewritten to assert on instance attributes — this is a direct consequence of D-06 and cannot be avoided by keeping the constants.
- **No other test-code impact.**

## Open-Question Resolutions

### 1. `get_mcp()` shape (D-04)

**Current code** (`forge_bridge/mcp/__init__.py:7-9`):
```python
def get_mcp():
    """Return the FastMCP server instance for tool registration."""
    return _mcp
```

**Already exists as a one-line function.** The existing implementation is correct and satisfies D-04 verbatim — returns the module-level `mcp` singleton from `server.py`. No lazy construction is needed because `mcp` is constructed at module load in `server.py:92-100` and `register_builtins(mcp)` runs at import time on line 103. By the time any consumer calls `get_mcp()`, the server is fully wired.

**Recommendation:** keep it exactly as-is but promote to the Phase 4 public surface by adding to D-02's root `__all__`. The existing `forge_bridge/mcp/__init__.py` already exports it — Phase 4 work for `get_mcp` is a one-line re-export in `forge_bridge/__init__.py`:

```python
# forge_bridge/__init__.py
from forge_bridge.mcp import get_mcp, register_tools
```

Adding a type annotation to match D-02's shape (and quiet Phase 5's type checkers) is a free improvement:

```python
# forge_bridge/mcp/__init__.py — recommended form
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from forge_bridge.mcp.registry import register_tools
from forge_bridge.mcp.server import mcp as _mcp


def get_mcp() -> FastMCP:
    """Return the FastMCP server instance for tool registration."""
    return _mcp


__all__ = ["register_tools", "get_mcp"]
```

Do not use a lambda (lambdas lack docstrings). Do not use `from ... import mcp as get_mcp` — `get_mcp` must be callable, not an attribute (CONTEXT.md §"Claude's Discretion" bullet 5 confirms the module-attribute rebind won't work). The one-line function is the right shape.

### 2. `SkillSynthesizer()` instantiation in `bridge.py` (D-20)

**Critical finding: there is no current call site for `synthesize()` in `forge_bridge/bridge.py`.** A grep of `forge_bridge/` returns zero calls to `synthesize(` outside its own definition. The function is only referenced by tests.

This means CONTEXT.md's D-20 ("Update the call site in `forge_bridge/bridge.py` (promotion hook)") is describing a call site that does not yet exist — Phase 4 must either (a) introduce the call site as part of this phase, or (b) clarify that no such call site is needed because the wiring lands later (Phase 6). The promotion hook described in CONTEXT.md §"Integration Points" ("`_lifespan()` in `mcp/server.py` — the one place the `_server_started` flag transitions") is separate from the synthesis-promotion hook.

**Recommendation for planner:** treat D-20 as **code that introduces the call site** — specifically, the promotion hook that connects `ExecutionLog.record()`'s return-`True`-at-threshold signal to a `SkillSynthesizer().synthesize(...)` call. This has never been wired (there's an existing `set_execution_callback` hook, but no component calls it from within the package). Raise this as a deviation before planning, or scope D-20 narrowly as "if a call site exists at planning time, update it; otherwise defer to Phase 6."

Given that caveat, **if a call site is introduced in Phase 4**, use the **module-level singleton pattern**:

```python
# forge_bridge/bridge.py — proposed
from forge_bridge.learning.synthesizer import SkillSynthesizer

_synthesizer: SkillSynthesizer | None = None


def _get_synthesizer() -> SkillSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = SkillSynthesizer()
    return _synthesizer
```

**Rationale for module-level singleton:**

1. **Matches existing pattern** — `bridge.py` already uses `@dataclass(frozen=True) _config = _BridgeConfig(...)` and `_on_execution_callback: Optional[Callable] = None` as module-level state (lines 33-45). A singleton synthesizer is consistent with this file's conventions.
2. **Matches `get_router()` pattern** — `LLMRouter` itself uses lazy singleton construction via `get_router()` (`router.py:250-258`). Mirroring that in `SkillSynthesizer` keeps the codebase's "convenience singleton" pattern consistent.
3. **Low state cost** — `SkillSynthesizer.__init__` does one attribute assignment (the router, if injected) and one path resolution (`synthesized_dir or SYNTHESIZED_DIR`). Per-call construction is cheap but pointless; the object has no meaningful per-instance mutable state beyond the router reference.
4. **Hook context** — promotion fires ~1-3 times per session, not hundreds. The difference between per-call and singleton is negligible runtime but meaningful readability.

Use lazy `_get_synthesizer()` (not eager module-level `_synthesizer = SkillSynthesizer()`) so that the `bridge.py` import doesn't force `forge_bridge.learning.synthesizer` to load for consumers who only use `execute()`.

If the planner concludes D-20 should not introduce a call site at all, `SkillSynthesizer` is still exported per D-17/D-02 and Phase 6 can wire it.

## Risks / Gotchas

### R-1. PKG-03 grep gate catches `portofino` in `tools/publish.py`

**Severity: HIGH — blocks success criterion #5.**

Grep of the full `forge_bridge/` tree (excluding `__pycache__`) shows `portofino` appears in **two** files, not one:

```
forge_bridge/llm/router.py:41,57,58  (the _DEFAULT_SYSTEM_PROMPT strings — D-10 covers these)
forge_bridge/tools/publish.py:66     (default="/mnt/portofino" — D-10 does NOT cover this)
```

The grep command in CONTEXT.md §Success Criteria #5 (`grep -r "portofino\|assist-01\|ACM_" forge_bridge/`) will find the `publish.py` hit and fail the phase gate even after D-10 is complete.

`publish.py:60-68` sets a Pydantic Field default for `output_directory`. This is a runtime config default (an installation-specific mount path), not a prompt string. Three options:

1. **Generic default**: change to `default="/tmp/publish"` or similar placeholder, document in the field description that users should override. Cleanest from the "zero forge-specific strings" contract.
2. **Env-var read**: change to `default_factory=lambda: os.environ.get("FORGE_PUBLISH_ROOT", "/tmp/publish")`. Matches the D-06 pattern for router env reads.
3. **Remove default, make required**: `default=...` (Ellipsis) or `default=None` with `Optional[str]` and a runtime check. Forces downstream callers to supply the path.

**Recommendation:** option 2 (env-var with generic fallback) — keeps backward compatibility for current deployments, scrubs the hardcoded hostname, matches the existing env-var pattern established elsewhere in the codebase.

**Planner action:** add a task to Phase 4 that generalizes `publish.py:66` alongside the D-10 router prompt scrub. Without this, success criterion #5 will not pass. This is a deviation from CONTEXT.md's scope — raise it in plan review.

### R-2. D-08 "module-level constants" choice affects `test_env_var_override` either way

The existing `test_env_var_override` test in `test_llm.py:62-78` asserts on `router_mod.LOCAL_BASE_URL`, `LOCAL_MODEL`, `CLOUD_MODEL`, `SYSTEM_PROMPT` after `importlib.reload`. Regardless of whether D-08 **keeps** the module-level constants (as named defaults) or **removes** them, this test's semantics change:

- **If kept**: the constants become static literals (e.g. `LOCAL_BASE_URL = "http://localhost:11434/v1"`). Env vars no longer influence them. The test assertions still reference the constants but will fail because env-setting no longer changes them.
- **If removed**: the test fails at import (`AttributeError`).

Either way, the test must be rewritten to target instance attributes (see "Test-Suite Impact Audit" above). D-08's choice does not change this test's required edit.

**Recommendation:** D-08 should **remove** the module-level constants entirely and inline the defaults inside `LLMRouter.__init__`. Rationale:

- Nothing outside `llm/router.py` imports `LOCAL_BASE_URL`/`LOCAL_MODEL`/`CLOUD_MODEL`/`SYSTEM_PROMPT` (verified: `grep -rn "LOCAL_BASE_URL\|CLOUD_MODEL" forge_bridge/` returns only `router.py` itself).
- After D-06, nothing should read env at module load time, so the constants serve no purpose as env-backed globals.
- Having hardcoded literals at module scope under names like `SYSTEM_PROMPT` invites accidental import (consumers assuming they're the canonical default) — the same class of mistake the phase is trying to prevent.

### R-3. D-19 clean-break timing must be atomic with test migration

CONTEXT.md §"Specifics" says "when a name becomes public, the old private name goes away (no aliases, no shims)." D-19 removes the module-level `async def synthesize(...)`. The seven existing test call sites (see audit above) **must** be migrated in the same commit/task as the removal — otherwise the quick-run test suite breaks between tasks and violates the Nyquist gate's per-task-commit sampling rate.

**Planner action:** structure D-17/D-18/D-19 + test migration as **one task**, not three. Partial completion is a broken intermediate state.

### R-4. `register_tools(source="builtin")` existing-signature verification

CONTEXT.md §D-22 states "No code change required; planner verifies with a test that passes `source="builtin"` from an external call site." Confirmed: `forge_bridge/mcp/registry.py:75-101` already accepts `source: str = "user-taught"` as a kwarg, and `_validate_name` at line 33-49 only gates the `synth_*` prefix on `source != "synthesized"` — it does **not** restrict `source="builtin"` from external callers. PKG-01 is satisfied by current code; one new test closes the loop.

The test should live in `tests/test_mcp_registry.py` (consistent with MCP-05 test already at `test_mcp_registry.py:8-9`) and assert both that the call succeeds and that the resulting tool's `meta["_source"]` is `"builtin"` (confirming `register_tool:72` forwards the source tag correctly).

### R-5. `_server_started` flag import path (D-14 / D-15)

D-14 places `_server_started: bool = False` at module scope in `forge_bridge/mcp/server.py`. D-15 has `register_tools()` in `forge_bridge/mcp/registry.py` import and read it. This crosses the `server.py` → `registry.py` module boundary in a direction that **does not exist today** (`server.py:42` imports from `registry.py`, not the other way around).

Reading `_server_started` from `registry.py` requires `from forge_bridge.mcp import server` inside `register_tools()` — if done at module top, it creates a circular import (`server.py` imports `registry.py` which imports `server.py`).

**Recommendation:** do the import lazily **inside** `register_tools()`:

```python
# forge_bridge/mcp/registry.py
def register_tools(mcp, fns, prefix="", source="user-taught"):
    from forge_bridge.mcp.server import _server_started  # lazy to avoid circular import
    if _server_started:
        raise RuntimeError(
            "register_tools() cannot be called after the MCP server has started. "
            "Register all tools before calling mcp.run()."
        )
    for fn in fns:
        # ... existing body
```

Reading `_server_started` inside the function captures the **current value at call time** (not a stale import-time snapshot), which is exactly the semantics D-14/D-15 need.

**Gotcha:** `from forge_bridge.mcp.server import _server_started` binds to the **name at module**, and Python `from ... import name` captures the value, not a reference. If someone later does `server._server_started = True`, other modules that already did `from server import _server_started` keep their stale `False`. The lazy import above avoids this because it re-imports on every call. Alternative: `import forge_bridge.mcp.server as _server; if _server._server_started: raise ...` — equivalent correctness, slightly more readable.

## Sources

### Primary (HIGH confidence)

- Direct code read: `forge_bridge/__init__.py`, `forge_bridge/llm/router.py`, `forge_bridge/mcp/server.py`, `forge_bridge/mcp/registry.py`, `forge_bridge/mcp/__init__.py`, `forge_bridge/learning/synthesizer.py`, `forge_bridge/learning/execution_log.py`, `forge_bridge/bridge.py`, `pyproject.toml` (all files at HEAD as of 2026-04-16)
- Direct read of all tests in `tests/` — 11 files, 2661 lines total
- `.planning/phases/04-api-surface-hardening/04-CONTEXT.md` (22 locked decisions)
- `.planning/REQUIREMENTS.md` (API-01..05, PKG-01..03 definitions)
- `.planning/config.json` (confirms `nyquist_validation: true`)
- Grep audit: `grep -rn "portofino\|assist-01\|ACM_\|flame-01" forge_bridge/` and `grep -rn "_startup\|_shutdown\|synthesize" tests/`

### Secondary

- CLAUDE.md (project instructions — confirms middleware philosophy and stability contract)

---

**Confidence breakdown:**

- Validation Architecture: HIGH — all assertions target code that exists or will exist per locked decisions; test infrastructure already in place.
- Test-Suite Impact: HIGH — based on direct grep of current tests with file:line precision.
- Open-question resolutions: HIGH for `get_mcp` (trivial), MEDIUM-HIGH for `SkillSynthesizer` instantiation (recommendation depends on whether D-20 introduces the call site — see R in that section).
- Risks R-1 to R-5: HIGH — each backed by direct code evidence. R-1 is a material scope question for plan review.

*Research complete — 2026-04-16*
