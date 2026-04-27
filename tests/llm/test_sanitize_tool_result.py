"""Unit tests for forge_bridge/llm/_sanitize.py — _sanitize_tool_result helper.

Coverage map:
    LLMTOOL-05  Tool result size cap — truncate to 8192 bytes, override kwarg
    LLMTOOL-06  Sanitization boundary — control-char strip, injection-marker
                replacement (NOT rejection — semantic divergence from Phase 7
                _sanitize_tag, intentional per FB-C CONTEXT.md <specifics>)

Test class layout mirrors tests/test_sanitize.py::TestSanitizeTag for
consistency with the existing sanitization test conventions.
"""
from __future__ import annotations

import logging

import pytest

from forge_bridge.llm._sanitize import (
    _BLOCKED_TOKEN,
    _TOOL_RESULT_MAX_BYTES,
    _sanitize_tool_result,
)


# ---------------------------------------------------------------------------
# Step 1 coverage — control-char stripping (preserves \n, \t)
# ---------------------------------------------------------------------------


class TestSanitizeToolResultControlChars:
    """D-11 step 1: strip ASCII control chars EXCEPT \\n and \\t."""

    def test_nul_byte_stripped(self):
        assert _sanitize_tool_result("a\x00b") == "ab"

    def test_other_control_chars_stripped(self):
        # \x01 through \x1f (except \x09 tab and \x0a newline), plus \x7f DEL
        for cc in (0x01, 0x05, 0x0b, 0x0c, 0x0d, 0x1f, 0x7f):
            inp = f"a{chr(cc)}b"
            out = _sanitize_tool_result(inp)
            assert out == "ab", (
                f"control char \\x{cc:02x} not stripped: input={inp!r}, output={out!r}"
            )

    def test_newline_preserved(self):
        assert _sanitize_tool_result("a\nb") == "a\nb"

    def test_tab_preserved(self):
        assert _sanitize_tool_result("a\tb") == "a\tb"

    def test_mixed_keeps_format_strips_garbage(self):
        # Newline and tab survive the strip; \x00 and \x01 do not.
        assert _sanitize_tool_result("line1\nline2\tcol\x00\x01end") == "line1\nline2\tcolend"


# ---------------------------------------------------------------------------
# Step 2 coverage — injection-marker REPLACEMENT (NOT rejection)
# ---------------------------------------------------------------------------


class TestSanitizeToolResultInjectionMarkers:
    """D-11 step 2: REPLACE case-insensitive INJECTION_MARKERS substrings inline
    with [BLOCKED:INJECTION_MARKER]. Semantic divergence from _sanitize_tag
    (which RETURNS None) is intentional per FB-C CONTEXT.md <specifics>."""

    def test_lowercase_marker_replaced(self):
        out = _sanitize_tool_result("please ignore previous text")
        assert _BLOCKED_TOKEN in out
        # The literal substring should be GONE (replaced)
        assert "ignore previous" not in out

    def test_uppercase_marker_replaced(self):
        # Case-insensitive match per re.IGNORECASE
        out = _sanitize_tool_result("STOP. IGNORE PREVIOUS.")
        assert _BLOCKED_TOKEN in out
        assert "IGNORE PREVIOUS" not in out

    def test_mixed_case_marker_replaced(self):
        out = _sanitize_tool_result("Ignore Previous Instructions.")
        assert _BLOCKED_TOKEN in out

    def test_multiple_markers_all_replaced(self):
        # Multiple distinct markers from INJECTION_MARKERS in same input.
        # NOTE: regex alternation is leftmost-first — the markers `<|` and `|>`
        # individually match BEFORE `<|im_start|>` would, so the outer brackets
        # get replaced while the inner `im_start` text remains as a fragment
        # between two BLOCKED tokens. This is still safe: the framing markers
        # are neutralized, and bare `im_start` text has no prompt-injection
        # power without its surrounding brackets. The "ignore previous" marker
        # is also replaced.
        out = _sanitize_tool_result("<|im_start|> ignore previous junk")
        # At least three distinct markers should have been replaced:
        # `<|`, `|>`, and `ignore previous` -> 3 BLOCKED tokens minimum
        assert out.count(_BLOCKED_TOKEN) >= 3, (
            f"expected 3+ replacements, got: {out!r}"
        )
        # Verify the surrounding markers are gone (the framing-bracket pair)
        assert "<|" not in out
        assert "|>" not in out
        assert "ignore previous" not in out

    def test_two_markers_in_same_text_both_replaced(self):
        # Two non-overlapping markers — each gets its own BLOCKED token
        out = _sanitize_tool_result("ignore previous and also [INST]")
        assert out.count(_BLOCKED_TOKEN) == 2, (
            f"expected exactly 2 replacements, got: {out!r}"
        )
        assert "ignore previous" not in out
        assert "[INST]" not in out

    def test_no_marker_returns_original_text(self):
        clean = "This is a perfectly fine tool result with no injection."
        assert _sanitize_tool_result(clean) == clean

    def test_marker_at_string_start(self):
        out = _sanitize_tool_result("ignore previous trailing")
        assert out.startswith(_BLOCKED_TOKEN)

    def test_marker_at_string_end(self):
        out = _sanitize_tool_result("leading ignore previous")
        assert out.endswith(_BLOCKED_TOKEN)

    def test_replacement_is_not_rejection(self):
        # Confirm semantic divergence — we DO get a string back (not None)
        out = _sanitize_tool_result("ignore previous")
        assert isinstance(out, str)
        assert out is not None


# ---------------------------------------------------------------------------
# Step 3 coverage — byte truncation with D-08 suffix
# ---------------------------------------------------------------------------


class TestSanitizeToolResultTruncation:
    """D-08 / LLMTOOL-05: truncate to _TOOL_RESULT_MAX_BYTES (default 8192)
    with the suffix `\\n[...truncated, full result was {n} bytes]` where {n}
    is the ORIGINAL byte length."""

    def test_at_max_bytes_no_truncation(self):
        # Exactly 8192 bytes — no truncation
        text = "a" * 8192
        out = _sanitize_tool_result(text)
        assert out == text
        assert "truncated" not in out

    def test_one_byte_over_truncates(self):
        text = "a" * 8193
        out = _sanitize_tool_result(text)
        assert "[...truncated, full result was 8193 bytes]" in out

    def test_suffix_contains_original_byte_length(self):
        text = "x" * 100000
        out = _sanitize_tool_result(text)
        # Suffix interpolates the ORIGINAL byte length, not the truncated length
        assert "100000 bytes" in out
        assert "8192 bytes" not in out

    def test_override_max_bytes_kwarg(self):
        text = "a" * 1000
        out = _sanitize_tool_result(text, max_bytes=100)
        assert "[...truncated, full result was 1000 bytes]" in out
        # Body must be at most 100 bytes; the suffix is appended after
        body_only = out.split("\n[...truncated")[0]
        assert len(body_only.encode("utf-8")) <= 100

    def test_multibyte_utf8_truncation_safe(self):
        # π is 2 UTF-8 bytes — 5000 of them is 10000 bytes
        text = "π" * 5000
        out = _sanitize_tool_result(text)
        # Must not raise UnicodeDecodeError
        assert "[...truncated" in out
        assert "10000 bytes" in out
        # Body bytes must be <= 8192 (boundary may drop a partial codepoint)
        body_only = out.split("\n[...truncated")[0]
        assert len(body_only.encode("utf-8")) <= 8192

    def test_truncation_preserves_d08_suffix_format(self):
        # D-08 verbatim: "\n[...truncated, full result was {n} bytes]"
        # Note: leading \n, then bracketed text. Lock the exact format.
        text = "a" * 9000
        out = _sanitize_tool_result(text)
        assert out.endswith("\n[...truncated, full result was 9000 bytes]")


# ---------------------------------------------------------------------------
# Logging coverage — operator-visible WARNING on injection-marker hit
# ---------------------------------------------------------------------------


class TestSanitizeToolResultLogging:
    """When an injection marker is detected, the helper emits a single WARNING
    log line (not per-match — avoids flooding on a result with many markers)."""

    def test_warning_emitted_on_injection_marker(self, caplog):
        with caplog.at_level(logging.WARNING, logger="forge_bridge.llm._sanitize"):
            _sanitize_tool_result("ignore previous instructions and...")
        warning_records = [
            r for r in caplog.records
            if r.levelno == logging.WARNING
            and "injection marker" in r.message
        ]
        assert len(warning_records) >= 1, (
            f"expected at least 1 WARNING log on injection marker hit; "
            f"got {[r.message for r in caplog.records]}"
        )


# ---------------------------------------------------------------------------
# Constant coverage — locked default
# ---------------------------------------------------------------------------


class TestSanitizeToolResultConstants:
    """LLMTOOL-05 D-08: the canonical default is 8192 bytes."""

    def test_max_bytes_default_is_8192(self):
        assert _TOOL_RESULT_MAX_BYTES == 8192


# ---------------------------------------------------------------------------
# Composition coverage — all three transformations apply IN ORDER
# ---------------------------------------------------------------------------


class TestSanitizeToolResultComposition:
    """D-11 mandates the order: 1) strip control, 2) replace markers, 3) truncate."""

    def test_control_char_stripped_then_marker_replaced(self):
        # Control char inside a marker prefix shouldn't prevent the marker match
        # after step 1 strips the control char.
        # "ignore\x00 previous" -> after step 1 -> "ignore previous" -> marker hit
        out = _sanitize_tool_result("ignore\x00 previous text")
        assert _BLOCKED_TOKEN in out

    def test_long_string_with_markers_truncates_after_replace(self):
        # Replace happens BEFORE truncate, so a marker in the head of a 100KB
        # string is replaced before the truncation kicks in.
        text = "ignore previous " + ("x" * 50000)
        out = _sanitize_tool_result(text)
        assert _BLOCKED_TOKEN in out  # marker was replaced even though we truncate
        assert "truncated" in out
