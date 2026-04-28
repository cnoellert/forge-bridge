# Phase 16 (FB-D): Chat Endpoint — Context

**Gathered:** 2026-04-27
**Status:** Ready for planning
**Aliases:** FB-D (canonical cross-repo identifier per projekt-forge v1.5 dependency contract); `16` is the gsd-tooling numeric ID.

<domain>
## Phase Boundary

`/api/v1/chat` exposes `LLMRouter.complete_with_tools()` (shipped FB-C) over HTTP with
end-to-end sanitization, IP-based rate limiting, wall-clock timeout enforcement, and
zero-divergence external-consumer parity. The Web UI chat panel (replaces the chat-nav
stub from CONSOLE-04 v1.3) is the first consumer; projekt-forge v1.5 Flame hooks
(Phase 22/23) are the second. Same endpoint, same payload shape, same behavior — that's
the parity contract.

forge-bridge stays the bookkeeper: the chat endpoint *coordinates* an LLM agentic loop,
it does not *propose* operations itself. Operations the LLM proposes via tools land as
`staged_operation` rows (FB-A) and surface via the staged-ops MCP/HTTP tools (FB-B).

**Surfaces shipped:**
- HTTP route: `POST /api/v1/chat` (provider-shape `messages` body, non-streaming JSON response)
- IP-based rate limiter (in-memory token bucket; 11 req/min → HTTP 429)
- Wall-clock timeout enforcement (125s = FB-C's 120s loop cap + 5s response framing buffer)
- Web UI chat panel (replaces `forge_bridge/console/templates/chat/stub.html`)
- Chat-nav stub gets a live page; the "launches in Phase 12" copy is removed
- 4 forward-looking SEED files (streaming, tool allowlist, cloud caller, history persistence)

**Out of scope for this phase:**
- Streaming tokens (SSE / WebSocket) — `SEED-CHAT-STREAMING-V1.4.x` planted
- Server-side conversation persistence — `SEED-CHAT-PERSIST-HISTORY-V1.5+` planted (paired with auth)
- Caller-specified tool allowlists — `SEED-CHAT-TOOL-ALLOWLIST-V1.5` planted
- Cloud (`sensitive=False` / Anthropic) chat path — `SEED-CHAT-CLOUD-CALLER-V1.5` planted (paired with `SEED-AUTH-V1.5`)
- Caller-identity rate limiting — folded into `SEED-AUTH-V1.5`
- Multi-project chat context — v1.4 stays single-bridge / single-project per v1.3 lock
- Markdown editor / rich input — single `<textarea>`; richer input is v1.5+ UX
- Chat-history search / export — v1.5+

</domain>

<decisions>
## Implementation Decisions

### Streaming Posture (Gray Area A)

- **D-01:** Non-streaming JSON response for v1.4. Single `POST /api/v1/chat` returns `{"messages": [...], "request_id": "<uuid>", "stop_reason": "..."}` after `complete_with_tools()` finishes the full loop.
  - **Why:** FB-C is non-streaming (15-CONTEXT). CHAT-02 (125s timeout) and CHAT-04 (<60s artist UAT) work fine non-streaming. Adding SSE on top of an already 5-criterion phase risks scope blow-out. Streaming is a UX upgrade, not a correctness requirement.
  - **Forward path:** `SEED-CHAT-STREAMING-V1.4.x` plants the SSE/WebSocket migration.

### Request Body Shape (Gray Area B)

- **D-02:** Native provider shape — no sugar. Request:
  ```json
  {
    "messages": [
      {"role": "user", "content": "what synthesis tools were created this week?"},
      {"role": "assistant", "content": "..."},
      {"role": "tool", "content": "...", "tool_call_id": "..."}
    ],
    "max_iterations": 8,            // optional, defaults to FB-C default
    "max_seconds": 120.0,           // optional, defaults to FB-C default
    "tool_result_max_bytes": 8192   // optional, defaults to FB-C default
  }
  ```
  Roles: `user | assistant | tool` (matches what FB-C's `_ToolAdapter.append_results()` already produces).
  - **Why:** Both Anthropic and Ollama use `messages` natively (FB-C adapters speak this format). projekt-forge Flame hooks (CHAT-05) build history client-side; single-shot would force a re-prompt round-trip. Caller-overridable loop caps match FB-C's overridable kwargs (research §6.3).

- **D-02a (Pattern B — FB-C surface extension):** FB-C `LLMRouter.complete_with_tools()` currently accepts `prompt: str` only. To honor the wire-shape `messages` contract WITHOUT lossy stitching, FB-C is extended in this phase with an optional `messages: list[dict] | None = None` kwarg. When `messages` is provided, the coordinator skips its internal `[{"role":"user","content":prompt}]` auto-wrap and passes the structured list directly to the adapter. The adapters (`AnthropicToolAdapter`, `OllamaToolAdapter`) already speak the `messages` format natively — this exposes existing capability on the public surface. Backwards-compatible: existing `prompt=` callers unchanged. ~20-30 LOC in `forge_bridge/llm/router.py` + 1 unit test. Lands in FB-D scope as a prerequisite plan in Wave 1.
  - **Why Pattern B over Pattern A (handler stitches to single prompt string):** Stitching loses structured `tool` role boundaries from prior turns, which degrades multi-turn agentic chat quality (LLM treats tool-call history as opaque user-content blob). Stitching also creates a wire/internal divergence — wire honors `messages`, internal flattens it. Pattern B closes that gap cleanly.

- **D-03:** Response shape:
  ```json
  {
    "messages": [
      // full echoed history including the new assistant + tool turns the loop produced
    ],
    "stop_reason": "end_turn",  // only "end_turn" in v1.4; cap-fires return HTTP 504 (D-14a)
    "request_id": "<uuid>"
  }
  ```
  Echoing the full message list (not just the new assistant turn) means the client owns conversation state without parsing `stop_reason` to know "did anything happen?".
  - **Cap-fire posture:** When `complete_with_tools()` raises `LLMLoopBudgetExceeded` (either `max_iterations` or `max_seconds`), the handler translates BOTH to HTTP 504 with the unified D-09 banner copy. Distinguishing the two cap types in the response surface would require extending FB-C with a `return_history: bool = False` kwarg to expose partial state — deferred to v1.5. `SEED-CHAT-PARTIAL-OUTPUT-V1.5` plants the partial-state response shape.

### Tool Registry Exposure (Gray Area C)

- **D-04:** All registered MCP tools are available to chat — snapshot at request time. The handler obtains the tool list via the public FastMCP API (whatever `forge_bridge.mcp.invoke_tool()` already lists) and passes them all to `complete_with_tools(tools=...)`.
  - **Why:** FB-C already shipped `forge_bridge.mcp.invoke_tool(name, args)` as the default executor (plan 15-07). Curating an allowlist is premature — no v1.4 consumer is asking for it. Caller-specified subsetting adds request-payload complexity for hypothetical use.
  - **Forward path:** `SEED-CHAT-TOOL-ALLOWLIST-V1.5` plants the path for caller-specified subsetting.

### Sensitivity Routing (Gray Area D)

- **D-05:** Chat handler hardcodes `sensitive=True` (local Ollama) in v1.4. The `sensitive` field is **not** accepted in the request body.
  - **Why:** Chat is IP-rate-limited only (no caller identity until SEED-AUTH-V1.5 lands). Opening the cloud path means any unauthenticated caller can rack up Anthropic bills. v1.4's value is artist-on-assist-01 — that's local-first by design. The full sensitive-routing surface stays available via direct `complete_with_tools()` for non-chat callers (e.g., synthesizer pipelines).
  - **Forward path:** `SEED-CHAT-CLOUD-CALLER-V1.5` plants the cloud path migration paired with auth.

### Web UI Chat Panel UX (Gray Area E)

- **D-06:** Per-tab in-browser conversation history. State lives in JavaScript, cleared on tab close. NO server-side persistence in v1.4.
  - **Why:** No identity → no per-user persistence boundary. Per-tab matches Phase 10's stateless console pattern. `SEED-CHAT-PERSIST-HISTORY-V1.5+` plants the server-side history migration paired with auth.

- **D-07:** Tool-call transparency: each `tool_use` round renders as a collapsed `<details>`-style block showing `{tool_name}({args_preview})`. Click expands to show full args + result preview (truncated at ~500 chars; expand again for full text).
  - **Why:** Default-collapsed is artist-friendly; expandable is the D-36 fresh-operator gate's "can I tell what happened?" affordance for dev/UAT verification. Mirrors Phase 11 CLI's manifest/tools cross-link pattern.

- **D-08:** LOGIK-PROJEKT amber spinner during in-flight requests. Matches Phase 10 / 10.1 visual language (per project memory: "artist-first, LOGIK-PROJEKT dark+amber palette"). **Pattern-mapper correction:** `forge_bridge/console/static/forge-console.css` does NOT currently ship a spinner. Plan ships a 10-line addition: `@keyframes spin` + `.spinner-amber` class using existing `--color-accent` amber token. No SVG, no new asset, CSS-only.

- **D-09:** Explicit error banners with prescribed copy:
  - HTTP 429: `"Rate limit reached — wait {retry_after}s before retrying."` (`Retry-After` header value substituted)
  - HTTP 504: `"Response timed out — try a simpler question or fewer tools."`
  - HTTP 500: `"Chat error — check console for details."` (links to `/ui/execs`)
  - HTTP 422: `"Invalid request — {validation_message}"` (Pydantic validator message)
  - **Why:** Banner pattern matches Phase 10's existing 4xx/5xx surface. Plain English; no stack traces user-side.

- **D-10:** Input: single `<textarea>` auto-growing to ~5 lines max. Enter sends; Shift+Enter inserts a newline. No slash commands, no `@` mentions, no rich formatting in v1.4.

- **D-11:** Assistant message rendering: minimal markdown renderer (no new dep). **Researcher correction:** Phase 10 ships ZERO markdown rendering (verified by template/static grep). Plan ships a ~50-line vanilla JS escape-first renderer in `forge_bridge/console/static/forge-chat.js` with the security-required ordering: (1) HTML-escape the entire string; (2) re-render fenced code blocks (` ```...``` `) preserving monospace; (3) re-render inline code (`` `...` ``); (4) re-render bold (`**...**`); (5) re-render http(s)-only links with `rel="noopener noreferrer" target="_blank"` — reject `javascript:`, `data:`, and other schemes. No syntax highlighting in v1.4 (additive, defer).

### Artist UAT Scope (Gray Area F — restated, locked)

- **D-12:** D-36 hard fresh-operator gate. An actual artist on assist-01, not a developer. UAT prompt: "what synthesis tools were created this week?" must produce a useful, plain-English answer in <60s. Failure → remediation phase analogous to Phase 10.1.
  - **Why:** ROADMAP CHAT-04 verbatim + project memory: "Every UI-touching phase (FB-D) includes mandatory non-developer dogfood UAT".

### Rate Limiting Implementation (CHAT-01)

- **D-13:** In-memory token bucket dict in a NEW module `forge_bridge/console/_rate_limit.py` (separated from the chat handler for testability — pattern-mapper recommendation; no existing analog in repo). NO new dependency (avoid `slowapi` / Redis). Single-process is fine — there's only one bridge process per machine in v1.4. **Lock primitive:** `threading.Lock` (NOT `asyncio.Lock`) — single-process simplicity, no async-context capture in test fixtures.
  - **Bucket:** Keyed by `request.client.host` (IPv4/IPv6 string). Capacity 10, refill rate 10/60s (sliding window approximation: 11th request in 60s → 429).
  - **TTL sweep:** Stale buckets (no activity in 5 minutes) are evicted lazily on every request to bound memory.
  - **Response on 429:** `{"error": "rate_limit_exceeded", "message": "...", "request_id": "<uuid>"}` + `Retry-After: <seconds>` header. Matches FB-B error envelope.
  - **Why:** Simple, testable, zero dep. Migrates cleanly to caller-identity bucketing once auth lands (`SEED-AUTH-V1.5` already covers this).

### Wall-Clock Timeout (CHAT-02)

- **D-14:** Handler wraps the coordinator call:
  ```python
  result = await asyncio.wait_for(
      llm_router.complete_with_tools(
          messages=messages,
          tools=tools,
          sensitive=True,
          max_iterations=body.max_iterations,
          max_seconds=120.0,
      ),
      timeout=125.0,
  )
  ```
  The outer 125s `wait_for` is the response-framing safety net per CHAT-02; the inner 120s is FB-C's wall-clock cap. On `asyncio.TimeoutError` from the outer wrap, the handler returns HTTP 504 with the prescribed banner copy from D-09.
  - **Why:** CHAT-02 verbatim. Two-layer timeout (loop cap + framing buffer) is the published contract.

- **D-14a (timeout/exception code-path translation):** Per Q4 resolution from research+pattern-mapper review, every cap-fire collapses to HTTP 504; structural / programming errors translate to HTTP 500.
  | Exception raised by FB-C | HTTP status | Error code | Notes |
  |---|---|---|---|
  | `LLMLoopBudgetExceeded` (max_seconds) | 504 | `request_timeout` | Inner 120s cap fired first; expected normal path |
  | `LLMLoopBudgetExceeded` (max_iterations) | 504 | `request_timeout` | Same banner copy (D-03 cap-fire posture) |
  | `asyncio.TimeoutError` (outer 125s) | 504 | `request_timeout` | Defense-in-depth; only fires if FB-C deadlock |
  | `RecursiveToolLoopError` | 500 | `internal_error` | Should never reach chat handler — FB-C's `_in_tool_loop` guard is for nested LLM calls inside synthesizer, not HTTP entry. Log as critical. |
  | `LLMToolError` (any flavor) | 500 | `internal_error` | Wrapped by FB-C; the loop already surfaces tool-internal failures back to the LLM as `is_error=True` per LLMTOOL-03. Reaching the handler with this means coordinator-level breakage. |
  | Any other exception | 500 | `internal_error` | Caught at outer try/except per FB-B handler convention |

### Sanitization Boundary (CHAT-03)

- **D-15:** End-to-end sanitization wiring:
  - Tool definitions: existing Phase 7 `_sanitize_tag()` already runs at registration time — nothing new wires in.
  - Tool results: existing FB-C `_sanitize_tool_result()` already runs inside `complete_with_tools()` — nothing new wires in.
  - User input messages: NOT sanitized. The LLM treats user content as untrusted by design; reformatting user prompts would damage UX (artist types literal `IGNORE PREVIOUS INSTRUCTIONS` as part of a question and we'd silently censor it).
  - **Verification:** integration test poisons a tool sidecar with `IGNORE PREVIOUS INSTRUCTIONS` in tool name + args; asserts the LLM-bound prompt does NOT contain the marker substring after the loop runs.

### LLMRouter Injection (no new singleton)

- **D-16:** Reuse the `_llm_router` already injected into `ConsoleReadAPI` (Phase 9 pattern, used today by `/api/v1/health`). The chat handler reads it via the same pattern as the staged-ops handlers.
  - **Why:** Instance-identity gate (Phase 9 D-25 / API-04) holds — `_lifespan` owns the canonical `LLMRouter` and we don't duplicate.

### Error Envelope Shape

- **D-17:** Match Phase 9 / FB-B envelope **verbatim** — note this is the **NESTED** shape locked by `forge_bridge/console/handlers.py:60` and `tests/console/test_staged_zero_divergence.py`:
  ```json
  {"error": {"code": "<machine_string>", "message": "<human>"}}
  ```
  (Pattern-mapper correction: I had previously written a flat `{"error": "<code>", "message": "..."}` shape — that was wrong. The nested shape is the FB-B test-locked contract; FB-D extends it via the existing `_error()` helper at `handlers.py:58-60`.) Specific codes:
  - `rate_limit_exceeded` — 429 (with `Retry-After` header)
  - `request_timeout` — 504
  - `validation_error` — 422 (Pydantic message)
  - `internal_error` — 500
  - `unsupported_role` — 422 (caller passed an invalid role in messages)
  - `bad_request` — 400 (malformed JSON, missing required field, etc.)
  - **Why:** Zero divergence from the 9 existing API routes. The cross-route consistency test (`test_staged_zero_divergence.py`) already locks this shape; we extend its sweep to include `/api/v1/chat`.
  - **`request_id`:** included as a top-level sibling of `error` in the success path; for error responses, included in the response headers as `X-Request-ID` (matches FB-B convention — the error envelope itself stays minimal).

### External-Consumer Parity (CHAT-05)

- **D-18:** Parity is verified by replaying identical requests through two clients:
  1. The Web UI chat panel (browser `fetch`)
  2. A stub Flame-hooks Python client (replays projekt-forge v1.5's expected request shape)

  Both hit the same `/api/v1/chat` endpoint with the same payload; the test asserts structural shape match of the response (modulo non-deterministic LLM output — assert keys + types + role progression, not content equality).
  - **Why:** "Same endpoint, multiple consumers, byte-identical behavior" is the FB-D mission statement (ROADMAP). The parity test catches accidental UI-coupling regressions early.

- **D-19:** No OpenAPI schema generation in v1.4. The endpoint contract is documented inline in `forge_bridge/console/handlers.py` (matches FB-B handlers' docstring convention). projekt-forge v1.5 reads the docstring + integration test as the contract.
  - **Why:** Adding OpenAPI now means picking a generator (`fastapi.openapi.utils` doesn't apply — we're on Starlette), which is a v1.5 surface decision.

### Chat-Nav Stub Replacement

- **D-20:** Delete `forge_bridge/console/templates/chat/stub.html`. Create `forge_bridge/console/templates/chat/panel.html` with the live chat panel. Update `shell.html` if needed (likely not — the existing `<a href="/ui/chat">` link from CONSOLE-04 already points to the right URL; only the rendered content changes).

### Logging & Observability

- **D-21:** Each `/api/v1/chat` call emits a structured log entry: `request_id`, `client_ip`, `message_count_in`, `message_count_out`, `tool_call_count`, `stop_reason`, `wall_clock_ms`. Reuse the existing `logging_config.py` setup. Tool-call traces inside the loop are already logged by FB-C.
  - **Why:** Phase 10.1 added timestamped log entries for the execs surface; chat needs the same observability for the artist UAT debrief and any post-hoc rate-limit / timeout investigations.

</decisions>

<canonical_refs>
## Canonical References (read these before research/planning)

**Roadmap-level:**
- `.planning/ROADMAP.md` — Phase 16 (FB-D) success criteria (CHAT-01..05) at line 187+; v1.4 milestone goal at line 73+

**Requirements:**
- `.planning/REQUIREMENTS.md` — CHAT-01..05 at lines 33-37; LLMTOOL-01..07 (FB-C dependencies) at lines 23-29

**Prior phase context (decisions that constrain FB-D):**
- `.planning/phases/15-fb-c-llmrouter-tool-call-loop/15-CONTEXT.md` — coordinator surface, sanitization patterns, exception classes, sensitivity routing
- `.planning/phases/14-fb-b-staged-ops-mcp-tools-read-api/14-CONTEXT.md` — error envelope shape, ConsoleReadAPI extension pattern, MCP tool registration
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-CONTEXT.md` — bookkeeper invariant (forge-bridge does not execute, it persists)

**Existing code patterns:**
- `forge_bridge/console/handlers.py` — staged_list/approve/reject handler patterns (FB-B); copy this style for chat handler
- `forge_bridge/console/app.py` — `Route(...)` registration (lines 73-98); add chat routes here
- `forge_bridge/console/read_api.py` — `_llm_router` injection at line 84-102; reuse the same pattern
- `forge_bridge/console/templates/chat/stub.html` — to be replaced
- `forge_bridge/console/static/forge-console.css` — LOGIK-PROJEKT amber spinner, banner styles, monospace conventions
- `forge_bridge/llm/router.py` — `LLMRouter.complete_with_tools()` (Phase 15 deliverable)
- `forge_bridge/mcp/registry.py` — `invoke_tool()` default executor (Phase 15 plan 15-07)

**FB-C planning artifacts (cross-cutting):**
- `.planning/research/FB-C-TOOL-CALL-LOOP.md` — research §6.1-6.4 (loop semantics, message shape rationale, parallel-tool-exec deferral)

**This phase's planning artifacts (must be read by planner + executor):**
- `.planning/phases/16-fb-d-chat-endpoint/16-RESEARCH.md` — pitfalls (request.client None, asyncio.wait_for nesting, tool snapshot async-API, model-speed risk, sanitization-vs-display semantics)
- `.planning/phases/16-fb-d-chat-endpoint/16-PATTERNS.md` — exact line-numbered analogs for each new file (handlers.py:179-224 staged_approve template, query_console.html:40-117 Alpine factory, tests/integration/test_complete_with_tools_live.py:49-66 skipif gate)

**Project-level:**
- `.planning/PROJECT.md` — current milestone scope, FB-A..FB-D consumer-driven naming
- `.planning/STATE.md` — milestone metadata, last activity
- `CLAUDE.md` — project instructions

</canonical_refs>

<deferred>
## Deferred Ideas (planted as SEED files in Phase 16 plan)

| SEED file | Triggers when | Why deferred |
|-----------|---------------|--------------|
| `SEED-CHAT-STREAMING-V1.4.x.md` | After v1.4 ships and artist UAT validates the non-streaming UX baseline | Streaming is a UX upgrade, not a correctness requirement; non-streaming closes CHAT-04 fine |
| `SEED-CHAT-TOOL-ALLOWLIST-V1.5.md` | When a v1.5 consumer needs request-time tool subsetting | All tools is the minimum-coupling default; subsetting adds payload complexity for hypothetical use |
| `SEED-CHAT-CLOUD-CALLER-V1.5.md` | When `SEED-AUTH-V1.5` lands (caller identity → cost attribution) | Without identity, opening cloud path means unauthenticated callers rack up Anthropic bills |
| `SEED-CHAT-PERSIST-HISTORY-V1.5+.md` | When auth + per-user data scoping land | No identity → no per-user persistence boundary; per-tab JS state covers v1.4 |
| `SEED-CHAT-PARTIAL-OUTPUT-V1.5.md` | When a v1.5 consumer needs partial-message output on cap-fire (vs blanket 504) | Requires extending FB-C with `return_history: bool = False` kwarg to expose partial state. Marginal user value at v1.4 MVP — same banner copy for both cap types makes the wire-shape distinction unnecessary. |

</deferred>

<specifics>
## Specifics the User Cares About

- **Visual language:** LOGIK-PROJEKT dark + amber palette (per project memory + Phase 10/10.1 precedent). Reuse existing CSS — no new color tokens.
- **Artist-first:** the D-36 fresh-operator gate is non-negotiable for FB-D. Tool-call traces are *collapsed by default* so the chat doesn't look like a developer log.
- **No new dependencies:** rate limiting in-memory dict, markdown rendering vanilla or reuse Phase 10's renderer. New deps require explicit user approval.
- **Bookkeeper invariant:** the chat endpoint never directly executes user-proposed mutations against domains; mutations go through staged_operation (FB-A/B). This is the v1.4 milestone's core architectural commitment.
- **Cross-repo parity:** projekt-forge v1.5 Flame hooks consume the same endpoint with byte-identical behavior. Any UI-coupled hack in the handler is a parity bug.

</specifics>

<open_questions>
## Open Questions for Research / Planning

**All four open questions raised by research+pattern-mapper review (2026-04-27) have been resolved into the decisions above:**

1. ~~**D-02 messages-vs-prompt mismatch (HIGH)**~~ — Resolved as **D-02a / Pattern B** (extend FB-C with `messages: list | None = None` kwarg; ~20-30 LOC + 1 unit test, backwards-compatible). Pattern B is preferred over Pattern A (handler stitches to single string) because stitching loses structured `tool` role boundaries from prior turns and degrades multi-turn agentic chat quality.
2. ~~**D-03 stop_reason partial-state on cap-fire (MEDIUM)**~~ — Resolved as **drop `max_iterations`/`max_seconds_exceeded` from response shape; both cap types translate to HTTP 504**. `SEED-CHAT-PARTIAL-OUTPUT-V1.5` plants the v1.5 path requiring FB-C `return_history` extension. Same banner copy for both cap types makes the wire-shape distinction unnecessary at MVP.
3. ~~**`qwen2.5-coder:32b` <60s latency (MEDIUM, CHAT-04 risk)**~~ — Resolved as **defer smoke test to plan's UAT phase**. If model misses <60s during CHAT-04 UAT on assist-01, that triggers a Phase 16.1 remediation phase mirroring Phase 10.1's pattern. `SEED-DEFAULT-MODEL-BUMP-V1.4.x` (already planted in Phase 15 plan 15-10) is the forward path. Don't gate this plan on a hardware-dependent smoke test.
4. ~~**Three timeout code paths (LOW)**~~ — Resolved as **D-14a translation matrix**: every cap-fire (outer `asyncio.TimeoutError`, inner `LLMLoopBudgetExceeded` for either max_seconds or max_iterations) translates to HTTP 504; structural errors (`RecursiveToolLoopError`, `LLMToolError`, anything else) translate to HTTP 500.

**Mechanical corrections also folded in:**
- **D-08 spinner** → ship 10-line CSS as part of plan (forge-console.css has no existing spinner; pattern-mapper verified)
- **D-11 markdown renderer** → ship 50-line vanilla escape-first JS renderer in `forge-chat.js` (Phase 10 ships zero markdown; researcher verified)
- **D-13 lock primitive** → `threading.Lock` over `asyncio.Lock` for single-process v1.4 simplicity
- **D-17 envelope** → corrected to NESTED `{"error": {"code", "message"}}` shape (matches FB-B handlers.py:60 + zero-divergence test lock)

**Genuine open questions remaining (planner can decide inline; not blocking):**

1. **Streaming concurrent test fixture cleanup** — the parity test (D-18) replays the same payload through two clients. Should the second replay reuse the first's session via `httpx.AsyncClient(transport=ASGITransport(app))` or open a fresh client? Researcher's recommendation: fresh client per replay (no shared state, parity is more meaningful).
2. **Token-bucket lazy-vs-active TTL sweep** — research recommends lazy sweep (every request checks TTL on accessed bucket); active sweep (background task) is overkill for v1.4 single-process. Planner picks.

</open_questions>
