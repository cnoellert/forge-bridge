"""Live sibling-discovery smoke test (Phase-6A Bridge Discovery proof).

Unlike ``test_sibling_registration.py`` (mock siblings), this exercises bridge's
discovery against the REAL ``forge_bridge.siblings`` entry points installed in the
environment. It is the permanent home of the **Pipeline-mandatory guard**: a proof
that admits only Vision (``perception``) and silently omits Pipeline (``execution``)
would mask the execution gap, so the test requires BOTH primaries.

Env-dependent by nature: it auto-skips when the mandatory pair isn't installed (no
single env is guaranteed to carry all siblings current — see
PHASE-6A-DISCOVERY-ALIGNMENT.md). When the siblings ARE discoverable, it must pass.
"""

from __future__ import annotations

import pytest

from forge_bridge.orchestration.discovery import (
    register_all_siblings,
    resolve_siblings,
)
from forge_bridge.orchestration.registration import ToolRegistry

_EXECUTION_CAPABILITY_ID = "forge_pipeline.execution.dispatch"


async def _discover() -> tuple[ToolRegistry, frozenset[str]]:
    """Run live discovery (request-all) and return the registry + families seen."""
    resolution = resolve_siblings()
    registry = ToolRegistry()

    async def _appender(_kind, _payload):  # event sink, no DB
        return None

    outcome = await register_all_siblings(
        resolution,
        tool_registry=registry,
        event_appender=_appender,
        bridge_version="test",
        requested_families=frozenset(),  # request-all + classify
    )
    return registry, outcome.capability_kinds_present


async def test_live_discovery_mandatory_pair() -> None:
    """Bridge discovers Vision (perception) AND Pipeline (execution) live, and the
    capability query for ``execution`` resolves to the Pipeline dispatch id."""
    registry, families = await _discover()

    if "perception" not in families or "execution" not in families:
        pytest.skip(
            "mandatory sibling pair not installed in this interpreter "
            f"(families present: {sorted(families)}); "
            "install forge-vision + forge-pipeline to exercise the live proof"
        )

    # Pipeline-mandatory guard: execution must be satisfied by the Pipeline dispatch.
    execution = registry.by_family("execution")
    assert any(t.tool_id == _EXECUTION_CAPABILITY_ID for t in execution), (
        f"execution family present but {_EXECUTION_CAPABILITY_ID} not among "
        f"{[t.tool_id for t in execution]}"
    )

    # Declaration-first (rung 2A): the stored record is invocation-free — the
    # handler/driver binding is decomposed out of the record entirely (routed to
    # its binding home at register time), so no record carries a handler field.
    assert all(not hasattr(t, "handler") for t in registry.all()), (
        "discovery records must be declaration-only (no handler stored on the record)"
    )
