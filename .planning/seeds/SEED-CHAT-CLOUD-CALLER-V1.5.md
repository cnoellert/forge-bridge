# SEED: Chat cloud (Anthropic) caller path (v1.5, paired with SEED-AUTH-V1.5)

**Source:** Phase 16 (FB-D) D-05 — hardcoded sensitive=True (local Ollama only)
**Status:** planted 2026-04-27

## Trigger

When `SEED-AUTH-V1.5` lands — i.e., when forge-bridge has caller identity and can attribute
Anthropic API costs. Without identity, opening the cloud path means any unauthenticated
caller can rack up Anthropic bills via the IP-rate-limited but otherwise wide-open chat
endpoint.

## v1.4 baseline

D-05: `chat_handler` hardcodes `sensitive=True`. The request body MUST NOT accept a
`sensitive` field — passing one is silently ignored. The full sensitive-routing surface
stays available via direct `LLMRouter.complete_with_tools()` for non-chat callers (e.g.,
synthesizer pipelines that already have caller context via the consumer's process boundary).

```python
# forge_bridge/console/handlers.py chat_handler — current
result_text = await router.complete_with_tools(
    messages=messages,
    tools=tools,
    sensitive=True,                          # D-05 hardcoded
    ...
)
```

## v1.5+ migration shape

After auth lands, the request body grows a `sensitive: bool = True` field with a default
that PRESERVES v1.4 behavior:

```json
{
  "messages": [...],
  "sensitive": false       // OPT-IN to cloud path; default stays True
}
```

Handler logic gates `sensitive=False` on caller authorization:

```python
sensitive = body.get("sensitive", True)
if sensitive is False and not _caller_has_cloud_quota(request):
    return _error("forbidden",
                  "cloud chat requires authenticated caller with quota", 403)
```

`_caller_has_cloud_quota(request)` is the auth integration point — depends on how
SEED-AUTH-V1.5 lands.

## Cross-references

- SEED-AUTH-V1.5.md — hard prerequisite (caller identity → cost attribution)
- 16-CONTEXT.md D-05 (sensitivity routing)
- LLMTOOL-02 (cloud path is already shipped at the LLMRouter level — chat just isn't
  exposing it yet)

## Open questions

1. Should cloud-quota be per-call (count) or per-month (token-budget)? Likely token-budget
   for cost predictability.
2. Per-caller default — should each caller's default be `sensitive=True` (privacy-first) or
   `sensitive=False` (best-model-first)? Likely first; caller opts in to cloud explicitly.
3. Should the response surface a `provider` field (`"ollama"` | `"anthropic"`) so the client
   knows which backend served the call? Useful for debugging cost overruns.
