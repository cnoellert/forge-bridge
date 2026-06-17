from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from forge_bridge.orchestration.drivers import (
    DriverPollResult,
    DriverSubmitResult,
    GenerationDriverRegistry,
)
from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.manual_qc import approve, revise, start_author
from forge_bridge.orchestration.dispatcher import InvocationEnvelope
from forge_bridge.orchestration.replay import RUN_LINEAGE_REL_KEYS
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.repo import RelationshipRepo


_TRIPLE = {
    "surface": "ollama-api",
    "path": "llama3.2",
    "revision": "llama3.2",
}
_BACKEND_ID = "ollama-api.llama3.2"


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


def _registry(driver: _AuthorDriver) -> GenerationDriverRegistry:
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    return registry


async def test_manual_qc_author_revise_and_approve_round_trip(session_factory, tmp_path):
    driver = _AuthorDriver()
    events, append = await _events()

    first = await start_author(
        "make a moody one-line beat",
        session_factory=session_factory,
        driver_registry=_registry(driver),
        event_appender=append,
        data_root=tmp_path,
    )

    assert first.text == "draft one"
    assert first.lifecycle_stage == "execution"
    assert first.lifecycle_status == "paused"

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
