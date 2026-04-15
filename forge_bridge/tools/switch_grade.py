"""MCP tools for FORGE Streams — query and switch alternative media streams on timeline segments.

Provides two MCP tools:
    flame_query_alternatives  — query available grade alternatives for a segment
    flame_switch_grade        — swap a segment to an alternative grade via smart_replace_media

flame_query_alternatives requires the catalog WebSocket server (projekt-forge infrastructure)
and is stubbed in standalone forge-bridge with a clear error message.

flame_switch_grade performs the Flame-side media swap directly using smart_replace_media.
When a direct media path is known, it can be used without the catalog server.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from forge_bridge import bridge

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------

class QueryAlternativesInput(BaseModel):
    """Query available media streams (alternative grades/versions) for a timeline segment."""

    segment_name: str = Field(
        ...,
        description="Name of the timeline segment to find alternatives for.",
    )
    sequence_name: str = Field(
        ...,
        description="Name of the sequence containing the segment.",
    )
    reel_group: str = Field(
        default="Desktop",
        description="Reel group containing the sequence.",
    )
    reel: str = Field(
        default="Sequences",
        description="Reel containing the sequence.",
    )


class SwitchGradeInput(BaseModel):
    """Swap a Flame timeline segment to an alternative grade via smart_replace_media."""

    segment_name: str = Field(
        ...,
        description="Name of the segment to swap.",
    )
    sequence_name: str = Field(
        ...,
        description="Sequence containing the segment.",
    )
    reel_group: str = Field(
        default="Desktop",
        description="Reel group.",
    )
    reel: str = Field(
        default="Sequences",
        description="Reel.",
    )
    media_path: str = Field(
        ...,
        description="Absolute path to the alternative media file or openclip to swap to.",
    )


# ---------------------------------------------------------------------------
# Tool: query_alternatives
# ---------------------------------------------------------------------------

async def query_alternatives(params: QueryAlternativesInput) -> str:
    """Query available grade alternatives for a shot. Requires catalog server.

    NOTE: This function requires the catalog WebSocket server (ws://127.0.0.1:9998)
    which is part of projekt-forge infrastructure and is not available in standalone
    forge-bridge. Use switch_grade directly if you know the target media path.
    """
    return json.dumps({
        "error": "query_alternatives requires the catalog WebSocket server (ws://127.0.0.1:9998) "
                 "which is part of projekt-forge infrastructure. "
                 "Use switch_grade directly if you know the target media path."
    })


# ---------------------------------------------------------------------------
# Tool: switch_grade
# ---------------------------------------------------------------------------

async def switch_grade(params: SwitchGradeInput) -> str:
    """Swap a Flame timeline segment to an alternative grade via smart_replace_media.

    Workflow:
      1. Validate the media path exists on disk
      2. Find the target segment in the specified sequence
      3. Lock all version tracks to prevent smart_replace_media leaking across versions
      4. Import the alternative media into a scratch reel
      5. Call smart_replace_media on the target segment
      6. Unlock tracks and clean up scratch reel

    Returns JSON: {"success": true, "segment": ..., "swapped_to": ...} or {"error": ...}

    Note: The alternative media must have overlapping source timecodes with the
    target segment. If using openclip vstacks for grade switching, build the
    openclip externally and pass its path as media_path.
    """
    seg_name = params.segment_name
    seq_name = params.sequence_name
    reel_group = params.reel_group
    reel_name = params.reel
    media_path = params.media_path

    swap_code = f"""
import flame, json, os

SEG_NAME = {seg_name!r}
SEQ_NAME = {seq_name!r}
REEL_GROUP = {reel_group!r}
REEL_NAME = {reel_name!r}
MEDIA_PATH = {media_path!r}

result = {{"ok": False, "error": None}}

if not os.path.isfile(MEDIA_PATH) and not os.path.isdir(MEDIA_PATH):
    result["error"] = f"Media not found: {{MEDIA_PATH}}"
    print(json.dumps(result))
else:
    seq = None
    desktop = flame.projects.current_project.current_workspace.desktop
    for rg in desktop.reel_groups:
        if rg.name.get_value() != REEL_GROUP:
            continue
        for reel in rg.reels:
            if reel.name.get_value() != REEL_NAME:
                continue
            for s in (reel.sequences or []):
                if s.name.get_value() == SEQ_NAME:
                    seq = s
                    break
            break
        break

    if seq is None:
        result["error"] = f"Sequence '{{SEQ_NAME}}' not found"
        print(json.dumps(result))
    else:
        target_seg = None
        for ver in seq.versions:
            for trk in ver.tracks:
                for seg in (trk.segments or []):
                    if seg.name.get_value() == SEG_NAME:
                        target_seg = seg
                        break
                if target_seg: break
            if target_seg: break

        if target_seg is None:
            result["error"] = f"Segment '{{SEG_NAME}}' not found in '{{SEQ_NAME}}'"
            print(json.dumps(result))
        else:
            # Lock all version tracks before smart_replace_media
            locked_tracks = []
            for ver in seq.versions:
                for track in ver.tracks:
                    try:
                        if not track.locked.get_value():
                            track.locked.set_value(True)
                            locked_tracks.append(track)
                    except Exception:
                        pass

            # Import media into scratch reel, then smart_replace_media
            scratch = desktop.create_reel("_switch_grade_tmp")
            try:
                imported = flame.import_clips(MEDIA_PATH, scratch)
                if imported:
                    clip = imported[0]
                    target_seg.smart_replace_media(clip)
                    result["ok"] = True
                    try:
                        flame.delete(clip, confirm=False)
                    except Exception:
                        pass
                else:
                    result["error"] = "import_clips returned empty list"
            except Exception as e:
                result["error"] = str(e)
            finally:
                try:
                    flame.delete(scratch, confirm=False)
                except Exception:
                    pass

            # Unlock tracks
            for track in locked_tracks:
                try:
                    track.locked.set_value(False)
                except Exception:
                    pass

            print(json.dumps(result))
"""

    swap_result = await bridge.execute_json(swap_code, main_thread=True)

    if swap_result.get("ok"):
        return json.dumps(
            {
                "success": True,
                "segment": seg_name,
                "swapped_to": media_path,
            },
            indent=2,
        )
    else:
        return json.dumps(
            {"error": swap_result.get("error", "Unknown swap error")}, indent=2
        )
