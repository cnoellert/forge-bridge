"""STAGED-05 / D-18 — MCP tool integration via _ResourceSpy.

Per RESEARCH.md Finding #7 Option B, hermetic in-process registration via spy
rather than booting a real FastMCP subprocess. Solution C (D-17 revised)
registers the four staged tools from register_console_resources, so the spy
captures them alongside the resource and shim.
"""
from __future__ import annotations

import json
import uuid
import pytest
import pytest_asyncio
from unittest.mock import MagicMock

from pydantic import ValidationError

from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.console.resources import register_console_resources
from forge_bridge.store.staged_operations import StagedOpRepo
from forge_bridge.mcp.tools import (
    ListStagedInput, GetStagedInput, ApproveStagedInput, RejectStagedInput,
)
from tests.test_console_mcp_resources import _ResourceSpy


@pytest_asyncio.fixture
async def spy_with_staged_data(session_factory):
    """A _ResourceSpy with the four staged tools + resource + shim registered,
    backed by a session_factory pre-seeded with one proposed op."""
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    mock_log._storage_callback = None
    api = ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, session_factory=session_factory,
    )
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(
            operation="flame.publish", proposer="test", parameters={"x": 1},
        )
        await session.commit()
    spy = _ResourceSpy()
    register_console_resources(spy, ms, api, session_factory=session_factory)
    return spy, op.id


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic validation tests (no DB required)
# ─────────────────────────────────────────────────────────────────────────────

def test_approve_staged_input_rejects_empty_actor():
    """D-07: empty actor string raises ValidationError before tool body runs."""
    with pytest.raises(ValidationError):
        ApproveStagedInput(id="some-uuid", actor="")


def test_reject_staged_input_rejects_empty_actor():
    """D-07: empty actor string on reject raises ValidationError."""
    with pytest.raises(ValidationError):
        RejectStagedInput(id="some-uuid", actor="")


def test_approve_staged_input_rejects_missing_actor():
    """D-07: missing actor field (required) raises ValidationError."""
    with pytest.raises(ValidationError):
        ApproveStagedInput(id="some-uuid")


# ─────────────────────────────────────────────────────────────────────────────
# Tool integration tests (require Postgres via session_factory)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_staged_returns_proposed_only(spy_with_staged_data, session_factory):
    """Seed 1 proposed + 1 approved; filter proposed → get exactly 1 record."""
    spy, proposed_op_id = spy_with_staged_data

    # Seed an approved op
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.propose(operation="flame.test", proposer="tester", parameters={})
        # Approve the second one we just created — need to fetch it first
        # Since there's only 2, let's approve via a separate call
        ops, _ = await repo.list(status="proposed")
        # The proposed_op_id is the first one, approve the second
        other_ops = [o for o in ops if o.id != proposed_op_id]
        if other_ops:
            await repo.approve(other_ops[0].id, approver="mcp:test")
        await session.commit()

    result = await spy.tools["forge_list_staged"](ListStagedInput(status="proposed"))
    decoded = json.loads(result)
    assert "data" in decoded
    assert all(r["status"] == "proposed" for r in decoded["data"])


@pytest.mark.asyncio
async def test_list_staged_clamps_limit(spy_with_staged_data):
    """D-05: limit=1000 is silently clamped to 500."""
    spy, _ = spy_with_staged_data
    result = await spy.tools["forge_list_staged"](ListStagedInput(limit=1000))
    decoded = json.loads(result)
    assert decoded["meta"]["limit"] == 500


@pytest.mark.asyncio
async def test_list_staged_unknown_status_returns_envelope(spy_with_staged_data):
    """Unknown status returns error envelope with code 'invalid_filter'."""
    spy, _ = spy_with_staged_data
    result = await spy.tools["forge_list_staged"](ListStagedInput(status="foo"))
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "invalid_filter"


@pytest.mark.asyncio
async def test_list_staged_bad_project_id_returns_envelope(spy_with_staged_data):
    """Malformed project_id returns error envelope with code 'bad_request'."""
    spy, _ = spy_with_staged_data
    result = await spy.tools["forge_list_staged"](
        ListStagedInput(project_id="not-a-uuid")
    )
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "bad_request"


@pytest.mark.asyncio
async def test_get_staged_returns_record(spy_with_staged_data):
    """Known op UUID → data contains record with matching id."""
    spy, op_id = spy_with_staged_data
    result = await spy.tools["forge_get_staged"](GetStagedInput(id=str(op_id)))
    decoded = json.loads(result)
    assert decoded["data"]["id"] == str(op_id)


@pytest.mark.asyncio
async def test_get_staged_unknown_returns_null_data(spy_with_staged_data):
    """Unknown UUID → data is None (NOT an error envelope per MCP convention)."""
    spy, _ = spy_with_staged_data
    bogus = uuid.uuid4()
    result = await spy.tools["forge_get_staged"](GetStagedInput(id=str(bogus)))
    decoded = json.loads(result)
    assert decoded["data"] is None


@pytest.mark.asyncio
async def test_get_staged_malformed_uuid_returns_envelope(spy_with_staged_data):
    """Malformed UUID → error envelope with code 'bad_request'."""
    spy, _ = spy_with_staged_data
    result = await spy.tools["forge_get_staged"](GetStagedInput(id="not-a-uuid"))
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "bad_request"


@pytest.mark.asyncio
async def test_approve_staged_advances_status(spy_with_staged_data):
    """Approve a proposed op → status becomes 'approved', approver is recorded."""
    spy, op_id = spy_with_staged_data
    result = await spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(op_id), actor="mcp:test")
    )
    decoded = json.loads(result)
    assert decoded["data"]["status"] == "approved"
    assert decoded["data"]["approver"] == "mcp:test"


@pytest.mark.asyncio
async def test_re_approve_staged_returns_illegal_transition(spy_with_staged_data):
    """Re-approving an already-approved op → illegal_transition error with current_status."""
    spy, op_id = spy_with_staged_data
    # First approval
    await spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(op_id), actor="mcp:test")
    )
    # Second approval — should fail
    result = await spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(op_id), actor="mcp:test")
    )
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "illegal_transition"
    assert decoded["error"]["current_status"] == "approved"


@pytest.mark.asyncio
async def test_approve_staged_unknown_returns_not_found(spy_with_staged_data):
    """Unknown UUID → staged_op_not_found error."""
    spy, _ = spy_with_staged_data
    bogus = uuid.uuid4()
    result = await spy.tools["forge_approve_staged"](
        ApproveStagedInput(id=str(bogus), actor="mcp:test")
    )
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "staged_op_not_found"


@pytest.mark.asyncio
async def test_approve_staged_bad_uuid_returns_envelope(spy_with_staged_data):
    """Malformed UUID → bad_request error."""
    spy, _ = spy_with_staged_data
    result = await spy.tools["forge_approve_staged"](
        ApproveStagedInput(id="not-a-uuid", actor="mcp:test")
    )
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "bad_request"


@pytest.mark.asyncio
async def test_reject_staged_advances_status(spy_with_staged_data):
    """Reject a proposed op → status becomes 'rejected'."""
    spy, op_id = spy_with_staged_data
    result = await spy.tools["forge_reject_staged"](
        RejectStagedInput(id=str(op_id), actor="mcp:test")
    )
    decoded = json.loads(result)
    assert decoded["data"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_re_reject_staged_returns_illegal_transition(spy_with_staged_data):
    """Re-rejecting a rejected op → illegal_transition error with current_status."""
    spy, op_id = spy_with_staged_data
    # First rejection
    await spy.tools["forge_reject_staged"](
        RejectStagedInput(id=str(op_id), actor="mcp:test")
    )
    # Second rejection — should fail
    result = await spy.tools["forge_reject_staged"](
        RejectStagedInput(id=str(op_id), actor="mcp:test")
    )
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "illegal_transition"
    assert decoded["error"]["current_status"] == "rejected"


@pytest.mark.asyncio
async def test_reject_staged_unknown_returns_not_found(spy_with_staged_data):
    """Unknown UUID → staged_op_not_found error."""
    spy, _ = spy_with_staged_data
    bogus = uuid.uuid4()
    result = await spy.tools["forge_reject_staged"](
        RejectStagedInput(id=str(bogus), actor="mcp:test")
    )
    decoded = json.loads(result)
    assert decoded["error"]["code"] == "staged_op_not_found"
