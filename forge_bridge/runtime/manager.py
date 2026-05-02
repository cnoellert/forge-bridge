"""Runtime manager — start/stop/observe forge-bridge servers as background processes.

The manager launches each server with ``subprocess.Popen`` in a new session
(detached from the CLI process group) and tracks PIDs in a JSON file under
``~/.forge-bridge/runtime.json`` (override via ``FORGE_RUNTIME_DIR``).

Architectural note: the Artist Console is co-hosted by the MCP HTTP server's
lifespan, so it does NOT have a standalone process. ``start_console()``
therefore reduces to "is :9996 reachable, and if not, start mcp_http".
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from forge_bridge import config

_TCP_PROBE_TIMEOUT = 0.5
_STOP_GRACE_SECONDS = 5.0
_STOP_POLL_INTERVAL = 0.25
_START_READY_TIMEOUT = 8.0


def _runtime_dir() -> Path:
    override = os.environ.get("FORGE_RUNTIME_DIR")
    if override:
        return Path(override)
    return Path.home() / ".forge-bridge"


def _runtime_file() -> Path:
    return _runtime_dir() / "runtime.json"


def _log_dir() -> Path:
    return _runtime_dir() / "logs"


# ── Service registry ──────────────────────────────────────────────────────
# Each entry is resolved lazily so config env overrides propagate.
def _services() -> dict[str, dict[str, Any]]:
    return {
        "mcp_http": {
            "host": config.mcp_http_host(),
            "port": config.mcp_http_port(),
            "argv": [sys.executable, "-m", "forge_bridge", "mcp", "http"],
            "log": "mcp_http.log",
        },
        "state_ws": {
            "host": config.state_ws_host(),
            "port": config.state_ws_port(),
            "argv": [sys.executable, "-m", "forge_bridge.server"],
            "log": "state_ws.log",
        },
    }


# ── Runtime state file ────────────────────────────────────────────────────
def _read_runtime() -> dict[str, Any]:
    path = _runtime_file()
    if not path.exists():
        return {"services": {}}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"services": {}}
    if not isinstance(data, dict) or "services" not in data:
        return {"services": {}}
    return data


def _write_runtime(state: dict[str, Any]) -> None:
    rd = _runtime_dir()
    rd.mkdir(parents=True, exist_ok=True)
    path = _runtime_file()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.replace(tmp, path)


# ── Process / port probes ─────────────────────────────────────────────────
def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _tcp_in_use(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=_TCP_PROBE_TIMEOUT):
            return True
    except OSError:
        return False


# ── Internal start/stop helpers ───────────────────────────────────────────
def _start(name: str) -> dict[str, Any]:
    spec = _services()[name]
    host, port = spec["host"], spec["port"]
    state = _read_runtime()
    services = state.setdefault("services", {})

    existing = services.get(name)
    # PR5: existing record with alive PID → forge-managed (we started it earlier).
    # An existing record with no PID is the "external" sentinel — fall through
    # to the port probe below.
    if existing and existing.get("pid") and _pid_alive(existing.get("pid")):
        return {
            "name": name, "started": False, "skipped": "already running",
            "pid": existing.get("pid"), "host": host, "port": port,
            "managed": True, "source": "forge",
        }

    if _tcp_in_use(host, port):
        record = {
            "pid": None, "host": host, "port": port,
            "started_at": time.time(), "argv": spec["argv"],
            "external": True,
        }
        services[name] = record
        _write_runtime(state)
        return {
            "name": name, "started": False, "skipped": "external (already running)",
            "pid": None, "host": host, "port": port,
            "managed": False, "source": "external",
        }

    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / spec["log"]
    log_fh = open(log_path, "ab", buffering=0)
    try:
        proc = subprocess.Popen(
            spec["argv"],
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(Path.home()),
        )
    finally:
        # Popen dups the fd; we can close ours.
        log_fh.close()

    record = {
        "pid": proc.pid, "host": host, "port": port,
        "started_at": time.time(), "argv": spec["argv"],
        "log": str(log_path),
    }
    services[name] = record
    _write_runtime(state)

    deadline = time.time() + _START_READY_TIMEOUT
    ready = False
    while time.time() < deadline:
        if not _pid_alive(proc.pid):
            break
        if _tcp_in_use(host, port):
            ready = True
            break
        time.sleep(0.2)

    return {
        "name": name, "started": True, "pid": proc.pid,
        "host": host, "port": port, "ready": ready, "log": str(log_path),
        "managed": True, "source": "forge",
    }


def _stop_one(name: str, rec: dict[str, Any]) -> dict[str, Any]:
    pid = rec.get("pid")
    # External record (no PID we own) — nothing to signal.
    if pid is None:
        return {
            "name": name, "stopped": False,
            "note": "external (no managed PID to stop)",
            "managed": False, "source": "external",
        }
    if not _pid_alive(pid):
        return {
            "name": name, "stopped": False, "note": "stale PID", "pid": pid,
            "managed": False, "source": "forge",
        }
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return {
            "name": name, "stopped": False, "note": "vanished", "pid": pid,
            "managed": False, "source": "forge",
        }

    deadline = time.time() + _STOP_GRACE_SECONDS
    while time.time() < deadline:
        if not _pid_alive(pid):
            return {
                "name": name, "stopped": True, "pid": pid, "method": "SIGTERM",
                "managed": True, "source": "forge",
            }
        time.sleep(_STOP_POLL_INTERVAL)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return {
            "name": name, "stopped": True, "pid": pid, "method": "SIGTERM",
            "managed": True, "source": "forge",
        }
    return {
        "name": name, "stopped": True, "pid": pid, "method": "SIGKILL",
        "managed": True, "source": "forge",
    }


# ── Public API ────────────────────────────────────────────────────────────
def start_console() -> dict[str, Any]:
    """Ensure the Artist Console (:9996) is reachable.

    The console is co-hosted by ``mcp_http`` via lifespan, so this checks
    the port and, if nothing is listening, starts ``mcp_http``.
    """
    host = config.console_host()
    port = config.console_port()
    if _tcp_in_use(host, port):
        return {"name": "console", "started": False, "skipped": "already serving",
                "host": host, "port": port}
    result = start_mcp_http()
    result["name"] = "console"
    result["host"] = host
    result["port"] = port
    result["note"] = "co-hosted with mcp_http"
    return result


def start_mcp_http() -> dict[str, Any]:
    return _start("mcp_http")


def start_state_ws() -> dict[str, Any]:
    return _start("state_ws")


def stop_all() -> list[dict[str, Any]]:
    state = _read_runtime()
    services = state.get("services", {})
    results: list[dict[str, Any]] = []
    for name in list(services.keys()):
        rec = services.get(name) or {}
        results.append(_stop_one(name, rec))
        del services[name]
    _write_runtime(state)
    return results


def status() -> dict[str, Any]:
    state = _read_runtime()
    services = state.get("services", {})
    dirty = False
    service_rows: list[dict[str, Any]] = []

    # Walk the registered services first so the derived `console` row can
    # inherit the mcp_http row's source (the console is co-hosted in that
    # process and has no PID of its own).
    for name, spec in _services().items():
        host, port = spec["host"], spec["port"]
        rec = services.get(name) or {}
        pid = rec.get("pid")
        alive = _pid_alive(pid) if pid else False
        port_open = _tcp_in_use(host, port)
        # Reconcile stale tracked PIDs that no longer back a port.
        if name in services and pid and not alive and not port_open:
            del services[name]
            dirty = True
        # PR5 semantics:
        #   managed=True  → we have an alive PID we started.
        #   managed=False → not ours (external port owner, or not running).
        managed = bool(alive)
        source = "forge" if managed else "external"
        service_rows.append({
            "name": name,
            "running": bool(alive or port_open),
            "tracked": name in services,  # back-compat field; new code uses managed/source
            "managed": managed,
            "source": source,
            "pid": pid if alive else None,
            "host": host,
            "port": port,
        })

    # Console row — co-hosted with mcp_http, so it inherits managed/source/pid.
    mcp_http_row = next((r for r in service_rows if r["name"] == "mcp_http"), None)
    console_host_v = config.console_host()
    console_port_v = config.console_port()
    console_running = _tcp_in_use(console_host_v, console_port_v)
    if mcp_http_row and console_running:
        console_managed = mcp_http_row["managed"]
        console_source = mcp_http_row["source"]
        console_pid = mcp_http_row["pid"]
    else:
        console_managed = False
        console_source = "external"
        console_pid = None
    console_row = {
        "name": "console",
        "running": console_running,
        "tracked": False,
        "managed": console_managed,
        "source": console_source,
        "pid": console_pid,
        "host": console_host_v,
        "port": console_port_v,
    }

    if dirty:
        _write_runtime(state)
    return {"services": [console_row, *service_rows]}
