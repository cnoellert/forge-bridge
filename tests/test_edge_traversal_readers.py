"""Producer-agnostic property: version↔shot readers traverse the version_of edge.

The principle (EDGE-TRAVERSAL-READERS-PROPOSAL.md): readers prefer the durable
graph edge over duplicated ``parent_id``/``shot_id`` attributes, which are
projections that drift per producer. The proof is the cross-tab row that the old
attribute readers could not see — a version linked to its shot *only* by the
``version_of`` edge, carrying no ``parent_id``/``shot_id`` attribute (the shape
``register_publish`` emits).

Each migrated reader must surface BOTH:
  - ``v-canon`` — parent_id attr + edge (the canonical 20-shape), and
  - ``v-edge``  — edge only, no parent_id/shot_id (register_publish-shape).

These tests fail under the pre-migration attribute filters and pass after the
edge-traversal swap. They also lock the type-exclusion guarantee: a render media
that also points at the shot must never be mistaken for a version.
"""

import asyncio
import json

import forge_bridge.mcp.tools as fbt
from forge_bridge.mcp.tools import (
    get_shot_versions, GetShotVersionsInput,
    list_versions, ListVersionsInput,
    get_shot_lineage, GetShotLineageInput,
    check_shots, CheckShotsInput,
    list_published_plates, ListPublishedPlatesInput,
    register_publish, RegisterPublishInput,
    blast_radius, BlastRadiusInput,
)
from forge_bridge.server.protocol import MsgType


class _EdgeFixtureClient:
    """Fakes the wire for a single shot with two edge-linked versions.

    Topology (what ``query_dependents`` returns over the wire — bare source ids
    of *all* incoming edges, unfiltered by type, exactly like the live router):

        query_dependents(SHOT)      -> [V_CANON, V_EDGE, RENDER_MEDIA]
        query_dependents(MEDIA_DEP) -> [V_EDGE]        (a version produced it)

    V_CANON carries a ``parent_id`` attribute; V_EDGE carries none — its only
    link to the shot is the edge. RENDER_MEDIA points at the shot too, and must
    be excluded by type when readers intersect against the version set.
    """

    SHOT = "shot-1"
    SHOT_NAME = "tst_010"  # _parse_shot_name('tst_010_graded_L01') → ('tst_010', 'graded', 1)
    V_CANON = "v-canon"        # parent_id attr + edge (the 20-shape)
    V_EDGE = "v-edge"          # edge only, no parent_id/shot_id (register_publish-shape)
    RENDER_MEDIA = "m-render"  # render media also pointing at the shot (type-exclusion)
    MEDIA_DEP = "m-dep"        # a media that V_EDGE depends on (blast_radius input)

    def __init__(self):
        self.sent = []

    def _versions(self):
        return [
            {
                "id": self.V_CANON,
                "name": "tst_010_graded_v001",
                "metadata": {
                    "parent_id": self.SHOT,
                    "version_number": 1,
                    "asset_name": "tst_010_graded",
                    "colour_space": "ACEScg",
                },
                "locations": [{"path": "/show/v001.exr", "storage_type": "local"}],
            },
            {
                "id": self.V_EDGE,
                "name": "tst_010_graded_v002",
                # register_publish-shape: NO parent_id, NO shot_id
                "metadata": {"version_number": 2, "colour_space": "ACEScg"},
                "locations": [{"path": "/show/v002.exr", "storage_type": "local"}],
            },
        ]

    async def request(self, msg, timeout=None):
        self.sent.append(dict(msg))
        t = msg["type"]
        if t == MsgType.PROJECT_LIST:
            return {"projects": [{"id": "proj-1"}]}
        if t == MsgType.ENTITY_LIST:
            et = msg["entity_type"]
            if et == "shot":
                return {"entities": [
                    {"id": self.SHOT, "name": self.SHOT_NAME, "status": "in_progress"},
                ]}
            if et == "version":
                return {"entities": self._versions()}
            return {"entities": []}  # media, etc.
        if t == MsgType.ENTITY_GET:
            eid = msg["entity_id"]
            if eid == self.MEDIA_DEP:
                return {
                    "id": self.MEDIA_DEP, "name": "render_dep", "status": "verified",
                    "metadata": {"colour_space": "ACEScg"}, "locations": [],
                }
            return {"id": eid}
        if t == MsgType.QUERY_DEPENDENTS:
            eid = msg["entity_id"]
            if eid == self.SHOT:
                # both versions AND a render media point at the shot
                return {"dependents": [self.V_CANON, self.V_EDGE, self.RENDER_MEDIA]}
            if eid == self.MEDIA_DEP:
                return {"dependents": [self.V_EDGE]}
            return {"dependents": []}
        if t == MsgType.ENTITY_CREATE:
            return {"id": "ver-new", "entity_id": "ver-new"}
        if t in (MsgType.REL_CREATE, MsgType.LOC_ADD):
            return {"ok": True}
        return {}


def _run(client, coro_factory):
    orig = fbt._client
    fbt._client = lambda: client
    try:
        return json.loads(asyncio.run(coro_factory()))
    finally:
        fbt._client = orig


# ── Forward readers: shot → versions ────────────────────────────────────────

def test_get_shot_versions_includes_edge_only_version():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: get_shot_versions(
        GetShotVersionsInput(shot_name=c.SHOT_NAME, project_id="proj-1")))
    ids = {r["version_id"] for r in out["versions"]}
    assert ids == {c.V_CANON, c.V_EDGE}, out
    assert out["count"] == 2


def test_list_versions_shot_filter_includes_edge_only_version():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: list_versions(
        ListVersionsInput(project_id="proj-1", shot_id=c.SHOT)))
    ids = {v["id"] for v in out["versions"]}
    assert ids == {c.V_CANON, c.V_EDGE}, out


def test_get_shot_lineage_includes_edge_only_version():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: get_shot_lineage(
        GetShotLineageInput(shot_name=c.SHOT_NAME, project_id="proj-1")))
    ids = {v["version_id"] for v in out["lineage"]}
    assert ids == {c.V_CANON, c.V_EDGE}, out
    assert out["version_count"] == 2


def test_check_shots_counts_edge_only_version():
    """next_version/version_count must count edge-only versions — otherwise it
    disagrees with register_publish's own edge count (split-brain numbering)."""
    c = _EdgeFixtureClient()
    out = _run(c, lambda: check_shots(
        CheckShotsInput(shot_names=[c.SHOT_NAME], project_id="proj-1")))
    rec = out["shots"][0]
    assert rec["version_count"] == 2, out
    assert rec["last_version"] == 2 and rec["next_version"] == 3, out


# ── Reverse readers: version → shot ─────────────────────────────────────────

def test_list_published_plates_resolves_edge_only_shot():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: list_published_plates(
        ListPublishedPlatesInput(project_id="proj-1")))
    by_id = {p["version_id"]: p for p in out["plates"]}
    assert c.V_EDGE in by_id, out
    # shot resolved via the edge, not the (absent) parent_id attribute
    assert by_id[c.V_EDGE]["shot_id"] == c.SHOT, by_id[c.V_EDGE]


def test_list_published_plates_shot_name_filter_matches_edge_only():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: list_published_plates(
        ListPublishedPlatesInput(project_id="proj-1", shot_name=c.SHOT_NAME)))
    ids = {p["version_id"] for p in out["plates"]}
    assert c.V_EDGE in ids, out


def test_blast_radius_resolves_edge_only_version_shot():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: blast_radius(
        BlastRadiusInput(media_id=c.MEDIA_DEP, project_id="proj-1")))
    assert c.SHOT_NAME in out["affected_shots"], out
    av = {v["version_id"]: v for v in out["dependent_versions"]}
    # under the old shot_id-attr read this resolved to "unknown"
    assert av[c.V_EDGE]["shot_name"] == c.SHOT_NAME, av[c.V_EDGE]


# ── register_publish: edge count + 2b (no shot_id attribute) ────────────────

def test_register_publish_next_version_counts_edge_versions():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: register_publish(RegisterPublishInput(
        segment_name="tst_010_graded_L01", output_path="/show/v003.exr",
        start_frame=1001, end_frame=1100, colour_space="ACEScg",
        project_id="proj-1")))
    assert "error" not in out, out
    assert out["version_number"] == 3, out  # counted v-canon + v-edge via the edge


def test_register_publish_omits_denormalized_shot_attribute():
    """2b: the version_of edge is the sole link — no drifting shot_id/parent_id."""
    c = _EdgeFixtureClient()
    _run(c, lambda: register_publish(RegisterPublishInput(
        segment_name="tst_010_graded_L01", output_path="/show/v003.exr",
        start_frame=1001, end_frame=1100, colour_space="ACEScg",
        project_id="proj-1")))
    creates = [
        m for m in c.sent
        if m["type"] == MsgType.ENTITY_CREATE and m["entity_type"] == "version"
    ]
    assert len(creates) == 1, c.sent
    attrs = creates[0]["attributes"]
    assert "shot_id" not in attrs, attrs
    assert "parent_id" not in attrs, attrs


# ── Type-exclusion: a media pointing at the shot is not a version ────────────

def test_edge_traversal_excludes_non_version_dependents():
    c = _EdgeFixtureClient()
    out = _run(c, lambda: get_shot_versions(
        GetShotVersionsInput(shot_name=c.SHOT_NAME, project_id="proj-1")))
    ids = {r["version_id"] for r in out["versions"]}
    # RENDER_MEDIA is an incoming dependent of the shot but is not a version
    assert c.RENDER_MEDIA not in ids, out
