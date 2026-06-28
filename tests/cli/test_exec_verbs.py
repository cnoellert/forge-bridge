"""Pure unit tests for the fbridge exec verb registry + result helpers.

No daemon, no Flame, no DB — just the deterministic spec-building and the
result-parsing helpers the interactive/one-shot renderers rely on.
"""
from __future__ import annotations

import json as _json
from types import SimpleNamespace

import pytest

from forge_bridge.cli import verbs


def _fake_seg(name: str = "shot_010") -> dict:
    return {
        "track_idx": 0,
        "record_in": "'01:00:00+00'",
        "record_in_frame": 86400,
        "record_out_frame": 86500,
        "duration": 100,
        "head": 8,
        "tail": 8,
        "seg_name": name,
        "source_name": name,
    }


def test_registry_exposes_rename():
    assert "rename" in verbs.REGISTRY
    v = verbs.REGISTRY["rename"]
    assert v.label and v.summary
    assert verbs.list_verbs()  # non-empty


def test_build_rename_delta_envelope():
    delta = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segment": _fake_seg(), "new_name": "shot_010_v2"}
    )
    # TimelineDelta.to_dict emits the change-list under "changes" (wire key).
    entry = (delta.get("changes") or delta.get("entries"))[0]
    assert entry["action"] == "updated"
    assert entry["object_type"] == "segment"
    assert entry["after"]["name"] == "shot_010_v2"
    md = entry["metadata"]
    assert md["track_idx"] == 0
    assert md["sequence_name"] == "CUT"
    assert md["seg_name"] == "shot_010"
    assert md["source_name"] == "shot_010"
    assert md["record_in"] == "'01:00:00+00'"


def test_build_host_mutation_spec_is_preview_shape():
    delta = verbs.build_rename_delta(
        {"sequence_name": "CUT", "segment": _fake_seg(), "new_name": "x"}
    )
    spec = verbs.build_host_mutation_spec(delta, verbs.host_resolve_operator())
    # operation -> delta_to_manifest, no commit (ratify replays commit separately)
    assert [n.node_id for n in spec.nodes] == ["op", "delta_to_manifest"]
    assert len(spec.edges) == 1
    assert spec.edges[0].to_port == "deltas"
    assert spec.nodes[0].config["arguments"]["delta"] is delta


# -- verbs: relative head/tail trim (temporal-delta rail) ---------------------


def test_registry_exposes_trim_head_and_tail_not_trim():
    assert "trim" not in verbs.REGISTRY  # the absolute-frame verb is gone
    for name, side, ckey in (("trim_head", "head", "record_in_frame"),
                             ("trim_tail", "tail", "record_out_frame")):
        v = verbs.REGISTRY[name]
        assert v.label and v.summary
        assert v.value_kind == "offset"
        assert v.value_field == "count"
        assert v.current_key == ckey
        assert v.trim_side == side


def test_build_trim_head_delta_offset_added_to_record_in():
    # positive count trims OFF the head: after_frame_in = record_in_frame + count
    delta = verbs.build_trim_head_delta(
        {"sequence_name": "CUT", "segment": _fake_seg(), "count": 12}
    )
    entry = (delta.get("changes") or delta.get("entries"))[0]
    assert entry["action"] == "updated"
    assert entry["object_type"] == "segment"
    assert entry["before"]["frame_in"] == 86400
    assert entry["after"]["frame_in"] == 86412  # +12 off the head
    assert entry["before"]["id"] == entry["after"]["id"]  # only frame_in changes
    md = entry["metadata"]
    assert md["track_idx"] == 0
    assert md["sequence_name"] == "CUT"
    assert md["seg_name"] == "shot_010"
    assert md["record_in"] == "'01:00:00+00'"


def test_build_trim_head_delta_negative_extends():
    delta = verbs.build_trim_head_delta(
        {"sequence_name": "CUT", "segment": _fake_seg(), "count": -5}
    )
    entry = (delta.get("changes") or delta.get("entries"))[0]
    assert entry["before"]["frame_in"] == 86400
    assert entry["after"]["frame_in"] == 86395  # -5 extends the head earlier


def test_build_trim_tail_delta_offset_subtracted_from_record_out():
    # positive count trims OFF the tail: after_frame_out = record_out_frame - count
    delta = verbs.build_trim_tail_delta(
        {"sequence_name": "CUT", "segment": _fake_seg(), "count": 12}
    )
    entry = (delta.get("changes") or delta.get("entries"))[0]
    assert "frame_out" in entry["before"] and "frame_in" not in entry["before"]
    assert entry["before"]["frame_out"] == 86500
    assert entry["after"]["frame_out"] == 86488  # -12 off the tail (out earlier)


def test_build_trim_tail_delta_negative_extends():
    delta = verbs.build_trim_tail_delta(
        {"sequence_name": "CUT", "segment": _fake_seg(), "count": -5}
    )
    entry = (delta.get("changes") or delta.get("entries"))[0]
    assert entry["before"]["frame_out"] == 86500
    assert entry["after"]["frame_out"] == 86505  # -5 extends the tail later


def test_build_trim_delta_spec_wiring():
    delta = verbs.build_trim_head_delta(
        {"sequence_name": "CUT", "segment": _fake_seg(), "count": 1}
    )
    spec = verbs.build_host_mutation_spec(delta, verbs.host_resolve_operator())
    assert [n.node_id for n in spec.nodes] == ["op", "delta_to_manifest"]
    assert spec.nodes[0].config["arguments"]["delta"] is delta


# -- CLI-side range validation (the legible-error UX fix) ---------------------


def test_validate_trim_rejects_over_trim_with_legible_message():
    v = verbs.REGISTRY["trim_head"]
    msg = verbs.validate_trim(v, 800, {"duration": 780, "head": 8, "tail": 8})
    assert msg is not None
    assert "can't trim 800 off a 780-frame segment" in msg


def test_validate_trim_rejects_over_extend_beyond_handle():
    head = verbs.validate_trim(verbs.REGISTRY["trim_head"], -20,
                               {"duration": 100, "head": 8, "tail": 8})
    assert head is not None and "head" in head and "8 frames" in head
    tail = verbs.validate_trim(verbs.REGISTRY["trim_tail"], -20,
                               {"duration": 100, "head": 8, "tail": 8})
    assert tail is not None and "tail" in tail and "8 frames" in tail


def test_validate_trim_accepts_in_range_and_ignores_non_trim_verbs():
    seg = {"duration": 100, "head": 8, "tail": 8}
    assert verbs.validate_trim(verbs.REGISTRY["trim_head"], 12, seg) is None
    assert verbs.validate_trim(verbs.REGISTRY["trim_head"], -8, seg) is None  # exactly the handle
    # non-trim verb -> always None (guard is a no-op)
    assert verbs.validate_trim(verbs.REGISTRY["rename"], 999, seg) is None


def test_describe_change_offset_never_leaks_absolute_frame():
    off = verbs.describe_change(verbs.REGISTRY["trim_head"], 86400, 12)
    assert off == "trim 12 frames off the head"
    assert "86400" not in off
    onto = verbs.describe_change(verbs.REGISTRY["trim_tail"], 86500, -5)
    assert onto == "trim 5 frames onto the tail"


# -- shared trust-boundary parse/validation -----------------------------------


def test_parse_value_offset_accepts_signed_and_rejects_zero():
    v = verbs.REGISTRY["trim_head"]
    # positive trims off, negative extends — both accepted
    assert verbs.parse_value(v, "12") == (12, None)
    assert verbs.parse_value(v, "  -5 ") == (-5, None)
    # non-integer rejected
    val, err = verbs.parse_value(v, "ten")
    assert val is None and "whole number" in err
    # zero is a no-op, not a frame -> rejected
    val, err = verbs.parse_value(v, "0")
    assert val is None and "nothing to trim" in err


def test_parse_value_str_rejects_empty():
    v = verbs.REGISTRY["rename"]
    assert verbs.parse_value(v, " shot_v2 ") == ("shot_v2", None)
    val, err = verbs.parse_value(v, "   ")
    assert val is None and "empty" in err


def test_is_unchanged():
    rn = verbs.REGISTRY["rename"]
    th = verbs.REGISTRY["trim_head"]
    assert verbs.is_unchanged(rn, "shot_010", "shot_010") is True
    assert verbs.is_unchanged(rn, "shot_011", "shot_010") is False
    # offset: 0 is the only no-op; the absolute "current" is irrelevant
    assert verbs.is_unchanged(th, 0, 86400) is True
    assert verbs.is_unchanged(th, 12, 86400) is False
    assert verbs.is_unchanged(th, -5, None) is False


# -- inline slash-arg parser (power-user fast path) ---------------------------

from forge_bridge.cli import interactive  # noqa: E402


def test_parse_inline_full_args_both_verbs():
    # rename: rest-of-line value may contain spaces
    seq, idx, val, err = interactive._parse_inline("myseq #3 New Shot Name")
    assert err is None
    assert (seq, idx) == ("myseq", 3)
    assert val == "New Shot Name"
    # trim: single signed int token as value (rest-of-line; parse_value types it)
    seq, idx, val, err = interactive._parse_inline("CUT #5 -12")
    assert err is None
    assert (seq, idx, val) == ("CUT", 5, "-12")


def test_parse_inline_partial_falls_back_to_none():
    # bare command -> prompt for everything
    assert interactive._parse_inline("") == (None, None, None, None)
    assert interactive._parse_inline("   ") == (None, None, None, None)
    # sequence only -> still prompt for index + value
    assert interactive._parse_inline("myseq") == ("myseq", None, None, None)
    # sequence + index -> still prompt for value
    assert interactive._parse_inline("myseq #2") == ("myseq", 2, None, None)


def test_parse_inline_rejects_bad_index():
    # second token must look like #N
    seq, idx, val, err = interactive._parse_inline("myseq 3 newname")
    assert seq is None and idx is None and err is not None and "#N" in err
    seq, idx, val, err = interactive._parse_inline("myseq #abc rest")
    assert idx is None and err is not None and "#N" in err


def test_parse_inline_value_typed_via_parse_value():
    # the parser stays raw; parse_value (the one trust boundary) types it.
    _, _, val, err = interactive._parse_inline("CUT #5 not-a-frame")
    assert err is None and val == "not-a-frame"
    # trim_head is offset-kind -> parse_value rejects the non-integer value
    typed, perr = verbs.parse_value(verbs.REGISTRY["trim_head"], val)
    assert typed is None and "whole number" in perr
    # trailing junk after a valid int is rejected whole (no partial parse)
    _, _, junk, err = interactive._parse_inline("CUT #5 -12 extra")
    assert err is None and junk == "-12 extra"
    typed, perr = verbs.parse_value(verbs.REGISTRY["trim_head"], junk)
    assert typed is None and "whole number" in perr
    # rename accepts the rest-of-line string with spaces
    _, _, name, _ = interactive._parse_inline("myseq #1 New Shot Name")
    typed, perr = verbs.parse_value(verbs.REGISTRY["rename"], name)
    assert typed == "New Shot Name" and perr is None


# -- result-parsing helpers (interactive/one-shot rely on these) --------------


def _res(output=None, status="ok", reason_code=None, message=None):
    return SimpleNamespace(output=output, status=status,
                           reason_code=reason_code, message=message)


def test_held_manifest_picks_apply_counterpart():
    results = {
        "op": _res(output={"deltas": []}),
        "delta_to_manifest": _res(output={"type": "mutation_plan",
                                           "apply_counterpart": {"tool": "x"},
                                           "resolved_plan": [1]}),
    }
    held = interactive._held_manifest(results)
    assert held is not None and held["apply_counterpart"]["tool"] == "x"


def test_node_error_surfaces_non_commit_failure():
    results = {
        "delta_to_manifest": _res(status="error", reason_code="UNRESOLVED_TARGET"),
        "commit": _res(status="error", reason_code="ASSENT_INVALID"),
    }
    err = interactive._node_error(results)
    assert err == ("delta_to_manifest", "UNRESOLVED_TARGET")


def test_commit_applied_detects_applied():
    results = {"commit": _res(output={"type": "commit_applied", "applied": True, "count": 1})}
    out = interactive._commit_applied(results)
    assert out and out["applied"] is True and out["count"] == 1


def test_commit_applied_none_when_absent():
    assert interactive._commit_applied({"x": _res(output={"type": "other"})}) is None


# -- one-shot branching (mocked deps; no daemon/Flame) ------------------------

async def _noop():  # patched _bootstrap
    return None


def test_humanize_maps_known_and_passes_unknown():
    assert "review" in interactive._humanize("HELD_FOR_REVIEW")
    assert interactive._humanize("WEIRD_CODE") == "WEIRD_CODE"
    assert interactive._humanize(None) == "could not complete"


@pytest.mark.asyncio
async def test_oneshot_bad_verb_is_json_and_skips_bootstrap(monkeypatch, capsys):
    async def boom():
        raise AssertionError("bootstrap must not run before the verb check")
    monkeypatch.setattr(interactive, "_bootstrap", boom)
    rc = await interactive.run_oneshot(verb="bogus", sequence="S", segment_name="x",
                                       new_name="y", do_apply=False, as_json=True)
    assert rc == 1
    out = _json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["where"] == "verb"


@pytest.mark.asyncio
async def test_oneshot_same_name_json(monkeypatch, capsys):
    monkeypatch.setattr(interactive, "_bootstrap", _noop)

    async def segs(_seq):
        return [{"seg_name": "x", "track_idx": 0, "record_in": "r", "source_name": "x"}]
    monkeypatch.setattr(interactive, "_segments", segs)
    # unchanged is now checked against the segment's current value (post-fetch)
    rc = await interactive.run_oneshot(verb="rename", sequence="S", segment_name="x",
                                       new_name="x", do_apply=False, as_json=True)
    assert rc == 1
    assert _json.loads(capsys.readouterr().out)["where"] == "input"


@pytest.mark.asyncio
async def test_oneshot_trim_rejects_non_integer(monkeypatch, capsys):
    monkeypatch.setattr(interactive, "_bootstrap", _noop)

    async def segs(_seq):
        return [{"seg_name": "x", "track_idx": 0, "record_in": "r",
                 "record_in_frame": 100, "record_out_frame": 200, "duration": 100,
                 "head": 8, "tail": 8, "source_name": "x"}]
    monkeypatch.setattr(interactive, "_segments", segs)
    rc = await interactive.run_oneshot(verb="trim_head", sequence="S", segment_name="x",
                                       new_name="not-a-frame", do_apply=False, as_json=True)
    assert rc == 1
    out = _json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["where"] == "input"


@pytest.mark.asyncio
async def test_oneshot_trim_over_range_is_legible(monkeypatch, capsys):
    # the UX fix: an impossible trim is rejected with a plain message, NOT the
    # opaque host "couldn't resolve the target" — and never reaches preview.
    monkeypatch.setattr(interactive, "_bootstrap", _noop)

    async def segs(_seq):
        return [{"seg_name": "x", "track_idx": 0, "record_in": "r",
                 "record_in_frame": 100, "record_out_frame": 200, "duration": 100,
                 "head": 8, "tail": 8, "source_name": "x"}]

    async def prev_boom(*a, **k):
        raise AssertionError("range guard must reject before preview")
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive, "_preview_mutation", prev_boom)
    rc = await interactive.run_oneshot(verb="trim_head", sequence="S", segment_name="x",
                                       new_name="800", do_apply=False, as_json=True)
    assert rc == 1
    out = _json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["where"] == "input"
    assert "can't trim 800 off a 100-frame segment" in out["why"]


@pytest.mark.asyncio
async def test_oneshot_bad_sequence_vs_missing_segment(monkeypatch, capsys):
    monkeypatch.setattr(interactive, "_bootstrap", _noop)

    async def empty(_seq):
        return []
    monkeypatch.setattr(interactive, "_segments", empty)
    rc = await interactive.run_oneshot(verb="rename", sequence="NOPE", segment_name="x",
                                       new_name="y", do_apply=False, as_json=True)
    assert rc == 1
    assert _json.loads(capsys.readouterr().out)["where"] == "sequence"

    async def one(_seq):
        return [{"seg_name": "other", "track_idx": 0, "record_in": "r", "source_name": "o"}]
    monkeypatch.setattr(interactive, "_segments", one)
    rc = await interactive.run_oneshot(verb="rename", sequence="S", segment_name="x",
                                       new_name="y", do_apply=False, as_json=True)
    assert rc == 1
    assert _json.loads(capsys.readouterr().out)["where"] == "select"


@pytest.mark.asyncio
async def test_oneshot_preview_json_pure(monkeypatch, capsys):
    monkeypatch.setattr(interactive, "_bootstrap", _noop)

    async def segs(_seq):
        return [{"seg_name": "x", "track_idx": 0, "record_in": "r", "source_name": "x"}]

    async def prev(_verb, _sequence, _seg, _values):
        return ({"apply_counterpart": {"tool": "forge_apply_segment_delta"},
                 "resolved_plan": [1]}, None)
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive, "_preview_mutation", prev)
    rc = await interactive.run_oneshot(verb="rename", sequence="S", segment_name="x",
                                       new_name="y", do_apply=False, as_json=True)
    assert rc == 0
    out = _json.loads(capsys.readouterr().out)
    assert out["ok"] and out["preview"]
    assert out["manifest"]["apply_counterpart"]["tool"] == "forge_apply_segment_delta"


@pytest.mark.asyncio
async def test_apply_held_surfaces_commit_drift(monkeypatch):
    import forge_bridge.orchestration.apply_editorial_delta as mod

    async def fake_apply(_spec, *, assent_record):
        return {"commit": _res(status="error", reason_code="PLAN_STATE_DRIFT")}
    monkeypatch.setattr(mod, "apply_editorial_delta", fake_apply)
    monkeypatch.setattr(mod, "graph_replay_commit_spec", lambda h: None)
    monkeypatch.setattr(interactive, "_ratified_assent", lambda: object())
    ok, msg = await interactive._apply_held({"apply_counterpart": {}})
    assert ok is False and "timeline changed" in msg  # humanized, not masked


@pytest.mark.asyncio
async def test_apply_held_success(monkeypatch):
    import forge_bridge.orchestration.apply_editorial_delta as mod

    async def fake_apply(_spec, *, assent_record):
        return {"commit": _res(output={"type": "commit_applied", "applied": True, "count": 1})}
    monkeypatch.setattr(mod, "apply_editorial_delta", fake_apply)
    monkeypatch.setattr(mod, "graph_replay_commit_spec", lambda h: None)
    monkeypatch.setattr(interactive, "_ratified_assent", lambda: object())
    ok, msg = await interactive._apply_held({})
    assert ok and "applied" in msg


# -- stage-for-ratification (the [s] path) ------------------------------------


def test_build_mutation_spec_is_canonical_author():
    # the one spec author both preview and stage use — proves single representation
    spec = interactive._build_mutation_spec(
        verbs.REGISTRY["rename"], "CUT", _fake_seg(), {"new_name": "shot_010_v2"})
    assert [n.node_id for n in spec.nodes] == ["op", "delta_to_manifest"]
    delta = spec.nodes[0].config["arguments"]["delta"]
    assert (delta.get("changes") or delta.get("entries"))[0]["after"]["name"] == "shot_010_v2"


@pytest.mark.asyncio
async def test_stage_mutation_persists_canonical_spec(monkeypatch):
    import forge_bridge.orchestration.apply_editorial_delta as mod
    import forge_bridge.store.session as sess

    captured = {}

    async def fake_producer(spec, *, session_factory, display):
        captured["spec"] = spec
        captured["display"] = display
        captured["session_factory"] = session_factory
        return {"graph_intent_id": "deadbeef1234"}
    monkeypatch.setattr(mod, "preview_editorial_delta_for_ratification", fake_producer)
    monkeypatch.setattr(sess, "get_async_session_factory", lambda: "SF")

    gid = await interactive._stage_mutation(
        verbs.REGISTRY["rename"], "CUT", _fake_seg(), {"new_name": "shot_010_v2"},
        display="rename shot_010 -> shot_010_v2")
    assert gid == "deadbeef1234"
    assert captured["session_factory"] == "SF"
    # persisted spec is the SAME canonical author the preview uses (one representation)
    spec = captured["spec"]
    assert [n.node_id for n in spec.nodes] == ["op", "delta_to_manifest"]
    delta = spec.nodes[0].config["arguments"]["delta"]
    assert (delta.get("changes") or delta.get("entries"))[0]["after"]["name"] == "shot_010_v2"


# -- interactive y/s/n branching (mocked; no daemon/Flame/DB) -----------------


class _FakeCon:
    def __init__(self):
        self.lines: list[str] = []

    def print(self, *a, **k):
        self.lines.append(" ".join(str(x) for x in a))


def _wire_run_verb(monkeypatch, *, choice):
    """Stub _segments/_preview_mutation and the y/s/n prompt for _run_verb tests."""
    async def segs(_seq):
        return [{"seg_name": "shot_010", "track_idx": 0, "record_in": "r",
                 "record_in_frame": 100, "source_name": "shot_010"}]

    async def prev(_verb, _seq, _seg, _values):
        return ({"apply_counterpart": {}, "resolved_plan": [1]}, None)
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive, "_preview_mutation", prev)
    monkeypatch.setattr(interactive.Prompt, "ask", lambda *a, **k: choice)


@pytest.mark.asyncio
async def test_run_verb_stage_branch(monkeypatch):
    con = _FakeCon()
    _wire_run_verb(monkeypatch, choice="s")
    staged = {}

    async def stage(verb, sequence, seg, values, *, display):
        staged["args"] = (verb.name, sequence, seg["seg_name"], values, display)
        return "abc123def456"

    async def apply_boom(_held):
        raise AssertionError("apply must not run on [s]")
    monkeypatch.setattr(interactive, "_stage_mutation", stage)
    monkeypatch.setattr(interactive, "_apply_held", apply_boom)

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"],
                                sequence="CUT", seg_index=1, value_raw="shot_010_v2")
    assert staged["args"][0] == "rename"
    assert staged["args"][3] == {"new_name": "shot_010_v2"}
    blob = "\n".join(con.lines)
    assert "abc123def456" in blob and "fbridge ratify" in blob
    assert "nothing applied yet" in blob


@pytest.mark.asyncio
async def test_run_verb_apply_branch(monkeypatch):
    con = _FakeCon()
    _wire_run_verb(monkeypatch, choice="y")
    applied = {}

    async def apply(held):
        applied["held"] = held
        return True, "1 applied"

    async def stage_boom(*a, **k):
        raise AssertionError("stage must not run on [y]")
    monkeypatch.setattr(interactive, "_apply_held", apply)
    monkeypatch.setattr(interactive, "_stage_mutation", stage_boom)

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"],
                                sequence="CUT", seg_index=1, value_raw="shot_010_v2")
    assert applied["held"] is not None
    assert any("enacted in Flame" in line for line in con.lines)


@pytest.mark.asyncio
async def test_run_verb_cancel_branch(monkeypatch):
    con = _FakeCon()
    _wire_run_verb(monkeypatch, choice="n")

    async def boom(*a, **k):
        raise AssertionError("neither apply nor stage may run on [n]")
    monkeypatch.setattr(interactive, "_apply_held", boom)
    monkeypatch.setattr(interactive, "_stage_mutation", boom)

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"],
                                sequence="CUT", seg_index=1, value_raw="shot_010_v2")
    assert any("not applied" in line for line in con.lines)
