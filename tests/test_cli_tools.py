"""TOOLS-03 — forge-bridge console tools tests.

Covers:
- list view rendering with `Created ▼` column
- client-side filters (--origin, --namespace, -q/--search)
- empty-result handling
- drilldown view + 404
- --json envelope passthrough
- connection-error UX (Rich + JSON)
- --help Examples block
"""
from __future__ import annotations

import json

import httpx
import typer
from typer.testing import CliRunner

from forge_bridge.cli.tools import tools_cmd

runner = CliRunner()


def _make_app():
    app = typer.Typer()
    app.command("tools")(tools_cmd)

    # Typer collapses a single-command app into the root callback, which would
    # cause `runner.invoke(app, ["tools"])` to treat "tools" as a positional
    # argument. Adding a no-op second command keeps subcommand-mode dispatch.
    @app.command("__noop__", hidden=True)
    def _noop() -> None:  # pragma: no cover - stub
        pass

    return app


def _mock_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_init = httpx.Client.__init__

    def patched(self, *a, **kw):
        kw["transport"] = transport
        real_init(self, *a, **kw)

    monkeypatch.setattr(httpx.Client, "__init__", patched)


SAMPLE_TOOLS = [
    {
        "name": "synth_foo",
        "origin": "synthesized",
        "namespace": "synth",
        "synthesized_at": "2026-04-22T10:00:00+00:00",
        "code_hash": "a" * 64,
        "version": "1.0.0",
        "observation_count": 5,
        "tags": [],
        "meta": {},
    },
    {
        "name": "flame_bar",
        "origin": "builtin",
        "namespace": "flame",
        "synthesized_at": None,
        "code_hash": None,
        "version": None,
        "observation_count": 0,
        "tags": [],
        "meta": {},
    },
]


def _ok_handler(request):
    if request.url.path == "/api/v1/tools":
        return httpx.Response(200, json={"data": SAMPLE_TOOLS, "meta": {"total": 2}})
    if request.url.path.startswith("/api/v1/tools/"):
        name = request.url.path.split("/")[-1]
        for t in SAMPLE_TOOLS:
            if t["name"] == name:
                return httpx.Response(200, json={"data": t, "meta": {}})
        return httpx.Response(
            404,
            json={"error": {"code": "tool_not_found", "message": f"no tool {name}"}},
        )
    return httpx.Response(500, json={"error": {"code": "internal_error", "message": ""}})


class TestToolsList:
    def test_lists_tools(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(_make_app(), ["tools"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        # Raw names stay visible — users need them for `fbridge run <name>`.
        assert "synth_foo" in result.output
        assert "flame_bar" in result.output
        # PR9: grouped sections instead of the old `Created ▼` column.
        assert "Flame" in result.output
        assert "Synthesized" in result.output

    def test_filter_origin_synthesized(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "--origin", "synthesized"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        assert "synth_foo" in result.output
        assert "flame_bar" not in result.output

    def test_filter_origin_builtin(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "--origin", "builtin"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        assert "flame_bar" in result.output
        assert "synth_foo" not in result.output

    def test_filter_namespace(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "--namespace", "synth"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert "synth_foo" in result.output
        assert "flame_bar" not in result.output

    def test_search(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "-q", "flame"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert "flame_bar" in result.output
        assert "synth_foo" not in result.output

    def test_empty_result_no_crash(self, monkeypatch):
        def empty(request):
            return httpx.Response(200, json={"data": [], "meta": {"total": 0}})

        _mock_transport(monkeypatch, empty)
        result = runner.invoke(_make_app(), ["tools"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        assert "No tools found" in result.output


class TestToolsDrilldown:
    def test_drilldown(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "synth_foo"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        assert "synth_foo" in result.output
        assert "1.0.0" in result.output  # version field surfaced

    def test_drilldown_not_found(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "nonexistent"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 1


class TestToolsJSON:
    def test_json_envelope(self, monkeypatch):
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output.strip())
        assert "data" in parsed
        assert len(parsed["data"]) == 2

    def test_unreachable_json(self, monkeypatch):
        def unreach(request):
            raise httpx.ConnectError("refused")

        _mock_transport(monkeypatch, unreach)
        result = runner.invoke(
            _make_app(), ["tools", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 2
        parsed = json.loads(result.output.strip())
        assert parsed["error"]["code"] == "server_unreachable"

    def test_unreachable_rich(self, monkeypatch):
        def unreach(request):
            raise httpx.ConnectError("refused")

        _mock_transport(monkeypatch, unreach)
        result = runner.invoke(
            _make_app(), ["tools"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 2
        assert "server is not running" in result.output


class TestToolsHelp:
    def test_examples_block(self):
        result = runner.invoke(_make_app(), ["tools", "--help"])
        assert result.exit_code == 0
        assert "Examples:" in result.output


class TestToolsGroupingPR9:
    """PR9 — improve action discovery UX (grouping + readable names)."""

    def test_actions_are_grouped_by_namespace(self, monkeypatch):
        # Mix one tool of each namespace so all three group headers must appear.
        sample = [
            {"name": "forge_list_shots", "origin": "builtin", "namespace": "forge",
             "synthesized_at": None, "code_hash": None, "version": None,
             "observation_count": 0, "tags": [], "meta": {}},
            {"name": "flame_get_sequence_segments", "origin": "builtin", "namespace": "flame",
             "synthesized_at": None, "code_hash": None, "version": None,
             "observation_count": 0, "tags": [], "meta": {}},
            {"name": "synth_rename_segment", "origin": "synthesized", "namespace": "synth",
             "synthesized_at": "2026-04-22T10:00:00+00:00", "code_hash": "a" * 64,
             "version": "1.0.0", "observation_count": 5, "tags": [], "meta": {}},
        ]

        def handler(request):
            return httpx.Response(200, json={"data": sample, "meta": {"total": 3}})

        _mock_transport(monkeypatch, handler)
        result = runner.invoke(_make_app(), ["tools"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        out = result.output

        # All three group titles render.
        assert "Forge" in out
        assert "Flame" in out
        assert "Synthesized" in out

        # Each tool appears in the section ordered by _GROUP_TITLES (forge → flame → synth).
        forge_pos = out.index("Forge")
        flame_pos = out.index("Flame")
        synth_pos = out.index("Synthesized")
        assert forge_pos < flame_pos < synth_pos

    def test_readable_names_appear(self, monkeypatch):
        sample = [
            {"name": "flame_get_sequence_segments", "origin": "builtin", "namespace": "flame",
             "synthesized_at": None, "code_hash": None, "version": None,
             "observation_count": 0, "tags": [], "meta": {}},
            {"name": "synth_rename_segment", "origin": "synthesized", "namespace": "synth",
             "synthesized_at": None, "code_hash": "a" * 64, "version": None,
             "observation_count": 0, "tags": [], "meta": {}},
        ]

        def handler(request):
            return httpx.Response(200, json={"data": sample, "meta": {"total": 2}})

        _mock_transport(monkeypatch, handler)
        result = runner.invoke(_make_app(), ["tools"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        out = result.output

        # snake_case → sentence case, prefix dropped.
        assert "Get sequence segments" in out
        assert "Rename segment" in out
        # Raw name still shown so `fbridge run <name>` is one copy/paste away.
        assert "flame_get_sequence_segments" in out
        assert "synth_rename_segment" in out

    def test_json_envelope_unchanged(self, monkeypatch):
        # Per spec: --json output must not change shape.
        _mock_transport(monkeypatch, _ok_handler)
        result = runner.invoke(
            _make_app(), ["tools", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output.strip())
        assert "data" in parsed
        assert {t["name"] for t in parsed["data"]} == {"synth_foo", "flame_bar"}
        # No grouped/humanized fields injected into the wire payload.
        for t in parsed["data"]:
            assert "group" not in t
            assert "readable" not in t


class TestToolsAvailabilityBugC:
    """Bug C — `available` annotation is surfaced; tools never silently drop."""

    def _sample(self):
        return [
            {"name": "flame_ping", "origin": "builtin", "namespace": "flame",
             "synthesized_at": None, "code_hash": None, "version": None,
             "observation_count": 0, "tags": [], "meta": {},
             "available": False},   # backend unreachable but still listed
            {"name": "forge_list_staged", "origin": "builtin", "namespace": "forge",
             "synthesized_at": None, "code_hash": None, "version": None,
             "observation_count": 0, "tags": [], "meta": {},
             "available": True},    # in-process, always available
            {"name": "synth_rename_segment", "origin": "synthesized",
             "namespace": "synth", "synthesized_at": "2026-04-22T10:00:00+00:00",
             "code_hash": "a" * 64, "version": "1.0.0", "observation_count": 5,
             "tags": [], "meta": {}, "available": True},
        ]

    def test_unreachable_tools_still_listed(self, monkeypatch):
        sample = self._sample()

        def handler(request):
            return httpx.Response(200, json={"data": sample, "meta": {"total": 3}})

        _mock_transport(monkeypatch, handler)
        result = runner.invoke(_make_app(), ["tools"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        out = result.output

        # Every tool appears, including the unreachable flame_ping.
        for t in sample:
            assert t["name"] in out

    def test_availability_column_renders(self, monkeypatch):
        sample = self._sample()

        def handler(request):
            return httpx.Response(200, json={"data": sample, "meta": {"total": 3}})

        _mock_transport(monkeypatch, handler)
        result = runner.invoke(_make_app(), ["tools"], env={"FORGE_CONSOLE_PORT": "9996"})
        assert result.exit_code == 0
        out = result.output

        # Both labels visible at least once each.
        assert "available" in out
        assert "unavailable" in out

    def test_json_envelope_includes_available_field(self, monkeypatch):
        sample = self._sample()

        def handler(request):
            return httpx.Response(200, json={"data": sample, "meta": {"total": 3}})

        _mock_transport(monkeypatch, handler)
        result = runner.invoke(
            _make_app(), ["tools", "--json"],
            env={"FORGE_CONSOLE_PORT": "9996"},
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output.strip())

        # Existing envelope shape preserved.
        assert "data" in parsed
        assert {t["name"] for t in parsed["data"]} == {
            "flame_ping", "forge_list_staged", "synth_rename_segment",
        }
        # New field carried verbatim from the API payload.
        availability = {t["name"]: t["available"] for t in parsed["data"]}
        assert availability == {
            "flame_ping": False,
            "forge_list_staged": True,
            "synth_rename_segment": True,
        }
