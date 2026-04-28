# Phase 15 (FB-C): LLMRouter Tool-Call Loop — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 15-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 15-fb-c-llmrouter-tool-call-loop
**Areas discussed:** Sanitization module location, Public API surface growth, Tool registry invocation contract, Per-turn observability
**Tactical defaults locked inline (skipped from interactive discussion per user reco-acceptance):** Ollama allow-list strictness, Cloud model bump, Anthropic strict mode, Live integration test policy, Ollama keep_alive, SystemExit defense

---

## Initial Gray-Area Selection

After loading prior context (PROJECT.md, REQUIREMENTS.md, STATE.md, prior CONTEXT files for Phases 13/14, FB-C research) and scouting the LLM router/synthesizer/sanitization code, presented 10 candidate gray areas to the user.

User asked for recommendations. Claude recommended discussing 4 (high-stakes, not pre-decided elsewhere) and locking 6 inline with research-recommended defaults. User confirmed.

**Discussed:** Areas 4, 5, 6, 8.
**Locked inline (no discussion):** Areas 1, 2, 3, 7, 9, 10.

---

## Area 4 — Sanitization Module Location

### 4a. Where do shared patterns live?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `forge_bridge/_sanitize_patterns.py` | Top-level, neutral between `learning/` and `llm/` | ✓ |
| (b) New package `forge_bridge/sanitize/__init__.py` | New package home | |
| (c) Keep at `learning/sanitize.py`, llm imports from there | No hoist | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Top-level neutral home; minimum coupling; matches STATE.md "single source of truth" mandate without forcing `llm/` to depend on `learning/`.

### 4b. What gets hoisted?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Patterns + `_CONTROL_CHAR_RE` only | Helpers stay in consumer modules | ✓ |
| (b) Full helpers move too (one module owns all sanitization) | Bigger hoist | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Phase 7 `_sanitize_tag()` and FB-C `_sanitize_tool_result()` have different rejection semantics (drop vs replace). Different consumers need different helpers; only the patterns are shared. Zero behavior change to Phase 7 watcher/registry code.

### 4c. What happens to existing `learning/sanitize.py`?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Becomes a thin re-export shim for backward compat | No caller updates needed | ✓ |
| (b) Hard cut — update all callers | More churn | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Two known callers (`learning/watcher.py:17`, `mcp/registry.py:90`) need ZERO updates if patterns re-export from old location. Lower diff size, lower regression risk.

---

## Area 5 — Public API Surface Growth

### 5a. Which exceptions to export from `forge_bridge.__all__`?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `LLMLoopBudgetExceeded` only (16→17, roadmap-locked) | Minimal growth | |
| (b) All three (`LLMLoopBudgetExceeded` + `RecursiveToolLoopError` + `LLMToolError`, 16→19) | Full discrimination | ✓ |
| (c) Budget + Recursive only (16→18) | Mid-ground | |

**User's choice:** (b) — accepted Claude's reco.
**Rationale:** FB-D needs to map each to a different HTTP status (504, 500, 502). Without exports, FB-D catches `RuntimeError` and loses the discrimination — regression vs. Phase 4's "explicit catchable contracts" precedent and Phase 8's `StoragePersistence` export pattern.

### 5b. Where do exception classes live?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `forge_bridge/llm/router.py` alongside `LLMRouter` | Module cohesion | ✓ |
| (b) New `forge_bridge/llm/_errors.py` | Separate errors module | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Matches Phase 8 precedent (`StoragePersistence` lives in `learning/storage.py` next to `ExecutionLog`, not a separate `_errors.py`).

### 5c. `complete_with_tools()` itself — public method or private?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Public method on `LLMRouter` | Symmetric with `acomplete()` | ✓ |
| (b) Module-level function `complete_with_tools(router, ...)` | Standalone | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Symmetric with existing `LLMRouter.acomplete()` and `LLMRouter.complete()`. No surprise for callers familiar with the router API.

---

## Area 6 — Tool Registry Invocation Contract

### 6a. `tool_executor` callable signature

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `async (tool_name: str, args: dict) -> str` | Coordinator handles stringification | ✓ |
| (b) `async (tool_name: str, args: dict) -> Any` | Caller stringifies | |
| (c) `async (tool_call: ToolCall) -> ToolCallResult` | Full canonical types | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Matches research §4.1 skeleton. Coordinator owns sanitization, truncation, error wrapping — executor stays a simple `name + args → text` function.

### 6b. Default executor location

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `forge_bridge/mcp/registry.py::invoke_tool(name, args)` — public | Importable everywhere | ✓ |
| (b) Private `_invoke_tool` + lazy-import inside coordinator | Hidden | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Importable by FB-D, by tests, by future external consumers. Matches existing `forge_bridge.mcp.registry.register_tools()` public-function pattern.

### 6c. What does the loop receive in the `tools=[...]` arg?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `list[mcp.types.Tool]` — the existing forge-bridge type | Roadmap text verbatim | ✓ |
| (b) `dict[str, Callable]` — pre-bound name→function map | Caller wires it | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Matches roadmap text verbatim. Coordinator extracts schema fields for adapter translation; the executor looks up by name. Minimum coupling.

### 6d. Empty `tools=[]` degenerate case

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Raise `ValueError("complete_with_tools requires at least one tool; use acomplete() for plain completion")` | Defensive | ✓ |
| (b) Fall through to `acomplete()` | Treat as plain completion | |
| (c) Send the request anyway; LLM returns text-only on first turn | Pass-through | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Defensive boundary; no silent semantic shift between `complete_with_tools(prompt, tools=[])` and `acomplete(prompt)`. If a caller wants plain completion, they should call `acomplete()` explicitly.

---

## Area 8 — Per-Turn Observability

### 8a. Log level + fields per turn

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `logger.info(...)` per turn with structured fields (iter, tool_name, args_hash, prompt_tokens, completion_tokens, elapsed_ms, terminal_reason) | Visible in production | ✓ |
| (b) `logger.debug(...)` per turn | Silent unless caller flips log level | |
| (c) Single aggregated `logger.info(...)` at session end only | Minimal | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Production deployments see it without log-level gymnastics. Per-turn granularity is the unit ops triage needs.

### 8b. Format style

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Key-value space-delimited (`tool-call iter=1 tool=foo elapsed_ms=42`) | Matches Phase 8 LRN-05 + Phase 9 console log shape | ✓ |
| (b) JSON line per turn | Better for log shipping, harder to read in dev | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** Greppable single-line format consistent with Phase 8 LRN-05 and Phase 9 console handlers. Existing log-shipping infra can extract fields with a tail+parse step if needed.

### 8c. Final-state log on success/error

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Always emit terminal log line at session end | One line per session = ops unit | ✓ |
| (b) Only on error path | Quieter | |
| (c) Skip — per-turn lines are sufficient | Minimal | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** One terminal line per session is the operational unit. Lets ops queries like "how long did session X take and why did it end" be a single grep.

### 8d. ExecutionLog integration?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) No — ExecutionLog is for `bridge.execute()` calls; tool-loop is separate concern | Keep Phase 6/8 boundary clean | ✓ |
| (b) Yes — fire an ExecutionLog record per loop session | Tighter integration | |
| (c) Optional callback hook — let FB-D wire it later | Deferred | |

**User's choice:** (a) — accepted Claude's reco.
**Rationale:** ExecutionLog (LRN-05) is for `bridge.execute()` — the persistence-mirror surface for synthesized tool runs. Tool-loop is its own observability concern. Tool calls inside the loop that hit `bridge.execute()` will still write ExecutionLog records via the existing Phase 6 hook — no double-counting at the loop level.

---

## Locked Defaults — Tactical Group (no interactive discussion; recos accepted inline)

| # | Decision | Selected | Rationale |
|---|----------|----------|-----------|
| 1 | Ollama tool-model allow-list strictness | **SOFT warn** | Artist-experimentation friendly; production env vars are deterministic |
| 2 | Cloud model default | **Stay on `claude-opus-4-6`** | SEED-CLOUD-MODEL-BUMP-V1.4.x for the bump; mirrors local-model conservative pattern |
| 3 | Anthropic `strict: true` policy | **Always-on with per-tool sticky downgrade fallback** | Zero-cost win when it works; per-tool fallback covers unknown blast radius |
| 7 | Live integration test policy | **Env-gated `FB_INTEGRATION_TESTS=1` (+ `ANTHROPIC_API_KEY` for cloud)** | Matches Phase 8 pattern verbatim |
| 9 | Ollama `keep_alive` on tool-call requests | **Set `"10m"`** | Eliminates 30s reload cliff mid-loop; zero cost (research §6.8) |
| 10 | SystemExit defense in coordinator | **`except (Exception, SystemExit)` belt-and-suspenders** | Belt-and-suspenders against pre-existing tools that might call `os._exit`/`sys.exit` despite synthesizer blocklist (research §6.6) |

---

## Claude's Discretion (deferred to planner)

- Exact filename split: single `_adapters.py` vs separate `_anthropic_adapter.py` + `_ollama_adapter.py` files (planner picks based on adapter LOC; research estimates ~80 LOC each)
- Whether dataclasses (`_TurnResponse`, `_ToolCall`, `ToolCallResult`) live in `_adapters.py` or a separate `_types.py` (planner decides based on import-cycle considerations)
- Test fixture placement for the stub adapter (likely `tests/llm/conftest.py`)
- Whether to add a `--no-skip-llm-integration` pytest flag in addition to the env var (not required; env var is sufficient and matches Phase 8)
- Exact wording of the synthetic repeat-call message string in D-07 (planner can polish; substance is locked)
- Exact `args_hash` algorithm beyond "8-hex sha256 prefix of `json.dumps(args, sort_keys=True)`" (planner can use existing `hashlib` patterns)

## Deferred Ideas

- Default Ollama tool model bump → SEED-DEFAULT-MODEL-BUMP-V1.4.x
- Default cloud model bump → SEED-CLOUD-MODEL-BUMP-V1.4.x
- Parallel tool execution → SEED-PARALLEL-TOOL-EXEC-V1.5
- Cross-provider sensitive fallback → SEED-CROSS-PROVIDER-FALLBACK-V1.5
- True message-history pruning → SEED-MESSAGE-PRUNING-V1.5
- Tool examples (Anthropic `input_examples`) → SEED-TOOL-EXAMPLES-V1.5
- Claude Managed Agents memory → SEED-CMA-MEMORY-V1.5+
- Anthropic `tool_runner()` beta helper adoption — REJECTED, no SEED
- OpenAI compatibility shim for Ollama tool calls — REJECTED, no SEED
- Streaming responses in `complete_with_tools()` — coordinator wrap-able without API change, no SEED
- Programmatic per-session token counter API — log-only in v1.4
- Sync wrapper `complete_with_tools_sync()` — no precedent for sync agentic loop
