"""forge_bridge.corpus._identity — identity-hash helpers.

Three functions returning identity strings:

  - ``narrower_version_hash()``     → sha256 of ``_tool_filter.py`` source
  - ``registered_tools_snapshot_hash(tools)`` → sha256 of normalized
                                                 sorted-tools + schemas
  - ``daemon_git_sha()``            → 40-char git SHA, or ``"non-git"``

Preserved invariants (carry through any future change to this module):

  1. **Descriptive, not evaluative.** Hashes record state snapshots —
     identity/version pairs. Do NOT invent compatibility grades,
     equivalence classes, drift scoring. Those are Layer 2 derived
     judgments.

  2. **Observational, not semantic.** Two records with the same
     ``narrower_version_hash`` ran against byte-identical narrower
     source. Two records with different hashes ran against different
     source. Whether those differences are *meaningful* is not this
     module's question.

  3. **No lazy runtime side effects.** Must not initialize providers,
     warm clients, allocate transports, touch arbitration state,
     spawn background tasks, or mutate caches into warm-state
     preparation. Lazy-cached file reads and a one-shot subprocess
     for git SHA are permitted; they are not runtime preparation.

  4. **Loud asymmetry preserved.** Identity working without replay
     is correct. The writer remains deferred to PR 3 specifically
     because the architectural pressure to fuse observation with
     persistence is highest at this moment.

Caching approach:

  - ``narrower_version_hash`` and ``daemon_git_sha`` are lazy-cached.
    First call computes; subsequent calls return the cached value
    with no I/O. The caches are process-local (module globals),
    intentional and documented; tests reset them via the
    ``clean_identity_caches`` fixture in ``tests/corpus/conftest.py``.
  - ``registered_tools_snapshot_hash`` is a pure function over its
    input — no caching, since inputs vary per call. Determinism comes
    from sorted, key-ordered JSON serialization (see
    ``_NORMALIZATION_VERSION`` and the inline normalization code).
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Normalization rule version. Bump if the rules below change in a way
# that would alter the hash for an unchanged input. Each version is a
# spec-level commitment: hashes from version N are not comparable to
# hashes from version N+1 even for identical inputs.
_NORMALIZATION_VERSION = 1

# Lazy-cached results — process-local, intentional. See module docstring.
_narrower_hash_cache: str | None = None
_daemon_git_sha_cache: str | None = None


def narrower_version_hash() -> str:
    """sha256 of ``forge_bridge/console/_tool_filter.py`` contents.

    Computed lazily on the first call and cached. Subsequent calls
    return the cached value with no I/O. The cache is process-local;
    tests reset via ``tests/corpus/conftest.py::clean_identity_caches``.
    """
    global _narrower_hash_cache
    if _narrower_hash_cache is None:
        from forge_bridge.console import _tool_filter

        path = Path(_tool_filter.__file__)
        _narrower_hash_cache = hashlib.sha256(path.read_bytes()).hexdigest()
    return _narrower_hash_cache


def registered_tools_snapshot_hash(tools: list[Any]) -> str:
    """sha256 of a normalized representation of registered tools.

    Pure function — no caching, since inputs vary per call.

    Normalization (v1):
      - Each tool reduced to ``{"name": <str>, "inputSchema": <dict>}``.
        Other Tool attributes (description, annotations, etc.) are
        deliberately NOT included; the contract is "name + arg schema",
        because a docstring change should not change the hash.
      - Tools sorted by name. Order-independence — same tool set in
        different orders produces the same hash.
      - JSON serialization with ``sort_keys=True`` and compact
        separators. Whitespace and key ordering are deterministic.
      - sha256 over UTF-8 bytes of the serialized representation.

    Bumping ``_NORMALIZATION_VERSION`` (above) is required if any of
    these rules change. Hashes from different versions are not
    comparable.
    """
    normalized: list[dict[str, Any]] = []
    for t in tools:
        name = getattr(t, "name", None)
        schema = getattr(t, "inputSchema", None) or {}
        normalized.append({
            "name": name,
            "inputSchema": schema,
        })
    normalized.sort(key=lambda x: x["name"] or "")
    body = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def daemon_git_sha() -> str:
    """Full git sha of the running daemon's source tree.

    Returns the literal string ``'non-git'`` when not running from a
    git checkout, or when the subprocess fails for any reason
    (timeout, missing git binary, detached worktree, etc.).

    Computed lazily on the first call and cached. The cache is
    process-local; tests reset via ``clean_identity_caches``.
    """
    global _daemon_git_sha_cache
    if _daemon_git_sha_cache is None:
        _daemon_git_sha_cache = _compute_git_sha()
    return _daemon_git_sha_cache


def _compute_git_sha() -> str:
    """Internal: run ``git rev-parse HEAD`` from the package's checkout.

    Anchors on the package's own file location so it works regardless
    of the daemon's working directory. Any failure mode returns
    ``"non-git"`` cleanly.
    """
    try:
        cwd = Path(__file__).resolve().parent
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            timeout=2,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return "non-git"
        sha = result.stdout.strip()
        if len(sha) == 40 and all(
            c in "0123456789abcdef" for c in sha
        ):
            return sha
        return "non-git"
    except Exception as exc:  # noqa: BLE001 — never break callers
        logger.debug("daemon_git_sha computation failed: %s", exc)
        return "non-git"


def _reset_caches_for_tests() -> None:
    """Test affordance — clear lazy caches so tests can exercise the
    first-call path. Used by ``clean_identity_caches`` fixture."""
    global _narrower_hash_cache, _daemon_git_sha_cache
    _narrower_hash_cache = None
    _daemon_git_sha_cache = None
