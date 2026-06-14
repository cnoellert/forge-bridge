"""Top-level ``forge-bridge doctor`` — runtime topology probe.

Distinct from the legacy ``console doctor`` (which inspects the running
console process in depth). This one answers the operator's first
question — "what's running on this box, and what should I do next?" — by
probing each surface at the URL it should be at and reporting a stable
shape:

    {"ok": bool, "checks": [{"name", "ok", "status", "url", "fix"}, ...]}

Human mode prints a Rich table plus a one-line "Suggested next action".
"""
from __future__ import annotations

import asyncio
import json
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

import httpx
import typer
from rich.table import Table

from forge_bridge import config
from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console, status_chip
from forge_bridge.runtime.graph_emit import graph_dir

_HTTP_TIMEOUT = 1.5
_TCP_TIMEOUT = 1.0
# Phase 24.2: daemon-routed flame_bridge probe runs flame_ping through the
# chain engine; allow more time than a passive HEAD because the daemon round-
# trips to the Flame hook before responding.
_EXEC_PROBE_TIMEOUT = 5.0
_RECENT_ACTIVITY_WINDOW = timedelta(hours=24)


def runtime_doctor_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit a stable JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Probe forge-bridge surfaces and report status, URLs, and next steps."""
    checks: list[dict[str, Any]] = [
        _check_console(),
        _check_install_provenance(),
        _check_mcp_http(),
        _check_flame_bridge(),
        _check_state_ws(),
        _check_ratification(),
        _check_graph_store(),
    ]
    overall_ok = all(c["ok"] for c in checks)

    if as_json:
        payload = {"ok": overall_ok, "checks": checks}
        sys.stdout.write(json.dumps(payload) + "\n")
        raise typer.Exit(code=0 if overall_ok else 1)

    _render_human(checks, overall_ok, no_color=no_color)
    raise typer.Exit(code=0 if overall_ok else 1)


# ── individual probes ─────────────────────────────────────────────────────

def _check_console() -> dict[str, Any]:
    url = config.console_url()
    health_url = f"{url}/api/v1/health"
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            r = client.get(health_url)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        return {
            "name": "console",
            "ok": False,
            "status": f"unreachable ({type(exc).__name__})",
            "url": url,
            "fix": "start the console + MCP server: `python -m forge_bridge mcp http`",
        }
    if r.status_code != 200:
        return {
            "name": "console",
            "ok": False,
            "status": f"http {r.status_code}",
            "url": url,
            "fix": "console responded but not 200 — check `forge-bridge console doctor`",
        }
    return {
        "name": "console",
        "ok": True,
        "status": "running",
        "url": url,
        "fix": "",
    }


def _check_install_provenance() -> dict[str, Any]:
    """Surface the daemon's loaded-code provenance as a first-class doctor row.

    Operational invariant established by the 24.6 + D-04 dogfood sessions:
    operators should always know what code the daemon is serving before
    interpreting behavioral observations. Reads the `install_provenance`
    block from /api/v1/health (added daemon-side in the preceding commit)
    and compares against the operator's CWD repo context.

    Three comparisons feed the verdict:

      drift          daemon.startup_sha vs daemon.disk_sha_now (same path)
      cross-repo     daemon.repo_root  vs operator CWD's repo root
      cross-commit   daemon.startup_sha vs operator CWD's HEAD SHA

    Green requires ALL THREE: provenance known, no drift, matches the
    operator's CWD checkout/HEAD. NOT "matches main" — every feature
    branch would otherwise produce a false warning. Warns for: drift
    (daemon stale vs disk), missing git metadata (detached / wheel
    install), cross-checkout state, or same-repo different-commit.
    Operator CWD outside any git repo: comparison skipped rather than
    warned (running doctor from ~/ or /tmp shouldn't generate noise).

    Output preserves raw facts (SHAs short-form + paths) alongside the
    interpreted verdict so operators can reason from underlying state,
    not from a synthesized conclusion alone.
    """
    url = config.console_url()
    health_url = f"{url}/api/v1/health"
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            r = client.get(health_url)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        return _provenance_warn(
            f"console unreachable ({type(exc).__name__}) — provenance unavailable",
            url=url,
            fix="see console row above",
        )
    if r.status_code != 200:
        return _provenance_warn(
            f"console http {r.status_code} — provenance unavailable",
            url=url,
            fix="see console row above",
        )
    try:
        body = r.json()
    except ValueError:
        return _provenance_warn(
            "console returned non-JSON — provenance unavailable",
            url=url,
            fix="see console row above",
        )

    # /api/v1/health wraps the get_health() body in the standard
    # {data, meta} envelope (handlers.py:408 -> _envelope). The CLI fetch()
    # helper auto-unwraps; we use raw httpx.Client to avoid coupling this
    # probe to the helper's error-translation layer, so we unwrap here.
    data = body.get("data") or {}
    prov = data.get("install_provenance") or {}
    if not prov:
        return _provenance_warn(
            "daemon does not report install_provenance — incompatible version",
            url=url,
            fix="restart the daemon from a build that includes "
                "forge_bridge.install_provenance",
        )

    daemon_path = prov.get("import_path") or "<unknown>"
    daemon_repo = prov.get("repo_root")
    daemon_startup = prov.get("startup_sha")
    daemon_disk = prov.get("disk_sha_now")

    if not daemon_repo or not daemon_startup:
        return _provenance_warn(
            f"daemon path={daemon_path} (no git metadata — "
            f"detached/unknown provenance)",
            url=daemon_path,
            fix="daemon was installed from a non-git source; provenance "
                "cannot be verified",
        )

    daemon_basename = Path(daemon_repo).name

    # Drift: daemon's loaded code differs from current disk at SAME path
    if daemon_disk and daemon_disk != daemon_startup:
        return {
            "name": "install_provenance",
            "ok": False,
            "chip": "warn",
            "status": (
                f"daemon serving {daemon_startup[:8]}; disk advanced to "
                f"{daemon_disk[:8]} @ {daemon_basename} — restart to load latest"
            ),
            "url": daemon_path,
            "fix": "restart the daemon process to pick up the on-disk state",
        }

    cwd_repo, cwd_sha = _operator_repo_context()

    if not cwd_repo or not cwd_sha:
        return {
            "name": "install_provenance",
            "ok": True,
            "status": (
                f"daemon {daemon_startup[:8]} @ {daemon_basename} "
                f"(operator CWD not in a git repo; comparison skipped)"
            ),
            "url": daemon_path,
            "fix": "",
        }

    if Path(cwd_repo).resolve() != Path(daemon_repo).resolve():
        cwd_basename = Path(cwd_repo).name
        return {
            "name": "install_provenance",
            "ok": False,
            "chip": "warn",
            "status": (
                f"daemon serves from {daemon_basename}; operator CWD in "
                f"{cwd_basename} — different checkouts"
            ),
            "url": daemon_path,
            "fix": (
                f"daemon imports from {daemon_repo}; your CWD is in "
                f"{cwd_repo} — restart the daemon from your active checkout, "
                f"or accept the cross-checkout state"
            ),
        }

    if cwd_sha != daemon_startup:
        return {
            "name": "install_provenance",
            "ok": False,
            "chip": "warn",
            "status": (
                f"daemon serving {daemon_startup[:8]}; operator CWD at "
                f"{cwd_sha[:8]} @ {daemon_basename} — different commits, "
                f"same repo"
            ),
            "url": daemon_path,
            "fix": (
                "restart the daemon to load your active commit, OR "
                "checkout the daemon's commit in your CWD"
            ),
        }

    return {
        "name": "install_provenance",
        "ok": True,
        "status": (
            f"daemon {daemon_startup[:8]} @ {daemon_basename} matches "
            f"operator CWD"
        ),
        "url": daemon_path,
        "fix": "",
    }


def _provenance_warn(status: str, *, url: str, fix: str) -> dict[str, Any]:
    """Build a warn-chip provenance row — used for unreachable / missing-field
    branches where we can't fully evaluate the verdict but want to surface
    the gap to the operator rather than silently passing."""
    return {
        "name": "install_provenance",
        "ok": False,
        "chip": "warn",
        "status": status,
        "url": url,
        "fix": fix,
    }


def _operator_repo_context() -> tuple[Optional[str], Optional[str]]:
    """Resolve the operator's CWD containing-git-repo root and HEAD SHA.

    Returns (None, None) if CWD is not inside a git checkout — the probe
    treats this as comparison-skipped, not as a warning.
    """
    from forge_bridge.install_provenance import find_repo_root, git_head

    cwd = Path.cwd()
    repo = find_repo_root(cwd)
    if not repo:
        return None, None
    return str(repo), git_head(repo)


def _check_mcp_http() -> dict[str, Any]:
    """Probe MCP HTTP transport with a TCP connect.

    streamable-http exposes JSON-RPC under ``/mcp`` and rejects bare GETs,
    so a TCP listen check is the cheapest reliable liveness probe — and
    matches what we can do for the WebSocket port.
    """
    host = config.mcp_http_host()
    port = config.mcp_http_port()
    url = config.mcp_http_url()
    if _tcp_reachable(host, port):
        return {
            "name": "mcp_http",
            "ok": True,
            "status": "listening",
            "url": url,
            "fix": "",
        }
    return {
        "name": "mcp_http",
        "ok": False,
        "status": "not listening",
        "url": url,
        "fix": "start the MCP HTTP server: `python -m forge_bridge mcp http`",
    }


def _check_flame_bridge() -> dict[str, Any]:
    """Daemon-routed Flame bridge dispatch probe (Phase 24.2).

    Probes the running daemon (Console on :9996) via
    ``POST /api/v1/exec {"tool": "flame_ping"}`` — the DETERMINISTIC exact-name
    dispatch, NOT the NL ``text`` path. The text path runs through
    ``filter_tools_by_reachable_backends``, which strips ``flame_ping`` from the
    resolvable set precisely when Flame is unreachable (the condition this probe
    exists to detect), so the resolver returns ``clarification_needed`` and a
    benign Flame-down misreports as a chain-engine error ("check daemon logs").
    The ``{"tool": ...}`` path dispatches ``flame_ping`` directly in the daemon's
    process — preserving the daemon-routed truth invariant — and bypasses the
    filter, so ``flame_ping`` always runs and echoes the daemon's effective
    ``bridge.BRIDGE_URL`` plus ``connected`` (see ``tools/utility.py:ping``).
    Doctor compares the daemon-effective URL against its own re-derived
    ``config.flame_bridge_url()`` to detect config-context divergence (e.g.
    shell env vs launchd env disagreeing on ``FORGE_BRIDGE_PORT``).

    Architectural invariant (Phase 24.2): the health surface reflects
    daemon-observed dispatch truth, not independently reconstructed local
    truth. Doctor never falls back to a re-derived local probe under
    degradation — daemon truth or no truth.

    Four operational states:
      OK         daemon reachable, ``connected=true``, daemon's bridge_url
                 matches doctor's re-derived URL
      WARN       daemon reachable, daemon's bridge_url disagrees with
                 doctor's re-derived URL (config-context divergence)
      FAIL       daemon reachable, daemon reports ``connected=false`` (URLs
                 agree but Flame is unreachable from the daemon)
      UNKNOWN    daemon unreachable; links to ``mcp_http`` row
    """
    shell_url = config.flame_bridge_url()
    exec_url = f"{config.console_url()}/api/v1/exec"

    try:
        with httpx.Client(timeout=_EXEC_PROBE_TIMEOUT) as client:
            r = client.post(exec_url, json={"tool": "flame_ping"})
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": f"unknown (daemon unreachable: {type(exc).__name__})",
            "url": shell_url,
            "fix": "daemon not running or not reachable — see mcp_http row",
        }

    if r.status_code != 200:
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": f"unknown (daemon http {r.status_code})",
            "url": shell_url,
            "fix": "daemon /api/v1/exec returned non-200 — see mcp_http row",
        }

    try:
        envelope = r.json()
    except ValueError:
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": "unknown (daemon returned malformed envelope)",
            "url": shell_url,
            "fix": "daemon /api/v1/exec returned invalid JSON — restart the daemon",
        }

    envelope_status = envelope.get("status")

    # Guard: clarification means flame_ping was not deterministically
    # dispatchable (e.g. an older daemon still on the NL ``text`` probe path
    # where the reachability filter removed the tool). This is NOT a chain-engine
    # error to chase in the logs — it almost always means Flame is simply down.
    if envelope_status == "clarification_needed":
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": "unknown (flame_ping not deterministically dispatchable)",
            "url": shell_url,
            "fix": (
                "flame_ping could not be dispatched as a tool — Flame is likely "
                "down (its tool is filtered out of the resolver when the backend "
                "is unreachable). Start Flame with the forge-bridge hook loaded, "
                "or update the daemon if it predates the {\"tool\": ...} exec path."
            ),
        }

    if envelope_status != "success":
        err = envelope.get("error") or {}
        code = err.get("code") or "unknown"
        # unknown_action: the daemon has no flame_ping tool registered at all —
        # a registration/install problem, distinct from a chain-engine error.
        if code == "unknown_action":
            return {
                "name": "flame_bridge",
                "ok": False,
                "status": "unknown (flame_ping tool not registered)",
                "url": shell_url,
                "fix": (
                    "daemon has no flame_ping tool registered — restart the "
                    "daemon, or verify the forge-bridge install (see mcp_http row)"
                ),
            }
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": f"daemon dispatch failed ({code})",
            "url": shell_url,
            "fix": err.get("message") or
                   "daemon chain engine returned error — check daemon logs",
        }

    chain = envelope.get("chain") or []
    if not chain:
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": "unknown (daemon returned empty chain)",
            "url": shell_url,
            "fix": "daemon /api/v1/exec returned no chain steps — restart the daemon",
        }

    ping_result = chain[0].get("result")
    if not isinstance(ping_result, dict):
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": "unknown (flame_ping returned non-dict result)",
            "url": shell_url,
            "fix": "daemon returned unexpected flame_ping shape — restart the daemon",
        }

    daemon_url = ping_result.get("bridge_url")
    connected = bool(ping_result.get("connected"))

    if daemon_url and daemon_url != shell_url:
        # WARN — config-context divergence between doctor and daemon
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": (
                f"dispatch target mismatch — daemon={daemon_url} "
                f"shell={shell_url}"
            ),
            "url": daemon_url,  # daemon-effective is authoritative
            "fix": (
                "FORGE_BRIDGE_HOST/PORT is set differently in the daemon's "
                "environment than in your shell. Unset it in the daemon's "
                "launchd/systemd env and restart the daemon, OR set it in "
                "your shell to match. See docs/TROUBLESHOOTING.md."
            ),
        }

    if not connected:
        # FAIL — daemon reports Flame unreachable; URLs agree
        ping_err = ping_result.get("error") or ""
        suffix = f" ({ping_err})" if ping_err else ""
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": f"daemon reports flame disconnected{suffix}",
            "url": daemon_url or shell_url,
            "fix": (
                "daemon's dispatch path is correct but Flame isn't reachable "
                "— start Flame with the forge-bridge hook loaded "
                "(see `./scripts/install-flame-hook.sh`) or open a project"
            ),
        }

    return {
        "name": "flame_bridge",
        "ok": True,
        "status": f"running (daemon dispatches {daemon_url})",
        "url": daemon_url,
        "fix": "",
    }


def _check_state_ws() -> dict[str, Any]:
    host = config.state_ws_host()
    port = config.state_ws_port()
    url = config.state_ws_url()
    if _tcp_reachable(host, port):
        return {
            "name": "state_ws",
            "ok": True,
            "status": "listening",
            "url": url,
            "fix": "",
        }
    return {
        "name": "state_ws",
        "ok": False,
        "status": "not listening",
        "url": url,
        "fix": "the State WebSocket server is optional — see docs/ARCHITECTURE.md "
               "if you need it for your workflow",
    }


def _check_ratification() -> dict[str, Any]:
    """Probe recent AssentRecord activity in the database."""
    from forge_bridge.store.session import get_db_url

    url = get_db_url()
    window_label = _format_recent_window(_RECENT_ACTIVITY_WINDOW)
    try:
        count = asyncio.run(_recent_ratification_count(_RECENT_ACTIVITY_WINDOW))
    except Exception as exc:
        return {
            "name": "ratification",
            "ok": False,
            "chip": "fail",
            "status": f"db unreachable ({type(exc).__name__})",
            "url": url,
            "fix": "check Postgres and run `alembic upgrade head`",
        }

    if count > 0:
        return {
            "name": "ratification",
            "ok": True,
            "chip": "ok",
            "status": f"{count} ratifications in last {window_label}",
            "url": url,
            "fix": "",
        }
    return {
        "name": "ratification",
        "ok": True,
        "chip": "loaded",
        "status": f"no ratifications in last {window_label}",
        "url": url,
        "fix": "",
    }


async def _recent_ratification_count(window: timedelta) -> int:
    from forge_bridge.store.assent_record_repo import AssentRecordRepo
    from forge_bridge.store.session import get_session

    cutoff = datetime.now(timezone.utc) - window
    count = 0
    async with get_session() as session:
        repo = AssentRecordRepo(session)
        for status in ("ratified", "applied", "failed"):
            records, _ = await repo.list_pending(status=status)
            for record in records:
                decided_at = record.decided_at
                if decided_at is None:
                    continue
                if decided_at.tzinfo is None:
                    decided_at = decided_at.replace(tzinfo=timezone.utc)
                if decided_at >= cutoff:
                    count += 1
    return count


def _format_recent_window(window: timedelta) -> str:
    total_seconds = int(window.total_seconds())
    if total_seconds % 3600 == 0:
        return f"{total_seconds // 3600}h"
    if total_seconds % 60 == 0:
        return f"{total_seconds // 60}m"
    return f"{total_seconds}s"


def _check_graph_store() -> dict[str, Any]:
    """Probe the Phase 24 JSONL graph store substrate.

    Tri-state per ``v1.6-WRITERS-ROOM-CONVERGENCE.md`` Q18 operator framing:

    - ``ok`` (chip ``ok``): directory exists, files present, newest is parseable.
      Substrate is installed AND exercised.
    - ``ok`` (chip ``loaded``): directory missing OR empty. Substrate installed
      but not yet exercised — normal on fresh install. Preserves the
      operational distinction operator framed at convergence (substrate
      installed != substrate exercised).
    - ``fail`` (chip ``fail``): directory present but unreadable, or newest
      file contains zero parseable records (structural error).

    Scope discipline per operator direction:
    no event counts, no topology reconstruction, no analytics, no retention
    logic, no summaries. Status / dir / file count / newest timestamp /
    parseability verdict. That's it. Doctor teaches existence + health;
    ``fbridge graph list/show`` is the browser.
    """
    target = graph_dir()
    url = str(target)

    if not target.exists():
        return {
            "name": "graph_store",
            "ok": True,
            "chip": "loaded",
            "status": "not yet created (no graphs recorded)",
            "url": url,
            "fix": "the graph store gets created at first emit — "
                   "try `fbridge chat \"what is running\"` to exercise it",
        }

    try:
        files = sorted(
            target.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError as exc:
        return {
            "name": "graph_store",
            "ok": False,
            "chip": "fail",
            "status": f"directory unreadable ({type(exc).__name__})",
            "url": url,
            "fix": f"check permissions on {target}",
        }

    if not files:
        return {
            "name": "graph_store",
            "ok": True,
            "chip": "loaded",
            "status": "no graphs recorded",
            "url": url,
            "fix": "the graph store exists but is empty — "
                   "try `fbridge chat \"what is running\"` to exercise it",
        }

    newest = files[0]
    parseable, newest_timestamp = _sample_parseability(newest)
    file_count = len(files)

    if not parseable:
        return {
            "name": "graph_store",
            "ok": False,
            "chip": "fail",
            "status": (
                f"{file_count} graphs, newest unparseable ({newest.name})"
            ),
            "url": url,
            "fix": f"newest graph file contains no parseable records — "
                   f"inspect {newest}",
        }

    return {
        "name": "graph_store",
        "ok": True,
        "chip": "ok",
        "status": (
            f"{file_count} graphs, last {newest_timestamp or '<no timestamp>'}"
        ),
        "url": url,
        "fix": "",
    }


def _sample_parseability(path: Path) -> tuple[bool, str]:
    """Return (any_record_parseable, newest_record_timestamp_or_empty).

    Read-only sample of one file. We do NOT enumerate every record — that's
    fbridge graph show's job. Doctor just asks: does at least one record in
    the newest file parse, and what's its timestamp?
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            last_timestamp = ""
            any_parsed = False
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    any_parsed = True
                    ts = rec.get("timestamp")
                    if isinstance(ts, str) and ts:
                        last_timestamp = ts
            return any_parsed, last_timestamp
    except OSError:
        return False, ""


def _tcp_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=_TCP_TIMEOUT):
            return True
    except (OSError, socket.timeout):
        return False


# ── human renderer ────────────────────────────────────────────────────────

def _render_human(
    checks: list[dict[str, Any]],
    overall_ok: bool,
    *,
    no_color: bool,
) -> None:
    console = make_console(no_color=no_color)
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Surface")
    table.add_column("Status")
    table.add_column("URL")
    for c in checks:
        # Rows may override the chip keyword to express tri-state (e.g.
        # graph_store: ok+loaded when substrate installed but unexercised).
        # JSON envelope keeps ok=bool for back-compat; chip is presentation-only.
        chip_keyword = c.get("chip") or ("ok" if c["ok"] else "fail")
        table.add_row(
            c["name"],
            status_chip(chip_keyword),
            f"{c['status']}  {c['url']}",
        )
    console.print(table)

    if overall_ok:
        console.print("Suggested next action: all surfaces are running. "
                      "Open the Artist Console at "
                      f"{config.console_url()}/ui/.")
        return

    first_fail = next((c for c in checks if not c["ok"]), None)
    if first_fail and first_fail.get("fix"):
        console.print(f"Suggested next action: {first_fail['fix']}")
    else:
        console.print("Suggested next action: see per-surface fix hints above.")
