"""Daemon-edge adapter for forge-generators terminal generation calls."""
from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_GENERATION_DATA_ROOT = Path.home() / ".forge-bridge" / "generation"
DEFAULT_OLLAMA_MODEL = "llama3.2"


class GenerationRunnerUnavailable(ImportError):
    """Raised when the forge-generators authoring surface is unavailable."""


def build_generation_runner(
    *,
    driver: Any | None = None,
    registry: Any | None = None,
    data_root: str | Path | None = None,
    model: str | None = None,
    timeout_seconds: float | None = None,
):
    """Return an async callable matching ``GenerationDispatchBoundary``.

    The import is guarded so a stock Bridge installation without
    forge-generators can still boot; the composition boundary simply receives
    no runner until the daemon edge wires one.
    """

    try:
        from forge_generators.drivers.llm import LLMDriver
        from forge_generators.operators.text import author_prompt_and_wait
        from forge_generators.registry.platform_uuid import PlatformUuidRegistry
    except (ImportError, ModuleNotFoundError) as exc:
        raise GenerationRunnerUnavailable(
            "forge_generators author_prompt surface is unavailable"
        ) from exc

    root = Path(data_root).expanduser() if data_root is not None else (
        DEFAULT_GENERATION_DATA_ROOT
    )
    runner_driver = driver or LLMDriver(
        provider="ollama",
        model=model or DEFAULT_OLLAMA_MODEL,
        data_root=root,
    )
    runner_registry = registry or PlatformUuidRegistry(root)

    async def run_generation(
        operator_id: str,
        *,
        intent: str,
        context: Any = None,
        target: Any = None,
        style: str | None = None,
    ) -> Any:
        if operator_id != "author_prompt":
            raise ValueError(f"unsupported generation operator: {operator_id!r}")
        return await author_prompt_and_wait(
            intent=intent,
            context=context,
            target=target,
            style=style,
            driver=runner_driver,
            registry=runner_registry,
            data_root=root,
            timeout_seconds=timeout_seconds,
        )

    return run_generation
