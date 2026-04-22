---
phase: 07-tool-provenance-in-mcp-annotations
plan: "02"
subsystem: learning-pipeline
tags: [sidecar, provenance, sanitize, watcher, prov-01, prov-03, prompt-injection]

requires:
  - phase: 07-tool-provenance-in-mcp-annotations
    plan: "01"
    provides: "Synthesizer writes .sidecar.json with v1.2 envelope {tags, meta, schema_version=1}"

provides:
  - "forge_bridge/learning/sanitize.py — _sanitize_tag(), apply_size_budget(), SANITIZE_ALLOWLIST, INJECTION_MARKERS, MAX_TAG_CHARS=64, MAX_TAGS_PER_TOOL=16, MAX_META_BYTES=4096"
  - "watcher._read_sidecar() — prefers .sidecar.json, falls back to .tags.json, applies sanitize + budget, always prepends literal 'synthesized' tag"
  - "_scan_once passes provenance=_read_sidecar(path) to register_tool via inspect feature-detect guard (forward-compatible with 07-03)"
  - "45 tests covering all PROV-03 sanitization cases and PROV-01 sidecar fallback cases"

affects:
  - 07-03-mcp-annotations-wiring

tech-stack:
  added: []
  patterns:
    - "Sanitize-at-READ-time: all consumer tags sanitized before leaving the watcher boundary — defense-in-depth for prompt injection (PROV-03)"
    - "Inspect feature-detect: inspect.signature(register_tool).parameters guards provenance kwarg call — allows Wave 2 to land before Wave 3 adds the registry kwarg"
    - "Unconditional 'synthesized' prepend: literal filter tag injected after sanitization so it is never sanitized away (TS-02.1)"
    - "Budget-first tag truncation: apply_size_budget caps tags at 16 AFTER 'synthesized' is prepended — net 15 consumer tags survive max"
    - "Protected canonical keys: forge-bridge/* meta keys are never evicted by budget pressure; non-canonical keys evicted first"

key-files:
  created:
    - forge_bridge/learning/sanitize.py
    - tests/test_sanitize.py
  modified:
    - forge_bridge/learning/watcher.py
    - tests/test_watcher.py

key-decisions:
  - "'synthesized' literal tag injected AFTER sanitization loop — it is never passed through _sanitize_tag(), so it cannot be dropped by the sanitizer. This means the tag is always first in the returned list."
  - "inspect.signature feature-detect guard chosen over try/except TypeError — cleaner and expresses intent. After Plan 07-03 adds the `provenance` kwarg to register_tool, the guard activates automatically without code changes in this module."
  - "apply_size_budget operates on the 'synthesized'-prepended list — so the 16-tag budget applies to the full payload including the literal tag. Net maximum of 15 consumer tags survive."
  - "Tags with injection markers log WARNING once via sanitize module logger (not watcher logger) — keeping the logging concern co-located with the rejection logic."
  - "Legacy .tags.json fallback returns meta:{} (empty) not None for meta — preserves the shape contract downstream even when meta is absent."

requirements-completed:
  - PROV-01
  - PROV-03

duration: 23min
completed: 2026-04-19
---

# Phase 7 Plan 02: Watcher Sidecar Reader + PROV-03 Sanitization Boundary

**Sanitization helper module (`sanitize.py`) + watcher `_read_sidecar()` with sidecar-preferred/legacy-fallback read path, prompt-injection rejection at read boundary, size budgets, and feature-detect provenance wire-through to `register_tool`.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-04-19T16:13:32Z
- **Completed:** 2026-04-19
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

### Task 1: forge_bridge/learning/sanitize.py (PROV-03)

- Created new module `forge_bridge/learning/sanitize.py` with:
  - `_sanitize_tag()`: rejects control chars (`\x00-\x1f`, `\x7f`), 8 injection markers, non-string types, empty strings; passes allowlist prefixes; redacts everything else to `redacted:<sha256[:8]>`
  - `apply_size_budget()`: enforces `MAX_TAGS_PER_TOOL=16` and `MAX_META_BYTES=4096`; never evicts the 5 canonical `forge-bridge/*` keys
  - Constants: `MAX_TAG_CHARS=64`, `MAX_TAGS_PER_TOOL=16`, `MAX_META_BYTES=4096`, `SANITIZE_ALLOWLIST`, `INJECTION_MARKERS`, `_PROTECTED_META_KEYS`
- Created `tests/test_sanitize.py` with 26 tests (20+ required by plan) covering all rejection/pass/redact cases, budget truncation, canonical key protection, and no-mutation guarantee
- Full TDD cycle: RED commit `53d7d5a`, GREEN commit `e742947`

### Task 2: watcher._read_sidecar + _scan_once provenance wire-through (PROV-01)

- Added `_read_sidecar()` helper to `forge_bridge/learning/watcher.py`:
  - Prefers `.sidecar.json` (v1.2+), falls back to `.tags.json` (v1.1 legacy)
  - Returns `None` for missing/malformed JSON/non-dict sidecar (with WARNING log)
  - Sanitizes all consumer tags via `_sanitize_tag()` at READ time
  - Prepends literal `"synthesized"` tag after sanitization (TS-02.1)
  - Enforces budgets via `apply_size_budget()`
- Modified `_scan_once` to call `_read_sidecar(path)` and pass result through `inspect.signature` feature-detect guard to `register_tool`
- Added `TestReadSidecar` class (8 tests) to `tests/test_watcher.py`
- Full TDD cycle: RED commit `0bff7e1`, GREEN commit `f498cca`

## Task Commits

Each task was committed atomically:

1. **Task 1 RED — failing sanitize tests** - `53d7d5a` (test)
2. **Task 1 GREEN — sanitize module implementation** - `e742947` (feat)
3. **Task 2 RED — failing TestReadSidecar tests** - `0bff7e1` (test)
4. **Task 2 GREEN — _read_sidecar + _scan_once wiring** - `f498cca` (feat)

## Files Created/Modified

- `forge_bridge/learning/sanitize.py` — New module: `_sanitize_tag`, `apply_size_budget`, 7 constants, `_PROTECTED_META_KEYS` frozenset
- `tests/test_sanitize.py` — 26 tests: `TestSanitizeTag` (22 cases), `TestApplySizeBudget` (4 cases), `TestAllowlistConstant` (1 case)
- `forge_bridge/learning/watcher.py` — Added `import inspect`, `import json as _json`, sanitize imports; added `_read_sidecar()` helper; modified `_scan_once` provenance call with feature-detect guard
- `tests/test_watcher.py` — Appended `TestReadSidecar` class (8 tests) for PROV-01 and sanitize-at-read cases

## Decisions Made

- `"synthesized"` literal injected AFTER the sanitization loop — never sanitized away, always first element in returned tags list.
- `inspect.signature` feature-detect chosen over try/except — expresses forward-compat intent cleanly; auto-activates when Plan 07-03 adds the `provenance` kwarg.
- `apply_size_budget` receives the full post-prepend list including `"synthesized"` — budget of 16 applies to total payload; net max 15 consumer tags.
- Legacy `.tags.json` fallback always returns `meta: {}` (not `None`) — preserves the `{"tags": [...], "meta": {...}}` shape contract for downstream consumers.

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- Task 1: RED `53d7d5a` (test) -> GREEN `e742947` (feat) — gate sequence verified
- Task 2: RED `0bff7e1` (test) -> GREEN `f498cca` (feat) — gate sequence verified

## Known Stubs

None. All implemented functionality is fully wired. The provenance dict is assembled and passed to `register_tool`; Plan 07-03 will consume it via the `provenance` kwarg it adds to the registry signature.

## Threat Flags

No new threat surface introduced beyond what was already declared in the plan's threat model (T-07-06 through T-07-11). All mitigations in the threat register are implemented:

- T-07-07 (PII leakage): Redaction allowlist implemented in `_sanitize_tag()`
- T-07-08 (prompt injection): `INJECTION_MARKERS` + `_CONTROL_CHAR_RE` implemented and tested
- T-07-09 (DoS via payload inflation): `apply_size_budget()` enforces <=16 tags, <=4KB meta
- T-07-10 (malformed sidecar crash): `_read_sidecar()` catches `JSONDecodeError` + `isinstance` check

## Self-Check: PASSED

- FOUND: forge_bridge/learning/sanitize.py
- FOUND: tests/test_sanitize.py
- FOUND: forge_bridge/learning/watcher.py (modified)
- FOUND: tests/test_watcher.py (modified)
- FOUND commit: 53d7d5a (test: RED sanitize)
- FOUND commit: e742947 (feat: GREEN sanitize)
- FOUND commit: 0bff7e1 (test: RED watcher)
- FOUND commit: f498cca (feat: GREEN watcher)
- pytest tests/test_sanitize.py: 26 passed
- pytest tests/test_watcher.py: 19 passed (11 existing + 8 new)
- pytest tests/: 258 passed (no regressions)

---
*Phase: 07-tool-provenance-in-mcp-annotations*
*Completed: 2026-04-19*
