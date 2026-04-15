"""
Wave 0 test scaffolds for Phase 1 Tool Parity requirements (TOOL-01 through TOOL-09).

Tests marked @pytest.mark.skip are stubs to be unskipped as implementation lands.
Tests NOT skipped verify immediately-verifiable properties of the codebase.

Requirements covered:
    TOOL-01  timeline: get_sequence_info, set_segment_attribute, bulk_rename_segments,
                       get_sequence_editing_guide, disconnect_segments,
                       inspect_sequence_versions
    TOOL-02  timeline: create_version, reconstruct_track
    TOOL-03  timeline: clone_version
    TOOL-04  timeline: replace_segment_media
    TOOL-05  timeline: scan_roles, assign_roles
    TOOL-06  batch: list_batch_nodes, get_node_attributes, create_node, connect_nodes,
                    set_node_attribute, render_batch, batch_setup, get_write_file_path,
                    inspect_batch_xml, prune_batch_xml
    TOOL-07  publish: rename_shots, rename_segments, publish_sequence,
                      assemble_published_sequence
    TOOL-08  reconform: reconform_sequence
    TOOL-09  switch_grade: switch_grade
"""

import tomllib

import pytest


# ── TOOL-01..05 — Timeline exports ────────────────────────────────────────────

def test_timeline_exports():
    """Verify timeline module exports all required functions."""
    from forge_bridge.tools import timeline

    expected = [
        "get_sequence_segments",
        "set_segment_attribute",
        "rename_shots",
        "get_sequence_editing_guide",
        "disconnect_segments",
        "inspect_sequence_versions",
        "create_version",
        "reconstruct_track",
        "clone_version",
        "replace_segment_media",
        "scan_roles",
        "assign_roles",
    ]
    for name in expected:
        assert hasattr(timeline, name), f"timeline is missing export: {name}"
        assert callable(getattr(timeline, name)), f"timeline.{name} is not callable"


# ── TOOL-06 — Batch exports ───────────────────────────────────────────────────

def test_batch_exports():
    """Verify batch module exports all required functions."""
    from forge_bridge.tools import batch

    expected = [
        "list_batch_nodes",
        "get_node_attributes",
        "create_node",
        "connect_nodes",
        "set_node_attribute",
        "render_batch",
        "batch_setup",
        "get_write_file_path",
        "inspect_batch_xml",
        "prune_batch_xml",
    ]
    for name in expected:
        assert hasattr(batch, name), f"batch is missing export: {name}"
        assert callable(getattr(batch, name)), f"batch.{name} is not callable"


# ── TOOL-07 — Publish exports ─────────────────────────────────────────────────

def test_publish_exports():
    """Verify publish module exports all required functions."""
    from forge_bridge.tools import publish

    expected = [
        "rename_shots",
        "rename_segments",
        "publish_sequence",
        "assemble_published_sequence",
    ]
    for name in expected:
        assert hasattr(publish, name), f"publish is missing export: {name}"
        assert callable(getattr(publish, name)), f"publish.{name} is not callable"


# ── TOOL-08 — Reconform exports ───────────────────────────────────────────────

def test_reconform_exports():
    """Verify reconform module exists and exports reconform_sequence."""
    from forge_bridge.tools import reconform

    assert hasattr(reconform, "reconform_sequence"), \
        "reconform module missing reconform_sequence"
    assert callable(reconform.reconform_sequence)


# ── TOOL-09 — Switch grade exports ───────────────────────────────────────────

def test_switch_grade_exports():
    """Verify switch_grade module exists and exports switch_grade."""
    from forge_bridge.tools import switch_grade as sg_module

    assert hasattr(sg_module, "switch_grade"), \
        "switch_grade module missing switch_grade function"
    assert callable(sg_module.switch_grade)


# ── Pydantic model coverage ───────────────────────────────────────────────────

def test_project_models():
    """Verify project.py Pydantic models exist for all parameterized functions."""
    from pydantic import BaseModel

    from forge_bridge.tools import project

    # Every parameterized function defined in project.py must have a BaseModel input type
    import inspect
    for name, fn in inspect.getmembers(project, inspect.isfunction):
        # Skip functions imported from other modules (e.g. Field from pydantic)
        if getattr(fn, "__module__", None) != project.__name__:
            continue
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        if not params:
            continue
        first_ann = params[0].annotation
        if first_ann is inspect.Parameter.empty:
            continue
        try:
            is_model = issubclass(first_ann, BaseModel)
        except TypeError:
            is_model = False
        assert is_model, (
            f"project.{name}: first param annotation is not a BaseModel subclass "
            f"(got {first_ann!r})"
        )


def test_utility_models():
    """Verify utility.py Pydantic models exist for all parameterized functions."""
    from pydantic import BaseModel

    from forge_bridge.tools import utility

    import inspect
    for name, fn in inspect.getmembers(utility, inspect.isfunction):
        # Skip functions imported from other modules
        if getattr(fn, "__module__", None) != utility.__name__:
            continue
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        if not params:
            continue
        first_ann = params[0].annotation
        if first_ann is inspect.Parameter.empty:
            continue
        try:
            is_model = issubclass(first_ann, BaseModel)
        except TypeError:
            is_model = False
        assert is_model, (
            f"utility.{name}: first param annotation is not a BaseModel subclass "
            f"(got {first_ann!r})"
        )


def test_pydantic_coverage():
    """Verify all parameterized tool functions have a Pydantic BaseModel as first argument."""
    import inspect
    import typing

    from pydantic import BaseModel

    from forge_bridge.tools import batch, project, publish, reconform, switch_grade, timeline, utility

    modules = [timeline, batch, publish, project, utility, reconform, switch_grade]
    failures = []

    for mod in modules:
        # Resolve string annotations (from __future__ import annotations) per module
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("_"):
                continue
            # Skip functions imported from other modules (e.g. Field from pydantic)
            if getattr(fn, "__module__", None) != mod.__name__:
                continue
            # Resolve annotations, falling back to raw signature if get_type_hints fails
            try:
                hints = typing.get_type_hints(fn)
            except Exception:
                hints = {}
            sig = inspect.signature(fn)
            params = [p for p in sig.parameters.values()
                      if p.name not in ("self", "cls")]
            if not params:
                continue
            first_param = params[0]
            # Prefer resolved hint over raw annotation (handles string annotations)
            first_ann = hints.get(first_param.name, first_param.annotation)
            if first_ann is inspect.Parameter.empty:
                failures.append(f"{mod.__name__}.{name}: missing type annotation")
                continue
            try:
                ok = issubclass(first_ann, BaseModel)
            except TypeError:
                ok = False
            if not ok:
                failures.append(
                    f"{mod.__name__}.{name}: first param is {first_ann!r}, not a BaseModel"
                )

    assert not failures, "Pydantic coverage failures:\n" + "\n".join(failures)


# ── Non-skipped: immediately-verifiable properties ────────────────────────────

def test_bridge_timeout():
    """FORGE_BRIDGE_TIMEOUT default must be 60 seconds (not 30)."""
    import importlib
    import os

    # Ensure env var is NOT set so we test the default
    env_backup = os.environ.pop("FORGE_BRIDGE_TIMEOUT", None)
    try:
        import forge_bridge.bridge as bridge_mod
        importlib.reload(bridge_mod)
        assert bridge_mod.BRIDGE_TIMEOUT == 60, (
            f"Expected BRIDGE_TIMEOUT=60, got {bridge_mod.BRIDGE_TIMEOUT}"
        )
    finally:
        if env_backup is not None:
            os.environ["FORGE_BRIDGE_TIMEOUT"] = env_backup
        # Reload once more to restore env state
        importlib.reload(bridge_mod)


def test_pyproject_no_duplicates():
    """pyproject.toml must have no duplicate packages and openai/anthropic not in core deps."""
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    core_deps = data["project"]["dependencies"]

    # Extract package names (strip version specifiers)
    def pkg_name(dep: str) -> str:
        # Handle extras like mcp[cli]>=1.0 → mcp
        return dep.split("[")[0].split(">=")[0].split("<=")[0].split("==")[0].strip().lower()

    names = [pkg_name(d) for d in core_deps]

    # No duplicates
    seen = set()
    duplicates = []
    for n in names:
        if n in seen:
            duplicates.append(n)
        seen.add(n)
    assert not duplicates, f"Duplicate packages in [project.dependencies]: {duplicates}"

    # openai and anthropic must NOT be in core deps
    assert "openai" not in seen, \
        "openai must not be in [project.dependencies] — put it in [llm] optional extra"
    assert "anthropic" not in seen, \
        "anthropic must not be in [project.dependencies] — put it in [llm] optional extra"

    # [llm] extra must exist and contain openai + anthropic
    opt = data["project"].get("optional-dependencies", {})
    llm_extra = opt.get("llm", [])
    llm_names = {pkg_name(d) for d in llm_extra}
    assert "openai" in llm_names, \
        "openai missing from [project.optional-dependencies] llm extra"
    assert "anthropic" in llm_names, \
        "anthropic missing from [project.optional-dependencies] llm extra"
