---
phase: 10-web-ui
plan: 02
subsystem: ui
tags: [jinja2, htmx, alpine, templates, sri, html]

# Dependency graph
requires:
  - phase: 10-web-ui plan 01
    provides: vendored htmx-2.0.10.min.js and alpinejs-3.14.1.min.js with computed SRI hashes

provides:
  - base.html: HTML doc skeleton with SRI-protected script tags and CSS link
  - shell.html: App chrome — top nav (5 links), persistent health strip, <main id=view-main> swap target, shellRoot() Alpine component
  - fragments/health_strip.html: Self-polling health strip partial with 7 service dots and click-to-expand
  - fragments/query_console.html: Reusable query console input + preset chip row with D-08 grammar parser
  - errors/not_found.html: 404 error template extending shell.html
  - errors/read_failed.html: 500 error template extending shell.html
  - Frozen template block contract: {% block title %}, {% block body %}, {% block head_extra %}, {% block view %}
  - active_view context variable convention for nav link highlighting

affects:
  - 10-03 (app wiring — will mount these templates via Jinja2Templates)
  - 10-04 (tools view — extends shell.html via {% block view %})
  - 10-05 (execs view — extends shell.html via {% block view %})
  - 10-06 (health view + health strip fragment route — renders health_strip.html)
  - 10-07 (manifest + chat views — extend shell.html)
  - 10-08 (UAT verification — smoke tests Jinja parseability)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Three-level template inheritance: base.html -> shell.html -> per-view (D-02)
    - Health strip outerHTML swap: fragment re-emits its own hx-trigger on every poll (D-06)
    - Alpine component granularity: one root shellRoot() on shell.html, per-view x-data nested inside views
    - D-08 grammar parser: client-side Alpine token parser, server never sees key:value grammar
    - SRI integrity enforcement: sha384 hash on both vendored script tags (D-31)

key-files:
  created:
    - forge_bridge/console/templates/base.html
    - forge_bridge/console/templates/shell.html
    - forge_bridge/console/templates/fragments/health_strip.html
    - forge_bridge/console/templates/fragments/query_console.html
    - forge_bridge/console/templates/errors/not_found.html
    - forge_bridge/console/templates/errors/read_failed.html
  modified: []

key-decisions:
  - "SRI hashes computed from vendored files in concurrent 10-01 worktree (files existed, SUMMARY not yet written); hashes match the committed JS bytes verbatim"
  - "shell.html uses #health-strip-container wrapper div with server-side {% include %} for HEALTH-04 first-paint; health_strip.html owns its own id=health-strip and hx-trigger for the poll contract"
  - "health_strip.html svc_order uses Jinja set to build the 7-service list with LLM backends collapsed to one dot — handles the list-vs-dict asymmetry in the health response shape"
  - "query_console.html uses tojson|safe only for Alpine component seed (JSON-encoded object — Jinja autoescape would break the quotes); all other values rely on autoescape"

patterns-established:
  - "Template block contract (frozen): base.html exposes title/head_extra/body; shell.html exposes view — Wave 2 plans extend shell.html and fill {% block view %}"
  - "active_view context variable: handlers pass active_view='tools'|'execs'|'manifest'|'health'|'chat' to shell context for nav highlighting"
  - "Error templates extend shell.html: artist keeps nav + health strip during failures, never lands on a bare error page"
  - "Fragment templates have no {% extends %}: health_strip.html and query_console.html are bare HTML for htmx swap targets"
  - "Alpine-to-htmx bridge: query console calls htmx.ajax() with target/#view-main to keep URL and swap contract consistent with hx-boost nav"

requirements-completed: [CONSOLE-01, CONSOLE-02, CONSOLE-04, HEALTH-04]

# Metrics
duration: 25min
completed: 2026-04-23
---

# Phase 10 Plan 02: Template Inheritance Foundation Summary

**Six Jinja2 templates establishing three-level inheritance (base.html -> shell.html -> per-view), SRI-protected vendored JS, persistent health strip with 7-dot service grid, and D-08 grammar parser in the query console partial**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-23T18:00:00Z
- **Completed:** 2026-04-23T18:29:25Z
- **Tasks:** 3
- **Files created:** 6

## Accomplishments

- `base.html` HTML doc skeleton with sha384 SRI hashes for htmx-2.0.10 and alpinejs-3.14.1, three exposed blocks (title, head_extra, body), color-scheme dark meta
- `shell.html` app shell with five-link top nav (hx-boost + hx-push-url), server-side health strip include for HEALTH-04 first-paint, single htmx swap target `<main id="view-main">`, `shellRoot()` Alpine root component with D-22 tab-visibility listener and D-11 slash-key focus
- `health_strip.html` self-polling fragment: outerHTML swap so it re-emits its own hx-trigger, 7 ordered service dots (mcp/flame/ws/llm/watcher/storage/port), Alpine click-to-expand panel
- `query_console.html` shared partial: D-08 grammar parser in Alpine with promoted->promoted_only and hash->code_hash API param mapping, D-10 inline amber error, D-11 Enter/Esc keyboard shortcuts
- Error templates (not_found.html, read_failed.html) extend shell.html so artist retains nav + health strip during failures

## Frozen Template Block Contract

Wave 2 view plans (10-04/05/06/07) MUST use these exact block names:

```jinja
{% extends "shell.html" %}
{% block title %}My View — Forge Console{% endblock %}
{% block view %}
  <!-- view content here -->
{% endblock %}
```

**Available blocks (do not rename):**
- `{% block title %}` — page `<title>` element (base.html)
- `{% block head_extra %}` — additional `<head>` content e.g. view-specific meta (base.html)
- `{% block body %}` — full body (base.html; only shell.html fills this directly)
- `{% block view %}` — the main content area inside `<main id="view-main">` (shell.html)

**Context variable convention:**
- `active_view`: str — one of `"tools"`, `"execs"`, `"manifest"`, `"health"`, `"chat"` — passed by handlers to highlight the correct nav link and set `aria-current="page"`

## Task Commits

1. **Task 1: base.html HTML doc skeleton** - `0e44097` (feat)
2. **Task 2: shell.html app shell** - `78daa3f` (feat)
3. **Task 3: fragments and error templates** - `d3fe650` (feat)

## Files Created

- `forge_bridge/console/templates/base.html` — HTML doc skeleton; SRI-protected htmx + Alpine script tags; CSS link; three blocks
- `forge_bridge/console/templates/shell.html` — App chrome; five-link nav; health strip include; `<main id="view-main">`; `shellRoot()` Alpine component
- `forge_bridge/console/templates/fragments/health_strip.html` — Self-polling health strip partial; 7 service dots; outerHTML swap; click-to-expand
- `forge_bridge/console/templates/fragments/query_console.html` — Query console input + chip row; D-08 Alpine parser; D-10 inline error; D-11 keyboard
- `forge_bridge/console/templates/errors/not_found.html` — 404 error template extending shell.html
- `forge_bridge/console/templates/errors/read_failed.html` — 500 error template extending shell.html

## Decisions Made

1. **SRI hash sourcing:** 10-01-SUMMARY.md did not yet exist (parallel Wave 1 execution). Hashes were computed directly from the committed vendored JS files in the 10-01 worktree (`openssl dgst -sha384 -binary | openssl base64 -A`). The computed hashes are: htmx `sha384-H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V`, alpine `sha384-l8f0VcPi/M1iHPv8egOnY/15TDwqgbOR1anMIJWvU6nLRgZVLTLSaNqi/TOoT5Fh`.

2. **Health strip container structure:** Plan Task 2 spec uses a `#health-strip-container` wrapper div with `{% include %}`, while the health_strip.html fragment carries its own `id="health-strip"` and `hx-trigger`. This keeps the polling contract entirely in the fragment (outerHTML swap re-emits trigger on each poll per D-06) while allowing shell.html's visibilitychange listener to `htmx.trigger` the `#health-strip` element directly.

3. **LLM backends dot aggregation:** The health API returns `llm_backends` as a list, not a dict. Used a Jinja `{% set %}` expression to collapse "all ok" → status-ok, otherwise → status-fail dot, matching D-18's "one dot per service" requirement.

## Deviations from Plan

None — plan executed exactly as written. SRI hash sourcing used the actual committed files (per the D-34 procedure documented in CONTEXT.md) rather than waiting for the 10-01 SUMMARY, which is a valid equivalent source.

## Issues Encountered

- `10-01-SUMMARY.md` did not exist at execution time (10-01 runs in the same Wave 1 parallel batch). Resolved by computing SRI hashes directly from the vendored JS files already committed in the 10-01 worktree, which is the same procedure documented in D-34.
- `jinja2` not installed in default Python environment; resolved via `pip3 install jinja2` for the parseability smoke test. (Runtime environment for the actual server has jinja2>=3.1 via pyproject.toml added in plan 10-01.)

## Next Phase Readiness

- **10-03 (app wiring):** Template directory exists at `forge_bridge/console/templates/`. Use `Jinja2Templates(directory=str(_CONSOLE_DIR / "templates"))` and attach to `app.state.templates`. The fragment route `/ui/fragments/health-strip` is required by health_strip.html (currently unregistered — 10-03 registers a 501 stub; 10-06 fills it).
- **10-04/05/06/07 (view plans):** All extend `shell.html` using `{% block view %}`. Pass `active_view` context var matching the view slug. Pass `query_params` dict and `preset_chips` list to views that include `query_console.html`.
- **Jinja parseability verified:** `python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('forge_bridge/console/templates'), autoescape=True); env.get_template('shell.html')"` exits 0.

---
*Phase: 10-web-ui*
*Completed: 2026-04-23*
