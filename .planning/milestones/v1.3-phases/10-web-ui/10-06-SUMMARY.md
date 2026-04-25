---
phase: 10-web-ui
plan: "06"
subsystem: console-ui-manifest-health
tags: [starlette, jinja2, htmx, alpine, manifest-view, health-view, wave-4]
dependency_graph:
  requires:
    - phase: 10-web-ui plan 02
      provides: shell.html block contract, query_console.html partial, error templates
    - phase: 10-web-ui plan 03
      provides: route table frozen, app.state.templates, ui_handlers stubs to replace
    - phase: 10-web-ui plan 04
      provides: handler pattern (_filter_tools, _query_params_as_tokens, _render_error)
    - phase: 10-web-ui plan 05
      provides: execs handler pattern (filter_querystring, fragment reuse)
  provides:
    - /ui/manifest full-page handler (MFST-04)
    - /ui/health full-page handler (HEALTH-01)
    - /ui/fragments/manifest-table fragment handler
    - /ui/fragments/health-view fragment handler
    - manifest/list.html Jinja2 template
    - fragments/manifest_table.html Jinja2 template (shared partial)
    - health/detail.html Jinja2 template (auto-polls health-view at 5s)
    - fragments/health_view.html Jinja2 template (bare fragment, bare health grid)
    - _filter_manifest_entries() in-Python filter with status derivation
    - _manifest_preset_chips() D-09 chip roster
  affects:
    - 10-08 (UAT — manifest + health views are Phase 10 MFST-04/HEALTH-01 surfaces)
    - 10-07 (chat stub — only remaining Wave 4 stub)

tech_stack:
  added: []
  patterns:
    - _filter_manifest_entries(entries, qp) shared between ui_manifest_handler and manifest_table_fragment via import (same pattern as _filter_tools in plan 10-04)
    - Status derivation in _filter_manifest_entries: active (code_hash + obs_count > 0) / loaded (code_hash only) / orphaned (no code_hash)
    - health/detail.html wraps #health-view-content with hx-trigger="every 5s[!document.hidden]" and hx-swap="innerHTML" — dedicated view polls faster than strip (5s vs 10s, D-20)
    - health_view.html uses {% set health = health|default({...}) %} guard — consistent with health_strip.html defensive default pattern from plan 10-04

key_files:
  created:
    - forge_bridge/console/templates/manifest/list.html
    - forge_bridge/console/templates/fragments/manifest_table.html
    - forge_bridge/console/templates/health/detail.html
    - forge_bridge/console/templates/fragments/health_view.html
    - tests/test_ui_manifest_view.py
    - tests/test_ui_health_view.py
  modified:
    - forge_bridge/console/ui_handlers.py (manifest + health stubs replaced)
    - forge_bridge/console/ui_fragments.py (manifest_table + health_view stubs replaced)

key_decisions:
  - "Status derivation in _filter_manifest_entries: active = has code_hash AND obs_count > 0; loaded = has code_hash but obs_count == 0; orphaned = no code_hash — provides a meaningful Status column in the manifest table without requiring sidecar parsing"
  - "status=orphaned filter heuristic: obs_count == 0 OR missing code_hash — matches CONTEXT.md D-09 planner note: orphaned = observation_count == 0 OR missing code_hash"
  - "Manifest table row drilldown links to /ui/tools/{name} — manifest is the synthesized-subset of tools; reusing the existing tools drilldown avoids creating a duplicate detail view (plan spec: key_links)"
  - "health/detail.html uses hx-swap='innerHTML' on #health-view-content — distinct from health strip which uses outerHTML (UI-SPEC Interaction Contracts rows 6-7)"
  - "health_view.html renders 6 fixed service cards + LLM backends loop — LLM backends are a variable-length list so they render separately from the fixed-key services"

patterns_established:
  - "_filter_manifest_entries imported in ui_fragments.py from ui_handlers — shared filter, no duplication (mirrors _filter_tools pattern from plan 10-04)"
  - "Preset chips hardcoded in handler (_manifest_preset_chips), passed as list[dict] to template — same pattern as _tools_preset_chips and _execs_preset_chips"
  - "querystring built in handler and passed as template var — fragment refresh button appends the current querystring so filter state is preserved on Refresh"
  - "health_view.html uses {% set health = health|default({...}) %} guard at top — defensive default for server-side include from health/detail.html"

requirements_completed: [MFST-04, HEALTH-01, HEALTH-04, CONSOLE-03]

# Metrics
duration: ~15min
completed: 2026-04-23
---

# Phase 10 Plan 06: Manifest Browser + Health Dedicated View — Summary

**Manifest browser at /ui/manifest with q/status filter grammar + status derivation, dedicated health view at /ui/health auto-polling every 5s with 6 service cards + LLM backends + instance identity — 9 pytest tests green**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-23
- **Completed:** 2026-04-23
- **Tasks:** 2
- **Files created:** 6
- **Files modified:** 2

## Accomplishments

- Four Jinja2 templates: `manifest/list.html` (extends shell.html, includes query console + table fragment, staleness counter, Refresh manifest CTA), `fragments/manifest_table.html` (bare fragment, 6-col table: Name/Code hash/Synthesized/Version/Obs count/Status, htmx row drilldown to /ui/tools/{name}, Manifest is empty state), `health/detail.html` (extends shell.html, wraps health-view content in #health-view-content polling /ui/fragments/health-view every 5s with tab-pause), `fragments/health_view.html` (bare fragment, aggregate status pill + version + ts, health-grid with 6 fixed service cards, LLM backends looped separately, instance_identity section)

- Four handler implementations: `ui_manifest_handler` (fetches manifest via get_manifest(), applies _filter_manifest_entries, renders manifest/list.html with D-09 preset chips and D-26 pre-population), `ui_health_view_handler` (fetches health via get_health(), renders health/detail.html), `manifest_table_fragment` (bare table for htmx Refresh swap, respects same filter params), `health_view_fragment` (bare health grid for 5s auto-poll)

- 9 functional pytest tests: 6 for manifest (full page, empty state, q filter, status:orphaned filter, fragment bare-HTML check, 500 no-traceback) and 3 for health (full page with all service labels + LLM backends + Degraded pill + instance identity, fragment bare-HTML check, 500 no-traceback)

## Manifest Status Derivation Logic

`_filter_manifest_entries()` derives a `status` field for each entry before passing to the template:

| Condition | Derived status |
|-----------|---------------|
| `code_hash` present AND `observation_count > 0` | `active` |
| `code_hash` present AND `observation_count == 0` | `loaded` |
| `code_hash` absent | `orphaned` |

Filter behavior:
- `status=orphaned`: excludes entries where `obs_count > 0 AND code_hash present`
- `status=loaded`: excludes entries where `code_hash` is missing
- No `status` param: all entries pass (status is still derived for display)

## Health View 5s Cadence + Tab-Pause Wiring

`health/detail.html` wraps the health content in:

```html
<div id="health-view-content"
     hx-get="/ui/fragments/health-view"
     hx-trigger="every 5s[!document.hidden]"
     hx-swap="innerHTML"
     hx-push-url="false">
```

- **5s cadence** (D-20): faster than strip's 10s — dedicated view is for active diagnostics, not ambient awareness
- **`[!document.hidden]` tab-pause** (D-22): htmx-native, no JS side-channel. When tab is hidden, polling pauses. Shell's `visibilitychange` listener fires an immediate health-strip refresh on un-hide; the health view's own hx-trigger resumes naturally.
- **`innerHTML` swap** (UI-SPEC row 7): distinct from health strip's `outerHTML` — the outer `#health-view-content` div and its poll declaration persist; only the inner content is replaced.

## LLM Backend List-to-Cards Rendering Pattern

The health response's `services.llm_backends` is a list (variable length). `health_view.html` handles it separately from the fixed-key services:

```jinja
{% for name, svc in [('MCP server', health.services.mcp|default({})), ...] %}
  {# fixed 6 service cards #}
{% endfor %}

{% for backend in health.services.llm_backends|default([]) %}
  {# one card per LLM backend: LLM: {backend.name} #}
{% endfor %}
```

This pattern avoids special-casing the list inside the fixed-key loop and allows zero LLM backends (no cards rendered) or many (one card each).

## Task Commits

1. **Task 1: manifest + health templates** — `96021a9` (feat)
2. **Task 2 RED: failing tests** — `35f5a22` (test)
3. **Task 2 GREEN: implement handlers** — `6536cf2` (feat)

## Deviations from Plan

None — plan executed exactly as written. All four templates match the plan's Jinja snippets. All four handlers implement the exact logic documented in the plan's `<action>` blocks. Status derivation, filter heuristics, and empty-state copy all match the spec.

## Known Stubs

None in this plan's scope. `ui_manifest_handler`, `ui_health_view_handler`, `manifest_table_fragment`, and `health_view_fragment` are all fully implemented with no 501 responses.

Remaining stubs outside this plan's scope: `ui_chat_stub_handler` (plan 10-07).

## Threat Surface Scan

No new network endpoints beyond those declared in the plan's `<threat_model>`.

- T-10-28 (XSS via manifest name/tags): autoescape active; `{{ entry.name }}` and `{{ entry.status }}` go through HTML escaping. Status is derived from the filter function (hardcoded strings: "active", "loaded", "orphaned") — not from user input or API data directly.
- T-10-30 (DoS via multi-tab health polling): `get_health()` uses Phase 9 D-17 asyncio.wait_for 2s bounds per sub-check. Tab-visibility pause reduces idle-tab waste to zero.
- T-10-31 (DoS via pathological q= input): _filter_manifest_entries is O(N) scan; N bounded by ManifestService size (tens at most).
- T-10-32 (500 traceback leak): both handlers + both fragments use try/except Exception, log type(exc).__name__ + exc_info=True, return error template or bland fragment. Tests enforce no "boom" or "Traceback" in response body.

## Self-Check: PASSED

- forge_bridge/console/templates/manifest/list.html: FOUND
- forge_bridge/console/templates/fragments/manifest_table.html: FOUND
- forge_bridge/console/templates/health/detail.html: FOUND
- forge_bridge/console/templates/fragments/health_view.html: FOUND
- forge_bridge/console/ui_handlers.py (real manifest + health impl, no 501): FOUND
- forge_bridge/console/ui_fragments.py (real manifest_table + health_view, no 501): FOUND
- tests/test_ui_manifest_view.py: FOUND
- tests/test_ui_health_view.py: FOUND
- Commit 96021a9 (templates): FOUND
- Commit 35f5a22 (RED tests): FOUND
- Commit 6536cf2 (GREEN handlers): FOUND
- 9/9 test_ui_manifest_view + test_ui_health_view tests: PASS
- 72/72 full regression suite: PASS
- ruff check ui_handlers.py ui_fragments.py test files: PASS

---
*Phase: 10-web-ui*
*Completed: 2026-04-23*
