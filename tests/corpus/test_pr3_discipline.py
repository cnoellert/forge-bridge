"""Discipline grep — bounded participation-creep boundary.

Originally landed in PR 3 as a *literal* "zero production imports of
``forge_bridge.corpus``" assertion. PR 4 transitions the test to
**allowlist mode**: each named integration call site is added
explicitly. Files not on the allowlist must still produce zero
imports.

The asymmetry doesn't disappear — it gets bounded. Per
``A.5.3.2-PR4-FRAMING.md`` §2:

  *"`handlers.py` is now an intentionally permitted observational
  emission surface. That truthful acknowledgment is healthier than
  pretending the asymmetry still literally means 'zero imports'.
  Bounded asymmetry, named explicitly, is more durable than literal
  asymmetry maintained by ignoring real integration."*

Allowlist contract (PR 4 framing §2):

- The test continues to walk the production tree.
- Files matching ``_ALLOWLIST`` are permitted to import
  ``forge_bridge.corpus``.
- Files not on ``_ALLOWLIST`` still produce zero imports.
- ``_ALLOWLIST`` growth is reviewable at the spec layer. Each
  future PR introducing a new corpus call site amends
  ``_ALLOWLIST`` by exactly one named entry, with spec amendment.

Other paths to make this test pass are rejected at the spec layer
(PR 4 framing §2):

- **Mocking the import out** — erodes mechanical visibility.
- **Removing the test** — bounded asymmetry is what protects
  against participation creep at unrelated call sites.
- **Inverting the test** — positive-only assertion on allowlisted
  files removes the negative across the rest of the tree.
"""
from __future__ import annotations

from pathlib import Path

import forge_bridge


_FORBIDDEN_NEEDLES: tuple[str, ...] = (
    "from forge_bridge.corpus",
    "import forge_bridge.corpus",
)

# Files explicitly permitted to import forge_bridge.corpus. Each
# entry is one named call-site integration.
#
# PR 4 added the chat-handler integration. PR 5 adds
# ``console/_step.py`` (chain-step integration) per
# A.5.3.2-PR5-SPEC.md §4.2. Growth is reviewable at the spec
# layer per A.5.3.2-PR4-FRAMING.md §2; each future PR
# introducing a new corpus call site must explicitly amend
# ``_ALLOWLIST`` and document the addition in its spec.
#
# Paths are relative to forge_bridge/ (the package root). They
# match the rglob form below — POSIX-style separators.
_ALLOWLIST: tuple[str, ...] = (
    "console/handlers.py",
    "console/_step.py",
)


def test_zero_production_imports_outside_corpus():
    """Walk the production package tree (excluding ``corpus/``
    itself and ``_ALLOWLIST`` entries) and assert no source file
    imports ``forge_bridge.corpus`` in any form.

    Test files (under ``tests/``) and the corpus package itself
    are deliberately excluded — the discipline applies to the
    *production code path*, which means code that runs in the
    daemon under normal operation.

    Allowlisted files are permitted to import the corpus emission
    path (``divergence_capture_enabled`` / ``emit_divergence_capture``
    / ``_capture``). Allowlist entries do not relax the
    participation-creep boundary — they are still subject to the
    narrowing-subsystem grep test in
    ``test_pr4_participation_creep.py``, which forbids importing
    any corpus module *other than* the emission path.
    """
    package_root = Path(forge_bridge.__file__).parent
    corpus_subtree = package_root / "corpus"

    offenders: list[tuple[str, int, str]] = []

    for py in package_root.rglob("*.py"):
        # Skip the corpus package itself — it imports itself freely.
        try:
            py.relative_to(corpus_subtree)
            continue
        except ValueError:
            pass

        rel = py.relative_to(package_root).as_posix()

        # Skip allowlisted integration sites.
        if rel in _ALLOWLIST:
            continue

        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # Skip pure-comment lines so doc references in comments
            # don't trip the discipline check (matches §10.2 of the
            # PR 3 spec: "Documentation references are encouraged.
            # The test matches the literal from/import syntax only.").
            if stripped.startswith("#"):
                continue
            for needle in _FORBIDDEN_NEEDLES:
                if needle in line:
                    offenders.append((rel, lineno, stripped))
                    break

    assert offenders == [], (
        "Discipline violated: forge_bridge.corpus is imported by "
        "production code path(s) NOT on the allowlist (currently: "
        f"{list(_ALLOWLIST)}).\n"
        "\n"
        "Either:\n"
        "  (a) the import is genuine integration — add the file to "
        "_ALLOWLIST with spec amendment, or\n"
        "  (b) the import was accidental — remove it.\n"
        "\n"
        "The bounded asymmetry is what protects against "
        "participation creep at unrelated call sites; mocking, "
        "removing, or inverting this test is rejected at the spec "
        "layer per A.5.3.2-PR4-FRAMING.md §2.\n"
        "\n"
        "Offenders:\n"
        + "\n".join(f"  {p}:{n}: {l}" for p, n, l in offenders)
    )
