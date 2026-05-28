---
name: main-reliability-debt
description: 10 test failures + 1 PR22 mechanical compliance violation on main branch, identity-matched pre-C.1 → post-C.1. Five debt clusters spanning console-startup binding, CLI entrypoint, flame timeline, ping fixtures, and PR22 flame_execute_python compliance. C.1 surfaced the debt by running the full suite as an acceptance gate; C.1 introduced none of it.
type: strategic-framing
planted_during: "C.1 close, 2026-05-27 — full-suite run during C.1 acceptance produced 10 failures. Pre-C.1 baseline (commit 32e8cfb, with new test_asset_tools.py removed) produced the same 10 failures by name and shape. Failure-shape-stability evidence per [[feedback-failure-shape-stability-as-disposition-evidence]] cleared the C.1 disposition; the underlying debt is recorded here for follow-on motion."
trigger_when: "A contributor reaches for a v1.7+ phase where suite stability becomes load-bearing (e.g. a phase that needs CI green, that touches console-startup binding, that exercises Flame timeline behavior, or that depends on the PR22 mechanical-enforcement gate as a contract surface). OR an explicit reliability-cleanup motion opens to sweep the clusters."
---

# Seed — main reliability debt (v1.7+ era)

> **Captured as forward-pressure, not as a blocker.** This seed
> exists because C.1's acceptance gate (full pytest suite passes)
> surfaced 10 failing tests + 1 PR22 violation that pre-date C.1.
> The failures are identity-matched between pre-C.1 commit
> `32e8cfb` (with new test_asset_tools.py removed) and post-C.1
> commit `8ea4a40`. Per
> `[[feedback-classify-don't-chase]]`: corpus-scope instruments
> surface archival imperfections that are not regressions;
> classification determines disposition. C.1 ships clean; the
> debt is named so the next motion has it as forward-pressure
> rather than silent erosion.

## What this seed names

Five clusters of pre-existing failures, surfaced together by the
v1.7 acceptance-gate machinery. Each cluster is its own root
cause; this seed enumerates and labels, it does not investigate.

### Cluster 1 — Console startup binding

```
tests/test_console_stdio_cleanliness::test_mcp_stdio_frames_are_clean_while_console_under_load
tests/test_console_stdio_cleanliness::test_stderr_contains_no_access_log_lines
```

15s-timeout test patterns under console-startup load. Stdio
cleanliness invariants. Adjacent surface: Phase 24.2 daemon-routed
doctor work + Phase 16.x SSE streaming work both touched console
startup; one of them or accumulated drift since may have eroded
the invariant.

### Cluster 2 — CLI entrypoint

```
tests/test_typer_entrypoint::test_bare_forge_bridge_boots_mcp_not_help
tests/test_typer_entrypoint::test_console_port_flag_sets_env
```

Bare-invocation behavior and CLI flag wiring. Phase 11 + Phase
20.x + Phase 24.x all touched the `fbridge` CLI surface; drift
likely accumulated across versions.

### Cluster 3 — Flame timeline

```
tests/test_timeline_gap_fill::test_gap_fills_tracks_segments_by_id
tests/test_timeline_gap_fill::test_pass2_skips_segments_already_used_as_gap_fills
```

Timeline gap-fill segment tracking. Domain-specific Flame timeline
logic; not a substrate concern but the test suite carries it.

### Cluster 4 — Ping fixture / module-state divergence

```
tests/test_utility_ping::test_ping_failure_path_echoes_bridge_url
tests/test_utility_ping::test_ping_failure_path_bridge_url_reflects_current_bridge_module_state
```

**Distinct behavioral shape:** these tests pass in isolation; they
fail under the full-suite test ordering. Test-isolation / module-
state pollution between tests, not a substantive code regression.
Phase 24.2 reworked utility.ping; that's the most-likely surface
the divergence rides on, but the failure mode is fixture/import-
order, not behavioral.

### Cluster 5 — PR22 mechanical compliance: flame_execute_python

```
tests/test_tool_contract_enforcement::test_pr22_every_registered_tool_satisfies_canonical_contract
```

Single violation: `flame_execute_python` (registered with a
**flat** signature, `execute_python(code: str, main_thread: bool
= False)` — per commit `f8328a4` from 23.1) fails the PR22
mechanical check. The test's `_has_drift` + `_has_required_inner_fields`
logic categorizes the violation as "annotation/runtime
divergence" — but the actual cause is that PR22's three-pattern
taxonomy (A/B/C with `params: <Model>` wrappers) does not name a
fourth category: **flat signatures with required top-level
fields**. `flame_execute_python` is correct-by-design for its
flat shape; the test logic does not yet recognize it.

Two paths forward when this cluster is addressed:

- **Low-cost.** Add `"flame_execute_python"` to
  `KNOWN_PR22_DRIFT` at
  `tests/test_tool_contract_enforcement.py:138` and update
  `SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+.md` to acknowledge a
  "flat-signature with required field" sub-class that is **not
  drift but an unnamed pattern.** This is a labeling fix, not a
  code change.
- **Higher-cost.** Extend `_has_drift` and
  `_has_required_inner_fields` to recognize flat-signature tools
  as a fourth pattern (Pattern D — flat-signature with required
  top-level field) and stop categorizing them as runtime
  divergence. This makes the test taxonomy match the actual
  registered-tool surface.

Either path is its own small motion; both restore the PR22 gate
to load-bearing status.

## Identity-match evidence

```
                              pre-C.1 (32e8cfb)   post-C.1 (8ea4a40)
test_mcp_stdio_frames_clean         FAIL                FAIL
test_stderr_no_access_log_lines     FAIL                FAIL
test_no_forge_specific_strings      FAIL                FAIL
test_gap_fills_tracks_segments      FAIL                FAIL
test_pass2_skips_segments           FAIL                FAIL
test_pr22_every_registered_tool     FAIL                FAIL
test_bare_forge_bridge_boots_mcp    FAIL                FAIL
test_console_port_flag_sets_env     FAIL                FAIL
test_ping_failure_path_echoes_url   FAIL                FAIL
test_ping_failure_path_module_state FAIL                FAIL

                              10 failed             10 failed
```

Identical names, identical shape, identical count. C.1 introduced
zero net regression. The clusters are existing debt the v1.7
phase machinery surfaced by running the suite end-to-end.

## Architectural framing

Per `[[feedback-decomposition-recomposition-validation-arc]]`:
this is a recomposition surface. The v1.7 acceptance-gate
discipline (writing room owes the implementer a verifiable
acceptance gate spec) is what made the previously-silent debt
visible. The earlier project cadence ran narrower test selections
that did not surface the cluster; v1.7's gate-as-contract change
made the corpus a load-bearing surface.

Per `[[feedback-explicitly-unbound-vs-implicitly-rejected]]`:
this seed is the deferral, not the rejection. Each cluster has a
named likely surface and a named follow-on shape; none are being
ignored. The room ratifies promotion to an active phase when the
forcing function arrives (CI-green requirement, contract surface
needed, or explicit cleanup motion).

Per `[[feedback-failure-shape-stability-as-disposition-evidence]]`:
the identity-match evidence is what made the C.1 disposition
decisive. Single-instance reuse here; the pattern was already
promoted from 24.7 H0 disposition. This is corroboration at a
new project layer (multi-surface integration test failure cluster
across the full suite, not a single-intervention behavioral
falsification).

## What this seed does NOT do

- It does not investigate any of the five clusters. Root causes
  are likely but unverified.
- It does not propose a fix shape. The two paths named for
  Cluster 5 are options for when the room rules on it, not
  ratified choices.
- It does not prioritize the clusters against each other. That
  ordering is the future motion's job.
- It does not block any v1.7 work. Threads A, B (closed), C
  (this close), and any v1.8 work proceed in parallel.

## Status

**Parked as forward-pressure.** Promotes to an active phase
(reliability-cleanup, or a more-targeted single-cluster motion)
when the trigger condition fires. The seed's load-bearing job is
to preserve the cluster identification + identity-match evidence
so the next investigator does not have to redo this work.
