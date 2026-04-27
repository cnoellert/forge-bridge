---
name: SEED-PARALLEL-TOOL-EXEC-V1.5
description: Flip complete_with_tools(parallel=True) from NotImplementedError to enabled after serial-baseline UAT
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: v1.5 milestone opens AND a measured workload demonstrates serial-execution throughput is the bottleneck (artist UAT or projekt-forge integration)
---

# SEED-PARALLEL-TOOL-EXEC-V1.5: Parallel tool execution within a single LLM turn

## Idea

FB-C ships with `parallel: bool = False` advertising the v1.5 path. Passing `True` raises `NotImplementedError`. Once the v1.4 serial baseline has artist UAT data and a workload (e.g., projekt-forge fan-out queries — "read sidecars for all 100 staged ops") demonstrates serial execution is the bottleneck, design and implement the parallel path.

## Why This Matters

- **Forge-bridge's tool surface is mostly serial-natural** — `bridge.execute()` to Flame serializes through the idle-event queue anyway, so parallel doesn't help that path.
- **Read-only sidecar/manifest fan-out IS parallel-friendly** — `manifest_read` × 100 has no race surface and would benefit from concurrent execution.
- **The kwarg is already shipped** — v1.4 advertises the v1.5 path so external consumers can write code with `parallel=True` and get a clear NotImplementedError today, then transparently benefit when v1.5 flips the implementation.

## When to Surface

- v1.5 milestone opens (this is the most common trigger)
- Any phase plan introduces a fan-out workload that would benefit from parallel tool execution
- An artist UAT report cites tool-call latency as a UX issue
- projekt-forge v1.5+ requests parallel tool execution for an explicit use case

## How to Apply

1. Audit the forge-bridge tool surface to classify each tool as parallel-safe (read-only) or parallel-unsafe (writes through `bridge.execute()`). Add a `parallel_safe: bool` annotation to the MCP `Tool` metadata if not present.
2. In `OllamaToolAdapter` and `AnthropicToolAdapter`, add `supports_parallel = True` paths gated by the new kwarg. Anthropic already supports it (omit `disable_parallel_tool_use=True` when parallel); Ollama parallel is model-dependent (research §3.6 — needs reliability check on qwen3:32b).
3. In `LLMRouter.complete_with_tools`, replace the current `NotImplementedError` raise with: when `parallel=True`, slice `response.tool_calls` to only include parallel-safe tools, run them concurrently via `asyncio.gather`, fall back to serial for any unsafe tool in the same turn.
4. Add tests: TestParallelToolExecution covering (a) all-parallel-safe → concurrent, (b) mixed-safe → fall back to serial, (c) all-unsafe → serial (matches v1.4 behavior).
5. Update CHAT-04 UAT to verify the artist sees a measurable latency improvement on fan-out queries.

## Cross-References

- FB-C CONTEXT.md D-06 — "Serial tool execution. Coordinator processes ONLY `tool_calls[0]` per turn... `parallel: bool = False` kwarg ships on `complete_with_tools()` and raises `NotImplementedError` if `True` (advertises v1.5 path)."
- FB-C research §6.4 — race-condition analysis + cost-of-seriality discussion + recommendation to defer.
- REQUIREMENTS.md Out of Scope row "Parallel tool execution within a single LLM turn".
- forge_bridge/llm/router.py — `complete_with_tools` parallel kwarg + NotImplementedError raise site.
- forge_bridge/llm/_adapters.py — `supports_parallel = False` on both adapters.
