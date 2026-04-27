---
phase: 16-fb-d-chat-endpoint
plan: 02
subsystem: console
tags: [rate-limiting, token-bucket, chat, security, threading]
requires:
  - python>=3.10
  - dataclasses (stdlib)
  - threading (stdlib)
  - time (stdlib)
provides:
  - forge_bridge.console._rate_limit.check_rate_limit
  - forge_bridge.console._rate_limit.RateLimitDecision
  - forge_bridge.console._rate_limit._reset_for_tests
affects:
  - "Plan 16-04 (chat handler) imports check_rate_limit + RateLimitDecision"
  - "Plan 16-04 wires HTTP 429 + Retry-After translation per D-09/D-13"
tech-stack:
  added: []           # zero new deps — stdlib only
  patterns:
    - "Module-level mutable state guarded by threading.Lock (mirrors read_api.py canonical id pattern)"
    - "Frozen @dataclass for return types (immutable decision contract)"
    - "Lazy TTL eviction on every call (no background sweeper)"
    - "_-prefixed test affordance (Phase 9 _canonical_* convention)"
key-files:
  created:
    - "forge_bridge/console/_rate_limit.py"
    - "tests/console/test_rate_limit.py"
  modified: []
decisions:
  - "Followed plan exactly — no deviations encountered"
  - "Wrote tests first (RED gate) then implementation (GREEN gate) — two atomic commits"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-27"
  tasks: 2
  files: 2
  tests: 10
  test_runtime: "<0.02s"
---

# Phase 16 Plan 02: Rate Limit Module Summary

**One-liner:** In-process IP-keyed token-bucket rate limiter (`check_rate_limit` + frozen `RateLimitDecision`) for the v1.4 chat endpoint — capacity 10, refill 10/60s, 300s lazy idle eviction, threading.Lock-guarded module state. Zero new deps.

## What Shipped

A single greenfield module (`forge_bridge/console/_rate_limit.py`, 101 lines) and a deterministic test file (`tests/console/test_rate_limit.py`, 125 lines, 10 tests, runtime <0.02s). The module ships the CHAT-01 enforcement primitive that plan 16-04 (chat handler) consumes via:

```python
from forge_bridge.console._rate_limit import check_rate_limit, RateLimitDecision

decision = check_rate_limit(client_ip)
# decision.allowed: bool   — True if a token was consumed
# decision.retry_after: int — seconds until at least 1 token refills (>=1 when blocked, 0 when allowed)
```

Plan 16-04 will translate `allowed=False` to HTTP 429 with `Retry-After: <retry_after>` per D-09/D-13.

## D-13 Numerical Contract (pinned in module constants)

| Constant         | Value | Meaning                                                |
| ---------------- | ----- | ------------------------------------------------------ |
| `_CAPACITY`      | 10.0  | Max tokens per IP                                      |
| `_REFILL_SECONDS`| 60.0  | Refill window (1 token every 6 s, sliding)             |
| `_REFILL_RATE`   | ~0.167| Tokens/sec (`_CAPACITY / _REFILL_SECONDS`)             |
| `_TTL_SECONDS`   | 300.0 | Idle eviction — buckets idle >5 min are dropped lazily |

## Tasks Completed

### Task 1 — `forge_bridge/console/_rate_limit.py` (GREEN commit `bc96b5e`)

- Module docstring documents D-13 design + migration path to caller-identity bucketing under SEED-AUTH-V1.5.
- `RateLimitDecision` is `@dataclass(frozen=True)` with `allowed: bool, retry_after: int`.
- `check_rate_limit(client_ip)` performs lazy TTL sweep, refills tokens since last touch (clamped to `_CAPACITY`), consumes 1 if available, otherwise returns `retry_after` clamped to `>=1` (prevents 0-second client retry storms).
- `_reset_for_tests()` clears `_buckets` under `_lock`. Production code MUST NOT call.
- `threading.Lock` (NOT `asyncio.Lock`) per D-13 single-process v1.4 stance.
- All 9 acceptance-criterion grep checks pass; smoke-verify exits 0.

### Task 2 — `tests/console/test_rate_limit.py` (RED commit `c7dafaf`)

10 deterministic tests; `monkeypatch.setattr(_rate_limit.time, "monotonic", ...)` is the time-control vector — no real `time.sleep` anywhere:

| Test                                            | What it pins                                              |
| ----------------------------------------------- | --------------------------------------------------------- |
| `test_decision_is_frozen`                       | `FrozenInstanceError` on attempted mutation               |
| `test_decision_fields`                          | Field round-trip                                          |
| `test_first_request_allowed`                    | First call → allowed=True, retry_after=0                  |
| `test_eleventh_request_blocked`                 | D-13 capacity invariant                                   |
| `test_distinct_ips_have_independent_buckets`    | No cross-IP throttle leakage                              |
| `test_refill_after_60s`                         | Full bucket refill at the contract window                 |
| `test_partial_refill_proportional`              | ~50% refill at 30s (4..5 successes accepting float drift) |
| `test_stale_buckets_evicted_after_ttl`          | TTL=300s → bucket evicted on next call                    |
| `test_unknown_ip_handled`                       | Starlette `request.client = None` fallback works          |
| `test_reset_for_tests_clears_state`             | Test affordance contract                                  |

`autouse=True` `_reset_state` fixture means every test starts with empty buckets — no inter-test leak. Total runtime: 0.01s on this machine, well under the <2s plan budget.

## Threat Model Outcomes

| Threat ID    | Disposition | Status                                                                                     |
| ------------ | ----------- | ------------------------------------------------------------------------------------------ |
| T-16-02-01   | accept      | "unknown" bucket DoS surface acknowledged in module docstring + RESEARCH.md; v1.5 fix     |
| T-16-02-02   | mitigate    | All read-then-mutate sequences guarded by `_lock`; critical sections microseconds         |
| T-16-02-03   | accept      | Single-process v1.4 only; multi-process bucket sharing out of scope                       |
| T-16-02-04   | mitigate    | `_reset_for_tests` is `_`-prefixed and docstring-marked test-only                          |

No new threat surfaces introduced beyond the plan's threat register.

## Verification

- All 9 Task-1 acceptance grep checks: PASS
- All 7 Task-2 acceptance grep checks: PASS
- `pytest tests/console/test_rate_limit.py -x -v --durations=0`: **10 passed in 0.01s**
- `pytest tests/console/`: 10 passed, 33 skipped (existing FB-B handler tests skip without live Postgres `session_factory` — unaffected by this plan)
- `git diff --stat HEAD~2..HEAD` shows only the two intended files
- Plan inline smoke-test command exits 0

## TDD Gate Compliance

- **RED gate** (`c7dafaf`): test file added, fails at import (module doesn't exist yet) — verified before GREEN
- **GREEN gate** (`bc96b5e`): module added, all 10 tests pass — verified after RED
- No REFACTOR commit needed — implementation matches plan template verbatim, code review pass-through clean.

## Deviations from Plan

None — plan executed exactly as written. The plan's `<behavior>` block listed 8 behaviors; the implementation produces 10 test functions because two of those behaviors (frozen dataclass invariant + field round-trip) are split across `test_decision_is_frozen` and `test_decision_fields` per the plan's verbatim test code in Task 2's `<action>`. Acceptance criteria specify exact-named tests and all are present.

## Consumers (Forward References)

- **Plan 16-04** (chat handler, Wave 2): imports `check_rate_limit, RateLimitDecision` and translates `allowed=False` → HTTP 429 + `Retry-After: <retry_after>`. Will pass `request.client.host or "unknown"` per RESEARCH.md §3.1 pitfall.
- **SEED-AUTH-V1.5**: when v1.5 auth lands, the bucket key swaps from `client_ip` to `caller_id` — public surface stable; only the bucket-key argument source changes in plan 16-04.

## Commits

| Commit  | Type | Description                                                |
| ------- | ---- | ---------------------------------------------------------- |
| `c7dafaf` | test | add failing tests for IP token-bucket rate limiter (RED)  |
| `bc96b5e` | feat | implement IP token-bucket rate limiter (GREEN)            |

## Self-Check

- [x] `forge_bridge/console/_rate_limit.py` exists (101 lines, > 60 min_lines)
- [x] `tests/console/test_rate_limit.py` exists (125 lines, > 80 min_lines)
- [x] Commit `c7dafaf` exists in git log (RED)
- [x] Commit `bc96b5e` exists in git log (GREEN)
- [x] All 10 tests pass in <0.02s
- [x] All plan acceptance criteria pass

## Self-Check: PASSED
