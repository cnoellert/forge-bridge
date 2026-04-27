"""
forge_bridge.llm.router
-----------------------
Async LLM router for forge-bridge.

Routes LLM requests to local Ollama or cloud Anthropic Claude
based on data sensitivity.

Sensitive data (shot names, client info, file paths, SQL, openclip XML) -> local
Architecture / design reasoning, non-sensitive -> cloud

Usage:
    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()

    # Sensitive -- stays on local network (async)
    result = await router.acomplete(
        "Write a regex to extract shot name from: PROJ_0010_comp_v003",
        sensitive=True
    )

    # Non-sensitive -- uses Claude (sync wrapper, outside async context only)
    design = router.complete(
        "What's the best pattern for async Flame export callbacks?",
        sensitive=False
    )
"""

import os
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

# Default system prompt injected into every local call.
# Keeps Flame/pipeline context in scope without repeating it per-call.
# Deployment-specific strings (hostnames, DB creds, machine specs) are excluded —
# callers that need them can pass system_prompt= to LLMRouter() or acomplete().
_DEFAULT_SYSTEM_PROMPT = """
You are a VFX pipeline assistant embedded in a toolkit of Autodesk Flame
Python tools for shot management and publishing.

Key context:
- Flame version: 2026, Python API via `import flame`
- Shot naming convention: {project}_{shot}_{layer}_v{version}  e.g. PROJ_0010_comp_v003
- Openclip files: XML-based multi-version containers written by Flame's MIO
  reader. Use Flame's native bracket notation [0991-1017] for frame ranges,
  NOT printf %04d notation.

Respond with concise, production-ready Python unless asked otherwise.
""".strip()


class LLMRouter:
    """
    Two-tier async LLM router for forge-bridge pipeline tools.

    Tier 1 (sensitive=True, default):
        -> local Ollama (local network, no data egress)
        -> Model: qwen2.5-coder:32b

    Tier 2 (sensitive=False):
        -> Anthropic Claude (cloud, non-sensitive queries only)
        -> Model: claude-opus-4-6

    Environment overrides:
        FORGE_LOCAL_LLM_URL    default: http://localhost:11434/v1
        FORGE_LOCAL_MODEL      default: qwen2.5-coder:32b
        FORGE_CLOUD_MODEL      default: claude-opus-4-6
        FORGE_SYSTEM_PROMPT    default: built-in VFX pipeline prompt
        ANTHROPIC_API_KEY      required for cloud calls

    Constructor kwargs override env vars, which override hardcoded defaults.
    Env reads happen at instance construction time, not at module import.
    """

    def __init__(
        self,
        local_url: str | None = None,
        local_model: str | None = None,
        cloud_model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.local_url = local_url or os.environ.get(
            "FORGE_LOCAL_LLM_URL", "http://localhost:11434/v1"
        )
        self.local_model = local_model or os.environ.get(
            "FORGE_LOCAL_MODEL", "qwen2.5-coder:32b"
        )
        self.cloud_model = cloud_model or os.environ.get(
            "FORGE_CLOUD_MODEL", "claude-opus-4-6"
        )
        self.system_prompt = system_prompt or os.environ.get(
            "FORGE_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT
        )
        self._local_client: Optional["AsyncOpenAI"] = None  # type: ignore[name-defined]
        self._cloud_client: Optional["AsyncAnthropic"] = None  # type: ignore[name-defined]
        # FB-C D-02: native ollama.AsyncClient slot for complete_with_tools().
        # The OpenAI-compat shim above (self._local_client) stays in place for
        # acomplete() — two clients in the router for two purposes per research §3.7.
        self._local_native_client: Optional["ollama.AsyncClient"] = None  # type: ignore[name-defined]

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def acomplete(
        self,
        prompt: str,
        sensitive: bool = True,
        system: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Generate a completion asynchronously.

        Args:
            prompt:      The user message / task description.
            sensitive:   True (default) -> local model (no data egress).
                         False -> Claude cloud.
            system:      Override system prompt. If None, uses self.system_prompt
                         for local calls, minimal prompt for cloud calls.
            temperature: Sampling temperature. Default 0.1 for deterministic
                         pipeline code generation.

        Returns:
            Model response string.

        Raises:
            RuntimeError: If the selected backend is unavailable.
        """
        if sensitive:
            return await self._async_local(prompt, system, temperature)
        return await self._async_cloud(prompt, system, temperature)

    def complete(self, prompt: str, **kwargs) -> str:
        """
        Sync convenience wrapper around acomplete().

        Do NOT call from inside an async context (e.g., MCP tool handlers).
        Use acomplete() directly instead. This wrapper uses asyncio.run() which
        creates its own event loop — it will raise RuntimeError if called from
        within a running event loop.

        Args:
            prompt: The user message / task description.
            **kwargs: Passed through to acomplete() (sensitive, system, temperature).

        Returns:
            Model response string.
        """
        return asyncio.run(self.acomplete(prompt, **kwargs))

    async def ahealth_check(self) -> dict:
        """
        Check availability of both backends asynchronously.

        Returns:
            dict with keys: local (bool), cloud (bool), local_model, cloud_model,
            and optional local_error / cloud_error strings.
        """
        status = {
            "local": False,
            "cloud": False,
            "local_model": self.local_model,
            "cloud_model": self.cloud_model,
        }
        try:
            client = self._get_local_client()
            await client.models.list()
            status["local"] = True
        except Exception as e:
            logger.warning(f"Local LLM unavailable: {e}")
            status["local_error"] = str(e)
        try:
            import anthropic as _anthropic  # noqa: F401
            status["cloud"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
        except ImportError:
            status["cloud_error"] = "anthropic not installed"
        return status

    def health_check(self) -> dict:
        """Sync convenience wrapper around ahealth_check(). See ahealth_check() for details."""
        return asyncio.run(self.ahealth_check())

    # ------------------------------------------------------------------
    # Internal client accessors (lazy import guards)
    # ------------------------------------------------------------------

    def _get_local_client(self):
        if self._local_client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. "
                    "Install LLM support: pip install forge-bridge[llm]"
                )
            self._local_client = AsyncOpenAI(
                base_url=self.local_url,
                api_key="ollama",  # Ollama ignores the key but AsyncOpenAI client requires one
            )
        return self._local_client

    def _get_cloud_client(self):
        if self._cloud_client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. "
                    "Install LLM support: pip install forge-bridge[llm]"
                )
            self._cloud_client = AsyncAnthropic()
        return self._cloud_client

    def _get_local_native_client(self):
        """Return the native ollama.AsyncClient (D-02), lazy-instantiated.

        Used by complete_with_tools() for the local/sensitive tool-call path.
        Distinct from _get_local_client() (OpenAI-compat shim, used by acomplete()):
          - acomplete() uses the shim because the wire format is identical for
            plain completions and the existing tests / pin (openai>=1.0) cover it.
          - complete_with_tools() uses the native client because the OpenAI shim
            drops tool_calls.function.arguments parsing quirks, hides
            message.thinking, and silently coerces error types (research §3.7).

        The native client takes host without the OpenAI /v1 suffix; we strip it
        from self.local_url if present (default self.local_url is
        "http://localhost:11434/v1" and the daemon is at "http://localhost:11434").
        """
        if self._local_native_client is None:
            try:
                from ollama import AsyncClient
            except ImportError:
                raise RuntimeError(
                    "ollama package not installed. "
                    "Install LLM support: pip install forge-bridge[llm]"
                )
            host = self.local_url
            if host.endswith("/v1"):
                host = host[:-3]
            self._local_native_client = AsyncClient(host=host)
        return self._local_native_client

    # ------------------------------------------------------------------
    # Internal async backend methods
    # ------------------------------------------------------------------

    async def _async_local(
        self, prompt: str, system: Optional[str], temperature: float
    ) -> str:
        client = self._get_local_client()
        sys_msg = system if system is not None else self.system_prompt
        messages = []
        if sys_msg:
            messages.append({"role": "system", "content": sys_msg})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await client.chat.completions.create(
                model=self.local_model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Local LLM call failed ({self.local_url}): {e}")

    async def _async_cloud(
        self, prompt: str, system: Optional[str], temperature: float
    ) -> str:
        client = self._get_cloud_client()
        sys_msg = system or "You are a VFX pipeline assistant."

        try:
            resp = await client.messages.create(
                model=self.cloud_model,
                max_tokens=4096,
                system=sys_msg,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except Exception as e:
            raise RuntimeError(f"Cloud LLM call failed: {e}")


# ---------------------------------------------------------------------------
# Convenience singleton -- import and use directly in forge-bridge tools
# ---------------------------------------------------------------------------
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Return the shared LLMRouter singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
