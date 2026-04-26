# Phase 13 (FB-A): Staged Operation Entity & Lifecycle — Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 6 (5 production + 1 test bundle)
**Analogs found:** 6 / 6 (all have strong in-tree analogs)

---

## Executive Summary (read first)

Three project conventions dominate this phase. Every pattern below derives from one of them.

1. **Single-table polymorphism** — `DBEntity` discriminates by `entity_type`; type-specific data lives in JSONB `attributes`. New rows for `staged_operation` need ZERO schema changes beyond extending the `ck_entities_type` CHECK and the Python `ENTITY_TYPES` frozenset.
2. **Append-only events with no DB-level vocabulary check** — `EVENT_TYPES` is a Python frozenset only; `events.event_type` has NO CHECK constraint at the DB layer (verified — see `models.py` and `0001_initial_schema.py`). Adding `staged.*` events is a Python-only edit. **D-15's migration needs only the entity_type constraint update — confirms Claude's Discretion bullet about EVENT_TYPES enforcement.**
3. **Application-layer enforcement** — Repos own business rules; the DB stores shape. `RegistryError` family in `core/registry.py` is the only existing exception convention to mirror for `StagedOpLifecycleError`.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `forge_bridge/store/models.py` (modify lines 207-209, 441-460, 292-303) | schema constants + CHECK | data definition | self (existing `ENTITY_TYPES`/`EVENT_TYPES`/`ck_entities_type`) | exact |
| `forge_bridge/store/repo.py` (extend) OR new `forge_bridge/store/staged_operations.py` | repo (state machine) | request-response (CRUD + transition) | `EntityRepo` (`repo.py:237-471`) + `EventRepo` (`repo.py:606-674`) | exact |
| `StagedOpLifecycleError` (new exception, location TBD by planner) | exception class | n/a | `RegistryError`/`OrphanError` (`core/registry.py:91-128`) | exact (different module — see Analog Distance note) |
| `forge_bridge/core/entities.py` (extend) OR new `forge_bridge/core/staged.py` | application class | object construction + serialization | `Version` class (`core/entities.py:296-343`) — non-Versionable, status-bearing, not project-scoped, has parent/created_by | exact |
| `forge_bridge/store/migrations/versions/0003_staged_operation.py` | Alembic migration | DDL | `0002_role_class_media_roles_process_graph.py:96-103` (drop+recreate CHECK idiom) | exact |
| `tests/test_staged_operations.py` (note: tests are flat, NOT under `tests/store/`) | test | async ORM round-trip | NO existing async-DB test in `tests/` — closest is the conftest-fixture pattern | role-match (see Test Strategy section) |

### Classification notes for the planner
- The CONTEXT.md says "tests/store/test_staged_operations.py" but **the project uses a flat `tests/` layout** — there is no `tests/store/` directory. The planner should default to `tests/test_staged_operations.py` unless it explicitly creates a new subdir.
- No async-DB integration test exists in the main tree today. The planner has design freedom here (Claude's Discretion D-19) — this is the most novel piece of test infrastructure in the phase.

---

## Pattern Assignments

### 1. `forge_bridge/store/models.py` — extend `ENTITY_TYPES`, `EVENT_TYPES`, and the CHECK constraint

**Analog:** self (lines already shape the canonical pattern). Three independent edits, all trivial.

**`ENTITY_TYPES` extension** (`models.py:207-209`):
```python
ENTITY_TYPES = frozenset({
    "sequence", "shot", "asset", "version", "media", "layer", "stack"
})
```
Add `"staged_operation"` — the frozenset is the SOLE Python-side gate.

**`EVENT_TYPES` extension** (`models.py:441-460`):
```python
EVENT_TYPES = frozenset({
    # Registry events
    "role.registered", "role.renamed", "role.label_changed",
    ...
    # Pipeline events
    "version.published",     # A Version (comp/batch) was published to a Shot
    "media.ingested",        # A raw media atom arrived via ingest
    "media.derived",         # A media atom was derived from another (lineage hop)
    "media.registered",      # A media atom was registered from a publish hook
    "entity.deleted",
    "client.connected", "client.disconnected",
})
```
Add a new `# Staged operations` block with the five events (D-06):
```python
    # Staged operations (FB-A — proposer/approver/executor lifecycle)
    "staged.proposed",
    "staged.approved",
    "staged.rejected",
    "staged.executed",
    "staged.failed",
```
**Pattern note:** comment-grouping by domain, granular per-action verbs in dotted form (no generic `staged.changed`). Matches `version.published`, `media.ingested`.

**CHECK constraint generator** (`models.py:292-296`):
```python
__table_args__ = (
    CheckConstraint(
        f"entity_type IN ({', '.join(repr(t) for t in sorted(ENTITY_TYPES))})",
        name="ck_entities_type",
    ),
    ...
)
```
This is auto-generated from `ENTITY_TYPES` — adding `"staged_operation"` to the frozenset propagates here for fresh `create_tables()` runs. Existing databases need the migration in §5 below to retrofit. **No code edit needed in this expression — it reads `ENTITY_TYPES` at module import time.**

**EVENT_TYPES CHECK constraint?** None exists. Confirmed by:
- `models.py` `DBEvent.__table_args__` (lines 499-503) contains only Index() entries
- `0001_initial_schema.py:141-156` creates the events table with NO CheckConstraint
- `grep -n "ck_event\|CheckConstraint"` returns only the three existing constraints (`ck_entities_type`, `ck_locations_owner`, `ck_locations_storage_type`)

**Implication for D-15:** the new migration touches `ck_entities_type` ONLY. Event-type additions are Python-only.

---

### 2. `StagedOpRepo` — state machine + event append

**Primary analog:** `EntityRepo` for the persistence shape (`repo.py:237-471`).
**Secondary analog:** `EventRepo` for the audit append (`repo.py:606-631`).

**Repo class shell pattern** (`repo.py:237-281`, `EntityRepo.__init__` and `EntityRepo.save`):
```python
class EntityRepo:
    """Persist and load all non-project entities.

    Translates between core entity objects and the single DBEntity table.
    Entity-specific attributes are serialized to/from the JSONB column.
    """

    def __init__(self, session: AsyncSession, registry: Registry):
        self.session  = session
        self.registry = registry

    async def save(
        self,
        entity: BridgeEntity,
        project_id: uuid.UUID | None = None,
    ) -> DBEntity:
        """Insert or update an entity record."""
        entity_type = entity.entity_type
        attrs       = self._attrs_to_dict(entity)
        name        = getattr(entity, "name", None)
        status_val  = None

        if hasattr(entity, "status"):
            status_val = entity.status.value if hasattr(entity.status, "value") else str(entity.status)

        existing = await self.session.get(DBEntity, entity.id)

        if existing:
            existing.name       = name
            existing.status     = status_val
            existing.attributes = attrs
            if project_id:
                existing.project_id = project_id
            return existing
        else:
            db_entity = DBEntity(
                id=entity.id,
                entity_type=entity_type,
                project_id=project_id,
                name=name,
                status=status_val,
                attributes=attrs,
            )
            self.session.add(db_entity)
            return db_entity
```

**Patterns to copy verbatim into `StagedOpRepo`:**
- Constructor signature: `__init__(self, session: AsyncSession)`. `StagedOpRepo` does NOT need `registry` (no role/relationship-key resolution).
- `await self.session.get(Model, id)` for primary-key fetch
- `self.session.add(...)` to insert; mutate-in-place for update
- `existing.attributes = attrs` (full replace, not merge — matches D-02 immutability of `parameters` enforced by repo, not DB)
- All methods `async def` returning the DB object or core entity

**Event append pattern** (`repo.py:606-631`, `EventRepo.append`):
```python
class EventRepo:
    """Append-only event log. Nothing here updates or deletes records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append(
        self,
        event_type: str,
        payload: dict,
        *,
        session_id: uuid.UUID | None = None,
        client_name: str | None = None,
        project_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> DBEvent:
        event = DBEvent(
            event_type=event_type,
            session_id=session_id,
            client_name=client_name,
            project_id=project_id,
            entity_id=entity_id,
            payload=payload,
        )
        self.session.add(event)
        return event
```
**To copy:** `StagedOpRepo` does NOT re-implement event append — it composes `EventRepo`. Recommended sketch:

```python
class StagedOpRepo:
    """Persist staged operations and enforce the proposed → approved → executed
    state machine. Every transition appends a DBEvent for full audit replay.
    """

    # State machine — single source of truth (D-10)
    _ALLOWED_TRANSITIONS: frozenset[tuple[str | None, str]] = frozenset({
        (None,        "proposed"),
        ("proposed",  "approved"),
        ("proposed",  "rejected"),
        ("approved",  "executed"),
        ("approved",  "failed"),
    })

    # Map (old_status, new_status) → event_type
    _TRANSITION_EVENTS: dict[tuple[str | None, str], str] = {
        (None,        "proposed"): "staged.proposed",
        ("proposed",  "approved"): "staged.approved",
        ("proposed",  "rejected"): "staged.rejected",
        ("approved",  "executed"): "staged.executed",
        ("approved",  "failed"):   "staged.failed",
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self._events = EventRepo(session)   # compose, don't reimplement

    async def propose(
        self,
        operation: str,
        proposer: str,
        parameters: dict,
        project_id: uuid.UUID | None = None,
    ) -> "StagedOperation": ...

    async def approve(self, op_id: uuid.UUID, approver: str) -> "StagedOperation": ...
    async def reject(self, op_id: uuid.UUID, approver: str) -> "StagedOperation": ...
    async def execute(
        self, op_id: uuid.UUID, executor: str, result: dict
    ) -> "StagedOperation": ...
    async def fail(
        self, op_id: uuid.UUID, executor: str, result: dict
    ) -> "StagedOperation": ...

    # Internal — enforces D-08, D-10
    async def _transition(
        self,
        op_id: uuid.UUID,
        new_status: str,
        actor: str,
        attribute_updates: dict | None = None,
    ) -> "StagedOperation":
        db_entity = await self.session.get(DBEntity, op_id)
        if db_entity is None or db_entity.entity_type != "staged_operation":
            raise StagedOpLifecycleError(...)
        old_status = db_entity.status
        if (old_status, new_status) not in self._ALLOWED_TRANSITIONS:
            raise StagedOpLifecycleError(
                f"Illegal transition from {old_status!r} to {new_status!r} "
                f"for staged_operation {op_id}"
            )
        # ...mutate db_entity.status, db_entity.attributes; append event...
```

**Why compose `EventRepo` instead of writing `DBEvent` directly:** keeps the "append to events" idiom in one place (mirrors how `EntityRepo` does NOT call `self.session.add(DBEvent(...))` directly anywhere — events are always written via `EventRepo`).

**Where the repo lives:** Claude's Discretion. The existing `repo.py` is already 28KB / 720 lines — adding a 6th repo class will make it long but consistent. **Recommendation: new `forge_bridge/store/staged_operations.py`** because (a) the state-machine constants (`_ALLOWED_TRANSITIONS`, `_TRANSITION_EVENTS`) are unique to this entity, (b) it imports from both models and entities, matching `repo.py`'s import shape, and (c) it lets the planner add the `StagedOpLifecycleError` class in the same file without growing `repo.py`. Re-export from `forge_bridge/store/__init__.py` next to the existing repo exports.

---

### 3. `StagedOpLifecycleError` — exception class

**Analog:** `OrphanError`/`ProtectedEntryError` (`core/registry.py:95-120`).

**Pattern** (`core/registry.py:91-120`):
```python
# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class RegistryError(Exception):
    """Raised when a registry operation would leave entities in an invalid state."""


class OrphanError(RegistryError):
    """Raised when a delete would leave entities with a dangling key."""

    def __init__(self, name: str, ref_count: int, entity_ids: list[uuid.UUID]):
        self.name = name
        self.ref_count = ref_count
        self.entity_ids = entity_ids
        super().__init__(
            f"Cannot delete '{name}': {ref_count} "
            f"entit{'y' if ref_count == 1 else 'ies'} still reference it. "
            f"Pass migrate_to='<name>' to reassign them first, "
            f"or call registry.roles.release(key, entity_id) on each manually.\n"
            f"Referencing entity IDs: {[str(eid) for eid in entity_ids[:5]]}"
            f"{'...' if len(entity_ids) > 5 else ''}"
        )


class ProtectedEntryError(RegistryError):
    """Raised when attempting to delete a protected entry."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"'{name}' is a protected (built-in) entry and cannot be deleted. "
            f"You can rename its label: registry.roles.rename_label('{name}', 'New Label')"
        )
```

**Patterns to copy:**
- Subclass `Exception` directly (no shared "BridgeError" base in this codebase — `RegistryError` is its own root)
- Stash structured fields on `self` (`.name`, `.ref_count`) for callers that want to introspect rather than parse the message
- Build the message in `__init__` and pass to `super().__init__(msg)`
- One-line docstring stating when raised

**`StagedOpLifecycleError` template:**
```python
class StagedOpLifecycleError(Exception):
    """Raised when a staged operation transition is not permitted by the state machine."""

    def __init__(
        self,
        from_status: str | None,
        to_status: str,
        op_id: uuid.UUID,
    ):
        self.from_status = from_status
        self.to_status   = to_status
        self.op_id       = op_id
        super().__init__(
            f"Illegal transition from {from_status!r} to {to_status!r} "
            f"for staged_operation {op_id}"
        )
```

**Analog Distance note:** the registry exceptions live in `core/`, but `StagedOpLifecycleError` belongs in `store/` per D-09 because it's a repo-layer error, not a vocabulary-layer error. The naming convention (`<Subject><Concern>Error`) is what we copy, not the location.

**Public API gate:** `forge_bridge/__init__.py:55-77` (`__all__`) currently re-exports zero error classes — `RegistryError`, `OrphanError`, etc. are exported only from `forge_bridge.core` (see `core/__init__.py:78-83`). **D-09 keeping `StagedOpLifecycleError` out of `forge_bridge.__all__` is consistent with existing convention** — it can still be exported from `forge_bridge.store.__init__.py`'s `__all__` if FB-B will need to import it (recommended); it just stays off the package-root surface.

---

### 4. `StagedOperation` application class

**Analog:** `Version` class (`core/entities.py:296-343`). Match quality: exact.

**Why `Version` is the right pick:**
- NOT `Versionable` (Version itself isn't versioned — operations aren't either, per D-18)
- HAS `status` (Status enum-like state field)
- HAS `created_by` (free-string actor — the closest existing analog to D-11's free-string actors)
- HAS `parent_id` + `parent_type` (a non-FK reference to another entity — pattern for staged_op's optional `project_id` plus future "this op affects shot X")
- Adds custom fields beyond the `BridgeEntity` base

**Pattern** (`core/entities.py:296-343`):
```python
class Version(BridgeEntity):
    """A specific iteration of a Shot or Asset at a point in time.

    Versions are immutable once created. A new iteration is always
    a new Version entity with a higher version_number.

    parent_type is "shot" or "asset" — determines what the version
    belongs to.
    """

    def __init__(
        self,
        version_number: int,
        parent_id: Optional[uuid.UUID | str] = None,
        parent_type: str = "shot",
        status: Status | str = Status.PENDING,
        created_by: Optional[str] = None,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.version_number: int = version_number
        self.parent_id: Optional[uuid.UUID] = (
            uuid.UUID(str(parent_id)) if parent_id else None
        )
        self.parent_type: str = parent_type
        self.status: Status = (
            Status.from_string(status) if isinstance(status, str)
            else (status if status is not None else Status.PENDING)
        )
        self.created_by: Optional[str] = created_by

        if self.parent_id:
            self.add_relationship(self.parent_id, "version_of")

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "version_number": self.version_number,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "parent_type": self.parent_type,
            "status": self.status.value,
            "created_by": self.created_by,
        })
        return d

    def __repr__(self) -> str:
        return f"Version(v{self.version_number}, parent={self.parent_id!s:.8}...)"
```

**Patterns to copy verbatim:**
- `class StagedOperation(BridgeEntity):` — single inheritance from `BridgeEntity`. `BridgeEntity` already mixes in `Relational, Locatable` (`entities.py:44`). Do NOT add `Versionable` (D-18).
- `super().__init__(id=id, metadata=metadata)` — the **only** way to construct the base. Note: `metadata` (dict) is the open key/value bag. The typed fields (`proposer`, `operation`, …) live as direct attributes ON THE INSTANCE, not inside `metadata`. The `EntityRepo._attrs_to_dict` method (`repo.py:335-389`) is what merges `metadata` + typed fields into the JSONB column at save time.
- `self.<field>: Optional[uuid.UUID] = uuid.UUID(str(x)) if x else None` — the canonical UUID coercion in `__init__`
- `self.status: Status = Status.from_string(status) if isinstance(status, str) else (status if status is not None else Status.PENDING)` — but **for staged_op, `status` is a free string (`"proposed"`/`"approved"`/etc.)**, NOT the existing `Status` enum (which is `PENDING/IN_PROGRESS/REVIEW/APPROVED/PUBLISHED/REJECTED`). The values overlap conceptually but the lifecycle is different. **Recommendation: store `status: str` directly, not `Status`.** This matches the D-08 "no DB enum, no validation at the type level" decision.
- `to_dict(self)` always extends via `d = super().to_dict(); d.update({...}); return d` — this is non-negotiable. The base `to_dict` (`entities.py:74-82`) provides `id`, `entity_type`, `created_at`, `metadata`, `locations`, `relationships`. STAGED-06 (zero-divergence with FB-B) requires this single-source-of-truth shape.
- `if self.<parent_id>: self.add_relationship(...)` — auto-declares an entity relationship in the in-memory graph. **For staged_operation: the planner can choose to leave this OUT in v1.4** (D-18 says relational trait is kept but unexercised). If the operation has a target shot/asset, calling `self.add_relationship(target_id, "references")` is fine and forward-compatible.

**Status default:** `Version` defaults to `Status.PENDING`. `StagedOperation` should default to `"proposed"` — but the **state-machine entry point lives in the repo**, not the constructor. Recommended: the constructor accepts `status: str = "proposed"` to match the data shape; the repo's `propose()` method is the only sanctioned way to mint one (so the `staged.proposed` event always fires).

**`to_dict` shape for staged_operation** (per D-02 + the FB-B contract):
```python
def to_dict(self) -> dict:
    d = super().to_dict()
    d.update({
        "operation":   self.operation,
        "proposer":    self.proposer,
        "parameters":  self.parameters,
        "result":      self.result,
        "status":      self.status,
        "approver":    self.approver,
        "executor":    self.executor,
        "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        "executed_at": self.executed_at.isoformat() if self.executed_at else None,
    })
    return d
```
This is what FB-B's MCP tool returns will mirror byte-for-byte (STAGED-06 zero-divergence).

**`entity_type` property:** the base class derives it from class name: `return self.__class__.__name__.lower()` (`entities.py:71-72`). `StagedOperation.__name__.lower() == "stagedoperation"` — **this does NOT match `"staged_operation"`**. The planner must override:
```python
@property
def entity_type(self) -> str:
    return "staged_operation"
```
This is the same problem the planner will need to solve; flag it now to avoid a class of subtle bugs at save time (the `EntityRepo.save` method reads `entity.entity_type` at `repo.py:254` to populate the discriminator column).

**Where the class lives:** Claude's Discretion. `entities.py` is already 22KB. **Recommendation: new `forge_bridge/core/staged.py`** to keep `entities.py` focused on the original-vocabulary entities and to make FB-B's import line read `from forge_bridge.core.staged import StagedOperation`. Re-export from `forge_bridge/core/__init__.py` next to the other entity exports (lines 24-34).

---

### 5. `forge_bridge/store/migrations/versions/0003_staged_operation.py`

**Analog:** `0002_role_class_media_roles_process_graph.py:96-103` (the "drop CHECK + recreate CHECK" idiom for `ck_locations_storage_type`). Match quality: exact.

**Filename convention** (verified by `ls versions/`): `NNNN_short_description.py`, 4-digit zero-padded, words separated by underscores. CONTEXT.md picks `0003_staged_operation.py` — confirmed correct.

**Header pattern** (`0002`:1-55):
```python
"""Role class discriminator, media lineage roles, process graph relationships.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-27

Changes:
  registry_roles
    - Add role_class column (VARCHAR 32, NOT NULL, DEFAULT 'track')
    - Seed media lineage roles: raw, grade, denoise, prep, roto, comp
  ...
"""

import uuid
import sqlalchemy as sa
from alembic import op


# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None
```

**To copy:**
- Module docstring with "Changes:" subsection summarizing every DDL effect
- `revision = "0003"`, `down_revision = "0002"`
- Imports limited to `sqlalchemy as sa`, `from alembic import op`, plus `uuid` if seeding rows (this migration won't seed — D-16)

**The CHECK-drop-and-recreate idiom** (`0002:96-103` upgrade, `:194-199` downgrade):
```python
# ── 2. Extend storage_type constraint to include 'clip' ───────────────────
# Drop existing CHECK, recreate with 'clip' added
op.drop_constraint("ck_locations_storage_type", "locations", type_="check")
op.create_check_constraint(
    "ck_locations_storage_type",
    "locations",
    "storage_type IN ('local', 'network', 'cloud', 'archive', 'clip')",
)
```
And the matching downgrade:
```python
# Restore original storage_type constraint
op.drop_constraint("ck_locations_storage_type", "locations", type_="check")
op.create_check_constraint(
    "ck_locations_storage_type",
    "locations",
    "storage_type IN ('local', 'network', 'cloud', 'archive')",
)
```

**Adapted for `0003`:**
```python
def upgrade() -> None:
    # Extend ck_entities_type to include 'staged_operation'
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        "entity_type IN ('asset', 'layer', 'media', 'sequence', 'shot', "
        "'stack', 'staged_operation', 'version')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        "entity_type IN ('asset', 'layer', 'media', 'sequence', 'shot', "
        "'stack', 'version')",
    )
```

**Pattern notes:**
- The CHECK list is alphabetical-sorted in `0001:86` (`'asset', 'layer', 'media', 'sequence', 'shot', 'stack', 'version'`). `models.py:294` generates the same order via `sorted(ENTITY_TYPES)`. **The upgrade migration must keep alphabetic order** — `staged_operation` slots between `stack` and `version`.
- No `events` table modification needed (no CHECK constraint on `event_type`, confirmed above).
- No data backfill (D-16).
- No new columns, indexes, or tables.

---

### 6. `tests/test_staged_operations.py` — the four STAGED-01..04 cases

**Honesty check first:** there is currently no async-DB integration test in `tests/`. The conftest fixtures (`tests/conftest.py:1-83`) are all about mocking the Flame bridge or stubbing LLM clients, not about database fixtures. The planner is shipping new test infrastructure for the store layer — this is in scope per Claude's Discretion D-19.

**Project test conventions (extracted from existing tests):**
- Flat layout: tests live directly under `tests/`, named `test_<subject>.py` (verified by `ls tests/`)
- `pytest-asyncio` is in `auto` mode (`pyproject.toml:71`) — async tests do NOT need `@pytest.mark.asyncio`
- Existing fixtures use `monkeypatch` for in-process patching, not external resources
- `conftest.py` defines repo-wide fixtures; per-file fixtures are local

**Analog (closest in-tree):** `tests/conftest.py:74-83` (`free_port` fixture) — the only fixture that touches a real OS resource. Its pattern:
```python
@pytest.fixture
def free_port() -> int:
    """Return an available local port on 127.0.0.1.
    ...
    """
    with _phase11_socket.socket(...) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
```
**To copy:** the docstring + minimal-construction style. NOT the resource (we're not using sockets, we're using a DB).

**Recommended test infrastructure (new for this phase — flag for the planner):**

The planner needs to choose how to provision a DB for the four tests. Two viable paths, both consistent with what's in `forge_bridge/store/session.py`:

**Path A (recommended): live Postgres via `FORGE_DB_URL` env override.**
- Use `get_async_engine(db_url=...)` with a per-test database (e.g., `postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge_test_<uuid>`).
- Run `await create_tables(db_url)` (`session.py:178-185`) at fixture setup, `await drop_tables(db_url)` at teardown.
- Pro: matches production Postgres semantics (JSONB containment ops, GIN indexes, asyncpg driver). The `find_by_attribute` test in STAGED-04 uses `attributes->'parameters'` syntax that is **Postgres-specific** — sqlite cannot run it.
- Con: requires a running Postgres in CI / local dev.

**Path B: skip if Postgres unavailable.**
- `pytest.skip(reason="postgres required")` at module level if a connection fails.
- Acceptable per "local first" project philosophy (CLAUDE.md design table).

**Test case templates** (matching D-19..D-22):

```python
# STAGED-01 — round-trip
async def test_staged_op_round_trip(session_factory):
    """Propose, fetch by id, assert all attributes intact."""
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(
            operation="flame.publish_sequence",
            proposer="mcp:claude-code",
            parameters={"shot_id": "abc", "frames": 100},
        )
        await session.commit()

    async with session_factory() as session:
        repo = StagedOpRepo(session)
        fetched = await repo.get(op.id)
        assert fetched.operation  == "flame.publish_sequence"
        assert fetched.proposer   == "mcp:claude-code"
        assert fetched.parameters == {"shot_id": "abc", "frames": 100}
        assert fetched.status     == "proposed"
        assert fetched.result     is None
```

```python
# STAGED-02 — illegal transitions (parameterized cross-product)
@pytest.mark.parametrize("from_status, to_status, legal", [
    (None,        "proposed",  True),
    ("proposed",  "approved",  True),
    ("proposed",  "rejected",  True),
    ("approved",  "executed",  True),
    ("approved",  "failed",    True),
    # All others illegal
    ("proposed",  "executed",  False),
    ("proposed",  "failed",    False),
    ("approved",  "approved",  False),  # idempotent re-app per D-10
    ("approved",  "rejected",  False),
    ("rejected",  "approved",  False),
    ("executed",  "failed",    False),
    ("failed",    "executed",  False),
    # ...full cross-product
])
async def test_transition_legality(session_factory, from_status, to_status, legal):
    ...
    if legal:
        await repo._transition(op.id, to_status, actor="...")
    else:
        with pytest.raises(StagedOpLifecycleError):
            await repo._transition(op.id, to_status, actor="...")
```

```python
# STAGED-03 — audit replay
async def test_audit_replay_happy_path(session_factory):
    """proposed → approved → executed produces 3 events in order."""
    ...
    events = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
    assert [e.event_type for e in reversed(events)] == [
        "staged.proposed",
        "staged.approved",
        "staged.executed",
    ]
    assert events[-1].payload["old_status"] is None  # proposed event
    assert events[-1].payload["new_status"] == "proposed"
```

```python
# STAGED-04 — SQL-only diff
async def test_sql_only_diff(session_factory):
    """attributes->'parameters' bit-identical across status advancements."""
    from sqlalchemy import select, text
    ...
    stmt = text(
        "SELECT attributes->'parameters' AS params, attributes->'result' AS res "
        "FROM entities WHERE id = :id"
    )
    rows_at_proposed = (await session.execute(stmt, {"id": op.id})).one()
    # advance to approved...
    rows_at_approved = (await session.execute(stmt, {"id": op.id})).one()
    assert rows_at_proposed.params == rows_at_approved.params  # immutable
    assert rows_at_proposed.res    is None
    assert rows_at_approved.res    is None  # not populated until executed/failed
```

**File-granularity recommendation (Claude's Discretion):** **single `tests/test_staged_operations.py`** with the four test functions clearly named per criterion. Splitting per-criterion creates four files of <100 lines each, fragmenting the shared `session_factory` fixture. Single-file matches the rest of `tests/` (e.g., `test_console_health.py` covers many criteria in one file).

---

## Shared Patterns

These apply across all six files.

### Imports + module header

**Source:** every file in `forge_bridge/store/` and `forge_bridge/core/`.
**Apply to:** all new modules.

Standard preamble (`store/repo.py:1-43` and `core/entities.py:1-32` are representative):
```python
"""<module purpose — one paragraph>.

<Optional: design notes, import examples, etc.>
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone   # only if timestamps are constructed in-module
from typing import Any, Optional

from sqlalchemy import delete, select, update                # store/ only
from sqlalchemy.ext.asyncio import AsyncSession              # store/ only

from forge_bridge.core.entities import BridgeEntity          # repo/store imports core
from forge_bridge.store.models import DBEntity, DBEvent      # repos depend on models
```
**Mandate:** `from __future__ import annotations` at top — all non-test files use it.

### Status / actor encoding

**Source:** `models.py:483` (`client_name = Column(String(128), nullable=True)`); `0001_initial_schema.py:146`; `repo.py:625` (event append `client_name` parameter).
**Apply to:** every staged-op event append, every actor field on `StagedOperation`.

The free-string actor (D-11) is stored:
- In `DBEvent.client_name` (top-level column for fast filter-by-actor queries)
- In `DBEvent.payload.actor` (denormalized inside JSONB for full-payload reads)
- In `DBEntity.attributes.proposer` / `.approver` / `.executor` (per D-02)

This three-place duplication is intentional and consistent with the existing `version.published` event flow (event tooling reads `client_name` first, falls back to `payload`).

### `BridgeEntity.__init__` deserialization

**Source:** `repo.py:391-471` (`EntityRepo._to_core`).
**Apply to:** `StagedOpRepo._to_core(db: DBEntity) -> StagedOperation`.

The pattern that EVERY existing core entity uses for DB → core conversion (`repo.py:407-414` for Shot is canonical):
```python
elif t == "shot":
    e = Shot.__new__(Shot)
    BridgeEntity.__init__(e, id=db.id, metadata={})
    e.name        = db.name
    e.sequence_id = uuid.UUID(a["sequence_id"]) if a.get("sequence_id") else None
    e.cut_in  = Timecode.from_string(a["cut_in"])  if a.get("cut_in")  else None
    e.cut_out = Timecode.from_string(a["cut_out"]) if a.get("cut_out") else None
    e.status  = Status.from_string(db.status) if db.status else Status.PENDING
```
**To copy:**
- `e = StagedOperation.__new__(StagedOperation)` — bypasses `__init__` so we don't redo UUID generation
- `BridgeEntity.__init__(e, id=db.id, metadata={})` — pass the JSONB-stored metadata back through the base init (or `metadata=db.attributes or {}` — see Asset/Project on lines 226-227 vs Shot on 409 for the inconsistency; planner picks one)
- Manual attribute assignment, with `uuid.UUID(...)` coercion guarded by `if a.get(...)`

**Subtle pattern:** `EntityRepo._to_core` for `version` (lines 424-431) does NOT pass `metadata=db.attributes` — it passes empty dict and copies typed fields onto the entity. For `staged_operation`, follow the Version pattern (typed-fields-on-entity, empty metadata in __init__) since `parameters`/`result`/etc. are typed first-class fields, not free metadata.

### Status property serialization

**Source:** `repo.py:259-260`.
**Apply to:** `StagedOpRepo.save` calls.

```python
if hasattr(entity, "status"):
    status_val = entity.status.value if hasattr(entity.status, "value") else str(entity.status)
```
This handles both enum-status (Shot/Version use `Status` enum) and string-status (StagedOperation uses raw string). **No change needed** — the existing code in `EntityRepo` already accommodates string status via the `else str(entity.status)` branch. If `StagedOpRepo` extends `EntityRepo` or uses similar logic, it works as-is.

### `_attrs_to_dict` extension

**Source:** `repo.py:335-389` (`EntityRepo._attrs_to_dict`).
**Apply to:** wherever staged_operation gets serialized to JSONB.

Add a new `elif t == "staged_operation":` branch following the existing pattern (lines 347-388):
```python
elif t == "staged_operation":
    op = entity
    a["operation"]   = op.operation
    a["proposer"]    = op.proposer
    a["parameters"]  = op.parameters
    a["result"]      = op.result
    a["approver"]    = op.approver
    a["executor"]    = op.executor
    a["approved_at"] = op.approved_at.isoformat() if op.approved_at else None
    a["executed_at"] = op.executed_at.isoformat() if op.executed_at else None
```
Per D-02, the JSONB shape is exactly this (no nesting under a `staged_operation` sub-key). The opening `a = dict(entity.metadata or {})` at line 345 ensures unknown metadata round-trips for free.

**Question for the planner:** does `StagedOpRepo` reuse `EntityRepo._attrs_to_dict` (by composing or inheriting `EntityRepo`), or duplicate the serialization in `staged_operations.py`? Composing is cleaner (single source of truth) but requires extending `EntityRepo` with a `staged_operation` branch. **Recommendation: extend `EntityRepo._attrs_to_dict` and `EntityRepo._to_core` with the new branch**, and have `StagedOpRepo` delegate `save`/`get` to a private `EntityRepo` instance. This keeps `EntityRepo` as the canonical entity persistence path and `StagedOpRepo` strictly responsible for the state machine and event audit.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_staged_operations.py` | async-DB integration test | DB round-trip + event audit | No existing async-DB test exists in `tests/` today. The four cases require ergonomic DB fixtures that the project hasn't yet codified. |
| `StagedOpRepo._transition` | state-machine method | request-response with side effect | No existing repo method enforces state transitions. `EntityRepo.save` allows arbitrary status updates; `RegistryRepo` uses application-layer validation but not as a state machine. The (from, to) tuple frozenset + event-emitting transition is novel for this codebase. |

For both gaps, `RESEARCH.md` was skipped — the planner has Claude's Discretion (D-19, D-08) to design the patterns. The closest in-tree role-match is documented above.

---

## Critical Pre-Planning Findings

These are facts the planner needs to internalize before drafting plans. They're load-bearing.

1. **`EVENT_TYPES` has no DB CHECK constraint** — verified by inspection of `models.py:499-503` and `0001_initial_schema.py:141-156`. D-15's migration is entity_type ONLY. Resolves the open Claude's-Discretion bullet ("Whether `EVENT_TYPES` enforcement is a CHECK constraint at the DB layer").

2. **`tests/store/` does not exist; `tests/` is flat.** CONTEXT.md's reference to "`tests/store/test_staged_operations.py`" is aspirational. Default to `tests/test_staged_operations.py`.

3. **`BridgeEntity.entity_type` returns `cls.__name__.lower()`** — `StagedOperation.__name__.lower() == "stagedoperation"`. The class MUST override the property to return `"staged_operation"`, or the `EntityRepo.save` code at `repo.py:254` will write the wrong discriminator. This is the #1 silent-bug risk.

4. **No async-DB tests exist today.** The four STAGED tests will need new fixtures (`session_factory`, schema setup/teardown). This is the largest greenfield piece of the phase. Consider co-locating fixtures in `tests/conftest.py` if multiple files end up needing them post-FB-A.

5. **`forge_bridge/store/__init__.py` re-exports the seven existing repo classes** (`store/__init__.py:18-26`). New `StagedOpRepo` (and optionally `StagedOpLifecycleError`) should be added there to keep import lines tidy: `from forge_bridge.store import StagedOpRepo, StagedOpLifecycleError`.

6. **The `Status` enum (in `core/vocabulary.py`, used by Shot/Asset/Version/Media) is NOT what staged_op's `status` field is.** Status enum values are `PENDING/IN_PROGRESS/REVIEW/APPROVED/PUBLISHED/REJECTED` — overlapping vocabulary but a different lifecycle. Use raw strings for staged_operation status, NOT `Status.from_string`. (D-08 rules out DB enum; this rules out application enum too — the values don't fit.)

7. **`StagedOpLifecycleError` should NOT subclass `RegistryError`.** They're unrelated domains. Subclass `Exception` directly, mirroring how `RegistryError` itself does (`registry.py:91`).

8. **Pre-existing convention: events are written via `EventRepo.append`, never via `session.add(DBEvent(...))` directly.** Verify: `grep -rn "session.add(DBEvent" forge_bridge/` returns empty (only the worktree copy at `.claude/worktrees/agent-a566f57e/forge_bridge/server/router.py` shows EntityRepo+EventRepo paired in the same session — the canonical "transition + audit" idiom for FB-A to mirror). `StagedOpRepo` should compose `EventRepo`, not bypass it.

---

## Metadata

**Analog search scope:**
- `forge_bridge/store/` (full read of `models.py`, `repo.py`, `session.py`, both migration versions)
- `forge_bridge/core/entities.py`, `traits.py`, `registry.py` (exception class section)
- `forge_bridge/__init__.py`, `forge_bridge/store/__init__.py`, `forge_bridge/core/__init__.py`
- `tests/conftest.py`; `ls tests/` (flat structure verified)
- `pyproject.toml` (pytest config)

**Files scanned:** 14 production files + 1 test conftest + 2 migration revisions + 3 package-level `__init__.py` files.

**Pattern extraction date:** 2026-04-25

**Lines of context loaded:** ~3500 (CONTEXT.md + the seven primary analog files).
