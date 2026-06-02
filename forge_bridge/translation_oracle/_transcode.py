"""TF.3a Step 4 — transcode seed-32 comprehension traces into ObservedTraces.

Item 5 (transcode, don't couple): a comprehension record is *imported and
transcoded* into a translation_oracle ``ObservedTrace`` with
``capture_provenance="seed-legibility"`` — NOT joined to ``comprehension/
_schema``. The seed contributes data lineage, not a schema dependency. Seed
traces are sparse by nature: the legibility-grain capture never recorded the
Tier-1 runtime markers (`tool_forced`, `tools_filtered`, the fine `:407`
abort), so a transcoded trace can feed Tier-2 value-comparison + expected-graph
authoring but CANNOT fill a Tier-1 coverage cell (the `_corpus` guard enforces
this — a seed-legibility trace is `tagged` but not `counting` for Tier-1).

What survives the transcode: the step-text graph, the coarse `outcome`
(answered/chain_aborted — an abort happened, but not *why*), and the per-step
params the production partial extractor recovers from the step text.
"""
from __future__ import annotations

from typing import Any, Optional

from forge_bridge.console._param_extract import extract_explicit_params


class TranscodeError(ValueError):
    """Raised when a comprehension record is too malformed to transcode."""


def _first_tool(steps: list[str]) -> Optional[str]:
    if not steps:
        return None
    head = steps[0].strip()
    return head.split(maxsplit=1)[0] if head else None


def transcode_comprehension_record(record: Any) -> dict:
    """Map one comprehension record to a seed-legibility ObservedTrace dict.

    Raises ``TranscodeError`` for the malformed records (null question / no
    chain) the batch caller should filter out (4 of the 36 seed traces).
    """
    if not isinstance(record, dict):
        raise TranscodeError(f"record must be a dict, got {type(record).__name__}")
    if record.get("question") is None:
        raise TranscodeError("record.question is null (malformed seed trace)")
    chain = record.get("chain")
    if not isinstance(chain, list):
        raise TranscodeError("record.chain must be a list")

    steps = [entry.get("step", "") for entry in chain if isinstance(entry, dict)]
    return {
        "capture_provenance": "seed-legibility",
        "observed_graph": steps,
        "observed_resolved_params": {
            str(i): extract_explicit_params(step) for i, step in enumerate(steps)
        },
        # coarse signal only — an abort is visible, the fine :407 reason is not.
        "outcome": record.get("outcome"),
        # the legibility capture never recorded these; absent, not False-meaning.
        "tool_forced": False,
        "tools_filtered": None,
        "abort_reason": None,
        "tool_selected": _first_tool(steps),
    }
