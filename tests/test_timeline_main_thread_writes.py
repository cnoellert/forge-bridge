import ast
import json
import textwrap
from pathlib import Path

import pytest

from forge_bridge.tools import timeline


_WRITE_TOOL_CASES = [
    (
        timeline.set_segment_attribute,
        timeline.SetSegmentInput(
            sequence_name="30sec_21",
            segment_name="sh010",
            attribute="comment",
            value="approved",
        ),
    ),
    (
        timeline.set_start_frames,
        timeline.SetStartFramesInput(sequence_name="30sec_21", default_frame=1001),
    ),
    (
        timeline.create_version,
        timeline.CreateVersionInput(sequence_name="30sec_21"),
    ),
    (
        timeline.reconstruct_track,
        timeline.ReconstructTrackInput(
            sequence_name="30sec_21",
            source_version_index=0,
            source_track_index=0,
            target_version_index=1,
            target_track_index=0,
        ),
    ),
    (
        timeline.clone_version,
        timeline.CloneVersionInput(sequence_name="30sec_21"),
    ),
    (
        timeline.disconnect_segments,
        timeline.DisconnectSegmentsInput(
            reel_name="Sequences",
            sequence_name="30sec_21",
        ),
    ),
]


def _assert_payload_parses(code: str) -> None:
    ast.parse(textwrap.dedent(code).strip())


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool", "params"), _WRITE_TOOL_CASES)
async def test_main_thread_write_tools_reject_empty_host_result(
    monkeypatch,
    tool,
    params,
):
    async def _empty_result(_code: str, *, main_thread: bool = False):
        assert main_thread is True
        _assert_payload_parses(_code)
        return {}

    monkeypatch.setattr(timeline.bridge, "execute_json", _empty_result)

    data = json.loads(await tool(params))

    assert data["ok"] is False
    assert data["error"] == "host write did not complete (empty/no-op result)"
    assert data["raw"] == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool", "params"), _WRITE_TOOL_CASES)
async def test_main_thread_write_tools_pass_through_completed_host_result(
    monkeypatch,
    tool,
    params,
):
    expected = {"ok": True, "new_value": "x"}

    async def _completed_result(_code: str, *, main_thread: bool = False):
        assert main_thread is True
        _assert_payload_parses(_code)
        return expected

    monkeypatch.setattr(timeline.bridge, "execute_json", _completed_result)

    assert json.loads(await tool(params)) == expected


def test_no_main_thread_timeline_payload_schedules_idle_event():
    source_path = Path(timeline.__file__)
    source = source_path.read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Await):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if not (isinstance(func, ast.Attribute) and func.attr == "execute_json"):
            continue
        if not any(
            keyword.arg == "main_thread"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in call.keywords
        ):
            continue

        payload = ast.get_source_segment(source, call.args[0]) or ""
        assert "schedule_idle_event" not in payload
