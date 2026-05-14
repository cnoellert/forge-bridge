---
name: SEED-DEFAULT-MODEL-PERFORMANCE-V1.6+
description: Phase 23.1 author-walk on portofino measured the default local model (qwen2.5-coder:32b) at ~71s per turn at 15K-token prompt context — too slow to complete a 2-iteration agentic Flame introspection query within the FB-C 120s inner cap. With the post-23.1-flatten chat path operationally correct end-to-end, the residual failure is purely model-performance. v1.6 must choose between (a) defaulting to a faster local model, (b) deferring more compute to cloud, (c) shrinking the per-turn prompt context, or (d) some combination.
type: forward-looking-decision
planted_during: Phase 23.1 author-walk on portofino 2026-05-14 — Gate 3 partition surfaced the model-speed bottleneck explicitly. flame_execute_python wrapper executed in 12ms (status=ok); router iter=1 took 71 seconds (LLM inference time on the 15K-token prompt). Session hit max_seconds at 120s after one full iter + partial follow-up generation.
trigger_when: v1.6 milestone opens OR the prompt-context-per-turn changes (chat REPL ships and shrinks history per SEED-MESSAGE-PRUNING-V1.5; or tools_offered_count drops materially via the flat-signature audit) OR a faster local-model option benchmarks acceptable on the canonical regression query (`SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+`) OR `SEED-DEFAULT-MODEL-BUMP-V1.4.x` activates with empirical evidence
---

# SEED-DEFAULT-MODEL-PERFORMANCE-V1.6+

## The Empirical Measurement

The 23.1 post-flatten author-walk on portofino with cloud-warm conditions:

```
[12:07:57] flame_execute_python utility.py:195
           code_hash=ffb774eeafdc0e4a main_thread=False elapsed_ms=12 status=ok code_len=581
[12:07:57] tool-call iter=1 router.py:699
           tool=flame_execute_python args_hash=6e396576
           prompt_tokens=15372 completion_tokens=194
           elapsed_ms=71002 status=continuing
[12:08:46] tool-call session complete iter=1
           elapsed_s=120.0 reason=max_seconds
```

**Tool wrapper executed in 12ms.** Pipeline correctness confirmed. The residual 120-second budget exhaustion is **70,990ms of LLM inference + ~49,000ms of post-tool-result generation** = the model itself, not the chat path.

## Why This Is a v1.6 Decision, Not a 23.1 Bug

23.1's forcing function was "the chat surface that v1.5 made *legible* turns out to be *operationally broken*." Pre-23.1, the chat surface was broken in three ways:

1. Misleading error message at retry exhaustion → fixed by `call_wrapper.py` rewrite.
2. No escape-hatch tool for the LLM → fixed by `flame_execute_python` registration + canonical-introspection repositioning.
3. Tool dispatch silently failed on args-shape mismatch → fixed by signature flatten.

All three landed and were verified. The remaining failure (slow LLM completion on a 32b local model with 15K-token context) is **not chat-surface correctness** — it's **default-model selection / sizing / context-budget** policy. That belongs in a milestone phase, not an in-flight ship-blocker patch.

## The Decision Surface (v1.6)

Four candidate directions, ranked by my read of cost/benefit (writer's-room can challenge):

### (a) Default to a faster local model

The `_DEFAULT_LOCAL_MODEL` constant in `forge_bridge/llm/router.py` (or equivalent) currently points at `qwen2.5-coder:32b`. Candidates:
- `qwen2.5-coder:14b` — 2-3x faster inference; less capable on tool selection. Compose with the 23.1 docstring repositioning to see if the smaller model still picks `flame_execute_python` cleanly.
- `qwen2.5:14b` (non-coder) — possibly better at general reasoning, slightly worse at Python authoring.
- A purpose-built distilled model for agentic tool-use — does not exist in the qwen2.5 lineage off-the-shelf.

**Risk:** smaller models historically struggled with the canonical-introspection-via-Python pattern. Need to benchmark against `SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+` before defaulting.

**Cost:** trivial code change + a benchmarking phase. Composes cleanly with `SEED-DEFAULT-MODEL-BUMP-V1.4.x` which already exists for this purpose.

### (b) Defer more compute to cloud

Make the chat handler smarter about routing: simple queries → local; complex agentic queries → cloud Anthropic. Requires `sensitive=False` codepath to work (currently broken per `SEED-CLOUD-CHAT-AGENTIC-ROUTER-V1.6+` — fix that first), plus a routing heuristic.

**Risk:** cloud cost increase; latency-vs-cost tradeoff needs framing; data-sensitivity questions (`SEED-AUTH-V1.5`).

**Cost:** medium. Requires fixing the cloud agentic-loop bug + implementing routing logic + framing the sensitive-routing question that's been deferred since v1.4.

### (c) Shrink per-turn prompt context

The 23.1 walk showed `prompt_tokens=15372` per iter. That's:
- System prompt (~1-2K)
- ~58 tool descriptions (~10-12K — the load-bearing weight)
- Message history (~1-2K so far; grows)

Shrinking tool descriptions via:
- More aggressive PR14 message-based filtering (currently passes ~58 tools through; could narrow to 10-15 with better keyword matching).
- Per-domain tool grouping ("when query is about timeline, show only timeline tools").
- Late-binding tool injection (start with a small core, escalate to wider set on retry).

**Risk:** PR14 changes are the kind of change the cross-writer warned against — "compensating for bad affordance with hidden cognitive layers becomes brittle fast." Need to be careful.

**Cost:** small-to-medium depending on approach; high archaeology risk if done wrong.

### (d) Streaming response per `SEED-CHAT-STREAMING-V1.4.x`

Doesn't change inference speed but changes operator experience. Combined with the deferred heartbeat (per `SEED-COLD-LOAD-UX-V1.6+`), shifts the failure mode from "120s of silence, then timeout" to "the model is generating tool calls live, here's where it is, you can interrupt." Doesn't fix the underlying speed problem but makes it bearable.

**Cost:** medium. Requires server-side streaming response + client-side streaming consumer + interruption protocol.

## What I'd Recommend (Strong Reco)

**Two-track v1.6 strategy:**

1. **Track A — Default-model bump (a):** swap `qwen2.5-coder:32b` for `qwen2.5-coder:14b` as the default local model. Benchmark on the canonical regression query. If it converges cleanly within 60s, ship. This is the cheapest highest-leverage move.

2. **Track B — Streaming + heartbeat (d):** decouple the UX problem from the inference-speed problem. Even if the 14b model also struggles on edge-case queries, streaming + heartbeat makes the failure mode tolerable instead of opaque.

Defer (b) until the cloud agentic-loop bug is fixed (separate seed) and the sensitive-routing question has a real answer. Defer (c) until tracks A + B prove insufficient — the filter-complexity escalation is exactly what the cross-writer cautioned against and shouldn't be the first move.

## Activation Triggers

Any of:

1. **v1.6 milestone opens** — natural sequencing; this is the load-bearing v1.6 model-policy question.
2. **`SEED-DEFAULT-MODEL-BUMP-V1.4.x` is being re-evaluated** — already exists as the formal carry-forward for default-local-model changes; this seed adds the empirical performance evidence.
3. **Prompt-context-per-turn changes materially** — REPL ships and shrinks history; or `SEED-FLAT-SIGNATURE-AUDIT-V1.6+` flattens 30 more tools and drops the tool-description token count.
4. **A faster local model benchmarks acceptable** on `SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+`. That seed's promotion to a fixtures module makes the benchmarking trivially repeatable.

## Cross-References

- 23.1 walk evidence: [forge_bridge/tools/utility.py](forge_bridge/tools/utility.py) `code_hash=ffb774eeafdc0e4a status=ok elapsed_ms=12` (tool wrapper) vs router `elapsed_ms=71002` (LLM inference).
- 23.1 close commit + STATE.md cursor — defers this to v1.6+.
- Sibling seeds: `SEED-DEFAULT-MODEL-BUMP-V1.4.x` (formal carry-forward this seed adds empirical weight to), `SEED-OPUS-4-7-TEMPERATURE-V1.5` (cloud-model fix that has to land before opus-4-7 default), `SEED-CHAT-STREAMING-V1.4.x` (the UX-decoupling work), `SEED-MESSAGE-PRUNING-V1.5` (the prompt-shrinking work), `SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+` (the benchmark fixture this decision tests against), `SEED-FLAT-SIGNATURE-AUDIT-V1.6+` (the prompt-shrinking work that lands "for free").

## The One-Line Lesson

> Once the chat path is structurally correct, the residual failure shape is operational not architectural. Model selection is operational. Frame it that way and the decision matrix becomes legible.
