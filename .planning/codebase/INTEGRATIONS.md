# External Integrations

**Analysis Date:** 2026-04-14

## APIs & External Services

**Autodesk Flame (HTTP Bridge):**
- Flame Python API access via HTTP remote code execution
  - SDK/Client: `forge_bridge/bridge.py` (httpx-based async client)
  - Connection: HTTP POST to `http://localhost:9999/exec` (configurable via env vars)
  - Protocol: JSON request/response with Python code execution
  - Auth: None (localhost-only by default, can bind to 0.0.0.0 for LAN)
  - Files: 
    - Flame-side: `flame_hooks/forge_bridge/scripts/forge_bridge.py` (HTTP server inside Flame)
    - Client-side: `forge_bridge/bridge.py`, `forge_bridge/tools/*.py`

**Ollama (Local LLM):**
- Local AI model serving via OpenAI-compatible API
  - SDK/Client: OpenAI Python SDK (`openai>=1.0`)
  - Endpoint: Configured via `FORGE_LOCAL_LLM_URL` (default: http://assist-01:11434/v1)
  - Model: `FORGE_LOCAL_MODEL` (default: qwen2.5-coder:32b)
  - Auth: None (API key ignored, Ollama runs on local network)
  - Usage: Sensitive queries stay on local network
  - Files: `forge_bridge/llm_router.py` (class `LLMRouter._local_complete()`)

**Anthropic Claude (Cloud LLM):**
- Cloud-based LLM for non-sensitive queries
  - SDK/Client: `anthropic>=0.25`
  - Endpoint: Anthropic API (cloud)
  - Model: `FORGE_CLOUD_MODEL` (default: claude-opus-4-6)
  - Auth: `ANTHROPIC_API_KEY` environment variable (required for cloud calls)
  - Usage: Non-sensitive architecture/design queries routed here
  - Files: `forge_bridge/llm_router.py` (class `LLMRouter._cloud_complete()`)

## Data Storage

**Databases:**
- PostgreSQL 12+
  - Connection: Async via `asyncpg>=0.29` (client-side)
  - Sync migrations: `psycopg2-binary>=2.9`
  - Client: SQLAlchemy ORM with async session factory
  - URL format: `postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge`
  - Env var: `FORGE_DB_URL`
  - Schema definition: `forge_bridge/store/models.py`
  - Migrations: `forge_bridge/store/migrations/versions/` (Alembic)
  - Migration config: `alembic.ini`
  - Tables:
    - Entities (Project, Sequence, Shot, Version, Media, Asset)
    - Relationships (graph edges connecting entities)
    - Roles (predefined role definitions for Stacks and Layers)
    - Location tracking (where entities can be found)
    - Process graph (dependency tracking for versioning)

**File Storage:**
- Local filesystem only
  - Flame projects and media stored on local filesystem
  - No S3/cloud storage integration detected
  - Path resolution via role templates in `forge_bridge/core/registry.py`

**Caching:**
- In-memory registry cache (`forge_bridge/core/registry.py`)
  - Caches role and relationship type definitions
  - No external cache (Redis/Memcached) detected

## Authentication & Identity

**Auth Provider:**
- Custom (auth deferred)
  - Implementation: Not yet implemented (see `docs/ARCHITECTURE.md`)
  - Message protocol supports auth context but enforcement is disabled
  - Local network only for now (Flame bridge binds to 127.0.0.1 by default)
  - Files: Protocol definition in `forge_bridge/server/protocol.py` with `auth_context` field

**API Key Management:**
- Environment variables only
  - `ANTHROPIC_API_KEY` for Claude cloud access
  - No secrets manager integration (Vault, AWS Secrets Manager, etc.)

## Monitoring & Observability

**Error Tracking:**
- None detected
  - Errors logged to stderr via Python logging
  - No external error tracking (Sentry, etc.) integrated

**Logs:**
- Approach: Python logging module (`import logging`)
  - Bridge hook: `_log()` function in `flame_hooks/forge_bridge/scripts/forge_bridge.py`
  - MCP server: Standard logging via logger setup in modules
  - Database migrations: Alembic logging configured in `alembic.ini`
  - No centralized logging system (ELK stack, Datadog, etc.) detected

**Tracing:**
- None detected
  - No distributed tracing (OpenTelemetry, Jaeger) found

## CI/CD & Deployment

**Hosting:**
- Local only (currently)
  - Flame bridge: Runs inside Flame on the same machine (127.0.0.1:9999)
  - MCP server: Local stdio transport by default, optional HTTP transport (default :8080)
  - Database: Local PostgreSQL instance

**CI Pipeline:**
- None detected
  - `pyproject.toml` includes pytest configuration
  - Test files in `tests/` directory (test_core.py, test_e2e.py, test_integration.py)
  - No GitHub Actions, GitLab CI, or other CI service configuration found
  - Ruff linting available (`ruff check` command can be run locally)

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` - Only if using cloud LLM calls (non-sensitive queries)

**Recommended env vars:**
- `FORGE_BRIDGE_HOST` - To bind to network interface other than localhost
- `FORGE_DB_URL` - To use non-default database
- `FORGE_LOCAL_LLM_URL` - If Ollama is not on assist-01
- `FORGE_LOCAL_MODEL` - If using different local model
- `FORGE_CLOUD_MODEL` - If using different Claude model

**Secrets location:**
- Environment variables only
  - `ANTHROPIC_API_KEY` must be set before running cloud LLM calls
  - No `.env` file reading detected (secrets not persisted in code)
  - No `.env.local`, `.env.secret`, or similar patterns found

## Webhooks & Callbacks

**Incoming:**
- None detected
  - System does not expose webhook endpoints for external systems to call

**Outgoing:**
- Flame API callbacks: Yes
  - Flame event handlers for timeline/batch changes
  - Implemented in individual tool functions (e.g., `tools/timeline.py`)
  - Not a true webhook system; changes detected via Flame API introspection

**Server Push Events:**
- WebSocket events: Yes
  - Protocol: Custom JSON messages via `websockets>=13.0`
  - Event types defined in `forge_bridge/server/protocol.py`
  - Message format:
    ```json
    {
      "type": "event",
      "event_type": "entity.updated",
      "entity_id": "...",
      "project_id": "...",
      "payload": {...}
    }
    ```
  - Implementation: `forge_bridge/server/connections.py` (ServerConnection handling)
  - Broadcast: Events pushed to all connected clients via `forge_bridge/server/connections.py:broadcast()`

## Message Format & Protocol

**Wire Protocol:**
- JSON over WebSocket (future multi-endpoint communication)
  - Protocol definition: `forge_bridge/server/protocol.py`
  - Message structure: Every message has `type` and `id` fields
  - Request/response correlation: Client generates UUID, server echoes in response
  - Error format:
    ```json
    {
      "type": "error",
      "id": "<request id or null>",
      "code": "NOT_FOUND",
      "message": "Shot EP60_010 not found"
    }
    ```

- HTTP JSON (Flame bridge communication)
  - Endpoint: POST `/exec` on Flame bridge
  - Request:
    ```json
    {
      "code": "python source code",
      "main_thread": false
    }
    ```
  - Response:
    ```json
    {
      "stdout": "captured output",
      "stderr": "captured errors",
      "result": "return value or null",
      "error": "error message or null",
      "traceback": "full traceback if error"
    }
    ```

---

*Integration audit: 2026-04-14*
