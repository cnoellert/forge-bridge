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

    # Save and restore forge_bridge.llm.router so the module-level _router singleton
    # is not replaced by a fresh module object after reimport. Without this, any
    # consumer that imported get_router from the original module object (e.g. the
    # synthesizer) and any new import of forge_bridge.llm.router would refer to
    # different module objects, breaking singleton identity.
    saved_router_mod = sys.modules.get("forge_bridge.llm.router")

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
        # Restore the original module object to avoid breaking singleton identity
        if saved_router_mod is not None:
            sys.modules["forge_bridge.llm.router"] = saved_router_mod
        else:
            sys.modules.pop("forge_bridge.llm.router", None)


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


# ── FB-C D-02 (LLMTOOL-01 prereq) — _get_local_native_client lazy slot ───────

def test_local_native_client_slot_initialized_to_none():
    """LLMRouter() must initialize _local_native_client lazy slot to None.

    Mirrors the existing _local_client / _cloud_client lazy-slot pattern
    (router.py:98-99) so complete_with_tools() ships with a clean cached slot
    on every fresh instance.
    """
    from forge_bridge.llm.router import LLMRouter

    r = LLMRouter()
    assert hasattr(r, "_local_native_client"), \
        "LLMRouter must declare _local_native_client lazy slot in __init__"
    assert r._local_native_client is None, \
        "_local_native_client must initialize to None (uninstantiated)"


def test_get_local_native_client_method_exists():
    """LLMRouter._get_local_native_client must exist as a bound method."""
    from forge_bridge.llm.router import LLMRouter

    r = LLMRouter()
    assert hasattr(r, "_get_local_native_client"), \
        "LLMRouter must define _get_local_native_client (D-02 lazy accessor)"
    assert callable(r._get_local_native_client), \
        "_get_local_native_client must be callable"


def test_get_local_native_client_lazy_caches_returned_instance():
    """Two consecutive calls to _get_local_native_client must return the SAME
    object — the slot is lazy-instantiated once and cached, mirroring
    _get_cloud_client's pattern.
    """
    from unittest.mock import MagicMock, patch

    from forge_bridge.llm.router import LLMRouter

    r = LLMRouter()
    mock_ollama = MagicMock()
    mock_client_instance = MagicMock()
    mock_ollama.AsyncClient.return_value = mock_client_instance
    with patch.dict("sys.modules", {"ollama": mock_ollama}):
        c1 = r._get_local_native_client()
        c2 = r._get_local_native_client()
    assert c1 is c2, \
        "lazy caching broken — two calls returned different objects"
    assert mock_ollama.AsyncClient.call_count == 1, \
        "AsyncClient must be instantiated exactly once across repeated calls"


def test_get_local_native_client_strips_v1_suffix_from_host():
    """The native ollama client takes host without /v1 suffix; the router stores
    self.local_url with the OpenAI-compat /v1 suffix (default
    http://localhost:11434/v1) for acomplete(), so _get_local_native_client must
    strip /v1 before passing to ollama.AsyncClient(host=...).
    """
    from unittest.mock import MagicMock, patch

    from forge_bridge.llm.router import LLMRouter

    r = LLMRouter()  # default local_url = http://localhost:11434/v1
    assert r.local_url.endswith("/v1"), \
        "test precondition: default local_url must keep /v1 OpenAI-compat suffix"

    mock_ollama = MagicMock()
    with patch.dict("sys.modules", {"ollama": mock_ollama}):
        r._get_local_native_client()

    call_kwargs = mock_ollama.AsyncClient.call_args.kwargs
    host = call_kwargs.get("host")
    assert host == "http://localhost:11434", \
        f"host must drop /v1 (got {host!r}); native daemon endpoint, not OpenAI shim"


def test_get_local_native_client_handles_host_without_v1_suffix():
    """If the user supplies a local_url without the /v1 suffix already, the
    method must pass it through unchanged (idempotent strip)."""
    from unittest.mock import MagicMock, patch

    from forge_bridge.llm.router import LLMRouter

    r = LLMRouter(local_url="http://localhost:11434")
    mock_ollama = MagicMock()
    with patch.dict("sys.modules", {"ollama": mock_ollama}):
        r._get_local_native_client()

    call_kwargs = mock_ollama.AsyncClient.call_args.kwargs
    assert call_kwargs.get("host") == "http://localhost:11434", \
        "no-/v1 host must pass through unchanged"


def test_get_local_native_client_raises_runtimeerror_when_ollama_missing():
    """When the ollama package is not importable, _get_local_native_client must
    raise RuntimeError whose message contains the standard install hint
    'pip install forge-bridge[llm]' — verbatim mirror of _get_cloud_client's
    error path so the UX of the install-extras hint is preserved across all
    three lazy-import sites.
    """
    import importlib
    import sys

    from forge_bridge.llm.router import LLMRouter

    r = LLMRouter()
    saved = sys.modules.pop("ollama", None)
    sys.modules["ollama"] = None  # type: ignore[assignment]  # forces ImportError on next import
    try:
        with pytest.raises(RuntimeError) as exc_info:
            r._get_local_native_client()
        msg = str(exc_info.value)
        assert "pip install forge-bridge[llm]" in msg, \
            f"RuntimeError must carry the install hint; got: {msg!r}"
        assert "ollama" in msg.lower(), \
            f"RuntimeError must mention the missing package name; got: {msg!r}"
    finally:
        if saved is not None:
            sys.modules["ollama"] = saved
        else:
            sys.modules.pop("ollama", None)
        # Re-import in case any consumer cached a None-bound module reference.
        if "ollama" in sys.modules and sys.modules["ollama"] is None:
            sys.modules.pop("ollama", None)
        importlib.invalidate_caches()


def test_existing_local_and_cloud_accessors_unchanged():
    """The new _get_local_native_client lazy slot must not regress the existing
    _get_local_client (OpenAI shim) or _get_cloud_client (AsyncAnthropic) lazy
    accessors. acomplete() continues to consume _get_local_client; this plan
    only ADDS the third slot."""
    from unittest.mock import MagicMock, patch

    from forge_bridge.llm.router import LLMRouter

    r = LLMRouter()
    # Existing lazy slots still exist and start as None.
    assert r._local_client is None
    assert r._cloud_client is None

    # _get_local_client still wires AsyncOpenAI.
    mock_openai = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai}):
        r._get_local_client()
    assert mock_openai.AsyncOpenAI.called, \
        "_get_local_client must still call openai.AsyncOpenAI (regression)"

    # _get_cloud_client still wires AsyncAnthropic.
    r2 = LLMRouter()
    mock_anthropic = MagicMock()
    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        r2._get_cloud_client()
    assert mock_anthropic.AsyncAnthropic.called, \
        "_get_cloud_client must still call anthropic.AsyncAnthropic (regression)"
