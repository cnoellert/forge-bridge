from __future__ import annotations

from forge_contracts import BackendIdentityTriple, GenerationCapabilityFacts

from forge_bridge.orchestration.authoring_targets import (
    list_authoring_target_options,
    resolve_authoring_target,
)
from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.orchestration.registration import ToolRegistration, ToolRegistry


class _Driver:
    def __init__(self, triple: BackendIdentityTriple) -> None:
        self.backend_identity_triple = triple.model_dump(mode="json")
        self.backend_id = f"{triple.surface}.{triple.path}"

    async def submit(self, _invocation):  # pragma: no cover - resolver never invokes
        raise NotImplementedError

    async def poll(self, _artifact):  # pragma: no cover - resolver never invokes
        raise NotImplementedError


def _register(
    tools: ToolRegistry,
    *,
    operator_id: str,
    triple: BackendIdentityTriple,
    tool_id: str,
    flat_triple: dict | None = None,
) -> None:
    facts = GenerationCapabilityFacts(backend_identity=triple)
    tools.register(
        ToolRegistration(
            tool_id=tool_id,
            family="generation",
            payload_family="generation.test",
            schema={"type": "object"},
            capabilities={
                "operator_id": operator_id,
                "backend_identity_triple": flat_triple
                or triple.model_dump(mode="json"),
                "generation_facts": facts.model_dump(mode="json"),
            },
        ),
        sibling_name="test-generators",
    )


def _triple(path: str) -> BackendIdentityTriple:
    return BackendIdentityTriple(
        surface="test-surface",
        path=path,
        auth_mechanism="no-auth",
        revision=f"{path}-r1",
    )


def test_list_options_uses_typed_facts_and_requires_live_driver() -> None:
    drivers = GenerationDriverRegistry()
    tools = ToolRegistry(generation_driver_registry=drivers)
    live = _triple("live")
    declaration_only = _triple("declaration-only")
    drivers.register_driver(_Driver(live))
    _register(
        tools,
        operator_id="generate_still",
        triple=live,
        tool_id="gen.still.live",
        flat_triple=_triple("drifted-flat-key").model_dump(mode="json"),
    )
    _register(
        tools,
        operator_id="generate_still",
        triple=declaration_only,
        tool_id="gen.still.declaration-only",
    )

    options = list_authoring_target_options(tools, drivers)

    assert len(options) == 1
    assert options[0].backend_id == "test-surface.live"
    assert options[0].target.backend_identity_triple == live


def test_resolve_explicit_backend_returns_exact_coordinate() -> None:
    drivers = GenerationDriverRegistry()
    tools = ToolRegistry(generation_driver_registry=drivers)
    for path in ("a", "b"):
        triple = _triple(path)
        drivers.register_driver(_Driver(triple))
        _register(
            tools,
            operator_id="generate_video_from_image",
            triple=triple,
            tool_id=f"gen.motion.{path}",
        )

    target = resolve_authoring_target(
        tools,
        drivers,
        operator_id="generate_video_from_image",
        backend_id="test-surface.b",
    )

    assert target.operator_id == "generate_video_from_image"
    assert target.backend_identity_triple.path == "b"


def test_resolve_single_backend_needs_no_backend_hint() -> None:
    drivers = GenerationDriverRegistry()
    tools = ToolRegistry(generation_driver_registry=drivers)
    triple = _triple("only")
    drivers.register_driver(_Driver(triple))
    _register(
        tools,
        operator_id="generate_3d_from_image",
        triple=triple,
        tool_id="gen.3d.only",
    )

    target = resolve_authoring_target(
        tools,
        drivers,
        operator_id="generate_3d_from_image",
    )

    assert target.backend_identity_triple == triple


def test_resolve_ambiguous_operator_requires_explicit_backend() -> None:
    drivers = GenerationDriverRegistry()
    tools = ToolRegistry(generation_driver_registry=drivers)
    for path in ("a", "b"):
        triple = _triple(path)
        drivers.register_driver(_Driver(triple))
        _register(
            tools,
            operator_id="generate_still",
            triple=triple,
            tool_id=f"gen.still.{path}",
        )

    try:
        resolve_authoring_target(tools, drivers, operator_id="generate_still")
    except ValueError as exc:
        assert "multiple authoring targets" in str(exc)
        assert "test-surface.a" in str(exc)
        assert "test-surface.b" in str(exc)
    else:  # pragma: no cover - assertion helper
        raise AssertionError("expected ambiguous target resolution to fail")


def test_resolve_unknown_backend_lists_valid_choices() -> None:
    drivers = GenerationDriverRegistry()
    tools = ToolRegistry(generation_driver_registry=drivers)
    triple = _triple("available")
    drivers.register_driver(_Driver(triple))
    _register(
        tools,
        operator_id="generate_still",
        triple=triple,
        tool_id="gen.still.available",
    )

    try:
        resolve_authoring_target(
            tools,
            drivers,
            operator_id="generate_still",
            backend_id="test-surface.missing",
        )
    except ValueError as exc:
        assert "test-surface.available" in str(exc)
    else:  # pragma: no cover - assertion helper
        raise AssertionError("expected unknown backend resolution to fail")
