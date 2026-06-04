# S3.4 — Context Pressure Capture (in-Flame Console orchestration)
#
# Paste into the Flame SGTK Python Console on the workstation (needs the :9996
# daemon up). Then, per capture, call:
#
#     capture("rename this sequence with prefix tv")
#     capture("what is the duration of this shot")
#
# (or `ask()` to type the prompt in a dialog).
#
# FLOW — resolver-blind via the TRANSPORT BOUNDARY:
#   1. snapshot world_state RAW in-Flame, at REQUEST TIME (the focus AT the prompt,
#      before the seconds-long compile can drift it)
#   2. POST prompt-only -> :9996/api/v1/chat   (compile stays desktop-blind)
#   3. read SSE: compile_complete.compiled_graph + the terminal outcome taxon
#   4. POST {prompt, compiled_graph, outcome, world_state_raw, provenance}
#         -> :9996/api/v1/context-capture       (storage-only; assembles
#            canonically server-side, appends; NEVER compiles)
#
# world_state NEVER crosses to /chat — only to /context-capture (a different route
# that never compiles). The guarantee is the wire itself.
#
# SELF-CONTAINED: Flame's python cannot import forge_bridge, so the world_state read
# MIRRORS forge_bridge/context_pressure/_focus.py FOCUS_SNAPSHOT_PY (validated by
# probe #4 — KEEP IN SYNC), and HTTP uses stdlib urllib only. Assembly/validation
# happen server-side via the canonical context_pressure functions (single source of
# truth) — this script only snapshots raw + relays.

import datetime
import json
import urllib.error
import urllib.request

import flame

DAEMON = "http://127.0.0.1:9996"
_PROVENANCE = {
    "context_source": "flame",
    "capture_version": "1",
    "capture_surface": "python_console",
    "capture_adapter": "sgtk_console_v1",
}
_TERMINAL = {"chain_complete", "preview_emitted", "apply_complete",
             "chain_aborted", "compile_error", "error"}


# ---- 1. world_state RAW snapshot (mirror of FOCUS_SNAPSHOT_PY; probe #4) -------
def _v(attr):
    try:
        return None if attr is None else str(attr)
    except Exception:
        return None


def _names(attr):
    # Flame selection attrs are non-iterable PyAttribute wrappers (probe #4) —
    # best-effort; non-critical (the assembler does not extract selected_nodes).
    try:
        return [_v(getattr(n, "name", n)) for n in list(attr)]
    except Exception:
        return None


def world_state_raw():
    proj = flame.projects.current_project
    batch = flame.batch
    tl = flame.timeline
    cur = getattr(tl, "current_segment", None)

    def _selection():
        out = []
        try:
            for ver in list(tl.clip.versions)[:1]:
                for trk in list(ver.tracks):
                    for seg in list(trk.segments):
                        try:
                            if bool(seg.selected):
                                out.append(_v(seg.shot_name) or _v(seg.name))
                        except Exception:
                            pass
        except Exception:
            pass
        return out

    return {
        "project": _v(proj.project_name),
        "current_tab": _v(flame.get_current_tab()),
        "batch": {
            "name": _v(batch.name),
            "opened": bool(batch.opened),
            "current_iteration": _v(getattr(batch, "current_iteration", None) and batch.current_iteration.name),
            "selected_nodes": _names(batch.selected_nodes),
        },
        "timeline": {
            "active_sequence": _v(getattr(tl.clip, "name", None)) if getattr(tl, "clip", None) else None,
            "current_shot": _v(getattr(cur, "shot_name", None)) if cur else None,
            "current_segment_name": _v(getattr(cur, "name", None)) if cur else None,
            "selection": _selection(),
        },
        "playhead_frame": None,
        "playhead_frame_reason": "unreachable_api",
    }


# ---- 2 + 3. prompt-only chat -> (compiled_graph, outcome) ----------------------
def _parse_sse(text):
    """forge-bridge single-line JSON SSE frames (event: / data: / blank)."""
    events = []
    name = data = None
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if line.startswith("event:"):
            name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data = line[len("data:"):].strip()
        elif line == "":
            if name is not None and data is not None:
                try:
                    events.append((name, json.loads(data)))
                except Exception:
                    events.append((name, {}))
            name = data = None
    return events


def _chat(prompt):
    body = json.dumps({"messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request(
        DAEMON + "/api/v1/chat", data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:   # >FB-C 125s wall-clock
        text = resp.read().decode("utf-8")
    compiled_graph = []
    outcome = "error"
    for name, data in _parse_sse(text):
        if name == "compile_complete":
            compiled_graph = data.get("compiled_graph") or []
        if name in _TERMINAL:
            outcome = name                                   # last terminal taxon wins
    return compiled_graph, outcome


# ---- 4. POST to the storage-only capture endpoint ------------------------------
def _post_capture(payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DAEMON + "/api/v1/context-capture", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return {"error": json.loads(exc.read().decode("utf-8"))}
        except Exception:
            return {"error": "HTTP %s" % exc.code}


# ---- public: one capture -------------------------------------------------------
def capture(prompt):
    """Capture one operator-pressure record. Returns the endpoint response."""
    raw = world_state_raw()                                      # request-time snapshot FIRST
    captured_at = datetime.datetime.utcnow().isoformat() + "Z"   # focus AT the prompt
    compiled_graph, outcome = _chat(prompt)                      # seconds; focus may drift after
    result = _post_capture({
        "captured_at": captured_at,
        "prompt": prompt,
        "compiled_graph": compiled_graph,
        "outcome": outcome,
        "world_state_raw": raw,
        "provenance": _PROVENANCE,
    })
    ok = isinstance(result, dict) and result.get("data", {}).get("appended") is True
    print("[context-capture] %s | outcome=%s | steps=%d | %s"
          % ("OK" if ok else "FAIL", outcome, len(compiled_graph),
             result if not ok else result["data"]["path"]))
    return result


def ask():
    """Convenience: prompt for the text in a dialog, then capture."""
    try:
        from PySide6 import QtWidgets
    except Exception:
        from PySide2 import QtWidgets
    text, okp = QtWidgets.QInputDialog.getText(None, "Context Pressure Capture", "Prompt:")
    if okp and text and text.strip():
        return capture(text.strip())
    print("[context-capture] cancelled")


print("Context Pressure capture ready. Call:  capture(\"<prompt>\")  or  ask()")
