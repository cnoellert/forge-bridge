"""#168 — thread ``fitted_model_asset_id`` at the planner door.

The #160 revocation gate lives at the ``dispatch_envelope`` submit chokepoint and
already fires for direct (plan-free) callers (see ``test_fitted_model_gate.py``).
This file proves the *plan-driven* door: ``dispatch_plan`` now threads a plan
step's ``fitted_model_asset_id`` onto the ``InvocationEnvelope`` it authors, so
the same gate enforces for plan-driven dispatch.

Three proofs go end-to-end through ``dispatch_plan`` (NOT ``dispatch_envelope``):

  1. A plan step naming a REVOKED fitted-model refuses with ``model_revoked`` and
     NEVER reaches ``driver.submit`` (fail-closed).
  2. A plan step naming a LIVE (non-revoked) fitted-model clears the gate and
     reaches submit.
  3. A plan step WITHOUT the key no-ops the gate and dispatches — the
     no-regression default (envelope carries no model id → gate passes).

The model gate sits AFTER the GenerationGrant spend-gate, so each proof supplies
a ratified grant + a resolvable driver so dispatch reaches the model gate.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from forge_bridge.orchestration import DispatchResult, GenerationDriverRegistry, dispatch_plan
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo

# Reuse the seed/grant/driver helpers + backend triple from the gate proof so the
# planner-door proof shares the exact same fitted-model + grant + driver wiring.
from tests.test_fitted_model_gate import (
    _TRIPLE,
    _CountingDriver,
    _fitted_model,
    _ratified_grant,
)

pytestmark = pytest.mark.asyncio

# Registry keys drivers by ``backend_id_from_identity_triple`` = "surface.path".
_BACKEND_ID = f"{_TRIPLE['surface']}.{_TRIPLE['path']}"


def _registry() -> tuple[GenerationDriverRegistry, _CountingDriver]:
    driver = _CountingDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    return registry, driver


async def _events() -> tuple[list[tuple[str, dict]], Any]:
    log: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        log.append((event_type, payload))

    return log, append


async def _plan(session_factory, *, fitted_model_asset_id: uuid.UUID | None):
    """Insert a one-generation-step plan, optionally carrying the model id."""
    step: dict[str, Any] = {
        "operator_id": "generate_video_from_image",
        "backend_id": _BACKEND_ID,
        "inputs": [],
        "output_artifact_id": str(uuid.uuid4()),
    }
    if fitted_model_asset_id is not None:
        step["fitted_model_asset_id"] = str(fitted_model_asset_id)
    async with session_factory() as session:
        plan = await ExecutionPlanRepo(session).insert_if_absent(
            {
                "operator_sequence": [step],
                "backend_assignments": {"generate_video_from_image": _BACKEND_ID},
                "transforms_inserted": [],
                "external_uploads_required": [],
                "cost_estimate": {},
                "predicted_compromise_consumption": [],
                "provenance_obligations": [],
                "feasibility_verdict": "feasible",
                "feasibility_explanation": "",
                "refusal_code": None,
                "intent_id": str(uuid.uuid4()),
                "planner_version": "issue-168-test",
                "capability_snapshot_id": None,
                "rule_snapshot_id": str(uuid.uuid4()),
                "partial_fidelity_snapshot_id": str(uuid.uuid4()),
            }
        )
        await session.commit()
    return plan


async def test_plan_step_revoked_model_refuses_and_does_not_submit(session_factory):
    """A REVOKED model id on the plan step makes ``dispatch_plan`` refuse."""
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory, revoked=True)
    plan = await _plan(session_factory, fitted_model_asset_id=model_id)

    result = await dispatch_plan(
        plan,
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        grant_id=grant_id,
    )

    assert result.status == "refused"
    assert result.refusal_code == "model_revoked"
    assert driver.submits == []  # fail-closed — the threaded id reached the gate
    refusals = [p for n, p in log if n == "dispatch_model_refused"]
    assert len(refusals) == 1
    assert refusals[0]["refusal_code"] == "model_revoked"


async def test_plan_step_live_model_passes_gate_and_reaches_submit(session_factory):
    """A LIVE model id on the plan step clears the gate and submits."""
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    model_id = await _fitted_model(session_factory, revoked=False)
    plan = await _plan(session_factory, fitted_model_asset_id=model_id)

    result = await dispatch_plan(
        plan,
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        grant_id=grant_id,
    )

    assert result.status == "submitted"
    assert result.artifact_id is not None
    assert len(driver.submits) == 1
    # The threaded id survives onto the envelope the plan door authored.
    assert driver.submits[0].fitted_model_asset_id == str(model_id)
    assert [n for n, _ in log if n == "dispatch_model_refused"] == []


async def test_plan_step_without_model_id_noops_gate_and_submits(session_factory):
    """No key on the plan step → gate no-ops; plan-driven dispatch unchanged."""
    registry, driver = _registry()
    log, append = await _events()
    grant_id = await _ratified_grant(session_factory)
    plan = await _plan(session_factory, fitted_model_asset_id=None)

    result = await dispatch_plan(
        plan,
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=append,
        grant_id=grant_id,
    )

    assert result.status == "submitted"
    assert len(driver.submits) == 1
    assert driver.submits[0].fitted_model_asset_id is None
    assert [n for n, _ in log if n == "dispatch_model_refused"] == []
    assert isinstance(result, DispatchResult)
