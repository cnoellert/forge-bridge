---
phase: 9
slug: read-api-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio (`asyncio_mode = "auto"` per existing pyproject) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing; no changes needed) |
| **Quick run command** | `pytest tests/test_console_*.py tests/test_manifest_service.py tests/test_typer_entrypoint.py -x -q` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~30-60 seconds (quick) / ~2-3 min (full, including MCP-stdio subprocess integration tests) |
| **MCP stdio test vehicle** | `tests/test_mcp_server_graceful_degradation.py` pattern — extend for SC#1 stdio-cleanliness test |
| **Lint gate** | `ruff check forge_bridge/console/` (T20 rules — bans `print(`) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_console_*.py tests/test_manifest_service.py tests/test_typer_entrypoint.py -x -q` (fast feedback, ~30s)
- **After every plan wave:** `pytest tests/` (full suite — includes v1.0-v1.2 regression baselines)
- **Before `/gsd-verify-work`:** Full suite green + SC#1 manual UAT (MCP client against stdio while curling `:9996`) + SC#2/3 manual MCP-client UAT
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Task IDs are placeholders — the planner fills `{plan}-{task}` cells once PLAN.md files exist. Every REQ-ID below MUST map to at least one task in a `requirements:` frontmatter list.

| Req / SC | Plan (TBD) | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|----------|------------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| API-01 | 09-XX | TBD | API-01 | — | `ConsoleReadAPI` methods return correct data in isolation | unit (mock deps) | `pytest tests/test_console_read_api.py -x` | ❌ W0 | ⬜ pending |
| API-02 | 09-XX | TBD | API-02 | — | Console HTTP API serves on `:9996` while MCP runs stdio | integration (real uvicorn + real FastMCP subprocess) | `pytest tests/test_console_http_transport.py -x` | ❌ W0 | ⬜ pending |
| API-03 | 09-XX | TBD | API-03 | — | `/tools`, `/execs`, `/manifest`, `/health` return envelope JSON | integration (httpx TestClient + Starlette) | `pytest tests/test_console_routes.py -x` | ❌ W0 | ⬜ pending |
| API-04 | 09-XX | TBD | API-04 | — | Instance-identity gate: live `bridge.execute()` visible in `/api/v1/execs` | integration (real MCP + real callback wire) | `pytest tests/test_console_instance_identity.py -x` | ❌ W0 | ⬜ pending |
| API-05 | 09-XX | TBD | API-05 | — | `/health.services.storage_callback` reflects registered vs absent | unit | `pytest tests/test_console_health.py::test_storage_callback_reflects_registration -x` | ❌ W0 | ⬜ pending |
| API-06 | 09-XX | TBD | API-06 | T-9-1 (port-unavailable misleading error) | Port unavailable → WARNING log + MCP still boots | integration (occupy :9996 first) | `pytest tests/test_console_port_degradation.py -x` | ❌ W0 | ⬜ pending |
| MFST-01 | 09-XX | TBD | MFST-01 | — | `ManifestService.register()` writes visible to `get_all()` (asyncio.Lock) | unit | `pytest tests/test_manifest_service.py -x` | ❌ W0 | ⬜ pending |
| MFST-02 | 09-XX | TBD | MFST-02 | — | `forge://manifest/synthesis` returns manifest JSON | integration (real MCP stdio client) | `pytest tests/test_console_mcp_resources.py::test_manifest_resource -x` | ❌ W0 | ⬜ pending |
| MFST-03 | 09-XX | TBD | MFST-03 | — | `forge_manifest_read` tool payload byte-identical to resource | integration (real MCP, `tools/call`) | `pytest tests/test_console_mcp_resources.py::test_manifest_tool_shim_byte_identical -x` | ❌ W0 | ⬜ pending |
| MFST-06 | 09-XX | TBD | MFST-06 | — | `/api/v1/manifest` == `forge://manifest/synthesis` == `forge_manifest_read` bytes | integration (cross-surface byte-diff) | `pytest tests/test_console_mcp_resources.py::test_manifest_cross_surface_byte_identity -x` | ❌ W0 | ⬜ pending |
| TOOLS-04 | 09-XX | TBD | TOOLS-04 | — | `forge://tools`, `forge://tools/{name}`, `forge_tools_read(name=None)` all functional | integration | `pytest tests/test_console_mcp_resources.py::test_tools_resources_and_shim -x` | ❌ W0 | ⬜ pending |
| EXECS-04 | 09-XX | TBD | EXECS-04 | — | `/api/v1/execs` and `ConsoleReadAPI.get_executions()` identical for same state | unit | `pytest tests/test_console_read_api.py::test_execs_shared_read_path -x` | ❌ W0 | ⬜ pending |
| **SC#1** | 09-XX | TBD | (criterion) | T-9-2 (stdout corruption) | MCP stdio `tools/list` clean while `:9996` serves concurrent GETs | integration (real subprocess MCP + concurrent httpx) | `pytest tests/test_console_stdio_cleanliness.py -x` | ❌ W0 (CRITICAL P-01 test) | ⬜ pending |
| **SC#3** | 09-XX | TBD | (criterion) | — | Live `bridge.execute()` record visible via `/api/v1/execs` immediately | integration | `pytest tests/test_console_instance_identity.py::test_execute_appears_in_execs -x` | ❌ W0 | ⬜ pending |
| **SC#4** | 09-XX | TBD | (criterion) | T-9-1 | Occupied `:9996` → WARNING + MCP boots + `tools/list` works | integration | `pytest tests/test_console_port_degradation.py -x` | ❌ W0 | ⬜ pending |
| **SC#5** | 09-XX | TBD | (criterion) | — | Existing integration tests pass unchanged (no `--http`) | regression | `pytest tests/test_mcp_server_graceful_degradation.py tests/test_e2e.py -x` | ✅ (existing) | ⬜ pending |
| **D-22** | 09-XX | TBD | (decision) | T-9-3 (print() leak) | `ruff check forge_bridge/console/` fails on `print(` | lint | `ruff check forge_bridge/console/` | ❌ W0 (config addition) | ⬜ pending |
| **D-10/11** | 09-XX | TBD | (decision) | — | Bare `forge-bridge` boots MCP; `forge-bridge console --help` exits 0 | integration (subprocess) | `pytest tests/test_typer_entrypoint.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 is the test-fixture wave that MUST land before per-feature execution so sampling works from task #1 onward.

- [ ] `tests/test_console_read_api.py` — unit tests for `ConsoleReadAPI.get_tools/get_tool/get_executions/get_manifest/get_health` against mocked `ManifestService` and `ExecutionLog`
- [ ] `tests/test_manifest_service.py` — unit tests for `ManifestService.register/remove/get_all/get` including `asyncio.Lock` concurrency
- [ ] `tests/test_console_http_transport.py` — Starlette `TestClient` + `_start_console_task` helper under `pytest-asyncio`
- [ ] `tests/test_console_routes.py` — per-route envelope shape, pagination clamping (D-05), CORS preflight
- [ ] `tests/test_console_health.py` — D-14 shape assertion, D-15 aggregation, D-17 2s timeout bounds
- [ ] `tests/test_console_instance_identity.py` — real `_lifespan` + real `bridge.execute()` + `/api/v1/execs` round-trip (API-04 gate)
- [ ] `tests/test_console_port_degradation.py` — occupy `:9996` via secondary `socket.bind()` before test, assert WARNING logged + MCP boots (API-06)
- [ ] `tests/test_console_mcp_resources.py` — spawn real MCP server subprocess, connect via stdio client; exercise `resources/list`, `resources/read forge://...`, `tools/call forge_manifest_read`, assert byte-identity (D-26). Mirror Phase 07.1 UAT evidence protocol.
- [ ] `tests/test_console_stdio_cleanliness.py` — **critical P-01 test:** spawn MCP subprocess, stdio client, issue 100 concurrent httpx GETs to `:9996`, then issue MCP `tools/list`, assert response framed correctly
- [ ] `tests/test_typer_entrypoint.py` — subprocess invocation of `forge-bridge`, `forge-bridge --console-port 9997`, `forge-bridge console --help`, assert exit codes + behavior
- [ ] `pyproject.toml` — add `[tool.ruff.lint] extend-select = ["T20"]` with per-file carve-outs outside `forge_bridge/console/` (D-22)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude Desktop / Cursor end-to-end UAT with live synthesized tools | SC#2 (resource=tool=route byte-identity as seen by a real client) | Third-party MCP client verifies wire integrity from a consumer perspective; impossible to fully simulate in pytest | Launch `forge-bridge` via Claude Desktop config. Open Claude Desktop. Ask it to call `forge_manifest_read`. Verify response matches `curl http://127.0.0.1:9996/api/v1/manifest`. |
| Artist-facing dogfood (per user memory: non-developer UAT required on every UI phase) | v1.3 UX philosophy | This phase has no UI (Phase 10 ships UI) — **N/A for Phase 9**; artist UAT belongs to Phase 10 onward | — |
| Concurrent stdio + HTTP soak under real working conditions | SC#1 (post-automated-test manual confirmation) | Integration test covers 100 GETs; manual soak covers a real hour-long session | `forge-bridge` running under Claude Desktop. Leave session open for ≥1 hour while hammering `:9996` via browser refresh on `/api/v1/execs`. Verify no MCP disconnects and no stdout corruption events in logs. |

*Dogfood UAT is not applicable in Phase 9 (backend-only); Phase 10 picks up that obligation per user's forge-bridge UX philosophy memory.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all ❌ rows in Per-Task Verification Map
- [ ] No watch-mode flags (`pytest-watch`, `--looponfail`) in any `<automated>` command
- [ ] Feedback latency < 60s for quick run, < 3min for full suite
- [ ] `nyquist_compliant: true` set in frontmatter once planner completes task mapping and Wave 0 task IDs are backfilled

**Approval:** pending
