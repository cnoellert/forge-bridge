---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 03
subsystem: api
tags: [llm, exceptions, public-api, fb-c, tool-call-loop, router, surface-contract]

# Dependency graph
requires:
  - phase: 04-public-api-surface-hardening
    provides: forge_bridge.__all__ barrel pattern + test_all_contract set-equality assertion shape (Phase 4 D-01/D-02)
  - phase: 06-projekt-forge-learning-pipeline-integration
    provides: ExecutionRecord/StorageCallback/PreSynthesisContext/PreSynthesisHook export pattern (LRN-02/LRN-04 — barrel grew 11→15)
  - phase: 08-sql-persistence-protocol
    provides: StoragePersistence module-cohesion precedent (export class next to its closest sibling rather than separate _errors.py); barrel grew 15→16 (D-02..D-04)
provides:
  - Three new public exception classes at forge_bridge/llm/router.py module top — LLMLoopBudgetExceeded (D-18 verbatim signature), RecursiveToolLoopError (D-19 message-only), LLMToolError (D-19 message-only)
  - forge_bridge.__all__ grown from 16 → 19 with all three new exceptions exported from package root (D-15)
  - Public-API contract test test_all_contract updated to lock the 19-name surface; new tests test_phase15_exceptions_importable_from_root and test_phase15_LLMLoopBudgetExceeded_signature lock D-15 + D-18
  - Catchable-failure-mode contract that Phase 16 (FB-D) /api/v1/chat will map to HTTP 504 (LLMLoopBudgetExceeded) / 500 (RecursiveToolLoopError) / 502 (LLMToolError)
affects:
  - 15-06 (recursive-synthesis guard plan — consumes RecursiveToolLoopError + the contextvar that raises it)
  - 15-08 (coordinator plan — raises LLMLoopBudgetExceeded on budget cap and LLMToolError on adapter failure)
  - 16 (FB-D chat endpoint — catches all three to discriminate HTTP status mapping)
  - projekt-forge v1.5 consumers — once forge-bridge ships v1.4, they can `from forge_bridge import LLMLoopBudgetExceeded, RecursiveToolLoopError, LLMToolError` to participate in the same discrimination

# Tech tracking
tech-stack:
  added: []  # Surface-only plan — no new runtime dependencies; ollama/anthropic pins were added in 15-02
  patterns:
    - "Module-cohesion exception placement (Phase 8 precedent extended): exception classes live next to the class that owns their semantics, NOT in a separate _errors.py file"
    - "Public-API barrel growth via test_all_contract set-equality lock: extras OR missing both fail loud at CI time (T-15-09 mitigation)"
    - "Per-exception importable test pattern from Phase 6/8 — enumerate each new export class, assert RuntimeError subclass, assert membership in __all__"
    - "Locked-signature test pattern for exception classes whose attributes are part of a downstream consumer contract (FB-D HTTP envelope reads .reason / .iterations / .elapsed_s)"

key-files:
  created: []
  modified:
    - "forge_bridge/llm/router.py — added 3 exception classes (72 lines) between _DEFAULT_SYSTEM_PROMPT and class LLMRouter:"
    - "forge_bridge/__init__.py — extended LLM-routing import block + __all__ list + module docstring example (16 → 19 entries)"
    - "tests/test_public_api.py — updated test_all_contract assertion to 19-name set; renamed test_public_surface_has_16_symbols → test_public_surface_has_19_symbols; added 2 new Phase 15 tests"

key-decisions:
  - "D-15 honored verbatim: barrel grows 16 → 19 (the v1.4 STATE.md mandate of '16 → 17' is superseded by D-15 because all three exceptions need distinct HTTP status mapping in Phase 16)"
  - "D-16 honored: all three classes live in router.py, NOT in a separate _errors.py module — matches Phase 8 StoragePersistence-next-to-ExecutionLog precedent"
  - "D-18 signature locked verbatim: LLMLoopBudgetExceeded(reason, iterations, elapsed_s) with exact format string `\"{reason} (iterations={iterations}, elapsed={elapsed_s:.1f}s)\"` — Phase 16 reads .reason / .iterations / .elapsed_s"
  - "D-19 honored: RecursiveToolLoopError + LLMToolError are message-only (no extra fields) for v1.4. Future fields deferred to v1.5 if FB-D needs them"
  - "Surface-only plan: this ships the catchable contract; the runtime that raises these exceptions lands in plans 15-06 (RecursiveToolLoopError via _in_tool_loop contextvar) and 15-08 (LLMLoopBudgetExceeded via budget caps + LLMToolError via adapter wrapping)"

patterns-established:
  - "Phase-scoped exception export pattern: when a phase introduces new failure modes that downstream consumers must discriminate (HTTP status mapping, retry policy, fallback), export the exception classes from forge_bridge.__all__ rather than forcing consumers to catch RuntimeError"
  - "Three-test-per-export-cluster lock-in: (1) extend test_all_contract with new names in expected set + new len() assert, (2) replace any historical 'has_N_symbols' test with the current count, (3) add a per-class importable test plus any signature-lock tests for classes whose constructor args are part of a downstream contract"

requirements-completed:
  - LLMTOOL-03
  - LLMTOOL-07

# Metrics
duration: 3min 26s
completed: 2026-04-27
---

# Phase 15 Plan 03: FB-C Public Exception Surface Summary

**Three new public exception classes (LLMLoopBudgetExceeded, RecursiveToolLoopError, LLMToolError) ship from forge_bridge.__all__ — barrel grows 16 → 19 — locking the catchable-failure contract Phase 16 (FB-D) /api/v1/chat will map to HTTP 504 / 500 / 502 respectively.**

## Performance

- **Duration:** 3min 26s (206s)
- **Started:** 2026-04-27T02:47:47Z
- **Completed:** 2026-04-27T02:51:18Z
- **Tasks:** 3 of 3 complete
- **Files modified:** 3

## Accomplishments

- Three new exception classes inserted at the top of `forge_bridge/llm/router.py` between `_DEFAULT_SYSTEM_PROMPT` and `class LLMRouter:`, all inheriting from `RuntimeError` per CONVENTIONS.md line 67. `LLMLoopBudgetExceeded` carries the D-18 verbatim signature `(reason, iterations, elapsed_s)` with the locked format string `"{reason} (iterations={iterations}, elapsed={elapsed_s:.1f}s)"`. The other two are message-only per D-19.
- `forge_bridge.__all__` grown from 16 to 19 entries with the new exceptions exported from the package root. Identity check (`forge_bridge.LLMToolError is forge_bridge.llm.router.LLMToolError`) confirms single source of truth — no duplicate class objects.
- `tests/test_public_api.py` locked to the 19-symbol contract. `test_all_contract` set-equality assertion catches both extras and missing names — a future commit that adds a fourth exception or removes one of these three will break the test loud at CI time (T-15-09 mitigation per the threat model).
- Two new tests (`test_phase15_exceptions_importable_from_root` + `test_phase15_LLMLoopBudgetExceeded_signature`) lock the D-15 export contract and the D-18 signature so Phase 16 can rely on `.reason` / `.iterations` / `.elapsed_s` when constructing the HTTP 504 envelope.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add three exception classes at top of router.py** — `2d31a94` (feat)
2. **Task 2: Grow forge_bridge.__all__ from 16 to 19** — `838aa19` (feat)
3. **Task 3: Lock 19-symbol contract in test_public_api.py** — `d3991d0` (test)

**Plan metadata:** committed in same atomic plan-completion commit (this SUMMARY.md write).

_Note: TDD was applied per task — RED was confirmed before each GREEN implementation via shell-level import-failure checks (Task 1, Task 2) and via a failing pytest run on the existing 16-name assertion (Task 3 RED happened automatically once Task 2 grew __all__ — `test_all_contract` failed because the expected set was still 16-name)._

## Files Created/Modified

- `forge_bridge/llm/router.py` — 72 lines added: box-drawing comment block + three exception classes between `_DEFAULT_SYSTEM_PROMPT` and `class LLMRouter:`. No existing code modified.
- `forge_bridge/__init__.py` — 11 lines added, 1 line changed: LLM-routing import block extended to a multi-line form with the three new names; `__all__` list grown by 3 entries (alphabetically the new names sort to `LLMLoopBudgetExceeded`, `LLMToolError`, `RecursiveToolLoopError`); module docstring example updated to reflect the new surface.
- `tests/test_public_api.py` — 64 lines added, 5 changed: `test_all_contract` set + len assertions updated to 19; `test_public_surface_has_16_symbols` renamed to `test_public_surface_has_19_symbols` with updated docstring; new `test_phase15_exceptions_importable_from_root` (loops over the 3 classes asserting RuntimeError + __all__ membership); new `test_phase15_LLMLoopBudgetExceeded_signature` (locks D-18 signature + format string + iterations=-1 wall-clock variant).

## Decisions Made

None new — followed the plan's locked decisions verbatim. The plan itself froze D-15 (16 → 19 export growth), D-16 (placement in router.py, not separate _errors.py), D-18 (LLMLoopBudgetExceeded signature), and D-19 (message-only RecursiveToolLoopError + LLMToolError) at the FB-C context-gathering stage; this plan was the mechanical realization.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' acceptance criteria passed on the first verification run; no Rule 1-4 deviations triggered.

## Key Surfaces Established

| Surface | Location | Catchable Contract |
|---------|----------|--------------------|
| `LLMLoopBudgetExceeded(reason, iterations, elapsed_s)` | `forge_bridge.LLMLoopBudgetExceeded` (re-exported from `forge_bridge.llm.router`) | Phase 16 maps to HTTP 504 (gateway timeout). Reads `.reason ∈ {"max_iterations", "max_seconds"}`, `.iterations` (int, -1 if wall-clock fired pre-iteration), `.elapsed_s` (float seconds). |
| `RecursiveToolLoopError(message)` | `forge_bridge.RecursiveToolLoopError` | Phase 16 maps to HTTP 500 (internal error — caller bug). Message-only. Plan 15-06 will raise this via the `_in_tool_loop` contextvar in `complete_with_tools()` and `acomplete()` entry points. |
| `LLMToolError(message)` | `forge_bridge.LLMToolError` | Phase 16 maps to HTTP 502 (bad gateway — provider failure). Message-only. Plan 15-08 will raise this when the coordinator catches an unrecoverable Anthropic/Ollama failure after SDK-internal retries are exhausted. |

## Sequencing Note (forward-looking)

This plan ships SURFACE ONLY. The runtime that raises these exceptions lands in:

- **Plan 15-06 (recursive-synthesis guard)** — adds the `_in_tool_loop` `contextvars.ContextVar[bool]` to `forge_bridge/llm/router.py` and the on-entry checks in `acomplete()` + `complete_with_tools()` that raise `RecursiveToolLoopError`. Also extends the synthesizer safety blocklist (D-14) to reject `forge_bridge.llm` imports at the AST level — belt-and-suspenders.
- **Plan 15-08 (coordinator)** — implements `complete_with_tools()` proper. Raises `LLMLoopBudgetExceeded` when `max_iterations` (D-03) or `max_seconds` (D-04) caps fire. Raises `LLMToolError` from adapter exception handlers using the Phase 8 cf221fe `type(exc).__name__` rule (NOT `str(exc)`) to avoid leaking provider credentials.
- **Phase 16 (FB-D) /api/v1/chat endpoint** — catches all three classes to discriminate HTTP status mapping. Without the exports this plan ships, FB-D would have to `except RuntimeError` and lose the 504/500/502 distinction, which is the regression vs. Phase 4's "explicit catchable contracts" precedent and Phase 8's StoragePersistence export.

## Verification Output

```
$ pytest tests/test_public_api.py tests/test_llm.py -x -q
......................................                                   [100%]
38 passed, 1 warning in 1.75s
```

```
$ python -c "import forge_bridge; print(sorted(forge_bridge.__all__))"
['ExecutionLog', 'ExecutionRecord', 'LLMLoopBudgetExceeded', 'LLMRouter',
 'LLMToolError', 'PreSynthesisContext', 'PreSynthesisHook',
 'RecursiveToolLoopError', 'SkillSynthesizer', 'StorageCallback',
 'StoragePersistence', 'execute', 'execute_and_read', 'execute_json',
 'get_mcp', 'get_router', 'register_tools', 'shutdown_bridge',
 'startup_bridge']
```

```
$ git diff --stat fec8835...HEAD
 forge_bridge/__init__.py   | 12 +++++++-
 forge_bridge/llm/router.py | 72 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_public_api.py   | 69 ++++++++++++++++++++++++++++++++++++++++----
 3 files changed, 147 insertions(+), 6 deletions(-)
```

Exactly 3 files modified — matches the verification gate.

## Threat-Model Alignment

The plan's `<threat_model>` register identified four threats (T-15-09 through T-15-12). Implementation status:

- **T-15-09 (T — silent surface drift):** MITIGATED. `test_all_contract` set-equality assertion fires on extras OR missing names. A future commit adding a fourth exception or removing one of these three will fail at CI time.
- **T-15-10 (I — exception message leak):** ACCEPTED. The `LLMLoopBudgetExceeded` format string interpolates only structural ints/floats and a controlled enum-shaped string. The Phase 8 cf221fe `type(exc).__name__` rule applies to plan 15-08's coordinator handlers, NOT to this plan's class definitions.
- **T-15-11 (D — caller cannot discriminate failure mode):** MITIGATED — this is the threat the export contract this plan ships exists to mitigate. Phase 16 can now `from forge_bridge import LLMLoopBudgetExceeded, RecursiveToolLoopError, LLMToolError` and discriminate 504 / 500 / 502 instead of falling through to a single 500 bucket.
- **T-15-12 (S — synthesized tool reuses class name):** ACCEPTED. Class identity is checked by `isinstance()` against the canonical class object owned by `forge_bridge.llm.router`, not by string name. Plan 15-06's static AST blocklist prevents the import vector required to even reach the canonical class.

No new threat surface introduced — exception classes are pure data definitions.

## Self-Check: PASSED

**Files claimed modified — all exist and contain expected content:**

- ✓ `forge_bridge/llm/router.py` — `grep -c "^class LLMLoopBudgetExceeded(RuntimeError):"` = 1; `grep -c "^class RecursiveToolLoopError(RuntimeError):"` = 1; `grep -c "^class LLMToolError(RuntimeError):"` = 1
- ✓ `forge_bridge/__init__.py` — `len(forge_bridge.__all__) == 19`; all 19 names match expected set
- ✓ `tests/test_public_api.py` — 19 tests, 19/19 passing; `grep -c "test_phase15_exceptions_importable_from_root"` = 1; `grep -c "test_phase15_LLMLoopBudgetExceeded_signature"` = 1; `grep -c "test_public_surface_has_16_symbols"` = 0 (replaced)

**Commits claimed — all exist in git log:**

- ✓ `2d31a94` (feat: Task 1) — `git log --oneline | grep -q 2d31a94`
- ✓ `838aa19` (feat: Task 2) — `git log --oneline | grep -q 838aa19`
- ✓ `d3991d0` (test: Task 3) — `git log --oneline | grep -q d3991d0`
