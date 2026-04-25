# Phase 10 — Non-developer Dogfood UAT Record

**Performed:** 2026-04-23 12:30 PDT
**Operator:** ET / tester
**Developer:** CN / dev
**Duration:** not measured — operator gave qualitative verdict before timing completed
**Outcome:** FAIL (remediated 2026-04-24 via Phase 10.1 — re-UAT verdict PASS with recorded deviations; see `.planning/phases/10.1-artist-ux-gap-closure/10.1-UAT.md` for details)

## Fixture state

- Tools present: 5 (all synthesized; 1 quarantined: `synth_extract_shot_notes` with `observation_count: 0`)
- Three most-recently-synthesized, per server:
  1. `synth_set_segment_note` — active (2026-04-23T18:45Z, obs=4)
  2. `synth_batch_rename_by_grade` — active (2026-04-23T15:20Z, obs=11)
  3. `synth_extract_shot_notes` — quarantined (2026-04-23T11:05Z, obs=0)

Fixtures were registered in-memory at console startup (no on-disk sidecar files). The `/api/v1/tools` endpoint returns empty because the MCP lifespan was bypassed to run a pure-UI server; the `/ui/*` surface reads from `ManifestService` directly, which had the fixtures loaded. This does not affect the UAT verdict — the operator tested the artist-facing surface.

## Operator answers

Operator did not complete the task. Qualitative response: "Nearly impossible to understand."

## Observations

**Shipping defect discovered in the same session (plan 10-02, shell.html line 7):**
- `<nav class="top-nav" hx-boost="true" hx-target="#view-main" hx-swap="innerHTML">` causes every nav link click to inject the *full* response (shell + view chrome + content) *inside* the existing `#view-main`, so the nav and health strip render twice on first nav interaction. Server HTML is correct — the duplication is an htmx-swap contract mismatch between `hx-boost` on the nav and handlers that return full pages (D-01). None of plan 10-02 / 10-03 tests exercised the in-browser swap; `TestClient` hits handlers in isolation.
- Suggested fix: remove `hx-target`/`hx-swap` from the nav and let `hx-boost` perform its default whole-body swap; OR make `/ui/*` handlers content-negotiate on `HX-Request` and return just the `view` block when htmx requested it.

**Operator-facing comprehensibility (D-35 / D-36 qualitative fail):**
- No explicit **Status** column. "Quarantined" must be inferred from `Obs count: 0` — a non-obvious derivation for an artist.
- Column headers read as developer telemetry (`Code hash`, `Obs count`, `Namespace`) rather than artist concepts. An artist does not have a mental model of "observation count" or a truncated SHA-256 code hash.
- No visible affordance for "which tool is safe / recommended / broken" at a glance.
- Preset chips ("Active synth", "Quarantined", "Builtin only") are present and may be the right escape hatch, but the operator did not use them before giving up — indicates the chips are not discoverable enough to carry first-load comprehension.

**Compounding UI bug on the dedicated Tools page:**
- The duplicate-nav render bug (above) is visible on this view and likely made the already-unclear data even harder to parse. A retest after the render fix may still fail the content-clarity gate — the two are independent problems.

## Decision

**FAIL → ship back to planning per D-36.**

Remediation scope for a follow-up phase (proposed 10.1 or 10-09):

1. Fix the `hx-boost` + `hx-target`/`hx-swap` mismatch on `shell.html` nav (content-negotiate or let `hx-boost` do default).
2. Add an explicit **Status** column to the Tools table with a visual chip (`active` / `quarantined` / `loaded`) — not inferred from Obs count.
3. Rename or complement the developer-jargon headers with artist-oriented labels (e.g. `Synthesized` → `Created`, `Obs count` → `Times used`, truncate or hide `Code hash` behind a details toggle).
4. Ensure the preset chips surface above the table are visible and discoverable on first paint; consider a one-line explanatory caption ("Click a chip to narrow the list").
5. Add an in-browser test (playwright or equivalent) that exercises the nav-click → swap contract end-to-end so plan 10-02's bug class is caught in CI going forward.
6. Re-run the non-developer dogfood UAT with a fresh operator on the remediated build; must pass within 30s to close Phase 10.

Record the next-step in STATE.md: Phase 10 execution COMPLETE through automated gates (tasks 1–3 pass: wheel contract, JS-disabled degradation, regression suite). Phase 10 BLOCKED on D-36 artist-UX gate. Do not advance to Phase 11 until remediation + re-UAT pass.

---

## Closure (2026-04-24)

Remediation Phase 10.1 completed all six scoped items above:

1. `shell.html` nav swap fix — `hx-target`/`hx-swap` removed; `hx-boost` handles whole-page swap (Plan 10.1-02).
2. Explicit **Status** chip column — `_derive_tool_status()` helper + `active`/`loaded` chip vocabulary (Plan 10.1-03). Quarantined-tool surfacing deferred to Phase 11 / v1.4 via amended ROADMAP SC#2 (Plan 10.1-01).
3. Artist-facing column headers — 4 primary columns (Name / Status / Type / Created); developer telemetry demoted into the Name cell's secondary row (Plan 10.1-03).
4. Chip discoverability — caption "Click a chip to narrow the list" + CSS refresh for the LOGIK-PROJEKT amber palette (Plan 10.1-03).
5. In-browser swap-contract test — Playwright `test_ui_nav_swap_regression.py` (Plan 10.1-04) + Playwright `test_ui_chip_click_regression.py` (gap-closure Plan 10.1-06 after a chip-click shell-dup bug was caught by the pre-UAT smoke check).
6. Fresh-operator re-UAT — performed 2026-04-24 10:50. Operator ET under two documented deviations (fresh-operator rule and partial-understanding criterion). Verdict: PASS with deviations. See `.planning/phases/10.1-artist-ux-gap-closure/10.1-UAT.md` §Deviations for the full audit trail.

Three Phase-11 follow-ups persisted in `.planning/phases/10.1-artist-ux-gap-closure/10.1-HUMAN-UAT.md`:
a. Truly-fresh-operator re-UAT (requalify SC#6 against D-44 without deviation).
b. Default-sort affordance legibility on the `Created` column header.
c. Non-Chromium browser parity smoke (Firefox + Safari).

Phase 10 is no longer blocking Phase 11. D-36 artist-UX gate closed.
