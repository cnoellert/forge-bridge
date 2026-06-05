"""Sibling tool registration types and in-memory registry (Phase 4B §9)."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from forge_contracts import CapabilityDeclaration, CapabilityRegistration

from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.orchestration.errors import (
    DuplicateToolIdError,
    InvalidGenerationDriverError,
)

# Bridge consumes the published forge-contracts registration protocol: siblings
# call ``register_capability(CapabilityRegistration(declaration=..., handler=...))``.
# ``RegisterToolCallable`` is retained as a back-compat alias of the bridge-internal
# shape for the existing ToolRegistry unit surface.
RegisterCapabilityCallable = Callable[[CapabilityRegistration], None]
RegisterToolCallable = Callable[["ToolRegistration"], None]


@dataclass(frozen=True)
class BridgeRegistrationContext:
    """Bridge → sibling. Passed to ``register_bridge_adapters(ctx, register_capability)``.

    ``requested_families`` is the family filter bridge asks siblings to honor;
    **empty means request-all** (siblings register every declared capability).
    Discovery must NOT pass bridge's local family vocabulary here — that silently
    filters out contract families bridge doesn't enumerate (see
    .planning/PHASE-6A-DISCOVERY-ALIGNMENT.md).
    """

    bridge_version: str
    requested_families: frozenset[str]
    dry_run: bool
    config: Mapping[str, Any]


@dataclass(frozen=True)
class ToolRegistration:
    """Bridge-internal registration shape. Sibling capabilities arrive as
    forge-contracts ``CapabilityRegistration`` and are adapted via
    :func:`tool_registration_from_capability`; the planner consumes this shape."""

    tool_id: str
    family: str
    payload_family: str
    schema: dict
    handler: Any
    capabilities: Any


def tool_registration_from_capability(
    registration: CapabilityRegistration,
) -> ToolRegistration:
    """Adapt a published ``CapabilityRegistration`` to the bridge-internal
    ``ToolRegistration`` consumed by ToolRegistry + the planner. Declaration-first:
    the family/id come from the serializable ``CapabilityDeclaration``; the
    ``handler`` is the optional, opaque invocation binding (``None`` for
    declaration-only discovery)."""
    declaration: CapabilityDeclaration = registration.declaration
    return ToolRegistration(
        tool_id=declaration.capability_id,
        family=declaration.family,
        payload_family=declaration.payload_family or "",
        schema=dict(declaration.input_schema or {}),
        handler=registration.handler,
        capabilities=dict(declaration.metadata or {}),
    )


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

        # Handler binding is invocation-time and optional. A declaration-only
        # generation capability (handler=None) is discoverable but not yet
        # invocable; validate + wire the driver only when a handler is present.
        if tool.family == "generation" and tool.handler is not None:
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
