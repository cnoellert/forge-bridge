# SEED: Chat streaming (SSE / WebSocket) (v1.4.x)

**Source:** Phase 16 (FB-D) D-01 — non-streaming JSON for v1.4
**Status:** planted 2026-04-27

## Trigger

After v1.4 ships and CHAT-04 artist UAT validates the non-streaming UX baseline. If the
artist UAT debrief reports "spinner runs too long, no progress feedback" or similar, this
SEED activates as a v1.4.x patch (NOT a v1.5 milestone item — UX upgrades within a milestone
patch are the right cadence).

## v1.4 baseline

`POST /api/v1/chat` is non-streaming. The handler returns a single JSON response after
`complete_with_tools()` finishes the full loop (`{messages, stop_reason, request_id}`). The
Web UI panel shows a `.spinner-amber` for the duration. CHAT-02 (125s timeout) and CHAT-04
(<60s artist UAT) work fine non-streaming.

## v1.5+ migration shape

Add a streaming variant alongside the JSON variant:

```
POST /api/v1/chat                       # Existing — non-streaming JSON (unchanged)
POST /api/v1/chat?stream=true           # NEW — SSE response (text/event-stream)
```

Or, prefer a separate route to keep the contract clean:

```
POST /api/v1/chat                       # Non-streaming JSON
GET  /api/v1/chat/stream                # SSE — connect-then-post pattern
```

SSE event shapes:
- `event: message`        — assistant token chunks
- `event: tool_call`      — tool invocation announced
- `event: tool_result`    — tool result returned (post-sanitization)
- `event: terminal`       — stop_reason fired; close connection
- `event: error`          — equivalent to a 4xx/5xx in the JSON path

The JS client switches from `fetch()` to `EventSource` when streaming is enabled. The
chat panel toggles between the two paths via a feature flag (env var or CONSOLE-08 setting).

## Cross-references

- 16-CONTEXT.md D-01 (streaming posture)
- 16-RESEARCH.md §6.1 (loop semantics — informs which events are surfaceable)
- ROADMAP CHAT-04 (artist UAT criterion — non-streaming must pass first)

## Open questions

1. SSE vs WebSocket — SSE is simpler (one-way server→client) and matches the loop's natural
   shape. WebSocket would be needed only if the client wants to abort mid-loop. Defer.
2. Token-by-token vs chunk-by-chunk — Anthropic and Ollama have different streaming
   primitives. Likely: chunk-by-chunk with the server normalizing per-event boundaries.
3. Backpressure — if the client's EventSource is paused (tab backgrounded), does the server
   buffer? For v1.4.x: drop oldest with a single warning event.
