"""Direct-door advisory refusals are durable without spending authority.

``dispatch_generation`` may fail fast before the authoritative
``dispatch_envelope`` chokepoint. These tests exercise the production database
event appender so that both advisory checks remain visible without being
mistaken for the chokepoint's consume/model refusal events.
"""

from __future__ import annotations

import uuid

import pytest
from forge_contracts.references import ArtifactRef

from forge_bridge.core import Asset, Project, Registry, Status
from forge_bridge.orchestration import generation_entry
from forge_bridge.orchestration.dispatcher import InvocationEnvelope
from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
from forge_bridge.store.repo import EntityRepo, EventRepo, ProjectRepo, revoke_asset

pytestmark = pytest.mark.asyncio

_OPERATOR_ID = "generate_video_from_image"
_TRIPLE = {"surface": "test", "path": "advisory_audit", "revision": "v1"}


def _envelope(*, fitted_model_asset_id: uuid.UUID | None = None) -> InvocationEnvelope:
    return InvocationEnvelope(
        operator_id=_OPERATOR_ID,
        inputs=[ArtifactRef(artifact_id="src-1", artifact_type="artifact", metadata={})],
        backend_identity_triple=dict(_TRIPLE),
        fitted_model_asset_id=(
            str(fitted_model_asset_id) if fitted_model_asset_id is not None else None
        ),
    )


def _bind_runtime(monkeypatch, session_factory) -> None:
    monkeypatch.setattr(generation_entry, "_generation_driver_registry", None)
    generation_entry.set_generation_driver_registry(GenerationDriverRegistry())
    monkeypatch.setattr(
        generation_entry,
        "get_async_session_factory",
        lambda: session_factory,
    )


async def _proposed_grant(session_factory) -> str:
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).propose(
            operator_id=_OPERATOR_ID,
            backend_identity_triple=_TRIPLE,
            estimated_cost={"currency": "USD", "amount": 1.0},
            run_kind="generation",
        )
        await session.commit()
        return grant.grant_id


async def _ratified_grant(session_factory) -> str:
    grant_id = await _proposed_grant(session_factory)
    async with session_factory() as session:
        await GenerationGrantRepo(session).ratify(grant_id, actor="operator")
        await session.commit()
    return grant_id


async def _revoked_model(session_factory) -> uuid.UUID:
    project = Project(name="Advisory Audit", code=f"AA{uuid.uuid4().hex[:8]}")
    model = Asset(
        name="identity.fitted",
        asset_type="fitted-model",
        project_id=project.id,
        status=Status.APPROVED,
    )
    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        await EntityRepo(session, Registry.default()).save(model, project.id)
        await session.commit()
    async with session_factory() as session:
        assert await revoke_asset(session, model.id, "consent withdrawn") is True
        await session.commit()
    return model.id


async def _advisory_events(session_factory):
    async with session_factory() as session:
        return await EventRepo(session).get_recent(
            event_type="dispatch_advisory_refused"
        )


async def test_grant_advisory_refusal_is_durable_and_non_consuming(
    session_factory,
    monkeypatch,
) -> None:
    _bind_runtime(monkeypatch, session_factory)
    grant_id = await _proposed_grant(session_factory)

    result = await generation_entry.dispatch_generation(
        _envelope(),
        provenance={"planned_output_artifact_id": None},
        grant_id=grant_id,
    )

    assert result.status == "refused"
    assert result.refusal_code == "grant_not_ratified"
    events = await _advisory_events(session_factory)
    assert [event.payload for event in events] == [{
        "door": "dispatch_generation",
        "advisory_check": "generation_grant",
        "operator_id": _OPERATOR_ID,
        "refusal_code": "grant_not_ratified",
        "run_id": None,
    }]
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert grant is not None
        assert grant.status == "proposed"
        assert await EventRepo(session).get_recent(
            event_type="dispatch_grant_refused"
        ) == []


async def test_model_advisory_refusal_is_durable_and_leaves_grant_ratified(
    session_factory,
    monkeypatch,
) -> None:
    _bind_runtime(monkeypatch, session_factory)
    grant_id = await _ratified_grant(session_factory)
    model_id = await _revoked_model(session_factory)

    result = await generation_entry.dispatch_generation(
        _envelope(fitted_model_asset_id=model_id),
        provenance={"planned_output_artifact_id": None},
        grant_id=grant_id,
    )

    assert result.status == "refused"
    assert result.refusal_code == "model_revoked"
    events = await _advisory_events(session_factory)
    assert [event.payload for event in events] == [{
        "door": "dispatch_generation",
        "advisory_check": "fitted_model",
        "operator_id": _OPERATOR_ID,
        "refusal_code": "model_revoked",
        "run_id": None,
    }]
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert grant is not None
        assert grant.status == "ratified"
        assert await EventRepo(session).get_recent(
            event_type="dispatch_model_refused"
        ) == []
