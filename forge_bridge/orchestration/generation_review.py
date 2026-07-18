"""Human visual review and approved-artifact conditioning for generation.

This is the bounded manual storyboard seam from forge-bridge#66. It records one
append-only human decision per generated artifact. A correction reuses the
existing typed ``qc_correction`` author replay; an approval permits that exact
still to be persisted as the conditioning input for a video author run.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from forge_contracts.references import ArtifactRef
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from forge_bridge.orchestration import manual_qc
from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.orchestration.errors import PlannerRefusalError
from forge_bridge.orchestration.registration import ToolRegistry
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.repo import EventRepo
from forge_bridge.store.session import get_async_session_factory

REVIEW_EVENT_TYPE = "generation_visual_review_decided"
VIDEO_FROM_IMAGE_OPERATOR = "generate_video_from_image"


@dataclass(frozen=True)
class GenerationReviewResult:
    generation_artifact_id: uuid.UUID
    decision: Literal["approved", "correction"]
    actor: str
    media_url: str
    source_author_artifact_id: uuid.UUID
    event_id: uuid.UUID | None = None
    revised_run_id: uuid.UUID | None = None
    revised_author_artifact_id: uuid.UUID | None = None
    idempotent: bool = False

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        for key in (
            "generation_artifact_id",
            "source_author_artifact_id",
            "event_id",
            "revised_run_id",
            "revised_author_artifact_id",
        ):
            value = body[key]
            body[key] = str(value) if value is not None else None
        return body


@dataclass(frozen=True)
class _ReviewableGeneration:
    artifact_id: uuid.UUID
    lifecycle_state: str
    operator_id: str
    media_url: str
    media_content_sha256: str | None
    content_hash: str
    source_author_artifact_id: uuid.UUID
    source_author_run_id: uuid.UUID


async def review_generation(
    generation_artifact_id: uuid.UUID | str,
    *,
    note: str | None = None,
    approve: bool = False,
    actor: str = "operator",
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    driver_registry: GenerationDriverRegistry | None = None,
    event_appender: Callable[[str, dict], Awaitable[None]] | None = None,
) -> GenerationReviewResult:
    """Approve a terminal generated artifact or author a corrected prompt.

    Exactly one decision is accepted for each generated artifact. Approval is
    idempotent and returns the original decision. A correction creates a new
    author run and leaves the rejected media immutable as evidence.
    """

    artifact_id = _parse_uuid(generation_artifact_id, "generation_artifact_id")
    clean_actor = actor.strip()
    if not clean_actor:
        raise ValueError("actor must be a non-empty string")
    clean_note = note.strip() if isinstance(note, str) else None
    if approve and clean_note:
        raise ValueError("omit note when approving a generated artifact")
    if not approve and not clean_note:
        raise ValueError("note is required unless approve is true")

    factory = session_factory or get_async_session_factory()
    async with factory() as session:
        generation = await _load_reviewable_generation(
            session,
            artifact_id,
            for_update=True,
        )
        existing = await _existing_review(session, artifact_id)
        if existing is not None:
            payload = existing.payload if isinstance(existing.payload, dict) else {}
            if approve and payload.get("decision") == "approved":
                return _result_from_event(existing, generation, idempotent=True)
            raise PlannerRefusalError(
                "generation_already_reviewed",
                f"generation artifact {artifact_id} already has a human decision",
            )
        if approve and generation.lifecycle_state != "complete":
            raise PlannerRefusalError(
                "partial_generation_not_approvable",
                f"generation artifact {artifact_id} is {generation.lifecycle_state!r}",
            )

        if not approve:
            assert clean_note is not None
            revised = await manual_qc.revise(
                generation.source_author_run_id,
                clean_note,
                session_factory=factory,
                driver_registry=driver_registry,
                event_appender=event_appender,
                source_generation_artifact_id=artifact_id,
            )
            payload = {
                "generation_artifact_id": str(artifact_id),
                "decision": "correction",
                "actor": clean_actor,
                "note": clean_note,
                "media_url": generation.media_url,
                "generation_content_hash": generation.content_hash,
                "source_author_artifact_id": str(
                    generation.source_author_artifact_id
                ),
                "source_author_run_id": str(generation.source_author_run_id),
                "revised_run_id": str(revised.run_id),
                "revised_author_artifact_id": str(revised.artifact_id),
            }
        else:
            payload = {
                "generation_artifact_id": str(artifact_id),
                "decision": "approved",
                "actor": clean_actor,
                "media_url": generation.media_url,
                "media_content_sha256": generation.media_content_sha256,
                "generation_content_hash": generation.content_hash,
                "source_author_artifact_id": str(
                    generation.source_author_artifact_id
                ),
                "source_author_run_id": str(generation.source_author_run_id),
            }

        event = await EventRepo(session).append(
            REVIEW_EVENT_TYPE,
            payload,
            client_name=clean_actor,
            entity_id=artifact_id,
        )
        await session.commit()
        await session.refresh(event)
        return _result_from_event(event, generation)


async def start_conditioned_video_author(
    intent: str,
    approved_still_artifact_id: uuid.UUID | str,
    *,
    target_backend: str | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    driver_registry: GenerationDriverRegistry | None = None,
    event_appender: Callable[[str, dict], Awaitable[None]] | None = None,
    data_root: Path | None = None,
    tool_registry: ToolRegistry | None = None,
) -> manual_qc.ManualQCResult:
    """Author motion for one exact human-approved generated still."""

    artifact_id = _parse_uuid(
        approved_still_artifact_id,
        "approved_still_artifact_id",
    )
    factory = session_factory or get_async_session_factory()
    async with factory() as session:
        generation = await _load_reviewable_generation(session, artifact_id)
        review = await _existing_review(session, artifact_id)
        payload = review.payload if review is not None else None
        if not isinstance(payload, dict) or payload.get("decision") != "approved":
            raise PlannerRefusalError(
                "generation_not_approved",
                f"generation artifact {artifact_id} has no human approval",
            )
        if payload.get("generation_content_hash") != generation.content_hash:
            raise PlannerRefusalError(
                "generation_review_stale",
                f"generation artifact {artifact_id} no longer matches its approval",
            )
        if generation.lifecycle_state != "complete":
            raise PlannerRefusalError(
                "partial_generation_not_approvable",
                f"generation artifact {artifact_id} is {generation.lifecycle_state!r}",
            )
        if generation.operator_id != "generate_still":
            raise PlannerRefusalError(
                "conditioning_artifact_not_still",
                f"generation artifact {artifact_id} came from {generation.operator_id!r}",
            )

        metadata: dict[str, Any] = {
            "role": "structural",
            "url": generation.media_url,
            "carry_to_make": True,
            "human_review_event_id": str(review.id),
            "human_review_actor": str(payload.get("actor") or "operator"),
            "human_review_content_hash": generation.content_hash,
            "source_generation_artifact_id": str(artifact_id),
        }
        if generation.media_content_sha256:
            metadata["content_sha256"] = generation.media_content_sha256
        conditioning_ref = ArtifactRef(
            artifact_id=str(artifact_id),
            artifact_type="image",
            metadata=metadata,
        )

    return await manual_qc.start_author(
        intent,
        session_factory=factory,
        driver_registry=driver_registry,
        event_appender=event_appender,
        data_root=data_root,
        target_operator=VIDEO_FROM_IMAGE_OPERATOR,
        target_backend=target_backend,
        conditioning_references=[conditioning_ref],
        tool_registry=tool_registry,
    )


async def _load_reviewable_generation(
    session: AsyncSession,
    artifact_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> _ReviewableGeneration:
    repo = GenerationArtifactRepo(session)
    artifact = (
        await repo.get_by_id_for_update(artifact_id)
        if for_update
        else await repo.get_by_id(artifact_id)
    )
    if artifact is None:
        raise PlannerRefusalError(
            "generation_artifact_missing",
            f"generation artifact {artifact_id} missing",
        )
    lifecycle = str(artifact.lifecycle_state or "")
    if lifecycle not in {"complete", "partial"}:
        raise PlannerRefusalError(
            "generation_artifact_not_reviewable",
            f"generation artifact {artifact_id} is {lifecycle!r}",
        )
    if not isinstance(artifact.content_hash, str) or not artifact.content_hash:
        raise PlannerRefusalError(
            "generation_content_unsealed",
            f"generation artifact {artifact_id} has no terminal content hash",
        )
    execution = (
        artifact.execution_provenance
        if isinstance(artifact.execution_provenance, dict)
        else {}
    )
    media_url = execution.get("media_url")
    if not isinstance(media_url, str) or not media_url:
        raise PlannerRefusalError(
            "generation_media_missing",
            f"generation artifact {artifact_id} has no reviewable media URL",
        )
    content = (
        artifact.content_provenance
        if isinstance(artifact.content_provenance, dict)
        else {}
    )
    operator_id = content.get("operator_id")
    if not isinstance(operator_id, str) or not operator_id:
        raise PlannerRefusalError(
            "generation_provenance_missing",
            f"generation artifact {artifact_id} has no operator provenance",
        )
    source_author_id = _parse_uuid(
        content.get("source_author_artifact_id"),
        "source_author_artifact_id",
    )
    source_author = await GenerationArtifactRepo(session).get_by_id(source_author_id)
    if source_author is None or source_author.lifecycle_state != "complete":
        raise PlannerRefusalError(
            "source_author_artifact_missing",
            f"generation artifact {artifact_id} has no complete author source",
        )
    return _ReviewableGeneration(
        artifact_id=artifact_id,
        lifecycle_state=lifecycle,
        operator_id=operator_id,
        media_url=media_url,
        media_content_sha256=(
            str(execution["media_content_sha256"])
            if execution.get("media_content_sha256")
            else None
        ),
        content_hash=artifact.content_hash,
        source_author_artifact_id=source_author_id,
        source_author_run_id=_parse_uuid(source_author.run_id, "source_author_run_id"),
    )


async def _existing_review(session: AsyncSession, artifact_id: uuid.UUID):
    events = await EventRepo(session).get_recent(
        event_type=REVIEW_EVENT_TYPE,
        entity_id=artifact_id,
        limit=1,
    )
    return events[0] if events else None


def _result_from_event(
    event: Any,
    generation: _ReviewableGeneration,
    *,
    idempotent: bool = False,
) -> GenerationReviewResult:
    payload = event.payload if isinstance(event.payload, dict) else {}
    decision = payload.get("decision")
    if decision not in {"approved", "correction"}:
        raise RuntimeError(f"invalid generation review decision {decision!r}")
    return GenerationReviewResult(
        generation_artifact_id=generation.artifact_id,
        decision=decision,
        actor=str(payload.get("actor") or "operator"),
        media_url=generation.media_url,
        source_author_artifact_id=generation.source_author_artifact_id,
        event_id=event.id,
        revised_run_id=(
            _parse_uuid(payload["revised_run_id"], "revised_run_id")
            if payload.get("revised_run_id")
            else None
        ),
        revised_author_artifact_id=(
            _parse_uuid(
                payload["revised_author_artifact_id"],
                "revised_author_artifact_id",
            )
            if payload.get("revised_author_artifact_id")
            else None
        ),
        idempotent=idempotent,
    )


def _parse_uuid(value: uuid.UUID | str | None, field: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a UUID") from exc
