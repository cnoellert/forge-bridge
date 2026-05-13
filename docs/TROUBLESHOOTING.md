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
| DIAG-01 | [Flame hook unreachable](#failure-mode-flame-hook-unreachable) *(forthcoming)* |
| DIAG-02 | [Postgres restart or unavailable](#failure-mode-postgres-restart-or-unavailable) *(forthcoming)* |

Sections marked *forthcoming* will land in subsequent Phase 23 commits. Recipe 1's pointer at "TROUBLESHOOTING.md — forthcoming under Phase 23" becomes accurate as each section ships.

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

*More failure modes land in subsequent Phase 23 commits.*
