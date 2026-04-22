# Pitfalls — forge-bridge v1.3 (Artist Console)

**Domain:** Adding Web UI + CLI + MCP resources to a FastMCP + asyncio + JSONL-log middleware package already in production use
**Researched:** 2026-04-22
**Confidence:** HIGH (direct codebase analysis of forge_bridge/mcp/server.py, forge_bridge/learning/*, forge_bridge/__init__.py; FastMCP and MCP Python SDK via Context7; targeted WebSearch for integration-specific failure modes; cross-referenced against v1.2 RETROSPECTIVE lessons)

> This document supersedes the v1.2 pitfalls file (archived as PITFALLS-v1.2.md), which was scoped to adding observability features to a stable contract. v1.3 pitfalls center on **adding a process-level HTTP surface, a CLI companion, MCP resources, and artist-facing UI to an existing FastMCP+asyncio package** — a structurally different risk profile involving transport coexistence, read-model discipline, and UX discipline for a non-technical operator.

---

## Critical Pitfalls

### P-01: Stdio transport + Web UI in the same process — stdout corruption

**What goes wrong:**
The existing MCP server runs FastMCP in stdio mode (the default, used by Claude Desktop and Claude Code). Stdio transport uses stdout as the exclusive MCP wire — every byte written to stdout must be a valid MCP message. If the Web UI HTTP server (uvicorn) is started in the same process alongside a stdio-mode FastMCP instance, any logging, startup banner, or status output that reaches stdout corrupts the MCP wire. The MCP client (Claude Desktop / Claude Code) sees garbled JSON or a framing error and disconnects.

**Why it happens:**
FastMCP's `custom_route` decorator only attaches custom HTTP routes when transport is HTTP, not stdio. Developers assume "I'll just add a uvicorn server alongside the existing mcp.run()" without recognizing that `mcp.run()` in stdio mode owns the process's stdin/stdout and is incompatible with a parallel HTTP server that also logs to stdout.

Concretely: `forge_bridge/mcp/server.py::main()` calls `mcp.run()` which invokes `mcp.run(transport="stdio")` by default. Adding `uvicorn.run(app, port=9996)` in the same call is a deadlock — both block the main thread.

**How to avoid:**
Use FastMCP's `@mcp.custom_route` decorator for the Web UI routes and run the MCP server in **HTTP transport mode** (`mcp.run(transport="http", port=9996)`). In HTTP mode, `custom_route` endpoints are served alongside the MCP endpoint by the same uvicorn instance. This is the documented pattern and avoids all stdout contention.

If stdio mode must be preserved for Claude Desktop compatibility, the Web UI must run as a completely separate process on its own port, with zero shared stdout/stderr (use a log file for console output). Do not start a sub-thread that writes to stdout from within a stdio-mode MCP server.

**Warning signs:**
- MCP client disconnects with a framing/parse error immediately after the Web UI starts
- `tools/list` works before the console route is added but breaks after
- Browser DevTools shows the console endpoint returning 200 but MCP client shows JSON parse failure
- `print()` statements in any function reachable from uvicorn's request path appear in the MCP client's error log

**Phase to address:**
Phase 9 (first Web UI phase). Must be in the Phase 9 CONTEXT.md as a locked architectural decision before any HTTP serving code is written. UAT criterion: MCP client (Claude Code) must complete a `tools/list` call without errors while the Web UI is serving traffic on `:9996`.

---

### P-02: FastMCP transport switch — existing Claude Desktop configs break silently

**What goes wrong:**
If the MCP server switches from stdio to HTTP transport to accommodate custom routes, all existing `claude_desktop_config.json` entries that launch the server as a subprocess (stdio mode) silently stop working — the process starts, stdout has no MCP framing, and Claude Desktop shows "Server failed to start" or worse, spins indefinitely.

**Why it happens:**
Claude Desktop and Claude Code both discover MCP servers via config files that specify a command to run. The config assumes stdio. Switching the default transport breaks every existing installation without any visible error that points to the transport change.

**How to avoid:**
Preserve stdio mode as the default (no args = stdio) and add `--http` / `--port` flags for Web UI mode. The Web UI is an **additive** surface — operators who want it pass `--http --port 9996`; existing Claude Desktop configs without flags continue to work in stdio mode with no Web UI.

This means the Web UI is unavailable when running in stdio mode. That is acceptable for v1.3 (localhost-only, same-posture as `:9999`). Document this trade-off in Phase 9 CONTEXT.md.

**Warning signs:**
- Claude Desktop "Server failed to start" after upgrade
- `mcp dev` shows no tools after the transport change
- projekt-forge's MCP integration tests fail to connect post-upgrade

**Phase to address:**
Phase 9 CONTEXT.md decision: "stdio is default; HTTP is opt-in via --http flag; Web UI requires --http mode." UAT criterion: run the test suite in both modes; Claude Code must connect successfully in stdio mode with no `--http` flag.

---

### P-03: MCP resources vs tools — client support is inconsistent; don't make the manifest resource the only path

**What goes wrong:**
The synthesis manifest is planned as an MCP resource at `forge://manifest/synthesis`. Resources are semantically correct (read-only, URI-addressable, cacheable). BUT: Cursor IDE does not support resources at all. Gemini CLI explicitly says "only tools are available; resources and prompts are not." Some clients subscribe to resources and emit `resources/subscribe` which requires a handler — without one, the server returns an unhandled-request error that can crash the session.

**Why it happens:**
The MCP spec defines resources as application-controlled (the host decides when to expose them), while tools are model-controlled. Many clients implemented tools first and treat resources as optional. The 2025-11-25 spec added subscribe capabilities, but many clients either always subscribe (breaking servers without a handler) or never subscribe (making subscriptions useless).

**How to avoid:**
Expose the manifest as BOTH a resource (`forge://manifest/synthesis` for spec-compliant clients and LLM agents) AND as a tool (`forge_manifest_read` or similar) for clients that only support tools. The resource is the canonical surface per the v1.3 milestone goal (EXT-01 / DF-02); the tool is a backward-compat shim.

Do NOT make the resource the exclusive path for any workflow in v1.3 — the Web UI and CLI read from the read-side API directly (JSONL + live bridge state), not from the MCP resource handler. The resource is for external LLM agent consumers, not for the console.

Register a no-op `resources/subscribe` handler or ensure FastMCP handles the subscribe capability declaration correctly; check with `mcp.get_capabilities()` that `subscribe=False` is advertised if no handler is registered.

**Warning signs:**
- MCP client logs show `Missing handler for request type: resources/subscribe` errors
- Cursor or VS Code extension reports "Server error" immediately on connection
- The manifest content visible in Claude Code differs from what the Web UI shows (diverged read paths)
- `forge://manifest/synthesis` returns 404 in one client, works in another

**Phase to address:**
Phase 9 (resource registration) and whichever phase adds the tool shim. UAT criterion: verify manifest is readable via `mcp__projekt-forge__forge_manifest_read` (tool path) AND via `resources/read forge://manifest/synthesis` (resource path) from a real MCP client session. Do not fake either path.

---

### P-04: JSONL concurrent reader — partial-line parse on write-boundary

**What goes wrong:**
The existing write path acquires `fcntl.LOCK_EX` (exclusive advisory lock) per write in `execution_log.py`. The console read API will poll or stream the same JSONL file. If the reader opens the file, reads to EOF, and the write boundary falls mid-line (OS write buffering means a line can be partially visible before the lock is released on some Linux filesystems), the reader's `json.loads(line)` raises `JSONDecodeError` on the partial line.

Even when the lock prevents write-boundary corruption in practice, the reader seeing the partial line during a lock window on a different file descriptor (fcntl advisory locks don't block open() from other processes) produces silent data loss or parse errors depending on reader error handling.

**Why it happens:**
`fcntl.LOCK_EX` is advisory — it only blocks other callers that also call `fcntl.flock()`. A reader that simply opens and reads the file does NOT check the lock. The JSONL write pattern (open → seek-to-end → write → flush → close) has a window where the line is physically present but not terminated with `\n` yet.

**How to avoid:**
Use the tail-reader pattern: never parse the last partial line. Maintain a `position` pointer (byte offset) from the last successful read. On each poll, read bytes from `position` to EOF; split on `\n`; parse all complete lines; store any suffix without `\n` as a carry-over buffer for the next poll. This is identical to the pattern used by `tail -f`.

The reader should also acquire `fcntl.LOCK_SH` (shared advisory lock) before reading if it needs strict consistency with the writer. But for poll-based console reads, the carry-over buffer pattern is sufficient and avoids the lock contention.

Do NOT hold the read lock for the duration of an HTTP request — acquire, read bytes, release immediately. The console API response should be computed from the bytes captured, not from a held-open file descriptor.

**Warning signs:**
- Intermittent `JSONDecodeError` in console API logs at high synthesis rates
- Console shows N-1 execution records when JSONL has N lines (last line not yet terminated)
- Occasional 500 errors from the console API that correlate with synthesis bursts
- Execution count in the Web UI is consistently one behind the CLI count

**Phase to address:**
The phase that implements the console read-side API (shared by Web UI + CLI). Deliverable: a `JournalReader` class with position tracking and partial-line carry-over buffer. Unit test: write N records, read concurrently, assert N complete records parsed and no partial-line errors.

---

### P-05: ManifestService memory-disk drift — sidecar written, MCP resource stale

**What goes wrong:**
The sidecar write path (synthesizer writes `.sidecar.json`) and the watcher poll cycle (every 5 seconds) create a window where:
1. A new tool is synthesized → `.sidecar.json` written to disk
2. An LLM agent calls `resources/read forge://manifest/synthesis` before the watcher fires
3. The MCP resource handler reads from the in-memory manifest (or cached tool list) which doesn't yet include the new tool
4. The agent acts on stale manifest data

The reverse drift also exists: if a tool file is deleted from disk (quarantine/cleanup) but the watcher hasn't fired yet, the in-memory resource reflects a tool that no longer exists.

**Why it happens:**
The current watcher uses a 5-second poll interval and updates in-process state. The MCP resource handler (not yet written) will need to decide: "serve from the watcher's in-memory state, or re-read the manifest from disk on every request?" In-memory is fast but stale; disk-on-every-request is consistent but slower and adds I/O to the hot path.

**How to avoid:**
Serve the manifest resource by re-reading `.sidecar.json` files from disk at request time, not from the watcher's `seen` dict. The watcher's job is tool registration (hot-load into FastMCP) — the resource handler's job is content retrieval. These are different reads for different purposes; don't conflate them.

If disk I/O on every resource read is a concern (it shouldn't be for localhost with a ~100-tool manifest), add a 1-second TTL cache with a `last_modified` check on the synthesized directory rather than a fixed-interval invalidation.

Do not try to make the watcher's state the authoritative source for the resource handler — the watcher has a 5-second staleness window by design.

**Warning signs:**
- An LLM agent reports "tool X synthesized" but `resources/read forge://manifest/synthesis` doesn't include it
- The tool appears in `tools/list` (registered by watcher) but not in the manifest resource (served from stale cache)
- `console manifest` CLI subcommand shows different tool count than `tools/list` response
- A deleted tool still appears in the manifest resource for up to 5 seconds after deletion

**Phase to address:**
The phase that implements `forge://manifest/synthesis` resource registration. Deliverable: resource handler reads from disk at request time (or with a 1-second TTL cache). UAT criterion: synthesize a tool, immediately call `resources/read`, confirm the new tool appears. Then delete the tool's `.py` file, wait <2 seconds, call `resources/read` again, confirm the tool is absent.

---

### P-06: LLM chat over the console — prompt injection from user queries entering system-prompt-adjacent context

**What goes wrong:**
The LLM chat surface layers on top of the console read API using the existing `LLMRouter`. User queries to the chat interface will describe pipeline state in natural language — "show me all shots in ACM_1234 that failed." If the chat system concatenates tool names, sidecar tags, or execution log entries into the system prompt or message context without sanitization, an attacker (or misconfigured tool) can craft tool names or tags that contain injection markers which then influence the LLM's response.

This is the v1.2 `_sanitize_tag()` problem extended to a new surface: tags sanitized for MCP `tools/list` are NOT automatically sanitized for the chat system's message construction. Two different sanitization boundaries.

**Why it happens:**
Reusing `_sanitize_tag()` for both MCP rendering and chat context construction seems natural. But the chat context builder has a different trust model: it assembles multi-turn conversation context, potentially including execution log entries that contain `raw_code` snippets, which were never treated as injection surfaces before because they only appeared in JSONL files, not in LLM context.

**How to avoid:**
The chat endpoint must apply its own context-sanitization pass, independent of `_sanitize_tag()`. Specifically:
- Never include `raw_code` from execution records directly in the LLM context; include only `intent` and `code_hash`
- Strip the same injection markers from any pipeline-state string that enters the system prompt or system-context block
- Cap total context injected from forge-bridge state per request (e.g., maximum 2KB of pipeline context per chat turn)
- Log the constructed system context at DEBUG level for audit

**Warning signs:**
- Chat responses reference phrases that appear in tool names or sidecar tags rather than the user's query
- The LLM "refuses" a legitimate request because a synthesized tool's name contained something that looked like a policy violation trigger
- Execution log entries with `raw_code` appear verbatim in chat responses
- Token count per chat turn grows unexpectedly (pipeline context not capped)

**Phase to address:**
The phase that implements the LLM chat surface (likely a later Phase 9+ phase, after the read API exists). Deliverable: a `build_chat_context(records, tool_list, max_bytes=2048)` function with its own sanitization pass. Unit test: a tool with an injection-marker name must not propagate the marker into the LLM context string.

---

### P-07: LLM chat cost runaway — no request-level rate limit or token cap

**What goes wrong:**
The LLM chat endpoint routes through `LLMRouter`, which calls the configured model (local Ollama or remote API). Without a per-session or per-minute request limit, an artist who accidentally loops a query (or a script that auto-submits), or a misrouted agent that feeds chat responses back to itself, produces runaway token spend. For a local Ollama deployment this is "just" compute; for a remote API it is direct dollar spend with no circuit breaker.

Real-world precedent: a multi-agent financial assistant in 2025 accumulated $47,000 in API spend over 11 days from a recursive agent loop before anyone noticed.

**Why it happens:**
`LLMRouter` has no built-in rate limiting — it was designed for synthesis calls (low frequency, triggered by threshold crossing) not interactive chat (high frequency, user-driven). Adding chat without adding a rate layer imports the router's latency model into an interactive path.

**How to avoid:**
Add a per-IP or per-session token-bucket rate limiter at the HTTP layer, enforced before the request reaches `LLMRouter`. Simple implementation: a sliding-window counter (in-process dict, no Redis needed for localhost) of requests-per-minute per source IP. A limit of 10 RPM per IP is sufficient for interactive use and blocks runaway loops.

Also cap total prompt tokens per request: the chat endpoint constructs the context from forge-bridge state; if the resulting prompt exceeds a configured token limit (e.g., 8,000 tokens), truncate or reject rather than sending.

**Warning signs:**
- Ollama GPU utilization stays at 100% long after the artist stopped typing
- Remote API invoice significantly higher than expected
- `LLMRouter` logs show the same query repeated hundreds of times with no user action
- The Web UI chat box is unresponsive (the event loop is blocked serving a long-running generation)

**Phase to address:**
Any phase that introduces the chat endpoint. Deliverable: rate limiter middleware (in-process sliding window) applied before `LLMRouter.generate()`. Test: assert that 11 rapid requests within a minute from the same IP are throttled after the 10th, and the 11th returns HTTP 429.

---

### P-08: LLM generation blocking the asyncio event loop

**What goes wrong:**
`LLMRouter.generate()` is an async method. If Ollama (or the remote API) takes 30-60 seconds to respond, the awaited coroutine holds an asyncio Task for that duration. In the same event loop: the MCP server handles tool calls, the watcher polls synthesized tools, and the console HTTP API serves requests. A long-running generation does NOT block the event loop (async awaiting yields), but it does mean:
1. A hung generation (no response, no timeout) that never resolves will keep the task alive indefinitely
2. If the client disconnects mid-generation (SSE drop, browser close), the generation keeps running and occupies a slot in `LLMRouter`'s connection pool

**Why it happens:**
`LLMRouter` has no request-level timeout enforced from the outside. The underlying HTTP client (httpx) has a default connect timeout but may not enforce a read timeout for streaming responses. A streaming generation that stalls mid-response will keep the asyncio task running until the OS TCP keepalive fires (typically minutes).

**How to avoid:**
Wrap every `LLMRouter.generate()` call from the chat endpoint in `asyncio.wait_for(generate(...), timeout=120.0)`. Catch `asyncio.TimeoutError` and return an error response to the user. Also listen for client disconnect (Starlette `request.is_disconnected()`) in any SSE streaming path and cancel the generation task on disconnect.

**Warning signs:**
- `asyncio.all_tasks()` count grows over a long session with no corresponding decrease
- Chat requests pile up waiting; new requests see high latency even though the system is idle
- Memory grows slowly over hours of chat use (held task objects + accumulated LLM response buffers)
- Killing and restarting the MCP server is the only way to recover from a stuck generation

**Phase to address:**
Any phase that introduces the chat endpoint. Deliverable: `asyncio.wait_for` wrapper with 120-second timeout and client-disconnect cancellation. Test: mock `LLMRouter.generate()` to block indefinitely; assert the endpoint returns a timeout error within 125 seconds.

---

### P-09: CLI vs Web UI read-model drift — two surfaces, two query paths, different numbers

**What goes wrong:**
The CLI (`forge-bridge console stats`) and the Web UI (`/console/stats` endpoint) both show execution counts, tool counts, and manifest state. If each surface implements its own query against the JSONL file and in-memory watcher state, they will diverge when edge cases arise: the JSONL has a partial line, the watcher hasn't fired since the last synthesis, or the CLI is run on a different machine (different JSONL path).

Artists will see different counts in the Web UI and in the terminal output and file a bug. The bug is actually not a bug — it's two surfaces reading from slightly different state — but it looks like a bug and erodes trust.

**Why it happens:**
CLI and Web UI are implemented by different phases or different engineers, each reaching for the most convenient data source. The CLI may call `ExecutionLog.get_count()` directly while the Web UI calls the console HTTP API. If these are not backed by the same read function, counts diverge on boundary conditions.

**How to avoid:**
Implement a single `ConsoleReadAPI` Python class (or module) that is the ONLY path both the CLI and the Web UI use to query forge-bridge state. The CLI calls it directly (in-process). The Web UI's HTTP handlers call it as a Python function (not via HTTP to itself). Zero duplication of query logic across surfaces.

The `ConsoleReadAPI` must be isolated from the JSONL write path and from the watcher's `seen` dict. It reads from disk and returns typed Python objects. The HTTP layer serializes them. The CLI formats them. Same data, different presentation.

**Warning signs:**
- `forge-bridge console stats` output differs from the Web UI stats panel even when run on the same machine
- A filter applied in the Web UI returns 47 records; the same filter via CLI returns 46
- The CLI and Web UI have different column names or sort orders for the same data
- A bug is filed for "wrong count" that turns out to be a query implementation difference, not a data difference

**Phase to address:**
Phase 9 (read API foundation). Before any Web UI or CLI surface is implemented, deliver `ConsoleReadAPI` as a tested class. Subsequent phases mount it as an HTTP handler (Web UI) or import it directly (CLI). UAT criterion: run `forge-bridge console stats` and compare its output against the `/console/stats` API response for the same data; assert zero divergence.

---

### P-10: CORS — browser on `:9999` calling API on `:9996` is cross-origin

**What goes wrong:**
The plan is to serve static Web UI assets and API endpoints from the same port (`:9996`). But if any Web UI assets are ever served from the existing Flame HTTP bridge (`:9999`) — even just a redirect or a link — and they make `fetch()` calls to `:9996`, the browser enforces same-origin policy. The `fetch()` call fails with a CORS error, the Web UI shows nothing, and there is no useful error message for an artist.

Less obviously: Claude Code's MCP client connects to the MCP server. If the MCP server is in HTTP mode on `:9996`, and a browser extension or web-based MCP client attempts to call the MCP endpoint from a page served from a different origin, CORS applies to the MCP HTTP endpoint itself.

**Why it happens:**
Localhost-only is not the same as same-origin. Two ports on localhost are two origins: `http://127.0.0.1:9996` and `http://127.0.0.1:9999` are different. Developers assume "it's all local, CORS doesn't apply" — it does.

**How to avoid:**
Serve both the static assets and the console API from the same port (`:9996`). Do not split assets to one port and API to another. Configure explicit CORS headers on the console API allowing `http://127.0.0.1:9996` as the origin (which is a no-op same-origin request, but makes the intent explicit). If SSE/WebSocket push is added, the same rule applies.

If the MCP HTTP endpoint needs to be accessible to web-based clients, add a CORS middleware to the FastMCP/Starlette app explicitly allowing the expected origins (even if just `["http://127.0.0.1:9996"]` for localhost).

**Warning signs:**
- Browser DevTools shows `Access-Control-Allow-Origin` missing on console API responses
- Web UI loads but all `fetch()` calls fail silently
- Artist reports "it works in the browser but only after I opened devtools" (CORS preflight was cached wrong)
- SSE stream connects in Postman but fails in the browser

**Phase to address:**
Phase 9 CONTEXT.md: "All console surfaces (static assets + API endpoints) served from the same port; CORS headers must be explicit." Deliverable: CORS middleware configured before the first HTTP route is implemented. Test: a browser `fetch()` from the Web UI origin to the API origin succeeds without CORS errors.

---

### P-11: Frontend stack overshoot — SPA framework requires a JS build step inside a pip package

**What goes wrong:**
React, Svelte, or Vue require a build step (`npm run build`) that produces a `dist/` directory. If the Web UI is implemented with one of these frameworks and the `dist/` output is not committed to the repository, `pip install forge-bridge` produces a package with no static assets — the Web UI returns 404 on all asset requests. If `dist/` IS committed, the repository bloats with generated files and `pip sdist` includes them unnecessarily.

Even if `dist/` is committed, the developer experience degrades: every UI change requires `npm run build` before testing, which is foreign to the Python developers who maintain this package.

**Why it happens:**
SPAs are the default mental model for "Web UI" for many developers. The mismatch between "Python package" and "JS build toolchain" is not obvious until someone tries to do `pip install -e .` and the Web UI doesn't work.

**How to avoid:**
Use htmx + Jinja2 templates (server-side rendered HTML fragments) served directly from Python. Zero JavaScript build step. The entire Web UI is Python template files and one `htmx.min.js` CDN-linked or vendored as a single static file. Tailwind CSS (if used for styling) can be applied via the precompiled CDN link for v1.3 (no `npx tailwindcss` required).

Ship HTML templates as package data (include in `pyproject.toml` `[tool.setuptools.package-data]`) so they are included in the wheel. The Web UI works immediately after `pip install forge-bridge`.

**Warning signs:**
- `pyproject.toml` adds a `[tool.setuptools.cmdclass]` that runs `npm build` during package build
- The repository has a `package.json` at the root
- Web UI testing requires running a separate `npm run dev` server
- `pip install -e .` works but the Web UI is empty (templates not included in package data)

**Phase to address:**
Phase 9 CONTEXT.md decision: "Web UI is htmx + Jinja2, no JS build step. Templates shipped as package data." This decision must be locked before any UI code is written. UAT criterion: fresh `pip install forge-bridge` from the built wheel, start the server in HTTP mode, load the Web UI in a browser — assets must load without any npm commands.

---

### P-12: SSE/WebSocket real-time push — proxy timeouts and "no events yet" first-paint

**What goes wrong:**
If real-time push (SSE or WebSocket) is added to the Web UI, three failure modes appear:

1. **Proxy timeout:** Any reverse proxy (nginx, caddy, or even macOS's native HTTP stack) will close idle SSE connections after 60-90 seconds. Without a heartbeat, the browser reconnects, which causes a flash of empty content while the stream re-establishes.

2. **No events yet (empty first paint):** If the Web UI renders entirely via SSE push, and the server has no events to send immediately, the artist sees a blank dashboard for several seconds on first load. This is the most common artist-facing failure mode for push-based dashboards.

3. **Backpressure / asyncio queue overflow:** If events are produced faster than the SSE client consumes them (e.g., a synthesis burst producing 50 events in 1 second), the asyncio queue backing the SSE stream fills. If the queue has no max size, memory grows unboundedly. If it has a max size, older events are dropped silently.

**Why it happens:**
These are all known SSE integration problems. They happen because the happy path (a connected client receiving events in real time) is straightforward, but the failure paths (first load, reconnect, burst) require explicit design.

**How to avoid:**
For v1.3: prefer poll-over-push. The Web UI polls the console API every 5 seconds using htmx `hx-trigger="every 5s"`. This avoids all three SSE failure modes. Real-time push is listed as "open" in the milestone scope — decide it explicitly in planning and default to poll unless a specific user need requires push.

If push is added: (a) send a `{: heartbeat}` SSE comment every 30 seconds to prevent proxy timeout; (b) send a synthetic "current state" event immediately on connect so first paint is not blank; (c) cap the asyncio event queue at 100 entries and drop oldest on overflow (log a WARNING).

**Warning signs:**
- Artist reports "the dashboard goes blank every few minutes" (proxy timeout with no heartbeat)
- Web UI is empty on first load until synthesis activity occurs (no initial state event)
- Memory grows slowly during high-synthesis periods (unbounded event queue)
- Browser console shows repeated `EventSource` reconnects

**Phase to address:**
If real-time push is in scope: the phase that adds SSE. Otherwise this pitfall is moot. UAT criterion (if SSE is added): simulate a 60-second idle period on the SSE stream; assert no disconnect/reconnect in browser network tab.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| CLI queries JSONL directly instead of using ConsoleReadAPI | Faster to ship the CLI | CLI and Web UI diverge; bugs appear as "wrong count" | Never — single read model is the v1.3 architectural invariant |
| Serve static assets from `:9999` (Flame bridge port), API from `:9996` | Avoid adding static file serving to a new port | CORS errors in every browser | Never — always co-serve assets and API |
| Use React/Svelte for the Web UI "because it's more powerful" | Better interactivity for future admin features | JS build step permanently embedded in the pip package | Only if admin write operations requiring complex UI are added in v1.4+ (defer the decision) |
| Rate-limit chat by adding `time.sleep()` between requests | Trivially simple | Blocks the asyncio event loop; degrades all other requests | Never — use a token-bucket or sliding-window in async context |
| Store manifest resource in a module-level dict updated by watcher | Fast reads, no disk I/O | Stale data windows; hard to reason about write ordering | Only for performance optimization after the disk-read baseline is proven correct |
| `print()` statements in Web UI route handlers for debugging | Easy debugging | Corrupts stdio MCP wire in stdio mode; leaks internal state | Never — use `logging.getLogger(__name__)` exclusively |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-----------------|
| FastMCP + HTTP transport + Web UI routes | Using `mcp.run(transport="stdio")` then adding uvicorn separately | Use HTTP transport + `@mcp.custom_route` so all routes share one uvicorn instance |
| MCP resources + Cursor/VS Code | Registering resources as the only path to manifest data | Always provide a tool fallback; never assume the client handles resources |
| `fcntl.LOCK_EX` + concurrent console reader | Opening file without acquiring lock, assuming no partial lines | Implement tail-reader with partial-line carry-over buffer; do not rely on lock to protect reader |
| `LLMRouter.generate()` in chat endpoint | Calling without a timeout; letting client disconnect silently | `asyncio.wait_for(..., timeout=120)` + disconnect detection |
| Jinja2 templates as package data | Adding templates to `src/` but not to `pyproject.toml` `package-data` | Add `[tool.setuptools.package-data] forge_bridge = ["console/templates/*.html", "console/static/**"]` |
| CORS on localhost multi-port | Assuming localhost = same-origin | Explicitly configure `CORSMiddleware` even for localhost; co-serve assets and API from same port |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Reading entire JSONL on every console API request | Each request scans O(N) records; N grows linearly with executions | Position-tracked incremental reader; cache record count; index JSONL if >10k lines | ~1,000 executions (~100 KB JSONL); still fast but noticeable |
| Disk I/O in the asyncio hot path (manifest resource reads) | Event loop stall; all requests slow while manifest is read | Use `asyncio.to_thread()` or a 1-second TTL cache for disk reads | First notable at ~500 concurrent requests (unlikely for localhost) |
| LLM generation without token cap | 60-second+ event loop Task held; UI unresponsive | `asyncio.wait_for` timeout + per-request token limit | Immediately on first slow local model or API timeout |
| Unbounded SSE event queue during synthesis burst | Memory grows; old events dropped silently | Max-size asyncio Queue + oldest-drop policy + WARNING log | ~50 synthesis events/second (possible during batch replay) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Including `raw_code` from execution log in LLM chat context | Synthesized code containing secrets or file paths leaks to LLM and potentially to logs | Inject only `intent` + `code_hash` into chat context; `raw_code` stays in JSONL |
| Not sanitizing tool names / sidecar tags before injecting into chat context | Injection markers in tool names influence LLM responses; chat surface is different from MCP `tools/list` surface | Independent sanitization pass in `build_chat_context()`; do not assume `_sanitize_tag()` covers the chat path |
| Using `str(exc)` to log DB or HTTP errors in the console API | SQLAlchemy / httpx exceptions walk their chain and include connection URLs with credentials (established in Phase 8 review) | `type(exc).__name__` only; never `str(exc)` in any logger call in forge-bridge code |
| Running Web UI without localhost binding (0.0.0.0) | Console accessible to anything on the LAN; no auth for v1.3 | Bind exclusively to `127.0.0.1` (matches `:9999` posture); document this as the v1.3 security contract |

---

## Artist-UX Failure Modes

These are qualitatively different from technical pitfalls — they produce a product that works but fails to serve its intended audience.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Dashboard title: "ExecutionLog Record Count: 47" | Artist sees jargon, doesn't know what to do | "47 Flame operations recorded" — use plain language, not class names |
| Error message: "JSONDecodeError at offset 412" surfaced to artist | Artist has no recovery path; they file a support ticket | Catch at the API layer; return "Unable to load execution history — try refreshing" with a retry button |
| Status shown as `promoted=True` / `promoted=False` | Internal dataclass field name; artist has no context | Show "Promoted to tool" / "Pending" with a visual indicator |
| Stats table sorted by internal `code_hash` | Random-looking order; no useful default | Sort by `timestamp DESC` (most recent first) by default |
| Async loading with no spinner or skeleton | Artist clicks a button and nothing happens for 3 seconds; they click again (double-submit) | Every action that takes >200ms must show a loading indicator; disable the button during the request |
| No "what now?" affordance when the console is empty | New user opens the Web UI for the first time; sees a blank panel with no guidance | Show an onboarding message when zero executions exist: "No operations recorded yet. Use Flame to start working — operations will appear here automatically." |
| Technical error details in the main panel | An exception traceback rendered in the artist's view | Log tracebacks server-side; show only a user-facing summary with an error code the operator can look up |
| Showing every synthesized tool with all its provenance fields | Information overload for an artist who just wants to know if the tool works | Default view: tool name + status (active/probation/quarantine) + last-used date; provenance drill-down on click |

**UAT criterion for artist UX:** A person who is not the developer must be able to identify the three most recently synthesized tools and their status within 30 seconds of opening the Web UI, without any explanation. If they cannot, the UI fails the artist-first test regardless of technical correctness.

---

## "Looks Done But Isn't" Checklist

- [ ] **Web UI static assets:** Template and CSS files listed in `pyproject.toml` `package-data` — verify `pip install .` from a clean venv serves assets (not just `pip install -e .`)
- [ ] **MCP resource:** Both `resources/list` and `resources/read forge://manifest/synthesis` return correct data — verify via real MCP client session, not unit test mock
- [ ] **CLI read model:** `forge-bridge console stats` output matches Web UI `/console/stats` response for same data — verify by running both after the same synthesis batch
- [ ] **JSONL reader:** Concurrent write + read produces zero `JSONDecodeError`s — verify with a stress test that runs synthesis at 10 ops/sec for 60 seconds while the console API is polled every second
- [ ] **CORS:** Web UI `fetch()` calls succeed in a real browser (not Postman / curl) — verify by opening the Web UI in Safari and Chrome and checking DevTools Network tab for CORS errors
- [ ] **Stdio mode preserved:** Existing Claude Desktop / Claude Code config (no `--http` flag) still works after v1.3 — verify by running the existing MCP integration test suite in stdio mode
- [ ] **Rate limiter:** 11 rapid chat requests from the same IP within 1 minute triggers HTTP 429 on request 11 — verify with a script, not a unit test
- [ ] **LLM timeout:** A hung `LLMRouter.generate()` returns an error to the user within 125 seconds — verify by mocking the LLM to sleep indefinitely and asserting the endpoint responds
- [ ] **Artist UX:** A non-developer can identify the three most recently synthesized tools and their status within 30 seconds — verify in a dogfood session, not a code review

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stdout corruption (P-01) — CLI breaks after adding Web UI | HIGH — requires transport rearchitecture | Switch to `mcp.run(transport="http")` + `--http` flag; audit all `print()` calls in the codebase |
| Transport switch broke Claude Desktop config (P-02) | MEDIUM | Restore stdio as default; add `--http` flag; publish patch release |
| MCP resource-only manifest with no tool fallback (P-03) — Cursor users have no manifest access | LOW | Add `forge_manifest_read` tool as a shim; no architectural change needed |
| CLI vs Web UI count divergence (P-09) | MEDIUM — requires read-model consolidation | Backtrack both surfaces to call `ConsoleReadAPI`; regression test before re-shipping |
| SPA framework embedded in pip package (P-11) | HIGH — requires UI rewrite | Rewrite UI as htmx + Jinja2; remove `package.json`, `node_modules` from repo; add templates to package-data |
| Artist UX failure (P-12 UX section) | MEDIUM | Dogfood session → list all jargon → replace with plain language in templates (no architectural change) |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P-01: Stdout corruption | Phase 9 CONTEXT.md (before any HTTP code) | MCP integration test passes while Web UI serves traffic |
| P-02: Transport switch breaks existing configs | Phase 9 CONTEXT.md (transport decision) | Existing stdio integration test passes with no `--http` flag |
| P-03: MCP resource client support | Phase that adds `forge://manifest/synthesis` resource | Both resource path + tool fallback verified via real MCP session |
| P-04: JSONL partial-line parse | Phase that implements ConsoleReadAPI | Stress test: 10 writes/sec + concurrent reads, zero JSONDecodeError |
| P-05: ManifestService drift | Phase that adds resource handler | Synthesize → immediately read resource → confirm new tool present |
| P-06: Chat prompt injection | Phase that adds LLM chat endpoint | Injection-marker in tool name does not propagate to chat context |
| P-07: Chat cost runaway | Phase that adds LLM chat endpoint | 11th rapid request returns HTTP 429 |
| P-08: LLM generation blocks event loop | Phase that adds LLM chat endpoint | Mocked infinite generation returns timeout error within 125s |
| P-09: CLI vs Web UI drift | Phase 9 (ConsoleReadAPI foundation) | Same data → same numbers in both surfaces |
| P-10: CORS misconfiguration | Phase 9 (first HTTP route) | Browser fetch() succeeds in Chrome and Safari without CORS error |
| P-11: SPA build step in pip package | Phase 9 CONTEXT.md (UI framework decision) | Fresh `pip install` from wheel serves Web UI without npm |
| P-12: SSE failure modes | Phase that adds real-time push (if in scope) | 60-second idle SSE stream shows no disconnect/reconnect |
| Artist-UX failures | Every UI phase | Dogfood session: non-developer identifies top-3 tools in <30s |

---

## Sources

- Direct codebase analysis: `forge_bridge/mcp/server.py` (v1.3.0), `forge_bridge/learning/execution_log.py`, `forge_bridge/learning/watcher.py`, `forge_bridge/learning/sanitize.py`, `.planning/PROJECT.md`, `.planning/RETROSPECTIVE.md`
- FastMCP documentation (Context7 `/prefecthq/fastmcp`): transport protocols, custom routes, HTTP mode, stdio mode constraints
- [FastMCP: Running Your Server](https://gofastmcp.com/deployment/running-server) — custom_route only in HTTP transport; stdio owns stdout exclusively
- [MCP Python SDK migration docs](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md) — resource URI type changes, subscribe capability behavior
- [Taming the Beast: FastMCP SSE with Uvicorn](https://medium.com/@wilson.urdaneta/taming-the-beast-3-lessons-learned-integrating-fastmcp-sse-with-uvicorn-and-pytest-5b5527763078) — FastMCP ASGI integration pitfalls; event loop readiness issues
- [MCP Resources vs Tools — Apigene Blog](https://apigene.ai/blog/mcp-resources) — application-controlled vs model-controlled semantics
- [Gemini CLI resources issue #3816](https://github.com/google-gemini/gemini-cli/issues/3816) — Gemini CLI does not support resources or prompts
- [Cursor MCP resources support](https://forum.cursor.com/t/mcp-resources-support/151758) — Cursor does not support resources; subscribe errors
- [LLM API Resilience in Production](https://tianpan.co/blog/2026-03-11-llm-api-resilience-production) — agent loop cost runaway patterns; $47K/week incident
- [Rate Limiting for LLM Applications](https://portkey.ai/blog/rate-limiting-for-llm-applications/) — token-aware rate limiting patterns
- [sse-starlette](https://github.com/sysid/sse-starlette) — SSE heartbeat + proxy buffering patterns
- [htmx vs React 2026](https://www.pkgpulse.com/blog/htmx-vs-react-2026) — no-build dashboard recommendation; 67% codebase reduction case study
- [CyberArk Poison Everywhere](https://www.cyberark.com/resources/threat-research-blog/poison-everywhere-no-output-from-your-mcp-server-is-safe) — injection surfaces in MCP schema fields (carried from v1.2 PITFALLS)
- Phase 8 retrospective lesson: "UAT must exercise the live production call path" (LRN-05) — prevention rationale for P-03 and P-09 UAT criteria
- Phase 8 retrospective lesson: "credential-leak via str(exc)" — source for P-10 security entry

---
*Pitfalls research for: forge-bridge v1.3 Artist Console (Web UI + CLI + MCP resources)*
*Researched: 2026-04-22*
*Previous milestone pitfalls archived at: .planning/research/PITFALLS-v1.2.md*
