---
phase: 16-fb-d-chat-endpoint
reviewed: 2026-04-27T12:30:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - forge_bridge/console/_rate_limit.py
  - forge_bridge/console/app.py
  - forge_bridge/console/handlers.py
  - forge_bridge/console/static/forge-chat.js
  - forge_bridge/console/static/forge-console.css
  - forge_bridge/console/templates/chat/panel.html
  - forge_bridge/console/ui_handlers.py
  - forge_bridge/llm/_adapters.py
  - forge_bridge/llm/router.py
  - tests/console/test_chat_handler.py
  - tests/console/test_rate_limit.py
  - tests/integration/test_chat_endpoint.py
  - tests/integration/test_chat_parity.py
  - tests/llm/conftest.py
  - tests/llm/test_complete_with_tools.py
  - tests/test_ui_wheel_package.py
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 16 (FB-D): Code Review Report

**Reviewed:** 2026-04-27T12:30:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Phase 16 (FB-D) implements `POST /api/v1/chat` with IP-keyed token-bucket rate
limiting, hardcoded `sensitive=True` LLM routing, an Alpine.js chat panel,
and integration tests covering CHAT-03 (sanitization E2E) + CHAT-05 (FB-C
parity). The implementation follows the documented decision register
(D-01..D-21) closely, the FB-B nested-error-envelope contract is preserved,
and the D-14a exception-translation matrix is enforced with `type(exc).__name__`
as the only logged exception text — no traceback strings leak through 500
responses.

**No critical issues found.** The XSS surface in `forge-chat.js` is correctly
guarded by escape-first ordering. Jinja2 auto-escape is on by default in
Starlette's `Jinja2Templates`, and the only `x-html` directive in
`templates/chat/panel.html` flows through the same escape-first renderer.
The rate limiter holds `threading.Lock` across read-modify-write, which is
correct for sync handlers but worth a note (WR-04) given the handler is
`async def`.

The strongest concerns are operational hardening rather than correctness:
no body-size cap (WR-01), no message-list length cap (WR-02), and the
rate limiter's `threading.Lock` isn't strictly compatible with the
single-threaded `async def` model under heavy concurrency (WR-04, but in
practice fine on a single-process bridge per STATE.md).

The test surface is disciplined: every test has assertions, mocks are
narrow (router.complete_with_tools + mcp.list_tools only), and rate-limit
state is reset both pre- and post-test via an autouse fixture. CHAT-03
Strategy A asserts the canonical `INJECTION_MARKERS` tuple includes
`'ignore previous'` (single-source-of-truth pin), and CHAT-05 reduces
responses to a structural signature so live-LLM variance does not flake
the test.

---

## Warnings

### WR-01: No request body-size cap before `await request.json()`

**File:** `forge_bridge/console/handlers.py:434-435`
**Issue:** The chat handler calls `await request.json()` without first
consulting `Content-Length` or capping the body. A client (or stale
stub on the same loopback after the v1.5 auth landing) can POST an
arbitrarily large JSON document (e.g., 50 MB of `messages[].content`).
Starlette buffers the entire body into memory before `.json()` parses
it. Even though the bridge binds to 127.0.0.1 (D-28), a single rogue
local process can OOM the bridge with one request.

**Fix:** Reject when `Content-Length` exceeds a documented cap before
reading the body. Pick a number that exceeds the realistic ceiling
(8192-byte tool results × 32 max iterations ≈ 256 KB; double it for
safety):
```python
_MAX_CHAT_BODY_BYTES = 524_288  # 512 KB

content_length = request.headers.get("content-length")
if content_length is not None:
    try:
        if int(content_length) > _MAX_CHAT_BODY_BYTES:
            return _chat_error(
                "request_too_large",
                f"chat body exceeds {_MAX_CHAT_BODY_BYTES} bytes",
                413, request_id,
            )
    except ValueError:
        pass  # malformed Content-Length — fall through, .json() will reject
```

---

### WR-02: No upper bound on `len(messages)` or per-message content length

**File:** `forge_bridge/console/handlers.py:450-483`
**Issue:** `messages` validation ensures it is a non-empty `list[dict]` and
each entry has a valid role + string `content`, but does not bound the
list length or the per-message content size. A 100,000-element messages
list passes validation, then is forwarded to the LLM router, where the
adapter sends it to Anthropic / Ollama as one giant payload (likely
provider-rejected, but only after CPU is spent on `_compile_tools` and
any system-prompt prepend). This is a request amplification / prompt-bomb
surface.

**Fix:** Add explicit caps mirroring the loop budget:
```python
_MAX_CHAT_MESSAGES = 64       # generous: 32 iter × ~2 messages/iter
_MAX_MESSAGE_CONTENT = 32_768  # 32 KB per message — fits Claude tool blocks

if len(messages) > _MAX_CHAT_MESSAGES:
    return _chat_error("validation_error",
        f"messages list exceeds {_MAX_CHAT_MESSAGES} entries",
        422, request_id)

# inside the per-message loop:
if len(msg["content"]) > _MAX_MESSAGE_CONTENT:
    return _chat_error("validation_error",
        f"messages[{i}].content exceeds {_MAX_MESSAGE_CONTENT} bytes",
        422, request_id)
```

---

### WR-03: `_chat_error` accepts a kwarg that the test does NOT cover for `extra_headers`

**File:** `forge_bridge/console/handlers.py:359-380`
**Issue:** `_chat_error(...)` accepts an optional `extra_headers` dict, but
the only call site that passes one is the 429 path (line 429) with
`Retry-After`. There is no test that asserts a non-rate-limit error path
reuses `extra_headers` correctly. The `headers.update(extra_headers)`
call has a subtle risk: if a future caller passes
`{"X-Request-ID": "spoofed"}`, the fixed `X-Request-ID` set on line 373
gets clobbered, and the response carries the spoofed request id. Low
probability now (only one in-tree caller), but the construction order
("set fixed, then update with caller dict") is the wrong precedence for
a security-relevant header.

**Fix:** Apply `extra_headers` first, then overwrite with the trusted
`X-Request-ID`:
```python
headers = dict(extra_headers) if extra_headers else {}
headers["X-Request-ID"] = request_id  # always wins
```

---

### WR-04: `_rate_limit` uses `threading.Lock` from inside `async def` handler

**File:** `forge_bridge/console/_rate_limit.py:38, 75`
**Issue:** `check_rate_limit()` is called from the async `chat_handler`
on the event loop thread. It uses `threading.Lock` and holds it during
`time.monotonic()` + dict mutation. On a single-thread asyncio loop,
this works correctly because the critical section is non-blocking
(no `await`). Documented intent (line 11-12) is single-process v1.4;
that is fine.

The risk is that if a future maintainer adds an `await` inside the
critical section (e.g., to log to an async sink or query a DB),
`threading.Lock` becomes a deadlock pothole — asyncio will not yield,
but the lock will not detect the re-entrance from the same task. A
brief comment plus a runtime assert would prevent the regression.

**Fix:** Add a header-comment warning and a defensive comment around
the `with _lock:` block:
```python
# CRITICAL: this critical section MUST remain synchronous (no await).
# threading.Lock + asyncio mixing is safe ONLY when the section is
# CPU-bound. If you need an async operation here, switch to asyncio.Lock
# AND ensure the rate-limit module is imported lazily inside the async
# context.
with _lock:
    ...
```

Optional defensive measure: assert the lock is held for less than ~1ms
in development builds (env-gated) to catch accidental long sections.

---

### WR-05: TTL eviction sweep is O(N) on every call — ip-spoofed DOS surface

**File:** `forge_bridge/console/_rate_limit.py:78-80`
**Issue:** `check_rate_limit` iterates `_buckets.items()` on every call
to evict stale entries. For a localhost-only v1.4 bridge this is a
non-issue; bucket count ≤ small. But if a future v1.5 deployment opens
the bridge to LAN traffic and the IP key is still `request.client.host`
(no auth migration yet), an attacker who can spoof / churn source IPs
can grow `_buckets` to millions of entries while every other request
pays O(N) work inside the lock. The TTL=300s is generous enough that
sustained spoofing churn keeps the dict large.

**Fix:** Either
- bound `len(_buckets)` (e.g., 10 000) and reject new IPs when full
  with a 503 (caller documented to retry), or
- amortize sweeping (e.g., sweep at most K stale entries per call,
  or sweep on a wallclock interval gate).

This is a v1.5 hardening item — adding a `# TODO(SEED-AUTH-V1.5): cap
_buckets size when IP-keying is replaced by caller_id` comment is
sufficient for now since the migration path already replaces the key.

---

## Info

### IN-01: Markdown renderer interaction order can produce nested-tag artifacts

**File:** `forge_bridge/console/static/forge-chat.js:23-60`
**Issue:** The renderer applies fenced-code → inline-code → bold → links →
newlines in sequence, but does not stash matched regions between passes.
Inputs like `**bold with \`code\`**` produce
`<strong>bold with <code class="chat-inline-code">code</code></strong>`
which is fine, but `\`code with **bold**\`` produces
`<code class="chat-inline-code">code with <strong>bold</strong></code>`
— the inline-code body is supposed to be monospace verbatim. Cosmetic,
not a security issue (escape-first guarantees no XSS), but worth noting
as a known v1 limitation.

**Fix:** Defer if you ship a real markdown lib later (D-11 explicitly
chose escape-first to avoid the dep). A lightweight mitigation is to
process inline code FIRST and substitute the matched body with a
placeholder, then re-substitute at the end. v1.4 is fine to ship as-is
given the artist-facing context.

---

### IN-02: `tool_call_id` field is plumbed through but never asserted in chat tests

**File:** `forge_bridge/console/handlers.py:357, 626` and
`forge_bridge/console/static/forge-chat.js:124-128, 158-163`
**Issue:** The wire shape supports `tool_call_id` per D-02
(`{role, content, tool_call_id?}`), and the JS strips/restores it
through fetch. But no chat-handler unit test asserts a request
containing a `tool_call_id` is forwarded to the router unchanged, and
no test asserts the JS round-trip preserves the field through history.
The contract is documented but not pinned by a test.

**Fix:** Extend `test_chat_passes_messages_list_to_router` to include a
tool-role message with `tool_call_id` and assert it round-trips. Low
priority — the live path is exercised by the FB-C integration tests
through `complete_with_tools`.

---

### IN-03: `_envelope_json` (line 74-81) is unused for chat path — minor dead-link risk

**File:** `forge_bridge/console/handlers.py:74-81`
**Issue:** `_envelope_json` is defined for D-26 byte-identity between
HTTP and MCP resource paths. The chat handler returns its own
`JSONResponse` directly (line 633) bypassing both `_envelope` and
`_envelope_json`, which is consistent with the D-03 chat-specific
envelope shape `{messages, stop_reason, request_id}`. No bug, just
worth noting that future MCP-resource parallels for the chat endpoint
must NOT use `_envelope_json` (the FB-B envelope) — they need a
chat-specific equivalent.

**Fix:** Add a one-line docstring comment in `_envelope_json` clarifying
it is for the FB-B `{data, meta}` shape only and should not be used by
future chat MCP-resource shims:
```python
def _envelope_json(data, **meta) -> str:
    """SAME serialization as _envelope — for MCP resource / tool shim use.
    NOTE: D-03 chat envelope is DIFFERENT — chat MCP shims must build
    {messages, stop_reason, request_id} directly, not via this helper."""
```

---

### IN-04: `from forge_bridge.mcp import server as _mcp_server` happens INSIDE the async hot path

**File:** `forge_bridge/console/handlers.py:524`
**Issue:** The MCP server module is imported lazily inside `chat_handler`
on every call. Python caches `sys.modules` so this is amortized to a
dict lookup, but the `from … import …` rebind is O(1) and the import
machinery acquires `_imp_lock` briefly. For a 10-rps endpoint this is
noise. For a future high-concurrency replay (e.g., projekt-forge batch
chat fan-out), moving the import to module-load would shave a few
microseconds per call.

**Fix:** Move to module top:
```python
from forge_bridge.mcp import server as _mcp_server
```
Defer if `_mcp_server` has its own load-time side effects that the
console module wants to delay. Looks safe to hoist.

---

### IN-05: Test `test_per_tool_sub_budget_caps_at_30s` only loosely asserts the contract

**File:** `tests/llm/test_complete_with_tools.py:253-285`
**Issue:** The test's docstring says "30s ceiling caps the per-tool
wait_for", but the test runs with `max_seconds=1.0` which capping per
the formula `max(1.0, min(30.0, remaining))` → 1.0, NOT the 30s
ceiling. The actual 30s-ceiling case is unverified. The conditional
`if adapter.appended_results:` even allows zero assertions to pass.

**Fix:** Either rename the test to reflect what it actually exercises
(`test_per_tool_sub_budget_falls_back_to_floor_when_remaining_low`),
or add a second test that pins the 30s ceiling using a MagicMock on
`time.monotonic` to control the elapsed clock. Optional v1.5 cleanup
— the current test does protect against regressions in the floor case.

---

### IN-06: Integration test class missing `pytest.mark.asyncio` (relies on auto-mode)

**File:** `tests/integration/test_chat_endpoint.py:124`,
`tests/integration/test_chat_parity.py:119`
**Issue:** The `TestChatSanitizationE2E` and `TestChatParityStructural`
classes contain `async def test_…` methods without explicit
`@pytest.mark.asyncio` decorators. Tests will run only because
`pyproject.toml` sets `asyncio_mode = "auto"`. If a future maintainer
inadvertently flips that setting (or copies these tests into a
sub-package with a stricter `pyproject.toml`), the tests silently
become coroutines that never await — and pytest reports them as
"passed" without running.

**Fix:** Either add `@pytest.mark.asyncio` decorators to each async
test (most explicit), or add a class-level marker:
```python
@pytest.mark.asyncio
class TestChatSanitizationE2E:
    ...
```
Belt-and-suspenders against the auto-mode flip. No-op under the
current config; cheap insurance.

---

_Reviewed: 2026-04-27T12:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
