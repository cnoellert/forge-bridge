"""Context Pressure Instrument — S2 focus-state snapshot (Flame).

S2 establishes SEMANTIC INTEGRITY between S1 (capture) and S4 (analysis). The
invariant (DT + Creative):

    RAW PRESERVES PROVENANCE; EXTRACTED PRESERVES MEANING.

For every Flame signal:
  - ``world_state.raw`` retains the faithful, recoverable representation the
    Flame read produced (the migration-if-wrong surface — a missing raw signal
    is unrecoverable; an extracted mistake is free to re-derive).
  - ``world_state.extracted`` holds the NORMALIZED semantic value, with any
    ``PyAttribute`` wrapper removed.

This is load-bearing, not hygiene: S4's ``wrong_resolution`` detector compares a
compiled concrete value against ``extracted[...]``. If a ``PyAttribute:30sec_edit 21``
wrapper string leaks into ``extracted``, every compiled value mismatches it and
S4 floods the corpus with false-positive failures — deterministically, with all
tests green. So ``assemble_world_state`` GUARANTEES unwrapped values in
``extracted`` regardless of whether ``raw`` carried a wrapper form.

Split for testability: the in-Flame read (``FOCUS_SNAPSHOT_PY``, workstation-
gated) produces ``raw``; ``assemble_world_state`` (dev-box, fully tested against
the probe fixtures) projects ``raw`` → ``extracted``.
"""
from __future__ import annotations

from typing import Any, Final

_PYATTR_PREFIX: Final[str] = "PyAttribute:"

# The one Tier-C signal Flame does not expose on demand (probe #2/#3): the
# numeric playhead frame. Recorded as absent-with-reason, never silently dropped.
UNREACHABLE_API: Final[str] = "unreachable_api"


def _unwrap(value: Any) -> Any:
    """Strip a leading ``PyAttribute:`` wrapper from a stringified Flame scalar.

    Idempotent: a clean value passes through unchanged. This is what keeps the
    wrapper out of ``extracted`` (and thus out of S4's comparison).
    """
    if isinstance(value, str) and value.startswith(_PYATTR_PREFIX):
        return value[len(_PYATTR_PREFIX):]
    return value


def assemble_world_state(raw: dict, *, source: str = "flame") -> dict:
    """Project a raw Flame focus snapshot into a ``world_state`` payload.

    Returns ``{source, raw, extracted}``: ``raw`` is preserved verbatim;
    ``extracted`` is the source-namespaced, PyAttribute-unwrapped semantic
    projection (the analysis surface S4 reads). Pure function of ``raw`` —
    ``extracted`` is always re-derivable; ``raw`` is not re-derivable from
    ``extracted`` (it carries strictly more).
    """
    extracted: dict = {}

    def put(key: str, value: Any) -> None:
        if value is None:
            return
        extracted[f"{source}.{key}"] = _unwrap(value)

    put("project", raw.get("project"))
    put("current_tab", raw.get("current_tab"))

    batch = raw.get("batch") or {}
    if batch.get("opened"):
        put("open_batch", batch.get("name"))

    timeline = raw.get("timeline") or {}
    put("active_sequence", timeline.get("active_sequence"))
    put("current_shot", timeline.get("current_shot"))

    selection = timeline.get("selection") or []
    shots = [_unwrap(s) for s in selection if s is not None]
    if shots:
        extracted[f"{source}.selection"] = shots

    return {"source": source, "raw": raw, "extracted": extracted}


# --- S2 LIVE read (Flame-gated; workstation-validated, NOT dev-box tested) ----
# Runs inside Flame (SGTK Python Console / bridge.execute). Implements the
# FOCUS-STATE-DISPOSITION recipe; reachability proven by probes #1-#3. Stores
# faithful values in `raw`; `assemble_world_state` does the unwrap into
# `extracted`. The numeric playhead frame is recorded null/unreachable_api.
FOCUS_SNAPSHOT_PY: Final[str] = '''
import flame, json

def _v(attr):
    # Faithful scalar render for `raw` — str() of a PyAttribute is its value;
    # None stays None. assemble_world_state() normalizes downstream.
    try:
        return None if attr is None else str(attr)
    except Exception:
        return None

def _names(attr):
    # LIVE FINDING (probe #4): Flame SELECTION attributes (batch.selected_nodes,
    # clip.selected_segments) are PyAttribute value-wrappers, NOT iterable
    # containers — list()/for raises TypeError (unlike versions/tracks/segments,
    # which DO iterate). Best-effort; non-critical (the assembler does not extract
    # selected_nodes; timeline selection comes from the segment walk below).
    try:
        return [_v(getattr(n, "name", n)) for n in list(attr)]
    except Exception:
        return None

proj = flame.projects.current_project
batch = flame.batch
tl = flame.timeline

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

cur = getattr(tl, "current_segment", None)
raw = {
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
    "playhead_frame": None,          # unreachable_api (no current_frame on PyTimeline)
    "playhead_frame_reason": "unreachable_api",
}
print(json.dumps(raw))
'''
