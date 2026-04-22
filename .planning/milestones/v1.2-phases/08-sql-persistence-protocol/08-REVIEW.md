---
phase: 08-sql-persistence-protocol
reviewed: 2026-04-21T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - forge_bridge/__init__.py
  - forge_bridge/learning/__init__.py
  - forge_bridge/learning/storage.py
  - tests/test_public_api.py
  - tests/test_storage_protocol.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-04-21
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found (Info-only)

## Summary

Phase 8 ships `StoragePersistence` as a `@runtime_checkable typing.Protocol` and grows `forge_bridge.__all__` from 15 to 16. The change is small, surgical, and faithful to the locked decisions in `08-CONTEXT.md`:

- **D-02** (one method only) — confirmed: `persist` is the only declared method; the contract test at `tests/test_storage_protocol.py:64-86` asserts this via `vars(StoragePersistence)` inspection plus explicit `hasattr` negative checks for `persist_batch` and `shutdown`.
- **D-03** (`@runtime_checkable`) — confirmed: decorator applied at `forge_bridge/learning/storage.py:79`; runtime `isinstance()` exercised by positive sync (`ConcreteBackend`), positive async (`AsyncBackend`), and two negative tests.
- **D-04** (canonical 4-column schema in docstring) — confirmed: `code_hash` / `timestamp` / `raw_code` / `intent`, `UNIQUE (code_hash, timestamp)`, two indexes. Docstring test extracts the `CREATE TABLE` block and asserts `promoted` does NOT appear inside it — a tight regression gate for D-08.
- **D-05 / D-06 / D-07** — consistency / no-retry / sync-callback language all present in the module docstring and verified by `test_module_docstring_states_consistency_and_no_retry_and_sync`.
- **STORE-02** (barrel re-export) — confirmed: symbol present in `forge_bridge.__all__`, in `forge_bridge.learning.__all__`, and identity-equal across all three import paths (`test_storage_persistence_identity_across_barrel`).
- **`__all__` size** — exactly 16 symbols; dual-asserted by both `test_all_contract` (set-equality + `len == 16`) and `test_public_surface_has_16_symbols`.
- **No credential handling** — bridge surface is a pure Protocol + docstring; no DB driver imports, no connection strings, no DDL. Schema ownership correctly delegated to consumers.
- **No async DB leakage** — `storage.py` imports only `typing.{Awaitable, Protocol, Union, runtime_checkable}` plus `ExecutionRecord`. No `sqlalchemy`, `asyncpg`, `aiopg`, or `tenacity`.
- **No `promoted` references in schema** — the only two mentions in `storage.py` (lines 22–23) correctly explain *why* it's omitted, outside the CREATE TABLE block.

No Critical or Warning issues found. Three Info-level suggestions follow — all are polish, not defects. The Phase 8 deliverable is ready to ship as-is.

## Info

### IN-01: Stale docstring count in `test_public_api_importable`

**File:** `tests/test_public_api.py:22-23`
**Issue:** The test's docstring says "All 11 public symbols import cleanly from forge_bridge root (D-02)." but the test body imports only 11 of the 16 exported symbols — and the surface has now grown to 16. The module-level docstring at `tests/test_public_api.py:5` also still references "the 11-name consumer surface (API-01)". Neither is a bug (the test still passes because it's a subset import), but the comments drift from reality and a future reader chasing "API-01 / 11 symbols" in the test file will be confused. The `__all__` contract is correctly enforced in `test_all_contract` and `test_public_surface_has_16_symbols`, so coverage is not at risk.
**Fix:** Update the two stale doc references, e.g.:
```python
# Line 5 (module docstring):
    API-01  forge_bridge.__all__ exports the 16-name consumer surface

# Line 22-23 (test docstring):
def test_public_api_importable():
    """Core public symbols import cleanly from forge_bridge root (D-02).

    Full 16-symbol __all__ contract is enforced by test_all_contract;
    this test is a smoke check on the most-used subset.
    """
```
Optional: extend the import list to cover all 16 symbols so the smoke test matches its name. Not required.

### IN-02: `__all__` ordering in `forge_bridge/__init__.py` is grouped; `forge_bridge/learning/__init__.py` is alphabetical

**File:** `forge_bridge/__init__.py:55-77`, `forge_bridge/learning/__init__.py:14-22`
**Issue:** The two barrels use different ordering conventions. Package root groups by logical area with section comments (LLM routing / Learning pipeline / MCP / lifecycle / Flame) — intentional and readable. The sub-package `forge_bridge/learning/__init__.py:14-22` is alphabetical, which puts `StorageCallback` *after* `SkillSynthesizer` and `StoragePersistence` *last*. The inconsistency is cosmetic only — Python doesn't care about `__all__` order, and no test asserts ordering — but a grouped-by-concern ordering in `learning/__init__.py` (e.g. `ExecutionLog` / `ExecutionRecord` / `StorageCallback` / `StoragePersistence` together, then `SkillSynthesizer` / `PreSynthesisContext` / `PreSynthesisHook` together) would mirror the root barrel and make related symbols adjacent.
**Fix:** Regroup `forge_bridge/learning/__init__.py:14-22` to match the root convention, or leave alphabetical and add a 1-line comment documenting the choice. Either is fine. If you pick grouping:
```python
__all__ = [
    # execution logging
    "ExecutionLog",
    "ExecutionRecord",
    "StorageCallback",
    "StoragePersistence",
    # synthesis
    "SkillSynthesizer",
    "PreSynthesisContext",
    "PreSynthesisHook",
]
```

### IN-03: `_is_protocol` is a private `typing` implementation detail

**File:** `tests/test_public_api.py:303`, `tests/test_storage_protocol.py:69`
**Issue:** Two tests assert `getattr(StoragePersistence, "_is_protocol", False) is True` to verify the class is a `typing.Protocol`. `_is_protocol` is a CPython-internal attribute on `typing.Protocol` subclasses (leading underscore); it's not part of the documented public API of `typing` and could in principle change across Python versions. Practically it has been stable since 3.8 and both tests use a safe `getattr(..., False)` default, so the cost of breakage is one test update — but a more portable check is available.
**Fix:** Prefer the public-ish `typing.get_type_hints(StoragePersistence)` + `issubclass(StoragePersistence, typing.Protocol)` pattern, or just keep the effective behavioral check (`isinstance` works on a matching duck, doesn't on a non-matching one) which the rest of `test_storage_protocol.py` already does comprehensively. One option:
```python
import typing
# Cleaner: assert it IS a Protocol via the public hierarchy
assert typing.Protocol in StoragePersistence.__mro__
```
Not worth changing unless you're touching those lines for another reason.

---

## Notes on items explicitly flagged in the review prompt

1. **API surface correctness** — `StoragePersistence` is present at both `forge_bridge.learning` (`forge_bridge/learning/__init__.py:7, 21`) and at `forge_bridge` (`forge_bridge/__init__.py:40, 63`). `__all__` at the root has exactly 16 symbols and matches the set asserted in `test_all_contract`.
2. **Protocol correctness** — `@runtime_checkable` is applied (`storage.py:79`). `isinstance()` works against classes that expose a `.persist` method (both sync and async), verified positively and negatively. The docstring schema is 4 columns with no `promoted` — verified by a CREATE-TABLE-block substring test, which is the right shape for the D-08 regression gate. The prompt asked whether `isinstance()` would work against "plain functions that expose a `.persist` attribute" — `typing.Protocol`'s runtime check uses `hasattr`, so yes, any object (including a function with a monkey-patched `.persist` attribute) would pass, but in normal usage consumers pass a *backend object* (per D-11 in projekt-forge), not a bare function. This is correct behavior.
3. **Security** — no credential-adjacent surface. `storage.py` imports only `typing` primitives and `ExecutionRecord`. No DDL, no connection strings, no env-var reads, no SQL injection surface (no SQL executed by the bridge). Credential handling stays in projekt-forge where it belongs.
4. **Test quality** — contract tests assert Protocol semantics (D-02 method set, D-03 runtime-checkable, D-04 schema shape, D-05/06/07 invariant language in docstring, identity-across-barrel), not just import checks. The public-API surface test enforces `len(__all__) == 16` in *two* places. Coverage is appropriately tight.
5. **Imports / dead code** — no spurious imports. `storage.py` pulls only what the Protocol signature needs. No `promoted` references inside the CREATE TABLE block. No async DB imports. `from __future__ import annotations` is present and makes the forward references valid under PEP 563 semantics.

---

_Reviewed: 2026-04-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
