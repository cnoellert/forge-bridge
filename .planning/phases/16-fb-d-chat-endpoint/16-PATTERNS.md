# Phase 16 (FB-D): Chat Endpoint — Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 8 new/modified
**Analogs found:** 7 / 8 (rate-limit module is greenfield — no analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `forge_bridge/console/handlers.py` (extend) | controller | request-response (POST + LLM loop) | `staged_approve_handler` lines 179-224 | exact |
| `forge_bridge/console/_rate_limit.py` (NEW) | utility / middleware | request-response gate | none — see "No Analog Found" | n/a |
| `forge_bridge/console/app.py` (extend) | config / route table | request-response | lines 96-98 (FB-B route block) | exact |
| `forge_bridge/console/templates/chat/panel.html` (NEW, replaces stub) | view (HTML) | request-response | `health/detail.html` (8-line shell + JS-driven content) | role-match |
| `forge_bridge/console/static/forge-chat.js` (NEW) | view (JS) | event-driven (fetch + DOM update) | `templates/fragments/query_console.html` lines 39-117 (vanilla Alpine factory) | partial |
| `forge_bridge/console/static/forge-console.css` (extend) | view (CSS) | n/a | lines 38-69 (card + chip + amber tokens) | exact |
| `tests/console/test_chat_handler.py` (NEW) | test | unit (in-process TestClient) | `tests/console/test_staged_handlers_writes.py` | exact |
| `tests/integration/test_chat_endpoint.py` (NEW) | test | integration (live LLM) | `tests/integration/test_complete_with_tools_live.py` | exact |

---

## Pattern Assignments

### `forge_bridge/console/handlers.py` — add `chat_handler`

**Analog:** `staged_approve_handler` at `forge_bridge/console/handlers.py:179-224`

**Imports to add (mirror lines 31-43):**
```python
import asyncio                                     # for asyncio.wait_for (D-14)
import uuid                                        # already imported
from forge_bridge.console._rate_limit import check_rate_limit
from forge_bridge.llm.router import (
    LLMLoopBudgetExceeded, LLMToolError, RecursiveToolLoopError,
)
```

**Envelope helpers — REUSE verbatim** (already in file):
- `_envelope(data, **meta)` lines 53-55 → success path (D-03 response shape goes in `data`)
- `_error(code, message, status)` lines 58-60 → use for 422/429/500/504. **MUST EXTEND** to also accept `request_id` so the D-17 envelope `{"error": "...", "message": "...", "request_id": "..."}` round-trips. Recommended: add `_chat_error(code, message, status, request_id)` helper next to `_error` rather than mutating `_error` (FB-B contract is locked by `tests/console/test_staged_zero_divergence.py`).
- `_envelope_json` line 63-70 → not needed for chat (no MCP-resource mirror in FB-D).

**Body validation pattern — mirror `_resolve_actor` at lines 118-142:**
```python
# Read JSON body once; on parse failure return 422 (NOT swallow like _resolve_actor does).
# D-02 messages list shape: list of {role, content, tool_call_id?}.
try:
    body = await request.json()
except Exception:
    return _chat_error("validation_error", "request body is not valid JSON", 422, request_id)
if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
    return _chat_error("validation_error", "messages: list[dict] is required", 422, request_id)
```
**Different from `_resolve_actor`:** chat MUST 422 on bad JSON (validation contract D-09 line 106), where `_resolve_actor` silently falls back to `http:anonymous`. Do NOT copy the silent-swallow.

**Core handler skeleton — mirror lines 179-224:**
```python
async def chat_handler(request: Request) -> JSONResponse:
    """POST /api/v1/chat — see Phase 16 D-01..D-21.

    Provider-shape `messages` body, non-streaming response, hardcoded
    sensitive=True (D-05), 125s outer wait_for around FB-C's 120s
    inner cap (D-14), rate-limited per `request.client.host` (D-13).
    """
    request_id = str(uuid.uuid4())                           # D-17/D-21
    client_ip = request.client.host if request.client else "unknown"

    # CHAT-01 rate limit BEFORE any LLM work
    rl = check_rate_limit(client_ip)
    if not rl.allowed:
        return JSONResponse(
            {"error": "rate_limit_exceeded",
             "message": f"Rate limit reached — wait {rl.retry_after}s before retrying.",
             "request_id": request_id},
            status_code=429,
            headers={"Retry-After": str(rl.retry_after)},
        )

    # body validation -> 422 (see block above)
    # ... (validation_error / unsupported_role)

    # CHAT-02 two-layer timeout: outer 125s wraps FB-C's inner 120s
    started = time.monotonic()
    router = request.app.state.console_read_api._llm_router  # D-16 reuse
    if router is None:
        return _chat_error("internal_error",
                           "LLM router not configured", 500, request_id)

    # D-04 snapshot all registered tools at request time
    from forge_bridge.mcp import server as _mcp_server
    tools = await _mcp_server.mcp.list_tools()

    try:
        result_text = await asyncio.wait_for(
            router.complete_with_tools(
                prompt=_extract_user_prompt(messages),  # see D-02 note below
                tools=tools,
                sensitive=True,                          # D-05 hardcoded
                max_iterations=body.get("max_iterations", 8),
                max_seconds=120.0,                       # D-14 inner
                tool_result_max_bytes=body.get("tool_result_max_bytes"),
            ),
            timeout=125.0,                               # D-14 outer
        )
    except asyncio.TimeoutError:
        return _chat_error("request_timeout",
                           "Response timed out — try a simpler question or fewer tools.",
                           504, request_id)
    except LLMLoopBudgetExceeded:
        return _chat_error("request_timeout",
                           "Response timed out — try a simpler question or fewer tools.",
                           504, request_id)
    except RecursiveToolLoopError:
        return _chat_error("internal_error",
                           "Chat error — check console for details.",
                           500, request_id)
    except LLMToolError:
        return _chat_error("internal_error",
                           "Chat error — check console for details.",
                           500, request_id)
    except Exception as exc:
        logger.warning("chat_handler failed: %s", type(exc).__name__, exc_info=True)
        return _chat_error("internal_error",
                           "Chat error — check console for details.",
                           500, request_id)

    # D-21 structured log (one entry per call)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "chat request_id=%s client_ip=%s message_count_in=%d "
        "tool_call_count=%d wall_clock_ms=%d stop_reason=end_turn",
        request_id, client_ip, len(messages),
        # tool_call_count derived from how many tool messages the loop appended
        sum(1 for m in messages if m.get("role") == "tool"),
        elapsed_ms,
    )

    # D-03 response shape
    return JSONResponse({
        "messages": messages + [{"role": "assistant", "content": result_text}],
        "stop_reason": "end_turn",
        "request_id": request_id,
    })
```

**Error-handling pattern — mirror lines 222-224 + Phase 8 LRN at line 117 (preserved at 234):**
- Always `logger.warning(... type(exc).__name__, exc_info=True)` — NEVER `str(exc)` (credentials hygiene).
- Catch in this exact order: `asyncio.TimeoutError` → `LLMLoopBudgetExceeded` → `RecursiveToolLoopError` → `LLMToolError` → bare `Exception`. Specific-before-general.

**MUST be different from analog:**
1. **No `session_factory` access** — chat doesn't write to staged_operations directly; the LLM may *propose* through tools (which themselves write), but the handler is read-only on the DB.
2. **Two-layer timeout** (D-14) — staged handlers have no wall-clock cap; chat needs `asyncio.wait_for` wrapping the LLM call.
3. **`request_id` is per-request not per-op** — generate `uuid.uuid4()` at handler entry, surface in BOTH success and error envelopes.
4. **D-15 sanitization is already inside `complete_with_tools()`** — handler does NOT re-sanitize. Verification test asserts the LLM-bound prompt does NOT contain poisoned marker substrings (mirror `tests/integration/test_complete_with_tools_live.py` sentinel-assertion pattern at lines 79, 145-152).

**Ambiguous — planner call:**
- D-02 says request body is `messages: [...]` shape; FB-C's `complete_with_tools()` takes `prompt: str` (not a messages list). The handler must either (a) extract the latest user turn as `prompt` and discard prior history (lossy), or (b) FB-C must grow a `messages=` kwarg overload. **Recommendation:** option (a) for v1.4 — D-06 says state lives client-side (`per-tab in-browser`), so server-side history reconstruction is out of scope. The handler joins prior `user`/`assistant`/`tool` messages into a single prompt string with role markers, OR ships an FB-C overload. **Planner must decide.** If (b), it adds a Wave 0 plan to FB-C's contract.

---

### `forge_bridge/console/_rate_limit.py` (NEW)

**No close analog.** No existing in-process throttler / cache exists. The closest dictionary-keyed-with-TTL pattern in the repo is `_canonical_execution_log_id` / `_canonical_manifest_service_id` at `forge_bridge/console/read_api.py:44-45` (module-level state, no eviction). That's not a token bucket, just identity tracking.

**What to copy from analog (sparse):**
- Module-level state pattern from `read_api.py:44-45`: store the bucket dict at module scope; expose `check_rate_limit(client_ip) -> RateLimitDecision` (a small frozen dataclass) as the only public function.
- Logger setup pattern from `handlers.py:45`: `logger = logging.getLogger(__name__)` + `logger.warning(... type(exc).__name__, exc_info=True)` style.

**Greenfield design (D-13):**
```python
# forge_bridge/console/_rate_limit.py
import time
import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_CAPACITY = 10                # D-13: 10 tokens
_REFILL_SECONDS = 60.0        # D-13: 60s window (10/min steady-state)
_TTL_SECONDS = 300.0          # D-13: evict if no activity 5min
_REFILL_RATE = _CAPACITY / _REFILL_SECONDS

_buckets: dict[str, tuple[float, float]] = {}   # ip -> (tokens, last_refill_monotonic)
_lock = threading.Lock()                         # Starlette TestClient is sync; real ASGI is async — lock cheap

@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int

def check_rate_limit(client_ip: str) -> RateLimitDecision:
    now = time.monotonic()
    with _lock:
        # Lazy TTL sweep on every call (D-13 — bounded memory)
        stale = [ip for ip, (_, last) in _buckets.items() if now - last > _TTL_SECONDS]
        for ip in stale:
            _buckets.pop(ip, None)

        tokens, last = _buckets.get(client_ip, (_CAPACITY, now))
        # Refill since last touch
        tokens = min(_CAPACITY, tokens + (now - last) * _REFILL_RATE)
        if tokens >= 1.0:
            _buckets[client_ip] = (tokens - 1.0, now)
            return RateLimitDecision(allowed=True, retry_after=0)
        # Blocked: how long until 1 token available?
        retry_after = max(1, int((1.0 - tokens) / _REFILL_RATE))
        _buckets[client_ip] = (tokens, now)
        return RateLimitDecision(allowed=False, retry_after=retry_after)

def _reset_for_tests() -> None:                 # test affordance, _-prefixed
    with _lock:
        _buckets.clear()
```

**Test-only reset:** Tests call `_reset_for_tests()` between cases; expose explicitly with `_` prefix (no public reset surface).

**Ambiguous — planner call:**
- Async-vs-sync lock: Starlette runs handlers in the event loop; using `threading.Lock` blocks briefly but the critical section is microseconds. `asyncio.Lock` would be more idiomatic but couples the module to event-loop ownership. **Recommendation:** `threading.Lock` (OK for v1.4 single process per D-13 rationale "single-process is fine"), document tradeoff in the module docstring. Migrating to `asyncio.Lock` is one-line if it ever matters.

---

### `forge_bridge/console/app.py` — add chat routes

**Analog:** `forge_bridge/console/app.py:96-98` (FB-B route block, the most recent additions).

**Pattern to mirror — additive, exact:**
```python
# In imports section near line 15-24:
from forge_bridge.console.handlers import (
    chat_handler,                  # NEW (Phase 16)
    execs_handler,
    # ... existing imports unchanged
)
from forge_bridge.console.ui_handlers import (
    ui_chat_handler,               # RENAMED from ui_chat_stub_handler (D-20)
    # ... existing imports
)

# In `routes` list — add NEXT TO the FB-B block at lines 96-98:
# Phase 16 (FB-D) — chat endpoint
Route("/api/v1/chat", chat_handler, methods=["POST"]),

# Replace the existing line 86 entry:
Route("/ui/chat", ui_chat_handler, methods=["GET"]),  # was ui_chat_stub_handler
```

**Different from analog:** the `/ui/chat` route already exists (line 86) — DO NOT add a second one. Just swap the handler name when the stub becomes a panel (D-20).

**CORS pattern — already correct** (lines 100-107). `allow_methods=["GET", "POST"]` already in place from FB-B; no change. Wildcard `allow_headers=["*"]` already permits `X-Request-Id` etc.

**Ambiguous — planner call:** The renamed handler (`ui_chat_stub_handler` → `ui_chat_handler` per D-20) appears in `forge_bridge/console/ui_handlers.py:467-476`. Planner decides: rename in place vs. add new function and delete old. **Recommendation:** rename in place — git blame stays sane and the chat-nav stub regression test `tests/test_ui_chat_stub.py` will need to be renamed-and-rewritten anyway.

---

### `forge_bridge/console/templates/chat/panel.html` (NEW, replaces `stub.html`)

**Analog:** `forge_bridge/console/templates/health/detail.html` (8 lines — minimal shell that defers content to a fragment + JS).

**Pattern to mirror (verbatim shell):**
```html
{% extends "shell.html" %}
{% block title %}LLM Chat — Forge Console{% endblock %}

{% block view %}
<h1 class="view-title">LLM Chat</h1>

<div id="chat-panel"
     x-data="chatPanel()"
     x-init="init()">
  <!-- transcript stream -->
  <div id="chat-transcript" class="card chat-transcript" role="log" aria-live="polite" aria-atomic="false">
    <template x-for="msg in messages" :key="msg.id">
      <!-- message rendering — see forge-chat.js for shape -->
    </template>
  </div>

  <!-- error banner (D-09) -->
  <div class="error-card" x-show="error" x-text="error" x-cloak></div>

  <!-- input (D-10 single textarea, Enter sends, Shift+Enter newline) -->
  <form @submit.prevent="send()">
    <textarea id="chat-input"
              x-model="draft"
              x-ref="input"
              @keydown.enter.prevent="onEnter($event)"
              placeholder="Ask about pipeline state, tools, executions…"
              rows="2"
              :disabled="inflight"></textarea>
    <button class="btn" type="submit" :disabled="inflight || !draft.trim()">
      <span x-show="!inflight">Send</span>
      <span x-show="inflight" class="spinner-amber"></span>
    </button>
  </form>
</div>

<script src="/ui/static/forge-chat.js" defer></script>
{% endblock %}
```

**Why this analog (and not `execs/list.html`):** execs templates couple to htmx fragment-swap; chat is an XHR `fetch()` + JSON contract (D-02/D-03), not a server-rendered HTML fragment. `health/detail.html` is the cleanest example of a "thin Jinja shell + client-side dynamic content" page in the repo.

**LOGIK-PROJEKT amber palette tokens — REUSE these CSS classes from `static/forge-console.css`:**
| Token | Value | Where to apply on chat panel |
|---|---|---|
| `--color-bg` (#242424) line 1 | page bg | already inherited via `body` |
| `--color-surface` (#2a2a2a) line 1 | card/message bubble bg | `.chat-message`, `.chat-tool-trace` |
| `--color-accent` (#cc9c00) line 1 | spinner, send-button hover, message author | `.amber` class (line 43) reusable |
| `--color-status-error` (#660000) line 1 | error banner | `.error-card` (line 38) — ALREADY EXISTS, reuse for D-09 banners |
| `--color-status-warn` (#664e00) line 1 | retry-after countdown | `.dot.status-warn` (line 54) reusable for the rate-limit banner |
| `--space-md`, `--space-lg`, `--space-xl` | 16/24/32px | message spacing |
| `--font-mono` (Consolas/Monaco) line 1 | tool-trace JSON arg/result blocks | `.mono` class (line 34) reusable |

**Tool-call expandable trace (D-07) — mirror the `execs/detail.html` `<details>` pattern at lines 36-44:**
```html
<details class="card sidecar-card chat-tool-trace" x-data="{ copyLabel: 'Copy result' }">
  <summary><strong x-text="msg.tool_name"></strong>(<span class="mono" x-text="msg.args_preview"></span>)</summary>
  <pre class="font-mono" x-ref="result" x-text="msg.result"></pre>
</details>
```
Default-collapsed `<details>`, copy-button affordance, monospace pre — all already styled by lines 36-44 of forge-console.css. NO new CSS needed for the trace shell; only new classes for the chat-message bubble layout.

**Different from analog:**
- `health/detail.html` uses htmx polling (line 8-11). Chat panel does NOT poll — it's request-driven via `<form @submit>`.
- Need new CSS classes for chat-specific layout (`.chat-transcript`, `.chat-message`, `.chat-message--user`, `.chat-message--assistant`, `.spinner-amber`). All MUST use existing `var(--color-*)` tokens — no new color values.

**Ambiguous — planner call:**
- D-08 says "reuse existing spinner from forge-console.css" but **NO spinner CSS exists** in this file (verified via grep). Planner must either: (a) add a 10-line `@keyframes spin` + `.spinner-amber` rule using `--color-accent`, or (b) use a static text indicator like "…" instead. **Recommendation:** (a). One @keyframes + one class is the right amber-palette move; non-developer artist UAT (D-12) needs visual feedback, "…" reads as unresponsive.

---

### `forge_bridge/console/static/forge-chat.js` (NEW)

**Analog:** `forge_bridge/console/templates/fragments/query_console.html:39-117` — vanilla Alpine factory function inline in a `<script>` tag.

**Pattern to copy — Alpine factory shape:**
```javascript
// forge-chat.js — Phase 16 (FB-D) chat panel client.
// D-02/D-03: messages list both ways. D-06: per-tab state.
// Mirrors the queryConsole() factory pattern at templates/fragments/query_console.html:40-117.
function chatPanel() {
  return {
    messages: [],          // [{id, role, content, tool_name?, args_preview?, result?}]
    draft: '',
    inflight: false,
    error: '',
    init() {
      // D-06 per-tab: messages cleared on tab close (no localStorage).
    },
    onEnter(ev) {          // D-10: Enter sends, Shift+Enter newline
      if (ev.shiftKey) {
        const t = ev.target;
        const start = t.selectionStart;
        this.draft = this.draft.slice(0, start) + '\n' + this.draft.slice(t.selectionEnd);
        return;
      }
      this.send();
    },
    async send() {
      if (!this.draft.trim() || this.inflight) return;
      const userMsg = { id: crypto.randomUUID(), role: 'user', content: this.draft };
      this.messages.push(userMsg);
      this.draft = '';
      this.inflight = true;
      this.error = '';
      try {
        const r = await fetch('/api/v1/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: this.messages.map(m => ({
            role: m.role, content: m.content,
          }))}),
        });
        const body = await r.json();
        if (r.status === 429) {
          this.error = body.message || 'Rate limit reached.';
        } else if (r.status === 504) {
          this.error = 'Response timed out — try a simpler question or fewer tools.';
        } else if (r.status === 422) {
          this.error = 'Invalid request — ' + (body.message || '');
        } else if (!r.ok) {
          this.error = 'Chat error — check console for details.';
        } else {
          // D-03 echoes full message list — replace local state.
          this.messages = body.messages.map((m, i) => ({ id: i + '-' + crypto.randomUUID(), ...m }));
        }
      } catch (e) {
        this.error = 'Chat error — check console for details.';
      } finally {
        this.inflight = false;
      }
    },
  };
}
```

**Why this analog:** the queryConsole factory is the only existing example of an Alpine.js component that does fetch + state + DOM updates without htmx. Both share the `x-data="factoryName()" x-init="init()"` boot pattern, both keep state in plain object fields, both use `@keydown` for keyboard handling. The chat panel is just queryConsole with a transcript instead of a URL push.

**Different from analog:**
- queryConsole submits via `htmx.ajax(...)` (line 97-100) — chat must use `fetch()` because we need JSON request body and JSON response parsing.
- queryConsole is inline in the template; chat-js is a separate static file (size — ~80 lines is the threshold; query_console is 80 lines inline; chat will likely be 120+ with the message rendering + retry-after countdown).

**Ambiguous — planner call:**
- File location: `static/forge-chat.js` vs inline in `panel.html`. **Recommendation:** separate file. The minified Alpine + htmx vendor files at `static/vendor/` set the precedent that page-specific JS lives in `static/`. Inline scripts work but bypass browser caching across navigations.

---

### `forge_bridge/console/static/forge-console.css` — extend

**Analog:** lines 38-69 of the same file (cards, chips, sidecar-card, code-card patterns).

**Pattern to copy — additive single-line rules using existing tokens:**
```css
/* === Phase 16 (FB-D) chat panel === */
.chat-transcript{display:flex;flex-direction:column;gap:var(--space-md);max-height:60vh;overflow-y:auto;padding:var(--space-md)}
.chat-message{padding:var(--space-md);border-radius:4px;background:var(--color-surface)}
.chat-message--user{border-left:2px solid var(--color-text-muted)}
.chat-message--assistant{border-left:2px solid var(--color-accent)}      /* amber */
.chat-message--tool{font-size:var(--text-label);color:var(--color-text-muted);font-family:var(--font-mono)}
.chat-tool-trace{margin-top:var(--space-sm)}                              /* uses sidecar-card base */
.spinner-amber{display:inline-block;width:12px;height:12px;border:2px solid var(--color-accent-muted);border-top-color:var(--color-accent);border-radius:50%;animation:spin 0.7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#chat-input{width:100%;font-family:var(--font-mono);background:#3a3f4f;border:1px solid var(--color-border-md);padding:var(--space-sm) var(--space-md);min-height:32px;color:var(--color-text);resize:vertical}
#chat-input:focus{outline:none;border-color:var(--color-accent)}
```

**Different from analog:** zero. Every value uses an existing `--*` token (per project memory: "artist-first, LOGIK-PROJEKT dark+amber palette"). No new colors. The single new technical introduction is `@keyframes spin` (CSS does not ship one yet).

---

### `tests/console/test_chat_handler.py` (NEW)

**Analog:** `tests/console/test_staged_handlers_writes.py` lines 1-204.

**Imports to mirror (lines 9-17):**
```python
from __future__ import annotations
import uuid
import pytest
import pytest_asyncio
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
```

**Fixture pattern — mirror `tests/console/conftest.py:24-39` (`staged_client`):** rebuild a `TestClient` over `build_console_app(...)` with a mocked `LLMRouter` whose `complete_with_tools` is an `AsyncMock`. Mock `forge_bridge.mcp.server.mcp.list_tools` to return a fixed list. Rate-limit module: call `_reset_for_tests()` in an autouse fixture.

```python
@pytest_asyncio.fixture
async def chat_client():
    """TestClient with mocked LLMRouter (no real Ollama dependency)."""
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.read_api import ConsoleReadAPI
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console import _rate_limit
    _rate_limit._reset_for_tests()

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="OK from mock LLM")

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,                # D-16 reuse
    )
    app = build_console_app(api)
    return TestClient(app)
```

**Test case roster — mirror lines 22-203 cell-by-cell:**

| Concern | Staged analog (line) | Chat test |
|---|---|---|
| Happy path 200 with envelope | `test_approve_proposed_returns_200` (98) | `test_chat_happy_path_returns_200` |
| 422 invalid JSON | n/a (FB-B has no body required) | `test_chat_invalid_json_body_returns_422` |
| 422 missing messages | n/a | `test_chat_missing_messages_field_returns_422` |
| 422 unsupported role | n/a | `test_chat_unsupported_role_returns_422` |
| 429 rate limit | n/a | `test_chat_rate_limit_returns_429_with_retry_after` (loop 11x) |
| 504 timeout | n/a | `test_chat_timeout_returns_504` (mock raises `LLMLoopBudgetExceeded`) |
| 500 internal error | n/a | `test_chat_recursive_loop_error_returns_500` |
| 500 LLMToolError | n/a | `test_chat_tool_error_returns_500` |
| Error envelope shape | `test_re_approve_returns_409_with_current_status` (108) | `test_chat_error_envelope_includes_request_id` |
| `request_id` in success too | n/a | `test_chat_success_includes_request_id` |
| Sanitization | n/a | see integration test (mock can't poison FB-C internals) |

**Pattern from `test_re_approve_returns_409_with_current_status` (lines 108-119) for error envelope shape assertions:**
```python
async def test_chat_rate_limit_returns_429_with_retry_after(chat_client):
    # 11th request fires the rate limit per D-13 (capacity=10)
    for _ in range(10):
        chat_client.post("/api/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    r = chat_client.post("/api/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "rate_limit_exceeded"
    assert "Retry-After" in r.headers
    assert "request_id" in body
```

**Different from analog:**
- Mock `complete_with_tools` rather than seeding a real DB row. Rate-limit and timeout tests need to mock `asyncio.wait_for` raising `TimeoutError` for the 504 path.
- No `session_factory` fixture needed — chat doesn't write.
- Need `patch('forge_bridge.mcp.server.mcp.list_tools', AsyncMock(return_value=[...]))` to stub the tool list snapshot (D-04).

---

### `tests/integration/test_chat_endpoint.py` (NEW, CHAT-04/05)

**Analog:** `tests/integration/test_complete_with_tools_live.py` lines 1-220.

**Env-gating pattern — REUSE verbatim from lines 49-66:**
```python
import os, pytest

requires_integration = pytest.mark.skipif(
    os.environ.get("FB_INTEGRATION_TESTS") != "1",
    reason="live LLM integration tests require FB_INTEGRATION_TESTS=1",
)
```
Both gates from FB-C (`requires_integration`, `requires_anthropic`) — chat only needs `requires_integration` because D-05 hardcodes `sensitive=True` (Ollama-only, no `ANTHROPIC_API_KEY` requirement).

**Sentinel test pattern — mirror lines 79, 100-104, 145-152:**
```python
_SENTINEL_RESULT = "FORGE-CHAT-SENTINEL-CHAT04Q"

# CHAT-04: artist UAT prompt
@requires_integration
@pytest.mark.asyncio
async def test_chat_endpoint_under_60s_via_uvicorn():
    """ROADMAP CHAT-04 / D-12 fresh-operator gate."""
    # Spin up a real uvicorn worker (or use httpx.AsyncClient over TestClient)
    # POST /api/v1/chat with messages=[{"role":"user","content":"what synthesis tools were created this week?"}]
    # Assert: response.elapsed_s < 60.0, response.json().messages[-1].role == "assistant"
```

**Sanitization verification (D-15 / CHAT-03):**
```python
@requires_integration
@pytest.mark.asyncio
async def test_chat_does_not_leak_poisoned_tool_marker():
    """D-15 verification: poison a tool sidecar with IGNORE PREVIOUS INSTRUCTIONS;
    assert that string does NOT appear in the LLM-bound prompt after the loop runs."""
    # Mirror lines 79-104 pattern: in-test tool that returns the poison string;
    # assert sentinel sanitization stripped it before the LLM saw it.
```

**Parity test (CHAT-05 / D-18) — pattern is unique to this phase:**
- Two clients hit the same endpoint: a `requests.Session` (browser-like fetch) and an `httpx.Client` configured to spoof projekt-forge's flame-hooks request shape.
- Compare structural shape of responses: assert keys + types + role progression, NOT content equality (LLM output is non-deterministic).
- This is greenfield — no existing parity test to mirror. Document the contract in the test docstring.

**Different from analog:**
- `test_complete_with_tools_live.py` calls `LLMRouter.complete_with_tools()` directly. Chat tests must call through HTTP (`uvicorn` subprocess or `httpx.AsyncClient(transport=ASGITransport(app=app))`). **Recommendation:** `httpx.AsyncClient` with `ASGITransport` — no subprocess overhead, full ASGI fidelity, runs in pytest event loop.

---

## Shared Patterns

### Logger setup
**Source:** `forge_bridge/console/handlers.py:45`
**Apply to:** `chat_handler`, `_rate_limit.py`
```python
logger = logging.getLogger(__name__)
logger.warning("operation failed: %s", type(exc).__name__, exc_info=True)  # NEVER str(exc)
```
Phase 8 LRN — credentials hygiene. Locked across FB-A/B/C.

### Error envelope (Phase 9 + FB-B)
**Source:** `forge_bridge/console/handlers.py:53-60`
**Apply to:** all chat handler exit paths
- 2xx: `{"data": ..., "meta": ...}` for staged/execs/tools, but **chat extends to a flat `{messages, stop_reason, request_id}` per D-03** (no `data`/`meta` wrap).
- 4xx/5xx: `{"error": "<code>", "message": "<human>", "request_id": "<uuid>"}` per D-17 — note this is **flatter than FB-B's `{"error": {"code", "message"}}`** (D-17 shape is `error: <string>` not `error: <object>`). Planner: confirm with user that D-17's flat shape is intentional and not a transcription error vs. FB-B's nested shape — **this is divergence from `tests/console/test_staged_zero_divergence.py`**.

### LLMRouter access (D-16)
**Source:** `forge_bridge/console/read_api.py:84-102` (constructor) and `forge_bridge/console/handlers.py` (where staged handlers reach `request.app.state.console_read_api`).
**Apply to:** `chat_handler` only
```python
router = request.app.state.console_read_api._llm_router
```
Underscore-prefixed attribute; treat as a stable internal contract per Phase 9 D-25 (single facade owns the router; no second instance).

### Tool snapshot (D-04)
**Source:** `forge_bridge/mcp/registry.py:230-238` (`invoke_tool` calls `mcp.list_tools()`).
**Apply to:** `chat_handler` (snapshot tools at request time)
```python
import forge_bridge.mcp.server as _mcp_server
tools = await _mcp_server.mcp.list_tools()
```
Reuses the same `_mcp_server.mcp` singleton FB-C's `invoke_tool` reaches; no second registry, no curated subset.

---

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `forge_bridge/console/_rate_limit.py` | utility — token bucket | First in-process throttler in the repo. Greenfield design above; planner copies the proposed module verbatim. Recommend writing a 100% unit-test target (no integration coupling). |

---

## Cross-cutting concerns the planner must resolve

1. **D-02 prompt-vs-messages mismatch (HIGH):** FB-C's `complete_with_tools(prompt: str, ...)` does not take a `messages` list. Either FB-C grows a `messages=` overload (Wave 0 plan against Phase 15 deliverables) OR `chat_handler` flattens the messages list into a single prompt string (lossy). **Recommendation:** flatten in v1.4, plant `SEED-CHAT-MESSAGES-NATIVE-V1.5` for the FB-C overload.
2. **D-17 envelope flat-vs-nested (MEDIUM):** D-17 in 16-CONTEXT shows `{"error": "<code>", "message": "<human>"}` (flat); FB-B's locked shape is `{"error": {"code": "...", "message": "..."}}` (nested). **Test `tests/console/test_staged_zero_divergence.py` will break if we ship the flat shape.** Planner must either: confirm D-17 is divergent-by-design and update the zero-divergence test scope, OR reinterpret D-17 as the nested shape with a typo. **Recommendation:** ask user — this is a contract bug or a deliberate v1.4 decision; either way it needs explicit acknowledgment before plans are written.
3. **Spinner CSS does not exist (LOW):** D-08 says "reuse existing spinner from forge-console.css" — there isn't one. Add 10-line `@keyframes spin` + `.spinner-amber` rule per the CSS pattern table above.
4. **Rate-limit lock primitive (LOW):** `threading.Lock` vs `asyncio.Lock`. Single-process v1.4 makes either fine; threading is simpler and migrates trivially if needed.

---

## Metadata

**Analog search scope:** `forge_bridge/console/`, `forge_bridge/llm/`, `forge_bridge/mcp/`, `tests/console/`, `tests/integration/`
**Files scanned:** 22
**Pattern extraction date:** 2026-04-26
