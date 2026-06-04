# Operator Focus-State Reachability Probe #2 — targeted getattr on PyTimeline
#
# WHY #2: probe #1 found `flame.timeline` (a live PyTimeline) but never opened it,
#   and proved dir() UNDER-reports Flame's dynamic attributes (desk.current_sequence
#   read fine but wasn't in dir(desk)). So #2 switches from dir()-discovery to
#   TARGETED getattr on guessed names — the only reliable way to map a dynamic API.
#
# THE LOAD-BEARING QUESTION: is SELECTION readable on-demand anywhere (PyTimeline /
#   loaded sequence / batch), or ONLY via customUIAction(selection)? The answer
#   decides whether the Python Console is selection-blind (→ surface decision).
#
# SETUP BEFORE RUNNING (so focus state EXISTS to read):
#   1. Load a sequence into the Timeline player.
#   2. Select 2-3 segments in that sequence.
#   3. Open a batch group and select a node.
# Then paste this whole file into the SGTK Python Console and copy the JSON back.
#
# SAFE: read-only. Targeted getattr + value rendering. Never invokes a discovered
#   callable (callables are reported as "<callable>", not called).

import flame
import json


def _safe(v, _d=0):
    if _d > 3:
        return f"<{type(v).__name__}>"
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe(x, _d + 1) for x in list(v)[:16]]
    if isinstance(v, dict):
        return {str(k): _safe(x, _d + 1) for k, x in list(v.items())[:16]}
    for attr in ("name", "project_name"):
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
    """Targeted getattr — report exist/value/callable/error for ONE name."""
    try:
        attr = getattr(obj, name)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if callable(attr):
        return {"ok": True, "callable": True}
    return {"ok": True, "value": _safe(attr)}


def _scan(obj, names):
    return {n: _read(obj, n) for n in names}


report = {"probe_version": "2", "flame_version": _safe(flame.get_version())}

# ── PyTimeline — the unprobed handle (playhead / loaded sequence / selection) ─
tl = None
try:
    tl = flame.timeline
    report["timeline_repr"] = _safe(tl)
except Exception as e:
    report["timeline_error"] = f"{type(e).__name__}: {e}"

_TIMELINE_NAMES = [
    # loaded sequence / clip
    "sequence", "current_sequence", "clip", "current_clip", "duration",
    "name", "frame_rate",
    # playhead / current frame / time
    "current_time", "current_frame", "playhead", "position", "cursor_position",
    "time", "current_position",
    # segment / track focus
    "current_segment", "selected_segments", "selection", "current_track",
    "current_version", "tracks",
    # marks
    "in_mark", "out_mark", "markers",
]
report["timeline_targeted"] = _scan(tl, _TIMELINE_NAMES) if tl is not None else {}

# Also raw dir() of PyTimeline as ONE more signal (acknowledged under-reporting).
try:
    report["timeline_dir_public"] = [n for n in dir(tl) if not n.startswith("__")]
except Exception as e:
    report["timeline_dir_public"] = f"<err {type(e).__name__}: {e}>"

# ── On-demand SELECTION across every plausible holder (the decisive test) ────
selection_probe = {}

# (a) timeline-level selection
if tl is not None:
    selection_probe["timeline.selected_segments"] = _read(tl, "selected_segments")
    selection_probe["timeline.selection"] = _read(tl, "selection")

# (b) loaded-sequence selection — resolve the sequence first, several ways
seq = None
for holder, name in ((tl, "sequence"), (tl, "current_sequence")):
    if holder is None:
        continue
    try:
        cand = getattr(holder, name)
        if cand is not None and not callable(cand):
            seq = cand
            report["resolved_sequence_via"] = f"flame.timeline.{name}"
            break
    except Exception:
        pass
if seq is None:
    # fall back: desktop.current_sequence (probe #1 had it null — recheck w/ load)
    try:
        cand = flame.projects.current_project.current_workspace.desktop.current_sequence
        report["desktop.current_sequence_now"] = _safe(cand)
        if cand is not None:
            seq = cand
            report["resolved_sequence_via"] = "desktop.current_sequence"
    except Exception as e:
        report["desktop.current_sequence_now"] = f"<err {type(e).__name__}: {e}>"

if seq is not None:
    selection_probe["sequence.selected_segments"] = _read(seq, "selected_segments")
    selection_probe["sequence.selection"] = _read(seq, "selection")
    # segments often expose a per-segment `.selected` bool — sample the first few.
    try:
        seg_sel = []
        for ver in list(getattr(seq, "versions", []) or [])[:1]:
            for trk in list(getattr(ver, "tracks", []) or [])[:2]:
                for s in list(getattr(trk, "segments", []) or [])[:6]:
                    seg_sel.append({"name": _safe(s), "selected": _read(s, "selected")})
        selection_probe["per_segment.selected_sample"] = seg_sel
    except Exception as e:
        selection_probe["per_segment.selected_sample"] = f"<err {type(e).__name__}: {e}>"
else:
    selection_probe["_sequence"] = "no sequence resolved — load one in the player first"

# (c) batch node selection
selection_probe["batch.selected_nodes"] = _read(flame.batch, "selected_nodes")
selection_probe["batch.current_node"] = _read(flame.batch, "current_node")
selection_probe["batch.cursor_position"] = _read(flame.batch, "cursor_position")

report["selection_ondemand"] = selection_probe

# ── emit ─────────────────────────────────────────────────────────────────────
print("\n========== FOCUS-STATE PROBE #2 RESULT (copy everything below) ==========\n")
print(json.dumps(report, indent=2, default=str))
print("\n========== END FOCUS-STATE PROBE #2 RESULT ==========\n")
