"""Consumer-shape check for #244: a Pipeline test can parse the receipt fixture
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
    Path(__file__).parent
    / "fixtures"
    / "editorial_workspace_promotion_workflow_receipt.json"
)

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
_KIND = "bridge.editorial_workspace.promotion_workflow_receipt"
_NON_BODY = {"kind", "schema_version", "fingerprint"}
_ACTIONS = {"propose", "ratify_apply", "status", "replay"}
_STATUSES = {"proposed", "applied", "partial_failed", "failed", "unavailable"}
_STAGE_STATUSES = {"not_started", "applied", "registered", "failed"}
_STAGE_FIELDS = (
    "resource_copy_status",
    "resource_registration_status",
    "main_registration_status",
)
_FINGERPRINT_FIELDS = (
    "resource_copy_manifest_fingerprint",
    "resource_copy_commit_fingerprint",
    "resource_registration_manifest_fingerprint",
    "resource_registration_commit_fingerprint",
    "main_registration_manifest_fingerprint",
    "main_registration_commit_fingerprint",
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
    for name, receipt in _fixture().items():
        assert receipt["kind"] == _KIND, name
        assert receipt["schema_version"] == 1, name
        assert set(receipt) == _RECEIPT_FIELDS, name
        body = {k: v for k, v in receipt.items() if k not in _NON_BODY}
        assert receipt["fingerprint"] == _canonical(body), name
        assert receipt["action"] in _ACTIONS, name
        assert receipt["status"] in _STATUSES, name
        for field in (
            "dispatch_authorized",
            "applied",
            "replayed",
            "main_advanced",
            "reconciliation_required",
        ):
            assert isinstance(receipt[field], bool), (name, field)
        for field in _STAGE_FIELDS:
            assert receipt[field] in _STAGE_STATUSES, (name, field)
        for field in (
            "selected_roles",
            "published_resource_asset_ids",
            "promoted_resource_asset_ids",
        ):
            values = receipt[field]
            assert isinstance(values, list), (name, field)
            assert all(isinstance(item, str) for item in values), (name, field)
            assert sorted(set(values)) == values, (name, field)
        assert receipt["selected_roles"], name
        assert receipt["published_resource_asset_ids"], name
        assert isinstance(receipt["target_main_version_number"], int), name
        assert receipt["target_main_version_number"] > 0, name
        for field in _FINGERPRINT_FIELDS:
            value = receipt[field]
            assert value is None or (
                isinstance(value, str) and len(value) == 64
            ), (name, field)


def test_receipts_carry_no_paths_or_held_bodies():
    forbidden = (
        "/",
        "promotion_plan",
        "callable_intent",
        "resolved_plan",
        "intent_parameters",
        "registration_plan",
        "apply_result",
        "workspace_main_promotion_plan",
        "source_location",
    )
    for name, receipt in _fixture().items():
        serialized = json.dumps(receipt)
        for marker in forbidden:
            assert marker not in serialized, (name, marker)


def test_status_invariants_hold_per_terminal():
    fixture = _fixture()

    for name in ("proposed", "status_proposed"):
        receipt = fixture[name]
        assert receipt["status"] == "proposed", name
        assert receipt["trust_status"] == "trusted", name
        assert receipt["dispatch_authorized"] is False, name
        assert receipt["applied"] is False, name
        assert receipt["main_advanced"] is False, name
        assert receipt["reconciliation_required"] is False, name
        assert receipt["promoted_resource_asset_ids"] == [], name
        assert receipt["assent_status"] == "proposed", name
        assert receipt["resource_copy_manifest_fingerprint"] is not None, name
        assert all(
            receipt[field] == "not_started" for field in _STAGE_FIELDS
        ), name

    for name in ("applied", "replayed", "replay_completed"):
        receipt = fixture[name]
        assert receipt["status"] == "applied", name
        assert receipt["applied"] is True, name
        assert receipt["main_advanced"] is True, name
        assert receipt["reconciliation_required"] is False, name
        assert receipt["dispatch_authorized"] is True, name
        assert receipt["resource_copy_status"] == "applied", name
        assert receipt["resource_registration_status"] == "registered", name
        assert receipt["main_registration_status"] == "registered", name
        assert receipt["main_version_id"], name
        assert receipt["main_media_id"], name
        assert len(receipt["promoted_resource_asset_ids"]) == len(
            receipt["selected_roles"]
        ), name
        assert all(receipt[field] for field in _FINGERPRINT_FIELDS), name

    partial = fixture["partial_failed"]
    assert partial["status"] == "partial_failed"
    assert partial["dispatch_authorized"] is True
    assert partial["applied"] is False
    assert partial["main_advanced"] is False
    assert partial["reconciliation_required"] is True
    assert partial["reason_code"]
    assert any(
        partial[field] != "not_started" for field in _STAGE_FIELDS
    )

    for name in ("replayed", "replay_completed"):
        assert fixture[name]["replayed"] is True, name
        assert fixture[name]["action"] == "replay", name
    for name, receipt in fixture.items():
        if receipt["replayed"]:
            assert receipt["action"] == "replay", name
            assert receipt["status"] == "applied", name


def test_replay_never_widens_authority_or_mints_a_new_assent():
    fixture = _fixture()
    partial = fixture["partial_failed"]
    completed = fixture["replay_completed"]

    assert completed["proposal_id"] == partial["proposal_id"]
    assert completed["proposal_fingerprint"] == partial["proposal_fingerprint"]
    assert completed["assent_record_id"] == partial["assent_record_id"]
    assert completed["selected_roles"] == partial["selected_roles"]
    assert completed["published_resource_asset_ids"] == (
        partial["published_resource_asset_ids"]
    )
    assert completed["target_main_version_number"] == (
        partial["target_main_version_number"]
    )
    assert completed["promotion_authority_fingerprint"] == (
        partial["promotion_authority_fingerprint"]
    )
    # The two stages that already stood keep their exact commit evidence.
    assert completed["resource_copy_commit_fingerprint"] == (
        partial["resource_copy_commit_fingerprint"]
    )
    assert completed["resource_registration_commit_fingerprint"] == (
        partial["resource_registration_commit_fingerprint"]
    )
