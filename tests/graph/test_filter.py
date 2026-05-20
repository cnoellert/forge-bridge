"""PR C — graph filter primitive contracts."""
from __future__ import annotations

import pytest

from forge_bridge.graph import (
    FilterNode,
    GraphInputError,
    PredicateParseError,
    is_filter_step,
    parse_filter_step,
)


def test_parse_filter_step_builds_flat_predicate_ast():
    predicate = parse_filter_step("filter(duration > 1)")

    assert predicate.to_dict() == {
        "field": "duration",
        "operator": ">",
        "value": 1,
    }


def test_parse_filter_step_supports_not_equal_exemplar():
    predicate = parse_filter_step("where version_index != 0")

    assert predicate.to_dict() == {
        "field": "version_index",
        "operator": "!=",
        "value": 0,
    }


def test_parse_filter_step_consumes_stacked_intent_keywords():
    assert parse_filter_step("filter where duration > 1").to_dict() == {
        "field": "duration",
        "operator": ">",
        "value": 1,
    }
    assert parse_filter_step("filter where is_open == true").to_dict() == {
        "field": "is_open",
        "operator": "==",
        "value": True,
    }
    assert parse_filter_step("filter where version_index != 0").to_dict() == {
        "field": "version_index",
        "operator": "!=",
        "value": 0,
    }


def test_parse_filter_step_rejects_or_semantics():
    with pytest.raises(PredicateParseError) as exc:
        parse_filter_step("filter(duration > 1 or version_index != 0)")

    assert exc.value.code == "or_not_supported"


def test_parse_filter_step_rejects_nested_predicates():
    with pytest.raises(PredicateParseError) as exc:
        parse_filter_step("filter((duration > 1))")

    assert exc.value.code == "nested_predicate_not_supported"


def test_parse_filter_step_unknown_predicates_fail_loud():
    with pytest.raises(PredicateParseError) as exc:
        parse_filter_step("filter only the comp segments")

    assert exc.value.code == "unknown_predicate"


def test_filter_intent_does_not_treat_keyed_value_only_as_filter():
    assert is_filter_step("list versions project_name=Only") is False


def test_filter_node_filters_enumeration_payload():
    predicate = parse_filter_step("filter(duration > 1)")
    node = FilterNode(predicate)
    payload = {
        "sequence": "30sec_21",
        "segments": [
            {"name": "a", "duration": 1},
            {"name": "b", "duration": 2},
        ],
        "count": 2,
    }

    result = node.run(payload)

    assert result["segments"] == [{"name": "b", "duration": 2}]
    assert result["count"] == 1
    assert result["filter"]["input_count"] == 2
    assert result["filter"]["output_count"] == 1


def test_empty_collections_are_valid_graph_state():
    predicate = parse_filter_step("filter(duration > 10)")
    node = FilterNode(predicate)
    payload = {"segments": [{"name": "a", "duration": 1}], "count": 1}

    result = node.run(payload)

    assert result["segments"] == []
    assert result["count"] == 0
    assert node.selected_collection(payload) == []


def test_filter_node_rejects_scalar_inputs_mechanically():
    predicate = parse_filter_step("filter(duration > 1)")
    node = FilterNode(predicate)

    with pytest.raises(GraphInputError) as exc:
        node.run("not a collection")

    assert exc.value.code == "invalid_collection"


def test_filter_node_rejects_mutation_manifests_mechanically():
    predicate = parse_filter_step("filter(duration > 1)")
    node = FilterNode(predicate)
    mutation_manifest = {
        "renamed": 2,
        "changes": [{"current": "old", "proposed": "new", "duration": 2}],
    }

    with pytest.raises(GraphInputError) as exc:
        node.run(mutation_manifest)

    assert exc.value.code == "non_enumeration_input"
