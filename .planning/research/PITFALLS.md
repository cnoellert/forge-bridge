# Domain Pitfalls

**Domain:** Learning pipeline + LLM router + pluggable MCP server added to existing Python async middleware
**Researched:** 2026-04-14
**Confidence:** HIGH (based on direct codebase analysis, FlameSavant JS source review, and known failure modes in the existing CONCERNS.md)

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

---

### Pitfall 1: Code Normalisation Too Aggressive or Too Weak

**What goes wrong:** The ExecutionLog uses a normalisation function to hash code for promotion counting. In FlameSavant, it strips all string and numeric literals to create a structural fingerprint. Porting to Python naively gets this wrong in both directions:
- Too aggressive (strip all identifiers): different operations hash to the same bucket, triggering synthesis of a meaningless "averaged" tool that does nothing useful.
- Too weak (no normalisation): identical logic with different shot names or paths never accumulates enough count to promote, defeating the entire system.

**Why it happens:** Python string literals are more varied than JS (triple-quotes, f-strings, raw strings, multiline). A regex-based normaliser that works on JS doesn't handle Python's quoting forms. Also: Flame API code often uses variable names as discriminators (`lib.name == 'ACM'` vs `segment.name == 'ACM'`) — stripping literals loses the structural intent.

**Consequences:** Learning pipeline either promotes garbage or never promotes anything. The entire auto-skill feature silently fails.

**Prevention:**
- Use Python's `ast` module for normalisation rather than regex. Walk the AST, replace `ast.Constant` nodes with a placeholder, reserialise with `ast.unparse`. This handles all string forms correctly and ignores whitespace by definition.
- Test normalisation against at least five known-equivalent code pairs and five known-different pairs before wiring to promotion.
- Keep examples stored (as FlameSavant does) so you can verify the promotion bucket contains genuinely similar operations before synthesis runs.

**Warning signs:** All promotions cluster on a single hash, or no hashes ever reach threshold after many executions.

**Phase:** Learning pipeline implementation (Phase 2).

---

### Pitfall 2: Synthesized Tool Immediately Overwrites Working Registry Entry

**What goes wrong:** SkillSynthesizer writes the synthesized tool file and RegistryWatcher picks it up. If synthesis produces a tool with the same name as an existing built-in or previously-synthesized tool, the registry entry is silently replaced. FlameSavant protects against this by appending a timestamp suffix — but the port may drop that guard. In the Python/MCP context this is worse: a synthesized tool registered under an existing `flame_*` or `forge_*` name will shadow the hand-written implementation for all downstream LLM consumers without any warning.

**Why it happens:** Name collision detection requires knowing the full current registry at write time. If the synthesizer runs asynchronously (as it does in FlameSavant — `synthesis.catch(() => {})`) the registry may have changed between synthesis start and file write.

**Consequences:** A working Flame tool stops working. The LLM gets a synthesized, unvalidated version of a previously stable tool. This is a deployed production regression.

**Prevention:**
- Synthesized tools go into a dedicated namespace: `synth_*` prefix, separate directory from `flame_*` / `forge_*` tools.
- Before writing, check the full registry (including static tools) for name collisions. Raise, don't silently suffix.
- Never allow synthesized tools to shadow tools registered by the static `server.py` registration block. Enforce this by checking the name against a frozen set of reserved names at synthesis time.
- Probation system (track success/failure) must be implemented before synthesized tools are surfaced to MCP consumers.

**Warning signs:** A `flame_*` tool starts returning different output format. `git diff` on the tools directory shows files with `_synth_` in the name.

**Phase:** Learning pipeline + pluggable MCP server (Phases 2–3).

---

### Pitfall 3: Async/Sync Boundary in LLM Router Breaks the Async Middleware

**What goes wrong:** The existing `LLMRouter.complete()` is synchronous — it blocks the calling thread. The synthesis pipeline and learning hooks will be wired into `bridge.py`, which is async. Calling a blocking LLM completion from inside an async handler without `asyncio.to_thread()` or an async wrapper will block the entire event loop, stalling all WebSocket connections to the server while synthesis runs (qwen2.5-coder:32b can take 30–90 seconds on first synthesis).

**Why it happens:** The router was written standalone (not in an async context). Promotion detection happens at execution log time, inside what will be an async request handler. The JS source (FlameSavant) runs synthesis as a fire-and-forget Promise — that pattern doesn't translate directly to Python async without care.

**Consequences:** All forge-bridge clients (Flame endpoint, MCP server, test scripts) hang for the duration of an LLM call. Any tool that triggers synthesis as a side effect becomes a random latency bomb.

**Prevention:**
- Promote `LLMRouter` to a proper async class (`async def complete()`) using `asyncio.to_thread()` for the blocking HTTP calls to Ollama and Anthropic. This is the correct pattern for wrapping sync IO in async Python.
- Synthesis must be scheduled as a background task (`asyncio.create_task()`) not awaited inline, mirroring FlameSavant's `.catch(() => {})` fire-and-forget.
- The CONCERNS.md already flags "Unimplemented LLM router backends" and no async support — fix this before wiring into the bridge, not after.

**Warning signs:** forge-bridge WebSocket connections time out sporadically. Server logs show no activity for 30+ seconds during synthesis.

**Phase:** LLM router promotion to `forge_bridge/llm/` (Phase 1 / first).

---

### Pitfall 4: `register_tools()` Pluggable API Breaks FastMCP's Static Registration Model

**What goes wrong:** The current `server.py` registers all tools at module import time using `mcp.tool(name=...)(fn)`. FastMCP builds its tool schema from this at startup. Adding a `register_tools()` API for downstream consumers (projekt-forge) means tools must be registered after the `mcp = FastMCP(...)` object exists but before `mcp.run()` starts serving. If the API is designed to be called at any time (including after startup), synthesized tools registered mid-run may not appear in the client's tool list until a reconnect, or FastMCP may not support dynamic registration at all.

**Why it happens:** MCP protocol sends the tool list to the client at connection time (or on `tools/list` request). FastMCP's internal tool registry is populated at definition time. Dynamic additions after the server is already running require either a protocol-level tool list notification or a server restart. This is not obvious from the FastMCP API.

**Consequences:** projekt-forge calls `register_tools()` and the tools silently don't appear for Claude. Synthesized tools are registered but not surfaced. The pluggable API ships and nobody notices it doesn't work.

**Prevention:**
- Verify FastMCP supports `tools/list_changed` notifications (MCP spec supports this as of 2024-11-05). If it does, use it. If it doesn't, synthesized tools must be available at startup or require a reconnect.
- Design `register_tools()` to be called before `mcp.run()` — i.e., it populates a list of callables that `server.py` registers in its startup phase, not after.
- For synthesized tools that must be hot-loaded: consider a separate "synthesized tools" MCP server that the LLM agent can call alongside the static server, rather than trying to mutate a running server's tool list.
- Write an integration test that verifies a tool registered via `register_tools()` appears in the `tools/list` response before merging.

**Warning signs:** `tools/list` response doesn't include tools added via `register_tools()`. Claude reports the tool doesn't exist even though it was registered.

**Phase:** Pluggable MCP server (Phase 3).

---

### Pitfall 5: Probation System Promotes Synthesized Tools Based on Execution Count Alone

**What goes wrong:** A synthesized tool that executes successfully five times in a row passes probation. But "successful execution" in the Flame context means the Python code ran without an exception — not that it produced the correct result. A synthesized tool that silently produces wrong output (incorrect shot rename, wrong frame range, malformed openclip XML) will pass probation and graduate to the full registry. These mistakes may not be caught until a production operation has been applied incorrectly to real media.

**Why it happens:** The learning pipeline has no semantic validation layer — it can only observe whether code raised an exception, not whether the output was correct. FlameSavant has the same limitation. The JS source in FlameAgent records executions as successful if `!flameResult.error`, which is purely a process-level check.

**Consequences:** Semantically wrong synthesized tools graduate to production registry. Incorrect Flame operations (wrong renames, wrong segment attributes) are applied to media without error. Downstream tools (publish, sequence assembly) operate on incorrect data.

**Prevention:**
- Probation must require human review for any tool that writes to Flame state (`readOnlyHint: False`). Read-only synthesized tools can pass probation by execution count.
- Store the full input/output log for every probation execution. Surface this to the operator before graduation.
- Default synthesized tools to `readOnlyHint: True` via annotation metadata. If the synthesis LLM marks an operation as write-side, require explicit human promotion.
- Add a `_source: 'synthesized'` annotation (as FlameSavant does with `module.exports._source = 'synthesized'`) and surface this in the MCP tool description so Claude knows to be extra cautious.

**Warning signs:** Synthesized tools in the registry that modify Flame state but have no human review log. A `flame_*` tool returns unexpected output after a recent synthesis run.

**Phase:** Learning pipeline probation system (Phase 2).

---

## Moderate Pitfalls

---

### Pitfall 6: JSONL Execution Log Replay Replays Stale Counts on Startup

**What goes wrong:** On startup, the ExecutionLog replays the JSONL file to restore in-memory counts. If the synthesis already happened (the skill exists in the registry), replaying will trigger promotion again on the first new execution that crosses threshold — potentially re-synthesizing a skill that already exists. In the Python port, if synthesis is triggered a second time for the same hash, it may produce a different skill name from the LLM (non-deterministic generation), creating an orphan or collision.

**Why it happens:** FlameSavant keeps counts only in memory (not persisted). The JSONL persists records but the in-memory `_counts` map is rebuilt fresh each run. The promotion check fires when `count === PROMOTION_THRESHOLD` exactly — meaning it never fires on replay since counts jump past threshold. The Python port may change this to `count >= PROMOTION_THRESHOLD`, which breaks this invariant.

**Prevention:**
- On JSONL replay, rebuild counts but mark any hash that already has a corresponding synthesized skill as `already_promoted`. Only fire synthesis for hashes with no existing skill.
- Use `count == PROMOTION_THRESHOLD` exactly (not `>=`) to prevent re-promotion on every startup after threshold is reached.
- Store a `promoted_at` timestamp in the JSONL record when synthesis succeeds, so replay can filter those hashes.

**Warning signs:** Duplicate synthesized skill files appearing in the skills directory after restarts. LLM synthesis calls happening at startup before any user activity.

**Phase:** Learning pipeline execution log (Phase 2).

---

### Pitfall 7: LLM Router Sensitivity Decision Is Binary and Caller-Controlled

**What goes wrong:** The router routes based on `sensitive=True/False` passed by the caller. There is no automatic sensitivity detection. Code synthesis always uses the same sensitivity flag regardless of what's in the prompt. A synthesized prompt that contains shot names, client names, or file paths from Flame will be sent to Claude (cloud) if the synthesis call passes `sensitive=False`, leaking production data to Anthropic.

**Why it happens:** The design puts sensitivity responsibility on the caller. For synthesis, the caller is the SkillSynthesizer, which works from example code containing real production data (shot names, paths, regex patterns containing client codes).

**Consequences:** Production shot names and client codes leak to the Anthropic API. CONCERNS.md flags the Anthropic API key risk — this makes it worse.

**Prevention:**
- Synthesis calls MUST always use `sensitive=True` (local Ollama). This is a hard constraint, not a config option.
- Add an assertion or explicit parameter `_force_local=True` to the synthesis path so it cannot be accidentally changed.
- Document this in the LLM router docstring: "Code synthesis always routes locally regardless of sensitive flag."
- Health check must verify local Ollama is available before synthesis is enabled. If Ollama is down, disable synthesis rather than falling back to cloud.

**Warning signs:** `sensitive=False` call in the SkillSynthesizer code path. Anthropic API usage spikes during synthesis sessions.

**Phase:** LLM router promotion (Phase 1).

---

### Pitfall 8: Dynamic Tool Registration Race With MCP Client Connection

**What goes wrong:** The pluggable `register_tools()` API is called by projekt-forge during its startup. If projekt-forge initialises after the MCP server is already serving clients (Claude connects early), the tools registered by projekt-forge will not be in the first `tools/list` response. Claude's tool list will be stale for that session.

**Why it happens:** MCP clients cache the tool list from the initial handshake. The protocol supports `notifications/tools/list_changed` to signal updates, but FastMCP may not implement this automatically. If the tool list changes after a client connects, the client must re-issue `tools/list` — which Claude Code and other clients may not do automatically.

**Prevention:**
- Document that `register_tools()` must be called before `mcp.run()`. Enforce with an `_started` flag that raises `RuntimeError` if called after server start.
- Test with an MCP client that connects, calls `tools/list`, receives `register_tools()` addition, then calls `tools/list` again to confirm it sees the new tool.
- Check FastMCP changelog for `tools/list_changed` notification support (as of MCP spec 2024-11-05 this is defined but implementation varies by server framework).

**Warning signs:** projekt-forge-specific tools not appearing in Claude's tool list. Claude reports "no such tool" for tools registered by projekt-forge.

**Phase:** Pluggable MCP server (Phase 3).

---

### Pitfall 9: Optional Dependency Import Errors Surface at Runtime, Not Install Time

**What goes wrong:** `openai` and `anthropic` are optional extras. The LLM router uses lazy import (`try: from openai import OpenAI`). If a user installs `forge-bridge` without the `[llm]` extra but the synthesis pipeline is wired in as a hook on `bridge.py`, every execution will hit the import-time `RuntimeError` when synthesis is attempted. CONCERNS.md already flags "Unimplemented LLM router backends" and no graceful fallback.

**Why it happens:** The current router raises `RuntimeError` if openai is not installed. When synthesis is triggered as a side effect of a successful Flame execution, the error propagates up through the execution handler. If not caught correctly, it will surface as a tool failure to the MCP client.

**Prevention:**
- Synthesis hook in bridge.py must catch `RuntimeError` from missing dependencies and log a one-time warning, not propagate.
- Add a `learning_pipeline_enabled()` check that verifies optional dependencies are importable before wiring in the hook.
- pyproject.toml `[llm]` extra (once deduplicated per CONCERNS.md) must include both `openai` and `anthropic` as a single group.
- Also fix the duplicate dependency declarations in pyproject.toml before the router is promoted (this is the exact tech debt flagged in CONCERNS.md lines 14–17).

**Warning signs:** `RuntimeError: openai package not installed` appearing in forge-bridge server logs during normal tool execution.

**Phase:** LLM router promotion (Phase 1) and learning pipeline wiring (Phase 2).

---

## Minor Pitfalls

---

### Pitfall 10: JSONL Append May Corrupt File on Disk Full or Process Kill

**What goes wrong:** FlameSavant wraps the JSONL append in a try/catch that swallows disk errors. The Python port should do the same, but a partial write (process killed mid-append) can leave a malformed last line. On the next startup, replaying the JSONL will fail to parse the corrupted line.

**Prevention:**
- Skip malformed lines during replay with a `json.JSONDecodeError` handler, log the skip, continue.
- Write to a temp file and rename (atomic write) if log integrity is critical. For a learning pipeline, skipping a corrupted entry is acceptable.

**Phase:** Learning pipeline execution log (Phase 2).

---

### Pitfall 11: Skill Synthesis Prompt Contains Too Much Context, Exceeds Token Budget

**What goes wrong:** If up to five code examples are passed to synthesis (as FlameSavant does) and each example is a long Flame operation with comments, the synthesis prompt can exceed the local model's context window (qwen2.5-coder:32b has a 32k context). The model silently truncates input, producing a synthesized skill based on incomplete examples.

**Prevention:**
- Cap each example at 500 tokens in the synthesis prompt (not 2000 characters as FlameSavant does — token count is what matters for the LLM).
- Use only the best two or three examples (most recent, shortest) rather than all five.
- Log the approximate token count of synthesis prompts. Alert if approaching 80% of model context limit.

**Phase:** Learning pipeline synthesis (Phase 2).

---

### Pitfall 12: MCP Tool Name Namespace Collision Between flame_* and synth_* at Discovery

**What goes wrong:** Claude receives a `tools/list` that includes both `flame_rename_shots` (static, hand-written) and `synth_rename_shots` (synthesized). Claude may prefer the synthesized version because it appears later in the list or has a more specific description generated by the LLM. There is no mechanism to signal tool authority or precedence.

**Prevention:**
- Synthesized tools use a distinct `synth_` prefix, not `flame_` or `forge_`.
- Include `[synthesized — use with caution]` in the tool description for synthesized tools.
- Consider not surfacing synthesized tools to Claude at all until they pass probation and human review — they exist in the registry for internal use only.

**Phase:** Learning pipeline probation + pluggable MCP server (Phases 2–3).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| LLM router async promotion | Blocking sync `complete()` in async context (Pitfall 3) | `asyncio.to_thread()` wrapper, do this first |
| LLM router sensitivity | Synthesis leaking production data to cloud (Pitfall 7) | Hard-code `sensitive=True` for all synthesis calls |
| Optional deps | Import errors surfacing as tool failures (Pitfall 9) | Capability check before wiring synthesis hook |
| Execution log | Code normalisation wrong for Python (Pitfall 1) | Use `ast` module, not regex |
| Execution log replay | Re-promotion on restart (Pitfall 6) | Track `promoted_at` in JSONL |
| Skill synthesis | Overwriting static tools (Pitfall 2) | `synth_` namespace, reserved name check |
| Probation system | Wrong tools graduating based on execution count alone (Pitfall 5) | Human review gate for write-side tools |
| Synthesis prompt | Token budget exceeded (Pitfall 11) | Cap examples at 500 tokens each |
| Pluggable register_tools() | FastMCP static registration incompatibility (Pitfall 4) | Call before `mcp.run()`, test with real client |
| Dynamic tool registration | Race with client connection (Pitfall 8) | Enforce registration-before-start invariant |
| Tool namespace | synth_* colliding with flame_* (Pitfall 12) | Strict prefix separation, don't surface until probation passed |

---

## Sources

- Direct codebase analysis: `forge_bridge/llm_router.py`, `forge_bridge/mcp/server.py`, `forge_bridge/mcp/tools.py`
- Direct codebase analysis: `.planning/codebase/CONCERNS.md` (known tech debt and fragile areas)
- FlameSavant source review: `src/learning/ExecutionLog.js`, `src/agents/SkillSynthesizer.js`, `src/agents/FlameAgent.js`, `src/learning/RegistryWatcher.js`
- MCP specification 2024-11-05: `notifications/tools/list_changed` defined at protocol level
- Python `ast` module documentation: canonical approach to language-aware code normalisation
- Confidence: HIGH for Pitfalls 1–9 (direct source evidence), MEDIUM for Pitfalls 10–12 (inferred from analogous systems)
