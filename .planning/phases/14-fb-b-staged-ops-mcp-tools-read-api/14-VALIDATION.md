---
phase: 14
slug: fb-b-staged-ops-mcp-tools-read-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `14-RESEARCH.md` §Validation Architecture (lines 895-1066).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with `pytest-asyncio` (`asyncio_mode = "auto"`, verified at `pyproject.toml:71`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) — pythonpath includes repo root |
| **Quick run command** | `pytest tests/test_staged_operations.py tests/console/test_staged_handlers_*.py tests/mcp/test_staged_tools.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~30s quick (Postgres-equipped); ~4-5 min full suite (~660 cases as of Phase 13 close) |
| **Postgres requirement** | Phase 13 fixture skips cleanly without Postgres (`_phase13_postgres_available()` probe at `tests/conftest.py:120-133`); FB-B handler tests inherit this behavior |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_staged_operations.py tests/console/test_staged_handlers_*.py tests/mcp/test_staged_tools.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green; human verification with Postgres at `localhost:5432` confirms 0 skipped (Phase 13 precedent)
- **Max feedback latency:** ~30 seconds (quick), ~5 min (full)

---

## Per-Task Verification Map

> Plan IDs are placeholders (14-01..14-05) and will be authoritative after the planner runs. Test commands here are derived from RESEARCH.md §Phase Requirements → Test Map.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-* | 01 (StagedOpRepo.list + WR-01 fix) | 1 | STAGED-05/06/07 | T-14-01 / — | Repo `list()` SQL filter + clamp + ordering correct | unit | `pytest tests/test_staged_operations.py -x -k list` | ❌ W0 | ⬜ pending |
| 14-02-* | 02 (ConsoleReadAPI + lifespan wiring) | 1 | STAGED-05/06/07 | T-14-02 / — | `session_factory` injected once at `_lifespan`; no leakage into reads | unit | `pytest tests/test_console_handlers.py::test_read_api_session_factory -x` | ❌ W0 | ⬜ pending |
| 14-03-* | 03 (HTTP routes + handlers) | 2 | STAGED-06 | T-14-03 / `bad_actor`, `illegal_transition`, `staged_op_not_found`, `bad_request`, `invalid_filter`, `internal_error` | All error mappings in D-10 emit byte-identical envelopes via `_envelope_json` | integration | `pytest tests/console/test_staged_handlers_*.py -x` | ❌ W0 | ⬜ pending |
| 14-04-* | 04 (MCP tools + registration) | 2 | STAGED-05 | T-14-04 / Pydantic-rejected empty actor (D-07) | Four `forge_*_staged` tools register with correct annotations (D-16) and call same write path as HTTP | integration | `pytest tests/mcp/test_staged_tools.py -x` | ❌ W0 | ⬜ pending |
| 14-05-* | 05 (resource + shim + zero-divergence + does-not-execute) | 3 | STAGED-07 | T-14-05 / D-21 negative assertion | `forge://staged/pending` matches `forge_list_staged(status='proposed', limit=500)` byte-for-byte; approval emits `staged.approved` without invoking execution | integration | `pytest tests/test_console_mcp_resources.py::test_staged_pending_resource_matches_list_tool tests/console/test_staged_zero_divergence.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Test directories and stub files that MUST exist before non-trivial implementation tasks run:

- [ ] `tests/console/__init__.py` — empty marker (currently absent — flat `tests/` layout)
- [ ] `tests/mcp/__init__.py` — empty marker (currently absent)
- [ ] `tests/console/test_staged_handlers_list.py` — list-handler stubs (STAGED-06 list/filter/pagination/error cases)
- [ ] `tests/console/test_staged_handlers_writes.py` — approve/reject handler stubs (STAGED-06 lifecycle + error matrix)
- [ ] `tests/console/test_staged_zero_divergence.py` — D-19 byte-identity stubs + D-21 does-not-execute negative assertion
- [ ] `tests/mcp/test_staged_tools.py` — D-18 MCP tool integration stubs (4 tools × happy-path + at least one error)
- [ ] `tests/test_console_mcp_resources.py` — extended (existing file) with `test_staged_pending_resource_matches_list_tool`

**Reused fixtures (no Wave 0 work needed):**
- `session_factory` async-DB fixture (Plan 13-04 deliverable, `tests/conftest.py:136-199`) — drop-in for both `tests/console/` and `tests/mcp/` test modules
- `_ResourceSpy` byte-identity helper (`tests/test_console_mcp_resources.py:50-72`) — extends to `forge://staged/pending`
- `_phase13_postgres_available()` probe (`tests/conftest.py:120-133`) — graceful skip when Postgres absent

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real MCP-client session calls all four `forge_*_staged` tools | STAGED-05 success criterion #1 | "Real MCP client session" requires wire-protocol exchange against a live FastMCP server; D-18 test harness automates this but human dogfood confirms the registry surface is discoverable | Boot `python -m forge_bridge`, connect Claude Code MCP client, run `forge_list_staged status=proposed`, `forge_get_staged id=<uuid>`, `forge_approve_staged id=<uuid> actor=mcp:claude-code`, `forge_reject_staged id=<uuid> actor=mcp:claude-code` — confirm each returns expected JSON envelope. Verify `forge://staged/pending` resource appears in client resource list. |
| projekt-forge v1.5 dependency contract holds | Cross-repo (FB-A..FB-D alias surface) | Requires projekt-forge v1.5 codebase to actually subscribe to `staged.approved` — out-of-scope for forge-bridge tests | Run forge-bridge MCP server locally; in projekt-forge v1.5 dev env, propose a stage op, confirm projekt-forge's event-bus subscription fires on approval. (Deferrable until projekt-forge v1.5 ships its consumer.) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (5 new test files + 2 `__init__.py` markers)
- [ ] No watch-mode flags (pytest `-x` is fail-fast, not watch)
- [ ] Feedback latency < 30s (quick suite)
- [ ] `nyquist_compliant: true` set in frontmatter (after planner finalizes plan IDs and the per-task verification map's "Test Type" / "Automated Command" cells map 1:1 to PLAN.md tasks)

**Approval:** pending — awaiting planner output and final task-ID assignment
