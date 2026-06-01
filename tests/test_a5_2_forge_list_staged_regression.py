"""A.5.2 regression coverage: forge_list_staged accepts {} on BOTH call sites.

The smoke-test masking finding from Phase A.5 explicitly noted: bug 2
(forced-tool wrapper schema mismatch) reproduced on **/api/v1/exec** as well
as **/api/v1/chat**. The migration that A.5.2 landed (Pattern C → Pattern B
for ``forge_list_staged`` in ``forge_bridge/console/resources.py``) must be
locked on BOTH surfaces. If only the chat path were tested, drift on the
deterministic path wouldn't surface until the next smoke pass.

These two tests exercise the REAL registered ``forge_list_staged`` (through
``register_console_resources``) — not the underlying ``_list_staged_impl``
directly — so a future revert of the closure signature in ``resources.py``
fails the test.

Static deliverables only:

  - ``tool_trace[0].error is None`` for the chat path (no Pydantic validation
    error escapes the forced-tool wrapper).
  - PR31 envelope ``status == "success"`` for the /api/v1/exec path.

Deferred (NOT this test, NOT this phase's claim of completion): end-to-end
Test 2 with ``final_text`` non-empty (i.e. "I asked for staged ops; the LLM
summarized them"). That requires LLM reachability and lives in the Phase
A.5 final smoke pass.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient


# ── Shared fixture: real FastMCP + register_console_resources ──────────────


@pytest.fixture(scope="module")
def real_mcp_with_staged():
    """Build a fresh FastMCP and register the staged-ops tools the way the
    daemon does. The ``forge_list_staged`` closure under test lives inside
    ``register_console_resources`` — using a real FastMCP + the real
    registration is what makes this a true regression test for the
    Pattern-B migration."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI
    from forge_bridge.console.resources import register_console_resources

    mcp = FastMCP("forge_a5_2_regression")

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    mock_log._storage_callback = None
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms)

    async def _empty_staged(**_kw):
        return [], 0
    api.get_staged_ops = _empty_staged   # type: ignore[assignment]
    api.get_staged_op = AsyncMock(return_value=None)  # type: ignore[assignment]

    register_console_resources(mcp, ms, api, session_factory=None)
    return mcp, api


# ── Path 1: chat handler PR20 short-circuit ────────────────────────────────


def test_a5_2_forge_list_staged_via_chat_pr20_short_circuit(real_mcp_with_staged):
    """When the message-narrower collapses ``"list staged operations"`` to
    a single survivor (``forge_list_staged``), the chat handler's PR20
    forced-execution path calls ``mcp.call_tool("forge_list_staged", {})``.
    Pre-A.5.2 that surfaced a Pydantic ``Field required [type=missing] params``
    error in the tool message body; post-migration it returns the canonical
    default-pagination envelope.

    Locks the chat short-circuit half of the masking-finding deliverable."""
    real_mcp, _ = real_mcp_with_staged

    from forge_bridge.console import _rate_limit
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

    _rate_limit._reset_for_tests()
    try:
        # Build a chat app whose router never fires (we want the PR20 forced
        # path, not the LLM loop).
        mock_router = MagicMock()
        mock_router.complete_with_tools = AsyncMock(return_value="UNREACHED")
        mock_router.system_prompt = "base"

        ms = ManifestService()
        mock_log = MagicMock()
        mock_log.snapshot.return_value = ([], 0)
        mock_log._storage_callback = None
        chat_api = ConsoleReadAPI(
            execution_log=mock_log,
            manifest_service=ms,
            llm_router=mock_router,
        )
        app = build_console_app(chat_api)

        async def fake_list_tools():
            # Surface forge_list_staged as a candidate alongside non-matching
            # tools so the narrower collapses to it for "staged" prompts.
            from mcp.types import Tool, ToolAnnotations
            return [
                Tool(
                    name="forge_list_staged",
                    description="list staged pipeline operations awaiting approval",
                    annotations=ToolAnnotations(readOnlyHint=True),
                    inputSchema={"type": "object", "properties": {}, "required": []},
                ),
                Tool(
                    name="flame_alpha",
                    description="alpha flame tool",
                    annotations=ToolAnnotations(readOnlyHint=True),
                    inputSchema={"type": "object", "properties": {}, "required": []},
                ),
                Tool(
                    name="flame_beta",
                    description="beta flame tool",
                    annotations=ToolAnnotations(readOnlyHint=True),
                    inputSchema={"type": "object", "properties": {}, "required": []},
                ),
                Tool(
                    name="synth_gamma",
                    description="gamma synth tool",
                    annotations=ToolAnnotations(readOnlyHint=True),
                    inputSchema={"type": "object", "properties": {}, "required": []},
                ),
            ]

        async def passthrough(tools):
            return tools

        async def real_call(name, arguments):
            # Route to the REAL registered forge_list_staged closure on the
            # real FastMCP — that's the migration site under test.
            return await real_mcp.call_tool(name, arguments)

        with patch(
            "forge_bridge.mcp.server.mcp.list_tools",
            new=AsyncMock(side_effect=fake_list_tools),
        ), patch(
            "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
            side_effect=passthrough,
        ), patch(
            "forge_bridge.mcp.server.mcp.call_tool",
            new=AsyncMock(side_effect=real_call),
        ):
            client = TestClient(app)
            r = client.post(
                "/api/v1/chat",
                json={"messages": [
                    {"role": "user", "content": "list staged operations"},
                ]},
            )

        assert r.status_code == 200, r.text
        body = r.json()

        # PR20 short-circuit fired (narrowed to a single tool).
        assert body["tool_forced"] is True
        assert body["tools_filtered"] == 1
        assert body["stop_reason"] == "tool_forced"

        # Tool was forge_list_staged.
        forced_call = body["messages"][1]["tool_calls"][0]
        assert forced_call["function"]["name"] == "forge_list_staged"

        # Static deliverable: tool_trace[0].error is None (no Pydantic error).
        trace = body["tool_trace"]
        assert len(trace) == 1, trace
        assert trace[0]["tool_name"] == "forge_list_staged"
        assert trace[0]["error"] is None, (
            f"A.5.2 regression: forge_list_staged forced-call surfaced an error: "
            f"{trace[0]['error']!r}"
        )

        # The tool message body MUST NOT contain a Pydantic validation-error
        # signature.
        tool_msg = body["messages"][-1]
        assert tool_msg["role"] == "tool"
        assert "validation error" not in tool_msg["content"].lower(), (
            f"A.5.2 regression: validation error escaped: {tool_msg['content']!r}"
        )
        assert "field required" not in tool_msg["content"].lower(), (
            f"A.5.2 regression: 'field required' escaped: {tool_msg['content']!r}"
        )

        # Canonical default-pagination envelope.
        payload = json.loads(tool_msg["content"])
        assert payload.get("data") == []
        assert payload.get("meta", {}).get("limit") == 50
        assert payload.get("meta", {}).get("offset") == 0
    finally:
        _rate_limit._reset_for_tests()


# ── Path 2: /api/v1/exec deterministic chain engine ────────────────────────


def test_a5_2_forge_list_staged_via_api_v1_exec_deterministic(real_mcp_with_staged):
    """The /api/v1/exec deterministic chain engine narrows on the same
    ``_tool_filter`` surface and ultimately calls ``mcp.call_tool(name, {})``
    with a no-arguments shape when the prompt collapses to a single tool
    with no extracted parameters. Pre-A.5.2 the same Pydantic
    ``Field required [type=missing] params`` error fired here; post-migration
    the PR31 envelope reports ``status == "success"``.

    Locks the deterministic-path half of the masking-finding deliverable —
    the bug A.5 explicitly noted reproduces on both surfaces."""
    real_mcp, _ = real_mcp_with_staged

    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    mock_log._storage_callback = None
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms)
    app = build_console_app(api)

    async def fake_list_tools():
        from mcp.types import Tool, ToolAnnotations
        return [
            Tool(
                name="forge_list_staged",
                description="list staged pipeline operations awaiting approval",
                annotations=ToolAnnotations(readOnlyHint=True),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="flame_alpha",
                description="alpha flame tool",
                annotations=ToolAnnotations(readOnlyHint=True),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="flame_beta",
                description="beta flame tool",
                annotations=ToolAnnotations(readOnlyHint=True),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
        ]

    async def passthrough(tools):
        return tools

    async def real_call(name, arguments):
        # Route to the REAL registered forge_list_staged closure on the
        # real FastMCP — that's the migration site under test.
        return await real_mcp.call_tool(name, arguments)

    call_mock = AsyncMock(side_effect=real_call)
    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(side_effect=fake_list_tools),
    ), patch(
        # _execute.py imports this lazily inside execute_command, so patch the
        # source module — patching the consumer module does nothing because
        # the binding is resolved at call time, not module-import time.
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        side_effect=passthrough,
    ), patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=call_mock,
    ):
        client = TestClient(app)
        r = client.post(
            "/api/v1/exec",
            json={"text": "list staged operations"},
        )

    assert r.status_code == 200, r.text
    envelope = r.json()

    # Static deliverable: PR31 envelope must report success, not a
    # CHAIN_STEP_FAILED with Pydantic ToolError.
    assert envelope.get("status") == "success", (
        f"A.5.2 regression on /api/v1/exec: status={envelope.get('status')!r}, "
        f"error={envelope.get('error')!r}"
    )
    chain = envelope.get("chain") or []
    assert len(chain) == 1, f"expected single-step chain, got: {chain!r}"
    step = chain[0]
    # Chain envelope shape (PR31): {"step": <input text>, "result": <tool output>}.
    # No tool_name field at the step level — the tool identity is verified via the
    # call_tool mock's call_args_list below. Result MUST be the canonical envelope.
    assert step.get("step") == "list staged operations", step
    assert step.get("result") == {
        "data": [],
        "meta": {"limit": 50, "offset": 0, "total": 0},
    }, f"unexpected result envelope: {step.get('result')!r}"

    # Confirm the engine actually called forge_list_staged with {} — the load-bearing
    # check that the deterministic path exercises the migrated registration, not
    # some other tool by coincidence.
    called_with = [
        (call.args[0], call.args[1]) for call in call_mock.call_args_list
    ]
    assert ("forge_list_staged", {}) in called_with, called_with

    # The step's serialized representation must NOT carry a Pydantic
    # validation-error string. (Belt-and-suspenders against future result-shape
    # changes that might pass the equality check above but smuggle errors.)
    serialized = json.dumps(step, default=str).lower()
    assert "validation error" not in serialized, (
        f"A.5.2 regression: validation error escaped on /api/v1/exec: {step!r}"
    )
    assert "field required" not in serialized, (
        f"A.5.2 regression: 'field required' escaped on /api/v1/exec: {step!r}"
    )
