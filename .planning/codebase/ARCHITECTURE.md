# Architecture

**Analysis Date:** 2026-04-14

## Pattern Overview

**Overall:** Multi-layered protocol-agnostic middleware with a central registry system, canonical vocabulary, and event-driven pub/sub architecture.

**Key Characteristics:**
- Protocol-agnostic: Endpoints (Flame, Maya, LLM agents, etc.) connect via standardized WebSocket protocol
- Registry-driven: Shared runtime registry (roles, relationship types) maintained in Postgres and cached in memory
- Canonical vocabulary: All pipeline data (projects, shots, sequences, versions, media, layers, stacks, assets) use fixed entity types with UUID identities
- Trait-based composition: Cross-cutting capabilities (Versionable, Locatable, Relational) implemented as mixins
- Event-driven: All state changes produce append-only events in Postgres; clients subscribe to projects and receive real-time broadcasts
- Dual-transport: Flame endpoint uses synchronous HTTP bridge (port 9999); all other endpoints use async WebSocket (port 9998)

## Layers

**Registry Layer:**
- Purpose: Define and track custom roles and relationship types; enforce referential integrity
- Location: `forge_bridge/core/registry.py`
- Contains: `Registry`, `RoleRegistry`, `RelationshipTypeRegistry`, `RoleDefinition`, `RelationshipTypeDef`
- Depends on: `core/vocabulary.py` (Status, Role, Timecode, FrameRange)
- Used by: All layers; loaded from Postgres on server startup via `RegistryRepo.restore_registry()`
- Pattern: Three-level mapping (name ↔ UUID key ↔ display label); orphan protection blocks deletion of in-use keys; supports migrate-on-delete

**Core Vocabulary Layer:**
- Purpose: Define canonical entity types and value objects
- Location: `forge_bridge/core/entities.py`, `forge_bridge/core/traits.py`, `forge_bridge/core/vocabulary.py`
- Contains: Entity hierarchy (Project, Sequence, Shot, Asset, Version, Media, Layer, Stack) and traits (Versionable, Locatable, Relational)
- Depends on: `registry.py` (for role lookups), UUID generation, datetime
- Used by: All downstream layers; entities are instantiated in-memory and serialized to/from JSON
- Pattern: Entities carry UUID identities, creation timestamps, and open metadata dicts; traits provide cross-cutting capabilities; entities auto-register relationships to parents at construction

**Trait System:**
- `Versionable`: Adds version tracking to Project, Sequence, Shot, Asset, Media
- `Locatable`: Tracks multiple file paths (Location objects) for entities; supports local, network, cloud, archive storage types
- `Relational`: Implements relationship graph; stores stable UUID keys (not names) for resilience to renames
- Pattern: Relationship edges carry optional attributes (e.g., track_role, layer_index for compositional roles)

**Data Layer (Store):**
- Purpose: Persist entities, registry, events, locations, relationships to Postgres
- Location: `forge_bridge/store/models.py` (SQLAlchemy ORM models), `forge_bridge/store/repo.py` (repository methods)
- Contains: Nine repository classes (EntityRepo, ProjectRepo, EventRepo, LocationRepo, RelationshipRepo, RegistryRepo, ClientSessionRepo, RelationshipTypeRepo, RoleRepo)
- Depends on: SQLAlchemy async, asyncpg PostgreSQL driver
- Used by: Router (message handler)
- Pattern: Repositories translate between domain objects (core/entities.py) and DB models (store/models.py); all queries parameterized; events are immutable append-only records
- Schema design: UUID primary keys, entity_type discriminator column, JSONB attributes, no polymorphic per-type tables

**Wire Protocol Layer:**
- Purpose: Define all message types that cross the WebSocket boundary
- Location: `forge_bridge/server/protocol.py`
- Contains: Message types (hello, ok, error, ping, pong, entity.*, role.*, project.*, location.*, relationship.*, query.*, event)
- Pattern: All messages are JSON with a required `type` field; requests include UUID `id` for correlation; responses echo the request id; events have no id and are server-push only
- Message groups: Handshake (hello/welcome/ping), Registry (role.*, rel_type.*), Projects, Entities, Graph (relationship, location), Queries, Subscriptions

**Message Routing Layer:**
- Purpose: Dispatch incoming messages to handler methods; coordinate with data layer and connection layer
- Location: `forge_bridge/server/router.py`
- Contains: `Router` class with 40+ async handler methods (`_handle_*`)
- Depends on: All repo classes, core entities, connection manager, registry
- Used by: Server application (called once per message)
- Pattern: Each handler is async; handlers write to Postgres atomically, update in-memory registry, and call connection manager to broadcast; errors caught and returned as error messages (never crash)
- Handler signature: `async def _handle_*(self, msg: Message, client: ConnectedClient) -> Message`

**Connection Layer:**
- Purpose: Track live WebSocket connections and manage subscriptions
- Location: `forge_bridge/server/connections.py`
- Contains: `ConnectedClient` (tracks session_id, endpoint_type, subscriptions, last_event_id), `ConnectionManager` (registry of all connected clients)
- Pattern: Client registers on hello; subscriptions default to wildcard (all projects); register_catch_up() replays missed events on reconnect
- Used by: Router to send targeted and broadcast messages; server lifecycle to clean up disconnects

**Server Application Layer:**
- Purpose: Bind WebSocket port, restore database state, create router/connections, run lifecycle
- Location: `forge_bridge/server/app.py`
- Contains: `ForgeServer` class with start/stop/shutdown handlers
- Lifecycle: 1. Connect to Postgres, 2. Create tables (idempotent), 3. Restore registry from Postgres, 4. Seed defaults if DB is empty, 5. Bind WebSocket, 6. Accept connections
- Entry point: `python -m forge_bridge.server` or `python -m forge_bridge.server --http --port 8080` (for testing)

**Client Layers:**
- **AsyncClient** (`forge_bridge/client/async_client.py`): Async WebSocket client used by MCP server; connection pool, pending request tracking, event subscriptions, auto-reconnect with backoff
  - Pattern: Send→receive via message ID correlation; callbacks for subscribed events; runs event loop
- **SyncClient** (`forge_bridge/client/sync_client.py`): Synchronous wrapper around AsyncClient used by Flame endpoint
- **MCP Server** (`forge_bridge/mcp/server.py`, `forge_bridge/mcp/tools.py`): FastMCP wrapper connecting to both forge-bridge WebSocket and Flame HTTP bridge; registers 40+ tools for LLM agents

**Flame Integration:**
- **Flame HTTP Bridge** (`flame_hooks/forge_bridge/scripts/forge_bridge.py`): HTTP server running inside Flame on port 9999; accepts Python code via POST /exec; executes on Flame's main thread via schedule_idle_event; returns {stdout, stderr, result, error, traceback}
- **Flame Endpoint** (`forge_bridge/flame/endpoint.py`): Synchronous client (SyncClient) that lives in Flame hooks directory; listens for Flame segment/version events and pushes them to forge-bridge; listens for forge-bridge entity.updated events and applies side effects in Flame

## Data Flow

**Incoming Entity Update (Client → Server → Database → Broadcast):**

1. Client sends `entity.update` message with request ID via WebSocket
2. Router receives message, looks up `_handle_entity_update`
3. Handler validates entity exists, updates in-memory representation, calls EntityRepo.update_entity() inside a database session
4. EntityRepo serializes the core entity to DB model and executes UPDATE
5. Handler emits `entity.updated` event to EventRepo
6. EventRepo appends immutable record to events table
7. Handler calls ConnectionManager.broadcast(project_id, event) to all subscribed clients
8. ConnectionManager iterates all clients; if subscribed to project, sends event message
9. Clients receive event and fire registered callbacks (e.g., `@client.on("entity.updated")`)

**Project Subscription:**

1. Client sends `subscribe` message with project_id
2. Router calls ConnectionManager.subscribe(session_id, project_id)
3. ConnectionManager replays last N events for that project (catch-up)
4. Client receives those events and processes them
5. Client receives all future events for that project until unsubscribe

**Registry Update (Rename Role):**

1. Client sends `role.rename` message with old_name="primary", new_name="hero"
2. Router calls Registry.roles.rename("primary", "hero")
3. Registry updates internal name mapping, checks for in-use layers
4. If migrate_to is provided, reassigns all holders to new role (calls Layer._on_role_migration callback)
5. RegistryRepo persists change to DBRole in Postgres
6. Handler broadcasts `role.renamed` event to all connected clients
7. All clients update their cached registry

**Flame Segment → forge-bridge Shot:**

1. User creates segment in Flame timeline
2. Flame hook calls FlameEndpoint.on_segment_created(segment)
3. Endpoint extracts segment metadata (name, cut_in, cut_out)
4. Endpoint creates SyncClient request: entity.create(entity_type="shot", name=segment.name, attributes={...})
5. SyncClient sends message via AsyncClient on dedicated event loop thread
6. Router receives, calls _handle_entity_create, EntityRepo.create_entity(Shot(...))
7. Shot entity inserted to DB, event broadcast to all subscribed clients
8. Flame endpoint receives entity.created event (if subscribed to project), stores shot_id in local cache
9. Endpoint now has bidirectional mapping: Flame segment_id ↔ forge-bridge shot_id

## Key Abstractions

**BridgeEntity:**
- Purpose: Base class for all non-project entities (sequence, shot, asset, version, media, layer, stack)
- Pattern: Carries `id` (UUID), `created_at` (timestamp), `metadata` (open dict), and inherits from Relational + Locatable
- Serialization: `to_dict()` includes locations and relationships as nested lists
- Subclasses: Project (top-level), Sequence, Shot, Asset (parallel hierarchy), Version, Media, Layer, Stack

**Relationship Graph:**
- Purpose: Track dependencies and compositional structure without explicit foreign keys
- Key types: member_of (hierarchical containment), version_of (immutable versions), references (media atom), peer_of (same stack), consumes/produces (process lineage)
- Pattern: Edges store stable UUID keys for both relationship type and target entity; attributes carry compositional metadata
- Used for: Blast radius queries (what depends on this?), lineage queries (what did this come from?)

**Role:**
- Purpose: Semantic function assignment (primary, matte, reference, raw, grade, comp, etc.)
- Pattern: Registry maps role name → UUID key; entities store only the key, look up name at read time
- Aliases: Roles carry endpoint-specific aliases ("primary" → flame:"L01", shotgrid:"main", ftrack:"hero")
- Path templates: Roles can define folder path patterns for media organization

**Status:**
- Purpose: Canonical lifecycle states (pending, in_progress, review, approved, rejected, delivered, archived, verified, failed)
- Pattern: Enums with string values and alias support (wip→in_progress, final→delivered, omit→archived)
- Used by: Shot, Version, Media, Asset to track progress through pipeline

**Timecode and FrameRange:**
- Purpose: Temporal representation for timelines and media frame ranges
- Pattern: Timecode (HHMMSSFF with drop-frame support, frame-rate aware); FrameRange (start, end inclusive, with containment/overlap tests)
- Serialization: Both support to_dict()/from_dict() and string representations

## Entry Points

**`python -m forge_bridge.server`:**
- Location: `forge_bridge/server/__main__.py` → `forge_bridge/server/app.py:main()`
- Triggers: CLI invocation; binds WebSocket on port 9998 (configurable via FORGE_PORT)
- Responsibilities: Initialize ForgeServer, call start(), enter serve loop, handle signals

**`python -m forge_bridge.mcp`:**
- Location: `forge_bridge/mcp/__main__.py` → `forge_bridge/mcp/server.py:main()`
- Triggers: Claude or other LLM agent startup
- Responsibilities: Create AsyncClient, connect to forge-bridge WebSocket, register 40+ tools with FastMCP, run MCP stdio transport

**`python -m forge_bridge` (package entry point):**
- Location: `forge_bridge/__main__.py`
- Triggers: Explicit invocation as module; acts as delegator based on args
- Responsibilities: Routes to server, mcp, or flame subcommand

**Flame Python Hook (async HTTP server):**
- Location: `flame_hooks/forge_bridge/scripts/forge_bridge.py`
- Triggers: Flame loads hooks directory; calls main() at import time
- Responsibilities: Start HTTP server on port 9999, accept POST /exec requests, schedule execution on Flame main thread, return results as JSON

## Error Handling

**Strategy:** All errors are caught at the handler level and returned as error messages (type="error", code=ErrorCode.*); no exceptions escape to crash the server or disconnect clients.

**Patterns:**

- **BridgeError / BridgeConnectionError** (`forge_bridge/bridge.py`): Raised by HTTP client when Flame execution fails or Flame is unreachable
- **ServerError** (`forge_bridge/client/async_client.py`): Raised by AsyncClient when server returns error response; includes code, message, details dict
- **ConnectionError / TimeoutError** (`forge_bridge/client/async_client.py`): Raised by AsyncClient on network issues; client retries with exponential backoff
- **RegistryError / OrphanError / ProtectedEntryError** (`forge_bridge/core/registry.py`): Raised by registry operations when invariants would be violated (e.g., deleting a role in use)
- **ValidationError** (implicit): Router handlers validate inputs before processing; if validation fails, return error message with specific code (e.g., NOT_FOUND, INVALID_INPUT)

**Error Codes** (`ErrorCode` enum in `server/protocol.py`):
- NOT_FOUND: Entity/project/role not found
- INVALID_INPUT: Message payload validation failed
- INTERNAL_ERROR: Unexpected error in handler (logged server-side)
- UNAUTH: Authentication failed (framework exists, not yet implemented)
- CONFLICT: Concurrent modification or invariant violation

## Cross-Cutting Concerns

**Logging:** Standard Python logging module; loggers created per module; server starts with INFO level (configurable via FORGE_LOG_LEVEL env var)

**Validation:** Inputs validated in handler methods before database access; error messages include reason (e.g., "entity_type must be one of: shot, sequence, version, ...")

**Authentication:** Framework in place (clients report name in hello message, tracked in ConnectedClient.client_name); full auth deferred (local-only for now)

**Timestamps:** All database records use `DateTime(timezone=True)` UTC; all API times are ISO8601 strings; comparisons use timezone-aware datetime objects

**Concurrency:** Async/await everywhere in server and MCP client; sync wrapper (SyncClient) used only by Flame endpoint to run async code in dedicated background thread

---

*Architecture analysis: 2026-04-14*
