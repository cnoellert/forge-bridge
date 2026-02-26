"""Timeline tools — sequence inspection, rename, and start frame operations.

All segment metadata follows the FORGE naming convention:
  {shot_name}_{role}[_{qualifier}]_L{track##}
  e.g. noise_010_graded_L01, tst_020_raw_alt_L02

Key Flame API facts (Flame 2026, discovered in production):
  - Traverse: seq.versions → version.tracks → track.segments
  - seq.tracks returns None — always go via seq.versions
  - seg.source_name — non-empty = real segment, empty/None = gap/filler
  - seg.head — head handle frames (source_in for start frame math)
  - seg.record_in / seg.record_out — edit timecodes (for shot propagation)
  - seg.file_path — source media path (for role detection via footage/{role}/)
  - seg.shot_name — shot name attribute (has .get_value() / .set_value())
  - seg.name — segment name attribute (has .get_value() / .set_value())
  - seg.change_start_frame(n) — sets clip start frame directly on segment
  - Set ops require main_thread=True via bridge
  - seg.uid returns None in Flame 2026 — name is the stable key
"""

import json
from typing import Optional

from pydantic import BaseModel, Field

from forge_mcp import bridge


# ── Shared helpers ─────────────────────────────────────────────────────

_COLLECT_CODE = """
KNOWN_ROLES = ['graded', 'raw', 'denoised', 'flat', 'external', 'scans', 'stock', 'source']

import re as _re

def _detect_role(file_path):
    if not file_path:
        return None
    m = _re.search(r'footage/([^/]+)/', str(file_path))
    if m and m.group(1) in KNOWN_ROLES:
        return m.group(1)
    return None

def _find_seq(name):
    desk = flame.projects.current_project.current_workspace.desktop
    for rg in desk.reel_groups:
        for reel in rg.reels:
            for seq in (reel.sequences or []):
                if str(seq.name) == name or str(seq.name).strip("'") == name:
                    return seq
    return None

def _collect_segments(seq):
    '''Return all non-gap segments with full metadata, grouped by track.
    Each entry: {
        track_idx, track_name, seg_name, shot_name, role, head,
        record_in, record_out, source_name, file_path, start_frame
    }
    '''
    result = []
    tracks = []
    for ver in seq.versions:
        for track in ver.tracks:
            tracks.append(track)
    for ti, track in enumerate(tracks):
        track_name = str(track.name) if track.name else ''
        layer_num  = str(ti + 1).zfill(2)
        for seg in track.segments:
            src = str(seg.source_name) if seg.source_name else ''
            if not src:
                continue   # gap / filler
            fp = ''
            try:
                fp = str(seg.file_path) if seg.file_path else ''
            except Exception:
                pass
            seg_name  = ''
            shot_name = ''
            try:
                seg_name  = seg.name.get_value()  if hasattr(seg.name,      'get_value') else str(seg.name)
                shot_name = seg.shot_name.get_value() if hasattr(seg.shot_name, 'get_value') else str(seg.shot_name)
            except Exception:
                pass
            head = 0
            try:
                head = int(seg.head)
            except Exception:
                pass
            result.append({
                'track_idx':   ti,
                'track_name':  track_name,
                'layer_num':   layer_num,
                'seg_name':    seg_name,
                'shot_name':   shot_name,
                'source_name': src,
                'file_path':   fp,
                'role':        _detect_role(fp) or 'source',
                'head':        head,
                'record_in':   str(seg.record_in),
                'record_out':  str(seg.record_out),
                'start_frame': int(seg.start_frame) if seg.start_frame else None,
            })
    return result
"""


# ── Tool: flame_get_sequence_segments ─────────────────────────────────


class GetSegmentsInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")


async def get_sequence_segments(params: GetSegmentsInput) -> str:
    """Get all segments from a sequence with full FORGE metadata.

    Returns every non-gap segment across all tracks with:
    - Parsed FORGE name (shot_name, role, layer from segment name)
    - Source metadata: file_path, source_name, head handles
    - Edit position: record_in, record_out
    - Start frame (for start frame workflow)
    - Role auto-detected from footage/{role}/ path pattern

    This is the primary inspection tool before running rename or
    set_start_frames. The metadata here drives both workflows.
    """
    data = await bridge.execute_json(f"""
import flame, json
{_COLLECT_CODE}

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{'error': 'Sequence not found: ' + {params.sequence_name!r}}}))
else:
    segs = _collect_segments(seq)
    # Also parse FORGE name components if segment has been renamed
    import re as _re2
    for s in segs:
        m = _re2.match(r'^([A-Za-z]\\w+_\\d+)_(.+)_L(\\d+)$', s['seg_name'])
        s['forge_shot']  = m.group(1) if m else ''
        s['forge_role']  = m.group(2) if m else ''
        s['forge_layer'] = int(m.group(3)) if m else 0
    print(json.dumps({{'sequence': {params.sequence_name!r}, 'segments': segs, 'count': len(segs)}}))
""")
    return json.dumps(data, indent=2)


# ── Tool: flame_preview_rename ─────────────────────────────────────────


class PreviewRenameInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")
    prefix:    str = Field(...,  description="Shot name prefix e.g. 'noise', 'tst'")
    increment: int = Field(10,   description="Shot number step (default 10)")
    padding:   int = Field(3,    description="Zero-pad width for shot number (default 3)")
    start:     int = Field(1,    description="Starting shot counter — first shot = start × increment")


async def preview_rename(params: PreviewRenameInput) -> str:
    """Preview the rename result for a sequence without making any changes.

    Shows what each segment will be renamed to using FORGE convention:
      {shot_name}_{role}_L{track##}

    Background track (L01) segments drive shot numbering. Upper track
    segments inherit the shot name of whichever L01 segment their
    record_in falls within.

    Use this to verify names before running flame_rename_shots.
    """
    data = await bridge.execute_json(f"""
import flame, json
{_COLLECT_CODE}

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{'error': 'Sequence not found: ' + {params.sequence_name!r}}}))
else:
    segs = _collect_segments(seq)
    prefix    = {params.prefix!r}
    increment = {params.increment!r}
    padding   = {params.padding!r}
    start     = {params.start!r}

    # Build shot map from background track (track_idx == 0)
    bg_map = []   # [(shot_name, record_in, record_out), ...]
    shot_num = start
    for s in segs:
        if s['track_idx'] != 0:
            continue
        num_str   = str(shot_num * increment).zfill(padding)
        shot_name = f"{{prefix}}_{{num_str}}"
        bg_map.append((shot_name, s['record_in'], s['record_out']))
        shot_num += 1

    # Assign shot names and build preview
    preview = []
    for s in segs:
        if s['track_idx'] == 0:
            num_str   = str(start * increment).zfill(padding)
            # find by position in bg_map
            bg_idx = sum(1 for x in segs[:segs.index(s)] if x['track_idx'] == 0)
            shot_name = bg_map[bg_idx][0] if bg_idx < len(bg_map) else ''
        else:
            shot_name = ''
            for bg_shot, bg_in, bg_out in bg_map:
                if bg_in <= s['record_in'] <= bg_out:
                    shot_name = bg_shot
                    break

        if not shot_name:
            continue

        new_name = f"{{shot_name}}_{{s['role']}}_L{{s['layer_num']}}"
        preview.append({{
            'track':     s['track_idx'],
            'layer':     s['layer_num'],
            'old_name':  s['seg_name'],
            'new_name':  new_name,
            'shot_name': shot_name,
            'role':      s['role'],
            'file_path': s['file_path'],
        }})

    print(json.dumps({{'sequence': {params.sequence_name!r}, 'preview': preview, 'count': len(preview)}}))
""")
    return json.dumps(data, indent=2)


# ── Tool: flame_rename_shots ───────────────────────────────────────────


class RenameInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")
    prefix:        str = Field(..., description="Shot name prefix e.g. 'noise', 'tst'")
    increment:     int = Field(10,  description="Shot number step (default 10)")
    padding:       int = Field(3,   description="Zero-pad width (default 3)")
    start:         int = Field(1,   description="Starting shot counter")
    role_overrides: dict = Field(
        default={},
        description="Override roles by segment index: {'0': 'graded', '2': 'raw'}"
    )
    qualifier_overrides: dict = Field(
        default={},
        description="Override qualifiers by segment index: {'1': 'alt'}"
    )


async def rename_shots(params: RenameInput) -> str:
    """Rename all shots and segments on a sequence using FORGE convention.

    Three-step process (matches forge_rename hook exactly):
    1. Assign shot names on background track: {prefix}_{NNN}
    2. Propagate shot names to upper tracks by record_in timecode overlap
    3. Rename all segments: {shot_name}_{role}[_{qualifier}]_L{track##}

    Role is auto-detected from footage/{role}/ in the source file path.
    Use role_overrides to force specific roles by segment index.

    Runs on Flame's main thread (required for set_value calls).
    Returns counts of shots_assigned, propagated, renamed, skipped.
    """
    data = await bridge.execute_json(f"""
import flame, json, threading
{_COLLECT_CODE}

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{'error': 'Sequence not found: ' + {params.sequence_name!r}}}))
else:
    prefix              = {params.prefix!r}
    increment           = {params.increment!r}
    padding             = {params.padding!r}
    start               = {params.start!r}
    role_overrides      = {{{', '.join(f'{int(k)}: {v!r}' for k, v in params.role_overrides.items())}}}
    qualifier_overrides = {{{', '.join(f'{int(k)}: {v!r}' for k, v in params.qualifier_overrides.items())}}}

    result = {{'shots_assigned': 0, 'propagated': 0, 'renamed': 0, 'skipped': 0, 'changes': []}}
    event  = threading.Event()

    def _do():
        try:
            tracks = []
            for ver in seq.versions:
                for track in ver.tracks:
                    tracks.append(track)

            # Pass 1: assign shot names on background track, build bg_map
            bg_map   = []   # [(shot_name, record_in_str, record_out_str)]
            shot_num = start
            for seg in tracks[0].segments:
                src = str(seg.source_name) if seg.source_name else ''
                if not src:
                    bg_map.append((None, str(seg.record_in), str(seg.record_out)))
                    continue
                num_str   = str(shot_num * increment).zfill(padding)
                shot_name = f"{{prefix}}_{{num_str}}"
                seg.shot_name.set_value(shot_name)
                bg_map.append((shot_name, str(seg.record_in), str(seg.record_out)))
                result['shots_assigned'] += 1
                shot_num += 1

            # Pass 2: propagate shot names to upper tracks
            for ti in range(1, len(tracks)):
                for seg in tracks[ti].segments:
                    src = str(seg.source_name) if seg.source_name else ''
                    if not src:
                        continue
                    seg_in = str(seg.record_in)
                    for bg_shot, bg_in, bg_out in bg_map:
                        if bg_shot and bg_in <= seg_in <= bg_out:
                            seg.shot_name.set_value(bg_shot)
                            result['propagated'] += 1
                            break

            # Pass 3: rename all segments
            seg_idx = 0
            for ti, track in enumerate(tracks):
                layer_num = str(ti + 1).zfill(2)
                for seg in track.segments:
                    src = str(seg.source_name) if seg.source_name else ''
                    if not src:
                        result['skipped'] += 1
                        continue
                    shot_name = seg.shot_name.get_value() if hasattr(seg.shot_name, 'get_value') else ''
                    if not shot_name:
                        result['skipped'] += 1
                        continue
                    if seg_idx in role_overrides:
                        role = role_overrides[seg_idx]
                    else:
                        fp = ''
                        try: fp = str(seg.file_path) if seg.file_path else ''
                        except: pass
                        role = _detect_role(fp) or 'source'
                    qualifier = qualifier_overrides.get(seg_idx, '')
                    old_name  = seg.name.get_value() if hasattr(seg.name, 'get_value') else ''
                    if qualifier:
                        new_name = f"{{shot_name}}_{{role}}_{{qualifier}}_L{{layer_num}}"
                    else:
                        new_name = f"{{shot_name}}_{{role}}_L{{layer_num}}"
                    seg.name.set_value(new_name)
                    result['changes'].append({{'seg_idx': seg_idx, 'old': old_name, 'new': new_name}})
                    result['renamed'] += 1
                    seg_idx += 1
        except Exception as e:
            result['error'] = str(e)
        event.set()

    flame.schedule_idle_event(_do)
    event.wait(timeout=60)
    print(json.dumps(result))
""", main_thread=True)
    return json.dumps(data, indent=2)


# ── Tool: flame_preview_start_frames ──────────────────────────────────


class PreviewStartFramesInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")
    default_frame: int = Field(1001, description="Default target start frame")


async def preview_start_frames(params: PreviewStartFramesInput) -> str:
    """Preview start frame assignments for a sequence — background track only.

    Returns one row per shot showing:
    - shot_name, seg_name
    - head: handle frames before the cut point (seg.head)
    - target: the proposed start frame (default_frame)
    - clip_start: target - head (actual first frame of clip material)
    - valid: False if clip_start < 0 (Flame cannot write negative frame numbers)

    Math: clip.change_start_frame(target - head)
    Frame 'target' will be the first visible frame. Head handles run
    from clip_start to target-1.

    Use this before flame_set_start_frames to check for negative frame issues.
    """
    data = await bridge.execute_json(f"""
import flame, json
{_COLLECT_CODE}

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{'error': 'Sequence not found: ' + {params.sequence_name!r}}}))
else:
    default_frame = {params.default_frame!r}
    segs = _collect_segments(seq)
    rows = []
    for s in segs:
        head        = s['head']
        clip_start  = default_frame - head
        rows.append({{
            'shot_name':   s['shot_name'],
            'seg_name':    s['seg_name'],
            'track':       s['track_idx'],
            'layer':       s['layer_num'],
            'head':        head,
            'target':      default_frame,
            'clip_start':  clip_start,
            'valid':       clip_start >= 0,
            'current_start_frame': s['start_frame'],
        }})
    invalid = [r['shot_name'] or r['seg_name'] for r in rows if not r['valid']]
    print(json.dumps({{
        'sequence':      {params.sequence_name!r},
        'default_frame': default_frame,
        'shot_count':    len(rows),
        'invalid_count': len(invalid),
        'invalid_shots': invalid,
        'rows':          rows,
    }}))
""")
    return json.dumps(data, indent=2)


# ── Tool: flame_set_start_frames ──────────────────────────────────────


class SetStartFramesInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")
    default_frame: int = Field(1001, description="Target start frame for all shots")
    overrides: dict = Field(
        default={},
        description="Per-shot overrides: {'noise_010': 1001, 'noise_020': 1101}"
    )


async def set_start_frames(params: SetStartFramesInput) -> str:
    """Set the composite start frame for all shots on a sequence.

    Processes all tracks (not just L01) — timelines are typically multi-track
    and every non-gap segment needs its start frame set.

    Calls seg.change_start_frame(target) directly — target is the absolute
    frame number (e.g. 1001). Flame handles the head handle offset internally.
    'Clip Starts At' (target - head) is informational only; it tells you what
    frame the clip material actually begins at, and is negative if handles
    exceed the target — that's the only invalid case.

    Default target applies to all shots. Use overrides dict for per-shot
    exceptions: {'noise_010': 1001, 'noise_020': 1101}

    Runs on Flame's main thread. Returns results per shot.
    """
    data = await bridge.execute_json(f"""
import flame, json, threading
{_COLLECT_CODE}

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{'error': 'Sequence not found: ' + {params.sequence_name!r}}}))
else:
    default_frame = {params.default_frame!r}
    overrides     = {params.overrides!r}

    result = {{'applied': 0, 'skipped': 0, 'errors': [], 'changes': []}}
    event  = threading.Event()

    def _do():
        try:
            tracks = []
            for ver in seq.versions:
                for track in ver.tracks:
                    tracks.append(track)

            for track in tracks:
                for seg in track.segments:
                    if not seg.source_name:
                        continue
                    shot_name = ''
                    try:
                        shot_name = seg.shot_name.get_value() if hasattr(seg.shot_name, 'get_value') else str(seg.shot_name)
                    except: pass
                    target = overrides.get(shot_name, default_frame)
                    head   = 0
                    try: head = int(seg.head)
                    except: pass
                    clip_start = target - head   # informational — negative = invalid
                    if clip_start < 0:
                        result['errors'].append(f"{{shot_name}}: clip_start={{clip_start}} < 0, skipped")
                        result['skipped'] += 1
                        continue
                    try:
                        seg.change_start_frame(target)
                        result['changes'].append({{'shot': shot_name, 'target': target, 'head': head, 'clip_start': clip_start}})
                        result['applied'] += 1
                    except Exception as e:
                        result['errors'].append(f"{{shot_name}}: {{e}}")
                        result['skipped'] += 1
        except Exception as e:
            result['error'] = str(e)
        event.set()

    flame.schedule_idle_event(_do)
    event.wait(timeout=60)
    print(json.dumps(result))
""", main_thread=True)
    return json.dumps(data, indent=2)


# ── Tool: flame_set_segment_attribute (kept, unchanged) ────────────────


class SetSegmentInput(BaseModel):
    sequence_name: str = Field(..., description="Name of the parent sequence.")
    segment_name:  str = Field(..., description="Name of the segment to modify.")
    attribute:     str = Field(..., description="Attribute to set: 'name', 'shot_name', 'comment'.")
    value:         str = Field(..., description="New value as string.")


async def set_segment_attribute(params: SetSegmentInput) -> str:
    """Set an attribute on a single timeline segment.

    For bulk operations use flame_rename_shots or flame_set_start_frames.
    Runs on Flame's main thread.
    """
    value_code = f"'{params.value}'"
    if params.value.lower() in ("true", "false"):
        value_code = params.value.capitalize()
    elif params.value.startswith("(") and params.value.endswith(")"):
        value_code = params.value

    data = await bridge.execute_json(f"""
import flame, json, threading
{_COLLECT_CODE}

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{'error': 'Sequence not found'}}))
else:
    attr_name = {params.attribute!r}
    new_value = {value_code}
    target = None
    for ver in seq.versions:
        for track in ver.tracks:
            for seg in track.segments:
                name = seg.name.get_value() if hasattr(seg.name, 'get_value') else str(seg.name)
                if str(name) == {params.segment_name!r}:
                    target = seg
                    break
            if target: break
        if target: break

    if not target:
        print(json.dumps({{'error': 'Segment not found: ' + {params.segment_name!r}}}))
    else:
        event  = threading.Event()
        result = {{}}
        def _do():
            try:
                attr = getattr(target, attr_name)
                attr.set_value(new_value)
                result['ok']        = True
                result['attribute'] = attr_name
                result['new_value'] = str(attr.get_value())
            except Exception as e:
                result['error'] = str(e)
            event.set()
        flame.schedule_idle_event(_do)
        event.wait(timeout=10)
        print(json.dumps(result))
""", main_thread=True)
    return json.dumps(data, indent=2)
