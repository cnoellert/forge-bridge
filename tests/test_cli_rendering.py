"""CLI-04 — Rich rendering helpers tests."""
from __future__ import annotations

import io

import pytest

from forge_bridge.cli.render import (
    HEADER_STYLE,
    TOOLS_BOX,
    created_column_header,
    format_timestamp,
    make_console,
    short_hash,
    status_chip,
)


class TestMakeConsole:
    def test_default_writes_to_stdout(self):
        console = make_console()
        assert console.stderr is False

    def test_stderr_flag(self):
        console = make_console(stderr=True)
        assert console.stderr is True

    def test_no_color_flag_strips_color_codes(self):
        # Rich's no_color suppresses COLOR codes (e.g. \x1b[31m for red) but
        # preserves style codes (bold/italic/dim) per Rich's documented behavior.
        # See RESEARCH.md §3: "NO_COLOR removes all color output. Styles (bold,
        # italic, dim) are preserved."
        from rich.console import Console as RC
        buf = io.StringIO()
        console = RC(file=buf, no_color=True, force_terminal=True)
        console.print("[bold red]text[/bold red]")
        output = buf.getvalue()
        # No SGR foreground/background color codes (30-39, 40-49, 90-97, 100-107).
        # Bold (1) and reset (0) are allowed because they are non-color style codes.
        for color_code in ("\x1b[31m", "\x1b[91m", "\x1b[38;", "\x1b[48;"):
            assert color_code not in output, f"unexpected color code {color_code!r} in {output!r}"
        assert "text" in output

    def test_no_color_env_auto_handled(self, monkeypatch):
        # Rich Console.__init__ reads NO_COLOR from os.environ automatically.
        monkeypatch.setenv("NO_COLOR", "1")
        from rich.console import Console as RC
        buf = io.StringIO()
        console = RC(file=buf, force_terminal=True)
        console.print("[bold red]text[/bold red]")
        output = buf.getvalue()
        for color_code in ("\x1b[31m", "\x1b[91m", "\x1b[38;", "\x1b[48;"):
            assert color_code not in output, f"unexpected color code {color_code!r} in {output!r}"


class TestStatusChip:
    @pytest.mark.parametrize("status,expected_style", [
        ("active", "green"),
        ("ok", "green"),
        ("loaded", "dim cyan"),
        ("degraded", "yellow"),
        ("warn", "yellow"),
        ("fail", "red"),
        ("absent-when-required", "red"),
        ("absent", "dim"),
    ])
    def test_known_statuses(self, status, expected_style):
        chip = status_chip(status)
        assert str(chip.style) == expected_style

    def test_unknown_falls_back_to_white(self):
        chip = status_chip("totally_unknown_status")
        assert str(chip.style) == "white"


class TestShortHash:
    def test_truncates_to_8_chars(self):
        assert short_hash("a" * 64) == "a" * 8

    def test_none_returns_empty(self):
        assert short_hash(None) == ""

    def test_empty_returns_empty(self):
        assert short_hash("") == ""

    def test_custom_width(self):
        assert short_hash("abcdefghij", width=4) == "abcd"


class TestFormatTimestamp:
    def test_passthrough(self):
        assert format_timestamp("2026-04-22T10:00:00+00:00") == "2026-04-22T10:00:00+00:00"

    def test_none_returns_empty(self):
        assert format_timestamp(None) == ""


class TestConstants:
    def test_tools_box_is_square(self):
        from rich import box
        assert TOOLS_BOX is box.SQUARE

    def test_header_style(self):
        assert HEADER_STYLE == "bold yellow"

    def test_created_column_header(self):
        # Phase 10.1 HUMAN-UAT #2 default-sort affordance.
        assert created_column_header() == "Created ▼"
