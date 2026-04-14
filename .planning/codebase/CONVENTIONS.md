# Coding Conventions

**Analysis Date:** 2026-04-14

## Naming Patterns

**Files:**
- Lowercase with underscores: `async_client.py`, `protocol.py`, `registry.py`
- Module names match primary class or concept: `entities.py` contains entity classes, `traits.py` contains trait definitions
- Test files use `test_*.py` prefix

**Functions:**
- Lowercase with underscores (PEP 8): `to_dict()`, `get_relationships()`, `get_default_registry()`
- Private functions prefixed with single underscore: `_get_registry()`, `_new_id()`, `_resolve_rel_key()`
- Lazy import helpers named `_<thing>()`: `_client()`, `_err()`, `_ok()`

**Variables:**
- Lowercase with underscores for module/function scope: `entity_type`, `role_name`, `project_id`
- Abbreviated names for loop counters and temps acceptable: `r` for result, `obj` for object, `msg` for message
- UUID/ID variables always include type suffix: `project_id`, `entity_id`, `role_key`, `rel_key`

**Types/Classes:**
- PascalCase: `BridgeEntity`, `AsyncClient`, `ServerError`, `FrameRange`
- Exception classes end with `Error`: `ClientError`, `ServerError`, `ConnectionError`, `TimeoutError`, `RegistryError`
- Data classes: `@dataclass` decorator used, fields snake_case: `Location(path, storage_type, exists, priority)`
- Constants in UPPER_SNAKE_CASE: `STANDARD_ROLES`, `SYSTEM_REL_KEYS`, `STANDARD_ROLE_KEYS`
- Enum class names PascalCase, members UPPER_CASE: `StorageType.LOCAL`, `MsgType.HELLO`, `ErrorCode.NOT_FOUND`

## Code Style

**Formatting:**
- Tool: ruff (configured in `pyproject.toml`)
- Line length: 100 characters
- Python target: 3.10+
- Imports organized by `from __future__ import annotations` at top (enables forward references)

**Linting:**
- Tool: ruff
- Config in `pyproject.toml`: `[tool.ruff]` section
- Line length 100, target Python 3.10

**Indentation & Spacing:**
- 4 spaces per indentation level (PEP 8 standard)
- Two blank lines between top-level definitions
- One blank line between method definitions in classes
- Sections within files separated by comment blocks using box-drawing characters: `# ─────────────────────────────────────────────────────────────`

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first if used)
2. Standard library imports (`uuid`, `asyncio`, `json`, `logging`, `dataclasses`, `datetime`, `typing`)
3. Third-party imports (`websockets`, `pydantic`, `sqlalchemy`, `httpx`)
4. Local imports (`from forge_bridge...`)

**Path Aliases:**
- None configured — all imports use absolute paths from package root
- Pattern: `from forge_bridge.core import Registry`, `from forge_bridge.server.protocol import Message`

**TYPE_CHECKING Block:**
- Used for circular import prevention: `if TYPE_CHECKING: from forge_bridge.core.registry import Registry`
- Allows type hints in docstrings without runtime circular dependencies

## Error Handling

**Patterns:**
- Custom exception hierarchy with meaningful names: `RegistryError` → `OrphanError`, `ProtectedEntryError`, `UnknownNameError`, `UnknownKeyError`
- Client exceptions inherit from `ClientError`: `ServerError`, `ConnectionError`, `TimeoutError`
- Exception `__init__` includes context: `OrphanError` carries `ref_count`, `entity_ids` for debugging
- Most operations return results or raise exceptions — no silent failures or None returns in critical paths
- MCP tool implementations return JSON with `{"error": message, "code": code}` structure rather than raising (see `_err()` helper in `forge_bridge/mcp/tools.py`)

**Try/except patterns:**
- Top-level handlers in async contexts wrap entire operations
- Exception context preserved in reraises or enriched exceptions
- Specific exception types caught, not bare `except Exception`
- Example: `ServerError` caught in client, converted to user-facing message

## Logging

**Framework:** Python standard library `logging`

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Configured in server startup code
- Logged for: connection state changes, protocol errors, registry mutations, async event processing
- No logging in entity/vocabulary classes — those are data, not operations

## Comments

**When to Comment:**
- Module docstrings (triple-quoted at top): explain purpose, design decisions, usage
- Class docstrings: explain role and relationships
- Complex methods: explain _why_ not _what_ (the code shows what)
- Section headers: box-drawing comments separate logical sections within files

**JSDoc/TSDoc:**
- Not used (this is pure Python, not TypeScript)
- Docstrings use triple quotes: `"""Docstring here."""`
- Docstring format: brief description, optional longer explanation, optional usage example

**Example from `forge_bridge/core/entities.py`:**
```python
class Project(Versionable, BridgeEntity):
    """Top-level container. Everything in bridge lives inside a Project.

    Endpoint mappings:
        Flame:    project (flame.project.current_project)
        ShotGrid: Project entity
        ftrack:   Project
    """
```

## Function Design

**Size:** 
- Most functions 10-50 lines
- Larger methods (100+ lines) appear in routers and stores where complex request handling is necessary
- Trait methods and entity methods kept lean — business logic delegated to registries and stores

**Parameters:**
- Use type hints on all parameters and return types
- Optional parameters have `Optional` type hint and default value
- Complex parameters documented in docstring
- Example: `def hello(client_name: str, endpoint_type: str = "unknown", capabilities: dict | None = None, last_event_id: str | None = None) -> Message`

**Return Values:**
- All non-void returns typed
- Consistent return types within function family (all role methods return dict structures with same keys)
- When operation can fail, raise exception rather than return None
- Example: `get_by_name()` raises `UnknownNameError` rather than returning None

## Module Design

**Exports:**
- Explicit imports in `__init__.py` files define public API
- Example `forge_bridge/core/__init__.py` imports and re-exports: `Asset`, `FrameRange`, `Layer`, `Location`, `Media`, `Project`, `Registry`, etc.
- Implementation files may be imported directly but canonical imports go through package `__init__.py`

**Barrel Files:**
- Used: `forge_bridge/core/__init__.py` aggregates all entity and registry types
- Not used elsewhere — imports are specific and explicit

**Module cohesion:**
- `forge_bridge/core/` — vocabulary, entities, traits, registry (immutable data definitions)
- `forge_bridge/server/` — wire protocol, connection management, routing, request handling
- `forge_bridge/client/` — async and sync clients for connecting to server
- `forge_bridge/mcp/` — MCP server and tool implementations
- `forge_bridge/flame/` — Flame endpoint integration
- `forge_bridge/store/` — database models, migrations, repository layer
- `forge_bridge/tools/` — legacy Flame bridge tools (pre-server)

## Type Hints

**Usage:**
- All function signatures include type hints
- All class attributes declared with type hints
- Dataclass fields typed: `@dataclass class Location: path: str; storage_type: StorageType`
- Union types use `|` syntax (Python 3.10+): `uuid.UUID | str`, `dict | None`
- Optional use `Optional` from typing: `Optional[uuid.UUID]` or `dict | None`
- Generic collections typed: `dict[str, Any]`, `list[uuid.UUID]`

**Forward references:**
- Enabled via `from __future__ import annotations` at module top
- Allows referencing types defined later in module or that create circular imports

## Constants and Enums

**Pattern:**
- Well-known UUIDs defined as module-level constants: `SYSTEM_REL_KEYS`, `STANDARD_ROLE_KEYS`
- Permanent — never change between versions (documented in comments)
- Reverse maps created: `_SYSTEM_REL_NAMES` maps UUID → name for fallback lookups
- Enums use `Enum` or `str` mixin for serialization: `class StorageType(str, Enum): LOCAL = "local"`

---

*Convention analysis: 2026-04-14*
