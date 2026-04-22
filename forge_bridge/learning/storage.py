"""StoragePersistence Protocol — typed contract for mirroring ExecutionRecord writes (STORE-01..04).

This module ships ONLY the Protocol definition; forge-bridge does NOT ship any
DDL, Alembic revisions, SQLAlchemy models, or connection management. Consumers
(today: projekt-forge) own the schema, the migration chain, and the session
lifecycle. See .planning/phases/08-sql-persistence-protocol/08-CONTEXT.md §D-03
for the ownership decision.

Canonical minimal schema (implementations MUST preserve this shape for
cross-consumer compatibility):

    CREATE TABLE <name> (
        code_hash   TEXT        NOT NULL,
        timestamp   TIMESTAMPTZ NOT NULL,
        raw_code    TEXT        NOT NULL,
        intent      TEXT        NULL,
        UNIQUE (code_hash, timestamp)
    );
    CREATE INDEX ix_<name>_code_hash ON <name>(code_hash);
    CREATE INDEX ix_<name>_timestamp ON <name>(timestamp DESC);

Four columns. `promoted` is deliberately OMITTED (D-08): ExecutionLog.mark_promoted()
writes to JSONL but does NOT fire the storage callback, so a `promoted` column
would always be False at insert and never updated — a false-negative query
landmine. Promotion state stays JSONL-only for v1.3.0; a dedicated mirror hook
(`set_promotion_callback`) is deferred to a future requirement.

Consistency model — log-authoritative, eventual, best-effort (D-05):
    JSONL is the source of truth. DB is a best-effort mirror. A row in DB implies
    a row in JSONL; the reverse is not guaranteed. Queries for promotion-count
    invariants MUST use ExecutionLog.get_count() or a JSONL scan, NOT the DB.

No-retry invariant (D-06, P-03.5):
    Implementations MUST NOT retry inside the callback. On DB failure:
    log one WARNING line and return. Retry stacks async tasks, holds
    connections open, and triggers QueuePool exhaustion under sustained
    outage. Durability comes from JSONL + optional backfill, NOT from
    retry-in-callback. If reconciliation is ever needed, it lives in a
    separate process that reads JSONL and writes missing rows out of the
    hot path.

Sync callback recommendation (D-07, P-03.8):
    ExecutionLog.record() can fire from Flame threads where no asyncio event
    loop is running. An async callback in that path silently drops via the
    `asyncio.ensure_future` RuntimeError branch. Implementations SHOULD
    prefer synchronous `def persist(self, record) -> None` using a sync
    database engine (e.g. a sync ORM engine + `engine.begin()` context manager).
    Async is permitted for consumers that can guarantee a running loop at
    record()-time, but sync is the documented default.

Idempotency (D-09):
    Implementations SHOULD use `insert(...).on_conflict_do_nothing(
    index_elements=["code_hash", "timestamp"])` (PostgreSQL dialect; native
    to projekt-forge's deployment). Two forge-bridge processes writing to
    distinct JSONL paths but sharing the same consumer DB produce no
    duplicate rows. Same `code_hash` with distinct `timestamp` is expected
    (different execution instances) and both rows persist.

Usage:
    from forge_bridge import StoragePersistence, ExecutionLog

    class MyBackend:
        def persist(self, record):
            # sync write; log-and-swallow on failure
            ...

    backend = MyBackend()
    assert isinstance(backend, StoragePersistence)  # runtime_checkable sanity
    log = ExecutionLog(log_path=...)
    log.set_storage_callback(backend.persist)  # signature unchanged from v1.1.0
"""
from __future__ import annotations

from typing import Awaitable, Protocol, Union, runtime_checkable

from forge_bridge.learning.execution_log import ExecutionRecord


@runtime_checkable
class StoragePersistence(Protocol):
    """Typed contract for durable-storage mirrors of ExecutionLog writes (STORE-01, D-02, D-03).

    Implementations MUST provide a `persist` method. Return type is duck-typed
    (`None | Awaitable[None]`) to match the existing StorageCallback signature
    accepted by ExecutionLog.set_storage_callback() (D-10). Runtime dispatch
    via inspect.iscoroutinefunction is unchanged.

    Decorated @runtime_checkable so consumers can `isinstance(fn, StoragePersistence)`
    at registration as a sanity check (D-03). Method-presence only; signatures
    are NOT enforced at runtime.

    See the module docstring for: canonical schema, consistency model, no-retry
    invariant, and sync-callback recommendation. The schema block above is
    normative — implementations that deviate are responsible for providing
    equivalent query performance.
    """

    def persist(self, record: ExecutionRecord) -> Union[None, Awaitable[None]]: ...
