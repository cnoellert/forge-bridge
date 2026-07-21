"""Actions view — renderer #2 of the fbridge exec verb registry.

Covers: the view lists REGISTRY verbs; the segment picker renders live segments
and degrades gracefully when the timeline fetch fails; the preview endpoint
returns the domain preview for a mocked segment; value validation rejects bad
input (the trust boundary); the stage endpoint calls the producer and returns a
graph_intent_id with the CA.1 ratify handoff. The live-timeline fetch and the
stage producer are mocked — no real daemon/DB.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client():
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.read_api import ConsoleReadAPI

    api = MagicMock(spec=ConsoleReadAPI)
    api.get_tools = AsyncMock(return_value=[])
    api.get_executions = AsyncMock(return_value=([], 0))
    api.get_manifest = AsyncMock(return_value={"tools": []})
    api.get_health = AsyncMock(return_value={
        "status": "ok", "services": {}, "instance_identity": {},
    })
    # session_factory present so the stage path is reachable (its DB call is mocked)
    app = build_console_app(api, session_factory=MagicMock())
    return TestClient(app)


# Wire-shape segment dict mirrors flame_get_sequence_segments output: rename's
# current_key is "seg_name"; trim_head/trim_tail are value_kind="offset" (a SIGNED
# relative frame count) and key off record_in_frame/record_out_frame. validate_trim
# reads duration + the head/tail handle to range-guard a relative trim.
_SEG = {
    "seg_name": "shot_010",
    "track_idx": 1,
    "record_in": "01:00:00:00",
    "record_in_frame": 100,
    "record_out_frame": 148,
    "source_name": "src_010",
    "duration": 48,
    "head": 5,
    "tail": 5,
}


def test_actions_list_renders_registry_verbs(client):
    r = client.get("/ui/actions")
    assert r.status_code == 200
    # all registered verbs surface as cards (rename + the two relative-trim verbs)
    assert "/ui/actions/rename" in r.text
    assert "/ui/actions/trim_head" in r.text
    assert "/ui/actions/trim_tail" in r.text
    assert "Rename a segment" in r.text


def test_actions_form_renders(client):
    r = client.get("/ui/actions/rename")
    assert r.status_code == 200
    assert 'name="sequence"' in r.text
    assert "Load segments" in r.text


def test_actions_form_unknown_verb_404_not_blank(client):
    r = client.get("/ui/actions/nope")
    assert r.status_code == 404
    assert "No action named" in r.text


def test_segments_fragment_lists_live_segments(client):
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])):
        r = client.get("/ui/fragments/actions-segments?verb=rename&sequence=seq01")
    assert r.status_code == 200
    assert 'name="segment_index"' in r.text
    assert "shot_010" in r.text


def test_segments_fragment_degrades_when_timeline_unreachable(client):
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(side_effect=RuntimeError("flame down"))):
        r = client.get("/ui/fragments/actions-segments?verb=rename&sequence=seq01")
    # de-blank guard: a clear message, never a blank page or a traceback
    assert r.status_code == 200
    assert "Could not reach the live timeline" in r.text
    assert "Traceback" not in r.text


def test_segments_fragment_empty_timeline_message(client):
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[])):
        r = client.get("/ui/fragments/actions-segments?verb=rename&sequence=seq01")
    assert r.status_code == 200
    assert "No segments found" in r.text


def test_preview_returns_domain_language(client):
    held = {"resolved_plan": [{"x": 1}]}
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.cli.interactive._preview_mutation",
               new=AsyncMock(return_value=(held, None))):
        r = client.post(
            "/ui/actions/rename/preview",
            data={"sequence": "seq01", "segment_index": "1", "value": "shot_999"},
        )
    assert r.status_code == 200
    assert "shot_010" in r.text          # the targeted segment
    assert "shot_999" in r.text          # the new value
    assert "Stage for ratification" in r.text
    assert "nothing applied" in r.text.lower()


@pytest.mark.parametrize("verb_name", ["trim_head", "trim_tail"])
def test_trim_verbs_render_as_number_inputs(client, verb_name):
    # offset verbs (trim_head/trim_tail) must render a number input — and must NOT
    # be floored at min=0, because a negative offset is a valid "extend".
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])):
        r = client.get(
            f"/ui/fragments/actions-segments?verb={verb_name}&sequence=seq01"
        )
    assert r.status_code == 200
    assert 'type="number"' in r.text
    assert 'step="1"' in r.text
    # negatives allowed (extend) → never a min floor for an offset verb
    assert 'min="0"' not in r.text


def test_preview_rejects_non_numeric_offset(client):
    # offset is numeric — a non-number is rejected at the trust boundary, before
    # any preview/mutation call.
    preview = AsyncMock()
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.cli.interactive._preview_mutation", new=preview):
        r = client.post(
            "/ui/actions/trim_head/preview",
            data={"sequence": "seq01", "segment_index": "1", "value": "notanumber"},
        )
    assert r.status_code == 400
    assert "whole number" in r.text
    preview.assert_not_awaited()


def test_preview_rejects_out_of_range_trim(client):
    # validate_trim guard: trimming >= the segment duration collapses it. The
    # legible reason must surface (not the opaque host failure) and the preview
    # mutation must never be reached.
    preview = AsyncMock()
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.cli.interactive._preview_mutation", new=preview):
        r = client.post(
            "/ui/actions/trim_head/preview",
            data={"sequence": "seq01", "segment_index": "1", "value": "50"},
        )
    assert r.status_code == 400
    # _SEG duration is 48 → trimming 50 is impossible (apostrophe is HTML-escaped)
    assert "trim 50 off a 48-frame segment" in r.text
    preview.assert_not_awaited()


def test_preview_rejects_over_extend_trim(client):
    # validate_trim guard: extending (negative offset) beyond the available handle
    # is impossible. _SEG head handle is 5; extending by 10 must be rejected.
    preview = AsyncMock()
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.cli.interactive._preview_mutation", new=preview):
        r = client.post(
            "/ui/actions/trim_head/preview",
            data={"sequence": "seq01", "segment_index": "1", "value": "-10"},
        )
    assert r.status_code == 400
    # apostrophe is HTML-escaped in the rendered fragment
    assert "extend the head by 10" in r.text
    assert "only 5 frames of handle available" in r.text
    preview.assert_not_awaited()


def test_preview_valid_offset_trim_uses_describe_change(client):
    # a valid in-range offset trim previews with the artist-legible describe_change
    # wording — and NEVER leaks an absolute timeline frame (the in-point 100 nor
    # the resulting after-frame 110).
    held = {"resolved_plan": [{"x": 1}]}
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.cli.interactive._preview_mutation",
               new=AsyncMock(return_value=(held, None))):
        r = client.post(
            "/ui/actions/trim_head/preview",
            data={"sequence": "seq01", "segment_index": "1", "value": "10"},
        )
    assert r.status_code == 200
    assert "trim 10 frames off the head" in r.text
    assert "Stage for ratification" in r.text
    # no absolute frame leaks into the preview
    assert "100" not in r.text
    assert "110" not in r.text


def test_stage_calls_producer_and_returns_graph_intent_id(client):
    staged = {"graph_intent_id": "abc123def456"}
    producer = AsyncMock(return_value=staged)
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.orchestration.apply_editorial_delta."
               "preview_editorial_delta_for_ratification", new=producer):
        r = client.post(
            "/ui/actions/rename/stage",
            data={"sequence": "seq01", "segment_index": "1", "value": "shot_999"},
        )
    assert r.status_code == 200
    producer.assert_awaited_once()
    # the producer was handed the canonical spec + the app session_factory
    assert producer.await_args.kwargs["session_factory"] is not None
    # CA.1 handoff: graph_intent_id + the fbridge ratify command + Chat link
    assert "abc123def456" in r.text
    assert "fbridge ratify abc123def456" in r.text
    assert "/ui/chat" in r.text
    assert "nothing applied" in r.text.lower()


def test_stage_unavailable_without_session_factory():
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.read_api import ConsoleReadAPI

    api = MagicMock(spec=ConsoleReadAPI)
    api.get_health = AsyncMock(return_value={
        "status": "ok", "services": {}, "instance_identity": {},
    })
    app = build_console_app(api, session_factory=None)
    c = TestClient(app)
    r = c.post(
        "/ui/actions/rename/stage",
        data={"sequence": "seq01", "segment_index": "1", "value": "shot_999"},
    )
    assert r.status_code == 200
    assert "Staging is unavailable" in r.text
