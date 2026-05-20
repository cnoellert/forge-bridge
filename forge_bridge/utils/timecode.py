"""
Flame timecode substrate normalization utility.

ARCHITECTURAL ROLE
------------------
This is the first substrate normalization utility in forge-bridge.
It converts Flame-native serialized values (timecode strings) into
typed graph-layer values (integer frame counts) consumed by substrate
primitives such as FilterNode.

Architectural boundary (load-bearing):
    Flame-native representations stay INSIDE tool implementations.
    Substrate-native representations (frame integers) cross OUTWARD.
    This utility belongs at the tool-output adapter layer — called
    by tools before emitting segment dicts, never by the graph layer
    or chain engine directly.

FLAME TIMECODE FORMAT (empirically verified 2026-05-20)
-------------------------------------------------------
Flame uses different separators depending on frame rate and
drop-frame status. Verified against real Flame instances:

    23.976 fps      HH:MM:SS+FF     colon-colon-colon-plus
    24 fps          HH:MM:SS+FF     colon-colon-colon-plus
    25 fps          HH:MM:SS:FF     all colons
    29.97 NDF       HH:MM:SS:FF     all colons
    29.97 DF        HH;MM;SS;FF     all semicolons (drop-frame)
    30 fps          HH:MM:SS:FF     all colons
    50 fps          HH:MM:SS#FF     colon-colon-colon-hash
    59.94 NDF       HH:MM:SS#FF     colon-colon-colon-hash
    59.94 DF        HH;MM;SS#FF     semicolon-colon-semicolon-hash
    60 fps          HH:MM:SS#FF     colon-colon-colon-hash

Frame separator summary:
    +   used by 23.976 and 24 fps
    :   used by 25, 29.97 NDF, 30 fps
    #   used by 50, 59.94 NDF, 60 fps
    ;   TIME separator (not frame separator) signals drop-frame

Drop-frame detection: time component separator is ';' not ':'

DURATION SEMANTICS (empirically verified 2026-05-20)
-----------------------------------------------------
Flame record_out is EXCLUSIVE — one frame past the last frame.
Duration = timecode_to_frames(record_out) - timecode_to_frames(record_in)

Verification: 4-second 3-frame clip at 24fps:
    record_in  = '00:00:00+00'  →  0 frames
    record_out = '00:00:04+03'  →  99 frames
    duration   = 99 - 0 = 99 frames (4*24 + 3 = correct)
    out - in = 99, NOT 100. Exclusive end confirmed.

SUPPORTED / UNSUPPORTED
-----------------------
Supported:    all non-drop-frame formats listed above
Unsupported:  drop-frame (29.97 DF, 59.94 DF)
              → raises TimecodeParseError with code
                "drop_frame_not_supported"
              → error message names the escape route:
                "use flame_execute_python for DF timecode arithmetic"
"""

from __future__ import annotations

import math
import re

_TIMECODE_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[+:#](\d{2})$")


class TimecodeParseError(ValueError):
    """Raised when a timecode string cannot be parsed or converted.

    Attributes:
        code: machine-readable error code string
        message: human-readable description

    Codes:
        "invalid_format"           — string doesn't match any known pattern
        "component_out_of_range"   — hours/minutes/seconds/frames out of range
        "drop_frame_not_supported" — DF timecode detected; not supported in v1
        "invalid_frame_rate"       — frame_rate is zero, negative, or None
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def timecode_to_frames(tc: str, frame_rate: float) -> int:
    """Convert a Flame timecode string to an integer frame count.

    Args:
        tc:         Flame timecode string. Supported formats:
                        HH:MM:SS+FF  (23.976, 24 fps)
                        HH:MM:SS:FF  (25, 29.97 NDF, 30 fps)
                        HH:MM:SS#FF  (50, 59.94 NDF, 60 fps)
                    Flame wraps timecode strings in single quotes;
                    this function strips leading/trailing quotes
                    and whitespace before parsing.
        frame_rate: frames per second as float. Must be positive
                    and non-zero. Caller is responsible for
                    extracting fps from the Flame sequence object.

    Returns:
        Integer frame count from timecode zero.

    Raises:
        TimecodeParseError("drop_frame_not_supported", ...)
            if time separator is ';' (drop-frame detected)
        TimecodeParseError("invalid_format", ...)
            if string doesn't match any supported pattern
        TimecodeParseError("component_out_of_range", ...)
            if any component is outside valid range
        TimecodeParseError("invalid_frame_rate", ...)
            if frame_rate <= 0

    Notes:
        Timecode arithmetic uses nominal frame rate (math.ceil of
        actual fps). Non-drop-frame timecode at 23.976/29.97/59.94
        counts in whole frames per the 24/30/60 nominal rate;
        the fractional fps applies to playback timing, not timecode
        counting.

        Duration arithmetic: record_out is EXCLUSIVE in Flame.
        duration_frames = timecode_to_frames(record_out, fps)
                        - timecode_to_frames(record_in, fps)
    """
    if frame_rate is None or frame_rate <= 0:
        raise TimecodeParseError(
            "invalid_frame_rate",
            "frame_rate must be positive and non-zero",
        )

    if not isinstance(tc, str):
        raise TimecodeParseError(
            "invalid_format",
            f"timecode must be a string, got {type(tc).__name__}",
        )

    value = tc.strip().strip("\"'")
    if ";" in value:
        raise TimecodeParseError(
            "drop_frame_not_supported",
            "drop-frame timecode is not supported; use flame_execute_python "
            "for DF timecode arithmetic",
        )

    match = _TIMECODE_RE.match(value)
    if not match:
        raise TimecodeParseError(
            "invalid_format",
            f"timecode does not match supported Flame formats: {tc!r}",
        )

    hours, minutes, seconds, frames = (int(part) for part in match.groups())
    nominal_fps = math.ceil(frame_rate)
    if minutes > 59 or seconds > 59 or frames >= nominal_fps:
        raise TimecodeParseError(
            "component_out_of_range",
            f"timecode component out of range for {frame_rate:g} fps: {tc!r}",
        )

    total = (
        hours * 3600 * nominal_fps
        + minutes * 60 * nominal_fps
        + seconds * nominal_fps
        + frames
    )
    return int(total)
