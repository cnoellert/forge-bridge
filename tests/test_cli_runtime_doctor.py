"""Tests for the new top-level `forge-bridge doctor` (runtime topology probe).

Covers the stable JSON shape from PR2 spec:
    {"ok": bool, "checks": [{"name", "ok", "status", "url", "fix"}, ...]}
"""
from __future__ import annotations

import json
from unittest.mock import patch

import httpx
from typer.testing import CliRunner

from forge_bridge import config
from forge_bridge.__main__ import app

runner = CliRunner()


# ── HTTP and TCP fakes ────────────────────────────────────────────────────

class _Resp:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class _Client:
    """Routes httpx.Client.get/.post to per-URL handler dicts.

    Phase 24.2: `_check_flame_bridge` now POSTs to ``:9996/api/v1/exec``
    instead of GETting ``:9999/status``; the test fake supports both verbs.
    """

    def __init__(self, *, handlers, post_handlers=None, **_kwargs):
        self._handlers = handlers
        self._post_handlers = post_handlers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def get(self, url):
        for prefix, handler in self._handlers.items():
            if url.startswith(prefix):
                if isinstance(handler, BaseException):
                    raise handler
                return handler
        raise httpx.ConnectError(f"no handler for {url}")

    def post(self, url, *, json=None, **_kwargs):
        for prefix, handler in self._post_handlers.items():
            if url.startswith(prefix):
                if isinstance(handler, BaseException):
                    raise handler
                if callable(handler):
                    return handler(json)
                return handler
        raise httpx.ConnectError(f"no POST handler for {url}")


def _flame_ping_envelope(
    *,
    connected: bool = True,
    bridge_url: str | None = None,
    error: str | None = None,
) -> _Resp:
    """Build a PR31 envelope wrapping a flame_ping result body.

    Mirrors ``forge_bridge/console/_engine.py:run_chain_steps`` success shape
    and ``forge_bridge/tools/utility.py:ping`` body shape.
    """
    body: dict = {"connected": connected}
    if bridge_url is not None:
        body["bridge_url"] = bridge_url
    if connected:
        body.update({
            "version": "2026.0.0",
            "project": "test_project",
            "current_tab": "Conform",
        })
    if error:
        body["error"] = error
    return _Resp(200, {
        "status": "success",
        "request_id": "test-rid",
        "chain": [{"step": "flame_ping", "result": body}],
        "error": None,
    })


def _health_body_ok(*, install_provenance: dict | None = None) -> dict:
    """Happy-path /api/v1/health body — install_provenance matches operator CWD.

    Defaults to a provenance block where startup_sha == disk_sha_now ==
    operator CWD HEAD, so the install_provenance probe returns ok. Pass
    `install_provenance=` to override for warn-state tests, or pass an
    empty dict to simulate a daemon that does not report the field
    (incompatible-version warn branch).
    """
    if install_provenance is None:
        from pathlib import Path as _P
        from forge_bridge.install_provenance import find_repo_root, git_head
        cwd_repo = find_repo_root(_P.cwd())
        cwd_sha = git_head(cwd_repo) if cwd_repo else None
        install_provenance = {
            "import_path": (
                str(cwd_repo / "forge_bridge") if cwd_repo else "/tmp/forge_bridge"
            ),
            "repo_root": str(cwd_repo) if cwd_repo else None,
            "startup_sha": cwd_sha,
            "pid": 99999,
            "started_at": "2026-05-18T22:00:00+00:00",
            "disk_sha_now": cwd_sha,
        }
    return {"status": "ok", "install_provenance": install_provenance}


def _default_post_handlers() -> dict:
    """Default Phase 24.2 POST handlers — convergent flame_ping at exec URL.

    Test cases that exercise WARN/FAIL/UNKNOWN states override this.
    """
    return {
        config.console_url() + "/api/v1/exec": _flame_ping_envelope(
            connected=True,
            bridge_url=config.flame_bridge_url(),
        ),
    }


def _patch_world(
    handlers,
    *,
    tcp_open: set[tuple[str, int]] | None = None,
    post_handlers: dict | None = None,
):
    """Patch httpx.Client and socket.create_connection together."""
    open_pairs = tcp_open or set()
    if post_handlers is None:
        post_handlers = _default_post_handlers()

    def _fake_create_connection(addr, timeout=None):
        if tuple(addr) in open_pairs:
            class _Sock:
                def close(self_inner): ...
                def __enter__(self_inner): return self_inner
                def __exit__(self_inner, *a): return False
            return _Sock()
        raise OSError("refused")

    return (
        patch("httpx.Client", lambda **kw: _Client(
            handlers=handlers, post_handlers=post_handlers, **kw
        )),
        patch("socket.create_connection", _fake_create_connection),
    )


# ── tests ─────────────────────────────────────────────────────────────────

def test_json_shape_all_ok():
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    assert payload["ok"] is True
    names = [c["name"] for c in payload["checks"]]
    assert names == [
        "console",
        "install_provenance",
        "mcp_http",
        "flame_bridge",
        "state_ws",
        "graph_store",
    ]
    for c in payload["checks"]:
        assert set(c.keys()) >= {"name", "ok", "status", "url", "fix"}
        assert c["ok"] is True
        # graph_store fix is non-empty on unexercised substrate (loaded chip);
        # all other rows have empty fix when ok.
        if c["name"] != "graph_store":
            assert c["fix"] == ""


def test_json_shape_console_down_sets_ok_false_and_fix():
    handlers = {
        config.console_url() + "/api/v1/health": httpx.ConnectError("nope"),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output.strip())
    assert payload["ok"] is False
    console = next(c for c in payload["checks"] if c["name"] == "console")
    assert console["ok"] is False
    assert "unreachable" in console["status"]
    assert "mcp http" in console["fix"]


def test_human_mode_shows_urls_and_next_action():
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    out = result.output
    assert "console" in out and "flame_bridge" in out
    assert "127.0.0.1:9996" in out
    assert "Suggested next action" in out


def test_human_mode_failure_surfaces_first_fix():
    handlers = {
        config.console_url() + "/api/v1/health": httpx.ConnectError("nope"),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "Suggested next action" in result.output


# ── Phase 24.2: flame_bridge 4-state row taxonomy ──────────────────────────
#
# Replaces the pre-24.2 single failure-mode test below. Doctor now POSTs to
# the daemon's /api/v1/exec endpoint with text="flame_ping", parses the PR31
# envelope, extracts the daemon's effective bridge_url from the flame_ping
# body, and renders one of four row states:
#
#   OK convergent  — daemon reachable, connected=true, daemon's bridge_url
#                    matches doctor's re-derived config.flame_bridge_url()
#   WARN divergent — daemon reachable, daemon's bridge_url disagrees with
#                    doctor's (config-context divergence between operator
#                    shell env and daemon process env)
#   FAIL disconn.  — daemon reachable, daemon reports connected=false
#   UNKNOWN unreach— can't reach :9996; defers to mcp_http row
#
# The architectural invariant: doctor never falls back to a re-derived local
# probe under degradation. Daemon truth or no truth.


def test_flame_bridge_ok_convergent():
    """OK state: daemon reachable, connected, URLs converge."""
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    # Default post_handlers fires _flame_ping_envelope(connected=True,
    # bridge_url=config.flame_bridge_url()) — convergent by construction.
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    flame = next(c for c in payload["checks"] if c["name"] == "flame_bridge")
    assert flame["ok"] is True
    assert "running" in flame["status"]
    assert flame["url"] == config.flame_bridge_url()
    assert flame["fix"] == ""


def test_flame_bridge_warn_divergent():
    """WARN state: daemon's bridge_url disagrees with doctor's re-derived URL.

    Reproduces the portofino misconfig — FORGE_BRIDGE_PORT=9998 in launchd
    env aims the daemon's bridge client at state_ws while doctor (operator
    shell env) keeps the 9999 default. Doctor reports the divergence
    explicitly with the daemon-effective URL as authoritative.
    """
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    # Simulate daemon reporting a different bridge_url than doctor expects.
    divergent_url = "http://127.0.0.1:9998"
    post_handlers = {
        config.console_url() + "/api/v1/exec": _flame_ping_envelope(
            connected=True,
            bridge_url=divergent_url,
        ),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open, post_handlers=post_handlers)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output.strip())
    flame = next(c for c in payload["checks"] if c["name"] == "flame_bridge")
    assert flame["ok"] is False
    assert "dispatch target mismatch" in flame["status"]
    assert f"daemon={divergent_url}" in flame["status"]
    assert f"shell={config.flame_bridge_url()}" in flame["status"]
    # Daemon-effective URL is authoritative per §6.4 truth-authority discipline.
    assert flame["url"] == divergent_url
    assert "FORGE_BRIDGE_HOST/PORT" in flame["fix"]
    assert "TROUBLESHOOTING.md" in flame["fix"]


def test_flame_bridge_fail_daemon_says_disconnected():
    """FAIL state: daemon reachable, URLs agree, Flame is unreachable."""
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    post_handlers = {
        config.console_url() + "/api/v1/exec": _flame_ping_envelope(
            connected=False,
            bridge_url=config.flame_bridge_url(),
            error="ConnectError",
        ),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open, post_handlers=post_handlers)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output.strip())
    flame = next(c for c in payload["checks"] if c["name"] == "flame_bridge")
    assert flame["ok"] is False
    assert "flame disconnected" in flame["status"]
    assert "ConnectError" in flame["status"]
    # URL reported is daemon-effective (which matches shell here)
    assert flame["url"] == config.flame_bridge_url()
    assert "install-flame-hook.sh" in flame["fix"]


def test_flame_bridge_unknown_daemon_unreachable():
    """UNKNOWN state: daemon unreachable; defers to mcp_http row."""
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    # Daemon /api/v1/exec is unreachable — simulate via httpx.ConnectError.
    post_handlers = {
        config.console_url() + "/api/v1/exec": httpx.ConnectError("refused"),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open, post_handlers=post_handlers)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output.strip())
    flame = next(c for c in payload["checks"] if c["name"] == "flame_bridge")
    assert flame["ok"] is False
    assert "unknown" in flame["status"].lower()
    assert "daemon unreachable" in flame["status"]
    # Falls back to shell_url for display — daemon truth unavailable.
    assert flame["url"] == config.flame_bridge_url()
    assert "mcp_http" in flame["fix"]


def test_flame_bridge_fail_daemon_envelope_error():
    """FAIL state: daemon returned a PR31 error envelope (chain step failed).

    Could happen if flame_ping tool isn't registered, chain parser rejects
    the input, etc. Doctor reports the error code in status + the message
    in fix.
    """
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    post_handlers = {
        config.console_url() + "/api/v1/exec": _Resp(200, {
            "status": "error",
            "request_id": "test-rid",
            "chain": [],
            "error": {
                "code": "TOOL_NOT_FOUND",
                "message": "flame_ping is not registered",
                "step_index": 0,
                "original_error": None,
            },
        }),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open, post_handlers=post_handlers)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output.strip())
    flame = next(c for c in payload["checks"] if c["name"] == "flame_bridge")
    assert flame["ok"] is False
    assert "TOOL_NOT_FOUND" in flame["status"]
    assert "flame_ping is not registered" in flame["fix"]


def test_runtime_doctor_uses_config_urls(monkeypatch):
    """Override env → doctor probes the new URL."""
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "18996")
    custom_console = "http://127.0.0.1:18996"
    handlers = {
        custom_console + "/api/v1/health": _Resp(200, _health_body_ok()),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    console = next(c for c in payload["checks"] if c["name"] == "console")
    assert console["url"] == custom_console


# ── graph_store row (Q18) ─────────────────────────────────────────────────


def _graph_store_world():
    """Default _patch_world for graph_store tests — every non-graph row ok."""
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, _health_body_ok()),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    return _patch_world(handlers, tcp_open=tcp_open)


def _doctor_graph_row(result_output: str) -> dict:
    payload = json.loads(result_output.strip())
    return next(c for c in payload["checks"] if c["name"] == "graph_store")


def test_graph_store_missing_dir_is_loaded_not_failed(tmp_path, monkeypatch):
    # autouse fixture already points FORGE_GRAPH_DIR at tmp_path/forge_graphs
    # which won't exist until something writes to it.
    p1, p2 = _graph_store_world()
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _doctor_graph_row(result.output)
    assert row["ok"] is True
    assert row["chip"] == "loaded"
    assert "not yet created" in row["status"]
    assert row["fix"]  # non-empty teaching


def test_graph_store_empty_dir_is_loaded(tmp_path, monkeypatch):
    target = tmp_path / "graphs"
    target.mkdir()
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(target))
    p1, p2 = _graph_store_world()
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _doctor_graph_row(result.output)
    assert row["ok"] is True
    assert row["chip"] == "loaded"
    assert "no graphs recorded" in row["status"]


def test_graph_store_populated_parseable_is_ok(tmp_path, monkeypatch):
    target = tmp_path / "graphs"
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(target))
    from forge_bridge.runtime.graph_emit import emit_event, new_graph_id

    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    emit_event(graph_id=gid, node_kind="python", status="completed")

    p1, p2 = _graph_store_world()
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _doctor_graph_row(result.output)
    assert row["ok"] is True
    assert row["chip"] == "ok"
    assert "1 graphs" in row["status"]
    assert "2026-" in row["status"] or "last " in row["status"]


def test_graph_store_newest_unparseable_is_fail(tmp_path, monkeypatch):
    target = tmp_path / "graphs"
    target.mkdir()
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(target))
    # Newest file is structurally unparseable (no valid JSONL lines).
    (target / "bad0000000000000000000000000000.jsonl").write_text(
        "not json\nstill not json\n"
    )
    p1, p2 = _graph_store_world()
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _doctor_graph_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "fail"
    assert "unparseable" in row["status"]


def test_graph_store_appears_in_human_output(tmp_path):
    p1, p2 = _graph_store_world()
    with p1, p2:
        result = runner.invoke(app, ["doctor"])
    assert "graph_store" in result.output


# ── install_provenance row — operational invariant from 24.6 + D-04 ─────────


def _provenance_world(health_body: dict):
    """Build the patch context for a provenance test — only the health body
    varies between cases; everything else stays at happy-path defaults."""
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, health_body),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    return _patch_world(handlers, tcp_open=tcp_open)


def _provenance_row(result_output: str) -> dict:
    payload = json.loads(result_output.strip())
    return next(c for c in payload["checks"] if c["name"] == "install_provenance")


def test_provenance_ok_matches_operator_cwd():
    """Happy path: daemon's snapshot SHA matches operator CWD HEAD; no drift."""
    p1, p2 = _provenance_world(_health_body_ok())
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is True
    assert "matches operator CWD" in row["status"]
    assert row["fix"] == ""


def test_provenance_warn_drift_daemon_behind_disk():
    """Daemon's loaded code is behind the on-disk HEAD at the same path."""
    body = _health_body_ok(install_provenance={
        "import_path": "/Users/cnoellert/GitHub/forge-bridge/forge_bridge",
        "repo_root": "/Users/cnoellert/GitHub/forge-bridge",
        "startup_sha": "a" * 40,           # daemon loaded at this SHA
        "disk_sha_now": "b" * 40,          # disk has advanced to a different SHA
        "pid": 99999,
        "started_at": "2026-05-18T22:00:00+00:00",
    })
    p1, p2 = _provenance_world(body)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "warn"
    assert "aaaaaaaa" in row["status"]
    assert "bbbbbbbb" in row["status"]
    assert "disk advanced" in row["status"]
    assert "restart" in row["fix"].lower()


def test_provenance_warn_detached_no_git_metadata():
    """Daemon installed from a non-git source — repo_root and startup_sha None."""
    body = _health_body_ok(install_provenance={
        "import_path": "/opt/forge-bridge/forge_bridge",
        "repo_root": None,
        "startup_sha": None,
        "disk_sha_now": None,
        "pid": 99999,
        "started_at": "2026-05-18T22:00:00+00:00",
    })
    p1, p2 = _provenance_world(body)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "warn"
    assert "no git metadata" in row["status"]
    assert "detached/unknown" in row["status"]


def test_provenance_warn_missing_field_incompatible_daemon():
    """Daemon health body lacks the install_provenance key — older version."""
    body = _health_body_ok(install_provenance={})  # empty dict — falsy after .get()
    p1, p2 = _provenance_world(body)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "warn"
    assert "does not report install_provenance" in row["status"]
    assert "restart the daemon" in row["fix"]


def test_provenance_warn_console_unreachable():
    """Console is down — provenance probe degrades to warn-with-link."""
    handlers = {
        config.console_url() + "/api/v1/health": httpx.ConnectError("nope"),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "warn"
    assert "unreachable" in row["status"]
    assert "console row above" in row["fix"]


def test_provenance_warn_console_non_200():
    """Console reachable but returns 500 — same degraded posture."""
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(500, {"status": "error"}),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": True}),
    }
    tcp_open = {
        (config.MCP_HTTP_HOST, config.MCP_HTTP_PORT),
        (config.STATE_WS_HOST, config.STATE_WS_PORT),
    }
    p1, p2 = _patch_world(handlers, tcp_open=tcp_open)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "warn"
    assert "http 500" in row["status"]


def test_provenance_warn_cross_checkout_different_repos():
    """Daemon's repo_root differs from operator CWD's repo root."""
    body = _health_body_ok(install_provenance={
        "import_path": "/some/other/checkout/forge_bridge",
        "repo_root": "/some/other/checkout",
        "startup_sha": "c" * 40,
        "disk_sha_now": "c" * 40,           # no drift on the daemon's side
        "pid": 99999,
        "started_at": "2026-05-18T22:00:00+00:00",
    })
    p1, p2 = _provenance_world(body)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "warn"
    assert "different checkouts" in row["status"]
    assert "/some/other/checkout" in row["fix"]


def test_provenance_warn_cross_commit_same_repo():
    """Same repo, but daemon's startup SHA differs from operator CWD HEAD."""
    # Operator CWD is the real test-runner cwd (forge-bridge); daemon claims
    # to be in the same repo but at a fake SHA.
    from pathlib import Path
    from forge_bridge.install_provenance import find_repo_root
    cwd_repo = find_repo_root(Path.cwd())
    if not cwd_repo:
        import pytest
        pytest.skip("test runner CWD is not in a git repo — cannot evaluate")
    body = _health_body_ok(install_provenance={
        "import_path": str(cwd_repo / "forge_bridge"),
        "repo_root": str(cwd_repo),
        "startup_sha": "d" * 40,            # fake — does NOT match real HEAD
        "disk_sha_now": "d" * 40,            # no drift between startup and "disk"
        "pid": 99999,
        "started_at": "2026-05-18T22:00:00+00:00",
    })
    p1, p2 = _provenance_world(body)
    with p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is False
    assert row["chip"] == "warn"
    assert "different commits" in row["status"]
    assert "dddddddd" in row["status"]


def test_provenance_ok_cwd_not_in_git_skips_comparison():
    """If operator CWD has no git repo, comparison is skipped (no false warn)."""
    body = _health_body_ok(install_provenance={
        "import_path": "/Users/cnoellert/GitHub/forge-bridge/forge_bridge",
        "repo_root": "/Users/cnoellert/GitHub/forge-bridge",
        "startup_sha": "e" * 40,
        "disk_sha_now": "e" * 40,
        "pid": 99999,
        "started_at": "2026-05-18T22:00:00+00:00",
    })
    p1, p2 = _provenance_world(body)
    # Force operator CWD lookup to return "no repo" so we don't depend on the
    # test runner's actual cwd repo state.
    with patch(
        "forge_bridge.cli.runtime_doctor._operator_repo_context",
        return_value=(None, None),
    ), p1, p2:
        result = runner.invoke(app, ["doctor", "--json"])
    row = _provenance_row(result.output)
    assert row["ok"] is True
    assert "comparison skipped" in row["status"]
    assert "eeeeeeee" in row["status"]


def test_provenance_row_appears_in_human_output():
    """Sanity: install_provenance row renders in the human-mode table."""
    p1, p2 = _provenance_world(_health_body_ok())
    with p1, p2:
        result = runner.invoke(app, ["doctor"])
    assert "install_provenance" in result.output
