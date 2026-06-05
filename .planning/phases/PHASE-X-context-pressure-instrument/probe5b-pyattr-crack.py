"""Probe #5b — crack the non-iterable selection PyAttribute (Phase X).

Probe #5 established: media_panel.selected_entries is a clean pull; the per-element
.selected flag is always-truthy (broken); the TRUE timeline/batch selection lives in
clip.selected_segments / batch.selected_nodes — non-iterable PyAttributes that the
repr shows ARE truthful (run #5: [<PyActionNode>]) but list()/for raises TypeError.

This probe tries candidate extraction methods on each, and dumps dir() so we can see
what the PyAttribute actually exposes. Outcome decides the timeline+batch fork:
  - some method extracts the selected objects -> PULL viable (reachable+reconstructable)
  - nothing works / dir() is opaque        -> PUSH-at-hook (capture where Flame pushes it)

Run with a couple of SEGMENTS selected on the timeline AND a couple of NODES selected
in batch, so both wrappers are non-empty. Appends to OUT (sweep-safe). Stdlib only.

Run:  exec(open('<this file abs path>').read())
"""
import flame
import json
import os
import datetime

OUT = os.path.expanduser("~/.forge-bridge/probe5b-pyattr-crack.jsonl")


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


def _crack(obj):
    """Try every plausible way to extract objects from a PyAttribute wrapper."""
    r = {
        "type": type(obj).__name__,
        "repr": _safe(obj),
        "bool": _try(lambda: bool(obj)),
        "len": _try(lambda: len(obj)),
        "subscript_0": _try(lambda: _safe(obj[0])),
        "by_index": _try(lambda: [_safe(obj[i]) for i in range(len(obj))]),
        "get_value": _try(lambda: _safe(obj.get_value())),
        "list_call": _try(lambda: [_safe(x) for x in list(obj)]),
        "dir": _try(lambda: [a for a in dir(obj) if not a.startswith("__")]),
    }
    return r


out = {}
try:
    out["captured_at"] = datetime.datetime.now().isoformat()
except Exception:
    out["captured_at"] = None
try:
    out["current_tab"] = _safe(flame.get_current_tab())
except Exception:
    out["current_tab"] = None

out["timeline_selected_segments"] = _try(lambda: _crack(flame.timeline.clip.selected_segments))
out["batch_selected_nodes"] = _try(lambda: _crack(flame.batch.selected_nodes))

blob = json.dumps(out, indent=2, default=_safe)
try:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as fh:
        fh.write(json.dumps(out, default=_safe) + "\n")
    where = "appended -> {}".format(OUT)
except Exception as e:
    where = "WRITE FAILED: {}: {}".format(type(e).__name__, e)

print(blob)
print("\n[probe5b] tab={} | {}".format(out.get("current_tab"), where))
