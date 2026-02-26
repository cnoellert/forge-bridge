"""
FORGE Bridge — Pipeline event hook for Flame.

Stdlib only. Safe to load in any Flame Python environment.

Listens for Flame callbacks and forwards them as JSON events to the
forge-bridge sidecar (forge_bridge/flame/sidecar.py), which runs in
a full Python environment and handles all forge-bridge communication.

This hook is independent of forge_bridge.py (the HTTP bridge). Both
can be loaded simultaneously, or this one alone if the HTTP bridge
isn't needed.

Architecture:

    Flame callbacks
        ↓
    forge_bridge_pipeline.py  (this file, Flame's Python, stdlib only)
        ↓  HTTP POST /event
    forge_bridge sidecar  (conda env, port 9997)
        ↓  WebSocket
    forge-bridge server  (port 9998)
        ↓
    PostgreSQL

If the sidecar is not running, events are silently dropped and Flame
continues normally.

Installation:
    Symlink or copy to the Flame shared Python hooks directory.
    Flame loads all .py files in that directory on startup.

Configuration (/opt/Autodesk/cfg/env.cfg):
    FORGE_SIDECAR_HOST   Sidecar host  (default: 127.0.0.1)
    FORGE_SIDECAR_PORT   Sidecar port  (default: 9997)
    FORGE_PIPELINE_ENABLED  Set to 0 to disable (default: 1)
"""

import http.client
import json
import os
import threading

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

SIDECAR_HOST     = os.environ.get("FORGE_SIDECAR_HOST",    "127.0.0.1")
SIDECAR_PORT     = int(os.environ.get("FORGE_SIDECAR_PORT", "9997"))
PIPELINE_ENABLED = os.environ.get("FORGE_PIPELINE_ENABLED", "1") != "0"


def _log(msg: str) -> None:
    print(f"[FORGE PIPELINE] {msg}")


# ─────────────────────────────────────────────────────────────
# Event forwarder
# ─────────────────────────────────────────────────────────────

def _forward(event_type: str, payload: dict) -> None:
    """POST a Flame event to the sidecar. Fire-and-forget, never raises."""
    def _send():
        try:
            body = json.dumps({
                "event_type": event_type,
                "payload":    payload,
            }).encode()
            conn = http.client.HTTPConnection(
                SIDECAR_HOST, SIDECAR_PORT, timeout=2
            )
            conn.request(
                "POST", "/event",
                body=body,
                headers={"Content-Type": "application/json"},
            )
            conn.getresponse()
            conn.close()
        except Exception:
            pass  # sidecar not running — drop silently

    threading.Thread(target=_send, daemon=True).start()


def _flame_object_to_dict(obj) -> dict:
    """Convert a Flame API object to a plain dict the sidecar can use."""
    d = {}
    for attr in ("name", "uid", "type", "frame_rate", "start_frame",
                 "duration", "tape_name", "shot_name"):
        try:
            val = getattr(obj, attr, None)
            if val is not None:
                d[attr] = str(val)
        except Exception:
            pass
    return d


# ─────────────────────────────────────────────────────────────
# Flame hook callbacks
# ─────────────────────────────────────────────────────────────

def app_initialized(project_name, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    _log(f"Pipeline hook active — project: {project_name}")
    _log(f"Forwarding events to sidecar at {SIDECAR_HOST}:{SIDECAR_PORT}")
    _forward("app.initialized", {"project_name": str(project_name)})


def project_changed_dict(info, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = {
            "project_name": str(info.get("project_name", "")),
            "project_dir":  str(info.get("project_dir",  "")),
            "user_name":    str(info.get("user_name",    "")),
        }
    except Exception:
        payload = {"raw": str(info)}
    _forward("project.changed", payload)


def segment_created(segment, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _flame_object_to_dict(segment)
        # Try to get parent sequence info
        try:
            seq = segment.parent
            payload["sequence_name"] = str(seq.name)
            payload["sequence_uid"]  = str(seq.uid) if hasattr(seq, "uid") else ""
        except Exception:
            pass
    except Exception as e:
        payload = {"error": str(e)}
    _forward("segment.created", payload)


def segment_deleted(segment, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _flame_object_to_dict(segment)
    except Exception as e:
        payload = {"error": str(e)}
    _forward("segment.deleted", payload)


def segment_renamed(segment, old_name, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _flame_object_to_dict(segment)
        payload["old_name"] = str(old_name)
    except Exception as e:
        payload = {"error": str(e)}
    _forward("segment.renamed", payload)


def batch_render_completed(info, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = {
            "render_node_name": str(info.get("render_node_name", "")),
            "render_path":      str(info.get("render_path",      "")),
            "shot_name":        str(info.get("shot_name",        "")),
            "start_frame":      str(info.get("start_frame",      "")),
            "end_frame":        str(info.get("end_frame",        "")),
            "frame_rate":       str(info.get("frame_rate",       "")),
        }
    except Exception:
        payload = {"raw": str(info)}
    _forward("batch.render_completed", payload)


def media_imported(media, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _flame_object_to_dict(media)
    except Exception as e:
        payload = {"error": str(e)}
    _forward("media.imported", payload)
