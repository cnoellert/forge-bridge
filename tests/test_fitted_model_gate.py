"""Fitted-model revocation and lifecycle enforcement at generation dispatch.

Two proofs:

  1. ``revoke_asset`` flips ``attributes.revoked_at`` / ``revocation_reason`` and
     emits an ``asset.revoked`` event, and is idempotent on re-revoke (stays
     revoked, no error, no duplicate event).

  2. The fail-closed gate at the dispatch submit chokepoint rejects unavailable
     fitted models, latches successful use and provenance, and holds a model row
     lock so collection cannot race an in-flight submit.

The model gate sits AFTER the GenerationGrant spend-gate, so every gate proof
supplies a ratified grant to clear the grant guard first, isolating the model
gate's behavior.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

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
from forge_bridge.store.fitted_model_lifecycle_repo import (
    GC_COLLECTED,
    FittedModelLifecycleError,
    FittedModelLifecycleRepo,
)
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
from forge_bridge.store.models import DBEntity
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
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


class _BlockingDriver(_CountingDriver):
    def __init__(self) -> None:
        super().__init__()
        self.submit_entered = asyncio.Event()
        self.release_submit = asyncio.Event()

    async def submit(self, invocation: InvocationEnvelope) -> DriverSubmitResult:
        self.submit_entered.set()
        await self.release_submit.wait()
        return await super().submit(invocation)


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
    """A live fitted-model submits and records use plus exact provenance."""
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

    async with session_factory() as session:
        model = await session.get(DBEntity, model_id)
        artifact = await GenerationArtifactRepo(session).get_by_id(result.artifact_id)
        use_events = await EventRepo(session).get_recent(
            event_type="fitted_model.used", entity_id=model_id
        )

    assert model.attributes["last_used_at"]
    assert artifact.content_provenance["fitted_model_asset_id"] == str(model_id)
    assert (
        artifact.content_provenance["lineage"]["fitted_model_asset_id"]
        == str(model_id)
    )
    assert len(use_events) == 1
    assert use_events[0].payload["request_id"] == "req-1"


async def test_gc_marked_model_refuses_and_does_not_submit(session_factory):
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory)
    as_of = datetime(2026, 7, 11, tzinfo=timezone.utc)
    async with session_factory() as session:
        lifecycle = FittedModelLifecycleRepo(session)
        await lifecycle.set_retention(
            model_id,
            retention_until=as_of - timedelta(days=1),
            actor="operator",
        )
        await lifecycle.mark_gc(
            model_id,
            collect_after=as_of + timedelta(days=7),
            actor="operator",
            as_of=as_of,
        )
        await session.commit()

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(model_id),
        grant_id=grant_id,
    )

    assert result.refusal_code == "model_gc_pending"
    assert driver.submits == []
    assert next(
        payload for name, payload in log if name == "dispatch_model_refused"
    )["fitted_model_asset_id"] == str(model_id)


async def test_collected_model_refuses_and_does_not_submit(session_factory):
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory)
    async with session_factory() as session:
        model = await session.get(DBEntity, model_id)
        attrs = dict(model.attributes or {})
        attrs["gc_state"] = GC_COLLECTED
        model.attributes = attrs
        await session.commit()

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(model_id),
        grant_id=grant_id,
    )

    assert result.refusal_code == "model_collected"
    assert driver.submits == []


async def test_non_fitted_asset_id_fails_closed(session_factory):
    registry, driver = _registry()
    _log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    project = Project(name="Gate Asset", code=f"GA{uuid.uuid4().hex[:8]}")
    plate = Asset(name="plate", asset_type="plate", project_id=project.id)
    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        await EntityRepo(session, Registry.default()).save(plate, project.id)
        await session.commit()

    result = await _dispatch(
        session_factory,
        registry,
        append,
        _envelope(plate.id),
        grant_id=grant_id,
    )

    assert result.refusal_code == "model_not_found"
    assert driver.submits == []


async def test_gc_mark_waits_for_submit_and_observes_latched_use(session_factory):
    """The dispatch transaction owns the model lock through backend submit."""
    driver = _BlockingDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    _log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory)
    as_of = datetime.now(timezone.utc)
    async with session_factory() as session:
        await FittedModelLifecycleRepo(session).set_retention(
            model_id,
            retention_until=as_of - timedelta(days=1),
            actor="operator",
        )
        await session.commit()

    dispatch_task = asyncio.create_task(
        _dispatch(
            session_factory,
            registry,
            append,
            _envelope(model_id),
            grant_id=grant_id,
        )
    )
    await asyncio.wait_for(driver.submit_entered.wait(), timeout=2)

    async def mark_model() -> None:
        async with session_factory() as session:
            await FittedModelLifecycleRepo(session).mark_gc(
                model_id,
                collect_after=as_of + timedelta(days=7),
                actor="collector",
                as_of=as_of,
            )
            await session.commit()

    mark_task = asyncio.create_task(mark_model())
    await asyncio.sleep(0.1)
    assert not mark_task.done()

    driver.release_submit.set()
    result = await asyncio.wait_for(dispatch_task, timeout=2)
    assert result.status == "submitted"
    with pytest.raises(FittedModelLifecycleError) as exc:
        await asyncio.wait_for(mark_task, timeout=2)
    assert exc.value.code == "model_not_gc_eligible"


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
