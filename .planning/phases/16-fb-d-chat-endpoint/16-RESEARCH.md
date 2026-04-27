# Phase 16 (FB-D): Chat Endpoint — Research

**Researched:** 2026-04-27
**Domain:** HTTP chat endpoint over `LLMRouter.complete_with_tools()` (FB-C); integration glue, not new infrastructure
**Confidence:** HIGH (every recommended pattern verified in checked-in code; no new dependencies in scope)

---

## Summary

FB-D is the smallest of the FB-* phases — five acceptance criteria, all of which are **wire-up** rather than new infrastructure. CONTEXT.md has already locked 21 decisions (D-01..D-21) including streaming posture, request/response shape, sensitivity routing, error envelope, rate-limit algorithm, timeout pattern, and UI-panel UX. This research validates those decisions against the actual checked-in FB-C code, surfaces five non-obvious pitfalls, and confirms the planner can proceed without re-deciding scope.

**Primary recommendation:** Treat FB-D as a thin Starlette handler + a vanilla-JS template + an in-process token-bucket dict — no new dependencies, no new abstractions. Reuse Phase 9/14's `_envelope`/`_error` helpers (`forge_bridge/console/handlers.py:53-60`), Phase 9's `app.state.console_read_api._llm_router` injection (`forge_bridge/console/read_api.py:84-102`), FB-C's already-shipped exception classes (`LLMLoopBudgetExceeded`, `RecursiveToolLoopError`, `LLMToolError` at `forge_bridge/llm/router.py:75-130`), and Phase 10's existing CSS palette (`forge_bridge/console/static/forge-console.css:1-69`). The five pitfalls below are the load-bearing surface area.

**Five pitfalls in priority order:**

1. **`request.client` may be `None`** — Starlette's docs say `if request.client:` is the safe pattern. If the chat handler dereferences `request.client.host` blindly, the test client (`httpx.AsyncClient(app=app)`) and any ASGI proxy without a remote-addr scope key crashes the rate limiter and surfaces as HTTP 500.
2. **Nested `asyncio.wait_for` already exists in FB-C** — `complete_with_tools()` at `router.py:582` already wraps `_loop_body()` in `asyncio.wait_for(timeout=max_seconds)`. The chat handler's outer `asyncio.wait_for(timeout=125.0)` is wrapping a coroutine that has its own internal timeout. This works but has a subtle race: when both fire near-simultaneously the inner `LLMLoopBudgetExceeded("max_seconds", ...)` may be in-flight when the outer cancels. We need to catch BOTH `asyncio.TimeoutError` AND `LLMLoopBudgetExceeded(reason="max_seconds")` and translate both to HTTP 504.
3. **Tool-list snapshot must call `mcp.list_tools()`** — D-04 says "snapshot at request time"; the existing FB-C executor at `mcp/registry.py:230-238` uses `await mcp.list_tools()` to get the live registry. The handler needs the same call to assemble the `tools=[...]` arg. **Pitfall:** `mcp.list_tools()` returns `list[mcp.types.Tool]` (already the right shape — no translation needed), but it is `async`. Calling it inside the handler is fine; calling it inside a sync helper is not.
4. **Phase 10 ships NO markdown renderer** — verified by reading `templates/execs/detail.html:23` (uses raw `<pre>` for code) and grepping `templates/` for "markdown" (zero hits). D-11 says "match whatever Phase 10 uses … or a 50-line vanilla pass through" — Phase 10 uses neither. The planner needs to pick: (a) ship a 30-50 line vanilla JS escaper + fenced-code-block renderer, (b) escape-only and live with no formatting, or (c) punt to v1.4.x. Recommendation in §6 below.
5. **The chat-nav stub already routes correctly** — `forge_bridge/console/app.py:86` already wires `/ui/chat → ui_chat_stub_handler`, and `templates/shell.html:12` already has the `<a href="/ui/chat">` nav link. D-20 is correct: the change is purely *content* — replace the stub template + replace the handler body. The route table and shell.html stay unchanged.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP request parsing + validation | API / Backend (Starlette handler) | — | Body shape contract lives at the API boundary; CONTEXT D-02 native messages shape |
| Rate limiting (IP-keyed token bucket) | API / Backend | — | In-memory dict; single-bridge-process per machine (STATE.md). Pre-handler logic, not middleware (one route only). |
| LLM tool-call orchestration | LLMRouter (existing FB-C surface) | — | `complete_with_tools()` shipped Phase 15; chat handler is a thin caller. |
| Tool registry snapshot | MCP registry (existing) | API / Backend | Handler calls `mcp.list_tools()` (async) once per request, passes to coordinator. |
| Sanitization (tool defs + tool results) | LLM module + Learning module (already wired) | — | Phase 7 + FB-C already enforce; D-15 says "no new wiring." |
| Conversation history persistence | Browser / Client (per-tab JS) | — | D-06 explicit: no server-side persistence in v1.4 (no auth → no per-user boundary). |
| Markdown rendering | Browser / Client (vanilla JS) | — | D-11: no new dep; one-tab-only scope means client-side is acceptable. |
| Tool-call transparency UI | Browser / Client (collapsed `<details>`) | — | D-07: `<details>` is the native HTML disclosure widget; no JS needed for collapse/expand. |

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 Streaming:** Non-streaming JSON for v1.4. `SEED-CHAT-STREAMING-V1.4.x` plants the migration path.

**D-02 Request shape:** Native `{messages: [...], max_iterations?, max_seconds?, tool_result_max_bytes?}`. Roles: `user | assistant | tool` matching FB-C `_ToolAdapter.append_results()`.

**D-03 Response shape:** `{messages: [...full echoed history...], stop_reason: "end_turn"|"max_iterations"|"max_seconds_exceeded", request_id: "<uuid>"}`.

**D-04 Tool registry exposure:** All registered MCP tools, snapshot at request time via `mcp.list_tools()`. No allowlist (`SEED-CHAT-TOOL-ALLOWLIST-V1.5`).

**D-05 Sensitivity routing:** Hardcoded `sensitive=True` (local Ollama). No `sensitive` field in request body. (`SEED-CHAT-CLOUD-CALLER-V1.5`).

**D-06 UI history:** Per-tab in-browser JS state, cleared on tab close. No server persistence (`SEED-CHAT-PERSIST-HISTORY-V1.5+`).

**D-07 Tool-call transparency:** Collapsed `<details>` per tool round, click to expand args + 500-char truncated result preview.

**D-08 Spinner:** LOGIK-PROJEKT amber, reuse existing `forge-console.css` palette (no new SVG asset).

**D-09 Error banners:** HTTP 429 / 504 / 500 / 422 with prescribed plain-English copy; HTTP 422 surfaces validator message.

**D-10 Input:** Single auto-growing `<textarea>` (~5 lines max). Enter sends, Shift+Enter newline. No slash commands.

**D-11 Markdown:** Vanilla minimal renderer. No new dep. (See §6 — Phase 10 ships no renderer; planner picks scope here.)

**D-12 Artist UAT:** D-36 hard fresh-operator gate. Real artist on assist-01. Failure → remediation phase analogous to Phase 10.1.

**D-13 Rate limiting:** In-memory token bucket dict, IP-keyed (`request.client.host`), capacity 10 / refill 10/60s, lazy 5-min TTL eviction, 429 envelope + `Retry-After` header.

**D-14 Wall-clock timeout:** Outer `asyncio.wait_for(coordinator_call, timeout=125.0)` wrapping FB-C's inner 120s. `TimeoutError` → HTTP 504.

**D-15 Sanitization:** Tool defs already sanitized by Phase 7 at registration; tool results already sanitized by FB-C inside the loop. User input NOT sanitized (would damage UX). Verification: integration test with poisoned tool sidecar.

**D-16 LLMRouter injection:** Reuse `app.state.console_read_api._llm_router` (Phase 9 D-25 instance-identity invariant).

**D-17 Error envelope:** `{"error": "<machine_code>", "message": "<human>", "request_id": "<uuid>"}` — verbatim Phase 9/14 shape. Codes: `rate_limit_exceeded`, `request_timeout`, `validation_error`, `internal_error`, `unsupported_role`.

**D-18 Parity test:** Two clients (browser fetch + stub Flame-hooks Python) replay same payload, assert structural shape match.

**D-19 OpenAPI:** None in v1.4. Inline docstring + integration test = the contract.

**D-20 Stub replacement:** Delete `templates/chat/stub.html`, create `templates/chat/panel.html`. Nav link unchanged (`shell.html:12`).

**D-21 Logging:** Per-call structured log: `request_id`, `client_ip`, `message_count_in`, `message_count_out`, `tool_call_count`, `stop_reason`, `wall_clock_ms`. Reuse existing `logging_config.py`.

### Claude's Discretion

- Internal handler module organization (one file vs split into rate-limit + handler + body-validator)
- Pydantic vs hand-rolled body validation (recommendation in §3 below: Pydantic 2)
- Markdown renderer scope (escape-only vs minimal-fences-and-bold; recommendation §6)
- Test file count + organization (existing pattern: `tests/console/test_handlers.py`)

### Deferred Ideas (OUT OF SCOPE)

| SEED file | Triggers when |
|-----------|---------------|
| `SEED-CHAT-STREAMING-V1.4.x.md` | After v1.4 ships; non-streaming UX baseline validated |
| `SEED-CHAT-TOOL-ALLOWLIST-V1.5.md` | When v1.5 consumer needs request-time tool subsetting |
| `SEED-CHAT-CLOUD-CALLER-V1.5.md` | When `SEED-AUTH-V1.5` lands (caller-identity → cost attribution) |
| `SEED-CHAT-PERSIST-HISTORY-V1.5+.md` | When auth + per-user data scoping land |

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | IP rate limit (11 req/min → 429) | §3.1 — token-bucket pattern + `request.client` pitfall |
| CHAT-02 | 125s wall-clock timeout | §3.2 — nested `wait_for` interaction with FB-C's 120s inner cap |
| CHAT-03 | End-to-end sanitization (no new wiring) | §3.3 — verified Phase 7 + FB-C already enforce |
| CHAT-04 | Artist dogfood UAT (<60s) | §3.4 — D-36 pattern + observability shape needed for debrief |
| CHAT-05 | External-consumer parity (browser + Flame hooks) | §3.5 — structural-shape assertion approach |

---

## Standard Stack

### Already Pinned (no new deps in FB-D)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Starlette | (transitive via mcp) | HTTP framework — `Route`, `Request`, `JSONResponse` | Already the v1.3 chat surface. `[VERIFIED: forge_bridge/console/app.py:8-13]` |
| Pydantic | 2.x (transitive via mcp) | Request body validation | Already used by 15+ tool input schemas. `[VERIFIED: grep "from pydantic import BaseModel" in forge_bridge/tools/]` |
| anthropic | `>=0.97,<1` | Cloud LLM (NOT used by chat — D-05 hardcodes sensitive=True) | Already pinned. `[VERIFIED: pyproject.toml:30]` |
| ollama | `>=0.6.1,<1` | Local LLM (used by FB-C inside `complete_with_tools()`) | Already pinned. `[VERIFIED: pyproject.toml:31]` |
| jinja2 | `>=3.1` | Template rendering | Already used by Phase 10 UI. `[VERIFIED: pyproject.toml:20]` |
| httpx | `>=0.27` | Test client + Flame-hooks parity stub | Already pinned. `[VERIFIED: pyproject.toml:13]` |

### Forbidden (per CONTEXT.md "no new dependencies")

| Library | Why Rejected | Alternative |
|---------|--------------|-------------|
| `slowapi` | FastAPI-only (we're on Starlette); adds 200KB+ for one route | In-memory token-bucket dict (~50 LOC) per D-13 |
| `pyrate-limiter` | New dep, multi-storage abstraction unneeded | Same |
| `markdown` / `markdown2` | Server-side render unneeded; full GFM is overkill for chat | Vanilla JS escaper + fenced-block renderer (§6) |
| `marked` / `markdown-it` (JS) | New vendored asset; D-11 says vanilla pass | Hand-rolled <50 LOC JS escaper (§6) |

**Verification of "no new deps":** the only optional dep delta in v1.4 was `ollama>=0.6.1,<1` for FB-C, already shipped. FB-D adds zero deps. `[VERIFIED: pyproject.toml diff vs v1.3 baseline]`

---

## Architecture Patterns

### System Architecture Diagram

```
┌─ Client (Web UI tab OR projekt-forge Flame hook) ──────────────┐
│  POST /api/v1/chat                                              │
│  Body: {messages: [...], max_iterations?, max_seconds?}         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─ Starlette Route (forge_bridge/console/app.py) ────────────────┐
│  Route("/api/v1/chat", chat_handler, methods=["POST"])         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─ chat_handler (forge_bridge/console/handlers.py) ──────────────┐
│  1. Resolve client IP   → request.client.host (if not None)    │
│  2. Token-bucket gate   → 429 + Retry-After if exhausted       │
│  3. Parse + validate    → Pydantic ChatRequest model           │
│  4. Snapshot tool list  → await mcp.list_tools()               │
│  5. Build request_id    → uuid.uuid4()                          │
│  6. Outer wait_for(125) →                                      │
│      └─→ router.complete_with_tools(                            │
│             tools=tools, sensitive=True,                        │
│             max_iterations=body.max_iterations or 8,            │
│             max_seconds=120.0)                                  │
│  7. Translate exception → HTTP status + envelope               │
│      • LLMLoopBudgetExceeded(max_seconds) → 504                │
│      • LLMLoopBudgetExceeded(max_iterations) → 200 stop_reason │
│      • RecursiveToolLoopError → 500                            │
│      • LLMToolError → 502                                       │
│      • asyncio.TimeoutError (outer fired) → 504                │
│      • ValidationError (Pydantic) → 422                         │
│  8. Emit structured log → D-21 fields                          │
│  9. Return envelope     → {data: {messages, stop_reason},       │
│                            meta: {request_id}}                  │
└─────────────────────────────────────────────────────────────────┘
                      │
                      ▼ (consumes existing FB-C surface)
┌─ LLMRouter.complete_with_tools (forge_bridge/llm/router.py) ───┐
│  - asyncio.wait_for(_loop_body(), timeout=120s) [INNER cap]    │
│  - Sanitization, repeat-detect, recursion-guard already wired  │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Plan Structure

```
forge_bridge/console/
├── handlers.py              # add chat_handler + _ChatRequestBody Pydantic model
├── _rate_limit.py           # NEW — token bucket impl (~50 LOC)
├── app.py                   # add Route("/api/v1/chat", ...)
└── templates/
    └── chat/
        ├── panel.html       # NEW — replaces stub.html
        └── _markdown.js     # NEW — inline <script> or vendor file (D-11)
```

Test layout (matches existing convention):
```
tests/console/
├── test_chat_handler.py     # CHAT-01..04 deterministic tests (stub LLM router)
├── test_rate_limit.py       # CHAT-01 token bucket unit tests
└── test_chat_parity.py      # CHAT-05 browser + flame-hooks stub clients
```

### Pattern 1: Pydantic Body Validation
**What:** Validate the request body via a Pydantic 2 `BaseModel` instead of hand-parsed `dict[str, Any]`.
**When to use:** Always for user-facing JSON endpoints when the schema has constraints.

```python
# Source: forge_bridge/console/handlers.py pattern (Phase 9 + 14 baseline)
from pydantic import BaseModel, Field, ValidationError
from typing import Literal

class _ChatMessage(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None  # required when role == "tool"

class _ChatRequestBody(BaseModel):
    messages: list[_ChatMessage] = Field(min_length=1)
    max_iterations: int = Field(default=8, ge=1, le=32)
    max_seconds: float = Field(default=120.0, gt=0, le=300.0)
    tool_result_max_bytes: int = Field(default=8192, ge=512, le=131072)

# Inside the handler:
try:
    body = _ChatRequestBody.model_validate(await request.json())
except ValidationError as exc:
    return _error("validation_error", exc.errors()[0]["msg"], status=422)
```

**Why Pydantic over `dict[str, Any]`:** the existing FB-B handlers parse manually (`uuid.UUID(op_id_raw)` then try/except) because the surface is small. Chat has 4+ fields with type/range constraints — Pydantic eliminates 30+ lines of validator boilerplate and produces consistent error messages. **Verified:** Pydantic 2 is already in the dep tree via `mcp[cli]>=1.19`.

**Pitfall:** `model_validate()` in Pydantic 2 (NOT `parse_obj()` — that's deprecated). `[CITED: docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel.model_validate]`

### Pattern 2: Token Bucket Rate Limit (D-13)
**What:** A small in-memory dict keyed by client IP; each value is a `_TokenBucket` dataclass with lazy refill on `consume()` and lazy TTL eviction.
**When to use:** Single-process bridge with no multi-instance ambitions in v1.4 (`[VERIFIED: STATE.md "single-bridge process per machine"]`).

```python
# Source: synthesized from oneuptime.com 2026-01-22 + Phase 9 patterns
# File: forge_bridge/console/_rate_limit.py
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Tuple

# D-13: capacity=10, refill_rate=10/60 per second → 11th req in 60s → 429
_DEFAULT_CAPACITY = 10.0
_DEFAULT_REFILL_RATE_PER_SECOND = 10.0 / 60.0
_TTL_SECONDS = 300.0  # 5-minute idle eviction per D-13

@dataclass
class _TokenBucket:
    capacity: float = _DEFAULT_CAPACITY
    refill_rate: float = _DEFAULT_REFILL_RATE_PER_SECOND
    tokens: float = field(default=_DEFAULT_CAPACITY)
    last_seen: float = field(default_factory=time.monotonic)

    def consume(self, n: float = 1.0) -> Tuple[bool, float]:
        """Returns (allowed, retry_after_seconds). retry_after is 0 when allowed."""
        now = time.monotonic()
        elapsed = now - self.last_seen
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_seen = now
        if self.tokens >= n:
            self.tokens -= n
            return True, 0.0
        retry_after = (n - self.tokens) / self.refill_rate
        return False, retry_after

class IPRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _TokenBucket] = {}
        self._last_sweep: float = time.monotonic()

    def check(self, ip: str) -> Tuple[bool, float]:
        # Lazy TTL sweep — every consume() call inspects up to N buckets.
        # Cheaper than a background sweeper and bounded by call rate.
        now = time.monotonic()
        if now - self._last_sweep > 60.0:
            stale = [k for k, b in self._buckets.items()
                     if now - b.last_seen > _TTL_SECONDS]
            for k in stale:
                del self._buckets[k]
            self._last_sweep = now

        bucket = self._buckets.get(ip)
        if bucket is None:
            bucket = _TokenBucket()
            self._buckets[ip] = bucket
        return bucket.consume()
```

**Mounting:** Single module-level instance attached to `app.state` in `build_console_app`:

```python
# forge_bridge/console/app.py — addition
from forge_bridge.console._rate_limit import IPRateLimiter
app.state.chat_rate_limiter = IPRateLimiter()
```

**Pitfall — `request.client` may be `None`:** Starlette's official docs `[CITED: github.com/kludex/starlette/blob/main/docs/requests.md]` explicitly use `if request.client:` before accessing `.host`. The httpx test-client doesn't set it; nor do some ASGI proxies. Defensive pattern:

```python
client_ip = request.client.host if request.client else "unknown"
```

If we treat all "unknown" callers as a single bucket, an attacker behind a reverse proxy that strips remote-addr can DoS through one shared bucket — but that's already the security posture for v1.4 (we have no auth). Document and move on; SEED-AUTH-V1.5 is the resolution.

### Pattern 3: Nested `asyncio.wait_for` (CHAT-02)
**What:** Outer 125s wraps a coroutine that internally does its own 120s wait_for.
**When to use:** Defense in depth — the outer guard catches *anything* that isn't the FB-C loop itself blocking (e.g., the `await mcp.list_tools()` snapshot blocks; the `await request.json()` body parse blocks).

```python
# Inside chat_handler — verified against FB-C's actual surface
import asyncio
import uuid
from forge_bridge.llm.router import (
    LLMLoopBudgetExceeded, RecursiveToolLoopError, LLMToolError,
)

request_id = str(uuid.uuid4())
try:
    final_text = await asyncio.wait_for(
        router.complete_with_tools(
            prompt=last_user_message,
            tools=tools_snapshot,
            sensitive=True,
            max_iterations=body.max_iterations,
            max_seconds=120.0,  # FB-C inner cap
            tool_result_max_bytes=body.tool_result_max_bytes,
        ),
        timeout=125.0,  # CHAT-02: outer cap = 120s + 5s framing buffer
    )
    stop_reason = "end_turn"
except asyncio.TimeoutError:
    # Outer fired before inner LLMLoopBudgetExceeded propagated.
    return _error("request_timeout", "Response timed out — try a simpler question.", status=504)
except LLMLoopBudgetExceeded as exc:
    # Inner fired and propagated. exc.reason ∈ {"max_iterations", "max_seconds"}.
    if exc.reason == "max_seconds":
        return _error("request_timeout", "Response timed out — try a simpler question.", status=504)
    # max_iterations: this is a "soft" termination per D-03 — return the partial
    # conversation as a 200 with stop_reason="max_iterations" so the client can
    # decide whether to continue with a follow-up turn.
    # NOTE: requires capturing partial state before the exception fires.
    # See pitfall §4.2 below — FB-C does NOT expose partial state today.
    ...
except RecursiveToolLoopError:
    return _error("internal_error", "Chat error — check console for details.", status=500)
except LLMToolError:
    return _error("internal_error", "LLM provider error.", status=502)
```

**Pitfall — partial state on max_iterations:** FB-C's `complete_with_tools()` returns a single `str` (the final terminal text) and raises `LLMLoopBudgetExceeded` when caps fire. There is no public partial-state accessor. **D-03 says response includes `stop_reason: "max_iterations"`**, which means FB-D either (a) reconstructs partial state from logs, (b) extends the FB-C surface to expose it, or (c) treats `max_iterations` as 504 like `max_seconds`. Recommendation in §4.2 below.

### Pattern 4: Tool Snapshot via `mcp.list_tools()`
**What:** Use the same async public API that FB-C's `invoke_tool` uses (`forge_bridge/mcp/registry.py:230-238`).

```python
# Inside chat_handler
from forge_bridge.mcp import server as _mcp_server
tools_snapshot = await _mcp_server.mcp.list_tools()
# Returns list[mcp.types.Tool] — exactly what complete_with_tools(tools=...) expects
```

**Pitfall:** FB-C's `complete_with_tools()` raises `ValueError` if `tools=[]`. Edge case — if `register_builtins()` hasn't run for some reason, `mcp.list_tools()` returns empty and the chat handler would surface this as a 500. Add an explicit early check: empty list → 503 `service_unavailable` "tool registry not initialized" (this is structural, not user error).

### Anti-Patterns to Avoid

- **Hand-parsing the message array** — Pydantic validation is already in the tree via `mcp[cli]`; parsing 3-role-tagged-union arrays by hand is 40+ lines of `isinstance` checks per spec D-02.
- **Putting rate limit in CORSMiddleware-style middleware** — middleware applies to the whole app; we want it on `/api/v1/chat` only. Per-handler check is one line and correct.
- **Calling `complete_with_tools()` from within the handler's outer `try/except Exception`** — the FB-C exceptions are deliberately public so callers can dispatch on type. Catch them by class, not by `except Exception as e: return 500`.
- **Stripping `assistant` history from the response** — D-03 explicitly echoes the full history including the new assistant + tool turns. Returning only the final text means the client must re-parse from logs. Don't.
- **Reading messages array as the prompt for `complete_with_tools()`** — the FB-C signature takes `prompt: str`, not `messages: list`. The handler must pull the *last* user message as the prompt and pass *prior* turns via system or context. **See pitfall §4.3** — this is a real design mismatch with D-02.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request body validation | Hand-rolled `if "messages" not in body: return 400` | Pydantic `BaseModel.model_validate()` | Already in deps; produces consistent error messages |
| Rate-limit storage | Redis client + adapter | `dict[str, _TokenBucket]` in module state | Single-process bridge; STATE.md confirms no multi-instance v1.4 |
| Markdown rendering (server side) | `markdown`, `markdown2`, `mistune` | Vanilla JS in browser (escape + fenced-block + bold) | Per-tab JS-only state means render is client-side; D-11 forbids new dep |
| Spinner asset | New SVG/PNG | Reuse `--color-accent: #cc9c00` + CSS keyframes | D-08 explicit |
| Conversation history persistence | Server-side store | Browser JS array in component state | D-06 explicit; SEED for auth-paired path |
| OpenAPI schema | `fastapi.openapi.utils` (we're on Starlette anyway) | Inline docstring + integration test | D-19 explicit |
| Tool registry walking | Custom MCP introspection | `await mcp.list_tools()` (existing public API) | Same call FB-C `invoke_tool` uses |

**Key insight:** FB-D is "wire it up." Every internal piece already exists. The only new code is (a) ~50-line token bucket, (b) ~150-line handler with Pydantic body model + exception dispatch, (c) ~200-line panel.html template + ~50-line vanilla JS, (d) the parity test. That's the entire phase.

---

## Common Pitfalls

### Pitfall 1: `request.client` is None in tests
**What goes wrong:** Tests using `httpx.AsyncClient(app=app)` produce a request scope without `client`. Handler crashes on `request.client.host`.
**Why it happens:** Starlette `[CITED: github.com/kludex/starlette/blob/main/docs/requests.md]` returns `None` when the ASGI scope has no client (test client default; some proxy configurations).
**How to avoid:** `client_ip = request.client.host if request.client else "unknown"` — pattern verified in Starlette's own docs.
**Warning signs:** A unit test calls the handler and gets `AttributeError: 'NoneType' object has no attribute 'host'` instead of the expected 200 envelope.

### Pitfall 2: Outer + inner `wait_for` race on max_iterations
**What goes wrong:** The 125s outer wraps `complete_with_tools()`, which has its own 120s wrapping `_loop_body()`. When the iteration cap fires (NOT the wall-clock cap), the inner method raises `LLMLoopBudgetExceeded(reason="max_iterations")`. D-03 says we return that as a *200 success* with `stop_reason: "max_iterations"`. But — **`complete_with_tools()` returns a `str`, not the message history**. So when iteration cap fires, the partial assistant+tool turns are lost.
**Why it happens:** FB-C's signature is `complete_with_tools(...) -> str` — designed for "give me the final text." It doesn't expose intermediate turns to the caller.
**How to avoid:** Three options:

| Option | Cost | Correctness |
|--------|------|------------|
| A. Treat `max_iterations` as 504 like `max_seconds` | Trivial | Surrenders D-03's distinct stop_reason |
| B. Extend FB-C to return `(text, messages_history)` | One-line API change in FB-C | Cleanest; preserves D-03 |
| C. Reconstruct messages from log lines | High; brittle | Worst |

**Recommendation: B.** Add an optional `return_history: bool = False` kwarg to `complete_with_tools()` that returns `tuple[str, list[dict]]` when True. FB-D passes True. Backward-compatible (default False = current behavior). Or — alternative **B':** raise an enhanced `LLMLoopBudgetExceeded` with a `partial_messages` field. Either works; B' keeps the success path cleaner.

**Critical:** This is an FB-C deviation. Either flag it for the discuss-phase to confirm, or have the planner add a small follow-up plan that extends `complete_with_tools()` before the chat handler plan lands. **Without resolving this, D-03's `stop_reason: "max_iterations"` is a contract that can't be honored.**

**Warning signs:** Integration test with `max_iterations=2` and a stub-LLM that always tool-calls returns `{"messages": [original_messages_only], "stop_reason": "max_iterations"}` — but the loop ran two iterations and the messages array doesn't reflect them.

### Pitfall 3: D-02 messages array vs FB-C `prompt: str` signature
**What goes wrong:** Request body D-02 carries `messages: [...]` (multi-turn). FB-C's `complete_with_tools(prompt: str, ...)` takes a single user prompt. Naïve handlers pull `messages[-1]["content"]` as the prompt, losing all prior conversation.
**Why it happens:** FB-C was scoped pre-FB-D. CONTEXT D-02 was written assuming FB-C accepts a messages array; it doesn't (verified `forge_bridge/llm/router.py:252-264`).
**How to avoid:** Two viable patterns:

**Pattern A — Stitch prior turns into the prompt:**
```python
# Last user message is the prompt; prior turns become context in `system`.
last_user = next(m for m in reversed(body.messages) if m.role == "user")
prior_turns = body.messages[:body.messages.index(last_user)]
context_block = "\n\n".join(f"{m.role.upper()}: {m.content}" for m in prior_turns)
system_with_history = f"{router.system_prompt}\n\nPrior conversation:\n{context_block}"
final = await router.complete_with_tools(
    prompt=last_user.content,
    system=system_with_history,
    tools=tools_snapshot,
    sensitive=True, ...)
```

**Pattern B — Extend FB-C to accept `messages: list[dict] | None = None`:**
```python
# In router.py — non-breaking optional kwarg
async def complete_with_tools(self, prompt: str, ..., messages: list[dict] | None = None):
    if messages is not None:
        # adapter init_state uses messages directly
        state = adapter.init_state_from_messages(messages, system=sys_msg, tools=tools, ...)
    else:
        state = adapter.init_state(prompt=prompt, system=sys_msg, ...)
```

**Recommendation: A (Pattern A) for v1.4.** Reason: keeps FB-C's surface stable and is fully sufficient for the artist-UAT use case (one-shot questions). The planner should plant `SEED-CHAT-MULTITURN-NATIVE-V1.4.x.md` for Pattern B once the artist UAT shows real multi-turn use. Pattern A is a slightly lossy serialization (the LLM sees prior turns as system context, not as Anthropic/Ollama-native message blocks) but for chat use cases where the artist asks one question, it doesn't matter.

**Warning signs:** Integration test with two-turn history (`[{user: "list shots"}, {assistant: "..."}, {user: "now versions"}]`) — the second user turn is treated as a fresh prompt without context.

### Pitfall 4: Ollama default model bypassed by D-05 hardcoding
**What goes wrong:** D-05 hardcodes `sensitive=True`. The `LLMRouter.local_model` defaults to `qwen2.5-coder:32b` (`router.py:188`). FB-C research §3.5 documents that `qwen2.5-coder:32b` works for tool calling but is older and slower than `qwen3:32b`. **For the CHAT-04 <60s artist UAT, model speed matters.**
**Why it happens:** `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` was planted but not yet executed.
**How to avoid:** Verify on assist-01 BEFORE the artist UAT that a representative chat completes in <60s on `qwen2.5-coder:32b`. If it doesn't, the planner should consider executing the model bump in a separate plan within FB-D scope (not waiting for v1.4.x). The bump itself is a one-line `_DEFAULT_LOCAL_MODEL` env-default change (`router.py:188`).
**Warning signs:** Artist UAT prompt produces a useful answer but in 80-100s. CHAT-04 fails not on correctness but on latency.

### Pitfall 5: Tool-call transparency vs sanitization conflict
**What goes wrong:** D-07 says collapsed `<details>` shows `{tool_name}({args_preview})`. D-15 says tool defs and tool results are sanitized. The Web UI display side renders **already-sanitized** tool args back in the panel. If a tool's args contained an injection marker, the marker has been replaced by `[BLOCKED:INJECTION_MARKER]` before the LLM saw it — **but the UI shows the LLM's view, not the raw caller args**. So an artist running a deliberate test ("show me the prompt-injection demo") sees `[BLOCKED:INJECTION_MARKER]` in the args preview, which is correct but confusing.
**Why it happens:** Sanitization is an LLM-input concern; UI display is a UX concern; they're conflated when the UI renders the same string the LLM saw.
**How to avoid:** Document explicitly in the panel template: the args preview shows what the LLM saw. If a value reads `[BLOCKED:INJECTION_MARKER]`, the input was sanitized for safety. This is correct behavior but needs to be visible to the artist UAT operator so the D-36 gate doesn't fail on "wait, what is this gibberish?"
**Warning signs:** Artist UAT prompt triggers a tool with sensitive content; artist sees `[BLOCKED:INJECTION_MARKER]` and assumes the system is broken.

---

## Code Examples

Verified patterns from the existing codebase:

### Existing handler envelope pattern (reuse verbatim)
```python
# Source: forge_bridge/console/handlers.py:53-60 (verified)
def _envelope(data, **meta) -> JSONResponse:
    """2xx envelope — applied on every success path (D-01)."""
    return JSONResponse({"data": data, "meta": meta})

def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    """4xx/5xx envelope — applied on every failure path. NEVER leak tracebacks."""
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)
```

### Existing LLMRouter injection pattern (reuse verbatim)
```python
# Source: forge_bridge/console/read_api.py:84-102 — _llm_router constructor arg
# Source: forge_bridge/console/app.py:110 — app.state.console_read_api = read_api
# Inside chat_handler:
router = request.app.state.console_read_api._llm_router
if router is None:
    return _error("service_unavailable", "LLM router not configured", status=503)
```

### FB-C exception import pattern
```python
# Source: forge_bridge/llm/router.py:75-130 (verified)
from forge_bridge.llm.router import (
    LLMLoopBudgetExceeded,
    RecursiveToolLoopError,
    LLMToolError,
)
# Per FB-C D-15: also exported from forge_bridge.__all__ (16→19)
# So this also works:
from forge_bridge import LLMLoopBudgetExceeded  # if user prefers barrel import
```

### Existing error-card / banner CSS classes (reuse for D-09)
```css
/* Source: forge_bridge/console/static/forge-console.css:38-40 */
.error-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 16px; max-width: 640px; margin: 64px auto; }
/* Source: forge_bridge/console/static/forge-console.css:48-50 — agg-pill borders we mirror for chat status banners */
.agg-pill.status-degraded { border-color: var(--color-accent); }
.agg-pill.status-fail { border-color: var(--color-status-error); }
```

For chat panel D-09 banners, recommend mirroring `.error-card` shape with `.chat-banner--429`, `.chat-banner--504`, `.chat-banner--500` modifier classes — matches Phase 10 design pattern.

### Existing logger pattern for D-21 structured log
```python
# Source: forge_bridge/console/handlers.py:34-45 (verified)
import logging
logger = logging.getLogger(__name__)

# D-21 structured per-call log line — match FB-C's per-session log shape:
logger.info(
    "chat-request request_id=%s client_ip=%s message_count_in=%d "
    "message_count_out=%d tool_call_count=%d stop_reason=%s wall_clock_ms=%d",
    request_id, client_ip, len(body.messages), len(response_messages),
    tool_call_count, stop_reason, wall_clock_ms,
)
```

---

## Markdown Rendering Recommendation (D-11 resolution)

**Verified state:** Phase 10 ships **no markdown renderer**. `templates/execs/detail.html:23` uses raw `<pre>{{ record.raw_code }}</pre>` for code (escaped by Jinja2 default autoescape). There is no client-side renderer; there is no server-side renderer.

**Three viable scopes for FB-D:**

| Option | LOC | Capabilities | Risk |
|--------|-----|--------------|------|
| **A. Escape-only** | ~10 | Plain text, line breaks, no formatting | LLM output looks ugly when it returns markdown |
| **B. Minimal vanilla (RECOMMENDED)** | ~50 | Fenced code blocks (`\`\`\``), inline code (`\``), bold (`**`), line breaks, links | Covers ~95% of LLM output formatting |
| **C. Full GFM via vendored marked.min.js** | New 50KB asset | Tables, lists, headings, GFM | Violates "no new dep" |

**Recommendation: B.** Sample implementation (~45 LOC):

```javascript
// Source: hand-rolled, verified-safe HTML escape + minimal markdown
function renderMarkdown(text) {
  // 1. Extract fenced code blocks first (preserve raw, escape)
  const codeBlocks = [];
  let placeholder = (i) => ` CODEBLOCK${i} `;
  text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (_m, lang, code) => {
    codeBlocks.push({ lang: lang || '', code });
    return placeholder(codeBlocks.length - 1);
  });

  // 2. Escape HTML
  text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // 3. Inline code
  text = text.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // 4. Bold
  text = text.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');

  // 5. Links — only http/https for safety
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
                      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

  // 6. Line breaks
  text = text.replace(/\n/g, '<br>');

  // 7. Restore code blocks (escape contents)
  text = text.replace(/ CODEBLOCK(\d+) /g, (_m, i) => {
    const { lang, code } = codeBlocks[parseInt(i, 10)];
    const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<pre class="code-block" data-lang="${lang}"><code>${escaped}</code></pre>`;
  });

  return text;
}
```

**Critical safety properties** (verify in test):
- Pre-extracts code blocks BEFORE any other transforms — prevents `**bold**` inside code from rendering.
- Escapes HTML before applying any tag substitution — prevents `<script>` injection.
- Whitelists `http://` and `https://` for links only — no `javascript:` URI risk.
- `target="_blank" rel="noopener noreferrer"` on all links — prevents reverse-tabnabbing.

**Test pattern:**
```javascript
// In a Playwright test or JS unit test
expect(renderMarkdown('<script>alert(1)</script>')).not.toContain('<script>');
expect(renderMarkdown('[click](javascript:alert(1))')).not.toContain('javascript:');
expect(renderMarkdown('```py\nprint("hi")\n```')).toContain('<pre class="code-block"');
```

**Place at:** `forge_bridge/console/static/chat-markdown.js` (vendored asset, served via existing `/ui/static/` mount).

---

## Anthropic / Ollama Messages-Shape Confirmation (research §3 from CONTEXT)

**D-02 carries roles `user | assistant | tool`.** Verified against FB-C research:

| Provider | role for tool result | role for tool call result | Field name |
|----------|---------------------|--------------------------|------------|
| Anthropic | `user` (with `tool_result` block) | `assistant` (with `tool_use` block) | `tool_use_id` for matching |
| Ollama | `tool` (recently added) | `assistant` (with `tool_calls`) | `tool_name` (NOT `tool_call_id`) |

**Conflict surfaced:** Anthropic uses `role: "user"` for tool results (with structured content blocks), while Ollama uses `role: "tool"` (with simple string content). **D-02 chose `role: "tool"` (Ollama-style)** — this is correct for v1.4 because D-05 hardcodes `sensitive=True` (Ollama path only). If/when SEED-CHAT-CLOUD-CALLER-V1.5 lands and the cloud path is enabled, the chat handler will need to translate request-side `role: "tool"` → adapter's Anthropic state. FB-C's `_ToolAdapter` Protocol already does this at the adapter layer (`init_state_from_messages` is the conceptual hook) — so the divergence stays inside the adapter, not the public API.

**Pitfall:** A request body with `role: "tool"` but `sensitive: true` request hardcoded — the adapter (Ollama) accepts `role: "tool"` natively. A request body with `role: "tool"` but later we flip to Anthropic — translation needed. Document this constraint in the docstring; the parity test (CHAT-05) verifies the v1.4 single-provider path.

`[VERIFIED: forge_bridge/llm/router.py + FB-C-TOOL-CALL-LOOP.md §2.3, §3.3]`

---

## External-Consumer Parity Test Design (CHAT-05)

**Challenge:** LLM output is non-deterministic. Asserting "byte-identical responses" between browser fetch and Flame-hooks Python is impossible. CONTEXT D-18 says "structural shape match."

**Recommended structural assertions:**

```python
# Source: pattern derived from FB-B's existing zero-divergence test
# tests/console/test_chat_parity.py

import httpx
import pytest

PROMPT = "what synthesis tools were created this week?"
PAYLOAD = {"messages": [{"role": "user", "content": PROMPT}]}

@pytest.mark.asyncio
async def test_chat_parity_browser_vs_flame_hooks(chat_app):
    """CHAT-05: same /api/v1/chat endpoint behaves identically across clients."""
    # Client 1: simulates browser fetch (the Web UI panel)
    async with httpx.AsyncClient(app=chat_app, base_url="http://t") as c1:
        r1 = await c1.post("/api/v1/chat", json=PAYLOAD)

    # Client 2: simulates projekt-forge v1.5 Flame-hooks Python
    async with httpx.AsyncClient(app=chat_app, base_url="http://t") as c2:
        r2 = await c2.post("/api/v1/chat", json=PAYLOAD)

    # Structural shape must match (NOT content):
    assert r1.status_code == r2.status_code
    assert r1.headers.get("content-type") == r2.headers.get("content-type")

    j1, j2 = r1.json(), r2.json()
    assert set(j1.keys()) == set(j2.keys()), "top-level envelope shape diverged"
    assert set(j1["data"].keys()) == set(j2["data"].keys()), "data shape diverged"
    assert "messages" in j1["data"] and "stop_reason" in j1["data"]
    assert "request_id" in j1["meta"] and "request_id" in j2["meta"]

    # Role progression must match — every response must have at least the original
    # user message + one assistant turn (final answer). Tool turns are optional.
    for j in (j1, j2):
        roles = [m["role"] for m in j["data"]["messages"]]
        assert roles[0] == "user"
        assert "assistant" in roles
        assert all(r in ("user", "assistant", "tool") for r in roles)

    # request_id must differ — uuids are per-request
    assert j1["meta"]["request_id"] != j2["meta"]["request_id"]
```

**Why structural-shape rather than content:** Two LLM calls with identical input produce different output (temperature 0.1, model sampling). Asserting content equality is a flaky test waiting to happen. Asserting **shape** equality (keys, types, role taxonomy) is what byte-identical *behavior* actually means.

**Stub LLM router for deterministic test:** Inject a fake `LLMRouter` whose `complete_with_tools` returns a scripted result. This is FB-C plan 15-08's `_StubAdapter` pattern (`tests/llm/test_complete_with_tools.py`). The stub gives both clients identical content; structural-shape assertion is then redundant but satisfies CHAT-05's stricter interpretation.

**Recommendation:** Ship both — the structural-shape test against a real LLM (env-gated `FB_INTEGRATION_TESTS=1`) AND a content-equality test against a stub router (default suite). The shape test verifies real parity; the content test verifies the handler doesn't accidentally re-shape based on caller (header sniffing, etc.).

---

## Logging Shape (D-21 resolution)

**Existing state:** `logging_config.py` configures uvicorn output to stderr only. The library `logger = logging.getLogger(__name__)` is used by every handler with the format `<handler_name> failed: <exc_type>` for warnings.

**D-21 fields recap:** `request_id`, `client_ip`, `message_count_in`, `message_count_out`, `tool_call_count`, `stop_reason`, `wall_clock_ms`.

**Most useful fields for artist-UAT debrief (CHAT-04):**

| Field | Why useful | Source |
|-------|-----------|--------|
| `request_id` | Correlates UI bug report → server logs → FB-C per-session log | uuid generated in handler |
| `tool_call_count` | "Did the LLM actually use tools to answer?" — distinguishes useful from generic answer | Sum of tool turns in response |
| `wall_clock_ms` | "Did it satisfy <60s?" CHAT-04 gate evidence | `time.monotonic()` delta |
| `stop_reason` | "Did it terminate naturally or hit a cap?" | `end_turn` / `max_iterations` / `max_seconds_exceeded` |

**Recommendation — match FB-C session log format exactly:**

```python
# FB-C session log (verified router.py:604-612)
# tool-call session complete iter=4 elapsed_s=18.3 prompt_tokens_total=1882 ...

# FB-D analog (recommended)
logger.info(
    "chat-request request_id=%s client_ip=%s message_count_in=%d "
    "message_count_out=%d tool_call_count=%d stop_reason=%s wall_clock_ms=%d",
    request_id, client_ip, len(body.messages), len(response_messages),
    tool_call_count, stop_reason, wall_clock_ms,
)
```

**Cross-correlation:** FB-C emits `request_id` is NOT in FB-C's session log today. Two options:
1. Pass `request_id` into `complete_with_tools()` as an optional kwarg, FB-C threads it into its session log. (Tiny FB-C extension.)
2. Wrap each chat call in `extra={"request_id": ...}` via `LoggerAdapter` and rely on log aggregation to correlate. (Zero FB-C change.)

**Recommendation:** Option 2 for v1.4. Operationally, `request_id` searches the chat-request line, then the timestamp window queries the FB-C session log line. One log aggregation query, no FB-C surface change.

---

## Web UI Chat Panel UX (D-06..D-11 implementation notes)

**Template structure (panel.html outline):**

```html
{% extends "shell.html" %}
{% block title %}Chat — Forge Console{% endblock %}

{% block view %}
<section class="card chat-panel" x-data="chatPanel()" x-init="init()">
  <div class="chat-history" x-ref="history">
    <template x-for="(msg, i) in messages" :key="i">
      <div :class="`chat-msg chat-msg--${msg.role}`">
        <!-- role label (artist-friendly) -->
        <div class="chat-msg__role" x-text="roleLabel(msg.role)"></div>

        <!-- assistant + user content rendered via vanilla markdown -->
        <template x-if="msg.role !== 'tool'">
          <div class="chat-msg__content" x-html="renderMarkdown(msg.content)"></div>
        </template>

        <!-- tool turn collapsed by default (D-07) -->
        <template x-if="msg.role === 'tool'">
          <details class="tool-trace">
            <summary x-text="toolSummary(msg)"></summary>
            <div class="tool-trace__args" x-text="msg.args_preview"></div>
            <div class="tool-trace__result" x-text="msg.content.slice(0, 500)"></div>
            <button x-show="msg.content.length > 500"
                    @click="msg._expanded = !msg._expanded">
              <span x-text="msg._expanded ? 'Collapse' : 'Show full result'"></span>
            </button>
            <div x-show="msg._expanded" class="tool-trace__full"
                 x-text="msg.content"></div>
          </details>
        </template>
      </div>
    </template>

    <!-- in-flight spinner (D-08) -->
    <div x-show="loading" class="chat-spinner" aria-label="Generating response"></div>

    <!-- error banners (D-09) -->
    <div x-show="lastError" class="chat-banner" :class="`chat-banner--${lastError.code}`"
         x-text="lastError.message"></div>
  </div>

  <form class="chat-input-form" @submit.prevent="send()">
    <textarea x-model="draftText"
              x-ref="input"
              @keydown.enter.prevent="onEnter($event)"
              rows="1"
              placeholder="Ask a question about your project..."></textarea>
    <button type="submit" :disabled="loading || !draftText.trim()">Send</button>
  </form>
</section>

<script src="/ui/static/chat-markdown.js"></script>
<script>
  function chatPanel() {
    return {
      messages: [],
      draftText: '',
      loading: false,
      lastError: null,

      init() { this.$refs.input.focus(); },

      onEnter(e) {
        if (e.shiftKey) {
          // Insert newline (textarea grows)
          this.draftText += '\n';
        } else {
          this.send();
        }
      },

      async send() {
        if (!this.draftText.trim() || this.loading) return;
        const userMsg = { role: 'user', content: this.draftText.trim() };
        this.messages.push(userMsg);
        this.draftText = '';
        this.lastError = null;
        this.loading = true;
        try {
          const res = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: this.messages }),
          });
          if (!res.ok) {
            const err = await res.json();
            this.lastError = {
              code: err.error?.code || res.status,
              message: this.errorBannerCopy(res.status, err.error),
            };
            return;
          }
          const body = await res.json();
          // D-03 echoes full history; replace in-place
          this.messages = body.data.messages;
          // Auto-scroll
          await this.$nextTick();
          this.$refs.history.scrollTop = this.$refs.history.scrollHeight;
        } catch (e) {
          this.lastError = { code: 'network', message: 'Network error — check console.' };
        } finally {
          this.loading = false;
          this.$refs.input.focus();
        }
      },

      errorBannerCopy(status, err) {
        // D-09 prescribed copy
        if (status === 429) {
          const retry = err?.retry_after || '60';
          return `Rate limit reached — wait ${retry}s before retrying.`;
        }
        if (status === 504) return 'Response timed out — try a simpler question or fewer tools.';
        if (status === 422) return `Invalid request — ${err?.message || 'check inputs'}.`;
        return 'Chat error — check console for details.';
      },

      renderMarkdown(text) { return window.renderMarkdown(text); },
      roleLabel(role) {
        return { user: 'You', assistant: 'Forge Assistant', tool: 'Tool' }[role] || role;
      },
      toolSummary(msg) {
        return `${msg.tool_name || 'tool'}(${(msg.args_preview || '').slice(0, 80)})`;
      },
    };
  }
</script>
{% endblock %}
```

**CSS additions (forge-console.css extensions, ~30 LOC):**

```css
.chat-panel { max-width: 800px; margin: 32px auto; }
.chat-history { min-height: 300px; max-height: 60vh; overflow-y: auto; padding: 16px; background: var(--color-surface-deep); border: 1px solid var(--color-border); border-radius: 4px; margin-bottom: 16px; }
.chat-msg { padding: 8px 16px; margin-bottom: 8px; border-radius: 4px; }
.chat-msg--user { background: var(--color-surface); border-left: 2px solid var(--color-accent); }
.chat-msg--assistant { background: transparent; border-left: 2px solid var(--color-status-ok); }
.chat-msg--tool { background: rgba(102,78,0,0.1); font-family: var(--font-mono); font-size: 12px; }
.chat-msg__role { font-size: 12px; font-weight: 600; color: var(--color-text-muted); margin-bottom: 4px; }
.chat-msg pre.code-block { background: var(--color-surface-deep); padding: 8px; overflow-x: auto; }
.tool-trace summary { cursor: pointer; color: var(--color-text-muted); padding: 4px 0; }
.tool-trace summary:hover { color: var(--color-text); }
.chat-spinner { display: block; width: 24px; height: 24px; border: 2px solid var(--color-border); border-top-color: var(--color-accent); border-radius: 50%; animation: chat-spin 0.8s linear infinite; margin: 16px auto; }
@keyframes chat-spin { to { transform: rotate(360deg); } }
.chat-banner { padding: 12px 16px; border-radius: 4px; margin: 8px 0; }
.chat-banner--429, .chat-banner--rate_limit_exceeded { background: var(--color-accent-muted); border: 1px solid var(--color-accent); color: var(--color-text); }
.chat-banner--504, .chat-banner--request_timeout { background: var(--color-accent-muted); border: 1px solid var(--color-accent); color: var(--color-text); }
.chat-banner--500, .chat-banner--internal_error, .chat-banner--network { background: rgba(102,0,0,0.2); border: 1px solid var(--color-status-error); color: var(--color-text); }
.chat-input-form { display: flex; gap: 8px; }
.chat-input-form textarea { flex: 1; min-height: 32px; max-height: 150px; padding: 8px; background: #3a3f4f; border: 1px solid var(--color-border-md); color: var(--color-text); font-family: var(--font-sans); resize: none; }
.chat-input-form textarea:focus { outline: none; border-color: var(--color-accent); }
.chat-input-form button { padding: 8px 24px; min-height: 32px; background: var(--color-accent-muted); border: 1px solid var(--color-accent); color: var(--color-text-bright); cursor: pointer; }
.chat-input-form button:disabled { opacity: 0.5; cursor: not-allowed; }
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio (asyncio_mode=auto) |
| Config file | `pyproject.toml:71-77` (no separate pytest.ini) |
| Quick run command | `pytest tests/console/test_chat_handler.py -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | 11 req/min IP → 429 | unit | `pytest tests/console/test_rate_limit.py` | ❌ Wave 0 |
| CHAT-01 | 429 envelope shape | unit | `pytest tests/console/test_chat_handler.py::test_chat_429_envelope -x` | ❌ Wave 0 |
| CHAT-02 | 125s timeout | integration (stub LLM blocks) | `pytest tests/console/test_chat_handler.py::test_chat_timeout` | ❌ Wave 0 |
| CHAT-03 | Sanitization E2E | integration (poisoned tool) | `pytest tests/console/test_chat_handler.py::test_chat_sanitization` | ❌ Wave 0 |
| CHAT-04 | Artist UAT <60s | manual (D-36 fresh-operator gate) | Manual on assist-01; record in `16-HUMAN-UAT.md` | N/A |
| CHAT-05 | Browser + Flame-hooks parity | integration (two httpx clients) | `pytest tests/console/test_chat_parity.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/console/test_chat_handler.py tests/console/test_rate_limit.py -x`
- **Per wave merge:** `pytest tests/`
- **Phase gate:** Full suite green + `16-HUMAN-UAT.md` PASS before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/console/test_rate_limit.py` — covers CHAT-01 token-bucket logic
- [ ] `tests/console/test_chat_handler.py` — covers CHAT-01..03 handler behavior with stub LLMRouter
- [ ] `tests/console/test_chat_parity.py` — covers CHAT-05 dual-client structural shape
- [ ] Stub LLMRouter fixture in `tests/console/conftest.py` (or reuse FB-C `_StubAdapter` pattern)
- [ ] `tests/integration/test_chat_live.py` — env-gated `FB_INTEGRATION_TESTS=1` — covers CHAT-04 against real Ollama

---

## Security Domain

`security_enforcement` is enabled (default).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (deferred — SEED-AUTH-V1.5) | — |
| V3 Session Management | no (no server-side sessions in v1.4) | — |
| V4 Access Control | no (single-bridge, localhost-bound, no per-user authz) | — |
| V5 Input Validation | yes | Pydantic 2 `BaseModel.model_validate()` on request body; FB-C `_sanitize_tool_result()` on tool results; Phase 7 `_sanitize_tag()` on tool defs |
| V6 Cryptography | no (no new crypto in chat surface) | — |
| V11 Business Logic | yes | Token-bucket rate limit (CHAT-01); recursive-synthesis guard inherited from FB-C |
| V13 API & Web Service | yes | CORS allow-list locked to localhost (`app.py:52`); structured `_envelope`/`_error` responses; no traceback leakage |
| V14 Configuration | yes | Bind to 127.0.0.1 only (existing v1.3 lock D-28); no `0.0.0.0` exposure |

### Known Threat Patterns for Starlette + LLM chat surface

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via tool result | Tampering | FB-C `_sanitize_tool_result()` already enforced (verified `router.py:509`); CHAT-03 verifies E2E |
| Prompt injection via user input | Tampering | NOT mitigated by design (D-15 — user input is untrusted by LLM design; sanitizing breaks UX) |
| DoS via expensive LLM calls | DoS | IP token bucket (CHAT-01) — 10 calls/min; FB-C 120s wall-clock per call |
| DoS via huge request body | DoS | Pydantic `max_length` constraint on each message content; recommend 32KB per message |
| Recursive LLM synthesis | EoP | FB-C `_in_tool_loop` ContextVar already enforced (verified `router.py:149`); CHAT-03's poisoned-tool test exercises the path |
| Reverse tabnabbing in markdown links | Tampering | `target="_blank" rel="noopener noreferrer"` on all rendered links (§6) |
| HTML/script injection in chat content | Tampering | HTML-escape before any tag substitution in `renderMarkdown()`; whitelist `http://`/`https://` schemes |
| Reverse-proxy IP spoofing | Spoofing | NOT mitigated — `request.client.host` is the connection peer, not an X-Forwarded-For. v1.4 binds to localhost only (no reverse proxy). Document and defer. |
| Cookie/session theft | InfoDisclosure | N/A — no cookies, no sessions in v1.4 |

### Recommended Pydantic constraints for body (input validation)

```python
class _ChatMessage(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str = Field(max_length=32768)  # 32KB per message — generous; tools cap at 8KB
    tool_call_id: str | None = Field(default=None, max_length=128)

class _ChatRequestBody(BaseModel):
    messages: list[_ChatMessage] = Field(min_length=1, max_length=64)  # 64-turn cap
    max_iterations: int = Field(default=8, ge=1, le=32)
    max_seconds: float = Field(default=120.0, gt=0, le=300.0)
    tool_result_max_bytes: int = Field(default=8192, ge=512, le=131072)
```

`max_length=64` on `messages` is a soft cap (artist sessions rarely exceed 20 turns; 64 is generous safety). `max_length=32768` on content prevents megabyte-payload DoS.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FastAPI + slowapi for rate limit | Starlette + in-process dict | N/A — we never had FastAPI | We're already on Starlette; in-process dict is the smallest viable surface for one route |
| Server-rendered chat (HTMX swaps) | Client-rendered chat (Alpine.js + fetch) | This phase | Per-tab JS state for D-06; HTMX would need a server-side store |
| `request.json()` ad-hoc parse | Pydantic 2 `model_validate()` | This phase | Already in deps; preserves 30+ lines of manual validation |
| Hand-rolled markdown render | Vanilla 50-LOC renderer | This phase | No new dep; cuts XSS surface vs full GFM library |

**Deprecated/outdated:**
- Pydantic 1 `parse_obj()` — use `model_validate()` (Pydantic 2.x — already in tree).
- `slowapi` — FastAPI-only; we're on Starlette.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `mcp.list_tools()` returns the registered tool list (already-built schemas) suitable to pass directly to `complete_with_tools(tools=...)` | Architecture Pattern 4 | If shape diverges from `complete_with_tools` expectations, FB-C raises `ValueError` — would surface as a 500 in tests immediately, not a silent bug |
| A2 | Pydantic 2 is the version in the current dep tree (via `mcp[cli]>=1.19,<2`) | Stack | If Pydantic 1 is somehow shadowed, `model_validate()` raises `AttributeError` — low risk; verified by checking `mcp` package metadata |
| A3 | `qwen2.5-coder:32b` on assist-01 produces a useful answer to "what synthesis tools were created this week?" in <60s | Pitfall 4 | If false, CHAT-04 fails at UAT and triggers remediation phase analogous to Phase 10.1 — the planner should flag this for early empirical check |
| A4 | The `complete_with_tools()` `prompt: str` signature does NOT accept a multi-turn message history natively | Pitfall 3 | Verified directly in `router.py:252-264` — claim is HIGH confidence |
| A5 | Phase 10 ships zero markdown rendering (no client-side, no server-side) | Pitfall (markdown §6) | Verified by reading `templates/execs/detail.html:23` + grep — claim is HIGH confidence |
| A6 | Single-bridge-process per machine (no multi-instance) for v1.4 | Stack: in-memory rate limit | Verified in STATE.md and CONTEXT.md — claim is HIGH confidence |
| A7 | The `request.client` Starlette pitfall fires for `httpx.AsyncClient(app=...)` test client | Pitfall 1 | `[CITED: github.com/kludex/starlette docs/requests.md]`; testable empirically |

**Items needing user confirmation before plan execution:**

- **A3 (model speed):** Recommend running a smoke test on assist-01 (`router.local_model = "qwen2.5-coder:32b"` + simple chat) to record baseline latency BEFORE the artist UAT. If it's 80-100s, the planner should consider including the `qwen3:32b` model bump as part of FB-D rather than deferring to v1.4.x.
- **Pitfall 2/3 resolutions (FB-C surface extension):** The two recommended FB-C extensions (`return_history` kwarg or `messages` kwarg) are non-breaking but DO modify the FB-C public API. The planner should flag whether to (a) include a small FB-C extension plan as the first wave of FB-D, or (b) accept Pattern A (system-prompt stitching) and the 504-on-max-iterations simplification.

---

## Open Questions (RESOLVED — see 16-CONTEXT.md `<open_questions>` for verdicts)

All four open questions raised in this section were resolved 2026-04-27 via the orchestrator's recommendation pass and folded into 16-CONTEXT.md as D-02a, D-03 cap-fire posture, D-14a, and the smoke-test deferral. The questions below are preserved for historical context — DO NOT re-open during planning.

1. **`stop_reason: "max_iterations"` per D-03 — how to honor when FB-C drops partial state?**
   - What we know: FB-C raises `LLMLoopBudgetExceeded(reason="max_iterations")` and returns no partial messages.
   - What's unclear: D-03 says return 200 + `stop_reason="max_iterations"` + the messages array. We don't have the messages.
   - Recommendation: Add a small FB-C extension plan in FB-D's first wave: `complete_with_tools(..., return_history: bool = False)` returning `tuple[str, list[dict]]` when True. ~20 LOC, fully backward-compatible. OR — drop D-03's `max_iterations` distinct stop_reason and treat as 504. Discuss-phase already locked D-03; planner should clarify.

2. **`prompt: str` vs `messages: [...]` mismatch — Pattern A or Pattern B?**
   - What we know: D-02 carries multi-turn `messages`; FB-C takes single `prompt`.
   - What's unclear: Which translation strategy the planner should use.
   - Recommendation: Pattern A (system-prompt stitching) for v1.4 — least invasive, fully sufficient for D-12 artist UAT use case. Plant `SEED-CHAT-MULTITURN-NATIVE-V1.4.x.md` for Pattern B once real multi-turn use emerges.

3. **Model bump (`qwen2.5-coder:32b` → `qwen3:32b`) — in-scope or v1.4.x?**
   - What we know: SEED was planted in FB-C for the bump. CHAT-04 latency budget is <60s.
   - What's unclear: Whether `qwen2.5-coder:32b` actually meets <60s on assist-01.
   - Recommendation: Run the smoke test described in A3 above. If <60s, defer to v1.4.x. If 60-100s, include the bump in FB-D as a separate plan (pre-UAT). If >100s, this is a CHAT-04 blocker — escalate.

4. **`LLMLoopBudgetExceeded("max_iterations")` is the FB-C signal for "loop hit cap" — but if FB-C's outer wait_for fires (max_seconds), it raises `LLMLoopBudgetExceeded("max_seconds")`. The chat handler's outer 125s `wait_for` raises bare `asyncio.TimeoutError`. Three possible code paths to translate to HTTP 504.**
   - Recommendation: Translate all three to HTTP 504 with the same envelope (`request_timeout`). The internal log line distinguishes via `stop_reason` field. Operationally, end users don't care which timer fired.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All | ✓ | (assumed local match) | — |
| Starlette | API surface | ✓ | (transitive via mcp) | — |
| Pydantic 2 | Body validation | ✓ | (transitive via mcp[cli]>=1.19) | — |
| ollama Python client | FB-C local path | ✓ | `>=0.6.1,<1` | — |
| Ollama daemon (assist-01) | CHAT-04 artist UAT | ✓ assumed (FB-C UAT pending) | `qwen2.5-coder:32b` | If down: chat returns 502 with FB-C `LLMToolError` mapping |
| anthropic SDK | NOT used by chat (D-05 hardcodes sensitive=True) | ✓ pinned | `>=0.97,<1` | N/A — only used if D-05 ever flips |

**Missing dependencies with no fallback:** None — all dependencies are already installed for v1.3+.

**Missing dependencies with fallback:** None.

---

## Sources

### Primary (HIGH confidence — verified in checked-in code)
- `forge_bridge/console/handlers.py:53-60` — `_envelope`/`_error` envelope helpers (Phase 9 pattern, FB-B-extended)
- `forge_bridge/console/handlers.py:118-142` — `_resolve_actor` priority pattern (FB-B precedent for D-06 actor patterns; analogous for chat)
- `forge_bridge/console/app.py:71-99` — Starlette Route registration pattern; FB-D adds one Route here
- `forge_bridge/console/app.py:100-108` — `CORSMiddleware` allow-list (already covers POST + localhost — no extension needed)
- `forge_bridge/console/read_api.py:84-102` — `_llm_router` injection pattern (D-16 reuses this)
- `forge_bridge/console/static/forge-console.css:1-69` — LOGIK-PROJEKT amber palette + spinner-able `--color-accent`
- `forge_bridge/console/templates/shell.html:12` — chat nav link already present and pointing to `/ui/chat`
- `forge_bridge/console/templates/chat/stub.html` — stub to replace per D-20
- `forge_bridge/console/templates/execs/detail.html:23` — verifies Phase 10 ships no markdown renderer
- `forge_bridge/console/logging_config.py` — uvicorn → stderr; standard Python `logging` for handler logs
- `forge_bridge/llm/router.py:75-130` — public exception classes (`LLMLoopBudgetExceeded`, `RecursiveToolLoopError`, `LLMToolError`)
- `forge_bridge/llm/router.py:252-318` — `complete_with_tools()` full signature (verifies prompt: str + return type str)
- `forge_bridge/llm/router.py:580-602` — inner `asyncio.wait_for` confirming nested-timeout pattern (Pitfall 2)
- `forge_bridge/mcp/registry.py:177-245` — `invoke_tool` and `mcp.list_tools()` pattern
- `pyproject.toml:12-32` — current dep set; no new deps allowed for FB-D

### Secondary (MEDIUM confidence — verified via Context7/WebFetch)
- `[CITED: github.com/kludex/starlette/blob/main/docs/requests.md]` — `if request.client:` defensive pattern
- `[CITED: oneuptime.com/blog/post/2026-01-22-token-bucket-rate-limiting-python]` — minimal token-bucket pattern (lazy refill, dict, TTL eviction)
- `[CITED: docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel.model_validate]` — Pydantic 2 method (NOT `parse_obj`)
- `.planning/research/FB-C-TOOL-CALL-LOOP.md §2.3, §3.3` — Anthropic vs Ollama messages-shape divergence
- `.planning/phases/15-fb-c-llmrouter-tool-call-loop/15-CONTEXT.md` — D-12..D-21 FB-C decisions FB-D consumes
- `.planning/phases/14-fb-b-staged-ops-mcp-tools-read-api/14-CONTEXT.md` — D-01..D-09 envelope/handler patterns FB-D mirrors
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-CONTEXT.md` — bookkeeper invariant (chat does not execute mutations)

### Tertiary (LOW confidence — flagged for empirical validation)
- A3: `qwen2.5-coder:32b` <60s for the artist UAT prompt — needs assist-01 smoke test before UAT.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep already in tree; verified in pyproject.toml.
- Architecture: HIGH — every pattern reuses an existing checked-in surface.
- Pitfalls 1, 4, 5: HIGH — verified in source.
- Pitfall 2 (nested wait_for + max_iterations partial state): HIGH on the gap; recommendation needs planner sign-off (D-03 contract is at risk).
- Pitfall 3 (prompt vs messages): HIGH on the gap; Pattern A recommendation is MEDIUM (works, but stitching is slightly lossy).
- Markdown § recommendation: HIGH on the security properties; MEDIUM on whether 50 LOC is "enough" for the artist UAT visual quality.
- Logging shape: HIGH — matches FB-C precedent verbatim.

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days; codebase is moving but FB-D surfaces are well-defined)
