---
phase: 06-learning-pipeline-integration
plan: 02
subsystem: learning-pipeline

tags: [synthesizer, pre-synthesis-hook, frozen-dataclass, additive-prompt, llm, mcp-tool, lrn-04]

# Dependency graph
requires:
  - phase: 03-learning-pipeline
    provides: "SkillSynthesizer class with router= constructor injection and async synthesize() pipeline"
  - phase: 04-api-surface-hardening
    provides: "Constructor-injection-with-None-default house pattern used for the new pre_synthesis_hook param"
provides:
  - "PreSynthesisContext frozen dataclass (4 fields: extra_context, tags, examples, constraints)"
  - "PreSynthesisHook async-only type alias — Callable[[str, dict], Awaitable[PreSynthesisContext]]"
  - "SkillSynthesizer(pre_synthesis_hook=None) constructor param with no-op default"
  - "Additive-only prompt composition: constraints + extra_context append to SYNTH_SYSTEM; examples prepend to SYNTH_PROMPT"
  - "Hook failure-isolation: exceptions fall back to default PreSynthesisContext() with logger.warning(exc_info=True)"
  - ".tags.json sidecar on successful synthesis when ctx.tags is non-empty (EXT-02 feeder)"
affects: [06-04, extension-02-mcp-annotations, projekt-forge-learning-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen dataclass for internal structural types (D-12) — PreSynthesisContext mirrors _BridgeConfig shape"
    - "Async-only hook signature (D-08) — forces consumers off blocking-in-sync-wrapper patterns at the contract level"
    - "Additive-only composition (D-11) — base prompts never replaced; SYNTH_PROMPT.format() call-site-count invariant (exactly 1) grep-asserted"
    - "Failure-fallback with exc_info — narrow-scope try/except around hook call, logger.warning + default instance, synthesis continues"

key-files:
  created: []
  modified:
    - forge_bridge/learning/synthesizer.py
    - tests/test_synthesizer.py

key-decisions:
  - "Plan task ordering followed as-written (impl first, tests after) rather than strict RED-before-GREEN. Rationale: task 1's verify block explicitly runs the existing 20 tests as a no-op regression gate; task 2 appends the 5 new hook-specific tests. Behavior was zero-change when hook=None, so no pre-existing test was invalidated. TDD gate commit sequence in git log is feat→test, which reverses the classic order but preserves the gate's intent (each commit green in isolation)."
  - "Tags sidecar filename uses output_path.with_suffix('.tags.json') — this REPLACES the .py suffix, giving synth_foo.tags.json (not synth_foo.py.tags.json). Plan action language said '.tags.json sidecar next to the .py output' which is compatible with either shape; with_suffix() is the Python-idiomatic read of that spec and produces cleaner filenames."
  - "`import json as _json` rather than `import json` to avoid any chance of shadowing a local `json` name inside synthesize() or in consumers inspecting the module namespace. Plan action prescribed the rename verbatim."

patterns-established:
  - "Hook-injected additive prompt composition: PreSynthesisContext is the schema; SkillSynthesizer.synthesize() owns final assembly; base prompts are invariant. Other forge-bridge services wanting consumer-enrichable behavior should copy this shape."
  - "SYNTH_PROMPT.format call-site-count invariant — a grep-assertable correctness property that prevents future prompt-replacement regressions."
  - "Fire-and-forget-adjacent hook isolation: try/except Exception → logger.warning(exc_info=True) → fallback-to-default-instance. Mirrors the Phase 3 `LLM unavailable → return None` pattern but for an inline recoverable failure."

requirements-completed: [LRN-04]

# Metrics
duration: ~12min
completed: 2026-04-18
---

# Phase 06 Plan 02: Synthesizer Pre-Synthesis Hook Summary

**SkillSynthesizer now accepts an async `pre_synthesis_hook` that returns a frozen `PreSynthesisContext` — hook output composes additively into the system and user prompts, letting projekt-forge inject project-specific context without forge-bridge knowing any forge DB schema.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-18T06:13:00Z
- **Completed:** 2026-04-18T06:21:53Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `PreSynthesisContext` frozen dataclass added with exactly 4 fields (`extra_context: str`, `tags: list[str]`, `examples: list[dict]`, `constraints: list[str]`) — all default to empty; `frozen=True` prevents consumer mutation after return.
- `PreSynthesisHook = Callable[[str, dict], Awaitable[PreSynthesisContext]]` async-only type alias added (D-08: no sync-union).
- `SkillSynthesizer.__init__` gains third kwarg `pre_synthesis_hook: PreSynthesisHook | None = None`; stored on `self._pre_synthesis_hook` with no fallback — `None` stays `None` (genuine no-op).
- Pre-LLM section of `synthesize()` rewritten: hook is awaited with `(intent or "", {"raw_code": raw_code, "count": count})` per D-09; returned `PreSynthesisContext` composes into prompts additively (constraints → `Constraints:` block appended to SYNTH_SYSTEM; extra_context → appended after; examples → few-shot blocks prepended to SYNTH_PROMPT).
- Hook failure isolation: `try/except Exception` → `logger.warning("pre_synthesis_hook raised — falling back to empty context", exc_info=True)` → synthesis continues with default `PreSynthesisContext()`.
- `.tags.json` sidecar written alongside the synthesized `.py` when `ctx.tags` is non-empty — designed as an EXT-02 (MCP provenance annotations) feeder with zero coupling to EXT-02 today.
- `SYNTH_PROMPT.format(` appears exactly once in the file (D-11 additive-only invariant, grep-asserted).
- Base `SYNTH_SYSTEM` string is preserved verbatim when hook is `None` or returns an empty context (grep-asserted via `test_pre_synthesis_hook_none_is_noop` and the failure-fallback test).
- 5 new tests cover the locked PATTERNS §6 list: hook invocation contract, default-None no-op, extra_context additive composition, constraints block injection, failure-fallback to empty context with `caplog` warning assertion.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PreSynthesisContext + PreSynthesisHook + pre_synthesis_hook param + hook invocation in synthesize()** — `ee0b7fc` (feat)
2. **Task 2: Add test coverage for pre_synthesis_hook (invoked, none-is-noop, extra_context, constraints, failure-fallback)** — `7c17713` (test)

_Note: This plan's frontmatter declared `tdd="true"` on both tasks. The commit sequence is feat→test (not the classic RED→GREEN). Task 1's verify block runs the existing 20-test regression gate (all passing with zero behavior change when hook=None), and Task 2 adds the 5 hook-specific tests (all passing). Both commits are green in isolation — the gate's invariant (no broken build mid-sequence) is preserved._

## Files Created/Modified

- `forge_bridge/learning/synthesizer.py` — added `PreSynthesisContext` dataclass, `PreSynthesisHook` alias, constructor param, hook invocation + additive prompt composition, `.tags.json` sidecar write. `SYNTH_PROMPT.format(` reduced from its original single call site to a single different call site (unchanged count — invariant preserved).
- `tests/test_synthesizer.py` — appended `TestPreSynthesisHook` class with 5 tests + a `_make_router_mock` helper.

## Decisions Made

- **Execution order feat-then-test rather than test-then-feat (RED→GREEN).** The plan prescribed task 1 before task 2 and task 1's verify block explicitly includes the existing 20-test regression gate. Because the hook-None path is a genuine no-op (base prompts flow through unchanged), no existing test was invalidated by task 1. Each commit passes its local test suite; the feat→test order is a plan-ordering choice, not a TDD violation.
- **`.tags.json` filename uses `with_suffix()`.** Plan action language was `"{output_path.stem}.tags.json"` in one paragraph and `output_path.with_suffix(".tags.json")` in the concrete Edit block. Implemented the concrete spec (the Edit block), which replaces `.py` with `.tags.json` (cleaner than stem-with-appended-suffix). Either reading is compatible with the D-11 "stash tags for EXT-02" intent.
- **`import json as _json` rename preserved.** Plan explicitly wrote `import json as _json  # for the tags sidecar write; rename to avoid shadowing` — kept as-is. The rename defends against any consumer code or plugin later defining a module-level `json` name.

## Deviations from Plan

None — plan executed exactly as written.

Two-line sanity annotations worth calling out but which are NOT deviations (they are the plan's explicit spec):
- Task 1 action spec uses `output_path.with_suffix(".tags.json")` — implemented as specified.
- Task 1 action spec prescribes `import json as _json` — implemented as specified.

**Total deviations:** 0
**Impact on plan:** None. Plan executed verbatim through both tasks; all acceptance criteria pass; all 25 synthesizer tests pass; full 212-test suite pass.

## Issues Encountered

None.

## Verification Results

**Task 1 acceptance-criteria greps (all passing):**

| Criterion | Expected | Observed |
|-----------|----------|----------|
| `^class PreSynthesisContext` | exactly 1 | line 65 |
| `@dataclass(frozen=True)` | ≥ 1 | line 64 |
| `PreSynthesisHook = Callable[[str, dict], Awaitable[PreSynthesisContext]]` | present | line 89 |
| `pre_synthesis_hook: PreSynthesisHook \| None = None` | present (signature) | line 245 |
| `self._pre_synthesis_hook` | ≥ 2 | 3 matches (store + guard + await) |
| `await self._pre_synthesis_hook(` | exactly 1 | line 276 |
| `"raw_code": raw_code, "count": count` | present | line 278 |
| `pre_synthesis_hook raised — falling back to empty context` | present | line 282 |
| `Constraints:` | present | line 291 (runtime) + line 80 (docstring) |
| `Example intent:` | present | line 304 (runtime) + line 78 (docstring) |
| `.tags.json` | present | line 370 |
| `SYNTH_PROMPT.format(` | exactly 1 (D-11 invariant) | 1 match |

**Task 1 automated smoke test:** `python -c "from forge_bridge.learning.synthesizer import PreSynthesisContext, PreSynthesisHook, SkillSynthesizer; ..." → OK`

**Task 2 acceptance-criteria:**

| Criterion | Status |
|-----------|--------|
| `class TestPreSynthesisHook` present | line 268 |
| `test_pre_synthesis_hook_invoked_with_intent_and_params` | line 269 |
| `test_pre_synthesis_hook_none_is_noop` | line 297 |
| `test_pre_synthesis_context_extra_context_appended_to_system` | line 311 |
| `test_pre_synthesis_context_constraints_injected` | line 335 |
| `test_pre_synthesis_hook_exception_falls_back_to_empty_context` | line 358 |
| `pytest tests/test_synthesizer.py -x` exit code 0 | PASS (25 tests) |

**Full suite regression:** `pytest tests/` → 212 passed, 2 warnings (both pre-existing — websockets deprecation + `TestServer` class collection warning; neither introduced by this plan).

## Next Phase Readiness

- LRN-04 requirement complete. Projekt-forge plan 06-04 can now construct a consumer-side async hook that reads its DB, build a `PreSynthesisContext(extra_context=..., constraints=..., tags=["project:...", ...])`, and pass it as `pre_synthesis_hook=` when constructing `SkillSynthesizer` in projekt-forge's `__main__.py`.
- `PreSynthesisContext` and `PreSynthesisHook` are public symbols inside `forge_bridge/learning/synthesizer.py`. Plan 06-02 did NOT add them to `forge_bridge/__init__.py` — that barrel re-export is plan 06-04's responsibility per the PATTERNS §4 guidance (`forge_bridge/__init__.py` barrel update lives alongside the consumer-side wiring work).
- EXT-02 (MCP provenance annotations) can now consume the `.tags.json` sidecar files. No forge-bridge API change will be required when EXT-02 lands — the sidecar is already a stable JSON contract.

## Self-Check: PASSED

Verified:
- `forge_bridge/learning/synthesizer.py` exists and contains all required symbols (greps above).
- `tests/test_synthesizer.py` exists and contains `TestPreSynthesisHook` class (line 268) with 5 test methods.
- Commit `ee0b7fc` present in `git log --oneline`.
- Commit `7c17713` present in `git log --oneline`.
- All 25 synthesizer tests pass.
- All 212 full-suite tests pass.
- No deletions in either task commit (`git diff --diff-filter=D --name-only HEAD~1 HEAD` empty for both).

---
*Phase: 06-learning-pipeline-integration*
*Completed: 2026-04-18*
