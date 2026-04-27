# SEED: Chat caller-specified tool allowlist (v1.5)

**Source:** Phase 16 (FB-D) D-04 — all registered MCP tools snapshot at request time
**Status:** planted 2026-04-27

## Trigger

When a v1.5 consumer (likely projekt-forge v1.5+ or a downstream Flame hook) needs to
restrict the LLM's tool surface to a subset of registered tools — e.g., a "browse-only"
session that excludes mutation tools like `forge_approve_staged`.

## v1.4 baseline

D-04: every chat request snapshots ALL registered MCP tools and passes them all to
`complete_with_tools(tools=...)`. No allowlist, no per-request curation.

```python
# forge_bridge/console/handlers.py chat_handler — current
tools = await _mcp_server.mcp.list_tools()
result_text = await router.complete_with_tools(messages=..., tools=tools, ...)
```

This is the minimum-coupling default. Curating an allowlist is premature — no v1.4 consumer
asked for it.

## v1.5+ migration shape

Extend the request body with an optional `tool_allowlist: list[str] | None = None` field:

```json
{
  "messages": [...],
  "tool_allowlist": ["forge_list_staged", "forge_get_staged"]
}
```

Handler logic:

```python
all_tools = await _mcp_server.mcp.list_tools()
if body.get("tool_allowlist"):
    tools = [t for t in all_tools if t.name in set(body["tool_allowlist"])]
    if not tools:
        return _error("validation_error",
                      "tool_allowlist matched zero registered tools", 422)
else:
    tools = all_tools
```

Or — bigger surface change — pair with a `tool_denylist` for the inverse pattern. Likely
just allowlist; denylist is harder to reason about (forgetting to add a new tool to the
denylist silently exposes it).

## Cross-references

- 16-CONTEXT.md D-04 (tool registry exposure)
- SEED-AUTH-V1.5 — when auth lands, allowlist might bind to caller role (e.g., "artist
  callers cannot invoke mutation tools").

## Open questions

1. Should the allowlist be per-request or per-session? v1.4 has no session concept — likely
   per-request initially.
2. Should an empty allowlist match ZERO tools (strict) or ALL tools (permissive default)?
   Recommendation: strict — `tool_allowlist: []` is an explicit caller error.
