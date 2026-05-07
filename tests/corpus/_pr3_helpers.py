"""Shared helpers for PR 3 tests.

A minimal ``MockTool`` stand-in (with ``.name`` and ``.inputSchema``
attributes) plus ``base_writer_args()``, the canonical
default-valid kwargs for ``emit_divergence_capture`` /
``_build_capture_record``. Tests override individual keys to
exercise specific behaviors; the rest stay valid by default so
test signatures stay tight.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MockTool:
    """Minimal Tool stand-in for tests.

    Has the ``.name`` and ``.inputSchema`` attributes that
    ``registered_tools_snapshot_hash`` inspects (per
    ``forge_bridge/corpus/_identity.py``). Production callers pass
    FastMCP ``Tool`` objects; tests use this.
    """
    name: str
    inputSchema: dict[str, Any] = field(default_factory=dict)


def tool(name: str, **schema_props: Any) -> MockTool:
    """Convenience: ``MockTool`` with a properties-bearing schema.

    Two tools with the same name + same schema produce the same
    identity-hash entry. Two tools with different names produce
    different entries. Schema-property differences are captured by
    the hash (per ``registered_tools_snapshot_hash`` v1
    normalization rules).
    """
    return MockTool(
        name=name,
        inputSchema={"properties": dict(schema_props)} if schema_props else {},
    )


def base_writer_args(**overrides: Any) -> dict[str, Any]:
    """Default-valid kwargs for the writer / builder.

    The defaults form a coherent record that passes schema
    validation. Tests override individual keys to exercise specific
    behaviors. The default set is deliberately small (two tools,
    one decision) so test assertions don't need to thread
    fixture-scale data through every check.
    """
    defaults: dict[str, Any] = {
        "prompt": "list staged",
        "registered_tools": [
            tool("forge_list_staged"),
            tool("forge_get_staged"),
            tool("forge_approve_staged"),
        ],
        "candidate_set_post_reachability": [
            tool("forge_list_staged"),
            tool("forge_get_staged"),
            tool("forge_approve_staged"),
        ],
        "candidate_set_post_pr14": [
            tool("forge_list_staged"),
            tool("forge_get_staged"),
        ],
        "narrower_decision": [tool("forge_list_staged")],
        "pr20_fired": True,
        "collapse_occurred": True,
        "ambiguity_state": "single_survivor",
        "narrower_latency_ms": 0.42,
        "source": "fixture",
    }
    defaults.update(overrides)
    return defaults
