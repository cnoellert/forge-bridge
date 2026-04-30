# Phase 18: Staged-handlers test harness rework - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning (baseline complete, D-05)
**Milestone:** v1.4.x Carry-Forward Debt
**Requirements:** HARNESS-01, HARNESS-02, HARNESS-03

<domain>
## Phase Boundary

Phase 18 delivers three isolated commits to `tests/` that turn 26 silently-skipping staged-ops tests into 25 actually-running, actually-passing tests against live Postgres on dev (`:7533/forge_bridge`). 1 of the 26 is a pre-existing test logic bug deferred to POLISH-03 (Phase 19) — see D-07. Root causes were triaged during v1.4 close-out and recorded in the `v1.4.x test-harness debt` memory; this phase converts that triage into landed code:

- **HARNESS-01 (test-client migration):** Swap `tests/console/conftest.py::staged_client` from `starlette.testclient.TestClient` (sync wrapper) to `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")` so the test event loop matches asyncpg's session loop. Adds `await` to the 23 call sites across `tests/console/test_staged_handlers_writes.py` (11), `tests/console/test_staged_handlers_list.py` (7), and `tests/console/test_staged_zero_divergence.py` (5). Tests are already `async def` and pytest-asyncio is in `auto` mode — no decorator churn. Eliminates `RuntimeError: got Future <Future pending ...> attached to a different loop`. After fix: 22/23 pass; 1 (`test_staged_list_filter_by_project_id`) fails with FK violation closed by HARNESS-02.
- **HARNESS-02 (Project FK seeding):** Introduce a new `seeded_project` `@pytest_asyncio.fixture` in `tests/conftest.py` that inserts a `DBProject` row using the `session_factory` and yields its UUID. Wire it into 3 FK-violating tests — 2 in `tests/test_staged_operations.py` (`test_staged_op_list_filter_by_project_id`, `test_staged_op_list_combined_filter`) and 1 in `tests/console/test_staged_handlers_list.py` (`test_staged_list_filter_by_project_id`, surfaced after HARNESS-01 lifts the loop-conflict mask). Each replaces inline `uuid.uuid4()` project_id with the fixture-provided id. Eliminates `entities_project_id_fkey` violations. **Note (D-07):** the 3rd test originally listed in the `v1.4.x test-harness debt` memory — `test_transition_atomicity` — is NOT an FK violation. Empirical baseline shows it fails with a pre-existing assertion bug (line 388 contradicts SQLAlchemy/Postgres rollback semantics). Deferred to POLISH-03 (Phase 19).
- **HARNESS-03 (gate removal + teardown fix):** Remove the `FORGE_TEST_DB=1` env-var gate from `_phase13_postgres_available()` in `tests/conftest.py:120-157`. Probe always honors `urlparse(FORGE_DB_URL).hostname/.port` when set, falls back to `localhost:5432` when unset, returns False (silent skip) on `OSError`. Also folds in a teardown fix: wrap the `pg_terminate_backend` SQL in `try/except InsufficientPrivilegeError` at `tests/conftest.py:218`, since the `forge` role on dev Postgres is not SUPERUSER and the current teardown produces transient ERRORs (1/47 in baseline).

**No production source files are touched.** The diff scope is `tests/conftest.py`, `tests/console/conftest.py`, `tests/console/test_staged_handlers_writes.py`, `tests/console/test_staged_handlers_list.py`, `tests/console/test_staged_zero_divergence.py`, and `tests/test_staged_operations.py` (2 specific tests in the last file). Phase 13/14 source code is verified-correct via Phase 16.2 live UAT — the harness is what was broken, not the handlers.

**Out of scope (deferred to v1.5):** `_OLLAMA_TOOL_MODELS` allow-list audit; SEED-CHAT-STREAMING-V1.4.x (trigger condition not surfaced); CI matrix job adding a Postgres service container; cross-host (assist-01) staged-ops UAT replication. All in `<deferred>` below.

</domain>

<decisions>
## Implementation Decisions

### Commit structure (D-30 isolated-commit mandate)

- **D-01:** Three plans, three commits, one per HARNESS requirement. Mirrors Phase 17's D-30 precedent. Per-file commits across HARNESS-01 (option 1b) was rejected as artificial fragmentation. Single bulk commit (option 1c) was rejected because it conflates the loop fix with the FK fix with the gate removal.
  - **P-01: HARNESS-01** — `staged_client` fixture body swap + 23 call-site `await` additions across the 3 console test files. One commit.
  - **P-02: HARNESS-02** — `seeded_project` fixture in `tests/conftest.py` + wiring into 2 store-layer FK tests in `tests/test_staged_operations.py` AND 1 console FK test in `tests/console/test_staged_handlers_list.py`. One commit.
  - **P-03: HARNESS-03** — Remove the `FORGE_TEST_DB=1` gate from `_phase13_postgres_available()` AND wrap the `pg_terminate_backend` teardown SQL in `try/except InsufficientPrivilegeError`. One commit. Sequenced LAST per memory ("Once 1+2 are done, flip back to opt-in-by-default") — landing P-03 before P-01+P-02 would expose the failures in default-CI runs that have `FORGE_DB_URL` set.

### TestClient → AsyncClient migration approach

- **D-02:** Swap the fixture body in `tests/console/conftest.py:25-39` to:
  ```python
  @pytest_asyncio.fixture
  async def staged_client(session_factory):
      ms = ManifestService()
      mock_log = MagicMock()
      mock_log.snapshot.return_value = ([], 0)
      api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms, session_factory=session_factory)
      app = build_console_app(api, session_factory=session_factory)
      transport = ASGITransport(app=app)
      async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
          yield client
  ```
  Then add `await` at the 23 call sites: `r = await staged_client.post(...)`, `r = await staged_client.get(...)`, etc. The response object's surface (`r.status_code`, `r.json()`, `r.headers`) is identical between `starlette.testclient.TestClient` and `httpx.AsyncClient` — no body changes beyond `await`. Wrapper-class shim (option 3b) was rejected as long-term abstraction debt. `anyio.from_thread.run` hybrid (option 3c) was rejected as obscuring async semantics.

### Project FK seeding strategy

- **D-03:** New `seeded_project` fixture in `tests/conftest.py` (NOT auto-seed in `session_factory`, NOT lazy-create inside `proposed_op`). Skeleton:
  ```python
  @_phase13_pytest_asyncio.fixture
  async def seeded_project(session_factory):
      """Insert one DBProject row and yield its UUID. For tests that need a real
      parent project for staged_operation rows that carry project_id."""
      from forge_bridge.store.models import DBProject
      async with session_factory() as session:
          proj = DBProject(name="harness-test-project", code="HARNESS")
          session.add(proj)
          await session.commit()
          await session.refresh(proj)
          yield proj.id
  ```
  Three FK-violating tests need wiring: `tests/test_staged_operations.py::test_staged_op_list_filter_by_project_id`, `::test_staged_op_list_combined_filter` (both need TWO distinct project ids — second project gets seeded inline in the test body, OR fixture is parameterized to yield N ids; planner picks); and `tests/console/test_staged_handlers_list.py::test_staged_list_filter_by_project_id` (also needs two ids in its seed phase). Auto-seed in `session_factory` (option 2a) was rejected (couples unrelated tests). Lazy-create inside `proposed_op` factory (option 2c) was rejected (hides the requirement). Surgical fixture is the most readable path.

### HARNESS-03 gate-removal semantics + teardown fix

- **D-04:** Two test-conftest.py edits in one commit:

  **(a) Gate removal at `_phase13_postgres_available()`:** always honors `FORGE_DB_URL` host/port if set, falls back to `localhost:5432` if unset, returns False (silent skip) on `OSError`. NO loud failure when `FORGE_DB_URL` is set-but-unreachable (option 4b/4c rejected) — silent-skip is the v1.4-close-state CI contract. Final shape:
  ```python
  def _phase13_postgres_available() -> bool:
      import socket
      from urllib.parse import urlparse
      url = _phase13_os.environ.get("FORGE_DB_URL", "")
      if url:
          scheme, _, rest = url.partition("://")
          scheme = scheme.split("+", 1)[0] or "postgresql"
          parsed = urlparse(f"{scheme}://{rest}")
          host = parsed.hostname or "localhost"
          port = parsed.port or 5432
      else:
          host, port = "localhost", 5432
      try:
          with socket.create_connection((host, port), timeout=0.5):
              return True
      except OSError:
          return False
  ```
  The `FORGE_TEST_DB == "1"` branch and its preserved-for-flip comment block both delete.

  **(b) Teardown PermissionError fix at `tests/conftest.py:218`:** wrap the `pg_terminate_backend` SQL in `try/except`. Surfaced by baseline (1/47 ERROR) — the `forge` role on dev Postgres is not SUPERUSER. Recommended shape:
  ```python
  try:
      await conn.execute(_phase13_text(
          f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
          f"WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()"
      ))
  except Exception:
      # forge role lacks SUPERUSER; skip the terminate-backend step.
      # The DROP DATABASE that follows will still succeed once asyncpg
      # closes its remaining connections via engine.dispose() above.
      pass
  ```
  Bare `except Exception` (rather than `except InsufficientPrivilegeError`) because the wrapped SQLAlchemy `ProgrammingError` doesn't expose the asyncpg-level type cleanly. Planner can tighten if mypy/pyright objects.

### Pre-run empirical UAT (Phase 17 D-02 pattern) — BASELINE COMPLETE

- **D-05:** Baseline ran 2026-04-29 on dev with `FORGE_TEST_DB=1` + `FORGE_DB_URL=postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge`. Memory's failure-mode prediction was **mostly accurate, with three corrections surfaced by the run:**

  **Console run (`pytest tests/console/test_staged_*.py -v`):**
  - 33 collected. 10 passed (input-validation tests that never hit DB).
  - **22 failed with `RuntimeError: got Future ... attached to a different loop`** — exact predicted shape, HARNESS-01 territory.
  - **1 failed with `entities_project_id_fkey` violation** (`test_staged_list_filter_by_project_id`, NOT loop conflict). The fixture-seed phase commits two `propose(project_id=...)` calls before the HTTP call ever runs — same FK root cause as the store-layer tests. **This reclassifies 1 test from HARNESS-01 → HARNESS-02.**

  **Store-layer run (`pytest tests/test_staged_operations.py -v`):**
  - 47 collected. 40 passed. 4 by-design skipped (parameterized `(None, X) → X != "proposed"` rows; explicitly skipped per test code lines 116-128, NOT a fixture/harness concern).
  - **2 failed with `entities_project_id_fkey` violation** (`test_staged_op_list_filter_by_project_id`, `test_staged_op_list_combined_filter`) — HARNESS-02 territory.
  - **1 failed with assertion error** (`test_transition_atomicity` line 388: `assert row is None` after `commit()` then `flush()` then `rollback()`). Memory listed this as an "FK violation" — empirically it's a pre-existing test logic bug, NOT an FK violation. The assertion contradicts SQLAlchemy/Postgres rollback semantics: `rollback()` cannot undo a prior `commit()`. **Deferred to POLISH-03 (Phase 19) — see D-07.**
  - **1 teardown ERROR** (`test_audit_replay`): `pg_terminate_backend` requires SUPERUSER; `forge` role isn't one. Same root cause as the 1 ERROR observed in the console run. Folded into HARNESS-03 (D-04 part b).

  Rationale for keeping this whole record in CONTEXT.md: deterministic plan resolution. Plan-phase now has the empirical truth, not the memory approximation.

### Verification scope

- **D-06:** Live UAT command is the sole verification gate. Final acceptance commands per requirement:
  - **HARNESS-01 acceptance:** `FORGE_DB_URL=postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge pytest tests/console/test_staged_*.py -v` → 0 loop-conflict RuntimeErrors; 22/23 PASSED; 1 (`test_staged_list_filter_by_project_id`) fails with FK violation that HARNESS-02 closes. AFTER P-03 lands, NO `FORGE_TEST_DB=1` is needed.
  - **HARNESS-02 acceptance:** `FORGE_DB_URL=... pytest tests/test_staged_operations.py -v` → 42 PASSED + 4 by-design SKIPPED + 1 expected FAIL (`test_transition_atomicity`, deferred to POLISH-03) = 47 collected. Console FK test (`test_staged_list_filter_by_project_id`) also passes after wiring.
  - **HARNESS-03 acceptance:** Diff `tests/conftest.py` shows the `FORGE_TEST_DB == "1"` branch removed AND the `pg_terminate_backend` SQL wrapped in `try/except`. `pytest tests/` (no env vars) still completes without Postgres-related failures (silent skip when DB unreachable). 0 teardown ERRORs in `pytest tests/test_staged_operations.py -v`.
  Adding a CI matrix job (option 6b) was deferred to v1.5. Cross-host (assist-01) UAT (option 6c) was rejected as redundant.

### Atomicity test deferral

- **D-07:** `test_transition_atomicity` in `tests/test_staged_operations.py:323-398` has a pre-existing test logic bug at line 388 surfaced by the baseline. The assertion `assert row is None` after the sequence `propose() → commit() → approve() → flush() → rollback()` contradicts SQLAlchemy/Postgres semantics: `commit()` durably persists the proposed entity to the database; the subsequent `rollback()` only reverts work done since that commit (the approve+events), NOT the proposed entity itself. The test author's assertion message ("post-rollback: even the original proposed entity is rolled back because its commit was tied to the rolled-back session") describes a behavior that does not exist in PostgreSQL. The test has been broken since written; the loop-conflict skip masked it.

  **POLISH-03 already scopes the atomicity sub-test rewrite** (`tests/test_staged_operations.py:356`, "placeholder cross-session atomicity sub-test ... becomes a real assertion"). The actual failing line is 388 (in the same test method's "Reconstruct the test in a single session for atomicity observation" block), but POLISH-03's broader "make the atomicity test actually work" mandate covers it. The line-388 fix is one of: (a) invert the assertion to `assert row is not None` and rewrite the message to reflect the actual atomicity claim ("approve+events rolled back; prior propose remains durable"), or (b) drop the second-half single-session block entirely and put a real cross-session atomicity test in the placeholder slot at line 356. Either approach is POLISH-03's call.

  **Phase 18 does not touch this test.** REQUIREMENTS HARNESS-02 acceptance was amended to reflect "1 expected fail (`test_transition_atomicity`, deferred to POLISH-03)" rather than the original "47 passed."

### Claude's Discretion

- Exact `seeded_project` fixture signature: single-id yield vs parameterized N-id yield (D-03). Planner picks based on whether the FK tests cleanly share one fixture invocation or each declare their own.
- Whether the `await` additions in the 23 call sites cluster into a single mechanical sub-task or split across the 3 files. Planner picks.
- Phase SUMMARY structure — follow the established v1.4 SUMMARY pattern (gates table + final-status section). Three gates: HARNESS-01, HARNESS-02, HARNESS-03. SUMMARY should explicitly note the atomicity test deferral to POLISH-03.
- Whether the teardown fix uses bare `except Exception` (D-04 part b) or a narrower `except sqlalchemy.exc.ProgrammingError`. Planner picks based on whether mypy/pyright is configured.
- Whether to add a brief comment block above the new `seeded_project` fixture explaining the FK-seeding rationale (probably yes, mirroring the `_phase13_*` comment style).

### Folded Todos

None. (`gsd-tools todo match-phase 18` returned 0 matches.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap

- `.planning/REQUIREMENTS.md` §HARNESS — HARNESS-01, HARNESS-02, HARNESS-03 acceptance criteria (lines 22-24, AMENDED 2026-04-29 to reflect baseline findings: HARNESS-01 22/23, HARNESS-02 scope = 2 store + 1 console FK tests, HARNESS-03 includes teardown fix)
- `.planning/REQUIREMENTS.md` §POLISH-03 (line 30) — atomicity sub-test rewrite (covers the deferred `test_transition_atomicity` line-388 logic bug)
- `.planning/ROADMAP.md` §"v1.4.x Carry-Forward Debt" line 83 — Phase 18 row + scope statement + requirement IDs
- `.planning/STATE.md` — current position; will update post-discussion to "Phase 18 context gathered"

### Decisive prior-phase context

- `.planning/phases/17-default-model-bumps/17-CONTEXT.md` D-01 + D-30 references — isolated-commit mandate that Phase 18 inherits
- `.planning/phases/17-default-model-bumps/17-CONTEXT.md` D-02 — pre-run-UAT-before-plan pattern that Phase 18 D-05 reuses
- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` — original surfacing of the 26-test loop-conflict + FK-violation failure modes

### Memory (durable cross-session context)

- `~/.claude/projects/-Users-cnoellert-Documents-GitHub-forge-bridge/memory/project_v1_4_x_harness_debt.md` — full triage detail. Note: memory listed all 3 store-layer failures as "FK violations" but baseline shows 2 FK + 1 atomicity logic bug. CONTEXT D-05 + D-07 supersede the memory on this point.

### Source files in scope

- `tests/conftest.py:120-157` — `_phase13_postgres_available()` (HARNESS-03 target a)
- `tests/conftest.py:218` — `pg_terminate_backend` teardown SQL (HARNESS-03 target b)
- `tests/conftest.py:160-223` — `session_factory` fixture (NOT modified; new `seeded_project` fixture sits alongside it)
- `tests/console/conftest.py:25-39` — `staged_client` fixture body swap (HARNESS-01 target)
- `tests/console/conftest.py:42-69` — `proposed_op_id` / `approved_op_id` / `rejected_op_id` factories (UNCHANGED — they don't carry `project_id`)
- `tests/console/test_staged_handlers_writes.py` (203 lines, 11 tests) — add `await` to all `staged_client.post/get(...)` call sites
- `tests/console/test_staged_handlers_list.py` (175 lines, 7 tests) — same await additions; ALSO HARNESS-02 target for `test_staged_list_filter_by_project_id` (wire `seeded_project`)
- `tests/console/test_staged_zero_divergence.py` (236 lines, 5 tests) — same await additions
- `tests/test_staged_operations.py:457-475` — `test_staged_op_list_filter_by_project_id` (HARNESS-02 target #1)
- `tests/test_staged_operations.py:477-498` — `test_staged_op_list_combined_filter` (HARNESS-02 target #2)
- `tests/test_staged_operations.py:323-398` — `test_transition_atomicity` (NOT touched by Phase 18; deferred to POLISH-03 per D-07)
- `forge_bridge/store/models.py:165-200` — `DBProject` model definition (read-only reference for fixture seeding shape)
- `forge_bridge/console/app.py:58-112` — `build_console_app()` returns a `Starlette` ASGI app (the `app=` argument to `ASGITransport`)

### External docs (httpx + ASGITransport)

- httpx 0.28+ docs — `httpx.AsyncClient(transport=ASGITransport(app=...), base_url="http://testserver")` is the documented pattern for testing ASGI apps without a network socket. `httpx==0.28.1` is already pinned in `pyproject.toml:13` (`httpx>=0.27`).
- pytest-asyncio docs — `asyncio_mode = "auto"` (set in `pyproject.toml`) means `async def test_*` is automatically marked.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`session_factory` fixture (tests/conftest.py:160-223)** — provisions a fresh per-test Postgres database, runs `Base.metadata.create_all`, yields an `async_sessionmaker`, tears down on exit. Already async-correct. The new `seeded_project` fixture composes on top of it.
- **`pytest-asyncio asyncio_mode = "auto"` (pyproject.toml)** — every `async def test_*` is auto-marked. This is what makes the `await` additions in HARNESS-01 mechanical.
- **`httpx==0.28.1` pinned in pyproject.toml:13** — `ASGITransport` available out of the box; no new dependency.
- **`build_console_app()` (forge_bridge/console/app.py:58)** — returns a `Starlette` instance. ASGI 3.0-compliant. Drop-in for `ASGITransport(app=...)`.

### Established Patterns

- **D-30 isolated-commit mandate** — Phase 15/17 precedent: one commit per requirement, separable for `git revert` and `gsd-undo`.
- **Pre-run-UAT-before-plan-phase** — Phase 17 D-02. Empirical evidence in hand at planning time. Phase 18 D-05 reuses (baseline complete).
- **Live UAT as verification gate** — Phase 17 D-04. Default `pytest tests/` stays fast and CI-green; gated commands prove requirement closure on dev. Phase 18 D-06 reuses.
- **Per-test database provisioning (session_factory)** — every store-layer test gets its own fresh DB; no test pollution; teardown drops the DB.

### Integration Points

- The migration boundary is entirely inside `tests/`. No production source file is touched. No `forge_bridge/*` import surface changes. No pyproject.toml dependency changes.
- The console fixture wiring (`build_console_app(api, session_factory=session_factory)` at `tests/console/conftest.py:38`) is the dependency-injection seam that makes the httpx+ASGITransport migration transparent to the production code.

### What's NOT changing

- `forge_bridge/store/staged_operations.py` (StagedOpRepo) — verified-correct via Phase 16.2 chat E2E live UAT.
- `forge_bridge/console/staged_handlers.py` — verified-correct via the same live path.
- The `proposed_op_id` / `approved_op_id` / `rejected_op_id` factory fixtures — they don't carry `project_id`.
- `_OLLAMA_TOOL_MODELS` allow-list, AnthropicAdapter, LLMRouter — out of scope (Phase 19 territory).
- `tests/test_staged_operations.py::test_transition_atomicity` lines 363-398 — deferred to POLISH-03 (D-07).

</code_context>

<specifics>
## Specific Ideas

- **Console-test count breakdown:** `test_staged_handlers_writes.py` (11) + `test_staged_handlers_list.py` (7) + `test_staged_zero_divergence.py` (5) = 23 tests touched by HARNESS-01's `await` additions. Of these, 22 fix to passing on HARNESS-01 alone; 1 (`test_staged_list_filter_by_project_id`) needs HARNESS-02's `seeded_project` to fully pass.
- **Store-layer FK count:** 2 tests in `tests/test_staged_operations.py` (`test_staged_op_list_filter_by_project_id`, `test_staged_op_list_combined_filter`). Both need TWO distinct project ids to test filter discrimination.
- **`base_url="http://testserver"`** is the conventional placeholder for ASGI tests — httpx requires a base URL, the ASGI transport synthesizes the host header from it, and "testserver" is the Starlette/FastAPI community convention. Don't substitute "localhost" (could collide with stray local services in CI).
- **Order of plan execution is sequential, not parallel**: P-01 → P-02 → P-03. P-03 (gate removal) MUST land last because P-01 and P-02 verification commands rely on the gate being present (`FORGE_TEST_DB=1`) to even run. After P-03 lands, the same commands work without the env var.
- **Baseline counts (D-05 reference):** Pre-Phase-18: console 10p/22-loopFAIL/1-FK-FAIL; store 40p/4skip/2-FK-FAIL/1-atomicity-FAIL/1-teardown-ERROR. Post-Phase-18: console 23/23 (with HARNESS-01+02); store 42p/4skip/1-atomicity-FAIL (POLISH-03 territory)/0-teardown-ERROR.

</specifics>

<deferred>
## Deferred Ideas

- **`test_transition_atomicity` line-388 logic bug fix** — POLISH-03 territory (Phase 19). See D-07 for full analysis. NOT touched in Phase 18.
- **CI matrix job with a Postgres service container** — would let HARNESS-01..03 run in default GitHub Actions CI. Deferred to v1.5+ (out of v1.4.x patch-milestone scope).
- **Cross-host UAT replication on assist-01** — would prove platform-agnostic correctness. Deferred — dev-host UAT is sufficient evidence for a tests-only rework.
- **`AsyncTestClient` shim class** (option 3b in discussion) — would preserve sync test-body shapes. Rejected at this phase.
- **`session_factory` auto-seeded default project** (option 2a in discussion) — would couple unrelated tests. Rejected.
- **Phase 19 (POLISH-01..04)** — sibling in the v1.4.x milestone, NOT in scope here. Will be discussed in `/gsd-discuss-phase 19`. POLISH-03 closes the atomicity test deferred from Phase 18.
- **SEED-CHAT-STREAMING-V1.4.x** — explicitly out-of-scope per v1.4.x REQUIREMENTS.

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 18` returned 0 matches.

</deferred>

---

*Phase: 18-staged-handlers-test-harness-rework*
*Context gathered: 2026-04-29 (baseline complete same day)*
