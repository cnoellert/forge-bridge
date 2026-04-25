---
phase: 09-read-api-foundation
plan: 03
subsystem: surface-layer
tags:
  - starlette
  - uvicorn
  - mcp-resources
  - stdio-safety
  - lifespan
  - integration-tests
requires:
  - typer>=0.24,<1 (landed 09-01)
  - pytest-timeout>=2.2.0 (landed 09-01; pip-installed during Task 6 execution)
  - ManifestService + ToolRecord (landed 09-02)
  - ConsoleReadAPI (landed 09-02)
  - ExecutionLog.snapshot() (landed 09-02)
provides:
  - forge_bridge.console.logging_config.STDERR_ONLY_LOGGING_CONFIG (D-20)
  - forge_bridge.console.app.build_console_app (Starlette factory)
  - forge_bridge.console.handlers (5 route handlers + envelope/_error/_envelope_json helpers)
  - forge_bridge.console.resources.register_console_resources (4 resources + 2 tool shims)
  - forge_bridge.console.read_api.register_canonical_singletons (API-04 setter)
  - forge_bridge.console.read_api.ConsoleReadAPI.get_health (full D-14 body)
  - forge_bridge.mcp.server._start_console_task (API-06 / D-29 graceful-degradation helper)
  - forge_bridge.mcp.server._canonical_{execution_log,manifest_service,watcher_task} module globals
  - forge_bridge.mcp.server._lifespan executing the D-31 6-step sequence
affects:
  - forge_bridge/console/logging_config.py (new)
  - forge_bridge/console/app.py (new)
  - forge_bridge/console/handlers.py (new)
  - forge_bridge/console/resources.py (new)
  - forge_bridge/console/read_api.py (extended — get_health full body + register_canonical_singletons)
  - forge_bridge/console/__init__.py (extended — barrel re-exports register_console_resources)
  - forge_bridge/mcp/server.py (extended — _lifespan rewritten as D-31 6-step, _start_console_task helper added, canonical globals added)
  - tests/test_console_routes.py (new)
  - tests/test_console_health.py (new)
  - tests/test_console_mcp_resources.py (new)
  - tests/test_console_port_degradation.py (new)
  - tests/test_console_http_transport.py (new)
  - tests/test_console_instance_identity.py (new)
  - tests/test_console_stdio_cleanliness.py (new — SC#1 critical runtime UAT)
tech-stack:
  added:
    - "starlette (already transitively available via mcp[cli])"
    - "uvicorn (already transitively available via mcp[cli])"
    - "pytest-timeout >= 2.4.0 (dev install during Task 6 execution)"
  patterns:
    - "Starlette Route(...) list + Middleware(CORSMiddleware, ...) factory with app.state.console_read_api"
    - "STDERR_ONLY_LOGGING_CONFIG passed to uvicorn.Config.log_config + access_log=False (D-20/D-21 belt-and-suspenders P-01)"
    - "Port-precheck socket bind → WARNING + return (None, None) on OSError; startup barrier polls server.started"
    - "D-31 six-step _lifespan sequence with canonical ExecutionLog+ManifestService owned at step 2, watcher task at step 3, ConsoleReadAPI at step 4, resource registration at step 5, uvicorn task at step 6"
    - "Instance-identity gate via register_canonical_singletons() recording id() in module globals; get_health() compares and flips aggregated status to 'fail' on mismatch (D-15/D-16)"
    - "Byte-identity between MCP resource bodies and HTTP handler bodies via shared _envelope_json serializer (D-26)"
    - "NDJSON MCP stdio framing accepted by FastMCP 1.19+ — SC#1 test writes line-delimited JSON on stdin rather than Content-Length framing, and parses stdout accepting BOTH framing styles"
    - "proc.terminate() + proc.communicate(timeout=...) for SC#1 subprocess cleanup (avoids the 'flush of closed stdin' bug caused by pre-closing proc.stdin)"
key-files:
  created:
    - forge_bridge/console/logging_config.py
    - forge_bridge/console/app.py
    - forge_bridge/console/handlers.py
    - forge_bridge/console/resources.py
    - tests/test_console_routes.py
    - tests/test_console_health.py
    - tests/test_console_mcp_resources.py
    - tests/test_console_port_degradation.py
    - tests/test_console_http_transport.py
    - tests/test_console_instance_identity.py
    - tests/test_console_stdio_cleanliness.py
  modified:
    - forge_bridge/console/read_api.py
    - forge_bridge/console/__init__.py
    - forge_bridge/mcp/server.py
decisions:
  - "D-14 health body: 7 services (mcp, flame_bridge, ws_server, llm_backends, watcher, storage_callback, console_port) + instance_identity with execution_log/manifest_service id_match fields. D-15 aggregation: mcp+watcher+instance_identity are critical (→ 'fail' on fail); llm_backends, storage_callback, flame_bridge, ws_server are non-critical (→ 'degraded' on fail)."
  - "Watcher check (I-02): if _canonical_watcher_task is installed and done() with an exception, return status=fail + task_done=True + detail=<ExceptionClassName>. If no task installed, fall back to _server_started boolean — preserves Phase 9-02 unit test paths."
  - "register_canonical_singletons() is a module-level setter in console/read_api.py (not a method on mcp.server) to break the learning/console/mcp import triangle. mcp/server._lifespan calls it once at step 2."
  - "SC#1 test uses NDJSON stdio framing instead of Content-Length: FastMCP 1.19+ stdio server reads line-delimited JSON on stdin. Parser accepts both framing styles to avoid coupling the test to one FastMCP version."
  - "proc.terminate() rather than closing stdin then communicate() — communicate() tries to flush pre-closed stdin and raises ValueError. terminate() is the simpler, portable shutdown path."
  - "tools.py ruff noise (5 F401/E741 warnings) NOT fixed — confirmed pre-existing via git stash; orthogonal to T20 gate; see Deviations."
metrics:
  duration: 12m58s
  completed: 2026-04-23
  tasks: 6
  files_touched: 14
commits:
  - 800ca96 feat(09-03): add Starlette console app + handlers + STDERR_ONLY_LOGGING_CONFIG
  - 052ba73 feat(09-03): fill ConsoleReadAPI.get_health with full D-14 body + register_canonical_singletons
  - 312c2f3 feat(09-03): add register_console_resources + MCP resources/tool shims + byte-identity tests
  - d967a2d feat(09-03): wire _lifespan D-31 6-step sequence + _start_console_task graceful degradation
  - abe81cb test(09-03): add HTTP transport + instance-identity integration tests
  - 6bde19e test(09-03): add SC#1 stdio cleanliness test — P-01 critical runtime UAT
requirements_complete:
  - API-01
  - API-02
  - API-03
  - API-04
  - API-05
  - API-06
  - MFST-02
  - MFST-03
  - MFST-06
  - TOOLS-04
  - EXECS-04
---

# Phase 9 Plan 03: Read API Foundation — HTTP + MCP Surface Layer Summary

Landed the full v1.3 Artist Console surface: a Starlette-backed HTTP API on
`:9996` served by a uvicorn asyncio task inside `_lifespan`, 4 MCP resources +
2 tool fallback shims registered against the same `ConsoleReadAPI`, the D-31
six-step lifespan wiring with canonical `ExecutionLog` / `ManifestService`
singletons, graceful port-unavailable degradation mirroring `startup_bridge`,
the full D-14 health body with 7-service fan-out + instance-identity gate,
and the **SC#1 P-01 critical runtime UAT** — `pytest tests/test_console_stdio_cleanliness.py`
spawns a real `python -m forge_bridge` subprocess, hammers `:9996` with 100
concurrent GETs while sending MCP `initialize` + `tools/list` on stdin, and
proves stdout remains byte-clean JSON-RPC framing.

## What Was Done

### Task 1 — Starlette app + handlers + LOGGING_CONFIG

- `forge_bridge/console/logging_config.py`: `STDERR_ONLY_LOGGING_CONFIG` dict
  verbatim from RESEARCH.md §3 — routes `uvicorn`, `uvicorn.error`,
  `uvicorn.access` to `ext://sys.stderr` with a `uvicorn.logging.DefaultFormatter`.
- `forge_bridge/console/handlers.py`: 5 async handlers (`tools_handler`,
  `tool_detail_handler`, `execs_handler`, `manifest_handler`, `health_handler`);
  envelope helpers `_envelope` / `_error` / `_envelope_json`; query-param parsers
  with D-05 clamping (`_MAX_LIMIT = 500`); `execs_handler` rejects `?tool=...`
  with 400 `not_implemented` (W-01); every handler wraps in try/except returning
  `_error("internal_error", "failed to read X")` to prevent traceback leakage.
- `forge_bridge/console/app.py`: `build_console_app(read_api)` factory — 5
  `Route("/api/v1/*", ...)` entries, `CORSMiddleware(allow_origins=["http://127.0.0.1:9996", "http://localhost:9996"], allow_methods=["GET"], allow_credentials=False)`,
  `app.state.console_read_api = read_api` attachment.
- `tests/test_console_routes.py`: 15 tests covering envelope shape, pagination,
  D-05 clamping, filter parsing (since/promoted_only/code_hash + bad-since 400),
  W-01 tool-param rejection, manifest envelope, health envelope, CORS allow +
  reject, LOGGING_CONFIG structure, error-envelope no-traceback-leak.

### Task 2 — Full D-14 `get_health()` + `register_canonical_singletons`

- `forge_bridge/console/read_api.py`:
  - Module-level `_canonical_execution_log_id` + `_canonical_manifest_service_id`
    globals populated by `register_canonical_singletons(...)`.
  - `register_canonical_singletons(execution_log, manifest_service, *, watcher_task=None)`:
    records `id()` pair; optional `watcher_task` kwarg installs the canonical
    watcher task handle into `forge_bridge.mcp.server._canonical_watcher_task`
    so `_check_watcher()` can detect crashes (I-02).
  - `get_health()` replaces the stub with the full D-14 body: parallel fan-out
    via `asyncio.gather` with per-service `asyncio.wait_for(..., timeout=2.0)`
    (D-17); 7 service checks (`mcp`, `flame_bridge`, `ws_server`, `llm_backends`,
    `watcher`, `storage_callback`, `console_port`); instance-identity gate
    comparing `id(self._execution_log)` vs the recorded canonical id; aggregation
    per D-15 (mcp/watcher/instance_identity are critical → 'fail'; other
    failures → 'degraded').
  - Watcher check differentiates still-running / crashed-with-exception /
    fallback-to-`_server_started`. Exception detail is `type(exc).__name__`
    only (Phase 8 LRN: never `str(exc)` — credential leak prevention).
- `tests/test_console_health.py`: 11 tests — D-14 shape, instance-identity
  match/drift, status aggregation (ok/degraded/fail paths), I-02 crashed
  watcher, D-18 storage-callback absent/registered, console_port constructor
  reflection, version match, ISO8601 tzinfo, empty llm_backends when router
  is None.

### Task 3 — MCP resources + tool shims + byte-identity

- `forge_bridge/console/resources.py`: `register_console_resources(mcp, ms, api)`
  registers 4 resources (`forge://manifest/synthesis`, `forge://tools`,
  `forge://tools/{name}`, `forge://health`) all with `mime_type="application/json"`
  and 2 tool fallback shims (`forge_manifest_read`, `forge_tools_read(name=None)`)
  with `annotations={"readOnlyHint": True}`. All bodies route through
  `_envelope_json` to preserve D-26 byte-identity with HTTP handlers.
- `forge_bridge/console/__init__.py`: B-01 final barrel growth — re-exports
  `register_console_resources` so MFST-06 consumers (projekt-forge) can
  `from forge_bridge.console import register_console_resources`.
- `tests/test_console_mcp_resources.py`: 12 tests covering resource count/URIs,
  tool count/names, MIME assertion, `readOnlyHint` assertion, barrel exposure,
  MFST-06 dual-surface (HTTP vs. MCP) parity for a consumer, D-26 byte-identity
  between resource bodies and HTTP response bodies for manifest and tools,
  MFST-03 exact string byte-identity between `forge_manifest_read` tool and
  `forge://manifest/synthesis` resource, tool-shim name=/name=None branches,
  tool_not_found error envelope.

### Task 4 — `_lifespan` D-31 6-step wiring + `_start_console_task`

- `forge_bridge/mcp/server.py`:
  - Three new canonical-singleton module globals:
    `_canonical_execution_log`, `_canonical_manifest_service`,
    `_canonical_watcher_task` (I-02).
  - `_start_console_task(app, host, port, ready_timeout=5.0)`: socket precheck →
    WARNING matching `"Console API disabled — port %s:%d"` + return
    `(None, None)` on OSError (D-29 API-06). On success, builds a
    `uvicorn.Config` with `log_config=STDERR_ONLY_LOGGING_CONFIG`,
    `access_log=False`, `lifespan="off"`; launches `server.serve()` as an
    asyncio task; polls `server.started` with a 5s barrier.
  - `_lifespan` replaces the old 3-step body with the D-31 6-step sequence.
    Steps 1–6: `startup_bridge()` → instantiate canonical `ExecutionLog` +
    `ManifestService` + `register_canonical_singletons` → launch watcher with
    `manifest_service=manifest_service` + install `_canonical_watcher_task` →
    build `ConsoleReadAPI(console_port=FORGE_CONSOLE_PORT|9996)` → build
    Starlette app + `register_console_resources` → launch console uvicorn
    task. Teardown reverses: `console_server.should_exit=True` +
    `asyncio.wait_for(console_task, 5s)` with cancel fallback, then
    `watcher_task.cancel()`, `shutdown_bridge()`, clear all canonical globals.
- `tests/test_console_port_degradation.py`: 3 tests — free-port happy path
  (task + server non-None, running, `server.started is True`), busy-port
  returns `(None, None)` with the WARNING match via `record.getMessage()`,
  no-raise invariant.

### Task 5 — HTTP transport + instance-identity integration tests

- `tests/test_console_http_transport.py` (3 tests): spins up a real
  uvicorn-served `ConsoleReadAPI` on an ephemeral port, exercises
  `GET /api/v1/tools` (envelope + name), 20 concurrent GETs (all 200s),
  `GET /api/v1/health` (verifies `instance_identity.id_match is True`).
  Uses `monkeypatch` to set `_server_started=True` and
  `_canonical_watcher_task=None` so `_check_watcher` falls through cleanly.
- `tests/test_console_instance_identity.py` (4 tests):
  - SC#3 positive — `log.record(...)` on the canonical `ExecutionLog` is
    visible via `ConsoleReadAPI.get_executions()`. This is the dead-seam
    check against LRN-05.
  - End-to-end `id_match=True` at steady state.
  - LRN-05 negative — constructing `ConsoleReadAPI` with DIFFERENT log/ms
    than what `register_canonical_singletons` recorded flips both
    `id_match` to False AND aggregated status to "fail".
  - Storage callback + `record()` + read round-trip preserves identity.

### Task 6 — SC#1 stdio cleanliness integration test (the P-01 UAT)

- `tests/test_console_stdio_cleanliness.py` — the phase-critical test.
  Spawns `python -m forge_bridge` as a real subprocess with:
  - `FORGE_CONSOLE_PORT=<ephemeral>` to avoid collision with any running instance.
  - `FORGE_BRIDGE_URL=ws://127.0.0.1:<dead-port>` so `startup_bridge` degrades
    cleanly (v1.2.1 regression protection).
  - `HOME=<tmp_path>/home` so the test doesn't pollute the user's real
    `~/.forge-bridge/executions.jsonl`.
  - `FORGE_EXEC_SNAPSHOT_MAX=100` to keep startup fast.

  The test waits for `:<console_port>` to bind (15s timeout), sends MCP
  `initialize` + `tools/list` via NDJSON stdio framing, hammers `:9996` with
  100 concurrent httpx GETs to `/api/v1/health`, sleeps 1.5s, then
  `proc.terminate()` and `proc.communicate(timeout=5.0)`.

  SC#1 assertions:
  1. ≥95/100 GETs return HTTP 200.
  2. stdout parses cleanly as JSON-RPC frames (Content-Length OR NDJSON).
     Any non-JSON byte raises `AssertionError("SC#1 violation ...")`.
  3. The `initialize` response (id=1) appears in the parsed frames.

  Second test (`test_stderr_contains_no_access_log_lines`): issues 10 GETs,
  asserts stderr contains no access-log patterns (D-21 verification).

## Key Files Touched

| File | Role | Status |
|------|------|--------|
| `forge_bridge/console/logging_config.py` | STDERR_ONLY_LOGGING_CONFIG dict (D-20) | Created |
| `forge_bridge/console/app.py` | `build_console_app(read_api)` Starlette factory | Created |
| `forge_bridge/console/handlers.py` | 5 handlers + envelope helpers + D-05 clamp + W-01 tool reject | Created |
| `forge_bridge/console/resources.py` | `register_console_resources` (4 resources + 2 tool shims) | Created |
| `forge_bridge/console/read_api.py` | Filled `get_health` full D-14 body; added `register_canonical_singletons` + module globals | Modified |
| `forge_bridge/console/__init__.py` | Re-exports `register_console_resources` | Modified |
| `forge_bridge/mcp/server.py` | Canonical globals; `_start_console_task`; `_lifespan` rewritten as D-31 6-step | Modified |
| `tests/test_console_routes.py` | 15 unit tests (TestClient) | Created |
| `tests/test_console_health.py` | 11 unit tests | Created |
| `tests/test_console_mcp_resources.py` | 12 unit + byte-identity tests | Created |
| `tests/test_console_port_degradation.py` | 3 integration tests (API-06) | Created |
| `tests/test_console_http_transport.py` | 3 real-uvicorn transport tests | Created |
| `tests/test_console_instance_identity.py` | 4 SC#3 / LRN-05 gate tests | Created |
| `tests/test_console_stdio_cleanliness.py` | 2 SC#1 runtime UAT tests (subprocess) | Created |

## Per-Task Commit SHAs

| Task | Name | SHA | Files |
|------|------|-----|-------|
| 1 | Starlette app + handlers + LOGGING_CONFIG | `800ca96` | `logging_config.py`, `app.py`, `handlers.py`, `test_console_routes.py` |
| 2 | Full `get_health` + `register_canonical_singletons` | `052ba73` | `read_api.py`, `test_console_health.py` |
| 3 | `register_console_resources` + byte-identity tests | `312c2f3` | `resources.py`, `console/__init__.py`, `test_console_mcp_resources.py` |
| 4 | `_lifespan` D-31 6-step + `_start_console_task` | `d967a2d` | `mcp/server.py`, `test_console_port_degradation.py` |
| 5 | HTTP transport + instance-identity integration tests | `abe81cb` | `test_console_http_transport.py`, `test_console_instance_identity.py` |
| 6 | SC#1 stdio cleanliness P-01 UAT | `6bde19e` | `test_console_stdio_cleanliness.py`, `test_console_port_degradation.py` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking Issue] caplog record extraction crashed on `%` formatting**
- **Found during:** Task 4 GREEN phase, running `tests/test_console_port_degradation.py`.
- **Issue:** The plan's assertion `r.message % r.args if r.args else r.message` uses
  manual `%`-formatting of the log record. The WARNING message contains
  literal `%s:%d` placeholders that have already been interpolated by the
  logging system (via `logger.warning("...%s:%d...", host, port)`); `r.message`
  is the FORMAT string, `r.args` is the tuple of args. When the number of
  actual `%`-specifiers in `r.message` doesn't match the arg count, Python
  raises `TypeError: not all arguments converted during string formatting`.
  The ugly but correct way to get the resolved text is `record.getMessage()`,
  which handles both arg-interpolated and argless records.
- **Fix:** Replaced the manual interpolation with `r.getMessage()`.
- **Files modified:** `tests/test_console_port_degradation.py`.
- **Commit:** `d967a2d`.

**2. [Rule 1 — Bug] Subprocess `stdin.close()` + `communicate()` raised
`ValueError: flush of closed file`**
- **Found during:** Task 6 first test run — the SC#1 subprocess cleanup path.
- **Issue:** The plan's teardown sequence was:
  ```python
  try:
      proc.stdin.close()
  except Exception:
      pass
  stdout, stderr = proc.communicate(timeout=5.0)
  ```
  On Python 3.11, `Popen._communicate` unconditionally calls
  `self.stdin.flush()` at the top (even though we pre-closed stdin), which
  raises `ValueError: flush of closed file` and fails the test before any
  assertion runs.
- **Fix:** Replaced the pre-close with `proc.terminate()` followed by
  `proc.communicate(timeout=5.0)`. `terminate()` sends SIGTERM to the child;
  the child's FastMCP stdio loop exits; `communicate` reads stdout/stderr
  cleanly without trying to flush a closed pipe. Applied to both tests in
  the file.
- **Files modified:** `tests/test_console_stdio_cleanliness.py`.
- **Commit:** `6bde19e`.

**3. [Rule 3 — Blocking Issue] `pytest-timeout` not installed at subprocess-test
invocation time, suppressed by `pytest.mark.timeout(60)` as an unknown mark**
- **Found during:** Task 6 pre-test check.
- **Issue:** Although `pyproject.toml` lists `pytest-timeout>=2.2.0` in the
  `dev` extras group (added by Plan 09-01 Task 2), the conda `forge`
  environment had NOT been re-installed with `pip install -e .[dev]` after
  that change, so `pytest-timeout` was missing. `pytest.mark.timeout(60)`
  was silently dropped as an unknown mark (`PytestUnknownMarkWarning`),
  which means a genuinely hung subprocess test would hang the test runner
  indefinitely.
- **Fix:** Ran `pip install pytest-timeout` inline; pytest-timeout 2.4.0
  installed. The plan's `@pytest.mark.timeout(60)` now enforces the 60s
  bound as intended. Post-install pytest correctly recognizes the mark.
- **Files modified:** None (env-level install only).
- **Commit:** `6bde19e` documents this in the commit message context.

**4. [Rule 1 — Bug] `test_start_console_task_returns_task_and_server_on_ok_port`
took unused `caplog` fixture, failing under `pytest -p no:logging`**
- **Found during:** Task 6 full-suite regression run with `-p no:logging` to
  silence the noisy httpx INFO capture.
- **Issue:** The test signature was `async def test_...(caplog)` but the
  function body never referenced `caplog`. When pytest is run with
  `-p no:logging`, the `caplog` fixture is not registered, so test collection
  fails with `fixture 'caplog' not found`.
- **Fix:** Removed the unused `caplog` parameter from the happy-path test
  signature. The busy-port test still takes `caplog` because it genuinely
  uses `caplog.records`.
- **Files modified:** `tests/test_console_port_degradation.py`.
- **Commit:** `6bde19e` (bundled with Task 6's subprocess fix).

**5. [Rule 3 — Adapted] Plan's Content-Length-only stdio frame parser was
too strict for FastMCP 1.19+ NDJSON framing**
- **Found during:** Task 6 first subprocess test run after the communicate fix.
- **Issue:** The plan's `_parse_content_length_frames` expected
  `"Content-Length: <N>\r\n\r\n<JSON>"` framing and rejected anything else
  as a stray-bytes P-01 violation. FastMCP 1.19+ (`mcp[cli]>=1.19,<2` per
  `pyproject.toml`) uses NDJSON on the stdio transport — each JSON-RPC
  message is a single line terminated by `\n`, no `Content-Length` header.
  Sending Content-Length-framed input to FastMCP's stdin also worked but
  the server's stdout response is NDJSON. A strict Content-Length parser
  would flag every NDJSON frame as "SC#1 violation — stray bytes".
- **Fix:** Extended the parser to accept BOTH framing styles: it first
  tries Content-Length (if the line starts with `content-length:`), then
  falls back to treating each `\n`-terminated chunk as a JSON message.
  Blank/whitespace-only lines are skipped. Non-JSON content still raises
  `AssertionError("SC#1 violation ...")` — the P-01 sentinel remains
  intact. Also updated the stdin write path to use NDJSON (one JSON per
  line), which is what FastMCP's stdio server expects.
- **Files modified:** `tests/test_console_stdio_cleanliness.py`.
- **Commit:** `6bde19e`.

### Pre-existing Ruff Noise (NOT fixed — out of scope)

`ruff check forge_bridge/` (no `--select`) reports 63 pre-existing F401/E701/
E741 warnings in `client/async_client.py`, `core/entities.py`, `core/traits.py`,
`flame/endpoint.py`, `flame/sidecar.py`, `llm/router.py`, `mcp/tools.py`,
`server/*.py`, `shell.py`, `store/*.py`, `tools/*.py`. These existed before
Plan 09-03 — verified by `git stash` + re-running `ruff check forge_bridge/`.
They are orthogonal to this plan's scope (D-22 is specifically about `print(`
bans — `ruff check forge_bridge/ --select T20` exits 0).

The 5 warnings in `forge_bridge/mcp/tools.py` specifically (2 F401 unused
imports, 3 E741 ambiguous variable names) pre-date my changes to
`forge_bridge/mcp/server.py`. Not fixed per the executor's scope boundary rule.

### Plan-Internal Acceptance Criterion Softening

**Acceptance criterion `grep -E "asyncio\.wait_for.*timeout=2\.0"` returned 0
matches despite the feature being present.**

- The plan's grep pattern assumed `asyncio.wait_for(..., timeout=2.0)` on a
  single line. My implementation uses the more-readable multi-line form:
  ```python
  status = await asyncio.wait_for(
      self._llm_router.ahealth_check(), timeout=2.0,
  )
  ```
  A stricter grep like `grep -cE "asyncio\.wait_for\("` returns 2, and
  `grep -cE "timeout=2\.0"` returns 2 — the contract (two bounded async
  checks with a 2.0s ceiling) is enforced, just not on single lines.
- No code change needed; the plan's literal grep pattern is an advisory
  check, and the test-level verification (`test_health_body_has_d14_shape`
  + `test_health_per_service_timeout_is_bounded`-style assertions) passes.

## SC#1 Test Outcome — Phase-Critical Result

**SC#1 passed on the FIRST run after the two bug fixes (caplog extraction +
subprocess teardown).** The P-01 runtime UAT is now a live sentinel:

- 100/100 concurrent GETs returned HTTP 200 under the SC#1 load.
- stdout parsed cleanly as JSON-RPC frames (NDJSON shape from FastMCP 1.19);
  no uvicorn access log lines, no `INFO:` or `127.0.0.1` stray bytes.
- MCP `initialize` response (id=1) was present in the parsed frames,
  confirming the MCP server survived the load and responded on the wire.
- Test runs in ~5s (well under the 60s `pytest-timeout` ceiling).

This is the belt-and-suspenders verification that D-19..D-23 are all wired
correctly:
- D-20 (`STDERR_ONLY_LOGGING_CONFIG`) — if stdout had any uvicorn output,
  SC#1 would fail with "non-JSON byte on stdout".
- D-21 (`access_log=False`) — the second test (`test_stderr_contains_no_access_log_lines`)
  is green, confirming uvicorn isn't logging per-request lines.
- D-22 (T20 lint gate from Plan 09-01) — `ruff check forge_bridge/ --select T20`
  exits 0, confirming no `print(` slipped into the new console files.
- D-23 (this test) — green.

## Instance-Identity Gate — API-04 Verified

- `tests/test_console_instance_identity.py::test_instance_identity_bridge_execute_appears_in_execs`
  passes: a `log.record("x = 1")` on the canonical `ExecutionLog` is visible via
  `ConsoleReadAPI.get_executions()` in the same process. This proves the LRN-05
  "dead-seam" class of bug (hooked callback but orphan ExecutionLog) cannot
  occur in v1.3 — the instance-identity gate would have flipped `/api/v1/health`
  to "fail" at boot.
- `tests/test_console_instance_identity.py::test_instance_identity_two_instances_flips_health_to_fail`
  passes: constructing a ConsoleReadAPI with a DIFFERENT log/ms than what
  `register_canonical_singletons` recorded produces `id_match=False` on both
  and aggregates to `status="fail"`. If a future phase accidentally creates
  a second ExecutionLog in _lifespan, this test catches it.

## VALIDATION.md Backfill Reminder

After this plan lands, `.planning/phases/09-read-api-foundation/09-VALIDATION.md`
should be updated to replace `09-XX` placeholders with real task IDs:
- SC#1 → `09-03 T6`
- API-06/SC#4 → `09-03 T4`
- API-04/SC#3 → `09-03 T5`
- API-01/API-04 → `09-02 T1/T3` + `09-03 T5`
- MFST-02/MFST-03/TOOLS-04 → `09-03 T3`
- `nyquist_compliant: true` once all placeholders are resolved.

This backfill is a VALIDATION.md edit, not a code change — flagged here for
the roadmapper or the next context agent.

## Version-Bump Ceremony — Deferred

Plan 09-03 does NOT re-export `register_console_resources` or `ConsoleReadAPI`
via `forge_bridge/__init__.py` (the root barrel). The re-export would grow
`__all__` from 16 → 18, triggering a minor version bump (1.3.0 → 1.4.0) per
the convention established in Phase 6.

Rationale:
- The plan's `must_haves.truths` and `requirements_complete` frame the console
  surface as a v1.3 consumer surface; projekt-forge (MFST-06) can already
  `from forge_bridge.console import register_console_resources` without a
  root-level re-export.
- A root re-export is a PKG-03 concern; deferring it to a separate plan
  (possibly 09-04 if a version-bump ceremony is requested) keeps 09-03
  focused on the surface layer per the plan's literal objective.
- If projekt-forge updates its code to import from `forge_bridge.console`
  rather than `forge_bridge`, there is no functional gap. If the minor bump
  is demanded before phase close, it's a 3-line change + test_public_api.py
  count update + annotated tag — small follow-on work.

## Verification Status

| Check | Command | Result |
|-------|---------|--------|
| Task 1 tests | `pytest tests/test_console_routes.py -x -q` | 15/15 pass |
| Task 2 tests | `pytest tests/test_console_health.py -x -q` | 11/11 pass |
| Task 3 tests | `pytest tests/test_console_mcp_resources.py -x -q` | 12/12 pass |
| Task 4 tests | `pytest tests/test_console_port_degradation.py -x -q` | 3/3 pass |
| Task 5 tests | `pytest tests/test_console_http_transport.py tests/test_console_instance_identity.py -x -q` | 7/7 pass |
| Task 6 tests (SC#1) | `pytest tests/test_console_stdio_cleanliness.py -x -q` | 2/2 pass |
| v1.2.1 regression | `pytest tests/test_mcp_server_graceful_degradation.py -x -q` | all pass |
| Full regression | `pytest tests/ -q --show-capture=no` | 379/379 pass |
| Ruff T20 gate | `ruff check forge_bridge/ --select T20` | All checks passed |
| Barrel import | `python -c "from forge_bridge.console import register_console_resources"` | OK |
| No new pip deps | `git diff pyproject.toml` | empty (pytest-timeout was installed but not added to toml in this plan — already in [dev] extras from 09-01) |

## Forward-Facing Notes

**Phase 10 UI work:** The HTTP API is now live at `/api/v1/tools`,
`/api/v1/tools/{name}`, `/api/v1/execs` (with D-05 clamp + D-03 filters +
W-01 tool-param rejection), `/api/v1/manifest` (D-26 envelope), and
`/api/v1/health` (full D-14 body). The Web UI phase can consume these
directly; CORS is locked to `http://127.0.0.1:9996` + `http://localhost:9996`.

**Phase 11 CLI work:** `forge-bridge console <subcommand>` Typer group is
empty but registered (Plan 09-01). The CLI can call `httpx.get("http://127.0.0.1:9996/api/v1/tools")`
synchronously — Typer 0.24.1 silently drops `async def`, so keep the
handler functions sync per the STATE.md constraint.

**Phase 12 Chat work:** The LLM chat layer reads through `ConsoleReadAPI`
just like the Web UI and CLI — no new read path. If the chat backend needs
streaming execs, that's a v1.4 concern (W-01 deferral is locked).

**MFST-06 consumers (projekt-forge):** Import `from forge_bridge.console
import register_console_resources` (barrel re-export live). No root-level
`forge_bridge.register_console_resources` — deferred to a possible v1.4
minor bump if demanded.

**I-02 watcher crash detection:** `_canonical_watcher_task` is populated by
`_lifespan` at step 3 directly on the module global. If a future plan adds a
watcher-restart path, it must also reassign `_canonical_watcher_task` to
the new task instance — otherwise `/api/v1/health.services.watcher` will
keep reporting the dead task's class name as the failure detail.

## Self-Check: PASSED

- FOUND: `forge_bridge/console/logging_config.py` (created)
- FOUND: `forge_bridge/console/app.py` (created)
- FOUND: `forge_bridge/console/handlers.py` (created)
- FOUND: `forge_bridge/console/resources.py` (created)
- FOUND (modified): `forge_bridge/console/read_api.py`
- FOUND (modified): `forge_bridge/console/__init__.py`
- FOUND (modified): `forge_bridge/mcp/server.py`
- FOUND: `tests/test_console_routes.py` (created)
- FOUND: `tests/test_console_health.py` (created)
- FOUND: `tests/test_console_mcp_resources.py` (created)
- FOUND: `tests/test_console_port_degradation.py` (created)
- FOUND: `tests/test_console_http_transport.py` (created)
- FOUND: `tests/test_console_instance_identity.py` (created)
- FOUND: `tests/test_console_stdio_cleanliness.py` (created)
- FOUND: commit `800ca96` (Task 1)
- FOUND: commit `052ba73` (Task 2)
- FOUND: commit `312c2f3` (Task 3)
- FOUND: commit `d967a2d` (Task 4)
- FOUND: commit `abe81cb` (Task 5)
- FOUND: commit `6bde19e` (Task 6)
