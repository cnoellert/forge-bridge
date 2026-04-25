# Phase 10: Web UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `10-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 10-web-ui
**Mode:** Interactive (text-mode fallback — `AskUserQuestion` not available; plain-text numbered lists)
**User preference carried in:** `Prefer strong recos for technical decisions` (auto-memory) — discussion presented recommendations up front rather than neutral menus; user accepted the full slate in one turn.
**Areas presented:** 7 (all accepted)

---

## Area 1: Template & htmx swap architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Full-page reloads (no htmx for nav) | Traditional MPA; htmx only for drilldown drawers. Simplest, but loses the partial-swap benefit. | |
| `hx-boost` everywhere (MPA + progressive enhancement) | `hx-boost="true"` on nav + `hx-push-url` for state changes. Base-shell template + fragment-swap routes for partials. | ✓ |
| SPA-ish with client router | Alpine.js as pseudo-router handling all transitions. Rejected — conflicts with vendored-only / zero-build posture and URL addressability contract. | |

**User's choice:** Base-shell + fragment swaps (D-01..D-06).
**Notes:** Picked for MPA-native idiom matching Jinja2+htmx; preserves graceful-degradation with JS disabled; no second routing layer. Three-level inheritance (`base` → `shell` → per-view) locked. Health strip polls a fragment route (`/ui/fragments/health-strip`) rather than JSON to keep htmx's contract clean.

---

## Area 2: Structured query console (DF-1)

| Option | Description | Selected |
|--------|-------------|----------|
| Full DSL with boolean operators, parens, quoted phrases | Grafana / Kibana-style query bar. Expressive but costs parser work and user education. | |
| Minimal `key:value` grammar + preset chips as primary artist surface | Whitespace-separated tokens, no booleans. Chips are the 80% path; grammar is the engineer escape hatch. Client-side parser in Alpine. | ✓ |
| Server-side parser endpoint | Dedicated `/api/v1/query?q=...` that translates friendly tokens to query params. Rejected — duplicates Phase 9 D-03 contract, adds a second filter dialect to maintain. | |

**User's choice:** Minimal grammar + preset chips + client-side parser (D-07..D-11).
**Notes:** Grammar table per view locked (D-08). 3–4 chips per view (D-09). Error surfacing is inline (amber highlight + message below input); never silent, never toast (D-10). Keyboard: `/` focuses, `Enter` submits, `Esc` clears (D-11).

---

## Area 3: Tool drilldown & execution detail

| Option | Description | Selected |
|--------|-------------|----------|
| Side drawer (slide-in from right) | Fashionable; lightweight; cost = hand-roll URL push+replay to satisfy CONSOLE-04. | |
| Modal overlay | Same URL-addressability cost as drawer; more jarring for dense data. | |
| URL-addressable full page at `/ui/tools/{name}` and `/ui/execs/{code_hash}/{timestamp}` | Satisfies CONSOLE-04 natively; shareable deep links ready for Phase 11 CLI; no URL-push hand-rolling needed. | ✓ |

**User's choice:** URL-addressable full pages (D-12..D-17).
**Notes:** Top provenance card = 2-col definition list of the 5 canonical `_meta` fields. Raw sidecar JSON in collapsed `<details>` for engineer mode. Raw source for synth tools = plain monospace `<pre>` with line numbers, no JS highlighter (keeps bundle < 30 KB). Copy-to-clipboard via Alpine. Code-hash display rule: 8-char truncation in lists, full hash on drilldown.

---

## Area 4: Health strip + polling cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Single aggregate pill only (no per-service dots) | Minimalist. Loses service-level granularity; artist can't tell which service is degraded without navigating away. | |
| Aggregate pill + 7 micro-dots + click-to-expand panel | Pill answers "should I panic?"; dots answer "where?"; expand panel answers "why?". Alpine-local state, no backend round-trip. | ✓ |
| Full multi-row strip always visible | Denser; steals vertical real estate from every view. Rejected. | |

**User's choice:** Pill + 7 dots + expand-in-place (D-18..D-22).
**Polling matrix decision:**

| Surface | Considered | Selected |
|---------|------------|----------|
| Health strip | 5 s, 10 s, 30 s | **10 s** |
| `/ui/health` dedicated view | 5 s, 10 s | **5 s** |
| Tools / execs / manifest lists | auto 30 s, auto 60 s, **manual refresh only** | **manual refresh only** |

**Notes:** Rationale for manual refresh on lists: tools/execs/manifest change on bursty human actions, not continuous telemetry; auto-polling wastes cycles and creates flicker. Flagged as a UX claim the dogfood UAT must validate — revisit at 30 s auto-refresh if artists expect live lists. Tab-visibility pause implemented once on `shell.html` via Alpine `visibilitychange` listener (D-22).

---

## Area 5: Filter UI + URL state encoding

| Option | Description | Selected |
|--------|-------------|----------|
| Visible filter dropdowns/checkboxes + structured query | Two filter surfaces to maintain. | |
| Structured query + preset chips only; plain URL query params for state | Single filter surface; URL state mirrors Phase 9 D-03 end-to-end. | ✓ |
| Fragment-hash (`#`-based) client state | Rejected — URLs should be server-interpretable for CLI / deep-link use. | |

**User's choice:** Structured query + chips only, plain URL params (D-23..D-27).
**Notes:** Bundled into areas 1+2 in conversation; documented here for the audit trail. Visible filter dropdowns deferred to v1.4 pending dogfood UAT. On full-page load, query console input pre-populates from URL so the input text matches the filtered view.

---

## Area 6: Chat nav stub

| Option | Description | Selected |
|--------|-------------|----------|
| Omit chat nav until Phase 12 | Smallest diff now; Phase 12 churns `shell.html` + route table when adding. | |
| Greyed-out (disabled) nav link | Visible but non-interactive; gives a hint of the roadmap. | |
| Visible nav link → `/ui/chat` placeholder page ("launches in Phase 12") | Ships nav contract now; Phase 12 fills panel content only; eliminates "where's chat?" at dogfood UAT. | ✓ |

**User's choice:** Visible nav + placeholder page (D-28, D-29).
**Notes:** Placeholder page renders full `shell.html` with intact health strip; centered card explains the Phase 12 gating and links to relevant chip presets.

---

## Area 7: Vendored static asset packaging

| Option | Description | Selected |
|--------|-------------|----------|
| Flat `static/` with plain `htmx.min.js` + `alpine.min.js` | Simplest. Rejected — no version trace in filename; no update audit. | |
| `static/vendor/` subdirectory with version in filename + SRI + explicit hatch include | Version lineage in filename; SRI catches tampering post-install; explicit wheel-include glob closes the "looks done but isn't" packaging risk. | ✓ |
| Bundle + re-minify at build time | Rejected — defeats the zero-build constraint and adds a build dep for trivial gain. | |

**User's choice:** `vendor/` subdir + version-in-filename + SRI + explicit hatch include (D-30..D-34).
**Notes:** Files locked: `htmx-2.0.10.min.js`, `alpinejs-3.14.1.min.js`. SRI via `sha384-...` + `crossorigin="anonymous"`. Target total vendored JS < 30 KB. 3-line README in `vendor/` documents the update process (drop file, recompute SRI, bump template ref).

---

## Scope-creep redirects

None raised during this discussion — user stayed within phase bounds and accepted the full rec slate.

## Claude's Discretion items (deferred to planner / UI-SPEC)

- Starlette route structure (`Route()` lists vs. `Mount()` vs. decorators) — planner picks what reads cleanly alongside Phase 9's `app.py`.
- Jinja2 filter / macro set for rendering helpers — planner adds as needed.
- Alpine component granularity — one root on `shell.html` vs. per-view components.
- Preset chip exact labels + token strings — UI-SPEC may sharpen wording.
- Pagination visualization (prev/next vs. numbered pages) — recommended prev/next + "page N of M".
- Jinja2 autoescape + extension config — default autoescape-on is the expectation.
- Footer presence + content on `shell.html` — minor; planner decides.

## Non-developer dogfood UAT (CONSOLE-05)

Locked as D-35/D-36 — operator-who-is-not-the-developer opens `http://localhost:9996/ui/` cold, identifies three most recently synthesized tools + their status within 30 seconds. Unit / E2E tests do NOT satisfy this. If dogfood fails, Phase 10 ships back to planning.

---

*Log written: 2026-04-22 at context capture*
