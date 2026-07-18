"""Phase 7 V3 — daemon-started execution runtime."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from sqlalchemy import select

from forge_bridge.orchestration.replay import ReplayEngine
from forge_bridge.store.models import DBEntity, DBEvent
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)

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
                "declaration_hash": "phase7-v3",
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


async def _bootstrap_runtime(_mcp_server, session_factory, monkeypatch):
    from forge_bridge.orchestration.discovery import SiblingResolution

    monkeypatch.setattr(
        "forge_bridge.orchestration.discovery.resolve_siblings",
        lambda: SiblingResolution(
            siblings={},
            required_capability_kinds=frozenset(),
        ),
    )
    monkeypatch.setenv("FORGE_EXECUTION_RUNTIME_INTERVAL_SECONDS", "0.05")
    monkeypatch.setattr(
        _mcp_server,
        "_wait_for_bus",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        _mcp_server,
        "startup_bridge",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        _mcp_server,
        "shutdown_bridge",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        _mcp_server,
        "get_async_session_factory",
        lambda: session_factory,
    )
    monkeypatch.setattr(
        "forge_bridge.learning.watcher.watch_synthesized_tools",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        _mcp_server,
        "_start_console_task",
        AsyncMock(return_value=(None, None)),
    )
    return await _mcp_server.bootstrap_daemon(_mcp_server.mcp)


async def _trigger_replay_execution(session_factory, *, capability: dict | None = None):
    async with session_factory() as session:
        source = await _seed_completed_source_run(session, capability=capability)
        replay: ReplayEngine = _make_replay_engine(session)
        lifecycle = await replay.reconstruct(
            _replay_request(
                source_run_id=source["run_id"],
                kind="remediation",
                remediation_entry="new_attempt_same_plan",
            )
        )
        # #146: the daemon dispatch consumer gates generation spend at the
        # driver.submit() chokepoint via run.grant_id. This bridge-owned proof
        # mints + auto-ratifies a grant and stamps it on the replay run so the
        # live consumer path stays green. Real replay grant-inheritance stays
        # reserved for #142; here we stamp the run attributes directly.
        from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
        from forge_bridge.store.models import DBEntity as _DBEntity

        grant_repo = GenerationGrantRepo(session)
        grant = await grant_repo.propose(
            operator_id="generate_video_from_image",
            backend_identity_triple=_TRIPLE,
            estimated_cost={"currency": "USD", "amount": 0.0},
            run_kind="daemon-proof",
        )
        await grant_repo.ratify(grant.grant_id, actor="bridge:test")
        run_entity = await session.get(_DBEntity, lifecycle.run_id)
        if run_entity is not None:
            attrs = dict(run_entity.attributes or {})
            attrs["grant_id"] = grant.grant_id
            run_entity.attributes = attrs
        await session.commit()
    return source, lifecycle


async def _wait_until(assertion, *, timeout: float = 4.0) -> object:
    deadline = asyncio.get_running_loop().time() + timeout
    last_error: AssertionError | None = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            return await assertion()
        except AssertionError as exc:
            last_error = exc
            await asyncio.sleep(0.05)
    if last_error is not None:
        raise last_error
    raise AssertionError("condition did not become true")


async def test_daemon_runtime_round_trip_reaches_terminal_and_audit(
    session_factory,
    monkeypatch,
) -> None:
    from forge_bridge.mcp import server as _mcp_server

    result = await _bootstrap_runtime(_mcp_server, session_factory, monkeypatch)
    try:
        driver = FaithfulLifecycleDriver()
        # V3 establishes the runtime; it does not expand the federation. The
        # proof injects this stub into the bootstrap-owned registry only to
        # prove daemon lifecycle + orchestration, not real generator integration.
        result.generation_driver_registry.register_driver(driver)
        _source, lifecycle = await _trigger_replay_execution(
            session_factory,
            capability=_generation_capability(),
        )

        async def _audit_reached():
            async with session_factory() as session:
                current = await OrchestrationLifecycleStateRepo(
                    session
                ).get_by_run_id(lifecycle.run_id)
                assert current is not None
                assert current.current_stage == "audit"
                artifact_rows = await session.execute(
                    select(DBEntity).where(
                        DBEntity.entity_type == "orch_generation_artifact"
                    )
                )
                artifacts = list(artifact_rows.scalars().all())
                assert len(artifacts) == 1
                artifact = await GenerationArtifactRepo(session).get_by_id(
                    artifacts[0].id
                )
                assert artifact is not None
                assert artifact.lifecycle_state == "complete"
                assert artifact.execution_provenance["backend_identity_triple"] == _TRIPLE
                events = await session.execute(select(DBEvent))
                event_types = {event.event_type for event in events.scalars().all()}
                assert {
                    "dispatch_consumed",
                    "generation_dispatch_submitted",
                    "generation_artifact_terminal",
                    "engine_consumer_advanced",
                } <= event_types
                return artifact

        artifact = await _wait_until(_audit_reached)
        assert artifact.content_hash is not None
        assert driver.submissions
        assert driver.polled_request_ids == ["req-1"]
        assert not result.dispatch_consumer_task.done()
        assert not result.generation_poller_task.done()
        assert not result.terminal_consumer_task.done()
    finally:
        await _mcp_server.teardown_daemon(result)

    assert result.dispatch_consumer_task.done()
    assert result.generation_poller_task.done()
    assert result.terminal_consumer_task.done()


async def test_daemon_runtime_empty_registry_degrades_to_no_driver(
    session_factory,
    monkeypatch,
) -> None:
    from forge_bridge.mcp import server as _mcp_server

    result = await _bootstrap_runtime(_mcp_server, session_factory, monkeypatch)
    try:
        assert result.generation_driver_registry.registered_backends() == frozenset()
        await _trigger_replay_execution(session_factory)

        async def _no_driver_emitted():
            async with session_factory() as session:
                events = await session.execute(
                    select(DBEvent).where(DBEvent.event_type == "dispatch_no_driver")
                )
                no_driver = list(events.scalars().all())
                assert len(no_driver) == 1
                assert no_driver[0].payload["backend_id"] == "test.backend"
                artifact_rows = await session.execute(
                    select(DBEntity).where(
                        DBEntity.entity_type == "orch_generation_artifact"
                    )
                )
                assert list(artifact_rows.scalars().all()) == []
                return no_driver[0]

        await _wait_until(_no_driver_emitted)
        assert not result.dispatch_consumer_task.done()
        assert not result.generation_poller_task.done()
        assert not result.terminal_consumer_task.done()
    finally:
        await _mcp_server.teardown_daemon(result)
