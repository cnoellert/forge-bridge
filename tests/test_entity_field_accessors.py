"""Wire-shape sweep (tier 2): entity read-layer correctness.

`entity_list`/`entity_get` return to_dict shape — typed fields at the top level,
open/pipeline attributes under `metadata`. Read sites historically used a
top-level `attributes` key that to_dict never emits, so every projected field
came back empty. These tests lock the shared accessors and prove a representative
read tool (`list_versions`) behaves correctly when versions ARE linked — the
filter that previously matched nothing now matches the linked version.

NOTE: in live data versions currently carry NO shot linkage (no parent_id, no
version_of edge) — see the separately-tracked version ownership/linkage gap.
These tests use properly-linked fixtures: the read path is correct; the absent
production linkage is a distinct producer/data-model concern.
"""

import asyncio
import json

from forge_bridge.mcp.tools import (
    GetShotLineageInput,
    GetShotVersionsInput,
    ListPublishedPlatesInput,
    ListVersionsInput,
    _attr,
    _entity_fields,
    get_shot_lineage,
    get_shot_versions,
    list_published_plates,
    list_versions,
)
import forge_bridge.mcp.tools as fbt
from forge_bridge.server.protocol import MsgType


# ── pure accessor coverage ───────────────────────────────────────────────

def test_attr_reads_typed_top_level():
    e = {"id": "x", "version_number": 3, "metadata": {}}
    assert _attr(e, "version_number") == 3


def test_attr_reads_open_metadata():
    e = {"id": "x", "metadata": {"shot_id": "s1"}}
    assert _attr(e, "shot_id") == "s1"


def test_attr_legacy_attributes_fallback():
    e = {"id": "x", "attributes": {"shot_id": "s1"}}  # legacy wire shape
    assert _attr(e, "shot_id") == "s1"


def test_attr_typed_wins_on_collision():
    # mirrors write-side _attrs_to_dict precedence (typed beats open)
    e = {"id": "x", "parent_type": "shot", "metadata": {"parent_type": "asset"}}
    assert _attr(e, "parent_type") == "shot"


def test_attr_default_when_absent():
    assert _attr({"id": "x", "metadata": {}}, "missing", "d") == "d"


def test_entity_fields_merges_typed_and_open():
    e = {"id": "x", "version_number": 2, "metadata": {"shot_id": "s1", "track": "L01"},
         "locations": [], "relationships": []}
    fields = _entity_fields(e)
    assert fields["version_number"] == 2     # typed top-level
    assert fields["shot_id"] == "s1"         # open
    assert fields["track"] == "L01"          # open
    assert "locations" not in fields         # structural keys excluded


# ── integration: list_versions filters linked versions correctly ─────────

class _FakeClient:
    def __init__(self, entities):
        self._entities = entities

    async def request(self, msg, timeout=None):
        return {"entities": self._entities}


_SHOT = "942a375d-bb4d-4584-8c98-d2d6f8805c55"

# to_dict wire shape: parent_id is a typed top-level field
_LINKED = {"id": "v1", "entity_type": "version", "version_number": 1,
           "parent_id": _SHOT, "parent_type": "shot", "metadata": {}}
_OTHER = {"id": "v2", "entity_type": "version", "version_number": 1,
          "parent_id": "00000000-0000-0000-0000-000000000000", "parent_type": "shot",
          "metadata": {}}


def _run(entities, **params):
    orig = fbt._client
    fbt._client = lambda: _FakeClient(entities)
    try:
        return json.loads(asyncio.run(list_versions(ListVersionsInput(project_id="p", **params))))
    finally:
        fbt._client = orig


def test_list_versions_filters_by_parent_id():
    """The shot filter matches the linked version — would be 0 under the old
    wrong-key read (v.get('attributes',{}).get('parent_id') was always None)."""
    data = _run([_LINKED, _OTHER], shot_id=_SHOT)
    assert data["count"] == 1
    assert data["versions"][0]["id"] == "v1"


def test_list_versions_unfiltered_returns_all():
    data = _run([_LINKED, _OTHER])
    assert data["count"] == 2


# ── integration: published-shot readers use canonical parent_id ─────────

_PROJECT = "project-1"
_SHOT_ENTITY = {"id": _SHOT, "entity_type": "shot", "name": "SHOT_010", "metadata": {}}
_PUBLISHED_LINKED = {
    "id": "v-linked",
    "entity_type": "version",
    "name": "SHOT_010_plate_v001",
    "version_number": 1,
    "parent_id": _SHOT,
    "parent_type": "shot",
    "metadata": {
        "asset_name": "SHOT_010_plate",
        "track": "L01",
        "colour_space": "ACEScct",
        "sequence_name": "seq_a",
        "version_number": 1,
    },
    "locations": [{"storage_type": "local", "path": "/show/SHOT_010_plate_v001.exr"}],
}
_PUBLISHED_OTHER = {
    "id": "v-other",
    "entity_type": "version",
    "name": "SHOT_020_plate_v001",
    "version_number": 1,
    "parent_id": "00000000-0000-0000-0000-000000000000",
    "parent_type": "shot",
    "metadata": {
        "asset_name": "SHOT_020_plate",
        "colour_space": "ACEScct",
        "version_number": 1,
    },
}


class _FakeRegistryClient:
    async def request(self, msg, timeout=None):
        if msg["type"] == MsgType.ENTITY_LIST and msg["entity_type"] == "shot":
            return {"entities": [_SHOT_ENTITY]}
        if msg["type"] == MsgType.ENTITY_LIST and msg["entity_type"] == "version":
            return {"entities": [_PUBLISHED_LINKED, _PUBLISHED_OTHER]}
        if msg["type"] == MsgType.ENTITY_LIST and msg["entity_type"] == "media":
            return {"entities": []}
        if msg["type"] == MsgType.QUERY_DEPENDENTS:
            return {"dependents": []}
        raise AssertionError(f"Unexpected request: {msg}")


def _run_registry_tool(tool, params):
    orig = fbt._client
    fbt._client = lambda: _FakeRegistryClient()
    try:
        return json.loads(asyncio.run(tool(params)))
    finally:
        fbt._client = orig


def test_get_shot_versions_filters_linked_versions_by_parent_id():
    data = _run_registry_tool(
        get_shot_versions,
        GetShotVersionsInput(project_id=_PROJECT, shot_name="SHOT_010"),
    )
    assert data["count"] == 1
    assert data["versions"][0]["version_id"] == "v-linked"


def test_get_shot_lineage_filters_linked_versions_by_parent_id():
    data = _run_registry_tool(
        get_shot_lineage,
        GetShotLineageInput(project_id=_PROJECT, shot_name="SHOT_010"),
    )
    assert data["version_count"] == 1
    assert data["lineage"][0]["version_id"] == "v-linked"


def test_list_published_plates_filters_linked_versions_by_parent_id():
    data = _run_registry_tool(
        list_published_plates,
        ListPublishedPlatesInput(project_id=_PROJECT, shot_name="SHOT_010"),
    )
    assert data["count"] == 1
    assert data["plates"][0]["version_id"] == "v-linked"
    assert data["plates"][0]["shot_id"] == _SHOT
