---
phase: 20
plan: "07"
subsystem: install
tags: [install-guide, topology, multi-host, ollama-remote, D-04-gap-fix, INSTALL-01, INSTALL-03]
dependency_graph:
  requires:
    - phase: 20-04
      provides: docs/INSTALL.md (initial single-machine framing)
  provides:
    - docs/INSTALL.md (topology-aware multi-host framing)
    - topology-truth: multi-host is the realistic default for Flame operators
  affects:
    - docs/INSTALL.md
tech_stack:
  added: []
  patterns: [multi-host-topology, remote-ollama-default, single-machine-as-exception]
key_files:
  created: []
  modified:
    - docs/INSTALL.md
decisions:
  - "Multi-host framing (operator workstation + separate LLM service host) is the realistic default for Flame operators; single-machine Ollama is documented as the exception requiring GPU/RAM headroom beyond Flame's needs"
  - "FORGE_LOCAL_LLM_URL is the operator-side knob — already accepted any URL (verified forge_bridge/llm/router.py:199); doc was the only artifact asserting localhost-only"
  - "LLM service host appendix is compact by design — Ollama daemon + model pull is the entire install; no bridge/Postgres/Flame on that host"
  - "20-04 SUMMARY.md preserved as historical artifact; Plan 20-07 SUMMARY explicitly documents that 20-04's topology framing is superseded for the topology sections only; all 20-04 mechanics (versions, commands, steps) are unchanged"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-30"
  tasks: 1
  files: 1
requirements: [INSTALL-01, INSTALL-03]
---

# Phase 20 Plan 07: INSTALL.md Topology Framing Fix Summary

Refreshed `docs/INSTALL.md` in 7 surgical passes to frame multi-host topology (operator workstation + separate LLM service host) as the realistic default for Flame operators — `FORGE_LOCAL_LLM_URL` has always accepted any URL; only the doc was wrong.

## What Triggered This Plan

During Phase 20 Track A pre-walk fixture prep, the fixture named as the reference operator workstation (assist-01 in CONTEXT.md D-02) turned out to be a dedicated LLM service host — Ollama + `qwen2.5-coder:32b` only; no Postgres, no Flame, no bridge. The non-author UAT could not start because the fixture's actual shape did not match what INSTALL.md presupposed.

The doc — not the fixture — had drifted from reality. INSTALL.md was authored under a single-machine mental model. The code has always supported multi-host via `FORGE_LOCAL_LLM_URL` (any URL accepted verbatim at `forge_bridge/llm/router.py:199`). `FORGE_DB_URL` is similarly remote-capable (`forge_bridge/store/session.py:44`). This is a doc-only fix.

## The 7 Surgical Passes

1. **Preamble** — replaced "Single-machine operator install" with "Operator-workstation install"; rewrote description to say Flame + Postgres are local, Ollama is reached over the network, separate LLM service host is the typical case.
2. **"Before you start" deps split** — replaced single flat table with "What runs where" heading + two tables: "Operator host" (conda/Python/Postgres/Flame) and "Reachable network services" (Ollama daemon + model + optional Anthropic API).
3. **New "Topology / network reachability" subsection** — inserted after qwen3 warning, before Track B carveout; explains remote-Ollama-as-default, documents `FORGE_LOCAL_LLM_URL` knob, provides reachability `curl` checks to run BEFORE Step 1.
4. **Track B carveout update** — appended one sentence noting Track B operators commonly point `FORGE_LOCAL_LLM_URL` at a separate LLM service host; Track B does not require Ollama to be local.
5. **Step 5 env-var annotation** — added `# Ollama base URL — change to your LLM service host if Ollama is not local` comment immediately above the `FORGE_LOCAL_LLM_URL` export line.
6. **Reference appendix env-var table** — updated Purpose for `FORGE_LOCAL_LLM_URL` ("set to remote LLM host if Ollama runs separately") and `FORGE_DB_URL` ("local default; set to remote Postgres URL if applicable").
7. **New "Reference: LLM service host" appendix** — inserted before "Reference: Cross-links"; explains the minimum install for a separate Ollama host (daemon + model pull, nothing else); documents the `FORGE_LOCAL_LLM_URL` export and two verification curls.

## What Stayed the Same

All Step 1–8 mechanics are unchanged. Every version pin is unchanged (`v1.4.1`, `qwen2.5-coder:32b`, `conda ~24.x`, `0.21.0`, etc.). Every command is unchanged (`install-flame-hook.sh`, `alembic upgrade head`, `forge-bridge console doctor`, all five surface smoke tests). The Track B carveout received one appended sentence only — the existing two paragraphs are verbatim. The Plan 20-01 version-consistency invariant still passes.

## What This Unblocks

Plan 20-05's checkpoint can now resume on a real operator-workstation host. The doc no longer demands Ollama be host-local — an operator workstation that points `FORGE_LOCAL_LLM_URL` at the existing assist-01 Ollama service is exactly what INSTALL.md now describes as the typical deployment.

## Code Cross-References (proof the code already supported this)

- `forge_bridge/llm/router.py:198-200` — `self.local_url = local_url or os.environ.get("FORGE_LOCAL_LLM_URL", "http://localhost:11434/v1")`. Any URL is accepted verbatim; `localhost` is just the fallback.
- `forge_bridge/store/session.py:44-46` — `get_db_url()` returns `os.environ.get("FORGE_DB_URL", DEFAULT_DB_URL)`. Already remote-capable.
- `forge_bridge/cli/doctor.py:179-190` — LLM backends from `/api/v1/health` are checked as `warn`-level; if `FORGE_LOCAL_LLM_URL` points at a remote host and that host is unreachable, the health endpoint will report the backend as degraded and `forge doctor` will surface it as a warning.

## Note on CONTEXT.md D-02 and the Fixture Misunderstanding

CONTEXT.md D-02 named assist-01 as the Track A reference operator workstation. In reality assist-01 is a dedicated LLM service host. This does not require a CONTEXT.md edit within this plan (out of scope per the plan's `<output>` block), but the next phase's CONTEXT or a one-line note in PROJECT.md should clarify that the Track A UAT machine is a Flame workstation that reaches assist-01 as its LLM service host. This is a tracking note only — no action in Plan 20-07.

## Verify Block Results

All checks passed after all 7 passes:

| Check | Result |
|-------|--------|
| `test -f docs/INSTALL.md` | PASS |
| `wc -l >= 290` | PASS (344 lines) |
| `grep -q "Operator-workstation install"` | PASS |
| `grep -q "Topology / network reachability"` | PASS |
| `grep -q "## Reference: LLM service host"` | PASS |
| `grep -q "Reachable network services"` | PASS |
| `! grep -q "Single-machine operator install"` | PASS (phrase GONE) |
| `grep -q "v1.4.1"` | PASS |
| `grep -q "qwen2.5-coder:32b"` | PASS |
| `grep -q "install-flame-hook.sh"` | PASS |
| `grep -q "alembic upgrade head"` | PASS |
| `grep -q "forge-bridge console doctor"` | PASS |
| `FORGE_LOCAL_LLM_URL count >= 4` | PASS (5 occurrences) |
| `pytest tests/test_install_hook_version_consistency.py -x -q` | PASS (2 passed) |
| `pytest -x -q` | PASS (845 passed, 41 skipped, 0 failed) |
| "Reference: LLM service host" before "Reference: Cross-links" | PASS (lines 309 vs 337) |

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| `7d31cdd` | `docs(20): refresh INSTALL.md for multi-host topology (D-04 in-flight gap-fix)` | `docs/INSTALL.md` |

## Deviations from Plan

None — all 7 passes applied exactly as specified. The `forge doctor` claim in Pass 3 ("will report `llm_router: degraded`") was verified against `forge_bridge/cli/doctor.py` before writing: `_health_to_checks` surfaces LLM backend status from `/api/v1/health` as `warn`-level entries; if the Ollama host is unreachable, the health endpoint marks the backend degraded and `forge doctor` renders it as a warning row. The plan's claim is accurate (using "degraded" as the status label, consistent with the codebase's degraded-tolerant language).

## Threat Mitigation Status

| Threat ID | Mitigation Status |
|-----------|-----------------|
| T-20-20 (Tampering — INSTALL.md edits) | Applied — 7 surgical passes with explicit before/after; verify block re-read and asserted on shape; committed only after all checks passed |
| T-20-21 (FORGE_LOCAL_LLM_URL in shell history) | Accept — non-secret network config; no change in exposure |
| T-20-22 (20-04 SUMMARY still claims single-machine framing) | Applied — 20-04 SUMMARY preserved as historical artifact; this 20-07 SUMMARY explicitly documents that 20-04's topology framing is superseded by this plan for the topology sections |

## Known Stubs

None. All added content is concrete and sourced from verified code behavior.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `docs/INSTALL.md` exists | FOUND |
| Line count >= 290 | FOUND (344 lines) |
| "Single-machine operator install" absent | CONFIRMED |
| "Operator-workstation install" in preamble | CONFIRMED |
| "What runs where" two-table split | CONFIRMED |
| "Topology / network reachability" subsection | CONFIRMED |
| Track B sentence appended | CONFIRMED |
| Step 5 FORGE_LOCAL_LLM_URL comment | CONFIRMED |
| Env-var table Purpose columns updated | CONFIRMED |
| "Reference: LLM service host" appendix | CONFIRMED |
| Appendix before "Reference: Cross-links" | CONFIRMED |
| "Reference: Cross-links" still final section | CONFIRMED |
| Commit `7d31cdd` exists | FOUND |
| `pytest tests/test_install_hook_version_consistency.py -x` | 2 passed |
| `pytest -x` | 845 passed, 41 skipped, 0 failed |
