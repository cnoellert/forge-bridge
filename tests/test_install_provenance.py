"""Tests for forge_bridge.install_provenance — daemon-side provenance capture.

Covers the snapshot/live asymmetry that is the module's load-bearing
contract: `get_provenance()` freezes at first call (startup_sha never
moves), while `current_disk_sha()` re-invokes git every call (catches
daemon-vs-disk drift).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from forge_bridge import install_provenance


@pytest.fixture(autouse=True)
def _clear_provenance_cache():
    """Reset the lru_cache between tests so each test sees a fresh snapshot."""
    install_provenance.get_provenance.cache_clear()
    yield
    install_provenance.get_provenance.cache_clear()


def test_get_provenance_returns_expected_keys():
    prov = install_provenance.get_provenance()
    assert set(prov.keys()) == {
        "import_path",
        "repo_root",
        "startup_sha",
        "pid",
        "started_at",
    }


def test_get_provenance_import_path_points_at_package_dir():
    prov = install_provenance.get_provenance()
    assert Path(prov["import_path"]).name == "forge_bridge"
    assert (Path(prov["import_path"]) / "__init__.py").exists()


def test_get_provenance_pid_is_current_process():
    import os

    prov = install_provenance.get_provenance()
    assert prov["pid"] == os.getpid()


def test_get_provenance_started_at_is_iso8601_utc():
    prov = install_provenance.get_provenance()
    # ISO8601 with timezone-suffix Z or +HH:MM
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$",
        prov["started_at"],
    )


def test_get_provenance_caches_first_call():
    """Two calls return the same dict object — proves lru_cache holds."""
    first = install_provenance.get_provenance()
    second = install_provenance.get_provenance()
    assert first is second


def test_get_provenance_in_git_repo_resolves_repo_root_and_sha():
    """When running inside the forge-bridge git checkout, repo_root and
    startup_sha must both be populated. This test asserts the happy path
    for the development environment."""
    prov = install_provenance.get_provenance()
    if prov["repo_root"] is None:
        pytest.skip("install path is not a git checkout (wheel/system install)")
    # repo_root should be a directory containing .git
    repo = Path(prov["repo_root"])
    assert (repo / ".git").exists()
    # startup_sha should be a 40-char hex string
    assert prov["startup_sha"] is not None
    assert re.match(r"^[0-9a-f]{40}$", prov["startup_sha"])


def test_current_disk_sha_matches_git_head_when_in_repo():
    """current_disk_sha() must agree with `git rev-parse HEAD` at the
    daemon's repo root — that IS its contract."""
    prov = install_provenance.get_provenance()
    if prov["repo_root"] is None:
        pytest.skip("install path is not a git checkout")
    expected = subprocess.run(
        ["git", "-C", prov["repo_root"], "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert install_provenance.current_disk_sha() == expected


def test_current_disk_sha_is_not_cached():
    """current_disk_sha() must NOT cache — it's the daemon-vs-disk drift
    detector and must re-read git every call. Verify by patching _git_head
    and asserting it's invoked on each call."""
    call_count = {"n": 0}

    def _spy(_repo_root):
        call_count["n"] += 1
        return "a" * 40

    with patch.object(install_provenance, "_git_head", side_effect=_spy):
        # Prime get_provenance with the spy so repo_root resolution succeeds
        # for tests where the install path IS a git repo
        prov = install_provenance.get_provenance()
        if prov["repo_root"] is None:
            pytest.skip("install path is not a git checkout")
        before = call_count["n"]
        install_provenance.current_disk_sha()
        install_provenance.current_disk_sha()
        install_provenance.current_disk_sha()
        assert call_count["n"] == before + 3


def test_find_repo_root_returns_none_for_non_repo(tmp_path):
    """A directory with no .git ancestor returns None."""
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    # tmp_path itself shouldn't be inside a git repo; if it is, we'd walk up
    # past it. Use a sentinel approach: just verify the walk terminates.
    result = install_provenance._find_repo_root(nested)
    # Either None (no .git anywhere up the tree) or some ancestor with .git
    # if tmp_path happens to live under a checkout. Both are valid; what we
    # care about is that the function terminates without raising.
    assert result is None or (result / ".git").exists()


def test_find_repo_root_finds_git_directory(tmp_path):
    """A .git directory (the standard case) is detected."""
    repo = tmp_path / "fake_repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    nested = repo / "deep" / "subdir"
    nested.mkdir(parents=True)
    assert install_provenance._find_repo_root(nested) == repo


def test_find_repo_root_finds_git_file(tmp_path):
    """Worktree checkouts use a .git FILE (pointer to gitdir). Must detect
    both directory-form and file-form."""
    repo = tmp_path / "fake_worktree"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /path/to/main/repo/.git/worktrees/foo\n")
    nested = repo / "deep"
    nested.mkdir()
    assert install_provenance._find_repo_root(nested) == repo


def test_git_head_returns_none_when_git_binary_missing():
    """If `git` is not on PATH, return None (do not raise)."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert install_provenance._git_head(Path("/tmp")) is None


def test_git_head_returns_none_on_nonzero_exit():
    """Non-zero exit (e.g. not a git repo, no commits yet) returns None."""
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=128, stdout="", stderr="fatal: not a git repo\n",
    )
    with patch("subprocess.run", return_value=fake_result):
        assert install_provenance._git_head(Path("/tmp")) is None


def test_git_head_returns_none_on_empty_stdout():
    """An empty SHA string collapses to None (defensive)."""
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="\n", stderr="",
    )
    with patch("subprocess.run", return_value=fake_result):
        assert install_provenance._git_head(Path("/tmp")) is None


def test_git_head_strips_whitespace_from_sha():
    """Real git output has a trailing newline; the SHA must be stripped."""
    sha = "a" * 40
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=f"{sha}\n", stderr="",
    )
    with patch("subprocess.run", return_value=fake_result):
        assert install_provenance._git_head(Path("/tmp")) == sha


def test_git_head_handles_timeout():
    """A hung git invocation returns None rather than raising."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=3)):
        assert install_provenance._git_head(Path("/tmp")) is None
