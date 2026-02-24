"""Timeline tools — sequence, segment, and track operations."""

import json
from typing import Optional

from pydantic import BaseModel, Field

from forge_mcp import bridge


# ── Tool: flame_get_sequence_info ───────────────────────────────────────


class GetSequenceInput(BaseModel):
    """Input for getting sequence information."""

    sequence_name: str = Field(
        ...,
        description="Name of the sequence to inspect. Must match exactly "
        "(use flame_find_media to search first).",
    )
    include_segments: bool = Field(
        default=True,
        description="Include segment details (names, timecodes, sources).",
    )


async def get_sequence_info(params: GetSequenceInput) -> str:
    """Get detailed information about a sequence: duration, segments, tracks.

    Returns sequence properties and optionally all segments with their
    names, timecodes, source info, and metadata.
    """
    data = await bridge.execute_json(f"""
        import flame, json
        seq_name = {params.sequence_name!r}
        include_segs = {params.include_segments!r}

        # Find the sequence
        found = flame.find_by_name(seq_name)
        if not found:
            print(json.dumps({{'error': f'Sequence "{{seq_name}}" not found'}}))
        else:
            seq = found[0]
            info = {{
                'name': seq.name.get_value(),
                'duration': str(seq.duration),
                'frame_rate': str(seq.frame_rate),
                'width': seq.width,
                'height': seq.height,
                'start_frame': seq.start_frame,
                'ratio': str(seq.ratio),
                'scan_mode': str(seq.scan_mode),
                'bit_depth': str(seq.bit_depth),
            }}

            if include_segs:
                segments = []
                for ver in seq.versions:
                    for track in ver.tracks:
                        track_name = track.name.get_value() if hasattr(track.name, 'get_value') else str(track.name)
                        for seg in track.segments:
                            seg_info = {{
                                'name': seg.name.get_value() if hasattr(seg.name, 'get_value') else str(seg.name),
                                'shot_name': seg.shot_name.get_value() if hasattr(seg.shot_name, 'get_value') else '',
                                'record_in': str(seg.record_in),
                                'record_out': str(seg.record_out),
                                'record_duration': str(seg.record_duration),
                                'source_in': str(seg.source_in),
                                'source_out': str(seg.source_out),
                                'source_name': seg.source_name,
                                'tape_name': str(seg.tape_name),
                                'track': track_name,
                                'file_path': str(seg.file_path) if seg.file_path else None,
                                'hidden': seg.hidden.get_value() if hasattr(seg.hidden, 'get_value') else False,
                            }}
                            try:
                                seg_info['comment'] = seg.comment.get_value()
                            except:
                                seg_info['comment'] = ''
                            segments.append(seg_info)
                info['segments'] = segments
                info['segment_count'] = len(segments)

            print(json.dumps(info))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_set_segment_attribute ───────────────────────────────────


class SetSegmentInput(BaseModel):
    """Input for setting a segment attribute."""

    sequence_name: str = Field(
        ..., description="Name of the parent sequence."
    )
    segment_name: str = Field(
        ...,
        description="Name of the segment to modify. Use get_sequence_info "
        "to list segments first.",
    )
    attribute: str = Field(
        ...,
        description="Attribute to set. Common: 'name', 'shot_name', "
        "'comment', 'colour', 'hidden', 'selected'.",
    )
    value: str = Field(
        ...,
        description="New value as string. Booleans: 'true'/'false'. "
        "Colours: '(r,g,b)' as 0-1 floats.",
    )


async def set_segment_attribute(params: SetSegmentInput) -> str:
    """Set an attribute on a timeline segment.

    Runs on Flame's main thread via schedule_idle_event. Use
    get_sequence_info first to find the exact segment name.
    """
    # Parse value type
    value_code = f"'{params.value}'"
    if params.value.lower() in ("true", "false"):
        value_code = params.value.capitalize()
    elif params.value.startswith("(") and params.value.endswith(")"):
        value_code = params.value  # tuple literal

    data = await bridge.execute_json(f"""
        import flame, json, threading
        seq_name = {params.sequence_name!r}
        seg_name = {params.segment_name!r}
        attr_name = {params.attribute!r}
        new_value = {value_code}

        found = flame.find_by_name(seq_name)
        if not found:
            print(json.dumps({{'error': f'Sequence "{{seq_name}}" not found'}}))
        else:
            seq = found[0]
            target = None
            for ver in seq.versions:
                for track in ver.tracks:
                    for seg in track.segments:
                        name = seg.name.get_value() if hasattr(seg.name, 'get_value') else str(seg.name)
                        if str(name) == seg_name:
                            target = seg
                            break
                    if target: break
                if target: break

            if not target:
                print(json.dumps({{'error': f'Segment "{{seg_name}}" not found in "{{seq_name}}"'}}))
            else:
                event = threading.Event()
                result = {{}}
                def _do():
                    try:
                        attr = getattr(target, attr_name)
                        attr.set_value(new_value)
                        result['ok'] = True
                        result['attribute'] = attr_name
                        result['new_value'] = str(attr.get_value())
                    except Exception as e:
                        result['error'] = str(e)
                    event.set()

                flame.schedule_idle_event(_do)
                event.wait(timeout=10)
                print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_bulk_rename_segments ────────────────────────────────────


class BulkRenameInput(BaseModel):
    """Input for bulk segment renaming."""

    sequence_name: str = Field(..., description="Name of the parent sequence.")
    attribute: str = Field(
        default="shot_name",
        description="Which attribute to rename: 'name', 'shot_name', or 'comment'.",
    )
    find: str = Field(..., description="Substring to find (case-sensitive).")
    replace: str = Field(..., description="Replacement string.")


async def bulk_rename_segments(params: BulkRenameInput) -> str:
    """Find-and-replace across all segment names/shot_names in a sequence.

    Runs on Flame's main thread. Returns count of segments modified.
    """
    data = await bridge.execute_json(f"""
        import flame, json, threading
        seq_name = {params.sequence_name!r}
        attr_name = {params.attribute!r}
        find_str = {params.find!r}
        replace_str = {params.replace!r}

        found = flame.find_by_name(seq_name)
        if not found:
            print(json.dumps({{'error': f'Sequence "{{seq_name}}" not found'}}))
        else:
            seq = found[0]
            targets = []
            for ver in seq.versions:
                for track in ver.tracks:
                    for seg in track.segments:
                        attr = getattr(seg, attr_name, None)
                        if attr and hasattr(attr, 'get_value'):
                            val = str(attr.get_value())
                            if find_str in val:
                                targets.append((seg, attr, val))

            event = threading.Event()
            result = {{'modified': 0, 'changes': []}}
            def _do():
                for seg, attr, old_val in targets:
                    new_val = old_val.replace(find_str, replace_str)
                    attr.set_value(new_val)
                    result['changes'].append({{'old': old_val, 'new': new_val}})
                    result['modified'] += 1
                event.set()

            flame.schedule_idle_event(_do)
            event.wait(timeout=30)
            print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)
