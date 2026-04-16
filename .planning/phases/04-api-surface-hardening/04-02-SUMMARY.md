---
phase: 04-api-surface-hardening
plan: 02
subsystem: mcp
tags: [api-hardening, lifecycle, registry, tdd]
dependency_graph:
  requires: []
  provides: [startup_bridge, shutdown_bridge, _server_started, register_tools-guard]
  affects: [forge_bridge.mcp.server, forge_bridge.mcp.registry]
tech_stack:
  added: []
  patterns: [lazy-import-circular-avoidance, arg-env-default-precedence, _server_started-flag]
key_files:
  created: []
  modified:
    - forge_bridge/mcp/server.py
    - forge_bridge/mcp/registry.py
    - tests/test_mcp_registry.py
decisions:
  - "startup_bridge/shutdown_bridge are clean renames — no backward-compat alias per D-11"
  - "_server_started transitions False->True in _lifespan before yield, False in finally for test isolation"
  - "register_tools guard uses lazy module import (not name import) per R-5 to avoid circular import and stale snapshot"
metrics:
  duration_seconds: 165
  completed_date: "2026-04-16"
  tasks_completed: 2
  files_changed: 3
requirements_addressed: [API-04, API-05, PKG-01]
---

# Phase 04 Plan 02: Server Lifecycle Public API + Register-Tools Guard Summary

**One-liner:** Public `startup_bridge`/`shutdown_bridge` lifecycle API with arg→env→default precedence, `_server_started` flag gating `register_tools()` post-run via lazy module-attribute read.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rename _startup/_shutdown + add _server_started flag | 77150f6 | forge_bridge/mcp/server.py |
| 2 | Post-run guard in register_tools + three regression tests | f2d3fdc (RED), b20ab2f (GREEN) | forge_bridge/mcp/registry.py, tests/test_mcp_registry.py |

## What Was Built

### Task 1: Server Lifecycle Public API (API-04)

Renamed `_startup()` → `startup_bridge(server_url, client_name)` and `_shutdown()` → `shutdown_bridge()` in `forge_bridge/mcp/server.py`.

Key changes:
- `startup_bridge` accepts `server_url: str | None = None` and `client_name: str | None = None`, using arg → env → default precedence (same pattern as `LLMRouter`)
- `shutdown_bridge` is parameterless — symmetrical with startup, no config needed for teardown
- Module-level `_server_started: bool = False` added near `_client` declaration
- `_lifespan` sets `_server_started = True` immediately after `await startup_bridge()` and before `yield` (BEFORE FastMCP accepts connections — T-04-06 mitigation)
- `_lifespan` resets `_server_started = False` in `finally` block for test isolation
- Clean break: no backward-compat aliases (`_startup`/`_shutdown` are gone)

D-16 audit result: zero references to `_startup`/`_shutdown` in the test suite — no test edits required for the rename.

### Task 2: Post-Run Guard + Regression Tests (API-05, PKG-01)

Added guard to `register_tools()` in `forge_bridge/mcp/registry.py`:
- Lazy `import forge_bridge.mcp.server as _server` inside the function body avoids the `server.py → registry.py → server.py` circular import
- Reading `_server._server_started` (module attribute) captures the current value on every call — not a stale snapshot from a name-binding import (R-5)
- Raises `RuntimeError("register_tools() cannot be called after the MCP server has started. Register all tools before calling mcp.run().")` when flag is True
- `register_builtins(mcp)` at `server.py:107` is called during module import (before any `_lifespan` run), so `_server_started` is still `False` — guard does NOT fire for builtin registration

Three new tests in `tests/test_mcp_registry.py`:
1. `test_register_tools_builtin_source` — PKG-01: `source="builtin"` accepted, `meta == {"_source": "builtin"}`
2. `test_register_tools_post_run_guard` — API-05: RuntimeError raised when `_server_started=True`
3. `test_register_tools_pre_run_ok` — API-05: success when `_server_started=False`

All three tests use `try/finally` to restore `_server_started` to original value (test isolation).

## Verification Results

- `pytest tests/ -x --no-header -q`: **162 passed** (all tests green)
- `pytest tests/test_mcp_registry.py -v`: **10 passed** (7 existing + 3 new)
- Cold-import sanity: `import forge_bridge.mcp.registry; import forge_bridge.mcp.server` — exits 0
- Public surface: `from forge_bridge.mcp.server import startup_bridge, shutdown_bridge; from forge_bridge.mcp.registry import register_tools` — exits 0
- No `_startup`/`_shutdown` in `forge_bridge/mcp/` (other `_shutdown` references are `self._shutdown` on unrelated classes in `server/app.py` and `flame/sidecar.py` — pre-existing, unrelated)

## Deviations from Plan

None — plan executed exactly as written.

## Notes on Output Requirements

- **D-16 audit was clean**: Zero references to `_startup`/`_shutdown` in tests before the rename — no test edits were required for the rename.
- **`_server_started = False` in finally block**: Kept (recommended path taken) — aids test isolation, matches PATTERNS.md target shape.
- **`register_builtins(mcp)` at import time does NOT trigger the guard**: Confirmed — `register_builtins` calls `register_tool` (singular), not `register_tools` (plural). The guard only applies to the public `register_tools()` entry point, and even if it did, `_server_started` is `False` during module import.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The `_server_started` flag is a module-level boolean — consistent with existing threat model analysis (T-04-06, T-04-07 documented in plan).

## Self-Check: PASSED

Files exist:
- forge_bridge/mcp/server.py: FOUND
- forge_bridge/mcp/registry.py: FOUND
- tests/test_mcp_registry.py: FOUND

Commits exist:
- 77150f6: FOUND (Task 1 — server.py rename)
- f2d3fdc: FOUND (Task 2 RED — test file)
- b20ab2f: FOUND (Task 2 GREEN — registry.py guard)
