# Phase 18: Staged-handlers test harness rework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 18-staged-handlers-test-harness-rework
**Areas discussed:** Commit structure, Project FK seeding strategy, TestClient → AsyncClient migration approach, HARNESS-03 gate-removal semantics, Pre-run empirical UAT, Verification scope

User directive: "I'm all good with the recos." All six recommended options accepted as a batch; no per-area follow-up needed.

---

## Commit structure

| Option | Description | Selected |
|--------|-------------|----------|
| Three commits, one per HARNESS-NN | Mirrors Phase 17 D-30 isolated-commit mandate; clean revert per requirement | ✓ |
| Per-file commits (4–5) | Splits HARNESS-01 across the 3 console files | |
| Single bulk commit | All three requirements in one commit | |

**User's choice:** Three commits, one per HARNESS-NN.
**Notes:** Per-file fragmentation rejected as artificial — the three console test files share one fixture-body change. Bulk-commit rejected as conflating loop fix + FK fix + gate removal.

---

## Project FK seeding strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-seed default project in `session_factory` | Every test DB has it; simplest, but couples unrelated tests | |
| New `seeded_project` fixture | Surgical; consumed by `proposed_op` and the 3 FK tests | ✓ |
| Modify `proposed_op` factory to lazy-create | Hides seeding inside existing helper | |

**User's choice:** New `seeded_project` fixture.
**Notes:** Auto-seed coupled 90% of unrelated store-layer tests to a default project they don't need. Lazy-create made the FK requirement implicit. Surgical fixture is the most readable.

---

## TestClient → AsyncClient migration approach

| Option | Description | Selected |
|--------|-------------|----------|
| Swap `staged_client` fixture body | `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")` + `await` at call sites | ✓ |
| Wrap in `AsyncTestClient` shim class | Preserves sync test-body shapes; permanent test-only abstraction | |
| Hybrid (`anyio.from_thread.run`) | Async fixture with sync call sites | |

**User's choice:** Swap fixture body and add `await` at the 23 call sites.
**Notes:** Minimal blast radius; idiomatic pytest-asyncio pattern. Tests are already `async def` and pytest-asyncio is in `auto` mode — no decorator churn. Response object surface (`r.status_code`, `r.json()`, `r.headers`) is identical between `TestClient` and `httpx.AsyncClient`.

---

## HARNESS-03 gate-removal semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Probe always honors `FORGE_DB_URL`; silent skip if unreachable | Memory-described path; CI stays green without DB | ✓ |
| Skip if unset; fail loudly if set-but-unreachable | Surfaces CI infra issues | |
| Always fail if set but unreachable | Strictest variant | |

**User's choice:** Always honor `FORGE_DB_URL`; silent skip on `OSError`.
**Notes:** Fail-loud variants would create a CI regression for any consumer who exports `FORGE_DB_URL` for unrelated reasons (e.g., docker-compose env files). Silent-skip preserves the v1.4-close-state CI contract: default `pytest tests/` runs green without Postgres.

---

## Pre-run empirical UAT

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-run the 23 tests on dev to establish baseline | Mirrors Phase 17 D-02; deterministic plan resolution | ✓ |
| Skip pre-run; trust the memory notes | Faster path to plan-phase | |
| Pre-run + capture output as `BASELINE.md` artifact | Most thorough; durable record | |

**User's choice:** Pre-run the failing-state baseline before plan-phase.
**Notes:** Two commands documented in CONTEXT.md D-05 (one for the 23 console tests, one for the 3 store-layer FK tests). User runs them on dev with `FORGE_TEST_DB=1` and brings the empirical result (PASS/FAIL counts + exact error messages) to `/gsd-plan-phase 18`. If results match the memory description, planning proceeds as scoped.

---

## Verification scope

| Option | Description | Selected |
|--------|-------------|----------|
| Live UAT command on dev | Phase 17 pattern | ✓ |
| Live UAT + CI matrix job with Postgres service container | Permanent CI coverage | |
| Live UAT + assist-01 cross-host run | Asymmetric env coverage | |

**User's choice:** Live UAT command on dev as the sole verification gate.
**Notes:** v1.4.x is a debt-paydown patch milestone, not an infrastructure expansion — CI matrix work belongs in v1.5+. Cross-host (assist-01) is reserved for Ollama integration tests; the test surface here is platform-agnostic asyncio + asyncpg + httpx.

---

## Claude's Discretion

- Exact `seeded_project` fixture signature (single-id vs parameterized N-id yield) — planner picks based on whether the two FK tests cleanly share one invocation.
- Whether the 23 `await` additions cluster into a single mechanical sub-task or split across the 3 files.
- Phase SUMMARY structure — follow v1.4 SUMMARY pattern (gates table + final-status section); three gates: HARNESS-01, HARNESS-02, HARNESS-03.
- Comment-block style for the new `seeded_project` fixture (likely mirror the `_phase13_*` style).

## Deferred Ideas

- CI matrix job with a Postgres service container (deferred to v1.5+).
- Cross-host UAT replication on assist-01 (rejected — dev UAT is sufficient).
- `AsyncTestClient` shim class (rejected at this phase; reasonable for a future much-larger migration).
- `session_factory` auto-seeded default project (rejected — couples unrelated tests).
- Phase 19 (POLISH-01..04) — sibling in v1.4.x; will be discussed in `/gsd-discuss-phase 19`.
- SEED-CHAT-STREAMING-V1.4.x — out of v1.4.x scope per REQUIREMENTS.
