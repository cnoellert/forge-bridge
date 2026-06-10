"""#24 — planner consumes the typed v0.3 GenerationCapabilityFacts.

Two acceptance layers:

(a) Unit (drift-proof): fixtures are built from the *real* forge-contracts
    GenerationCapabilityFacts type, so they cannot drift from the contract. The
    typed ``backend_identity`` is deliberately made to DIFFER from the flat
    ``backend_identity_triple`` decoy key, so "typed source wins the join" is a
    provable assertion, not an accident of equal values. Plus the malformed-
    payload degrade path (from_metadata raises -> fall back, never crash).

(b) Stub-sibling (real round-trip): a stub sibling publishes a contract-valid
    declaration through the *real* ``register_all_siblings`` path, and the planner
    selects a backend whose id is derived from the typed triple end-to-end.
"""

from __future__ import annotations

import sys
import types

from forge_contracts import CapabilityDeclaration, CapabilityRegistration
from forge_contracts.generation import (
    GENERATION_FACTS_KEY,
    BackendIdentityTriple,
    GenerationCapabilityFacts,
    ReferenceRequirementSpec,
)

from forge_bridge.orchestration import (
    InMemoryLineageGraph,
    Planner,
    ToolRegistry,
    register_all_siblings,
    resolve_siblings,
)
from forge_bridge.orchestration.identity_registries import (
    InMemoryPlatformUUIDRegistry,
    InMemoryTrainedIdentityRegistry,
)
from forge_bridge.orchestration.registration import ToolRegistration
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo

# Typed identity (what facts publish) deliberately DIFFERS from the flat decoy,
# so an assertion on the resulting backend_id distinguishes the two sources.
_TYPED_TRIPLE = {
    "surface": "forge_generators",
    "path": "trellis2",
    "auth_mechanism": "api_key",
    "revision": "rev-typed",
}
_TYPED_BACKEND_ID = "forge_generators.trellis2"  # backend_id_from_snapshot_entry shape

_FLAT_DECOY_TRIPLE = {
    "surface": "stale_flat",
    "path": "should_lose",
    "revision": "rev-flat",
}


def _facts_metadata(
    *, typed_triple: dict | None, flat_triple: dict, malformed: bool = False, **extra
) -> dict:
    """Declaration metadata carrying a flat decoy triple plus a typed
    ``generation_facts`` payload built from the real contract type."""
    metadata: dict = {
        "backend_identity_triple": flat_triple,
        "acceptance_score": 0.95,
        "estimated_cost": 1.0,
        **extra,
    }
    if malformed:
        # Present but invalid -> GenerationCapabilityFacts.from_metadata RAISES.
        metadata[GENERATION_FACTS_KEY] = {"backend_identity": {"surface": "only"}}
    elif typed_triple is not None:
        metadata[GENERATION_FACTS_KEY] = GenerationCapabilityFacts(
            backend_identity=BackendIdentityTriple(**typed_triple),
            reference_requirements=ReferenceRequirementSpec(
                accepts_roles=["reference"],
                required_roles=[],
                requires_first_frame=False,
                max_references=4,
            ),
        ).model_dump(mode="json")
    return metadata


def _generation_tool(metadata: dict) -> ToolRegistration:
    return ToolRegistration(
        tool_id="forge_generators.test.backend",
        family="generation",
        payload_family="generation_v1",
        schema={"type": "object"},
        capabilities=metadata,
    )


# Deliverable intentionally requires neither first-frame nor identity-lock: those
# pass_2 filters are out of #24 scope (no request-side operand), and generators
# no longer publish first_frame_guarantee (Gate 0). The candidate survives on the
# facts it actually carries.
def _locked_intent_body() -> dict:
    return {
        "source_read": {"shot_id": "shot-001"},
        "change_manifest": [],
        "success_criteria": [
            {
                "criterion_id": "motion_arc",
                "statement": "hand reaches clock face",
                "measurement_spec": {"method": "temporal_ioU"},
                "tolerances": {"min": 0.7},
            }
        ],
        "allowed_compromises": [{"criterion_id": "motion_arc", "budget": 0.5}],
        "hard_constraints": [],
        "escalation_threshold": 0.9,
        "deliverable_spec": {"medium": "video", "acceptance_bar": 0.7},
    }


def _rule_snapshot_body() -> dict:
    return {"rules": [], "source_ref": "methodology/v17"}


def _partial_fidelity_body(model_triple: dict) -> dict:
    return {
        "models": [
            {
                "backend_identity_triple": model_triple,
                "dimensions": [{"axis": "dynamic_range", "scalar": 0.2}],
            }
        ]
    }


async def _seed(session, *, model_triple: dict) -> dict:
    intent = await LockedIntentRepo(session).insert_if_absent(_locked_intent_body())
    rule = await RuleSnapshotRepo(session).insert_if_absent(_rule_snapshot_body())
    partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
        _partial_fidelity_body(model_triple)
    )
    run = await PipelineRunRepo(session).insert_if_absent(
        {"run_kind": "original", "intent_id": str(intent.id)}
    )
    return {
        "intent_id": intent.id,
        "rule_snapshot_id": rule.id,
        "partial_fidelity_snapshot_id": partial.id,
        "run_id": run.id,
    }


def _make_planner(session, tools: ToolRegistry) -> Planner:
    return Planner(
        session,
        tool_registry=tools,
        platform_uuid_registry=InMemoryPlatformUUIDRegistry(),
        trained_identity_registry=InMemoryTrainedIdentityRegistry(),
        lineage_graph=InMemoryLineageGraph(),
    )


def _plan_kwargs(ids: dict) -> dict:
    return {
        "intent_id": ids["intent_id"],
        "run_id": ids["run_id"],
        "rule_snapshot_id": ids["rule_snapshot_id"],
        "partial_fidelity_snapshot_id": ids["partial_fidelity_snapshot_id"],
    }


# ── (a) unit ──────────────────────────────────────────────────────────────────


async def test_pass1_sources_join_triple_from_typed_facts(session_factory) -> None:
    """When a sibling publishes generation_facts, pass_1 keys the snapshot off the
    TYPED backend_identity (all four fields), not the flat decoy key."""
    tools = ToolRegistry()
    tools.register(
        _generation_tool(
            _facts_metadata(typed_triple=_TYPED_TRIPLE, flat_triple=_FLAT_DECOY_TRIPLE)
        ),
        sibling_name="forge_generators",
    )
    async with session_factory() as session:
        ids = await _seed(session, model_triple=_TYPED_TRIPLE)
        plan = await _make_planner(session, tools).plan(**_plan_kwargs(ids))
        cap_id = plan.capability_snapshot_id
        assert cap_id is not None

        snapshot = await CapabilitySnapshotRepo(session).get_by_id(cap_id)
        await session.commit()

    entry = snapshot.attributes["snapshots"][0]
    # The typed source won — full four-field triple, not the flat decoy.
    assert entry["backend_identity_triple"] == _TYPED_TRIPLE
    assert entry["backend_identity_triple"] != _FLAT_DECOY_TRIPLE
    # And the join asserted on BackendIdentityTriple resolves to the typed backend.
    assert plan.refusal_code is None
    assert plan.operator_sequence[0]["backend_id"] == _TYPED_BACKEND_ID


async def test_pass1_degrades_on_malformed_facts_without_crashing(
    session_factory,
) -> None:
    """A present-but-malformed generation_facts payload makes from_metadata raise;
    _safe_generation_facts swallows it and falls back to the flat key — one bad
    declaration must not abort planning for every sibling."""
    tools = ToolRegistry()
    tools.register(
        _generation_tool(
            _facts_metadata(
                typed_triple=None, flat_triple=_FLAT_DECOY_TRIPLE, malformed=True
            )
        ),
        sibling_name="forge_generators",
    )
    flat_backend_id = "stale_flat.should_lose"
    async with session_factory() as session:
        ids = await _seed(session, model_triple=_FLAT_DECOY_TRIPLE)
        plan = await _make_planner(session, tools).plan(**_plan_kwargs(ids))
        cap_id = plan.capability_snapshot_id
        snapshot = await CapabilitySnapshotRepo(session).get_by_id(cap_id)
        await session.commit()

    entry = snapshot.attributes["snapshots"][0]
    assert entry["backend_identity_triple"] == _FLAT_DECOY_TRIPLE
    assert plan.refusal_code is None
    assert plan.operator_sequence[0]["backend_id"] == flat_backend_id


async def test_pass1_falls_back_when_no_facts_namespace(session_factory) -> None:
    """Off-namespace sibling (no generation_facts) keeps the pre-#24 behavior:
    the flat backend_identity_triple key is used. No regression."""
    tools = ToolRegistry()
    tools.register(
        _generation_tool(
            _facts_metadata(typed_triple=None, flat_triple=_FLAT_DECOY_TRIPLE)
        ),
        sibling_name="forge_generators",
    )
    async with session_factory() as session:
        ids = await _seed(session, model_triple=_FLAT_DECOY_TRIPLE)
        plan = await _make_planner(session, tools).plan(**_plan_kwargs(ids))
        snapshot = await CapabilitySnapshotRepo(session).get_by_id(
            plan.capability_snapshot_id
        )
        await session.commit()

    assert snapshot.attributes["snapshots"][0]["backend_identity_triple"] == (
        _FLAT_DECOY_TRIPLE
    )
    assert plan.operator_sequence[0]["backend_id"] == "stale_flat.should_lose"


# ── (b) stub-sibling through the real register_all_siblings path ───────────────


class _StubDriver:
    backend_id = "forge_generators.trellis2"
    backend_identity_triple = _TYPED_TRIPLE

    async def poll(self, artifact):  # required by _validate_generation_handler
        return None


def _install_module(name: str, register_fn) -> str:
    module = types.ModuleType(name)
    module.register_bridge_adapters = register_fn
    sys.modules[name] = module
    return f"{name}:register_bridge_adapters"


async def _events():
    events: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    return events, append


async def test_stub_sibling_round_trip_typed_join(session_factory) -> None:
    """A stub sibling publishes a contract-valid generation_facts declaration
    through the REAL register_all_siblings machinery; the planner selects the
    backend by the typed triple end-to-end. Proves the integration (a) can't, and
    doubles as the generators' conformance reference."""
    driver = _StubDriver()
    tools = ToolRegistry()

    def _capability() -> CapabilityRegistration:
        return CapabilityRegistration(
            declaration=CapabilityDeclaration(
                capability_id="forge_generators.test.trellis2",
                family="generation",
                owner="test-sibling",
                payload_family="generation_v1",
                input_schema={"type": "object"},
                metadata=_facts_metadata(
                    typed_triple=_TYPED_TRIPLE, flat_triple=_FLAT_DECOY_TRIPLE
                ),
            ),
            handler=driver,
        )

    async def register_bridge_adapters(ctx, register_capability):
        register_capability(_capability())

    target = _install_module(
        "tests.gen_facts_stub_sibling", register_bridge_adapters
    )
    events, append = await _events()
    outcome = await register_all_siblings(
        resolve_siblings(entry_points_loader=lambda _group: {"generator": target}),
        tool_registry=tools,
        event_appender=append,
        bridge_version="issue-24-test",
    )
    assert outcome.siblings_registered == 1
    assert [t.tool_id for t in tools.by_family("generation")] == [
        "forge_generators.test.trellis2"
    ]

    async with session_factory() as session:
        ids = await _seed(session, model_triple=_TYPED_TRIPLE)
        plan = await _make_planner(session, tools).plan(**_plan_kwargs(ids))
        await session.commit()

    assert plan.refusal_code is None
    assert plan.operator_sequence[0]["backend_id"] == _TYPED_BACKEND_ID
