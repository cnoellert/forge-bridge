"""TF.3a — detectors over ObservedTraces.

Starts with the WELL-FORMEDNESS detector (room ratification 2026-06-02): the
gating, Tier-1 check that decides whether a graph is structurally evaluable at
all. A malformed graph (detached args, prose/non-tool steps, compile-shape
failure) short-circuits content evaluation — you cannot ask "was the tool
right?" of a graph whose args never attached.

This is the dominant live-capture failure (chain-step serialization): the
model emits the tool name and its args-JSON as SEPARATE steps, so the params
never reach the tool.
"""
from __future__ import annotations

import shlex
from typing import Iterable, Optional


def compute_well_formed(
    observed_graph: list,
    *,
    outcome: Optional[str] = None,
    known_tools: Optional[Iterable[str]] = None,
) -> tuple[bool, Optional[str]]:
    """Return (well_formed, reason). A graph is malformed if ANY step is.

    Checks (in order):
      - compile produced nothing AND it was a compile error -> invalid shape.
      - a step is a bare args object (`{...}`) -> detached args (the dominant
        serialization failure: tool name and args emitted as separate steps).
      - a step's first token is not a tool (when `known_tools` is given) or has
        no `_`/`commit` tool shape -> a prose / non-tool step.
    An empty graph that is NOT a compile error (e.g. an honest decline) is
    well-formed (there is no malformed step).
    """
    known = set(known_tools) if known_tools is not None else None

    if not observed_graph:
        if outcome == "compile_error":
            return (False, "invalid_chain_shape")
        return (True, None)

    for step in observed_graph:
        s = str(step).strip()
        if not s:
            return (False, "empty_step")
        if s.startswith("{"):
            return (False, "detached_args")
        first = s.split(maxsplit=1)[0]
        if known is not None:
            if first not in known and first != "commit":
                return (False, "non_tool_step")
        else:
            # no registry on hand: real tools are snake_case with a `_`
            # (flame_*, forge_*, format_result); `commit` is the lone keyword.
            if "_" not in first and first != "commit":
                return (False, "non_tool_step")

    return (True, None)


def _extract_param_values(observed_graph: list) -> set[str]:
    values: set[str] = set()
    for step in observed_graph:
        try:
            tokens = shlex.split(str(step))
        except ValueError:
            tokens = str(step).split()
        for token in tokens:
            if "=" not in token:
                continue
            _key, value = token.split("=", 1)
            values.add(value.strip().strip("\"'"))
    return values


def detect_entity_value_fidelity(
    observed_graph: list,
    expected_params: dict,
) -> tuple[bool, Optional[str]]:
    """Return whether every expected value appears as an emitted param value.

    This detector is param-location-blind and exact: any key in any step may
    carry the value, but the value must match verbatim after parameter-token
    extraction. It never performs substring, fuzzy, or nearest-entity matching.
    """
    observed_values = _extract_param_values(observed_graph)
    for value in expected_params.values():
        canonical = str(value)
        if canonical not in observed_values:
            return (False, canonical)
    return (True, None)
