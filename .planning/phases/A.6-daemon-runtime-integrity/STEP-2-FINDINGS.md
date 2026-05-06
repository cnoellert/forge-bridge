# A.6 Step 2 — Timing-probe findings

**Date:** 2026-05-06
**Authorization:** observation-only wrapper instrumentation per PHASE-A.6-SPEC.md §"Authorization boundary."
**Probe:** `forge_bridge/llm/_adapters.py` — wrapper around `ollama.AsyncClient.chat(...)` call site in `OllamaToolAdapter.send_turn`. No library monkey-patching. Marked with `# === A6 PROBE BEGIN/END ===`. **NOT removed yet** — removal is gated on Step 4.

---

## Capture method

- One daemon restart (`fbridge down && fbridge up` at 13:43; daemon PID 91854).
- One smoke-test run: Smoke Test 1, prompt `"Explain what forge-bridge is in one sentence."` — chosen because it exercises the full LLM-loop path with no PR20 short-circuit (validates the lazy-allocation surface).
- Logs read from `~/.forge-bridge/logs/mcp_http.log`.

## Raw timestamps (monotonic seconds)

| Marker | Value (s) | Site |
|--------|-----------|------|
| `T1` | `244636.006037` | `_adapters.py:697` — `send_turn`, just before `await` |
| `T2` | `244636.006916` | `_adapters.py:64`  — wrapper, library about-to-be-called |
| `T3` | `244711.009854` | `_adapters.py:723` — `send_turn`, after `await`, `outcome=exception` |

Surrounding log context (immediately after T3):
```
tool-call session complete iter=0    router.py:753
WARNING  chat tool_error             handlers.py:1199
```

Outcome on the await: exception. The exception type is not directly logged at T3 by the probe (intentional; probe is observation-only and the existing `LLMToolError` re-raise machinery handles surfacing). The `chat tool_error` line is consistent with the `LLMToolError("Ollama call failed: ...")` raise at `_adapters.py:735`.

## Deltas

| Span | Duration | Classification |
|------|----------|----------------|
| `T1 → T2` | 0.879 ms | small — pre-call path is essentially free |
| `T2 → T3` | **75 002.938 ms** | **large** — time is spent *inside* the awaited library call |
| `T1 → T3` | 75 003.817 ms | matches request wall-clock (~75.04 s end-to-end) |

The 75 s figure is consistent across all three prior occurrences (Test 1 13:46, Test 5 12:59, prior Test 1 12:56). The exactness across runs is itself a finding — a flapping connection or random network event would not produce three identical 75.0 s readings. This is most plausibly a **configured timeout boundary** firing somewhere downstream of the wrapper.

## Interpretation (per RUNTIME-MAP.md §"Step 2 timing-probe rules")

| Rule | Pattern | Match? |
|------|---------|--------|
| Large `T1 → T2` → pre-call blockage | T1→T2 = 0.88 ms | **no** |
| Large `T2 → T3` → real Ollama / HTTP / network latency | T2→T3 = 75 003 ms | **YES** |
| `T2` never observed → call path never entered | T2 fired | **no** |
| All gaps small + wall-clock large → probe placed too late | T2→T3 is large | **no** |

Pattern matched: **rule 2 — large `T2 → T3` gap**. The classification implication is that the time is being consumed **at or after the library entry**, not before it. The wrapper-fidelity contract (T2 = "library about-to-be-called") is sufficient to rule out pre-call blockage; it does not by itself distinguish between "time spent inside ollama.AsyncClient logic" and "time spent inside the network round-trip" — Step 3 will narrow that.

## What this means for the failing surface (mechanism vs. consequence)

**Mechanism (fact, from this capture):**

- The full LLM-loop path through `complete_with_tools → OllamaToolAdapter.send_turn` reaches the wrapper and the underlying `client.chat(...)` await is dispatched.
- The await does not return for ~75.003 seconds, after which an exception is raised that surfaces as `LLMToolError("Ollama call failed: …")`.
- Pre-call path is sub-millisecond. No detectable blockage between `complete_with_tools` and library entry.

**Consequence (hypothesis, requires Step 3 evidence):**

The 75 s is attributable to one of (Step 3 will distinguish):
1. **Environment resolution divergence inside the daemon** — `self.local_url` / `OLLAMA_HOST` resolves differently inside the daemon process than it does from the shell. The daemon's `ollama.AsyncClient(host=...)` may be pointed at an unreachable endpoint, with httpx silently retrying until a configured ceiling fires.
2. **Configured timeout firing on an unreachable Ollama endpoint** — even if the host string is correct, if Ollama is not reachable from inside the daemon process (DNS, IPv4-vs-IPv6 binding, loopback context) the AsyncClient will hang on connect / first byte until a timeout. The 75 s exactness across runs is consistent with this.
3. **Ollama-side hang** — Ollama is reachable but does not respond to this specific request shape (e.g., model load wait, queue starvation, tools-payload format issue under specific sub-versions of `qwen2.5-coder:32b`). The shell's `/api/tags` query (3 ms) does not exercise the same code path; it does not refute this hypothesis.
4. **Transport library bug exposed by daemon-vs-shell context** — e.g., httpx connection pool acquired in one event-loop context but used from another (lazy alloc race), producing a silent retry until ceiling.

The 75 s exactness across three independent runs makes hypotheses 1 and 2 the highest-prior candidates. Hypothesis 3 is plausible but would more typically produce variable latency. Hypothesis 4 is the lowest-prior candidate now that the lazy-allocation site has been confirmed reachable (T2 fires reliably).

**None of these are confirmed.** Step 3 produces the environment evidence needed to distinguish them.

## Authorization-boundary discipline observations

- No code was modified beyond the probe.
- The probe lines are bracketed by `# === A6 PROBE BEGIN ===` / `# === A6 PROBE END ===` markers in `forge_bridge/llm/_adapters.py` and tagged `probe-A6` in log output. Removal at Step 4 is mechanical.
- Probe-removal boundary is **mandatory**, not aspirational — if any probe survives Step 4, that becomes a separate explicit decision (debug-flag promotion, metric surface, etc.).
- One daemon restart, one canonical capture. Probe also captured the prior 12:56 / 12:59 / pre-restart Test 5 events implicitly via the existing `tool-call session complete iter=0 elapsed_s=75.0` log lines (those preceded probe deployment so they have no T1/T2/T3 — but the 75-second consistency is corroborated).

## Step 2 status

- Classification data: **filed (this document).**
- Timestamps: **preserved (above).**
- Interpretation: **rule 2 match — large T2→T3 gap, time spent inside library call.**
- Likely failing surface: **environment / network reachability between the daemon and Ollama**, with configured-timeout signature (75.0 s exactness).
- Probes: **NOT removed.** Removal gated on Step 4.
- Fixes: **none implemented.** Per discipline, Step 3 adds environment evidence before fix planning.

## Methodological observation (preserve, do not formalize yet)

The lifecycle map (Step 1) **materially compressed the runtime hypothesis space before instrumentation began.** The "map first, probe second" sequence produced concrete diagnostic leverage:

- The lazy-allocation finding from the map (router.py:817-871, 240-264, 468) downgraded "wrong-loop affinity" from a top hypothesis to structurally implausible — *before* the probe ran.
- The masking-relationship subsection identified the failing surface as the lazy-allocation LLM-loop path specifically, which directly determined where the probe was placed (`OllamaToolAdapter.send_turn`, not `_execute_forced_tool`). Probing the wrong path would have produced clean traces and told us nothing.
- The Step 2 timing-probe rules table (with the fourth interpretation case) gave the capture an explicit classification grammar before the data existed.

The Step 2 result interprets in seconds because the diagnostic frame was prepared for it. Without the map's preparatory work, the same 75 s capture would have admitted many more interpretations.

This is a real methodological result, not narrative. Preserve as evidence for the eventual methodology-promotion question (still gated on additional reliability phases).

---

## Awaiting review before Step 3 begins.

Step 3's environment-verification work is the natural next move under hypotheses 1 and 2. Specifically:

- Probe `os.environ.get("FORGE_LOCAL_LLM_URL")` and `OLLAMA_HOST` from inside the daemon process at request time (not just bootstrap time).
- Probe what `self.local_url` was resolved to in the LLMRouter instance.
- Probe whether `ollama.AsyncClient(host=...)` was constructed with the host the operator expected (`http://localhost:11434`) or something else (e.g., the daemon may have inherited an environment that points elsewhere — a Cursor / VSCode / launchd env override).
- Compare to a shell-process probe (a one-shot Python script run as the same user that calls `ollama.AsyncClient(host="http://localhost:11434").chat(...)` directly — outside the daemon — to see whether the same timeout reproduces).

These remain Step 3 work items. **No fixes until Step 3/4 review approves the classification path.**
