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

- **D-03:** Response shape:
  ```json
  {
    "messages": [
      // full echoed history including the new assistant + tool turns the loop produced
    ],
    "stop_reason": "end_turn" | "max_iterations" | "max_seconds_exceeded",
    "request_id": "<uuid>"
  }
  ```
  Echoing the full message list (not just the new assistant turn) means the client owns conversation state without parsing `stop_reason` to know "did anything happen?".

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

- **D-08:** LOGIK-PROJEKT amber spinner during in-flight requests. Matches Phase 10 / 10.1 visual language (per project memory: "artist-first, LOGIK-PROJEKT dark+amber palette"). No new SVG asset — reuse the existing spinner from `forge_bridge/console/static/forge-console.css`.

- **D-09:** Explicit error banners with prescribed copy:
  - HTTP 429: `"Rate limit reached — wait {retry_after}s before retrying."` (`Retry-After` header value substituted)
  - HTTP 504: `"Response timed out — try a simpler question or fewer tools."`
  - HTTP 500: `"Chat error — check console for details."` (links to `/ui/execs`)
  - HTTP 422: `"Invalid request — {validation_message}"` (Pydantic validator message)
  - **Why:** Banner pattern matches Phase 10's existing 4xx/5xx surface. Plain English; no stack traces user-side.

- **D-10:** Input: single `<textarea>` auto-growing to ~5 lines max. Enter sends; Shift+Enter inserts a newline. No slash commands, no `@` mentions, no rich formatting in v1.4.

- **D-11:** Assistant message rendering: minimal markdown renderer (no new dep — match whatever Phase 10 uses for execs / manifest detail rendering, or a 50-line vanilla pass through). Code fences preserve monospace; no syntax highlighting in v1.4 (additive, defer).

### Artist UAT Scope (Gray Area F — restated, locked)

- **D-12:** D-36 hard fresh-operator gate. An actual artist on assist-01, not a developer. UAT prompt: "what synthesis tools were created this week?" must produce a useful, plain-English answer in <60s. Failure → remediation phase analogous to Phase 10.1.
  - **Why:** ROADMAP CHAT-04 verbatim + project memory: "Every UI-touching phase (FB-D) includes mandatory non-developer dogfood UAT".

### Rate Limiting Implementation (CHAT-01)

- **D-13:** In-memory token bucket dict in the chat handler module. NO new dependency (avoid `slowapi` / Redis). Single-process is fine — there's only one bridge process per machine in v1.4.
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

- **D-17:** Match Phase 9 / FB-B envelope verbatim: `{"error": "<machine_code>", "message": "<human>", "request_id": "<uuid>"}`. Specific codes:
  - `rate_limit_exceeded` — 429
  - `request_timeout` — 504
  - `validation_error` — 422
  - `internal_error` — 500
  - `unsupported_role` — 422 (caller passed an invalid role in messages)
  - **Why:** Zero divergence from the 9 existing API routes. Cross-route consistency tests already exist (FB-B D-37); we extend them.

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

None blocking. The decisions above are tight enough that the planner can proceed directly to plan generation. Two things the research phase may want to validate:

1. **Markdown renderer choice:** does Phase 10's existing renderer handle GFM tables / fenced code well enough for chat output, or do we need a 50-line vanilla pass? (Researcher reads `forge_bridge/console/static/` for whatever Phase 10 ships.)
2. **Token-bucket library shape:** confirm in-memory dict is sufficient for v1.4 single-process — i.e., is there any planned multi-instance deployment in v1.4? (STATE.md says no, but worth a quick check during research.)

</open_questions>
