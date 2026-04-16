"""forge-bridge — Protocol-agnostic communication middleware for post-production pipelines.

Public API:

    from forge_bridge import (
        # LLM routing
        LLMRouter, get_router,
        # Learning pipeline
        ExecutionLog, SkillSynthesizer,
        # MCP server
        register_tools, get_mcp,
        # Server lifecycle
        startup_bridge, shutdown_bridge,
        # Flame HTTP bridge
        execute, execute_json, execute_and_read,
    )

For canonical vocabulary types (Project, Shot, Registry, Role, Status, etc.),
import from forge_bridge.core — these are intentionally NOT re-exported at
the package root to keep the consumer surface focused on operational APIs.
"""

# LLM routing
from forge_bridge.llm.router import LLMRouter, get_router

# Learning pipeline
from forge_bridge.learning.execution_log import ExecutionLog
from forge_bridge.learning.synthesizer import SkillSynthesizer

# MCP server (registry + singleton access + lifecycle)
from forge_bridge.mcp import register_tools, get_mcp
from forge_bridge.mcp.server import startup_bridge, shutdown_bridge

# Flame HTTP bridge
from forge_bridge.bridge import execute, execute_json, execute_and_read


__all__ = [
    # LLM routing
    "LLMRouter",
    "get_router",
    # Learning pipeline
    "ExecutionLog",
    "SkillSynthesizer",
    # MCP server
    "register_tools",
    "get_mcp",
    # Server lifecycle
    "startup_bridge",
    "shutdown_bridge",
    # Flame HTTP bridge
    "execute",
    "execute_json",
    "execute_and_read",
]
