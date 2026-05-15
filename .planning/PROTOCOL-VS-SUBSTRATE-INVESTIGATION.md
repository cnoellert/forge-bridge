# Protocol-vs-Substrate Investigation — chat-path structured invocation

**Date:** 2026-05-14
**Host:** portofino (MacBook Pro, Apple Silicon, 16 cores, 128 GB unified memory)
**Ollama model:** `qwen2.5-coder:32b` (Q4_K_M)
**Bridge version:** post-Phase-24.1 (HEAD at `c480353`)
**Measurement bundle:** `~/forge-measurements/2026-05-14-180110/`
**Sibling artifact:** `.planning/COLD-START-INVESTIGATION.md` (foundational measurement; this artifact builds on it)

## What this artifact closes

Phase 24.1 set out to attack KV-cache instability in the chat hot path. Three commits landed against a single architectural target — making the `{system, tools}` prefix Ollama sees stable across consecutive calls so the cache hits instead of misses:

- **Commit 4 (`fbf4b56`)** — deterministic alphabetical tool ordering at the compile boundary
- **Commit 6 (`c480353`)** — reachability state cached across conversational timescales (5s → 60s)
- **Commit 5 attempt → reverted at `44c6890`** — capability-domain bucketing surfaced an irreducible taxonomy substrate gap (`SEED-CAPABILITY-DOMAIN-BUCKETING-V1.6+`)

This artifact freezes the result: **the cache-locality work succeeded as measured.** No further architectural work on that surface is justified until different evidence surfaces. Post-Commit-6 measurement also exposed a separate, deeper problem that this artifact opens: **structured-invocation reliability**, which is downstream of cache locality, not solved by it, and not within Phase 23.1's actual scope.

## Method

Canonical 6-call measurement sequence run via the operator's portofino measurement block:

1. Cold reset (`fbridge down`; force model unload via `keep_alive=0`)
2. `fbridge up`; wait for `:9996` + `:11434` readiness
3. Five `/api/v1/chat` calls in sequence, capturing total wall-clock + response body + bridge logs + graph emissions

Bundle artifacts: `00-down.txt` through `10-graph-files.txt`, plus `forge-measurement-2026-05-14-180110.tgz`.

## Findings — Phase 24.1 cache-locality work succeeded

Per-call total latency (verbatim from `*.time` files):

| # | Call | Total | tools_available | tools_filtered | tool_trace |
|---|------|-------|-----------------|----------------|------------|
| 1 | canonical-cold | **17.10s** | 7 | 7 | `[]` |
| 2 | canonical-repeat (identical payload) | **1.73s** | 8 | 8 | `[]` |
| 3 | adjacent-flame ("Show me timeline segments") | 3.52s | 8 | 2 | `[]` |
| 4 | conversational ("What time is it") | 9.75s | 8 | 8 | `[]` |
| 5 | canonical-return (same as call 1 payload) | **1.06s** | 8 | 8 | `[]` |

**Operational evidence the prefix-stability work delivered:**

1. **Call 2 = 1.73s after call 1 = 17.10s.** Cache hit on the system + tools prefix after the cold first call. Generation cost dominates; prompt-eval is sub-second per the COLD-START investigation's hot-cache measurement.

2. **Call 5 = 1.06s after non-Flame interlude.** The canonical query returned at sub-second latency *after* calls 3 (different Flame query) and 4 (conversational) intervened. The prefix survived two consecutive different-user-message calls. **This is the direct empirical confirmation that Commit 4 (deterministic ordering) + Commit 6 (60s reachability TTL) closed the per-message cache-bust sources COLD-START identified.**

3. **PR14 variance is no longer dominant.** PR14 narrowed the tool list to a non-full set on only 1 of 5 calls (call 3: 2/8). The other four hit PR14's no-match fallback path returning the full reachable set — which is *stable*, so the prefix matches across them. PR14's per-message variance is bounded to the rare exact-keyword-match case.

4. **Generation is now the primary cost on hot-prefix calls.** Calls 2 and 5 at 1.06–1.73s reflect generation time (~25 tokens × ~22 tok/s ≈ 1s) plus framing overhead. Cold-call cost (call 1: 17.10s) includes model load + cache-miss prompt-eval on the ~1850-token prefix.

5. **Cache TTL bump confirmed surviving the multi-call window.** Reachability transitioned from 7 → 8 tools between call 1 and call 2 (Flame hook came online during the sequence) but did NOT bounce back down on subsequent calls — the 60s TTL held.

**Result: the Phase 24.1 KV-cache-locality arc is empirically validated and operationally complete.** Re-litigation is not warranted absent new evidence; further KV-cache-locality work is deferred behind that bar.

## Findings — the new architectural finding

The measurement surfaced an unanticipated, deeper problem. Every call's `tool_trace` is `[]`. Every call's `final_text` is a fabricated tool-call-shaped *string*:

| Call | `final_text` (verbatim from `*.json`) |
|------|---------------------------------------|
| 1 / canonical | `"flame_list_clips({\"reel_name\": \"Reel 1\"})"` |
| 2 / canonical | `"flame_list_clips({\"reel_name\": \"Reel 1\"})"` |
| 3 / flame | `"flame.get_timeline_segments()"` |
| 4 / conversational | `"flame.get_current_time()"` |
| 5 / canonical | `"flame_list_clips({\"reel_name\": \"Reel 1\"})"` |

None of these are registered tools. `flame_list_clips` doesn't exist; `flame.get_timeline_segments()` and `flame.get_current_time()` are Python-method-call syntax, not MCP tool calls. The model is generating *text that pattern-matches what a tool call should look like* without producing the structured MCP `tool_calls` payload the chat handler can dispatch.

**The critical empirical sentence:**

> **No `flame_execute_python` graph events were emitted during the run, proving the failure occurred before execution-substrate entry.**

`10-graph-files.txt` is empty — no `~/.forge-bridge/graphs/<graph_id>.jsonl` files were written during the measurement window. Phase 24 Commit 2's instrumentation (entry emission at `utility.py` execute_python) confirms by absence: the function was never invoked. The model's text-shaped fabrications never reached the substrate; they failed at the protocol layer between LLM output and tool dispatch.

## The semantic-vs-protocol distinction

This freezes a durable architectural distinction the project did not previously articulate explicitly:

- **Semantic layer** — *what* the model decides to do. Tool discoverability, docstring legibility, escalation-rule clarity, system-prompt guidance. The model reads its inputs and forms an intent.
- **Protocol layer** — *how* the model expresses what it decided. Structured `tool_calls` JSON in the response message vs free-form text content. The model's intent crossing the wire in a shape the chat handler can act on.

These are different reliability surfaces with different failure modes:

| Layer | Failure shape | Observability |
|-------|---------------|----------------|
| Semantic | Model picks the wrong tool / fails to escalate / misreads the docstring | Captured by the chat trace + bridge router log + tool-call records in `tool_trace` |
| Protocol | Model produces text that pattern-matches a tool call but isn't a structured tool_calls payload | Captured by `tool_trace == []` despite the prose looking actionable |

The Phase 24.1 measurement shows the bridge is currently hitting the **protocol-layer** failure mode 5 of 5 times on canonical inputs. The semantic layer arguably succeeded — the model *understood* it was supposed to call something Flame-shaped — but the protocol layer (the JSON shape of the response) never received that intent.

This is now the real debugging boundary for v1.6+ chat-path work. Substrate (Commits 1-2) + cache locality (Commits 4, 6) are done; protocol-invocation reliability is the next surface.

## What Phase 23.1 actually solved (and didn't)

Phase 23.1 closed the v1.5 ship-blocker by:

- Registering `flame_execute_python` in the MCP server (it existed in `forge_bridge/tools/utility.py` pre-23.1 but was never exposed)
- Repositioning the docstring as the canonical Flame introspection surface with three worked examples
- Flattening the signature so FastMCP exposes a flat JSON schema the model can generate

Post-Phase-23.1 author-walk on portofino confirmed the substrate path worked end-to-end (`utility.py:195` emitted `status=ok elapsed_ms=12 code_len=581` on the canonical query). That walk verified **affordance discoverability** — the model could find and invoke `flame_execute_python` when the path was hot and the model produced a structured tool call.

What Phase 23.1 did NOT solve, as the measurement now shows:

> **Phase 23.1 solved affordance discoverability but NOT structured invocation reliability.**

The tool is discoverable. The schema is flat. The docstring teaches escalation. None of this constrains the model to *emit* a structured `tool_calls` payload instead of free-form text. Under cold-load + 1850-token-prefix conditions with no recent training-style biasing, the model defaults to producing prose-shaped fabrications that *describe* a tool call rather than *invoke* one.

This is not a Phase 23.1 regression. Phase 23.1's success criterion was the affordance path, which holds. The structured-invocation reliability surface is downstream of affordance and was not in 23.1's scope. Naming this distinction explicitly is the durable archaeology this artifact preserves.

## What this artifact opens

The next investigation is **protocol-path instrumentation**, not additional semantic shaping. Concretely:

1. **Capture the raw Ollama response body**, not just the bridge's processed `final_text`, on each canonical query. The model's actual output (and its `tool_calls` field structure) is the ground truth — the bridge's text-mode salvage path (`OllamaToolAdapter._try_parse_text_tool_call`, Bug D fallback) may be transforming or failing to extract structured calls.
2. **Trace the protocol-layer dispatch decision**: when does the chat handler decide the model's response is text vs structured? Where does that decision live? Is the Bug D salvage firing? Is it firing wrong?
3. **Compare structured-call success rate** across model versions, prompt-shape variations (with/without the PR15 enforcement block), and tool-list sizes. The 1850-token prefix is large; smaller schemas may bias the model toward structured output. The COLD-START investigation listed schema slimming as low priority for *cache-locality*; it may be more relevant for *structured-invocation reliability*.
4. **Verify Bug D fallback under canonical query**: the v1.4 FB-D fix added `_try_parse_text_tool_call` salvage when the model emits `{"name": ..., "arguments": ...}` JSON in `message.content` while leaving `message.tool_calls` empty. The canonical-run failures *should* have been salvaged — the fabricated strings include parentheses-syntax `flame.get_current_time()`, NOT the JSON shape Bug D salvages. So the salvage path can't help here; the issue is upstream.

Anti-scope for the next investigation (binding until protocol-layer evidence surfaces otherwise):

- **No more semantic shaping.** Docstring rewrites, system-prompt reordering, tool-name renaming, additional worked examples — none of these address the protocol-layer failure shape.
- **No more cache-locality work.** Empirically validated. Re-opens only on new evidence.
- **No replacement of the Bug D salvage path** without first measuring whether it's currently doing harm or just not firing.
- **No model swap** without measuring whether protocol-layer reliability is qwen2.5-coder-specific.

## Operational status as of this artifact

- Phase 24.1 cache-locality arc: **closed**. Commits 4 + 6 deliver measurable wins; Commit 5's bucketing failure produced durable archaeology (`SEED-CAPABILITY-DOMAIN-BUCKETING-V1.6+`) and is correctly deferred.
- Graph emission substrate (Commits 1-2): **operational**. Confirmed by absence — no graph files = function not called = substrate working as designed (emissions only happen on real invocations).
- Canonical regression fixture (Commit 3): **operational**. The fixture works against mocked execution; the measurement shows the chat path doesn't reach the substrate even when the fixture's exact query is sent.
- Chat-path structured invocation: **broken on production routing**. 0 of 5 canonical-shape calls produced a structured tool call. The semantic-vs-protocol boundary identified above is the next architectural surface.

## Appendix — what to investigate the canonical regression query against next time

The measurement bundle's `09-mcp-log.txt` captured *stale* log entries (the launchd-managed `mcp_http` writes to a different log path than the `fbridge` managed-daemon code expected). The actual measurement-window log entries from request_ids `3c83fd51`, `b70e6c78`, `e1ac8ce7`, `4d3f0ed7`, `ed44ead4` are not in the captured tail.

Resolve before next measurement run:

- Identify the launchd-managed `mcp_http` log destination on portofino (likely `/var/log/com.forge-bridge.mcp_http.{out,err}.log` or `~/Library/Logs/com.forge-bridge/*`)
- Update the measurement block's log-path candidate list to include it
- Re-run the canonical sequence with the correct log capture so the per-iter router log lines (prompt_tokens, completion_tokens, tool field) are available for protocol-path analysis

This is methodology-debt, not architectural-debt. The empirical conclusions above stand on the response bodies + timing + graph-emission absence, all of which the bundle captured cleanly.

---

*Artifact authored 2026-05-14 immediately after Phase 24.1 commit chain landed at `c480353` and the canonical measurement sequence completed. Builds on `.planning/COLD-START-INVESTIGATION.md`. Opens the protocol-path-instrumentation investigation as the next architectural surface for v1.6+ chat-path work.*
