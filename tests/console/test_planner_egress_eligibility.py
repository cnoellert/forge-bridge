"""#56 / #58 — format_result is evicted from the reads-planner palette.

#56 decision: the planner must not author a cloud-egress terminal into a local
sensitive read. `_narrate` already presents reads, and `format_result` ships a
condensed payload to the Anthropic cloud model (`sensitive=False`). The gate is a
POSITIVE egress annotation (`egress="cloud"`), not a name denylist or a
`readOnlyHint` flip — flipping `readOnlyHint` would be dual-use (the authority
gate at `_authority.py:20` and the explicit `-> format as email` deterministic
chain both read it).

#58 closes-with #56: the planner's missing-`data` defect (it emits
`format_result({'format':'table'})` and omits the required chain-ref `data` arg)
evaporates once `format_result` leaves the palette. The class only stays closed
while `format_result` remains the SOLE planner-eligible consumer of a `data`
chain-ref param — guarded below.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge_bridge.console._planner_front import (
    _inner_param_schema,
    _planner_eligible,
    _read_only_tools,
)


def _tool(name: str, **annotations) -> SimpleNamespace:
    return SimpleNamespace(name=name, annotations=SimpleNamespace(**annotations))


# ── #56: the egress eligibility predicate ─────────────────────────────────

def test_read_tool_without_egress_is_eligible():
    assert _planner_eligible(_tool("forge_list_shots", readOnlyHint=True)) is True


def test_read_tool_with_cloud_egress_is_excluded():
    # readOnlyHint=True alone is no longer sufficient — cloud egress evicts.
    assert _planner_eligible(
        _tool("format_result", readOnlyHint=True, egress="cloud")
    ) is False


def test_mutation_is_excluded():
    assert _planner_eligible(_tool("flame_rename_shots", readOnlyHint=False)) is False


def test_absent_annotations_is_excluded():
    assert _planner_eligible(SimpleNamespace(name="mystery")) is False


def test_non_cloud_egress_value_stays_eligible():
    # The gate is `egress != "cloud"`, not `egress is None` — a future non-cloud
    # egress value (e.g. local sidecar) must not be swept out.
    assert _planner_eligible(
        _tool("forge_export_local", readOnlyHint=True, egress="local")
    ) is True


def test_read_only_tools_filters_cloud_egress():
    tools = [
        _tool("forge_list_shots", readOnlyHint=True),
        _tool("format_result", readOnlyHint=True, egress="cloud"),
        _tool("flame_rename_shots", readOnlyHint=False),
    ]
    assert {t.name for t in _read_only_tools(tools)} == {"forge_list_shots"}


# ── #56 / #58: end-to-end over the live registry ──────────────────────────

@pytest.mark.asyncio
async def test_format_result_carries_cloud_egress_annotation():
    """The registration survives the list_tools round-trip (ToolAnnotations
    allows extra fields), so the planner gate actually sees egress=cloud."""
    from forge_bridge.mcp import server as s

    tools = await s.mcp.list_tools()
    fr = next((t for t in tools if t.name == "format_result"), None)
    assert fr is not None
    assert getattr(fr.annotations, "egress", None) == "cloud"


@pytest.mark.asyncio
async def test_format_result_not_in_live_planner_palette():
    from forge_bridge.mcp import server as s

    tools = await s.mcp.list_tools()
    eligible = {t.name for t in _read_only_tools(tools)}
    assert "format_result" not in eligible
    # Sanity: the gate did not nuke ordinary reads.
    assert any(name.startswith("forge_list") for name in eligible)


@pytest.mark.asyncio
async def test_58_class_closure_no_eligible_data_chainref_consumer():
    """#58 stays closed only while format_result is the SOLE planner-eligible
    tool with a `data` param. The `__previous_result__ -> data` injection is
    keyed on tool_name == 'format_result' (_step.py); any OTHER eligible tool
    with a `data` param would re-open the missing-chain-ref defect class. If
    this fails, a new read tool introduced a `data` arg — re-evaluate #58."""
    from forge_bridge.mcp import server as s

    tools = await s.mcp.list_tools()
    offenders = []
    for t in _read_only_tools(tools):
        inner = _inner_param_schema(t)
        if "data" in (inner.get("properties") or {}):
            offenders.append(t.name)
    assert offenders == [], (
        f"planner-eligible tools with a 'data' param re-open #58: {offenders}"
    )
