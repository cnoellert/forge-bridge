from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from forge_bridge.orchestration.generation_runner import (
    GenerationRunnerUnavailable,
    build_generation_runner,
)


@dataclass
class _Driver:
    provider: str
    model: str
    data_root: Path


@dataclass
class _Registry:
    data_root: Path


@dataclass
class _Artifact:
    lifecycle_state: str
    text: str


def _install_fake_generators(monkeypatch: pytest.MonkeyPatch):
    forge_generators = ModuleType("forge_generators")
    drivers = ModuleType("forge_generators.drivers")
    llm = ModuleType("forge_generators.drivers.llm")
    operators = ModuleType("forge_generators.operators")
    text = ModuleType("forge_generators.operators.text")
    registry_pkg = ModuleType("forge_generators.registry")
    platform_uuid = ModuleType("forge_generators.registry.platform_uuid")

    calls: list[dict[str, Any]] = []

    async def author_prompt_and_wait(**kwargs):
        calls.append(kwargs)
        return _Artifact(lifecycle_state="complete", text="authored")

    llm.LLMDriver = _Driver
    text.author_prompt_and_wait = author_prompt_and_wait
    platform_uuid.PlatformUuidRegistry = _Registry
    forge_generators.drivers = drivers
    forge_generators.operators = operators
    forge_generators.registry = registry_pkg

    monkeypatch.setitem(sys.modules, "forge_generators", forge_generators)
    monkeypatch.setitem(sys.modules, "forge_generators.drivers", drivers)
    monkeypatch.setitem(sys.modules, "forge_generators.drivers.llm", llm)
    monkeypatch.setitem(sys.modules, "forge_generators.operators", operators)
    monkeypatch.setitem(sys.modules, "forge_generators.operators.text", text)
    monkeypatch.setitem(sys.modules, "forge_generators.registry", registry_pkg)
    monkeypatch.setitem(
        sys.modules,
        "forge_generators.registry.platform_uuid",
        platform_uuid,
    )
    return calls


@pytest.mark.asyncio
async def test_build_generation_runner_wraps_author_prompt_and_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    calls = _install_fake_generators(monkeypatch)

    runner = build_generation_runner(data_root=tmp_path, model="llama3.2")
    artifact = await runner(
        "author_prompt",
        intent="write a prompt",
        context={"refs": []},
        target="generate_image",
        style="warm",
    )

    assert artifact.text == "authored"
    assert len(calls) == 1
    call = calls[0]
    assert call["intent"] == "write a prompt"
    assert call["context"] == {"refs": []}
    assert call["target"] == "generate_image"
    assert call["style"] == "warm"
    assert call["driver"] == _Driver(
        provider="ollama",
        model="llama3.2",
        data_root=tmp_path,
    )
    assert call["registry"] == _Registry(data_root=tmp_path)
    assert call["data_root"] == tmp_path


@pytest.mark.asyncio
async def test_generation_runner_rejects_unsupported_operator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _install_fake_generators(monkeypatch)
    runner = build_generation_runner(data_root=tmp_path)

    with pytest.raises(ValueError, match="unsupported generation operator"):
        await runner("generate_image", intent="write")


def test_build_generation_runner_degrades_when_generators_absent(monkeypatch):
    monkeypatch.setitem(sys.modules, "forge_generators.operators.text", None)

    with pytest.raises(GenerationRunnerUnavailable):
        build_generation_runner()
