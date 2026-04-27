"""Tests for forge_bridge._sanitize_patterns — single-source-of-truth constants.

Per FB-C D-09 (15-01 Plan Task 1): the new top-level module hoists
INJECTION_MARKERS and _CONTROL_CHAR_RE so both forge_bridge.learning.sanitize
(Phase 7 _sanitize_tag) and forge_bridge.llm._sanitize (FB-C
_sanitize_tool_result) can import the same patterns.
"""
from __future__ import annotations


class TestSanitizePatternsImport:
    def test_import_injection_markers_succeeds(self):
        from forge_bridge._sanitize_patterns import INJECTION_MARKERS  # noqa: F401

    def test_import_control_char_re_succeeds(self):
        from forge_bridge._sanitize_patterns import _CONTROL_CHAR_RE  # noqa: F401


class TestInjectionMarkers:
    def test_injection_markers_is_tuple_of_eight(self):
        from forge_bridge._sanitize_patterns import INJECTION_MARKERS

        assert isinstance(INJECTION_MARKERS, tuple)
        assert len(INJECTION_MARKERS) == 8

    def test_injection_markers_contents_match_phase7_verbatim(self):
        """Locked verbatim from forge_bridge/learning/sanitize.py:50-59."""
        from forge_bridge._sanitize_patterns import INJECTION_MARKERS

        expected = (
            "ignore previous",
            "<|",
            "|>",
            "[INST]",
            "[/INST]",
            "<|im_start|>",
            "```",
            "---",
        )
        assert INJECTION_MARKERS == expected


class TestControlCharRegex:
    def test_control_char_re_matches_nul(self):
        from forge_bridge._sanitize_patterns import _CONTROL_CHAR_RE

        assert _CONTROL_CHAR_RE.search("a\x00b") is not None

    def test_control_char_re_does_not_match_clean_ascii(self):
        from forge_bridge._sanitize_patterns import _CONTROL_CHAR_RE

        assert _CONTROL_CHAR_RE.search("project:acme") is None
