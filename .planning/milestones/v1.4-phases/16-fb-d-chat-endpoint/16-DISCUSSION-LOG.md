# Phase 16 (FB-D): Chat Endpoint — Discussion Log

**Session:** 2026-04-27
**Mode:** Recommendation-driven (user requested "Make recos based on previous design decisions and I can review")

## Gray areas surfaced

| # | Area | Stakes |
|---|------|--------|
| A | Streaming vs non-streaming response | API contract permanence; FB-C is non-streaming |
| B | Request body shape (single-shot prompt vs `messages` array) | Cross-consumer parity; client state ownership |
| C | Tool registry exposure (all / allowlist / caller-specified) | Coupling surface; future config burden |
| D | Sensitivity routing default | Cost surface without auth; artist-on-assist-01 baseline |
| E | Web UI chat panel UX | Artist-facing affordances; D-36 gate readability |
| F | CHAT-04 artist UAT scope | Locked by ROADMAP + project memory |

## Recommendations made → user accepted all

User directive: "Please make recos based on our previous design decisions and I can review."
User response: "Look good!" → all 6 recommendations accepted without override.

| # | Recommendation | Anchored in |
|---|----------------|-------------|
| A | Non-streaming JSON; plant `SEED-CHAT-STREAMING-V1.4.x` | FB-C 15-CONTEXT (non-streaming); CHAT-02/04 timing budgets work non-streaming |
| B | `{"messages": [{role, content}, ...]}` provider-native shape; loop caps overridable | FB-C adapters speak this format natively; projekt-forge v1.5 builds history client-side |
| C | All registered MCP tools at request-time snapshot; plant `SEED-CHAT-TOOL-ALLOWLIST-V1.5` | FB-C plan 15-07 shipped `mcp.invoke_tool()` as default executor; minimum-coupling default |
| D | Hardcoded `sensitive=True` (local Ollama); plant `SEED-CHAT-CLOUD-CALLER-V1.5` paired with `SEED-AUTH-V1.5` | IP-rate-limited only; cost-attribution requires identity (deferred) |
| E | Per-tab JS history; collapsed `<details>` tool traces; LOGIK-PROJEKT amber spinner; explicit 429/504/500 banners; textarea input; vanilla markdown | Phase 10/10.1 visual language; project memory ("artist-first, dark+amber, mandatory non-developer UAT") |
| F | D-36 hard fresh-operator gate (real artist on assist-01) | ROADMAP CHAT-04 verbatim; project memory |

## Implementation-level decisions surfaced (no user override requested)

- Rate limiting: in-memory token bucket dict, no new dependency; IP-keyed; `Retry-After` header
- Wall-clock timeout: 125s outer `asyncio.wait_for` wrapping FB-C's 120s loop cap (CHAT-02 verbatim contract)
- Sanitization wiring: tool defs (Phase 7) + tool results (FB-C) — both already in place; user input messages NOT sanitized (would break UX); E2E verified via poisoned-tool integration test
- LLMRouter injection: reuse `_llm_router` already on `ConsoleReadAPI` (Phase 9 D-25 instance-identity invariant)
- Error envelope: match Phase 9 / FB-B verbatim — `{"error", "message", "request_id"}`; specific machine codes per response type
- External-consumer parity test (CHAT-05): two clients (browser fetch + stub Flame-hooks Python) replay same payload; assert structural shape match (modulo non-deterministic LLM output)
- Chat-nav stub: delete `templates/chat/stub.html`, create `templates/chat/panel.html`; nav link from CONSOLE-04 v1.3 already points to `/ui/chat` — only rendered content changes
- Logging: structured per-request log entry (request_id, client_ip, message counts, tool_call_count, stop_reason, wall_clock_ms)

## Deferred ideas captured

4 SEED files identified for inclusion in plan 16-XX (planning to mirror Phase 15's plan 15-10 SEED-planting pattern):
- `SEED-CHAT-STREAMING-V1.4.x.md`
- `SEED-CHAT-TOOL-ALLOWLIST-V1.5.md`
- `SEED-CHAT-CLOUD-CALLER-V1.5.md`
- `SEED-CHAT-PERSIST-HISTORY-V1.5+.md`

## Scope creep avoided

The user did not request any out-of-scope additions. Items the workflow filtered as scope creep before reaching the user:
- Markdown rich input / slash commands → "v1.5+ UX"
- Multi-project chat context → already-locked v1.3 single-project decision
- Server-side conversation persistence → folded into SEED paired with auth
- OpenAPI schema generation → v1.5 surface decision
- Syntax highlighting in code blocks → additive, defer

## Next step

`/gsd-plan-phase 16` — researcher reads CONTEXT.md, then planner generates plans. Likely shape: 5-6 plans across 3 waves (handler+rate-limit+timeout, sanitization+parity tests, Web UI panel + chat-nav replacement, then UAT + SEEDs).
