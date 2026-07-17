"""Unit tests for the bridge-local ollama author_prompt driver (#66 Slice 1)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge_contracts import AuthoringTarget, BackendIdentityTriple
from forge_contracts.references import ArtifactRef

from forge_bridge.orchestration.author_driver import (
    AUTHOR_SURFACE,
    OllamaAuthorDriver,
)
from forge_bridge.orchestration.dispatcher import InvocationEnvelope
from forge_bridge.orchestration.drivers import DriverPollResult
from forge_bridge.orchestration.manual_qc import _runtime, _select_author_backend
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo


class _FakeRouter:
    """Stand-in for LLMRouter so unit tests need no live Ollama."""

    local_model = "qwen2.5-coder:14b"

    def __init__(self, text: str = "a moody neon-lit alley") -> None:
        self._text = text
        self.calls: list[tuple[str, bool]] = []
        self.systems: list[str | None] = []

    async def acomplete(self, prompt, sensitive=True, system=None, temperature=0.1):
        self.calls.append((prompt, sensitive))
        self.systems.append(system)
        return self._text


def _envelope(*, prompt=None, correction=None, target=None) -> InvocationEnvelope:
    inputs: list[ArtifactRef] = []
    if prompt is not None:
        inputs.append(
            ArtifactRef(
                artifact_id="intent-1",
                artifact_type="text_intent",
                metadata={
                    "prompt": prompt,
                    "role": "structural",
                    **({"scalars": {"target": target}} if target is not None else {}),
                },
            )
        )
    if correction is not None:
        inputs.append(
            ArtifactRef(
                artifact_id="qc-1",
                artifact_type="qc_correction",
                metadata={"qc_correction": correction, "role": "editorial"},
            )
        )
    return InvocationEnvelope(
        operator_id="author_prompt",
        inputs=inputs,
        backend_identity_triple={"surface": AUTHOR_SURFACE},
    )


def _fake_artifact(request_id: str):
    return SimpleNamespace(execution_provenance={"request_id": request_id})


def test_backend_identity_triple_shape():
    driver = OllamaAuthorDriver(router=_FakeRouter())
    assert driver.backend_identity_triple["surface"] == AUTHOR_SURFACE
    assert driver.backend_identity_triple["path"] == "qwen2.5-coder:14b"
    # Composite backend_id round-trips surface.path exactly like sibling drivers.
    assert driver.backend_id == "ollama-api.qwen2.5-coder:14b"


async def test_submit_calls_acomplete_locally_then_poll_is_terminal():
    router = _FakeRouter(text="a moody neon-lit alley")
    driver = OllamaAuthorDriver(router=router)

    handle = await driver.submit(_envelope(prompt="make a moody one-line beat"))

    # submit authored via LOCAL Ollama (sensitive=True) exactly once.
    assert len(router.calls) == 1
    prompt_sent, sensitive = router.calls[0]
    assert sensitive is True
    assert "make a moody one-line beat" in prompt_sent
    assert handle.request_id

    poll = await driver.poll(_fake_artifact(handle.request_id))

    # FIRST poll is terminal, carrying the authored text where _artifact_text reads it.
    assert poll.next_state == "complete"
    assert poll.next_state in GenerationArtifactRepo.TERMINAL_STATES
    assert poll.terminal_provenance is not None
    assert poll.terminal_provenance["text"] == "a moody neon-lit alley"


async def test_qc_correction_threads_into_authoring_prompt():
    router = _FakeRouter(text="draft two")
    driver = OllamaAuthorDriver(router=router)

    await driver.submit(
        _envelope(prompt="a beat", correction="make the subject more specific")
    )

    prompt_sent, _sensitive = router.calls[0]
    assert "make the subject more specific" in prompt_sent


async def test_typed_motion_target_shapes_local_fallback_system_prompt():
    router = _FakeRouter(text="motion draft")
    driver = OllamaAuthorDriver(router=router)
    target = AuthoringTarget(
        operator_id="generate_video_from_image",
        backend_identity_triple=BackendIdentityTriple(
            surface="comfyui",
            path="seedance_2_0",
            auth_mechanism="local",
            revision="r5",
        ),
    )

    await driver.submit(
        _envelope(prompt="a runner crosses frame", target=target.model_dump(mode="json"))
    )

    assert "camera verbs, timing, and subject choreography" in router.systems[0]


async def test_malformed_typed_target_refuses_before_local_author_call():
    router = _FakeRouter()
    driver = OllamaAuthorDriver(router=router)

    with pytest.raises(ValueError, match="forge-contracts AuthoringTarget"):
        await driver.submit(
            _envelope(prompt="a runner crosses frame", target={"operator_id": "bad"})
        )

    assert router.calls == []


def test_non_terminal_poll_is_a_silent_bug_guard():
    """Prove the terminal-text assertion has teeth.

    If poll had returned a NON-terminal result (no terminal_provenance), the run
    would pause with NO authored text merged into execution_provenance, and
    _artifact_text would yield "". This documents the exact silent bug the
    driver avoids by always returning terminal.
    """
    from forge_bridge.orchestration.manual_qc import _artifact_text

    non_terminal = DriverPollResult(
        next_state="submitted", polling_event={}, terminal_provenance=None
    )
    assert non_terminal.next_state not in GenerationArtifactRepo.TERMINAL_STATES
    # No terminal_provenance -> nothing merged -> _artifact_text sees empty state.
    assert _artifact_text({}) == ""
    # And a terminal result WITHOUT a text field would also yield no answer.
    assert _artifact_text({"request_id": "x"}) == ""


async def test_default_runtime_registers_bridge_author_driver_zero_siblings(
    session_factory,
):
    """The load-bearing self-contained proof.

    With no federation siblings installed in the test env, the DEFAULT runtime
    still exposes an ollama-api author driver, so _select_author_backend
    succeeds on a stock install.
    """
    runtime = await _runtime(
        session_factory=session_factory,
        driver_registry=None,
        event_appender=None,
    )

    backend_id, triple = _select_author_backend(runtime.driver_registry)
    assert triple["surface"] == AUTHOR_SURFACE
    assert backend_id.startswith("ollama-api.")
