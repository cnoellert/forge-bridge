"""Participation-creep boundary — narrowing subsystem may import
ONLY the corpus emission path.

Per ``A.5.3.2-PR4-FRAMING.md`` §1.3 and ``A.5.3.2-PR4-SPEC.md`` §4.3:
the protected property is **one-directional observational flow**.
The narrower observes nothing about the corpus; the corpus observes
the narrower's decisions. Capture flows one direction only:
arbitration → capture → corpus. The reverse — corpus reads back
into arbitration — is the contract violation this test forbids
mechanically.

The test is implemented as a **positive list**, not a negative
denylist. Future corpus modules (Gate 4 comparator, replay-analysis
helpers, historical lookup, corpus-derived heuristic surfaces)
inherit the prohibition automatically — any new corpus module
surface that is NOT in ``_PERMITTED_CORPUS_IMPORTS`` is forbidden,
without the test needing edits. PRs introducing new corpus modules
carry the responsibility to extend this test ONLY when the new
module belongs in the emission path; otherwise the prohibition
extends silently and correctly.

Bounded asymmetry at the file level (``test_pr3_discipline.py``'s
allowlist) does NOT relax this boundary at the import-target level.
``handlers.py`` and ``_step.py`` are allowlisted to import the
corpus, but the narrowing subsystem (``_tool_filter.py`` and
``_step.py``) is independently constrained to the emission path
only. The two tests protect different properties.
"""
from __future__ import annotations

import ast
from pathlib import Path

import forge_bridge


# The narrowing subsystem source files. The participation-creep
# boundary is defined at this file level: these are the modules
# that perform arbitration, and they must never read from the
# corpus.
_NARROWING_SUBSYSTEM: tuple[str, ...] = (
    "console/_tool_filter.py",
    "console/_step.py",
)

# The ONLY corpus references the narrowing subsystem may import.
# Per A.5.3.2-PR4-SPEC.md §4.3:
#
#   "The narrowing subsystem may import ONLY the emission path.
#   Any other corpus module surface — reader, comparator (Gate 4),
#   replay-analysis helpers, historical lookup, corpus-derived
#   heuristic surfaces — is a participation-creep boundary
#   violation."
#
# Two reference shapes are permitted:
#   (a) the emission submodule itself: forge_bridge.corpus._capture
#   (b) the public-API names re-exported through the package:
#       forge_bridge.corpus.divergence_capture_enabled
#       forge_bridge.corpus.emit_divergence_capture
#
# The test inspects what's actually imported, not just the module
# path — `from forge_bridge.corpus import emit_divergence_capture`
# is permitted, but `from forge_bridge.corpus import
# read_capture_file` is rejected even though both come "via the
# top-level package."
_PERMITTED_CORPUS_IMPORTS: frozenset[str] = frozenset({
    "forge_bridge.corpus._capture",
    "forge_bridge.corpus.divergence_capture_enabled",
    "forge_bridge.corpus.emit_divergence_capture",
})


def _corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified ``forge_bridge.corpus.<X>``
    reference imported by ``source``.

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
                # `from forge_bridge.corpus import X, Y` —
                # each imported name is a corpus reference.
                for alias in node.names:
                    refs.append(f"forge_bridge.corpus.{alias.name}")
            elif module.startswith("forge_bridge.corpus."):
                # `from forge_bridge.corpus.X import Y` —
                # the submodule itself is the reference.
                refs.append(module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    alias.name == "forge_bridge.corpus"
                    or alias.name.startswith("forge_bridge.corpus.")
                ):
                    refs.append(alias.name)
    return refs


def test_narrowing_subsystem_imports_zero_corpus_modules_except_capture():
    """Walk ``_tool_filter.py`` and ``_step.py``; assert every
    ``forge_bridge.corpus.<X>`` reference is in
    ``_PERMITTED_CORPUS_IMPORTS``.

    A failure means the narrowing subsystem has acquired a
    forbidden corpus dependency. Per
    ``A.5.3.2-PR4-FRAMING.md`` §1.3, the protected property is
    one-directional observational flow: arbitration → capture →
    corpus, never the reverse.
    """
    package_root = Path(forge_bridge.__file__).parent

    offenders: list[tuple[str, str]] = []

    for rel in _NARROWING_SUBSYSTEM:
        path = package_root / rel
        assert path.exists(), (
            f"narrowing-subsystem source missing: {rel}. The "
            f"participation-creep test cannot enforce its boundary "
            f"if the file it walks is gone. Either restore the file "
            f"or amend _NARROWING_SUBSYSTEM."
        )
        source = path.read_text(encoding="utf-8")
        for ref in _corpus_references(source):
            if ref not in _PERMITTED_CORPUS_IMPORTS:
                offenders.append((rel, ref))

    assert offenders == [], (
        "Participation-creep boundary violated: the narrowing "
        "subsystem imports a corpus surface OUTSIDE the emission "
        "path.\n"
        "\n"
        "Permitted (emission path only):\n"
        + "".join(
            f"  {p}\n" for p in sorted(_PERMITTED_CORPUS_IMPORTS)
        )
        + "\n"
        "Offenders:\n"
        + "".join(f"  {f}: {ref}\n" for f, ref in offenders)
        + "\n"
        "Per A.5.3.2-PR4-FRAMING.md §1.3, the protected property "
        "is one-directional observational flow. The narrower "
        "observes nothing about the corpus; the corpus observes "
        "the narrower's decisions. The reverse — corpus reads "
        "back into arbitration — is the contract violation this "
        "test forbids mechanically.\n"
        "\n"
        "If the import is genuinely an emission-path addition, "
        "amend _PERMITTED_CORPUS_IMPORTS with spec amendment. If "
        "the import is a reader / comparator / replay-analysis / "
        "historical-lookup / corpus-derived heuristic, the import "
        "belongs in a Layer 2 surface, NOT the narrowing subsystem."
    )
