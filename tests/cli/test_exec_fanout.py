"""Multi-select fan-out for `fbridge exec` (Approach A: one multi-entry delta).

When the artist highlights MULTIPLE segments, a bare verb applies to ALL of them
in ONE preview->ratify->commit via a single TimelineDelta with N DeltaEntry rows.
These tests are pure (no daemon / Flame / DB) and cover:

  * the counter helpers (`has_counter` / `expand_counter`) + `timeline_sorted`
  * the N-segment delta builders (rename counter-template, trim shared offset)
  * single-segment output stays byte-identical to the legacy 1-entry build
  * `_run_fanout` guards: multi-rename needs a counter; a trim out-of-range on
    ANY selected segment is rejected naming the offender(s)
  * timeline-order numbering for an out-of-order selection
"""
from __future__ import annotations

import pytest

from forge_bridge.cli import interactive, verbs


def _seg(name: str, *, track_idx: int = 0, record_in_frame: int = 100,
         duration: int = 100, head: int = 8, tail: int = 8) -> dict:
    return {
        "track_idx": track_idx,
        "record_in": "r",
        "record_in_frame": record_in_frame,
        "record_out_frame": record_in_frame + duration,
        "duration": duration,
        "head": head,
        "tail": tail,
        "seg_name": name,
        "source_name": name,
    }


def _entries(delta: dict) -> list:
    return delta.get("changes") or delta.get("entries")


# -- counter helpers ----------------------------------------------------------


def test_has_counter_detects_every_token():
    assert verbs.has_counter("shot_$n")
    assert verbs.has_counter("shot_$nn")
    assert verbs.has_counter("shot_$nnn")
    assert verbs.has_counter("shot_$iteration")
    assert not verbs.has_counter("shot_010")


def test_expand_counter_bare_and_padded_and_alias():
    # position is 0-based; bare $n -> start 1, step 1
    assert verbs.expand_counter("shot_$n", 0) == "shot_1"
    assert verbs.expand_counter("shot_$n", 11) == "shot_12"
    # $n{width} zero-pads
    assert verbs.expand_counter("s_$n{2}", 0) == "s_01"
    assert verbs.expand_counter("s_$n{2}", 11) == "s_12"
    assert verbs.expand_counter("s_$n{3}", 1) == "s_002"
    # $n{width,start,step} -> the sh### convention
    assert verbs.expand_counter("sh$n{3,10,10}", 0) == "sh010"
    assert verbs.expand_counter("sh$n{3,10,10}", 2) == "sh030"
    # $iteration is an alias for $n
    assert verbs.expand_counter("sh_$iteration", 2) == "sh_3"
    # no token -> returned unchanged (literal)
    assert verbs.expand_counter("HERO", 0) == "HERO"


def test_timeline_sorted_orders_by_track_then_in_point():
    a = _seg("a", track_idx=0, record_in_frame=200)
    b = _seg("b", track_idx=0, record_in_frame=100)
    c = _seg("c", track_idx=1, record_in_frame=50)
    ordered = verbs.timeline_sorted([a, c, b])
    assert [s["seg_name"] for s in ordered] == ["b", "a", "c"]


# -- N-segment delta builders -------------------------------------------------


def test_build_rename_delta_multi_numbers_in_timeline_order():
    # pass OUT OF ORDER -> numbered by timeline position (track, in-point)
    later = _seg("later", track_idx=0, record_in_frame=300)
    earlier = _seg("earlier", track_idx=0, record_in_frame=100)
    delta = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segments": [later, earlier], "new_name": "shot_$n"})
    entries = _entries(delta)
    assert len(entries) == 2
    # entry order follows timeline order; numbering matches
    assert entries[0]["metadata"]["seg_name"] == "earlier"
    assert entries[0]["after"]["name"] == "shot_1"
    assert entries[1]["metadata"]["seg_name"] == "later"
    assert entries[1]["after"]["name"] == "shot_2"


def test_build_rename_delta_multi_zero_padded():
    s1 = _seg("one", record_in_frame=100)
    s2 = _seg("two", record_in_frame=200)
    delta = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segments": [s1, s2], "new_name": "s_$n{2}"})
    names = [e["after"]["name"] for e in _entries(delta)]
    assert names == ["s_01", "s_02"]


def test_build_rename_delta_multi_start_step():
    # $n{width,start,step} -> the sh### shot-numbering convention
    s1 = _seg("one", record_in_frame=100)
    s2 = _seg("two", record_in_frame=200)
    s3 = _seg("three", record_in_frame=300)
    delta = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segments": [s1, s2, s3], "new_name": "sh$n{3,10,10}"})
    names = [e["after"]["name"] for e in _entries(delta)]
    assert names == ["sh010", "sh020", "sh030"]


def test_build_trim_head_delta_multi_shared_offset():
    s1 = _seg("one", record_in_frame=100)
    s2 = _seg("two", track_idx=1, record_in_frame=500)
    delta = verbs.build_trim_head_delta(
        {"sequence_name": "CUT", "segments": [s1, s2], "count": 12})
    entries = _entries(delta)
    assert len(entries) == 2
    assert entries[0]["before"]["frame_in"] == 100 and entries[0]["after"]["frame_in"] == 112
    assert entries[1]["before"]["frame_in"] == 500 and entries[1]["after"]["frame_in"] == 512


def test_build_trim_tail_delta_multi_shared_offset():
    s1 = _seg("one", record_in_frame=100, duration=100)   # out=200
    s2 = _seg("two", track_idx=1, record_in_frame=500, duration=100)  # out=600
    delta = verbs.build_trim_tail_delta(
        {"sequence_name": "CUT", "segments": [s1, s2], "count": 10})
    entries = _entries(delta)
    assert entries[0]["before"]["frame_out"] == 200 and entries[0]["after"]["frame_out"] == 190
    assert entries[1]["before"]["frame_out"] == 600 and entries[1]["after"]["frame_out"] == 590


# -- single-segment byte-identity (the binding constraint) --------------------


def test_single_segment_segments_list_equals_legacy_segment():
    seg = _seg("shot_010", record_in_frame=86400, duration=100)
    # rename: legacy single-segment key vs 1-element segments list -> identical
    legacy_rn = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segment": seg, "new_name": "shot_010_v2"})
    multi_rn = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segments": [seg], "new_name": "shot_010_v2"})
    assert legacy_rn == multi_rn
    # a counter token now expands even for a lone rename (0-based position 0 -> 1);
    # byte-identity is only promised for a TOKEN-FREE literal (asserted above).
    lit = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segment": seg, "new_name": "shot_$n"})
    assert _entries(lit)[0]["after"]["name"] == "shot_1"
    # trim: same equivalence
    legacy_th = verbs.build_trim_head_delta(
        {"sequence_name": "CUT", "segment": seg, "count": 12})
    multi_th = verbs.build_trim_head_delta(
        {"sequence_name": "CUT", "segments": [seg], "count": 12})
    assert legacy_th == multi_th


# -- _run_fanout guards + flow (mocked; no daemon/Flame/DB) -------------------


class _FakeCon:
    def __init__(self):
        self.lines: list[str] = []

    def print(self, *a, **k):
        self.lines.append(" ".join(str(x) for x in a))


def _value_then_choice(value: str, choice: str = "y"):
    """A Prompt.ask double: returns the y/s/n choice for the gate, else `value`."""
    def ask(p="", *a, **k):
        return choice if "y / s / n" in str(p) else value
    return ask


@pytest.mark.asyncio
async def test_fanout_trim_multi_previews_and_applies(monkeypatch):
    con = _FakeCon()
    s1 = _seg("one", record_in_frame=100)
    s2 = _seg("two", track_idx=1, record_in_frame=500)
    captured: dict = {}

    async def prev_multi(_verb, _seq, segs_in, values):
        captured["segs"] = segs_in
        captured["values"] = values
        return ({"apply_counterpart": {}, "resolved_plan": [1, 1]}, None)

    async def apply(_held):
        captured["applied"] = True
        return True, "2 applied"
    monkeypatch.setattr(interactive, "_preview_mutation_multi", prev_multi)
    monkeypatch.setattr(interactive, "_apply_held", apply)
    # one offset for the whole batch via IntPrompt; y at the gate
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 12)
    monkeypatch.setattr(interactive.Prompt, "ask", _value_then_choice(""))

    await interactive._run_fanout(con, verb=verbs.REGISTRY["trim_head"],
                                  sequence="CUT", segs=[s1, s2])
    assert captured["values"] == {"count": 12}
    assert [s["seg_name"] for s in captured["segs"]] == ["one", "two"]
    assert captured.get("applied") is True
    blob = "\n".join(con.lines)
    assert "2 segments in Flame" in blob and "enacted in Flame" in blob


def test_build_rename_multi_bare_name_applies_literally_to_all():
    # no counter token -> Flame allows duplicate names; every segment gets the
    # literal name, no reject (the old "needs a counter" guard is gone).
    s1 = _seg("one", record_in_frame=100)
    s2 = _seg("two", record_in_frame=200)
    delta = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segments": [s1, s2], "new_name": "plain_name"})
    names = [e["after"]["name"] for e in _entries(delta)]
    assert names == ["plain_name", "plain_name"]


@pytest.mark.asyncio
async def test_fanout_rename_malformed_counter_is_rejected(monkeypatch):
    con = _FakeCon()
    s1 = _seg("one")
    s2 = _seg("two", track_idx=1)

    async def prev_boom(*a, **k):
        raise AssertionError("must reject a malformed counter before preview")
    monkeypatch.setattr(interactive, "_preview_mutation_multi", prev_boom)
    monkeypatch.setattr(interactive.Prompt, "ask", _value_then_choice("x_$n{q}"))

    await interactive._run_fanout(con, verb=verbs.REGISTRY["rename"],
                                  sequence="CUT", segs=[s1, s2])
    blob = "\n".join(con.lines)
    assert "bad counter format" in blob and "$n{q}" in blob


@pytest.mark.asyncio
async def test_fanout_trim_out_of_range_names_offender(monkeypatch):
    con = _FakeCon()
    ok = _seg("ok_seg", record_in_frame=100, duration=100)        # 12 is fine
    bad = _seg("bad_seg", track_idx=1, record_in_frame=500, duration=10)  # 12 >= 10

    async def prev_boom(*a, **k):
        raise AssertionError("must reject before preview, never partial-apply")
    monkeypatch.setattr(interactive, "_preview_mutation_multi", prev_boom)
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 12)
    monkeypatch.setattr(interactive.Prompt, "ask", _value_then_choice(""))

    await interactive._run_fanout(con, verb=verbs.REGISTRY["trim_head"],
                                  sequence="CUT", segs=[ok, bad])
    reject = next(line for line in con.lines if "can't do that" in line)
    assert "bad_seg" in reject        # the offender is named with its reason
    assert "10-frame segment" in reject
    assert "ok_seg" not in reject     # the in-range one is NOT in the reject line


@pytest.mark.asyncio
async def test_fanout_rename_stage_branch(monkeypatch):
    con = _FakeCon()
    s1 = _seg("one", record_in_frame=100)
    s2 = _seg("two", record_in_frame=200)
    staged: dict = {}

    async def prev_multi(_verb, _seq, segs_in, _values):
        return ({"apply_counterpart": {}, "resolved_plan": [1, 1]}, None)

    async def stage_multi(verb, sequence, segs_in, values, *, display):
        staged["args"] = (verb.name, sequence, [s["seg_name"] for s in segs_in],
                          values, display)
        return "gid_multi_123"

    async def apply_boom(_held):
        raise AssertionError("apply must not run on [s]")
    monkeypatch.setattr(interactive, "_preview_mutation_multi", prev_multi)
    monkeypatch.setattr(interactive, "_stage_mutation_multi", stage_multi)
    monkeypatch.setattr(interactive, "_apply_held", apply_boom)
    monkeypatch.setattr(interactive.Prompt, "ask", _value_then_choice("shot_$n", choice="s"))

    await interactive._run_fanout(con, verb=verbs.REGISTRY["rename"],
                                  sequence="CUT", segs=[s1, s2])
    assert staged["args"][0] == "rename"
    assert staged["args"][2] == ["one", "two"]
    assert staged["args"][3] == {"new_name": "shot_$n"}
    blob = "\n".join(con.lines)
    assert "gid_multi_123" in blob and "fbridge ratify" in blob
    # preview shows each expanded name before the stage decision
    assert "one  →  shot_1" in blob and "two  →  shot_2" in blob
