"""Phase N+ commit graph primitive contracts."""
from __future__ import annotations

import asyncio
import inspect
import json
from copy import deepcopy
from types import SimpleNamespace

from forge_bridge.console._step import execute_chain_step
from forge_bridge.graph.commit import (
    CommitNode,
    is_commit_step,
    parse_commit_step,
)
from forge_bridge.graph.mutation import (
    ChangeRecord,
    MutationManifest,
)
from forge_bridge.graph.ports import PortTopology, infer_topology

from tests.console.test_pr30_chain import _text_block


def _record(name: str, value: str) -> dict:
    return {
        "identity": {"name": name},
        "payload": {"value": value},
    }


def _manifest(records: list[dict] | None = None) -> dict:
    return {
        "type": "mutation_plan",
        "intent_parameters": {"request": "demo"},
        "resolved_plan": records or [_record("a", "one")],
        "originating_capability": "apply_plan",
        "apply_counterpart": {
            "tool": "apply_plan",
            "parameter_overrides": {"dry_run": False},
        },
    }


def _tool(name: str = "apply_plan"):
    return SimpleNamespace(name=name)


class VerifyMCP:
    def __init__(self, result: dict):
        self.result = result
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return _text_block(json.dumps(self.result))


def _run_commit(previous: dict, *, tools=None, fresh: dict | None = None):
    mcp = VerifyMCP(fresh or previous)
    result = asyncio.run(execute_chain_step(
        step_text="commit",
        tools=[_tool()] if tools is None else tools,
        mcp=mcp,
        inherited_context={
            "__previous_result__": previous,
            "__previous_topology__": PortTopology.manifest().to_dict(),
        },
        step_index=3,
    ))
    return result, mcp


def _manifest_object(records: list[dict] | None = None) -> MutationManifest:
    return MutationManifest.from_dict(_manifest(records))


def test_commit_valid_manifest_verifies_clean():
    result, mcp = _run_commit(_manifest())

    assert result["tool"] == "graph_commit"
    assert result["result"]["message"] == "verified, would apply"
    assert result["result"]["applied"] is False
    assert result["result"]["count"] == 1
    assert result["extracted_context"] == {}
    assert result["emitted_topology"] == {"kind": "manifest"}
    assert mcp.calls == [(
        "apply_plan",
        {
            "request": "demo",
            "dry_run": False,
            "mode": "verify",
            "resolved_plan": [_record("a", "one")],
        },
    )]


def test_commit_invalid_manifest_returns_manifest_error():
    value = deepcopy(_manifest())
    value["type"] = "preview"

    result, mcp = _run_commit(value)

    assert result["error"]["type"] == "MUTATION_MANIFEST_INVALID"
    assert result["error"]["step_index"] == 3
    assert result["error"]["step"] == "commit"
    assert mcp.calls == []


def test_commit_unregistered_apply_counterpart_returns_declared_error():
    result, mcp = _run_commit(_manifest(), tools=[])

    assert result["error"]["type"] == "APPLY_COUNTERPART_NOT_DECLARED"
    assert result["error"]["step_index"] == 3
    assert result["error"]["step"] == "commit"
    assert mcp.calls == []


def test_commit_drifted_resolved_plan_returns_drift_envelope():
    held = _manifest([_record("a", "one"), _record("b", "two")])
    fresh = _manifest([_record("a", "one"), _record("b", "different")])

    result, _mcp = _run_commit(held, fresh=fresh)

    assert result["error"]["type"] == "PLAN_STATE_DRIFT"
    assert result["error"]["step_index"] == 3
    assert result["error"]["step"] == "commit"
    assert result["error"]["drift_count"] == 1
    assert result["error"]["first_drift_index"] == 1


def test_commit_node_structural_comparison_matches_identical_plan():
    held = _manifest_object([_record("a", "one")])
    fresh = _manifest_object([_record("a", "one")])

    verification = CommitNode().verify(held, fresh)

    assert verification.matched is True
    assert verification.drift_count == 0
    assert verification.first_drift_index is None


def test_commit_node_structural_comparison_finds_single_record_drift():
    held = _manifest_object([_record("a", "one"), _record("b", "two")])
    fresh = _manifest_object([_record("a", "one"), _record("b", "other")])

    verification = CommitNode().verify(held, fresh)

    assert verification.matched is False
    assert verification.drift_count == 1
    assert verification.first_drift_index == 1


def test_commit_node_structural_comparison_finds_multi_record_drift():
    held = _manifest_object([_record("a", "one"), _record("b", "two")])
    fresh = _manifest_object([_record("a", "other"), _record("b", "other")])

    verification = CommitNode().verify(held, fresh)

    assert verification.matched is False
    assert verification.drift_count == 2
    assert verification.first_drift_index == 0


def test_commit_topology_binding_accepts_mutation_manifest():
    assert CommitNode.port_contract.accepts_topology(PortTopology.manifest())
    assert infer_topology(_manifest()) == PortTopology.manifest()


def test_commit_bare_step_recognition():
    assert is_commit_step("commit")
    assert is_commit_step("  commit  ")
    assert not is_commit_step("commit now")
    assert parse_commit_step("commit") is None


def test_commit_determinism_uses_positionally_identical_plan():
    first = _manifest_object([_record("a", "one"), _record("b", "two")])
    second = _manifest_object([_record("a", "one"), _record("b", "two")])

    assert first.resolved_plan == second.resolved_plan
    assert CommitNode().verify(first, second).matched is True


def test_commit_manifest_records_round_trip_as_tuple():
    manifest = MutationManifest(
        type="mutation_plan",
        intent_parameters={"request": "demo"},
        resolved_plan=(
            ChangeRecord(identity={"name": "a"}, payload={"value": "one"}),
        ),
        originating_capability="apply_plan",
        apply_counterpart={
            "tool": "apply_plan",
            "parameter_overrides": {"dry_run": False},
        },
    )

    assert MutationManifest.from_dict(manifest.to_dict()) == manifest


def test_commit_module_has_no_rename_domain_vocabulary():
    """18th discipline-policy enforcement test: commit contract is generic."""
    import forge_bridge.graph.commit as commit_module

    src = inspect.getsource(commit_module)
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
