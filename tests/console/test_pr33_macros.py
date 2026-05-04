"""PR33 — Macro expansion is deterministic and single-pass."""
from __future__ import annotations

import json

import forge_bridge.console._macros as macros

from forge_bridge.console._macros import expand_macro, register_macro


def test_macro_expands_basic():
    register_macro("deploy_check", "list projects -> list versions")

    out = expand_macro("deploy_check")

    assert out == "list projects -> list versions"


def test_macro_expands_with_run_prefix():
    register_macro("deploy_check", "list projects -> list versions")

    out = expand_macro("run deploy_check")

    assert out == "list projects -> list versions"


def test_macro_with_params_passthrough():
    register_macro("deploy_check", "list projects -> list versions")

    out = expand_macro("run deploy_check project_id=abc")

    assert out == "list projects -> list versions project_id=abc"


def test_unknown_macro_passthrough():
    out = expand_macro("run unknown_macro")

    assert out == "run unknown_macro"


def test_macro_not_first_token_no_expand():
    register_macro("deploy_check", "list projects")

    out = expand_macro("please deploy_check")

    assert out == "please deploy_check"


def test_macro_single_pass_no_recursion():
    register_macro("a", "b")
    register_macro("b", "c")

    out = expand_macro("a")

    # Only expands once: a -> b (not b -> c)
    assert out == "b"


def test_macro_persists_to_file(tmp_path, monkeypatch):
    macro_file = tmp_path / "macros.json"

    monkeypatch.setattr(macros, "_MACRO_FILE", str(macro_file))

    macros._clear_macros_for_tests()
    macros.register_macro("persist_test", "list projects")

    assert macro_file.exists()

    data = json.loads(macro_file.read_text(encoding="utf-8"))
    assert data.get("persist_test") == "list projects"


def test_macro_loads_from_file(tmp_path, monkeypatch):
    macro_file = tmp_path / "macros.json"
    macro_file.write_text(
        json.dumps({"loaded_macro": "list projects"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(macros, "_MACRO_FILE", str(macro_file))

    macros._clear_macros_for_tests()
    macros._load_macros()

    assert macros.get_macro("loaded_macro") == "list projects"
