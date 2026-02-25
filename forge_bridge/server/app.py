"""
forge-bridge server application.

Entry point: python -m forge_bridge.server

Lifecycle:
  1. Start — connect to Postgres, restore registry, bind WebSocket port
  2. Run   — accept connections, dispatch messages via Router
  3. Stop  — close all connections cleanly, close DB pool

Each connected client gets its own asyncio task running the
connection loop. The Router is shared and stateless per-message.
The ConnectionManager is shared and tracks all live connections.

Configuration via environment variables:

    FORGE_DB_URL      PostgreSQL connection URL (async asyncpg)
    FORGE_HOST        Bind host (default: 0.0.0.0)
    FORGE_PORT        Bind port (default: 9998)
    FORGE_LOG_LEVEL   Logging level (default: INFO)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import uuid
from typing import Any

import websockets
from websockets.asyncio.server import serve, ServerConnection

from forge_bridge.server.connections import ConnectionManager
from forge_bridge.server.protocol import (
    Message, MsgType,
    error, ErrorCode, welcome,
)
from forge_bridge.server.router import Router
from forge_bridge.store.repo import ClientSessionRepo, RegistryRepo
from forge_bridge.store.session import create_tables, get_session

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────

class ForgeServer:
    """The forge-bridge WebSocket server.

    Holds:
        connections  — ConnectionManager (who is connected)
        router       — Router (handles all message types)
        registry     — Registry (in-memory, shared with Router)
    """

    VERSION = "0.1.0"

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9998,
    ):
        self.host = host
        self.port = port
        self.connections = ConnectionManager()
        self.registry    = None   # populated on startup
        self.router      = None   # populated on startup
        self._server     = None
        self._shutdown   = asyncio.Event()

    # ── Lifecycle ─────────────────────────────────────────────

    async def start(self) -> None:
        """Initialize the server — connect to DB, load registry, bind socket."""
        logger.info(f"forge-bridge server v{self.VERSION} starting...")

        # Ensure tables exist (idempotent — safe to run every startup)
        await create_tables()
        logger.info("Database tables verified.")

        # Restore registry from Postgres
        async with get_session() as session:
            repo = RegistryRepo(session)
            self.registry = await repo.restore_registry()

        role_count    = len(self.registry.roles.names())
        reltype_count = len(self.registry.relationships.names())
        logger.info(
            f"Registry loaded: {role_count} roles, {reltype_count} relationship types."
        )

        # Build the router with the live registry
        self.router = Router(self.connections, self.registry)

        # Bind the WebSocket server
        self._server = await serve(
            self._connection_handler,
            self.host,
            self.port,
            ping_interval=30,    # send WebSocket pings every 30s
            ping_timeout=10,     # disconnect if no pong within 10s
            max_size=10 * 1024 * 1024,  # 10MB max message size
        )

        logger.info(f"Listening on ws://{self.host}:{self.port}")

    async def run_forever(self) -> None:
        """Run until a shutdown signal is received."""
        await self.start()

        # Register OS signal handlers for clean shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._request_shutdown)

        logger.info("Server ready. Press Ctrl+C to stop.")
        await self._shutdown.wait()
        await self.stop()

    def _request_shutdown(self) -> None:
        logger.info("Shutdown signal received.")
        self._shutdown.set()

    async def stop(self) -> None:
        """Graceful shutdown — close all connections then the server socket."""
        logger.info("Shutting down...")

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Mark all sessions as disconnected
        if self.connections.count > 0:
            logger.info(f"Closing {self.connections.count} active connections...")
            async with get_session() as session:
                repo = ClientSessionRepo(session)
                for client in self.connections.all_clients():
                    await repo.close(client.session_id)

        logger.info("Server stopped.")

    # ── Connection handler ────────────────────────────────────

    async def _connection_handler(
        self,
        ws: ServerConnection,
    ) -> None:
        """Manage one client connection from connect to disconnect.

        This coroutine runs as a separate asyncio task per connection.
        It:
          1. Waits for the hello message
          2. Registers the client
          3. Runs the message loop until disconnect
          4. Cleans up on exit
        """
        client = None
        try:
            # Step 1: Expect hello as first message
            client = await self._handshake(ws)
            if client is None:
                return   # handshake failed, ws already closed

            # Step 2: Message loop
            await self._message_loop(ws, client)

        except websockets.exceptions.ConnectionClosed:
            pass  # normal disconnect
        except Exception as e:
            logger.exception(f"Unexpected error in connection handler: {e}")
        finally:
            if client:
                self.connections.unregister(client.session_id)
                async with get_session() as session:
                    await ClientSessionRepo(session).close(client.session_id)

    async def _handshake(
        self,
        ws: ServerConnection,
    ):
        """Wait for a hello message and register the client.

        Returns the ConnectedClient on success, None on failure.
        """
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning(f"Connection from {ws.remote_address} timed out waiting for hello")
            await ws.close()
            return None

        try:
            msg = Message.parse(raw)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Malformed hello message: {e}")
            await ws.close()
            return None

        if msg.type != MsgType.HELLO:
            logger.warning(f"Expected hello, got {msg.type!r}")
            err = error(msg.msg_id, ErrorCode.INVALID, "First message must be hello")
            await ws.send(err.serialize())
            await ws.close()
            return None

        session_id = uuid.uuid4()
        client = self.connections.register(
            session_id=session_id,
            ws=ws,
            client_name=msg.get("client_name", "unknown"),
            endpoint_type=msg.get("endpoint_type", "unknown"),
            last_event_id=msg.get("last_event_id"),
        )

        # Send welcome
        reply = welcome(
            session_id=str(session_id),
            request_id=msg.msg_id,
            server_version=self.VERSION,
            registry_summary=self.registry.summary(),
        )
        await ws.send(reply.serialize())

        # If reconnecting, replay missed events
        last_event_id = msg.get("last_event_id")
        if last_event_id:
            await self._replay_missed_events(ws, last_event_id)

        return client

    async def _replay_missed_events(
        self,
        ws: ServerConnection,
        last_event_id: str,
    ) -> None:
        """Send any events the client missed since last_event_id."""
        try:
            async with get_session() as session:
                missed = await __import__(
                    "forge_bridge.store.repo", fromlist=["EventRepo"]
                ).EventRepo(session).get_since_sequence(
                    uuid.UUID(last_event_id)
                )

            for db_event in missed:
                from forge_bridge.server.protocol import event as make_event
                msg = make_event(
                    event_type=db_event.event_type,
                    payload=db_event.payload,
                    project_id=str(db_event.project_id) if db_event.project_id else None,
                    entity_id=str(db_event.entity_id)   if db_event.entity_id  else None,
                    event_id=str(db_event.id),
                )
                await ws.send(msg.serialize())

            if missed:
                logger.info(
                    f"Replayed {len(missed)} missed event(s) to reconnecting client"
                )
        except Exception as e:
            logger.warning(f"Failed to replay missed events: {e}")

    async def _message_loop(
        self,
        ws: ServerConnection,
        client,
    ) -> None:
        """Receive and dispatch messages until the connection closes."""
        async for raw in ws:
            try:
                msg = Message.parse(raw)
            except (ValueError, json.JSONDecodeError) as e:
                err = error(None, ErrorCode.INVALID, f"Malformed message: {e}")
                await ws.send(err.serialize())
                continue

            # Dispatch to router
            reply = await self.router.dispatch(msg, client)

            if reply is not None:
                await ws.send(reply.serialize())

            # Clean disconnect
            if msg.type == MsgType.BYE:
                await ws.close()
                break


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point: python -m forge_bridge.server"""
    log_level = os.environ.get("FORGE_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    host = os.environ.get("FORGE_HOST", "0.0.0.0")
    port = int(os.environ.get("FORGE_PORT", "9998"))

    server = ForgeServer(host=host, port=port)

    asyncio.run(server.run_forever())


if __name__ == "__main__":
    main()
