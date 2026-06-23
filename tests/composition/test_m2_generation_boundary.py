from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

from forge_bridge.composition.boundary import UnsupportedCompositionNodeError
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.generation_boundary import (
    GENERATION_FAILED,
    GENERATION_INPUT_ERROR,
    GENERATION_UNAVAILABLE,
    GenerationDispatchBoundary,
)
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult

RESOLVED_CLASS = "generators.author_prompt"


@dataclass
class _GenerationArtifact:
    lifecycle_state: str
    artifact_id: str = "gen-001"
    operator_id: str = "author_prompt"
    media_kind: str = "text/plain"
    media_locator: str | None = None
    media_content_sha256: str | None = "sha-text"
    failure_reason: str | None = None
    text: str | None = None

    def to_transport_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "lifecycle_state": self.lifecycle_state,
            "operator_id": self.operator_id,
            "media_kind": self.media_kind,
            "media_locator": self.media_locator,
            "media_content_sha256": self.media_content_sha256,
            "failure_reason": self.failure_reason,
            "text": self.text,
        }


def _node(arguments: dict | None = None) -> NodeSpec:
    return NodeSpec(
        node_id="author",
        operator_id="author_prompt",
        config={"arguments": arguments or {}},
    )


@pytest.mark.asyncio
async def test_generation_boundary_success_maps_authored_text_from_artifact_file(
    tmp_path: Path,
):
    text_path = tmp_path / "authored.txt"
    text_path.write_text("a warmer lighthouse at dusk", encoding="utf-8")
    calls: list[dict] = []
    source_id = uuid.uuid4()

    async def run_generation(operator_id: str, **kwargs):
        calls.append({"operator_id": operator_id, **kwargs})
        return _GenerationArtifact(
            lifecycle_state="complete",
            media_locator=str(text_path),
        )

    result = await GenerationDispatchBoundary(
        run_generation=run_generation,
        run_id=uuid.UUID("00000000-0000-0000-0000-000000000204"),
        artifact_id_factory=lambda: uuid.UUID("00000000-0000-0000-0000-000000000205"),
    ).dispatch(
        _node(
            {
                "intent": "write a lighthouse prompt",
                "context": {"refs": []},
                "target": "generate_image",
                "style": "warm",
            }
        ),
        {
            "intent": NodeResult(
                status="ok",
                run_id=uuid.uuid4(),
                artifact_id=source_id,
                output={"intent": "edge intent wins"},
            )
        },
    )

    assert result.status == "ok"
    assert result.output["text"] == "a warmer lighthouse at dusk"
    assert result.output["artifact"]["artifact_id"] == "gen-001"
    assert result.artifact_id == uuid.UUID("00000000-0000-0000-0000-000000000205")
    assert result.artifact_type == "text/plain"
    assert result.source_artifact_ids == (source_id,)
    assert result.resolved_class == RESOLVED_CLASS
    assert calls == [{
        "operator_id": "author_prompt",
        "intent": "edge intent wins",
        "context": {"refs": []},
        "target": "generate_image",
        "style": "warm",
    }]


@pytest.mark.asyncio
async def test_generation_boundary_failure_maps_to_error_without_output():
    async def run_generation(operator_id: str, **kwargs):
        return _GenerationArtifact(
            lifecycle_state="failed",
            failure_reason="ollama_unavailable",
        )

    result = await GenerationDispatchBoundary(run_generation=run_generation).dispatch(
        _node({"intent": "write something"}),
        {},
    )

    assert result.status == "error"
    assert result.reason_code == "ollama_unavailable"
    assert result.message == "ollama_unavailable"
    assert result.output is None
    assert result.control_signal == "skip"


@pytest.mark.asyncio
async def test_generation_boundary_unknown_terminal_status_fails_closed():
    async def run_generation(operator_id: str, **kwargs):
        return _GenerationArtifact(lifecycle_state="running")

    result = await GenerationDispatchBoundary(run_generation=run_generation).dispatch(
        _node({"intent": "write something"}),
        {},
    )

    assert result.status == "error"
    assert result.reason_code == GENERATION_FAILED


@pytest.mark.asyncio
async def test_generation_boundary_missing_intent_is_deterministic_error():
    result = await GenerationDispatchBoundary(run_generation=lambda *a, **k: None).dispatch(
        _node({}),
        {},
    )

    assert result.status == "error"
    assert result.reason_code == GENERATION_INPUT_ERROR


@pytest.mark.asyncio
async def test_generation_boundary_missing_runner_is_deterministic_error():
    result = await GenerationDispatchBoundary().dispatch(
        _node({"intent": "write something"}),
        {},
    )

    assert result.status == "error"
    assert result.reason_code == GENERATION_UNAVAILABLE


@pytest.mark.asyncio
async def test_generation_boundary_rejects_non_generation_node():
    with pytest.raises(UnsupportedCompositionNodeError):
        await GenerationDispatchBoundary(run_generation=lambda *a, **k: None).dispatch(
            NodeSpec(node_id="filter", operator_id="filter"),
            {},
        )


@pytest.mark.asyncio
async def test_generation_routes_through_real_graph_executor_and_unified_dispatch():
    calls: list[dict] = []

    async def run_generation(operator_id: str, **kwargs):
        calls.append({"operator_id": operator_id, **kwargs})
        return _GenerationArtifact(
            lifecycle_state="complete",
            text="a crisp authored prompt",
        )

    graph = GraphSpec(
        nodes=(
            NodeSpec(node_id="intent", operator_id="forge_is_greenscreen"),
            NodeSpec(
                node_id="author",
                operator_id="author_prompt",
                input_ports={"intent": __import__(
                    "forge_bridge.graph.ports",
                    fromlist=["PortContract"],
                ).PortContract.any()},
            ),
        ),
        edges=(Edge(from_node="intent", to_node="author", to_port="intent"),),
    )

    async def dispatch(node: NodeSpec, resolved_inputs: dict[str, NodeResult]):
        if node.node_id == "intent":
            return NodeResult(
                status="ok",
                run_id=uuid.uuid4(),
                artifact_id=uuid.UUID("00000000-0000-0000-0000-000000000301"),
                output="write a prompt",
            )
        return await UnifiedDispatch(
            generation_boundary=GenerationDispatchBoundary(
                run_generation=run_generation
            )
        ).dispatch(node, resolved_inputs)

    results = await GraphExecutor(dispatch).run(graph)

    assert results["author"].status == "ok"
    assert results["author"].output["text"] == "a crisp authored prompt"
    assert results["author"].resolved_class == RESOLVED_CLASS
    assert calls == [{
        "operator_id": "author_prompt",
        "intent": "write a prompt",
        "context": None,
        "target": None,
        "style": None,
    }]


def test_graph_executor_is_byte_stable_vs_main():
    repo = Path(__file__).parents[2]
    diff = subprocess.run(
        ["git", "diff", "main", "--", "forge_bridge/composition/executor.py"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout == ""
