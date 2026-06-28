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
    artist_description,
    artist_label,
    tool_registration_from_capability,
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


# ── description seam: summary carry + resolver ────────────────────────────────


def test_tool_registration_carries_peer_summary() -> None:
    """The peer-authored CapabilityDeclaration.summary survives the discovery
    boundary onto the bridge-internal ToolRegistration (was dropped pre-seam)."""
    reg = CapabilityRegistration(
        declaration=CapabilityDeclaration(
            capability_id="vision.classify_shot",
            family="validation",
            owner="forge_vision",
            summary="Classify a shot's framing and motion.",
            input_schema={"type": "object"},
        ),
    )
    tool = tool_registration_from_capability(reg)
    assert tool.summary == "Classify a shot's framing and motion."


def test_tool_registration_summary_absent_is_none() -> None:
    tool = tool_registration_from_capability(_cap("vision.no_summary"))
    assert tool.summary is None


def test_artist_description_prefers_peer_summary() -> None:
    assert (
        artist_description(
            summary="Canonical peer line.",
            operator_id="vision.classify_shot",
            fallback_doc="Some local docstring first line.\nrest",
        )
        == "Canonical peer line."
    )


def test_artist_description_falls_back_to_docstring_first_line() -> None:
    assert (
        artist_description(
            summary=None,
            operator_id="vision.classify_shot",
            fallback_doc="Derived from the docstring.\nmore detail",
        )
        == "Derived from the docstring."
    )


def test_artist_description_falls_back_to_humanized_id() -> None:
    # No summary, no docstring → clearly-derived humanized operator_id.
    assert (
        artist_description(summary="  ", operator_id="traffik.flame_delta.host_resolve")
        == "Host resolve"
    )


# ── label seam: short-name carry + resolver ───────────────────────────────────


def test_tool_registration_carries_peer_label() -> None:
    """The peer-authored CapabilityDeclaration.label survives the discovery
    boundary onto the bridge-internal ToolRegistration (mirrors the summary carry)."""
    reg = CapabilityRegistration(
        declaration=CapabilityDeclaration(
            capability_id="vision.classify_shot",
            family="validation",
            owner="forge_vision",
            label="Classify Shot",
            input_schema={"type": "object"},
        ),
    )
    tool = tool_registration_from_capability(reg)
    assert tool.label == "Classify Shot"


def test_tool_registration_label_absent_is_none() -> None:
    tool = tool_registration_from_capability(_cap("vision.no_label"))
    assert tool.label is None


def test_artist_label_prefers_peer_label() -> None:
    assert (
        artist_label(label="Classify Shot", operator_id="vision.classify_shot")
        == "Classify Shot"
    )


def test_artist_label_falls_back_to_humanized_id() -> None:
    # No label → clearly-derived humanized operator_id (subordinate, never blank).
    assert (
        artist_label(label="  ", operator_id="traffik.flame_delta.host_resolve")
        == "Host resolve"
    )
    assert (
        artist_label(label=None, operator_id="vision.classify_shot")
        == "Classify shot"
    )


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


async def test_register_all_siblings_invalid_generation_driver_is_skipped() -> None:
    events: list[tuple[str, dict]] = []

    async def bad_generation(ctx, register_capability):
        register_capability(
            _cap("gen.bad", family="generation", handler=_MissingBackendIdDriver())
        )

    async def ok(ctx, register_capability):
        register_capability(_cap("ok.after.invalid"))

    bad = _install_module("tests.mock_sibling_bad_generation", bad_generation)
    good = _install_module("tests.mock_sibling_after_bad_generation", ok)
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
        bridge_version="1.5.1",
    )

    assert outcome.siblings_failed == 1
    assert outcome.siblings_registered == 1
    failed = next(e for e in events if e[0] == "sibling_registration_failed")
    assert failed[1]["reason"] == "driver_registration_rejected"
    assert failed[1]["exception_type"] == "InvalidGenerationDriverError"
    assert any(
        payload.get("tool_id") == "ok.after.invalid"
        for event_type, payload in events
        if event_type == "tool_registered"
    )


async def test_register_all_siblings_duplicate_tool_id_is_skipped() -> None:
    events: list[tuple[str, dict]] = []

    async def first(ctx, register_capability):
        register_capability(_cap("dup.tool"))

    async def duplicate(ctx, register_capability):
        register_capability(_cap("dup.tool"))

    async def ok(ctx, register_capability):
        register_capability(_cap("ok.after.dup"))

    target_first = _install_module("tests.mock_sibling_first_dup", first)
    target_duplicate = _install_module("tests.mock_sibling_duplicate_dup", duplicate)
    target_ok = _install_module("tests.mock_sibling_after_dup", ok)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {
            "first": target_first,
            "duplicate": target_duplicate,
            "ok": target_ok,
        },
    )
    append = await _memory_event_appender(events)

    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(),
        event_appender=append,
        bridge_version="1.5.1",
    )

    assert outcome.siblings_failed == 1
    assert outcome.siblings_registered == 2
    failed = next(e for e in events if e[0] == "sibling_registration_failed")
    assert failed[1]["reason"] == "driver_registration_rejected"
    assert failed[1]["exception_type"] == "DuplicateToolIdError"
    registered_ids = [
        payload["tool_id"]
        for event_type, payload in events
        if event_type == "tool_registered"
    ]
    assert registered_ids == ["dup.tool", "ok.after.dup"]


async def test_register_all_siblings_failure_discards_partial_pending_events() -> None:
    events: list[tuple[str, dict]] = []
    tool_registry = ToolRegistry()

    async def partial_then_fail(ctx, register_capability):
        register_capability(_cap("partial.tool"))
        raise RuntimeError("boom after partial")

    async def ok(ctx, register_capability):
        register_capability(_cap("ok.after.partial"))

    bad = _install_module("tests.mock_sibling_partial_failure", partial_then_fail)
    good = _install_module("tests.mock_sibling_after_partial", ok)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {
            "bad": bad,
            "good": good,
        },
    )
    append = await _memory_event_appender(events)

    outcome = await register_all_siblings(
        resolution,
        tool_registry=tool_registry,
        event_appender=append,
        bridge_version="1.5.1",
    )

    assert outcome.siblings_failed == 1
    assert outcome.siblings_registered == 1
    assert tool_registry.get("partial.tool") is None
    assert tool_registry.get("ok.after.partial") is not None
    registered_ids = [
        payload["tool_id"]
        for event_type, payload in events
        if event_type == "tool_registered"
    ]
    assert registered_ids == ["ok.after.partial"]


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


async def test_register_all_siblings_generation_declaration_only_signal() -> None:
    """#61: a generation sibling that registers DECLARATIONS but lands zero
    drivers (handler=None — the stale dist-info entry-point symptom) gets a
    distinct ``sibling_registered_declaration_only`` signal, not a silent
    ``sibling_registered`` that later degrades to ``dispatch_no_driver``."""
    events: list[tuple[str, dict]] = []

    async def declaration_only(ctx, register_capability):
        register_capability(_cap("gen.decl.only", family="generation", handler=None))

    target = _install_module("tests.mock_sibling_decl_only", declaration_only)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"declonly": target},
    )
    append = await _memory_event_appender(events)
    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(GenerationDriverRegistry()),
        event_appender=append,
        bridge_version="1.4.1",
    )

    # The declaration DID land — discovery is healthy, the sibling counts as
    # registered — but the distinct invocation-dead signal fires alongside it.
    assert outcome.siblings_registered == 1
    assert outcome.siblings_declaration_only == 1
    decl_only = [e for e in events if e[0] == "sibling_registered_declaration_only"]
    assert len(decl_only) == 1
    payload = decl_only[0][1]
    assert payload["sibling_name"] == "declonly"
    assert payload["family"] == "generation"
    assert payload["declaration_count"] == 1
    assert payload["driver_count"] == 0
    assert payload["resolved_entry_point"] == target


async def test_register_all_siblings_generation_with_driver_no_signal() -> None:
    """Positive control: a generation sibling whose declaration carries a real
    handler lands a driver and must NOT raise the declaration-only signal."""
    events: list[tuple[str, dict]] = []

    async def with_driver(ctx, register_capability):
        register_capability(
            _cap("gen.real", family="generation", handler=_ValidGenerationDriver())
        )

    target = _install_module("tests.mock_sibling_gen_driver", with_driver)
    resolution = resolve_siblings(
        entry_points_loader=lambda _group: {"gendriver": target},
    )
    append = await _memory_event_appender(events)
    outcome = await register_all_siblings(
        resolution,
        tool_registry=ToolRegistry(GenerationDriverRegistry()),
        event_appender=append,
        bridge_version="1.4.1",
    )

    assert outcome.siblings_registered == 1
    assert outcome.siblings_declaration_only == 0
    assert not any(
        e[0] == "sibling_registered_declaration_only" for e in events
    )


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
