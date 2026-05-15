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
    """Routes httpx.Client.get(url) to a per-URL handler dict."""

    def __init__(self, *, handlers, **_kwargs):
        self._handlers = handlers

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


def _patch_world(handlers, *, tcp_open: set[tuple[str, int]] | None = None):
    """Patch httpx.Client and socket.create_connection together."""
    open_pairs = tcp_open or set()

    def _fake_create_connection(addr, timeout=None):
        if tuple(addr) in open_pairs:
            class _Sock:
                def close(self_inner): ...
                def __enter__(self_inner): return self_inner
                def __exit__(self_inner, *a): return False
            return _Sock()
        raise OSError("refused")

    return (
        patch("httpx.Client", lambda **kw: _Client(handlers=handlers, **kw)),
        patch("socket.create_connection", _fake_create_connection),
    )


# ── tests ─────────────────────────────────────────────────────────────────

def test_json_shape_all_ok():
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, {"status": "ok"}),
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
    assert names == ["console", "mcp_http", "flame_bridge", "state_ws", "graph_store"]
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
        config.console_url() + "/api/v1/health": _Resp(200, {"status": "ok"}),
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


def test_flame_bridge_running_but_no_flame_module():
    handlers = {
        config.console_url() + "/api/v1/health": _Resp(200, {"status": "ok"}),
        config.flame_bridge_url() + "/status": _Resp(200, {"flame_available": False}),
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
    flame = next(c for c in payload["checks"] if c["name"] == "flame_bridge")
    assert flame["ok"] is False
    assert "no flame module" in flame["status"]


def test_runtime_doctor_uses_config_urls(monkeypatch):
    """Override env → doctor probes the new URL."""
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "18996")
    custom_console = "http://127.0.0.1:18996"
    handlers = {
        custom_console + "/api/v1/health": _Resp(200, {"status": "ok"}),
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
        config.console_url() + "/api/v1/health": _Resp(200, {"status": "ok"}),
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
