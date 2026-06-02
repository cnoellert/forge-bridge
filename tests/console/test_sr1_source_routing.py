from __future__ import annotations

from types import SimpleNamespace

from forge_bridge.console._source_route import apply_source_routing


def _tool(name: str):
    return SimpleNamespace(name=name)


def _tools():
    return [
        _tool("flame_get_sequence_segments"),
        _tool("forge_get_shot"),
        _tool("forge_list_shots"),
        _tool("flame_list_desktop"),
        _tool("flame_set_start_frames"),
    ]


def test_sr1_sequence_ref_rewrites_forge_get_shot_to_sequence_segments():
    routed = apply_source_routing(
        "what is the path to shot 10 on 30sec 21",
        ["forge_get_shot"],
        _tools(),
    )

    assert routed == ["flame_get_sequence_segments 30sec 21"]
    assert "30sec 21" in routed[0]


def test_sr1_sequence_ref_rewrites_forge_list_shots_to_sequence_segments():
    routed = apply_source_routing(
        "list shots on 30sec 21",
        ["forge_list_shots"],
        _tools(),
    )

    assert routed == ["flame_get_sequence_segments 30sec 21"]


def test_sr1_no_sequence_ref_returns_steps_unchanged():
    steps = ["forge_get_shot"]

    assert apply_source_routing("what is the path to shot 10", steps, _tools()) is steps


def test_sr1_non_shot_read_is_unchanged_with_sequence_ref():
    routed = apply_source_routing(
        "show desktop for 30sec 21",
        ["flame_list_desktop"],
        _tools(),
    )

    assert routed == ["flame_list_desktop"]


def test_sr1_mutating_step_is_never_rewritten():
    routed = apply_source_routing(
        "set start frames on 30sec 21",
        ["flame_set_start_frames"],
        _tools(),
    )

    assert routed == ["flame_set_start_frames"]


def test_sr1_qualified_sequence_ref_preserves_operator_reference():
    routed = apply_source_routing(
        "what is the duration of shot 10 on 30sec_edit 21",
        ["forge_get_shot"],
        _tools(),
    )

    assert routed == ["flame_get_sequence_segments 30sec_edit 21"]


def test_sr1_normalizes_existing_sequence_segment_step_to_prompt_reference():
    routed = apply_source_routing(
        "what is the duration of shot 10 on 30sec_edit 21",
        ["flame_get_sequence_segments 30sec_edit_21"],
        _tools(),
    )

    assert routed == ["flame_get_sequence_segments 30sec_edit 21"]
