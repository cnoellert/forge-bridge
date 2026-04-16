"""
Wave 0 test scaffolds for Phase 1 LLM Router requirements (LLM-01 through LLM-08).

Tests marked @pytest.mark.skip are stubs to be unskipped as implementation lands.
test_llm_shim_import is not skipped — it verifies the backwards-compat shim in
forge_bridge/llm_router.py which already exists.

Requirements covered:
    LLM-01  forge_bridge.llm.router.LLMRouter class exists, importable
    LLM-02  LLMRouter.acomplete is an async coroutine
    LLM-03  LLMRouter.complete is a sync wrapper (not a coroutine)
    LLM-04  Router reads env vars: FORGE_LOCAL_LLM_URL, FORGE_LOCAL_MODEL,
                                   FORGE_CLOUD_MODEL, FORGE_SYSTEM_PROMPT
    LLM-05  Importing forge_bridge.llm.router does NOT fail without openai/anthropic
    LLM-06  ahealth_check() returns dict with keys local, cloud, local_model, cloud_model
    LLM-07  register_llm_resources(mcp) registers resource at forge://llm/health
    LLM-08  forge_bridge.llm_router shim provides LLMRouter and get_router (backwards compat)
"""

import pytest


# ── LLM-01 — Package structure and importability ─────────────────────────────

def test_llm_package_structure():
    """forge_bridge.llm.router must export LLMRouter and get_router."""
    from forge_bridge.llm.router import LLMRouter, get_router

    assert callable(LLMRouter), "LLMRouter must be callable (class)"
    assert callable(get_router), "get_router must be callable"


# ── LLM-02 — acomplete is async ───────────────────────────────────────────────

def test_acomplete_is_coroutine():
    """LLMRouter.acomplete must be an async coroutine function."""
    import asyncio

    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()
    assert asyncio.iscoroutinefunction(router.acomplete), \
        "LLMRouter.acomplete must be declared with 'async def'"


# ── LLM-03 — complete is sync ─────────────────────────────────────────────────

def test_complete_sync_wrapper():
    """LLMRouter.complete must exist and must NOT be a coroutine function."""
    import asyncio

    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()
    assert hasattr(router, "complete"), "LLMRouter must have a complete() method"
    assert not asyncio.iscoroutinefunction(router.complete), \
        "LLMRouter.complete must be synchronous (not async)"


# ── LLM-04 — Env var overrides and injected config ───────────────────────────


def test_env_fallback_at_init_time(monkeypatch):
    """LLMRouter() reads env vars inside __init__, not at module import time."""
    monkeypatch.setenv("FORGE_LOCAL_LLM_URL", "http://test-host:11434/v1")
    monkeypatch.setenv("FORGE_LOCAL_MODEL", "test-local-model")
    monkeypatch.setenv("FORGE_CLOUD_MODEL", "test-cloud-model")
    monkeypatch.setenv("FORGE_SYSTEM_PROMPT", "Custom system prompt")

    from forge_bridge.llm.router import LLMRouter
    router = LLMRouter()
    assert router.local_url == "http://test-host:11434/v1"
    assert router.local_model == "test-local-model"
    assert router.cloud_model == "test-cloud-model"
    assert router.system_prompt == "Custom system prompt"


def test_injected_arg_beats_env(monkeypatch):
    """Explicit __init__ arg wins over env var (D-06 precedence)."""
    monkeypatch.setenv("FORGE_LOCAL_LLM_URL", "http://env-value:11434/v1")
    from forge_bridge.llm.router import LLMRouter
    router = LLMRouter(local_url="http://injected:11434/v1")
    assert router.local_url == "http://injected:11434/v1"


def test_default_fallback(monkeypatch):
    """LLMRouter() with no args and no env uses hardcoded defaults."""
    for key in ("FORGE_LOCAL_LLM_URL", "FORGE_LOCAL_MODEL",
                "FORGE_CLOUD_MODEL", "FORGE_SYSTEM_PROMPT"):
        monkeypatch.delenv(key, raising=False)
    from forge_bridge.llm.router import LLMRouter
    router = LLMRouter()
    assert router.local_url == "http://localhost:11434/v1"
    assert router.local_model == "qwen2.5-coder:32b"
    assert router.cloud_model == "claude-opus-4-6"
    assert "Flame" in router.system_prompt  # generic prompt intact


def test_router_accepts_injected_config():
    """All four kwargs accepted and wired to instance attributes (D-05)."""
    from forge_bridge.llm.router import LLMRouter
    router = LLMRouter(
        local_url="http://x:11434",
        local_model="m1",
        cloud_model="m2",
        system_prompt="custom",
    )
    assert router.local_url == "http://x:11434"
    assert router.local_model == "m1"
    assert router.cloud_model == "m2"
    assert router.system_prompt == "custom"


def test_default_prompt_has_generic_flame_context(monkeypatch):
    """Default system prompt keeps Flame markers, drops forge-specific strings."""
    for key in ("FORGE_LOCAL_LLM_URL", "FORGE_LOCAL_MODEL",
                "FORGE_CLOUD_MODEL", "FORGE_SYSTEM_PROMPT"):
        monkeypatch.delenv(key, raising=False)
    from forge_bridge.llm.router import LLMRouter
    prompt = LLMRouter().system_prompt
    # Keeps
    assert "Flame" in prompt
    assert "import flame" in prompt
    assert "{project}_{shot}_{layer}_v{version}" in prompt
    assert "[0991-1017]" in prompt
    # Purges
    for token in ("portofino", "assist-01", "ACM_", "flame-01",
                  "Backburner", "cmdjob"):
        assert token not in prompt, f"Default prompt still contains {token!r}"


# ── LLM-05 — Optional import guard ───────────────────────────────────────────

def test_optional_import_guard():
    """Importing forge_bridge.llm.router must NOT raise ImportError even without
    openai or anthropic installed at module level.

    Both openai and anthropic must be imported lazily (inside functions/methods).
    """
    import importlib
    import sys

    # Temporarily hide openai and anthropic from the import system
    saved = {}
    for pkg in ("openai", "anthropic"):
        if pkg in sys.modules:
            saved[pkg] = sys.modules.pop(pkg)
        sys.modules[pkg] = None  # type: ignore[assignment]  # blocks import

    try:
        if "forge_bridge.llm.router" in sys.modules:
            del sys.modules["forge_bridge.llm.router"]
        importlib.import_module("forge_bridge.llm.router")  # Must not raise
    except ImportError as e:
        pytest.fail(
            f"forge_bridge.llm.router raised ImportError without openai/anthropic: {e}"
        )
    finally:
        for pkg in ("openai", "anthropic"):
            if pkg in saved:
                sys.modules[pkg] = saved[pkg]
            else:
                sys.modules.pop(pkg, None)


# ── LLM-06 — ahealth_check shape ─────────────────────────────────────────────

async def test_health_check_shape():
    """ahealth_check() must return a dict with keys: local, cloud, local_model, cloud_model."""
    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()
    result = await router.ahealth_check()

    assert isinstance(result, dict), "ahealth_check() must return a dict"
    for key in ("local", "cloud", "local_model", "cloud_model"):
        assert key in result, f"ahealth_check() result missing key: {key!r}"


# ── LLM-07 — MCP resource registration ───────────────────────────────────────

def test_health_resource_registered():
    """register_llm_resources(mcp) must register a resource at forge://llm/health."""
    from unittest.mock import MagicMock

    from forge_bridge.llm.health import register_llm_resources

    mock_mcp = MagicMock()
    register_llm_resources(mock_mcp)

    # Expect mock_mcp.resource to have been called with "forge://llm/health"
    registered_uris = [
        call.args[0]
        for call in mock_mcp.resource.call_args_list
    ]
    assert "forge://llm/health" in registered_uris, (
        f"register_llm_resources did not register forge://llm/health. "
        f"Registered: {registered_uris}"
    )


# ── LLM-08 — Backwards-compat shim ───────────────────────────────────────────

def test_llm_shim_import():
    """forge_bridge.llm_router shim must export LLMRouter and get_router.

    This is the backwards-compat import path that existed before the llm/ subpackage
    was created. The shim at forge_bridge/llm_router.py must remain importable.
    """
    from forge_bridge.llm_router import LLMRouter, get_router

    assert callable(LLMRouter), "forge_bridge.llm_router.LLMRouter must be callable"
    assert callable(get_router), "forge_bridge.llm_router.get_router must be callable"
