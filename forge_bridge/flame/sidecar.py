"""
forge-bridge Flame sidecar.

Runs in a full Python environment (conda) alongside Flame.
Receives Flame events from forge_bridge_pipeline.py via HTTP on port 9997,
translates them into forge-bridge protocol messages, and publishes them
to the forge-bridge server via AsyncClient.

Also polls the Flame HTTP bridge (port 9999) for state queries when needed.

Usage:
    python3 -m forge_bridge.flame.sidecar

Configuration (environment variables):
    FORGE_BRIDGE_URL       forge-bridge WebSocket  (default: ws://127.0.0.1:9998)
    FORGE_SIDECAR_HOST     Bind host               (default: 127.0.0.1)
    FORGE_SIDECAR_PORT     Bind port               (default: 9997)
    FORGE_HTTP_BRIDGE_URL  Flame HTTP bridge       (default: http://127.0.0.1:9999)
    FORGE_SIDECAR_NAME     Client name             (default: flame_sidecar)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

import httpx

from forge_bridge.client import AsyncClient
from forge_bridge.server.protocol import (
    entity_create, entity_update, entity_list, entity_get,
    project_create, project_list,
    relationship_create,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

BRIDGE_URL       = os.environ.get("FORGE_BRIDGE_URL",      "ws://127.0.0.1:9998")
SIDECAR_HOST     = os.environ.get("FORGE_SIDECAR_HOST",    "127.0.0.1")
SIDECAR_PORT     = int(os.environ.get("FORGE_SIDECAR_PORT", "9997"))
HTTP_BRIDGE_URL  = os.environ.get("FORGE_HTTP_BRIDGE_URL", "http://127.0.0.1:9999")
SIDECAR_NAME     = os.environ.get("FORGE_SIDECAR_NAME",    "flame_sidecar")


# ─────────────────────────────────────────────────────────────
# Flame HTTP bridge helper
# ─────────────────────────────────────────────────────────────

class FlameHTTPBridge:
    """Thin wrapper around the Flame HTTP bridge for state queries."""

    def __init__(self, base_url: str = HTTP_BRIDGE_URL):
        self.base_url = base_url.rstrip("/")

    async def exec(self, code: str, main_thread: bool = False) -> dict:
        """Execute Python code inside Flame, return result dict."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/exec",
                    json={"code": code, "main_thread": main_thread},
                )
                return resp.json()
        except Exception as e:
            logger.warning(f"Flame HTTP bridge error: {e}")
            return {"error": str(e), "result": None}

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/status")
                return resp.status_code == 200
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────

class SidecarState:
    """Tracks forge-bridge IDs for known Flame objects."""

    def __init__(self):
        self.project_id:  Optional[str] = None
        self.project_name: Optional[str] = None
        # Maps Flame names → forge-bridge UUIDs
        self.shot_ids:     dict[str, str] = {}
        self.seq_ids:      dict[str, str] = {}
        self.stack_ids:    dict[str, str] = {}  # shot_id → stack_id

    def reset(self):
        self.project_id   = None
        self.project_name = None
        self.shot_ids.clear()
        self.seq_ids.clear()
        self.stack_ids.clear()


# ─────────────────────────────────────────────────────────────
# Event handlers
# ─────────────────────────────────────────────────────────────

class SidecarEventHandler:
    """Translates Flame events into forge-bridge operations."""

    DEFAULT_LAYERS = ["primary", "matte", "reference"]

    def __init__(self, client: AsyncClient, flame: FlameHTTPBridge):
        self.client = client
        self.flame  = flame
        self.state  = SidecarState()

    async def handle(self, event_type: str, payload: dict) -> None:
        logger.debug(f"Event: {event_type}  payload={payload}")
        handlers = {
            "app.initialized":      self._on_app_initialized,
            "project.changed":      self._on_project_changed,
            "segment.created":      self._on_segment_created,
            "segment.deleted":      self._on_segment_deleted,
            "segment.renamed":      self._on_segment_renamed,
            "batch.render_completed": self._on_batch_render_completed,
            "media.imported":       self._on_media_imported,
        }
        handler = handlers.get(event_type)
        if handler:
            try:
                await handler(payload)
            except Exception as e:
                logger.error(f"Error handling {event_type}: {e}", exc_info=True)
        else:
            logger.debug(f"No handler for event: {event_type}")

    # ── Handlers ──────────────────────────────────────────────

    async def _on_app_initialized(self, payload: dict) -> None:
        project_name = payload.get("project_name", "")
        logger.info(f"Flame initialized — project: {project_name!r}")
        await self._ensure_project(project_name)

    async def _on_project_changed(self, payload: dict) -> None:
        project_name = payload.get("project_name", "")
        if project_name == self.state.project_name:
            return
        logger.info(f"Project changed → {project_name!r}")
        self.state.reset()
        await self._ensure_project(project_name)

    async def _on_segment_created(self, payload: dict) -> None:
        if not self.state.project_id:
            logger.warning("segment.created before project — skipping")
            return

        shot_name = payload.get("name", "")
        seq_name  = payload.get("sequence_name", "")

        if not shot_name:
            return

        if shot_name in self.state.shot_ids:
            logger.debug(f"Shot {shot_name!r} already known — skipping")
            return

        # Get or create sequence
        seq_id = await self._ensure_sequence(seq_name or "default")

        # Create shot
        attrs = {"sequence_id": seq_id}
        if payload.get("start_frame"):
            attrs["cut_in"] = payload["start_frame"]
        if payload.get("duration"):
            try:
                end = int(payload["start_frame"] or 0) + int(payload["duration"]) - 1
                attrs["cut_out"] = str(end)
            except (ValueError, TypeError):
                pass

        r = await self.client.request(
            entity_create("shot", self.state.project_id,
                          name=shot_name, attributes=attrs)
        )
        shot_id = r["entity_id"]
        self.state.shot_ids[shot_name] = shot_id
        logger.info(f"Shot created: {shot_name!r} → {shot_id}")

        # Link shot → sequence
        await self.client.request(
            relationship_create(shot_id, seq_id, "member_of")
        )

        # Create stack + default layers
        await self._create_stack(shot_id, shot_name)

    async def _on_segment_deleted(self, payload: dict) -> None:
        shot_name = payload.get("name", "")
        shot_id   = self.state.shot_ids.get(shot_name)
        if not shot_id:
            return

        await self.client.request(entity_update(shot_id, status="on_hold"))
        logger.info(f"Shot {shot_name!r} set to on_hold")

    async def _on_segment_renamed(self, payload: dict) -> None:
        old_name  = payload.get("old_name", "")
        new_name  = payload.get("name", "")
        shot_id   = self.state.shot_ids.get(old_name)
        if not shot_id or not new_name:
            return

        await self.client.request(entity_update(shot_id, name=new_name))
        self.state.shot_ids[new_name] = shot_id
        del self.state.shot_ids[old_name]
        logger.info(f"Shot renamed: {old_name!r} → {new_name!r}")

    async def _on_batch_render_completed(self, payload: dict) -> None:
        if not self.state.project_id:
            return

        shot_name = payload.get("shot_name") or payload.get("render_node_name", "")
        shot_id   = self.state.shot_ids.get(shot_name)

        r = await self.client.request(
            entity_create("version", self.state.project_id,
                status="review",
                attributes={
                    "parent_id":   shot_id or "",
                    "parent_type": "shot",
                    "render_path": payload.get("render_path", ""),
                    "frame_rate":  payload.get("frame_rate",  ""),
                    "start_frame": payload.get("start_frame", ""),
                    "end_frame":   payload.get("end_frame",   ""),
                })
        )
        logger.info(f"Version created for {shot_name!r} → {r['entity_id']}")

    async def _on_media_imported(self, payload: dict) -> None:
        if not self.state.project_id:
            return
        name = payload.get("name", "imported_media")
        r = await self.client.request(
            entity_create("media", self.state.project_id,
                name=name,
                attributes=payload)
        )
        logger.info(f"Media created: {name!r} → {r['entity_id']}")

    # ── Helpers ───────────────────────────────────────────────

    async def _ensure_project(self, project_name: str) -> Optional[str]:
        """Look up or create a project in forge-bridge."""
        if not project_name:
            return None

        # Try to find existing project by name
        try:
            r = await self.client.request(project_list())
            for p in r.get("projects", []):
                if p.get("name") == project_name:
                    self.state.project_id   = p["id"]
                    self.state.project_name = project_name
                    logger.info(f"Project found: {project_name!r} → {p['id']}")
                    return p["id"]
        except Exception as e:
            logger.warning(f"project_list failed: {e}")

        # Create it
        try:
            code = _make_code(project_name)
            r = await self.client.request(project_create(project_name, code))
            self.state.project_id   = r["project_id"]
            self.state.project_name = project_name
            logger.info(f"Project created: {project_name!r} → {r['project_id']}")
            return r["project_id"]
        except Exception as e:
            logger.error(f"project_create failed: {e}")
            return None

    async def _ensure_sequence(self, seq_name: str) -> str:
        """Get or create a sequence, return its ID."""
        if seq_name in self.state.seq_ids:
            return self.state.seq_ids[seq_name]

        r = await self.client.request(
            entity_create("sequence", self.state.project_id,
                          name=seq_name, attributes={})
        )
        seq_id = r["entity_id"]
        self.state.seq_ids[seq_name] = seq_id
        logger.info(f"Sequence created: {seq_name!r} → {seq_id}")
        return seq_id

    async def _create_stack(self, shot_id: str, shot_name: str) -> None:
        """Create a stack with default layers for a shot."""
        r = await self.client.request(
            entity_create("stack", self.state.project_id,
                          attributes={"shot_id": shot_id})
        )
        stack_id = r["entity_id"]
        self.state.stack_ids[shot_id] = stack_id

        for i, role in enumerate(self.DEFAULT_LAYERS):
            await self.client.request(
                entity_create("layer", self.state.project_id,
                    attributes={"role": role, "stack_id": stack_id, "order": i})
            )

        logger.info(
            f"Stack created for {shot_name!r}: {stack_id} "
            f"({len(self.DEFAULT_LAYERS)} layers)"
        )


def _make_code(name: str) -> str:
    """Generate a short project code from name."""
    words = name.upper().split()
    if len(words) >= 2:
        return "".join(w[0] for w in words[:4])
    return name.upper()[:6]


# ─────────────────────────────────────────────────────────────
# HTTP server — receives events from Flame hook
# ─────────────────────────────────────────────────────────────

class _EventHandler(BaseHTTPRequestHandler):
    """Receives POST /event from forge_bridge_pipeline.py."""

    # Injected by SidecarServer
    event_queue: asyncio.Queue = None

    def do_POST(self):
        if self.path != "/event":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400)
            return

        # Put event onto the asyncio queue (thread-safe via call_soon_threadsafe)
        if self.server.loop and self.server.event_queue:
            self.server.loop.call_soon_threadsafe(
                self.server.event_queue.put_nowait,
                data
            )

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"running"}')
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        pass  # suppress access log


class _ReuseHTTPServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, *args, loop, event_queue, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop        = loop
        self.event_queue = event_queue


# ─────────────────────────────────────────────────────────────
# Sidecar main
# ─────────────────────────────────────────────────────────────

class FlameSidecar:
    """The sidecar process.

    Runs an HTTP server in a background thread to receive events from
    the Flame hook, and an asyncio loop to process them and talk to
    forge-bridge.
    """

    def __init__(self):
        self.client:  Optional[AsyncClient]       = None
        self.flame:   FlameHTTPBridge              = FlameHTTPBridge()
        self.handler: Optional[SidecarEventHandler] = None
        self._queue:  asyncio.Queue                = None
        self._http:   Optional[_ReuseHTTPServer]   = None
        self._shutdown = asyncio.Event()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()

        # Start forge-bridge client
        self.client = AsyncClient(SIDECAR_NAME, BRIDGE_URL, endpoint_type="flame")
        await self.client.start()

        try:
            await self.client.wait_until_connected(timeout=10)
            logger.info(f"Connected to forge-bridge at {BRIDGE_URL}")
        except asyncio.TimeoutError:
            logger.warning(
                "forge-bridge server not reachable — will retry on events"
            )

        self.handler = SidecarEventHandler(self.client, self.flame)

        # Start HTTP listener in background thread
        try:
            self._http = _ReuseHTTPServer(
                (SIDECAR_HOST, SIDECAR_PORT),
                _EventHandler,
                loop=loop,
                event_queue=self._queue,
            )
        except OSError as e:
            if e.errno in (48, 98):  # EADDRINUSE — macOS=48, Linux=98
                logger.info(
                    f"Port {SIDECAR_PORT} already in use — "
                    "another sidecar is running. Exiting cleanly."
                )
                await self.client.stop()
                return
            raise
        http_thread = threading.Thread(
            target=self._http.serve_forever,
            name="sidecar-http",
            daemon=True,
        )
        http_thread.start()
        logger.info(f"Listening for Flame events on {SIDECAR_HOST}:{SIDECAR_PORT}")

        # Register shutdown signals
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._request_shutdown)

        logger.info("Sidecar ready. Waiting for Flame events...")

        # Event loop
        await self._event_loop()
        await self._cleanup()

    async def _event_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                event_type = event.get("event_type", "unknown")
                payload    = event.get("payload", {})

                # Reconnect if needed
                if not self.client.is_connected:
                    logger.info("Reconnecting to forge-bridge...")
                    try:
                        await self.client.wait_until_connected(timeout=5)
                    except asyncio.TimeoutError:
                        logger.warning("forge-bridge unreachable — dropping event")
                        continue

                await self.handler.handle(event_type, payload)

            except asyncio.TimeoutError:
                continue  # normal — just checking shutdown flag
            except Exception as e:
                logger.error(f"Event loop error: {e}", exc_info=True)

    def _request_shutdown(self) -> None:
        logger.info("Shutdown requested")
        self._shutdown.set()

    async def _cleanup(self) -> None:
        logger.info("Shutting down...")
        if self._http:
            self._http.shutdown()
        if self.client:
            await self.client.stop()
        logger.info("Sidecar stopped.")


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main() -> None:
    log_level = os.environ.get("FORGE_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info(f"forge-bridge Flame sidecar starting...")
    logger.info(f"  forge-bridge server : {BRIDGE_URL}")
    logger.info(f"  event listener      : {SIDECAR_HOST}:{SIDECAR_PORT}")
    logger.info(f"  Flame HTTP bridge   : {HTTP_BRIDGE_URL}")

    sidecar = FlameSidecar()
    asyncio.run(sidecar.run())


if __name__ == "__main__":
    main()
