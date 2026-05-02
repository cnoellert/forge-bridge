"""PR7 / PR7.1 — `fbridge run <action>` tests.

Covers:
  - valid action executes (human + verbose stderr)
  - invalid action errors with friendly suggest-actions hint
  - JSON output shape is {ok, action, result}
  - PR7.1: tuple/content-block returns are unpacked into clean human output
    (no TextContent reprs, no tuple reprs); JSON envelope carries the
    parsed structured value, not the raw FastMCP shape.
"""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import typer
from typer.testing import CliRunner

from forge_bridge.cli.run import run_cmd

# Recent typer/click drop the `mix_stderr` kwarg. Fall back to merged streams;
# in that mode `result.output` carries both stdout and stderr (matches the
# pattern in tests/test_cli_chat.py).
try:
    runner = CliRunner(mix_stderr=False)
    _STREAMS_SPLIT = True
except TypeError:
    runner = CliRunner()
    _STREAMS_SPLIT = False


def _stderr(result) -> str:
    return result.stderr if _STREAMS_SPLIT else result.output


def _stdout(result) -> str:
    return result.stdout if _STREAMS_SPLIT else result.output


def _make_app() -> typer.Typer:
    app = typer.Typer()
    app.command("run")(run_cmd)

    # Typer collapses single-command apps into the root callback. A hidden
    # second command keeps subcommand-mode dispatch so `runner.invoke(app,
    # ["run", ...])` resolves to `run_cmd`.
    @app.command("__noop__", hidden=True)
    def _noop() -> None:  # pragma: no cover - stub
        pass

    return app


def _patch_mcp(monkeypatch, available: list[str], result):
    """Stub the in-process FastMCP singleton: list_tools + call_tool.

    `result` is whatever `mcp.call_tool(...)` should return — a tuple,
    a list of content blocks, or a plain value. Lets each test exercise
    a specific FastMCP return shape.

    We patch the ``mcp`` attribute on the real ``forge_bridge.mcp.server``
    module rather than swapping ``sys.modules``. Once the package has been
    imported once, ``from forge_bridge.mcp import server`` returns the
    cached attribute regardless of what sys.modules holds.
    """
    import forge_bridge.mcp.server as real_server

    async def _list_tools():
        return [SimpleNamespace(name=n) for n in available]

    async def _call_tool(name, arguments):
        if name not in available:
            raise KeyError(name)
        return result

    fake_mcp = SimpleNamespace(list_tools=_list_tools, call_tool=_call_tool)
    monkeypatch.setattr(real_server, "mcp", fake_mcp)


def _text_block(text: str):
    """Stand-in for mcp.types.TextContent — only `.text` is consumed."""
    return SimpleNamespace(type="text", text=text)


# ── valid execution ──────────────────────────────────────────────────────


class TestRunValidAction:
    def test_text_content_blocks_only(self, monkeypatch):
        _patch_mcp(monkeypatch, ["flame_ping"], result=[_text_block("pong")])
        result = runner.invoke(_make_app(), ["run", "flame_ping"])
        assert result.exit_code == 0
        assert "pong" in result.output
        assert "TextContent" not in result.output

    def test_verbose_emits_timing_to_stderr(self, monkeypatch):
        _patch_mcp(monkeypatch, ["flame_ping"], result=[_text_block("pong")])
        result = runner.invoke(_make_app(), ["run", "flame_ping", "--verbose"])
        assert result.exit_code == 0
        assert "pong" in _stdout(result)
        assert "[run]" in _stderr(result)
        assert "flame_ping" in _stderr(result)


# ── PR7.1: tuple unpacking + key:value rendering ────────────────────────


class TestRunCleanFormatting:
    def test_structured_dict_renders_as_key_value_lines(self, monkeypatch):
        # FastMCP "wrap_output" shape — structured["result"] is a JSON string.
        payload = '{"connected": true, "version": "2026.2.1", "project": "abc"}'
        raw = ([_text_block(payload)], {"result": payload})
        _patch_mcp(monkeypatch, ["flame_ping"], result=raw)

        result = runner.invoke(_make_app(), ["run", "flame_ping"])
        assert result.exit_code == 0
        out = result.output
        assert "connected: True" in out
        assert "version: 2026.2.1" in out
        assert "project: abc" in out
        # Negative checks — no internal structure leaks through.
        assert "TextContent" not in out
        assert "tuple" not in out
        assert "(" not in out.splitlines()[0]

    def test_structured_dict_without_result_key(self, monkeypatch):
        # Tool with an output_schema but no wrap_output — structured is the
        # value itself, not nested under "result".
        raw = ([_text_block("ignored")], {"connected": True, "host": "127.0.0.1"})
        _patch_mcp(monkeypatch, ["flame_ping"], result=raw)

        result = runner.invoke(_make_app(), ["run", "flame_ping"])
        assert result.exit_code == 0
        assert "connected: True" in result.output
        assert "host: 127.0.0.1" in result.output

    def test_content_blocks_only_no_object_repr(self, monkeypatch):
        # No output_schema — call_tool returns a plain list of ContentBlocks.
        _patch_mcp(monkeypatch, ["flame_ping"], result=[_text_block("hello world")])
        result = runner.invoke(_make_app(), ["run", "flame_ping"])
        assert result.exit_code == 0
        assert result.output.strip() == "hello world"
        assert "TextContent" not in result.output

    def test_empty_blocks_fallback_no_output(self, monkeypatch):
        _patch_mcp(monkeypatch, ["flame_ping"], result=[])
        result = runner.invoke(_make_app(), ["run", "flame_ping"])
        assert result.exit_code == 0
        assert "No output" in result.output

    def test_plain_dict_return_renders_as_key_value(self, monkeypatch):
        _patch_mcp(monkeypatch, ["flame_ping"], result={"foo": "bar", "n": 3})
        result = runner.invoke(_make_app(), ["run", "flame_ping"])
        assert result.exit_code == 0
        assert "foo: bar" in result.output
        assert "n: 3" in result.output


# ── invalid action ──────────────────────────────────────────────────────


class TestRunInvalidAction:
    def test_unknown_exits_1_with_suggestion(self, monkeypatch):
        _patch_mcp(monkeypatch, ["flame_ping"], result=[_text_block("pong")])
        result = runner.invoke(_make_app(), ["run", "does_not_exist"])
        assert result.exit_code == 1
        assert "Unknown action: does_not_exist" in _stderr(result)
        assert "fbridge actions" in _stderr(result)

    def test_unknown_json_envelope(self, monkeypatch):
        _patch_mcp(monkeypatch, ["flame_ping"], result=[_text_block("pong")])
        result = runner.invoke(_make_app(), ["run", "does_not_exist", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.output.strip())
        assert payload["ok"] is False
        assert payload["action"] == "does_not_exist"
        assert payload["error"]["code"] == "unknown_action"
        assert "fbridge actions" in payload["error"]["fix"]


# ── JSON envelope ───────────────────────────────────────────────────────


class TestRunJsonOutput:
    def test_json_unpacks_tuple_to_parsed_dict(self, monkeypatch):
        payload = '{"connected": true, "version": "2026.2.1"}'
        raw = ([_text_block(payload)], {"result": payload})
        _patch_mcp(monkeypatch, ["flame_ping"], result=raw)

        result = runner.invoke(_make_app(), ["run", "flame_ping", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.output.strip())
        assert envelope["ok"] is True
        assert envelope["action"] == "flame_ping"
        assert envelope["result"] == {"connected": True, "version": "2026.2.1"}

    def test_json_text_blocks_returned_as_string(self, monkeypatch):
        _patch_mcp(monkeypatch, ["flame_ping"], result=[_text_block("pong")])
        result = runner.invoke(_make_app(), ["run", "flame_ping", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.output.strip())
        assert envelope == {"ok": True, "action": "flame_ping", "result": "pong"}

    def test_execution_failure_surfaces_in_json(self, monkeypatch):
        import forge_bridge.mcp.server as real_server

        async def _list_tools():
            return [SimpleNamespace(name="flame_ping")]

        async def _call_tool(name, arguments):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            real_server, "mcp",
            SimpleNamespace(list_tools=_list_tools, call_tool=_call_tool),
        )

        result = runner.invoke(_make_app(), ["run", "flame_ping", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.output.strip())
        assert payload["ok"] is False
        assert payload["action"] == "flame_ping"
        assert payload["error"]["code"] == "execution_failed"
        assert "boom" in payload["error"]["message"]


# ── help ────────────────────────────────────────────────────────────────


class TestRunHelp:
    def test_help_lists_examples(self):
        # The Examples epilog lives on the wiring in main.py, not on the
        # bare run_cmd. Hit the real app to verify the user-visible help.
        from forge_bridge.__main__ import app as real_app
        result = runner.invoke(real_app, ["run", "--help"])
        assert result.exit_code == 0
        assert "Examples" in result.output
        assert "--json" in result.output
        assert "--verbose" in result.output
