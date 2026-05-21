"""Phase N — foreach + collect graph primitive contracts."""
from __future__ import annotations

import inspect

import pytest

from forge_bridge.graph import (
    ChainWireCompatibilityError,
    CollectNode,
    ForEachNode,
    ForeachParseError,
    PortTopology,
    is_collect_step,
    is_foreach_step,
    parse_collect_step,
    parse_foreach_step,
)


def _iteration(index: int, result: dict):
    return {
        "index": index,
        "item": {"name": f"item_{index}"},
        "result": result,
        "emitted_topology": {"kind": "manifest"},
    }


def test_foreach_one_item_emits_iteration_input():
    node = ForEachNode("select a")

    assert node.items({"segments": [{"seg_name": "a"}]}) == [{"seg_name": "a"}]


def test_foreach_n_items_emits_n_iteration_inputs():
    node = ForEachNode("select a")

    assert len(node.items({"segments": [{"seg_name": "a"}, {"seg_name": "b"}]})) == 2


def test_foreach_accepts_varied_collection_keys():
    node = ForEachNode("select clip_a")

    assert node.items({"clips": [{"clip_name": "clip_a"}]}) == [
        {"clip_name": "clip_a"},
    ]


def test_foreach_envelope_outputs_list_iteration_result():
    node = ForEachNode("select a")
    iteration = node.wrap_result(
        index=0,
        item={"seg_name": "a"},
        result={"renamed": 1},
        emitted_topology={"kind": "manifest"},
    )

    envelope = node.envelope([iteration])

    assert envelope["iterations"][0]["result"] == {"renamed": 1}
    assert envelope["count"] == 1


def test_collect_zero_item_reconciles_to_empty_collection_manifest():
    result = CollectNode().run({"iterations": []})

    assert result["collection"] == []
    assert result["count"] == 0


def test_collect_one_item_reconciles_body_output():
    result = CollectNode().run({"iterations": [_iteration(0, {"values": [1]})]})

    assert result["values"] == [1]
    assert result["collect"]["input_count"] == 1


def test_collect_merges_list_fields():
    result = CollectNode().run({
        "iterations": [
            _iteration(0, {"values": [1]}),
            _iteration(1, {"values": [2]}),
        ],
    })

    assert result["values"] == [1, 2]


def test_collect_output_topology_is_manifest():
    result = CollectNode().run({"iterations": [_iteration(0, {"values": [1]})]})

    assert result["collect"]["output_topology"] == {"kind": "manifest"}


def test_foreach_port_declares_collection_to_iteration_results():
    assert ForEachNode.port_contract.to_dict() == {
        "accepts": [{"kind": "list", "item_type": "item"}],
        "emits": {"kind": "list", "item_type": "IterationResult"},
    }


def test_collect_port_consumes_iteration_results_and_emits_manifest():
    assert CollectNode.port_contract.to_dict() == {
        "accepts": [{"kind": "list", "item_type": "IterationResult"}],
        "emits": {"kind": "manifest"},
    }


def test_collect_accepts_iteration_result_topology():
    assert CollectNode.port_contract.accepts_topology(
        PortTopology.iteration_results(),
    )


def test_foreach_over_empty_collection_outputs_no_iterations():
    assert ForEachNode("select a").envelope([])["iterations"] == []


def test_collect_over_empty_collection_propagates_valid_manifest():
    result = CollectNode().run({"iterations": []})

    assert result["collect"]["input_count"] == 0
    assert result["collect"]["output_topology"] == {"kind": "manifest"}


def test_collect_drops_varying_scalar_field_from_reconciled_top_level():
    result = CollectNode().run({
        "iterations": [
            _iteration(0, {"status": "ok"}),
            _iteration(1, {"status": "changed"}),
        ],
    })

    assert "status" not in result


def test_collect_retains_constant_scalar_field_as_scalar():
    result = CollectNode().run({
        "iterations": [
            _iteration(0, {"status": "ok"}),
            _iteration(1, {"status": "ok"}),
        ],
    })

    assert result["status"] == "ok"


def test_collect_reconciled_manifest_contains_only_fields_stable_across_all_iterations():
    result = CollectNode().run({
        "iterations": [
            _iteration(0, {"stable": "same", "varies": "a", "items": [1]}),
            _iteration(1, {"stable": "same", "varies": "b", "items": [2]}),
        ],
    })

    assert result["stable"] == "same"
    assert result["items"] == [1, 2]
    assert "varies" not in result


def test_collect_iterations_array_carries_full_per_item_detail():
    iterations = [
        _iteration(0, {"status": "ok", "detail": "first"}),
        _iteration(1, {"status": "changed", "detail": "second"}),
    ]

    result = CollectNode().run({"iterations": iterations})

    assert result["iterations"] == iterations
    assert result["iterations"][0]["result"]["detail"] == "first"
    assert result["iterations"][1]["result"]["detail"] == "second"


def test_collect_drops_partially_present_field_from_reconciled_top_level():
    result = CollectNode().run({
        "iterations": [
            _iteration(0, {"stable": "same", "optional": "present"}),
            _iteration(1, {"stable": "same"}),
        ],
    })

    assert result["stable"] == "same"
    assert "optional" not in result


def test_collect_does_not_raise_chain_wire_compatibility_error_for_scalar_variance():
    """16th discipline-policy enforcement test: scalar variance is not topology."""
    try:
        result = CollectNode().run({
            "iterations": [
                _iteration(0, {"status": "ok"}),
                _iteration(1, {"status": "changed"}),
            ],
        })
    except ChainWireCompatibilityError as exc:  # pragma: no cover - assertion path
        pytest.fail(f"Scalar variance raised wire compatibility error: {exc}")

    assert "status" not in result


def test_collect_list_field_uses_generic_list_merge_rule():
    result = CollectNode().run({
        "iterations": [
            _iteration(0, {"items": [{"name": "a"}]}),
            _iteration(1, {"items": [{"name": "b"}]}),
        ],
    })

    assert result["items"] == [{"name": "a"}, {"name": "b"}]


def test_collect_scalar_field_uses_generic_scalar_compatibility_rule():
    result = CollectNode().run({
        "iterations": [
            _iteration(0, {"state": "same"}),
            _iteration(1, {"state": "same"}),
        ],
    })

    assert result["state"] == "same"


def test_collect_implementation_has_no_domain_field_special_cases():
    """14th discipline-policy enforcement test: collect is substrate-generic."""
    from forge_bridge.graph import collect as collect_module

    src = inspect.getsource(collect_module)

    assert '"proposed_changes"' not in src
    assert '"execution_state"' not in src


def test_parse_foreach_step_extracts_single_body_step():
    assert parse_foreach_step("foreach(rename shots dry_run)") == (
        "rename shots dry_run"
    )


def test_parse_foreach_rejects_chain_body_separator():
    """15th discipline-policy enforcement test: one-step body only."""
    with pytest.raises(ForeachParseError) as exc:
        parse_foreach_step("foreach(filter(duration > 1) -> rename shots)")

    assert exc.value.code == "FOREACH_CHAIN_BODY_NOT_SUPPORTED"


def test_parse_foreach_allows_single_step_with_modifier():
    assert parse_foreach_step("foreach(rename shots with prefix genesis dry_run)") == (
        "rename shots with prefix genesis dry_run"
    )


def test_parse_foreach_rejects_two_steps_in_body():
    with pytest.raises(ForeachParseError) as exc:
        parse_foreach_step("foreach(select a -> select b)")

    assert exc.value.code == "FOREACH_CHAIN_BODY_NOT_SUPPORTED"


def test_collect_step_parser_accepts_collect_only():
    assert is_collect_step("collect")
    assert parse_collect_step("collect") is None


def test_foreach_step_parser_is_anchored_to_start():
    assert is_foreach_step("foreach(select a)")
    assert not is_foreach_step("please foreach(select a)")
