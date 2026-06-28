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
    # The peer-authored artist-facing description (CapabilityDeclaration.summary).
    # ONE canonical author: the description of a PEER operator lives in the peer's
    # declaration; bridge CONSUMES it for display and never re-authors it. ``None``
    # when the peer omitted it — resolve via :func:`artist_description` for a
    # clearly-DERIVED fallback. Routing/trust stay on AdmissionRecord; the
    # description never goes there.
    summary: str | None = None
    # The peer-authored artist-facing SHORT NAME (CapabilityDeclaration.label).
    # Same ONE-canonical-author rule as ``summary``: a peer operator's short name
    # lives in the peer's declaration and bridge CONSUMES it for display, never
    # re-authoring it. ``None`` when the peer omitted it — resolve via
    # :func:`artist_label` for a clearly-DERIVED humanized fallback. Distinct from
    # ``summary`` (the longer prose line) and from the machine ``tool_id``.
    label: str | None = None


def tool_registration_from_capability(
    registration: CapabilityRegistration,
) -> ToolRegistration:
    """Adapt a published ``CapabilityRegistration`` to the bridge-internal
    ``ToolRegistration`` consumed by ToolRegistry + the planner. Declaration-first:
    the family/id come from the serializable ``CapabilityDeclaration``. The
    ``registration.handler`` is the optional, opaque invocation binding — it is NOT
    placed on the record; ``ToolRegistry.register`` routes it to its binding home.

    Carries the peer-authored ``summary`` across the discovery boundary (Phase 6A
    Option B previously dropped it) so the canonical artist description survives to
    the display surfaces — one canonical author, consumed not re-authored."""
    declaration: CapabilityDeclaration = registration.declaration
    return ToolRegistration(
        tool_id=declaration.capability_id,
        family=declaration.family,
        payload_family=declaration.payload_family or "",
        schema=dict(declaration.input_schema or {}),
        capabilities=dict(declaration.metadata or {}),
        summary=declaration.summary,
        label=declaration.label,
    )


def _humanize_operator_id(operator_id: str) -> str:
    """Derive a human label from an operator_id (last dotted segment, words)."""
    tail = (operator_id or "").rsplit(".", 1)[-1]
    words = tail.replace("_", " ").strip()
    return (words[:1].upper() + words[1:]) if words else (operator_id or "")


def artist_description(
    *,
    summary: str | None,
    operator_id: str,
    fallback_doc: str | None = None,
) -> str:
    """Resolve the artist-facing description of an operator/capability.

    ONE canonical author: a PEER operator's description lives in its
    ``CapabilityDeclaration.summary`` (peer-authored). Bridge CONSUMES that summary
    here and never re-authors it. When ``summary`` is absent (a Bridge-internal
    operator, or a peer that omitted it), return a clearly-DERIVED fallback — the
    first line of a supplied local docstring if any, else a humanized
    ``operator_id``. The fallback is a fallback, NOT a competing canonical source.

    Renderer-neutral: callers in any surface pass the data they hold. This does NOT
    live on a renderer and the description is never placed on AdmissionRecord
    (routing/trust only)."""
    if summary and summary.strip():
        return summary.strip()
    if fallback_doc:
        lines = inspect.cleandoc(fallback_doc).splitlines()
        if lines and lines[0].strip():
            return lines[0].strip()
    return _humanize_operator_id(operator_id)


def artist_label(
    *,
    label: str | None,
    operator_id: str,
) -> str:
    """Resolve the artist-facing SHORT NAME of an operator/capability.

    Mirrors :func:`artist_description` (subordinate-fallback shape) but for the
    short ``CapabilityDeclaration.label`` rather than the longer ``summary``. ONE
    canonical author: a PEER operator's short name lives in its declaration's
    ``label`` (peer-authored); bridge CONSUMES it here and never re-authors it.
    When ``label`` is absent (a Bridge-internal operator, or a peer that omitted
    it), return a clearly-DERIVED humanized ``operator_id``. The fallback is a
    fallback, NOT a competing canonical source. Always returns non-empty (Console
    de-blank guard); never placed on AdmissionRecord."""
    if label and label.strip():
        return label.strip()
    return _humanize_operator_id(operator_id)


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
        # Backend identity reconciles at driver registration time:
        # backend_identity_triple is the canonical source, while collision or
        # divergence with handler.backend_id is rejected loudly in register_driver.
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

    def _discard_registered_tools(self, tool_ids: set[str]) -> None:
        for tool_id in tool_ids:
            self._tools.pop(tool_id, None)

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
