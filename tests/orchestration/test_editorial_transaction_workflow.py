"""Acceptance matrix for #241 / Pipeline Phase 153 — the governed editorial
transaction workflow. Every numbered test maps to one bullet of the handoff's
"Acceptance Matrix".

Like the #242 matrix (and unlike #235's), these do NOT fake the commit rail:
the API is built with the REAL verify-before-apply ``CommitBoundary`` driven by
a fake MCP shaped like the Pipeline transaction callables, and a fake operation
runner for ``flame.editorial.transaction_realization``. Only Postgres is
substituted (in-memory workflow store + in-memory AssentRecord gateway), so
discover/verify/apply ordering, assent gating, and drift refusal are genuine
rail proofs.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import forge_bridge.orchestration.editorial_transaction_workflow as etw
from forge_bridge.orchestration.editorial_transaction_workflow import (
    PROPOSAL_KIND,
    RECEIPT_KIND,
    RECOVERY_TOKEN_KIND,
    TRANSACTION_RESTORE_TOOL,
    TRANSACTION_TOOL,
    EditorialTransactionWorkflowError,
    InMemoryAssentGateway,
    InMemoryEditorialTransactionWorkflowStore,
    make_editorial_transaction_workflow_api,
)

SEQ = "FORGE_UAT_TRANSACTION_20260724"
SEGMENT = "segment-a1"
SEQUENCE_ID = "sequence-1"
TRANSACTION_OPERATION_TYPE = etw.TRANSACTION_OPERATION_TYPE
RESTORE_OPERATION_TYPE = etw.TRANSACTION_RESTORE_OPERATION_TYPE
REALIZATION_TYPE = etw.TRANSACTION_REALIZATION_OPERATION_TYPE

_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "editorial_transaction_workflow_receipt.json"
)


def _fingerprint(value: Any) -> str:
    """Independent canonical fingerprint — the consumer's own arithmetic."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _h(seed: str) -> str:
    return _fingerprint(seed)


# --------------------------------------------------------------------------- #
# Proposal / realization / manifest fixtures
# --------------------------------------------------------------------------- #
def make_step_plan(
    *,
    operations: tuple[str, ...] = ("trim_head", "trim_tail"),
    segments: tuple[str, ...] | None = None,
    sequence_id: str = SEQUENCE_ID,
) -> dict[str, Any]:
    names = segments if segments is not None else (SEGMENT,) * len(operations)
    return {
        "plan_id": "phase153-transaction-plan",
        "steps": [
            {
                "operation": operation,
                "step_id": f"phase153-{index}-{operation}",
                "node_id": names[index],
                "params": {
                    "sequence_id": sequence_id,
                    "segment_id": names[index],
                    "frames": 8 + index,
                },
            }
            for index, operation in enumerate(operations)
        ],
    }


def make_proposal(
    *, step_plan: dict[str, Any] | None = None, tag: str = "a", **overrides: Any
) -> dict[str, Any]:
    plan = step_plan if step_plan is not None else make_step_plan()
    proposal = {
        "kind": PROPOSAL_KIND,
        "schema_version": 1,
        "preview_id": f"transaction-preview-{tag}",
        "project_id": "project-1",
        "sequence_id": SEQUENCE_ID,
        "sequence_name": SEQ,
        "requested_by": "artist-1",
        "source_authority": "catalog",
        "source_fingerprint": _h(f"src-{tag}"),
        "preview_authority_fingerprint": _h(f"authority-{tag}"),
        "preview_fingerprint": _h(f"preview-{tag}"),
        "interaction_fingerprint": _h(f"interaction-{tag}"),
        "source_state_fingerprint": _h(f"source-state-{tag}"),
        "final_state_fingerprint": _h(f"final-state-{tag}"),
        "step_plan": plan,
        "step_plan_fingerprint": _fingerprint(plan),
        "semantic_capability_plan_fingerprint": _h(f"semantic-{tag}"),
        "pure_apply_fingerprint": _h(f"pure-apply-{tag}"),
        "delta_set_fingerprint": _h(f"delta-set-{tag}"),
        "realization_plan_fingerprint": _h(f"realization-{tag}"),
    }
    proposal.update(overrides)
    body = {
        key: value
        for key, value in proposal.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    proposal["fingerprint"] = _fingerprint(body)
    return proposal


def make_realization(proposal: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    realization = {
        "operation_type": REALIZATION_TYPE,
        "mode": "discover",
        "status": "ready",
        "trust_status": "trusted",
        "allowed": True,
        "dispatch_authorized": False,
        "drift": False,
        "read_only": True,
        "mutation_safe": True,
        "realization_authority": "forge_flame",
        "composition_owner": "bridge",
        "step_plan_fingerprint": proposal["step_plan_fingerprint"],
        "semantic_capability_plan_fingerprint": proposal[
            "semantic_capability_plan_fingerprint"
        ],
        "apply_result_fingerprint": proposal["pure_apply_fingerprint"],
        "delta_set_fingerprint": proposal["delta_set_fingerprint"],
        "final_state_fingerprint": proposal["final_state_fingerprint"],
        "realization_plan_fingerprint": proposal["realization_plan_fingerprint"],
        "command_count": len(proposal["step_plan"]["steps"]),
    }
    realization.update(overrides)
    return realization


def make_recovery(**overrides: Any) -> dict[str, Any]:
    token = {
        "kind": RECOVERY_TOKEN_KIND,
        "schema_version": 1,
        "method": "restore_temporal_transaction",
        "sequence_name": SEQ,
        "transaction_id": "txn-phase153-1",
        "segment_id": SEGMENT,
        "restore_commands": [
            {"operation": "extend_edit", "side": "tail", "frames": 9},
            {"operation": "extend_edit", "side": "head", "frames": 8},
        ],
    }
    token.update(overrides)
    return token


def make_transaction_manifest(
    proposal: dict[str, Any], **plan_overrides: Any
) -> dict[str, Any]:
    steps = proposal["step_plan"]["steps"]
    plan = {
        "kind": "pipeline.traffik.editorial.temporal_transaction_plan",
        "schema_version": 1,
        "sequence_name": proposal["sequence_name"],
        "commands": [
            {"operation": step["operation"], "segment_id": SEGMENT}
            for step in steps
        ],
        "step_plan_fingerprint": proposal["step_plan_fingerprint"],
        "delta_set_fingerprint": proposal["delta_set_fingerprint"],
        "realization_plan_fingerprint": proposal["realization_plan_fingerprint"],
        "final_state_fingerprint": proposal["final_state_fingerprint"],
    }
    plan.update(plan_overrides)
    return {
        "kind": "pipeline.traffik.editorial.temporal_transaction_result",
        "schema_version": 1,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "state_owner": "dcc_host",
        "transaction_plan": plan,
        "intent_parameters": {
            "sequence_name": proposal["sequence_name"],
            "step_plan": proposal["step_plan"],
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": TRANSACTION_OPERATION_TYPE,
                    "realization_plan_fingerprint": proposal[
                        "realization_plan_fingerprint"
                    ],
                    "command_count": len(steps),
                },
                "payload": {"transaction_plan": plan},
            }
        ],
        "originating_capability": TRANSACTION_TOOL,
        "apply_counterpart": {
            "tool": TRANSACTION_TOOL,
            "parameter_overrides": {},
        },
    }


def make_restore_manifest(
    recovery: dict[str, Any] | None = None, **overrides: Any
) -> dict[str, Any]:
    token = recovery if recovery is not None else make_recovery()
    manifest = {
        "kind": "pipeline.traffik.editorial.temporal_transaction_restore_result",
        "schema_version": 1,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "state_owner": "dcc_host",
        "intent_parameters": {"sequence_name": SEQ, "recovery": dict(token)},
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": RESTORE_OPERATION_TYPE,
                    "transaction_id": token.get("transaction_id"),
                },
                "payload": {"recovery": dict(token)},
            }
        ],
        "originating_capability": TRANSACTION_RESTORE_TOOL,
        "apply_counterpart": {
            "tool": TRANSACTION_RESTORE_TOOL,
            "parameter_overrides": {},
        },
    }
    manifest.update(overrides)
    return manifest


_SCHEMA = {
    "type": "object",
    "properties": {
        "sequence_name": {"type": "string"},
        "step_plan": {"type": "object"},
        "recovery": {"type": "object"},
        "mode": {"type": "string"},
        "resolved_plan": {"type": "array"},
        "held_realization_plan_fingerprint": {"type": "string"},
        "held_delta_set_fingerprint": {"type": "string"},
    },
    "required": ["sequence_name"],
}


class FakeMCP:
    """Stands in for the Pipeline transaction + restore callables."""

    def __init__(
        self,
        *,
        proposal: dict[str, Any] | None = None,
        held: dict[str, Any] | None = None,
        fresh: dict[str, Any] | None = None,
        recovery: dict[str, Any] | None = -1,  # type: ignore[assignment]
        apply_ok: bool = True,
        apply_drift: bool = False,
        transaction_status: str = "committed",
        restore_held: dict[str, Any] | None = None,
        restore_fresh: dict[str, Any] | None = None,
        restore_apply_ok: bool = True,
        restore_baseline: str | None = None,
        restore_tool_present: bool = True,
        apply_delay: float = 0.0,
    ) -> None:
        base = proposal if proposal is not None else make_proposal()
        self.held = copy.deepcopy(held or make_transaction_manifest(base))
        self.fresh = copy.deepcopy(fresh if fresh is not None else self.held)
        self.recovery = make_recovery() if recovery == -1 else recovery
        self.apply_ok = apply_ok
        self.apply_drift = apply_drift
        self.transaction_status = transaction_status
        self.restore_held = copy.deepcopy(
            restore_held or make_restore_manifest(self.recovery or make_recovery())
        )
        self.restore_fresh = copy.deepcopy(
            restore_fresh if restore_fresh is not None else self.restore_held
        )
        self.restore_apply_ok = restore_apply_ok
        self.restore_baseline = restore_baseline
        self.restore_tool_present = restore_tool_present
        self.apply_delay = apply_delay
        self.calls: list[tuple[str, str]] = []
        self.arguments: list[tuple[str, dict[str, Any]]] = []
        self.apply_count = 0
        self.restore_apply_count = 0

    async def list_tools(self):
        names = [TRANSACTION_TOOL]
        if self.restore_tool_present:
            names.append(TRANSACTION_RESTORE_TOOL)
        return [
            SimpleNamespace(name=name, inputSchema=_SCHEMA) for name in names
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        mode = str(arguments.get("mode") or "read")
        self.calls.append((name, mode))
        self.arguments.append((name, copy.deepcopy(arguments)))
        if name == TRANSACTION_TOOL:
            return await self._transaction(mode, arguments)
        if name == TRANSACTION_RESTORE_TOOL:
            return await self._restore(mode, arguments)
        raise AssertionError(name)

    async def _transaction(self, mode: str, arguments: dict[str, Any]):
        if mode == "discover":
            return copy.deepcopy(self.held)
        assert arguments["resolved_plan"] == self.held["resolved_plan"]
        if mode == "verify":
            return copy.deepcopy(self.fresh)
        if mode == "apply":
            self.apply_count += 1
            if self.apply_delay:
                await asyncio.sleep(self.apply_delay)
            if self.apply_drift:
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "plan_drift",
                    "drift": True,
                    "mutation_safe": True,
                }
            if not self.apply_ok:
                # A hard native failure: the callable itself reports failure,
                # so the CommitBoundary discards the payload (see §11 ceiling).
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "apply",
                    "mutation_safe": False,
                    "error": {"code": "temporal_transaction.member_failed"},
                }
            results: list[dict[str, Any]] = [{"ok": True, "index": 0}]
            if self.recovery is not None:
                results = [{"ok": True, "recovery": copy.deepcopy(self.recovery)}]
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "state_owner": "dcc_host",
                "transaction_apply": {
                    "status": self.transaction_status,
                    "trust_status": "trusted",
                    "applied_count": 2
                    if self.transaction_status == "committed"
                    else 0,
                },
                "results": results,
            }
        raise AssertionError(mode)

    async def _restore(self, mode: str, arguments: dict[str, Any]):
        if mode == "discover":
            return copy.deepcopy(self.restore_held)
        assert arguments["resolved_plan"] == self.restore_held["resolved_plan"]
        if mode == "verify":
            return copy.deepcopy(self.restore_fresh)
        if mode == "apply":
            self.restore_apply_count += 1
            if not self.restore_apply_ok:
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "apply",
                    "mutation_safe": False,
                    "error": {"code": "temporal_transaction_restore.failed"},
                }
            restore_apply: dict[str, Any] = {
                "status": "restored",
                "trust_status": "trusted",
            }
            if self.restore_baseline is not None:
                restore_apply["terminal_state_fingerprint"] = (
                    self.restore_baseline
                )
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "state_owner": "dcc_host",
                "restore_apply": restore_apply,
                "results": [{"ok": True, "restored": True}],
            }
        raise AssertionError(mode)


class FakeOperationRunner:
    """Stands in for the Pipeline runner behind the realization operator."""

    def __init__(self, realization: dict[str, Any] | None = None) -> None:
        self.realization = realization
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail = False

    async def __call__(self, operation_type: str, **kwargs: Any):
        self.calls.append((operation_type, copy.deepcopy(kwargs)))
        if operation_type != REALIZATION_TYPE:
            raise AssertionError(operation_type)
        if self.fail:
            raise RuntimeError("realization operator unreachable")
        return SimpleNamespace(
            status="succeeded", data=copy.deepcopy(self.realization)
        )


class CountingAssentGateway(InMemoryAssentGateway):
    def __init__(self, *, ratify_takes: bool = True) -> None:
        super().__init__()
        self.proposed: list[str] = []
        self.ratified: list[str] = []
        self._ratify_takes = ratify_takes

    async def propose(self, chain_steps, *, metadata):
        record = await super().propose(chain_steps, metadata=metadata)
        self.proposed.append(record.graph_intent_id)
        return record

    async def ratify(self, graph_intent_id, *, actor):
        record = await super().ratify(graph_intent_id, actor=actor)
        self.ratified.append(graph_intent_id)
        if not self._ratify_takes:
            # A ratification that did not take: the commit rail must refuse.
            record.status = "proposed"
            record.decided_by = None
        return record


def build_api(
    *,
    proposal: dict[str, Any] | None = None,
    mcp: FakeMCP | None = None,
    realization: dict[str, Any] | None = None,
    store: Any = None,
    gateway: Any = None,
    ratify_takes: bool = True,
):
    base = proposal if proposal is not None else make_proposal()
    mcp = mcp or FakeMCP(proposal=base)
    runner = FakeOperationRunner(
        realization if realization is not None else make_realization(base)
    )
    store = store if store is not None else (
        InMemoryEditorialTransactionWorkflowStore()
    )
    gateway = gateway or CountingAssentGateway(ratify_takes=ratify_takes)
    api = make_editorial_transaction_workflow_api(
        session_factory=None,
        mcp=mcp,
        run_operation=runner,
        store=store,
        assent_gateway=gateway,
        clock=lambda: "2026-07-26T00:00:00Z",
    )
    return api, mcp, runner, store, gateway


def _args(receipt):
    return {
        "proposal_id": receipt["proposal_id"],
        "expected_proposal_fingerprint": receipt["proposal_fingerprint"],
    }


async def _applied_workflow(**kwargs):
    proposal = kwargs.pop("proposal", None) or make_proposal()
    kwargs.setdefault(
        "mcp",
        FakeMCP(
            proposal=proposal,
            restore_baseline=proposal["source_state_fingerprint"],
        ),
    )
    api, mcp, runner, store, gateway = build_api(proposal=proposal, **kwargs)
    proposed = await api.propose(proposal)
    applied = await api.ratify_apply(**_args(proposed), requested_by="artist-1")
    return api, mcp, runner, store, gateway, proposal, proposed, applied


# --------------------------------------------------------------------------- #
# Proposal admission — cardinality / command order / continuity
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_00_proposal_admission_refuses_before_any_host_contact():
    api, mcp, runner, _store, gateway = build_api()

    unknown = make_proposal()
    unknown["surprise"] = "nope"
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(unknown)
    assert exc.value.code == etw.REASON_PROPOSAL_INVALID

    missing = make_proposal()
    del missing["interaction_fingerprint"]
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(missing)
    assert exc.value.code == etw.REASON_PROPOSAL_INVALID

    drifted = make_proposal()
    drifted["fingerprint"] = "d" * 64
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(drifted)
    assert exc.value.code == etw.REASON_PROPOSAL_INVALID

    assert mcp.calls == []
    assert runner.calls == []
    assert gateway.proposed == []


@pytest.mark.parametrize(
    "operations,code",
    [
        pytest.param(
            ("trim_head",), etw.REASON_CARDINALITY_INVALID, id="one_command"
        ),
        pytest.param((), etw.REASON_CARDINALITY_INVALID, id="zero_commands"),
        pytest.param(
            ("trim_head", "trim_tail") * 5,
            etw.REASON_CARDINALITY_INVALID,
            id="ten_commands",
        ),
        pytest.param(
            ("trim_tail", "trim_head"),
            etw.REASON_COMMAND_ORDER_INVALID,
            id="reversed_order",
        ),
        pytest.param(
            ("trim_head", "rename_segment"),
            etw.REASON_COMMAND_ORDER_INVALID,
            id="unadmitted_shape",
        ),
    ],
)
@pytest.mark.asyncio
async def test_00b_cardinality_and_command_order_refuse(operations, code):
    api, mcp, runner, _store, _gateway = build_api()
    plan = make_step_plan(operations=operations)

    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(make_proposal(step_plan=plan))

    assert exc.value.code == code
    assert mcp.calls == []
    assert runner.calls == []


@pytest.mark.asyncio
async def test_00c_continuity_mismatch_refuses():
    api, mcp, _runner, _store, _gateway = build_api()

    two_segments = make_step_plan(segments=(SEGMENT, "segment-b2"))
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(make_proposal(step_plan=two_segments))
    assert exc.value.code == etw.REASON_CONTINUITY_INVALID

    other_sequence = make_step_plan(sequence_id="sequence-9")
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(make_proposal(step_plan=other_sequence))
    assert exc.value.code == etw.REASON_CONTINUITY_INVALID

    assert mcp.calls == []


# --------------------------------------------------------------------------- #
# §1 — exact proposal duplicate returns the original proposed receipt
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_01_duplicate_propose_returns_the_original_receipt():
    api, mcp, runner, _store, gateway = build_api()
    proposal = make_proposal()

    first = await api.propose(proposal)
    second = await api.propose(proposal)

    assert first == second
    assert len(gateway.proposed) == 1
    assert len(runner.calls) == 1
    assert [mode for _name, mode in mcp.calls] == ["discover"]

    # …and it stays byte-identical after the workflow advances AND is replayed,
    # even though replay_observations is inside the fingerprinted field set.
    await api.ratify_apply(**_args(first), requested_by="artist-1")
    await api.replay(**_args(first), requested_by="artist-1")
    third = await api.propose(proposal)
    assert third == first
    assert third["status"] == "proposed"
    assert third["replay_observations"] == 0
    assert third["transaction_status"] == "not_started"


@pytest.mark.asyncio
async def test_01b_receipt_equality_is_not_workflow_identity():
    """(c) replay_observations is fingerprinted, so two receipts for one
    workflow legitimately differ. Identity is (proposal_id, proposal_fp)."""
    api, _mcp, _runner, _store, _gw, _proposal, proposed, _applied = (
        await _applied_workflow()
    )

    first = await api.replay(**_args(proposed), requested_by="artist-1")
    second = await api.replay(**_args(proposed), requested_by="artist-1")

    assert first["replay_observations"] == 1
    assert second["replay_observations"] == 2
    assert first["fingerprint"] != second["fingerprint"]
    assert first["proposal_id"] == second["proposal_id"]
    assert first["proposal_fingerprint"] == second["proposal_fingerprint"]


# --------------------------------------------------------------------------- #
# §2 — changed proposal under the same preview authority refuses
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_02_changed_proposal_under_the_same_authority_refuses():
    api, mcp, _runner, _store, gateway = build_api()
    original = make_proposal()
    await api.propose(original)
    calls = len(mcp.calls)

    changed = make_proposal(
        preview_id="transaction-preview-a2",
        preview_authority_fingerprint=original[
            "preview_authority_fingerprint"
        ],
    )
    assert changed["fingerprint"] != original["fingerprint"]

    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(changed)

    assert exc.value.code == etw.REASON_PROPOSAL_INVALID
    assert len(mcp.calls) == calls  # no second discovery
    assert len(gateway.proposed) == 1


@pytest.mark.asyncio
async def test_02b_wrong_expected_fingerprint_refuses_every_transition():
    api, mcp, _runner, _store, _gateway = build_api()
    proposed = await api.propose(make_proposal())
    wrong = {
        "proposal_id": proposed["proposal_id"],
        "expected_proposal_fingerprint": "f" * 64,
    }

    for action in ("ratify_apply", "status", "replay", "restore"):
        kwargs = {} if action == "status" else {"requested_by": "artist-1"}
        receipt = await getattr(api, action)(**wrong, **kwargs)
        assert receipt["action"] == action
        assert receipt["status"] == "failed"
        assert receipt["reason_code"] == etw.REASON_PROPOSAL_CHANGED
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_02c_stale_realization_or_manifest_refuses_before_any_intent():
    """A stale semantic plan, apply receipt, delta set, realization, or
    manifest all refuse before a graph intent exists."""
    proposal = make_proposal()

    for key in (
        "semantic_capability_plan_fingerprint",
        "apply_result_fingerprint",
        "delta_set_fingerprint",
        "final_state_fingerprint",
        "realization_plan_fingerprint",
    ):
        drifted = make_realization(proposal, **{key: _h(f"stale-{key}")})
        api, mcp, _runner, _store, gateway = build_api(
            proposal=proposal, realization=drifted
        )
        with pytest.raises(EditorialTransactionWorkflowError) as exc:
            await api.propose(proposal)
        assert exc.value.code == etw.REASON_REALIZATION_DRIFT, key
        assert mcp.calls == []  # realization is fenced BEFORE the manifest
        assert gateway.proposed == []

    blocked = make_realization(proposal, trust_status="review_required")
    api, mcp, _runner, _store, gateway = build_api(
        proposal=proposal, realization=blocked
    )
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == etw.REASON_REALIZATION_UNAVAILABLE
    assert gateway.proposed == []

    stale_manifest = make_transaction_manifest(
        proposal, delta_set_fingerprint=_h("stale-delta-set")
    )
    api, mcp, _runner, _store, gateway = build_api(
        proposal=proposal, mcp=FakeMCP(proposal=proposal, held=stale_manifest)
    )
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == etw.REASON_MANIFEST_DRIFT
    assert [mode for _name, mode in mcp.calls] == ["discover"]
    assert gateway.proposed == []  # no assent for an unverified manifest


@pytest.mark.asyncio
async def test_02d_propose_persists_one_intent_assent_and_held_manifest():
    api, mcp, runner, store, gateway = build_api()

    receipt = await api.propose(make_proposal())

    assert [(name, mode) for name, mode in mcp.calls] == [
        (TRANSACTION_TOOL, "discover")
    ]
    assert mcp.apply_count == 0
    assert len(runner.calls) == 1
    assert runner.calls[0][1]["params"]["mode"] == "discover"
    assert len(gateway.proposed) == 1
    assert gateway.ratified == []

    assert receipt["kind"] == RECEIPT_KIND
    assert receipt["action"] == "propose"
    assert receipt["status"] == "proposed"
    assert receipt["trust_status"] == "trusted"
    assert receipt["assent_status"] == "proposed"
    assert receipt["command_count"] == 2
    assert receipt["dispatch_authorized"] is False
    assert receipt["manifest_fingerprint"]
    assert receipt["restore_availability"] == "not_applicable"

    row = await store.get_by_proposal_id(receipt["proposal_id"])
    assert row["forward_assent_status"] == "proposed"
    assert row["forward_commit_fingerprint"] is None
    assert row["forward_held_manifest"]["type"] == "mutation_plan"
    assert row["recovery_token"] is None


# --------------------------------------------------------------------------- #
# §3 — unratified apply refuses
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_03_unratified_apply_refuses_without_dispatch():
    api, mcp, _runner, _store, gateway = build_api(ratify_takes=False)
    proposed = await api.propose(make_proposal())

    receipt = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == etw.REASON_ASSENT_INVALID
    assert receipt["applied"] is False
    assert receipt["dispatch_authorized"] is False
    assert receipt["transaction_status"] == "not_started"
    assert mcp.apply_count == 0
    assert gateway.ratified  # ratification attempted, apply was not


# --------------------------------------------------------------------------- #
# §4 — ratified apply dispatches the aggregate callable exactly once
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_04_ratified_apply_dispatches_the_aggregate_once():
    _api, mcp, _runner, _store, gateway, _p, _proposed, applied = (
        await _applied_workflow()
    )

    assert [mode for name, mode in mcp.calls if name == TRANSACTION_TOOL] == [
        "discover",
        "verify",
        "apply",
    ]
    assert mcp.apply_count == 1
    assert len(gateway.ratified) == 1
    assert applied["status"] == "applied"
    assert applied["applied"] is True
    assert applied["assent_status"] == "applied"
    assert applied["transaction_status"] == "committed"
    assert applied["commit_fingerprint"]
    assert applied["dispatch_authorized"] is True
    assert applied["command_count"] == 2


@pytest.mark.asyncio
async def test_04b_one_assent_produces_at_most_one_dispatch():
    api, mcp, _runner, _store, _gw, _p, proposed, _applied = (
        await _applied_workflow()
    )

    second = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert second["status"] == "failed"
    assert second["reason_code"] == etw.REASON_ASSENT_INVALID
    assert mcp.apply_count == 1


@pytest.mark.asyncio
async def test_04c_concurrent_ratify_apply_dispatches_once():
    proposal = make_proposal()
    api, mcp, _runner, _store, _gateway = build_api(
        proposal=proposal,
        mcp=FakeMCP(proposal=proposal, apply_delay=0.02),
    )
    proposed = await api.propose(proposal)
    kwargs = dict(**_args(proposed), requested_by="artist-1")

    results = await asyncio.gather(
        api.ratify_apply(**kwargs), api.ratify_apply(**kwargs)
    )

    assert sorted(receipt["status"] for receipt in results) == [
        "applied",
        "failed",
    ]
    assert mcp.apply_count == 1


@pytest.mark.asyncio
async def test_04d_fresh_plan_drift_refuses_before_apply():
    proposal = make_proposal()
    drifted = make_transaction_manifest(proposal)
    drifted["resolved_plan"][0]["payload"] = {"transaction_plan": "moved"}
    api, mcp, _runner, _store, _gateway = build_api(
        proposal=proposal, mcp=FakeMCP(proposal=proposal, fresh=drifted)
    )
    proposed = await api.propose(proposal)

    receipt = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == etw.REASON_MANIFEST_DRIFT
    assert receipt["applied"] is False
    assert mcp.apply_count == 0
    assert [mode for name, mode in mcp.calls if name == TRANSACTION_TOOL] == [
        "discover",
        "verify",
    ]


# --------------------------------------------------------------------------- #
# §5 — second-member native failure returns compensated failure, unapplied
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_05_compensated_transaction_is_failed_and_unapplied():
    """The legible half: the callable returns a successful envelope whose
    ``transaction_apply.status`` reports a COMPENSATED transaction."""
    proposal = make_proposal()
    api, mcp, _runner, store, _gateway = build_api(
        proposal=proposal,
        mcp=FakeMCP(
            proposal=proposal,
            transaction_status="compensated",
            recovery=None,
        ),
    )
    proposed = await api.propose(proposal)

    receipt = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == etw.REASON_COMMIT_COMPENSATED
    assert receipt["transaction_status"] == "compensated"
    assert receipt["applied"] is False
    assert receipt["dispatch_authorized"] is False
    assert receipt["commit_fingerprint"] is None
    assert receipt["recovery_token_fingerprint"] is None
    assert receipt["restore_availability"] == "unavailable"
    assert mcp.apply_count == 1

    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["status"] == "failed"
    assert row["recovery_token"] is None

    # …and restore is not on offer over an unapplied transaction.
    restore = await api.restore(**_args(proposed), requested_by="artist-1")
    assert restore["status"] == "unavailable"
    assert restore["reason_code"] == etw.REASON_RESTORE_UNAVAILABLE
    assert mcp.restore_apply_count == 0


@pytest.mark.asyncio
async def test_05b_hard_native_failure_stays_unapplied_with_an_evidence_ceiling():
    """EVIDENCE CEILING (surfaced, not faked): when the callable reports a hard
    failure, ``CommitBoundary`` discards the host apply payload, so Bridge
    cannot read whether the host actually rolled back. It proves only what it
    controls — the workflow stays unapplied, no token is captured, restore is
    unavailable — and reports ``transaction_status="unknown"`` rather than
    claiming a compensation it did not observe.
    """
    proposal = make_proposal()
    api, mcp, _runner, store, _gateway = build_api(
        proposal=proposal, mcp=FakeMCP(proposal=proposal, apply_ok=False)
    )
    proposed = await api.propose(proposal)

    receipt = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == etw.REASON_COMMIT_FAILED
    assert receipt["applied"] is False
    assert receipt["commit_fingerprint"] is None
    assert receipt["recovery_token_fingerprint"] is None
    assert receipt["restore_availability"] == "unavailable"
    # The honest disposition: dispatched, outcome not readable at this seam.
    assert receipt["transaction_status"] == "unknown"
    assert mcp.apply_count == 1
    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["forward_commit_fingerprint"] is None


# --------------------------------------------------------------------------- #
# §6 — successful apply captures the recovery token verbatim
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_06_successful_apply_captures_the_token_byte_for_byte():
    _api, mcp, _runner, store, _gw, _p, proposed, applied = (
        await _applied_workflow()
    )

    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["recovery_token"] == make_recovery()  # verbatim, not rebuilt
    assert row["recovery_token_fingerprint"] == _fingerprint(make_recovery())
    assert applied["recovery_token_fingerprint"] == _fingerprint(
        make_recovery()
    )
    assert applied["restore_availability"] == "available"
    # the token BODY never reaches a receipt
    assert "restore_commands" not in json.dumps(applied)


@pytest.mark.asyncio
async def test_06b_missing_or_invalid_token_does_not_rewrite_the_success():
    for recovery in (
        None,
        make_recovery(schema_version=2),
        make_recovery(kind="something.else"),
        make_recovery(sequence_name="OTHER_SEQUENCE"),
        make_recovery(method=""),
    ):
        proposal = make_proposal()
        api, mcp, _runner, _store, _gateway = build_api(
            proposal=proposal,
            mcp=FakeMCP(proposal=proposal, recovery=recovery),
        )
        proposed = await api.propose(proposal)

        applied = await api.ratify_apply(
            **_args(proposed), requested_by="artist-1"
        )

        assert applied["status"] == "applied"
        assert applied["applied"] is True
        assert applied["commit_fingerprint"]
        assert applied["recovery_token_fingerprint"] is None
        assert applied["restore_availability"] == "unavailable"

        restore = await api.restore(**_args(proposed), requested_by="artist-1")
        assert restore["status"] == "unavailable"
        assert restore["reason_code"] == etw.REASON_RESTORE_UNAVAILABLE
        assert mcp.restore_apply_count == 0


# --------------------------------------------------------------------------- #
# §7 — exact replay performs zero additional MCP calls
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_07_replay_observes_without_dispatching():
    api, mcp, runner, store, gateway, _p, proposed, applied = (
        await _applied_workflow()
    )
    calls_before = list(mcp.calls)
    runner_calls_before = len(runner.calls)
    row_before = await store.get_by_proposal_id(proposed["proposal_id"])

    replayed = await api.replay(**_args(proposed), requested_by="artist-1")

    assert replayed["action"] == "replay"
    assert replayed["status"] == "applied"
    assert replayed["replayed"] is True
    assert replayed["applied"] is True
    assert replayed["replay_observations"] == 1
    assert replayed["commit_fingerprint"] == applied["commit_fingerprint"]
    assert replayed["assent_record_id"] == applied["assent_record_id"]
    assert replayed["manifest_fingerprint"] == applied["manifest_fingerprint"]
    # zero additional MCP calls, no new assent, no new manifest, no commit
    assert mcp.calls == calls_before
    assert mcp.apply_count == 1
    assert len(runner.calls) == runner_calls_before
    assert len(gateway.proposed) == 1
    assert len(gateway.ratified) == 1

    row_after = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row_after["forward_manifest_fingerprint"] == row_before[
        "forward_manifest_fingerprint"
    ]
    assert row_after["forward_commit_fingerprint"] == row_before[
        "forward_commit_fingerprint"
    ]
    assert row_after["forward_assent_record_id"] == row_before[
        "forward_assent_record_id"
    ]


@pytest.mark.asyncio
async def test_07b_replay_before_apply_is_unavailable():
    api, mcp, _runner, _store, _gateway = build_api()
    proposed = await api.propose(make_proposal())

    receipt = await api.replay(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == etw.REASON_REPLAY_UNAVAILABLE
    assert receipt["replayed"] is False
    assert mcp.apply_count == 0


# --------------------------------------------------------------------------- #
# §8 — restore uses the persisted token, a fresh manifest, a separate assent
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_08_restore_uses_the_token_a_fresh_manifest_and_a_new_assent():
    api, mcp, _runner, store, gateway, _p, proposed, applied = (
        await _applied_workflow()
    )
    calls_before = len(mcp.calls)

    restored = await api.restore(**_args(proposed), requested_by="artist-1")

    # a FRESH restore discovery, then the same verify-before-apply rail
    assert [
        mode
        for name, mode in mcp.calls[calls_before:]
        if name == TRANSACTION_RESTORE_TOOL
    ] == ["discover", "verify", "apply"]
    assert mcp.restore_apply_count == 1
    # the persisted token was handed back untouched
    discover_args = [
        arguments
        for name, arguments in mcp.arguments
        if name == TRANSACTION_RESTORE_TOOL
        and arguments.get("mode") == "discover"
    ]
    assert len(discover_args) == 1
    assert discover_args[0]["recovery"] == make_recovery()

    # a SECOND proposed AssentRecord, distinct from the forward one
    assert len(gateway.proposed) == 2
    assert len(gateway.ratified) == 2
    assert restored["restore_assent_record_id"] != restored["assent_record_id"]
    assert restored["restore_manifest_fingerprint"] != (
        restored["manifest_fingerprint"]
    )
    assert restored["restore_commit_fingerprint"] != (
        restored["commit_fingerprint"]
    )
    assert restored["status"] == "restored"
    assert restored["restored"] is True
    assert restored["restore_availability"] == "restored"

    # §9 (handoff) — every forward identity survives the restore untouched
    for key in (
        "proposal_fingerprint",
        "preview_authority_fingerprint",
        "step_plan_fingerprint",
        "semantic_capability_plan_fingerprint",
        "pure_apply_fingerprint",
        "delta_set_fingerprint",
        "realization_plan_fingerprint",
        "manifest_fingerprint",
        "assent_record_id",
        "commit_fingerprint",
        "recovery_token_fingerprint",
    ):
        assert restored[key] == applied[key], key

    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["forward_manifest_fingerprint"] != row[
        "restore_manifest_fingerprint"
    ]

    # idempotent: a second restore never dispatches a second host mutation
    again = await api.restore(**_args(proposed), requested_by="artist-1")
    assert again["status"] == "restored"
    assert mcp.restore_apply_count == 1
    assert len(gateway.proposed) == 2


@pytest.mark.asyncio
async def test_08b_restore_before_apply_is_unavailable():
    api, mcp, _runner, _store, _gateway = build_api()
    proposed = await api.propose(make_proposal())

    receipt = await api.restore(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == etw.REASON_RESTORE_UNAVAILABLE
    assert mcp.restore_apply_count == 0


@pytest.mark.asyncio
async def test_08c_undiscoverable_counterpart_is_restore_unavailable():
    proposal = make_proposal()
    api, mcp, _runner, _store, _gateway = build_api(
        proposal=proposal,
        mcp=FakeMCP(proposal=proposal, restore_tool_present=False),
    )
    proposed = await api.propose(proposal)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.restore(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == etw.REASON_RESTORE_UNAVAILABLE
    assert mcp.restore_apply_count == 0


@pytest.mark.asyncio
async def test_08d_concurrent_restore_mutates_once():
    proposal = make_proposal()
    api, mcp, _runner, _store, gateway = build_api(
        proposal=proposal,
        mcp=FakeMCP(
            proposal=proposal,
            restore_baseline=proposal["source_state_fingerprint"],
        ),
    )
    proposed = await api.propose(proposal)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")
    kwargs = dict(**_args(proposed), requested_by="artist-1")

    results = await asyncio.gather(api.restore(**kwargs), api.restore(**kwargs))

    assert [receipt["status"] for receipt in results] == [
        "restored",
        "restored",
    ]
    assert mcp.restore_apply_count == 1
    assert len(gateway.proposed) == 2


# --------------------------------------------------------------------------- #
# §9 — restore success reaches the exact Pipeline baseline
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_09_restore_success_reaches_the_pipeline_baseline():
    _api, _mcp, _runner, store, _gw, proposal, proposed, _applied = (
        await _applied_workflow()
    )
    api = _api

    restored = await api.restore(**_args(proposed), requested_by="artist-1")

    assert restored["terminal_baseline_fingerprint"] == proposal[
        "source_state_fingerprint"
    ]
    assert restored["terminal_baseline_verified"] is True
    assert restored["transaction_status"] == "restored"
    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["terminal_baseline_verified"] is True


@pytest.mark.asyncio
async def test_09b_unreported_or_mismatched_baseline_is_not_claimed_verified():
    """Bridge reports what the apply result carries — it never certifies a
    baseline the host did not report."""
    for baseline in (None, _h("some-other-state")):
        proposal = make_proposal()
        api, _mcp, _runner, _store, _gateway = build_api(
            proposal=proposal,
            mcp=FakeMCP(proposal=proposal, restore_baseline=baseline),
        )
        proposed = await api.propose(proposal)
        await api.ratify_apply(**_args(proposed), requested_by="artist-1")

        restored = await api.restore(
            **_args(proposed), requested_by="artist-1"
        )

        assert restored["status"] == "restored"
        assert restored["terminal_baseline_verified"] is False
        assert restored["terminal_baseline_fingerprint"] == baseline


# --------------------------------------------------------------------------- #
# §10 — failed restore remains applied
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_10_failed_restore_leaves_the_workflow_applied():
    proposal = make_proposal()
    api, mcp, _runner, store, _gateway = build_api(
        proposal=proposal,
        mcp=FakeMCP(proposal=proposal, restore_apply_ok=False),
    )
    proposed = await api.propose(proposal)
    applied = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.restore(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == etw.REASON_RESTORE_FAILED
    assert receipt["restored"] is False
    assert receipt["restore_commit_fingerprint"] is None
    assert receipt["restore_assent_record_id"]  # the assent WAS taken
    assert mcp.restore_apply_count == 1

    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["status"] == "applied"  # the forward apply still stands
    assert row["transaction_status"] == "committed"
    assert row["forward_commit_fingerprint"] == applied["commit_fingerprint"]

    status = await api.status(**_args(proposed))
    assert status["status"] == "applied"
    assert status["applied"] is True
    assert status["restore_availability"] == "available"


# --------------------------------------------------------------------------- #
# §11 — token tamper and live drift refuse before restore dispatch
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_11_token_tamper_refuses_before_restore_dispatch():
    _api, mcp, _runner, store, _gw, _p, proposed, _applied = (
        await _applied_workflow()
    )
    api = _api
    calls_before = len(mcp.calls)
    # Tamper with the persisted token, leaving its fingerprint intact.
    tampered = make_recovery(transaction_id="txn-someone-else")
    await store.update(
        proposed["proposal_id"], {"recovery_token": tampered}
    )

    receipt = await api.restore(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == etw.REASON_RESTORE_DRIFT
    assert mcp.restore_apply_count == 0
    assert mcp.calls[calls_before:] == []  # never even discovered


@pytest.mark.asyncio
async def test_11b_restore_discovery_drift_refuses_before_dispatch():
    for mutate in (
        {"originating_capability": "forge_apply_segment_split_restore"},
        {"trust_status": "review_required"},
        {"intent_parameters": {"sequence_name": SEQ, "recovery": {"a": 1}}},
        {"intent_parameters": {"sequence_name": "OTHER", "recovery": {}}},
    ):
        proposal = make_proposal()
        drifted = make_restore_manifest(**mutate)
        api, mcp, _runner, _store, gateway = build_api(
            proposal=proposal,
            mcp=FakeMCP(proposal=proposal, restore_held=drifted),
        )
        proposed = await api.propose(proposal)
        await api.ratify_apply(**_args(proposed), requested_by="artist-1")
        proposed_assents = len(gateway.proposed)

        receipt = await api.restore(
            **_args(proposed), requested_by="artist-1"
        )

        assert receipt["status"] == "failed", mutate
        assert receipt["reason_code"] == etw.REASON_RESTORE_DRIFT, mutate
        assert mcp.restore_apply_count == 0
        # no restore assent is persisted for an untrusted counterpart
        assert len(gateway.proposed) == proposed_assents
        assert receipt["restore_assent_record_id"] is None


@pytest.mark.asyncio
async def test_11c_restore_verify_drift_refuses_at_the_commit_boundary():
    """Live host drift between the fresh restore discover and its verify."""
    proposal = make_proposal()
    fresh = make_restore_manifest()
    fresh["resolved_plan"][0]["payload"] = {"recovery": "moved"}
    api, mcp, _runner, store, _gateway = build_api(
        proposal=proposal,
        mcp=FakeMCP(proposal=proposal, restore_fresh=fresh),
    )
    proposed = await api.propose(proposal)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.restore(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == etw.REASON_RESTORE_FAILED
    assert mcp.restore_apply_count == 0  # verify refused before apply
    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["status"] == "applied"


# --------------------------------------------------------------------------- #
# §12 — v1.9.11's one-step matrix stays byte-compatible
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_12_one_step_proposals_still_route_the_v1911_path(monkeypatch):
    """A one-command proposal is REFUSED here on cardinality and continues
    through the shipped v1.9.11 single-edit workflow unchanged.

    The full v1.9.11 matrix is proven by its own shipped suites
    (``test_editorial_edit_workflow*.py``), which this change does not touch.
    This test proves the routing seam itself: the same one-step edit is
    rejected by #241 and accepted by #235, and #235's receipt kind, proposal
    kind, and closed field set are unmoved.
    """
    import forge_bridge.orchestration.editorial_edit_workflow as eew
    from tests.orchestration.test_editorial_edit_workflow import (
        _activate,
        build_api as build_one_step_api,
        make_proposal as make_one_step_proposal,
    )

    # (a) #241 refuses a one-command transaction on cardinality, without
    #     touching the host.
    api, mcp, runner, _store, gateway = build_api()
    one_command = make_proposal(
        step_plan=make_step_plan(operations=("trim_head",))
    )
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(one_command)
    assert exc.value.code == etw.REASON_CARDINALITY_INVALID
    assert mcp.calls == []
    assert runner.calls == []
    assert gateway.proposed == []

    # (b) the shipped v1.9.11 path still accepts that same one-step edit and
    #     still emits its own receipt kind, unchanged.
    one_step_api, recorder, _store = build_one_step_api(monkeypatch)
    one_step_proposal = make_one_step_proposal()
    _activate(one_step_proposal)
    receipt = await one_step_api.propose(one_step_proposal)
    assert receipt["kind"] == eew.RECEIPT_KIND
    assert receipt["kind"] != RECEIPT_KIND
    assert receipt["status"] == "proposed"
    assert recorder.preview_calls == 1

    # (c) the two contracts share no kind and no closed field set.
    assert eew.PROPOSAL_KIND != PROPOSAL_KIND
    assert set(eew._RECEIPT_KEYS) != set(etw._RECEIPT_KEYS)
    # #235 keeps its own fingerprint arithmetic (over EVERY key); #241 uses
    # the #242 exclusion rule. Neither silently governs the other.
    assert etw._RECEIPT_FINGERPRINT_EXCLUDES == {"kind", "schema_version"}


# --------------------------------------------------------------------------- #
# Receipt closure, self-verification, and privacy
# --------------------------------------------------------------------------- #
_RECEIPT_FIELDS = set(etw._RECEIPT_KEYS) | {"fingerprint"}

_FORBIDDEN_RECEIPT_SUBSTRINGS = (
    "transaction_plan",
    "resolved_plan",
    "intent_parameters",
    "apply_counterpart",
    "held_manifest",
    "restore_commands",
    "segment_id",
    "step_id",
    "plan_id",
    "node_id",
    SEGMENT,
    SEQ,
)


async def _every_receipt() -> dict[str, dict[str, Any]]:
    """One receipt from every terminal, captured from the LIVE API."""
    proposal = make_proposal()
    api, _mcp, _runner, _store, _gw, _proposal, proposed, applied = (
        await _applied_workflow(proposal=proposal)
    )
    replayed = await api.replay(**_args(proposed), requested_by="artist-1")
    restored = await api.restore(**_args(proposed), requested_by="artist-1")

    fresh_proposal = make_proposal(tag="b")
    bad_api, _m2, _r2, _s2, _g2 = build_api(
        proposal=fresh_proposal,
        mcp=FakeMCP(proposal=fresh_proposal, apply_ok=False),
    )
    bad_proposed = await bad_api.propose(fresh_proposal)
    failed = await bad_api.ratify_apply(
        **_args(bad_proposed), requested_by="artist-1"
    )
    unavailable = await bad_api.restore(
        **_args(bad_proposed), requested_by="artist-1"
    )
    status = await bad_api.status(**_args(bad_proposed))

    return {
        "proposed": proposed,
        "applied": applied,
        "replayed": replayed,
        "restored": restored,
        "failed": failed,
        "unavailable": unavailable,
        "status": status,
    }


@pytest.mark.asyncio
async def test_13_every_receipt_is_closed_and_self_verifying():
    receipts = await _every_receipt()

    for name, receipt in receipts.items():
        assert set(receipt) == _RECEIPT_FIELDS, name
        assert receipt["kind"] == RECEIPT_KIND, name
        assert receipt["schema_version"] == 1, name
        assert receipt["action"] in {
            "propose",
            "ratify_apply",
            "status",
            "replay",
            "restore",
        }, name
        assert receipt["status"] in {
            "proposed",
            "applied",
            "failed",
            "unavailable",
            "restored",
        }, name
        assert receipt["transaction_status"] in etw._TRANSACTION_STATUSES, name
        assert receipt["restore_availability"] in etw._RESTORE_AVAILABILITY
        if receipt["reason_code"] is not None:
            assert receipt["reason_code"] in etw._REASON_CODES, name
            assert receipt["reason_code"].startswith("transaction_workflow_")
        # (a) fingerprint excludes kind, schema_version, and itself
        body = {
            key: value
            for key, value in receipt.items()
            if key not in {"kind", "schema_version", "fingerprint"}
        }
        assert receipt["fingerprint"] == _fingerprint(body), name
        for field in (
            "dispatch_authorized",
            "applied",
            "replayed",
            "restored",
            "terminal_baseline_verified",
        ):
            assert isinstance(receipt[field], bool), (name, field)
        assert isinstance(receipt["replay_observations"], int), name
        assert receipt["command_count"] == 2, name


@pytest.mark.asyncio
async def test_14_serialized_receipts_carry_no_paths_or_held_payload_bodies():
    receipts = await _every_receipt()

    for name, receipt in receipts.items():
        serialized = json.dumps(receipt, sort_keys=True)
        assert "/" not in serialized, name
        for needle in _FORBIDDEN_RECEIPT_SUBSTRINGS:
            assert needle not in serialized, (name, needle)
        for key, value in receipt.items():
            # every value is a scalar — no structured body can ride out
            assert not isinstance(value, (dict, list)), (name, key)


@pytest.mark.asyncio
async def test_14b_typed_errors_carry_no_paths():
    api, _mcp, _runner, _store, _gateway = build_api()
    plan = make_step_plan(operations=("trim_tail", "trim_head"))

    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.propose(make_proposal(step_plan=plan))

    assert "/" not in str(exc.value)
    assert "/" not in exc.value.message


@pytest.mark.asyncio
async def test_15_unknown_proposal_raises_a_typed_error():
    api, _mcp, _runner, _store, _gateway = build_api()
    with pytest.raises(EditorialTransactionWorkflowError) as exc:
        await api.status(
            proposal_id="etw_deadbeefdeadbeef",
            expected_proposal_fingerprint="0" * 64,
        )
    assert exc.value.code == etw.REASON_PROPOSAL_NOT_FOUND


@pytest.mark.asyncio
async def test_16_restart_preserves_every_durable_authority():
    proposal = make_proposal()
    api, mcp, _runner, store, gateway, _p, proposed, applied = (
        await _applied_workflow(proposal=proposal)
    )

    restarted = make_editorial_transaction_workflow_api(
        session_factory=None,
        mcp=mcp,
        run_operation=FakeOperationRunner(make_realization(proposal)),
        store=store,
        assent_gateway=gateway,
        clock=lambda: "2026-07-26T01:00:00Z",
    )

    duplicate = await restarted.propose(proposal)
    assert duplicate == proposed

    status = await restarted.status(**_args(proposed))
    assert status["status"] == "applied"
    assert status["manifest_fingerprint"] == applied["manifest_fingerprint"]
    assert status["recovery_token_fingerprint"] == applied[
        "recovery_token_fingerprint"
    ]

    restored = await restarted.restore(
        **_args(proposed), requested_by="artist-1"
    )
    assert restored["status"] == "restored"
    assert mcp.restore_apply_count == 1


# --------------------------------------------------------------------------- #
# Published receipt fixture — the shape Pipeline pins against
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_17_the_published_fixture_matches_the_live_receipts():
    """The committed fixture is CAPTURED from the live API, not hand-written,
    so it is a real pin for a consumer adapter rather than a wish."""
    live = await _every_receipt()
    fixture = json.loads(_FIXTURE.read_text())

    assert set(fixture) == set(live)
    for name, receipt in fixture.items():
        # identities are per-run; compare the closed SHAPE and the arithmetic
        assert set(receipt) == _RECEIPT_FIELDS, name
        body = {
            key: value
            for key, value in receipt.items()
            if key not in {"kind", "schema_version", "fingerprint"}
        }
        assert receipt["fingerprint"] == _fingerprint(body), name
        assert receipt["kind"] == RECEIPT_KIND, name
        assert receipt["action"] == live[name]["action"], name
        assert receipt["status"] == live[name]["status"], name
        assert receipt["transaction_status"] == live[name][
            "transaction_status"
        ], name
        assert receipt["restore_availability"] == live[name][
            "restore_availability"
        ], name
        assert receipt["reason_code"] == live[name]["reason_code"], name
        serialized = json.dumps(receipt, sort_keys=True)
        assert "/" not in serialized, name
