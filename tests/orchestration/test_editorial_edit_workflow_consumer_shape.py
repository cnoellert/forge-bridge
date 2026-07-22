"""Consumer-shape check: a Pipeline test can parse the receipt fixture using
only stdlib — no forge_bridge imports — and re-verify its canonical fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

_FIXTURE = Path(__file__).parent / "fixtures" / "editorial_edit_workflow_receipt.json"

_RECEIPT_KEYS = [
    "kind", "schema_version", "action", "status", "workflow_id", "proposal_id",
    "proposal_fingerprint", "preview_id", "preview_authority_fingerprint",
    "step_plan_fingerprint", "live_state_fingerprint",
    "semantic_capability_plan_fingerprint", "realization_plan_fingerprint",
    "delta_fingerprint", "manifest_fingerprint", "assent_record_id",
    "assent_status", "commit_fingerprint", "dispatch_authorized", "applied",
    "replayed", "restored", "reason_code",
]


def _canonical(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_receipt_fixture_is_closed_and_self_verifying():
    data = json.loads(_FIXTURE.read_text())
    for receipt in (data["proposed"], data["applied"]):
        assert receipt["kind"] == "bridge.editorial_edit_workflow_receipt"
        assert set(receipt) == set(_RECEIPT_KEYS) | {"fingerprint"}
        body = {k: receipt[k] for k in _RECEIPT_KEYS}
        assert receipt["fingerprint"] == _canonical(body)
        # path-free: no value carries a filesystem path
        for value in receipt.values():
            assert not (isinstance(value, str) and "/" in value)


def test_applied_receipt_flags_are_mutually_exclusive():
    applied = json.loads(_FIXTURE.read_text())["applied"]
    assert applied["status"] == "applied"
    assert applied["applied"] is True
    assert applied["replayed"] is False
    assert applied["restored"] is False
    assert applied["dispatch_authorized"] is True
