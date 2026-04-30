---
phase: 17-default-model-bumps
verified: 2026-04-28T22:00:00Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 17: Default Model Bumps Verification Report

**Phase Goal:** Bump `_DEFAULT_CLOUD_MODEL` from `claude-opus-4-6` to `claude-sonnet-4-6` (MODEL-01); decide on `_DEFAULT_LOCAL_MODEL` bump from `qwen2.5-coder:32b` to `qwen3:32b` based on assist-01 UAT (MODEL-02 — accept either branch (a) ship the bump OR (b) defer with phase-17 SUMMARY note citing specific qwen3:32b failure modes). Closes SEED-CLOUD-MODEL-BUMP-V1.4.x and SEED-DEFAULT-MODEL-BUMP-V1.4.x. Single-commit isolated `_DEFAULT_*` constant changes per Phase 15 D-30 decoupled-commit mandate.
**Verified:** 2026-04-28T22:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Aggregated must_haves across 17-01 / 17-02 / 17-03 plan frontmatter, deduped to a single set covering both MODEL-01 (cloud bump) and MODEL-02 (deferral via seed retargeting + SUMMARY note).

| #  | Truth                                                                                                                                                                                                                  | Status     | Evidence |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------- |
| 1  | Module-level `_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"` exists in `forge_bridge/llm/router.py`                                                                                                                       | VERIFIED   | router.py:64 — single occurrence at module scope |
| 2  | Module-level `_DEFAULT_CLOUD_MODEL = "claude-sonnet-4-6"` exists in `forge_bridge/llm/router.py` (post-P-02 value)                                                                                                     | VERIFIED   | router.py:72 — single occurrence at module scope |
| 3  | `LLMRouter.__init__` consumes both constants via `os.environ.get(env_var, _DEFAULT_*)` (no inline literals at consumption sites)                                                                                       | VERIFIED   | router.py:201-206 — both consumption sites rewired; `grep -c` for old inline literals at consumption sites returns 0 |
| 4  | `LLMRouter().local_model == "qwen2.5-coder:32b"` (default behavior preserved through P-01 + P-03)                                                                                                                      | VERIFIED   | Live `python -c` smoke test: `INST_LOCAL = 'qwen2.5-coder:32b'`; `tests/test_llm.py::test_default_fallback` line 94 asserts the same |
| 5  | `LLMRouter().cloud_model == "claude-sonnet-4-6"` (post-MODEL-01 value)                                                                                                                                                 | VERIFIED   | Live `python -c` smoke test: `INST_CLOUD = 'claude-sonnet-4-6'`; `tests/test_llm.py::test_default_fallback` line 95 asserts the same |
| 6  | Default-suite regression test in `tests/test_llm.py::test_default_fallback` updated to assert `claude-sonnet-4-6` and runs without API keys / `FB_INTEGRATION_TESTS=1`                                                  | VERIFIED   | `pytest tests/test_llm.py::test_default_fallback -v` → 1 passed in 0.01s; `grep -c 'claude-opus-4-6' tests/test_llm.py` → 0 |
| 7  | Live LLMTOOL-02 (`test_anthropic_tool_call_loop_live`) PASSED against the new default with NO `FORGE_CLOUD_MODEL` env override                                                                                          | VERIFIED   | 17-02-SUMMARY captures the live PASS: 1 passed in 4.52s; user resume signal `LLMTOOL-02 PASS` confirmed; sentinel `FORGE-INTEGRATION-SENTINEL` returned in terminal LLM response |
| 8  | `SEED-OPUS-4-7-TEMPERATURE-V1.5.md` exists in `.planning/seeds/` and captures (a) opus-4-7 rejects temperature per v1.4 audit line 273, (b) AnthropicAdapter currently always sends `temperature`                       | VERIFIED   | File exists (4169 bytes); frontmatter `name: SEED-OPUS-4-7-TEMPERATURE-V1.5`; lines 13-14 capture fact (a); lines 40-42 capture fact (b); cross-ref to "audit, line 273" present |
| 9  | The MODEL-01 bump commit on `forge_bridge/llm/router.py` is a one-line value flip (no other source lines change in that commit)                                                                                         | VERIFIED   | Commit `edbfef6` diffstat: 2 files (router.py, test_llm.py), 8 insertions / 6 deletions — confined to the constant + comment-block + docstring mirrors + the regression-test assertion. `git diff edbfef6 -- forge_bridge/llm/router.py` shows no method-body changes |
| 10 | `_DEFAULT_LOCAL_MODEL` value remains `qwen2.5-coder:32b` (MODEL-02 takes deferral branch (b) — no source change in P-03)                                                                                                | VERIFIED   | router.py:64 still reads `_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"`; `git diff 1bb060f~1 1bb060f -- forge_bridge/` is empty |
| 11 | `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` re-targeted to v1.5 and amended with empirical evidence (cold-run failure, warm-run extended-budget pass, qwen3 thinking-mode token verbosity diagnosis, 3 candidate v1.5 fixes)   | VERIFIED   | Frontmatter `description` retargeted to v1.5; `## Empirical Evidence (Phase 17 pre-run UAT, 2026-04-28)` section appended with Run 1 / Run 2 numerics + sentinel echo; `## Candidate v1.5 Fixes` section with all three options (max_seconds bump, qwen3 `/no_think`, warmup ping); `## Phase 17 Closure (2026-04-28)` paragraph naming acceptance branch (b) |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `forge_bridge/llm/router.py` | Two module-level `_DEFAULT_*` constants; `__init__` rewired to consume them; `_DEFAULT_CLOUD_MODEL = "claude-sonnet-4-6"` post-P-02; `_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"` preserved | VERIFIED | All four expected lines present (constants at 64, 72; consumption sites at 201-206); class docstring updated to `Model: claude-sonnet-4-6` and `FORGE_CLOUD_MODEL default: claude-sonnet-4-6`; gsd-tools artifact verify all_passed=true |
| `tests/test_llm.py` | `test_default_fallback` asserts `cloud_model == "claude-sonnet-4-6"` and `local_model == "qwen2.5-coder:32b"`; runs in default suite (no API keys / FB_INTEGRATION_TESTS gate) | VERIFIED | Lines 94-95 contain the asserted defaults; `pytest tests/test_llm.py::test_default_fallback -v` passes in 0.01s; `grep -c 'claude-opus-4-6' tests/test_llm.py` → 0 |
| `.planning/seeds/SEED-OPUS-4-7-TEMPERATURE-V1.5.md` | New file capturing v1.5 follow-up (per-model temperature elision in AnthropicAdapter) with frontmatter, two facts, How-to-Apply, Cross-References | VERIFIED | File present (84 lines, 4169 bytes); frontmatter slug correct; `temperature is deprecated` substring present (line 14); `## How to Apply` and `## Cross-References` sections both present |
| `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` | Retargeted to v1.5 with empirical evidence + candidate fixes + Phase 17 closure; original sections (Idea / Why This Matters / When to Surface / How to Apply / Cross-References) preserved | VERIFIED | Frontmatter `description` retargeted; original 5 sections preserved; 3 new sections appended (Empirical Evidence with Run 1 / Run 2 numerics, Candidate v1.5 Fixes, Phase 17 Closure naming branch (b)); sentinel `FORGE-INTEGRATION-SENTINEL-XJK29Q` cited at lines 63 + 70 |

**Wiring (Level 3):** All artifacts wired:
- Both `_DEFAULT_*` constants are imported by `LLMRouter.__init__` (router.py:202, 205) — same module, no import statement required.
- `tests/test_llm.py::test_default_fallback` instantiates `LLMRouter()` and asserts the propagated default values — closes the loop from constant → instance attribute.

**Data flow (Level 4):** N/A for this phase. The "data" is constant strings; the integration test (LLMTOOL-02 live, captured in 17-02-SUMMARY) confirms the constants flow through to the live Anthropic API request body.

---

### Key Link Verification

Note: gsd-tools `verify key-links` returned "Source file not found" for all links because the `from:` field in the plan frontmatter uses prose descriptions (e.g., "LLMRouter.__init__ (router.py ~line 188)") rather than parseable file paths. Manual verification confirmed each link below.

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `LLMRouter.__init__` (router.py:201) | `_DEFAULT_LOCAL_MODEL` constant | `os.environ.get("FORGE_LOCAL_MODEL", _DEFAULT_LOCAL_MODEL)` | WIRED | Confirmed via direct read of router.py:201-203 |
| `LLMRouter.__init__` (router.py:204) | `_DEFAULT_CLOUD_MODEL` constant | `os.environ.get("FORGE_CLOUD_MODEL", _DEFAULT_CLOUD_MODEL)` | WIRED | Confirmed via direct read of router.py:204-206 |
| `tests/test_llm.py::test_default_fallback` (line 95) | `_DEFAULT_CLOUD_MODEL` constant value | default-instantiation regression assertion `assert router.cloud_model == "claude-sonnet-4-6"` | WIRED | Test passes; constant value flows through `LLMRouter()` → instance attribute → assertion |
| `test_anthropic_tool_call_loop_live` (live) | `LLMRouter()` default `cloud_model` | live Anthropic API tool-call loop with NO `FORGE_CLOUD_MODEL` env override | WIRED | 17-02-SUMMARY records `LLMTOOL-02 PASSED [100%]` in 4.52s under the no-override regime |
| MODEL-02 acceptance branch (b) | `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` (re-targeted) | empirical-evidence section + v1.5 retargeting | WIRED | Seed retargeted (`description` line 3, `trigger_when` line 6); empirical evidence section present; closure paragraph naming branch (b) on lines 113-121 |
| Phase 17 SUMMARY (in 17-03-SUMMARY.md) | `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` | carry-forward addendum reference | WIRED | 17-03-SUMMARY references `SEED-DEFAULT-MODEL-BUMP` 12 times including explicit "Durable home for the empirical evidence: The bumped seed at .planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md" |

---

### Data-Flow Trace (Level 4)

Skipped — phase produces module-level constants and documentation, not dynamic data sources. The closest analogue (constants flowing into live API requests) is exercised end-to-end by LLMTOOL-02 live UAT, captured under Truth #7.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Constants importable + correct values | `python -c "from forge_bridge.llm.router import _DEFAULT_LOCAL_MODEL, _DEFAULT_CLOUD_MODEL; ..."` | `CONST_LOCAL = 'qwen2.5-coder:32b'` / `CONST_CLOUD = 'claude-sonnet-4-6'` / `ok` | PASS |
| `LLMRouter()` defaults flow through | Same script — `r = LLMRouter()` then `r.local_model` / `r.cloud_model` | `INST_LOCAL = 'qwen2.5-coder:32b'` / `INST_CLOUD = 'claude-sonnet-4-6'` | PASS |
| Default-suite regression test | `pytest tests/test_llm.py::test_default_fallback -v -p no:pytest-blender` | 1 passed, 1 warning in 0.01s | PASS |
| Old cloud literal purged from test | `grep -c 'claude-opus-4-6' tests/test_llm.py` | 0 | PASS |
| Commit shape isolation (P-02) | `git show --stat edbfef6` | 2 files (router.py, test_llm.py), 8 insertions / 6 deletions | PASS |
| Commit shape isolation (P-03) | `git show --stat 1bb060f` (one file: the seed) | seed only — no source / test files | PASS |
| Commit shape isolation (P-01 refactor) | `git show --stat 9a9b7b9` | router.py only | PASS |
| All cited commits exist on main | `git log --oneline | grep -E '9a9b7b9|edbfef6|05c5f78|1bb060f|7722f1c'` | All five commits found in `git log --oneline` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| MODEL-01 | 17-01, 17-02 | `_DEFAULT_CLOUD_MODEL` flips `claude-opus-4-6` → `claude-sonnet-4-6`; LLMTOOL-02 still passes against the new default with no env override; no other source files touched in the same commit | SATISFIED | `_DEFAULT_CLOUD_MODEL = "claude-sonnet-4-6"` at router.py:72; default-suite test asserts new value; live LLMTOOL-02 PASS (4.52s, no env override) captured in 17-02-SUMMARY; commit `edbfef6` touches router.py + test_llm.py only |
| MODEL-02 | 17-01, 17-03 | `_DEFAULT_LOCAL_MODEL` flips `qwen2.5-coder:32b` → `qwen3:32b` IF assist-01 UAT passes; OTHERWISE bump deferred with phase-17 SUMMARY note citing specific qwen3:32b failure modes | SATISFIED (branch b) | Pre-run UAT showed cold-start LLMLoopBudgetExceeded (522 tokens / 55.2s iter 1) + warm-run pass (58.0s total, sentinel returned); branch (b) deferral evidence durably captured in retargeted seed; failure mode (qwen3 thinking-mode 400-525 tokens/turn vs ~50 for qwen2.5-coder) explicitly cited; 17-03-SUMMARY explicitly closes against branch (b) |

**Orphaned check:** REQUIREMENTS.md traceability table maps only MODEL-01 + MODEL-02 to Phase 17. Both are claimed by plan frontmatter (17-01 lists both, 17-02 lists MODEL-01, 17-03 lists MODEL-02). No orphaned requirements.

---

### Anti-Patterns Found

None.

`grep -nE "TODO|FIXME|XXX|HACK|placeholder|not.yet.implemented" forge_bridge/llm/router.py` returned no matches. The seed files contain forward-looking "How to Apply" steps but those are intentional — seeds document v1.5 work, not Phase 17 stubs.

The 17-02-SUMMARY "Plan-internal contradictions" section flags two unsatisfiable grep-pattern acceptance criteria from the plan (the historical `claude-opus-4-6` reference deliberately preserved in the comment block per the plan's verbatim prescribed text; backtick-interrupted `AnthropicAdapter currently` grep). Per the phase_specific_notes guidance: verbatim text precedence is the right call. Verifier accepts this resolution — semantic content is met, the grep patterns were authored before the verbatim text was finalized.

---

### Human Verification Required

None. The only human-in-the-loop gate (live LLMTOOL-02 UAT in 17-02 Task 3) was already executed and confirmed PASSED with the user's resume signal `LLMTOOL-02 PASS`. All remaining acceptance criteria are programmatically verifiable and pass.

---

### Gaps Summary

None. All 11 must-haves verified. MODEL-01 closed via the cloud-default flip + live LLMTOOL-02 PASS. MODEL-02 closed via acceptance branch (b) — deferral with empirical evidence durably captured in the retargeted SEED-DEFAULT-MODEL-BUMP-V1.4.x.md seed and explicit closure note in 17-03-SUMMARY.md. Decoupled-commit purity preserved across all four task commits (`9a9b7b9` refactor, `edbfef6` MODEL-01 bump + regression test, `05c5f78` SEED-OPUS-4-7 plant, `1bb060f` SEED-DEFAULT retarget). Default test suite green at 763 passed / 117 skipped post-merge.

Phase 17 goal achieved.

---

_Verified: 2026-04-28T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
