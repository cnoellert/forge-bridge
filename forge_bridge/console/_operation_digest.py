"""Compact first-party operation grounding for the operation front."""

from __future__ import annotations


def operation_v1_digest() -> str:
    """Return the minimal additive-create operation vocabulary."""
    return "\n".join([
        "OPERATIONS:",
        "- create_reel: create a Flame reel; requires reel_name; target "
        "container is optional; default target is the workspace library",
        "- create_reel_group: create a Flame reel group on the current desktop; "
        "requires reel_group_name",
        "- create_library: create a Flame library in the current workspace; "
        "requires library_name",
        "- API fact: Flame libraries and reel groups expose create_reel(name); "
        "the desktop exposes create_reel_group(name); the workspace exposes "
        "create_library(name)",
        "- default target: target_type=library, target_name=default workspace "
        "library; the preview must show this before ratification",
        "- output graphs: flame_create_reel {\"params\": {...}} -> commit; "
        "flame_create_reel_group {\"params\": {...}} -> commit; "
        "flame_create_library {\"params\": {...}} -> commit",
    ])
