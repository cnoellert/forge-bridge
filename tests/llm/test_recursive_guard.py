"""LLMTOOL-07: recursive-synthesis guard tests.

Belt-and-suspenders verification per CONTEXT.md <specifics> third bullet —
two layers tested here, third layer (process-level synthesizer quarantine)
ships in Phase 3 (already in production):

  Layer 1: Static AST check at synthesis time
           (forge_bridge/learning/synthesizer.py::_check_safety, D-14, plan 15-06 Task 2)
  Layer 2: Runtime ContextVar check at LLM-call time
           (forge_bridge/llm/router.py::_in_tool_loop + acomplete entry check,
            D-12/D-13, plan 15-06 Task 1)

Acceptance per LLMTOOL-07 verbatim: "a tool function that calls acomplete()
raises RecursiveToolLoopError when invoked from within complete_with_tools()."
This file proves both the static prevention path AND the runtime fallback path.
"""
from __future__ import annotations

import ast
import textwrap

import pytest

from forge_bridge.learning.synthesizer import _check_safety
from forge_bridge.llm.router import (
    LLMRouter,
    RecursiveToolLoopError,
    _in_tool_loop,
)


# ---------------------------------------------------------------------------
# Layer 1: Static AST guard (D-14)
# ---------------------------------------------------------------------------


class TestSafetyForgeBridgeLlmImport:
    """D-14: synthesizer._check_safety rejects any synthesized code that
    imports from forge_bridge.llm.* — the recursive-synthesis attack surface."""

    def test_rejects_from_forge_bridge_llm_router_import_LLMRouter(self):
        """The classic recursive-synthesis pattern from research §6.3."""
        code = textwrap.dedent("""
            from forge_bridge.llm.router import LLMRouter
            async def synth_recursive(prompt: str) -> str:
                router = LLMRouter()
                return await router.acomplete(prompt)
        """)
        tree = ast.parse(code)
        assert _check_safety(tree) is False, (
            "must reject `from forge_bridge.llm.router import LLMRouter`"
        )

    def test_rejects_from_forge_bridge_llm_import_router(self):
        code = textwrap.dedent("""
            from forge_bridge.llm import router
            async def synth_x(p: str) -> str:
                return await router.get_router().acomplete(p)
        """)
        assert _check_safety(ast.parse(code)) is False

    def test_rejects_import_forge_bridge_llm_router(self):
        code = textwrap.dedent("""
            import forge_bridge.llm.router
            async def synth_x(p: str) -> str:
                return await forge_bridge.llm.router.get_router().acomplete(p)
        """)
        assert _check_safety(ast.parse(code)) is False

    def test_rejects_import_forge_bridge_llm(self):
        code = textwrap.dedent("""
            import forge_bridge.llm
            async def synth_x(p: str) -> str:
                return p
        """)
        assert _check_safety(ast.parse(code)) is False

    def test_allows_forge_bridge_bridge_import(self):
        """Regression guard: the SUPPORTED synthesized-tool import pattern
        (forge_bridge.bridge.execute) must continue to work — D-14 only
        blocks the .llm subtree, not the .bridge subtree."""
        code = textwrap.dedent("""
            from forge_bridge.bridge import execute, execute_json
            async def synth_x(p: str) -> str:
                result = await execute("print('hello')")
                return result.stdout
        """)
        assert _check_safety(ast.parse(code)) is True, (
            "forge_bridge.bridge import must remain allowed — it's the "
            "supported synthesized-tool pattern (CLAUDE.md / SYNTH_PROMPT)"
        )

    def test_allows_bare_forge_bridge_import(self):
        """Bare prefix `import forge_bridge` is too broad to block."""
        code = textwrap.dedent("""
            import forge_bridge
            async def synth_x(p: str) -> str:
                return p
        """)
        assert _check_safety(ast.parse(code)) is True


# ---------------------------------------------------------------------------
# Layer 2: Runtime ContextVar guard (D-12/D-13)
# ---------------------------------------------------------------------------


class TestContextVarRuntimeGuard:
    """D-12/D-13: _in_tool_loop ContextVar set inside complete_with_tools()
    (Wave 3 plan 15-08); checked on entry to acomplete() (this plan Task 1)
    and complete_with_tools() (Wave 3 plan 15-08)."""

    def test_default_value_is_false(self):
        assert _in_tool_loop.get() is False, "ContextVar default must be False"

    async def test_acomplete_raises_when_contextvar_true(self):
        """LLMTOOL-07 acceptance: from within a tool-call loop (simulated by
        ContextVar=True), acomplete() raises RecursiveToolLoopError on entry
        BEFORE any provider call is made."""
        router = LLMRouter()
        token = _in_tool_loop.set(True)
        try:
            with pytest.raises(RecursiveToolLoopError) as exc_info:
                await router.acomplete("inner call")
            # Message identifies the cause for Phase 16 chat-endpoint mapping
            assert (
                "complete_with_tools" in str(exc_info.value)
                or "recursive" in str(exc_info.value).lower()
            )
        finally:
            _in_tool_loop.reset(token)

    async def test_acomplete_proceeds_after_contextvar_reset(self):
        """The try/finally pattern in complete_with_tools() (Wave 3 plan 15-08)
        depends on reset() restoring the prior False state. Verify here."""
        token = _in_tool_loop.set(True)
        _in_tool_loop.reset(token)
        # After reset, the check should NOT fire — but we don't have a real
        # backend so we can't actually call acomplete. We assert the value
        # is back to False, which is the precondition for normal operation.
        assert _in_tool_loop.get() is False, (
            "after reset, ContextVar must be back to default False; otherwise "
            "complete_with_tools() try/finally cleanup is broken"
        )


# ---------------------------------------------------------------------------
# Integration: belt-and-suspenders demonstration
# ---------------------------------------------------------------------------


class TestRecursiveSynthesisIntegration:
    """Demonstrates the layered defense — even if a tool author tries to
    write a recursive-synthesis tool body, the static AST check stops it
    BEFORE the runtime guard ever gets a chance to fire (LLMTOOL-07 acceptance
    verbatim from research §7)."""

    def test_synthesized_tool_with_recursive_llm_call_is_quarantined(self):
        """The full attack surface: a synthesized tool body that imports
        the LLMRouter and calls back into acomplete(). _check_safety must
        return False — Phase 3's quarantine path then blocks the file from
        landing in the registered tool surface (process-level safeguard,
        layer 3 — already shipped)."""
        evil_code = textwrap.dedent("""
            from forge_bridge.llm.router import LLMRouter

            async def synth_recursive_attack(prompt: str) -> str:
                \"\"\"Synthesizer tool body that tries to call back into the LLM.

                In production this would never reach _check_safety because the
                static blocklist rejects forge_bridge.llm imports. This test
                proves that path (layer 1 of the belt-and-suspenders defense).
                \"\"\"
                router = LLMRouter()
                return await router.acomplete(prompt)
        """)
        tree = ast.parse(evil_code)
        assert _check_safety(tree) is False, (
            "LLMTOOL-07 layer 1 (static AST check) MUST reject this body "
            "before it reaches the runtime ContextVar guard (layer 2). "
            "If this assertion fires, the recursive-synthesis attack surface "
            "is open — investigate D-14 / synthesizer._check_safety extension."
        )
