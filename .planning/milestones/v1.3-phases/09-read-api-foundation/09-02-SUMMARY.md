---
phase: 09-read-api-foundation
plan: 02
subsystem: data-layer
tags:
  - data-layer
  - manifest-service
  - execution-log
  - read-api
  - watcher
requires:
  - typer>=0.24,<1 (landed 09-01)
  - pytest-timeout>=2.2.0 (landed 09-01)
provides:
  - forge_bridge.console.ManifestService (in-memory singleton; asyncio.Lock-guarded writes, lockless reads)
  - forge_bridge.console.ToolRecord (frozen dataclass; snake_case D-04; tuple-only tags/meta)
  - forge_bridge.console.ConsoleReadAPI (sole read layer for Web UI/CLI/MCP resources/chat)
  - ExecutionLog._records deque + snapshot() (D-06/D-07/D-09 — bounded deque query surface)
  - ExecutionLog._promoted_hashes set (D-09 snapshot projection)
  - watch_synthesized_tools manifest_service kwarg (backward-compatible; None preserves Phase 3-8 behavior)
affects:
  - forge_bridge/console/__init__.py (new; barrel re-exports 3 symbols)
  - forge_bridge/console/manifest_service.py (new)
  - forge_bridge/console/read_api.py (new)
  - forge_bridge/learning/execution_log.py (extended — imports, __init__, _replay, record, mark_promoted, new snapshot method)
  - forge_bridge/learning/watcher.py (extended — TYPE_CHECKING import, watch_synthesized_tools + _scan_once signatures, two new helpers, register/remove mirroring)
  - tests/test_manifest_service.py (new; 10 tests)
  - tests/test_console_read_api.py (new; 9 tests)
  - tests/test_execution_log.py (extended; +11 tests, total 34)
  - tests/test_watcher.py (extended; +4 tests in TestWatcherManifestServiceInjection)
tech-stack:
  added:
    - "collections.deque (stdlib, already available)"
    - "dataclasses.replace for D-09 frozen-record promoted projection (stdlib)"
  patterns:
    - "asyncio.Lock-guarded writes + lockless atomic dict reads on the ManifestService (Python GIL + frozen ToolRecord = safe without RWLock)"
    - "Bounded collections.deque(maxlen=FORGE_EXEC_SNAPSHOT_MAX) for snapshot()'s hot path — never touches JSONL"
    - "sync-in-async bridge via asyncio.create_task(...) + add_done_callback(_log_manifest_register_exception) from watcher's _scan_once (called inside the watch_synthesized_tools coroutine)"
    - "Lazy import of ToolRecord inside _build_tool_record to break the learning<->console import cycle"
    - "API-04 instance-identity seat: required no-default execution_log + manifest_service kwargs on ConsoleReadAPI — TypeError on empty construction proves the canonical singletons must be threaded from _lifespan"
    - "D-09 frozen-record promotion projection: dataclasses.replace(rec, promoted=True) at snapshot-read time instead of mutating the frozen deque entry"
key-files:
  created:
    - forge_bridge/console/__init__.py
    - forge_bridge/console/manifest_service.py
    - forge_bridge/console/read_api.py
    - tests/test_manifest_service.py
    - tests/test_console_read_api.py
  modified:
    - forge_bridge/learning/execution_log.py
    - forge_bridge/learning/watcher.py
    - tests/test_execution_log.py
    - tests/test_watcher.py
decisions:
  - "ToolRecord uses tuple[str, ...] + tuple[tuple[str,str],...] for tags/meta (frozen dataclass requires hashable fields); __post_init__ runtime guard rejects list/dict at construction time with a clear TypeError message."
  - "ConsoleReadAPI.get_executions does NOT accept a `tool=` kwarg per W-01 — the /api/v1/execs route in Plan 09-03 rejects `?tool=...` with a 400 not_implemented. Symmetric `test_get_executions_does_not_accept_tool_kwarg` locks the contract so a future maintainer cannot quietly add the kwarg without a REQ-ID."
  - "ExecutionLog keeps BOTH _promoted and _promoted_hashes sets. _promoted governs the threshold/retrigger logic (pre-existing). _promoted_hashes is the snapshot-projection source. They are written together (invariant: _promoted subset-of _promoted_hashes) but read independently — changing one would desync the D-09 projection."
  - "_build_tool_record lazy-imports ToolRecord from forge_bridge.console.manifest_service to avoid the watcher<->console circular import. Hoisting the import to module top triggers ImportError on learning package load."
  - "ConsoleReadAPI.get_health() is a STUB in Plan 09-02 — returns status + ts + empty services dict + instance_identity ids. Plan 09-03 fills the full D-14 body (services.flame/ws_bridge/llm_backends fan-out + full instance_identity gate)."
metrics:
  duration: 7m33s
  completed: 2026-04-23
  tasks: 3
  files_touched: 9
commits:
  - 5d0ae4e feat(09-02): add forge_bridge/console package with ManifestService + ToolRecord
  - 266b873 feat(09-02): extend ExecutionLog with _records deque + snapshot() + _promoted_hashes
  - 821b79c feat(09-02): add ConsoleReadAPI + inject ManifestService into watcher
requirements_complete:
  - API-01
  - API-04
  - MFST-01
  - EXECS-04
---

# Phase 9 Plan 02: Read API Foundation — Data Layer Summary

Built the substrate the Plan 09-03 HTTP + MCP surface layer consumes: the
in-memory `ManifestService` singleton, the `ConsoleReadAPI` facade, the
`ExecutionLog` bounded-deque `snapshot()` query surface, and the watcher
injection that keeps the manifest in lock-step with the live MCP tool registry.
No HTTP, Starlette, uvicorn, or MCP-resource wiring in this plan — those land
in 09-03. No new pip dependencies.

## What Was Done

### Task 1 — `forge_bridge/console/` package scaffolding

- Created the `forge_bridge/console/` Python package with two source files:
  - `manifest_service.py` — `@dataclass(frozen=True) ToolRecord` with snake_case
    field names (`name/origin/namespace/synthesized_at/code_hash/version/
    observation_count/tags/meta`), tuple-only `tags` + `meta` (frozen dataclass
    requirement), and `__post_init__` runtime guards that raise `TypeError`
    with clear messages when a list or dict is passed. `to_dict()` serializes
    tuples to list/dict at the wire boundary (D-26 envelope shape).
    `ManifestService` exposes `async register/remove` under an `asyncio.Lock`
    plus lockless sync `get/get_all` (dict lookup atomic under CPython GIL +
    immutable ToolRecord = safe).
  - `__init__.py` — barrel re-exporting `ManifestService` and `ToolRecord`.
    Task 3 grows it to add `ConsoleReadAPI`; Plan 09-03 Task 3 adds
    `register_console_resources` (B-01 incremental barrel growth).
- Created `tests/test_manifest_service.py` with 10 unit tests: frozen
  invariants, `to_dict` wire shape, list/dict-rejection `__post_init__` guards
  on both `tags` and `meta`, register/get/get_all/remove CRUD, insertion-order
  iteration, shallow-copy-on-read, and a 20-task concurrent-register
  serialization test that pins the `asyncio.Lock` contract.

### Task 2 — `ExecutionLog` deque + `snapshot()` + `_promoted_hashes`

- Added `import collections`, `import dataclasses`, and module-level constant
  `_DEFAULT_MAX_SNAPSHOT = 10_000`.
- `ExecutionLog.__init__`: new `self._records: collections.deque[ExecutionRecord]`
  sized from `FORGE_EXEC_SNAPSHOT_MAX` env with the 10,000-record default, plus
  a new `self._promoted_hashes: set[str]` for the D-09 projection source. The
  deque is created BEFORE `self._replay()` so replay can populate it.
- `_replay()`: both the promotion-only branch and the normal-record branch now
  write to `self._promoted_hashes` as well as the existing `self._promoted`.
  The normal-record branch also builds a replayed `ExecutionRecord` and
  `self._records.append(replayed)` per row — the deque's `maxlen` guarantees
  newest-wins when the JSONL has more rows than the cap.
- `record()`: appends to `self._records` AFTER the JSONL `fp.flush()` +
  fcntl-unlock AND after the storage callback fires. Order is the D-06
  contract: canonical disk write -> consumer mirror -> in-memory snapshot.
- `mark_promoted()`: also adds to `self._promoted_hashes`.
- New `snapshot(limit, offset, since, promoted_only, code_hash)` method reads
  the deque only (D-07), iterates `reversed(...)` for newest-first order,
  and applies filters in this order: `since` (ISO8601 parse + drop-on-
  unparseable for clock-skew tolerance), `promoted_only` (membership in
  `_promoted_hashes`), `code_hash` prefix match (D-03). For records whose
  hash is promoted but whose frozen `.promoted == False`, a
  `dataclasses.replace(rec, promoted=True)` projection synthesizes the
  current state without mutating the deque entry. Returns
  `(page: list[ExecutionRecord], total_before_pagination: int)`. `tool=`
  kwarg is deliberately absent per W-01.
- `tests/test_execution_log.py`: +11 tests covering deque maxlen from env
  (with default), record-appends-to-deque-after-JSONL-flush ordering,
  snapshot newest-first default, limit+offset pagination, `since` filter,
  `promoted_only` filter with D-09 projection (the critical "promoted=True
  on a frozen record whose stored .promoted is False" assertion),
  `code_hash` prefix filter, replay deque refill, replay-maxlen-newest-wins
  (50 JSONL rows down to 10-deep deque), and `mark_promoted` +
  `_promoted_hashes` invariant. Existing 23 tests remain green.

### Task 3 — `ConsoleReadAPI` + watcher injection

- Created `forge_bridge/console/read_api.py` with `ConsoleReadAPI`:
  - REQUIRED no-default `execution_log: "ExecutionLog"` + `manifest_service:
    "ManifestService"` kwargs (API-04 seat — constructor-without-args raises
    `TypeError`, proving that Plan 09-03 must pass the `_lifespan`-owned
    canonical singletons).
  - Optional `llm_router`, `flame_bridge_url`, `ws_bridge_url`, `console_port`
    (defaults read from `FORGE_BRIDGE_HOST/PORT` and `FORGE_BRIDGE_URL` env
    per the LLMRouter env-fallback pattern; console_port defaults to 9996
    per D-27).
  - `async get_tools()` / `async get_tool(name)` delegate to
    `self._manifest_service.get_all()` / `.get(name)`.
  - `async get_executions(limit=50, offset=0, since=None, promoted_only=False,
    code_hash=None)` forwards all 5 filter kwargs to `self._execution_log.
    snapshot(...)`. No `tool=` kwarg (W-01).
  - `async get_manifest()` returns the D-26 envelope
    `{"tools": [t.to_dict() ...], "count": N, "schema_version": "1"}`.
  - `async get_health()` returns a STUB `{status, ts, services: {},
    instance_identity: {execution_log.id, manifest_service.id}}` — Plan 09-03
    fills the full services fan-out + identity-gate body.
- Extended `forge_bridge/console/__init__.py` to re-export `ConsoleReadAPI`
  (B-01 incremental barrel growth; three entries now).
- Extended `forge_bridge/learning/watcher.py`:
  - `TYPE_CHECKING` import added for `ManifestService` (no runtime cost).
  - `watch_synthesized_tools` and `_scan_once` both gain a trailing
    `manifest_service: "ManifestService | None" = None` kwarg (backward-
    compatible default preserves every Phase 3-8 test path).
  - Two new helpers near the bottom of the module:
    - `_log_manifest_register_exception(task)` — done-callback mirroring
      `_log_callback_exception` in execution_log.py; logs only
      `type(exc).__name__` (no `str(exc)` credential leak, per Phase 8
      LRN).
    - `_build_tool_record(stem, provenance, digest)` — lazy-imports
      `ToolRecord` to break the circular import, infers namespace from
      `flame_`/`forge_`/default `synth`, extracts meta/tags/version/
      `synthesized_at`/`observation_count` from the sanitized provenance,
      returns a fully-populated `ToolRecord` with `origin="synthesized"`
      and `code_hash=digest`.
  - Successful-registration branch: after `seen[stem] = digest` +
    `logger.info(...)`, when `manifest_service is not None` it schedules
    `manifest_service.register(record)` via `asyncio.create_task(...)` with
    `add_done_callback(_log_manifest_register_exception)`. Wrapped in
    try/except so a scheduling failure logs but does not break the scan.
  - File-deletion branch (inside the `for stem in list(seen)` cleanup): mirrors
    into `manifest_service.remove(stem)` via the same create_task pattern.
- Created `tests/test_console_read_api.py` with 9 tests: required-kwarg
  construction (empty-args and missing-manifest-service both raise
  TypeError), tools delegation, single-tool-or-None lookup, all-5-kwargs
  forwarding through to `snapshot()`, W-01 enforcement that passing
  `tool="synth_*"` raises `TypeError` (unexpected kwarg), manifest envelope
  shape + wire-friendly types, and three async-method-signature assertions.
- Extended `tests/test_watcher.py` with `TestWatcherManifestServiceInjection`
  (+4 tests): signature has the new kwarg with `default is None`, successful
  register mirrors into the service, backward-compat-with-None preserves the
  MCP registration path, and file-deletion mirrors into `manifest_service.
  remove()`.

## Key Files Touched

| File | Role | Status |
|------|------|--------|
| `forge_bridge/console/__init__.py` | Barrel — 3 re-exports (ManifestService, ToolRecord, ConsoleReadAPI) | Created in Task 1, extended in Task 3 |
| `forge_bridge/console/manifest_service.py` | ToolRecord + ManifestService singleton | Created (Task 1, ~120 lines) |
| `forge_bridge/console/read_api.py` | ConsoleReadAPI facade | Created (Task 3, ~145 lines) |
| `forge_bridge/learning/execution_log.py` | Added deque + snapshot + _promoted_hashes | Modified (Task 2, +93 lines) |
| `forge_bridge/learning/watcher.py` | Added manifest_service injection + helpers | Modified (Task 3, +88 lines) |
| `tests/test_manifest_service.py` | 10 unit tests | Created (Task 1) |
| `tests/test_console_read_api.py` | 9 unit tests | Created (Task 3) |
| `tests/test_execution_log.py` | +11 tests (23 -> 34) | Extended (Task 2) |
| `tests/test_watcher.py` | +4 tests in TestWatcherManifestServiceInjection | Extended (Task 3) |

## Per-Task Commit SHAs

| Task | Name | SHA | Files |
|------|------|-----|-------|
| 1 | Console package + ManifestService + ToolRecord | `5d0ae4e` | `forge_bridge/console/__init__.py`, `forge_bridge/console/manifest_service.py`, `tests/test_manifest_service.py` |
| 2 | ExecutionLog deque + snapshot() + _promoted_hashes | `266b873` | `forge_bridge/learning/execution_log.py`, `tests/test_execution_log.py` |
| 3 | ConsoleReadAPI + watcher manifest_service injection | `821b79c` | `forge_bridge/console/read_api.py`, `forge_bridge/console/__init__.py`, `forge_bridge/learning/watcher.py`, `tests/test_console_read_api.py`, `tests/test_watcher.py` |

## Deviations from Plan

### Auto-fixed / Clarified

**1. [Plan internal inconsistency — no code change]
`tests/test_manifest_service.py` ends up with 10 test functions, not the 9
called out in the Task 1 acceptance criterion.**

- **Found during:** Task 1 RED phase.
- **Issue:** The Task 1 action block (lines 496-501 of the plan) explicitly
  writes `test_tool_record_meta_non_tuple_raises` alongside
  `test_tool_record_tags_non_tuple_raises`, but the acceptance-criteria grep
  target reads `grep -cE "def test_" tests/test_manifest_service.py` returns
  9. The plan author wrote 10 tests in the reference implementation and
  mis-counted in the grep line.
- **Fix:** Kept the 10th test — `test_tool_record_meta_non_tuple_raises` is a
  symmetric runtime-guard assertion and carries real contract value. The
  `pytest -x -q` verification passes 10/10. The advisory grep-count check is
  the only artifact that differs from the plan's literal expectation.
- **Files modified:** None beyond the plan-sanctioned test file.
- **Commit:** `5d0ae4e`.

**2. [Plan internal inconsistency — no code change]
`tests/test_console_read_api.py` ends up with 9 test functions, not the 8
called out in the Task 3 acceptance criterion.**

- **Found during:** Task 3 RED phase.
- **Issue:** The Task 3 behavior block lists Test 1 + Test 2 + Test 3 +
  Test 4 + **Test 4b** + Test 5 + Test 6 + Test 7 + Test 8 — that is 9
  entries (the 4b is explicit), and the action block at lines 1356-1366
  literally writes `test_get_executions_does_not_accept_tool_kwarg`. The
  acceptance-criteria grep says 8, which undercounts by one.
- **Fix:** Kept the 9th test — the W-01 tool-kwarg-rejection assertion is
  load-bearing (it pins the symmetric contract with the `not_implemented`
  route in Plan 09-03). `pytest` is authoritative and passes 9/9.
- **Files modified:** None beyond the plan-sanctioned test file.
- **Commit:** `821b79c`.

Both inconsistencies are plan-internal. No code deviation was required.

### No deviations from plan code shape

- Every import, every class body, every method signature, every
  acceptance-criteria grep pattern for source files matched the plan's
  literal prescription.
- The W-01 decision (drop `tool=` kwarg from `snapshot()` + `ConsoleReadAPI.
  get_executions`) was followed verbatim; the plan's `test_get_executions_
  does_not_accept_tool_kwarg` enforces it.
- The `asyncio.create_task` scheduling pattern in `_scan_once` worked
  first-try — no alternate scheduling shape was needed.
- `ConsoleReadAPI.get_health()` is a stub returning the minimal
  `{status, ts, services: {}, instance_identity: {...}}` shape, as the
  plan prescribes. Plan 09-03 fills it.

## `get_health()` is a STUB in Plan 09-02

`ConsoleReadAPI.get_health()` currently returns:

```python
{
    "status": "ok",
    "ts": datetime.utcnow().isoformat(),
    "services": {},
    "instance_identity": {
        "execution_log": {"id": id(self._execution_log)},
        "manifest_service": {"id": id(self._manifest_service)},
    },
}
```

This is deliberately minimal. Plan 09-03 fills it with the D-14 body
(services.flame_bridge, services.ws_bridge, services.llm_backends fan-out +
full instance-identity gate comparing against `_canonical_execution_log`
in `forge_bridge/mcp/server.py`).

## Instance-identity seats (API-04 precondition)

Both singletons are REQUIRED kwargs with NO DEFAULTS on `ConsoleReadAPI`:

```python
def __init__(
    self,
    execution_log: "ExecutionLog",       # required, no default
    manifest_service: "ManifestService", # required, no default
    ...
) -> None:
```

- `ConsoleReadAPI()` raises `TypeError` (Test 1 locks this).
- `ConsoleReadAPI(execution_log=...)` without `manifest_service=...` also
  raises `TypeError`.
- Plan 09-03 will construct the canonical singletons in `_lifespan`, pass
  both to `ConsoleReadAPI`, and flip `/api/v1/health.instance_identity` to
  PASS by comparing `id(...)` against the `_canonical_*` seats on the
  FastMCP server module.

If a future code path ever constructs a second `ExecutionLog` or
`ManifestService` and threads them through a different `ConsoleReadAPI`
instance, the identity gate will flip to FAIL at boot, exactly as API-04
demands.

## Ruff T20 status (from Plan 09-01)

- `ruff check forge_bridge/console/ forge_bridge/learning/` exits 0.
- Zero `print(` calls in the new package.
- T20 remains the lint contract forward — Plan 09-03's router / handlers /
  resources will be gated at their first commit too.

## Verification status

| Check | Command | Result |
|-------|---------|--------|
| Barrel imports end-to-end | `python -c "from forge_bridge.console import ManifestService, ToolRecord, ConsoleReadAPI"` | OK |
| Env var name present | `grep FORGE_EXEC_SNAPSHOT_MAX forge_bridge/learning/execution_log.py` | OK |
| Watcher signature has manifest_service | `inspect.signature(watch_synthesized_tools)` | OK (default=None) |
| Snapshot end-to-end | `log.record('x = 1'); log.snapshot(limit=10)` returns `(1 rec, total=1)` | OK |
| No pip deps changed | `git diff pyproject.toml` | empty |
| Full test suite | `pytest tests/ -x -q` | 329/329 pass |
| Task 1 tests | `pytest tests/test_manifest_service.py -x -q` | 10/10 |
| Task 2 tests | `pytest tests/test_execution_log.py -x -q` | 34/34 (23 prior + 11 new) |
| Task 3 tests (console API) | `pytest tests/test_console_read_api.py -x -q` | 9/9 |
| Task 3 tests (watcher) | `pytest tests/test_watcher.py -x -q` | all (prior + 4 new) pass |
| Ruff T20 gate | `ruff check forge_bridge/console/ forge_bridge/learning/` | All checks passed |

## Forward-Facing Notes for Plan 09-03

- `ConsoleReadAPI` is the ONLY read path for the HTTP/MCP surface — any
  route handler, MCP resource, or shim that parses JSONL or touches
  ManifestService internals is a plan violation.
- The `_lifespan` function in Plan 09-03 must construct exactly ONE
  `ExecutionLog` and ONE `ManifestService`, pass both to
  `ConsoleReadAPI(execution_log=..., manifest_service=...)`, and thread the
  same references into the watcher's `manifest_service` kwarg. The
  instance-identity gate in `/api/v1/health` compares against these same
  references.
- `get_health()` MUST be replaced with the full D-14 body in Plan 09-03
  (the stub here is intentional; overlooking it will break the /api/v1/health
  acceptance tests).
- The `?tool=...` query parameter on `/api/v1/execs` MUST return a 400
  `{"error": {"code": "not_implemented"}}` response — NOT be silently
  accepted. This plan's `test_get_executions_does_not_accept_tool_kwarg`
  enforces that `ConsoleReadAPI.get_executions` does not accept it either,
  so the rejection must happen at the route handler (before `ConsoleReadAPI`
  is called).
- No new pip deps landed in 09-02. 09-03's only additional dep is
  `jinja2>=3.1` (all other deps — Starlette, uvicorn, httpx — ship
  transitively via `mcp[cli]`).

## Self-Check: PASSED

- FOUND: `forge_bridge/console/__init__.py`
- FOUND: `forge_bridge/console/manifest_service.py`
- FOUND: `forge_bridge/console/read_api.py`
- FOUND: `tests/test_manifest_service.py`
- FOUND: `tests/test_console_read_api.py`
- FOUND (modified): `forge_bridge/learning/execution_log.py`
- FOUND (modified): `forge_bridge/learning/watcher.py`
- FOUND (modified): `tests/test_execution_log.py`
- FOUND (modified): `tests/test_watcher.py`
- FOUND: commit `5d0ae4e` (Task 1)
- FOUND: commit `266b873` (Task 2)
- FOUND: commit `821b79c` (Task 3)
