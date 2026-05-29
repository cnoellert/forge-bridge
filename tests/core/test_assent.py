from __future__ import annotations

from datetime import datetime

import forge_bridge

from forge_bridge.core.assent import AssentRecord


def test_assent_record_defaults_to_proposed():
    record = AssentRecord(
        graph_intent_id="abc123",
        chain_steps=["list shots", "commit"],
    )

    assert record.graph_intent_id == "abc123"
    assert record.chain_steps == ["list shots", "commit"]
    assert record.status == "proposed"
    assert record.decided_by is None
    assert record.decided_at is None
    assert record.applied_at is None
    assert record.apply_result is None
    assert record.apply_failure_reason is None


def test_assent_record_entity_type_override():
    record = AssentRecord(
        graph_intent_id="abc123",
        chain_steps=["list shots", "commit"],
    )

    assert record.entity_type == "assent_record"


def test_assent_record_to_dict_shape_and_none_timestamps():
    record = AssentRecord(
        graph_intent_id="abc123",
        chain_steps=["list shots", "commit"],
    )

    data = record.to_dict()

    assert set(data) == {
        "id",
        "entity_type",
        "created_at",
        "metadata",
        "locations",
        "relationships",
        "graph_intent_id",
        "chain_steps",
        "status",
        "decided_by",
        "decided_at",
        "applied_at",
        "apply_result",
        "apply_failure_reason",
    }
    assert len(data) == 14
    assert data["entity_type"] == "assent_record"
    assert data["graph_intent_id"] == "abc123"
    assert data["chain_steps"] == ["list shots", "commit"]
    assert data["decided_at"] is None
    assert data["applied_at"] is None


def test_assent_record_to_dict_serializes_timestamps():
    decided_at = datetime(2026, 5, 28, 12, 1, 2)
    applied_at = datetime(2026, 5, 28, 12, 3, 4)
    record = AssentRecord(
        graph_intent_id="abc123",
        chain_steps=["list shots", "commit"],
        decided_at=decided_at,
        applied_at=applied_at,
    )

    data = record.to_dict()

    assert data["decided_at"] == decided_at.isoformat()
    assert data["applied_at"] == applied_at.isoformat()


def test_assent_record_not_exported_from_package_root():
    assert not hasattr(forge_bridge, "AssentRecord")
    assert "AssentRecord" not in forge_bridge.__all__
