"""
Unit tests for forge_bridge.mcp.registry — namespace enforcement and source tagging.

Requirements covered:
    MCP-01  flame_* and forge_* namespace enforcement; synth_* blocked from static path
    MCP-02  Dynamic registration via add_tool / remove_tool roundtrip
    MCP-04  register_tools() pluggable API for downstream consumers
    MCP-05  All tools carry _source metadata (builtin/synthesized/user-taught)
    MCP-06  synth_* prefix accepted from synthesized source only
"""

import pytest
from mcp.server.fastmcp import FastMCP

from forge_bridge.mcp.registry import register_tool, register_tools


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fresh_mcp() -> FastMCP:
    """Return a fresh FastMCP instance for each test (no shared state)."""
    return FastMCP("test")


def _make_fn(name: str = "my_fn"):
    """Return a trivial callable with the given __name__."""
    def fn() -> str:
        return "ok"
    fn.__name__ = name
    fn.__qualname__ = name
    return fn


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_builtin_namespace():
    """register_tool with a flame_ prefix and builtin source succeeds.

    After registration the tool must appear in mcp._tool_manager._tools
    under the exact key 'flame_foo'.
    """
    mcp = _fresh_mcp()
    fn = _make_fn("flame_foo")
    register_tool(mcp, fn, name="flame_foo", source="builtin")
    assert "flame_foo" in mcp._tool_manager._tools, (
        "Expected 'flame_foo' to appear in mcp._tool_manager._tools after registration"
    )


def test_synth_prefix_rejected_from_static():
    """register_tool with synth_ prefix and builtin source must raise ValueError.

    The error message must reference 'reserved synth_ prefix'.
    """
    mcp = _fresh_mcp()
    fn = _make_fn("synth_foo")
    with pytest.raises(ValueError, match="reserved synth_ prefix"):
        register_tool(mcp, fn, name="synth_foo", source="builtin")


def test_synth_name_enforcement():
    """register_tool with synth_ prefix and synthesized source must succeed.

    The synthesis pipeline is the only allowed caller for synth_* names.
    """
    mcp = _fresh_mcp()
    fn = _make_fn("synth_foo")
    register_tool(mcp, fn, name="synth_foo", source="synthesized")
    assert "synth_foo" in mcp._tool_manager._tools


def test_invalid_prefix_rejected():
    """register_tool with a name that has no valid prefix must raise ValueError.

    The error must reference 'must start with flame_, forge_, or synth_'.
    """
    mcp = _fresh_mcp()
    fn = _make_fn("bad_name")
    with pytest.raises(ValueError, match="must start with flame_, forge_, or synth_"):
        register_tool(mcp, fn, name="bad_name", source="builtin")


def test_source_tagging():
    """Tool registered via register_tool must carry meta={'_source': 'builtin'}.

    Access via mcp._tool_manager._tools['flame_bar'].meta.
    """
    mcp = _fresh_mcp()
    fn = _make_fn("flame_bar")
    register_tool(mcp, fn, name="flame_bar", source="builtin")
    tool = mcp._tool_manager._tools["flame_bar"]
    assert tool.meta == {"_source": "builtin"}, (
        f"Expected meta={{'_source': 'builtin'}}, got {tool.meta!r}"
    )


def test_register_tools_api():
    """register_tools() with prefix and source registers multiple tools.

    register_tools(mcp, [fn1, fn2], prefix="forge_", source="user-taught")
    must produce entries 'forge_fn1' and 'forge_fn2', each tagged
    with _source='user-taught'.
    """
    mcp = _fresh_mcp()
    fn1 = _make_fn("fn1")
    fn2 = _make_fn("fn2")
    register_tools(mcp, [fn1, fn2], prefix="forge_", source="user-taught")

    assert "forge_fn1" in mcp._tool_manager._tools
    assert "forge_fn2" in mcp._tool_manager._tools
    assert mcp._tool_manager._tools["forge_fn1"].meta == {"_source": "user-taught"}
    assert mcp._tool_manager._tools["forge_fn2"].meta == {"_source": "user-taught"}


def test_dynamic_registration():
    """register_tool + mcp.remove_tool roundtrip works correctly.

    Tool must be present after registration and absent after removal.
    """
    mcp = _fresh_mcp()
    fn = _make_fn("flame_dynamic")
    register_tool(mcp, fn, name="flame_dynamic", source="builtin")

    # Tool should be registered
    assert "flame_dynamic" in mcp._tool_manager._tools

    # Remove it
    mcp.remove_tool("flame_dynamic")

    # Tool should be gone
    assert "flame_dynamic" not in mcp._tool_manager._tools


def test_register_tools_builtin_source():
    """PKG-01: register_tools(source='builtin') is accepted and the tool's
    _source metadata is 'builtin' for downstream builtin callers."""
    mcp = _fresh_mcp()

    def my_tool() -> str:
        """A downstream-supplied tool."""
        return "ok"

    register_tools(mcp, [my_tool], prefix="forge_", source="builtin")

    # Tool registered under the expected name and carries source=builtin metadata
    registered = mcp._tool_manager._tools
    assert "forge_my_tool" in registered
    tool = registered["forge_my_tool"]
    # FastMCP stores meta on the tool object; check meta._source
    assert tool.meta == {"_source": "builtin"}


def test_register_tools_post_run_guard():
    """API-05: register_tools raises RuntimeError when _server_started is True."""
    import forge_bridge.mcp.server as server_mod
    mcp = _fresh_mcp()

    def my_tool() -> str:
        """Late tool."""
        return "late"

    original = server_mod._server_started
    try:
        server_mod._server_started = True
        with pytest.raises(RuntimeError, match="cannot be called after the MCP server has started"):
            register_tools(mcp, [my_tool], prefix="forge_")
    finally:
        server_mod._server_started = original


def test_register_tools_pre_run_ok():
    """API-05: register_tools succeeds when _server_started is False (default)."""
    import forge_bridge.mcp.server as server_mod
    mcp = _fresh_mcp()

    def my_tool() -> str:
        """Early tool."""
        return "early"

    original = server_mod._server_started
    try:
        server_mod._server_started = False
        register_tools(mcp, [my_tool], prefix="forge_")  # must not raise
        assert "forge_my_tool" in mcp._tool_manager._tools
    finally:
        server_mod._server_started = original
