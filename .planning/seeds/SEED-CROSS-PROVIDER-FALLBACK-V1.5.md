---
name: SEED-CROSS-PROVIDER-FALLBACK-V1.5
description: Graceful degradation of intelligence availability — when the configured LLM is unreachable, fall back to an alternate provider while preserving response-envelope determinism (NEVER behavioral equivalence).
type: forward-looking-idea + framing-artifact
planted_during: v1.4 FB-C planning (2026-04-26); refreshed with A.6 framing (2026-05-06)
trigger_when: An Anthropic / Ollama outage report cites mid-loop session failures as a recurring operational concern, OR v1.5 introduces a high-availability requirement for the chat endpoint, OR a future B.1 / resilience phase tackles intelligence availability as infrastructure
---

# SEED-CROSS-PROVIDER-FALLBACK: Cross-provider graceful degradation

## Architectural constraint (binding — read this before anything else)

**Cross-provider fallback preserves response-envelope determinism. It does NOT preserve behavioral determinism.**

Concretely:

- A chat session that falls back from Anthropic to Ollama (or Ollama to Anthropic) MUST produce a response with the **same shape** as a non-fallback session — the PR31 envelope, `messages[]` round-trip, `tool_trace[]` semantics, `stop_reason` values, error envelope on failure. A consumer reading the response cannot tell from envelope shape alone whether a fallback occurred.
- A chat session that falls back from Anthropic to Ollama (or vice versa) **WILL NOT** produce the same answer, the same tool selection, the same iteration count, or the same final summary text. Behavioral equivalence between providers is **not a goal** of this work and is not promised by the contract.

The contract surface to operators is: *"if the primary provider is unavailable, the chat endpoint will keep working with reduced behavioral fidelity, and the response shape will tell consumers exactly what happened."* The contract surface is **not**: *"if the primary provider is unavailable, the chat endpoint will produce equivalent results."*

### Why this distinction is load-bearing

Behavioral equivalence between Anthropic and Ollama is not technically possible without a translation harness that normalizes tool-selection behavior, summary style, refusal patterns, and (most importantly) the model's internal "voice." That harness would itself be a multi-phase effort, would never fully succeed, and would absorb scope at every step. Trying to deliver it inside a graceful-degradation phase is a scope-explosion trap.

Deterministic envelopes are a small, precise contract. Behavioral equivalence is an unbounded research program. The seed promises only the former.

### Elevate condition (mandatory)

**If, during implementation, the work begins drifting toward behavioral equivalence — message-style normalization, tool-selection alignment, "make Ollama feel like Anthropic" — STOP and re-scope.**

That is not a "maybe later" deferral; that is a hard boundary. The phase that lands cross-provider fallback either ships envelope-determinism only and closes, or it pauses and surfaces the scope drift to the project owner before continuing. Behavioral-equivalence work, if it ever happens, is a separate project with its own phase, its own research, and its own seed.

---

## Motivation (graceful degradation of intelligence availability)

Phase A.6 (2026-05-06) surfaced a concrete instance of the underlying problem: the daemon was configured to route LLM calls to a cross-host Ollama at `192.168.86.15:11434` (the operator's GPU host). When that host became unreachable, the chat path waited the OS-level TCP connect default (~75 s), produced a generic `LLMToolError`, and from the operator's seat looked indistinguishable from a broken daemon. The system has no way to gracefully redirect the work to an alternate provider.

That outage is the project's first lived instance of treating **intelligence availability as infrastructure**. Just as a database or message bus needs reachability surfaces, fast-fail timeouts, and graceful-degradation paths, an LLM endpoint does too. Cross-provider fallback is the load-bearing piece of that posture: when Anthropic 5xx's mid-loop, or Ollama becomes unreachable, the chat endpoint stays useful for the queries that *can* still be answered.

Specifically:
- `sensitive=True` sessions MUST stay local (operator policy on data residency); a cloud fallback for those is **not** part of this seed.
- `sensitive=False` sessions that the operator has flagged safe to redirect MAY fall back to local when Anthropic is unavailable.
- The reverse (Ollama unavailable → fall back to Anthropic for non-sensitive work) is symmetric and equally in scope.

Per Phase A.6's discipline note: this should be paired with a fast-fail connect-timeout (`SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+`) so the unavailability detection itself happens in seconds, not 75. The two seeds are designed to compose.

---

## Why this was not v1.4

FB-C v1.4 sensitive routing is verbatim from `acomplete()`: `sensitive=True → Ollama, sensitive=False → Anthropic`. There is no mid-loop fallback. If Anthropic returns a 5xx mid-loop, the SDK retries internally then surfaces `LLMToolError` and the session aborts.

Loop state is provider-specific (Anthropic message dicts ≠ Ollama message dicts per FB-C research §5.4). A mid-loop fallback requires state reconstruction in the alternate format — non-trivial design that warrants its own dedicated phase, not a hidden fix.

---

## When to surface

- An Anthropic outage report cites lost mid-loop sessions in production
- An Ollama unreachability report (cross-host or local) recurs as an operational concern
- A v1.5 phase introduces a high-availability or chat-endpoint-SLA requirement
- A new chat-endpoint consumer (e.g., projekt-forge service-account batch jobs) requires graceful degradation
- A v1.5+ phase ships a state-translation surface for any other reason — that surface can be reused
- A B.1 / resilience phase explicitly takes "intelligence availability as infrastructure" as its scope

---

## How to apply (when triggered)

1. **State-translation contract** — design the minimum translation surface:
   - `_translate_state_anthropic_to_ollama(state: dict) -> dict` and the inverse
   - tool_call_ref translation (`toolu_*` → composite `{idx}:{name}` for Ollama, and back)
   - Decide what to do with assistant `text` blocks that have no Ollama analog (likely: concatenate into the assistant message content)
   - **Do NOT** attempt to normalize message style, refusal patterns, tool-selection bias, or any other behavioral surface beyond what the envelope contract requires. That is the elevate-condition boundary.

2. **Fallback kwarg** — add `fallback_to_local: bool = False` (or `fallback_to_cloud: bool = False`, depending on direction) to `complete_with_tools`. When the kwarg is set AND the originating call is non-sensitive AND the primary provider raises a fallback-eligible error after SDK retries, log the fallback at WARNING and reconstruct state for the alternate adapter, then continue the loop.

3. **Operator-visible telemetry** — a session that fell back gets a `fallback=true` field in the D-25 terminal log line, plus the originating provider name and the destination provider name, so operators can audit. The chat response envelope SHOULD also carry a `fallback_provider=<name>` indicator on `meta` so consumers can reason about behavioral drift if they care to.

4. **Tests** — TestCrossProviderFallback covering:
   - cloud success → no fallback
   - cloud LLMToolError + `fallback_to_local=True` → state reconstructed, loop continues, **envelope shape identical** to non-fallback
   - cloud LLMToolError + `fallback_to_local=False` (default) → re-raise (matches v1.4 behavior)
   - sensitive=True session + cloud fallback flag → no fallback (policy boundary)
   - the reverse direction (local LLMToolError + `fallback_to_cloud=True`) — same matrix

5. **CHAT-04 UAT extension** — fallback drill: set `ANTHROPIC_API_KEY=invalid` mid-conversation and verify the chat panel keeps responding; verify the response carries `fallback_provider`; verify behavioral drift is visible to the operator (different summary style, different tool selection — that is **expected**, not a regression).

---

## What success looks like

A chat session whose primary provider is unavailable produces a response with the same envelope shape as a non-fallback session, carries an explicit `fallback_provider` field, and answers the user's question with reduced fidelity. The operator can tell from the response that a fallback happened. The consumer code does not need to special-case the response shape. The operator's day-to-day is uninterrupted.

A chat session whose primary provider is available behaves exactly as it does today.

That is the entire envelope-deterministic contract. Anything beyond that is the elevate boundary.

---

## Cross-references

- `docs/learnings/2026-05-06-phase-transition.md` — project-level framing of intelligence availability as infrastructure (the layer Layer 2 / moat work this seed sits inside).
- `SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+.md` — composes with this seed: detects unavailability fast, then this seed gracefully degrades.
- `SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+.md` — broader audit of every external dependency the daemon touches; this seed is the LLM-specific instance.
- FB-C CONTEXT.md `<deferred>` "Cross-provider sensitive fallback (cloud-fail → local)" — explicit defer with this seed as carry-forward.
- FB-C research §5.4 — verbatim "Document as `SEED-CROSS-PROVIDER-FALLBACK-V1.5` and reject for FB-C."
- FB-C research §6.7 — Anthropic API outage threat model.
- REQUIREMENTS.md Out of Scope row "Cross-provider sensitive fallback".
- `forge_bridge/llm/_adapters.py` — both adapters' state shapes are the inputs to the translation functions.
- `forge_bridge/llm/router.py` — `complete_with_tools` is the integration site for the new kwarg + fallback logic.
