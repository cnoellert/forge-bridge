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
    """Default-valid kwargs for ``emit_divergence_capture`` (the
    writer surface).

    Tests passing these kwargs to the writer get a canonical record
    emission; the writer sets ``record_kind="observation"``
    internally (it is not in this kwarg set because
    ``emit_divergence_capture`` does not accept ``record_kind`` —
    only the builder does, per PR 7 §4.3 amendment).

    Tests that call ``_build_capture_record`` directly should use
    ``base_builder_args()`` instead — that helper layers on
    ``record_kind="observation"`` so the builder's record_kind
    keyword-only requirement is satisfied.

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
        "pr20_condition_met": True,
        "collapse_occurred": True,
        "ambiguity_state": "single_survivor",
        "narrower_latency_ms": 0.42,
        # Migrated 2026-05-09 per A.5.3.2-PR7-SPEC.md §4.3 amendment:
        # "fixture" is removed from the schema's source-class
        # governance; production ontology is {runtime, seed}. Tests
        # constructing records via this helper now emit "runtime" as
        # the source, preserving the test-as-construction-site
        # distinction structurally rather than via the source field.
        "source": "runtime",
    }
    defaults.update(overrides)
    return defaults


def base_builder_args(**overrides: Any) -> dict[str, Any]:
    """Default-valid kwargs for ``_build_capture_record`` (the
    builder surface).

    Layered on ``base_writer_args()`` with ``record_kind="observation"``
    added per PR 7 §4.3 amendment. The builder requires record_kind
    as a keyword-only parameter; the writer (``emit_divergence_capture``)
    sets it internally and does not accept it as a kwarg. Two helpers
    exist because the boundary is real — tests that construct records
    via the builder directly must specify the truth class; tests that
    go through the writer get observation semantics by definition.

    Tests that need to build expectation records (PR 8 territory)
    pass ``record_kind="expectation"`` as an override; PR 7 ships no
    such test (expectation records aren't built until PR 8 lands the
    seed driver).
    """
    args = base_writer_args(**overrides)
    args.setdefault("record_kind", "observation")
    return args
