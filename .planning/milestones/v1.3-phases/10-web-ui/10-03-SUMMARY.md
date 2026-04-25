---
phase: 10-web-ui
plan: "03"
subsystem: console-ui-routing
tags: [starlette, jinja2, htmx, routing, wave-1]
dependency_graph:
  requires: []
  provides:
    - /ui/* and /ui/fragments/* route table (frozen for Wave 2)
    - app.state.templates (Jinja2Templates instance)
    - ui_handlers.py (8 full-page handlers)
    - ui_fragments.py (5 fragment handlers)
    - health_strip_fragment (Wave 1 functional implementation)
  affects:
    - forge_bridge/console/app.py (Starlette factory extended)
    - tests/test_console_routes.py (Phase 9 regression — still passes)
tech_stack:
  added:
    - jinja2>=3.1 (pip dep added to pyproject.toml)
  patterns:
    - Starlette StaticFiles mount at /ui/static anchored to package dir via Path(__file__).parent
    - app.state.templates for cross-handler template access (mirrors app.state.console_read_api)
    - 501 stubs for Wave 2 routes (never 404 — route table locked)
    - health_strip_fragment: real Wave 1 implementation (template-rendered, try/except, no traceback leak)
key_files:
  created:
    - forge_bridge/console/ui_handlers.py
    - forge_bridge/console/ui_fragments.py
    - forge_bridge/console/templates/fragments/health_strip.html
    - forge_bridge/console/static/forge-console.css (placeholder — plan 10-01 will replace)
    - forge_bridge/console/static/vendor/htmx-2.0.10.min.js (placeholder — plan 10-01 will replace)
    - forge_bridge/console/static/vendor/alpinejs-3.14.1.min.js (placeholder — plan 10-01 will replace)
    - tests/test_console_ui_routes_registered.py
  modified:
    - forge_bridge/console/app.py
    - pyproject.toml
decisions:
  - "Placeholder static assets created (CSS + vendor JS stubs) to let Wave 1 smoke tests pass without depending on plan 10-01 completing first"
  - "health_strip.html minimal template created in this plan (not waiting for 10-02) so health_strip_fragment returns 200 with id=health-strip + agg-pill required by test"
  - "TemplateResponse called with old positional signature (name, context) matching PATTERNS.md pattern — Starlette 0.52.1 emits deprecation warning but tests pass; Wave 2 plans will use same pattern"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-23"
  tasks_completed: 3
  files_created: 7
  files_modified: 2
---

# Phase 10 Plan 03: App Frame Wiring — Route Table + Handler Stubs Summary

**One-liner:** Extended Starlette factory with Jinja2Templates + StaticFiles + 13 new /ui/* and /ui/fragments/* routes, all locked as stubs so Wave 2 plans run fully parallel without touching app.py.

## Frozen Route Table (Wave 2 Contract)

Every route below is registered and returns 200 or 501 — never 404. Wave 2 plans fill in handler bodies; none touches app.py.

| Route | Handler | Module | Wave 1 Status | Wave 2 Plan |
|-------|---------|--------|---------------|-------------|
| `GET /ui/` | `ui_index_handler` | ui_handlers.py | Real (302 redirect to /ui/tools) | — |
| `GET /ui/tools` | `ui_tools_handler` | ui_handlers.py | 501 stub | 10-04 |
| `GET /ui/tools/{name}` | `ui_tool_detail_handler` | ui_handlers.py | 501 stub | 10-04 |
| `GET /ui/execs` | `ui_execs_handler` | ui_handlers.py | 501 stub | 10-05 |
| `GET /ui/execs/{code_hash}/{timestamp}` | `ui_exec_detail_handler` | ui_handlers.py | 501 stub | 10-05 |
| `GET /ui/manifest` | `ui_manifest_handler` | ui_handlers.py | 501 stub | 10-06 |
| `GET /ui/health` | `ui_health_view_handler` | ui_handlers.py | 501 stub | 10-06 |
| `GET /ui/chat` | `ui_chat_stub_handler` | ui_handlers.py | 501 stub | 10-07 |
| `GET /ui/fragments/health-strip` | `health_strip_fragment` | ui_fragments.py | Real (200 + template) | 10-06 (enhances) |
| `GET /ui/fragments/tools-table` | `tools_table_fragment` | ui_fragments.py | 501 stub | 10-04 |
| `GET /ui/fragments/execs-table` | `execs_table_fragment` | ui_fragments.py | 501 stub | 10-05 |
| `GET /ui/fragments/manifest-table` | `manifest_table_fragment` | ui_fragments.py | 501 stub | 10-06 |
| `GET /ui/fragments/health-view` | `health_view_fragment` | ui_fragments.py | 501 stub | 10-06 |
| Mount `/ui/static` | StaticFiles | app.py | Active | — |

## Patterns Wave 2 Handlers Must Use

### Reading data

```python
data = await request.app.state.console_read_api.get_tools()
```

Only call `get_tools()`, `get_tool(name)`, `get_executions(...)`, `get_manifest()`, `get_health()`. No direct ManifestService or ExecutionLog access. Phase 9 D-25.

### Rendering templates

```python
return request.app.state.templates.TemplateResponse(
    "path/to/template.html",
    {"request": request, "active_view": "tools", ...},
)
```

### Error rendering

```python
return request.app.state.templates.TemplateResponse(
    "errors/read_failed.html",
    {"request": request, "message": "Could not load tools", "active_view": None},
    status_code=500,
)
```

### Error posture (Phase 9 D-22 — never leak tracebacks)

```python
try:
    data = await request.app.state.console_read_api.get_<x>(...)
except Exception as exc:
    logger.warning("<handler> failed: %s", type(exc).__name__, exc_info=True)
    # render error template
```

### Logger per module

```python
logger = logging.getLogger(__name__)
```

No `print()` calls — ruff T20 is live for `forge_bridge/console/`.

## Stub vs. Real Implementations

**Real in Wave 1:**
- `ui_index_handler` — returns `RedirectResponse(url="/ui/tools", status_code=302)`
- `health_strip_fragment` — fetches health via `console_read_api.get_health()`, renders `fragments/health_strip.html` with `id="health-strip"` and `class="agg-pill"`. Falls back to degraded-but-valid data on exception.

**Stubs (501 inline HTML) — Wave 2 fills in:**
- All other 7 full-page handlers and 4 fragment handlers

## Deviations from Plan

### Auto-fix (Rule 3): Removed unused imports from ui_handlers.py

**Found during:** Task 1 verification — ruff check
**Issue:** The plan's code block imported `_parse_pagination`, `_parse_filters`, and `Optional` which are not used in the Wave 1 stubs
**Fix:** Removed `from typing import Optional`, `from forge_bridge.console.handlers import _parse_pagination, _parse_filters` — Wave 2 plans that implement the actual handlers will add them back
**Files modified:** `forge_bridge/console/ui_handlers.py`
**Commit:** 6c3a3b5

### Auto-add (Rule 2): Created minimal placeholder static assets

**Found during:** Task 3 — test `test_ui_static_mount_registered` and `test_vendored_js_assets_served` require actual files
**Issue:** Plan 10-01 creates the real CSS and vendor JS in a parallel worktree — not available at test time
**Fix:** Created placeholder stubs at the correct paths: `forge-console.css`, `vendor/htmx-2.0.10.min.js`, `vendor/alpinejs-3.14.1.min.js`. Plan 10-01 will overwrite them with the real files on merge.
**Files created:** 3 placeholder static assets
**Commit:** fcc71e4

### Auto-add (Rule 2): Created minimal health_strip.html template

**Found during:** Task 3 — `test_health_strip_fragment_returns_200_in_wave_1` requires `id="health-strip"` and `"agg-pill"` in the response body
**Issue:** Plan 10-02 creates the full template in a parallel worktree; `health_strip_fragment` uses `TemplateResponse("fragments/health_strip.html", ...)` which requires the template to exist
**Fix:** Created `forge_bridge/console/templates/fragments/health_strip.html` with minimal but correct implementation. Plan 10-02 may overwrite/extend it on merge.
**Files created:** `forge_bridge/console/templates/fragments/health_strip.html`
**Commit:** 6c3a3b5

### Deviation from PATTERNS.md: pyproject.toml also updated

**Found during:** Task 2 — jinja2 is not installed in the test environment
**Issue:** `Jinja2Templates` fails with `AssertionError` if jinja2 is not installed; pyproject.toml did not list it
**Fix:** Added `"jinja2>=3.1"` to dependencies and added `include` directives to `[tool.hatch.build.targets.wheel]` for templates and static assets (D-33 requirement from PATTERNS.md)
**Files modified:** `pyproject.toml`
**Commit:** fcc71e4

## Known Stubs

| Handler | File | Status | Resolved by |
|---------|------|--------|-------------|
| `ui_tools_handler` | ui_handlers.py | 501 stub | Plan 10-04 |
| `ui_tool_detail_handler` | ui_handlers.py | 501 stub | Plan 10-04 |
| `ui_execs_handler` | ui_handlers.py | 501 stub | Plan 10-05 |
| `ui_exec_detail_handler` | ui_handlers.py | 501 stub | Plan 10-05 |
| `ui_manifest_handler` | ui_handlers.py | 501 stub | Plan 10-06 |
| `ui_health_view_handler` | ui_handlers.py | 501 stub | Plan 10-06 |
| `ui_chat_stub_handler` | ui_handlers.py | 501 stub | Plan 10-07 |
| `tools_table_fragment` | ui_fragments.py | 501 stub | Plan 10-04 |
| `execs_table_fragment` | ui_fragments.py | 501 stub | Plan 10-05 |
| `manifest_table_fragment` | ui_fragments.py | 501 stub | Plan 10-06 |
| `health_view_fragment` | ui_fragments.py | 501 stub | Plan 10-06 |
| `forge-console.css` | static/ | placeholder | Plan 10-01 |
| `htmx-2.0.10.min.js` | static/vendor/ | placeholder | Plan 10-01 |
| `alpinejs-3.14.1.min.js` | static/vendor/ | placeholder | Plan 10-01 |

All stubs are intentional Wave 1 placeholders. They return 501 (not 404) so the route table contract is verified. Wave 2 plans fill in the bodies.

## Test Coverage

| Test | Scope | Result |
|------|-------|--------|
| `test_phase9_api_routes_return_200` (4 cases) | Phase 9 regression | PASS |
| `test_ui_root_redirects_to_tools` | /ui/ redirect | PASS |
| `test_ui_full_page_routes_registered` (7 cases) | Route registration | PASS |
| `test_ui_fragment_routes_registered` (5 cases) | Fragment registration | PASS |
| `test_health_strip_fragment_returns_200_in_wave_1` | Wave 1 functional | PASS |
| `test_ui_static_mount_registered` | Static mount | PASS |
| `test_vendored_js_assets_served` (2 cases) | Vendor assets | PASS |
| `test_app_state_templates_attached` | app.state wiring | PASS |
| **Total** | | **22/22 pass** |

## Self-Check: PASSED

- forge_bridge/console/ui_handlers.py: FOUND
- forge_bridge/console/ui_fragments.py: FOUND
- forge_bridge/console/app.py: FOUND (modified)
- forge_bridge/console/templates/fragments/health_strip.html: FOUND
- forge_bridge/console/static/forge-console.css: FOUND
- forge_bridge/console/static/vendor/htmx-2.0.10.min.js: FOUND
- forge_bridge/console/static/vendor/alpinejs-3.14.1.min.js: FOUND
- tests/test_console_ui_routes_registered.py: FOUND
- Commit 6c3a3b5: FOUND (Task 1 — ui_handlers + ui_fragments + health_strip template)
- Commit fcc71e4: FOUND (Task 2 — app.py + static placeholders + pyproject.toml)
- Commit 4433ff1: FOUND (Task 3 — smoke test)
- All 22 smoke tests: PASS
- All 59 Phase 9 regression tests: PASS
- ruff check forge_bridge/console/: PASS
