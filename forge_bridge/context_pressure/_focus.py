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

This is load-bearing, not hygiene: S4's ``wrong_referent`` detector compares a
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
    """Normalize a stringified Flame scalar into its bare semantic value.

    Two real Flame representations are stripped (idempotent — a clean value
    passes through unchanged):
      - a leading ``PyAttribute:`` wrapper (probe-_safe form), and
      - a BALANCED SURROUNDING QUOTE PAIR: live ``str(PyAttribute)`` wraps the
        value in single quotes — ``str(clip.name) -> "'30sec_edit 21'"`` (probe #4
        live finding). The compiled-graph side is quote-stripped by the param
        parser, so extracted must be too or a genuine match compares UNEQUAL and
        S4 false-positives ``wrong_referent`` on correct records.
    This is what keeps both wrappers out of ``extracted`` (and out of S4's
    comparison); ``raw`` retains the faithful quoted form for recoverability.
    """
    if not isinstance(value, str):
        return value
    v = value
    if v.startswith(_PYATTR_PREFIX):
        v = v[len(_PYATTR_PREFIX):]
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        v = v[1:-1]
    return v


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
    put("current_segment_name", timeline.get("current_segment_name"))

    # typed selection (probe #5b): pulled per-context via get_value() — the old
    # bool(seg.selected) segment-walk is ABANDONED (the flag was a truthy-for-all
    # PyAttribute, so the walk captured EVERY segment, not the selected set). This
    # is the REFERENTIAL signal (selected typed object), primary over the
    # loaded/playhead signals above (which remain as fallback). Names are
    # unwrapped; the source context is tagged. S4 matches the dimension's
    # selection_type against the captured ``type``.
    combined: list = []
    for ctx in ("media_panel", "timeline", "batch"):
        for it in ((raw.get(ctx) or {}).get("selected") or []):
            if not isinstance(it, dict):
                continue
            name = _unwrap(it["name"]) if it.get("name") is not None else None
            shot = _unwrap(it["shot_name"]) if it.get("shot_name") is not None else None
            if not name and not shot:
                continue
            combined.append({"type": it.get("type"), "name": name,
                             "shot_name": shot, "context": ctx})
    if combined:
        extracted[f"{source}.selected"] = combined

    return {"source": source, "raw": raw, "extracted": extracted}


# --- S2 LIVE read (Flame-gated; workstation-validated, NOT dev-box tested) ----
# Runs inside Flame (SGTK Python Console / bridge.execute). Implements the
# FOCUS-STATE-DISPOSITION recipe; reachability proven by probes #1-#3, typed
# context-scoped selection via .get_value() proven by probe #5b. Stores
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

def _selected(attr):
    # PROBE #5b: Flame SELECTION attributes (media_panel.selected_entries,
    # clip.selected_segments, batch.selected_nodes) are PyAttribute wrappers.
    # The wrapper is NOT opaque: every container path (len/subscript/list()/
    # iterate) raises TypeError, but .get_value() returns the real list of
    # selected objects. (The old bool(seg.selected) segment-walk was a
    # truthy-for-all PyAttribute flag — it captured EVERY segment, not the
    # selection — and is abandoned.) Capture type + name + shot_name faithfully;
    # assemble_world_state() unwraps. isinstance is the clean discriminator
    # downstream; here we record type(it).__name__ verbatim.
    if attr is None:
        return None
    try:
        items = attr.get_value()
    except Exception:
        try:
            items = list(attr)   # media_panel.selected_entries is directly iterable
        except Exception:
            return None
    out = []
    for it in (items or []):
        try:
            out.append({
                "type": type(it).__name__,
                "name": _v(getattr(it, "name", None)),
                "shot_name": _v(getattr(it, "shot_name", None)),
            })
        except Exception:
            pass
    return out

proj = flame.projects.current_project
batch = flame.batch
tl = flame.timeline
mp = getattr(flame, "media_panel", None)
clip = getattr(tl, "clip", None)
cur = getattr(tl, "current_segment", None)

raw = {
    "project": _v(proj.project_name),
    "current_tab": _v(flame.get_current_tab()),
    "media_panel": {
        "selected": _selected(getattr(mp, "selected_entries", None)) if mp is not None else None,
    },
    "batch": {
        "name": _v(batch.name),
        "opened": bool(batch.opened),
        "current_iteration": _v(getattr(batch, "current_iteration", None) and batch.current_iteration.name),
        "selected": _selected(getattr(batch, "selected_nodes", None)),
    },
    "timeline": {
        "active_sequence": _v(getattr(clip, "name", None)) if clip is not None else None,
        "current_shot": _v(getattr(cur, "shot_name", None)) if cur else None,
        "current_segment_name": _v(getattr(cur, "name", None)) if cur else None,
        "selected": _selected(getattr(clip, "selected_segments", None)) if clip is not None else None,
    },
    "playhead_frame": None,          # unreachable_api (no current_frame on PyTimeline)
    "playhead_frame_reason": "unreachable_api",
}
print(json.dumps(raw))
'''
