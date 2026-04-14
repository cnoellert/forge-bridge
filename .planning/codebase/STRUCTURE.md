# Codebase Structure

**Analysis Date:** 2026-04-14

## Directory Layout

```
forge-bridge/
├── docs/                           # Design documentation (not code)
│   ├── ARCHITECTURE.md            # System design rationale
│   ├── VOCABULARY.md              # Canonical entity types + spec
│   ├── API.md                     # HTTP API (Flame bridge)
│   ├── ENDPOINTS.md               # How to write new endpoint adapters
│   ├── DATA_MODEL.md              # Entity relationships
│   └── FLAME_API.md               # Flame Python API reference
│
├── forge_bridge/                   # Main Python package
│   ├── __init__.py                # Package marker
│   ├── __main__.py                # Entry point router
│   │
│   ├── core/                      # Vocabulary layer (entities, traits, registry)
│   │   ├── __init__.py            # Re-exports all core types
│   │   ├── entities.py            # Entity hierarchy (Project, Shot, Version, Media, Layer, Stack, Asset)
│   │   ├── traits.py              # Trait classes (Versionable, Locatable, Relational)
│   │   ├── vocabulary.py          # Value objects (Status, Role, Timecode, FrameRange)
│   │   └── registry.py            # Registry system (roles, relationship types, orphan protection)
│   │
│   ├── client/                    # WebSocket clients
│   │   ├── __init__.py
│   │   ├── async_client.py        # Main async WebSocket client (used by MCP)
│   │   └── sync_client.py         # Sync wrapper (used by Flame endpoint)
│   │
│   ├── server/                    # Central server (runs on port 9998)
│   │   ├── __init__.py
│   │   ├── __main__.py            # Entry point: python -m forge_bridge.server
│   │   ├── app.py                 # ForgeServer lifecycle
│   │   ├── protocol.py            # Wire protocol (all message types)
│   │   ├── router.py              # Message dispatcher (40+ handlers)
│   │   └── connections.py         # ConnectionManager, ConnectedClient tracking
│   │
│   ├── store/                     # Data persistence layer
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy ORM models (DBEntity, DBEvent, DBRole, etc.)
│   │   ├── session.py             # Database connection, session factory
│   │   ├── repo.py                # 9 repository classes (EntityRepo, ProjectRepo, EventRepo, etc.)
│   │   ├── memory.py              # In-memory fallback repo (used in tests)
│   │   └── migrations/            # Alembic schema versions (not tracked in git, generated per environment)
│   │
│   ├── mcp/                       # MCP server (Model Context Protocol for LLMs)
│   │   ├── __init__.py
│   │   ├── __main__.py            # Entry point: python -m forge_bridge.mcp
│   │   ├── server.py              # FastMCP setup, client connection, tool registration
│   │   └── tools.py               # MCP tool implementations (ping, list_projects, get_project, entity.*, etc.)
│   │
│   ├── flame/                     # Flame endpoint integration
│   │   ├── __init__.py
│   │   ├── __main__.py            # Reserved for future Flame sidecar process
│   │   ├── endpoint.py            # FlameEndpoint (SyncClient wrapper, event translation)
│   │   └── sidecar.py             # Sidecar process (future: separate thread/process for Flame hooks)
│   │
│   ├── bridge.py                  # HTTP client to Flame bridge (port 9999)
│   ├── llm_router.py              # LLM-based request routing (experimental)
│   └── shell.py                   # Interactive shell (reserved, not yet implemented)
│
├── flame_hooks/                    # Installs into Flame's Python hooks directory
│   └── forge_bridge/
│       └── scripts/
│           ├── forge_bridge.py        # HTTP server (port 9999) running inside Flame
│           ├── forge_bridge_pipeline.py # Flame-specific pipeline utilities (draft)
│           └── forge_bridge_v2.py      # V2 hook implementation (draft)
│
├── tests/                         # Test suite
│   ├── test_core.py              # Tests for core vocabulary, entities, registry, traits
│   ├── test_integration.py       # Tests for client/server integration
│   └── test_e2e.py               # End-to-end tests (future)
│
├── alembic.ini                    # Database migration config
├── pyproject.toml                 # Package metadata, dependencies
├── CLAUDE.md                      # AI context recovery document
└── README.md                      # Project overview
```

## Directory Purposes

**`forge_bridge/core/`:**
- Purpose: Canonical vocabulary and entity types — the "nouns" of the bridge language
- Contains: All entity classes (Project, Sequence, Shot, Asset, Version, Media, Layer, Stack), traits (Versionable, Locatable, Relational), vocabulary value objects (Status, Role, Timecode, FrameRange), and the registry system
- Key files:
  - `entities.py`: Entity hierarchy; each entity carries UUID, created_at, metadata, and auto-registers relationships to parents
  - `traits.py`: Cross-cutting capabilities; Relational stores stable UUID keys (not names) for resilience to renames
  - `vocabulary.py`: Status enum (pending/in_progress/approved/delivered/archived/verified/failed), Role (with path templates and aliases), Timecode (frame-rate aware with drop-frame support), FrameRange
  - `registry.py`: Three-tier registry (name ↔ UUID key ↔ display label); orphan protection; usage tracking
- Import pattern: `from forge_bridge.core import Project, Shot, Role, Status, Registry, ...`

**`forge_bridge/store/`:**
- Purpose: Persistence layer — translate between in-memory core objects and Postgres
- Contains: SQLAlchemy models, repositories, session management, database initialization
- Key files:
  - `models.py`: DBEntity (polymorphic via entity_type discriminator), DBRole, DBRelationshipType, DBProject, DBLocation, DBRelationship, DBEvent, DBSession
  - `repo.py`: Nine repository classes (EntityRepo, ProjectRepo, EventRepo, LocationRepo, RelationshipRepo, RegistryRepo, ClientSessionRepo, RoleRepo, RelationshipTypeRepo)
  - `session.py`: AsyncSession factory, connection pool, table creation (idempotent)
- Pattern: All queries parameterized; repositories handle the translation to/from domain objects
- Never imported by: core/ (one-way dependency; core doesn't know about DB)

**`forge_bridge/server/`:**
- Purpose: Central server; WebSocket acceptance, message routing, registry management, event broadcasting
- Contains: FastMCP server skeleton, connection tracking, message protocol, message handlers, lifecycle
- Key files:
  - `app.py`: ForgeServer class; lifecycle (start/stop/shutdown); binds port 9998; creates Router and ConnectionManager
  - `protocol.py`: All message types (hello, ok, error, ping, entity.*, role.*, project.*, etc.); Message dataclass with serialize/deserialize
  - `router.py`: Router class with 40+ async handler methods; each handler reads/writes DB, updates registry, broadcasts events
  - `connections.py`: ConnectionManager; tracks live WebSocket connections; manages subscriptions; broadcasts to interested clients
- Entry point: `python -m forge_bridge.server`

**`forge_bridge/client/`:**
- Purpose: Client libraries for connecting to the server
- Contains: Async client (used by MCP), sync wrapper (used by Flame endpoint)
- Key files:
  - `async_client.py`: AsyncClient; WebSocket connection, pending request tracking, auto-reconnect, event subscriptions
  - `sync_client.py`: SyncClient wrapper that runs AsyncClient in a background thread and exposes sync methods
- Used by: MCP server (AsyncClient directly), Flame endpoint (SyncClient wrapper)

**`forge_bridge/mcp/`:**
- Purpose: Model Context Protocol server — expose forge-bridge as structured tools to LLM agents (Claude, etc.)
- Contains: FastMCP setup, tool implementations, shared client singleton
- Key files:
  - `server.py`: FastMCP instance, client connection, tool registration, main() entry point
  - `tools.py`: 40+ tool implementations; each tool validates input, calls client, formats JSON output
- Entry point: `python -m forge_bridge.mcp`
- Tools: ping, list_projects, get_project, entity_create, entity_get, entity_list, entity_update, entity_delete, location_add, relationship_create, role_register, role_list, query_dependents, etc.

**`forge_bridge/flame/`:**
- Purpose: Flame integration — translate between Flame's native API and forge-bridge canonical vocabulary
- Contains: FlameEndpoint (SyncClient wrapper that listens to Flame hooks and pushes events to forge-bridge)
- Key files:
  - `endpoint.py`: FlameEndpoint class; maps segment_id ↔ shot_id; listens for Flame segment.created/updated/deleted and publishes to forge-bridge; listens for forge-bridge entity.updated and applies side effects in Flame
  - `sidecar.py`: Reserved for future multiprocess architecture
- Never run directly; loaded as a Flame Python hook

**`flame_hooks/forge_bridge/scripts/`:**
- Purpose: Code that runs inside Flame
- Contains: HTTP server (forge_bridge.py) and utilities
- Key files:
  - `forge_bridge.py`: HTTP server on port 9999; accepts POST /exec with Python code; executes on Flame's main thread via schedule_idle_event; returns {stdout, stderr, result, error, traceback}
  - Installs to: `/opt/Autodesk/shared/python/forge_bridge/scripts/` (or equivalent on macOS/Windows)

**`tests/`:**
- Purpose: Test coverage for core vocabulary, entity lifecycle, registry, and integration
- Key files:
  - `test_core.py`: Tests for Timecode, FrameRange, Status, Registry, roles, relationships, traits, entities
  - `test_integration.py`: Tests for AsyncClient, Router, end-to-end message flows
  - `test_e2e.py`: Reserved for full pipeline tests (not yet implemented)

## Key File Locations

**Entry Points:**
- `forge_bridge/__main__.py`: Delegator to server/mcp/flame subcommands
- `forge_bridge/server/__main__.py` → `forge_bridge/server/app.py`: Server start
- `forge_bridge/mcp/__main__.py` → `forge_bridge/mcp/server.py`: MCP start
- `flame_hooks/forge_bridge/scripts/forge_bridge.py`: Flame hook HTTP server (runs inside Flame process)

**Configuration:**
- `pyproject.toml`: Package metadata, version, dependencies, dev tools
- `alembic.ini`: Database migration configuration

**Core Logic:**
- `forge_bridge/core/entities.py`: Entity definitions
- `forge_bridge/core/registry.py`: Registry system
- `forge_bridge/server/router.py`: Message dispatch
- `forge_bridge/store/repo.py`: Database access

**Testing:**
- `tests/test_core.py`: Entity and registry tests
- `tests/test_integration.py`: Client/server integration
- `tests/test_e2e.py`: End-to-end pipeline tests

## Naming Conventions

**Files:**
- `snake_case.py`: Standard; modules named after their primary class or responsibility (e.g., `entities.py`, `router.py`)
- `__main__.py`: Entry point in package directory
- `test_*.py`: Test files in `tests/` directory

**Directories:**
- `lowercase/`: All package directories use lowercase (core/, store/, server/, client/, mcp/, flame/)
- `UPPERCASE.md`: Documentation files are uppercase

**Classes:**
- `PascalCase`: Entity classes (Project, Shot, Sequence), utility classes (Router, Registry, ConnectionManager)
- Prefixed with `DB` for ORM models (DBEntity, DBRole, DBProject)

**Functions:**
- `snake_case()`: All functions and methods use snake_case
- Private methods: `_snake_case()` prefix (e.g., `_handle_entity_create()`, `_on_role_migration()`)
- Message handlers: `_handle_<message_type>()` pattern (e.g., `_handle_entity_create`, `_handle_role_register`)
- Factory functions: `create_*()` or `from_*()` pattern (e.g., `create_tables()`, `from_string()`)

**Variables:**
- `snake_case`: Local variables, instance variables, parameters
- `UPPER_CASE`: Module-level constants (e.g., `BRIDGE_URL`, `SYSTEM_REL_KEYS`)

**Constants:**
- `STANDARD_ROLE_KEYS`: Dict of role UUID keys (in registry.py)
- `SYSTEM_REL_KEYS`: Dict of system relationship type UUID keys (in traits.py)
- `STANDARD_ROLES`: List of default roles (in vocabulary.py)

## Where to Add New Code

**New Entity Type (e.g., Component for character rigging):**
- Add class to `forge_bridge/core/entities.py`
- Add to `__init__.py` re-exports
- Create DBComponent in `forge_bridge/store/models.py`
- Add repository methods in `forge_bridge/store/repo.py` (create, get, list, update, delete)
- Add message handlers in `forge_bridge/server/router.py` (_handle_entity_create, _handle_entity_update, etc.)
- Add protocol messages if needed in `forge_bridge/server/protocol.py`

**New MCP Tool (e.g., query_cost_breakdown):**
- Implement function in `forge_bridge/mcp/tools.py`
- Add @mcp.tool() decorator in `forge_bridge/mcp/server.py`
- Function signature: `async def query_cost_breakdown(params: QueryCostBreakdownInput) -> str`
- Return value: JSON string via `_ok(data)` or `_err(message)`

**New Relationship Type (e.g., "depends_on" for task dependencies):**
- Register via `registry.relationships.register("depends_on", label="Depends On")`
- Add UUID key to `SYSTEM_REL_KEYS` in `forge_bridge/core/traits.py` if it's system-level
- Use via `entity.add_relationship(target_id, "depends_on", attributes={...})`
- Add migration in `forge_bridge/store/migrations/` if persisting to default registry

**New Custom Role (e.g., "temp_grade" for temporary color work):**
- Register via `registry.roles.register("temp_grade", label="Temp Grade")`
- Add path template if needed: `registry.roles.register("temp_grade", label="Temp Grade", path_template="{project}/{sequence}/{shot}/temp/grade")`
- Layer can be created: `layer = Layer(role="temp_grade", registry=registry)`
- Aliases can be added: `registry.roles.set_alias("temp_grade", "flame", "TEMP_01")`

**New Endpoint (e.g., Maya adapter):**
- Create `forge_bridge/maya/` directory
- Add `endpoint.py` with MayaEndpoint class (similar to FlameEndpoint)
- MayaEndpoint uses SyncClient (or AsyncClient in dedicated thread)
- MayaEndpoint listens for Flame hooks, translates to core entities, calls client.request(entity_create(...))
- MayaEndpoint receives server events, applies side effects in Maya
- Load endpoint in a Maya startup script or plugin

**New Query Type (e.g., query_cost_by_role):**
- Add message type in `forge_bridge/server/protocol.py` (e.g., `QUERY_COST_BY_ROLE`)
- Implement handler in `forge_bridge/server/router.py` (_handle_query_cost_by_role)
- Handler uses repositories to fetch needed data, computes result, returns ok() message
- Add protocol helper in `server/protocol.py` (e.g., `def query_cost_by_role(...) -> Message:`)

## Special Directories

**`.planning/codebase/`:**
- Purpose: GSD (Goal-Seeking Design) generated analysis documents
- Generated: Yes (by `/gsd:map-codebase` command)
- Committed: Yes (checked into version control for reference)
- Contains: ARCHITECTURE.md, STRUCTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**`forge_bridge/store/migrations/`:**
- Purpose: Alembic database schema versions
- Generated: Automatically when `alembic revision --autogenerate` is run
- Committed: Yes (schema history is part of the codebase)
- Pattern: One .py file per version (alembic generates the upgrade/downgrade functions)
- Generated automatically but not checked in by default (Alembic manages this)

**`docs/`:**
- Purpose: Design documentation and API reference
- Contains: VOCABULARY.md (entity spec), ARCHITECTURE.md (system design), API.md (HTTP API), ENDPOINTS.md (how to write adapters)
- Not code; reference materials

---

*Structure analysis: 2026-04-14*
