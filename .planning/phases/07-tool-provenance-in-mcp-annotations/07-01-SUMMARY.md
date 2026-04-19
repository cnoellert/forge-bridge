---
phase: 07-tool-provenance-in-mcp-annotations
plan: "01"
subsystem: learning-pipeline
tags: [sidecar, provenance, synthesizer, json, prov-01]

requires:
  - phase: 06-learning-pipeline-integration
    provides: "SkillSynthesizer with pre_synthesis_hook and ctx.tags support (LRN-04)"

provides:
  - "Synthesizer writes .sidecar.json with v1.2 envelope {tags, meta, schema_version=1} on every successful synthesis"
  - "Five canonical forge-bridge/* provenance meta keys in every sidecar"
  - "Legacy .tags.json write path fully retired from the synthesizer writer"
  - "Round-trip test class TestSidecarEnvelope (4 tests) proving envelope shape and anti-regression"

affects:
  - 07-02-watcher-sidecar-reader
  - 07-03-mcp-annotations-wiring

tech-stack:
  added: []
  patterns:
    - "Sidecar-first provenance: write .sidecar.json unconditionally at synthesis time; reader (07-02) applies sanitization at read time"
    - "Local import of forge_bridge inside synthesize() avoids circular import while still reading __version__"
    - "datetime.now(timezone.utc).isoformat() for UTC-aware ISO-8601 synthesized_at timestamp"

key-files:
  created: []
  modified:
    - forge_bridge/learning/synthesizer.py
    - tests/test_synthesizer.py

key-decisions:
  - "Sidecar is always written (unconditional) — no ctx.tags guard. meta provenance is always non-empty for a successful synthesis, so the guard would hide provenance for tagless runs."
  - "forge-bridge/code_hash uses hashlib.sha256(fn_code.encode()).hexdigest() — same pattern as the existing name-collision check in synthesize(); no new dependency."
  - "import forge_bridge as _forge_bridge placed as a local import inside synthesize() to avoid circular import: forge_bridge/__init__.py imports SkillSynthesizer; module-level would create a cycle."
  - "Legacy .tags.json write path fully retired from writer in v1.2. Backward-compat READ fallback for old sidecars lives in Plan 07-02's watcher, not in the writer."

patterns-established:
  - "Sidecar envelope v1.2: {tags: [...], meta: {forge-bridge/origin, forge-bridge/code_hash, forge-bridge/synthesized_at, forge-bridge/version, forge-bridge/observation_count}, schema_version: 1}"
  - "TestSidecarEnvelope class with _run_synth() helper — pattern for testing synthesizer file output in future plans"

requirements-completed:
  - PROV-01

duration: 18min
completed: 2026-04-19
---

# Phase 7 Plan 01: Sidecar Schema v1.2 — .sidecar.json Envelope + Canonical Provenance Meta

**Synthesizer now writes .sidecar.json with schema_version=1, five canonical forge-bridge/* provenance keys, and unconditional write (no ctx.tags guard) — retiring the legacy .tags.json writer and locking the sidecar shape before Plans 07-02/07-03 consume it.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-19T00:00:00Z
- **Completed:** 2026-04-19
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced the `if ctx.tags: tags_path.write(.tags.json)` conditional writer with an unconditional `.sidecar.json` envelope writer
- Added `from datetime import datetime, timezone` to the stdlib import block in synthesizer.py
- Injected five canonical `forge-bridge/*` meta keys: origin, code_hash, synthesized_at, version, observation_count
- Added `TestSidecarEnvelope` class to `tests/test_synthesizer.py` with 4 tests covering round-trip, meta completeness, empty-tags path, and anti-regression against `.tags.json`
- Full suite: 224 tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace .tags.json writer with .sidecar.json envelope + canonical meta** - `a40859f` (feat)
2. **Task 2: Round-trip test for sidecar envelope + canonical meta keys** - `65e4468` (test)

**Plan metadata:** see final metadata commit

## Files Created/Modified

- `forge_bridge/learning/synthesizer.py` - Added datetime/timezone imports; replaced .tags.json conditional with unconditional .sidecar.json envelope writer containing schema_version=1 and five canonical meta keys
- `tests/test_synthesizer.py` - Appended TestSidecarEnvelope class with 4 round-trip and anti-regression tests

## Decisions Made

- Sidecar written unconditionally — the `if ctx.tags:` guard was dropped because `meta` provenance is always non-empty for a successful synthesis; hiding provenance for tagless runs would be incorrect.
- `import forge_bridge as _forge_bridge` placed as a local import inside `synthesize()` to avoid circular import at module load time (forge_bridge/__init__.py imports SkillSynthesizer).
- Legacy `.tags.json` write path fully retired from the writer. Backward-compat read support for old sidecars is Plan 07-02's responsibility (at the reader/watcher layer).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. The local import pattern for `forge_bridge.__version__` (to avoid circular import) was explicitly called out in the plan and worked as documented.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `.sidecar.json` writer shape is locked as the v1.2 canonical format — Plans 07-02 and 07-03 can safely depend on it
- Plan 07-02 owns: watcher reads .sidecar.json (with backward-compat .tags.json fallback), `_sanitize_tag()` sanitization boundary
- Plan 07-03 owns: registry wiring of sidecar meta into MCP tool `_meta` annotations

## Self-Check: PASSED

- FOUND: forge_bridge/learning/synthesizer.py
- FOUND: tests/test_synthesizer.py
- FOUND: 07-01-SUMMARY.md
- FOUND commit: a40859f (feat: sidecar writer)
- FOUND commit: 65e4468 (test: TestSidecarEnvelope)

---
*Phase: 07-tool-provenance-in-mcp-annotations*
*Completed: 2026-04-19*
