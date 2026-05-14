# Cold-Start Investigation — fbridge chat latency

**Date:** 2026-05-14
**Host:** portofino (MacBook Pro, Apple Silicon, 16 cores, 128 GB unified memory)
**Ollama model:** `qwen2.5-coder:32b` (Q4_K_M, 19 GB on disk, 30 GB in VRAM)
**Bridge version:** v1.4.1 (post-PR14/PR15/PR20/PR21 chat handler)

## Question

> Why does `fbridge chat "What time is it?"` take ~60 seconds while the native Ollama chat window answers the same question instantly, even though both hit the same daemon and the same model?

## Method

Five timed curl probes against `:9996/api/v1/chat` and `:11434/api/chat`, with `/api/ps` inspections to verify model-load state and a hand-crafted payload to isolate Ollama's KV-cache behavior from the bridge's request-shaping behavior.

## Findings

### The native chat is not actually faster — it sends a smaller prompt

There is only one model installed on portofino (`qwen2.5-coder:32b`). Both the native Ollama chat window and `fbridge chat` route to the same daemon on `:11434`. The "instant" feeling of the native chat is not a model-load advantage; it is a **prompt-size advantage**.

| Path | System prompt | Tools attached | Input tokens |
|---|---|---|---|
| Native Ollama chat | trivial ("you are a helpful assistant"-ish) | none | ~20 |
| `fbridge chat` (current) | FORGE pipeline assistant + PR15 enforcement stack | 7–8 schemas (post-filter) | ~695 |

The bridge ships ~35× more input tokens per call. Most of the latency follows from this.

### Measured costs on this hardware

Direct `/api/chat`, hot model, no tools (the floor):

```
load_duration:      49 ms
prompt_eval:       252 ms   (34 tokens → ~135 tok/s)
eval (generation): 1417 ms  (33 tokens → ~23 tok/s)
total:            1729 ms
```

`fbridge chat`, hot model, cache cold (`/api/v1/chat` Call A):

```
total:            11160 ms
```

`fbridge chat`, hot model, cache hot, identical payload (Call B–C):

```
total:             1410 ms  (cache HIT — same as direct Ollama)
```

`fbridge chat`, hot model, cache hot, **different** user message (Call D):

```
total:             1040 ms  (cache HIT on system+tools, only user tokens re-evaluated)
```

Cold-model load on this hardware:

```
~6.7 s   (Call A first-ever fbridge chat vs. Call C identical hot)
```

### Cost decomposition (hot model)

| Component | Cost | Source |
|---|---|---|
| Prompt eval, 695 tokens, cache miss | ~3.5 s | `_adapters.py:666` `ollama.AsyncClient.chat()` |
| Prompt eval, 695 tokens, cache hit | ~0.05 s | Ollama KV cache (longest-prefix match) |
| Generation, 90–110 output tokens | ~4–5 s | Model output rate ~22 tok/s on this hardware |
| Tool-loop scaffolding + HTTP framing | ~0.5 s | `handlers.py:824` + router internals |

Cold-load adds ~6.7 s on top when the model has expired from VRAM (10-minute `keep_alive` default — `_adapters.py:59` `_OLLAMA_KEEP_ALIVE = "10m"`).

### Headline result: KV cache works, but the bridge under-uses it

Ollama's KV cache delivers a **70× reduction** in prompt-evaluation cost when the prefix matches (3.5 s → 0.05 s). It survives across:

- Identical user messages (Call B–C).
- **Different** user messages (Call D — cache hits the system + tools prefix; only the new user tokens are evaluated).

It does not survive:

- A 10-minute idle (model unloaded → entire context dropped).
- Any intervening Ollama call with a different system/tools prefix (eviction, observed in the earlier Run 1 → Run 2 → Run 3 sequence where Run 3 missed the cache despite identical payload to Run 1 — the intervening direct `/api/chat` with no tools displaced the slot).
- Tool-list reordering between requests.
- Reachability flips that change which tools survive `_tool_filter.py:filter_tools_by_reachable_backends` (5-second probe cache TTL at `_tool_filter.py:84` — can change mid-conversation if Flame goes up/down).

## Prefix stability audit

`chat_handler` (`handlers.py:824`) builds the prefix in this order each request:

1. `await _mcp_server.mcp.list_tools()` — registry snapshot (`:966`).
2. `filter_tools_by_reachable_backends(tools)` — drops backend-unreachable tools (`:1007`). Reachability probed per-call with 5 s cache.
3. `filter_tools_by_message(tools, last_user_text)` — PR14 keyword-narrow (`:1134`). Returns ≤ 8 tools whose names overlap message tokens; falls back to full reachable list when nothing matches.
4. `deterministic_narrow(tools, last_user_text)` — PR21 multi-tool disambiguator (`:1160`).
5. `build_enforcement_system_prompt(router.system_prompt, tools_filtered_count)` — composes base prompt + PR15 enforcement block; appends `PR15_HARD_TOOL_INSTRUCTION` only when `tools_filtered_count == 1` (`_tool_enforcement.py:60`).
6. `OllamaToolAdapter._compile_tools()` walks the filtered list in input order (`_adapters.py:646`).

Every one of these steps is a potential cache-bust source:

| Step | Stable across consecutive calls? | Notes |
|---|---|---|
| `mcp.list_tools()` ordering | Believed stable; not asserted | If MCP registry is dict-iteration-order under the hood, fine on Python 3.7+ but worth confirming. |
| Reachability filter | Stable for 5 s, then re-probes | Flame coming up/down mid-session flips the prefix. |
| PR14 keyword filter | Stable per identical user message; varies across messages | The behavior we want: cache hit on repeated identical messages, cache miss is expected on new messages. |
| PR21 deterministic narrow | Stable per identical input | OK. |
| `build_enforcement_system_prompt` | Branches on `tools_filtered_count == 1` | If filter ever narrows to exactly one tool, the system prompt grows by `PR15_HARD_TOOL_INSTRUCTION` — invalidates cache. |
| Tool-list iteration order | Pass-through from filter | If filter returns `set`-derived ordering anywhere, non-deterministic. |

## Why the original ~60 second symptom was worse than today's 18 s cold path

Today Flame is down, so most `flame_*` and `forge_*` tools are dropped by `filter_tools_by_reachable_backends`. Only the seven in-process tools survive. With Flame **up**, the surviving set roughly triples, the compiled schema payload grows, and prompt eval scales linearly with input tokens. Combined with a true cold disk read (no recent activity to keep pages warm), the ~60 s observation is plausible and consistent with the model we've measured.

## Recommended optimizations (no code yet — ranked by yield)

### 1. Stabilize the prefix to land on cache hits — **saves ~3.5 s per call after the first**

This is the single highest-leverage change. The cache provably works; we just have to stop knocking it over. Tactics:

- **Sort the compiled tool list deterministically** (alphabetical by name) inside `OllamaToolAdapter._compile_tools()` so reachability/filter ordering can't leak in.
- **Lengthen `_PROBE_CACHE_TTL_SEC`** from 5 s to ~60 s on the chat hot path. Flame's up/down state doesn't usually flip mid-conversation; the 5 s ceiling exists for `forge doctor` snappiness, not for chat. Consider a separate TTL for chat vs. diagnostic paths.
- **Pin the PR15_HARD_TOOL_INSTRUCTION branch** or accept the cache invalidation only when it actually matters (i.e., when the tool list legitimately narrows to one tool — that path already takes PR20's force-execute shortcut, so the model isn't seeing the extra instruction in practice. Sanity-check this.)

### 2. Branch on "does this message need tools?" — **saves ~6–8 s on chit-chat**

For inputs that obviously have no tool semantics (no token overlap with any tool name, short message, conversational shape), route to `router.acomplete()` instead of `complete_with_tools()`. The bridge's PR14 filter already detects "no match" — but its fallback today is to send the *full* tool list. The high-yield change is to flip that fallback for short/conversational inputs to "no tools at all," landing at the 1.7 s floor.

The risk is regressing legitimate tool-needing questions phrased without tool keywords. The mitigation is conservative gating: only branch when `len(message_tokens) < 15` **and** `len(exact_matches) + len(other_matches) == 0` in `filter_tools_by_message`.

### 3. Pre-warm the canonical prefix on lifespan startup — **saves ~3.5 s on the first user chat after `fbridge up`**

Once #1 is in place (stable prefix), add a lifespan hook in `app.py` that fires one throwaway `ollama.chat(...)` with the same `{system, tools}` the chat handler will use. The KV cache is hot before any user lands. Cheap.

### 4. Bump `_OLLAMA_KEEP_ALIVE` from `"10m"` to `"60m"` or `"-1"` — **saves ~6.7 s on the first user chat after a quiet period**

On a dedicated 24+ GB VRAM box where `qwen2.5-coder:32b` is the only resident, holding it forever is free. The 10-minute default makes sense for shared/desktop Ollama, not for a dedicated chat backend.

### 5. Slim each tool's `inputSchema` before compilation — **modest, maybe 0.5–1 s**

`_adapters.py:646` (`_compile_tools`) emits the full MCP `inputSchema` per tool. Stripping `description` on simple-typed fields, dropping `examples`, collapsing `$defs` could roughly halve the per-tool token cost. Yield is bounded; do this last.

### What *not* to do

- Don't add streaming as a "speed-up" — it improves perceived latency but doesn't change total time, and `SEED-CHAT-STREAMING-V1.4.x` already exists for a v1.6+ pass at this.
- Don't switch the default model to `qwen3:32b` — your own CLAUDE.md (`SEED-DEFAULT-MODEL-BUMP-V1.4.x`) explicitly forbids it; thinking-mode token verbosity blows the wall-clock budget.

## Open questions worth resolving before any code change

1. **Does `mcp.list_tools()` return a stable ordering across requests?** If the registry is dict-backed on Python 3.7+, yes, but it should be asserted with a test rather than assumed. Otherwise sorting in `_compile_tools()` is mandatory for #1 to deliver.
2. **Are tool descriptions or inputSchemas ever mutated between requests?** A synthesized tool's manifest update would change schema bytes mid-session. Worth confirming the learning pipeline can't bust the cache while a chat session is active.
3. **Does the `request_id` ever appear in any prompt-bound field?** We confirmed by diff that the *response* body carries it but the prompt does not — verify this stays true for any future logging/telemetry that might thread it into the prompt or system block.
4. **Does Ollama's KV cache survive a model reload triggered by `keep_alive` expiry, or does the cache go with the model?** If the cache dies with the model, #4 (longer keep_alive) compounds with #1 (stable prefix). If the cache outlives unloads, #4 is less critical.

## Appendix — raw measurements

```
Run 1 — fbridge chat, COLD model + tools:                18.15 s
Run 2 — direct Ollama, hot, no tools:                     1.73 s   (prompt 252 ms, gen 1417 ms)
Run 3 — fbridge chat, hot, identical payload to Run 1:   11.48 s   (cache MISS — intervening Run 2 evicted)

Hand-crafted /api/chat with bridge-shaped tools payload:
  Call A — cache cold:    7.58 s   (prompt 3588 ms for 695 tokens, gen 3902 ms)
  Call B — cache hot:     5.08 s   (prompt   46 ms for 695 tokens, gen 4955 ms)

Back-to-back fbridge chat sequence:
  A — "What time is it?":             11.16 s   (cache cold)
  B — "What time is it?" (same):       1.41 s   (cache HIT)
  C — "What time is it?" (same):       1.41 s   (cache HIT)
  D — "Tell me a joke" (different):    1.04 s   (cache HIT on system+tools)
  E — "What time is it?" (same):       1.60 s   (cache HIT)
```

## File references

- `forge_bridge/console/handlers.py:824` — `chat_handler` entry
- `forge_bridge/console/handlers.py:966` — `mcp.list_tools()` registry snapshot
- `forge_bridge/console/handlers.py:1007` — reachability filter call
- `forge_bridge/console/handlers.py:1134` — PR14 keyword filter call
- `forge_bridge/console/handlers.py:1160` — PR21 deterministic narrow call
- `forge_bridge/console/handlers.py:1209` — system-prompt composition
- `forge_bridge/console/_tool_filter.py:84` — `_PROBE_CACHE_TTL_SEC = 5.0`
- `forge_bridge/console/_tool_filter.py:258` — `filter_tools_by_message` (PR14)
- `forge_bridge/console/_tool_enforcement.py:60` — `build_enforcement_system_prompt`
- `forge_bridge/llm/_adapters.py:59` — `_OLLAMA_KEEP_ALIVE = "10m"`
- `forge_bridge/llm/_adapters.py:646` — `OllamaToolAdapter._compile_tools`
- `forge_bridge/llm/_adapters.py:666` — `self._client.chat(...)` call site
- `forge_bridge/llm/router.py:844` — `_get_local_native_client` lazy init
