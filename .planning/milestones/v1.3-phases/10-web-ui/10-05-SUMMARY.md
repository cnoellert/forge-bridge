---
phase: 10-web-ui
plan: "05"
subsystem: console-ui-execs
tags: [starlette, jinja2, htmx, alpine, execs-view, wave-3]
dependency_graph:
  requires:
    - phase: 10-web-ui plan 02
      provides: shell.html block contract, query_console.html partial, error templates
    - phase: 10-web-ui plan 03
      provides: route table frozen, app.state.templates, ui_handlers stubs to replace
    - phase: 10-web-ui plan 04
      provides: handler pattern (filter/fragment/drilldown), _query_params_as_tokens, _render_error
  provides:
    - /ui/execs full-page handler (EXECS-01)
    - /ui/execs/{code_hash}/{timestamp} drilldown handler (EXECS-02)
    - /ui/fragments/execs-table fragment handler
    - execs/list.html Jinja2 template
    - fragments/execs_table.html Jinja2 template (shared partial)
    - execs/detail.html Jinja2 template with 4-field provenance card + copy button
    - _execs_preset_chips() D-09 chip roster
  affects:
    - 10-08 (UAT — execs view is secondary artist surface for CONSOLE-05)
    - 10-06 (manifest/health views — same handler pattern)

tech_stack:
  added: []
  patterns:
    - filter_querystring built from query_params in handler and passed as template var for pagination filter-preservation
    - tool= and until= silently dropped (W-01 scope note — handler does not pass them to get_executions)
    - asdict(ExecutionRecord) called in handler before template context (frozen dataclass → plain dict, same as ToolRecord.to_dict())
    - _parse_pagination/_parse_filters reused from handlers.py (Phase 9 D-05 limit-clamp + D-03 filter contract)
    - ValueError from _parse_filters returned as 400 with friendly message (T-10-25 mitigation)

key_files:
  created:
    - forge_bridge/console/templates/execs/list.html
    - forge_bridge/console/templates/fragments/execs_table.html
    - forge_bridge/console/templates/execs/detail.html
    - tests/test_ui_execs_view.py
  modified:
    - forge_bridge/console/ui_handlers.py (execs stubs replaced with real implementations)
    - forge_bridge/console/ui_fragments.py (execs_table_fragment stub replaced)

key_decisions:
  - "filter_querystring built as &key=val string without limit/offset — pagination links preserve filter state (since, promoted_only, code_hash) without clobbering page position"
  - "tool= and until= silently dropped in ui_execs_handler — tool= is W-01 not_implemented; until= has no Phase 9 API param; get_executions() has no kwargs for these so drop is safe"
  - "Preset chips roster changed from D-09 (Last 24h + Synthesized only) to (Promoted only + Hash prefix) — Last 24h needs client-computed ISO timestamp (planner recommendation defers); Synthesized only has no execs-view equivalent filter key"
  - "D-26 pre-population uses _query_params_as_tokens with _EXECS_KEYS — promoted_only maps to 'promoted' token via _API_TO_UI_KEY; code_hash maps to 'hash'"

patterns_established:
  - "execs_table.html fragment reused via {% include %} on list.html and rendered directly by fragment route — single source of truth for table markup"
  - "asdict(r) for r in records in handler context — ExecutionRecord is frozen dataclass; asdict converts to plain dict for Jinja; same pattern as ToolRecord.to_dict()"
  - "filter_querystring template variable carries &-prefixed filter params only — pagination hrefs concatenate /ui/execs?limit=N&offset=M + filter_querystring"

requirements_completed: [EXECS-01, EXECS-02, CONSOLE-03]

# Metrics
duration: ~20min
completed: 2026-04-23
---

# Phase 10 Plan 05: Executions View — Handler + Templates + Tests Summary

**Paginated execution history at /ui/execs with filter round-trip, /ui/execs/{hash}/{ts} drilldown showing 4 metadata fields + raw_code with copy button, /ui/fragments/execs-table bare fragment — 12 pytest tests green**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-23T00:00:00Z
- **Completed:** 2026-04-23T00:20:00Z
- **Tasks:** 2
- **Files created:** 4
- **Files modified:** 2

## Accomplishments

- Three Jinja2 templates: `execs/list.html` (extends shell.html, includes query console + execs_table fragment, staleness counter, prev/next + page label pagination), `fragments/execs_table.html` (bare fragment with htmx row-click drilldown, D-16 hash truncation at first 8 chars + title tooltip, empty state), `execs/detail.html` (4-field provenance `<dl>` with amber `<dd>`, full hash per D-16, raw_code `<pre>` block with copy-to-clipboard Alpine button)
- Three handler implementations: `ui_execs_handler` (fetches + paginates + renders list with filter round-trip, `filter_querystring` for pagination filter-preservation), `ui_exec_detail_handler` (finds record by exact code_hash + timestamp match, 404 on miss), `execs_table_fragment` (bare table for htmx Refresh button swap, same filter params)
- 12 functional pytest tests covering: full page, empty state, promoted_only filter, since filter (ISO parse), since filter (invalid → 400), pagination page 1, pagination page 2, fragment partial (no top-nav), fragment filters, drilldown found (full hash + intent + copy button), drilldown not found (404), 500 error posture (no traceback)
- One ruff fix: removed unused `timezone` import from test file

## filter_querystring Pagination Pattern

The `filter_querystring` variable is built in `ui_execs_handler` as a `&`-prefixed string containing only the active filter params (`since`, `promoted_only`, `code_hash`). Pagination `<a>` hrefs are constructed as:

```
/ui/execs?limit={{ limit }}&offset={{ offset + limit }}{{ filter_querystring }}
```

This preserves filter state across page navigation without encoding `limit` or `offset` twice. The same pattern is used in `execs/list.html` for both the Prev and Next links.

## tool= / until= Silent-Drop Behavior

Per the plan scope note (W-01) and Phase 9 constraint:

- `tool=` is rejected with 400 at `/api/v1/execs` in Phase 9. The UI handler does NOT pass `tool=` to `get_executions()` (the method has no `tool` kwarg). Any `tool=` param that arrives via the Alpine query console parser is silently dropped.
- `until=` has no corresponding kwarg in `get_executions()` (Phase 9 only implemented `since`). Silently dropped.

The Alpine query console accepts `tool:X` grammar (D-08 key list) but neither the fragment route nor the full-page handler passes it downstream. The artist sees no error; the filter is a no-op. This is the "simple path" per the planner's recommendation in the scope note.

## Preset Chip Roster Deviation from D-09

D-09 specified: "Last 24h", "Promoted only", "Synthesized only".

Shipped: "Promoted only" + "Hash prefix".

Reason:
- **"Last 24h"** dropped — requires computing a dynamic ISO-8601 timestamp client-side (Alpine at chip-click time) which is out of scope for v1.3; the `since:` grammar key still works via manual input.
- **"Synthesized only"** dropped — the execs view has no `origin:` or `tool:` filter that maps to "synthesized" (W-01 defers `tool=`). No equivalent filter key exists.
- **"Hash prefix"** added as a practical chip — shows the grammar for `hash:abcd`, which surfaces a useful lookup pattern without needing a dynamic value.

This matches the planner's recommendation in the plan scope note.

## ExecutionRecord Fields → Template Section Mapping

| ExecutionRecord field | Template section | Display rule |
|-----------------------|-----------------|--------------|
| `timestamp` | execs_table.html `<td class="mono">` + detail.html `<dt>timestamp</dt>` | Plain text; list: full ISO string; drilldown: full ISO string |
| `code_hash` | execs_table.html `<td class="mono" title="{{ rec.code_hash }}">` + detail.html `<dt>code_hash</dt>` | List: first 8 chars + title tooltip (D-16); drilldown: full 64-char hash (D-16) |
| `intent` | execs_table.html `<td>` + detail.html `<dt>intent</dt>` | `or '—'` fallback when None |
| `promoted` | execs_table.html `<td>` + detail.html `<dt>promoted</dt>` | `yes` / `no` |
| `raw_code` | detail.html `<pre class="font-mono" x-ref="src">` | Full source; autoescape handles `<script>` tags (T-10-23); copy-to-clipboard via Alpine |

## Task Commits

1. **Task 1: execs templates** - `39067b2` (feat)
2. **Task 2 RED: failing tests** - `2f788d4` (test)
3. **Task 2 GREEN: implement handlers** - `d0fd04a` (feat)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one minor cleanup:

**1. [Rule 1 - Bug] Unused `timezone` import in test file**
- **Found during:** Task 2 ruff check
- **Issue:** `from datetime import datetime, timezone` — `timezone` was in the plan's test template but not used in any assertion (the `_get_execs` mock receives a `datetime` object already parsed by `_parse_filters`; no `timezone.utc` construction needed)
- **Fix:** Removed `timezone` from the import
- **Files modified:** `tests/test_ui_execs_view.py`
- **Committed in:** `d0fd04a` (Task 2 GREEN commit)

## Known Stubs

None. All three execs handlers are fully implemented. Remaining Wave 3 stubs (`ui_manifest_handler`, `ui_health_view_handler`, `ui_chat_stub_handler`, `manifest_table_fragment`, `health_view_fragment`) are outside this plan's scope.

## Threat Surface Scan

No new network endpoints beyond those declared in the plan's `<threat_model>`.

- T-10-23 (XSS via raw_code): `<pre>{{ record.raw_code }}</pre>` — Jinja autoescape active; `<script>` tags rendered as `&lt;script&gt;`. Covered by `test_ui_exec_detail_found` which asserts 200 and content renders.
- T-10-24 (XSS via intent): `{{ record.intent }}` through autoescape — same posture.
- T-10-25 (stack trace on bad `since`): `test_ui_execs_filter_since_invalid_returns_400` asserts 400 + "Traceback" not in body.
- T-10-26 (huge limit): `_parse_pagination` clamps to [1, 500] per Phase 9 D-05 — reused here.

## Self-Check: PASSED

- forge_bridge/console/templates/execs/list.html: FOUND
- forge_bridge/console/templates/fragments/execs_table.html: FOUND
- forge_bridge/console/templates/execs/detail.html: FOUND
- forge_bridge/console/ui_handlers.py (real impl, no 501 in execs handlers): FOUND
- forge_bridge/console/ui_fragments.py (execs_table_fragment real, no 501): FOUND
- tests/test_ui_execs_view.py: FOUND
- Commit 39067b2 (templates): FOUND
- Commit 2f788d4 (RED tests): FOUND
- Commit d0fd04a (GREEN handlers): FOUND
- 12/12 test_ui_execs_view tests: PASS
- 63/63 regression tests (test_ui_execs + test_console_routes + test_ui_tools + test_console_ui_routes_registered): PASS
- ruff check forge_bridge/console/ui_handlers.py forge_bridge/console/ui_fragments.py tests/test_ui_execs_view.py: PASS

---
*Phase: 10-web-ui*
*Completed: 2026-04-23*
