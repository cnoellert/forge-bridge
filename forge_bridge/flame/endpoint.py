"""
forge-bridge Flame endpoint.

Runs inside Flame alongside the existing HTTP bridge hook. Connects to
the forge-bridge server via SyncClient and provides bidirectional
event flow:

  Flame → forge-bridge:
    segment.created    → entity.created (shot + stack + layers)
    segment.renamed    → entity.updated (shot name)
    segment.deleted    → entity.deleted
    version.published  → version.published + media.ingested
    project.opened     → client.connected + project context

  forge-bridge → Flame:
    entity.updated     → rename segments if name changed
    version.published  → update Flame media library reference
    role.renamed       → update any Flame markers or metadata

This module is designed to be loaded as a Flame Python hook. It uses
SyncClient because Flame's hook system is synchronous.

The endpoint registers itself as "flame_<hostname>" so multiple Flame
workstations can run simultaneously and be distinguished in the event log.

Usage (in a Flame Python hook):

    from forge_bridge.flame.endpoint import FlameEndpoint
    _endpoint = None

    def project_opened(project):
        global _endpoint
        _endpoint = FlameEndpoint.start()
        _endpoint.on_project_opened(project)

    def segment_created(segment, *args):
        if _endpoint:
            _endpoint.on_segment_created(segment)
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import uuid
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Flame type stubs — only available inside Flame
# ─────────────────────────────────────────────────────────────
# These stubs make the module importable outside Flame for testing.
# Real Flame objects are passed in at runtime.

try:
    import flame as _flame_module
    FLAME_AVAILABLE = True
except ImportError:
    _flame_module = None
    FLAME_AVAILABLE = False


def _str(val) -> str:
    """Safely extract string from Flame attribute (handles PyFlame wrappers)."""
    if val is None:
        return ""
    if hasattr(val, "get_value"):
        return str(val.get_value())
    return str(val)


# ─────────────────────────────────────────────────────────────
# Flame Endpoint
# ─────────────────────────────────────────────────────────────

class FlameEndpoint:
    """Manages the connection between Flame and forge-bridge.

    One instance per Flame session. Created when Flame loads a project,
    torn down when Flame exits or the project closes.
    """

    def __init__(
        self,
        server_url: str = "ws://127.0.0.1:9998",
        client_name: str | None = None,
    ):
        self.server_url  = server_url
        self.client_name = client_name or f"flame_{socket.gethostname()}"

        self._client    = None
        self._project_id: str | None = None   # current project UUID in forge-bridge
        self._seq_ids:    dict[str, str] = {}  # sequence_name → UUID
        self._shot_ids:   dict[str, str] = {}  # shot_name → UUID
        self._connected  = threading.Event()

        # Callbacks for Flame-side effects
        # registry: event_type → callable(event_dict)
        self._outbound_handlers: dict[str, list[Callable]] = {}

    @classmethod
    def start(
        cls,
        server_url: str | None = None,
        client_name: str | None = None,
    ) -> "FlameEndpoint":
        """Create and connect a FlameEndpoint.

        Called from a Flame hook at project-open time.
        Blocks until the handshake completes (max 10s), then returns.
        If the server is unreachable, logs a warning and returns anyway —
        Flame should not fail to open a project because forge-bridge is down.
        """
        url  = server_url  or os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")
        name = client_name or os.environ.get("FORGE_MCP_CLIENT_NAME")

        endpoint = cls(server_url=url, client_name=name)
        endpoint._connect()
        return endpoint

    def _connect(self) -> None:
        """Connect to forge-bridge in a background thread."""
        from forge_bridge.client import SyncClient

        self._client = SyncClient(
            client_name=self.client_name,
            server_url=self.server_url,
            endpoint_type="flame",
            request_timeout=10.0,
        )
        try:
            self._client.connect(timeout=10.0)
            self._connected.set()
            logger.info(f"Flame endpoint connected to {self.server_url}")

            # Register server-push event handlers
            self._register_inbound_handlers()

        except Exception as e:
            logger.warning(
                f"Flame endpoint could not connect to forge-bridge: {e}\n"
                "Pipeline sync disabled. Flame will continue without it."
            )

    def disconnect(self) -> None:
        """Clean disconnect. Call from project-close or Flame-exit hook."""
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._connected.clear()
        logger.info("Flame endpoint disconnected.")

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def _require_connection(self) -> bool:
        """Return False (with log) if not connected — callers skip gracefully."""
        if not self.is_connected:
            logger.debug("forge-bridge not connected — event not published")
            return False
        return True

    # ─────────────────────────────────────────────────────────
    # Outbound: Flame → forge-bridge
    # ─────────────────────────────────────────────────────────

    def on_project_opened(self, project: Any) -> None:
        """Called when Flame opens a project.

        Looks up or creates the project in forge-bridge and subscribes
        to its events so incoming changes can be applied to Flame.
        """
        if not self._require_connection():
            return

        try:
            project_name = _str(getattr(project, "project_name", project))
            project_code = _str(getattr(project, "nickname", project_name))
            if not project_code:
                project_code = project_name[:8].upper().replace(" ", "_")

            # Try to find existing project by code
            projects = self._client.project_list()
            match = next(
                (p for p in projects if p.get("code") == project_code),
                None,
            )

            if match:
                self._project_id = match["id"]
                logger.info(f"Found existing project {project_code!r} → {self._project_id}")
            else:
                result = self._client.project_create(project_name, project_code)
                self._project_id = result["project_id"]
                logger.info(f"Created project {project_code!r} → {self._project_id}")

            # Subscribe to this project's events
            self._client.subscribe(self._project_id)
            logger.info(f"Subscribed to project {self._project_id}")

        except Exception as e:
            logger.error(f"on_project_opened failed: {e}")

    def on_segment_created(
        self,
        segment: Any,
        sequence: Any | None = None,
    ) -> None:
        """Called when a timeline segment is created in Flame.

        Creates a shot + stack + default layers in forge-bridge.
        The default layers are: primary, matte, reference.
        """
        if not self._require_connection() or not self._project_id:
            return

        try:
            shot_name    = _str(getattr(segment, "name", "unknown"))
            seq_name     = _str(getattr(sequence, "name", "")) if sequence else ""
            sequence_id  = self._get_or_create_sequence(seq_name)

            # Cut point extraction — Flame timecodes vary by project setup
            cut_in  = _extract_timecode(segment, "start_frame")
            cut_out = _extract_timecode(segment, "end_frame")

            result = self._client.entity_create(
                entity_type="shot",
                project_id=self._project_id,
                name=shot_name,
                attributes={
                    "sequence_id": sequence_id,
                    "cut_in":      cut_in,
                    "cut_out":     cut_out,
                },
            )
            shot_id = result["entity_id"]
            self._shot_ids[shot_name] = shot_id

            # Create stack
            stack_result = self._client.entity_create(
                entity_type="stack",
                project_id=self._project_id,
                attributes={"shot_id": shot_id},
            )
            stack_id = stack_result["entity_id"]

            # Default layers
            for i, role in enumerate(["primary", "matte", "reference"]):
                self._client.entity_create(
                    entity_type="layer",
                    project_id=self._project_id,
                    attributes={
                        "role":     role,
                        "stack_id": stack_id,
                        "order":    i,
                    },
                )

            logger.info(
                f"Shot created: {shot_name!r} → {shot_id} "
                f"(stack {stack_id})"
            )

        except Exception as e:
            logger.error(f"on_segment_created failed: {e}")

    def on_segment_renamed(
        self,
        segment: Any,
        old_name: str,
        new_name: str,
    ) -> None:
        """Called when a timeline segment is renamed in Flame."""
        if not self._require_connection():
            return

        try:
            shot_id = self._shot_ids.get(old_name)
            if not shot_id:
                logger.debug(f"No shot ID for {old_name!r} — skipping rename")
                return

            self._client.entity_update(entity_id=shot_id, name=new_name)
            self._shot_ids[new_name] = self._shot_ids.pop(old_name)
            logger.info(f"Shot renamed: {old_name!r} → {new_name!r}")

        except Exception as e:
            logger.error(f"on_segment_renamed failed: {e}")

    def on_segment_deleted(self, segment: Any) -> None:
        """Called when a timeline segment is deleted in Flame."""
        if not self._require_connection():
            return

        try:
            shot_name = _str(getattr(segment, "name", ""))
            shot_id   = self._shot_ids.pop(shot_name, None)
            if shot_id:
                # We don't hard-delete — we set status to on_hold
                # Permanent deletes require explicit user action
                self._client.entity_update(
                    entity_id=shot_id,
                    status="on_hold",
                )
                logger.info(f"Shot {shot_name!r} marked on_hold (segment deleted in Flame)")

        except Exception as e:
            logger.error(f"on_segment_deleted failed: {e}")

    def on_version_published(
        self,
        clip: Any,
        shot_name: str,
        version_number: int,
        media_path: str | None = None,
    ) -> None:
        """Called when a version is published from Flame.

        Creates a version entity and optionally a media entity with the
        file path attached as a location.
        """
        if not self._require_connection() or not self._project_id:
            return

        try:
            shot_id = self._shot_ids.get(shot_name)
            if not shot_id:
                logger.warning(f"on_version_published: no shot_id for {shot_name!r}")
                return

            # Create version
            version_result = self._client.entity_create(
                entity_type="version",
                project_id=self._project_id,
                status="review",
                attributes={
                    "version_number": version_number,
                    "parent_id":      shot_id,
                    "parent_type":    "shot",
                    "created_by":     _str(getattr(clip, "created_by", "")),
                },
            )
            version_id = version_result["entity_id"]

            # Create relationship: version → shot
            self._client.relationship_create(
                source_id=version_id,
                target_id=shot_id,
                rel_type="version_of",
            )

            # Media entity if we have a path
            if media_path:
                fmt = _detect_format(media_path)
                media_result = self._client.entity_create(
                    entity_type="media",
                    project_id=self._project_id,
                    attributes={
                        "format":     fmt,
                        "version_id": version_id,
                    },
                )
                media_id = media_result["entity_id"]
                self._client.location_add(
                    entity_id=media_id,
                    path=media_path,
                    storage_type="network",
                )
                logger.info(
                    f"Version v{version_number:03d} published for {shot_name!r} "
                    f"→ {version_id} (media {media_id})"
                )
            else:
                logger.info(
                    f"Version v{version_number:03d} published for {shot_name!r} "
                    f"→ {version_id}"
                )

        except Exception as e:
            logger.error(f"on_version_published failed: {e}")

    # ─────────────────────────────────────────────────────────
    # Inbound: forge-bridge → Flame
    # ─────────────────────────────────────────────────────────

    def _register_inbound_handlers(self) -> None:
        """Register callbacks for events pushed by the forge-bridge server."""
        if not self._client:
            return

        self._client.on("entity.updated", self._on_entity_updated)
        self._client.on("role.renamed",   self._on_role_renamed)
        logger.debug("Inbound event handlers registered.")

    def _on_entity_updated(self, event: dict) -> None:
        """Handle an entity.updated event from forge-bridge.

        If a shot's name changed and we're the Flame that knows that shot,
        apply the rename in Flame (if the shot exists in our map).
        """
        entity_type = event.get("payload", {}).get("entity_type", "")
        if entity_type != "shot":
            return

        entity_id = event.get("entity_id")
        new_name  = event.get("payload", {}).get("name")
        if not entity_id or not new_name:
            return

        # Find if this is one of our shots
        old_name = next(
            (name for name, sid in self._shot_ids.items() if sid == entity_id),
            None,
        )
        if old_name and old_name != new_name:
            logger.info(
                f"forge-bridge renamed shot {old_name!r} → {new_name!r}. "
                "Apply to Flame timeline (not implemented — requires main thread dispatch)."
            )
            # TODO: queue rename for Flame main thread execution
            # flame_rename_segment(old_name, new_name)

    def _on_role_renamed(self, event: dict) -> None:
        """Handle a role.renamed event — log for now."""
        old_name = event.get("payload", {}).get("old_name", "")
        new_name = event.get("payload", {}).get("new_name", "")
        if old_name and new_name:
            logger.info(f"Role renamed in pipeline registry: {old_name!r} → {new_name!r}")

    # ─────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────

    def _get_or_create_sequence(self, name: str) -> str:
        """Look up or create a sequence entity. Returns the UUID."""
        if not name:
            name = "default"

        if name in self._seq_ids:
            return self._seq_ids[name]

        result = self._client.entity_create(
            entity_type="sequence",
            project_id=self._project_id,
            name=name,
            attributes={"frame_rate": "24"},
        )
        seq_id = result["entity_id"]
        self._seq_ids[name] = seq_id
        return seq_id

    def get_project_id(self) -> str | None:
        """Return the current project UUID in forge-bridge."""
        return self._project_id

    def get_shot_id(self, shot_name: str) -> str | None:
        """Return the forge-bridge UUID for a Flame shot name."""
        return self._shot_ids.get(shot_name)

    def status(self) -> dict:
        """Return a summary of the endpoint state."""
        return {
            "connected":    self.is_connected,
            "client_name":  self.client_name,
            "server_url":   self.server_url,
            "project_id":   self._project_id,
            "known_shots":  len(self._shot_ids),
            "known_seqs":   len(self._seq_ids),
        }


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _extract_timecode(segment: Any, attr: str) -> str | None:
    """Extract a timecode string from a Flame segment attribute."""
    try:
        val = getattr(segment, attr, None)
        if val is None:
            return None
        # Flame timecodes are often PyTimecode or integer frame numbers
        if hasattr(val, "get_value"):
            return str(val.get_value())
        return str(val)
    except Exception:
        return None


def _detect_format(path: str) -> str:
    """Detect media format from file path extension."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    formats = {
        "exr": "EXR", "dpx": "DPX", "tif": "TIFF", "tiff": "TIFF",
        "mov": "MOV", "mp4": "MP4", "mxf": "MXF",
        "jpg": "JPEG", "jpeg": "JPEG", "png": "PNG",
    }
    return formats.get(ext, ext.upper() or "UNKNOWN")
