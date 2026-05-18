"""Tests for the `flame_execute_python` MCP tool — Phase 23.1.

The function `execute_python` has lived in `forge_bridge/tools/utility.py`
since pre-23.1 but was never registered with the MCP server. 23.1 ships
two changes:

  1. Docstring rewrite — 3 worked examples + structured "use ONLY when /
     do NOT use" guidance, so the LLM has enough signal to pattern-match
     the tool when no narrow flame_* tool fits.
  2. Registration — alongside other flame_* tools in
     `forge_bridge/mcp/registry.py`, under MCP name `flame_execute_python`
     with `readOnlyHint=False` (honest annotation: tool CAN mutate via
     main_thread=True).

These tests are the regression surface for both — if a future cleanup
strips the worked examples or drops the registration, the chat surface
silently reverts to the pre-23.1 unusability.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from forge_bridge import bridge
from forge_bridge.tools import utility
from forge_bridge.tools.utility import ExecutePythonInput, execute_python


# ── Function-shape invariants (rarely change) ────────────────────────────


def test_execute_python_callable_and_async():
    """Post-23.1-in-flight: the function takes flat kwargs (code, main_thread),
    NOT a wrapped ExecutePythonInput. FastMCP introspects the signature to
    generate the MCP JSON schema; a flat signature → flat schema → model
    can generate the args correctly."""
    import inspect
    assert inspect.iscoroutinefunction(execute_python)
    sig = inspect.signature(execute_python)
    params = list(sig.parameters.values())
    # Must be FLAT — direct `code` + `main_thread` kwargs, no wrapper.
    assert [p.name for p in params] == ["code", "main_thread"], (
        f"signature is not flat — got {[p.name for p in params]}. "
        f"FastMCP will generate a nested JSON schema and the chat model "
        f"will fail to call this tool (Phase 23.1 in-flight gap fix)."
    )
    # `code` is required (no default); `main_thread` has a False default.
    code_param = sig.parameters["code"]
    main_thread_param = sig.parameters["main_thread"]
    assert code_param.default is inspect.Parameter.empty
    assert main_thread_param.default is False


def test_execute_python_input_back_compat_model_still_exists():
    """ExecutePythonInput is retained post-23.1-in-flight for direct-Python
    callers that constructed it pre-23.1, but it is NO LONGER the function
    signature. Schema-shape assertions on the back-compat model — preserved
    so the back-compat surface doesn't accidentally drift."""
    schema = ExecutePythonInput.model_json_schema()
    assert "code" in schema["properties"]
    assert "main_thread" in schema["properties"]
    assert schema["properties"]["code"]["type"] == "string"
    assert schema["properties"]["main_thread"]["type"] == "boolean"
    # `code` is required; `main_thread` has a default → not required.
    required = schema.get("required", [])
    assert "code" in required
    assert "main_thread" not in required


def test_flame_execute_python_mcp_schema_is_flat_not_nested():
    """LOAD-BEARING 23.1 invariant. FastMCP introspects the function
    signature to build the JSON schema the LLM sees. Pre-23.1-in-flight,
    the signature was `execute_python(params: ExecutePythonInput)` which
    generated a NESTED schema requiring `{"params": {"code": "..."}}`.
    The chat model consistently generated the flat `{"code": "..."}`
    shape and pydantic-validation failed at MCP dispatch BEFORE the
    function body ran — every chat tool_error event was a silent
    schema-mismatch failure with zero tool-wrapper log records.

    The flat signature generates a flat schema. This test pins that
    invariant — if a future refactor re-wraps the signature, the model
    will silently fail again. Catch it here, not in production.
    """
    import json

    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)
    tool = mcp._tool_manager._tools["flame_execute_python"]

    # FastMCP exposes the schema as `parameters` on the Tool object.
    # Walk the candidate attrs and pick whichever is non-None.
    schema = None
    for attr in ("parameters", "input_schema", "inputSchema"):
        candidate = getattr(tool, attr, None)
        if candidate:
            schema = candidate if isinstance(candidate, dict) else (
                candidate() if callable(candidate) else None
            )
            break
    assert schema is not None, "could not extract MCP schema from FastMCP tool"

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # FLAT — direct `code` + `main_thread` keys at the top level, NOT a
    # nested `params` wrapper.
    assert "code" in properties, (
        f"MCP schema MUST expose `code` as a top-level property; got: "
        f"{json.dumps(properties, indent=2)}"
    )
    assert "main_thread" in properties, (
        f"MCP schema MUST expose `main_thread` as a top-level property; "
        f"got: {json.dumps(properties, indent=2)}"
    )
    assert "params" not in properties, (
        f"REGRESSION: MCP schema has a nested `params` wrapper. The "
        f"function signature was probably refactored back to "
        f"`execute_python(params: ExecutePythonInput)`. Revert to flat "
        f"kwargs — see Phase 23.1 in-flight gap-fix archaeology."
    )
    assert "code" in required, "code must be required at the top level"
    # main_thread has a default, so should NOT be required.
    assert "main_thread" not in required


# ── Docstring contract (23.1 worked examples must survive cleanup) ───────


# ── Canonical regression query (load-bearing operational test) ────────────
#
# Phase 23.1 post-walk repositioning identified this query as load-bearing
# for the entire chat-convergence story — it tests semantic retrieval, tool
# ranking, introspection escalation, runtime convergence, and graph
# completeness in one sentence. If forge-bridge can't answer it naturally,
# the graph-native runtime story is not yet operationally believable.
#
# Pinned as a constant so future regression work has a stable reference.
# v1.6+ should promote this to a fixtures module or CI smoke path; see
# SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+.md.

CANONICAL_FLAME_INTROSPECTION_QUERY = "What are the clips on Reel 1"


def test_docstring_contains_three_worked_examples():
    """If a future docstring cleanup drops examples, the LLM loses pattern-
    match material and chat regresses to pre-23.1 unusability. Pin all
    three example markers."""
    doc = execute_python.__doc__ or ""
    assert "Example 1" in doc
    assert "Example 2" in doc
    assert "Example 3" in doc


def test_docstring_teaches_canonical_positioning_not_escape_hatch():
    """Post-walk repositioning (23.1, in-flight per D-20; refined 24.6 per
    affordance-selection-sharpening framing): the docstring's opening must
    position this tool as the canonical Flame introspection surface, NOT as
    a generic escape hatch / dangerous code execution primitive. The model
    reads the opening as positioning; without canonical-surface framing it
    treats this tool as a last-resort fallback rather than the right answer
    to Flame state questions.

    Specifically pins:
      - Canonical-surface framing in the opening tagline ('canonical
        introspection surface', per 24.6 — replaced 23.1's 'universal Flame
        introspection and automation surface' as part of rhetorical inversion
        that fronts concrete capabilities before universality)
      - The 'canonical answer' positioning relative to dedicated flame_* tools
      - The 'reflective surface of Flame itself' generalization
    """
    doc = execute_python.__doc__ or ""
    # Canonical positioning, not escape-hatch language.
    assert "canonical introspection surface" in doc, (
        "lost canonical-surface positioning in opening tagline; the model "
        "will read this tool as escape-hatch-shaped and skip it for "
        "introspection queries"
    )
    assert "canonical answer" in doc.lower(), (
        "lost the 'canonical answer' positioning relative to dedicated tools"
    )
    assert "reflective surface of Flame itself" in doc, (
        "lost the introspection-generalization sentence"
    )


def test_docstring_teaches_when_to_use_and_when_not_to():
    """The structured guidance is what the LLM reads to pick this tool
    over the narrow flame_* tools. Post-walk repositioning replaced
    'Use this tool when' with an escalation rule that teaches when to
    reach for this tool vs the narrow flame_* surface. Both forms are
    acceptable; what's NOT acceptable is dropping the escalation rule
    entirely.

    Whitespace is normalized before substring checks because intentional
    paragraph rewrapping (e.g. the 24.6 rhetorical inversion) can split
    the escalation phrase across a line break without changing its meaning.
    """
    doc = execute_python.__doc__ or ""
    # Normalize whitespace so line-wrapping changes don't break semantic checks.
    normalized = " ".join(doc.split())
    # The escalation rule — load-bearing for tool selection.
    assert "no dedicated flame_* tool directly exposes" in normalized, (
        "lost the escalation rule that teaches the model when to escalate "
        "to this tool from narrow flame_* tools"
    )
    assert "Do NOT use this tool when:" in doc


def test_docstring_includes_canonical_use_case_section():
    """Post-walk: domain-shaped use cases (reel inspection, clip enumeration,
    timeline traversal, batch graph traversal, sequence inspection) bridge
    operator domain vocabulary to tool affordance. Without these, the
    PR14-passes-all-tools fallback still leaves the model unable to map
    domain queries to this tool."""
    doc = execute_python.__doc__ or ""
    assert "Canonical use cases:" in doc
    # The five load-bearing domain anchors. If any goes missing, the
    # corresponding domain query may regress.
    for anchor in (
        "reel inspection",
        "clip enumeration",
        "timeline traversal",
        "batch graph traversal",
        "sequence inspection",
    ):
        assert anchor in doc, (
            f"lost canonical use-case anchor: {anchor!r} — the LLM may "
            f"fail to map the corresponding operator query to this tool"
        )


def test_docstring_pins_canonical_regression_query_verbatim():
    """The exact phrase 'Reel 1' from the dogfood-23.1-walk query must
    appear in Example 1. This is the operational regression-pin: if the
    canonical query string drifts out of the docstring, the LLM may stop
    pattern-matching against the exact form artists use."""
    doc = execute_python.__doc__ or ""
    # 'Reel 1' — the literal name format in the canonical query.
    assert "Reel 1" in doc
    # The "list clip names" framing — surfaces the noun "clip names" the
    # operator uses, bridging operator domain → tool example.
    assert "list clip names" in doc.lower()


def test_canonical_regression_query_constant_is_stable():
    """The constant should hold the exact query string used in the
    Phase 23.1 author-walk. v1.6+ may promote this to a shared fixtures
    module; until then, this is the single source of truth."""
    assert CANONICAL_FLAME_INTROSPECTION_QUERY == "What are the clips on Reel 1"
    # The constant's domain terms should also appear in the docstring,
    # so the canonical query and the docstring co-evolve.
    doc = execute_python.__doc__ or ""
    assert "Reel 1" in doc
    assert "clip" in doc.lower()


# ── Response-shape invariants (wraps bridge.execute correctly) ───────────


class _FakeBridgeResponse:
    """Mimic forge_bridge.bridge.BridgeResponse for the success path."""
    def __init__(self, stdout="", stderr="", result=None, error=None, traceback=None):
        self.stdout = stdout
        self.stderr = stderr
        self.result = result
        self.error = error
        self.traceback = traceback


@pytest.mark.asyncio
async def test_execute_python_returns_json_with_stdout_stderr_result():
    """Happy path — wrapping yields a JSON string with the three core fields."""
    import json
    fake = _FakeBridgeResponse(stdout="hello\n", stderr="", result=None)
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        out = await execute_python(code="print('hello')")
    parsed = json.loads(out)
    assert parsed["stdout"] == "hello\n"
    assert parsed["stderr"] == ""
    assert parsed["result"] is None
    # No error key on success.
    assert "error" not in parsed
    assert "traceback" not in parsed


@pytest.mark.asyncio
async def test_execute_python_includes_error_and_traceback_on_flame_exception():
    """When the snippet raises inside Flame, bridge returns error+traceback;
    the tool surface MUST propagate both so the LLM can see what failed."""
    import json
    fake = _FakeBridgeResponse(
        stdout="", stderr="",
        result=None,
        error="NameError: name 'flam' is not defined",
        traceback="Traceback (most recent call last):\n  ...",
    )
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        out = await execute_python(code="flam.foo()")
    parsed = json.loads(out)
    assert parsed["error"] == "NameError: name 'flam' is not defined"
    assert "Traceback" in parsed["traceback"]


@pytest.mark.asyncio
async def test_execute_python_passes_main_thread_param_through():
    """The main_thread param routes through to bridge.execute — required
    for write operations. Default is False; True must propagate."""
    fake = _FakeBridgeResponse(stdout="ok", stderr="", result=None)
    mock = AsyncMock(return_value=fake)
    with patch.object(utility.bridge, "execute", new=mock):
        await execute_python(code="x=1", main_thread=True)
    # Bridge.execute called with main_thread=True (kwarg, not positional).
    assert mock.call_args.kwargs.get("main_thread") is True


@pytest.mark.asyncio
async def test_execute_python_default_main_thread_is_false():
    """Read-only-safe default: main_thread=False unless explicitly set."""
    fake = _FakeBridgeResponse(stdout="ok", stderr="", result=None)
    mock = AsyncMock(return_value=fake)
    with patch.object(utility.bridge, "execute", new=mock):
        await execute_python(code="x=1")
    assert mock.call_args.kwargs.get("main_thread") is False


# ── MCP registration (the function is exposed to the LLM) ────────────────


def test_flame_execute_python_registered_on_mcp_server():
    """Phase 23.1 — the function MUST be registered under the canonical
    MCP name `flame_execute_python`. Pre-23.1 the function existed in
    utility.py but was never registered → the LLM was blind to it →
    chat couldn't converge on simple Flame introspection queries."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)

    # FastMCP exposes registered tools via _tool_manager._tools (private but
    # stable across the versions forge-bridge pins).
    tool_names = set(mcp._tool_manager._tools.keys())
    assert "flame_execute_python" in tool_names, (
        f"flame_execute_python missing from registry; have: "
        f"{sorted(n for n in tool_names if n.startswith('flame_'))}"
    )


def test_flame_execute_python_registered_as_not_readonly():
    """readOnlyHint=False is the honest annotation — the tool CAN mutate
    via main_thread=True even though the docstring biases toward reads."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)

    tool = mcp._tool_manager._tools["flame_execute_python"]
    annotations = getattr(tool, "annotations", None)
    # annotations may be a pydantic model or a dict depending on FastMCP version.
    if hasattr(annotations, "readOnlyHint"):
        assert annotations.readOnlyHint is False
    elif isinstance(annotations, dict):
        assert annotations.get("readOnlyHint") is False
    else:
        pytest.fail(f"Unexpected annotations shape: {type(annotations)}")


def test_flame_execute_python_source_is_builtin():
    """Builtin source — distinguishes from synthesized + user-taught tools."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)

    tool = mcp._tool_manager._tools["flame_execute_python"]
    meta = getattr(tool, "_meta", None) or getattr(tool, "meta", None)
    if isinstance(meta, dict):
        assert meta.get("_source") == "builtin"
    else:
        # Fall back to checking the tool's exported metadata via FastMCP.
        # If the meta isn't accessible by direct attribute, skip — the
        # registration code paths are independently tested in
        # tests/test_mcp_registry.py.
        pytest.skip("FastMCP tool meta not directly accessible in this version")


# ── Phase 23.1 observability instrumentation ─────────────────────────────
#
# Every invocation logs code_hash + main_thread + elapsed_ms + status +
# code_len so post-walk diagnostics correlate per-call behavior without
# re-running the failure. SEED-FLAME-EXEC-OBSERVABILITY-V1.6+ captures the
# richer instrumentation (queue-wait timing, hook-side per-stage breakdown)
# deferred to v1.6's observability phase because it requires hook protocol
# cooperation.


@pytest.mark.asyncio
async def test_execute_python_logs_invocation_telemetry(caplog):
    """Each call emits a structured log record with the five Phase 23.1
    observability fields. Test pins the exact field set so a future log-
    format refactor cannot silently drop instrumentation operators rely on."""
    import logging
    fake = _FakeBridgeResponse(stdout="hello\n", stderr="", result=None)
    with caplog.at_level(logging.INFO, logger="forge_bridge.tools.utility"):
        with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
            await execute_python(code="print('hello')")

    # Find the flame_execute_python log line.
    invocation_logs = [
        r for r in caplog.records
        if r.name == "forge_bridge.tools.utility"
        and "flame_execute_python" in r.message
    ]
    assert len(invocation_logs) == 1, (
        f"expected exactly one flame_execute_python invocation log; "
        f"got {len(invocation_logs)} (records: {[r.message for r in caplog.records]})"
    )
    msg = invocation_logs[0].message
    # The five load-bearing observability fields.
    assert "code_hash=" in msg
    assert "main_thread=" in msg
    assert "elapsed_ms=" in msg
    assert "status=" in msg
    assert "code_len=" in msg


@pytest.mark.asyncio
async def test_execute_python_logs_status_ok_on_clean_success(caplog):
    """status=ok when bridge returns no error."""
    import logging
    fake = _FakeBridgeResponse(stdout="hello\n", stderr="", result=None)
    with caplog.at_level(logging.INFO, logger="forge_bridge.tools.utility"):
        with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
            await execute_python(code="print('hello')")
    msg = next(
        r.message for r in caplog.records
        if "flame_execute_python" in r.message
    )
    assert "status=ok" in msg


@pytest.mark.asyncio
async def test_execute_python_logs_status_flame_error_on_flame_exception(caplog):
    """status=flame_error when Flame-side Python raised — the tool returns
    cleanly (error in JSON envelope) but the model should see this as a
    distinct status from a clean run."""
    import logging
    fake = _FakeBridgeResponse(
        stdout="", stderr="",
        result=None,
        error="NameError: name 'flam' is not defined",
        traceback="Traceback (most recent call last):\n  ...",
    )
    with caplog.at_level(logging.INFO, logger="forge_bridge.tools.utility"):
        with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
            await execute_python(code="flam.foo()")
    msg = next(
        r.message for r in caplog.records
        if "flame_execute_python" in r.message
    )
    assert "status=flame_error" in msg


@pytest.mark.asyncio
async def test_execute_python_logs_status_transport_error_on_bridge_exception(caplog):
    """status=transport_error when bridge.execute raises. This is what the
    chat router surfaces as `status=tool_error` in its per-iteration log —
    the 23.1 instrumentation lets operators correlate that event with the
    tool-side cause without cross-referencing two log streams."""
    import logging
    mock = AsyncMock(side_effect=bridge.BridgeConnectionError("transport boom"))
    with caplog.at_level(logging.INFO, logger="forge_bridge.tools.utility"):
        with patch.object(utility.bridge, "execute", new=mock):
            with pytest.raises(bridge.BridgeConnectionError):
                await execute_python(code="anything")
    msg = next(
        r.message for r in caplog.records
        if "flame_execute_python" in r.message
    )
    assert "status=transport_error" in msg


@pytest.mark.asyncio
async def test_execute_python_logs_main_thread_flag_value(caplog):
    """The main_thread flag value flows through to the log so operators can
    spot 'model is defaulting to main_thread=True on reads' patterns."""
    import logging
    fake = _FakeBridgeResponse(stdout="ok", stderr="", result=None)
    with caplog.at_level(logging.INFO, logger="forge_bridge.tools.utility"):
        with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
            await execute_python(code="x=1", main_thread=True)
    msg = next(
        r.message for r in caplog.records
        if "flame_execute_python" in r.message
    )
    assert "main_thread=True" in msg


@pytest.mark.asyncio
async def test_execute_python_code_hash_is_deterministic_per_snippet(caplog):
    """Same snippet → same hash. Different snippets → different hashes.
    Lets operators group log lines by snippet identity across runs."""
    import logging
    fake = _FakeBridgeResponse(stdout="ok", stderr="", result=None)
    snippet_a = "print('a')"
    snippet_b = "print('b')"
    with caplog.at_level(logging.INFO, logger="forge_bridge.tools.utility"):
        with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
            await execute_python(code=snippet_a)
            await execute_python(code=snippet_a)
            await execute_python(code=snippet_b)

    hashes = []
    for r in caplog.records:
        if "flame_execute_python" in r.message:
            # Extract code_hash=<16chars> from message
            for token in r.message.split():
                if token.startswith("code_hash="):
                    hashes.append(token.split("=", 1)[1])
    assert len(hashes) == 3
    assert hashes[0] == hashes[1], "same snippet should produce same hash"
    assert hashes[0] != hashes[2], "different snippets should produce different hashes"
    # Hash is 16-char hex (sha256 prefix).
    for h in hashes:
        assert len(h) == 16
        int(h, 16)  # raises if non-hex


# ── Phase 24 Commit 2: graph-event emission ─────────────────────────────
#
# Two events emit per execute_python call: `started` at entry, terminal
# status at exit (`ok` / `flame_error` / `transport_error`). Records land
# in ~/.forge-bridge/graphs/<graph_id>.jsonl (FORGE_GRAPH_DIR override
# honored by the substrate). The Phase 23.1 stderr structured log line
# stays unchanged — these tests verify the additional JSONL substrate,
# not a replacement.


def _read_jsonl_records(jsonl_path):
    import json
    return [json.loads(line) for line in jsonl_path.read_text().splitlines()]


@pytest.mark.asyncio
async def test_execute_python_emits_started_event_at_entry(monkeypatch, tmp_path):
    """Entry-side emit: status='started', payload carries code_hash +
    main_thread + code_len so post-walk diagnostics can correlate per-
    attempt records even if the call never completes."""
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))
    fake = _FakeBridgeResponse(stdout="ok", stderr="", result=None)
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        await execute_python(code="print('hi')")
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1, "exactly one graph file per call (one-graph-per-call at this phase)"
    records = _read_jsonl_records(files[0])
    assert len(records) >= 1
    started_evt = records[0]
    assert started_evt["status"] == "started"
    # node_kind is substrate-level (Python execution against Flame), NOT
    # MCP tool name. See utility.py entry-emit comment + v1.6-FRAMING.md §4.
    assert started_evt["node_kind"] == "python"
    assert started_evt["payload"]["main_thread"] is False
    assert started_evt["payload"]["code_len"] == len("print('hi')")
    assert len(started_evt["payload"]["code_hash"]) == 16


@pytest.mark.asyncio
async def test_execute_python_emits_ok_terminal_event_on_success(monkeypatch, tmp_path):
    """Success path: terminal event has status='ok' and elapsed_ms in payload."""
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))
    fake = _FakeBridgeResponse(stdout="x", stderr="", result=None)
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        await execute_python(code="print('x')")
    files = list(tmp_path.glob("*.jsonl"))
    records = _read_jsonl_records(files[0])
    assert len(records) == 2
    terminal = records[1]
    assert terminal["status"] == "ok"
    assert terminal["node_kind"] == "python"
    assert isinstance(terminal["payload"]["elapsed_ms"], int)
    assert terminal["payload"]["elapsed_ms"] >= 0


@pytest.mark.asyncio
async def test_execute_python_emits_flame_error_terminal_on_flame_exception(
    monkeypatch, tmp_path,
):
    """Flame-side Python raised but transport returned cleanly:
    terminal status='flame_error' (matches Phase 23.1 stderr-log convention)."""
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))
    fake = _FakeBridgeResponse(
        stdout="", stderr="", result=None,
        error="NameError: bad", traceback="Traceback...",
    )
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        await execute_python(code="bad()")
    files = list(tmp_path.glob("*.jsonl"))
    records = _read_jsonl_records(files[0])
    assert len(records) == 2
    assert records[1]["status"] == "flame_error"


@pytest.mark.asyncio
async def test_execute_python_emits_transport_error_terminal_on_bridge_raise(
    monkeypatch, tmp_path,
):
    """Transport-layer failure (bridge.execute raised): terminal status=
    'transport_error'. The tool surface re-raises so the MCP/CLI consumer
    still sees the failure — the graph event is observability AROUND that
    failure, not a substitute for it."""
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))

    class _BadConnection(Exception):
        pass

    with patch.object(
        utility.bridge, "execute",
        new=AsyncMock(side_effect=_BadConnection("refused")),
    ):
        with pytest.raises(_BadConnection):
            await execute_python(code="x=1")
    files = list(tmp_path.glob("*.jsonl"))
    records = _read_jsonl_records(files[0])
    assert len(records) == 2
    assert records[0]["status"] == "started"
    assert records[1]["status"] == "transport_error"


@pytest.mark.asyncio
async def test_execute_python_started_and_terminal_share_graph_id(monkeypatch, tmp_path):
    """Both events emit to the same graph_id (one graph per call at this
    phase). The JSONL file is therefore named for the shared graph_id."""
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))
    fake = _FakeBridgeResponse(stdout="x", stderr="", result=None)
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        await execute_python(code="print('x')")
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    records = _read_jsonl_records(files[0])
    gid = records[0]["graph_id"]
    assert records[1]["graph_id"] == gid
    assert files[0].name == f"{gid}.jsonl"
    # Distinct event_ids within the shared graph.
    assert records[0]["event_id"] != records[1]["event_id"]


@pytest.mark.asyncio
async def test_execute_python_distinct_calls_emit_to_distinct_graph_files(
    monkeypatch, tmp_path,
):
    """Each call gets its own graph_id at this phase (chat-session graph
    propagation lands in a later commit). Two successful calls → two
    JSONL files, two graph_ids."""
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))
    fake = _FakeBridgeResponse(stdout="x", stderr="", result=None)
    with patch.object(utility.bridge, "execute", new=AsyncMock(return_value=fake)):
        await execute_python(code="print('a')")
        await execute_python(code="print('b')")
    files = sorted(tmp_path.glob("*.jsonl"))
    assert len(files) == 2
    gid_a = _read_jsonl_records(files[0])[0]["graph_id"]
    gid_b = _read_jsonl_records(files[1])[0]["graph_id"]
    assert gid_a != gid_b
