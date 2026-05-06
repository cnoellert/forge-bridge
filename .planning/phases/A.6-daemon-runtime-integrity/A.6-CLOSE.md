# Phase A.6 — Closure

**Date:** 2026-05-06
**Status:** **CLOSED — environmental finding, no code change**
**Predecessors:** A (truthful chat contract), A.4 (startup-path unification), A.5 (paused → resuming)

---

## Outcome (one paragraph)

The 75-second chat failure that triggered A.5.1's hard-elevate was **not a code regression.** The daemon's configured Ollama endpoint (`192.168.86.15:11434`, the cross-host assist-01 setup from `/etc/forge-bridge/forge-bridge.env`) is presently unreachable from this workstation; macOS TCP connect times out at its default ~75 s; the daemon faithfully surfaces `LLMToolError`. Reachability tests with `ping`, `nc`, and `curl` reproduce the same 75 s outside the daemon process. The A.4 commit landed ~90 s after the last-healthy chat session and was temporally co-incident with a network state change, not its cause. **A.4's startup-path unification is structurally confirmed correct** (`docs/learnings/a4-runtime-integrity-confirmed.md`).

## What landed

| Artifact | Path |
|----------|------|
| Phase spec | `PHASE-A.6-SPEC.md` |
| Lifecycle map (REQUIRED deliverable) | `RUNTIME-MAP.md` |
| Step 2 timing-probe findings | `STEP-2-FINDINGS.md` |
| Step 3 environment / reachability findings | `STEP-3-FINDINGS.md` |
| Closure document (this file) | `A.6-CLOSE.md` |
| A.5.1 elevation audit trail | `../A.5-chain-execution-reliability-audit/A.5.1-ELEVATE.md` |
| A.5 status (paused → resuming) | `../A.5-chain-execution-reliability-audit/STATUS.md` |
| A.4 runtime confirmation | `docs/learnings/a4-runtime-integrity-confirmed.md` |
| Seed: fast-fail LLM connect timeout | `.planning/seeds/SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+.md` |
| Seed: external-dependency preflight probes | `.planning/seeds/SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+.md` |

## What did NOT land (intentionally)

- Code changes to `bootstrap_daemon`, `teardown_daemon`, `_lifespan`, `_wait_for_bus`. The runtime substrate is correct; nothing to fix.
- A UX-timeout fix in `_adapters.py`. **Planted as seed** (`SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+`) for v1.5 chat-reliability resumption. Out of A.6 scope per the spec's authorization boundary.
- An audit of every external-dependency client construction site. **Planted as seed** (`SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+`).
- The Step 2 timing probe. **Removed** from `forge_bridge/llm/_adapters.py` (verified `grep` returns 0 matches for `probe-A6` / `_a6_` / `A6 PROBE`); module re-imports clean.

## Phase invariants (verified at close)

- PR31 envelope contract on `/api/v1/exec`: preserved.
- Phase A truthful chat contract on `/api/v1/chat`: preserved.
- All four entry points still functional (`mcp stdio`, `mcp http`, `fbridge up`, launchd plist): preserved.
- Public `forge_bridge.__all__` at 19: preserved (no public surface change).
- No new external libraries: preserved.
- No A.5 work pulled forward into A.6: preserved.

## Methodology results captured (preserve, do not formalize yet)

A.6 produced **three** independent methodological observations across Steps 1-3. Each is preserved in its source artifact; consolidated here for the methodology-promotion question (still gated on additional reliability phases).

### 1. "Map first, probe second" produces diagnostic leverage

**Source:** Step 1 → Step 2.
The lifecycle map's lazy-allocation finding (router.py:817-871, 240-264, 468) downgraded "wrong-loop affinity" from a top hypothesis to structurally implausible **before** the probe ran. The masking-relationship subsection identified the failing surface (lazy-allocation LLM-loop path) which directly determined where the probe was placed. Probing the wrong path would have produced clean traces and told us nothing.

### 2. Verify the bisect is *causal*, not co-incident

**Source:** Step 3 vs. A.5.1 elevate.
A.5.1's bisect window contained exactly one substantive commit and matched the spec's named trigger phrases verbatim. That was diagnostically correct discipline, but it ran on circumstantial evidence: commit timing plus symbol overlap. Two minutes of `ping` / `nc` / `curl` against the configured Ollama endpoint would have surfaced the environmental cause **before** A.6 opened.

**Forward rule for future reliability phases:** when a hard-elevate condition triggers on a bisect window, run a cheap environmental-cause ruleout pass (network reachability, environment variables, host resolution) before committing to deep runtime investigation. This is **not a reason to skip the elevate** — the discipline of evidence-before-patching remains correct. It is a reason to bound the elevated phase tighter.

### 3. A reliability phase's substantive output is not always a fix

**Source:** A.6 closure as a whole.
A.4 entered A.6 as the prime suspect. It came out structurally confirmed. That is a real result — the kind of confirmation that's hard to schedule for its own sake but is produced naturally as a side-effect of forcing structural evidence to surface. Future runtime work can now reason against the A.6 lifecycle map as a verified baseline, not a working-but-unaudited narrative.

These three observations are still **sample-size 3** (Phase A, A.4, A.5→A.6). Per the methodology-promotion gate, do not formalize yet. Continue preserving observations across future reliability phases.

## A.5 hand-off

A.5 resumes immediately, with sharpened scope. See `../A.5-chain-execution-reliability-audit/STATUS.md` for the resume conditions:

- **A.5.2** (forced-tool wrapper schema contract) — proceeds. The Pydantic `params`-required mismatch reproduces statically; no working LLM path needed.
- **A.5.3.1** (semantic mismatch — "list projects" → `forge_list_staged`) — proceeds. The `_tool_filter` keyword-matching logic reproduces statically; the wrong narrowing decision can be inspected without running the LLM.
- **A.5.3.2** (over-eager collapse — multi-intent prompts hijacked by PR20 short-circuit) — **deferred** until LLM reachability returns. Diagnosing the over-eager collapse requires comparing the narrower's choice against what the LLM would do given the same prompt — that comparison is not possible against a dead LLM path. A.5.3.2 will need its own instrumentation when it eventually runs.

The A.5 masking finding is unchanged: forced-tool path bypasses lazy allocation; full LLM loop enters it. A.5.3.2's deferral does not invalidate the masking analysis — it acknowledges that the comparison-against-truth half of the diagnosis cannot land while the comparison's reference is unreachable.

## Phase boundary respected

A.6 did not broaden. The runtime substrate was the only subject; the runtime substrate was found correct; the phase closes. UX, doctor extensions, multi-dependency audit, and timeout-surfacing improvements are all out of A.6 scope by the spec's own out-of-scope list and have been preserved as seeds.

## Closing observation

Both phases produced more value than their original scopes anticipated.

- A.5 originally framed itself as "fix three chat reliability bugs." The smoke-test discipline revealed a masking dependency between them and a structurally distinct fourth issue (environmental) that turned out to dominate.
- A.6 originally framed itself as "audit a suspect commit." The audit confirmed the commit and produced a durable lifecycle map plus three methodological observations.

The discipline of writing the spec carefully, bounding authorization, and preserving evidence at each step is what produced the over-yield. That is the result worth preserving most.
