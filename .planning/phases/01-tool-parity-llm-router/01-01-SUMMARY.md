---
phase: 01-tool-parity-llm-router
plan: "01"
subsystem: packaging, test-infrastructure
tags: [pyproject, dependencies, test-scaffold, bridge-timeout, wave-0]
dependency_graph:
  requires: []
  provides: [clean-pyproject, wave-0-test-scaffolds, 60s-bridge-timeout]
  affects: [all-subsequent-plans-in-phase-1]
tech_stack:
  added: []
  patterns: [pytest-skip-stub pattern, tomllib pyproject validation]
key_files:
  created:
    - tests/conftest.py
    - tests/test_tools.py
    - tests/test_llm.py
  modified:
    - pyproject.toml
    - forge_bridge/bridge.py
decisions:
  - "openai and anthropic moved to [project.optional-dependencies] llm extra; base install stays lean"
  - "BRIDGE_TIMEOUT default raised from 30s to 60s to handle longer Flame operations"
  - "Wave 0 stub pattern: all non-implemented tests marked @pytest.mark.skip, immediately-verifiable tests run green"
metrics:
  duration: "2m"
  completed: "2026-04-15"
  tasks_completed: 2
  files_modified: 5
---

# Phase 1 Plan 01: Foundation Cleanup & Wave 0 Test Scaffolds Summary

**One-liner:** pyproject.toml cleaned of duplicate openai/anthropic deps with [llm] optional extra added, bridge timeout raised to 60s, and 18-test Wave 0 scaffold created for all Phase 1 requirements.

## What Was Built

### Task 1: Fix pyproject.toml and bump bridge timeout

- Removed two duplicate `openai>=1.0` and two duplicate `anthropic>=0.25` entries from `[project.dependencies]`
- Added `[project.optional-dependencies]` section with `llm = ["openai>=1.0", "anthropic>=0.25"]`
- Preserved existing `dev = [pytest, pytest-asyncio, ruff]` optional extra
- Changed `BRIDGE_TIMEOUT` default from `"30"` to `"60"` in `forge_bridge/bridge.py`

### Task 2: Wave 0 test scaffolds

- **tests/conftest.py**: Shared fixtures — `monkeypatch_bridge` (patches `forge_bridge.bridge.execute`), `mock_openai`, `mock_anthropic`
- **tests/test_tools.py**: Stubs for TOOL-01..TOOL-09 (all skipped except 2 immediate tests)
  - `test_bridge_timeout`: verifies BRIDGE_TIMEOUT == 60 (PASSES)
  - `test_pyproject_no_duplicates`: verifies pyproject integrity via tomllib (PASSES)
- **tests/test_llm.py**: Stubs for LLM-01..LLM-07 plus one non-skipped test
  - `test_llm_shim_import`: verifies `forge_bridge.llm_router` shim exports LLMRouter and get_router (PASSES)

### Test results

```
3 passed, 15 skipped in 0.01s
```

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **[llm] optional extra**: `openai` and `anthropic` are now optional dependencies. `pip install forge-bridge` installs neither. `pip install forge-bridge[llm]` adds both. This matches the design decision to keep the base install lean.

2. **60s bridge timeout**: Flame operations (render, batch processing) can take well over 30s. The new default covers typical interactive use without requiring env var overrides.

3. **Wave 0 stub pattern**: Skipped tests serve as living documentation of what each plan must implement. The skip reason `"Wave 0 stub — unskip when X implemented"` makes clear exactly what triggers each test becoming active.

## Self-Check

### Files exist

- [x] tests/conftest.py
- [x] tests/test_tools.py
- [x] tests/test_llm.py
- [x] pyproject.toml (modified)
- [x] forge_bridge/bridge.py (modified)

### Commits exist

- [x] 52400ed — chore(01-01): fix pyproject.toml and bump bridge timeout
- [x] a222b6f — test(01-01): add Wave 0 test scaffolds for all Phase 1 requirements

## Self-Check: PASSED
