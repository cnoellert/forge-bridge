"""Phase 24.3 commit 4 — SSE history-grows streaming tests for chat_handler.

Coverage per .planning/milestones/v1.6-PHASE-24-3-FRAMING.md §5 commit-4 spec:

  1. Event-shape parseability             — emitted SSE frames parse per spec
  2. Terminal-event correctness           — done event carries final_text +
                                            stop_reason + request_id + tool_*
  3. History-grows / D-03 equivalence     — concatenated stream messages
                                            reconstruct the same final state
                                            as the JSON path's messages array
  4. Salvage-on-stream equivalence        — Bug-D salvage (already pre-callback
                                            at _adapters.py:733) round-trips
                                            into the assistant message event
  5. Rate-limit gate before stream        — D-13 rate limit returns JSON 429
                                            even with Accept: text/event-stream
                                            (gate fires pre-stream-start)
  6. Timeout becomes in-stream error      — LLMLoopBudgetExceeded after stream
                                            has started → in-stream `event:
                                            error` instead of HTTP 504

All tests use a mocked LLMRouter. The mock's complete_with_tools fires the
message_callback synchronously with shaped messages before returning the
ChatTurnResult — same pattern the real router exhibits per the Phase 24.3
streaming hooks added to forge_bridge/llm/router.py.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

from forge_bridge.console import _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.llm.router import ChatTurnResult, LLMLoopBudgetExceeded


# ---------------------------------------------------------------------------
# SSE parsing helper — tight per HTML5 SSE spec (event: <name>\ndata: <json>\n\n)
# ---------------------------------------------------------------------------


def _parse_sse_stream(text: str) -> list[tuple[str, dict]]:
    """Parse an SSE stream body into [(event_name, data_dict), ...].

    Strict per spec: each frame is `event: <name>\\ndata: <json>\\n\\n`.
    No support for multi-line data (forge-bridge's SSE schema is single-line
    JSON per frame by construction — see handlers._format_sse_event).
    """
    events: list[tuple[str, dict]] = []
    current_event: str | None = None
    current_data: str | None = None
    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:"):].strip()
        elif line == "":  # frame terminator
            if current_event is not None and current_data is not None:
                events.append((current_event, json.loads(current_data)))
            current_event = None
            current_data = None
    return events


# ---------------------------------------------------------------------------
# Shared fixtures — mirror tests/console/test_chat_handler.py pattern
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _make_test_tool():
    from mcp.types import Tool
    return Tool(
        name="forge_test_probe",
        description="Test probe tool for chat handler SSE tests.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def _passthrough_filter(tools):
    return tools


def _build_streaming_mock_router(
    *,
    final_text: str = "OK from mock LLM",
    stream_messages: list[dict] | None = None,
    raise_after_emit: BaseException | None = None,
):
    """Build a mock LLMRouter whose complete_with_tools fires the
    message_callback with the given stream_messages, then either raises
    `raise_after_emit` or returns a ChatTurnResult.

    The stream_messages model what the real router would emit via the
    Phase 24.3 _emit_stream_assistant / _emit_stream_tool hooks.
    """
    if stream_messages is None:
        stream_messages = []

    async def _mock_complete(
        *, messages, message_callback=None, **kwargs,
    ):
        if message_callback is not None:
            for m in stream_messages:
                await message_callback(m)
        if raise_after_emit is not None:
            raise raise_after_emit
        return ChatTurnResult(
            final_text=final_text,
            messages=list(messages) + [{"role": "assistant", "content": final_text}],
            tool_trace=[],
        )

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(side_effect=_mock_complete)
    return mock_router


@pytest.fixture
def make_client():
    """Factory fixture — caller provides the mock_router."""
    def _build(mock_router):
        ms = ManifestService()
        mock_log = MagicMock()
        mock_log.snapshot.return_value = ([], 0)
        api = ConsoleReadAPI(
            execution_log=mock_log,
            manifest_service=ms,
            llm_router=mock_router,
        )
        app = build_console_app(api)
        patches = (
            patch(
                "forge_bridge.mcp.server.mcp.list_tools",
                new=AsyncMock(return_value=[_make_test_tool()]),
            ),
            patch(
                "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
                side_effect=_passthrough_filter,
            ),
        )
        return TestClient(app), patches
    return _build


# ---------------------------------------------------------------------------
# 1. Event-shape parseability
# ---------------------------------------------------------------------------


def test_chat_sse_accept_returns_event_stream_content_type(make_client):
    """`Accept: text/event-stream` flips the response to SSE — verify the
    content-type, status, and that the body parses as ≥1 SSE frame."""
    mock_router = _build_streaming_mock_router(
        stream_messages=[{"role": "assistant", "content": "hello"}],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )
    assert r.status_code == 200, r.text
    assert "text/event-stream" in r.headers["content-type"]
    assert "X-Request-ID" in r.headers
    events = _parse_sse_stream(r.text)
    assert len(events) >= 1, f"expected at least one SSE frame; got body: {r.text!r}"


def test_chat_sse_no_accept_header_returns_json(make_client):
    """No Accept header → default JSON path. Regression guard for the content-
    negotiation branch in chat_handler."""
    mock_router = _build_streaming_mock_router()
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200, r.text
    assert "application/json" in r.headers["content-type"]
    body = r.json()
    assert body["stop_reason"] == "end_turn"
    assert "messages" in body


# ---------------------------------------------------------------------------
# 2 + 3. Terminal-event correctness + history-grows / D-03 equivalence
# ---------------------------------------------------------------------------


def test_chat_sse_terminal_done_event_carries_all_metadata(make_client):
    """The `event: done` frame must carry: final_text, stop_reason,
    request_id, tools_available, tools_filtered, tool_enforced, tool_forced,
    tool_trace — i.e. the same top-level keys the JSON path packs into its
    body. D-03 contract semantics preserved at the contents level."""
    mock_router = _build_streaming_mock_router(
        final_text="final answer",
        stream_messages=[{"role": "assistant", "content": "final answer"}],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )
    events = _parse_sse_stream(r.text)
    done = [e for e in events if e[0] == "done"]
    assert len(done) == 1, f"expected exactly one done event; got: {[e[0] for e in events]}"
    _, payload = done[0]
    for key in (
        "final_text", "stop_reason", "request_id",
        "tools_available", "tools_filtered", "tool_enforced",
        "tool_forced", "tool_trace",
    ):
        assert key in payload, f"done event missing key {key!r}; got: {sorted(payload.keys())}"
    assert payload["stop_reason"] == "end_turn"
    assert payload["final_text"] == "final answer"
    assert payload["tool_forced"] is False  # LLM-loop path; PR20 short-circuit would be True


def test_chat_sse_history_grows_reconstructs_final_messages(make_client):
    """The framing §6.5 history-grows invariant: client's input + accumulated
    SSE message events ≡ JSON response's `messages` field.

    Concretely: send 1 user message, mock router emits 1 assistant tool-call,
    1 tool result, 1 terminal assistant. Verify that:
      input [user] + 3 streamed messages = 4 total messages
    which matches the D-03 messages array a non-streaming caller would receive
    (user → assistant → tool → assistant)."""
    mock_router = _build_streaming_mock_router(
        final_text="here you go",
        stream_messages=[
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "0:probe",
                    "type": "function",
                    "function": {"name": "forge_test_probe", "arguments": "{}"},
                }],
            },
            {
                "role": "tool",
                "tool_call_id": "0:probe",
                "name": "forge_test_probe",
                "content": "probe result",
            },
            {"role": "assistant", "content": "here you go"},
        ],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "test the probe"}]},
            headers={"Accept": "text/event-stream"},
        )
    events = _parse_sse_stream(r.text)
    messages = [payload for kind, payload in events if kind == "message"]
    assert len(messages) == 3, f"expected 3 stream messages; got {len(messages)}: {messages}"
    # Reconstruct the equivalent of D-03's messages array:
    reconstructed = (
        [{"role": "user", "content": "test the probe"}] + messages
    )
    assert len(reconstructed) == 4
    assert reconstructed[0]["role"] == "user"
    assert reconstructed[1]["role"] == "assistant"
    assert reconstructed[1].get("tool_calls"), "assistant emit must carry tool_calls"
    assert reconstructed[2]["role"] == "tool"
    assert reconstructed[2]["tool_call_id"] == "0:probe"
    assert reconstructed[3]["role"] == "assistant"
    assert reconstructed[3]["content"] == "here you go"


# ---------------------------------------------------------------------------
# 4. Salvage-on-stream equivalence — Bug-D salvage runs BEFORE the callback
#    at _adapters.py:733; the salvaged tool_calls must round-trip into the
#    emitted assistant SSE event unchanged. Per framing §7 anti-scope, the
#    salvage logic body is UNTOUCHED — we test the round-trip, not the
#    salvage logic itself (that's tested in tests/llm/test_ollama_adapter.py).
# ---------------------------------------------------------------------------


def test_chat_sse_salvaged_tool_call_round_trips_into_assistant_event(make_client):
    """Phase 16.2 Bug D shape: model emits a tool call as JSON-shaped text;
    the adapter salvages it at _adapters.py:733 BEFORE the router's stream
    hook fires. The emitted assistant SSE event MUST carry the salvaged
    tool_calls field intact — domain-boundary discipline per framing §7
    Path A (salvage is protocol-layer, streaming is UX-layer; they must
    not bleed into each other)."""
    # Simulate what the real router emits via _emit_stream_assistant after
    # salvage has already populated response.tool_calls from text content.
    salvaged_assistant_msg = {
        "role": "assistant",
        "content": "",  # consumed by salvage per _adapters.py:748 (text="")
        "tool_calls": [{
            "id": "0:forge_tools_read",  # salvage POLISH-01 ref format
            "type": "function",
            "function": {
                "name": "forge_tools_read",
                "arguments": '{"name": "synthesis-tools"}',
            },
        }],
    }
    mock_router = _build_streaming_mock_router(
        stream_messages=[
            salvaged_assistant_msg,
            {"role": "tool", "tool_call_id": "0:forge_tools_read",
             "name": "forge_tools_read", "content": "ok"},
            {"role": "assistant", "content": "done"},
        ],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "list synthesis tools"}]},
            headers={"Accept": "text/event-stream"},
        )
    events = _parse_sse_stream(r.text)
    messages = [payload for kind, payload in events if kind == "message"]
    # The salvaged assistant message must appear in the stream verbatim —
    # the streaming layer does NOT touch the salvage output.
    salvaged_emitted = [
        m for m in messages
        if m.get("role") == "assistant" and m.get("tool_calls")
    ]
    assert len(salvaged_emitted) == 1, (
        f"expected exactly 1 salvaged assistant emit; got {len(salvaged_emitted)}: "
        f"{messages}"
    )
    tc = salvaged_emitted[0]["tool_calls"][0]
    assert tc["function"]["name"] == "forge_tools_read"
    assert json.loads(tc["function"]["arguments"]) == {"name": "synthesis-tools"}


# ---------------------------------------------------------------------------
# 5. Rate-limit gate fires PRE-stream — D-13 still returns JSON 429 even
#    with Accept: text/event-stream (gate is upstream of the SSE branch).
# ---------------------------------------------------------------------------


def test_chat_sse_rate_limit_gate_returns_json_429(make_client):
    """D-13 rate-limit gate runs BEFORE the LLM-loop content negotiation —
    SSE clients exceeding capacity get a JSON 429, not an in-stream error
    event. This is the intentional contract: pre-flight failures (validation,
    rate limit, missing tools, short-circuit paths) emit JSON regardless of
    the Accept header."""
    mock_router = _build_streaming_mock_router()
    client, patches = make_client(mock_router)
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    with patches[0], patches[1]:
        # First 10 SSE requests succeed (capacity=10 per D-13)
        for _ in range(10):
            r = client.post(
                "/api/v1/chat", json=payload,
                headers={"Accept": "text/event-stream"},
            )
            assert r.status_code == 200
        # 11th exceeds capacity — must be JSON 429 even with SSE Accept
        r = client.post(
            "/api/v1/chat", json=payload,
            headers={"Accept": "text/event-stream"},
        )
    assert r.status_code == 429
    assert "application/json" in r.headers["content-type"]
    body = r.json()
    assert body["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in r.headers


# ---------------------------------------------------------------------------
# 6. Timeout/budget after stream-start becomes in-stream error event
# ---------------------------------------------------------------------------


def test_chat_sse_loop_budget_exceeded_emits_in_stream_error(make_client):
    """When LLMLoopBudgetExceeded fires AFTER HTTP 200 has been committed
    (because the StreamingResponse has started), the failure becomes an
    in-stream `event: error` frame instead of a JSON HTTP 504. HTTP status
    is still 200 (response headers already sent); the failure semantics
    move into the data plane."""
    mock_router = _build_streaming_mock_router(
        stream_messages=[{"role": "assistant", "content": ""}],
        raise_after_emit=LLMLoopBudgetExceeded("max_seconds", -1, 120.0),
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )
    assert r.status_code == 200  # SSE committed before the budget exception
    events = _parse_sse_stream(r.text)
    error_events = [e for e in events if e[0] == "error"]
    assert len(error_events) == 1, (
        f"expected exactly one error event; got: {[e[0] for e in events]}"
    )
    _, payload = error_events[0]
    assert "error" in payload
    assert payload["error"]["code"] == "request_timeout"
    # No done event — error is terminal.
    assert not [e for e in events if e[0] == "done"]


def test_chat_sse_outer_timeout_emits_in_stream_error(make_client):
    """Same as loop_budget but via asyncio.TimeoutError from the outer
    wait_for. D-14 timeout interaction preserved under streaming."""
    mock_router = _build_streaming_mock_router(
        raise_after_emit=asyncio.TimeoutError(),
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )
    assert r.status_code == 200
    events = _parse_sse_stream(r.text)
    error_events = [e for e in events if e[0] == "error"]
    assert len(error_events) == 1
    assert error_events[0][1]["error"]["code"] == "request_timeout"


# ---------------------------------------------------------------------------
# Negative regression: salvage body anti-scope guard.
# ---------------------------------------------------------------------------


def test_chat_sse_event_format_is_strict_html5_sse(make_client):
    """Frame terminator is `\\n\\n` (W3C SSE spec). Each frame is
    `event: <name>\\ndata: <json>`. No interleaved content; no multi-line
    data; no comments. Per framing §7 — keep the wire format conservative
    so future consumers don't have to reverse-engineer it from a flexible
    parser."""
    mock_router = _build_streaming_mock_router(
        stream_messages=[{"role": "assistant", "content": "hello"}],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )
    body = r.text
    # Every frame ends with \n\n
    frames = [f for f in body.split("\n\n") if f.strip()]
    for frame in frames:
        lines = frame.split("\n")
        assert any(L.startswith("event:") for L in lines), (
            f"frame missing `event:` line: {frame!r}"
        )
        assert any(L.startswith("data:") for L in lines), (
            f"frame missing `data:` line: {frame!r}"
        )
        # data line is single-line JSON (forge-bridge schema contract).
        data_line = next(L for L in lines if L.startswith("data:"))
        json.loads(data_line[len("data:"):].strip())  # raises if malformed


# ---------------------------------------------------------------------------
# Phase 24.4 — SSE orchestration-terminated event taxonomy
# (.planning/milestones/v1.6-PHASE-24-4-FRAMING.md §5 + §9 Seam B)
# ---------------------------------------------------------------------------


from forge_bridge.llm.router import OrchestrationTerminationEnvelope


def _build_terminating_mock_router(
    *,
    stream_messages: list[dict],
    tool_name: str = "forge_x",
    result_text: str = "canonical_answer",
    k: int = 2,
):
    """Mock router that fires stream_messages, then returns a
    ChatTurnResult shaped like the K-fold canonical trigger fired —
    final_text="" + populated OrchestrationTerminationEnvelope."""
    accumulated = [
        {
            "tool_name": tool_name,
            "args_hash": "deadbeef",
            "result_hash": "abc12345",
            "content": result_text,
            "iter": i,
        }
        for i in range(1, k + 1)
    ]

    async def _mock_complete(*, messages, message_callback=None, **kwargs):
        if message_callback is not None:
            for m in stream_messages:
                await message_callback(m)
        return ChatTurnResult(
            final_text="",
            messages=list(messages) + stream_messages,
            tool_trace=[
                {"tool_name": tool_name, "arguments": {}, "result": result_text,
                 "error": None, "index": i}
                for i in range(k)
            ],
            termination=OrchestrationTerminationEnvelope(
                status="orchestration_terminated",
                trigger="k_fold_canonical",
                reason=(
                    f"Tool {tool_name} dispatched successfully {k} times with "
                    "identical canonical arguments and identical canonical "
                    "result. Loop terminated by orchestration policy."
                ),
                iterations=k,
                accumulated_results=accumulated,
            ),
        )

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(side_effect=_mock_complete)
    return mock_router


def test_chat_sse_orchestration_terminated_emits_distinct_event(make_client):
    """Framing §10.1 + §9 Seam B: terminal event is named
    ``orchestration_terminated``, NOT ``done`` (model-decided success)
    and NOT ``error`` (transport failure). Consumers branch by event
    name; three terminal-event taxa now exist."""
    mock_router = _build_terminating_mock_router(
        stream_messages=[
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_0",
                    "type": "function",
                    "function": {"name": "forge_x", "arguments": "{}"},
                }],
            },
            {"role": "tool", "tool_call_id": "call_0", "name": "forge_x",
             "content": "canonical_answer"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "forge_x", "arguments": "{}"},
                }],
            },
            {"role": "tool", "tool_call_id": "call_1", "name": "forge_x",
             "content": "canonical_answer"},
        ],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "show canonical"}]},
            headers={"Accept": "text/event-stream"},
        )
    events = _parse_sse_stream(r.text)
    event_kinds = [k for k, _ in events]
    # No `done` event — policy outcome is distinct from model-decided success
    assert "done" not in event_kinds, f"unexpected `done` event: {event_kinds}"
    # No `error` event — orchestration succeeded at its scope (policy)
    assert "error" not in event_kinds, f"unexpected `error` event: {event_kinds}"
    # Exactly one orchestration_terminated event
    terminated = [e for e in events if e[0] == "orchestration_terminated"]
    assert len(terminated) == 1, (
        f"expected exactly one orchestration_terminated event; got: {event_kinds}"
    )


def test_chat_sse_orchestration_terminated_event_carries_envelope(make_client):
    """Framing §3.1.3 + §5: terminal event payload carries the verbatim
    envelope inside ``data["termination"]`` plus transport metadata
    parity with model-decided ``done`` event."""
    mock_router = _build_terminating_mock_router(
        stream_messages=[{"role": "tool", "tool_call_id": "c0",
                          "name": "forge_x", "content": "canonical_answer"}],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "show"}]},
            headers={"Accept": "text/event-stream"},
        )
    events = _parse_sse_stream(r.text)
    terminated = [p for k, p in events if k == "orchestration_terminated"]
    assert len(terminated) == 1
    payload = terminated[0]

    # Envelope verbatim under data.termination
    assert "termination" in payload
    env = payload["termination"]
    assert env["status"] == "orchestration_terminated"
    assert env["trigger"] == "k_fold_canonical"
    assert env["iterations"] == 2
    assert "forge_x" in env["reason"]
    assert len(env["accumulated_results"]) == 2

    # Transport metadata parity with done event
    for key in (
        "stop_reason", "request_id", "tools_available",
        "tools_filtered", "tool_enforced", "tool_forced", "tool_trace",
    ):
        assert key in payload, f"missing transport key {key!r}"
    assert payload["stop_reason"] == "orchestration_terminated"
    assert payload["tool_forced"] is False

    # final_text OMITTED — orchestrator did not synthesize prose
    assert "final_text" not in payload


def test_chat_sse_orchestration_terminated_emits_messages_before_terminal(make_client):
    """Framing §5 + §8.3: deferred-raise sequencing — the K-th tool
    result reaches the consumer via ``event: message`` BEFORE the
    terminal ``event: orchestration_terminated``. SSE truthfulness
    preserved (operator observes the canonical answer that triggered
    termination, not just the policy decision)."""
    mock_router = _build_terminating_mock_router(
        stream_messages=[
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "c0", "type": "function",
                             "function": {"name": "forge_x", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c0", "name": "forge_x",
             "content": "canonical_answer"},
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "c1", "type": "function",
                             "function": {"name": "forge_x", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "name": "forge_x",
             "content": "canonical_answer"},
        ],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "show"}]},
            headers={"Accept": "text/event-stream"},
        )
    events = _parse_sse_stream(r.text)
    # Sequence: 4 message events, then 1 orchestration_terminated
    kinds = [k for k, _ in events]
    assert kinds == [
        "message", "message", "message", "message",
        "orchestration_terminated",
    ], f"unexpected event sequence: {kinds}"
    # K-th tool result observed before terminal event
    msgs = [p for k, p in events if k == "message"]
    tool_results = [m for m in msgs if m.get("role") == "tool"]
    assert len(tool_results) == 2
    assert tool_results[-1]["content"] == "canonical_answer"


def test_chat_sse_model_decided_done_event_unaffected(make_client):
    """C-layer regression check (framing §7.4): model-decided
    ``event: done`` path BYTE-IDENTICAL to pre-24.4 behavior.
    The terminated path is OPT-IN via populated ChatTurnResult.termination;
    nothing in the model-decided path changes."""
    mock_router = _build_streaming_mock_router(
        final_text="model answered",
        stream_messages=[{"role": "assistant", "content": "model answered"}],
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1]:
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )
    events = _parse_sse_stream(r.text)
    kinds = [k for k, _ in events]
    assert "done" in kinds, f"missing model-decided done event: {kinds}"
    assert "orchestration_terminated" not in kinds, (
        f"unexpected orchestration_terminated in model-decided path: {kinds}"
    )
    done = next(p for k, p in events if k == "done")
    assert done["stop_reason"] == "end_turn"
    assert done["final_text"] == "model answered"
