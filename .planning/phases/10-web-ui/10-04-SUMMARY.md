---
phase: 10-web-ui
plan: "04"
subsystem: console-ui-tools
tags: [starlette, jinja2, htmx, alpine, tools-view, wave-2]
dependency_graph:
  requires:
    - phase: 10-web-ui plan 02
      provides: shell.html block contract, query_console.html partial, error templates
    - phase: 10-web-ui plan 03
      provides: route table frozen, app.state.templates, ui_handlers stubs to replace
  provides:
    - /ui/tools full-page handler (TOOLS-01)
    - /ui/tools/{name} drilldown handler (TOOLS-02)
    - /ui/fragments/tools-table fragment handler
    - tools/list.html Jinja2 template
    - fragments/tools_table.html Jinja2 template (shared partial)
    - tools/detail.html Jinja2 template with 5-field provenance card
    - _filter_tools() in-Python filter helper (D-23)
    - _read_synth_source() with path-traversal guard (T-10-18)
    - _tools_preset_chips() D-09 chip roster
  affects:
    - 10-08 (UAT — tools view is the primary artist surface for CONSOLE-05)
    - 10-05 (execs view — same handler pattern)
    - 10-06 (manifest/health views — same handler pattern)

tech_stack:
  added: []
  patterns:
    - In-Python filter for UI-grammar params (D-23 — server-side filter deferred, done client-side in Alpine then in-Python in handler)
    - _filter_tools(tools, qp) reused by both list handler and fragment handler via import
    - _read_synth_source with Path.resolve() + relative_to() guard (T-10-18 path traversal mitigation)
    - ToolRecord.to_dict() called in handler before building template context (frozen dataclass → plain dict)
    - health_strip.html uses Jinja set health = health|default({}) to tolerate missing context on server-side include

key_files:
  created:
    - forge_bridge/console/templates/tools/list.html
    - forge_bridge/console/templates/fragments/tools_table.html
    - forge_bridge/console/templates/tools/detail.html
    - tests/test_ui_tools_view.py
  modified:
    - forge_bridge/console/ui_handlers.py (stubs replaced with real implementations)
    - forge_bridge/console/ui_fragments.py (tools_table_fragment stub replaced)
    - forge_bridge/console/templates/fragments/health_strip.html (health|default guard added)
    - tests/test_console_ui_routes_registered.py (404 check updated for real handlers)

key_decisions:
  - "Filtering done in-Python in ui_tools_handler/_filter_tools — Phase 9 /api/v1/tools has no server-side filter params (D-23); v1.3 correct posture"
  - "_read_synth_source uses Path.resolve() + relative_to(_SYNTH_ROOT.resolve()) before reading — T-10-18 path traversal guard, prevents escape from SYNTH_ROOT"
  - "health_strip.html adds Jinja set health = health|default({}) — server-side include from shell.html fails if page handler does not provide health in context; graceful degradation shows Error status until htmx polls the real /ui/fragments/health-strip"
  - "test_console_ui_routes_registered updated to allow handler-generated 404 — /ui/tools/example-tool correctly returns 404 (not found) from real handler; Starlette routing 404 has no HTML body so can be distinguished"
  - "tools_table.html fragment reused via {% include %} on both list.html and the fragment route — single source of truth for table markup"

patterns_established:
  - "Fragment reuse via {% include %}: list.html includes fragments/tools_table.html; fragment route renders the same template directly — one table definition, two render paths"
  - "_filter_tools imported in ui_fragments.py from ui_handlers — shared filter logic, no duplication"
  - "Preset chips hardcoded in handler (_tools_preset_chips), passed as list[dict] to template — no database dependency for chip labels"
  - "querystring built in handler and passed as template var — avoids reconstructing URL in template, cleaner separation"

requirements_completed: [TOOLS-01, TOOLS-02, CONSOLE-03]

# Metrics
duration: ~30min
completed: 2026-04-23
---

# Phase 10 Plan 04: Tools View — Handler + Templates + Tests Summary

**Full-page /ui/tools list with in-Python filter grammar, /ui/tools/{name} drilldown with 5-field amber provenance card and path-traversal-safe raw source reader, /ui/fragments/tools-table fragment — 14 pytest tests green**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-23T00:00:00Z
- **Completed:** 2026-04-23T00:30:00Z
- **Tasks:** 2
- **Files created:** 4
- **Files modified:** 4

## Accomplishments

- Three Jinja2 templates: `tools/list.html` (extends shell.html, includes query console + table fragment, staleness counter), `fragments/tools_table.html` (bare fragment with htmx row-click drilldown, D-16 hash truncation, empty state), `tools/detail.html` (5-field provenance `<dl>` with amber `<dd>`, consumer tag chips, raw source section for synth tools, sidecar JSON `<details>`)
- Three handler implementations: `ui_tools_handler` (fetches + filters + renders list), `ui_tool_detail_handler` (fetches single tool, reads synth source from disk with T-10-18 traversal guard), `tools_table_fragment` (bare table for htmx Refresh button swap)
- 14 functional pytest tests covering happy path, empty state, all four filters (origin/namespace/q/combined), query input pre-population (D-26), preset chips (D-09), fragment bare-HTML check, drilldown 5-field provenance + full code_hash (D-16), not-found 404, error posture (500 with no traceback)
- Two Rule 1 auto-fixes: `health_strip.html` health|default guard and `test_console_ui_routes_registered.py` 404 distinction

## Task Commits

1. **Task 1: tools/list.html + fragments/tools_table.html + tools/detail.html** - `a196328` (feat)
2. **Task 2 RED: failing tests** - `c48fdb0` (test)
3. **Task 2 GREEN: implement handlers** - `99a5534` (feat)

## ToolRecord Fields → Drilldown Section Mapping

| ToolRecord field | Template section | Display rule |
|-----------------|-----------------|--------------|
| `name` | `<h1 class="view-title">` | Plain text, autoescape |
| `origin` | provenance card `<dt>origin</dt>` | amber `<dd>`, plain |
| `code_hash` | provenance card `<dt>code_hash</dt>` | amber mono `<dd>`, FULL hash (D-16); list view: `[:8]` + title tooltip |
| `synthesized_at` | provenance card `<dt>synthesized_at</dt>` | amber mono `<dd>` |
| `version` | provenance card `<dt>version</dt>` | amber `<dd>` |
| `observation_count` | provenance card `<dt>observation_count</dt>` | amber `<dd>` |
| `tags` | chip row below provenance card | `chip chip-readonly` spans, one per tag |
| `origin == 'synthesized'` + disk file | raw source `<pre>` block | Only rendered if `raw_code` truthy (separate context var, not ToolRecord field) |
| all fields via `to_dict()` | sidecar JSON `<details>` | `tool | tojson(indent=2)` — full serialized dict |

## _filter_tools UI-Grammar-to-Phase-9-API-Param Contract

`_filter_tools(tools, qp)` applies filter params that the query console Alpine parser sends as plain URL query params. This is the D-23 posture: v1.3 does filtering in-Python because `/api/v1/tools` has no server-side filter params.

| URL param | Filter logic |
|-----------|-------------|
| `origin=X` | `t.origin == X` |
| `namespace=X` | `t.namespace == X` |
| `readonly=X` | `dict(t.meta).get("read_only_hint", "").lower() == X.lower()` |
| `q=X` | `X.lower() in t.name.lower()` (substring match) |

The Alpine parser in `query_console.html` translates UI tokens to these URL params:
- `origin:synthesized` → `?origin=synthesized`
- `namespace:flame` → `?namespace=flame`
- `q:recent` → `?q=recent`

The same `_filter_tools` function is imported in `ui_fragments.py` and used by `tools_table_fragment` so the Refresh button fragment respects the same filters as the full page.

## _read_synth_source Disk-Read Contract + Path-Traversal Guard

```python
_SYNTH_ROOT = Path(os.environ.get(
    "FORGE_SYNTH_ROOT",
    str(Path.home() / ".forge-bridge" / "tools" / "synth"),
))

def _read_synth_source(name: str) -> str | None:
    candidate = _SYNTH_ROOT / f"{name}.py"
    try:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(_SYNTH_ROOT.resolve())
        except ValueError:
            return None  # traversal attempt — reject silently
        if resolved.is_file():
            return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning(...)
    return None
```

- Path is constructed as `_SYNTH_ROOT / f"{name}.py"` — no user input goes directly to filesystem without this join
- `candidate.resolve()` normalizes the path (collapses `../`, symlinks)
- `resolved.relative_to(_SYNTH_ROOT.resolve())` raises `ValueError` if the resolved path escapes the root — this is the T-10-18 guard
- A crafted name like `../../etc/passwd` would resolve outside `_SYNTH_ROOT` and be rejected before any file read

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] health_strip.html crashed when health context missing**
- **Found during:** Task 2 GREEN phase — first test run
- **Issue:** `shell.html` does `{% include "fragments/health_strip.html" %}` for server-side first-paint, but page handlers (`ui_tools_handler`) do not put `health` in the template context. The template used `health.status` directly, raising `UndefinedError`.
- **Fix:** Added `{% set health = health|default({'status': 'fail', 'services': {}, 'instance_identity': {}}) %}` at the top of `health_strip.html`. On first-paint from a non-health handler, the strip shows "Error" status; htmx polls `/ui/fragments/health-strip` within 10 s and refreshes with real data.
- **Files modified:** `forge_bridge/console/templates/fragments/health_strip.html`
- **Committed in:** `99a5534` (Task 2 GREEN commit)

**2. [Rule 1 - Bug] test_console_ui_routes_registered expected != 404 but real handler returns 404**
- **Found during:** Task 2 GREEN phase — regression suite
- **Issue:** Wave 1 test asserted `status_code != 404` for all `/ui/*` routes. The stub returned 501; the real `ui_tool_detail_handler` correctly returns 404 when the tool doesn't exist (fake_read_api.get_tool returns None). Test failed.
- **Fix:** Updated the assertion to distinguish a Starlette routing 404 (plain-text body, no `<html>`) from a handler-generated 404 (renders errors/not_found.html, has `<html>`). A handler 404 proves the route IS registered.
- **Files modified:** `tests/test_console_ui_routes_registered.py`
- **Committed in:** `99a5534` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Known Stubs

None in this plan's scope. `ui_tools_handler`, `ui_tool_detail_handler`, and `tools_table_fragment` are all fully implemented. The other Wave 2 stubs (execs, manifest, health, chat) remain as 501 — outside this plan's scope.

## Threat Surface Scan

No new network endpoints beyond those declared in the plan's `<threat_model>`. T-10-18 path-traversal guard implemented as specified. T-10-19 (XSS) — autoescape on, no `| safe` on any ToolRecord field. T-10-20 (error traceback) — verified by `test_ui_tools_500_renders_error_template_without_traceback`.

## Self-Check: PASSED

- forge_bridge/console/templates/tools/list.html: FOUND
- forge_bridge/console/templates/fragments/tools_table.html: FOUND
- forge_bridge/console/templates/tools/detail.html: FOUND
- forge_bridge/console/ui_handlers.py (real impl): FOUND
- forge_bridge/console/ui_fragments.py (tools_table_fragment real): FOUND
- tests/test_ui_tools_view.py: FOUND
- Commit a196328 (templates): FOUND
- Commit c48fdb0 (RED tests): FOUND
- Commit 99a5534 (GREEN handlers): FOUND
- 14/14 test_ui_tools_view tests: PASS
- 37/37 regression tests (test_console_routes + test_console_ui_routes_registered): PASS
- ruff check forge_bridge/console/ui_handlers.py forge_bridge/console/ui_fragments.py tests/test_ui_tools_view.py: PASS

---
*Phase: 10-web-ui*
*Completed: 2026-04-23*
