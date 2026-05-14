---
name: SEED-CLOUD-CHAT-AGENTIC-ROUTER-V1.6+
description: Phase 23.1 author-walk surfaced a previously-invisible bug. The chat handler hardcodes `sensitive=True` which routes through local Ollama, so the cloud agentic-loop codepath (`sensitive=False`) has been functionally dark since FB-D landed. Temporarily flipping `sensitive=False` for diagnostic isolation revealed that cloud routing aborts pre-LLM in 0.2s with `reason=tool_loop_error` + `exc_type=LLMToolError` + `prompt_tokens=0`. The router refuses to make ANY Anthropic API call. Bug needs root-cause investigation before cloud routing can be operationally relied on.
type: bug-with-reproducer
planted_during: Phase 23.1 author-walk on portofino 2026-05-14 — diagnostic swap test confirmed local-model performance is the only residual 23.1 blocker, BUT incidentally revealed cloud routing is broken at a layer that's structurally separate from anything 23.1 touched
trigger_when: v1.6 milestone opens AND any cloud-routing use case wants to ship (auth, sensitive-data routing, agentic-from-Claude-Desktop, default-model-bump considers cloud) OR `SEED-DEFAULT-MODEL-PERFORMANCE-V1.6+` track B (defer to cloud) needs cloud routing to work OR `SEED-CHAT-CLOUD-CALLER-V1.5` activates and needs cloud-callable surface
---

# SEED-CLOUD-CHAT-AGENTIC-ROUTER-V1.6+

## Reproducer

```bash
# 1. Ensure ANTHROPIC_API_KEY is set in /etc/forge-bridge/forge-bridge.env
fbridge console doctor | grep llm_backend
# Should show: llm_backend.cloud  ok  reachable; model=claude-sonnet-4-6

# 2. Temporarily flip sensitive=True → sensitive=False in handlers.py
python -c "
import re, pathlib
p = pathlib.Path('forge_bridge/console/handlers.py')
text = p.read_text()
new = re.sub(r'sensitive=True,\s*# D-05 hardcoded',
             'sensitive=False,  # cloud agentic diagnostic',
             text)
p.write_text(new)
"
fbridge down && fbridge up

# 3. Run any chat query that would trigger an agentic loop
fbridge chat "What are the clips on Reel 1"

# 4. Read the log
tail -n 80 ~/.forge-bridge/logs/mcp_http.log | grep -B 2 -A 5 "tool_loop_error\|chat tool_error"
```

## Observed Failure

CLI side:
```
Sending request...
Chat error — check console for details.
Retrying (attempt 2/2, sleeping 1.1s)...
forge-bridge chat: invalid_response: HTTP 500 from http://127.0.0.1:9996/api/v1/chat
  (fast-fail in 0.18s): Chat error — check console for details.
```

Daemon side:
```
[12:26:58] INFO   tool-call session complete iter=0  router.py:753
                  elapsed_s=0.2
                  prompt_tokens_total=0
                  completion_tokens_total=0
                  reason=tool_loop_error
           WARN   chat tool_error  handlers.py:1337
                  request_id=...
                  exc_type=LLMToolError
```

**Critical signal:** `iter=0`, `prompt_tokens_total=0`, `completion_tokens_total=0`, `elapsed_s=0.2`. Anthropic API was **never reached**. The router aborted before making any LLM call. The local-Ollama path on the SAME chat handler with the SAME registered tools completes multiple iterations and makes successful tool calls (see Phase 23.1 walk evidence) — so the failure is specific to the cloud routing codepath, not the chat handler or tool registry generically.

## Why This Has Been Invisible

CLAUDE.md and `handlers.py` line 1288 hardcode `sensitive=True`:

```python
chat_result = await asyncio.wait_for(
    router.complete_with_tools(
        messages=messages,
        tools=tools,
        sensitive=True,               # D-05 hardcoded
        system=enforced_system,
        ...
    ),
    timeout=125.0,
)
```

Every production chat request routes through local Ollama. The cloud routing path (`sensitive=False`) has had no production caller since FB-D landed at v1.4. Code paths without callers rot — and this one rotted.

The 23.1 walk's diagnostic swap was the first time the cloud agentic-loop path was exercised end-to-end in production conditions. The bug surfaced immediately.

## Hypotheses for Root Cause (Priority Ordered)

Without router.py / AnthropicAdapter introspection, three candidates:

### (1) AnthropicAdapter tool-schema validation (highest likelihood)

Anthropic's API has stricter tool-definition requirements than Ollama. Potential rejection paths:
- Tool descriptions exceeding length limits (Anthropic caps tool descriptions; some `flame_*` tools have multi-paragraph docstrings).
- Tool schemas with `$ref` indirection — Anthropic requires inlined schemas; FastMCP's nested `$ref` shape may not be inlined before send.
- Tool names with invalid characters — unlikely (forge-bridge uses `flame_` / `forge_` / `synth_` only).

The AnthropicAdapter probably validates the tool list pre-send and raises on rejection. `LLMToolError` is the bubbled-up classification.

### (2) Synthesized-tool guard

`synth_rename_segment` was in the registry during the 23.1 walk (`Registered synthesized tool: synth_rename_segment` log entry). The router or AnthropicAdapter may have a guard that rejects synthesized tools in cloud routing — possibly for sensitivity reasons (don't send LLM-generated code definitions to a third-party API).

If true: the guard isn't documented anywhere I can see; would be archaeology debt.

### (3) `RecursiveToolLoopError` classification mismatch

The `reason=tool_loop_error` field hints at the router's recursive-tool-loop guard firing. But that guard should NOT fire on iter=0 with zero prompt tokens — it's designed to catch recursive synthesizer attempts, not initial-request validation. Possible bug in the guard's classification logic when paired with cloud routing.

## Why This Doesn't Block 23.1 Close

23.1's scope is the chat-path correctness on the production routing path (`sensitive=True` → local). That path is now verified end-to-end:

- Affordance: model picks `flame_execute_python` (post-repositioning)
- Dispatch: args validate, tool runs (post-flatten)
- Instrumentation: utility.py log line fires with structured fields
- Tool execution: 12ms, status=ok

The cloud routing failure is **structurally orthogonal** — different code path, different adapter, different failure mode. It's a real bug worth fixing, but fixing it is not what 23.1 was framed to do.

## What v1.6 Should Do

1. **Reproduce reliably** — the reproducer above is the minimum viable repro. v1.6 should turn it into a hermetic test (mock AnthropicAdapter or use the cloud API with a tiny query) so subsequent investigators don't have to do the full author-walk.
2. **Read the router code path for `sensitive=False`** — identify where `tool_loop_error` is set at iter=0. The check should be obvious once we look at the code; it's a 5-minute investigation pre-blocked by 23.1's scope discipline.
3. **Fix the underlying validation** — either inline schemas, shorten tool descriptions, fix the synth-tool guard, or whatever the root cause turns out to be.
4. **Add a `fbridge chat --cloud` diagnostic flag** — once cloud routing is functional, expose it as an opt-in flag so future cloud-routing regressions surface immediately instead of going dark for another release cycle.
5. **Decide the sensitive-routing policy** — `SEED-AUTH-V1.5` flagged this; cloud routing fix + auth + a real policy decision compose together.

## Activation Triggers

Any of:

1. **v1.6 milestone opens** and a phase scopes cloud-routing work.
2. **`SEED-DEFAULT-MODEL-PERFORMANCE-V1.6+` track B** needs cloud routing to work for the "defer complex queries to cloud" strategy.
3. **`SEED-CHAT-CLOUD-CALLER-V1.5`** activates — its trigger was "any consumer surface needs cloud routing." This seed names the implementation blocker.
4. **Claude Desktop / agentic-from-cloud use case ships** and needs the `sensitive=False` path.

## Cross-References

- 23.1 walk reproducer + log evidence: log timestamps 12:26:57-58 in `~/.forge-bridge/logs/mcp_http.log` on portofino.
- 23.1 close commit + STATE.md cursor — defers this to v1.6+.
- Sibling seeds: `SEED-AUTH-V1.5` (the sensitive-routing policy this enables), `SEED-CHAT-CLOUD-CALLER-V1.5` (the consumer-surface trigger), `SEED-DEFAULT-MODEL-PERFORMANCE-V1.6+` (the use case that wants this fixed), `SEED-OPUS-4-7-TEMPERATURE-V1.5` (a different cloud-side fix that also needs to land before opus-4-7 cloud routing).

## The One-Line Lesson

> Code paths without callers rot. The cloud routing path has been dark since FB-D shipped; the 23.1 swap test was the first call in over a milestone cycle. The bug it surfaced is real but predictable: untested codepaths regress silently.
