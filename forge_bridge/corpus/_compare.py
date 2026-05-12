"""forge_bridge.corpus._compare — comparator helper for divergence
between authored expectation and observed arbitration records.

This module is the **read-only-interpretive authority** surface of
the corpus package. It consumes one observation record + one
expectation record (both pre-read by the caller from corpus
persistence), validates their joinability through authority-class
pre-checks, and produces a structured ``DivergenceReport`` dict
preserving each authority surface's authored contribution
explicitly.

The comparator is a **leaf consumer**. It is structurally incapable
of mutating its inputs, triggering upstream emission, persisting
state, or holding state across calls. These properties are
protected at three layers: type signature, module imports (Layer 2
4th walker), and function body discipline (PR-10-LOCAL binding
statement asserted by tests).

PR 10 carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR10-SPEC.md`` §0).

Relevance-by-file ordering at this module: carrier #17 +
Gate-3-LOCAL governing sentence + proactive scope guardrail +
PR-10-LOCAL binding statement + cross-surface unbinding
clarification land at the TOP of the carrier block per spec
§4.1.1. Inherited carriers #1–#15 + Gate 2 binding framing
clarification land after.

Active carrier #17 — recomposition discipline (Gate 3, introduced
at Gate 3 framing §5.1):

  Recomposition preserves authorship. The comparator joins
  observation + expectation records by fixture_id at read time;
  the join produces a derived view that names each authority
  surface's contribution explicitly. Cleanup pressure to collapse
  the three-authority-surface partition through interpretive
  synthesis is rejected at the spec layer.

Gate-3-LOCAL governing sentence — candidate carrier #16
corroboration substrate (Gate 3 framing §0 + §6.1; promotion to
active carrier #16 evaluated at Gate 3 close, NOT PR 10):

  Gate 3 proves topology, not infrastructure.

This sentence travels with explicit *candidate carrier #16
corroboration substrate* marking. PR 10 must not write "17 active
carriers" or "carriers #1–#17" — correct phrasing is "16 active
carriers + candidate #16."

Proactive scope guardrail (Gate 3 framing §2.3 + PR 10 framing
§3.5):

  The comparator compares authored expectation records against
  observed arbitration records within a single operational
  arbitration surface.

(NOT "logical prompts," NOT "semantic tasks," NOT "cross-surface
executions.")

PR-10-LOCAL binding statement — read-only mutability invariant
(PR 10 framing §5.6):

  The comparator function is structurally incapable of mutating
  its inputs or producing side effects. The signature returns a
  new structured value; the inputs are read but never modified;
  no I/O is invoked; no module-level state is held across calls.
  Tests assert input records remain byte-identical after the
  function returns.

Binding framing clarification — cross-surface unbinding (Gate 3
framing §6.2):

  The comparator's authority is bounded to within-surface
  divergence between authored expectation and observed
  arbitration outcome for a single operational arbitration
  surface. Cross-surface comparator semantics are intentionally
  unbound pending dedicated framing review.

The language is **deferral, not rejection** (per
``feedback_explicitly_unbound_vs_implicitly_rejected``). Cross-
surface comparator semantics may eventually surface; PR 10 does
not foreclose them by spec language; PR 10 does not implement
them.

Inherited carriers #1–#15 + binding framing clarification on
call-site-owned arbitration inputs (verbatim). Canonical
production-truth source: ``forge_bridge/corpus/_capture.py:6–135``
+ ``forge_bridge/corpus/_seed.py:19–135``.

Inherited carriers #1–#2 — risk-category shift (PR 4):

  PR 4 is the controlled introduction of observational
  side-effects into live arbitration surfaces.

  The risk category has shifted from persistence-substrate risk
  to participation-creep risk.

Inherited carriers #3–#6 — integration-discipline quartet (PR 4):

  The call site is the source of the three explicit inputs.

  The integration layer passes truth.

  The integration layer never reconstructs truth.

  The builder does not discover runtime state.

Inherited carrier #7 — finalized-state contract (PR 4):

  Capture emission occurs only after arbitration state is
  finalized for the current execution path. Capture records
  completed arbitration observations, not provisional
  intermediate state.

Inherited carrier #8 — risk-inheritance + surface-geometry
distinction (PR 5):

  PR 5 is the second call site under the integration discipline
  PR 4 established. The risk profile is inherited; the surface
  geometry is not.

Inherited carrier #9 — caller's view of deployment identity
(PR 5):

  The chain-step's deployment identity is the caller's view, not
  the global daemon registry view.

Inherited carrier #10 — ambiguity-as-arbitration-outcome (PR 5):

  Ambiguity rejection is an arbitration outcome. Capture must
  record it. At this surface, ``narrower_decision`` carries the
  filtered list verbatim at narrowing finalization — including
  zero-match and multi-match rejection paths.
  ``pr20_condition_met`` is always False and ``collapse_occurred``
  is False on all rejection paths. These semantics differ from
  the chat-handler case and must not be silently overloaded.

Inherited carrier #11 — measured-not-inferred coverage (PR 5):

  No-dependency coverage at the chain-step surface must be
  measured, not inferred. The existing probe drives only the
  chat-handler single-step path; PR 5 owns the responsibility
  to extend coverage to the chain-step path empirically.

Inherited carrier #12 — structural-backstop framing (PR 6):

  PR 6 is the structural backstop for the visual-asymmetry
  pattern. The lint validates shape, not content; structure, not
  interpretation. Carrier content is the room's job; field
  validation is the helper signature's job; the lint validates
  the visual asymmetry between arbitration and observation.

Inherited carrier #13 — observation-not-participation framing
(PR 6):

  The lint operates by observation, not by participation. It
  reads source files; it does not import the corpus package. The
  lint's own scope is the same one-directional observational
  flow the call sites enforce.

Inherited carrier #14 — declared epistemic class vs. persisted
provenance (Gate 2):

  Property C governs the epistemic class declared at the
  observation boundary. KNOWN_SOURCE_VALUES governs persisted
  provenance classes after contextual annotation has been
  resolved.

Inherited carrier #15 — chat-handler-only seeding scope (PR 8):

  PR 8 seeds the chat-handler observation surface only. Chain-
  step seeding is explicitly deferred because ``handlers.py``
  and ``_step.py`` produce semantically distinct observation
  records. Cross-surface expectation semantics require a
  dedicated framing pass before implementation proceeds.

Carrier #15 is the operational ancestor of carrier #17's
"three-authority-surface partition" governance — both reject
silent collapse of semantically distinct authority surfaces.

Binding framing clarification — call-site-owned arbitration
inputs (Gate 2):

  Arbitration-state fields remain call-site-owned explicit
  inputs. Dispatch provenance is contextual metadata derived at
  emission time and does not participate in arbitration
  semantics.

PR-N-LOCAL non-regeneration note (Gate 2 framing §3.1 +
``A.5.3.2-PR10-SPEC.md`` §0):

  The PR-7-LOCAL binding pairs (§4.2 inert-parameter, §5.5
  legacy-synthesis) remain scope-local to ``_capture.py`` +
  ``reader.py``. The PR-8-LOCAL binding statements (member #7
  truth-partitioning, member #8 semantics-not-topology) remain
  scope-local to ``_seed.py`` + ``emit_seed_expectation``. The
  PR-10-LOCAL binding statement above is scope-local to this
  module + ``compare_records`` + PR 10 test modules; future PR /
  Gate work does not inherit it unless re-stated at framing
  level.

See ``A.5.3.2-PR10-SPEC.md`` §4.1 for the contract this module
implements + the seven symbol-level decisions locked at spec
time. See ``A.5.3.2-PR10-FRAMING.md`` §0 for the crystallizing
pair (carrier #17 + Gate-3-LOCAL form) this module enacts.
"""
from __future__ import annotations

from typing import Any, TypeAlias


# ── DivergenceReport — per-surface nested dict shape preserving authorship ──
#
# Structural posture: option (a) per PR 10 framing §4.3 — per-
# surface nested dict. The three sub-dict keys (``expectation``,
# ``observation``, ``divergence``) structurally enforce the three-
# authority-surface partition per carrier #17. The ``divergence``
# key's value is the comparator's interpretive claim; the
# ``expectation`` and ``observation`` keys' values are the surface
# contributions the claim is derived from.
#
# The TypeAlias resolves to plain ``dict[str, Any]`` — no typing
# enforcement beyond the IDE-discoverability of the alias name.
# Future contributors proposing to tighten the alias into a
# ``TypedDict`` or ``Protocol`` are rejected at the spec layer per
# PR 10 framing §4.3 (c)-rejection + carrier #17 (the typing
# ceremony doesn't add protection; the field-naming discipline +
# the function-body construction discipline + the unit tests are
# what enforce the shape).


DivergenceReport: TypeAlias = dict[str, Any]
"""Per-surface nested dict shape preserving authorship.

Structural shape (verbatim — exact field names are part of the
contract per ``A.5.3.2-PR10-SPEC.md`` §4.1.4):

    {
        "fixture_id": str,
        "expectation": {
            "expected_narrow": list[str],
        },
        "observation": {
            "observed_narrow": list[str],
        },
        "divergence": {
            "narrow_diverged": bool,
        },
    }

Field-naming discipline (load-bearing):

  - The ``expectation.*`` and ``observation.*`` sub-dicts use the
    prefix discipline ``expected_*`` / ``observed_*`` for the
    surface contribution field. Symmetric naming makes the
    per-surface partition structurally visible at the field-name
    level AS WELL AS the dict-structure level (double redundancy
    of carrier #17 protection).
  - The ``divergence.*`` sub-dict uses the suffix discipline
    ``*_diverged`` for the comparator's interpretive claims. The
    prefix asymmetry between surface contributions
    (``expected_`` / ``observed_``) and comparator claims
    (``*_diverged``) makes the authority-class distinction
    structurally visible.
  - No cross-surface vocabulary. Field names like
    ``task_outcome``, ``prompt_resolution``, ``semantic_match``
    are rejected per proactive scope guardrail above.

The lists inside ``expectation.expected_narrow`` and
``observation.observed_narrow`` are FRESH allocations (per the
§4.1.6 implementation discipline — fresh ``list(...)`` copies
of the source field values). Mutation of the report does not
propagate back into the input records.
"""


class ComparatorInputError(ValueError):
    """Raised when caller misuses the comparator's authority-class
    contract.

    The comparator validates seven authority-class boundaries at
    entry (per ``A.5.3.2-PR10-SPEC.md`` §4.1.5):

      1. ``observation_record`` must be a ``dict``.
      2. ``expectation_record`` must be a ``dict``.
      3. ``observation_record["record_kind"] == "observation"``.
      4. ``expectation_record["record_kind"] == "expectation"``.
      5. ``observation_record["fixture_id"] ==
         expectation_record["fixture_id"]`` (both non-None).
      6. ``observation_record["narrower"]["decision"]`` exists +
         is a list.
      7. ``expectation_record["expected_narrow"]`` exists + is a
         list.

    Any of these failing raises ``ComparatorInputError``. The
    exception subclasses ``ValueError`` so callers catching
    ``ValueError`` for general input-validation reasons get this
    one too; subclassing lets discriminating callers catch the
    comparator-specific case explicitly.

    Distinct from
    ``forge_bridge.corpus._schema.SchemaValidationError``: the
    schema validator enforces *whether a record is a structurally
    valid record* (universal keys + record_kind-conditional
    fields); ``ComparatorInputError`` enforces *whether the
    caller passed records of the correct authority class to the
    comparator function*. The records may be schema-valid yet
    still misused at the comparator (right schema, wrong
    authority class for the parameter — e.g., two observation
    records passed where the comparator expects an observation +
    expectation pair).

    Future contributors must not collapse ``ComparatorInputError``
    into ``SchemaValidationError`` or vice versa — the two
    enforce different boundaries and the comparator's boundary is
    authority-class, not schema. Distinct exception types
    preserve the discriminability at the catch-site.
    """


def compare_records(
    observation_record: dict,
    expectation_record: dict,
) -> DivergenceReport:
    """Compare a single observation record against its companion
    expectation record. Return a structured divergence report
    naming each authority surface's contribution explicitly.

    Carrier #17 verbatim (Gate 3, recomposition discipline):

      Recomposition preserves authorship. The comparator joins
      observation + expectation records by fixture_id at read
      time; the join produces a derived view that names each
      authority surface's contribution explicitly. Cleanup
      pressure to collapse the three-authority-surface partition
      through interpretive synthesis is rejected at the spec
      layer.

    Proactive scope guardrail (Gate 3 framing §2.3 + PR 10
    framing §3.5):

      The comparator compares authored expectation records
      against observed arbitration records within a single
      operational arbitration surface.

    §4.2 binding behavioral commitment — "compare as persisted"
    (PR 10 framing §4.2):

      The comparator compares authored and observed records as
      persisted. It does not normalize, reorder, canonicalize,
      repair, or semantically coerce either surface before
      comparison.

    Four operational rejections this commitment makes explicit:

      - The comparator does NOT sort ``narrower.decision`` or
        ``expected_narrow`` before comparing — order is
        meaningful observation/expectation; reordering masks
        divergence.
      - The comparator does NOT lowercase tool names, strip
        whitespace, or apply any string canonicalization — those
        are surface-authorship details preserved.
      - The comparator does NOT "repair" missing fields, fill
        defaults, or infer absent values — missing data is a
        validation failure, not a silent normalization.
      - The comparator does NOT compare semantically — comparison
        is byte-for-byte structural on the persisted record
        contents.

    PR-10-LOCAL binding statement — read-only mutability
    invariant (PR 10 framing §5.6):

      The comparator function is structurally incapable of
      mutating its inputs or producing side effects. The
      signature returns a new structured value; the inputs are
      read but never modified; no I/O is invoked; no module-
      level state is held across calls. Tests assert input
      records remain byte-identical after the function returns.

    Args:
        observation_record: a dict with
            ``record_kind == "observation"`` — the runtime
            observation authored by ``emit_divergence_capture``
            under ``seed_dispatch_scope``. Must contain
            ``record_kind="observation"``, a non-None
            ``fixture_id``, and a ``narrower`` sub-dict carrying
            ``decision`` (list[str]).
        expectation_record: a dict with
            ``record_kind == "expectation"`` — the authored
            expectation declared by ``emit_seed_expectation``.
            Must contain ``record_kind="expectation"``, a
            non-None ``fixture_id`` equal to
            ``observation_record["fixture_id"]``, and
            ``expected_narrow`` (list[str]).

    Returns:
        A ``DivergenceReport`` (typed alias for
        ``dict[str, Any]``) with the four-key structural shape
        (``fixture_id``, ``expectation``, ``observation``,
        ``divergence``) preserving authorship. The lists inside
        ``expectation.expected_narrow`` and
        ``observation.observed_narrow`` are FRESH allocations —
        mutation of the report does not propagate back into the
        input records.

    Raises:
        ComparatorInputError: on any of the seven authority-class
            boundary violations enumerated in
            ``ComparatorInputError``'s docstring (records not
            dicts, wrong ``record_kind``, ``fixture_id``
            mismatch or None, missing required fields, wrong
            field types).
    """
    raise NotImplementedError(
        "compare_records body lands at Step 3 per "
        "A.5.3.2-PR10-SPEC.md §6"
    )
