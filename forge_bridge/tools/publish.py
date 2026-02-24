"""
Publish workflow tools — shot rename, segment rename, sequence publish.

Post-conform workflow:
1. rename_shots → assign shot names on background track, propagate up
2. rename_segments → apply segment naming template across all tracks
3. publish_sequence → export via PyExporter with preset
"""

from pydantic import BaseModel, Field
from typing import Optional

from forge_mcp import bridge


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
