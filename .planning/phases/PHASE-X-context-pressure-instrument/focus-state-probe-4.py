# Probe #4 — Live Flame -> Assembler -> S4 CONTRACT VERIFICATION (Phase X / S2 close)
#
# NOT a raw dump. This proves the PRODUCTION Flame shape satisfies the S2->S4
# contract: live FOCUS_SNAPSHOT_PY (str()-rendered) -> assemble_world_state ->
# clean extracted -> S4 flags a real mismatch and does NOT false-positive a match.
# The dev-box fixtures used probe-_safe ("PyAttribute:...") shape; the live read
# renders via str() (clean). This is the first test of the real shape against the
# assembler (fixture-mirrors-production gap).
#
# WHERE: SGTK Python Console (Flame's python). It tries to import the REAL
# forge_bridge functions; if Flame's python can't see them, it falls back to
# VERBATIM inlined copies and says so.
#
# SETUP: load a sequence in Timeline; select 2-3 segments; ensure a current
# segment; (optional) open a batch with a selected node. Then paste + run.
# SAFE: read-only.

import flame
import json
from collections import namedtuple

# ============================ 0. LIVE FLAME READ ============================
def _v(attr):
    try:
        return None if attr is None else str(attr)
    except Exception:
        return None

def _names(attr):
    # LIVE FINDING (probe #4): Flame selection attrs are PyAttribute value-wrappers,
    # NOT iterable — list()/for raises TypeError. Best-effort, non-critical.
    try:
        return [_v(getattr(n, "name", n)) for n in list(attr)]
    except Exception:
        return None

def _diag(attr):
    """Discover an attribute's real shape: type, str-repr, iterability."""
    try:
        iterable = True
        try:
            list(attr)
        except TypeError:
            iterable = False
        return {"type": type(attr).__name__, "str": _v(attr), "iterable": iterable}
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e)}

def _live_raw():
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
        "workspace": _v(proj.current_workspace),
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

# ===================== 1. REAL forge_bridge OR INLINED ======================
_SOURCE = None
try:
    from forge_bridge.context_pressure import assemble_world_state, flag_contextual_failure_candidates
    _SOURCE = "REAL forge_bridge (importable in Flame python)"
except Exception:
    _SOURCE = "INLINED verbatim copies (forge_bridge not importable in Flame python)"
    import re, shlex
    _PYATTR_PREFIX = "PyAttribute:"

    def _unwrap(value):
        if isinstance(value, str) and value.startswith(_PYATTR_PREFIX):
            return value[len(_PYATTR_PREFIX):]
        return value

    def assemble_world_state(raw, source="flame"):
        extracted = {}
        def put(key, value):
            if value is None:
                return
            extracted["%s.%s" % (source, key)] = _unwrap(value)
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
            extracted["%s.selection" % source] = shots
        return {"source": source, "raw": raw, "extracted": extracted}

    _Dimension = namedtuple("_Dimension", "name nouns param_keys focus_key")
    _CONTEXTUAL_TOKENS = frozenset({"this", "that", "these", "those", "current", "selected", "active", "here"})
    _DIMENSIONS = (
        _Dimension("sequence", frozenset({"sequence", "seq", "timeline"}), ("sequence_name", "sequence"), "active_sequence"),
        _Dimension("shot", frozenset({"shot", "segment"}), ("shot", "shot_name", "segment_name", "segment"), "current_shot"),
        _Dimension("batch", frozenset({"batch"}), ("batch", "batch_name"), "open_batch"),
    )
    def _has_contextual_ref(prompt):
        return bool(set(re.findall(r"[a-z]+", prompt.lower())) & _CONTEXTUAL_TOKENS)
    def _graph_params(compiled_graph):
        params = {}
        for step in compiled_graph:
            try:
                tokens = shlex.split(str(step))
            except ValueError:
                tokens = str(step).split()
            for tok in tokens:
                if "=" not in tok:
                    continue
                k, vv = tok.split("=", 1)
                params.setdefault(k.strip(), vv.strip().strip("\"'"))
        return params
    def _focus_value(world_state, focus_key):
        extracted = world_state.get("extracted") or {}
        source = world_state.get("source")
        for key in ("%s.%s" % (source, focus_key), focus_key):
            if key in extracted and extracted[key] is not None:
                return str(extracted[key])
        return None
    def flag_contextual_failure_candidates(record):
        prompt = record.get("prompt", "") or ""
        if not _has_contextual_ref(prompt):
            return []
        plow = prompt.lower()
        params = _graph_params((record.get("observed_translation") or {}).get("compiled_graph") or [])
        ws = record.get("world_state") or {}
        cands = []
        for dim in _DIMENSIONS:
            if not any(n in plow for n in dim.nouns):
                continue
            focus = _focus_value(ws, dim.focus_key)
            compiled = next((params[k] for k in dim.param_keys if k in params), None)
            if compiled is None:
                cands.append({"mode": "unresolved_reference", "dimension": dim.name,
                              "compiled_value": None, "focus_value": focus,
                              "focus_signal_present": focus is not None})
            elif focus is not None and compiled != focus:
                cands.append({"mode": "wrong_resolution", "dimension": dim.name,
                              "compiled_value": compiled, "focus_value": focus,
                              "focus_signal_present": True})
        return cands

# ============================ 2. RUN THE CHAIN =============================
raw = _live_raw()
ws = assemble_world_state(raw)
extracted = ws["extracted"]
checks = []

def _check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})

# ---- CONTRACT CHECKS ----
extracted_json = json.dumps(extracted)
_check("no PyAttribute: in extracted", "PyAttribute:" not in extracted_json, extracted_json[:200])
_check("active_sequence populated", bool(extracted.get("flame.active_sequence")),
       repr(extracted.get("flame.active_sequence")))
_check("current_shot populated", bool(extracted.get("flame.current_shot")),
       repr(extracted.get("flame.current_shot")))
_sel = extracted.get("flame.selection")
_raw_sel = (raw.get("timeline") or {}).get("selection") or []
_check("selection resolved to names", bool(_sel) and all(isinstance(s, str) and s for s in _sel)
       and len(_sel) == len([s for s in _raw_sel if s]), repr(_sel))
_check("unreachable_api tenant recorded",
       raw.get("playhead_frame") is None and raw.get("playhead_frame_reason") == "unreachable_api")
# extracted scalars consistent with raw-derived values
_consistent = (
    extracted.get("flame.active_sequence") == ((raw.get("timeline") or {}).get("active_sequence") or "").replace("PyAttribute:", "")
    and extracted.get("flame.current_shot") == ((raw.get("timeline") or {}).get("current_shot") or "").replace("PyAttribute:", "")
)
_check("extracted consistent with raw-derived", _consistent)

# ---- S4 COMPATIBILITY (the load-bearing check) ----
seq = extracted.get("flame.active_sequence")
if seq:
    match = {"prompt": "rename this sequence with prefix tv", "world_state": ws,
             "observed_translation": {"compiled_graph": ['flame_rename_shots sequence_name="%s" prefix=tv commit=true' % seq]}}
    mismatch = {"prompt": "rename this sequence with prefix tv", "world_state": ws,
                "observed_translation": {"compiled_graph": ['flame_rename_shots sequence_name="%s_WRONG" prefix=tv commit=true' % seq]}}
    match_cands = flag_contextual_failure_candidates(match)
    mismatch_cands = flag_contextual_failure_candidates(mismatch)
    _check("S4 match-case NOT flagged (no false positive)", match_cands == [], repr(match_cands))
    _check("S4 mismatch-case flagged wrong_resolution",
           [c["mode"] for c in mismatch_cands] == ["wrong_resolution"], repr(mismatch_cands))
else:
    _check("S4 compatibility", False, "SKIPPED — no active_sequence; load a sequence in Timeline and re-run")

# ============================ 3. REPORT =====================================
# ---- shape diagnostics (learn the real PyAttribute selection shapes) ----
shape_diag = {}
try:
    shape_diag["batch.selected_nodes"] = _diag(flame.batch.selected_nodes)
except Exception as e:
    shape_diag["batch.selected_nodes"] = {"error": "%s: %s" % (type(e).__name__, e)}
try:
    shape_diag["clip.selected_segments"] = _diag(getattr(flame.timeline.clip, "selected_segments", None))
except Exception as e:
    shape_diag["clip.selected_segments"] = {"error": "%s: %s" % (type(e).__name__, e)}

verified = all(c["pass"] for c in checks)
report = {
    "probe_version": "4",
    "flame_version": _v(flame.get_version()),
    "assembler_source": _SOURCE,
    "raw_capture": raw,
    "assembled_extracted": extracted,
    "shape_diagnostics": shape_diag,
    "contract_checks": checks,
    "verdict": "CONTRACT VERIFIED" if verified else "CONTRACT FAILURE",
}
print("\n========== PROBE #4 RESULT (copy everything below) ==========\n")
print(json.dumps(report, indent=2, default=str))
print("\nPROBE #4 RESULT:", report["verdict"])
if not verified:
    print("FAILING CHECKS:", [c["check"] for c in checks if not c["pass"]])
print("\n========== END PROBE #4 RESULT ==========\n")
