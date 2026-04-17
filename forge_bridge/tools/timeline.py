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

from forge_bridge import bridge


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

            # Pass 1: assign shot names on background track, build bg_map.
            # When T0 has a gap, scan upward tracks (T1, T2, ...) for a real
            # segment covering the gap range and use it as the gap fill.
            # This prevents silent shot-number skips when T0 has a hole but
            # an upper track covers the cut.
            bg_map     = []   # [(shot_name, record_in_str, record_out_str)]
            gap_fills  = set()  # id() of segments used as gap fills
            shot_num   = start
            for seg in tracks[0].segments:
                src = str(seg.source_name) if seg.source_name else ''
                if not src:
                    # Gap on T0 — scan upward tracks for a real segment
                    gap_in  = str(seg.record_in)
                    gap_out = str(seg.record_out)
                    fill_seg = None
                    for fti in range(1, len(tracks)):
                        for fseg in tracks[fti].segments:
                            fsrc = str(fseg.source_name) if fseg.source_name else ''
                            if not fsrc:
                                continue
                            if gap_in <= str(fseg.record_in) <= gap_out:
                                fill_seg = fseg
                                break
                        if fill_seg:
                            break
                    if fill_seg is not None:
                        num_str   = str(shot_num * increment).zfill(padding)
                        shot_name = f"{{prefix}}_{{num_str}}"
                        fill_seg.shot_name.set_value(shot_name)
                        bg_map.append((shot_name, gap_in, gap_out))
                        gap_fills.add(id(fill_seg))
                        result['shots_assigned'] += 1
                        shot_num += 1
                    else:
                        bg_map.append((None, gap_in, gap_out))
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
                    if id(seg) in gap_fills:
                        # Already named in Pass 1 as a T0 gap fill — skip
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


# ── Sequence Editing Guide ──────────────────────────────────────────────


class GetSequenceEditingGuide(BaseModel):
    """Return the authoritative guide for editing sequences together in Flame 2026.

    Returns a structured recipe covering:
    - How to assemble clips into a sequence using overwrite()
    - Which copy method to use (copy_to_media_panel vs import_clips) and why
    - How to handle source timecode / handles correctly
    - Known crashes and gotchas (flame.delete on active sequences, etc.)
    - Openclip version switching and nbTicks
    - Cleanup patterns

    Use this tool before writing any sequence assembly code to ensure you
    follow the correct API patterns and avoid known crashes.
    """
    topic: Optional[str] = Field(
        default=None,
        description=(
            "Optional topic filter. One of: 'overwrite', 'copy_methods', "
            "'timecode', 'openclip', 'crashes', 'cleanup', 'full'. "
            "Defaults to 'full' (all topics)."
        ),
    )


async def get_sequence_editing_guide(params: GetSequenceEditingGuide) -> str:
    """Return the Flame 2026 sequence editing guide."""

    guide = {
        "overwrite": {
            "title": "Assembling clips into a sequence with overwrite()",
            "summary": (
                "PySequence.overwrite(clip, record_in, track_index) places a PyClip "
                "at a specific timeline position. record_in is a PyTime or timecode "
                "string (e.g. '10:00:00+12'). track_index is 0-based int."
            ),
            "example": (
                "clip = seg.copy_to_media_panel(scratch_reel)\n"
                "ok = assembled_seq.overwrite(clip, record_in='10:00:00+12', track_index=0)\n"
                "flame.delete(clip, confirm=False)  # clean up scratch clip"
            ),
            "gotchas": [
                "overwrite() uses the clip's source_in/source_out as already set — "
                "you cannot pass a separate source offset.",
                "Returns bool. False means the overwrite failed silently.",
                "track_index must exist in the sequence — you cannot overwrite onto "
                "a track that has no content yet.",
            ],
        },
        "copy_methods": {
            "title": "copy_to_media_panel vs import_clips",
            "table": {
                "copy_to_media_panel": {
                    "preserves_source_in_handles": True,
                    "preserves_openclip_versions": "API says 1 version, but full structure works in Flame UI",
                    "use_for": "V1 assembly — always use this for sequence-to-sequence copying",
                },
                "import_clips": {
                    "preserves_source_in_handles": False,
                    "preserves_openclip_versions": True,
                    "use_for": "DO NOT use for assembly — loses source_in offset (places from frame 0)",
                },
            },
            "recommendation": (
                "Always use copy_to_media_panel when assembling segments from "
                "one sequence into another. Although the Python API reports "
                "len(clip.versions) == 1, the openclip file on disk retains its "
                "full multi-version structure and Flame's version switcher works correctly."
            ),
        },
        "timecode": {
            "title": "Source timecode, handles, and source_in",
            "key_facts": [
                "seg.source_in is READ-ONLY after placement — cannot be set.",
                "seg.mark_in / seg.mark_out on PyClip are also NOT settable.",
                "The source_in is baked into the clip at export time by Flame's exporter.",
                "copy_to_media_panel preserves the original source_in — this is why "
                "it must be used instead of import_clips.",
                "import_clips always starts at frame 0 of the media, discarding "
                "the original source offset and handles.",
            ],
            "openclip_timecode": {
                "nbTicks": (
                    "Camera timecode as absolute frame count at project frame rate. "
                    "Flame uses this to reconcile the openclip startFrame (sequential, "
                    "e.g. 1) with the EXR's embedded timecode (e.g. 09:55:27:08). "
                    "If nbTicks=0 and the EXR has embedded TC, Flame ADDS the EXR "
                    "frame count to startFrame — nonsense value like 857457."
                ),
                "fix": (
                    "When injecting an alt grade into an existing openclip, read "
                    "nbTicks from the v00 feed XML and apply the same value to the "
                    "alt version (same camera roll = same TC base)."
                ),
            },
        },
        "openclip": {
            "title": "Openclip XML structure and version switching",
            "structure": {
                "feeds_currentVersion": "Controls which version loads by default",
                "versions_currentVersion": "Must match feeds_currentVersion",
                "feed_vuid": "e.g. v00, v01 — matches version uid",
                "version_n": "Display name shown in Flame's version switcher UI",
                "startFrame": "Sequential export frame number — always 1 from preset",
                "nbTicks": "Camera TC as absolute frame count — MUST match v00 when injecting alt",
                "colourSpace": (
                    "Reflects the SOURCE / INPUT colorspace of the media (e.g. ACEScg). "
                    "Do NOT overwrite with display/output space — Flame uses this "
                    "to know the media's native space."
                ),
            },
            "mismatched_xml_tag": (
                "Flame writes <name type=\"string\">VALUE</n> — mismatched open/close tags. "
                "Fix before parsing with ElementTree:\n"
                "  content = re.sub(r'(<name type=\"string\">[^<]*)</n>', r'\\1</n>', content)"
            ),
            "fmt_from_segment_gotcha": (
                "seg.get_colour_space() returns the INPUT media colorspace, not the "
                "export output colorspace. Use the segment's actual source CS — "
                "not the display/publish CS — when writing openclip colourSpace."
            ),
        },
        "crashes": {
            "title": "Known Flame 2026 crashes and unsafe operations",
            "crash_list": [
                {
                    "operation": "flame.delete(PySegment, confirm=False)",
                    "context": "Segment is in an active sequence",
                    "result": "Flame crashes immediately — no exception, hard crash",
                    "workaround": "Build sequence correctly from start. Never delete segments post-assembly.",
                },
                {
                    "operation": "flame.delete(PyTrack, confirm=False)",
                    "context": "Track is in an active sequence",
                    "result": "Flame crashes immediately",
                    "workaround": "Same — do not attempt track removal on active sequences.",
                },
            ],
            "safe_deletes": [
                "flame.delete(PyClip, confirm=False)  # scratch reel clips — safe",
                "flame.delete(PySequence, confirm=False)  # whole sequences — safe",
            ],
        },
        "cleanup": {
            "title": "Cleanup patterns after assembly",
            "patterns": [
                {
                    "what": "Scratch clips used for overwrite()",
                    "how": "flame.delete(clip, confirm=False) immediately after overwrite()",
                },
                {
                    "what": "_export_tmp_publish sequences",
                    "how": (
                        "Delete all EXCEPT the one renamed as the assembled base. "
                        "Use identity check (is), not name equality (==)."
                    ),
                },
            ],
            "assembled_base_pattern": (
                "# The first _export_tmp_publish seq is RENAMED as the published seq.\n"
                "# It remains in all_tmp_seqs — skip it by object identity, not name.\n"
                "for tmp in all_tmp_seqs:\n"
                "    if tmp is assembled:  # identity, not ==\n"
                "        continue\n"
                "    flame.delete(tmp, confirm=False)"
            ),
        },
    }

    topic = (params.topic or "full").lower()
    if topic == "full":
        return json.dumps(guide, indent=2)
    elif topic in guide:
        return json.dumps({topic: guide[topic]}, indent=2)
    else:
        return json.dumps({
            "error": f"Unknown topic '{topic}'",
            "available_topics": list(guide.keys()) + ["full"],
        }, indent=2)


# ── Tool: flame_inspect_sequence_versions ─────────────────────────────
#
# Editorial note (probed 2026-03-20, Flame 2026.2.1):
#   - seq.versions returns a list of PyVersion objects (index-only — no name attr)
#   - Each PyVersion has .tracks (list of PyTrack)
#   - PyVersion has NO name attribute — versions are referenced by index only
#   - create_version() creates a BLANK version (1 empty track, 1 gap segment)
#   - seq.tracks returns None — ALWAYS use seq.versions[N].tracks
#   - seg.record_in / record_out / source_in / source_out are PyTime objects
#     PyTime API: .timecode (str "01:00:00+00"), .frame (int), .frame_rate
#     NOT PyAttribute — get_value() does not exist on PyTime
#   - Empty segments (name == "") are gap fillers between clips
#     Skip them during reconstruction; Flame creates equivalent gaps automatically


class InspectVersionsInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")


async def inspect_sequence_versions(params: InspectVersionsInput) -> str:
    """Inspect all versions, tracks, and segments on a sequence.

    Returns the full editorial structure:
    - Number of versions (PyVersion objects, index-only — no name attribute)
    - For each version: all tracks with segment names, record positions,
      source timecodes, and whether each segment is a real clip or a gap

    This is the starting point before any version creation or track
    reconstruction work. Run this first to understand what exists.

    Key Flame facts:
    - Versions have NO name attribute — referenced by index only
    - seq.tracks returns None — always use seq.versions[N].tracks
    - Empty segment name ("") = gap/filler — not real media
    - seg.record_in/source_in are PyTime: use .timecode for string, .frame for int
    """
    data = await bridge.execute_json(f"""
import flame, json

def _find_seq(name):
    desk = flame.projects.current_project.current_workspace.desktop
    for rg in desk.reel_groups:
        for reel in rg.reels:
            for s in (reel.sequences or []):
                if s.name.get_value() == name:
                    return s
    return None

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{"error": "Sequence not found: " + {params.sequence_name!r}}}))
else:
    result = {{
        "sequence": {params.sequence_name!r},
        "frame_rate": str(seq.frame_rate),
        "duration": seq.duration.timecode,
        "num_versions": len(seq.versions),
        "versions": []
    }}
    for vi, ver in enumerate(seq.versions):
        v_info = {{"version_index": vi, "num_tracks": len(ver.tracks), "tracks": []}}
        for ti, track in enumerate(ver.tracks):
            segs = []
            for seg in track.segments:
                name = seg.name.get_value()
                segs.append({{
                    "name": name,
                    "is_gap": name == "",
                    "rec_in": seg.record_in.timecode,
                    "rec_out": seg.record_out.timecode,
                    "src_in": seg.source_in.timecode,
                    "src_out": seg.source_out.timecode,
                    "rec_in_frame": seg.record_in.frame,
                    "rec_out_frame": seg.record_out.frame,
                }})
            real_segs = sum(1 for s in segs if not s["is_gap"])
            v_info["tracks"].append({{
                "track_index": ti,
                "num_segments": len(segs),
                "real_segments": real_segs,
                "gap_segments": len(segs) - real_segs,
                "segments": segs
            }})
        result["versions"].append(v_info)
    print(json.dumps(result, indent=2))
""")
    return json.dumps(data, indent=2)


# ── Tool: flame_create_version ────────────────────────────────────────


class CreateVersionInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")


async def create_version(params: CreateVersionInput) -> str:
    """Create a new blank version on a sequence.

    Returns the index of the newly created version and its initial state.

    Important facts about what you get:
    - A blank PyVersion with NO name (versions have no name attribute in Flame)
    - 1 empty track with 1 gap segment spanning the full sequence duration
    - Content from existing versions is NOT copied — the new version is empty
    - Version is referenced by its index (len(seq.versions) - 1 after creation)

    To populate the new version with content from an existing version,
    use flame_reconstruct_track or flame_clone_version.

    Runs on Flame's main thread.
    """
    data = await bridge.execute_json(f"""
import flame, json, threading

def _find_seq(name):
    desk = flame.projects.current_project.current_workspace.desktop
    for rg in desk.reel_groups:
        for reel in rg.reels:
            for s in (reel.sequences or []):
                if s.name.get_value() == name:
                    return s
    return None

seq = _find_seq({params.sequence_name!r})
if not seq:
    print(json.dumps({{"error": "Sequence not found: " + {params.sequence_name!r}}}))
else:
    result = {{}}
    event = threading.Event()

    def _do():
        try:
            before_count = len(seq.versions)
            new_ver = seq.create_version()
            new_idx = len(seq.versions) - 1
            t0 = new_ver.tracks[0]
            result.update({{
                "ok": True,
                "new_version_index": new_idx,
                "versions_before": before_count,
                "versions_after": len(seq.versions),
                "initial_tracks": len(new_ver.tracks),
                "initial_segments": len(t0.segments),
                "note": "Version is blank — use flame_reconstruct_track to populate"
            }})
        except Exception as e:
            result["error"] = str(e)
        event.set()

    flame.schedule_idle_event(_do)
    event.wait(timeout=10)
    print(json.dumps(result))
""", main_thread=True)
    return json.dumps(data, indent=2)


# ── Tool: flame_reconstruct_track ─────────────────────────────────────


class ReconstructTrackInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")
    source_version_index: int = Field(..., description="Version index to copy from (0-based)")
    source_track_index: int = Field(..., description="Track index within source version (0-based)")
    target_version_index: int = Field(..., description="Version index to copy into (0-based)")
    target_track_index: int = Field(
        0,
        description="Track index within target version (0-based). Default 0."
    )
    scratch_reel_name: str = Field(
        "Reel A",
        description="Name of a reel to use as scratch space for copy_to_media_panel. "
                    "Clips placed here are deleted after reconstruction."
    )


async def reconstruct_track(params: ReconstructTrackInput) -> str:
    """Copy all segments from one version's track onto another version's track.

    This is the core stream publishing primitive — proven to produce
    bit-for-bit identical timing and source references.

    Method (the only correct approach):
      1. For each real (non-gap) segment on the source track:
         a. seg.copy_to_media_panel(scratch_reel) → PyClip
            Preserves source_in/source_out exactly (verified in production)
         b. seq.overwrite(clip, seg.record_in, target_track)
            Places clip at same record position on target track
         c. flame.delete(clip) — clean up scratch reel immediately
      2. Gap segments are skipped — Flame fills gaps automatically

    Key constraints proven in production:
    - seq.overwrite() requires PyTime for position — NOT int, NOT str
      seg.record_in is already PyTime — pass it directly
    - source_in is READ-ONLY after placement — carried through copy_to_media_panel
    - import_clips() LOSES source_in — do NOT use for reconstruction
    - Reconstruction fidelity: 100% on 8-segment test (name, rec_in, rec_out,
      src_in, src_out all match after reconstruction)

    Runs on Flame's main thread.
    """
    data = await bridge.execute_json(f"""
import flame, json, threading

def _find_seq(name):
    desk = flame.projects.current_project.current_workspace.desktop
    for rg in desk.reel_groups:
        for reel in rg.reels:
            for s in (reel.sequences or []):
                if s.name.get_value() == name:
                    return s, reel
    return None, None

def _find_reel(name):
    desk = flame.projects.current_project.current_workspace.desktop
    for rg in desk.reel_groups:
        for reel in rg.reels:
            if reel.name.get_value() == name:
                return reel
    return None

seq, _ = _find_seq({params.sequence_name!r})
scratch_reel = _find_reel({params.scratch_reel_name!r})

if not seq:
    print(json.dumps({{"error": "Sequence not found: " + {params.sequence_name!r}}}))
elif not scratch_reel:
    print(json.dumps({{"error": "Scratch reel not found: " + {params.scratch_reel_name!r}}}))
else:
    result = {{"placed": [], "skipped": [], "errors": []}}
    event = threading.Event()

    def _do():
        try:
            src_ver = seq.versions[{params.source_version_index}]
            src_track = src_ver.tracks[{params.source_track_index}]
            tgt_ver = seq.versions[{params.target_version_index}]
            tgt_track = tgt_ver.tracks[{params.target_track_index}]

            scratch_clips = []
            for seg in src_track.segments:
                name = seg.name.get_value()
                if not name:
                    result["skipped"].append({{"rec_in": seg.record_in.timecode, "reason": "gap"}})
                    continue
                try:
                    clip = seg.copy_to_media_panel(scratch_reel)
                    scratch_clips.append(clip)
                    seq.overwrite(clip, seg.record_in, tgt_track)
                    result["placed"].append({{
                        "name": name,
                        "rec_in": seg.record_in.timecode,
                        "rec_out": seg.record_out.timecode,
                        "src_in": seg.source_in.timecode,
                    }})
                except Exception as e:
                    result["errors"].append({{"name": name, "error": str(e)}})

            # Verify fidelity
            mismatches = []
            tgt_segs = [s for s in tgt_track.segments if s.name.get_value()]
            src_segs = [s for s in src_track.segments if s.name.get_value()]
            for s0, s1 in zip(src_segs, tgt_segs):
                if (s0.record_in.timecode != s1.record_in.timecode or
                    s0.source_in.timecode != s1.source_in.timecode):
                    mismatches.append(s0.name.get_value())
            result["fidelity_mismatches"] = mismatches
            result["fidelity_ok"] = len(mismatches) == 0

            # Clean up scratch clips
            for clip in scratch_clips:
                try:
                    flame.delete(clip, confirm=False)
                except Exception:
                    pass

            result["segments_placed"] = len(result["placed"])
            result["segments_skipped"] = len(result["skipped"])

        except Exception as e:
            result["error"] = str(e)
        event.set()

    flame.schedule_idle_event(_do)
    event.wait(timeout=60)
    print(json.dumps(result))
""", main_thread=True)
    return json.dumps(data, indent=2)


# ── Tool: flame_clone_version ─────────────────────────────────────────


class CloneVersionInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")
    source_version_index: int = Field(
        0,
        description="Version index to clone from. Default 0 (first version)."
    )
    scratch_reel_name: str = Field(
        "Reel A",
        description="Reel to use as scratch space during reconstruction."
    )


async def clone_version(params: CloneVersionInput) -> str:
    """Create a new version on a sequence and reconstruct all tracks from a source version.

    This is the stream fork operation — creates an independent copy of an
    existing version that can be worked on without affecting the source.

    Internally calls create_version() then reconstruct_track() for every
    track in the source version. Additional tracks beyond the default are
    created on the new version via create_track() before reconstruction.

    The new version is appended at the end of seq.versions. It has no
    name (Flame's PyVersion has no name attribute).

    Returns:
    - new_version_index: index of the created version
    - tracks_cloned: number of tracks reconstructed
    - per-track placed/skipped/fidelity summary

    Runs on Flame's main thread.
    """
    data = await bridge.execute_json(f"""
import flame, json, threading

def _find_seq(name):
    desk = flame.projects.current_project.current_workspace.desktop
    for rg in desk.reel_groups:
        for reel in rg.reels:
            for s in (reel.sequences or []):
                if s.name.get_value() == name:
                    return s
    return None

def _find_reel(name):
    desk = flame.projects.current_project.current_workspace.desktop
    for rg in desk.reel_groups:
        for reel in rg.reels:
            if reel.name.get_value() == name:
                return reel
    return None

seq = _find_seq({params.sequence_name!r})
scratch_reel = _find_reel({params.scratch_reel_name!r})

if not seq:
    print(json.dumps({{"error": "Sequence not found: " + {params.sequence_name!r}}}))
elif not scratch_reel:
    print(json.dumps({{"error": "Scratch reel not found: " + {params.scratch_reel_name!r}}}))
else:
    result = {{"tracks": [], "errors": []}}
    event = threading.Event()

    def _do():
        try:
            src_ver = seq.versions[{params.source_version_index}]
            src_tracks = src_ver.tracks

            # Create blank version — comes with 1 track
            new_ver = seq.create_version()
            new_idx = len(seq.versions) - 1
            result["new_version_index"] = new_idx

            # Create additional tracks if source has more than 1
            while len(new_ver.tracks) < len(src_tracks):
                new_ver.create_track()

            # Reconstruct each track
            scratch_clips_all = []
            for ti, src_track in enumerate(src_tracks):
                tgt_track = new_ver.tracks[ti]
                placed = []
                skipped = []
                t_errors = []
                scratch_clips = []

                for seg in src_track.segments:
                    name = seg.name.get_value()
                    if not name:
                        skipped.append(seg.record_in.timecode)
                        continue
                    try:
                        clip = seg.copy_to_media_panel(scratch_reel)
                        scratch_clips.append(clip)
                        scratch_clips_all.append(clip)
                        seq.overwrite(clip, seg.record_in, tgt_track)
                        placed.append({{
                            "name": name,
                            "rec_in": seg.record_in.timecode,
                            "src_in": seg.source_in.timecode,
                        }})
                    except Exception as e:
                        t_errors.append({{"name": name, "error": str(e)}})

                # Fidelity check
                tgt_segs = [s for s in tgt_track.segments if s.name.get_value()]
                src_segs = [s for s in src_track.segments if s.name.get_value()]
                mismatches = []
                for s0, s1 in zip(src_segs, tgt_segs):
                    if (s0.record_in.timecode != s1.record_in.timecode or
                        s0.source_in.timecode != s1.source_in.timecode):
                        mismatches.append(s0.name.get_value())

                result["tracks"].append({{
                    "track_index": ti,
                    "segments_placed": len(placed),
                    "segments_skipped": len(skipped),
                    "fidelity_ok": len(mismatches) == 0,
                    "mismatches": mismatches,
                    "errors": t_errors,
                }})

            # Clean up all scratch clips
            for clip in scratch_clips_all:
                try:
                    flame.delete(clip, confirm=False)
                except Exception:
                    pass

            result["tracks_cloned"] = len(src_tracks)
            result["source_version_index"] = {params.source_version_index}

        except Exception as e:
            result["error"] = str(e)
        event.set()

    flame.schedule_idle_event(_do)
    event.wait(timeout=120)
    print(json.dumps(result))
""", main_thread=True)
    return json.dumps(data, indent=2)


# ── Tool: flame_disconnect_segments ──────────────────────────────────


class DisconnectSegmentsInput(BaseModel):
    """Input for disconnecting segments."""

    reel_name: str = Field(
        ...,
        description="Name of the reel containing sequences (e.g. 'Sequences').",
    )
    sequence_name: Optional[str] = Field(
        default=None,
        description="If provided, only disconnect segments in this sequence. "
        "If omitted, disconnect all segments in every sequence in the reel.",
    )


async def disconnect_segments(params: DisconnectSegmentsInput) -> str:
    """Remove all segment connections from sequences in a reel.

    Calls seg.remove_connection() unconditionally on every non-gap segment.
    The connected_segments() API does not reliably report connections, so
    we cannot gate on it — just call remove_connection() on everything.

    Iterates all versions (not just versions[0]) to catch segments added
    by PyExporter or other workflows.

    Reopen the sequence in Flame after running to refresh the UI.

    Runs on Flame's main thread. Returns count of processed segments
    per sequence.
    """
    seq_filter = params.sequence_name
    data = await bridge.execute_json(f"""
import flame, json, threading

event = threading.Event()
result = {{"sequences": [], "total_processed": 0, "errors": []}}

def _do():
    try:
        desk = flame.projects.current_project.current_workspace.desktop
        for rg in desk.reel_groups:
            for reel in rg.reels:
                if reel.name.get_value() != {params.reel_name!r}:
                    continue
                for seq in reel.sequences:
                    seq_name = seq.name.get_value()
                    seq_filter = {seq_filter!r}
                    if seq_filter and seq_name != seq_filter:
                        continue
                    count = 0
                    for ver in seq.versions:
                        for t in ver.tracks:
                            for seg in t.segments:
                                src = str(seg.source_name) if seg.source_name else ""
                                if not src:
                                    continue
                                try:
                                    seg.remove_connection()
                                    count += 1
                                except Exception as e:
                                    result["errors"].append(
                                        str(seg.name.get_value()) + ": " + str(e)
                                    )
                    result["sequences"].append(
                        {{"name": seq_name, "processed": count}}
                    )
                    result["total_processed"] += count
    except Exception as e:
        result["errors"].append(str(e))
    event.set()

flame.schedule_idle_event(_do)
event.wait(timeout=30)
print(json.dumps(result))
""", main_thread=True)
    return json.dumps(data, indent=2)


# ── Tool: flame_replace_segment_media ─────────────────────────────────


class ReplaceSegmentMediaInput(BaseModel):
    sequence_name: str = Field(..., description="Exact sequence name")
    segment_name: str = Field(..., description="Name of the segment to relink")
    new_media_path: str = Field(
        ...,
        description="Absolute path to the replacement media file or frame sequence",
    )


async def replace_segment_media(params: ReplaceSegmentMediaInput) -> str:
    """Replace a segment's source media via smart_replace_media.

    Imports the new media as a temporary clip, calls
    smart_replace_media on the target segment, then cleans up.
    The segment keeps its name, position, and editorial timing —
    only the underlying source file changes.

    Use this to relink media to a new location (e.g. moving a clip
    from prep/ to footage/stock/ so role detection works correctly).
    """
    data = await bridge.execute_json(f"""
import flame, json, os

seq_name = {params.sequence_name!r}
seg_name = {params.segment_name!r}
new_path = {params.new_media_path!r}

if not os.path.exists(new_path):
    print(json.dumps({{"error": f"File not found: {{new_path}}"}}))
else:
    desk = flame.projects.current_project.current_workspace.desktop
    seq = None
    for rg in desk.reel_groups:
        for reel in rg.reels:
            for s in (reel.sequences or []):
                if str(s.name).strip("'") == seq_name:
                    seq = s
                    break
            if seq: break
        if seq: break

    if not seq:
        print(json.dumps({{"error": f"Sequence not found: {{seq_name}}"}}))
    else:
        target_seg = None
        for ver in seq.versions:
            for track in ver.tracks:
                for seg in track.segments:
                    if str(seg.name).strip("'") == seg_name:
                        target_seg = seg
                        break
                if target_seg: break
            if target_seg: break

        if not target_seg:
            print(json.dumps({{"error": f"Segment not found: {{seg_name}}"}}))
        else:
            old_fp = str(target_seg.file_path).strip("'") if target_seg.file_path else ''
            rg0 = desk.reel_groups[0]
            scratch = rg0.reels[-1]
            imported = flame.import_clips(new_path, scratch)
            clip = scratch.clips[-1]
            target_seg.smart_replace_media(clip)
            new_fp = str(target_seg.file_path).strip("'") if target_seg.file_path else ''
            try:
                flame.delete(clip, confirm=False)
            except Exception:
                pass
            print(json.dumps({{
                "segment": seg_name,
                "old_path": old_fp,
                "new_path": new_fp,
                "success": new_fp != old_fp,
            }}))
""", main_thread=True)
    return json.dumps(data, indent=2)


# ── Tool: flame_scan_roles ────────────────────────────────────────────


class ScanRolesInput(BaseModel):
    """Scan segments for their detected/tagged roles."""
    sequence_names: list[str] = Field(
        ..., description="Sequence names to scan. Scans all tracks of the last version.",
    )
    reel_group: str = Field(
        default="", description="Reel group name. Empty = search all reel groups.",
    )
    reel_name: str = Field(
        default="", description="Reel name. Empty = search all reels.",
    )


async def scan_roles(params: ScanRolesInput) -> str:
    """Scan segments and report their current role assignments.

    For each non-gap segment, reports:
    - tagged_role: existing forge:{role} tag (highest priority)
    - detected_role: auto-detected from file path, source name, segment name
    - effective_role: tagged_role if present, else detected_role

    Use this to audit role assignments before publish, or to identify
    segments with "unknown" roles that need manual assignment.
    """
    data = await bridge.execute_json(f"""
import flame, json, re

FOOTAGE_ROLES = ['graded', 'raw', 'denoised', 'flat', 'external', 'scans', 'stock', 'source']
NON_FOOTAGE_ROLES = ['graphics', 'reference', 'comp']
ALL_KNOWN = set(FOOTAGE_ROLES + NON_FOOTAGE_ROLES)
_GRAPHICS_KW = ('legal', 'super', 'title', 'logo', 'endcard', 'end_card',
                'slate', 'card', 'bug', 'watermark', 'bumper', 'graphic')
_REF_KW = ('offline', 'ref', 'proxy')

def _detect_role(fp, src, sn):
    fp = (fp or '').lower()
    src = (src or '').lower()
    sn = (sn or '').lower()
    m = re.match(r'^[a-z0-9]+_\\d+_([a-z][a-z0-9]*)_', sn)
    if m and m.group(1) in ALL_KNOWN:
        return m.group(1)
    if fp:
        m2 = re.search(r'footage/([^/]+)/', fp)
        if m2 and m2.group(1) in set(FOOTAGE_ROLES):
            return m2.group(1)
    if any(kw in fp for kw in ('/render/', '/comp/', '/output/', '/cg/')):
        return 'comp'
    combined = fp + ' ' + src + ' ' + sn
    if any(kw in combined for kw in _GRAPHICS_KW):
        return 'graphics'
    if any(kw in combined for kw in _REF_KW):
        return 'reference'
    if fp.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.psd')):
        return 'graphics'
    if fp.endswith(('.mov', '.mp4', '.mxf')):
        return 'stock'
    if 'footage/' in fp:
        return 'source'
    return 'unknown'

def _get_forge_tag(tags):
    for t in (tags or []):
        if t.startswith('forge:'):
            role = t[len('forge:'):]
            if role in ALL_KNOWN:
                return role
    return None

desk = flame.projects.current_project.current_workspace.desktop
seq_names = {params.sequence_names!r}
rg_filter = {params.reel_group!r}
reel_filter = {params.reel_name!r}

sequences = []
for rg in desk.reel_groups:
    if rg_filter and rg.name.get_value() != rg_filter:
        continue
    for reel in rg.reels:
        if reel_filter and reel.name.get_value() != reel_filter:
            continue
        for seq in (reel.sequences or []):
            if seq.name.get_value() in seq_names:
                sequences.append(seq)

entries = []
for seq in sequences:
    sname = seq.name.get_value()
    ver = seq.versions[-1]
    for ti, track in enumerate(ver.tracks):
        for seg in (track.segments or []):
            seg_name = seg.name.get_value() if seg.name else ''
            if not seg_name:
                continue
            fp = ''
            try:
                fp = str(seg.file_path).strip("'\\"") if seg.file_path else ''
            except Exception:
                pass
            src = ''
            try:
                src = str(seg.source_name).strip("'\\"") if seg.source_name else ''
            except Exception:
                pass
            tags = []
            try:
                tags = seg.tags.get_value() or []
            except Exception:
                pass
            tagged = _get_forge_tag(tags)
            detected = _detect_role(fp, src, seg_name)
            entries.append({{
                'sequence': sname,
                'segment': seg_name,
                'track': ti,
                'tagged_role': tagged,
                'detected_role': detected,
                'effective_role': tagged or detected,
                'source_name': src,
                'file_path': fp[-80:] if len(fp) > 80 else fp,
            }})

unknown_count = sum(1 for e in entries if e['effective_role'] == 'unknown')
tagged_count = sum(1 for e in entries if e['tagged_role'])
print(json.dumps({{
    'total_segments': len(entries),
    'unknown_count': unknown_count,
    'tagged_count': tagged_count,
    'segments': entries,
}}))
""")
    return json.dumps(data, indent=2)


# ── Tool: flame_assign_roles ─────────────────────────────────────────


class AssignRolesInput(BaseModel):
    """Assign forge role tags to segments."""
    sequence_names: list[str] = Field(
        ..., description="Sequence names containing the target segments.",
    )
    assignments: dict[str, str] = Field(
        ..., description="Map of segment_name → role to assign. "
        "Valid roles: graded, raw, denoised, flat, external, scans, stock, "
        "source, graphics, reference, comp.",
    )
    reel_group: str = Field(
        default="", description="Reel group name. Empty = search all.",
    )
    reel_name: str = Field(
        default="", description="Reel name. Empty = search all.",
    )


async def assign_roles(params: AssignRolesInput) -> str:
    """Assign forge:{role} tags to segments by name.

    Writes persistent forge:role tags that the publish pipeline and
    role detection system use as highest-priority role source.
    Replaces any existing forge:role tag on the segment.

    Typical workflow:
    1. flame_scan_roles → identify segments with "unknown" roles
    2. flame_assign_roles → assign correct roles
    3. Re-run publish or reconform with correct role detection
    """
    data = await bridge.execute_json(f"""
import flame, json

FOOTAGE_ROLES = ['graded', 'raw', 'denoised', 'flat', 'external', 'scans', 'stock', 'source']
NON_FOOTAGE_ROLES = ['graphics', 'reference', 'comp']
ALL_KNOWN = set(FOOTAGE_ROLES + NON_FOOTAGE_ROLES)
ROLE_TAGS = tuple('forge:' + r for r in ALL_KNOWN)

desk = flame.projects.current_project.current_workspace.desktop
seq_names = {params.sequence_names!r}
assignments = {params.assignments!r}
rg_filter = {params.reel_group!r}
reel_filter = {params.reel_name!r}

# Validate roles
invalid = [r for r in assignments.values() if r not in ALL_KNOWN]
if invalid:
    print(json.dumps({{'error': 'Invalid roles: ' + ', '.join(set(invalid))}}))
else:
    sequences = []
    for rg in desk.reel_groups:
        if rg_filter and rg.name.get_value() != rg_filter:
            continue
        for reel in rg.reels:
            if reel_filter and reel.name.get_value() != reel_filter:
                continue
            for seq in (reel.sequences or []):
                if seq.name.get_value() in seq_names:
                    sequences.append(seq)

    applied = []
    not_found = []
    errors = []

    for seg_name, role in assignments.items():
        found = False
        for seq in sequences:
            ver = seq.versions[-1]
            for track in ver.tracks:
                for seg in (track.segments or []):
                    if seg.name.get_value() == seg_name:
                        found = True
                        try:
                            existing = seg.tags.get_value() or []
                            filtered = [t for t in existing if t not in ROLE_TAGS]
                            filtered.append('forge:' + role)
                            seg.tags.set_value(filtered)
                            applied.append({{'segment': seg_name, 'role': role}})
                        except Exception as e:
                            errors.append({{'segment': seg_name, 'error': str(e)}})
                        break
                if found:
                    break
            if found:
                break
        if not found:
            not_found.append(seg_name)

    print(json.dumps({{
        'applied': len(applied),
        'not_found': not_found,
        'errors': errors,
        'details': applied,
    }}))
""", main_thread=True)
    return json.dumps(data, indent=2)
