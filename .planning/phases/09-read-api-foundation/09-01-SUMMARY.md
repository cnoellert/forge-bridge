---
phase: 09-read-api-foundation
plan: 01
subsystem: entrypoint-cli
tags:
  - cli
  - typer
  - lint
  - bootstrap
requires:
  - typer>=0.24,<1
  - pytest-timeout>=2.2.0
provides:
  - typer_root_app: forge_bridge.__main__.app
  - typer_console_app: forge_bridge.__main__.console_app (empty — Phase 11 fills it)
  - script_entry: "forge-bridge = forge_bridge.__main__:app"
  - lint_gate_T20: ruff flake8-print repo-wide with tests/** carve-out
affects:
  - forge_bridge/__main__.py
  - pyproject.toml
  - tests/test_typer_entrypoint.py
tech-stack:
  added:
    - "typer==0.24.1 (already transitively available via mcp[cli])"
    - "pytest-timeout>=2.2.0 (dev extras)"
  patterns:
    - "Typer callback with invoke_without_command=True + ctx.invoked_subcommand guard"
    - "Lazy import of heavy modules inside the callback body (fast --help path)"
    - "CliRunner + unittest.mock.patch of lazy-import target for env-propagation tests"
key-files:
  created:
    - tests/test_typer_entrypoint.py
  modified:
    - forge_bridge/__main__.py
    - pyproject.toml
decisions:
  - "D-10: bare `forge-bridge` boots MCP unchanged (no_args_is_help=False on root app)"
  - "D-11: `forge-bridge console --help` exits 0 even with no subcommands registered (no_args_is_help=True on console_app)"
  - "D-22: ruff T20 gate live repo-wide with tests/** carve-out; Phase 11 adds forge_bridge/cli/** carve-out"
  - "D-27: --console-port flag precedence via manual os.environ write (envvar=None on the Option, not Typer's built-in envvar lookup, for self-documenting precedence)"
  - "Script entry points at `forge_bridge.__main__:app` (Typer instance is callable) — replaces the previously-broken `:main` entry"
  - "Lazy import of forge_bridge.mcp.server keeps `console --help` fast (no asyncio/httpx/websockets drag on help-only paths)"
metrics:
  duration: 4m2s
  completed: 2026-04-23
  tasks: 3
  files_touched: 3
commits:
  - 8c76098 feat(09-01): rewrite __main__.py as Typer root
  - e5b88f8 chore(09-01): fix [project.scripts] + add ruff T20 gate + pytest-timeout
  - 1ca2d39 test(09-01): add Typer entrypoint acceptance tests
requirements_complete:
  - API-02
---

# Phase 9 Plan 01: Typer-Root Refactor + Ruff T20 Gate Summary

Landed the Typer root refactor per D-10/D-11 (bare `forge-bridge` boots MCP on stdio,
`forge-bridge console --help` exits 0 as an empty subcommand group reserved for Phase
11) and the ruff T20 (flake8-print) lint gate per D-22 (banning stray `print(` repo-wide
so Plan 09-02's `forge_bridge/console/` files are lint-gated from their first commit).

## What Was Done

### Task 1 — `forge_bridge/__main__.py` rewrite
- Replaced the 4-line bootstrap (`from ... import main; main()`) with a full Typer root.
- `app = typer.Typer(..., no_args_is_help=False)` — bare invocation MUST boot MCP.
- `console_app = typer.Typer(..., no_args_is_help=True)` attached via `app.add_typer`.
- `@app.callback(invoke_without_command=True)` with a `--console-port` option that
  pushes the value into `os.environ["FORGE_CONSOLE_PORT"]` with flag > env > default
  precedence before lazily importing `forge_bridge.mcp.server.main`.
- Module-level import is side-effect-free; `app` is the module-level Typer instance
  consumed by `[project.scripts]`.

### Task 2 — `pyproject.toml` edits
- Fixed the pre-existing broken script entry: `forge_bridge.__main__:main` → `:app`.
- Added `[tool.ruff.lint] extend-select = ["T20"]`.
- Added `[tool.ruff.lint.per-file-ignores]` with `"tests/**" = ["T20"]`.
- Added `pytest-timeout>=2.2.0` to the `dev` optional-dependencies group (I-01 enabler
  for Plan 09-03 Task 6's `@pytest.mark.timeout(60)` marker).
- Version unchanged at `1.3.0`.

### Task 3 — `tests/test_typer_entrypoint.py`
- Six subprocess + CliRunner-based acceptance tests covering D-10, D-11, D-27, and a
  regression guard that `import forge_bridge.__main__` has no side effects.
- `test_bare_forge_bridge_boots_mcp_not_help` uses a guaranteed-free port (bound then
  released) as the `FORGE_BRIDGE_URL` so `startup_bridge`'s graceful-degradation path
  fires and proves `mcp_main()` was reached.
- `test_console_port_flag_sets_env` uses `typer.testing.CliRunner` +
  `unittest.mock.patch("forge_bridge.mcp.server.main", side_effect=...)` to capture
  the env at the moment `mcp_main` would have run — avoids standing up a real MCP
  server and keeps the test <0.1s.

## Key Files Touched

| File | Role | Status |
|------|------|--------|
| `forge_bridge/__main__.py` | Typer root, module-level `app`, callback + lazy-import of `mcp_main` | Modified (4 lines → 58 lines) |
| `pyproject.toml` | `[project.scripts]` fix, T20 gate + carve-outs, `pytest-timeout` dev dep | Modified (+16/-1 lines) |
| `tests/test_typer_entrypoint.py` | Six acceptance tests | Created (171 lines) |

## Per-Task Commit SHAs

| Task | Name | SHA | Files |
|------|------|-----|-------|
| 1 | Rewrite `__main__.py` as Typer root | `8c76098` | `forge_bridge/__main__.py` |
| 2 | Fix script entry + ruff T20 gate + pytest-timeout | `e5b88f8` | `pyproject.toml` |
| 3 | Typer entrypoint acceptance tests | `1ca2d39` | `tests/test_typer_entrypoint.py` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Added dead-code carve-outs for pre-existing T20 violations**
- **Found during:** Task 2 verification
- **Issue:** The plan's acceptance criterion (`ruff check forge_bridge/` exits 0) and
  its verification block (`ruff check forge_bridge/ --extend-select T20 --config
  pyproject.toml` exits 0) both assumed the current codebase was print-free. It wasn't.
  Two orphaned pre-Phase-5 modules violate T20:
  - `forge_bridge/server.py` — 1 `print()` call, imports from nonexistent `forge_mcp.tools`
  - `forge_bridge/shell.py` — 14 `print()` calls, CLI-style interactive shell
  Both reference the long-gone `forge_mcp` package, neither is re-exported in
  `forge_bridge/__init__.py`, and neither is imported at runtime anywhere in the codebase
  or tests (`grep -rn` confirmed zero callers). They are effectively dead code.
- **Fix:** Added two entries to `[tool.ruff.lint.per-file-ignores]` with a FIXME comment
  identifying them as pre-Phase-5 orphans:
  ```toml
  "forge_bridge/server.py" = ["T20"]
  "forge_bridge/shell.py" = ["T20"]
  ```
- **Why not delete:** Deletion is an architectural choice (Rule 4) and not in this plan's
  scope. The carve-out preserves the plan's intent (T20 is live for every real code path,
  especially the forthcoming `forge_bridge/console/`) without the destructive cleanup.
- **Files modified:** `pyproject.toml`
- **Commit:** `e5b88f8`

**2. [Style] Dropped unused `import pytest` from tests/test_typer_entrypoint.py**
- **Found during:** Task 3 authoring
- **Issue:** The plan's test-file shape showed `import pytest`, but no test function
  actually references `pytest` directly (the `monkeypatch` fixture is a parameter name;
  it doesn't require the import). Keeping the import would trip F401 if someone ever
  runs ruff over the file with a non-tests carve-out.
- **Fix:** Removed the unused import.
- **Files modified:** `tests/test_typer_entrypoint.py`
- **Commit:** `1ca2d39`

### Pre-existing ruff noise (out of scope, not fixed)

`ruff check forge_bridge/` (no `--select`) reports 63 pre-existing F401/E701/E741
warnings in other files (`client/async_client.py`, `core/entities.py`, `core/traits.py`,
`flame/endpoint.py`, `store/*.py`, etc.). These existed before Plan 09-01 — verified by
stashing the plan's changes and re-running `ruff check`. They are orthogonal to this
plan's scope (D-22 is specifically about `print(` bans, not general lint hygiene). Not
fixed per the executor's scope boundary rule; a follow-up lint-cleanup plan can address
them in bulk.

## Ruff T20 Status (live)

- `ruff check forge_bridge/ --select T20` exits 0 — gate is green.
- New `print(` in `forge_bridge/console/` (Plan 09-02) will fail this gate at lint time.
- `tests/**` exempted from T20 (pytest debugging / caplog patterns use `print`).
- Phase 11 will add `forge_bridge/cli/**` carve-out when Typer subcommands use
  `rich.print()` (not builtin `print()`).

## Verification Status

| Check | Command | Result |
|-------|---------|--------|
| T20 gate live | `ruff check forge_bridge/ --select T20` | All checks passed |
| Typer app importable | `python -c "from forge_bridge.__main__ import app; ..."` | OK |
| Bare help exits 0 | `python -m forge_bridge --help` | exit 0 |
| Console help exits 0 | `python -m forge_bridge console --help` | exit 0 |
| New tests pass | `pytest tests/test_typer_entrypoint.py -x -q` | 6/6 pass |
| Regression guard | `pytest tests/ -x -q --ignore=tests/test_typer_entrypoint.py` | 289/289 pass |

## Forward-Facing Notes

**Plan 09-02 constraint:** Ruff T20 is now enforced on every commit forward. The very
first file Plan 09-02 adds to `forge_bridge/console/` must use `logger.info(...)` or
similar — `print(...)` will fail lint at the earliest commit, exactly as D-22 specifies.

**Plan 09-03 constraint:** `pytest-timeout` is now in the `dev` extras group so the
`@pytest.mark.timeout(60)` marker planned for Plan 09-03 Task 6 will actually enforce
the timeout rather than be silently ignored.

**Script-entry fix downstream:** Any consumer who installed forge-bridge pre-09-01 via
`pip install -e .` had a broken `forge-bridge` command (ImportError on script resolution
because `__main__.py` did not expose `main`). Post-09-01, re-running `pip install -e .`
(or a fresh install) makes `forge-bridge --help` work from any shell.

## Self-Check: PASSED

- FOUND: `forge_bridge/__main__.py` (modified)
- FOUND: `pyproject.toml` (modified)
- FOUND: `tests/test_typer_entrypoint.py` (created)
- FOUND: commit `8c76098`
- FOUND: commit `e5b88f8`
- FOUND: commit `1ca2d39`
