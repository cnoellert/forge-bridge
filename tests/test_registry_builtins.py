"""Regression — protected built-in relationship types must survive a restore
from a DB that lacks them.

Reported by projekt-forge integration (docs/forge-bridge-findings-2026-05-31.md
finding #1, HIGH): a DB whose registry rows were established by migrations alone
— never by a seeded Registry — is missing the protected built-ins (member_of,
version_of, derived_from, references, peer_of). Any consumer creating those
edges then fails with `[NOT_FOUND] Relationship type 'version_of' not found`,
which broke every Flame publish on such DBs.

Root cause: forge_bridge/server/app.py:start() only seeded defaults when the
registry was *completely empty* (role_count == 0 and reltype_count == 0), so a
migrations-provisioned DB with other rel types present fell through the gate and
the built-ins were never registered. Fix: RegistryRepo.ensure_builtins() upserts
them idempotently by canonical UUID on every startup.

session_factory builds schema via Base.metadata.create_all, so the per-test DB
starts with an empty registry_relationship_types table — which models the
missing-built-ins state directly. Skips cleanly when Postgres is unreachable.
"""
from __future__ import annotations

import pytest

from forge_bridge.core.traits import SYSTEM_REL_KEYS
from forge_bridge.store.repo import RegistryRepo


async def test_restore_seeds_builtins_when_db_lacks_them(session_factory):
    """ensure_builtins() heals a DB missing the protected built-ins, and a
    restore afterwards resolves every system relationship type by canonical key.
    """
    # Pre-heal: a fresh (migrations-modelled) DB has no built-in rel types,
    # so restore_registry cannot resolve them — this is the reported bug.
    async with session_factory() as session:
        reg = await RegistryRepo(session).restore_registry()
    for name in SYSTEM_REL_KEYS:
        assert name not in reg.relationships.names()

    # Heal — exactly what app.start() now does on every startup.
    async with session_factory() as session:
        await RegistryRepo(session).ensure_builtins()
        await session.commit()

    # Post-heal: every system type resolves, and to its canonical UUID.
    async with session_factory() as session:
        reg = await RegistryRepo(session).restore_registry()
    for name, key in SYSTEM_REL_KEYS.items():
        assert reg.relationships.get_key(name) == key


async def test_ensure_builtins_is_idempotent(session_factory):
    """Running the heal twice neither errors nor duplicates rows — the upsert
    matches on the canonical UUID key (name has a UNIQUE constraint)."""
    async with session_factory() as session:
        await RegistryRepo(session).ensure_builtins()
        await session.commit()
    async with session_factory() as session:
        await RegistryRepo(session).ensure_builtins()
        await session.commit()

    async with session_factory() as session:
        types = await RegistryRepo(session).load_all_relationship_types()

    names = [t.name for t in types]
    # No duplicate rows for any built-in despite two heal passes.
    for name in SYSTEM_REL_KEYS:
        assert names.count(name) == 1
