"""Sibling tool registration types and in-memory registry (Phase 4B §9)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from forge_contracts import CapabilityDeclaration, CapabilityRegistration
from forge_contracts.registration import (
    BridgeRegistrationContext,  # noqa: F401 - re-exported by this module
    RegisterCapabilityCallable,  # noqa: F401 - re-exported by this module
)

from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.orchestration.errors import (
    DuplicateToolIdError,
    InvalidGenerationDriverError,
)

# Bridge consumes the published forge-contracts registration protocol: siblings
# call ``register_capability(CapabilityRegistration(declaration=..., handler=...))``.
# ``RegisterToolCallable`` is retained as a back-compat alias of the bridge-internal
# shape for the existing ToolRegistry unit surface.
RegisterToolCallable = Callable[["ToolRegistration"], None]


@dataclass(frozen=True)
class ToolRegistration:
    """Bridge-internal DECLARATION record (discovery-side, invocation-free).
    Sibling capabilities arrive as forge-contracts ``CapabilityRegistration`` and
    are adapted via :func:`tool_registration_from_capability`; the planner consumes
    this shape. The invocation binding (handler/driver) is NOT stored here — it is
    routed to its family-shaped binding home at register time; see
    :meth:`ToolRegistry.register`."""

    tool_id: str
    family: str
    payload_family: str
    schema: dict
    capabilities: Any


def tool_registration_from_capability(
    registration: CapabilityRegistration,
) -> ToolRegistration:
    """Adapt a published ``CapabilityRegistration`` to the bridge-internal
    ``ToolRegistration`` consumed by ToolRegistry + the planner. Declaration-first:
    the family/id come from the serializable ``CapabilityDeclaration``. The
    ``registration.handler`` is the optional, opaque invocation binding — it is NOT
    placed on the record; ``ToolRegistry.register`` routes it to its binding home."""
    declaration: CapabilityDeclaration = registration.declaration
    return ToolRegistration(
        tool_id=declaration.capability_id,
        family=declaration.family,
        payload_family=declaration.payload_family or "",
        schema=dict(declaration.input_schema or {}),
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

    def register(
        self, tool: ToolRegistration, *, sibling_name: str, handler: Any = None
    ) -> None:
        if tool.tool_id in self._tools:
            raise DuplicateToolIdError(tool.tool_id)

        # The registry stores declaration-only records. Invocation binding is
        # family-shaped + invocation-time: route the handler to its binding home
        # (generation -> GenerationDriverRegistry); never store it on the record.
        # A declaration-only capability (handler=None) is discoverable but not yet
        # invocable; validate + wire the driver only when a handler is present.
        #
        # SEAM (named, not filled): backend_id reconciliation. The driver's own
        # handler.backend_id is independent of the planner's declaration-derived
        # backend_identity_triple (planner_passes.pass_1); nothing reconciles them.
        # Materialize the reconciler only when a plan step first needs to EXECUTE a
        # selected capability (Phase 7). See PHASE-6A-DISCOVERY-ALIGNMENT.md.
        if tool.family == "generation" and handler is not None:
            _validate_generation_handler(tool.tool_id, handler)
            if self._generation_driver_registry is not None:
                self._generation_driver_registry.register_driver(handler)

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
