# A.5.1 — Hard Elevate Triggered

**Date:** 2026-05-06
**Outcome:** STOP Phase A.5. Elevate A.5.1 into a separate daemon-runtime phase.

## Bisect window

Last known healthy chat session: `2026-05-05 14:25:56` (`~/.forge-bridge/logs/mcp_http.log` — `chat ok`, 40.5 s, end_turn).
Current state: every prompt that escapes the narrower fails with `LLMToolError` at iter=0 after ~75 s.

```
git log --since="2026-05-05 14:00" --until="2026-05-06 14:00" --oneline --reverse

52e2743 phase-a4: daemon startup-path unification — bootstrap_daemon()
d7ee43f Merge pull request #2 from cnoellert/phase-a4/startup-path-unification
```

One substantive commit. One merge.

## Diff scope

```
forge_bridge/console/read_api.py      |  44 ++++++
forge_bridge/mcp/server.py            | 274 ++++++++++++++++++++++++++--------
packaging/launchd/forge-bridge-daemon |  17 +--
tests/console/test_lifespan_wiring.py |  15 ++
tests/test_bootstrap_unification.py   | 269 +++++++++++++++++++++++++++++++++
tests/test_packaging.py               |  27 +++-
```

Symbol-level changes in `forge_bridge/mcp/server.py`:
- Renamed `_lifespan` → `bootstrap_daemon()`
- Added `teardown_daemon()`
- Added `_wait_for_bus()` — bus-readiness gate moved into daemon bootstrap
- Restructured `_lifespan` into a thin wrapper delegating to bootstrap/teardown
- Touched daemon launch wrapper (`packaging/launchd/forge-bridge-daemon`)

## Why this trips the elevate condition

The Phase A.5 spec defines a hard elevate trigger with this list:

> `bootstrap_daemon()`, `teardown_daemon()`, lifespan, asyncio loop ownership, daemon lifecycle, or startup-path unification

Every item in that list is present in commit `52e2743`. The trigger is unambiguous.

The spec's reason: at this point this is no longer "router health." It is **runtime integrity uncertainty**. Patching around it inside A.5 would risk landing reliability fixes against an unstable substrate.

## What is NOT yet known

- Whether the LLMRouter's connection pool is being constructed under the wrong loop.
- Whether the bus-wait gate is starving the router init.
- Whether router lifespan is now bound to a task that gets cancelled or never started.
- Whether the regression is environmental (Ollama base URL resolution from inside daemon vs. shell).

These are exactly the questions a daemon-runtime phase should answer. Not under A.5.

## Recommended next step

Open a new phase scoped to runtime integrity. Suggested title:

> **Phase A.6 — Daemon Runtime Integrity (router lifecycle audit)**

Phase A.5 remains open with status **PAUSED — gated on A.6**. The masking finding, smoke-test results, and decomposition stand. A.5.2 and A.5.3 cannot land while A.6 is in flight (per the spec's parallelization rule for A.5.2).

## Discipline note

The smoke-test methodology worked exactly as intended. Without a structured baseline (Test 0 deterministic, Test 1 conversational LLM-only, Test 4 multi-tool), the dependency between failures would have been invisible and the natural temptation would have been to patch `LLMRouter` directly — which would have masked the actual A.4-induced regression. The hard-elevate gate forced the diagnostic to halt at the right place.
