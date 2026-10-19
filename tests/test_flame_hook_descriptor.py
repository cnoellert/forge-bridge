"""Session descriptor coverage for the production Flame hook (#287).

The hook announces a descriptor to Pipeline's session registry, which routes
by the forge project name. These pin Pipeline Phase 50.1 (FORGE_PROJECT wins
over the Flame project name) and link-propagation Hop 2 (flame_projekt and
flame_uuid), which once lived only in Pipeline's undeployed copy of the hook.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


_BRIDGE_PATH = (
    Path(__file__).parent.parent / "flame_hooks" / "forge_bridge" / "scripts" / "forge_bridge.py"
)

_EXPECTED_DESCRIPTOR_KEYS = {
    "instance_id", "dcc", "user", "project", "shot",
    "host", "pid", "port", "started_at", "version",
    "flame_projekt", "flame_uuid",
}


@pytest.fixture
def bridge(monkeypatch):
    for name in ("FORGE_PROJECT", "FORGE_FLAME_PROJEKT", "FORGE_FLAME_UUID"):
        monkeypatch.delenv(name, raising=False)
    spec = importlib.util.spec_from_file_location(
        "forge_bridge_descriptor_test",
        _BRIDGE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_flame(name: str) -> ModuleType:
    flame = ModuleType("flame")
    flame.project = ModuleType("flame.project")

    class _CurrentProject:
        pass

    current = _CurrentProject()
    current.name = name
    flame.project.current_project = current
    return flame


def test_forge_project_env_wins_over_flame_name(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_PROJECT", "sched1814_uat_review")
    monkeypatch.setitem(
        sys.modules, "flame", _fake_flame("sched1814_uat_review_2026_2_2_portofino")
    )

    desc = bridge._make_descriptor()

    assert desc["project"] == "sched1814_uat_review"
    assert desc["flame_projekt"] == "sched1814_uat_review_2026_2_2_portofino"


def test_forge_project_env_wins_when_flame_unavailable(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_PROJECT", "test_project_123")
    monkeypatch.setitem(sys.modules, "flame", None)

    assert bridge._make_descriptor()["project"] == "test_project_123"


def test_empty_forge_project_normalizes_to_none(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_PROJECT", "")
    monkeypatch.setitem(sys.modules, "flame", None)

    assert bridge._make_descriptor()["project"] is None


def test_falls_back_to_flame_name_without_env(bridge, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "flame", _fake_flame("native_flame_proj"))

    desc = bridge._make_descriptor()

    assert desc["project"] == "native_flame_proj"
    assert desc["flame_projekt"] == "native_flame_proj"


def test_project_is_none_without_env_or_flame(bridge, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "flame", None)

    assert bridge._make_descriptor()["project"] is None


def test_descriptor_emits_all_fields(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_PROJECT", "some_project")

    assert set(bridge._make_descriptor()) == _EXPECTED_DESCRIPTOR_KEYS


def test_descriptor_shot_is_none_and_dcc_is_flame(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_PROJECT", "some_project")

    desc = bridge._make_descriptor()

    assert desc["shot"] is None
    assert desc["dcc"] == "flame"


def test_descriptor_is_json_serializable(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_PROJECT", "serializable_test")

    parsed = json.loads(json.dumps(bridge._make_descriptor()))

    assert parsed["project"] == "serializable_test"


def test_flame_identity_from_env(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_PROJECT", "TST_Decouple")
    monkeypatch.setenv("FORGE_FLAME_PROJEKT", "TST_Decouple_2027_portofino")
    monkeypatch.setenv("FORGE_FLAME_UUID", "7e8ef33f-0362-428c-8d34-0daaa30eb701")
    monkeypatch.setitem(sys.modules, "flame", None)

    desc = bridge._make_descriptor()

    assert desc["project"] == "TST_Decouple"
    assert desc["flame_projekt"] == "TST_Decouple_2027_portofino"
    assert desc["flame_uuid"] == "7e8ef33f-0362-428c-8d34-0daaa30eb701"


def test_flame_identity_absent_without_env(bridge, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "flame", None)

    desc = bridge._make_descriptor()

    assert desc["flame_uuid"] is None
    assert desc["flame_projekt"] is None


def test_flame_projekt_env_wins_over_live_name(bridge, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_FLAME_PROJEKT", "from_launcher_2026_2_2_portofino")
    monkeypatch.setitem(sys.modules, "flame", _fake_flame("live_name"))

    desc = bridge._make_descriptor()

    assert desc["flame_projekt"] == "from_launcher_2026_2_2_portofino"
    assert desc["project"] == "live_name"
