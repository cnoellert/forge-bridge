"""PR-10-local Layer 2 read-only-interpretive authority discipline.

This module enforces the PR-10-local read-only-interpretive
authority discipline for ``forge_bridge/corpus/_compare.py``. The
discipline is mechanically enforced by two surfaces in this
module:

  1. ``_COMPARE_PERMITTED_IMPORTS`` — value-locked frozenset of
     ``forge_bridge.corpus.*`` symbols ``_compare.py`` is
     permitted to import. **Cardinality is exactly 0 at PR 10**
     — the comparator's reference implementation
     (``A.5.3.2-PR10-SPEC.md`` §4.1.6) uses string literals
     (``"observation"``, ``"expectation"``) for ``record_kind``
     comparison + dict-path traversal for field access; no
     ``forge_bridge.corpus`` imports are required. Test
     ``test_compare_permitted_imports_value_locked`` fires on
     any growth of the set.
  2. ``_compare_corpus_references`` AST walker — extracts every
     ``forge_bridge.corpus.<X>`` reference from
     ``forge_bridge/corpus/_compare.py`` source code. Test
     ``test_compare_module_references_subset_of_permitted_imports``
     fires on ``_compare.py`` acquiring a forbidden import.

The read-only-interpretive authority discipline is the
**zero-symbol-gate**: ``_compare.py`` imports zero corpus
symbols at PR 10. Admitting any symbol requires framing-level
review per ``A.5.3.2-PR10-SPEC.md`` §4.1.7 amendment trigger
language. The amendment evaluates whether the imported symbol
preserves read-only-interpretive authority (e.g., a universal-
truth-class lock like ``_KNOWN_RECORD_KINDS``) or erodes it
(e.g., emission helpers, persistence helpers, orchestration
surfaces — all rejected regardless of framing review).

PR 10 carrier sentences (verbatim, load-bearing — relevance-by-
file ordering per ``A.5.3.2-PR10-SPEC.md`` §4.2.2).

Active carrier #17 — recomposition discipline (Gate 3,
introduced at Gate 3 framing §5.1):

  Recomposition preserves authorship. The comparator joins
  observation + expectation records by fixture_id at read time;
  the join produces a derived view that names each authority
  surface's contribution explicitly. Cleanup pressure to
  collapse the three-authority-surface partition through
  interpretive synthesis is rejected at the spec layer.

Gate-3-LOCAL governing sentence — *candidate carrier #16
corroboration substrate* (Gate 3 framing §0 + §6.1; promotion
to active carrier #16 evaluated at Gate 3 close, NOT PR 10):

  Gate 3 proves topology, not infrastructure.

The sentence is the rejection key for the function-vs-subsystem
cleanup-pressure trap. The 4th walker is the canonical
operationalization of that trap's resistance at the Layer 2
import-discipline surface: a single-file value-locked walker
protecting a distinct ontology (read-only-interpretive
authority), not a parametrized base class generalized across
the three prior walkers' ontologies.

Four-walker partition (parallel-not-extension):

At PR 10 close, four Layer 2 AST walkers operate against the
codebase. Each protects a distinct ontology. The protections
are partitioned, not unified:

  - **PR 4 walker** (``test_pr4_participation_creep.py``) —
    protects PRODUCTION import topology: the narrowing-subsystem
    may not acquire corpus dependencies (one-directional flow).
    Target set: production source files. Rejection rule:
    one-directional flow.
  - **PR 8 walker** (``test_pr8_seed_surface.py``,
    ``_corpus_references`` + ``_SEED_PERMITTED_IMPORTS``) —
    protects orchestration participation discipline:
    ``_seed.py``'s own corpus-internal imports stay within the
    5-symbol bounded toolbox (semantics-not-cardinal per PR 8
    close §1.7). Target set: ``_seed.py``. Rejection rule:
    persistence-topology authority cannot leak into the seed-
    driver-internal scope.
  - **PR 9 walker** (``test_pr9_fixture_discipline.py``,
    ``_fixture_corpus_references`` + ``_FIXTURE_PERMITTED_IMPORTS``)
    — protects declarative fixture-data discipline: fixture
    modules under ``tests/corpus/fixtures/`` import nothing
    from the corpus beyond the single orchestration symbol
    (``drive_seed_fixture``). Target set: fixture directory
    glob. Rejection rule: single-symbol-gate.
  - **PR 10 walker** (this module,
    ``_compare_corpus_references`` + ``_COMPARE_PERMITTED_IMPORTS``)
    — protects read-only-interpretive authority:
    ``_compare.py`` imports zero corpus symbols. Target file:
    ``_compare.py``. Rejection rule: zero-symbol-gate at PR 10
    (framing amendment routes any symbol admission).

The four walkers share AST mechanics (each uses ``ast.walk`` +
import-node traversal); they do NOT share ontology.
Generalization would require unifying their target-set
semantics + their admission ontologies + their rejection-
message shapes + their future evolution pressure — which
collapses four protections into one rejection surface.

**Future "walker unification" cleanup proposals are rejected at
the spec layer** per ``A.5.3.2-PR10-SPEC.md`` §4.2.1 + Gate 2
close §1.6 + §2.4 item 5 + framing §3.3 + §8.2. A unified
walker abstraction is appealing locally (deduplication of AST
traversal code) but architecturally erodes four distinct
protections. Each walker stays local to its ontology.

**Shared AST mechanics do not imply shared ontology.**

Carriers carried by reference (not regenerated verbatim) per
spec §4.2.2 abbreviation discipline — the PR 10 walker module
is one layer removed from production authority emission;
carrier travel discipline here is reduced relative to
``_compare.py`` itself:

  - Inherited carriers #1–#15 (PR 4 + PR 5 + PR 6 + PR 8 +
    Gate 2 lineage). Canonical source:
    ``forge_bridge/corpus/_capture.py:6–135`` +
    ``forge_bridge/corpus/_seed.py:19–135`` +
    ``forge_bridge/corpus/_compare.py`` module docstring.
  - Gate 2 binding framing clarification — call-site-owned
    arbitration inputs.

PR-7-LOCAL pairs (§4.2 inert-parameter, §5.5 legacy-synthesis)
do NOT travel here — they remain scope-local to ``_capture.py``
+ ``reader.py``. PR-8-LOCAL binding statements (member #7
truth-partitioning, member #8 semantics-not-topology) do NOT
regenerate here — they remain scope-local to ``_seed.py`` +
``emit_seed_expectation``. PR-9-LOCAL fixture-data discipline
remains scope-local to ``tests/corpus/fixtures/`` + the PR 9
walker. PR-10-LOCAL binding statement (read-only mutability
invariant) is asserted by ``test_pr10_comparator.py`` test 4
mechanically; this discipline module does not repeat it. Per
``A.5.3.2-PR10-SPEC.md`` §0 PR-N-LOCAL non-regeneration rule.

This module operationalizes the Gate-3-LOCAL governing sentence
at the Layer 2 read-only-interpretive authority surface: the
frozenset value-locks at ZERO symbols (admitting any symbol
erodes the zero-symbol-gate; framing amendment discipline
applies per ``A.5.3.2-PR10-SPEC.md`` §4.1.7), and the walker
target is exclusively ``_compare.py`` (admitting any other
target would erode the parallel-not-extension protection).

See ``A.5.3.2-PR10-SPEC.md`` §4.2 + §5.1 + §6 for the contract
this module implements.
"""
from __future__ import annotations

import ast
import pathlib

import forge_bridge


# Layer 2 read-only-interpretive authority constant —
# value-locked at ZERO symbols at PR 10. Admission to this
# frozenset requires framing-level review per
# A.5.3.2-PR10-SPEC.md §4.1.7 amendment trigger language.
# The amendment evaluates whether the imported symbol preserves
# read-only-interpretive authority discipline (e.g., a
# universal-truth-class lock like _KNOWN_RECORD_KINDS —
# conditionally admitted if the implementation chooses
# set-membership validation over string-literal validation) or
# erodes it (e.g., emission helpers, persistence helpers,
# orchestration surfaces — rejected regardless of framing
# review).
_COMPARE_PERMITTED_IMPORTS: frozenset[str] = frozenset()


# Target file for the walker. Lives at module scope so the
# value-lock test + the subset-enforcement test share the same
# target reference. Single-file target preserves the
# parallel-not-extension boundary per A.5.3.2-PR10-SPEC.md
# §4.2.1: PR 4 walks production sources, PR 8 walks _seed.py,
# PR 9 walks the fixture directory glob, PR 10 walks _compare.py
# only.
_COMPARE_TARGET = pathlib.Path(
    forge_bridge.__file__
).parent / "corpus" / "_compare.py"


def _compare_corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified ``forge_bridge.corpus.<X>``
    reference imported by ``source``.

    Mirrors the AST mechanics of
    ``tests/corpus/test_pr8_seed_surface.py::_corpus_references``
    and
    ``tests/corpus/test_pr9_fixture_discipline.py::_fixture_corpus_references``
    — scoped to a different target (``_compare.py``) and a
    different protected ontology (read-only-interpretive
    authority vs. orchestration-participation vs. fixture-data-
    discipline). Shared AST mechanics do not imply shared
    ontology.

    Walks the AST for ``ImportFrom`` and ``Import`` nodes;
    records dotted symbol forms for any
    ``from forge_bridge.corpus.<submodule> import <symbol>``
    (the form ``_COMPARE_PERMITTED_IMPORTS`` would admit if it
    were nonempty) and any direct
    ``import forge_bridge.corpus.<submodule>``. Both syntactic
    forms are captured for completeness; at PR 10 close
    ``_compare.py`` carries zero ``forge_bridge.corpus.*``
    imports of either form, so both branches exercise vacuously.

    Returns a list of dotted strings — one per imported name or
    submodule. Comments and docstrings are not inspected (AST
    walks only ``Import`` / ``ImportFrom`` nodes), matching the
    "import-target, not text-occurrence" semantic the discipline
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


def test_compare_permitted_imports_value_locked() -> None:
    """Frozenset value-lock regression.

    The frozenset MUST equal exactly the empty frozenset::

        frozenset()

    Cardinality is exactly 0 at PR 10. Any future PR adding a
    symbol must amend the spec + framing first per
    ``A.5.3.2-PR10-SPEC.md`` §4.1.7 amendment trigger language
    — the zero-symbol-gate IS the read-only-interpretive
    authority discipline at PR 10. The test asserts both
    cardinality AND exact set membership.
    """
    expected: frozenset[str] = frozenset()
    assert _COMPARE_PERMITTED_IMPORTS == expected, (
        "_COMPARE_PERMITTED_IMPORTS has drifted from the "
        "A.5.3.2-PR10-FRAMING.md §5.5 + A.5.3.2-PR10-SPEC.md "
        "§4.1.7 zero-symbol-gate lock. Expected exactly zero "
        "symbols.\n"
        f"Actual ({len(_COMPARE_PERMITTED_IMPORTS)} elements):\n"
        + "".join(f"  {s}\n" for s in sorted(_COMPARE_PERMITTED_IMPORTS))
        + "Any admission of a symbol requires framing-level "
        "review per A.5.3.2-PR10-SPEC.md §4.1.7 amendment "
        "trigger language. The amendment evaluates whether the "
        "imported symbol erodes read-only-interpretive authority "
        "discipline (e.g., emission helpers, persistence "
        "helpers, orchestration surfaces — all rejected) vs. "
        "preserves it (e.g., a universal-truth-class lock like "
        "_KNOWN_RECORD_KINDS — conditionally admitted if the "
        "implementation chooses set-membership validation over "
        "string-literal validation)."
    )


def test_compare_module_references_subset_of_permitted_imports() -> None:
    """Walker subset-enforcement.

    ``forge_bridge/corpus/_compare.py`` is walked; every fully-
    qualified ``forge_bridge.corpus.<X>`` reference is collected;
    the collected set must be a SUBSET of
    ``_COMPARE_PERMITTED_IMPORTS`` (which is empty at PR 10).

    At PR 10 close: ``_compare.py`` carries zero
    ``forge_bridge.corpus.*`` imports (validation uses string
    literals + dict-path traversal per ``A.5.3.2-PR10-SPEC.md``
    §4.1.4 reference implementation). The subset-enforcement
    holds vacuously (empty set is a subset of the empty set),
    which is the correct shape at PR 10.

    A future PR adding ``from forge_bridge.corpus._schema import
    _KNOWN_RECORD_KINDS`` to ``_compare.py`` (e.g., to replace
    string-literal validation with set-membership validation)
    fails the walker. The implementer must amend
    ``_COMPARE_PERMITTED_IMPORTS`` to admit the symbol AND
    route through framing review per
    ``A.5.3.2-PR10-SPEC.md`` §4.1.7.

    A future PR adding ``from forge_bridge.corpus._capture
    import emit_divergence_capture`` (the canonical helper-
    merger cleanup-pressure form per
    ``A.5.3.2-PR10-FRAMING.md`` §3.6 form #1) fails the walker
    structurally — the comparator is read-only-interpretive
    authority; emission helpers are rejected regardless of
    framing review.
    """
    assert _COMPARE_TARGET.exists(), (
        f"_compare.py expected at {_COMPARE_TARGET}. The PR-10-"
        f"local read-only-interpretive authority discipline test "
        f"cannot enforce its boundary if the file it walks is "
        f"gone. Either restore the file or amend this test's "
        f"path."
    )
    source = _COMPARE_TARGET.read_text(encoding="utf-8")

    offenders: list[str] = []
    for ref in _compare_corpus_references(source):
        if ref not in _COMPARE_PERMITTED_IMPORTS:
            offenders.append(ref)

    assert not offenders, (
        "PR-10-local read-only-interpretive authority discipline "
        "violated: _compare.py imports a corpus surface OUTSIDE "
        "the permitted set.\n"
        "\n"
        "comparator is interpretive read-only authority; "
        "emission/persistence imports are rejected at the spec "
        "layer. The 4th walker preserves the three-walker "
        "partition's parallel-not-extension boundary — "
        "read-only-interpretive ontology is distinct from "
        "production-import-topology, orchestration-participation, "
        "and fixture-data-discipline ontologies. Shared AST "
        "mechanics do not imply shared ontology.\n"
        "\n"
        f"Permitted ({len(_COMPARE_PERMITTED_IMPORTS)} elements):\n"
        + "".join(f"  {p}\n" for p in sorted(_COMPARE_PERMITTED_IMPORTS))
        + "\n"
        "Offenders:\n"
        + "".join(f"  {ref}\n" for ref in offenders)
        + "\n"
        "If the import is genuinely required for validation "
        "(e.g., set-membership over _KNOWN_RECORD_KINDS), the "
        "admission decision is framing-level — route through "
        "framing review per A.5.3.2-PR10-SPEC.md §4.1.7 "
        "amendment trigger language. The amendment evaluates "
        "whether the imported symbol preserves read-only-"
        "interpretive authority or erodes it."
    )
