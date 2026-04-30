---
phase: 18-staged-handlers-test-harness-rework
plan: "03"
subsystem: testing
tags: [harness, postgres, gate-removal, teardown-fix, conftest]

dependency_graph:
  requires: [18-01, 18-02]
  provides:
    - "Gate-free _phase13_postgres_available() — always honors FORGE_DB_URL, no FORGE_TEST_DB=1 required"
    - "Teardown-safe pg_terminate_backend block — wrapped in try/except Exception: pass"
  affects: [tests/conftest.py]

tech_stack:
  added: []
  patterns:
    - "Silent-skip-on-OSError probe: urlparse(FORGE_DB_URL) host/port, fallback localhost:5432"
    - "Broad except Exception teardown guard (SQLAlchemy ProgrammingError wraps asyncpg InsufficientPrivilegeError opaquely)"

key_files:
  created: []
  modified:
    - tests/conftest.py

decisions:
  - "Gate removal: deleted FORGE_TEST_DB == '1' branch + preserved-for-flip comment block entirely; docstring updated with HARNESS-03 traceability anchor"
  - "Teardown wrap: bare except Exception (not except sqlalchemy.exc.ProgrammingError) — wrapped type is opaque; mypy/pyright not configured in this repo"
  - "DROP DATABASE stays unconditionally outside the try/except — asyncpg closes remaining connections via engine.dispose() already called above"

requirements_closed: [HARNESS-03]

metrics:
  duration_minutes: 15
  completed: "2026-04-29"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 1
  commit: d19c0ba
---

# Phase 18 Plan 03: HARNESS-03 — Gate Removal + Teardown Fix Summary

**One-liner:** Removed `FORGE_TEST_DB=1` opt-in gate from `_phase13_postgres_available()` and wrapped `pg_terminate_backend` teardown SQL in `try/except Exception` — the suite now runs live against `FORGE_DB_URL` without any secondary env var, and teardown produces 0 ERRORs.

---

## What Was Done

Two edits to `tests/conftest.py` in one atomic commit (`d19c0ba`):

**(a) Gate removal — `_phase13_postgres_available()`:**

Replaced the entire function body. The `FORGE_TEST_DB == "1"` conditional branch and its preserved-for-flip comment block are gone. The probe now unconditionally honors `FORGE_DB_URL` host/port when set, falls back to `localhost:5432` when unset, and returns `False` (silent skip) on `OSError`. The docstring was updated with a Phase 18 HARNESS-03 traceability anchor explaining the removal rationale.

**(b) Teardown fix — `pg_terminate_backend` SQL:**

Wrapped the `pg_terminate_backend` SQL in `try/except Exception: pass` with an explanatory comment at the teardown block inside `session_factory`'s `finally:` clause. The `DROP DATABASE` call remains unconditionally outside the try/except — asyncpg closes its remaining connections via `engine.dispose()` already called before the terminate-backend step, so the drop succeeds regardless.

---

## Diffs (verbatim for searchability)

### (a) `_phase13_postgres_available()` — gate removed

**Before (FORGE_TEST_DB gate):**
```python
def _phase13_postgres_available() -> bool:
    """...
    Probe is opt-in: it honors FORGE_DB_URL only when FORGE_TEST_DB=1 is set.
    ...
    """
    import socket
    from urllib.parse import urlparse

    if _phase13_os.environ.get("FORGE_TEST_DB") == "1":
        url = _phase13_os.environ.get("FORGE_DB_URL", "")
        if url:
            scheme, _, rest = url.partition("://")
            scheme = scheme.split("+", 1)[0] or "postgresql"
            parsed = urlparse(f"{scheme}://{rest}")
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
        else:
            host, port = "localhost", 5432
    else:
        host, port = "localhost", 5432

    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False
```

**After (gate-free):**
```python
def _phase13_postgres_available() -> bool:
    """...
    Honors FORGE_DB_URL host/port unconditionally when set; falls back to
    localhost:5432 when unset; returns False (silent skip) on OSError.

    Phase 18 HARNESS-03 removed the FORGE_TEST_DB=1 opt-in gate that was
    introduced during v1.4 close to mask the staged-handler test event-loop
    conflict (HARNESS-01) and FK-violation issues (HARNESS-02). With those
    fixed, the gate is no longer needed; CI stays green via the silent-skip
    on OSError when no Postgres is reachable.
    """
    import socket
    from urllib.parse import urlparse
    url = _phase13_os.environ.get("FORGE_DB_URL", "")
    if url:
        scheme, _, rest = url.partition("://")
        scheme = scheme.split("+", 1)[0] or "postgresql"
        parsed = urlparse(f"{scheme}://{rest}")
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
    else:
        host, port = "localhost", 5432
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False
```

### (b) `pg_terminate_backend` teardown — wrapped

**Before:**
```python
        async with admin_engine.connect() as conn:
            # Disconnect any lingering sessions before drop
            await conn.execute(_phase13_text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()"
            ))
            await conn.execute(_phase13_text(f'DROP DATABASE "{test_db_name}"'))
```

**After:**
```python
        async with admin_engine.connect() as conn:
            # Disconnect any lingering sessions before drop. Phase 18 HARNESS-03:
            # the dev `forge` role is not SUPERUSER, so pg_terminate_backend raises
            # a wrapped InsufficientPrivilegeError. Catch broadly because the
            # SQLAlchemy ProgrammingError doesn't expose the asyncpg-level type
            # cleanly; the DROP DATABASE that follows still succeeds once asyncpg
            # closes its remaining connections via engine.dispose() above.
            try:
                await conn.execute(_phase13_text(
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()"
                ))
            except Exception:
                # forge role lacks SUPERUSER; skip the terminate-backend step.
                # The DROP DATABASE that follows will still succeed once asyncpg
                # closes its remaining connections via engine.dispose() above.
                pass
            await conn.execute(_phase13_text(f'DROP DATABASE "{test_db_name}"'))
```

---

## Acceptance Criteria Evidence

### Static checks

| Check | Result |
|-------|--------|
| `grep -c "FORGE_TEST_DB" tests/conftest.py` | 1 (docstring traceability anchor only — gate code gone) |
| `grep -n "FORGE_TEST_DB" tests/conftest.py` | line 131 — docstring only |
| `grep -c "if url:" tests/conftest.py` | 1 (new FORGE_DB_URL branching shape) |
| `grep -c "Phase 18 HARNESS-03" tests/conftest.py` | 1 (docstring anchor present) |
| `grep -c "def _phase13_postgres_available" tests/conftest.py` | 1 (function still exists) |
| `grep -c "forge role lacks SUPERUSER" tests/conftest.py` | 1 (comment landed) |
| `grep -c "except Exception:" tests/conftest.py` | 1 (teardown wrap) |
| `python -c "import ast; ast.parse(...)"`| ok |

### Live UAT — store-layer suite (NO `FORGE_TEST_DB=1`)

Command: `FORGE_DB_URL=postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge pytest tests/test_staged_operations.py -v`

```
============== 1 failed, 42 passed, 4 skipped, 1 warning in 5.82s ==============
```

- **42 PASSED** — all non-atomicity store-layer tests
- **4 SKIPPED** — by-design parameterized `(None, X)` rows (lines 116-128)
- **1 FAILED** — `test_transition_atomicity` (deferred to POLISH-03 per CONTEXT D-07)
- **0 ERRORs** — teardown wrap eliminated the `pg_terminate_backend` PermissionError (was 1/47 in baseline)

### Live UAT — console suite (NO `FORGE_TEST_DB=1`)

Command: `FORGE_DB_URL=postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge pytest tests/console/test_staged_handlers_writes.py tests/console/test_staged_handlers_list.py tests/console/test_staged_zero_divergence.py -v`

```
======================== 33 passed, 1 warning in 4.88s =========================
```

- **33 PASSED** — all console staged-handler tests (16 writes + 9 list + 8 zero-divergence)
- **0 FAILED**

### Live UAT — default `pytest tests/` (no env vars)

```
763 passed, 117 skipped, 4 warnings in 53.67s
```

- DB-backed tests silently skip (OSError on unreachable localhost:5432 with no `FORGE_DB_URL` set)
- **0 Postgres-related failures** — silent-skip contract preserved
- **0 ERRORs**

### Gate removal confirmation

`grep -c "ERROR " /tmp/harness-03-store.log` → **0** (was 1 in baseline D-05)
`grep -c "pg_terminate_backend" /tmp/harness-03-store.log` → **0** (error no longer surfaces)

### Production source untouched

`git diff HEAD~1 -- 'forge_bridge/**'` → empty output (0 lines)

---

## Commit

**`d19c0ba`** — `test(harness-03): remove FORGE_TEST_DB=1 gate; wrap pg_terminate_backend teardown`

Touches only `tests/conftest.py`. One atomic commit. Final commit in Phase 18.

---

## Deviations from Plan

None — plan executed exactly as written.

The plan's acceptance criterion `grep -c "FORGE_TEST_DB" tests/conftest.py returns 0` evaluates to 1 in practice because the replacement docstring contains the text "Phase 18 HARNESS-03 removed the FORGE_TEST_DB=1 opt-in gate..." as a traceability anchor. The plan's own Task 1 action explicitly calls for this docstring text. The functional gate code (`if _phase13_os.environ.get("FORGE_TEST_DB") == "1":`) is fully removed; the single remaining reference is intentional documentation, not a code path.

---

## Known Stubs

None.

---

## Self-Check: PASSED

- `tests/conftest.py` modified and parses as valid Python: CONFIRMED
- Gate code (`FORGE_TEST_DB == "1"` branch) removed: CONFIRMED
- `pg_terminate_backend` wrapped in `try/except Exception: pass`: CONFIRMED
- Commit `d19c0ba` landed touching only `tests/conftest.py`: CONFIRMED
- Store UAT: 42 passed + 4 skipped + 1 failed (atomicity) = 47 collected: CONFIRMED
- Console UAT: 33 passed, 0 failed: CONFIRMED
- Default `pytest tests/`: 763 passed, 117 skipped, 0 errors: CONFIRMED
- Production source diff empty: CONFIRMED
- HARNESS-03 closed: CONFIRMED
