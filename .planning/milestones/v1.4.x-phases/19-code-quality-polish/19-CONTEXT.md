# Phase 19: Code-quality polish - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning
**Milestone:** v1.4.x Carry-Forward Debt
**Requirements:** POLISH-01, POLISH-02, POLISH-03, POLISH-04

<domain>
## Phase Boundary

Phase 19 closes the four code-quality debt items recorded in v1.4 close-out review artifacts. Each requirement is a surgical fix mapped to a specific file/line, with acceptance criteria already written into REQUIREMENTS.md. Three of four targets touch production source (`forge_bridge/llm/_adapters.py`, `forge_bridge/store/staged_operations.py`, `forge_bridge/console/handlers.py` or `forge_bridge/llm/_adapters.py`); one targets a test file (`tests/test_staged_operations.py`).

- **POLISH-01 (WR-02 closure):** `_try_parse_text_tool_call` in `forge_bridge/llm/_adapters.py:206` no longer hard-codes `ref=f"0:{name}"`. Replace with a derived ref computed at the call site so that even if the salvage guard ever loosens (multiple salvaged calls per turn), refs cannot collide with structured-path refs that use `f"{idx}:{name}"`.
- **POLISH-02 (Phase 13 WR-01 closure — verification-led):** Baseline already confirms the literal `"(missing)"` exists in `forge_bridge/store/staged_operations.py` ONLY as a historical comment (line 326). Production code already passes `from_status=None` (line 329) and the type signature is already `from_status: str | None` (line 74). Phase 19 closes this requirement by (a) deleting the now-misleading historical comment, (b) adding a regression unit test that asserts the `Optional[str]` contract is honored, and (c) verifying no other `"(missing)"` literal hides in the codebase.
- **POLISH-03 (Phase 13 WR-02 closure / Phase 18 D-07 deferral):** `tests/test_staged_operations.py::test_transition_atomicity` currently has an `assert True  # placeholder` (line 363) followed by an assertion block (line 388) whose claim contradicts SQLAlchemy/Postgres rollback semantics — Phase 18 baseline confirmed this is the failure mode. Replace the placeholder + broken assertion with a real RED→GREEN single-session rollback assertion that observes the rolled-back state correctly. Minimal scope: keep the existing test shape; fix only the assertion logic; produce a deliberate-break commit (RED) and the fix commit (GREEN).
- **POLISH-04 (qwen2.5-coder tail-token strip):** Phase 16.2 UAT recorded qwen2.5-coder occasionally appending `<|im_start|><|im_start|>{...}` chat-template noise on the assistant's terminal content. Strip terminal special tokens at the **OllamaToolAdapter** layer (close to source, no impact on Anthropic adapter or other models) using a small helper that consumes the existing `INJECTION_MARKERS` pattern set in `forge_bridge/_sanitize_patterns.py` (extend it with `<|im_end|>` and `<|endoftext|>`).

**Out of scope (deferred to v1.5 milestone work):** Refactoring `_try_parse_text_tool_call` itself; consolidating sanitize helpers across modules; broadening atomicity coverage to cross-session FK contracts; tail-strip for non-Ollama adapters until evidence emerges.

</domain>

<decisions>
## Implementation Decisions

### Commit structure (mirrors Phase 17 D-30 / Phase 18 D-01 isolated-commit precedent)

- **D-01:** Four plans, four commits, one per POLISH requirement. Mirrors Phase 17/18 precedent. Grouped variants (LLM-related: 01+04; store/test: 02+03) and single-bulk-commit variants were rejected — atomic per-requirement commits give the cleanest milestone-audit traceability.
  - **P-01: POLISH-01** — ref derivation fix in `_try_parse_text_tool_call` salvage path. One commit (production change + unit test).
  - **P-02: POLISH-02** — verify-and-document closure: comment cleanup in `staged_operations.py:326` + new regression unit test asserting `from_status: Optional[str]` contract. One commit.
  - **P-03: POLISH-03** — atomicity sub-test rewrite: drop placeholder + replace broken assertion with correct single-session rollback observation. One commit (test-only). RED→GREEN evidence captured in plan SUMMARY.md but landed atomically.
  - **P-04: POLISH-04** — tail-token strip helper in `OllamaToolAdapter` + extend `INJECTION_MARKERS` set. One commit (production change + unit test, ideally captured-fixture-grounded).

### POLISH-01 — ref derivation strategy

- **D-02:** Compute the salvaged ref at the **call site** after `tool_calls.append(salvaged)`:
  ```python
  if not tool_calls and text:
      salvaged = _try_parse_text_tool_call(text)
      if salvaged is not None:
          # Derive ref from current position in tool_calls — collision-free even if
          # the salvage guard ever loosens. Was hardcoded "0:{name}" (WR-02).
          salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.name}")
          tool_calls.append(salvaged)
          text = ""
  ```
  Rationale: minimal blast radius; helper signature stays context-free; the index is derived (no magic literal). Rejected alternatives: (b) passing `idx` into helper (signature churn for a one-line need), (c) `assert len(tool_calls) == 0` (preserves the literal — defeats WR-02's spirit).
- **D-03:** Inside `_try_parse_text_tool_call` itself, change the literal `ref=f"0:{name}"` at line 206 to a benign placeholder (e.g., `ref=""` or `ref=f"salvage:{name}"`) that the call site overwrites. The string literal `"0:"` MUST NOT appear in the helper or its call site after this plan lands (POLISH-01 acceptance).
- **D-04:** Add a unit test in `tests/llm/` that constructs an `OllamaToolAdapter`, invokes the salvage path with a captured-fixture-style text payload, and asserts the resulting `tool_calls[0].ref == "0:{name}"` (current empirical behavior — preserved across the fix). The test exists to catch regressions if the salvage guard later loosens.

### POLISH-02 — verification-led closure (baseline-first per Phase 18 D-05)

- **D-05:** Baseline established 2026-04-29 during context discussion: `grep -rn '"(missing)"' forge_bridge/ tests/` returns ONLY one match — the historical comment at `forge_bridge/store/staged_operations.py:326`. No production code passes the literal, no test asserts against it. The actual WR-01 fix landed sometime between Phase 13 and v1.4 close.
- **D-06:** P-02 scope is therefore (a) delete or rewrite the misleading comment at line 326 to read as past-tense closure ("WR-01 was closed by passing `from_status=None`; sentinel string `\"(missing)\"` is no longer used"), (b) add a regression unit test in `tests/test_staged_operations.py` (or `tests/store/`) asserting `StagedOpLifecycleError` carries `from_status: str | None` — never the string `"(missing)"`, and (c) re-run the grep at plan execution time to confirm zero literals in the codebase before commit. If executor's grep finds literals (somehow regressed since context-time), surface immediately as a deviation.
- **D-07:** P-02 is the smallest plan in this phase by file footprint. Do NOT bundle it with another plan to "balance" plan sizes — atomic per-requirement commits matter more than plan size symmetry (D-01).

### POLISH-03 — atomicity sub-test rewrite (minimal)

- **D-08:** Keep the existing `test_transition_atomicity` test shape (single test function, single-session block). Drop the `assert True  # placeholder` at line 363 and the trailing block whose assertion `assert row is None` contradicts SQLAlchemy/Postgres rollback semantics. Replace with a corrected single-session observation:
  ```python
  async with session_factory() as session:
      repo = StagedOpRepo(session)
      op = await repo.propose(operation="op-atom", proposer="p", parameters={})
      await session.commit()  # baseline: 1 entity + 1 staged.proposed event committed

      # Approve in same session, flush (push to DB), then rollback
      await repo.approve(op.id, approver="artist")
      await session.flush()
      events_mid = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
      assert len(events_mid) == 2  # both visible pre-rollback

      await session.rollback()

      # Post-rollback: only the originally-committed state remains
      events_after = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
      assert len(events_after) == 1
      assert events_after[0].event_type == "staged.proposed"
      fetched = await repo.get(op.id)
      assert fetched is not None
      assert fetched.status == "proposed"
  ```
  This actually exercises the atomicity contract: the pre-rollback `commit()` survives (entity + 1 event), the in-session approve+flush is rolled back (2nd event vanishes, status reverts).
- **D-09:** RED→GREEN evidence: P-03 is committed atomically (one commit), but the plan's SUMMARY.md MUST record the RED experiment — temporarily delete the `await session.rollback()` line, confirm the test fails with "still has staged.approved event", restore the line, confirm GREEN. The RED commit is NOT landed; the evidence is documented in SUMMARY.md only. (Rationale: P-03 is closing test debt, not introducing a new TDD discipline. The Phase 19 deliverable is the corrected test, not a RED guard commit.)
- **D-10:** Out of scope for P-03: cross-session atomicity assertions, FK-rollback assertions, multi-test refactor of `tests/test_staged_operations.py`. Scope creep would balloon a 1-test rewrite into a test-architecture phase. If POLISH-03 surfaces deeper atomicity bugs during execution, capture in SUMMARY.md and propose a v1.5 follow-up.

### POLISH-04 — qwen2.5-coder tail-token strip

- **D-11:** Strip layer is `OllamaToolAdapter.send_turn()` in `forge_bridge/llm/_adapters.py`, NOT `chat_handler` in `forge_bridge/console/handlers.py`. Rationale: the noise is provenance-specific to qwen2.5-coder via Ollama; the chat handler is a narrow waist for ALL adapters and stripping there would mask issues in other models that should surface as bugs. Adapter-layer stripping keeps Anthropic and future providers untouched.
- **D-12:** Token set: extend the existing `INJECTION_MARKERS` tuple in `forge_bridge/_sanitize_patterns.py:19` to include `<|im_end|>` and `<|endoftext|>` (currently absent — only `<|im_start|>` and the bare `<|`/`|>` fragments are listed). Optional: add `<|im_sep|>` defensively. The extension lands in P-04 with the tail-strip helper.
- **D-13:** Tail-strip helper signature: `_strip_terminal_chat_template_tokens(text: str) -> str`. Applies a regex anchored to the **end of string** that consumes a contiguous run of any chat-template token, optionally interleaved with whitespace. Does NOT strip mid-content occurrences — those are sanitization concerns handled by `_sanitize_tag()` and `_sanitize_tool_result()` (D-09 of FB-C). Helper lives in `forge_bridge/llm/_adapters.py` (private, tied to OllamaToolAdapter) — NOT in `_sanitize_patterns.py` (which is for shared patterns, not consumer-specific helpers per its docstring).
- **D-14:** RED test pattern: prefer a captured-fixture test if a Phase 16.2 UAT log preserved the noise-tail variant. Search `.planning/phases/16.2-bug-d-chat-tool-call-loop/` and `assist-01` log artifacts during research. Fallback to a synthetic fixture (`text = "answer prose <|im_start|><|im_start|>{...}"`) if no captured one exists. Either way: the test must FAIL on `text` returned through `send_turn()` without the strip, and PASS after. Acceptance per REQUIREMENTS.md: "no impact on legitimate prose responses" — add a second test that confirms a clean response (no chat-template tokens) passes through unchanged.
- **D-15:** Apply the strip after the salvage path runs (so any tool-call salvaged from text-shaped JSON sees the full original text), but before `text` is returned in `_TurnResponse`. Order:
  1. Parse structured `tool_calls` from `response.message.tool_calls`
  2. Salvage from `text` if `tool_calls` is empty (POLISH-01 fixed-ref path)
  3. **NEW**: `text = _strip_terminal_chat_template_tokens(text)`
  4. Return `_TurnResponse(text=text, tool_calls=tool_calls, ...)`

### Wave/dependency structure

- **D-16:** All four plans are independent — no inter-plan file overlap, no shared imports that would force ordering. Wave assignment can be **all-Wave-1** (parallel execution) since:
  - P-01 touches `forge_bridge/llm/_adapters.py` (salvage path)
  - P-02 touches `forge_bridge/store/staged_operations.py` (comment) + new test file
  - P-03 touches `tests/test_staged_operations.py` only
  - P-04 touches `forge_bridge/llm/_adapters.py` (NEW helper + send_turn modification) + `forge_bridge/_sanitize_patterns.py` (extend tuple)
- **D-17:** EXCEPTION: P-01 and P-04 BOTH modify `forge_bridge/llm/_adapters.py` — intra-wave files_modified overlap. Per Phase 18's executor protocol (intra-wave overlap detection), these MUST NOT run in parallel. Either (a) sequentialize P-01 → P-04 in a single wave (planner's choice), or (b) split into Wave 1 (P-01, P-02, P-03) and Wave 2 (P-04). Recommended: (b) — keeps Wave 1 cleanly parallelizable across 3 plans, lets P-04 build on P-01's salvage-path fix without merge contention.

### Claude's Discretion

- Whether to land the RED experiment for POLISH-03 (D-09) as a real commit or as documented-only in SUMMARY.md — D-09 picks documented-only; if planner has strong opinions on RED/GREEN commit discipline, they can override (justify in PLAN.md).
- Specific test file locations for new POLISH-01 unit test — `tests/llm/test_adapters_salvage_ref.py` vs adding to existing `tests/llm/test_adapters.py` (if it exists). Planner's call.
- Whether to consolidate the three OllamaToolAdapter changes from POLISH-01 (D-02/D-03) and POLISH-04 (D-11..D-15) into a single `_TurnResponse`-construction refactor or keep them as discrete edits. Atomicity (D-01) requires per-requirement commits, so any refactor must net to TWO commits (P-01 then P-04). Default: discrete, no refactor.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, executor) MUST read these before acting.**

### Requirements & roadmap
- `.planning/ROADMAP.md` lines 89–95 — Phase 19 entry; v1.4.x milestone goal; tag `v1.4.1` target.
- `.planning/REQUIREMENTS.md` POLISH-01..04 — full acceptance criteria for each requirement (file paths, line numbers, MUST conditions).

### Project context
- `.planning/PROJECT.md` — v1.4.x active milestone bullet; v1.4 close summary; codebase scale at v1.4 (40,038 LOC, 754 tests).
- `.planning/STATE.md` — current phase pointer post-Phase-18 completion.

### Prior CONTEXT.md (precedents to mirror)
- `.planning/phases/17-default-model-bumps/17-CONTEXT.md` — D-30 isolated-commit precedent for v1.4.x debt-closure phases.
- `.planning/phases/18-staged-handlers-test-harness-rework/18-CONTEXT.md` — D-01 (3 plans, 3 commits), D-05 (baseline-first per Phase 18), D-07 (POLISH-03 deferral rationale).
- `.planning/phases/18-staged-handlers-test-harness-rework/18-VERIFICATION.md` — confirmed POLISH-03 target test failure mode.

### Prior REVIEW.md / SUMMARY.md (the WRs Phase 19 closes)
- `.planning/phases/16.2-bug-d-chat-tool-call-loop/16.2-REVIEW.md` (or wherever Phase 16.2 review landed) WR-02 — the original POLISH-01 finding.
- `.planning/phases/13-staged-ops-entity/13-REVIEW.md` (or equivalent) WR-01 — the original POLISH-02 finding.
- `.planning/phases/13-staged-ops-entity/13-REVIEW.md` WR-02 — the original POLISH-03 finding.
- `.planning/phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json` — Phase 16.2 captured fixture; check whether it includes the noise-tail variant for POLISH-04 RED test.

### Source files (POLISH targets)
- `forge_bridge/llm/_adapters.py:122-208` — `_try_parse_text_tool_call` salvage helper (POLISH-01 D-02..D-04).
- `forge_bridge/llm/_adapters.py:535-560` — salvage call site in `OllamaToolAdapter.send_turn()` (POLISH-01 D-02 + POLISH-04 D-15).
- `forge_bridge/store/staged_operations.py:74-82,290-340` — `StagedOpLifecycleError` constructor + raise sites (POLISH-02 D-05..D-07).
- `tests/test_staged_operations.py:340-400` — `test_transition_atomicity` (POLISH-03 D-08..D-10).
- `forge_bridge/_sanitize_patterns.py:19-28` — `INJECTION_MARKERS` tuple (POLISH-04 D-12).

### Memory references
- `v1.4.x test-harness debt` memory — context for POLISH-03's deferral lineage from Phase 18.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`forge_bridge/_sanitize_patterns.py::INJECTION_MARKERS`** — already centralizes `<|im_start|>`, `<|`, `|>`, `[INST]`, etc. POLISH-04 extends this tuple rather than inventing a new pattern set. The module's docstring documents the "patterns hoisted, helpers per-consumer" pattern (FB-C D-09) — POLISH-04's tail-strip helper follows this convention by living next to its consumer (`OllamaToolAdapter`) rather than in `_sanitize_patterns.py`.
- **`tests/test_sanitize.py:61` + `tests/llm/test_sanitize_tool_result.py:85-91`** — established test patterns for asserting chat-template tokens are recognized by `_sanitize_tag` / `_sanitize_tool_result`. POLISH-04's RED test mirrors this style.
- **`replace()` from `dataclasses`** — already imported elsewhere in `_adapters.py`; use for D-02's `salvaged = replace(salvaged, ref=...)` (avoids mutating frozen `_ToolCall` dataclasses).

### Established patterns
- **D-30 isolated-commit pattern** (Phase 17) → **Phase 18 D-01 three-plan three-commit pattern** → Phase 19 follows with four-plan four-commit. Each commit is named `feat({phase}-{plan}): close POLISH-0X — {one-line summary}` or `fix(...)` depending on whether it lands new behavior or corrects a bug.
- **Captured-fixture RED test pattern** (Phase 16.2) — preferred over synthetic fixtures when an upstream artifact preserves the failure-mode evidence. POLISH-04 D-14 follows this.
- **Baseline-first approach** (Phase 18 D-05) — measure the assumed-broken state before writing the fix. POLISH-02 D-05 is the canonical example (baseline measurement landed during this CONTEXT discussion).

### Integration points
- **`OllamaToolAdapter.send_turn()`** at `forge_bridge/llm/_adapters.py` is the join point for POLISH-01 (salvage ref) AND POLISH-04 (tail-strip). Per D-17, these run in separate waves to avoid intra-wave file-overlap conflict.
- **`StagedOpRepo` / `EventRepo`** in `forge_bridge/store/staged_operations.py` — the surface area POLISH-03's atomicity test exercises. No new methods needed; existing `propose`/`approve`/`get`/`get_recent` cover the test scenario.
- **`_phase13_postgres_available()` probe** in `tests/conftest.py` — POLISH-03's test execution depends on this gating function (now Phase 18-cleaned: no `FORGE_TEST_DB=1` opt-in). Test is skipped silently if Postgres is unreachable, which preserves CI compatibility.

</code_context>

<specifics>
## Specific Ideas

- **Captured-fixture preference for POLISH-04 RED test:** The Phase 16.2 captured fixture (`16.2-CAPTURED-OLLAMA-RESPONSE.json`) MAY contain the noise-tail variant. Researcher MUST grep that fixture file before falling back to synthetic. If the variant isn't there, check `~/.claude` logs from Phase 16.2 UAT timestamps (assist-01).
- **Comment-rewrite tone for POLISH-02:** The existing comment at `staged_operations.py:326` reads as if the bug is current ("Sentinel string '(missing)' was the WR-01 bug; the [...]"). Rewrite to past-tense closure: "WR-01 (Phase 13 review) was closed by passing `from_status=None` here; the original sentinel string `\"(missing)\"` is no longer used in the codebase. POLISH-02 (Phase 19) confirmed this with a regression test."
- **Tail-strip token order matters:** Strip in greedy mode — if the model emits `<|im_start|><|im_start|>{...}<|im_end|>`, the regex needs to consume the WHOLE terminal run, not just the last token. Anchor with `\Z` (end of string), allow optional whitespace and any chat-template token from the union, repeat.
- **POLISH-03 RED experiment must be local-only:** D-09 explicitly says don't land the RED commit. The plan SUMMARY.md captures the experiment as text (e.g., "Removed `await session.rollback()` line; confirmed `assert len(events_after) == 1` failed with `assert 2 == 1`. Restored line; test passes."). This avoids cluttering the v1.4.1 history with intentional-failure commits while preserving the evidence trail.

</specifics>

<deferred>
## Deferred Ideas

- **Refactor `_try_parse_text_tool_call`** to take an explicit `index` parameter (cleaner API but a bigger change). Deferred to v1.5+ when the salvage path may need to support multiple tool-call extractions per turn.
- **Cross-session atomicity tests** beyond the single-session contract POLISH-03 covers (e.g., FK-cascade rollback observability across two `session_factory()` instances on the same DB instance). Deferred to v1.5 — would balloon Phase 19 scope.
- **Chat-template token stripping for the Anthropic adapter or any future provider.** Deferred until evidence emerges that another provider exhibits the noise-tail behavior. Adapter-layer scoping (D-11) is intentional — central stripping would mask provider-specific bugs.
- **Tail-strip-aware sanitization re-run** — passing the stripped text back through `_sanitize_tag()` for double-defense. Deferred — adds latency for no observed risk.
- **Consolidating `INJECTION_MARKERS` extension into a Phase 7 sanitization audit.** Deferred to v1.5 alongside the broader sanitize-helper consolidation that FB-C D-09 already explicitly rejected for v1.4.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 19-code-quality-polish*
*Context gathered: 2026-04-29*
*v1.4.x milestone: closes 4/4 remaining requirements before tag `v1.4.1`*
