# Architecture Research — v1.2 Observability & Provenance

**Research mode:** Architecture (subsequent milestone, v1.2 scope)
**Overall confidence:** HIGH — integration points map directly to existing forge-bridge modules and v1.1 non-goals are respected.

## EXT-02 integration points

### Files changed

| File | New/Modified | Symbols touched | Reason |
|------|--------------|-----------------|--------|
| `forge_bridge/learning/watcher.py` | **Modified** | `_scan_once`, (new) `_read_sidecar` | Sidecar is co-located with `synth_*.py`; watcher owns the load path and is the natural place to read it |
| `forge_bridge/mcp/registry.py` | **Modified** | `register_tool` (new internal `provenance` kwarg) | Pass-through only — already accepts `annotations` and already sets `meta={"_source": source}` |
| `forge_bridge/learning/synthesizer.py` | **Modified (tiny)** | sidecar schema bump: `.tags.json` → `.sidecar.json` with `schema_version: 1`; WR-02 docstring fix on `ExecutionRecord` | Sidecar schema evolution + code-review hygiene |
| `tests/learning/test_watcher_sidecar.py` | **New** | — | Covers: sidecar present → annotation attached; sidecar missing → tool still registers; malformed sidecar → warning + register without annotation |
| `tests/mcp/test_registry_provenance.py` | **New** | — | Covers: consumer-supplied `annotations` merges with sidecar tags; source-tag preserved |
| `README.md` | **Modified** | conda-env section | Bundled in as a Phase 7 polish task (deferred item in v1.1-ROADMAP) |
| `forge_bridge/__init__.py` | **Not modified** | — | No new public symbols for EXT-02; annotations are transport-level, not API |

### API surface impact

- **`__all__` does NOT change for EXT-02.** Provenance is conveyed over the MCP wire via tool annotations — consumers read it via the MCP client, not via a Python import. The 15-name barrel is stable at v1.1.0 and should stay stable for EXT-02.
- **`register_tools(mcp, fns, prefix="", source="user-taught")` does NOT change signature.** No new kwargs. The sidecar path is entirely internal to `watcher._scan_once` → `registry.register_tool` (the singular form), which is not in `__all__` and is not a consumer-facing API.
- **`register_tool` (internal) grows one kwarg:** `provenance: dict | None = None`. This is the only place where a signature grows.

### Recommended wiring — Option (b′), with refinement

The prompt offered three options. **Pick (b) but with a twist: watcher reads the sidecar and passes an annotations/provenance dict to `register_tool`, not a function attribute.**

Concretely, in `watcher._scan_once` the existing call at `watcher.py:91`:

```python
register_tool(mcp, fn, name=stem, source="synthesized")
```

becomes:

```python
provenance = _read_sidecar(path)   # None if no sidecar / malformed
register_tool(mcp, fn, name=stem, source="synthesized", provenance=provenance)
```

where `_read_sidecar(path)` reads `path.with_suffix(".sidecar.json")` (or legacy `.tags.json` for backward-compat), returns `{"tags": [...], "meta": {...}}` or `None`.

**Why this path is best:**

1. **Zero public-API change.** `register_tool`'s internal surface grows one kwarg; `register_tools` (public) is untouched. Blast radius = two internal modules.
2. **Sidecar discovery stays co-located with file discovery.** The watcher already does `path.stem`, `manifest_verify(path)`, `_sha256(path)`, and `importlib.util.spec_from_file_location(stem, path)` — reading one more neighbour file is the idiomatic extension of that loop.
3. **Function-object attributes (option b as stated) are a dead end.** `mcp.add_tool(fn, ...)` inspects the function for its signature/docstring, not for `fn.__forge_metadata__`. Adding such an attribute would be invisible to FastMCP unless we also modify `register_tool` to read and forward it — strictly more indirection than just forwarding the dict.
4. **Option (c) — `register_tool` grows sidecar discovery — leaks filesystem concerns into a pure-registration function.** `register_tool` is currently stateless and path-agnostic (called for builtins, synthesized, and user-taught tools). Teaching it to probe the filesystem for sidecars couples it to the synthesis pipeline. Rejected.
5. **Option (a) — API addition — violates the 15-symbol barrel discipline.** Rejected.

### Where the metadata lands on the wire

`ToolAnnotations` (Pydantic) has `extra='allow'`, so we *could* stuff `tags` into `annotations`. **But do not.** The MCP spec defines a bounded set of hints (`title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`); consumer-defined keys in `annotations` will be confusing to MCP clients that follow the spec literally. The right place is the already-in-use **`meta` dict**, which is exactly the bag that `registry.register_tool` currently uses for `{"_source": source}`. Recommendation:

```python
# Inside register_tool(), if provenance kwarg present:
meta = {"_source": source}
if provenance:
    meta["_tags"] = provenance.get("tags", [])
    meta["_synthesized_at"] = provenance.get("meta", {}).get("synthesized_at")
    meta["_source_hash"] = provenance.get("meta", {}).get("source_hash")
    # Additional forge.bridge.* keys per FEATURES.md TS-02.2
mcp.add_tool(fn, name=name, annotations=annotations, meta=meta)
```

### Non-synthesized tools (builtin / user-taught) — no placeholder sidecar

Builtin tools have no `.sidecar.json` (they are not produced by `SkillSynthesizer.synthesize`). The correct behaviour is: **if no sidecar exists, do not add provenance fields to `meta`**. The `_source` tag already distinguishes builtins. Writing placeholder sidecars for builtins would duplicate information already carried by `_source` and blur the "sidecar == synthesis artifact" contract.

### Migration concern: existing sidecars on disk

Phase 6-02 shipped the sidecar-write path as `.tags.json`. Phase 7-01 should rename to `.sidecar.json` with the schema_version bump. Migration strategy:
- **Watcher reads both** for a grace period: prefer `.sidecar.json`, fall back to `.tags.json`.
- **Synthesizer writes only** `.sidecar.json` from v1.2.0 onwards.
- A one-shot migration script (`forge-ctl migrate sidecars`) can batch-convert old `.tags.json` on disk if desired, but it's optional because the watcher handles both.

## EXT-03 integration points

### Where `StoragePersistence` Protocol lives

**Definitive recommendation: define it in `forge_bridge/learning/storage.py` (new module, forge-bridge side).**

Rationale:

1. **The callback contract is already in forge-bridge** (`StorageCallback = Callable[[ExecutionRecord], Union[None, Awaitable[None]]]`, exported at the barrel). A `Protocol` is a typed evolution of that contract — it belongs next to the thing it types.
2. **`ExecutionRecord` is in forge-bridge** and locked by D-03. Any Protocol describing "how to persist an `ExecutionRecord`" has to import it; keeping both in-package avoids projekt-forge needing to re-export forge-bridge types.
3. **Swappable backends are a forge-bridge concern, not a projekt-forge one.** A SQLAlchemy backend, an in-memory test backend, and a no-op logger stub (like `_persist_execution` today) are all valid. The Protocol describes the shape; implementations live wherever the consumer wants (projekt-forge has the SQLAlchemy impl; a future Redis-backed impl could live anywhere).
4. **Pre-1.0 philosophy extended into v1.2**: the barrel already exports `StorageCallback`; adding a sibling `StoragePersistence` to the same module and re-exporting it at the barrel is the minor-version-bump-ceremony pattern established at v1.1.0.

### `ExecutionLog.set_storage_callback` signature — stays as-is

**Do not change the signature.** The Protocol is *documentation of the expected shape*, not a replacement type. Three reasons:

1. **Backwards compatibility with the v1.1.0 API.** `set_storage_callback(fn)` where `fn` is a bare callable is the locked contract. projekt-forge's `init_learning_pipeline` registers `_persist_execution` (a bare async function). Changing the signature to require a `StoragePersistence` instance would break that call site and force a coupled release.
2. **A `StoragePersistence` instance naturally adapts to a callable.** The Protocol defines `async def persist(self, record: ExecutionRecord) -> None`. Consumers pass `backend.persist` (bound method — a `StorageCallback`). Either way, the existing `set_storage_callback` accepts it without change.
3. **Per-instance sync/async detection still works.** `inspect.iscoroutinefunction(backend.persist)` returns `True` for an `async def persist`, which is exactly what the existing code at `execution_log.py:141` already does.

### Shape of the Protocol

```python
# forge_bridge/learning/storage.py
from typing import Protocol, Sequence, runtime_checkable
from forge_bridge.learning.execution_log import ExecutionRecord

@runtime_checkable
class StoragePersistence(Protocol):
    """Pluggable backend that mirrors ExecutionRecords into durable storage.

    The JSONL log is source-of-truth; Protocol implementations are a
    best-effort mirror. A raising persist() MUST NOT disrupt the JSONL
    append (ExecutionLog catches and logs at WARNING).
    """

    async def persist(self, record: ExecutionRecord) -> None: ...
    async def persist_batch(self, records: Sequence[ExecutionRecord]) -> None: ...
    async def shutdown(self) -> None: ...
```

Consumer in projekt-forge binds it:

```python
# projekt_forge/learning/wiring.py
from projekt_forge.learning.sql_persistence import SQLAlchemyPersistence
backend = SQLAlchemyPersistence(session_factory=get_session_factory())
execution_log.set_storage_callback(backend.persist)   # existing API
```

### Package-tree changes

```
forge_bridge/
  learning/
    execution_log.py     (existing — no change to public surface)
    manifest.py          (existing)
    probation.py         (existing)
    synthesizer.py       (existing — sidecar schema bump only)
    watcher.py           (modified: sidecar reader)
    storage.py           (NEW: StoragePersistence Protocol)
  __init__.py            (modified: re-export StoragePersistence; __all__ 15 → 16)
```

**`__all__` grows by exactly 1**: `"StoragePersistence"`. Same minor-version ceremony as v1.1.0.

## Cross-cutting / build order

### Phase 7 (EXT-02) before Phase 8 (EXT-03) — recommended

**Reasoning:**

1. **EXT-02 is a smaller change with no consumer-side implementation dependency.** The sidecar-to-annotation path lives entirely in forge-bridge (watcher, registry). No projekt-forge PR is required to verify it.
2. **EXT-03 requires a projekt-forge implementation to validate end-to-end.** The `StoragePersistence` Protocol on its own is untestable beyond type-check and contract tests; the real SC ("execution appears in SQL") needs projekt-forge's SQLAlchemy backend. Phase 5's hard-earned lesson was: two-repo phases are expensive.
3. **EXT-02 surfaces what metadata is worth persisting.** If EXT-02 ships first and projekt-forge's MCP clients start consuming `_tags` / `_source_hash` via the MCP wire, the EXT-03 schema design gets a concrete signal: "persist what the annotations promise." If EXT-03 ships first, you pick a schema in the dark.

### Parallelizable? — No

Two structural overlap risks:

1. **Both phases touch `forge_bridge/__init__.py` `__all__`.** A parallel merge would race on the barrel. This creates ceremony conflicts (both phases want to cut a version tag that grows `__all__`).
2. **EXT-03 may want to consume `ExecutionRecord` fields that EXT-02 inspires adding.** Concrete example: if during EXT-02 the team decides `ExecutionRecord` should carry a `tool_name: Optional[str]` (filled when the execution was routed through a synthesized tool), that's a D-03-locked change. Running in parallel risks committing a schema that misses the new field.

**If the team really wants parallelism:** freeze `ExecutionRecord` at v1.1.0 shape for v1.2 (no new fields) and accept that EXT-03's schema may need a v1.3 migration. This is a real option but not recommended — the low-friction sequential path is faster in total wall-clock time.

### Does EXT-03 need additional provenance work after EXT-02?

**No**, if `ExecutionRecord` remains the wire-format for both features. If EXT-03's SQL schema mirrors `ExecutionRecord`'s five fields exactly, the answer is yes — EXT-02 requires no provenance work in EXT-03. If the SQL schema wants to **join** "executions that caused synthesis" to "synthesized tool provenance," that's a design choice, not a dependency.

**Recommendation:** keep EXT-03's v1.2 schema strictly mirroring `ExecutionRecord` — one row per execution, no join to synthesis provenance. A future v1.3 can add the join if the data proves interesting.

### Dependencies on Phase 6 artifacts

| Artifact | Produced by | Consumed by |
|----------|-------------|-------------|
| `.tags.json` sidecar write path | Phase 6-02 (synthesizer.py:369-371) | EXT-02 (watcher reads them; schema bumped to `.sidecar.json`) |
| `ExecutionRecord` frozen dataclass | Phase 6-01 (execution_log.py:33) | EXT-03 (Protocol types it) |
| `StorageCallback` type alias | Phase 6-01 (execution_log.py:49) | EXT-03 (Protocol evolves it) |
| `set_storage_callback` dispatch | Phase 6-01 (execution_log.py:117) | EXT-03 (unchanged) |
| `pre_synthesis_hook` → `ctx.tags` | Phase 6-02 | EXT-02 (indirect: sidecar content source) |
| projekt-forge `_persist_execution` stub | Phase 6-04 (wiring.py:100) | EXT-03 replaces body with SQL write |

All inputs are stable and locked at v1.1.0. No re-work of Phase 6 is needed for v1.2.

## Non-goals check

| v1.1 non-goal | Intersection with v1.2 | Status |
|---|---|---|
| No LLMRouter hot-reload | Neither EXT-02 nor EXT-03 touches router wiring | ✓ Safe |
| No shared-path JSONL writers | EXT-02 touches MCP registration (no JSONL writer). EXT-03 persists to SQL outside JSONL path. | ✓ Safe — but Phase 8 SC tests must assert no second writer to the JSONL path |

## Summary for the roadmapper

- **EXT-02 modules touched:** `forge_bridge/learning/watcher.py` (sidecar read), `forge_bridge/mcp/registry.py` (internal `provenance` kwarg on `register_tool`), `forge_bridge/learning/synthesizer.py` (sidecar schema bump + WR-02 docstring). Three production-code files, two new test files, one README polish.
- **`register_tools()` signature:** **unchanged**. `register_tool` (singular, internal) grows one internal-only kwarg.
- **`StoragePersistence` location:** **forge-bridge** (`forge_bridge/learning/storage.py` — new module, re-exported from barrel; `__all__` grows 15 → 16).
- **`set_storage_callback` signature:** **unchanged**. Protocol is documentation; consumers pass `backend.persist` bound methods as the existing callable.
- **Build order:** **Phase 7 → Phase 8, strictly sequential.** Not parallelizable — shared barrel edits + potential `ExecutionRecord` evolution make concurrent landing risky.
- **Non-goals respected:** ✓ both features.
