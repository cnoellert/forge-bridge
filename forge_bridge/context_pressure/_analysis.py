"""Context Pressure Instrument — S4 counterfactual analysis (dual-mode).

The phase-defining step. A contextual resolver fails TWO ways, and an analyzer
that sees only the first systematically under-counts the dominant, most-dangerous
failures and biases the build/don't-build ruling toward *don't-build* (it omits
exactly what desktop-wiring would fix). So the failure set is dual-mode:

  (a) unresolved_reference — "this sequence" -> no concrete value (honest-decline).
      Derivable from the captured compiled_graph (no resolved value for the
      referenced dimension).
  (b) wrong_referent — "this sequence" -> resolved to a WRONG concrete value,
      dispatched as if grounded (the IDX-13 case: focus=30sec_edit 21, compiled
      sequence_name=30sec_21; the TF.4 space-mangle class). Candidate ⇔ the
      compiled value != the captured world_state focus signal.

The captured/authored lock holds across the seam:
  - CANDIDATE-FLAGGING is automatic and captured-derivable (``flag_contextual_
    failure_candidates``) — it only ever says "this looks suspicious".
  - CONFIRMATION is AUTHORED (``author_analysis`` writes the analysis layer with
    authored_at) — only authored analysis says "this WAS wrong" and decides
    world_state_resolvable.

``resolvable_delta`` is computed over the UNION of both confirmed classes — the
metric that drives the build/don't-build decision.

The dimension map is the measure-first seam: it starts small and grows additively
as real captures show which contextual dimensions matter.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

# Committed seed corpus (authored ground truth exercising BOTH failure modes,
# incl. the IDX-13 mode-(b) case) — the CR.1-fix gate: the analysis loop is
# proven closed on a seed before real operator data arrives.
SEED_DIR: Final[Path] = Path(__file__).resolve().parent / "seed"

# Deictic / contextual-reference tokens that trigger candidate analysis. A prompt
# without one of these makes no contextual claim, so it is never a candidate.
_CONTEXTUAL_TOKENS: Final[frozenset[str]] = frozenset({
    "this", "that", "these", "those", "current", "selected", "active", "here",
})

# Seed-minimal placeholder sentinels (measure-first — observed forms only; do NOT
# pre-lock a taxonomy: over-broad matching mis-classifies real values as unresolved).
_PLACEHOLDER_EXACT: Final[frozenset[str]] = frozenset({"UUID"})
_PLACEHOLDER_RE: Final = re.compile(r"^<.*>$")


@dataclass(frozen=True)
class _Dimension:
    name: str
    nouns: frozenset       # prompt nouns that invoke this dimension
    param_keys: tuple      # compiled-graph param keys carrying its concrete value
    focus_keys: tuple      # loaded/playhead fallback signals (priority-ordered)
    selection_type: Optional[str] = None  # flame Py* type of the selected REFERENT (primary)


# Measure-first seam — extend as captures show which dimensions matter.
# selection_type is the REFERENTIAL signal (the selected typed object, probe #5b),
# checked PRIMARY; focus_keys are the loaded/playhead FALLBACK. The hooks key off
# typed selection (forge_rename -> selected flame.PySequence), so the referent for
# "this sequence" is the selected PySequence, not the loaded active_sequence.
_DIMENSIONS: Final[tuple] = (
    _Dimension("sequence", frozenset({"sequence", "seq", "timeline"}),
               ("sequence_name", "sequence"), ("active_sequence",),
               selection_type="PySequence"),
    # current_segment_name is a fallback focus signal on the shot dimension, not
    # a new dimension. shot.focus_keys = ("current_shot", "current_segment_name"),
    # first non-empty wins. selection_type=PySegment is the selected-segment
    # referent (primary). Revisit only if a capture shows an operator expressing
    # segment != shot as distinct referents in one world_state.
    _Dimension("shot", frozenset({"shot", "segment"}),
               ("shot", "shot_name", "shot_id", "segment_name", "segment"),
               ("current_shot", "current_segment_name"),
               selection_type="PySegment"),
    # batch dimension keys off the loaded open_batch (no selected-node referent
    # yet — batch-node ops are not in the failure corpus; add a selected
    # PyClipNode/PyOFXNode/PyWriteFileNode dimension when one appears).
    _Dimension("batch", frozenset({"batch"}),
               ("batch", "batch_name"), ("open_batch",)),
)


def _has_contextual_ref(prompt: str) -> bool:
    return bool(set(re.findall(r"[a-z]+", prompt.lower())) & _CONTEXTUAL_TOKENS)


def _graph_params(compiled_graph: list) -> dict:
    """Collect key=value params across all steps (first value wins per key)."""
    params: dict = {}
    for step in compiled_graph:
        try:
            tokens = shlex.split(str(step))
        except ValueError:
            tokens = str(step).split()
        for tok in tokens:
            if "=" not in tok:
                continue
            key, value = tok.split("=", 1)
            params.setdefault(key.strip(), value.strip().strip("\"'"))
    return params


def _is_placeholder(value: str) -> bool:
    return value in _PLACEHOLDER_EXACT or bool(_PLACEHOLDER_RE.match(value))


def _focus_value(world_state: dict, focus_keys: tuple) -> Optional[str]:
    """First present, non-empty focus signal across priority-ordered keys."""
    extracted = world_state.get("extracted") or {}
    source = world_state.get("source")
    for focus_signal_key in focus_keys:
        for key in (f"{source}.{focus_signal_key}", focus_signal_key):
            val = extracted.get(key)
            if val is not None and str(val) != "":
                return str(val)
    return None


def _selected_value(world_state: dict, selection_type: Optional[str]) -> Optional[str]:
    """The selected typed object's name — the REFERENTIAL signal (probe #5b),
    checked PRIMARY over the loaded/playhead focus. Matches the dimension's flame
    Py* ``selection_type`` against the captured ``type`` tag; returns shot_name or
    name (first non-empty)."""
    if not selection_type:
        return None
    extracted = world_state.get("extracted") or {}
    source = world_state.get("source")
    for key in (f"{source}.selected", "selected"):
        for item in (extracted.get(key) or []):
            if isinstance(item, dict) and item.get("type") == selection_type:
                nm = item.get("shot_name") or item.get("name")
                if nm is not None and str(nm) != "":
                    return str(nm)
    return None


def flag_contextual_failure_candidates(record: dict) -> list[dict]:
    """AUTO candidate-flagging over CAPTURED fields only — dual-mode, no authoring.

    Returns a list of candidate dicts (possibly empty). Each candidate:
    ``{mode, dimension, compiled_value, focus_value, focus_signal_present,
    focus_source}`` where ``mode`` ∈ {``unresolved_reference``,
    ``wrong_referent``} and ``focus_source`` ∈ {``selected``, ``loaded``,
    ``None``} records WHICH signal won (referential selected-typed vs the
    loaded/playhead fallback). This only ever says "suspicious";
    ``author_analysis`` confirms.
    """
    prompt = record.get("prompt", "") or ""
    if not _has_contextual_ref(prompt):
        return []
    plow = prompt.lower()
    params = _graph_params((record.get("observed_translation") or {}).get("compiled_graph") or [])
    world_state = record.get("world_state") or {}

    candidates: list[dict] = []
    for dim in _DIMENSIONS:
        if not any(noun in plow for noun in dim.nouns):
            continue
        # selected typed object (referential) is PRIMARY; loaded/playhead fallback.
        focus = _selected_value(world_state, dim.selection_type)
        focus_source = "selected" if focus is not None else None
        if focus is None:
            focus = _focus_value(world_state, dim.focus_keys)
            focus_source = "loaded" if focus is not None else None
        compiled = next((params[k] for k in dim.param_keys if k in params), None)
        if compiled is not None and _is_placeholder(compiled):
            compiled = None

        if compiled is None:
            # (a) unresolved: a contextual ref to this dimension, no concrete value.
            candidates.append({
                "mode": "unresolved_reference",
                "dimension": dim.name,
                "compiled_value": None,
                "focus_value": focus,
                "focus_signal_present": focus is not None,
                "focus_source": focus_source,
            })
        elif focus is not None and compiled != focus:
            # (b) wrong_referent: resolved to a value that differs from focus.
            candidates.append({
                "mode": "wrong_referent",
                "dimension": dim.name,
                "compiled_value": compiled,
                "focus_value": focus,
                "focus_signal_present": True,
                "focus_source": focus_source,
            })
        # else: compiled present and == focus (correct), or no focus to compare
        # against (unanalyzable — left for authored review, not auto-flagged).
    return candidates


def author_analysis(
    record: dict,
    *,
    authored_at: str,
    failure_class: Optional[str] = None,
    referent: Optional[str] = None,
    world_state_resolvable: Optional[bool] = None,
    resolving_signal: Optional[str] = None,
) -> dict:
    """The distinct AUTHORING pass — returns a NEW record with ``analysis`` set.

    Crosses the captured/authored seam by hand: the author supplies ``referent``
    and ``world_state_resolvable`` as judgement; observed context is NOT copied
    in automatically. Does not mutate the input. Validated before return.
    """
    from forge_bridge.context_pressure._schema import validate_context_pressure_record

    authored = dict(record)
    authored["analysis"] = {
        "authored_at": authored_at,
        "failure_class": failure_class,
        "referent": referent,
        "world_state_resolvable": world_state_resolvable,
        "resolving_signal": resolving_signal,
    }
    validate_context_pressure_record(authored)
    return authored


def resolvable_delta(records: list[dict]) -> dict:
    """The decision metric over the UNION of both confirmed failure classes.

    A confirmed contextual failure = a record whose authored ``analysis`` carries
    a ``failure_class``. Of those, how many would the captured world_state have
    resolved (``world_state_resolvable is True``)? Ranked by ``resolving_signal``.
    Computes over BOTH modes — never just unresolved refs.
    """
    failures = [
        r for r in records
        if (r.get("analysis") or {}).get("failure_class") is not None
    ]
    resolvable = [
        r for r in failures
        if r["analysis"].get("world_state_resolvable") is True
    ]
    by_failure_class: dict = {}
    for r in failures:
        fc = r["analysis"]["failure_class"]
        by_failure_class[fc] = by_failure_class.get(fc, 0) + 1
    signal_rank: dict = {}
    for r in resolvable:
        sig = r["analysis"].get("resolving_signal") or "unspecified"
        signal_rank[sig] = signal_rank.get(sig, 0) + 1
    total = len(failures)
    return {
        "total_contextual_failures": total,
        "world_state_resolvable_count": len(resolvable),
        "resolvable_rate": (len(resolvable) / total) if total else 0.0,
        "by_failure_class": by_failure_class,
        "resolving_signal_ranking": dict(
            sorted(signal_rank.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
    }
