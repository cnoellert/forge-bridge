"""Routing-real stage graph primitive contracts."""
from __future__ import annotations

import pytest

from forge_bridge.graph import (
    StageError,
    StageNode,
    is_stage_step,
    parse_stage_step,
)
from forge_bridge.graph.mutation import validate_mutation_manifest


def _assessment(disposition: str = "drifted") -> dict:
    return {
        "disposition": disposition,
        "verdict": "do-not-leak",
        "artifact": {
            "assessment_reason": "Vision says the edges drifted.",
            "source_characterization_id": "src-1",
            "comp_characterization_id": "comp-1",
        },
    }


def test_parse_stage_step_accepts_closed_review_kinds():
    assert is_stage_step("stage(ee_drift_review)")
    assert parse_stage_step("stage(ee_drift_review)") == "ee_drift_review"
    assert parse_stage_step("stage(ee_needs_human_look)") == (
        "ee_needs_human_look"
    )


def test_parse_stage_step_rejects_unknown_kind():
    with pytest.raises(StageError) as exc:
        parse_stage_step("stage(run_pipeline)")

    assert exc.value.code == "UNKNOWN_STAGE_KIND"


def test_stage_parameters_project_reason_first_and_exclude_verdict():
    params = StageNode("ee_drift_review").parameters(_assessment())

    assert list(params)[0] == "assessment_reason"
    assert params["assessment_reason"] == "Vision says the edges drifted."
    assert params["disposition"] == "drifted"
    assert "verdict" not in params
    assert params["terminus"] == (
        "human_review_only — no downstream action fires on approval "
        "(action-real deferred)"
    )


def test_stage_result_is_not_a_mutation_manifest():
    result = {
        "type": "staged_for_review",
        "staged_operation_id": "op-1",
        "disposition": "drifted",
        "review_kind": "ee_drift_review",
    }

    error = validate_mutation_manifest(result)

    assert error is not None
    assert error.field_path == "type"
