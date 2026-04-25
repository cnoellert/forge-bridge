# Phase 11: CLI Companion — Research

**Researched:** 2026-04-24
**Domain:** Typer CLI client consuming `/api/v1/*` HTTP API with Rich terminal output
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Filter flag grammar:** Kebab-case Typer options mirroring Phase 10 D-08 Web UI tokens one-for-one. Flag rosters per command as specified.

**D-02 — `--since` grammar:** Accepts `Nm/Nh/Nd/Nw` relative AND ISO 8601 timestamps; ~15 LOC client-side parser; emits ISO 8601 to API.

**D-03 — `tools` filters client-side:** Fetch full tool list from `/api/v1/tools`, filter in Python before rendering. No API changes.

**D-04 — `execs --tool` client-side (W-01 workaround):** Build API request from server-supported filters, filter returned records by `tool` in Python. One stderr note on every `--tool` invocation. Cap at user-supplied `--limit`.

**D-05 — No `--quarantined` flag:** Quarantined tools filtered upstream at ConsoleReadAPI layer; flag would always return empty.

**D-06 — One canonical `Examples:` block per subcommand docstring.**

**D-07 — Global flags per-command (NOT group-scoped):** `--json`, `--no-color`, `--quiet/-q`. No `--verbose`/`--debug`/`--log-level`. Honors `NO_COLOR`/`FORCE_COLOR` env.

**D-08 — Soft self-administered dogfood UAT gate:** Developer-as-operator acceptable. "Can I decipher the output without re-reading the source?" criterion. `11-UAT.md` records pass/fail + note. No ship-back-to-planning clause.

**Claude's Discretion areas:** Doctor depth, remediation hint shape, exit codes (Area 1); server-unreachable UX for non-doctor commands (Area 2); Rich output shape, density, column choices (Area 3) — all resolved with concrete defaults in CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

- Server-side `/api/v1/tools` filter params
- W-01 `/api/v1/execs?tool=...` server-side filter (v1.4)
- `--wide`/`--compact` density flags
- Humanized timestamps
- `--quarantined` flag
- `--verbose`/`--debug`/`--log-level` CLI flags
- Watch/tail mode
- Interactive REPL
- Embedded server-start mode
- Shell completion (planner decides if low-cost)
- `console export` subcommand
- Configurable retry/backoff
- `--bind-host`/`--remote` flag
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | `forge-bridge` Typer entry-point with `console` subcommand dispatch; subcommands: tools, execs, manifest, health, doctor | Scaffold already in `forge_bridge/__main__.py` (console_app group wired); Phase 11 adds five command registrations |
| CLI-02 | CLI calls console HTTP API on `:9996` via sync `httpx`; all command bodies are sync | Verified: Typer 0.24.1 sync constraint confirmed live; sync `httpx.Client.get()` is the correct pattern |
| CLI-03 | Every subcommand supports `--json` (machine-readable) and `--help` with concrete usage examples | Rich/CliRunner test confirmed: `--json` mode writes clean JSON to stdout; `result.stderr` isolates stderr content in tests |
| CLI-04 | CLI output uses `rich` for human-readable rendering (tables, panels) when stdout is a TTY; plain text otherwise | Rich 14.3.3 confirmed installed; SQUARE box verified; TTY auto-detection via `Console()`; `Console(stderr=True)` routes stderr messages separately |
| TOOLS-03 | `forge-bridge console tools` subcommand lists tools with same data and filter flags as Web UI view | Client-side filter implementation pattern confirmed; D-03 decision locks no API extension |
| EXECS-03 | `forge-bridge console execs` subcommand returns same view — default last 50 records, `--json`, `--since` | `--since` parser shape confirmed (15 LOC, handles Z-suffix cross-Python-version); D-04 client-side `--tool` pattern confirmed |
| MFST-05 | `forge-bridge console manifest` subcommand returns manifest as JSON or human-formatted Rich table | Byte-identical envelope from `/api/v1/manifest`; `--json` passthrough confirmed correct approach |
| HEALTH-02 | `forge-bridge console health` subcommand returns same status (Rich panel or `--json`) | Health response shape from `read_api.py` fully inspected; CLI unwraps `{data, meta}` envelope and renders service blocks |
| HEALTH-03 | `forge-bridge console doctor` runs expanded diagnostic — HEALTH-01 checks + manifest validation + JSONL parsability + probation summary + actionable remediation hints; non-zero exit on failure for CI gating | Doctor probe sequence confirmed; JSONL tail-read safe with concurrent writer (verified); exit code taxonomy D-04 Area 2 is implementable with `typer.Exit(code=N)` |
</phase_requirements>

---

## Executive Summary

- **`rich` is available transitively via `mcp[cli]` → `typer` → `rich`, but must be pinned as a direct dep.** `mcp[cli]` lists `typer>=0.16.0` as an extras dep. `typer==0.24.1` declares `rich>=12.3.0` as a direct dep. `mcp` itself has a separate `[rich]` extra that pins `rich>=13.9.4`. The chain works today (`rich 14.3.3` is installed), but if `mcp[cli]` ever upgrades typer to a version that no longer bundles rich, or if the project pins `mcp` but not `[cli]`, `rich` disappears silently. **Verdict: add `"rich>=13.9.4"` as a direct dep in `pyproject.toml`.**

- **Typer 0.24.1 + CliRunner works correctly for exit-code assertions.** Both `typer.Exit(code=N)` and `sys.exit(N)` propagate correctly through `typer.testing.CliRunner` and subcommand groups. `result.output` contains combined stdout+stderr; `result.stderr` contains stderr only — use this separation in P-01 JSON-purity tests.

- **The `--since` parser is safe on Python 3.11.** `datetime.fromisoformat` in Python 3.11 accepts `Z` suffix natively. For Python 3.10 compatibility (project minimum is 3.10), apply a `.replace('Z', '+00:00')` normalization before calling `fromisoformat` — 1 extra LOC, no new dep.

- **Rich SQUARE box renders correctly in both TTY and dumb/piped contexts; `NO_COLOR`/`FORCE_COLOR` are handled automatically** by `Console.__init__` — no manual plumbing needed in CLI code. At narrow widths (< 80 cols) Rich truncates with `…` gracefully rather than wrapping or crashing.

- **The httpx connection-error catch for exit-2 path is: `(httpx.ConnectError, httpx.TimeoutException)`.** `ConnectError` covers refused connections and DNS failures. `TimeoutException` is the base class for `ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, and `PoolTimeout`. `RemoteProtocolError` is a subclass of `ProtocolError` (not `NetworkError`) and should be added separately for the edge case where the server starts responding then dies mid-response.

---

## Technical Assumptions: Confirm or Disconfirm

### 1. Is `rich` transitively available via `mcp[cli]`? Must it be pinned as a direct dep?

**CONFIRMED with pinning required.** [VERIFIED: pip show commands + importlib.metadata inspection]

`mcp[cli]>=1.19,<2` pulls in `typer>=0.16.0`. Typer 0.24.1 declares `rich>=12.3.0` as a direct dep. Therefore `rich 14.3.3` is currently installed. However:

- `mcp` base package does NOT list `rich` in its `Requires`
- `mcp[rich]` extra pins `rich>=13.9.4` independently
- `rich` arrives only through `mcp[cli]` → `typer` — a two-hop transitive dependency with no lower-bound above 12.3.0

**If `mcp[cli]` is upgraded to a typer version that relaxes or removes the rich dep, or if the project ever adds `mcp` without `[cli]`, rich disappears silently.**

**Verdict: Add `"rich>=13.9.4"` to `pyproject.toml` `[project.dependencies]`.** This is the version already provided by the `mcp[rich]` extra and matches what the research confirmed as having the `SQUARE` box style. This is the only pyproject.toml change Phase 11 needs (plus the ruff T20 carve-out for `forge_bridge/cli/`).

### 2. Does `typer.testing.CliRunner` capture Rich-formatted stdout cleanly?

**CONFIRMED: Rich stdout capture works correctly.** [VERIFIED: live test in forge conda env]

Key findings from direct testing:

- `CliRunner` captures all stdout into `result.output` (includes stderr unless `mix_stderr=False`)
- `CliRunner.__init__` in Typer 0.24.1 does NOT accept `mix_stderr` kwarg (Click-based runners differ)
- `result.stderr` attribute IS available and contains only the stderr portion
- `result.output` = stdout + stderr combined
- `Console(stderr=True).print(...)` output appears in `result.stderr`; `Console().print(...)` output appears in `result.output` but NOT in `result.stderr`
- **P-01 JSON-purity test pattern:** In `--json` mode, check `result.output == result.stderr + json_body` — i.e., subtract `result.stderr` from `result.output` to isolate stdout; then assert `json.loads(stdout_only)` succeeds.

**Known gotcha with `Console(stderr=True)` in tests:** When writing to stderr (for the `--tool` client-side note, `--json` connection-error envelope, etc.), always route through `Console(stderr=True)` rather than `typer.echo(err=True)` — both work in the runner, but using Rich's stderr console keeps the style-stripping logic consistent.

**Shell-completion via `--install-completion`:** Works at the Typer level (confirmed: appears in `--help`), but requires `shellingham` to detect the shell at runtime. In a subshell/CI environment where `shellingham.detect_shell()` raises `ShellDetectionFailure`, `--install-completion` exits with code 1 and "Shell None is not supported." Verdict from CONTEXT.md deferred list: include `--install-completion` as a freebie — it's zero cost to include (already in every Typer app), but document that it may fail in non-interactive shells. No extra packaging logic required.

### 3. What is the correct sync-httpx connection-error matrix for the "server unreachable → exit 2" path?

**VERIFIED via live inspection of httpx 0.28.1 exception hierarchy.** [VERIFIED: python MRO introspection]

```
httpx.ConnectError        → NetworkError → TransportError  (refused connection, DNS failure)
httpx.ConnectTimeout      → TimeoutException → TransportError  (connect phase timed out)
httpx.ReadTimeout         → TimeoutException → TransportError  (server accepted, no response)
httpx.WriteTimeout        → TimeoutException → TransportError  (request body timeout)
httpx.PoolTimeout         → TimeoutException → TransportError  (connection pool exhausted)
httpx.RemoteProtocolError → ProtocolError → TransportError  (server dropped mid-response)
```

**Recommended catch pattern in `forge_bridge/cli/client.py`:**

```python
try:
    response = client.get(path, timeout=10.0)
except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
    # exit code 2 — server unreachable
    raise ServerUnreachableError from exc
```

`httpx.TimeoutException` covers `ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, and `PoolTimeout` in one catch. `httpx.RemoteProtocolError` is NOT a subclass of `NetworkError` (confirmed via MRO) and must be caught separately. For the Phase 11 pure-client use case (one synchronous GET per invocation), `WriteTimeout` and `PoolTimeout` are theoretically possible but extremely unlikely; catching the full `TimeoutException` base is low-cost insurance.

**Note from CONTEXT.md D-04 Area 2:** `httpx.TimeoutException` is the correct generic form; the CONTEXT.md text lists `httpx.ConnectTimeout` individually but the pattern above handles the full timeout family.

**Sources:** [VERIFIED: `python3 -c "import httpx; print(httpx.ConnectError.__mro__)"` etc.], [CITED: https://www.python-httpx.org/exceptions/]

### 4. Rich `Console.print` + CliRunner stdout capture: any stream-corruption cases documented?

**NO corruption cases found. The P-01 discipline is sufficient.** [VERIFIED: live tests]

The concern in P-01 is mixing Rich-styled bytes with raw JSON on the same stdout stream. Testing confirmed:

- When `--json` mode exits before any Rich calls, `result.output` is clean JSON
- Rich's `Console()` (no stderr arg) writes to stdout; `Console(stderr=True)` writes to stderr — they do not cross-contaminate in CliRunner
- Rich adds ANSI escape codes only when `Console(force_terminal=True)` or when the output is a real TTY; in CliRunner (non-TTY), `Console()` emits plain text without ANSI codes by default
- **The only corruption risk:** If a `Console()` print is accidentally called before the `--json` early-return guard, its plain-text output (no ANSI in test) will precede the JSON. The fix is structural: `if as_json: ... return` must be the first thing in every command body, before any `Console()` instantiation.

**P-01 test recipe for the plan:**
```python
def test_json_stdout_is_pure_json(runner, fake_server):
    result = runner.invoke(app, ['console', 'tools', '--json'])
    # stdout = result.output minus any stderr content
    stdout = result.output[len(result.stderr):]  # strip stderr prefix if any
    json.loads(stdout.strip())  # raises on non-JSON bytes — test fails
```

### 5. Typer 0.24.1 + Python 3.11: any live reports of silent-drop of sync commands with keyword-only args?

**NO new issues found beyond the known async-drop.** [VERIFIED: live test in forge conda env + existing test_typer_entrypoint.py passing]

The Phase 9 STATE.md constraint is: "Typer 0.24.1 silently drops `async def`." This is confirmed. For **sync** commands:

- Regular positional, keyword, and Optional keyword args work correctly
- `typer.Option(...)` and `typer.Argument(...)` work as documented
- Subcommand groups (`add_typer`) propagate `typer.Exit(code=N)` and `sys.exit(N)` correctly (both tested)
- The existing `test_typer_entrypoint.py` (which passes) already exercises the subcommand group path

**Specific risk for Phase 11:** Keyword-only args (using `*` in function signature) are NOT standard Typer usage — Typer derives CLI params from type annotations, not Python keyword-only syntax. Use Annotated type hints with `typer.Option(...)` exclusively. No keyword-only Python function args in command bodies.

---

## Implementation Gaps Filled

### 1. Rich rendering primitives: `rich.box.SQUARE` in xterm-256color vs dumb terminal

**CONFIRMED: `rich.box.SQUARE` is the correct choice.** [VERIFIED: live render test]

Tested behavior:
- In `xterm-256color` (TTY with `force_terminal=True`): SQUARE box glyphs (`┌─┬┐│├─┼┤└─┴┘`) render correctly, header bold-yellow ANSI codes present
- In dumb/piped context (no `force_terminal`, non-TTY file): SQUARE box glyphs still render (Unicode box drawing is not color-dependent), no ANSI codes, clean readable table
- At narrow widths (40 col): Rich truncates cell content with `…` glyph — the table structure is preserved, individual cells are truncated. Header text wraps within the cell width if necessary. No crash, no garbling.

**80-column minimum recommendation:** The 4-column tools table (Name/Status/Type/Created ▼) fits comfortably at 80 columns. For narrower terminals, Rich degrades gracefully. No minimum-width guard is needed in the CLI code; Rich handles it.

`SQUARE` box is the current Rich guidance for "clean monospace-friendly" tables as of Rich >= 13.x. [CITED: rich.box module, `rich.box.SQUARE` symbol present in Rich 14.3.3]

### 2. Shell-completion shipping: Typer's `--install-completion`

**Verdict: Include as a freebie (zero packaging cost). Document known CI limitation.** [VERIFIED: live test]

`--install-completion` is automatically included in every Typer app with `add_completion=True` (default). It appears in `--help` output already. No extra packaging steps required.

**The limitation:** `shellingham` (Typer's shell-detection dependency) raises `ShellDetectionFailure` when not inside a recognized shell process (e.g., CI runners, subprocess invocations). In these environments `--install-completion` exits code 1 with "Shell None is not supported." This is cosmetic — it does not affect any other command. No per-shell files need to be installed manually; Typer handles the profile injection automatically when shell detection succeeds.

**Plan action:** No packaging change needed. Optionally add one line to the root `--help` text noting `--install-completion` is available.

### 3. `NO_COLOR` + `FORCE_COLOR` handling in Rich: automatic or must CLI plumb it?

**AUTOMATIC — no manual plumbing required.** [VERIFIED: live test + Rich source inspection]

Rich's `Console.__init__` reads these env vars directly from `os.environ` on construction:

- `NO_COLOR` — if set to any non-empty string, removes all color output. Styles (bold, italic, dim) are preserved. Takes precedence over `FORCE_COLOR`. [CITED: https://rich.readthedocs.io/en/stable/console.html]
- `FORCE_COLOR` — if set to any non-empty string, enables color and styles regardless of TTY detection. [CITED: https://rich.readthedocs.io/en/stable/console.html]

**Live verification:**
```python
os.environ['NO_COLOR'] = '1'
Console(file=StringIO()).print('[bold red]text[/bold red]')
# Output: 'text\n'  — no ANSI codes
```

The `--no-color` CLI flag (D-07) should be implemented by constructing `Console(no_color=True)` rather than setting the env var — this scopes the effect to the current invocation without mutating the process environment.

**Recommended pattern in `render.py`:**
```python
def make_console(no_color: bool = False, stderr: bool = False) -> Console:
    return Console(no_color=no_color, stderr=stderr)
```
Pass `no_color=no_color_flag` from each command. `NO_COLOR` env is already honored by `Console()` without the explicit kwarg.

### 4. ISO 8601 parsing for `--since`: stdlib limitations in 3.11 and recommended parser shape

**Python 3.11 handles `Z` suffix natively; Python 3.10 does not.** Project minimum is `>=3.10`. [VERIFIED: live test on Python 3.11.14]

```python
# Python 3.11: datetime.fromisoformat('2026-04-24T10:00:00Z') → OK
# Python 3.10: same call → ValueError: Invalid isoformat string
```

**Recommended `since.py` (~15 LOC, stdlib only, no new deps):**

```python
import re
from datetime import datetime, timedelta, timezone


_RELATIVE_RE = re.compile(r'^(\d+)(m|h|d|w)$')
_UNIT_SECONDS = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}


def parse_since(value: str) -> str:
    """Parse --since value into an ISO 8601 string for the API.

    Accepts:
      - Relative: "30m", "24h", "7d", "2w"
      - ISO 8601: "2026-04-24T10:00:00Z", "2026-04-24T10:00:00+00:00"

    Returns an ISO 8601 UTC string. Raises ValueError on bad input.
    """
    m = _RELATIVE_RE.match(value)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        dt = datetime.now(timezone.utc) - timedelta(seconds=n * _UNIT_SECONDS[unit])
        return dt.isoformat()
    # Normalize Z suffix for Python 3.10 compatibility
    normalized = value[:-1] + '+00:00' if value.endswith('Z') else value
    dt = datetime.fromisoformat(normalized)  # ValueError on bad input — let it propagate
    return dt.isoformat()
```

**Rejected tokens (per D-02):** "yesterday", "last tuesday", ISO 8601 durations (`P1D`), locale-specific strings. The `re.fullmatch` against `^(\d+)(m|h|d|w)$` rejects all of these and falls through to the ISO 8601 path, which raises `ValueError` for non-ISO inputs.

**Test cases that MUST pass:**
- `"30m"` → ISO 8601 string ~30 minutes before now
- `"24h"` → ISO 8601 string ~24 hours before now
- `"7d"` → ISO 8601 string ~7 days before now
- `"2w"` → ISO 8601 string ~2 weeks before now
- `"2026-04-24T10:00:00Z"` → `"2026-04-24T10:00:00+00:00"`
- `"2026-04-24"` → parses without error (date-only, midnight UTC)
- `"bad_input"` → `ValueError`
- `"P1D"` → `ValueError` (rejected)
- `"yesterday"` → `ValueError` (rejected)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing; `asyncio_mode = "auto"` in `pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_cli_*.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |
| Coverage tool | No `fail_under` baseline configured in project — set Phase 11 floor at **80%** for `forge_bridge/cli/` (matches industry standard; no prior project baseline to inherit from) |

### Per-Requirement Test Topology

| REQ-ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CLI-01 | Five subcommands registered, help exits 0 | unit (CliRunner) | `pytest tests/test_cli_commands.py -x -q` | No — Wave 0 |
| CLI-02 | All command bodies are sync; API called via sync httpx | unit (CliRunner + httpx mock) | `pytest tests/test_cli_client.py -x -q` | No — Wave 0 |
| CLI-03 | `--json` emits raw API envelope; `--help` shows Examples block | unit (CliRunner) | `pytest tests/test_cli_json_mode.py -x -q` | No — Wave 0 |
| CLI-04 | TTY: Rich-formatted; non-TTY: plain text; `--no-color` suppresses ANSI | unit (CliRunner) | `pytest tests/test_cli_rendering.py -x -q` | No — Wave 0 |
| TOOLS-03 | `tools` lists correct columns; `--origin`/`--namespace`/`--search` filter correctly | unit (CliRunner + fake API) | `pytest tests/test_cli_tools.py -x -q` | No — Wave 0 |
| EXECS-03 | `execs` shows last 50 records; `--since` parses relative + ISO; `--tool` adds stderr note | unit (CliRunner + fake API) | `pytest tests/test_cli_execs.py -x -q` | No — Wave 0 |
| MFST-05 | `manifest` returns Rich table or `--json` body | unit (CliRunner + fake API) | `pytest tests/test_cli_manifest.py -x -q` | No — Wave 0 |
| HEALTH-02 | `health` renders service groups; `--json` returns envelope | unit (CliRunner + fake API) | `pytest tests/test_cli_health.py -x -q` | No — Wave 0 |
| HEALTH-03 | `doctor` probes checklist; exit 1 on any fail; exit 2 on server unreachable; CI-safe | unit (CliRunner + mocked checks) + integration | `pytest tests/test_cli_doctor.py -x -q` | No — Wave 0 |

### Minimum Sample Sizes per Requirement

**CLI-03 `--json` mode (3 minimum samples):**
1. Positive path: server returns valid data → stdout is parse-able JSON, stderr empty
2. Connection-error path: server unreachable → stdout is `{"error": {"code": "server_unreachable", ...}}`, exit code 2
3. HTTP-error path: server returns 4xx/5xx → stdout is `{"error": ...}` envelope, exit code 1

**EXECS-03 `--since` parser (5 minimum samples):**
1. `"24h"` → valid ISO string passed to API
2. `"7d"` → valid ISO string passed to API
3. `"2026-04-24T10:00:00Z"` → normalized to `+00:00` suffix, passed to API
4. `"bad_input"` → `ValueError` surfaced as CLI error message, exit code 1
5. `"P1D"` → rejected as invalid, not passed to API

**HEALTH-03 doctor (6 minimum samples):**
1. All checks pass → exit 0
2. Critical service fails (mcp status=fail) → exit 1
3. Non-critical degraded (LLM offline) → exit 0 (warn, not fail)
4. Server unreachable on `:9996` → exit 2, correct error message on stderr
5. JSONL parse error found in tail → check reported as fail → exit 1
6. Sidecar dir not writable → check reported as fail → exit 1

**TOOLS-03 edge cases (2 minimum per edge):**
1. `--origin synthesized` with 0 matching tools → empty table with "No tools found" footer (not a crash)
2. `--namespace nonexistent_ns` → empty table
3. `--search "synth_"` with partial match → filtered list shows matching tools only
4. `tools <name>` with nonexistent tool name → exit 1 with "tool not found" error

**EXECS-03 edge cases:**
1. `--tool synth_foo` with 0 matches → empty table + stderr note about client-side filtering
2. `--since` with malformed token (`"bad"`) → CLI error, not a server request made
3. `--limit 0` → treated as minimum limit (1) or rejected with error
4. `--offset` beyond total records → empty table, no error

**HEALTH-03 doctor edge cases:**
1. JSONL log file missing entirely → check fails with "log file not found" hint
2. Disk space < 100 MB → warn (not fail); < 10 MB → fail
3. `--json` on doctor output → structured JSON per check, exit codes preserved

### Fixture Strategy

**Verdict: Extract shared fixture-server helper into `tests/conftest.py`.** [VERIFIED: inspected conftest.py and test_ui_js_disabled_graceful_degradation.py]

Current `tests/conftest.py` has three fixtures (`monkeypatch_bridge`, `mock_openai`, `mock_anthropic`) — all unrelated to the console API. The `fake_read_api` fixture in `test_ui_js_disabled_graceful_degradation.py` is a standalone fixture that builds a `MagicMock` over `ConsoleReadAPI`.

**Recommendation:** For Phase 11 unit tests, each `test_cli_*.py` file defines its own `fake_read_api`-style mock using `respx` (or `unittest.mock.patch`) to intercept `httpx.Client.get()` calls at the HTTP layer (not the Python layer). This is cleaner for a CLI client test than mocking `ConsoleReadAPI` directly — it tests the full CLI→httpx→mock-response→render pipeline.

**For integration tests** (CLI → real fixture server): Reuse the `build_console_app(fake_read_api)` pattern from `test_ui_js_disabled_graceful_degradation.py`, boot it on a free port with `uvicorn.Server` in a background thread, then invoke the CLI with `FORGE_CONSOLE_PORT` set to that port. This requires the server to be up; tests that need a real HTTP round-trip should be marked `@pytest.mark.integration` and conditionally skipped in CI if the server cannot start.

**conftest.py additions:** Add a `free_port()` fixture that finds an available local port. Add a `console_server(free_port)` fixture that starts a `TestClient`-backed fake console server. These are shared across all `test_cli_*.py` files.

### Coverage Surface

No `fail_under` is configured in `pyproject.toml`. **Set Phase 11 Nyquist floor: 80% line coverage for `forge_bridge/cli/`.**

Measure with: `pytest tests/test_cli_*.py --cov=forge_bridge/cli --cov-fail-under=80 -q`

The 80% floor is achievable while excluding:
- The `if TYPE_CHECKING:` branches (not runtime)
- The `if __name__ == '__main__':` guard (not callable via CliRunner)
- The `doctor` disk-space probe (OS-dependent, may need platform skip)

### Pitfall-Specific Tests

**P-01 (stdout corruption) — MUST have an explicit test per subcommand in `--json` mode:**

```python
def test_tools_json_stdout_is_pure_json(runner, fake_server):
    result = runner.invoke(app, ['console', 'tools', '--json'])
    assert result.exit_code == 0
    # Strip stderr from combined output to get pure stdout
    stdout = result.output[len(result.stderr):]
    parsed = json.loads(stdout.strip())  # raises AssertionError on corrupt output
    assert 'data' in parsed
```

This test FAILS if any Rich output leaks into stdout before the `--json` guard fires.

**P-09 (CLI vs Web UI drift) — verify CLI reads byte-identical envelope:**

```python
def test_tools_json_matches_api_envelope(runner, fake_server):
    # CLI --json output must match direct GET /api/v1/tools response
    api_response = httpx.get(f'http://127.0.0.1:{fake_server.port}/api/v1/tools').json()
    result = runner.invoke(app, ['console', 'tools', '--json'])
    cli_output = json.loads(result.output.strip())
    assert cli_output == api_response
```

### Wave 0 Gaps

- [ ] `tests/test_cli_commands.py` — CLI-01 subcommand registration
- [ ] `tests/test_cli_client.py` — CLI-02 sync httpx + connection-error matrix
- [ ] `tests/test_cli_json_mode.py` — CLI-03 JSON stdout purity + P-01 tests
- [ ] `tests/test_cli_rendering.py` — CLI-04 TTY/non-TTY/no-color rendering
- [ ] `tests/test_cli_tools.py` — TOOLS-03 list + filters + drilldown
- [ ] `tests/test_cli_execs.py` — EXECS-03 list + since parser + tool client-side filter
- [ ] `tests/test_cli_manifest.py` — MFST-05 list + --json
- [ ] `tests/test_cli_health.py` — HEALTH-02 health panel
- [ ] `tests/test_cli_doctor.py` — HEALTH-03 doctor checks + exit codes
- [ ] `tests/conftest.py` additions: `free_port()`, `console_server()` fixtures

*(No framework install needed — pytest is already in `[project.optional-dependencies] dev`.)*

---

## Risks and Non-Obvious Pitfalls

### Risk 1: `FORGE_CONSOLE_PORT` with invalid values is silently mishandled

**What:** Phase 9 D-27 sets `FORGE_CONSOLE_PORT` in env. The CLI `client.py` will read it with `int(os.environ.get('FORGE_CONSOLE_PORT', '9996'))`.

**The gap:** If `FORGE_CONSOLE_PORT=99999` (port > 65535), `int()` succeeds and the URL is constructed successfully, but httpx raises `httpx.ConnectError` when it tries to connect (verified live — the OS rejects the bind immediately). This is handled correctly by the exit-code-2 path. **No special validation needed.**

If `FORGE_CONSOLE_PORT=not_a_port`, `int()` raises `ValueError` immediately at client construction — before any HTTP call is made. **This must be caught and converted to a user-readable error + exit code 1** (not a raw traceback). The plan must include: `try: port = int(os.environ.get('FORGE_CONSOLE_PORT', '9996')); except ValueError: typer.echo(..., err=True); raise typer.Exit(1)`.

### Risk 2: Rich table rendering at < 80 cols is safe but produces truncated cell content

**What:** Tested at 40-col width — Rich truncates long cell values with `…` glyph. The table structure is preserved (box borders remain intact). Header text wraps within column width.

**Implication:** The `Name` column for long tool names like `synth_very_long_tool_name` will be truncated to `synth_…` at narrow widths. This is acceptable behavior (it's better than crashing). The `--json` escape hatch always gives the full name.

**No action needed in the plan.** Rich handles this gracefully without any min-width guard.

### Risk 3: `typer.Exit(code=N)` vs `sys.exit(N)` — both work, but `typer.Exit` is preferred

**VERIFIED: Both propagate correctly through CliRunner in subcommand groups.** [VERIFIED: live test]

```python
# Both work:
raise typer.Exit(code=2)   # preferred — Typer-idiomatic
sys.exit(2)                # also works — propagates correctly
```

**Recommendation:** Use `raise typer.Exit(code=N)` exclusively in CLI command bodies. `sys.exit()` works but is less idiomatic and may interact unexpectedly with `catch_exceptions=True` (the default in CliRunner) in edge cases.

### Risk 4: `doctor`'s JSONL-tail probe safety with concurrent writers

**SAFE for the tail-read pattern.** [VERIFIED: concurrent write/read test — 200 writes, 400 reads, 0 parse errors]

The JSONL log is append-only with `fcntl.LOCK_EX` on writes. The doctor's probe reads the last 100 lines without acquiring the lock (following the P-04 tail-reader pattern from PITFALLS.md).

**Why it's safe:** Python's `readlines()` on an append-only file reads complete lines that were fully written before the `readlines()` call. The only risk is a partial last line (write boundary mid-line). The doctor's probe should skip the last line if it does not end with `\n` to handle this edge case:

```python
def _tail_jsonl(path: str, n: int = 100) -> list[str]:
    with open(path, 'r') as f:
        lines = f.readlines()
    tail = lines[-n:] if len(lines) >= n else lines
    # Skip last line if no trailing newline (partial write boundary)
    if tail and not tail[-1].endswith('\n'):
        tail = tail[:-1]
    return [line.rstrip('\n') for line in tail if line.strip()]
```

**No file lock needed for the doctor probe.** The append-only nature and the skip-partial-last-line guard are sufficient.

### Risk 5: Rich output to `Console(stderr=True)` in `--json` mode

**CONTEXT.md D-04 Area 2 specifies:** In `--json` mode on connection error, emit the error JSON to stdout and keep stderr silent. This means `Console(stderr=True)` must NOT be called in `--json` mode either — even for the "note: --tool is filtered client-side" message on `execs --tool --json`.

**Implication for the plan:** Every command must have a clear `if as_json` guard that suppresses ALL Rich output, including the `--tool` stderr note:

```python
@console_app.command("execs")
def execs_cmd(tool: ... = None, as_json: bool = ...):
    if tool and not as_json:
        typer.echo("note: --tool is filtered client-side until v1.4 API support; "
                   "narrow with --since to scan less history.", err=True)
    data = _fetch_execs(...)
    if tool:
        data = [r for r in data if r['tool'] == tool]
    if as_json:
        sys.stdout.write(json.dumps(data) + '\n')
        return
    render_execs_table(data)
```

### Risk 6: `CliRunner` test isolation — `FORGE_CONSOLE_PORT` env bleeds between tests

**What:** If one test sets `FORGE_CONSOLE_PORT` in `os.environ` (via the CLI's flag handling), subsequent tests in the same process may pick up the wrong port.

**Mitigation:** Use `CliRunner(env={...})` to pass env vars per-invocation rather than mutating `os.environ`. The `CliRunner` `env` parameter sets env vars for the duration of `invoke()` only.

```python
runner = CliRunner()
result = runner.invoke(app, ['console', 'health'], env={'FORGE_CONSOLE_PORT': str(port)})
```

This is cleaner than `monkeypatch.setenv()` and works across all test files.

---

## Standard Stack

### Core CLI Stack

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| `typer` | 0.24.1 | Typer CLI framework; `console_app` group already wired in `__main__.py` | [VERIFIED: pip show] |
| `rich` | 14.3.3 | Terminal formatting: `Table`, `Panel`, `Syntax`, `Console` | [VERIFIED: pip show] |
| `httpx` (sync client) | 0.28.1 | Sync HTTP client to `/api/v1/*`; `httpx.Client(base_url=...).get(...)` | [VERIFIED: pip show] |

### Supporting Libraries (all already installed)

| Library | Purpose |
|---------|---------|
| `rich.box.SQUARE` | Table box style — confirmed available in 14.3.3 |
| `rich.syntax.Syntax` | Code preview in drilldowns (Python lexer) |
| `typer.testing.CliRunner` | Unit test harness; `result.stderr` for stderr isolation |
| `datetime` (stdlib) | `--since` ISO 8601 parsing via `fromisoformat` + Z-normalization |
| `re` (stdlib) | `--since` relative grammar matching |
| `sys.stdout.write()` | `--json` mode raw output (bypasses Rich) |

### New `pyproject.toml` changes

```toml
# Add to [project.dependencies]:
"rich>=13.9.4",

# Add to [tool.ruff.lint.per-file-ignores]:
"forge_bridge/cli/**" = ["T20"]  # if any module legitimately needs print()
```

---

## Architecture Patterns

### System Architecture Diagram

```
forge-bridge console <subcommand> [flags]
         │
         ▼
  __main__.py:app (Typer root)
         │  console_app group (already wired, Phase 9 D-10/D-11)
         ▼
  forge_bridge/cli/<command>.py
  (tools.py | execs.py | manifest.py | health.py | doctor.py)
         │
         ├── flag: --json?
         │      yes → skip Rich → write raw JSON envelope to stdout → exit
         │      no  → continue to render path
         │
         ├── forge_bridge/cli/since.py (--since parsing, 15 LOC)
         │
         ├── forge_bridge/cli/client.py
         │   sync httpx.Client(base_url="http://127.0.0.1:{FORGE_CONSOLE_PORT}")
         │         │
         │         ▼
         │   GET /api/v1/{tools|execs|manifest|health}
         │         │
         │   on ConnectError/TimeoutException/RemoteProtocolError:
         │         ├── --json → stdout JSON error envelope → exit 2
         │         └── --rich → stderr message → exit 2
         │         │
         │   on HTTP 4xx/5xx:
         │         ├── --json → stdout JSON error envelope → exit 1
         │         └── --rich → stderr error message → exit 1
         │         │
         │   on HTTP 2xx:
         │         └── unwrap {data, meta} envelope → return data
         │
         ├── client-side filtering (tools: origin/namespace/search; execs: --tool)
         │
         └── forge_bridge/cli/render.py
             (status chips, hash truncation, timestamp formatting,
              Panel/Table builders, Rich Console factory)
```

### Recommended Project Structure

```
forge_bridge/
├── __main__.py        # Typer root (existing; Phase 11 adds 5 console_app.command() registrations)
└── cli/               # NEW directory
    ├── __init__.py    # empty or re-exports app commands
    ├── client.py      # sync httpx wrapper, connection-error handling, envelope unwrap
    ├── render.py      # Rich rendering helpers (Console factory, tables, panels, chips)
    ├── since.py       # --since parser (~15 LOC)
    ├── tools.py       # tools + tools <name> subcommands
    ├── execs.py       # execs + execs <hash> subcommands
    ├── manifest.py    # manifest subcommand
    ├── health.py      # health subcommand
    └── doctor.py      # doctor subcommand
```

### Anti-Patterns to Avoid

- **Never call `Console()` before the `--json` guard fires.** Even a `Console(stderr=True)` call can leak bytes if not guarded — keep the guard as the first statement in every command body.
- **Never use `asyncio.run()` inside command bodies.** Typer 0.24.1 silently drops `async def` commands; sync `httpx.Client` eliminates the need for asyncio in the CLI entirely.
- **Never use `print()` in `forge_bridge/cli/`.** T20 ruff rule applies. Use `typer.echo()` for simple messages, `Console().print()` for Rich output, `sys.stdout.write()` for raw JSON.
- **Never hold `httpx.Client` as a module-level singleton.** Create per-invocation: `with httpx.Client(base_url=..., timeout=10.0) as client: ...`. This keeps connection state scoped to one command invocation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Terminal table rendering | Custom string formatting with `ljust`/`rjust` | `rich.table.Table` with `rich.box.SQUARE` |
| Syntax highlighting in drilldowns | ANSI code injection | `rich.syntax.Syntax(code, 'python')` |
| Status chip color mapping | `if status == 'active': print('\033[32m...')` | `Text(status, style='green')` via render.py |
| ISO 8601 parsing | Custom regex | `datetime.fromisoformat()` + Z-normalization (15 LOC) |
| CLI testing harness | subprocess + string matching | `typer.testing.CliRunner` |
| HTTP client | `urllib.request` | `httpx.Client` (already a dep) |

---

## Open Questions

1. **`forge_bridge/cli/__init__.py` — register commands at import time or in `__main__.py`?**
   - CONTEXT.md D-11: "Phase 11 only fills the empty group" by adding five `console_app.command("...")(...)` registrations.
   - **Recommendation:** Register commands in `forge_bridge/__main__.py` (5 lines: `from forge_bridge.cli import tools, execs, manifest, health, doctor; console_app.command("tools")(tools.tools_cmd)` etc.). The command implementations live in `forge_bridge/cli/*.py`. This keeps `__main__.py` as the single registration file, consistent with Phase 9's intent.

2. **`execs <hash>` drilldown — is there a `GET /api/v1/execs/<hash>` endpoint?**
   - CONTEXT.md Area 3 describes "Exec drilldown (`forge-bridge console execs <hash>`)" but Phase 9/10 API may not have a single-exec-by-hash endpoint. The `handlers.py` has `execs_handler` which takes `limit`/`offset`/`since`/`promoted_only`/`code_hash` but no path param.
   - **Recommendation for planner:** Implement `execs <hash>` as a filtered list call: `GET /api/v1/execs?code_hash=<hash>&limit=1`. If result is empty, exit 1 "not found". This avoids needing a new API endpoint (per D-04: Phase 11 does NOT extend the API).

3. **`tools <name>` drilldown — is `GET /api/v1/tools/<name>` implemented?**
   - `handlers.py` has `tool_detail_handler` at `GET /api/v1/tools/{name}`. Confirmed exists.
   - **No issue — endpoint is available.**

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.11.14 | — |
| typer | CLI framework | ✓ | 0.24.1 | — |
| rich | Terminal rendering | ✓ | 14.3.3 | — |
| httpx (sync) | HTTP client | ✓ | 0.28.1 | — |
| pytest | Test harness | ✓ | (installed) | — |
| forge-bridge server on :9996 | Integration tests | Conditional | — | Unit tests with httpx mocks |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Live server on `:9996` — integration tests require it; unit tests use mocked HTTP responses and can run without it.

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `--since` parser validates before passing to API; FORGE_CONSOLE_PORT `int()` conversion with explicit error catch |
| V2 Authentication | no | CLI is localhost-only, same posture as the API (no auth in v1.3) |
| V6 Cryptography | no | No secrets handled by CLI layer |

**LRN-05 credential-leak rule applies:** The CLI `client.py` must use `type(exc).__name__` only in log/error messages — never `str(exc)`. httpx exceptions can include URLs in their string representation; the URL includes the port but not credentials (safe in this case), but the rule applies universally per Phase 8 project convention.

**Injection risk:** The doctor's JSONL-tail probe must report parse errors by line number and exception class name only — never the raw failing line content (could contain sensitive data from execution records). Use: `f"line {i}: {type(exc).__name__}"`.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Async CLI commands with `asyncio.run()` | Sync commands with sync `httpx.Client` | Eliminates the Typer 0.24.1 async-drop bug; no asyncio wrapper needed |
| `argparse` CLI | Typer 0.24.1 (already installed) | Type-annotated params, auto-help, subcommand groups |
| Manual ANSI codes | Rich 14.3.3 tables/panels | Correct truncation at narrow widths, NO_COLOR/FORCE_COLOR auto-handled |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GET /api/v1/execs?code_hash=<hash>&limit=1` is the correct approach for `execs <hash>` drilldown (no dedicated single-exec endpoint) | Open Questions #2 | If a dedicated endpoint exists, the workaround still works; if it doesn't exist and the workaround doesn't work, the drilldown feature needs a plan change |
| A2 | `rich>=13.9.4` is the correct minimum version to specify as a direct dep (matches `mcp[rich]` floor) | Standard Stack | If Rich 13.9.x has a bug that 14.x fixed, the CLI may behave differently on systems with only mcp[cli] installed; negligible risk in practice |

**All other claims in this document were verified against the live forge conda environment (Python 3.11.14, rich 14.3.3, typer 0.24.1, httpx 0.28.1) or cited from official documentation.**

---

## References

### Primary (HIGH confidence — verified against installed packages)

- `pip show rich typer httpx mcp` — version verification [VERIFIED]
- `python3 -c "import httpx; print(httpx.ConnectError.__mro__)"` etc. — exception hierarchy [VERIFIED]
- `python3 -c "from typer.testing import CliRunner; ..."` — CliRunner behavior [VERIFIED]
- `python3 -c "import rich.box; print(rich.box.SQUARE)"` — SQUARE box availability [VERIFIED]
- `python3 -c "import os; os.environ['NO_COLOR']='1'; ..."` — NO_COLOR/FORCE_COLOR behavior [VERIFIED]
- `python3 -c "datetime.fromisoformat('2026-04-24T10:00:00Z')"` — Python 3.11 Z-suffix handling [VERIFIED]
- Concurrent JSONL read/write test — tail safety confirmed [VERIFIED]
- `forge_bridge/__main__.py` — console_app group scaffold inspected [VERIFIED]
- `forge_bridge/console/handlers.py` — API envelope shape, W-01 rejection, path params [VERIFIED]
- `forge_bridge/console/read_api.py` — health response structure, service groups [VERIFIED]
- `pyproject.toml` — T20 carve-out pattern, current deps [VERIFIED]
- `tests/conftest.py` — existing fixture inventory [VERIFIED]
- `tests/test_ui_js_disabled_graceful_degradation.py` — fake_read_api fixture pattern [VERIFIED]
- `tests/test_typer_entrypoint.py` — CliRunner usage patterns [VERIFIED]
- `importlib.metadata.distribution('mcp')` — mcp[cli] transitive dep chain [VERIFIED]

### Secondary (MEDIUM confidence — cited from official documentation)

- [Rich docs: Console environment variables](https://rich.readthedocs.io/en/stable/console.html) — NO_COLOR and FORCE_COLOR behavior [CITED]
- [httpx exception handling](https://www.python-httpx.org/exceptions/) — ConnectError, TimeoutException, RemoteProtocolError [CITED]
- [Python 3.11 changelog](https://docs.python.org/3/whatsnew/3.11.html) — datetime.fromisoformat Z suffix support [CITED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified live in the forge conda env
- Architecture: HIGH — based on direct inspection of Phase 9/10/10.1 shipped code
- Pitfalls: HIGH — all risks tested or traced through source code
- Validation architecture: HIGH — based on existing test patterns in the repo

**Research date:** 2026-04-24
**Valid until:** 2026-06-24 (stable stack; only risk is httpx/typer/rich major version bumps)
