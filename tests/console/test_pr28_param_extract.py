"""PR28 — Unit and integration tests for explicit user-supplied parameter
injection (project selection).

Two layers covered:

  - **Unit tests** target ``_param_extract.extract_explicit_params``
    directly. They pin the strict-UUID contract: keyed form precedence,
    bare-UUID single-match fallback, multiple-UUID rejection, malformed
    input pass-through. No fuzzy matching, no name resolution.

  - **Integration tests** drive the chat handler end-to-end with a
    multi-project fixture and verify that an explicit ``project_id=<uuid>``
    in the user message bypasses PR27 disambiguation and PR26 memory
    consultation, executing the forced tool deterministically.

Per the PR28 brief's six tests:
  1. extract_project_id_explicit
  2. extract_project_id_uuid_only
  3. extract_multiple_uuids_returns_empty
  4. extract_invalid_uuid_ignored
  5. multi-project + explicit project_id → executes successfully
  6. explicit project_id → no resolver call
  7. explicit project_id overrides memory
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from forge_bridge.console._memory import _MEMORY
from forge_bridge.console._param_extract import extract_explicit_params
from forge_bridge.console._tool_chain import resolve_required_params
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI


_FIXTURE_UUID = "7ad1756d-7a20-44f1-b4e5-56c8cbc9026e"
_FIXTURE_UUID_B = "11111111-2222-3333-4444-555555555555"


# ── Unit AC #1: explicit project_id=<uuid> form ──────────────────────────


def test_extract_project_id_explicit():
    """``project_id=<uuid>`` is the primary form. Returns a single-key dict
    with the exact UUID the caller wrote — no transformation, no
    normalization."""
    out = extract_explicit_params(f"fetch versions project_id={_FIXTURE_UUID}")
    assert out == {"project_id": _FIXTURE_UUID}


def test_extract_project_id_explicit_with_trailing_text():
    """The keyed candidate is whitespace-terminated; trailing context after
    a space is ignored."""
    out = extract_explicit_params(
        f"please fetch versions project_id={_FIXTURE_UUID} for the hero shots"
    )
    assert out == {"project_id": _FIXTURE_UUID}


def test_extract_project_id_explicit_takes_precedence_over_bare():
    """When the message contains both keyed and a stray bare UUID, the
    keyed value wins — the bare UUID is ignored as incidental context."""
    out = extract_explicit_params(
        f"project_id={_FIXTURE_UUID} (was {_FIXTURE_UUID_B})"
    )
    assert out == {"project_id": _FIXTURE_UUID}


# ── Unit AC #2: bare UUID fallback ───────────────────────────────────────


def test_extract_project_id_uuid_only():
    """A message containing exactly one bare UUID resolves to it as
    ``project_id`` — fallback for users who paste just an id."""
    out = extract_explicit_params(f"fetch versions {_FIXTURE_UUID}")
    assert out == {"project_id": _FIXTURE_UUID}


def test_extract_bare_uuid_at_end_of_message():
    """Position doesn't matter — a single UUID anywhere in the message is
    extracted via the bare-UUID fallback."""
    out = extract_explicit_params(_FIXTURE_UUID)
    assert out == {"project_id": _FIXTURE_UUID}


# ── Unit AC #3: multiple UUIDs → empty (ambiguity preserved) ─────────────


def test_extract_multiple_uuids_returns_empty():
    """Two-or-more bare UUIDs is ambiguous. We refuse to pick — better to
    let PR27's MULTIPLE_PROJECTS envelope fire than to guess.

    Critical contract: the bare-UUID fallback is *single-match-only*. A
    refactor that loosens this (e.g. "pick the first") would silently
    re-introduce the heuristic PR28 explicitly forbids."""
    out = extract_explicit_params(
        f"choose between {_FIXTURE_UUID} and {_FIXTURE_UUID_B}"
    )
    assert out == {}


def test_extract_three_or_more_uuids_returns_empty():
    """The ``len(matches) > 1`` rejection rule applies for any count >1,
    not just N=2. Locks the explicit early-return so a future refactor
    that reverts to ``if len(matches) == 1: ... else: pass`` (which
    happens to behave identically today) doesn't silently re-introduce
    a path that picks the first match."""
    third = "deadbeef-1234-5678-9abc-def012345678"
    msg = f"options: {_FIXTURE_UUID} {_FIXTURE_UUID_B} {third}"
    out = extract_explicit_params(msg)
    assert out == {}
    # Negative assertion — none of the candidates leak through.
    for uid in (_FIXTURE_UUID, _FIXTURE_UUID_B, third):
        assert uid not in out.values()


# ── Unit AC #4: malformed input is ignored (fail-closed) ─────────────────


def test_extract_invalid_uuid_ignored():
    """Strings that look UUID-shaped but aren't valid hex/length must NOT
    match. Returns empty dict — downstream PR22 contract surfaces
    MISSING_PROJECT_ID."""
    # Wrong length
    assert extract_explicit_params("project_id=not-a-uuid") == {}
    # Almost-UUID (one segment short)
    assert extract_explicit_params(
        "project_id=7ad1756d-7a20-44f1-b4e5"
    ) == {}
    # Non-hex character in the middle
    assert extract_explicit_params(
        "project_id=7ad1756d-7a20-44f1-b4e5-56c8cbc9026z"
    ) == {}


def test_extract_keyed_with_trailing_punctuation_resolved_via_keyed_branch():
    """Patch block 7: trailing punctuation (``.``, ``,``, ``;``, ``)``)
    immediately after the UUID is correctly stripped at the candidate
    boundary, so the keyed branch resolves DIRECTLY — no fallthrough to
    the bare-UUID fallback.

    Pre-patch behavior used ``str.split(maxsplit=1)`` (whitespace-only),
    which left punctuation glued to the UUID and forced fullmatch failure.
    The end-state was still correct (bare-UUID fallback rescued the value),
    but the path was wrong: an ambiguous multi-UUID message with one
    keyed-form UUID would have been silently rejected as ambiguous when
    the explicit selector was right there.

    The boundary regex ``[^\\w-]`` keeps the candidate strictly inside
    the UUID-allowed alphabet — anything that isn't ``[A-Za-z0-9_-]``
    terminates the candidate."""
    # Sweep the punctuation chars the brief calls out plus a few more
    # that real users actually type (semicolon for list separators,
    # close-paren for inline references).
    for trailing in (".", ",", ";", ")", "?", "!"):
        msg = f"fetch versions project_id={_FIXTURE_UUID}{trailing}"
        out = extract_explicit_params(msg)
        assert out == {"project_id": _FIXTURE_UUID}, (
            f"trailing {trailing!r} failed: got {out!r}"
        )


def test_extract_keyed_form_resolves_with_trailing_comma_in_ambiguous_context():
    """Regression lock for the path the patch is really protecting: a
    message with multiple bare UUIDs but one explicit ``project_id=``
    selector. Pre-patch this would have hit the multi-UUID rejection
    rule and returned ``{}`` because the keyed candidate (with trailing
    comma) failed fullmatch and the fallback found 2 UUIDs.

    Post-patch the keyed branch resolves the explicit selector directly,
    so the user's intent (one UUID is THE answer, the other is incidental
    context) is honored."""
    msg = (
        f"fetch versions project_id={_FIXTURE_UUID}, "
        f"not the older one {_FIXTURE_UUID_B}"
    )
    out = extract_explicit_params(msg)
    assert out == {"project_id": _FIXTURE_UUID}


def test_extract_empty_or_non_string_input():
    """Defensive: empty string and non-string inputs return empty dict
    without raising. Caller (handler) passes ``last_user_text`` which can
    be ``""`` when no user message is present."""
    assert extract_explicit_params("") == {}
    assert extract_explicit_params(None) == {}  # type: ignore[arg-type]


def test_extract_zero_uuids_returns_empty():
    """A message with no UUID-shaped content yields an empty dict — the
    overwhelming majority of real-world chat messages take this path."""
    assert extract_explicit_params("just chatting, no ids here") == {}


def test_extract_uppercase_uuid_accepted():
    """Canonical UUIDs are case-insensitive; uppercase hex is valid input.
    The extractor returns the value verbatim — no case normalization
    (the caller's value is the value the downstream tool sees)."""
    upper = _FIXTURE_UUID.upper()
    out = extract_explicit_params(f"project_id={upper}")
    assert out == {"project_id": upper}


# ── Whitespace + key-case normalization (PR28 patch block 2) ─────────────


def test_extract_strips_leading_and_trailing_whitespace():
    """Leading/trailing whitespace is stripped before parsing — a chat
    client's ``"\\n"`` framing or copy-paste padding must not change
    the parser's behavior."""
    out = extract_explicit_params(f"  \n  project_id={_FIXTURE_UUID}  \n")
    assert out == {"project_id": _FIXTURE_UUID}


def test_extract_whitespace_only_message_returns_empty():
    """A message that is only whitespace strips to empty and returns
    ``{}`` — same end-state as ``""``."""
    assert extract_explicit_params("   \n\t  ") == {}


def test_extract_keyed_form_is_case_insensitive():
    """The KEY ``project_id=`` matches case-insensitively. ``PROJECT_ID=``,
    ``Project_Id=``, etc. are all valid. UUID value preserves its case."""
    upper = _FIXTURE_UUID.upper()
    out = extract_explicit_params(f"PROJECT_ID={upper}")
    assert out == {"project_id": upper}

    mixed = extract_explicit_params(f"Project_Id={_FIXTURE_UUID}")
    assert mixed == {"project_id": _FIXTURE_UUID}


def test_extract_uppercase_key_with_uppercase_uuid_preserves_case():
    """End-to-end case preservation: uppercase key + uppercase UUID →
    UUID is returned verbatim with its original case. The KEY is matched
    case-insensitively but the VALUE is sliced from the original text."""
    upper_uuid = _FIXTURE_UUID.upper()
    out = extract_explicit_params(
        f"please use PROJECT_ID={upper_uuid} for this run"
    )
    assert out == {"project_id": upper_uuid}


# ── Resolver-level memory-write contract lock (patch block 4) ───────────


def _text_block(text: str):
    """TextContent helper for mocked ``mcp.call_tool`` returns. Mirrors
    the helper in PR26/PR27 unit tests to keep fixture shapes aligned."""
    from mcp.types import TextContent
    return [TextContent(type="text", text=text)]


def _make_mcp(project_count: int) -> Any:
    """Mock with `mcp.call_tool` returning a TextContent block matching
    the requested project count for `forge_list_projects`. Mirrors the
    PR26 / PR27 helpers exactly so memory-related assertions stay
    comparable across the test surfaces."""
    mcp = AsyncMock()

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_projects_payload(project_count))
        return _text_block(json.dumps({"called": name, "args": arguments}))

    mcp.call_tool = AsyncMock(side_effect=fake_call_tool)
    return mcp


@pytest.mark.asyncio
async def test_pr28_explicit_project_id_does_not_write_memory():
    """Resolver contract lock: when caller params satisfy the requirement
    explicitly, ``resolve_required_params`` MUST NOT write to memory.

    This is the test PR28 patch block 4 calls out by name. PR26's
    test_pr26_caller_params_take_precedence_over_memory covers the same
    invariant at the precedence-chain level; this test pins it from the
    PR28 angle: a UUID extracted from the user message becomes caller
    params, and those caller params must never silently populate
    ``_MEMORY``. A regression here would couple user input to cached
    state — exactly the silent path the PR28 brief forbids.

    Run regardless of system state (single-project here, but the
    invariant must hold across all project counts — see the integration
    test ``test_pr28_handler_explicit_project_id_does_not_write_memory``
    for the multi-project case)."""
    _MEMORY.clear()  # autouse fixture also handles this; explicit per brief

    mcp = _make_mcp(project_count=1)

    params = {"project_id": _FIXTURE_UUID}
    out = await resolve_required_params("forge_list_versions", params, mcp)

    # Caller's value flowed through unchanged (precedence sanity).
    assert out == {"project_id": _FIXTURE_UUID}
    # No upstream probe — resolver short-circuited on satisfied requirement.
    mcp.call_tool.assert_not_called()
    # The contract lock — memory must remain empty.
    assert _MEMORY.get("project_id") is None


# ── Integration helpers (mirror PR27 fixture shape) ──────────────────────


def _projects_payload(count: int) -> str:
    if count == 0:
        projects: list[dict] = []
    else:
        projects = [
            {"id": f"proj-{i}", "name": f"P{i}", "code": f"P{i}"}
            for i in range(count)
        ]
    return json.dumps({"count": len(projects), "projects": projects})


def _passthrough_filter(tools, **_):
    return tools


def _make_handler_app_for_param_injection(project_count: int):
    """Build a chat-handler app whose tool registry contains a single
    forced-execution target (``forge_list_versions``) and a stubbed
    ``mcp.call_tool`` that returns the requested project count from
    ``forge_list_projects``.

    Mirrors the PR27 fixture so behavior diffs between PR27 disambiguation
    and PR28 explicit-injection are easy to read."""
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
            return [TextContent(type="text", text=_projects_payload(project_count))]
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


# ── Integration AC #5: multi-project + explicit project_id → executes ───


def test_pr28_handler_explicit_project_id_executes_with_multiple_projects():
    """End-to-end: a multi-project deployment + an explicit
    ``project_id=<uuid>`` in the user message → handler skips PR27
    disambiguation and forces ``forge_list_versions`` with the caller's
    value. 200 + ``tool_forced=True`` instead of 400 MULTIPLE_PROJECTS."""
    list_p, back_p, call_p, app, mock_router = (
        _make_handler_app_for_param_injection(project_count=5)
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": (
                    f"forge fetch versions project_id={_FIXTURE_UUID}"
                )},
            ]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    # The forced tool ran with the EXPLICIT id — not any of the upstream
    # candidates. PR27 disambiguation never fired.
    call_mock.assert_called_with(
        "forge_list_versions", {"project_id": _FIXTURE_UUID},
    )
    mock_router.complete_with_tools.assert_not_called()


# ── Integration AC #6: explicit project_id → no resolver call ───────────


def test_pr28_handler_explicit_project_id_skips_upstream_probe():
    """When the caller supplies ``project_id`` explicitly, the resolver
    short-circuits before the upstream ``forge_list_projects`` probe.
    Verifies the PR26 precedence (explicit > memory > resolver) carries
    through the PR28 wiring."""
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_param_injection(project_count=3)
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": (
                    f"fetch versions project_id={_FIXTURE_UUID}"
                )},
            ]},
        )

    assert r.status_code == 200, r.text
    # The probe was NEVER issued — only the actual forced tool ran.
    probe_calls = [
        c for c in call_mock.call_args_list
        if c.args and c.args[0] == "forge_list_projects"
    ]
    assert probe_calls == [], (
        f"Expected zero forge_list_projects probes, got {len(probe_calls)}"
    )
    # Only the forced tool was called.
    call_mock.assert_called_once_with(
        "forge_list_versions", {"project_id": _FIXTURE_UUID},
    )


def test_pr28_handler_explicit_project_id_does_not_write_memory():
    """Explicit caller params NEVER write to memory — preserves PR26's
    invariant that only deterministic resolutions populate the cache."""
    assert _MEMORY.get("project_id") is None  # autouse fixture
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_param_injection(project_count=2)
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": (
                    f"versions project_id={_FIXTURE_UUID}"
                )},
            ]},
        )
    assert r.status_code == 200, r.text
    # Memory remained untouched — caller-supplied values are not cached.
    assert _MEMORY.get("project_id") is None


# ── Integration AC #7: explicit project_id overrides memory ─────────────


def test_pr28_handler_explicit_project_id_overrides_memory():
    """PR26 precedence: explicit > memory > resolver. A pre-populated
    memory entry must NOT shadow an explicit ``project_id=<uuid>`` from
    the user message — the caller's value wins."""
    _MEMORY.set("project_id", "memory-cached-id")

    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_param_injection(project_count=3)
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": (
                    f"versions project_id={_FIXTURE_UUID}"
                )},
            ]},
        )

    assert r.status_code == 200, r.text
    # Forced tool got the EXPLICIT value, not the memory value.
    call_mock.assert_called_once_with(
        "forge_list_versions", {"project_id": _FIXTURE_UUID},
    )
    # Pre-existing memory survived untouched (caller-supplied never writes).
    assert _MEMORY.get("project_id") == "memory-cached-id"


# ── Trace integrity: tool_calls.arguments reflects injected params ──────


def test_pr28_tool_call_arguments_match_explicit_param():
    """PR20/PR28 trace integrity: the assistant message in the response
    carries a ``tool_calls[0].function.arguments`` JSON string that
    reflects the EXACT params the tool was called with — including any
    PR28-injected ``project_id``.

    Why outward-only: the brief explicitly says "do not inspect internal
    state". Trace consumers (the wrapper trace summary, fbridge chat,
    audit logs) read this body shape; if injection silently desyncs from
    the trace, debugging a forced-execution failure becomes a guessing
    game. Pin the substring match so a future change that, say, drops
    the tool_calls envelope or stops passing user_params through to
    `_execute_forced_tool` fails loudly here."""
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_param_injection(project_count=3)
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": (
                    f"fetch versions project_id={_FIXTURE_UUID}"
                )},
            ]},
        )

    assert r.status_code == 200, r.text
    data = r.json()

    # Echoed history shape: [user, assistant(tool_calls), tool(result)].
    # The assistant entry sits at index 1 — the brief locks this index
    # explicitly so a refactor that prepends extra messages (e.g. an
    # injected system note) shows up here as a structural change rather
    # than silently shifting the trace.
    assistant_msg = data["messages"][1]
    assert assistant_msg["role"] == "assistant"
    calls = assistant_msg["tool_calls"]
    assert len(calls) == 1
    args = calls[0]["function"]["arguments"]

    # Substring match — outward-only verification per the brief. The
    # arguments are JSON-encoded (``json.dumps(params)``) so the UUID
    # surfaces as a literal substring inside the string.
    assert _FIXTURE_UUID in args
    # Belt-and-braces: the function name is also locked so a refactor
    # that swaps the forced tool doesn't drop into the substring win
    # accidentally.
    assert calls[0]["function"]["name"] == "forge_list_versions"


# ── Sanity: existing PR27 path still fires with no explicit param ───────


def test_pr28_handler_no_explicit_param_falls_through_to_pr27():
    """Sanity check: when the user does NOT supply an explicit
    ``project_id``, the handler still falls through to PR27's
    MULTIPLE_PROJECTS envelope. PR28 is purely additive — it does not
    change behavior for messages without an explicit selector."""
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_param_injection(project_count=4)
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )

    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"]["code"] == "MULTIPLE_PROJECTS"
