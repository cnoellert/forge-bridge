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


# -- result-parsing helpers (interactive/one-shot rely on these) --------------

from forge_bridge.cli import interactive  # noqa: E402


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
    rc = await interactive.run_oneshot(verb="rename", sequence="S", segment_name="x",
                                       new_name="x", do_apply=False, as_json=True)
    assert rc == 1
    assert _json.loads(capsys.readouterr().out)["where"] == "input"


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

    async def prev(_sequence, _seg, _new):
        return ({"apply_counterpart": {"tool": "forge_apply_segment_delta"},
                 "resolved_plan": [1]}, None)
    monkeypatch.setattr(interactive, "_segments", segs)
    monkeypatch.setattr(interactive, "_preview_rename", prev)
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
    assert ok and "renamed" in msg
