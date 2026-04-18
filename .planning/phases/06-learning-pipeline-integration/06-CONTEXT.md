# Phase 6: Learning Pipeline Integration - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire forge-bridge's learning pipeline into projekt-forge's infrastructure so:

- Synthesis routes to projekt-forge's configured Ollama instance (not forge-bridge's default)
- Execution logs persist to projekt-forge's DB in addition to the JSONL log
- Generated prompts carry projekt-forge's project context (active shot, roles, naming conventions, etc.)
- Two forge-bridge processes can run concurrently without cross-contaminating promotion counts

**In scope (LRN-01..04):**
- Two small additive hook APIs in forge-bridge (`ExecutionLog.set_storage_callback`, `SkillSynthesizer(pre_synthesis_hook=...)`)
- Consumer-side wiring in projekt-forge's `__main__.py` that reads `forge_config.yaml`, constructs an `LLMRouter`, injects into `SkillSynthesizer`, and registers the storage callback

**Out of scope (deferred):**
- EXT-03 SQL persistence backend for ExecutionLog — deferred to v1.1.x per 2026-04-18 decision. Phase 6 stays JSONL + callback; consumers bring their own storage.
- EXT-02 Tool provenance in MCP annotations — future. The LRN-04 hook's `tags` field is designed so EXT-02 can consume them later without retrofitting.
- Hot-reload of `forge_config.yaml` — restart required for config changes in v1.1.

</domain>

<decisions>
## Implementation Decisions

### LRN-02 — Storage callback on ExecutionLog

- **D-01:** Single callback registered via `ExecutionLog.set_storage_callback(fn)`. Not a list, not separate hooks for record-vs-promotion. One hook, one purpose.
- **D-02:** Fires on every `.record()` call, immediately after the JSONL append succeeds. Not on promotion events (those stay internal to ExecutionLog's counts for now).
- **D-03:** Callback receives the full `ExecutionRecord` dataclass — not a subset, not just a slug/hash. Consumer decides what fields to persist.
- **D-04:** Signature accepts both sync and async: `Callable[[ExecutionRecord], None | Awaitable[None]]`. Dispatch mode (sync vs async) is detected once at `set_storage_callback()` time via `inspect.iscoroutinefunction(fn)` and stored; per-call dispatch uses the stored tag with no re-inspection.
- **D-05:** Async callbacks fire-and-forget via `asyncio.ensure_future`; errors surface through `add_done_callback` logging. Sync callbacks execute synchronously. Both modes isolate exceptions — a failing callback never breaks the JSONL write (caught, logged as warning, discarded). The log is source-of-truth; the callback is a best-effort mirror.
- **D-06 (usage constraint):** Registering an async callback requires `.record()` to be called from a running event loop. Documented in the `set_storage_callback` docstring. No runtime check at registration; `asyncio.ensure_future` raises `RuntimeError` at call time if no loop exists.

### LRN-04 — Pre-synthesis hook on SkillSynthesizer

- **D-07:** Constructor param: `SkillSynthesizer(pre_synthesis_hook: PreSynthesisHook | None = None)`. Type alias: `PreSynthesisHook = Callable[[str, dict], Awaitable[PreSynthesisContext]]`.
- **D-08:** Hook signature is **async only** (not sync-or-async union). Rationale: pre-synthesis context will come from projekt-forge's DB via SQLAlchemy async session; forcing async at the contract level avoids accidental blocking-in-sync-wrapper patterns.
- **D-09:** Hook is invoked with `(intent: str, params: dict)` — the same two values the synthesizer already has internally. No new upstream data plumbing required.
- **D-10:** Hook returns `PreSynthesisContext` — a frozen dataclass, NOT a plain string. Four fields:
  ```python
  @dataclass(frozen=True)
  class PreSynthesisContext:
      extra_context: str = ""                              # freeform prose appended to system prompt
      tags: list[str] = field(default_factory=list)        # "key:value" (K8s label convention); flows to MCP annotations (EXT-02) later
      examples: list[dict] = field(default_factory=list)   # few-shot pairs: [{"intent": "...", "code": "..."}, ...]
      constraints: list[str] = field(default_factory=list) # hard rules, e.g. "do not import flame"
  ```
  All fields default to empty. Consumers populate only what they need.
- **D-11:** The hook is **additive only**. Synthesizer owns final prompt assembly; the hook contributes content but cannot replace the base prompt. `extra_context` appends to the system prompt; `constraints` inject near the rules section; `examples` wrap as few-shot blocks; `tags` attach to synthesized tool metadata (not to the LLM call itself — they're for bookkeeping).
- **D-12:** Frozen dataclass, not Pydantic. Reason: internal structural type passed between two async functions, no JSON boundary, no runtime validation value. Zero new dependencies. (Pydantic is available in forge-bridge but unnecessary here.)

### LRN-03 — LLMRouter construction in projekt-forge

- **D-13:** Build `LLMRouter` once at startup inside projekt-forge's `__main__.py`, read values from `forge_config.yaml` (not env vars in production, though env fallback is preserved for dev). Inject into `SkillSynthesizer(router=router)` when the synthesizer is constructed. Matches the Phase 4 constructor-injection pattern end-to-end.
- **D-14:** Restart required for `forge_config.yaml` changes. Hot-reload is explicitly out-of-scope for v1.1. Acceptable tradeoff: forge-config changes during dev are rare; production restarts are cheap.

### LRN-01 — ExecutionLog log path

- **D-15:** Already essentially implemented. `ExecutionLog.__init__(log_path: Path = LOG_PATH)` has been constructor-configurable since Phase 3. No new forge-bridge API needed for LRN-01. Phase 6's LRN-01 work is pure consumer-side: projekt-forge constructs `ExecutionLog(log_path=...)` with a per-project path during startup.
- **D-16:** Per-process log isolation handled by naming discipline, not by bridge machinery. Standalone forge-bridge defaults to `~/.forge-bridge/executions.jsonl`; projekt-forge passes `$FORGE_PROJECT_ROOT/.forge/executions.jsonl` or similar per-project path. Different paths → no contention → success criterion #1 met with zero new code. Same-path concurrent writes remain **explicitly unsupported** unless/until a future requirement justifies the cost of file locking or shared-log coordination.

### Claude's Discretion

- **Internal formatting of PreSynthesisContext into the final prompt.** Synthesizer decides exactly where `constraints` vs `examples` vs `extra_context` land in the prompt structure. Suggested approach: system prompt = base + constraints block; user message = intent + params + examples as few-shot; tags attach to the synthesized tool as `_synthesized_tags` attribute for later inspection. Planner may adjust structure during implementation.
- **Whether `set_storage_callback(None)` clears the callback.** Recommend yes (symmetric unset), but it's a small API nicety — planner's call.
- **Exact `logger.warning` message text** on callback failure. Just make it grep-able.

### Folded Todos

None — no pending todos matched Phase 6 at discussion time.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap

- `.planning/REQUIREMENTS.md` §"Learning Pipeline" (LRN-01 through LRN-04, lines 33-36)
- `.planning/REQUIREMENTS.md` §"Future Requirements" (EXT-02, EXT-03 — explicitly deferred but the tags field in D-10 is designed to feed EXT-02 later)
- `.planning/ROADMAP.md` §"Phase 6: Learning Pipeline Integration" (goal + success criteria, lines 63-72)

### Phase 5 (prior)

- `.planning/phases/05-import-rewiring/05-CONTEXT.md` — disposition decisions and client-layer preservation that affect how projekt-forge's `__main__.py` hooks into the lifespan. Particularly D-09b (client layer stays in projekt-forge) and D-14 (canonical lifespan owns `startup_bridge`/`shutdown_bridge`) shape where the new wiring calls go.
- `.planning/phases/05-import-rewiring/05-04-SUMMARY.md` — RWR-04 guard semantics. Phase 6 consumer-side changes in projekt-forge will run under the same pytest guard; any new forge_bridge import must still resolve to site-packages.

### Phase 4 (prior)

- `.planning/phases/04-api-surface-hardening/04-CONTEXT.md` — injection-pattern precedent. Phase 6's LLMRouter/Synthesizer wiring follows the same constructor-injection model Phase 4 established.
- `.planning/phases/04-api-surface-hardening/04-PATTERNS.md` — reference for how new additive APIs (hooks, callbacks) were layered onto existing classes in Phase 4.

### Current implementation (read before modifying)

- `forge_bridge/learning/execution_log.py` — `ExecutionLog` current shape. Constructor takes `log_path` and `threshold`; no storage-callback plumbing exists yet. Phase 6 adds `set_storage_callback()` and a dispatch path inside whatever `.record()` is called.
- `forge_bridge/learning/synthesizer.py` — `SkillSynthesizer` current shape. Already accepts `router=` injection. Phase 6 adds `pre_synthesis_hook=` constructor param and a call site before the LLM `acomplete()`.
- `forge_bridge/llm/router.py` — `LLMRouter` constructor API (Phase 4). No changes needed in forge-bridge; projekt-forge consumes it.
- `forge_bridge/bridge.py` lines 45-51, 162-164 — existing `set_execution_callback` for the **Flame bridge** (different callback; fires on every `execute()` sent to Flame). Not related to LRN-02, but worth reading as a precedent for how module-level callbacks are shaped in this codebase. **Do not confuse with LRN-02**, which is on `ExecutionLog`, not `bridge.py`.

### projekt-forge side (read for consumer wiring)

- `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__main__.py` — where the LLMRouter construction and synthesizer wiring lands. Already has `_run_mcp_only(args)` helper from Phase 5 Wave C; Phase 6 adds the learning-pipeline init alongside.
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_config.yaml` (path TBD by planner — projekt-forge owns the schema). Source of `local_url`, `local_model`, `system_prompt` values for LLMRouter construction.
- `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/config/` (if present) or wherever projekt-forge reads forge_config.yaml today. Planner should locate this and use its existing loader rather than adding a new one.
- `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/db/` — storage callback target. Planner identifies the right table/service for writing `ExecutionRecord` rows.

### Tooling

- `inspect.iscoroutinefunction` (Python stdlib) — used for D-04 registration-time dispatch detection.
- `asyncio.ensure_future` + `add_done_callback` (Python stdlib) — D-05 async dispatch mechanism.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ExecutionLog.__init__(log_path=..., threshold=...)`** (`forge_bridge/learning/execution_log.py` line 63): already constructor-configurable. LRN-01 satisfied at bridge level; Phase 6 just adds `set_storage_callback()`.
- **`SkillSynthesizer(router=...)`** (`forge_bridge/learning/synthesizer.py` line 206): already accepts router injection. LRN-03 bridge-side surface is in place; Phase 6 adds `pre_synthesis_hook=` alongside.
- **`LLMRouter(local_url=..., local_model=..., system_prompt=...)`** (`forge_bridge/llm/router.py` line 79): constructor injection with env fallback was delivered in Phase 4 (API-02). No forge-bridge changes needed; projekt-forge consumes directly.
- **`asyncio.ensure_future` + `add_done_callback` pattern**: used in existing code for fire-and-forget async dispatch. New LRN-02 dispatch follows the same pattern.

### Established Patterns

- **Constructor injection with env fallback** (Phase 4 pattern): all public classes accept explicit config and fall back to env vars. Phase 6 extends this: new hook params (`pre_synthesis_hook`, the callback registration) accept explicit function references with `None` as the no-op default.
- **Callback-on-class via setter method** (`set_execution_callback` in `bridge.py`): existing precedent for registering a single callable post-construction. LRN-02's `set_storage_callback` mirrors this shape.
- **Frozen dataclasses for internal structural types**: used across the codebase for message types (`forge_bridge/server/protocol.py` `Message`). `PreSynthesisContext` follows the same convention.
- **Single source of truth, best-effort mirrors**: Phase 4's `register_tools(source="builtin")` gives MCP tools a provenance tag; JSONL is the analogous single-source-of-truth for executions, with the new storage callback as a best-effort mirror.

### Integration Points

- **projekt-forge `__main__.py`** is the single wiring point for all Phase 6 consumer-side work. Phase 5 Wave C already rebuilt it around the canonical lifespan; Phase 6 adds ~30-50 lines there (router construction, synthesizer config, callback registration).
- **`forge_config.yaml` loader in projekt-forge** — wherever it lives today is where LRN-03's router config comes from. Planner discovers the existing path during research rather than inventing a new loader.
- **projekt-forge DB layer** — LRN-02's storage callback writes here. Planner identifies the right session factory / table / service during research.

</code_context>

<specifics>
## Specific Ideas

- **Tags field in `PreSynthesisContext`** uses the Kubernetes label convention: `"key:value"` strings in a list. Examples: `"project:ACM_12345"`, `"tool:batch_render"`, `"shot:SHOT_010"`. Consistent, parseable, forward-compatible with EXT-02 (MCP tool provenance annotations).
- **"The JSONL log is source-of-truth; the callback is a best-effort mirror"** — framing that should survive into the `set_storage_callback` docstring and user-facing docs. Makes the isolation semantic easy to reason about and gives consumers permission to design their DB writes as append-only/idempotent.

</specifics>

<deferred>
## Deferred Ideas

- **Promotion-event callback** — a second hook that fires only when ExecutionLog promotes a pattern to a synthesized tool. Phase 6 success criterion is per-execution, not per-promotion. If a consumer actually needs it later, add `set_promotion_callback()` as a focused v1.1.x change.
- **Hot-reload of `forge_config.yaml`** — LLMRouter is built once at startup; config changes require restart. Adding a reload mechanism is a real feature, not a bug fix, and belongs in a future phase.
- **Full prompt replacement via pre_synthesis_hook** — additive-only is the locked design (D-11). If a consumer needs fully custom prompts, that's effectively "bring your own synthesizer", which is a bigger architecture question than a hook extension.
- **SQL persistence backend for ExecutionLog (EXT-03)** — deferred to v1.1.x per 2026-04-18 decision. Stays documented in `.planning/REQUIREMENTS.md`.
- **Tool provenance in MCP annotations (EXT-02)** — deferred, but LRN-04's `tags` field is designed to feed it trivially when the time comes.
- **Synchronous-only enforcement via type system** — LRN-02 accepts sync OR async; LRN-04 is async-only. The asymmetry is deliberate (LRN-02 has many natural sync consumers like stdout loggers; LRN-04 will always talk to async DBs). No further convergence planned.

### Reviewed Todos (not folded)

None — no todos surfaced during the todo match step.

</deferred>

---

*Phase: 06-learning-pipeline-integration*
*Context gathered: 2026-04-18*
