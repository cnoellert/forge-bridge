---
phase: 20
slug: reality-audit-canonical-install
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing project framework) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_public_api.py tests/test_install_hook_version_consistency.py -x` |
| **Full suite command** | `pytest tests/ -x --tb=short` |
| **Estimated runtime** | ~30 seconds quick, ~2 minutes full |

Phase 20's validation strategy mixes automated invariants (version consistency, package self-report) with **manual non-author UAT on Track A** as the milestone gate. The non-author UAT is the locked acceptance criterion (CONTEXT.md D-02) — it cannot be replaced by automation.

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_public_api.py -x` (~5 seconds)
- **After every plan wave:** Run quick suite + verify the touched docs render cleanly
- **Before `/gsd-verify-work`:** Full suite green AND Track A non-author UAT recorded in `20-HUMAN-UAT.md`
- **Max feedback latency:** 30 seconds for automated checks; the non-author UAT is a milestone-gate event, not a per-task check

---

## Per-Task Verification Map

> Populated by gsd-planner during planning. Each PLAN.md task's `<automated>` block becomes one row. The planner MUST emit grep-checkable acceptance criteria so Wave 0 / per-task verification fires automatically.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | INSTALL-01..04, DOCS-02 | — | N/A (docs/install path; no new attack surface) | mixed | TBD per task | ⬜ pending | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Phase 20 is doc-heavy with two automation hooks. Wave 0 installs:

- [ ] `tests/test_install_hook_version_consistency.py` — IF the planner picks Option (c) from CONTEXT.md D-17 (regression guard as unit test). If planner picks Option (a) `forge doctor` sub-check or Option (b) CI lint, replace this row with the equivalent.
- [ ] `tests/conftest.py` — already exists; no new fixtures expected (this is a docs phase)

*If none of the above are needed (all gap-fixes ship as doc edits + a single-line script flip + a pyproject version bump): "Existing infrastructure covers all phase requirements; no Wave 0 test additions."*

---

## Manual-Only Verifications

The two non-automatable gates Phase 20 ships against:

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| **Track A non-author UAT** — fresh-conda-env operator follows `docs/INSTALL.md` verbatim and reaches all 5 surfaces | INSTALL-01..04, DOCS-02 + CONTEXT.md D-02 | Author cannot UAT their own doc — comprehension blind spots are the bug being hunted | Non-author runs the doc on assist-01 fresh conda env. Outcome recorded per-step in `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md`. Every gap encountered is fixed in-flight (D-04) before sign-off. |
| **Track B integrator/MCP-only dry-run** — author runs the doc on a Flame-less machine to surface dep-presence assumptions | INSTALL-04 | Surfaces "I assumed Postgres was running" / "I assumed Ollama was preloaded" gaps that Track A masks | Author dry-run on a non-Flame machine. Per CONTEXT.md D-03, this is not a milestone gate — it exists to catch dep-presence assumptions only. Outcome recorded in `20-HUMAN-UAT.md` Track B section. |
| **v1.4.1 raw-URL resolution** | INSTALL-02 | One-shot pre-flight check; not a recurring assertion | `curl -fsSI https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh` returns 200 (already verified by researcher; planner re-checks immediately before flipping the script default per D-16) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter
- [ ] Track A non-author UAT recorded in `20-HUMAN-UAT.md` with PASS verdict
- [ ] Track B author dry-run recorded in `20-HUMAN-UAT.md`
- [ ] Version-consistency invariant (script default == README curl URL == pyproject `version`) is enforced by the chosen D-17 regression guard

**Approval:** pending
