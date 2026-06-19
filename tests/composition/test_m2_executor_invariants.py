from __future__ import annotations

import subprocess
from pathlib import Path


def test_graph_executor_has_no_assent_conduit():
    executor_source = (
        Path(__file__).parents[2] / "forge_bridge" / "composition" / "executor.py"
    ).read_text()

    forbidden = ("AssentRecord", "assent_record", "ratified", "ratification")
    for token in forbidden:
        assert token not in executor_source


def test_graph_executor_matches_main_byte_for_byte():
    executor_path = "forge_bridge/composition/executor.py"
    local = (Path(__file__).parents[2] / executor_path).read_bytes()
    main = subprocess.run(
        ["git", "show", f"main:{executor_path}"],
        check=True,
        capture_output=True,
    ).stdout

    assert local == main
