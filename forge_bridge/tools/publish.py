"""
Publish workflow tools — shot rename, segment rename, sequence publish.

Post-conform workflow:
1. rename_shots → assign shot names on background track, propagate up
2. rename_segments → apply segment naming template across all tracks
3. publish_sequence → export via PyExporter with preset
"""

from pydantic import BaseModel, Field
from typing import Optional

from forge_bridge import bridge


# ── Input Models ────────────────────────────────────────────────────────


class RenameShots(BaseModel):
    """Assign shot names to a sequence's segments."""
    sequence_name: str = Field(
        ..., description="Name of the sequence to rename shots in.",
    )
    prefix: str = Field(
        default="ABC", description="Shot name prefix, e.g. 'noise', 'spk', 'gen'. "
        "Defaults to 'ABC' as a placeholder — operator should set this.",
    )
    increment: int = Field(
        default=10, description="Shot number increment (default 10).",
    )
    padding: int = Field(
        default=3, description="Digit padding for shot number (default 3). "
        "A trailing zero is appended, so padding=3 → '010', '020', etc.",
    )
    start: int = Field(
        default=1, description="Starting shot number before multiplication "
        "by increment (default 1 → first shot is 010).",
    )


class RenameSegments(BaseModel):
    """Rename all segments in a sequence using naming template."""
    sequence_name: str = Field(
        ..., description="Name of the sequence.",
    )
    role_name: Optional[str] = Field(
        default=None, description="Override footage role for all segments. "
        "If not set, auto-detects from source media path by extracting "
        "the footage subdirectory (e.g. footage/graded → 'graded', "
        "footage/raw → 'raw'). Known roles: graded, raw, denoised, "
        "flat, external, scans, stock. Falls back to 'graded' if undetectable.",
    )


class PublishSequence(BaseModel):
    """Publish a sequence using an export preset."""
    sequence_name: str = Field(
        ..., description="Name of the sequence to publish.",
    )
    preset_path: str = Field(
        default="/opt/Autodesk/shared/export/presets/sequence_publish/"
        "FlameNIM_style_16bit_EXR_Sequence_Publish.xml",
        description="Absolute path to the export preset XML.",
    )
    output_directory: str = Field(
        default="/mnt/portofino",
        description="Root output directory. Preset namePattern adds subdirs.",
    )
    foreground: bool = Field(
        default=True,
        description="True for blocking export, False for background job.",
    )


# ── Tool Implementations ───────────────────────────────────────────────


async def rename_shots(params: RenameShots) -> str:
    """Assign shot names on background track and propagate to upper tracks."""

    code = f'''
import flame, json, threading

seq_name = {repr(params.sequence_name)}
prefix = {repr(params.prefix)}
increment = {params.increment}
padding = {params.padding}
start = {params.start}

found = flame.find_by_name(seq_name)
seqs = [x for x in found if type(x).__name__ == 'PySequence']
if not seqs:
    print(json.dumps({{"error": f"Sequence '{{seq_name}}' not found"}}))
else:
    seq = seqs[0]

    # Collect all tracks
    all_tracks = []
    for ver in seq.versions:
        for track in ver.tracks:
            all_tracks.append(track)

    if not all_tracks:
        print(json.dumps({{"error": "No tracks found"}}))
    else:
        event = threading.Event()
        result = {{"shots_assigned": 0, "propagated": 0, "changes": []}}

        def _do():
            # Step 1: Assign shot names on track 0 (background)
            bg_track = all_tracks[0]
            bg_segments = []
            shot_num = start
            for seg in bg_track.segments:
                src = seg.source_name
                if not src:
                    bg_segments.append((seg, None, None, None))
                    continue
                num_str = str(shot_num * increment).zfill(padding)
                shot_name = f"{{prefix}}_{{num_str}}"
                old_shot = seg.shot_name.get_value() if hasattr(seg.shot_name, 'get_value') else ''
                seg.shot_name.set_value(shot_name)
                bg_segments.append((seg, shot_name, str(seg.record_in), str(seg.record_out)))
                result["shots_assigned"] += 1
                result["changes"].append({{"track": 0, "old_shot": old_shot, "new_shot": shot_name}})
                shot_num += 1

            # Step 2: Propagate to upper tracks by timecode overlap
            for ti in range(1, len(all_tracks)):
                track = all_tracks[ti]
                for seg in track.segments:
                    if not seg.source_name:
                        continue
                    seg_in = str(seg.record_in)
                    # Find overlapping bg segment
                    for bg_seg, bg_shot, bg_in, bg_out in bg_segments:
                        if bg_shot and seg_in >= bg_in and seg_in <= bg_out:
                            old_shot = seg.shot_name.get_value() if hasattr(seg.shot_name, 'get_value') else ''
                            seg.shot_name.set_value(bg_shot)
                            result["propagated"] += 1
                            result["changes"].append({{"track": ti, "old_shot": old_shot, "new_shot": bg_shot}})
                            break

            event.set()

        flame.schedule_idle_event(_do)
        event.wait(timeout=30)
        print(json.dumps(result))
'''
    return await bridge.execute_and_read(code)


async def rename_segments(params: RenameSegments) -> str:
    # Verified identical to projekt-forge 2026-04-14
    # Parity status: implementations are functionally identical.
    # Both use bridge.execute_and_read(), threading.Event, same role-detection logic,
    # same fallback role ('graded'), same track iteration pattern (all versions).
    # Import path note: standalone tools use 'from forge_mcp import bridge' or
    # 'from forge_bridge import bridge' depending on package resolution — both resolve
    # to the same bridge.py HTTP client in this repo.
    """Rename all segments using shot_name + role + layer template."""

    # Role override as string 'None' for the bridge code to handle
    role_override = repr(params.role_name) if params.role_name else 'None'

    code = f'''
import flame, json, threading, re

seq_name = {repr(params.sequence_name)}
role_override = {role_override}

# Known footage roles from pipeline config
KNOWN_ROLES = {{"graded", "raw", "denoised", "flat", "external", "scans", "stock"}}

def detect_role(file_path):
    """Extract role from source media path via footage subdirectory."""
    if not file_path:
        return None
    m = re.search(r'footage/([^/]+)/', str(file_path))
    if m and m.group(1) in KNOWN_ROLES:
        return m.group(1)
    return None

found = flame.find_by_name(seq_name)
seqs = [x for x in found if type(x).__name__ == 'PySequence']
if not seqs:
    print(json.dumps({{"error": f"Sequence '{{seq_name}}' not found"}}))
else:
    seq = seqs[0]

    all_tracks = []
    for ver in seq.versions:
        for track in ver.tracks:
            all_tracks.append(track)

    event = threading.Event()
    result = {{"renamed": 0, "skipped": 0, "undetected": 0, "changes": []}}

    def _do():
        for ti, track in enumerate(all_tracks):
            layer_num = str(ti + 1).zfill(2)
            for seg in track.segments:
                if not seg.source_name:
                    result["skipped"] += 1
                    continue
                shot_name = seg.shot_name.get_value() if hasattr(seg.shot_name, 'get_value') else ''
                if not shot_name:
                    result["skipped"] += 1
                    continue

                # Determine role
                if role_override:
                    seg_role = role_override
                else:
                    fp = ''
                    try:
                        fp = str(seg.file_path) if seg.file_path else ''
                    except:
                        pass
                    seg_role = detect_role(fp)
                    if not seg_role:
                        seg_role = 'graded'
                        result["undetected"] += 1

                old_name = seg.name.get_value() if hasattr(seg.name, 'get_value') else ''
                new_name = f"{{shot_name}}_{{seg_role}}_L{{layer_num}}"
                seg.name.set_value(new_name)
                result["renamed"] += 1
                result["changes"].append({{"track": ti, "old": old_name, "new": new_name, "role": seg_role}})

        event.set()

    flame.schedule_idle_event(_do)
    event.wait(timeout=30)
    print(json.dumps(result))
'''
    return await bridge.execute_and_read(code)


async def publish_sequence(params: PublishSequence) -> str:
    """Export sequence using PyExporter with the specified preset."""

    code = f'''
import flame, json, threading

seq_name = {repr(params.sequence_name)}
preset_path = {repr(params.preset_path)}
output_dir = {repr(params.output_directory)}
foreground = {params.foreground}

found = flame.find_by_name(seq_name)
seqs = [x for x in found if type(x).__name__ == 'PySequence']
if not seqs:
    print(json.dumps({{"error": f"Sequence '{{seq_name}}' not found"}}))
else:
    seq = seqs[0]

    import os
    if not os.path.exists(preset_path):
        print(json.dumps({{"error": f"Preset not found: {{preset_path}}"}}))
    else:
        event = threading.Event()
        result = {{}}

        def _do():
            try:
                e = flame.PyExporter()
                e.foreground = foreground
                e.export(seq, preset_path, output_dir)
                result["ok"] = True
                result["sequence"] = seq_name
                result["preset"] = preset_path
                result["output_directory"] = output_dir
                result["foreground"] = foreground
            except Exception as ex:
                result["error"] = str(ex)
            event.set()

        flame.schedule_idle_event(_do)
        event.wait(timeout=300)
        print(json.dumps(result))
'''
    return await bridge.execute_and_read(code)


# ── Assemble Published Sequence ─────────────────────────────────────────


class AssemblePublishedSequence(BaseModel):
    """Assemble a *_published sequence from per-shot _export_tmp_publish sequences.

    After plate exports complete, this tool rebuilds the published sequence so
    that V1.1 references source openclips (with multi-version alt grade support)
    and V2.1 references batch outputs.

    Strategy:
    - The first shot's _export_tmp_publish seq is renamed to <base>_published
      and becomes the assembled base (clean — no alt tracks).
    - Remaining shots are assembled via copy_to_media_panel + overwrite() at
      their original timeline record_in positions.
    - All other _export_tmp_publish seqs are deleted.

    Key API constraints discovered in production (Flame 2026):
    - flame.delete(PySegment/PyTrack) on active sequences CRASHES Flame.
    - seg.source_in is read-only — can't be set after placement.
    - copy_to_media_panel preserves source_in/handles; import_clips does not.
    - copy_to_media_panel reports 1 version via Python API but the underlying
      openclip multi-version structure (alt grades) is preserved on disk and
      accessible via Flame's version switcher UI.
    """
    source_sequence_name: str = Field(
        ..., description="Name of the source sequence (pre-publish, e.g. 'test long').",
    )
    published_sequence_name: str = Field(
        ..., description="Name of the target published sequence (e.g. 'test long_published').",
    )
    reel_name: Optional[str] = Field(
        default=None, description="Reel to search in. If omitted, searches all reels.",
    )


async def assemble_published_sequence(params: AssemblePublishedSequence) -> str:
    """Assemble the published sequence from _export_tmp_publish sequences."""
    src_name = params.source_sequence_name
    pub_name = params.published_sequence_name
    reel_filter = params.reel_name

    code = f'''
import flame, json

src_name    = {src_name!r}
pub_name    = {pub_name!r}
reel_filter = {reel_filter!r}

def _find_seqs():
    """Return (source_seq, all_tmp_seqs, scratch_reel)."""
    source_seq   = None
    tmp_seqs     = []
    scratch_reel = None
    suffix       = "_export_tmp_publish"
    for rg in flame.project.current_project.current_workspace.desktop.reel_groups:
        for reel in rg.reels:
            if reel_filter and str(reel.name).strip("'") != reel_filter:
                continue
            scratch_reel = reel
            for item in list(reel.sequences):
                n = str(item.name).strip("'")
                if n == src_name:
                    source_seq = item
                elif n.endswith(suffix):
                    tmp_seqs.append(item)
    return source_seq, tmp_seqs, scratch_reel

source_seq, tmp_seqs, scratch_reel = _find_seqs()

if source_seq is None:
    print(json.dumps({{"error": f"Source sequence '{{src_name}}' not found"}}))
elif not tmp_seqs:
    print(json.dumps({{"error": "No _export_tmp_publish sequences found — run plate export first"}}))
elif scratch_reel is None:
    print(json.dumps({{"error": "No reel found"}}))
else:
    # Collect shot timings from the source sequence (track-0, V1)
    import re
    shot_timings = []
    seen = set()
    try:
        for seg in source_seq.versions[0].tracks[0].segments:
            sn = str(seg.name).strip("'")
            if not sn:
                continue
            m = re.match(r'^([A-Za-z]+_\\d+)_', sn)
            if not m:
                continue
            shot = m.group(1)
            if shot in seen:
                continue
            seen.add(shot)
            shot_timings.append({{
                "shot_name":  shot,
                "seg_name":   sn,
                "record_in":  seg.record_in,
                "record_out": seg.record_out,
            }})
    except Exception as e:
        print(json.dumps({{"error": f"Failed to collect shot timings: {{e}}"}}))
        raise SystemExit

    # Build map: shot_name → publish seq
    publish_seqs = {{}}
    for tmp in tmp_seqs:
        n = str(tmp.name).strip("'")
        # n is e.g. "SHOT_020_graded_L01_export_tmp_publish"
        m = re.match(r'^([A-Za-z]+_\\d+)_', n)
        if m:
            publish_seqs[m.group(1)] = tmp

    ordered = [t for t in shot_timings if t["shot_name"] in publish_seqs]
    if not ordered:
        print(json.dumps({{"error": "No shot_timings matched any publish seq"}}))
        raise SystemExit

    # Use first shot's publish seq as assembled base (rename it)
    first_shot = ordered[0]["shot_name"]
    assembled  = publish_seqs.pop(first_shot)
    assembled.name = pub_name
    placed = 1

    errors = []

    # Assemble remaining shots
    for info in ordered[1:]:
        shot   = info["shot_name"]
        tmp_s  = publish_seqs.get(shot)
        if tmp_s is None:
            errors.append(f"No publish seq for {{shot}}")
            continue
        try:
            for vi, ver in enumerate(tmp_s.versions):
                for ti, tr in enumerate(ver.tracks):
                    for seg in tr.segments:
                        sn = str(seg.name).strip("'")
                        if not sn:
                            continue
                        clip = seg.copy_to_media_panel(scratch_reel)
                        try:
                            ok = assembled.overwrite(clip, info["record_in"], vi * 10 + ti)
                            if not ok:
                                errors.append(f"overwrite returned False: {{sn}}")
                        finally:
                            flame.delete(clip, confirm=False)
            placed += 1
        except Exception as e:
            errors.append(f"{{shot}}: {{e}}")

    # Delete tmp seqs (skip assembled base)
    deleted = 0
    for tmp in tmp_seqs:
        if tmp is assembled:
            continue
        try:
            flame.delete(tmp, confirm=False)
            deleted += 1
        except Exception as e:
            errors.append(f"cleanup: {{e}}")

    print(json.dumps({{
        "ok":      len(errors) == 0,
        "placed":  placed,
        "deleted": deleted,
        "errors":  errors,
        "assembled_sequence": pub_name,
    }}))
'''
    return await bridge.execute_and_read(code)

