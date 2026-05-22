"""Phase N+ mutation manifest contract tests."""
from __future__ import annotations

import inspect
from copy import deepcopy

import pytest

from forge_bridge.graph.mutation import (
    ChangeRecord,
    MutationManifest,
    MutationManifestError,
    validate_mutation_manifest,
)
from forge_bridge.graph.ports import (
    PortTopology,
    infer_iteration_item_topology,
    infer_topology,
)


def _manifest_dict() -> dict:
    return {
        "type": "mutation_plan",
        "intent_parameters": {"dry_run": True},
        "resolved_plan": [
            {
                "identity": {"name": "a"},
                "payload": {"value": "b"},
            },
        ],
        "originating_capability": "flame_rename_shots",
        "apply_counterpart": {
            "tool": "flame_rename_shots",
            "parameter_overrides": {"dry_run": False},
        },
    }


def _without_key(data: dict, path: tuple[str, ...]) -> dict:
    clone = deepcopy(data)
    parent = clone
    for key in path[:-1]:
        parent = parent[key]
    parent.pop(path[-1])
    return clone


def _with_value(data: dict, path: tuple[str, ...], value) -> dict:
    clone = deepcopy(data)
    parent = clone
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    return clone


def _assert_error(value, *, field_path: str, reason: str):
    error = validate_mutation_manifest(value)

    assert isinstance(error, MutationManifestError)
    assert error.field_path == field_path
    assert error.reason == reason
    assert error.to_error()["type"] == "MUTATION_MANIFEST_INVALID"
    return error


def test_valid_mutation_manifest_returns_none():
    assert validate_mutation_manifest(_manifest_dict()) is None


@pytest.mark.parametrize(
    ("value", "field_path", "reason"),
    [
        (_without_key(_manifest_dict(), ("type",)), "type", "missing"),
        (
            _with_value(_manifest_dict(), ("type",), "preview"),
            "type",
            "wrong_type_string",
        ),
        (
            _with_value(_manifest_dict(), ("intent_parameters",), []),
            "intent_parameters",
            "not_a_dict",
        ),
        (
            _with_value(_manifest_dict(), ("resolved_plan",), {}),
            "resolved_plan",
            "wrong_type_sequence",
        ),
        (
            _with_value(_manifest_dict(), ("resolved_plan",), [None]),
            "resolved_plan[0]",
            "not_a_dict",
        ),
        (
            _without_key(_manifest_dict(), ("resolved_plan", 0, "identity")),
            "resolved_plan[0].identity",
            "missing",
        ),
        (
            _with_value(_manifest_dict(), ("resolved_plan", 0, "identity"), []),
            "resolved_plan[0].identity",
            "not_a_dict",
        ),
        (
            _without_key(_manifest_dict(), ("resolved_plan", 0, "payload")),
            "resolved_plan[0].payload",
            "missing",
        ),
        (
            _with_value(_manifest_dict(), ("resolved_plan", 0, "payload"), []),
            "resolved_plan[0].payload",
            "not_a_dict",
        ),
        (
            _with_value(_manifest_dict(), ("originating_capability",), ""),
            "originating_capability",
            "wrong_type_string",
        ),
        (
            _with_value(_manifest_dict(), ("apply_counterpart",), []),
            "apply_counterpart",
            "not_a_dict",
        ),
        (
            _without_key(_manifest_dict(), ("apply_counterpart", "tool")),
            "apply_counterpart.tool",
            "missing",
        ),
        (
            _with_value(_manifest_dict(), ("apply_counterpart", "tool"), ""),
            "apply_counterpart.tool",
            "wrong_type_string",
        ),
        (
            _without_key(
                _manifest_dict(),
                ("apply_counterpart", "parameter_overrides"),
            ),
            "apply_counterpart.parameter_overrides",
            "missing",
        ),
        (
            _with_value(
                _manifest_dict(),
                ("apply_counterpart", "parameter_overrides"),
                [],
            ),
            "apply_counterpart.parameter_overrides",
            "not_a_dict",
        ),
    ],
)
def test_mutation_manifest_structural_defects_return_fielded_errors(
    value,
    field_path,
    reason,
):
    _assert_error(value, field_path=field_path, reason=reason)


def test_mutation_manifest_error_includes_expected_when_available():
    error = _assert_error(
        _with_value(_manifest_dict(), ("type",), "preview"),
        field_path="type",
        reason="wrong_type_string",
    )

    assert error.to_error()["expected"] == '"mutation_plan"'


def test_mutation_manifest_to_dict_from_dict_round_trip():
    manifest = MutationManifest(
        type="mutation_plan",
        intent_parameters={"dry_run": True},
        resolved_plan=(
            ChangeRecord(identity={"name": "a"}, payload={"value": "b"}),
        ),
        originating_capability="flame_rename_shots",
        apply_counterpart={
            "tool": "flame_rename_shots",
            "parameter_overrides": {"dry_run": False},
        },
    )

    wire = manifest.to_dict()
    restored = MutationManifest.from_dict(wire)

    assert restored == manifest
    assert restored.to_dict() == wire


def test_change_record_to_dict_from_dict_round_trip():
    record = ChangeRecord(identity={"name": "a"}, payload={"value": "b"})

    assert ChangeRecord.from_dict(record.to_dict()) == record


def test_infer_topology_recognizes_mutation_plan_as_manifest():
    topology = infer_topology({
        "type": "mutation_plan",
        "segments": [{"name": "a"}],
    })

    assert topology == PortTopology.manifest()


def test_infer_iteration_item_topology_recognizes_mutation_plan_as_manifest():
    topology = infer_iteration_item_topology(
        item={"type": "mutation_plan", "segments": [{"name": "a"}]},
        collection_topology=PortTopology.list_of("segment"),
    )

    assert topology == PortTopology.manifest()


def test_mutation_plan_type_check_precedes_collection_marker_inference():
    without_type = infer_topology({"segments": [{"name": "a"}]})
    with_type = infer_topology({
        "type": "mutation_plan",
        "segments": [{"name": "a"}],
    })

    assert without_type == PortTopology.list_of("segment")
    assert with_type == PortTopology.manifest()


def test_mutation_module_has_no_rename_domain_vocabulary():
    """17th discipline-policy enforcement test: mutation contract is generic."""
    import forge_bridge.graph.mutation as mutation_module

    src = inspect.getsource(mutation_module)
    blacklist = (
        "track_idx",
        "record_in",
        "seg_name",
        "source_name",
        "shot_name",
        "prefix",
        "padding",
        "increment",
        "start",
        "role_overrides",
        "qualifier_overrides",
        "selected_segments",
        "proposed_changes",
        "renamed",
        "shots_assigned",
        "skipped",
        "changes",
        "propagated",
        "seg_idx",
        "old",
        "new",
    )

    for token in blacklist:
        assert token not in src
