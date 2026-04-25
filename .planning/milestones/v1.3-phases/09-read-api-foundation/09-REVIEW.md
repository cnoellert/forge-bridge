---
status: issues_found
phase: 09-read-api-foundation
depth: standard
reviewed: 2026-04-22
reviewer: gsd-code-reviewer
files_reviewed: 24
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
---

# Phase 9: Code Review Report

## Files Reviewed

- `forge_bridge/__main__.py`
- `forge_bridge/console/__init__.py`
- `forge_bridge/console/app.py`
- `forge_bridge/console/handlers.py`
- `forge_bridge/console/logging_config.py`
- `forge_bridge/console/manifest_service.py`
- `forge_bridge/console/read_api.py`
- `forge_bridge/console/resources.py`
- `forge_bridge/learning/execution_log.py`
- `forge_bridge/learning/watcher.py`
- `forge_bridge/mcp/server.py`
- `pyproject.toml`
- `tests/test_console_health.py`
- `tests/test_console_http_transport.py`
- `tests/test_console_instance_identity.py`
- `tests/test_console_mcp_resources.py`
- `tests/test_console_port_degradation.py`
- `tests/test_console_read_api.py`
- `tests/test_console_routes.py`
- `tests/test_console_stdio_cleanliness.py`
- `tests/test_execution_log.py`
- `tests/test_manifest_service.py`
- `tests/test_typer_entrypoint.py`
- `tests/test_watcher.py`

## Summary

Phase 9 establishes the Artist Console read layer (`ConsoleReadAPI`, `ManifestService`, HTTP routes, MCP resources, Typer entry point). Overall quality is high: code is well-structured, thoroughly commented with REQ-ID / decision references (D-01..D-31), defensive, and backed by extensive tests covering instance identity, byte-identity across surfaces, stdio cleanliness under load, and graceful port degradation.

The review surfaces four **warnings** (reachable `AttributeError` on bare `ExecutionLog` mocks, env-var parse crashes at boot, sync-calls-async watcher smell with silent task leak, silent pagination coercion) and five **info** items (naming, duplication, minor robustness). No critical security issues or bugs were found.

**Totals:** 0 Critical / 4 Warning / 5 Info = 9 items.

## Warnings

### WR-01: `_check_storage_callback` AttributeErrors on bare mocks — reachable via `execs_handler` except path

**File:** `forge_bridge/console/read_api.py:299-311` (also `forge_bridge/console/handlers.py:150-153`)

`_check_storage_callback` reads `self._execution_log._storage_callback` — a private attribute. Every test that constructs `ConsoleReadAPI(execution_log=MagicMock(), ...)` must remember to set `mock_log._storage_callback = None` (see `tests/test_console_mcp_resources.py:46` for a correct example, but `tests/test_console_routes.py:34` and `tests/test_console_routes.py:188-189` do NOT set it). When `get_health()` is called against such a mock, `getattr` would succeed but any real-world production `ExecutionLog` substitute that omits the private attribute would raise `AttributeError`.

Critically: the three async checks (`_check_flame_bridge`, `_check_ws_server`, `_check_llm_backends`) are wrapped in `asyncio.gather(..., return_exceptions=True)`, but the five sync checks (`_check_mcp`, `_check_watcher`, `_check_storage_callback`, `_check_console_port`, `_check_instance_identity`) run unguarded at lines 364-368. Any unexpected attribute access failure on a non-canonical `ExecutionLog` (e.g., a subclass or a test mock) crashes the whole `get_health()` call.

**Fix:** Guard every sync check the same way the async checks are guarded. Better: expose a public `ExecutionLog.has_storage_callback()` method so the console layer does not reach into private state.

### WR-02: Env-var parse crashes boot when `FORGE_PROMOTION_THRESHOLD` / `FORGE_EXEC_SNAPSHOT_MAX` / `FORGE_CONSOLE_PORT` are non-integer

**File:** `forge_bridge/learning/execution_log.py:115,123` and `forge_bridge/mcp/server.py:126`

Three `int(os.environ.get("...", default))` calls assume the env var, if set, is parseable. A user who sets `FORGE_CONSOLE_PORT=auto` or `FORGE_EXEC_SNAPSHOT_MAX=10k` gets a `ValueError` at boot from `_lifespan` step 2 or step 4 — inside the FastMCP lifespan, where exceptions kill the whole MCP server (breaking the stdio contract with no actionable user message — P-01 territory).

**Fix:** Wrap each env read with a validated helper that falls back to the default and logs a WARNING.

### WR-03: `_scan_once` uses `asyncio.create_task` from a sync function — silent task leak, broad `except`

**File:** `forge_bridge/learning/watcher.py:268, 288`

`_scan_once` is synchronous but calls `asyncio.create_task(manifest_service.register(record))` inside its body. The `try: ... except Exception: logger.exception(...)` wrapper at lines 270 and 290 catches the RuntimeError if no loop is running, but the `except Exception` is broad enough to silently swallow `_build_tool_record`'s errors too. Additionally, the fire-and-forget mirror tasks are NOT awaited anywhere — they leak out of the watcher task's cancellation scope on teardown.

**Fix:** Narrow the exception handler to `RuntimeError`, or refactor `_scan_once` to `async def` and `await` `manifest_service.register` directly (see IN-01).

### WR-04: `_parse_pagination` silently coerces nonsensical values rather than 400ing

**File:** `forge_bridge/console/handlers.py:65-77`

`?limit=foo` and `?offset=bar` currently fall back to defaults without any error signal to the caller. Compare this to `?since=bad` which correctly returns 400 `bad_request` (line 95-96). A client mistyping `limit=a50` thinks pagination works and sees default 50 results without ever knowing the flag was ignored.

**Fix:** Raise `ValueError` on unparseable input and return 400 `bad_request`, mirroring the `since` handler's behavior.

## Info

### IN-01: Sync `_scan_once` vs async `manifest_service.register` — mixing sync/async boundary adds complexity

**File:** `forge_bridge/learning/watcher.py:218-294`

The sync-calls-async-via-create_task pattern (WR-03) is an architectural smell. The watcher coroutine is the only caller of `_scan_once`, so converting `_scan_once` to `async def` would allow a simple `await manifest_service.register(record)` instead of the fire-and-forget + done-callback machinery. Tests already use `asyncio.sleep(0)` to drain fire-and-forget tasks (e.g., `tests/test_watcher.py:339, 386`), which is fragile.

### IN-02: Unused parameter `manifest_service` in `register_console_resources`

**File:** `forge_bridge/console/resources.py:29-49`

The function accepts `manifest_service` but deliberately ignores it (`_ = manifest_service  # silence unused warning`). The docstring says "accepted for signature stability / future use." This is a YAGNI concession that leaks into the caller API.

**Fix:** Drop the parameter from the signature. If future needs arise, add it back as a kwarg with default `None`.

### IN-03: `_check_flame_bridge` uses nested timeouts (1.5s httpx + 2.0s wait_for) with partial redundancy

**File:** `forge_bridge/console/read_api.py:182-205`

`httpx.AsyncClient(timeout=1.5)` is wrapped in `asyncio.wait_for(..., timeout=2.0)`. Additionally, `client.get(self._flame_bridge_url, timeout=1.5)` passes the timeout to the request on line 186, overriding the client-level setting.

**Fix:** Simplify to one timeout — either the httpx level or the `asyncio.wait_for` level, not both.

### IN-04: `_find_free_port` idiom duplicated across 3 test files

**Files:** `tests/test_console_http_transport.py:24-27`, `tests/test_console_port_degradation.py:18-21`, `tests/test_console_stdio_cleanliness.py:32-35`

Same 4-line helper copy-pasted into three test modules.

**Fix:** Move `_find_free_port` into `tests/conftest.py` as a session-scoped fixture or module-level utility.

### IN-05: `_read_sidecar` has large duplicated block between sidecar and legacy paths

**File:** `forge_bridge/learning/watcher.py:67-154`

The sidecar-path block (lines 84-116) and the legacy-path block (lines 117-139) share ~20 lines of type-guard + warning logic with trivial differences.

**Fix:** Factor shared logic into a `_load_with_guards(path, kind)` helper.

## Observations (not findings)

- **Excellent defense-in-depth on stdout cleanliness (P-01):** D-19..D-23 combine custom uvicorn logging config, `access_log=False`, a T20 ruff lint gate, a `_start_console_task` probe, and a full subprocess-level SC#1 test. Layering is good.
- **Instance-identity gate is well-implemented:** The `id()` comparison + `DRIFT` marker in the health body is a clean way to surface LRN-05-class bugs. Tests cover both canonical and drift paths.
- **Byte-identity contract between HTTP and MCP surfaces** is tested end-to-end via `test_manifest_resource_body_matches_http_route_bytes` — the right abstraction level for MFST-06.
- **Pyproject ruff carve-outs for `forge_bridge/server.py` and `forge_bridge/shell.py`** are flagged as pre-Phase-5 orphans with a cleanup TODO. Acceptable tech-debt accounting.
- **`ExecutionRecord` is frozen + dataclass** — good choice for the cross-thread/async callback contract.

---

_Reviewed: 2026-04-22_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
