"""Acceptance matrix for #244 / Pipeline Phase 156 — the workspace main
promotion workflow API. Every numbered test maps to one item of handoff §12.

Like the #242 matrix, these do NOT fake the commit rail: the API is built with
the real ``MCPToolBoundary``, the real ``OperationDispatchBoundary``, and the
real verify-before-apply ``CommitBoundary``, driven by a fake MCP and a fake
operation runner shaped like the released Pipeline callables. Only Postgres is
substituted (in-memory workflow store + in-memory AssentRecord gateway), so
discover/verify/apply ordering, ONE-assent-over-THREE-commits, plan drift, the
partial-failure dispositions, and resumable replay are proven end to end.

The proposal fixture mirrors Pipeline's own adapter fixture field-for-field
(``forge_core/bridge/tests/test_editorial_workspace_promotion_workflow_adapter.py``),
and ``test_pipeline_dataclass_proposal_is_accepted_unchanged`` feeds a proposal
built by Pipeline's released frozen dataclass straight into ``propose``.
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

from forge_bridge.orchestration.editorial_workspace_promotion_workflow import (
    MAIN_PLAN_OPERATION,
    MAIN_REGISTER_TOOL,
    PROMOTE_TOOL,
    PROPOSAL_KIND,
    RECEIPT_KIND,
    RESOURCE_PLAN_OPERATION,
    RESOURCE_REGISTER_TOOL,
    VALIDATE_OPERATION,
    EditorialWorkspacePromotionWorkflowError,
    InMemoryAssentGateway,
    InMemoryEditorialWorkspacePromotionWorkflowStore,
    make_editorial_workspace_promotion_workflow_api,
    promotion_operator_sequence,
)

PROJECT_ID = "project-1"
ACTOR = "supervisor-1"
SOURCE_VERSION_ID = "source-version-1"
SOURCE_MAIN_VERSION_ID = "main-version-1"
TARGET_MAIN_NUMBER = 2
ROLES = ("beauty", "matte")
PUBLISHED_IDS = ("published-1", "published-2")
PROMOTED_IDS = ("promoted-1", "promoted-2")
MAIN_VERSION_ID = "main-version-2"
MAIN_MEDIA_ID = "main-media-2"
PROMOTION_CALLABLE_OPERATION_TYPE = (
    "pipeline.shot_resource.stream_promotion.callable"
)
RESOURCE_REGISTER_OPERATION_TYPE = (
    "pipeline.shot_resource.stream_promotion.registration.callable"
)
MAIN_REGISTER_OPERATION_TYPE = (
    "pipeline.editorial_workspace.main_promotion.registration.callable"
)

_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "editorial_workspace_promotion_workflow_receipt.json"
)


def _fingerprint(value: Any) -> str:
    """Independent canonical fingerprint — the consumer's own arithmetic."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# --------------------------------------------------------------------------- #
# Proposal fixtures (handoff §3, mirroring Pipeline's adapter fixture)
# --------------------------------------------------------------------------- #
def make_callable_intent(**overrides: Any) -> dict[str, Any]:
    intent = {
        "tool": PROMOTE_TOOL,
        "operation_type": PROMOTION_CALLABLE_OPERATION_TYPE,
        # A private absolute path: must never reach a receipt.
        "params": {"canonical": "/private/project", "shot": "sh010"},
        "bridge_asset_ids": list(PUBLISHED_IDS),
        "idempotency_key": "promotion-callable-1",
        "project_id": PROJECT_ID,
        "requested_by": ACTOR,
    }
    intent.update(overrides)
    return intent


def make_main_plan(**overrides: Any) -> dict[str, Any]:
    plan = {
        "kind": "pipeline.editorial_workspace.main_promotion_plan",
        "schema_version": 1,
        # Private absolute paths: must never reach a receipt.
        "source_location": "/private/workfile.batch",
        "source_version_id": SOURCE_VERSION_ID,
        "source_main_version_id": SOURCE_MAIN_VERSION_ID,
        "target_stream": "main",
        "target_version_number": TARGET_MAIN_NUMBER,
        "selected_roles": list(ROLES),
        "published_resource_asset_ids": list(PUBLISHED_IDS),
        "promoted_resource_asset_ids": [],
    }
    plan.update(overrides)
    return plan


def make_proposal(**overrides: Any) -> dict[str, Any]:
    intent = overrides.pop("promotion_callable_intent", None) or (
        make_callable_intent()
    )
    promotion_plan = overrides.pop("promotion_plan", None) or {
        "kind": "pipeline.shot_resource.stream_promotion_plan",
        "actions": [{"source_path": "/private/published.exr"}],
    }
    main_plan = overrides.pop("workspace_main_promotion_plan", None) or (
        make_main_plan()
    )
    proposal = {
        "kind": PROPOSAL_KIND,
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "requested_by": ACTOR,
        "promotion_preview_id": "promotion-preview-1",
        "promotion_preview_fingerprint": "a" * 64,
        "promotion_authority_fingerprint": "b" * 64,
        "publish_preview_id": "publish-preview-1",
        "publish_preview_fingerprint": "c" * 64,
        "source_version_id": SOURCE_VERSION_ID,
        "source_main_version_id": SOURCE_MAIN_VERSION_ID,
        "target_main_version_number": TARGET_MAIN_NUMBER,
        "selected_roles": sorted(ROLES),
        "published_resource_asset_ids": sorted(PUBLISHED_IDS),
        "promotion_plan_fingerprint": _fingerprint(promotion_plan),
        "promotion_callable_intent_fingerprint": _fingerprint(intent),
        "workspace_main_promotion_plan_fingerprint": _fingerprint(main_plan),
        "promotion_plan": promotion_plan,
        "promotion_callable_intent": intent,
        "workspace_main_promotion_plan": main_plan,
    }
    proposal.update(overrides)
    body = {
        key: value
        for key, value in proposal.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    proposal["fingerprint"] = _fingerprint(body)
    return proposal


# --------------------------------------------------------------------------- #
# Pipeline-shaped manifests and results
# --------------------------------------------------------------------------- #
def _promotion_result(*, target_version: str = "v002") -> dict[str, Any]:
    return {
        "kind": "pipeline.shot_resource.stream_promotion_result",
        "schema_version": 1,
        "status": "passed",
        "trust_status": "trusted",
        "canonical": "/private/project",
        "shot": "sh010",
        "target_stream": "main",
        "target_version": target_version,
        "action_results": [
            {
                "kind": "pipeline.shot_resource.stream_promotion_proof",
                "status": "passed",
                "trust_status": "trusted",
                "role": role,
                "target_stream": "main",
                "target_version": target_version,
                "target_path": f"/private/sh010/{role}/{target_version}",
            }
            for role in ROLES
        ],
    }


def _copy_manifest(*, target_version: str = "v002") -> dict[str, Any]:
    intent = make_callable_intent()
    plan = {
        "kind": "pipeline.shot_resource.stream_promotion_plan",
        "schema_version": 1,
        "status": "ready",
        "ready_for_promotion": True,
        "mutation_safe": True,
        "shot": "sh010",
        "target_version": target_version,
        "actions": [{"role": role} for role in ROLES],
    }
    return {
        "kind": "pipeline.shot_resource.callable_stream_promotion_result",
        "schema_version": 1,
        "operation_type": PROMOTION_CALLABLE_OPERATION_TYPE,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "state_owner": "peer_owned",
        "intent_parameters": {
            "params": dict(intent["params"]),
            "idempotency_key": intent["idempotency_key"],
            "bridge_asset_ids": list(intent["bridge_asset_ids"]),
            "project_id": intent["project_id"],
            "requested_by": intent["requested_by"],
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": PROMOTION_CALLABLE_OPERATION_TYPE,
                    "shot": "sh010",
                    "target_version": target_version,
                },
                "payload": {"promotion_plan": plan},
            }
        ],
        "originating_capability": PROMOTE_TOOL,
        "apply_counterpart": {"tool": PROMOTE_TOOL, "parameter_overrides": {}},
    }


def _validation() -> dict[str, Any]:
    return {
        "kind": "pipeline.shot_resource.stream_promotion_validation_result",
        "schema_version": 1,
        "status": "passed",
        "trust_status": "trusted",
        "mutation_safe": True,
        "ready_for_registration": True,
        "promotion_result": _promotion_result(),
    }


def _resource_registration_manifest(
    *, target_version: str = "v002"
) -> dict[str, Any]:
    plan = {
        "kind": "pipeline.shot_resource.publish_registration_plan",
        "schema_version": 1,
        "status": "ready",
        "ready_for_registration": True,
        "mutation_safe": True,
        "candidate_count": len(ROLES),
        "candidates": [
            {
                "status": "ready",
                "trust_status": "trusted",
                "asset_registration": {"name": f"sh010_{role}_{target_version}"},
            }
            for role in ROLES
        ],
    }
    return {
        "kind": (
            "pipeline.shot_resource.stream_promotion_registration_plan_result"
        ),
        "schema_version": 1,
        "operation_type": RESOURCE_PLAN_OPERATION,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "ready_for_registration": True,
        "registration_plan": plan,
        "intent_parameters": {
            "params": {"promotion_result": _promotion_result()},
            "idempotency_key": "promotion-callable-1:catalog-plan",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": RESOURCE_REGISTER_OPERATION_TYPE,
                    "candidate_count": len(ROLES),
                    "target_version": target_version,
                },
                "payload": {"registration_plan": plan},
            }
        ],
        "originating_capability": RESOURCE_PLAN_OPERATION,
        "apply_counterpart": {
            "tool": RESOURCE_REGISTER_TOOL,
            "parameter_overrides": {},
        },
    }


def _main_registration_manifest(
    *, promoted: tuple[str, ...] = PROMOTED_IDS
) -> dict[str, Any]:
    ready = make_main_plan(promoted_resource_asset_ids=list(promoted))
    return {
        "kind": (
            "pipeline.editorial_workspace.main_promotion_registration_plan_result"
        ),
        "schema_version": 1,
        "operation_type": MAIN_PLAN_OPERATION,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "ready_for_registration": True,
        "intent_parameters": {
            "params": {"workspace_main_promotion_plan": ready},
            "idempotency_key": "promotion-callable-1:main-registration-plan",
            "bridge_asset_ids": list(promoted),
            "project_id": PROJECT_ID,
            "requested_by": ACTOR,
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": MAIN_REGISTER_OPERATION_TYPE,
                    "project_id": PROJECT_ID,
                    "target_stream": "main",
                    "target_version_number": TARGET_MAIN_NUMBER,
                    "promoted_resource_asset_ids": list(promoted),
                },
                "payload": {"workspace_main_promotion_plan": ready},
            }
        ],
        "originating_capability": MAIN_PLAN_OPERATION,
        "apply_counterpart": {
            "tool": MAIN_REGISTER_TOOL,
            "parameter_overrides": {},
        },
    }


# --------------------------------------------------------------------------- #
# Fake MCP + fake operation runner shaped like the released Pipeline callables
# --------------------------------------------------------------------------- #
class FakeMCP:
    """Discover/verify/apply for the three admitted promotion tools."""

    def __init__(
        self,
        *,
        fresh_copy: dict[str, Any] | None = None,
        copy_apply_fails: bool = False,
        resource_apply: str = "registered",
        main_apply: str = "registered",
        discovery_raises: bool = False,
    ) -> None:
        self.copy = _copy_manifest()
        self.fresh_copy = fresh_copy
        self.copy_apply_fails = copy_apply_fails
        self.resource_apply = resource_apply
        self.main_apply = main_apply
        self.discovery_raises = discovery_raises
        self.calls: list[tuple[str, str]] = []
        self.apply_counts = {
            PROMOTE_TOOL: 0,
            RESOURCE_REGISTER_TOOL: 0,
            MAIN_REGISTER_TOOL: 0,
        }
        self.held_resource_manifest = _resource_registration_manifest()
        self.held_main_manifest = _main_registration_manifest()

    async def list_tools(self):
        schema = {
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
        }
        return [
            SimpleNamespace(name=name, inputSchema=schema)
            for name in (
                PROMOTE_TOOL,
                RESOURCE_REGISTER_TOOL,
                MAIN_REGISTER_TOOL,
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        mode = str(arguments.get("mode") or "discover")
        self.calls.append((name, mode))
        if name == PROMOTE_TOOL:
            if mode == "discover":
                if self.discovery_raises:
                    raise ConnectionError("/private/socket unreachable")
                return copy.deepcopy(self.copy)
            if mode == "verify":
                return copy.deepcopy(self.fresh_copy or self.copy)
            self.apply_counts[name] += 1
            if self.copy_apply_fails:
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "/private/copy failed",
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "promotion_apply": _promotion_result(),
                "catalog_registration_status": "pending",
            }
        if name == RESOURCE_REGISTER_TOOL:
            if mode == "verify":
                return copy.deepcopy(self.held_resource_manifest)
            self.apply_counts[name] += 1
            if self.resource_apply == "registered":
                return {
                    "ok": True,
                    "status": "succeeded",
                    "trust_status": "trusted",
                    "catalog_registration_status": "registered",
                    "created_asset_ids": list(PROMOTED_IDS),
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "catalog_registration_status": "partial",
                "created_asset_ids": [],
            }
        if name == MAIN_REGISTER_TOOL:
            if mode == "verify":
                return copy.deepcopy(self.held_main_manifest)
            self.apply_counts[name] += 1
            if self.main_apply == "registered":
                return {
                    "ok": True,
                    "status": "succeeded",
                    "trust_status": "trusted",
                    "catalog_status": "registered",
                    "main_version_id": MAIN_VERSION_ID,
                    "main_media_id": MAIN_MEDIA_ID,
                    "created_asset_ids": [MAIN_VERSION_ID, MAIN_MEDIA_ID],
                    "main_advanced": True,
                }
            if self.main_apply == "version_only":
                # Version registered, Media never landed — handoff §7.
                return {
                    "ok": True,
                    "status": "succeeded",
                    "trust_status": "trusted",
                    "catalog_status": "partial",
                    "main_version_id": MAIN_VERSION_ID,
                    "main_media_id": None,
                    "main_advanced": False,
                }
            if self.main_apply == "media_only":
                return {
                    "ok": True,
                    "status": "succeeded",
                    "trust_status": "trusted",
                    "catalog_status": "partial",
                    "main_version_id": None,
                    "main_media_id": MAIN_MEDIA_ID,
                    "main_advanced": False,
                }
            # location / lineage interruption: the callable itself refuses.
            return {
                "ok": False,
                "status": "failed",
                "trust_status": "review_required",
                "stage": (
                    "editorial_workspace_main_promotion_catalog_location_drift"
                    if self.main_apply == "location"
                    else "editorial_workspace_main_promotion_catalog_incomplete"
                ),
                "error": "/private/alias differs",
                "main_advanced": False,
            }
        raise AssertionError(name)


class FakeOperations:
    """The three Pipeline operations, as the operation runner sees them."""

    def __init__(self, *, mcp: FakeMCP) -> None:
        self._mcp = mcp
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(
        self, operation_type: str, *, params: dict[str, Any], **metadata: Any
    ):
        self.calls.append((operation_type, copy.deepcopy(params)))
        if operation_type == VALIDATE_OPERATION:
            assert params["promotion_commit"]["type"] == "commit_applied"
            return {"status": "success", "data": _validation()}
        if operation_type == RESOURCE_PLAN_OPERATION:
            assert params["promotion_commit"]["type"] == "commit_applied"
            assert params["promotion_validation"] == _validation()
            return {
                "status": "success",
                "data": copy.deepcopy(self._mcp.held_resource_manifest),
            }
        if operation_type == MAIN_PLAN_OPERATION:
            # Handoff §5: the operation refuses any resource registration
            # output that is not succeeded, trusted, and registered.
            commit = params["promotion_registration_commit"]
            apply_result = (
                commit.get("apply_result") if isinstance(commit, dict) else None
            )
            if (
                not isinstance(apply_result, dict)
                or apply_result.get("catalog_registration_status") != "registered"
            ):
                return {
                    "status": "failed",
                    "error_code": (
                        "editorial_workspace_main_promotion_"
                        "resource_registration_incomplete"
                    ),
                    "error": "promoted resources are not registered",
                }
            created = sorted(set(apply_result.get("created_asset_ids") or []))
            assert params["workspace_main_promotion_plan"]["kind"] == (
                "pipeline.editorial_workspace.main_promotion_plan"
            )
            assert metadata.get("idempotency_key", "").endswith(
                ":main-registration-plan"
            )
            return {
                "status": "success",
                "data": copy.deepcopy(self._mcp.held_main_manifest)
                if created == sorted(PROMOTED_IDS)
                else _main_registration_manifest(promoted=tuple(created)),
            }
        raise AssertionError(operation_type)


def build_api(**mcp_kwargs: Any):
    mcp = FakeMCP(**mcp_kwargs)
    operations = FakeOperations(mcp=mcp)
    gateway = InMemoryAssentGateway()
    store = InMemoryEditorialWorkspacePromotionWorkflowStore()
    api = make_editorial_workspace_promotion_workflow_api(
        session_factory=None,
        mcp=mcp,
        store=store,
        assent_gateway=gateway,
        run_operation=operations,
    )
    return api, mcp, operations, gateway, store


async def _propose(api, proposal=None):
    return await api.propose(proposal or make_proposal())


async def _full_apply(**mcp_kwargs: Any):
    api, mcp, operations, gateway, store = build_api(**mcp_kwargs)
    proposal = make_proposal()
    proposed = await _propose(api, proposal)
    applied = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )
    return api, mcp, operations, gateway, store, proposed, applied


# --------------------------------------------------------------------------- #
# §12.1 — unknown/missing fields and every fingerprint drift fail before MCP
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_1_unknown_missing_and_drifted_fields_fail_before_mcp():
    api, mcp, operations, _gateway, _store = build_api()

    async def refused(proposal: dict[str, Any]) -> str:
        with pytest.raises(EditorialWorkspacePromotionWorkflowError) as exc:
            await api.propose(proposal)
        return exc.value.code

    unknown = make_proposal()
    unknown["journal_path"] = "/private/journal.json"
    assert await refused(unknown) == "promotion_workflow_proposal_invalid"

    missing = make_proposal()
    missing.pop("source_main_version_id")
    assert await refused(missing) == "promotion_workflow_proposal_invalid"

    tampered = make_proposal()
    tampered["target_main_version_number"] = 7
    assert await refused(tampered) == "promotion_workflow_proposal_invalid"

    for field in (
        "promotion_plan_fingerprint",
        "promotion_callable_intent_fingerprint",
        "workspace_main_promotion_plan_fingerprint",
    ):
        drifted = make_proposal()
        drifted[field] = "d" * 64
        body = {
            key: value
            for key, value in drifted.items()
            if key not in {"kind", "schema_version", "fingerprint"}
        }
        drifted["fingerprint"] = _fingerprint(body)
        assert await refused(drifted) == "promotion_workflow_proposal_invalid"

    unsorted = make_proposal(selected_roles=["matte", "beauty"])
    assert await refused(unsorted) == "promotion_workflow_proposal_invalid"

    widened = make_proposal(
        workspace_main_promotion_plan=make_main_plan(
            selected_roles=["beauty", "matte", "extra"]
        )
    )
    assert await refused(widened) == "promotion_workflow_proposal_invalid"

    # Not one MCP or operation call was made by any of those refusals.
    assert mcp.calls == []
    assert operations.calls == []


# --------------------------------------------------------------------------- #
# §12.2 / §12.3 — duplicate propose; same authority under a new proposal
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_2_exact_duplicate_propose_returns_the_original_proposal():
    api, mcp, _operations, _gateway, _store = build_api()
    proposal = make_proposal()
    first = await api.propose(proposal)
    second = await api.propose(copy.deepcopy(proposal))

    assert first == second
    assert first["status"] == "proposed"
    # Discovery ran exactly once; the duplicate re-read durable state.
    assert mcp.calls == [(PROMOTE_TOOL, "discover")]


@pytest.mark.asyncio
async def test_3_same_authority_under_a_different_proposal_fails_closed():
    api, _mcp, _operations, _gateway, _store = build_api()
    await api.propose(make_proposal())

    with pytest.raises(EditorialWorkspacePromotionWorkflowError) as exc:
        await api.propose(make_proposal(publish_preview_id="publish-preview-2"))
    assert exc.value.code == "promotion_workflow_proposal_invalid"


# --------------------------------------------------------------------------- #
# §12.4 — propose performs physical discovery only, persists ONE AssentRecord
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_4_propose_discovers_only_and_persists_one_assent():
    api, mcp, operations, gateway, _store = build_api()
    receipt = await _propose(api)

    assert receipt["kind"] == RECEIPT_KIND
    assert receipt["action"] == "propose"
    assert receipt["status"] == "proposed"
    assert receipt["trust_status"] == "trusted"
    # ZERO mutation: no verify, no apply, no operation, no commit.
    assert mcp.calls == [(PROMOTE_TOOL, "discover")]
    assert mcp.apply_counts == {
        PROMOTE_TOOL: 0,
        RESOURCE_REGISTER_TOOL: 0,
        MAIN_REGISTER_TOOL: 0,
    }
    assert operations.calls == []
    assert receipt["dispatch_authorized"] is False
    assert receipt["applied"] is False
    assert receipt["main_advanced"] is False
    assert receipt["reconciliation_required"] is False
    assert receipt["promoted_resource_asset_ids"] == []
    assert receipt["assent_status"] == "proposed"
    assert receipt["resource_copy_manifest_fingerprint"] is not None
    assert (
        receipt["resource_copy_status"]
        == receipt["resource_registration_status"]
        == receipt["main_registration_status"]
        == "not_started"
    )
    # Exactly ONE AssentRecord, carrying the seven-step chain text.
    assert len(gateway._records) == 1
    record = next(iter(gateway._records.values()))
    assert record.status == "proposed"
    assert record.chain_steps.count("commit") == 3
    assert len(record.chain_steps) == 7


# --------------------------------------------------------------------------- #
# §12.5 — unratified apply refuses without verify/apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_5_unratified_apply_refuses_without_verify_or_apply():
    api, mcp, _operations, gateway, _store = build_api()
    proposed = await _propose(api)

    # Drop the record so ratification cannot succeed — the same closed path a
    # withdrawn or already-consumed assent takes.
    gateway._records.clear()
    receipt = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == "promotion_workflow_assent_invalid"
    assert receipt["dispatch_authorized"] is False
    assert mcp.apply_counts[PROMOTE_TOOL] == 0
    assert [call for call in mcp.calls if call[1] in {"verify", "apply"}] == []


# --------------------------------------------------------------------------- #
# §12.6 / §12.7 — the exact seven-node graph, each plan on the prior commit
# --------------------------------------------------------------------------- #
def test_6_bridge_composes_the_exact_seven_node_graph():
    sequence = promotion_operator_sequence(make_proposal())

    assert [step["operator_id"] for step in sequence] == [
        PROMOTE_TOOL,
        "commit",
        VALIDATE_OPERATION,
        RESOURCE_PLAN_OPERATION,
        "commit",
        MAIN_PLAN_OPERATION,
        "commit",
    ]
    # The final registration-plan node consumes the resource registration
    # commit under the exact input port named by the contract.
    main_plan = sequence[5]
    assert [item["metadata"]["role"] for item in main_plan["inputs"]] == [
        "promotion_registration_commit"
    ]
    assert main_plan["inputs"][0]["artifact_id"] == "registration:commit"
    assert set(main_plan["arguments"]) == {
        "workspace_main_promotion_plan",
        "idempotency_key",
        "project_id",
        "requested_by",
    }
    assert main_plan["arguments"]["idempotency_key"].endswith(
        ":main-registration-plan"
    )
    # Discovery node carries the retained callable intent, unwidened.
    assert sequence[0]["arguments"]["mode"] == "discover"
    assert sequence[0]["arguments"]["params"] == (
        make_callable_intent()["params"]
    )


@pytest.mark.asyncio
async def test_7_each_stage_dispatches_once_in_order_under_one_assent():
    _api, mcp, operations, gateway, _store, _proposed, applied = (
        await _full_apply()
    )

    assert applied["status"] == "applied"
    assert mcp.calls == [
        (PROMOTE_TOOL, "discover"),
        (PROMOTE_TOOL, "verify"),
        (PROMOTE_TOOL, "apply"),
        (RESOURCE_REGISTER_TOOL, "verify"),
        (RESOURCE_REGISTER_TOOL, "apply"),
        (MAIN_REGISTER_TOOL, "verify"),
        (MAIN_REGISTER_TOOL, "apply"),
    ]
    # ONE assent produced AT MOST ONE dispatch per stage.
    assert mcp.apply_counts == {
        PROMOTE_TOOL: 1,
        RESOURCE_REGISTER_TOOL: 1,
        MAIN_REGISTER_TOOL: 1,
    }
    assert [name for name, _params in operations.calls] == [
        VALIDATE_OPERATION,
        RESOURCE_PLAN_OPERATION,
        MAIN_PLAN_OPERATION,
    ]
    # ONE AssentRecord governed all three commits; ratify was called once.
    assert len(gateway._records) == 1
    assert len(gateway.ratify_calls) == 1
    # Each downstream plan consumed the EXACT prior commit output.
    main_params = dict(operations.calls[2][1])
    commit = main_params["promotion_registration_commit"]
    assert commit["type"] == "commit_applied"
    assert commit["apply_result"]["created_asset_ids"] == list(PROMOTED_IDS)


# --------------------------------------------------------------------------- #
# §12.8 — selected roles and resource IDs cannot widen, reorder, or drift
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_8_roles_and_resource_ids_cannot_widen_or_drift():
    api, _mcp, _operations, _gateway, _store = build_api()
    proposed = await _propose(api)

    drifted = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint="e" * 64,
        requested_by=ACTOR,
    )
    assert drifted["status"] == "failed"
    assert drifted["reason_code"] == "promotion_workflow_proposal_changed"
    assert drifted["dispatch_authorized"] is False

    # A widened proposal is a DIFFERENT proposal id; it never rebinds the
    # original workflow, and it cannot rebind the same held authority (§12.3).
    with pytest.raises(EditorialWorkspacePromotionWorkflowError):
        await api.propose(
            make_proposal(
                selected_roles=["beauty", "extra", "matte"],
                published_resource_asset_ids=["published-1", "published-2"],
            )
        )


# --------------------------------------------------------------------------- #
# §12.9 — stale source refuses BEFORE main registration
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_9_stale_source_refuses_before_main_registration():
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(fresh_copy=_copy_manifest(target_version="v003"))
    )

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == "promotion_workflow_resource_copy_failed"
    # Verify-time drift: nothing was dispatched anywhere.
    assert mcp.apply_counts == {
        PROMOTE_TOOL: 0,
        RESOURCE_REGISTER_TOOL: 0,
        MAIN_REGISTER_TOOL: 0,
    }
    assert receipt["dispatch_authorized"] is False
    assert receipt["reconciliation_required"] is False
    assert receipt["main_registration_status"] == "not_started"


# --------------------------------------------------------------------------- #
# §12.10 — successful apply retains six fingerprints and both main asset IDs
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_10_applied_receipt_carries_all_evidence():
    *_rest, applied = await _full_apply()

    assert applied["status"] == "applied"
    assert applied["trust_status"] == "trusted"
    assert applied["applied"] is True
    assert applied["main_advanced"] is True
    assert applied["reconciliation_required"] is False
    assert applied["dispatch_authorized"] is True
    assert applied["resource_copy_status"] == "applied"
    assert applied["resource_registration_status"] == "registered"
    assert applied["main_registration_status"] == "registered"
    assert applied["promoted_resource_asset_ids"] == sorted(PROMOTED_IDS)
    assert len(applied["promoted_resource_asset_ids"]) == len(
        applied["selected_roles"]
    )
    assert applied["main_version_id"] == MAIN_VERSION_ID
    assert applied["main_media_id"] == MAIN_MEDIA_ID
    fingerprints = [
        applied[field]
        for field in (
            "resource_copy_manifest_fingerprint",
            "resource_copy_commit_fingerprint",
            "resource_registration_manifest_fingerprint",
            "resource_registration_commit_fingerprint",
            "main_registration_manifest_fingerprint",
            "main_registration_commit_fingerprint",
        )
    ]
    assert all(isinstance(item, str) and len(item) == 64 for item in fingerprints)
    # Six DISTINCT fingerprints — no stage silently reuses another's evidence.
    assert len(set(fingerprints)) == 6


# --------------------------------------------------------------------------- #
# §12.11 — every partial-failure variant reports honest stage statuses
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "main_apply", ["version_only", "media_only", "location", "lineage"]
)
async def test_11_partial_failure_variants_report_honest_stages(main_apply):
    _api, mcp, _operations, gateway, _store, _proposed, receipt = (
        await _full_apply(main_apply=main_apply)
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["trust_status"] == "review_required"
    assert receipt["applied"] is False
    assert receipt["main_advanced"] is False
    assert receipt["reconciliation_required"] is True
    assert receipt["dispatch_authorized"] is True
    assert receipt["reason_code"] == (
        "promotion_workflow_main_registration_failed"
    )
    # The two completed stages stay honestly complete; only main failed.
    assert receipt["resource_copy_status"] == "applied"
    assert receipt["resource_registration_status"] == "registered"
    assert receipt["main_registration_status"] == "failed"
    assert receipt["promoted_resource_asset_ids"] == sorted(PROMOTED_IDS)
    assert receipt["main_registration_commit_fingerprint"] is None
    assert receipt["resource_registration_commit_fingerprint"] is not None
    assert mcp.apply_counts[MAIN_REGISTER_TOOL] == 1
    # The assent stays RATIFIED so replay can forward-complete under it.
    record = next(iter(gateway._records.values()))
    assert record.status == "ratified"


@pytest.mark.asyncio
async def test_11b_resource_registration_interruption_is_partial_too():
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(resource_apply="partial")
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["resource_copy_status"] == "applied"
    assert receipt["resource_registration_status"] == "failed"
    assert receipt["main_registration_status"] == "not_started"
    assert receipt["reason_code"] == (
        "promotion_workflow_resource_registration_failed"
    )
    assert receipt["promoted_resource_asset_ids"] == []
    # The main registration never dispatched on incomplete resource evidence.
    assert mcp.apply_counts[MAIN_REGISTER_TOOL] == 0


# --------------------------------------------------------------------------- #
# §12.12 / §12.13 — replay forward-completes; replay of a completed graph is a
# no-op; neither creates a new AssentRecord
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_12_replay_forward_completes_without_duplicate_mutation():
    api, mcp, operations, gateway, _store, proposed, partial = (
        await _full_apply(main_apply="version_only")
    )
    assert partial["status"] == "partial_failed"

    # The interruption clears; replay must complete ONLY the missing stage.
    mcp.main_apply = "registered"
    mcp.calls.clear()
    operations.calls.clear()
    replayed = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert replayed["status"] == "applied"
    assert replayed["action"] == "replay"
    assert replayed["replayed"] is True
    assert replayed["main_advanced"] is True
    assert replayed["reconciliation_required"] is False
    # NO duplicate copy and NO duplicate resource registration.
    assert mcp.apply_counts == {
        PROMOTE_TOOL: 1,
        RESOURCE_REGISTER_TOOL: 1,
        MAIN_REGISTER_TOOL: 2,
    }
    assert mcp.calls == [
        (MAIN_REGISTER_TOOL, "verify"),
        (MAIN_REGISTER_TOOL, "apply"),
    ]
    assert [name for name, _p in operations.calls] == [MAIN_PLAN_OPERATION]
    # NO new AssentRecord, and no second ratification.
    assert len(gateway._records) == 1
    assert len(gateway.ratify_calls) == 1
    # Replay never widened authority.
    assert replayed["selected_roles"] == partial["selected_roles"]
    assert replayed["proposal_fingerprint"] == partial["proposal_fingerprint"]
    assert replayed["assent_record_id"] == partial["assent_record_id"]
    assert replayed["target_main_version_number"] == (
        partial["target_main_version_number"]
    )
    # Handoff §7 (reconciled at forge-pipeline@cd6abf3e) names ONE dependency
    # Bridge must preserve: promoted_resource_asset_ids feeds the main plan's
    # catalog transaction fingerprint, so a replay that re-derived a different
    # ID set would change the main-plan idempotency keys and make duplicate
    # main assets reachable. Bridge does not merely "replay to the same IDs" —
    # once the registration stage is durably `registered` its node is never
    # re-composed, so the ID set and the exact commit projection the main plan
    # consumes are frozen, not recomputed.
    assert replayed["promoted_resource_asset_ids"] == (
        partial["promoted_resource_asset_ids"]
    )
    assert replayed["resource_registration_commit_fingerprint"] == (
        partial["resource_registration_commit_fingerprint"]
    )
    # The resumed main-plan node consumed the PERSISTED registration commit
    # projection — the registration tool was not called again at all.
    assert RESOURCE_REGISTER_TOOL not in {name for name, _mode in mcp.calls}
    assert operations.calls[0][1]["promotion_registration_commit"][
        "apply_result"
    ]["created_asset_ids"] == list(PROMOTED_IDS)


@pytest.mark.asyncio
async def test_13_replay_of_a_completed_graph_performs_no_mutation():
    api, mcp, operations, gateway, _store, proposed, applied = (
        await _full_apply()
    )
    assert applied["status"] == "applied"
    before = dict(mcp.apply_counts)
    mcp.calls.clear()
    operations.calls.clear()

    replayed = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert replayed["status"] == "applied"
    assert mcp.apply_counts == before
    assert mcp.calls == []
    assert operations.calls == []
    assert len(gateway._records) == 1
    assert len(gateway.ratify_calls) == 1


@pytest.mark.asyncio
async def test_12b_replay_resumes_from_the_resource_registration_stage():
    api, mcp, operations, gateway, _store, proposed, partial = (
        await _full_apply(resource_apply="partial")
    )
    assert partial["resource_registration_status"] == "failed"

    mcp.resource_apply = "registered"
    mcp.calls.clear()
    operations.calls.clear()
    replayed = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert replayed["status"] == "applied"
    # The physical copy is NEVER re-run: no promote verify and no promote apply.
    assert PROMOTE_TOOL not in {name for name, _mode in mcp.calls}
    assert mcp.apply_counts[PROMOTE_TOOL] == 1
    assert [name for name, _p in operations.calls] == [
        VALIDATE_OPERATION,
        RESOURCE_PLAN_OPERATION,
        MAIN_PLAN_OPERATION,
    ]
    # The resumed validate consumed the PERSISTED copy-commit projection.
    assert operations.calls[0][1]["promotion_commit"]["type"] == "commit_applied"
    assert len(gateway.ratify_calls) == 1


@pytest.mark.asyncio
async def test_12c_replay_before_ratification_is_unavailable():
    api, mcp, _operations, gateway, _store = build_api()
    proposed = await _propose(api)

    receipt = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == "promotion_workflow_replay_unavailable"
    assert mcp.apply_counts[PROMOTE_TOOL] == 0
    assert gateway.ratify_calls == []


# --------------------------------------------------------------------------- #
# §12.14 — status performs no discovery, assent, commit, or MCP apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_14_status_is_a_durable_non_mutating_read():
    api, mcp, operations, gateway, _store = build_api()
    proposed = await _propose(api)
    mcp.calls.clear()

    polled = await api.status(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )

    assert polled["action"] == "status"
    assert polled["status"] == "proposed"
    assert mcp.calls == []
    assert operations.calls == []
    assert gateway.ratify_calls == []
    assert mcp.apply_counts == {
        PROMOTE_TOOL: 0,
        RESOURCE_REGISTER_TOOL: 0,
        MAIN_REGISTER_TOOL: 0,
    }

    with pytest.raises(EditorialWorkspacePromotionWorkflowError) as exc:
        await api.status(
            proposal_id="epr_missing", expected_proposal_fingerprint="f" * 64
        )
    assert exc.value.code == "promotion_workflow_proposal_not_found"


@pytest.mark.asyncio
async def test_14b_status_reports_the_partial_disposition_durably():
    api, _mcp, _operations, _gateway, _store, proposed, partial = (
        await _full_apply(main_apply="media_only")
    )

    polled = await api.status(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )

    assert polled["status"] == "partial_failed"
    assert polled["reconciliation_required"] is True
    assert polled["main_registration_status"] == "failed"
    assert polled["resource_copy_status"] == partial["resource_copy_status"]


# --------------------------------------------------------------------------- #
# §12.15 — restart preserves proposal, graph, assent, stage, and replay
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_15_restart_preserves_the_whole_durable_workflow():
    api, mcp, operations, gateway, store, proposed, partial = (
        await _full_apply(main_apply="version_only")
    )
    assert partial["status"] == "partial_failed"

    # A "restart": a brand new API object over the SAME durable store and the
    # same assent gateway. Nothing is carried in process memory.
    restarted = make_editorial_workspace_promotion_workflow_api(
        session_factory=None,
        mcp=mcp,
        store=store,
        assent_gateway=gateway,
        run_operation=operations,
    )
    row = await store.get_by_proposal_id(proposed["proposal_id"])

    assert row["proposal"]["fingerprint"] == proposed["proposal_fingerprint"]
    assert row["graph_node_sequence"] == [
        PROMOTE_TOOL,
        "commit",
        VALIDATE_OPERATION,
        RESOURCE_PLAN_OPERATION,
        "commit",
        MAIN_PLAN_OPERATION,
        "commit",
    ]
    assert row["assent_status"] == "ratified"
    assert row["resource_copy_status"] == "applied"
    assert row["main_registration_status"] == "failed"
    assert row["resource_copy_held_manifest"]["type"] == "mutation_plan"

    mcp.main_apply = "registered"
    replayed = await restarted.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )
    assert replayed["status"] == "applied"
    assert replayed["replayed"] is True


# --------------------------------------------------------------------------- #
# §12.16 — concurrent transition attempts do not double-apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_16_concurrent_transitions_do_not_double_apply():
    api, mcp, _operations, gateway, _store = build_api()
    proposed = await _propose(api)

    receipts = await asyncio.gather(
        *[
            api.ratify_apply(
                proposal_id=proposed["proposal_id"],
                expected_proposal_fingerprint=proposed[
                    "proposal_fingerprint"
                ],
                requested_by=ACTOR,
            )
            for _ in range(4)
        ]
    )

    assert mcp.apply_counts == {
        PROMOTE_TOOL: 1,
        RESOURCE_REGISTER_TOOL: 1,
        MAIN_REGISTER_TOOL: 1,
    }
    assert len(gateway.ratify_calls) == 1
    assert sum(1 for item in receipts if item["applied"]) == len(receipts)
    assert {item["status"] for item in receipts} == {"applied"}


@pytest.mark.asyncio
async def test_16b_concurrent_replay_over_a_partial_does_not_double_register():
    api, mcp, _operations, gateway, _store, proposed, partial = (
        await _full_apply(main_apply="version_only")
    )
    mcp.main_apply = "registered"

    receipts = await asyncio.gather(
        *[
            api.replay(
                proposal_id=proposed["proposal_id"],
                expected_proposal_fingerprint=proposed[
                    "proposal_fingerprint"
                ],
                requested_by=ACTOR,
            )
            for _ in range(3)
        ]
    )

    # Exactly one additional main registration: 1 partial + 1 completing apply.
    assert mcp.apply_counts[MAIN_REGISTER_TOOL] == 2
    assert mcp.apply_counts[PROMOTE_TOOL] == 1
    assert mcp.apply_counts[RESOURCE_REGISTER_TOOL] == 1
    assert {item["status"] for item in receipts} == {"applied"}
    assert len(gateway.ratify_calls) == 1


# --------------------------------------------------------------------------- #
# §12.17 / §12.18 — closed field set, valid fingerprint, no private bodies
# --------------------------------------------------------------------------- #
_RECEIPT_FIELDS = {
    "kind", "schema_version", "action", "status", "trust_status",
    "workflow_id", "proposal_id", "proposal_fingerprint",
    "promotion_preview_id", "promotion_preview_fingerprint",
    "promotion_authority_fingerprint", "source_version_id",
    "source_main_version_id", "target_main_version_number", "selected_roles",
    "published_resource_asset_ids", "promoted_resource_asset_ids",
    "main_version_id", "main_media_id", "assent_record_id", "assent_status",
    "resource_copy_manifest_fingerprint", "resource_copy_commit_fingerprint",
    "resource_copy_status", "resource_registration_manifest_fingerprint",
    "resource_registration_commit_fingerprint",
    "resource_registration_status", "main_registration_manifest_fingerprint",
    "main_registration_commit_fingerprint", "main_registration_status",
    "dispatch_authorized", "applied", "replayed", "main_advanced",
    "reconciliation_required", "reason_code", "fingerprint",
}
_PRIVATE_MARKERS = (
    "/private/",
    "/capture/",
    "workfile.batch",
    "promotion_plan",
    "callable_intent",
    "resolved_plan",
    "intent_parameters",
    "workspace_main_promotion_plan",
    "apply_result",
    "registration_plan",
    "source_location",
    "target_path",
)


def _assert_closed_and_path_free(receipt: dict[str, Any], label: str) -> None:
    assert set(receipt) == _RECEIPT_FIELDS, label
    assert receipt["kind"] == RECEIPT_KIND, label
    body = {
        key: value
        for key, value in receipt.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    assert receipt["fingerprint"] == _fingerprint(body), label
    serialized = json.dumps(receipt)
    assert "/" not in serialized, label
    for marker in _PRIVATE_MARKERS:
        assert marker not in serialized, (label, marker)


@pytest.mark.asyncio
async def test_17_every_receipt_is_closed_and_self_verifying():
    for receipt, label in await _lifecycle_receipts():
        _assert_closed_and_path_free(receipt, label)


@pytest.mark.asyncio
async def test_18_errors_and_receipts_never_leak_private_bodies():
    api, _mcp, _operations, _gateway, _store = build_api(discovery_raises=True)
    with pytest.raises(EditorialWorkspacePromotionWorkflowError) as exc:
        await _propose(api)
    assert exc.value.code == "promotion_workflow_callable_unavailable"
    assert "/private/" not in str(exc.value)
    assert "/" not in str(exc.value)

    # A proposal refusal quotes field names, never values: here the retained
    # callable intent carries an absolute path AND drifts from the manifest.
    api2, _m2, _o2, _g2, _s2 = build_api()
    bad = make_proposal(
        promotion_callable_intent=make_callable_intent(
            params={"canonical": "/private/leak", "shot": "sh010"}
        )
    )
    with pytest.raises(EditorialWorkspacePromotionWorkflowError) as exc2:
        await api2.propose(bad)
    assert exc2.value.code == "promotion_workflow_manifest_invalid"
    assert "/private/" not in str(exc2.value)
    assert "/" not in str(exc2.value)


# --------------------------------------------------------------------------- #
# Fixture capture — the pin Pipeline's strict adapter parses
# --------------------------------------------------------------------------- #
async def _lifecycle_receipts() -> list[tuple[dict[str, Any], str]]:
    """Capture one receipt per terminal from the LIVE API, never hand-built."""
    receipts: list[tuple[dict[str, Any], str]] = []

    api, _mcp, _ops, _gw, _store = build_api()
    proposed = await _propose(api)
    receipts.append((proposed, "proposed"))
    common = {
        "proposal_id": proposed["proposal_id"],
        "expected_proposal_fingerprint": proposed["proposal_fingerprint"],
    }
    receipts.append((await api.status(**common), "status_proposed"))

    api, mcp, _ops, _gw, _store, proposed, applied = await _full_apply()
    receipts.append((applied, "applied"))
    common = {
        "proposal_id": proposed["proposal_id"],
        "expected_proposal_fingerprint": proposed["proposal_fingerprint"],
    }
    receipts.append((await api.replay(**common, requested_by=ACTOR), "replayed"))

    api, mcp, _ops, _gw, _store, proposed, partial = await _full_apply(
        main_apply="version_only"
    )
    receipts.append((partial, "partial_failed"))
    common = {
        "proposal_id": proposed["proposal_id"],
        "expected_proposal_fingerprint": proposed["proposal_fingerprint"],
    }
    mcp.main_apply = "registered"
    receipts.append(
        (await api.replay(**common, requested_by=ACTOR), "replay_completed")
    )

    api, _mcp, _ops, _gw, _store, proposed, failed = await _full_apply(
        fresh_copy=_copy_manifest(target_version="v003")
    )
    receipts.append((failed, "failed"))

    api, _mcp, _ops, _gw, _store = build_api()
    proposed = await _propose(api)
    receipts.append(
        (
            await api.replay(
                proposal_id=proposed["proposal_id"],
                expected_proposal_fingerprint=proposed[
                    "proposal_fingerprint"
                ],
                requested_by=ACTOR,
            ),
            "unavailable",
        )
    )
    return receipts


@pytest.mark.asyncio
async def test_receipt_fixture_matches_the_live_api():
    """The committed fixture is CAPTURED, not authored.

    Run with ``FORGE_BRIDGE_CAPTURE_FIXTURES=1`` to refresh it.
    """
    import os

    captured = {label: receipt for receipt, label in await _lifecycle_receipts()}
    if os.environ.get("FORGE_BRIDGE_CAPTURE_FIXTURES") == "1":
        _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        _FIXTURE.write_text(json.dumps(captured, indent=2, sort_keys=True) + "\n")
    stored = json.loads(_FIXTURE.read_text())
    assert stored == captured


# --------------------------------------------------------------------------- #
# Cross-check against Pipeline's released frozen dataclass
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_pipeline_dataclass_proposal_is_accepted_unchanged():
    """A proposal built by Pipeline's own frozen dataclass proposes verbatim."""
    module = pytest.importorskip(
        "forge_core.session.editorial_workspace_promotion_workflow"
    )
    main_plan = make_main_plan()
    intent = make_callable_intent()
    promotion_plan = {
        "kind": "pipeline.shot_resource.stream_promotion_plan",
        "actions": [{"source_path": "/private/published.exr"}],
    }
    proposal = module.EditorialWorkspacePromotionBridgeProposal(
        project_id=PROJECT_ID,
        requested_by=ACTOR,
        promotion_preview_id="promotion-preview-1",
        promotion_preview_fingerprint="a" * 64,
        promotion_authority_fingerprint="b" * 64,
        publish_preview_id="publish-preview-1",
        publish_preview_fingerprint="c" * 64,
        source_version_id=SOURCE_VERSION_ID,
        source_main_version_id=SOURCE_MAIN_VERSION_ID,
        target_main_version_number=TARGET_MAIN_NUMBER,
        selected_roles=tuple(sorted(ROLES)),
        published_resource_asset_ids=tuple(sorted(PUBLISHED_IDS)),
        promotion_plan_fingerprint=_fingerprint(promotion_plan),
        promotion_callable_intent_fingerprint=_fingerprint(intent),
        workspace_main_promotion_plan_fingerprint=_fingerprint(main_plan),
        promotion_plan=promotion_plan,
        promotion_callable_intent=intent,
        workspace_main_promotion_plan=main_plan,
    )
    api, _mcp, _ops, _gw, _store = build_api()

    receipt = await api.propose(proposal.to_dict())

    assert receipt["status"] == "proposed"
    assert receipt["proposal_fingerprint"] == proposal.fingerprint
    # And Bridge's receipt parses back through Pipeline's strict dataclass.
    parsed = {
        key: value
        for key, value in receipt.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    for field in (
        "selected_roles",
        "published_resource_asset_ids",
        "promoted_resource_asset_ids",
    ):
        parsed[field] = tuple(parsed[field])
    rebuilt = module.EditorialWorkspacePromotionBridgeReceipt(**parsed)
    assert rebuilt.to_dict() == receipt
