from types import SimpleNamespace

import pytest

from forge_bridge.tools import timeline
from forge_bridge.tools.timeline import _COLLECT_CODE


def test_find_seq_tier3_strips_flame_quote_wrapped_sequence_name():
    seq = SimpleNamespace(name="'30sec 21'")
    reel = SimpleNamespace(sequences=[seq])
    reel_group = SimpleNamespace(reels=[reel])
    desktop = SimpleNamespace(reel_groups=[reel_group])
    workspace = SimpleNamespace(desktop=desktop)
    project = SimpleNamespace(current_workspace=workspace)
    flame = SimpleNamespace(
        projects=SimpleNamespace(current_project=project),
    )
    namespace = {"flame": flame}

    exec(_COLLECT_CODE, namespace)

    assert namespace["_find_seq"]("30sec_21") is seq


def _fake_flame_for_quoted_sequence(seq):
    reel = SimpleNamespace(sequences=[seq])
    reel_group = SimpleNamespace(reels=[reel])
    desktop = SimpleNamespace(reel_groups=[reel_group])
    workspace = SimpleNamespace(desktop=desktop)
    project = SimpleNamespace(current_workspace=workspace)
    return SimpleNamespace(projects=SimpleNamespace(current_project=project))


@pytest.mark.parametrize(
    ("func", "params"),
    [
        (
            timeline.inspect_sequence_versions,
            timeline.InspectVersionsInput(sequence_name="30sec_21"),
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
                target_version_index=0,
                target_track_index=0,
                scratch_reel_name="Reel A",
            ),
        ),
        (
            timeline.clone_version,
            timeline.CloneVersionInput(
                sequence_name="30sec_21",
                source_version_index=0,
                scratch_reel_name="Reel A",
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_affected_sequence_tools_use_shared_quote_strip_ladder(
    monkeypatch,
    func,
    params,
):
    seq = SimpleNamespace(name="'30sec 21'")

    async def fake_execute_json(code, **_kwargs):
        assert "sname_stripped = sname.strip" in code
        assert "s.name.get_value() == name" not in code

        namespace = {"flame": _fake_flame_for_quoted_sequence(seq)}
        exec(_COLLECT_CODE, namespace)
        assert namespace["_find_seq"]("30sec_21") is seq
        return {"ok": True}

    monkeypatch.setattr(timeline.bridge, "execute_json", fake_execute_json)

    await func(params)
