"""#153 slice 1 — upstream-result VALUE → downstream tool KWARG binding.

The graph path used to build a tool-call node's kwargs from a *static parse of
its own step text* only. Legacy (`run_chain_steps`) additionally folds the
previous step's result VALUES into the call args at runtime (the
``extract_chain_context`` singleton-id forward). So on any chain where step N
inherits an id from step N-1's result (absent from N's own text) the two paths
built DIFFERENT args and a live graph run under-specified the tool.

Slice 1 binds the ``extract_chain_context`` singleton-id-forward case via a
compiler-authored ``ExtractContextNode`` + an edge-sourced *mechanical*
kwarg-merge on the MCP boundary (``.planning/CONVERGENCE-153-value-kwarg-binding.md``).

These tests pin, in order:
  1. PRECEDENCE (the one seam) — a step-text arg WINS over the inherited value,
     matching legacy's ``{**public_inherited, **static}`` fold order.
  2. PROBE — a 2-step chain where step 2 inherits a singleton id: graph-built
     args == legacy-built args (both carry the inherited id).
  3. STATIC regression — a fully-literal chain still builds identical args.
  4. A direct merge-precedence self-check on ``_node_arguments``.
"""
from __future__ import annotations

import time
import uuid
from types import SimpleNamespace

import pytest

from forge_bridge.composition.boundary import MCPToolBoundary, _node_arguments
from forge_bridge.composition.chain_compiler import compile_chain_steps
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.console._engine import run_chain_steps
from forge_bridge.graph.ports import PortContract


# ── Shared mock + tool schema (mirrors the corpus capture test) ─────────────


class _SequencedMCP:
    """Records call args and returns a programmed payload per call ordinal."""

    def __init__(self, payloads: list[dict]):
        self.payloads = list(payloads)
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return _tools()

    async def call_tool(self, name: str, arguments=None, *args, **kwargs):
        params = arguments if arguments is not None else (args[0] if args else {})
        self.calls.append((name, dict(params)))
        index = min(len(self.calls) - 1, len(self.payloads) - 1)
        return self.payloads[index]


def _tool(name: str):
    # No ``params`` property → ``normalize_tool_args`` leaves flat args flat, so
    # both paths call the tool with an identical flat kwargs dict.
    return SimpleNamespace(
        name=name,
        description="Test tool",
        annotations=SimpleNamespace(readOnlyHint=True),
        inputSchema={
            "type": "object",
            "properties": {
                "shot_id": {"type": "string"},
                "project_id": {"type": "string"},
                "clip_ref": {"type": "string"},
            },
            "required": [],
        },
    )


def _tools():
    return [_tool("forge_is_greenscreen")]


async def _legacy_calls(steps: list[str], payloads: list[dict]) -> list[tuple[str, dict]]:
    mcp = _SequencedMCP(payloads)
    body = await run_chain_steps(
        steps=steps,
        tools=_tools(),
        mcp=mcp,
        request_id="req-legacy",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    )
    assert body["status"] == "success", body
    return mcp.calls


async def _graph_calls(steps: list[str], payloads: list[dict]) -> list[tuple[str, dict]]:
    mcp = _SequencedMCP(payloads)
    graph = compile_chain_steps(steps)
    await GraphExecutor(
        UnifiedDispatch(mcp_boundary=MCPToolBoundary(mcp=mcp)).dispatch
    ).run(graph)
    return mcp.calls


# ── 1. PRECEDENCE (pin-before-wire) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_step_text_kwarg_wins_over_inherited_value():
    """Legacy folds inherited context UNDER static args; graph must match.

    Step 1 emits a singleton ``projects`` list (inherited ``project_id`` =
    ``p_inherited``); step 2's own text supplies ``project_id`` = ``p_literal``.
    Both paths must send the TEXT value.
    """
    steps = [
        "forge_is_greenscreen",
        'forge_is_greenscreen {"params": {"project_id": "p_literal"}}',
    ]
    payloads = [
        {"projects": [{"id": "p_inherited"}], "count": 1},
        {"is_greenscreen": True},
    ]

    legacy = await _legacy_calls(steps, payloads)
    graph = await _graph_calls(steps, payloads)

    assert legacy[1] == ("forge_is_greenscreen", {"project_id": "p_literal"})
    assert graph[1] == legacy[1]


# ── 2. PROBE — inherited singleton id forwards through the graph ─────────────


@pytest.mark.asyncio
async def test_inherited_singleton_shot_id_forwards_in_graph_like_legacy():
    """The #153 probe: step 2's text omits ``shot_id``; step 1 yields one shot."""
    steps = ["forge_is_greenscreen", "forge_is_greenscreen"]
    payloads = [
        {"shots": [{"id": "gs_777"}], "count": 1},
        {"is_greenscreen": True},
    ]

    legacy = await _legacy_calls(steps, payloads)
    graph = await _graph_calls(steps, payloads)

    # Both build step-1 args from text alone; step-2 inherits shot_id=gs_777.
    assert legacy[0] == ("forge_is_greenscreen", {})
    assert legacy[1] == ("forge_is_greenscreen", {"shot_id": "gs_777"})
    assert graph == legacy


# ── 3. STATIC regression — no qualifying singleton, args from text only ─────


@pytest.mark.asyncio
async def test_fully_static_chain_builds_identical_args_no_regression():
    """A chain with no inheritable singleton still matches legacy byte-for-byte."""
    steps = [
        'forge_is_greenscreen {"params": {"shot_id": "explicit_1", '
        '"clip_ref": "mock://a.mov"}}',
        'forge_is_greenscreen {"params": {"shot_id": "explicit_2", '
        '"clip_ref": "mock://b.mov"}}',
    ]
    # Step-1 result is a bare manifest (no projects/shots/versions list) → the
    # extractor emits {} → step 2 is purely text-driven.
    payloads = [
        {"is_greenscreen": True},
        {"is_greenscreen": False},
    ]

    legacy = await _legacy_calls(steps, payloads)
    graph = await _graph_calls(steps, payloads)

    assert legacy[1] == (
        "forge_is_greenscreen",
        {"shot_id": "explicit_2", "clip_ref": "mock://b.mov"},
    )
    assert graph == legacy


# ── 4. Merge-precedence self-check (the smallest thing that fails if it flips)


def test_node_arguments_merges_edge_scalars_under_static():
    """``_node_arguments`` = ``{**edge_scalars, **static}`` — static wins.

    If precedence ever flips to ``{**static, **edge_scalars}`` this fails.
    """
    node = NodeSpec(
        node_id="fig#1",
        operator_id="forge_is_greenscreen",
        input_ports={"inherited_kwargs": PortContract.any()},
        config={
            "arguments": {"shot_id": "static_wins", "clip_ref": "keep"},
            "kwarg_input_port": "inherited_kwargs",
        },
    )
    edge_result = NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output={"shot_id": "edge_loses", "project_id": "inherited_only"},
    )

    args = _node_arguments(node, {"inherited_kwargs": edge_result})

    assert args == {
        "shot_id": "static_wins",  # static beats the edge value
        "clip_ref": "keep",
        "project_id": "inherited_only",  # edge-only key still merges in
    }


def test_node_arguments_ignores_unnominated_edges():
    """Without a ``kwarg_input_port`` nomination, edges stay lineage-only."""
    node = NodeSpec(
        node_id="fig#1",
        operator_id="forge_is_greenscreen",
        input_ports={"input": PortContract.any()},
        config={"arguments": {"shot_id": "only_static"}},
    )
    lineage = NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output={"shots": [{"id": "should_not_leak"}]},
    )

    args = _node_arguments(node, {"input": lineage})

    assert args == {"shot_id": "only_static"}
