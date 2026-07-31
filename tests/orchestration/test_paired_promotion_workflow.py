"""Acceptance matrix for #261 / Pipeline Phase 160 — the paired render +
workfile promotion workflow API.

Like the #244 matrix these do NOT fake the commit rail: the API is built with
the real ``MCPToolBoundary``, the real ``OperationDispatchBoundary``, and the
real verify-before-apply ``CommitBoundary``, driven by a fake MCP and a fake
operation runner shaped like the released Pipeline callables. Only Postgres is
substituted (in-memory workflow store + in-memory AssentRecord gateway), so
discover/verify/apply ordering, ONE-assent-over-FOUR-commits, plan drift, the
partial-failure dispositions, and resumable replay are proven end to end.

Every payload shape here is DERIVED from Pipeline at ``6f0c7075``:

- workfile manifest envelope + identity keys — ``forge_core/bridge/registry.py``
  ``_workfile_stream_promotion_manifest`` (:968-1023);
- workfile plan body — ``forge_core/workfile/callable_promotion.py``
  ``resolve_workfile_stream_promotion_plan`` (:325-355);
- workfile apply envelope — same file, :117-137, over
  ``WorkfileOp.promote_stream`` (``forge_core/workfile/ops.py``:1437-1453);
- lineage manifest identity — ``registry.py``:1137-1176;
- lineage apply envelope — ``forge_core/workfile/promoted_lineage.py``:98-115
  and :296-311;
- registration apply envelope —
  ``forge_core/shot_resources/callable_promotion_registration.py``:184-197 with
  ``publish_register`` from
  ``forge_core/operations/shot_resource_publish_registration_plan.py``:319-345.

The identifiers are the RETAINED live Phase 160 preparation identities from the
issue's last comment, so the offline matrix and the live UAT name the same
artist render, render Media, and exact rendered-from Batch Version.
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

from forge_bridge.orchestration.paired_promotion_workflow import (
    LINEAGE_BIND_TOOL,
    LINEAGE_CALLABLE_OPERATION_TYPE,
    PROMOTE_TOOL,
    PROPOSAL_KIND,
    RECEIPT_KIND,
    RESOURCE_PLAN_OPERATION,
    RESOURCE_REGISTER_TOOL,
    VALIDATE_OPERATION,
    WORKFILE_CALLABLE_OPERATION_TYPE,
    WORKFILE_PROMOTE_TOOL,
    InMemoryAssentGateway,
    InMemoryPairedPromotionWorkflowStore,
    PairedPromotionWorkflowError,
    make_paired_promotion_workflow_api,
    paired_promotion_operator_sequence,
)

# --------------------------------------------------------------------------- #
# Retained live Phase 160 preparation identities (issue #261, last comment)
# --------------------------------------------------------------------------- #
PROJECT_ID = "FORGE_UAT"
ACTOR = "supervisor-1"
SHOT_ID = "forge_uat_010"
ARTIST_STREAM = "uat-phase160-20260730-213027-fixed"
SOURCE_RENDER_VERSION_ID = "c227ce59-8e5f-4bb0-a6e2-ae41b957dc19"
SOURCE_RENDER_MEDIA_ID = "ca67767a-e79e-4a8d-8827-0225e0f52151"
SOURCE_WORKFILE_VERSION_ID = "2d0f5670-ab64-4e13-a3d9-a97ffdb8ec34"
WORKFILE_V001 = "1ba9e4e7-88db-4c2d-bdd7-42fc62ce97d9"
WORKFILE_V002 = "ce8cc2e6-0915-49c5-ab53-1ab04c8d57d7"
# Main authority fingerprint retained from the live preparation report.
MAIN_AUTHORITY_FINGERPRINT = (
    "b695a017eb35c045ea79d8631a7ee07227f1dbeea897cc551a722d6f4f1fc34d"
)

MAIN_RENDER_VERSION_ID = "main-render-version-1"
MAIN_RENDER_MEDIA_ID = "main-render-media-1"
MAIN_WORKFILE_VERSION_ID = "main-workfile-version-1"
MAIN_WORKFILE_MEDIA_ID = "main-workfile-media-1"
LINEAGE_RELATIONSHIP_ID = "lineage-relationship-1"

ROLES = ("comp",)
PUBLISHED_IDS = tuple(sorted((SOURCE_RENDER_VERSION_ID, SOURCE_RENDER_MEDIA_ID)))
PROMOTED_IDS = tuple(sorted((MAIN_RENDER_VERSION_ID, MAIN_RENDER_MEDIA_ID)))

PROMOTION_CALLABLE_OPERATION_TYPE = (
    "pipeline.shot_resource.stream_promotion.callable"
)
RESOURCE_REGISTER_OPERATION_TYPE = (
    "pipeline.shot_resource.stream_promotion.registration.callable"
)

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "paired_promotion_workflow_receipt.json"
)


def _fingerprint(value: Any) -> str:
    """Independent canonical fingerprint — the consumer's own arithmetic."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# --------------------------------------------------------------------------- #
# Proposal fixtures
# --------------------------------------------------------------------------- #
def make_promotion_intent(**overrides: Any) -> dict[str, Any]:
    intent = {
        "tool": PROMOTE_TOOL,
        "operation_type": PROMOTION_CALLABLE_OPERATION_TYPE,
        # Private absolute paths: must never reach a receipt.
        "params": {"canonical": "/private/forge_uat", "shot": SHOT_ID},
        "bridge_asset_ids": list(PUBLISHED_IDS),
        "idempotency_key": "paired-promotion-1",
        "project_id": PROJECT_ID,
        "requested_by": ACTOR,
    }
    intent.update(overrides)
    return intent


def make_workfile_intent(**overrides: Any) -> dict[str, Any]:
    """The retained workfile callable intent.

    Param names are Pipeline's, from the issue's declared intent block and
    ``forge_core/workfile/callable_promotion.py``:152-205.
    """
    intent = {
        "tool": WORKFILE_PROMOTE_TOOL,
        "operation_type": WORKFILE_CALLABLE_OPERATION_TYPE,
        "params": {
            "canonical": "/private/forge_uat",
            "config_path": (
                "/private/forge_uat/_07_system/cfg/forge/pipeline_config.yaml"
            ),
            "source_version_id": SOURCE_WORKFILE_VERSION_ID,
            "owner_id": SHOT_ID,
            "owner_type": "shot",
            "task": "comp",
            "dcc": "flame",
            "source_stream": ARTIST_STREAM,
            "target_stream": "main",
        },
        "bridge_asset_ids": [SOURCE_WORKFILE_VERSION_ID],
        "idempotency_key": "paired-promotion-1:workfile",
        "project_id": PROJECT_ID,
        "requested_by": ACTOR,
    }
    intent.update(overrides)
    return intent


def make_proposal(**overrides: Any) -> dict[str, Any]:
    promotion_intent = overrides.pop("promotion_callable_intent", None) or (
        make_promotion_intent()
    )
    workfile_intent = overrides.pop("workfile_callable_intent", None) or (
        make_workfile_intent()
    )
    promotion_plan = overrides.pop("promotion_plan", None) or {
        "kind": "pipeline.shot_resource.stream_promotion_plan",
        "actions": [{"source_path": "/private/forge_uat/published.exr"}],
    }
    proposal = {
        "kind": PROPOSAL_KIND,
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "requested_by": ACTOR,
        "promotion_preview_id": "paired-preview-1",
        "promotion_preview_fingerprint": "a" * 64,
        "promotion_authority_fingerprint": MAIN_AUTHORITY_FINGERPRINT,
        "source_render_version_id": SOURCE_RENDER_VERSION_ID,
        "source_render_media_id": SOURCE_RENDER_MEDIA_ID,
        "source_workfile_version_id": SOURCE_WORKFILE_VERSION_ID,
        "selected_roles": sorted(ROLES),
        "published_resource_asset_ids": sorted(PUBLISHED_IDS),
        "promotion_plan_fingerprint": _fingerprint(promotion_plan),
        "promotion_callable_intent_fingerprint": _fingerprint(promotion_intent),
        "workfile_callable_intent_fingerprint": _fingerprint(workfile_intent),
        "promotion_plan": promotion_plan,
        "promotion_callable_intent": promotion_intent,
        "workfile_callable_intent": workfile_intent,
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
        "canonical": "/private/forge_uat",
        "shot": SHOT_ID,
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
                "target_path": f"/private/{SHOT_ID}/{role}/{target_version}",
            }
            for role in ROLES
        ],
    }


def _copy_manifest(*, target_version: str = "v002") -> dict[str, Any]:
    intent = make_promotion_intent()
    plan = {
        "kind": "pipeline.shot_resource.stream_promotion_plan",
        "schema_version": 1,
        "status": "ready",
        "ready_for_promotion": True,
        "mutation_safe": True,
        "shot": SHOT_ID,
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
                    "shot": SHOT_ID,
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


def _resource_registration_manifest() -> dict[str, Any]:
    plan = {
        "kind": "pipeline.shot_resource.publish_registration_plan",
        "schema_version": 1,
        "status": "ready",
        "ready_for_registration": True,
        "mutation_safe": True,
        "candidate_count": 2,
        "candidates": [
            {
                "status": "ready",
                "trust_status": "trusted",
                "asset_registration": {
                    "type": kind,
                    "name": f"{SHOT_ID}_comp_v002",
                },
            }
            for kind in ("version", "media")
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
            "idempotency_key": "paired-promotion-1:catalog-plan",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": RESOURCE_REGISTER_OPERATION_TYPE,
                    "candidate_count": 2,
                    "target_version": "v002",
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


def _workfile_plan(*, target_version_number: int = 4) -> dict[str, Any]:
    """``resolve_workfile_stream_promotion_plan``'s return, verbatim keys."""
    return {
        "kind": "pipeline.workfile.stream_promotion_plan",
        "schema_version": 1,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "project_id": PROJECT_ID,
        "owner_id": SHOT_ID,
        "owner_type": "shot",
        "task": "comp",
        "dcc": "flame",
        "source_version_id": SOURCE_WORKFILE_VERSION_ID,
        "source_version_number": 3,
        "source_stream": ARTIST_STREAM,
        "source_path": f"/private/{SHOT_ID}/_streams/{ARTIST_STREAM}/comp_v003.batch",
        "source_tokenized_path": (
            f"{{shots}}/{SHOT_ID}/_streams/{ARTIST_STREAM}/comp_v003.batch"
        ),
        "source_workfile_identity": {
            "package_kind": "flame_batch_setup",
            "sidecar_present": True,
        },
        "target_stream": "main",
        "target_version_id": None,
        "target_version_number": target_version_number,
        "target_path": (
            f"/private/{SHOT_ID}/comp_v{target_version_number:03d}.batch"
        ),
        "scene_asset_root": f"/private/{SHOT_ID}",
        "shots_root": "/private/forge_uat/shots",
        "assets_root": "/private/forge_uat/assets",
        "project_root": "/private/forge_uat",
        "config_path": (
            "/private/forge_uat/_07_system/cfg/forge/pipeline_config.yaml"
        ),
        "idempotent_replay": False,
    }


def _workfile_manifest(*, target_version_number: int = 4) -> dict[str, Any]:
    intent = make_workfile_intent()
    plan = _workfile_plan(target_version_number=target_version_number)
    identity = {
        "operation_type": WORKFILE_CALLABLE_OPERATION_TYPE,
        **{
            key: plan[key]
            for key in (
                "kind",
                "project_id",
                "owner_id",
                "task",
                "dcc",
                "source_version_id",
                "source_stream",
                "target_stream",
                "target_version_number",
            )
        },
    }
    return {
        "kind": "pipeline.workfile.stream_promotion_callable_result",
        "schema_version": 1,
        "operation_type": WORKFILE_CALLABLE_OPERATION_TYPE,
        "ok": True,
        "status": "succeeded",
        "trust_status": "trusted",
        "mode": "discover",
        "mutation_safe": True,
        "plan_source": "compiled",
        "promotion_plan": plan,
        "idempotency_key": intent["idempotency_key"],
        "bridge_asset_ids": list(intent["bridge_asset_ids"]),
        "type": "mutation_plan",
        "intent_parameters": {
            "params": dict(intent["params"]),
            "idempotency_key": intent["idempotency_key"],
            "bridge_asset_ids": list(intent["bridge_asset_ids"]),
            "project_id": intent["project_id"],
            "requested_by": intent["requested_by"],
        },
        "resolved_plan": [
            {"identity": identity, "payload": {"promotion_plan": plan}}
        ],
        "originating_capability": WORKFILE_PROMOTE_TOOL,
        "apply_counterpart": {
            "tool": WORKFILE_PROMOTE_TOOL,
            "parameter_overrides": {},
        },
    }


def _lineage_plan(
    *,
    main_render_version_id: str,
    main_workfile_version_id: str,
) -> dict[str, Any]:
    authority = {
        "project_id": PROJECT_ID,
        "owner_id": SHOT_ID,
        "source_render_version_id": SOURCE_RENDER_VERSION_ID,
        "main_render_version_id": main_render_version_id,
        "source_workfile_version_id": SOURCE_WORKFILE_VERSION_ID,
        "main_workfile_version_id": main_workfile_version_id,
        "source_render_fingerprint": "1" * 64,
        "main_render_authority_fingerprint": "2" * 64,
        "source_workfile_fingerprint": "3" * 64,
        "main_workfile_fingerprint": "4" * 64,
    }
    return {
        "kind": "pipeline.workfile.promoted_lineage_plan",
        "schema_version": 1,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        **authority,
        "authority_fingerprint": _fingerprint(authority),
        "idempotent_replay": False,
    }


def _lineage_manifest(
    *,
    main_render_version_id: str,
    main_workfile_version_id: str,
    params: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    plan = _lineage_plan(
        main_render_version_id=main_render_version_id,
        main_workfile_version_id=main_workfile_version_id,
    )
    identity = {
        "operation_type": LINEAGE_CALLABLE_OPERATION_TYPE,
        **{
            key: plan[key]
            for key in (
                "project_id",
                "owner_id",
                "source_render_version_id",
                "main_render_version_id",
                "source_workfile_version_id",
                "main_workfile_version_id",
                "authority_fingerprint",
            )
        },
    }
    return {
        "kind": "pipeline.workfile.promoted_lineage_callable_result",
        "schema_version": 1,
        "operation_type": LINEAGE_CALLABLE_OPERATION_TYPE,
        "ok": True,
        "status": "succeeded",
        "trust_status": "trusted",
        "mode": "discover",
        "mutation_safe": True,
        "plan_source": "compiled",
        "lineage_plan": plan,
        "idempotency_key": idempotency_key,
        "bridge_asset_ids": sorted(
            {value for value in params.values() if isinstance(value, str)}
        ),
        "type": "mutation_plan",
        "intent_parameters": {
            "params": dict(params),
            "idempotency_key": idempotency_key,
            "bridge_asset_ids": sorted(
                {value for value in params.values() if isinstance(value, str)}
            ),
            "project_id": PROJECT_ID,
            "requested_by": ACTOR,
        },
        "resolved_plan": [
            {"identity": identity, "payload": {"lineage_plan": plan}}
        ],
        "originating_capability": LINEAGE_BIND_TOOL,
        "apply_counterpart": {
            "tool": LINEAGE_BIND_TOOL,
            "parameter_overrides": {},
        },
    }


# --------------------------------------------------------------------------- #
# Fake MCP + fake operation runner shaped like the released Pipeline callables
# --------------------------------------------------------------------------- #
class FakeMCP:
    """Discover/verify/apply for the four admitted paired-promotion tools."""

    def __init__(
        self,
        *,
        fresh_copy: dict[str, Any] | None = None,
        fresh_workfile: dict[str, Any] | None = None,
        resource_apply: str = "registered",
        workfile_apply: str = "promoted",
        lineage_apply: str = "bound",
        lineage_discovery: str = "exact",
        discovery_raises: str = "",
    ) -> None:
        self.copy = _copy_manifest()
        self.workfile = _workfile_manifest()
        self.fresh_copy = fresh_copy
        self.fresh_workfile = fresh_workfile
        self.resource_apply = resource_apply
        self.workfile_apply = workfile_apply
        self.lineage_apply = lineage_apply
        self.lineage_discovery = lineage_discovery
        self.discovery_raises = discovery_raises
        self.calls: list[tuple[str, str]] = []
        self.apply_counts = {
            PROMOTE_TOOL: 0,
            RESOURCE_REGISTER_TOOL: 0,
            WORKFILE_PROMOTE_TOOL: 0,
            LINEAGE_BIND_TOOL: 0,
        }
        self.held_resource_manifest = _resource_registration_manifest()
        self.held_lineage_manifest: dict[str, Any] | None = None

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
                WORKFILE_PROMOTE_TOOL,
                LINEAGE_BIND_TOOL,
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        mode = str(arguments.get("mode") or "discover")
        self.calls.append((name, mode))
        if name == PROMOTE_TOOL:
            return self._promote(mode)
        if name == RESOURCE_REGISTER_TOOL:
            return self._register(mode)
        if name == WORKFILE_PROMOTE_TOOL:
            return self._workfile(mode)
        if name == LINEAGE_BIND_TOOL:
            return self._lineage(mode, arguments)
        raise AssertionError(name)

    # -- forge_promote_shot_resource_stream ------------------------------- #
    def _promote(self, mode: str):
        if mode == "discover":
            if self.discovery_raises == PROMOTE_TOOL:
                raise ConnectionError("/private/socket unreachable")
            return copy.deepcopy(self.copy)
        if mode == "verify":
            return copy.deepcopy(self.fresh_copy or self.copy)
        self.apply_counts[PROMOTE_TOOL] += 1
        return {
            "ok": True,
            "status": "succeeded",
            "trust_status": "trusted",
            "promotion_apply": _promotion_result(),
            "catalog_registration_status": "pending",
        }

    # -- forge_register_shot_resource_promotion --------------------------- #
    def _register(self, mode: str):
        if mode == "verify":
            return copy.deepcopy(self.held_resource_manifest)
        self.apply_counts[RESOURCE_REGISTER_TOOL] += 1
        if self.resource_apply == "registered":
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "catalog_registration_status": "registered",
                "registered_count": 2,
                "created_asset_ids": list(PROMOTED_IDS),
                "publish_register": {
                    "kind": "pipeline.shot_resource.publish_register_result",
                    "status": "registered",
                    "registered_count": 2,
                    "version_asset_ids": [MAIN_RENDER_VERSION_ID],
                    "media_asset_ids": [MAIN_RENDER_MEDIA_ID],
                },
            }
        if self.resource_apply == "ambiguous":
            # Two registered Versions: the lineage node could not be told which
            # main render to bind, so the pair fails closed.
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "catalog_registration_status": "registered",
                "registered_count": 4,
                "created_asset_ids": [*PROMOTED_IDS, "extra-version-1"],
                "publish_register": {
                    "status": "registered",
                    "registered_count": 4,
                    "version_asset_ids": [
                        MAIN_RENDER_VERSION_ID,
                        "extra-version-1",
                    ],
                    "media_asset_ids": [MAIN_RENDER_MEDIA_ID],
                },
            }
        return {
            "ok": True,
            "status": "succeeded",
            "trust_status": "trusted",
            "catalog_registration_status": "partial",
            "created_asset_ids": [],
            "publish_register": {
                "status": "partial_failed",
                "registered_count": 0,
                "version_asset_ids": [],
                "media_asset_ids": [],
            },
        }

    # -- forge_promote_workfile_version ----------------------------------- #
    def _workfile(self, mode: str):
        if mode == "discover":
            if self.discovery_raises == WORKFILE_PROMOTE_TOOL:
                raise ConnectionError("/private/socket unreachable")
            return copy.deepcopy(self.workfile)
        if mode == "verify":
            return copy.deepcopy(self.fresh_workfile or self.workfile)
        self.apply_counts[WORKFILE_PROMOTE_TOOL] += 1
        plan = _workfile_plan()
        if self.workfile_apply == "promoted":
            promotion_apply = {
                "status": "promoted",
                "method": "copy_workfile_stream_version",
                "source_version_id": SOURCE_WORKFILE_VERSION_ID,
                "source_version_number": 3,
                "source_stream": ARTIST_STREAM,
                "target_version_id": MAIN_WORKFILE_VERSION_ID,
                "target_version_number": plan["target_version_number"],
                "media_id": MAIN_WORKFILE_MEDIA_ID,
                "target_stream": "main",
                "path": plan["source_tokenized_path"],
                "trust_status": "trusted",
                "idempotent_replay": False,
                "copy_proof": {
                    "package_kind": "flame_batch_setup",
                    "sidecar_present": True,
                    "package_manifest_match": True,
                },
                "workfile_identity": plan["source_workfile_identity"],
            }
            return {
                "kind": "pipeline.workfile.stream_promotion_callable_result",
                "operation_type": WORKFILE_CALLABLE_OPERATION_TYPE,
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "mutation_safe": False,
                "plan_source": "held_verified",
                "promotion_plan": plan,
                "promotion_apply": promotion_apply,
                "idempotent_replay": False,
                "target_version_id": MAIN_WORKFILE_VERSION_ID,
                "target_version_number": plan["target_version_number"],
            }
        # Copy landed but the catalog never registered the Version:
        # ``WorkfileOp.promote_stream`` returns catalog=unavailable, so the
        # callable reports a reconciliation-required apply failure.
        return {
            "kind": "pipeline.workfile.stream_promotion_callable_result",
            "operation_type": WORKFILE_CALLABLE_OPERATION_TYPE,
            "ok": False,
            "status": "failed",
            "trust_status": "review_required",
            "mode": "apply",
            "mutation_safe": False,
            "reconciliation_required": True,
            "stage": "apply",
            "error": "Workfile promotion did not commit.",
            "promotion_apply": {
                "status": "promoted",
                "catalog": "unavailable",
                "warning": "RuntimeError: /private catalog unavailable",
            },
        }

    # -- forge_bind_promoted_workfile_lineage ----------------------------- #
    def _lineage(self, mode: str, arguments: dict[str, Any]):
        if mode == "discover":
            if self.discovery_raises == LINEAGE_BIND_TOOL:
                raise ConnectionError("/private/socket unreachable")
            params = dict(arguments.get("params") or {})
            main_render = params.get("main_render_version_id")
            main_workfile = params.get("main_workfile_version_id")
            if self.lineage_discovery == "wrong_render":
                # The callable answered about a DIFFERENT promoted render.
                main_render = "some-other-main-render"
            elif self.lineage_discovery == "wrong_workfile":
                main_workfile = "some-other-main-workfile"
            self.held_lineage_manifest = _lineage_manifest(
                main_render_version_id=main_render,
                main_workfile_version_id=main_workfile,
                params=params,
                idempotency_key=str(arguments.get("idempotency_key") or ""),
            )
            return copy.deepcopy(self.held_lineage_manifest)
        if mode == "verify":
            return copy.deepcopy(self.held_lineage_manifest)
        self.apply_counts[LINEAGE_BIND_TOOL] += 1
        if self.lineage_apply == "bound":
            return {
                "kind": "pipeline.workfile.promoted_lineage_callable_result",
                "operation_type": LINEAGE_CALLABLE_OPERATION_TYPE,
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "mutation_safe": False,
                "plan_source": "held_verified",
                "lineage_apply": {
                    "ok": True,
                    "status": "bound",
                    "trust_status": "trusted",
                    "idempotent_replay": False,
                    "main_render_version_id": MAIN_RENDER_VERSION_ID,
                    "main_workfile_version_id": MAIN_WORKFILE_VERSION_ID,
                    "source_render_version_id": SOURCE_RENDER_VERSION_ID,
                    "source_workfile_version_id": SOURCE_WORKFILE_VERSION_ID,
                    "relationship_id": LINEAGE_RELATIONSHIP_ID,
                    "updated_asset_id": MAIN_RENDER_VERSION_ID,
                },
                "idempotent_replay": False,
            }
        # Edge created, metadata never landed — partial binding refuses as
        # reconciliation-required rather than silently normalizing.
        return {
            "kind": "pipeline.workfile.promoted_lineage_callable_result",
            "operation_type": LINEAGE_CALLABLE_OPERATION_TYPE,
            "ok": False,
            "status": "failed",
            "trust_status": "review_required",
            "mode": "apply",
            "mutation_safe": False,
            "reconciliation_required": True,
            "stage": "apply",
            "error": "promoted render/workfile lineage is partially bound",
            "lineage_apply": {
                "ok": False,
                "status": "failed",
                "trust_status": "review_required",
                "mutation_started": True,
            },
        }


class FakeOperations:
    """The two Pipeline operations, as the operation runner sees them."""

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
        raise AssertionError(operation_type)


def build_api(**mcp_kwargs: Any):
    mcp = FakeMCP(**mcp_kwargs)
    operations = FakeOperations(mcp=mcp)
    gateway = InMemoryAssentGateway()
    store = InMemoryPairedPromotionWorkflowStore()
    api = make_paired_promotion_workflow_api(
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
    proposed = await _propose(api)
    applied = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )
    return api, mcp, operations, gateway, store, proposed, applied


ALL_ZERO = {
    PROMOTE_TOOL: 0,
    RESOURCE_REGISTER_TOOL: 0,
    WORKFILE_PROMOTE_TOOL: 0,
    LINEAGE_BIND_TOOL: 0,
}
ALL_ONCE = {tool: 1 for tool in ALL_ZERO}


# --------------------------------------------------------------------------- #
# 1 — unknown/missing fields and every fingerprint drift fail before MCP
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_1_unknown_missing_and_drifted_fields_fail_before_mcp():
    api, mcp, operations, _gateway, _store = build_api()

    async def refused(proposal: dict[str, Any]) -> str:
        with pytest.raises(PairedPromotionWorkflowError) as exc:
            await api.propose(proposal)
        return exc.value.code

    unknown = make_proposal()
    unknown["journal_path"] = "/private/journal.json"
    assert await refused(unknown) == "paired_promotion_workflow_proposal_invalid"

    missing = make_proposal()
    missing.pop("source_workfile_version_id")
    assert await refused(missing) == "paired_promotion_workflow_proposal_invalid"

    tampered = make_proposal()
    tampered["source_workfile_version_id"] = WORKFILE_V002
    assert await refused(tampered) == "paired_promotion_workflow_proposal_invalid"

    for field in (
        "promotion_plan_fingerprint",
        "promotion_callable_intent_fingerprint",
        "workfile_callable_intent_fingerprint",
    ):
        drifted = make_proposal()
        drifted[field] = "d" * 64
        body = {
            key: value
            for key, value in drifted.items()
            if key not in {"kind", "schema_version", "fingerprint"}
        }
        drifted["fingerprint"] = _fingerprint(body)
        assert await refused(drifted) == (
            "paired_promotion_workflow_proposal_invalid"
        )

    unsorted = make_proposal(
        published_resource_asset_ids=list(reversed(sorted(PUBLISHED_IDS)))
    )
    assert await refused(unsorted) == "paired_promotion_workflow_proposal_invalid"

    # The retained workfile intent must name the SELECTED Batch Version, not an
    # older or newer one in the same artist stream.
    widened = make_proposal(
        workfile_callable_intent=make_workfile_intent(
            params={
                **make_workfile_intent()["params"],
                "source_version_id": WORKFILE_V001,
            }
        )
    )
    assert await refused(widened) == "paired_promotion_workflow_proposal_invalid"

    not_main = make_proposal(
        workfile_callable_intent=make_workfile_intent(
            params={
                **make_workfile_intent()["params"],
                "target_stream": "review",
            }
        )
    )
    assert await refused(not_main) == "paired_promotion_workflow_proposal_invalid"

    assert mcp.calls == []
    assert operations.calls == []


# --------------------------------------------------------------------------- #
# 2 / 3 — duplicate propose; same authority under a new proposal
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_2_exact_duplicate_propose_returns_the_original_proposal():
    api, mcp, _operations, gateway, _store = build_api()
    first = await _propose(api)
    calls = list(mcp.calls)

    second = await _propose(api)

    assert second == first
    assert mcp.calls == calls
    assert len(gateway._records) == 1


@pytest.mark.asyncio
async def test_3_same_authority_under_a_different_proposal_fails_closed():
    api, _mcp, _operations, _gateway, _store = build_api()
    await _propose(api)

    with pytest.raises(PairedPromotionWorkflowError) as exc:
        await api.propose(make_proposal(promotion_preview_id="paired-preview-2"))
    assert exc.value.code == "paired_promotion_workflow_proposal_invalid"


# --------------------------------------------------------------------------- #
# 4 — propose discovers BOTH physical promotions only, and mutates nothing
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_4_propose_is_mutation_free_and_retains_both_artist_versions():
    api, mcp, operations, gateway, store = build_api()

    receipt = await _propose(api)

    assert receipt["status"] == "proposed"
    assert receipt["action"] == "propose"
    assert receipt["trust_status"] == "trusted"
    assert receipt["dispatch_authorized"] is False
    assert receipt["applied"] is False
    assert receipt["main_advanced"] is False
    # Both selected artist identities are retained verbatim.
    assert receipt["source_render_version_id"] == SOURCE_RENDER_VERSION_ID
    assert receipt["source_render_media_id"] == SOURCE_RENDER_MEDIA_ID
    assert receipt["source_workfile_version_id"] == SOURCE_WORKFILE_VERSION_ID
    # Discovery only: no verify, no apply, nowhere.
    assert mcp.calls == [
        (PROMOTE_TOOL, "discover"),
        (WORKFILE_PROMOTE_TOOL, "discover"),
    ]
    assert mcp.apply_counts == ALL_ZERO
    assert operations.calls == []
    # Two held manifests exist and are fingerprinted; the other two do not.
    assert receipt["resource_copy_manifest_fingerprint"] is not None
    assert receipt["workfile_promotion_manifest_fingerprint"] is not None
    assert receipt["resource_registration_manifest_fingerprint"] is None
    assert receipt["lineage_binding_manifest_fingerprint"] is None
    assert receipt["resource_copy_manifest_fingerprint"] != (
        receipt["workfile_promotion_manifest_fingerprint"]
    )
    # Exactly ONE AssentRecord, still proposed.
    assert len(gateway._records) == 1
    assert gateway.ratify_calls == []
    row = await store.get_by_proposal_id(receipt["proposal_id"])
    assert row["assent_status"] == "proposed"
    assert row["workfile_promotion_held_manifest"]["type"] == "mutation_plan"


# --------------------------------------------------------------------------- #
# 5 — non-ratified apply is refused BEFORE any dispatch
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_5_unratified_apply_refuses_before_dispatch():
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
    assert receipt["reason_code"] == "paired_promotion_workflow_assent_invalid"
    assert receipt["dispatch_authorized"] is False
    assert mcp.apply_counts == ALL_ZERO
    assert [call for call in mcp.calls if call[1] in {"verify", "apply"}] == []


# --------------------------------------------------------------------------- #
# 6 / 7 — the exact nine-node graph; four commits under ONE assent
# --------------------------------------------------------------------------- #
def test_6_bridge_composes_the_exact_nine_node_graph():
    sequence = paired_promotion_operator_sequence(
        make_proposal(),
        main_render_version_id=MAIN_RENDER_VERSION_ID,
        main_workfile_version_id=MAIN_WORKFILE_VERSION_ID,
    )

    assert [step["operator_id"] for step in sequence] == [
        PROMOTE_TOOL,
        "commit",
        VALIDATE_OPERATION,
        RESOURCE_PLAN_OPERATION,
        "commit",
        WORKFILE_PROMOTE_TOOL,
        "commit",
        LINEAGE_BIND_TOOL,
        "commit",
    ]
    # Both discovery nodes carry their retained callable intent, unwidened.
    assert sequence[0]["arguments"]["mode"] == "discover"
    assert sequence[0]["arguments"]["params"] == (
        make_promotion_intent()["params"]
    )
    assert sequence[5]["arguments"]["mode"] == "discover"
    assert sequence[5]["arguments"]["params"] == make_workfile_intent()["params"]
    # The lineage node receives the EXACT committed identities.
    assert sequence[7]["arguments"]["params"] == {
        "source_render_version_id": SOURCE_RENDER_VERSION_ID,
        "main_render_version_id": MAIN_RENDER_VERSION_ID,
        "source_workfile_version_id": SOURCE_WORKFILE_VERSION_ID,
        "main_workfile_version_id": MAIN_WORKFILE_VERSION_ID,
    }
    assert sequence[7]["arguments"]["idempotency_key"].endswith(
        ":promoted-workfile-lineage"
    )


@pytest.mark.asyncio
async def test_7_each_stage_dispatches_once_in_order_under_one_assent():
    _api, mcp, operations, gateway, _store, _proposed, applied = (
        await _full_apply()
    )

    assert applied["status"] == "applied"
    assert mcp.calls == [
        (PROMOTE_TOOL, "discover"),
        (WORKFILE_PROMOTE_TOOL, "discover"),
        (PROMOTE_TOOL, "verify"),
        (PROMOTE_TOOL, "apply"),
        (RESOURCE_REGISTER_TOOL, "verify"),
        (RESOURCE_REGISTER_TOOL, "apply"),
        (WORKFILE_PROMOTE_TOOL, "verify"),
        (WORKFILE_PROMOTE_TOOL, "apply"),
        (LINEAGE_BIND_TOOL, "discover"),
        (LINEAGE_BIND_TOOL, "verify"),
        (LINEAGE_BIND_TOOL, "apply"),
    ]
    assert mcp.apply_counts == ALL_ONCE
    assert [name for name, _params in operations.calls] == [
        VALIDATE_OPERATION,
        RESOURCE_PLAN_OPERATION,
    ]
    # ONE AssentRecord governed all four commits; ratify was called once.
    assert len(gateway._records) == 1
    assert len(gateway.ratify_calls) == 1


# --------------------------------------------------------------------------- #
# 8 — the applied receipt carries eight fingerprints and every identity
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_8_applied_receipt_carries_all_evidence():
    *_rest, applied = await _full_apply()

    assert applied["status"] == "applied"
    assert applied["trust_status"] == "trusted"
    assert applied["applied"] is True
    assert applied["main_advanced"] is True
    assert applied["reconciliation_required"] is False
    assert applied["dispatch_authorized"] is True
    assert applied["resource_copy_status"] == "applied"
    assert applied["resource_registration_status"] == "registered"
    assert applied["workfile_promotion_status"] == "promoted"
    assert applied["lineage_binding_status"] == "bound"
    assert applied["promoted_resource_asset_ids"] == sorted(PROMOTED_IDS)
    assert applied["main_render_version_id"] == MAIN_RENDER_VERSION_ID
    assert applied["main_render_media_id"] == MAIN_RENDER_MEDIA_ID
    assert applied["main_workfile_version_id"] == MAIN_WORKFILE_VERSION_ID
    assert applied["main_workfile_media_id"] == MAIN_WORKFILE_MEDIA_ID
    assert applied["lineage_relationship_id"] == LINEAGE_RELATIONSHIP_ID
    fingerprints = [
        applied[field]
        for field in (
            "resource_copy_manifest_fingerprint",
            "resource_copy_commit_fingerprint",
            "resource_registration_manifest_fingerprint",
            "resource_registration_commit_fingerprint",
            "workfile_promotion_manifest_fingerprint",
            "workfile_promotion_commit_fingerprint",
            "lineage_binding_manifest_fingerprint",
            "lineage_binding_commit_fingerprint",
        )
    ]
    assert all(isinstance(item, str) and len(item) == 64 for item in fingerprints)
    # Eight DISTINCT fingerprints — no stage reuses another's evidence.
    assert len(set(fingerprints)) == 8


# --------------------------------------------------------------------------- #
# 9 — tampered source/target/plan fingerprints fail closed BEFORE dispatch
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_9a_proposal_fingerprint_drift_refuses_before_dispatch():
    api, mcp, _operations, _gateway, _store = build_api()
    proposed = await _propose(api)

    drifted = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint="e" * 64,
        requested_by=ACTOR,
    )

    assert drifted["status"] == "failed"
    assert drifted["reason_code"] == "paired_promotion_workflow_proposal_changed"
    assert drifted["dispatch_authorized"] is False
    assert mcp.apply_counts == ALL_ZERO


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field",
    ["resource_copy_held_manifest", "workfile_promotion_held_manifest"],
)
async def test_9b_tampered_held_manifest_refuses_before_dispatch(field):
    api, mcp, _operations, _gateway, store = build_api()
    proposed = await _propose(api)

    tampered = dict(await store.get_by_proposal_id(proposed["proposal_id"]))
    body = copy.deepcopy(tampered[field])
    body["resolved_plan"][0]["identity"]["operation_type"] = "tampered"
    await store.update(proposed["proposal_id"], {field: body})

    receipt = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == "paired_promotion_workflow_manifest_drift"
    assert receipt["dispatch_authorized"] is False
    assert mcp.apply_counts == ALL_ZERO
    assert [call for call in mcp.calls if call[1] in {"verify", "apply"}] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["wrong_render", "wrong_workfile"])
async def test_9c_lineage_plan_that_is_not_the_committed_pair_never_dispatches(
    variant,
):
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(lineage_discovery=variant)
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_manifest_invalid"
    )
    assert receipt["reconciliation_required"] is True
    assert receipt["lineage_binding_status"] == "not_started"
    assert receipt["lineage_relationship_id"] is None
    # The lineage plan was refused BEFORE the commit boundary dispatched.
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 0
    assert (LINEAGE_BIND_TOOL, "verify") not in mcp.calls
    # The three earlier stages stay honestly complete.
    assert receipt["resource_copy_status"] == "applied"
    assert receipt["resource_registration_status"] == "registered"
    assert receipt["workfile_promotion_status"] == "promoted"


@pytest.mark.asyncio
async def test_9d_stale_workfile_plan_refuses_at_verify_without_applying():
    """A next-main allocation that moved under Bridge fails at verify time."""
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(
            fresh_workfile=_workfile_manifest(target_version_number=9)
        )
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_workfile_promotion_failed"
    )
    assert receipt["workfile_promotion_status"] == "not_started"
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 0
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 0
    # The render side had already committed, so this is reconciliation, not a
    # clean failure.
    assert receipt["reconciliation_required"] is True


@pytest.mark.asyncio
async def test_9e_stale_render_plan_refuses_before_anything_dispatches():
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(fresh_copy=_copy_manifest(target_version="v003"))
    )

    assert receipt["status"] == "failed"
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_resource_copy_failed"
    )
    assert receipt["dispatch_authorized"] is False
    assert receipt["reconciliation_required"] is False
    assert mcp.apply_counts == ALL_ZERO


# --------------------------------------------------------------------------- #
# 10 — every partial-failure variant reports honest stage statuses
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_10a_resource_registration_interruption_is_partial():
    _api, mcp, _operations, gateway, _store, _proposed, receipt = (
        await _full_apply(resource_apply="partial")
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["resource_copy_status"] == "applied"
    assert receipt["resource_registration_status"] == "failed"
    assert receipt["workfile_promotion_status"] == "not_started"
    assert receipt["lineage_binding_status"] == "not_started"
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_resource_registration_failed"
    )
    # Neither the workfile promotion nor the lineage bind ran on incomplete
    # render evidence.
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 0
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 0
    # The assent stays RATIFIED so replay can forward-complete under it.
    record = next(iter(gateway._records.values()))
    assert record.status == "ratified"


@pytest.mark.asyncio
async def test_10b_ambiguous_registration_refuses_to_guess_the_main_render():
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(resource_apply="ambiguous")
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["resource_registration_status"] == "failed"
    assert receipt["main_render_version_id"] is None
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 0
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 0


@pytest.mark.asyncio
async def test_10c_workfile_catalog_interruption_is_partial():
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(workfile_apply="catalog_unavailable")
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["resource_copy_status"] == "applied"
    assert receipt["resource_registration_status"] == "registered"
    assert receipt["workfile_promotion_status"] == "failed"
    assert receipt["lineage_binding_status"] == "not_started"
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_workfile_promotion_failed"
    )
    assert receipt["main_workfile_version_id"] is None
    assert receipt["reconciliation_required"] is True
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 1
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 0


@pytest.mark.asyncio
async def test_10d_partial_lineage_binding_is_reconciliation_required():
    _api, mcp, _operations, _gateway, _store, _proposed, receipt = (
        await _full_apply(lineage_apply="partial")
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["lineage_binding_status"] == "failed"
    assert receipt["lineage_relationship_id"] is None
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_lineage_binding_failed"
    )
    assert receipt["applied"] is False
    assert receipt["main_advanced"] is False
    assert receipt["reconciliation_required"] is True
    # The three earlier stages advanced exactly once each.
    assert mcp.apply_counts == ALL_ONCE
    assert receipt["main_render_version_id"] == MAIN_RENDER_VERSION_ID
    assert receipt["main_workfile_version_id"] == MAIN_WORKFILE_VERSION_ID


@pytest.mark.asyncio
async def test_10e_a_partial_cannot_be_ratified_a_second_time():
    api, mcp, _operations, gateway, _store, proposed, partial = (
        await _full_apply(lineage_apply="partial")
    )
    assert partial["status"] == "partial_failed"
    before = dict(mcp.apply_counts)

    again = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert again["status"] == "partial_failed"
    assert again["reason_code"] == (
        "paired_promotion_workflow_partial_reconciliation_required"
    )
    assert mcp.apply_counts == before
    assert len(gateway.ratify_calls) == 1


# --------------------------------------------------------------------------- #
# 11 — interruption after EACH commit boundary resumes without duplication
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_11a_resume_after_the_resource_copy_commit():
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
    assert replayed["replayed"] is True
    # The physical copy is NEVER re-run.
    assert PROMOTE_TOOL not in {name for name, _mode in mcp.calls}
    assert mcp.apply_counts[PROMOTE_TOOL] == 1
    assert mcp.apply_counts[RESOURCE_REGISTER_TOOL] == 2
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 1
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 1
    # The resumed validate consumed the PERSISTED copy-commit projection.
    assert operations.calls[0][1]["promotion_commit"]["type"] == "commit_applied"
    assert len(gateway.ratify_calls) == 1


@pytest.mark.asyncio
async def test_11b_resume_after_the_resource_registration_commit():
    api, mcp, operations, gateway, _store, proposed, partial = (
        await _full_apply(workfile_apply="catalog_unavailable")
    )
    assert partial["workfile_promotion_status"] == "failed"
    registered_ids = partial["promoted_resource_asset_ids"]

    mcp.workfile_apply = "promoted"
    mcp.calls.clear()
    operations.calls.clear()
    replayed = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert replayed["status"] == "applied"
    # No duplicate copy and no duplicate registration.
    assert mcp.apply_counts[PROMOTE_TOOL] == 1
    assert mcp.apply_counts[RESOURCE_REGISTER_TOOL] == 1
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 2
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 1
    assert operations.calls == []
    assert mcp.calls == [
        (WORKFILE_PROMOTE_TOOL, "verify"),
        (WORKFILE_PROMOTE_TOOL, "apply"),
        (LINEAGE_BIND_TOOL, "discover"),
        (LINEAGE_BIND_TOOL, "verify"),
        (LINEAGE_BIND_TOOL, "apply"),
    ]
    # The registered identities are frozen, never re-derived.
    assert replayed["promoted_resource_asset_ids"] == registered_ids
    assert replayed["resource_registration_commit_fingerprint"] == (
        partial["resource_registration_commit_fingerprint"]
    )
    assert len(gateway.ratify_calls) == 1


@pytest.mark.asyncio
async def test_11c_resume_after_the_workfile_promotion_commit():
    api, mcp, operations, gateway, _store, proposed, partial = (
        await _full_apply(lineage_apply="partial")
    )
    assert partial["lineage_binding_status"] == "failed"

    mcp.lineage_apply = "bound"
    mcp.calls.clear()
    operations.calls.clear()
    replayed = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert replayed["status"] == "applied"
    assert replayed["lineage_relationship_id"] == LINEAGE_RELATIONSHIP_ID
    # NO duplicate copy, registration, or workfile allocation.
    assert mcp.apply_counts[PROMOTE_TOOL] == 1
    assert mcp.apply_counts[RESOURCE_REGISTER_TOOL] == 1
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 1
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 2
    assert mcp.calls == [
        (LINEAGE_BIND_TOOL, "discover"),
        (LINEAGE_BIND_TOOL, "verify"),
        (LINEAGE_BIND_TOOL, "apply"),
    ]
    assert operations.calls == []
    # Replay never widened authority and never minted a second assent.
    assert replayed["proposal_fingerprint"] == partial["proposal_fingerprint"]
    assert replayed["assent_record_id"] == partial["assent_record_id"]
    assert replayed["main_render_version_id"] == (
        partial["main_render_version_id"]
    )
    assert replayed["main_workfile_version_id"] == (
        partial["main_workfile_version_id"]
    )
    assert len(gateway._records) == 1
    assert len(gateway.ratify_calls) == 1


@pytest.mark.asyncio
async def test_11d_resume_after_the_lineage_commit_is_a_no_op():
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
    assert mcp.apply_counts == before == ALL_ONCE
    assert mcp.calls == []
    assert operations.calls == []
    assert len(gateway.ratify_calls) == 1


@pytest.mark.asyncio
async def test_11e_replay_before_ratification_is_unavailable():
    api, mcp, _operations, gateway, _store = build_api()
    proposed = await _propose(api)

    receipt = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert receipt["status"] == "unavailable"
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_replay_unavailable"
    )
    assert mcp.apply_counts == ALL_ZERO
    assert gateway.ratify_calls == []


# --------------------------------------------------------------------------- #
# 12 — status is a durable, non-mutating read that preserves identities
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_12a_status_is_a_durable_non_mutating_read():
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
    assert mcp.apply_counts == ALL_ZERO

    with pytest.raises(PairedPromotionWorkflowError) as exc:
        await api.status(
            proposal_id="ppr_missing", expected_proposal_fingerprint="f" * 64
        )
    assert exc.value.code == "paired_promotion_workflow_proposal_not_found"


@pytest.mark.asyncio
async def test_12b_status_preserves_fingerprints_and_target_versions():
    api, mcp, _operations, _gateway, _store, proposed, applied = (
        await _full_apply()
    )
    mcp.calls.clear()

    polled = await api.status(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )

    assert mcp.calls == []
    assert polled["status"] == "applied"
    for field in (
        "proposal_fingerprint",
        "promotion_preview_fingerprint",
        "promotion_authority_fingerprint",
        "assent_record_id",
        "source_render_version_id",
        "source_workfile_version_id",
        "main_render_version_id",
        "main_render_media_id",
        "main_workfile_version_id",
        "lineage_relationship_id",
        "resource_copy_manifest_fingerprint",
        "resource_copy_commit_fingerprint",
        "resource_registration_commit_fingerprint",
        "workfile_promotion_manifest_fingerprint",
        "workfile_promotion_commit_fingerprint",
        "lineage_binding_commit_fingerprint",
    ):
        assert polled[field] == applied[field], field
    assert polled["proposal_fingerprint"] == proposed["proposal_fingerprint"]


# --------------------------------------------------------------------------- #
# 13 — restart preserves proposal, graph, assent, stage state, and replay
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_13_restart_preserves_the_whole_durable_workflow():
    api, mcp, operations, gateway, store, proposed, partial = (
        await _full_apply(lineage_apply="partial")
    )
    assert partial["status"] == "partial_failed"

    # A "restart": a brand new API object over the SAME durable store and the
    # same assent gateway. Nothing is carried in process memory.
    restarted = make_paired_promotion_workflow_api(
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
        WORKFILE_PROMOTE_TOOL,
        "commit",
        LINEAGE_BIND_TOOL,
        "commit",
    ]
    assert row["assent_status"] == "ratified"
    assert row["resource_copy_status"] == "applied"
    assert row["workfile_promotion_status"] == "promoted"
    assert row["lineage_binding_status"] == "failed"
    assert row["main_workfile_version_id"] == MAIN_WORKFILE_VERSION_ID
    assert row["workfile_promotion_held_manifest"]["type"] == "mutation_plan"

    mcp.lineage_apply = "bound"
    replayed = await restarted.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )
    assert replayed["status"] == "applied"
    assert replayed["replayed"] is True


# --------------------------------------------------------------------------- #
# 14 — concurrent transition attempts do not double-apply
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_14a_concurrent_ratify_apply_does_not_double_apply():
    api, mcp, _operations, gateway, _store = build_api()
    proposed = await _propose(api)

    receipts = await asyncio.gather(
        *[
            api.ratify_apply(
                proposal_id=proposed["proposal_id"],
                expected_proposal_fingerprint=proposed["proposal_fingerprint"],
                requested_by=ACTOR,
            )
            for _ in range(4)
        ]
    )

    assert mcp.apply_counts == ALL_ONCE
    assert len(gateway.ratify_calls) == 1
    assert {item["status"] for item in receipts} == {"applied"}


@pytest.mark.asyncio
async def test_14b_concurrent_replay_over_a_partial_does_not_double_bind():
    api, mcp, _operations, gateway, _store, proposed, _partial = (
        await _full_apply(lineage_apply="partial")
    )
    mcp.lineage_apply = "bound"

    receipts = await asyncio.gather(
        *[
            api.replay(
                proposal_id=proposed["proposal_id"],
                expected_proposal_fingerprint=proposed["proposal_fingerprint"],
                requested_by=ACTOR,
            )
            for _ in range(3)
        ]
    )

    # Exactly one additional lineage bind: 1 partial + 1 completing apply.
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 2
    assert mcp.apply_counts[PROMOTE_TOOL] == 1
    assert mcp.apply_counts[RESOURCE_REGISTER_TOOL] == 1
    assert mcp.apply_counts[WORKFILE_PROMOTE_TOOL] == 1
    assert {item["status"] for item in receipts} == {"applied"}
    assert len(gateway.ratify_calls) == 1


# --------------------------------------------------------------------------- #
# 15 — closed field set, valid fingerprint, no private bodies
# --------------------------------------------------------------------------- #
_RECEIPT_FIELDS = {
    "kind", "schema_version", "action", "status", "trust_status",
    "workflow_id", "proposal_id", "proposal_fingerprint",
    "promotion_preview_id", "promotion_preview_fingerprint",
    "promotion_authority_fingerprint", "source_render_version_id",
    "source_render_media_id", "source_workfile_version_id", "selected_roles",
    "published_resource_asset_ids", "promoted_resource_asset_ids",
    "main_render_version_id", "main_render_media_id",
    "main_workfile_version_id", "main_workfile_media_id",
    "lineage_relationship_id", "assent_record_id", "assent_status",
    "resource_copy_manifest_fingerprint", "resource_copy_commit_fingerprint",
    "resource_copy_status", "resource_registration_manifest_fingerprint",
    "resource_registration_commit_fingerprint",
    "resource_registration_status", "workfile_promotion_manifest_fingerprint",
    "workfile_promotion_commit_fingerprint", "workfile_promotion_status",
    "lineage_binding_manifest_fingerprint",
    "lineage_binding_commit_fingerprint", "lineage_binding_status",
    "dispatch_authorized", "applied", "replayed", "main_advanced",
    "reconciliation_required", "reason_code", "fingerprint",
}
_PRIVATE_MARKERS = (
    "/private/",
    ".batch",
    "promotion_plan",
    "lineage_plan",
    "callable_intent",
    "resolved_plan",
    "intent_parameters",
    "apply_result",
    "registration_plan",
    "target_path",
    "source_path",
    "copy_proof",
    "config_path",
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
async def test_15a_every_receipt_is_closed_and_self_verifying():
    for receipt, label in await _lifecycle_receipts():
        _assert_closed_and_path_free(receipt, label)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool", [PROMOTE_TOOL, WORKFILE_PROMOTE_TOOL]
)
async def test_15b_errors_never_leak_private_bodies(tool):
    api, _mcp, _operations, _gateway, _store = build_api(discovery_raises=tool)
    with pytest.raises(PairedPromotionWorkflowError) as exc:
        await _propose(api)
    assert exc.value.code == (
        "paired_promotion_workflow_callable_unavailable"
    )
    assert "/private/" not in str(exc.value)
    assert "/" not in str(exc.value)


@pytest.mark.asyncio
async def test_15c_a_manifest_that_is_not_this_proposal_refuses_path_free():
    # The retained workfile intent drifts from the discovered manifest: the
    # refusal quotes field names, never the absolute paths in either body.
    api, _mcp, _operations, _gateway, _store = build_api()
    bad = make_proposal(
        workfile_callable_intent=make_workfile_intent(
            params={
                **make_workfile_intent()["params"],
                "canonical": "/private/other_project",
            }
        )
    )
    with pytest.raises(PairedPromotionWorkflowError) as exc:
        await api.propose(bad)
    assert exc.value.code == "paired_promotion_workflow_manifest_invalid"
    assert "/private/" not in str(exc.value)
    assert "/" not in str(exc.value)


@pytest.mark.asyncio
async def test_15d_lineage_callable_outage_after_commits_is_reconciliation():
    api, mcp, _operations, _gateway, _store = build_api()
    proposed = await _propose(api)
    mcp.discovery_raises = LINEAGE_BIND_TOOL

    receipt = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by=ACTOR,
    )

    assert receipt["status"] == "partial_failed"
    assert receipt["reason_code"] == (
        "paired_promotion_workflow_callable_unavailable"
    )
    assert receipt["reconciliation_required"] is True
    assert receipt["lineage_binding_status"] == "not_started"
    assert mcp.apply_counts[LINEAGE_BIND_TOOL] == 0
    _assert_closed_and_path_free(receipt, "lineage_unavailable")


# --------------------------------------------------------------------------- #
# Fixture capture — the pin Pipeline's adapter parses
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

    api, _mcp, _ops, _gw, _store, proposed, applied = await _full_apply()
    receipts.append((applied, "applied"))
    common = {
        "proposal_id": proposed["proposal_id"],
        "expected_proposal_fingerprint": proposed["proposal_fingerprint"],
    }
    receipts.append((await api.replay(**common, requested_by=ACTOR), "replayed"))

    api, mcp, _ops, _gw, _store, proposed, partial = await _full_apply(
        lineage_apply="partial"
    )
    receipts.append((partial, "partial_failed"))
    common = {
        "proposal_id": proposed["proposal_id"],
        "expected_proposal_fingerprint": proposed["proposal_fingerprint"],
    }
    mcp.lineage_apply = "bound"
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
                expected_proposal_fingerprint=proposed["proposal_fingerprint"],
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
