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


# Wire-shape segment dict mirrors flame_get_sequence_segments output: the verb's
# current_key for rename is "seg_name" and for trim "record_in_frame".
_SEG = {
    "seg_name": "shot_010",
    "track_idx": 1,
    "record_in": "01:00:00:00",
    "record_in_frame": 100,
    "source_name": "src_010",
}


def test_actions_list_renders_registry_verbs(client):
    r = client.get("/ui/actions")
    assert r.status_code == 200
    # both registered verbs surface as cards
    assert "/ui/actions/rename" in r.text
    assert "/ui/actions/trim" in r.text
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


def test_preview_rejects_bad_int_for_trim(client):
    # trim is value_kind=int — a non-int must be rejected at the trust boundary,
    # before any preview/mutation call.
    preview = AsyncMock()
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.cli.interactive._preview_mutation", new=preview):
        r = client.post(
            "/ui/actions/trim/preview",
            data={"sequence": "seq01", "segment_index": "1", "value": "notanumber"},
        )
    assert r.status_code == 400
    assert "whole number" in r.text
    preview.assert_not_awaited()


def test_preview_rejects_negative_for_trim(client):
    preview = AsyncMock()
    with patch("forge_bridge.cli.interactive._segments",
               new=AsyncMock(return_value=[_SEG])), \
         patch("forge_bridge.cli.interactive._preview_mutation", new=preview):
        r = client.post(
            "/ui/actions/trim/preview",
            data={"sequence": "seq01", "segment_index": "1", "value": "-5"},
        )
    assert r.status_code == 400
    assert "0 or greater" in r.text
    preview.assert_not_awaited()


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
