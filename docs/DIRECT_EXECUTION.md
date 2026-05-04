# Direct execution (`execute_command`)

In-process deterministic command execution for integrations and the **`fbridge exec`** CLI. This path does **not** use HTTP or the Artist Console.

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
