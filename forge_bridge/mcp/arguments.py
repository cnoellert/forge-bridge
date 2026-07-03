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
    input_schema = getattr(tool, "inputSchema", None)
    if tool is None or not requires_params_wrapper(input_schema):
        return args
    if not args and not _params_wrapper_is_required(input_schema):
        return args

    # #153 slice 2a — drop flat keys the wrapper model does not declare before
    # nesting them under ``params``. Edge-sourced context (e.g. an inherited
    # ``sequence_name``) is forwarded tool-agnostically by the upstream
    # extractor/``public_inherited`` fold; the wrapper is where the tool's
    # accepted surface is finally known, so over-forwarded keys are shed here.
    # This is the "over-insertion is safe" contract the #153 convergence relied
    # on (``normalize_tool_args`` drops keys the tool does not accept). Only
    # applied when the wrapper declares an explicit closed property set.
    wrapper_props = _params_wrapper_properties(input_schema)
    if wrapper_props is not None:
        filtered = {key: value for key, value in args.items() if key in wrapper_props}
        if filtered != args:
            logger.debug(
                "invoke_tool: dropped unaccepted flat keys for %s: %r",
                name,
                sorted(set(args) - set(filtered)),
            )
        args = filtered

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


def _params_wrapper_properties(input_schema: dict[str, Any] | None) -> set[str] | None:
    """Return the wrapper model's declared property names, or ``None``.

    ``None`` means "do not filter" — the schema does not present a closed,
    explicit property set (no resolvable ``$defs`` model, no declared
    ``properties``, or the model explicitly allows ``additionalProperties``).
    Only a closed property set authorizes shedding unaccepted flat keys.
    """
    ref = _params_model_ref(input_schema)
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        return None
    def_name = ref[len("#/$defs/"):]
    defs = (input_schema or {}).get("$defs") or {}
    nested = defs.get(def_name)
    if not isinstance(nested, dict):
        return None
    if nested.get("additionalProperties") is True:
        return None
    properties = nested.get("properties")
    if not isinstance(properties, dict) or not properties:
        return None
    return set(properties.keys())


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
