"""Unit tests for ManifestService + ToolRecord (MFST-01)."""
from __future__ import annotations

import asyncio
import dataclasses

import pytest

from forge_bridge.console.manifest_service import ManifestService, ToolRecord


# -- ToolRecord invariants --------------------------------------------------


def test_tool_record_is_frozen_dataclass():
    assert dataclasses.is_dataclass(ToolRecord)
    assert ToolRecord.__dataclass_params__.frozen is True


def test_tool_record_to_dict_returns_plain_dict():
    tr = ToolRecord(
        name="synth_foo",
        origin="synthesized",
        namespace="synth",
        synthesized_at="2026-04-22T00:00:00Z",
        code_hash="a" * 64,
        version="1.0.0",
        observation_count=5,
        tags=("synthesized", "project:acme"),
        meta=(("author", "alice"), ("pipeline", "v3")),
    )
    d = tr.to_dict()
    assert isinstance(d, dict)
    assert d["name"] == "synth_foo"
    assert d["origin"] == "synthesized"
    assert d["namespace"] == "synth"
    assert d["tags"] == ["synthesized", "project:acme"]  # list on the wire
    assert d["meta"] == {"author": "alice", "pipeline": "v3"}  # dict on the wire


def test_tool_record_tags_non_tuple_raises():
    with pytest.raises(TypeError, match="tags must be a tuple"):
        ToolRecord(name="x", origin="builtin", namespace="flame", tags=["synthesized"])


def test_tool_record_meta_non_tuple_raises():
    with pytest.raises(TypeError, match="meta must be a tuple"):
        ToolRecord(
            name="x", origin="builtin", namespace="flame",
            meta={"a": "b"},
        )


# -- ManifestService CRUD ---------------------------------------------------


@pytest.fixture
def ms():
    return ManifestService()


def _make_record(name: str, origin: str = "synthesized") -> ToolRecord:
    ns = {"flame": "flame", "forge": "forge", "synth": "synth"}.get(
        name.split("_", 1)[0], "synth"
    )
    return ToolRecord(
        name=name, origin=origin, namespace=ns,
        synthesized_at="2026-04-22T00:00:00Z" if origin == "synthesized" else None,
        code_hash="a" * 64 if origin == "synthesized" else None,
        tags=("synthesized",) if origin == "synthesized" else (),
    )


async def test_manifest_service_register_stores_record(ms):
    tr = _make_record("synth_foo")
    await ms.register(tr)
    assert ms.get("synth_foo") == tr


async def test_manifest_service_register_replaces_existing(ms):
    tr1 = _make_record("synth_foo")
    await ms.register(tr1)
    tr2 = dataclasses.replace(tr1, version="2.0.0")
    await ms.register(tr2)
    assert ms.get("synth_foo") == tr2
    assert ms.get("synth_foo").version == "2.0.0"


async def test_manifest_service_get_all_returns_list_snapshot(ms):
    for name in ("a_tool", "b_tool", "c_tool"):
        await ms.register(_make_record(name))
    result = ms.get_all()
    assert isinstance(result, list)
    assert [tr.name for tr in result] == ["a_tool", "b_tool", "c_tool"]
    # Mutation of returned list MUST NOT affect internal state
    result.clear()
    assert len(ms.get_all()) == 3


async def test_manifest_service_remove_drops_record(ms):
    tr = _make_record("synth_foo")
    await ms.register(tr)
    await ms.remove("synth_foo")
    assert ms.get("synth_foo") is None
    assert ms.get_all() == []


async def test_manifest_service_remove_nonexistent_is_noop(ms):
    await ms.remove("does_not_exist")  # MUST NOT raise
    assert ms.get_all() == []


async def test_manifest_service_concurrent_register_is_serialized(ms):
    """Fire 20 concurrent registers; all 20 must be present.

    Without the asyncio.Lock, CPython's dict is still technically safe at
    the individual insert level, but any future compound-write (e.g.
    "only if absent") would race. The test pins the Lock contract.
    """
    records = [_make_record(f"tool_{i}") for i in range(20)]
    await asyncio.gather(*(ms.register(r) for r in records))
    got = {t.name for t in ms.get_all()}
    assert got == {f"tool_{i}" for i in range(20)}
