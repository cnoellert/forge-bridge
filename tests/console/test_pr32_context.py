"""PR32 — Unit tests for priority-based ``extract_chain_context``."""
from __future__ import annotations

from forge_bridge.console._chain_parse import extract_chain_context


def test_single_version_propagates():
    res = {"versions": [{"id": "v1"}]}
    assert extract_chain_context(res) == {"version_id": "v1"}


def test_multi_versions_ignored():
    res = {"versions": [{"id": "v1"}, {"id": "v2"}]}
    assert extract_chain_context(res) == {}


def test_priority_project_over_others():
    res = {
        "projects": [{"id": "p1"}],
        "shots": [{"id": "s1"}],
        "versions": [{"id": "v1"}],
    }
    assert extract_chain_context(res) == {"project_id": "p1"}


def test_malformed_entries_ignored():
    res = {"versions": [{"no_id": "x"}]}
    assert extract_chain_context(res) == {}


def test_non_list_ignored():
    res = {"versions": {"id": "v1"}}
    assert extract_chain_context(res) == {}


def test_empty_id_ignored():
    res = {"versions": [{"id": "  "}]}
    assert extract_chain_context(res) == {}
