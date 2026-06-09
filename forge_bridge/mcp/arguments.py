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
    if not args and not _params_wrapper_is_required(getattr(tool, "inputSchema", None)):
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
    ref = _params_model_ref(input_schema)
    if ref is None:
        return False

    if not ref.startswith("#/$defs/"):
        return False

    def_name = ref[len("#/$defs/"):]
    defs = input_schema.get("$defs") or {}
    nested = defs.get(def_name)
    return isinstance(nested, dict) and nested.get("type") == "object"


def _params_wrapper_is_required(input_schema: dict[str, Any] | None) -> bool:
    if not input_schema:
        return False
    required = input_schema.get("required") or []
    return "params" in required


def _params_model_ref(input_schema: dict[str, Any] | None) -> str | None:
    if not input_schema:
        return None

    properties = input_schema.get("properties") or {}
    params_schema = properties.get("params")
    if not isinstance(params_schema, dict):
        return None

    direct_ref = params_schema.get("$ref")
    if isinstance(direct_ref, str):
        return direct_ref

    # Optional[Model] = None schemas emit params as anyOf/oneOf:
    # {"anyOf": [{"$ref": "#/$defs/Input"}, {"type": "null"}], "default": null}.
    # That is still a wrapper schema for non-empty flat args; only the empty
    # call remains unwrapped so the tool body can preserve its PR22
    # params=None graceful error/default path.
    for key in ("anyOf", "oneOf"):
        variants = params_schema.get(key)
        if not isinstance(variants, list):
            continue
        refs = [
            variant.get("$ref")
            for variant in variants
            if isinstance(variant, dict) and isinstance(variant.get("$ref"), str)
        ]
        if len(refs) == 1:
            return refs[0]
    return None
