# Phase A.4 Runtime Integrity — Structurally Confirmed

**Captured:** 2026-05-06, during Phase A.6 closure
**Source phase:** A.6 — Daemon Runtime Integrity (`.planning/phases/A.6-daemon-runtime-integrity/`)
**Subject:** the startup-path unification work landed in commit `52e2743 phase-a4: daemon startup-path unification — bootstrap_daemon()`

---

## What A.6 expected to find

A.6 was opened because the bisect window from the last known healthy chat session (2026-05-05 14:25:56) to a confirmed-broken chat path contained exactly one substantive commit: A.4. The A.5 hard-elevate condition matched every named A.4 trigger phrase verbatim — `bootstrap_daemon()`, `teardown_daemon()`, `_lifespan`, asyncio loop ownership, startup-path unification — and per discipline A.5 paused while A.6 audited the runtime.

The phase's working assumption: A.4 introduced something — a defect, an ordering regression, a loop-affinity bug, a session-manager race — that broke the LLM path in a runtime-integrity sense.

## What A.6 actually found

The 75-second chat failure was **environmental**, not a code regression. The configured Ollama endpoint (`192.168.86.15:11434`) was unreachable from the workstation; macOS TCP connect timed out at its default ~75 s; the daemon faithfully surfaced that as `LLMToolError`. Reachability tests with `ping`, `nc`, and `curl` reproduced the same 75 s outside the daemon process — refuting any asyncio / loop / library-internal hypothesis.

The A.4 commit landed approximately **90 seconds after** the last-healthy chat session. The bisect was temporally correct but **causally wrong**: A.4 was co-incident with a network state change, not the source of one.

## What this confirms about A.4

A.4 unified four daemon entry points (`mcp stdio`, `mcp http`, `fbridge up`, launchd plist) onto a single `bootstrap_daemon()` startup path with bytecode-equivalent Steps 1-6 plus a new Step 0 (`_wait_for_bus`). Until A.6, this work was assessed as "appears to work" — a softer claim than the spec's "every entry point inherits identical initialization" invariant deserved.

A.6 produced **structural confirmation**:

1. **The lifecycle map (Step 1)** statically traced `bootstrap_daemon` from its callers (`_lifespan`, `_composed_lifespan`) through every entry point, confirming they converge on a single asyncio loop `L` and a single set of initialization steps. No entry-point-specific bypass was found in static reading.
2. **The Step 2 timing probe** showed pre-call latency of 0.88 ms from `complete_with_tools` through the lazy-allocation site to library entry. There is no detectable bootstrap-induced blockage between router construction (Step 4 of bootstrap) and first-use lazy allocation. If A.4 had introduced a loop-ownership or starvation regression, this gap would have been observable.
3. **The Step 3 OS-level reproductions** showed identical 75-second timeouts from `nc` and `curl` running outside the daemon. The daemon is doing exactly what any other client process with the same target would do — no daemon-specific runtime artifact exists.

Together these three independent lines of evidence support a stronger claim than "A.4 still appears to work":

> **A.4's startup-path unification produces a structurally sound runtime substrate.** The bus-readiness gate (`_wait_for_bus`) does what its commit message claims; the `bootstrap_daemon` / `teardown_daemon` factoring preserves the prior `_lifespan` 6-step sequence; the single-loop ownership invariant holds in practice as well as in design.

This is the kind of confirmation that's hard to schedule for its own sake. A.6 produced it as a side-effect of treating A.4 as suspect and forcing structural evidence to surface.

## What this means for future runtime work

- **The A.4 invariant is now a load-bearing assumption that has been tested.** Future work that touches daemon initialization (entry points, lifespan ordering, task ownership) can reason against the A.6 lifecycle map (`.planning/phases/A.6-daemon-runtime-integrity/RUNTIME-MAP.md`) as a verified baseline, not a working-but-unaudited narrative.
- **The lifecycle map should be promoted to `docs/RUNTIME.md` if and when it survives the next material runtime change unmodified.** Per the A.6 spec, the map is "intended to survive as a durable reference for future runtime work."
- **Treat bisect outcomes that match named trigger phrases as necessary-but-not-sufficient.** A.5.1's hard-elevate was correct discipline, but it ran on circumstantial evidence (commit timing + symbol overlap). Future reliability phases that elevate on similar grounds should add a cheap environmental-cause ruleout pass before committing to deep-runtime investigation. Two minutes of `ping` / `nc` / `curl` would have caught the network state change before A.6 opened — not a reason to skip the elevate, but a reason to bound it tighter.

## Discipline note

The methodological observation worth preserving: **the act of treating a commit as suspect, generating a falsifiable runtime model, and instrumenting against it is what produced the confirmation that A.4 is correct.** The substantive output of a reliability phase is not always a fix; sometimes it is structural evidence about code that was previously trusted by inertia.

A.4 went into A.6 as the prime suspect. It came out structurally confirmed. That is a real result.
