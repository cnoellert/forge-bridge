"""Verify the Phase 10 wheel-packaging contract (D-33).

pyproject.toml's [tool.hatch.build.targets.wheel].include globs must
pick up every template and every static asset. Without this,
`pip install forge-bridge` from the wheel silently drops non-.py
files and the Web UI 404s on every asset request.

This is the SC#1 mechanical check ("no npm commands, fresh install works").
The full SC#1 dogfood loop is in 10-UAT.md.
"""
from __future__ import annotations

import hashlib
import base64
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory):
    """Build the wheel once per module. Skip if `python -m build` isn't
    available (e.g. on a minimal CI where the build tool isn't installed).
    """
    out_dir = tmp_path_factory.mktemp("wheel-out")
    # Try `python -m build --wheel` first; fall back to hatch if build
    # isn't installed.
    try:
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"python -m build failed or not installed: {exc}")
    wheels = list(out_dir.glob("forge_bridge-*.whl"))
    if not wheels:
        pytest.skip("no wheel produced")
    return wheels[0]


def test_wheel_contains_forge_console_css(built_wheel):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    assert any(
        n.endswith("forge_bridge/console/static/forge-console.css") for n in names
    ), f"forge-console.css missing from wheel; contents: {names[:20]}..."


def test_wheel_contains_vendored_htmx(built_wheel):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    assert any(
        n.endswith("forge_bridge/console/static/vendor/htmx-2.0.10.min.js")
        for n in names
    )


def test_wheel_contains_vendored_alpinejs(built_wheel):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    assert any(
        n.endswith("forge_bridge/console/static/vendor/alpinejs-3.14.1.min.js")
        for n in names
    )


def test_wheel_contains_vendored_readme(built_wheel):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    assert any(
        n.endswith("forge_bridge/console/static/vendor/README.md")
        for n in names
    )


def test_wheel_contains_base_html(built_wheel):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    assert any(
        n.endswith("forge_bridge/console/templates/base.html") for n in names
    )


def test_wheel_contains_shell_html(built_wheel):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    assert any(
        n.endswith("forge_bridge/console/templates/shell.html") for n in names
    )


@pytest.mark.parametrize("relpath", [
    "forge_bridge/console/templates/tools/list.html",
    "forge_bridge/console/templates/tools/detail.html",
    "forge_bridge/console/templates/execs/list.html",
    "forge_bridge/console/templates/execs/detail.html",
    "forge_bridge/console/templates/manifest/list.html",
    "forge_bridge/console/templates/health/detail.html",
    "forge_bridge/console/templates/chat/panel.html",
    "forge_bridge/console/templates/fragments/tools_table.html",
    "forge_bridge/console/templates/fragments/execs_table.html",
    "forge_bridge/console/templates/fragments/manifest_table.html",
    "forge_bridge/console/templates/fragments/health_view.html",
    "forge_bridge/console/templates/fragments/health_strip.html",
    "forge_bridge/console/templates/fragments/query_console.html",
    "forge_bridge/console/templates/errors/not_found.html",
    "forge_bridge/console/templates/errors/read_failed.html",
])
def test_wheel_contains_all_phase_10_templates(built_wheel, relpath):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    assert any(n.endswith(relpath) for n in names), (
        f"template {relpath} MISSING from wheel. "
        f"Check pyproject.toml [tool.hatch.build.targets.wheel] include globs "
        f"(plan 10-01 Task 1 contract)."
    )


def test_wheel_sri_hashes_match_committed_vendored_files(built_wheel):
    """SRI contract — the hash baked into base.html must match the hash
    computed from the vendored file in the wheel. If they drift, browsers
    will refuse to load the script and the UI breaks silently."""
    with zipfile.ZipFile(built_wheel) as zf:
        base_html_name = next(
            (n for n in zf.namelist()
             if n.endswith("forge_bridge/console/templates/base.html")),
            None,
        )
        htmx_name = next(
            (n for n in zf.namelist()
             if n.endswith("forge_bridge/console/static/vendor/htmx-2.0.10.min.js")),
            None,
        )
        alpine_name = next(
            (n for n in zf.namelist()
             if n.endswith("forge_bridge/console/static/vendor/alpinejs-3.14.1.min.js")),
            None,
        )
        assert base_html_name and htmx_name and alpine_name
        base_html = zf.read(base_html_name).decode("utf-8")
        htmx_bytes = zf.read(htmx_name)
        alpine_bytes = zf.read(alpine_name)
    htmx_sri = "sha384-" + base64.b64encode(
        hashlib.sha384(htmx_bytes).digest()
    ).decode("ascii")
    alpine_sri = "sha384-" + base64.b64encode(
        hashlib.sha384(alpine_bytes).digest()
    ).decode("ascii")
    assert htmx_sri in base_html, (
        f"htmx SRI mismatch: computed {htmx_sri} but base.html uses a "
        f"different hash. Re-run plan 10-01 Task 2 SRI computation and "
        f"update plan 10-02 Task 1's base.html substitution."
    )
    assert alpine_sri in base_html, (
        f"alpinejs SRI mismatch: computed {alpine_sri} but base.html uses a "
        f"different hash."
    )
