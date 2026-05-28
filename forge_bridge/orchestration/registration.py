"""Sibling tool registration types and in-memory registry (Phase 4B §9)."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.orchestration.errors import (
    DuplicateToolIdError,
    InvalidGenerationDriverError,
)

RegisterToolCallable = Callable[["ToolRegistration"], None]


@dataclass(frozen=True)
class BridgeRegistrationContext:
    """Bridge → sibling. Passed to ``register_bridge_adapters(ctx, register_tool)``."""

    bridge_version: str
    capability_kinds: frozenset[str]
    dry_run: bool
    config: Mapping[str, Any]


@dataclass(frozen=True)
class ToolRegistration:
    """Sibling → bridge (via ``register_tool`` callable)."""

    tool_id: str
    family: str
    payload_family: str
    schema: dict
    handler: Any
    capabilities: Any


def _validate_generation_handler(tool_id: str, handler: Any) -> None:
    if not hasattr(handler, "backend_id"):
        raise InvalidGenerationDriverError(tool_id, "missing backend_id attribute")
    poll = getattr(handler, "poll", None)
    if poll is None or not inspect.iscoroutinefunction(poll):
        raise InvalidGenerationDriverError(tool_id, "missing async poll method")


class ToolRegistry:
    """In-memory registry of tools registered by siblings at bridge startup."""

    def __init__(
        self,
        generation_driver_registry: GenerationDriverRegistry | None = None,
    ) -> None:
        self._generation_driver_registry = generation_driver_registry
        self._tools: dict[str, ToolRegistration] = {}
        self._pending_events: list[tuple[str, dict[str, Any]]] = []

    def register(self, tool: ToolRegistration, *, sibling_name: str) -> None:
        if tool.tool_id in self._tools:
            raise DuplicateToolIdError(tool.tool_id)

        if tool.family == "generation":
            _validate_generation_handler(tool.tool_id, tool.handler)
            if self._generation_driver_registry is not None:
                self._generation_driver_registry.register_driver(tool.handler)

        self._tools[tool.tool_id] = tool
        self._pending_events.append(
            (
                "tool_registered",
                {
                    "tool_id": tool.tool_id,
                    "family": tool.family,
                    "sibling_name": sibling_name,
                },
            )
        )

    def drain_pending_events(self) -> list[tuple[str, dict[str, Any]]]:
        events = self._pending_events
        self._pending_events = []
        return events

    def get(self, tool_id: str) -> ToolRegistration | None:
        return self._tools.get(tool_id)

    def by_family(self, family: str) -> list[ToolRegistration]:
        return [tool for tool in self._tools.values() if tool.family == family]

    def by_capability_kind(self, kind: str) -> list[ToolRegistration]:
        return self.by_family(kind)

    def all(self) -> list[ToolRegistration]:
        return list(self._tools.values())

    def registered_capability_kinds(self) -> frozenset[str]:
        return frozenset(tool.family for tool in self._tools.values())
