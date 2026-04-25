---
phase: 11
plan: "01"
subsystem: cli-foundation
tags: [cli, typer, rich, httpx, sync-http, test-scaffolding]
dependency_graph:
  requires:
    - "Phase 9: console_app Typer group scaffold + /api/v1/* envelope contract"
    - "Phase 10.1: D-40/D-41 artist column lessons; HUMAN-UAT #2 default-sort affordance"
  provides:
    - "forge_bridge.cli.client: sync httpx wrapper with typed exceptions + envelope unwrap"
    - "forge_bridge.cli.render: Rich Console factory + status chip + hash truncation + Created ▼"
    - "forge_bridge.cli.since: --since parser (Nm/Nh/Nd/Nw + ISO 8601, ~30 LOC)"
    - "tests/conftest.py:free_port fixture (shared across all test_cli_*.py)"
  affects:
    - "Plan 02 imports client.py / render.py / since.py with no infrastructure ambiguity"
tech_stack:
  added:
    - "rich>=13.9.4 — direct dep (was fragile two-hop transitive via mcp[cli]→typer→rich)"
  patterns:
    - "sync httpx.Client(base_url=..., timeout=10.0) as context manager (per-invocation)"
    - "type(exc).__name__ only — never str(exc) — for any wrapped exception (LRN-05 / T-11-01)"
    - "127.0.0.1 hardcoded in _build_base_url (T-11-03)"
    - "FORGE_CONSOLE_PORT int() try/except + range clamp [1, 65535] (T-11-04)"
    - "rich.box.SQUARE + bold yellow header style (CONTEXT.md Area 3 locked visual contract)"
    - "Created ▼ glyph signals default-sort affordance (Phase 10.1 HUMAN-UAT #2 lesson)"
key_files:
  created:
    - forge_bridge/cli/__init__.py
    - forge_bridge/cli/client.py
    - forge_bridge/cli/render.py
    - forge_bridge/cli/since.py
    - tests/test_cli_client.py
    - tests/test_cli_rendering.py
  modified:
    - pyproject.toml
    - tests/conftest.py
decisions:
  - "fetch_raw_envelope ships alongside fetch — needed by --json mode for byte-faithful API responses; same exception contract"
  - "console_server fixture intentionally NOT moved to conftest.py — tightly coupled to async + register_canonical_singletons setup; Plan 01 unit tests use respx-style mocking via httpx.MockTransport instead"
  - "T20 carve-out for forge_bridge/cli/** NOT activated in pyproject.toml — no print() calls needed; Console.print() and typer.echo() cover everything (placeholder comment kept for Plan 02 if needed)"
metrics:
  duration: "~25 minutes"
  completed: 2026-04-24
  tasks: 3
  files: 8
  tests_added: 39
  tests_total_passing: 520
---

# Phase 11 Plan 01: CLI Foundation Primitives Summary

Sync httpx wrapper with typed exceptions and envelope unwrap, Rich rendering helpers (status chips, hash truncation, Created ▼ sort affordance), --since parser supporting Nm/Nh/Nd/Nw + ISO 8601, and Wave 0 test scaffolding (conftest free_port fixture + 39 unit tests covering client + rendering primitives at 100% line coverage).

## Files Created / Modified

| File | Status | Lines | Purpose |
|------|--------|-------|---------|
| `forge_bridge/cli/__init__.py` | created | 1 | Empty package marker |
| `forge_bridge/cli/client.py` | created | 124 | Sync httpx wrapper, typed `ServerError` / `ServerUnreachableError`, `fetch()` (unwraps `data`), `fetch_raw_envelope()` (full envelope for `--json`), `resolve_port()`, `_build_base_url()` |
| `forge_bridge/cli/render.py` | created | 78 | `make_console()`, `status_chip()`, `short_hash()`, `format_timestamp()`, `created_column_header()`, `TOOLS_BOX = box.SQUARE`, `HEADER_STYLE = "bold yellow"` |
| `forge_bridge/cli/since.py` | created | 32 | `parse_since(value)` — Nm/Nh/Nd/Nw relative + ISO 8601 with Z-suffix normalization for Python 3.10 |
| `tests/conftest.py` | modified | +20 | Append `free_port` fixture (shared across all `test_cli_*.py`) |
| `tests/test_cli_client.py` | created | 220 | CLI-02 — 23 tests covering port resolution, base URL, exception class, fetch + fetch_raw_envelope across 200/400/connect/timeout/protocol/malformed paths |
| `tests/test_cli_rendering.py` | created | 100 | CLI-04 — 16 tests covering Console factory, status chips (parametrized over 8 known statuses + unknown), hash truncation, timestamp formatting, constants |
| `pyproject.toml` | modified | +1 | Pin `rich>=13.9.4` as direct dep |

## Threat Model Mitigations

| Threat ID | Category | Mitigation | Test that proves it |
|-----------|----------|------------|---------------------|
| **T-11-01** | Information Disclosure (credential leak via `str(exc)`) | `ServerUnreachableError.__init__(exc_class_name)` stores only `type(exc).__name__`, never `str(original_exc)` (LRN-05 rule from Phase 8). Verified by grep: `forge_bridge/cli/client.py` contains `type(exc).__name__` (2 occurrences — one per fetch / fetch_raw_envelope call site). | `tests/test_cli_client.py::TestServerUnreachableError::test_stores_class_name_only` + `TestFetch::test_raises_unreachable_on_*` (3 tests assert `exc.exc_class_name == "ConnectError"` / `"ReadTimeout"` / `"RemoteProtocolError"`) |
| **T-11-03** | Tampering / Spoofing (CLI pointed at non-loopback host) | `_build_base_url(port)` returns `f"http://127.0.0.1:{port}"` literal — no `--bind-host` / `--remote` flag (locked v1.3 non-goal). Verified by grep: `127.0.0.1` appears in `client.py`. | `tests/test_cli_client.py::TestBuildBaseURL::test_loopback_only` — regex match `^http://127\.0\.0\.1:\d+$` |
| **T-11-04** | Denial of Service / Tampering (operator-controlled `FORGE_CONSOLE_PORT`) | `resolve_port()` wraps `int()` in `try/except ValueError` → `typer.Exit(1)`; clamps to `[1, 65535]` → `typer.Exit(1)`. Both paths emit a stderr message before exiting. | `tests/test_cli_client.py::TestResolvePort::test_malformed_raises_exit_1`, `test_out_of_range_low_raises_exit_1`, `test_out_of_range_high_raises_exit_1` |

T-11-02 (JSONL tail-parse safety) is NOT in scope for this plan — it is the responsibility of the `doctor` subcommand in Plan 02.

## Coverage

```
Name                           Stmts   Miss  Cover
forge_bridge/cli/__init__.py       0      0   100%
forge_bridge/cli/client.py        62      0   100%
forge_bridge/cli/render.py        25      0   100%
forge_bridge/cli/since.py         14     14     0%   (Plan 02 exercises via --since tests)
TOTAL                            101     14    86%
```

`forge_bridge/cli/client.py` and `forge_bridge/cli/render.py` are at **100% line coverage**, well above the Phase 11 Nyquist floor of 80%. `since.py` is functionally verified (manual smoke test: 9/9 cases pass — `30m`, `24h`, `7d`, `2w`, ISO with Z-suffix, date-only, plus rejection of `bad_input`, `P1D`, `yesterday`); coverage will be picked up by Plan 02's `execs --since` tests per the VALIDATION.md plan.

Total CLI surface coverage: **86%** — exceeds the 80% floor.

## Acceptance Criteria Audit

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `pyproject.toml` contains `"rich>=13.9.4"` | ✓ | `grep -c '"rich>=13.9.4"' pyproject.toml` returns 1 |
| `forge_bridge/cli/__init__.py` exists, importable | ✓ | smoke test passes |
| `client.py` contains `class ServerError`, `class ServerUnreachableError`, `def resolve_port`, `def fetch`, `def fetch_raw_envelope`, `_DEFAULT_PORT = 9996`, `def _build_base_url` | ✓ | all symbols importable + grep |
| `client.py` contains literal `"127.0.0.1"` (T-11-03) | ✓ | `grep -c "127\.0\.0\.1"` returns 1 |
| `client.py` exact catch tuple `(httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError)` | ✓ | `grep` returns 2 occurrences (one per fetch / fetch_raw_envelope) |
| `client.py` contains `type(exc).__name__` (T-11-01 LRN-05) | ✓ | `grep` returns 2 occurrences |
| `client.py` contains `if not (1 <= port <= 65535):` clamp (T-11-04) | ✓ | present at line 51 |
| `since.py` contains `_RELATIVE_RE = re.compile(r'^(\d+)(m|h|d|w)$')` and `_UNIT_SECONDS = {...}` | ✓ | grep returns 1 / verified literal |
| `since.py` contains Z-normalization line | ✓ | line 28 |
| `ruff check forge_bridge/cli/` exits 0 | ✓ | "All checks passed!" |
| Import smoke test prints `ok` | ✓ | combined import of all 8 public symbols + parse_since prints `ok` |
| No `print(` substring in `forge_bridge/cli/*.py` | ✓ | `grep -r "print(" forge_bridge/cli/` returns empty |
| `render.py` contains `def make_console(`, `def status_chip(`, `def short_hash(`, `def format_timestamp(`, `def created_column_header(`, `TOOLS_BOX = box.SQUARE`, `HEADER_STYLE = "bold yellow"` | ✓ | all symbols importable |
| `render.py` contains literal `"▼"` | ✓ | line 38 |
| Status map has 8 entries (active/ok/loaded/degraded/warn/fail/absent-when-required/absent) | ✓ | parametrized test enumerates all 8 |
| `TOOLS_BOX is rich.box.SQUARE` evaluates True | ✓ | `tests/test_cli_rendering.py::TestConstants::test_tools_box_is_square` |
| `created_column_header() == 'Created ▼'` | ✓ | `tests/test_cli_rendering.py::TestConstants::test_created_column_header` |
| `tests/conftest.py` contains `def free_port` | ✓ | `grep -c "def free_port"` returns 1 |
| `tests/test_cli_client.py` contains test classes `TestResolvePort`, `TestBuildBaseURL`, `TestServerUnreachableError`, `TestFetch` (+ `TestFetchRawEnvelope` added for coverage) | ✓ | all 5 test classes present |
| `tests/test_cli_client.py` covers all 5 httpx exception paths | ✓ | `test_raises_unreachable_on_{connect_error,timeout,remote_protocol_error}` + `test_raises_server_error_on_400` + `test_unwraps_envelope_on_200` |
| `tests/test_cli_client.py` contains T-11-04 tests | ✓ | `test_malformed_raises_exit_1`, `test_out_of_range_low/high_raises_exit_1` |
| `tests/test_cli_client.py` contains T-11-03 test asserting `127.0.0.1` | ✓ | `TestBuildBaseURL::test_loopback_only` |
| `tests/test_cli_rendering.py` parametrizes all 8 known statuses | ✓ | `TestStatusChip::test_known_statuses` parametrize list |
| `pytest tests/test_cli_client.py -x -q` exits 0 | ✓ | 23 passed |
| `pytest tests/test_cli_rendering.py -x -q` exits 0 | ✓ | 16 passed |
| Coverage on client.py ≥ 80% | ✓ | 100% |
| Coverage on render.py ≥ 80% | ✓ | 100% |

## Test Suite Health

- Plan 01 added: **39 new tests** (23 client + 16 rendering)
- Plan 01 net delta on full suite: **+39 tests, 0 regressions**
- Full suite before Plan 01: 481 tests passing
- Full suite after Plan 01: **520 tests passing** (481 + 39)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test Bug] Initial `test_no_color_flag_strips_ansi` assertion was too strict**

- **Found during:** Task 3 verification
- **Issue:** The test asserted `"\x1b["` is absent from output when `Console(no_color=True, force_terminal=True)` renders `[bold red]text[/bold red]`. But Rich's `no_color` only strips COLOR codes, not STYLE codes (bold/italic/dim) — confirmed by RESEARCH.md §3 and live behavior. Bold ANSI (`\x1b[1m`) is preserved; only the red color (`\x1b[31m`) is stripped.
- **Fix:** Renamed test to `test_no_color_flag_strips_color_codes`; assertion now checks specifically for color SGR codes (`\x1b[31m`, `\x1b[91m`, `\x1b[38;`, `\x1b[48;`) being absent rather than ALL escape sequences. This matches Rich's actual contract.
- **Files modified:** `tests/test_cli_rendering.py`
- **Commit:** included in Task 3 commit `9ab116e`

### Coverage Push to Hit 80% on client.py

The plan acceptance criteria called for `≥ 80% on forge_bridge/cli/client.py`. After the originally-specified test set, coverage on client.py was 79% (just below) because `fetch_raw_envelope()` was untested (lines 105-124 — entire function uncovered). This is a public symbol exposed in the acceptance criteria's `exports: [..., fetch_raw_envelope]` (via the imports smoke test).

Added a `TestFetchRawEnvelope` class with 4 tests (200/400/connect-error/non-JSON-body), bringing client.py to 100%. This is Rule 1 (auto-fix bug) — the plan listed `fetch_raw_envelope` in the import smoke test but did not include behavior tests for it.

## Authentication Gates

None. CLI runs against localhost-only HTTP API with no auth (locked v1.3 non-goal).

## Confirmation: Clean Python REPL Smoke Test

```
$ python -c "from forge_bridge.cli.client import fetch, ServerError, ServerUnreachableError, resolve_port; from forge_bridge.cli.render import make_console, status_chip, short_hash, TOOLS_BOX, HEADER_STYLE, created_column_header; from forge_bridge.cli.since import parse_since; print('ok')"
ok
```

All Plan 01 public symbols load without import errors from a clean Python interpreter. Plan 02 can begin — no infrastructure ambiguity remains.

## Self-Check: PASSED

**Files exist:**
- forge_bridge/cli/__init__.py ✓
- forge_bridge/cli/client.py ✓
- forge_bridge/cli/render.py ✓
- forge_bridge/cli/since.py ✓
- tests/test_cli_client.py ✓
- tests/test_cli_rendering.py ✓
- pyproject.toml ✓ (modified)
- tests/conftest.py ✓ (modified)

**Commits exist on this branch (5a4fd9f..HEAD):**
- `95d4026` feat(11-01): add cli foundation primitives — client, since parser, package init ✓
- `1e17659` feat(11-01): add Rich rendering helpers — make_console, status_chip, short_hash, Created ▼ ✓
- `9ab116e` test(11-01): wave 0 — conftest free_port fixture + cli_client + cli_rendering tests ✓
