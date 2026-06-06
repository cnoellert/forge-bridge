"""Tests for v1.0.1 protocol builder extensions.

Covers:
  - query_lineage(entity_id) builder + QUERY_LINEAGE MsgType
  - query_shot_deps(shot_id) builder + QUERY_SHOT_DEPS MsgType
  - media_scan(project_name, role, shot_name, project_id) builder + MEDIA_SCAN MsgType
  - entity_list() backward compatibility (no narrowing kwargs)
  - entity_list() with shot_id / role / source_name narrowing kwargs
"""

from __future__ import annotations

from forge_bridge.server.protocol import (
    Message,
    MsgType,
    entity_list,
    error,
    media_scan,
    ok,
    pong,
    query_lineage,
    query_shot_deps,
    welcome,
)


# ── MsgType constants ──────────────────────────────────────────────────


def test_msg_type_query_lineage_constant():
    assert MsgType.QUERY_LINEAGE == "query.lineage"


def test_msg_type_query_shot_deps_constant():
    assert MsgType.QUERY_SHOT_DEPS == "query.shot_deps"


def test_msg_type_media_scan_constant():
    assert MsgType.MEDIA_SCAN == "media.scan"


# ── query_lineage builder ──────────────────────────────────────────────


def test_query_lineage_builder_shape():
    msg = query_lineage(entity_id="e-123")
    assert msg["type"] == "query.lineage"
    assert msg["entity_id"] == "e-123"
    assert msg.msg_id  # non-empty uuid


# ── query_shot_deps builder ────────────────────────────────────────────


def test_query_shot_deps_builder_shape():
    msg = query_shot_deps(shot_id="s-456")
    assert msg["type"] == "query.shot_deps"
    assert msg["shot_id"] == "s-456"
    assert msg.msg_id


# ── media_scan builder ─────────────────────────────────────────────────


def test_media_scan_builder_shape():
    msg = media_scan(
        project_name="proj",
        role="plate",
        shot_name="s001",
        project_id="p-1",
    )
    assert msg["type"] == "media.scan"
    assert msg["project_name"] == "proj"
    assert msg["role"] == "plate"
    assert msg["shot_name"] == "s001"
    assert msg["project_id"] == "p-1"
    assert msg.msg_id


# ── entity_list backward compatibility ─────────────────────────────────


def test_entity_list_backward_compat_two_args():
    """Existing 2-arg positional call sites must keep working."""
    msg = entity_list("shot", "p-1")
    assert msg["type"] == "entity.list"
    assert msg["entity_type"] == "shot"
    assert msg["project_id"] == "p-1"
    # No narrowing kwargs produced when not passed.
    assert "shot_id" not in msg
    assert "role" not in msg
    assert "source_name" not in msg


# ── entity_list narrowing kwargs ───────────────────────────────────────


def test_entity_list_with_all_narrowing_kwargs():
    msg = entity_list(
        "version",
        "p-1",
        shot_id="s-1",
        role="plate",
        source_name="cam_a",
    )
    assert msg["entity_type"] == "version"
    assert msg["project_id"] == "p-1"
    assert msg["shot_id"] == "s-1"
    assert msg["role"] == "plate"
    assert msg["source_name"] == "cam_a"


def test_entity_list_with_only_shot_id_narrowing():
    msg = entity_list("version", "p-1", shot_id="s-1")
    assert msg["shot_id"] == "s-1"
    assert "role" not in msg
    assert "source_name" not in msg


# ── Cross-repo state_ws correlation contract ──────────────────────────────
# Bridge's native correlation key is "id"; forge_core clients key the request id
# as "msg_id" and correlate replies on "ref_msg_id" (fallback "msg_id"). The
# state_ws must read either inbound key and echo "ref_msg_id" so EVERY client
# correlates. See .planning/STATE-WS-CORRELATION-CONTRACT.md.


def test_msg_id_reads_bridge_native_id_key():
    assert Message({"type": "ping", "id": "Y"}).msg_id == "Y"


def test_msg_id_reads_forge_core_msg_id_key():
    # forge_core envelope: request id under "msg_id", no "id"
    assert Message({"type": "ping", "msg_id": "X"}).msg_id == "X"


def test_is_request_true_for_both_envelopes():
    assert Message({"type": "ping", "id": "Y"}).is_request()
    assert Message({"type": "ping", "msg_id": "X"}).is_request()


def test_replies_echo_correlation_under_all_keys():
    rid = "req-123"
    for reply in (
        ok(rid, {"k": "v"}),
        error(rid, "INVALID", "bad"),
        pong(rid),
        welcome("sess-1", rid),
    ):
        # Every client correlation strategy must match:
        assert reply["id"] == rid          # bridge-native clients
        assert reply["ref_msg_id"] == rid  # forge_core response branch (ok/error)
        assert reply["msg_id"] == rid      # forge_core pong branch (bare msg_id)


def test_round_trip_correlation_response_branch():
    # forge_core ok/error path: matches on ref_msg_id (fallback msg_id).
    request = Message({"type": "entity.get", "msg_id": "abc"})
    reply = error(request.msg_id, "NOT_FOUND", "nope")
    forge_core_ref = reply.get("ref_msg_id") or reply.msg_id
    assert forge_core_ref == "abc"


def test_round_trip_correlation_pong_branch():
    # forge_core pong path is SEPARATE: it matches on the reply's bare msg_id,
    # NOT ref_msg_id. This is the gap that left ping hanging until msg_id was
    # echoed on replies too.
    request = Message({"type": "ping", "msg_id": "ping-xyz"})
    reply = pong(request.msg_id)
    assert reply.msg_id == "ping-xyz"      # forge_core resolves _pending["ping-xyz"]
