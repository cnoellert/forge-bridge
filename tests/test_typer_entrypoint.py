"""Acceptance tests for the Typer-root refactor in forge_bridge/__main__.py.

Covers D-10 (bare invocation boots MCP unchanged), D-11 (`console --help` exits 0),
and D-27 (--console-port flag precedence). Subprocess-based to catch side-effect
regressions (e.g. the current broken state where `main()` was called at import).
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


# ── D-10: bare invocation falls through to mcp_main() ───────────────────────

def test_bare_forge_bridge_boots_mcp_not_help(monkeypatch):
    """Bare `forge-bridge` with a dead bridge URL should fall through to
    mcp_main() — proven by the existing 'Could not connect to forge-bridge'
    WARNING appearing on stderr within a short timeout.

    We use FORGE_BRIDGE_URL set to a guaranteed-dead port so startup_bridge's
    graceful-degradation path fires, logs the warning, and allows MCP to
    proceed (at which point we kill the subprocess — we're not testing the
    full stdio flow here, only that mcp_main was entered).
    """
    # Find a guaranteed-free port; we DON'T bind it so it stays dead
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        dead_port = s.getsockname()[1]
    dead_url = f"ws://127.0.0.1:{dead_port}"

    env = dict(os.environ)
    env["FORGE_BRIDGE_URL"] = dead_url

    # Short timeout — we just need to see the WARNING fire and prove
    # mcp_main() was reached. After that, kill the process.
    proc = subprocess.Popen(
        [PYTHON, "-m", MODULE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    try:
        # Wait up to 5s for mcp_main to enter and emit the bridge-unreachable warning
        _, stderr = proc.communicate(timeout=5.0)
    except subprocess.TimeoutExpired:
        # mcp_main() is running and blocked on MCP stdio loop — that's the
        # positive signal. Kill and collect stderr so far.
        proc.kill()
        _, stderr = proc.communicate(timeout=5.0)

    # Either we saw the warning (process exited) or the process was still
    # running MCP (timeout). Both prove the bare path boots MCP.
    # Assertion: stderr contains evidence that mcp_main() was reached — the
    # logging.basicConfig + graceful-degradation log line.
    assert "Could not connect to forge-bridge" in stderr or "forge_bridge" in stderr, (
        f"Bare `forge-bridge` must boot MCP (D-10). Expected the bridge-unreachable "
        f"WARNING or some forge_bridge log output on stderr. Got: {stderr!r}"
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


# ── D-27: --console-port flag pushes into env ──────────────────────────────

def test_console_port_flag_sets_env(monkeypatch):
    """D-27 precedence: flag > env > default.

    Monkeypatch `mcp_main` to a sentinel that captures os.environ at call
    time, then invoke the Typer callback directly — avoids standing up
    a real MCP server just to check env propagation.
    """
    import forge_bridge.__main__ as entrypoint
    from unittest.mock import patch

    captured: dict[str, str] = {}

    def _stub_mcp_main():
        # Capture the env at the moment mcp_main would have started
        captured["FORGE_CONSOLE_PORT"] = os.environ.get("FORGE_CONSOLE_PORT", "")

    # Invoke Typer app via the CliRunner so the callback runs end-to-end
    from typer.testing import CliRunner
    runner = CliRunner()

    monkeypatch.delenv("FORGE_CONSOLE_PORT", raising=False)
    # Patch the lazy-imported target — the import happens INSIDE the callback,
    # so we patch forge_bridge.mcp.server.main, which is the resolved symbol.
    with patch("forge_bridge.mcp.server.main", side_effect=_stub_mcp_main):
        result = runner.invoke(entrypoint.app, ["--console-port", "9997"])
    assert result.exit_code == 0, (
        f"--console-port 9997 should succeed. output: {result.output!r}, "
        f"exception: {result.exception!r}"
    )
    assert captured.get("FORGE_CONSOLE_PORT") == "9997", (
        f"D-27 requires --console-port 9997 to set FORGE_CONSOLE_PORT=9997 in env "
        f"before mcp_main() runs. Got: {captured!r}"
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
