"""Capture and expose the daemon's install provenance.

Surfaced by `fbridge doctor` as an operational invariant: you should always
know what code the daemon is serving before interpreting behavioral
observations. The 24.6 + D-04 dogfood sessions established this — both
phases hit the dual-state condition where the daemon was running pre-edit
code while the on-disk source had advanced, and the only signal was
"the operator's natural request didn't get acted on."

Three distinct facts are exposed:

  startup_sha     git HEAD at the daemon's import-path repo, captured at
                  process start. NEVER changes after capture. Represents
                  the actual code the daemon's running interpreter holds.
  disk_sha_now    git HEAD at the same path, re-read on every call.
                  Represents the code that a *fresh* import would load.
  pid + started_at  process identity for cross-checking against
                  ps/launchctl/systemctl output.

The asymmetry between `startup_sha` (frozen) and `disk_sha_now` (live)
is load-bearing. When they disagree, the daemon's process holds stale
code relative to its own import path and needs a restart. This is the
single most diagnostically valuable comparison the provenance surface
makes, and the one that 24.6 + D-04 dogfood couldn't surface from any
other observability channel.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import forge_bridge

_GIT_TIMEOUT_SECS = 3


@lru_cache(maxsize=1)
def get_provenance() -> dict:
    """Return the daemon's startup-time install provenance snapshot.

    Cached for the process lifetime. The snapshot captures import path,
    containing git repo root (if any), git HEAD AT FIRST CALL, PID, and
    UTC ISO timestamp. Re-invocation returns the same dict.

    Keys that may be None: `repo_root`, `startup_sha`. These are None when
    the install path is not inside a git checkout (wheel install, system
    package, frozen bundle) or when git metadata is otherwise unavailable.
    Callers must treat None as "provenance unknown" and surface it to the
    operator rather than silently failing or fabricating a default.
    """
    pkg_file = Path(forge_bridge.__file__).resolve()
    import_path = str(pkg_file.parent)
    repo_root = _find_repo_root(pkg_file.parent)
    startup_sha = _git_head(repo_root) if repo_root else None
    return {
        "import_path": import_path,
        "repo_root": str(repo_root) if repo_root else None,
        "startup_sha": startup_sha,
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def current_disk_sha() -> Optional[str]:
    """Read git HEAD at the daemon's import-path repo NOW.

    Deliberately uncached — every call re-invokes git so the doctor can
    detect drift between the daemon's loaded code (startup_sha) and the
    current on-disk state. Returns None if the import path is not in a
    git repo or git invocation fails.
    """
    prov = get_provenance()
    repo_root = prov.get("repo_root")
    if not repo_root:
        return None
    return _git_head(Path(repo_root))


def _find_repo_root(start: Path) -> Optional[Path]:
    """Walk up from `start` looking for a `.git` directory or file.

    Worktree checkouts use a `.git` FILE (not a directory) that points at
    the main repo's gitdir — `Path.exists()` returns True for either form,
    which is correct for HEAD-resolution purposes.
    """
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _git_head(repo_root: Path) -> Optional[str]:
    """Return the current HEAD SHA at `repo_root`, or None on failure.

    Failure modes intentionally collapse to None: missing git binary, not
    a git repo, detached-HEAD with no commits yet, command timeout. Callers
    treat None uniformly as "provenance unknown" and surface that state.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None
