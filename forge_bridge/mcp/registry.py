"""
forge_bridge.mcp.registry — Namespace enforcement and source tagging for MCP tools.

Every tool registration (builtins, synthesized, user-taught) routes through this
module. It enforces the flame_*/forge_*/synth_* prefix rules and attaches
_source metadata to every registered tool.

Public API:
    register_tool(mcp, fn, name, source, annotations=None)
    register_tools(mcp, fns, prefix="", source="user-taught")
    register_builtins(mcp)

Constants:
    _VALID_PREFIXES         — all accepted prefixes
    _SYNTH_RESERVED_PREFIXES — prefixes only the synthesis pipeline may use
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

# Prefixes exclusively owned by the synthesis pipeline.
# Static (builtin / user-taught) registrations are blocked from using these.
_SYNTH_RESERVED_PREFIXES: frozenset[str] = frozenset({"synth_"})

# All valid prefixes for this server.
_VALID_PREFIXES: frozenset[str] = frozenset({"flame_", "forge_", "synth_"})


def _validate_name(name: str, source: str) -> None:
    """Raise ValueError if *name* violates namespace rules for *source*.

    Rules:
        1. Every tool name must start with one of the _VALID_PREFIXES.
        2. Only source="synthesized" may register under _SYNTH_RESERVED_PREFIXES.
    """
    if not any(name.startswith(p) for p in _VALID_PREFIXES):
        raise ValueError(
            f"Tool name {name!r} must start with flame_, forge_, or synth_. "
            f"Got source={source!r}."
        )
    if source != "synthesized" and any(name.startswith(p) for p in _SYNTH_RESERVED_PREFIXES):
        raise ValueError(
            f"Tool name {name!r} uses a reserved synth_ prefix. "
            "Only the synthesis pipeline may register under synth_."
        )


def register_tool(
    mcp: FastMCP,
    fn: Callable[..., Any],
    name: str,
    source: str,
    annotations: dict[str, Any] | None = None,
) -> None:
    """Register a single tool with namespace enforcement and source tagging.

    Args:
        mcp:         The live FastMCP instance to register against.
        fn:          The callable to register as an MCP tool.
        name:        Tool name — must start with flame_, forge_, or synth_.
        source:      One of "builtin", "synthesized", or "user-taught".
        annotations: Optional MCP tool annotations dict (readOnlyHint, etc.).

    Raises:
        ValueError: If name violates namespace rules for the given source.
    """
    _validate_name(name, source)
    mcp.add_tool(fn, name=name, annotations=annotations, meta={"_source": source})


def register_tools(
    mcp: FastMCP,
    fns: list[Callable[..., Any]],
    prefix: str = "",
    source: str = "user-taught",
) -> None:
    """Register multiple tools under a shared prefix and source tag.

    Public API for downstream consumers (e.g. projekt-forge).

    Usage (before mcp.run()):
        from forge_bridge.mcp import register_tools, get_mcp
        register_tools(get_mcp(), [my_fn1, my_fn2], prefix="forge_")

    Note: Must be called before mcp.run(). Tools registered after run() will
    not appear in the client's tool list until the client reconnects (no
    ToolListChangedNotification is sent by this function).

    Args:
        mcp:    The live FastMCP instance.
        fns:    List of callables to register.
        prefix: Prefix prepended to each fn.__name__ to form the tool name.
        source: Source tag for all tools in this batch.
    """
    for fn in fns:
        name = f"{prefix}{fn.__name__}" if prefix else fn.__name__
        register_tool(mcp, fn, name=name, source=source)


def register_builtins(mcp: FastMCP) -> None:
    """Register all builtin flame_* and forge_* tools. Implemented in Plan 02.

    This stub is called by server.py at import time. The actual registrations
    (migrating ~30 tools from mcp.tool() decorators through register_tool())
    are implemented when server.py is rebuilt in Phase 2 Plan 02.
    """
    pass
