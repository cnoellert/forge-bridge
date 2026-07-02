"""Spend-gate at the dispatch chokepoint (#146).

Fake-driver + synthetic envelope proofs that the GenerationGrant CAS consume
guards ``driver.submit()``: missing grant refuses, unratified refuses, ratified
submits once and flips the grant to consumed, replay refuses, and a no-anchor
call (run_id=None AND grant_id=None) refuses. On every refusal driver.submit
must NOT have been called.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from forge_contracts.references import ArtifactRef

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

_TRIPLE = {"surface": "test", "path": "gate_backend", "revision": "v1"}
_BACKEND_ID = "test.gate_backend"


class _CountingDriver:
    backend_identity_triple = _TRIPLE

    def __init__(self) -> None:
        self.submits: list[InvocationEnvelope] = []

    async def submit(self, invocation: InvocationEnvelope) -> DriverSubmitResult:
        self.submits.append(invocation)
        return DriverSubmitResult(
            request_id=f"req-{len(self.submits)}",
            submitted_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            raw_response_summary={},
        )

    async def poll(self, request_id: str):  # pragma: no cover - unused
        raise NotImplementedError


def _registry() -> tuple[GenerationDriverRegistry, _CountingDriver]:
    driver = _CountingDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    return registry, driver


def _envelope() -> InvocationEnvelope:
    return InvocationEnvelope(
        operator_id="generate_video_from_image",
        inputs=[ArtifactRef(artifact_id="src-1", artifact_type="artifact", metadata={})],
        backend_identity_triple=dict(_TRIPLE),
    )


async def _events():
    log: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        log.append((event_type, payload))

    return log, append


async def _proposed(session_factory) -> str:
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).propose(
            operator_id="generate_video_from_image",
            backend_identity_triple=_TRIPLE,
            estimated_cost={"currency": "USD", "amount": 1.0},
            run_kind="generation",
        )
        await session.commit()
        return grant.grant_id


async def _ratified(session_factory) -> str:
    grant_id = await _proposed(session_factory)
    async with session_factory() as session:
        await GenerationGrantRepo(session).ratify(grant_id, actor="op")
        await session.commit()
    return grant_id


async def _dispatch(session_factory, registry, append, **kw) -> DispatchResult:
    return await dispatch_envelope(
        _envelope(),
        provenance={"planned_output_artifact_id": None},
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        **kw,
    )


async def test_no_anchor_refuses(session_factory):
    """run_id=None AND grant_id=None → fail-closed refuse, no submit."""
    registry, driver = _registry()
    _log, append = await _events()
    result = await _dispatch(session_factory, registry, append)
    assert result.status == "refused"
    assert result.refusal_code == "grant_not_ratified"
    assert driver.submits == []


async def test_missing_grant_refuses(session_factory):
    """An unknown grant_id → refuse, no submit."""
    registry, driver = _registry()
    _log, append = await _events()
    result = await _dispatch(
        session_factory, registry, append, grant_id="ffffffffffff",
    )
    assert result.status == "refused"
    assert result.refusal_code == "grant_not_ratified"
    assert driver.submits == []


async def test_unratified_grant_refuses(session_factory):
    """A proposed-but-not-ratified grant → refuse, no submit."""
    registry, driver = _registry()
    _log, append = await _events()
    grant_id = await _proposed(session_factory)
    result = await _dispatch(session_factory, registry, append, grant_id=grant_id)
    assert result.status == "refused"
    assert result.refusal_code == "grant_not_ratified"
    assert driver.submits == []


async def test_ratified_grant_submits_once_and_consumes(session_factory):
    """A ratified grant submits exactly once and flips to consumed."""
    registry, driver = _registry()
    _log, append = await _events()
    grant_id = await _ratified(session_factory)

    result = await _dispatch(session_factory, registry, append, grant_id=grant_id)
    assert result.status == "submitted"
    assert result.artifact_id is not None
    assert len(driver.submits) == 1

    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert grant is not None
        assert grant.status == "consumed"
        assert grant.consumed_at is not None


async def test_replay_on_consumed_grant_refuses(session_factory):
    """Re-submitting on a consumed grant → refuse with grant_consumed, no 2nd submit."""
    registry, driver = _registry()
    _log, append = await _events()
    grant_id = await _ratified(session_factory)

    first = await _dispatch(session_factory, registry, append, grant_id=grant_id)
    assert first.status == "submitted"
    assert len(driver.submits) == 1

    second = await _dispatch(session_factory, registry, append, grant_id=grant_id)
    assert second.status == "refused"
    assert second.refusal_code == "grant_consumed"
    assert len(driver.submits) == 1  # NOT called again


async def test_run_grant_id_resolution_gates_planner_door(session_factory):
    """A grant resolved via run.grant_id (no explicit kwarg) gates + consumes."""
    from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo

    registry, driver = _registry()
    _log, append = await _events()
    grant_id = await _ratified(session_factory)

    async with session_factory() as session:
        run = await PipelineRunRepo(session).insert_if_absent(
            {"run_kind": "gate-test", "intent_id": str(uuid.uuid4()), "grant_id": grant_id}
        )
        await session.commit()
        run_id = run.id

    result = await _dispatch(session_factory, registry, append, run_id=run_id)
    assert result.status == "submitted"
    assert len(driver.submits) == 1

    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert grant.status == "consumed"
