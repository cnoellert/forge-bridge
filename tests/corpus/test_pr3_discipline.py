"""PR 3 — discipline grep test (I-4 / spec §10).

Verifies the load-bearing structural asymmetry that defines PR 3:
``forge_bridge.corpus`` is a real, callable package after PR 3 —
``emit_divergence_capture`` and ``read_capture_file`` are real
implementations — but no production code path imports it. The two
arbitration call sites land in PR 4 (chat handler) and PR 5 (chain
step). Until then, the writer is real but uncalled.

Same property held in PR 1 and PR 2 (verified at commit time in
each PR's commit message). PR 3 promotes the discipline check from
commit-time prose to executable test, because the asymmetry is more
fragile after the writer becomes real — the temptation to "just
wire up the chat handler quickly while we're here" is highest at
the moment the writer first works.

When this test starts failing on a future PR, that PR is either
PR 4/5 (in which case it should explicitly allowlist the
integration site, see spec §10.3) or it is a discipline regression
(in which case CI rejects it).
"""
from __future__ import annotations

from pathlib import Path

import forge_bridge


_FORBIDDEN_NEEDLES: tuple[str, ...] = (
    "from forge_bridge.corpus",
    "import forge_bridge.corpus",
)


def test_zero_production_imports_outside_corpus():
    """Walk the production package tree (excluding ``corpus/``
    itself) and assert no source file imports
    ``forge_bridge.corpus`` in any form.

    Test files (under ``tests/``) and the corpus package itself are
    deliberately excluded — the discipline applies to the
    *production code path*, which means code that runs in the
    daemon under normal operation.
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
            pass  # py is outside corpus_subtree — keep checking

        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # Skip pure-comment lines so doc references in comments
            # don't trip the discipline check (this matches §10.2:
            # "Documentation references are encouraged. The test
            # matches the literal from/import syntax only.").
            if stripped.startswith("#"):
                continue
            for needle in _FORBIDDEN_NEEDLES:
                if needle in line:
                    rel = py.relative_to(package_root)
                    offenders.append((str(rel), lineno, stripped))
                    break

    assert offenders == [], (
        "PR 3 discipline violated: forge_bridge.corpus is imported "
        "by production code path(s). Call-site integration belongs "
        "in PR 4 (chat handler) or PR 5 (chain step), not PR 3.\n"
        "Offenders:\n"
        + "\n".join(f"  {p}:{n}: {l}" for p, n, l in offenders)
    )
