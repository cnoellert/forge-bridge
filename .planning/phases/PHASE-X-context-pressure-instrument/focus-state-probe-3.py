# Focus-State Probe #3 — the last open question: on-demand TIMELINE selection
#
# Probe #2 found the loaded sequence is flame.timeline.clip (a PySequence), but my
# resolver looked for .sequence/.current_sequence (absent) so the per-segment
# .selected test never ran. #3 resolves clip correctly and tests whether timeline
# segment SELECTION is readable on-demand — the single fact that decides whether
# the Python Console is selection-capable (Creative's Console choice stands) or
# selection-blind (must be a UI-action hook).
#
# SETUP BEFORE RUNNING: load a sequence in the Timeline player and SELECT 2-3
#   segments in it (this is the state we're testing the readability of).
# SAFE: read-only; never invokes a discovered callable.

import flame
import json


def _safe(v, _d=0):
    if _d > 3:
        return f"<{type(v).__name__}>"
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe(x, _d + 1) for x in list(v)[:24]]
    for attr in ("name",):
        try:
            n = getattr(v, attr)
            n = n() if callable(n) else n
            return f"{type(v).__name__}:{str(n).strip(chr(39))}"
        except Exception:
            pass
    try:
        return f"{type(v).__name__}:{str(v).strip(chr(39))}"
    except Exception:
        return f"<{type(v).__name__}>"


def _read(obj, name):
    try:
        attr = getattr(obj, name)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "callable": True} if callable(attr) else {"ok": True, "value": _safe(attr)}


def _scan(obj, names):
    return {n: _read(obj, n) for n in names}


report = {"probe_version": "3", "flame_version": _safe(flame.get_version())}

clip = None
try:
    clip = flame.timeline.clip
    report["clip"] = _safe(clip)
    report["clip_dir_public"] = [n for n in dir(clip) if not n.startswith("__")]
    report["clip_targeted"] = _scan(clip, [
        "selected_segments", "selection", "versions", "name", "duration", "markers",
    ])
except Exception as e:
    report["clip_error"] = f"{type(e).__name__}: {e}"

# THE decisive walk: clip → versions → tracks → segments → .selected
seg_sample = []
n_selected = 0
n_total = 0
try:
    for ver in list(getattr(clip, "versions", []) or [])[:1]:
        for trk in list(getattr(ver, "tracks", []) or [])[:6]:
            for s in list(getattr(trk, "segments", []) or [])[:40]:
                n_total += 1
                sel = _read(s, "selected")
                if sel.get("value") is True:
                    n_selected += 1
                if len(seg_sample) < 12:
                    seg_sample.append({
                        "name": _safe(s),
                        "type": type(s).__name__,
                        "selected": sel,
                    })
    report["segment_walk"] = {
        "total_segments_seen": n_total,
        "selected_count": n_selected,
        "sample": seg_sample,
        "verdict": (
            "ON-DEMAND SELECTION READABLE" if n_selected > 0
            else "no segment reported selected=True — either none selected, or "
                 ".selected is not on-demand readable (re-run with segments selected)"
        ),
    }
except Exception as e:
    report["segment_walk"] = f"<err {type(e).__name__}: {e}>"

# current_segment detail — why was .name empty in probe #2?
try:
    cs = flame.timeline.current_segment
    report["current_segment_detail"] = _scan(cs, [
        "name", "selected", "start_frame", "record_duration", "parent", "type", "shot_name",
    ])
    report["current_segment_dir_public"] = [n for n in dir(cs) if not n.startswith("__")]
except Exception as e:
    report["current_segment_error"] = f"{type(e).__name__}: {e}"

print("\n========== FOCUS-STATE PROBE #3 RESULT (copy everything below) ==========\n")
print(json.dumps(report, indent=2, default=str))
print("\n========== END FOCUS-STATE PROBE #3 RESULT ==========\n")
