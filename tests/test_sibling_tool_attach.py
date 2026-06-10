"""Federation tool-attach hook (issue #23).

`register_sibling_mcp_tools` invokes each sibling's
`<pkg>.bridge.registry:register_with(mcp)` so operators attach as forge_* MCP
tools. Per-sibling failures are isolated — one bad sibling must never break
bootstrap.
"""
from __future__ import annotations

from types import SimpleNamespace

from forge_bridge.orchestration.discovery import register_sibling_mcp_tools


def _loader(mapping):
    def loader(_group):
        return mapping
    return loader


def test_attaches_sibling_with_register_with() -> None:
    calls = []
    module = SimpleNamespace(register_with=lambda mcp: calls.append(mcp))
    mcp = object()

    status = register_sibling_mcp_tools(
        mcp,
        entry_points_loader=_loader(
            {"forge_vision": "forge_vision.bridge.contract_registry:register_bridge_adapters"}
        ),
        module_loader=lambda name: {"forge_vision.bridge.registry": module}[name],
    )

    assert status == {"forge_vision": "attached"}
    assert calls == [mcp]  # register_with received the live mcp instance


def test_skips_sibling_with_no_attach_module() -> None:
    def module_loader(name):
        raise ModuleNotFoundError(name)

    status = register_sibling_mcp_tools(
        object(),
        entry_points_loader=_loader(
            {"forge_pipeline": "forge_core.bridge.contract_registry:register_bridge_adapters"}
        ),
        module_loader=module_loader,
    )
    assert status == {"forge_pipeline": "no_register_with"}


def test_skips_module_without_register_with_attr() -> None:
    status = register_sibling_mcp_tools(
        object(),
        entry_points_loader=_loader({"x": "x.bridge.contract_registry:y"}),
        module_loader=lambda name: SimpleNamespace(),  # no register_with
    )
    assert status == {"x": "no_register_with"}


def test_one_throwing_sibling_does_not_break_the_others() -> None:
    good_calls = []
    modules = {
        "bad.bridge.registry": SimpleNamespace(
            register_with=lambda mcp: (_ for _ in ()).throw(RuntimeError("boom"))
        ),
        "good.bridge.registry": SimpleNamespace(
            register_with=lambda mcp: good_calls.append(mcp)
        ),
    }
    mcp = object()

    status = register_sibling_mcp_tools(
        mcp,
        entry_points_loader=_loader(
            {
                "bad": "bad.bridge.contract_registry:r",
                "good": "good.bridge.contract_registry:r",
            }
        ),
        module_loader=lambda name: modules[name],
    )

    assert status == {"bad": "error", "good": "attached"}
    assert good_calls == [mcp]  # isolation: the good sibling still attached
