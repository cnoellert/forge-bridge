"""POSIX append atomicity verification for forge_bridge.runtime.graph_emit.

v1.6-WRITERS-ROOM-CONVERGENCE.md Q8 acceptance criterion: verify that
``emit_event`` preserves record integrity under aggressive concurrent
multi-process append pressure on both platforms the bridge actually runs
on (Linux flame-01 + macOS portofino).

This is an empirical verification of an architectural assumption, NOT a
belief statement. POSIX ``O_APPEND`` is atomic per-write within
``PIPE_BUF``; that constant is 4096 bytes on Linux but **512 bytes on
macOS**. Typical Phase 24 records exceed 512 bytes — so macOS atomicity
under cross-process appends is *not* guaranteed by POSIX alone. This test
asks the question the convergence flagged: does it actually fail in
practice?

If this test passes cleanly on both platforms under aggressive pressure
with records biased above 512 bytes, the convergence-anticipated fcntl
advisory locking fallback stays a deferred-not-needed seed. If it fails
on macOS, the convergence's option (b) activates as a separately-bounded
~10-LOC addition.

What this test verifies (five narrow invariants):

1. **No torn writes** — every JSONL line parses as JSON without raising.
2. **No merged lines** — no line contains a JSON-object boundary
   followed by another JSON-object boundary on the same line.
3. **No truncated JSON** — every parsed value is a dict with the six
   required graph_emit fields.
4. **No dropped records** — total line count == workers × records-per-worker.
5. **Content integrity** — each record's payload reflects what the
   producer asked emit_event to write (size hint matches data length).

What this test does NOT verify (intentionally out of scope):

- Record ordering / sequencing semantics. That is a different guarantee.
  Multi-producer append-order is not promised by the substrate and not
  required by any Phase 24 consumer.
- Behavior under threads (vs processes). Threads share file descriptors
  and mask the kernel-level question this test exists to answer.
- Behavior over network filesystems. POSIX append atomicity guarantees do
  not extend to NFS / SMB / FUSE-mediated paths.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import random
import sys
from pathlib import Path

import pytest

from forge_bridge.runtime.graph_emit import emit_event, graph_dir


# Test parameters chosen to surface tearing probabilistically if it exists.
#
# - 8 worker processes — enough concurrent pressure to defeat any per-process
#   buffering that would mask a kernel-level atomicity gap.
# - 100 records per worker (= 800 total) — enough to make tearing reliably
#   observable, small enough to keep the test under a few seconds.
# - Payload sizes bias 600 / 1500 / 3000 bytes — all above macOS PIPE_BUF
#   (512) and below Linux PIPE_BUF (4096) at the small end, spanning the
#   risk band on both platforms.
_WORKERS = 8
_RECORDS_PER_WORKER = 100
_PAYLOAD_SIZES = (600, 1500, 3000)


def _worker(graph_dir_str: str, graph_id: str, worker_id: int, count: int) -> None:
    """Append ``count`` records to the shared graph_id JSONL file.

    Runs in a child process. Because ``multiprocessing`` defaults to ``spawn``
    on macOS, the child does not inherit the parent's monkeypatched env —
    we set ``FORGE_GRAPH_DIR`` explicitly before importing emit_event.
    """
    os.environ["FORGE_GRAPH_DIR"] = graph_dir_str
    # Import inside the worker so the env var takes effect for graph_dir().
    from forge_bridge.runtime.graph_emit import emit_event as _emit  # noqa: WPS433

    rng = random.Random(worker_id * 1_000_003)
    for i in range(count):
        size = rng.choice(_PAYLOAD_SIZES)
        payload = {
            "worker": worker_id,
            "i": i,
            "size": size,
            # Filler designed to make torn writes obvious: a contiguous run
            # of the worker's id character. If two writes interleave inside
            # one line, the run will contain two different characters.
            "data": chr(ord("a") + worker_id) * size,
        }
        _emit(
            graph_id=graph_id,
            node_kind="atomicity_test",
            status="record",
            payload=payload,
        )


def _has_merged_records(line: str) -> bool:
    """Detect two concatenated JSON objects on the same line.

    The JSONL substrate writes ``json.dumps(record) + "\\n"``. Each record
    starts with ``{`` and ends with ``}``. A merged line — produced by an
    atomicity failure where one write's tail and another's head land
    adjacent on the same line — would contain ``}{`` somewhere mid-string.
    """
    return "}{" in line


@pytest.mark.atomicity
def test_concurrent_multiprocess_append_preserves_record_integrity(
    tmp_path: Path,
) -> None:
    """Q8 acceptance: 8 workers × 100 records preserve all five invariants."""
    # Use a tmp dir explicitly — the conftest autouse fixture sets the env
    # for the parent, but child processes need it passed in.
    target_dir = tmp_path / "atomicity_graphs"
    target_dir.mkdir()
    os.environ["FORGE_GRAPH_DIR"] = str(target_dir)
    graph_id = "atom" + "0" * 28  # fixed 32-char hex; all workers share it.

    # Spawn explicitly for cross-platform predictability. fork on macOS has
    # known issues with Python subprocess state; spawn is what the actual
    # bridge runs under (uvicorn workers, MCP subprocess managers, etc.).
    ctx = multiprocessing.get_context("spawn")
    processes = [
        ctx.Process(
            target=_worker,
            args=(str(target_dir), graph_id, wid, _RECORDS_PER_WORKER),
        )
        for wid in range(_WORKERS)
    ]
    for p in processes:
        p.start()
    for p in processes:
        p.join(timeout=60.0)
        assert p.exitcode == 0, f"worker {p.pid} exited non-zero: {p.exitcode}"

    target_file = target_dir / f"{graph_id}.jsonl"
    assert target_file.exists(), f"expected JSONL file at {target_file}"

    expected_total = _WORKERS * _RECORDS_PER_WORKER
    raw_lines = target_file.read_text(encoding="utf-8").splitlines()

    # ── Invariant 4: no dropped records, exact count preservation ─────────
    assert len(raw_lines) == expected_total, (
        f"expected {expected_total} lines, got {len(raw_lines)} — "
        f"records were dropped or torn into multiple lines"
    )

    parsed_records: list[dict] = []
    for idx, line in enumerate(raw_lines):
        # ── Invariant 2: no merged records on the same line ───────────────
        assert not _has_merged_records(line), (
            f"line {idx} contains merged JSON objects (atomicity failure): "
            f"{line[:200]}..."
        )
        # ── Invariant 1: no torn writes — every line parses ───────────────
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"line {idx} did not parse as JSON: {exc}\nfirst 200 chars: "
                f"{line[:200]}"
            )
        assert isinstance(rec, dict), f"line {idx} parsed but not a dict"

        # ── Invariant 3: no truncated JSON — structural fields intact ─────
        required = {"event_id", "graph_id", "node_kind", "timestamp", "status", "payload"}
        missing = required - rec.keys()
        assert not missing, f"line {idx} missing required fields: {missing}"
        assert rec["graph_id"] == graph_id

        # ── Invariant 5: content integrity — data length matches size hint
        payload = rec["payload"]
        assert isinstance(payload, dict)
        assert "size" in payload and "data" in payload
        assert len(payload["data"]) == payload["size"], (
            f"line {idx} payload size hint ({payload['size']}) does not "
            f"match data length ({len(payload['data'])}) — torn write inside payload"
        )
        # The filler is a contiguous run of one character. If two writes
        # interleaved INSIDE the payload, we'd see multiple distinct
        # characters in the data field — a stronger atomicity check than
        # the line-level boundary tests above.
        assert len(set(payload["data"])) == 1, (
            f"line {idx} payload data is not a single repeated character "
            f"({sorted(set(payload['data']))}) — interleaved writes from "
            f"multiple workers landed in the same record"
        )

        parsed_records.append(rec)

    # Every worker emitted exactly _RECORDS_PER_WORKER records — verify by
    # bucketing parsed records back to their authoring worker.
    by_worker: dict[int, int] = {}
    for rec in parsed_records:
        worker_id = rec["payload"]["worker"]
        by_worker[worker_id] = by_worker.get(worker_id, 0) + 1
    assert set(by_worker.keys()) == set(range(_WORKERS)), (
        f"missing/extra workers in output: {sorted(by_worker.keys())}"
    )
    for wid, count in by_worker.items():
        assert count == _RECORDS_PER_WORKER, (
            f"worker {wid} emitted {count} records, expected {_RECORDS_PER_WORKER}"
        )


def test_atomicity_test_platform_provenance() -> None:
    """Record the platform the verification ran on for archaeology.

    Q8 acceptance is platform-conditional. This test exists so that a
    failed Q8 run on either platform surfaces in test output with the
    platform identifier, making it trivially obvious which acceptance
    branch failed without re-reading the convergence artifact.
    """
    platform = sys.platform
    # Both supported platforms must be one of these; anything else means
    # someone is running the test off-target.
    assert platform in ("darwin", "linux"), (
        f"Q8 acceptance criterion is scoped to macOS (portofino) + Linux "
        f"(flame-01); this run is on {platform}"
    )
