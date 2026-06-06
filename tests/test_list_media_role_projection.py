"""Regression: forge_list_media must surface the media `role` from the wire.

`entity_list` returns entities as `to_dict()` — open attributes ride under the
`metadata` key (with the media role inside), typed fields at top level. The
projection historically read `m.get("attributes")` (wrong key) and projected
`kind` (wrong field), so `role` never surfaced. This locks the corrected
projection: role is read from `metadata`, exposed as a `role` field, and the
`kind` filter matches the media-role vocabulary.
"""

import asyncio
import json

import pytest

import forge_bridge.mcp.tools as fbt
from forge_bridge.mcp.tools import list_media, ListMediaInput


class _FakeClient:
    """Returns entity_list-shaped (to_dict) media for any request."""

    def __init__(self, media):
        self._media = media

    async def request(self, msg, timeout=None):
        return {"entities": self._media}


# to_dict wire shape for a render media: open dict under `metadata`,
# typed fields at top level (as Media.to_dict emits them).
_RENDER_MEDIA = {
    "id": "15138e75-914a-44f2-b987-a7eba256530a",
    "entity_type": "media",
    "metadata": {"role": "render"},
    "format": "EXR",
    "resolution": None,
    "locations": [],
    "relationships": [],
}
_RAW_MEDIA = {
    "id": "28e6dfac-77aa-43ba-89d3-fcf0b411bc97",
    "entity_type": "media",
    "metadata": {"role": "raw"},
    "format": "EXR",
    "resolution": None,
    "locations": [],
    "relationships": [],
}


def _run(media, **params):
    client = _FakeClient(media)
    orig = fbt._client
    fbt._client = lambda: client
    try:
        out = asyncio.run(list_media(ListMediaInput(project_id="p", **params)))
    finally:
        fbt._client = orig
    return json.loads(out)


def test_role_surfaces_in_projection():
    data = _run([_RENDER_MEDIA, _RAW_MEDIA])
    by_id = {r["media_id"]: r for r in data["media"]}
    assert by_id["15138e75-914a-44f2-b987-a7eba256530a"]["role"] == "render"
    assert by_id["28e6dfac-77aa-43ba-89d3-fcf0b411bc97"]["role"] == "raw"


def test_kind_filter_matches_media_role():
    """`kind` param filters on the media-role vocabulary (kind == role)."""
    data = _run([_RENDER_MEDIA, _RAW_MEDIA], kind="render")
    assert data["count"] == 1
    assert data["media"][0]["role"] == "render"


def test_legacy_attributes_key_still_read():
    """Back-compat: media carrying the open dict under `attributes` still works."""
    legacy = {**_RENDER_MEDIA}
    legacy.pop("metadata")
    legacy["attributes"] = {"role": "render"}
    data = _run([legacy])
    assert data["media"][0]["role"] == "render"
