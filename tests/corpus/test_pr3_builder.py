"""PR 3 — ``_build_capture_record`` builder unit tests.

Coverage per ``A.5.3.2-PR3-SPEC.md`` §11.1:

  - test_builder_returns_schema_valid_record
  - test_builder_populates_topology_block
  - test_builder_populates_identity_block
  - test_builder_is_pure
  - test_builder_deterministic_with_injected_clock_uuid
  - test_builder_keeps_identity_separate_from_candidate_sets  (§5)
  - test_builder_uses_registered_tools_not_candidate_set_for_identity (§5)

The last two pin the orthogonal-truth-surfaces framing (§5):
``registered_tools`` fingerprints deployment identity; candidate sets
fingerprint runtime topology. Recombining them is prohibited per §14
phase-end conditions.
"""
from __future__ import annotations

import socket
from typing import Any
from unittest.mock import patch

import pytest

from forge_bridge.corpus._capture import _build_capture_record
from forge_bridge.corpus._identity import registered_tools_snapshot_hash
from forge_bridge.corpus._schema import (
    SCHEMA_VERSION,
    SchemaValidationError,
    validate_capture_record,
)

from tests.corpus._pr3_helpers import base_builder_args, tool


# ── Schema validity ────────────────────────────────────────────────────────


def test_builder_returns_schema_valid_record(clean_identity_caches):
    """The builder produces a record that passes schema validation."""
    record = _build_capture_record(**base_builder_args())
    validate_capture_record(record)  # no exception
    assert record["schema_version"] == SCHEMA_VERSION


def test_builder_populates_required_top_level_keys(clean_identity_caches):
    record = _build_capture_record(**base_builder_args())
    expected = {
        "schema_version", "capture_id", "captured_at", "source",
        "prompt", "candidate_set", "topology", "identity", "narrower",
    }
    assert expected <= record.keys()


# ── Topology block ─────────────────────────────────────────────────────────


def test_builder_populates_topology_block(clean_identity_caches):
    """The topology block matches the contract §3 shape — has
    ``probed_at`` and a ``backends`` dict with the three required
    backends."""
    record = _build_capture_record(**base_builder_args())
    topo = record["topology"]
    assert isinstance(topo, dict)
    assert "probed_at" in topo
    assert "backends" in topo
    assert {"flame_bridge", "ollama_local", "anthropic"} <= topo["backends"].keys()


# ── Identity block ─────────────────────────────────────────────────────────


def test_builder_populates_identity_block(clean_identity_caches):
    """The identity block contains all three hashes from PR 2."""
    record = _build_capture_record(**base_builder_args())
    identity = record["identity"]
    assert isinstance(identity, dict)
    for key in (
        "narrower_version_hash",
        "registered_tools_snapshot_hash",
        "daemon_git_sha",
    ):
        assert key in identity
        assert isinstance(identity[key], str)
        assert identity[key]  # non-empty


# ── Purity ─────────────────────────────────────────────────────────────────


def test_builder_is_pure_no_disk_writes(clean_identity_caches, tmp_path, monkeypatch):
    """Builder must not perform any disk write. We monkeypatch the
    corpus-dir env var to a tmp path that we then verify is
    untouched."""
    corpus_dir = tmp_path / "corpus"
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(corpus_dir))

    _ = _build_capture_record(**base_builder_args())

    # The directory must not exist (the builder did not create it,
    # and the writer was never called).
    assert not corpus_dir.exists()


def test_builder_is_pure_no_network(clean_identity_caches):
    """Builder must not open network sockets. We patch
    ``socket.socket`` and assert it's never called."""
    with patch("socket.socket", wraps=socket.socket) as patched:
        _ = _build_capture_record(**base_builder_args())
    assert patched.call_count == 0


# ── Test-injection seams ───────────────────────────────────────────────────


def test_builder_deterministic_with_injected_clock_uuid(clean_identity_caches):
    """Test-injection seams (``now``, ``new_uuid``) produce
    byte-identical records across multiple invocations."""
    fixed_time = "2026-05-07T14:32:11.123Z"
    fixed_uuid = "12345678-1234-1234-1234-123456789abc"

    args = base_builder_args(
        now=lambda: fixed_time,
        new_uuid=lambda: fixed_uuid,
    )
    record_a = _build_capture_record(**args)
    record_b = _build_capture_record(**args)

    assert record_a["captured_at"] == fixed_time
    assert record_a["capture_id"] == fixed_uuid

    # Records differ only in topology.probed_at (which is also
    # time-derived but uses the topology helper's own clock — that's
    # PR 2's domain). Strip topology.probed_at for the equality
    # check; everything else must match.
    a_topo_probed = record_a["topology"].pop("probed_at")
    b_topo_probed = record_b["topology"].pop("probed_at")
    assert isinstance(a_topo_probed, str)
    assert isinstance(b_topo_probed, str)

    assert record_a == record_b


# ── Orthogonal truth surfaces (§5) ─────────────────────────────────────────


def test_builder_keeps_identity_separate_from_candidate_sets(
    clean_identity_caches,
):
    """§5 orthogonality regression guard.

    Emit two records with the SAME ``registered_tools`` but
    DIFFERENT ``candidate_set_post_reachability`` (e.g., one with
    flame_bridge tools reachable, one without). The
    ``identity.registered_tools_snapshot_hash`` must be IDENTICAL
    across both records. This is the regression guard against
    future "simplification" PRs that recombine identity and
    topology signal surfaces.

    Per spec §14 phase-end conditions: a future PR proposing to
    drop the ``registered_tools`` parameter and derive identity
    from the post-reachability set is rejected at the spec layer.
    """
    registered = [
        tool("forge_list_staged"),
        tool("forge_get_staged"),
        tool("flame_publish_sequence"),
        tool("flame_assemble_published_sequence"),
    ]

    # Scenario A: flame_bridge is reachable; all flame_* tools are
    # in post_reachability.
    args_a = base_builder_args(
        registered_tools=registered,
        candidate_set_post_reachability=registered,
    )
    record_a = _build_capture_record(**args_a)

    # Scenario B: flame_bridge is unreachable; flame_* tools are
    # filtered out of post_reachability. ``registered_tools`` is
    # the same.
    args_b = base_builder_args(
        registered_tools=registered,
        candidate_set_post_reachability=[
            tool("forge_list_staged"),
            tool("forge_get_staged"),
        ],
    )
    record_b = _build_capture_record(**args_b)

    # Identity hash must be identical — registered set didn't change.
    assert (
        record_a["identity"]["registered_tools_snapshot_hash"]
        == record_b["identity"]["registered_tools_snapshot_hash"]
    ), (
        "registered_tools_snapshot_hash diverged when only the "
        "post-reachability set differed. This is the §5 "
        "orthogonality violation: identity drift must be "
        "distinguishable from topology drift in the corpus."
    )


def test_builder_uses_registered_tools_not_candidate_set_for_identity(
    clean_identity_caches,
):
    """§5 orthogonality: when ``registered_tools`` and
    ``candidate_set_post_reachability`` differ, the identity hash
    must equal the hash of ``registered_tools``, NOT the hash of
    the candidate set.

    This is the case where a backend was unreachable: the registered
    set is a strict superset of the post-reachability set. The
    identity hash captures the deployment, not the runtime topology.
    """
    registered = [
        tool("forge_list_staged"),
        tool("forge_get_staged"),
        tool("flame_publish_sequence"),
    ]
    post_reach = [
        tool("forge_list_staged"),
        tool("forge_get_staged"),
    ]
    # registered ≠ post_reach (flame backend unreachable).

    args = base_builder_args(
        registered_tools=registered,
        candidate_set_post_reachability=post_reach,
    )
    record = _build_capture_record(**args)

    expected_identity_hash = registered_tools_snapshot_hash(registered)
    wrong_identity_hash = registered_tools_snapshot_hash(post_reach)

    assert (
        record["identity"]["registered_tools_snapshot_hash"]
        == expected_identity_hash
    )
    assert (
        record["identity"]["registered_tools_snapshot_hash"]
        != wrong_identity_hash
    ), (
        "identity hash matched the candidate-set hash instead of the "
        "registered-tools hash. §5 violation: the builder must use "
        "the deployment-identity input, not the topology-filtered "
        "operational subset."
    )
