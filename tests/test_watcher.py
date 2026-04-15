"""Tests for forge_bridge.learning.watcher — synthesized tool hot-loading."""
import pytest
from unittest.mock import MagicMock, patch
from mcp.server.fastmcp import FastMCP
from forge_bridge.learning.watcher import _scan_once, _load_fn
from forge_bridge.learning.manifest import manifest_register
from forge_bridge.learning.probation import ProbationTracker


@pytest.fixture
def synth_dir(tmp_path):
    """Create a temporary synthesized directory."""
    d = tmp_path / "synthesized"
    d.mkdir()
    return d


@pytest.fixture
def manifest_path(synth_dir):
    """Return the manifest path co-located with synth_dir."""
    return synth_dir / ".manifest.json"


@pytest.fixture
def fresh_mcp():
    return FastMCP("test_watcher")


def _write_tool(synth_dir, name, body="return 'ok'", register=True):
    """Write a minimal tool .py file and optionally register in manifest."""
    code = f"def {name}() -> str:\n    \"\"\"Test tool.\"\"\"\n    {body}\n"
    path = synth_dir / f"{name}.py"
    path.write_text(code)
    if register:
        manifest_register(path, manifest_path=synth_dir / ".manifest.json")
    return path


class TestWatcherLoadsNewFile:
    def test_new_file_registers_tool(self, fresh_mcp, synth_dir, manifest_path):
        seen = {}
        _write_tool(synth_dir, "synth_hello")
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert "synth_hello" in fresh_mcp._tool_manager._tools
        assert "synth_hello" in seen

    def test_new_file_has_synthesized_source(self, fresh_mcp, synth_dir, manifest_path):
        seen = {}
        _write_tool(synth_dir, "synth_tagged")
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        tool = fresh_mcp._tool_manager._tools["synth_tagged"]
        assert tool.meta == {"_source": "synthesized"}


class TestWatcherReloadsChangedFile:
    def test_changed_file_updates_tool(self, fresh_mcp, synth_dir, manifest_path):
        seen = {}
        _write_tool(synth_dir, "synth_evolve", body="return 'v1'")
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        old_hash = seen["synth_evolve"]
        # Modify the file (re-registers in manifest)
        _write_tool(synth_dir, "synth_evolve", body="return 'v2'")
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert seen["synth_evolve"] != old_hash
        assert "synth_evolve" in fresh_mcp._tool_manager._tools


class TestWatcherRemovesDeletedFile:
    def test_deleted_file_removes_tool(self, fresh_mcp, synth_dir, manifest_path):
        seen = {}
        path = _write_tool(synth_dir, "synth_goodbye")
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert "synth_goodbye" in fresh_mcp._tool_manager._tools
        # Delete the file
        path.unlink()
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert "synth_goodbye" not in fresh_mcp._tool_manager._tools
        assert "synth_goodbye" not in seen


class TestWatcherEdgeCases:
    def test_skips_dunder_files(self, fresh_mcp, synth_dir, manifest_path):
        seen = {}
        (synth_dir / "__init__.py").write_text("")
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert len(seen) == 0

    def test_nonexistent_dir_is_noop(self, fresh_mcp, tmp_path):
        seen = {}
        _scan_once(fresh_mcp, seen, tmp_path / "does_not_exist")
        assert len(seen) == 0

    def test_file_without_matching_callable_skipped(self, fresh_mcp, synth_dir, manifest_path):
        seen = {}
        # File has wrong function name — register in manifest so it passes manifest check
        path = synth_dir / "synth_mismatch.py"
        path.write_text("def other_name() -> str:\n    return 'x'\n")
        manifest_register(path, manifest_path=manifest_path)
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert "synth_mismatch" not in fresh_mcp._tool_manager._tools
        assert "synth_mismatch" not in seen

    def test_rejects_file_not_in_manifest(self, fresh_mcp, synth_dir, manifest_path):
        """Files not in the manifest are rejected (CR-001)."""
        seen = {}
        _write_tool(synth_dir, "synth_rogue", register=False)
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert "synth_rogue" not in fresh_mcp._tool_manager._tools
        assert "synth_rogue" not in seen

    def test_rejects_file_with_tampered_content(self, fresh_mcp, synth_dir, manifest_path):
        """Files whose content doesn't match manifest hash are rejected (CR-001)."""
        seen = {}
        path = _write_tool(synth_dir, "synth_tampered")
        # Tamper with the file after manifest registration
        path.write_text("def synth_tampered() -> str:\n    \"\"\"Evil.\"\"\"\n    return 'hacked'\n")
        _scan_once(fresh_mcp, seen, synth_dir, manifest_path=manifest_path)
        assert "synth_tampered" not in fresh_mcp._tool_manager._tools
        assert "synth_tampered" not in seen


class TestWatcherTrackerIntegration:
    def test_tracker_none_no_wrapping(self, fresh_mcp, synth_dir, manifest_path):
        """When tracker is None, tools are registered without wrapping."""
        seen = {}
        _write_tool(synth_dir, "synth_plain")
        _scan_once(fresh_mcp, seen, synth_dir, tracker=None, manifest_path=manifest_path)
        assert "synth_plain" in fresh_mcp._tool_manager._tools
        assert "synth_plain" in seen

    def test_tracker_wraps_before_registration(self, fresh_mcp, synth_dir, tmp_path, manifest_path):
        """When tracker is provided, wrap() is called before register_tool."""
        quarantine = tmp_path / "quarantined"
        tracker = ProbationTracker(
            failure_threshold=3,
            synth_dir=synth_dir,
            quarantine_dir=quarantine,
        )
        seen = {}
        _write_tool(synth_dir, "synth_tracked")

        with patch.object(tracker, "wrap", wraps=tracker.wrap) as mock_wrap:
            _scan_once(fresh_mcp, seen, synth_dir, tracker=tracker, manifest_path=manifest_path)
            mock_wrap.assert_called_once()
            call_args = mock_wrap.call_args
            assert call_args[0][1] == "synth_tracked"  # tool_name arg

        assert "synth_tracked" in fresh_mcp._tool_manager._tools
