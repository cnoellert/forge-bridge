"""Observed-sourced verdict emission for the translation oracle.

``emit`` is the TF.3b boundary: labels calibrate the oracle, but the core
verdict comes from the observed trace. Content scoring is the only label-gated
axis because it needs canonical expected parameters.
"""
from __future__ import annotations

from typing import Optional

from forge_bridge.translation_oracle._detect import detect_entity_value_fidelity

_SUBSTRATE_PASS_OUTCOMES = frozenset({None, "answered", "preview_emitted", "apply_complete"})
_VERDICT_PAIR_KEYS = ("pass/pass", "fail/pass", "pass/gap", "fail/gap")


def _substrate_verdict(observed: dict) -> str:
    outcome = observed.get("outcome")
    abort_reason = observed.get("abort_reason")
    if abort_reason is not None:
        return "gap"
    if outcome in _SUBSTRATE_PASS_OUTCOMES:
        return "pass"
    return "gap"


def emit(observed: dict, *, label: Optional[dict] = None) -> dict:
    """Emit an observed-sourced verdict pair.

    Malformed graphs fail translation before content scoring. Well-formed,
    label-free traces emit only the core well-formedness/substrate verdict; the
    content axis is intentionally unscored without canonical label params.
    """
    substrate = _substrate_verdict(observed)

    if observed.get("well_formed") is False:
        return {"translation": "fail", "substrate": substrate}

    if label is None:
        return {"translation": "pass", "substrate": substrate}

    faithful, _reason = detect_entity_value_fidelity(
        observed.get("observed_graph") or [],
        label.get("expected_params") or {},
    )
    return {
        "translation": "pass" if faithful else "fail",
        "substrate": substrate,
    }


def verdict_frequency(cases: list[dict]) -> dict:
    """Count observed-sourced verdict-pair emissions for labeled cases.

    This is a manifestation-frequency reader, not a validation-set coverage
    reader: it scores each observed trace through ``emit`` and leaves the
    label-sourced coverage dimensions in ``coverage_report`` alone.
    """
    counts = {key: 0 for key in _VERDICT_PAIR_KEYS}
    labeled_count = 0
    for case in cases:
        label = case.get("label")
        if label is None:
            continue
        labeled_count += 1
        verdict = emit(case["observed"], label=label)
        key = f"{verdict['translation']}/{verdict['substrate']}"
        counts[key] += 1
    return {"labeled_count": labeled_count, "verdict_pairs": counts}
