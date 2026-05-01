"""
Regression guard: install-flame-hook.sh FORGE_BRIDGE_VERSION default, README
curl URL, and pyproject.toml version must all agree.

Covers INSTALL-02 and INSTALL-03 from the v1.5 Legibility milestone (Phase 20).
Fails immediately when a version bump touches one source without updating the
others — the three-way drift that Phase 20 corrects (script v1.1.0, README
v1.2.1, live tag v1.4.1).

Phase 20 D-17 chose this regression-guard placement (Option c) over a `forge
doctor` sub-check (requires a running server) and a CI lint (no .github/
pipeline exists). Mirrors the established `tests/test_public_api.py` style:
pure file reads + regex, no fixtures, no asyncio.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text()


def test_install_hook_default_version_matches_pyproject():
    """install-flame-hook.sh FORGE_BRIDGE_VERSION default matches pyproject.toml version.

    Covers INSTALL-02: the default version installed by the script must match
    the package version declared in pyproject.toml. Without this guard, an
    operator running `curl ... | bash` could silently install a Flame hook
    from a tag that does not match their pip-installed forge-bridge.
    """
    hook = _read("scripts/install-flame-hook.sh")
    # Matches: VERSION="${FORGE_BRIDGE_VERSION:-v1.4.1}"
    m = re.search(r'VERSION="\$\{FORGE_BRIDGE_VERSION:-([^"\}]+)\}"', hook)
    assert m, "Could not find VERSION default in scripts/install-flame-hook.sh"
    script_version = m.group(1).lstrip("v")  # strip leading 'v' for comparison

    pyproject = _read("pyproject.toml")
    mp = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert mp, "Could not find version field in pyproject.toml"
    pkg_version = mp.group(1)

    assert script_version == pkg_version, (
        f"install-flame-hook.sh default (v{script_version}) != "
        f"pyproject.toml version ({pkg_version}). "
        "Bump both together when releasing a new version (Phase 20 D-17 guard)."
    )


def test_readme_curl_url_version_matches_pyproject():
    """README.md curl URL version matches pyproject.toml version.

    Covers INSTALL-03: the curl URL shown to operators in README.md must
    install the same version that pyproject.toml declares. Without this guard,
    the README can drift one minor release ahead of the install script (the
    exact failure mode that Phase 20 corrects: README at v1.2.1, script at
    v1.1.0).
    """
    readme = _read("README.md")
    # Matches: https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh
    m = re.search(
        r"raw\.githubusercontent\.com/cnoellert/forge-bridge/(v[^/]+)/scripts/install-flame-hook\.sh",
        readme,
    )
    assert m, "Could not find forge-bridge version in README.md curl URL"
    readme_version = m.group(1).lstrip("v")

    pyproject = _read("pyproject.toml")
    mp = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert mp, "Could not find version field in pyproject.toml"
    pkg_version = mp.group(1)

    assert readme_version == pkg_version, (
        f"README.md curl URL version (v{readme_version}) != "
        f"pyproject.toml version ({pkg_version}). "
        "Bump the README curl URL when releasing a new version (Phase 20 D-17 guard)."
    )
