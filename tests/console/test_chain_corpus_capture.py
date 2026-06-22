from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from forge_bridge.chain_corpus import CAPTURE_DIR_ENV, CAPTURE_ENV, canonical_hash
from forge_bridge.chain_corpus.reader import read_compile_file, read_trace_file
from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.chain_compiler import compile_chain_steps
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.console._chat_compile import run_compile_branch
from forge_bridge.console._engine import run_chain_steps


class _FakeMCP:
    def __init__(self, payload):
        self.payloads = list(payload) if isinstance(payload, list) else [payload]
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return _tools()

    async def call_tool(self, name: str, arguments=None, *args, **kwargs):
        params = arguments if arguments is not None else (args[0] if args else {})
        self.calls.append((name, dict(params)))
        if name == "forge_is_greenscreen":
            index = min(len(self.calls) - 1, len(self.payloads) - 1)
            return self.payloads[index]
        raise AssertionError(name)


class _TraceReplayMCP:
    def __init__(self, trace_rows):
        self._rows = {
            (row["tool_name"], row["args_hash"]): row["result"]
            for row in trace_rows
        }
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return _tools()

    async def call_tool(self, name: str, arguments=None, *args, **kwargs):
        params = arguments if arguments is not None else (args[0] if args else {})
        self.calls.append((name, dict(params)))
        return self._rows[(name, canonical_hash(params))]


def _tool(name: str):
    return SimpleNamespace(
        name=name,
        description="Test tool",
        annotations=SimpleNamespace(readOnlyHint=True),
        inputSchema={
            "type": "object",
            "properties": {
                "shot_id": {"type": "string"},
                "clip_ref": {"type": "string"},
            },
            "required": ["shot_id", "clip_ref"],
        },
    )


def _tools():
    return [_tool("forge_is_greenscreen")]


_CAPTURE_STEP = (
    'forge_is_greenscreen {"params": {"shot_id": "gs_010", '
    '"clip_ref": "mock://gs.mov"}}'
)


@pytest.mark.asyncio
async def test_chain_corpus_capture_is_gate_off_by_default(tmp_path: Path):
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            return_value=[_CAPTURE_STEP]
        )
    )

    outcome = await run_compile_branch(
        router=router,
        user_prompt="is gs_010 greenscreen?",
        tools=_tools(),
        mcp=_FakeMCP({"shot_id": "gs_010", "is_greenscreen": True}),
        request_id="req-corpus-off",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    )

    assert outcome.regime == "compiled_non_mutating"
    assert list(tmp_path.glob("*.jsonl")) == []


@pytest.mark.asyncio
async def test_chain_corpus_captured_read_replays_legacy_and_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(CAPTURE_ENV, "1")
    monkeypatch.setenv(CAPTURE_DIR_ENV, str(tmp_path))
    payload = {"shot_id": "gs_010", "is_greenscreen": True}
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            return_value=[_CAPTURE_STEP]
        )
    )

    outcome = await run_compile_branch(
        router=router,
        user_prompt="is gs_010 greenscreen?",
        tools=_tools(),
        mcp=_FakeMCP(payload),
        request_id="req-corpus-on",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    )

    assert outcome.regime == "compiled_non_mutating"
    compile_rows = read_compile_file(next(tmp_path.glob("chain-compile-*.jsonl")))
    trace_rows = read_trace_file(next(tmp_path.glob("chain-trace-*.jsonl")))
    assert compile_rows[0]["request_id"] == "req-corpus-on"
    assert compile_rows[0]["chain_steps"] == outcome.steps
    assert compile_rows[0]["replayable"] is True
    assert trace_rows[0]["result"] == payload

    legacy_mcp = _TraceReplayMCP(trace_rows)
    legacy = await run_chain_steps(
        steps=compile_rows[0]["chain_steps"],
        tools=_tools(),
        mcp=legacy_mcp,
        request_id="req-corpus-legacy",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    )

    graph_mcp = _TraceReplayMCP(trace_rows)
    graph = compile_chain_steps(compile_rows[0]["chain_steps"])
    graph_results = await GraphExecutor(UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=graph_mcp),
    ).dispatch).run(graph)

    assert legacy["status"] == "success"
    assert legacy["chain"][0]["result"] == payload
    assert graph_results["forge_is_greenscreen#0"].status == "ok"
    assert graph_results["forge_is_greenscreen#0"].output == payload
    assert legacy_mcp.calls == graph_mcp.calls == [
        ("forge_is_greenscreen", {"shot_id": "gs_010", "clip_ref": "mock://gs.mov"})
    ]


@pytest.mark.asyncio
async def test_chain_corpus_collision_marks_compile_record_unreplayable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(CAPTURE_ENV, "1")
    monkeypatch.setenv(CAPTURE_DIR_ENV, str(tmp_path))
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[_CAPTURE_STEP, _CAPTURE_STEP])
    )

    outcome = await run_compile_branch(
        router=router,
        user_prompt="check gs_010 twice",
        tools=_tools(),
        mcp=_FakeMCP([
            {"shot_id": "gs_010", "is_greenscreen": True},
            {"shot_id": "gs_010", "is_greenscreen": False},
        ]),
        request_id="req-corpus-collision",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    )

    assert outcome.regime == "compiled_non_mutating"
    compile_rows = read_compile_file(next(tmp_path.glob("chain-compile-*.jsonl")))
    assert compile_rows[0]["replayable"] is False
