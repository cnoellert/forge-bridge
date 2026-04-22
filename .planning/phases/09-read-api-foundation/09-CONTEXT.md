# Phase 9: Read API Foundation - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The shared read layer for the v1.3 Artist Console — `ConsoleReadAPI` as the sole read path for every surface, `ManifestService` singleton injected into the watcher (write side) and console router (read side), a separate uvicorn asyncio task on `:9996` launched from `_lifespan`, MCP resources (`forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`) plus the `forge_manifest_read` and `forge_tools_read` tool fallback shims, and the `ExecutionLog` instance-identity gate that prevents LRN-05-class drift between writer and reader.

In scope (REQ-IDs): API-01, API-02, API-03, API-04, API-05, API-06, MFST-01, MFST-02, MFST-03, MFST-06, TOOLS-04, EXECS-04.

Out of scope for Phase 9: Web UI templates (Phase 10), CLI subcommands (Phase 11 — but the Typer entry-point root ships here), LLM chat endpoint (Phase 12 / v1.4), SSE/WebSocket streaming push (v1.4), real-time per-record updates, multi-project view, admin/mutation actions, auth.

</domain>

<decisions>
## Implementation Decisions

### API response conventions

- **D-01:** All `/api/v1/` endpoints return a JSON envelope: `{"data": <payload>, "meta": {...}}`. Errors return `{"error": {"code": "<machine_string>", "message": "<human string>"}}`. RFC 7807 Problem Details is rejected as overkill for a localhost read API.
- **D-02:** Pagination is `limit`/`offset` query params with `meta.total` returned. Cursor pagination is the correct shape for log-tail data, but earns its keep only with SSE — defer to v1.4 alongside streaming push.
- **D-03:** Filter syntax on the HTTP API is plain query params — `?promoted=true&since=2026-04-01T00:00:00Z&tool=synth_*&code_hash=abcd1234`. The DF-1 structured query console (`tool:synth_* status:active`) is a Phase 10 UI-layer parser that translates token syntax into query params before calling `/api/v1/`. The API stays conventional; the UI owns the friendly grammar.
- **D-04:** Field naming is `snake_case` end-to-end (matches the existing `ExecutionRecord` shape, `_meta` keys, and JSONL on-disk format). No camelCase translation layer.
- **D-05:** Default `limit` is 50 when omitted; max enforced `limit` is 500. Requests with `limit > 500` are clamped silently and `meta.limit` reflects the clamped value.

### ExecutionLog snapshot retention

- **D-06:** `ExecutionLog` gains a `_records: collections.deque[ExecutionRecord]` with `maxlen` configurable via `FORGE_EXEC_SNAPSHOT_MAX` env var, default `10_000`. Records are appended in `record()` after the JSONL flush + storage callback fire, so the in-memory deque mirrors the canonical write order.
- **D-07:** `ExecutionLog.snapshot(limit, offset, since=None, promoted_only=False, tool=None)` reads from the deque only — never JSONL — to sidestep P-04 (partial-line race) and to keep `/api/v1/execs` O(1) per request.
- **D-08:** Replay on startup re-fills the deque from JSONL up to `maxlen` (newest records win when the file is larger than the bound). Documented contract: "the deque is the hot-path query surface; the JSONL on disk is canonical for full history."
- **D-09:** Promotion-only JSONL rows (the `{code_hash, promoted, timestamp}` shape from `mark_promoted()`) do NOT enter the deque — they mutate the existing record's `promoted` flag in-place if the hash is still in the deque, otherwise they are dropped from the snapshot view (full history still on disk).

### `forge-bridge` entry-point refactor

- **D-10:** `forge_bridge/__main__.py` is refactored to a Typer root in Phase 9. Bare `forge-bridge` continues to boot the MCP server (zero behavior change for existing users / Claude Desktop configs). `forge-bridge console` is registered as an empty subcommand group with a `--help` placeholder. Phase 11 fills the actual subcommands.
- **D-11:** This refactor lands as its OWN small plan (likely `09-XX-typer-entrypoint`) — separate from the API plan — so the diff is reviewable and the failure surface stays small. Acceptance: `forge-bridge` (no args) still boots MCP, `forge-bridge console --help` exits 0.
- **D-12:** STATE.md research flag re-affirmed: this is a Phase 9 design decision, not a Phase 11 surprise. Deferring forces Phase 11 to bundle "refactor entry point" + "implement 5 CLI subcommands" into a single PR — rejected.

### `/api/v1/health` depth and shape

- **D-13:** Phase 9 ships the FULL multi-service health shape, not a thin liveness placeholder. Phase 10 (HEALTH-01) and Phase 11 (HEALTH-02 + `console doctor` HEALTH-03) both consume the same body — locking the shape now means downstream templates and CLI rendering don't churn against a v9.1 schema bump.
- **D-14:** Response shape:
  ```json
  {
    "data": {
      "status": "ok|degraded|fail",
      "ts": "<ISO8601>",
      "version": "<forge_bridge.__version__>",
      "services": {
        "mcp": {"status": "ok|fail", "detail": "..."},
        "flame_bridge": {"status": "ok|fail", "url": "http://...:9999", "detail": "..."},
        "ws_server": {"status": "ok|fail", "url": "ws://...:9998", "detail": "..."},
        "llm_backends": [{"name": "ollama", "status": "ok|fail", "detail": "..."}, ...],
        "watcher": {"status": "ok|fail", "task_done": false, "detail": "..."},
        "storage_callback": {"status": "ok|absent", "registered": true, "detail": "..."},
        "console_port": {"status": "ok|fail", "port": 9996, "detail": "..."}
      },
      "instance_identity": {
        "execution_log": {"id_match": true, "detail": "..."},
        "manifest_service": {"id_match": true, "detail": "..."}
      }
    },
    "meta": {}
  }
  ```
- **D-15:** Top-level `status` aggregates: `ok` if all services ok, `degraded` if any non-critical (LLM, storage_callback) fail, `fail` if any critical (mcp, watcher, instance_identity) fail.
- **D-16:** `instance_identity` checks compare `id(execution_log_in_lifespan)` to `id(execution_log_in_console_read_api)` and same for `manifest_service`. Mismatch flips to FAIL with a clear message at server boot — catches LRN-05-class duplicate-instance bugs before the first artist UAT.
- **D-17:** Health checks are best-effort and bounded: each service check has a 2s timeout and short-circuits on first failure. The handler never blocks longer than `~ N_services * 2s` even when everything is offline.
- **D-18:** Storage-callback check is "registered or absent" — this is opt-in per API-05/STORE-06; absence is not a failure, and the field just reflects presence + (if registered) `isinstance(_persist_execution, StoragePersistence)`.

### Stdio safety enforcement (P-01)

- **D-19:** Belt-and-suspenders applied — P-01 has no graceful failure mode, so cheap defenses pay off forever.
- **D-20:** Custom `LOGGING_CONFIG` dict passed to `uvicorn.Config(log_config=LOGGING_CONFIG)`. Routes `uvicorn`, `uvicorn.access`, and `uvicorn.error` loggers through stdlib `logging` to stderr — never stdout. Disables uvicorn's default stdout `StreamHandler`.
- **D-21:** `access_log=False` on the uvicorn config. We don't need access logs in v1.3; surface request count via `/api/v1/health` if needed in v1.4.
- **D-22:** Lint gate added to `pyproject.toml` `[tool.ruff]` — ban `print(` in `forge_bridge/console/` and (post-Phase-11) `forge_bridge/cli/` via `per-file-ignores` inversion or a custom check. All console output uses `logger = logging.getLogger(__name__)`.
- **D-23:** Phase 9 SC#1 integration test is the runtime UAT — `tools/list` over MCP stdio while the console HTTP API is concurrently serving traffic on `:9996`. Test must assert the MCP wire is byte-clean (no extra bytes between framed messages).

### MCP resources + tool fallback shims

- **D-24:** Phase 9 ships ALL of: `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}` (URI template per RFC 6570), `forge://health`, `forge_manifest_read` tool, and `forge_tools_read(name: str | None = None)` tool. The tool shim is a single function that returns the list when `name is None` and the per-tool detail otherwise — keeps the surface small for Cursor / Gemini CLI clients that don't implement resources (P-03).
- **D-25:** Resources and tool shims read through the SAME `ConsoleReadAPI` methods that back the HTTP routes. No second read path. Verified by D-16 instance-identity check at boot.
- **D-26:** All resources return `application/json` MIME type. Resource bodies are byte-identical to the corresponding `/api/v1/` HTTP response payloads (envelope and all) — same serializer, same shape. Spec: "MCP resource for tool X is the read of HTTP route X."

### Console port configuration

- **D-27:** Port precedence: `--console-port` flag > `FORGE_CONSOLE_PORT` env > default `9996`. Standard Unix convention. Flag is on the bare `forge-bridge` invocation, not under the `console` subcommand group (since the subcommand group is for CLI client commands, not server config).
- **D-28:** Bind address is `127.0.0.1` only — locked non-goal in REQUIREMENTS.md ("Non-local network access — console is localhost-bound"). Not configurable in v1.3.
- **D-29:** Graceful degradation per API-06 — if `:9996` (or the configured port) is unavailable, the uvicorn task logs WARNING and the MCP server continues to boot. Mirrors the v1.2.1 `startup_bridge` pattern. The `_lifespan` handler awaits a short startup signal from the uvicorn task; failure to bind is logged but not raised.

### `_lifespan` task lifecycle

- **D-30:** `_lifespan` owns three independent asyncio tasks — `watcher_task`, `console_task` (uvicorn), and the existing bridge client. Failure of any one logs WARNING and does not cancel the others. Independent supervision per task.
- **D-31:** Order of operations in `_lifespan` startup: (1) `startup_bridge()`, (2) instantiate `ManifestService` + canonical `ExecutionLog`, (3) launch `watcher_task` with `manifest_service` injected, (4) build `ConsoleReadAPI(execution_log=..., manifest_service=...)`, (5) build console Starlette app + `register_console_resources(mcp, manifest_service, console_read_api)`, (6) launch `console_task`. Teardown reverses.

### Claude's Discretion

- Exact `ConsoleReadAPI` method signatures (kwargs, return types) — research recommends `get_tools()`, `get_executions(limit, since, promoted_only)`, `get_manifest()`, `get_health()`; planner can refine based on Starlette handler ergonomics.
- Internal package layout under `forge_bridge/console/` — research suggests `manifest_service.py`, `read_api.py`, `app.py`, `resources.py`; planner can split or merge as fits.
- Whether the Starlette app uses `Route()` lists or `@app.route` decorators — pick whichever the FastMCP-bundled Starlette idiom favors.
- CORS middleware decision — Phase 10 Web UI is same-origin (served from `:9996`), so CORS is not strictly required. Default to `CORSMiddleware` configured with `allow_origins=["http://127.0.0.1:9996", "http://localhost:9996"]` so a developer hitting the API from another tab doesn't get blocked. Not security — localhost only — convenience.
- Watcher injection signature for `ManifestService` — backward-compatible default `manifest_service: ManifestService | None = None` per research; planner confirms.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 9 inputs (locked decisions and requirements)
- `.planning/PROJECT.md` — v1.3 milestone scope, locked non-goals (no auth, no admin, no streaming, no `LLMRouter` hot-reload, no shared-path JSONL writers), key design decisions through Phase 8
- `.planning/REQUIREMENTS.md` — REQ-IDs API-01..06, MFST-01/02/03/06, TOOLS-04, EXECS-04 with full acceptance text and traceability
- `.planning/ROADMAP.md` §"Phase 9: Read API Foundation" — five success criteria the phase must satisfy
- `.planning/STATE.md` §"Session Handoff" — v1.3 implementation constraints (uvicorn task pattern locked, ConsoleReadAPI as sole read path, ManifestService singleton, MFST-02/03 same plan, instance-identity gate, jinja2 only new dep, Typer sync constraint)
- `.planning/research/SUMMARY.md` — full v1.3 research synthesis with HIGH confidence; conflict resolution between STACK.md and ARCHITECTURE.md/PITFALLS.md on `:9996` separate-uvicorn-task pattern
- `.planning/research/ARCHITECTURE.md` — `forge_bridge/console/` package layout, `ManifestService` + `ConsoleReadAPI` component boundaries, `_lifespan` wiring sequence
- `.planning/research/PITFALLS.md` — P-01 (stdout corruption), P-02 (transport switch), P-03 (resource client incompatibility), P-04 (JSONL partial-line), P-09 (CLI vs Web UI drift)
- `.planning/research/STACK.md` — Starlette/uvicorn/Typer transitive availability via `mcp[cli]`, Typer 0.24.1 sync constraint, `mcp==1.26.0` resource decorator verification
- `.planning/research/FEATURES.md` — TS-A/E/L feature scope and DF-1/2/3/4 differentiators

### Carried-forward v1.2 context (foundation)
- `.planning/milestones/v1.2-ROADMAP.md` — Phase 7/07.1/8 outcomes, the `_lifespan` pattern that Phase 9 extends, the v1.2.1 graceful-degradation precedent that Phase 9 mirrors for `:9996`
- `.planning/phases/v1.2-phases/08-sql-persistence-protocol/08-CONTEXT.md` — STORE-06 ("JSONL is canonical, SQL is mirror") and the LRN-05 lesson that drives Phase 9's instance-identity gate

### Codebase touchpoints
- `forge_bridge/__main__.py` — Typer-root refactor target (D-10/11)
- `forge_bridge/mcp/server.py` — `_lifespan` extension target (D-30/31), existing `startup_bridge`/`shutdown_bridge` graceful-degradation pattern to mirror
- `forge_bridge/learning/execution_log.py` — `snapshot()` + bounded deque addition (D-06..09); `set_storage_callback` already exists (Phase 6 LRN-02, instance-identity-gated by Phase 8 LRN-05)
- `forge_bridge/learning/watcher.py` — `manifest_service` kwarg injection point (Claude discretion)
- `forge_bridge/__init__.py` — barrel re-export updates if `ManifestService`/`ConsoleReadAPI` join `__all__` (planner decision; minor version bump applies if so)
- `pyproject.toml` — no new pip deps in Phase 9 (jinja2 lands in Phase 10); Typer entrypoint already wired via `[project.scripts]`

### MCP / FastMCP / Spec
- MCP Specification 2025-06-18 — Resources section (URI template syntax per RFC 6570, MIME types)
- FastMCP docs (`@mcp.resource()` decorator, resource template parameters) — verified against `mcp==1.26.0`
- MCP Tool Annotations as Risk Vocabulary (2026-03-16) — relevant for the tool-shim safety baseline

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`forge_bridge/mcp/server.py` `_lifespan`** — already an `@asynccontextmanager` running `startup_bridge` + `watcher_task`. Phase 9 extends with `console_task` + `ManifestService` instantiation. The cancel-on-exit pattern is reusable.
- **`forge_bridge/mcp/server.py` `startup_bridge` graceful-degradation pattern** — exactly the shape Phase 9 needs for the `:9996` console task per API-06. Mirror the try/except + WARNING log + don't-raise contract.
- **`forge_bridge/learning/execution_log.py` `ExecutionLog`** — already maintains `_code_by_hash`, `_intent_by_hash`, `_counters`, `_promoted` in memory. The `_records` deque (D-06) is a small additive change that integrates cleanly with the existing `record()` write path.
- **`forge_bridge/learning/execution_log.py` `set_storage_callback` + sync/async dispatch detection** — already in place from Phase 6 LRN-02 with the Phase 8 LRN-05 hook installation. No changes for Phase 9; health endpoint just reads `self._storage_callback is not None`.
- **`forge_bridge/llm/router.py` `LLMRouter.health()`** — already exists per `forge://llm/health` resource (Phase 1). Health endpoint reuses it directly for the `llm_backends` field.
- **`forge_bridge/learning/watcher.py`** — already publishes tool registration via `mcp.add_tool()` after manifest validation. Adding `manifest_service.register()` after the existing `register_tool` call is additive and keeps the manifest in sync without restructuring.
- **`forge_bridge/learning/sanitize.py` `_sanitize_tag` + `apply_size_budget`** — already gates consumer-supplied tag rendering (Phase 7 PROV-03). Phase 9 reuses these on the read path before serializing to JSON; no new sanitizer needed.

### Established Patterns

- **Async context-manager `_lifespan`** — FastMCP's documented lifecycle hook; Phase 9 stays within this pattern, no new lifecycle abstraction.
- **`asyncio.create_task` + cancel-on-exit** — pattern used for `watcher_task` already; identical pattern applies to `console_task`.
- **Env-var-then-default config (`os.environ.get(..., default)`)** — used throughout `startup_bridge`, `ExecutionLog`, `LLMRouter`. Phase 9's `FORGE_CONSOLE_PORT` and `FORGE_EXEC_SNAPSHOT_MAX` follow the same shape.
- **Frozen dataclasses for wire/storage records** — `ExecutionRecord` is `@dataclass(frozen=True)`. New `ToolRecord` (for `ManifestService`) follows the same pattern.
- **JSONL append + `fcntl.LOCK_EX` for write safety** — Phase 9 doesn't write JSONL; it only adds an in-memory mirror, so the existing pattern is preserved unchanged.
- **Logger-per-module via `logging.getLogger(__name__)`** — universal in the codebase. D-22 grep gate for `print(` enforces this for the new console package.

### Integration Points

- **`forge_bridge/mcp/server.py` `_lifespan`** — adds `ManifestService` instantiation, watcher injection, console uvicorn task launch, `register_console_resources` call. Sequence locked by D-31.
- **`forge_bridge/learning/watcher.py` `watch_synthesized_tools` signature** — gains `manifest_service: ManifestService | None = None` (backward-compatible default).
- **`forge_bridge/learning/execution_log.py` `ExecutionLog.__init__` and `record`** — gains `_records` deque + bounded replay; `record()` appends after JSONL flush + callback fire.
- **`forge_bridge/__main__.py`** — Typer-root refactor (D-10/11); bare invocation behavior unchanged.
- **`forge_bridge/__init__.py`** — likely re-exports `ManifestService`, `ToolRecord`, `ConsoleReadAPI` (planner decision; if so, minor version bump ceremony applies — `__all__` grows from 16 toward ~18-19).
- **`pyproject.toml`** — `[tool.ruff]` lint gate addition (D-22). No dependency changes in Phase 9.

</code_context>

<specifics>
## Specific Ideas

- **"Belt-and-suspenders" framing for stdio safety** — P-01 has no graceful failure mode (corrupted stdout silently disconnects MCP clients with no log line), so the cost of `LOGGING_CONFIG` + `access_log=False` + ruff gate + integration test is well-spent. This is the Phase 9 risk that justifies extra rigor.
- **Health endpoint as self-test** — `instance_identity` field is a runtime LRN-05 detector. If `id(execution_log_in_lifespan) != id(execution_log_in_console_read_api)`, health flips to FAIL at boot with a clear message. Catches duplicate-instance bugs before the first artist UAT.
- **Conventional API, friendly UI** — the HTTP API stays plain (snake_case, `?promoted=true&since=...`). The DF-1 structured query console (`tool:synth_* status:active`) is a Phase 10 UI parser concern. Don't conflate the two layers.
- **MCP resource = HTTP route, byte-identical** — `forge://manifest/synthesis` returns the exact same JSON bytes as `GET /api/v1/manifest`. Same serializer, same envelope, same fields. Spec it as "the resource is the read of the route." Removes any "is the manifest the same in both places?" ambiguity for downstream LLM agents.
- **Single `forge_tools_read(name=None)` shim, not two** — covers both `/tools` (list) and `/tools/{name}` (detail) for clients that lack resources. Smaller surface; one function to keep aligned with the read API.

</specifics>

<deferred>
## Deferred Ideas

- **Cursor pagination on `/api/v1/execs`** — earns its keep with SSE/WebSocket streaming; revisit alongside v1.4 push-update work.
- **RFC 7807 Problem Details error envelope** — overkill for a localhost read API. Reconsider if/when console moves off localhost (would pair with the auth milestone).
- **CORS configurability** — fixed allow-list of `127.0.0.1:9996` + `localhost:9996` in v1.3; broader policy waits on the auth milestone.
- **Storage-callback details exposed via `/api/v1/health`** — only "registered or absent" in Phase 9. Detailed adapter health (last-write timestamp, error counts) is a v1.4 idea, paired with EXT-04-class metrics.
- **Promotion-event mirror in the in-memory deque** — promotion-only JSONL rows mutate-in-place if the hash is in the deque, otherwise drop. A future "show me the full promotion timeline" view would read JSONL, not deque.
- **Real-time push (SSE) for execs/manifest/health** — locked v1.4 deferral per REQUIREMENTS.md.
- **`forge://tools/{name}` etag/cache-control headers** — useful when many MCP clients poll; defer until measurable.

</deferred>

---

*Phase: 09-read-api-foundation*
*Context gathered: 2026-04-22*
