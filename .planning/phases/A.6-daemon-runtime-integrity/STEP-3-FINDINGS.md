# A.6 Step 3 — Environment + Reachability Findings

**Date:** 2026-05-06
**Authorization:** observation-only (continued). No code changes. Existing probe still in place; not removed yet.
**Captured by:** ps eww, env, ping, nc, curl, python socket.getaddrinfo, grep — no daemon restart, no probe extension.

---

## Step 3.1 — Environment parity (daemon vs. shell)

**Method:** `ps eww -p <daemon_pid>` to read the daemon's process environment from outside; `env` for shell.

**Daemon PID:** 91854 (post-restart from Step 2).

**Captured environment (relevant keys, both daemon and shell):**

```
FORGE_LOCAL_LLM_URL=http://192.168.86.15:11434/v1
FORGE_LOCAL_MODEL=qwen2.5-coder:32b   (from /etc/forge-bridge/forge-bridge.env)
FORGE_BRIDGE_PORT=9998
FORGE_CONSOLE_PORT=9996
FORGE_MCP_PORT=9997
ANTHROPIC_API_KEY=<set>                (redacted; confirmed present)
USER=cnoellert
HOME=/Users/cnoellert
PWD=/Users/cnoellert/Documents/GitHub/forge-bridge
PATH=<long; identical surface; conda forge env on PATH for both>
```

**Proxy variables checked:** `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` — **all unset** in both daemon and shell.

### Key finding (Step 3.1)

**No daemon-vs-shell environment divergence.** Both processes read the same `FORGE_LOCAL_LLM_URL` value. The configuration source is `/etc/forge-bridge/forge-bridge.env` (the system env file installed during Phase 20.1).

**Critical reframing:** the daemon's target Ollama is **`192.168.86.15:11434`**, *not* `localhost:11434`. The earlier shell probe `curl http://localhost:11434/api/tags` succeeding in ~3 ms was probing a **different Ollama instance** than the one the daemon talks to. That misled the Step 2 hypothesis briefly — corrected here.

This matches the project memory entry on the cross-host setup: assist-01 is the operator's GPU host running Ollama; the daemon on this workstation routes LLM calls there.

---

## Step 3.2 — Reachability + host-resolution parity

### `getaddrinfo` (refutes IPv6/`::1` hypothesis)

```
192.168.86.15  →  AF_INET 192.168.86.15:11434   (single IPv4 address — IP literal)
localhost      →  AF_INET6 ::1:11434, AF_INET 127.0.0.1:11434   (would have IPv6-first ordering, but irrelevant — daemon is not pointed at localhost)
```

The daemon's target is an IPv4 literal. There is no DNS lookup, no AAAA record, no IPv6 fallback ordering. **The IPv6-first / `::1` failure-mode hypothesis from the directive does not apply** — `192.168.86.15` resolves to itself, single AF_INET.

### Reachability tests (all from this workstation, same env as daemon)

| Probe | Outcome | Wall-clock |
|-------|---------|------------|
| `ping -c 2 -W 2000 192.168.86.15` | 100 % packet loss; "Request timeout for icmp_seq 0" | n/a |
| `nc -z 192.168.86.15 11434` (5s wait flag ignored by macOS nc) | exit=1 (connection refused/unreachable) | **75.00 s** |
| `curl -fsS -m 80 http://192.168.86.15:11434/api/tags` | curl error 28: "Failed to connect to 192.168.86.15 port 11434 after 75001 ms: Couldn't connect to server" | **75.001 s** |
| Daemon chat (Smoke Test 1, Step 2 capture) | `LLMToolError` | **75.04 s** |

**The 75-second figure is identical (within instrument noise) across all four probes**, including from outside the daemon. This is conclusively an **OS-level network timeout**, not an application-level timer.

### Step 3.2 conclusion

`192.168.86.15:11434` is **presently unreachable** from this workstation. SYN packets get no response; the OS retries until its default ceiling (~75 s on macOS for unreachable IPv4 hosts) and surfaces a connect error. Behavior reproduces from `nc`, `curl`, and the daemon — refuting any hypothesis of asyncio / loop / library-internal causation.

The local-Ollama instance at `localhost:11434` has `qwen2.5-coder:32b` available — that is the viable fallback target if remediation requires a working LLM path on this workstation.

---

## Step 3.3 — Connection-stage instrumentation (skipped, with rationale)

The directive listed Step 3.3 as: "Distinguish unreachable endpoint vs. reachable endpoint with hung response vs. transport retry exhaustion."

**Skipped on evidence sufficiency.** The OS-level probes (Step 3.2) already answer this:

- `nc -z` and `curl` from outside the daemon show identical 75-second timeouts.
- That conclusively classifies as **"unreachable endpoint"** (the OS never reaches the application layer).
- Extending the in-daemon probe to capture TCP-connect / first-byte / retry events would require a second daemon restart and produce the same answer. Information-vs-cost ratio is unfavorable.

The discipline boundary remains: probe extension is authorized if classification is ambiguous; here it is not.

---

## Step 3.4 — Timeout provenance audit

**Method:** `grep` for timeout / wait_for / max_seconds across `router.py`, `_adapters.py`, `handlers.py`.

**Configured application-level timeouts:**

| Site | Timeout | Purpose |
|------|---------|---------|
| `handlers.py:1156` | **125.0 s** outer `asyncio.wait_for` | CHAT-02 chat handler outer cap |
| `handlers.py:1153` | **120.0 s** `max_seconds=` passed to `complete_with_tools` | FB-C inner LLM-loop wall-clock cap |
| `router.py:722` | **120.0 s** loop-body `asyncio.wait_for` | wraps the agentic loop body |
| `router.py:639` | configurable per-tool budget | per-tool execution cap |
| `handlers.py:398` | **60.0 s** `_EXEC_HTTP_TIMEOUT` | `/api/v1/exec` per-call cap |
| `_adapters.py` | none directly | adapter calls `client.chat(...)` with no explicit timeout |

**No application-level 75-second timeout exists in our codebase.**

The chat session's `tool-call session complete iter=0 elapsed_s=75.0` log line records that the *first* iteration of the LLM loop ended at 75 s. Per the layering: `await client.chat(...)` raised after 75 s (OS connect timeout) → `LLMToolError` → `_loop_body` exits → `complete_with_tools` returns iter=0. Our 120 s and 125 s caps would only fire on a longer-running call; the OS gave up first.

### Step 3.4 conclusion

The 75 s budget being consumed is **not ours.** It is the macOS kernel's TCP connect timeout on an unreachable IPv4 host (default behavior, no network bug). Confirmed by Step 3.2 reproductions outside the daemon process.

---

## Bisect-window reinterpretation (mechanism vs. consequence)

**Mechanism (fact, now established):**

- The last-healthy chat session was 2026-05-05 14:25:56.
- The A.4 commit landed at 2026-05-05 14:27:27 — approximately **90 s after** the last-healthy session.
- The bisect window therefore included exactly one substantive commit (A.4), which superficially matched all the named hard-elevate trigger phrases (`bootstrap_daemon`, `teardown_daemon`, `_lifespan`, asyncio loop ownership).
- Step 3 evidence shows the daemon's behavior is correct: it dispatches to the configured remote, OS times out at 75 s, daemon faithfully reports `LLMToolError`. No code regression.

**Consequence (still hypothesis-with-strong-prior):**

The regression is **environmental** — `192.168.86.15` was reachable on 2026-05-05 14:25 and is unreachable on 2026-05-06. The A.4 commit is **temporally co-located** with the network state change but **not causally responsible.**

**The bisect was diagnostically correct; the trigger condition was correctly applied; the elevation to A.6 was the right discipline call.** The reason that discipline mattered is precisely that, without it, we would have spent A.6 hunting a non-existent code defect in `bootstrap_daemon`.

---

## Implications for A.6 phase-end condition

Per `PHASE-A.6-SPEC.md` §"Hard elevate condition," A.6 should STOP and elevate if:

> "The classification reveals that the regression is **not** in the A.4 commit (i.e. the bisect window was too narrow because the daemon was already broken before 2026-05-05 14:25 and we mistook a coincidence for a root cause)."

**Partial match.** The regression is not in the A.4 commit, and the bisect did mistake coincidence for cause — but the underlying daemon was not "already broken." It was always healthy; the network state changed.

The intended elevate response was "do not patch; recommend a deeper-scope phase." That action does **not** apply here, because:

- The daemon code does not need to be patched.
- The lifecycle map's structural model is correct.
- Steps 1-3 produced a falsifiable, reproducible explanation.
- No deeper phase is needed to understand runtime integrity.

**Recommended phase boundary (for user review):**

- **Close A.6** with an environmental finding documented and a small set of remediation options (none of which require runtime-substrate changes).
- **Resume A.5** — the masking finding still holds: forced-tool wrapper schema (A.5.2) and narrower (A.5.3) are real bugs that will reproduce as soon as the operator restores Ollama reachability. They are not affected by this finding.

This is **not** a phase broadening. The runtime-integrity phase achieved its diagnostic goal: it ruled out runtime defect as the cause, on evidence.

---

## Remediation options (for Step 4 / 5 review — not yet authorized)

These are options for the user to choose from, not actions to take.

| Option | Effect | Cost | Touches code? |
|--------|--------|------|----------------|
| Restore network reachability to `192.168.86.15` (operator-side: VPN, Wi-Fi, host availability) | Daemon resumes working; no other change needed | operator action only | no |
| Repoint `FORGE_LOCAL_LLM_URL` to `http://localhost:11434/v1` in `/etc/forge-bridge/forge-bridge.env` | Daemon talks to local Ollama (already has `qwen2.5-coder:32b`) | one-line config edit, daemon restart | no |
| Lower the **surfaced** failure latency: configure `httpx`/`ollama.AsyncClient` with a connect-timeout (e.g. 5 s) so the user sees a fast, informative error instead of a 75 s wait | Better UX when the remote is unreachable; does NOT make the call succeed | small `_adapters.py` change at the lazy-construction site (`_get_local_native_client`) | yes (small) |
| Add a runtime preflight: `forge doctor` check or `bootstrap_daemon` warning when the LLM endpoint is unreachable | Operator sees the issue at startup, not at first request | larger; touches doctor + bootstrap | yes (larger) |

The **third option** is the only one that fits inside an A.6-style "small fix" — and it is a UX improvement, not a correctness fix. The other options are operator-side or larger-scope.

---

## Authorization-boundary discipline (continued)

- No fixes implemented.
- Probe still in place at `forge_bridge/llm/_adapters.py` (marked `probe-A6`); not removed yet (gated on Step 4).
- All findings reproducible: env capture via `ps eww`, reachability via `nc`/`curl`/`ping`, host resolution via `socket.getaddrinfo`, timeout provenance via `grep`. None required modifying daemon state.

## Methodological observation (preserve, do not formalize yet)

The Step 1 → Step 2 → Step 3 sequence demonstrated a second methodological pattern beyond "map first, probe second":

> **Verify the bisect is causal, not co-incident, before assuming the bisect commit is the regression.**

The bisect window contained one substantive commit and matched the spec's trigger phrases verbatim. Without environment evidence, the natural action would have been to re-architect `bootstrap_daemon`. The 90-second gap between last-healthy and the A.4 commit was structurally invisible until Step 3 surfaced the real (environmental) cause.

This is a real result. Preserve as evidence; do not formalize.

---

## Step 3 status

- Steps 3.1, 3.2, 3.4: **completed.**
- Step 3.3: **intentionally skipped** with documented rationale (evidence sufficiency).
- Findings: filed (this document).
- Probe: NOT removed (gated on Step 4).
- Fixes: none implemented.

## Awaiting review before Step 4 (classification + remediation choice).

Step 4 needs a user decision on:

1. Whether A.6 closes with environmental finding + Step 5 = "no code change" or "small UX timeout fix"
2. Whether to resume A.5 (forced-tool schema + narrower) immediately or wait for the operator-side network restore first (the smoke tests for A.5.2 / A.5.3 will reproduce once the daemon's chat path can complete an LLM call)
3. Whether the timeout-surfacing UX fix is in scope for A.6 or planted as a seed for v1.5+
