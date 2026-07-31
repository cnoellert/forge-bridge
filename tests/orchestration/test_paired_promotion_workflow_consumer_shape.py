"""Consumer-shape check for #261: a Pipeline test can parse the receipt fixture
using only stdlib — no forge_bridge imports — and re-verify every invariant its
adapter enforces.

The fixture is CAPTURED from the live API (see the acceptance matrix), not
hand-assembled, so it is a real pin for Pipeline's adapter contract.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "paired_promotion_workflow_receipt.json"
)

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
_KIND = "bridge.paired_promotion.workflow_receipt"
_NON_BODY = {"kind", "schema_version", "fingerprint"}
_ACTIONS = {"propose", "ratify_apply", "status", "replay"}
_STATUSES = {"proposed", "applied", "partial_failed", "failed", "unavailable"}
_STAGE_STATUSES = {
    "not_started", "applied", "registered", "promoted", "bound", "failed",
}
_STAGE_FIELDS = (
    "resource_copy_status",
    "resource_registration_status",
    "workfile_promotion_status",
    "lineage_binding_status",
)
_COMPLETE_STAGE = {
    "resource_copy_status": "applied",
    "resource_registration_status": "registered",
    "workfile_promotion_status": "promoted",
    "lineage_binding_status": "bound",
}
_FINGERPRINT_FIELDS = (
    "resource_copy_manifest_fingerprint",
    "resource_copy_commit_fingerprint",
    "resource_registration_manifest_fingerprint",
    "resource_registration_commit_fingerprint",
    "workfile_promotion_manifest_fingerprint",
    "workfile_promotion_commit_fingerprint",
    "lineage_binding_manifest_fingerprint",
    "lineage_binding_commit_fingerprint",
)


def _canonical(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _fixture() -> dict:
    return json.loads(_FIXTURE.read_text())


def test_fixture_covers_every_terminal():
    assert set(_fixture()) == {
        "proposed",
        "status_proposed",
        "applied",
        "replayed",
        "partial_failed",
        "replay_completed",
        "failed",
        "unavailable",
    }


def test_every_receipt_is_closed_and_self_verifying():
    for label, receipt in _fixture().items():
        assert set(receipt) == _RECEIPT_FIELDS, label
        assert receipt["kind"] == _KIND, label
        assert receipt["schema_version"] == 1, label
        assert receipt["action"] in _ACTIONS, label
        assert receipt["status"] in _STATUSES, label
        body = {
            key: value
            for key, value in receipt.items()
            if key not in _NON_BODY
        }
        assert receipt["fingerprint"] == _canonical(body), label


def test_no_receipt_carries_a_path_or_a_private_body():
    for label, receipt in _fixture().items():
        serialized = json.dumps(receipt)
        assert "/" not in serialized, label
        for marker in (
            "promotion_plan",
            "lineage_plan",
            "callable_intent",
            "resolved_plan",
            "intent_parameters",
            "apply_result",
            ".batch",
        ):
            assert marker not in serialized, (label, marker)


def test_stage_vocabulary_is_closed_and_not_interchangeable():
    for label, receipt in _fixture().items():
        for field in _STAGE_FIELDS:
            assert receipt[field] in _STAGE_STATUSES, (label, field)
            if receipt[field] not in {"not_started", "failed"}:
                assert receipt[field] == _COMPLETE_STAGE[field], (label, field)


def test_applied_receipts_prove_all_four_stages_and_both_promoted_pairs():
    for label in ("applied", "replayed", "replay_completed"):
        receipt = _fixture()[label]
        assert receipt["status"] == "applied", label
        assert receipt["trust_status"] == "trusted", label
        assert receipt["applied"] is True, label
        assert receipt["main_advanced"] is True, label
        assert receipt["reconciliation_required"] is False, label
        assert receipt["reason_code"] is None, label
        for field in _STAGE_FIELDS:
            assert receipt[field] == _COMPLETE_STAGE[field], (label, field)
        for field in _FINGERPRINT_FIELDS:
            assert isinstance(receipt[field], str), (label, field)
            assert len(receipt[field]) == 64, (label, field)
        assert len({receipt[field] for field in _FINGERPRINT_FIELDS}) == 8, label
        for field in (
            "main_render_version_id",
            "main_render_media_id",
            "main_workfile_version_id",
            "lineage_relationship_id",
        ):
            assert receipt[field], (label, field)


def test_partial_receipts_are_reconciliation_required_and_never_advanced():
    receipt = _fixture()["partial_failed"]
    assert receipt["status"] == "partial_failed"
    assert receipt["trust_status"] == "review_required"
    assert receipt["applied"] is False
    assert receipt["main_advanced"] is False
    assert receipt["reconciliation_required"] is True
    assert receipt["dispatch_authorized"] is True
    assert receipt["reason_code"]
    assert receipt["lineage_relationship_id"] is None


def test_proposed_receipts_claim_nothing():
    for label in ("proposed", "status_proposed"):
        receipt = _fixture()[label]
        assert receipt["status"] == "proposed", label
        assert receipt["dispatch_authorized"] is False, label
        assert receipt["applied"] is False, label
        assert receipt["replayed"] is False, label
        assert receipt["main_advanced"] is False, label
        assert receipt["reconciliation_required"] is False, label
        assert receipt["assent_status"] == "proposed", label
        assert receipt["promoted_resource_asset_ids"] == [], label
        for field in _STAGE_FIELDS:
            assert receipt[field] == "not_started", (label, field)
        # The two manifests discovered at propose ARE pinned; the two that can
        # only exist after a commit are not.
        assert receipt["resource_copy_manifest_fingerprint"], label
        assert receipt["workfile_promotion_manifest_fingerprint"], label
        assert receipt["resource_registration_manifest_fingerprint"] is None
        assert receipt["lineage_binding_manifest_fingerprint"] is None


def test_replay_flag_only_rides_a_completed_replay():
    for label, receipt in _fixture().items():
        if receipt["replayed"]:
            assert receipt["action"] == "replay", label
            assert receipt["status"] == "applied", label


def test_retained_artist_identities_survive_every_terminal():
    for label, receipt in _fixture().items():
        assert receipt["source_render_version_id"] == (
            "c227ce59-8e5f-4bb0-a6e2-ae41b957dc19"
        ), label
        assert receipt["source_render_media_id"] == (
            "ca67767a-e79e-4a8d-8827-0225e0f52151"
        ), label
        assert receipt["source_workfile_version_id"] == (
            "2d0f5670-ab64-4e13-a3d9-a97ffdb8ec34"
        ), label
