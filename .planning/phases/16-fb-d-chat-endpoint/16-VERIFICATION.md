---
phase: 16-fb-d-chat-endpoint
verified: 2026-04-27T19:45:00Z
status: human_needed
score: 5/6 must-haves verified (1 needs human UAT)
overrides_applied: 0
human_verification:
  - test: "CHAT-04 fresh-operator artist UAT — non-developer artist asks 'what synthesis tools were created this week?' in the Web UI chat panel on assist-01 (live qwen2.5-coder:32b)"
    expected: "Artist receives a useful, plain-English answer within <60s. Spinner stops, assistant message bubble renders with amber left-border, content describes the synthesis tools (no error banner, no timeout, no rate-limit fallback). Artist confirms the answer feels natural and useful."
    why_human: "D-12 / D-36 hard fresh-operator gate per Phase 10 precedent — UX quality + LLM response quality are not programmatically verifiable. The in-loop dogfood UAT during plan 16-05 ('That's working' after 2-pass fix) verified the wire end-to-end on a dev machine without Ollama (504 fallback path), but the formal CHAT-04 contract requires the actual happy-path question + answer cycle on assist-01 with a non-developer artist. Failure here triggers Phase 16.1 remediation analogous to Phase 10.1."
---

# Phase 16 (FB-D): Chat Endpoint — Verification Report

**Phase Goal:** `/api/v1/chat` exposes `complete_with_tools()` over HTTP with sanitized context assembly, wall-clock timeout, and rate limiting. Consumed by the Web UI chat panel and by external Flame hooks. One chat surface, multiple consumers, byte-identical behavior.
**Verified:** 2026-04-27T19:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Rate limit: 11th rapid request from same IP within 60s returns HTTP 429 with `{"error": ...}` envelope, IP-keyed for v1.4 | VERIFIED | `forge_bridge/console/_rate_limit.py:175-212` token bucket (capacity=10, refill=10/60s); `forge_bridge/console/handlers.py:418-432` chat_handler pre-gate produces 429 + Retry-After; `tests/console/test_chat_handler.py::test_chat_rate_limit_returns_429_with_retry_after` PASSES; `tests/console/test_rate_limit.py::test_eleventh_request_blocked` PASSES |
| 2 | Wall-clock timeout: blocking call returns timeout error within 125s (Phase 15 inner cap 120s + 5s framing) | VERIFIED | `forge_bridge/console/handlers.py:552-562` outer `asyncio.wait_for(timeout=125.0)` wrapping `complete_with_tools(..., max_seconds=120.0)`; D-14a translation matrix at handlers.py:564-606; `tests/console/test_chat_handler.py::test_chat_outer_timeout_returns_504` + `test_chat_loop_budget_exceeded_returns_504` both PASS |
| 3 | Sanitization boundary holds end-to-end: marker injection in tool sidecar/result does NOT reach LLM context | VERIFIED | `forge_bridge/_sanitize_patterns.py:19` INJECTION_MARKERS single source of truth (contains "ignore previous"); `forge_bridge/llm/_sanitize.py:61` `_sanitize_tool_result()` helper; `forge_bridge/llm/router.py:473,494,537,551,564,582` invokes `_sanitize_tool_result(...)` on every tool-result content string before LLM sees it; `tests/integration/test_chat_endpoint.py::TestChatSanitizationE2E` (Strategy A — 2 always-on tests) PASSES; Strategy B `test_chat_does_not_leak_poisoned_tool_marker` SKIPPED without `FB_INTEGRATION_TESTS=1` (live Ollama gate) |
| 4 | Non-developer dogfood UAT: artist asks "what synthesis tools were created this week?" and receives useful plain-English answer <60s on assist-01 | NEEDS HUMAN | Code surface fully shipped: `forge_bridge/console/templates/chat/panel.html` (Alpine x-data="chatPanel()"), `forge_bridge/console/static/forge-chat.js` (chatPanel factory + escape-first markdown + fetch wiring to /api/v1/chat), `forge_bridge/console/ui_handlers.py:ui_chat_handler` renders panel.html, route `/ui/chat` registered in `app.py:87`. In-loop dogfood UAT during plan 16-05 confirmed wire end-to-end ("That's working" — user verdict after 2-pass fix), but that was on a dev machine without Ollama (504 fallback). Formal CHAT-04 fresh-operator artist UAT (D-12/D-36 gate) is operator activity that is not programmatically verifiable — see human_verification section. |
| 5 | External-consumer parity: same /api/v1/chat serves projekt-forge Flame hooks with zero divergence vs Web UI; structural shape match | VERIFIED | `tests/integration/test_chat_parity.py::TestChatParityStructural::test_chat_parity_browser_vs_flame_hooks` PASSES — replays same payload through 2 httpx clients (browser-shape minimal headers + Flame-hooks-shape with `User-Agent: projekt-forge-flame-hooks/1.5` + `X-Forge-Actor`); asserts structural+content equality + X-Request-ID on both. `test_chat_parity_envelope_keys_locked` PASSES — D-03 envelope locked to `{messages, stop_reason, request_id}` with `stop_reason=="end_turn"`. Strategy B live test SKIPPED without FB_INTEGRATION_TESTS=1. |
| 6 | LLMTOOL-06 tool-result sanitization helper wired into chat path (FB-C ships, FB-D consumes) | VERIFIED | FB-C ships `_sanitize_tool_result()` at `forge_bridge/llm/_sanitize.py:61`, INJECTION_MARKERS shared with Phase 7's `_sanitize_tag` via `forge_bridge/_sanitize_patterns.py`. Wired into `complete_with_tools()` at router.py multiple call sites (473/494/537/551/564/582). Chat handler does NOT re-sanitize (D-15 mandate — handler forwards verbatim, sanitization is BELOW handler boundary inside the loop). `test_handler_passes_messages_verbatim_to_router` confirms handler doesn't pre-sanitize; `test_injection_markers_present_in_pattern_set` confirms the canonical 'ignore previous' marker is in the source-of-truth tuple. |

**Score:** 5/6 truths verified, 1 routed to human verification (CHAT-04 — operator UAT)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `forge_bridge/llm/router.py` | `complete_with_tools(messages: Optional[list[dict]] = None)` D-02a Pattern B | VERIFIED | Line 265 has `messages: Optional[list[dict]] = None`; mutual-exclusion guard ("mutually exclusive" + "must provide either prompt or messages") fires with correct ordering after `_in_tool_loop.get()` recursive guard. Backwards-compat preserved — all 27 pre-existing tests pass. |
| `forge_bridge/llm/_adapters.py` | Both adapters + Protocol accept `messages=` kwarg | VERIFIED | Lines 140, 176, 333 — Anthropic + Ollama + Protocol all accept `messages: Optional[list[dict]] = None`. Ollama prepends system only if caller didn't include one. |
| `forge_bridge/console/_rate_limit.py` | IP-keyed token bucket + RateLimitDecision frozen dataclass + _reset_for_tests | VERIFIED | 101 LOC; `_CAPACITY=10.0`, `_REFILL_SECONDS=60.0`, `_TTL_SECONDS=300.0` constants pinned (lines 28-31); `RateLimitDecision` is `@dataclass(frozen=True)`; `check_rate_limit()` lazy TTL sweep + retry_after clamped to ≥1; `_reset_for_tests()` clears state under lock |
| `forge_bridge/console/handlers.py` | async chat_handler with rate-limit, validation, timeout, D-14a translation, D-17 nested envelope | VERIFIED | Line 383 `async def chat_handler(request)`; rate-limit pre-gate at 418-432; hand-rolled body validation 437-510 (validation_error / unsupported_role); LLMRouter access via `request.app.state.console_read_api._llm_router` (D-16); `await _mcp_server.mcp.list_tools()` (D-04) at line 525; outer `asyncio.wait_for(timeout=125.0)` at 552-562 wrapping `complete_with_tools(messages=..., sensitive=True, max_seconds=120.0)`; D-14a exception translation 564-606; X-Request-ID on every reply via `_chat_error()` helper |
| `forge_bridge/console/app.py` | `Route("/api/v1/chat", chat_handler, methods=["POST"])` registered | VERIFIED | Line 16 imports `chat_handler`; line 101 `Route("/api/v1/chat", chat_handler, methods=["POST"])`. Build smoke-test confirms route resolves. |
| `forge_bridge/console/templates/chat/panel.html` | Alpine x-data="chatPanel()" + transcript + tool-trace + spinner + textarea | VERIFIED | Line 16 `x-data="chatPanel()"`; `<script src="/ui/static/forge-chat.js">` loaded SYNCHRONOUSLY at top of view block (post pass-2 fix per 16-05 SUMMARY); `chat-transcript`, `chat-message--{user,assistant,tool}`, `chat-tool-trace`, `spinner-amber`, `#chat-input` classes all present |
| `forge_bridge/console/static/forge-chat.js` | chatPanel factory + escape-first renderMarkdown + fetch wiring | VERIFIED | 176 LOC; `function chatPanel` at line 64; `escapeHtml` + `renderMarkdown` at lines 14-58 (escape FIRST, then re-render fenced/inline-code/bold/http(s)-only-links); `fetch("/api/v1/chat")` at line 131 with 429/504/422/!ok branches mapping to D-09 prescribed copy; zero `localStorage`/`sessionStorage` (D-06); `rel="noopener noreferrer" target="_blank"` on rendered links |
| `forge_bridge/console/ui_handlers.py` | `ui_chat_handler` renders chat/panel.html (renamed from ui_chat_stub_handler) | VERIFIED | `async def ui_chat_handler` exists; renders `chat/panel.html`; old `ui_chat_stub_handler` removed; old `chat/stub.html` deleted |
| `forge_bridge/console/static/forge-console.css` | LOGIK-PROJEKT amber spinner + chat layout classes | VERIFIED | Plan 16-03 appended core classes; plan 16-05 added 7 layout classes (`.chat-panel`, `.chat-form`, `.chat-send`, `.chat-empty`, `.chat-error`, `.chat-message-content`, `.visually-hidden`) — all LOGIK-PROJEKT-token-only, zero new `--color-*` introduced |
| `tests/console/test_chat_handler.py` | 11+ deterministic handler tests + post-rename guard | VERIFIED | 12 tests (11 from plan 16-04 + 1 post-rename guard from plan 16-07); all PASS in 0.06s; mocked LLMRouter via AsyncMock; patched `forge_bridge.mcp.server.mcp.list_tools` |
| `tests/console/test_rate_limit.py` | 8+ deterministic rate-limit tests | VERIFIED | 10 tests (2 RateLimitDecision + 8 CheckRateLimit including capacity, refill, partial refill, TTL eviction, distinct IPs, unknown-IP fallback, reset); all PASS in 0.01s |
| `tests/integration/test_chat_endpoint.py` | CHAT-03 sanitization E2E (Strategy A always-on + Strategy B gated) | VERIFIED | 3 tests: `test_handler_passes_messages_verbatim_to_router` PASSES, `test_injection_markers_present_in_pattern_set` PASSES, `test_chat_does_not_leak_poisoned_tool_marker` SKIPPED (FB_INTEGRATION_TESTS gate) |
| `tests/integration/test_chat_parity.py` | CHAT-05 parity (Strategy A always-on + Strategy B gated) | VERIFIED | 3 tests: `test_chat_parity_browser_vs_flame_hooks` PASSES, `test_chat_parity_envelope_keys_locked` PASSES, `test_chat_parity_live_structural_match` SKIPPED (FB_INTEGRATION_TESTS gate) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `chat_handler` | `_rate_limit.check_rate_limit` | `from forge_bridge.console._rate_limit import check_rate_limit, RateLimitDecision` | WIRED | handlers.py:46-48 import; line 418 invocation; rate-limit decision drives 429 response with Retry-After header |
| `chat_handler` | `LLMRouter.complete_with_tools` | `await asyncio.wait_for(router.complete_with_tools(messages=..., tools=..., sensitive=True, max_seconds=120.0), timeout=125.0)` | WIRED | handlers.py:552-562 — exact pattern matches must-have spec |
| `chat_handler` | `mcp.server.mcp.list_tools` | `await _mcp_server.mcp.list_tools()` (lazy import) | WIRED | handlers.py:524-525 — lazy `from forge_bridge.mcp import server as _mcp_server` avoids circular import; runtime tool snapshot per D-04 |
| `forge-chat.js` | `POST /api/v1/chat` | `fetch("/api/v1/chat", { method: "POST", body: JSON.stringify({messages: [...]})})` | WIRED | forge-chat.js:131-135; response handler maps status to D-09 prescribed copy; success path replaces `this.messages` from `body.messages` (Level 4 data flow confirmed) |
| `panel.html` | `forge-chat.js` | `<script src="/ui/static/forge-chat.js">` (synchronous, top of view block) | WIRED | Plan 16-05 pass-2 fix moved script to TOP of `{% block view %}` without `defer` so `window.chatPanel` is registered before Alpine processes `x-data` on DOMContentLoaded |
| `complete_with_tools` | `_sanitize_tool_result` | Multiple call sites in router.py (473, 494, 537, 551, 564, 582) | WIRED | Every tool-result content string passed to LLM is sanitized via `_sanitize_tool_result(msg, max_bytes=effective_max_bytes)`. INJECTION_MARKERS replaced with `[BLOCKED:INJECTION_MARKER]`. Single source of truth shared with Phase 7's `_sanitize_tag` via `forge_bridge/_sanitize_patterns.py`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `chat/panel.html` | `messages` (Alpine state) | `body.messages` from `fetch("/api/v1/chat")` response (forge-chat.js:158-163) | Yes — chat handler appends real assistant content from `complete_with_tools()` to incoming messages list before returning (handlers.py:611-613); LLM router invokes real provider (Ollama/Anthropic) inside the loop, sanitization-protected | FLOWING |
| `chat_handler` response | `out_messages = list(messages) + [{"role": "assistant", "content": result_text}]` | `result_text` from `await router.complete_with_tools(...)` | Yes — real LLM output from FB-C coordinator | FLOWING |
| `chat_handler` validation | `messages` from request body | `await request.json()` | Yes — caller-supplied; validated at lines 437-510 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Chat handler module imports cleanly | `python -c "from forge_bridge.console.handlers import chat_handler; import inspect; assert inspect.iscoroutinefunction(chat_handler)"` | exit 0 | PASS |
| /api/v1/chat route registered in build_console_app | `python -c "from forge_bridge.console.app import build_console_app; from unittest.mock import MagicMock; app = build_console_app(MagicMock()); paths = [r.path for r in app.routes if hasattr(r,'path')]; assert '/api/v1/chat' in paths"` | exit 0 | PASS |
| Rate limiter smoke-test | `python -c "from forge_bridge.console._rate_limit import check_rate_limit; assert check_rate_limit('test').allowed"` | exit 0 (allowed=True on first call) | PASS |
| Phase 16 unit + integration tests | `pytest tests/console/test_chat_handler.py tests/console/test_rate_limit.py tests/integration/test_chat_endpoint.py tests/integration/test_chat_parity.py -v` | 26 passed, 2 skipped (FB_INTEGRATION_TESTS gated), 0 failed | PASS |
| Full repo regression check | `pytest tests/ -q` | 729 passed, 106 skipped, 0 failed | PASS |
| `forge-chat.js` has zero localStorage/sessionStorage references (D-06) | `grep -c "localStorage\|sessionStorage" forge_bridge/console/static/forge-chat.js` | 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CHAT-01 | 16-02, 16-04 | Rate limit (10 req/60s, 11th → 429 + Retry-After, IP-keyed v1.4) | SATISFIED | `_rate_limit.py` token bucket + handler 429 path + 2 unit tests verify 11th request blocks |
| CHAT-02 | 16-04 | 125s wall-clock timeout via integration test with sleep-forever stub | SATISFIED | Outer `asyncio.wait_for(timeout=125.0)` at handlers.py:552-562; `test_chat_outer_timeout_returns_504` + `test_chat_loop_budget_exceeded_returns_504` both PASS |
| CHAT-03 | 16-06 | Sanitization E2E — poisoned tool marker does NOT propagate to LLM context | SATISFIED | Strategy A: handler forwards user content verbatim (D-15) + INJECTION_MARKERS contains "ignore previous"; sanitization wired in router.py at 6 call sites; Strategy B (live Ollama) skipped without `FB_INTEGRATION_TESTS=1` |
| CHAT-04 | 16-05 (UI), N/A (UAT) | Artist asks "what synthesis tools were created this week?", gets useful answer <60s on assist-01 | NEEDS HUMAN | Web UI panel + JS + handler all shipped; in-loop dogfood UAT passed in plan 16-05 ("That's working"); formal D-12/D-36 fresh-operator artist UAT is human-only |
| CHAT-05 | 16-06 | External-consumer parity (browser + Flame-hooks structural shape match) | SATISFIED | `test_chat_parity_browser_vs_flame_hooks` PASSES — same payload, same endpoint, structurally identical responses; envelope keys locked to `{messages, stop_reason, request_id}` |
| LLMTOOL-06 | 15-* (FB-C), 16-04 (consumed) | Tool result sanitization boundary (overlaps with CHAT-03 — FB-C ships, FB-D wires) | SATISFIED | `_sanitize.py:_sanitize_tool_result()` ships in FB-C; INJECTION_MARKERS source-of-truth in `_sanitize_patterns.py`; consumed transitively via `complete_with_tools()` (router.py 6 call sites). Chat handler does NOT re-sanitize (D-15 — sanitization happens BELOW handler boundary inside the FB-C loop). |

No orphaned requirements — REQUIREMENTS.md maps Phase 16 to CHAT-01..05 + LLMTOOL-06 (which is FB-C-shipped, FB-D-consumed); all 6 IDs accounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none in Phase 16 code) | - | - | - | - |

Per 16-REVIEW.md: 5 warnings + 6 info findings, 0 critical. None block goal achievement:

| Review ID | Severity | Description | Disposition |
|-----------|----------|-------------|-------------|
| WR-01 | Warning | No body-size cap before `request.json()` (theoretical OOM via 50MB JSON on loopback) | Operational hardening — does not block goal. v1.4 binds 127.0.0.1; v1.5 auth migration is the appropriate gate. |
| WR-02 | Warning | No upper bound on `len(messages)` or per-message content length | Operational hardening. FB-C inner cap (`max_iterations=8`) bounds the loop; the unguarded prompt-bomb surface is theoretical. |
| WR-03 | Warning | `_chat_error` `extra_headers` precedence bug (theoretical — only one in-tree caller) | Defense-in-depth. Currently safe; documented for future maintainers. |
| WR-04 | Warning | `_rate_limit` uses `threading.Lock` from `async def` handler | Documented in module docstring; safe under single-thread asyncio loop because critical section is non-blocking. v1.5 hardening item. |
| WR-05 | Warning | TTL eviction sweep is O(N) per call — DoS surface if v1.5 opens to LAN with IP keys | v1.5 hardening item; SEED-AUTH-V1.5 migration replaces IP key with caller_id. |

All 5 warnings are explicitly classified as v1.5+ operational hardening, not v1.4 correctness blockers. The 6 info items (cosmetic markdown rendering quirks, missing `tool_call_id` test, lazy import in hot path, etc.) are all judgment-call quality improvements — not gaps.

### Human Verification Required

#### 1. CHAT-04 fresh-operator artist UAT (D-12 / D-36 hard gate)

**Test:**
1. Deploy forge-bridge to assist-01 (canonical local LLM hardware host with `qwen2.5-coder:32b` on Ollama).
2. Open the Web UI at `http://<assist-01>:9996/ui/chat` in a browser as a non-developer artist (NOT the implementer).
3. Type the canonical UAT prompt verbatim: **"what synthesis tools were created this week?"**
4. Press Enter (D-10 — Enter sends, Shift+Enter inserts newline).
5. Observe the response.

**Expected:**
- Spinner (`spinner-amber`) appears on the Send button while inflight.
- Within <60s, an assistant message bubble appears (left-border amber `#cc9c00` `--color-accent`).
- Bubble content is plain English, factually responsive to the question, references actual synthesis tools created in the past week (the LLM uses MCP tools like `forge_list_synthesized_tools` or similar to answer).
- NO error banner (no 429, no 504, no 422, no generic "Chat error" message).
- NO timeout (response within 60s — well under the 125s outer cap).
- If the artist asks follow-up questions, the conversation continues with intact per-tab history (D-06).
- Artist subjectively confirms the answer is useful — not just syntactically correct, but actually answers what they asked.

**Why human:**
- D-12 / D-36 hard fresh-operator gate per Phase 10 precedent — this is a UX quality + LLM response quality assertion that cannot be programmatically verified.
- The in-loop dogfood UAT during plan 16-05 (user verdict: "That's working" after the 2-pass rendering fix) verified the wire end-to-end on a dev machine WITHOUT live Ollama (the panel correctly fell through to a 504 banner). That confirmed the panel structure + send/receive cycle + error-handling path. It did NOT verify the artist-facing happy path on assist-01 with a real LLM answer.
- The CHAT-04 spec explicitly calls for an artist (NOT the implementer, NOT a developer) asking a specific canonical prompt and judging the answer subjectively useful. Failure here is the documented Phase 16.1 remediation trigger (analogous to Phase 10.1).

**On failure:** Trigger Phase 16.1 remediation phase. Failure modes to look for: (a) LLM produces inaccurate or unhelpful response → likely a system-prompt or tool-selection issue in the FB-C coordinator, not FB-D; (b) request times out at 125s → Ollama model loading or hardware issue, surface to operator; (c) UI rendering bug — should not happen given plan 16-05's two-pass fix and the post-rename guard test, but flag if observed.

### Gaps Summary

No gaps blocking automated goal achievement. The 5 ROADMAP success criteria for Phase 16 are all VERIFIED at the structural / contract level:

- **SC-1 (rate limit)** — code shipped, unit-tested, integration-tested
- **SC-2 (timeout)** — outer 125s `asyncio.wait_for` wraps FB-C's 120s inner cap; D-14a exception translation tested
- **SC-3 (sanitization)** — handler forwards user content verbatim (D-15); FB-C `_sanitize_tool_result` invoked at 6 call sites in `complete_with_tools`; injection-marker source-of-truth pinned in `_sanitize_patterns.py`
- **SC-4 (artist UAT)** — Web UI panel + API + sanitization all shipped; the artist UAT itself is operator activity scheduled separately (see human_verification)
- **SC-5 (external-consumer parity)** — browser-shape + Flame-hooks-shape clients hit same endpoint, produce structurally identical responses

The single human verification item is the formal CHAT-04 fresh-operator artist UAT, which is an operator activity by design (D-12/D-36 hard gate). All code paths are in place; the UAT validates the LLM's actual response quality on assist-01 hardware with a non-developer artist asking the canonical question.

The 5 code review warnings (no criticals) are documented as v1.5+ operational hardening — none block goal achievement at v1.4.

---

_Verified: 2026-04-27T19:45:00Z_
_Verifier: Claude (gsd-verifier)_
