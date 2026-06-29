"""Live-selection resolver for `fbridge exec` bare verbs.

A bare ``/verb`` (no typed sequence + no segment index) auto-targets the
segment(s) the artist highlighted in Flame's open timeline, collapsing the
sequence prompt AND the segment-index prompt to zero/one pick. These tests mock
``_selected_segments`` + ``_segments`` (no daemon / Flame / DB) and prove:

  (a) exactly 1 selected -> both prompts skipped, the selected seg is used
  (b) >1 selected        -> a scoped list of ONLY the selected segs + IntPrompt
  (c) selection None      -> falls back to the existing _resolve_sequence flow
  (d) empty selection     -> same fallback
  (e) explicit sequence=/seg_index= -> selection is NEVER consulted
  (f) the chosen dict is _segments-shaped (carries trim fields), not the thin id
"""
from __future__ import annotations

import pytest

from forge_bridge.cli import interactive, verbs


# -- _FakeCon mirrors the test_exec_verbs.py console double --------------------


class _FakeCon:
    def __init__(self):
        self.lines: list[str] = []

    def print(self, *a, **k):
        self.lines.append(" ".join(str(x) for x in a))


def _full_seg(name: str, *, track_idx: int = 0, record_in: str = "r",
              record_in_frame: int = 100) -> dict:
    """A full _segments-shaped dict (carries the trim fields a thin id lacks)."""
    return {
        "track_idx": track_idx,
        "record_in": record_in,
        "record_in_frame": record_in_frame,
        "record_out_frame": record_in_frame + 100,
        "duration": 100,
        "head": 8,
        "tail": 8,
        "seg_name": name,
        "source_name": name,
    }


def _id_of(seg: dict) -> dict:
    """The thin selection identity for a full seg (what _selected_segments emits)."""
    return {k: seg[k] for k in ("track_idx", "record_in", "seg_name", "source_name")}


# -- pure helpers: _selection_key / _match_selected ---------------------------


def test_selection_key_matches_full_dict_and_thin_identity():
    full = _full_seg("shot_010")
    assert interactive._selection_key(full) == interactive._selection_key(_id_of(full))
    # the 'name' alias is honored (mirrors _selected_key_tuple)
    aliased = {"track_idx": 0, "record_in": "r", "name": "shot_010", "source_name": "shot_010"}
    assert interactive._selection_key(aliased) == interactive._selection_key(full)


def test_match_selected_filters_to_identities_only():
    s1, s2, s3 = _full_seg("a"), _full_seg("b", track_idx=1), _full_seg("c", track_idx=2)
    chosen = interactive._match_selected([s1, s2, s3], [_id_of(s1), _id_of(s3)])
    assert chosen == [s1, s3]  # only the selected, full dicts preserved
    # a non-matching identity yields nothing (caller falls through)
    assert interactive._match_selected([s1, s2], [_id_of(s3)]) == []


# -- _selected_segments tri-state (mock the bridge read) ----------------------


@pytest.mark.asyncio
async def test_selected_segments_returns_name_and_identities(monkeypatch):
    import forge_bridge.bridge as br

    async def ok(_code, **k):
        return {"sequence": "SEQ", "selected": [
            {"track_idx": 0, "record_in": "r", "seg_name": "x", "source_name": "x"}]}
    monkeypatch.setattr(br, "execute_json", ok)
    res = await interactive._selected_segments()
    assert res is not None
    name, ids = res
    assert name == "SEQ" and ids[0]["seg_name"] == "x"


@pytest.mark.asyncio
async def test_selected_segments_empty_is_successful_read(monkeypatch):
    import forge_bridge.bridge as br

    async def empty(_code, **k):
        return {"sequence": "SEQ", "selected": []}
    monkeypatch.setattr(br, "execute_json", empty)
    assert await interactive._selected_segments() == ("SEQ", [])


@pytest.mark.asyncio
async def test_selected_segments_none_on_guard_and_failure(monkeypatch):
    import forge_bridge.bridge as br

    async def guard_null(_code, **k):  # not on Timeline / no open clip -> JSON null
        return None
    monkeypatch.setattr(br, "execute_json", guard_null)
    assert await interactive._selected_segments() is None

    async def boom(_code, **k):  # Flame unreachable
        raise br.BridgeConnectionError("Flame down")
    monkeypatch.setattr(br, "execute_json", boom)
    assert await interactive._selected_segments() is None


# -- _run_verb wiring: the six required cases ---------------------------------


def _wire_downstream(monkeypatch, *, segs, captured=None):
    """Stub _segments + _preview_mutation + _apply_held so the SELECTION branch is
    the only live logic. Returns nothing; pass `captured` to record the chosen seg."""
    async def _segs(_seq):
        return segs
    monkeypatch.setattr(interactive, "_segments", _segs)

    async def prev(_verb, _seq, seg, _values):
        if captured is not None:
            captured["seg"] = seg
        return ({"apply_counterpart": {}, "resolved_plan": [1]}, None)
    monkeypatch.setattr(interactive, "_preview_mutation", prev)

    async def apply(_held):
        return True, "1 applied"
    monkeypatch.setattr(interactive, "_apply_held", apply)


@pytest.mark.asyncio
async def test_a_single_selection_skips_both_prompts(monkeypatch):
    con = _FakeCon()
    seg = _full_seg("shot_010")
    _wire_downstream(monkeypatch, segs=[seg, _full_seg("shot_020", track_idx=1)])

    async def sel():
        return ("SEQ", [_id_of(seg)])
    monkeypatch.setattr(interactive, "_selected_segments", sel)

    # the segment-index IntPrompt must NEVER fire on a single selection
    monkeypatch.setattr(interactive.IntPrompt, "ask",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no IntPrompt")))
    # a "Sequence" Prompt must NEVER fire; only the value + y/s/n gate
    asked = []

    def prompt(p="", *a, **k):
        asked.append(str(p))
        return "y" if "y / s / n" in str(p) else "shot_010_v2"
    monkeypatch.setattr(interactive.Prompt, "ask", prompt)

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"])
    blob = "\n".join(con.lines)
    assert "using your selected segment" in blob and "shot_010" in blob
    assert not any("Sequence" in p for p in asked)
    assert any("enacted in Flame" in line for line in con.lines)


@pytest.mark.asyncio
async def test_b_multi_selection_scoped_list_and_pick(monkeypatch):
    con = _FakeCon()
    s1 = _full_seg("sel_one")
    s2 = _full_seg("not_sel", track_idx=1)
    s3 = _full_seg("sel_two", track_idx=2)
    captured: dict = {}
    _wire_downstream(monkeypatch, segs=[s1, s2, s3], captured=captured)

    async def sel():
        return ("SEQ", [_id_of(s1), _id_of(s3)])  # 2 of 3 selected
    monkeypatch.setattr(interactive, "_selected_segments", sel)
    # the scoped picker chooses the 2nd of the SELECTED list -> s3
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 2)
    monkeypatch.setattr(interactive.Prompt, "ask",
                        lambda p="", *a, **k: "y" if "y / s / n" in str(p) else "x_v2")

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"])
    blob = "\n".join(con.lines)
    assert "segments selected" in blob and "2[/bold] segments selected" in blob
    assert "sel_one" in blob and "sel_two" in blob
    assert "not_sel" not in blob  # only the selected segs are listed
    assert captured["seg"]["seg_name"] == "sel_two"  # the IntPrompt pick (s3)


@pytest.mark.asyncio
async def test_c_selection_none_falls_back_to_resolve_sequence(monkeypatch):
    con = _FakeCon()
    _wire_downstream(monkeypatch, segs=[_full_seg("shot_010")])

    async def sel():
        return None
    monkeypatch.setattr(interactive, "_selected_segments", sel)

    resolved = {}

    async def resolve(_con):
        resolved["hit"] = True
        return "FALLBACK_SEQ"
    monkeypatch.setattr(interactive, "_resolve_sequence", resolve)
    # the full segment list + its IntPrompt is the fallback path
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 1)
    monkeypatch.setattr(interactive.Prompt, "ask",
                        lambda p="", *a, **k: "n")  # cancel at the gate

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"])
    assert resolved.get("hit") is True
    assert any("Segments on" in line for line in con.lines)  # full list, not scoped


@pytest.mark.asyncio
async def test_d_empty_selection_falls_back(monkeypatch):
    con = _FakeCon()
    _wire_downstream(monkeypatch, segs=[_full_seg("shot_010")])

    async def sel():
        return ("SEQ", [])  # successful read, nothing highlighted
    monkeypatch.setattr(interactive, "_selected_segments", sel)

    resolved = {}

    async def resolve(_con):
        resolved["hit"] = True
        return "FALLBACK_SEQ"
    monkeypatch.setattr(interactive, "_resolve_sequence", resolve)
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 1)
    monkeypatch.setattr(interactive.Prompt, "ask", lambda p="", *a, **k: "n")

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"])
    assert resolved.get("hit") is True


@pytest.mark.asyncio
@pytest.mark.parametrize("sequence,seg_index", [
    ("EXPLICIT", 1),   # one-shot / inline both supplied
    (None, 1),         # seg_index supplied alone
    ("EXPLICIT", None),  # sequence supplied alone
])
async def test_e_explicit_args_never_consult_selection(monkeypatch, sequence, seg_index):
    con = _FakeCon()
    _wire_downstream(monkeypatch, segs=[_full_seg("shot_010")])

    async def sel_boom():
        raise AssertionError("selection must not be consulted when an arg is explicit")
    monkeypatch.setattr(interactive, "_selected_segments", sel_boom)

    async def resolve(_con):
        return "FALLBACK_SEQ"  # only reached when sequence is None
    monkeypatch.setattr(interactive, "_resolve_sequence", resolve)
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 1)
    monkeypatch.setattr(interactive.Prompt, "ask", lambda p="", *a, **k: "n")

    # must not raise (sel_boom never fires) and must cancel cleanly at the gate
    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"],
                                sequence=sequence, seg_index=seg_index,
                                value_raw="shot_010_v2")
    assert any("not applied" in line for line in con.lines)


@pytest.mark.asyncio
async def test_f_chosen_seg_is_segments_shaped_for_trim(monkeypatch):
    # the selected dict passed downstream MUST carry the trim fields (record_in_frame
    # etc.), proving _match_selected reuses the full _segments dict — not the thin id.
    con = _FakeCon()
    seg = _full_seg("shot_010", record_in_frame=100)
    captured: dict = {}
    _wire_downstream(monkeypatch, segs=[seg], captured=captured)

    async def sel():
        return ("SEQ", [_id_of(seg)])
    monkeypatch.setattr(interactive, "_selected_segments", sel)
    # trim_head: value is an offset supplied by IntPrompt (12 frames off the head);
    # no segment-picker IntPrompt fires on a single selection, so 12 is the offset.
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 12)
    monkeypatch.setattr(interactive.Prompt, "ask",
                        lambda p="", *a, **k: "y" if "y / s / n" in str(p) else "")

    await interactive._run_verb(con, verb=verbs.REGISTRY["trim_head"])
    chosen = captured["seg"]
    assert "record_in_frame" in chosen and chosen["record_in_frame"] == 100
    assert "record_out_frame" in chosen and "head" in chosen and "tail" in chosen
