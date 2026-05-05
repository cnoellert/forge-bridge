# Direct execution (`execute_command`)

In-process deterministic command execution for integrations, the **`fbridge exec`** CLI, **`POST /api/v1/exec`** on the Artist Console (`:9996`), and the Flame hook adapter.

**APIs:**

- `forge_bridge.console._execute.execute_command` (async; returns a **dict**).
- `forge_bridge.flame.integration.run_command_from_flame` (sync; wraps `execute_command` for Flame UI — appends optional explicit `key=value` context, then `asyncio.run`).

---

## Contract

| Property | Guarantee |
|----------|-----------|
| **Determinism** | Deterministic only — tool narrowing, resolver, and `mcp.call_tool` execution; no probabilistic model. |
| **LLM** | No LLM — `LLMRouter` / `complete_with_tools` are not used. |
| **Response shape** | **PR31 envelope always** — success and failure use the same top-level keys as chat chain execution (`status`, `request_id`, `chain`, `error`). |
| **PR32 context** | Context between chain steps is propagated only via **`extract_chain_context`** (single-key rules: `project_id` → `shot_id` → `version_id`). |

---

## HTTP (`POST /api/v1/exec`)

The Artist Console serves **`POST /api/v1/exec`** with JSON body `{"text": "<command>"}`. The handler calls **`forge_bridge.console.app.execute_command`** (re-exported from `forge_bridge/console/app.py` so tests can **`monkeypatch.setattr("forge_bridge.console.app.execute_command", ...)`**).

The response body is the **raw PR31 dict** (`status`, `request_id`, `chain`, `error`) — not the `{data, meta}` envelope used by read routes.

**Concurrency:** server-side **`asyncio.Semaphore(1)`** — at most one `execute_command` runs at a time.

**Timeout:** each invocation is wrapped in **`asyncio.wait_for(..., timeout=60)`**. Past that, the handler returns **`error.code`: `TIMEOUT`**.

**Worst-case latency:** under `Semaphore(1)` and a 60s budget per request, a second concurrent client can wait up to **~120s** end-to-end (up to 60s queued behind an in-flight request, plus up to 60s for its own execution window). Expected for v1 safety.

**Logging:** logger **`forge.exec`** at INFO. Lines include **`exec start rid=<uuid> text='…'`** and **`exec end rid=<uuid> engine_rid=<uuid|None> status=<…>`** (timeout ends with `status=error code=TIMEOUT`).

**POST-only:** **`GET /api/v1/exec`** returns **405 Method Not Allowed**.

### Runbook — verify logging once

With the console listening on `:9996` (`python -m forge_bridge`):

```bash
curl -X POST http://127.0.0.1:9996/api/v1/exec \
  -H "Content-Type: application/json" \
  -d '{"text": "list projects"}'
```

Expected on stdout/journal (two INFO lines from **`forge.exec`**): **`exec start rid=… text='list projects'`** then **`exec end rid=… engine_rid=… status=…`** (`engine_rid` matches the PR31 **`request_id`** in the JSON body on success).

---

## Relationship to chat (`POST /api/v1/chat`)

**May differ from chat** when chat would route the message to the **LLM** (ambiguous tool sets, conversational text, etc.). The chat handler can fall through to the router; **`execute_command`** does not.

Multi-step chains (`->`) use the **same** shared engine as chat’s chain branch (same tool snapshot + backend filter + step runner), modulo chat-only gates (rate limit, PR35/PR36 macro listing/deletion shortcuts).

---

## CLI

```bash
fbridge exec "list forge projects"
fbridge exec "list forge projects -> list versions project_name=MyProj" --json
```

**`fbridge chat`** remains the HTTP + LLM-capable path.
