"""PR-8-local participation discipline + PR 8 seed-surface tests.

This module enforces the PR-8-local participation contract for
``forge_bridge/corpus/_seed.py`` and houses the unit tests for
the seed-driver authority surface (``emit_seed_expectation`` +
``drive_seed_fixture`` + ``_invoke_chat_handler_in_process``).

The PR-8-local participation discipline is enforced by two
mechanisms in this module:

  1. ``_SEED_PERMITTED_IMPORTS`` — the value-locked frozenset of
     ``forge_bridge.corpus.*`` symbols ``_seed.py`` is permitted
     to import. Test ``test_seed_module_permitted_imports_locked``
     fires on growth, shrinkage, or substitution of the set.
  2. ``_corpus_references`` AST walker — extracts every
     ``forge_bridge.corpus.<X>`` reference from ``_seed.py``
     source. Test ``test_seed_module_imports_match_permitted_set``
     fires on ``_seed.py`` acquiring a forbidden import.

The participation contract is **semantic, not cardinal.** The
bright line rejects persistence-topology authority
(``_build_capture_record``, ``_resolve_corpus_dir``,
``_make_header``, ``_serialize_line``, direct file I/O), not the
cardinal symbol count. See ``A.5.3.2-PR8-SPEC.md`` §4.5.2 for
the architectural rationale.

The 18 verbatim entries governing this module live in
``forge_bridge/corpus/_seed.py``'s module docstring (carrier #15
at top, inherited carriers #1–#14, binding framing clarification,
two PR 8-local binding statements). Per ``A.5.3.2-PR8-SPEC.md``
§0 travel sites #4: per-test-file carrier blocks stay slim —
test names and module name carry the contract; the docstring
carries inherited governance by reference.

Carriers carried by reference from ``_seed.py``:

  - #1–#2 risk-category shift (PR 4).
  - #3–#6 integration-discipline quartet (PR 4).
  - #7 finalized-state contract (PR 4).
  - #8 risk-inheritance + surface-geometry distinction (PR 5).
  - #9 caller's view of deployment identity (PR 5).
  - #10 ambiguity-as-arbitration-outcome (PR 5).
  - #11 measured-not-inferred coverage (PR 5).
  - #12 structural-backstop framing (PR 6).
  - #13 observation-not-participation framing (PR 6).
  - #14 declared epistemic class vs. persisted provenance (Gate 2).
  - #15 chat-handler-only seeding scope (PR 8).
  - Binding framing clarification (Gate 2) — call-site-owned
    arbitration inputs.
  - PR 8-local binding #1 — companion records as truth-
    partitioning (cleanup-pressure-resistance class member #7).
  - PR 8-local binding #2 — emit_seed_expectation as semantics-
    not-topology (cleanup-pressure-resistance class member #8).

This module is a SKELETON at PR 8 Step 1. Only the participation
discipline tests (tests 12 + 13 per ``A.5.3.2-PR8-SPEC.md`` §5.1)
land at Step 1. The remaining 12 tests (4 schema + 3 helper +
4 driver + 1 ``__all__`` drift) land at Steps 2–4 per
``A.5.3.2-PR8-SPEC.md`` §6.

See ``A.5.3.2-PR8-SPEC.md`` §4.4 + §5.1 + §6 Step 1 for the
contract this module implements.
"""
from __future__ import annotations

import ast
import inspect
import logging
from pathlib import Path
from typing import Any

import pytest

import forge_bridge
from forge_bridge.corpus._seed import emit_seed_expectation
from forge_bridge.corpus._schema import (
    SCHEMA_VERSION,
    SchemaValidationError,
    validate_capture_record,
)
from tests.corpus._pr3_helpers import base_expectation_args


# PR-8-local participation discipline — _seed.py is the corpus-
# adjacent orchestration surface for Gate 2. It is permitted to
# import a small, named set of corpus symbols. The set is
# documented as the participation contract: two authority
# surfaces (the seam consumed by emit_seed_expectation, the
# scope consumed by drive_seed_fixture) plus three universal-
# key utilities (uuid, timestamp, schema version constant).
#
# The participation contract is SEMANTIC, not cardinal. The
# bright line rejects persistence-topology authority
# (_build_capture_record, _resolve_corpus_dir, _make_header,
# _serialize_line, direct file I/O), not the cardinal symbol
# count. Universal-key utilities and the schema version constant
# are infrastructural, not authority-bearing.
#
# Future PRs adding a sibling universal-key utility (e.g., a
# deterministic-ID generator at PR 9) route through framing
# review to confirm the addition belongs in the universal-keys
# class and not in the persistence-topology class. The
# admission decision is framing-level; the test value here is
# the artifact of that decision.
#
# See A.5.3.2-PR8-SPEC.md §4.4.1 + §4.5 amendment for the
# rationale and the cleanup-pressure-resistance class member #8
# protection this constant operationalizes.
_SEED_PERMITTED_IMPORTS: frozenset[str] = frozenset({
    # Authority surfaces (2):
    "forge_bridge.corpus._capture.seed_dispatch_scope",
    "forge_bridge.corpus._capture._persist_expectation_record",
    # Universal-key utilities (3):
    "forge_bridge.corpus._capture._now_iso_ms",
    "forge_bridge.corpus._capture._new_uuid",
    "forge_bridge.corpus._schema.SCHEMA_VERSION",
})


def _corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified ``forge_bridge.corpus.<X>``
    reference imported by ``source``.

    Mirrors the shape of
    ``tests/corpus/test_pr4_participation_creep.py::_corpus_references``
    but scoped to a single source file (``_seed.py``) and a
    different protected property (PR-8-local participation
    discipline rather than narrowing-subsystem → corpus
    one-directional flow).

    For ``from forge_bridge.corpus.<submodule> import <symbol>``,
    records the dotted symbol form
    (``forge_bridge.corpus.<submodule>.<symbol>``) — matches the
    ``_SEED_PERMITTED_IMPORTS`` element shape. This differs from
    the PR 4 walker, which records the submodule itself; PR 8's
    test enforces symbol-level admission, not submodule-level.

    Returns a list of dotted strings — one per imported name or
    submodule. Comments and docstrings are not inspected (AST
    walks only Import / ImportFrom nodes), matching the
    "import-target, not text-occurrence" semantic the framing
    requires.
    """
    refs: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "forge_bridge.corpus":
                for alias in node.names:
                    refs.append(f"forge_bridge.corpus.{alias.name}")
            elif module.startswith("forge_bridge.corpus."):
                # `from forge_bridge.corpus.<submodule> import <symbol>` —
                # record the dotted import target (module.symbol).
                for alias in node.names:
                    refs.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    alias.name == "forge_bridge.corpus"
                    or alias.name.startswith("forge_bridge.corpus.")
                ):
                    refs.append(alias.name)
    return refs


def test_seed_module_permitted_imports_locked():
    """Risk #5a — the allowlist constant value must match the
    spec-locked frozenset exactly.

    Per ``A.5.3.2-PR8-SPEC.md`` §3 risk #5 + §5.1 test 12: the
    test fires on growth (a 6th symbol added), shrinkage (a
    symbol removed), or substitution (a symbol replaced).

    The participation contract is semantic, not cardinal — the
    bright line is rejection of persistence-topology authority,
    not enforcement of an exact symbol count. But the constant
    value itself is locked at the PR 8 spec; changes route
    through framing review (per ``A.5.3.2-PR8-SPEC.md`` §7
    phase-end conditions row "Acquiring persistence-topology
    authority in _SEED_PERMITTED_IMPORTS").
    """
    expected: frozenset[str] = frozenset({
        # Authority surfaces (2):
        "forge_bridge.corpus._capture.seed_dispatch_scope",
        "forge_bridge.corpus._capture._persist_expectation_record",
        # Universal-key utilities (3):
        "forge_bridge.corpus._capture._now_iso_ms",
        "forge_bridge.corpus._capture._new_uuid",
        "forge_bridge.corpus._schema.SCHEMA_VERSION",
    })
    assert _SEED_PERMITTED_IMPORTS == expected, (
        "PR-8-local participation discipline allowlist drift "
        "detected.\n"
        "\n"
        f"Expected (5 elements — 2 authority surfaces + 3 "
        f"universal-key utilities):\n"
        + "".join(f"  {p}\n" for p in sorted(expected))
        + "\n"
        f"Actual ({len(_SEED_PERMITTED_IMPORTS)} elements):\n"
        + "".join(f"  {p}\n" for p in sorted(_SEED_PERMITTED_IMPORTS))
        + "\n"
        "If this drift is intentional, the admission decision "
        "is framing-level (NOT a cleanup-PR-layer change). See "
        "A.5.3.2-PR8-SPEC.md §7 phase-end conditions for the "
        "review routing."
    )


def test_seed_module_imports_match_permitted_set():
    """Risk #5b — _seed.py's actual corpus imports must all be
    in _SEED_PERMITTED_IMPORTS.

    Per ``A.5.3.2-PR8-SPEC.md`` §3 risk #5 + §5.1 test 13:
    AST-walks ``_seed.py`` source; extracts every
    ``forge_bridge.corpus.<X>`` reference via
    ``_corpus_references(...)``; asserts each is in the
    allowlist. Fires on ``_seed.py`` acquiring a forbidden
    import (e.g., ``_build_capture_record`` "for symmetry,"
    ``_resolve_corpus_dir`` "to inline persistence").

    At Step 1, ``_seed.py`` has zero ``forge_bridge.corpus.*``
    imports (the function stubs use no corpus symbols; consumers
    land at Steps 2–4). The test passes trivially with zero
    offenders. At each subsequent step, additional imports
    accumulate and the test actively exercises the
    allowlist-lookup logic.
    """
    package_root = Path(forge_bridge.__file__).parent
    seed_path = package_root / "corpus" / "_seed.py"
    assert seed_path.exists(), (
        f"_seed.py expected at {seed_path}. The PR-8-local "
        f"participation discipline test cannot enforce its "
        f"boundary if the file it walks is gone. Either restore "
        f"the file or amend this test's path."
    )
    source = seed_path.read_text(encoding="utf-8")

    offenders: list[str] = []
    for ref in _corpus_references(source):
        if ref not in _SEED_PERMITTED_IMPORTS:
            offenders.append(ref)

    assert offenders == [], (
        "PR-8-local participation discipline violated: _seed.py "
        "imports a corpus surface OUTSIDE the permitted set.\n"
        "\n"
        "Permitted (semantic, not cardinal — the bright line "
        "rejects persistence-topology authority):\n"
        + "".join(f"  {p}\n" for p in sorted(_SEED_PERMITTED_IMPORTS))
        + "\n"
        "Offenders:\n"
        + "".join(f"  {ref}\n" for ref in offenders)
        + "\n"
        "Per cleanup-pressure-resistance class member #8 "
        "(A.5.3.2-PR8-FRAMING.md §6.2 + A.5.3.2-PR8-SPEC.md "
        "§4.1.5.1): authored expectation and persistence "
        "topology are intentionally distinct authority surfaces. "
        "_seed.py may not acquire persistence-topology "
        "authority — that includes _build_capture_record, "
        "_resolve_corpus_dir, _make_header, _serialize_line, "
        "and any direct file I/O surface.\n"
        "\n"
        "If the import is genuinely a universal-key utility "
        "sibling (e.g., a deterministic-ID generator at PR 9), "
        "the admission decision is framing-level — route "
        "through framing review per A.5.3.2-PR8-SPEC.md §7 "
        "phase-end conditions row 'Acquiring a universal-key "
        "sibling utility to _SEED_PERMITTED_IMPORTS'."
    )


# ── Schema validator extension — PR 8 Step 2 tests 1-4 ─────────────
#
# Per A.5.3.2-PR8-SPEC.md §4.2 + §5.1 tests 1-4: PR 8 extends
# _schema.py's record_kind == "expectation" branch with the three
# PR 8-required fields (fixture_id, prompt, expected_narrow) plus
# per-field type validation. The existing no-source check is
# preserved unchanged.
#
# These tests use hand-crafted minimum-shape expectation records
# (not base_expectation_args — that helper returns kwargs for
# emit_seed_expectation, which lands at Step 3). The pattern
# mirrors PR 7's expectation-persistence tests:
#   "Schema validation tests that need raw record dicts hand-craft
#    the minimum-shape records directly."
# (A.5.3.2-PR8-SPEC.md §5.4 + §0 PR-8-local binding statements.)


def _minimum_valid_expectation_record(**overrides: Any) -> dict[str, Any]:
    """Build a minimum-shape valid expectation record.

    Returns a dict carrying the 4 universal keys (schema_version,
    capture_id, captured_at, record_kind) + the 3 PR 8-required
    fields (fixture_id, prompt, expected_narrow). Tests override
    individual keys (or delete them) to exercise the validator's
    failure modes.

    This helper is local to schema tests because:

    1. ``base_expectation_args`` (§4.3, lands at Step 3) returns
       kwargs for ``emit_seed_expectation``; it does NOT return
       universal keys.
    2. Schema validation operates on full record dicts, not
       kwargs. The dict needs the universal keys too.

    Per A.5.3.2-PR8-SPEC.md §5.4: "Schema validation tests that
    need raw record dicts hand-craft the minimum-shape records
    directly (same pattern as PR 7's expectation-persistence
    tests)."
    """
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": "test-capture-id",
        "captured_at": "2026-05-10T12:00:00.000Z",
        "record_kind": "expectation",
        "fixture_id": "fix-001",
        "prompt": "list staged",
        "expected_narrow": ["forge_list_staged"],
    }
    record.update(overrides)
    return record


def test_expectation_record_rejects_observation_fields() -> None:
    """Risk #2 — schema validator rejects expectation records
    carrying the canonical observation-record marker (``source``
    field).

    Per A.5.3.2-PR8-SPEC.md §3 risk #2 + §5.1 test 1: the
    unified-record shape (expectation + observation fields in one
    record) destroys falsifiability by allowing expectation and
    observation to co-author the same artifact. The schema
    validator enforces the partition at the persistence boundary.

    Co-named with cleanup-pressure-resistance class member #7
    (companion records as truth-partitioning) per
    A.5.3.2-PR8-SPEC.md §0 PR 8-local binding statement #1.
    """
    record = _minimum_valid_expectation_record(source="runtime")
    with pytest.raises(SchemaValidationError, match="source"):
        validate_capture_record(record)


@pytest.mark.parametrize(
    "missing_key",
    ["fixture_id", "prompt", "expected_narrow"],
)
def test_expectation_record_requires_three_keys(missing_key: str) -> None:
    """Risk #2 sibling — schema validator rejects expectation
    records missing any of the 3 PR 8-required fields.

    Per A.5.3.2-PR8-SPEC.md §3 risk #2 + §5.1 test 2 +
    _schema.py::_REQUIRED_EXPECTATION_KEYS: the minimum-viable
    expectation shape requires exactly three fields beyond the 4
    universal keys. Locked at framing §5.3 (Q2) — cleanup PRs may
    not extend this set without framing review.
    """
    record = _minimum_valid_expectation_record()
    del record[missing_key]
    with pytest.raises(
        SchemaValidationError,
        match="expectation record missing required keys",
    ):
        validate_capture_record(record)


@pytest.mark.parametrize(
    "field,invalid_value",
    [
        # fixture_id: must be a non-empty string.
        ("fixture_id", ""),
        ("fixture_id", 42),
        ("fixture_id", None),
        # prompt: must be a non-empty string.
        ("prompt", ""),
        ("prompt", None),
        ("prompt", 42),
        # expected_narrow: must be a list of strings (possibly empty).
        ("expected_narrow", "not a list"),
        ("expected_narrow", None),
        ("expected_narrow", [1, 2, 3]),
        ("expected_narrow", ["valid", 42]),
    ],
)
def test_expectation_record_field_types_validated(
    field: str, invalid_value: Any,
) -> None:
    """Behavioral fill — schema validator enforces per-field type
    contracts on expectation records.

    Per A.5.3.2-PR8-SPEC.md §4.2.2 + §5.1 test 3:

      - fixture_id: non-empty string.
      - prompt: non-empty string.
      - expected_narrow: list[str] (possibly empty — the empty
        list is valid; expresses zero-survivor narrowing).

    Failure modes per the parametrize set: empty string, wrong
    type, list-of-wrong-type, mixed-type list. Each raises
    SchemaValidationError with a field-named message.
    """
    record = _minimum_valid_expectation_record(**{field: invalid_value})
    with pytest.raises(SchemaValidationError, match=field):
        validate_capture_record(record)


def test_expectation_record_round_trip_valid() -> None:
    """Behavioral fill — fully-valid expectation record passes
    validation.

    Per A.5.3.2-PR8-SPEC.md §4.2.2 + §5.1 test 4: covers the
    happy path (4 universal keys + record_kind + 3 PR 8-required
    fields, all with valid values).

    Sub-case: empty expected_narrow list is also valid — expresses
    "expected zero-survivor narrowing for this prompt" (a
    meaningful Gate 4 comparator case; expectation is not
    certainty).
    """
    # Standard happy path:
    record = _minimum_valid_expectation_record()
    assert validate_capture_record(record) is None

    # Empty expected_narrow list (zero-survivor expectation):
    record_zero_survivor = _minimum_valid_expectation_record(
        expected_narrow=[],
    )
    assert validate_capture_record(record_zero_survivor) is None

    # Multi-tool expected_narrow:
    record_multi = _minimum_valid_expectation_record(
        expected_narrow=["forge_list_staged", "forge_get_staged"],
    )
    assert validate_capture_record(record_multi) is None


# ── emit_seed_expectation helper — PR 8 Step 3 tests 5-7 ───────────
#
# Per A.5.3.2-PR8-SPEC.md §4.1.3 + §5.1 tests 5-7: PR 8 Step 3
# lands the helper body that operationalizes cleanup-pressure-
# resistance class member #8 (semantics-not-topology guard).
# The helper builds the expectation record dict and delegates
# persistence to _persist_expectation_record (the PR 7 seam).
#
# Risk #1 (helper-singularity smearing of member #8 surface) is
# enforced mechanically by test 5 — signature shape IS the truth
# claim; widening it would silently broaden the authority
# surface.


def test_emit_seed_expectation_signature_is_authority_pure() -> None:
    """Risk #1 — helper signature shape IS the authored-expectation
    truth claim.

    Per A.5.3.2-PR8-SPEC.md §3 risk #1 + §5.1 test 5: asserts
    ``inspect.signature(emit_seed_expectation)`` has exactly 3
    keyword-only parameters (``fixture_id``, ``prompt``,
    ``expected_narrow``), each without a default value, and the
    return annotation is ``None``.

    Widening the signature with arbitration-state fields, optional
    kwargs, a return value, or a ``source`` parameter would erode
    the semantics-not-topology guard (cleanup-pressure-resistance
    class member #8). The helper begins behaving like a thin
    observation-helper variant; authority partitioning collapses.

    The signature shape IS the truth claim — verbatim PR 8-local
    binding statement #2 (semantics-not-topology guard) lives in
    the helper's docstring; this test is the mechanical
    enforcement.
    """
    sig = inspect.signature(emit_seed_expectation)

    # Exactly 3 parameters:
    param_names = list(sig.parameters.keys())
    assert param_names == ["fixture_id", "prompt", "expected_narrow"], (
        f"Helper signature must have exactly 3 parameters in order "
        f"(fixture_id, prompt, expected_narrow), got: {param_names}. "
        f"Adding/removing/reordering parameters breaks the authored-"
        f"expectation truth claim per A.5.3.2-PR8-SPEC.md §0 PR "
        f"8-local binding statement #2."
    )

    # All keyword-only:
    for name, param in sig.parameters.items():
        assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
            f"Parameter {name!r} must be keyword-only (got kind="
            f"{param.kind}). The keyword-only marker matches the "
            f"corpus convention and prevents positional-argument "
            f"acquisition."
        )

    # No defaults:
    for name, param in sig.parameters.items():
        assert param.default is inspect.Parameter.empty, (
            f"Parameter {name!r} must not have a default value "
            f"(got default={param.default!r}). Optional parameters "
            f"would invite helper-singularity smearing per "
            f"A.5.3.2-PR8-SPEC.md §3 risk #1."
        )

    # Return annotation is None. With `from __future__ import
    # annotations`, the annotation is the string "None"; without
    # it, the annotation is type(None) or None. Both forms are
    # acceptable; widening (e.g., to a dict return) is not.
    return_annot = sig.return_annotation
    assert return_annot in (None, type(None), "None"), (
        f"Return annotation must be None, got {return_annot!r}. "
        f"Returning a value would invite consumers to depend on "
        f"the helper's internal record dict, eroding the "
        f"fire-and-forget I-6 contract."
    )


def test_emit_seed_expectation_persists_via_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Behavioral fill — helper delegates persistence to the PR 7
    seam.

    Per A.5.3.2-PR8-SPEC.md §5.1 test 6: patches
    ``_persist_expectation_record`` (in ``_seed.py``'s namespace —
    module-scoped import bound at load time, patching consumer
    intercepts the lookup); invokes
    ``emit_seed_expectation(**base_expectation_args())``; asserts
    the seam was called exactly once with a dict carrying
    ``record_kind="expectation"``, the 3 PR 8-required fields, and
    the 4 universal keys.

    The dict shape assertion is structural, not value-exact —
    uuid + timestamp are non-deterministic; the structural
    requirement is "has these keys with these expected
    types/values."

    Member #8 protection: the helper delegates persistence; it
    does NOT inline _resolve_corpus_dir, _make_header,
    _serialize_line, or any direct file I/O.
    """
    captured: list[dict] = []

    def sentinel(record: dict) -> None:
        captured.append(record)

    # Patch consumer namespace (where _seed.py looks up the seam at
    # call time). Module-scoped imports bind at load time; the
    # consumer's name table holds the original reference. Patching
    # the source namespace would NOT intercept the call because
    # _seed.py's binding still points to the original function
    # object.
    monkeypatch.setattr(
        "forge_bridge.corpus._seed._persist_expectation_record",
        sentinel,
    )

    emit_seed_expectation(**base_expectation_args())

    assert len(captured) == 1, (
        f"Expected exactly one seam invocation, got {len(captured)}."
    )
    record = captured[0]

    # PR 8-required fields match base_expectation_args defaults:
    assert record["fixture_id"] == "fix-pr8-default"
    assert record["prompt"] == "list staged shots"
    assert record["expected_narrow"] == ["forge_list_staged"]

    # Universal keys + record_kind:
    assert record["record_kind"] == "expectation"
    assert record["schema_version"] == SCHEMA_VERSION
    assert isinstance(record["capture_id"], str)
    assert record["capture_id"], "capture_id must be non-empty"
    assert isinstance(record["captured_at"], str)
    assert record["captured_at"], "captured_at must be non-empty"

    # No observation-record fields — member #7 protection
    # (companion records as truth-partitioning):
    assert "source" not in record, (
        "Expectation records MUST NOT carry a 'source' field "
        "(member #7 protection — truth-partitioning)."
    )
    assert "narrower" not in record
    assert "candidate_set" not in record
    assert "topology" not in record
    assert "identity" not in record


def test_emit_seed_expectation_failure_invisibility(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    """Behavioral fill — I-6 enforcement on the helper's outer
    try/except wrapper.

    Per A.5.3.2-PR8-SPEC.md §5.1 test 7: patches the seam to
    raise ``RuntimeError``; invokes the helper; asserts the
    helper returns ``None`` and the exception is logged at
    WARNING level with the fixture_id + error context.

    I-6 contract: observation failure cannot become arbitration
    failure. The helper's outer try/except is defense in depth
    on top of ``_persist_expectation_record``'s own I-6 wrap
    (both layers preserve the fire-and-forget contract).
    """
    def raising_seam(record: dict) -> None:
        raise RuntimeError("seam failure for test")

    monkeypatch.setattr(
        "forge_bridge.corpus._seed._persist_expectation_record",
        raising_seam,
    )

    caplog.set_level(logging.WARNING, logger="forge_bridge.corpus._seed")

    result = emit_seed_expectation(**base_expectation_args())

    # I-6: fire-and-forget — no exception propagates, returns None.
    assert result is None, (
        f"Helper must return None under failure (I-6); got {result!r}."
    )

    # WARNING logged with fixture_id + error type context:
    warning_records = [
        r for r in caplog.records
        if r.levelname == "WARNING"
        and r.name == "forge_bridge.corpus._seed"
    ]
    assert len(warning_records) >= 1, (
        f"Expected at least one WARNING log; got "
        f"{[(r.levelname, r.name) for r in caplog.records]}."
    )

    warning_msg = warning_records[0].getMessage()
    assert "emit_seed_expectation failed" in warning_msg, (
        f"Expected 'emit_seed_expectation failed' in warning; got: "
        f"{warning_msg!r}."
    )
    assert "fix-pr8-default" in warning_msg, (
        f"Expected fixture_id 'fix-pr8-default' in warning context; "
        f"got: {warning_msg!r}."
    )
    assert "RuntimeError" in warning_msg, (
        f"Expected error type 'RuntimeError' in warning context; "
        f"got: {warning_msg!r}."
    )
