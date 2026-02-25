"""
forge-bridge async client.

The async client is the foundation. The sync client wraps this.
The MCP server uses this directly.

Design:

  - Connects once, reconnects automatically with backoff
  - Pending requests tracked by message ID — send and await reply
  - Event subscriptions: register callbacks that fire on server push
  - Thread-safe: one asyncio event loop, everything runs there

Usage:

    async with AsyncClient.connect("flame_a", "ws://server:9998") as client:
        # Subscribe to a project
        await client.subscribe(project_id)

        # Create a shot
        result = await client.request(entity_create(
            entity_type="shot",
            project_id=str(project_id),
            name="EP60_010",
            attributes={"sequence_id": str(seq_id)},
        ))
        shot_id = result["entity_id"]

        # Listen for changes
        @client.on("entity.updated")
        async def handle_update(event):
            print(f"Entity updated: {event['entity_id']}")

        await client.run_forever()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Coroutine

import websockets
import websockets.asyncio.client as ws_asyncio
from websockets.connection import State as WsState

from forge_bridge.server.protocol import (
    Message, MsgType, ErrorCode,
    hello, ping, bye, subscribe as make_subscribe, unsubscribe as make_unsubscribe,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class ClientError(Exception):
    """Base error for client operations."""


class ServerError(ClientError):
    """The server returned an error response."""
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code    = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class ConnectionError(ClientError):
    """Could not connect or connection was lost."""


class TimeoutError(ClientError):
    """Request timed out waiting for a response."""


# ─────────────────────────────────────────────────────────────
# Pending request tracking
# ─────────────────────────────────────────────────────────────

class PendingRequest:
    """Tracks one in-flight request waiting for a server response."""
    __slots__ = ("future",)

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.future: asyncio.Future = loop.create_future()

    def resolve(self, msg: Message) -> None:
        if not self.future.done():
            self.future.set_result(msg)

    def reject(self, exc: Exception) -> None:
        if not self.future.done():
            self.future.set_exception(exc)


# ─────────────────────────────────────────────────────────────
# Async Client
# ─────────────────────────────────────────────────────────────

class AsyncClient:
    """Async WebSocket client for forge-bridge.

    Manages a persistent connection to the server, automatic reconnection,
    request/response correlation, and event subscriptions.

    Instantiate with AsyncClient.connect() context manager, or
    create manually and call start()/stop().
    """

    DEFAULT_TIMEOUT      = 30.0    # seconds to wait for a response
    RECONNECT_BASE_DELAY = 1.0     # initial reconnect delay
    RECONNECT_MAX_DELAY  = 60.0    # maximum reconnect delay
    RECONNECT_MULTIPLIER = 2.0     # exponential backoff multiplier

    def __init__(
        self,
        client_name: str,
        server_url: str = "ws://localhost:9998",
        endpoint_type: str = "unknown",
        capabilities: dict | None = None,
        auto_reconnect: bool = True,
        request_timeout: float = DEFAULT_TIMEOUT,
    ):
        self.client_name     = client_name
        self.server_url      = server_url
        self.endpoint_type   = endpoint_type
        self.capabilities    = capabilities or {}
        self.auto_reconnect  = auto_reconnect
        self.request_timeout = request_timeout

        self._ws:              object | None = None  # websockets connection
        self._session_id:      str | None = None
        self._last_event_id:   str | None = None
        self._registry_summary: dict = {}

        # msg_id → PendingRequest
        self._pending: dict[str, PendingRequest] = {}

        # event_type → list of async callbacks
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

        # Subscribed project UUIDs (maintained locally for reconnect)
        self._subscriptions: set[str] = set()

        self._connected    = asyncio.Event()
        self._stopped      = False
        self._recv_task:   asyncio.Task | None = None
        self._reconnect_delay = self.RECONNECT_BASE_DELAY

    # ── Connection lifecycle ──────────────────────────────────

    @classmethod
    @asynccontextmanager
    async def connect(
        cls,
        client_name: str,
        server_url: str = "ws://localhost:9998",
        **kwargs,
    ) -> AsyncGenerator["AsyncClient", None]:
        """Async context manager that connects and disconnects cleanly.

        Usage:
            async with AsyncClient.connect("flame_a") as client:
                result = await client.request(project_list())
        """
        client = cls(client_name, server_url, **kwargs)
        await client.start()
        try:
            yield client
        finally:
            await client.stop()

    async def start(self) -> None:
        """Connect to the server and start the receive loop."""
        await self._connect()
        self._recv_task = asyncio.create_task(
            self._receive_loop(),
            name=f"forge-client-recv-{self.client_name}",
        )

    async def stop(self) -> None:
        """Disconnect cleanly."""
        self._stopped = True
        self._auto_reconnect = False

        if self._ws and getattr(self._ws, 'state', None) == WsState.OPEN:
            try:
                await self._ws.send(bye().serialize())
                await self._ws.close()
            except Exception:
                pass

        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass

        # Reject all pending requests
        for pending in self._pending.values():
            pending.reject(ConnectionError("Client stopped"))
        self._pending.clear()

        logger.info(f"Client {self.client_name!r} disconnected.")

    async def wait_until_connected(self, timeout: float = 15.0) -> None:
        """Block until the handshake completes."""
        await asyncio.wait_for(self._connected.wait(), timeout=timeout)

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and getattr(self._ws, 'state', None) == WsState.OPEN and self._connected.is_set()

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def registry_summary(self) -> dict:
        """The registry state as reported by the server at connect time."""
        return self._registry_summary

    # ── Request/response ──────────────────────────────────────

    async def request(
        self,
        msg: Message,
        timeout: float | None = None,
    ) -> dict:
        """Send a request and wait for the server's response.

        Returns the result dict from the ok response.
        Raises ServerError on error response.
        Raises TimeoutError if no response within timeout seconds.

        Args:
            msg:     A Message object (from protocol constructors).
            timeout: Override the default request timeout.
        """
        if not self.is_connected:
            await self.wait_until_connected()

        if not msg.msg_id:
            raise ClientError("Message has no id — use protocol constructors")

        loop    = asyncio.get_running_loop()
        pending = PendingRequest(loop)
        self._pending[msg.msg_id] = pending

        try:
            await self._ws.send(msg.serialize())
            reply = await asyncio.wait_for(
                pending.future,
                timeout=timeout or self.request_timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"No response to {msg.type!r} after {timeout or self.request_timeout}s"
            )
        finally:
            self._pending.pop(msg.msg_id, None)

        if reply.type == MsgType.ERROR:
            raise ServerError(
                reply.get("code", ErrorCode.INTERNAL),
                reply.get("message", "Unknown error"),
                reply.get("details"),
            )

        return reply.get("result") or {}

    async def send(self, msg: Message) -> None:
        """Fire-and-forget send. No response expected."""
        if not self.is_connected:
            await self.wait_until_connected()
        await self._ws.send(msg.serialize())

    # ── Subscriptions ─────────────────────────────────────────

    async def subscribe(self, project_id: str | uuid.UUID) -> None:
        """Subscribe to events for a project."""
        pid = str(project_id)
        await self.request(make_subscribe(pid))
        self._subscriptions.add(pid)

    async def unsubscribe(self, project_id: str | uuid.UUID) -> None:
        """Unsubscribe from a project's events."""
        pid = str(project_id)
        await self.request(make_unsubscribe(pid))
        self._subscriptions.discard(pid)

    # ── Event listeners ───────────────────────────────────────

    def on(self, event_type: str) -> Callable:
        """Decorator to register an async event listener.

        Usage:
            @client.on("entity.updated")
            async def handle(event: dict):
                print(event["entity_id"])

        The callback receives the full event message dict.
        Multiple listeners per event type are supported.
        Listeners registered with "*" receive all events.
        """
        def decorator(fn: Callable) -> Callable:
            self._listeners[event_type].append(fn)
            return fn
        return decorator

    def off(self, event_type: str, fn: Callable) -> None:
        """Remove a specific event listener."""
        listeners = self._listeners.get(event_type, [])
        if fn in listeners:
            listeners.remove(fn)

    async def _dispatch_event(self, msg: Message) -> None:
        """Fire all listeners for an event message."""
        event_type = msg.get("event_type", "unknown")
        payload    = dict(msg)

        targets = (
            self._listeners.get(event_type, []) +
            self._listeners.get("*", [])
        )
        for fn in targets:
            try:
                result = fn(payload)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.exception(f"Error in event listener for {event_type!r}: {e}")

    # ── Internal ──────────────────────────────────────────────

    async def _connect(self) -> None:
        """Establish the WebSocket connection and complete the handshake."""
        self._connected.clear()

        ws = await ws_asyncio.connect(
            self.server_url,
            additional_headers={},
        )
        self._ws = ws

        # Send hello
        hello_msg = hello(
            client_name=self.client_name,
            endpoint_type=self.endpoint_type,
            capabilities=self.capabilities,
            last_event_id=self._last_event_id,
        )
        await ws.send(hello_msg.serialize())

        # Wait for welcome
        raw     = await asyncio.wait_for(ws.recv(), timeout=15.0)
        welcome = Message.parse(raw)

        if welcome.type != MsgType.WELCOME:
            raise ConnectionError(
                f"Expected welcome, got {welcome.type!r}: "
                f"{welcome.get('message', '')}"
            )

        self._session_id      = welcome.get("session_id")
        self._registry_summary = welcome.get("registry_summary", {})
        self._reconnect_delay  = self.RECONNECT_BASE_DELAY
        self._connected.set()

        logger.info(
            f"Connected to {self.server_url} as {self.client_name!r} "
            f"(session {self._session_id!s:.8}...)"
        )

        # Re-subscribe to any projects from before a reconnect
        for pid in list(self._subscriptions):
            try:
                await self._ws.send(make_subscribe(pid).serialize())
            except Exception:
                pass

    async def _receive_loop(self) -> None:
        """Continuously receive messages and dispatch them."""
        while not self._stopped:
            try:
                raw = await self._ws.recv()
            except Exception as e:
                is_close = (
                    isinstance(e, websockets.exceptions.ConnectionClosed)
                    or "ConnectionClosed" in type(e).__name__
                )
                self._connected.clear()
                if is_close:
                    logger.warning(f"Connection closed: {e}")
                    if not self._stopped and self.auto_reconnect:
                        await self._reconnect()
                else:
                    logger.exception(f"Receive error: {e}")
                break

            try:
                msg = Message.parse(raw)
            except Exception as e:
                logger.warning(f"Failed to parse message: {e} — raw: {raw!r:.100}")
                continue

            await self._handle_message(msg)

    async def _handle_message(self, msg: Message) -> None:
        """Route a received message to pending request or event listener."""
        msg_type = msg.type

        if msg_type in (MsgType.OK, MsgType.ERROR):
            # Response to a pending request
            msg_id = msg.msg_id
            if msg_id and msg_id in self._pending:
                self._pending[msg_id].resolve(msg)
            else:
                logger.debug(f"Received {msg_type!r} with no matching pending request: {msg_id}")

        elif msg_type == MsgType.EVENT:
            # Server-push event — fire listeners
            event_id = msg.get("event_id")
            if event_id:
                self._last_event_id = event_id
            await self._dispatch_event(msg)

        elif msg_type == MsgType.PONG:
            # Pong is a response to a client-initiated ping request
            msg_id = msg.msg_id
            if msg_id and msg_id in self._pending:
                self._pending[msg_id].resolve(msg)

        elif msg_type == MsgType.WELCOME:
            # Received after a reconnect
            self._session_id      = msg.get("session_id")
            self._registry_summary = msg.get("registry_summary", {})
            self._connected.set()

        else:
            logger.debug(f"Unhandled message type: {msg_type!r}")

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        while not self._stopped:
            delay = self._reconnect_delay
            logger.info(f"Reconnecting in {delay:.1f}s...")
            await asyncio.sleep(delay)

            self._reconnect_delay = min(
                delay * self.RECONNECT_MULTIPLIER,
                self.RECONNECT_MAX_DELAY,
            )

            try:
                await self._connect()
                # Restart the receive loop
                self._recv_task = asyncio.create_task(
                    self._receive_loop(),
                    name=f"forge-client-recv-{self.client_name}",
                )
                logger.info("Reconnected successfully.")
                return
            except Exception as e:
                logger.warning(f"Reconnect failed: {e}")
