---
name: SEED-CROSS-PROVIDER-FALLBACK-V1.5
description: Explicit cross-provider sensitive-fallback design — cloud-fail mid-loop → fall back to local for non-sensitive queries
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: An Anthropic outage report cites mid-loop session failures as a recurring operational concern, OR v1.5 introduces a high-availability requirement for the chat endpoint
---

# SEED-CROSS-PROVIDER-FALLBACK-V1.5: Cross-provider sensitive-fallback

## Idea

FB-C v1.4 sensitive routing is verbatim from `acomplete()`: `sensitive=True → Ollama, sensitive=False → Anthropic`. There is NO mid-loop fallback. If Anthropic returns a 5xx mid-loop, the SDK retries internally then surfaces `LLMToolError` and the session aborts. v1.5 may want a fallback path: when Anthropic is unavailable, fall back to Ollama for non-sensitive queries that the operator deems safe to redirect.

The reason this is NOT v1.4: loop state is provider-specific (Anthropic message dicts ≠ Ollama message dicts per research §5.4). A mid-loop fallback would require state reconstruction in the other format — non-trivial design that warrants its own dedicated phase, not a hidden fix.

## Why This Matters

- **Anthropic outages happen** — research §6.7 documents the existing exposure: "Anthropic API outage during a loop" is a MEDIUM-severity operational concern.
- **The chat endpoint (Phase 16 / FB-D) is consumer-facing** — degraded availability is more visible than internal forge-bridge tools.
- **Local fallback is technically possible** — Ollama is always available on assist-01. The hard part is state translation (research §5.4): the conversation history Anthropic accumulated is a list of MessageParam dicts; Ollama expects a list of `{role, content, tool_calls?}` dicts. Tool result IDs (Anthropic `toolu_*`) become composite refs (`{idx}:{name}` for Ollama).
- **NOT all sessions can fail back** — `sensitive=True` sessions MUST stay local (operator policy); only `sensitive=False` cloud failures are candidates for fallback.

## When to Surface

- An Anthropic outage report cites lost mid-loop sessions in production
- A v1.5 phase introduces a high-availability or chat-endpoint-SLA requirement
- A new chat-endpoint consumer (e.g., projekt-forge service-account batch jobs) requires graceful degradation
- A v1.5+ phase ships a state-translation surface for any other reason — that surface can be reused

## How to Apply

1. Design the state-translation contract:
   - `_translate_state_anthropic_to_ollama(state: dict) -> dict` and the inverse
   - Document tool_call_ref translation (toolu_* → composite, and back)
   - Decide what to do with assistant `text` blocks that have no Ollama analog (likely: concatenate into the assistant message content)
2. Add a `fallback_to_local: bool = False` kwarg to `complete_with_tools`. When set AND `sensitive=False` AND a cloud `LLMToolError` fires after SDK retries, log the fallback at WARNING and reconstruct state for OllamaToolAdapter, then continue the loop.
3. Add operator-visible telemetry: a session that fell back gets a `fallback=true` field in the D-25 terminal log line so operators can audit.
4. Add tests: TestCrossProviderFallback covering (a) cloud success → no fallback, (b) cloud LLMToolError + fallback_to_local=True → state reconstructed and loop continues, (c) cloud LLMToolError + fallback_to_local=False (default) → re-raise (matches v1.4 behavior).
5. Update CHAT-04 UAT to include a fallback drill (e.g., set `ANTHROPIC_API_KEY=invalid` mid-conversation and verify the chat panel keeps responding).

## Cross-References

- FB-C CONTEXT.md `<deferred>` "Cross-provider sensitive fallback (cloud-fail → local)" — explicit defer with this seed as carry-forward.
- FB-C research §5.4 — verbatim "Document as `SEED-CROSS-PROVIDER-FALLBACK-V1.5` and reject for FB-C."
- FB-C research §6.7 — Anthropic API outage threat model.
- REQUIREMENTS.md Out of Scope row "Cross-provider sensitive fallback".
- forge_bridge/llm/_adapters.py — both adapters' state shapes are the inputs to the translation functions.
- forge_bridge/llm/router.py — `complete_with_tools` is the integration site for the new kwarg + fallback logic.
