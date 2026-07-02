"""Phase 7 V2 — dispatch attaches to execution-stage entry."""

from __future__ import annotations

from sqlalchemy import select

from forge_bridge.orchestration import (
    DispatchOnExecutionEntryConsumer,
    GenerationDriverRegistry,
    GenerationPoller,
)
from forge_bridge.orchestration.replay import ReplayEngine
from forge_bridge.store.models import DBEntity, DBEvent
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo

from tests.test_phase7_generation_vertical import _TRIPLE, FaithfulLifecycleDriver
from tests.test_replay_engine import (
    _make_replay_engine,
    _replay_request,
    _seed_completed_source_run,
)


def _generation_capability() -> dict:
    return {
        "snapshots": [
            {
                "backend_identity_triple": _TRIPLE,
                "declaration_hash": "phase7-v2",
                "capabilities_opaque": {
                    "first_frame_guarantee": True,
                    "identity_lock_support": True,
                    "upload_support": True,
                    "acceptance_score": 0.95,
                    "estimated_cost": 1.0,
                },
            }
        ]
    }


async def test_replay_execution_entry_dispatches_automatically_and_polls_terminal(
    session_factory,
) -> None:
    driver = FaithfulLifecycleDriver()
    shared_registry = GenerationDriverRegistry()
    shared_registry.register_driver(driver)

    async with session_factory() as session:
        source = await _seed_completed_source_run(
            session,
            capability=_generation_capability(),
        )
        replay: ReplayEngine = _make_replay_engine(session)
        lifecycle = await replay.reconstruct(
            _replay_request(
                source_run_id=source["run_id"],
                kind="remediation",
                remediation_entry="new_attempt_same_plan",
            )
        )
        # #146: this proof drives replay.reconstruct DIRECTLY (bypassing
        # manual_qc.revise where the production grant-mint lives), then feeds the
        # run through the live dispatch consumer, now spend-gated at the
        # driver.submit() chokepoint. Mint + auto-ratify a grant and stamp
        # run.grant_id so the chokepoint resolves it via run_id and the
        # bridge-owned proof stays green (sibling of the daemon-runtime fix).
        from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
        from forge_bridge.store.models import DBEntity as _DBEntity

        grant_repo = GenerationGrantRepo(session)
        grant = await grant_repo.propose(
            operator_id="generate_video_from_image",
            backend_identity_triple=_TRIPLE,
            estimated_cost={"currency": "USD", "amount": 0.0},
            run_kind="attach-vertical-proof",
        )
        await grant_repo.ratify(grant.grant_id, actor="bridge:test")
        run_entity = await session.get(_DBEntity, lifecycle.run_id)
        if run_entity is not None:
            attrs = dict(run_entity.attributes or {})
            attrs["grant_id"] = grant.grant_id
            run_entity.attributes = attrs
        await session.commit()

    assert lifecycle.current_stage == "execution"
    assert lifecycle.plan_id == source["plan_id"]

    consumer = DispatchOnExecutionEntryConsumer(session_factory, shared_registry)
    results = await consumer.process_pending()

    dispatched = [r for r in results if r.action == "dispatched"]
    assert len(dispatched) == 1
    artifact_id = dispatched[0].artifact_id
    assert artifact_id is not None
    assert driver.submissions[0].backend_identity_triple == _TRIPLE

    async with session_factory() as session:
        artifact = await GenerationArtifactRepo(session).get_by_id(artifact_id)
        assert artifact is not None
        assert artifact.lifecycle_state == "submitted"
        assert artifact.execution_provenance["backend_identity_triple"] == _TRIPLE
        assert artifact.execution_provenance["request_id"] == "req-1"

    poll_result = await GenerationPoller(session_factory, shared_registry).poll_once()
    assert poll_result.terminal == 1
    assert driver.polled_request_ids == ["req-1"]

    async with session_factory() as session:
        terminal = await GenerationArtifactRepo(session).get_by_id(artifact_id)
        assert terminal is not None
        assert terminal.lifecycle_state == "complete"
        assert terminal.content_hash is not None

        event_rows = await session.execute(
            select(DBEvent).where(
                DBEvent.event_type.in_(
                    [
                        "dispatch_consumed",
                        "generation_dispatch_submitted",
                        "generation_artifact_terminal",
                    ]
                )
            )
        )
        event_types = {event.event_type for event in event_rows.scalars().all()}
        assert {
            "dispatch_consumed",
            "generation_dispatch_submitted",
            "generation_artifact_terminal",
        } <= event_types


async def test_execution_entry_with_unresolvable_backend_refuses_without_artifact(
    session_factory,
) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        replay = _make_replay_engine(session)
        lifecycle = await replay.reconstruct(
            _replay_request(
                source_run_id=source["run_id"],
                kind="remediation",
                remediation_entry="new_attempt_same_plan",
            )
        )
        await session.commit()

    assert lifecycle.current_stage == "execution"
    consumer = DispatchOnExecutionEntryConsumer(
        session_factory,
        GenerationDriverRegistry(),
    )
    results = await consumer.process_pending()

    refused = [r for r in results if r.action == "refused"]
    assert len(refused) == 1
    assert refused[0].refusal_code == "dispatch_no_driver"

    async with session_factory() as session:
        artifact_rows = await session.execute(
            select(DBEntity).where(DBEntity.entity_type == "orch_generation_artifact")
        )
        assert list(artifact_rows.scalars().all()) == []
        events = await session.execute(
            select(DBEvent).where(DBEvent.event_type == "dispatch_no_driver")
        )
        no_driver = list(events.scalars().all())
        assert len(no_driver) == 1
        assert no_driver[0].payload["backend_id"] == "test.backend"
