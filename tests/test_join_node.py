"""Assert-based coverage for the `join` value-transform graph primitive."""
from __future__ import annotations

import asyncio
import uuid

import pytest

from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary
from forge_bridge.graph.join import JoinError, JoinNode, JoinSpec


def test_exact_match_happy_path_nests_and_stamps_provenance():
    left = {"segments": [{"seg_name": "sh010"}, {"seg_name": "sh020"}]}
    right = {"slates": [
        {"seg_name": "sh010", "slate": "A"},
        {"seg_name": "sh020", "slate": "B"},
    ]}
    output = JoinNode(spec=JoinSpec(left_key="seg_name")).run(left, right)

    assert output["segments"][0]["joined"] == {"seg_name": "sh010", "slate": "A"}
    assert output["segments"][1]["joined"] == {"seg_name": "sh020", "slate": "B"}
    # Both sides intact.
    assert output["segments"][0]["seg_name"] == "sh010"
    prov = output["join"]
    assert prov == {
        "left_count": 2,
        "right_count": 2,
        "matched": 2,
        "left_key": "seg_name",
        "right_key": "seg_name",
        "normalize": False,
    }


def test_bare_list_inputs_and_distinct_right_key_and_into():
    left = [{"shot": "sh010"}]
    right = [{"name": "sh010", "payload": 7}]
    output = JoinNode(
        spec=JoinSpec(left_key="shot", right_key="name", into="matched_slate")
    ).run(left, right)

    assert output["collection"][0]["matched_slate"] == {"name": "sh010", "payload": 7}
    assert output["count"] == 1
    assert output["join"]["left_key"] == "shot"
    assert output["join"]["right_key"] == "name"


def test_miss_raises_join_miss():
    left = [{"seg_name": "sh010"}]
    right = [{"seg_name": "sh999"}]
    with pytest.raises(JoinError) as excinfo:
        JoinNode(spec=JoinSpec(left_key="seg_name")).run(left, right)
    assert excinfo.value.code == "join_miss"


def test_ambiguous_raises_join_ambiguous():
    left = [{"seg_name": "sh010"}]
    right = [
        {"seg_name": "sh010", "slate": "A"},
        {"seg_name": "sh010", "slate": "B"},
    ]
    with pytest.raises(JoinError) as excinfo:
        JoinNode(spec=JoinSpec(left_key="seg_name")).run(left, right)
    assert excinfo.value.code == "join_ambiguous"


def test_collision_on_preexisting_into_key_raises_join_collision():
    left = [{"seg_name": "sh010", "joined": "already here"}]
    right = [{"seg_name": "sh010", "slate": "A"}]
    with pytest.raises(JoinError) as excinfo:
        JoinNode(spec=JoinSpec(left_key="seg_name")).run(left, right)
    assert excinfo.value.code == "join_collision"


def test_normalize_matches_where_exact_would_miss():
    left = [{"seg_name": "  SH010 "}]
    right = [{"seg_name": "sh010", "slate": "A"}]

    # Exact match misses.
    with pytest.raises(JoinError) as exact:
        JoinNode(spec=JoinSpec(left_key="seg_name")).run(left, right)
    assert exact.value.code == "join_miss"

    # Casefold + strip pairs them.
    output = JoinNode(spec=JoinSpec(left_key="seg_name", normalize=True)).run(left, right)
    assert output["collection"][0]["joined"] == {"seg_name": "sh010", "slate": "A"}
    assert output["join"]["normalize"] is True


def test_missing_attr_raises_join_key_missing():
    left = [{"seg_name": "sh010"}]
    right = [{"other": "sh010"}]
    with pytest.raises(JoinError) as excinfo:
        JoinNode(spec=JoinSpec(left_key="seg_name")).run(left, right)
    assert excinfo.value.code == "join_key_missing"


def test_boundary_returns_error_status_not_raised_exception():
    def _ok(output):
        return NodeResult(
            status="ok",
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            output=output,
        )

    node = NodeSpec(
        node_id="j",
        operator_id="join",
        config={"left_key": "seg_name"},
    )
    resolved_inputs = {
        "left": _ok([{"seg_name": "sh010"}]),
        "right": _ok([{"seg_name": "sh999"}]),  # no match → join_miss
    }

    result = asyncio.run(PrimitiveBoundary().dispatch(node, resolved_inputs))
    assert result.status == "error"
    assert result.reason_code == "join_miss"


def test_boundary_happy_path_returns_ok():
    def _ok(output):
        return NodeResult(
            status="ok",
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            output=output,
        )

    node = NodeSpec(
        node_id="j",
        operator_id="join",
        config={"left_key": "seg_name"},
    )
    resolved_inputs = {
        "left": _ok([{"seg_name": "sh010"}]),
        "right": _ok([{"seg_name": "sh010", "slate": "A"}]),
    }

    result = asyncio.run(PrimitiveBoundary().dispatch(node, resolved_inputs))
    assert result.status == "ok"
    assert result.output["collection"][0]["joined"]["slate"] == "A"
