# Phase 17: Default model bumps - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning
**Milestone:** v1.4.x Carry-Forward Debt
**Requirements:** MODEL-01, MODEL-02

<domain>
## Phase Boundary

Phase 17 delivers two **isolated, decoupled commits** to `forge_bridge/llm/router.py` that flip the default LLM model strings:

- **MODEL-01 (unconditional):** `cloud_model` default `claude-opus-4-6` → `claude-sonnet-4-6`. The current default returns 500 from the live Anthropic API (deprecated alias); `claude-sonnet-4-6` was already verified passing in v1.4 LLMTOOL-02 UAT after the SDK API-drift fixes (`tool_choice` + `additionalProperties: false`).
- **MODEL-02 (conditional):** `local_model` default `qwen2.5-coder:32b` → `qwen3:32b` IF a re-run of LLMTOOL-01 (`test_ollama_tool_call_loop_live`) against `qwen3:32b` on assist-01 PASSES with the widened salvage helper from commit `a4eaa5c`. Otherwise hold the bump and record the empirical evidence in the phase SUMMARY for v1.5 reconsideration.

**No tool-loop, adapter, chat-handler, or wire-format code is touched.** The diff scope per requirement is one literal value. The decoupled-commit mandate from Phase 15 D-30 ("isolated commits that touch ONLY `_DEFAULT_*` constants — must NOT be coupled to loop logic") is binding here.

**Out of scope (deferred to v1.5):** AnthropicAdapter `temperature` elision needed for `claude-opus-4-7` (which rejects `temperature` per v1.4 audit); any sensitive-routing changes (waits on auth); SEED-CHAT-STREAMING-V1.4.x (trigger condition not surfaced).

</domain>

<decisions>
## Implementation Decisions

### Source layout (constant extraction)

- **D-01:** Refactor inline string literals at `forge_bridge/llm/router.py:188` and `:191` into module-level constants `_DEFAULT_LOCAL_MODEL` and `_DEFAULT_CLOUD_MODEL`. Mirror the existing `_DEFAULT_SYSTEM_PROMPT` precedent (router.py:46) — module-level definition, consumed by `__init__` via `os.environ.get(..., _DEFAULT_*)`. Rationale: matches the SEED + REQUIREMENTS language exactly ("`_DEFAULT_*` constant changes"), and makes every future bump a one-line literal flip with zero risk of touching surrounding code. The extraction itself is a pure refactor (no behavior change) and ships as its own commit, preserving absolute decoupled-commit purity for the two value-flip commits that follow.

### MODEL-02 empirical-UAT timing (gating signal)

- **D-02:** Pre-run the qwen3:32b live UAT on assist-01 BEFORE plan-phase locks the plan. The empirical result (PASS in <60s with sentinel `FORGE-INTEGRATION-SENTINEL-XJK29Q` correctly returned, OR specific failure mode) is fed into planning so plan resolution is deterministic — either "bump" or "defer with SUMMARY note." Mirrors the Phase 16.2 / LLMTOOL-01 dedicated-UAT pattern (gather empirical evidence on assist-01, then plan with known result). Rationale: avoids carrying a conditional "if-pass-then-bump-else-defer" branch through plan + execute + verify; collapses the branch at the planning boundary. UAT command: `FORGE_LOCAL_MODEL=qwen3:32b FB_INTEGRATION_TESTS=1 pytest tests/integration/test_complete_with_tools_live.py::test_ollama_tool_call_loop_live -v` on assist-01.

### Plan structure

- **D-03:** Three plans, three commits, in this order:
  - **P-01: Extract `_DEFAULT_*` constants** — pure refactor in `forge_bridge/llm/router.py`. Adds `_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"` and `_DEFAULT_CLOUD_MODEL = "claude-opus-4-6"` at module scope (preserving current values), updates `__init__` to consume them. No behavior change. Default unit-test suite still passes 758/758.
  - **P-02: MODEL-01 bump (cloud)** — flip `_DEFAULT_CLOUD_MODEL` value `"claude-opus-4-6"` → `"claude-sonnet-4-6"`. Single one-line constant change. Acceptance: `LLMRouter().cloud_model == "claude-sonnet-4-6"` (new unit test) AND LLMTOOL-02 (`test_anthropic_tool_call_loop_live`) PASSES against the new default with no env override (re-run live on dev).
  - **P-03: MODEL-02 bump-or-defer (local)** — branch on D-02 empirical result:
    - **If pre-run PASSED:** flip `_DEFAULT_LOCAL_MODEL` value `"qwen2.5-coder:32b"` → `"qwen3:32b"`. Single one-line constant change. Acceptance: `LLMRouter().local_model == "qwen3:32b"` (new unit test) AND LLMTOOL-01 PASSES against the new default in <60s on assist-01.
    - **If pre-run FAILED:** no source change. Plan ships only a SUMMARY note documenting the specific qwen3:32b failure modes that block the conservative-bump-first pattern, plus a re-evaluation trigger for v1.5. Acceptance: phase SUMMARY records empirical evidence; SEED-DEFAULT-MODEL-BUMP-V1.4.x stays open and is re-targeted to v1.5.

  Rationale: maximum decoupled-commit purity per D-30. Each value-flip commit touches exactly ONE constant value. P-01 absorbs the structural refactor so P-02/P-03 are pure one-line changes that `git blame` will show as model-bump commits, not refactor-with-bump commits.

### Regression unit tests

- **D-04:** Add `tests/test_llm.py` assertions that `LLMRouter().cloud_model == "claude-sonnet-4-6"` (in P-02) and `LLMRouter().local_model == "qwen3:32b"` (in P-03 if bump lands). These are cheap default-value regression guards that run in default `pytest tests/` (no `FB_INTEGRATION_TESTS=1` required, no API keys). Live UATs (LLMTOOL-01/02) are gated and don't run in default CI; a unit-test default-value assertion catches accidental constant flips. Aligns with SEED-DEFAULT-MODEL-BUMP-V1.4.x step 5 ("Add a regression test asserting the default has been bumped"). If MODEL-02 defers, the local_model assertion test is NOT added (would lock in the deferred state).

### Forward-looking seed

- **D-05:** Plant `SEED-OPUS-4-7-TEMPERATURE-V1.5.md` at the end of P-02 capturing two facts surfaced during v1.4 close-out: (a) `claude-opus-4-7` rejects `temperature` ("temperature is deprecated for this model"), and (b) AnthropicAdapter currently always passes `temperature` in its request payload. Trigger: a v1.5 cloud-model bump consideration AND/OR Anthropic deprecation of `claude-sonnet-4-6`. Apply: per-model temperature elision in AnthropicAdapter (or pre-flight detection) before the bump becomes viable. Rationale: knowledge captured in audit + memory; seed file makes it durable in `.planning/seeds/` where future-you will look during v1.5 planning.

### Claude's Discretion

- Exact docstring/comment phrasing on the new `_DEFAULT_*` constants (mirror the `_DEFAULT_SYSTEM_PROMPT` style — short rationale + caller-override note).
- Whether the new unit-test additions go alongside existing `tests/test_llm.py` cases or in a new dedicated `test_llm_defaults.py` (whichever fits the existing test-file conventions).
- Phase SUMMARY structure — follow the established v1.4 SUMMARY pattern (gates table + final-status section + carry-forward addendum if any).

### Folded Todos

None. (`gsd-tools todo match-phase 17` returned 0 matches.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap

- `.planning/REQUIREMENTS.md` §MODEL — MODEL-01 + MODEL-02 acceptance criteria (single source of truth for what "done" looks like)
- `.planning/ROADMAP.md` §v1.4.x Carry-Forward Debt — Phase 17 row + milestone goal + out-of-scope list
- `.planning/STATE.md` — current position, v1.4.x milestone metadata, Next-action note for Phase 17

### Seeds being closed by this phase

- `.planning/seeds/SEED-CLOUD-MODEL-BUMP-V1.4.x.md` — closed by MODEL-01 (note: seed originally targeted opus-4-7; REQUIREMENTS overrode to sonnet-4-6 because opus-4-7 rejects `temperature` per v1.4 audit line 273)
- `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` — closed by MODEL-02 (apply step 5: add regression test asserting bumped default; planning-time pre-run UAT replaces seed step 2's "after FB-C ships, run UAT")

### Decisive prior-phase context

- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` §"LLMTOOL-02 — Anthropic live UAT PASSED" (line 267 onward) — empirical evidence that `claude-sonnet-4-6` is verified passing; opus-4-7 `temperature` rejection note (line 273)
- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` §"LLMTOOL-01 dedicated sentinel UAT + WR-01 closure" — widened salvage helper (`_try_parse_text_tool_call`) from commit `a4eaa5c` is what the qwen3:32b pre-run UAT exercises
- Phase 15 (FB-C) D-30 — "Stay on `claude-opus-4-6` for FB-C ship. Plant `SEED-CLOUD-MODEL-BUMP-V1.4.x.md` for the bump as an isolated commit after FB-C UAT." Mandate carries forward into Phase 17 commit structure.
- Phase 15 (FB-C) D-28 — "Stay on qwen2.5-coder:32b for FB-C ship; bump after assist-01 UAT" (conservative-bump-first pattern; empirical evidence required before default change).

### Source files in scope

- `forge_bridge/llm/router.py:46` — `_DEFAULT_SYSTEM_PROMPT` precedent for constant extraction style
- `forge_bridge/llm/router.py:188` — current inline literal `"qwen2.5-coder:32b"` (target of MODEL-02)
- `forge_bridge/llm/router.py:191` — current inline literal `"claude-opus-4-6"` (target of MODEL-01)
- `forge_bridge/llm/router.py:160-169` — class docstring with current default values; update alongside constants

### Tests in scope

- `tests/integration/test_complete_with_tools_live.py::test_anthropic_tool_call_loop_live` — LLMTOOL-02 live UAT (P-02 verification gate; runs on dev with `FB_INTEGRATION_TESTS=1` + `ANTHROPIC_API_KEY`)
- `tests/integration/test_complete_with_tools_live.py::test_ollama_tool_call_loop_live` — LLMTOOL-01 live UAT (D-02 pre-run gate AND P-03 verification gate; runs on assist-01 with `FB_INTEGRATION_TESTS=1` + `FORGE_LOCAL_MODEL=qwen3:32b` for pre-run)
- `tests/test_llm.py` — target for new default-value regression assertions per D-04
- `forge_bridge/llm/_adapters.py` — `_OLLAMA_TOOL_MODELS` allow-list already includes `qwen3:32b` per Phase 15 D-29 (no allow-list change needed)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_DEFAULT_SYSTEM_PROMPT` constant pattern (router.py:46)** — module-level constant with leading docstring describing rationale and caller-override semantics. The two new `_DEFAULT_*` constants should mirror this style precisely (short comment block, then `NAME = "value"`, consumed via `os.environ.get("ENV_VAR", _DEFAULT_NAME)`).
- **Widened salvage helper (`_adapters.py::_try_parse_text_tool_call`)** — closed WR-01 in commit `a4eaa5c`, handles 5 known qwen2.5-coder tool-call shapes including trailing-prose and markdown-fenced variants. The qwen3:32b pre-run UAT directly exercises this code path; if qwen3:32b emits a 6th shape, MODEL-02 will surface it.
- **`_OLLAMA_TOOL_MODELS` allow-list (`_adapters.py`)** — already includes `qwen3:32b` per Phase 15 D-29. No allow-list edit required for MODEL-02; only the default literal changes.

### Established Patterns

- **Single-commit isolation for default changes** — Phase 15 D-30 mandate. Every `git log forge_bridge/llm/router.py` line that flips a default value must be a one-line change, separable for `git revert` and `gsd-undo`. P-01 (refactor) buys this purity for P-02 + P-03.
- **Live UAT gating via `FB_INTEGRATION_TESTS=1`** — integration tests are opt-in to keep default `pytest tests/` fast and CI-green without API keys. Default-value regression assertions go in unit tests (default suite), not integration tests.
- **Phase SUMMARY pattern** — gates table + final-status section + carry-forward addendum (see Phase 16.2 SUMMARY for canonical structure). Phase 17 SUMMARY follows this; if MODEL-02 defers, the carry-forward addendum is the home for the empirical evidence.

### Integration Points

- `forge_bridge/llm/router.py` is the ONLY source file touched across all three plans. No imports change, no public API change, no `__init__.py` barrel change.
- `tests/test_llm.py` gets new default-value assertions in P-02 (and P-03 if the bump lands).
- `.planning/seeds/SEED-OPUS-4-7-TEMPERATURE-V1.5.md` is created in P-02 (plants the v1.5 follow-up).

</code_context>

<specifics>
## Specific Ideas

- **MODEL-01 target is `claude-sonnet-4-6`, NOT `claude-opus-4-7`** despite the SEED-CLOUD-MODEL-BUMP-V1.4.x seed originally calling for opus-4-7. Reason: opus-4-7 rejects `temperature` (audit line 273), and AnthropicAdapter currently always sends temperature. Switching to opus-4-7 would require an adapter change, which violates the Phase 17 "isolated default-only change" boundary. sonnet-4-6 is empirically verified passing.
- **MODEL-02 pre-run UAT command** (run on assist-01 before plan-phase): `FORGE_LOCAL_MODEL=qwen3:32b FB_INTEGRATION_TESTS=1 pytest tests/integration/test_complete_with_tools_live.py::test_ollama_tool_call_loop_live -v`. PASS = sentinel substring `FORGE-INTEGRATION-SENTINEL-XJK29Q` returned in <60s. Bring the result back to plan-phase (paste output or summarize PASS/FAIL + duration + any unexpected emit shapes).
- **MODEL-01 verification command** (run on dev after P-02 lands): `FB_INTEGRATION_TESTS=1 ANTHROPIC_API_KEY=... pytest tests/integration/test_complete_with_tools_live.py::test_anthropic_tool_call_loop_live -v` — note the deliberate ABSENCE of `FORGE_CLOUD_MODEL=...` env override; that's the acceptance criterion ("LLMTOOL-02 still passes against the new default with no env override").

</specifics>

<deferred>
## Deferred Ideas

- **AnthropicAdapter `temperature` elision** — needed before any bump to `claude-opus-4-7` becomes viable. Captured in `SEED-OPUS-4-7-TEMPERATURE-V1.5.md` (planted in P-02 per D-05). Targets v1.5 milestone consideration.
- **`qwen3:32b` adoption if pre-run FAILS** — re-evaluation deferred to v1.5; SEED-DEFAULT-MODEL-BUMP-V1.4.x stays open and is re-targeted with empirical failure evidence.
- **Phase 18 (HARNESS-01..03) and Phase 19 (POLISH-01..04)** — siblings in the v1.4.x milestone, NOT in scope here. Will be discussed in their own `/gsd-discuss-phase 18` and `/gsd-discuss-phase 19` sessions.
- **SEED-CHAT-STREAMING-V1.4.x** — explicitly out-of-scope per v1.4.x REQUIREMENTS (trigger condition was not reported in Phase 16.2 UAT).

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 17` returned 0 matches.

</deferred>

---

*Phase: 17-default-model-bumps*
*Context gathered: 2026-04-28*
