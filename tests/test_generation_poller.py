"""Tests for GenerationPoller and driver registry (Phase 4B Step 7)."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from forge_bridge.orchestration.drivers import (
    DriverPollResult,
    GenerationDriverRegistry,
    resolve_backend_id,
)
from forge_bridge.orchestration.errors import (
    DuplicateGenerationDriverError,
    GenerationDriverBackendIdMismatchError,
    MissingGenerationDriverBackendIdError,
)
from forge_bridge.orchestration.worker import GenerationPoller, PollPassResult
from forge_bridge.store.models import DBEvent
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.repo import EventRepo

MOCK_BACKEND_ID = "test.mock_backend"


def _artifact_body(**overrides) -> dict:
    body = {
        "platform_locators": {"output": "https://cdn.example/video.mp4"},
        "content_provenance": {"reference_inputs": []},
        "execution_provenance": {
            "request_id": "req-1",
            "backend_identity_triple": {
                "surface": "test",
                "path": "mock_backend",
                "auth_mechanism": "api-key",
                "revision": "v1",
            },
        },
        "run_id": str(uuid.uuid4()),
        "polling_history": [],
    }
    body.update(overrides)
    return body


class MockGenerationDriver:
    backend_id = MOCK_BACKEND_ID

    def __init__(
        self,
        *,
        results: DriverPollResult | list[DriverPollResult] | None = None,
        per_artifact: dict[uuid.UUID, DriverPollResult] | None = None,
        poll_error: Exception | None = None,
        poll_errors_for: set[uuid.UUID] | None = None,
    ) -> None:
        self._results = results
        self._per_artifact = per_artifact or {}
        self._poll_error = poll_error
        self._poll_errors_for = poll_errors_for or set()
        self._sequence_index: dict[uuid.UUID, int] = {}
        self.polled_artifact_ids: list[uuid.UUID] = []

    async def poll(self, artifact):
        self.polled_artifact_ids.append(artifact.id)
        if artifact.id in self._poll_errors_for:
            raise RuntimeError("backend timeout")
        if self._poll_error is not None:
            raise self._poll_error

        if artifact.id in self._per_artifact:
            return self._per_artifact[artifact.id]

        if isinstance(self._results, list):
            idx = self._sequence_index.get(artifact.id, 0)
            if idx >= len(self._results):
                return self._results[-1]
            result = self._results[idx]
            self._sequence_index[artifact.id] = idx + 1
            return result

        if self._results is not None:
            return self._results

        return DriverPollResult(
            next_state="polling",
            polling_event={
                "ts": "2026-05-28T12:00:00Z",
                "backend_status": "running",
                "response_summary": "default",
            },
        )


async def _insert_artifact(session, *, state: str = "submitted", **body_overrides):
    repo = GenerationArtifactRepo(session)
    artifact = await repo.insert_submitted(_artifact_body(**body_overrides))
    if state != "submitted":
        artifact = await repo.transition(artifact.id, state)
    await session.commit()
    return artifact


async def _events_for_artifact(session, artifact_id: uuid.UUID) -> list[DBEvent]:
    result = await session.execute(
        select(DBEvent)
        .where(DBEvent.entity_id == artifact_id)
        .order_by(DBEvent.occurred_at.asc())
    )
    return list(result.scalars().all())


# ── driver registry ───────────────────────────────────────────────────────────


def test_registry_register_and_lookup() -> None:
    registry = GenerationDriverRegistry()
    driver = MockGenerationDriver()
    registry.register_driver(driver)
    assert registry.get_driver(MOCK_BACKEND_ID) is driver
    assert registry.registered_backends() == frozenset({MOCK_BACKEND_ID})
    assert registry.get_driver("missing") is None


def test_registry_duplicate_backend_id_raises() -> None:
    registry = GenerationDriverRegistry()
    first = MockGenerationDriver(results=DriverPollResult("polling", {"tick": 1}))
    second = MockGenerationDriver(results=DriverPollResult("complete", {"tick": 2}))
    registry.register_driver(first)
    with pytest.raises(DuplicateGenerationDriverError):
        registry.register_driver(second)
    assert registry.get_driver(MOCK_BACKEND_ID) is first


def test_registry_rejects_triple_backend_id_disagreement() -> None:
    class MismatchedDriver(MockGenerationDriver):
        backend_id = "legacy.wrong"
        backend_identity_triple = {
            "surface": "test",
            "path": "mock_backend",
        }

    registry = GenerationDriverRegistry()
    with pytest.raises(GenerationDriverBackendIdMismatchError):
        registry.register_driver(MismatchedDriver())


def test_registry_accepts_backend_identity_triple_only_driver() -> None:
    class TripleOnlyDriver:
        backend_identity_triple = {
            "surface": "test",
            "path": "mock_backend",
        }

        async def poll(self, artifact):
            return None

    driver = TripleOnlyDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    assert registry.get_driver(MOCK_BACKEND_ID) is driver


def test_registry_rejects_driver_without_key() -> None:
    class NoBackendDriver:
        async def poll(self, artifact):
            return None

    registry = GenerationDriverRegistry()
    with pytest.raises(MissingGenerationDriverBackendIdError):
        registry.register_driver(NoBackendDriver())


def test_resolve_backend_id_from_triple() -> None:
    from forge_bridge.store.orch_entity_views import DBOrchGenerationArtifact
    from forge_bridge.store.models import DBEntity

    entity = DBEntity(
        id=uuid.uuid4(),
        entity_type="orch_generation_artifact",
        status="submitted",
        attributes=_artifact_body(),
    )
    artifact = DBOrchGenerationArtifact.from_entity(entity)
    assert resolve_backend_id(artifact) == MOCK_BACKEND_ID


# ── single artifact scripted polls ──────────────────────────────────────────


async def test_poll_once_submitted_to_polling(session_factory) -> None:
    registry = GenerationDriverRegistry()
    registry.register_driver(
        MockGenerationDriver(
            results=DriverPollResult(
                next_state="polling",
                polling_event={
                    "ts": "2026-05-28T12:00:00Z",
                    "backend_status": "running",
                    "response_summary": "still running",
                },
            )
        )
    )
    poller = GenerationPoller(session_factory, registry)

    async with session_factory() as session:
        artifact = await _insert_artifact(session)
        artifact_id = artifact.id

    result = await poller.poll_once()
    assert result == PollPassResult(
        processed=1, transitioned=1, terminal=0, errors=0, no_driver=0
    )

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        updated = await repo.get_by_id(artifact_id)
        assert updated is not None
        assert updated.lifecycle_state == "polling"
        assert len(updated.polling_history) == 1
        events = await _events_for_artifact(session, artifact_id)
        assert not any(e.event_type == "generation_artifact_terminal" for e in events)


async def test_poll_once_to_complete_emits_terminal_event(session_factory) -> None:
    run_id = str(uuid.uuid4())
    terminal_provenance = {"completion_timestamp": "2026-05-28T12:05:00Z"}
    registry = GenerationDriverRegistry()
    registry.register_driver(
        MockGenerationDriver(
            results=DriverPollResult(
                next_state="complete",
                polling_event={
                    "ts": "2026-05-28T12:05:00Z",
                    "backend_status": "complete",
                    "response_summary": "done",
                },
                terminal_provenance=terminal_provenance,
            )
        )
    )
    poller = GenerationPoller(session_factory, registry)

    async with session_factory() as session:
        artifact = await _insert_artifact(session, run_id=run_id)
        artifact_id = artifact.id

    result = await poller.poll_once()
    assert result.terminal == 1

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        updated = await repo.get_by_id(artifact_id)
        assert updated is not None
        assert updated.lifecycle_state == "complete"
        assert updated.content_hash is not None
        events = await _events_for_artifact(session, artifact_id)
        terminal_events = [
            e for e in events if e.event_type == "generation_artifact_terminal"
        ]
        assert len(terminal_events) == 1
        payload = terminal_events[0].payload
        assert payload["artifact_id"] == str(artifact_id)
        assert payload["run_id"] == run_id
        assert payload["terminal_state"] == "complete"
        assert payload["terminal_provenance"] == terminal_provenance


async def test_poll_once_partial_carries_fidelity_report(session_factory) -> None:
    report = {"dimensions": [{"axis": "motion", "scalar": 0.8}]}
    registry = GenerationDriverRegistry()
    registry.register_driver(
        MockGenerationDriver(
            results=DriverPollResult(
                next_state="partial",
                polling_event={
                    "ts": "2026-05-28T12:05:00Z",
                    "backend_status": "partial",
                    "response_summary": "partial output",
                },
                partial_fidelity_report=report,
            )
        )
    )
    poller = GenerationPoller(session_factory, registry)

    async with session_factory() as session:
        artifact = await _insert_artifact(session)
        artifact_id = artifact.id

    await poller.poll_once()

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        updated = await repo.get_by_id(artifact_id)
        assert updated is not None
        assert updated.lifecycle_state == "partial"
        assert updated.partial_fidelity_report == report
        events = await _events_for_artifact(session, artifact_id)
        terminal = next(
            e for e in events if e.event_type == "generation_artifact_terminal"
        )
        assert terminal.payload["partial_fidelity_report"] == report


# ── multiple artifacts ───────────────────────────────────────────────────────


async def test_poll_once_multiple_artifacts_isolated(session_factory) -> None:
    registry = GenerationDriverRegistry()
    registry.register_driver(
        MockGenerationDriver(
            per_artifact={},
        )
    )
    driver = registry.get_driver(MOCK_BACKEND_ID)
    assert driver is not None

    async with session_factory() as session:
        a1 = await _insert_artifact(session)
        a2 = await _insert_artifact(session)
        a3 = await _insert_artifact(session)
        driver._per_artifact[a1.id] = DriverPollResult(  # type: ignore[attr-defined]
            "polling",
            {"artifact": "a1", "backend_status": "running", "response_summary": "1"},
        )
        driver._per_artifact[a2.id] = DriverPollResult(  # type: ignore[attr-defined]
            "complete",
            {"artifact": "a2", "backend_status": "complete", "response_summary": "2"},
            terminal_provenance={"done": True},
        )
        driver._per_artifact[a3.id] = DriverPollResult(  # type: ignore[attr-defined]
            "failed",
            {"artifact": "a3", "backend_status": "failed", "response_summary": "3"},
            terminal_provenance={"error": "boom"},
        )

    poller = GenerationPoller(session_factory, registry)
    result = await poller.poll_once()
    assert result == PollPassResult(
        processed=3, transitioned=3, terminal=2, errors=0, no_driver=0
    )

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        u1 = await repo.get_by_id(a1.id)
        u2 = await repo.get_by_id(a2.id)
        u3 = await repo.get_by_id(a3.id)
        assert u1 is not None and u1.lifecycle_state == "polling"
        assert u2 is not None and u2.lifecycle_state == "complete"
        assert u3 is not None and u3.lifecycle_state == "failed"
        assert u1.polling_history[0]["artifact"] == "a1"
        assert u2.polling_history[0]["artifact"] == "a2"
        assert u3.polling_history[0]["artifact"] == "a3"


# ── no driver / driver error ──────────────────────────────────────────────────


async def test_poll_once_no_driver_records_event(session_factory) -> None:
    poller = GenerationPoller(session_factory, GenerationDriverRegistry())

    async with session_factory() as session:
        artifact = await _insert_artifact(
            session,
            execution_provenance={
                "request_id": "req-1",
                "backend_identity_triple": {
                    "surface": "unknown",
                    "path": "backend",
                    "auth_mechanism": "api-key",
                    "revision": "v1",
                },
            },
        )
        artifact_id = artifact.id

    result = await poller.poll_once()
    assert result.no_driver == 1

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        unchanged = await repo.get_by_id(artifact_id)
        assert unchanged is not None
        assert unchanged.lifecycle_state == "submitted"
        events = await _events_for_artifact(session, artifact_id)
        assert len(events) == 1
        assert events[0].event_type == "generation_artifact_no_driver"
        assert events[0].payload["backend_id"] == "unknown.backend"


async def test_poll_once_driver_error_other_artifacts_continue(session_factory) -> None:
    registry = GenerationDriverRegistry()
    registry.register_driver(MockGenerationDriver())

    async with session_factory() as session:
        failing = await _insert_artifact(session)
        ok = await _insert_artifact(session)
        driver = registry.get_driver(MOCK_BACKEND_ID)
        assert isinstance(driver, MockGenerationDriver)
        driver._poll_errors_for = {failing.id}

    poller = GenerationPoller(session_factory, registry)
    result = await poller.poll_once()
    assert result.errors == 1
    assert result.transitioned == 1

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        failed = await repo.get_by_id(failing.id)
        succeeded = await repo.get_by_id(ok.id)
        assert failed is not None and failed.lifecycle_state == "submitted"
        assert succeeded is not None and succeeded.lifecycle_state == "polling"
        error_events = await _events_for_artifact(session, failing.id)
        assert error_events[0].event_type == "generation_artifact_polling_error"
        assert error_events[0].payload["exception_type"] == "RuntimeError"


# ── atomicity ───────────────────────────────────────────────────────────────


async def test_poll_once_rolls_back_when_terminal_event_append_fails(
    session_factory,
) -> None:
    registry = GenerationDriverRegistry()
    registry.register_driver(
        MockGenerationDriver(
            results=DriverPollResult(
                next_state="complete",
                polling_event={"backend_status": "complete", "response_summary": "x"},
                terminal_provenance={"done": True},
            )
        )
    )
    poller = GenerationPoller(session_factory, registry)

    async with session_factory() as session:
        artifact = await _insert_artifact(session, state="polling")
        artifact_id = artifact.id
        ok_id = (await _insert_artifact(session, state="polling")).id

    real_append = EventRepo.append
    terminal_append_calls = {"count": 0}

    async def append_fail_on_terminal(self, event_type, payload, **kwargs):
        if event_type == "generation_artifact_terminal":
            terminal_append_calls["count"] += 1
            if terminal_append_calls["count"] == 1:
                raise RuntimeError("terminal event write failed")
        return await real_append(self, event_type, payload, **kwargs)

    with patch.object(EventRepo, "append", append_fail_on_terminal):
        result = await poller.poll_once()

    assert result.processed == 2
    assert result.errors == 1
    assert result.terminal == 1

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        rolled_back = await repo.get_by_id(artifact_id)
        unaffected = await repo.get_by_id(ok_id)
        assert rolled_back is not None
        assert rolled_back.lifecycle_state == "polling"
        assert rolled_back.polling_history == []
        assert unaffected is not None
        assert unaffected.lifecycle_state == "complete"
        events = await _events_for_artifact(session, artifact_id)
        assert events == []


# ── find_non_terminal filtering / empty pass ─────────────────────────────────


async def test_poll_once_only_visits_non_terminal_artifacts(session_factory) -> None:
    registry = GenerationDriverRegistry()
    driver = MockGenerationDriver()
    registry.register_driver(driver)
    poller = GenerationPoller(session_factory, registry)

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        submitted = await repo.insert_submitted(_artifact_body())
        polling = await repo.insert_submitted(_artifact_body())
        await repo.transition(polling.id, "polling")
        for terminal_state in ("complete", "partial", "failed", "cancelled"):
            terminal = await repo.insert_submitted(_artifact_body())
            await repo.transition(terminal.id, terminal_state)
        await session.commit()
        submitted_id = submitted.id
        polling_id = polling.id

    await poller.poll_once()

    assert set(driver.polled_artifact_ids) == {submitted_id, polling_id}


async def test_poll_once_empty_pass(session_factory) -> None:
    driver = MockGenerationDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    poller = GenerationPoller(session_factory, registry)

    result = await poller.poll_once()
    assert result == PollPassResult(
        processed=0, transitioned=0, terminal=0, errors=0, no_driver=0
    )
    assert driver.polled_artifact_ids == []


# ── run_forever shutdown ──────────────────────────────────────────────────────


async def test_run_forever_shutdown_cleanly(session_factory) -> None:
    registry = GenerationDriverRegistry()
    registry.register_driver(MockGenerationDriver())
    poller = GenerationPoller(
        session_factory,
        registry,
        poll_interval_seconds=0.05,
    )
    shutdown = asyncio.Event()

    async with session_factory() as session:
        await _insert_artifact(session)

    task = asyncio.create_task(poller.run_forever(shutdown_event=shutdown))
    await asyncio.sleep(0.02)
    shutdown.set()
    await asyncio.wait_for(task, timeout=1.0)

    async with session_factory() as session:
        result = await session.execute(select(DBEvent))
        events = list(result.scalars().all())
        for event in events:
            assert event.event_type
            assert event.payload is not None
