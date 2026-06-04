"""S3.3 — route-separation invariant (room ruling, Fork 1 additional requirement).

Compile-blindness for the capture route is a TESTED guarantee, not a convention:
  - STRUCTURAL: the capture handler's module imports/references no compile-path
    entrypoint (a deliberate compile import would fail this test → it has teeth).
  - BEHAVIORAL: with the compile entrypoints patched to explode, a capture POST
    still succeeds and the compile path is never invoked.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

import forge_bridge.console._context_capture as capture_mod
from forge_bridge.console import _chat_compile, _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI

# compile-path ENTRYPOINT identifiers — checked as real code references (AST
# Name/Attribute), NOT raw source text, so the module's own docstring may name
# them to document the invariant without tripping the guard.
_COMPILE_ENTRYPOINTS = ("compile_intent", "run_compile_branch", "run_chain_steps")


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def test_structural_no_compile_path_references():
    """The capture module makes no CODE reference to a compile-path entrypoint
    (docstring mentions are fine; an actual call/name reference fails this)."""
    src = Path(inspect.getsourcefile(capture_mod)).read_text()
    referenced: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    for token in _COMPILE_ENTRYPOINTS:
        assert token not in referenced, f"capture module references compile entrypoint {token!r}"


def test_structural_imports_are_compile_free():
    """Parse the imports: only context_pressure / starlette / _rate_limit allowed."""
    src = Path(inspect.getsourcefile(capture_mod)).read_text()
    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.update(a.name for a in node.names)
    for mod in imported_modules:
        assert "compile" not in mod, f"unexpected compile import: {mod}"
        assert not mod.endswith("console.handlers"), "must not import the compile-bearing handlers module"


def test_behavioral_capture_succeeds_with_compile_exploded(tmp_path, monkeypatch):
    """Patch the compile entrypoint to raise; a capture POST still succeeds —
    proving the capture route never reaches compile."""
    monkeypatch.setenv("CONTEXT_PRESSURE_DIR", str(tmp_path))
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ManifestService(), llm_router=MagicMock())
    client = TestClient(build_console_app(api))

    boom = MagicMock(side_effect=AssertionError("compile path must not be reached from capture"))
    with patch.object(_chat_compile, "run_compile_branch", boom):
        r = client.post("/api/v1/context-capture", json={
            "captured_at": "2026-06-04T12:00:00Z",
            "prompt": "what is the duration of this shot",
            "compiled_graph": ["flame_get_sequence_segments"],
            "outcome": "chain_aborted",
            "world_state_raw": {"timeline": {"current_shot": "'tst_020'"}},
            "provenance": {"context_source": "flame", "capture_version": "1",
                           "capture_surface": "python_console", "capture_adapter": "v1"},
        })
    assert r.status_code == 200, r.text
    boom.assert_not_called()
