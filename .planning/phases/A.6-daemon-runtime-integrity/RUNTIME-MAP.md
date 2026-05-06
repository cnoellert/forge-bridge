# Daemon Runtime Map (Phase A.6 Step 1)

**Status:** initial draft, 2026-05-06
**Source of truth:** `forge_bridge/mcp/server.py` (post-A.4), `forge_bridge/__main__.py`, `forge_bridge/cli/main.py`, `forge_bridge/runtime/manager.py`, `packaging/launchd/forge-bridge-daemon`
**Scope:** MCP server + Console + chat endpoint runtime. Out of scope: state_ws server (separate process), Flame hook (separate process inside Flame).

This document is a **required deliverable of A.6** and is intended to survive as a durable reference for future runtime work. If it is wrong in places, fix it as Step 2 / Step 3 produce evidence — do **not** reason from it as ground truth.

---

## Process topology

There are **three** processes under daily operation:

```
┌────────────────────────────────────┐    ┌──────────────────────┐
│ MCP server / Console / chat        │    │ state_ws bus         │
│ (this map)                         │◄──►│ ws://127.0.0.1:9998  │
│ python -m forge_bridge mcp http    │    │ separate process     │
│   - port 9997: FastMCP HTTP        │    └──────────────────────┘
│   - port 9996: Console (uvicorn)   │
└────────────────────────────────────┘
              ▲
              │ HTTP from inside Flame (PR42)
              │
┌────────────────────────────────────┐
│ Flame hook                         │
│ flame_hooks/.../forge_bridge.py    │
│ port 9999, runs INSIDE Flame proc  │
└────────────────────────────────────┘
```

Process boundaries matter for A.6 because the state_ws bus runs in a separate process — `_wait_for_bus` (new in A.4) does a TCP probe across process boundaries, not an in-process check.

---

## Entry-point matrix

Every entry point converges on `forge_bridge.mcp.server.main()` (or the underlying FastMCP `mcp` object), which runs `_lifespan` → `bootstrap_daemon()`. **A.4 invariant:** every entry point inherits the same initialization. The matrix below records *how* each one gets there.

| # | Entry point | Caller | Path through code | Transport | Lifespan invoked? |
|---|-------------|--------|-------------------|-----------|-------------------|
| 1 | Claude Desktop | external (Anthropic Desktop app) | spawn `python -m forge_bridge mcp stdio` | stdio | yes — FastMCP `mcp.run("stdio")` honors registered lifespan once per session (line 513) |
| 2 | Direct daemon | shell or operator | `python -m forge_bridge mcp http --port 9997` | streamable-http | yes — `_composed_lifespan` wraps `_lifespan` over the FastMCP `streamable_http_app()` (line 534-541) |
| 3 | `fbridge up` | operator | spawns `mcp http` as a detached subprocess via `forge_bridge.runtime.manager.start_mcp_http()` | streamable-http | yes — same as #2 (subprocess literally runs `mcp http`) |
| 4 | launchd plist | macOS launchd | `packaging/launchd/forge-bridge-daemon` shell wrapper → `python -m forge_bridge mcp http --port 9997` | streamable-http | yes — same as #2 |

**Convergence point:** entries 2/3/4 all funnel through `main(transport="streamable-http", port=...)` at `forge_bridge/mcp/server.py:493`. Entry 1 takes the `stdio` branch at line 509.

**Pre-A.4 divergence (now closed):** only entry 4 had the `nc -z localhost 9998` pre-exec gate. Entries 1/2/3 raced. A.4 moved the gate into `bootstrap_daemon()` so all four entries share it.

---

## Lifespan ordering — `bootstrap_daemon()`

`bootstrap_daemon` is the **single source of truth for daemon initialization** (A.4). Every observable daemon behavior is supposed to be identical regardless of entry point.

### Steps (in execution order)

| Step | Action | Code location | Loop / Task | New in A.4? |
|------|--------|---------------|-------------|-------------|
| 0 | `await _wait_for_bus(bus_url, 30 s)` — TCP poll on `ws://127.0.0.1:9998` | server.py:155-193, 224-229 | runs on outer loop (the loop that called `bootstrap_daemon`) | **YES** |
| 1 | `await startup_bridge()` — connect `AsyncClient` to state_ws; on failure, log WARNING and set `_client = None` | server.py:374-414, 232 | outer loop | unchanged |
| 2 | Construct `ExecutionLog()` + `ManifestService()` (sync, no await) | server.py:243-247 | outer loop | unchanged |
| 3 | `asyncio.create_task(watch_synthesized_tools(...))` → `watcher_task` | server.py:251-255 | task spawned on outer loop | unchanged |
| 4 | Construct `LLMRouter()` + `ConsoleReadAPI(llm_router=...)`; assign to `app.state.console_read_api` later | server.py:260-269 | outer loop | unchanged behavior; lifecycle ordering shifted relative to Step 0 |
| 5 | `build_console_app(read_api, ...)` + `register_console_resources(...)` | server.py:272-279 | outer loop (sync) | unchanged |
| 6 | `_start_console_task(app, "127.0.0.1", 9996)` → `console_task` (uvicorn `Server.serve()` running as a task) + bind barrier (`server.started`) | server.py:282-284, 429-490 | console uvicorn runs as a **task on the outer loop** | unchanged |

### `_BootstrapResult` carries through `_lifespan`

```python
result = await bootstrap_daemon(mcp_server)   # constructs everything
try:
    yield                                      # mcp_server runs requests
finally:
    await teardown_daemon(result)              # reverse: console → watcher → bridge
```

**Outer-loop owner of `_lifespan` depends on transport:**

- Entry 1 (stdio): FastMCP's `mcp.run("stdio")` creates the loop and runs `_lifespan` inside it for the lifetime of the stdio session.
- Entries 2/3/4 (streamable-http): `asyncio.run(uvicorn.Server(config).serve())` at line 549 creates the loop. `_lifespan` is wired into the Starlette app's lifespan chain via `_composed_lifespan` at line 534-541.

---

## Loop ownership

There is **one** asyncio loop per daemon process. All tasks live on it.

| Resource | Constructed where | Used from where | Same loop? |
|----------|-------------------|-----------------|------------|
| FastMCP server (`mcp`) | module-load (line 356-364) | `mcp.run()` / `streamable_http_app()` driven by outer loop | yes |
| `AsyncClient` (state_ws) | `startup_bridge()` (Step 1) | tools that call `get_client()` from any handler | yes |
| `ExecutionLog`, `ManifestService` | Step 2 (sync constructors) | console handlers, MCP tools | n/a (no async state at construction) |
| `watcher_task` | Step 3 | runs forever; cancelled by `teardown_daemon` | yes |
| `LLMRouter` | Step 4 (constructor is **lazy** — no clients allocated yet) | chat handler at `/api/v1/chat` | yes (constructor adds nothing to a loop) |
| `_local_native_client` (ollama.AsyncClient) | **lazy, on first use** inside `LLMRouter._async_local_with_tools` (or similar) | called from chat handler running on console uvicorn task | **MUST verify in Step 2** — this is the suspect site for loop-affinity issues |
| `_local_client` (AsyncOpenAI) | **lazy, on first use** inside `LLMRouter._async_local` | called from `acomplete` from chat handler | **MUST verify in Step 2** |
| `_cloud_client` (AsyncAnthropic) | **lazy, on first use** | called from cloud-routed paths | **MUST verify in Step 2** |
| Console uvicorn (`server.serve()`) | Step 6 | runs forever; cancelled by `teardown_daemon` | yes — runs as a task on outer loop |
| Outer FastMCP server (entries 2/3/4) | `asyncio.run(uvicorn.Server(...).serve())` at line 549 | the `asyncio.run` drives it | yes |

### Lazy-client construction (mechanism vs. consequence)

**Mechanism (fact, from static reading):**

- `LLMRouter.__init__` (router.py:240-264) stores config strings only; no HTTP clients are allocated.
- `_get_local_native_client` (router.py:844-871) is the lazy constructor for the native Ollama client. Pattern: `if self._local_native_client is None: self._local_native_client = AsyncClient(host=host); return self._local_native_client`.
- `_get_local_client` (router.py:817-830) and `_get_cloud_client` (router.py:832-842) follow the same pattern for the OpenAI-compat shim and Anthropic clients respectively.
- `complete_with_tools` reaches the native client at router.py:468 (`self._get_local_native_client()`).
- The `host` string passed to `ollama.AsyncClient(host=...)` is derived from `self.local_url`, which was captured from `os.environ` at `__init__` time (router.py:247-249).

**Consequence (hypothesis until Step 2):**

- Because the client is allocated only at first await of an LLM call, "router constructed on the wrong loop" is structurally implausible as a root cause: the client is bound to whichever loop is running at first call, which the loop-ownership table identifies as the single daemon loop `L`.
- That makes the lazy-allocation site itself, not router construction, the candidate for the 75 s symptom. Plausible mechanisms (each unverified):
  - environment / config resolution at first call (Step 3 territory: what `self.local_url` resolves to inside the daemon)
  - ordering interaction between `_composed_lifespan`'s two lifespans (whether `session_manager.run()` startup gates a resource the chat path eventually awaits)
  - request-time blocker (lock, semaphore, connection-pool init under daemon vs. shell)
  - a pre-existing condition exposed but not caused by A.4

**Step 2 must produce evidence before any of the above is treated as confirmed.**

---

## Task ownership

| Task name | Created in | Awaited / cancelled in | Cancellation propagation |
|-----------|------------|------------------------|--------------------------|
| `watcher_task` | bootstrap Step 3 | `teardown_daemon` (`.cancel()` + `await`) | best-effort; CancelledError swallowed |
| `console_uvicorn_task` | bootstrap Step 6 (inside `_start_console_task`) | `teardown_daemon` sets `console_server.should_exit = True`, then `await asyncio.wait_for(task, 5.0)`, falls back to `.cancel()` | best-effort; exceptions swallowed |
| FastMCP `session_manager.run()` lifespan | streamable-http only — runs *alongside* `_lifespan` via `_composed_lifespan` | exits when outer uvicorn server exits | controlled by FastMCP, not by us |
| outer uvicorn `Server.serve()` | streamable-http only — `asyncio.run(...)` at line 549 | drives the whole process; exits when the process is signaled | n/a |

---

## Where the chat handler reads `LLMRouter`

```
POST /api/v1/chat                                       (console uvicorn, port 9996)
   ↓
forge_bridge.console.handlers.chat_handler              (line 763)
   ↓
request.app.state.console_read_api._llm_router          (set in build_console_app, line 122)
   ↓
_llm_router.complete_with_tools(...)                    (router.py)
   ↓
self._local_native_client = ollama.AsyncClient(...)     ← LAZY, first use
   ↓
HTTP to http://localhost:11434/v1                       (Ollama, separate process)
```

The same `console_read_api` instance is referenced by:
- `app.state.console_read_api` (set in `build_console_app`, line 122 of `console/app.py`)
- `_canonical_console_read_api` module global (set in bootstrap Step 4, line 269 of `mcp/server.py`)

Both point at the object constructed during bootstrap Step 4. Identity should hold across the daemon lifetime.

### Failing surface — restated structurally

The smoke-test data does not say "the router is broken." It says **the lazy-allocation LLM-loop path is broken.** Restating with that precision is load-bearing for Step 2 instrumentation placement:

`/api/v1/chat` has **two distinct internal paths** through `chat_handler` (handlers.py):

```
chat_handler
   │
   ├── PR20 short-circuit (line 1089-1103, _execute_forced_tool)
   │       └── tools_filtered_count == 1 AND < tools_available_count
   │           ↓
   │       mcp.call_tool(...) directly                    ← NEVER enters complete_with_tools
   │           ↓                                          ← NEVER triggers lazy client allocation
   │       returns chat envelope with stop_reason=tool_forced
   │
   └── full LLM loop (line 1151+)
           ↓
       _llm_router.complete_with_tools(...)               ← enters router agentic loop
           ↓
       self._get_local_native_client()                    ← LAZY ALLOCATION on first iter
           ↓
       ollama.AsyncClient(host=...).chat(...)             ← first network await
```

**Smoke-test masking explained structurally:**

| Test prompt class | Path taken | Lazy allocation triggered? | Observed symptom |
|---|---|---|---|
| Tool-keyword prompts (Tests 0, 2, 3, 4 — narrowed to 1) | PR20 short-circuit | **no** | succeeds-but-bad-args (forced-call schema bug, A.5.2) |
| Conversational prompts (Test 1) | full LLM loop | **yes** | 75 s `LLMToolError` at iter=0 |
| Unmatched prompts (Test 5 — no narrowing match) | full LLM loop | **yes** | 75 s `LLMToolError` at iter=0 |

The PR20 short-circuit was bypassing the failing surface entirely. Conversational and unmatched prompts were the only ones that exercised the actual broken path. **This is exactly the masking relationship the A.5 spec recorded — and it now resolves to one structural distinction: bypass-vs-allocate.**

**Implication for Step 2 (load-bearing for instrumentation placement):**

- Probes MUST instrument the full LLM loop path, not the PR20 short-circuit path.
- Specifically: the probe site is around `complete_with_tools` → `_get_local_native_client()` → first `await client.chat(...)` (router.py:468 and the corresponding adapter inside `OllamaToolAdapter`).
- Probing `_execute_forced_tool` will produce a clean trace and tell us nothing about the actual failure.

This restatement does not change the spec's hypotheses; it sharpens which code surface they apply to.

---

## What changed in A.4 (commit `52e2743`)

The commit message describes A.4 as a **structural refactor with one new behavioral element (Step 0)** — Steps 1-6 are claimed bytecode-equivalent to the prior `_lifespan`. The bytecode-equivalence claim is unverified by this map; the steady-state-equivalence question remains a hypothesis until Step 2. The intended delta per the commit message:

1. **NEW** `_wait_for_bus` (Step 0) — TCP-level poll for `ws://127.0.0.1:9998`. 30 s default, override via `FORGE_BRIDGE_BUS_WAIT_SECONDS`.
2. **RENAMED** `_lifespan` body → `bootstrap_daemon()` (Steps 1-6 are bytecode-equivalent to the previous `_lifespan` 6-step sequence per the commit message).
3. **NEW** `teardown_daemon()` — extracted from the previous `_lifespan` finally-block.
4. **THIN WRAPPER** `_lifespan` now delegates to `bootstrap_daemon` / `teardown_daemon`.
5. **REMOVED** the launchd `nc -z` pre-exec poll loop (now redundant; lives in Step 0).

### Behavioral changes introduced by A.4 (mechanism vs. consequence)

Each row separates **mechanism** (structural fact, derivable from static code reading) from **consequence** (hypothesis about runtime symptom — must be verified in Steps 2/3, NOT patched).

| Item | Mechanism (fact) | Consequence (hypothesis) |
|------|------------------|---------------------------|
| Step 0 awaitable | `bootstrap_daemon` awaits `_wait_for_bus(...)`, an async sleep / TCP-probe loop, for up to 30 s before Step 1. | Whether this delay produces user-observable symptoms depends on what the daemon attempts to serve during that window. Async sleep does not block other tasks on the same loop, but it does delay every step that follows in the same coroutine. Unverified at runtime. |
| Lifespan ordering under streamable-http | `_composed_lifespan` (line 538) is structured `async with _lifespan(mcp), fastmcp_lifespan(app):`. Per `async with` semantics, `_lifespan(mcp)` enters fully before `fastmcp_lifespan(app)` enters. Therefore Steps 0-6 of `bootstrap_daemon` complete *before* FastMCP's `session_manager.run()` startup. | Whether this strict ordering causes the 75 s symptom in `/api/v1/chat` is hypothesis. Plausible mechanisms: session_manager startup gates a resource the chat path eventually awaits; some FastMCP-side initialization is deferred until first request, masking earlier blocking. Unverified. |
| Stdio vs. streamable-http lifespan invocation | FastMCP `mcp.run("stdio")` invokes the registered lifespan once per session. Under streamable-http, FastMCP's `*_app()` builders historically wired only `session_manager.run()` as the Starlette app's lifespan; A.4 keeps the `_composed_lifespan` workaround that chains `_lifespan(mcp)` alongside it. | Workaround is in place per static reading. Whether per-request lifespan re-entry occurs in practice under our specific FastMCP version is unverified. |
| Bridge degradation does not break chat (claimed) | `bootstrap_daemon` Step 4 constructs `LLMRouter` regardless of whether `_client` was set (Step 1 degrades to `_client = None` on connection failure). The chat handler reads `request.app.state.console_read_api._llm_router`. Static reading of `chat_handler` (handlers.py:763 onward) does not show a direct call to `get_client()`. | Whether some indirect dependency exists in the LLM tool-call path that pulls `get_client()` (e.g., a tool the LLM selects, or a sanitizer that touches the bridge) is not verified by static reading. Hypothesis until Step 2/3 traces the request path. |
| Console bind barrier returns optimistically | `_start_console_task` polls `server.started` for up to `ready_timeout=5.0`; if the flag never flips it logs a warning and returns the task anyway (server.py:486-489). | Whether this produces a user-observable issue depends on whether `server.started` reliably flips in practice. No evidence either way yet. |

The structural facts on the left are testable by static reading. The hypotheses on the right require runtime observation. **Step 2 must not collapse a fact column entry into a consequence column conclusion without evidence.**

---

## Open questions for Step 2 / Step 3

1. (Step 2) Does the lazy-allocation of `ollama.AsyncClient` actually happen on the same loop that handles `/api/v1/chat`?
2. (Step 2) Does `_composed_lifespan` start `fastmcp_lifespan(app)` correctly, or does the new `_wait_for_bus` blocking interact poorly with FastMCP's session manager startup?
3. (Step 2) Is there a per-request handler somewhere that's calling `asyncio.run(...)` or `loop.run_until_complete(...)`, creating a fresh nested loop?
4. (Step 3) From inside the daemon process, what does `os.environ.get("FORGE_LOCAL_LLM_URL")` resolve to? What does `OLLAMA_HOST` look like?
5. (Step 3) Does `httpx` / `ollama.AsyncClient` see the same DNS / connection behavior the shell sees when probing `localhost:11434`?
6. (Step 3) When the chat request comes in, what is the **actual** time spent — is it 75 s of `await ollama_client.chat(...)`, or is it 75 s of waiting for some lock / semaphore before that call?

---

## Step 2 timing-probe rules

Question 6 above is the highest-value diagnostic question — it partitions the hypothesis space cleanly. Step 2 will answer it with an **observation-only** timing probe. **Authorization boundary still active: probe is logging-only, no behavior change, removed after Step 4.**

### Probe placement

Three timestamps inside the full LLM loop path (NOT the PR20 short-circuit path):

| Timestamp | Site | What it measures |
|-----------|------|------------------|
| `T1` | Immediately before `await client.chat(...)` inside the Ollama tool adapter (i.e. just before the network call dispatch site invoked from `complete_with_tools` iter=0) | "Ready to call Ollama" |
| `T2` | First observable entry inside the client call path — e.g. just after `ollama.AsyncClient` enters its async send method, or equivalent first reachable point inside the underlying `httpx` client | "Client actually entered" |
| `T3` | Immediately after the call returns or raises | "Client returned or errored" |

Probe site selection rule: instrument the **full LLM loop path** (router.py:468 → adapter dispatch → first network await), not `_execute_forced_tool` and not the short-circuit. The masking-relationship subsection explains why probing the wrong path is uninformative.

### Interpretation rules

| Pattern | Interpretation | Implication for Step 4 |
|---------|----------------|-------------------------|
| Large `T1 → T2` gap | Pre-call blockage between "ready to call" and "client entered" — most likely lazy alloc itself, ContextVar overhead, lock, semaphore, or a guard like `_in_tool_loop` | Root cause is in router/client wiring, not Ollama or network |
| Large `T2 → T3` gap | Actual Ollama / HTTP / network latency | Root cause is Ollama-side, network-side, or env-resolution (Step 3 territory) |
| `T2` never observed | Call path never entered — lazy alloc hung *before* construction completed, or an exception fired before reaching the network call | Root cause is inside the lazy constructor or its imports (e.g., `from ollama import AsyncClient` failing under daemon env) |
| All three gaps small **but total request latency remains large** | Instrumentation placed too late in the request path — the latency is being consumed *upstream* of `T1` | Probe must be widened upstream. Candidate upstream sites: middleware (CORS, rate limit), request body parsing, narrowing (`_tool_filter`, `filter_tools_by_message`), routing into `chat_handler`, synchronous preprocessing (`build_enforcement_system_prompt`, tool-list snapshotting), request-level locks/semaphores, lifecycle gating before `complete_with_tools(...)` |

The fourth case keeps Step 2 unblocked if the first probe placement is too deep. Without it, the analysis would terminate at "probe shows nothing unusual but request still takes 75 s" with no guidance on how to reclassify.

### What Step 2 produces

- A single re-run of Smoke Test 1 (`"Explain what forge-bridge is in one sentence."`) with probe active.
- The three timestamp values (`T1`, `T2`, `T3`) and the total wall-clock from the chat handler's own `started`/`elapsed_ms` log.
- Pattern classification per the interpretation table.
- Updated map / classification document carrying the result.
- **No code changes beyond the probe.** Probe is removed at Step 4 boundary, regardless of whether it identified the cause.

---

## Diagram

```
                            ┌─────────────────────┐
                            │  asyncio.run()      │   (entries 2/3/4)
                            │   creates loop L    │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │ uvicorn.Server.serve│  (FastMCP HTTP, port 9997)
                            │   on loop L         │
                            └──────────┬──────────┘
                                       │ Starlette lifespan = _composed_lifespan
                                       ▼
                       ┌────────────────────────────────┐
                       │ _composed_lifespan (line 534)  │
                       │   async with                   │
                       │     _lifespan(mcp),            │
                       │     fastmcp_lifespan(app):     │
                       │       yield                    │
                       └─────────────┬──────────────────┘
                                     │ enter _lifespan first
                                     ▼
                       ┌────────────────────────────────┐
                       │ _lifespan(mcp_server)          │
                       │   bootstrap_daemon → yield →   │
                       │   teardown_daemon              │
                       └─────────────┬──────────────────┘
                                     │
                                     ▼
                       ┌────────────────────────────────┐
                       │ bootstrap_daemon Steps 0-6     │
                       └─────────────┬──────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
        ┌───────────┐         ┌─────────────┐        ┌──────────────────────┐
        │ AsyncClient│        │ watcher_task│        │ console_uvicorn_task │
        │ → :9998    │        │ (loop L)    │        │ (loop L, port 9996)  │
        │ (loop L)   │        │             │        │   serves /api/v1/*   │
        └───────────┘         └─────────────┘        │   serves /ui/*       │
                                                      │   ← chat_handler     │
                                                      │     reads            │
                                                      │     app.state.       │
                                                      │     console_read_api │
                                                      │     ._llm_router     │
                                                      └──────────────────────┘
                                                                │
                                                                ▼
                                                       ┌────────────────────┐
                                                       │ LLMRouter (loop L) │
                                                       │  lazy clients →    │
                                                       │  ollama.AsyncClient│
                                                       │  AsyncOpenAI       │
                                                       │  AsyncAnthropic    │
                                                       │  bound to L on     │
                                                       │  first await       │
                                                       └────────────────────┘
```

Single loop. Single bootstrap. The runtime substrate is, by design, simple — that is the structural claim from static reading. The 75 s timeout / `LLMToolError` at iter=0 is therefore **most likely** (not provably) to originate from one of:

- a request-time blocker (lock, semaphore, connection pool, broken first-call init)
- environment divergence (Step 3)
- a subtle interaction between `_composed_lifespan`'s two lifespans
- a pre-existing condition exposed but not caused by A.4 reordering
- a category not yet enumerated — the list above is hypothesis space, not exhaustive proof

The "most likely" framing matters: the structural simplicity claim is verifiable, but the inference that the bug must therefore lie in this specific list depends on no per-request handler doing something unusual (e.g., nested `asyncio.run`), which static reading has not exhaustively proved. Step 2's timing-probe rules (above) give Step 4 a way to discover whether the actual cause is in this list or upstream of where the probe was first placed.

Steps 2-4 will narrow this. **No code is to be touched until Step 4 completes.**
