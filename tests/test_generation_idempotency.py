"""#141 generation dispatch idempotency across both doors and concurrency."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from forge_contracts.references import ArtifactRef

from forge_bridge.orchestration import generation_entry
from forge_bridge.orchestration.discovery import make_db_event_appender
from forge_bridge.orchestration.dispatcher import (
    InvocationEnvelope,
    dispatch_envelope,
    dispatch_plan,
)
from forge_bridge.orchestration.drivers import (
    DriverSubmitResult,
    GenerationDriverRegistry,
)
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.repo import EventRepo

pytestmark = pytest.mark.asyncio

_OPERATOR_ID = "generate_video_from_image"
_TRIPLE = {"surface": "test", "path": "idempotency", "revision": "v1"}
_BACKEND_ID = "test.idempotency"


class _CountingDriver:
    backend_identity_triple = _TRIPLE

    def __init__(self, *, submit_delay: float = 0.0) -> None:
        self.submit_delay = submit_delay
        self.submissions: list[InvocationEnvelope] = []

    async def submit(self, invocation: InvocationEnvelope) -> DriverSubmitResult:
        self.submissions.append(invocation)
        if self.submit_delay:
            await asyncio.sleep(self.submit_delay)
        return DriverSubmitResult(
            request_id=f"request-{len(self.submissions)}",
            submitted_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
            raw_response_summary={},
        )

    async def poll(self, request_id: str):  # pragma: no cover - unused
        raise NotImplementedError


def _registry(*, submit_delay: float = 0.0):
    driver = _CountingDriver(submit_delay=submit_delay)
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    return registry, driver


def _envelope(*, prompt: str = "product hero") -> InvocationEnvelope:
    return InvocationEnvelope(
        operator_id=_OPERATOR_ID,
        inputs=[ArtifactRef(
            artifact_id="source-1",
            artifact_type="image",
            metadata={"prompt": prompt},
        )],
        backend_identity_triple=dict(_TRIPLE),
    )


async def _ratified_grant(session_factory) -> str:
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).propose(
            operator_id=_OPERATOR_ID,
            backend_identity_triple=_TRIPLE,
            estimated_cost={"currency": "USD", "amount": 1.0},
            run_kind="generation",
        )
        await session.commit()
        grant_id = grant.grant_id
    async with session_factory() as session:
        await GenerationGrantRepo(session).ratify(grant_id, actor="operator")
        await session.commit()
    return grant_id


async def _grant_statuses(session_factory, *grant_ids: str) -> list[str]:
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        grants = [await repo.get_by_grant_id(grant_id) for grant_id in grant_ids]
    assert all(grant is not None for grant in grants)
    return [grant.status for grant in grants if grant is not None]


def _bind_direct_runtime(monkeypatch, session_factory, registry) -> None:
    monkeypatch.setattr(generation_entry, "_generation_driver_registry", None)
    generation_entry.set_generation_driver_registry(registry)
    monkeypatch.setattr(
        generation_entry,
        "get_async_session_factory",
        lambda: session_factory,
    )


async def test_planner_artifact_is_reused_by_direct_door_before_grant_spend(
    session_factory,
    monkeypatch,
) -> None:
    registry, driver = _registry()
    _bind_direct_runtime(monkeypatch, session_factory, registry)
    first_grant = await _ratified_grant(session_factory)
    retry_grant = await _ratified_grant(session_factory)
    envelope = _envelope()
    plan = SimpleNamespace(
        id=uuid.uuid4(),
        operator_sequence=[{
            "operator_id": envelope.operator_id,
            "backend_id": _BACKEND_ID,
            "inputs": list(envelope.inputs),
            "output_artifact_id": "planned-output-1",
        }],
    )
    key = "cross-door-key"

    planned = await dispatch_plan(
        plan,
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=make_db_event_appender(session_factory),
        grant_id=first_grant,
        idempotency_key=key,
    )
    consumed_grant_retry = await generation_entry.dispatch_generation(
        envelope,
        provenance={"origin": "direct_tool"},
        grant_id=first_grant,
        idempotency_key=key,
    )
    fresh_grant_retry = await generation_entry.dispatch_generation(
        envelope,
        provenance={"origin": "direct_tool"},
        grant_id=retry_grant,
        idempotency_key=key,
    )

    assert (
        planned.status
        == consumed_grant_retry.status
        == fresh_grant_retry.status
        == "submitted"
    )
    assert (
        planned.artifact_id
        == consumed_grant_retry.artifact_id
        == fresh_grant_retry.artifact_id
    )
    assert len(driver.submissions) == 1
    assert await _grant_statuses(
        session_factory, first_grant, retry_grant
    ) == ["consumed", "ratified"]
    async with session_factory() as session:
        artifact = await GenerationArtifactRepo(session).get_by_id(planned.artifact_id)
        events = await EventRepo(session).get_recent(
            event_type="generation_dispatch_deduplicated"
        )
    assert artifact is not None
    assert artifact.idempotency_key == key
    assert artifact.idempotency_fingerprint is not None
    assert len(events) == 2
    assert {event.payload["artifact_id"] for event in events} == {
        str(planned.artifact_id)
    }
    async with session_factory() as session:
        submitted = await EventRepo(session).get_recent(
            event_type="generation_dispatch_submitted"
        )
    assert len(submitted) == 1
    assert submitted[0].payload["idempotency_key"] == key


async def test_same_key_for_different_invocation_refuses_without_spend(
    session_factory,
) -> None:
    registry, driver = _registry()
    first_grant = await _ratified_grant(session_factory)
    conflict_grant = await _ratified_grant(session_factory)
    events: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    first = await dispatch_envelope(
        _envelope(prompt="product hero"),
        provenance={"origin": "direct_tool"},
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        grant_id=first_grant,
        idempotency_key="conflicting-key",
    )
    conflict = await dispatch_envelope(
        _envelope(prompt="different work"),
        provenance={"origin": "direct_tool"},
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        grant_id=conflict_grant,
        idempotency_key="conflicting-key",
    )

    assert first.status == "submitted"
    assert conflict.status == "refused"
    assert conflict.refusal_code == "idempotency_conflict"
    assert len(driver.submissions) == 1
    assert await _grant_statuses(
        session_factory, first_grant, conflict_grant
    ) == ["consumed", "ratified"]
    conflicts = [
        payload
        for name, payload in events
        if name == "generation_dispatch_idempotency_conflict"
    ]
    assert len(conflicts) == 1
    assert conflicts[0]["artifact_id"] == str(first.artifact_id)
    assert conflicts[0]["stored_fingerprint"] != conflicts[0][
        "requested_fingerprint"
    ]


async def test_concurrent_same_key_submits_once_and_preserves_second_grant(
    session_factory,
) -> None:
    registry, driver = _registry(submit_delay=0.05)
    first_grant = await _ratified_grant(session_factory)
    second_grant = await _ratified_grant(session_factory)
    events: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    async def run(grant_id: str):
        return await dispatch_envelope(
            _envelope(),
            provenance={"origin": "concurrency_test"},
            driver_registry=registry,
            session_factory=session_factory,
            event_appender=append,
            grant_id=grant_id,
            idempotency_key="concurrent-key",
        )

    first, second = await asyncio.gather(run(first_grant), run(second_grant))

    assert first.status == second.status == "submitted"
    assert first.artifact_id == second.artifact_id
    assert len(driver.submissions) == 1
    assert sorted(await _grant_statuses(
        session_factory, first_grant, second_grant
    )) == ["consumed", "ratified"]
    assert [name for name, _ in events].count(
        "generation_dispatch_submitted"
    ) == 1
    assert [name for name, _ in events].count(
        "generation_dispatch_deduplicated"
    ) == 1


async def test_keyless_calls_preserve_independent_submit_behavior(
    session_factory,
) -> None:
    registry, driver = _registry()
    first_grant = await _ratified_grant(session_factory)
    second_grant = await _ratified_grant(session_factory)

    async def append(_event_type: str, _payload: dict) -> None:
        return None

    first = await dispatch_envelope(
        _envelope(),
        provenance={"origin": "keyless_test"},
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        grant_id=first_grant,
    )
    second = await dispatch_envelope(
        _envelope(),
        provenance={"origin": "keyless_test"},
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        grant_id=second_grant,
    )

    assert first.status == second.status == "submitted"
    assert first.artifact_id != second.artifact_id
    assert len(driver.submissions) == 2
