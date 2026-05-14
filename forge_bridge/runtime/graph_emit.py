"""Minimal append-only graph-event emission — Phase 24 substrate.

Phase 24 ships proto-node emission against the smallest possible substrate.
Records are observability artifacts FIRST, runtime primitives LATER.

Schema (six required fields, payload-extensible). Refined toward
observability-first at implementation contact per operator direction
2026-05-14 — flat event records with shared correlation ID
(OpenTelemetry-shape), NOT tree-reconstruction primitives.

    {
        "event_id":  "<uuid4-hex>",      # unique per record
        "graph_id":  "<uuid4-hex>",      # groups records into one logical session/chain
        "node_kind": "<string>",         # kind of substrate producing the event
        "timestamp": "<ISO-8601-UTC>",   # millisecond precision, trailing Z
        "status":    "<string>",         # producer-conventional (e.g. created/started/completed/failed)
        "payload":   {...}               # kind-specific opaque blob; extensible
    }

Storage: ``~/.forge-bridge/graphs/<graph_id>.jsonl``, append-only, one
record per line. Path convention matches ``runtime.manager``'s
``~/.forge-bridge/runtime.json`` and the learning pipeline's
``~/.forge-bridge/executions.jsonl``. Override via ``FORGE_GRAPH_DIR``.

Status conventions are intentionally NOT enforced at the substrate.
Producer surfaces (Phase 24 ships ``flame_execute_python`` in the next
commit) establish conventions through use; substrate stays generic
until conventions stabilize. Per
``.planning/milestones/v1.6-PHASE-24-CONVERGENCE.md`` §6:
intentional deferral, not implicit rejection.

What this module is NOT:

- Not a graph executor.
- Not a graph reconstruction helper.
- Not a replay engine.
- Not a type registry.
- Not a runtime primitive that downstream code depends on for execution.

These are deferred per ``v1.6-PHASE-24-CONVERGENCE.md`` §3 anti-scope.
The runtime must emit truth before designing around imagined future
complexity.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = ["new_graph_id", "emit_event", "graph_dir"]

_GRAPH_DIR_ENV = "FORGE_GRAPH_DIR"


def graph_dir() -> Path:
    """Return the directory where per-graph JSONL files live.

    Honors ``FORGE_GRAPH_DIR`` env var (for tests + non-default deployments).
    Defaults to ``~/.forge-bridge/graphs/``.
    """
    override = os.environ.get(_GRAPH_DIR_ENV)
    if override:
        return Path(override)
    return Path.home() / ".forge-bridge" / "graphs"


def new_graph_id() -> str:
    """Generate a new graph_id.

    Caller persists this for the duration of the session/chain it represents.
    Phase 24 substrate does not track graph lifetime — that lives in the caller.
    """
    return uuid.uuid4().hex


def emit_event(
    *,
    graph_id: str,
    node_kind: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Emit one graph event to the append-only JSONL stream for ``graph_id``.

    Returns the generated ``event_id`` so callers can correlate downstream
    log lines or audit traces against the emitted record.

    The function is append-only and idempotent at the substrate: re-calling
    with the same arguments produces another record (with a fresh event_id +
    timestamp). Deduplication, if needed, is producer-surface responsibility.

    Concurrency: JSONL append on POSIX is atomic per ``write()`` call for
    single-line writes under PIPE_BUF size. Phase 24 emits from a single
    producer (``flame_execute_python``); multi-surface concurrency lands as
    a separate convergence (``v1.6-FRAMING.md`` §12.2.8).
    """
    event_id = uuid.uuid4().hex
    timestamp = (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    record = {
        "event_id": event_id,
        "graph_id": graph_id,
        "node_kind": node_kind,
        "timestamp": timestamp,
        "status": status,
        "payload": payload if payload is not None else {},
    }
    target_dir = graph_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{graph_id}.jsonl"
    line = json.dumps(record, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
    return event_id
