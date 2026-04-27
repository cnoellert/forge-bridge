---
name: SEED-TOOL-EXAMPLES-V1.5
description: Add Anthropic input_examples field to forge MCP Tool definitions for higher first-call accuracy
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: A workload report cites repeated schema-mismatch retries or "Claude doesn't know how to call X correctly" symptoms — or any v1.5 phase that re-evaluates the tool-definition surface
---

# SEED-TOOL-EXAMPLES-V1.5: Anthropic input_examples on registered tools

## Idea

Anthropic's tool-definition shape supports an optional `input_examples` field — an array of valid example inputs. The model uses these as few-shot guidance for calling the tool correctly on the first try. FB-C v1.4 ships without it because forge-bridge tools have terse parameter sets and the schema-translation table (research §5.1) covers the common cases. v1.5 should add `input_examples` to high-traffic tools (e.g., `flame_publish_sequence`, `forge_create_shot`) where the parameter set has multiple optional fields and the LLM occasionally chooses the wrong combination.

## Why This Matters

- **Reduces retry round-trips** — eliminates "missing required parameter" 400s and the per-tool-downgrade fallback (D-31) churn.
- **Token-cost is small** — 20-50 tokens per simple example, 100-200 for complex (research §2.1). Three examples per tool ≈ 150 tokens overhead per tool definition.
- **Improves Web UI chat panel UX (CHAT-04)** — fewer botched first calls = faster artist response.
- **Ollama doesn't support `input_examples`** — but the forge MCP `Tool` metadata can carry examples as a separate annotation that AnthropicToolAdapter consumes and OllamaToolAdapter ignores. Single source of truth, provider-specific consumption.

## When to Surface

- A v1.4.x or v1.5 phase touches the MCP tool registration surface (registry.py, register_builtins, projekt-forge external-tool registration)
- An artist UAT or projekt-forge integration cites first-call-accuracy issues
- D-31 per-tool downgrade fires repeatedly in production logs (signals schema-translation friction)
- v1.5 introduces a new tool with >5 optional parameters

## How to Apply

1. Add an optional `input_examples: list[dict]` field to forge MCP Tool metadata (extend the existing `Tool.inputSchema` annotation system or add a sibling `tool_examples` annotation passed through registry.register_tool).
2. In AnthropicToolAdapter._compile_tools, if `input_examples` is present on a Tool, include it in the compiled dict alongside `name`, `description`, `input_schema`, `strict`.
3. Audit the existing builtin tool surface (forge_bridge/mcp/registry.py register_builtins) and add 2-3 examples per tool with multiple optional fields. Start with `flame_publish_sequence`, `forge_create_shot`, `flame_switch_grade`.
4. Add tests: TestToolExamplesAnthropic verifying that examples reach the wire format; TestToolExamplesOllama verifying they're ignored cleanly without breaking the Ollama path.
5. Document the convention so projekt-forge and other external consumers can add examples to their registered tools.

## Cross-References

- FB-C CONTEXT.md `<deferred>` "Tool examples (`input_examples` field on Anthropic tool definitions)".
- FB-C research §2.1 — input_examples shape + token-cost estimates.
- FB-C research §2.7 — explicit "Defer to v1.4.x or v1.5" recommendation.
- REQUIREMENTS.md Out of Scope row "Anthropic `tool_runner()` beta helper" (related — both are Anthropic features deferred for v1.4).
- forge_bridge/llm/_adapters.py — AnthropicToolAdapter._compile_tools is the addition site.
- forge_bridge/mcp/registry.py — Tool annotation surface for the example metadata.
