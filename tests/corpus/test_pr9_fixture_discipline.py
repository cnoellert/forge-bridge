"""PR-9-local Layer 2 fixture discipline.

This module enforces the PR-9-local fixture-data discipline for
``tests/corpus/fixtures/*.py``. The discipline is mechanically
enforced by two surfaces in this module:

  1. ``_FIXTURE_PERMITTED_IMPORTS`` — value-locked frozenset of
     ``forge_bridge.corpus.*`` symbols fixture modules are
     permitted to import. **Cardinality is exactly 1** —
     ``forge_bridge.corpus._seed.drive_seed_fixture`` is the sole
     admission. Test ``test_fixture_permitted_imports_locked_at_one_symbol``
     fires on growth, shrinkage, or substitution of the set.
  2. ``_fixture_corpus_references`` AST walker — extracts every
     ``forge_bridge.corpus.<X>`` reference from each fixture
     module under ``tests/corpus/fixtures/*.py`` (excluding
     ``__init__.py``). Test ``test_fixture_modules_references_subset_of_permitted_imports``
     fires on any fixture module acquiring a forbidden import.

The fixture-data discipline is the **single-symbol-gate**: fixture
modules are data + one orchestration call only (per cleanup-
pressure-resistance class member #9 — ``A.5.3.2-PR9-FRAMING.md``
§6.1). Admitting a second symbol to ``_FIXTURE_PERMITTED_IMPORTS``
or relaxing the walker's enforcement requires framing-level
review.

Three-walker partition (parallel-not-extension):

At PR 9 close, three Layer 2 AST walkers operate against the
codebase. Each protects a distinct ontology. The protections are
partitioned, not unified:

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
  - **PR 9 walker** (this module, ``_fixture_corpus_references``
    + ``_FIXTURE_PERMITTED_IMPORTS``) — protects declarative
    fixture-data discipline: fixture modules under
    ``tests/corpus/fixtures/`` import nothing from the corpus
    beyond the single orchestration symbol. Target set: fixture
    directory glob. Rejection rule: single-symbol-gate.

The three walkers share AST mechanics (each uses ``ast.walk`` +
import-node traversal); they do NOT share ontology.
Generalization would require unifying their target-set semantics
+ their admission ontologies + their rejection-message shapes +
their future evolution pressure — which collapses three
protections into one rejection surface.

**Future "walker unification" cleanup proposals are rejected at
the spec layer** per ``A.5.3.2-PR9-SPEC.md`` §4.6 + §7. A unified
walker abstraction is appealing locally (deduplication of AST
traversal code) but architecturally erodes three distinct
protections. Each walker stays local to its ontology.

**Shared AST mechanics do not imply shared ontology.**

PR 9 governing sentence (framing-artifact-scoped per
``A.5.3.2-PR9-FRAMING.md`` §0):

  PR 9 proves topology, not infrastructure.

This module operationalizes the governing sentence at the
Layer 2 fixture-discipline surface: the frozenset value-locks at
one symbol (admitting any second symbol would erode member #9's
single-symbol-gate protection); the walker target-set is the
fixture directory glob (admitting any other target would erode
the parallel-not-extension protection).

Carriers carried by reference from
``forge_bridge/corpus/_seed.py`` (canonical verbatim source):

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
  - #15 chat-handler-only seeding scope (PR 8) — most-relevant
    inherited governance for PR 9 fixture-discipline surface
    (per relevance-by-file ordering).
  - Binding framing clarification (Gate 2) — call-site-owned
    arbitration inputs.

PR-7-LOCAL pairs (§4.2 inert-parameter, §5.5 legacy-synthesis)
do NOT travel here — they remain scope-local to ``_capture.py``
+ ``reader.py``. PR-8-LOCAL binding statements (member #7
truth-partitioning, member #8 semantics-not-topology) do NOT
regenerate here — they remain scope-local to ``_seed.py`` +
``emit_seed_expectation``. Per ``A.5.3.2-PR9-SPEC.md`` §0
PR-N-LOCAL non-regeneration rule.

See ``A.5.3.2-PR9-SPEC.md`` §4.6 + §5.1 + §6 for the contract
this module implements.
"""
from __future__ import annotations

import ast
import pathlib


# Layer 2 fixture-discipline constant — value-locked at 1 symbol.
# Admission to this frozenset requires explicit framing-level
# review per cleanup-pressure-resistance class member #9
# (A.5.3.2-PR9-FRAMING.md §6.1). The single-symbol-gate IS the
# fixture-data discipline; admitting a second symbol erodes the
# protection. Future cleanup PRs proposing to admit
# emit_seed_expectation, seed_dispatch_scope, or any direct
# corpus-internal symbol are rejected at the spec layer per
# A.5.3.2-PR9-SPEC.md §2 out-of-scope #12 + §7 future-PR
# rejection table.
_FIXTURE_PERMITTED_IMPORTS: frozenset[str] = frozenset({
    "forge_bridge.corpus._seed.drive_seed_fixture",
})


# Target glob for the walker. Lives at module scope so test B can
# discover the file set + the value-lock test can document the
# scope. Excludes __init__.py (package marker, not a fixture
# module).
_FIXTURE_DIRECTORY = pathlib.Path(__file__).parent / "fixtures"


def _fixture_corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified ``forge_bridge.corpus.<X>``
    reference imported by ``source``.

    Mirrors the AST mechanics of
    ``tests/corpus/test_pr8_seed_surface.py::_corpus_references``
    — scoped to a different target-set (fixture modules vs.
    ``_seed.py``) and a different protected ontology (fixture-
    data discipline vs. seed-driver-internal participation
    discipline). Shared AST mechanics do not imply shared
    ontology.

    Walks the AST for ``ImportFrom`` and ``Import`` nodes; records
    dotted symbol forms for any
    ``from forge_bridge.corpus.<submodule> import <symbol>`` (the
    form ``_FIXTURE_PERMITTED_IMPORTS`` admits) and any direct
    ``import forge_bridge.corpus.<submodule>``. Direct submodule
    imports are expected to not appear in fixture modules at PR 9
    (fixtures import nothing); the walker captures them for
    completeness in case a future PR proposes
    ``import forge_bridge.corpus._seed as fb_seed`` syntax — that
    case is rejected by spec language (single-symbol-gate) but
    the walker captures it mechanically.

    Returns a list of dotted strings — one per imported name or
    submodule. Comments and docstrings are not inspected (AST
    walks only ``ImportFrom`` / ``Import`` nodes), matching the
    "import-target, not text-occurrence" semantic the discipline
    requires.
    """
    refs: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("forge_bridge.corpus"):
                for alias in node.names:
                    refs.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("forge_bridge.corpus"):
                    refs.append(alias.name)
    return refs


def test_fixture_permitted_imports_locked_at_one_symbol() -> None:
    """Frozenset value-lock regression.

    The frozenset MUST equal exactly::

        {"forge_bridge.corpus._seed.drive_seed_fixture"}

    Cardinality is exactly 1. Any future PR adding a second
    symbol must amend the spec + framing first (cleanup-pressure-
    resistance class member #9; A.5.3.2-PR9-FRAMING.md §6.1
    single-symbol-gate). The test asserts both cardinality AND
    exact set membership.
    """
    expected = frozenset({"forge_bridge.corpus._seed.drive_seed_fixture"})
    assert _FIXTURE_PERMITTED_IMPORTS == expected, (
        "_FIXTURE_PERMITTED_IMPORTS has drifted from the "
        "A.5.3.2-PR9-FRAMING.md §5.4 (Q4) lock. Expected exactly "
        "one symbol: forge_bridge.corpus._seed.drive_seed_fixture.\n"
        f"Actual ({len(_FIXTURE_PERMITTED_IMPORTS)} elements):\n"
        + "".join(f"  {s}\n" for s in sorted(_FIXTURE_PERMITTED_IMPORTS))
        + "Any admission of a second symbol requires framing-level "
        "review per cleanup-pressure-resistance class member #9 "
        "(A.5.3.2-PR9-FRAMING.md §6.1 single-symbol-gate)."
    )


def test_fixture_modules_references_subset_of_permitted_imports() -> None:
    """Walker subset-enforcement.

    Every Python file under ``tests/corpus/fixtures/`` (excluding
    ``__init__.py``) is walked; every fully-qualified
    ``forge_bridge.corpus.<X>`` reference is collected; the
    collected set must be a SUBSET of
    ``_FIXTURE_PERMITTED_IMPORTS``.

    At PR 9 close: fixture modules import nothing from
    ``forge_bridge.corpus`` (the FIXTURE constants are pure data
    delegated to ``drive_seed_fixture`` via the integration test,
    not via the fixture module itself). The subset-enforcement
    holds vacuously (empty set is a subset of any set), which is
    the correct shape at PR 9.

    At Step 1: the placeholder ``fix_single_survivor.py`` ships
    with the empty corpus-imports set; the walker passes
    vacuously. Step 2 fills in the real fixture content + adds
    the other two fixture modules; the walker continues to pass
    vacuously because the real content also carries no corpus
    imports (fixtures are data, not orchestration consumers).

    A future PR adding ``from forge_bridge.corpus._seed import
    drive_seed_fixture`` to a fixture module (e.g., to inline
    the driver invocation) passes the walker because
    ``drive_seed_fixture`` is the admitted symbol. A future PR
    adding any other corpus symbol import fails the walker.
    """
    fixture_files = sorted(
        f for f in _FIXTURE_DIRECTORY.glob("*.py") if f.name != "__init__.py"
    )
    assert len(fixture_files) >= 1, (
        f"Expected fixture modules under {_FIXTURE_DIRECTORY}; "
        f"found {len(fixture_files)}. PR 9 ships 3 fixture modules "
        "per A.5.3.2-PR9-FRAMING.md §5.3 (Q3); Step 1 ships 1 "
        "placeholder fixture module to satisfy this precondition."
    )

    offenders: list[tuple[str, list[str]]] = []
    for f in fixture_files:
        refs = _fixture_corpus_references(f.read_text())
        forbidden = [r for r in refs if r not in _FIXTURE_PERMITTED_IMPORTS]
        if forbidden:
            offenders.append((f.name, forbidden))

    assert not offenders, (
        "Fixture modules acquired forbidden corpus imports — "
        "violating cleanup-pressure-resistance class member #9 "
        "(fixture-surface-data-discipline; "
        "A.5.3.2-PR9-FRAMING.md §6.1) + Q4 single-symbol-gate "
        "Layer 2 discipline.\n"
        "Offenders:\n"
        + "".join(
            f"  {fname}:\n" + "".join(f"    {r}\n" for r in fbidn)
            for fname, fbidn in offenders
        )
        + f"\nPermitted ({len(_FIXTURE_PERMITTED_IMPORTS)} symbol):\n"
        + "".join(f"  {s}\n" for s in sorted(_FIXTURE_PERMITTED_IMPORTS))
        + "\nAny import beyond the single permitted symbol requires "
        "framing-level review (member #9 protection)."
    )
