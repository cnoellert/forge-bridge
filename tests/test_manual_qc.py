from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from forge_contracts import (
    AuthoringTarget,
    BackendIdentityTriple,
    GenerationCapabilityFacts,
)

from forge_bridge.orchestration.drivers import (
    DriverPollResult,
    DriverSubmitResult,
    GenerationDriverRegistry,
)
from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.manual_qc import (
    approve,
    make_approved,
    revise,
    start_author,
)
from forge_bridge.orchestration.dispatcher import InvocationEnvelope
from forge_bridge.orchestration.errors import PlannerRefusalError
from forge_bridge.orchestration.generation_review import (
    REVIEW_EVENT_TYPE,
    review_generation,
    start_conditioned_video_author,
)
from forge_bridge.orchestration.replay import RUN_LINEAGE_REL_KEYS
from forge_bridge.orchestration.registration import ToolRegistration, ToolRegistry
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.repo import EventRepo, RelationshipRepo
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo


_TRIPLE = {
    "surface": "ollama-api",
    "path": "llama3.2",
    "revision": "llama3.2",
}
_BACKEND_ID = "ollama-api.llama3.2"
_AUTHORING_TARGET = AuthoringTarget(
    operator_id="generate_video_from_image",
    backend_identity_triple=BackendIdentityTriple(
        surface="comfyui",
        path="seedance_2_0",
        auth_mechanism="local",
        revision="r5",
    ),
)
_STILL_TARGET = AuthoringTarget(
    operator_id="generate_still",
    backend_identity_triple=BackendIdentityTriple(
        surface="higgsfield-cli",
        path="nano_banana_2",
        auth_mechanism="device-flow-bearer",
        revision="nano_banana_2",
    ),
)


class _AuthorDriver:
    backend_id = _BACKEND_ID
    backend_identity_triple = _TRIPLE

    def __init__(self) -> None:
        self.submissions: list[InvocationEnvelope] = []
        self._text_by_request: dict[str, str] = {}

    async def submit(self, invocation: InvocationEnvelope) -> DriverSubmitResult:
        self.submissions.append(invocation)
        request_id = f"req-{len(self.submissions)}"
        correction = _correction_from(invocation)
        text = "draft one" if correction is None else f"draft two: {correction}"
        self._text_by_request[request_id] = text
        return DriverSubmitResult(
            request_id=request_id,
            submitted_at=datetime(2026, 6, 16, tzinfo=timezone.utc),
            raw_response_summary={"accepted": True},
        )

    async def poll(self, artifact: Any) -> DriverPollResult:
        request_id = artifact.execution_provenance["request_id"]
        return DriverPollResult(
            next_state="complete",
            polling_event={"raw_status": "complete", "request_id": request_id},
            terminal_provenance={
                "request_id": request_id,
                "text": self._text_by_request[request_id],
            },
        )


class _TargetDriver:
    backend_identity_triple = _AUTHORING_TARGET.backend_identity_triple.model_dump(
        mode="json"
    )
    backend_id = "comfyui.seedance_2_0"

    def __init__(self) -> None:
        self.submissions: list[InvocationEnvelope] = []

    async def submit(self, invocation: InvocationEnvelope) -> DriverSubmitResult:
        self.submissions.append(invocation)
        return DriverSubmitResult(
            request_id=f"target-{len(self.submissions)}",
            submitted_at=datetime(2026, 6, 16, tzinfo=timezone.utc),
            raw_response_summary={"accepted": True},
        )

    async def poll(self, _artifact):  # pragma: no cover - target is not rendered here
        raise NotImplementedError


def _correction_from(invocation: InvocationEnvelope) -> str | None:
    for ref in invocation.inputs:
        note = ref.metadata.get("qc_correction")
        if isinstance(note, str):
            return note
    return None


async def _events():
    events: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    return events, append


async def _ratified_target_grant(session_factory) -> str:
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        grant = await repo.propose(
            operator_id=_AUTHORING_TARGET.operator_id,
            backend_identity_triple=(
                _AUTHORING_TARGET.backend_identity_triple.model_dump(mode="json")
            ),
            estimated_cost={"currency": "USD", "amount": 0.25},
            run_kind="manual_qc_make",
        )
        await repo.ratify(grant.grant_id, actor="human-reviewer")
        await session.commit()
        return grant.grant_id


async def _insert_generated_still(
    session_factory,
    *,
    source_author_artifact_id,
    source_run_id,
    state: str = "complete",
):
    async with session_factory() as session:
        repo = GenerationArtifactRepo(session)
        artifact = await repo.insert_submitted(
            {
                "name": "generated-still",
                "platform_locators": {},
                "content_provenance": {
                    "operator_id": "generate_still",
                    "source_author_artifact_id": str(source_author_artifact_id),
                    "lineage": {
                        "source_author_artifact_id": str(source_author_artifact_id)
                    },
                },
                "execution_provenance": {
                    "backend_identity_triple": (
                        _STILL_TARGET.backend_identity_triple.model_dump(mode="json")
                    ),
                    "request_id": "still-request-1",
                },
                "run_id": str(source_run_id),
                "polling_history": [],
            }
        )
        artifact = await repo.transition(
            artifact.id,
            state,
            terminal_provenance={
                "media_url": "https://cdn.example/approved-still.png",
                "media_content_sha256": "a" * 64,
                "media_kind": "image",
            },
        )
        await session.commit()
        return artifact


def _registry(driver: _AuthorDriver) -> GenerationDriverRegistry:
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    return registry


def _target_catalog(registry: GenerationDriverRegistry) -> ToolRegistry:
    tools = ToolRegistry(generation_driver_registry=registry)
    tools.register(
        ToolRegistration(
            tool_id="forge_generators.generate_video_from_image.comfyui.seedance_2_0",
            family="generation",
            payload_family="generation.test",
            schema={"type": "object"},
            capabilities={
                "operator_id": _AUTHORING_TARGET.operator_id,
                "generation_facts": GenerationCapabilityFacts(
                    backend_identity=_AUTHORING_TARGET.backend_identity_triple
                ).model_dump(mode="json"),
            },
        ),
        sibling_name="test-generators",
    )
    return tools


async def test_manual_qc_author_revise_and_approve_round_trip(session_factory, tmp_path):
    driver = _AuthorDriver()
    events, append = await _events()

    first = await start_author(
        "make a moody one-line beat",
        session_factory=session_factory,
        driver_registry=_registry(driver),
        event_appender=append,
        data_root=tmp_path,
        authoring_target=_AUTHORING_TARGET,
    )

    assert first.text == "draft one"
    assert first.lifecycle_stage == "execution"
    assert first.lifecycle_status == "paused"
    assert first.authoring_target == _AUTHORING_TARGET.model_dump(mode="json")
    assert driver.submissions[0].inputs[0].metadata["scalars"]["target"] == (
        _AUTHORING_TARGET.model_dump(mode="json")
    )

    async with session_factory() as session:
        lifecycle = await OrchestrationLifecycleStateRepo(session).get_by_run_id(
            first.run_id
        )
        assert lifecycle is not None
        assert lifecycle.block["decision_type"] == "approve_remediation"
        # The live daemon's terminal consumer advances completed generation runs
        # to audit while preserving the manual-QC pause block. ReplayEngine must
        # still treat that as a valid remediation source.
        await GraphEngine(session).transition(first.run_id, to_stage="audit")
        await session.commit()

    second = await revise(
        first.run_id,
        "make the subject more specific",
        session_factory=session_factory,
        driver_registry=_registry(driver),
        event_appender=append,
    )

    assert second.run_id != first.run_id
    assert second.text == "draft two: make the subject more specific"
    assert len(driver.submissions) == 2
    assert _correction_from(driver.submissions[1]) == "make the subject more specific"
    assert second.authoring_target == _AUTHORING_TARGET.model_dump(mode="json")
    assert driver.submissions[1].inputs[0].metadata["scalars"]["target"] == (
        _AUTHORING_TARGET.model_dump(mode="json")
    )

    async with session_factory() as session:
        edges = await RelationshipRepo(session).get_outgoing(
            second.run_id,
            RUN_LINEAGE_REL_KEYS["remediates_run"],
        )
        assert len(edges) == 1
        assert edges[0].target_id == first.run_id

    accepted = await approve(first.run_id, session_factory=session_factory)
    assert accepted.lifecycle_stage == "audit"
    assert accepted.lifecycle_status == "active"

    async with session_factory() as session:
        lifecycle = await OrchestrationLifecycleStateRepo(session).get_by_run_id(
            first.run_id
        )
        assert lifecycle is not None
        assert lifecycle.block is None

    event_names = {name for name, _payload in events}
    assert "generation_dispatch_submitted" in event_names


async def test_manual_qc_start_requires_author_driver(session_factory):
    events, append = await _events()
    try:
        await start_author(
            "make something",
            session_factory=session_factory,
            driver_registry=GenerationDriverRegistry(),
            event_appender=append,
        )
    except RuntimeError as exc:
        assert "no local (ollama-api) author_prompt driver registered" in str(exc)
    else:  # pragma: no cover - assertion helper
        raise AssertionError("expected missing author driver failure")


async def test_manual_qc_resolves_target_from_discovered_catalog(
    session_factory,
    tmp_path,
):
    author_driver = _AuthorDriver()
    registry = _registry(author_driver)
    registry.register_driver(_TargetDriver())

    result = await start_author(
        "author motion for this beat",
        session_factory=session_factory,
        driver_registry=registry,
        tool_registry=_target_catalog(registry),
        event_appender=(await _events())[1],
        data_root=tmp_path,
        target_operator="generate_video_from_image",
        target_backend="comfyui.seedance_2_0",
    )

    assert result.authoring_target == _AUTHORING_TARGET.model_dump(mode="json")
    assert author_driver.submissions[0].inputs[0].metadata["scalars"]["target"] == (
        _AUTHORING_TARGET.model_dump(mode="json")
    )


async def test_manual_qc_rejects_malformed_authoring_target_before_runtime(
    session_factory,
):
    with pytest.raises(ValueError, match="forge-contracts AuthoringTarget"):
        await start_author(
            "make something",
            session_factory=session_factory,
            authoring_target={"operator_id": "generate_still"},
        )


async def test_manual_qc_rejects_unpaired_injected_tool_registry(session_factory):
    with pytest.raises(ValueError, match="matching driver_registry"):
        await start_author(
            "make something",
            session_factory=session_factory,
            tool_registry=ToolRegistry(),
        )


async def test_manual_qc_make_uses_approved_prompt_exact_target_and_grant(
    session_factory,
    tmp_path,
):
    author_driver = _AuthorDriver()
    target_driver = _TargetDriver()
    registry = _registry(author_driver)
    registry.register_driver(target_driver)
    events, append = await _events()
    authored = await start_author(
        "author motion for this beat",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
        data_root=tmp_path,
        authoring_target=_AUTHORING_TARGET,
    )
    grant_id = await _ratified_target_grant(session_factory)

    with pytest.raises(PlannerRefusalError, match="has not been approved"):
        await make_approved(
            authored.artifact_id,
            grant_id,
            session_factory=session_factory,
            driver_registry=registry,
            event_appender=append,
        )

    async with session_factory() as session:
        unspent = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert unspent is not None
        assert unspent.status == "ratified"

    await approve(authored.run_id, session_factory=session_factory, actor="reviewer")
    start_image = {
        "artifact_id": "approved-still",
        "artifact_type": "image",
        "metadata": {
            "role": "structural",
            "url": "https://cdn.example/approved-still.png",
        },
    }
    made = await make_approved(
        authored.artifact_id,
        grant_id,
        scalars={"duration_seconds": 5},
        references=[start_image],
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
    )

    assert made.status == "submitted"
    assert made.artifact_id is not None
    assert made.operator_id == _AUTHORING_TARGET.operator_id
    assert made.backend_identity_triple == (
        _AUTHORING_TARGET.backend_identity_triple.model_dump(mode="json")
    )
    assert made.poll_with == "forge_generation_status"
    assert len(target_driver.submissions) == 1
    invocation = target_driver.submissions[0]
    assert invocation.operator_id == _AUTHORING_TARGET.operator_id
    assert invocation.backend_identity_triple == made.backend_identity_triple
    assert invocation.inputs[0].artifact_id == "approved-still"
    assert invocation.inputs[0].metadata["prompt"] == authored.text
    assert invocation.inputs[0].metadata["scalars"] == {"duration_seconds": 5}
    assert invocation.inputs[0].metadata["authored_prompt_artifact_id"] == str(
        authored.artifact_id
    )

    async with session_factory() as session:
        spent = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert spent is not None
        assert spent.status == "consumed"
        artifact = await GenerationArtifactRepo(session).get_by_id(made.artifact_id)
        assert artifact is not None
        assert artifact.content_provenance["source_author_artifact_id"] == str(
            authored.artifact_id
        )
        assert artifact.content_provenance["lineage"][
            "source_author_artifact_id"
        ] == str(authored.artifact_id)

    replay = await make_approved(
        authored.artifact_id,
        grant_id,
        scalars={"duration_seconds": 5},
        references=[start_image],
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
    )
    assert replay.artifact_id == made.artifact_id
    assert len(target_driver.submissions) == 1
    assert any(name == "manual_qc_make_resolved" for name, _payload in events)


async def test_generated_still_correction_reauthors_with_typed_source(
    session_factory,
    tmp_path,
):
    author_driver = _AuthorDriver()
    registry = _registry(author_driver)
    events, append = await _events()
    authored = await start_author(
        "a car crosses a wet bridge",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
        data_root=tmp_path,
        authoring_target=_STILL_TARGET,
    )
    await approve(authored.run_id, session_factory=session_factory)
    still = await _insert_generated_still(
        session_factory,
        source_author_artifact_id=authored.artifact_id,
        source_run_id=authored.run_id,
    )

    review = await review_generation(
        still.id,
        note="keep the bridge visible behind the car",
        actor="reviewer",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
    )

    assert review.decision == "correction"
    assert review.revised_run_id is not None
    assert review.revised_author_artifact_id is not None
    correction = next(
        ref
        for ref in author_driver.submissions[-1].inputs
        if ref.artifact_type == "qc_correction"
    )
    assert correction.metadata["qc_correction"] == (
        "keep the bridge visible behind the car"
    )
    assert correction.metadata["source_generation_artifact_id"] == str(still.id)

    with pytest.raises(PlannerRefusalError, match="already has a human decision"):
        await review_generation(
            still.id,
            approve=True,
            session_factory=session_factory,
        )


async def test_approved_still_is_persisted_and_carried_into_video_make(
    session_factory,
    tmp_path,
):
    author_driver = _AuthorDriver()
    target_driver = _TargetDriver()
    registry = _registry(author_driver)
    registry.register_driver(target_driver)
    tools = _target_catalog(registry)
    events, append = await _events()
    still_author = await start_author(
        "a car crosses a wet bridge",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
        data_root=tmp_path,
        authoring_target=_STILL_TARGET,
    )
    await approve(still_author.run_id, session_factory=session_factory)
    still = await _insert_generated_still(
        session_factory,
        source_author_artifact_id=still_author.artifact_id,
        source_run_id=still_author.run_id,
    )
    approved = await review_generation(
        still.id,
        approve=True,
        actor="reviewer",
        session_factory=session_factory,
    )
    approved_retry = await review_generation(
        still.id,
        approve=True,
        actor="reviewer",
        session_factory=session_factory,
    )
    assert approved.decision == "approved"
    assert approved_retry.event_id == approved.event_id
    assert approved_retry.idempotent is True

    video_author = await start_conditioned_video_author(
        "the camera tracks beside the moving car",
        still.id,
        target_backend="comfyui.seedance_2_0",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
        data_root=tmp_path,
        tool_registry=tools,
    )
    assert video_author.authoring_target == _AUTHORING_TARGET.model_dump(mode="json")
    assert video_author.conditioning_artifact_ids == (str(still.id),)
    conditioning = next(
        ref
        for ref in author_driver.submissions[-1].inputs
        if ref.artifact_id == str(still.id)
    )
    assert conditioning.metadata["carry_to_make"] is True
    assert conditioning.metadata["url"] == (
        "https://cdn.example/approved-still.png"
    )
    assert conditioning.metadata["human_review_content_hash"] == still.content_hash

    await approve(video_author.run_id, session_factory=session_factory)
    grant_id = await _ratified_target_grant(session_factory)
    made = await make_approved(
        video_author.artifact_id,
        grant_id,
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=append,
    )
    assert made.status == "submitted"
    assert len(target_driver.submissions) == 1
    submitted = target_driver.submissions[0]
    assert submitted.inputs[0].artifact_id == str(still.id)
    assert submitted.inputs[0].metadata["url"] == (
        "https://cdn.example/approved-still.png"
    )
    assert submitted.inputs[0].metadata["prompt"] == video_author.text


async def test_video_author_refuses_unapproved_still(
    session_factory,
    tmp_path,
):
    author_driver = _AuthorDriver()
    target_driver = _TargetDriver()
    registry = _registry(author_driver)
    registry.register_driver(target_driver)
    still_author = await start_author(
        "a car crosses a wet bridge",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=(await _events())[1],
        data_root=tmp_path,
        authoring_target=_STILL_TARGET,
    )
    await approve(still_author.run_id, session_factory=session_factory)
    still = await _insert_generated_still(
        session_factory,
        source_author_artifact_id=still_author.artifact_id,
        source_run_id=still_author.run_id,
    )

    with pytest.raises(PlannerRefusalError, match="has no human approval"):
        await start_conditioned_video_author(
            "track beside the car",
            still.id,
            target_backend="comfyui.seedance_2_0",
            session_factory=session_factory,
            driver_registry=registry,
            event_appender=(await _events())[1],
            data_root=tmp_path,
            tool_registry=_target_catalog(registry),
        )


async def test_concurrent_still_approval_records_one_decision(
    session_factory,
    tmp_path,
):
    import asyncio

    author_driver = _AuthorDriver()
    registry = _registry(author_driver)
    authored = await start_author(
        "a car crosses a wet bridge",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=(await _events())[1],
        data_root=tmp_path,
        authoring_target=_STILL_TARGET,
    )
    await approve(authored.run_id, session_factory=session_factory)
    still = await _insert_generated_still(
        session_factory,
        source_author_artifact_id=authored.artifact_id,
        source_run_id=authored.run_id,
    )

    first, second = await asyncio.gather(
        review_generation(
            still.id,
            approve=True,
            actor="reviewer-a",
            session_factory=session_factory,
        ),
        review_generation(
            still.id,
            approve=True,
            actor="reviewer-b",
            session_factory=session_factory,
        ),
    )

    assert first.event_id == second.event_id
    assert {first.idempotent, second.idempotent} == {False, True}
    async with session_factory() as session:
        decisions = await EventRepo(session).get_recent(
            event_type=REVIEW_EVENT_TYPE,
            entity_id=still.id,
        )
        assert len(decisions) == 1


async def test_partial_generation_can_be_corrected_but_not_approved(
    session_factory,
    tmp_path,
):
    author_driver = _AuthorDriver()
    registry = _registry(author_driver)
    authored = await start_author(
        "a car crosses a wet bridge",
        session_factory=session_factory,
        driver_registry=registry,
        event_appender=(await _events())[1],
        data_root=tmp_path,
        authoring_target=_STILL_TARGET,
    )
    await approve(authored.run_id, session_factory=session_factory)
    still = await _insert_generated_still(
        session_factory,
        source_author_artifact_id=authored.artifact_id,
        source_run_id=authored.run_id,
        state="partial",
    )

    with pytest.raises(PlannerRefusalError, match="is 'partial'"):
        await review_generation(
            still.id,
            approve=True,
            session_factory=session_factory,
        )
