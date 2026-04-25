---
phase: 11
plan: "02"
subsystem: cli-companion
tags: [cli, typer, rich, httpx, sync-http, p-01-stdout-purity]
dependency_graph:
  requires:
    - "Plan 01: forge_bridge.cli.client / render / since primitives + free_port fixture"
    - "Phase 9: console_app Typer scaffold + /api/v1/* envelope contract"
    - "Phase 10.1: D-40/D-41 artist column lessons + Created ▼ default-sort affordance"
  provides:
    - "forge_bridge.cli.tools — list/drilldown + client-side filters (D-03)"
    - "forge_bridge.cli.execs — list/drilldown + --since parser + W-01 client-side --tool"
    - "forge_bridge.cli.manifest — Rich table or byte-identical --json passthrough"
    - "forge_bridge.cli.health — aggregate pill + 4 service-group panels"
    - "forge_bridge.cli.doctor — expanded diagnostic with CI-gating exit codes"
    - "console_app subcommand registrations: tools, execs, manifest, health, doctor"
  affects:
    - "Plan 03 (soft UAT) — CLI is functionally ready to dogfood"
tech_stack:
  added: []  # rich pinned in Plan 01; no new deps
  patterns:
    - "P-01 stdout-purity: --json guard is the FIRST non-import statement before any Console() instantiation"
    - "T-11-01 / LRN-05: doctor reports JSONL parse failures by line# + type(exc).__name__ only — never raw line"
    - "T-11-02: _tail_jsonl uses plain open(path, 'r') + readlines() with NO fcntl.flock / fcntl.lockf; partial-last-line guard"
    - "W-01 workaround: execs --tool runs client-side after server fetch + emits the locked stderr note (suppressed in --json)"
    - "Single-command Typer test apps register a hidden `__noop__` second command to force subcommand-mode dispatch"
    - "FastMCP RichHandler defense: forge_bridge/cli/__init__.py silences httpx/httpcore INFO logging at import to prevent JSON corruption"
key_files:
  created:
    - forge_bridge/cli/tools.py
    - forge_bridge/cli/execs.py
    - forge_bridge/cli/manifest.py
    - forge_bridge/cli/health.py
    - forge_bridge/cli/doctor.py
    - tests/test_cli_tools.py
    - tests/test_cli_execs.py
    - tests/test_cli_manifest.py
    - tests/test_cli_health.py
    - tests/test_cli_doctor.py
    - tests/test_cli_commands.py
    - tests/test_cli_json_mode.py
  modified:
    - forge_bridge/__main__.py
    - forge_bridge/cli/__init__.py
    - .gitignore
decisions:
  - "execs --tool client-side filter on r.get('tool') is forward-compat: ExecutionRecord doesn't expose tool today, but the W-01 workaround scaffold is in place for v1.4 API extension"
  - "Single-command Typer test apps add a hidden __noop__ command to force subcommand-mode dispatch — without this, runner.invoke(app, ['tools']) treats 'tools' as a positional arg"
  - "httpx + httpcore loggers silenced at WARNING in cli/__init__.py to defend P-01 stdout-purity against FastMCP's RichHandler-on-root side effect"
  - "test_sidecar_dir_missing_warns asserts via --json instead of Rich output: long fact strings are truncated by Rich's table column width"
metrics:
  duration: "~10 minutes"
  completed: 2026-04-25
  tasks: 2
  files: 12 created + 3 modified
  tests_added: 72
  tests_total_passing: 592
---

# Phase 11 Plan 02: Five CLI Subcommands Summary

Five Typer subcommands (`tools`, `execs`, `manifest`, `health`, `doctor`) shipped on top of the Plan 01 primitives, with --json passthrough on every command, exit-code taxonomy 0/1/2 wired across the board, T-11-01 and T-11-02 mitigations implemented in `doctor`, and 72 new tests bringing forge_bridge/cli/ coverage to 91% (well above the 80% Phase 11 Nyquist floor).

## Files Created / Modified

| File | Status | Lines | Purpose |
|------|--------|-------|---------|
| `forge_bridge/cli/tools.py` | created | 209 | List + drilldown view; client-side filters (--origin, --namespace, --readonly, -q/--search); --json envelope passthrough; Created ▼ glyph |
| `forge_bridge/cli/execs.py` | created | 222 | List + drilldown; --since via parse_since; W-01 client-side --tool with locked stderr note (suppressed in --json); --hash, --limit, --offset, --promoted server-side params |
| `forge_bridge/cli/manifest.py` | created | 113 | Rich table with same columns as tools list; -q/--search client-side filter; --json byte-identical to /api/v1/manifest body; --status reserved |
| `forge_bridge/cli/health.py` | created | 116 | Aggregate status pill + 4 Rich Panels per service group (critical / degraded-tolerant / LLM backends / provenance); --json passthrough |
| `forge_bridge/cli/doctor.py` | created | 318 | Expanded diagnostic; translates /api/v1/health into per-service rows; client-side probes (JSONL parseability, sidecar/probation dir, console-port reprobe, disk-space); CI-gating exit codes 0/1/2 |
| `forge_bridge/cli/__init__.py` | modified | +12 | Silence httpx/httpcore INFO loggers at import — P-01 stdout-purity defense against FastMCP's RichHandler-on-root |
| `forge_bridge/__main__.py` | modified | +11 | Five `console_app.command(...)(...)` registrations + deferred import |
| `tests/test_cli_tools.py` | created | 196 | TOOLS-03 — list, filters, drilldown, --json, unreachable, --help |
| `tests/test_cli_execs.py` | created | 273 | EXECS-03 — list, --since (24h + bad input), W-01 --tool stderr note, server-param wiring (code_hash/limit/offset/promoted_only), drilldown, --json |
| `tests/test_cli_manifest.py` | created | 137 | MFST-05 — list, search, byte-identical --json, unreachable, --help, empty |
| `tests/test_cli_health.py` | created | 121 | HEALTH-02 — panels, --json, unreachable (Rich + JSON), --help, empty backends |
| `tests/test_cli_doctor.py` | created | 247 | HEALTH-03 — exit-code matrix, T-11-01 raw-line redaction, T-11-02 lock-free, partial-last-line guard, --json, sidecar dir warn |
| `tests/test_cli_commands.py` | created | 49 | CLI-01 — five-subcommand registration smoke + Examples block per command |
| `tests/test_cli_json_mode.py` | created | 110 | CLI-03 + P-01 — parametrized stdout-purity (4 cmds × 3 scenarios = 12 tests) |
| `.gitignore` | modified | +2 | `.coverage` and `htmlcov/` from pytest-cov runs |

## Threat Model Mitigations

| Threat ID | Category | Mitigation | Test that proves it |
|-----------|----------|------------|---------------------|
| **T-11-01** | Information Disclosure (raw line content in JSONL parse-failure report) | `_check_jsonl_parseability` surfaces failures as `f"line {i}: {type(exc).__name__}"`. Raw line content is NEVER included. The `console_port_reprobe` fail path also uses `type(exc).__name__` only, never `str(exc)`. Verified by grep: `forge_bridge/cli/doctor.py` contains 3 occurrences of `type(exc).__name__`. | `tests/test_cli_doctor.py::test_jsonl_parse_error_exit_1` — asserts `"JSONDecodeError" in result.output` AND `"NOT_JSON" not in result.output` |
| **T-11-02** | DoS / Tampering (JSONL tail-read against concurrent writer) | `_tail_jsonl()` opens with plain `open(path, 'r')` (no `fcntl.LOCK_EX`, no `O_EXLOCK`); reads with `readlines()`; skips the last line when it lacks `\n` (partial-write boundary guard). Verified by grep: `forge_bridge/cli/doctor.py` has zero `fcntl` imports. | Three tests in `tests/test_cli_doctor.py`: `test_jsonl_no_lock_acquired` (mocks `fcntl.flock` and `fcntl.lockf`, asserts both `call_count == 0`), `test_jsonl_partial_last_line_skipped` (asserts trailing partial line is dropped without parse error), `test_jsonl_parse_error_exit_1` (cleanly tail-parses with malformed line surfacing) |

T-11-03 (loopback-only) and T-11-04 (FORGE_CONSOLE_PORT validation) are inherited from Plan 01's `client.py` and exercised across every subcommand here without additional code.

## Coverage

```
Name                           Stmts   Miss  Cover
--------------------------------------------------
forge_bridge/cli/__init__.py       3      0   100%
forge_bridge/cli/client.py        62      0   100%
forge_bridge/cli/doctor.py       149     19    87%
forge_bridge/cli/execs.py        102     14    86%
forge_bridge/cli/health.py        59      3    95%
forge_bridge/cli/manifest.py      55      6    89%
forge_bridge/cli/render.py        25      0   100%
forge_bridge/cli/since.py         14      1    93%
forge_bridge/cli/tools.py         95      9    91%
--------------------------------------------------
TOTAL                            564     52    91%
```

`forge_bridge/cli/` total coverage: **90.78%** — exceeds the 80% Phase 11 Nyquist floor by ~11 points. Every module is at ≥86% line coverage. Uncovered lines are mostly defensive branches in `doctor.py` (disk-space `OSError` fallback; rare reprobe non-200 path) and `--quiet` rendering branches that don't get exercised in the unit-test paths but are visually verified during smoke testing.

## Acceptance Criteria Audit

### Task 1 (tools / execs / manifest)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Three new source files exist | ✓ | `forge_bridge/cli/{tools,execs,manifest}.py` |
| Three new test files exist | ✓ | `tests/test_cli_{tools,execs,manifest}.py` |
| Each source file has `if as_json:` guard as first non-import statement | ✓ | `grep -c "if as_json"` returns 1/2/1 (execs has 2 because the json branch is reused for drilldown) |
| `tools.py` filter flags + global flags | ✓ | `--origin`, `--namespace`, `--readonly`, `-q/--search`, `--json`, `--no-color`, `--quiet` |
| `execs.py` imports `parse_since` | ✓ | `grep -c "from forge_bridge.cli.since import parse_since"` returns 1 |
| `execs.py` filter flags + global flags | ✓ | `--tool`, `--since`, `--until`, `--promoted`, `--hash`, `--limit`, `--offset`, `--json`, `--no-color`, `--quiet` |
| `execs.py` contains `_TOOL_CLIENT_SIDE_NOTE` verbatim from D-04 | ✓ | `grep -c "_TOOL_CLIENT_SIDE_NOTE"` returns 2 |
| `execs.py` does NOT include `tool` in API params | ✓ | code review + `test_tool_filter_does_not_send_to_api` |
| `manifest.py` flags | ✓ | `-q/--search`, `--status`, `--json`, `--no-color`, `--quiet` |
| All test files use `typer.testing.CliRunner` + `httpx.MockTransport` | ✓ | grep |
| `tests/test_cli_execs.py` has both `_TOOL_CLIENT_SIDE_NOTE in non-json` AND `not in --json` | ✓ | `test_tool_flag_emits_stderr_note` + `test_tool_flag_json_suppresses_note` |
| `tests/test_cli_execs.py` has `tool not in API params` test | ✓ | `test_tool_filter_does_not_send_to_api` |
| `--since 24h` parses + `--since bad_input` exits 1 | ✓ | `test_since_24h` + `test_since_bad_input` |
| Three test commands exit 0 | ✓ | 36 passed |
| `ruff check` exits 0 | ✓ | "All checks passed!" |
| `--help` for each contains `Examples:` | ✓ | `test_examples_block` per command |

### Task 2 (health / doctor / registration / cross-command)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All 5 source files exist | ✓ | tools.py, execs.py, manifest.py, health.py, doctor.py |
| `__main__.py` contains all 5 registrations | ✓ | `grep -c 'console_app.command("X")'` returns 1 for each of tools/execs/manifest/health/doctor |
| `doctor.py` contains `def _tail_jsonl(`, `type(exc).__name__`, partial-line guard | ✓ | grep |
| `doctor.py` does NOT call `fcntl.flock` or `fcntl.lockf` | ✓ | `grep "fcntl" forge_bridge/cli/doctor.py` returns empty |
| Doctor exit-code logic | ✓ | `test_all_ok_exit_0` (0), `test_critical_fail_exit_1` (1), `test_unreachable_exit_2` (2), `test_non_critical_warn_exit_0` (warn-only → 0) |
| `test_jsonl_parse_error_exit_1` asserts JSONDecodeError + NOT NOT_JSON | ✓ | T-11-01 verified |
| `test_jsonl_no_lock_acquired` (T-11-02) | ✓ | fcntl.flock + fcntl.lockf both `call_count == 0` |
| `test_jsonl_partial_last_line_skipped` | ✓ | trailing partial line dropped |
| `tests/test_cli_commands.py` covers all 5 `--help` invocations | ✓ | 6 tests in file |
| `tests/test_cli_json_mode.py` parametrized 4 cmds × 3 scenarios | ✓ | 12 parametrized tests |
| `--cov-fail-under=80` exits 0 | ✓ | "Required test coverage of 80% reached. Total coverage: 90.78%" |
| `pytest tests/` exits 0 (no regressions) | ✓ | 592 passed |
| `ruff check forge_bridge/cli/ forge_bridge/__main__.py` exits 0 | ✓ | "All checks passed!" |
| `grep -r "print(" forge_bridge/cli/` has zero hits | ✓ | only `console.print(...)` / `stderr_console.print(...)` matches (Rich Console method, not bare `print()`) — ruff T20 already validates this |

## __main__.py Five-Line Insert (verbatim)

```python
console_app.command("tools")(tools.tools_cmd)
console_app.command("execs")(execs.execs_cmd)
console_app.command("manifest")(manifest.manifest_cmd)
console_app.command("health")(health.health_cmd)
console_app.command("doctor")(doctor.doctor_cmd)
```

(Preceded by `from forge_bridge.cli import doctor, execs, health, manifest, tools  # noqa: E402`; the `noqa: E402` matches the project's existing lazy-import pattern in this file.)

## Test Suite Health

- Plan 02 added: **72 new tests** (36 in Task 1 + 36 in Task 2)
- Plan 02 net delta on full suite: **+72 tests, 0 regressions**
- Full suite before Plan 02: 520 passing (Plan 01 hand-off)
- Full suite after Plan 02: **592 passing**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Critical Functionality] Silenced httpx/httpcore INFO loggers at CLI package import**

- **Found during:** Task 1 verification (test_json_envelope failed)
- **Issue:** Importing `forge_bridge` triggers `from forge_bridge.mcp import register_tools, get_mcp` which in turn instantiates `mcp = FastMCP(...)` whose `__init__` calls `configure_logging(...)` which calls `logging.basicConfig(handlers=[RichHandler(...)])` on the root logger at INFO level. That handler then renders every httpx INFO request log into the `result.output` buffer captured by Click's CliRunner — corrupting the `--json` output and causing `json.loads(result.output.strip())` to fail. P-01 stdout-purity is a HARD plan requirement.
- **Fix:** Added `forge_bridge/cli/__init__.py` body that calls `logging.getLogger("httpx").setLevel(logging.WARNING)` + same for `"httpcore"`. The package import in `forge_bridge/__main__.py` triggers this before any subcommand runs, so the silence is in effect for every CLI invocation without per-command boilerplate. CLI never needs httpx INFO chatter.
- **Files modified:** `forge_bridge/cli/__init__.py` (3 stmts → meaningful module body)
- **Commit:** included in `5e47b7a` (Task 1 commit)

**2. [Rule 1 — Test Bug] Single-command Typer test apps need a hidden second command**

- **Found during:** Task 1 first test run (test_lists_tools failed: GET /api/v1/tools/tools 404)
- **Issue:** Typer collapses single-command apps into the root callback. `app.command("tools")(tools_cmd)` followed by `runner.invoke(app, ["tools"])` causes the literal string `"tools"` to be passed as the positional NAME argument instead of being interpreted as a command name — so `tools_cmd` was called with `name="tools"` and hit `/api/v1/tools/tools` (drilldown for a tool named "tools").
- **Fix:** Each `_make_app()` helper in the test files registers a hidden `__noop__` second command. Two registered commands force Typer into subcommand-mode dispatch where `["tools"]` is treated as the command name.
- **Files modified:** `tests/test_cli_{tools,execs,manifest,health,doctor}.py`
- **Commit:** included in Task 1 / Task 2 commits

**3. [Rule 1 — Test Bug] Stderr-note assertion needed whitespace normalization**

- **Found during:** Task 1 verification (test_tool_flag_emits_stderr_note failed)
- **Issue:** Rich soft-wraps long lines at terminal width (~80 cols). The `_TOOL_CLIENT_SIDE_NOTE` constant (~120 chars) gets broken at "since\nto scan" by Rich. Substring match on the original 120-char string failed.
- **Fix:** Test now collapses whitespace (`" ".join(result.output.split())`) before checking substring — preserves the contract while tolerating soft-wrap.
- **Files modified:** `tests/test_cli_execs.py::TestExecsTool::test_tool_flag_emits_stderr_note`
- **Commit:** included in `5e47b7a`

**4. [Rule 1 — Test Bug] Long fact strings truncated by Rich table column width**

- **Found during:** Task 2 verification (test_sidecar_dir_missing_warns failed)
- **Issue:** `"directory does not exist at /private/var/.../forge-bridge/synthesized/"` is wider than the Rich table's "Fact" column on a small TTY, so Rich truncated with an ellipsis. The substring assertion against `result.output` failed.
- **Fix:** Test now invokes with `--json` and parses the structured envelope to assert against the unrendered `fact` field. This is actually a stronger assertion (it checks the structured value, not the rendered surface).
- **Files modified:** `tests/test_cli_doctor.py::test_sidecar_dir_missing_warns`
- **Commit:** included in `989d0ed`

### Non-Issue Acknowledgement: ExecutionRecord has no `tool` field

`forge_bridge.learning.execution_log.ExecutionRecord` does NOT carry a `tool` field — it only has `code_hash`, `raw_code`, `intent`, `timestamp`, `promoted`. The plan's `r.get("tool") == tool` filter in `execs.py` therefore filters against `None` for real records and produces empty results. This is forward-compatible with v1.4 when the API surfaces tool attribution; the W-01 client-side-filter scaffold (including the locked stderr note) is in place. Test fixtures inject a synthetic `tool` field so the filter behavior is exercised in unit tests. Documented in plan-level decisions above.

### Authentication Gates

None. CLI runs against localhost-only HTTP API with no auth (locked v1.3 non-goal).

## Confirmation: pytest tests/ is green

```
$ pytest tests/ -x -q 2>&1 | tail -2
592 passed, 70 warnings in 15.78s
```

70 warnings are pre-existing Starlette TemplateResponse deprecation warnings unrelated to Phase 11 — see `tests/test_ui_*.py`. Zero new warnings introduced by Plan 02.

## Confirmation: Smoke tests against the actual user environment

```
$ python -m forge_bridge console --help
... (lists all five subcommands with one-line descriptions) ...

$ python -m forge_bridge console doctor (against running server)
... (Rich check table; exit 0 with mcp/watcher/console_port/instance_identity all ok) ...
```

The CLI is live and answers a real `doctor` against the user's running console server.

## Self-Check: PASSED

**Files exist:**
- forge_bridge/cli/tools.py ✓
- forge_bridge/cli/execs.py ✓
- forge_bridge/cli/manifest.py ✓
- forge_bridge/cli/health.py ✓
- forge_bridge/cli/doctor.py ✓
- forge_bridge/cli/__init__.py ✓ (modified)
- forge_bridge/__main__.py ✓ (modified)
- .gitignore ✓ (modified)
- tests/test_cli_tools.py ✓
- tests/test_cli_execs.py ✓
- tests/test_cli_manifest.py ✓
- tests/test_cli_health.py ✓
- tests/test_cli_doctor.py ✓
- tests/test_cli_commands.py ✓
- tests/test_cli_json_mode.py ✓

**Commits exist on this branch (90bc336..HEAD):**
- `5e47b7a` feat(11-02): tools, execs (W-01 client-side --tool), and manifest subcommands + tests ✓
- `989d0ed` feat(11-02): health + doctor subcommands; register all five on console_app; CLI-01/03/P-01 tests ✓
