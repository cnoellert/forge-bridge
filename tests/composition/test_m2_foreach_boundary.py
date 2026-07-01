from __future__ import annotations

import uuid

import pytest

from forge_bridge.composition.foreach_boundary import ForeachBoundary
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.ports import PortContract


def _collection_result() -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        output={
            "shots": [
                {"id": "gs_010", "is_greenscreen": True},
                {"id": "gs_020", "is_greenscreen": True},
            ],
            "count": 2,
        },
    )


def _foreach_node() -> NodeSpec:
    return NodeSpec(
        node_id="foreach",
        operator_id="foreach",
        config={
            "body": NodeSpec(
                node_id="roto_body",
                operator_id="forge_roto_ref",
                input_ports={"item": PortContract.any()},
            )
        },
    )


@pytest.mark.asyncio
async def test_foreach_boundary_reenters_shared_dispatch_per_item():
    seen_payloads: list[dict] = []

    async def reenter(node: NodeSpec, resolved_inputs: dict[str, NodeResult]):
        assert node.operator_id == "forge_roto_ref"
        item_input = resolved_inputs["item"]
        seen_payloads.append(item_input.output)
        return NodeResult(
            status="ok",
            run_id=uuid.uuid4(),
            output={"matte": item_input.output["shots"][0]["id"]},
            output_topology={"kind": "manifest"},
            artifact_id=uuid.uuid4(),
        )

    result = await ForeachBoundary().dispatch(
        _foreach_node(),
        {"input": _collection_result()},
        reenter=reenter,
    )

    assert result.status == "ok"
    assert result.artifact_id is not None
    assert result.source_artifact_ids == (
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )
    assert result.output["count"] == 2
    assert result.output["foreach"] == {
        "body": "forge_roto_ref",
        "input_count": 2,
        "output_count": 2,
    }
    # foreach authors each item's ordinal iteration index onto the per-item
    # payload under the reserved ``_foreach`` namespace (foreach is the sole
    # author); the body reads a real index rather than a pre-stamped scaffold.
    assert [p["shots"] for p in seen_payloads] == [
        [{"id": "gs_010", "is_greenscreen": True, "_foreach": {"index": 0}}],
        [{"id": "gs_020", "is_greenscreen": True, "_foreach": {"index": 1}}],
    ]
    assert [p["count"] for p in seen_payloads] == [1, 1]
    assert [i["result"] for i in result.output["iterations"]] == [
        {"matte": "gs_010"},
        {"matte": "gs_020"},
    ]


@pytest.mark.asyncio
async def test_foreach_boundary_first_body_error_fails_whole_node():
    async def reenter(_node: NodeSpec, _resolved_inputs: dict[str, NodeResult]):
        return NodeResult(
            status="error",
            run_id=uuid.uuid4(),
            reason_code="body_failed",
            message="body failed",
        )

    result = await ForeachBoundary().dispatch(
        _foreach_node(),
        {"input": _collection_result()},
        reenter=reenter,
    )

    assert result.status == "error"
    assert result.reason_code == "body_failed"
    assert result.source_artifact_ids == (
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )
    assert result.output["iteration_index"] == 0
    assert result.output["body_step"] == "forge_roto_ref"


@pytest.mark.asyncio
async def test_foreach_boundary_abstained_body_fails_whole_node():
    async def reenter(_node: NodeSpec, _resolved_inputs: dict[str, NodeResult]):
        return NodeResult(
            status="abstained",
            run_id=uuid.uuid4(),
            reason_code="body_abstained",
            message="body abstained",
        )

    result = await ForeachBoundary().dispatch(
        _foreach_node(),
        {"input": _collection_result()},
        reenter=reenter,
    )

    assert result.status == "error"
    assert result.reason_code == "body_abstained"
    assert result.message == "body abstained"
    assert result.source_artifact_ids == (
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )
    assert result.output["iteration_index"] == 0
    assert result.output["body_error"]["reason_code"] == "body_abstained"


@pytest.mark.asyncio
async def test_foreach_boundary_requires_exactly_one_upstream():
    async def reenter(_node: NodeSpec, _resolved_inputs: dict[str, NodeResult]):
        raise AssertionError("should not re-enter")

    result = await ForeachBoundary().dispatch(
        _foreach_node(),
        {},
        reenter=reenter,
    )

    assert result.status == "error"
    assert result.reason_code == "invalid_foreach_input"


@pytest.mark.asyncio
async def test_foreach_boundary_lowercases_graph_input_error_code():
    async def reenter(_node: NodeSpec, _resolved_inputs: dict[str, NodeResult]):
        raise AssertionError("should not re-enter")

    bad_collection = NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        output={"not_a_collection": "nope"},
    )

    result = await ForeachBoundary().dispatch(
        _foreach_node(),
        {"input": bad_collection},
        reenter=reenter,
    )

    assert result.status == "error"
    assert result.reason_code == "invalid_foreach_input"


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [{}, {"body": {"operator_id": "forge_roto_ref"}}])
async def test_foreach_boundary_malformed_body_config_fails_closed(config):
    async def reenter(_node: NodeSpec, _resolved_inputs: dict[str, NodeResult]):
        raise AssertionError("should not re-enter")

    result = await ForeachBoundary().dispatch(
        NodeSpec(node_id="foreach", operator_id="foreach", config=config),
        {"input": _collection_result()},
        reenter=reenter,
    )

    assert result.status == "error"
    assert result.reason_code == "invalid_foreach_config"
    assert "config['body']" in (result.message or "")
    assert result.source_artifact_ids == (
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )
