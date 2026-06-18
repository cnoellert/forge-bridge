from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass, field

import pytest

import forge_bridge.composition.dispatch as dispatch_module
import forge_bridge.composition.executor as executor_module
from forge_bridge.composition.admission import AdmissionRejected
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult


@dataclass
class _SpyBoundary:
    status: str = "ok"
    calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        self.calls.append((node.operator_id, tuple(sorted(resolved_inputs))))
        return NodeResult(
            status=self.status,
            run_id=uuid.uuid4(),
            resolved_class=f"spy.{node.operator_id}",
        )


@pytest.mark.asyncio
async def test_unified_dispatch_routes_mcp_and_primitive_halves():
    mcp = _SpyBoundary()
    primitive = _SpyBoundary()
    dispatch = UnifiedDispatch(mcp_boundary=mcp, primitive_boundary=primitive)

    await dispatch.dispatch(NodeSpec(node_id="a", operator_id="forge_roto_ref"), {})
    await dispatch.dispatch(NodeSpec(node_id="b", operator_id="filter"), {})

    assert mcp.calls == [("forge_roto_ref", ())]
    assert primitive.calls == [("filter", ())]


@pytest.mark.asyncio
async def test_unified_dispatch_rejects_unknown_operator_before_fallback():
    mcp = _SpyBoundary()
    primitive = _SpyBoundary()
    dispatch = UnifiedDispatch(mcp_boundary=mcp, primitive_boundary=primitive)

    with pytest.raises(AdmissionRejected):
        await dispatch.dispatch(NodeSpec(node_id="x", operator_id="unknown_op"), {})

    assert mcp.calls == []
    assert primitive.calls == []


def test_dispatch_module_has_no_private_operator_vocabulary():
    source = inspect.getsource(dispatch_module)

    assert "forge_is_greenscreen" not in source
    assert "forge_roto_ref" not in source
    assert "filter\"" not in source
    assert "admit_operator" in source


def test_executor_stays_dispatch_injection_only():
    source = inspect.getsource(executor_module)

    assert "UnifiedDispatch" not in source
    assert "admit_operator" not in source
    assert "PrimitiveBoundary" not in source

