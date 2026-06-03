"""TF.3a Step 4 — the authored reference cases (operator-ratified ground truth).

This is the committed ground-truth LABEL set (TF.2-LABELS-DRAFT.md, ratified
2026-06-02). Each case pairs an authored Label with a capture `source`:
  - "seed": the ObservedTrace is transcoded from a matching comprehension
    trace (seed-legibility) — no live model needed.
  - "live": the ObservedTrace is captured by running the input through the real
    compile path (instrumented-translation) — needs Ollama (qwen2.5-coder:14b).

The Label is authored; the ObservedTrace is paired at build time
(`run_captures.py`). Reviewable on purpose — correct the labels here, not in a
hand-edited JSONL.
"""
from __future__ import annotations

from typing import Any, Optional


def _case(
    cid: str,
    user_input: str,
    source: str,
    *,
    graph: list[str],
    params: dict,
    verdict: tuple[str, str],
    classes: list[str],
    world_state: Optional[dict] = None,
    defect_ref: Optional[str] = None,
    provenance: Optional[dict] = None,
) -> dict[str, Any]:
    return {
        "id": cid,
        "source": source,
        "input": user_input,
        "label": {
            "input": user_input,
            "expected_graph": graph,
            "expected_params": params,
            "expected_verdict_pair": {"translation": verdict[0], "substrate": verdict[1]},
            "expected_classes": classes,
            "world_state": world_state,
            "defect_ref": defect_ref,
            "expected_provenance": provenance or {},
        },
    }


AUTHORED_CASES: list[dict[str, Any]] = [
    # ---- clean reads — cell (a), seed-usable ----
    _case("A1.1", "What batch groups are on the desktop", "seed",
          graph=["flame_list_batch_groups {}"], params={}, verdict=("pass", "pass"), classes=[]),
    _case("A1.2", "What is the name of the current desktop", "seed",
          graph=["flame_list_desktop {}"], params={}, verdict=("pass", "pass"), classes=[]),

    # ---- routing / wrong-selection — cell (b), seed-usable (observed wrong tool) ----
    _case("A1.3", "What reels are on the desktop", "seed",
          graph=["flame_list_reel_groups {}"], params={}, verdict=("fail", "pass"), classes=["routing"]),
    _case("A1.4", "What is the name of the current reels group", "seed",
          graph=["flame_list_reel_groups {}"], params={}, verdict=("fail", "pass"), classes=["routing"]),

    # ---- routing failures — cell (b), live ----
    _case("L1", "list the projects", "live",
          graph=["forge_list_projects {}"], params={}, verdict=("fail", "pass"), classes=["routing"]),
    _case("L2", "What's the duration in frames of 30sec_edit 21", "live",
          graph=['flame_get_sequence_segments sequence_name="30sec_edit 21"'],
          params={"sequence_name": "30sec_edit 21"}, verdict=("fail", "pass"),
          classes=["routing", "entity-resolution"]),
    _case("L3", "What is the path to shot 10 on 30sec_edit 21?", "live",
          graph=['flame_get_sequence_segments sequence_name="30sec_edit 21"'],
          params={"sequence_name": "30sec_edit 21"}, verdict=("fail", "pass"),
          classes=["routing", "entity-resolution"]),
    _case("L4", "What's the duration of shot 10 on 30sec_edit 21?", "live",
          graph=['flame_get_sequence_segments sequence_name="30sec_edit 21"'],
          params={"sequence_name": "30sec_edit 21"}, verdict=("fail", "pass"),
          classes=["routing", "entity-resolution"]),
    _case("L5", "What iteration is gen_0460 on?", "live",
          graph=['flame_open_batch_group batch_group_name="gen_0460"', "flame_get_batch_iterations {}"],
          params={"batch_group_name": "gen_0460"}, verdict=("fail", "pass"),
          classes=["routing", "entity-resolution"]),

    # ---- grounding / example-salience — cell (b), live ----
    _case("L6", "rename the shots on 30sec_21 with prefix tv", "live",
          graph=['flame_rename_shots sequence_name="30sec_21" prefix="tv"'],
          params={"sequence_name": "30sec_21", "prefix": "tv"}, verdict=("fail", "pass"),
          classes=["grounding"], defect_ref="defect-1",
          provenance={"sequence_name": "grounded-from-intent", "prefix": "grounded-from-intent"}),
    _case("L9", "set the start frames on 30sec_edit 21", "live",
          # correct behavior = honest decline (no frame value given); the defect is
          # default_frame lifted from the `e.g. 1001` docstring (TF.1-CONTRACT §5).
          graph=[], params={}, verdict=("fail", "pass"), classes=["grounding"],
          defect_ref="defect-1b", provenance={"default_frame": "unresolved"}),

    # ---- routing + extraction (multi-tag) — cell (b), live ----
    _case("L7", "rename shots on 30sec_edit 21 prefix noise", "live",
          graph=['flame_rename_shots sequence_name="30sec_edit 21" prefix="noise"'],
          params={"sequence_name": "30sec_edit 21", "prefix": "noise"}, verdict=("fail", "pass"),
          classes=["routing", "extraction"], defect_ref="defect-2"),

    # ---- contextual — cell (b), live (needs desktop world_state) ----
    _case("L8", "rename this sequence with prefix tv", "live",
          graph=['flame_rename_shots sequence_name="unresolved-pending-dispatch" prefix="tv"'],
          params={"sequence_name": "unresolved-pending-dispatch", "prefix": "tv"},
          verdict=("fail", "pass"), classes=["contextual"], defect_ref="defect-3",
          world_state={"open_sequence": "30sec_edit 21"},
          provenance={"sequence_name": "unresolved", "prefix": "grounded-from-intent"}),

    # ---- honest decline (R9 capability gap) — cell (c) REWARDED, live confirms the decline ----
    _case("L10", "Does shot 10 on 30sec_edit 21 have a timewarp?", "live",
          graph=[], params={}, verdict=("pass", "gap"), classes=[]),

    # ---- correct read that aborted (D2) — cell (a), live confirms ----
    _case("L11", "What is the name of the current batch", "live",
          graph=["flame_list_batch_groups {}"], params={}, verdict=("pass", "pass"), classes=[]),
]
