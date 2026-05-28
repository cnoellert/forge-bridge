---
milestone: v1.7
thread: C
phase: C.1
phase_name: Bridge MCP asset tools — make Asset operationally legible
status: closed
opened: 2026-05-27
closed: 2026-05-27
type: phase-close
derives_from: .planning/phases/C.1-thread-c-asset-operability/C.1-PLAN.md
implementation_arc: b5e21f7..8ea4a40 (8 commits, in D1..D9 order per spec)
---

# C.1 — Phase close cursor

> **Asset is no longer quiet.** Six dedicated MCP tools, three
> Status aliases, behavioral test coverage, and operator-readable
> docs shipped in a single cycle. The substrate's already-present
> Asset infrastructure now has an operator surface; downstream
> systems can register, version, locate, relate, and query
> durable production objects through canonical MCP affordances.

## What shipped

Eight commits in expected D1..D9 sequence (the spec's deliverable
ordering carried through implementation byte-for-byte):

```
b5e21f7  feat(C.1): Status aliases for operator vocabulary parity
407e5f4  feat(C.1): forge_create_asset MCP tool
3f1caa1  feat(C.1): forge_list_assets MCP tool
92a35d1  feat(C.1): forge_get_asset MCP tool
903d968  feat(C.1): forge_update_asset MCP tool
7a59e81  feat(C.1): forge_attach_asset_location MCP tool
03ee2db  feat(C.1): forge_relate_asset MCP tool
8ea4a40  docs(C.1): docs/ASSET.md + VOCABULARY.md cross-link
```

Concrete deliverables landed:

- **3 Status aliases** in `forge_bridge/core/vocabulary.py`
  (`proposed→PENDING`, `published→DELIVERED`,
  `invalidated→ARCHIVED`), inserted grouped-by-target-enum per
  the existing convention. `"invalidate"` verb form
  intentionally excluded per Path A constitutional ruling.
- **6 dedicated asset MCP tools** in `forge_bridge/mcp/tools.py`
  with PR22-compliant Input models (one Pattern B —
  `forge_list_assets`; five Pattern C — the remaining five).
- **6 registrations** in `forge_bridge/mcp/registry.py` under the
  asset section header inserted after the shot tools and before
  `list_versions`, with `readOnlyHint` / `idempotentHint`
  annotations matching the L1 table exactly.
- **18-row behavioral test coverage** in
  `tests/mcp/test_asset_tools.py` exercising the full
  handler → entity_create → EntityRepo → JSONB round-trip path
  via the live-Postgres `session_factory` fixture (20 passed
  including the 3 Status alias unit tests).
- **`docs/ASSET.md`** authored against the D9 spec; six tools
  documented, 7-relationship-type substrate truth captured
  (including `peer_of` per D9 §4 ruling), R-9 + R-5 + R-10
  pointers explicit; **`docs/VOCABULARY.md`** cross-link added.
- **No schema work** (per R-2): zero alembic migrations, zero
  edits to `forge_bridge/store/models.py` or `repo.py`.
- **No Version-publish surface** (per R-9 / L3): zero
  modifications to `list_versions`, `register_publish`,
  `list_published_plates`, `get_shot_versions`,
  `snapshot_timeline`.

`forge_bridge.__all__` remains at 19 — byte-identical public API
invariant preserved across the v1.4.x → v1.6 → v1.7 arc.

## Gate-by-gate disposition

| Gate | Status | Evidence |
|---|---|---|
| 1 — D8 tests pass | ✓ | 20 passed in `tests/mcp/test_asset_tools.py` + the three Status alias unit tests |
| 2 — existing suite passes unchanged | ✓ | 10 failures pre-existing on commit `32e8cfb`; identity-matched post-C.1; zero net regression |
| 3 — PR22 mechanical compliance on new tools | ✓ | Six new tools pass individually; the full-suite gate's failure is on pre-existing `flame_execute_python`, not C.1 surface |
| 4 — `fbridge doctor` clean | ✓ | Cleared after launchd kickstart 2026-05-27; `install_provenance` row reflects current commit |
| 5 — docs/ASSET.md + VOCABULARY.md cross-link | ✓ | Grep verified: six tools present, R-9 / R-5 / R-10 references present, VOCABULARY.md cross-link present |
| 6 — `forge_bridge.__all__` at 19 | ✓ | Confirmed unchanged |

## Discoveries

Five findings worth archaeology beyond the standard close shape.

### D-1. Pre-existing reliability-debt cluster surfaced

C.1's acceptance gate (full pytest suite passes) ran the suite
end-to-end and surfaced 10 failures + 1 PR22 mechanical violation
that pre-date C.1 by months. The failures cluster into five
domain areas: console-startup binding, CLI entrypoint, flame
timeline, ping fixtures (test-isolation), and PR22
flame_execute_python compliance (flat-signature pattern not yet
named in PR22's A/B/C taxonomy).

**Identity-match evidence** between pre-C.1 commit `32e8cfb`
(with new `test_asset_tools.py` removed) and post-C.1 commit
`8ea4a40`: 10 failed → 10 failed, identical names. C.1
introduced zero net regression.

Recorded as forward-pressure at
`.planning/seeds/SEED-MAIN-RELIABILITY-DEBT-V1.7+.md` — promotes
to an active phase (reliability-cleanup or a single-cluster
motion) when the forcing function arrives (CI-green requirement,
contract surface needed, or explicit cleanup ratified). Per
`[[feedback-decomposition-recomposition-validation-arc]]`: this
is a recomposition surface — accumulated debt becoming visible
as v1.7's gate-as-contract discipline exercises the suite
end-to-end where earlier narrower selections did not.

### D-2. Acceptance-gate scope-of-test observation (candidate memory)

C.1-PLAN.md Gate 3 read "PR22 mechanical compliance test passes
with the six new tools registered." The test runs **full-registry**
— so the gate inherits the shared mechanical test's health, not
just the new code's compliance. The implementer's strict reading
held the close appropriately; the writing room owed the
classification (load-bearing semantic: failure on any new tool
fails the gate; failure on pre-existing tools is corpus-scope
archaeology, not new-code regression).

**Pattern shape:** acceptance gates that reference shared
mechanical tests inherit the shared surface's health, not just
the new code's compliance. Gate language needs explicit
scope-of-test qualification — "passes on the six new tools" vs
"passes" — to prevent the strict-reading hold that occurred
here.

**Candidate-memory status:** single-instance now. Hold pending a
second occurrence at a distinct pressure surface before
promotion. Sibling memory to
`[[feedback-distinct-success-criteria-per-adjacent-layer]]`
(success criteria stay attached to the native layer); this would
extend that discipline to gate-scope-of-test language.

### D-3. External-daemon-restart operational gap

`fbridge doctor` correctly flagged the snapshot-vs-live
asymmetry: the daemon was serving commit `0974c5f` while disk
was at `8ea4a40`. The `install_provenance` doctor row did
exactly what
`[[feedback-provenance-precedes-behavioral-interpretation]]`
engineered it to do: caught the divergence as a first-class
observable.

**Operational gap surfaced:** `fbridge down && fbridge up` does
**not** own launchd-supervised daemons. The supervised-daemon
path (installed via `sudo ./scripts/install-bootstrap.sh`)
requires the supervisor's kickstart:

```bash
sudo launchctl kickstart -k system/com.cnoellert.forge-bridge
# and for the WS server, if needed:
sudo launchctl kickstart -k system/com.cnoellert.forge-bridge-server
```

The operator's muscle-memory reflex ("restart the daemon") does
not always reach the right substrate; the doctor row catches
the gap correctly. Two outcomes recorded:

- **The doctor row is load-bearing for writer's-room / operator
  separation.** Without it, the snapshot-vs-live asymmetry would
  be silent and indefinite — exactly the failure mode Phase 24.2
  was engineered to close. This close confirms 24.2's
  architecture is doing its job at C.1's pressure surface.
- **A docs/TROUBLESHOOTING.md one-liner** naming the
  launchctl-kickstart path is the right operational artifact;
  landed alongside this close cursor.

### D-4. Stage 2 leakage-watch — clean across 8 commits

The ontology-leakage watch (Implementation Guidance section of
C.1-PLAN.md) named five surfaces where asset-awareness most
commonly spreads sideways: utility functions, serializers,
shared query surfaces, registry helpers, response envelope
conventions.

**Result:** Stage 2 grep across the 8 implementation commits
showed asset terms only in the intended local asset surfaces
and registrations. The five named substrate-side surfaces stayed
generic. The discipline held under implementation pressure.

This is meaningful evidence for the discipline. Capturing as
discipline-proof-of-life: the ontology-leakage-watch + Stage 2
grep prompt structure works as engineered. Sibling to the
Phase N+ drift-guard-as-determinism-enforcement constitutional
finding — both are mechanisms that proved load-bearing under
real implementation pressure rather than only on paper.

### D-5. Failure-shape-stability pattern firing as designed

`[[feedback-failure-shape-stability-as-disposition-evidence]]`
fired at C.1 close. 10→10 identity-match across pre-C.1 → post-C.1
closed what could otherwise have been a multi-hour "is C.1
broken?" investigation in minutes. The pattern (promoted from
24.7 H0 disposition) was the operational instrument that made
the disposition decisive.

**Corroboration evidence:** new project layer
(multi-surface integration test failure cluster across the full
suite, not a single-intervention behavioral falsification).
Pattern was already memory-grade; this is reuse-at-a-distinct-
pressure-surface evidence.

## Methodology — candidate-memory ledger

One pattern at hold pending second occurrence:

**Acceptance-gate scope-of-test discipline.** Acceptance gates
that reference shared mechanical tests inherit the shared
surface's health, not just the new code's compliance. Single-
instance promotion-bar; carry forward as candidate until a
second distinct-pressure-surface occurrence appears. Sibling to
`[[feedback-distinct-success-criteria-per-adjacent-layer]]`.

## Closure records

- **Reliability-debt seed planted** at
  `.planning/seeds/SEED-MAIN-RELIABILITY-DEBT-V1.7+.md`. Five
  clusters enumerated with identity-match evidence; trigger
  conditions named; two paths forward for Cluster 5 (PR22
  flame_execute_python) explicit.
- **docs/TROUBLESHOOTING.md** — launchd-kickstart entry added
  for the supervised-daemon restart path.

## Carried forward

- **Convenience aggregation pressure watch.** Creative's
  forward-looking warning at Stage 1b sign-off: now that Asset
  ontology exists, downstream pressure for joins / unified
  queries / helper abstractions / generalized entity handling
  will arrive. Sibling pressure to the ontology-leakage watch —
  leakage flows substrate-ward (asset knowledge into shared
  infrastructure); aggregation pressure flows surface-ward
  (substrate generality eroding into asset-specific
  aggregation). Worth attending to in C.2 and beyond.
- **R-10 forcing-criterion contract.** C.3 (projekt-forge
  consumer proof) opens with the three-bucket evidence-required
  contract intact. Substrate is now operable from the bridge
  side; the consumer-side investigation can begin.
- **Status-transition validation question.** R-7 noted that
  state-transition validation, if ever needed, is a
  substrate-wide concern not an Asset-specific motion. Carried
  forward; not promoted to an active question.

## Next motion

**C.2 — Bridge CLI asset surface.** Operates against the same
six operations (create, list, get, update, attach_location,
relate) at the operator-friendly Typer subgroup under
`fbridge asset`, with `--json` mode preserved per P-01
stdout-purity discipline. Dogfood pass per Thread B B-2 pattern.

C.3 (Projekt Forge consumer proof) waits on neither C.1 close
nor C.2 — but per R-6 sequencing the C.3 investigation has the
strongest evidence base if C.1 is settled before C.3 opens.
Either way, the R-10 forcing-criterion contract is the gate.

## Status

**Closed.** v1.7 Thread C / Phase C.1 ships. Asset is no longer
quiet — it speaks through six dedicated MCP affordances. The
substrate's already-present infrastructure now has an operator
surface; the room ratified the writing-room → spec → Stage 1b
→ implementation → Stage 2 → close cadence across a single
day-long cycle without role-distinction violation.
