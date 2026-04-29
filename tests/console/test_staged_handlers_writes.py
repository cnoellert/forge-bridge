"""FB-B STAGED-06 — staged_approve_handler + staged_reject_handler HTTP route tests.

Covers D-06 actor resolution priority, D-09 strict 409 on re-approve/re-reject,
D-10 error code matrix (bad_actor, illegal_transition, staged_op_not_found, bad_request).
All tests use the `staged_client`, `proposed_op_id`, `approved_op_id` fixtures from
tests/console/conftest.py.  Tests skip cleanly when Postgres at localhost:5432 is
unreachable.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from forge_bridge.store.staged_operations import StagedOpRepo


# ── D-06 Actor resolution — approve ─────────────────────────────────────────────

async def test_approve_with_header_actor(staged_client, proposed_op_id):
    """Header X-Forge-Actor takes priority; no body needed."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "approved"
    assert body["data"]["approver"] == "test-suite"


async def test_approve_with_body_actor_no_header(staged_client, proposed_op_id):
    """JSON body actor used when no header present."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        json={"actor": "test-suite"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["approver"] == "test-suite"


async def test_approve_fallback_actor_no_header_no_body(staged_client, proposed_op_id):
    """No header, no body → 'http:anonymous' fallback."""
    r = await staged_client.post(f"/api/v1/staged/{proposed_op_id}/approve")
    assert r.status_code == 200
    assert r.json()["data"]["approver"] == "http:anonymous"


async def test_approve_empty_header_actor_returns_400(staged_client, proposed_op_id):
    """Empty X-Forge-Actor header returns 400 bad_actor."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        headers={"X-Forge-Actor": ""},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "bad_actor"
    assert "X-Forge-Actor" in body["error"]["message"] or "empty" in body["error"]["message"].lower()


async def test_approve_empty_body_actor_returns_400(staged_client, proposed_op_id):
    """Empty body actor returns 400 bad_actor."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        json={"actor": ""},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_actor"


async def test_approve_non_string_body_actor_returns_400(staged_client, proposed_op_id):
    """Non-string body actor (e.g. 123) returns 400 bad_actor."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        json={"actor": 123},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_actor"


async def test_approve_malformed_json_body_falls_back(staged_client, proposed_op_id):
    """Malformed JSON body swallowed silently → falls back to 'http:anonymous'."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        content=b"{{not valid json}}",
        headers={"Content-Type": "application/json"},
    )
    # Body parse fails → body=None → fallback to http:anonymous
    assert r.status_code == 200
    assert r.json()["data"]["approver"] == "http:anonymous"


# ── D-09 Idempotency / lifecycle — approve ──────────────────────────────────────

async def test_approve_proposed_returns_200(staged_client, proposed_op_id):
    """Happy-path: approve a proposed op returns 200 with status=approved."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "approved"


async def test_re_approve_returns_409_with_current_status(staged_client, approved_op_id):
    """Re-approving an already-approved op returns 409 with error.code=illegal_transition
    and error.current_status=approved (D-09 strict, no idempotent 200)."""
    r = await staged_client.post(
        f"/api/v1/staged/{approved_op_id}/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "illegal_transition"
    assert err["current_status"] == "approved"
    assert "Illegal transition" in err["message"]


async def test_approve_unknown_uuid_returns_404(staged_client):
    """Unknown UUID returns 404 with error.code=staged_op_not_found."""
    bogus = uuid.uuid4()
    r = await staged_client.post(
        f"/api/v1/staged/{bogus}/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "staged_op_not_found"
    assert "no staged_operation with id" in body["error"]["message"]


async def test_approve_malformed_uuid_returns_400(staged_client):
    """Non-UUID path param returns 400 with error.code=bad_request."""
    r = await staged_client.post(
        "/api/v1/staged/not-a-uuid/approve",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "bad_request"
    assert "invalid staged_operation id" in body["error"]["message"]


# ── D-06 Actor resolution — reject ──────────────────────────────────────────────

async def test_reject_proposed_returns_200(staged_client, proposed_op_id):
    """Happy-path: reject a proposed op returns 200 with status=rejected."""
    r = await staged_client.post(
        f"/api/v1/staged/{proposed_op_id}/reject",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "rejected"


# ── D-09 Idempotency — reject ───────────────────────────────────────────────────

async def test_re_reject_returns_409(staged_client, rejected_op_id):
    """Re-rejecting a rejected op returns 409 with current_status=rejected."""
    r = await staged_client.post(
        f"/api/v1/staged/{rejected_op_id}/reject",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "illegal_transition"
    assert err["current_status"] == "rejected"


async def test_approve_then_reject_returns_409(staged_client, approved_op_id):
    """Approved op cannot be rejected → 409 with current_status=approved."""
    r = await staged_client.post(
        f"/api/v1/staged/{approved_op_id}/reject",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "illegal_transition"
    assert err["current_status"] == "approved"


async def test_reject_unknown_uuid_returns_404(staged_client):
    """Unknown UUID returns 404 with error.code=staged_op_not_found."""
    bogus = uuid.uuid4()
    r = await staged_client.post(
        f"/api/v1/staged/{bogus}/reject",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "staged_op_not_found"


async def test_reject_malformed_uuid_returns_400(staged_client):
    """Non-UUID path param returns 400 on reject route."""
    r = await staged_client.post(
        "/api/v1/staged/not-a-uuid/reject",
        headers={"X-Forge-Actor": "test-suite"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_request"
