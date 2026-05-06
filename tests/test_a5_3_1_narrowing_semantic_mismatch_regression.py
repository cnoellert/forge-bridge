"""A.5.3.1 regression coverage: narrower fails open on verb-only overlap.

Phase A.5 Smoke Test 3 codification. The original symptom was:

    "list projects"  →  forge_list_staged

instead of the expected ``forge_list_projects``. The repro is environmental
(Flame :9999 unreachable on the dev machine) but the bug is structural: when
the reachability filter prunes the natural-home tool out of the candidate
set, the deterministic narrower had no exit clause for "the only signal
between message and survivors is a verb token." Rule 3's raw-token
tie-breaker degenerated into "whichever survivor has the literal verb in
its name wins" — an arbitrary pick on a non-signal.

A.5.3.1 fix: skip Rule 3 when Rule 1's normalized overlap is verb-only
across all survivors. The candidate set is returned >1 so the chat
handler hands the decision to the LLM and the chain executor surfaces
``tool_selection_ambiguous``.

These tests cover both halves of the contract:

1. **Flame reachable (Smoke Test 3 baseline).** With the natural-home
   tool present in the candidate universe, the narrower picks
   ``forge_list_projects`` correctly. Confirms the fix did not regress
   the working case.

2. **Flame unreachable (A.5.3.1 reproducer).** With only the seven
   in-process staged-ops tools surviving the reachability filter, the
   narrower must NOT collapse to a single wrong tool — it must return
   the unfiltered candidate set so the LLM (or chain executor) decides.

3. **Rule 3 motivating case preserved.** ``forge_list_projects`` vs
   ``forge_get_project`` for "list projects" still disambiguates to
   ``forge_list_projects``: the overlap ``{list, project}`` includes a
   noun, so the verb-only guard does NOT fire and Rule 3 runs as
   before.

4. **Chain step ``tool_selection_ambiguous`` integration.** The
   ``/api/v1/exec`` chain step path (``forge_bridge.console._step``)
   sees the multi-tool return and emits the structured ambiguity error
   instead of running the wrong tool — the user-facing recovery path.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from forge_bridge.console._tool_filter import (
    _IN_PROCESS_FORGE_TOOLS,
    _VERB_TOKENS,
    deterministic_narrow,
    filter_tools_by_message,
)


def _mk(name: str) -> MagicMock:
    """Mock Tool object with ``.name`` — duck-typed against `mcp.types.Tool`."""
    t = MagicMock()
    t.name = name
    return t


def _names(tools: list) -> list[str]:
    return [t.name for t in tools]


# ── Smoke Test 3 baseline: Flame reachable ─────────────────────────────────


def test_flame_reachable_list_projects_picks_forge_list_projects():
    """Smoke Test 3 baseline. With the full Flame-backed registry visible
    (i.e., Flame :9999 reachable), ``"list projects"`` MUST select
    ``forge_list_projects``. This is the working case — the fix must
    not regress it."""
    full_registry = [_mk(n) for n in [
        "forge_list_projects",
        "forge_get_project",
        "forge_list_shots",
        "forge_list_versions",
        "forge_list_media",
        "forge_list_desktop",
        "forge_list_published_plates",
        "forge_list_roles",
        "flame_list_libraries",
        "flame_list_desktop",
    ] + sorted(_IN_PROCESS_FORGE_TOOLS)]

    filtered = filter_tools_by_message(full_registry, "list projects")
    narrowed = deterministic_narrow(filtered, "list projects")
    assert _names(narrowed) == ["forge_list_projects"]


# ── A.5.3.1 reproducer: Flame unreachable ──────────────────────────────────


def test_flame_unreachable_list_projects_does_not_collapse_to_wrong_tool():
    """A.5.3.1 reproducer. With only the seven in-process staged-ops tools
    surviving the reachability filter (because Flame :9999 is down), the
    narrower MUST NOT collapse "list projects" to a single tool — none
    of the survivors has any noun token in common with "project". Pre-fix:
    Rule 3 picked ``forge_list_staged`` because its raw tokens contain
    the literal ``list``. Post-fix: returns >1 (fails open).
    """
    in_proc_only = [_mk(n) for n in sorted(_IN_PROCESS_FORGE_TOOLS)]
    filtered = filter_tools_by_message(in_proc_only, "list projects")
    narrowed = deterministic_narrow(filtered, "list projects")

    assert len(narrowed) > 1, (
        f"narrower collapsed to a single tool {_names(narrowed)!r} when no "
        "in-process tool semantically matches 'list projects'. The verb-"
        "only-overlap guard in deterministic_narrow must fall through here."
    )
    # Defensive: the only post-PR14 survivors should be the two
    # ``staged`` tools whose tokens normalize to {forge, list, staged}.
    # If this set ever changes, regenerate the assertion against the
    # actual NORMALIZATION_MAP — but not by relaxing the >1 guard above.
    assert set(_names(narrowed)) == {"forge_get_staged", "forge_list_staged"}


# ── Rule 3 motivating case must still disambiguate ─────────────────────────


def test_rule3_motivating_case_preserved_when_overlap_has_noun():
    """The Rule 3 docstring's motivating case: ``"list projects"`` against
    ``[forge_list_projects, forge_get_project]`` ties on normalized
    tokens (both = {forge, list, project}) and Rule 3's raw-token rule
    correctly picks ``forge_list_projects``. The A.5.3.1 guard must NOT
    fire here — the normalized overlap includes the noun ``project``."""
    tools = [_mk("forge_list_projects"), _mk("forge_get_project")]
    narrowed = deterministic_narrow(tools, "list projects")
    assert _names(narrowed) == ["forge_list_projects"]


# ── Verb-only-overlap general principle ────────────────────────────────────


def test_verb_tokens_constant_matches_normalization_map_canonical_verbs():
    """The ``_VERB_TOKENS`` constant must stay in sync with the verb→
    canonical entries in ``NORMALIZATION_MAP``. Today the canonical verb
    is ``"list"`` (with show/get/fetch/listing all mapping to it). If a
    future PR adds a new verb cluster, this test pins the discipline:
    add the new canonical to ``_VERB_TOKENS`` in the same change."""
    from forge_bridge.console._tool_filter import NORMALIZATION_MAP

    # Canonical verb forms = values in the map that are reached via at
    # least one non-identity verb-shaped key. Today: only "list".
    canonical_verbs_via_map = {
        NORMALIZATION_MAP[k]
        for k in ("show", "get", "fetch", "listing")
    }
    assert _VERB_TOKENS == frozenset(canonical_verbs_via_map), (
        "_VERB_TOKENS drifted from NORMALIZATION_MAP's verb cluster. Update "
        "the constant when adding a new verb-cluster to NORMALIZATION_MAP."
    )


def test_verb_only_overlap_returns_full_set_when_max_overlap_ties():
    """General principle: when Rule 1 leaves >1 survivors that each
    overlap the message ONLY via verb tokens, the narrower returns the
    candidate set unchanged (so the LLM/chain decides)."""
    # Two tools whose only normalized overlap with "list X" is the verb.
    tools = [_mk("forge_get_staged"), _mk("forge_list_staged")]
    narrowed = deterministic_narrow(tools, "list projects")
    # Both should survive; fix must NOT collapse to a single arbitrary pick.
    assert sorted(_names(narrowed)) == ["forge_get_staged", "forge_list_staged"]


# ── Chain executor integration: tool_selection_ambiguous ───────────────────


@pytest.mark.asyncio
async def test_chain_step_emits_tool_selection_ambiguous_for_list_projects_when_flame_down():
    """Smoke Test 3 codified at the /api/v1/exec layer. With only the
    in-process tools reachable, ``execute_chain_step("list projects",
    ...)`` MUST surface a structured ``tool_selection_ambiguous`` error
    rather than silently invoke the wrong tool. The user-facing
    recovery path: caller sees 'be more specific' instead of staged ops."""
    from forge_bridge.console._step import execute_chain_step

    in_proc_only = [_mk(n) for n in sorted(_IN_PROCESS_FORGE_TOOLS)]
    mcp = MagicMock()
    mcp.call_tool = AsyncMock()  # MUST NOT be invoked — bug would call
                                  # forge_list_staged instead of erroring out.

    outcome = await execute_chain_step(
        step_text="list projects",
        tools=in_proc_only,
        mcp=mcp,
        inherited_context={},
    )

    assert "error" in outcome, f"expected error outcome, got {outcome!r}"
    assert outcome["error"]["type"] == "tool_selection_ambiguous"
    # Defensive: the wrong tool must NEVER have been called.
    mcp.call_tool.assert_not_called()
    # The candidates list should surface both staged-ops tools so the
    # operator-facing message names what the system saw.
    candidates = set(outcome["error"].get("candidates", []))
    assert candidates == {"forge_get_staged", "forge_list_staged"}
