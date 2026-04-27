---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 10
subsystem: planning-artifacts
tags:
  - seeds
  - forward-looking
  - fb-c
  - v1.4
  - v1.5
  - documentation
dependency_graph:
  requires:
    - .planning/seeds/SEED-AUTH-V1.5.md (existing format reference)
    - .planning/phases/15-fb-c-llmrouter-tool-call-loop/15-CONTEXT.md (D-06, D-28, D-30 + deferred ideas)
    - .planning/research/FB-C-TOOL-CALL-LOOP.md (§1, §2, §3.5, §5.4, §6.2, §6.4, §6.7, §8 Q1)
  provides:
    - Seven forward-looking SEED files in .planning/seeds/ — discoverable via standard gsd seed-discovery convention
    - Trigger conditions for v1.4.x model-default bumps (Ollama qwen3:32b, Anthropic claude-opus-4-7)
    - Trigger conditions for v1.5+ feature work (parallel tool exec, message pruning, input_examples, CMA memory, cross-provider fallback)
  affects:
    - Future v1.4.x and v1.5+ planning sessions — seeds resurface when their triggers fire
tech_stack:
  added: []
  patterns:
    - SEED frontmatter schema (name, description, type=forward-looking-idea, planted_during, trigger_when) — verbatim from SEED-AUTH-V1.5.md
    - Five-section markdown body (Idea, Why This Matters, When to Surface, How to Apply, Cross-References) — verbatim from SEED-AUTH-V1.5.md
key_files:
  created:
    - .planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md
    - .planning/seeds/SEED-CLOUD-MODEL-BUMP-V1.4.x.md
    - .planning/seeds/SEED-PARALLEL-TOOL-EXEC-V1.5.md
    - .planning/seeds/SEED-MESSAGE-PRUNING-V1.5.md
    - .planning/seeds/SEED-TOOL-EXAMPLES-V1.5.md
    - .planning/seeds/SEED-CMA-MEMORY-V1.5+.md
    - .planning/seeds/SEED-CROSS-PROVIDER-FALLBACK-V1.5.md
  modified: []
decisions:
  - Seed format mirrors SEED-AUTH-V1.5.md verbatim (frontmatter shape + five markdown sections) so seed-discovery tooling finds them via the same convention
  - Each seed is a single isolated commit (no batching) — atomic per-file commits make the seed-planting workflow legible in git log
  - All seeds tagged planted_during="v1.4 FB-C planning (2026-04-26)" to group them as a single planning cohort
metrics:
  duration_seconds: 295
  duration_human: "~5 minutes"
  tasks_completed: 7
  files_created: 7
  commits: 7
  completed_date: "2026-04-27"
---

# Phase 15 Plan 10: Forward-Looking SEED Files Summary

Planted seven forward-looking SEED markdown files documenting deferred FB-C ideas (model bumps, parallel tool exec, message pruning, tool input_examples, CMA memory, cross-provider fallback) so future planning sessions can resurface them via standard `.planning/seeds/` discovery.

## Files Created

All seven files placed under `.planning/seeds/`. Each file is a single atomic commit so the planting workflow is greppable in git log.

| Seed | Target | Trigger | Commit |
| --- | --- | --- | --- |
| `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` | v1.4.x patch | Post-FB-C UAT baseline established | f165dc6 |
| `SEED-CLOUD-MODEL-BUMP-V1.4.x.md` | v1.4.x patch | Post-FB-C UAT + ANTHROPIC_API_KEY available | 0a73cfd |
| `SEED-PARALLEL-TOOL-EXEC-V1.5.md` | v1.5 milestone | Serial-execution throughput demonstrated as bottleneck | 399cab7 |
| `SEED-MESSAGE-PRUNING-V1.5.md` | v1.5 milestone | Long-session workload hits context window mid-loop | e3eff8b |
| `SEED-TOOL-EXAMPLES-V1.5.md` | v1.4.x or v1.5 | Schema-mismatch retries cited in workload report | 0056999 |
| `SEED-CMA-MEMORY-V1.5+.md` | v1.5 or later | Persistent agent memory becomes an explicit goal OR Anthropic CMA GA | 2f3d39b |
| `SEED-CROSS-PROVIDER-FALLBACK-V1.5.md` | v1.5 milestone | Anthropic outage cited as recurring operational concern | 5e6f74a |

## Mapping to CONTEXT.md `<canonical_refs>` Forward-looking Seeds

The plan derived directly from the seven entries listed in `15-CONTEXT.md` `<canonical_refs>` "Forward-looking seeds (plant during planning)". Each plan task corresponds 1-to-1 with one CONTEXT.md bullet:

| CONTEXT.md bullet | Plan task | Seed file |
| --- | --- | --- |
| qwen2.5-coder:32b → qwen3:32b after assist-01 UAT (D-28) | Task 1 | SEED-DEFAULT-MODEL-BUMP-V1.4.x.md |
| claude-opus-4-6 → claude-opus-4-7 after FB-C UAT (D-30) | Task 2 | SEED-CLOUD-MODEL-BUMP-V1.4.x.md |
| flip parallel: bool = True after serial baseline UAT (D-06) | Task 3 | SEED-PARALLEL-TOOL-EXEC-V1.5.md |
| true history pruning beyond 8 KB ingest truncation | Task 4 | SEED-MESSAGE-PRUNING-V1.5.md |
| Anthropic input_examples field on registered tools | Task 5 | SEED-TOOL-EXAMPLES-V1.5.md |
| Claude Managed Agents memory feature integration | Task 6 | SEED-CMA-MEMORY-V1.5+.md |
| explicit design when sensitive-fallback becomes a need (research §5.4) | Task 7 | SEED-CROSS-PROVIDER-FALLBACK-V1.5.md |

## Milestone Phasing

- **Seeds 1-2** target **v1.4.x patch milestones** — model-default bumps that ride on top of the FB-C ship.
- **Seeds 3-7** target **v1.5+ milestones** — feature work that requires architectural design beyond the v1.4 surface.

`SEED-AUTH-V1.5.md` (existing, planted at v1.4 milestone open on 2026-04-25) is a sibling to these seven. Together with the seven new seeds plus the existing `SEED-STAGED-CLOSURE-V1.5.md` and `SEED-STAGED-REASON-V1.5.md` (planted by FB-A and FB-B respectively), the full v1.5 deferred-work landscape is now captured in the canonical `.planning/seeds/` directory.

## Code/Test Changes

**Zero code or test changes** — pure planning-artifact ship. `git diff --stat 12f41bbd...HEAD` shows exactly 7 files added, all under `.planning/seeds/`, totaling 310 insertions. No source files modified, no tests modified, no `pyproject.toml` change.

## Deviations from Plan

None — plan executed exactly as written. All seven tasks ran with their `<action>` blocks copied verbatim into the seed files, and every acceptance criterion passed on the first verification run.

## Verification Results

All per-task verification commands passed:

- `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md`: `qwen3:32b` count = 7 (≥3), `D-28` count = 1 (≥1), frontmatter type = 1 (==1) — PASS
- `SEED-CLOUD-MODEL-BUMP-V1.4.x.md`: `claude-opus-4-7` count = 5 (≥3), `D-30` count = 3 (≥1), frontmatter type = 1 — PASS
- `SEED-PARALLEL-TOOL-EXEC-V1.5.md`: `parallel` count = 14 (≥5), `D-06` count = 1 (≥1), frontmatter type = 1 — PASS
- `SEED-MESSAGE-PRUNING-V1.5.md`: `pruning` count = 11 (≥5), `research §6.2` count = 1 (≥1), frontmatter type = 1 — PASS
- `SEED-TOOL-EXAMPLES-V1.5.md`: `input_examples` count = 8 (≥4), `research §2.1` count = 2 (≥1), frontmatter type = 1 — PASS
- `SEED-CMA-MEMORY-V1.5+.md`: `Managed Agents` count = 6 (≥2), `research §1` count = 1 (≥1), frontmatter type = 1 — PASS
- `SEED-CROSS-PROVIDER-FALLBACK-V1.5.md`: `fallback` count = 13 (≥5), `research §5.4` count = 3 (≥1), frontmatter type = 1 — PASS

Plan-level verification:

- `ls .planning/seeds/SEED-*.md | wc -l` returned 7 (all 7 new seeds present in worktree; the existing SEED-AUTH-V1.5.md, SEED-STAGED-CLOSURE-V1.5.md, and SEED-STAGED-REASON-V1.5.md live on the main branch and merge cleanly because the worktree adds only NEW files).
- `git diff --stat <base> HEAD` shows exactly 7 files added in `.planning/seeds/` and zero other changes — pure planning-artifact ship.
- `pytest tests/ -x -q` skipped per worktree pure-docs scope (no source/test files touched; no possible regression surface to validate).

## Threat Surface

Per the plan's `<threat_model>`, this plan introduces **no code surface**. The mitigations all relate to the planning workflow's ability to discover and act on seeds in future sessions:

- T-15-53 (frontmatter drift): mitigated — every seed verified with `grep -c "type: forward-looking-idea" == 1`.
- T-15-54 (information disclosure): accepted — seeds contain design intent only, no secrets.
- T-15-55 (seed never resurfaces): mitigated — every seed's `trigger_when` field is concrete (specific milestone or event), and Cross-References pin the original D-XX or research citation.
- T-15-56 (cross-references go stale): accepted — file-level references are durable; line numbers are convenience.

## Self-Check: PASSED

- All 7 seed files exist under `.planning/seeds/` in the worktree
- All 7 commits exist in `git log --oneline -10` (f165dc6, 0a73cfd, 399cab7, e3eff8b, 0056999, 2f3d39b, 5e6f74a)
- `git diff --stat <base> HEAD` matches expectation (7 files, 310 insertions, 0 deletions, 0 source files touched)
