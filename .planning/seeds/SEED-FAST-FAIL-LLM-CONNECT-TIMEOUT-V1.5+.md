# SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+

**Planted:** 2026-05-06
**Source:** Phase A.6 — Daemon Runtime Integrity (closure)
**Trigger condition:** v1.5 chat-reliability work resumes, OR an operator reports a chat request that hangs ~75 s before failing

## Background

A.6 Step 3 confirmed that when the daemon's configured Ollama endpoint (`FORGE_LOCAL_LLM_URL`) is unreachable, the chat path waits **~75 seconds** before surfacing `LLMToolError`. The 75 s figure is the macOS TCP connect default for unreachable IPv4 hosts, not an application-level timeout. From the operator's seat this is indistinguishable from a "broken" daemon — they wait a long time, then see a generic error.

Application-level timeouts that exist today:

| Layer | Cap |
|-------|-----|
| Chat handler outer (`asyncio.wait_for`) | 125 s |
| LLM loop wall-clock (`max_seconds`) | 120 s |
| Per-tool execution | configurable per call |
| Exec endpoint | 60 s |

None of these fire before the OS, because the OS fails first.

## What this seed covers

A small UX-only change: configure the `ollama.AsyncClient` (or its underlying `httpx` transport) with an explicit **connect-timeout** at the lazy-construction site (`LLMRouter._get_local_native_client`, `forge_bridge/llm/router.py:844-871`). A 5 s connect-timeout would convert a 75 s silent wait into a 5 s explicit "Ollama unreachable at `<host>`" error.

This is a UX correctness fix, not a logical one. The call still fails when the host is unreachable; it just fails fast and informatively.

## What this seed does NOT cover

- Does not "make the call succeed" when the host is genuinely unreachable.
- Does not introduce retries.
- Does not change the read-timeout (the 120 s LLM-loop cap remains correct for slow-but-responsive models).
- Does not add a runtime preflight (see companion seed `SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+`).

## Suggested implementation sketch (verify against reality at fix time)

```python
def _get_local_native_client(self):
    if self._local_native_client is None:
        from ollama import AsyncClient
        host = self.local_url
        if host.endswith("/v1"):
            host = host[:-3]
        # Configure short connect-timeout, preserve generous read-timeout for
        # slow models. httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)
        # passed via the underlying client (verify ollama.AsyncClient API at fix time).
        self._local_native_client = AsyncClient(host=host, timeout=...)
    return self._local_native_client
```

Verify at fix time:
1. The exact `ollama.AsyncClient` timeout API (it may take an `httpx.Timeout` object, a single float, or separate kwargs depending on version).
2. The error type raised on connect-timeout — should map to a clear user-facing message in the chat handler, not a generic 500.
3. Behavior under a slow-but-responsive Ollama (a connect-timeout of 5 s is fine; a read-timeout of 5 s would break legitimate slow-model responses and is NOT the goal).

## Acceptance criteria when this lands

- A chat request to an unreachable LLM endpoint surfaces an error in **< 10 seconds**, not 75 s.
- The error message names the unreachable host explicitly.
- A chat request to a working endpoint behaves identically to today.
- A test that uses a deliberately-unreachable host (e.g. `http://127.0.0.1:65535/`) verifies fast-fail.

## Why deferred

A.6's authorization boundary scoped it to runtime-integrity classification. The connect-timeout configuration is UX, not runtime correctness — it does not affect whether the daemon is structurally sound. Out of A.6 scope by the spec's own out-of-scope list. Best landed during A.5 resumption or as part of a v1.5 chat-reliability polish pass.
