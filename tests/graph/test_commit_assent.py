from __future__ import annotations

from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError, CommitNode
from forge_bridge.graph.mutation import MutationManifest


def _record(name: str, value: str) -> dict:
    return {
        "identity": {"name": name},
        "payload": {"value": value},
    }


def _manifest_object(records: list[dict] | None = None) -> MutationManifest:
    return MutationManifest.from_dict({
        "type": "mutation_plan",
        "intent_parameters": {"request": "demo"},
        "resolved_plan": records or [_record("a", "one")],
        "originating_capability": "apply_plan",
        "apply_counterpart": {
            "tool": "apply_plan",
            "parameter_overrides": {"dry_run": False},
        },
    })


def _assent(status: str) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="abc123def456",
        chain_steps=["apply_plan", "commit"],
        status=status,
    )


def test_commit_verify_without_assent_keeps_backward_compatible_defaults():
    held = _manifest_object([_record("a", "one")])
    fresh = _manifest_object([_record("a", "one")])

    verification = CommitNode().verify(held, fresh)

    assert verification.matched is True
    assert verification.drift_count == 0
    assert verification.first_drift_index is None
    assert verification.assent_valid is True
    assert verification.assent_record is None


def test_commit_verify_ratified_assent_passes_independently_of_drift():
    held = _manifest_object([_record("a", "one")])
    fresh = _manifest_object([_record("a", "one")])
    assent = _assent("ratified")

    verification = CommitNode().verify(held, fresh, assent=assent)

    assert verification.matched is True
    assert verification.drift_count == 0
    assert verification.first_drift_index is None
    assert verification.assent_valid is True
    assert verification.assent_record is assent


def test_commit_verify_proposed_assent_fails_without_changing_drift_signal():
    held = _manifest_object([_record("a", "one")])
    fresh = _manifest_object([_record("a", "one")])
    assent = _assent("proposed")

    verification = CommitNode().verify(held, fresh, assent=assent)

    assert verification.matched is True
    assert verification.drift_count == 0
    assert verification.first_drift_index is None
    assert verification.assent_valid is False
    assert verification.assent_record is assent


def test_commit_verify_drift_and_assent_are_independent_signals():
    held = _manifest_object([_record("a", "one"), _record("b", "two")])
    fresh = _manifest_object([_record("a", "other"), _record("b", "other")])

    ratified = CommitNode().verify(held, fresh, assent=_assent("ratified"))
    proposed = CommitNode().verify(held, fresh, assent=_assent("proposed"))

    assert ratified.matched is False
    assert ratified.drift_count == 2
    assert ratified.first_drift_index == 0
    assert ratified.assent_valid is True

    assert proposed.matched is False
    assert proposed.drift_count == 2
    assert proposed.first_drift_index == 0
    assert proposed.assent_valid is False


def test_commit_error_assent_invalid_shape_is_conditional():
    error = CommitError(
        CommitError.ASSENT_INVALID,
        "AssentRecord is not in ratified state.",
        graph_intent_id="abc123def456",
    ).to_error()

    assert CommitError.ASSENT_INVALID == "ASSENT_INVALID"
    assert error == {
        "type": "ASSENT_INVALID",
        "message": "AssentRecord is not in ratified state.",
        "graph_intent_id": "abc123def456",
    }

    drift = CommitError(
        CommitError.PLAN_STATE_DRIFT,
        "Mutation plan no longer matches current state.",
        drift_count=2,
        first_drift_index=1,
    ).to_error()

    assert drift == {
        "type": "PLAN_STATE_DRIFT",
        "message": "Mutation plan no longer matches current state.",
        "drift_count": 2,
        "first_drift_index": 1,
    }
