"""PR 2 — topology snapshot tests.

Preserved invariants for PR 2 (verbatim from the user-supplied
review framing — carry into commit message under "preserved
invariants" and into this docstring):

  1. Descriptive, not evaluative.
     Capture: reachable/unreachable, configured/available,
              identity/version, routing state.
     Do not capture: healthy, preferred, recommended, fallback-worthy.
     Evaluative fields propagate semantic weight that belongs in
     Layer 2.

  2. Observational, not semantic.
     Identity hashes record state snapshots.
     Do not invent: compatibility grades, equivalence classes,
                    drift scoring.
     Those are derived judgments for Layer 2's classifier.

  3. No lazy runtime side effects.
     Topology and identity helpers must not:
       - initialize providers
       - warm clients
       - allocate transports
       - touch arbitration state
       - spawn background tasks
       - mutate caches into warm-state preparation
     Capture observes existing state; capture never causes state.
     Test this explicitly.

  4. Loud asymmetry preserved.
     Topology working without writes is correct.
     Identity working without replay is correct.
     The writer remains deferred to PR 3 specifically because the
     architectural pressure to fuse observation with persistence is
     highest at this moment.

This test module covers ``snapshot_topology`` against the four
invariants. The identity-side coverage lives in
``test_pr2_identity.py``.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest


# ── Returned shape conforms to the Layer 1 schema ──────────────────────────


def test_snapshot_returns_schema_compliant_topology_block(
    clean_flame_reachability_cache, monkeypatch,
):
    """Snapshot output is suitable for direct embedding under
    ``topology`` in a Layer 1 record."""
    from forge_bridge.corpus._topology import snapshot_topology
    from forge_bridge.corpus import validate_capture_record

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    snap = snapshot_topology()

    assert "probed_at" in snap
    assert "backends" in snap
    backends = snap["backends"]
    assert set(backends.keys()) >= {
        "flame_bridge", "ollama_local", "anthropic",
    }
    for name, state in backends.items():
        assert "reachable" in state, name
        assert isinstance(state["reachable"], bool), name
        assert "configured" in state, name
        assert "identity" in state, name

    # Embed into a minimal record and confirm the schema accepts it.
    record = _minimal_record_with_topology(snap)
    validate_capture_record(record)


# ── Invariant 1 — descriptive, not evaluative ──────────────────────────────


def test_snapshot_emits_only_descriptive_fields(
    clean_flame_reachability_cache,
):
    """The topology block must NOT carry evaluative fields like
    'healthy', 'preferred', 'recommended', or 'fallback-worthy'.
    Those belong in Layer 2's classifier."""
    from forge_bridge.corpus._topology import snapshot_topology

    snap = snapshot_topology()
    forbidden = {"healthy", "preferred", "recommended", "fallback_worthy",
                 "fallbackWorthy", "fallback-worthy"}
    for backend_name, state in snap["backends"].items():
        leaked = forbidden & state.keys()
        assert not leaked, (
            f"backend {backend_name!r} leaked evaluative fields: "
            f"{leaked}. Layer 1 records observations only; evaluative "
            f"semantics belong to Layer 2."
        )


# ── Invariant 2 — observational, not semantic ──────────────────────────────


def test_snapshot_does_not_synthesize_grades_or_classes(
    clean_flame_reachability_cache,
):
    """The topology block must NOT carry derived judgments like
    'compatibility_grade', 'equivalence_class', or 'drift_score'."""
    from forge_bridge.corpus._topology import snapshot_topology

    snap = snapshot_topology()
    forbidden = {
        "compatibility_grade", "equivalence_class", "drift_score",
        "score", "grade", "class",
    }
    for backend_name, state in snap["backends"].items():
        leaked = forbidden & state.keys()
        assert not leaked, (
            f"backend {backend_name!r} leaked semantic-judgment "
            f"fields: {leaked}."
        )


# ── Invariant 3 — no lazy runtime side effects ─────────────────────────────


def test_snapshot_does_not_call_probe_backend(
    clean_flame_reachability_cache,
):
    """Reading topology MUST NOT trigger a fresh probe of any backend.

    The cache may be cold (no probe done yet); in that case
    `reachable: false` is the truthful answer, not the result of an
    on-demand probe."""
    from forge_bridge.corpus._topology import snapshot_topology

    with patch(
        "forge_bridge.console._tool_filter._probe_backend",
        side_effect=AssertionError(
            "snapshot_topology must not probe; this is invariant 3"
        ),
    ) as probe:
        for _ in range(10):
            snapshot_topology()
        probe.assert_not_called()


def test_snapshot_does_not_open_network_connections(
    clean_flame_reachability_cache,
):
    """Snapshot MUST NOT open any TCP connection."""
    from forge_bridge.corpus._topology import snapshot_topology

    with patch(
        "asyncio.open_connection",
        side_effect=AssertionError(
            "snapshot_topology must not open connections"
        ),
    ):
        for _ in range(10):
            snapshot_topology()


def test_snapshot_does_not_mutate_flame_reachability_cache(
    clean_flame_reachability_cache,
):
    """Snapshot MUST be a pure read of the existing cache; calling it
    must not populate, expand, or otherwise alter ``_tool_filter._cache``."""
    from forge_bridge.console._tool_filter import _cache as _flame_cache
    from forge_bridge.corpus._topology import snapshot_topology

    initial = dict(_flame_cache)
    for _ in range(10):
        snapshot_topology()
    assert dict(_flame_cache) == initial, (
        "snapshot_topology mutated _tool_filter._cache; this would "
        "be 'observation causing state' which invariant 3 forbids."
    )


def test_snapshot_does_not_spawn_background_tasks(
    clean_flame_reachability_cache,
):
    """Snapshot MUST NOT create any asyncio.Task. Verified by running
    inside an event loop and counting tasks before/after."""
    from forge_bridge.corpus._topology import snapshot_topology

    async def _run():
        # Snapshot the set of tasks BEFORE; running the call sync
        # inside an async context shouldn't create any new task.
        before = asyncio.all_tasks()
        for _ in range(10):
            snapshot_topology()
        after = asyncio.all_tasks()
        # The "current task" set is the same; nothing new appeared.
        assert after == before, (
            f"snapshot_topology created tasks: {after - before}"
        )

    asyncio.run(_run())


# ── Idempotence — first and tenth call operationally indistinguishable ────


def test_snapshot_is_observationally_idempotent(
    clean_flame_reachability_cache,
):
    """The first and tenth call return the same shape (same keys,
    same value types) and produce no new side effects.

    Per invariant 3: 'first and tenth invocation should be
    operationally indistinguishable except for returned data
    freshness'. The probed_at timestamp may legitimately differ;
    everything else must be stable."""
    from forge_bridge.corpus._topology import snapshot_topology

    snaps = [snapshot_topology() for _ in range(10)]

    # Same set of backend keys.
    backend_key_sets = [frozenset(s["backends"].keys()) for s in snaps]
    assert all(k == backend_key_sets[0] for k in backend_key_sets)

    # Same per-backend keys.
    for backend in snaps[0]["backends"]:
        per_call_keys = [
            frozenset(s["backends"][backend].keys()) for s in snaps
        ]
        assert all(k == per_call_keys[0] for k in per_call_keys), backend

    # Reachable values are stable across calls (no probe-on-demand
    # quietly flipping things).
    for backend in snaps[0]["backends"]:
        reachable = [s["backends"][backend]["reachable"] for s in snaps]
        assert all(r == reachable[0] for r in reachable), backend


# ── Unknown-state-is-truthful ──────────────────────────────────────────────


def test_unknown_reachability_does_not_throw_or_synthesize(
    clean_flame_reachability_cache, monkeypatch,
):
    """With a cold cache and no env config, snapshot returns a
    truthful record (reachable: false, identity: null) rather than
    throwing or synthesizing defaults."""
    from forge_bridge.corpus._topology import snapshot_topology

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("FORGE_LOCAL_LLM_URL", raising=False)

    snap = snapshot_topology()
    backends = snap["backends"]

    # Per the user's example: unknown ≠ thrown / silently omitted.
    assert backends["flame_bridge"]["reachable"] is False
    assert backends["flame_bridge"]["identity"] is None
    assert backends["ollama_local"]["reachable"] is False
    assert backends["ollama_local"]["identity"] is None
    assert backends["anthropic"]["reachable"] is False
    assert backends["anthropic"]["identity"] is None
    assert backends["anthropic"]["configured"] is False  # no API key set


def test_warm_flame_cache_is_observed_truthfully(
    clean_flame_reachability_cache,
):
    """When ``_tool_filter._cache`` carries a fresh probe result,
    snapshot reflects it. This verifies snapshot is reading the cache
    (not always returning false)."""
    import time

    from forge_bridge.console._tool_filter import _cache as _flame_cache
    from forge_bridge.corpus._topology import snapshot_topology

    # Seed the cache as if a probe just ran and saw flame as reachable.
    _flame_cache["flame_bridge"] = (True, time.monotonic() + 5.0)
    snap = snapshot_topology()
    assert snap["backends"]["flame_bridge"]["reachable"] is True

    # And falsy state is observed too.
    _flame_cache["flame_bridge"] = (False, time.monotonic() + 5.0)
    snap = snapshot_topology()
    assert snap["backends"]["flame_bridge"]["reachable"] is False


# ── Helpers ────────────────────────────────────────────────────────────────


def _minimal_record_with_topology(topology_block: dict) -> dict:
    """Build a minimal Layer 1 record with the given topology block,
    suitable for schema validation."""
    return {
        "schema_version": "1",
        "capture_id": "00000000-0000-0000-0000-000000000000",
        "captured_at": "2026-05-06T12:00:00Z",
        "source": "fixture",
        "prompt": "x",
        "candidate_set": {
            "post_reachability": [],
            "post_pr14_filter": [],
        },
        "topology": topology_block,
        "identity": {
            "narrower_version_hash": "a" * 64,
            "registered_tools_snapshot_hash": "b" * 64,
            "daemon_git_sha": "c" * 40,
        },
        "narrower": {
            "decision": [],
            "pr20_condition_met": False,
            "collapse_occurred": False,
            "ambiguity_state": "zero_survivor",
            "latency_ms": 0.0,
        },
    }
