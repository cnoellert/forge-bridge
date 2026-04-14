# Feature Landscape

**Domain:** Learning pipeline systems, LLM routers, and pluggable MCP servers for post-production pipeline middleware
**Researched:** 2026-04-14
**Confidence:** MEDIUM — based on direct code inspection of FlameSavant (source system), existing forge-bridge codebase, and established patterns from MCP SDK/FastMCP. Web search unavailable; findings cross-referenced against in-repo evidence.

---

## Table Stakes

Features users (LLM agents, downstream consumers like projekt-forge) expect. Missing = the system does not fulfil its stated purpose.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Execution logging with JSONL persistence | Learning pipelines must survive restarts; replay-on-startup requires durable log | Low | Established in FlameSavant `ExecutionLog.js`. Append-only JSONL at `~/.forge/executions.jsonl`. Cap stored output to avoid unbounded growth. |
| Code normalisation + hash fingerprinting | Pattern deduplication across semantically equivalent executions (different literals, same structure) | Low | Strip string/number literals, collapse whitespace, SHA-256 first 16 hex chars. Proven in FlameSavant. |
| Promotion threshold counter | Engine for deciding when a pattern has been seen enough to synthesise | Low | In-memory counter keyed by hash; configurable threshold (FlameSavant uses 3). Returns `promoted=True` signal to caller. |
| Replay on startup | Rebuild in-memory counters from JSONL without re-executing code | Low | Linear scan of log file on init; re-hydrate `_counts` map from records. Required for threshold survival across restarts. |
| LLM backend abstraction | Synthesiser and any other generation need must not depend on a specific provider | Medium | Single `complete(prompt, sensitive, system, temperature)` call surface; provider swap is config, not code change. |
| Sensitivity-based routing | Production pipelines contain sensitive data (shot names, file paths, SQL, openclip XML) that must not egress to cloud | Low | `sensitive=True` → local Ollama; `sensitive=False` → cloud Claude. Existing in `llm_router.py` but sync-only. |
| Async completion API | MCP tools are async; synthesiser runs inside the async tool pipeline | Medium | Existing `llm_router.py` is sync-only — blocking `asyncio` event loop in async context. Must be `async def complete(...)`. |
| Health check endpoint | Agents need to know if backends are reachable before committing to a synthesis attempt | Low | `health_check() → dict` already exists; needs async counterpart and MCP resource exposure. |
| Skill synthesis from examples | Core learning outcome: turn repeated ad-hoc code into a reusable, parameterised MCP tool | High | LLM generates Python function; validation required before registration. Source: FlameSavant `SkillSynthesizer.js`. |
| Synthesised tool validation | LLM output is untrusted; syntactically broken or wrongly-shaped tools must be rejected before registration | Medium | At minimum: parse Python (compile()), verify function signature matches MCP tool pattern, confirm required fields present. |
| Dynamic MCP tool registration | Synthesised tools must appear in the MCP tool list without a process restart | High | FastMCP supports `mcp.tool()` decorator; dynamic registration requires calling this at runtime rather than at import time. Tools must survive the stdio transport loop. |
| Probation / success tracking | Synthesised tools need a trial period; failed calls should not silently stay registered | Medium | Track call count and failure count per synthesised tool. Demote or quarantine on repeated failure. |
| `register_tools(mcp)` pluggable API | projekt-forge and other downstream consumers need to add their own tools to the shared MCP server | Medium | Single function that accepts the FastMCP instance and registers additional tools. No fork of server.py needed. |
| Configurable system prompt | Different callers (synthesiser vs interactive agent vs project-specific tools) need different pipeline context | Low | Pass `system` override to `complete()`; default to `FORGE_SYSTEM_PROMPT` for local, minimal prompt for cloud. Already present in `llm_router.py`. |
| Optional dependency installation | `openai` and `anthropic` are not needed by consumers who only use the WebSocket bridge or MCP without LLM features | Low | Move to `pyproject.toml` extras group (e.g. `pip install forge-bridge[llm]`). Currently hard dependencies — must change. |

---

## Differentiators

Features that create competitive advantage for this specific use case. Not expected by default, but meaningful when present.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Intent tracking on executions | Log not just "what ran" but "why it ran" (user intent string) | Low | Enrich `ExecutionLog` record with optional `intent: str` field. Enables better synthesis prompts: "Write a skill for: [intent]". |
| Re-synthesis on failure | When a synthesised tool fails probation, attempt to regenerate it using the failure context | High | Local LLM makes this economically viable (cost ≈ $0). Pass original examples + error trace to synthesiser. FlameSavant does not implement this — it's an improvement. |
| LLM router exposed as MCP resource | Agents can query backend health and model selection without a tool call | Low | FastMCP `@mcp.resource("llm://health")` returning current backend status, active model names. |
| Namespace partitioning for tool names | `flame_*` for Flame HTTP tools, `forge_*` for pipeline state tools, `skill_*` for synthesised tools | Low | Already partially implemented (flame_/forge_). Extending to `skill_*` prefix for synthesised tools gives agents clear semantic cues about tool provenance. |
| User-taught skill path | Beyond auto-synthesis: expose a "save this code as a named skill" pathway | Medium | Maps to FlameSavant `synthesizeFromDescription`. Requires a dedicated MCP tool: `forge_save_skill(name, description, code)`. |
| Synthesiser targeting Python not JS | All synthesis output is Python MCP tool functions (not JS CommonJS modules like FlameSavant) | Medium | Python tools register directly into FastMCP at runtime. No intermediate file format; function object is the artefact. |
| Per-tool `_source` tagging | Distinguish built-in tools from synthesised tools from user-taught tools in the registry | Low | Simple metadata on the registered tool object. Lets agents and downstream consumers reason about tool provenance. |
| Pydantic input models for all tools | Structured validation before any Flame or forge-bridge call | Low | projekt-forge already does this (see `reconform.py`). Missing from current `forge_bridge/tools/`. Prevents silent bad-input errors. |
| Synthesis prompt includes execution intent | Enrich synthesis prompt with intent strings when available | Low | `"User intent: ${intent}\nExamples:\n${examples}"` produces better named, better described skills than raw code examples alone. |

---

## Anti-Features

Things to deliberately NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Execution log in Postgres | Postgres adds schema migration burden and a runtime dependency for what is essentially a local append-only journal | Use JSONL file at `~/.forge/executions.jsonl` — fast, portable, survives DB downtime, consistent with FlameSavant's proven approach |
| Sandboxed Python execution of synthesised tools | Sandboxing Python is complex (seccomp, sub-interpreter), provides false security for trusted local tools, and breaks Flame API access which requires the main process | Apply structural validation (compile(), signature check) and rely on probation tracking for quality control. Document that synthesised tools run in process. |
| LLM router calling cloud for sensitive operations | Data governance violation — client shot names, file paths, SQL are in scope | Hard-code the routing rule: `sensitive=True` never reaches cloud. Make this non-configurable at the routing layer. |
| Blocking (sync) LLM calls in async context | `asyncio.get_event_loop().run_until_complete()` inside an async tool will deadlock or produce unexpected behaviour | Implement async-native `complete()` using `asyncio.to_thread()` for the blocking OpenAI/Anthropic client calls until native async clients are wired. |
| Auto-purge of synthesised skills | Automatic deletion of underperforming skills risks losing captured knowledge | Flag for review (quarantine status), never auto-delete. The human or downstream consumer decides removal. |
| forge-specific tools (catalog, orchestrate, scan, seed) | These belong in projekt-forge, not forge-bridge | Implement pluggable `register_tools()` so projekt-forge adds its own tools without forking the server |
| Authentication in this milestone | Local-only deployment, deferred by explicit design decision | Framework already exists (client_name in hello). Do not implement in Phases 0-3. |
| HTTP mode for MCP server as primary transport | stdio is the MCP standard for Claude Desktop / agent integration; HTTP mode is a debug aid | Keep `--http` flag for testing but do not design synthesised tool registration around it |

---

## Feature Dependencies

```
Async LLM router
  → Skill synthesiser (synthesiser calls router)
  → LLM health check MCP resource (needs async health_check)

Execution log (JSONL)
  → Replay on startup (reads log)
  → Promotion threshold counter (reads/writes in-memory counts)
  → Promotion counter → Skill synthesiser trigger (promoted=True signals synthesis)

Skill synthesiser
  → Synthesised tool validation (syntactic check before write)
  → Dynamic MCP tool registration (validated tool is registered)
  → Dynamic registration → Probation tracker (new tool needs tracking)

Probation tracker
  → Re-synthesis on failure (failure events trigger re-synthesis path)

register_tools(mcp) API
  → Depends on: dynamic tool registration working at all
  → Used by: projekt-forge (Phase 4, out of scope here)

Optional LLM deps
  → Must be done before: any release where downstream consumers don't need LLM features
  → Blocks nothing functionally, but is a packaging correctness fix

Pydantic input models
  → Independent; can be added per-tool during flame parity work
  → Required before: any probation tracking (need structured failure attribution)

Intent tracking
  → Depends on: execution log (adds a field)
  → Used by: synthesis prompt builder (optional enrichment, gracefully absent)
```

---

## MVP Recommendation

The minimum set that makes the learning pipeline functional end-to-end:

1. **Async LLM router** — everything downstream is blocked on this. Promote `llm_router.py` to `forge_bridge/llm/router.py` with `async def complete()`.
2. **Execution log with JSONL persistence + replay** — durability and threshold state survival across restarts.
3. **Promotion counter → skill synthesis trigger** — the core loop: record → count → synthesise.
4. **Skill synthesiser targeting Python MCP tools** — port FlameSavant's `SkillSynthesizer` to Python; validate and register output.
5. **Dynamic MCP tool registration** — synthesised tools must appear without restart.
6. **Probation tracking** — basic success/failure counter; quarantine on threshold.
7. **`register_tools(mcp)` API** — pluggable registration so projekt-forge can extend without forking.

Defer:
- **Re-synthesis on failure** — valuable but complex; defer to after probation is working.
- **User-taught skill path** — nice-to-have; defer to after automatic synthesis is stable.
- **Intent tracking** — low complexity but low urgency; add as enrichment once basic log is working.
- **`_source` tagging** — one-liner addition; include in synthesis step (low cost).

---

## Sources

- Direct code inspection: `/Users/cnoellert/Documents/GitHub/FlameSavant/src/learning/ExecutionLog.js` — execution log design (HIGH confidence, primary source)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/FlameSavant/src/learning/RegistryWatcher.js` — hot-reload registry watcher (HIGH confidence, primary source)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/FlameSavant/src/agents/SkillSynthesizer.js` — synthesiser design, validation patterns, prompt structure (HIGH confidence, primary source)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/llm_router.py` — existing sync LLM router, sensitivity routing (HIGH confidence, in-repo)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/server.py` — current MCP registration model (HIGH confidence, in-repo)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/reconform.py` — Pydantic model usage, tool patterns (HIGH confidence, upstream source)
- `.planning/PROJECT.md` — scope definition, validated/active requirements (HIGH confidence, authoritative for this project)
- `.planning/codebase/ARCHITECTURE.md` — current system structure (HIGH confidence, in-repo)
- `pyproject.toml` — dependency packaging structure, optional dep gap (HIGH confidence, in-repo)
