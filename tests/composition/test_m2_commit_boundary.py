from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge_bridge.composition.commit_boundary import (
    APPLY_FAILED_OPERATOR_MESSAGE,
    DRIFT_OPERATOR_MESSAGE,
    UNRATIFIED_OPERATOR_MESSAGE,
    VERIFICATION_FAILED_OPERATOR_MESSAGE,
    CommitBoundary,
)
from forge_bridge.composition.compare import (
    compare_strategy_for,
    normalize_terminal_output,
)
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError
from forge_bridge.graph.mutation import MutationManifest


_FIXTURE_DIR = Path(__file__).parent / "fixtures"


class _RenameMCP:
    def __init__(self, *, fresh_manifest: dict):
        self.calls: list[tuple[str, dict]] = []
        self._fresh_manifest = copy.deepcopy(fresh_manifest)
        self.state = {
            _identity_key(item["identity"]): item["identity"]["seg_name"]
            for item in fresh_manifest["resolved_plan"]
        }

    async def list_tools(self):
        return [
            SimpleNamespace(
                name="flame_rename_shots",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, copy.deepcopy(arguments)))
        if name != "flame_rename_shots":
            raise AssertionError(name)
        mode = arguments["mode"]
        if mode == "verify":
            return copy.deepcopy(self._fresh_manifest)
        if mode == "apply":
            return self._apply(arguments["resolved_plan"])
        raise AssertionError(mode)

    def _apply(self, plan: list[dict]) -> dict:
        for item in plan:
            self.state[_identity_key(item["identity"])] = item["payload"]["shot_name"]
        return {
            "type": "rename_apply_result",
            "renamed": len(plan),
            "post_shot_names": list(self.state.values()),
        }


class _ApplyFailureMCP(_RenameMCP):
    def __init__(self, *, fresh_manifest: dict, apply_payload: dict):
        super().__init__(fresh_manifest=fresh_manifest)
        self._apply_payload = copy.deepcopy(apply_payload)

    def _apply(self, plan: list[dict]) -> dict:
        return copy.deepcopy(self._apply_payload)


class _TransportFailureMCP(_RenameMCP):
    def __init__(self, *, fresh_manifest: dict, fail_mode: str):
        super().__init__(fresh_manifest=fresh_manifest)
        self._fail_mode = fail_mode

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, copy.deepcopy(arguments)))
        if arguments["mode"] == self._fail_mode:
            raise TimeoutError(f"{self._fail_mode} main-thread timeout")
        if arguments["mode"] == "verify":
            return copy.deepcopy(self._fresh_manifest)
        return self._apply(arguments["resolved_plan"])


def _identity_key(identity: dict) -> tuple:
    return (
        identity.get("sequence_name"),
        identity.get("track_idx"),
        identity.get("record_in"),
        identity.get("source_name"),
    )


def _held_manifest_dict() -> dict:
    return json.loads((_FIXTURE_DIR / "commit_rename_held.json").read_text())


def _drift_manifest_dict(held: dict) -> dict:
    """README-grounded drift: fresh state moved to dt_* before apply.

    The capture note says the drift recompute returns identities in the dt
    world while the held manifest identities are DATA_*, with payloads narrowed
    to shot_name. This fixture keeps that observed failure shape explicit
    without re-mutating Flame during the unit run.
    """

    drifted = copy.deepcopy(held)
    for item in drifted["resolved_plan"]:
        payload = item["payload"]
        identity = item["identity"]
        identity["seg_name"] = payload.get("segment_name") or payload["shot_name"]
        item["payload"] = {"shot_name": payload["shot_name"]}
    return drifted


def _ratified_assent() -> AssentRecord:
    return AssentRecord(
        graph_intent_id="graph-intent-commit",
        chain_steps=["commit"],
        status="ratified",
        decided_by="operator",
    )


def _commit_graph(held: dict) -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="commit",
                operator_id="commit",
                config={"held": held},
            ),
        ),
        edges=(),
    )


@pytest.mark.asyncio
async def test_commit_boundary_verifies_and_applies_once_against_controlled_state():
    held = _held_manifest_dict()
    mcp = _RenameMCP(fresh_manifest=held)
    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(
            mcp=mcp,
            artifact_id_factory=lambda: uuid.UUID(
                "00000000-0000-0000-0000-000000000301"
            ),
        ),
        assent_record=_ratified_assent(),
    )

    results = await GraphExecutor(dispatch.dispatch).run(_commit_graph(held))
    result = results["commit"]

    assert result.status == "ok"
    assert result.output["type"] == "commit_applied"
    assert result.output["verified"] is True
    assert result.output["applied"] is True
    assert result.output["count"] == len(held["resolved_plan"])
    assert result.resolved_class == "mcp.host_mutation"
    assert result.artifact_id == uuid.UUID("00000000-0000-0000-0000-000000000301")
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
        ("flame_rename_shots", "apply"),
    ]
    assert mcp.calls[0][1]["resolved_plan"] == held["resolved_plan"]
    assert mcp.calls[1][1]["resolved_plan"] == held["resolved_plan"]
    expected_names = [
        item["payload"]["shot_name"]
        for item in held["resolved_plan"]
    ]
    assert result.output["apply_result"]["post_shot_names"] == expected_names
    assert list(mcp.state.values()) == expected_names
    assert "assent" not in json.dumps(result.output).lower()
    assert "ratified" not in json.dumps(result.output).lower()


@pytest.mark.asyncio
async def test_commit_boundary_drift_aborts_before_apply_with_operator_message():
    held = _held_manifest_dict()
    mcp = _RenameMCP(fresh_manifest=_drift_manifest_dict(held))
    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )

    results = await GraphExecutor(dispatch.dispatch).run(_commit_graph(held))
    result = results["commit"]

    assert result.status == "error"
    assert result.reason_code == CommitError.PLAN_STATE_DRIFT
    assert result.message == DRIFT_OPERATOR_MESSAGE
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "apply_payload",
    [
        {
            "error": {"code": "segment_temporal_delta_apply_failed"},
            "results": [{"ok": False}],
        },
        {"error": {"code": "flame_bridge_unreachable"}},
    ],
)
async def test_commit_boundary_apply_error_payload_fails_commit(apply_payload):
    held = _held_manifest_dict()
    mcp = _ApplyFailureMCP(fresh_manifest=held, apply_payload=apply_payload)
    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )

    results = await GraphExecutor(dispatch.dispatch).run(_commit_graph(held))
    result = results["commit"]

    assert result.status == "error"
    assert result.reason_code == CommitError.APPLY_FAILED
    assert result.output == {
        "error": {
            "type": CommitError.APPLY_FAILED,
            "message": (
                "could not apply — host reported "
                f"{apply_payload['error']['code']}"
            ),
        }
    }
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
        ("flame_rename_shots", "apply"),
    ]


@pytest.mark.asyncio
async def test_commit_boundary_verify_timeout_fails_closed_before_apply():
    held = _held_manifest_dict()
    mcp = _TransportFailureMCP(fresh_manifest=held, fail_mode="verify")
    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )

    result = (await GraphExecutor(dispatch.dispatch).run(_commit_graph(held)))["commit"]

    assert result.status == "error"
    assert result.reason_code == CommitError.VERIFICATION_FAILED
    assert result.message == (
        f"{VERIFICATION_FAILED_OPERATOR_MESSAGE} "
        "(TimeoutError: verify main-thread timeout)"
    )
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
    ]


@pytest.mark.asyncio
async def test_commit_boundary_apply_timeout_is_never_laundered_into_success():
    held = _held_manifest_dict()
    mcp = _TransportFailureMCP(fresh_manifest=held, fail_mode="apply")
    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )

    result = (await GraphExecutor(dispatch.dispatch).run(_commit_graph(held)))["commit"]

    assert result.status == "error"
    assert result.reason_code == CommitError.APPLY_FAILED
    assert result.message == (
        f"{APPLY_FAILED_OPERATOR_MESSAGE} "
        "(TimeoutError: apply main-thread timeout)"
    )
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
        ("flame_rename_shots", "apply"),
    ]


@pytest.mark.asyncio
async def test_commit_boundary_requires_ratified_assent_before_apply():
    held = _held_manifest_dict()
    mcp = _RenameMCP(fresh_manifest=held)
    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=AssentRecord(
            graph_intent_id="graph-intent-commit",
            chain_steps=["commit"],
            status="proposed",
        ),
    )

    results = await GraphExecutor(dispatch.dispatch).run(_commit_graph(held))
    result = results["commit"]

    assert result.status == "error"
    assert result.reason_code == CommitError.ASSENT_INVALID
    assert result.message == UNRATIFIED_OPERATOR_MESSAGE
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
    ]


@pytest.mark.asyncio
async def test_commit_boundary_rejects_discovered_but_unreviewed_counterpart():
    held = _held_manifest_dict()
    held["apply_counterpart"]["tool"] = "forge_apply_unreviewed_host_plan"
    mcp = _RenameMCP(fresh_manifest=held)
    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )

    result = (await GraphExecutor(dispatch.dispatch).run(_commit_graph(held)))["commit"]

    assert result.status == "error"
    assert result.reason_code == CommitError.APPLY_COUNTERPART_NOT_DECLARED
    assert "not admitted" in (result.message or "")
    assert mcp.calls == []


def test_mutation_manifest_normalization_ignores_capture_metadata_only():
    held = _held_manifest_dict()
    canonical = MutationManifest.from_dict(held).to_dict()
    with_capture_changed = copy.deepcopy(held)
    with_capture_changed["_capture"] = {"note": "different capture provenance"}

    assert normalize_terminal_output(with_capture_changed) == canonical

    changed_plan = copy.deepcopy(held)
    changed_plan["resolved_plan"][0]["payload"]["shot_name"] = "different"
    assert normalize_terminal_output(changed_plan) != canonical


def test_commit_admission_selects_record_replay_compare_strategy():
    from forge_bridge.composition.compare import admitted_records_for

    records = admitted_records_for(_commit_graph(_held_manifest_dict()))

    assert records[0].operator_id == "commit"
    assert records[0].no_state_mutation is False
    assert records[0].idempotent_result is False
    assert records[0].state_owner == "dcc_host"
    assert compare_strategy_for(records) == "record_replay"
