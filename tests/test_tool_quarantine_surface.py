"""Phase 10.1 quarantine-surface pinning test.

Locks the data contract: quarantined synthesized tools are REMOVED from the
ManifestService by the watcher's removal-mirror path (watcher.py:278-293)
after ProbationTracker.quarantine() (probation.py:71-88) moves the source
file and calls mcp.remove_tool(). Therefore ConsoleReadAPI.get_tools() never
surfaces a quarantined tool under the current read path.

This test is the Phase 10.1 contract lock. If a future refactor exposes
quarantined tools as a zombie category in the registry, Test 2 fails and
the Tools-view Status-chip design (Plan 10.1-03) must be re-planned to
include the `quarantined` chip variant.

Related: CONTEXT.md D-40, PATTERNS.md "No Analog Gap Flag".
"""
from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace

import pytest

from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI


@pytest.fixture
def ms() -> ManifestService:
    return ManifestService()


@pytest.fixture
def api(ms: ManifestService, monkeypatch) -> ConsoleReadAPI:
    # A bare ExecutionLog stand-in — get_tools() never touches it.
    from forge_bridge.learning.execution_log import ExecutionLog
    import forge_bridge.mcp.server as real_server
    from forge_bridge.console import _tool_filter

    # Bug C — get_tools() now sources from the live MCP registry. Bind the
    # MCP stub to the manifest so the test's ms.remove() (which simulates
    # the watcher's removal-mirror path) also drops the tool from the
    # registry — production quarantine removes from BOTH stores.
    async def _list_tools():
        return [SimpleNamespace(name=r.name) for r in ms.get_all()]

    async def _reach():
        return {"flame_bridge": True}

    monkeypatch.setattr(real_server, "mcp",
                        SimpleNamespace(list_tools=_list_tools))
    monkeypatch.setattr(_tool_filter, "_get_backend_reachability", _reach)

    return ConsoleReadAPI(
        execution_log=ExecutionLog(),
        manifest_service=ms,
    )


@pytest.fixture
def three_tools() -> list[ToolRecord]:
    return [
        ToolRecord(
            name="synth_active",
            origin="synthesized",
            namespace="synth",
            code_hash="a" * 64,
            observation_count=5,
        ),
        ToolRecord(
            name="synth_loaded",
            origin="synthesized",
            namespace="synth",
            code_hash="b" * 64,
            observation_count=0,
        ),
        ToolRecord(
            name="builtin_foo",
            origin="builtin",
            namespace="flame",
            observation_count=2,
        ),
    ]


async def test_get_tools_returns_all_registered(
    ms: ManifestService, api: ConsoleReadAPI, three_tools: list[ToolRecord]
) -> None:
    """Happy path: everything registered shows up in get_tools()."""
    for t in three_tools:
        await ms.register(t)
    result = await api.get_tools()
    assert [t.name for t in result] == [
        "synth_active",
        "synth_loaded",
        "builtin_foo",
    ]


async def test_quarantined_tool_is_not_in_get_tools(
    ms: ManifestService, api: ConsoleReadAPI, three_tools: list[ToolRecord]
) -> None:
    """The Phase 10.1 contract lock.

    Simulates the watcher's removal-mirror behavior (watcher.py:288) that
    fires after ProbationTracker.quarantine() runs: ms.remove(name) is
    called directly. After that call, get_tools() must not surface the
    removed tool under ANY circumstance.

    If this test ever fails, Plan 10.1-03's two-variant chip design is
    wrong and must be re-planned to include a `quarantined` chip variant.
    """
    for t in three_tools:
        await ms.register(t)
    # Simulate the quarantine path: watcher.py:278-293 does exactly this
    # after probation.py:71-88 moves the source file + removes MCP reg.
    await ms.remove("synth_loaded")
    result = await api.get_tools()
    names = [t.name for t in result]
    assert "synth_loaded" not in names, (
        "Quarantine contract broken: a tool removed from ManifestService "
        "must not appear in get_tools(). See Phase 10.1 CONTEXT D-40 and "
        "PATTERNS 'No Analog Gap Flag'. If this test is failing, the "
        "Tools-view Status-chip design must be re-planned to include the "
        "`quarantined` chip variant (currently dropped for this phase)."
    )
    assert names == ["synth_active", "builtin_foo"]


def test_tool_record_has_no_status_or_quarantined_field() -> None:
    """Self-audit: the frozen dataclass shape has no status-ish field.

    Phase 10.1 ships a template-only Status column. If a future phase adds
    a `quarantined` or `status` field to ToolRecord, this test fails to
    force a re-read of the chip-variant design before the new field
    silently changes the rendering contract.
    """
    field_names = {f.name for f in fields(ToolRecord)}
    assert "quarantined" not in field_names, (
        "ToolRecord gained a `quarantined` field; Plan 10.1-03 must be "
        "re-planned to include the quarantined chip variant."
    )
    assert "status" not in field_names, (
        "ToolRecord gained a `status` field; Plan 10.1-03 must be "
        "re-planned to read status from the record directly instead of "
        "deriving it in _filter_tools()."
    )


def test_derive_tool_status_active_for_synth_with_obs() -> None:
    """D-40: origin=synthesized AND code_hash AND obs>0 -> active."""
    from forge_bridge.console.ui_handlers import _derive_tool_status

    tool = ToolRecord(
        name="synth_a",
        origin="synthesized",
        namespace="synth",
        code_hash="a" * 64,
        observation_count=5,
    )
    assert _derive_tool_status(tool) == "active"


def test_derive_tool_status_loaded_for_synth_with_zero_obs() -> None:
    from forge_bridge.console.ui_handlers import _derive_tool_status

    tool = ToolRecord(
        name="synth_b",
        origin="synthesized",
        namespace="synth",
        code_hash="b" * 64,
        observation_count=0,
    )
    assert _derive_tool_status(tool) == "loaded"


def test_derive_tool_status_loaded_for_builtin() -> None:
    from forge_bridge.console.ui_handlers import _derive_tool_status

    tool = ToolRecord(
        name="flame_get_project",
        origin="builtin",
        namespace="flame",
        code_hash=None,
        observation_count=10,
    )
    assert _derive_tool_status(tool) == "loaded"


def test_derive_tool_status_loaded_for_synth_missing_code_hash() -> None:
    """Edge case: synth with missing code_hash falls to loaded (not active, not a new variant)."""
    from forge_bridge.console.ui_handlers import _derive_tool_status

    tool = ToolRecord(
        name="synth_c",
        origin="synthesized",
        namespace="synth",
        code_hash=None,
        observation_count=3,
    )
    assert _derive_tool_status(tool) == "loaded"
