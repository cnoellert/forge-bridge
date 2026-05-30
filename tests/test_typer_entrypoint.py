"""Acceptance tests for the Typer-root refactor in forge_bridge/__main__.py.

Covers D-11 (`console --help` exits 0) and the post-refactor invariant that
bare ``python -m forge_bridge`` prints help and exits 0 — the MCP server only
starts via the explicit ``mcp stdio`` / ``mcp http`` subcommands. The legacy
top-level ``--console-port`` flag is gone; ``FORGE_CONSOLE_PORT`` is the
canonical env-var precedence handle. Subprocess-based to catch side-effect
regressions.
"""
from __future__ import annotations

import os
import subprocess
import sys


PYTHON = sys.executable
MODULE = "forge_bridge"


# ── D-11: bare `forge-bridge --help` exits 0 ────────────────────────────────

def test_bare_forge_bridge_help_exits_zero():
    result = subprocess.run(
        [PYTHON, "-m", MODULE, "--help"],
        capture_output=True, text=True, timeout=10.0,
    )
    assert result.returncode == 0, (
        f"python -m forge_bridge --help must exit 0. "
        f"stderr: {result.stderr!r}"
    )
    assert "forge-bridge" in result.stdout, (
        f"Expected the Typer root help to mention 'forge-bridge'. "
        f"stdout: {result.stdout!r}"
    )


# ── D-11: `forge-bridge console --help` exits 0 ─────────────────────────────

def test_console_subcommand_help_exits_zero():
    result = subprocess.run(
        [PYTHON, "-m", MODULE, "console", "--help"],
        capture_output=True, text=True, timeout=10.0,
    )
    assert result.returncode == 0, (
        f"python -m forge_bridge console --help must exit 0. "
        f"stderr: {result.stderr!r}"
    )
    assert "Artist Console" in result.stdout, (
        f"Expected the console subcommand help to mention 'Artist Console'. "
        f"stdout: {result.stdout!r}"
    )


# ── bare invocation prints help and exits 0 (post-refactor invariant) ──────

def test_bare_forge_bridge_prints_help_and_exits_zero():
    """Bare ``python -m forge_bridge`` (no args, no subcommand) must print
    help and exit 0 — it must NOT start any services.

    This is the post Typer-front-door invariant documented in
    ``forge_bridge/cli/main.py`` and CLAUDE.md: the MCP server only starts
    via the explicit ``mcp stdio`` / ``mcp http`` subcommands. Earlier
    versions of this test asserted the inverse (bare invocation falling
    through to mcp_main); that behavior was deliberately removed when the
    Typer root callback gained the ``ctx.invoked_subcommand is None`` →
    print-help-and-exit branch.

    Subprocess-based on purpose: a side-effecting __main__ import would
    bypass the callback guard and surface here.
    """
    proc = subprocess.run(
        [PYTHON, "-m", MODULE],
        capture_output=True, text=True, timeout=10.0,
    )
    assert proc.returncode == 0, (
        f"Bare `python -m forge_bridge` must exit 0. "
        f"stdout: {proc.stdout!r}, stderr: {proc.stderr!r}"
    )
    # Help text identification: Typer root help mentions the app name and
    # the canonical subcommand surface.
    assert "forge-bridge" in proc.stdout, (
        f"Expected Typer root help on stdout mentioning 'forge-bridge'. "
        f"stdout: {proc.stdout!r}"
    )
    # Negative assertion: bare invocation must NOT have started MCP — the
    # pre-refactor failure mode emitted the bridge-unreachable WARNING on
    # stderr from mcp_main()'s startup_bridge call.
    assert "Could not connect to forge-bridge" not in proc.stderr, (
        f"Bare `python -m forge_bridge` must NOT start MCP. "
        f"Found bridge-unreachable warning in stderr: {proc.stderr!r}"
    )


# ── regression guard: module import has no side effects ────────────────────

def test_module_importable_without_side_effects():
    """Regression guard for the current broken state where `__main__.py`
    called `main()` at import time — which is incompatible with both
    `[project.scripts]` and `from forge_bridge.__main__ import app`.
    """
    result = subprocess.run(
        [
            PYTHON, "-c",
            "import forge_bridge.__main__; print('OK', forge_bridge.__main__.app.info.name)",
        ],
        capture_output=True, text=True, timeout=10.0,
    )
    assert result.returncode == 0, (
        f"`import forge_bridge.__main__` must succeed with zero side effects. "
        f"stderr: {result.stderr!r}"
    )
    assert "OK" in result.stdout, result.stdout
    assert "forge-bridge" in result.stdout, (
        f"Expected `app.info.name` to be 'forge-bridge'. stdout: {result.stdout!r}"
    )


# ── FORGE_CONSOLE_PORT env-var precedence (post-Typer-front-door) ──────────

def test_console_port_env_var_overrides_default(monkeypatch):
    """``FORGE_CONSOLE_PORT`` is the canonical precedence handle for console
    port selection — the legacy top-level ``--console-port`` flag was
    removed when the Typer root replaced the old single-callback main.

    Precedence (post-refactor): FORGE_CONSOLE_PORT env > default (9996).
    Verify via ``forge_bridge.config.console_port()`` which is what the
    MCP bootstrap reads at startup (see ``forge_bridge.mcp.server`` step 4).
    """
    from forge_bridge import config

    # Default path: no env → 9996
    monkeypatch.delenv("FORGE_CONSOLE_PORT", raising=False)
    assert config.console_port() == 9996, (
        "Default console port must be 9996 when FORGE_CONSOLE_PORT is unset."
    )

    # Env-var path: explicit override wins
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "9997")
    assert config.console_port() == 9997, (
        f"FORGE_CONSOLE_PORT=9997 must override default. "
        f"Got: {config.console_port()!r}"
    )

# ── sanity: `app` is a Typer instance (needed for [project.scripts]) ──────

def test_app_attribute_is_typer_instance():
    import typer
    from forge_bridge.__main__ import app
    assert isinstance(app, typer.Typer), (
        f"forge_bridge.__main__.app must be a typer.Typer instance for "
        f"[project.scripts] `forge-bridge = \"forge_bridge.__main__:app\"` to work. "
        f"Got: {type(app)!r}"
    )
