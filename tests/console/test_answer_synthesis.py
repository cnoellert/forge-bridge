from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from forge_bridge.console import _answer
from forge_bridge.console._answer import (
    _SYNTHESIS_SYSTEM,
    _build_synthesis_prompt,
    _synthesize_answer,
)


def test_build_synthesis_prompt_uses_last_user_and_chain_entries():
    prompt = _build_synthesis_prompt(
        [
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": "what shots are in molecule?"},
        ],
        [{"step": "forge_list_shots sequence=molecule", "result": {
            "shots": ["010", "020"],
        }}],
    )

    assert "what shots are in molecule?" in prompt
    assert "old question" not in prompt
    assert "- forge_list_shots sequence=molecule" in prompt
    assert '{"shots":["010","020"]}' in prompt


@pytest.mark.asyncio
async def test_synthesize_answer_calls_acomplete_with_locked_system_prompt():
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value="  Molecule has shots 010 and 020.  ")
    )

    answer, elapsed_ms = await _synthesize_answer(
        router,
        [{"role": "user", "content": "what shots?"}],
        [{"step": "forge_list_shots", "result": {"shots": ["010", "020"]}}],
    )

    assert answer == "Molecule has shots 010 and 020."
    assert elapsed_ms >= 0
    router.acomplete.assert_awaited_once()
    args, kwargs = router.acomplete.await_args
    assert "forge_list_shots" in args[0]
    assert kwargs == {
        "sensitive": True,
        "system": _SYNTHESIS_SYSTEM,
        "temperature": 0.1,
    }


@pytest.mark.asyncio
async def test_synthesize_answer_swallows_exceptions():
    router = SimpleNamespace(acomplete=AsyncMock(side_effect=RuntimeError("down")))

    answer, elapsed_ms = await _synthesize_answer(
        router,
        [{"role": "user", "content": "what shots?"}],
        [{"step": "forge_list_shots", "result": {"shots": []}}],
    )

    assert answer == ""
    assert elapsed_ms >= 0


@pytest.mark.asyncio
async def test_synthesize_answer_bounds_hung_model(monkeypatch):
    async def _sleep_forever(*_args, **_kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(_answer, "_SYNTHESIS_TIMEOUT_S", 0.01)
    router = SimpleNamespace(acomplete=_sleep_forever)

    answer, elapsed_ms = await _synthesize_answer(
        router,
        [{"role": "user", "content": "what shots?"}],
        [{"step": "forge_list_shots", "result": {"shots": []}}],
    )

    assert answer == ""
    assert elapsed_ms < 1000
