# Three-Domain Architectural Decomposition

**Date:** 2026-05-14 (post-Pass-1-instrumentation)
**Predecessor investigations:**
- `.planning/COLD-START-INVESTIGATION.md` (operator-authored; runtime-economics framing)
- `.planning/PROTOCOL-VS-SUBSTRATE-INVESTIGATION.md` (Phase 24.1 close + protocol-path investigation open)

## What this artifact closes

The two predecessor investigations were investigative — each surfaced a failure shape and isolated it. This artifact closes the investigative arc by integrating their findings into a coherent architectural decomposition. Where the predecessors framed individual symptoms, this artifact freezes the architectural conclusion: forge-bridge has **three distinct engineering domains** that must be held separately rather than collapsed under "LLM unreliability."

## What the investigations actually proved

**The cold-start investigation explained WHY the runtime felt slow.**
**The Pass-1 instrumentation explained WHY the runtime still failed even after the latency work succeeded.**

Those are separate layers. They were previously collapsed together under a single diagnostic frame ("the model/tool system is flaky"). They are now independently measurable.

## The three domains

### 1. Runtime economics layer

- prompt size
- KV-cache locality
- generation latency
- tool-prefix stability
- model unload / keep_alive

**Empirical anchor:** COLD-START-INVESTIGATION.md + Phase 24.1 commits `fbf4b56` (deterministic tool ordering) and `c480353` (reachability TTL 5s→60s). Validated 2026-05-14 portofino measurement: canonical-cold 17.10s → canonical-repeat 1.73s → canonical-return-after-non-Flame-interlude 1.06s.

**Status: substantially resolved.** Prefix stability holds across conversational timescales. Generation dominates warm-call cost. Re-opens only on new evidence.

### 2. Protocol serialization layer

- native `tool_calls` field absent in Ollama responses
- prose-embedded JSON emitted instead
- Bug-D salvage reconstructing operations from `message.content`

**Empirical anchor:** Pass 1 instrumentation at `forge_bridge/llm/_adapters.py:OllamaToolAdapter.send_turn` (commit `5aef0ec`). Canonical-warm measurement 2026-05-14 evening: 8/8 turns showed `raw_tool_calls=0` and `salvage_fired=true`. The model emitted JSON-shape calls embedded in conversational prose ("It seems there might be an issue...") rather than Ollama's structured field.

**Status: failure shape identified; architectural response pending.** qwen2.5-coder:32b never emits Ollama's native `tool_calls` under large MCP tool prefixes. Bug-D salvage is the operational protocol adapter for this provider/model combination. This was not designed as a primary path — it was a 16.2-era patch.

### 3. Dispatch substrate layer

- `flame_execute_python` invoked
- graph events emitted at `~/.forge-bridge/graphs/<graph_id>.jsonl`
- `transport_error` observable independently of protocol-layer state

**Empirical anchor:** Phase 24 graph-emission substrate (`8b17a3d` / `56ea87b` / `b66ceef` / `3c253bf`). Canonical-warm measurement 2026-05-14 evening: 5 graph files written; `status=transport_error` observable as a distinct signal from protocol-layer salvage state.

**Status: substrate operational.** Phase 24 Commit 2's instrumentation of `flame_execute_python` and the canonical regression fixture (Commit 3) provide the dispatch-layer observation surface independently of the protocol-layer state.

## Why this decomposition matters

Before the investigations, all three failure modes presented through a single diagnostic frame: "the chat surface is unreliable." Each had to be reasoned about indirectly because the layers were not independently observable. Optimization choices in any one layer risked interfering with the others — for example, cache-locality work could shift protocol-layer behavior without making the shift visible.

After the investigations, each layer has its own instrumentation, its own failure shape, and its own diagnostic signature. Architectural changes can target one layer without entangling with the others.

## The architectural inversion

**Before the measurements**, optimization heuristics included:

- schema slimming looked high-leverage
- PR14 narrowing looked structurally necessary
- prompt churn looked existential

**After the measurements**, the same heuristics invert:

- stable large prefixes are acceptable
- generation dominates warm calls
- narrowing instability can cost more than it saves
- operational determinism matters more than token minimization

This is a major architectural inversion. The investigations proved the system is not failing because the model is incapable. It is failing because:

- provider serialization contracts are weak under large tool envelopes
- and the runtime previously lacked enough observability to isolate that cleanly

Now it does.

## What changes in next-direction priority

### A. Treat salvage as a first-class normalization boundary

Not a fallback. Not a bug patch. A **normalization layer** between provider output and canonical operation dispatch. The Bug-D path is currently load-bearing for qwen2.5-coder structured invocation under 50+-tool prefixes; treating it as a transient compensation undersells its operational role.

### B. Preserve provider-agnostic operation semantics internally

The canonical internal object is:
- operation intent
- tool name
- arguments
- provenance

NOT:
- provider-native `tool_call` payloads

Provider-native formats become **ingestion formats only**. The internal dispatch substrate operates on the canonical object; the protocol normalization layer converts between them.

### C. Keep runtime economics orthogonal from protocol semantics

The KV-cache work and the salvage work solve different problems. Do not entangle them again operationally. A change in salvage strategy should not be evaluated against cache-locality metrics; a change in prefix stability should not be evaluated against salvage success rate.

### D. Shift immediate operator-facing optimization toward perceived-responsiveness wins

- Flame reachability fast-fail
- conversational tool-free path

Both now dominate perceived responsiveness more than any remaining cache or prompt-shape work. The 2026-05-14 evening measurement's `transport_error` chain and the artifact's COLD-START Recommendation #2 (route short conversational inputs to `acomplete()`) are both inside this directional shift.

## Anti-scope binding for the next phase

Carried forward from `.planning/PROTOCOL-VS-SUBSTRATE-INVESTIGATION.md` §"What this artifact opens" and **strengthened by this synthesis**:

**Do NOT:**
- More cache tuning — runtime-economics-layer is substantially resolved
- More instrumentation — Pass 1 is sufficient; additional observational layers risk contaminating the architectural baseline this artifact establishes
- More narrowing experiments — narrowing instability can cost more than it saves
- More prompt surgery — prompt churn is no longer existential

Those were correct investigative steps. They answered their questions. The next phase executes within the three-domain frame, not within "LLM unreliability."

## Predecessor artifact status

| Artifact | Pre-synthesis status | Post-synthesis status |
|---|---|---|
| `COLD-START-INVESTIGATION.md` | Operator-authored; foundational measurement (2026-05-14 mid-day) | **Closed.** Runtime-economics layer surfaced and named. Resolution lives in Phase 24.1 commits. |
| `PROTOCOL-VS-SUBSTRATE-INVESTIGATION.md` | Opened protocol-path investigation as next architectural surface | **Closed.** Pass 1 instrumentation answered the binary diagnostic question; this synthesis names the three-layer decomposition the artifact's findings imply. Anti-scope binding carries forward and strengthens. |

Neither predecessor is being amended — they stand as the investigative archaeology that produced this synthesis.

## What this artifact opens

Four operationally-disjoint paths within the three-domain frame:

1. **Path A — Salvage formalization.** Promote Bug-D salvage from compensation to designed normalization layer. Architectural; v1.6+ scope.
2. **Path B — Canonical operation-intent type.** Define the provider-agnostic internal object referenced in §B. Architectural; v1.6+ scope.
3. **Path C — Domain-boundary discipline.** Codify §C as a forward-governance norm — protocol changes and economics changes evaluated against disjoint metrics. Process/discipline; immediate.
4. **Path D — Operator-facing optimization.** Flame reachability fast-fail and conversational tool-free path. Operationally visible; v1.6+ scope; informed by the measurements but constrained by the operator's "do not pre-empt protocol-path investigation" guidance (now resolved).

Path ordering and phase scope are not bound by this artifact — that's the operator-direction surface for v1.6 planning, not this synthesis's scope.

## What this artifact does NOT do

This artifact freezes architectural framing. It does **not**:

- open a v1.6 milestone
- create phase boundaries
- specify implementation order for Paths A-D
- amend either predecessor investigation
- modify any code

The synthesis is the work. Subsequent work executes from this framing; this framing does not execute itself.

---

*Artifact authored 2026-05-14 evening immediately after the canonical-warm Pass 1 instrumentation measurement. Operator-framed; cross-references and structural scaffolding added during transcription. Builds on `.planning/COLD-START-INVESTIGATION.md` and `.planning/PROTOCOL-VS-SUBSTRATE-INVESTIGATION.md`. Closes the investigative arc those artifacts opened. Opens four directional paths within the resulting three-domain frame.*
