from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-commit"
INSTALLER = ROOT / "scripts" / "install-git-hooks.sh"


def _git(repo: Path, *args: str, env: dict[str, str] | None = None):
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture
def hooked_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "-b", "main").returncode == 0
    assert _git(repo, "config", "user.name", "Hook Test").returncode == 0
    assert _git(repo, "config", "user.email", "hook@example.invalid").returncode == 0

    hooks = repo / ".githooks"
    hooks.mkdir()
    copied = hooks / "pre-commit"
    shutil.copy2(HOOK, copied)
    copied.chmod(0o755)
    assert _git(repo, "config", "core.hooksPath", ".githooks").returncode == 0

    (repo / "README.md").write_text("initial\n", encoding="utf-8")
    assert _git(repo, "add", "README.md").returncode == 0
    assert _git(repo, "commit", "-m", "initial").returncode == 0
    assert _git(repo, "checkout", "-b", "feature").returncode == 0
    return repo


def _stage_planning_file(repo: Path) -> None:
    planning = repo / ".planning"
    planning.mkdir(exist_ok=True)
    (planning / "NOTE.md").write_text("plan\n", encoding="utf-8")
    assert _git(repo, "add", ".planning/NOTE.md").returncode == 0


def test_planning_only_commit_is_blocked_off_main(hooked_repo: Path):
    _stage_planning_file(hooked_repo)

    result = _git(hooked_repo, "commit", "-m", "planning")

    assert result.returncode != 0
    assert "Planning-only commit blocked on branch 'feature'" in result.stderr
    assert "ALLOW_PLANNING_OFF_MAIN=1" in result.stderr


def test_explicit_override_allows_planning_commit(hooked_repo: Path):
    _stage_planning_file(hooked_repo)
    env = dict(os.environ, ALLOW_PLANNING_OFF_MAIN="1")

    result = _git(hooked_repo, "commit", "-m", "intentional planning", env=env)

    assert result.returncode == 0, result.stderr


def test_planning_only_commit_is_allowed_on_main(hooked_repo: Path):
    assert _git(hooked_repo, "checkout", "main").returncode == 0
    _stage_planning_file(hooked_repo)

    result = _git(hooked_repo, "commit", "-m", "planning on main")

    assert result.returncode == 0, result.stderr


def test_mixed_feature_commit_remains_allowed(hooked_repo: Path):
    _stage_planning_file(hooked_repo)
    (hooked_repo / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert _git(hooked_repo, "add", "feature.py").returncode == 0

    result = _git(hooked_repo, "commit", "-m", "feature with planning")

    assert result.returncode == 0, result.stderr


def test_detached_head_planning_commit_is_blocked(hooked_repo: Path):
    assert _git(hooked_repo, "checkout", "--detach").returncode == 0
    _stage_planning_file(hooked_repo)

    result = _git(hooked_repo, "commit", "-m", "detached planning")

    assert result.returncode != 0
    assert "Planning-only commit blocked on branch 'DETACHED'" in result.stderr


def test_installer_sets_repository_local_hooks_path(tmp_path: Path):
    repo = tmp_path / "install-target"
    repo.mkdir()
    assert _git(repo, "init", "-b", "main").returncode == 0
    hooks = repo / ".githooks"
    hooks.mkdir()
    copied = hooks / "pre-commit"
    shutil.copy2(HOOK, copied)
    copied.chmod(0o755)

    result = subprocess.run(
        [str(INSTALLER)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "core.hooksPath=.githooks" in result.stdout
    configured = _git(repo, "config", "--local", "--get", "core.hooksPath")
    assert configured.stdout.strip() == ".githooks"
