"""Tests for forge_bridge.learning.synthesizer."""
from __future__ import annotations

import ast
import hashlib
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SYNTH_CODE = textwrap.dedent('''\
    async def synth_get_shot_name(clip_name: str) -> str:
        """Extract shot name from a Flame clip name."""
        from forge_bridge.bridge import execute_and_read
        result = await execute_and_read(f"print('{clip_name}'.split('_')[1])")
        return result
''')

VALID_SYNTH_CODE_NO_FENCE = VALID_SYNTH_CODE

VALID_SYNTH_CODE_FENCED = f"```python\n{VALID_SYNTH_CODE}```"

SYNC_FUNCTION_CODE = textwrap.dedent('''\
    def synth_not_async(name: str) -> str:
        """Not async."""
        return name
''')

NO_SYNTH_PREFIX_CODE = textwrap.dedent('''\
    async def get_shot_name(clip_name: str) -> str:
        """Missing synth_ prefix."""
        return clip_name
''')

NO_RETURN_ANNOTATION_CODE = textwrap.dedent('''\
    async def synth_no_return(clip_name: str):
        """Missing return annotation."""
        return clip_name
''')

NO_DOCSTRING_CODE = textwrap.dedent('''\
    async def synth_no_docs(clip_name: str) -> str:
        return clip_name
''')

MULTIPLE_FUNCTIONS_CODE = textwrap.dedent('''\
    async def synth_one(a: str) -> str:
        """First."""
        return a

    async def synth_two(b: str) -> str:
        """Second."""
        return b
''')

RAISING_FUNCTION_CODE = textwrap.dedent('''\
    async def synth_raises(name: str) -> str:
        """This raises."""
        raise ValueError("boom")
''')


# ---------------------------------------------------------------------------
# _extract_function tests
# ---------------------------------------------------------------------------

class TestExtractFunction:
    def test_strips_markdown_fences(self):
        from forge_bridge.learning.synthesizer import _extract_function
        result = _extract_function(VALID_SYNTH_CODE_FENCED)
        assert "```" not in result
        assert "async def synth_get_shot_name" in result

    def test_returns_raw_if_no_fences(self):
        from forge_bridge.learning.synthesizer import _extract_function
        result = _extract_function(VALID_SYNTH_CODE_NO_FENCE)
        assert "async def synth_get_shot_name" in result


# ---------------------------------------------------------------------------
# _check_signature tests
# ---------------------------------------------------------------------------

class TestCheckSignature:
    def test_valid_function_returns_name(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(VALID_SYNTH_CODE)
        assert _check_signature(tree) == "synth_get_shot_name"

    def test_rejects_sync_function(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(SYNC_FUNCTION_CODE)
        assert _check_signature(tree) is None

    def test_rejects_no_synth_prefix(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(NO_SYNTH_PREFIX_CODE)
        assert _check_signature(tree) is None

    def test_rejects_no_return_annotation(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(NO_RETURN_ANNOTATION_CODE)
        assert _check_signature(tree) is None

    def test_rejects_no_docstring(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(NO_DOCSTRING_CODE)
        assert _check_signature(tree) is None

    def test_rejects_multiple_functions(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(MULTIPLE_FUNCTIONS_CODE)
        assert _check_signature(tree) is None


# ---------------------------------------------------------------------------
# _dry_run tests
# ---------------------------------------------------------------------------

class TestDryRun:
    @pytest.mark.asyncio
    async def test_valid_function_passes(self):
        from forge_bridge.learning.synthesizer import _dry_run
        result = await _dry_run(VALID_SYNTH_CODE, "synth_get_shot_name")
        assert result is True

    @pytest.mark.asyncio
    async def test_raising_function_fails(self):
        from forge_bridge.learning.synthesizer import _dry_run
        result = await _dry_run(RAISING_FUNCTION_CODE, "synth_raises")
        assert result is False


# ---------------------------------------------------------------------------
# SkillSynthesizer tests
# ---------------------------------------------------------------------------

class TestSkillSynthesizer:
    @pytest.mark.asyncio
    async def test_returns_path_on_valid_llm_output(self, tmp_path):
        from forge_bridge.learning.synthesizer import SkillSynthesizer

        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)

        synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
        result = await synth.synthesize("some code", "get shot name", 5)

        assert result is not None
        assert result.exists()
        assert result.name == "synth_get_shot_name.py"

    @pytest.mark.asyncio
    async def test_returns_none_on_syntax_error(self, tmp_path):
        from forge_bridge.learning.synthesizer import SkillSynthesizer
        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(return_value="def this is not valid python(")
        synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
        result = await synth.synthesize("some code", "intent", 3)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_llm_unavailable(self, tmp_path):
        from forge_bridge.learning.synthesizer import SkillSynthesizer
        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
        result = await synth.synthesize("some code", "intent", 3)
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_identical_existing_file(self, tmp_path):
        from forge_bridge.learning.synthesizer import SkillSynthesizer
        out = tmp_path / "synth_get_shot_name.py"
        out.write_text(VALID_SYNTH_CODE.strip())
        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)
        synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
        result = await synth.synthesize("some code", "intent", 3)
        assert result == out

    @pytest.mark.asyncio
    async def test_rejects_collision_different_content(self, tmp_path):
        from forge_bridge.learning.synthesizer import SkillSynthesizer
        out = tmp_path / "synth_get_shot_name.py"
        out.write_text("# different content\n")
        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)
        synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
        result = await synth.synthesize("some code", "intent", 3)
        assert result is None

    @pytest.mark.asyncio
    async def test_calls_router_with_sensitive_true(self, tmp_path):
        from forge_bridge.learning.synthesizer import SkillSynthesizer
        mock_router = MagicMock()
        mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)
        synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
        await synth.synthesize("some code", "intent", 3)
        mock_router.acomplete.assert_called_once()
        call_kwargs = mock_router.acomplete.call_args
        assert call_kwargs.kwargs.get("sensitive") is True or call_kwargs[1].get("sensitive") is True

    def test_router_injection(self):
        """D-17: router kwarg stored on self; None falls back to get_router()."""
        from forge_bridge.learning.synthesizer import SkillSynthesizer
        mock_router = MagicMock()
        synth = SkillSynthesizer(router=mock_router)
        assert synth._router is mock_router

        # Default path: None falls back to get_router()
        from forge_bridge.llm.router import get_router
        synth2 = SkillSynthesizer()
        assert synth2._router is get_router()

    def test_synth_dir_injection(self, tmp_path):
        """D-17: synthesized_dir kwarg stored on self; None falls back to SYNTHESIZED_DIR."""
        from forge_bridge.learning.synthesizer import SkillSynthesizer, SYNTHESIZED_DIR
        synth = SkillSynthesizer(synthesized_dir=tmp_path)
        assert synth._synthesized_dir == tmp_path

        synth_default = SkillSynthesizer()
        assert synth_default._synthesized_dir is SYNTHESIZED_DIR


# ---------------------------------------------------------------------------
# D-19 regression guard: module-level synthesize() must be gone
# ---------------------------------------------------------------------------

def test_module_level_synthesize_removed():
    """D-19: module-level async def synthesize(...) is removed (no backward-compat alias)."""
    from forge_bridge.learning import synthesizer
    assert not hasattr(synthesizer, "synthesize"), (
        "Module-level synthesize() must be removed per D-19 clean-break. "
        "If present, SkillSynthesizer.synthesize is the replacement."
    )


# ---------------------------------------------------------------------------
# Path contract test
# ---------------------------------------------------------------------------

class TestPathContract:
    def test_synthesized_dir_is_same_object_as_watcher(self):
        from forge_bridge.learning.synthesizer import SYNTHESIZED_DIR as synth_dir
        from forge_bridge.learning.watcher import SYNTHESIZED_DIR as watch_dir
        assert synth_dir is watch_dir


# ---------------------------------------------------------------------------
# pre_synthesis_hook tests (LRN-04)
# ---------------------------------------------------------------------------


def _make_router_mock(return_text: str = VALID_SYNTH_CODE) -> MagicMock:
    """Return a MagicMock standing in for LLMRouter with async acomplete."""
    router = MagicMock()
    router.acomplete = AsyncMock(return_value=return_text)
    return router


class TestPreSynthesisHook:
    async def test_pre_synthesis_hook_invoked_with_intent_and_params(self, tmp_path):
        """Hook is awaited once with (intent, {raw_code, count}) per D-09."""
        from forge_bridge.learning.synthesizer import (
            PreSynthesisContext,
            SkillSynthesizer,
        )

        hook = AsyncMock(return_value=PreSynthesisContext())
        router = _make_router_mock()
        synth = SkillSynthesizer(
            router=router,
            synthesized_dir=tmp_path,
            pre_synthesis_hook=hook,
        )

        await synth.synthesize(
            raw_code="seg.name = 'ACM_0010'",
            intent="rename segment",
            count=3,
        )

        assert hook.await_count == 1
        args, _kwargs = hook.await_args
        assert args[0] == "rename segment"
        assert isinstance(args[1], dict)
        assert args[1]["raw_code"] == "seg.name = 'ACM_0010'"
        assert args[1]["count"] == 3

    async def test_pre_synthesis_hook_none_is_noop(self, tmp_path):
        """Synthesizer with pre_synthesis_hook=None behaves exactly as pre-LRN-04."""
        from forge_bridge.learning.synthesizer import SYNTH_SYSTEM, SkillSynthesizer

        router = _make_router_mock()
        synth = SkillSynthesizer(router=router, synthesized_dir=tmp_path)

        out = await synth.synthesize(raw_code="x = 1", intent=None, count=3)

        assert out is not None
        # The system prompt passed to acomplete must equal SYNTH_SYSTEM verbatim.
        _args, kwargs = router.acomplete.await_args
        assert kwargs["system"] == SYNTH_SYSTEM

    async def test_pre_synthesis_context_extra_context_appended_to_system(
        self, tmp_path
    ):
        """ctx.extra_context is appended to the system prompt (D-11 additive)."""
        from forge_bridge.learning.synthesizer import (
            PreSynthesisContext,
            SkillSynthesizer,
        )

        async def hook(_intent, _params):
            return PreSynthesisContext(extra_context="XTRA_MARKER_STRING")

        router = _make_router_mock()
        synth = SkillSynthesizer(
            router=router,
            synthesized_dir=tmp_path,
            pre_synthesis_hook=hook,
        )

        await synth.synthesize(raw_code="x = 1", intent="t", count=3)

        _args, kwargs = router.acomplete.await_args
        assert "XTRA_MARKER_STRING" in kwargs["system"]

    async def test_pre_synthesis_context_constraints_injected(self, tmp_path):
        """ctx.constraints render as a 'Constraints:' block in the system prompt."""
        from forge_bridge.learning.synthesizer import (
            PreSynthesisContext,
            SkillSynthesizer,
        )

        async def hook(_intent, _params):
            return PreSynthesisContext(constraints=["do not import flame"])

        router = _make_router_mock()
        synth = SkillSynthesizer(
            router=router,
            synthesized_dir=tmp_path,
            pre_synthesis_hook=hook,
        )

        await synth.synthesize(raw_code="x = 1", intent="t", count=3)

        _args, kwargs = router.acomplete.await_args
        assert "Constraints:" in kwargs["system"]
        assert "- do not import flame" in kwargs["system"]

    async def test_pre_synthesis_hook_exception_falls_back_to_empty_context(
        self, tmp_path, caplog
    ):
        """When the hook raises, synthesis continues with default PreSynthesisContext()."""
        import logging

        from forge_bridge.learning.synthesizer import SYNTH_SYSTEM, SkillSynthesizer

        async def hook(_intent, _params):
            raise RuntimeError("db offline")

        router = _make_router_mock()
        synth = SkillSynthesizer(
            router=router,
            synthesized_dir=tmp_path,
            pre_synthesis_hook=hook,
        )

        with caplog.at_level(logging.WARNING, logger="forge_bridge.learning.synthesizer"):
            out = await synth.synthesize(raw_code="x = 1", intent="t", count=3)

        # Synthesis still completed.
        assert out is not None
        # System prompt fell back to SYNTH_SYSTEM verbatim (no Constraints block).
        _args, kwargs = router.acomplete.await_args
        assert kwargs["system"] == SYNTH_SYSTEM
        assert "Constraints:" not in kwargs["system"]
        # Fallback warning logged.
        assert any(
            "pre_synthesis_hook raised" in rec.message for rec in caplog.records
        )
