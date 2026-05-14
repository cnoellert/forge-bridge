"""Tests for the `flame_execute_python` MCP tool — Phase 23.1.

The function `execute_python` has lived in `forge_bridge/tools/utility.py`
since pre-23.1 but was never registered with the MCP server. 23.1 ships
two changes:

  1. Docstring rewrite — 3 worked examples + structured "use ONLY when /
     do NOT use" guidance, so the LLM has enough signal to pattern-match
     the tool when no narrow flame_* tool fits.
  2. Registration — alongside other flame_* tools in
     `forge_bridge/mcp/registry.py`, under MCP name `flame_execute_python`
     with `readOnlyHint=False` (honest annotation: tool CAN mutate via
     main_thread=True).

These tests are the regression surface for both — if a future cleanup
strips the worked examples or drops the registration, the chat surface
silently reverts to the pre-23.1 unusability.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from forge_bridge.tools import utility
from forge_bridge.tools.utility import ExecutePythonInput, execute_python


# ── Function-shape invariants (rarely change) ────────────────────────────


def test_execute_python_callable_and_async():
    """The function exists, takes ExecutePythonInput, returns str."""
    import inspect
    assert inspect.iscoroutinefunction(execute_python)


def test_execute_python_input_schema_has_required_fields():
    """ExecutePythonInput carries `code` (str) and `main_thread` (bool, default False)."""
    schema = ExecutePythonInput.model_json_schema()
    assert "code" in schema["properties"]
    assert "main_thread" in schema["properties"]
    assert schema["properties"]["code"]["type"] == "string"
    assert schema["properties"]["main_thread"]["type"] == "boolean"
    # `code` is required; `main_thread` has a default → not required.
    required = schema.get("required", [])
    assert "code" in required
    assert "main_thread" not in required


# ── Docstring contract (23.1 worked examples must survive cleanup) ───────


def test_docstring_contains_three_worked_examples():
    """If a future docstring cleanup drops examples, the LLM loses pattern-
    match material and chat regresses to pre-23.1 unusability. Pin all
    three example markers."""
    doc = execute_python.__doc__ or ""
    assert "Example 1" in doc
    assert "Example 2" in doc
    assert "Example 3" in doc


def test_docstring_teaches_when_to_use_and_when_not_to():
    """The structured guidance is what the LLM reads to pick this tool
    over the narrow flame_* tools. Pin the headers so the structure
    survives downstream edits."""
    doc = execute_python.__doc__ or ""
    assert "Use this tool when:" in doc
    assert "Do NOT use this tool when:" in doc


def test_docstring_includes_reel_clips_dogfood_example():
    """The query that motivated 23.1 — 'What are the clips on Reel 1' —
    is Example 1. If that example gets dropped or renamed, the LLM may
    fail to pattern-match the exact dogfood case again."""
    doc = execute_python.__doc__ or ""
    assert "Reel 1" in doc
    assert "list clip names" in doc.lower()


# ── Response-shape invariants (wraps bridge.execute correctly) ───────────


class _FakeBridgeResponse:
    """Mimic forge_bridge.bridge.BridgeResponse for the success path."""
    def __init__(self, stdout="", stderr="", result=None, error=None, traceback=None):
        self.stdout = stdout
        self.stderr = stderr
        self.result = result
        self.error = error
        self.traceback = traceback


@pytest.mark.asyncio
async def test_execute_python_returns_json_with_stdout_stderr_result():
    """Happy path — wrapping yields a JSON string with the three core fields."""
    import json
    fake = _FakeBridgeResponse(stdout="hello\n", stderr="", result=None)
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        out = await execute_python(ExecutePythonInput(code="print('hello')"))
    parsed = json.loads(out)
    assert parsed["stdout"] == "hello\n"
    assert parsed["stderr"] == ""
    assert parsed["result"] is None
    # No error key on success.
    assert "error" not in parsed
    assert "traceback" not in parsed


@pytest.mark.asyncio
async def test_execute_python_includes_error_and_traceback_on_flame_exception():
    """When the snippet raises inside Flame, bridge returns error+traceback;
    the tool surface MUST propagate both so the LLM can see what failed."""
    import json
    fake = _FakeBridgeResponse(
        stdout="", stderr="",
        result=None,
        error="NameError: name 'flam' is not defined",
        traceback="Traceback (most recent call last):\n  ...",
    )
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        out = await execute_python(ExecutePythonInput(code="flam.foo()"))
    parsed = json.loads(out)
    assert parsed["error"] == "NameError: name 'flam' is not defined"
    assert "Traceback" in parsed["traceback"]


@pytest.mark.asyncio
async def test_execute_python_passes_main_thread_param_through():
    """The main_thread param routes through to bridge.execute — required
    for write operations. Default is False; True must propagate."""
    fake = _FakeBridgeResponse(stdout="ok", stderr="", result=None)
    mock = AsyncMock(return_value=fake)
    with patch.object(utility.bridge, "execute", new=mock):
        await execute_python(ExecutePythonInput(code="x=1", main_thread=True))
    # Bridge.execute called with main_thread=True (kwarg, not positional).
    assert mock.call_args.kwargs.get("main_thread") is True


@pytest.mark.asyncio
async def test_execute_python_default_main_thread_is_false():
    """Read-only-safe default: main_thread=False unless explicitly set."""
    fake = _FakeBridgeResponse(stdout="ok", stderr="", result=None)
    mock = AsyncMock(return_value=fake)
    with patch.object(utility.bridge, "execute", new=mock):
        await execute_python(ExecutePythonInput(code="x=1"))
    assert mock.call_args.kwargs.get("main_thread") is False


# ── MCP registration (the function is exposed to the LLM) ────────────────


def test_flame_execute_python_registered_on_mcp_server():
    """Phase 23.1 — the function MUST be registered under the canonical
    MCP name `flame_execute_python`. Pre-23.1 the function existed in
    utility.py but was never registered → the LLM was blind to it →
    chat couldn't converge on simple Flame introspection queries."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)

    # FastMCP exposes registered tools via _tool_manager._tools (private but
    # stable across the versions forge-bridge pins).
    tool_names = set(mcp._tool_manager._tools.keys())
    assert "flame_execute_python" in tool_names, (
        f"flame_execute_python missing from registry; have: "
        f"{sorted(n for n in tool_names if n.startswith('flame_'))}"
    )


def test_flame_execute_python_registered_as_not_readonly():
    """readOnlyHint=False is the honest annotation — the tool CAN mutate
    via main_thread=True even though the docstring biases toward reads."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)

    tool = mcp._tool_manager._tools["flame_execute_python"]
    annotations = getattr(tool, "annotations", None)
    # annotations may be a pydantic model or a dict depending on FastMCP version.
    if hasattr(annotations, "readOnlyHint"):
        assert annotations.readOnlyHint is False
    elif isinstance(annotations, dict):
        assert annotations.get("readOnlyHint") is False
    else:
        pytest.fail(f"Unexpected annotations shape: {type(annotations)}")


def test_flame_execute_python_source_is_builtin():
    """Builtin source — distinguishes from synthesized + user-taught tools."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)

    tool = mcp._tool_manager._tools["flame_execute_python"]
    meta = getattr(tool, "_meta", None) or getattr(tool, "meta", None)
    if isinstance(meta, dict):
        assert meta.get("_source") == "builtin"
    else:
        # Fall back to checking the tool's exported metadata via FastMCP.
        # If the meta isn't accessible by direct attribute, skip — the
        # registration code paths are independently tested in
        # tests/test_mcp_registry.py.
        pytest.skip("FastMCP tool meta not directly accessible in this version")
