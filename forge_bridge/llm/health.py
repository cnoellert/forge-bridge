"""LLM health check — MCP resource registration."""
import json

from mcp.server.fastmcp import FastMCP


def register_llm_resources(mcp: FastMCP) -> None:
    """Register forge://llm/health resource on the MCP server."""

    @mcp.resource("forge://llm/health")
    async def llm_health() -> str:
        """Report available LLM backends for forge-bridge."""
        from forge_bridge.llm.router import get_router
        router = get_router()
        status = await router.ahealth_check()
        return json.dumps(status, indent=2)
