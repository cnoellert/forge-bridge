---
phase: 20
plan: "04"
subsystem: install
tags: [install-guide, operator-docs, five-surfaces, INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04]
dependency_graph:
  requires:
    - phase: 20-01
      provides: canonical-version-1.4.1, D17-consistency-guard
    - phase: 20-02
      provides: claude-md-v1.4.1-ground-truth
    - phase: 20-03
      provides: readme-install-section-v1.4.1
  provides:
    - docs/INSTALL.md
    - canonical-operator-install-path
  affects:
    - docs/INSTALL.md
tech_stack:
  added: []
  patterns: [opinionated-single-path, track-b-carveout, min-ref-version-model]
key_files:
  created:
    - docs/INSTALL.md
  modified: []
decisions:
  - "Single opinionated path (D-07): conda + Python 3.11 + Postgres + Ollama + qwen2.5-coder:32b as the reference track; no alternative paths documented"
  - "Track B / MCP-only carveout in Before-you-start section (D-08): single callout block, not a forked doc — tells operators to skip Step 4 and notes Surface 5 unavailability + staged-ops Postgres dependency"
  - "alembic.ini hardcoded-URL note added to Step 3 to prevent credential mismatch on non-default Postgres setups (T-20-02 mitigation)"
  - "ANTHROPIC_API_KEY documented as optional with explicit safe-paste guidance (T-20-03 mitigation)"
  - "All five surface smoke commands in Step 7 sourced verbatim from RESEARCH.md §D1"
  - "qwen3:32b warning present with SEED-DEFAULT-MODEL-BUMP-V1.4.x seed reference"
  - "stdin-keepalive (tail -f /dev/null) documented per 16.2-HUMAN-UAT.md precedent"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-30"
  tasks: 1
  files: 1
requirements: [INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04]
---

# Phase 20 Plan 04: Canonical Operator Install Guide Summary

Created `docs/INSTALL.md` — the single-machine opinionated operator install path for forge-bridge v1.4.1, covering all five surfaces and including a Track B / MCP-only carveout.

## What Was Built

A new 288-line, 1510-word install guide (`docs/INSTALL.md`) that walks a fresh conda env on a workstation with Flame + Postgres + Ollama to a verified five-surface install. Sourced entirely from RESEARCH.md §B-§D verified ground truth — no assumptions.

## Commits Landed

| Commit | Message | Files |
|--------|---------|-------|
| `adef5b1` | `docs(20): create canonical operator install guide (INSTALL-01..04)` | `docs/INSTALL.md` |

## Document Statistics

| Metric | Value |
|--------|-------|
| Line count | 288 lines |
| Word count | 1510 words |
| Sections | H1 title + Before you start + 8 numbered steps + 3 reference appendices |
| Tables | 4 (dep table, Flame-hook env vars, env-var reference, port reference) |
| Code blocks | 20 (all with language tags: `bash`, `json`) |

## Structural Inventory

All 8 steps and carveouts present in canonical order:

| Section | Content |
|---------|---------|
| Before you start | 7-dependency external-dep table (INSTALL-04) + Track B / MCP-only carveout (D-08) |
| Step 1 | Prepare the conda environment (conda create + Python 3.11) |
| Step 2 | Install forge-bridge (`pip install -e ".[dev,llm]"` + version self-report + CLI verify) |
| Step 3 | Set up Postgres (default creds + alembic upgrade head + alembic.ini hardcoded-URL note) |
| Step 4 | Install the Flame hook (local script + standalone curl pinned at v1.4.1) |
| Step 5 | Configure environment variables (FORGE_DB_URL required; others optional; ANTHROPIC_API_KEY safe handling) |
| Step 6 | Start the server (daily + headless stdin-keepalive launches; artifact paths auto-created) |
| Step 7 | Verify all five surfaces (smoke test block: Flame hook, MCP CLI, Web UI, chat, browser visual) |
| Step 8 | Post-install diagnostic (forge-bridge console doctor + supplemental Postgres + Ollama model checks) |
| Ref: Env vars | 11-var table with defaults |
| Ref: Ports | 3-port table (9996, 9998, 9999) |
| Ref: Cross-links | 6 cross-links (API.md, ARCHITECTURE.md, VOCABULARY.md, ENDPOINTS.md, README.md, CLAUDE.md) |

## Verification Grep Results

All automated verification checks passed:

| Check | Result |
|-------|--------|
| `grep -q '^# forge-bridge Install Guide' docs/INSTALL.md` | PASS |
| `grep -q '^## Before you start' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 1: Prepare the conda environment' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 2: Install forge-bridge' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 3: Set up Postgres' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 4: Install the Flame hook' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 5: Configure environment variables' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 6: Start the server' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 7: Verify all five surfaces' docs/INSTALL.md` | PASS |
| `grep -q '^## Step 8: Post-install diagnostic' docs/INSTALL.md` | PASS |
| `grep -q "If you don't have Flame" docs/INSTALL.md` | PASS (D-08) |
| `grep -q 'qwen2.5-coder:32b' docs/INSTALL.md` | PASS |
| `grep -q 'qwen3:32b' docs/INSTALL.md` | PASS (warning present) |
| `grep -q 'tested at v1.4.1' docs/INSTALL.md` | PASS (D-13 ref-version model) |
| `grep -q 'tail -f /dev/null \| python -m forge_bridge' docs/INSTALL.md` | PASS |
| `grep -q 'forge-bridge console doctor' docs/INSTALL.md` | PASS |
| `grep -q 'curl -fsS http://localhost:9996/ui/' docs/INSTALL.md` | PASS |
| `grep -q 'curl -s http://localhost:9999/status' docs/INSTALL.md` | PASS |
| `grep -q 'api/v1/chat' docs/INSTALL.md` | PASS |
| `grep -q 'alembic upgrade head' docs/INSTALL.md` | PASS |
| `grep -q 'pip install -e "\.\[dev,llm\]"' docs/INSTALL.md` | PASS |
| `grep -q 'cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh' docs/INSTALL.md` | PASS (INSTALL-02) |
| `grep -q 'forge_config.yaml' docs/INSTALL.md` returns 0 matches | PASS (no config file) |
| `[ "$(wc -l < docs/INSTALL.md)" -ge "200" ]` | PASS (288 lines) |

## Plan 20-01 Consistency Test: PASSED

The v1.4.1 curl URL in INSTALL.md is consistent with README.md and pyproject.toml. D-17 regression guard confirms:

```
pytest tests/test_install_hook_version_consistency.py tests/test_public_api.py -x
21 passed, 1 warning in 0.07s
```

## Full Test Suite: PASSED

```
pytest tests/ -x --tb=short
845 passed, 41 skipped, 198 warnings in 31.89s
```

## Observations During Authoring

### No new gaps surfaced

All env vars documented in INSTALL.md were present in RESEARCH.md §C5-§C6. No undocumented env vars were found during authoring. The env-var table (11 vars) matches the RESEARCH §C5-§C6 inventory exactly.

### alembic.ini hardcoded-URL note — Phase 23 enhancement candidate

The `alembic.ini` sync URL is hardcoded (`postgresql+psycopg2://forge:forge@localhost:5432/forge_bridge`) and does NOT auto-read `FORGE_DB_URL`. This is documented in Step 3 with a workaround. A `forge doctor` sub-check that verifies `FORGE_DB_URL` is a valid async URL (and prints a warning if it appears to differ from `alembic.ini`'s hardcoded sync URL) would improve the operator experience. Logged as a Phase 23 `forge doctor` enhancement candidate.

### install-flame-hook.sh embedded next-steps use :9999/ not :9999/status

The script's `NEXT` heredoc (line 78) uses `curl -s http://localhost:9999/ -o /dev/null -w "%{http_code}\n"` while INSTALL.md Step 7 uses `curl -s http://localhost:9999/status` (the canonical smoke test per RESEARCH.md §D1). Both are valid — the `/status` endpoint is preferable for its machine-parseable JSON. No action required; both pass.

### Five smoke test block ordering

INSTALL.md Step 7 lists the Flame hook smoke test first (Surface 1), unlike RESEARCH.md §D1 which lists it last. Ordering was reversed for narrative flow: the Track B / MCP-only carveout mentions Surface 5 as skipped, so Step 7 leading with Surface 1 (Flame hook) makes the skip explicit for Track B operators. No functional impact.

## Threat Mitigation Status

| Threat ID | Mitigation Status |
|-----------|-----------------|
| T-20-01 (curl\|bash chain) | Applied — curl URL pinned to `v1.4.1` tag; prose links to script source for inspection |
| T-20-02 (alembic target mismatch) | Applied — Step 3 explicitly calls out alembic.ini hardcoded URL and provides --url override syntax |
| T-20-03 (ANTHROPIC_API_KEY disclosure) | Applied — Step 5 specifies shell profile / sourced .env; warns against command-line paste and git commit |
| T-20-09 (doc claims vs. reality) | Applied — Step 7 five-surface smoke test block gives operator immediate ground-truth verification |

## Deviations from Plan

None — plan executed exactly as written. The plan provided the complete `docs/INSTALL.md` content verbatim; it was written as specified without modification. All required checks pass.

## Known Stubs

None. All content is concrete, sourced from RESEARCH.md verified ground truth. No placeholder text, hardcoded empty values, or "coming soon" strings.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `docs/INSTALL.md` exists | FOUND |
| `docs/INSTALL.md` line count >= 200 | FOUND (288 lines) |
| All 8 step headings present in order | CONFIRMED |
| Track B / MCP-only carveout present | CONFIRMED |
| qwen3:32b warning present | CONFIRMED |
| stdin-keepalive note present | CONFIRMED |
| All 5 surface smoke tests in Step 7 | CONFIRMED |
| forge-bridge console doctor in Step 8 | CONFIRMED |
| v1.4.1 curl URL in Step 4 | CONFIRMED |
| Env-var table (11 vars) present | CONFIRMED |
| Port table (3 ports) present | CONFIRMED |
| 6 cross-links present | CONFIRMED |
| forge_config.yaml absent | CONFIRMED |
| Commit `adef5b1` exists | FOUND |
| `pytest tests/test_install_hook_version_consistency.py -x` | 2 passed |
| `pytest tests/ -x` | 845 passed, 41 skipped, 0 failed |
