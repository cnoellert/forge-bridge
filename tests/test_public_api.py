"""
Unit tests for forge-bridge's public API surface (Phase 4 API-01..API-05, PKG-02, PKG-03).

Requirements covered:
    API-01  forge_bridge.__all__ exports the 11-name consumer surface
    API-04  startup_bridge / shutdown_bridge public; _startup / _shutdown removed
    API-05  register_tools() raises RuntimeError after mcp.run() has started
    PKG-02  pyproject.toml version is 1.0.0
    PKG-03  grep finds zero portofino / assist-01 / ACM_ matches in forge_bridge/
"""
from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest


# ── API-01 / D-02 — Public-API importability + __all__ contract ─────────────

def test_public_api_importable():
    """All 11 public symbols import cleanly from forge_bridge root (D-02)."""
    from forge_bridge import (
        LLMRouter,
        get_router,
        ExecutionLog,
        SkillSynthesizer,
        register_tools,
        get_mcp,
        startup_bridge,
        shutdown_bridge,
        execute,
        execute_json,
        execute_and_read,
    )
    # Sanity: callables are callable
    assert callable(LLMRouter)
    assert callable(SkillSynthesizer)
    assert callable(ExecutionLog)
    assert callable(get_router)
    assert callable(get_mcp)
    assert callable(register_tools)
    assert callable(startup_bridge)
    assert callable(shutdown_bridge)
    assert callable(execute)
    assert callable(execute_json)
    assert callable(execute_and_read)


def test_all_contract():
    """forge_bridge.__all__ matches the 15-name surface exactly (Phase 4 D-01/D-02 + Phase 6 LRN-02/LRN-04)."""
    import forge_bridge

    expected = {
        "LLMRouter", "get_router",
        "ExecutionLog", "ExecutionRecord", "StorageCallback",
        "SkillSynthesizer", "PreSynthesisContext", "PreSynthesisHook",
        "register_tools", "get_mcp",
        "startup_bridge", "shutdown_bridge",
        "execute", "execute_json", "execute_and_read",
    }
    assert set(forge_bridge.__all__) == expected, (
        f"__all__ mismatch.\n"
        f"  Extras:   {set(forge_bridge.__all__) - expected}\n"
        f"  Missing:  {expected - set(forge_bridge.__all__)}"
    )
    # Size must equal the expected set (catches duplicates)
    assert len(forge_bridge.__all__) == 15


def test_core_types_not_reexported():
    """Canonical vocabulary types stay at forge_bridge.core, not root (D-03)."""
    import forge_bridge

    for name in ("Project", "Sequence", "Shot", "Asset", "Version",
                 "Media", "Stack", "Layer", "Registry", "Role", "Status"):
        assert name not in forge_bridge.__all__, (
            f"{name} must not be re-exported at forge_bridge root. "
            f"Import from forge_bridge.core instead."
        )


def test_get_mcp_returns_singleton():
    """get_mcp() returns the same FastMCP singleton across calls (D-04)."""
    from forge_bridge import get_mcp
    from forge_bridge.mcp.server import mcp as server_mcp

    assert get_mcp() is server_mcp
    assert get_mcp() is get_mcp()  # idempotent


# ── API-04 / D-11..D-13 — Server lifecycle rename + signatures ──────────────

def test_lifecycle_renamed_no_alias():
    """_startup / _shutdown removed; startup_bridge / shutdown_bridge added (D-11)."""
    import forge_bridge.mcp.server as server_mod
    assert hasattr(server_mod, "startup_bridge")
    assert hasattr(server_mod, "shutdown_bridge")
    assert not hasattr(server_mod, "_startup"), (
        "D-11 clean break: _startup must be removed with no backward-compat alias"
    )
    assert not hasattr(server_mod, "_shutdown"), (
        "D-11 clean break: _shutdown must be removed with no backward-compat alias"
    )


def test_startup_bridge_signature():
    """startup_bridge accepts server_url and client_name (both optional) (D-12)."""
    from forge_bridge.mcp.server import startup_bridge

    sig = inspect.signature(startup_bridge)
    params = list(sig.parameters)
    assert params == ["server_url", "client_name"]
    # Both must default to None per D-12
    assert sig.parameters["server_url"].default is None
    assert sig.parameters["client_name"].default is None


def test_shutdown_bridge_signature():
    """shutdown_bridge() takes no args (D-13)."""
    from forge_bridge.mcp.server import shutdown_bridge

    sig = inspect.signature(shutdown_bridge)
    assert len(sig.parameters) == 0, (
        f"shutdown_bridge must take no args per D-13; got {list(sig.parameters)}"
    )


@pytest.mark.asyncio
async def test_startup_bridge_injection(monkeypatch):
    """startup_bridge(server_url=...) uses injected URL over env (D-12)."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import forge_bridge.mcp.server as server_mod

    monkeypatch.setenv("FORGE_BRIDGE_URL", "ws://should-be-overridden:9998")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.wait_until_connected = AsyncMock()
    mock_client.stop = AsyncMock()

    with patch("forge_bridge.mcp.server.AsyncClient", return_value=mock_client) as mock_cls:
        try:
            await server_mod.startup_bridge(server_url="ws://injected:9998")
            ctor_kwargs = mock_cls.call_args.kwargs
            assert ctor_kwargs.get("server_url") == "ws://injected:9998", (
                f"Injected arg must beat env; got {ctor_kwargs.get('server_url')!r}"
            )
        finally:
            await server_mod.shutdown_bridge()  # cleanup


# ── API-05 / D-14, D-15 — Post-run guard + flag initialization ──────────────

def test_server_started_flag_default():
    """_server_started module-level flag initializes to False (D-14)."""
    import forge_bridge.mcp.server as server_mod
    # Importing the module fresh: flag must be False
    assert server_mod._server_started is False


# Note: the post-run guard behavior itself is tested in tests/test_mcp_registry.py
# (Plan 02 Task 2) — test_register_tools_post_run_guard and test_register_tools_pre_run_ok.
# Keeping those in test_mcp_registry.py per RESEARCH.md §Validation Architecture.


# ── PKG-02 / D-23 — Version pin ─────────────────────────────────────────────
# Phase 4 (D-23) pinned version = "1.0.0".
# Phase 5-00 v1.0.1 patch release bumps to "1.0.1" (protocol builders,
# ref_msg_id correlation fix, timeline gap-fill).
# Phase 6-03 v1.1.0 minor release bumps to "1.1.0" (LRN-02 storage callback +
# LRN-04 pre-synthesis hook additive API surface).

def test_package_version():
    """pyproject.toml version is 1.1.0 after Phase 6-03 v1.1.0 minor release."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'version = "1.1.0"' in content, (
        'pyproject.toml must declare version = "1.1.0" per Phase 6-03 v1.1.0 minor release.'
    )


# ── PKG-03 / D-10 + user resolution #1 — whole-package string scrub ────────

def test_no_forge_specific_strings():
    """ROADMAP success criterion #5: grep -r returns zero matches for forge-specific tokens.

    This is the standing regression guard — if anyone re-adds portofino, assist-01,
    or ACM_ to the forge_bridge/ package, this test fails at CI time.
    """
    root = Path(__file__).parent.parent / "forge_bridge"
    result = subprocess.run(
        ["grep", "-r", "-E", "portofino|assist-01|ACM_", str(root),
         "--include=*.py"],
        capture_output=True,
        text=True,
    )
    # grep returns 1 when no matches found — that's the success condition
    assert result.returncode == 1, (
        f"Found forge-specific strings in forge_bridge/:\n{result.stdout}\n"
        f"These tokens are banned per Phase 4 PKG-03 / user resolution #1."
    )


# ── Sanity: bridge module imports cleanly (catches D-17/D-18 class-construct bugs) ─

def test_bridge_module_imports_clean():
    """forge_bridge.bridge imports without side-effect errors after Phase 4 refactors.

    Catches any eager-init bug introduced by the D-17/D-18 SkillSynthesizer
    work or the D-11/D-14 server refactor.
    """
    import importlib
    import sys
    sys.modules.pop("forge_bridge.bridge", None)
    importlib.import_module("forge_bridge.bridge")  # must not raise


def test_synthesizer_module_level_synthesize_removed():
    """D-19 regression guard at the public-API layer: no module-level synthesize()."""
    from forge_bridge.learning import synthesizer
    assert not hasattr(synthesizer, "synthesize"), (
        "Module-level synthesize() must be removed per D-19. "
        "Use SkillSynthesizer().synthesize() instead."
    )
