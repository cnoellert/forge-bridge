"""In-memory synthesis manifest service for the v1.3 Artist Console.

The ManifestService singleton owns a `dict[str, ToolRecord]` keyed by tool name.
It is the single source of truth for:
  - Web UI manifest browser (Phase 10)
  - CLI `forge-bridge console manifest` (Phase 11)
  - MCP resource `forge://manifest/synthesis` (Plan 09-03)
  - MCP tool fallback shim `forge_manifest_read` (Plan 09-03)
  - projekt-forge (MFST-06) -- consumed via MCP resource or HTTP API

Consistency model
-----------------
The synthesized-tool WATCHER (forge_bridge/learning/watcher.py) is the SOLE
writer: after every successful `register_tool(mcp, ..., source="synthesized")`,
it calls `await manifest_service.register(ToolRecord(...))`. Similarly,
file-deletion removes from both the MCP registry and the manifest.

The CONSOLE READ API (forge_bridge/console/read_api.py) is the SOLE reader on
the console surface -- no handler, resource, or MCP tool shim ever reads
`_tools` directly.

An `asyncio.Lock` serializes writes (register/remove). Reads are lockless --
dict lookup is atomic in CPython (GIL), and the immutable ToolRecord shape
means callers never see a half-constructed record.

This pattern mirrors the LRN-02/LRN-05 lesson from Phase 6/8: one writer +
one reader + an instance-identity gate prevents dead-seam drift.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolRecord:
    """Canonical tool provenance record shared across all read surfaces.

    Matches the shape the watcher captures from `.sidecar.json` + register_tool
    kwargs. snake_case end-to-end per D-04. Frozen so callers cannot mutate
    state shared across the write/read seats.

    tags and meta use tuple types because frozen dataclass fields must be
    hashable; mutable list/dict would trigger `TypeError: unhashable type`
    in any downstream set/dict membership check.
    """

    name: str
    origin: str                         # "builtin" | "synthesized"
    namespace: str                      # "flame" | "forge" | "synth"
    synthesized_at: Optional[str] = None
    code_hash: Optional[str] = None
    version: Optional[str] = None
    observation_count: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    meta: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    # Bug C — Backend reachability annotation (computed at read time, never
    # persisted). None means "not yet annotated" (e.g. fresh from the watcher);
    # True/False are set by ConsoleReadAPI.get_tools() via the existing
    # _tool_filter probe. ManifestService writers leave this at None and
    # callers compute the value from live backend state.
    available: Optional[bool] = None

    def __post_init__(self) -> None:
        # Fail fast on list/dict -- frozen dataclass silently accepts them
        # but downstream hashing breaks. Explicit runtime guard.
        if not isinstance(self.tags, tuple):
            raise TypeError(
                f"ToolRecord.tags must be a tuple, got {type(self.tags).__name__}"
            )
        if not isinstance(self.meta, tuple):
            raise TypeError(
                f"ToolRecord.meta must be a tuple of (key, value) tuples, "
                f"got {type(self.meta).__name__}"
            )

    def to_dict(self) -> dict:
        """Return a plain dict (serializer-ready).

        `tags` becomes a list and `meta` becomes a dict -- JSON serialization
        does not support tuples in any meaningful way, and the HTTP/MCP
        envelopes (D-26) expect list/dict on the wire.
        """
        d = asdict(self)
        # Convert tuples to wire-friendly shapes at the serialization boundary
        d["tags"] = list(self.tags)
        d["meta"] = dict(self.meta)
        return d


class ManifestService:
    """Async-safe in-memory registry of ToolRecord by name.

    Sole writer: the synthesized-tool watcher.
    Sole reader (on the console surface): ConsoleReadAPI.

    All mutating methods are `async def` + `asyncio.Lock`-guarded. Reads are
    sync and lockless (atomic dict lookup + immutable ToolRecord).
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolRecord] = {}
        self._lock = asyncio.Lock()

    async def register(self, record: ToolRecord) -> None:
        """Insert or replace a ToolRecord by `record.name`."""
        async with self._lock:
            self._tools[record.name] = record

    async def remove(self, name: str) -> None:
        """Drop a record by name. No-op if the name is not present."""
        async with self._lock:
            self._tools.pop(name, None)

    def get(self, name: str) -> Optional[ToolRecord]:
        """Return a ToolRecord by name, or None. Lockless read."""
        return self._tools.get(name)

    def get_all(self) -> list[ToolRecord]:
        """Return every ToolRecord in insertion order as a shallow copy.

        The returned list is freshly materialized -- callers may iterate,
        slice, or sort it freely without affecting internal state.
        """
        return list(self._tools.values())
