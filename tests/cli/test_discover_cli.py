"""Thread B B-1 — `fbridge discover` registry-enumeration CLI tests."""
from __future__ import annotations

import inspect
import json
import re

import pytest
from typer.testing import CliRunner

import forge_bridge.graph as graph
from forge_bridge.cli.main import app
from forge_bridge.console import _chain_parse


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _primitive_names_from_graph() -> set[str]:
    names: set[str] = set()
    pattern = re.compile(r"^is_(?P<name>.+)_step$")
    for attr_name in dir(graph):
        match = pattern.match(attr_name)
        if match and callable(getattr(graph, attr_name)):
            names.add(match.group("name"))
    return names


def test_discover_primitives_json_matches_graph_registry(runner):
    result = runner.invoke(app, ["discover", "primitives", "--json"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    actual = {row["name"] for row in body["data"]}
    assert actual == _primitive_names_from_graph()


def test_discover_primitives_human_lists_known_fixture(runner):
    result = runner.invoke(app, ["discover", "primitives", "--no-color"])

    assert result.exit_code == 0
    assert "collect" in result.stdout
    assert "Topology-converging collect graph primitive." in result.stdout


def test_discover_primitive_detail_renders_module_and_parse_docstrings(runner):
    result = runner.invoke(app, ["discover", "primitive", "collect", "--no-color"])

    assert result.exit_code == 0
    assert "primitive: collect" in result.stdout
    assert "Topology-converging collect graph primitive." in result.stdout
    assert "Validate collect step syntax." in result.stdout


def test_discover_primitive_unknown_is_nonzero(runner):
    result = runner.invoke(app, ["discover", "primitive", "missing"])

    assert result.exit_code == 1
    assert "primitive not found: missing" in result.stderr


def test_discover_tools_json_envelope_lists_known_tool(runner):
    result = runner.invoke(app, ["discover", "tools", "--json"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert "data" in body
    tools = {row["name"]: row for row in body["data"]}
    assert "forge_ping" in tools
    assert tools["forge_ping"]["annotations"]["title"] == "Check forge-bridge connection"
    assert tools["forge_ping"]["_source"] == "builtin"


def test_discover_tool_detail_renders_known_tool(runner):
    result = runner.invoke(app, ["discover", "tool", "forge_ping", "--no-color"])

    assert result.exit_code == 0
    assert "tool: forge_ping" in result.stdout
    assert "_source: builtin" in result.stdout
    assert "Check forge-bridge server connectivity." in result.stdout


def test_discover_tool_unknown_is_nonzero(runner):
    result = runner.invoke(app, ["discover", "tool", "not_a_tool"])

    assert result.exit_code == 1
    assert "tool not found: not_a_tool" in result.stderr


def test_discover_macros_empty_registry_is_clean_exit(runner, monkeypatch):
    from forge_bridge.console import _macros

    monkeypatch.setattr(_macros, "list_macros", lambda: {})

    result = runner.invoke(app, ["discover", "macros", "--no-color"])

    assert result.exit_code == 0
    assert "no macros registered" in result.stdout


def test_discover_macros_json_envelope_and_macro_detail(runner, monkeypatch):
    from forge_bridge.console import _macros

    monkeypatch.setattr(
        _macros,
        "list_macros",
        lambda: {"daily": "list projects -> list shots project_name=demo"},
    )

    result = runner.invoke(app, ["discover", "macros", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body == {
        "data": [
            {
                "name": "daily",
                "chain": "list projects -> list shots project_name=demo",
            }
        ]
    }

    detail = runner.invoke(app, ["discover", "macro", "daily", "--no-color"])
    assert detail.exit_code == 0
    assert "macro: daily" in detail.stdout
    assert "list projects -> list shots project_name=demo" in detail.stdout


def test_discover_macro_unknown_is_nonzero(runner, monkeypatch):
    from forge_bridge.console import _macros

    monkeypatch.setattr(_macros, "list_macros", lambda: {})

    result = runner.invoke(app, ["discover", "macro", "missing"])

    assert result.exit_code == 1
    assert "macro not found: missing" in result.stderr


def test_discover_grammar_renders_chain_parse_module_docstring(runner):
    result = runner.invoke(app, ["discover", "grammar", "--no-color"])

    assert result.exit_code == 0
    first_line = inspect.cleandoc(_chain_parse.__doc__ or "").splitlines()[0]
    assert first_line in result.stdout

