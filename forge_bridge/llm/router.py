"""
forge_bridge.llm.router
-----------------------
Async LLM router for forge-bridge.

Routes LLM requests to local (Ollama on assist-01) or cloud (Anthropic Claude)
based on data sensitivity.

Sensitive data (shot names, client info, file paths, SQL, openclip XML) -> local
Architecture / design reasoning, non-sensitive -> cloud

Usage:
    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()

    # Sensitive -- stays on local network (async)
    result = await router.acomplete(
        "Write a regex to extract shot name from: ACM_0010_comp_v003",
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

# ---------------------------------------------------------------------------
# Endpoints & models
# ---------------------------------------------------------------------------

LOCAL_BASE_URL = os.environ.get("FORGE_LOCAL_LLM_URL", "http://assist-01:11434/v1")
LOCAL_MODEL    = os.environ.get("FORGE_LOCAL_MODEL",   "qwen2.5-coder:32b")
CLOUD_MODEL    = os.environ.get("FORGE_CLOUD_MODEL",   "claude-opus-4-6")

# Default system prompt injected into every local call.
# Keeps Flame/pipeline context in scope without repeating it per-call.
_DEFAULT_SYSTEM_PROMPT = """
You are a VFX pipeline assistant embedded in FORGE, a suite of Autodesk Flame
Python tools for shot management and publishing.

Key context:
- Flame version: 2026, Python API via `import flame`
- Shot naming convention: {project}_{shot}_{layer}_v{version}  e.g. ACM_0010_comp_v003
- Openclip files: XML-based multi-version containers written by Flame's MIO
  reader. Use Flame's native bracket notation [0991-1017] for frame ranges,
  NOT printf %04d notation.
- forge_bridge PostgreSQL on portofino: host=localhost port=7533 user=forge db=forge_bridge
- Desktop: Flame on portofino (MacBook Pro, macOS, Apple Silicon)
- Render: flame-01 (Threadripper, Linux, RTX A5000 Ada) via Backburner / cmdjob

Respond with concise, production-ready Python unless asked otherwise.
""".strip()

SYSTEM_PROMPT = os.environ.get("FORGE_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT)


class LLMRouter:
    """
    Two-tier async LLM router for FORGE pipeline tools.

    Tier 1 (sensitive=True, default):
        -> Ollama on assist-01 (local network, no data egress)
        -> Model: qwen2.5-coder:32b

    Tier 2 (sensitive=False):
        -> Anthropic Claude (cloud, non-sensitive queries only)
        -> Model: claude-opus-4-6

    Environment overrides:
        FORGE_LOCAL_LLM_URL    default: http://assist-01:11434/v1
        FORGE_LOCAL_MODEL      default: qwen2.5-coder:32b
        FORGE_CLOUD_MODEL      default: claude-opus-4-6
        FORGE_SYSTEM_PROMPT    default: built-in VFX pipeline prompt
        ANTHROPIC_API_KEY      required for cloud calls
    """

    def __init__(self):
        self._local_client: Optional["AsyncOpenAI"] = None  # type: ignore[name-defined]
        self._cloud_client: Optional["AsyncAnthropic"] = None  # type: ignore[name-defined]

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
            system:      Override system prompt. If None, uses SYSTEM_PROMPT
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
            "local_model": LOCAL_MODEL,
            "cloud_model": CLOUD_MODEL,
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
                base_url=LOCAL_BASE_URL,
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

    # ------------------------------------------------------------------
    # Internal async backend methods
    # ------------------------------------------------------------------

    async def _async_local(
        self, prompt: str, system: Optional[str], temperature: float
    ) -> str:
        client = self._get_local_client()
        sys_msg = system if system is not None else SYSTEM_PROMPT
        messages = []
        if sys_msg:
            messages.append({"role": "system", "content": sys_msg})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await client.chat.completions.create(
                model=LOCAL_MODEL,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Local LLM call failed ({LOCAL_BASE_URL}): {e}")

    async def _async_cloud(
        self, prompt: str, system: Optional[str], temperature: float
    ) -> str:
        client = self._get_cloud_client()
        sys_msg = system or "You are a VFX pipeline assistant."

        try:
            resp = await client.messages.create(
                model=CLOUD_MODEL,
                max_tokens=4096,
                system=sys_msg,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except Exception as e:
            raise RuntimeError(f"Cloud LLM call failed: {e}")


# ---------------------------------------------------------------------------
# Convenience singleton -- import and use directly in FORGE tools
# ---------------------------------------------------------------------------
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Return the shared LLMRouter singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
