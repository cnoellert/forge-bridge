"""
Tests for forge-bridge core vocabulary and registry.

Run with: pytest tests/test_core.py -v
"""

import uuid
from fractions import Fraction

import pytest

from forge_bridge.core import (
    Asset, FrameRange, Layer, Location, Media, Project,
    Relational, Relationship, Registry, RelationshipTypeDef,
    RoleDefinition, Sequence, Shot, Stack, STANDARD_ROLES,
    SYSTEM_REL_KEYS, Status, StorageType, Timecode, Version,
    OrphanError, ProtectedEntryError, UnknownNameError, RegistryError,
    get_default_registry, set_default_registry,
)


# ─────────────────────────────────────────────────────────────
# Timecode
# ─────────────────────────────────────────────────────────────

class TestTimecode:
    def test_from_string(self):
        tc = Timecode.from_string("01:00:00:00")
        assert tc.hours == 1 and tc.frames == 0

    def test_to_frames_24fps(self):
        tc = Timecode(1, 0, 0, 0, fps=Fraction(24))
        assert tc.to_frames() == 86400

    def test_roundtrip(self):
        orig = Timecode.from_string("00:01:30:12", fps=Fraction(24))
        assert str(Timecode.from_frames(orig.to_frames(), fps=Fraction(24))) == str(orig)

    def test_drop_frame_detected(self):
        assert Timecode.from_string("00:00:00;00").drop_frame is True

    def test_str(self):
        assert str(Timecode(0, 1, 2, 3)) == "00:01:02:03"


# ─────────────────────────────────────────────────────────────
# FrameRange
# ─────────────────────────────────────────────────────────────

class TestFrameRange:
    def test_duration(self):
        assert FrameRange(1001, 1100).duration == 100

    def test_invalid(self):
        with pytest.raises(ValueError):
            FrameRange(1100, 1001)

    def test_contains(self):
        fr = FrameRange(1001, 1100)
        assert fr.contains(1050) and not fr.contains(1000)

    def test_overlaps(self):
        assert FrameRange(1001, 1050).overlaps(FrameRange(1040, 1100))
        assert not FrameRange(1001, 1050).overlaps(FrameRange(1060, 1100))


# ─────────────────────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────────────────────

class TestStatus:
    def test_canonical(self):
        assert Status.from_string("approved") == Status.APPROVED

    def test_alias(self):
        assert Status.from_string("wip") == Status.IN_PROGRESS
        assert Status.from_string("final") == Status.DELIVERED

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            Status.from_string("nonsense")


# ─────────────────────────────────────────────────────────────
# Registry — RoleRegistry
# ─────────────────────────────────────────────────────────────

class TestRoleRegistry:
    def setup_method(self):
        self.reg = Registry.default()

    def test_standard_roles_present(self):
        assert self.reg.roles.exists("primary")
        assert self.reg.roles.exists("matte")

    def test_flame_alias(self):
        assert self.reg.roles.get_by_name("primary").get_alias("flame") == "L01"

    def test_rename_safe(self):
        """Renaming a role: key stays the same, name changes."""
        old_key = self.reg.roles.get_key("primary")
        self.reg.roles.rename("primary", "hero")
        assert not self.reg.roles.exists("primary")
        assert self.reg.roles.exists("hero")
        assert self.reg.roles.get_key("hero") == old_key

    def test_rename_to_existing_raises(self):
        with pytest.raises(RegistryError):
            self.reg.roles.rename("primary", "matte")

    def test_add_custom(self):
        defn = self.reg.roles.add("paint", label="Paint Pass", order=9)
        assert self.reg.roles.exists("paint")
        assert defn.label == "Paint Pass"

    def test_add_duplicate_raises(self):
        with pytest.raises(RegistryError):
            self.reg.roles.add("primary")

    def test_delete_unused(self):
        self.reg.roles.add("temp_role")
        self.reg.roles.delete("temp_role")
        assert not self.reg.roles.exists("temp_role")

    def test_delete_blocks_when_in_use(self):
        """Deleting a role that a Layer holds raises OrphanError."""
        self.reg.roles.add("fragile_role")
        layer = Layer("fragile_role", registry=self.reg)
        with pytest.raises(OrphanError) as exc:
            self.reg.roles.delete("fragile_role")
        assert exc.value.usage_count == 1

    def test_delete_succeeds_after_unregister(self):
        """After the entity is removed, deletion is allowed."""
        self.reg.roles.add("temp2")
        layer = Layer("temp2", registry=self.reg)
        self.reg.roles.unregister_usage(layer.role_key, layer.id)
        self.reg.roles.delete("temp2")   # should not raise
        assert not self.reg.roles.exists("temp2")

    def test_usage_count(self):
        self.reg.roles.add("counted")
        assert self.reg.roles.usage_count("counted") == 0
        l1 = Layer("counted", registry=self.reg)
        l2 = Layer("counted", registry=self.reg)
        assert self.reg.roles.usage_count("counted") == 2

    def test_not_found_raises(self):
        with pytest.raises(UnknownNameError):
            self.reg.roles.get_by_name("does_not_exist")


# ─────────────────────────────────────────────────────────────
# Registry — RelationshipRegistry
# ─────────────────────────────────────────────────────────────

class TestRelationshipRegistry:
    def setup_method(self):
        self.reg = Registry.default()

    def test_system_types_present(self):
        for name in ("member_of", "version_of", "derived_from", "references", "peer_of"):
            assert self.reg.relationships.exists(name)

    def test_system_keys_stable(self):
        """System type keys must match the constants in traits.py."""
        for name, expected_key in SYSTEM_REL_KEYS.items():
            assert self.reg.relationships.get_key(name) == expected_key

    def test_rename_system_safe(self):
        """System types can be renamed."""
        old_key = self.reg.relationships.get_key("member_of")
        self.reg.relationships.rename("member_of", "belongs_to")
        assert not self.reg.relationships.exists("member_of")
        assert self.reg.relationships.get_key("belongs_to") == old_key

    def test_delete_system_blocked(self):
        """System types can never be deleted."""
        with pytest.raises(ProtectedEntryError):
            self.reg.relationships.delete("version_of")

    def test_add_custom(self):
        self.reg.relationships.add("approved_by")
        assert self.reg.relationships.exists("approved_by")

    def test_delete_custom_unused(self):
        self.reg.relationships.add("ephemeral")
        self.reg.relationships.delete("ephemeral")
        assert not self.reg.relationships.exists("ephemeral")

    def test_delete_custom_in_use_blocked(self):
        self.reg.relationships.add("blocking_type")
        custom_key = self.reg.relationships.get_key("blocking_type")
        # Manually register a usage
        src = uuid.uuid4()
        tgt = uuid.uuid4()
        self.reg.relationships.register_usage(custom_key, src, tgt)
        with pytest.raises(OrphanError):
            self.reg.relationships.delete("blocking_type")

    def test_rename_to_existing_blocked(self):
        with pytest.raises(RegistryError):
            self.reg.relationships.rename("member_of", "version_of")


# ─────────────────────────────────────────────────────────────
# Entities — relationships use keys, not enums
# ─────────────────────────────────────────────────────────────

class TestRelationships:
    def test_relationship_stores_key_not_name(self):
        shot = Shot(name="EP60_010")
        seq  = Sequence(name="Seq01")
        shot_with_seq = Shot(name="EP60_010", sequence_id=seq.id)
        rels = shot_with_seq.get_relationships()
        assert len(rels) == 1
        # rel_key must be the stable UUID, not an enum value
        assert rels[0].rel_key == SYSTEM_REL_KEYS["member_of"]

    def test_type_name_resolves_through_registry(self):
        seq  = Sequence(name="Seq01")
        shot = Shot(name="EP60_010", sequence_id=seq.id)
        rel  = shot.get_relationships()[0]
        assert rel.type_name() == "member_of"

    def test_rename_relationship_type_reflects_in_existing_relationships(self):
        """After renaming a rel type, existing relationships show the new name."""
        reg = Registry.default()
        set_default_registry(reg)

        seq  = Sequence(name="Seq01")
        shot = Shot(name="EP60_010", sequence_id=seq.id)
        rel  = shot.get_relationships()[0]

        # Rename the relationship type
        reg.relationships.rename("member_of", "belongs_to")

        # The existing relationship now shows the new name
        assert rel.type_name(reg) == "belongs_to"
        # The key is unchanged
        assert rel.rel_key == SYSTEM_REL_KEYS["member_of"]

        # Restore for other tests
        reg.relationships.rename("belongs_to", "member_of")
        set_default_registry(Registry.default())

    def test_filter_by_system_name(self):
        seq  = Sequence(name="Seq01")
        shot = Shot(name="EP60_010", sequence_id=seq.id)
        assert len(shot.get_relationships("member_of")) == 1
        assert len(shot.get_relationships("version_of")) == 0

    def test_filter_by_key(self):
        seq  = Sequence(name="Seq01")
        shot = Shot(name="EP60_010", sequence_id=seq.id)
        key  = SYSTEM_REL_KEYS["member_of"]
        assert len(shot.get_relationships(key)) == 1

    def test_remove_relationship(self):
        seq  = Sequence(name="Seq01")
        shot = Shot(name="EP60_010", sequence_id=seq.id)
        removed = shot.remove_relationship(seq.id, "member_of")
        assert removed is True
        assert len(shot.get_relationships("member_of")) == 0


# ─────────────────────────────────────────────────────────────
# Layer stores role_key, not Role object
# ─────────────────────────────────────────────────────────────

class TestLayer:
    def setup_method(self):
        self.reg = Registry.default()

    def test_layer_stores_key(self):
        layer = Layer("primary", registry=self.reg)
        expected_key = self.reg.roles.get_key("primary")
        assert layer.role_key == expected_key

    def test_role_name_lookup(self):
        layer = Layer("primary", registry=self.reg)
        assert layer.role_name(self.reg) == "primary"

    def test_rename_role_reflects_in_layer(self):
        """After renaming 'primary' → 'hero', layer.role_name() returns 'hero'."""
        layer = Layer("primary", registry=self.reg)
        self.reg.roles.rename("primary", "hero")
        assert layer.role_name(self.reg) == "hero"
        # Restore
        self.reg.roles.rename("hero", "primary")

    def test_delete_role_blocked_by_layer(self):
        self.reg.roles.add("disposable")
        layer = Layer("disposable", registry=self.reg)
        with pytest.raises(OrphanError):
            self.reg.roles.delete("disposable")


# ─────────────────────────────────────────────────────────────
# Stack
# ─────────────────────────────────────────────────────────────

class TestStack:
    def setup_method(self):
        self.reg = Registry.default()

    def test_stack_assembles(self):
        shot  = Shot(name="EP60_010")
        stack = Stack(shot_id=shot.id)
        for role in ("primary", "reference", "matte"):
            stack.add_layer(Layer(role, registry=self.reg))
        assert stack.depth == 3
        assert [l.role_name(self.reg) for l in stack.get_layers()] == [
            "primary", "reference", "matte"
        ]

    def test_get_layer_by_role(self):
        stack = Stack()
        stack.add_layer(Layer("primary",   registry=self.reg))
        stack.add_layer(Layer("matte",     registry=self.reg))
        assert stack.get_layer_by_role("matte",   self.reg) is not None
        assert stack.get_layer_by_role("missing", self.reg) is None

    def test_layers_are_peers(self):
        stack = Stack()
        l1 = Layer("primary",   registry=self.reg)
        l2 = Layer("reference", registry=self.reg)
        stack.add_layer(l1)
        stack.add_layer(l2)
        peer_rels = l2.get_relationships("peer_of")
        assert any(r.target_id == l1.id for r in peer_rels)


# ─────────────────────────────────────────────────────────────
# Full pipeline graph integration
# ─────────────────────────────────────────────────────────────

class TestPipelineGraph:
    def test_relationship_chain(self):
        reg     = Registry.default()
        project = Project(name="Epic60")
        seq     = Sequence(name="Seq01",    project_id=project.id)
        shot    = Shot(name="EP60_010",     sequence_id=seq.id)
        stack   = Stack(shot_id=shot.id)
        stack.add_layer(Layer("primary", registry=reg))
        version = Version(version_number=4, parent_id=shot.id)
        media   = Media(format="EXR",       version_id=version.id)

        member_of_key  = SYSTEM_REL_KEYS["member_of"]
        version_of_key = SYSTEM_REL_KEYS["version_of"]
        references_key = SYSTEM_REL_KEYS["references"]

        assert seq.get_relationships(member_of_key)[0].target_id   == project.id
        assert shot.get_relationships(member_of_key)[0].target_id  == seq.id
        assert stack.get_relationships(member_of_key)[0].target_id == shot.id
        assert version.get_relationships(version_of_key)[0].target_id == shot.id
        assert media.get_relationships(references_key)[0].target_id   == version.id

    def test_media_location_priority(self):
        media = Media(format="EXR")
        media.add_location("/local",   storage_type="local",   priority=10)
        media.add_location("/network", storage_type="network", priority=5)
        assert media.get_primary_location().path == "/local"

    def test_registry_serialization_roundtrip(self):
        reg = Registry.default()
        reg.roles.add("custom_paint", order=9)
        reg.roles.rename("primary", "hero")
        reg.relationships.add("approved_by")

        data     = reg.to_dict()
        restored = Registry.from_dict(data)

        assert restored.roles.exists("hero")
        assert not restored.roles.exists("primary")
        assert restored.roles.exists("custom_paint")
        assert restored.relationships.exists("approved_by")
        # System types survive roundtrip
        for name in SYSTEM_REL_KEYS:
            # May have been renamed, but key must exist
            assert reg.relationships.get_by_key(SYSTEM_REL_KEYS[name]) is not None
