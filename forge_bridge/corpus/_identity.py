"""forge_bridge.corpus._identity — identity-hash helpers (PR 2 stub).

Three functions returning hex-encoded sha256 strings: narrower
version hash, registered-tools snapshot hash, daemon git SHA. See
``A.5.3.2-GATE-1-SPEC.md`` §3.4.

PR 1 status: stub. Implementation lands in PR 2.
"""
from __future__ import annotations

from typing import Any


def narrower_version_hash() -> str:
    """sha256 of ``_tool_filter.py`` source. Cached at import time.

    PR 1 stub: raises NotImplementedError. Implementation lands in
    PR 2.
    """
    raise NotImplementedError(
        "narrower_version_hash lands in PR 2."
    )


def registered_tools_snapshot_hash(tools: list[Any]) -> str:
    """sha256 of normalized sorted-tool-names + arg-schemas.

    PR 1 stub: raises NotImplementedError. Implementation lands in
    PR 2; the normalization rules are documented in that PR's
    landing.
    """
    raise NotImplementedError(
        "registered_tools_snapshot_hash lands in PR 2."
    )


def daemon_git_sha() -> str:
    """Full git sha of the running daemon's source tree.

    Returns the literal string ``'non-git'`` when not running from a
    git checkout.

    PR 1 stub: raises NotImplementedError. Implementation lands in
    PR 2.
    """
    raise NotImplementedError(
        "daemon_git_sha lands in PR 2."
    )
