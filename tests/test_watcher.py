"""Tests for forge_bridge.learning.watcher — synthesized tool hot-loading."""
import pytest
from mcp.server.fastmcp import FastMCP
from forge_bridge.learning.watcher import _scan_once, _load_fn


@pytest.fixture
def synth_dir(tmp_path):
    """Create a temporary synthesized directory."""
    d = tmp_path / "synthesized"
    d.mkdir()
    return d


@pytest.fixture
def fresh_mcp():
    return FastMCP("test_watcher")


def _write_tool(synth_dir, name, body="return 'ok'"):
    """Write a minimal tool .py file."""
    code = f"def {name}() -> str:\n    \"\"\"Test tool.\"\"\"\n    {body}\n"
    path = synth_dir / f"{name}.py"
    path.write_text(code)
    return path


class TestWatcherLoadsNewFile:
    def test_new_file_registers_tool(self, fresh_mcp, synth_dir):
        seen = {}
        _write_tool(synth_dir, "synth_hello")
        _scan_once(fresh_mcp, seen, synth_dir)
        assert "synth_hello" in fresh_mcp._tool_manager._tools
        assert "synth_hello" in seen

    def test_new_file_has_synthesized_source(self, fresh_mcp, synth_dir):
        seen = {}
        _write_tool(synth_dir, "synth_tagged")
        _scan_once(fresh_mcp, seen, synth_dir)
        tool = fresh_mcp._tool_manager._tools["synth_tagged"]
        assert tool.meta == {"_source": "synthesized"}


class TestWatcherReloadsChangedFile:
    def test_changed_file_updates_tool(self, fresh_mcp, synth_dir):
        seen = {}
        _write_tool(synth_dir, "synth_evolve", body="return 'v1'")
        _scan_once(fresh_mcp, seen, synth_dir)
        old_hash = seen["synth_evolve"]
        # Modify the file
        _write_tool(synth_dir, "synth_evolve", body="return 'v2'")
        _scan_once(fresh_mcp, seen, synth_dir)
        assert seen["synth_evolve"] != old_hash
        assert "synth_evolve" in fresh_mcp._tool_manager._tools


class TestWatcherRemovesDeletedFile:
    def test_deleted_file_removes_tool(self, fresh_mcp, synth_dir):
        seen = {}
        path = _write_tool(synth_dir, "synth_goodbye")
        _scan_once(fresh_mcp, seen, synth_dir)
        assert "synth_goodbye" in fresh_mcp._tool_manager._tools
        # Delete the file
        path.unlink()
        _scan_once(fresh_mcp, seen, synth_dir)
        assert "synth_goodbye" not in fresh_mcp._tool_manager._tools
        assert "synth_goodbye" not in seen


class TestWatcherEdgeCases:
    def test_skips_dunder_files(self, fresh_mcp, synth_dir):
        seen = {}
        (synth_dir / "__init__.py").write_text("")
        _scan_once(fresh_mcp, seen, synth_dir)
        assert len(seen) == 0

    def test_nonexistent_dir_is_noop(self, fresh_mcp, tmp_path):
        seen = {}
        _scan_once(fresh_mcp, seen, tmp_path / "does_not_exist")
        assert len(seen) == 0

    def test_file_without_matching_callable_skipped(self, fresh_mcp, synth_dir):
        seen = {}
        # File has wrong function name
        (synth_dir / "synth_mismatch.py").write_text("def other_name() -> str:\n    return 'x'\n")
        _scan_once(fresh_mcp, seen, synth_dir)
        assert "synth_mismatch" not in fresh_mcp._tool_manager._tools
        assert "synth_mismatch" not in seen
