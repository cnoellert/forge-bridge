"""A.1 D2 commit-node classifier tests."""
from __future__ import annotations

from forge_bridge.graph.commit import graph_contains_commit_node


def test_graph_contains_commit_node_empty_returns_false():
    assert graph_contains_commit_node([]) is False


def test_graph_contains_commit_node_no_commit_returns_false():
    assert graph_contains_commit_node(["list shots"]) is False


def test_graph_contains_commit_node_with_commit_returns_true():
    assert graph_contains_commit_node([
        "flame_rename_shots dry_run=False",
        "commit",
    ]) is True


def test_graph_contains_commit_node_bare_commit_returns_true():
    assert graph_contains_commit_node(["commit"]) is True


def test_graph_contains_commit_node_case_insensitive():
    assert graph_contains_commit_node(["COMMIT"]) is True
