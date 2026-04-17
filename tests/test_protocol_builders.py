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
    MsgType,
    entity_list,
    media_scan,
    query_lineage,
    query_shot_deps,
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
