# Milestones

## v1.0 Canonical Package & Learning Pipeline (Shipped: 2026-04-15)

**Phases completed:** 3 phases, 13 plans, 25 tasks

**Key accomplishments:**

- One-liner:
- Async LLM router in forge_bridge/llm/ with acomplete() coroutine, lazy optional-dep guards, full env-var configuration, and backwards-compatible shim at original path
- forge://llm/health MCP resource exposing local (Ollama) and cloud (Anthropic) backend availability via ahealth_check() on LLMRouter
- [Observation] Linter auto-corrected bridge import in publish.py
- One-liner:
- 13 new Flame MCP tools registered in active server (reconform, switch_grade, timeline disconnect/inspect/version/reconstruct/clone/replace/scan/assign, batch XML) plus LLM health resource wired
- One-liner:
- Namespace-enforcing MCP tool registry with source tagging via meta={'_source'} and frozenset prefix allowlist, with TDD-verified synth_ reservation for synthesis pipeline only
- All ~42 MCP tool registrations centralised in register_builtins() in registry.py; server.py reduced to lifecycle-only with zero direct mcp.tool() calls; forge_bridge.mcp exports register_tools and get_mcp as public API
- ExecutionLog with AST normalization stripping literals, JSONL append-only persistence, SHA-256 fingerprinting, configurable promotion threshold, and bridge.py callback hook
- 1. [Rule 1 - Bug] Fixed test for identical file skip -- content hash mismatch
- ProbationTracker wrapping synthesized tools with per-tool success/failure counters, threshold-based quarantine (file move + MCP removal), and watcher integration

---
