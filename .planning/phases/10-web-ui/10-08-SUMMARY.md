---
phase: 10-web-ui
plan: 08
status: blocked
outcome: FAIL
reason: D-36 artist-UX gate not passed; phase ships back to planning
---

# Plan 10-08 — Phase 10 Closeout + Dogfood UAT

## Overview

Final Phase 10 plan: four hardening checks + the mandatory non-developer dogfood UAT (CONSOLE-05, D-35/D-36). Automated tasks 1–3 passed cleanly. Task 4 (human-verify checkpoint) returned **FAIL** — Phase 10 ships back to planning per D-36.

## Tasks

### Task 1 — Wheel-build + asset-inclusion test ✓

Commit: `9c527c5` — `test(10-08): wheel-build + asset-inclusion verification test`

- `tests/test_ui_wheel_package.py` (22 tests, all pass)
- Every Phase 10 template + vendored JS confirmed inside the built wheel
- SRI round-trip test verifies `base.html` `integrity="sha384-*"` attributes match the bytes of the wheel-packaged `htmx-2.0.10.min.js` and `alpinejs-3.14.1.min.js` (T-10-36 mitigation)
- 15 parametrized template-inclusion tests pass (all Phase 10 templates reachable in `pip install` output)

### Task 2 — JS-disabled graceful degradation test ✓

Commit: `b2d67c0` — `test(10-08): JS-disabled graceful degradation smoke test`

- `tests/test_ui_js_disabled_graceful_degradation.py` (9 tests, all pass)
- All 6 full-page routes (`/ui/tools`, `/ui/tools/{name}`, `/ui/execs`, `/ui/manifest`, `/ui/health`, `/ui/chat`) return a complete HTML document on first paint with JS off
- Shell chrome (top-nav + `#health-strip`) rendered server-side
- CSS link + 5 nav anchors present on every full-page response

### Task 3 — Full-suite regression + path-traversal probe ✓

No new files; live-server probe results recorded below.

Regression run (16 test files):
- **152 tests passed, 0 failed, 0 skipped**
- `ruff check forge_bridge/console/` — 0 findings

Live-server path-traversal probes (T-10-37 + T-10-38):
- `GET /ui/static/../handlers.py` → **404**
- `GET /ui/tools/..%2F..%2Fetc%2Fpasswd` → **404**
- `GET /ui/` → **302 → /ui/tools**
- `GET /ui/tools` → **200**

### Task 4 — Non-developer dogfood UAT (D-35/D-36) ✗

Commit: `ef37dd9` — `test(10-08): record non-developer dogfood UAT — FAIL per D-36`

Record: `.planning/phases/10-web-ui/10-UAT.md`

- Operator: `ET / tester`
- Developer: `CN / dev`
- Outcome: **FAIL**
- Duration: not measured — operator's qualitative verdict "nearly impossible to understand" made further timing moot
- Fixtures loaded: 5 synthesized tools (1 quarantined) in-memory on a standalone UI server bound to `:9996`

## Findings

### Shipping bug (plan 10-02 defect, not caught by any Phase 10 test)

`forge_bridge/console/templates/shell.html` line 7:

```html
<nav class="top-nav" hx-boost="true" hx-push-url="true" hx-target="#view-main" hx-swap="innerHTML">
```

`hx-boost="true"` on the nav intercepts every anchor click. Combined with `hx-target="#view-main"` and `hx-swap="innerHTML"`, clicking a nav link fetches `/ui/<view>` — which returns the full shell + view per D-01 — and injects the entire response *inside* the existing `#view-main`. Result: the nav and health strip render twice after the first nav interaction.

Server HTML is correct (1 nav, 1 health-strip, 1 health-error box in the raw response). The duplication is entirely client-side, from the htmx swap contract mismatch. Tests did not catch this because `starlette.testclient.TestClient` exercises handlers in isolation and never simulates the browser htmx swap.

### Artist-UX gate (D-35/D-36)

- No explicit **Status** column — artists must infer "quarantined" from `Obs count: 0`
- Column headers read as developer telemetry (`Code hash`, `Obs count`, `Namespace`) rather than artist concepts
- Preset chips (`Active synth` / `Quarantined` / `Builtin only`) are present but not discoverable enough to rescue first-load comprehension — the operator gave up before trying them
- The duplicate-nav render bug compounded the problem on the Tools page itself

## Key files

- `tests/test_ui_wheel_package.py` (created, 22 tests)
- `tests/test_ui_js_disabled_graceful_degradation.py` (created, 9 tests)
- `.planning/phases/10-web-ui/10-UAT.md` (created — FAIL record)

## Self-Check: PASSED (automated) / FAILED (artist-UX gate)

Automated tasks 1–3: PASSED. 152/152 tests green, ruff clean, path-traversal mitigations confirmed in a live server.

Task 4 (mandatory human-verify gate): FAILED per D-36. Operator could not identify tools in the required cognitive window; developer observed a shipping render bug in the same session.

## Phase 10 closure decision

**Ship back to planning per D-36.** Phase 10 does NOT advance to Phase 11.

Remediation scope for a follow-up phase (proposed as `10.1` gap-closure or `10-09` if a full phase is preferred):

1. Fix the `hx-boost` + `hx-target`/`hx-swap` mismatch on shell.html (content-negotiate on `HX-Request` or let `hx-boost` do its default whole-body swap).
2. Add an explicit **Status** column with a visual chip (`active` / `quarantined` / `loaded`) — not inferred from Obs count.
3. Rename or complement developer-jargon column headers with artist-oriented labels.
4. Make the preset chips more discoverable on first paint (explanatory caption, clearer separation from the query console).
5. Add an in-browser test (playwright or equivalent) that exercises the nav-click → swap contract so plan 10-02's bug class is caught in CI.
6. Re-run the non-developer dogfood UAT with a fresh operator on the remediated build; must pass within 30 s to close Phase 10.
