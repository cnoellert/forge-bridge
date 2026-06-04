"""TF.4 Slice #3 deterministic trailing-empty-segment recovery bar."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge_bridge.llm.router import (
    CompileInvalidChainShape,
    _parse_compile_output,
    normalize_chain_shape,
)
from forge_bridge.translation_oracle._detect import compute_well_formed


def _tool(name: str):
    return SimpleNamespace(name=name, description=f"{name} description")


def _slice2_list_projects_raws() -> list[str]:
    raws: list[str] = []
    root = (
        Path(__file__).parents[2]
        / "forge_bridge"
        / "translation_oracle"
        / "reference"
    )
    for run in ("run1", "run2", "run3"):
        path = root / f"postgate-slice2-{run}" / "cases.jsonl"
        rows = [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip() and not json.loads(line).get("_header")
        ]
        row = next(
            case
            for case in rows
            if case["label"]["input"] == "list the projects"
        )
        raws.append(row["observed"]["compile_raw"])
    return raws


def _parse_and_normalize(raw: str) -> tuple[list[str], dict | None]:
    parsed = _parse_compile_output(raw, tools=[_tool("forge_list_projects")])
    return normalize_chain_shape(parsed)


def test_tf4_slice3_replays_slice2_raws_to_observable_trailing_salvage():
    raws = _slice2_list_projects_raws()

    assert raws == [
        "forge_list_projects ->",
        "forge_list_projects ->",
        "forge_list_projects ->",
    ]
    for raw in raws:
        steps, salvage = _parse_and_normalize(raw)
        well_formed, reason = compute_well_formed(steps)

        assert steps == ["forge_list_projects"]
        assert salvage == {
            "salvage_applied": True,
            "original_reason": "trailing_empty_segment",
        }
        assert well_formed is True
        assert reason is None


def test_tf4_slice3_production_conformance_matrix():
    steps, salvage = normalize_chain_shape(["forge_list_projects", ""])
    assert steps == ["forge_list_projects"]
    assert salvage == {
        "salvage_applied": True,
        "original_reason": "trailing_empty_segment",
    }

    with pytest.raises(CompileInvalidChainShape):
        normalize_chain_shape(["a_tool", "", "b_tool"])

    steps, salvage = normalize_chain_shape(["a_tool", "b_tool"])
    assert steps == ["a_tool", "b_tool"]
    assert salvage is None

    with pytest.raises(CompileInvalidChainShape):
        normalize_chain_shape(['{"params": {"project": "all"}}'])


def test_tf4_slice3_production_multi_salvage_is_attribution_complete():
    parsed = _parse_compile_output(
        'flame_rename_shots -> {"params": {"sequence_name": "30sec_21"}} ->',
        tools=[_tool("flame_rename_shots")],
    )
    steps, salvage = normalize_chain_shape(parsed)

    assert steps == [
        'flame_rename_shots {"params": {"sequence_name": "30sec_21"}}'
    ]
    assert salvage == {
        "salvage_applied": True,
        "original_reason": "detached_args+trailing_empty_segment",
    }
