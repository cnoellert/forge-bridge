import pytest

from forge_bridge.utils.timecode import TimecodeParseError, timecode_to_frames


def test_timecode_format_verification_ground_truth_fixtures():
    assert timecode_to_frames("00:00:00+00", 24.0) == 0
    assert timecode_to_frames("00:00:04+03", 24.0) == 99
    assert timecode_to_frames("00:00:04+03", 23.976) == 99
    assert timecode_to_frames("00:00:04:03", 25.0) == 103
    assert timecode_to_frames("00:00:04:04", 29.97) == 124
    assert timecode_to_frames("00:00:04:04", 30.0) == 124
    assert timecode_to_frames("00:00:04#07", 50.0) == 207
    assert timecode_to_frames("00:00:04#09", 59.94) == 249
    assert timecode_to_frames("00:00:04#09", 60.0) == 249


def test_timecode_strips_flame_outer_quotes():
    assert timecode_to_frames("'00:00:04+03'", 24.0) == 99


@pytest.mark.parametrize("value,frame_rate", [
    ("00;00;04;04", 29.97),
    ("00;00;04#09", 59.94),
])
def test_timecode_rejects_drop_frame(value, frame_rate):
    with pytest.raises(TimecodeParseError) as exc_info:
        timecode_to_frames(value, frame_rate)

    assert exc_info.value.code == "drop_frame_not_supported"
    assert "flame_execute_python" in exc_info.value.message


def test_timecode_rejects_invalid_format():
    with pytest.raises(TimecodeParseError) as exc_info:
        timecode_to_frames("not_a_timecode", 24.0)

    assert exc_info.value.code == "invalid_format"


@pytest.mark.parametrize("frame_rate", [0.0, -1.0])
def test_timecode_rejects_invalid_frame_rate(frame_rate):
    with pytest.raises(TimecodeParseError) as exc_info:
        timecode_to_frames("00:00:04+03", frame_rate)

    assert exc_info.value.code == "invalid_frame_rate"


def test_timecode_duration_arithmetic_uses_exclusive_record_out():
    duration = (
        timecode_to_frames("00:00:04+03", 24.0)
        - timecode_to_frames("00:00:00+00", 24.0)
    )

    assert duration == 99


def test_timecode_accepts_frame_component_at_fps_limit_minus_one():
    assert timecode_to_frames("00:00:00:24", 25.0) == 24


def test_timecode_rejects_frame_component_at_fps_limit():
    with pytest.raises(TimecodeParseError) as exc_info:
        timecode_to_frames("00:00:00:25", 25.0)

    assert exc_info.value.code == "component_out_of_range"


def test_timecode_uses_nominal_frame_rate_for_ndf_counting():
    assert timecode_to_frames("01:00:00+00", 23.976) == 86400
    assert timecode_to_frames("01:00:00:00", 29.97) == 108000
    assert timecode_to_frames("01:00:00#00", 59.94) == 216000
