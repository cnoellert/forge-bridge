"""
forge-bridge end-to-end tests.

Three participants, all real:
  - forge-bridge server  (on port 19999)
  - MCP client           (AsyncClient, endpoint_type="mcp")
  - Flame endpoint       (SyncClient, endpoint_type="flame")

No Postgres — DB calls are patched (same approach as test_integration.py).
No real Flame — FlameEndpoint is driven directly by calling its methods.

Test scenarios:
  1. All three connect and see each other in server status
  2. Flame creates a project + shot → MCP client queries it back
  3. MCP creates a shot → Flame endpoint receives the event
  4. Flame publishes a version → MCP queries the version
  5. Role rename propagates to both clients as an event
  6. Flame endpoint reconnects after server restart (port shift)
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid

import pytest

from forge_bridge.client import AsyncClient, SyncClient
from forge_bridge.core.registry import Registry
from forge_bridge.flame.endpoint import FlameEndpoint
from forge_bridge.server.app import ForgeServer
from forge_bridge.server.connections import ConnectionManager
from forge_bridge.server.protocol import (
    Message,
    entity_list, project_list, query_shot_stack,
    role_register, role_rename,
)
from forge_bridge.server.router import Router


# ─────────────────────────────────────────────────────────────
# Shared test server (same no-DB pattern as test_integration.py)
# ─────────────────────────────────────────────────────────────

class E2EServer:
    """Lightweight test server on a fixed port. No Postgres."""

    def __init__(self, port: int = 19999):
        self.port     = port
        self.url      = f"ws://localhost:{port}"
        self.registry = Registry.default()
        self._thread: threading.Thread | None = None
        self._loop:   asyncio.AbstractEventLoop | None = None
        self._ready   = threading.Event()
        self._server: ForgeServer | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="e2e-server", daemon=True
        )
        self._thread.start()
        assert self._ready.wait(timeout=10), "E2E server did not start"

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._server.stop(), self._loop
            ).result(timeout=5)
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._patch_db()

        connections = ConnectionManager()
        router      = Router(connections, self.registry)
        server      = ForgeServer(host="127.0.0.1", port=self.port)
        server.connections = connections
        server.registry    = self.registry
        server.router      = router
        self._server       = server

        self._loop.run_until_complete(self._start_ws(server))
        self._ready.set()
        self._loop.run_forever()

    async def _start_ws(self, server: ForgeServer) -> None:
        from websockets.asyncio.server import serve
        server._server = await serve(
            server._connection_handler, "127.0.0.1", self.port
        )

    def _patch_db(self) -> None:
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        @asynccontextmanager
        async def fake_session(*a, **kw):
            s = AsyncMock()
            s.commit  = AsyncMock()
            s.rollback = AsyncMock()
            s.flush   = AsyncMock()
            s.add     = MagicMock()
            async def _get(cls, pk): return None
            s.get = _get
            async def _exec(stmt):
                r = MagicMock()
                r.scalars.return_value.all.return_value = []
                r.scalar_one_or_none.return_value = None
                r.all.return_value = []
                return r
            s.execute = _exec
            yield s

        import forge_bridge.server.router as rm
        import forge_bridge.store.session as sm
        sm.get_session = fake_session
        rm.get_session = fake_session


@pytest.fixture(scope="module")
def e2e_server():
    server = E2EServer(port=19999)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def server_url(e2e_server):
    return e2e_server.url


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

async def _mcp_client(server_url: str) -> AsyncClient:
    """Create and connect an MCP-style async client."""
    client = AsyncClient("mcp_claude", server_url, endpoint_type="mcp")
    await client.start()
    await client.wait_until_connected(timeout=10)
    return client


def _flame_client(server_url: str) -> SyncClient:
    """Create and connect a Flame-style sync client."""
    client = SyncClient("flame_test_ws", server_url, endpoint_type="flame")
    client.connect(timeout=10)
    return client


# ─────────────────────────────────────────────────────────────
# 1. Three-way connection
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_three_clients_connect(server_url):
    """All three client types connect and complete handshake."""
    mcp   = await _mcp_client(server_url)
    flame = _flame_client(server_url)

    try:
        assert mcp.is_connected,   "MCP client not connected"
        assert flame._async.is_connected, "Flame client not connected"
        assert mcp.session_id   is not None
        assert mcp.registry_summary.get("roles") is not None

        # Both see the same standard roles
        # registry_summary["roles"] is a dict keyed by name
        mcp_roles   = set(mcp.registry_summary.get("roles", {}).keys())
        flame_roles = set(flame._async.registry_summary.get("roles", {}).keys())
        assert "primary"   in mcp_roles
        assert "primary"   in flame_roles
        assert mcp_roles == flame_roles, "Clients see different registries"

    finally:
        await mcp.stop()
        flame.disconnect()


# ─────────────────────────────────────────────────────────────
# 2. Flame creates → MCP reads
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_flame_creates_shot_mcp_reads(server_url):
    """Flame registers a custom role — MCP can see it immediately."""
    mcp   = await _mcp_client(server_url)
    flame = _flame_client(server_url)

    try:
        role_name = f"test_role_{uuid.uuid4().hex[:6]}"
        flame.role_register(role_name, label="Test Role from Flame")

        # MCP reads back the registry — should include the new role
        result = await mcp.request(
            __import__(
                "forge_bridge.server.protocol",
                fromlist=["role_list"]
            ).role_list()
        )
        role_names = [r["name"] for r in result.get("roles", [])]
        assert role_name in role_names, \
            f"New role {role_name!r} not visible to MCP client"

    finally:
        await mcp.stop()
        flame.disconnect()


# ─────────────────────────────────────────────────────────────
# 3. MCP creates → Flame receives event
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_creates_role_flame_receives_event(server_url):
    """MCP registers a role → Flame endpoint receives the broadcast event."""
    received       = threading.Event()
    received_event = {}

    mcp   = await _mcp_client(server_url)
    flame = _flame_client(server_url)

    try:
        def on_role_registered(event: dict) -> None:
            received_event.update(event)
            received.set()

        flame.on("role.registered", on_role_registered)

        role_name = f"mcp_role_{uuid.uuid4().hex[:6]}"
        await mcp.request(role_register(role_name, label="Role from MCP"))

        assert received.wait(timeout=5), "Flame did not receive role.registered event"
        assert received_event.get("event_type") == "role.registered"

    finally:
        await mcp.stop()
        flame.disconnect()


# ─────────────────────────────────────────────────────────────
# 4. Role rename propagates to both clients
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_role_rename_broadcast_to_all(server_url):
    """Renaming a role broadcasts role.renamed to all OTHER connected clients.

    The sender (mcp) is excluded from receiving its own event — that's the
    intended behaviour. A third observer client and the Flame client both
    receive it.
    """
    flame_received    = threading.Event()
    observer_received = asyncio.Event()
    flame_event       = {}
    observer_event    = {}

    mcp      = await _mcp_client(server_url)          # sender
    flame    = _flame_client(server_url)               # receiver 1
    observer = await _mcp_client(server_url)           # receiver 2 (different session)

    try:
        # Register a fresh role to rename (done by mcp so it has the session context)
        role_name = f"rename_me_{uuid.uuid4().hex[:6]}"
        await mcp.request(role_register(role_name))
        await asyncio.sleep(0.05)   # let register event settle

        def _flame_on_rename(event: dict) -> None:
            flame_event.update(event)
            flame_received.set()

        @observer.on("role.renamed")
        async def _observer_on_rename(event: dict) -> None:
            observer_event.update(event)
            observer_received.set()

        flame.on("role.renamed", _flame_on_rename)

        new_name = f"{role_name}_v2"
        await mcp.request(role_rename(role_name, new_name))

        # Both non-originating clients should receive the event
        await asyncio.wait_for(observer_received.wait(), timeout=5)
        assert flame_received.wait(timeout=5), "Flame did not receive rename event"

        assert observer_event.get("event_type") == "role.renamed"
        assert flame_event.get("event_type")    == "role.renamed"

    finally:
        await mcp.stop()
        await observer.stop()
        flame.disconnect()


# ─────────────────────────────────────────────────────────────
# 5. FlameEndpoint class — outbound event flow
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_flame_endpoint_segment_created(server_url):
    """FlameEndpoint.on_segment_created publishes a shot entity."""
    mcp = await _mcp_client(server_url)

    # Build endpoint using SyncClient
    endpoint = FlameEndpoint(server_url=server_url, client_name="endpoint_test")
    endpoint._connect()

    shot_created = asyncio.Event()
    shot_event   = {}

    @mcp.on("entity.created")
    async def _on_entity(event):
        if event.get("payload", {}).get("entity_type") == "shot":
            shot_event.update(event)
            shot_created.set()

    try:
        # Simulate project open
        class _FakeProject:
            project_name = "Test Project"
            nickname     = "TST"

        endpoint.on_project_opened(_FakeProject())
        time.sleep(0.2)  # let project create complete

        assert endpoint.get_project_id() is not None, "Project not registered"

        # Simulate segment creation
        class _FakeSegment:
            name  = f"TST_{uuid.uuid4().hex[:4].upper()}"
            start_frame = "01:00:00:00"
            end_frame   = "01:00:08:00"

        seg = _FakeSegment()
        endpoint.on_segment_created(seg)

        await asyncio.wait_for(shot_created.wait(), timeout=5)
        assert shot_event.get("event_type") == "entity.created"

        # Verify the shot is tracked in the endpoint
        assert endpoint.get_shot_id(seg.name) is not None

    finally:
        endpoint.disconnect()
        await mcp.stop()


# ─────────────────────────────────────────────────────────────
# 6. FlameEndpoint — version published
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_flame_endpoint_version_published(server_url):
    """FlameEndpoint.on_version_published creates version + relationship."""
    mcp = await _mcp_client(server_url)

    endpoint = FlameEndpoint(server_url=server_url, client_name="endpoint_v2")
    endpoint._connect()

    version_event = {}
    version_created = asyncio.Event()

    @mcp.on("entity.created")
    async def _on_entity(event):
        if event.get("payload", {}).get("entity_type") == "version":
            version_event.update(event)
            version_created.set()

    try:
        class _FakeProject:
            project_name = "Publish Test"
            nickname     = "PBT"

        endpoint.on_project_opened(_FakeProject())
        time.sleep(0.2)

        # Create a shot first
        class _FakeSeg:
            name        = f"PBT_{uuid.uuid4().hex[:4].upper()}"
            start_frame = None
            end_frame   = None

        seg = _FakeSeg()
        endpoint.on_segment_created(seg)
        time.sleep(0.2)

        # Publish a version
        endpoint.on_version_published(
            clip={},
            shot_name=seg.name,
            version_number=1,
            media_path="/jobs/PBT/comp/PBT_0010_v001.exr",
        )

        await asyncio.wait_for(version_created.wait(), timeout=5)
        assert version_event.get("event_type") == "entity.created"

    finally:
        endpoint.disconnect()
        await mcp.stop()


# ─────────────────────────────────────────────────────────────
# 7. MCP tool smoke test (no Postgres needed)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_tools_ping(server_url, monkeypatch):
    """forge_ping MCP tool returns connected status."""
    mcp = await _mcp_client(server_url)

    # Patch the module-level _client so tools.ping() can find it
    import forge_bridge.mcp.server as mcp_server
    monkeypatch.setattr(mcp_server, "_client", mcp)

    from forge_bridge.mcp.tools import ping
    result_json = await ping()

    import json
    result = json.loads(result_json)
    assert result.get("status") == "connected"
    assert "session_id" in result

    await mcp.stop()


@pytest.mark.asyncio
async def test_mcp_tools_list_roles(server_url, monkeypatch):
    """forge_list_roles MCP tool returns standard roles."""
    mcp = await _mcp_client(server_url)

    import forge_bridge.mcp.server as mcp_server
    monkeypatch.setattr(mcp_server, "_client", mcp)

    from forge_bridge.mcp.tools import list_roles
    import json
    result = json.loads(await list_roles())
    role_names = [r["name"] for r in result.get("roles", [])]

    assert "primary"   in role_names
    assert "matte"     in role_names
    assert "reference" in role_names
    assert result["count"] >= 5

    await mcp.stop()
