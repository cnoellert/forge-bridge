# C2 — Compile → Commit-Bearing Executor Chain (CLOSE)

**Status:** `closed-mechanism-shipped-bridge-side-verified; live-E2E-gated-on-executors`
**Milestone:** v1.12 Mutation Delegation (phase 1 of 2). **Implementation:** `9ecd503` (pushed).
**Companion ADR:** `.planning/adr/ADR-0001-…` (Door C / C1). **Shape:** A+ (intent-ratification).

---

## What shipped

A rename intent through `/api/v1/chat` now compiles to a **commit-bearing executor chain**
(`flame_rename_shots <args>` → `forge_apply_rename <args> -> commit`) and reaches
preview/`AssentRecord`/ratify instead of the DI.1 hard-block. Five tasks, all landed in `9ecd503`:

- **T1** `forge_bridge/console/_executor_route.py` — deterministic post-compile rewrite; rename-only
  `_EXECUTOR_MAP`; 5-clause guard incl. **Finding 1** (`dispatch_authority(executor_tool)`); multi-mutation
  fail-safe; clean passthrough.
- **T2** hook at `_chat_compile.py:183` (before `graph_contains_commit_node` at `:184`), `execution_tools
  or tools`.
- **T3** A+ — `_commit_count` (type-keyed on `result["type"]=="commit_applied"`) lifts `count` into
  `_apply_complete_body`; `panel.html` renders *"Renamed N shots."* (data + confirmation, per Creative).
- **T4** `tests/console/test_c2_executor_routing.py` (+163) — incl. Finding-1 mis-declared-executor
  fail-safe and the strip-guard preview/propose E2E.
- **T5** in-chat `apply <id>` replay aligned onto the reachable surface (`execution_tools or tools` SSE /
  `tools_post_reachability` JSON), with the PR20-forced-execution avoidance the Finding-2 trace surfaced;
  `tests/console/test_chat_apply_dispatch.py` (+33).

---

## The decision arc (how A+ was reached)

- **Fork settled (operator-ratified):** A+ (intent-ratification + apply-time count) now; **Shape B**
  (manifest-ratification, Window-2 drift protection) opened as v1.12 **phase 2**, not smuggled in.
- **Grounding settled the fork honestly:** discover does *not* run at preview (commit path stores chain
  TEXT; `build_preview_from_steps` is lexical). DT's two-windows reframe (`Window 1` apply-discover→verify,
  protected; `Window 2` preview→apply, B's job) dissolved a phantom "A regresses line 64." A pure-A preview
  shows *no count*, so the silent-count-drift flip-condition is a Shape-B artifact, not an A risk.
- **Plan-check (DT + Creative):** Finding 1 (HIGH) adopted into T1; publish **excluded** (G2 — no
  `ApplyPublishInput`↔`PublishSequence` arg parity, bare tool unconfirmed) → own future motion; "no
  reshaping" invariant rescoped to rename-proven. Finding 2 traced to the bottom and **relocated** — the
  C2 hook surface is benign (strip-guard robust to the superset); the real exposure was a *pre-existing*
  in-chat apply-replay narrowing that C2 was merely first to exercise (→ T5).
- **All pre-flight groundings resolved before lock:** G1 confirmed safe (registry `setdefault(readOnlyHint,
  False)`), G2 → exclude, G3 → type-keyed extraction (the commit result shape `_step.py:889-897`).

---

## Verification

Bridge-side acceptance **met**. Operator: 56 focused passed; full suite **2688 → 2697** (+9, the two new
test files); `ruff` clean; `forge_bridge.__all__`==19; tree clean. Implementation read against the locked
plan: every load-bearing lock landed verbatim (Finding-1 conjunction, rename-only map, hook position, G3
type-keyed count, count+confirmation, T5 surface). **DT sign-off: no reservations.**

DT's count-shape grounding (strengthening): `count = len(manifest.resolved_plan)` is computed bridge-side
from the manifest the commit node already holds — *not* lifted from the executor's `apply_result` — so
*"Renamed N shots"* is robust independent of the executor's final apply-return shape, and is semantically
the ratified plan's cardinality at apply (exactly the A+ intent). Fixture-mirrors-production risk dissolved.

---

## Residual (known, not defects)

- **Live 26-04 E2E** still gated on the unpushed forge-pipeline executors (`claude/document-action-api-ZYmqX`,
  ~146 commits ahead of stale origin) + their registration. The substrate-before-consumer boundary the plan
  named — C2 degrades honestly to the DI.1 block until they land, by design.
- **Degradation-message wording** recorded as UX debt: Finding 1's fail-safe lands the operator on the same
  DI.1 block as the unregistered case, so a future wording fix covers unregistered + mis-declared uniformly.

---

## Forward pointers

- **Shape B — Manifest-Ratification** = v1.12 phase 2 (named next motion; preview-time discover, manifest
  persistence, Window-2 drift). Maturation condition: room judges Window-2 drift unacceptable in production.
- **Publish executor delegation** = its own future motion (own grounding; discover mirrors the proposer).
- **`/gsd-secure-phase 26`** before the forge-pipeline executor branch merges.
- **26-04 live E2E** resumes as a ratify-chain rerun against the registered executors (non-autonomous,
  live-Flame).

---

## Methodology candidates

- **Grounding-flip relocates the finding (not just corrects the fact).** Finding 2 was *mis-located* at the
  C2 hook seam; tracing to the bottom moved it to a pre-existing apply-replay surface, downgraded it, and
  spun out T5. Distinct from a value-flip — the *seam* moves. The same pattern fired on the housekeeping
  "2-ahead" claim (grounded → 1-ahead). Candidate amendment to `[[feedback-ground-specs-in-actual-files]]`
  / `[[feedback-provenance-precedes-behavioral-interpretation]]`: *the grounded answer can relocate where
  the risk lives, not only whether the claim is true.*
- **Grounding reduced scope, not expanded it** (Creative). G2 trimmed the map to rename-only; the executor
  contract removed transform complexity (no `mode` token, no reshaping). Scope-shrinks-under-grounding as a
  convergence signal — the plan fitting the system rather than being imposed on it.
- **Boundary invariant > one-time grounding** (Finding 1). G1 proved the annotation *today*; Finding 1
  enforces it *every time*. Instance of `[[feedback-baseline-drift-invalidates-controls]]` applied
  prospectively at plan stage.
