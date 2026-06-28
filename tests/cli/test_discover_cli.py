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


# discover's tool listing/detail are now read-API consumers (:9996 /api/v1/tools),
# where artist_description / artist_label are resolved daemon-side from the
# peer-authored CapabilityDeclaration carry. Tests mock the httpx read-API call
# (forge_bridge.cli.discover.fetch / fetch_raw_envelope) — NO live daemon.

_SAMPLE_TOOLS = [
    {
        "name": "forge_classify_shot",
        "origin": "builtin",
        "namespace": "forge",
        "available": True,
        "artist_description": "Peer-authored summary.",
        "artist_label": "Classify Shot",
    },
    {
        "name": "forge_ping",
        "origin": "builtin",
        "namespace": "forge",
        "available": True,
        "artist_description": "Check forge-bridge server connectivity.",
        "artist_label": "Forge ping",
    },
]


def _envelope(rows):
    return {"data": rows, "meta": {"total": len(rows)}}


def test_discover_tools_json_passes_through_read_api_envelope(runner, monkeypatch):
    """--json emits the read-API payload byte-faithfully (artist fields included)."""
    from forge_bridge.cli import discover as discover_mod

    envelope = _envelope(_SAMPLE_TOOLS)
    monkeypatch.setattr(discover_mod, "fetch_raw_envelope", lambda path: envelope)

    result = runner.invoke(app, ["discover", "tools", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body == envelope
    rows = {r["name"]: r for r in body["data"]}
    assert rows["forge_classify_shot"]["artist_description"] == "Peer-authored summary."
    assert rows["forge_classify_shot"]["artist_label"] == "Classify Shot"


def test_discover_tools_human_displays_artist_description(runner, monkeypatch):
    from forge_bridge.cli import discover as discover_mod

    monkeypatch.setattr(discover_mod, "fetch", lambda path: list(_SAMPLE_TOOLS))

    result = runner.invoke(app, ["discover", "tools", "--no-color"])
    assert result.exit_code == 0
    assert "forge_classify_shot" in result.stdout
    assert "Peer-authored summary." in result.stdout


def test_discover_tools_unreachable_daemon_exits_2(runner, monkeypatch):
    from forge_bridge.cli import discover as discover_mod
    from forge_bridge.cli.client import ServerUnreachableError

    def _raise(path):
        raise ServerUnreachableError("ConnectError")

    monkeypatch.setattr(discover_mod, "fetch", _raise)
    result = runner.invoke(app, ["discover", "tools", "--no-color"])
    assert result.exit_code == 2


def test_discover_tools_unreachable_daemon_json_exits_2(runner, monkeypatch):
    from forge_bridge.cli import discover as discover_mod
    from forge_bridge.cli.client import ServerUnreachableError

    def _raise(path):
        raise ServerUnreachableError("ConnectError")

    monkeypatch.setattr(discover_mod, "fetch_raw_envelope", _raise)
    result = runner.invoke(app, ["discover", "tools", "--json"])
    assert result.exit_code == 2
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "server_unreachable"


def test_discover_tool_detail_displays_artist_fields(runner, monkeypatch):
    from forge_bridge.cli import discover as discover_mod

    monkeypatch.setattr(discover_mod, "fetch", lambda path: dict(_SAMPLE_TOOLS[0]))

    result = runner.invoke(
        app, ["discover", "tool", "forge_classify_shot", "--no-color"]
    )
    assert result.exit_code == 0
    assert "tool: forge_classify_shot" in result.stdout
    assert "label: Classify Shot" in result.stdout
    assert "origin: builtin" in result.stdout
    assert "Peer-authored summary." in result.stdout


def test_discover_tool_detail_json_passes_through(runner, monkeypatch):
    from forge_bridge.cli import discover as discover_mod

    envelope = {"data": dict(_SAMPLE_TOOLS[0]), "meta": {}}
    monkeypatch.setattr(discover_mod, "fetch_raw_envelope", lambda path: envelope)

    result = runner.invoke(
        app, ["discover", "tool", "forge_classify_shot", "--json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == envelope


def test_discover_tool_unknown_is_nonzero(runner, monkeypatch):
    """A 404 from the read API (tool not registered) → exit 1."""
    from forge_bridge.cli import discover as discover_mod
    from forge_bridge.cli.client import ServerError

    def _raise(path):
        raise ServerError("tool_not_found", "no tool named 'not_a_tool'", 404)

    monkeypatch.setattr(discover_mod, "fetch", _raise)
    result = runner.invoke(app, ["discover", "tool", "not_a_tool"])
    assert result.exit_code == 1


def test_discover_tool_unreachable_daemon_exits_2(runner, monkeypatch):
    from forge_bridge.cli import discover as discover_mod
    from forge_bridge.cli.client import ServerUnreachableError

    def _raise(path):
        raise ServerUnreachableError("ConnectError")

    monkeypatch.setattr(discover_mod, "fetch", _raise)
    result = runner.invoke(app, ["discover", "tool", "forge_ping"])
    assert result.exit_code == 2


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

