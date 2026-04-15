"""
Reconform tools — smart_replace_media on timeline segments.

Provides two MCP tools:
    flame_reconform_sequence — Tag-driven reconform (source + shot modes)
    flame_replace_segment_media — Targeted per-segment media replacement

flame_reconform_sequence reads forge: tags from segments, discovers openclips
from the pipeline directory structure, and applies smart_replace_media.
No external mapping needed — the tool does the same work as the Flame hook.

flame_batch_replace_media is the escape hatch for arbitrary per-segment
media swaps where the caller knows the exact paths.
"""

import json
from typing import Optional

from pydantic import BaseModel, Field

from forge_bridge import bridge


# ── Input Models ────────────────────────────────────────────────────────


class ReconformSequenceInput(BaseModel):
    """Reconform a published sequence using forge tags and pipeline openclips."""
    sequence_name: str = Field(
        ..., description="Name of the sequence to reconform.",
    )
    reel_group: str = Field(
        ..., description="Reel group containing the sequence.",
    )
    reel: str = Field(
        ..., description="Reel containing the sequence.",
    )
    mode: str = Field(
        default="source",
        description="Reconform mode: "
        "'source' replaces per-layer segments with plate openclips. "
        "'shot' creates new version with L01 only, replaces with shot (comp) openclips.",
    )
    version_index: Optional[int] = Field(
        default=None,
        description="Editorial version to reconform from. "
        "None = auto-detect (first version with forge tags).",
    )


class ReplaceSegmentMediaInput(BaseModel):
    """Replace media on specific segments via smart_replace_media.

    Targeted operation: only replaces listed segments, preserving
    all timeline effects. Works for any media type — graded plates,
    raws, stock, alts, comp openclips.
    """
    sequence_name: str = Field(
        ..., description="Name of the sequence.",
    )
    reel_group: str = Field(
        ..., description="Reel group containing the sequence.",
    )
    reel: str = Field(
        ..., description="Reel containing the sequence.",
    )
    replacements: list[dict] = Field(
        ...,
        description="List of replacement instructions. Each dict has: "
        "'segment_name' (str), 'track_index' (int), 'record_in' (int), "
        "'media_path' (str — absolute path to clip/openclip). "
        "Optional: 'role' (str — informational, e.g. 'graded', 'raw').",
    )
    version_index: int = Field(
        default=-1,
        description="Which sequence version to operate on (-1 = editorial/last).",
    )


# ── Tool Implementations ───────────────────────────────────────────────


async def reconform_sequence(params: ReconformSequenceInput) -> str:
    """Reconform a sequence using forge tags and pipeline openclips.

    Reads forge: tags from segments, discovers openclips from the
    pipeline directory structure ({canonical}/_04_shots/), and applies
    smart_replace_media. Creates a new version on the sequence.

    For 'source' mode: replaces primary segments across all tracks
    with plate openclips ({shot}/images/openclip/{seg_name}.clip).

    For 'shot' mode: creates new version with L01 only, replaces
    with shot openclips ({shot}/images/comps/flame/clip/{shot}.clip).
    """
    code = _build_reconform_code(
        seq_name=params.sequence_name,
        reel_group=params.reel_group,
        reel=params.reel,
        mode=params.mode,
        version_index=params.version_index,
    )

    data = await bridge.execute_json(code, main_thread=True)
    return json.dumps(data, indent=2)


async def replace_segment_media(params: ReplaceSegmentMediaInput) -> str:
    """Replace media on specific segments via smart_replace_media.

    Targeted per-segment operation. Works for any media type — plates,
    raws, stock, alts, comps. The replacement media must have overlapping
    source timecodes with the target segment.
    """
    replacements_json = json.dumps(params.replacements)

    code = f"""
import flame, json, os

SEQ_NAME = {params.sequence_name!r}
REEL_GROUP = {params.reel_group!r}
REEL_NAME = {params.reel!r}
VERSION_INDEX = {params.version_index}
REPLACEMENTS = json.loads({replacements_json!r})

result = {{"ok": False, "replaced": [], "skipped": [], "errors": []}}

desktop = flame.projects.current_project.current_workspace.desktop

seq = None
rg_obj = None
for rg in desktop.reel_groups:
    if rg.name.get_value() != REEL_GROUP:
        continue
    rg_obj = rg
    for reel in rg.reels:
        if reel.name.get_value() != REEL_NAME:
            continue
        for s in (reel.sequences or []):
            if s.name.get_value() == SEQ_NAME:
                seq = s
                break
        break
    break

if not seq:
    result["errors"].append(f"Sequence '{{SEQ_NAME}}' not found")
else:
    ver = seq.versions[VERSION_INDEX]
    seg_lookup = {{}}
    for ti, track in enumerate(ver.tracks):
        for seg in (track.segments or []):
            sn = seg.name.get_value()
            if sn:
                seg_lookup[(sn, ti, seg.record_in.frame)] = seg

    scratch = rg_obj.create_reel("_replace_tmp")

    for repl in REPLACEMENTS:
        seg_name = repl["segment_name"]
        track_idx = repl["track_index"]
        rec_in = repl["record_in"]
        media_path = repl["media_path"]
        role = repl.get("role", "")

        target = seg_lookup.get((seg_name, track_idx, rec_in))
        if not target:
            result["skipped"].append(f"{{seg_name}}: not found at T{{track_idx}} rec={{rec_in}}")
            continue

        if not os.path.isfile(media_path):
            result["skipped"].append(f"{{seg_name}}: media missing")
            continue

        try:
            imported = flame.import_clips(media_path, scratch)
            if not imported:
                result["skipped"].append(f"{{seg_name}}: import failed")
                continue
            clip = imported[0]
            target.smart_replace_media(clip)
            new_fp = str(target.file_path).strip("'")[-50:] if target.file_path else ""
            result["replaced"].append({{
                "segment": seg_name, "track": track_idx,
                "role": role, "new_fp": new_fp,
            }})
            try:
                flame.delete(clip, confirm=False)
            except:
                pass
        except Exception as e:
            result["errors"].append(f"{{seg_name}}: {{e}}")

    try:
        for c in list(scratch.clips or []):
            try:
                flame.delete(c, confirm=False)
            except:
                pass
        flame.delete(scratch, confirm=False)
    except:
        pass

    result["ok"] = len(result["errors"]) == 0

print(json.dumps(result, indent=2))
"""
    data = await bridge.execute_json(code, main_thread=True)
    return json.dumps(data, indent=2)


# ── Code Generator ────────────────────────────────────────────────────


def _build_reconform_code(
    seq_name: str, reel_group: str, reel: str,
    mode: str, version_index: Optional[int],
) -> str:
    """Generate self-contained Flame Python for tag-driven reconform.

    The generated code:
    1. Loads the forge manifest + pipeline config to get the canonical path
    2. Finds the sequence by name in the specified reel group/reel
    3. Auto-detects the editorial version (or uses the provided index)
    4. Scans segments for forge: tags (shot name, role, primary/alt/skip)
    5. Discovers plate or shot openclips on disk
    6. Locks all tracks, copies editorial to a new version
    7. Applies smart_replace_media for each matched segment
    8. Cleans up scratch reel, unlocks tracks
    """
    vi_repr = repr(version_index)

    return f"""\
import flame, json, os, re

SEQ_NAME = {seq_name!r}
REEL_GROUP = {reel_group!r}
REEL_NAME = {reel!r}
MODE = {mode!r}
VERSION_INDEX_OVERRIDE = {vi_repr}

result = {{
    "ok": False,
    "mode": MODE,
    "version_created": False,
    "editorial_version": None,
    "replaced": [],
    "deleted_upper": 0,
    "skipped": [],
    "errors": [],
    "scan_summary": {{}},
}}


# ── Pipeline config ──────────────────────────────────────────────────

def _load_canonical():
    project = flame.projects.current_project
    setups_dir = str(project.setups_folder)
    manifest_path = os.path.join(setups_dir, "status", "forge_manifest.json")
    if not os.path.isfile(manifest_path):
        return None, f"No manifest at {{manifest_path}}"
    with open(manifest_path) as f:
        manifest = json.load(f)
    projekt_root = manifest.get("projekt_root", "")
    config_dir = manifest.get("forge_config_dir", "")
    if not projekt_root or not config_dir:
        return None, "Manifest missing projekt_root or forge_config_dir"
    config_path = os.path.join(projekt_root, config_dir, "pipeline_config.json")
    if not os.path.isfile(config_path):
        return None, f"No config at {{config_path}}"
    with open(config_path) as f:
        config = json.load(f)
    return config.get("canonical", projekt_root), None


# ── Tag reading ──────────────────────────────────────────────────────

SHOT_PREFIX = "forge:shot="
_META_PREFIXES = ("forge:shot", "forge:alt", "forge:primary",
                  "forge:skip", "forge:prefix", "forge:publish",
                  "forge:renamed")
KNOWN_ROLES = frozenset([
    "graded", "raw", "denoised", "flat", "external", "scans",
    "stock", "source", "graphics", "reference", "comp",
])

def _seg_tags(seg):
    try:
        return set(seg.tags.get_value() or [])
    except Exception:
        return set()

def _tag_value(tags, prefix):
    for t in tags:
        if t.startswith(prefix):
            return t[len(prefix):]
    return ""

def _tag_role(tags):
    for t in tags:
        if t.startswith("forge:") and not any(t.startswith(p) for p in _META_PREFIXES):
            role = t[len("forge:"):]
            if role in KNOWN_ROLES:
                return role
    return ""


# ── Find editorial version ───────────────────────────────────────────

def _find_editorial_version(seq):
    versions = seq.versions
    if not versions:
        return 0
    for vi, ver in enumerate(versions):
        tracks = ver.tracks
        if not tracks:
            continue
        total_named = 0
        has_forge = False
        for track in tracks:
            for seg in (track.segments or []):
                sn = seg.name.get_value() if seg.name else ""
                if sn:
                    total_named += 1
                    tags = _seg_tags(seg)
                    if any(t.startswith("forge:shot=") for t in tags):
                        has_forge = True
        if has_forge:
            return vi
        if total_named > 1 and vi > 0:
            return vi
    return min(1, len(versions) - 1)


# ── Scan segments ────────────────────────────────────────────────────

def _scan_segments(seq, version_index):
    entries = []
    ver = seq.versions[version_index]
    for ti, track in enumerate(ver.tracks):
        for seg in (track.segments or []):
            seg_name = seg.name.get_value() if seg.name else ""
            if not seg_name:
                continue
            tags = _seg_tags(seg)
            shot_name = _tag_value(tags, SHOT_PREFIX)
            if not shot_name:
                continue
            entries.append({{
                "seg_name": seg_name,
                "shot_name": shot_name,
                "role": _tag_role(tags),
                "track_index": ti,
                "record_in": seg.record_in.frame,
                "is_primary": "forge:primary" in tags,
                "is_alt": "forge:alt" in tags,
                "is_skip": "forge:skip" in tags,
            }})
    return entries


# ── Openclip discovery ───────────────────────────────────────────────

def _find_plate_openclips(canonical, entries):
    found = {{}}
    for e in entries:
        p = os.path.join(canonical, "_04_shots", e["shot_name"],
                         "images", "openclip", f"{{e['seg_name']}}.clip")
        if os.path.isfile(p):
            found[e["seg_name"]] = p
    return found

def _find_shot_openclips(canonical, entries):
    found = {{}}
    seen = set()
    for e in entries:
        shot = e["shot_name"]
        if shot in seen:
            continue
        seen.add(shot)
        p = os.path.join(canonical, "_04_shots", shot,
                         "images", "comps", "flame", "clip", f"{{shot}}.clip")
        if os.path.isfile(p):
            found[shot] = p
    return found


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

canonical, cfg_err = _load_canonical()
if cfg_err:
    result["errors"].append(f"Config: {{cfg_err}}")
    print(json.dumps(result, indent=2))
else:
    # Find sequence
    desktop = flame.projects.current_project.current_workspace.desktop
    seq = None
    rg_obj = None
    for rg in desktop.reel_groups:
        if rg.name.get_value() != REEL_GROUP:
            continue
        rg_obj = rg
        for reel in rg.reels:
            if reel.name.get_value() != REEL_NAME:
                continue
            for s in (reel.sequences or []):
                if s.name.get_value() == SEQ_NAME:
                    seq = s
                    break
            break
        break

    if not seq:
        result["errors"].append(f"Sequence '{{SEQ_NAME}}' not found in {{REEL_GROUP}}/{{REEL_NAME}}")
        print(json.dumps(result, indent=2))
    else:
        # Determine editorial version
        if VERSION_INDEX_OVERRIDE is not None:
            vi = VERSION_INDEX_OVERRIDE
        else:
            vi = _find_editorial_version(seq)
        result["editorial_version"] = vi

        if vi < 0 or vi >= len(seq.versions):
            result["errors"].append(f"Version index {{vi}} out of range (0-{{len(seq.versions)-1}})")
            print(json.dumps(result, indent=2))
        else:
            # Scan segments for forge tags
            entries = _scan_segments(seq, vi)
            result["scan_summary"] = {{
                "total_tagged": len(entries),
                "primary": sum(1 for e in entries if e["is_primary"]),
                "alt": sum(1 for e in entries if e["is_alt"]),
                "skip": sum(1 for e in entries if e["is_skip"]),
            }}

            if not entries:
                result["errors"].append("No forge-tagged segments found. Run rename first.")
                print(json.dumps(result, indent=2))
            else:
                # Discover openclips
                if MODE == "source":
                    oc_map = _find_plate_openclips(canonical, entries)
                    # Build replacements: primary, non-skip segments with openclips
                    replacements = []
                    for e in entries:
                        if e["is_skip"] or not e["is_primary"]:
                            result["skipped"].append(
                                f"{{e['seg_name']}}: {{'skip' if e['is_skip'] else 'alt/non-primary'}}")
                            continue
                        oc = oc_map.get(e["seg_name"])
                        if not oc:
                            result["skipped"].append(f"{{e['seg_name']}}: no plate openclip on disk")
                            continue
                        replacements.append(e | {{"openclip_path": oc}})
                else:
                    oc_map = _find_shot_openclips(canonical, entries)
                    # Build replacements: L01, non-skip, T0 segments with openclips
                    _L01 = re.compile(r'_L01$')
                    replacements = []
                    seen_shots = set()
                    for e in entries:
                        if e["is_skip"]:
                            result["skipped"].append(f"{{e['seg_name']}}: skip tag")
                            continue
                        if e["track_index"] != 0:
                            continue
                        if not _L01.search(e["seg_name"]):
                            continue
                        shot = e["shot_name"]
                        if shot in seen_shots:
                            continue
                        seen_shots.add(shot)
                        oc = oc_map.get(shot)
                        if not oc:
                            result["skipped"].append(f"{{shot}}: no shot openclip on disk")
                            continue
                        replacements.append(e | {{"openclip_path": oc}})

                result["scan_summary"]["matched"] = len(replacements)
                result["scan_summary"]["openclips_found"] = len(oc_map)

                if not replacements:
                    result["errors"].append(
                        f"No openclips matched. canonical={{canonical}}, "
                        f"openclips_found={{len(oc_map)}}")
                    print(json.dumps(result, indent=2))
                else:
                    # ── Execute reconform ─────────────────────────────────
                    scratch = rg_obj.create_reel("_reconform_tmp")
                    src_ver = seq.versions[vi]

                    # Find overwrite time from first real segment on T0
                    ow_time = None
                    for seg in src_ver.tracks[0].segments:
                        if seg.name.get_value():
                            ow_time = seg.record_in
                            break

                    if not ow_time:
                        result["errors"].append("No named segment on T0 for overwrite time")
                        try:
                            flame.delete(scratch, confirm=False)
                        except Exception:
                            pass
                        print(json.dumps(result, indent=2))
                    else:
                        # Lock ALL version tracks to prevent smart_replace_media leak
                        locked_tracks = []
                        for ver in seq.versions:
                            for track in ver.tracks:
                                was_locked = track.locked.get_value()
                                if not was_locked:
                                    track.locked.set_value(True)
                                    locked_tracks.append(track)

                        # Copy editorial to new version
                        standalone = src_ver.copy_to_media_panel(scratch)
                        new_ver = seq.create_version()
                        t0 = new_ver.tracks[0]
                        seq.overwrite(standalone, overwrite_time=ow_time,
                                      destination_track=t0)
                        result["version_created"] = True

                        try:
                            flame.delete(standalone, confirm=False)
                        except Exception:
                            pass

                        if MODE == "shot":
                            # Delete upper track footage segments (keep graphics)
                            _LAYER_PAT = re.compile(r'_L\\d+$')
                            for ti in range(1, len(new_ver.tracks)):
                                for seg in list(new_ver.tracks[ti].segments or []):
                                    sn = seg.name.get_value()
                                    if sn and _LAYER_PAT.search(sn):
                                        try:
                                            flame.delete(seg, confirm=False)
                                            result["deleted_upper"] += 1
                                        except Exception:
                                            pass

                        # Build segment lookup on new version
                        if MODE == "source":
                            seg_lookup = {{}}
                            for ti, track in enumerate(new_ver.tracks):
                                for seg in (track.segments or []):
                                    sn = seg.name.get_value()
                                    if sn:
                                        seg_lookup[(sn, ti, seg.record_in.frame)] = seg
                        else:
                            seg_lookup = {{}}
                            for seg in (new_ver.tracks[0].segments or []):
                                sn = seg.name.get_value()
                                if sn:
                                    seg_lookup[(sn, seg.record_in.frame)] = seg

                        # smart_replace_media
                        for repl in replacements:
                            seg_name = repl["seg_name"]
                            oc_path = repl["openclip_path"]

                            if MODE == "source":
                                key = (seg_name, repl["track_index"], repl["record_in"])
                            else:
                                key = (seg_name, repl["record_in"])

                            target = seg_lookup.get(key)
                            if not target:
                                result["skipped"].append(f"{{seg_name}}: not found in new version")
                                continue

                            try:
                                imported = flame.import_clips(oc_path, scratch)
                                if not imported:
                                    result["skipped"].append(f"{{seg_name}}: import failed")
                                    continue
                                clip = imported[0]
                                target.smart_replace_media(clip)
                                if MODE == "source":
                                    result["replaced"].append({{
                                        "segment": seg_name,
                                        "track": repl["track_index"],
                                    }})
                                else:
                                    result["replaced"].append(repl["shot_name"])
                                try:
                                    flame.delete(clip, confirm=False)
                                except Exception:
                                    pass
                            except Exception as e:
                                result["errors"].append(f"{{seg_name}}: {{e}}")

                        # Unlock tracks
                        for track in locked_tracks:
                            try:
                                track.locked.set_value(False)
                            except Exception:
                                pass

                        # Name tracks
                        if MODE == "source":
                            replaced_tracks = set(
                                r["track"] for r in result["replaced"]
                                if isinstance(r, dict)
                            )
                            for ti in replaced_tracks:
                                if ti < len(new_ver.tracks):
                                    try:
                                        new_ver.tracks[ti].name.set_value("source published")
                                    except Exception:
                                        pass
                        else:
                            try:
                                new_ver.tracks[0].name.set_value("shots published")
                            except Exception:
                                pass
                            for ti in range(1, len(new_ver.tracks)):
                                try:
                                    new_ver.tracks[ti].name.set_value("*")
                                except Exception:
                                    pass

                        # Clean up scratch reel
                        try:
                            for c in list(scratch.clips or []):
                                try:
                                    flame.delete(c, confirm=False)
                                except Exception:
                                    pass
                            flame.delete(scratch, confirm=False)
                        except Exception:
                            pass

                        result["ok"] = len(result["errors"]) == 0
                        print(json.dumps(result, indent=2))
"""
