"""Phase 4B Step 4 — GenerationArtifactRepo lifecycle carve-out tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from forge_bridge.store.content_addressed_repo import (
    ContentAddressedRepo,
    ImmutableArtifactError,
)
from forge_bridge.store.orch_generation_artifact_repo import (
    GenerationArtifactRepo,
    InvalidTransitionError,
)


def _generation_body(**overrides) -> dict:
    body = {
        "platform_locators": {"output": "https://cdn.example/video.mp4"},
        "content_provenance": {"reference_inputs": []},
        "execution_provenance": {"request_id": "req-1"},
        "run_id": str(uuid.uuid4()),
        "polling_history": [],
    }
    body.update(overrides)
    return body


async def test_insert_submitted(session_factory) -> None:
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        artifact = await repo.insert_submitted(_generation_body())
        await session.commit()

        assert artifact.lifecycle_state == "submitted"
        assert artifact.content_hash is None
        assert artifact.polling_history == []


async def test_transition_to_polling_appends_history(session_factory) -> None:
    event = {"status": "polling", "at": "2026-05-28T12:00:00Z"}

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        artifact = await repo.insert_submitted(_generation_body())
        await session.commit()
        artifact_id = artifact.id

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        updated = await repo.transition(artifact_id, "polling", polling_event=event)
        await session.commit()

        assert updated.lifecycle_state == "polling"
        assert updated.content_hash is None
        assert updated.polling_history == [event]


async def test_transition_to_complete_seals_content_hash(session_factory) -> None:
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        artifact = await repo.insert_submitted(_generation_body())
        artifact_id = artifact.id
        await repo.transition(artifact_id, "polling", polling_event={"tick": 1})
        sealed = await repo.transition(artifact_id, "complete")
        await session.commit()

        assert sealed.lifecycle_state == "complete"
        assert sealed.content_hash is not None

        expected_hash = ContentAddressedRepo._canonical_hash(sealed.attributes)
        assert sealed.content_hash == expected_hash


async def test_transition_from_terminal_raises_immutable(session_factory) -> None:
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        artifact = await repo.insert_submitted(_generation_body())
        artifact_id = artifact.id
        await repo.transition(artifact_id, "complete")
        await session.commit()

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        with pytest.raises(ImmutableArtifactError) as exc:
            await repo.transition(artifact_id, "polling")
        assert "transition" in str(exc.value)


async def test_transition_invalid_state_raises(session_factory) -> None:
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        artifact = await repo.insert_submitted(_generation_body())
        artifact_id = artifact.id

        with pytest.raises(InvalidTransitionError):
            await repo.transition(artifact_id, "not_a_real_state")


async def test_get_by_content_hash_terminal_only(session_factory) -> None:
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        in_flight = await repo.insert_submitted(_generation_body())
        in_flight_id = in_flight.id
        await session.commit()
        assert await repo.get_by_content_hash("0" * 64) is None

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        sealed = await repo.transition(in_flight_id, "complete")
        await session.commit()
        content_hash = sealed.content_hash
        assert content_hash is not None

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        found = await repo.get_by_content_hash(content_hash)
        assert found is not None
        assert found.id == in_flight_id


async def test_find_non_terminal(session_factory) -> None:
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        submitted = await repo.insert_submitted(_generation_body())
        polling_body = _generation_body(run_id=str(uuid.uuid4()))
        polling = await repo.insert_submitted(polling_body)
        await repo.transition(polling.id, "polling")
        terminal_body = _generation_body(run_id=str(uuid.uuid4()))
        terminal = await repo.insert_submitted(terminal_body)
        await repo.transition(terminal.id, "failed")
        await session.commit()

        submitted_id = submitted.id
        polling_id = polling.id
        terminal_id = terminal.id

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        non_terminal = await repo.find_non_terminal()
        ids = {row.id for row in non_terminal}
        assert submitted_id in ids
        assert polling_id in ids
        assert terminal_id not in ids


async def test_get_by_idempotency_key(session_factory) -> None:
    body = _generation_body(
        idempotency_key="generation-key-1",
        idempotency_fingerprint="fingerprint-1",
    )
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        inserted = await repo.insert_submitted(body)
        await session.commit()

    async with session_factory() as session:
        found = await GenerationArtifactRepo(session).get_by_idempotency_key(
            "generation-key-1"
        )

    assert found is not None
    assert found.id == inserted.id
    assert found.idempotency_key == "generation-key-1"
    assert found.idempotency_fingerprint == "fingerprint-1"


async def test_idempotency_key_is_unique_for_generation_artifacts(
    session_factory,
) -> None:
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        await repo.insert_submitted(_generation_body(
            idempotency_key="generation-key-1",
            idempotency_fingerprint="fingerprint-1",
        ))
        await session.commit()

    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        with pytest.raises(IntegrityError):
            await repo.insert_submitted(_generation_body(
                idempotency_key="generation-key-1",
                idempotency_fingerprint="fingerprint-1",
            ))
