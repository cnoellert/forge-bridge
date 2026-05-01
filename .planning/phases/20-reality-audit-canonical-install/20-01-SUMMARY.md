---
phase: 20
plan: "01"
subsystem: install
tags: [version-bump, regression-guard, install-script, pyproject]
dependency_graph:
  requires: []
  provides: [canonical-version-1.4.1, D17-consistency-guard]
  affects: [README.md, pyproject.toml, scripts/install-flame-hook.sh, tests/test_install_hook_version_consistency.py]
tech_stack:
  added: []
  patterns: [TDD-red-green, decoupled-commit-purity, conservative-bump-first]
key_files:
  created:
    - tests/test_install_hook_version_consistency.py
  modified:
    - pyproject.toml
    - tests/test_public_api.py
    - scripts/install-flame-hook.sh
    - README.md
decisions:
  - "Bumped pyproject.toml to 1.4.1 to match the v1.4.1 git tag (INSTALL-02 correction; v1.4.0 and v1.4.1 milestones tagged without bumping the package version)"
  - "D-17 regression guard implemented as Option (c) unit test — pure file reads + regex, no fixtures, no asyncio, runs with default pytest tests/"
  - "D-16 pre-flip URL verification passed at execute time (both raw GitHub v1.4.1 URLs returned 200 OK)"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-30"
  tasks: 3
  files: 5
requirements: [INSTALL-02, INSTALL-03]
---

# Phase 20 Plan 01: Version Consistency Pin + D-17 Regression Guard Summary

Established v1.4.1 as the canonical pinned version across every install-relevant source-of-truth file, and locked three-way consistency in place with a regression-guarding pytest.

## What Was Built

Three-way version drift (script `v1.1.0` / README `v1.2.1` / pyproject `1.3.0` vs live tag `v1.4.1`) fully resolved. All four files now agree. A new regression guard (`tests/test_install_hook_version_consistency.py`) enforces the three-way consistency invariant permanently.

## Commits Landed

| Commit | Message | Files |
|--------|---------|-------|
| `f7efe2b` | `chore(20): bump pyproject.toml to 1.4.1 + sync test_package_version assertion` | `pyproject.toml`, `tests/test_public_api.py` |
| `b684490` | `chore(20): bump install-flame-hook.sh default to v1.4.1` | `scripts/install-flame-hook.sh` |
| `024e395` | `chore(20): bump README curl URL to v1.4.1 + add D-17 consistency guard` | `README.md`, `tests/test_install_hook_version_consistency.py` |

## D-16 Pre-Flip URL Verification

Both v1.4.1 raw GitHub URLs verified at execute time (re-verified per D-16 conservative-bump-first pattern; researcher verified at research time, executor re-verified at execute time):

| URL | HTTP Status |
|-----|-------------|
| `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh` | **200 OK** |
| `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/flame_hooks/forge_bridge/scripts/forge_bridge.py` | **200 OK** |

Both URLs resolve. The version flip was safe.

## Test Results

**Quick suite** (`pytest tests/test_public_api.py tests/test_install_hook_version_consistency.py -x`):
- 21 passed, 0 failed

**Full suite** (`pytest tests/ -x --tb=short`):
- 845 passed, 41 skipped, 0 failed

## forge_bridge.__version__ Verification

After editable reinstall (`pip install -e . --quiet`):
```
$ python -c "from importlib.metadata import version; print(version('forge-bridge'))"
1.4.1
```

`forge_bridge.__version__` now correctly reports `"1.4.1"`.

## Per-Task Details

### Task 1 (TDD): Bump pyproject.toml to 1.4.1 + sync test_package_version

**TDD cycle:**
- RED: Updated `tests/test_public_api.py::test_package_version` to assert `1.4.1` — test failed as expected (pyproject still had `1.3.0`)
- GREEN: Changed `pyproject.toml` line 7 from `version = "1.3.0"` to `version = "1.4.1"` — both `test_package_version` and `test_version_attribute_exposed` passed
- REFACTOR: Not needed

**Changes:**
- `pyproject.toml`: `version = "1.3.0"` → `version = "1.4.1"` (line 7 only; no other lines touched)
- `tests/test_public_api.py`: Updated `test_package_version` docstring, assertion string, and error message from `1.3.0` to `1.4.1`; appended Phase 20 entry to PKG-02 historical changelog comment block

### Task 2: Pre-flight verify + bump install-flame-hook.sh

**D-16 verification:** Both v1.4.1 raw URLs returned 200 OK (re-verified at execute time).

**Changes (three lines only; no other lines touched):**
- Line 10 (standalone curl example comment): `v1.1.0` → `v1.4.1`
- Line 13 (FORGE_BRIDGE_VERSION env-override comment): `v1.1.0` → `v1.4.1`
- Line 29 (runtime VERSION default): `v1.1.0` → `v1.4.1`

### Task 3 (TDD): Bump README + add D-17 consistency guard

**TDD cycle:**
- RED: Created `tests/test_install_hook_version_consistency.py` — `test_install_hook_default_version_matches_pyproject` passed immediately (script and pyproject already aligned); `test_readme_curl_url_version_matches_pyproject` failed with `README.md curl URL version (v1.2.1) != pyproject.toml version (1.4.1)`
- GREEN: Updated README.md line 106 (curl URL) and line 109 (prose "default v1.2.1") from `v1.2.1` to `v1.4.1` — both tests passed
- REFACTOR: Not needed

**README changes (two lines only; no other lines touched):**
- Line 106: `v1.2.1` → `v1.4.1` in curl URL
- Line 109: `v1.2.1` → `v1.4.1` in FORGE_BRIDGE_VERSION prose

**New test file:** `tests/test_install_hook_version_consistency.py` — two tests covering INSTALL-02 and INSTALL-03.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All changes are concrete version-literal updates and a pure-Python regex test file. No placeholder values.

## Threat Flags

No new security surface introduced. All changes are metadata (version strings) and a local-filesystem read test. No new network endpoints, auth paths, or schema changes. Per threat register T-20-01..03: all dispositions remain `accept (LOW)`.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `pyproject.toml` exists | FOUND |
| `scripts/install-flame-hook.sh` exists | FOUND |
| `README.md` exists | FOUND |
| `tests/test_public_api.py` exists | FOUND |
| `tests/test_install_hook_version_consistency.py` exists | FOUND |
| `20-01-SUMMARY.md` exists | FOUND |
| Commit `f7efe2b` exists | FOUND |
| Commit `b684490` exists | FOUND |
| Commit `024e395` exists | FOUND |
