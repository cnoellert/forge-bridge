# Phase 10: Web UI — Pattern Map

**Mapped:** 2026-04-23
**Phase:** 10 — web-ui
**Files analyzed:** 15 new/modified files
**Analogs found:** 12 / 15 (3 no-analog — first Jinja templates in the repo)

## Scope note

Phase 10 extends the **existing** `forge_bridge/console/` Starlette app shipped by Phase 9. No new package. No new process. The `_lifespan` in `forge_bridge/mcp/server.py` already hands a `ConsoleReadAPI` to `build_console_app(read_api)`; Phase 10 only adds routes, templates, and static assets to that same `Starlette(...)` instance. The single `ConsoleReadAPI` stays the sole read layer — all new `/ui/*` and `/ui/fragments/*` handlers call `request.app.state.console_read_api`, exactly like the `/api/v1/*` handlers do today.

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `forge_bridge/console/app.py` (MODIFIED) | app-factory / route-registry | request-response | self (Phase 9) | exact (self-extend) |
| `forge_bridge/console/handlers.py` (MODIFIED or split) | route-handler | request-response, reads via `ConsoleReadAPI` | `forge_bridge/console/handlers.py` Phase 9 handlers | exact |
| `forge_bridge/console/ui_handlers.py` (NEW, optional split) | route-handler (full-page) | `ConsoleReadAPI` → Jinja2 → HTML | `handlers.tools_handler` / `handlers.execs_handler` | role-match |
| `forge_bridge/console/ui_fragments.py` (NEW, optional split) | route-handler (partial) | `ConsoleReadAPI` → Jinja2 partial → HTML | `handlers.tools_handler` | role-match |
| `forge_bridge/console/templates/base.html` (NEW) | template (doc skeleton) | SSR | none in repo — use UI-SPEC | no-analog (first template) |
| `forge_bridge/console/templates/shell.html` (NEW) | template (app shell) | SSR + htmx swap target | base.html (self-extend) | no-analog (first template) |
| `forge_bridge/console/templates/tools/list.html` (NEW) | template (view) | SSR from `ConsoleReadAPI.get_tools()` | `resources.tools_list` JSON shape | role-match |
| `forge_bridge/console/templates/tools/detail.html` (NEW) | template (view) | SSR from `ConsoleReadAPI.get_tool(name)` | `resources.tool_detail` JSON shape | role-match |
| `forge_bridge/console/templates/execs/list.html` (NEW) | template (view) | SSR from `ConsoleReadAPI.get_executions(...)` | `handlers.execs_handler` | role-match |
| `forge_bridge/console/templates/execs/detail.html` (NEW) | template (view) | SSR per `code_hash/timestamp` | `handlers.execs_handler` (snapshot filter) | role-match |
| `forge_bridge/console/templates/manifest/list.html` (NEW) | template (view) | SSR from `ConsoleReadAPI.get_manifest()` | `resources.synthesis_manifest` | role-match |
| `forge_bridge/console/templates/health/detail.html` (NEW) | template (view) | SSR from `ConsoleReadAPI.get_health()` | `resources.health` | role-match |
| `forge_bridge/console/templates/chat/stub.html` (NEW) | template (stub view) | SSR (no data) | shell.html only | role-match |
| `forge_bridge/console/templates/fragments/*.html` (NEW) | fragment-template | htmx partial swap | per-view templates | role-match |
| `forge_bridge/console/static/forge-console.css` (NEW) | static-asset (CSS) | served via `StaticFiles` | UI-SPEC `:root` token block | no-analog (first CSS) |
| `forge_bridge/console/static/vendor/htmx-2.0.10.min.js` (NEW) | static-asset (vendored JS) | served via `StaticFiles` | n/a | no-analog |
| `forge_bridge/console/static/vendor/alpinejs-3.14.1.min.js` (NEW) | static-asset (vendored JS) | served via `StaticFiles` | n/a | no-analog |
| `forge_bridge/console/static/vendor/README.md` (NEW) | doc (asset-update procedure) | n/a | D-34 text in CONTEXT.md | exact |
| `pyproject.toml` (MODIFIED) | package-metadata | — | self | exact |

---

## Pattern Assignments

### `forge_bridge/console/app.py` — MODIFIED (app-factory)

**Analog:** itself, Phase 9.

**Excerpt to extend** — `forge_bridge/console/app.py` L30-55:

```python
def build_console_app(read_api: "ConsoleReadAPI") -> Starlette:
    routes = [
        Route("/api/v1/tools", tools_handler, methods=["GET"]),
        Route("/api/v1/tools/{name}", tool_detail_handler, methods=["GET"]),
        Route("/api/v1/execs", execs_handler, methods=["GET"]),
        Route("/api/v1/manifest", manifest_handler, methods=["GET"]),
        Route("/api/v1/health", health_handler, methods=["GET"]),
    ]
    middleware = [ Middleware(CORSMiddleware, ...) ]
    app = Starlette(routes=routes, middleware=middleware)
    app.state.console_read_api = read_api
    return app
```

**Phase 10 delta — append-only inside the same factory:**

1. Add Jinja2 templates instance + static mount imports (top of file):
   ```python
   from pathlib import Path
   from starlette.staticfiles import StaticFiles
   from starlette.templating import Jinja2Templates
   ```
2. Instantiate `Jinja2Templates` once, attach to `app.state` (mirrors `app.state.console_read_api` pattern from L54):
   ```python
   _CONSOLE_DIR = Path(__file__).parent
   templates = Jinja2Templates(directory=str(_CONSOLE_DIR / "templates"))
   # autoescape is on by default in Jinja2Templates; keep it on (D-discretion).
   ```
3. Add `/ui/*` full-page Routes (use `hx-boost` on nav → `innerHTML` swap target `#view-main`) and `/ui/fragments/*` partial Routes alongside the existing `/api/v1/*` Route list — **one Starlette app, one read layer** (D-04).
4. Add a `Mount("/ui/static", StaticFiles(directory=str(_CONSOLE_DIR / "static")), name="static")` on the same `routes = [...]` list. Use `Mount`, not `Route`, because `StaticFiles` is its own ASGI app.
5. Attach `app.state.templates = templates` so `ui_handlers` can reach it via `request.app.state.templates` — same pattern as `app.state.console_read_api`.

**Do NOT change:** `/api/v1/*` routes, CORS middleware, the `build_console_app(read_api)` signature, or `app.state.console_read_api`. Phase 9 tests (`test_console_routes.py`, `test_console_stdio_cleanliness.py`) MUST still pass unchanged.

---

### `forge_bridge/console/ui_handlers.py` (NEW) — full-page route handlers

**Analog:** `forge_bridge/console/handlers.py` L105-171 (Phase 9 JSON handlers).

**Why split:** keeps JSON-envelope handlers (`/api/v1/*`) and HTML-template handlers (`/ui/*`) on separate modules so the `_envelope / _error` helpers stay owned by one file and the HTML error path can render a template instead of a JSON body. Planner may fold them into `handlers.py` if it reads cleaner — the important contract is that both modules read through `request.app.state.console_read_api`.

**Imports pattern** (from handlers.py L24-35):

```python
from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from starlette.requests import Request
from starlette.responses import HTMLResponse   # NEW — replaces JSONResponse

logger = logging.getLogger(__name__)
```

**Core handler pattern** — copy shape from `tools_handler` (handlers.py L105-111) and swap the envelope for a template render:

```python
async def ui_tools_handler(request: Request) -> HTMLResponse:
    try:
        tools = await request.app.state.console_read_api.get_tools()
    except Exception as exc:
        logger.warning("ui_tools_handler failed: %s", type(exc).__name__, exc_info=True)
        return request.app.state.templates.TemplateResponse(
            "errors/read_failed.html",
            {"request": request, "message": "Could not load tools"},
            status_code=500,
        )
    # Server-side pre-populate of query console input from URL params (D-26).
    return request.app.state.templates.TemplateResponse(
        "tools/list.html",
        {
            "request": request,
            "tools": [t.to_dict() for t in tools],  # Jinja gets plain dicts (D-04)
            "query_params": dict(request.query_params),
        },
    )
```

**Drilldown handler pattern** — shape from `tool_detail_handler` (handlers.py L114-123):

```python
async def ui_tool_detail_handler(request: Request) -> HTMLResponse:
    name = request.path_params["name"]
    tool = await request.app.state.console_read_api.get_tool(name)
    if tool is None:
        return request.app.state.templates.TemplateResponse(
            "errors/not_found.html",
            {"request": request, "what": f"tool {name!r}"},
            status_code=404,
        )
    return request.app.state.templates.TemplateResponse(
        "tools/detail.html",
        {"request": request, "tool": tool.to_dict()},
    )
```

**Filter/pagination parse** — REUSE `_parse_pagination` and `_parse_filters` from `handlers.py` L65-100. Import them:

```python
from forge_bridge.console.handlers import _parse_pagination, _parse_filters
```

These are private, but they're in the sibling module under the same package; calling them is cheaper and safer than duplicating the limit-clamp logic (D-05). Planner may promote them to a public `_query.py` module if both `handlers.py` and `ui_handlers.py` end up importing them — minor refactor, not required.

**Error handling pattern** — NEVER leak tracebacks (handlers.py L49-50 comment: *"NEVER leak tracebacks"*). Log `type(exc).__name__` + `exc_info=True`; render a neutral error template. Same posture as Phase 9.

**DO NOT** reinvent the `ConsoleReadAPI` read path. Every `ui_*_handler` calls one of: `get_tools()`, `get_tool(name)`, `get_executions(...)`, `get_manifest()`, `get_health()`. Phase 9 D-25.

---

### `forge_bridge/console/ui_fragments.py` (NEW) — fragment route handlers

**Analog:** `forge_bridge/console/ui_handlers.py` (role-match — same data path, smaller template).

**Pattern** — identical to `ui_handlers` but renders a partial (no `{% extends %}`). Example — the `/ui/fragments/health-strip` route (D-06, polled every 10 s):

```python
async def health_strip_fragment(request: Request) -> HTMLResponse:
    try:
        data = await request.app.state.console_read_api.get_health()
    except Exception as exc:
        logger.warning("health_strip_fragment failed: %s", type(exc).__name__, exc_info=True)
        data = {"status": "fail", "services": {}, "instance_identity": {}}
    return request.app.state.templates.TemplateResponse(
        "fragments/health_strip.html",
        {"request": request, "health": data},
    )
```

**htmx contract** — fragment templates return bare HTML (no `{% extends "shell.html" %}`). They match the `hx-target` / `hx-swap` pairs in UI-SPEC.md "Interaction Contracts" table. Poll cadence is declared in the Jinja template via `hx-trigger="every 10s"` (D-20) — NOT in the handler.

---

### `forge_bridge/console/templates/base.html` (NEW) — HTML doc skeleton

**Analog:** none in repo (first Jinja template). Use UI-SPEC.md §"CSS Architecture" + §"Asset Inventory" as the authoritative source.

**Pattern** — the `<head>` must:

1. Link the single stylesheet at `/ui/static/forge-console.css`.
2. Load both vendored JS files with **SRI** `integrity="sha384-..."` + `crossorigin="anonymous"` per D-31.
3. Set `<meta charset>` and a `viewport` meta for sane rendering on dev laptops (UI-SPEC focus is desktop; no responsive gate in v1.3).

**Structure** (extracted from CONTEXT.md D-02 + UI-SPEC.md):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Forge Console{% endblock %}</title>
  <link rel="stylesheet" href="/ui/static/forge-console.css">
  <script src="/ui/static/vendor/htmx-2.0.10.min.js"
          integrity="sha384-..." crossorigin="anonymous" defer></script>
  <script src="/ui/static/vendor/alpinejs-3.14.1.min.js"
          integrity="sha384-..." crossorigin="anonymous" defer></script>
</head>
<body>
  {% block body %}{% endblock %}
</body>
</html>
```

**Rules**:
- Two `<script>` tags, minified-only, version in filename (D-30/32).
- SRI hashes computed at vendor-drop time per D-34 README procedure.
- No inline JS blocks larger than ~4 LOC (Alpine component seed on shell.html is the one exception — the tab-visibility listener per D-22).
- Autoescape on. All `{{ value }}` interpolations pass through Jinja's HTML escaper. Tool names and consumer tags are already sanitized upstream (Phase 7 `_sanitize_tag`); Jinja autoescape is the second belt.

---

### `forge_bridge/console/templates/shell.html` (NEW) — app shell

**Analog:** `base.html` (self-extend — 3-level inheritance, D-02).

**Pattern**:

```jinja
{% extends "base.html" %}

{% block body %}
<div x-data="shellRoot()" x-init="init()">
  <nav class="top-nav" hx-boost="true" hx-push-url="true" hx-target="#view-main">
    <a href="/ui/tools"    class="nav-link">Tools</a>
    <a href="/ui/execs"    class="nav-link">Executions</a>
    <a href="/ui/manifest" class="nav-link">Manifest</a>
    <a href="/ui/health"   class="nav-link">Health</a>
    <a href="/ui/chat"     class="nav-link">Chat</a>
  </nav>

  <div id="health-strip"
       hx-get="/ui/fragments/health-strip"
       hx-trigger="load, every 10s[!document.hidden]"
       hx-swap="outerHTML">
    {% include "fragments/health_strip.html" %}
  </div>

  <main id="view-main">
    {% block view %}{% endblock %}
  </main>
</div>

<script>
  function shellRoot() {
    return {
      init() {
        // D-22: single tab-visibility listener, not per-view.
        document.addEventListener('visibilitychange', () => {
          if (!document.hidden) htmx.trigger('#health-strip', 'load');
        });
        // D-11: '/' focuses query console from anywhere.
        document.addEventListener('keydown', (e) => {
          if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
            const q = document.getElementById('query-console-input');
            if (q) { e.preventDefault(); q.focus(); }
          }
        });
      }
    }
  }
</script>
{% endblock %}
```

**Contract points**:
- `hx-boost="true"` + `hx-push-url="true"` on the nav (D-03). Back/forward/refresh work natively.
- `#view-main` is the single full-page htmx swap target (UI-SPEC Interaction Contracts table, rows 1-5).
- Health strip has its own `id` and its own poll — `outerHTML` swap so the fragment template owns the next poll declaration (D-06, D-20).
- `every 10s[!document.hidden]` is the htmx-native tab-visibility pause (D-22). Pair with the `visibilitychange` listener that fires an immediate refresh on un-hide.
- Alpine `x-data="shellRoot()"` scopes one root component to the whole shell. Per-view Alpine components (query-console parser, copy-to-clipboard) are nested inside their own `x-data` on the view templates — keeps state localized (CONTEXT.md Claude's Discretion §"Alpine component granularity").

---

### `forge_bridge/console/templates/tools/list.html` (NEW) — view template

**Analog:** `resources.tools_list` (resources.py L56-59) — returns the same `tools` list with `to_dict()` shape, just as JSON instead of HTML.

**Pattern**:

```jinja
{% extends "shell.html" %}
{% block title %}Registered Tools — Forge Console{% endblock %}

{% block view %}
<h1 class="view-title">Registered Tools</h1>

{% include "fragments/query_console.html" with context %}

<div class="table-toolbar">
  <button hx-get="/ui/fragments/tools-table{{ query_string }}"
          hx-target="#tools-table"
          hx-swap="outerHTML">Refresh tools</button>
  <span class="staleness" x-data="{ shown: 0 }" x-init="setInterval(() => shown++, 1000)"
        x-text="`Last refreshed ${shown}s ago`"></span>
</div>

<div id="tools-table">
  {% include "fragments/tools_table.html" %}
</div>
{% endblock %}
```

**Rules**:
- `{% extends "shell.html" %}` — three-level inheritance (D-02).
- Table lives in a fragment so the "Refresh tools" button can `hx-swap` just the table, not the entire view.
- `query_params` is passed in by the handler; templates render the query-console input pre-populated from URL state (D-26).
- Frozen dataclasses (ToolRecord) are converted to dict in the handler via `t.to_dict()` before template context (see `ui_handlers` example). This matches the resources.py pattern: `[t.to_dict() for t in tools]`.
- Code hash display: first 8 chars + `title="..."` tooltip for full hash (D-16, UI-SPEC §"Data table").

---

### `forge_bridge/console/templates/fragments/tools_table.html` (NEW) — fragment template

**Analog:** `ui_handlers.ui_tools_handler` (role-match, same data, just the table block).

**Pattern** (no `{% extends %}`, returns bare HTML):

```jinja
<table class="data-table">
  <thead>
    <tr>
      <th>Name</th><th>Origin</th><th>Namespace</th>
      <th>Code hash</th><th>Synthesized</th><th>Obs count</th>
    </tr>
  </thead>
  <tbody>
    {% for tool in tools %}
    <tr hx-get="/ui/tools/{{ tool.name }}"
        hx-target="#view-main"
        hx-push-url="true"
        class="row-link">
      <td>{{ tool.name }}</td>
      <td>{{ tool.origin }}</td>
      <td>{{ tool.namespace }}</td>
      <td class="mono" title="{{ tool.code_hash or '' }}">
        {{ (tool.code_hash or '')[:8] }}
      </td>
      <td>{{ tool.synthesized_at or '—' }}</td>
      <td>{{ tool.observation_count }}</td>
    </tr>
    {% else %}
    <tr><td colspan="6" class="empty-state">
      <strong>No tools registered</strong><br>
      Start the MCP server and connect a client to populate this list.
    </td></tr>
    {% endfor %}
  </tbody>
</table>
```

- Row click uses `hx-get` + `hx-push-url` (D-12). Direct URL navigation to `/ui/tools/{name}` still works cold (D-05).
- Empty state copy comes from UI-SPEC.md Copywriting Contract table.

---

### `forge_bridge/console/templates/tools/detail.html` (NEW) — drilldown template

**Analog:** `resources.tool_detail` (resources.py L61-71) for data shape; UI-SPEC.md §"Drilldown pages" for layout.

**Pattern** — D-14 locks the structure:

```jinja
{% extends "shell.html" %}
{% block title %}{{ tool.name }} — Tool — Forge Console{% endblock %}

{% block view %}
<h1 class="view-title">{{ tool.name }}</h1>

<section class="card provenance-card">
  <dl class="dl-two-col">
    <dt>origin</dt>            <dd class="amber">{{ tool.origin }}</dd>
    <dt>code_hash</dt>         <dd class="amber mono">{{ tool.code_hash or '—' }}</dd>
    <dt>synthesized_at</dt>    <dd class="amber mono">{{ tool.synthesized_at or '—' }}</dd>
    <dt>version</dt>           <dd class="amber">{{ tool.version or '—' }}</dd>
    <dt>observation_count</dt> <dd class="amber">{{ tool.observation_count }}</dd>
  </dl>
</section>

<section class="chip-row">
  {% for tag in tool.tags %}
  <span class="chip chip-readonly">{{ tag }}</span>
  {% endfor %}
</section>

{% if tool.origin == 'synthesized' and tool.raw_code %}
<section class="card code-card" x-data="{ copyLabel: 'Copy source' }">
  <button class="copy-btn"
          @click="navigator.clipboard.writeText($refs.src.textContent);
                  copyLabel = 'Copied!'; setTimeout(() => copyLabel = 'Copy source', 2000)"
          x-text="copyLabel"></button>
  <pre class="font-mono" x-ref="src">{{ tool.raw_code }}</pre>
</section>
{% endif %}

<details class="card sidecar-card">
  <summary>Show raw sidecar JSON (engineer mode)</summary>
  <pre class="font-mono">{{ tool | tojson(indent=2) }}</pre>
</details>
{% endblock %}
```

- Monospace for `code_hash` and `synthesized_at` values per UI-SPEC §"Drilldown pages / Provenance card".
- Full hash (never truncated) on drilldown (D-16).
- Consumer tags already sanitized by Phase 7 `_sanitize_tag`; autoescape handles anything that slipped.
- `<details>` default closed (UI-SPEC Copywriting Contract row "Drilldown: raw sidecar toggle").
- Alpine `x-data` scoped to the copy button only, ~4 LOC (D-14 budget).

---

### `forge_bridge/console/templates/fragments/health_strip.html` (NEW) — persistent strip

**Analog:** `resources.health` (resources.py L73-76); data shape pinned by Phase 9 D-14/15.

**Pattern**:

```jinja
<div id="health-strip"
     class="health-strip"
     hx-get="/ui/fragments/health-strip"
     hx-trigger="every 10s[!document.hidden]"
     hx-swap="outerHTML"
     x-data="{ expanded: false }">
  <button class="agg-pill status-{{ health.status }}" @click="expanded = !expanded">
    {% if health.status == 'ok' %}OK
    {% elif health.status == 'degraded' %}Degraded
    {% else %}Error{% endif %}
  </button>
  <span class="dot-row">
    {% for name, svc in [('mcp',   health.services.mcp),
                         ('flame', health.services.flame_bridge),
                         ('ws',    health.services.ws_server),
                         ('llm',   health.services.llm_backends),
                         ('watcher',  health.services.watcher),
                         ('storage',  health.services.storage_callback),
                         ('port',     health.services.console_port)] %}
    <span class="dot status-{{ svc.status if svc.status else 'fail' }}"
          title="{{ name }}: {{ svc.detail if svc.detail else '' }}"></span>
    {% endfor %}
  </span>
  <div class="expanded-panel" x-show="expanded" x-cloak>
    <!-- per-service detail panel; Alpine-local state (D-19) -->
    {% for name, svc in health.services.items() %}
    <div>{{ name }}: {{ svc }}</div>
    {% endfor %}
  </div>
</div>
```

- `outerHTML` swap — the fragment re-emits its own `hx-trigger` declaration on every poll (D-06).
- `[!document.hidden]` htmx-native tab-pause (D-22) — no JS side-channel needed here; just on the shell.html `visibilitychange` listener for immediate-on-unhide.
- Status classes (`status-ok`, `status-degraded`, `status-fail`) map to UI-SPEC color tokens (`--color-status-ok`, etc.).

---

### `forge_bridge/console/static/forge-console.css` (NEW)

**Analog:** none in repo. Sole authority is **UI-SPEC.md §"CSS Architecture"** — the `:root` custom-property block is copy-verbatim.

**Rules**:
- Single flat file, target ≤ 4 KB (D-32).
- No `@import`, no external URLs (UI-SPEC §"CSS Architecture").
- All color / font / spacing values come from CSS custom properties defined in the `:root` block.
- Amber (`--color-accent`) usage strictly limited to the six allowed roles in UI-SPEC §"Color" ("Accent is reserved for:" list).

No further pattern to copy from the codebase — this is the first stylesheet. Planner writes it against UI-SPEC.

---

### `forge_bridge/console/static/vendor/README.md` (NEW)

**Analog:** D-34 text block in CONTEXT.md (exact — 3-line procedure is the analog).

**Content** (copy verbatim from D-34, reformatted as markdown):

```markdown
# Vendored frontend assets

## Update procedure

1. Drop the new file with the bumped version in the filename:
   `htmx-<version>.min.js` or `alpinejs-<version>.min.js`.
2. Recompute the SRI hash:
   `openssl dgst -sha384 -binary < <file> | openssl base64 -A`
3. Bump the `<script>` `src` + `integrity` attributes in
   `forge_bridge/console/templates/base.html`.

No build step. No lockfile.
```

---

### `pyproject.toml` (MODIFIED)

**Analog:** itself (self-extend).

**Current state** (lines 10-18):

```toml
dependencies = [
    "httpx>=0.27",
    "websockets>=13.0",
    "mcp[cli]>=1.19,<2",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
]
```

**Current state** (lines 37-41):

```toml
[tool.hatch.build.targets.wheel]
packages = ["forge_bridge"]

[tool.hatch.build]
include = ["forge_bridge/**"]
```

**Phase 10 delta — two edits, no removals:**

1. Append `"jinja2>=3.1"` to the `dependencies` list. Only new pip dep in v1.3 (CONTEXT.md D-line, STATE.md v1.3 constraint).
2. Replace the `[tool.hatch.build.targets.wheel]` block with D-33's explicit-include form:

   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["forge_bridge"]
   include = [
       "forge_bridge/console/static/**/*",
       "forge_bridge/console/templates/**/*",
   ]
   ```

   The existing `[tool.hatch.build] include = ["forge_bridge/**"]` **stays** — it controls the sdist, not the wheel; the wheel target needs its own include directive to pick up non-`.py` files that hatch otherwise ignores by default (this is the exact pitfall D-33 closes).

**Verify after edit**:
- `pip install -e .` followed by an `import forge_bridge; from importlib.resources import files; files("forge_bridge.console.templates").iterdir()` round-trip must show the template files present. (Phase 10 VERIFY section owns the exact test; not planner's discretion.)

---

## Shared Patterns

### Read-path boundary (applies to EVERY new `/ui/*` and `/ui/fragments/*` handler)

**Source:** `forge_bridge/console/handlers.py` L106-107, L116-117, L143-146 — every handler does `request.app.state.console_read_api.get_<thing>(...)`.

**Apply to:** all new files under `forge_bridge/console/ui_handlers.py` and `forge_bridge/console/ui_fragments.py`.

**Pattern**:

```python
async def <ui_handler>(request: Request) -> HTMLResponse:
    try:
        data = await request.app.state.console_read_api.get_<x>(...)
    except Exception as exc:
        logger.warning("<handler> failed: %s", type(exc).__name__, exc_info=True)
        # render error template, 500
```

**DO NOT**:
- Read `ManifestService._tools` directly.
- Read `ExecutionLog._records` directly.
- Parse JSONL.
- Construct a second `ConsoleReadAPI` instance.

Phase 9 D-25 / API-04 / the instance-identity gate all enforce this. Breaking it breaks `/api/v1/health.instance_identity`.

### Logger-per-module pattern (applies to EVERY new .py file)

**Source:** `forge_bridge/console/handlers.py` L35 — `logger = logging.getLogger(__name__)`.

**Apply to:** `ui_handlers.py`, `ui_fragments.py`, any other new `.py` under `forge_bridge/console/`.

**Rule** (Phase 9 D-22 + pyproject.toml `[tool.ruff.lint] extend-select = ["T20"]`): **no `print()` calls, ever.** ruff `T20` is live for everything under `forge_bridge/console/`. Use `logger.debug` / `logger.info` / `logger.warning` only.

### Stdio-safety inheritance

**Source:** `forge_bridge/console/logging_config.py` `STDERR_ONLY_LOGGING_CONFIG` — wired into uvicorn in `forge_bridge/mcp/server.py::_start_console_task`.

**Apply to:** Phase 10 adds NO new log sinks, NO new uvicorn instances, NO new `print` call sites. The Phase 9 posture is inherited as-is. Planner must verify the `tests/test_console_stdio_cleanliness.py` suite still passes after Phase 10 ships — no change expected, but gate is live.

### URL-query-param round-trip (applies to EVERY list view)

**Source:** `forge_bridge/console/handlers.py` L65-100 (`_parse_pagination`, `_parse_filters`) — Phase 9 D-03 contract.

**Apply to:** `ui_tools_handler`, `ui_execs_handler`, `ui_manifest_handler`, and their matching fragment routes.

**Pattern**:
- Fragment and full-page routes both read the **same** query params as `/api/v1/*` (D-24): `?limit=`, `?offset=`, `?since=`, `?promoted_only=`, `?code_hash=`.
- The query console (D-07) parses the `key:value` grammar in Alpine, then calls `hx-get` with those plain params. Server does NOT know about the token grammar.
- Handler renders the query-console input pre-populated with a reconstructed token string built from `request.query_params` (D-26). Build as a Jinja macro (one place) so list-view templates don't each roll it.

### Autoescape on (applies to EVERY template)

**Source:** `Jinja2Templates(directory=...)` — autoescape on by default for `.html`.

**Apply to:** every template. Rely on it; don't `| safe` filter anything coming from `ToolRecord` / `ExecutionRecord` / health dicts unless it's literally pre-rendered HTML (which in Phase 10 it never is). Consumer tags are sanitized upstream by `forge_bridge/learning/sanitize.py::_sanitize_tag`; autoescape is the belt, sanitize is the suspenders.

### htmx-target discipline

**Source:** UI-SPEC.md §"Interaction Contracts — htmx swap targets" (the 8-row table).

**Apply to:** every template with an htmx attribute.

**Pattern**:
- Full-page swap → `hx-target="#view-main"`, `hx-swap="innerHTML"`, `hx-push-url="true"`.
- Health strip poll → `hx-target="#health-strip"`, `hx-swap="outerHTML"`, `hx-push-url="false"`.
- Health view poll → `hx-target="#health-view-content"`, `hx-swap="innerHTML"`, `hx-push-url="false"`.
- Pill expand / copy-to-clipboard / query-console token parse → Alpine local state, zero htmx.

**DO NOT** invent new swap targets. Eight patterns, taken from the UI-SPEC table. Every other interaction in v1.3 collapses into one of them.

---

## No Analog Found

These files introduce first-of-their-kind surfaces in this codebase. Planner must base them on the canonical references listed, not on existing code:

| File | Canonical reference |
|------|---------------------|
| `forge_bridge/console/templates/base.html` | UI-SPEC.md §"CSS Architecture" + §"Asset Inventory" + D-31 SRI rules |
| `forge_bridge/console/templates/shell.html` | CONTEXT.md D-02/D-03/D-06/D-22 + UI-SPEC.md §"Interaction Contracts" |
| `forge_bridge/console/static/forge-console.css` | UI-SPEC.md §"CSS Architecture" (verbatim `:root` block) + §"Color" (accent rules) + §"Spacing Scale" + §"Typography" |
| `forge_bridge/console/static/vendor/*.min.js` | D-32 size budgets (≤ 30 KB total); drop files verbatim from upstream release archives |

These four items are the whole "new-surface" budget for Phase 10. Everything else in the phase reuses shape from Phase 9 handlers.

---

## Key Patterns Identified

1. **One Starlette app, one read layer.** Phase 9 shipped `build_console_app(read_api)` + `ConsoleReadAPI` as a paired contract. Phase 10 adds routes, templates, and static mounts to that **same** factory — no second app, no second `ConsoleReadAPI`. The instance-identity gate (`/api/v1/health.instance_identity`) silently enforces this at runtime.
2. **Dataclass → `.to_dict()` → template.** `ToolRecord` / `ExecutionRecord` are frozen dataclasses with `to_dict()` methods (manifest_service.py L75-86). Handlers call `.to_dict()` before building the template context; templates render plain dicts. Same conversion Phase 9 already uses for JSON envelopes.
3. **`app.state.*` for cross-cutting dependencies.** Phase 9 pinned `app.state.console_read_api` (app.py L54); Phase 10 adds `app.state.templates`. No module-level globals; no request-level construction.
4. **Handlers never raise; always return.** Phase 9 pattern (handlers.py L105-111) — every handler wraps its body in `try/except Exception`, logs `type(exc).__name__`, returns an error envelope. Never leaks a traceback. Phase 10 handlers render an error template instead of a JSON body; same posture.
5. **Three-level template inheritance** (D-02): `base.html` → `shell.html` → per-view. Every full-page response goes through `shell.html`. Fragment templates sidestep inheritance entirely (bare HTML, no `{% extends %}`).
6. **htmx declarations live in templates, not handlers.** `hx-target`, `hx-swap`, `hx-trigger`, `hx-push-url` are HTML attributes authored by Jinja templates. Handlers return HTML; they do not set htmx-specific headers (no `HX-Push-Url` response-header hacks in v1.3).
7. **Alpine is small-and-local.** ~40 LOC total across the whole UI — query-console parser, copy-to-clipboard, strip expand, shell-level tab-visibility + `/` focus. No Alpine store, no Alpine.data() registry, no component framework. Nested `x-data="{...}"` blocks scoped to their region.
8. **Vendored assets + SRI + explicit wheel include.** D-30/D-31/D-33 are one coherent pitfall-closer: filename contains version, `<script>` carries SRI, `pyproject.toml` wheel target explicitly includes `templates/**/*` and `static/**/*`. Planner MUST land all three together — partial landing reproduces the "looks done but isn't" wheel-pack pitfall called out in research.

---

## Metadata

- **Analog search scope:** `forge_bridge/console/*.py`, `forge_bridge/mcp/server.py`, `forge_bridge/learning/execution_log.py`, `tests/test_console_*`
- **Files scanned:** 12
- **Pattern extraction date:** 2026-04-23
- **CONTEXT.md decisions mapped:** D-01..D-36 (all)
- **UI-SPEC.md sections mapped:** Design System, Spacing Scale, Typography, Color, Component Inventory, Interaction Contracts, Copywriting Contract, CSS Architecture, Asset Inventory
