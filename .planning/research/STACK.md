# Technology Stack — v1.2 Observability & Provenance (EXT-02 + EXT-03)

**Project:** forge-bridge v1.2 (EXT-02 MCP tool annotations + EXT-03 SQL persistence Protocol)
**Researched:** 2026-04-17
**Scope:** Only the dependency / version-pin decisions needed for the two new features. See `STACK-v1.1.md` for the prior milestone's full stack.
**Overall confidence:** HIGH

---

## MCP annotation surface (EXT-02)

### What the spec actually says (as of 2025-06-18 revision)

The current live spec is **2025-06-18** (modelcontextprotocol.io/docs/concepts/tools and `/specification/2025-06-18/server/tools`). A `Tool` object on the wire has **six** optional metadata slots, three of which are relevant here:

| Field | Type | Purpose |
|-------|------|---------|
| `name` | `str` (required) | Unique tool ID |
| `title` | `str \| null` | Human-readable display title |
| `description` | `str \| null` | Free-prose description |
| `inputSchema` / `outputSchema` | JSON Schema | Arg / return validation |
| `annotations` | `ToolAnnotations \| null` | **Fixed-shape behavioral hints only** (see below) |
| `_meta` | `dict[str, Any] \| null` | **Freeform custom-extension bag** |
| `icons` | `list[Icon] \| null` | UI icons |
| `execution` | `ToolExecution \| null` | Task-support hints |

**Critical distinction.** "Annotations" in MCP vocabulary does **not** mean "arbitrary metadata." `ToolAnnotations` is a closed schema with exactly five fields:

```
ToolAnnotations:
  title: str | null
  readOnlyHint: bool | null
  destructiveHint: bool | null
  idempotentHint: bool | null
  openWorldHint: bool | null
```

These are safety/behavior hints for clients. Our provenance payload (`project`, `intent`, `code_hash`, `tags`) **does not fit here** — there is no freeform property bag inside `ToolAnnotations`, and the spec explicitly warns clients that annotations from untrusted servers must be ignored.

**The correct slot is `_meta`** (serialized as the literal key `_meta` on the wire; exposed as the `meta: dict[str, Any]` Python attribute on `mcp.types.Tool`, via `Field(alias='_meta')`). From the spec's `General fields: _meta` section, `_meta` is defined as *"optional metadata that can contain any key-value pairs for custom extensions"* — exactly the EXT-02 contract.

Verified against the installed `mcp==1.26.0` Pydantic schema — `Tool.model_fields` shows:
- `annotations: ToolAnnotations | None = None`
- `meta: dict[str, Any] | None = None  (alias='_meta', alias_priority=2)`
- `title: str | None = None`
- `icons: list[Icon] | None = None`

### FastMCP SDK surface

The Python SDK reached parity with the spec in stages; the critical commits + release mapping:

| Release | Date | Feature |
|---------|------|---------|
| **v1.7.0** | 2025-05-01 | `ToolAnnotations` param on `FastMCP.tool()` / `add_tool()` (PR #482) |
| **v1.10.0** | 2025-06-26 | `title` param added for tools/resources/prompts (PR #972) |
| **v1.15.0** | 2025-09-25 | SEP 973 — icons + `_meta` on types, end-to-end (PR #1357) |
| **v1.19.0** | 2025-10-24 | **`meta: dict[str, Any]` param on `FastMCP.tool()` decorator** (PR #1463) |
| v1.26.0 | 2026-01-24 | Backport-only release on `v1.x` branch |
| v1.27.0 | 2026-04-02 | Backport-only release on `v1.x` branch |

The signature we depend on (verified against local `mcp==1.26.0` install):

```python
FastMCP.tool(
    self,
    name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    annotations: ToolAnnotations | None = None,
    icons: list[Icon] | None = None,
    meta: dict[str, Any] | None = None,       # <-- the EXT-02 attach point
    structured_output: bool | None = None,
) -> Callable[[AnyFunction], AnyFunction]
```

Verified end-to-end — the following roundtrips cleanly on 1.26.0:

```python
@mcp.tool(
    name="synth_reconform_from_linked_timelines",
    title="Reconform from Linked Timelines",
    meta={
        "provenance": "forge_bridge.learning",
        "project": "alpha",
        "intent": "reconform a shot stack",
        "code_hash": "abc123…",
        "tags": ["source:synthesized", "intent:reconform"],
    },
)
async def synth_reconform(...) -> str: ...
```

### Version pin decision

**Bump `mcp[cli]>=1.0` → `mcp[cli]>=1.19,<2` in `pyproject.toml`.**

Rationale:

1. **Lower bound `>=1.19`** — floor is the first release shipping `meta=` on `FastMCP.tool()`. 1.18 and earlier force us into the workaround path (JSON-encoded description, which is hostile to LLM agents reading the description as free prose, and invisible to clients that only consult `_meta`).
2. **Upper bound `<2`** — mcp `main` branch (post-v1.27) is renaming `FastMCP → MCPServer` (commit `65c614e`, 2026-01-25). Our entire `forge_bridge/mcp/server.py` is built on `from mcp.server.fastmcp import FastMCP`. v2 will be a coordinated migration, not an accidental `pip install --upgrade` breakage. Pin the major.
3. **No migration risk from v1.0 → v1.19 on the existing `register_tools` contract.** The decorator signature added parameters; it did not remove or rename any. A quick audit of `forge_bridge/mcp/registry.py` + all builtin tool registrations would only need to verify no downstream consumer is relying on positional args beyond `name=` (which would be fragile regardless).
4. **projekt-forge is already resolved** — since projekt-forge consumes forge-bridge via git-URL tag pin (`git+https://…@v1.1.1`), bumping the `mcp[cli]` requirement here propagates cleanly through pip's resolver.

**Breaking-change hazards to validate in a Plan 07-XX task:**
- `FastMCP("forge_bridge", instructions=…, lifespan=_lifespan)` constructor — still accepts these in 1.19+? (Spot-check: yes, `instructions` and `lifespan` are both present in 1.26.0's signature.)
- Any direct `FastMCP._tool_manager.list_tools()` internal use anywhere? (If yes, `_tool_manager` is a private API that has churned between 1.7 and 1.26; use only public `list_tools()` RPC or `mcp.list_tools()` coroutine.)
- The `mcp[cli]` extra has itself been reshuffled in 1.24 (2025-12-12 "transport-specific parameters moved from FastMCP constructor to run()"). Worth a CI smoke test.

### Alternatives considered (and rejected)

| Option | Why rejected |
|--------|-------------|
| Embed JSON-encoded provenance in `tool.description` | Description is model-facing free prose. Embedding `{"project": …, "code_hash": …}` in it pollutes the LLM's context window and is not a machine-readable API for other clients. |
| Use `ToolAnnotations` | Wrong slot — fixed schema, safety/behavior hints only, no freeform keys. |
| Ship a parallel MCP resource (`forge://synth/provenance/<name>`) | Doubles the surface area. Clients listing tools still wouldn't see provenance without a second round-trip. Keep resources for things that need URIs (e.g. the source code itself); keep small structured metadata in `_meta`. |
| Pin `mcp[cli]>=1.15` (first release with `_meta` on types) | `_meta` existed on the `Tool` type but the FastMCP decorator did not expose a `meta=` param until 1.19. Would force us into `mcp._tool_manager` internals or post-hoc mutation. |

### Confidence

**HIGH.** Verified against the 2025-06-18 spec text, the SDK changelog, and the installed `mcp==1.26.0` Pydantic models. Live-tested the `meta=` parameter roundtrip on this machine.

---

## `typing.Protocol` for `StoragePersistence` (EXT-03)

### Context

`ExecutionLog.set_storage_callback(fn)` (Phase 6-01, already shipped in v1.1.0) accepts a sync *or* async `Callable[[ExecutionRecord], Union[None, Awaitable[None]]]` and detects async-ness once via `inspect.iscoroutinefunction`. The callback is the storage seam. EXT-03 adds a `typing.Protocol` so consumers (projekt-forge, future adopters) have a name for the contract, not just a `Callable` type alias.

### Idiomatic pattern

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable

from forge_bridge.learning.execution_log import ExecutionRecord


@runtime_checkable
class StoragePersistence(Protocol):
    """Mirror ExecutionLog writes into durable storage.

    Implementations SHOULD be async (the callback is awaited on the
    bridge's event loop). Sync implementations are accepted by
    ExecutionLog.set_storage_callback() for backward compat, but
    async is the idiomatic shape for this protocol.

    Implementations MUST be side-effect-isolated — raising propagates
    to a WARNING log but never disrupts the canonical JSONL append
    (source-of-truth invariant, Phase 6-01).
    """

    async def __call__(self, record: ExecutionRecord) -> None: ...
```

### Why this shape

| Choice | Rationale |
|--------|-----------|
| **Structural (`Protocol`) not nominal (`ABC`)** | Consumer code (projekt-forge's `_persist_execution`) is already a bare async function today. Nominal inheritance would force it into a class. Structural typing captures the contract without forcing inheritance. |
| **`__call__` method (not a named method like `persist(...)`)** | Matches the existing `set_storage_callback(fn)` contract — `fn` is a plain callable, not an object with a named method. Lets consumers write `async def _persist_execution(record): ...` and pass the function directly. |
| **`@runtime_checkable` present but advisory** | Lets forge-bridge (or consumers) do an `isinstance(fn, StoragePersistence)` sanity check at registration time. **Caveat:** per PEP 544 and verified locally, `runtime_checkable` only checks for `__call__`'s *presence*, not whether it's async. A sync function still passes `isinstance(fn, StoragePersistence)`. `ExecutionLog` already does the sync/async disambiguation via `inspect.iscoroutinefunction`; the Protocol is for documentation + optional typing, not runtime enforcement. |
| **`ExecutionRecord` (frozen dataclass, already exists) as the arg type** | Already the shipped contract. The Protocol simply names the shape. |
| **No generic `TypeVar`** | Single concrete record type — don't over-engineer. |
| **Return `None` (not `None \| Awaitable[None]`)** | The async-only shape is what we *want* consumers to write. `ExecutionLog.set_storage_callback()` will still accept sync callbacks at runtime for backward compat, but the Protocol codifies the intended future form — async is how you do non-blocking I/O to a DB. |

### Python version compat

- **3.10 minimum (forge-bridge)**: `typing.Protocol` + `@runtime_checkable` have been stable stdlib since 3.8. Python 3.10 natively supports this pattern with no qualifications relevant to our case.
- **3.11 (projekt-forge)**: Same stdlib Protocol works identically. No behavior difference.
- **`typing_extensions`**: **Not needed.** The `typing_extensions` package provides Protocol performance improvements and bug fixes for Python <3.12, but they are optimizations — correctness on 3.10+ is fine without the backport. Adding a `typing_extensions` dependency for the sake of a single Protocol would be pure bloat.

### What `runtime_checkable` can and cannot do

Live-verified on Python 3.11:

```python
@runtime_checkable
class StoragePersistence(Protocol):
    async def __call__(self, record: ExecutionRecord) -> None: ...

async def good(r): ...
def bad_sync(r): return None

isinstance(good, StoragePersistence)      # True  ✓
isinstance(bad_sync, StoragePersistence)  # True  ✗ (false positive — sync passes)
isinstance(object(), StoragePersistence)  # False ✓ (no __call__)
```

Conclusion: **`isinstance(fn, StoragePersistence)` is useful for catching the "you passed a non-callable object" case at registration time. It cannot enforce async-ness.** `ExecutionLog.set_storage_callback` already handles the sync/async distinction via `inspect.iscoroutinefunction`; the Protocol is documentation, not enforcement.

### Where to put it

New module `forge_bridge/learning/persistence.py`:

```python
"""Public Protocol surface for durable storage backends."""
from __future__ import annotations
from typing import Protocol, runtime_checkable

from forge_bridge.learning.execution_log import ExecutionRecord

__all__ = ["StoragePersistence"]


@runtime_checkable
class StoragePersistence(Protocol):
    async def __call__(self, record: ExecutionRecord) -> None: ...
```

Re-exported from `forge_bridge/__init__.py` (pattern established in Phase 6-03 — v1.1.0 minor bump, barrel entry in `__all__`).

### Version pin impact

**None.** `typing.Protocol` is stdlib since 3.8; `@runtime_checkable` is stdlib since 3.8. forge-bridge is already 3.10+. No new dependency, no `typing_extensions` pin.

### Confidence

**HIGH.** PEP 544 verified, Python 3.10/3.11 behavior verified locally, existing `ExecutionLog` sync/async detection mechanism already aligns with the "Protocol is advisory, runtime detection is authoritative" pattern.

---

## Alembic chain strategy (EXT-03)

### Question restated

projekt-forge already has an Alembic migration tree for its own tables. EXT-03 adds a new table (`execution_log` or similar) for forge-bridge's `ExecutionRecord` payload. Where does that migration live — in forge-bridge (shipped with the package, layered as a separate chain) or in projekt-forge (one more revision on its existing chain)?

### What Alembic actually offers

Alembic supports three distinct mechanisms that sound similar but solve different problems:

| Mechanism | What it is | When to use |
|-----------|-----------|-------------|
| **Multiple heads** | Two revisions that share a parent; temporary state during branch work | Transient; typically resolved by `alembic merge` |
| **Branch labels** (`branch_labels=("forge_bridge",)`) | Named branch you can target via `forge_bridge@head` | When you want one Alembic config to manage multiple independent lineages sharing the same `alembic_version` table |
| **Multiple `version_locations`** (`path_sep`-separated dir list) | Alembic scans multiple directories for revision files | When revision files physically live in different packages |

The closest thing to "a library ships its own migration chain that a host app layers in" is **branch labels + multiple `version_locations`**, combined with an independent `base` revision for the library's subtree. The `alembic_version` table stores one row per head, so multiple independent chains coexist without colliding on version numbers.

Verified against the current Alembic changelog: `branch_labels` and `version_locations` have been stable since well before the 1.13 floor; current Alembic is 1.18.4 (2026-02-10); no breaking changes affecting this pattern between 1.13 → 1.18.

### Recommendation: **Single chain in projekt-forge**

Despite the multi-chain feature being available, **add the `execution_log` table as one more revision on projekt-forge's existing Alembic chain**. Do not ship migration files from forge-bridge.

Rationale:

1. **forge-bridge doesn't own the database.** forge-bridge defines the `StoragePersistence` Protocol and the `ExecutionRecord` shape — the *contract*. The schema, the engine URL, the migration cadence, the backup policy, and the alembic.ini all live in the consumer. Shipping migrations from forge-bridge would mean the bridge has an opinion on DDL it never owns at runtime.
2. **Single consumer today.** projekt-forge is the only consumer. "Layered migration chains for pluggable library schemas" is a real pattern, but it pays off when *multiple* independent consumers need the same table. We have one. Build for the problem we have.
3. **Recovery is cheaper with a single chain.** When projekt-forge dev wants to rebase, squash, or reset migrations during active development, they don't need to coordinate with a separate library-owned chain. One `alembic upgrade head` does everything.
4. **Reversibility.** If EXT-01 (shared synthesis manifest) ever comes back from the deferred list and we discover *multiple* consumers want the same schema, we can lift the table definition out of projekt-forge into a forge-bridge SQLAlchemy model module and start shipping migrations from the bridge. That's a real project but the v1.1 architecture doesn't prevent it — the Protocol contract is the stable surface, the schema migration story is an implementation detail that can move.
5. **forge-bridge's existing deps (`sqlalchemy[asyncio]>=2.0`, `alembic>=1.13`, `asyncpg>=0.29`, `psycopg2-binary>=2.9`) are already carried** from v1.0 when the bridge itself had a PostgreSQL backend. EXT-03 does not *add* any new DB deps to forge-bridge. It consumes the existing ones only if forge-bridge later needs to define SQLAlchemy models for convenience (e.g. a `declarative_base` that projekt-forge imports). Even this is optional — projekt-forge can define its own `ExecutionLogRow` ORM class matching `ExecutionRecord`'s shape.

### What forge-bridge DOES ship for EXT-03

- `forge_bridge.learning.persistence.StoragePersistence` — the `Protocol`.
- (Optional, nice-to-have) `forge_bridge.learning.persistence.ExecutionLogMixin` — a SQLAlchemy declarative mixin with typed columns matching `ExecutionRecord` fields (`code_hash: Mapped[str]`, `raw_code: Mapped[str]`, `intent: Mapped[str | None]`, `timestamp: Mapped[datetime]`, `promoted: Mapped[bool]`), so projekt-forge can do:

  ```python
  class ExecutionLogRow(Base, ExecutionLogMixin):
      __tablename__ = "execution_log"
      id: Mapped[int] = mapped_column(primary_key=True)
  ```

  Whether to ship the mixin is a planning-phase decision. It couples the package to SQLAlchemy's ORM API, not just Core. The upside is consumers never drift from the dataclass schema.

### What projekt-forge owns

- The `alembic.ini`, `migrations/versions/` tree, and the new `YYYYMMDD_add_execution_log.py` revision file.
- The `ExecutionLogRow` ORM class (or Core `Table` definition).
- The `async def _persist_execution(record: ExecutionRecord) -> None:` implementation that opens a session, constructs the row, and commits — replacing the v1.1 logger-only stub.
- The `StoragePersistence` isinstance check at registration: `assert isinstance(_persist_execution, StoragePersistence)` — catches regressions where the callback's signature drifts from the Protocol.

### Version pins

**No change to forge-bridge's alembic / sqlalchemy / asyncpg pins.** All EXT-03 DDL lives in projekt-forge; projekt-forge's own pins already carry `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `alembic`.

### Confidence

**HIGH** on recommendation. **MEDIUM** on the ExecutionLogMixin question — that's a planning-phase judgment call that depends on how much schema drift we're willing to tolerate between the dataclass and the DB row.

---

## Summary of pin changes

| File | Current | Proposed | Reason |
|------|---------|----------|--------|
| `pyproject.toml` `dependencies` | `mcp[cli]>=1.0` | `mcp[cli]>=1.19,<2` | `meta=` param on `FastMCP.tool()` landed in 1.19 (EXT-02 precondition); avoid accidental v2 upgrade (`FastMCP → MCPServer` rename on `main`) |
| (no other dep changes) | — | — | EXT-03 Protocol is pure stdlib; Alembic work lands in projekt-forge |

**No new dependencies added to forge-bridge.**

---

## Open questions for planning phase

1. **Should EXT-02 attach provenance at synthesis time or at registration time?**
   Today `SkillSynthesizer` writes `*.py` + `*.tags.json`; the MCP registry (`forge_bridge.learning.watcher`) separately imports the `.py` and calls `mcp.tool()(fn)`. The `meta=` has to be supplied to the decorator at registration. Does the watcher read the adjacent `.tags.json` and pass a `meta={...}` derived from it, or does the synthesizer stash a `__forge_meta__` attribute on the function itself that the watcher harvests? Either works; a planning decision, not a research decision.

2. **Does EXT-02 also want `title=` and `description=` from the tags sidecar?**
   The spec splits display title (`title`) from machine description (`description`). Our sidecar has `tags` and (via `PreSynthesisContext`) potentially `intent`. We could map `intent` → `title`, the function's docstring → `description`, and shove everything else into `meta`. Not a research gap, a UX decision.

3. **Should we add `ToolAnnotations(readOnlyHint=..., destructiveHint=...)` alongside `_meta`?**
   Synthesized tools from `SkillSynthesizer` have a safety blocklist (`_DANGEROUS_CALLS`) — by construction, none of them should be `destructiveHint=True`. A mechanical `readOnlyHint=False, destructiveHint=False` baseline for all synthesized tools would be honest and low-effort. Worth a Phase 7 plan task.

4. **ExecutionLogMixin — ship or defer?**
   See Alembic section. HIGH confidence on "single chain in projekt-forge"; MEDIUM on whether forge-bridge should also ship a SQLAlchemy mixin for schema-drift prevention. Defer to planning phase.

5. **`typing_extensions` pin — really not needed?**
   Double-checked: PEP 544 features used (`Protocol`, `@runtime_checkable`, async `__call__`) have been stable stdlib since 3.8. No `typing_extensions` required. Flagging this as "researched and confirmed negative" so the planning phase doesn't re-ask.

6. **Does projekt-forge's existing `ExecutionRecord` type hint need updating once `StoragePersistence` lands?**
   projekt-forge currently imports `ExecutionRecord` from `forge_bridge` directly (barrel re-export from v1.1.0). It should additionally import `StoragePersistence` and annotate `_persist_execution` with it. Planning item, not research.

---

## Sources

- MCP spec (2025-06-18): https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP concepts — Tools: https://modelcontextprotocol.io/docs/concepts/tools
- mcp Python SDK releases: https://github.com/modelcontextprotocol/python-sdk/releases
- mcp Python SDK PR #1463 "add tool metadata in FastMCP.tool decorator" (v1.19.0, Oct 2025)
- mcp Python SDK PR #482 "Add ToolAnnotations support in FastMCP and lowlevel servers" (v1.7.0, Apr 2025)
- mcp Python SDK PR #1357 "SEP 973 — Additional metadata + icons support" (v1.15.0, Sep 2025)
- PyPI — mcp 1.27.0 current as of 2026-04-02: https://pypi.org/project/mcp/
- PEP 544 — Protocols: https://peps.python.org/pep-0544/
- Python 3.10 `typing` docs (Protocol + runtime_checkable): https://docs.python.org/3.10/library/typing.html
- typing_extensions changelog: https://github.com/python/typing_extensions/blob/main/CHANGELOG.md (confirms backports are perf/fixes, not correctness for our pattern)
- Alembic Branches and Multiple Heads: https://alembic.sqlalchemy.org/en/latest/branches.html
- Alembic Tutorial — version_locations: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Local verification: `mcp==1.26.0` on Python 3.11.x, inspected via `Tool.model_fields` and `FastMCP.tool` signature; `Protocol` + `runtime_checkable` async `__call__` isinstance behavior
