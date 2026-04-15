---
phase: 03-learning-pipeline
plan: 02
subsystem: learning
tags: [llm, ast, synthesizer, validation, mcp-tools, code-generation]

# Dependency graph
requires:
  - phase: 03-learning-pipeline
    provides: ExecutionLog with promotion signals, watcher with SYNTHESIZED_DIR constant
  - phase: 01-tool-parity-llm-router
    provides: LLMRouter with acomplete() async API and sensitivity routing
provides:
  - synthesize() async function that generates validated synth_*.py MCP tools from LLM output
  - 3-stage validation pipeline (ast.parse, signature check, dry-run with mocked bridge)
  - _extract_function, _check_signature, _dry_run internal helpers
affects: [03-learning-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [3-stage-llm-validation, importlib-dry-run, shared-constant-import-contract]

key-files:
  created:
    - forge_bridge/learning/synthesizer.py
    - tests/test_synthesizer.py
  modified: []

key-decisions:
  - "SYNTHESIZED_DIR imported from watcher.py (not redefined) — contract test enforces identity"
  - "3-stage validation: ast.parse -> signature check -> dry-run with mocked bridge functions"
  - "Name collision: identical content = return existing path (idempotent), different content = reject with warning"

patterns-established:
  - "Import-based constant sharing: synthesizer imports SYNTHESIZED_DIR from watcher to guarantee path agreement"
  - "Contract test pattern: assert obj_a is obj_b to catch accidental constant redefinition"
  - "Dry-run validation: importlib.util temp-load + inspect.signature for sample kwargs + AsyncMock bridge patches"

requirements-completed: [LEARN-07, LEARN-08, LEARN-09]

# Metrics
duration: 2min
completed: 2026-04-15
---

# Phase 3 Plan 02: Skill Synthesizer Summary

**LLM-powered skill synthesizer with 3-stage validation (AST parse, signature check, mocked dry-run) generating synth_*.py MCP tools via local-only LLM router**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-15T04:35:49Z
- **Completed:** 2026-04-15T04:37:47Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- synthesize() calls LLM router with sensitive=True, generates validated async MCP tool files
- 3-stage validation rejects: syntax errors, non-async functions, missing synth_ prefix, missing docstring, missing return annotation, multiple functions, runtime errors
- Name collision handling: identical content returns existing path (idempotent), different content rejects
- SYNTHESIZED_DIR imported from watcher.py with contract test proving identity
- 17 new tests (all mocked LLM, no real network calls), 141 total suite green

## Task Commits

Each task was committed atomically:

1. **Task 1: Create synthesizer.py with LLM synthesis, 3-stage validation, and file output**
   - `233313a` (test: add failing tests -- RED phase)
   - `daefcc8` (feat: implement synthesizer -- GREEN phase)

## Files Created/Modified
- `forge_bridge/learning/synthesizer.py` - synthesize(), _extract_function, _check_signature, _dry_run, prompt templates
- `tests/test_synthesizer.py` - 17 tests covering extraction, signature validation, dry-run, synthesis flow, path contract

## Decisions Made
- SYNTHESIZED_DIR imported from watcher.py rather than redefined -- contract test enforces this permanently
- _extract_function strips markdown fences and whitespace so LLM output format variations are tolerated
- Dry-run builds sample kwargs from inspect.signature type annotations (str="", int=0, float=0.0, bool=False)
- SHA-256 hash comparison for idempotent file collision detection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test for identical file skip -- content hash mismatch**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test pre-wrote file with un-stripped content but synthesizer writes stripped content after _extract_function, causing hash mismatch
- **Fix:** Changed test to write VALID_SYNTH_CODE.strip() to match what synthesizer actually writes
- **Files modified:** tests/test_synthesizer.py
- **Verification:** Test passes, idempotent skip behavior confirmed
- **Committed in:** daefcc8 (part of GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test correction only -- no implementation scope change.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Synthesizer is ready for the orchestrator (Plan 03) to wire execution_log promotion -> synthesize() calls
- Output lands in SYNTHESIZED_DIR where watcher.py already monitors for new .py files
- Full pipeline: bridge callback -> execution_log.record() -> promotion -> synthesize() -> watcher pickup -> MCP registration

---
*Phase: 03-learning-pipeline*
*Completed: 2026-04-15*
