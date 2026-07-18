# Bridge Canonical Warning-Free Proof

Date: 2026-07-18
Branch: `codex/canonical-warning-hygiene`
Baseline: Bridge v1.9.2 (`5f35cfc`)

## Result

The canonical Bridge suite is warning-free:

```text
3760 passed, 19 skipped in 135.00s (0:02:15)
```

Command:

```bash
/Users/cnoellert/miniconda3/envs/forge/bin/python -m pytest -q \
  --tb=short \
  --junitxml=/tmp/forge-bridge-zero-warning-20260718.xml
```

The v1.9.2 baseline passed the same test count with 40 warnings.

## Warning Ownership

- Alembic now declares `path_separator = os`, removing 30 configuration
  deprecations.
- The Console's HTTP-only uvicorn server disables WebSocket protocol loading,
  avoiding legacy protocol deprecations without changing Bridge's state
  WebSocket service.
- HTTPX malformed-body coverage uses `content=` instead of deprecated raw
  `data=` input.
- The integration server harness no longer looks like a pytest test class.
- Health and structural bootstrap unit tests use opt-in fake SQL sessions.
  Real daemon-runtime and store integration tests retain live Postgres.
- The no-Postgres E2E and integration harnesses patch the session symbol used
  by `forge_bridge.server.app`, not only the router and source module.
- Per-test database teardown no longer attempts a known-to-fail superuser-only
  `pg_terminate_backend` call after its engine has already been disposed.

## Focused Gates

```text
36 passed  health + identity + bootstrap, RuntimeWarning promoted to error
50 passed  graph engine + manifest assembler, RuntimeWarning promoted to error
48 passed  lifespan + routes + E2E + integration, RuntimeWarning promoted to error
12 passed  bootstrap unification + real daemon runtime, RuntimeWarning promoted to error
```

Runtime instrumentation over the four formerly leaking unit boundaries recorded
zero calls to the process-global async engine after the fixes.

## Scope Note

Ruff still reports pre-existing unused imports and legacy formatting in the two
older integration modules. No new Ruff finding points at this slice's added
lines, and `git diff --check` passes.
