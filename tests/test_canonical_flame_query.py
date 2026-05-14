"""Canonical regression invariants for Flame introspection convergence.

Phase 24 Commit 3 — formalize the canonical operational regression as
shared substrate. Three invariants pinned against the producer
(``flame_execute_python``) with mocked Flame execution. Live Flame is
NOT required; the author-walk against real Flame remains a separate
operational gate.

The three invariants prove three distinct substrate properties:

  1. Graph correlation — runtime coherence (events from one request
     share one graph_id).
  2. Event lifecycle shape — append-only observability semantics
     (every started has a terminal; no orphans).
  3. Substrate kind correctness — runtime legitimacy at the
     substrate layer (node_kind names the execution kind, not the
     MCP tool surface).

What this file does NOT do (deliberately, per
`.planning/milestones/v1.6-PHASE-24-CONVERGENCE.md` §3 anti-scope):

  - No chat-handler exercises. The chat-layer escalation to
    `flame_execute_python` is a separate concern; author-walks +
    eventual live-Flame CI smoke own that gate.
  - No semantic output assertions (no "the model answered correctly").
    The legitimacy test is "the runtime selected the correct
    execution substrate," not "the answer was right."
  - No graph reconstruction, replay logic, or executor semantics.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from forge_bridge.tools import utility
from forge_bridge.tools.utility import execute_python
from tests.fixtures.canonical_queries import (
    CANONICAL_FLAME_INTROSPECTION_PYTHON,
    CANONICAL_FLAME_INTROSPECTION_QUERY,
)


# ── Fixture sanity (cheap drift detector) ────────────────────────────────


def test_canonical_query_string_is_verbatim_stable() -> None:
    """The fixture's natural-language string is canonical. If a future
    cleanup paraphrases or normalizes it, downstream consumers (author-
    walks, future CI smoke, fixture references in seeds) silently break.
    Pin the exact value here."""
    assert CANONICAL_FLAME_INTROSPECTION_QUERY == "What are the clips on Reel 1"


def test_canonical_python_references_target_reel() -> None:
    """The synthesized Python must reference 'Reel 1' (the substrate
    concept the natural-language query names) and `flame.project` (the
    introspection surface). Light sanity, not behavioral assertion."""
    assert "Reel 1" in CANONICAL_FLAME_INTROSPECTION_PYTHON
    assert "flame.project" in CANONICAL_FLAME_INTROSPECTION_PYTHON


# ── Helpers ──────────────────────────────────────────────────────────────


class _FakeBridgeResponse:
    """Mimic ``forge_bridge.bridge.BridgeResponse`` for the success path.

    Mirrors the helper in ``test_flame_execute_python.py``. Kept local
    here so this file stays self-sufficient as a regression substrate;
    duplication is intentional (the canonical regression fixture should
    not depend on test-suite-internal helper paths)."""
    def __init__(self, stdout="", stderr="", result=None, error=None, traceback=None):
        self.stdout = stdout
        self.stderr = stderr
        self.result = result
        self.error = error
        self.traceback = traceback


def _read_jsonl_records(jsonl_path):
    return [json.loads(line) for line in jsonl_path.read_text().splitlines()]


def _exec_canonical_under_mock(monkeypatch, tmp_path, *, response=None, raises=None):
    """Exercise execute_python with the canonical synthesized Python
    against a mocked bridge. Returns the list of emitted JSONL records."""
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))

    if raises is not None:
        mock = AsyncMock(side_effect=raises)
    else:
        mock = AsyncMock(
            return_value=response if response is not None
            else _FakeBridgeResponse(stdout='{"reel": "Reel 1", "clips": []}'),
        )

    async def _run():
        if raises is not None:
            with pytest.raises(type(raises)):
                await execute_python(code=CANONICAL_FLAME_INTROSPECTION_PYTHON)
        else:
            await execute_python(code=CANONICAL_FLAME_INTROSPECTION_PYTHON)

    import asyncio
    with patch.object(utility.bridge, "execute", new=mock):
        asyncio.run(_run())

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1, "canonical regression assumes one-graph-per-call"
    return _read_jsonl_records(files[0])


# ── Invariant 1: graph correlation ───────────────────────────────────────


def test_invariant_1_graph_correlation_all_events_share_one_graph_id(
    monkeypatch, tmp_path,
):
    """Every event emitted during one canonical-query execution shares a
    single graph_id. This is the first real runtime coherence proof —
    without it, events are observability noise; with it, they form a
    coherent operational trace."""
    records = _exec_canonical_under_mock(monkeypatch, tmp_path)
    assert len(records) >= 2, "canonical regression emits at minimum started + terminal"
    graph_ids = {r["graph_id"] for r in records}
    assert len(graph_ids) == 1, (
        f"canonical regression must produce coherent graph; "
        f"saw {len(graph_ids)} distinct graph_ids: {graph_ids}"
    )
    # The JSONL filename is the shared graph_id — confirms substrate path
    # convention (~/.forge-bridge/graphs/<graph_id>.jsonl) is honored.
    only_gid = next(iter(graph_ids))
    files = list(tmp_path.glob("*.jsonl"))
    assert files[0].name == f"{only_gid}.jsonl"


# ── Invariant 2: event lifecycle shape ───────────────────────────────────


def test_invariant_2_lifecycle_shape_started_and_terminal_no_orphans_success(
    monkeypatch, tmp_path,
):
    """Successful canonical-query execution emits exactly one `started`
    and exactly one terminal record (here: `ok`). No orphan starts.
    No terminal-only records. This proves append-only observability
    semantics: every operation has a documented beginning AND end."""
    records = _exec_canonical_under_mock(monkeypatch, tmp_path)
    started_records = [r for r in records if r["status"] == "started"]
    terminal_records = [
        r for r in records if r["status"] in {"ok", "flame_error", "transport_error"}
    ]
    assert len(started_records) == 1, (
        f"exactly one `started` record expected; saw {len(started_records)}"
    )
    assert len(terminal_records) == 1, (
        f"exactly one terminal record expected; saw {len(terminal_records)}"
    )
    # No mystery statuses outside the declared lifecycle:
    assert len(records) == len(started_records) + len(terminal_records), (
        f"unexpected non-lifecycle records: "
        f"{[r['status'] for r in records]}"
    )


def test_invariant_2_lifecycle_shape_holds_under_transport_error(
    monkeypatch, tmp_path,
):
    """If bridge.execute raises (transport-layer failure), the lifecycle
    still emits both events — the `started` from entry, plus a terminal
    `transport_error` from the finally block. No orphan starts even on
    failure; the substrate stays append-only coherent under errors."""
    records = _exec_canonical_under_mock(
        monkeypatch, tmp_path,
        raises=RuntimeError("simulated transport failure"),
    )
    statuses = [r["status"] for r in records]
    assert statuses == ["started", "transport_error"]


# ── Invariant 3: substrate kind correctness ──────────────────────────────


def test_invariant_3_node_kind_is_substrate_python_not_tool_name(
    monkeypatch, tmp_path,
):
    """Every emitted record's node_kind is ``"python"`` — substrate-level
    execution identity, NOT the MCP tool name. This is the actual
    legitimacy proof: the runtime selected the correct execution
    substrate.

    A future maya_execute_python would emit node_kind="python" too
    (same substrate, different transport); a future flame_run_batch
    would emit node_kind="batch_run" (different substrate). The
    closed enumeration in v1.6-FRAMING.md §4 holds at the substrate
    layer.

    If this test ever fails with node_kind="flame_execute_python", the
    substrate/surface boundary has collapsed — see Commit 2.5 archaeology
    (commit b66ceef) for the reasoning."""
    records = _exec_canonical_under_mock(monkeypatch, tmp_path)
    kinds = {r["node_kind"] for r in records}
    assert kinds == {"python"}, (
        f"substrate-level node_kind expected; saw {kinds}. "
        f"If you see an MCP tool name here, the substrate/surface "
        f"distinction has eroded; see commit b66ceef."
    )
