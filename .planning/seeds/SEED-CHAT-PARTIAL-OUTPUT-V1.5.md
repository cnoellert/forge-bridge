# SEED: Chat partial-output on cap-fire (v1.5)

**Source:** Phase 16 (FB-D) D-03 / D-14a — both cap types collapse to HTTP 504
**Status:** planted 2026-04-27

## Trigger

When a v1.5 consumer needs partial-message output on cap-fire (vs. blanket 504) — e.g., an
artist sees a half-finished tool call and wants to refine the prompt without losing the
context the LLM had built up.

## v1.4 baseline

D-03 + D-14a: every cap-fire (max_iterations OR max_seconds) translates to HTTP 504 with the
prescribed banner copy "Response timed out — try a simpler question or fewer tools." The
client gets ZERO partial state — just an error envelope. The handler does not have access
to the in-flight messages list because `LLMLoopBudgetExceeded` is raised AFTER the loop
discards the state.

## v1.5+ migration shape

Two-step: first extend FB-C, then extend FB-D.

**Step 1 — FB-C surface change.** Add a `return_history: bool = False` kwarg to
`LLMRouter.complete_with_tools()`. When `True`, on cap-fire (either type), the method
returns a tuple `(partial_messages_list, raised_exception)` instead of raising. Default
behavior (raise on cap) is preserved.

```python
async def complete_with_tools(
    self,
    *args, **kwargs,
    return_history: bool = False,
) -> str | tuple[list[dict], LLMLoopBudgetExceeded]:
    ...
```

**Step 2 — FB-D handler change.** When the handler catches `LLMLoopBudgetExceeded`, it now
has access to the partial state and can surface it:

```json
HTTP 200    // Or HTTP 207 Multi-Status — TBD
{
  "messages": [...partial history including last assistant turn...],
  "stop_reason": "max_iterations",        // OR "max_seconds"
  "request_id": "<uuid>",
  "_partial": true
}
```

Or, preserve the 504 with an extended body:

```json
HTTP 504
{
  "error": {"code": "request_timeout", "message": "..."},
  "partial": {
    "messages": [...],
    "stop_reason": "max_iterations"
  },
  "request_id": "<uuid>"
}
```

Either response shape is valid; the choice depends on whether v1.5 wants the cap-fire to
look like a success-with-warning or a failure-with-data.

## Cross-references

- 16-CONTEXT.md D-03 (response-shape stop_reason posture)
- 16-CONTEXT.md D-14a (timeout/exception code-path translation matrix)
- LLMTOOL-03 (FB-C cap contract — currently terminal, not partial)

## Open questions

1. HTTP status — 200 (success-with-flag), 207 Multi-Status, or 504-with-partial? Each has
   a different implication for monitoring/alerting tools that watch HTTP status codes.
2. Should the partial messages be sanitized again before return? Tool results inside are
   already sanitized by FB-C (LLMTOOL-06); the assistant turn is fresh from the LLM. No
   re-sanitization should be needed.
3. Streaming interaction — does this SEED change if SEED-CHAT-STREAMING-V1.4.x lands first?
   Streaming naturally exposes partial state per-event, so this SEED becomes redundant
   in the streaming path. But the non-streaming caller (Flame hooks) still needs it.
