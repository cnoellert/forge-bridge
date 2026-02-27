"""
forge-bridge sync client.

Flame's Python hooks run in a synchronous context — no event loop,
no await. This client wraps the async client in a background thread
so Flame code can use it with ordinary function calls.

Design:

  A single background thread owns the asyncio event loop.
  The sync client submits coroutines to that loop via
  asyncio.run_coroutine_threadsafe() and blocks until they complete.

  This is the standard pattern for bridging sync/async Python:
  the async machinery lives in its own thread, callers block on
  a threading.Future (not asyncio.Future) waiting for results.

  Thread safety: the async client itself is not thread-safe, but
  all calls go through run_coroutine_threadsafe(), which IS designed
  for cross-thread submission to a running event loop.

Usage (Flame hook):

    from forge_bridge.client import SyncClient

    # Typically created once at module level or in the hook's setup
    client = SyncClient("flame_a")
    client.connect()   # returns immediately once handshake completes

    # In any hook function:
    def on_segment_created(segment):
        result = client.entity_create(
            entity_type="shot",
            project_id=current_project_id,
            name=segment.name,
        )
        shot_id = result["entity_id"]

    # Cleanup
    client.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from concurrent.futures import Future as ThreadFuture
from typing import Any, Callable

from forge_bridge.client.async_client import AsyncClient
from forge_bridge.server.protocol import (
    Message,
    entity_create, entity_update, entity_get, entity_list,
    project_create, project_get, project_list,
    relationship_create, location_add,
    query_dependents, query_shot_stack, query_events,
    role_register, role_rename, role_delete,
    subscribe, unsubscribe,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Background event loop thread
# ─────────────────────────────────────────────────────────────

class _LoopThread(threading.Thread):
    """A daemon thread that owns and runs an asyncio event loop.

    Stays alive for the lifetime of the SyncClient.
    """

    def __init__(self):
        super().__init__(name="forge-bridge-loop", daemon=True)
        self.loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()

    def start_and_wait(self) -> None:
        """Start the thread and block until the event loop is ready."""
        self.start()
        self._ready.wait()

    def submit(self, coro) -> ThreadFuture:
        """Submit a coroutine to the loop. Returns a concurrent.futures.Future."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self) -> None:
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


# ─────────────────────────────────────────────────────────────
# Sync Client
# ─────────────────────────────────────────────────────────────

class SyncClient:
    """Synchronous forge-bridge client.

    All methods block until the server responds or a timeout occurs.
    Safe to call from Flame Python hooks, synchronous scripts, and
    any context where you can't use await.

    Internally runs an AsyncClient on a background thread.
    """

    def __init__(
        self,
        client_name: str,
        server_url: str = "ws://localhost:9998",
        endpoint_type: str = "flame",
        request_timeout: float = 30.0,
    ):
        self.client_name     = client_name
        self.server_url      = server_url
        self.endpoint_type   = endpoint_type
        self.request_timeout = request_timeout

        self._thread: _LoopThread | None      = None
        self._async:  AsyncClient | None = None

    # ── Lifecycle ─────────────────────────────────────────────

    def connect(self, timeout: float = 15.0) -> None:
        """Connect to the server. Blocks until the handshake is complete.

        Args:
            timeout: Maximum seconds to wait for the connection.

        Raises:
            ConnectionError: If the server is unreachable.
            TimeoutError:    If the handshake doesn't complete in time.
        """
        self._thread = _LoopThread()
        self._thread.start_and_wait()

        self._async = AsyncClient(
            client_name=self.client_name,
            server_url=self.server_url,
            endpoint_type=self.endpoint_type,
            auto_reconnect=True,
            request_timeout=self.request_timeout,
        )

        future = self._thread.submit(self._async.start())
        future.result(timeout=timeout)

        # Wait for handshake to complete
        wait_future = self._thread.submit(
            self._async.wait_until_connected(timeout=timeout)
        )
        wait_future.result(timeout=timeout + 1)

        logger.info(
            f"SyncClient {self.client_name!r} connected to {self.server_url}"
        )

    def disconnect(self) -> None:
        """Disconnect cleanly."""
        if self._async:
            future = self._thread.submit(self._async.stop())
            try:
                future.result(timeout=5.0)
            except Exception:
                pass

        if self._thread:
            self._thread.stop()

        logger.info(f"SyncClient {self.client_name!r} disconnected.")

    def __enter__(self) -> "SyncClient":
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()

    # ── Core request method ───────────────────────────────────

    def _run(self, msg: Message, timeout: float | None = None) -> dict:
        """Submit a request and block for the response.

        This is the internal method everything else calls.
        """
        if not self._async or not self._async.is_connected:
            raise RuntimeError(
                "Not connected. Call connect() first."
            )
        future = self._thread.submit(
            self._async.request(msg, timeout=timeout or self.request_timeout)
        )
        return future.result(timeout=(timeout or self.request_timeout) + 1)

    def on(self, event_type: str, fn: Callable) -> None:
        """Register a callback for server-push events.

        The callback is called in the background loop thread.
        Keep it short — heavy work should be dispatched to a thread pool.

        Args:
            event_type: e.g. "entity.updated", "role.renamed", "*" for all
            fn:         Callable that accepts one dict argument (the event).
                        May be sync or async.
        """
        if not self._async:
            raise RuntimeError("Not connected.")

        async def _wrapper(event: dict) -> None:
            try:
                result = fn(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.exception(f"Event callback error: {e}")

        self._async._listeners[event_type].append(_wrapper)

    # ── Subscriptions ─────────────────────────────────────────

    def subscribe(self, project_id: str | uuid.UUID) -> None:
        """Subscribe to events for a project."""
        self._run(subscribe(str(project_id)))

    def unsubscribe(self, project_id: str | uuid.UUID) -> None:
        """Unsubscribe from a project's events."""
        self._run(unsubscribe(str(project_id)))

    # ── Projects ──────────────────────────────────────────────

    def project_create(
        self,
        name: str,
        code: str,
        metadata: dict | None = None,
    ) -> dict:
        """Create a new project. Returns {"project_id": "..."}."""
        return self._run(project_create(name, code, metadata))

    def project_get(self, project_id: str | uuid.UUID) -> dict:
        """Fetch a project by ID. Returns the project dict."""
        return self._run(project_get(str(project_id)))

    def project_list(self) -> list[dict]:
        """Return all projects."""
        result = self._run(project_list())
        return result.get("projects", [])

    # ── Entities ──────────────────────────────────────────────

    def entity_create(
        self,
        entity_type: str,
        project_id:  str | uuid.UUID,
        attributes:  dict,
        name:        str | None = None,
        status:      str | None = None,
    ) -> dict:
        """Create an entity. Returns {"entity_id": "..."}."""
        return self._run(entity_create(
            entity_type=entity_type,
            project_id=str(project_id),
            attributes=attributes,
            name=name,
            status=status,
        ))

    def entity_update(
        self,
        entity_id:  str | uuid.UUID,
        attributes: dict | None = None,
        name:       str | None = None,
        status:     str | None = None,
    ) -> None:
        """Update an entity's fields."""
        self._run(entity_update(
            entity_id=str(entity_id),
            attributes=attributes,
            name=name,
            status=status,
        ))

    def entity_get(self, entity_id: str | uuid.UUID) -> dict:
        """Fetch an entity by ID."""
        return self._run(entity_get(str(entity_id)))

    def entity_list(
        self,
        entity_type: str,
        project_id:  str | uuid.UUID,
    ) -> list[dict]:
        """List all entities of a type in a project."""
        result = self._run(entity_list(entity_type, str(project_id)))
        return result.get("entities", [])

    # ── Graph ─────────────────────────────────────────────────

    def relationship_create(
        self,
        source_id:  str | uuid.UUID,
        target_id:  str | uuid.UUID,
        rel_type:   str,
        attributes: dict | None = None,
    ) -> None:
        """Create a relationship edge, optionally with edge attributes.

        For consumes/produces edges, pass:
            attributes={"track_role": "primary", "layer_index": "001"}
        """
        self._run(relationship_create(
            str(source_id), str(target_id), rel_type,
            attributes=attributes,
        ))

    def location_add(
        self,
        entity_id:    str | uuid.UUID,
        path:         str,
        storage_type: str = "local",
        priority:     int = 0,
    ) -> None:
        """Add a file path location to an entity."""
        self._run(location_add(
            entity_id=str(entity_id),
            path=path,
            storage_type=storage_type,
            priority=priority,
        ))

    # ── Queries ───────────────────────────────────────────────

    def get_dependents(self, entity_id: str | uuid.UUID) -> list[str]:
        """Return IDs of all entities that depend on entity_id."""
        result = self._run(query_dependents(str(entity_id)))
        return result.get("dependents", [])

    def get_shot_stack(self, shot_id: str | uuid.UUID) -> dict:
        """Return the stack and all layers for a shot."""
        return self._run(query_shot_stack(str(shot_id)))

    def get_events(
        self,
        project_id: str | uuid.UUID | None = None,
        entity_id:  str | uuid.UUID | None = None,
        limit:      int = 50,
    ) -> list[dict]:
        """Return recent events from the audit log."""
        result = self._run(query_events(
            project_id=str(project_id) if project_id else None,
            entity_id=str(entity_id)   if entity_id  else None,
            limit=limit,
        ))
        return result.get("events", [])

    # ── Registry ──────────────────────────────────────────────

    def role_register(
        self,
        name:          str,
        label:         str | None = None,
        order:         int = 0,
        path_template: str | None = None,
        aliases:       dict | None = None,
    ) -> dict:
        """Register a new custom role. Returns {"key": "...", "name": "..."}."""
        return self._run(role_register(name, label, order, path_template, aliases))

    def role_rename(self, old_name: str, new_name: str) -> dict:
        """Rename a role's canonical name."""
        return self._run(role_rename(old_name, new_name))

    def role_delete(
        self,
        name:       str,
        migrate_to: str | None = None,
    ) -> dict:
        """Delete a role, optionally migrating refs to another role."""
        return self._run(role_delete(name, migrate_to))

    # ── Convenience — shot stack creation ────────────────────

    def create_shot_stack(
        self,
        project_id:  str | uuid.UUID,
        sequence_id: str | uuid.UUID,
        shot_name:   str,
        layers:      list[dict],
        cut_in:      str | None = None,
        cut_out:     str | None = None,
    ) -> dict:
        """Create a complete shot + stack + layers in one call.

        Args:
            project_id:  Project to create in.
            sequence_id: Sequence the shot belongs to.
            shot_name:   Shot code e.g. "EP60_010".
            layers:      List of dicts with "role" and optional "order".
                         e.g. [{"role": "primary"}, {"role": "matte", "order": 1}]
            cut_in:      Timecode string e.g. "01:00:00:00".
            cut_out:     Timecode string e.g. "01:00:08:00".

        Returns:
            {
                "shot_id":  "...",
                "stack_id": "...",
                "layer_ids": {"primary": "...", "matte": "..."},
            }
        """
        attrs = {"sequence_id": str(sequence_id)}
        if cut_in:
            attrs["cut_in"] = cut_in
        if cut_out:
            attrs["cut_out"] = cut_out

        shot_result = self.entity_create(
            entity_type="shot",
            project_id=project_id,
            name=shot_name,
            attributes=attrs,
        )
        shot_id = shot_result["entity_id"]

        stack_result = self.entity_create(
            entity_type="stack",
            project_id=project_id,
            attributes={"shot_id": shot_id},
        )
        stack_id = stack_result["entity_id"]

        layer_ids = {}
        for i, layer_spec in enumerate(layers):
            role  = layer_spec.get("role", "primary")
            order = layer_spec.get("order", i)
            layer_result = self.entity_create(
                entity_type="layer",
                project_id=project_id,
                attributes={
                    "role":     role,
                    "stack_id": stack_id,
                    "order":    order,
                },
            )
            layer_ids[role] = layer_result["entity_id"]

        return {
            "shot_id":   shot_id,
            "stack_id":  stack_id,
            "layer_ids": layer_ids,
        }
