# Codebase Concerns

**Analysis Date:** 2026-04-14

## Tech Debt

**Incomplete Flame segment rename callback:**
- Issue: Flame can rename segments in the timeline, but the callback handler has a TODO noting that the actual rename operation is not implemented. The handler logs the intention but does not queue the rename for Flame's main thread execution.
- Files: `forge_bridge/flame/endpoint.py` (line 426)
- Impact: Changes to shot names in forge-bridge will not propagate back to Flame's timeline, creating a divergence between Flame state and bridge state.
- Fix approach: Implement `_on_entity_updated` to handle shot renames. Requires constructing a callback that can execute on Flame's main thread safely. See existing pattern in `_connect()` and `schedule_idle_event` documentation in `docs/ARCHITECTURE.md`.

**Duplicate dependency declarations in pyproject.toml:**
- Issue: Both `openai` and `anthropic` packages are declared twice in the dependencies list.
- Files: `pyproject.toml` (lines 18-23)
- Impact: Creates confusion about actual requirements. May cause build tool warnings. Wastes lines in config.
- Fix approach: Remove duplicate entries. Consolidate to single declaration of each package.

**No input validation in entity creation messages:**
- Issue: The router's `_handle_entity_create` and related handlers accept message payloads without explicit validation of required fields or type constraints. Validation happens implicitly during entity instantiation, but error messages are not standardized.
- Files: `forge_bridge/server/router.py` (entity creation handlers)
- Impact: Malformed requests may produce unhelpful error messages. Potential for incorrect data to be written to the database if validation is incomplete.
- Fix approach: Add a pre-handler validation layer in `Router.dispatch()` that checks message structure against a schema per message type before routing to handlers.

**Exception swallowing in entity constructors:**
- Issue: In `forge_bridge/core/entities.py`, the `Layer` constructor catches all exceptions in the registry bookkeeping blocks (lines 460-463, 494-496, 500-502) with bare `except Exception: pass`. This silently hides registration failures.
- Files: `forge_bridge/core/entities.py` (lines 460-463, 494-496, 500-502)
- Impact: A layer may be created but not properly registered with the role registry, leading to orphan protection not working and inconsistent state.
- Fix approach: Replace bare exception handlers with specific exception types. Log warnings when bookkeeping fails. Consider failing layer creation if registration fails rather than continuing silently.

**Unimplemented LLM router backends:**
- Issue: The LLMRouter in `forge_bridge/llm_router.py` includes an Ollama backend hardcoded to "assist-01" and Claude backend with environment variable configuration. Both are conditional on specific infrastructure being available. No graceful fallback if both backends are unavailable.
- Files: `forge_bridge/llm_router.py` (lines 38-40, 122-133)
- Impact: If Ollama is down and `ANTHROPIC_API_KEY` is not set, any call to `complete()` with `sensitive=False` will raise RuntimeError, breaking code generation in tools that depend on the router.
- Fix approach: Implement a mock/dummy LLM backend for testing. Add configuration for fallback behavior (fail fast vs. use default responses).

## Known Bugs

**Media status not round-tripped correctly:**
- Symptoms: When creating Media entities, the status field may not persist correctly through database round-trips.
- Files: `forge_bridge/core/entities.py` (lines 378-391, 396-406), recent commits indicate fixes were applied
- Trigger: Create a Media with a specific status, query it back from the database, status may differ.
- Workaround: Explicitly re-set status after database round-trip. Recent fixes (commits ba47fdc, 2b04727) indicate this was a known issue. Verify it's fully resolved in current tests.

## Security Considerations

**No authentication or authorization on WebSocket server:**
- Risk: The forge-bridge server accepts connections from any client that can reach the WebSocket port. There is no authentication (who are you?) or authorization (what are you allowed to do?). Any client can create, read, update, or delete any entity.
- Files: `forge_bridge/server/app.py`, `forge_bridge/server/connections.py`, `forge_bridge/server/router.py`
- Current mitigation: Local-only deployment (not exposed to network). Single user/small trusted team environment. Reliance on network isolation.
- Recommendations: 
  - Implement token-based authentication (JWT or similar) in the handshake. See `docs/ARCHITECTURE.md` (line 149+) — this was explicitly deferred but flagged as required long-term.
  - Add per-client authorization rules (e.g., Flame client can only update its own project).
  - Add audit logging for all mutations (already partially done via event table, but not enforced).

**No validation of file paths in Location entities:**
- Risk: Locations store arbitrary filesystem paths. No validation of:
  - Path traversal attempts (e.g., `../../../etc/passwd`)
  - Symbolic link dereferencing
  - Network path injection
- Files: `forge_bridge/core/traits.py` (lines 127-149, `Location` class), `forge_bridge/flame/endpoint.py` (line 372-373 — adds paths from Flame)
- Current mitigation: Flame endpoint only adds paths derived from Flame's own export (trusted source). Local filesystem only.
- Recommendations:
  - Sanitize paths before storage: canonicalize, block parent directory references.
  - Document assumption that all path sources are trusted (Flame, same-machine scripts).
  - Add a `path_safe()` utility to validate/normalize paths.

**No size limits on JSONB attributes:**
- Risk: Entity attributes stored in JSONB columns have no enforced size limit. A malicious or buggy client could write gigabytes of metadata, exhausting database storage.
- Files: `forge_bridge/store/models.py` (DBEntity, DBProject, DBRole, etc. all have `attributes` JSONB columns)
- Current mitigation: In-memory registry and entity limits (Python object creation limits). Single-user environment.
- Recommendations:
  - Set `max_size` on WebSocket connections (already done: 10MB in `server/app.py` line 128).
  - Add per-attribute size validation in entity creation handlers.
  - Monitor database disk usage.

**LLM Router hardcodes infrastructure details:**
- Risk: The LLMRouter stores hardcoded Ollama host and API details. If that infrastructure changes or is compromised, the code must be updated. No secrets management.
- Files: `forge_bridge/llm_router.py` (lines 38-40, 149)
- Current mitigation: Ollama is on local network ("assist-01"). API key is hardcoded to "ollama" (not a secret).
- Recommendations:
  - Move Ollama endpoint to configuration or environment variable (already partially done — see `FORGE_LOCAL_LLM_URL` on line 38).
  - Use a proper secrets manager for any real API keys (Anthropic key is already sourced from `ANTHROPIC_API_KEY` env var).

## Performance Bottlenecks

**In-memory registry scales linearly with number of roles and relationship types:**
- Problem: The Registry holds all roles and relationship types in Python dictionaries. Operations like `register_usage()` iterate over all refs for an entry to check for orphans. With thousands of custom roles, lookups stay O(1) but deletion checks become O(n).
- Files: `forge_bridge/core/registry.py` (lines 139-550)
- Cause: By design — the registry is meant to be small (hundreds of entries). Relationship type definitions are application-level metadata, not data scale with media.
- Improvement path: Not urgent. If needed, add a `_ref_index` to track only the first few refs and lazy-load more on demand. Or use a database-backed registry for scale.

**Flame endpoint maintains shot and sequence name-to-UUID maps manually:**
- Problem: The FlameEndpoint stores `_shot_ids` and `_seq_ids` as simple Python dicts. If Flame has many shots, lookups by name stay O(1) but the maps must be kept in sync with Flame and bridge state manually.
- Files: `forge_bridge/flame/endpoint.py` (lines 96-97)
- Cause: Early implementation — the maps were needed to correlate Flame's segment callbacks with bridge's shot entities (Flame gives us a segment object, we need to find the corresponding bridge shot ID).
- Improvement path: Replace with a query to bridge when a shot is referenced: `bridge.entity_list(entity_type="shot", name=segment_name)`. Eliminates the map and the sync burden. Costs one RPC per operation but enables correct handling of renamed shots.

**No query optimization in EntityRepo:**
- Problem: Listing entities by type requires fetching from the database and filtering in memory. For projects with thousands of shots, this can be slow.
- Files: `forge_bridge/store/repo.py` (EntityRepo methods)
- Cause: JSONB attributes are flexible but not indexed by entity-specific fields (e.g., sequence_id is in attributes, not a separate column).
- Improvement path: Add indexed columns for frequently-queried attributes (sequence_id, parent_id, etc.). Use database-level filtering instead of in-memory filtering.

## Fragile Areas

**Registry delete+migrate mechanism:**
- Files: `forge_bridge/core/registry.py` (lines 385-434), `forge_bridge/core/entities.py` (Layer._on_role_migration callback, lines 481-484)
- Why fragile: The mechanism relies on every entity that holds a key to register a migration callback and respond correctly. If a callback is missed (not registered), a migration will silently leave that entity with a stale key. If multiple migrations happen in quick succession, callbacks might fire out of order.
- Safe modification:
  - Add comprehensive tests for migration chains (role A → B → C).
  - Add logging when migrations fire so orphans can be detected.
  - Consider making migrations serialized (only one at a time) to avoid ordering issues.
- Test coverage: Covered by `test_core.py` for basic case, but not for race conditions or callback chains.

**Flame endpoint connection handling:**
- Files: `forge_bridge/flame/endpoint.py` (lines 86-157)
- Why fragile: Connection logic is in a separate thread (`_connect()`) but the main thread may call event handlers before the connection completes. The `_require_connection()` check (line 162-167) prevents crashes but silently drops events.
- Safe modification:
  - Ensure `_connected` event is always set before any outbound call is attempted.
  - Use connection status checks in tests to ensure events are not lost.
- Test coverage: No integration tests for connection lifecycle. Tested only in unit tests that assume connection succeeds.

**Media entity status field initialization:**
- Files: `forge_bridge/core/entities.py` (lines 378-391)
- Why fragile: Status is conditionally imported and initialized differently than other status fields. Recent commits (ba47fdc, 2b04727) indicate this was a bug. Current code looks correct but the pattern is fragile.
- Safe modification:
  - Simplify: always import Status at the top of the file, use the same initialization pattern as Shot and Asset.
  - Add a test that verifies status round-trips through a database save/load cycle.

**Server registry seeding on first run:**
- Files: `forge_bridge/server/app.py` (lines 94-112)
- Why fragile: On first startup, the server seeds default roles and relationship types from the Python defaults. If defaults are missing, incomplete, or out of sync with the database, subsequent clients will have stale or incomplete registry state.
- Safe modification:
  - Validate that seeding produced the expected number of roles/types.
  - Add a migration check: compare in-memory Registry with what's in the database, warn on mismatch.
  - Write a recovery tool to rebuild the registry from a known good source.
- Test coverage: No tests for the seeding path.

## Scaling Limits

**Single Postgres instance for all data:**
- Current capacity: Single machine, tested for hundreds of entities and relationships.
- Limit: When would it break?
  - Number of entities: After millions, query performance degrades without sharding.
  - Concurrent clients: Single server connection pool may bottleneck after ~100 concurrent connections.
  - Event log size: Append-only events table grows unbounded. After millions of events, queries that scan the table become slow.
- Scaling path:
  - Event log retention: Implement archival (move old events to cold storage) and summarization (store aggregate data instead of raw events).
  - Query optimization: Add indexes and materialized views for common queries.
  - Connection pooling: Use PgBouncer or similar for better concurrency.
  - Sharding (if needed): Partition entities by project ID.

**In-memory registry on single server:**
- Current capacity: Thousands of roles and relationship types.
- Limit: If many clients connect and each defines custom roles, the registry can grow. Swapping to disk would be slow.
- Scaling path:
  - If registry size becomes an issue (unlikely), make it database-backed with a cache layer.
  - For now, document that custom role definitions should be added at startup, not per-connection.

## Dependencies at Risk

**Anthropic API key stored in environment variable:**
- Risk: `ANTHROPIC_API_KEY` is required for cloud LLM completions. If exposed (in logs, config files, etc.), the account is compromised.
- Impact: Anyone who gets the key can make API calls on the account's dime.
- Migration plan: Move to a secrets manager (AWS Secrets Manager, Vault, etc.). Or use short-lived tokens.

**Ollama dependency for sensitive data processing:**
- Risk: Ollama ("assist-01") is a single point of failure. If it goes down, all sensitive LLM operations fail.
- Impact: Forge tools that rely on sensitive=True completions (code generation, regex logic, etc.) will break.
- Migration plan: Add a fallback to a cached/mock model, or accept that sensitive ops require Ollama.

**Old Flame HTTP bridge code still in flux:**
- Risk: `flame_hooks/forge_bridge/scripts/` contains multiple versions (forge_bridge.py, forge_bridge_v2.py, forge_bridge_pipeline.py). It's unclear which is active.
- Impact: Bugs fixed in one version may not be fixed in others. Maintenance confusion.
- Migration plan: Audit which version is deployed. Delete unused versions. Consolidate into a single canonical hook.

## Missing Critical Features

**No implemented dependency graph engine:**
- Problem: The design calls for automatic dependency graph construction and change propagation. Current code has the data structures (traits, relationships) but no engine that parses incoming data, identifies entities, builds the graph, and propagates notifications.
- Blocks: Impact analysis tools, change propagation, blast radius queries.
- Priority: High — this is core to the bridge's value proposition.

**No versioning/branching for registry changes:**
- Problem: When a role is renamed or a relationship type is deleted, the change is immediate and global. There is no way to stage changes, test them, or roll them back.
- Blocks: Safe evolution of the registry in production. Running migrations.
- Priority: Medium — needed before this is used in multi-team environments.

**No schema evolution tooling for entity attributes:**
- Problem: Entities store JSON in the `attributes` column. If the schema of those attributes changes (a field is renamed, type changes, etc.), there is no migration path to update existing records.
- Blocks: Safe schema evolution. Backwards compatibility.
- Priority: Medium — not urgent while the schema is evolving, but critical once it stabilizes.

**No explicit data validation schema:**
- Problem: Entities accept arbitrary attributes. There is no schema definition of what fields are valid for each entity type, what types they must be, what values are allowed.
- Blocks: Catching invalid data early. Clear API contracts.
- Priority: Medium — needed before external integrations rely on the bridge.

**No WebSocket reconnection or fallback logic in clients:**
- Problem: If the WebSocket connection drops, clients do not automatically reconnect. They require manual intervention or a restart.
- Blocks: Resilience to network hiccups. Automatic failover.
- Priority: Medium — not critical for local development but essential for production.

## Test Coverage Gaps

**Flame endpoint event handler tests:**
- What's not tested: The callbacks registered in `_register_inbound_handlers()` (_on_entity_updated, _on_role_renamed) are not tested. No tests verify that server events trigger Flame-side updates.
- Files: `forge_bridge/flame/endpoint.py`
- Risk: Flame-side effects (renaming segments, updating metadata) may break silently.
- Priority: High — Flame integration is critical to the system.

**Server router concurrency tests:**
- What's not tested: Multiple clients connecting and sending messages simultaneously. Race conditions in entity creation, relationship updates, event broadcast.
- Files: `forge_bridge/server/router.py`, `forge_bridge/server/connections.py`
- Risk: Data corruption or stale state in multi-client scenarios.
- Priority: High — the server is designed for concurrent clients.

**Database transaction isolation:**
- What's not tested: Multiple clients updating the same entity simultaneously (e.g., two clients renaming the same shot). No tests verify that the database constraints prevent corruption.
- Files: `forge_bridge/store/session.py`, `forge_bridge/store/repo.py`
- Risk: Dirty reads, lost updates.
- Priority: Medium — depends on concurrency patterns in actual use.

**LLMRouter backend availability:**
- What's not tested: Behavior when Ollama is down, when Anthropic API key is missing, when both backends are unavailable.
- Files: `forge_bridge/llm_router.py`
- Risk: Tools that depend on LLM completions crash or hang.
- Priority: Medium — not critical until tools rely on it.

**Media entity database round-trip:**
- What's not tested: Save Media to database and query it back. Verify all fields (including status) survive the round-trip.
- Files: `forge_bridge/core/entities.py`, `forge_bridge/store/repo.py`
- Risk: Status field or other attributes may not persist correctly (as was the case in commits ba47fdc, 2b04727).
- Priority: High — foundational to data integrity.

---

*Concerns audit: 2026-04-14*
