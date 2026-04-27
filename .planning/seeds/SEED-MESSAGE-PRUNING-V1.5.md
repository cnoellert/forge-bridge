---
name: SEED-MESSAGE-PRUNING-V1.5
description: True message-history pruning beyond the v1.4 8 KB ingest-time truncation
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: A long-session workload (artist multi-turn chat, projekt-forge agentic batch) hits the model's context window mid-loop AND v1.5 milestone is open OR a v1.4.x context-pressure incident is reported
---

# SEED-MESSAGE-PRUNING-V1.5: True message-history pruning

## Idea

FB-C v1.4 ships with ingest-time per-result truncation (8 KB) — adequate for typical sessions (8 iterations × ~5 KB results = 40 KB total, well within Opus 4.7's 200K context and qwen3:32b's 128K). For pathological sessions (long artist chats with verbose `manifest_read` results, or projekt-forge agentic batches with deep tool-call traces), the cumulative input prompt eventually approaches the model's context window. Real pruning summarizes old turns into a system note, drops early tool results, or both.

## Why This Matters

- **Truncation is reactive; pruning is proactive** — 8 KB per-result cap protects against single-message bloat but does nothing about the cumulative growth.
- **Context-window cliff is a hard fail** — Anthropic returns `400 prompt is too long`; Ollama silently truncates and returns garbage. Either way the loop breaks.
- **forge-bridge will hit this when projekt-forge synthesizes 100+ tools** — `manifest_read` returning sidecar metadata for all of them in a single tool result will exceed 8 KB even with truncation, and the truncated result still grows the message history turn-over-turn.

## When to Surface

- A workload report (artist UAT or projekt-forge integration) cites context-window exhaustion or "loop failed at iteration N with context-too-long" symptom
- v1.5 milestone opens with a "long-running agentic sessions" or "memory" goal
- A v1.4.x phase introduces a tool whose typical result size is >2 KB sustained (manifest_read, rich shot-lineage queries)
- The CMA Memory feature (SEED-CMA-MEMORY-V1.5+) lands and obsoletes the need for in-process pruning

## How to Apply

1. Decide on a pruning STRATEGY:
   - **Summarize-old-turns:** keep recent N turns verbatim, replace older turns with a single system message "earlier in this session: tool X was called Y times, returned summaries: ..."
   - **Drop-early-tool-results:** keep recent N tool_result blocks; for older turns, replace tool_result content with a placeholder like "(result from earlier turn — N bytes, hash=abcd1234)"
   - **Hybrid:** drop early tool results AND summarize the assistant's interleaved text into a single system note.
2. Implement the chosen strategy as `_prune_history(state, target_input_tokens, model_context_window)` in `forge_bridge/llm/router.py` (or a new `_pruning.py` if logic warrants a module).
3. Add a `target_input_tokens` kwarg to `complete_with_tools` (default = 50% of model context window) and trigger pruning when the running token count exceeds it.
4. Add tests: TestMessagePruning covering (a) prune fires at threshold, (b) prune preserves recent turns, (c) prune produces a parseable summary that the LLM can reference, (d) prune is no-op for short sessions.
5. Coordinate with the SEED-CMA-MEMORY-V1.5+ workstream to avoid duplicating effort.

## Cross-References

- FB-C CONTEXT.md `<deferred>` "True message-history pruning" — explicit deferral with this seed as carry-forward target.
- FB-C research §6.2 — token budget exhaustion threat model + mitigation strategy table; explicitly says "Pruning is OUT OF SCOPE for v1.4."
- REQUIREMENTS.md Out of Scope row "Message-history pruning".
- forge_bridge/llm/_sanitize.py — `_TOOL_RESULT_MAX_BYTES = 8192` (the v1.4 stopgap; pruning is the v1.5 successor).
