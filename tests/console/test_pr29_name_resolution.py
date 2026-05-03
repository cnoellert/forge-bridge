"""PR29 — Unit and integration tests for deterministic name-based
disambiguation (scoped, exact match).

Two layers covered:

  - **Unit tests** target ``_name_resolve.resolve_name_from_candidates``
    plus the ``project_name=`` extraction in ``_param_extract``. They
    pin the strict exact-match contract: case-insensitive, trimmed,
    single-match-or-None.

  - **Integration tests** drive the chat handler end-to-end with a
    multi-project fixture and verify that an explicit ``project_name=
    <name>`` in the user message resolves a unique candidate to its
    UUID, injects it, and forces tool execution — all without an
    upstream probe and without writing memory.

Per the PR29 brief's eleven tests:
  Unit:
    1. test_exact_name_match_single_candidate
    2. test_case_insensitive_match
    3. test_trimmed_match
    4. test_no_match_returns_none
    5. test_multiple_matches_returns_none
    6. test_invalid_name_returns_none

  Integration:
    7. multi-project + project_name exact → executes
    8. multi-project + bad name → MULTIPLE_PROJECTS
    9. multi-project + ambiguous name → MULTIPLE_PROJECTS
    10. name match does NOT call upstream resolver (after candidate fetch)
    11. name match does NOT write memory
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from forge_bridge.console._memory import _MEMORY
from forge_bridge.console._name_resolve import resolve_name_from_candidates
from forge_bridge.console._param_extract import extract_explicit_params
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI


# ── Unit AC #1: exact match against single candidate ─────────────────────


def test_exact_name_match_single_candidate():
    """Exact name match against a unique candidate returns its id.
    The lone happy path the brief gives as the canonical example."""
    candidates = [
        {"id": "A", "name": "chatTest"},
        {"id": "B", "name": "other"},
    ]
    assert resolve_name_from_candidates("chatTest", candidates) == "A"


# ── Unit AC #2: case-insensitive match ───────────────────────────────────


def test_case_insensitive_match():
    """Match folds case on both sides — ``CHATTEST``, ``chattest``,
    ``ChAtTeSt`` all resolve to the candidate stored as ``chatTest``."""
    candidates = [
        {"id": "A", "name": "chatTest"},
        {"id": "B", "name": "Other"},
    ]
    for variant in ("chatTest", "chattest", "CHATTEST", "ChAtTeSt"):
        assert resolve_name_from_candidates(variant, candidates) == "A", (
            f"variant {variant!r} failed"
        )


def test_case_insensitive_match_with_uppercase_candidate():
    """Symmetrical — uppercase candidate name + lowercase input still
    resolves. The fold direction must not matter."""
    candidates = [
        {"id": "X", "name": "PROJECT-ALPHA"},
        {"id": "Y", "name": "project-beta"},
    ]
    assert resolve_name_from_candidates("project-alpha", candidates) == "X"
    assert resolve_name_from_candidates("PROJECT-BETA", candidates) == "Y"


# ── Unit AC #3: trimmed match ────────────────────────────────────────────


def test_trimmed_match():
    """Leading and trailing whitespace on the input is ignored. A user
    typing ``project_name=  chatTest  `` (after PR28's tokenizer strips
    most of it) still resolves cleanly if any sneaks through."""
    candidates = [{"id": "A", "name": "chatTest"}]
    assert resolve_name_from_candidates("  chatTest  ", candidates) == "A"
    assert resolve_name_from_candidates("\tchatTest\n", candidates) == "A"


def test_trimmed_match_on_candidate_side():
    """Candidates with stored leading/trailing whitespace also resolve.
    The brief specifies ``c["name"].strip().lower() == target`` so a
    legacy entry like ``" Alpha "`` matches ``"alpha"``."""
    candidates = [{"id": "A", "name": "  Alpha  "}]
    assert resolve_name_from_candidates("alpha", candidates) == "A"


# ── Unit AC #4: zero matches → None ──────────────────────────────────────


def test_no_match_returns_none():
    """Name that doesn't appear in the candidate list resolves to
    ``None`` — caller falls through to the existing PR27 envelope."""
    candidates = [
        {"id": "A", "name": "Alpha"},
        {"id": "B", "name": "Beta"},
    ]
    assert resolve_name_from_candidates("Gamma", candidates) is None


def test_no_match_does_not_pick_substring():
    """``"Alph"`` does not partial-match ``"Alpha"`` — exact-only.
    Pin against a future regression that adds ``startswith`` /
    ``in`` matching."""
    candidates = [{"id": "A", "name": "Alpha"}]
    assert resolve_name_from_candidates("Alph", candidates) is None
    assert resolve_name_from_candidates("Alphabet", candidates) is None
    assert resolve_name_from_candidates("alp", candidates) is None


def test_no_match_does_not_pick_substring_inside_candidate():
    """Symmetric — a candidate whose name CONTAINS the input is not
    a match. ``"Alpha"`` does not match ``"Project Alpha"``."""
    candidates = [{"id": "A", "name": "Project Alpha"}]
    assert resolve_name_from_candidates("Alpha", candidates) is None


def test_no_match_with_empty_candidates_returns_none():
    """Empty candidate list → no possible match. Returns ``None`` even
    for a non-empty name input."""
    assert resolve_name_from_candidates("anything", []) is None


# ── Unit AC #5: multiple matches → None (no guessing) ────────────────────


def test_multiple_matches_returns_none():
    """Two candidates with the same name → ``None``. Ambiguity stays
    ambiguous; the caller's escape hatch is the UUID form (PR28).

    Critical contract: this MUST NOT silently pick the first match.
    A regression that does so would re-introduce exactly the
    heuristic PR29 forbids."""
    candidates = [
        {"id": "A", "name": "Alpha"},
        {"id": "B", "name": "Alpha"},  # collision
        {"id": "C", "name": "Other"},
    ]
    assert resolve_name_from_candidates("Alpha", candidates) is None


def test_multiple_matches_with_case_variation_returns_none():
    """Case-folded duplicates also collide. ``"alpha"`` and ``"Alpha"``
    are the same target after fold — neither resolves."""
    candidates = [
        {"id": "A", "name": "alpha"},
        {"id": "B", "name": "Alpha"},  # case-only difference
    ]
    assert resolve_name_from_candidates("Alpha", candidates) is None


# ── Unit AC #6: invalid input → None ─────────────────────────────────────


def test_invalid_name_returns_none():
    """Non-string and empty/whitespace-only inputs return ``None``
    without raising. Defensive contract for future call sites."""
    candidates = [{"id": "A", "name": "Alpha"}]
    assert resolve_name_from_candidates(None, candidates) is None  # type: ignore[arg-type]
    assert resolve_name_from_candidates("", candidates) is None
    assert resolve_name_from_candidates("   ", candidates) is None
    assert resolve_name_from_candidates(123, candidates) is None  # type: ignore[arg-type]


def test_candidate_with_non_string_name_is_skipped():
    """A malformed candidate (non-string ``name``) is skipped during
    matching, not raised on. The valid sibling still resolves."""
    candidates = [
        {"id": "A", "name": "Alpha"},
        {"id": "B", "name": None},  # malformed — skip
        {"id": "C", "name": "Beta"},
    ]
    assert resolve_name_from_candidates("Alpha", candidates) == "A"
    assert resolve_name_from_candidates("Beta", candidates) == "C"


# ── Param extraction — project_name= keyed form (PR29 wiring) ────────────


def test_extract_project_name_explicit():
    """``project_name=<value>`` is extracted into the params dict with
    the key ``project_name``. Whitespace-terminated value, case-
    sensitive on the value (only the KEY is case-insensitive)."""
    out = extract_explicit_params("fetch versions project_name=chatTest")
    assert out == {"project_name": "chatTest"}


def test_extract_project_name_with_trailing_text():
    """Trailing context after a space terminates the candidate. The
    user typed an explicit selector; everything else is incidental."""
    out = extract_explicit_params(
        "please fetch versions project_name=chatTest for the hero shots"
    )
    assert out == {"project_name": "chatTest"}


def test_extract_project_name_key_is_case_insensitive():
    """Same as PR28: the KEY is case-insensitive (``PROJECT_NAME=``,
    ``Project_Name=``); the VALUE preserves its case."""
    out = extract_explicit_params("PROJECT_NAME=ChatTest")
    assert out == {"project_name": "ChatTest"}


def test_extract_project_name_value_preserves_case():
    """Names are case-significant in their stored form; the extractor
    must not fold the value. Matching is case-insensitive at the
    resolver layer (``resolve_name_from_candidates``), not here."""
    out = extract_explicit_params("project_name=CamelCaseName")
    assert out["project_name"] == "CamelCaseName"


def test_extract_project_id_takes_precedence_over_project_name():
    """A keyed UUID outranks a keyed name — the UUID is the canonical
    handle. Returns ONLY ``project_id``; the name is dropped because
    it would be ignored by the downstream tool anyway."""
    uuid_str = "7ad1756d-7a20-44f1-b4e5-56c8cbc9026e"
    out = extract_explicit_params(
        f"project_id={uuid_str} project_name=chatTest"
    )
    assert out == {"project_id": uuid_str}
    assert "project_name" not in out


def test_extract_project_name_takes_precedence_over_bare_uuid():
    """Explicit keyed name wins over an incidental bare UUID. The user
    committed to the name form — honor it."""
    uuid_str = "7ad1756d-7a20-44f1-b4e5-56c8cbc9026e"
    out = extract_explicit_params(
        f"project_name=chatTest reference: {uuid_str}"
    )
    assert out == {"project_name": "chatTest"}
    assert "project_id" not in out


def test_extract_empty_project_name_value_ignored():
    """``project_name=`` with no value (or only whitespace after) is
    ignored — extractor returns ``{}`` rather than carrying an empty
    string forward."""
    assert extract_explicit_params("project_name=") == {}
    # Only whitespace after = → no token; the key block returns no
    # candidate, then bare-UUID fallback finds nothing → {}.
    assert extract_explicit_params("project_name=   ") == {}


# ── Integration helpers ───────────────────────────────────────────────────


def _named_projects_payload(names: list[str]) -> str:
    """Build a forge_list_projects payload with explicit project names
    so name resolution has something to match against."""
    projects = [
        {"id": f"proj-{i}", "name": name, "code": name}
        for i, name in enumerate(names)
    ]
    return json.dumps({"count": len(projects), "projects": projects})


def _passthrough_filter(tools, **_):
    return tools


def _make_handler_app_for_name_resolution(project_names: list[str]):
    """Build a chat-handler app whose tool registry contains a single
    forced-execution target (``forge_list_versions``) and a stubbed
    ``mcp.call_tool`` returning the specified named projects from
    ``forge_list_projects``.

    Mirrors the PR27 / PR28 fixture shape so behavior diffs across the
    three resolution paths (UUID, name, fall-through) are easy to read."""
    from mcp.types import TextContent, Tool

    tools_list = [
        Tool(
            name=n,
            description=f"{n} description",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
        for n in [
            "forge_list_versions",
            "flame_alpha", "flame_beta", "synth_gamma",
        ]
    ]

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="UNREACHED")
    mock_router.system_prompt = "base"

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, llm_router=mock_router,
    )
    app = build_console_app(api)

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return [TextContent(
                type="text", text=_named_projects_payload(project_names),
            )]
        return [TextContent(
            type="text", text=f"{name}-result:{arguments!r}",
        )]

    list_p = patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools_list),
    )
    back_p = patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    )
    call_p = patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=fake_call_tool),
    )
    return list_p, back_p, call_p, app, mock_router


# ── Integration AC #7: multi-project + exact name → executes ─────────────


def test_pr29_handler_exact_name_executes_with_multiple_projects():
    """End-to-end: a multi-project deployment + an explicit
    ``project_name=<name>`` in the user message → handler resolves the
    name to the matching candidate's id, injects it, and forces
    ``forge_list_versions`` execution. 200 + ``tool_forced=True``
    instead of 400 MULTIPLE_PROJECTS."""
    list_p, back_p, call_p, app, mock_router = (
        _make_handler_app_for_name_resolution(
            project_names=["chatTest", "other", "third"],
        )
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "fetch versions project_name=chatTest"},
            ]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    # Tool was invoked with the resolved candidate's id.
    call_mock.assert_any_call(
        "forge_list_versions", {"project_id": "proj-0"},
    )
    mock_router.complete_with_tools.assert_not_called()


def test_pr29_handler_case_insensitive_name_executes():
    """Case-insensitive resolution all the way to execution. ``CHATTEST``
    in the message resolves to the candidate stored as ``chatTest``."""
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_name_resolution(
            project_names=["chatTest", "other"],
        )
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "fetch versions project_name=CHATTEST"},
            ]},
        )
    assert r.status_code == 200, r.text
    call_mock.assert_any_call(
        "forge_list_versions", {"project_id": "proj-0"},
    )


# ── Integration AC #8: bad name → MULTIPLE_PROJECTS ──────────────────────


def test_pr29_handler_unknown_name_falls_through_to_multiple_projects():
    """A ``project_name=`` that doesn't match any candidate falls
    through to the existing PR27 envelope. The user's intent was
    explicit but unresolvable; better to surface the structured error
    than to guess."""
    list_p, back_p, call_p, app, mock_router = (
        _make_handler_app_for_name_resolution(
            project_names=["alpha", "beta"],
        )
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "fetch versions project_name=gamma"},
            ]},
        )

    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"]["code"] == "MULTIPLE_PROJECTS"
    # The forced tool was NEVER called — the candidate fetch fired
    # exactly once, no second probe and no execution.
    forced_calls = [
        c for c in call_mock.call_args_list
        if c.args and c.args[0] == "forge_list_versions"
    ]
    assert forced_calls == []
    mock_router.complete_with_tools.assert_not_called()


# ── Integration AC #9: ambiguous name → MULTIPLE_PROJECTS ───────────────


def test_pr29_handler_ambiguous_name_falls_through_to_multiple_projects():
    """When 2+ candidates share the same name, resolution returns
    ``None`` and the handler surfaces MULTIPLE_PROJECTS. The user must
    disambiguate further (e.g. switch to UUID form)."""
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_name_resolution(
            project_names=["alpha", "alpha", "other"],  # collision
        )
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "fetch versions project_name=alpha"},
            ]},
        )

    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"]["code"] == "MULTIPLE_PROJECTS"
    # Belt-and-braces: the candidates list in the envelope still
    # carries all three projects (PR27 contract intact).
    details = body["error"]["details"]
    assert details["type"] == "project"
    assert len(details["candidates"]) == 3
    # No forced execution.
    forced_calls = [
        c for c in call_mock.call_args_list
        if c.args and c.args[0] == "forge_list_versions"
    ]
    assert forced_calls == []


# ── Integration AC #10: name match does NOT call upstream resolver ─────


def test_pr29_handler_name_match_does_not_call_upstream_twice():
    """The name-resolution path must operate on the EXISTING candidate
    list — not issue a second ``forge_list_projects`` probe. Verifies
    the brief's "MUST NOT query upstream again" constraint at the
    integration boundary.

    Expected upstream calls on the success path:
      - 1 × forge_list_projects (initial candidate fetch)
      - 1 × forge_list_versions (the actual forced tool)
    Total: 2. Anything else is a regression."""
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_name_resolution(
            project_names=["chatTest", "other", "third"],
        )
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                # Include "versions" so PR14's filter narrows to
                # forge_list_versions and triggers the forced path.
                {"role": "user", "content": "list versions project_name=chatTest"},
            ]},
        )
    assert r.status_code == 200, r.text

    # Exactly one candidate fetch — no second probe after name resolved.
    probe_calls = [
        c for c in call_mock.call_args_list
        if c.args and c.args[0] == "forge_list_projects"
    ]
    assert len(probe_calls) == 1, (
        f"Expected exactly 1 forge_list_projects call, got {len(probe_calls)}"
    )
    # Total upstream calls is 2: candidate fetch + the forced tool.
    assert call_mock.call_count == 2


# ── Integration AC #11: name match does NOT write memory ────────────────


def test_pr29_handler_name_match_does_not_write_memory():
    """Name-resolved values are CALLER params (extracted from explicit
    user input) and never touch ``_MEMORY``. Same invariant PR28 locks
    for the explicit-UUID path: only deterministic resolutions populate
    the cache, never user-supplied values."""
    assert _MEMORY.get("project_id") is None  # autouse fixture
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_name_resolution(
            project_names=["chatTest", "other"],
        )
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                # PR14 keyword "versions" needed to narrow tools to 1.
                {"role": "user", "content": "list versions project_name=chatTest"},
            ]},
        )
    assert r.status_code == 200, r.text
    # Memory remained untouched.
    assert _MEMORY.get("project_id") is None


def test_pr29_handler_pre_populated_memory_short_circuits_before_name_resolution():
    """When memory already holds ``project_id``, the resolver short-
    circuits BEFORE returning a disambiguation sentinel — so PR29's
    name-resolution branch never fires. This is the brief-conformant
    PR26 precedence behavior: explicit (caller) > memory > resolver,
    and ``project_name=`` only counts as explicit input AT the
    disambiguation branch (when memory couldn't satisfy the
    requirement).

    What this test pins:
      - Memory's ``project_id`` is used (cached id wins, name ignored).
      - The tool's argument dict does NOT carry ``project_name`` —
        the handler pops it before the resolver call so the field
        doesn't leak into the trace or the tool kwargs.
      - Memory itself is unchanged after the request (the autouse
        fixture clears it, but we re-assert here for clarity).

    Why this is the right semantic: PR29 fires "BEFORE returning error"
    on disambiguation (per the brief). If memory short-circuits, no
    disambiguation, no PR29. The user can clear memory (process
    restart) or use the explicit-UUID form (PR28) to override —
    those paths are unambiguously caller-driven."""
    _MEMORY.set("project_id", "memory-cached-id")

    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_name_resolution(
            project_names=["chatTest", "other"],
        )
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                # PR14 keyword "versions" needed to narrow tools to 1.
                {"role": "user", "content": "list versions project_name=chatTest"},
            ]},
        )

    assert r.status_code == 200, r.text
    # Memory's id was used (precedence preserved, brief-conformant).
    call_mock.assert_any_call(
        "forge_list_versions", {"project_id": "memory-cached-id"},
    )
    # Critical: ``project_name`` was popped BEFORE the resolver call,
    # so it never leaks into the tool's argument dict. Inspect every
    # forced-tool call to confirm.
    forced_calls = [
        c for c in call_mock.call_args_list
        if c.args and c.args[0] == "forge_list_versions"
    ]
    assert len(forced_calls) == 1
    assert "project_name" not in forced_calls[0].args[1], (
        "project_name leaked into the tool kwargs — handler "
        "should pop it before resolve_required_params"
    )
    # Pre-existing memory survived untouched.
    assert _MEMORY.get("project_id") == "memory-cached-id"


# ── Trace integrity (mirrors PR28 patch block 5) ────────────────────────


def test_pr29_tool_call_arguments_reflect_resolved_id():
    """The trace's ``tool_calls[0].function.arguments`` reflects the
    NAME-RESOLVED id, not the user-supplied name. Trace consumers
    (audit logs, fbridge chat) need to see what the tool actually
    received — the user-readable name is irrelevant at that layer."""
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_name_resolution(
            project_names=["chatTest", "other"],
        )
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "fetch versions project_name=chatTest"},
            ]},
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assistant_msg = data["messages"][1]
    assert assistant_msg["role"] == "assistant"
    args_str = assistant_msg["tool_calls"][0]["function"]["arguments"]
    args = json.loads(args_str)
    # Trace shows the resolved id — not the user-supplied name.
    assert args == {"project_id": "proj-0"}
    # Defensive — the user's name string must NOT leak into the
    # trace (the trace is for tool inputs, not user inputs).
    assert "chatTest" not in args_str
