# Phase 6: Learning Pipeline Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 06-learning-pipeline-integration
**Areas discussed:** Storage-callback shape (LRN-02), Pre-synthesis hook contract (LRN-04), LLMRouter construction in projekt-forge (LRN-03), Cross-process log isolation (LRN-01 operational)

---

## Storage-callback shape (LRN-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Single `on_record` hook | One callback, fires on every `.record()` call, passes full `ExecutionRecord` | ✓ |
| Separate `on_record` + `on_promotion` hooks | Two hooks for different use cases | |
| Promotion-only hook | Only fires when pattern → synthesized tool | |
| Subset of `ExecutionRecord` (slug + hash) | Minimal callback payload | |

**User's choice:** Single hook, full `ExecutionRecord`, may be sync or async, callback failure does not break primary flow.

**Notes:**
- Accepted Claude's recommendation for single-hook minimal surface. The Phase 6 success criterion is per-execution, not per-promotion.
- User proposed signature accepting sync-or-async union: `Callable[[ExecutionRecord], None | Awaitable[None]]`. Claude accepted with two refinements: dispatch mode detected once at `set_storage_callback()` registration via `inspect.iscoroutinefunction`, and errors isolated so a failing callback never breaks the JSONL write. Async callbacks fire-and-forget via `asyncio.ensure_future` with `add_done_callback` for error logging.
- Promotion-event hook deferred to v1.1.x if a consumer actually needs it.

---

## Pre-synthesis hook contract (LRN-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Returns a string to append to system prompt | Simple, consumer formats its own prose | |
| Returns structured `PreSynthesisContext` dataclass | Synthesizer formats each field appropriately (context vs examples vs constraints vs tags) | ✓ |
| Returns a full prompt replacement | Consumer takes over prompt construction | |
| Sync callable | No await in hook | |
| Async callable | Supports async DB lookups | ✓ |

**User's choice:** Async hook returning structured `PreSynthesisContext`, additive-only (not full replacement).

**Notes:**
- Claude initially recommended plain-string return. User countered with structured type proposal citing tags, examples, constraints as distinct categories.
- Claude accepted the counter-proposal; structured return is better for three reasons: (1) examples deserve few-shot formatting distinct from prose context, (2) tags enable EXT-02 tool provenance trivially later, (3) constraints are assertions that belong near system-prompt rules, not mushed into freeform prose.
- Shape locked as frozen dataclass (not Pydantic): `extra_context: str`, `tags: list[str]` (K8s `key:value` convention), `examples: list[dict]`, `constraints: list[str]`. All default to empty.
- "Additive-only" constraint locked: synthesizer owns final prompt assembly; hook contributes but cannot replace.

---

## LLMRouter construction in projekt-forge (LRN-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Build at startup in `__main__.py`, inject once | Explicit DI, restart-to-reload | ✓ |
| Lazy per-call inside synthesizer | Reads config every synthesis; more dynamic | |
| Module-level singleton with `configure()` entry point | Matches existing `bridge.configure()` pattern but adds coupling | |

**User's choice:** Build once at startup from forge_config.yaml, inject into synthesizer, restart required for config changes.

**Notes:**
- Unanimous choice. Mirrors Phase 4's constructor-injection pattern. Hot-reload is a hypothetical future requirement, not a Phase 6 one.
- `__main__.py` already rewired in Phase 5 Wave C (`_run_mcp_only` helper) — natural home for Phase 6 router construction.

---

## Cross-process log isolation (LRN-01 operational)

| Option | Description | Selected |
|--------|-------------|----------|
| Consumer passes explicit per-process `log_path` | Naming discipline; zero bridge changes | ✓ |
| Auto-append PID to filename | Magic; breaks cross-run replay invariant | |
| Advisory file locking (fcntl/msvcrt) | Cross-platform complexity | |
| Document-unsupported, no mechanism | Fails success criterion #1 | |

**User's choice:** Explicit consumer-owned log path strategy. Same-path concurrent writes explicitly unsupported unless later designed intentionally.

**Notes:**
- Claude recommended (a); user affirmed.
- Rejected PID-suffix because ExecutionLog's JSONL-replay-on-startup rebuilds promotion counts; changing the filename per run would prevent aggregation.
- Rejected file locking for cross-platform complexity versus v1.1 value.

---

## Claude's Discretion

- Internal formatting of `PreSynthesisContext` into the final prompt (where to place constraints vs examples vs extra_context in the prompt structure).
- Whether `set_storage_callback(None)` clears the callback (recommend yes, symmetric unset).
- Exact `logger.warning` message text on callback failure.

## Deferred Ideas

- **Promotion-event callback** — focused v1.1.x change if a consumer needs it.
- **Hot-reload of `forge_config.yaml`** — future phase.
- **Full prompt replacement via pre_synthesis_hook** — conflicts with additive-only design.
- **SQL persistence backend for ExecutionLog (EXT-03)** — deferred to v1.1.x per 2026-04-18 scoping decision, logged in STATE.md Decisions.
- **Tool provenance in MCP annotations (EXT-02)** — deferred, but LRN-04's `tags` field is designed to feed it.
