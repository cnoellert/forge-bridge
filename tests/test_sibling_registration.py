"""Tests for sibling registration protocol (Phase 4B Step 8)."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from forge_contracts import (
    CONTRACT_VERSION,
    CapabilityDeclaration,
    CapabilityRegistration,
)
import forge_contracts.registration as contract_registration

import forge_bridge
import forge_bridge.orchestration as orchestration
from forge_bridge.orchestration.discovery import (
    make_db_event_appender,
    register_all_siblings,
    resolve_siblings,
)
from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.orchestration.errors import (
    DuplicateToolIdError,
    InvalidGenerationDriverError,
)
from forge_bridge.orchestration.registration import (
    BridgeRegistrationContext,
    RegisterToolCallable,
    ToolRegistration,
    ToolRegistry,
)
from forge_bridge.store.repo import EventRepo


def _tool(
    tool_id: str,
    *,
    family: str = "validation",
) -> ToolRegistration:
    """Bridge-internal declaration record (invocation-free). Handlers are passed
    separately to ``ToolRegistry.register(..., handler=...)``, never on the record."""
    return ToolRegistration(
        tool_id=tool_id,
        family=family,
        payload_family="perception_validation_v1",
        schema={"type": "object"},
        capabilities={},
    )


def _cap(
    tool_id: str,
    *,
    family: str = "validation",
    handler: Any = None,
) -> CapabilityRegistration:
    """Sibling-side registration in the published forge-contracts protocol.
    ``handler=None`` is declaration-only discovery (the common case)."""
    return CapabilityRegistration(
        declaration=CapabilityDeclaration(
            capability_id=tool_id,
            family=family,
            owner="test-sibling",
            payload_family="perception_validation_v1",
            input_schema={"type": "object"},
        ),
        handler=handler,
    )


class _ValidGenerationDriver:
    backend_id = "test.mock_backend"

    async def poll(self, artifact):
        return None


class _MissingBackendIdDriver:
    async def poll(self, artifact):
        return None


class _MissingPollDriver:
    backend_id = "test.no_poll"


def _install_module(name: str, register_bridge_adapters) -> str:
    module = types.ModuleType(name)
    module.register_bridge_adapters = register_bridge_adapters
    sys.modules[name] = module
    return f"{name}:register_bridge_adapters"


async def _memory_event_appender(events: list[tuple[str, dict]]):
    async def append(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    return append


# ── ToolRegistry ──────────────────────────────────────────────────────────────


def test_registration_context_reexport_is_published_contract_type() -> None:
    assert BridgeRegistrationContext is contract_registration.BridgeRegistrationContext
    assert orchestration.BridgeRegistrationContext is (
        contract_registration.BridgeRegistrationContext
    )
    assert orchestration.RegisterCapabilityCallable is (
        contract_registration.RegisterCapabilityCallable
    )
    assert "RegisterToolCallable" in orchestration.__all__
    assert RegisterToolCallable is orchestration.RegisterToolCallable
    assert len(forge_bridge.__all__) == 19


def test_tool_registry_register_and_query() -> None:
    registry = ToolRegistry()
    registry.register(_tool("a.validation.one"), sibling_name="sibling_a")
    registry.register(
        _tool("b.generation.one", family="generation"),
        sibling_name="sibling_b",
        handler=_ValidGenerationDriver(),
    )

    assert registry.get("a.validation.one") is not None
    assert len(registry.all()) == 2
    assert len(registry.by_family("validation")) == 1
    assert len(registry.by_family("generation")) == 1
    assert registry.by_capability_kind("validation")[0].tool_id == "a.validation.one"
    assert registry.registered_capability_kinds() == frozenset(
        {"validation", "generation"}
    )


def test_tool_registry_duplicate_tool_id_raises() -> None:
    registry = ToolRegistry()
    registry.register(_tool("dup.tool"), sibling_name="sibling")
    with pytest.raises(DuplicateToolIdError):
        registry.register(_tool("dup.tool"), sibling_name="sibling")


def test_tool_registry_invalid_generation_missing_backend_id() -> None:
    registry = ToolRegistry()
    with pytest.raises(InvalidGenerationDriverError):
        registry.register(
            _tool("gen.bad", family="generation"),
            sibling_name="sibling",
            handler=_MissingBackendIdDriver(),
        )


def test_tool_registry_invalid_generation_missing_poll() -> None:
    registry = ToolRegistry()
    with pytest.raises(InvalidGenerationDriverError):
        registry.register(
            _tool("gen.bad", family="generation"),
            sibling_name="sibling",
            handler=_MissingPollDriver(),
        )


def test_tool_registry_generation_wires_driver_registry() -> None:
    driver_registry = GenerationDriverRegistry()
    registry = ToolRegistry(generation_driver_registry=driver_registry)
    driver = _ValidGenerationDriver()
    registry.register(
        _tool("gen.ok", family="generation"),
        sibling_name="sibling",
        handler=driver,
    )
    assert driver_registry.get_driver("test.mock_backend") is driver


def test_tool_registry_generation_without_driver_registry() -> None:
    registry = ToolRegistry()
    registry.register(
        _tool("gen.ok", family="generation"),
        sibling_name="sibling",
        handler=_ValidGenerationDriver(),
    )
    assert len(registry.all()) == 1


def test_tool_registry_emits_pending_tool_registered_event() -> None:
    registry = ToolRegistry()
    registry.register(_tool("tool.one"), sibling_name="sibling_a")
    events = registry.drain_pending_events()
    assert events == [
        (
            "tool_registered",
            {
                "tool_id": "tool.one",
                "family": "validation",
                "sibling_name": "sibling_a",
            },
        )
    ]
    assert registry.drain_pending_events() == []


# ── resolve_siblings ──────────────────────────────────────────────────────────


def test_resolve_siblings_baseline_entry_points() -> None:
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {
            "forge_generators": "forge_generators.bridge:register_bridge_adapters",
            "forge_matte": "forge_matte.bridge:register_bridge_adapters",
        }
    )
    assert resolution.siblings["forge_generators"].endswith(
        "register_bridge_adapters"
    )
    assert resolution.required_capability_kinds == frozenset()


def test_resolve_siblings_config_disables_sibling() -> None:
    resolution = resolve_siblings(
        config={"disabled_siblings": ["forge_matte"]},
        entry_points_loader=lambda _group: {
            "forge_generators": "mod:a",
            "forge_matte": "mod:b",
        },
    )
    assert "forge_matte" not in resolution.siblings
    assert "forge_generators" in resolution.siblings


def test_resolve_siblings_config_adds_sibling() -> None:
    resolution = resolve_siblings(
        config={"additional_siblings": {"custom": "custom.mod:register"}},
        entry_points_loader=lambda _group: {},
    )
    assert resolution.siblings["custom"] == "custom.mod:register"


def test_resolve_siblings_config_overrides_entry_point() -> None:
    resolution = resolve_siblings(
        config={"additional_siblings": {"forge_generators": "override.mod:register"}},
        entry_points_loader=lambda _group: {
            "forge_generators": "original.mod:register",
        },
    )
    assert resolution.siblings["forge_generators"] == "override.mod:register"


def test_resolve_siblings_required_capability_kinds() -> None:
    resolution = resolve_siblings(
        config={"required_capability_kinds": ["generation", "matte"]},
        entry_points_loader=lambda _group: {},
    )
    assert resolution.required_capability_kinds == frozenset(
        {"generation", "matte"}
    )


# ── register_all_siblings ─────────────────────────────────────────────────────


async def test_register_all_siblings_success_two_tools() -> None:
    events: list[tuple[str, dict]] = []

    async def register_bridge_adapters(ctx, register_capability):
        register_capability(_cap("sibling.tool.one"))
        register_capability(_cap("sibling.tool.two", family="generation", handler=_ValidGenerationDriver()))

    target = _install_module("tests.mock_sibling_two_tools", register_bridge_adapters)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"mock_sibling": target},
    )
    tool_registry = ToolRegistry()
    append = await _memory_event_appender(events)

    outcome = await register_all_siblings(
        resolution,
        tool_registry=tool_registry,
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert outcome.siblings_registered == 1
    assert outcome.tools_registered == 2
    assert outcome.degraded is False
    assert any(e[0] == "sibling_registered" for e in events)
    sibling_event = next(e for e in events if e[0] == "sibling_registered")
    assert sibling_event[1]["tool_count"] == 2
    assert set(sibling_event[1]["families"]) == {"validation", "generation"}
    assert events[-1][0] == "bridge_registration_complete"


async def test_register_all_siblings_classifies_off_contract_family() -> None:
    """Classify against KNOWN_CAPABILITY_FAMILIES as observability, not a gate:
    an off-contract family (``editorial``) is still registered, but surfaced on
    the outcome + events. Contract families are not flagged."""
    events: list[tuple[str, dict]] = []

    async def register_bridge_adapters(ctx, register_capability):
        register_capability(_cap("sibling.known", family="validation"))
        register_capability(_cap("sibling.offcontract", family="editorial"))

    target = _install_module(
        "tests.mock_sibling_off_contract", register_bridge_adapters
    )
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"mock_sibling": target},
    )
    tool_registry = ToolRegistry()
    append = await _memory_event_appender(events)

    outcome = await register_all_siblings(
        resolution,
        tool_registry=tool_registry,
        event_appender=append,
        bridge_version="1.5.1",
    )

    # Not gated: both families registered.
    assert outcome.tools_registered == 2
    assert {"validation", "editorial"} <= outcome.capability_kinds_present
    # Classified: only the off-contract family is flagged.
    assert outcome.off_contract_families == frozenset({"editorial"})
    # Surfaced on both the per-sibling and completion events.
    sibling_event = next(e for e in events if e[0] == "sibling_registered")
    assert sibling_event[1]["off_contract_families"] == ["editorial"]
    complete = next(e for e in events if e[0] == "bridge_registration_complete")
    assert complete[1]["off_contract_families"] == ["editorial"]


async def test_register_all_siblings_adapter_raises_other_sibling_continues() -> None:
    events: list[tuple[str, dict]] = []

    async def failing(ctx, register_capability):
        raise RuntimeError("boom")

    async def ok(ctx, register_capability):
        register_capability(_cap("ok.tool"))

    bad = _install_module("tests.mock_sibling_failing", failing)
    good = _install_module("tests.mock_sibling_ok", ok)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {
            "bad": bad,
            "good": good,
        },
    )
    append = await _memory_event_appender(events)
    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert outcome.siblings_failed == 1
    assert outcome.siblings_registered == 1
    failed = next(e for e in events if e[0] == "sibling_registration_failed")
    assert failed[1]["reason"] == "adapter_registration_raised"
    assert failed[1]["exception_type"] == "RuntimeError"


async def test_register_all_siblings_empty_sibling() -> None:
    events: list[tuple[str, dict]] = []

    async def empty(ctx, register_capability):
        return None

    target = _install_module("tests.mock_sibling_empty", empty)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"empty": target},
    )
    append = await _memory_event_appender(events)
    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert outcome.siblings_empty == 1
    assert any(e[0] == "sibling_registered_empty" for e in events)


async def test_register_all_siblings_missing_entry_point() -> None:
    events: list[tuple[str, dict]] = []
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {
            "missing": "tests.nonexistent_module_xyz:register_bridge_adapters",
        },
    )
    append = await _memory_event_appender(events)
    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert outcome.siblings_failed == 1
    failed = events[0]
    assert failed[0] == "sibling_registration_failed"
    assert failed[1]["reason"] == "entry_point_missing"


async def test_register_all_siblings_degraded_missing_generation() -> None:
    events: list[tuple[str, dict]] = []

    async def validation_only(ctx, register_capability):
        register_capability(_cap("only.validation"))

    target = _install_module("tests.mock_sibling_validation_only", validation_only)
    resolution = resolve_siblings(
        config={"required_capability_kinds": ["generation"]},
        entry_points_loader=lambda _group: {"mock": target},
    )
    append = await _memory_event_appender(events)
    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert outcome.degraded is True
    assert outcome.missing_required_capability_kinds == frozenset({"generation"})
    assert events[-1][0] == "bridge_degraded"
    assert events[-1][1]["missing_capability_kinds"] == ["generation"]


async def test_register_all_siblings_complete_when_required_present() -> None:
    events: list[tuple[str, dict]] = []

    async def generation(ctx, register_capability):
        register_capability(
            _cap("gen.tool", family="generation", handler=_ValidGenerationDriver())
        )

    target = _install_module("tests.mock_sibling_generation", generation)
    resolution = resolve_siblings(
        config={"required_capability_kinds": ["generation"]},
        entry_points_loader=lambda _group: {"mock": target},
    )
    append = await _memory_event_appender(events)
    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert outcome.degraded is False
    assert events[-1][0] == "bridge_registration_complete"


async def test_register_all_siblings_dry_run_propagates_to_context() -> None:
    captured: list[BridgeRegistrationContext] = []

    async def capture_ctx(ctx, register_capability):
        captured.append(ctx)

    target = _install_module("tests.mock_sibling_capture_ctx", capture_ctx)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"mock": target},
    )
    events: list[tuple[str, dict]] = []
    append = await _memory_event_appender(events)
    await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
        dry_run=True,
        config_by_sibling={"mock": {"api_key": "secret"}},
    )

    assert len(captured) == 1
    assert isinstance(captured[0], contract_registration.BridgeRegistrationContext)
    # Assert against the contract's own constant so this never drifts on a bump.
    assert captured[0].contract_version == CONTRACT_VERSION
    assert captured[0].requested_families == []
    assert captured[0].dry_run is True
    assert captured[0].config == {"api_key": "secret"}


async def test_register_all_siblings_requested_families_are_published_list() -> None:
    captured: list[BridgeRegistrationContext] = []

    async def capture_ctx(ctx, register_capability):
        captured.append(ctx)

    target = _install_module("tests.mock_sibling_capture_requested", capture_ctx)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"mock": target},
    )
    events: list[tuple[str, dict]] = []
    append = await _memory_event_appender(events)
    await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
        requested_families=frozenset({"generation", "perception"}),
    )

    assert sorted(captured[0].requested_families) == ["generation", "perception"]
    assert isinstance(captured[0].requested_families, list)


async def test_register_all_siblings_event_ordering() -> None:
    events: list[tuple[str, dict]] = []

    async def two_tools(ctx, register_capability):
        register_capability(_cap("order.tool.one"))
        register_capability(_cap("order.tool.two"))

    target = _install_module("tests.mock_sibling_order", two_tools)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"mock": target},
    )
    append = await _memory_event_appender(events)
    await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.4.1",
    )

    types = [event_type for event_type, _ in events]
    tool_indices = [i for i, t in enumerate(types) if t == "tool_registered"]
    sibling_index = types.index("sibling_registered")
    complete_index = types.index("bridge_registration_complete")
    assert len(tool_indices) == 2
    assert all(i < sibling_index for i in tool_indices)
    assert sibling_index < complete_index


async def test_register_all_siblings_driver_registry_side_effect() -> None:
    driver_registry = GenerationDriverRegistry()
    driver = _ValidGenerationDriver()

    async def generation(ctx, register_capability):
        register_capability(
            _cap("gen.side_effect", family="generation", handler=driver),
        )

    target = _install_module("tests.mock_sibling_side_effect", generation)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"mock": target},
    )
    events: list[tuple[str, dict]] = []
    append = await _memory_event_appender(events)
    await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(generation_driver_registry=driver_registry),
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert driver_registry.get_driver("test.mock_backend") is driver


async def test_make_db_event_appender_writes_events(session_factory) -> None:
    append = make_db_event_appender(session_factory)
    await append("tool_registered", {"tool_id": "db.tool", "family": "validation"})

    async with session_factory() as session:
        repo = EventRepo(session)
        events = await repo.get_recent(limit=10, event_type="tool_registered")
        assert len(events) == 1
        assert events[0].payload["tool_id"] == "db.tool"
