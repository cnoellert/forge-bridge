"""PR 1 — Gate 1 skeleton smoke tests.

Discipline check: if PR 1 is the only thing that ever lands, daemon
observable behavior is unchanged. These tests verify the PR 1
surface in isolation:

  - The package imports cleanly.
  - ``divergence_capture_enabled`` honors the env-var gate, including
    invalid values (one-time WARNING per unique value, treated as
    disabled).
  - ``emit_divergence_capture`` exists but is a stub that fails
    loudly (NotImplementedError) — accidental integration before
    PR 3 surfaces immediately, not silently.
  - The schema validator accepts a hand-written valid Layer 1 record
    and rejects records with missing or invalid fields.
  - The PR 2/PR 3 stubs raise NotImplementedError as expected.

PR 2 (identity + topology), PR 3 (capture builder + writer), PR 4
(chat handler call site), PR 5 (chain step call site) all add their
own test files alongside their implementations.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest


# ── Package imports cleanly ────────────────────────────────────────────────


def test_package_imports_cleanly():
    """The PR 1 package imports without side effects, and the
    documented public API symbols are present."""
    import forge_bridge.corpus  # noqa: F401
    from forge_bridge.corpus import (
        SCHEMA_VERSION,
        SchemaValidationError,
        divergence_capture_enabled,
        emit_divergence_capture,
        read_capture_file,
        validate_capture_record,
    )

    assert SCHEMA_VERSION == "1"
    assert callable(divergence_capture_enabled)
    assert callable(emit_divergence_capture)
    assert callable(read_capture_file)
    assert callable(validate_capture_record)
    assert issubclass(SchemaValidationError, ValueError)


# ── divergence_capture_enabled — env-var gate ──────────────────────────────


@pytest.mark.parametrize("raw,expected", [
    ("1", True), ("true", True), ("TRUE", True), ("True", True),
    ("yes", True), ("YES", True),
    ("  1  ", True),  # whitespace tolerated
    ("0", False), ("false", False), ("FALSE", False), ("no", False),
    ("", False),
])
def test_divergence_capture_enabled_recognized_values(monkeypatch, raw, expected):
    from forge_bridge.corpus import divergence_capture_enabled
    monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", raw)
    assert divergence_capture_enabled() is expected


def test_divergence_capture_enabled_unset_defaults_disabled(monkeypatch):
    """The disabled-by-default discipline: the gate is OFF unless
    explicitly turned on."""
    from forge_bridge.corpus import divergence_capture_enabled
    monkeypatch.delenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", raising=False)
    assert divergence_capture_enabled() is False


def test_divergence_capture_enabled_invalid_value_warns_once(
    monkeypatch, caplog, clean_warning_state,
):
    """Invalid values are treated as disabled and warn ONCE per
    unique invalid value seen — surfaces typos without log spam.

    Test isolation handled by the ``clean_warning_state`` fixture
    (see ``tests/corpus/conftest.py``)."""
    from forge_bridge.corpus import divergence_capture_enabled

    monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "maybe")
    with caplog.at_level(logging.WARNING, logger="forge_bridge.corpus._capture"):
        assert divergence_capture_enabled() is False
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "maybe" in warnings[0].getMessage()

    # Second call with the same invalid value: no additional warning.
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="forge_bridge.corpus._capture"):
        assert divergence_capture_enabled() is False
        assert [
            r for r in caplog.records if r.levelno == logging.WARNING
        ] == []


def test_divergence_capture_enabled_distinct_invalid_values_each_warn(
    monkeypatch, caplog, clean_warning_state,
):
    """Two different invalid values each warn independently.

    Test isolation handled by the ``clean_warning_state`` fixture."""
    from forge_bridge.corpus import divergence_capture_enabled

    monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "maybe")
    with caplog.at_level(logging.WARNING, logger="forge_bridge.corpus._capture"):
        divergence_capture_enabled()

    caplog.clear()
    monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "perhaps")
    with caplog.at_level(logging.WARNING, logger="forge_bridge.corpus._capture"):
        divergence_capture_enabled()
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "perhaps" in warnings[0].getMessage()


# ── emit_divergence_capture stub ───────────────────────────────────────────


def test_emit_divergence_capture_stub_raises():
    """Stub-as-error rather than stub-as-noop is intentional —
    accidental integration before PR 3 surfaces immediately."""
    from forge_bridge.corpus import emit_divergence_capture

    with pytest.raises(NotImplementedError, match="PR 1 skeleton stub"):
        emit_divergence_capture(
            prompt="x",
            candidate_set_post_reachability=[],
            candidate_set_post_pr14=[],
            narrower_decision=[],
            pr20_fired=False,
            collapse_occurred=False,
            ambiguity_state="single_survivor",
            narrower_latency_ms=0.0,
            source="fixture",
        )


# ── validate_capture_record ────────────────────────────────────────────────


def _valid_record() -> dict:
    """A hand-written Layer 1 record that conforms to the v1 schema.

    Per ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3. Used as the baseline
    that subsequent tests mutate to exercise specific failure modes.
    """
    return {
        "schema_version": "1",
        "capture_id": "00000000-0000-0000-0000-000000000000",
        "captured_at": "2026-05-06T12:00:00Z",
        "source": "fixture",
        "prompt": "list projects",
        "candidate_set": {
            "post_reachability": ["forge_list_staged", "forge_get_staged"],
            "post_pr14_filter":  ["forge_list_staged", "forge_get_staged"],
        },
        "topology": {
            "probed_at": "2026-05-06T12:00:00Z",
            "backends": {
                "flame_bridge": {
                    "reachable": False, "host": "127.0.0.1", "port": 9999,
                },
                "ollama_local": {
                    "reachable": True,  "host": "127.0.0.1", "port": 11434,
                },
                "anthropic": {
                    "reachable": True,  "configured": True,
                },
            },
        },
        "identity": {
            "narrower_version_hash": "a" * 64,
            "registered_tools_snapshot_hash": "b" * 64,
            "daemon_git_sha": "c" * 40,
        },
        "narrower": {
            "decision": ["forge_list_staged"],
            "pr20_fired": True,
            "collapse_occurred": True,
            "ambiguity_state": "single_survivor",
            "latency_ms": 0.42,
        },
    }


def test_validate_accepts_canonical_record():
    """The hand-written canonical record validates without error.
    This is the contract anchor — every other test is a deviation
    from this baseline."""
    from forge_bridge.corpus import validate_capture_record

    validate_capture_record(_valid_record())  # no exception


def test_validate_rejects_non_dict():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    with pytest.raises(SchemaValidationError, match="must be a dict"):
        validate_capture_record(["not", "a", "dict"])


@pytest.mark.parametrize("missing_key", [
    "schema_version", "capture_id", "captured_at", "source", "prompt",
    "candidate_set", "topology", "identity", "narrower",
])
def test_validate_rejects_missing_top_level_key(missing_key):
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    del record[missing_key]
    with pytest.raises(SchemaValidationError, match=missing_key):
        validate_capture_record(record)


def test_validate_rejects_unknown_schema_version():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    record["schema_version"] = "99"
    with pytest.raises(SchemaValidationError, match="schema_version"):
        validate_capture_record(record)


def test_validate_rejects_invalid_source():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    record["source"] = "production"
    with pytest.raises(SchemaValidationError, match="source"):
        validate_capture_record(record)


def test_validate_rejects_empty_prompt():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    record["prompt"] = ""
    with pytest.raises(SchemaValidationError, match="prompt"):
        validate_capture_record(record)


def test_validate_rejects_invalid_ambiguity_state():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    record["narrower"]["ambiguity_state"] = "many"
    with pytest.raises(SchemaValidationError, match="ambiguity_state"):
        validate_capture_record(record)


def test_validate_rejects_missing_required_backend():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    del record["topology"]["backends"]["flame_bridge"]
    with pytest.raises(SchemaValidationError, match="flame_bridge"):
        validate_capture_record(record)


def test_validate_rejects_backend_missing_reachable():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    del record["topology"]["backends"]["flame_bridge"]["reachable"]
    with pytest.raises(SchemaValidationError, match="reachable"):
        validate_capture_record(record)


def test_validate_rejects_empty_identity_hash():
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    record["identity"]["narrower_version_hash"] = ""
    with pytest.raises(
        SchemaValidationError, match="narrower_version_hash",
    ):
        validate_capture_record(record)


def test_validate_rejects_non_bool_pr20_fired():
    """pr20_fired must be a strict bool — not a truthy int."""
    from forge_bridge.corpus import (
        SchemaValidationError,
        validate_capture_record,
    )

    record = _valid_record()
    record["narrower"]["pr20_fired"] = 1  # truthy but not bool
    with pytest.raises(SchemaValidationError, match="pr20_fired"):
        validate_capture_record(record)


# ── PR 3 stubs still raise (PR 2 stubs are now implemented) ────────────────


def test_reader_stub_raises():
    """read_capture_file lands in PR 3 alongside the writer."""
    from forge_bridge.corpus import read_capture_file

    with pytest.raises(NotImplementedError, match="PR 3"):
        list(read_capture_file(Path("/nonexistent")))


# Note: ``test_topology_stub_raises`` and ``test_identity_stubs_raise``
# were removed in PR 2 because their underlying stubs are now
# implemented. PR 2's actual behavior is verified by
# ``tests/corpus/test_pr2_topology.py`` and
# ``tests/corpus/test_pr2_identity.py``.


# ── Discipline test: schema constraint on pr20_fired bool ──────────────────
#
# Strict bool checking guards against a class of subtle bugs where
# truthy/falsy ints would silently pass. This pairs with the contract
# §3 schema definition (pr20_fired: bool).
