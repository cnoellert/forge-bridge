# Phase 19: Code-quality polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `19-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 19-code-quality-polish
**Mode:** discuss (text mode — `AskUserQuestion` not exposed in this runtime; fell back to plain-text numbered prompts per workflow)
**Areas discussed:** Commit structure, POLISH-01 ref derivation, POLISH-02 closure scope, POLISH-03 atomicity rewrite scope, POLISH-04 strip layer + tokens + RED test
**User mode:** "Recos" — accept all recommended defaults

---

## Pre-discussion baseline (live, recorded during context-gathering)

| Check | Result | Decision impact |
|-------|--------|-----------------|
| `grep -rn '"(missing)"' forge_bridge/ tests/` | 1 hit, comment-only at `forge_bridge/store/staged_operations.py:326` | POLISH-02 collapses to verification-led closure (D-05..D-07) |
| `grep -rn "im_start\|im_end\|endoftext" tests/ forge_bridge/` | `INJECTION_MARKERS` already lists `<\|im_start\|>` at `_sanitize_patterns.py:25`; tests exist for `_sanitize_tag` rejection of these tokens | POLISH-04 extends existing infrastructure rather than greenfielding |
| `forge_bridge/llm/_adapters.py:206` | Hardcoded `ref=f"0:{name}"`; structured path uses `f"{idx}:{name}"` at line 531 | Confirms POLISH-01 surface area |
| `tests/test_staged_operations.py:340-400` | `assert True  # placeholder` at 363; `assert row is None` at 388 (the actually-failing one) | Confirms POLISH-03 surface area + Phase 18 D-07 deferral logic |

---

## Commit structure

| Option | Description | Selected |
|--------|-------------|----------|
| 4 isolated plans / 4 commits | One plan per POLISH; mirrors Phase 17 D-30 + Phase 18 D-01 | ✓ |
| Grouped (LLM 01+04, store/test 02+03) | Two plans, two commits, by code area | |
| Single bulk commit | All four POLISH closures in one plan/commit | |

**User's choice:** 4 isolated plans / 4 commits.
**Notes:** User originally proposed 4x4 explicitly, then asked for confirmation it made sense. Recommendation matched user intent. Captured as D-01.

---

## POLISH-01 — ref derivation strategy

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Compute at call site | `salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.name}")` after salvage append | ✓ |
| (b) Pass index into helper | `_try_parse_text_tool_call(text, idx=len(tool_calls))` | |
| (c) Assert precondition | `assert len(tool_calls) == 0; ref="0:..."` (preserves literal) | |

**User's choice:** (a) — recommended option.
**Notes:** Helper stays context-free; no signature churn; uses `dataclasses.replace()` for frozen dataclass mutation. Captured as D-02..D-04. Acceptance per REQUIREMENTS.md: literal `"0:"` MUST NOT appear in the helper or its call site.

---

## POLISH-02 — closure scope

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Verification-led (baseline-first) | Confirm literal absence, delete misleading comment, add regression test | ✓ |
| (b) Assume work needed | Execute a small diff plus guard test without baseline | |

**User's choice:** (a) — recommended option, baseline confirmed during context discussion.
**Notes:** Production code already passes `from_status=None`; only the historical comment at line 326 references the literal. Phase 19's deliverable is the comment cleanup + a regression test asserting the `Optional[str]` contract. Captured as D-05..D-07. Mirrors Phase 18 D-05 baseline-first pattern.

---

## POLISH-03 — atomicity sub-test rewrite scope

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Minimal | Keep test shape, fix broken assertion, drop placeholder, RED via documented experiment | ✓ |
| (b) Full restructure | Replace with two-session pattern using `seeded_project` + cross-session asserts | |
| (c) Defer further | Split atomicity into its own follow-up if scope balloons | |

**User's choice:** (a) — recommended option.
**Notes:** Phase 19 is debt closure, not test architecture. Single-session rollback observation is the right contract to test. RED experiment is documented-only in SUMMARY.md (D-09); the v1.4.1 history doesn't get cluttered with intentional-failure commits. Captured as D-08..D-10.

---

## POLISH-04 — strip layer, token set, RED test pattern

### Strip layer

| Option | Description | Selected |
|--------|-------------|----------|
| `chat_handler` (broad guard) | Strip in `forge_bridge/console/handlers.py` before response emission | |
| `OllamaToolAdapter` (close to source) | Strip in `_adapters.py::OllamaToolAdapter.send_turn()` | ✓ |

**User's choice:** OllamaToolAdapter — recommended option.
**Notes:** Provenance-specific to qwen2.5-coder via Ollama; chat handler is provider-neutral and shouldn't mask other providers' bugs. Captured as D-11.

### Token set

| Option | Description | Selected |
|--------|-------------|----------|
| Just `<\|im_start\|>` and `<\|im_end\|>` | Observed only | |
| Four-token set | Add `<\|endoftext\|>` and `<\|im_sep\|>` defensively | ✓ |

**User's choice:** Four-token set — recommended option.
**Notes:** Extends existing `INJECTION_MARKERS` tuple in `_sanitize_patterns.py:19` (currently lists only `<\|im_start\|>` from the chat-template family). Captured as D-12.

### RED test pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Captured fixture | Use Phase 16.2 captured-fixture if it preserves the noise-tail variant | ✓ |
| Synthetic fixture | Construct test text manually | (fallback) |

**User's choice:** Captured fixture preferred, synthetic as fallback — recommended.
**Notes:** Researcher MUST grep `.planning/phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json` first. Captured as D-14.

---

## Wave structure

| Option | Description | Selected |
|--------|-------------|----------|
| All-Wave-1 (4 parallel plans) | Maximum parallelism | |
| Wave 1 (P-01, P-02, P-03) + Wave 2 (P-04) | Avoids `_adapters.py` intra-wave overlap | ✓ |
| Sequential single wave | All four sequential | |

**User's choice:** Wave 1 (P-01, P-02, P-03) + Wave 2 (P-04).
**Notes:** P-01 and P-04 both modify `forge_bridge/llm/_adapters.py` — intra-wave overlap detection (Phase 18 executor protocol) requires sequencing. P-04 builds on P-01's salvage-path fix. Captured as D-16..D-17. Planner can override if a different sequencing reveals itself, with justification in PLAN.md.

---

## Claude's Discretion

- Specific test file locations for new POLISH-01 unit test (`tests/llm/test_adapters_salvage_ref.py` vs adding to existing `tests/llm/test_adapters.py`).
- Whether RED experiment for POLISH-03 lands as a real commit (D-09 says documented-only; planner can override with justification).
- Whether to consolidate POLISH-01 + POLISH-04 OllamaToolAdapter changes into a single refactor — atomicity (D-01) requires per-requirement commits, so any refactor still nets to two commits.

## Deferred Ideas

- Refactor `_try_parse_text_tool_call` to take an explicit `index` parameter (v1.5+).
- Cross-session atomicity tests beyond single-session contract (v1.5).
- Chat-template token stripping for non-Ollama adapters (deferred until evidence).
- Tail-strip-aware sanitization re-run for double-defense (deferred — adds latency for no observed risk).
- Consolidating `INJECTION_MARKERS` extension into a Phase 7 sanitization audit (v1.5).
