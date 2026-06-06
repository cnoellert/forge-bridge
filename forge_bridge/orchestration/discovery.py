"""Sibling discovery and registration orchestration (Phase 4B §9)."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from forge_contracts import KNOWN_CAPABILITY_FAMILIES, CapabilityRegistration

from forge_bridge.orchestration.errors import (
    DuplicateToolIdError,
    InvalidGenerationDriverError,
)
from forge_bridge.orchestration.registration import (
    BridgeRegistrationContext,
    ToolRegistry,
    tool_registration_from_capability,
)
from forge_bridge.store.repo import EventRepo

# Discovery requests ALL families by default (empty ``requested_families``) and
# classifies what siblings declare against the contract vocabulary. Bridge's old
# local family allowlist {perceptual, validation, generation, matte, editorial}
# was retired: it misspelled ``perception`` and omitted ``execution``/``packaging``,
# silently filtering out both primary siblings (see PHASE-6A-DISCOVERY-ALIGNMENT.md).
DEFAULT_ENTRY_POINT_GROUP = "forge_bridge.siblings"


@dataclass(frozen=True)
class SiblingResolution:
    siblings: Mapping[str, str]
    required_capability_kinds: frozenset[str]


@dataclass(frozen=True)
class RegistrationOutcome:
    siblings_attempted: int
    siblings_registered: int
    siblings_failed: int
    siblings_empty: int
    tools_registered: int
    capability_kinds_present: frozenset[str]
    missing_required_capability_kinds: frozenset[str]
    degraded: bool
    # Families siblings declared that are NOT in the contract's
    # ``KNOWN_CAPABILITY_FAMILIES``. Observability only — off-contract families are
    # still registered (the contract treats ``CapabilityFamily`` as an open string,
    # ``KNOWN_CAPABILITY_FAMILIES`` as a soft set). This surfaces vocabulary drift
    # (e.g. a sibling declaring ``editorial``) without gating discovery.
    off_contract_families: frozenset[str] = frozenset()


def _enumerate_entry_points(group: str) -> dict[str, str]:
    return {ep.name: ep.value for ep in entry_points(group=group)}


def resolve_siblings(
    *,
    config: Mapping[str, Any] | None = None,
    entry_point_group: str = DEFAULT_ENTRY_POINT_GROUP,
    entry_points_loader: Callable[[str], Mapping[str, str]] | None = None,
) -> SiblingResolution:
    loader = entry_points_loader or _enumerate_entry_points
    siblings = dict(loader(entry_point_group))
    cfg = config or {}

    for name in cfg.get("disabled_siblings", []):
        siblings.pop(name, None)

    for name, target in (cfg.get("additional_siblings") or {}).items():
        siblings[name] = target

    required = frozenset(cfg.get("required_capability_kinds", []))
    return SiblingResolution(
        siblings=siblings,
        required_capability_kinds=required,
    )


def _load_sibling_callable(target: str) -> Any:
    if ":" not in target:
        raise ImportError(f"Invalid sibling entry point target: {target!r}")
    module_name, attr_name = target.rsplit(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


async def _invoke_sibling(
    sibling_func: Any,
    ctx: BridgeRegistrationContext,
    register_capability: Callable[..., None],
) -> None:
    result = sibling_func(ctx, register_capability)
    if inspect.isawaitable(result):
        await result


async def register_all_siblings(
    resolution: SiblingResolution,
    *,
    tool_registry: ToolRegistry,
    event_appender: Callable[[str, dict], Awaitable[None]],
    bridge_version: str,
    requested_families: frozenset[str] = frozenset(),
    config_by_sibling: Mapping[str, Mapping[str, Any]] | None = None,
    dry_run: bool = False,
) -> RegistrationOutcome:
    # Empty ``requested_families`` = request-all: siblings register every declared
    # capability and bridge classifies against the contract vocabulary. Do NOT
    # default to a bridge-local family allowlist (see PHASE-6A-DISCOVERY-ALIGNMENT).
    sibling_config = config_by_sibling or {}

    siblings_attempted = 0
    siblings_registered = 0
    siblings_failed = 0
    siblings_empty = 0
    tools_registered_total = 0

    for sibling_name, target in resolution.siblings.items():
        siblings_attempted += 1
        tools_before = len(tool_registry.all())

        try:
            sibling_func = _load_sibling_callable(target)
        except Exception as exc:
            siblings_failed += 1
            await event_appender(
                "sibling_registration_failed",
                {
                    "sibling_name": sibling_name,
                    "reason": "entry_point_missing",
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            continue

        ctx = BridgeRegistrationContext(
            bridge_version=bridge_version,
            requested_families=requested_families,
            dry_run=dry_run,
            config=dict(sibling_config.get(sibling_name, {})),
        )

        families_registered: set[str] = set()

        def register_capability(registration: CapabilityRegistration):
            tool = tool_registration_from_capability(registration)
            tool_registry.register(
                tool, sibling_name=sibling_name, handler=registration.handler
            )
            families_registered.add(tool.family)

        try:
            await _invoke_sibling(sibling_func, ctx, register_capability)
        except (DuplicateToolIdError, InvalidGenerationDriverError):
            raise
        except Exception as exc:
            siblings_failed += 1
            await event_appender(
                "sibling_registration_failed",
                {
                    "sibling_name": sibling_name,
                    "reason": "adapter_registration_raised",
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            continue

        for event_type, payload in tool_registry.drain_pending_events():
            await event_appender(event_type, payload)

        tools_after = len(tool_registry.all())
        tool_count = tools_after - tools_before
        tools_registered_total += tool_count

        if tool_count == 0:
            siblings_empty += 1
            await event_appender(
                "sibling_registered_empty",
                {"sibling_name": sibling_name},
            )
        else:
            siblings_registered += 1
            await event_appender(
                "sibling_registered",
                {
                    "sibling_name": sibling_name,
                    "tool_count": tool_count,
                    "families": sorted(families_registered),
                    # Classify (observe, don't gate): which of this sibling's
                    # families fall outside the contract's known vocabulary.
                    "off_contract_families": sorted(
                        families_registered - KNOWN_CAPABILITY_FAMILIES
                    ),
                },
            )

    capability_kinds_present = tool_registry.registered_capability_kinds()
    # Classify against the contract vocabulary (observe, never gate): families
    # outside KNOWN_CAPABILITY_FAMILIES are still registered, just surfaced.
    off_contract_families = capability_kinds_present - KNOWN_CAPABILITY_FAMILIES
    missing_required = (
        resolution.required_capability_kinds - capability_kinds_present
    )
    degraded = bool(missing_required)

    if degraded:
        await event_appender(
            "bridge_degraded",
            {
                "reason": "required_capability_missing",
                "missing_capability_kinds": sorted(missing_required),
            },
        )
    else:
        await event_appender(
            "bridge_registration_complete",
            {
                "capability_kinds": sorted(capability_kinds_present),
                "off_contract_families": sorted(off_contract_families),
                "tool_count": len(tool_registry.all()),
            },
        )

    return RegistrationOutcome(
        siblings_attempted=siblings_attempted,
        siblings_registered=siblings_registered,
        siblings_failed=siblings_failed,
        siblings_empty=siblings_empty,
        tools_registered=tools_registered_total,
        capability_kinds_present=capability_kinds_present,
        missing_required_capability_kinds=missing_required,
        degraded=degraded,
        off_contract_families=off_contract_families,
    )


def make_db_event_appender(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[str, dict], Awaitable[None]]:
    """Production helper: one session + commit per emitted registration event."""

    async def append(event_type: str, payload: dict) -> None:
        async with session_factory() as session:
            repo = EventRepo(session)
            await repo.append(event_type, payload)
            await session.commit()

    return append
