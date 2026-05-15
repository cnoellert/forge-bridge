"""Tests for `fbridge graph list` + `fbridge graph show` — Phase 24 §2.4.

Verifies the smallest consumer of the proto-node JSONL substrate that
forge_bridge.runtime.graph_emit writes. Read-only debug surface; not a
product surface. Contract per v1.6-PHASE-24-CONVERGENCE.md §2.4 + Q20
(v1.6-WRITERS-ROOM-CONVERGENCE.md).

Conftest autouse fixture already redirects FORGE_GRAPH_DIR to a per-test
tmp dir, so tests freely call graph_emit.emit_event without touching
~/.forge-bridge/graphs/.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from forge_bridge.cli.main import app
from forge_bridge.runtime.graph_emit import emit_event, graph_dir, new_graph_id

runner = CliRunner()


# ── list ──────────────────────────────────────────────────────────────────


def test_graph_list_empty_dir_human() -> None:
    result = runner.invoke(app, ["graph", "list"])
    assert result.exit_code == 0
    assert "no graphs recorded" in result.stdout


def test_graph_list_empty_dir_json() -> None:
    result = runner.invoke(app, ["graph", "list", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["data"] == []
    assert body["graph_dir"]


def test_graph_list_populated_human_shows_graph_ids() -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    emit_event(graph_id=gid, node_kind="python", status="completed")
    result = runner.invoke(app, ["graph", "list"])
    assert result.exit_code == 0
    assert gid[:12] in result.stdout
    assert "python" in result.stdout
    # status="completed" maps to chip "ok" in render._chip_for_status
    assert "ok" in result.stdout


def test_graph_list_json_envelope_shape() -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    result = runner.invoke(app, ["graph", "list", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    row = body["data"][0]
    assert row["graph_id"] == gid
    assert row["record_count"] == 1
    assert row["first_node_kind"] == "python"
    assert row["first_status"] == "started"
    assert row["last_status"] == "started"
    assert row["last_timestamp"]


def test_graph_list_sorts_newest_first() -> None:
    import time

    g_old = new_graph_id()
    emit_event(graph_id=g_old, node_kind="python", status="started")
    time.sleep(0.01)
    g_new = new_graph_id()
    emit_event(graph_id=g_new, node_kind="python", status="started")

    result = runner.invoke(app, ["graph", "list", "--json"])
    body = json.loads(result.stdout)
    ids = [row["graph_id"] for row in body["data"]]
    assert ids.index(g_new) < ids.index(g_old)


def test_graph_list_honors_limit() -> None:
    for _ in range(5):
        emit_event(graph_id=new_graph_id(), node_kind="python", status="started")
    result = runner.invoke(app, ["graph", "list", "--limit", "3", "--json"])
    body = json.loads(result.stdout)
    assert len(body["data"]) == 3


# ── show ──────────────────────────────────────────────────────────────────


def test_graph_show_full_id_human() -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    emit_event(graph_id=gid, node_kind="python", status="completed", payload={"elapsed_ms": 42})
    result = runner.invoke(app, ["graph", "show", gid])
    assert result.exit_code == 0
    assert gid in result.stdout
    assert "python" in result.stdout
    # status="completed" renders as chip "ok"; "started" renders as "loaded"
    assert "ok" in result.stdout
    assert "loaded" in result.stdout
    assert "elapsed_ms" in result.stdout


def test_graph_show_full_id_json_envelope() -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    emit_event(graph_id=gid, node_kind="python", status="completed")
    result = runner.invoke(app, ["graph", "show", gid, "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["graph_id"] == gid
    assert len(body["data"]) == 2
    assert body["data"][0]["status"] == "started"
    assert body["data"][1]["status"] == "completed"
    assert body["path"].endswith(f"{gid}.jsonl")


def test_graph_show_unique_prefix_resolves() -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    result = runner.invoke(app, ["graph", "show", gid[:8], "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["graph_id"] == gid


def test_graph_show_ambiguous_prefix_exits_1() -> None:
    # Force two graph_ids with shared prefix by writing files directly.
    target = graph_dir()
    target.mkdir(parents=True, exist_ok=True)
    a = target / "abcd0000000000000000000000000001.jsonl"
    b = target / "abcd0000000000000000000000000002.jsonl"
    a.write_text(
        json.dumps(
            {
                "event_id": "x",
                "graph_id": a.stem,
                "node_kind": "python",
                "timestamp": "2026-05-15T00:00:00.000Z",
                "status": "started",
                "payload": {},
            }
        )
        + "\n"
    )
    b.write_text(
        json.dumps(
            {
                "event_id": "y",
                "graph_id": b.stem,
                "node_kind": "python",
                "timestamp": "2026-05-15T00:00:01.000Z",
                "status": "started",
                "payload": {},
            }
        )
        + "\n"
    )
    result = runner.invoke(app, ["graph", "show", "abcd", "--json"])
    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "graph_ambiguous"
    assert len(body["error"]["matches"]) == 2


def test_graph_show_missing_id_exits_2() -> None:
    result = runner.invoke(app, ["graph", "show", "deadbeef" * 4, "--json"])
    assert result.exit_code == 2
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "graph_not_found"


def test_graph_show_missing_dir_exits_2() -> None:
    # autouse fixture points FORGE_GRAPH_DIR at tmp_path / "forge_graphs" which
    # does not yet exist until something writes to it.
    result = runner.invoke(app, ["graph", "show", "deadbeef" * 4, "--json"])
    assert result.exit_code == 2
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "graph_not_found"


# ── tolerance of malformed records ────────────────────────────────────────


def test_graph_list_skips_malformed_lines() -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    # Append a malformed line directly.
    path = graph_dir() / f"{gid}.jsonl"
    with path.open("a") as f:
        f.write("not valid json\n")
        f.write("\n")  # blank line
    emit_event(graph_id=gid, node_kind="python", status="completed")
    result = runner.invoke(app, ["graph", "list", "--json"])
    body = json.loads(result.stdout)
    row = body["data"][0]
    # Two real records + one malformed (skipped) + one blank (skipped) = 2
    assert row["record_count"] == 2
    assert row["last_status"] == "completed"


def test_graph_show_emits_path_field() -> None:
    gid = new_graph_id()
    emit_event(graph_id=gid, node_kind="python", status="started")
    result = runner.invoke(app, ["graph", "show", gid, "--json"])
    body = json.loads(result.stdout)
    assert Path(body["path"]).name == f"{gid}.jsonl"
