"""
FORGE Bridge — Pipeline event hook for Flame.

Stdlib only. Safe to load in any Flame Python environment.

On app_initialized, spawns the forge-bridge sidecar as a subprocess
using the configured Python interpreter, then monitors it and restarts
it if it dies. Artists don't need to manage any processes manually.

Architecture:

    Flame callbacks
        ↓
    forge_bridge_pipeline.py  (this file, Flame's Python, stdlib only)
        ↓  spawns on startup, watchdog keeps alive
        ↓  HTTP POST /event
    forge_bridge sidecar  (conda env, port 9997)
        ↓  WebSocket
    forge-bridge server  (port 9998)
        ↓
    PostgreSQL

Configuration (/opt/Autodesk/cfg/env.cfg):
    FORGE_PYTHON            Python interpreter for sidecar (required)
                            e.g. /Users/you/miniconda3/envs/forge-bridge/bin/python3
    FORGE_BRIDGE_REPO       Path to forge-bridge repo root
    FORGE_SIDECAR_HOST      Sidecar bind host  (default: 127.0.0.1)
    FORGE_SIDECAR_PORT      Sidecar port       (default: 9997)
    FORGE_PIPELINE_ENABLED  Set to 0 to disable (default: 1)
    FORGE_DB_URL            Passed through to sidecar
    FORGE_BRIDGE_URL        Passed through to sidecar
"""

import http.client
import json
import os
import subprocess
import threading
import time

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

SIDECAR_HOST     = os.environ.get("FORGE_SIDECAR_HOST",    "127.0.0.1")
SIDECAR_PORT     = int(os.environ.get("FORGE_SIDECAR_PORT", "9997"))
PIPELINE_ENABLED = os.environ.get("FORGE_PIPELINE_ENABLED", "1") != "0"
BRIDGE_REPO      = os.environ.get("FORGE_BRIDGE_REPO",
                       "/Users/cnoellert/Documents/GitHub/forge-bridge")

_PYTHON_CANDIDATES = [
    os.environ.get("FORGE_PYTHON", ""),
    os.path.expanduser("~/miniconda3/envs/forge-bridge/bin/python3"),
    os.path.expanduser("~/anaconda3/envs/forge-bridge/bin/python3"),
    os.path.expanduser("~/opt/miniconda3/envs/forge-bridge/bin/python3"),
    os.path.expanduser("~/miniforge3/envs/forge-bridge/bin/python3"),
]


def _find_python():
    for p in _PYTHON_CANDIDATES:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def _log(msg):
    print(f"[FORGE PIPELINE] {msg}")


# ─────────────────────────────────────────────────────────────
# Sidecar process manager
# ─────────────────────────────────────────────────────────────

_sidecar_proc    = None
_sidecar_lock    = threading.Lock()
_sidecar_monitor = None


def _build_env():
    env = dict(os.environ)
    pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{BRIDGE_REPO}:{pp}" if pp else BRIDGE_REPO
    env.setdefault("FORGE_SIDECAR_HOST", SIDECAR_HOST)
    env.setdefault("FORGE_SIDECAR_PORT", str(SIDECAR_PORT))
    env.setdefault("FORGE_BRIDGE_URL",   "ws://127.0.0.1:9998")
    env.setdefault("FORGE_DB_URL",
        "postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge")
    return env


def _spawn():
    global _sidecar_proc
    python = _find_python()
    if not python:
        _log("No Python found for sidecar — set FORGE_PYTHON in env.cfg")
        return False
    if not BRIDGE_REPO or not os.path.isdir(BRIDGE_REPO):
        _log(f"FORGE_BRIDGE_REPO not found: {BRIDGE_REPO!r}")
        return False
    try:
        log_path = os.path.join(os.path.expanduser("~"), ".forge_sidecar.log")
        log_file = open(log_path, "a")
        _sidecar_proc = subprocess.Popen(
            [python, "-m", "forge_bridge.flame.sidecar"],
            env=_build_env(),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
        _log(f"Sidecar started (pid={_sidecar_proc.pid}), log: {log_path}")
        return True
    except Exception as e:
        _log(f"Failed to start sidecar: {e}")
        return False


def _ensure_sidecar():
    with _sidecar_lock:
        if _sidecar_proc is not None and _sidecar_proc.poll() is None:
            return
        _spawn()


def _watchdog():
    time.sleep(5)
    while True:
        time.sleep(10)
        with _sidecar_lock:
            if _sidecar_proc is not None:
                rc = _sidecar_proc.poll()
                if rc is not None and rc != 0:
                    _log(f"Sidecar exited unexpectedly (rc={rc}) — restarting...")
                    _spawn()


def _start_watchdog():
    global _sidecar_monitor
    if _sidecar_monitor is None or not _sidecar_monitor.is_alive():
        _sidecar_monitor = threading.Thread(
            target=_watchdog, name="forge-sidecar-watchdog", daemon=True
        )
        _sidecar_monitor.start()


# ─────────────────────────────────────────────────────────────
# Event forwarder
# ─────────────────────────────────────────────────────────────

def _forward(event_type, payload):
    """POST event to sidecar. Fire-and-forget, never raises."""
    def _send():
        try:
            body = json.dumps({"event_type": event_type, "payload": payload}).encode()
            conn = http.client.HTTPConnection(SIDECAR_HOST, SIDECAR_PORT, timeout=2)
            conn.request("POST", "/event", body=body,
                         headers={"Content-Type": "application/json"})
            conn.getresponse()
            conn.close()
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


def _obj_to_dict(obj):
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
    # Intentionally empty — forge_bridge.py also defines app_initialized
    # and must own it to start the HTTP bridge. We launch the sidecar from
    # project_changed_dict which fires reliably after startup.
    pass


def project_changed_dict(info, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return

    # Launch sidecar here instead of app_initialized to avoid
    # overwriting forge_bridge.py's HTTP bridge startup
    _ensure_sidecar()
    _start_watchdog()

    try:
        payload = {
            "project_name": str(info.get("project_name", "")),
            "project_dir":  str(info.get("project_dir",  "")),
            "user_name":    str(info.get("user_name",    "")),
        }
    except Exception:
        payload = {"raw": str(info)}

    project_name = payload.get("project_name", "")
    if project_name:
        _log(f"Pipeline hook active — project: {project_name}")

    # Delay first event slightly so sidecar has time to bind its port
    threading.Timer(2.0, _forward, args=("project.changed", payload)).start()


def segment_created(segment, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _obj_to_dict(segment)
        try:
            seq = segment.parent
            payload["sequence_name"] = str(seq.name)
            payload["sequence_uid"]  = str(getattr(seq, "uid", ""))
        except Exception:
            pass
    except Exception as e:
        payload = {"error": str(e)}
    _forward("segment.created", payload)


def segment_deleted(segment, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _obj_to_dict(segment)
    except Exception as e:
        payload = {"error": str(e)}
    _forward("segment.deleted", payload)


def segment_renamed(segment, old_name, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _obj_to_dict(segment)
        payload["old_name"] = str(old_name)
    except Exception as e:
        payload = {"error": str(e)}
    _forward("segment.renamed", payload)


def batch_render_completed(info, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = {k: str(info.get(k, "")) for k in (
            "render_node_name", "render_path", "shot_name",
            "start_frame", "end_frame", "frame_rate",
        )}
    except Exception:
        payload = {"raw": str(info)}
    _forward("batch.render_completed", payload)


def media_imported(media, *args, **kwargs):
    if not PIPELINE_ENABLED:
        return
    try:
        payload = _obj_to_dict(media)
    except Exception as e:
        payload = {"error": str(e)}
    _forward("media.imported", payload)
