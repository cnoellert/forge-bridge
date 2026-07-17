"""Bridge-owned resolution of downstream targets for prompt authoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forge_contracts import AuthoringTarget, BackendIdentityTriple
from forge_contracts.generation import GenerationCapabilityFacts

from forge_bridge.orchestration.drivers import (
    GenerationDriverRegistry,
    backend_id_from_identity_triple,
)
from forge_bridge.orchestration.registration import ToolRegistry


@dataclass(frozen=True)
class AuthoringTargetOption:
    """One declared and invocable downstream operator/backend coordinate."""

    target: AuthoringTarget
    backend_id: str
    tool_id: str
    label: str | None = None
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.model_dump(mode="json"),
            "backend_id": self.backend_id,
            "tool_id": self.tool_id,
            "label": self.label,
            "summary": self.summary,
        }


def list_authoring_target_options(
    tool_registry: ToolRegistry,
    driver_registry: GenerationDriverRegistry,
    *,
    operator_id: str | None = None,
) -> tuple[AuthoringTargetOption, ...]:
    """List valid generation coordinates with a live invocation binding."""

    options: dict[tuple[str, str], AuthoringTargetOption] = {}
    for tool in sorted(tool_registry.by_family("generation"), key=lambda item: item.tool_id):
        capabilities = tool.capabilities
        if not isinstance(capabilities, dict):
            continue
        declared_operator = capabilities.get("operator_id")
        if not isinstance(declared_operator, str) or not declared_operator:
            continue
        if operator_id is not None and declared_operator != operator_id:
            continue

        triple = _declared_backend_identity(capabilities)
        if triple is None:
            continue
        triple_wire = triple.model_dump(mode="json")
        backend_id = backend_id_from_identity_triple(triple_wire)
        if backend_id is None or driver_registry.get_driver(backend_id) is None:
            continue

        target = AuthoringTarget(
            operator_id=declared_operator,
            backend_identity_triple=triple,
        )
        options.setdefault(
            (declared_operator, backend_id),
            AuthoringTargetOption(
                target=target,
                backend_id=backend_id,
                tool_id=tool.tool_id,
                label=tool.label,
                summary=tool.summary,
            ),
        )

    return tuple(
        sorted(options.values(), key=lambda option: (option.target.operator_id, option.backend_id))
    )


def resolve_authoring_target(
    tool_registry: ToolRegistry,
    driver_registry: GenerationDriverRegistry,
    *,
    operator_id: str,
    backend_id: str | None = None,
) -> AuthoringTarget:
    """Resolve an explicit operator/backend choice without inventing ranking policy."""

    clean_operator = operator_id.strip()
    if not clean_operator:
        raise ValueError("target_operator must be a non-empty string")
    clean_backend = backend_id.strip() if isinstance(backend_id, str) else None
    if isinstance(backend_id, str) and not clean_backend:
        raise ValueError("target_backend must be a non-empty string")

    options = list_authoring_target_options(
        tool_registry,
        driver_registry,
        operator_id=clean_operator,
    )
    if clean_backend is not None:
        matches = [option for option in options if option.backend_id == clean_backend]
        if len(matches) == 1:
            return matches[0].target
        available = ", ".join(option.backend_id for option in options) or "none"
        raise ValueError(
            f"target backend {clean_backend!r} is not invocable for {clean_operator!r}; "
            f"available backends: {available}"
        )

    if len(options) == 1:
        return options[0].target
    if not options:
        raise ValueError(f"no invocable authoring target for operator {clean_operator!r}")
    available = ", ".join(option.backend_id for option in options)
    raise ValueError(
        f"multiple authoring targets are available for {clean_operator!r}; "
        f"choose target_backend from: {available}"
    )


async def discover_authoring_target_options(
    *,
    operator_id: str | None = None,
) -> tuple[AuthoringTargetOption, ...]:
    """Discover the installed generation catalog without requiring the database."""

    from forge_bridge import __version__
    from forge_bridge.orchestration.discovery import (
        register_all_siblings,
        resolve_siblings,
    )

    drivers = GenerationDriverRegistry()
    tools = ToolRegistry(generation_driver_registry=drivers)

    async def discard_event(_event_type: str, _payload: dict[str, Any]) -> None:
        return None

    await register_all_siblings(
        resolve_siblings(),
        tool_registry=tools,
        event_appender=discard_event,
        bridge_version=__version__,
        requested_families=frozenset({"generation"}),
    )
    return list_authoring_target_options(
        tools,
        drivers,
        operator_id=operator_id,
    )


def _declared_backend_identity(
    capabilities: dict[str, Any],
) -> BackendIdentityTriple | None:
    try:
        facts = GenerationCapabilityFacts.from_metadata(capabilities)
        if facts is not None:
            return facts.backend_identity
        return BackendIdentityTriple.model_validate(
            capabilities.get("backend_identity_triple")
        )
    except (TypeError, ValueError):
        return None
