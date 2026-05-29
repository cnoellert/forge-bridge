---
milestone: v1.7
thread: A
phase: A.3
phase_name: Hardening — operational integrity of the authority chain
status: phase-plan
opened: 2026-05-29
drafted: 2026-05-29
type: phase-plan
derives_from:
  - .planning/phases/A.3-thread-a-hardening/A.3-FRAMING.md (87f6fe1)
  - .planning/phases/A.3-thread-a-hardening/A.3-DISCUSS-QUESTIONS.md (f358d04)
grounding: this-session reads of forge_bridge/core/assent.py (14-key to_dict shape) + forge_bridge/store/assent_record_repo.py (list_pending / get_by_graph_intent_id query API) + forge_bridge/store/session.py (get_session async context manager) + forge_bridge/cli/runtime_doctor.py:48-55 (6-row pattern, _check_graph_store tri-state precedent) + tests/integration/test_a2_ratify_apply_flow.py (httpx.AsyncClient + ASGITransport pattern) + docs/RATIFICATION.md (7-section structure) + A.2-PLAN.md L8 (6-class failure envelope)
artifact_role: code-handoff — A.3 implementation drafts from these shape locks
---

# A.3 — Phase plan

Six shape locks (L1..L6) covering R-A3.0..R-A3.7 rulings.
Architectural inheritance + rationale + cascade analysis live in
A.3-FRAMING + A.3-DISCUSS-QUESTIONS; this artifact carries what
implementation needs to land each lock cleanly.

Drafted under
`[[feedback-cadence-artifacts-shrink-to-load-bearing]]` — shape
locks (file paths, signatures, dict keys, acceptance criteria) are
load-bearing for implementation; cycle archaeology + rationale +
cascade analysis are not. Per
`[[feedback-substrate-shape-grounding-at-plan-stage]]` every shape
below is grounded by file reads at draft time.

## L1 — Doctor row: `_check_ratification` (per R-A3.2)

**File:** `forge_bridge/cli/runtime_doctor.py`

**Add:** `_check_ratification()` function — pattern derives from
`_check_graph_store` at lines 475-562. Register in `checks` list at
line 48-55 between `_check_state_ws()` and `_check_graph_store()`.

**Return shape** (matches the 6 existing rows):

```python
{
    "name": "ratification",
    "ok": bool,
    "chip": str,        # "ok" | "loaded" | "fail"
    "status": str,      # human-readable status line
    "url": str,         # DB URL or empty
    "fix": str,         # remediation hint or empty
}
```

**Tri-state semantics:**

| chip | ok | Condition | status line shape |
|---|---|---|---|
| `ok` | True | `assent_record` table reachable, ≥1 record with `decided_at` within window | `"<N> ratifications in last <window>"` |
| `loaded` | True | Table reachable, zero records in window | `"no ratifications in last <window>"` |
| `fail` | False | Session unreachable / schema mismatch / query exception | `"<reason>"` (e.g. `"db unreachable (ConnectionError)"`) |

**Locked constant:** `_RECENT_ACTIVITY_WINDOW = timedelta(hours=24)`
(module-level, near existing `_HTTP_TIMEOUT` constant).

**Session pattern:** wrap `get_session()` with `asyncio.run()` per
the sync-CLI bridging pattern; catch session-init failures as the
`fail` case.

**Acceptance:**
- `fbridge doctor` renders 7 rows in human output
- `fbridge doctor --json` returns 7 entries in `checks` array
- Tests at `tests/cli/test_runtime_doctor_ratification.py` cover
  all three tri-state branches (mock the session factory)
- Exit code remains 0 when chip is `ok` or `loaded`; 1 only when
  any row's `ok` is False

## L2 — Helpers: `forge_bridge.console.helpers` (per R-A3.5)

**File:** `forge_bridge/console/helpers.py` (new public module —
first underscore-free module in `forge_bridge/console/`; sibling
to existing private modules `_chain_parse.py`, `_chat_compile.py`,
etc.)

**Public API** (three async functions; ground against AssentRecord
shape from `forge_bridge/core/assent.py:47-69`):

```python
from datetime import timedelta
from forge_bridge.core.assent import AssentRecord


async def recent_ratifications(
    window: timedelta = timedelta(hours=24),
) -> list[AssentRecord]:
    """Return assent records whose decided_at falls within window.

    Filters by status='ratified' OR status='applied' OR status='failed'
    (any state that passed through ratified — proposed records are
    not yet ratified).
    """


async def pending_assent_records() -> list[AssentRecord]:
    """Return assent records in 'proposed' state.

    Thin wrapper over AssentRecordRepo.list_pending(status='proposed').
    Returns the records list only (drops the count tuple element).
    """


async def recent_failed_applies(
    window: timedelta = timedelta(hours=24),
) -> list[AssentRecord]:
    """Return assent records whose status='failed' and applied_at within window."""
```

**Session pattern:** each function opens its own session via
`async with get_session() as session:` and instantiates
`AssentRecordRepo(session)` internally. Operator never passes a
session.

**Anti-scope (preserved verbatim from R-A3.5):**
- NO MCP tool registration
- NO HTTP endpoint
- NO new wire surface
- NO Pydantic input schema
- NO sanitization at read boundary
- NO rate-limit infrastructure
- NO sync wrapper (operators in async REPL can `await`; PLAN-pick:
  add sync wrapper lazily if first operator request surfaces)

**Acceptance:**
- Module importable: `from forge_bridge.console.helpers import recent_ratifications, pending_assent_records, recent_failed_applies`
- Each helper closes session cleanly on success and exception (per
  `get_session()` context manager guarantee)
- Tests at `tests/console/test_helpers.py` cover each helper against
  the existing `AssentRecordRepo` fixture pattern from
  `tests/store/test_assent_record_repo.py`: one happy-path + one
  empty-result path per helper (6 tests total)
- `forge_bridge.__all__` unchanged (helpers exported only via module
  path, not bridge-level public API)

## L3 — UAT runbook (per R-A3.1)

**File:** `docs/UAT-A3.md` (new — co-located with INSTALL.md /
GETTING-STARTED.md / RECIPES.md / TROUBLESHOOTING.md)

**Catalog** — locked against L8 failure envelope (6 failure classes
+ happy path + multi-cycle):

| # | UAT item | Trigger | Pass criterion |
|---|---|---|---|
| 1 | Drift-invalidation live smoke | propose mutating chain → modify substrate so held_hash ≠ fresh_hash → ratify | exit 1, envelope code `drift_invalid`, held_hash + fresh_hash populated |
| 2 | Happy-path full chain | NL → compile → preview → ratify → apply against live Flame project | exit 0, `assent.applied` event emitted, assent_record status='applied' |
| 3 | Recovery: assent_record_not_found | ratify a graph_intent_id that resolves to no row | exit 1, envelope code `assent_record_not_found` |
| 4 | Recovery: assent_illegal_state | ratify an already-applied graph_intent_id | exit 1, envelope code `assent_illegal_state`, current_status populated |
| 5 | Recovery: chain_aborted | propose chain with a deliberately failing step → ratify → apply | exit 1, envelope code `chain_aborted`, step_index + step_text populated |
| 6 | Recovery: daemon_unreachable | stop daemon → ratify | exit 2, envelope code `daemon_unreachable`, url + reason populated |
| 7 | Multi-cycle ratification cadence | sequence 5 sequential propose-ratify-apply cycles | all 5 succeed, doctor row chip stays `ok` throughout |

**Sub-set gated by A.3 implementation:** Item 1 only (drift smoke —
the named A.2 carry-forward). Items 2-7 are operator UAT post-A.3;
the runbook is operationally complete.

**Acceptance:**
- `docs/UAT-A3.md` lands with all 7 items enumerated
- Each item names trigger + pass criterion verbatim (no narrative
  prose between items)
- Item 1's pass criterion matches the assertion shape in L4 below

## L4 — Drift-invalidation smoke test (per R-A3.1)

**File:** `tests/integration/test_a3_drift_invalidation_smoke.py` (new)

**Pattern:** derives from
`tests/integration/test_a2_ratify_apply_flow.py` (httpx.AsyncClient
+ ASGITransport per A.2 D7 fix). No new fixture shapes invented.

**Scenario:**

1. Setup: build_console_app + RatifyApplyMCP fixture
2. Chat compile a mutating chain → preview returned with
   `graph_intent_id` + chain_steps persisted (assent_record status
   = `proposed`)
3. **Drift trigger:** directly modify persisted chain content so
   fresh re-evaluation of content_hash differs from held value
   (e.g., mutate `chain_steps` JSONB attribute via test session;
   exact mechanism PLAN-locks as: rewrite the chain_steps list in
   `db_entity.attributes['chain_steps']` to a different
   list-of-strings before ratify dispatch)
4. POST `/api/v1/ratify` with `{graph_intent_id, actor: "test"}`
5. Assert response envelope:
   ```python
   {
       "ok": False,
       "error": {
           "code": "drift_invalid",
           "graph_intent_id": <12-char>,
           "held_hash": <64-char hex>,
           "fresh_hash": <64-char hex>,
       },
   }
   ```
6. Assert assent_record state: status transitioned `ratified → failed`,
   apply_failure_reason='drift_invalid'

**Acceptance:**
- Test passes: `pytest tests/integration/test_a3_drift_invalidation_smoke.py`
- Test uses existing fixtures from `test_a2_ratify_apply_flow.py`
  (no new shared fixtures added)
- Test is independent of `_reset_rate_limit` per the existing
  autouse fixture

## L5 — Auth-seed deferral docs (per R-A3.3)

**File:** `docs/RATIFICATION.md`

**Add:** new section `## Authentication (deferred — SEED-AUTH-V1.5)`
inserted **before** `## Relationship To Staged Operations` (the
final section). Position rationale: groups with the substrate-shape
sections, ahead of the cross-substrate comparison footer.

**Section content** (locked language per
`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`):

```markdown
## Authentication (deferred — SEED-AUTH-V1.5)

The `decided_by` field on `AssentRecord` is a free string today.
This is a deliberate placeholder: the A.2 substrate carries no
identity-validation logic, no identity resolution, and no
authentication contract.

The future SEED-AUTH-V1.5 milestone will define:
- Where identity validation lives (substrate vs gateway vs both)
- How identities bind to assent records (free-string vs typed
  identity reference vs both)
- What the eventual integration boundary looks like (signature
  change to `AssentRecordRepo.ratify()` vs upstream gateway vs
  pluggable validator)

A.3 makes NO claim about any of these. The `decided_by`
placeholder remains free-string until SEED-AUTH-V1.5 resolves
the shape; intervening callers may treat it as an audit-trail
field, not an authentication signal.
```

**Acceptance:**
- Section lands at the indicated position (between `## Failure Envelopes`
  and `## Relationship To Staged Operations`)
- Section uses deferral language (no "must" / "will not be
  supported" / "rejected" — preserve deferral discipline)
- No signature change to `AssentRecordRepo.ratify()` or any other
  A.2-shipped substrate
- `docs/RATIFICATION.md` total length grows by ~25 lines (mechanical
  check: `wc -l` post-edit)

## L6 — A.3-CLOSE signal section template (per R-A3.7)

**File:** `.planning/phases/A.3-thread-a-hardening/A.3-CLOSE.md` —
drafted at phase close, NOT in implementation arc. This lock
records the template the close cursor will use.

**Signal section content** (locked language per F1 absorption —
"architecturally sufficient", NOT "architecturally complete"):

```markdown
## Thread A authority-chain — architecturally sufficient

A.1 + A.2 closed the substrate. A.3 hardened it operationally. The
authority chain — NL → compile → graph-intent → preview → ratify
→ apply — is architecturally sufficient for the sync-apply
common case A.2 designed for, and operationally exercised through
the A.3 UAT catalog + drift-invalidation smoke.

A.3-CLOSE SIGNALS the work as sufficient. Thread A framing or
v1.7 milestone framing RULES on formal Thread A closure.

Future work opens as separate threads / milestones:
- **SEED-AUTH-V1.5** — auth identity binding (per L5 deferral)
- **Console ratification** — UI surface for assent (NOT Q5-safe
  via chat per inherited constraint)
- **Multi-turn graph-intent persistence** — graph-intent lifetime
  extension beyond single-session scope
```

**Acceptance:**
- A.3-CLOSE.md drafted at phase close contains this section
  verbatim under heading `## Thread A authority-chain — architecturally sufficient`
- Cross-link to `docs/RATIFICATION.md` § Authentication
- A.3-CLOSE remains compact (target: ~80 lines per A.2-CLOSE
  precedent at 77 lines)

## Implementation step sequence

8 atomic commits, independence noted:

| # | Step | File | Dependency |
|---|---|---|---|
| D1 | Auth-seed deferral docs | `docs/RATIFICATION.md` | none |
| D2 | Helpers module | `forge_bridge/console/helpers.py` | none |
| D3 | Helpers tests | `tests/console/test_helpers.py` | D2 |
| D4 | Doctor row `_check_ratification` | `forge_bridge/cli/runtime_doctor.py` | none |
| D5 | Doctor row tests | `tests/cli/test_runtime_doctor_ratification.py` | D4 |
| D6 | Drift-invalidation smoke | `tests/integration/test_a3_drift_invalidation_smoke.py` | none (consumes A.2-shipped substrate) |
| D7 | UAT runbook doc | `docs/UAT-A3.md` | none |
| D8 | A.3-CLOSE.md draft | `.planning/phases/A.3-thread-a-hardening/A.3-CLOSE.md` | D1..D7 (phase close) |

D1, D2, D4, D6, D7 are independent and may land in any order.
D3 follows D2; D5 follows D4. D8 closes the phase.

## Acceptance gate (phase-level)

- All 6 shape locks (L1..L6) land
- All 7 UAT items enumerated in `docs/UAT-A3.md`
- Drift smoke executes green: `pytest tests/integration/test_a3_drift_invalidation_smoke.py`
- `fbridge doctor` shows 7 rows in both human and JSON output
- `forge_bridge.__all__` unchanged at 19 (no new bridge-level public symbols)
- `pyproject.toml` version unchanged at 1.4.1
- `ruff` clean on changed files
- A.2-shipped substrate (`AssentRecord`, `AssentRecordRepo`,
  4 `assent.*` event types, CommitNode.verify assent extension,
  `fbridge ratify` CLI) byte-equivalent — no signature changes

## What execution-stage needs to confirm at draft time

(Stage 1b spec-review territory; flagged here to gate against
substrate drift between plan draft and execution.)

- `_check_graph_store` row dict shape still matches L1's locked
  shape (re-grep at execution time)
- `AssentRecordRepo.list_pending` signature still matches L2's
  consumer expectation (re-read repo at execution time)
- `tests/integration/test_a2_ratify_apply_flow.py` fixture pattern
  still uses `httpx.AsyncClient + ASGITransport` (re-read at L4
  draft time)
- `docs/RATIFICATION.md` section order matches the L5 insertion
  point (re-read at L5 draft time)
