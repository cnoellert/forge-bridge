"""#67 — sibling-attached in-process ops survive the Flame-reachability filter.

The chat/exec reachability filter dropped `forge_*` sibling ops (forge-vision's
`forge_assess_drift`, …) whenever Flame (:9999) was down, because in-process-ness
was inferred from a `forge_` prefix + a 7-name hardcoded allowlist. These ops run
in the bridge process and need no Flame. Fix: bridge captures sibling-attached
names at the `register_sibling_mcp_tools` boundary and the filter consults them.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import forge_bridge.console._tool_filter as tf
from forge_bridge.orchestration import discovery as d


def _tool(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


@pytest.fixture(autouse=True)
def _clean_sibling_set():
    tf._SIBLING_IN_PROCESS_TOOLS.clear()
    yield
    tf._SIBLING_IN_PROCESS_TOOLS.clear()


_FLAME_DOWN = AsyncMock(return_value={"flame_bridge": False})
_FLAME_UP = AsyncMock(return_value={"flame_bridge": True})


@pytest.mark.asyncio
async def test_registered_sibling_op_survives_flame_down():
    tf.register_sibling_in_process_tools({"forge_assess_drift", "forge_classify_shot"})
    tools = [
        _tool("forge_assess_drift"),    # sibling in-process -> survives
        _tool("forge_tools_read"),      # hardcoded in-process 7 -> survives
        _tool("forge_list_projects"),   # flame-backed forge_* -> dropped
        _tool("flame_ping"),            # flame_* -> dropped
    ]
    with patch.object(tf, "_get_backend_reachability", new=_FLAME_DOWN):
        survivors = {t.name for t in await tf.filter_tools_by_reachable_backends(tools)}

    assert "forge_assess_drift" in survivors
    assert "forge_tools_read" in survivors
    assert "forge_list_projects" not in survivors
    assert "flame_ping" not in survivors


@pytest.mark.asyncio
async def test_unregistered_sibling_op_still_dropped_flame_down():
    # Load-bearing guard: WITHOUT registration the op is dropped — proves the
    # fix is the registration, not a no-op that always lets forge_* through.
    tools = [_tool("forge_assess_drift")]
    with patch.object(tf, "_get_backend_reachability", new=_FLAME_DOWN):
        survivors = {t.name for t in await tf.filter_tools_by_reachable_backends(tools)}
    assert survivors == set()


@pytest.mark.asyncio
async def test_no_regression_when_flame_up():
    tf.register_sibling_in_process_tools({"forge_assess_drift"})
    tools = [
        _tool("forge_assess_drift"),
        _tool("forge_list_projects"),
        _tool("flame_ping"),
    ]
    with patch.object(tf, "_get_backend_reachability", new=_FLAME_UP):
        survivors = {t.name for t in await tf.filter_tools_by_reachable_backends(tools)}
    assert survivors == {"forge_assess_drift", "forge_list_projects", "flame_ping"}


def test_register_sibling_mcp_tools_captures_attached_names():
    """The attach boundary records the names each sibling's register_with adds,
    via a sync before/after delta over the FastMCP tool manager."""

    class _ToolManager:
        def __init__(self) -> None:
            self._tools: dict[str, object] = {
                "flame_ping": object(),  # pre-existing builtin
            }

        def list_tools(self):
            return [SimpleNamespace(name=n) for n in self._tools]

    class _MCP:
        def __init__(self) -> None:
            self._tool_manager = _ToolManager()

    mcp = _MCP()

    def _register_with(m):
        m._tool_manager._tools["forge_fake_op"] = object()

    fake_module = SimpleNamespace(register_with=_register_with)

    status = d.register_sibling_mcp_tools(
        mcp,
        entry_points_loader=lambda _g: {
            "fakesib": "fake_pkg.bridge.contract_registry:register_bridge_adapters",
        },
        module_loader=lambda _name: fake_module,
    )

    assert status == {"fakesib": "attached"}
    attached = d.attached_sibling_tool_names()
    assert "forge_fake_op" in attached      # newly attached -> captured
    assert "flame_ping" not in attached     # pre-existing -> not in the delta
