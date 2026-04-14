# Technology Stack

**Analysis Date:** 2026-04-14

## Languages

**Primary:**
- Python 3.10+ - The entire codebase is Python-based
  - Flame bridge hook: Standard library only (runs inside Flame's Python interpreter)
  - MCP server & core: Full Python ecosystem with async/await patterns
  - Database migrations & tooling: SQLAlchemy + Alembic

## Runtime

**Environment:**
- Python 3.10+ (specified in `pyproject.toml`)
- Flame 2026 (for Flame endpoint)
- Local execution (single-machine, HTTP-based communication between processes)

**Package Manager:**
- pip (via `pyproject.toml` with hatchling build backend)
- Lockfile: Not detected (virtual environment via `.venv/`)

## Frameworks

**Core:**
- MCP (Model Context Protocol) 1.0+ - Structured protocol for LLM tool exposure
  - Package: `mcp[cli]>=1.0`
  - Used in: `forge_bridge/server.py` via FastMCP
- Autodesk Flame Python API - Available as `import flame` within Flame runtime
  - Accessed via HTTP bridge from external processes

**Async Runtime:**
- asyncio (stdlib) - Async/await pattern throughout
- SQLAlchemy AsyncIO (`sqlalchemy[asyncio]>=2.0`) - Async ORM layer

**HTTP & WebSocket:**
- httpx 0.27+ - Async HTTP client for bridge communication
  - Used in: `forge_bridge/bridge.py` for POST requests to Flame bridge
- websockets 13.0+ - WebSocket server/client for multi-endpoint communication
  - Used in: `forge_bridge/server/app.py`, `forge_bridge/client/`, `forge_bridge/shell.py`
  - Protocol: Custom JSON-based message format defined in `forge_bridge/server/protocol.py`

**LLM Integration:**
- OpenAI SDK 1.0+ - Access to local Ollama and cloud models via OpenAI-compatible API
  - Used in: `forge_bridge/llm_router.py` for local Ollama calls
- Anthropic SDK 0.25+ - Claude cloud API integration
  - Used in: `forge_bridge/llm_router.py` for sensitive-data-safe cloud completions

**Testing:**
- pytest - Test runner
- pytest-asyncio - Async test support
- Config: `pyproject.toml` with `asyncio_mode = "auto"`

**Build/Dev:**
- ruff 0.x - Linting and code formatting (configured with line-length=100, target-version=py310)
- hatchling - Build backend
- Alembic 1.13+ - Database schema migrations

## Key Dependencies

**Critical:**
- `sqlalchemy[asyncio]>=2.0` - ORM, schema definition, query building
  - Core to entity storage and relationship tracking
  - Database-agnostic (uses PostgreSQL specifically via `asyncpg`)
- `asyncpg>=0.29` - Async PostgreSQL driver
  - High-performance async interface to database
- `mcp[cli]>=1.0` - Model Context Protocol implementation
  - Exposes Flame tools to LLM agents
- `httpx>=0.27` - HTTP client (async-first)
  - Primary transport for Flame bridge communication
- `websockets>=13.0` - WebSocket implementation
  - Foundation for server-to-client bi-directional communication

**Infrastructure:**
- `psycopg2-binary>=2.9` - Synchronous PostgreSQL driver
  - Used for migrations and sync CLI operations (via Alembic)
- `alembic>=1.13` - Database schema versioning
  - Migrations live in `forge_bridge/store/migrations/versions/`

**LLM/AI:**
- `openai>=1.0` - Used for both local (Ollama via OpenAI-compatible endpoint) and cloud models
- `anthropic>=0.25` - Claude API for sensitive-aware routing

## Configuration

**Environment Variables:**

**Bridge Connection (client-side, in `forge_bridge/bridge.py`):**
- `FORGE_BRIDGE_HOST` - Flame bridge hostname (default: 127.0.0.1)
- `FORGE_BRIDGE_PORT` - Flame bridge port (default: 9999)
- `FORGE_BRIDGE_TIMEOUT` - HTTP timeout in seconds (default: 30)

**Database Connection (in `forge_bridge/store/session.py`):**
- `FORGE_DB_URL` - Async PostgreSQL connection string
  - Default: `postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge`
  - Alembic sync connection: `postgresql+psycopg2://forge:forge@localhost:5432/forge_bridge`

**LLM Routing (in `forge_bridge/llm_router.py`):**
- `FORGE_LOCAL_LLM_URL` - Ollama base URL (default: http://assist-01:11434/v1)
- `FORGE_LOCAL_MODEL` - Local model name (default: qwen2.5-coder:32b)
- `FORGE_CLOUD_MODEL` - Cloud model name (default: claude-opus-4-6)
- `ANTHROPIC_API_KEY` - Required for cloud LLM calls

**Flame Bridge (in-Flame environment, in `flame_hooks/forge_bridge/scripts/forge_bridge.py`):**
- `FORGE_BRIDGE_HOST` - HTTP server bind address (default: 127.0.0.1, set to 0.0.0.0 for LAN)
- `FORGE_BRIDGE_PORT` - HTTP server port (default: 9999)
- `FORGE_BRIDGE_ENABLED` - Enable/disable hook (default: 1, set to 0 to disable)

**Build:**
- `pyproject.toml` - Single source of truth for dependencies, build, entry points
- `alembic.ini` - Database migration configuration
  - Schema version folder: `forge_bridge/store/migrations/versions/`
  - Alembic tracks schema versions and auto-generates migration scripts

## Platform Requirements

**Development:**
- Python 3.10+ (virtual environment via `python -m venv .venv`)
- PostgreSQL database (default localhost:5432)
- Autodesk Flame 2026 (for testing Flame integration locally)
- Optional: Ollama running on assist-01 (for local LLM calls)

**Production:**
- Python 3.10+
- PostgreSQL 12+ (tested via asyncpg)
- Flame 2026 (on machine where Flame runs — hook is standard library only)
- Optional: Ollama instance (for sensitive-data LLM operations)
- Optional: Anthropic API key (for non-sensitive LLM queries)

---

*Stack analysis: 2026-04-14*
