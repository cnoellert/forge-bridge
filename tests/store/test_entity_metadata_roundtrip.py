"""Regression: open `entity.metadata` must survive the JSONB round-trip.

`_attrs_to_dict` merges `entity.metadata` into the stored JSONB column, but the
typed branches of `_to_core` historically reset `metadata={}` and lifted only
their formal fields — silently dropping open attributes (notably a media's
`role`, which "travels with the media entity as media.attributes.role"). This
locks the symmetric restore in place.
"""

from types import SimpleNamespace

from forge_bridge.store.repo import EntityRepo, _TYPED_ATTR_KEYS


def _to_core(attributes: dict, entity_type: str = "media", name: str = "shot010_render"):
    import uuid
    db = SimpleNamespace(
        id=uuid.uuid4(),
        entity_type=entity_type,
        name=name,
        status=None,
        project_id=None,
        attributes=attributes,
    )
    # media branch doesn't touch self.registry
    return EntityRepo(session=None, registry=None)._to_core(db)


def test_media_role_survives_roundtrip():
    """The canonical media-role carrier: render media reads back its role."""
    e = _to_core({"role": "render", "format": "EXR", "resolution": "1920x1080"})
    assert e.format == "EXR"                 # typed field still reconstructed
    assert e.metadata.get("role") == "render"  # open attribute restored


def test_typed_fields_do_not_leak_into_metadata():
    """Formal properties stay typed — they must not double-appear in metadata."""
    e = _to_core({"role": "render", "format": "EXR", "resolution": "1920x1080"})
    for typed in _TYPED_ATTR_KEYS["media"]:
        assert typed not in e.metadata


def test_arbitrary_pipeline_attributes_survive():
    """Open key/values beyond role round-trip too (the write-side promise)."""
    e = _to_core({"role": "comp", "kind": "deliverable", "tape_name": "A001"})
    assert e.metadata.get("kind") == "deliverable"
    assert e.metadata.get("tape_name") == "A001"
    assert e.metadata.get("role") == "comp"


def test_layer_role_key_is_typed_not_metadata():
    """Track roles live on the Layer as a typed role_key, not open metadata."""
    import uuid
    key = str(uuid.uuid4())
    e = _to_core({"role_key": key, "order": 0}, entity_type="layer", name="L01")
    assert str(e.role_key) == key
    assert "role_key" not in e.metadata
