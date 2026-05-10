"""tests.corpus.test_pr7_known_source_values — PR 7 Step 5 governance tests.

Locks the structural shape of ``forge_bridge/corpus/_sources.py``
post-§4.3 amendment: the constant is the canonical authority for
source-class governance (Gate 2 framing carrier #14), the module
is leaf governance (no imports from forge_bridge.corpus.*), and
the truth-vs-mechanism docstring framing is preserved.

See ``forge_bridge/corpus/_sources.py`` module docstring for the
14 inherited carriers + binding framing clarification (verbatim).
See ``A.5.3.2-PR7-SPEC.md`` §0 + §4.1 + §4.3 amendment for the
governance contract these tests enforce mechanically.

Step 5 lands these tests alongside the schema validator's
KNOWN_SOURCE_VALUES integration and the test migration that
removes the legacy "fixture" value from the production ontology.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Final, get_type_hints

import forge_bridge.corpus._sources as _sources_module
from forge_bridge.corpus._sources import KNOWN_SOURCE_VALUES


def test_constant_is_frozenset() -> None:
    """Step 5. Asserts ``KNOWN_SOURCE_VALUES`` is exactly the
    expected frozenset and typed as ``Final``.

    Pins the value: future renames (e.g., adding "fixture" back,
    removing "seed", adding a third value) surface here as a test
    failure forcing framing-level review per the protected-property
    contract in _sources.py's docstring (synchronous lockstep update
    of four downstream surfaces required).

    Per A.5.3.2-PR7-SPEC.md §4.3 amendment: "fixture" was removed
    from the schema's source-class governance; the production
    ontology is exactly {runtime, seed}. This test enforces that
    contract structurally.
    """
    assert KNOWN_SOURCE_VALUES == frozenset({"runtime", "seed"})
    assert isinstance(KNOWN_SOURCE_VALUES, frozenset)

    # Final[...] annotation is preserved on the module-level constant.
    # Reading via __annotations__ is the supported introspection path
    # for module-level Final declarations.
    annotations = getattr(_sources_module, "__annotations__", {})
    assert "KNOWN_SOURCE_VALUES" in annotations, (
        "KNOWN_SOURCE_VALUES must be annotated at module level "
        "(currently missing from __annotations__)."
    )
    # The annotation string contains "Final" — preserves the
    # immutability declaration even if the typing module's runtime
    # representation evolves across Python versions.
    annotation = annotations["KNOWN_SOURCE_VALUES"]
    annotation_repr = annotation if isinstance(annotation, str) else repr(annotation)
    assert "Final" in annotation_repr, (
        f"KNOWN_SOURCE_VALUES must be Final-annotated; "
        f"got annotation={annotation_repr!r}"
    )


def test_governance_docstring_present() -> None:
    """Step 5. Asserts the module docstring carries the
    truth-vs-mechanism governance markers.

    The docstring's "PROTECTED PROPERTY (truth)" + "MECHANISM"
    sections are load-bearing per A.5.3.2-PR7-SPEC.md §4.1 + the
    PR 6 close §1.3 truth-vs-mechanism distinction. They name the
    framing-level discipline that governs additions to the constant
    (synchronous update of four downstream surfaces in lockstep).

    Removing or renaming these sections would erode the structural
    backstop against silent ontology drift. Reject at CI; review
    surfaces the §4.1 binding text.
    """
    docstring = _sources_module.__doc__ or ""

    assert "PROTECTED PROPERTY (truth):" in docstring, (
        "_sources.py docstring must contain the "
        "'PROTECTED PROPERTY (truth):' marker per spec §4.1."
    )
    assert "MECHANISM (this file):" in docstring, (
        "_sources.py docstring must contain the "
        "'MECHANISM (this file):' marker per spec §4.1."
    )

    # The protected property names the four downstream surfaces
    # that must update in lockstep. Keeping the four-surface phrase
    # mechanically asserted protects against partial deletions of
    # the governance text. Whitespace-normalize the docstring so
    # multi-word phrases survive line wrapping.
    normalized = " ".join(docstring.split())
    assert "reader validation" in normalized
    assert "contextvar resolution path" in normalized
    assert "Gate 4 comparator" in normalized
    assert "lockstep" in normalized


def test_no_corpus_imports() -> None:
    """Step 5. Asserts ``_sources.py`` imports nothing from
    ``forge_bridge.corpus.*``.

    Leaf governance must remain a leaf: the constant + docstring
    is the artifact; introducing a corpus dependency here would
    create a cycle hazard and conflate the leaf-governance role
    with operational logic. Future readers + the post-§4.5-
    amendment discipline-test contract both depend on this
    structural property.

    The check parses the file's AST and inspects all
    ``Import`` / ``ImportFrom`` nodes — text-grep would miss
    aliased imports or string-quoted module references.
    """
    source_path = Path(_sources_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    forbidden_prefix = "forge_bridge.corpus"

    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == forbidden_prefix or module.startswith(
                forbidden_prefix + "."
            ):
                offenders.append(f"line {node.lineno}: from {module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == forbidden_prefix or alias.name.startswith(
                    forbidden_prefix + "."
                ):
                    offenders.append(
                        f"line {node.lineno}: import {alias.name}"
                    )

    assert offenders == [], (
        "_sources.py must not import from forge_bridge.corpus.*; "
        "leaf governance constant must remain a leaf. "
        f"Offenders:\n  " + "\n  ".join(offenders)
    )
