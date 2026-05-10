"""tests.corpus.test_pr7_record_kind_schema — PR 7 Step 5 schema tests.

Locks the record_kind discriminator's behavior in
``forge_bridge/corpus/_schema.py``: observation records carry
source ∈ KNOWN_SOURCE_VALUES and the original PR 1-3 canonical
fields; expectation records carry record_kind="expectation" and
explicitly NO source field; unknown record_kind values are
rejected.

See ``forge_bridge/corpus/_sources.py`` module docstring for the
14 inherited carriers + binding framing clarification (verbatim).
See ``A.5.3.2-PR7-SPEC.md`` §4.3.1 + the §4.3 amendment for the
record_kind contract these tests enforce mechanically.

Step 5 lands these tests alongside the schema validator's
KNOWN_SOURCE_VALUES integration; PR 7 ships record_kind
validation but expectation-record-shape definition (beyond "no
source field") is PR 8's domain.
"""
from __future__ import annotations

from typing import Any

import pytest

from forge_bridge.corpus._capture import _build_capture_record
from forge_bridge.corpus._schema import (
    SchemaValidationError,
    validate_capture_record,
)
from tests.corpus._pr3_helpers import base_builder_args


def _minimum_expectation_record() -> dict[str, Any]:
    """Build a minimum-shape expectation record.

    Per PR 7 §4.3 amendment, expectation records require only the
    universal top-level keys (schema_version, capture_id,
    captured_at, record_kind) and MUST NOT carry a source field.
    PR 8's seed driver will define expectation-specific required
    fields when the seed driver lands; PR 7 ships only the
    structural asymmetry.
    """
    return {
        "schema_version": "1",
        "capture_id": "00000000-0000-0000-0000-000000000000",
        "captured_at": "2026-05-09T12:00:00.000Z",
        "record_kind": "expectation",
    }


def test_observation_record_validates(clean_identity_caches) -> None:
    """Step 5. Minimum-shape observation record passes validation.

    Constructs a coherent observation record via _build_capture_record
    (the canonical builder; tests bypassing it would have to mirror
    the contract §3 record shape inline). Asserts
    validate_capture_record does not raise.
    """
    record = _build_capture_record(**base_builder_args())
    validate_capture_record(record)  # no exception


def test_expectation_record_validates() -> None:
    """Step 5. Minimum-shape expectation record passes validation.

    Constructs a record with record_kind="expectation" and no
    source field; asserts validate_capture_record does not raise.
    The minimum shape is locked by PR 7: schema_version, capture_id,
    captured_at, record_kind. PR 8 may extend with expectation-
    specific required fields when the seed driver lands.
    """
    record = _minimum_expectation_record()
    validate_capture_record(record)  # no exception


def test_unknown_record_kind_rejected() -> None:
    """Step 5. Unknown record_kind values raise SchemaValidationError.

    Locks the record_kind enum mechanically: any value outside
    {observation, expectation} fails validation. Per Gate 2 framing
    §9.2, adding a third record_kind requires a new authority
    surface (framing-level decision); the validator must not
    silently accept new values.
    """
    invalid_values: list[Any] = ["", "obs", "expect", "unknown", "Observation"]

    for invalid in invalid_values:
        record = _minimum_expectation_record()
        record["record_kind"] = invalid
        with pytest.raises(SchemaValidationError, match="record_kind"):
            validate_capture_record(record)


def test_observation_record_unknown_source_rejected(
    clean_identity_caches,
) -> None:
    """Step 5. Observation records with source ∉ KNOWN_SOURCE_VALUES
    raise SchemaValidationError.

    Per PR 7 §4.3 amendment + carrier #14: source-class governance
    is the persistence-layer authority; only KNOWN_SOURCE_VALUES
    are admissible on observation records. Legacy "fixture" was
    removed from the set; future additions require lockstep
    framing-level review.

    Tests both a clearly-bogus value ("cosmic") and the legacy
    value that was removed in this amendment ("fixture") — the
    latter is the mechanical assertion that the migration didn't
    silently revert.
    """
    for invalid_source in ["cosmic", "fixture", "phantom", ""]:
        record = _build_capture_record(
            **base_builder_args(source=invalid_source)
        )
        with pytest.raises(SchemaValidationError, match="source"):
            validate_capture_record(record)
