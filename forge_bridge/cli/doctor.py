"""forge-bridge console doctor — expanded diagnostic with CI-gating exit codes.

Probes /api/v1/health AND client-side: JSONL parseability, sidecar/probation dir
presence + writability, console-port re-confirm, optional disk-space.

Exit codes:
  0 — all ok or warn-only
  1 — any fail
  2 — server unreachable on initial probe
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
from rich.table import Table

from forge_bridge.cli.client import (
    ServerError,
    ServerUnreachableError,
    fetch,
    resolve_port,
)
from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console, status_chip

logger = logging.getLogger(__name__)

_UNREACHABLE_STDERR = (
    "forge-bridge console: server is not running on :9996.\n"
    "Start it with: python -m forge_bridge"
)
_UNREACHABLE_JSON = {
    "error": {"code": "server_unreachable", "message": _UNREACHABLE_STDERR}
}
_DISK_WARN_BYTES = 100 * 1024 * 1024  # 100 MB
_DISK_FAIL_BYTES = 10 * 1024 * 1024   # 10 MB
_CRITICAL_SERVICES = ("mcp", "watcher")  # plus instance_identity (handled separately)


def doctor_cmd(
    as_json: Annotated[bool, typer.Option("--json")] = False,
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
    quiet: Annotated[bool, typer.Option("--quiet")] = False,
) -> None:
    """Run an expanded diagnostic across the bridge — CI-gating exit codes.

    Examples:
      forge-bridge console doctor
    """
    # Probe 1: /api/v1/health — if it fails, exit 2 immediately (no further probes).
    try:
        health_data = fetch("/api/v1/health")
    except ServerUnreachableError:
        if as_json:
            sys.stdout.write(json.dumps(_UNREACHABLE_JSON) + "\n")
        else:
            stderr_console = make_console(no_color=no_color, stderr=True)
            stderr_console.print(_UNREACHABLE_STDERR)
        raise typer.Exit(code=2)
    except ServerError as e:
        if as_json:
            sys.stdout.write(json.dumps({
                "error": {"code": e.code, "message": e.message}
            }) + "\n")
        else:
            make_console(stderr=True).print(f"error: {e.code}: {e.message}")
        raise typer.Exit(code=1)

    # Run all client-side probes
    checks: list[dict[str, Any]] = []
    checks.extend(_health_to_checks(health_data))
    checks.append(_check_jsonl_parseability())
    checks.append(_check_sidecar_writable())
    checks.append(_check_probation_writable())
    checks.append(_check_console_port_reconfirm())
    disk_check = _check_disk_space()
    if disk_check is not None:
        checks.append(disk_check)

    # Compute exit code from check results
    any_fail = any(c["status"] == "fail" for c in checks)
    exit_code = 1 if any_fail else 0

    if as_json:
        sys.stdout.write(
            json.dumps({"data": {"checks": checks, "exit_code": exit_code}}) + "\n"
        )
        raise typer.Exit(code=exit_code)

    # Rich rendering
    console = make_console(no_color=no_color)
    if quiet:
        for c in checks:
            console.print(f"{c['name']}\t{c['status']}\t{c.get('fact', '')}")
        raise typer.Exit(code=exit_code)

    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Fact")
    table.add_column("Try")
    for c in checks:
        table.add_row(
            c["name"],
            status_chip(c["status"]),
            c.get("fact", ""),
            c.get("try", ""),
        )
    console.print(table)
    raise typer.Exit(code=exit_code)


def _health_to_checks(data: dict) -> list[dict]:
    """Translate /api/v1/health response into doctor check rows.

    Critical services (mcp/watcher/instance_identity) → fail
    Degraded services (LLM, storage, flame, ws) → warn
    """
    out: list[dict] = []
    services = data.get("services", {}) or {}
    for svc_name in _CRITICAL_SERVICES:
        info = services.get(svc_name, {}) or {}
        raw = info.get("status", "unknown")
        status = "ok" if raw == "ok" else "fail"
        out.append({
            "name": svc_name,
            "status": status,
            "fact": info.get("detail", "") or raw,
            "try": "" if status == "ok" else f"check that {svc_name} subsystem is initialized",
        })
    # Console port (critical)
    cp = services.get("console_port", {}) or {}
    cp_status = "ok" if cp.get("status") == "ok" else "fail"
    out.append({
        "name": "console_port",
        "status": cp_status,
        "fact": cp.get("detail", "") or cp.get("status", ""),
        "try": ""
        if cp_status == "ok"
        else "ensure :9996 is bound (server may have failed to start its console task)",
    })
    # Instance identity (critical)
    ii = data.get("instance_identity", {}) or {}
    for key in ("execution_log", "manifest_service"):
        sub = ii.get(key, {}) or {}
        ok = bool(sub.get("id_match"))
        out.append({
            "name": f"instance_identity.{key}",
            "status": "ok" if ok else "fail",
            "fact": sub.get("detail", "") or ("canonical" if ok else "duplicate detected"),
            "try": ""
            if ok
            else "ensure _lifespan owns the canonical singleton (Phase 9 API-04)",
        })
    # Degraded-tolerant: flame_bridge, ws_server, storage_callback → warn
    for svc_name in ("flame_bridge", "ws_server", "storage_callback"):
        info = services.get(svc_name, {}) or {}
        raw = info.get("status", "absent")
        if raw == "ok":
            status = "ok"
        else:
            status = "warn"  # absent or degraded — non-blocking
        out.append({
            "name": svc_name,
            "status": status,
            "fact": info.get("detail", "") or raw,
            "try": ""
            if status == "ok"
            else f"{svc_name} is degraded — system continues operating without it",
        })
    # LLM backends — each warn
    for backend in services.get("llm_backends") or []:
        name = backend.get("name", "llm_backend")
        raw = backend.get("status", "absent")
        status = "ok" if raw == "ok" else "warn"
        out.append({
            "name": f"llm_backend.{name}",
            "status": status,
            "fact": backend.get("detail", "") or raw,
            "try": ""
            if status == "ok"
            else f"check {name} backend reachability (degraded-tolerant)",
        })
    return out


def _check_jsonl_parseability() -> dict:
    """T-11-02 mitigation: read-only tail-parse with no locking.

    Reports parse failures by line number + exception class name only — never
    raw line content (LRN-05 / T-11-01 credential-leak rule).
    """
    path = Path(os.environ.get(
        "FORGE_EXECUTION_LOG_PATH",
        os.path.expanduser("~/.forge-bridge/executions.jsonl"),
    ))
    if not path.exists():
        return {
            "name": "jsonl_parseability",
            "status": "warn",
            "fact": f"log file not found at {path}",
            "try": "execution log not yet created — runs will create it",
        }
    try:
        tail = _tail_jsonl(str(path), n=100)
    except OSError as exc:
        return {
            "name": "jsonl_parseability",
            "status": "fail",
            "fact": f"could not read log: {type(exc).__name__}",
            "try": "check filesystem permissions on the log directory",
        }
    failures: list[str] = []
    for i, line in enumerate(tail):
        try:
            json.loads(line)
        except json.JSONDecodeError as exc:
            # T-11-01 / LRN-05: NEVER include the raw line — only its number + exception class
            failures.append(f"line {i}: {type(exc).__name__}")
    if failures:
        return {
            "name": "jsonl_parseability",
            "status": "fail",
            "fact": f"{len(failures)} parse error(s); {failures[0]}",
            "try": "inspect ~/.forge-bridge/executions.jsonl tail for malformed entries",
        }
    return {
        "name": "jsonl_parseability",
        "status": "ok",
        "fact": f"{len(tail)} line(s) tail-parsed cleanly",
        "try": "",
    }


def _tail_jsonl(path: str, n: int = 100) -> list[str]:
    """Read last n lines without acquiring any lock. T-11-02 mitigation.

    Skips the last line if it lacks a trailing newline (concurrent-writer guard).
    """
    with open(path, "r") as f:
        lines = f.readlines()
    tail = lines[-n:] if len(lines) >= n else lines
    if tail and not tail[-1].endswith("\n"):
        tail = tail[:-1]
    return [line.rstrip("\n") for line in tail if line.strip()]


def _check_sidecar_writable() -> dict:
    path = Path(os.path.expanduser("~/.forge-bridge/synthesized/"))
    return _check_dir_writable("sidecar_dir", path)


def _check_probation_writable() -> dict:
    path = Path(os.path.expanduser("~/.forge-bridge/probation/"))
    return _check_dir_writable("probation_dir", path)


def _check_dir_writable(name: str, path: Path) -> dict:
    if not path.exists():
        return {
            "name": name,
            "status": "warn",
            "fact": f"directory does not exist at {path}",
            "try": f"create it: mkdir -p {path}",
        }
    if not os.access(path, os.W_OK):
        return {
            "name": name,
            "status": "fail",
            "fact": f"directory not writable: {path}",
            "try": f"chmod u+w {path}",
        }
    return {"name": name, "status": "ok", "fact": str(path), "try": ""}


def _check_console_port_reconfirm() -> dict:
    """Re-probe :9996 directly to detect lying-health-body case (Area 1)."""
    port = resolve_port()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2.0) as client:
            r = client.get("/api/v1/health")
        if r.status_code == 200:
            return {
                "name": "console_port_reprobe",
                "status": "ok",
                "fact": f"http {r.status_code} on :{port}",
                "try": "",
            }
        return {
            "name": "console_port_reprobe",
            "status": "fail",
            "fact": f"http {r.status_code} on :{port}",
            "try": "server is responding but reports an error status",
        }
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        # T-11-01: surface the exception class name only — never str(exc).
        return {
            "name": "console_port_reprobe",
            "status": "fail",
            "fact": f"reprobe failed: {type(exc).__name__}",
            "try": "the initial /api/v1/health call succeeded but the reprobe failed — "
                   "transient or a host-only resolution issue",
        }


def _check_disk_space() -> "dict | None":
    path = Path(os.path.expanduser("~/.forge-bridge/"))
    if not path.exists():
        return None
    try:
        free = shutil.disk_usage(str(path)).free
    except OSError:
        return None
    if free < _DISK_FAIL_BYTES:
        return {
            "name": "disk_space",
            "status": "fail",
            "fact": f"{free // (1024 * 1024)} MB free at {path}",
            "try": "free disk space — execution log appends will fail soon",
        }
    if free < _DISK_WARN_BYTES:
        return {
            "name": "disk_space",
            "status": "warn",
            "fact": f"{free // (1024 * 1024)} MB free at {path}",
            "try": "consider freeing disk space — log directory has < 100 MB",
        }
    return {
        "name": "disk_space",
        "status": "ok",
        "fact": f"{free // (1024 * 1024)} MB free",
        "try": "",
    }
