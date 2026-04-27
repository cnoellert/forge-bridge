# SEED: Chat server-side history persistence (v1.5+, paired with SEED-AUTH-V1.5)

**Source:** Phase 16 (FB-D) D-06 — per-tab in-browser JS state, cleared on tab close
**Status:** planted 2026-04-27

## Trigger

When auth + per-user data scoping land — i.e., when forge-bridge has identity AND a
user-scoped storage layer to persist conversations against. Without identity, there's no
per-user persistence boundary, so per-tab JS state is the only safe default for v1.4.

## v1.4 baseline

D-06: chat history lives in browser JS only. State clears on tab close. No localStorage,
no sessionStorage, no server-side persistence. Each tab is a fresh conversation.

## v1.5+ migration shape

Add a new entity type `chat_session` (analogous to `staged_operation` from FB-A) and a
small set of MCP/HTTP routes:

```
POST   /api/v1/chat/sessions               # Start a new session, returns session_id
GET    /api/v1/chat/sessions/{id}          # Fetch full message history
DELETE /api/v1/chat/sessions/{id}          # Delete session (caller's only)
GET    /api/v1/chat/sessions               # List caller's sessions
```

Modify the existing `POST /api/v1/chat`:

```json
{
  "messages": [...],            // Optional now — server can reload from session_id
  "session_id": "<uuid>"        // Optional; if present, server appends to that session
}
```

Storage: a new `chat_session` entity with `entity_type='chat_session'`, fields:
- `caller_id` (foreign key to whatever auth provides)
- `messages` (JSONB list of {role, content, tool_call_id?})
- `created_at`, `updated_at`

The Web UI panel:
- On load, fetch the caller's most-recent session (or list of sessions for selection).
- On send, post with `session_id` so the server appends to the persistent record.

## Cross-references

- SEED-AUTH-V1.5.md — hard prerequisite
- 13-CONTEXT.md (FB-A entity-type pattern — chat_session uses the same lifecycle)
- 16-CONTEXT.md D-06 (per-tab v1.4 posture)
- SEED-MESSAGE-PRUNING-V1.5.md — pruning policy for long-running sessions

## Open questions

1. Retention — how long do server-side sessions live? 30 days? Caller-configurable?
2. Cross-device — should the same caller see sessions across browsers? Likely yes; that's
   one of the main reasons to persist server-side.
3. Audit — does the staged-operation lifecycle apply (every chat session emits a DBEvent)?
   For audit-heavy production deployments, yes. For lighter setups, optional.
