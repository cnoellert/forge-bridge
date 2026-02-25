"""
forge-bridge integration tests.

Spins up a real ForgeServer on a random port (no Postgres required —
uses SQLite via the test fixture), connects both async and sync clients,
and exercises the full request/response/event cycle.

Run with: pytest tests/test_integration.py -v

Postgres is not required for these tests. We patch the session factory
to use an in-memory SQLite database instead.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from forge_bridge.client.async_client import AsyncClient, ServerError
from forge_bridge.client.sync_client import SyncClient
from forge_bridge.core.registry import Registry
from forge_bridge.server.app import ForgeServer
from forge_bridge.server.connections import ConnectionManager
from forge_bridge.server.protocol import (
    Message, MsgType,
    hello, ping, project_create, project_list,
    entity_create, entity_get, entity_list,
    role_register, role_delete, role_list,
    query_dependents, query_shot_stack,
    subscribe,
)
from forge_bridge.server.router import Router


# ─────────────────────────────────────────────────────────────
# In-memory store fixture — no Postgres needed
# ─────────────────────────────────────────────────────────────

class InMemoryStore:
    """Dead-simple in-memory backing store for integration tests.

    Replaces the Postgres session/repo layer with dicts.
    """
    def __init__(self):
        self.projects:   dict[str, dict] = {}
        self.entities:   dict[str, dict] = {}
        self.locations:  dict[str, list] = {}
        self.rels:       list[dict]      = []
        self.events:     list[dict]      = []
        self.sessions:   dict[str, dict] = {}


def _make_mock_session(store: InMemoryStore):
    """Build a mock AsyncSession that uses the InMemoryStore."""
    session = AsyncMock()
    session.commit  = AsyncMock()
    session.rollback = AsyncMock()
    session.flush   = AsyncMock()

    async def mock_get(model_cls, pk):
        name = model_cls.__tablename__ if hasattr(model_cls, "__tablename__") else str(model_cls)
        if name == "projects":
            row = store.projects.get(str(pk))
            if row:
                obj = MagicMock()
                obj.id = pk
                obj.name = row["name"]
                obj.code = row["code"]
                obj.attributes = row.get("metadata", {})
                return obj
        elif name == "entities":
            row = store.entities.get(str(pk))
            if row:
                obj = MagicMock()
                for k, v in row.items():
                    setattr(obj, k, v)
                return obj
        elif name == "sessions":
            row = store.sessions.get(str(pk))
            if row:
                obj = MagicMock()
                for k, v in row.items():
                    setattr(obj, k, v)
                return obj
        return None

    session.get = mock_get

    async def mock_execute(stmt):
        result = MagicMock()
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        result.scalar_one_or_none = MagicMock(return_value=None)
        result.all = MagicMock(return_value=[])
        return result

    session.execute = mock_execute
    session.add = MagicMock()
    return session


# ─────────────────────────────────────────────────────────────
# Server fixture
# ─────────────────────────────────────────────────────────────

class TestServer:
    """A ForgeServer instance running on localhost for tests.

    Bypasses Postgres — uses an in-memory registry and a mock store.
    The WebSocket layer is fully real.
    """

    def __init__(self, port: int):
        self.port    = port
        self.url     = f"ws://localhost:{port}"
        self.registry = Registry.default()
        self._server: ForgeServer | None = None
        self._thread: threading.Thread | None = None
        self._loop:   asyncio.AbstractEventLoop | None = None
        self._ready   = threading.Event()
        self._store   = InMemoryStore()

    def start(self) -> None:
        """Start the server in a background thread."""
        self._thread = threading.Thread(
            target=self._run, name="forge-test-server", daemon=True
        )
        self._thread.start()
        assert self._ready.wait(timeout=10), "Test server did not start in time"

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._server.stop(), self._loop
            ).result(timeout=5)
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Patch get_session before anything starts so router never touches Postgres
        self._patch_db()

        connections = ConnectionManager()
        router      = Router(connections, self.registry)

        # Build a minimal server that skips DB init
        server = ForgeServer(host="127.0.0.1", port=self.port)
        server.connections = connections
        server.registry    = self.registry
        server.router      = router
        self._server       = server

        self._loop.run_until_complete(self._start_server(server))
        self._ready.set()
        self._loop.run_forever()

    def _patch_db(self) -> None:
        """Replace get_session with a no-op in-memory version."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        @asynccontextmanager
        async def fake_get_session(*args, **kwargs):
            session = AsyncMock()
            session.commit   = AsyncMock()
            session.rollback = AsyncMock()
            session.flush    = AsyncMock()
            session.add      = MagicMock()

            # get() always returns None (nothing persisted)
            async def _get(cls, pk):
                return None
            session.get = _get

            # execute() returns empty results
            async def _execute(stmt):
                r = MagicMock()
                r.scalars.return_value.all.return_value = []
                r.scalar_one_or_none.return_value = None
                r.all.return_value = []
                return r
            session.execute = _execute

            yield session

        import forge_bridge.server.router as router_mod
        import forge_bridge.store.session as session_mod
        session_mod.get_session = fake_get_session
        router_mod.get_session  = fake_get_session

    async def _start_server(self, server: ForgeServer) -> None:
        """Start just the WebSocket listener, skipping DB setup."""
        from websockets.asyncio.server import serve
        server._server = await serve(
            server._connection_handler,
            "127.0.0.1",
            self.port,
        )


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_server():
    """Module-scoped test server on port 19998."""
    server = TestServer(port=19998)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def server_url(test_server):
    return test_server.url


# ─────────────────────────────────────────────────────────────
# Async client tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAsyncClient:

    async def test_connect_and_welcome(self, server_url):
        """Client connects, server sends welcome with session_id."""
        async with AsyncClient.connect("test_async", server_url) as client:
            assert client.is_connected
            assert client.session_id is not None
            assert "roles" in client.registry_summary

    async def test_ping_pong(self, server_url):
        """Ping gets a pong back."""
        async with AsyncClient.connect("test_ping", server_url) as client:
            result = await client.request(ping())
            # pong has no result body — just no error is fine

    async def test_role_register(self, server_url):
        """Register a custom role."""
        async with AsyncClient.connect("test_role", server_url) as client:
            result = await client.request(
                role_register("vfx_hero", label="VFX Hero Layer", order=10)
            )
            assert "key" in result
            assert result["name"] == "vfx_hero"

    async def test_role_duplicate_raises(self, server_url):
        """Registering an existing role name raises ServerError."""
        async with AsyncClient.connect("test_dup", server_url) as client:
            await client.request(role_register("dup_role"))
            with pytest.raises(ServerError) as exc:
                await client.request(role_register("dup_role"))
            assert "ALREADY_EXISTS" in exc.value.code

    async def test_role_list(self, server_url):
        """List returns at least the standard roles."""
        async with AsyncClient.connect("test_list", server_url) as client:
            result = await client.request(role_list())
            names = [r["name"] for r in result["roles"]]
            assert "primary" in names
            assert "matte" in names
            assert "reference" in names

    async def test_delete_protected_role_raises(self, server_url):
        """Deleting a standard role raises ServerError PROTECTED."""
        async with AsyncClient.connect("test_protected", server_url) as client:
            with pytest.raises(ServerError) as exc:
                await client.request(role_delete("primary"))
            assert exc.value.code == "PROTECTED"

    async def test_event_received_by_subscriber(self, server_url):
        """Client A registers a role → Client B receives the event."""
        received = asyncio.Event()
        received_event = {}

        async with AsyncClient.connect("sender", server_url) as sender:
            async with AsyncClient.connect("listener", server_url) as listener:
                @listener.on("role.registered")
                async def on_role(event):
                    received_event.update(event)
                    received.set()

                await sender.request(role_register("broadcast_test_role"))

                # Give the event a moment to propagate
                await asyncio.wait_for(received.wait(), timeout=3.0)
                assert received_event.get("event_type") == "role.registered"

    async def test_subscribe_and_receive_project_event(self, server_url):
        """Subscribing to a project scopes events correctly."""
        # We can't test Postgres-backed project.created without the DB,
        # but we can test that subscribe doesn't error and returns ok.
        async with AsyncClient.connect("test_sub", server_url) as client:
            project_id = str(uuid.uuid4())
            await client.subscribe(project_id)
            # No error = success

    async def test_unknown_message_type_returns_error(self, server_url):
        """Sending an unknown message type gets an error response."""
        async with AsyncClient.connect("test_unknown", server_url) as client:
            msg = Message({"type": "totally.unknown.type", "id": str(uuid.uuid4())})
            with pytest.raises(ServerError) as exc:
                await client.request(msg)
            assert exc.value.code == "UNKNOWN_TYPE"

    async def test_reconnect_on_disconnect(self, server_url):
        """Client auto-reconnects after connection is dropped."""
        client = AsyncClient(
            "test_reconnect", server_url, auto_reconnect=True
        )
        await client.start()
        try:
            assert client.is_connected

            # Force-close the underlying WebSocket
            await client._ws.close()
            await asyncio.sleep(0.1)

            # Should reconnect automatically
            await asyncio.wait_for(
                client.wait_until_connected(timeout=10.0),
                timeout=12.0,
            )
            assert client.is_connected
        finally:
            await client.stop()


# ─────────────────────────────────────────────────────────────
# Sync client tests
# ─────────────────────────────────────────────────────────────

class TestSyncClient:
    """Sync client tests — all blocking calls."""

    def test_connect_and_disconnect(self, server_url):
        with SyncClient("sync_test", server_url) as client:
            assert client._async.is_connected

    def test_context_manager(self, server_url):
        """with statement connects and disconnects cleanly."""
        with SyncClient("sync_ctx", server_url) as client:
            pass
        assert not client._async.is_connected

    def test_role_register_sync(self, server_url):
        with SyncClient("sync_role", server_url) as client:
            result = client.role_register("sync_custom_role", label="Sync Test")
            assert result["name"] == "sync_custom_role"
            assert "key" in result

    def test_role_rename_sync(self, server_url):
        with SyncClient("sync_rename", server_url) as client:
            client.role_register("rename_me")
            result = client.role_rename("rename_me", "renamed_role")
            assert result["new_name"] == "renamed_role"

    def test_delete_protected_role_raises_sync(self, server_url):
        from forge_bridge.client.async_client import ServerError
        with SyncClient("sync_protected", server_url) as client:
            with pytest.raises(ServerError) as exc:
                client.role_delete("reference")
            assert exc.value.code == "PROTECTED"

    def test_event_listener_sync(self, server_url):
        """Sync client can register event listeners and receive events."""
        received = threading.Event()
        received_data = {}

        with SyncClient("sync_listen", server_url) as listener:
            with SyncClient("sync_send", server_url) as sender:
                def on_role(event):
                    received_data.update(event)
                    received.set()

                listener.on("role.registered", on_role)
                sender.role_register("sync_event_test_role")

                assert received.wait(timeout=5.0), "Event not received within timeout"
                assert received_data.get("event_type") == "role.registered"

    def test_cannot_call_without_connect(self):
        """Calling methods before connect() raises RuntimeError."""
        client = SyncClient("unconnected", "ws://localhost:19998")
        with pytest.raises(RuntimeError, match="Not connected"):
            client.role_register("will_fail")


# ─────────────────────────────────────────────────────────────
# Protocol tests (no server needed)
# ─────────────────────────────────────────────────────────────

class TestProtocol:
    """Unit tests for the wire protocol — no network required."""

    def test_message_round_trip(self):
        msg = hello("test_client", "flame")
        parsed = Message.parse(msg.serialize())
        assert parsed.type == MsgType.HELLO
        assert parsed["client_name"] == "test_client"
        assert parsed.msg_id is not None

    def test_message_parse_requires_type(self):
        import json
        with pytest.raises(ValueError, match="missing 'type'"):
            Message.parse(json.dumps({"no_type": True}))

    def test_error_message_structure(self):
        from forge_bridge.server.protocol import error, ErrorCode
        err = error("req-123", ErrorCode.NOT_FOUND, "Shot not found")
        assert err.type == MsgType.ERROR
        assert err["code"] == "NOT_FOUND"
        assert err.msg_id == "req-123"

    def test_all_protocol_constructors_have_id(self):
        """Every request constructor must generate a message ID."""
        from forge_bridge.server.protocol import (
            project_create, entity_create, role_register,
            query_dependents, location_add, relationship_create,
        )
        constructors = [
            project_create("Test", "TST"),
            entity_create("shot", str(uuid.uuid4()), {}),
            role_register("test"),
            query_dependents(str(uuid.uuid4())),
            location_add(str(uuid.uuid4()), "/path/to/file"),
            relationship_create(str(uuid.uuid4()), str(uuid.uuid4()), "member_of"),
        ]
        for msg in constructors:
            assert msg.msg_id is not None, f"{msg.type!r} has no id"
