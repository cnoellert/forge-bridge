# Phase 16 (FB-D) — PLAN-CHECK Report

**Reviewed:** 2026-04-27 (Mon Apr 27 10:11 PDT)
**Reviewer:** gsd-plan-checker (Opus 4.7, 1M ctx)
**Plans checked:** 16-01 → 16-07 (7 plans, 4 waves)
**Verdict:** **REVISE** — 2 BLOCKERS (one operator-flagged, one new), 5 WARNINGS, 0 PASSes that need celebration

The plan set is structurally strong — all CHAT-01..05 are covered, exception-translation matrix matches D-14a, envelope shape is correct, sanitization wiring is right. But there are two concrete frontmatter-level issues that will trip execution: the Wave 2 file overlap on app.py, and incorrect test-file paths in plan 16-01 that reference files that don't exist.

---

## Operator's 7 Concerns — Per-Item Verdicts

### Concern 1 — Wave 2 file overlap on `forge_bridge/console/app.py` — **REVISE (BLOCKER)**

**Confirmed:** both 16-04 and 16-05 declare `forge_bridge/console/app.py` in their `files_modified` lists. They are both in Wave 2 with no dependency edge between them.

- 16-04 line 11: `files_modified: [..., forge_bridge/console/app.py, ...]`. Adds `chat_handler` import + `Route("/api/v1/chat", chat_handler, methods=["POST"])` after line 98.
- 16-05 line 11: `files_modified: [..., forge_bridge/console/app.py]`. Renames import `ui_chat_stub_handler → ui_chat_handler` (line 33) and updates `Route("/ui/chat", ...)` at line 86.

The two edits touch DIFFERENT lines of app.py and would merge cleanly in human-hands, but the orchestrator's intra-wave `files_modified` overlap check is line-blind — it serializes any plan pair that names the same file. Without an explicit dependency, the orchestrator either (a) refuses to schedule them in parallel (silent serialization) or (b) lets the executor race-rebase, which is the riskier path.

**Cleaner fix — add explicit dependency to 16-05.** 16-05 is the lighter-weight edit (rename + route swap), and it already touches the panel template + JS that 16-04 doesn't care about. Adding `16-04` to 16-05's `depends_on` makes the dependency graph reflect reality:

```yaml
# .planning/phases/16-fb-d-chat-endpoint/16-05-PLAN.md, line 6-7
# CURRENT:
depends_on:
  - 16-03
# REVISED:
depends_on:
  - 16-03
  - 16-04
```

This pushes 16-05 into Wave 3 (along with 16-06), but 16-06 already depends on 16-05, so 16-06 becomes Wave 4 and 16-07 becomes Wave 5. Total wave count grows 4 → 5 but parallelism inside each wave stays correct. The schedule is:

- Wave 1: 16-01, 16-02, 16-03 (parallel)
- Wave 2: 16-04 (alone — ships handler + app.py route registration)
- Wave 3: 16-05 (alone — ships UI panel + app.py rename) + 16-06 (parallel — integration tests; ALSO depends on 16-05, see Concern 1b below)
- Wave 4: 16-07 (alone)

**Concern 1b — 16-06 also depends on 16-05.** 16-06 declares `depends_on: [16-04, 16-05]` and is currently Wave 3. With 16-05 pushed to Wave 3, 16-06 cannot be in the same wave; it must become Wave 4. Then 16-07 (which declares `depends_on: [16-04, 16-05, 16-06]`) becomes Wave 5.

**Concrete frontmatter edits required:**

```yaml
# 16-05-PLAN.md line 7
depends_on:
  - 16-03
  - 16-04        # NEW — serialize after 16-04 due to shared app.py edit
# (no wave field exists in current frontmatter; orchestrator computes from depends_on)

# 16-06-PLAN.md — wave will recompute from max(deps)+1 → Wave 4 (was 3)
# No frontmatter edit needed; just note in execute-phase orchestration

# 16-07-PLAN.md — wave will recompute → Wave 5 (was 4)
# No frontmatter edit needed
```

**Alternative — accept executor-side rebase (loose).** The orchestrator could merge both edits to app.py since they touch disjoint lines. But this requires the orchestrator's overlap detector to do AST-level diffing, which it doesn't. The clean dependency edit is strictly safer and the only cost is one extra wave.

**Recommendation:** Add `16-04` to 16-05's `depends_on`. This is the cleanest fix.

---

### Concern 2 — 16-01 backwards-compat risk — **PASS (with one warning)**

The new signature `complete_with_tools(self, prompt: str = "", tools: list = None, ...)` was checked against every existing call site:

- `tests/llm/test_complete_with_tools.py` — uses positional `complete_with_tools("hi", tools=[...])` form 17 times. The first positional arg is `prompt`, which still binds the same way. Backwards-compatible.
- `tests/integration/test_complete_with_tools_live.py:133, 179` — uses kwarg `prompt=...` form. Backwards-compatible.
- `tests/test_llm.py:234` — only references the function in a comment, no call. N/A.
- 16-04's chat_handler — uses kwarg `messages=...` form (the new path), no positional `prompt`. Compatible.

The mutual-exclusion guard in 16-01 fires only when BOTH `prompt` AND `messages` are passed (or when neither is passed). Existing positional callers pass only `prompt`, so they hit the `prompt and messages is not None` branch with `messages=None` → does NOT raise. Correct.

**One warning — `tools: list = None` typing regression.** Plan 16-01 line 132 says: "`tools: list = None` becomes `tools: Optional[list] = None` for typing consistency, but keep the existing `if not tools: raise ValueError(...)` guard at line 343". This phrasing is contradictory:
- The CURRENT signature (router.py:255) is `tools: list` (no default — required).
- The NEW signature in plan 16-01 line 124-138 has `tools: list = None` (default None — optional).

Making `tools` optional with `None` default is a typing/semantic regression: callers who omit `tools` now get a `TypeError` from the existing `if not tools` check (since `None` is falsy), but the type annotation `list = None` is wrong (None is not a list). The guard at router.py:343 (`if not tools: raise ValueError`) still fires correctly because `None` is falsy, but the annotation lies.

**Recommended fix — keep `tools` required:**
```python
async def complete_with_tools(
    self,
    prompt: str = "",
    tools: list = ...,             # REQUIRED — no default, current behavior preserved
    ...
    messages: Optional[list[dict]] = None,
) -> str:
```

Or, since the chat_handler always passes `tools=tools` (kwarg) and existing tests always pass `tools=[...]` (kwarg), making `tools` keyword-only is the cleanest:

```python
async def complete_with_tools(
    self,
    prompt: str = "",
    *,
    tools: list,                   # REQUIRED, keyword-only
    sensitive: bool = True,
    ...
    messages: Optional[list[dict]] = None,
) -> str:
```

**Edit needed in 16-01-PLAN.md Task 1 Change 1** (line 124-138): drop the `tools: list = None` change; keep `tools: list` (required, positional or kwarg) OR make it keyword-only with `*` separator.

---

### Concern 3 — 16-04 envelope-shape divergence test placement — **PASS**

I read `tests/console/test_staged_zero_divergence.py` end-to-end. It is NOT a "broad envelope shape sweep across all routes." It locks **MCP-tool-vs-HTTP byte-identity for the staged_operation surface only** (D-19 / STAGED-05/06/07). The fixtures wire up a `_ResourceSpy` for the MCP side and a `staged_client` for the HTTP side, then assert `json.loads(tool_body) == json.loads(http_body)` for matched calls.

`/api/v1/chat` has no MCP-tool counterpart (chat is HTTP-only — D-19's contract is staged_ops-specific), so extending `test_staged_zero_divergence.py`'s sweep to include chat would require fabricating a fake MCP-tool side just to compare to itself. That's worse than what 16-04 ships.

**16-04's `test_chat_envelope_shape_is_nested` is correctly placed** as a direct structural assertion on the chat handler output: it asserts `body["error"]` is a dict with `code`/`message` keys, and that no flat `code`/`message` siblings exist on the response body. This pins D-17 NESTED shape directly without coupling to FB-B's MCP-vs-HTTP test.

No revision needed.

---

### Concern 4 — Hand-rolled validation vs Pydantic — **PASS (researcher's recommendation flagged for awareness)**

Both approaches are defensible. The plan goes hand-rolled (~50 LOC of body validation in 16-04 Task 1). The researcher's RESEARCH.md §3 Pattern 1 recommends Pydantic 2 `BaseModel.model_validate()` (~20 LOC + reusable `_ChatRequestBody` model).

I checked the existing FB-B handlers — they ARE hand-rolled (`_resolve_actor` at lines 118-142 parses `X-Forge-Actor` manually; `staged_list_handler` at 145-176 parses query params manually). FB-B convention IS hand-rolled. Pydantic 2 is in the dep tree (`mcp[cli]>=1.19` pulls it transitively, verified RESEARCH.md §3).

**Trade-off snapshot:**

| Aspect | Hand-rolled (current plan) | Pydantic 2 |
|---|---|---|
| LOC | ~50 inline | ~20 model + ~5 caller |
| Convention match | Matches FB-B's `_resolve_actor` style | New convention for HTTP body validation |
| Error message quality | Manual messages per branch | Auto-generated from field name + constraint |
| Future refactor cost | Each handler duplicates validation | Reusable across 16-04 + future endpoints |
| Type safety | Dict-typed `body.get(...)` | Typed `body.messages` access |

**Researcher's recommendation is technically cleaner** for an endpoint with 4+ constrained fields (messages, max_iterations, max_seconds, tool_result_max_bytes). FB-B's hand-rolled pattern was acceptable for `actor: str` (one field). Chat has 4-5 fields with type/range constraints; Pydantic is a better fit.

**However:** the plan's choice is defensible — consistency with FB-B beats minor LOC savings, and a future refactor to Pydantic across all handlers is one PR. Either is shippable.

**Recommendation for user awareness — go with Pydantic.** The plan is technically correct as written, but I'd flag this for the user: 4+ constrained fields is the threshold where hand-rolled validation becomes painful. The cost to switch is low (the plan already lists the `_ChatRequestBody` model in RESEARCH.md §3), and the typed `body.messages` access removes a class of `body.get("messages")` typo bugs that hand-rolled validation cannot catch.

If user prefers FB-B convention, ship as-is. No frontmatter change required either way.

---

### Concern 5 — 16-05 escape-first markdown renderer has no JS unit test — **PASS (matches Phase 10 convention)**

I verified by checking the project's testing precedent. The closest analog is Phase 10's `query_console.html:40-117` — an Alpine factory function inline in a `<script>` tag. There is **no JS unit test** for that factory. The tests that exercise it are:

- `tests/test_query_console.py` (or equivalent) — tests the SERVER-side query route, not the JS factory.
- The factory's behavior is exercised indirectly via the integration tests that drive the full ASGI app + browser.

This is the project's established convention: vanilla Alpine factories are exercised E2E, not unit-tested in isolation. There's no JS test runner (`vitest`, `jest`, `karma`) configured in the repo. Adding one for a 50-line escape-first renderer would be premature.

**16-05's approach is correct:**
- The renderer's security ordering (escape → fenced → inline → bold → http(s)-link → newline) is documented in the plan's task 2 action with an inline review checklist.
- The Wave 3 integration test (16-06's `TestChatParityStructural`) exercises the full request/response cycle, which indirectly invokes the renderer when assistant messages echo through the loop.
- The human-verify checkpoint (16-05 Task 4 step 8) explicitly tests `<script>alert('xss')</script>` rendering in the live UI — manual smoke test of the security boundary.

This matches the Phase 10 testing pattern. No revision needed.

---

### Concern 6 — CHAT-04 (artist UAT) handoff — **PASS (with one warning)**

I verified that none of the 7 plans implement CHAT-04 directly. UAT is run by an actual artist on assist-01 per D-12. The handoff exists in three places:

1. **16-05's Task 4 (`checkpoint:human-verify`)** — Claude pauses, user runs the 8 manual verification steps. This is a sanity check before integration tests run, NOT the artist UAT itself.
2. **16-05's `<success_criteria>`** says "the artist UAT itself runs separately under D-12, after Wave 3 ships" — explicit handoff.
3. **16-07's `<success_criteria>`** at line 597-602 explicitly says: "Phase 16 is structurally complete — the only outstanding work item is the CHAT-04 D-12 D-36 fresh-operator artist UAT, which runs separately as an operator activity (not a coded test)." 16-07's `<output>` template at lines 612-614 instructs the executor's SUMMARY.md to include the UAT-pending callout.

This matches Phase 10 → 10.1 pattern (Phase 10 closed with D-36 gate flagged as PENDING; Phase 10.1 was the remediation phase triggered by UAT findings).

**One warning — checkpoint placement timing.** 16-05 Task 4's human-verify checkpoint runs BEFORE Wave 3 integration tests (16-06) ship. Step 3 of the verification ("Type 'ping' and press Enter") expects either a real LLM response or a 504 timeout banner. With NO real LLM running and NO mocked LLM in the UI server (16-05 doesn't ship a mock), the user would hit the 504 path on every send. That's correct behavior but the verification step's "Expected: assistant reply appears" is misleading — the user will only see the assistant reply if they have Ollama running locally.

**Recommended edit to 16-05 line 626** (Task 4 Step 3):

```
3. Type a question (e.g. "ping") and press Enter.
   - Expected: user message bubble appears with `--color-text-muted` left border.
   - Expected: Send button shows `.spinner-amber` (amber spinning circle) for the duration of the request.
   - Expected (if Ollama IS running locally on this machine): assistant reply appears with `--color-accent` (amber) left border within ~30s.
   - Expected (if Ollama is NOT running locally): a 504 timeout banner with the prescribed D-09 copy after ~125s. This is the verification target — proves the panel's error-handling path works.
```

The current text says "If Ollama is not running locally on assist-01, expect a 504 timeout banner..." which assumes the user is on assist-01. The user verifying 16-05 likely IS the developer on a dev machine, not the artist on assist-01. Tighten the conditional language.

This is a minor copy fix, not a structural blocker.

---

### Concern 7 — `IGNORE PREVIOUS INSTRUCTIONS` and `INJECTION_MARKERS` references — **PASS**

I grepped all phase 16 docs and plans for these strings. Findings:

| Location | Type | OK? |
|---|---|---|
| `16-CONTEXT.md:163-164` | D-15 contract docstring | ✅ Documentation |
| `16-PATTERNS.md:543` | Test pattern docstring | ✅ Test docstring |
| `16-01-PLAN.md:359` | Threat-model accept clause | ✅ Documentation |
| `16-06-PLAN.md:96, 190, 201, 313, 347, 370-371` | Integration test fixture | ✅ Test source — `_POISON` constant in `tests/integration/test_chat_endpoint.py` |
| `16-07-PLAN.md` SEED files | None — no SEED file mentions these markers | ✅ |

**Verification: zero references in src/ execution paths.** All references are in test files (`tests/integration/test_chat_endpoint.py`) or documentation (`.planning/`). The `INJECTION_MARKERS` constant lives at `forge_bridge/_sanitize_patterns.py:19-28` (the source-of-truth tuple), which is correct — it IS the sanitization data, not an embedded instruction.

The `_POISON` constant at 16-06 line 201 is a test fixture string used to poison a tool result and assert the sanitizer strips it. The marker substring should appear ONLY in tests/ and .planning/ — never in `forge_bridge/console/handlers.py`, `forge_bridge/llm/router.py`, or any execution path. The plans honor this.

No revision needed.

---

## Standard Plan-Checker Sweep

### Acceptance Criteria Coverage (CHAT-01..05)

| REQ-ID | Plan(s) | Truth Vehicle | Verdict |
|---|---|---|---|
| CHAT-01 (rate limit, 11→429) | 16-02 (token bucket), 16-04 (handler integration + 1 test) | `test_chat_rate_limit_returns_429_with_retry_after` in 16-04 | ✅ Covered |
| CHAT-02 (125s wall-clock timeout) | 16-04 (asyncio.wait_for(timeout=125.0) + 2 tests) | `test_chat_outer_timeout_returns_504` + `test_chat_loop_budget_exceeded_returns_504` | ✅ Covered |
| CHAT-03 (sanitization E2E) | 16-06 (Strategy A always-on + Strategy B gated) | `test_chat_does_not_leak_poisoned_tool_marker` (Strategy B) + `test_handler_passes_messages_verbatim_to_router` + `test_injection_markers_present_in_pattern_set` (Strategy A) | ✅ Covered |
| CHAT-04 (artist UAT <60s) | NOT IMPLEMENTED — operator handoff in 16-05 + 16-07 | Manual artist UAT on assist-01 | ✅ Per D-12 (this is correct) |
| CHAT-05 (external-consumer parity) | 16-06 (`test_chat_parity_browser_vs_flame_hooks`) | Two-client parity test with `_structural_signature` helper | ✅ Covered |

All 5 requirements have either a covering test or an explicit operator-handoff. Coverage is complete.

### Dependency Graph

| Plan | depends_on | Wave (current) | Wave (after Concern 1 fix) |
|---|---|---|---|
| 16-01 | [] | 1 | 1 |
| 16-02 | [] | 1 | 1 |
| 16-03 | [] | 1 | 1 |
| 16-04 | [16-01, 16-02] | 2 | 2 |
| 16-05 | [16-03] | 2 | **3** (after adding 16-04) |
| 16-06 | [16-04, 16-05] | 3 | **4** (recompute) |
| 16-07 | [16-04, 16-05, 16-06] | 4 | **5** (recompute) |

No cycles. No forward references. The graph is correct in shape; only the wave assignment for 16-05 needs the dep edit per Concern 1.

### Line-Numbered Reference Accuracy (sampled)

| Plan claim | Actual at HEAD | Verdict |
|---|---|---|
| 16-01 cites `router.py:252-264` for current `complete_with_tools` signature | Verified — `complete_with_tools` def at line 252, params end at 264 | ✅ |
| 16-01 cites `router.py:382-384` for `adapter.init_state` call site | Verified — line 382-384 | ✅ |
| 16-04 cites `handlers.py:179-224` for `staged_approve_handler` analog | Verified — function spans 179-224 | ✅ |
| 16-04 cites `handlers.py:53-60` for `_envelope` + `_error` helpers | Verified — `_envelope` at 53-55, `_error` at 58-60 | ✅ |
| 16-04 cites `app.py:96-98` for FB-B route block | Verified — staged_list at 96, staged_approve at 97, staged_reject at 98 | ✅ |
| 16-05 cites `ui_handlers.py:467-476` for `ui_chat_stub_handler` | Verified — function spans 467-476 | ✅ |
| 16-05 cites `app.py:86` for `Route("/ui/chat", ui_chat_stub_handler...)` | Verified — exact match at line 86 | ✅ |
| 16-05 cites `shell.html:12` for nav link | Verified — line 12 has `<a href="/ui/chat">` | ✅ |
| 16-PATTERNS cites `forge-console.css:38-69` for card/chip patterns | Verified — `.card` at 38, range correct | ✅ |
| RESEARCH cites `mcp/registry.py:230-238` for `mcp.list_tools` | Verified — `available = await mcp.list_tools()` at line 232 | ✅ |

Line-number accuracy is excellent. The planner's mechanical work is solid.

### `must_haves` Block Soundness

Each plan's `must_haves` block was sampled for grep-pattern accuracy:

- 16-01 line 32-34 — `pattern: "adapter\\.init_state\\("` matches `forge_bridge/llm/router.py:382` ✅
- 16-02 line 36 — `pattern: "_buckets: dict\\["` matches the planned new file ✅
- 16-04 line 50 — `pattern: "complete_with_tools\\(messages="` matches the planned chat_handler call ✅
- 16-04 line 54 — `pattern: "await.*list_tools\\(\\)"` matches the planned snapshot call ✅
- 16-05 line 50-52 — `pattern: "fetch\\(['\"]/api/v1/chat['\"]"` matches the planned forge-chat.js fetch ✅

`must_haves` blocks are well-formed.

### `files_modified` Completeness Sweep

Cross-checked each plan's `files_modified` list against actual files referenced in tasks:

- **16-01** ✅ `forge_bridge/llm/router.py` + `tests/test_llm_router.py` — but Task 1 line 197 also mutates `forge_bridge/llm/_adapters.py` (init_state on both adapters). **`files_modified` is INCOMPLETE — missing `forge_bridge/llm/_adapters.py`.** This is a BLOCKER for orchestration: if a parallel plan in Wave 1 also touched `_adapters.py`, the overlap detector would miss it.

   **Concrete fix to 16-01-PLAN.md line 8:**
   ```yaml
   files_modified:
     - forge_bridge/llm/router.py
     - forge_bridge/llm/_adapters.py    # NEW — init_state extension on both adapters per Task 1 Change 4
     - tests/llm/test_complete_with_tools.py    # CORRECTION — actual location
   ```

   **ALSO BLOCKER:** the test file path `tests/test_llm_router.py` is wrong. There is no such file. The actual coordinator unit-test file is `tests/llm/test_complete_with_tools.py`. Plan 16-01's Task 2 (line 246-340) writes the new `TestCompleteWithToolsMessagesKwarg` class into `tests/test_llm_router.py`. The acceptance_criteria at line 333-340 grep this file. The file does NOT exist; either the planner conflated the file name or copy-pasted from a stale draft.

   The `_StubAdapter` is also imported as `from tests.helpers.stub_adapter import _StubAdapter` (Task 2 line 261), but the actual location is `tests/llm/conftest.py:30`. Tests in `tests/llm/test_complete_with_tools.py` access it via `from tests.llm.conftest import _StubAdapter` (line 44).

   **Fix needed in 16-01-PLAN.md:**
   - Line 8: change `tests/test_llm_router.py` → `tests/llm/test_complete_with_tools.py`
   - Add `forge_bridge/llm/_adapters.py` to `files_modified`
   - Task 2 line 261: change import to match actual location: `from tests.llm.conftest import _StubAdapter`
   - Task 2 line 322: drop the `tests/helpers/` reference; the `_StubAdapter` is in `tests/llm/conftest.py`
   - All grep acceptance criteria targeting `tests/test_llm_router.py` should retarget `tests/llm/test_complete_with_tools.py`

- **16-02** ✅ Both files declared, no missing references.
- **16-03** ✅ Single file declared (forge-console.css), no missing references.
- **16-04** ✅ All three files declared. handlers.py + app.py + new test file. No missing.
- **16-05** ✅ All five files declared. The plan also expects (Sub-step C) to update tests that reference `ui_chat_stub_handler`, but says "DO NOT delete tests in this plan; plan 16-07 handles the test cleanup." This is correct — `tests/test_ui_chat_stub.py` is NOT in 16-05's `files_modified` because 16-07 owns its retirement.
- **16-06** ✅ Both new test files declared.
- **16-07** ✅ 5 SEED files declared. The orphan-test cleanup is handled in Sub-step A of Task 2 — `tests/test_ui_chat_stub.py` will be deleted, but it's NOT in `files_modified`. **WARNING:** for orchestrator overlap-detection accuracy, list `tests/test_ui_chat_stub.py` in 16-07's `files_modified` even though it's a deletion. The orchestrator's check is on touched-paths, not write-paths.

**Recommended edit to 16-07-PLAN.md line 11-15:**
```yaml
files_modified:
  - .planning/seeds/SEED-CHAT-STREAMING-V1.4.x.md
  - .planning/seeds/SEED-CHAT-TOOL-ALLOWLIST-V1.5.md
  - .planning/seeds/SEED-CHAT-CLOUD-CALLER-V1.5.md
  - .planning/seeds/SEED-CHAT-PERSIST-HISTORY-V1.5+.md
  - .planning/seeds/SEED-CHAT-PARTIAL-OUTPUT-V1.5.md
  - tests/test_ui_chat_stub.py                          # NEW — deletion target per Task 2 Sub-step A
  - tests/console/test_chat_handler.py                  # NEW (optional) — guard test added per Sub-step B
```

If the optional guard test in Sub-step B is shipped, that adds `tests/console/test_chat_handler.py` to the modified set. If skipped, omit.

### Intra-Wave Parallelization Safety

Wave 1 (16-01, 16-02, 16-03 currently parallel):
- 16-01 touches: `forge_bridge/llm/router.py`, `forge_bridge/llm/_adapters.py` (uncatalogued — see above), test file (wrong path — see above)
- 16-02 touches: `forge_bridge/console/_rate_limit.py`, `tests/console/test_rate_limit.py`
- 16-03 touches: `forge_bridge/console/static/forge-console.css`

After 16-01's `files_modified` is corrected to include `_adapters.py`, the intersection is still empty across the three plans. **Wave 1 is parallel-safe.**

Wave 2 (16-04, 16-05 currently parallel) — see Concern 1.

Wave 3 (16-06 alone) — touches `tests/integration/test_chat_endpoint.py` + `tests/integration/test_chat_parity.py`. No overlap with anything.

Wave 4 (16-07 alone) — touches 5 SEED files + (after fix) `tests/test_ui_chat_stub.py` (delete). No overlap.

After Concern 1 fix, all waves are parallel-safe.

### Architectural Tier Compliance

I checked the Architectural Responsibility Map at RESEARCH.md lines 25-37 against the task placements:

| Capability | Map says | Plan places | Verdict |
|---|---|---|---|
| HTTP request parsing + validation | API/Backend | 16-04 chat_handler in handlers.py | ✅ |
| Rate limiting | API/Backend | 16-02 _rate_limit.py + 16-04 handler call | ✅ |
| LLM tool-call orchestration | LLMRouter (existing FB-C) | 16-04 calls FB-C surface | ✅ |
| Tool registry snapshot | MCP registry | 16-04 calls `mcp.list_tools()` | ✅ |
| Sanitization | LLM module + Learning module | Already wired by Phase 7 + FB-C | ✅ |
| Conversation history | Browser/Client | 16-05 forge-chat.js per-tab state | ✅ |
| Markdown rendering | Browser/Client | 16-05 escape-first JS | ✅ |
| Tool-call transparency UI | Browser/Client | 16-05 `<details>` block | ✅ |

No tier mismatches. Each capability is placed where the responsibility map assigns it.

### Context Compliance (D-01..D-21)

Sampled 12 of the 21 locked decisions for plan-implementation coverage:

| Decision | Implemented in | Verdict |
|---|---|---|
| D-01 (non-streaming JSON) | 16-04 + 16-07 SEED-CHAT-STREAMING | ✅ |
| D-02 (messages shape) | 16-04 chat handler validates exact shape | ✅ |
| D-02a (Pattern B FB-C extension) | 16-01 — entire plan | ✅ |
| D-04 (all tools snapshot) | 16-04 `await mcp.list_tools()` | ✅ |
| D-05 (sensitive=True hardcoded) | 16-04 + test asserts call_kwargs["sensitive"] is True | ✅ |
| D-06 (per-tab history) | 16-05 — no localStorage, no sessionStorage | ✅ |
| D-13 (token bucket) | 16-02 — capacity=10, refill=10/60s, TTL=300s, threading.Lock | ✅ exact |
| D-14 (asyncio.wait_for(125)) | 16-04 line 379 — `timeout=125.0` outer, `max_seconds=120.0` inner | ✅ |
| D-14a (translation matrix) | 16-04 — all 6 exception branches map exactly per matrix | ✅ |
| D-15 (sanitization wiring) | NO new wiring per plan; FB-C already does it | ✅ correct |
| D-16 (LLMRouter via ConsoleReadAPI) | 16-04 line 330 — `request.app.state.console_read_api._llm_router` | ✅ |
| D-17 (NESTED envelope) | 16-04 — every error response uses `{"error": {"code", "message"}}` | ✅ |
| D-21 (structured logging) | 16-04 — fields request_id, client_ip, message_count_in/out, tool_call_count, wall_clock_ms, stop_reason | ✅ |

All 12 sampled decisions are implemented. No contradictions found. No deferred ideas leaked into plans (the 5 SEED files in 16-07 cover all deferred items from CONTEXT lines 248-258).

### CLAUDE.md Compliance

I checked the 3 active CLAUDE.md directives against the plans:

1. **"Don't break the working flame hook + MCP server during restructuring"** — none of the 7 plans touch `flame_hooks/` or break the MCP server entry point. ✅
2. **"Vocabulary spec is written but not yet implemented in code"** — chat endpoint does not introduce new vocabulary terms. ✅
3. **Project memory: "Every UI-touching phase (FB-D) includes mandatory non-developer dogfood UAT"** — 16-05 explicitly hands off to artist UAT (D-12), and 16-07's success_criteria flags UAT as the remaining gate. ✅

No CLAUDE.md violations.

### Research Resolution (RESEARCH.md Open Questions)

RESEARCH.md line 271+ has `## Open Questions for Research / Planning` section. I checked: it does NOT have `(RESOLVED)` in the heading suffix, but the body explicitly states (line 274): "All four open questions raised by research+pattern-mapper review (2026-04-27) have been resolved into the decisions above." Then it lists 4 resolved questions with `~~strikethrough~~` markers and explicit "Resolved as..." text.

**WARNING:** the heading does not match the standard format `## Open Questions (RESOLVED)` that the plan-checker dimension 11 expects. The body content makes it clear the questions are resolved, but a strict check would FAIL this dimension.

**Recommended trivial edit to 16-RESEARCH.md line 271:**
```markdown
## Open Questions for Research / Planning (RESOLVED)
```

This is a one-character fix and unblocks the formal Dimension-11 check. The body already documents resolutions correctly.

### Pattern Compliance (PATTERNS.md analogs)

I cross-checked the 7 mapped analogs in PATTERNS.md `## File Classification` against each plan's references:

| New file | Analog | Plan that ships | Plan references analog? |
|---|---|---|---|
| `handlers.py` (chat_handler) | `staged_approve_handler:179-224` | 16-04 | ✅ Tasks 1 read_first |
| `_rate_limit.py` | none (greenfield) | 16-02 | ✅ marked as greenfield |
| `app.py` (route addition) | `app.py:96-98` (FB-B block) | 16-04 + 16-05 | ✅ both reference |
| `chat/panel.html` | `health/detail.html` | 16-05 | ✅ Task 1 read_first |
| `forge-chat.js` | `query_console.html:39-117` Alpine factory | 16-05 | ✅ Task 2 read_first |
| `forge-console.css` (chat rules) | `forge-console.css:38-69` | 16-03 | ✅ Task 1 read_first |
| `tests/console/test_chat_handler.py` | `test_staged_handlers_writes.py` | 16-04 | ✅ Task 3 read_first |
| `tests/integration/test_chat_endpoint.py` | `test_complete_with_tools_live.py` | 16-06 | ✅ Task 1 read_first |

All analog references are present in the plans' `read_first` blocks. Pattern compliance is excellent.

---

## Issues Summary

### Blockers (must fix before execution)

**1. [files_modified accuracy] 16-01 has wrong test-file path AND missing `_adapters.py`**
- Plan: 16-01
- Severity: blocker
- Description: `files_modified` lists `tests/test_llm_router.py` which does not exist. Actual coordinator-tests file is `tests/llm/test_complete_with_tools.py`. Also missing `forge_bridge/llm/_adapters.py` from `files_modified` even though Task 1 Change 4 (line 172-197) modifies init_state on both adapters.
- Fix:
  ```yaml
  # 16-01-PLAN.md line 8:
  files_modified:
    - forge_bridge/llm/router.py
    - forge_bridge/llm/_adapters.py            # NEW
    - tests/llm/test_complete_with_tools.py    # CORRECTED from tests/test_llm_router.py
  ```
- Also fix Task 2 imports (line 261, 322): change `from tests.helpers.stub_adapter import _StubAdapter` → `from tests.llm.conftest import _StubAdapter`
- Also fix all Task 2 acceptance_criteria grep targets at lines 333-339: change `tests/test_llm_router.py` → `tests/llm/test_complete_with_tools.py`

**2. [Wave overlap] 16-04 and 16-05 both modify app.py with no dep edge**
- Plans: 16-04, 16-05
- Severity: blocker
- Description: both plans appear in Wave 2 with `forge_bridge/console/app.py` in their `files_modified` lists. Orchestrator's intra-wave overlap detector will force serialization or executor race-rebase.
- Fix:
  ```yaml
  # 16-05-PLAN.md line 7:
  depends_on:
    - 16-03
    - 16-04        # NEW — explicit dep due to shared app.py edit
  ```
- Side effect: 16-05 → Wave 3, 16-06 → Wave 4, 16-07 → Wave 5 (orchestrator recomputes from depends_on; no other frontmatter changes needed).

### Warnings (should fix, execution may work)

**1. [Typing regression] 16-01 plan changes `tools: list` to `tools: list = None` — type annotation lies**
- Plan: 16-01
- Severity: warning
- Description: Task 1 Change 1 line 132 makes `tools` optional with `None` default, but the existing `if not tools: raise ValueError` guard at router.py:343 stays. The annotation `list = None` is a lie (None is not a list); existing tests bind `tools=[...]` by kwarg so they still work, but the typing is broken.
- Fix: keep `tools: list` (required, no default), or make it keyword-only with `*` separator. See concern 2 above.

**2. [Open Questions heading format] 16-RESEARCH.md line 271 lacks `(RESOLVED)` suffix**
- File: 16-RESEARCH.md
- Severity: warning
- Description: Body declares all 4 questions resolved, but heading is `## Open Questions for Research / Planning` — a strict Dimension-11 check expects `## Open Questions (RESOLVED)`.
- Fix: append `(RESOLVED)` to the heading. One-character fix.

**3. [files_modified completeness] 16-07 should list deletion target + optional guard test**
- Plan: 16-07
- Severity: warning
- Description: Task 2 Sub-step A deletes `tests/test_ui_chat_stub.py`. Sub-step B optionally adds a guard test to `tests/console/test_chat_handler.py`. Neither is in `files_modified`.
- Fix: add `tests/test_ui_chat_stub.py` (always — deletion is a touched-path) and `tests/console/test_chat_handler.py` (if shipping the optional guard). See concrete YAML in the Standard Sweep section above.

**4. [UAT step copy] 16-05 Task 4 step 3 expected-outcome copy assumes user is on assist-01**
- Plan: 16-05
- Severity: warning
- Description: Step 3 says "If Ollama is not running locally on assist-01, expect..." but the user verifying the human-verify checkpoint is most likely a developer on a dev machine, not the artist on assist-01. The conditional should be Ollama-availability-based, not host-based.
- Fix: rewrite step 3 expected-outcomes per the Concern 6 recommendation above.

**5. [dead CSS rule] forge-console.css `.chat-stub-card` rule (line 59-60) becomes dead code after 16-05 deletes stub.html**
- Plan: 16-07 (cleanup scope)
- Severity: warning (info, low impact)
- Description: After 16-05 deletes `chat/stub.html`, the `.chat-stub-card` CSS rule at forge-console.css:59-60 has no consumers. Not a correctness issue but a cleanliness one.
- Fix: 16-07 Task 2 could optionally also strip the `.chat-stub-card` rules from forge-console.css. If shipping, add `forge_bridge/console/static/forge-console.css` to 16-07's `files_modified`. Or leave as-is and bundle the cleanup into a future v1.4.x patch.

---

## Final Verdict

**Status:** REVISE

**Required fixes before execution:**
1. **16-05 frontmatter** — add `16-04` to `depends_on` (shared app.py edit).
2. **16-01 frontmatter** — correct `files_modified` test-file path AND add `forge_bridge/llm/_adapters.py`.
3. **16-01 Task 2** — fix `_StubAdapter` import path + all `tests/test_llm_router.py` references throughout the task.

**Recommended fixes (warnings, may be deferred to executor):**
4. **16-01 Task 1 Change 1** — keep `tools: list` (required) instead of `tools: list = None`.
5. **16-RESEARCH.md** — append `(RESOLVED)` to the Open Questions heading.
6. **16-07 frontmatter** — add `tests/test_ui_chat_stub.py` to `files_modified`.
7. **16-05 Task 4 step 3** — clarify expected-outcomes for dev-machine UAT.

**Pre-revision plan quality:** strong. The structural decisions (D-14a translation matrix, D-17 nested envelope, D-04 tool snapshot, D-13 token bucket parameters, D-02a Pattern B prerequisite ordering) are all correctly reflected in the task actions. Line numbers cited in PATTERNS.md are accurate at HEAD. The 7 plans collectively cover CHAT-01..05 with appropriate test depth (deterministic Strategy A + gated Strategy B for the live tests). The CHAT-04 operator-handoff pattern matches Phase 10 → 10.1 precedent.

**Post-revision:** the 3 blocker fixes are mechanical frontmatter edits totaling ~10 lines of YAML. Once corrected, the plan set is ready for `/gsd-execute-phase 16`.

---

*Authored 2026-04-27 by gsd-plan-checker. Re-run after planner applies frontmatter edits.*
