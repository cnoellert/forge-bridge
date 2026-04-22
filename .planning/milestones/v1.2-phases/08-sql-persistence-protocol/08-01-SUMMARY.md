---
phase: 08-sql-persistence-protocol
plan: "01"
subsystem: learning
tags:
  - protocol
  - learning
  - public-api
  - storage
dependency_graph:
  requires:
    - forge_bridge/learning/execution_log.py (ExecutionRecord dataclass — unchanged)
  provides:
    - forge_bridge/learning/storage.StoragePersistence (@runtime_checkable Protocol)
    - forge_bridge.__all__ 16-symbol surface
  affects:
    - tests/test_public_api.py (16-symbol assertions updated)
    - 08-02 (projekt-forge adapter imports StoragePersistence directly from working tree)
tech_stack:
  added:
    - "typing.Protocol + @runtime_checkable (stdlib — no new deps)"
  patterns:
    - "Barrel re-export chain: module → sub-package barrel → root barrel → __all__"
    - "Protocol-only module: no DB imports, docstring carries canonical schema"
key_files:
  created:
    - forge_bridge/learning/storage.py
    - tests/test_storage_protocol.py
  modified:
    - forge_bridge/learning/__init__.py
    - forge_bridge/__init__.py
    - tests/test_public_api.py
decisions:
  - "D-10 param name confirmed as 'fn' (not 'callback') — test_set_storage_callback_signature_unchanged corrected to assert ['fn']"
  - "pytest import removed from test_storage_protocol.py (unused — ruff F401)"
  - "sqlalchemy mention removed from module docstring to pass grep acceptance criterion for no DB library refs"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-21"
  tasks_completed: 3
  files_changed: 5
---

# Phase 08 Plan 01: StoragePersistence Protocol Summary

**One-liner:** `@runtime_checkable StoragePersistence Protocol` with canonical 4-column SQL schema in module docstring, full barrel re-export chain (15 → 16 symbols in `forge_bridge.__all__`), and 10 contract tests covering isinstance behavior, D-02 method exclusivity, D-04/D-05/D-06/D-07 docstring invariants, and D-10 signature stability.

## What Was Built

### `forge_bridge/learning/storage.py` (new — commit `6809e36`)

`@runtime_checkable` Protocol with exactly one method (`persist`). Module docstring carries:
- Canonical 4-column schema (`code_hash TEXT`, `timestamp TIMESTAMPTZ`, `raw_code TEXT`, `intent TEXT`) with `UNIQUE (code_hash, timestamp)` and two indexes (`ix_<name>_code_hash`, `ix_<name>_timestamp DESC`)
- Consistency model: JSONL is source of truth, DB is best-effort mirror (D-05)
- No-retry invariant: `MUST NOT retry inside the callback` (D-06)
- Sync callback recommendation: prefer `def persist(...)` for Flame-thread safety (D-07)
- `promoted` column explicitly OMITTED with rationale (D-08)
- Idempotency guidance: `on_conflict_do_nothing(index_elements=["code_hash", "timestamp"])` (D-09)

Zero DB library imports. No `persist_batch`, no `shutdown` (D-02 lock).

### Barrel Re-Export Chain (commit `0f74d28`)

`forge_bridge/learning/__init__.py` — full barrel exposing `ExecutionLog`, `ExecutionRecord`, `StorageCallback`, `StoragePersistence`, `SkillSynthesizer`, `PreSynthesisContext`, `PreSynthesisHook`.

`forge_bridge/__init__.py` — three changes:
1. Docstring example updated: `StoragePersistence` added to learning pipeline line
2. `from forge_bridge.learning.storage import StoragePersistence` import added
3. `"StoragePersistence"` added to `__all__` after `"StorageCallback"`

Final `forge_bridge.__all__` (16 symbols, alphabetical for reference):
```
ExecutionLog, ExecutionRecord, LLMRouter, PreSynthesisContext, PreSynthesisHook,
SkillSynthesizer, StorageCallback, StoragePersistence, execute, execute_and_read,
execute_json, get_mcp, get_router, register_tools, shutdown_bridge, startup_bridge
```

### Contract Tests (commit `7695481`)

`tests/test_storage_protocol.py` — 10 tests:

| Test | Covers |
|------|--------|
| `test_isinstance_positive_class_with_persist` | D-03 positive |
| `test_isinstance_positive_async_persist` | D-03 async variant |
| `test_isinstance_negative_object_without_persist` | D-03 negative |
| `test_isinstance_negative_simple_namespace` | D-03 negative (namespace) |
| `test_protocol_has_only_persist_method` | D-02 method exclusivity |
| `test_module_docstring_carries_canonical_schema` | D-04, D-08 (no promoted in CREATE TABLE) |
| `test_module_docstring_states_consistency_and_no_retry_and_sync` | D-05, D-06, D-07 |
| `test_storage_persistence_importable_from_root` | STORE-02 |
| `test_storage_persistence_identity_across_barrel` | barrel identity |
| `test_set_storage_callback_signature_unchanged` | D-10 / STORE-03 |

`tests/test_public_api.py` updates:
- `test_all_contract`: 16-symbol expected set + `== 16` assertion
- `test_public_surface_has_15_symbols` → `test_public_surface_has_16_symbols`
- `test_phase8_symbols_importable_from_root` appended

## Test Results

```
pytest tests/test_storage_protocol.py -v
10 passed in 0.03s

pytest tests/ -q
289 passed, 2 warnings in 6.48s  (no regressions)
```

## Decision Confirmations

| Decision | Status |
|----------|--------|
| D-02: persist ONLY | Confirmed — `test_protocol_has_only_persist_method` guards it at CI |
| D-03: @runtime_checkable | Confirmed — isinstance positive/negative tests green |
| D-04: 4-column schema in docstring | Confirmed — `test_module_docstring_carries_canonical_schema` green |
| D-08: no promoted column | Confirmed — CREATE TABLE block scan in test passes |
| D-10: set_storage_callback signature unchanged | Confirmed — param name is `fn` (v1.1.0 shape) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_set_storage_callback_signature_unchanged` expected wrong param name**
- **Found during:** Task 3 test run (RED → GREEN)
- **Issue:** Plan spec said `params == ["callback"]` but actual v1.1.0 signature uses `fn` (not `callback`) — confirmed via `inspect.signature(ExecutionLog.set_storage_callback)`
- **Fix:** Changed assertion to `params == ["fn"]` — preserves D-10's intent (signature locked to v1.1.0 shape) with the correct parameter name
- **Files modified:** `tests/test_storage_protocol.py`
- **Commit:** `7695481`

**2. [Rule 1 - Bug] Unused `pytest` import in `test_storage_protocol.py`**
- **Found during:** Task 3 ruff check
- **Issue:** Plan's verbatim test content included `import pytest` but none of the tests use pytest fixtures or markers — ruff F401
- **Fix:** Removed unused import
- **Files modified:** `tests/test_storage_protocol.py`
- **Commit:** `7695481`

**3. [Rule 1 - Bug] `sqlalchemy` mention in module docstring triggered grep acceptance criterion**
- **Found during:** Task 1 acceptance criteria check
- **Issue:** Plan acceptance criterion checks `grep -q "sqlalchemy|..." forge_bridge/learning/storage.py exits 1` — the docstring contained "sqlalchemy.create_engine(...)" as a consumer example, causing a false positive
- **Fix:** Replaced with generic "sync database engine (e.g. a sync ORM engine + `engine.begin()` context manager)" — preserves the D-07 sync recommendation without naming the library in forge-bridge's source
- **Files modified:** `forge_bridge/learning/storage.py`
- **Commit:** `6809e36`

## Note for Plan 08-02

`StoragePersistence` is now available from the working tree at `forge_bridge.learning.storage.StoragePersistence`. Plan 08-02's adapter in projekt-forge can import it directly:

```python
from forge_bridge import StoragePersistence
```

The Protocol is at commit `6809e36` on branch `worktree-agent-a66445e2`. The orchestrator will merge this to main before 08-02 executes.

## Commits

| Hash | Message |
|------|---------|
| `6809e36` | feat(08-01): add StoragePersistence Protocol module (STORE-01, D-02, D-03, D-04) |
| `0f74d28` | feat(08-01): extend barrel re-export chain for StoragePersistence (STORE-02) |
| `7695481` | test(08-01): add StoragePersistence contract tests + update public-API surface to 16 (STORE-01..04, STORE-06) |

## Known Stubs

None — this plan ships a Protocol (documentation-only type contract). No data flows through it in this plan; projekt-forge's adapter in 08-02 provides the implementation.

## Threat Flags

None — no new network endpoints, no auth paths, no file access patterns, no schema changes at trust boundaries introduced. Protocol + docstring + tests only.

## Self-Check: PASSED

- `forge_bridge/learning/storage.py` exists: FOUND
- `tests/test_storage_protocol.py` exists: FOUND
- Commit `6809e36` exists: FOUND
- Commit `0f74d28` exists: FOUND
- Commit `7695481` exists: FOUND
- `pytest tests/` green (289 passed): CONFIRMED
