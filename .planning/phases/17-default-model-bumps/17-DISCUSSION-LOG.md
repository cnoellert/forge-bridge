# Phase 17: Default model bumps - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 17-default-model-bumps
**Areas discussed:** Constant extraction, MODEL-02 empirical-UAT timing, Plan structure, Regression unit tests, opus-4-7 temperature seed
**Mode:** standard discuss (advisor mode off — no USER-PROFILE.md)
**Runtime note:** AskUserQuestion not available in this runtime; questions presented as plain-text numbered choices per workflow text-mode fallback.

---

## Constant extraction approach

| Option | Description | Selected |
|--------|-------------|----------|
| Extract `_DEFAULT_*` constants | Refactor inline literals at router.py:188 + :191 into module-level `_DEFAULT_LOCAL_MODEL` / `_DEFAULT_CLOUD_MODEL` mirroring the `_DEFAULT_SYSTEM_PROMPT` pattern at router.py:46. Slightly larger diff but matches SEED + REQUIREMENTS language exactly. | ✓ |
| Bump inline literals | Just flip the string at router.py:188 and :191. Smaller diff, but the seed/REQUIREMENTS language ("`_DEFAULT_*` constant changes") doesn't quite match what's in the file. | |

**User's choice:** Recommendation accepted — extract constants.
**Notes:** "Let's go with recos." Future bumps become a one-line constant change; refactor itself ships as its own commit (P-01) to preserve absolute decoupled-commit purity for the value-flip commits.

---

## MODEL-02 empirical-UAT timing

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-run on assist-01 | Run `FORGE_LOCAL_MODEL=qwen3:32b FB_INTEGRATION_TESTS=1 pytest tests/integration/test_complete_with_tools_live.py::test_ollama_tool_call_loop_live -v` on assist-01 BEFORE plan-phase. Plan resolves deterministically to bump or defer. Mirrors Phase 16.2 / LLMTOOL-01 dedicated-UAT pattern. | ✓ |
| Run during execution | Executor runs the UAT on assist-01, branches based on result. Requires assist-01 access during execute-phase. | |
| Split into two plans | P-EMPIRICAL records result, P-BUMP-OR-DEFER acts on it. Clean separation but heavy for a single ollama+pytest invocation. | |

**User's choice:** Recommendation accepted — pre-run.
**Notes:** Collapses the if-pass-then-bump-else-defer branch at the planning boundary instead of carrying it through plan + execute + verify. Result feeds directly into P-03 plan resolution.

---

## Plan structure

| Option | Description | Selected |
|--------|-------------|----------|
| 1 plan, 2 commits | Both bumps in one plan with two atomic commits. Simpler dependency tracking but harder for /gsd-review or /gsd-undo to address one independently. | |
| 2 plans (no refactor) | P-01 = MODEL-01 bump, P-02 = MODEL-02 bump-or-defer. One isolated commit each. Mirrors requirement boundary. | |
| 3 plans (refactor + 2 bumps) | P-01 = extract `_DEFAULT_*` constants (no behavior change, refactor prep), P-02 = MODEL-01 bump (one-line constant value flip), P-03 = MODEL-02 bump-or-defer. Maximum decoupled-commit purity. | ✓ |

**User's choice:** Recommendation accepted — 3 plans.
**Notes:** Each value-flip commit touches exactly ONE constant value. P-01 absorbs the structural refactor so P-02/P-03 are pure one-line changes that `git blame` will show as model-bump commits, not refactor-with-bump commits. Honors Phase 15 D-30 "isolated commits that touch ONLY `_DEFAULT_*` constants" mandate absolutely.

---

## Regression unit tests

| Option | Description | Selected |
|--------|-------------|----------|
| Add unit tests | Assert `LLMRouter().cloud_model == "claude-sonnet-4-6"` (P-02) and `LLMRouter().local_model == "qwen3:32b"` (P-03 if bump lands). Cheap regression guard runs in default `pytest tests/`. Aligns with SEED-DEFAULT-MODEL-BUMP-V1.4.x step 5. | ✓ |
| Skip — rely on live UAT | LLMTOOL-01/02 are sufficient verification. | |

**User's choice:** Recommendation accepted — add unit tests.
**Notes:** Live UATs are gated on `FB_INTEGRATION_TESTS=1` + API keys; they don't run in default CI. Unit assertion catches accidental constant flip in default `pytest tests/`. If MODEL-02 defers, the local_model assertion test is NOT added (would lock in the deferred state).

---

## opus-4-7 temperature seed

| Option | Description | Selected |
|--------|-------------|----------|
| Plant seed | Create `SEED-OPUS-4-7-TEMPERATURE-V1.5.md` capturing that opus-4-7 rejects `temperature` and that AnthropicAdapter would need a per-model temperature-elision fix before that bump becomes viable. | ✓ |
| Skip | Already noted in v1.4 audit — that's enough. | |

**User's choice:** Recommendation accepted — plant.
**Notes:** Costs nothing, prevents future rediscovery. Memory entries can drift; seeds in `.planning/seeds/` are durable. Plants in P-02 alongside the cloud bump that closes its predecessor seed.

---

## Claude's Discretion

- Exact docstring/comment phrasing on the new `_DEFAULT_*` constants (mirror the `_DEFAULT_SYSTEM_PROMPT` style).
- Whether the new unit-test additions go alongside existing `tests/test_llm.py` cases or in a new dedicated test module.
- Phase SUMMARY structure — follow established v1.4 SUMMARY pattern.

## Deferred Ideas

- AnthropicAdapter `temperature` elision (captured via planted seed; v1.5 target).
- qwen3:32b adoption if pre-run FAILS (re-evaluation deferred to v1.5; SEED-DEFAULT-MODEL-BUMP-V1.4.x stays open and re-targeted).
- Phase 18 (HARNESS-01..03) and Phase 19 (POLISH-01..04) — siblings in v1.4.x, discussed separately.
- SEED-CHAT-STREAMING-V1.4.x — explicitly out-of-scope per v1.4.x REQUIREMENTS.
