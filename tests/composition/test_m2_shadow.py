"""M2 slice 5 — shadow parity instrumentation over live read chains.

Shadow makes the graph engine a live production caller for READ chains without
changing authoritative behavior: legacy ``run_chain_steps`` stays authoritative
and byte-identical, and the graph path runs opportunistically alongside it,
emitting one interpretable parity-evidence record per run.

These tests pin the load-bearing invariants:

  * FLAG-OFF is an exact passthrough of ``run_chain_steps`` — the wrapper does
    not wrap the MCP, does not emit, does not change the returned body.
  * FLAG-ON match lands a record with ``outcome="match"`` and a stamped
    ``comparison_mode="replay"``.
  * A graph explosion lands ``outcome="shadow_error"`` AND the authoritative
    body is returned intact (a shadow failure never regresses a read).
  * A time-box overrun lands ``outcome="shadow_timeout"`` (a hung run never
    vanishes — it lands as its own outcome).
  * The match-key collapses benign argument-shape skew but distinguishes a
    genuinely-different value (the property that makes a robustly-keyed miss
    interpretable #153 evidence).

No live daemon is needed: the graph MCP is a replay server over the in-memory
records the (stubbed) legacy path captured.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from forge_bridge.composition import _shadow
from forge_bridge.composition._shadow import (
    SHADOW_ENV,
    ShadowRecorder,
    _match_key,
    shadow_enabled,
    wrap_mcp_for_shadow,
)
from forge_bridge.console import _engine
from forge_bridge.console._engine import run_chain_steps_with_shadow


class _FakeMCP:
    """Minimal async MCP: returns a fixed payload for any ``call_tool``."""

    def __init__(self, payload):
        self.payload = payload

    async def call_tool(self, tool_name, *args, **kwargs):
        return self.payload


def _read_records(tmp_path):
    files = list(tmp_path.glob("shadow-compare-*.jsonl"))
    assert len(files) == 1, f"expected one sink file, got {files}"
    lines = [
        json.loads(line)
        for line in files[0].read_text().splitlines()
        if line.strip()
    ]
    return [rec for rec in lines if not rec.get("_header")]


@pytest.fixture()
def shadow_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(_shadow.SHADOW_DIR_ENV, str(tmp_path))
    return tmp_path


# ── FLAG-OFF: exact passthrough ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flag_off_is_byte_identical_passthrough(monkeypatch, shadow_dir):
    monkeypatch.setenv(SHADOW_ENV, "0")
    sentinel = {"status": "success", "request_id": "r0", "chain": [], "error": None}
    seen = {}

    async def _fake_legacy(*, mcp, **kwargs):
        seen["mcp"] = mcp
        seen["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(_engine, "run_chain_steps", _fake_legacy)
    raw_mcp = _FakeMCP({"status": "ok"})

    result = await run_chain_steps_with_shadow(
        steps=["forge_is_greenscreen shot_id=gs clip_ref=mock://x"],
        tools=[],
        mcp=raw_mcp,
        request_id="r0",
        client_ip="test",
        started=0.0,
    )

    assert result is sentinel  # body unchanged, same object
    assert seen["mcp"] is raw_mcp  # MCP not wrapped when flag off
    assert not list(shadow_dir.glob("shadow-compare-*.jsonl"))  # nothing emitted


# ── FLAG-ON: match lands a record with comparison_mode stamped ──────────────


@pytest.mark.asyncio
async def test_flag_on_match_records_match_and_mode(monkeypatch, shadow_dir):
    monkeypatch.setenv(SHADOW_ENV, "1")
    payload = {"status": "ok", "is_greenscreen": True, "shot_id": "gs"}
    steps = ["forge_is_greenscreen shot_id=gs clip_ref=mock://x"]

    async def _fake_legacy(*, mcp, steps, request_id, **kwargs):
        # Legacy makes its one tool call through the (recorder-wrapped) mcp,
        # exactly as the real engine does: positional (tool_name, params).
        raw = await mcp.call_tool(
            "forge_is_greenscreen",
            {"shot_id": "gs", "clip_ref": "mock://x"},
        )
        return {
            "status": "success",
            "request_id": request_id,
            "chain": [{"step": steps[0], "result": raw}],
            "error": None,
        }

    monkeypatch.setattr(_engine, "run_chain_steps", _fake_legacy)

    body = await run_chain_steps_with_shadow(
        steps=steps,
        tools=[],
        mcp=_FakeMCP(payload),
        request_id="r-match",
        client_ip="test",
        started=0.0,
    )

    assert body["status"] == "success"  # authoritative body intact
    records = _read_records(shadow_dir)
    assert len(records) == 1
    rec = records[0]
    assert rec["outcome"] == "match"
    assert rec["comparison_mode"] == "replay"
    assert rec["chain_steps"] == steps
    assert rec["step_count"] == 1
    # operator-idempotency class is recorded as evidence metadata, distinct
    # from comparison_mode.
    assert rec["operator_strategy"] == "double_exec"


# ── FLAG-ON: graph explodes → shadow_error, body intact ─────────────────────


@pytest.mark.asyncio
async def test_flag_on_graph_explosion_records_error_and_returns_body(
    monkeypatch, shadow_dir
):
    monkeypatch.setenv(SHADOW_ENV, "1")
    sentinel = {
        "status": "success",
        "request_id": "r-boom",
        "chain": [],
        "error": None,
    }

    async def _fake_legacy(*, request_id, **kwargs):
        return sentinel

    def _boom(_steps):
        raise RuntimeError("graph compile exploded")

    monkeypatch.setattr(_engine, "run_chain_steps", _fake_legacy)
    monkeypatch.setattr(_shadow, "compile_chain_steps", _boom)

    body = await run_chain_steps_with_shadow(
        steps=["forge_is_greenscreen shot_id=gs clip_ref=mock://x"],
        tools=[],
        mcp=_FakeMCP({"status": "ok"}),
        request_id="r-boom",
        client_ip="test",
        started=0.0,
    )

    assert body is sentinel  # a shadow failure never regresses the read
    records = _read_records(shadow_dir)
    assert len(records) == 1
    assert records[0]["outcome"] == "shadow_error"
    assert records[0]["comparison_mode"] == "replay"
    assert "graph compile exploded" in records[0]["detail"]


# ── FLAG-ON: time-box overrun → shadow_timeout ──────────────────────────────


@pytest.mark.asyncio
async def test_flag_on_timeout_records_shadow_timeout(monkeypatch, shadow_dir):
    monkeypatch.setenv(SHADOW_ENV, "1")
    monkeypatch.setattr(_shadow, "SHADOW_BUDGET_S", 0.01)

    async def _fake_legacy(*, request_id, **kwargs):
        return {"status": "success", "request_id": request_id, "chain": [], "error": None}

    async def _slow(**kwargs):
        await asyncio.sleep(1.0)
        return {}

    monkeypatch.setattr(_engine, "run_chain_steps", _fake_legacy)
    monkeypatch.setattr(_shadow, "_build_compare_record", _slow)

    body = await run_chain_steps_with_shadow(
        steps=["forge_is_greenscreen shot_id=gs clip_ref=mock://x"],
        tools=[],
        mcp=_FakeMCP({"status": "ok"}),
        request_id="r-slow",
        client_ip="test",
        started=0.0,
    )

    assert body["status"] == "success"  # never blocks the response
    records = _read_records(shadow_dir)
    assert len(records) == 1
    assert records[0]["outcome"] == "shadow_timeout"


# ── FLAG-ON: graph replay requests an identity legacy never recorded ────────


@pytest.mark.asyncio
async def test_flag_on_replay_miss_records_replay_miss_distinct_from_divergence(
    monkeypatch, shadow_dir
):
    """A #153-shaped divergence lands ``outcome="replay_miss"`` end-to-end.

    Construction: WRAPPER-LEVEL (option 1, the truest end-to-end). This drives
    the real ``run_chain_steps_with_shadow`` with the flag on; only the
    authoritative ``run_chain_steps`` is stubbed, exactly as every other flag-on
    test in this file does. The stubbed legacy records ONE ``forge_is_greenscreen``
    call whose ``shot_id`` value diverges from the value in the compiled step
    (``shot_id=gs-DIVERGENT`` recorded vs ``shot_id=gs`` in the chain step). The
    graph path is fully real from there: the SAME step is compiled, the
    ``GraphExecutor`` dispatches the operator, and ``_ReplayMCP`` looks up the
    graph-requested call-identity — which, because the recorded value differs,
    is a distinct ``_match_key`` the captured records never cover. That raises
    the real ``ShadowReplayMiss`` at ``_shadow.py:328`` and lands the real
    emitted ``replay_miss`` record in the JSONL sink.

    This is the truest available construction: the whole graph → compile →
    dispatch → replay → emit path runs unmocked; the assertion is on the REAL
    record in the sink, not a mock of the emit. (Option 2 — hand-driving
    ``shadow_compare`` with a bare recorder — was unnecessary because the
    wrapper accepts a stubbed legacy cleanly, so the wrapper stays in the loop.)

    The value-divergence (not a bare empty/absent record) is deliberately the
    faithful #153 shape: the graph asks for a call identity legacy never
    recorded *because a kwarg value differs* — the exact property the
    skew-robust match-key preserves and the reason a robustly-keyed miss is
    #153 evidence rather than benign skew.
    """

    monkeypatch.setenv(SHADOW_ENV, "1")
    steps = ["forge_is_greenscreen shot_id=gs clip_ref=mock://x"]

    async def _fake_legacy(*, mcp, steps, request_id, **kwargs):
        # Legacy records a call whose shot_id value diverges from the compiled
        # step, so the graph's replay request keys to an identity absent from
        # the captured records → a genuine (not benign-skew) replay miss.
        raw = await mcp.call_tool(
            "forge_is_greenscreen",
            {"shot_id": "gs-DIVERGENT", "clip_ref": "mock://x"},
        )
        return {
            "status": "success",
            "request_id": request_id,
            "chain": [{"step": steps[0], "result": raw}],
            "error": None,
        }

    monkeypatch.setattr(_engine, "run_chain_steps", _fake_legacy)

    body = await run_chain_steps_with_shadow(
        steps=steps,
        tools=[],
        mcp=_FakeMCP({"status": "ok", "is_greenscreen": True}),
        request_id="r-miss",
        client_ip="test",
        started=0.0,
    )

    assert body["status"] == "success"  # authoritative body intact
    records = _read_records(shadow_dir)
    assert len(records) == 1
    rec = records[0]
    assert rec["outcome"] == "replay_miss"
    assert rec["comparison_mode"] == "replay"
    # replay_miss is its OWN category and must NEVER be conflated with
    # divergence — that separation is a locked review decision.
    assert rec["outcome"] != "divergence"
    # It is the REPLAY-stage miss (the graph asked for an uncaptured identity),
    # not the compile-stage replay_miss (a compiler-gap): the graph compiled,
    # ran, and the miss carries the tool it could not serve.
    assert rec["stage"] == "replay"
    assert "forge_is_greenscreen" in rec["replay_misses"]
    assert rec["chain_steps"] == steps


# ── The skew-robust match-key (grounding-pass Q2) ───────────────────────────


def test_match_key_collapses_benign_skew():
    # numeric-string vs number
    assert _match_key("t", {"n": "5"}) == _match_key("t", {"n": 5})
    # bool-string vs bool
    assert _match_key("t", {"flag": "true"}) == _match_key("t", {"flag": True})
    # explicit None vs omitted kwarg
    assert _match_key("t", {"a": 1, "b": None}) == _match_key("t", {"a": 1})
    # key ordering (canonical JSON sorts)
    assert _match_key("t", {"a": 1, "b": 2}) == _match_key("t", {"b": 2, "a": 1})
    # whitespace on a string scalar
    assert _match_key("t", {"s": " x "}) == _match_key("t", {"s": "x"})


def test_match_key_distinguishes_real_value_difference():
    # A genuinely different value survives normalization → distinct key. This is
    # what makes a robustly-keyed replay_miss interpretable #153 evidence.
    assert _match_key("t", {"n": 5}) != _match_key("t", {"n": 6})
    # A missing inherited kwarg (the #153 divergence shape) → distinct key.
    assert _match_key("t", {"shot_id": "s"}) != _match_key("t", {})
    # Different tool name never collides.
    assert _match_key("a", {}) != _match_key("b", {})


# ── The recorder is a transparent observer ──────────────────────────────────


@pytest.mark.asyncio
async def test_recorder_is_transparent_and_captures():
    payload = {"status": "ok"}
    recorder = wrap_mcp_for_shadow(_FakeMCP(payload))
    assert isinstance(recorder, ShadowRecorder)
    got = await recorder.call_tool("forge_ping", {"a": 1})
    assert got is payload  # result passes through unchanged
    assert recorder.records == [("forge_ping", {"a": 1}, payload)]


def test_shadow_enabled_reads_env(monkeypatch):
    monkeypatch.setenv(SHADOW_ENV, "on")
    assert shadow_enabled() is True
    monkeypatch.setenv(SHADOW_ENV, "0")
    assert shadow_enabled() is False
    monkeypatch.delenv(SHADOW_ENV, raising=False)
    assert shadow_enabled() is False
