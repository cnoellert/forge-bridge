---
phase: 17-default-model-bumps
plan: 03
subsystem: planning/docs
tags: [docs, seeds, model-bump, defer, model-02, qwen3, llm-router]
requires:
  - SEED-DEFAULT-MODEL-BUMP-V1.4.x.md (existing — Phase 17 P-03 amends, does not rewrite)
  - .planning/REQUIREMENTS.md §MODEL-02 acceptance branch (b)
  - .planning/phases/17-default-model-bumps/17-CONTEXT.md §D-02 + §D-03 P-03 + §D-04
provides:
  - .planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md retargeted to v1.5 (durable home for the empirical evidence)
  - MODEL-02 closure against acceptance branch (b)
affects:
  - Future v1.5 milestone planning (seed will resurface when one of three trigger conditions is met)
tech-stack:
  added: []
  patterns:
    - Defer-with-empirical-evidence — seed retargeting + concrete numerics + diagnosis + named candidate fixes (mirrors v1.4 Phase 16.2 D-14 PASS-with-deviations precedent applied to a deferral)
    - Conservative-bump-first — empirical UAT before default change; deferral preserves the v1.4.x baseline
key-files:
  created:
    - .planning/phases/17-default-model-bumps/17-03-SUMMARY.md
  modified:
    - .planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md (retargeted v1.4.x → v1.5; +Empirical Evidence + Candidate v1.5 Fixes + Phase 17 Closure sections; original Idea / Why This Matters / When to Surface / How to Apply / Cross-References sections preserved verbatim)
decisions:
  - MODEL-02 takes acceptance branch (b) — defer the qwen3:32b bump with empirical evidence captured in the seed (2026-04-28 assist-01 pre-run UAT)
  - No regression unit test for `local_model == "qwen2.5-coder:32b"` is added in P-03 (CONTEXT.md D-04: existing `test_default_fallback` already covers it after P-01; adding a `qwen3:32b` assertion would falsely lock in the deferred state)
  - The seed slug `SEED-DEFAULT-MODEL-BUMP-V1.4.x` is preserved (not renamed to V1.5) so `git log` and back-references stay stable; only frontmatter `description` + `trigger_when` flip
metrics:
  duration: ~10min
  tasks: 1
  files: 1
  completed: 2026-04-28
---

# Phase 17 Plan 03: MODEL-02 Deferral — Re-target Seed to v1.5 Summary

One docs commit re-targets `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` to v1.5 and appends three new sections (Empirical Evidence, Candidate v1.5 Fixes, Phase 17 Closure) capturing the 2026-04-28 assist-01 pre-run UAT result; closes MODEL-02 against acceptance branch (b) with no source or test change.

## What Shipped

### File modified

- `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` (78 insertions, 2 deletions, single hunk):
  - **Frontmatter `description`** flipped: now reads "Bump default Ollama tool-call model qwen2.5-coder:32b → qwen3:32b in v1.5 (deferred from v1.4.x Phase 17 — see empirical evidence below)"
  - **Frontmatter `trigger_when`** flipped: now requires "A v1.5 milestone planning session AND one of (a) the default complete_with_tools `max_seconds` budget has been bumped to ≥120s, (b) `OllamaToolAdapter` gains a per-model `think=False` / qwen3 `/no_think` directive, OR (c) router-init adds a warmup-ping path that absorbs cold-start cost"
  - **`name:` field unchanged** — slug `SEED-DEFAULT-MODEL-BUMP-V1.4.x` preserved for git-history stability (convention precedent: v1.4.x-planted concern even after retargeting)
  - **Original sections preserved verbatim:** `## Idea`, `## Why This Matters`, `## When to Surface`, `## How to Apply`, `## Cross-References` — qwen3:32b is still the v1.5 candidate, just gated on additional infrastructure
  - **Three new sections appended:**
    - `## Empirical Evidence (Phase 17 pre-run UAT, 2026-04-28)` — Run 1 cold-start failure (55.2s / 522 tokens / no sentinel / LLMLoopBudgetExceeded), Run 2 warm-start extended-budget pass (39.6s + 18.4s = 58.0s total / 445 + 195 tokens / sentinel returned verbatim), and the diagnosis (qwen3 thinking-mode emits 400-525 tokens/turn at ~10 tok/s on assist-01 → borderline against 60s default; salvage helper handles the shape correctly — no 6th shape, no widening required)
    - `## Candidate v1.5 Fixes (pick one or stack)` — three named options: (1) bump default `max_seconds` 60→120, (2) add qwen3 `/no_think` / `think=False` directive support in `OllamaToolAdapter`, (3) router-init warmup ping
    - `## Phase 17 Closure (2026-04-28)` — explicit closure note naming MODEL-02 acceptance branch (b); confirms `_DEFAULT_LOCAL_MODEL` stays `qwen2.5-coder:32b` through P-01 + P-03; designates the seed as the durable home for the empirical evidence

### Files NOT modified

- `forge_bridge/llm/router.py` — `_DEFAULT_LOCAL_MODEL` stays `"qwen2.5-coder:32b"` (its post-P-01 value)
- `tests/test_llm.py` — no `local_model == "qwen3:32b"` assertion added (would lock in the deferred state); no `local_model == "qwen2.5-coder:32b"` assertion added (existing `test_default_fallback` already covers it after P-01, per CONTEXT.md D-04)
- All other source / test files

### Commit

- `1bb060f` — `docs(seeds): retarget SEED-DEFAULT-MODEL-BUMP-V1.4.x to v1.5 with Phase 17 UAT evidence` (1 file changed, 78 insertions(+), 2 deletions(-))

## Acceptance Criteria — Evidence

| AC | Check | Expected | Actual |
|----|-------|----------|--------|
| 1 | `grep -c '^description: Bump default Ollama tool-call model qwen2.5-coder:32b → qwen3:32b in v1.5' SEED` | 1 | **1 ✓** |
| 2 | `grep -c 'A v1.5 milestone planning session' SEED` | 1 | **1 ✓** |
| 3 | `grep -c '^## Empirical Evidence (Phase 17 pre-run UAT, 2026-04-28)' SEED` | 1 | **1 ✓** |
| 4 | `grep -c '^## Candidate v1.5 Fixes' SEED` | 1 | **1 ✓** |
| 5 | `grep -c 'FORGE-INTEGRATION-SENTINEL-XJK29Q' SEED` | ≥1 | **2 ✓** (Run 1 not-returned + Run 2 returned-verbatim) |
| 6 | `grep -cE '522 completion tokens\|55.2 s' SEED` | ≥1 | **1 ✓** (Run 1 numerics line) |
| 7 | `grep -cE 'Total elapsed: 58.0 s\|58.0 s' SEED` | ≥1 | **1 ✓** (Run 2 total) |
| 8 | `grep -cE '/no_think\|think=False' SEED` | ≥1 | **2 ✓** (candidate fix #2 mentions both) |
| 9 | `grep -c 'warmup' SEED` | ≥1 | **3 ✓** (trigger_when + candidate fix #3 + Diagnosis cross-ref) |
| 10 | `grep -c '^## Idea' SEED` | 1 | **1 ✓** (original section preserved) |
| 11 | `grep -c '^## Why This Matters' SEED` | 1 | **1 ✓** (original section preserved) |
| 12 | `grep -c '^## How to Apply' SEED` | 1 | **1 ✓** (original section preserved) |
| 13 | `grep -c '^## Cross-References' SEED` | 1 | **1 ✓** (original section preserved) |
| 14 | `git diff --name-only HEAD~1 HEAD` | exactly `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` | **`.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` ✓** (one file, nothing else) |
| 15 | `git diff HEAD~1 HEAD -- forge_bridge/llm/router.py` | empty | **empty ✓** (no source change in P-03) |
| 16 | `git diff HEAD~1 HEAD -- tests/` | empty | **empty ✓** (no test change in P-03) |
| 17 | `git diff HEAD~1 HEAD -- forge_bridge/` | empty | **empty ✓** (no source-tree change at all) |

All 17 acceptance criteria PASS. The commit is provably docs-only.

## MODEL-02 Closure

MODEL-02 closed against **REQUIREMENTS.md MODEL-02 acceptance branch (b)** — verbatim:

> "(b) bump deferred with a phase-17 SUMMARY note citing specific qwen3:32b failure modes that block the conservative-bump-first pattern."

**One-line deferral rationale:** The 2026-04-28 assist-01 pre-run UAT (CONTEXT.md D-02) showed qwen3:32b's mechanics work end-to-end (salvage helper handles the shape, 2-step loop completes when given enough wall-clock budget) but thinking-mode completion-token verbosity (400-525 tokens/turn vs ~50 for qwen2.5-coder, at ~10 tok/s on assist-01) pushes the loop's total elapsed past the default `max_seconds=60` budget on cold-start runs — borderline non-deterministic.

**Durable home for the empirical evidence:** The bumped seed at `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` (specifically the new `## Empirical Evidence (Phase 17 pre-run UAT, 2026-04-28)` and `## Candidate v1.5 Fixes` sections). The Phase 17 SUMMARY (workflow artifact owned by the orchestrator after the wave completes) cites this seed.

## Deviations from Plan

**None.** Plan executed exactly as written:

- One file modified, one atomic commit
- Frontmatter `description` + `trigger_when` flipped per the plan's exact strings
- Two new sections appended (Empirical Evidence + Candidate v1.5 Fixes); a third closure paragraph appended exactly per the plan's specified Markdown
- `name:` field preserved (file slug stays for git history)
- Original sections (`## Idea`, `## Why This Matters`, `## When to Surface`, `## How to Apply`, `## Cross-References`) preserved verbatim
- No source change to `forge_bridge/llm/router.py`; no test change to `tests/test_llm.py`
- Commit message exactly per the plan's <action> block (subject + body)

No deviation rules were triggered (Rules 1-3). No checkpoints (autonomous plan). No auth gates.

## Threat Surface

Per the plan's `<threat_model>`: documentation-only change, no source code, no API surface, no I/O. No new trust boundary, no new STRIDE threats. T-17.03-01 disposition `accept` is honored — ASVS L1 sufficient.

No threat flags surfaced during execution.

## Self-Check: PASSED

- File created: `.planning/phases/17-default-model-bumps/17-03-SUMMARY.md` — **FOUND**
- File modified: `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` — **FOUND** (verified via `git diff --name-only HEAD~1 HEAD`)
- Commit: `1bb060f` (`docs(seeds): retarget SEED-DEFAULT-MODEL-BUMP-V1.4.x to v1.5 with Phase 17 UAT evidence`) — verified after this SUMMARY commits via the `git log` check below
- All 17 acceptance criteria from the plan: **PASS** (see table above)
- No source files touched (`git diff HEAD~1 HEAD -- forge_bridge/`): **empty**
- No test files touched (`git diff HEAD~1 HEAD -- tests/`): **empty**
- MODEL-02 closure language matches REQUIREMENTS.md branch (b) verbatim: **YES**
