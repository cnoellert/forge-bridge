"""PR22 — Tool Contract Normalization (Pydantic v2 fix).

Pydantic v2 makes ``Optional[X]`` still REQUIRED unless an explicit
``= None`` default is supplied. Tools whose handler signature was
``params: SomeInput`` (no default) therefore raised
``"Field required [type=missing]"`` when invoked with ``{}`` — the exact
shape PR20 forced execution sends. PR22 closes this so the deterministic
single-tool path never surfaces a Pydantic validation error.

Scope (per the brief): the three tools that PR21 narrowing routinely
collapses to as a single survivor — ``forge_list_projects`` (no params,
already safe), ``forge_list_shots`` and ``forge_list_versions``
(required ``project_id`` business field). The latter two get an explicit
``Optional[...] = None`` on the handler signature plus a graceful
structured-error path for the ``params is None`` case so the chat handler
renders a friendly tool message instead of a Pydantic stack trace.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import typing
from typing import Optional, Union, get_args, get_origin

import pytest

# The three tools the brief explicitly names. forge_list_projects already
# takes no params (no fix needed); the other two must accept {} after PR22.
PR22_TOOLS_UNDER_CONTRACT = (
    "list_projects",
    "list_shots",
    "list_versions",
)


# ── Schema invariant: handler signature has Optional[X] = None default ──────


def _accepts_none(handler) -> bool:
    """True iff the handler's `params` argument has a None default and an
    Optional/Union-with-None type annotation, i.e., calling the handler
    with no arguments is legal under Pydantic v2.

    The handler module uses ``from __future__ import annotations`` so
    annotations are stored as strings — resolve them with
    ``typing.get_type_hints``, then inspect the resolved Union form."""
    sig = inspect.signature(handler)
    if "params" not in sig.parameters:
        # No `params` at all — handler is trivially safe (e.g. list_projects).
        return True
    param = sig.parameters["params"]
    if param.default is not None:
        return False
    try:
        hints = typing.get_type_hints(handler)
    except Exception:
        return False
    ann = hints.get("params")
    if ann is None:
        # No resolvable annotation — empty default already accepted above.
        return True
    origin = get_origin(ann)
    # Optional[X] / Union[X, None] / X | None all expose None in get_args.
    return origin is Union and type(None) in get_args(ann)


@pytest.mark.parametrize("tool_attr", PR22_TOOLS_UNDER_CONTRACT)
def test_pr22_handler_signature_accepts_empty_args(tool_attr):
    """Handler's `params` argument MUST have ``= None`` default (or no
    `params` argument at all). Without this, Pydantic v2 builds a
    Tool ``Arguments`` model that requires `params`, and forced execution
    with ``{}`` raises ``Field required``."""
    from forge_bridge.mcp import tools as mcp_tools

    handler = getattr(mcp_tools, tool_attr)
    assert _accepts_none(handler), (
        f"PR22: tool handler {tool_attr!r} must accept calls with no args. "
        f"Add ``params: Optional[X] = None`` to the signature."
    )


# ── Runtime invariant: every tool returns a string (no raise) on {} ────────


@pytest.mark.parametrize("tool_attr", PR22_TOOLS_UNDER_CONTRACT)
def test_pr22_handler_does_not_raise_on_empty_call(tool_attr):
    """Calling the handler with no args must not raise. Tools that need
    business fields (project_id) return a structured ``_err()`` message
    instead — same shape ``fbridge run`` produces."""
    from forge_bridge.mcp import tools as mcp_tools

    handler = getattr(mcp_tools, tool_attr)
    # Async handlers — drive them on a private loop so the test stays sync.
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(handler())
    finally:
        loop.close()
    # Every tool returns a string (json.dumps payload).
    assert isinstance(result, str)
    # No Pydantic validation error in the payload.
    assert "validation error" not in result.lower(), (
        f"PR22: handler {tool_attr!r} surfaced a validation error: {result}"
    )


def test_pr22_list_versions_missing_project_id_returns_structured_error():
    """When invoked without project_id, list_versions returns a structured
    `_err()` message naming the missing field — NOT a Pydantic stack trace."""
    from forge_bridge.mcp.tools import list_versions

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(list_versions())
    finally:
        loop.close()
    payload = json.loads(result)
    assert "error" in payload, payload
    assert "project_id" in payload["error"].lower()
    assert payload.get("code") == "MISSING_PROJECT_ID"


def test_pr22_list_shots_missing_project_id_returns_structured_error():
    """Same contract for list_shots."""
    from forge_bridge.mcp.tools import list_shots

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(list_shots())
    finally:
        loop.close()
    payload = json.loads(result)
    assert "error" in payload, payload
    assert "project_id" in payload["error"].lower()
    assert payload.get("code") == "MISSING_PROJECT_ID"


def test_pr22_list_projects_takes_no_params_so_call_with_empty_succeeds():
    """list_projects has no params at all — call with empty dict must
    succeed up to the point of needing the WS bridge. Asserts only that
    no Pydantic validation fires (any downstream connection error is OK
    for this contract test)."""
    from forge_bridge.mcp.tools import list_projects

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(list_projects())
    finally:
        loop.close()
    assert isinstance(result, str)
    # No validation-error noise.
    assert "validation error" not in result.lower()


# ── Pydantic schema check: Arguments model must accept {} ──────────────────


@pytest.mark.parametrize("tool_attr", PR22_TOOLS_UNDER_CONTRACT)
def test_pr22_pydantic_arguments_model_accepts_empty_dict(tool_attr):
    """Build a TypeAdapter over the handler's resolved params annotation
    and validate ``None`` — this proves the type allows the absence of
    `params` at the Pydantic layer (the FastMCP Arguments model wraps
    the handler signature and inherits its required/optional contract).
    Pre-PR22 this raised ``Field required`` for handlers whose `params`
    lacked a ``= None`` default."""
    from pydantic import TypeAdapter
    from forge_bridge.mcp import tools as mcp_tools

    handler = getattr(mcp_tools, tool_attr)
    sig = inspect.signature(handler)
    if "params" not in sig.parameters:
        return
    # `from __future__ import annotations` stringifies annotations —
    # resolve them through get_type_hints (with the tools module's
    # namespace) before handing to TypeAdapter.
    hints = typing.get_type_hints(handler)
    ann = hints["params"]
    adapter = TypeAdapter(ann)
    out = adapter.validate_python(None)
    assert out is None


# ── End-to-end: PR20 forced execution surfaces no validation-error string ──


def _make_chat_app():
    """Build a chat app + multi-tool registry where ``"fetch versions"``
    narrows to forge_list_versions and triggers PR20 forced execution."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from mcp.types import Tool

    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="UNREACHED")
    mock_router.system_prompt = "base"

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,
    )
    app = build_console_app(api)

    def _make_tool(name):
        return Tool(
            name=name,
            description=f"{name} description",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )

    multi_tools = [
        _make_tool("forge_list_versions"),
        _make_tool("flame_alpha"),
        _make_tool("flame_beta"),
        _make_tool("synth_gamma"),
    ]
    return app, multi_tools, mock_router


def test_pr22_chat_forced_execution_no_validation_error_in_message():
    """End-to-end (PR22 AC1): ``fbridge chat "fetch versions"`` →
    tool_forced=True, tools_filtered==1, and the tool message body must
    NOT contain the substring ``"validation error"``. Pre-PR22 the
    message body said ``"Field required [type=missing]"`` because
    ``list_versions``'s `params` lacked a None default."""
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from forge_bridge.console import _rate_limit
    from forge_bridge.mcp import tools as mcp_tools

    _rate_limit._reset_for_tests()
    try:
        app, multi_tools, mock_router = _make_chat_app()

        async def fake_call_tool(name, arguments):
            # Route forge_list_versions through the REAL handler so the
            # actual PR22 fix is exercised. Other tools return placeholder.
            if name == "forge_list_versions":
                return [type("X", (), {"text": await mcp_tools.list_versions()})()]
            return [type("X", (), {"text": f"{name}-result"})()]

        async def passthrough(tools):
            return tools

        with patch(
            "forge_bridge.mcp.server.mcp.list_tools",
            new=AsyncMock(return_value=multi_tools),
        ), patch(
            "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
            side_effect=passthrough,
        ), patch(
            "forge_bridge.mcp.server.mcp.call_tool",
            new=AsyncMock(side_effect=fake_call_tool),
        ):
            client = TestClient(app)
            r = client.post(
                "/api/v1/chat",
                json={"messages": [
                    {"role": "user", "content": "forge fetch versions"},
                ]},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        # PR20/PR21 invariants from PR21.1 still hold.
        assert body["tool_forced"] is True
        assert body["tools_filtered"] == 1
        assert body["tool_enforced"] is True
        assert body["stop_reason"] == "tool_forced"
        # PR22 contract: no validation-error string in the tool reply.
        tool_msg = body["messages"][-1]
        assert tool_msg["role"] == "tool"
        assert tool_msg["name"] == "forge_list_versions"
        assert "validation error" not in tool_msg["content"].lower(), (
            f"PR22 AC1: tool message surfaced a validation error: "
            f"{tool_msg['content']!r}"
        )
        # The graceful structured-error path fired instead.
        payload = json.loads(tool_msg["content"])
        assert payload.get("code") == "MISSING_PROJECT_ID"
    finally:
        _rate_limit._reset_for_tests()


# ── No-regression guards (PR14..PR21 chain still intact) ───────────────────


def test_pr22_serializer_handles_fastmcp_tuple_shape():
    """FastMCP `call_tool(..., convert_result=True)` returns a 2-tuple
    ``(content_blocks, {"result": "<stringified payload>"})``. The
    chat-handler serializer must extract the structured `result` string
    rather than dumping the whole tuple/list repr (the bug visible in the
    first PR22 live-verify run)."""
    from mcp.types import TextContent

    from forge_bridge.console.handlers import _serialize_forced_tool_result

    payload = '{"error": "project_id is required.", "code": "MISSING_PROJECT_ID"}'
    blocks = [TextContent(type="text", text=payload)]
    raw = (blocks, {"result": payload})
    out = _serialize_forced_tool_result(raw)
    assert out == payload, (
        f"PR22: serializer must return the structured payload string, got {out!r}"
    )
    # No leaky type repr.
    assert "TextContent(" not in out
    assert "{'result':" not in out


def test_pr22_serializer_falls_back_to_block_text_when_no_structured_result():
    """If the structured slot of the tuple is empty/None, the serializer
    falls back to extracting text from the content blocks."""
    from mcp.types import TextContent

    from forge_bridge.console.handlers import _serialize_forced_tool_result

    blocks = [TextContent(type="text", text="hello")]
    raw = (blocks, None)  # no structured result
    out = _serialize_forced_tool_result(raw)
    assert out == "hello"


def test_pr22_serializer_handles_bare_dict_with_result_key():
    """Forward-compat: if FastMCP ever passes the bare dict (no tuple),
    the serializer still extracts `result` correctly."""
    from forge_bridge.console.handlers import _serialize_forced_tool_result

    out = _serialize_forced_tool_result({"result": "x"})
    assert out == "x"


def test_pr22_no_regression_pr20_forced_execution_still_fires():
    """The chain PR14→PR19→PR21→PR20 still routes ``"forge fetch versions"``
    to forced execution. PR22 only changes the tool's response shape; the
    handler's narrow→force path is unaffected."""
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from forge_bridge.console import _rate_limit
    _rate_limit._reset_for_tests()
    try:
        app, multi_tools, mock_router = _make_chat_app()

        async def fake_call_tool(name, arguments):
            return [type("X", (), {"text": "ok"})()]

        async def passthrough(tools):
            return tools

        with patch(
            "forge_bridge.mcp.server.mcp.list_tools",
            new=AsyncMock(return_value=multi_tools),
        ), patch(
            "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
            side_effect=passthrough,
        ), patch(
            "forge_bridge.mcp.server.mcp.call_tool",
            new=AsyncMock(side_effect=fake_call_tool),
        ) as call_mock:
            client = TestClient(app)
            r = client.post(
                "/api/v1/chat",
                json={"messages": [
                    {"role": "user", "content": "forge fetch versions"},
                ]},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["tool_forced"] is True
        assert body["stop_reason"] == "tool_forced"
        mock_router.complete_with_tools.assert_not_called()
        call_mock.assert_called_once_with("forge_list_versions", {})
    finally:
        _rate_limit._reset_for_tests()
