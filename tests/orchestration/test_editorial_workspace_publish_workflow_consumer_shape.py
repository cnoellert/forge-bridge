"""Consumer-shape check for #242: a Pipeline test can parse the receipt fixture
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
    / "editorial_workspace_publish_workflow_receipt.json"
)

_RECEIPT_FIELDS = {
    "kind", "schema_version", "action", "status", "trust_status",
    "workflow_id", "proposal_id", "proposal_fingerprint", "publish_preview_id",
    "publish_preview_fingerprint", "transaction_batch_fingerprint",
    "callable_intent_fingerprint", "transaction_id", "selected_roles",
    "published_asset_ids", "manifest_fingerprint", "assent_record_id",
    "assent_status", "commit_fingerprint", "transaction_status",
    "recovery_status", "recovery_manifest_fingerprint",
    "recovery_assent_record_id", "recovery_assent_status",
    "recovery_commit_fingerprint", "dispatch_authorized", "applied",
    "replayed", "reason_code", "fingerprint",
}
_KIND = "bridge.editorial_workspace.publish_workflow_receipt"
_NON_BODY = {"kind", "schema_version", "fingerprint"}


def _canonical(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _fixture() -> dict:
    return json.loads(_FIXTURE.read_text())


def test_fixture_covers_every_terminal():
    assert set(_fixture()) == {
        "proposed",
        "applied",
        "replayed",
        "failed",
        "recovery_proposed",
        "aborted",
    }


def test_every_receipt_is_closed_and_self_verifying():
    for name, receipt in _fixture().items():
        assert receipt["kind"] == _KIND, name
        assert receipt["schema_version"] == 1, name
        assert set(receipt) == _RECEIPT_FIELDS, name
        body = {k: v for k, v in receipt.items() if k not in _NON_BODY}
        assert receipt["fingerprint"] == _canonical(body), name
        for field in ("dispatch_authorized", "applied", "replayed"):
            assert isinstance(receipt[field], bool), (name, field)
        for field in ("selected_roles", "published_asset_ids"):
            values = receipt[field]
            assert isinstance(values, list), (name, field)
            assert all(isinstance(item, str) for item in values), (name, field)
            assert sorted(set(values)) == values, (name, field)
        assert receipt["selected_roles"], name
        for field in (
            "trust_status",
            "workflow_id",
            "proposal_id",
            "publish_preview_id",
            "transaction_id",
            "transaction_status",
        ):
            assert isinstance(receipt[field], str) and receipt[field], (
                name,
                field,
            )


def test_no_receipt_carries_a_path_or_a_held_payload():
    for name, receipt in _fixture().items():
        serialized = json.dumps(receipt, sort_keys=True)
        assert "/" not in serialized, name
        for needle in (
            "transaction_plan",
            "abort_plan",
            "resolved_plan",
            "intent_parameters",
            "apply_counterpart",
            "held_manifest",
            "journal",
            "source_path",
        ):
            assert needle not in serialized, (name, needle)
        for value in receipt.values():
            assert not isinstance(value, dict), name


def test_terminal_invariants_match_the_handoff():
    fixture = _fixture()

    proposed = fixture["proposed"]
    assert proposed["status"] == "proposed"
    assert proposed["dispatch_authorized"] is False
    assert proposed["applied"] is False
    assert proposed["transaction_status"] == "not_started"
    assert proposed["published_asset_ids"] == []
    assert proposed["recovery_status"] == "not_required"

    applied = fixture["applied"]
    assert applied["status"] == "applied"
    assert applied["applied"] is True
    assert applied["replayed"] is False
    assert applied["transaction_status"] == "committed"
    assert applied["commit_fingerprint"]
    assert applied["published_asset_ids"]

    replayed = fixture["replayed"]
    assert replayed["action"] == "replay"
    assert replayed["status"] == "applied"
    assert replayed["replayed"] is True
    assert replayed["commit_fingerprint"] == applied["commit_fingerprint"]

    recovery = fixture["recovery_proposed"]
    assert recovery["action"] == "propose_recovery"
    assert recovery["recovery_status"] == "available"
    assert recovery["recovery_assent_status"] == "proposed"
    assert recovery["recovery_manifest_fingerprint"]
    assert recovery["recovery_commit_fingerprint"] is None
    assert recovery["dispatch_authorized"] is False

    aborted = fixture["aborted"]
    assert aborted["action"] == "ratify_recovery"
    assert aborted["status"] == "aborted"
    assert aborted["transaction_status"] == "aborted"
    assert aborted["recovery_status"] == "aborted"
    assert aborted["recovery_commit_fingerprint"]
    assert aborted["dispatch_authorized"] is True


def test_recovery_authority_never_overwrites_the_forward_authority():
    fixture = _fixture()
    forward = fixture["failed"]
    for name in ("recovery_proposed", "aborted"):
        receipt = fixture[name]
        for field in (
            "proposal_fingerprint",
            "publish_preview_fingerprint",
            "transaction_batch_fingerprint",
            "callable_intent_fingerprint",
            "manifest_fingerprint",
            "assent_record_id",
            "transaction_id",
        ):
            assert receipt[field] == forward[field], (name, field)
        assert receipt["recovery_manifest_fingerprint"] != (
            receipt["manifest_fingerprint"]
        )
        assert receipt["recovery_assent_record_id"] != (
            receipt["assent_record_id"]
        )
