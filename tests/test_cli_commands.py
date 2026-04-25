"""CLI-01 — subcommand registration smoke tests.

Verifies that all five Phase 11 subcommands are registered on the console_app
group exposed via `forge_bridge.__main__`. These tests do NOT execute any
business logic; they only confirm `--help` resolves and (where applicable)
the Examples block from D-06 is present.
"""
from __future__ import annotations

from typer.testing import CliRunner

from forge_bridge import __main__ as entrypoint

runner = CliRunner()


def test_console_lists_all_five_subcommands():
    result = runner.invoke(entrypoint.app, ["console", "--help"])
    assert result.exit_code == 0
    for cmd in ("tools", "execs", "manifest", "health", "doctor"):
        assert cmd in result.output


def test_tools_help_exits_zero():
    result = runner.invoke(entrypoint.app, ["console", "tools", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


def test_execs_help_exits_zero():
    result = runner.invoke(entrypoint.app, ["console", "execs", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


def test_manifest_help_exits_zero():
    result = runner.invoke(entrypoint.app, ["console", "manifest", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


def test_health_help_exits_zero():
    result = runner.invoke(entrypoint.app, ["console", "health", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


def test_doctor_help_exits_zero():
    result = runner.invoke(entrypoint.app, ["console", "doctor", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output
