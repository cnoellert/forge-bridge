"""
forge_bridge.llm_router -- Backwards-compatible shim.

This module has been promoted to forge_bridge.llm.router.
Import from there for new code. This shim exists so that existing
code using `from forge_bridge.llm_router import LLMRouter` continues
to work.
"""
from forge_bridge.llm.router import LLMRouter, get_router

__all__ = ["LLMRouter", "get_router"]
