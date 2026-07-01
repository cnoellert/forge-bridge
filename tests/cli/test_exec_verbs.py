"""Pure unit tests for the fbridge exec verb registry + result helpers.

No daemon, no Flame, no DB — just the deterministic spec-building and the
result-parsing helpers the interactive/one-shot renderers rely on.
"""
from __future__ import annotations

import json as _json
from pathlib import Path
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
    # the one spec author both preview and stage use — proves single representation.
    # DUAL-PATH cutover: a counter-free LITERAL rename is now GRAPH-authored
    # (literal_source -> foreach -> collect -> host_resolve -> delta_to_manifest);
    # the rename template rides the foreach body config, not a hand-built delta.
    spec = interactive._build_mutation_spec(
        verbs.REGISTRY["rename"], "CUT", _fake_seg(), {"new_name": "shot_010_v2"})
    assert [n.node_id for n in spec.nodes] == [
        "segments", "foreach", "collect", "host_resolve", "delta_to_manifest"]
    body = spec.nodes[1].config["body"]
    assert body.operator_id == "rename_delta_entry"
    assert body.config["new_name"] == "shot_010_v2"


def test_build_mutation_spec_counter_stays_on_cli_rail():
    # The order-sensitive $n counter rename stays on the proven CLI hand-build
    # rail — the graph rename path is literal-rename only (order-agnostic).
    counter = interactive._build_mutation_spec(
        verbs.REGISTRY["rename"], "CUT", _fake_seg(), {"new_name": "shot_$n{3,10,10}"})
    assert [n.node_id for n in counter.nodes] == ["op", "delta_to_manifest"]


def test_build_mutation_spec_trim_is_graph_authored():
    # DUAL-PATH cutover: a relative trim is now GRAPH-authored
    # (literal_source -> foreach(trim_delta_entry) -> collect -> host_resolve ->
    # delta_to_manifest), order-agnostic like the literal rename. The offset +
    # trim_side ride the foreach body config, not a hand-built delta.
    for side, verb in (("head", "trim_head"), ("tail", "trim_tail")):
        trim = interactive._build_mutation_spec(
            verbs.REGISTRY[verb], "CUT", _fake_seg(), {"count": 12})
        assert [n.node_id for n in trim.nodes] == [
            "segments", "foreach", "collect", "host_resolve", "delta_to_manifest"]
        body = trim.nodes[1].config["body"]
        assert body.operator_id == "trim_delta_entry"
        assert body.config["count"] == 12
        assert body.config["trim_side"] == side
        # THE FINDING: trim rides the SAME host_resolve operator as rename; the
        # temporal executor is selected from the delta content downstream.
        host_resolve = trim.nodes[3]
        assert host_resolve.operator_id == verbs.host_resolve_operator()


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
    # persisted spec is the SAME canonical author the preview uses (one
    # representation) — a literal rename is GRAPH-authored (dual-path cutover).
    spec = captured["spec"]
    assert [n.node_id for n in spec.nodes] == [
        "segments", "foreach", "collect", "host_resolve", "delta_to_manifest"]
    body = spec.nodes[1].config["body"]
    assert body.operator_id == "rename_delta_entry"
    assert body.config["new_name"] == "shot_010_v2"


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


# -- slash-command completion + did-you-mean (pure, registry-driven) ----------


def test_command_completions_prefix_matches():
    # the orphaned "/trim" (post-#128) now resolves to both trim verbs
    assert interactive._command_completions("/tr") == ["/trim_head", "/trim_tail"]
    assert interactive._command_completions("/re") == ["/rename"]
    # leading slash optional; case-insensitive
    assert interactive._command_completions("RE") == ["/rename"]


def test_command_completions_bare_slash_returns_all():
    allcmds = interactive._command_completions("/")
    # every registry verb + the meta-commands, all slash-prefixed and sorted
    for v in verbs.list_verbs():
        assert f"/{v.name}" in allcmds
    for meta in interactive._META_COMMANDS:
        assert f"/{meta}" in allcmds
    assert allcmds == sorted(allcmds)
    assert interactive._command_completions("") == allcmds  # empty == bare slash


def test_command_completions_unknown_is_empty():
    assert interactive._command_completions("/xyz") == []


def test_command_completions_is_registry_driven(monkeypatch):
    # a hypothetical newly-registered verb auto-appears (no hard-coded list)
    extra = verbs.Verb(
        name="zaprooni", label="Zap", summary="hypothetical verb",
        build_delta=lambda values: {}, value_field="v", value_kind="str",
        value_label="V", current_key="seg_name",
    )
    monkeypatch.setitem(verbs.REGISTRY, "zaprooni", extra)
    assert interactive._command_completions("/za") == ["/zaprooni"]


def test_did_you_mean_fires_on_near_miss_not_exact():
    # /trim is a prefix of two verbs -> a legible hint
    assert interactive._did_you_mean("trim") == ["/trim_head", "/trim_tail"]
    # an exact command is excluded (it would be dispatched, never hinted)
    assert interactive._did_you_mean("rename") == []
    # a true miss yields nothing -> caller falls back to the bland unknown line
    assert interactive._did_you_mean("xyz") == []


# -- inline-arg END-TO-END through _run_verb for the trim verbs ----------------
# (the parser is tested above; these prove the *dispatch* path: a signed inline
#  offset survives into the verb, and the range guard fires on the inline route.)


def _trim_seg() -> dict:
    return {"seg_name": "shot_010", "track_idx": 0, "record_in": "r",
            "record_in_frame": 100, "record_out_frame": 200, "duration": 100,
            "head": 8, "tail": 8, "source_name": "shot_010"}


@pytest.mark.asyncio
async def test_run_verb_inline_signed_offset_reaches_verb(monkeypatch):
    # /trim_head CUT #1 -5 : the negative offset must survive inline -> parse_value
    # -> preview with {"count": -5} (it is NOT mangled into a positive / absolute).
    con = _FakeCon()
    captured = {}

    async def segs(_seq):
        return [_trim_seg()]

    async def prev(_verb, _seq, _seg, values):
        captured["values"] = values
        return ({"apply_counterpart": {}, "resolved_plan": [1]}, None)

    async def apply(_held):
        return True, "1 applied"
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive, "_preview_mutation", prev)
    monkeypatch.setattr(interactive, "_apply_held", apply)
    monkeypatch.setattr(interactive.Prompt, "ask", lambda *a, **k: "y")

    await interactive._run_verb(con, verb=verbs.REGISTRY["trim_head"],
                                sequence="CUT", seg_index=1, value_raw="-5")
    assert captured["values"] == {"count": -5}  # signed, intact
    assert any("enacted in Flame" in line for line in con.lines)


@pytest.mark.asyncio
async def test_run_verb_inline_trim_range_guard_fires(monkeypatch):
    # /trim_head CUT #1 800 : the CLI-side range guard (validate_trim) must reject
    # an impossible trim on the INLINE path too — legible message, never reaches preview.
    con = _FakeCon()

    async def segs(_seq):
        return [_trim_seg()]

    async def prev_boom(*a, **k):
        raise AssertionError("range guard must reject before preview on the inline path")
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive, "_preview_mutation", prev_boom)

    await interactive._run_verb(con, verb=verbs.REGISTRY["trim_head"],
                                sequence="CUT", seg_index=1, value_raw="800")
    blob = "\n".join(con.lines)
    assert "can't trim 800 off a 100-frame segment" in blob


# -- persistent REPL command history (stdlib readline; guarded, no-dep) --------


def test_history_path_under_forge_bridge_home():
    # reuses the per-machine ~/.forge-bridge/ runtime convention
    assert interactive._history_path() == Path.home() / ".forge-bridge" / "exec_history"


def test_load_history_noop_without_readline():
    interactive._load_history(None)  # readline unavailable -> silent no-op


def test_load_history_missing_file_is_clean_noop(tmp_path, monkeypatch):
    # no history file yet -> read raises FileNotFoundError -> swallowed; length still set.
    monkeypatch.setattr(interactive, "_history_path",
                        lambda: tmp_path / "nope" / "exec_history")
    seen = {}

    class _RL:
        def read_history_file(self, p):
            raise FileNotFoundError(p)

        def set_history_length(self, n):
            seen["len"] = n

    interactive._load_history(_RL())  # must not raise
    assert seen["len"] == 1000


def test_save_history_noop_without_readline():
    interactive._save_history(None)  # silent no-op


def test_save_history_writes_and_creates_dir(tmp_path, monkeypatch):
    hist = tmp_path / "sub" / "exec_history"  # parent does NOT exist yet
    monkeypatch.setattr(interactive, "_history_path", lambda: hist)
    written = {}

    class _RL:
        def write_history_file(self, p):
            written["path"] = p

    interactive._save_history(_RL())
    assert written["path"] == str(hist)
    assert hist.parent.is_dir()  # the ~/.forge-bridge/ dir is created on demand


def test_save_history_swallows_oserror(tmp_path, monkeypatch):
    # a locked / read-only home must never crash the REPL on exit
    monkeypatch.setattr(interactive, "_history_path", lambda: tmp_path / "h")

    class _RL:
        def write_history_file(self, p):
            raise OSError("read-only filesystem")

    interactive._save_history(_RL())  # must not raise


# -- bare /verb sequence auto-resolution off the live desktop ------------------
# (the typed-identity usability fix: no Prompt.ask("Sequence") when the desktop
#  can resolve it; falls back cleanly on a read failure so nothing regresses.)


def _wire_resolve(monkeypatch, *, desktop):
    """Stub _desktop_sequences + the rest of _run_verb so the SEQUENCE-resolution
    branch is the only live logic. Records whether Prompt.ask ever fired."""
    async def desk():
        return desktop
    monkeypatch.setattr(interactive, "_desktop_sequences", desk)

    async def segs(_seq):
        return [{"seg_name": "shot_010", "track_idx": 0, "record_in": "r",
                 "record_in_frame": 100, "source_name": "shot_010"}]

    async def prev(_verb, _seq, _seg, _values):
        return ({"apply_counterpart": {}, "resolved_plan": [1]}, None)
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive, "_preview_mutation", prev)


@pytest.mark.asyncio
async def test_run_verb_resolve_single_sequence_no_prompt(monkeypatch):
    # exactly 1 open sequence -> used silently, the "Sequence" prompt NEVER fires.
    con = _FakeCon()
    _wire_resolve(monkeypatch, desktop=["the_only_seq"])
    used = {}

    async def segs(seq):
        used["seq"] = seq
        return [{"seg_name": "shot_010", "track_idx": 0, "record_in": "r",
                 "record_in_frame": 100, "source_name": "shot_010"}]
    monkeypatch.setattr(interactive, "_segments", segs)

    def boom(*a, **k):
        raise AssertionError("must not prompt for a sequence when exactly one is open")
    monkeypatch.setattr(interactive.Prompt, "ask", boom)
    # auto-decline at the y/s/n gate via IntPrompt-free path: stub apply/stage off
    async def apply(_held):
        return True, "1 applied"
    monkeypatch.setattr(interactive, "_apply_held", apply)
    # the only Prompt.ask in the happy path after resolution is the y/s/n choice;
    # we replaced Prompt.ask wholesale with boom, so feed the choice via IntPrompt?
    # Instead, cancel cleanly: stub the y/s/n by re-permitting Prompt only for it.
    # Simplest: seg_index + value supplied, choice forced through a narrow stub.
    monkeypatch.setattr(interactive, "_stage_mutation",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no stage")))

    # Provide seg_index + value so only the y/s/n Prompt remains — but Prompt is
    # boom. Re-stub Prompt.ask to answer ONLY the choice and assert no Sequence ask.
    asked = []

    def choice_only(prompt="", *a, **k):
        asked.append(str(prompt))
        return "y"
    monkeypatch.setattr(interactive.Prompt, "ask", choice_only)

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"],
                                seg_index=1, value_raw="shot_010_v2")
    assert used["seq"] == "the_only_seq"
    # the only Prompt.ask was the y/s/n gate, never a "Sequence" prompt
    assert not any("Sequence" in p for p in asked)
    assert any("using the open sequence" in line for line in con.lines)


@pytest.mark.asyncio
async def test_run_verb_resolve_multi_sequence_int_pick(monkeypatch):
    # >1 open -> list names + IntPrompt pick (2nd one chosen here).
    con = _FakeCon()
    _wire_resolve(monkeypatch, desktop=["seq_a", "seq_b", "seq_c"])
    used = {}

    async def segs(seq):
        used["seq"] = seq
        return [{"seg_name": "shot_010", "track_idx": 0, "record_in": "r",
                 "record_in_frame": 100, "source_name": "shot_010"}]
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive.IntPrompt, "ask", lambda *a, **k: 2)
    monkeypatch.setattr(interactive.Prompt, "ask", lambda *a, **k: "n")  # cancel at gate

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"],
                                seg_index=1, value_raw="shot_010_v2")
    assert used["seq"] == "seq_b"
    blob = "\n".join(con.lines)
    assert "Open sequences" in blob and "seq_a" in blob and "seq_c" in blob


@pytest.mark.asyncio
async def test_run_verb_resolve_zero_sequence_early_return(monkeypatch):
    # 0 open -> "no sequence open" message + early return (no segment read).
    con = _FakeCon()

    async def desk():
        return []
    monkeypatch.setattr(interactive, "_desktop_sequences", desk)

    async def segs_boom(_seq):
        raise AssertionError("must not read segments when no sequence is open")
    monkeypatch.setattr(interactive, "_segments", segs_boom)

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"], seg_index=1,
                                value_raw="x")
    assert any("no sequence open" in line for line in con.lines)


@pytest.mark.asyncio
async def test_run_verb_resolve_read_failure_falls_back_to_prompt(monkeypatch):
    # _desktop_sequences -> None (Flame unreachable) -> original typed prompt.
    con = _FakeCon()

    async def desk():
        return None
    monkeypatch.setattr(interactive, "_desktop_sequences", desk)
    used = {}

    async def segs(seq):
        used["seq"] = seq
        return [{"seg_name": "shot_010", "track_idx": 0, "record_in": "r",
                 "record_in_frame": 100, "source_name": "shot_010"}]
    monkeypatch.setattr(interactive, "_segments", segs)

    asked = []

    def prompt(p="", *a, **k):
        asked.append(str(p))
        # first ask is the Sequence fallback; then the y/s/n gate -> cancel
        return "typed_seq" if "Sequence" in str(p) else "n"
    monkeypatch.setattr(interactive.Prompt, "ask", prompt)

    async def prev(_verb, _seq, _seg, _values):
        return ({"apply_counterpart": {}, "resolved_plan": [1]}, None)
    monkeypatch.setattr(interactive, "_preview_mutation", prev)

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"], seg_index=1,
                                value_raw="shot_010_v2")
    assert used["seq"] == "typed_seq"  # fell back to the typed prompt
    assert any("Sequence" in p for p in asked)


@pytest.mark.asyncio
async def test_run_verb_explicit_sequence_skips_resolution(monkeypatch):
    # an explicit sequence= (inline-args path) must NEVER hit _desktop_sequences.
    con = _FakeCon()

    async def desk_boom():
        raise AssertionError("explicit sequence must not trigger desktop resolution")
    monkeypatch.setattr(interactive, "_desktop_sequences", desk_boom)
    _wire_run_verb(monkeypatch, choice="n")

    await interactive._run_verb(con, verb=verbs.REGISTRY["rename"],
                                sequence="EXPLICIT", seg_index=1, value_raw="shot_010_v2")
    assert any("not applied" in line for line in con.lines)


@pytest.mark.asyncio
async def test_desktop_sequences_distinguishes_empty_from_failure(monkeypatch):
    import forge_bridge.bridge as br
    # success-but-zero -> [] ; read failure (raises) -> None
    async def ok_empty(_code, **k):
        return []
    monkeypatch.setattr(br, "execute_json", ok_empty)
    assert await interactive._desktop_sequences() == []

    async def ok_names(_code, **k):
        return ["a", "b"]
    monkeypatch.setattr(br, "execute_json", ok_names)
    assert await interactive._desktop_sequences() == ["a", "b"]

    async def boom(_code, **k):
        raise br.BridgeConnectionError("Flame down")
    monkeypatch.setattr(br, "execute_json", boom)
    assert await interactive._desktop_sequences() is None
