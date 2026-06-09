"""Compact first-party operation grounding for the operation front."""

from __future__ import annotations


def operation_v1_digest() -> str:
    """Return the minimal create-reel operation vocabulary."""
    return "\n".join([
        "OPERATIONS:",
        "- create_reel: create a Flame reel; requires reel_name; target "
        "container is optional",
        "- API fact: Flame libraries and reel groups expose create_reel(name)",
        "- default target: target_type=library, target_name=default workspace "
        "library; the preview must show this before ratification",
        "- output graph: flame_create_reel {\"params\": {...}} -> commit",
    ])
