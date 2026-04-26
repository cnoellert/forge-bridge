"""MCP resource + tool shim registration for the v1.3 Artist Console.

Every resource body and every tool-shim body uses `_envelope_json` -- the
SAME serializer the HTTP handlers use -- so MCP resources and HTTP routes
produce byte-identical payloads (D-26). Cross-surface byte-identity is
tested in tests/test_console_mcp_resources.py.

Registration timing (P9-2): this function is called from `_lifespan` AFTER
ManifestService and ConsoleReadAPI are live. NOT at module import -- FastMCP
accepts @mcp.resource/@mcp.tool registration after server construction.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from forge_bridge.console.handlers import _envelope_json

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

logger = logging.getLogger(__name__)


def register_console_resources(
    mcp: "FastMCP",
    manifest_service: "ManifestService",
    console_read_api: "ConsoleReadAPI",
    session_factory: Optional["async_sessionmaker"] = None,
) -> None:
    """Register the v1.3 Artist Console MCP surface.

    4 resources:
      forge://manifest/synthesis  -- full synthesis manifest (MFST-02)
      forge://tools               -- all registered tools with provenance (TOOLS-04)
      forge://tools/{name}        -- single tool by name (TOOLS-04 template)
      forge://health              -- full D-14 health body

    2 tool fallback shims for clients without resources support (P-03):
      forge_manifest_read           -- alias for forge://manifest/synthesis (MFST-03)
      forge_tools_read(name=None)   -- alias for forge://tools + tools/{name} (TOOLS-04 shim)
    """

    # Note: manifest_service is accepted for signature stability / future use
    # (e.g. cache invalidation callbacks); Phase 9 reads via console_read_api only.
    _ = manifest_service  # silence unused warning without touching ruff F841

    @mcp.resource("forge://manifest/synthesis", mime_type="application/json")
    async def synthesis_manifest() -> str:
        data = await console_read_api.get_manifest()
        return _envelope_json(data)

    @mcp.resource("forge://tools", mime_type="application/json")
    async def tools_list() -> str:
        tools = await console_read_api.get_tools()
        return _envelope_json([t.to_dict() for t in tools], total=len(tools))

    @mcp.resource("forge://tools/{name}", mime_type="application/json")
    async def tool_detail(name: str) -> str:
        tool = await console_read_api.get_tool(name)
        if tool is None:
            return json.dumps({
                "error": {
                    "code": "tool_not_found",
                    "message": f"no tool named {name!r}",
                }
            })
        return _envelope_json(tool.to_dict())

    @mcp.resource("forge://health", mime_type="application/json")
    async def health() -> str:
        data = await console_read_api.get_health()
        return _envelope_json(data)

    # -- Tool fallback shims (D-24, P-03) -----------------------------------

    @mcp.tool(
        name="forge_manifest_read",
        description=(
            "Read the current synthesis manifest. Alias for "
            "`resources/read forge://manifest/synthesis` for MCP clients "
            "that don't support resources (Cursor, Gemini CLI)."
        ),
        annotations={"readOnlyHint": True},
    )
    async def forge_manifest_read() -> str:
        data = await console_read_api.get_manifest()
        return _envelope_json(data)

    @mcp.tool(
        name="forge_tools_read",
        description=(
            "Read registered tools. Omit 'name' for the full list (alias for "
            "`forge://tools`); pass 'name' for per-tool detail (alias for "
            "`forge://tools/{name}`)."
        ),
        annotations={"readOnlyHint": True},
    )
    async def forge_tools_read(name: str | None = None) -> str:
        if name is None:
            tools = await console_read_api.get_tools()
            return _envelope_json([t.to_dict() for t in tools], total=len(tools))
        tool = await console_read_api.get_tool(name)
        if tool is None:
            return json.dumps({
                "error": {
                    "code": "tool_not_found",
                    "message": f"no tool named {name!r}",
                }
            })
        return _envelope_json(tool.to_dict())

    # -- Phase 14 (FB-B) — staged-ops MCP tools (4 tools) --------------------
    # Per CONTEXT D-17 revised (Solution C): registered from register_console_resources
    # so closures capture console_read_api and session_factory natively.
    # NO registration in register_builtins() — D-17 revised removes them from there.
    #
    # Lazy import breaks the circular path:
    #   mcp.tools → console.handlers → console.__init__ → console.resources → mcp.tools
    # By importing inside the function (called from _lifespan, not at module load),
    # both modules are fully initialised before either import runs.
    from forge_bridge.mcp.tools import (  # noqa: PLC0415 — intentional deferred import
        ListStagedInput, GetStagedInput, ApproveStagedInput, RejectStagedInput,
        _list_staged_impl, _get_staged_impl, _approve_staged_impl, _reject_staged_impl,
    )

    # Inject input model names into module globals so FastMCP's get_type_hints()
    # can resolve `params: ListStagedInput` annotations on the nested @mcp.tool
    # functions below. Without this, `from __future__ import annotations` keeps
    # the annotations as strings and get_type_hints() looks them up in
    # fn.__globals__ — which is this module, not the local scope of the
    # deferred import. Documented FastMCP requirement for forward-ref tools.
    globals().update({
        "ListStagedInput": ListStagedInput,
        "GetStagedInput": GetStagedInput,
        "ApproveStagedInput": ApproveStagedInput,
        "RejectStagedInput": RejectStagedInput,
    })

    @mcp.tool(
        name="forge_list_staged",
        description=(
            "List staged operations with optional status / project_id filter and "
            "pagination. status: proposed|approved|rejected|executed|failed (default: all)."
        ),
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def forge_list_staged(params: ListStagedInput) -> str:
        return await _list_staged_impl(params, console_read_api)

    @mcp.tool(
        name="forge_get_staged",
        description="Get a single staged operation by UUID.",
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def forge_get_staged(params: GetStagedInput) -> str:
        return await _get_staged_impl(params, console_read_api)

    @mcp.tool(
        name="forge_approve_staged",
        description="Approve a staged operation. Requires non-empty actor identity.",
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_approve_staged(params: ApproveStagedInput) -> str:
        return await _approve_staged_impl(params, session_factory)

    @mcp.tool(
        name="forge_reject_staged",
        description="Reject a staged operation. Requires non-empty actor identity.",
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_reject_staged(params: RejectStagedInput) -> str:
        return await _reject_staged_impl(params, session_factory)
