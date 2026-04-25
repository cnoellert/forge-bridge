# Phase 9: Read API Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `09-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 09-read-api-foundation
**Areas discussed:** API shape & retention, Entry-point refactor, Health endpoint depth, Stdio safety enforcement
**Mode:** Recommendation-led (user requested "would love to hear your recos") — Claude proposed strong recommendations with rationale; user locked all four as-is.

---

## Pre-discussion: Carried-forward decisions (not re-asked)

| Decision | Source |
|---|---|
| Separate uvicorn task on `:9996` inside `_lifespan`, NOT `FastMCP.custom_route` | STATE.md, research SUMMARY.md (P-01/P-02 prevention) |
| `ConsoleReadAPI` is the sole read path for every surface | API-01, REQUIREMENTS.md (LRN-05 lesson) |
| `ManifestService` singleton — watcher = sole writer, console = reader via `snapshot()` | MFST-01, REQUIREMENTS.md |
| MCP resource + tool fallback shim ship in the same plan | MFST-02 + MFST-03 (P-03 prevention) |
| Canonical `ExecutionLog` + `ManifestService` owned by `_lifespan` (instance-identity gate) | API-04 |
| Graceful degradation when `:9996` unavailable — log WARNING, MCP boots anyway | API-06 (mirrors v1.2.1 pattern) |
| `/api/v1/` namespace, JSON responses | API-03 |
| StoragePersistence read-adapter is opt-in; JSONL is canonical | API-05, STORE-06 |
| Stdio stays MCP default transport | P-02 prevention |
| Only new pip dep for the milestone is `jinja2>=3.1` (lands in Phase 10) | research STACK.md |

---

## Area 1: API response conventions, pagination, filters, retention

| Sub-decision | Options considered | Selected | Rationale |
|---|---|---|---|
| Response envelope | (a) Raw arrays/objects (b) `{data, meta}` envelope (c) RFC 7807 Problem Details | **(b) `{data, meta}` envelope** ✓ | Raw arrays bake in a ceiling — once Phase 10 needs `meta.total` for a paginated UI, the contract has to break. RFC 7807 is overkill for localhost. |
| Pagination | (a) `limit`/`offset` + `meta.total` (b) Cursor-based (c) No pagination | **(a) `limit`/`offset`** ✓ | Cursor is correct for log-tail data but earns its keep only with SSE — defer to v1.4. v1.3 is single-user localhost with bounded retention. |
| Filter syntax | (a) Plain query params (b) Structured DSL on the API (`?q=tool:foo status:active`) (c) POST body filter objects | **(a) Plain query params** ✓ | The DF-1 structured query console is a Phase 10 UI-layer parser that translates token syntax into query params. API stays conventional; UI owns the friendly grammar. |
| Field naming | (a) snake_case (b) camelCase (c) Mixed | **(a) snake_case** ✓ | Matches existing `ExecutionRecord`, `_meta` keys, JSONL on-disk format. No translation layer. |
| ExecutionLog retention strategy | (a) Bounded `deque(maxlen=N)` (b) Unbounded list (c) Re-read JSONL per query | **(a) Bounded deque, default 10k, env-overrideable** ✓ | Unbounded grows forever in long-lived MCP processes. JSONL re-read re-introduces P-04 (partial-line race) and is slower per request. 10k records ≈ a few MB; full history lives on disk. |
| Default/max page size | (a) default 50, max 500 (b) default 25, max 100 (c) no max | **(a) default 50, max 500 (clamped silently)** ✓ | Matches "default last 50" pattern from research; cap prevents runaway responses on a localhost-only service. |

**User's choice:** Locked recommendation as-is.

---

## Area 2: `forge-bridge` entry-point refactor — Phase 9 or Phase 11

| Option | Pros | Cons | Selected |
|---|---|---|---|
| **Defer to Phase 11** | Phase 9 stays scope-pure ("Read API Foundation") | Phase 11 PR balloons to "refactor entry point + implement 5 CLI subcommands"; touchpoint conflict risk during Phase 10 | |
| **Do in Phase 9 as its own small plan** ✓ | ~30 lines, near-zero risk; Phase 11 just adds subcommands; STATE.md research flag explicitly assigned this to Phase 9 | Adds one small plan to Phase 9 | ✓ |
| Bundle into the main API plan | Minimum plan count | Mixes architectural concerns; harder to review | |

**User's choice:** Locked recommendation as-is.

---

## Area 3: `/api/v1/health` depth for Phase 9

| Option | Pros | Cons | Selected |
|---|---|---|---|
| **Thin liveness now, full panel in Phase 10** | Smallest Phase 9 surface | Phase 10 templates and Phase 11 CLI both lock against whatever Phase 9 returns; growing the shape later forces template churn | |
| **Full multi-service shape in Phase 9** ✓ | Phase 10 + 11 both consume the same body — no schema bump churn; `instance_identity` field doubles as a runtime LRN-05 detector at boot | Adds health-check polling logic for ~7 services to Phase 9 | ✓ |
| Middle ground (status + a few critical checks) | Smaller surface than full | Still requires a schema bump in Phase 10; defeats the purpose | |

**Sub-decisions inside the locked option:**
- Aggregate status: `ok` / `degraded` (LLM, storage_callback fail) / `fail` (mcp, watcher, instance_identity fail)
- Service check timeout: 2s per service, short-circuit on first failure
- Instance-identity check: compare `id(execution_log_in_lifespan)` vs `id(execution_log_in_console_read_api)` (and same for `manifest_service`)
- Storage-callback field: "registered or absent" — absence is not a failure

**User's choice:** Locked recommendation as-is.

---

## Area 4: Stdio safety enforcement (P-01 prevention)

| Option | Pros | Cons | Selected |
|---|---|---|---|
| **Belt-and-suspenders** ✓ | Defense-in-depth on the most-cited risk in v1.3 research; near-zero cost | ~20 lines of `LOGGING_CONFIG` + one ruff rule + one integration test | ✓ |
| Lighter (just the SC#1 integration test + `access_log=False`) | Smaller surface | P-01 has no graceful failure mode — corrupted stdout silently disconnects MCP clients with no log line. Trusting review for `print()` audits is fragile. | |
| Defer logging discipline to a follow-on phase | Smallest Phase 9 surface | Defers the most dangerous failure mode of the milestone | |

**Components of the belt-and-suspenders approach:**
1. Custom `LOGGING_CONFIG` dict passed to `uvicorn.Config(log_config=...)` routing all uvicorn loggers to stderr via stdlib logging
2. `access_log=False` on the uvicorn config
3. Lint gate (`ruff` rule) banning `print(` in `forge_bridge/console/` (and post-Phase-11 `forge_bridge/cli/`)
4. Phase 9 SC#1 integration test: `tools/list` over MCP stdio while `:9996` is concurrently serving traffic — assert MCP wire byte-clean

**User's choice:** Locked recommendation as-is.

---

## Claude's Discretion (deferred to planning)

- Exact `ConsoleReadAPI` method signatures (kwargs, return types)
- Internal package layout under `forge_bridge/console/`
- Whether the Starlette app uses `Route()` lists or `@app.route` decorators
- CORS middleware configuration (default to `allow_origins=["http://127.0.0.1:9996", "http://localhost:9996"]` — convenience, not security)
- Watcher injection signature for `ManifestService` (backward-compatible default per research)

## Deferred Ideas

- Cursor pagination on `/api/v1/execs` — pair with v1.4 SSE/streaming
- RFC 7807 Problem Details error envelope — pair with auth milestone
- CORS configurability — pair with auth milestone
- Detailed storage-callback metrics in `/api/v1/health` — v1.4 EXT-04-class metrics
- Promotion-event mirror in the in-memory deque — read JSONL for full timeline
- Real-time SSE push — locked v1.4 deferral
- `forge://tools/{name}` etag/cache-control headers — defer until measurable polling load
