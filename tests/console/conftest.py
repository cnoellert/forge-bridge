"""Shared fixtures for tests/console/ — FB-B HTTP handler integration tests.

Shared fixtures extracted here per PLAN.md Task 2 Claude's Discretion directive:
both test_staged_handlers_list.py and test_staged_handlers_writes.py use these
to avoid duplication.

Requires: session_factory fixture from tests/conftest.py (Phase 13 deliverable).
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from unittest.mock import MagicMock
import httpx
from httpx import ASGITransport

from forge_bridge.console._memory import _MEMORY
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.store.staged_operations import StagedOpRepo


@pytest.fixture(autouse=True)
def _reset_tool_memory():
    """PR26 — clear the process-global tool-argument memory before AND
    after every test in tests/console/.

    The chain resolver (`forge_bridge.console._tool_chain`) writes
    deterministically-resolved values (today: ``project_id``) into a
    module-level ``_MEMORY`` instance that survives across HTTP
    requests within a single server process. In production that's the
    UX win; in tests it's cross-test pollution — a single-project test
    seeds memory that a subsequent zero-projects test would silently
    inherit, masking regressions.

    Autouse + before/after clear keeps every console test running
    against a known-empty memory regardless of order or selection.
    """
    _MEMORY.clear()
    yield
    _MEMORY.clear()


@pytest_asyncio.fixture
async def staged_client(session_factory):
    """httpx.AsyncClient wired to a real session_factory + ConsoleReadAPI via ASGITransport.

    Phase 18 HARNESS-01 migration (was starlette.testclient.TestClient — its private
    sync event loop conflicted with asyncpg's session loop, masking 22 of 23 console
    staged tests with `RuntimeError: got Future ... attached to a different loop`).
    Use this fixture when the test seeds its own data.
    """
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        session_factory=session_factory,
    )
    app = build_console_app(api, session_factory=session_factory)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def proposed_op_id(session_factory):
    """Seed one proposed op and return its UUID."""
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(operation="flame.publish", proposer="seed", parameters={})
        await session.commit()
    return op.id


@pytest_asyncio.fixture
async def approved_op_id(session_factory, proposed_op_id):
    """Seed one proposed op then approve it; return the UUID."""
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(proposed_op_id, approver="seed")
        await session.commit()
    return proposed_op_id


@pytest_asyncio.fixture
async def rejected_op_id(session_factory, proposed_op_id):
    """Seed one proposed op then reject it; return the UUID."""
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.reject(proposed_op_id, actor="seed")
        await session.commit()
    return proposed_op_id
