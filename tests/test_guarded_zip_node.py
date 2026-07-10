"""Assert-based coverage for the `guarded_zip` positional-binding primitive."""
from __future__ import annotations

import asyncio
import uuid

import pytest

from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary
from forge_bridge.graph.guarded_zip import (
    GuardedZipAbstain,
    GuardedZipError,
    GuardedZipNode,
    GuardedZipSpec,
)


def _ok(output):
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output=output,
    )


def _dispatch(config, left, right):
    node = NodeSpec(node_id="gz", operator_id="guarded_zip", config=config)
    resolved_inputs = {"left": _ok(left), "right": _ok(right)}
    return asyncio.run(PrimitiveBoundary().dispatch(node, resolved_inputs))


# --- Barrel import contract -------------------------------------------------


def test_barrel_reexports_guarded_zip_symbols():
    from forge_bridge.graph import (  # noqa: F401
        GuardedZipError,
        GuardedZipNode,
        GuardedZipSpec,
        JoinNode,
    )


# --- Success: positional pairing nests and stamps provenance ----------------


def test_boundary_equal_length_all_correspond_ok_nested_and_provenance():
    result = _dispatch(
        {"left_key": "seg_name"},
        left={"segments": [{"seg_name": "sh010"}, {"seg_name": "sh020"}]},
        right={"slates": [
            {"seg_name": "sh010", "slate": "A"},
            {"seg_name": "sh020", "slate": "B"},
        ]},
    )
    assert result.status == "ok"
    segments = result.output["segments"]
    # Positional binding: left[i] pairs with right[i], nested under `paired`.
    assert segments[0]["paired"] == {"seg_name": "sh010", "slate": "A"}
    assert segments[1]["paired"] == {"seg_name": "sh020", "slate": "B"}
    assert segments[0]["seg_name"] == "sh010"
    assert result.output["guarded_zip"] == {
        "left_count": 2,
        "right_count": 2,
        "paired": 2,
        "left_key": "seg_name",
        "right_key": "seg_name",
        "normalize": True,
    }


def test_run_bare_list_inputs_distinct_right_key_and_into():
    output = GuardedZipNode(
        spec=GuardedZipSpec(left_key="shot", right_key="name", into="slate")
    ).run(
        left=[{"shot": "sh010"}],
        right=[{"name": "sh010", "payload": 7}],
    )
    assert output["collection"][0]["slate"] == {"name": "sh010", "payload": 7}
    assert output["count"] == 1
    assert output["guarded_zip"]["left_key"] == "shot"
    assert output["guarded_zip"]["right_key"] == "name"


# --- Length mismatch → ABSTAIN (not error, not raised) ----------------------


def test_length_mismatch_abstains_with_message_naming_lengths():
    result = _dispatch(
        {"left_key": "seg_name"},
        left=[{"seg_name": "sh010"}, {"seg_name": "sh020"}, {"seg_name": "sh030"},
              {"seg_name": "sh040"}, {"seg_name": "sh050"}],
        right=[{"seg_name": "sh010"}, {"seg_name": "sh020"}, {"seg_name": "sh030"},
               {"seg_name": "sh040"}],
    )
    # Grounded abstain shape: status="abstained" (NOT "error"), no usable output.
    assert result.status == "abstained"
    assert result.has_usable_output is False
    assert result.reason_code == "guarded_zip_length_mismatch"
    assert "length mismatch (left=5, right=4)" in result.message


# --- Name mismatch at index k → ABSTAIN naming index + both values ----------


def test_name_mismatch_abstains_naming_index_and_both_values():
    result = _dispatch(
        {"left_key": "seg_name"},
        left=[
            {"seg_name": "sh010"},
            {"seg_name": "sh020"},
            {"seg_name": "sh030"},
            {"seg_name": "shot_040"},
        ],
        right=[
            {"seg_name": "sh010"},
            {"seg_name": "sh020"},
            {"seg_name": "sh030"},
            {"seg_name": "slate_050"},
        ],
    )
    assert result.status == "abstained"
    assert result.has_usable_output is False
    assert result.reason_code == "guarded_zip_name_mismatch"
    assert "index 3" in result.message
    assert "shot_040" in result.message
    assert "slate_050" in result.message


# --- Normalized correspondence: case/whitespace differences still pair -------


def test_normalized_case_and_whitespace_still_ok_by_default():
    result = _dispatch(
        {"left_key": "seg_name"},
        left=[{"seg_name": "  SH010 "}],
        right=[{"seg_name": "sh010", "slate": "A"}],
    )
    assert result.status == "ok"
    assert result.output["collection"][0]["paired"] == {"seg_name": "sh010", "slate": "A"}


def test_strict_normalize_false_treats_formatting_difference_as_mismatch():
    result = _dispatch(
        {"left_key": "seg_name", "normalize": False},
        left=[{"seg_name": "  SH010 "}],
        right=[{"seg_name": "sh010"}],
    )
    assert result.status == "abstained"
    assert result.reason_code == "guarded_zip_name_mismatch"


# --- None values do not crash: a None-vs-something is a non-correspondence ---


def test_none_value_does_not_crash_and_abstains():
    result = _dispatch(
        {"left_key": "seg_name"},
        left=[{"seg_name": None}],
        right=[{"seg_name": "sh010"}],
    )
    assert result.status == "abstained"
    assert result.reason_code == "guarded_zip_name_mismatch"


# --- `into` collision → structured ERROR (real authoring error) -------------


def test_into_collision_raises_guarded_zip_error_on_node():
    with pytest.raises(GuardedZipError) as excinfo:
        GuardedZipNode(spec=GuardedZipSpec(left_key="seg_name")).run(
            left=[{"seg_name": "sh010", "paired": "already here"}],
            right=[{"seg_name": "sh010", "slate": "A"}],
        )
    assert excinfo.value.code == "guarded_zip_collision"


def test_into_collision_boundary_returns_error_status():
    result = _dispatch(
        {"left_key": "seg_name"},
        left=[{"seg_name": "sh010", "paired": "already here"}],
        right=[{"seg_name": "sh010", "slate": "A"}],
    )
    assert result.status == "error"
    assert result.reason_code == "guarded_zip_collision"


# --- Missing / empty left_key → structured _error, never a raised KeyError ---


def test_missing_left_key_returns_invalid_spec_error_not_keyerror():
    result = _dispatch(
        {},  # no left_key
        left=[{"seg_name": "sh010"}],
        right=[{"seg_name": "sh010"}],
    )
    assert result.status == "error"
    assert result.reason_code == "guarded_zip_invalid_spec"


def test_empty_left_key_returns_invalid_spec_error():
    result = _dispatch(
        {"left_key": ""},
        left=[{"seg_name": "sh010"}],
        right=[{"seg_name": "sh010"}],
    )
    assert result.status == "error"
    assert result.reason_code == "guarded_zip_invalid_spec"


# --- Length mismatch also raises the typed abstain at the node level ---------


def test_length_mismatch_raises_guarded_zip_abstain_on_node():
    with pytest.raises(GuardedZipAbstain) as excinfo:
        GuardedZipNode(spec=GuardedZipSpec(left_key="seg_name")).run(
            left=[{"seg_name": "sh010"}],
            right=[{"seg_name": "sh010"}, {"seg_name": "sh020"}],
        )
    assert excinfo.value.code == "guarded_zip_length_mismatch"


# --- Boundary robustness: missing input / bad shape never escape -------------


def test_missing_right_input_returns_missing_input_error():
    node = NodeSpec(node_id="gz", operator_id="guarded_zip", config={"left_key": "x"})
    result = asyncio.run(
        PrimitiveBoundary().dispatch(node, {"left": _ok([{"x": "a"}])})
    )
    assert result.status == "error"
    assert result.reason_code == "guarded_zip_missing_input"


def test_bad_input_shape_returns_invalid_input_error_not_raise():
    result = _dispatch(
        {"left_key": "seg_name"},
        left=42,  # not a collection
        right=[{"seg_name": "sh010"}],
    )
    assert result.status == "error"
    assert result.reason_code == "guarded_zip_invalid_input"
