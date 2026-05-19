from types import SimpleNamespace

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
