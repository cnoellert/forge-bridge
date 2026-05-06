# Phase A.6 — Daemon Runtime Integrity

**Status:** **CLOSED 2026-05-06** — environmental finding, no code change. See `A.6-CLOSE.md`.
**Opened:** 2026-05-06
**Milestone:** v1.5 Legibility (interrupt — gated A.5)
**Predecessors:** Phase A (truthful chat contract), Phase A.4 (startup-path unification — structurally confirmed by A.6), Phase A.5 (resumed at A.6 close)
**Discipline:** diagnostic-first. Steps 1–4 were diagnostic-only. Patching was authorized only after Step 4 classification — and Step 4 classified the cause as environmental (unreachable Ollama endpoint), so no patches landed in this phase.

---

## Why this phase exists

A.6 was opened because **A.5.1 triggered its hard-elevate condition immediately.**

The bisect window between the last known healthy chat session (`2026-05-05 14:25:56`) and the current broken state contains exactly one substantive commit: `52e2743 phase-a4: daemon startup-path unification — bootstrap_daemon()`. That commit touches every named trigger phrase in the A.5 spec verbatim:

- `bootstrap_daemon()`
- `teardown_daemon()`
- `_lifespan`
- asyncio loop ownership
- startup-path unification
- `_wait_for_bus` ordering

Therefore the current failure class is:

> **daemon runtime integrity**, not chat reliability.

A.5 remains **PAUSED** until runtime lifecycle correctness is restored and verified.

### Carried forward unchanged from A.5 (none of this work is lost)

- Smoke-test results (Tests 0–5)
- Masking-finding analysis
- Three-bug decomposition (router → forced-call → narrower)
- A.5.2 forced-tool schema work (queued)
- A.5.3 narrowing / vocabulary work (queued)
- Vocabulary learnings note plan (queued, written at first narrowing-fix decision)

A.5 resumes only after A.6 closes successfully.

---

## Architectural framing

| Phase | Solved |
|-------|--------|
| A | Observability — truthful chat contract, round-trip tool execution history |
| A.4 | Startup-path consistency — single `bootstrap_daemon()` for every entry point |
| A.5 (paused) | Reliability in the shared chain execution layer |
| **A.6 (this)** | **Runtime integrity — daemon lifecycle correctness as a load-bearing substrate** |
| Future | Usability — making truthful, reliable execution legible and comfortable for humans to operate |

The runtime substrate is now load-bearing enough that lifecycle understanding must become **explicit rather than implicit tribal knowledge**.

---

## Initial hypotheses (investigative targets, NOT confirmed root causes)

These are starting points for diagnostic work. Do **not** collapse hypothesis into conclusion prematurely.

1. **Wrong event-loop affinity** — `LLMRouter`'s connection pool / async client constructed under one loop, used from another.
2. **Router initialization starvation** — the new `_wait_for_bus` gate inside `bootstrap_daemon` blocks or reorders router construction.
3. **Cancelled / unstarted lifespan task** — router lifespan now bound to a task that gets cancelled or never started.
4. **Daemon-vs-shell environment divergence** — Ollama base URL / model selection / `OLLAMA_HOST` resolves differently inside the daemon process than from the shell.
5. **Lifecycle ordering regression introduced during startup-path unification** — startup steps run in a different order than pre-A.4, breaking router init invariants that pre-A.4 took for granted.

The classification step (Step 4) selects which of these is the actual cause from evidence, not assumption.

---

## Authorization boundary (BINDING)

**Steps 1–4 are diagnostic-only.** No patching is authorized during:

- lifecycle mapping
- loop-ownership analysis
- environment verification
- observability instrumentation
- classification

**Patching is authorized only after Step 4 (classification) lands.**

Reason: runtime-integrity work is especially vulnerable to premature "obvious fix" behavior. The purpose of A.6 is to **understand lifecycle correctness before mutating it further.** A wrong fix at this layer would compound the original A.4 regression instead of resolving it.

This boundary is binding even if a candidate fix becomes obvious during diagnosis. Surface the candidate, do not land it. Step 4 evaluates all candidates against the full classification before any code is touched.

---

## Step 1 — Lifecycle map (REQUIRED deliverable)

The lifecycle map is **not** a side artifact. It is a required deliverable of A.6 and must survive the phase as a durable runtime reference at:

```
docs/RUNTIME.md   (or .planning/phases/A.6-.../RUNTIME-MAP.md if scoped narrower)
```

The map must clearly show:

- daemon startup sequence
- loop ownership (which task / coroutine owns which loop)
- task ownership (who creates which `asyncio.Task`, who awaits/cancels it)
- lifespan ordering (which steps run before which other steps)
- router initialization timing (relative to `_wait_for_bus`, MCP bind, console mount)
- where `bootstrap_daemon()`, `teardown_daemon()`, and `_wait_for_bus()` participate
- which entry points own which stages — at minimum:
  - Claude Desktop `mcp stdio`
  - direct `python -m forge_bridge` (i.e. `mcp http`)
  - `fbridge up` subprocess spawn
  - launchd plist (`packaging/launchd/forge-bridge-daemon`)

**Why this matters beyond A.6:** the runtime is now load-bearing for chat, exec, console, MCP stdio, and the Flame hook. Future phases (A.5 resumption, vocabulary work, observability instrumentation) will all reference this map. Implicit understanding is no longer adequate.

---

## Step 2 — Loop-ownership / task-ownership analysis

Using the Step 1 map, identify:

- Which loop owns the `LLMRouter` and its underlying clients (`AsyncOllamaClient`, `AsyncAnthropicClient`).
- Whether router construction occurs on the same loop that handles `/api/v1/chat` requests.
- Whether any router-owned task is created under one loop and awaited from another.
- Whether `_wait_for_bus` introduces an `await` boundary that displaces router init relative to pre-A.4.
- Whether `teardown_daemon` is reachable from every entry-point exit path (some launch shells may SIGKILL before `teardown_daemon` runs — that's lifecycle data, not a bug).

Output: a concise findings document appended to the lifecycle map.

---

## Step 3 — Environment verification (daemon vs. shell)

Verify, **from inside the daemon process** (not from the shell):

- `OLLAMA_HOST` / Ollama base URL resolution.
- Model name resolution (default model, `sensitive=True` routing target).
- Whether `httpx.AsyncClient` (or whatever HTTP client the router uses) sees the same DNS / network behavior the shell does.
- Whether any environment variable the router reads is empty / unset / different inside the daemon.

Method: one-shot probe handler or a debug log emitted during `bootstrap_daemon` startup. **Read-only**. No behavior change.

---

## Step 4 — Classification

Synthesize Steps 1–3 findings into a structured classification document:

- Confirmed root cause (with evidence trail).
- Refuted hypotheses (with evidence).
- Remaining ambiguity (if any).
- Proposed fix scope (minimal change, named functions/modules, no implementation yet).
- Regression-test requirements (must reproduce the failure before any fix lands).
- Whether the fix is reversible (can it be reverted cleanly if it makes things worse).

**No code is touched in Step 4.** The output is a document that authorizes the next step.

---

## Step 5 — Apply fix (authorized only after Step 4)

Land the minimal change identified in Step 4. Do **not** absorb adjacent cleanup, refactors, or "while we're here" improvements. Reversibility takes priority over elegance.

---

## Step 6 — Re-smoke-test (Tests 0–5)

After the fix lands, re-run the full A.5 smoke-test sequence. Required outcomes:

- Test 1: 200, `stop_reason=end_turn`, `tool_trace=[]`. Real LLM loop executed. No 75 s timeout.
- Test 5: no longer collapses to router failure (independent of degraded-state correctness, which is A.5.3 territory).
- Tests 0, 2, 3, 4: behavior unchanged from the A.5 smoke baseline (these failures still exist; they are A.5's job).

If any test that was passing before A.6 now fails, that is a regression. Investigate before closing.

---

## Step 7 — Resume A.5

Hand back to A.5 with:

- Updated smoke-test baseline (Tests 1 and 5 now pass; Tests 0, 2, 3, 4 still in their pre-A.6 failure shape).
- Lifecycle map preserved at the agreed location.
- A.5.2 and A.5.3 free to land per their original gates.

---

## Hard elevate condition (inside A.6 itself)

A.6 has its own elevate trigger. **STOP A.6 and elevate** if:

- The classification reveals that the regression is **not** in the A.4 commit (i.e. the bisect window was too narrow because the daemon was already broken before 2026-05-05 14:25 and we mistook a coincidence for a root cause).
- The classification reveals that the daemon's loop / lifecycle architecture is structurally incorrect in ways that predate A.4 — meaning the fix requires more than a localized correction to A.4-era code.
- Step 1's lifecycle map cannot be produced because the runtime is too tangled to map confidently — that itself is a finding, and means a full runtime redesign should be scoped before patching.

In any of these cases, do not patch. Surface the elevate, recommend the new phase scope, and pause A.6.

---

## Invariants (must hold across all A.6 work)

- PR31 envelope contract preserved on `/api/v1/exec`.
- Phase A truthful chat contract preserved on `/api/v1/chat`.
- All four entry points keep working (`mcp stdio`, `mcp http`, `fbridge up`, launchd plist) — the A.4 invariant is not regressed.
- Public `forge_bridge.__all__` stays at 19.
- No new external libraries.
- No A.5 work pulled forward into A.6 (no narrowing tweaks, no forced-call-wrapper changes, no UI work).

---

## Out of scope (plant seeds, do not absorb)

| Tangent | Disposition |
|---------|-------------|
| Forced-tool schema fix | A.5.2, gated on A.6 close |
| Narrower correctness | A.5.3, gated on A.6 close |
| Vocabulary learnings note | A.5.3 deliverable |
| Tool-row UI rendering | `SEED-CHAT-UI-TOOL-ROW-RENDERING-V1.5+` |
| Ask / Foundry surface | `SEED-FLAME-CHAT-FOUNDRY-V1.6+` |
| Schematic | `SEED-NODE-SCHEMATIC-V1.6+` |
| Streaming | `SEED-CHAT-STREAMING-V1.4.x` |
| Auth | `SEED-AUTH-V1.5` |
| Default-model bump | `SEED-DEFAULT-MODEL-BUMP-V1.4.x` |
| Observability instrumentation broader than what Step 3 needs | seed for follow-on |

---

## Methodology meta-observation (record, do not formalize yet)

The reliability discipline is now empirically validated across multiple phases:

- **Phase A** — contract realignment / truthful execution history.
- **Phase A.4** — elevation from "single client surface" to "single startup path."
- **Phase A.5 → A.6** — smoke-test → bisect → hard-elevate sequence stopping work at the correct runtime boundary on the **first** investigative step.

Sample size is still too small to formalize as project-wide methodology. The trajectory is now clear, however: the discipline is producing **real protective value at the moments where mistakes would otherwise compound.** A.5.1's elevate fired before any code was touched. A.6's diagnostic-only authorization extends the same protection to the next layer down.

When A.6 closes, evaluate (do not commit to) whether to extract a durable artifact. Promotion still requires more than two reliability phases of evidence. Avoid prematurely calcifying process.

---

## Execution sequence

1. Open A.6 (this document).
2. Freeze A.5 in PAUSED state.
3. **Step 1** — produce lifecycle/runtime map (REQUIRED deliverable).
4. **Step 2** — loop / task-ownership analysis.
5. **Step 3** — environment verification (daemon vs. shell).
6. **Step 4** — classification document.
7. **Step 5** — apply fix (only now is patching authorized).
8. **Step 6** — re-smoke-test (Tests 0–5).
9. **Step 7** — resume A.5.

Proceed carefully.
