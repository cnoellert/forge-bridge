"""Contract tests for forge_bridge.learning.storage.StoragePersistence Protocol (STORE-01..04, STORE-06).

Covers:
  D-02  persist is the ONLY declared method (no persist_batch, no shutdown)
  D-03  @runtime_checkable supports isinstance() checks
  D-04  canonical schema documented in module docstring (4 cols, UNIQUE, 2 indexes, NO promoted)
  D-05/D-06/D-07  consistency / no-retry / sync-callback language present in module docstring
  D-10  ExecutionLog.set_storage_callback signature unchanged from v1.1.0
  STORE-02  StoragePersistence importable from forge_bridge root and in __all__
"""
from __future__ import annotations

import inspect
import types


# ── D-03: isinstance behavior via @runtime_checkable ────────────────────────


def test_isinstance_positive_class_with_persist():
    """A class with a persist method satisfies StoragePersistence (D-03)."""
    from forge_bridge.learning.storage import StoragePersistence

    class ConcreteBackend:
        def persist(self, record):
            return None

    assert isinstance(ConcreteBackend(), StoragePersistence)


def test_isinstance_positive_async_persist():
    """async def persist also satisfies the Protocol — method-presence, not signature (D-03)."""
    from forge_bridge.learning.storage import StoragePersistence

    class AsyncBackend:
        async def persist(self, record):
            return None

    assert isinstance(AsyncBackend(), StoragePersistence)


def test_isinstance_negative_object_without_persist():
    """An object missing persist does not satisfy StoragePersistence."""
    from forge_bridge.learning.storage import StoragePersistence

    class NoPersist:
        def write(self, record):
            return None

    assert not isinstance(NoPersist(), StoragePersistence)


def test_isinstance_negative_simple_namespace():
    """A plain namespace with no methods does not satisfy StoragePersistence."""
    from forge_bridge.learning.storage import StoragePersistence

    obj = types.SimpleNamespace(x=1)
    assert not isinstance(obj, StoragePersistence)


# ── D-02: persist is the ONLY method (no persist_batch, no shutdown) ────────


def test_protocol_has_only_persist_method():
    """D-02: Protocol exposes exactly one method — persist. No persist_batch, no shutdown."""
    from forge_bridge.learning.storage import StoragePersistence

    # _is_protocol attribute exists on typing.Protocol subclasses
    assert getattr(StoragePersistence, "_is_protocol", False) is True

    # Collect declared protocol members (excluding dunders + inherited Protocol machinery).
    declared = {
        name for name in vars(StoragePersistence)
        if not name.startswith("_") and callable(vars(StoragePersistence)[name])
    }
    assert declared == {"persist"}, (
        f"D-02 violation: StoragePersistence must expose only 'persist'. Got {declared}"
    )

    # Belt-and-suspenders: explicit absence checks
    assert not hasattr(StoragePersistence, "persist_batch"), (
        "D-02: persist_batch deferred to future BatchingStoragePersistence sub-Protocol"
    )
    assert not hasattr(StoragePersistence, "shutdown"), (
        "D-02: shutdown deferred; session-per-call has nothing to clean up"
    )


# ── D-04/D-05/D-06/D-07: docstring carries canonical schema + invariants ────


def test_module_docstring_carries_canonical_schema():
    """D-04: module docstring contains the 4-column schema with UNIQUE + 2 indexes, NO promoted."""
    import forge_bridge.learning.storage as storage_mod

    doc = storage_mod.__doc__ or ""
    assert "code_hash" in doc and "TEXT" in doc
    assert "timestamp" in doc and "TIMESTAMPTZ" in doc
    assert "raw_code" in doc
    assert "intent" in doc
    assert "UNIQUE (code_hash, timestamp)" in doc
    assert "ix_<name>_code_hash" in doc
    assert "ix_<name>_timestamp" in doc

    # D-08: no promoted column in the schema.
    # (The word 'promoted' may appear elsewhere in the docstring discussing the
    # decision; but it MUST NOT appear inside a CREATE TABLE block.)
    create_block_start = doc.find("CREATE TABLE")
    assert create_block_start >= 0, "CREATE TABLE block missing from module docstring"
    create_block_end = doc.find(");", create_block_start)
    assert create_block_end > create_block_start
    create_block = doc[create_block_start:create_block_end]
    assert "promoted" not in create_block, (
        f"D-08 violation: 'promoted' column must not appear in CREATE TABLE block.\n"
        f"Block was:\n{create_block}"
    )


def test_module_docstring_states_consistency_and_no_retry_and_sync():
    """D-05, D-06, D-07: docstring contains consistency model, no-retry, sync-callback guidance."""
    import forge_bridge.learning.storage as storage_mod

    doc = (storage_mod.__doc__ or "").lower()
    # D-05 — log-authoritative / best-effort
    assert "source of truth" in doc or "log-authoritative" in doc
    assert "best-effort" in doc or "best effort" in doc
    # D-06 — no retry in callback
    assert "no retry" in doc or "not retry" in doc or "must not retry" in doc
    # D-07 — sync callback recommended
    assert "sync" in doc


# ── STORE-02: barrel re-export from forge_bridge root ───────────────────────


def test_storage_persistence_importable_from_root():
    """STORE-02: StoragePersistence importable from forge_bridge and in __all__."""
    import forge_bridge
    from forge_bridge import StoragePersistence

    assert StoragePersistence is not None
    assert "StoragePersistence" in forge_bridge.__all__


def test_storage_persistence_identity_across_barrel():
    """Re-exports return the same class identity."""
    from forge_bridge import StoragePersistence as A
    from forge_bridge.learning import StoragePersistence as B
    from forge_bridge.learning.storage import StoragePersistence as C

    assert A is B is C


# ── D-10 / STORE-03: ExecutionLog.set_storage_callback signature unchanged ──


def test_set_storage_callback_signature_unchanged():
    """STORE-03: set_storage_callback accepts one positional parameter (D-10, v1.1.0 shape)."""
    from forge_bridge import ExecutionLog

    sig = inspect.signature(ExecutionLog.set_storage_callback)
    params = [p for p in sig.parameters if p != "self"]
    # The v1.1.0 parameter name is 'fn' — asserting exact name preserves the locked contract.
    assert params == ["fn"], (
        f"STORE-03: set_storage_callback signature must be (self, fn). Got {params}"
    )
