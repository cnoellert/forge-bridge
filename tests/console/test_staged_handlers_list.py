"""FB-B STAGED-06 — staged_list_handler HTTP route tests.

Covers D-01 pagination/filtering/ordering, D-05 limit clamp, D-10 error codes.
All tests use the `staged_client` fixture from tests/console/conftest.py which
wires a real session_factory (Phase 13 Postgres fixture) to the ConsoleReadAPI +
Starlette app.  Tests skip cleanly when Postgres at localhost:5432 is unreachable.
"""
from __future__ import annotations

import uuid
import asyncio
import time

import pytest
import pytest_asyncio
from starlette.testclient import TestClient

from forge_bridge.store.staged_operations import StagedOpRepo


# ── Envelope shape ──────────────────────────────────────────────────────────────

async def test_staged_list_default_returns_envelope(staged_client):
    """GET /api/v1/staged with no filters returns 200 with data + meta envelope."""
    r = staged_client.get("/api/v1/staged")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body, f"Expected 'data' key; got {list(body.keys())}"
    assert "meta" in body, f"Expected 'meta' key; got {list(body.keys())}"
    assert isinstance(body["data"], list)
    assert "limit" in body["meta"]
    assert "offset" in body["meta"]
    assert "total" in body["meta"]


# ── Status filter ────────────────────────────────────────────────────────────────

async def test_staged_list_filter_by_status(session_factory, staged_client):
    """?status=proposed returns only proposed records; seed 1 proposed + 1 approved."""
    # Seed
    proposed_id = None
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op1 = await repo.propose(operation="flame.publish", proposer="test", parameters={})
        op2 = await repo.propose(operation="flame.export", proposer="test", parameters={})
        proposed_id = op1.id
        await session.commit()
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(op2.id, approver="test")
        await session.commit()

    r = staged_client.get("/api/v1/staged?status=proposed")
    assert r.status_code == 200
    body = r.json()
    assert all(op["status"] == "proposed" for op in body["data"]), (
        f"Expected only proposed records; got {[op['status'] for op in body['data']]}"
    )
    assert body["meta"]["total"] >= 1


async def test_staged_list_unknown_status_returns_400(staged_client):
    """?status=foo returns 400 with error.code=invalid_filter."""
    r = staged_client.get("/api/v1/staged?status=foo")
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "invalid_filter"
    assert "expected one of" in body["error"]["message"].lower(), (
        f"Expected message to contain 'expected one of'; got {body['error']['message']!r}"
    )


# ── Limit clamp (D-05) ──────────────────────────────────────────────────────────

async def test_staged_list_clamps_limit_to_500(staged_client):
    """?limit=1000 is silently clamped to 500 per Phase 9 D-05."""
    r = staged_client.get("/api/v1/staged?limit=1000")
    assert r.status_code == 200
    assert r.json()["meta"]["limit"] == 500


# ── project_id filter ────────────────────────────────────────────────────────────

async def test_staged_list_bad_project_id_returns_400(staged_client):
    """?project_id=not-a-uuid returns 400 with error.code=bad_request."""
    r = staged_client.get("/api/v1/staged?project_id=not-a-uuid")
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "bad_request"
    assert "invalid project_id" in body["error"]["message"]


async def test_staged_list_filter_by_project_id(session_factory, staged_client):
    """?project_id=<uuid> returns only records for that project."""
    project_a = uuid.uuid4()
    project_b = uuid.uuid4()
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.propose(operation="op.a", proposer="test", parameters={}, project_id=project_a)
        await repo.propose(operation="op.b", proposer="test", parameters={}, project_id=project_b)
        await session.commit()

    r = staged_client.get(f"/api/v1/staged?project_id={project_a}")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["status"] is not None  # record exists


# ── Pagination ────────────────────────────────────────────────────────────────────

async def test_staged_list_pagination_offset(session_factory, staged_client):
    """?limit=2&offset=2 returns 2 records with correct meta.offset and meta.total."""
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        for i in range(5):
            await repo.propose(operation=f"op.{i}", proposer="test", parameters={})
        await session.commit()

    r = staged_client.get("/api/v1/staged?limit=2&offset=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == 2
    assert body["meta"]["offset"] == 2
    assert body["meta"]["total"] == 5


# ── Ordering ─────────────────────────────────────────────────────────────────────

async def test_staged_list_orders_by_created_at_desc(session_factory, staged_client):
    """Records are returned newest-first (created_at DESC per D-01)."""
    # Seed 3 ops with a small delay between them so created_at is distinct
    op_ids = []
    for i in range(3):
        async with session_factory() as session:
            repo = StagedOpRepo(session)
            op = await repo.propose(operation=f"op.order.{i}", proposer="test", parameters={})
            await session.commit()
        op_ids.append(op.id)
        # Small sleep to ensure distinct created_at timestamps
        await asyncio.sleep(0.01)

    r = staged_client.get("/api/v1/staged?limit=3&offset=0")
    assert r.status_code == 200
    records = r.json()["data"]
    # Extract created_at strings and verify DESC order
    timestamps = [rec["created_at"] for rec in records if rec["id"] in [str(i) for i in op_ids]]
    # At minimum: the response must be ordered (each created_at >= the next)
    all_records = r.json()["data"]
    if len(all_records) >= 2:
        for i in range(len(all_records) - 1):
            assert all_records[i]["created_at"] >= all_records[i + 1]["created_at"], (
                f"Records not in DESC order: {all_records[i]['created_at']!r} < {all_records[i+1]['created_at']!r}"
            )


# ── Empty result ──────────────────────────────────────────────────────────────────

async def test_staged_list_empty_result_returns_empty_data(session_factory, staged_client):
    """No matching records returns 200 with data=[] and meta.total=0 (NOT 404)."""
    # Seed only an approved op; then query for rejected — should be empty
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(operation="op.x", proposer="test", parameters={})
        await session.commit()
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(op.id, approver="test")
        await session.commit()

    r = staged_client.get("/api/v1/staged?status=rejected")
    assert r.status_code == 200
    body = r.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0
