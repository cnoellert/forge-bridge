---
status: failed
phase: 16-fb-d-chat-endpoint
source: [16-VERIFICATION.md]
started: 2026-04-27T19:50:00Z
updated: 2026-04-27T21:45:00Z
debug_session: deferred-to-16.1
---

## Current Test

[FAILED — deferred to Phase 16.1 gap closure]

## Tests

### 1. CHAT-04 fresh-operator artist UAT (D-12 / D-36 hard gate)
expected: Non-developer artist asks "what synthesis tools were created this week?" in the Web UI chat panel on assist-01 (live `qwen2.5-coder:32b`). Artist receives a useful, plain-English answer within <60s. Spinner stops, assistant message bubble renders with amber left-border, content describes the synthesis tools (no error banner, no timeout, no rate-limit fallback). Artist confirms the answer feels natural and useful.
result: failed
detail: |
  Deploy to assist-01 surfaced THREE Phase-16 wiring/integration bugs that
  blocked the artist UAT before it could meaningfully run. Two were patched
  inline during the session (commits below); the third is structural and
  routed to Phase 16.1 for proper gap-closure planning.

  Bug A (FIXED — commit cfc39f2): Starlette 1.0.0 (resolved by fresh `pip
  install -e ".[dev,llm]"` on assist-01) had removed the back-compat shim
  for `TemplateResponse(name, ctx)` (deprecated since 0.30). Every UI
  handler in forge_bridge/console/ui_handlers.py uses the deprecated
  signature → `TypeError: unhashable type: 'dict'` on every UI page render.
  Pinned `starlette<0.53` in pyproject.toml.
  Follow-up TODO: migrate all UI handlers to `TemplateResponse(request, name, ctx)`
  so the pin can be dropped.

  Bug B (FIXED — commit 60d28fa): ConsoleReadAPI was being constructed in
  forge_bridge/mcp/server.py:_lifespan WITHOUT the `llm_router=` kwarg, so
  `_llm_router` was permanently None and chat_handler short-circuited with
  500 "LLM router not configured" on every POST /api/v1/chat. The dev-machine
  visual UAT during plan 16-05 ("That's working") was on a misread — we
  attributed the error banner to "no Ollama → expected 504" but it was
  actually this 500-internal-error path. Wired LLMRouter() into ConsoleReadAPI
  at boot. CHAT-04 wire is now actually connected for the first time.

  Bug C (DEFERRED — routed to Phase 16.1): With Bugs A+B fixed and Ollama
  healthy on assist-01 (qwen2.5-coder:32b loaded in VRAM, `ollama run` returns
  in 1.4s), `complete_with_tools()` hangs the full 120s wall-clock budget on
  iter=0 with prompt_tokens_total=0 / completion_tokens_total=0. Bisected:
  - 1-tool synthetic test (SimpleNamespace with name/description/inputSchema)
    via complete_with_tools → returns in 2.3s, 269 prompt tokens, end_turn.
  - mcp.list_tools() returns 49 tools (21 forge_*, 28 flame_*).
  - When chat_handler passes the full 49-tool MCP list to
    complete_with_tools, Ollama hangs the full budget with zero token output.
  Root cause not yet pinpointed. Hypotheses: tool-schema bloat exceeds
  qwen2.5-coder's tool-selection capacity; one or more tool schemas have
  malformed/oversized fields confusing the model; on bare assist-01 (no
  projekt-forge bridge on :9998, no Flame), every forge_* and flame_* tool
  the model picks would fail at execution anyway. CHAT-04 may need
  tool-list scoping — exposing only tools whose backends are reachable —
  before the artist UAT can succeed in principle.

why_human: |
  Even after fixing the structural wiring, the artist UAT requires a working
  end-to-end tool-call loop on assist-01. The 49-tool list hang is a real
  Phase-16 gap that needs proper planning, not inline debug-and-patch in a
  long shell session. Routing to Phase 16.1 (per Phase-10/10.1 precedent)
  for systematic gap closure.

## Summary

total: 1
passed: 0
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

### Gap-1: chat-handler tool-list hang on full MCP registry
status: failed
debug_session: deferred-to-16.1
evidence: |
  - 1-tool path works (2.3s, end_turn) → native ollama client + tool-calling
    is fundamentally functional with qwen2.5-coder:32b on assist-01.
  - 49-tool path hangs (iter=0, elapsed=120s, 0 prompt tokens, 0 completion
    tokens) → reproducible.
  - Bisection between 1 and 49 tools not yet performed.
  - `ollama run "say hi"` returns in 1.4s → Ollama daemon healthy.
  - Model loaded 100% GPU, 32k context window.
recommendation: |
  Phase 16.1 should:
  1. Bisect the tool-count threshold (5 → 10 → 20 → 30 → 40 → 49) with
     synthetic SimpleNamespace tools to determine if it's a count issue or
     a content issue.
  2. If count issue: investigate tool-list scoping for chat — only expose
     tools whose backends are reachable at request time (skip forge_* if
     projekt-forge bridge unreachable, skip flame_* if Flame unreachable).
     Likely a small "core" tool set for chat (manifest read, registry list)
     that doesn't depend on Flame/projekt-forge being up.
  3. If content issue: identify which tool schemas confuse qwen2.5-coder and
     fix them (likely description/parameter shape issues from tool definitions
     in forge_bridge/mcp/tools.py and the FastMCP-registered flame_* set).
  4. Add a verification test that chat_handler succeeds end-to-end with the
     real (filtered) tool list against a live Ollama — currently no test
     exercises this path; integration tests inject a mocked router.

### Gap-2: TemplateResponse signature migration
status: deferred
recommendation: |
  Migrate all UI handlers in forge_bridge/console/ui_handlers.py from
  `TemplateResponse(name, ctx)` to `TemplateResponse(request, name, ctx)`
  per Starlette ≥0.30 deprecation. Drop the `starlette<0.53` pin from
  pyproject.toml once migration is verified. Roughly 8 call sites to update;
  mechanical change.

### Gap-3: Boot-time LLMRouter wiring lacks regression guard
status: deferred
recommendation: |
  Add a test that asserts `app.state.console_read_api._llm_router is not None`
  after `_lifespan()` finishes — a single TestClient-based smoke test against
  build_console_app + the lifespan hook would have caught Bug B before it
  reached assist-01. Phase 16's integration tests inject a mocked router via
  `app.state` directly, bypassing the boot path.
