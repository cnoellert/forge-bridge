"""Probe #5 — typed-selection reachability + reconstructability (Phase X).

Runs standalone inside Flame (SGTK Python console). Tests, per context
(media-panel / timeline / batch), TWO axes the capture-model spec gates on:
  (a) reachability      — can a standalone snippet PULL the selection?
  (b) reconstructability — can it reproduce the op's guard predicate
                           (nominal isinstance / duck-typed hasattr / cardinality)?

Dumps RAW (the probe-#3/#4 lesson: a derived verdict can lie, the raw can't).
Writes the result to OUT_PATH AND prints it. No forge_bridge import (stdlib only).

Run:  exec(open('<this file abs path>').read())
"""
import flame
import json
import os
import datetime

OUT_PATH = os.path.expanduser("~/.forge-bridge/probe5-typed-selection.json")   # latest run (quick eyeball)
RUNS_PATH = os.path.expanduser("~/.forge-bridge/probe5-runs.jsonl")            # ALL runs (atomic append — sweep-safe)

_REFERENT_TYPES = (
    "PySequence", "PyClip", "PyClipNode", "PyOFXNode", "PyWriteFileNode", "PySegment",
)


def _safe(x):
    try:
        return str(x)
    except Exception:
        return "<unreprable>"


def _try(fn):
    try:
        return {"ok": True, "value": fn()}
    except Exception as e:
        return {"ok": False, "error": "{}: {}".format(type(e).__name__, e)}


def _describe(item):
    d = {"type": type(item).__name__, "isinstance": [], "has_record_in": hasattr(item, "record_in")}
    for tn in _REFERENT_TYPES:
        t = getattr(flame, tn, None)
        try:
            if t is not None and isinstance(item, t):
                d["isinstance"].append(tn)
        except Exception:
            pass
    try:
        d["name"] = _safe(getattr(item, "name", None))
    except Exception:
        d["name"] = None
    return d


def _items(seq):
    try:
        L = list(seq)
        return {"count": len(L), "items": [_describe(x) for x in L]}
    except Exception as e:
        return {"iter_error": "{}: {}".format(type(e).__name__, e), "repr": _safe(seq)}


def _seg_walk():
    res = []
    for ver in list(flame.timeline.clip.versions)[:1]:
        for trk in list(ver.tracks):
            for seg in list(trk.segments):
                try:
                    if bool(seg.selected):
                        res.append(_describe(seg))
                except Exception:
                    pass
    return {"count": len(res), "items": res}


def _node_walk():
    res = []
    for n in list(flame.batch.nodes):
        try:
            if bool(n.selected):
                res.append(_describe(n))
        except Exception:
            pass
    return {"count": len(res), "items": res}


def main():
    out = {}
    try:
        out["captured_at"] = datetime.datetime.now().isoformat()
    except Exception:
        out["captured_at"] = None
    try:
        out["current_tab"] = _safe(flame.get_current_tab())   # auto context-label per run
    except Exception:
        out["current_tab"] = None
    try:
        out["flame_version"] = _safe(flame.get_version())
    except Exception:
        out["flame_version"] = None

    out["media_panel"] = {
        "has_media_panel": hasattr(flame, "media_panel"),
        "selected_entries": _try(lambda: _items(flame.media_panel.selected_entries)),
    }
    out["timeline"] = {
        "segment_walk": _try(_seg_walk),
        "selected_segments_direct": _try(lambda: _items(flame.timeline.clip.selected_segments)),
    }
    out["batch"] = {
        "selected_nodes_direct": _try(lambda: _items(flame.batch.selected_nodes)),
        "node_walk": _try(_node_walk),
    }

    blob = json.dumps(out, indent=2, default=_safe)
    line = json.dumps(out, default=_safe)
    try:
        os.makedirs(os.path.dirname(RUNS_PATH), exist_ok=True)
        with open(RUNS_PATH, "a") as fh:          # ACCUMULATE every run (sweep-safe)
            fh.write(line + "\n")
        with open(OUT_PATH, "w") as fh:           # latest, for a quick eyeball
            fh.write(blob)
        where = "appended -> {}  (latest also at {})".format(RUNS_PATH, OUT_PATH)
    except Exception as e:
        where = "WRITE FAILED: {}: {}".format(type(e).__name__, e)

    print(blob)
    print("\n[probe5] tab={} | {}".format(out.get("current_tab"), where))


main()
