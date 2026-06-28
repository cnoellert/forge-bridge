import json, re

def _safe_str(val):
    """Strip PyAttribute quote wrapping."""
    s = str(val).strip("'\"")
    return s if s else ""

def _safe_int(val):
    """int() with infinite/error handling."""
    try:
        v = int(val)
        return v
    except (ValueError, TypeError):
        return None

def _parse_fps(fps_str):
    """Extract numeric fps from Flame's '23.976 fps' format."""
    m = re.match(r'([\d.]+)', str(fps_str))
    return float(m.group(1)) if m else None

def _extract_segment(seg):
    """Extract one segment to a plain dict."""
    source_name = getattr(seg, "source_name", None)
    if not source_name:
        return None
    sn = _safe_str(source_name)
    if not sn:
        return None

    # Colour space
    try:
        cs = seg.get_colour_space() or ""
    except Exception:
        cs = ""

    # Tags
    try:
        tags = seg.tags.get_value() if hasattr(seg.tags, "get_value") else []
    except Exception:
        tags = []

    # File path
    try:
        fp = str(seg.file_path) if hasattr(seg, "file_path") else ""
    except Exception:
        fp = ""

    # Source duration
    try:
        sd_frame = seg.source_duration.frame
    except Exception:
        sd_frame = None

    # Timewarp extraction — reuses the proven frame mapping from
    # forge-align (_get_segment_info + _source_frame_at_record pattern).
    tw_data = None
    try:
        tw = None
        for fx in seg.effects:
            if fx.type == "Timewarp":
                tw = fx
                break

        if tw is not None:
            import os as _os
            rec_in = seg.record_in.frame
            rec_out = seg.record_out.frame
            rec_dur = rec_out - rec_in
            src_in = seg.source_in.frame

            try:
                head = int(seg.head)
            except (ValueError, TypeError, OverflowError):
                head = 0

            # frame_offset: forge-align pattern — differs for sequences vs containers
            _CONTAINER_EXTS = {".mov", ".mxf", ".mp4", ".avi", ".arx"}
            file_ext = _os.path.splitext(fp)[1].lower() if fp else ""
            is_container = file_ext in _CONTAINER_EXTS

            if is_container:
                frame_offset = src_in - head
            else:
                frame_offset = 0
                _m = re.match(r'^(.*?)(\d+)(\.\w+)$', _os.path.basename(fp)) if fp else None
                if _m:
                    disk_first = int(_m.group(2))
                    frame_offset = src_in - (disk_first + head)

            tw_mode = str(tw.mode).strip("'\"")  # "Timing" or "Speed"

            # Per-frame source map using forge-align formula:
            # disk_frame = src_in - head + (timing_val - 1) - frame_offset
            timing_samples = []
            for i in range(rec_dur):
                seg_frame = float(i + 1)  # 1-based segment-relative
                try:
                    if tw_mode == "Timing":
                        tv = tw.get_timing(seg_frame)
                    else:
                        tv = tw.get_speed_timing(seg_frame)
                    disk_frame = int(src_in - head + (tv - 1.0) - frame_offset)
                    timing_samples.append(disk_frame)
                except Exception:
                    timing_samples.append(None)

            # Effective speed ratio from actual sampled frames
            valid = [s for s in timing_samples if s is not None]
            if len(valid) >= 2:
                source_span = valid[-1] - valid[0]
                speed_ratio = source_span / max(1, rec_dur - 1)
            else:
                speed_ratio = 1.0

            tw_data = {
                "mode": tw_mode,
                "speed_ratio": round(speed_ratio, 6),
                "frame_offset": frame_offset,
                "timing_samples": timing_samples,
            }
    except Exception:
        tw_data = None

    # Phase 21 — Effect capture (adjacent to Timewarp block above).
    # Runs in Flame analyzer phase BEFORE any render cycle.  seg.effects
    # access during render cycles causes SIGSEGV; pre-export is safe
    # (project memory feedback_no_seg_effects_in_export).
    # save_setup() requires main_thread=True on bridge calls (caller
    # responsibility — already the case for build_extraction_code users).
    # CLAUDE.md gotcha: save_setup replaces dots with underscores in output
    # filenames — dotless stems avoid ghost filenames.
    effect_setups = []
    try:
        import os as _os
        import tempfile as _tempfile
        _eff_root = _tempfile.mkdtemp(prefix="forge_effect_capture_")
        for _order, _fx in enumerate(seg.effects):
            _etype = "unknown"
            try:
                _etype = str(_fx.type) if hasattr(_fx, "type") else "unknown"
                _safe = _etype.lower().replace(" ", "_").replace("/", "_")
                _stem = _os.path.join(_eff_root, f"{_order:02d}_{_safe}")
                _fx.save_setup(_stem)
                effect_setups.append({
                    "order": _order,
                    "type": _etype,
                    "stem": _stem,
                    "error": None,
                })
            except Exception as _err:
                effect_setups.append({
                    "order": _order,
                    "type": _etype,
                    "stem": None,
                    "error": str(_err),
                })
    except Exception as _err:
        # Outer failure: whole iteration bombed out.  Record sentinel.
        effect_setups = [{
            "order": -1, "type": "extraction_error",
            "stem": None, "error": str(_err),
        }]

    return {
        "name":          _safe_str(seg.name),
        "source_name":   sn,
        "source_in":     seg.source_in.frame,
        "source_out":    seg.source_out.frame,
        "record_in":     seg.record_in.frame,
        "record_out":    seg.record_out.frame,
        "source_in_tc":  seg.source_in.timecode,
        "source_out_tc": seg.source_out.timecode,
        "record_in_tc":  seg.record_in.timecode,
        "record_out_tc": seg.record_out.timecode,
        "head":          _safe_int(seg.head),
        "tail":          _safe_int(seg.tail),
        "tape_name":     _safe_str(seg.tape_name) if hasattr(seg, "tape_name") else "",
        "file_path":     fp,
        "colour_space":  cs,
        "tags":          tags or [],
        "source_duration_frames": sd_frame,
        "start_frame":   _safe_int(seg.start_frame) if hasattr(seg, "start_frame") else None,
        "timewarp":      tw_data,
        # Phase 21 additions:
        "effect_setups": effect_setups,
    }

def _extract_sequence(seq):
    """Extract one PySequence to a plain dict."""
    seq_name = _safe_str(seq.name)
    fps_str = str(seq.frame_rate)
    fps = _parse_fps(fps_str)
    drop_frame = bool(seq.drop_frame) if seq.drop_frame is not None else False

    # Duration
    try:
        dur_frame = seq.duration.frame
    except Exception:
        dur_frame = None

    # Resolution
    try:
        width = int(seq.width)
        height = int(seq.height)
    except Exception:
        width = height = None

    # Sequence-level tags
    try:
        seq_tags = seq.tags.get_value() if hasattr(seq.tags, "get_value") else []
    except Exception:
        seq_tags = []

    # Versions → tracks → segments
    versions_data = []
    versions = seq.versions
    for vi, ver in enumerate(versions):
        ver_name = _safe_str(ver.name) if ver.name is not None else ""
        tracks_data = []
        try:
            tracks = ver.tracks
        except Exception:
            tracks = []
        for ti, track in enumerate(tracks):
            track_name = _safe_str(track.name) if track.name is not None else ""
            try:
                locked = track.locked.get_value() if hasattr(track.locked, "get_value") else bool(track.locked)
            except Exception:
                locked = False

            segs_data = []
            try:
                track_segs = track.segments
            except Exception:
                track_segs = []
            for seg in track_segs:
                sd = _extract_segment(seg)
                if sd is not None:
                    # Phase 21: stamp the 0-based track index so pure-Python
                    # downstream can derive the composite key (D-06).
                    sd["track_idx"] = ti
                    segs_data.append(sd)

            tracks_data.append({
                "index":    ti,
                "name":     track_name,
                "locked":   locked,
                "segments": segs_data,
            })
        versions_data.append({
            "index":  vi,
            "name":   ver_name,
            "tracks": tracks_data,
        })

    # Audio tracks — separate from video in Flame
    audio_data = []
    try:
        audio_tracks = seq.audio_tracks
    except Exception:
        audio_tracks = []
    for ati, at in enumerate(audio_tracks):
        stereo = bool(at.stereo) if hasattr(at, "stereo") else False
        channels_data = []
        try:
            channels = at.channels
        except Exception:
            channels = []
        for ci, ch in enumerate(channels):
            ch_name = _safe_str(ch.name) if ch.name is not None else ""
            try:
                ch_locked = ch.locked.get_value() if hasattr(ch.locked, "get_value") else bool(ch.locked)
            except Exception:
                ch_locked = False
            ch_segs = []
            try:
                ch_segments = ch.segments
            except Exception:
                ch_segments = []
            for seg in ch_segments:
                sd = _extract_segment(seg)
                if sd is not None:
                    # Phase 21: stamp audio track index — uniform schema
                    # with video track walk.  Phase 21's builder filters
                    # audio segments; this keeps extraction forward-compat.
                    sd["track_idx"] = ati
                    ch_segs.append(sd)
            channels_data.append({
                "index": ci,
                "name": ch_name,
                "locked": ch_locked,
                "segments": ch_segs,
            })
        audio_data.append({
            "index": ati,
            "stereo": stereo,
            "channels": channels_data,
        })

    return {
        "name":        seq_name,
        "fps":         fps,
        "fps_string":  fps_str,
        "drop_frame":  drop_frame,
        "duration_frames": dur_frame,
        "width":       width,
        "height":      height,
        "tags":        seq_tags or [],
        "versions":    versions_data,
        "audio_tracks": audio_data,
    }

# --- Find and extract requested sequences ---
desktop = flame.projects.current_project.current_workspace.desktop
seq_filter = {'FORGE_UAT_HOST_APPLY_20260624'}
reel_filter = set()

results = []
for rg in desktop.reel_groups:
    for reel in rg.reels:
        reel_name = _safe_str(reel.name)
        if reel_filter and reel_name not in reel_filter:
            continue
        if hasattr(reel, "sequences"):
            for seq in reel.sequences:
                sn = _safe_str(seq.name)
                if seq_filter and sn not in seq_filter:
                    continue
                data = _extract_sequence(seq)
                data["reel_group"] = _safe_str(rg.name)
                data["reel_name"] = reel_name
                results.append(data)

class _SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        # Catch any PyAttribute or other Flame objects that slipped through
        return str(obj).strip("'\"")

print(json.dumps({"sequences": results}, cls=_SafeEncoder))