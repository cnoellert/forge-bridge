"""#153 slice 2a — ``normalize_tool_args`` sheds flat keys the wrapper rejects.

The upstream extractor / legacy ``public_inherited`` fold forwards inherited
context (e.g. ``sequence_name``) tool-agnostically. The params-wrapper is where
the downstream tool's accepted surface is finally known, so over-forwarded keys
are dropped there — the "over-insertion is safe" contract the #153 convergence
relied on. These tests lock the drop AND its guards (only a closed declared
property set authorizes shedding).
"""
from __future__ import annotations

from types import SimpleNamespace

from forge_bridge.mcp.arguments import normalize_tool_args


def _wrapped_tool(name: str, properties: dict, *, additional=None):
    nested: dict = {"type": "object", "properties": properties, "required": []}
    if additional is not None:
        nested["additionalProperties"] = additional
    return SimpleNamespace(
        name=name,
        inputSchema={
            "$defs": {"Input": nested},
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/Input"}},
            "required": ["params"],
        },
    )


def _flat_tool(name: str, properties: dict):
    return SimpleNamespace(
        name=name,
        inputSchema={"type": "object", "properties": properties, "required": []},
    )


def test_drops_unaccepted_flat_keys_before_wrapping():
    tool = _wrapped_tool("format_result", {"data": {}, "format": {"type": "string"}})
    out = normalize_tool_args(
        "format_result",
        {"sequence_name": "leak", "data": {"a": 1}, "format": "email"},
        [tool],
    )
    assert out == {"params": {"data": {"a": 1}, "format": "email"}}


def test_keeps_accepted_flat_keys():
    tool = _wrapped_tool("flame_get_sequence_segments", {"sequence_name": {"type": "string"}})
    out = normalize_tool_args(
        "flame_get_sequence_segments", {"sequence_name": "SEQ_A"}, [tool]
    )
    assert out == {"params": {"sequence_name": "SEQ_A"}}


def test_does_not_filter_when_additional_properties_true():
    tool = _wrapped_tool("open_tool", {"known": {}}, additional=True)
    out = normalize_tool_args("open_tool", {"known": 1, "extra": 2}, [tool])
    assert out == {"params": {"known": 1, "extra": 2}}


def test_flat_tool_without_wrapper_passes_keys_through():
    tool = _flat_tool("forge_is_greenscreen", {"shot_id": {"type": "string"}})
    out = normalize_tool_args(
        "forge_is_greenscreen", {"shot_id": "S1", "sequence_name": "SEQ_A"}, [tool]
    )
    # No params wrapper → normalization is a no-op, keys unchanged.
    assert out == {"shot_id": "S1", "sequence_name": "SEQ_A"}


def test_explicit_params_key_left_untouched():
    tool = _wrapped_tool("format_result", {"data": {}})
    payload = {"params": {"data": {"a": 1}, "sequence_name": "keep"}}
    assert normalize_tool_args("format_result", payload, [tool]) == payload
