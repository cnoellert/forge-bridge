"""Acceptance matrix for #242 / Pipeline Phase 156 — the workspace publish
workflow API. Every numbered test below maps to one item of handoff §11.

Unlike the #235 matrix, these do NOT fake the commit rail: the API is built
with the real ``MCPToolBoundary`` discovery dispatch and the real
verify-before-apply ``CommitBoundary``, driven by a fake MCP shaped like the
Pipeline callables. Only Postgres is substituted (in-memory workflow store +
in-memory AssentRecord gateway), so discover/verify/apply ordering, assent
gating, and plan-drift refusal are proven end-to-end at this seam.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from types import SimpleNamespace
from typing import Any

import pytest

import forge_bridge.orchestration.editorial_workspace_publish_workflow as epw
from forge_bridge.orchestration.editorial_workspace_publish_workflow import (
    ABORT_TOOL,
    INSPECT_TOOL,
    PROPOSAL_KIND,
    PUBLISH_TOOL,
    RECEIPT_KIND,
    EditorialWorkspacePublishWorkflowError,
    InMemoryAssentGateway,
    InMemoryEditorialWorkspacePublishWorkflowStore,
    make_editorial_workspace_publish_workflow_api,
)

CANONICAL = "/show/FORGE_UAT"
TRANSACTION_ID = "txn-sh010-comp-artist_a-v002"
SOURCE_VERSION_ID = "version-1"
ROLES = ("beauty", "matte")
CALLABLE_OPERATION_TYPE = "pipeline.shot_resource.publish_transaction.callable"
ABORT_OPERATION_TYPE = (
    "pipeline.shot_resource.publish_transaction.abort.callable"
)


def _fingerprint(value: Any) -> str:
    """Independent canonical fingerprint — the consumer's own arithmetic."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# --------------------------------------------------------------------------- #
# Proposal / manifest fixtures
# --------------------------------------------------------------------------- #
def make_callable_intent(**overrides: Any) -> dict[str, Any]:
    intent = {
        "tool": PUBLISH_TOOL,
        "operation_type": CALLABLE_OPERATION_TYPE,
        "params": {
            "canonical": CANONICAL,
            "shot": "sh010",
            "task": "comp",
            "stream": "artist_a",
            "roles": list(ROLES),
            "outputs": [
                {
                    "role": role,
                    # A private absolute path: must never reach a receipt.
                    "source_path": f"/capture/{role}.1001.exr",
                    "lineage_asset_ids": [SOURCE_VERSION_ID],
                }
                for role in ROLES
            ],
        },
        "bridge_asset_ids": [SOURCE_VERSION_ID],
        "idempotency_key": "publish-transaction-1",
        "project_id": "project-1",
        "requested_by": "artist-1",
    }
    intent.update(overrides)
    return intent


def make_proposal(
    *, callable_intent: dict[str, Any] | None = None, **overrides: Any
) -> dict[str, Any]:
    intent = callable_intent if callable_intent is not None else (
        make_callable_intent()
    )
    proposal = {
        "kind": PROPOSAL_KIND,
        "schema_version": 1,
        "project_id": "project-1",
        "requested_by": "artist-1",
        "publish_preview_id": "publish-preview-1",
        "publish_preview_fingerprint": "a" * 64,
        "transaction_batch_fingerprint": "b" * 64,
        "callable_intent_fingerprint": _fingerprint(intent),
        "owner_id": "shot-1",
        "owner_type": "shot",
        "sequence_id": "sequence-1",
        "task": "comp",
        "role": "comp",
        "stream": "artist_a",
        "source_version_id": SOURCE_VERSION_ID,
        "source_package_fingerprint": "c" * 64,
        "selected_roles": sorted(ROLES),
        "callable_intent": intent,
    }
    proposal.update(overrides)
    body = {
        key: value
        for key, value in proposal.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    proposal["fingerprint"] = _fingerprint(body)
    return proposal


def _transaction_plan(*, version: str = "v002") -> dict[str, Any]:
    return {
        "kind": "pipeline.shot_resource.publish_transaction_plan",
        "schema_version": 1,
        "status": "ready",
        "trust_status": "trusted",
        "ready_for_apply": True,
        "mutation_safe": True,
        "transaction_id": TRANSACTION_ID,
        "canonical": CANONICAL,
        "shot": "sh010",
        "task": "comp",
        "stream": "artist_a",
        "version": version,
        "roles": list(ROLES),
        "selected_roles": list(ROLES),
        "actions": [
            {
                "role": role,
                "lineage_asset_ids": [SOURCE_VERSION_ID],
                "final_version_path": f"{CANONICAL}/sh010/{role}/{version}",
            }
            for role in ROLES
        ],
    }


def _publish_manifest(
    *, version: str = "v002", intent: dict[str, Any] | None = None
) -> dict[str, Any]:
    callable_intent = intent if intent is not None else make_callable_intent()
    plan = _transaction_plan(version=version)
    return {
        "kind": "pipeline.shot_resource.callable_publish_transaction_result",
        "schema_version": 1,
        "operation_type": CALLABLE_OPERATION_TYPE,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "state_owner": "federated_transaction",
        "transaction_plan": plan,
        "intent_parameters": {
            "params": dict(callable_intent["params"]),
            "idempotency_key": callable_intent["idempotency_key"],
            "bridge_asset_ids": list(callable_intent["bridge_asset_ids"]),
            "project_id": callable_intent["project_id"],
            "requested_by": callable_intent["requested_by"],
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": CALLABLE_OPERATION_TYPE,
                    "transaction_id": TRANSACTION_ID,
                    "stream": "artist_a",
                    "version": version,
                    "roles": list(ROLES),
                },
                "payload": {"transaction_plan": plan},
            }
        ],
        "originating_capability": PUBLISH_TOOL,
        "apply_counterpart": {"tool": PUBLISH_TOOL, "parameter_overrides": {}},
    }


def _abort_plan(
    *,
    journal_sha256: str = "journal-sha-1",
    ready: bool = True,
    transaction_id: str = TRANSACTION_ID,
) -> dict[str, Any]:
    return {
        "kind": "pipeline.shot_resource.publish_transaction_abort_plan",
        "schema_version": 1,
        "status": "ready" if ready else "blocked",
        "trust_status": "trusted" if ready else "review_required",
        "ready_for_abort": ready,
        "mutation_safe": True,
        "state_owner": "peer_owned",
        "canonical": CANONICAL,
        "transaction_id": transaction_id,
        "journal_path": (
            f"{CANONICAL}/.forge/publish_transactions/{transaction_id}/"
            "journal.json"
        ),
        "journal_status": "failed",
        "journal_sha256": journal_sha256,
        "registered_count": 0,
        "registration_started": False,
        "recommended_action": "retry_or_abort",
        "expected_cleaned_paths": [f"{CANONICAL}/.forge/stage/beauty/v002"],
        "issues": [],
    }


def _abort_manifest(**plan_overrides: Any) -> dict[str, Any]:
    plan = _abort_plan(**plan_overrides)
    return {
        "kind": (
            "pipeline.shot_resource.callable_publish_transaction_abort_result"
        ),
        "schema_version": 1,
        "operation_type": ABORT_OPERATION_TYPE,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "state_owner": "peer_owned",
        "abort_plan": plan,
        "intent_parameters": {
            "params": {
                "canonical": CANONICAL,
                "transaction_id": TRANSACTION_ID,
            },
            "idempotency_key": "transaction-abort-1",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": ABORT_OPERATION_TYPE,
                    "transaction_id": plan["transaction_id"],
                    "journal_sha256": plan["journal_sha256"],
                },
                "payload": {"abort_plan": plan},
            }
        ],
        "originating_capability": ABORT_TOOL,
        "apply_counterpart": {"tool": ABORT_TOOL, "parameter_overrides": {}},
    }


def _status_payload(
    *,
    abort_allowed: bool = True,
    registration_started: bool = False,
    registered_count: int = 0,
    ok: bool = True,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "status": "failed",
        "trust_status": "review_required",
        "read_only": True,
        "state_owner": "read_only",
        "canonical": CANONICAL,
        "transaction_id": TRANSACTION_ID,
        "journal_path": f"{CANONICAL}/.forge/journal.json",
        "abort_allowed": abort_allowed,
        "registration_started": registration_started,
        "registered_count": registered_count,
        "recommended_action": "retry_or_abort",
    }


_SCHEMA = {
    "type": "object",
    "properties": {
        "params": {"type": "object"},
        "mode": {"type": "string"},
        "resolved_plan": {"type": "array"},
        "idempotency_key": {"type": "string"},
        "bridge_asset_ids": {"type": "array"},
        "project_id": {"type": "string"},
        "requested_by": {"type": "string"},
    },
    "required": ["params"],
}


class FakeMCP:
    """Stands in for the Pipeline publish / inspect / abort callables."""

    def __init__(
        self,
        *,
        held: dict[str, Any] | None = None,
        fresh: dict[str, Any] | None = None,
        apply_ok: bool = True,
        apply_drift: bool = False,
        created_asset_ids: list[str] | None = None,
        status_payload: dict[str, Any] | None = None,
        abort_held: dict[str, Any] | None = None,
        abort_fresh: dict[str, Any] | None = None,
        abort_apply_ok: bool = True,
        apply_delay: float = 0.0,
    ) -> None:
        self.held = copy.deepcopy(held or _publish_manifest())
        self.fresh = copy.deepcopy(
            fresh if fresh is not None else self.held
        )
        self.apply_ok = apply_ok
        self.apply_drift = apply_drift
        self.created_asset_ids = (
            created_asset_ids
            if created_asset_ids is not None
            else ["asset-matte-1", "asset-beauty-1"]
        )
        self.status_payload = status_payload or _status_payload()
        self.abort_held = copy.deepcopy(abort_held or _abort_manifest())
        self.abort_fresh = copy.deepcopy(
            abort_fresh if abort_fresh is not None else self.abort_held
        )
        self.abort_apply_ok = abort_apply_ok
        self.apply_delay = apply_delay
        self.calls: list[tuple[str, str]] = []
        self.arguments: list[tuple[str, dict[str, Any]]] = []
        self.apply_count = 0
        self.abort_apply_count = 0

    async def list_tools(self):
        return [
            SimpleNamespace(name=name, inputSchema=_SCHEMA)
            for name in (PUBLISH_TOOL, INSPECT_TOOL, ABORT_TOOL)
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        mode = str(arguments.get("mode") or "read")
        self.calls.append((name, mode))
        self.arguments.append((name, copy.deepcopy(arguments)))
        if name == INSPECT_TOOL:
            return copy.deepcopy(self.status_payload)
        if name == PUBLISH_TOOL:
            return await self._publish(mode, arguments)
        if name == ABORT_TOOL:
            return await self._abort(mode, arguments)
        raise AssertionError(name)

    async def _publish(self, mode: str, arguments: dict[str, Any]):
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
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "apply",
                    "mutation_safe": False,
                    "error": {"code": "publish_transaction.artifact_failed"},
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "state_owner": "federated_transaction",
                "idempotent_replay": False,
                "registered_count": len(self.created_asset_ids),
                "created_asset_ids": list(self.created_asset_ids),
                "transaction_apply": {
                    "status": "committed",
                    "trust_status": "trusted",
                    "registered_count": len(self.created_asset_ids),
                },
            }
        raise AssertionError(mode)

    async def _abort(self, mode: str, arguments: dict[str, Any]):
        if mode == "discover":
            return copy.deepcopy(self.abort_held)
        assert arguments["resolved_plan"] == self.abort_held["resolved_plan"]
        if mode == "verify":
            return copy.deepcopy(self.abort_fresh)
        if mode == "apply":
            self.abort_apply_count += 1
            if not self.abort_apply_ok:
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "plan_drift",
                    "drift": True,
                    "mutation_safe": False,
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "state_owner": "peer_owned",
                "idempotent_replay": False,
                "abort_apply": {
                    "status": "aborted",
                    "trust_status": "trusted",
                    "cleaned_count": 1,
                },
            }
        raise AssertionError(mode)


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
            # Simulate a ratification that did not take: the commit rail must
            # still refuse rather than apply.
            record.status = "proposed"
            record.decided_by = None
        return record


def build_api(
    *,
    mcp: FakeMCP | None = None,
    store: Any = None,
    gateway: Any = None,
    ratify_takes: bool = True,
):
    mcp = mcp or FakeMCP()
    store = store if store is not None else (
        InMemoryEditorialWorkspacePublishWorkflowStore()
    )
    gateway = gateway or CountingAssentGateway(ratify_takes=ratify_takes)
    api = make_editorial_workspace_publish_workflow_api(
        session_factory=None,
        mcp=mcp,
        store=store,
        assent_gateway=gateway,
        clock=lambda: "2026-07-25T00:00:00Z",
    )
    return api, mcp, store, gateway


async def _proposed(api, proposal=None):
    return await api.propose(proposal if proposal is not None else make_proposal())


def _args(receipt):
    return {
        "proposal_id": receipt["proposal_id"],
        "expected_proposal_fingerprint": receipt["proposal_fingerprint"],
    }


async def _applied_workflow(**kwargs):
    api, mcp, store, gateway = build_api(**kwargs)
    proposed = await _proposed(api)
    applied = await api.ratify_apply(**_args(proposed), requested_by="artist-1")
    return api, mcp, store, gateway, proposed, applied


async def _failed_workflow(**kwargs):
    kwargs.setdefault("mcp", FakeMCP(apply_ok=False))
    api, mcp, store, gateway = build_api(**kwargs)
    proposed = await _proposed(api)
    failed = await api.ratify_apply(**_args(proposed), requested_by="artist-1")
    return api, mcp, store, gateway, proposed, failed


# --------------------------------------------------------------------------- #
# §11.1 — unknown/missing proposal fields and fingerprint drift fail before MCP
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_01_unknown_missing_and_drifted_proposals_fail_before_mcp():
    api, mcp, _store, gateway = build_api()

    unknown = make_proposal()
    unknown["surprise"] = "nope"
    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(unknown)
    assert exc.value.code == epw.REASON_PROPOSAL_INVALID

    missing = make_proposal()
    del missing["owner_type"]
    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(missing)
    assert exc.value.code == epw.REASON_PROPOSAL_INVALID

    drifted = make_proposal()
    drifted["fingerprint"] = "d" * 64
    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(drifted)
    assert exc.value.code == epw.REASON_PROPOSAL_INVALID

    unsorted_roles = make_proposal(selected_roles=["matte", "beauty"])
    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(unsorted_roles)
    assert exc.value.code == epw.REASON_PROPOSAL_INVALID

    assert mcp.calls == []  # refused before any MCP contact
    assert gateway.proposed == []


# --------------------------------------------------------------------------- #
# §11.2 — callable identity / role / output / lineage / idempotency drift
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda i: i.update(tool="forge_apply_publish"), id="tool"
        ),
        pytest.param(
            lambda i: i.update(operation_type="pipeline.other"),
            id="operation_type",
        ),
        pytest.param(
            lambda i: i.update(project_id="project-2"), id="project"
        ),
        pytest.param(
            lambda i: i.update(bridge_asset_ids=["version-9"]),
            id="source_lineage",
        ),
        pytest.param(
            lambda i: i.update(idempotency_key="  "), id="idempotency"
        ),
        pytest.param(
            lambda i: i["params"].update(roles=["beauty"]), id="params_roles"
        ),
        pytest.param(
            lambda i: i["params"]["outputs"].pop(), id="output_count"
        ),
        pytest.param(
            lambda i: i["params"]["outputs"][0].update(role="grade"),
            id="output_role",
        ),
        pytest.param(
            lambda i: i["params"]["outputs"][0].update(lineage_asset_ids=[]),
            id="output_lineage",
        ),
        pytest.param(
            lambda i: i.update(extra_field=1), id="unknown_callable_field"
        ),
    ],
)
@pytest.mark.asyncio
async def test_02_callable_intent_drift_fails_closed(mutate):
    api, mcp, _store, _gateway = build_api()
    intent = make_callable_intent()
    mutate(intent)
    # The proposal is otherwise internally consistent — its own fingerprints
    # are recomputed — so only the callable verification can catch this.
    proposal = make_proposal(callable_intent=intent)

    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(proposal)

    assert exc.value.code == epw.REASON_PROPOSAL_INVALID
    assert mcp.calls == []


@pytest.mark.asyncio
async def test_02b_callable_intent_fingerprint_must_match():
    api, mcp, _store, _gateway = build_api()
    proposal = make_proposal()
    proposal["callable_intent_fingerprint"] = "e" * 64
    body = {
        key: value
        for key, value in proposal.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    proposal["fingerprint"] = _fingerprint(body)

    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(proposal)

    assert exc.value.code == epw.REASON_PROPOSAL_INVALID
    assert mcp.calls == []


@pytest.mark.asyncio
async def test_02c_discovered_manifest_drift_fails_closed():
    """The host may answer with a manifest that is not this proposal's."""
    drifted = _publish_manifest()
    drifted["transaction_plan"]["roles"] = ["beauty"]
    api, mcp, _store, gateway = build_api(mcp=FakeMCP(held=drifted))

    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(make_proposal())

    assert exc.value.code == epw.REASON_MANIFEST_INVALID
    assert [mode for _name, mode in mcp.calls] == ["discover"]
    assert gateway.proposed == []  # no assent for an unverified manifest


# --------------------------------------------------------------------------- #
# §11.3 — exact duplicate propose returns the original durable proposal
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_03_duplicate_propose_returns_the_original_receipt():
    api, mcp, _store, gateway = build_api()
    proposal = make_proposal()

    first = await api.propose(proposal)
    second = await api.propose(proposal)

    assert first == second
    assert len(gateway.proposed) == 1
    assert [mode for _name, mode in mcp.calls] == ["discover"]

    # …and it stays the original even after the workflow advances (§6).
    await api.ratify_apply(**_args(first), requested_by="artist-1")
    third = await api.propose(proposal)
    assert third == first
    assert third["status"] == "proposed"
    assert third["published_asset_ids"] == []


@pytest.mark.asyncio
async def test_03b_same_publish_authority_on_another_proposal_fails_closed():
    api, _mcp, _store, _gateway = build_api()
    await api.propose(make_proposal())

    rebound = make_proposal(publish_preview_id="publish-preview-2")
    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(rebound)
    assert exc.value.code == epw.REASON_PROPOSAL_INVALID


# --------------------------------------------------------------------------- #
# §11.4 — propose discovers only, and persists ONE proposed AssentRecord
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_04_propose_discovers_only_and_persists_one_assent():
    api, mcp, store, gateway = build_api()

    receipt = await api.propose(make_proposal())

    assert [(name, mode) for name, mode in mcp.calls] == [
        (PUBLISH_TOOL, "discover")
    ]
    assert mcp.apply_count == 0
    assert len(gateway.proposed) == 1
    assert gateway.ratified == []

    assert receipt["kind"] == RECEIPT_KIND
    assert receipt["action"] == "propose"
    assert receipt["status"] == "proposed"
    assert receipt["trust_status"] == "trusted"
    assert receipt["assent_status"] == "proposed"
    assert receipt["transaction_status"] == "not_started"
    assert receipt["recovery_status"] == "not_required"
    assert receipt["dispatch_authorized"] is False
    assert receipt["applied"] is False
    assert receipt["replayed"] is False
    assert receipt["published_asset_ids"] == []
    assert receipt["manifest_fingerprint"]
    assert receipt["transaction_id"] == TRANSACTION_ID
    assert receipt["selected_roles"] == sorted(ROLES)

    row = await store.get_by_proposal_id(receipt["proposal_id"])
    assert row["forward_assent_status"] == "proposed"
    assert row["forward_commit_fingerprint"] is None
    assert row["recovery_held_manifest"] is None


@pytest.mark.asyncio
async def test_04b_bridge_composes_publish_into_commit():
    """§5: Bridge, not Pipeline, constructs publish -> commit."""
    intent = make_callable_intent()
    sequence = epw.publish_commit_operator_sequence(intent)

    assert [step["operator_id"] for step in sequence] == [PUBLISH_TOOL, "commit"]
    assert sequence[0]["arguments"] == {
        "params": intent["params"],
        "bridge_asset_ids": intent["bridge_asset_ids"],
        "idempotency_key": intent["idempotency_key"],
        "project_id": intent["project_id"],
        "requested_by": intent["requested_by"],
        "mode": "discover",
    }
    assert sequence[1]["inputs"][0]["metadata"] == {"role": "held"}


# --------------------------------------------------------------------------- #
# §11.5 — unratified forward commit refuses without apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_05_unratified_commit_refuses_without_apply():
    api, mcp, _store, gateway = build_api(ratify_takes=False)
    proposed = await _proposed(api)

    receipt = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == epw.REASON_ASSENT_INVALID
    assert receipt["applied"] is False
    assert receipt["dispatch_authorized"] is False
    assert receipt["transaction_status"] == "not_started"
    assert mcp.apply_count == 0
    assert gateway.ratified  # ratification was attempted, apply was not


# --------------------------------------------------------------------------- #
# §11.6 — ratified apply performs discover, verify, apply exactly once
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_06_ratified_apply_discovers_verifies_applies_once():
    _api, mcp, _store, gateway, _proposal, applied = await _applied_workflow()

    assert [mode for name, mode in mcp.calls if name == PUBLISH_TOOL] == [
        "discover",
        "verify",
        "apply",
    ]
    assert mcp.apply_count == 1
    assert len(gateway.ratified) == 1
    assert applied["status"] == "applied"
    assert applied["assent_status"] == "applied"


# --------------------------------------------------------------------------- #
# §11.7 — fresh-plan drift refuses before apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_07_fresh_plan_drift_refuses_before_apply():
    mcp = FakeMCP(fresh=_publish_manifest(version="v003"))
    api, mcp, _store, _gateway = build_api(mcp=mcp)
    proposed = await _proposed(api)

    receipt = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == epw.REASON_MANIFEST_DRIFT
    assert receipt["applied"] is False
    assert mcp.apply_count == 0
    assert [mode for name, mode in mcp.calls if name == PUBLISH_TOOL] == [
        "discover",
        "verify",
    ]


# --------------------------------------------------------------------------- #
# §11.8 — successful apply retains transaction ID and sorted created asset IDs
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_08_applied_receipt_retains_transaction_and_sorted_assets():
    _api, _mcp, store, _gateway, proposed, applied = await _applied_workflow()

    assert applied["status"] == "applied"
    assert applied["applied"] is True
    assert applied["replayed"] is False
    assert applied["dispatch_authorized"] is True
    assert applied["transaction_status"] == "committed"
    assert applied["transaction_id"] == TRANSACTION_ID
    assert applied["published_asset_ids"] == [
        "asset-beauty-1",
        "asset-matte-1",
    ]
    assert applied["commit_fingerprint"]
    assert applied["recovery_status"] == "not_required"
    # every forward proposal authority survives the apply
    for key in (
        "proposal_fingerprint",
        "publish_preview_id",
        "publish_preview_fingerprint",
        "transaction_batch_fingerprint",
        "callable_intent_fingerprint",
        "manifest_fingerprint",
        "assent_record_id",
    ):
        assert applied[key] == proposed[key]

    row = await store.get_by_proposal_id(applied["proposal_id"])
    assert row["published_asset_ids"] == ["asset-beauty-1", "asset-matte-1"]


@pytest.mark.asyncio
async def test_08b_apply_without_created_assets_is_not_applied():
    mcp = FakeMCP(created_asset_ids=[])
    api, mcp, _store, _gateway = build_api(mcp=mcp)
    proposed = await _proposed(api)

    receipt = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == epw.REASON_COMMIT_FAILED
    assert receipt["published_asset_ids"] == []


# --------------------------------------------------------------------------- #
# §11.9 — status performs no mutation
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_09_status_is_read_only():
    api, mcp, store, gateway, proposed, applied = await _applied_workflow()
    before = await store.get_by_proposal_id(proposed["proposal_id"])
    calls_before = list(mcp.calls)

    receipt = await api.status(**_args(proposed))

    assert receipt["action"] == "status"
    assert receipt["status"] == "applied"
    assert receipt["published_asset_ids"] == applied["published_asset_ids"]
    assert receipt["replayed"] is False
    assert mcp.calls == calls_before
    assert mcp.apply_count == 1
    assert await store.get_by_proposal_id(proposed["proposal_id"]) == before
    assert len(gateway.proposed) == 1


@pytest.mark.asyncio
async def test_09b_status_on_a_proposed_workflow_reports_proposed():
    """Handoff §8 lists no other honest status for an un-ratified workflow.

    NB: Pipeline's shipped receipt dataclass additionally binds status
    "proposed" to action "propose"; see the module note and the #242 PR body.
    """
    api, _mcp, _store, _gateway = build_api()
    proposed = await _proposed(api)

    receipt = await api.status(**_args(proposed))

    assert receipt["status"] == "proposed"
    assert receipt["dispatch_authorized"] is False
    assert receipt["transaction_status"] == "not_started"


@pytest.mark.asyncio
async def test_09c_wrong_expected_fingerprint_refuses_every_transition():
    api, mcp, _store, _gateway = build_api()
    proposed = await _proposed(api)
    wrong = {
        "proposal_id": proposed["proposal_id"],
        "expected_proposal_fingerprint": "f" * 64,
    }

    for action, kwargs in (
        ("ratify_apply", {"requested_by": "artist-1"}),
        ("status", {}),
        ("replay", {"requested_by": "artist-1"}),
        ("propose_recovery", {"requested_by": "artist-1"}),
        ("ratify_recovery", {"requested_by": "artist-1"}),
    ):
        receipt = await getattr(api, action)(**wrong, **kwargs)
        assert receipt["action"] == action
        assert receipt["status"] == "failed"
        assert receipt["reason_code"] == epw.REASON_PROPOSAL_CHANGED
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_09d_unknown_proposal_raises_typed_error():
    api, _mcp, _store, _gateway = build_api()
    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.status(
            proposal_id="epw_deadbeefdeadbeef",
            expected_proposal_fingerprint="0" * 64,
        )
    assert exc.value.code == epw.REASON_PROPOSAL_NOT_FOUND


# --------------------------------------------------------------------------- #
# §11.10 — replay performs no new discovery, assent, commit, or apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_10_replay_observes_without_dispatching():
    api, mcp, _store, gateway, proposed, applied = await _applied_workflow()
    calls_before = list(mcp.calls)

    replayed = await api.replay(**_args(proposed), requested_by="artist-1")

    assert replayed["action"] == "replay"
    assert replayed["status"] == "applied"
    assert replayed["replayed"] is True
    assert replayed["applied"] is True
    assert replayed["dispatch_authorized"] is True
    assert replayed["commit_fingerprint"] == applied["commit_fingerprint"]
    assert replayed["published_asset_ids"] == applied["published_asset_ids"]
    assert mcp.calls == calls_before
    assert mcp.apply_count == 1
    assert len(gateway.proposed) == 1
    assert len(gateway.ratified) == 1


@pytest.mark.asyncio
async def test_10b_replay_before_apply_is_unavailable():
    api, mcp, _store, _gateway = build_api()
    proposed = await _proposed(api)

    receipt = await api.replay(**_args(proposed), requested_by="artist-1")

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == epw.REASON_REPLAY_UNAVAILABLE
    assert receipt["replayed"] is False
    assert mcp.apply_count == 0


# --------------------------------------------------------------------------- #
# §11.11 — failed apply reports the real transaction and recovery disposition
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_11_failed_apply_reports_transaction_and_recovery_disposition():
    _api, mcp, _store, _gateway, _proposed, failed = await _failed_workflow()

    assert failed["status"] == "failed"
    assert failed["reason_code"] == epw.REASON_COMMIT_FAILED
    assert failed["applied"] is False
    assert failed["dispatch_authorized"] is False
    assert failed["published_asset_ids"] == []
    assert failed["commit_fingerprint"] is None
    # the apply WAS dispatched, so the journal state is the status tool's to
    # answer — Bridge reports review_required rather than guessing.
    assert failed["transaction_status"] == "failed"
    assert failed["recovery_status"] == "review_required"
    assert mcp.apply_count == 1


@pytest.mark.asyncio
async def test_11b_pre_dispatch_refusal_leaves_the_transaction_not_started():
    api, mcp, _store, _gateway = build_api(ratify_takes=False)
    proposed = await _proposed(api)

    failed = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert failed["transaction_status"] == "not_started"
    assert failed["recovery_status"] == "not_required"
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_11c_second_ratify_apply_after_success_refuses():
    api, mcp, _store, _gateway, proposed, _applied = await _applied_workflow()

    second = await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    assert second["status"] == "failed"
    assert second["reason_code"] == epw.REASON_ASSENT_INVALID
    assert mcp.apply_count == 1


# --------------------------------------------------------------------------- #
# §11.12 — recovery proposal inspects + discovers abort, but never aborts
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_12_recovery_proposal_inspects_and_discovers_only():
    api, mcp, store, gateway, proposed, failed = await _failed_workflow()
    calls_before = len(mcp.calls)

    recovery = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert [call for call in mcp.calls[calls_before:]] == [
        (INSPECT_TOOL, "read"),
        (ABORT_TOOL, "discover"),
    ]
    assert mcp.abort_apply_count == 0
    assert recovery["action"] == "propose_recovery"
    assert recovery["status"] == "recovery_proposed"
    assert recovery["recovery_status"] == "available"
    assert recovery["recovery_assent_status"] == "proposed"
    assert recovery["recovery_manifest_fingerprint"]
    assert recovery["recovery_assent_record_id"]
    assert recovery["recovery_commit_fingerprint"] is None
    assert recovery["dispatch_authorized"] is False
    # a SECOND proposed AssentRecord, distinct from the forward one
    assert len(gateway.proposed) == 2
    assert recovery["assent_record_id"] != recovery["recovery_assent_record_id"]

    # forward authorities are never overwritten by the recovery rail (§9)
    for key in (
        "proposal_fingerprint",
        "callable_intent_fingerprint",
        "manifest_fingerprint",
        "assent_record_id",
        "transaction_id",
    ):
        assert recovery[key] == failed[key]
    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["forward_manifest_fingerprint"] == failed["manifest_fingerprint"]
    assert row["forward_commit_fingerprint"] is None


@pytest.mark.asyncio
async def test_12b_recovery_derives_its_own_private_parameters():
    """The Shell supplies none of the recovery parameters (§7).

    Bridge derives ``canonical`` (an absolute path) and ``transaction_id`` from
    the RETAINED forward manifest — nothing in the transition signature could
    have supplied them.
    """
    api, mcp, _store, _gateway, proposed, _failed = await _failed_workflow()

    await api.propose_recovery(**_args(proposed), requested_by="artist-1")

    inspect_args = [
        arguments for name, arguments in mcp.arguments if name == INSPECT_TOOL
    ]
    assert len(inspect_args) == 1
    assert inspect_args[0]["params"] == {
        "canonical": CANONICAL,
        "transaction_id": TRANSACTION_ID,
    }
    abort_args = [
        arguments
        for name, arguments in mcp.arguments
        if name == ABORT_TOOL and arguments.get("mode") == "discover"
    ]
    assert abort_args[0]["params"] == {
        "canonical": CANONICAL,
        "transaction_id": TRANSACTION_ID,
    }
    # The transition signature carries no path, plan, or token.
    assert set(_args(proposed)) == {
        "proposal_id",
        "expected_proposal_fingerprint",
    }


@pytest.mark.asyncio
async def test_12c_recovery_is_unavailable_over_a_committed_transaction():
    api, mcp, _store, _gateway, proposed, _applied = await _applied_workflow()

    receipt = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == epw.REASON_RECOVERY_UNAVAILABLE
    assert mcp.abort_apply_count == 0
    assert (INSPECT_TOOL, "read") not in mcp.calls


@pytest.mark.asyncio
async def test_12d_duplicate_recovery_proposal_is_idempotent():
    api, mcp, _store, gateway, proposed, _failed = await _failed_workflow()
    first = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )
    calls = len(mcp.calls)

    second = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert second == first
    assert len(mcp.calls) == calls  # no second inspect/discover
    assert len(gateway.proposed) == 2


# --------------------------------------------------------------------------- #
# §11.13 — recovery ratification verifies and aborts exactly once
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_13_recovery_ratification_verifies_and_aborts_once():
    api, mcp, store, gateway, proposed, failed = await _failed_workflow()
    recovery = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    aborted = await api.ratify_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert [mode for name, mode in mcp.calls if name == ABORT_TOOL] == [
        "discover",
        "verify",
        "apply",
    ]
    assert mcp.abort_apply_count == 1
    assert aborted["action"] == "ratify_recovery"
    assert aborted["status"] == "aborted"
    assert aborted["transaction_status"] == "aborted"
    assert aborted["recovery_status"] == "aborted"
    assert aborted["recovery_commit_fingerprint"]
    assert aborted["dispatch_authorized"] is True
    assert aborted["applied"] is False
    assert len(gateway.ratified) == 2
    # separate recovery manifest / assent / commit fingerprints (§7)
    assert (
        aborted["recovery_manifest_fingerprint"]
        == recovery["recovery_manifest_fingerprint"]
    )
    assert aborted["recovery_manifest_fingerprint"] != (
        aborted["manifest_fingerprint"]
    )
    assert aborted["recovery_commit_fingerprint"] != (
        aborted["commit_fingerprint"]
    )
    assert aborted["manifest_fingerprint"] == failed["manifest_fingerprint"]

    # idempotent: a second ratification never dispatches a second abort
    again = await api.ratify_recovery(**_args(proposed), requested_by="a")
    assert again["status"] == "aborted"
    assert mcp.abort_apply_count == 1

    row = await store.get_by_proposal_id(proposed["proposal_id"])
    assert row["forward_manifest_fingerprint"] != row[
        "recovery_manifest_fingerprint"
    ]


@pytest.mark.asyncio
async def test_13b_ratify_recovery_without_a_proposal_is_unavailable():
    api, mcp, _store, _gateway, proposed, _failed = await _failed_workflow()

    receipt = await api.ratify_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == epw.REASON_RECOVERY_UNAVAILABLE
    assert mcp.abort_apply_count == 0


@pytest.mark.asyncio
async def test_13c_recovery_apply_drift_reports_recovery_drift():
    api, mcp, _store, _gateway, proposed, _failed = await _failed_workflow()
    await api.propose_recovery(**_args(proposed), requested_by="artist-1")
    mcp.abort_apply_ok = False

    receipt = await api.ratify_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == epw.REASON_RECOVERY_DRIFT
    assert receipt["recovery_status"] == "review_required"
    assert receipt["recovery_commit_fingerprint"] is None


# --------------------------------------------------------------------------- #
# §11.14 — uncertain registration or recovery drift refuses before abort
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_14_uncertain_registration_refuses_before_abort_discovery():
    mcp = FakeMCP(
        apply_ok=False,
        status_payload=_status_payload(registration_started=True),
    )
    api, mcp, _store, _gateway = build_api(mcp=mcp)
    proposed = await _proposed(api)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == epw.REASON_RECOVERY_UNAVAILABLE
    assert receipt["recovery_status"] == "review_required"
    assert receipt["recovery_manifest_fingerprint"] is None
    assert mcp.abort_apply_count == 0
    assert [name for name, _mode in mcp.calls if name == ABORT_TOOL] == []


@pytest.mark.asyncio
async def test_14b_abort_not_allowed_refuses_before_abort_discovery():
    mcp = FakeMCP(
        apply_ok=False, status_payload=_status_payload(abort_allowed=False)
    )
    api, mcp, _store, _gateway = build_api(mcp=mcp)
    proposed = await _proposed(api)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "unavailable"
    assert receipt["recovery_status"] == "review_required"
    assert [name for name, _mode in mcp.calls if name == ABORT_TOOL] == []


@pytest.mark.asyncio
async def test_14c_status_tool_unavailable_refuses_before_abort():
    mcp = FakeMCP(
        apply_ok=False,
        status_payload={
            "ok": False,
            "error": {"code": "publish_transaction_status_unavailable"},
        },
    )
    api, mcp, _store, _gateway = build_api(mcp=mcp)
    proposed = await _proposed(api)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == epw.REASON_STATUS_UNAVAILABLE
    assert receipt["recovery_status"] == "unavailable"
    assert mcp.abort_apply_count == 0


@pytest.mark.asyncio
async def test_14d_abort_discovery_drift_refuses_before_abort():
    mcp = FakeMCP(
        apply_ok=False,
        abort_held=_abort_manifest(transaction_id="txn-someone-else"),
    )
    api, mcp, _store, gateway = build_api(mcp=mcp)
    proposed = await _proposed(api)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == epw.REASON_RECOVERY_DRIFT
    assert receipt["recovery_status"] == "review_required"
    assert receipt["recovery_assent_record_id"] is None
    assert mcp.abort_apply_count == 0
    assert len(gateway.proposed) == 1  # no recovery assent was persisted


@pytest.mark.asyncio
async def test_14e_abort_plan_not_ready_refuses_before_abort():
    mcp = FakeMCP(apply_ok=False, abort_held=_abort_manifest(ready=False))
    api, mcp, _store, _gateway = build_api(mcp=mcp)
    proposed = await _proposed(api)
    await api.ratify_apply(**_args(proposed), requested_by="artist-1")

    receipt = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == epw.REASON_RECOVERY_DRIFT
    assert mcp.abort_apply_count == 0


# --------------------------------------------------------------------------- #
# §11.15 — restart preserves proposal, forward receipt, and recovery authority
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_15_restart_preserves_every_durable_authority():
    api, mcp, store, gateway, proposed, failed = await _failed_workflow()
    recovery = await api.propose_recovery(
        **_args(proposed), requested_by="artist-1"
    )

    # A brand-new API instance over the SAME durable store (Bridge restart).
    restarted = make_editorial_workspace_publish_workflow_api(
        session_factory=None,
        mcp=mcp,
        store=store,
        assent_gateway=gateway,
        clock=lambda: "2026-07-25T01:00:00Z",
    )

    duplicate = await restarted.propose(make_proposal())
    assert duplicate == proposed

    status = await restarted.status(**_args(proposed))
    assert status["status"] == "failed"
    assert status["manifest_fingerprint"] == failed["manifest_fingerprint"]
    assert status["recovery_status"] == "available"
    assert status["recovery_manifest_fingerprint"] == (
        recovery["recovery_manifest_fingerprint"]
    )
    assert status["recovery_assent_record_id"] == (
        recovery["recovery_assent_record_id"]
    )

    aborted = await restarted.ratify_recovery(
        **_args(proposed), requested_by="artist-1"
    )
    assert aborted["status"] == "aborted"
    assert mcp.abort_apply_count == 1


# --------------------------------------------------------------------------- #
# §11.16 — concurrent transition attempts do not double-apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_16_concurrent_ratify_apply_dispatches_once():
    api, mcp, _store, _gateway = build_api(mcp=FakeMCP(apply_delay=0.02))
    proposed = await _proposed(api)
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
async def test_16b_concurrent_recovery_ratification_aborts_once():
    api, mcp, _store, _gateway, proposed, _failed = await _failed_workflow()
    await api.propose_recovery(**_args(proposed), requested_by="artist-1")
    kwargs = dict(**_args(proposed), requested_by="artist-1")

    results = await asyncio.gather(
        api.ratify_recovery(**kwargs), api.ratify_recovery(**kwargs)
    )

    assert [receipt["status"] for receipt in results] == ["aborted", "aborted"]
    assert mcp.abort_apply_count == 1


@pytest.mark.asyncio
async def test_16c_concurrent_recovery_proposals_discover_once():
    api, mcp, _store, gateway, proposed, _failed = await _failed_workflow()
    kwargs = dict(**_args(proposed), requested_by="artist-1")

    results = await asyncio.gather(
        api.propose_recovery(**kwargs), api.propose_recovery(**kwargs)
    )

    assert results[0] == results[1]
    assert len(gateway.proposed) == 2  # forward + exactly one recovery
    assert (
        len([name for name, _mode in mcp.calls if name == ABORT_TOOL]) == 1
    )


# --------------------------------------------------------------------------- #
# §11.17 / §11.18 — closed field set, valid fingerprint, no private payloads
# --------------------------------------------------------------------------- #
_RECEIPT_FIELDS = {
    "kind",
    "schema_version",
    "action",
    "status",
    "trust_status",
    "workflow_id",
    "proposal_id",
    "proposal_fingerprint",
    "publish_preview_id",
    "publish_preview_fingerprint",
    "transaction_batch_fingerprint",
    "callable_intent_fingerprint",
    "transaction_id",
    "selected_roles",
    "published_asset_ids",
    "manifest_fingerprint",
    "assent_record_id",
    "assent_status",
    "commit_fingerprint",
    "transaction_status",
    "recovery_status",
    "recovery_manifest_fingerprint",
    "recovery_assent_record_id",
    "recovery_assent_status",
    "recovery_commit_fingerprint",
    "dispatch_authorized",
    "applied",
    "replayed",
    "reason_code",
    "fingerprint",
}
_FORBIDDEN_RECEIPT_SUBSTRINGS = (
    "transaction_plan",
    "abort_plan",
    "resolved_plan",
    "callable_intent\":",
    "intent_parameters",
    "apply_counterpart",
    "journal",
    "source_path",
    "held_manifest",
    "expected_cleaned_paths",
)


async def _every_receipt() -> list[dict[str, Any]]:
    """One receipt from every action, across the success and recovery rails."""
    receipts: list[dict[str, Any]] = []

    ok_api, _mcp, _store, _gateway, proposed, applied = (
        await _applied_workflow()
    )
    receipts.extend([proposed, applied])
    receipts.append(await ok_api.status(**_args(proposed)))
    receipts.append(
        await ok_api.replay(**_args(proposed), requested_by="artist-1")
    )
    receipts.append(
        await ok_api.propose_recovery(
            **_args(proposed), requested_by="artist-1"
        )
    )
    receipts.append(
        await ok_api.replay(
            proposal_id=proposed["proposal_id"],
            expected_proposal_fingerprint="f" * 64,
            requested_by="artist-1",
        )
    )

    bad_api, _mcp2, _store2, _gw2, bad_proposed, failed = (
        await _failed_workflow()
    )
    receipts.append(failed)
    recovery = await bad_api.propose_recovery(
        **_args(bad_proposed), requested_by="artist-1"
    )
    receipts.append(recovery)
    receipts.append(
        await bad_api.ratify_recovery(
            **_args(bad_proposed), requested_by="artist-1"
        )
    )
    receipts.append(await bad_api.status(**_args(bad_proposed)))
    return receipts


@pytest.mark.asyncio
async def test_17_every_receipt_is_closed_and_self_verifying():
    receipts = await _every_receipt()
    assert len(receipts) == 10

    for receipt in receipts:
        assert set(receipt) == _RECEIPT_FIELDS
        assert receipt["kind"] == RECEIPT_KIND
        assert receipt["schema_version"] == 1
        assert receipt["action"] in {
            "propose",
            "ratify_apply",
            "status",
            "replay",
            "propose_recovery",
            "ratify_recovery",
        }
        assert receipt["status"] in {
            "proposed",
            "applied",
            "failed",
            "unavailable",
            "recovery_proposed",
            "aborted",
        }
        assert receipt["recovery_status"] in {
            "not_required",
            "available",
            "review_required",
            "unavailable",
            "aborted",
        }
        # fingerprint excludes kind, schema_version and itself (§8)
        body = {
            key: value
            for key, value in receipt.items()
            if key not in {"kind", "schema_version", "fingerprint"}
        }
        assert receipt["fingerprint"] == _fingerprint(body)
        for field in ("dispatch_authorized", "applied", "replayed"):
            assert isinstance(receipt[field], bool)
        for field in ("selected_roles", "published_asset_ids"):
            values = receipt[field]
            assert isinstance(values, list)
            assert sorted(set(values)) == values
        assert receipt["selected_roles"]


@pytest.mark.asyncio
async def test_18_serialized_receipts_carry_no_private_paths_or_payloads():
    receipts = await _every_receipt()

    for receipt in receipts:
        serialized = json.dumps(receipt, sort_keys=True)
        assert "/" not in serialized, receipt["action"]
        for needle in _FORBIDDEN_RECEIPT_SUBSTRINGS:
            assert needle not in serialized, (receipt["action"], needle)
        for value in receipt.values():
            assert not isinstance(value, dict)
            if isinstance(value, list):
                assert all(isinstance(item, str) for item in value)


@pytest.mark.asyncio
async def test_18b_typed_errors_carry_no_private_paths():
    api, _mcp, _store, _gateway = build_api()
    intent = make_callable_intent()
    intent["params"]["outputs"][0]["lineage_asset_ids"] = []
    with pytest.raises(EditorialWorkspacePublishWorkflowError) as exc:
        await api.propose(make_proposal(callable_intent=intent))

    assert "/" not in str(exc.value)
    assert "/" not in exc.value.message
    assert exc.value.code == epw.REASON_PROPOSAL_INVALID
