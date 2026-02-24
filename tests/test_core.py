"""
Tests for forge-bridge core vocabulary.

Run with: pytest tests/test_core.py -v
"""

import uuid
from fractions import Fraction

import pytest

from forge_bridge.core import (
    Asset,
    FrameRange,
    Layer,
    Location,
    Media,
    Project,
    Relational,
    RelationshipType,
    Role,
    Sequence,
    Shot,
    Stack,
    STANDARD_ROLES,
    Status,
    StorageType,
    Timecode,
    Version,
)


# ─────────────────────────────────────────────────────────────
# Timecode
# ─────────────────────────────────────────────────────────────

class TestTimecode:
    def test_from_string(self):
        tc = Timecode.from_string("01:00:00:00")
        assert tc.hours == 1
        assert tc.minutes == 0
        assert tc.seconds == 0
        assert tc.frames == 0

    def test_to_frames_24fps(self):
        tc = Timecode(1, 0, 0, 0, fps=Fraction(24))
        assert tc.to_frames() == 86400   # 1hr * 3600s * 24fps

    def test_from_frames_roundtrip(self):
        original = Timecode.from_string("00:01:30:12", fps=Fraction(24))
        frames = original.to_frames()
        recovered = Timecode.from_frames(frames, fps=Fraction(24))
        assert str(original) == str(recovered)

    def test_drop_frame_detected(self):
        tc = Timecode.from_string("00:00:00;00")
        assert tc.drop_frame is True

    def test_str_representation(self):
        tc = Timecode(0, 1, 2, 3)
        assert str(tc) == "00:01:02:03"


# ─────────────────────────────────────────────────────────────
# FrameRange
# ─────────────────────────────────────────────────────────────

class TestFrameRange:
    def test_duration(self):
        fr = FrameRange(1001, 1100)
        assert fr.duration == 100

    def test_invalid_range(self):
        with pytest.raises(ValueError):
            FrameRange(1100, 1001)

    def test_contains(self):
        fr = FrameRange(1001, 1100)
        assert fr.contains(1050)
        assert not fr.contains(1000)
        assert not fr.contains(1101)

    def test_overlaps(self):
        a = FrameRange(1001, 1050)
        b = FrameRange(1040, 1100)
        c = FrameRange(1060, 1100)
        assert a.overlaps(b)
        assert not a.overlaps(c)

    def test_timecode_roundtrip(self):
        fps = Fraction(24)
        tc_in  = Timecode.from_string("01:00:00:00", fps=fps)
        tc_out = Timecode.from_string("01:00:04:00", fps=fps)
        fr = FrameRange.from_timecodes(tc_in, tc_out)
        assert fr.duration == 97   # 4 seconds * 24fps + 1 (inclusive)


# ─────────────────────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────────────────────

class TestStatus:
    def test_from_string_canonical(self):
        assert Status.from_string("approved") == Status.APPROVED

    def test_from_string_alias(self):
        assert Status.from_string("wip") == Status.IN_PROGRESS
        assert Status.from_string("final") == Status.DELIVERED

    def test_from_string_unknown(self):
        with pytest.raises(ValueError):
            Status.from_string("totally_unknown_status")


# ─────────────────────────────────────────────────────────────
# Role
# ─────────────────────────────────────────────────────────────

class TestRole:
    def test_standard_roles_exist(self):
        assert "primary" in STANDARD_ROLES
        assert "matte" in STANDARD_ROLES

    def test_flame_alias(self):
        assert STANDARD_ROLES["primary"].get_alias("flame") == "L01"

    def test_path_template_resolution(self):
        role = Role("primary", path_template="{project}/{shot}/v{version:04d}")
        path = role.resolve_path(project="EP60", shot="EP60_010", version=4)
        assert path == "EP60/EP60_010/v0004"

    def test_path_template_missing_token(self):
        role = Role("primary", path_template="{project}/{shot}")
        with pytest.raises(ValueError):
            role.resolve_path(project="EP60")   # missing shot


# ─────────────────────────────────────────────────────────────
# Entities
# ─────────────────────────────────────────────────────────────

class TestProject:
    def test_creation(self):
        p = Project(name="Epic60", code="EP60")
        assert p.name == "Epic60"
        assert p.code == "EP60"
        assert isinstance(p.id, uuid.UUID)

    def test_code_defaults_to_name(self):
        p = Project(name="Epic60")
        assert p.code == "Epic60"

    def test_to_dict(self):
        p = Project(name="Epic60", code="EP60")
        d = p.to_dict()
        assert d["name"] == "Epic60"
        assert d["entity_type"] == "project"


class TestSequence:
    def test_member_of_relationship_auto_created(self):
        project = Project(name="Epic60")
        seq = Sequence(name="Seq01", project_id=project.id)
        rels = seq.get_relationships(RelationshipType.MEMBER_OF)
        assert len(rels) == 1
        assert rels[0].target_id == project.id


class TestShot:
    def test_duration_in_frames(self):
        fps = Fraction(24)
        shot = Shot(
            name="EP60_010",
            cut_in=Timecode.from_string("01:00:00:00", fps=fps),
            cut_out=Timecode.from_string("01:00:04:00", fps=fps),
        )
        assert shot.duration == 96   # 4 seconds * 24fps

    def test_status_from_string(self):
        shot = Shot(name="EP60_010", status="wip")
        assert shot.status == Status.IN_PROGRESS

    def test_member_of_relationship(self):
        seq = Sequence(name="Seq01")
        shot = Shot(name="EP60_010", sequence_id=seq.id)
        rels = shot.get_relationships(RelationshipType.MEMBER_OF)
        assert rels[0].target_id == seq.id


class TestVersion:
    def test_version_of_relationship(self):
        shot = Shot(name="EP60_010")
        v = Version(version_number=4, parent_id=shot.id, parent_type="shot")
        rels = v.get_relationships(RelationshipType.VERSION_OF)
        assert len(rels) == 1
        assert rels[0].target_id == shot.id


class TestMedia:
    def test_location_priority_ordering(self):
        media = Media(format="EXR")
        media.add_location("/local/path", storage_type="local",   priority=10)
        media.add_location("/net/path",   storage_type="network", priority=5)
        locations = media.get_locations()
        assert locations[0].path == "/local/path"
        assert locations[1].path == "/net/path"

    def test_primary_location(self):
        media = Media(format="EXR")
        media.add_location("/local/path", priority=10)
        assert media.get_primary_location().path == "/local/path"

    def test_references_relationship(self):
        version = Version(version_number=1)
        media = Media(format="EXR", version_id=version.id)
        rels = media.get_relationships(RelationshipType.REFERENCES)
        assert rels[0].target_id == version.id


# ─────────────────────────────────────────────────────────────
# Stack and Layer
# ─────────────────────────────────────────────────────────────

class TestStackAndLayer:
    def test_stack_builds_from_layers(self):
        shot = Shot(name="EP60_010")
        stack = Stack(shot_id=shot.id)
        l1 = Layer(role="primary",   order=0)
        l2 = Layer(role="reference", order=1)
        l3 = Layer(role="matte",     order=2)
        stack.add_layer(l1)
        stack.add_layer(l2)
        stack.add_layer(l3)

        assert stack.depth == 3
        assert [l.role.name for l in stack.get_layers()] == ["primary", "reference", "matte"]

    def test_get_layer_by_role(self):
        stack = Stack()
        stack.add_layer(Layer(role="primary"))
        stack.add_layer(Layer(role="matte"))
        assert stack.get_layer_by_role("matte") is not None
        assert stack.get_layer_by_role("nonexistent") is None

    def test_layer_gets_stack_id_on_add(self):
        stack = Stack()
        layer = Layer(role="primary")
        stack.add_layer(layer)
        assert layer.stack_id == stack.id

    def test_layers_are_peers(self):
        stack = Stack()
        l1 = Layer(role="primary")
        l2 = Layer(role="reference")
        stack.add_layer(l1)
        stack.add_layer(l2)
        # l2 should have a peer_of relationship to l1
        peer_rels = l2.get_relationships(RelationshipType.PEER_OF)
        assert any(r.target_id == l1.id for r in peer_rels)

    def test_layer_role_from_string(self):
        layer = Layer(role="primary")
        assert layer.role.name == "primary"
        assert layer.role.get_alias("flame") == "L01"

    def test_full_pipeline_graph(self):
        """Integration test — build a complete pipeline graph and verify relationships."""
        project  = Project(name="Epic60")
        seq      = Sequence(name="Seq01", project_id=project.id)
        shot     = Shot(name="EP60_010", sequence_id=seq.id)
        stack    = Stack(shot_id=shot.id)
        layer    = Layer(role="primary")
        stack.add_layer(layer)
        version  = Version(version_number=4, parent_id=shot.id)
        media    = Media(format="EXR", version_id=version.id)

        # Verify the relationship chain
        assert seq.get_relationships(RelationshipType.MEMBER_OF)[0].target_id  == project.id
        assert shot.get_relationships(RelationshipType.MEMBER_OF)[0].target_id == seq.id
        assert stack.get_relationships(RelationshipType.MEMBER_OF)[0].target_id == shot.id
        assert version.get_relationships(RelationshipType.VERSION_OF)[0].target_id == shot.id
        assert media.get_relationships(RelationshipType.REFERENCES)[0].target_id == version.id
