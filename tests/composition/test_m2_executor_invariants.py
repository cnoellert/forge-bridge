from __future__ import annotations

from pathlib import Path


def test_graph_executor_has_no_assent_conduit():
    executor_source = (
        Path(__file__).parents[2] / "forge_bridge" / "composition" / "executor.py"
    ).read_text()

    forbidden = ("AssentRecord", "assent_record", "ratified", "ratification")
    for token in forbidden:
        assert token not in executor_source

