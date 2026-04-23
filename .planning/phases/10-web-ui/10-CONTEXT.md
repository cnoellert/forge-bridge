# Phase 10: Web UI - Context

**Gathered:** 2026-04-22
**Status:** Ready for UI design contract (`/gsd-ui-phase 10`) → planning

<domain>
## Phase Boundary

The five-view Jinja2 Web UI served at `http://127.0.0.1:9996/ui/` — tools table with provenance drilldown, execution history with per-record detail, manifest browser, health panel, and chat navigation stub — rendered as server-side templates with htmx partial swaps and Alpine.js state, plus a persistent health strip and a structured query console on every list view. Reads exclusively through the Phase 9 `/api/v1/` JSON API. Zero npm build step. Only new pip dep: `jinja2>=3.1`.

In scope (REQ-IDs): CONSOLE-01, CONSOLE-02, CONSOLE-03, CONSOLE-04, CONSOLE-05, TOOLS-01, TOOLS-02, EXECS-01, EXECS-02, MFST-04, HEALTH-01, HEALTH-04.

Out of scope for Phase 10: CLI subcommands (Phase 11 — but `forge-bridge console --help` placeholder already ships from Phase 9 D-10/11), LLM chat endpoint and chat panel content (Phase 12 / v1.4), SSE/WebSocket push (v1.4), real-time per-record updates, admin/mutation actions, auth, visible filter dropdowns/checkboxes (v1.4 reconsider after dogfood UAT).

**CONTEXT scope note:** This file captures *implementation* decisions (template architecture, htmx swap strategy, polling matrix, DF-1 grammar). *Visual* decisions (density, typography, spacing, component styling, color semantics beyond the locked 3-token palette) are owned by `UI-SPEC.md` produced by `/gsd-ui-phase 10` before planning.

</domain>

<decisions>
## Implementation Decisions

### Template & htmx swap architecture

- **D-01:** Server-rendered MPA with htmx as the swap engine. No SPA, no client-side router. Matches Phase 9's "conventional API, friendly UI" split — `/api/v1/` stays JSON for CLI/MCP/chat; the UI has its own tiny partial-HTML surface under `/ui/`.
- **D-02:** Three-level template inheritance — `base.html` (HTML doc skeleton, vendored JS/CSS links, meta) → `shell.html` (extends base; owns top nav, persistent health strip, `<main id="view-main">` slot) → per-view templates (extend shell). Every full-page response goes through `shell.html`.
- **D-03:** Top-nav uses `hx-boost="true"` + `hx-push-url="true"` so link clicks swap `#view-main` and push URL. Back/forward/refresh work natively; no JS framework router.
- **D-04:** Filter changes, pagination, and drilldown navigation hit **fragment routes** under `/ui/fragments/*` that return partial HTML (not JSON). htmx swaps these into `#view-main` (or a nested target) and pushes URL. Fragment routes read through the same `ConsoleReadAPI` as `/api/v1/` — one read layer (Phase 9 D-25).
- **D-05:** Direct URL navigation (`/ui/tools?promoted=true`) returns the full `shell.html + view` template. First paint works with JavaScript disabled for all read flows — free SSH-tunnel / text-browser support, and a guardrail against htmx regressions. JS-disabled is a graceful-degradation target, not a certified UAT surface.
- **D-06:** Health strip polls its own fragment route `/ui/fragments/health-strip` (renders mini HTML, not JSON). Keeps htmx's `hx-get` contract clean and avoids Alpine fetching JSON and rebuilding DOM.

### Structured query console (DF-1)

- **D-07:** Client-side token parser written in Alpine.js (~40 LOC). Converts whitespace-separated `key:value` tokens into Phase 9's plain URL query params, then triggers `hx-get` with the computed URL. **No server-side parse endpoint.** Single layer to debug; no duplication of Phase 9 D-03's query-param contract.
- **D-08:** Grammar for v1.3 is deliberately minimal — `key:value` pairs separated by whitespace. No boolean operators, no parens, no quotes. `q:` is the freeform escape hatch (substring match).

  | View | Supported keys |
  |------|----------------|
  | tools | `origin:`, `namespace:`, `readonly:`, `q:` |
  | execs | `tool:`, `since:`, `until:`, `promoted:`, `hash:` |
  | manifest | `q:`, `status:` |

- **D-09:** **Preset chips (3–4 per view) are the primary artist surface; the query input is the engineer escape hatch.** One click stuffs the canonical query into the input and submits. Chip roster (planner may refine per UI-SPEC):
  - tools — "Active synth", "Quarantined", "Builtin only"
  - execs — "Last 24h", "Promoted only", "Synthesized only"
  - manifest — "Loaded", "Orphaned"
- **D-10:** Error surfacing — unparseable tokens are highlighted in amber, a single-line message appears directly below the input. Never silent, never toast. Toasts break the read-flow the artist is in.
- **D-11:** Keyboard affordances — `/` focuses the input from anywhere on the page, `Enter` submits, `Esc` clears. Standard-for-operator-consoles; no modifier chords.

### Tool drilldown & execution detail

- **D-12:** URL-addressable **full pages**, not drawers or modals. Routes: `/ui/tools/{name}` and `/ui/execs/{code_hash}/{timestamp}`. Reached via `hx-get` + `hx-push-url` from list-row interactions; also work cold via direct URL / refresh / shared link.
- **D-13:** Rationale: SC#3 ("artist can click into any tool and see canonical `_meta` provenance fields … no jargon-only displays") pairs with CONSOLE-04 (URL-addressable state). Drawers/modals break the URL contract unless hand-rolled with URL push + replay — more code than a real page, and Phase 11 CLI will want stable deep-link URLs to reference.
- **D-14:** Tool drilldown layout:
  - **Top card** — 2-column definition list of the 5 canonical `_meta` fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`). Monospace for codes. Amber accent on value column. Exact styling = UI-SPEC.
  - **Consumer-tag chip row** — below the provenance card. Tags already pass Phase 7 `_sanitize_tag` boundary at read time.
  - **Raw source** (synth tools only) — `<pre>` with line numbers, plain text, no JS syntax highlighter. Copy-to-clipboard button via Alpine (~4 LOC).
  - **Raw sidecar JSON** — collapsed `<details>` at the bottom (engineer mode, default closed).
- **D-15:** Exec detail layout — full `raw_code` (in `<pre>`), `intent`, `code_hash`, `timestamp`, `promoted` flag. No sidecar equivalent.
- **D-16:** Code-hash display rule — **list views show first 8 chars + hover-tooltip for full hash**; **drilldown pages show full hash, never truncated**. Consistent shorthand across every list surface.
- **D-17:** No JS syntax highlighter in v1.3. Plain monospace `<pre>`. Rationale: keeps the vendored JS bundle under 30 KB total, keeps the stdio-safety posture (no third-party JS that might try to log to stdout during SSR, though this is a belt-and-suspenders framing), and matches the LOGIK-PROJEKT code-panel heritage.

### Health strip + polling cadence

- **D-18:** Strip layout — one aggregate status pill (from Phase 9 D-15's `status` field) followed by seven micro-dots, one per service: `mcp · flame · ws · llm · watcher · storage · port`. Hover tooltip on each dot shows the service's `detail` string from the `/api/v1/health` response.
- **D-19:** Click-to-expand behavior — clicking the pill expands the strip in-place to show a per-service detail panel (Alpine local state, `x-show`). Click again to collapse. No page navigation; no modal. Dedicated `/ui/health` view remains available for full-depth diagnostics.
- **D-20:** Polling matrix:

  | Surface | Cadence | Pause when tab hidden |
  |---------|---------|------------------------|
  | Health strip | 10 s | yes |
  | `/ui/health` dedicated view | 5 s | yes |
  | Tools / execs / manifest lists | manual refresh only | — |

- **D-21:** Rationale for manual refresh on lists — tools, execs, and manifest change on bursty human actions (synthesis promotions, probation flips, manifest writes), not continuous telemetry. Auto-polling wastes cycles and creates mid-read flicker right when the artist is scanning the table. Every list view has an explicit "Refresh" button + "Last refreshed Xs ago" label so the artist has control. Dogfood UAT will validate; if artists expect auto-refresh, revisit in v1.4 with a 30 s cadence.
- **D-22:** Tab-visibility pause — implemented once on `shell.html` via an Alpine component listening for `visibilitychange`. `document.hidden` → pause all htmx `hx-trigger="every Xs"` via `htmx.config.timeout` or explicit `htmx:abort`; visible → immediate one-shot refresh + resume cadence. Single listener, not per-view.

### Filter UI + URL state

- **D-23:** v1.3 ships the **structured query console + preset chips as the only filter surface**. No dropdowns, no checkboxes, no sidebar filters. Revisit in v1.4 if dogfood UAT shows the chip set is too narrow.
- **D-24:** Filter and pagination state is encoded as **plain URL query params** — `?promoted=true&since=2026-04-01T00:00:00Z&limit=50&offset=100`. Matches Phase 9 D-03 end-to-end, so a shared Web UI URL can be pasted into `curl` / `httpx` with `/ui/` → `/api/v1/` path swap and get the same data.
- **D-25:** `hx-push-url="true"` on every state-changing interaction (chip click, query submit, pagination, drilldown open). Browser refresh replays the exact view.
- **D-26:** On full-page load (direct URL, refresh, deep-link paste), the query console input is pre-populated from the URL so the visible input text matches the filtered view. Server-rendered on first paint; Alpine re-syncs on hydrate.
- **D-27:** No fragment-hash (`#`-based) state. URLs are fully server-interpretable.

### Chat nav stub

- **D-28:** Visible chat nav item → `/ui/chat` placeholder page. Full `shell.html` render, health strip intact, centered card: "LLM chat launches in Phase 12. For now, use the structured query console." Links reference the relevant chip presets so the artist has an on-ramp.
- **D-29:** Rationale — ships the nav contract now; Phase 12 fills in the panel content without churning `shell.html`, the route table, or the nav markup. Also eliminates "where's chat?" confusion at the dogfood UAT.

### Vendored static assets + packaging

- **D-30:** Directory layout:
  ```
  forge_bridge/console/static/
  ├── forge-console.css
  └── vendor/
      ├── htmx-2.0.10.min.js
      └── alpinejs-3.14.1.min.js
  ```
  Version in filename, not in a subdirectory. Served under `/ui/static/vendor/` via the existing Starlette `StaticFiles` mount (same instance as Phase 9).
- **D-31:** SRI `integrity="sha384-..."` + `crossorigin="anonymous"` attributes on every `<script>` tag in `base.html`. Belt-and-suspenders — we serve the assets ourselves, so attacker surface is limited to a compromised wheel, but SRI costs nothing and catches tampering post-install.
- **D-32:** Minified-only in v1.3. No dev / non-minified duplicates. Target total vendored JS < 30 KB. CSS target ~4 KB.
- **D-33:** `pyproject.toml` `[tool.hatch.build.targets.wheel]` explicit include globs:
  ```toml
  [tool.hatch.build.targets.wheel]
  packages = ["forge_bridge"]
  include = [
      "forge_bridge/console/static/**/*",
      "forge_bridge/console/templates/**/*",
  ]
  ```
  Explicit, not inferred. Closes the "looks done but isn't" wheel-packaging pitfall flagged in research.
- **D-34:** Asset-update process documented in `forge_bridge/console/static/vendor/README.md` (3-line note): (1) drop new file with bumped version in filename; (2) recompute SRI via `openssl dgst -sha384 -binary < file | openssl base64 -A`; (3) bump the `<script>` ref in `base.html`. No build step, no lockfile churn.

### Non-developer dogfood UAT

- **D-35:** CONSOLE-05 mandatory UAT — operator-who-is-not-the-developer opens `http://localhost:9996/ui/` cold (no prior briefing) and identifies the three most recently synthesized tools and their status (active / quarantined) within 30 seconds. Run on the `:9996` integration test server with fixture data before phase closure.
- **D-36:** Dogfood UAT is the primary artist-UX gate. Unit tests and playwright-style E2E tests do NOT satisfy CONSOLE-05. If the operator fails the 30 s task, Phase 10 ships back to planning, not to Phase 11.

### Claude's Discretion

- **Exact Starlette route structure** under `/ui/` — whether to use `Route()` lists, `Mount()`, or a `@route` decorator style. Planner picks whatever reads cleanest alongside Phase 9's existing `app.py`.
- **Exact Jinja2 filter / macro set** needed for provenance rendering (timestamp humanization, hash truncation helper, duration formatting). Planner can add as needed; none are user-visible decisions.
- **Alpine component granularity** — one root component on `shell.html` vs. per-view components. Pick whichever keeps Alpine state localized and doesn't leak across routes.
- **Preset chip labels + token strings** (D-09) — the roster above is the starting point; UI-SPEC or dogfood feedback may sharpen the wording ("Active synth" vs. "Synthesized, active").
- **Pagination UI** — prev/next buttons vs. numbered page links vs. infinite scroll. Phase 9 D-02 locked the API to `limit`/`offset`; the UI visualization is Claude's discretion. Recommend prev/next + "page N of M" since artist case is bursty-browsing, not bulk analysis.
- **Which Jinja template extensions / auto-escape defaults** to configure on `Jinja2Templates`. Default autoescape-on is the expectation; XSS vectors in our data come from consumer tags and tool names, both already sanitized upstream.
- **Whether `shell.html` includes a footer** (version string, "localhost:9996", link to GitHub). Minor; planner decides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (UI-SPEC, researcher, planner) MUST read these before producing artifacts.**

### Phase 10 inputs (locked scope + requirements)

- `.planning/PROJECT.md` — v1.3 "Artist Console" milestone scope, locked non-goals (no auth, no admin/mutation, no streaming push, no `LLMRouter` hot-reload, no shared-path JSONL writers), all v1.0–v1.2 key design decisions that still bind Phase 10
- `.planning/REQUIREMENTS.md` — REQ-IDs CONSOLE-01..05, TOOLS-01/02, EXECS-01/02, MFST-04, HEALTH-01/04; traceability table
- `.planning/ROADMAP.md` §"Phase 10: Web UI" — five success criteria + the "CONTEXT NOTE — UI design contract" instruction requiring `/gsd-ui-phase` before `/gsd-plan-phase 10`
- `.planning/STATE.md` §"Session Handoff" — v1.3 implementation constraints, uvicorn task pattern, ConsoleReadAPI-as-sole-read-path, instance-identity gate, jinja2-only-new-dep, non-developer dogfood requirement

### Phase 9 hand-off (the API contract this phase consumes)

- `.planning/phases/09-read-api-foundation/09-CONTEXT.md` — locked API response shape (D-01 `{data, meta}` envelope; D-03 plain query-param filter grammar; D-04 snake_case; D-05 limit clamping; D-14 health response shape; D-24/25 MCP resource + tool shim byte-identity contract; D-30/31 `_lifespan` wiring)
- `.planning/phases/09-read-api-foundation/09-01-PLAN.md`, `09-02-PLAN.md`, `09-03-PLAN.md` — as-shipped code surface Phase 10 extends (`forge_bridge/console/app.py`, `read_api.py`, `manifest_service.py`, `resources.py`)
- `.planning/phases/09-read-api-foundation/09-VERIFICATION.md` — confirms SC#1 stdout-cleanliness + API-06 graceful port degradation both hold; Phase 10 inherits that posture

### Research (v1.3 milestone — all HIGH confidence)

- `.planning/research/SUMMARY.md` §"Phase 10: Web UI" — recommended stack (Jinja2 + vendored htmx 2.0.10 + Alpine.js 3.x), anti-picks (FastAPI, SPA frameworks, Tailwind CDN), UAT criteria
- `.planning/research/STACK.md` — Starlette `Jinja2Templates`, `StaticFiles`, uvicorn programmatic API, exact htmx + Alpine vendor versions, dependency sizes
- `.planning/research/FEATURES.md` — TS-A.1/2/3/4/5, TS-E.1/2, TS-L.1/2 feature scope; DF-1 structured query console, DF-3 doctor (Phase 11), artist-vs-engineer user taxonomy
- `.planning/research/ARCHITECTURE.md` — `forge_bridge/console/` package layout, `ManifestService` + `ConsoleReadAPI` read-boundary that Phase 10 calls into
- `.planning/research/PITFALLS.md` — P-01 (stdout corruption — Phase 10 inherits but doesn't re-open), P-10 (asset + API origin coupling, satisfied by same-port serving), P-11 (no-SPA / no-npm), artist-UX failure modes (the CONSOLE-05 dogfood case)

### UX / palette provenance

- `~/Documents/GitHub/projekt-forge/forge_gui/ui/themes/forge_dark_theme.py` — LOGIK-PROJEKT `modular_dark_theme` source; `#242424` / `#cc9c00` / `#cccccc` tokens + the broader palette UI-SPEC will translate to web idioms. Pixel-clone is explicitly NOT the goal; inherit-and-adapt is.
- Memory: `forge-bridge UX philosophy — artist-first, LOGIK-PROJEKT aesthetic` (auto-memory, 2026-04-22) — the non-developer dogfood UAT requirement and the artist-vs-engineer audience split

### Frontend stack references (for the planner / researcher — already pinned in research)

- htmx 2.0.10 docs — `hx-boost`, `hx-push-url`, `hx-swap`, `hx-trigger="every Xs"`, visibility / pause patterns
- Alpine.js 3.x docs — `x-data`, `x-init`, `x-show`, `$watch` (used only for query console parser + copy-to-clipboard + strip expand)
- MCP Specification 2025-06-18 — irrelevant to Phase 10 (no resources added); referenced only so downstream doesn't re-research
- Starlette 0.52.1 docs — `Jinja2Templates`, `StaticFiles`, route registration alongside existing Phase 9 routes

### Carried-forward v1.2 context (foundation)

- `.planning/milestones/v1.2-ROADMAP.md` — Phase 7/07.1/8 outcomes; the graceful-degradation pattern Phase 9 mirrored and Phase 10 inherits
- `.planning/phases/v1.2-phases/08-sql-persistence-protocol/08-CONTEXT.md` — STORE-06 "JSONL canonical, SQL mirror"; LRN-05 lesson that locked the single-read-path architecture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 9 shipped)

- **`forge_bridge/console/read_api.py` `ConsoleReadAPI`** — sole read layer. All Phase 10 fragment routes and full-page handlers call `get_tools()`, `get_executions(...)`, `get_manifest()`, `get_health()` directly. No new query logic in Phase 10.
- **`forge_bridge/console/app.py`** — Starlette app instance where Phase 10 adds:
  - `Jinja2Templates("forge_bridge/console/templates")` configuration
  - `StaticFiles(directory="forge_bridge/console/static")` mount at `/ui/static`
  - Full-page routes under `/ui/` (tools list, tool drilldown, execs list, exec detail, manifest, health, chat-stub)
  - Fragment routes under `/ui/fragments/` (tools-list partial, execs-list partial, health-strip partial, etc.)
- **`forge_bridge/console/manifest_service.py` `ManifestService.snapshot()`** — already returns the in-memory manifest consistent with `.sidecar.json` on disk; drilldown pages and manifest browser both consume this via `ConsoleReadAPI`.
- **`forge_bridge/console/resources.py` `forge://health` + `/api/v1/health` handler** — produces the exact response shape (D-14 from Phase 9) the health strip expands into. Fragment route `/ui/fragments/health-strip` calls the same `get_health()` method and renders a tiny template.
- **`forge_bridge/learning/sanitize.py` `_sanitize_tag` + size budgets** — already gates consumer-tag rendering at the read boundary. Provenance drilldown renders tags already-sanitized; no new sanitizer pass in Phase 10.
- **`forge_bridge/learning/execution_log.py` `ExecutionLog.snapshot(limit, offset, since, promoted_only, tool)`** — in-memory deque read path per Phase 9 D-06..D-09. Exec list + exec detail views both read through `ConsoleReadAPI.get_executions(...)` which wraps this.
- **Logger-per-module pattern + D-22 ruff print-ban (from Phase 9)** — already enforced across `forge_bridge/console/`. All new Phase 10 modules follow the pattern automatically.

### Established Patterns

- **Single `ConsoleReadAPI` read path** — Phase 9 D-25. Web UI handlers, fragment routes, MCP resources, CLI (future) all read through it. Phase 10 adds zero new read code; it only adds presentation.
- **JSON envelope `{data, meta}` for API, plain HTML for fragments** — API stays conventional (Phase 9 D-01); fragments are tiny Jinja partials. Two rendering surfaces, one read layer.
- **Stdio safety via custom `LOGGING_CONFIG` + `access_log=False`** — Phase 9 D-20/21. Phase 10 adds no new log sinks; inherits cleanly.
- **`asyncio.create_task` + cancel-on-exit in `_lifespan`** — Phase 9 D-30/31 already runs the uvicorn task. Phase 10 adds no new lifecycle hooks; the same uvicorn instance serves `/ui/` and `/api/v1/`.
- **Frozen dataclasses for records** — `ToolRecord`, `ExecutionRecord` are `@dataclass(frozen=True)`. Phase 10 templates render these directly via `{{ record.field }}` — no DTO translation layer.
- **Env-var-then-default config** — Phase 10 adds no new env vars. `FORGE_CONSOLE_PORT` (Phase 9 D-27) is the only knob.

### Integration Points

- **`forge_bridge/console/app.py`** — gains template + static mount + `/ui/` routes + `/ui/fragments/` routes. No change to `/api/v1/` surface.
- **`forge_bridge/console/` new subdirectories** — `templates/` (Jinja2 files) and `static/` (CSS + vendored JS). Packaged via `pyproject.toml` `[tool.hatch.build.targets.wheel].include` globs (D-33).
- **`pyproject.toml`** — add `"jinja2>=3.1"` to `dependencies`; add the hatch-include globs (D-33). No other dep changes.
- **`forge_bridge/__init__.py`** — no new public symbols expected in Phase 10 (templates and routes are internal). Minor version bump ceremony likely deferred until after Phase 10 + 11 ship together.
- **`forge_bridge/mcp/server.py` `_lifespan`** — **no changes**. Phase 9's wiring already starts uvicorn on `:9996`, and the Starlette app Phase 10 extends is the same instance.
- **`forge_bridge/learning/watcher.py`** — **no changes**. Manifest writes flow through `ManifestService.register()`; Web UI reads via `ConsoleReadAPI`.

</code_context>

<specifics>
## Specific Ideas

- **"Conventional API, friendly UI" applied twice** — Phase 9 locked the JSON API to plain query params; Phase 10 applies the same framing inside the UI: plain URL params for state, structured token grammar only in the query console input. One filter dialect to maintain, artist-friendly tokens layered on top client-side.
- **Preset chips carry the 80% artist path; grammar is the engineer escape hatch** — D-09 is the single most important artist-UX decision in Phase 10. If a dogfood operator can't do their task via chips alone, the chip roster is wrong, not the grammar.
- **Drilldown as full page, not drawer** — D-12/13 is a deliberate bet against UI fashion. URL-addressability (CONSOLE-04) + shareable deep links for Phase 11 CLI + SC#3 provenance visibility all point the same direction. Modals are cheaper to build but cost more to integrate.
- **Manual refresh on list views is a UX claim that the dogfood UAT must validate** — D-20/21. If artists expect auto-refresh (projekt-forge's Qt forge_gui auto-refreshes its tool tree), revisit at the first artist dogfood review. Flipping to 30 s cadence later is one-line in the template.
- **Health strip = aggregate pill + 7 dots = the whole HEALTH-04 requirement** — D-18/19. Dedicated `/ui/health` view is for deep-inspection, not for "is it up right now." The strip answers "should I panic?" in half a second.
- **JS disabled = basic read flows still work** — D-05. Not a certified UAT path, but a free guardrail against htmx breakage and a nice gift for SSH-tunnel workflows. Costs nothing — we're already server-rendering.
- **Chat nav stub ships the contract, not the functionality** — D-28/29. Phase 12 fills the panel; `shell.html` and the route table don't churn. Eliminates the "where's chat?" question at dogfood UAT #1.
- **LOGIK-PROJEKT palette inheritance is web-idiom translation, not pixel clone** — UX-philosophy memory. UI-SPEC.md owns the exact translation; Phase 10 plans reference UI-SPEC for any styling finer than the three locked CSS custom properties.

</specifics>

<deferred>
## Deferred Ideas

- **Visible filter dropdowns/checkboxes** — v1.4 reconsider after dogfood UAT surfaces whether preset chips + grammar cover the artist case. Would live in the left rail of list views if added.
- **JS syntax highlighter for raw source** — v1.4+ if artists complain that plain `<pre>` is unreadable. Prism / highlight.js are both vendorable. Deferred to keep bundle < 30 KB.
- **Auto-refresh on list views (tools/execs/manifest)** — if dogfood UAT flips the call, 30 s cadence with same tab-visibility pause. Single-line template change.
- **Pagination visualization upgrade** — numbered page links, keyboard shortcuts, "jump to page N." Prev/next + "page N of M" covers v1.3.
- **Fragment-hash (`#`-based) state** — not needed while `hx-push-url` covers every state-changing interaction. Would only become interesting if a view ever has two independent axes of state (filter + sort within a sub-panel, say).
- **Live table sort** — columns would need client-side sort via Alpine. Preset chips cover the common orderings; deferred until UAT demand surfaces.
- **Boolean operators / quoted phrases / parens in the query grammar** — v1.4+. `q:` freeform search is the escape hatch for v1.3.
- **Dedicated "developer / engineer view" toggle** — if the artist/engineer split proves sharper than D-14's collapsed-sidecar handles, we add a per-user mode toggle. Deferred until UAT signal emerges.
- **Dark/light mode toggle** — locked to dark only in v1.3 (LOGIK-PROJEKT heritage). Light mode is a v1.4+ call once UI-SPEC is stable.
- **Keyboard shortcut surface beyond `/`, `Enter`, `Esc`** — deferred. `g t`-style Vim-nav chords or `?` help overlay are v1.4+ if operators ask.

</deferred>

---

*Phase: 10-web-ui*
*Context gathered: 2026-04-22*
