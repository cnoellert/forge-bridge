# Phase 8: SQL Persistence Protocol - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 7 (5 forge-bridge, 2 projekt-forge)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `forge_bridge/learning/storage.py` | protocol/contract | request-response | `projekt_forge/conform/matcher.py` (MatchStrategy Protocol) | role-match |
| `forge_bridge/learning/__init__.py` | barrel re-export | — | `forge_bridge/__init__.py` lines 35-39 | exact |
| `forge_bridge/__init__.py` | barrel re-export + `__all__` | — | self (existing `__all__` block lines 54-75) | exact |
| `tests/test_storage_protocol.py` | test | — | `tests/test_execution_log.py` (storage callback tests lines 222-391) + `tests/test_public_api.py` (isinstance + `__all__` patterns) | role-match |
| `tests/test_public_api.py` | test (modify) | — | self (existing `test_all_contract` + `test_package_version` lines 51-69, 179-185) | exact |
| `pyproject.toml` | config (version bump) | — | self (line 6) | exact |
| `projekt_forge/learning/wiring.py` + new Alembic revision | service + migration | CRUD | `projekt_forge/cli/project.py` sync Session pattern (lines 151-166) + `projekt_forge/db/migrations/versions/004_media_content_hash.py` | role-match |

---

## Pattern Assignments

### `forge_bridge/learning/storage.py` (protocol, request-response)

**Analog:** `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/conform/matcher.py`

**No existing Protocol in forge-bridge.** The only Protocol class in either repo is `MatchStrategy` in projekt-forge. Use it as the structural template.

**Imports pattern** (matcher.py lines 1-11 — adapt for storage.py):
```python
"""<module docstring carrying schema, consistency model, no-retry invariant>"""
from __future__ import annotations

from typing import Awaitable, Union
from typing import Protocol, runtime_checkable

from forge_bridge.learning.execution_log import ExecutionRecord
```

**Protocol class pattern** (matcher.py lines 44-49 — adapt for StoragePersistence):
```python
class MatchStrategy(Protocol):
    """Protocol for a single match strategy."""

    name: str

    def match(self, query: SegmentQuery, index: MediaIndex) -> list[MatchCandidate]: ...
```

Adapted shape for `StoragePersistence`:
```python
@runtime_checkable
class StoragePersistence(Protocol):
    """<docstring — must cover: schema, consistency model, no-retry, sync-callback rec>"""

    def persist(self, record: ExecutionRecord) -> Union[None, Awaitable[None]]: ...
```

**Critical constraints from CONTEXT.md decisions:**
- D-02: `persist` ONLY — no `persist_batch`, no `shutdown`
- D-03: `@runtime_checkable` decorator required
- D-04: class docstring carries the canonical SQL schema (4 columns + UNIQUE + 2 indexes, NO `promoted` column per D-08)
- D-05: docstring must state JSONL is source-of-truth, DB is best-effort mirror
- D-06: docstring must state no retry ever in callback
- D-07: docstring must recommend sync `def persist(...)` for consumers running on Flame threads

**Schema to embed verbatim in docstring** (from D-04):
```
CREATE TABLE <name> (
    code_hash   TEXT        NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL,
    raw_code    TEXT        NOT NULL,
    intent      TEXT        NULL,
    UNIQUE (code_hash, timestamp)
);
CREATE INDEX ix_<name>_code_hash ON <name>(code_hash);
CREATE INDEX ix_<name>_timestamp ON <name>(timestamp DESC);
```

---

### `forge_bridge/learning/__init__.py` (barrel re-export, modify)

**Analog:** `forge_bridge/__init__.py` lines 35-39

**Current state of `forge_bridge/learning/__init__.py`** (line 1 only):
```python
"""forge_bridge.learning — execution logging, synthesis, and tool watching."""
```

The file has no re-exports yet. The pattern to follow is the root `__init__.py` import block:

**Re-export pattern to copy** (`forge_bridge/__init__.py` lines 35-39):
```python
from forge_bridge.learning.execution_log import (
    ExecutionLog,
    ExecutionRecord,
    StorageCallback,
)
```

Add alongside these imports:
```python
from forge_bridge.learning.storage import StoragePersistence
```

---

### `forge_bridge/__init__.py` (barrel re-export + `__all__`, modify)

**Analog:** self — `forge_bridge/__init__.py` lines 35-39 and 54-75

**Learning pipeline import block to extend** (lines 35-39, current):
```python
from forge_bridge.learning.execution_log import (
    ExecutionLog,
    ExecutionRecord,
    StorageCallback,
)
```

Add `StoragePersistence` import from `forge_bridge.learning` (via the sub-package barrel):
```python
from forge_bridge.learning.storage import StoragePersistence
```

**`__all__` block to extend** (lines 54-75, current — 15 symbols):
```python
__all__ = [
    # LLM routing
    "LLMRouter",
    "get_router",
    # Learning pipeline
    "ExecutionLog",
    "ExecutionRecord",
    "StorageCallback",
    "SkillSynthesizer",
    "PreSynthesisContext",
    "PreSynthesisHook",
    # MCP server
    "register_tools",
    "get_mcp",
    # Server lifecycle
    "startup_bridge",
    "shutdown_bridge",
    # Flame HTTP bridge
    "execute",
    "execute_json",
    "execute_and_read",
]
```

Add `"StoragePersistence"` in the Learning pipeline group after `"StorageCallback"`. Result: 16 symbols.

**Docstring update** (lines 5-17): add `StoragePersistence` to the module-level docstring's import example alongside `StorageCallback`.

---

### `tests/test_storage_protocol.py` (test, new)

**Note on test directory:** Tests are flat in `tests/` — there is NO `tests/learning/` subdirectory. Closest analogs confirm this: `tests/test_execution_log.py` lives directly in `tests/`. The new file should be `tests/test_storage_protocol.py`.

**Analog 1:** `tests/test_execution_log.py` — storage callback tests (lines 222-391) for test structure and import style.

**Analog 2:** `tests/test_public_api.py` — `isinstance`, `__all__` membership, and `callable()` assertion patterns.

**Test file imports pattern** (test_execution_log.py lines 1-8):
```python
"""Tests for forge_bridge.learning.execution_log module."""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
```

Adapted for storage_protocol:
```python
"""Contract tests for forge_bridge.learning.storage.StoragePersistence Protocol (STORE-01..04)."""
from __future__ import annotations

import pytest
```

**isinstance positive test pattern** (test_public_api.py lines 253-282 for structure, adapted):
```python
def test_isinstance_positive_class_with_persist():
    """A class with a persist method satisfies StoragePersistence (D-03)."""
    from forge_bridge.learning.storage import StoragePersistence

    class ConcreteBackend:
        def persist(self, record):
            pass

    backend = ConcreteBackend()
    assert isinstance(backend, StoragePersistence)
```

**isinstance negative test patterns** — two cases required (CONTEXT.md §Specifics):
```python
def test_isinstance_negative_object_without_persist():
    """An object missing persist does not satisfy StoragePersistence."""
    from forge_bridge.learning.storage import StoragePersistence

    class NoPersist:
        def write(self, record):
            pass

    assert not isinstance(NoPersist(), StoragePersistence)


def test_isinstance_negative_non_callable():
    """A plain object (no methods at all) does not satisfy StoragePersistence."""
    import types
    from forge_bridge.learning.storage import StoragePersistence

    obj = types.SimpleNamespace(x=1)
    assert not isinstance(obj, StoragePersistence)
```

**Barrel re-export test pattern** (test_public_api.py lines 254-282):
```python
def test_storage_persistence_importable_from_root():
    """StoragePersistence is importable from forge_bridge root and in __all__."""
    import forge_bridge
    from forge_bridge import StoragePersistence

    assert StoragePersistence is not None
    assert "StoragePersistence" in forge_bridge.__all__
```

**Error handling for callback pattern** (test_execution_log.py lines 266-287 — simulated outage, adapted for adapter tests in projekt-forge 08-02):
```python
def test_storage_callback_error_does_not_break_jsonl_write(tmp_path, caplog):
    import logging
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)

    def boom(_rec):
        raise RuntimeError("storage offline")

    log.set_storage_callback(boom)

    with caplog.at_level(logging.WARNING, logger="forge_bridge.learning.execution_log"):
        log.record("x = 1")

    assert log_path.exists()
    assert log_path.read_text().strip() != ""
    assert any("storage_callback" in rec.message for rec in caplog.records)
```

---

### `tests/test_public_api.py` (modify — version guard + `__all__` membership)

**Analog:** self — lines 51-69 (`test_all_contract`) and lines 179-185 (`test_package_version`).

**Version guard to update** (lines 179-185):
```python
def test_package_version():
    """pyproject.toml version is 1.2.1 after Phase 07.1 v1.2.1 hotfix release."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'version = "1.2.1"' in content, (
        'pyproject.toml must declare version = "1.2.1" per Phase 07.1 v1.2.1 hotfix.'
    )
```

Change `"1.2.1"` to `"1.3.0"` in both the assertion string and the docstring.

**`__all__` membership test to update** (lines 51-69):
```python
def test_all_contract():
    """forge_bridge.__all__ matches the 15-name surface exactly ..."""
    import forge_bridge

    expected = {
        "LLMRouter", "get_router",
        "ExecutionLog", "ExecutionRecord", "StorageCallback",
        "SkillSynthesizer", "PreSynthesisContext", "PreSynthesisHook",
        "register_tools", "get_mcp",
        "startup_bridge", "shutdown_bridge",
        "execute", "execute_json", "execute_and_read",
    }
    assert set(forge_bridge.__all__) == expected, ...
    assert len(forge_bridge.__all__) == 15
```

Add `"StoragePersistence"` to `expected` set; change `== 15` to `== 16`; update docstring to say "16-name surface" and reference "Phase 8 STORE-01..04".

Also update `test_public_surface_has_15_symbols` (line 285-289): rename to `test_public_surface_has_16_symbols`, change `== 15` to `== 16`, update docstring.

Add a `test_phase8_symbols_importable_from_root` function following the Phase 6 precedent at lines 253-282:
```python
def test_phase8_symbols_importable_from_root():
    """Phase 8 adds StoragePersistence to the public API surface."""
    import forge_bridge
    from forge_bridge import StoragePersistence

    assert StoragePersistence is not None
    assert "StoragePersistence" in forge_bridge.__all__
```

---

### `pyproject.toml` (version bump, modify)

**Analog:** self — line 6.

**Current** (line 6):
```toml
version = "1.2.1"
```

**Target:**
```toml
version = "1.3.0"
```

---

### `projekt_forge/learning/wiring.py` (modify — replace `_persist_execution` stub)

**Analog:** `projekt_forge/cli/project.py` lines 1-16 + 141-166 — sync SQLAlchemy `Session` usage (the ONLY sync session pattern in projekt-forge).

**Current stub** (`projekt_forge/learning/wiring.py` lines 100-122):
```python
async def _persist_execution(record: ExecutionRecord) -> None:
    """Storage callback: mirror every ExecutionRecord to projekt-forge's logs.

    EXT-03 (SQL persistence backend) is deferred to v1.1.x. Today this is a
    logger-only stub that proves the callback fires end-to-end. When EXT-03
    lands, replace the body of this function with:

        from projekt_forge.db.engine import get_engine, get_session_factory
        engine = get_engine()
        Session = get_session_factory(engine)
        async with Session() as session:
            session.add(ExecutionRow.from_record(record))
            await session.commit()

    The contract is stable (ExecutionRecord fields are locked by D-03); only
    the storage mechanism is swap-able.
    """
    logger.info(
        "execution mirrored: code_hash=%s intent=%r promoted=%s",
        record.code_hash[:12],
        record.intent,
        record.promoted,
    )
```

**Target shape** (D-07 sync, D-06 no retry, D-09 on_conflict_do_nothing, D-11 isinstance assert):

**Sync Session pattern to copy** (`projekt_forge/cli/project.py` lines 141-166):
```python
def _create_invite(...) -> None:
    from sqlalchemy.orm import Session as SaSession
    from projekt_forge.db.models import DBProjectInvite

    engine = _get_admin_engine()
    with SaSession(engine) as session:
        invite = DBProjectInvite(...)
        session.add(invite)
        session.commit()
```

**Adapted target for `_persist_execution`:**
```python
def _persist_execution(record: ExecutionRecord) -> None:
    """Storage callback: mirror ExecutionRecord to the execution_log table.

    Sync (D-07): safe to call from Flame threads where no event loop runs.
    No retry (D-06): DB outage is logged at WARNING; JSONL is source of truth.
    Idempotent (D-09): on_conflict_do_nothing on (code_hash, timestamp).
    """
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        from sqlalchemy.dialects.postgresql import insert

        engine = _get_sync_engine()
        stmt = (
            insert(_execution_log_table)
            .values(
                code_hash=record.code_hash,
                timestamp=record.timestamp,
                raw_code=record.raw_code,
                intent=record.intent,
            )
            .on_conflict_do_nothing(index_elements=["code_hash", "timestamp"])
        )
        with engine.begin() as conn:
            conn.execute(stmt)
    except Exception:
        logger.warning(
            "execution_log DB write failed — JSONL unaffected",
            exc_info=True,
        )
```

**isinstance sanity check at wiring time** (D-11 — goes in `init_learning_pipeline` near line 183):
```python
from forge_bridge import StoragePersistence

assert isinstance(_persist_execution, StoragePersistence), (
    "_persist_execution must satisfy StoragePersistence Protocol. "
    "If forge-bridge added required methods (v1.3+), update the adapter."
)
execution_log.set_storage_callback(_persist_execution)
```

**Note on `_persist_execution` signature change:** Current stub is `async def`. The replacement is `def` (sync). Tests in `tests/test_learning_wiring.py` at lines 95-117 assert an async callback fires; those tests must be updated to reflect sync dispatch (no `await asyncio.sleep(0)` needed, no `AsyncMock`).

**Note on engine accessor:** projekt-forge has no existing sync singleton engine. The adapter needs a `_get_sync_engine()` helper using `sqlalchemy.create_engine` (same pattern as `projekt_forge/cli/project.py` lines 9-15). Use `psycopg2` URL derived from `FORGE_DB_URL` or `get_db_config()`.

---

### New Alembic revision in `projekt_forge/db/migrations/versions/` (new file)

**Analog:** `projekt_forge/db/migrations/versions/004_media_content_hash.py` (most recent revision — same chain)

**Revision scaffolding pattern** (004_media_content_hash.py lines 1-36):
```python
"""Add content_hash column to media table for content-addressed deduplication.

NOTE: Alembic autogenerate does NOT detect index changes reliably.
This migration is hand-written.

...

Revision ID: 004
Revises: 003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(...)
    op.create_index(...)


def downgrade() -> None:
    op.drop_index(...)
    op.drop_column(...)
```

**Adapted shape for revision 005** (from D-04 schema + D-09 idempotency):
```python
"""Add execution_log table for forge-bridge SQL persistence backend (EXT-03).

NOTE: Hand-written migration — autogenerate does not detect CHECK constraints
or custom index patterns reliably.

Revision ID: 005
Revises: 004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_log",
        sa.Column("code_hash", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_code", sa.Text, nullable=False),
        sa.Column("intent", sa.Text, nullable=True),
        sa.UniqueConstraint("code_hash", "timestamp", name="uq_execution_log_code_hash_timestamp"),
    )
    op.create_index("ix_execution_log_code_hash", "execution_log", ["code_hash"], unique=False)
    op.create_index("ix_execution_log_timestamp", "execution_log", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_execution_log_timestamp", table_name="execution_log")
    op.drop_index("ix_execution_log_code_hash", table_name="execution_log")
    op.drop_table("execution_log")
```

**Note on table name:** Planner must confirm `execution_log` does not collide with existing projekt-forge tables before adopting. Fallback per D-13: `forge_execution_log`.

**Note on revision ID convention:** projekt-forge uses string revision IDs (`"001"`, `"002"`, `"003"`, `"004"`). New revision is `"005"` with `down_revision = "004"`.

---

## Shared Patterns

### Barrel Re-Export Chain
**Source:** `forge_bridge/__init__.py` lines 35-51 + `forge_bridge/learning/__init__.py` (currently empty)
**Apply to:** `storage.py` → `forge_bridge/learning/__init__.py` → `forge_bridge/__init__.py` → `__all__`
**Pattern:** New public symbols always travel the full chain: module → sub-package barrel → root barrel → `__all__` → asserted in `tests/test_public_api.py`.

### `from __future__ import annotations`
**Source:** `forge_bridge/learning/execution_log.py` line 7; `projekt_forge/learning/wiring.py` line 14
**Apply to:** All new `.py` files in both repos. Every module in both codebases uses this.

### Logger initialization
**Source:** `forge_bridge/learning/execution_log.py` line 23; `projekt_forge/learning/wiring.py` line 28
```python
# forge-bridge pattern
logger = logging.getLogger(__name__)

# projekt-forge pattern (uses explicit name, not __name__)
logger = logging.getLogger("projekt_forge.learning.wiring")
```
**Apply to:** `forge_bridge/learning/storage.py` uses `logging.getLogger(__name__)`. projekt-forge adapter uses the explicit-name convention.

### Error isolation (log-and-swallow)
**Source:** `forge_bridge/learning/execution_log.py` lines 224-231
```python
try:
    self._storage_callback(record)
except Exception:
    logger.warning(
        "storage_callback raised — execution log unaffected",
        exc_info=True,
    )
```
**Apply to:** `_persist_execution` body in `projekt_forge/learning/wiring.py` — same `try/except Exception: logger.warning(...); return` with no inner retry. D-06 is an absolute invariant.

### Sync SQLAlchemy session (projekt-forge)
**Source:** `projekt_forge/cli/project.py` lines 9-16 + 151-166
```python
def _get_admin_engine():
    from sqlalchemy import create_engine
    db_cfg = get_db_config()
    url = f"postgresql://{db_cfg['user']}:{db_cfg['password']}@{db_cfg['host']}:{db_cfg['port']}/forge_admin"
    return create_engine(url)

# Usage:
engine = _get_admin_engine()
with SaSession(engine) as session:
    session.add(obj)
    session.commit()
```
**Apply to:** `_persist_execution` adapter. Use `engine.begin()` (auto-commit context manager) rather than `session.add() + commit()` since the adapter issues a single INSERT statement.

### Alembic revision scaffolding
**Source:** `projekt_forge/db/migrations/versions/004_media_content_hash.py` (full file)
**Apply to:** New revision `005_execution_log.py` — copy scaffolding verbatim, update revision ID, down_revision, docstring, and upgrade/downgrade bodies.

---

## No Analog Found

No files fall into this category. All 7 files have usable analogs. Note that `StoragePersistence` has no Protocol analog in forge-bridge itself — the analog is from projekt-forge's `MatchStrategy`. The key structural difference: `MatchStrategy` is not `@runtime_checkable` and has two members (`name` attribute + `match` method). `StoragePersistence` must be `@runtime_checkable` and has one method (`persist` only, per D-02/D-03).

---

## Key Facts for Planner (Decision Summary)

| Decision | Constraint |
|----------|-----------|
| D-02 | `persist` ONLY — no `persist_batch`, no `shutdown` |
| D-03 | `@runtime_checkable` on the Protocol class |
| D-04 | 4-column schema in docstring; NO `promoted` column |
| D-06 | No retry EVER in `_persist_execution` |
| D-07 | `def persist(...)` sync in projekt-forge adapter |
| D-08 | `promoted` column deliberately omitted |
| D-09 | `on_conflict_do_nothing(index_elements=["code_hash","timestamp"])` |
| D-10 | `set_storage_callback()` signature unchanged |
| D-11 | `assert isinstance(self.persist, StoragePersistence)` in projekt-forge wiring |
| D-13 | Alembic revision 005, single-head chain, down_revision = "004" |
| D-14 | Version bump `1.2.1` → `1.3.0` |
| Tests | `tests/test_storage_protocol.py` (flat in `tests/` — NO `tests/learning/` subdir) |

## Metadata

**Analog search scope:** `forge_bridge/` (full), `tests/` (full), `projekt_forge/` (learning, db, cli, conform)
**Files scanned:** 12 source files + 3 test files
**Pattern extraction date:** 2026-04-21
