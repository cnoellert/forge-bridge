---
name: SEED-CMA-MEMORY-V1.5+
description: Integrate Claude Managed Agents memory feature for persistent forge-bridge agent context across sessions
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: A v1.5 or later milestone introduces "persistent agent memory" or "session continuity across requests" as an explicit goal — OR Anthropic graduates Claude Managed Agents memory out of beta into GA
---

# SEED-CMA-MEMORY-V1.5+: Claude Managed Agents memory integration

## Idea

Anthropic's Claude Managed Agents (CMA) memory feature — public beta in anthropic SDK v0.97.0 — lets agents persist context across sessions without forge-bridge having to manage it locally. FB-C v1.4 is stateless per-request (each `complete_with_tools` call starts fresh), but a future "what did we talk about last week?" workflow benefits from CMA memory. Orthogonal to FB-C v1.4 — track for when forge-bridge wants persistent agent memory.

## Why This Matters

- **Persistent context without local storage** — forge-bridge avoids building its own session-history database; Anthropic manages persistence on their side.
- **Multi-session artist workflows** — "continue what we started yesterday on shot PROJ_0010" requires either local persistence (which forge-bridge defers) or CMA memory (which Anthropic provides).
- **Combines well with SEED-MESSAGE-PRUNING-V1.5** — CMA memory could absorb the pruned context into managed memory rather than discarding it; the two seeds are coordinated v1.5 work.
- **Ollama parity is open** — local-side persistent memory for sensitive sessions has no direct equivalent; would require forge-bridge to ship its own session-store. Decision deferred until the cloud-side experiment proves the UX is worth the investment.

## When to Surface

- v1.5 or later milestone opens with a "persistent agent context" or "multi-session continuity" goal
- Anthropic announces CMA memory GA (out of beta)
- Artist UAT cites "I have to re-explain context every chat session" as a UX pain point
- The chat endpoint (Phase 16 / FB-D) gains a "history" view — CMA memory is the natural backing store

## How to Apply

1. Audit Anthropic SDK v0.97+ CMA memory API surface (still under `client.beta.*` namespace as of FB-C planning — verify GA status before adopting).
2. Decide on the SCOPE: per-user sessions (requires v1.5 auth — see SEED-AUTH-V1.5), per-project sessions, or per-conversation-id (caller-supplied).
3. Add a `session_id: str | None = None` kwarg to `complete_with_tools` that, when set on the cloud path, threads through to CMA memory APIs.
4. Local (Ollama) path remains stateless v1.5 unless we ship a local session-store (likely a new SEED at that point — `SEED-LOCAL-SESSION-STORE-V1.5+`).
5. Integration test against the live Anthropic API verifying that two consecutive `complete_with_tools` calls with the same `session_id` produce coherent context (e.g., "what did we just discuss?" returns a reference to the prior turn).
6. Update CHAT-04 UAT to include a multi-session scenario.

## Cross-References

- FB-C CONTEXT.md `<deferred>` "Claude Managed Agents memory feature integration" — explicit defer with this seed as carry-forward target.
- FB-C research §1 paragraph "CMA Memory" — flagged as orthogonal-to-FB-C.
- FB-C research §2.7 — "Track as `SEED-CMA-MEMORY-V1.5+` in case forge-bridge wants persistent agent memory later."
- REQUIREMENTS.md Future Requirements row "Claude Managed Agents memory feature integration".
- SEED-AUTH-V1.5.md — companion seed; per-user CMA scoping requires caller identity.
- SEED-MESSAGE-PRUNING-V1.5.md — companion seed; CMA memory and local pruning are alternative-or-coordinated approaches.
- forge_bridge/llm/_adapters.py — AnthropicToolAdapter would be the integration site.
