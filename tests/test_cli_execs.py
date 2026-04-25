"""EXECS-03 — forge-bridge console execs tests.

Covers:
- list view + columns
- --since parser wiring (24h passes; bad input exits 1)
- W-01: --tool runs client-side and emits stderr note (suppressed in --json)
- API params: code_hash, limit, offset, promoted_only
- drilldown by hash + not-found
- --json envelope passthrough
- --help Examples block
"""
from __future__ import annotations

import json
import re

import httpx
import typer
from typer.testing import CliRunner

from forge_bridge.cli.execs import _TOOL_CLIENT_SIDE_NOTE, execs_cmd

runner = CliRunner()


def _make_app():
    app = typer.Typer()
    app.command("execs")(execs_cmd)

    # Force subcommand-mode dispatch so `runner.invoke(app, ["execs"])` doesn't
    # collapse "execs" into the positional HASH argument.
    @app.command("__noop__", hidden=True)
    def _noop() -> None:  # pragma: no cover - stub
        pass

    return app


def _capturing_transport(monkeypatch, handler, captured: list[httpx.Request]):
    def wrapped(request):
        captured.append(request)
        return handler(request)

    transport = httpx.MockTransport(wrapped)
    real_init = httpx.Client.__init__

    def patched(self, *a, **kw):
        kw["transport"] = transport
        real_init(self, *a, **kw)

    monkeypatch.setattr(httpx.Client, "__init__", patched)


def _mock_transport(monkeypatch, handler):
    return _capturing_transport(monkeypatch, handler, [])


SAMPLE_RECORDS = [
    {
        "code_hash": "deadbeefcafebabe1234567890abcdef" + "1" * 32,
        "raw_code": "print('hello')",
        "intent": "test_intent",
        "timestamp": "2026-04-22T10:00:00+00:00",
        "promoted": True,
        "tool": "synth_foo",
    },
    {
        "code_hash": "1234abcd" + "0" * 56,
        "raw_code": "x = 1",
        "intent": None,
        "timestamp": "2026-04-21T10:00:00+00:00",
        "promoted": False,
        "tool": "synth_bar",
    },
]


def _ok_handler(request):
    return httpx.Response(
        200,
        json={"data": SAMPLE_RECORDS, "meta": {"total": 2, "limit": 50, "offset": 0}},
    )


class TestExecsList:
    def test_list_default(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(_make_app(), ["execs"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        # Columns are wide-cell-rendered; verify that key tokens appear
        assert "synth_foo" in result.output
        assert "Tool" in result.output
        assert "Hash" in result.output
        assert "Timestamp" in result.output
        assert "Promoted" in result.output

    def test_empty(self, monkeypatch):
        def empty(req):
            return httpx.Response(
                200, json={"data": [], "meta": {"total": 0, "limit": 50, "offset": 0}}
            )

        _mock_transport(monkeypatch, empty)
        result = runner.invoke(_make_app(), ["execs"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        assert "No executions found" in result.output


class TestExecsSince:
    def test_since_24h(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        result = runner.invoke(
            _make_app(), ["execs", "--since", "24h"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        assert len(captured) == 1
        params = dict(captured[0].url.params)
        assert "since" in params
        # ISO 8601 — looks like "YYYY-MM-DDTHH:MM:SS..."
        assert re.match(r"\d{4}-\d{2}-\d{2}T", params["since"])

    def test_since_bad_input(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        result = runner.invoke(
            _make_app(), ["execs", "--since", "yesterday"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 1
        # No API call made — parser failed before fetch
        assert len(captured) == 0


class TestExecsTool:
    def test_tool_flag_emits_stderr_note(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["execs", "--tool", "synth_foo"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        # CliRunner combines stdout+stderr by default; the note must appear.
        # Rich may soft-wrap the note across two lines on narrow terminals, so
        # collapse whitespace before comparing.
        assert result.exit_code == 0
        normalized = " ".join(result.output.split())
        assert _TOOL_CLIENT_SIDE_NOTE in normalized

    def test_tool_flag_json_suppresses_note(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["execs", "--tool", "synth_foo", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        # The locked stderr note must NOT pollute the json stream.
        assert _TOOL_CLIENT_SIDE_NOTE not in result.output
        # Output must be parseable JSON
        parsed = json.loads(result.output.strip())
        assert "data" in parsed

    def test_tool_filter_does_not_send_to_api(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        result = runner.invoke(
            _make_app(), ["execs", "--tool", "synth_foo"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        assert len(captured) == 1
        params = dict(captured[0].url.params)
        # W-01: tool MUST NOT be sent as a server param
        assert "tool" not in params

    def test_tool_filter_narrows_data_in_json(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["execs", "--tool", "synth_foo", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        parsed = json.loads(result.output.strip())
        assert all(r.get("tool") == "synth_foo" for r in parsed["data"])
        assert len(parsed["data"]) == 1


class TestExecsServerParams:
    def test_hash_passed_to_api(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        runner.invoke(
            _make_app(), ["execs", "--hash", "deadbeef"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        params = dict(captured[0].url.params)
        assert params["code_hash"] == "deadbeef"

    def test_limit_passed_to_api(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        runner.invoke(
            _make_app(), ["execs", "--limit", "100"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        params = dict(captured[0].url.params)
        assert params["limit"] == "100"

    def test_offset_passed_to_api(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        runner.invoke(
            _make_app(), ["execs", "--offset", "10"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        params = dict(captured[0].url.params)
        assert params["offset"] == "10"

    def test_promoted_passed_to_api(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        runner.invoke(
            _make_app(), ["execs", "--promoted"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        params = dict(captured[0].url.params)
        assert params["promoted_only"] == "true"


class TestExecsDrilldown:
    def test_drilldown_by_hash(self, monkeypatch):
        captured: list[httpx.Request] = []
        _capturing_transport(monkeypatch, _ok_handler, captured)
        result = runner.invoke(
            _make_app(), ["execs", "deadbeef"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        params = dict(captured[0].url.params)
        assert params["code_hash"] == "deadbeef"
        assert params["limit"] == "1"

    def test_drilldown_not_found(self, monkeypatch):
        def empty(req):
            return httpx.Response(
                200, json={"data": [], "meta": {"total": 0, "limit": 1, "offset": 0}}
            )

        _mock_transport(monkeypatch, empty)
        result = runner.invoke(
            _make_app(), ["execs", "ffffffff"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 1


class TestExecsJSON:
    def test_json_envelope(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["execs", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output.strip())
        assert "data" in parsed

    def test_json_unreachable(self, monkeypatch):
        def unreach(req):
            raise httpx.ConnectError("refused")

        _mock_transport(monkeypatch, unreach)
        result = runner.invoke(
            _make_app(), ["execs", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 2
        parsed = json.loads(result.output.strip())
        assert parsed["error"]["code"] == "server_unreachable"


class TestExecsHelp:
    def test_examples_block(self):
        result = runner.invoke(_make_app(), ["execs", "--help"])
        assert result.exit_code == 0
        assert "Examples:" in result.output
