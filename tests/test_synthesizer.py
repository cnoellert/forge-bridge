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
