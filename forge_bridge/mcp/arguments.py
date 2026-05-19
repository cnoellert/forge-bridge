"""Argument normalization helpers for FastMCP tool invocation boundaries."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def normalize_tool_args(name: str, args: dict, tools: list[Any]) -> dict:
    """Normalize provider-native flat args to FastMCP wrapper args when needed."""
    if not isinstance(args, dict):
        return args
    if "params" in args:
        return args

    tool = next((candidate for candidate in tools if candidate.name == name), None)
    if tool is None or not requires_params_wrapper(getattr(tool, "inputSchema", None)):
        return args

    normalized = {"params": args}
    logger.debug(
        "invoke_tool: flat→params normalization applied for %s: %r",
        name,
        args,
    )
    return normalized


def requires_params_wrapper(input_schema: dict[str, Any] | None) -> bool:
    """Return True when a tool schema requires a nested object under params."""
    if not input_schema:
        return False

    required = input_schema.get("required") or []
    if "params" not in required:
        return False

    properties = input_schema.get("properties") or {}
    params_schema = properties.get("params")
    if not isinstance(params_schema, dict):
        return False

    ref = params_schema.get("$ref")
    if not isinstance(ref, str):
        return False
    if not ref.startswith("#/$defs/"):
        return False

    def_name = ref[len("#/$defs/"):]
    defs = input_schema.get("$defs") or {}
    nested = defs.get(def_name)
    return isinstance(nested, dict) and nested.get("type") == "object"
