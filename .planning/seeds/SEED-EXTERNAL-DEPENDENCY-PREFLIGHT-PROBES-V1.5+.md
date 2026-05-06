# SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+

**Planted:** 2026-05-06
**Source:** Phase A.6 — Daemon Runtime Integrity (closure)
**Trigger condition:** any future operator report of "the daemon is hanging" that turns out to be an unreachable external dependency, OR a runtime-resilience phase

## Observation

Phase A.6 surfaced that the daemon depends on **at least four external endpoints** at request time, each of which can fail silently for an extended period (15-75 s) when unreachable:

| Endpoint | Default URL | Daemon code path |
|----------|-------------|------------------|
| state_ws bus | `ws://127.0.0.1:9998` | `bootstrap_daemon` Step 1 (`startup_bridge`) — has fast-fail today via `_wait_for_bus` (Phase A.4) |
| Ollama (LLM) | `$FORGE_LOCAL_LLM_URL` | `OllamaToolAdapter.send_turn` — **no fast-fail today** (subject of `SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+`) |
| Anthropic API | `api.anthropic.com` | `AnthropicToolAdapter.send_turn` — fast-fail behavior unverified |
| Flame HTTP bridge | `http://127.0.0.1:9999` | `forge_bridge.bridge.execute()` — fast-fail behavior unverified; reachability filter in MCP tool registry partially mitigates |
| Postgres | `$FORGE_DB_URL` | session factory — fast-fail behavior unverified |

The A.4 work introduced `_wait_for_bus` for state_ws specifically because that dependency had a known race. The other four were not similarly hardened.

## What this seed covers

A small, consistent **fast-fail probe pattern** for every external dependency the daemon talks to:

1. **Connect-timeout configuration** at every transport-client construction site (where applicable).
2. A `forge doctor` (or `bootstrap_daemon` startup-warning) check that exercises each dependency once and surfaces "X reachable / Y unreachable" before first request.
3. A runtime resilience invariant: **no operator-visible failure should take longer than ~10 seconds to surface clearly**, regardless of which dependency is down.

## What this seed does NOT cover

- Does not require all dependencies to be reachable to start the daemon (graceful degradation is already a v1.4 invariant for state_ws and Flame).
- Does not introduce retries.
- Does not add a heavyweight health-monitoring system.

## Why this is a methodology-level seed, not a single bug fix

A.6 only surfaced this for one dependency (Ollama) because the smoke tests happened to hit that path. The same structural issue almost certainly applies to the other four — but only an audit of construction sites + connect-timeout config would confirm. That audit is the actual unit of work this seed represents, not a single-file fix.

## Suggested scope when this lands

1. Audit every external-dependency client construction site in the codebase for connect-timeout config.
2. Standardize on a small set of timeouts (e.g. `connect=5s`, `read=<dep-specific>`, `pool=5s`).
3. Extend `forge doctor` to exercise each external dependency with the same connect-timeout discipline.
4. Optional: a single startup-warning summary in `bootstrap_daemon` ("LLM endpoint unreachable; chat path will fail fast").

## Why deferred

The Phase A.6 boundary forbade absorbing this. The single-endpoint UX fix (`SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+`) is small enough to land during A.5 resumption; the broader audit is a v1.5+ resilience phase in its own right.

## Cross-reference

- `SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+.md` — the narrow, immediate single-dependency fix this seed generalizes.
- `SEED-DOCTOR-CRASH-LOOP-CHECK-V1.6+.md` — adjacent doctor-extension work.
