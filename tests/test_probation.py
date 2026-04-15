"""Tests for forge_bridge.learning.probation — synthesized tool probation tracking."""
import asyncio
from unittest.mock import MagicMock

import pytest

from forge_bridge.learning.probation import ProbationTracker


@pytest.fixture
def tracker(tmp_path):
    """Tracker with threshold=3, using tmp dirs."""
    synth = tmp_path / "synthesized"
    synth.mkdir()
    quarantine = tmp_path / "quarantined"
    return ProbationTracker(
        failure_threshold=3,
        synth_dir=synth,
        quarantine_dir=quarantine,
    )


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    mcp.remove_tool = MagicMock()
    return mcp


class TestProbationTrackerInit:
    def test_default_threshold(self, tmp_path):
        t = ProbationTracker(failure_threshold=3, synth_dir=tmp_path, quarantine_dir=tmp_path)
        assert t._threshold == 3

    def test_env_var_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FORGE_PROBATION_THRESHOLD", "2")
        t = ProbationTracker(synth_dir=tmp_path, quarantine_dir=tmp_path)
        assert t._threshold == 2


class TestRecordSuccess:
    def test_increments_counter(self, tracker):
        tracker.record_success("tool_a")
        assert tracker.get_stats("tool_a")["successes"] == 1
        tracker.record_success("tool_a")
        assert tracker.get_stats("tool_a")["successes"] == 2


class TestRecordFailure:
    def test_increments_and_returns_false_below_threshold(self, tracker):
        result = tracker.record_failure("tool_a")
        assert result is False
        assert tracker.get_stats("tool_a")["failures"] == 1

    def test_returns_true_at_threshold(self, tracker):
        tracker.record_failure("tool_a")
        tracker.record_failure("tool_a")
        result = tracker.record_failure("tool_a")
        assert result is True
        assert tracker.get_stats("tool_a")["failures"] == 3


class TestWrapSuccess:
    def test_calls_original_and_records_success(self, tracker, mock_mcp):
        async def my_tool():
            return "hello"

        wrapped = tracker.wrap(my_tool, "my_tool", mock_mcp)
        result = asyncio.run(wrapped())
        assert result == "hello"
        assert tracker.get_stats("my_tool")["successes"] == 1
        assert tracker.get_stats("my_tool")["failures"] == 0


class TestWrapFailure:
    def test_records_failure_and_reraises(self, tracker, mock_mcp):
        async def bad_tool():
            raise ValueError("boom")

        wrapped = tracker.wrap(bad_tool, "bad_tool", mock_mcp)
        with pytest.raises(ValueError, match="boom"):
            asyncio.run(wrapped())
        assert tracker.get_stats("bad_tool")["failures"] == 1

    def test_triggers_quarantine_at_threshold(self, tracker, mock_mcp):
        # Create a file so quarantine has something to move
        src = tracker._synth_dir / "fail_tool.py"
        src.write_text("def fail_tool(): pass\n")

        async def fail_tool():
            raise RuntimeError("fail")

        wrapped = tracker.wrap(fail_tool, "fail_tool", mock_mcp)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                asyncio.run(wrapped())

        # File should be quarantined
        assert not src.exists()
        assert (tracker._quarantine_dir / "fail_tool.py").exists()
        mock_mcp.remove_tool.assert_called_with("fail_tool")


class TestQuarantine:
    def test_moves_file(self, tracker, mock_mcp):
        src = tracker._synth_dir / "tool_x.py"
        src.write_text("def tool_x(): pass\n")
        tracker.quarantine("tool_x", mock_mcp)
        assert not src.exists()
        assert (tracker._quarantine_dir / "tool_x.py").exists()

    def test_calls_remove_tool(self, tracker, mock_mcp):
        src = tracker._synth_dir / "tool_y.py"
        src.write_text("def tool_y(): pass\n")
        tracker.quarantine("tool_y", mock_mcp)
        mock_mcp.remove_tool.assert_called_with("tool_y")

    def test_creates_quarantine_dir(self, tracker, mock_mcp):
        assert not tracker._quarantine_dir.exists()
        src = tracker._synth_dir / "tool_z.py"
        src.write_text("def tool_z(): pass\n")
        tracker.quarantine("tool_z", mock_mcp)
        assert tracker._quarantine_dir.exists()

    def test_handles_missing_source_file(self, tracker, mock_mcp):
        # Should not crash even if source file doesn't exist
        tracker.quarantine("nonexistent_tool", mock_mcp)
        mock_mcp.remove_tool.assert_called_with("nonexistent_tool")


class TestGetStats:
    def test_returns_zeros_for_unknown(self, tracker):
        stats = tracker.get_stats("unknown")
        assert stats == {"successes": 0, "failures": 0}

    def test_returns_correct_counts(self, tracker):
        tracker.record_success("counted")
        tracker.record_success("counted")
        tracker.record_failure("counted")
        stats = tracker.get_stats("counted")
        assert stats == {"successes": 2, "failures": 1}
