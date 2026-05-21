"""Phase 25.2 — manifest-level if-gate graph primitive."""
from __future__ import annotations

import pytest

from forge_bridge.graph import (
    FilterPredicate,
    GraphInputError,
    IfGateNode,
    is_if_step,
    parse_if_step,
)


def test_parse_if_step_reuses_flat_filter_predicate_ast():
    predicate = parse_if_step("if(proposed_changes exists)")

    assert predicate == FilterPredicate(field="proposed_changes", operator="exists")
    assert predicate.to_dict() == {
        "field": "proposed_changes",
        "operator": "exists",
    }


def test_parse_if_step_accepts_spaced_gate_syntax():
    predicate = parse_if_step("if proposed_changes exists")

    assert predicate.field == "proposed_changes"
    assert predicate.operator == "exists"


def test_is_if_step_is_anchored_to_chain_step_start():
    assert is_if_step("if(proposed_changes exists)")
    assert is_if_step("if proposed_changes exists")
    assert not is_if_step("what if proposed_changes exists")
    assert not is_if_step("filter(proposed_changes exists)")


def test_if_gate_pass_preserves_manifest_and_marks_gate_decision():
    manifest = {
        "dry_run": True,
        "proposed_changes": [{"current": "a", "proposed": "b"}],
        "sequence": "30sec_21",
    }

    result = IfGateNode(parse_if_step("if(proposed_changes exists)")).run(manifest)

    assert result["execution_state"] == "passed"
    assert result["if_gate"] == {
        "matched": True,
        "predicate": {"field": "proposed_changes", "operator": "exists"},
    }
    assert result["proposed_changes"] == manifest["proposed_changes"]
    assert result["sequence"] == "30sec_21"


@pytest.mark.parametrize(
    "manifest",
    [
        {"dry_run": True},
        {"dry_run": True, "proposed_changes": []},
    ],
)
def test_if_gate_miss_preserves_manifest_and_marks_skipped(manifest):
    result = IfGateNode(parse_if_step("if(proposed_changes exists)")).run(manifest)

    assert result["execution_state"] == "skipped"
    assert result["if_gate"]["matched"] is False
    assert result["dry_run"] is True


def test_if_gate_rejects_non_manifest_input():
    with pytest.raises(GraphInputError) as exc:
        IfGateNode(parse_if_step("if(proposed_changes exists)")).run([
            {"proposed_changes": []},
        ])

    assert exc.value.code == "invalid_manifest"
