"""Tests for forge_bridge.runtime.graph_emit — Phase 24 substrate.

Embarrassingly small substrate; embarrassingly small tests. Substrate
contract:

- ``new_graph_id`` returns a unique 32-char hex string.
- ``graph_dir`` honors ``FORGE_GRAPH_DIR`` override.
- ``emit_event`` writes one JSONL line per call to
  ``<graph_dir>/<graph_id>.jsonl`` with the six required fields.
- Records append, do not overwrite.
- Distinct ``graph_id`` values land in distinct files.
- ``payload`` defaults to ``{}`` when omitted.
- Missing target directory is created at first write.
- Timestamps are ISO-8601 UTC with trailing ``Z`` and parse cleanly.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from forge_bridge.runtime.graph_emit import emit_event, graph_dir, new_graph_id


@pytest.fixture
def tmp_graph_dir(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(tmp_path))
    return tmp_path


def test_new_graph_id_returns_unique_values() -> None:
    assert new_graph_id() != new_graph_id()


def test_new_graph_id_is_32_char_hex_string() -> None:
    gid = new_graph_id()
    assert isinstance(gid, str)
    assert len(gid) == 32
    int(gid, 16)  # parses cleanly as hex; raises if not


def test_graph_dir_respects_env_override(tmp_graph_dir: Path) -> None:
    assert graph_dir() == tmp_graph_dir


def test_emit_event_returns_event_id(tmp_graph_dir: Path) -> None:
    gid = new_graph_id()
    eid = emit_event(graph_id=gid, node_kind="test", status="created")
    assert isinstance(eid, str)
    assert len(eid) == 32
    int(eid, 16)


def test_emit_event_writes_jsonl_record_with_six_required_fields(
    tmp_graph_dir: Path,
) -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="test_kind", status="created")
    path = tmp_graph_dir / f"{gid}.jsonl"
    assert path.exists()
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert set(rec.keys()) == {
        "event_id",
        "graph_id",
        "node_kind",
        "timestamp",
        "status",
        "payload",
    }
    assert rec["graph_id"] == gid
    assert rec["node_kind"] == "test_kind"
    assert rec["status"] == "created"
    assert rec["payload"] == {}


def test_emit_event_appends_does_not_overwrite(tmp_graph_dir: Path) -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="test", status="created")
    emit_event(graph_id=gid, node_kind="test", status="completed")
    path = tmp_graph_dir / f"{gid}.jsonl"
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    rec1 = json.loads(lines[0])
    rec2 = json.loads(lines[1])
    assert rec1["status"] == "created"
    assert rec2["status"] == "completed"
    assert rec1["graph_id"] == rec2["graph_id"] == gid
    assert rec1["event_id"] != rec2["event_id"]


def test_emit_event_separates_distinct_graph_ids_into_distinct_files(
    tmp_graph_dir: Path,
) -> None:
    g1 = new_graph_id()
    g2 = new_graph_id()
    emit_event(graph_id=g1, node_kind="test", status="created")
    emit_event(graph_id=g2, node_kind="test", status="created")
    f1 = tmp_graph_dir / f"{g1}.jsonl"
    f2 = tmp_graph_dir / f"{g2}.jsonl"
    assert f1.exists() and f2.exists()
    rec1 = json.loads(f1.read_text().strip())
    rec2 = json.loads(f2.read_text().strip())
    assert rec1["graph_id"] == g1
    assert rec2["graph_id"] == g2


def test_emit_event_records_payload_verbatim(tmp_graph_dir: Path) -> None:
    gid = new_graph_id()
    payload = {"elapsed_ms": 42, "result": "ok", "nested": {"k": "v"}}
    emit_event(graph_id=gid, node_kind="test", status="completed", payload=payload)
    rec = json.loads((tmp_graph_dir / f"{gid}.jsonl").read_text().strip())
    assert rec["payload"] == payload


def test_emit_event_creates_missing_target_directory(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "deep" / "nested" / "graphs"
    monkeypatch.setenv("FORGE_GRAPH_DIR", str(target))
    assert not target.exists()
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="test", status="created")
    assert target.exists()
    assert (target / f"{gid}.jsonl").exists()


def test_emit_event_timestamp_is_parseable_iso8601_utc(
    tmp_graph_dir: Path,
) -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="test", status="created")
    rec = json.loads((tmp_graph_dir / f"{gid}.jsonl").read_text().strip())
    ts = rec["timestamp"]
    assert ts.endswith("Z")
    # parse as UTC; raises if malformed
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
