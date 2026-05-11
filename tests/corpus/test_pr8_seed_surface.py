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
from forge_bridge.corpus._capture import _DispatchContext, _dispatch_context
from forge_bridge.corpus._seed import (
    drive_seed_fixture,
    emit_seed_expectation,
)
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


# ── drive_seed_fixture driver — PR 8 Step 4 tests 8-11 ─────────────
#
# Per A.5.3.2-PR8-SPEC.md §4.1.5 + §5.1 tests 8-11: PR 8 Step 4
# lands the driver body that operationalizes:
#
#   - Carrier #15 governance (chat-handler-only seeding scope) —
#     test 8 enforces.
#   - Orchestration-not-authoring guard (driver delegates
#     expectation construction to emit_seed_expectation) —
#     test 9 enforces.
#   - Member #7 protection (companion records as truth-
#     partitioning) — scope-around-handler structure
#     operationalizes; test 10 verifies the dispatch context is
#     active inside the chat_handler invocation.
#   - Q1 lock (in-process direct invocation of chat_handler) —
#     test 11 enforces.
#
# All four driver tests use the clean_rate_limit_state fixture
# (per spec §4.6) — driver invocation triggers chat_handler's
# D-13 rate-limit pre-gate; clean state is required for test
# isolation.
#
# Patch-target architecture per Step 3 archaeological note:
#   - emit_seed_expectation (test 9): CONSUMER namespace
#     (forge_bridge.corpus._seed.emit_seed_expectation) —
#     module-scoped import binds at load time.
#   - _invoke_chat_handler_in_process (test 10): CONSUMER
#     namespace (forge_bridge.corpus._seed._invoke_chat_handler_in_process)
#     — defined in same module, looked up via module namespace.
#   - chat_handler (test 11): SOURCE namespace
#     (forge_bridge.console.handlers.chat_handler) — function-
#     scoped import inside _invoke_chat_handler_in_process looks
#     up at call time.
#   - execute_chain_step (test 8): CONSUMER namespace
#     (forge_bridge.console._engine.execute_chain_step) — module-
#     scoped import in _engine.py binds at load time.


def test_driver_does_not_invoke_chain_step(
    monkeypatch: pytest.MonkeyPatch,
    clean_rate_limit_state: None,
) -> None:
    """Risk #3 (carrier #15 breach) — driver does NOT invoke
    chain-step arbitration during seeded driver execution.

    Per A.5.3.2-PR8-SPEC.md §3 risk #3 + §5.1 test 8: the test
    invokes ``drive_seed_fixture(**base_expectation_args())``
    directly with canonical single-step fixture shapes while
    patching the chain-step entry point with a sentinel. The
    sentinel asserts that chain-step arbitration was not invoked
    during those seeded driver executions.

    The scope is local orchestration-boundary enforcement (the
    test asserts what the driver does), not global suite
    surveillance.

    Carrier #15 governs (verbatim, see ``_seed.py`` module
    docstring): chain-step seeding is explicitly deferred. The
    test catches:
      - Direct invocation of execute_chain_step from
        drive_seed_fixture (regression).
      - Modifications that bypass chat_handler and invoke
        chain-step directly.

    NOT covered at unit-test scope:
      - Future fixtures with multi-step prompt content that go
        through the REAL chat_handler. That coverage lives in
        PR 9 integration tests (real fixtures + real daemon
        state).

    Patch targets:
      - chat_handler (SOURCE) — function-scoped import in
        _invoke_chat_handler_in_process; patching source
        intercepts the lookup. Benign sentinel allows the driver
        to complete without daemon state.
      - execute_chain_step (CONSUMER in _engine.py) — module-
        scoped import binds at load time; patching consumer
        intercepts the lookup. Tracer detects any invocation.
    """
    chain_step_invocations: list[tuple[tuple, dict]] = []

    async def chain_step_tracer(*args: Any, **kwargs: Any) -> None:
        chain_step_invocations.append((args, kwargs))
        return None

    async def benign_chat_handler(request: Any) -> None:
        # No-op: chat_handler is bypassed in this test. The
        # driver's interest is only in the chain-step
        # invocation detection.
        return None

    monkeypatch.setattr(
        "forge_bridge.console.handlers.chat_handler",
        benign_chat_handler,
    )
    monkeypatch.setattr(
        "forge_bridge.console._engine.execute_chain_step",
        chain_step_tracer,
    )

    drive_seed_fixture(**base_expectation_args())

    assert chain_step_invocations == [], (
        f"Carrier #15 violation: execute_chain_step was invoked "
        f"during seeded driver execution.\n"
        f"\n"
        f"Invocations: {chain_step_invocations}\n"
        f"\n"
        f"Per A.5.3.2-PR8-SPEC.md §0 carrier #15: PR 8 seeds the "
        f"chat-handler observation surface only. Chain-step "
        f"seeding is explicitly deferred. Cross-surface "
        f"expectation semantics require a dedicated framing pass "
        f"before implementation proceeds."
    )


def test_driver_emits_expectation_through_helper(
    monkeypatch: pytest.MonkeyPatch,
    clean_rate_limit_state: None,
) -> None:
    """Risk #4 — orchestration-not-authoring guard mechanically
    enforced.

    Per A.5.3.2-PR8-SPEC.md §3 risk #4 + §5.1 test 9: the test
    protects against orchestration-layer collapse into authored-
    semantics authority. The driver MUST delegate expectation
    construction to emit_seed_expectation; it MUST NOT build the
    expectation record dict directly.

    The orchestration-not-authoring guard (verbatim in
    drive_seed_fixture's docstring): "drive_seed_fixture is an
    orchestration surface, not an expectation-authoring surface."

    Test patches emit_seed_expectation (in _seed.py's namespace —
    CONSUMER patch; module-scoped import binds at load time);
    invokes drive_seed_fixture(**base_expectation_args()); asserts
    the sentinel was called exactly once with the exact 3-kwarg
    shape (no positional args, no extra kwargs, no missing
    kwargs).

    Also patches chat_handler benignly to allow the driver to
    complete without daemon state.
    """
    helper_invocations: list[tuple[tuple, dict]] = []

    def helper_sentinel(*args: Any, **kwargs: Any) -> None:
        helper_invocations.append((args, kwargs))

    async def benign_chat_handler(request: Any) -> None:
        return None

    monkeypatch.setattr(
        "forge_bridge.corpus._seed.emit_seed_expectation",
        helper_sentinel,
    )
    monkeypatch.setattr(
        "forge_bridge.console.handlers.chat_handler",
        benign_chat_handler,
    )

    drive_seed_fixture(**base_expectation_args())

    # Exactly one invocation:
    assert len(helper_invocations) == 1, (
        f"Expected exactly one emit_seed_expectation invocation, "
        f"got {len(helper_invocations)}: {helper_invocations}."
    )

    args, kwargs = helper_invocations[0]

    # No positional args:
    assert args == (), (
        f"emit_seed_expectation must be called with keyword-only "
        f"args; got positional args: {args}. The orchestration-"
        f"not-authoring guard requires structural delegation via "
        f"the 3-kwarg contract."
    )

    # Exact 3-kwarg shape:
    expected_kwargs = base_expectation_args()
    assert kwargs == expected_kwargs, (
        f"emit_seed_expectation kwarg shape drift detected.\n"
        f"Expected: {expected_kwargs!r}\n"
        f"Got:      {kwargs!r}\n"
        f"\n"
        f"The driver must forward kwargs verbatim to "
        f"emit_seed_expectation. Modifying or filtering the kwargs "
        f"in the driver's body collapses the orchestration/"
        f"authoring authority partition."
    )


def test_driver_opens_scope_around_chat_handler(
    monkeypatch: pytest.MonkeyPatch,
    clean_rate_limit_state: None,
) -> None:
    """Behavioral fill — scope ordering verified mechanically.

    Per A.5.3.2-PR8-SPEC.md §5.1 test 10: the driver opens
    seed_dispatch_scope BEFORE invoking chat_handler, and exits
    the scope AFTER. Inside the scope, _dispatch_context.get()
    returns a _DispatchContext with source="seed" + the
    supplied fixture_id.

    This is the operational placement of member #7 protection
    (companion records): inside the scope, observation emissions
    from chat_handler's internal arbitration (handlers.py:1185)
    persist source="seed" + fixture_id. The expectation record
    persisted before the scope (emit_seed_expectation) is the
    companion of any observation record that fires inside the
    scope; Gate 4's comparator joins them on fixture_id.

    Patches _invoke_chat_handler_in_process with an async
    sentinel that captures _dispatch_context.get() at invocation
    time. The capture proves the scope is active during the
    chat_handler call site's effective context.

    After drive_seed_fixture returns, asserts
    _dispatch_context.get() is None — the scope was correctly
    exited.
    """
    captured_context: list[Any] = []

    async def context_capturing_sentinel(prompt: str) -> None:
        # Capture the dispatch context at the point where
        # chat_handler would be invoked.
        captured_context.append(_dispatch_context.get())

    monkeypatch.setattr(
        "forge_bridge.corpus._seed._invoke_chat_handler_in_process",
        context_capturing_sentinel,
    )

    # Pre-condition: no scope active.
    assert _dispatch_context.get() is None

    drive_seed_fixture(**base_expectation_args())

    # Post-condition: scope exited cleanly.
    assert _dispatch_context.get() is None, (
        "seed_dispatch_scope did not reset after drive_seed_fixture "
        "returned. The contextvar leak could cause subsequent "
        "emissions to falsely persist source='seed'."
    )

    # Captured context inside the scope:
    assert len(captured_context) == 1, (
        f"Expected one _invoke_chat_handler_in_process invocation, "
        f"got {len(captured_context)}."
    )
    ctx = captured_context[0]
    assert ctx is not None, (
        "Dispatch context was None inside the scope. The driver "
        "must open seed_dispatch_scope BEFORE invoking "
        "_invoke_chat_handler_in_process."
    )
    assert isinstance(ctx, _DispatchContext), (
        f"Dispatch context type mismatch: expected "
        f"_DispatchContext, got {type(ctx).__name__}."
    )
    assert ctx.source == "seed", (
        f"Dispatch context source must be 'seed' inside the scope, "
        f"got {ctx.source!r}."
    )
    assert ctx.fixture_id == "fix-pr8-default", (
        f"Dispatch context fixture_id must match the driver's "
        f"fixture_id kwarg ('fix-pr8-default'), got "
        f"{ctx.fixture_id!r}."
    )


def test_driver_invokes_chat_handler_in_process(
    monkeypatch: pytest.MonkeyPatch,
    clean_rate_limit_state: None,
) -> None:
    """Q1 lock confirmation — driver invokes chat_handler
    in-process with the canonical D-02 body shape.

    Per A.5.3.2-PR8-SPEC.md §5.1 test 11: patches
    ``forge_bridge.console.handlers.chat_handler`` (the SOURCE
    namespace, not the consumer/imported namespace inside
    ``_invoke_chat_handler_in_process``) with an async sentinel;
    invokes ``drive_seed_fixture(**base_expectation_args())``;
    asserts the sentinel was called exactly once with a Starlette
    Request argument carrying a JSON body whose
    ``messages[0].content`` matches the prompt kwarg.

    Patching the source namespace is structurally load-bearing:
    the architectural contract is that the driver reaches the
    console handler surface; tests should not couple to import
    timing or helper-local bindings. The function-scoped import
    inside ``_invoke_chat_handler_in_process`` looks up
    ``chat_handler`` at call time → patching source intercepts
    the lookup.

    Patching the consumer namespace would silently succeed if the
    helper acquired a second ``chat_handler`` reference (e.g.,
    via a different import path), masking the boundary
    violation.
    """
    captured_requests: list[Any] = []

    async def chat_handler_sentinel(request: Any) -> None:
        captured_requests.append(request)
        return None

    monkeypatch.setattr(
        "forge_bridge.console.handlers.chat_handler",
        chat_handler_sentinel,
    )

    drive_seed_fixture(**base_expectation_args())

    # Exactly one invocation:
    assert len(captured_requests) == 1, (
        f"Expected exactly one chat_handler invocation, got "
        f"{len(captured_requests)}."
    )

    request = captured_requests[0]

    # The argument is a Starlette Request:
    from starlette.requests import Request as StarletteRequest
    assert isinstance(request, StarletteRequest), (
        f"chat_handler must be invoked with a Starlette Request "
        f"argument; got {type(request).__name__}."
    )

    # The request body carries the canonical D-02 shape with
    # the driver's prompt as messages[0].content:
    body = await_request_json(request)
    assert isinstance(body, dict), (
        f"Request body must be a dict, got {type(body).__name__}."
    )
    messages = body.get("messages")
    assert isinstance(messages, list) and len(messages) == 1, (
        f"Request body must carry exactly one message, got: "
        f"{messages!r}."
    )
    msg = messages[0]
    assert msg.get("role") == "user", (
        f"Message role must be 'user', got {msg.get('role')!r}."
    )
    assert msg.get("content") == "list staged shots", (
        f"Message content must match the driver's prompt kwarg "
        f"('list staged shots' from base_expectation_args), got "
        f"{msg.get('content')!r}."
    )


def await_request_json(request: Any) -> Any:
    """Synchronously extract JSON body from an in-process Starlette
    Request that has ``_body`` injected.

    Path E (per A.5.3.2-PR8-SPEC.md §4.5.4) injects the body
    bytes directly into ``request._body``. The driver-invoked
    chat_handler would normally await ``request.json()``; in
    tests, the captured Request needs JSON extraction without
    re-entering the asyncio loop.

    This helper reads ``_body`` directly (bypassing
    ``request.json()``'s async path), deserializes via json.loads.
    """
    import json as _json
    body_bytes = getattr(request, "_body", None)
    assert body_bytes is not None, (
        "Request._body was not set — the driver did not inject "
        "the body bytes via Path E."
    )
    return _json.loads(body_bytes)


# ── Public API drift guard — PR 8 Step 4 test 14 ─────────────────
#
# Per A.5.3.2-PR8-SPEC.md §3 risk #6 + §5.1 test 14: Q5 (`__all__`
# deferral) lock enforced mechanically. Neither emit_seed_expectation
# nor drive_seed_fixture enters forge_bridge.__all__ at PR 8.
# Public-API promotion routes through framing review at first
# concrete external consumer.


def test_pr8_helpers_remain_corpus_internal() -> None:
    """Risk #6 — `__all__` drift guard.

    Per A.5.3.2-PR8-SPEC.md §3 risk #6 + §5.1 test 14: asserts
    neither PR 8 helper enters forge_bridge.__all__; additionally
    asserts len(forge_bridge.__all__) == 19 (the v1.4.1 baseline
    count).

    Q5 lock per framing §5.6: each __all__ entry is authority-
    surface expansion. Silent promotion inside a cleanup PR is
    rejected at the spec layer; the public-API decision is
    deferred to first concrete external consumer.

    Counter-asserts protect against both targeted promotion
    (specific symbol added) and silent baseline drift (any other
    symbol changes the count).
    """
    assert "emit_seed_expectation" not in forge_bridge.__all__, (
        "Q5 (__all__ deferral) violation: emit_seed_expectation "
        "has been promoted to forge_bridge.__all__. Per "
        "A.5.3.2-PR8-FRAMING.md §5.6 + A.5.3.2-PR8-SPEC.md §2 "
        "out-of-scope #4, the public-API decision is deferred to "
        "first concrete external consumer. Revisit at framing "
        "time, not inside an unrelated cleanup PR."
    )
    assert "drive_seed_fixture" not in forge_bridge.__all__, (
        "Q5 (__all__ deferral) violation: drive_seed_fixture has "
        "been promoted to forge_bridge.__all__. See "
        "test_pr8_helpers_remain_corpus_internal failure message "
        "for emit_seed_expectation; same protection applies."
    )

    # Baseline count guard — protects against silent drift in
    # forge_bridge.__all__ membership (e.g., a different symbol
    # gets added/removed without the explicit Q5-relevant tests
    # firing).
    assert len(forge_bridge.__all__) == 19, (
        f"forge_bridge.__all__ baseline count drift detected.\n"
        f"Expected: 19 (the v1.4.1 baseline at PR 8 spec "
        f"drafting per A.5.3.2-PR8-SPEC.md §1 success condition).\n"
        f"Actual:   {len(forge_bridge.__all__)}\n"
        f"\n"
        f"Current __all__:\n"
        + "".join(f"  {s}\n" for s in sorted(forge_bridge.__all__))
        + "\n"
        f"If the count change is intentional (e.g., v1.5 public-"
        f"API expansion), update this assertion via spec "
        f"amendment per A.5.3.2-PR8-SPEC.md §7 phase-end "
        f"conditions. NOT acceptable as a cleanup-PR-layer "
        f"change."
    )
