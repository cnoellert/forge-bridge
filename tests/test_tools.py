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
        "list_batch_groups",
        "get_node_types",
        "get_batch_iterations",
        "get_batch_reels",
        "open_batch_group",
        "delete_node",
        "disconnect_nodes",
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


def test_flame_list_batch_groups_happy_path(monkeypatch):
    """Batch group enumeration returns names plus is_open state."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = [
        {"name": "Comp A", "is_open": True},
        {"name": "Comp B", "is_open": False},
    ]

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "is_open" in code
        assert "desk.batch_groups" in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(batch_tools.list_batch_groups())
    assert json.loads(out) == fixture


def test_flame_get_node_types_happy_path(monkeypatch):
    """Node type enumeration returns live Flame node type strings."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "flame.batch.node_types" in code
        return {"node_types": ["Action", "Write File", "Colour Source"]}

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(batch_tools.get_node_types())
    parsed = json.loads(out)
    assert parsed["node_types"]
    assert "Action" in parsed["node_types"]


def test_flame_get_batch_iterations_happy_path(monkeypatch):
    """Iteration enumeration returns current, total, and iteration indices."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = {
        "current_iteration": 1,
        "total_iterations": 2,
        "iterations": [
            {"index": 1},
            {"index": 2},
        ],
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "current_iteration_number" in code
        assert "batch_iterations" in code
        assert "render_state" not in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(batch_tools.get_batch_iterations())
    assert json.loads(out) == fixture


def test_flame_get_batch_iterations_no_batch_open_structured_error(monkeypatch):
    """Iteration reads require an open batch group and fail structurally."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "no_batch_open" in code
        return {
            "error": "no_batch_open",
            "message": "Open a batch group first via flame_open_batch_group",
        }

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(batch_tools.get_batch_iterations())
    parsed = json.loads(out)
    assert parsed["error"] == "no_batch_open"


def test_flame_get_batch_reels_happy_path(monkeypatch):
    """Batch reel enumeration returns minimum filter-ready clip payload."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = {
        "reels": [
            {
                "name": "Batch Reel",
                "type": "reel",
                "clips": [{"name": "plate_A", "duration": 120}],
            },
            {
                "name": "Shelf",
                "type": "shelf_reel",
                "clips": [],
            },
        ]
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "shelf_reels" in code
        assert "colourspace" not in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(batch_tools.get_batch_reels())
    assert json.loads(out) == fixture


def test_flame_get_batch_reels_no_batch_open_structured_error(monkeypatch):
    """Batch reel reads require an open batch group and fail structurally."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "no_batch_open" in code
        return {
            "error": "no_batch_open",
            "message": "Open a batch group first via flame_open_batch_group",
        }

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(batch_tools.get_batch_reels())
    parsed = json.loads(out)
    assert parsed["error"] == "no_batch_open"


def test_flame_open_batch_group_dry_run_preview(monkeypatch):
    """Opening dry_run previews current and proposed batch context."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = {
        "dry_run": True,
        "action": "open_batch_group",
        "proposed": "Comp B",
        "current": "Comp A",
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "flame.schedule_idle_event" not in code
        assert "current" in code
        assert "proposed" in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.OpenBatchGroupInput(batch_group_name="Comp B", dry_run=True)
    out = asyncio.run(batch_tools.open_batch_group(params))
    assert json.loads(out) == fixture


def test_flame_open_batch_group_executes_context_switch(monkeypatch):
    """Opening dry_run=False schedules a UI context switch and confirms previous context."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = {"opened": "Comp B", "previous": "Comp A"}

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "flame.schedule_idle_event" in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.OpenBatchGroupInput(batch_group_name="Comp B")
    out = asyncio.run(batch_tools.open_batch_group(params))
    assert json.loads(out) == fixture


def test_flame_delete_node_dry_run_preview(monkeypatch):
    """Node deletion dry_run returns preview metadata without scheduling a write."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = {
        "dry_run": True,
        "action": "delete_node",
        "node_name": "Blur 1",
        "node_type": "Blur",
        "connected_inputs": 1,
        "connected_outputs": 1,
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        compile(code, "<flame-delete-dry-run>", "exec")
        assert "flame.schedule_idle_event" not in code
        assert ".set_value" not in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DeleteNodeInput(node_name="Blur 1", dry_run=True)
    out = asyncio.run(batch_tools.delete_node(params))
    assert json.loads(out) == fixture


def test_flame_delete_node_dry_run_does_not_invoke_main_thread(monkeypatch):
    """Policy retention: delete dry_run must not schedule real mutation code."""
    import asyncio

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        compile(code, "<flame-delete-dry-run-policy>", "exec")
        assert "flame.schedule_idle_event" not in code
        assert ".set_value" not in code
        return {"dry_run": True}

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DeleteNodeInput(node_name="Blur 1", dry_run=True)
    asyncio.run(batch_tools.delete_node(params))


def test_flame_delete_node_executes_and_confirms(monkeypatch):
    """Node deletion dry_run=False schedules a graph mutation and returns confirmation."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        compile(code, "<flame-delete-exec>", "exec")
        assert "flame.schedule_idle_event" in code
        return {"deleted": "Blur 1"}

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DeleteNodeInput(node_name="Blur 1")
    out = asyncio.run(batch_tools.delete_node(params))
    assert json.loads(out) == {"deleted": "Blur 1"}


def test_flame_delete_node_no_batch_open_structured_error(monkeypatch):
    """Delete requires explicit open batch scope."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "no_batch_open" in code
        return {
            "error": "no_batch_open",
            "message": "Open a batch group first via flame_open_batch_group",
        }

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DeleteNodeInput(node_name="Blur 1")
    out = asyncio.run(batch_tools.delete_node(params))
    parsed = json.loads(out)
    assert parsed["error"] == "no_batch_open"


def test_flame_delete_node_ambiguous_node_name(monkeypatch):
    """Duplicate node names return structured ambiguity with match count."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "ambiguous_node_name" in code
        return {
            "error": "ambiguous_node_name",
            "matches": 2,
            "message": "Multiple nodes share this name; rename or specify a unique node first.",
        }

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DeleteNodeInput(node_name="Blur")
    out = asyncio.run(batch_tools.delete_node(params))
    parsed = json.loads(out)
    assert parsed["error"] == "ambiguous_node_name"
    assert parsed["matches"] == 2


def test_flame_disconnect_nodes_dry_run_preview(monkeypatch):
    """Node disconnect dry_run previews graph-state mutation."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = {
        "dry_run": True,
        "action": "disconnect_nodes",
        "input_node": "Write File 1",
        "input_socket": "Front",
        "connection_exists": True,
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        compile(code, "<flame-disconnect-dry-run>", "exec")
        assert "flame.schedule_idle_event" not in code
        assert ".set_value" not in code
        assert "output_socket" not in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DisconnectNodesInput(
        output_node="Blur 1",
        input_node="Write File 1",
        output_socket="Result",
        input_socket="Front",
        dry_run=True,
    )
    out = asyncio.run(batch_tools.disconnect_nodes(params))
    assert json.loads(out) == fixture


def test_flame_disconnect_nodes_dry_run_does_not_invoke_main_thread(monkeypatch):
    """Policy retention: disconnect dry_run must not schedule real mutation code."""
    import asyncio

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        compile(code, "<flame-disconnect-dry-run-policy>", "exec")
        assert "flame.schedule_idle_event" not in code
        assert ".set_value" not in code
        return {"dry_run": True}

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DisconnectNodesInput(
        output_node="Blur 1",
        input_node="Write File 1",
        dry_run=True,
    )
    asyncio.run(batch_tools.disconnect_nodes(params))


def test_flame_disconnect_nodes_executes_and_confirms(monkeypatch):
    """Node disconnect dry_run=False schedules graph mutation and returns confirmation."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    fixture = {
        "disconnected": True,
        "input_node": "Write File 1",
        "input_socket": "Default",
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        compile(code, "<flame-disconnect-exec>", "exec")
        assert "flame.schedule_idle_event" in code
        assert "batch.disconnect_node(node, input_socket)" in code
        assert "disconnect_nodes(out_node" not in code
        return fixture

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DisconnectNodesInput(output_node="Blur 1", input_node="Write File 1")
    out = asyncio.run(batch_tools.disconnect_nodes(params))
    assert json.loads(out) == fixture


def test_flame_disconnect_nodes_no_batch_open_structured_error(monkeypatch):
    """Disconnect requires explicit open batch scope."""
    import asyncio
    import json

    from forge_bridge.tools import batch as batch_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "no_batch_open" in code
        return {
            "error": "no_batch_open",
            "message": "Open a batch group first via flame_open_batch_group",
        }

    monkeypatch.setattr(batch_tools.bridge, "execute_json", _fake_execute_json)

    params = batch_tools.DisconnectNodesInput(output_node="Blur 1", input_node="Write File 1")
    out = asyncio.run(batch_tools.disconnect_nodes(params))
    parsed = json.loads(out)
    assert parsed["error"] == "no_batch_open"


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
    """Verify project.py Pydantic models exist for all parameterized functions.

    Accepts both ``params: Model`` and ``params: Optional[Model] = None``
    (Pydantic v2 idiom for tools that must be callable with no arguments —
    see ``flame_list_libraries``).
    """
    import inspect
    import typing

    from pydantic import BaseModel

    from forge_bridge.tools import project

    def _is_basemodel_or_optional_basemodel(ann) -> bool:
        try:
            if issubclass(ann, BaseModel):
                return True
        except TypeError:
            pass
        # Optional[X] / Union[X, None] / X | None — accept iff the non-None
        # arm is a BaseModel subclass.
        origin = typing.get_origin(ann)
        if origin in (typing.Union, type(None)) or str(origin) == "types.UnionType":
            for arg in typing.get_args(ann):
                if arg is type(None):
                    continue
                try:
                    if issubclass(arg, BaseModel):
                        return True
                except TypeError:
                    continue
        return False

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
        assert _is_basemodel_or_optional_basemodel(first_ann), (
            f"project.{name}: first param annotation is not a BaseModel "
            f"or Optional[BaseModel] (got {first_ann!r})"
        )


# ── flame_list_libraries: must be callable with no arguments ──────────────


def test_flame_list_libraries_signature_has_default_for_params():
    """The Pydantic-v2 fix: ``params`` must have a default so the tool's
    JSON schema doesn't mark it required, otherwise ``fbridge run
    flame_list_libraries`` and the LLM tool-call path both fail with
    ``params: Field required``."""
    import inspect

    from forge_bridge.tools.project import list_libraries

    sig = inspect.signature(list_libraries)
    params_arg = sig.parameters["params"]
    assert params_arg.default is not inspect.Parameter.empty, (
        "flame_list_libraries: `params` has no default — Pydantic v2 will "
        "treat it as required and reject zero-arg calls."
    )


def test_run_flame_list_libraries_no_args(monkeypatch):
    """Calling list_libraries() with no args must succeed end-to-end (no
    validation error). The bridge.execute_json is mocked to return a stub
    library list; the test only asserts the no-arg call doesn't raise."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    captured: dict = {}

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        captured["code"] = code
        return [{"name": "default_library", "opened": True}]

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(project_tools.list_libraries())
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert parsed[0]["name"] == "default_library"
    # Default include_contents=False → the conditional block must not appear.
    assert "folder_details" not in captured["code"]


def test_run_flame_list_libraries_explicit_args_still_work(monkeypatch):
    """No regression: passing an explicit ListLibrariesInput still works."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    captured: dict = {}

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        captured["code"] = code
        return [{"name": "lib1", "opened": True, "folders": 2,
                 "reels": 0, "reel_groups": 0, "clips": 4, "sequences": 1,
                 "folder_details": []}]

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    args = project_tools.ListLibrariesInput(include_contents=True)
    out = asyncio.run(project_tools.list_libraries(args))
    parsed = json.loads(out)
    assert parsed[0]["clips"] == 4
    # include_contents=True path must inject the folder_details block.
    assert "folder_details" in captured["code"]


def test_flame_list_desktop_signature_is_original_no_args():
    """flame_list_desktop remains a no-arg tool with unchanged wire shape."""
    import inspect

    from forge_bridge.tools.project import list_desktop

    assert inspect.signature(list_desktop).parameters == {}


def test_flame_list_desktop_preserves_original_shape(monkeypatch):
    """Default desktop listing remains the compact count-only response."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    old_shape = {
        "reel_groups": [
            {"name": "Default", "reels": [{"name": "Sequences", "clips": 1, "sequences": 1}]}
        ],
        "batch_groups": [{"name": "Batch 1"}],
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "entry['items']" not in code
        assert "include_names" not in code
        return old_shape

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(project_tools.list_desktop())
    assert json.loads(out) == old_shape


def test_flame_list_reel_groups_happy_path(monkeypatch):
    """Reel group enumeration returns groups with one-level reel counts."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    fixture = [
        {
            "name": "Default",
            "reels": [
                {"name": "Sequences", "clips": 1, "sequences": 2},
                {"name": "Plates", "clips": 12, "sequences": 0},
            ],
        }
    ]

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "desk.reel_groups" in code
        assert "batch_groups" not in code
        return fixture

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(project_tools.list_reel_groups())
    assert json.loads(out) == fixture


def test_flame_list_reel_groups_empty_desktop(monkeypatch):
    """A desktop with no reel groups returns [] rather than an error."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        return []

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(project_tools.list_reel_groups())
    assert json.loads(out) == []


def test_flame_list_reel_groups_allows_empty_reels(monkeypatch):
    """A reel group with no reels is represented cleanly."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    fixture = [{"name": "Empty Group", "reels": []}]

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        return fixture

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    out = asyncio.run(project_tools.list_reel_groups())
    assert json.loads(out) == fixture


def test_flame_list_reel_contents_happy_path(monkeypatch):
    """Reel enumeration returns flat clip/sequence entries."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    fixture = [
        {"name": "plate_A", "type": "PyClip", "duration": 120, "track_count": 0},
        {"name": "30sec_21", "type": "PySequence", "duration": 720, "track_count": 3},
    ]

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "target_reel = 'Sequences'" in code
        return fixture

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.ListReelContentsInput(reel_name="Sequences")
    out = asyncio.run(project_tools.list_reel_contents(params))
    assert json.loads(out) == fixture


def test_flame_list_reel_contents_empty_reel(monkeypatch):
    """An existing empty reel returns [] rather than an error."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        return []

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.ListReelContentsInput(reel_name="Empty Reel")
    out = asyncio.run(project_tools.list_reel_contents(params))
    assert json.loads(out) == []


def test_flame_list_reel_contents_not_found_structured_error(monkeypatch):
    """Missing reels return a structured error payload."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        return {"error": "Reel not found", "reel_name": "Missing", "reel_group": ""}

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.ListReelContentsInput(reel_name="Missing")
    out = asyncio.run(project_tools.list_reel_contents(params))
    parsed = json.loads(out)
    assert parsed["error"] == "Reel not found"
    assert parsed["reel_name"] == "Missing"


def test_flame_get_clip_happy_path(monkeypatch):
    """Clip inspection returns Tier 1 operator-decision metadata."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    fixture = {
        "name": "plate_A",
        "type": "PyClip",
        "duration": 120,
        "duration_tc": "00:00:05:00",
        "width": 3840,
        "height": 2160,
        "frame_rate": "23.976 fps",
        "colour_space": "ACEScg",
        "bit_depth": "16-bit",
        "track_count": 0,
        "file_path": "/show/plates/plate_A.exr",
    }

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "target_clip = 'plate_A'" in code
        return fixture

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.GetClipInput(clip_name="plate_A")
    out = asyncio.run(project_tools.get_clip(params))
    assert json.loads(out) == fixture


def test_flame_get_clip_empty_or_missing_reel_not_found(monkeypatch):
    """A clip lookup narrowed to an empty/missing reel returns structured not found."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        return {"error": "Clip not found", "clip_name": "plate_A", "reel_name": "Empty Reel"}

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.GetClipInput(clip_name="plate_A", reel_name="Empty Reel")
    out = asyncio.run(project_tools.get_clip(params))
    parsed = json.loads(out)
    assert parsed["error"] == "Clip not found"
    assert parsed["reel_name"] == "Empty Reel"


def test_flame_list_library_contents_happy_path(monkeypatch):
    """Library enumeration returns one-level top-level entries."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    fixture = [
        {"name": "Reel 1", "type": "PyReel", "count": 3},
        {"name": "Folder A", "type": "PyFolder", "count": 2},
        {"name": "loose_clip", "type": "PyClip", "count": 0},
    ]

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        assert "target_library = 'Library 1'" in code
        return fixture

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.ListLibraryContentsInput(library_name="Library 1")
    out = asyncio.run(project_tools.list_library_contents(params))
    assert json.loads(out) == fixture


def test_flame_list_library_contents_empty_library(monkeypatch):
    """An existing empty library returns [] rather than an error."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        return []

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.ListLibraryContentsInput(library_name="Empty Library")
    out = asyncio.run(project_tools.list_library_contents(params))
    assert json.loads(out) == []


def test_flame_list_library_contents_not_found_structured_error(monkeypatch):
    """Missing libraries return a structured error payload."""
    import asyncio
    import json

    from forge_bridge.tools import project as project_tools

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        return {"error": "Library not found", "library_name": "Missing"}

    monkeypatch.setattr(project_tools.bridge, "execute_json", _fake_execute_json)

    params = project_tools.ListLibraryContentsInput(library_name="Missing")
    out = asyncio.run(project_tools.list_library_contents(params))
    parsed = json.loads(out)
    assert parsed["error"] == "Library not found"
    assert parsed["library_name"] == "Missing"


def test_utility_models():
    """Verify utility.py Pydantic models exist for all parameterized functions.

    Phase 23.1 in-flight exception: `execute_python` deliberately takes flat
    kwargs (`code: str, main_thread: bool`) instead of a BaseModel wrapper.
    FastMCP introspects the function signature; a BaseModel-wrapped signature
    generates a NESTED JSON schema (`{"params": {"code": "..."}}`) that the
    chat model could not generate, causing 100% silent dispatch failure pre-
    23.1-in-flight. Flat signature → flat schema → model can call the tool.
    See `SEED-FLAT-SIGNATURE-AUDIT-V1.6+` for the wider convention review.
    """
    from pydantic import BaseModel

    from forge_bridge.tools import utility

    # 23.1 carve-out — see docstring above for rationale.
    _FLAT_SIGNATURE_EXCEPTIONS = {"execute_python"}

    import inspect
    for name, fn in inspect.getmembers(utility, inspect.isfunction):
        # Skip functions imported from other modules
        if getattr(fn, "__module__", None) != utility.__name__:
            continue
        # Skip private helpers (underscore prefix). They are internal shared
        # bodies (e.g. _execute_python_core, called by operator-side CLI and
        # the MCP tool entry point) — not registered to FastMCP, so the
        # BaseModel-first-arg invariant does not apply to them.
        if name.startswith("_"):
            continue
        if name in _FLAT_SIGNATURE_EXCEPTIONS:
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
    """Verify all parameterized tool functions have a Pydantic BaseModel as
    first argument. Accepts ``Optional[Model]`` for tools that must remain
    callable with no arguments (Pydantic-v2 idiom — see flame_list_libraries).
    """
    import inspect
    import typing

    from pydantic import BaseModel

    from forge_bridge.tools import batch, project, publish, reconform, switch_grade, timeline, utility

    def _is_basemodel_or_optional(ann) -> bool:
        try:
            if issubclass(ann, BaseModel):
                return True
        except TypeError:
            pass
        origin = typing.get_origin(ann)
        if origin in (typing.Union,) or str(origin) == "types.UnionType":
            for arg in typing.get_args(ann):
                if arg is type(None):
                    continue
                try:
                    if issubclass(arg, BaseModel):
                        return True
                except TypeError:
                    continue
        return False

    modules = [timeline, batch, publish, project, utility, reconform, switch_grade]
    failures = []

    # Phase 23.1 in-flight: `flame_execute_python` deliberately uses flat
    # kwargs (code: str, main_thread: bool) because a BaseModel wrapper
    # generates a nested JSON schema FastMCP exposes to the LLM, and the
    # chat model could not produce the nested shape. Flat signature ⇒ flat
    # schema ⇒ model can call. The wider convention question — should
    # other tools also flatten? — is intentionally deferred to
    # `SEED-FLAT-SIGNATURE-AUDIT-V1.6+`.
    _FLAT_SIGNATURE_EXCEPTIONS = {"execute_python"}

    for mod in modules:
        # Resolve string annotations (from __future__ import annotations) per module
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("_"):
                continue
            if name in _FLAT_SIGNATURE_EXCEPTIONS:
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
            if not _is_basemodel_or_optional(first_ann):
                failures.append(
                    f"{mod.__name__}.{name}: first param is {first_ann!r}, "
                    "not a BaseModel or Optional[BaseModel]"
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
