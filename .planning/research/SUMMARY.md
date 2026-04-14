# Project Research Summary

**Project:** forge-bridge — learning pipeline milestone
**Domain:** Post-production pipeline middleware with self-improving LLM tooling
**Researched:** 2026-04-14
**Confidence:** HIGH

## Executive Summary

This milestone adds a learning pipeline, async LLM router, and pluggable MCP server to the existing forge-bridge middleware. The work is a Python port of proven patterns from FlameSavant (JavaScript) combined with confirmed FastMCP runtime APIs. The recommended approach builds three additive subsystems — `forge_bridge/llm/`, `forge_bridge/learning/`, and a rebuilt `forge_bridge/mcp/` — that wire into the existing `bridge.py` and MCP server via optional callbacks and a public `register_tools()` API. Nothing in the existing `core/`, `store/`, `server/`, or `client/` packages changes.

The recommended build order is: LLM router async promotion first (everything blocks on this), then MCP server rebuild with the pluggable API, then execution log with the bridge hook, then synthesizer and watcher as the final integration phase. This order follows the hard dependency graph: synthesizer calls the router; watcher calls the MCP registry; the bridge hook calls the log. Each phase is independently shippable and testable before the next begins.

The key risks are async/sync boundary violations (blocking event loop during LLM synthesis), code normalisation errors (Python f-strings and triple-quotes break regex-based fingerprinting), and synthesized tool collisions with static `flame_*` registry entries. All three are preventable with well-understood patterns: `asyncio.to_thread()` wrapping, AST-based normalisation via Python's `ast.unparse`, and strict `synth_` namespace enforcement for synthesized tools.

---

## Key Findings

### Recommended Stack

The entire learning pipeline is buildable with zero new package dependencies. The async LLM router uses `AsyncOpenAI` (openai 2.29.0) and `AsyncAnthropic` (anthropic 0.86.0), both already installed. The execution log uses stdlib `json`, `hashlib`, `re`, and `asyncio.to_thread`. The skill synthesizer uses stdlib `ast`, `types`, and `pydantic` (2.12.5, already installed via FastMCP). The registry watcher uses stdlib `asyncio` polling and `importlib`. The pluggable MCP API uses `FastMCP.add_tool()` / `remove_tool()`, confirmed available in the installed `mcp/server/fastmcp/tools/tool_manager.py`.

One packaging bug must be fixed before release: `openai` and `anthropic` are currently declared as hard dependencies twice in `pyproject.toml`. They must move to a `[project.optional-dependencies]` group named `llm`, making `forge-bridge` installable without LLM packages for consumers who only need the WebSocket bridge or MCP tools.

**Core technologies:**
- `AsyncOpenAI` / `AsyncAnthropic` (installed): async LLM completions — already present, just not wired async
- `ast.unparse` (stdlib): Python-aware code normalisation for execution fingerprinting — handles f-strings, triple-quotes, all Python literal forms
- `asyncio.to_thread` (stdlib): wraps blocking IO (disk writes, sync HTTP clients) without adding `aiofiles` dep
- `FastMCP.add_tool()` / `remove_tool()` (installed): runtime tool registration — confirmed public API, supports hot-load without restart
- `pydantic.BaseModel` (installed): `SkillManifest` schema validation before writing synthesized tools to disk
- `importlib.util.spec_from_file_location` (stdlib): dynamic module loading for synthesized skill files

### Expected Features

**Must have (table stakes):**
- Async `LLMRouter.acomplete()` — all downstream synthesis blocks on this; sync `complete()` preserved as shim
- Execution log (JSONL persistence + replay) — durability across restarts; threshold state survives process kills
- Code normalisation and hash fingerprinting — structural deduplication via `ast.unparse`, not regex
- Promotion threshold counter — in-memory, configurable (default 3), returns `promoted=True` to trigger synthesis
- Skill synthesizer targeting Python MCP tools — LLM generates `async def` functions; validates AST, signature, and runtime shape before writing
- Synthesized tool validation — `ast.parse` + `exec` in isolated namespace + `build_code(**test_params)` call
- Dynamic MCP tool registration — `mcp.add_tool()` called by RegistryWatcher; tools appear in next `tools/list` response without restart
- Probation tracking — success/failure counters per synthesized tool; quarantine (not delete) on threshold breach
- `register_tools(mcp)` pluggable API — projekt-forge injects tools before `mcp.run()` without forking server.py
- Optional LLM dependency extras — `pip install forge-bridge[llm]` installs openai + anthropic; base install stays lean

**Should have (differentiators):**
- Intent tracking on executions — optional `intent: str` field enriches synthesis prompts with user context
- `_source` tagging on all tools — `builtin` / `synthesized` / `user-taught` provenance visible to LLM agents
- LLM health check as MCP resource (`forge://llm/health`) — agents can verify backend availability without a tool call
- `synth_*` namespace for synthesized tools — hard separation from `flame_*` / `forge_*` so synthesized tools cannot shadow static implementations
- Synthesis prompt includes intent strings — produces better-named, better-described skills
- Pydantic input models for all MCP tools — structured validation catches bad input before any Flame execution

**Defer (v2+):**
- Re-synthesis on failure — automatic regeneration using failure trace; defer until basic probation is working
- User-taught skill path (`forge_save_skill` tool) — explicit named-skill pathway; defer until auto-synthesis is stable
- Authentication — explicitly deferred by project design; local-only for this milestone

### Architecture Approach

The three new subsystems are additive and layered: `llm/` has no dependencies on forge-bridge internals; `learning/` depends on `llm/` and calls back into `bridge.py` via an optional callback; `mcp/registry.py` is called by `learning/watcher.py` to hot-register synthesized tools. The `bridge.py` `on_execution` callback is the sole integration point between the existing codebase and the new learning pipeline. The `mcp/server.py` lifespan function starts the `RegistryWatcher` and wires the bridge hook. No other existing files change.

**Major components:**
1. `forge_bridge/llm/router.py` — async `acomplete()` with sensitivity-based backend selection (local Ollama / cloud Claude); sync `complete()` shim for backwards compatibility
2. `forge_bridge/llm/health.py` — health check for both backends; exposed as `forge://llm/health` MCP resource
3. `forge_bridge/learning/log.py` — JSONL execution log; in-memory count table; promotion trigger returning `(promoted=True, hash, examples[])` to caller
4. `forge_bridge/learning/synthesizer.py` — builds synthesis prompt from examples; calls `llm/router.py` with `sensitive=True` (always local); validates output; writes to `mcp/synthesized/`
5. `forge_bridge/learning/watcher.py` — `asyncio` polling on `mcp/synthesized/`; `importlib` hot-loads new files; calls `mcp/registry.py.register_tools()`
6. `forge_bridge/mcp/registry.py` — owns the mutable tool set; separates static registration (at startup) from dynamic registration (at runtime)

### Critical Pitfalls

1. **Blocking sync LLM calls in async context** — synthesis must use `asyncio.to_thread()` and be scheduled as `asyncio.create_task()` (fire-and-forget). qwen2.5-coder:32b synthesis takes 30–90s and will stall all WebSocket connections if called synchronously.

2. **Code normalisation fails on Python string forms** — regex-based normalisation (direct port of FlameSavant JS) will fail on f-strings, triple-quotes, and raw strings. Use `ast.parse` + `ast.unparse` after replacing `ast.Constant` nodes with a placeholder. Test with at least five known-equivalent and five known-different code pairs.

3. **Synthesized tool overwrites static registry entry** — enforce `synth_*` prefix for all synthesized tools; check against a frozen set of reserved names at synthesis time; never allow synthesized tools to shadow static implementations.

4. **JSONL replay re-triggers synthesis on restart** — use `count == PROMOTION_THRESHOLD` (not `>=`) to prevent re-promotion; store `promoted_at` timestamp in log so replay marks already-promoted hashes and skips synthesis.

5. **Probation passes semantically wrong tools** — for any write-side tool (`readOnlyHint: False`), require human review before graduation. Default synthesized tools to `readOnlyHint: True`; surface `_source: synthesized` in tool description.

---

## Implications for Roadmap

Based on the dependency graph in ARCHITECTURE.md, the build order is fixed by hard dependencies. The phases below follow that graph exactly. Each phase is independently testable and delivers value before the next begins.

### Phase 0: LLM Router Async Promotion

**Rationale:** Everything downstream blocks on this. Synthesizer cannot be async without it. Bridge hook cannot fire synthesis without it. pyproject.toml packaging bug must be fixed here to avoid breaking other consumers.
**Delivers:** `forge_bridge/llm/` package with `AsyncLLMRouter`, async health check, and `llm/prompts.py`; `llm_router.py` replaced by compatibility shim; `pyproject.toml` cleaned up with `[llm]` extra.
**Addresses:** Async completion API (table stakes), optional dependency installation (table stakes), health check endpoint (table stakes).
**Avoids:** Pitfall 3 (blocking async context), Pitfall 7 (synthesis leaking to cloud — hard-code `sensitive=True` here), Pitfall 9 (import errors at runtime — add capability check).

### Phase 1: MCP Server Rebuild with Pluggable API

**Rationale:** Independent of the learning pipeline. Provides `mcp/registry.py` and `register_tools()` API that Phase 3 (watcher) depends on. Right time to establish `flame_*` / `forge_*` / `synth_*` namespace conventions and add Pydantic input validation.
**Delivers:** `mcp/registry.py`; `register_tools(mcp, [fns])` public API in `mcp/__init__.py`; Pydantic input models for existing tools; `synth_*` namespace reserved.
**Addresses:** `register_tools(mcp)` pluggable API (table stakes), Pydantic input models (differentiator), namespace partitioning (differentiator).
**Avoids:** Pitfall 4 (FastMCP static registration — enforce `register_tools()` before `mcp.run()`), Pitfall 8 (race with client connection — `_started` guard flag), Pitfall 2 (synthesized tool collision — reserved name set established here).

### Phase 2: Execution Log and Bridge Hook

**Rationale:** Foundation of the learning pipeline. Self-contained — no LLM calls, no synthesis. Provides the `on_execution` callback point in `bridge.py` and the promotion trigger that Phase 3 (synthesizer) receives.
**Delivers:** `forge_bridge/learning/log.py` (JSONL, in-memory counts, promotion trigger); `bridge.py` `on_execution` optional callback; `~/.forge-bridge/executions.jsonl` storage; startup replay with `promoted_at` guard.
**Addresses:** Execution logging (table stakes), code normalisation (table stakes), promotion counter (table stakes), replay on startup (table stakes), intent tracking (differentiator — add `intent` field here at low cost).
**Avoids:** Pitfall 1 (use `ast.unparse` normalisation, not regex), Pitfall 6 (replay re-promotion — `count == threshold` exactly, `promoted_at` field), Pitfall 10 (JSONL corruption — skip bad lines on replay).

### Phase 3: Skill Synthesizer and Registry Watcher

**Rationale:** Final integration. Requires all three prior phases. This is where the full learning loop closes: execution → log → promotion → synthesis → validation → watcher → hot-registration → probation.
**Delivers:** `forge_bridge/learning/synthesizer.py`; `forge_bridge/learning/watcher.py`; `mcp/synthesized/` directory (gitignored); probation tracking integrated into `log.py`; synthesized tools appearing live in MCP tool list under `synth_*` prefix.
**Addresses:** Skill synthesis (table stakes), synthesized tool validation (table stakes), dynamic MCP registration (table stakes), probation tracking (table stakes), `_source` tagging (differentiator), synthesis prompt with intent (differentiator).
**Avoids:** Pitfall 2 (synth_* namespace, reserved name check), Pitfall 5 (human review gate for write-side tools), Pitfall 11 (cap examples at 500 tokens each in synthesis prompt), Pitfall 12 (strict prefix separation, hide synthesized tools until probation passed).

### Phase Ordering Rationale

- Phase 0 before all others: `LLMRouter.acomplete()` is a hard dependency for the synthesizer; blocking LLM calls in an async context are a showstopper that gets worse the later it is addressed.
- Phase 1 before Phase 3: `mcp/registry.py` and `register_tools()` must exist before the watcher can hot-register synthesized tools. Also establishes namespace conventions that Phases 2 and 3 enforce.
- Phase 2 before Phase 3: The synthesizer is triggered by `promoted=True` from the execution log. Phase 3 cannot wire its inputs without Phase 2 existing.
- Probation in Phase 3 (not Phase 2): Probation counters live in the log but only have meaning after synthesized tools exist. Implement probe hooks alongside the tools they track.

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 0:** `AsyncOpenAI` and `AsyncAnthropic` confirmed in installed sources. Direct promotion of existing `llm_router.py`. No ambiguity.
- **Phase 2:** FlameSavant is the primary reference and has been fully read. `ast.unparse` normalisation is established Python idiom. JSONL append-only log is a standard pattern.

Phases that may benefit from deeper research during planning:
- **Phase 1:** FastMCP's handling of `notifications/tools/list_changed` is confirmed at the protocol level (MCP spec 2024-11-05) but FastMCP's implementation is unverified. Check `mcp/server/fastmcp/server.py` for whether `list_changed` notifications are sent automatically when `add_tool()` is called at runtime. This determines whether downstream consumers see dynamically added tools without a reconnect.
- **Phase 3:** The probation graduation criteria for write-side tools (human review gate) needs a concrete implementation decision before planning: UI notification, approval MCP tool, or log-only gate.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages confirmed from installed sources; stdlib sufficiency verified; no external docs needed |
| Features | MEDIUM | Based on FlameSavant source (direct read) and in-repo code; no external benchmarking against similar tools |
| Architecture | HIGH | Component boundaries and data flow derived from existing codebase analysis + FlameSavant reference; dependency graph is explicit |
| Pitfalls | HIGH | Pitfalls 1–9 have direct source evidence (code analysis, FlameSavant comparison); Pitfalls 10–12 are well-founded inferences from analogous systems |

**Overall confidence:** HIGH

### Gaps to Address

- **FastMCP `tools/list_changed` notification behaviour:** Confirmed at protocol level but unverified in installed FastMCP implementation. Check during Phase 1 planning to determine whether hot-registered synthesized tools appear without a client reconnect.
- **Probation human review gate implementation:** The pitfall analysis identifies human review as required for write-side synthesized tools, but the concrete mechanism (approval MCP tool, log-only gate, UI notification) is unspecified. Resolve before Phase 3 planning.
- **qwen2.5-coder:32b synthesis latency on `assist-01:11434`:** Estimated 30–90s from general model knowledge. Actual latency on the local instance is unverified. Relevant for deciding whether fire-and-forget synthesis is sufficient or whether progress feedback is needed.

---

## Sources

### Primary (HIGH confidence)
- Installed MCP SDK: `.venv/lib/python3.13/site-packages/mcp/` — `add_tool()`, `remove_tool()`, protocol version
- Installed openai SDK: `.venv/lib/python3.13/site-packages/openai/` — `AsyncOpenAI` confirmed, version 2.29.0
- Installed anthropic SDK: `.venv/lib/python3.13/site-packages/anthropic/` — `AsyncAnthropic` confirmed, version 0.86.0
- Installed pydantic: `.venv/lib/python3.13/site-packages/pydantic/version.py` — version 2.12.5
- FlameSavant source (read directly): `ExecutionLog.js`, `SkillSynthesizer.js`, `RegistryWatcher.js` — primary design reference
- In-repo: `forge_bridge/llm_router.py`, `forge_bridge/mcp/server.py`, `pyproject.toml`, `.planning/codebase/CONCERNS.md`
- In-repo: `.planning/PROJECT.md` — authoritative scope definition

### Secondary (MEDIUM confidence)
- `.planning/codebase/ARCHITECTURE.md` — existing system architecture (generated 2026-04-14, derived from codebase)
- `.planning/codebase/STRUCTURE.md` — existing directory layout
- `projekt-forge/forge_bridge/tools/reconform.py` — Pydantic model usage patterns

### Tertiary (inferred)
- qwen2.5-coder:32b synthesis latency estimate (30–90s) — inferred from model size; not measured on `assist-01:11434`

---
*Research completed: 2026-04-14*
*Ready for roadmap: yes*
