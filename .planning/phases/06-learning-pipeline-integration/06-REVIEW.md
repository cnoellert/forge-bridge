---
phase: 06-learning-pipeline-integration
reviewed: 2026-04-17T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - forge_bridge/__init__.py
  - forge_bridge/learning/execution_log.py
  - forge_bridge/learning/synthesizer.py
  - tests/conftest.py
  - tests/test_execution_log.py
  - tests/test_public_api.py
  - tests/test_synthesizer.py
  - pyproject.toml
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-04-17
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 6 lands two additive extension points on the learning pipeline:

1. `ExecutionLog.set_storage_callback()` with a new frozen `ExecutionRecord`
   dataclass delivered after every JSONL append (LRN-02).
2. `SkillSynthesizer.pre_synthesis_hook` with a `PreSynthesisContext` that
   composes additively into the base synthesis prompts (LRN-04).
3. Four new public-API re-exports in `forge_bridge/__init__.py` bringing
   `__all__` from 11 to 15 names, plus a `pyproject.toml` bump to 1.1.0.

Overall the change set is small, well-scoped, and the critical invariants the
prompt asked me to verify all hold:

- **Exception isolation is correct.** Sync callbacks are wrapped in a narrow
  `try/except Exception` that logs at WARNING and returns. Async callbacks are
  scheduled via `asyncio.ensure_future` with a `done_callback` that swallows
  the exception and logs it. Neither path can break the JSONL append.
- **fcntl ordering is correct.** The callback fires after `LOCK_UN` and after
  `fp.flush()`, so bytes are on their way to the OS before any consumer code
  runs. The file object is still open at that instant (the `with` block has
  not yet exited), but that does not affect correctness.
- **Sync/async dispatch detection is done once at registration.** `inspect
  .iscoroutinefunction` is called inside `set_storage_callback` and the
  boolean is cached on `self._storage_callback_is_async`; `record()` does not
  re-inspect per call. Good.
- **Prompt composition is strictly additive.** Base `SYNTH_SYSTEM` is assigned
  to `system_prompt` first and then extended via f-string concatenation;
  neither `ctx.constraints` nor `ctx.extra_context` can replace it. Base
  `SYNTH_PROMPT` is built via `.format(...)` first and few-shot examples are
  prepended, never spliced into or replacing the base template. This matches
  D-11.
- **Hook-failure fallback is correct.** `except Exception` around the await
  resets `ctx` to a fresh `PreSynthesisContext()` and logs; synthesis
  continues with the unmodified base prompts (verified in test
  `test_pre_synthesis_hook_exception_falls_back_to_empty_context`).
- **`.tags.json` sidecar cannot path-traverse.** The sidecar path is derived
  from `output_path.with_suffix(".tags.json")`, and `output_path` is built
  from `fn_name` which comes from `ast.AsyncFunctionDef.name` (a Python
  identifier — only letters, digits, underscores). Consumer-supplied tag
  strings are JSON-encoded into the body, never into the filename.
- **`__all__` matches the declared re-exports.** All 15 named symbols are
  both imported and listed in `__all__`; the test `test_all_contract`
  asserts set-equality and length.

Three Warning-level issues and six Info items follow. No Critical findings.

## Warnings

### WR-01: Async storage-callback failure paths are not test-covered

**File:** `tests/test_execution_log.py`
**Issue:** The prompt specifically asked me to check whether the new tests
exercise failure paths. The **sync** callback failure path is covered
(`test_storage_callback_error_does_not_break_jsonl_write`), but two distinct
**async** failure paths in `ExecutionLog.record()` are not:

1. `execution_log.py:213-219` — the `asyncio.ensure_future(...)` RuntimeError
   branch (async callback scheduled when no event loop is running). This is
   user-reachable if a consumer registers an async callback and then calls
   `record()` from synchronous code.
2. `execution_log.py:52-66` — the `_log_callback_exception` done-callback
   swallowing an exception raised inside an awaited async callback. This is
   the core "async storage offline" resilience guarantee.

The sync-failure test uses `caplog` on the `forge_bridge.learning
.execution_log` logger — the same pattern drops straight into async tests.

**Fix:**
```python
async def test_async_storage_callback_error_is_isolated(tmp_path, caplog):
    import logging, asyncio as _a
    from forge_bridge.learning.execution_log import ExecutionLog

    log = ExecutionLog(log_path=tmp_path / "executions.jsonl")

    async def boom(_rec):
        raise RuntimeError("db offline")

    log.set_storage_callback(boom)

    with caplog.at_level(logging.WARNING,
                         logger="forge_bridge.learning.execution_log"):
        log.record("x = 1")
        await _a.sleep(0)  # let done_callback run

    assert (tmp_path / "executions.jsonl").read_text().strip() != ""
    assert any("storage_callback" in r.message for r in caplog.records)


def test_async_callback_outside_event_loop_is_isolated(tmp_path, caplog):
    import logging
    from unittest.mock import AsyncMock
    from forge_bridge.learning.execution_log import ExecutionLog

    log = ExecutionLog(log_path=tmp_path / "executions.jsonl")
    log.set_storage_callback(AsyncMock())  # async, but we call record() sync

    with caplog.at_level(logging.WARNING,
                         logger="forge_bridge.learning.execution_log"):
        log.record("x = 1")  # no running loop

    assert (tmp_path / "executions.jsonl").read_text().strip() != ""
    assert any("outside event loop" in r.message for r in caplog.records)
```

### WR-02: JSONL schema drift — `ExecutionRecord` only models one of two on-disk shapes

**File:** `forge_bridge/learning/execution_log.py:34-46, 233-248`
**Issue:** The `ExecutionRecord` dataclass docstring claims it "Mirrors the
JSONL on-disk schema exactly", but two different record shapes are written to
the same file:

1. `record()` (line 193-208) writes a 5-field line via `asdict(record)`:
   `{code_hash, raw_code, intent, timestamp, promoted=False}`.
2. `mark_promoted()` (line 236-248) writes a **3-field** line directly:
   `{code_hash, promoted=True, timestamp}` — **no** `raw_code`, **no**
   `intent`.

`_replay()` handles both via the `"raw_code" not in rec` branch at line 164,
so the log itself works. But the field-drift risk the prompt asked about is
real in the opposite direction: if a future change adds a field to
`ExecutionRecord`, the author also has to remember to add it to the
`mark_promoted` dict manually, because `mark_promoted` does **not** build a
record through the dataclass. The docstring contract is misleading.

**Fix:** Either (a) reword the `ExecutionRecord` docstring to say "Mirrors
the normal-execution JSONL line; promotion-only lines are a separate, smaller
shape," or (b) extract a small helper `_write_jsonl_line(self, payload: dict)`
that both paths call and add a short schema note near `LOG_PATH` listing
both shapes. Option (a) is the lower-risk fix.

### WR-03: `conftest.py` `sys.path.insert(0, repo_root)` is the wrong fix location

**File:** `tests/conftest.py:14-18`
**Issue:** The comment explicitly flags this as a "Rule 3 workaround for a
site-packages shadow install," which is exactly the smell the prompt asked
me to flag. Prepending `sys.path` in `conftest.py` papers over the real
problem (an out-of-date editable install or a stale site-packages copy of
`forge_bridge`). Consequences:

1. Anyone running `pytest` from an environment where `forge-bridge` is
   installed normally still exercises the repo sources, not the installed
   wheel — so this hides packaging regressions (e.g. a missing file in
   `[tool.hatch.build] include`).
2. It makes the test suite non-portable: running the same tests against an
   installed wheel (e.g. in CI packaging tests) is no longer possible
   without deleting this block.
3. The correct fix lives in `pyproject.toml`, not in test setup code.

**Fix:** Remove the `sys.path` prepend from `conftest.py`. In
`pyproject.toml`, under `[tool.pytest.ini_options]`, add:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
```
This makes pytest-aware path resolution explicit and documented. Then have
developers run `pip install -e .` to kill any stale shadow install —
`conftest.py` should not be compensating for environment bugs.

## Info

### IN-01: `_json` import alias is unnecessary

**File:** `forge_bridge/learning/synthesizer.py:14`
**Issue:** `import json as _json  # for the tags sidecar write; rename to
avoid shadowing` — but `json` is never shadowed anywhere else in this
module. Nothing is named `json` locally. The alias adds cognitive cost for
no benefit.
**Fix:** `import json` and use `json.dumps(...)` at line 371.

### IN-02: Mixed `Optional[X]` and `X | None` styles in the same module

**File:** `forge_bridge/learning/synthesizer.py:21, 145, 243-245, 258, 260`
**Issue:** The module uses `Optional[str]` / `Optional[Path]` on some
signatures (lines 145, 258, 260) and `LLMRouter | None` / `Path | None` /
`PreSynthesisHook | None` on others (lines 243-245, 253). Given
`from __future__ import annotations` is active and `requires-python = ">=3.10"`,
pick one. PEP 604 (`X | None`) is the modern idiom and matches the rest of
the 3.10+ codebase.
**Fix:** Drop `Optional` from the `typing` import and convert the three
remaining `Optional[...]` usages to `... | None`.

### IN-03: Weak assertion on `PreSynthesisHook` in public-API test

**File:** `tests/test_public_api.py:247-248`
**Issue:** `PreSynthesisHook` is a type alias (`Callable[...]`), so
`PreSynthesisHook is not None` is trivially true at import time. The
assertion adds no coverage beyond "the import did not raise" — which is
already what the preceding import statement verifies.
**Fix:** Either drop the loop over `PreSynthesisHook`, or assert something
load-bearing — e.g. `assert PreSynthesisHook.__origin__ is
collections.abc.Callable` — to actually catch a regression if the alias
ever gets redefined as the wrong thing.

### IN-04: Prompt-composition ordering is not explicitly tested

**File:** `tests/test_synthesizer.py:311-356`
**Issue:** The tests assert that `extra_context` and `constraints` each end
up in the system prompt, but no test asserts the **order** mandated by the
code (constraints block first, extra_context after). If a refactor silently
reorders them, few-shot example ordering (examples **before** base prompt)
has the same gap. These are D-11 invariants — worth a regression test.
**Fix:**
```python
async def test_prompt_composition_order(tmp_path):
    from forge_bridge.learning.synthesizer import PreSynthesisContext, SkillSynthesizer
    async def hook(_i, _p):
        return PreSynthesisContext(
            constraints=["C_MARKER"],
            extra_context="X_MARKER",
            examples=[{"intent": "E_INTENT", "code": "E_CODE"}],
        )
    router = _make_router_mock()
    synth = SkillSynthesizer(router=router, synthesized_dir=tmp_path,
                             pre_synthesis_hook=hook)
    await synth.synthesize(raw_code="x = 1", intent="t", count=3)
    _, kwargs = router.acomplete.await_args
    sys_p, usr_p = kwargs["system"], _[0]
    assert sys_p.index("Constraints:") < sys_p.index("X_MARKER")
    assert usr_p.index("E_CODE") < usr_p.index("This Flame code pattern was")
```

### IN-05: Tags sidecar write path has no test

**File:** `forge_bridge/learning/synthesizer.py:367-371`
**Issue:** The `.tags.json` write path (the whole point of `ctx.tags`
existing in the contract) is not exercised in `tests/test_synthesizer.py`.
No test asserts that non-empty tags produce a sidecar, empty tags produce
no sidecar, and the sidecar body is valid JSON of the declared shape.
**Fix:**
```python
async def test_tags_sidecar_written_when_tags_present(tmp_path):
    import json as _j
    from forge_bridge.learning.synthesizer import PreSynthesisContext, SkillSynthesizer
    async def hook(_i, _p):
        return PreSynthesisContext(tags=["role:rename", "scope:shot"])
    router = _make_router_mock()
    synth = SkillSynthesizer(router=router, synthesized_dir=tmp_path,
                             pre_synthesis_hook=hook)
    out = await synth.synthesize(raw_code="x = 1", intent="t", count=3)
    sidecar = out.with_suffix(".tags.json")
    assert sidecar.exists()
    assert _j.loads(sidecar.read_text()) == {"tags": ["role:rename", "scope:shot"]}

async def test_no_sidecar_when_tags_empty(tmp_path):
    # default PreSynthesisContext(tags=[]) — no sidecar
    ...
```

### IN-06: `test_record_returns_false_after_mark_promoted` uses a brittle accessor

**File:** `tests/test_execution_log.py:96`
**Issue:** `log.mark_promoted(log._counters.copy().popitem()[0])` reaches
into a private dict and relies on it containing exactly one key. It works
today because the test records the same code three times, but the test's
intent ("promote *this* hash") is obscured. The suite already uses the
cleaner pattern two tests down (`test_replay_promoted_does_not_reemit`
line 131) — `_, h = normalize_and_hash("x = 1")` — so this test is just
inconsistent with itself.
**Fix:**
```python
from forge_bridge.learning.execution_log import normalize_and_hash
_, h = normalize_and_hash("x = 1")
log.mark_promoted(h)
```

---

_Reviewed: 2026-04-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
