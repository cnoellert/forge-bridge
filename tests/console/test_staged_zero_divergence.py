"""STAGED-05/06/07 cross-surface verification.

D-19: MCP tool output equals HTTP route output (byte-identity mod formatting).
D-20: covered by tests/test_console_mcp_resources.py::test_staged_pending_resource_matches_list_tool.
D-21: approval is bookkeeping only — bridge.execute is NEVER called during approval/rejection.

These are regression guards. Any future change that diverges MCP from HTTP, or
that wires forge-bridge into execution-on-approval (a load-bearing architectural
no-no — projekt-forge owns execution), fails CI here.
"""
from __future__ import annotations
import json
import uuid
import pytest
import pytest_asyncio
from unittest.mock import MagicMock
import httpx
from httpx import ASGITransport

from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.console.resources import register_console_resources
from forge_bridge.store.staged_operations import StagedOpRepo
from forge_bridge.store.repo import EventRepo
from forge_bridge.mcp.tools import (
    ListStagedInput, GetStagedInput, ApproveStagedInput, RejectStagedInput,
)
from tests.test_console_mcp_resources import _ResourceSpy


@pytest_asyncio.fixture
async def staged_api(session_factory):
    """A ConsoleReadAPI configured with the session_factory; no pre-seeded data."""
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    return ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, session_factory=session_factory,
    )


@pytest_asyncio.fixture
async def staged_client(staged_api, session_factory):
    app = build_console_app(staged_api, session_factory=session_factory)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def staged_spy(staged_api, session_factory):
    spy = _ResourceSpy()
    register_console_resources(spy, staged_api._manifest_service, staged_api, session_factory=session_factory)
    return spy


async def _seed_proposed(session_factory, *, n: int = 1):
    ids = []
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        for i in range(n):
            op = await repo.propose(operation=f"seed_op_{i}", proposer="seed", parameters={"i": i})
            ids.append(op.id)
        await session.commit()
    return ids


async def _seed_approved(session_factory):
    ids = await _seed_proposed(session_factory, n=1)
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(ids[0], approver="seed")
        await session.commit()
    return ids[0]


# ── D-19 BYTE-IDENTITY TESTS ────────────────────────────────────────────────

async def test_list_staged_no_filter_byte_identity(staged_spy, staged_client, session_factory):
    """forge_list_staged() == GET /api/v1/staged (no filters)."""
    await _seed_proposed(session_factory, n=2)
    tool_body = await staged_spy.tools["forge_list_staged"](ListStagedInput())
    http_body = (await staged_client.get("/api/v1/staged")).content.decode()
    assert json.loads(tool_body) == json.loads(http_body), (
        f"Tool: {tool_body!r}\nHTTP: {http_body!r}"
    )


async def test_list_staged_filtered_byte_identity(staged_spy, staged_client, session_factory):
    """forge_list_staged(status='proposed', limit=50) == GET /api/v1/staged?status=proposed&limit=50."""
    await _seed_proposed(session_factory, n=2)
    # Promote one to approved so the filter actually narrows the result set
    proposed_ids = await _seed_proposed(session_factory, n=1)
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(proposed_ids[0], approver="seed")
        await session.commit()
    tool_body = await staged_spy.tools["forge_list_staged"](
        ListStagedInput(status="proposed", limit=50, offset=0)
    )
    http_body = (await staged_client.get("/api/v1/staged?status=proposed&limit=50&offset=0")).content.decode()
    assert json.loads(tool_body) == json.loads(http_body)


async def test_list_staged_invalid_filter_byte_identity(staged_spy, staged_client):
    """Both surfaces return the same invalid_filter envelope."""
    tool_body = await staged_spy.tools["forge_list_staged"](ListStagedInput(status="bogus"))
    http_body = (await staged_client.get("/api/v1/staged?status=bogus")).content.decode()
    assert json.loads(tool_body) == json.loads(http_body)
    decoded = json.loads(tool_body)
    assert decoded["error"]["code"] == "invalid_filter"


async def test_approve_lifecycle_error_byte_identity(staged_spy, staged_client, session_factory):
    """Re-approving an already-approved op returns the same illegal_transition
    envelope (with current_status field) on both surfaces."""
    approved_id = await _seed_approved(session_factory)
    tool_body = await staged_spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(approved_id), actor="test")
    )
    http_body = (await staged_client.post(
        f"/api/v1/staged/{approved_id}/approve",
        headers={"X-Forge-Actor": "test"},
    )).content.decode()
    tool_decoded = json.loads(tool_body)
    http_decoded = json.loads(http_body)
    assert tool_decoded == http_decoded, (
        f"D-19 lifecycle error divergence.\nTool: {tool_decoded!r}\nHTTP: {http_decoded!r}"
    )
    assert tool_decoded["error"]["code"] == "illegal_transition"
    assert tool_decoded["error"]["current_status"] == "approved"


async def test_approve_not_found_byte_identity(staged_spy, staged_client):
    """Approving an unknown UUID returns the same staged_op_not_found envelope."""
    bogus = uuid.uuid4()
    tool_body = await staged_spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(bogus), actor="test")
    )
    http_body = (await staged_client.post(
        f"/api/v1/staged/{bogus}/approve",
        headers={"X-Forge-Actor": "test"},
    )).content.decode()
    assert json.loads(tool_body) == json.loads(http_body)
    decoded = json.loads(tool_body)
    assert decoded["error"]["code"] == "staged_op_not_found"


async def test_reject_lifecycle_error_byte_identity(staged_spy, staged_client, session_factory):
    """Re-rejecting returns the same illegal_transition envelope on both surfaces."""
    proposed_ids = await _seed_proposed(session_factory, n=1)
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.reject(proposed_ids[0], actor="seed")
        await session.commit()
    rejected_id = proposed_ids[0]
    tool_body = await staged_spy.tools["forge_reject_staged"](
        RejectStagedInput(id=str(rejected_id), actor="test")
    )
    http_body = (await staged_client.post(
        f"/api/v1/staged/{rejected_id}/reject",
        headers={"X-Forge-Actor": "test"},
    )).content.decode()
    assert json.loads(tool_body) == json.loads(http_body)
    decoded = json.loads(tool_body)
    assert decoded["error"]["current_status"] == "rejected"


# ── D-21 DOES-NOT-EXECUTE REGRESSION GUARD ──────────────────────────────────

async def test_approval_does_not_execute(session_factory, monkeypatch):
    """STAGED-07 success criterion #4 — approval is bookkeeping only.

    forge-bridge contains NO code that listens for staged.approved and runs
    execution. The proposer (projekt-forge) consumes the event via its own
    bus subscription and executes against Flame. This test fails the day
    someone wires execution into the approval path.

    Negative-assertion pattern (proves something did NOT happen):
    - Monkeypatch forge_bridge.bridge.execute to raise AssertionError if called.
    - Drive an approval through StagedOpRepo.approve.
    - Assert no AssertionError surfaced AND the only DBEvents are
      staged.proposed + staged.approved.
    """
    sentinel = {"called": False}

    async def _no_exec(*args, **kwargs):
        sentinel["called"] = True
        raise AssertionError("approval triggered execution — D-21 violated")

    # Patch the canonical Flame execution entry point. If the codebase later
    # adds another execution entry point (e.g. forge_bridge.synthesizer.run),
    # add it to this monkeypatch list — keep the negative-assertion sentinel
    # set to ensure execution is NEVER called from approval.
    monkeypatch.setattr("forge_bridge.bridge.execute", _no_exec, raising=False)

    proposed_ids = await _seed_proposed(session_factory, n=1)
    op_id = proposed_ids[0]
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(op_id, approver="artist")
        await session.commit()

    assert not sentinel["called"], "approval must NOT call bridge.execute"

    # Audit trail check — exactly 2 events, no execution event
    async with session_factory() as session:
        events = await EventRepo(session).get_recent(entity_id=op_id, limit=10)
    event_types = sorted(e.event_type for e in events)
    assert event_types == ["staged.approved", "staged.proposed"], (
        f"Expected exactly [staged.approved, staged.proposed], got {event_types}"
    )


async def test_rejection_does_not_execute(session_factory, monkeypatch):
    """Symmetric to test_approval_does_not_execute — rejection is also bookkeeping only."""
    sentinel = {"called": False}

    async def _no_exec(*args, **kwargs):
        sentinel["called"] = True
        raise AssertionError("rejection triggered execution — D-21 violated")

    monkeypatch.setattr("forge_bridge.bridge.execute", _no_exec, raising=False)

    proposed_ids = await _seed_proposed(session_factory, n=1)
    op_id = proposed_ids[0]
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.reject(op_id, actor="artist")
        await session.commit()

    assert not sentinel["called"], "rejection must NOT call bridge.execute"

    async with session_factory() as session:
        events = await EventRepo(session).get_recent(entity_id=op_id, limit=10)
    event_types = sorted(e.event_type for e in events)
    assert event_types == ["staged.proposed", "staged.rejected"], (
        f"Expected exactly [staged.proposed, staged.rejected], got {event_types}"
    )
