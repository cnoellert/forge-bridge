# forge-bridge Troubleshooting

Recovery paths for the failure modes you'll actually hit during daily use.

Most of what goes wrong with forge-bridge isn't catastrophic — a model is still warming, a daemon was restarted, a host is briefly unreachable. This document is organized so that **observed symptom** is the entry point and a working bridge in under two minutes is the goal.

If you arrived here from a recipe, the failure-mode section header lists the recipe step that surfaces it. Return to the recipe's Verification once you've recovered.

---

## Recovery shape

Every failure-mode section in this document follows the same skeleton:

- **Symptom** — what you literally see (error text, log line, doctor row).
- **What `fbridge doctor` shows** — orient before acting. Doctor's row-level output tells you whether the issue is per-request or subsystem-level.
- **Diagnosis** — what's actually wrong, and importantly, what isn't.
- **Recovery** — the short, confidence-restoring path. Most cases recover in under two minutes.
- **Verification** — concrete signals you're back.
- **Why this happens** — archaeology for the curious; safe to skip during a recovery.

Two optional sections appear where they earn their keep:

- **If you arrived here while following...** — recipe-anchored re-entry points so you're not lost in diagnostics land mid-workflow.
- **Cross-references** — adjacent failure modes, seeds, source files.

## The operator habit this document trains

1. Symptom occurs.
2. Run `fbridge doctor`.
3. Orient from doctor's row-level summary.
4. Follow the matching failure mode's Recovery.
5. Verify and continue.

`fbridge doctor` is the single-pane orientation tool. The failure-mode sections all open with a doctor-output snapshot so you can read symptoms in operator order, not architecture order.

If doctor's output disagrees with what's documented here, doctor wins — its output reflects live state. Open an issue and we'll close the gap.

## Failure-mode coverage commitment

Every failure mode this document names must be one of:

- **Visible in `fbridge doctor` output** at a row that names the affected subsystem, OR
- **Explicitly per-request** with doctor confirming the underlying subsystems are healthy.

Failure modes that violate this commitment get `fbridge doctor` polished in-flight rather than documented around the gap. This is DIAG-05 from the v1.5 roadmap and an explicit Phase 23 scope allowance.

---

## Failure mode → DIAG requirement map

| DIAG | Failure mode |
|---|---|
| DIAG-04 | [Chat returns "Response timed out"](#failure-mode-chat-returns-response-timed-out) |
| DIAG-03 | [Chat hangs ~75 seconds, then errors](#failure-mode-chat-hangs-then-errors) |
| DIAG-01 | [Flame hook unreachable](#failure-mode-flame-hook-unreachable) |
| DIAG-02 | [Postgres restart or unavailable](#failure-mode-postgres-restart-or-unavailable) |

These four failure modes are the v1.5 ROADMAP DIAG-01..04 coverage; the order in the table follows recovery frequency (chat-side issues are the most common), not requirement numbering.

---

## Failure mode: Chat returns "Response timed out"

**Maps to:** DIAG-04
**Surfaces from:** Recipe 1 Step 8 (smoke-test), Recipe 2 first invocation, Recipe 4 Step 3, or the Artist Console chat tab.

### Symptom

A chat call returns this exact message after 60-125 seconds:

> **Response timed out — try a simpler question or fewer tools.**

HTTP 504. The Artist Console renders it as a single red error line; no traceback, no partial response. The chat history shows your prompt and the error; nothing in between.

**This usually means the model is still loading or warming, not that forge-bridge itself is broken.**

### What `fbridge doctor` shows

Doctor reports the LLM backend as healthy:

```text
$ fbridge doctor
console_port            ok     bound on :9996
instance_identity.execution_log    ok
instance_identity.manifest_service ok
flame_bridge            ok     reachable on :9999
ws_server               ok     reachable on :9998
storage_callback        ok
llm_backend.local       ok     reachable on http://localhost:11434
jsonl_parseability      ok     100 line(s) tail-parsed cleanly
daemon_state            ok
```

The key row is `llm_backend.local: ok` — Ollama is reachable and responding to forge-bridge's health probes. A budget-exceeded chat failure is a **per-request outcome**, not a subsystem failure: doctor confirms the substrate is sound.

If `llm_backend.local` reports `warn` or `fail`, this is a different failure mode → see [Failure mode: Chat hangs ~75 seconds, then errors](#failure-mode-chat-hangs-then-errors).

### Diagnosis

Two causes account for nearly all occurrences of this symptom:

1. **Cold start.** Ollama lazy-loads model weights on the first call after daemon start (or after several minutes idle). For 32B-class models on operator-workstation GPUs, the first token can take 30-60 seconds to emit — long enough that a 2-step tool-call loop exceeds forge-bridge's 120-second wall-clock budget.
2. **`qwen3:32b` configured as the model.** qwen3's thinking-mode emits roughly 10× more tokens per turn than `qwen2.5-coder:32b`. Every call sits close to the budget; cold-start calls reliably exceed it.

The model is reachable, responding, and warming. Nothing is structurally wrong.

### Recovery

**Fast path (under 2 minutes):**

1. **Resend the same prompt.** If it succeeds in 5-15 seconds, the model was cold — it's now warm in memory and the next several calls will land sub-10s. You're done.

2. If it times out again, confirm which model is configured:

    ```bash
    grep FORGE_LOCAL_MODEL /etc/forge-bridge/forge-bridge.env
    ```

    If it shows `qwen3:32b`, switch to the supported default:

    ```bash
    sudo sed -i.bak 's/qwen3:32b/qwen2.5-coder:32b/' /etc/forge-bridge/forge-bridge.env
    sudo systemctl restart forge-bridge          # Linux
    sudo launchctl kickstart -k system/com.cnoellert.forge-bridge   # macOS
    ```

    Resend. The first call after a model change is itself a cold start (30-60 s); the second call should land sub-10s.

3. If the model is already `qwen2.5-coder:32b` and the symptom persists across three resends with idle gaps under five minutes, this is not warmup. Re-check `llm_backend.local` with `fbridge doctor`. If it now reports `warn` or `fail`, go to [Failure mode: Chat hangs ~75 seconds, then errors](#failure-mode-chat-hangs-then-errors).

### Verification

You're recovered when **all three** signals hold:

- A chat call from the Artist Console returns a natural-language response in under 15 seconds.
- `fbridge doctor` reports `llm_backend.local: ok`.
- `grep FORGE_LOCAL_MODEL /etc/forge-bridge/forge-bridge.env` shows `qwen2.5-coder:32b`.

### If you arrived here while following...

- **Recipe 1 Step 8 (smoke-test the surfaces).** This is the documented first-call cold-start. Resend once; if the second call lands sub-10s, return to Recipe 1's Verification.
- **Recipe 2 (Wire Claude Desktop).** Claude Desktop's first `forge_*` tool invocation pays the same cold-start cost. Return to Recipe 2's Verification once the warm call lands fast.
- **Recipe 4 Step 3 (Drive Flame from chat).** The first prompt of a session is a cold start. If subsequent prompts stay slow, the model is wrong (Recovery Step 2), not cold.

### Why this happens

forge-bridge's chat path wraps the LLM tool-call loop in a 120-second wall-clock budget (`forge_bridge/llm/router.py` — `max_seconds=120.0`) with an outer chat-handler timeout of 125 seconds (`forge_bridge/console/handlers.py:1294`). When the budget fires, the router raises `LLMLoopBudgetExceeded`; the handler converts it to HTTP 504 and the user-facing "Response timed out — try a simpler question or fewer tools" message.

That budget was calibrated for a warm `qwen2.5-coder:32b` — emits ~50 tokens per turn, completes a typical 2-step tool-call loop in well under 60 seconds. On `qwen3:32b`, thinking-mode verbosity (400-525 tokens per turn) pushes the same 2-step loop to 55-75 seconds warm and beyond 120 seconds cold. This was confirmed empirically on assist-01 during Phase 17: cold-start qwen3 hit iter-1=55.2 s and blew the baseline budget; warm + extended 180s budget passed at 58.0 s total elapsed. The default model bump from `qwen2.5-coder:32b` → `qwen3:32b` is deferred to v1.6+ pending one of: a default-budget bump, a per-model thinking-mode-suppression directive, or a router-init warmup ping.

### Cross-references

- Recipe 1 Common pitfall: "qwen3:32b as the default model" — preventive guidance for the same condition.
- `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` — full empirical archaeology and the v1.6+ trigger conditions for the model bump.
- `forge_bridge/llm/router.py` — `_DEFAULT_LOCAL_MODEL` definition (line 113) and the `max_seconds` budget plumbing.
- `forge_bridge/console/handlers.py:1294` — chat-handler outer 125s `asyncio.wait_for` cap.

---

## Failure mode: Chat hangs ~75 seconds, then errors

**Maps to:** DIAG-03
**Surfaces from:** Recipe 1 Step 8 (smoke-test), Recipe 4 Step 3, or the Artist Console chat tab — typically after a network change, an Ollama restart, or a misconfigured `FORGE_LOCAL_LLM_URL`.

### Symptom

A chat call hangs for ~75 seconds — no streaming output, no partial response — then returns:

> **Chat error — check console for details.**

HTTP 500. The Artist Console renders it as a single red error line. The chat history shows your prompt and the error; nothing in between.

The ~75-second wait is the dead giveaway. DIAG-04 (cold start) waits 60-125 seconds for a *responsive* model that's just slow. DIAG-03 waits ~75 seconds because the OS gave up trying to *connect* to a host that isn't there.

**This usually means Ollama is down, or the configured URL is pointing somewhere Ollama isn't — not that forge-bridge itself is broken.**

### What `fbridge doctor` shows

Doctor reports the LLM backend as degraded:

```text
$ fbridge doctor
console_port            ok     bound on :9996
instance_identity.execution_log    ok
instance_identity.manifest_service ok
flame_bridge            ok     reachable on :9999
ws_server               ok     reachable on :9998
storage_callback        ok
llm_backend.local       warn   model=qwen2.5-coder:32b
jsonl_parseability      ok
daemon_state            ok
```

The key row is `llm_backend.local: warn`. forge-bridge classifies LLM backends as degraded-tolerant — the bridge keeps running for non-chat surfaces (Read API, Flame hook, Artist Console views, MCP tools) even when the LLM is unreachable. Chat is the surface that breaks first.

The detail field currently reports `model=<name>` rather than the reachability state. That's a known gap (a follow-up Phase 23 commit will polish doctor to surface `reachable at <url>` vs `unreachable at <url>` directly). For now, the `warn` row plus the ~75-second hang symptom is your signal that Ollama isn't responding at the configured URL.

If `llm_backend.local: ok` *and* you're seeing the symptom, this is a different failure mode — most likely DIAG-04. The ~75-second hang is structural to OS-level connect timeouts; a budget-exceeded failure on a reachable LLM doesn't look like this.

### Diagnosis

Three causes account for nearly all occurrences:

1. **Ollama isn't running** on the host `FORGE_LOCAL_LLM_URL` points at. The daemon stopped, the box restarted, or it never started.
2. **`FORGE_LOCAL_LLM_URL` points at the wrong host.** Studios that run Ollama on a dedicated LLM service host (so Flame can keep the workstation GPU) sometimes drift between hostnames, ports, or VPN states.
3. **The LLM host is reachable but the port isn't.** Firewall, security group, or Ollama bound to `127.0.0.1` instead of `0.0.0.0` on a remote host.

forge-bridge itself is healthy. It's faithfully waiting on a TCP connect that the OS will eventually give up on.

### Recovery

**Fast path (under 2 minutes):**

1. **Confirm the configured URL:**

    ```bash
    grep FORGE_LOCAL_LLM_URL /etc/forge-bridge/forge-bridge.env
    ```

    Note the host and port (default is `http://localhost:11434/v1`).

2. **Probe Ollama directly from the bridge host:**

    ```bash
    curl -s --max-time 5 http://YOUR-LLM-HOST:11434/api/version
    ```

    - **JSON with a `version` field returns in <1 s** → Ollama is up. The bridge env points elsewhere or the bridge daemon needs a restart to pick up an env change. Skip to step 4.
    - **`curl: (7) Failed to connect`** → Ollama isn't listening at that host:port. Continue to step 3.
    - **`curl: (28) timed out`** → host is unreachable (DNS, firewall, VPN). Fix the network path, then re-probe.

3. **Start Ollama if it's stopped:**

    - **macOS:** `open -a Ollama` (or relaunch the Ollama menu-bar app)
    - **Linux:** `sudo systemctl start ollama`

    Re-run the `curl` probe from step 2. Once it returns `version` JSON, Ollama is up.

4. **Restart the bridge daemon** so the LLM client reconnects:

    ```bash
    sudo systemctl restart forge-bridge          # Linux
    sudo launchctl kickstart -k system/com.cnoellert.forge-bridge   # macOS
    ```

    Wait ~15 seconds for the daemon to come back. Run `fbridge doctor` — `llm_backend.local` should now report `ok`.

5. **Resend the chat prompt.** The first call is a cold start (30-60 s — see [Failure mode: Chat returns "Response timed out"](#failure-mode-chat-returns-response-timed-out)); the second call should land sub-10 s.

### Verification

You're recovered when **all three** signals hold:

- `curl -s http://YOUR-LLM-HOST:11434/api/version` returns JSON with a `version` field.
- `fbridge doctor` reports `llm_backend.local: ok`.
- A chat call from the Artist Console returns a natural-language response (allow up to 60 s for the first call; expect sub-10 s after).

### If you arrived here while following...

- **Recipe 1 Step 3 (Verify Ollama reachability).** This is the install-time variant of the same probe. If `curl` to `:11434/api/version` returns a connection error, fix the network path / start the Ollama daemon, then continue Recipe 1 from Step 3.
- **Recipe 1 Step 8 (smoke-test the surfaces).** A chat hang during the smoke test usually means Ollama wasn't running when the bridge started. Step 4 of this section's Recovery (restart the bridge) is what closes the loop.
- **Recipe 4 Step 3 (Drive Flame from chat).** Same recovery path — Ollama needs to be reachable before chat-driven Flame automation works.

### Why this happens

The chat path calls `LLMRouter.complete_with_tools()` → `OllamaToolAdapter.send_turn()` → `ollama.AsyncClient` → `httpx` → the OS-level TCP connect. When the target host is unreachable on IPv4, the OS waits for the default connect timeout to expire before reporting failure — roughly 75 seconds on macOS, varying on Linux depending on `tcp_syn_retries`. No application-level connect-timeout is configured today: the lazy-construction site at `forge_bridge/llm/router.py:867-870` builds the client with default httpx transport settings.

The router catches the eventual connect error and raises `LLMToolError`; the chat handler at `forge_bridge/console/handlers.py:1336` converts that to HTTP 500 and the user-facing "Chat error — check console for details" message.

A 5-second application-level connect-timeout would convert this 75-second silent wait into a 5-second explicit "Ollama unreachable at `<url>`" error. The fix is in scope for v1.5 chat-reliability polish but lives outside Phase 23's documentation scope. Trigger conditions and implementation sketch are in `.planning/seeds/SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+.md`. A broader audit of every external dependency's connect-timeout config (Postgres, Anthropic, Flame, state_ws) is captured in `SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+.md`.

### Cross-references

- Recipe 1 Step 3 — install-time Ollama reachability probe (the same `curl` used here for recovery).
- `.planning/seeds/SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+.md` — the application-level connect-timeout fix that would convert the 75 s wait into a 5 s explicit error.
- `.planning/seeds/SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+.md` — broader audit of every external-dependency connect-timeout site.
- `forge_bridge/llm/router.py:844-871` — `_get_local_native_client` lazy-construction site (no connect-timeout config today).
- `forge_bridge/console/handlers.py:1336` — chat-handler `LLMToolError` → HTTP 500 path.

---

## Failure mode: Postgres restart or unavailable

**Maps to:** DIAG-02
**Surfaces from:** Recipe 5 Step 1 (list staged operations), Claude Desktop or chat-driven `forge_list_staged` / `forge_get_staged` / `forge_approve_staged` / `forge_reject_staged` calls, or any staged-ops or dependency-graph query.

### Symptom

Staged-ops MCP tools return errors that name an asyncpg or SQLAlchemy exception class:

> Tool error: ConnectionRefusedError
> Tool error: OperationalError: could not connect to server

Other surfaces stay alive:

- Artist Console UI renders; tools / execs / health views work.
- Chat answers normally for prompts that don't touch staged-ops tools.
- Synthesis pipeline keeps recording observations to JSONL.
- Flame hook on `:9999` executes code as usual.
- `fbridge doctor` itself runs and reports most rows as `ok`.

**The bridge is degraded, not dead.** forge-bridge's storage architecture is **JSONL-authoritative + SQL-mirror** — the JSONL execution log at `~/.forge-bridge/executions.jsonl` is the source of truth, and Postgres is a mirror of it. When the mirror is unreachable, the source-of-truth path keeps running. The surfaces that DO break are the ones that read from SQL directly (staged operations on the `staged_operation` table, dependency-graph queries).

### What `fbridge doctor` shows

Doctor today doesn't probe Postgres reachability directly:

```text
$ fbridge doctor
console_port            ok     bound on :9996
instance_identity.execution_log    ok
instance_identity.manifest_service ok
flame_bridge            ok     reachable on :9999
ws_server               ok     reachable on :9998
storage_callback        ok     callback attached
postgres                warn   unreachable: ConnectionRefusedError
llm_backend.local       ok     reachable; model=qwen2.5-coder:32b
jsonl_parseability      ok     100 line(s) tail-parsed cleanly
daemon_state            ok
```

The key row is `postgres: warn`. Detail names the failure shape:

- `unreachable: ConnectionRefusedError` — Postgres process is down or not bound to the configured port.
- `unreachable: TimeoutError after 2.0s` — host reachable but the query hung past doctor's bounded probe budget.
- `unreachable: <other class name>` — auth failure, protocol error, etc.

Doctor probes Postgres reachability directly by opening an async session via the daemon's actual `get_session()` factory and running `SELECT 1` within a 2.0-second bound. The bound is aggressive deliberately — doctor must remain psychologically responsive during a Postgres outage; an unbounded probe would invert the trust the doctor surface is trying to establish.

#### `storage_callback` and `postgres` are orthogonal

These two rows answer independent questions. `storage_callback` reports **integration topology** (is the SQL-mirror callback wired into the execution log?). `postgres` reports **backend availability** (is the SQL backend reachable and queryable?). Their states vary independently:

| `storage_callback` | `postgres` | Operational meaning |
|---|---|---|
| `ok` | `ok` | Full SQL mirror operational |
| `ok` | `warn` | Mirror configured, backend down — writes fail, JSONL still authoritative |
| `absent` | `ok` | Substrate ready, no consumer wired (Track B / stock install) |
| `absent` | `warn` | Substrate dormant AND backend down — non-SQL surfaces still operational |

This 4-state table is the substrate/consumer split rendered directly in the doctor output. `storage_callback: absent` is a normal, healthy state on a stock install — the bridge ships the synthesis substrate; consumers (projekt-forge in production) wire the SQL mirror callback when they need it. Don't read `absent` as suspicious.

The `postgres` row is classified **degraded-tolerant**: when the probe fails, doctor surfaces `warn` (not `fail`) because the bridge stays substantially operational during a Postgres outage. The aggregate health status flips to `degraded`, not `fail`. This is the operational-survivability invariant — doctor severity reflects what's usable, not what's impaired.

If staged-ops tools succeed normally and `postgres: ok`, this is not the failure mode you're hitting.

### Diagnosis

The "degraded vs dead" distinction is what makes recovery feel safe here. The bridge keeps working for most surfaces during a Postgres outage:

| Surface | Behavior when Postgres is down |
|---|---|
| Synthesis pipeline | Works — JSONL log is authoritative |
| Watcher / probation | Works — filesystem-based |
| Artist Console UI | Renders; non-SQL views work |
| Chat (non-staged-ops paths) | Works |
| Flame hook | Works — independent of SQL |
| Staged operations (list / get / approve / reject) | **Fail — require SQL session** |
| Dependency-graph queries | **Fail — require SQL session** |
| SQL-mirror writes from synthesis | Fail silently; JSONL writes already succeeded |

Two common causes:

1. **Postgres daemon stopped or crashed.** The OS service exited; nothing is bound to the configured port.
2. **`FORGE_DB_URL` points at a Postgres that's unreachable.** Network change, firewall, VPN, or a remote Postgres host that restarted.

forge-bridge itself is healthy. The SQL mirror is what's offline.

### Recovery

**Fast path (under 2 minutes):**

1. **Verify Postgres is actually down:**

    ```bash
    pg_isready -h YOUR-PG-HOST -p 5432
    ```

    - `accepting connections` → Postgres is up. The bridge daemon may need a connection-pool reset. Skip to Step 4.
    - `no response` / `rejecting connections` → continue to Step 2.

2. **Confirm the bridge env points at the right Postgres:**

    ```bash
    grep FORGE_DB_URL /etc/forge-bridge/forge-bridge.env
    ```

    Default is `postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge`. If this points at a remote host, that's where Postgres must be running.

3. **Start or restart Postgres:**

    - **Linux (systemd):** `sudo systemctl restart postgresql` (substitute the actual unit name — `postgresql-16`, etc.).
    - **macOS (Homebrew):** `brew services restart postgresql@16`.
    - **Flame host with Autodesk-bundled Postgres:** see INSTALL.md Step 3a — the bootstrap script's Postgres detection logic identifies the right binary.

    Re-run `pg_isready` until it reports `accepting connections`.

4. **Restart the bridge daemon** to reset its connection pool:

    ```bash
    sudo systemctl restart forge-bridge          # Linux
    sudo launchctl kickstart -k system/com.cnoellert.forge-bridge   # macOS
    ```

5. **Retry the staged-ops call that failed.** It should now succeed.

### Verification

You're recovered when **all three** signals hold:

- `pg_isready -h YOUR-PG-HOST -p 5432` reports `accepting connections`.
- `forge_list_staged` (from chat, Claude Desktop, or `fbridge run forge_list_staged`) returns successfully — an empty list is a healthy response on a freshly-bootstrapped install.
- The staged-ops surface from Recipe 5 Step 1 works end-to-end.

### If you arrived here while following...

- **Recipe 5 Step 1 (List the staged operations).** This is the most common arrival path — staged-ops are the surface that's most sensitive to a Postgres outage. Once `forge_list_staged` returns successfully, return to Recipe 5 Step 2.
- **Recipe 3 (Observe the synthesis pipeline).** Surprising-but-correct: Recipe 3 *won't* surface this failure mode. The synthesis pipeline writes JSONL (authoritative path) and the watcher reads from filesystem — neither touches Postgres on the hot path. SQL-mirror writes fail silently in the background until Postgres returns, but the synthesis observation has already been recorded canonically.
- **Recipe 1 Step 4 (Bootstrap script).** If the bootstrap script itself failed because Postgres wouldn't accept connections, this section's recovery path (verify reachability, start Postgres, re-run) applies before re-attempting the bootstrap.

### Why this happens

forge-bridge's storage layer is built on a deliberate split:

- **JSONL is canonical.** The execution log at `~/.forge-bridge/executions.jsonl` is the source of truth for every observation the bridge records. Nothing else takes its place; nothing else can.
- **SQL is a mirror.** Postgres persistence is wired in as a storage callback on the `ExecutionLog`. When the callback fires successfully, the same observation is mirrored to the `execution` table; when the callback fails, the failure is logged and the JSONL write already succeeded — the source of truth is preserved.

This architecture is intentional. The bridge stays usable as a synthesis substrate and Flame coordinator during Postgres outages — only the surfaces that require SQL queries (staged operations on the `staged_operation` table, dependency-graph queries) actually fail. This is the **substrate/consumer** pattern from Recipes 3 and 5 manifesting at the failure-mode level: the substrate stays operational; only the consumer-facing surfaces break.

Postgres-dependent surfaces fail per-request, not at daemon startup. The bridge daemon does NOT refuse to start when Postgres is unreachable — it comes up cleanly and surfaces the failure when an operator triggers a SQL-touching code path. The `postgres` doctor row makes this visible at the orientation layer: an operator running `fbridge doctor` sees `postgres: warn` immediately, without having to invoke a SQL-touching tool to discover the outage.

The doctor row's classification deserves a note. `postgres: fail` in the health body downgrades to `postgres: warn` at the doctor surface. Future contributors will eventually ask "why isn't postgres surfaced as fail?" — the answer is the operational-survivability invariant: doctor severity reflects what's usable, not what's impaired. Surfacing `fail` at the orientation layer would contradict the substrate/consumer architectural truth this section teaches. The aggregate health status flips to `degraded` (correct) rather than `fail` (would be wrong).

### Cross-references

- Recipe 5 (Approve a staged operation) — the workflow this section's symptom most often blocks.
- Recipe 3 (Observe the synthesis pipeline) — the workflow that explicitly does NOT break under this failure mode, by architectural design.
- `CLAUDE.md` "Postgres persistence layer" + "Learning pipeline" + "Staged operations platform" subsystem bullets — substrate/consumer architectural framing.
- `.planning/seeds/SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+.md` — broader audit of every external-dependency probe site (Postgres included).
- `forge_bridge/store/session.py:40` — `DEFAULT_DB_URL` definition.
- `forge_bridge/console/read_api.py:463-475` — `storage_callback` row derivation today (the registered-vs-reachable gap).
- `docs/INSTALL.md` Step 3a — Postgres bootstrap path on Flame-bundled installs.

---

## Failure mode: Flame hook unreachable

**Maps to:** DIAG-01
**Surfaces from:** Recipe 4 (drive Flame from chat), Recipe 1 Step 5 (install Flame hook), Recipe 1 Step 8 (smoke-test), or `fbridge flame ping`.

### Symptom

You try to drive Flame from chat (Recipe 4) and one of three things happens:

1. **`forge_*` Flame tools aren't offered to the LLM.** The chat answers about Flame but says it doesn't have access to Flame tools right now. Claude Desktop's tool catalogue is missing the `flame_*` entries that should appear.
2. **`fbridge flame ping` returns connection refused** (or non-zero exit with a network error).
3. **A direct `curl http://localhost:9999/status` returns connection refused** — the Flame hook's HTTP server isn't bound.

In every variant, the rest of the bridge keeps working: chat answers about non-Flame topics, `forge_list_staged` still queries staged operations, the Artist Console UI renders, synthesis observations keep recording to JSONL.

**This usually means Flame is closed, asleep, or its hook never loaded — not that forge-bridge itself is broken.** The Flame integration surface is unavailable; the bridge's other surfaces are not.

### What `fbridge doctor` shows

Doctor reports the Flame bridge as degraded:

```text
$ fbridge doctor
console_port            ok     bound on :9996
instance_identity.execution_log    ok
instance_identity.manifest_service ok
flame_bridge            warn   ConnectError
ws_server               ok     reachable on :9998
storage_callback        ok
postgres                ok     reachable; SELECT 1 succeeded
llm_backend.local       ok     reachable; model=qwen2.5-coder:32b
jsonl_parseability      ok
daemon_state            ok
```

The key row is `flame_bridge: warn`. The detail field names the failure shape:

- `ConnectError` — nothing is listening on `:9999`. Flame is closed, the hook never loaded, or the workstation is asleep.
- `TimeoutError` or similar — `:9999` accepts connections but the hook hangs. Rare; usually means Flame is mid-launch or the hook thread is wedged.
- `http 5xx` — hook is up but reporting an error.

The Phase 07.1 graceful-degradation contract is intentional here: the bridge classifies `flame_bridge` as a degraded-tolerant subsystem because the daemon must stay operational for every non-Flame surface (chat, synthesis, manifests, staged ops, console UI) when Flame happens to be closed. Same architectural philosophy as `postgres` and `llm_backend.local` — `warn`, not `fail`, because operational survivability is not at stake.

If `flame_bridge: ok`, this is not the failure mode you're hitting.

### Diagnosis

Verify Flame-side state before suspecting bridge-side problems. The likely causes, in order of operator frequency:

1. **Flame isn't running.** Most common — the operator closed Flame, the workstation rebooted, or Flame has never been launched in this session.
2. **The Flame hook isn't loaded.** `./scripts/install-flame-hook.sh` was never run, or it was run for a different Flame version than the one currently launched.
3. **The workstation is asleep or screen-locked.** macOS App Nap or Linux suspend can pause the hook's HTTP listener even though Flame appears running.
4. **Port mismatch.** `FORGE_BRIDGE_PORT` was overridden in the Flame hook env to something other than `9999`, or another process bound `:9999` first.
5. **Local firewall.** Rare on operator workstations; only matters when Flame and the bridge daemon are on different hosts (unusual configuration).

forge-bridge itself is healthy. The Flame integration surface is what's offline.

### Recovery

**Fast path (under 2 minutes):**

1. **Is Flame actually running?** Check the dock, menu bar, or task list. If it's not running, launch it. The hook auto-starts on Flame launch (per `flame_hooks/forge_bridge/scripts/forge_bridge.py:332` — `app_initialized`).

2. **Is the hook reachable?**

    ```bash
    curl -s --max-time 3 http://localhost:9999/status
    ```

    - **JSON with `"status":"running"` and `"flame_available":true`** → hook is up; the bridge daemon may need a connection-pool reset. Skip to Step 4.
    - **JSON with `"flame_available":false`** → hook is up but Flame's Python namespace doesn't have the application context yet. Open or relaunch a Flame project; the hook needs an active Flame app context. Re-curl to confirm `flame_available:true`.
    - **`curl: (7) Failed to connect`** → hook isn't listening. Continue to Step 3.
    - **`curl: (28) timed out`** → hook is wedged. Quit and relaunch Flame.

3. **Is the hook installed?** If the previous step returned connection refused even with Flame running, the hook isn't loaded:

    ```bash
    ls ~/Library/Preferences/Autodesk/flame/python/forge_bridge/  # macOS
    ls ~/.config/Autodesk/flame/python/forge_bridge/              # Linux (path varies)
    ```

    No directory → run `./scripts/install-flame-hook.sh` (from the forge-bridge repo). Then **relaunch Flame**. Hooks are only loaded at Flame startup; an already-running Flame won't pick up a freshly-installed hook.

4. **Restart the bridge daemon** so its reachability cache refreshes:

    ```bash
    sudo systemctl restart forge-bridge          # Linux
    sudo launchctl kickstart -k system/com.cnoellert.forge-bridge   # macOS
    ```

    Wait ~15 seconds for the daemon to come back. Run `fbridge doctor` — `flame_bridge` should now report `ok`.

5. **Retry the chat / Claude Desktop call that failed.** The `forge_*` Flame tools should now be in the catalogue and invokable.

### Verification

You're recovered when **all four** signals hold:

- `curl -s http://localhost:9999/status` returns JSON with `"flame_available":true`.
- `fbridge doctor` reports `flame_bridge: ok`.
- `fbridge flame ping` exits 0 with a success line.
- Recipe 4 Step 3 works end-to-end — a chat-driven Flame tool call returns a non-error response.

### If you arrived here while following...

- **Recipe 4 (Drive Flame from chat).** This is the most psychologically expensive arrival path — you were mid-workflow trying to orchestrate Flame and the call failed. The bridge is not broken; Flame's integration surface is unavailable. Once `fbridge doctor` reports `flame_bridge: ok`, return to Recipe 4 Step 3 and re-issue the prompt. The same chat session is fine; you don't need to start over.
- **Recipe 1 Step 5 (Install the Flame hook).** This is the install-time variant. If `./scripts/install-flame-hook.sh` ran successfully but the hook is still unreachable, you almost certainly need to **relaunch Flame** — hooks are loaded only at Flame startup, not dynamically.
- **Recipe 1 Step 8 (Smoke-test the surfaces).** Connection refused on `:9999` during smoke-test is the same recovery path; the bootstrap doesn't auto-start Flame for you.
- **Recipe 5 (Approve a staged operation).** Staged operations that proxy a Flame call (rename, set start frames, publish shots) will fail at the execute step when Flame is unreachable. The staging itself (proposed → approved) works without Flame; only the execution step needs it.

### Why this happens

The Flame hook is a separate process lifecycle from the bridge daemon. The hook lives inside Flame's address space — it auto-starts when Flame's `app_initialized` callback fires (`flame_hooks/forge_bridge/scripts/forge_bridge.py:332`) and dies when Flame quits. The bridge daemon has no way to start Flame on the operator's behalf and intentionally doesn't try; Flame is the operator's primary application, not the bridge's.

Phase 07.1 hardened the graceful-degradation contract for exactly this case. Pre-07.1, an unreachable Flame hook could prevent the daemon from starting cleanly. Post-07.1, the daemon classifies `flame_bridge` as a degraded-tolerant subsystem at startup — it comes up cleanly, reports `flame_bridge: warn` at doctor, and filters Flame-dependent MCP tools out of the catalogue (`forge_bridge/console/_tool_filter.py:149`) so the chat path doesn't offer tools that will fail.

The doctor row's classification is the same operational-survivability invariant that `postgres` and `llm_backend.local` honor: **doctor severity reflects what's usable, not what's impaired.** Surfacing `flame_bridge: fail` would imply the bridge is broken, when in reality only the DCC-orchestration surface is offline. The four-row degraded-tolerant set — `flame_bridge`, `ws_server`, `storage_callback`, `postgres`, `llm_backend.*` — collectively renders forge-bridge's middleware architecture at the doctor surface: layered subsystems that can degrade independently, each preserving its own truth without dragging the others down.

### Cross-references

- Recipe 4 (Drive Flame from chat) — the workflow this section's symptom most often blocks.
- Recipe 1 Step 5 (install Flame hook) — install-time path; relaunch-Flame requirement noted here too.
- `flame_hooks/forge_bridge/scripts/forge_bridge.py` — the hook source (the thing that runs inside Flame on `:9999`).
- `flame_hooks/forge_bridge/scripts/forge_bridge.py:332` — `app_initialized` callback (where the hook auto-starts).
- `forge_bridge/console/_tool_filter.py:149` — `filter_tools_by_reachable_backends` (the catalog-filtering machinery that hides Flame tools when the hook is unreachable).
- `forge_bridge/bridge.py:112` — `execute()` (the HTTP client that makes the actual `POST /exec` calls).
- Phase 07.1 close artifacts in `.planning/phases/07.1-startup-bridge-graceful-degradation-hotfix-deployment-uat/` — the graceful-degradation contract origin.

---

## Failure mode: `flame_bridge` dispatch target mismatch (config-context divergence)

**Maps to:** Phase 24.2 architectural correction.
**Surfaces from:** `fbridge doctor` reporting `flame_bridge: dispatch target mismatch — daemon=... shell=...`, OR a chat call producing `flame_execute_python` invocations that all fail with `status=transport_error` despite the Flame hook being reachable from your shell.

### Symptom

You hit one of two presentations:

1. **Doctor row is explicit.** `fbridge doctor` produces a row like:

    ```text
    flame_bridge   fail   dispatch target mismatch — daemon=http://127.0.0.1:9998 shell=http://127.0.0.1:9999
    ```

    Both URLs appear; the row tells you the daemon and your shell disagree about where the Flame hook lives.

2. **Chat appears to converge but every Flame call fails fast.** The model picks `flame_execute_python` (or a `flame_*` tool), the call returns in ~10–15ms with a transport error, and the model retries against the same misrouted target. `fbridge doctor` may or may not surface the divergence depending on the order in which the daemon was reconfigured — but the divergence is structurally what's wrong.

A direct probe of the Flame hook from your shell succeeds:

```bash
$ curl -s http://localhost:9999/status
{"status":"running","flame_available":true,...}
```

So Flame and its hook are fine. So is the bridge daemon itself (Console renders, chat replies, `fbridge doctor` produces output). What's wrong is **the daemon's view of where the Flame hook is** disagrees with **your shell's view**.

### What `fbridge doctor` shows

Post Phase 24.2, the `flame_bridge` row exercises a daemon-routed dispatch probe rather than a passive `:9999/status` GET — doctor POSTs to the running daemon's `/api/v1/exec` and asks it to call `flame_ping`. The daemon's response echoes its own effective `bridge.BRIDGE_URL`. Doctor compares that against the URL it would compute itself from your shell env.

When they agree, you see:

```text
flame_bridge   ok     running (daemon dispatches http://127.0.0.1:9999)
```

When they disagree, you see the divergence rendered explicitly:

```text
flame_bridge   fail   dispatch target mismatch — daemon=http://127.0.0.1:9998 shell=http://127.0.0.1:9999
               → FORGE_BRIDGE_HOST/PORT is set differently in the daemon's
                 environment than in your shell. Unset it in the daemon's
                 launchd/systemd env and restart the daemon, OR set it in
                 your shell to match.
```

The `daemon=` URL is **authoritative** — that's where dispatch will actually go. The `shell=` URL is **diagnostic** — that's what your shell would have predicted. Doctor surfaces both so you can see which world is wrong without guessing.

### Diagnosis

The daemon runs under `launchd` (macOS) or `systemd` (Linux); your shell runs the env you sourced from your dotfiles. The two environments are independent process contexts. If `FORGE_BRIDGE_HOST` or `FORGE_BRIDGE_PORT` is set in only one of them — or set differently in each — the daemon's bridge client and your shell's view of the Flame hook will disagree.

The most common cause is an operator-side install-script edit that set `FORGE_BRIDGE_PORT` in the daemon's launchd plist (typically to move state_ws off `:9998` onto a custom port, then forgetting that the same env name controls a different role in `forge_bridge/bridge.py`). The bridge client silently followed the env to a port that doesn't speak HTTP, every dispatch RST'd in ~12ms, and your shell continued to see the correct hook because *your* shell env wasn't touched.

The substrate is fine. The Flame hook is fine. Doctor's two-world view is what's wrong — and Phase 24.2 made that visible.

### Recovery

**Fast path (under 2 minutes):**

1. **Inspect the daemon's effective environment.** macOS:

    ```bash
    launchctl print system/com.cnoellert.forge-bridge | grep -i FORGE_
    # or, for a user-session daemon:
    launchctl print gui/$(id -u)/com.cnoellert.forge-bridge | grep -i FORGE_
    ```

    Linux:

    ```bash
    systemctl show forge-bridge --property=Environment
    # or read the service file directly:
    sudo cat /etc/systemd/system/forge-bridge.service | grep Environment
    ```

    Note any `FORGE_BRIDGE_HOST` or `FORGE_BRIDGE_PORT` values that don't match the default (`127.0.0.1` / `9999`).

2. **Decide which side is wrong.** The default is `127.0.0.1:9999`. If your shell or your `~/.zshrc` / `~/.bashrc` exports a non-default, that's probably load-bearing for some other workflow — leave it and fix the daemon side instead. If the daemon's launchd/systemd env has a value that doesn't match where the Flame hook is actually listening (likely the case — the warm-probe diagnostic that exposed this on portofino had `FORGE_BRIDGE_PORT=9998` in launchd aimed at the WebSocket port), unset it.

3. **Unset the daemon-side override.** macOS:

    ```bash
    # Edit the LaunchDaemon plist that sets the env. Common paths:
    sudo vi /Library/LaunchDaemons/com.cnoellert.forge-bridge.plist
    # Remove the <key>FORGE_BRIDGE_PORT</key> / <string>...</string> pair from
    # the EnvironmentVariables dict. Save.
    ```

    Linux:

    ```bash
    sudo systemctl edit forge-bridge
    # Remove the [Service] Environment=FORGE_BRIDGE_PORT=... line. Save.
    ```

4. **Restart the daemon:**

    ```bash
    # macOS
    sudo launchctl kickstart -k system/com.cnoellert.forge-bridge
    # or:
    sudo launchctl bootout system/com.cnoellert.forge-bridge && \
    sudo launchctl bootstrap system/Library/LaunchDaemons/com.cnoellert.forge-bridge.plist

    # Linux
    sudo systemctl daemon-reload && sudo systemctl restart forge-bridge
    ```

    Wait ~15 seconds.

5. **Re-run doctor:**

    ```bash
    fbridge doctor
    ```

    The `flame_bridge` row should now report `ok` with `daemon=` and `shell=` agreeing (or just `running (daemon dispatches http://127.0.0.1:9999)`).

### Verification

You're recovered when **all three** signals hold:

- `fbridge doctor` reports `flame_bridge: ok` with the daemon-effective URL matching `http://127.0.0.1:9999` (or whichever URL is correct for your install).
- A chat call that picks `flame_execute_python` returns a real Flame result with `status=ok` graph emission at `~/.forge-bridge/graphs/<graph_id>.jsonl` — NOT `status=transport_error` in ~12ms.
- `fbridge flame-exec "import flame; print(flame.project.current_project.name)"` succeeds and surfaces the project name.

### If you arrived here while following...

- **Recipe 4 (Drive Flame from chat).** Same recovery path; the symptom often presents as the chat looping on `flame_execute_python` because affordance recovery finds the right tool but every dispatch silently RSTs.
- **Recipe 1 Step 6 (Bring up forge-bridge).** Install-time variant. If the bootstrap script set a non-default `FORGE_BRIDGE_PORT` in the daemon's env, that's the source. Unset it; the install default is `9999` and the Flame hook installer also uses `9999` by default.
- **Recipe 1 Step 8 (Smoke-test the surfaces).** `curl http://localhost:9999/status` succeeding while `fbridge doctor` reports `flame_bridge: fail` with `dispatch target mismatch` is the canonical signature of this failure mode.

### Why this happens

Pre Phase 24.2, doctor probed `:9999/status` directly from its own process. Doctor read `FORGE_BRIDGE_HOST/PORT` from the operator's shell env, the daemon read the same names from its own launchd/systemd env, and the two computations could disagree silently. Doctor would report `flame_bridge: ok` based on **its own view** of where the hook lives, even when the daemon was misrouting every dispatch.

Phase 24.2 collapsed this two-world divergence by re-rooting the doctor probe through the daemon. Doctor now asks the running daemon to call `flame_ping` (the chain engine's deterministic path); the daemon's response echoes its own effective `bridge.BRIDGE_URL`. Doctor compares that against its own re-derived URL and surfaces the divergence directly.

**The architectural invariant:** the health surface reflects daemon-observed dispatch truth, not independently reconstructed local truth. Doctor never falls back to a re-derived local probe under degradation — daemon truth or no truth. Shell-derived config remains *diagnostic context* for divergence detection; it is never authoritative.

This is one specific operational asymmetry (operator-shell env vs daemon-launchd env). It is not generalized distributed config reconciliation, service discovery, config orchestration, or runtime topology management — those patterns are not what Phase 24.2 introduces. The single failure mode this section documents is the only divergence class doctor currently surfaces; if a future operational truth gap appears under a different daemon-side surface, that's a separate phase.

### Cross-references

- `.planning/milestones/v1.6-PHASE-24-2-FRAMING.md` — the architectural diagnosis + Q1-Q4 convergence record.
- `forge_bridge/cli/runtime_doctor.py:_check_flame_bridge` — the daemon-routed probe implementation.
- `forge_bridge/console/read_api.py:_check_flame_bridge` — the Console mirror probe (in-process direct call to `utility.ping`).
- `forge_bridge/tools/utility.py:ping` — the `flame_ping` MCP tool, which echoes the daemon's effective `bridge.BRIDGE_URL`.
- `forge_bridge/config.py` — the role-separated port env vars (`FORGE_CONSOLE_PORT` / `FORGE_MCP_PORT` / `FORGE_STATE_WS_PORT` / `FORGE_BRIDGE_PORT`) and their `9996` / `9997` / `9998` / `9999` defaults.
- Phase 24.2 commit `7fdacf7` (`feat(24.2): doctor truth ↔ effective dispatch truth — daemon-routed flame_bridge probe`) — the substrate-correction commit that introduced this row taxonomy.

---

## Failure mode: `ModuleNotFoundError: No module named 'forge_bridge'` (editable-install anchor lost)

**Surfaces from:** any `fbridge <subcommand>`, `python -m forge_bridge`, `python -c "import forge_bridge"`, or `pytest` invocation in a conda env where the package was previously installed editable. Distinctive signature: the `fbridge` console script is still on `$PATH` (so the install looked fine), but Python can't actually import the package.

> **Scope note.** This failure mode is structurally pre-runtime — the daemon never starts and `fbridge doctor` can't run, so it falls outside the doctor-coverage commitment that governs the DIAG-01..04 sections above. It lives here because the symptom is real, the recovery is short, and the alternative is a long arc through "did I `pip install` correctly" diagnostics. Polishing doctor cannot close this gap; the gap is upstream of doctor itself.

### Symptom

```text
$ fbridge doctor
Traceback (most recent call last):
  ...
ModuleNotFoundError: No module named 'forge_bridge'
```

Or:

```text
$ python -c "import forge_bridge"
ModuleNotFoundError: No module named 'forge_bridge'
```

`which fbridge` resolves to a real binary in your conda env's `bin/`. `pip list` claims `forge-bridge` is installed. But every actual invocation fails on import. The install **looks** present at every layer except the one that matters.

### What `fbridge doctor` shows

Nothing — doctor cannot run. The error occurs during interpreter startup, before any forge-bridge code is reached. This is the structural marker of the failure mode: when doctor itself fails to import, the issue is the install anchor, not any runtime subsystem.

### Diagnosis

`pip install -e .` records the **absolute filesystem path** of the source tree into the conda env (under `site-packages/__editable__.forge_bridge-*.pth` and a corresponding `.dist-info` entry). When that path stops existing — typically because a git worktree got removed, the repo got moved, or the original checkout got deleted — Python's import resolver returns nothing, but the console-script wrapper in `bin/fbridge` stays on `$PATH` and continues to be reachable until you actually invoke it.

The most common precipitating shape on this project:

1. AI assistant or operator runs `git worktree remove <path>` for cleanup.
2. The active conda env's editable install pointed at that worktree.
3. The next `fbridge` / `python -m forge_bridge` / `pytest` invocation fails with `ModuleNotFoundError`.

The bridge daemon may still be running from the now-deleted source path — its interpreter holds an open file handle, so the daemon itself continues to serve until restarted. Doctor failing while the daemon keeps running is the cleanest signature of this dual-state condition.

### Recovery

**Fast path (under 1 minute):**

1. **Confirm the diagnosis:**

    ```bash
    pip show forge-bridge | grep -E '^(Name|Location|Editable)'
    ```

    A dangling install shows `Location:` or `Editable project location:` pointing at a path that no longer exists. Verify with `ls` if you want to be certain.

2. **Re-anchor the install** from the checkout you're keeping:

    ```bash
    cd /path/to/your/active/forge-bridge/checkout
    pip install -e ".[dev,llm]"
    ```

    The new editable install overwrites the old `.pth` / `.dist-info` entry; the console-script wrapper in `bin/` stays in place unchanged.

3. **Verify the new anchor:**

    ```bash
    python -c "import forge_bridge; print(forge_bridge.__file__)"
    ```

    The path printed should point into your active checkout.

### Verification

You're recovered when **all three** signals hold:

- `python -c "import forge_bridge"` succeeds without error.
- `pip show forge-bridge` reports a `Location` that exists on disk.
- `fbridge doctor` runs to completion — the underlying daemon-runtime failure modes are now reachable through doctor again.

### Why this happens

`pip install -e .` is implemented as a `.pth` file in `site-packages` that injects the source tree's absolute path onto `sys.path` at interpreter startup. The console script entry point (`fbridge`) is installed as a tiny wrapper in the conda env's `bin/` that does `from forge_bridge.cli.main import app; app()` — but the wrapper itself lives in the env, not in the source tree. So:

- Delete the source tree → import breaks, wrapper still on `$PATH`.
- Move the source tree → import breaks, wrapper still on `$PATH`.
- Switch git branches in the same checkout → import keeps working (paths unchanged).
- Remove a git worktree that the editable install was anchored to → import breaks; this is the most common precipitating action on this project because worktrees feel disposable but a `pip install -e` against one anchors the env to the worktree path.

This is a Python packaging / workflow hazard, not a forge-bridge bug. The same shape applies to every editable install of every Python package; forge-bridge surfaces it more often than most because the daily workflow involves multiple checkouts (main, worktrees, AI-assistant scratch branches) and a long-running daemon that masks the issue until something triggers a fresh import.

### Cross-references

- `CLAUDE.md` "Housekeeping discipline (cleanup actions)" — the precondition check that prevents this in the first place, written so AI assistants doing routine cleanup catch the editable-install anchor before destructive worktree removal.

---
