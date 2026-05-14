"""Canonical operational regression for Flame introspection convergence.

This query exercises semantic retrieval, tool discoverability, graph
emission, and runtime legitimacy simultaneously. Every v1.6+ phase that
touches the chat path, MCP registry, or proto-node emission verifies
against this fixture before close.

The natural-language query is what a non-author operator types into the
chat surface. The canonical Python is what a correctly-functioning LLM
synthesizes in response — taken verbatim from the Phase 23.1 docstring
Example 1 of ``flame_execute_python``. Tests that exercise the producer
without live Flame use the Python; tests that exercise the chat surface
(live Flame author-walks, eventual CI smoke) use the query.

Both strings are load-bearing. Do not inline, paraphrase, or compress
them — the verbatim form is the canonical reference. See
`SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+` for the formalization
arc, and `.planning/milestones/v1.6-PHASE-24-CONVERGENCE.md` §4 for
why this single sentence operationally tests four orthogonal substrate
properties at once.
"""
from __future__ import annotations

__all__ = [
    "CANONICAL_FLAME_INTROSPECTION_QUERY",
    "CANONICAL_FLAME_INTROSPECTION_PYTHON",
]


CANONICAL_FLAME_INTROSPECTION_QUERY: str = "What are the clips on Reel 1"
"""The canonical natural-language regression query.

Verbatim, with exact capitalization and spacing. Tests, author-walks,
and eventual CI smoke all reference this string as ground truth.

Operationally tests four substrate properties in one sentence:

1. Semantic retrieval — can the model interpret "Reel 1" as the
   Flame-substrate concept the operator means?
2. Affordance discoverability — does the model find
   `flame_execute_python` when narrow `flame_*` tools don't fit?
3. Tool discoverability — is the canonical-introspection docstring
   legible enough to bias the model toward escalation?
4. Graph-runtime legitimacy — does the resulting proto-node record
   stream describe what happened in a way a non-author can read back?
"""


CANONICAL_FLAME_INTROSPECTION_PYTHON: str = """
import flame, json
desk = flame.project.current_project.current_workspace.desktop
target_reel = None
for rg in desk.reel_groups:
    for r in rg.reels:
        name = r.name.get_value() if hasattr(r.name, "get_value") else str(r.name)
        if name == "Reel 1":
            target_reel = r
            break
if target_reel is None:
    print(json.dumps({"error": "Reel 1 not found"}))
else:
    clips = [
        c.name.get_value() if hasattr(c.name, "get_value") else str(c.name)
        for c in target_reel.clips
    ]
    print(json.dumps({"reel": "Reel 1", "clips": clips}))
""".strip()
"""The canonical Python a correctly-functioning LLM synthesizes for
the natural-language query. Verbatim from Phase 23.1's
``flame_execute_python`` docstring Example 1.

Tests that exercise the producer (``execute_python``) directly use
this string as the deterministic ``code`` argument — it represents
the expected LLM synthesis for the canonical query without requiring
the chat-layer escalation path to be exercised. Live-Flame author-
walks exercise the chat path with the natural-language query and
verify that the LLM produces equivalent Python (a separate concern,
out of Commit 3 scope).
"""
