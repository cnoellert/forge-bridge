# Operator Focus-State Reachability Probe — Phase X (Context Pressure Instrument)
#
# PURPOSE: settle Q-focus-2 empirically — what operator FOCUS state the Flame
# Python API actually exposes on-demand, vs callback-only, vs absent. This bounds
# which contextual-reference TYPES the corpus can ever measure.
#
# WHERE TO RUN: the Flame SGTK Python Console
#   (/opt/Autodesk/presets/2025.2.1/shotgun/python/tk_multi_pythonconsole).
#   It runs on Flame's main thread, so `import flame` calls work synchronously —
#   no schedule_idle_event needed.
#
# HOW: open a project (and ideally open a batch + load a sequence in the player +
#   select a couple of segments) so focus state EXISTS to be probed, then paste
#   this whole file into the console and run. Copy the final JSON block back.
#
# SAFE: read-only. It reads attributes and runs dir() introspection. It mutates
#   nothing, opens nothing, deletes nothing.

import flame
import json
import traceback


def _safe(v, _depth=0):
    """Best-effort JSON-friendly rendering of a Flame object."""
    if _depth > 2:
        return f"<{type(v).__name__}>"
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe(x, _depth + 1) for x in list(v)[:12]]
    if isinstance(v, dict):
        return {str(k): _safe(x, _depth + 1) for k, x in list(v.items())[:12]}
    # Flame wrapper objects: prefer .name, strip the PyAttribute quoting.
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


def _try(fn):
    """Run a probe lambda; capture value or the exception shape."""
    try:
        return {"ok": True, "value": _safe(fn())}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


_FOCUS_PATTERNS = (
    "current", "active", "select", "player", "frame", "time",
    "playhead", "position", "mark", "open", "tab", "sequence", "cursor",
)


def _focus_attrs(obj):
    """dir() filtered to focus-relevant attribute names — DISCOVERS the API
    surface so we don't have to guess accessor names."""
    out = {}
    try:
        names = dir(obj)
    except Exception as e:
        return {"_dir_error": f"{type(e).__name__}: {e}"}
    for name in names:
        if name.startswith("__"):
            continue
        if not any(p in name.lower() for p in _FOCUS_PATTERNS):
            continue
        try:
            attr = getattr(obj, name)
            if callable(attr):
                out[name] = "<callable>"  # do NOT invoke unknown callables
            else:
                out[name] = _safe(attr)
        except Exception as e:
            out[name] = f"<err {type(e).__name__}: {e}>"
    return out


report = {"probe_version": "1", "flame_version": _try(lambda: flame.get_version())}

# ── handles ────────────────────────────────────────────────────────────────
proj = ws = desk = None
try:
    proj = flame.projects.current_project
    ws = proj.current_workspace
    desk = ws.desktop
except Exception:
    report["handle_error"] = traceback.format_exc().splitlines()[-1]

# ── TIER A — global on-demand reads (expected: all reachable) ───────────────
report["tier_a_global"] = {
    "project": _try(lambda: proj.project_name),
    "workspace": _try(lambda: ws.name),
    "desktop": _try(lambda: desk.name),
    "current_tab": _try(lambda: flame.get_current_tab()),
    "batch_name": _try(lambda: flame.batch.name),
    "batch_opened": _try(lambda: flame.batch.opened),
    "batch_current_iteration": _try(lambda: flame.batch.current_iteration.name),
}

# ── TIER B — selection (expected: NO global accessor; callback-only) ────────
# We confirm absence by introspection — there should be no global selection read.
report["tier_b_selection"] = {
    "flame_dot_selection": _try(lambda: flame.selection),  # expected: error/absent
    "desktop_selection_attrs": {
        k: v for k, v in _focus_attrs(desk).items() if "select" in k.lower()
    },
    "module_selection_attrs": {
        k: v for k, v in _focus_attrs(flame).items() if "select" in k.lower()
    },
    "_note": "selection is delivered as a customUIAction(name, selection) arg, "
             "scoped to the invoking panel — not expected to be globally readable.",
}

# ── TIER C — the real unknowns: active sequence in player, playhead/frame ────
# Targeted guesses (report exist/value/error) ...
report["tier_c_targeted"] = {
    "desktop.current_reel": _try(lambda: desk.current_reel),
    "desktop.current_sequence": _try(lambda: desk.current_sequence),
    "ws.current_sequence": _try(lambda: ws.current_sequence),
    "flame.players": _try(lambda: flame.players),
    "flame.player": _try(lambda: flame.player),
    "flame.timeline": _try(lambda: flame.timeline),
    "flame.get_current_sequence": _try(lambda: flame.get_current_sequence()),
}

# ... plus introspection sweeps (DISCOVER what actually exists) ──────────────
report["tier_c_introspection"] = {
    "flame_module": _focus_attrs(flame),
    "current_project": _focus_attrs(proj),
    "current_workspace": _focus_attrs(ws),
    "desktop": _focus_attrs(desk),
    "batch": _try(lambda: _focus_attrs(flame.batch)),
}

# If a sequence is reachable anywhere on the desktop, introspect ONE for
# playhead/frame/position/mark attributes (the player-position unknown).
def _first_sequence():
    for rg in desk.reel_groups:
        for r in rg.reels:
            for s in list(r.sequences):
                return s
    raise RuntimeError("no sequence found on desktop")

report["tier_c_sequence_object"] = _try(lambda: _focus_attrs(_first_sequence()))

# ── emit ────────────────────────────────────────────────────────────────────
print("\n========== FOCUS-STATE PROBE RESULT (copy everything below) ==========\n")
print(json.dumps(report, indent=2, default=str))
print("\n========== END FOCUS-STATE PROBE RESULT ==========\n")
