"""Slice B (#160) — fitted-model revocation state + fail-closed inference gate.

Two proofs:

  1. ``revoke_asset`` flips ``attributes.revoked_at`` / ``revocation_reason`` and
     emits an ``asset.revoked`` event, and is idempotent on re-revoke (stays
     revoked, no error, no duplicate event).

  2. The fail-closed gate at the dispatch submit chokepoint: an envelope naming a
     REVOKED fitted-model refuses with ``model_revoked`` and NEVER calls
     ``driver.submit``; a MISSING model refuses with ``model_not_found``; a live
     (non-revoked) model passes the gate and reaches submit; and an envelope
     with ``fitted_model_asset_id=None`` no-ops the gate (existing behavior
     preserved — the no-regression property).

The model gate sits AFTER the GenerationGrant spend-gate, so every gate proof
supplies a ratified grant to clear the grant guard first, isolating the model
gate's behavior.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from forge_contracts.references import ArtifactRef

from forge_bridge.core import Asset, Project, Registry, Status
from forge_bridge.orchestration.dispatcher import (
    DispatchResult,
    InvocationEnvelope,
    dispatch_envelope,
)
from forge_bridge.orchestration.drivers import (
    DriverSubmitResult,
    GenerationDriverRegistry,
)
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
from forge_bridge.store.repo import EntityRepo, EventRepo, ProjectRepo, revoke_asset

pytestmark = pytest.mark.asyncio

_TRIPLE = {"surface": "test", "path": "gate_backend", "revision": "v1"}


class _CountingDriver:
    backend_identity_triple = _TRIPLE

    def __init__(self) -> None:
        self.submits: list[InvocationEnvelope] = []

    async def submit(self, invocation: InvocationEnvelope) -> DriverSubmitResult:
        self.submits.append(invocation)
        return DriverSubmitResult(
            request_id=f"req-{len(self.submits)}",
            submitted_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
            raw_response_summary={},
        )

    async def poll(self, request_id: str):  # pragma: no cover - unused
        raise NotImplementedError


def _registry() -> tuple[GenerationDriverRegistry, _CountingDriver]:
    driver = _CountingDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    return registry, driver


def _envelope(fitted_model_asset_id: uuid.UUID | None = None) -> InvocationEnvelope:
    return InvocationEnvelope(
        operator_id="generate_video_from_image",
        inputs=[ArtifactRef(artifact_id="src-1", artifact_type="artifact", metadata={})],
        backend_identity_triple=dict(_TRIPLE),
        fitted_model_asset_id=(
            str(fitted_model_asset_id) if fitted_model_asset_id is not None else None
        ),
    )


async def _events():
    log: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        log.append((event_type, payload))

    return log, append


async def _ratified_grant(session_factory) -> str:
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).propose(
            operator_id="generate_video_from_image",
            backend_identity_triple=_TRIPLE,
            estimated_cost={"currency": "USD", "amount": 1.0},
            run_kind="generation",
        )
        await session.commit()
        grant_id = grant.grant_id
    async with session_factory() as session:
        await GenerationGrantRepo(session).ratify(grant_id, actor="op")
        await session.commit()
    return grant_id


async def _fitted_model(session_factory, *, revoked: bool = False) -> uuid.UUID:
    project = Project(name="Gate FM", code=f"GFM{uuid.uuid4().hex[:8]}")
    model = Asset(
        name="m.fitted",
        asset_type="fitted-model",
        project_id=project.id,
        status=Status.APPROVED,
    )
    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        await EntityRepo(session, Registry.default()).save(model, project.id)
        await session.commit()
    if revoked:
        async with session_factory() as session:
            did = await revoke_asset(session, model.id, "consent withdrawn")
            await session.commit()
        assert did is True
    return model.id


async def _dispatch(session_factory, registry, append, envelope, **kw) -> DispatchResult:
    return await dispatch_envelope(
        envelope,
        provenance={"planned_output_artifact_id": None},
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        **kw,
    )


# ── revoke_asset state + idempotency ──────────────────────────────────────


async def test_revoke_asset_sets_state_and_emits_event(session_factory):
    model_id = await _fitted_model(session_factory)

    async with session_factory() as session:
        did = await revoke_asset(session, model_id, "consent withdrawn")
        await session.commit()
    assert did is True

    from forge_bridge.store.models import DBEntity

    async with session_factory() as session:
        db_entity = await session.get(DBEntity, model_id)
        assert db_entity.attributes.get("revoked_at")
        assert db_entity.attributes.get("revocation_reason") == "consent withdrawn"
        # Revocation stays OFF the shared Status enum — the flip is JSONB-only.
        assert db_entity.status == "approved"

        events = await EventRepo(session).get_recent(
            event_type="asset.revoked", entity_id=model_id
        )
        assert len(events) == 1
        assert events[0].payload["revocation_reason"] == "consent withdrawn"


async def test_revoke_asset_is_idempotent(session_factory):
    model_id = await _fitted_model(session_factory)

    async with session_factory() as session:
        first = await revoke_asset(session, model_id, "first reason")
        await session.commit()
    assert first is True

    async with session_factory() as session:
        second = await revoke_asset(session, model_id, "second reason")
        await session.commit()
    assert second is False  # already revoked — no-op

    from forge_bridge.store.models import DBEntity

    async with session_factory() as session:
        db_entity = await session.get(DBEntity, model_id)
        # Stays revoked; the original reason is preserved (no clobber).
        assert db_entity.attributes.get("revoked_at")
        assert db_entity.attributes.get("revocation_reason") == "first reason"

        # No duplicate event — exactly one asset.revoked across both calls.
        events = await EventRepo(session).get_recent(
            event_type="asset.revoked", entity_id=model_id
        )
        assert len(events) == 1


async def test_revoke_asset_missing_raises(session_factory):
    with pytest.raises(ValueError):
        async with session_factory() as session:
            await revoke_asset(session, uuid.uuid4(), "no such asset")


# ── fail-closed inference gate at the submit chokepoint ───────────────────


async def test_revoked_model_refuses_and_does_not_submit(session_factory):
    """A revoked fitted-model refuses with model_revoked; submit never runs."""
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory, revoked=True)

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(model_id),
        grant_id=grant_id,
    )

    assert result.status == "refused"
    assert result.refusal_code == "model_revoked"
    assert driver.submits == []  # fail-closed — submit NOT reached
    refusals = [payload for name, payload in log if name == "dispatch_model_refused"]
    assert len(refusals) == 1
    assert refusals[0]["refusal_code"] == "model_revoked"


async def test_falsy_present_revoked_at_still_refuses(session_factory):
    """A FALSY-but-present ``revoked_at`` (e.g. "") still refuses model_revoked.

    Locks the presence semantics (``is not None``) against a regression back to
    truthiness: a future writer (the #161 consent path) that stamps a falsy
    sentinel must NOT silently open the gate. Written directly on the row to
    simulate that writer — ``revoke_asset`` never emits a falsy sentinel.
    """
    from forge_bridge.store.models import DBEntity

    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory, revoked=False)

    async with session_factory() as session:
        db_entity = await session.get(DBEntity, model_id)
        attrs = dict(db_entity.attributes or {})
        attrs["revoked_at"] = ""  # falsy but PRESENT — a future writer's sentinel
        db_entity.attributes = attrs
        await session.commit()

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(model_id),
        grant_id=grant_id,
    )

    assert result.status == "refused"
    assert result.refusal_code == "model_revoked"
    assert driver.submits == []  # fail-closed — presence, not truthiness
    refusals = [payload for name, payload in log if name == "dispatch_model_refused"]
    assert len(refusals) == 1
    assert refusals[0]["refusal_code"] == "model_revoked"


async def test_missing_model_refuses_and_does_not_submit(session_factory):
    """An envelope naming an unknown asset refuses with model_not_found."""
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(uuid.uuid4()),
        grant_id=grant_id,
    )

    assert result.status == "refused"
    assert result.refusal_code == "model_not_found"
    assert driver.submits == []
    refusals = [payload for name, payload in log if name == "dispatch_model_refused"]
    assert len(refusals) == 1
    assert refusals[0]["refusal_code"] == "model_not_found"


async def test_live_model_passes_gate_and_reaches_submit(session_factory):
    """A live (non-revoked) fitted-model clears the gate and submits."""
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory, revoked=False)

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(model_id),
        grant_id=grant_id,
    )

    assert result.status == "submitted"
    assert result.artifact_id is not None
    assert len(driver.submits) == 1
    assert [name for name, _ in log if name == "dispatch_model_refused"] == []


async def test_no_model_id_noops_gate_and_submits(session_factory):
    """fitted_model_asset_id=None → gate no-ops; existing dispatch unchanged."""
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(None),
        grant_id=grant_id,
    )

    assert result.status == "submitted"
    assert len(driver.submits) == 1
    assert [name for name, _ in log if name == "dispatch_model_refused"] == []
