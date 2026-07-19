"""Regression proof for Flame's camelCase lifecycle hook discovery."""

from __future__ import annotations

from pathlib import Path
import runpy


HOOK_PATH = (
    Path(__file__).parent.parent
    / "flame_hooks"
    / "forge_bridge"
    / "scripts"
    / "forge_bridge.py"
)


def test_hook_exports_flame_lifecycle_compatibility_aliases() -> None:
    namespace = runpy.run_path(str(HOOK_PATH))

    assert namespace["appInitialized"] is namespace["app_initialized"]
    assert namespace["projectChanged"] is namespace["project_changed"]
    assert namespace["getCustomUIActions"] is namespace["get_custom_ui_actions"]
    assert namespace["customUIAction"] is namespace["custom_ui_action"]
