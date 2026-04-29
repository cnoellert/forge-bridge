# Phase 18: Staged-handlers test harness rework - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning (pending pre-run UAT, see D-05)
**Milestone:** v1.4.x Carry-Forward Debt
**Requirements:** HARNESS-01, HARNESS-02, HARNESS-03

<domain>
## Phase Boundary

Phase 18 delivers three isolated commits to `tests/` that turn 26 silently-skipping staged-ops tests into 26 actually-running, actually-passing tests against live Postgres on dev (`:7533/forge_bridge`). The root causes were already triaged during v1.4 close-out and recorded in the `v1.4.x test-harness debt` memory; this phase converts that triage into landed code:

- **HARNESS-01 (test-client migration):** Swap `tests/console/conftest.py::staged_client` from `starlette.testclient.TestClient` (sync wrapper) to `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")` so the test event loop matches asyncpg's session loop. Adds `await` to the 23 call sites across `tests/console/test_staged_handlers_writes.py` (11), `tests/console/test_staged_handlers_list.py` (7), and `tests/console/test_staged_zero_divergence.py` (5). The tests are already `async def` and pytest-asyncio is in `auto` mode — no decorator churn needed. Eliminates `RuntimeError: got Future <Future pending ...> attached to a different loop`.
- **HARNESS-02 (Project FK seeding):** Introduce a new `seeded_project` `@pytest_asyncio.fixture` in `tests/conftest.py` that inserts a `DBProject` row using the `session_factory` and yields its UUID. Wire it into the three FK-violating tests in `tests/test_staged_operations.py` (`test_transition_atomicity`, `test_staged_op_list_filter_by_project_id`, `test_staged_op_list_combined_filter`) — each replaces its inline `uuid.uuid4()` project_id with the fixture-provided id. Eliminates `entities_project_id_fkey` violations.
- **HARNESS-03 (gate removal):** Remove the `FORGE_TEST_DB=1` env-var gate from `_phase13_postgres_available()` in `tests/conftest.py:120-157`. Probe always honors `urlparse(FORGE_DB_URL).hostname/.port` when set, falls back to `localhost:5432` when unset, and returns False (silent skip) when unreachable.

**No production source files are touched.** The diff scope is `tests/conftest.py`, `tests/console/conftest.py`, `tests/console/test_staged_handlers_writes.py`, `tests/console/test_staged_handlers_list.py`, `tests/console/test_staged_zero_divergence.py`, and `tests/test_staged_operations.py` (3 specific tests in the last file). Phase 13/14 source code is verified-correct via Phase 16.2 live UAT — the harness is what was broken, not the handlers.

**Out of scope (deferred to v1.5):** `_OLLAMA_TOOL_MODELS` allow-list audit; SEED-CHAT-STREAMING-V1.4.x (trigger condition not surfaced); CI matrix job adding a Postgres service container; cross-host (assist-01) staged-ops UAT replication. All in `<deferred>` below.

</domain>

<decisions>
## Implementation Decisions

### Commit structure (D-30 isolated-commit mandate)

- **D-01:** Three plans, three commits, one per HARNESS requirement. Mirrors Phase 17's D-30 precedent (every requirement closure ships as a single-purpose commit; `git blame` and `gsd-undo` get a clean revert per requirement). Per-file commits across HARNESS-01 (option 1b) was rejected as artificial fragmentation — the three console test files share one fix and one fixture-body change. Single bulk commit (option 1c) was rejected because it conflates the loop fix with the FK fix with the gate removal, violating decoupled-commit purity.
  - **P-01: HARNESS-01** — `staged_client` fixture body swap + 23 call-site `await` additions across the 3 console test files. One commit.
  - **P-02: HARNESS-02** — `seeded_project` fixture in `tests/conftest.py` + wiring into the 3 FK-violating tests in `tests/test_staged_operations.py`. One commit.
  - **P-03: HARNESS-03** — Remove the `FORGE_TEST_DB=1` gate from `_phase13_postgres_available()`. One commit. Sequenced LAST per memory ("Once 1+2 are done, flip back to opt-in-by-default") — landing P-03 before P-01+P-02 would expose the failures in default-CI runs that have `FORGE_DB_URL` set.

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
  Then add `await` at the 23 call sites: `r = await staged_client.post(...)`, `r = await staged_client.get(...)`, etc. The response object's surface (`r.status_code`, `r.json()`, `r.headers`) is identical between `starlette.testclient.TestClient` and `httpx.AsyncClient` — no body changes beyond the `await` keyword. Rationale: minimal blast radius, idiomatic pytest-asyncio pattern, no permanent test-only shim class to maintain. Wrapper-class shim (option 3b) was rejected as carrying long-term abstraction debt to avoid a one-time mechanical edit. `anyio.from_thread.run` hybrid (option 3c) was rejected as obscuring async semantics in tests that are already async-correct.

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
  Three FK-violating tests in `tests/test_staged_operations.py` replace their inline `project_a = uuid.uuid4()` / `project_b = uuid.uuid4()` with the fixture id (or two-of-them combined with one fresh UUID for the second project where the test asserts on filter discrimination). Auto-seed in `session_factory` (option 2a) was rejected because it would couple every store-layer test to a project row that 90% of them don't need; surfaces unrelated coupling in future tests. Lazy-create inside `proposed_op` factory (option 2c) was rejected because it hides the seeding inside an existing helper and makes the FK requirement implicit instead of explicit. Surgical fixture is the most readable path. Note: `tests/test_staged_operations.py::test_staged_op_list_combined_filter` and `::test_staged_op_list_filter_by_project_id` both need TWO distinct project ids to test filter discrimination — the second project gets seeded inline in the test body via a second `await session.add(DBProject(...))`, or the fixture is parameterized to yield N ids. Planner picks the cleaner shape.

### HARNESS-03 gate-removal semantics

- **D-04:** `_phase13_postgres_available()` always honors `FORGE_DB_URL` host/port if set, falls back to `localhost:5432` if unset, and returns False (silent skip) on `OSError`. NO loud failure when `FORGE_DB_URL` is set-but-unreachable (option 4b/4c rejected) — the silent-skip behavior is the v1.4-close-state CI contract: default `pytest tests/` runs green without Postgres, runs and passes with Postgres reachable. Fail-loud-on-set-but-unreachable would create a CI regression for any consumer who exports `FORGE_DB_URL` for unrelated reasons (e.g., docker-compose env files). Final shape:
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
  The `FORGE_TEST_DB == "1"` branch and its preserved-for-flip comment block both delete. Acceptance criterion (REQUIREMENTS HARNESS-03 line 24): "removing `FORGE_TEST_DB=1` from the audit/UAT commands no longer causes any skip-vs-fail divergence."

### Pre-run empirical UAT (Phase 17 D-02 pattern)

- **D-05:** Run the failing-state baseline on dev BEFORE `/gsd-plan-phase 18` locks the plan. Two commands, both with `FORGE_TEST_DB=1` (current gate state) so the probe lets the tests run:
  ```bash
  # Console handler tests — expect 23/23 to FAIL with "got Future ... attached to a different loop"
  FORGE_TEST_DB=1 \
    FORGE_DB_URL="postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge" \
    FORGE_DB_SYNC_URL="postgresql+psycopg2://forge:forge@127.0.0.1:7533/forge_bridge" \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    python3 -m pytest -p pytest_asyncio.plugin tests/console/test_staged_*.py -v

  # Store-layer tests — expect 3/47 to FAIL with entities_project_id_fkey
  FORGE_TEST_DB=1 \
    FORGE_DB_URL="postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge" \
    FORGE_DB_SYNC_URL="postgresql+psycopg2://forge:forge@127.0.0.1:7533/forge_bridge" \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    python3 -m pytest -p pytest_asyncio.plugin tests/test_staged_operations.py -v
  ```
  Bring the empirical result to plan-phase (PASS/FAIL counts + the exact RuntimeError + FK-violation messages from the output). If the baseline matches the memory description (23 console failures with loop conflict + 3 store failures with FK violation), planning proceeds as scoped. If it diverges (e.g., a 24th failure mode surfaces, or the loop conflict no longer reproduces because something upstream changed), planning re-scopes accordingly. Rationale: deterministic plan resolution; mirrors the Phase 17 D-02 pre-run-UAT pattern that collapsed the conditional MODEL-02 branch at the planning boundary.

### Verification scope

- **D-06:** Live UAT command is the sole verification gate (no CI matrix job, no assist-01 cross-host run). Final acceptance commands per requirement:
  - **HARNESS-01 acceptance:** `FORGE_DB_URL=postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge pytest tests/console/test_staged_*.py -v` → 23/23 PASSED. Note: AFTER P-03 lands, NO `FORGE_TEST_DB=1` is needed.
  - **HARNESS-02 acceptance:** `FORGE_DB_URL=... pytest tests/test_staged_operations.py -v` → 47/47 PASSED (was 44/47 with 3 FK violations).
  - **HARNESS-03 acceptance:** Diff `tests/conftest.py` shows the `FORGE_TEST_DB == "1"` branch removed and the urlparse-honoring path is unconditional; `pytest tests/` (no env vars) still completes without Postgres-related failures (silent skip).
  Adding a CI matrix job with a Postgres service container (option 6b) was deferred to v1.5 because v1.4.x is a debt-paydown patch milestone, not an infrastructure expansion. Cross-host (assist-01) UAT (option 6c) was rejected as redundant — the test surface is platform-agnostic asyncio + asyncpg + httpx; success on dev's `:7533` Postgres is sufficient evidence for a `tests/` rework.

### Claude's Discretion

- Exact `seeded_project` fixture signature: single-id yield vs parameterized N-id yield (D-03). Planner picks based on whether the two FK tests cleanly share one fixture invocation or each declare their own.
- Whether the `await` additions in the 23 call sites cluster into a single mechanical sub-task or split across the 3 files. Planner picks (single sub-task is fine; per-file sub-tasks if it helps readability).
- Phase SUMMARY structure — follow the established v1.4 SUMMARY pattern (gates table + final-status section). Three gates: HARNESS-01, HARNESS-02, HARNESS-03.
- Whether to add a brief comment block above the new `seeded_project` fixture explaining the FK-seeding rationale (probably yes, mirroring the `_phase13_*` comment style).

### Folded Todos

None. (`gsd-tools todo match-phase 18` returned 0 matches.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap

- `.planning/REQUIREMENTS.md` §HARNESS — HARNESS-01, HARNESS-02, HARNESS-03 acceptance criteria (single source of truth for what "done" looks like; lines 22-24)
- `.planning/ROADMAP.md` §"v1.4.x Carry-Forward Debt" line 83 — Phase 18 row + scope statement + requirement IDs
- `.planning/STATE.md` — current position; will update post-discussion to "Phase 18 context gathered"

### Decisive prior-phase context

- `.planning/phases/17-default-model-bumps/17-CONTEXT.md` D-01 + D-30 references — isolated-commit mandate that Phase 18 inherits (one commit per HARNESS requirement)
- `.planning/phases/17-default-model-bumps/17-CONTEXT.md` D-02 — pre-run-UAT-before-plan pattern that Phase 18 D-05 reuses
- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` — original surfacing of the 26-test loop-conflict + FK-violation failure modes

### Memory (durable cross-session context)

- `~/.claude/projects/-Users-cnoellert-Documents-GitHub-forge-bridge/memory/project_v1_4_x_harness_debt.md` — full triage detail: which 26 tests fail, with what error, why each fixture is broken, and the 3-step apply plan that this phase implements

### Source files in scope

- `tests/conftest.py:120-157` — `_phase13_postgres_available()` (target of HARNESS-03; remove the `FORGE_TEST_DB=1` branch and its comment block)
- `tests/conftest.py:160-223` — `session_factory` fixture (NOT modified; new `seeded_project` fixture sits alongside it)
- `tests/console/conftest.py:25-39` — `staged_client` fixture body swap (target of HARNESS-01)
- `tests/console/conftest.py:42-69` — `proposed_op_id` / `approved_op_id` / `rejected_op_id` factories (UNCHANGED — they don't carry `project_id`)
- `tests/console/test_staged_handlers_writes.py` (203 lines, 11 tests) — add `await` to all `staged_client.post/get(...)` call sites
- `tests/console/test_staged_handlers_list.py` (175 lines, 7 tests) — same await additions
- `tests/console/test_staged_zero_divergence.py` (236 lines, 5 tests) — same await additions
- `tests/test_staged_operations.py:323-398` — `test_transition_atomicity` (HARNESS-02 target #1)
- `tests/test_staged_operations.py:457-475` — `test_staged_op_list_filter_by_project_id` (HARNESS-02 target #2)
- `tests/test_staged_operations.py:477-498` — `test_staged_op_list_combined_filter` (HARNESS-02 target #3)
- `forge_bridge/store/models.py:165-200` — `DBProject` model definition (read-only reference for fixture seeding shape)
- `forge_bridge/console/app.py:58-112` — `build_console_app()` returns a `Starlette` ASGI app (the `app=` argument to `ASGITransport`)

### External docs (httpx + ASGITransport)

- httpx 0.28+ docs — `httpx.AsyncClient(transport=ASGITransport(app=...), base_url="http://testserver")` is the documented pattern for testing ASGI apps without a network socket. `httpx==0.28.1` is already pinned in `pyproject.toml:13` (`httpx>=0.27`); `ASGITransport` is in `httpx._transports.asgi`.
- pytest-asyncio docs — `asyncio_mode = "auto"` (set in `pyproject.toml`) means `async def test_*` is automatically marked; no `@pytest.mark.asyncio` decorator needed. The 23 console tests already use this style.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`session_factory` fixture (tests/conftest.py:160-223)** — provisions a fresh per-test Postgres database, runs `Base.metadata.create_all`, yields an `async_sessionmaker`, and tears down on test exit. Already async-correct and shared by all store-layer tests. The new `seeded_project` fixture composes on top of it (`async def seeded_project(session_factory): async with session_factory() as session: ...`).
- **`pytest-asyncio asyncio_mode = "auto"` (pyproject.toml)** — every `async def test_*` is auto-marked. This is what makes the `await` additions in HARNESS-01 mechanical — no decorator additions needed.
- **`httpx==0.28.1` pinned in pyproject.toml:13** — `ASGITransport` available out of the box; no new dependency.
- **`build_console_app()` (forge_bridge/console/app.py:58)** — returns a `Starlette` instance. ASGI 3.0-compliant. Drop-in for `ASGITransport(app=...)`.

### Established Patterns

- **D-30 isolated-commit mandate** — Phase 15/17 precedent: one commit per requirement, separable for `git revert` and `gsd-undo`. Phase 18 inherits this; three plans, three commits.
- **Pre-run-UAT-before-plan-phase** — Phase 17 D-02. Empirical evidence in hand at planning time, not at execution time. Phase 18 D-05 reuses for the failing-state baseline.
- **Live UAT as verification gate** — Phase 17 D-04. Default `pytest tests/` stays fast and CI-green; gated/env-flagged commands prove the requirement closure on dev. Phase 18 D-06 reuses.
- **Per-test database provisioning (session_factory)** — every store-layer test gets its own fresh DB; no test pollution; teardown drops the DB. This pattern continues to work as-is for both HARNESS-01 (httpx ASGI client also runs against per-test DB via dependency injection through `build_console_app(api, session_factory=session_factory)`) and HARNESS-02 (the `seeded_project` fixture provisions its row inside the same per-test DB, no cross-test contamination).

### Integration Points

- The migration boundary is entirely inside `tests/`. No production source file is touched. No `forge_bridge/*` import surface changes. No pyproject.toml dependency changes (httpx is already a runtime dep).
- The console fixture wiring (`build_console_app(api, session_factory=session_factory)` at `tests/console/conftest.py:38`) is the dependency-injection seam that makes the httpx+ASGITransport migration transparent to the production code — the same `Starlette` app is exercised, just via a different transport.

### What's NOT changing

- `forge_bridge/store/staged_operations.py` (StagedOpRepo) — verified-correct via Phase 16.2 chat E2E live UAT.
- `forge_bridge/console/staged_handlers.py` — verified-correct via the same live path.
- The `proposed_op_id` / `approved_op_id` / `rejected_op_id` factory fixtures — they don't carry `project_id`, so the FK-seeding fix doesn't reach them.
- `_OLLAMA_TOOL_MODELS` allow-list, AnthropicAdapter, LLMRouter — out of scope (Phase 19 territory).

</code_context>

<specifics>
## Specific Ideas

- **The 23-test count** breaks down as: `test_staged_handlers_writes.py` (11) + `test_staged_handlers_list.py` (7) + `test_staged_zero_divergence.py` (5) per the v1.4-close memory. These are the loop-conflict failures.
- **The 3-test FK count** breaks down as: `test_transition_atomicity`, `test_staged_op_list_filter_by_project_id`, `test_staged_op_list_combined_filter`, all in `tests/test_staged_operations.py`. Total store-layer file passes 47/47 after the fix (was 44/47 with 3 FK failures).
- **`base_url="http://testserver"`** is the conventional placeholder for ASGI tests — httpx requires a base URL, the ASGI transport synthesizes the host header from it, and "testserver" is the Starlette/FastAPI community convention. Don't substitute "localhost" (could collide with stray local services in CI).
- **Order of plan execution is sequential, not parallel**: P-01 → P-02 → P-03. P-03 (gate removal) MUST land last because P-01 and P-02 verification commands rely on the gate being present (`FORGE_TEST_DB=1`) to even run. After P-03 lands, the same commands work without the env var.

</specifics>

<deferred>
## Deferred Ideas

- **CI matrix job with a Postgres service container** — would let HARNESS-01..03 run in default GitHub Actions CI on every PR. Deferred to v1.5+ (out of v1.4.x patch-milestone scope; needs a separate phase to define the workflow file, secrets, and matrix shape).
- **Cross-host UAT replication on assist-01** — would prove platform-agnostic correctness. Deferred — dev-host UAT is sufficient evidence for a tests-only rework; assist-01 is reserved for Ollama integration tests.
- **`AsyncTestClient` shim class** (option 3b in discussion) — would preserve sync test-body shapes. Rejected at this phase; if a future phase needs to migrate a much larger body of sync tests, the shim is a reasonable approach but is a permanent test-only abstraction that this 23-call-site migration doesn't justify.
- **`session_factory` auto-seeded default project** (option 2a in discussion) — would simplify the FK fix to a one-line factory change, but couples every store-layer test to a project row 90% of them don't need. Re-evaluate if a future phase introduces 10+ tests that all need the same default project.
- **Phase 19 (POLISH-01..04)** — sibling in the v1.4.x milestone, NOT in scope here. Will be discussed in `/gsd-discuss-phase 19`.
- **SEED-CHAT-STREAMING-V1.4.x** — explicitly out-of-scope per v1.4.x REQUIREMENTS (trigger condition not surfaced in Phase 16.2 UAT).

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 18` returned 0 matches.

</deferred>

---

*Phase: 18-staged-handlers-test-harness-rework*
*Context gathered: 2026-04-29*
