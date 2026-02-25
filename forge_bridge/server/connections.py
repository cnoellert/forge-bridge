"""
forge-bridge connection manager.

Tracks every connected WebSocket client. Handles:
  - Registration on connect / cleanup on disconnect
  - Project subscriptions (who gets which events)
  - Targeted sends and project-wide broadcasts
  - Reconnect catch-up (replay missed events)

The ConnectionManager is a singleton held by the server application.
It has no database access — it only knows about live connections.
The router calls it to send messages; it doesn't call the router.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from forge_bridge.server.protocol import Message, MsgType, event as make_event

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Connected client state
# ─────────────────────────────────────────────────────────────

@dataclass
class ConnectedClient:
    """Everything the server knows about one live connection.

    session_id   — the UUID written to the sessions table in Postgres
    ws           — the live WebSocket connection
    client_name  — self-reported name ("flame_a", "mcp_claude", etc.)
    endpoint_type — "flame", "mcp", "maya", "unknown"
    subscriptions — project UUIDs this client wants events for
    last_event_id — most recent event ID sent to this client
                    (used for catch-up on reconnect)
    """
    session_id:    uuid.UUID
    ws:            WebSocketServerProtocol
    client_name:   str
    endpoint_type: str = "unknown"
    subscriptions: set[uuid.UUID] = field(default_factory=set)
    last_event_id: str | None = None

    @property
    def remote_address(self) -> str:
        try:
            host, port = self.ws.remote_address
            return f"{host}:{port}"
        except Exception:
            return "unknown"

    async def send(self, msg: Message) -> bool:
        """Send a message to this client. Returns False if the send failed."""
        try:
            await self.ws.send(msg.serialize())
            return True
        except (websockets.exceptions.ConnectionClosed,
                websockets.exceptions.WebSocketException) as e:
            logger.debug(f"Send failed to {self.client_name}: {e}")
            return False

    def subscribes_to(self, project_id: uuid.UUID) -> bool:
        return project_id in self.subscriptions or len(self.subscriptions) == 0
        # Empty subscriptions = wildcard — receives all project events
        # This is the default state after hello until the first subscribe message


# ─────────────────────────────────────────────────────────────
# Connection Manager
# ─────────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages all live WebSocket connections.

    Thread-safety: designed for asyncio. All methods are coroutines or
    are called from a single event loop. No locks needed.
    """

    def __init__(self):
        # session_id → ConnectedClient
        self._clients: dict[uuid.UUID, ConnectedClient] = {}
        # project_id → set of session_ids subscribed to it
        self._project_subs: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)

    # ── Connection lifecycle ──────────────────────────────────

    def register(
        self,
        session_id: uuid.UUID,
        ws: WebSocketServerProtocol,
        client_name: str,
        endpoint_type: str = "unknown",
        last_event_id: str | None = None,
    ) -> ConnectedClient:
        """Register a new connection. Called after hello/welcome handshake."""
        client = ConnectedClient(
            session_id=session_id,
            ws=ws,
            client_name=client_name,
            endpoint_type=endpoint_type,
            last_event_id=last_event_id,
        )
        self._clients[session_id] = client
        logger.info(
            f"Client connected: {client_name!r} ({endpoint_type}) "
            f"from {client.remote_address} — session {session_id!s:.8}..."
        )
        return client

    def unregister(self, session_id: uuid.UUID) -> ConnectedClient | None:
        """Remove a connection. Called on disconnect."""
        client = self._clients.pop(session_id, None)
        if client:
            # Clean up all subscription indexes
            for project_id in list(client.subscriptions):
                self._project_subs[project_id].discard(session_id)
            logger.info(
                f"Client disconnected: {client.client_name!r} "
                f"session {session_id!s:.8}..."
            )
        return client

    def get(self, session_id: uuid.UUID) -> ConnectedClient | None:
        return self._clients.get(session_id)

    def all_clients(self) -> list[ConnectedClient]:
        return list(self._clients.values())

    @property
    def count(self) -> int:
        return len(self._clients)

    # ── Subscriptions ─────────────────────────────────────────

    def subscribe(self, session_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Subscribe a client to events for a project."""
        client = self._clients.get(session_id)
        if client:
            client.subscriptions.add(project_id)
            self._project_subs[project_id].add(session_id)
            logger.debug(f"{client.client_name!r} subscribed to project {project_id!s:.8}...")

    def unsubscribe(self, session_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Unsubscribe a client from a project's events."""
        client = self._clients.get(session_id)
        if client:
            client.subscriptions.discard(project_id)
            self._project_subs[project_id].discard(session_id)

    # ── Sending ───────────────────────────────────────────────

    async def send_to(self, session_id: uuid.UUID, msg: Message) -> bool:
        """Send a message to one specific client by session ID."""
        client = self._clients.get(session_id)
        if not client:
            return False
        return await client.send(msg)

    async def broadcast(
        self,
        msg: Message,
        project_id: uuid.UUID | None = None,
        exclude: uuid.UUID | None = None,
    ) -> int:
        """Broadcast a message to multiple clients.

        If project_id is given, sends only to clients subscribed to that project.
        If project_id is None, sends to all connected clients.
        exclude: session_id of the originating client (don't echo back to sender).

        Returns the number of clients successfully reached.
        """
        if project_id is not None:
            # Send to subscribers of this project
            target_ids = self._project_subs.get(project_id, set())
            # Also send to wildcard clients (subscriptions is empty set)
            wildcards = {
                sid for sid, c in self._clients.items()
                if len(c.subscriptions) == 0
            }
            target_ids = target_ids | wildcards
        else:
            target_ids = set(self._clients.keys())

        if exclude:
            target_ids = target_ids - {exclude}

        if not target_ids:
            return 0

        results = await asyncio.gather(
            *[self._clients[sid].send(msg)
              for sid in target_ids
              if sid in self._clients],
            return_exceptions=True,
        )

        sent = sum(1 for r in results if r is True)
        return sent

    async def broadcast_event(
        self,
        event_type: str,
        payload: dict,
        project_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        originator_session_id: uuid.UUID | None = None,
        event_id: str | None = None,
    ) -> int:
        """Build and broadcast an event message.

        This is the primary method the router uses to notify clients
        of state changes. Returns number of clients notified.
        """
        msg = make_event(
            event_type=event_type,
            payload=payload,
            project_id=str(project_id) if project_id else None,
            entity_id=str(entity_id)   if entity_id  else None,
            event_id=event_id,
        )

        # Update last_event_id for all recipients
        if event_id:
            for client in self._clients.values():
                if client.subscribes_to(project_id) if project_id else True:
                    client.last_event_id = event_id

        return await self.broadcast(
            msg,
            project_id=project_id,
            exclude=originator_session_id,
        )

    # ── Status ────────────────────────────────────────────────

    def status(self) -> dict:
        """Return a summary of current connection state."""
        return {
            "total_connections": self.count,
            "clients": [
                {
                    "session_id":    str(c.session_id),
                    "client_name":   c.client_name,
                    "endpoint_type": c.endpoint_type,
                    "address":       c.remote_address,
                    "subscriptions": [str(p) for p in c.subscriptions],
                }
                for c in self._clients.values()
            ],
        }
