# Phase 19: Code-quality polish - Research

**Researched:** 2026-04-29
**Domain:** Surgical code-quality debt closure — Python adapter/test fixes
**Confidence:** HIGH (all targets verified against current source; no library-API uncertainty)

## Summary

Phase 19 closes four carry-forward debt items recorded in v1.4 close-out. Every fix is mapped to a specific file/line, and CONTEXT.md (D-01..D-17) has already locked the implementation approach. This research is verification-led: confirm exact line numbers, fixture availability, and supporting test infrastructure so the planner can write four mechanical plans without re-litigating design.

Verification headlines:

- **POLISH-01** target literal `ref=f"0:{name}"` exists at `forge_bridge/llm/_adapters.py:206` (inside `_try_parse_text_tool_call`, which spans lines 122-209). Salvage call site at lines **543-547** in `OllamaToolAdapter.send_turn()` (CONTEXT cited 535-560 — the tighter range is 543-547; Architectural Responsibility table records the verified range). [VERIFIED: source file]
- **POLISH-02** baseline holds: `grep '"(missing)"' forge_bridge/ tests/` returns exactly ONE match — the historical comment at `forge_bridge/store/staged_operations.py:326`. Production code at line 329 already passes `from_status=None`; type signature at line 74 is already `from_status: str | None`. The phase reduces to (a) comment rewrite and (b) regression test. [VERIFIED: grep + source file]
- **POLISH-03** confirms the failure mode: `tests/test_staged_operations.py::test_transition_atomicity` (lines 323-398) contains `assert True  # placeholder` at line **360** (CONTEXT said 363 — off by 3) and the contradiction-assertion at line **388** (`assert row is None, ...`). The test is structured as three sequential `async with session_factory()` blocks — CONTEXT D-08's rewrite collapses the third block into a single-session observation. All needed imports (`EventRepo`, `select`, `DBEntity`, `DBEvent`) are already present at the top of the file. [VERIFIED: source file]
- **POLISH-04** captured fixture at `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json` does NOT contain `<|im_start|>`/`<|im_end|>`/`<|endoftext|>` — fallback to synthetic fixture per CONTEXT D-14. However, the **HUMAN-UAT artifact** at `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md:106-107` contains the verbatim noise tail captured during fresh-operator UAT. The synthetic fixture should mirror this exact text. [VERIFIED: file search + content read]
- **POLISH-04** secondary verification: `INJECTION_MARKERS` in `forge_bridge/_sanitize_patterns.py:19-28` is a tuple of 8 entries today; `<|im_start|>` is present (line 25), `<|im_end|>` and `<|endoftext|>` are NOT. CONTEXT D-12's "extend with two markers" is correct. **However, `tests/test_sanitize.py:177` asserts `len(INJECTION_MARKERS) == 8`** — the plan MUST bump this assertion or the polish breaks an existing test. This is an additional touchpoint not flagged in CONTEXT. [VERIFIED: grep]

**Primary recommendation:** Plan four discrete commits (P-01..P-04) per CONTEXT D-01. Sequence P-01 → P-04 across two waves per CONTEXT D-17 (both edit `_adapters.py`); Wave 1 holds P-01/P-02/P-03 in parallel, Wave 2 holds P-04 alone. Surface the `test_sanitize.py:177` count-bump as an in-scope edit for P-04.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tool-call salvage from text-shaped JSON | LLM adapter (`OllamaToolAdapter`) | — | Provider-specific quirk; should not leak into coordinator (`router.py`) or chat handler. Confirmed by Phase 16.2's adapter-layer placement of `_try_parse_text_tool_call`. |
| Ref derivation for salvaged tool calls | LLM adapter call site (`send_turn`) | LLM adapter helper (`_try_parse_text_tool_call`) | Helper produces a context-free placeholder; call site composes the index because only it knows current `tool_calls` length (CONTEXT D-02). |
| Type contract for `StagedOpLifecycleError.from_status` | Store layer (`staged_operations.py`) | FB-B handlers | Already correct — type is `str | None`; Phase 19 only documents closure and adds a regression assertion. |
| Atomicity observation across approve+rollback | Test layer (`tests/test_staged_operations.py`) | — | Pure test rewrite; no production code touched. SQLAlchemy semantics force single-session observation (CONTEXT D-08). |
| Chat-template token tail-strip | LLM adapter (`OllamaToolAdapter.send_turn`) | Pattern source (`_sanitize_patterns.py`) for marker tuple | CONTEXT D-11 explicitly rejects chat-handler placement to keep the strip provider-scoped. Helper colocates with consumer per FB-C D-09 (patterns hoisted, helpers per-consumer). |
| Pattern set extension (`<|im_end|>`, `<|endoftext|>`) | Pattern source (`_sanitize_patterns.py`) | Test (`tests/test_sanitize.py`) | Single source of truth per FB-C D-09; existing count-lock test must move from 8→10. |

## Standard Stack

### Core (verified against `forge_bridge/llm/_adapters.py` imports + `pyproject.toml`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | bundled (3.10+) | `_ToolCall`, `_TurnResponse` shapes; `dataclasses.replace` for ref override | Already used module-wide; no new dep. [VERIFIED: line 28] |
| Python stdlib `re` | bundled | Tail-strip regex anchored at `\Z` | Already used in `_sanitize_patterns.py:31` for control-char removal. [VERIFIED] |
| Python stdlib `json` | bundled | Salvage JSON parsing (existing) | Already imported; no change. [VERIFIED: line 26] |
| `pytest` + `pytest-asyncio` (auto mode) | per `pyproject.toml` | Test runner | Already configured: `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` decorator needed. [VERIFIED: pyproject.toml] |
| `sqlalchemy` (async) | per project pin | Session/rollback semantics in POLISH-03 | Already used by `tests/test_staged_operations.py` and `forge_bridge/store/staged_operations.py`. [VERIFIED] |
| `ollama` | `>=0.6.1,<1` (latest 0.6.3) | Adapter target — no API touched by Phase 19 | Phase 19 does not call new ollama APIs; `_FakeTool` and `_fake_response_dict` test doubles in `tests/llm/test_ollama_adapter.py:48-65` cover all needed paths. [VERIFIED: npm view ollama / pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Existing `_sanitize_patterns.INJECTION_MARKERS` | tuple of 8 | Pattern set for tail-strip helper | Source of truth for chat-template tokens after P-04 extension. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dataclasses.replace(salvaged, ref=...)` for POLISH-01 | Direct mutation `salvaged.ref = ...` | `_ToolCall` is `@dataclass` (mutable, NOT frozen — verified at line 86), so direct mutation works too. CONTEXT D-02 / `code_context.reusable assets` recommends `replace()` for immutability discipline. Either is correct; `replace()` is the documented choice. |
| Adding `<|im_sep|>` to INJECTION_MARKERS | Skip it | CONTEXT D-12 marks it "Optional: defensively." No evidence of qwen2.5-coder emitting `<|im_sep|>`. Recommend skipping — yagni; bump only the two CONTEXT-locked tokens to keep the count-lock assertion bump auditable. |
| Tail-strip regex as a tuple-of-literals match-from-end | Single compiled regex from `INJECTION_MARKERS` | Compiled regex anchored at `\Z` is the cleaner expression for "consume contiguous run of any chat-template token possibly interleaved with whitespace." Specifics §3 prescribes greedy mode. |

**Installation:** No new deps. `pip install -e .[dev]` already in place from Phase 18.

**Version verification (2026-04-29):**
- `ollama` published version 0.6.3 (per `npm view`) — within the `>=0.6.1,<1` pin. No API drift relevant to Phase 19.

## Architecture Patterns

### System Architecture Diagram (data flow through Phase 19 touchpoints)

```
                       ┌───────────────────────────────────────┐
                       │  OllamaToolAdapter.send_turn()        │
                       │  forge_bridge/llm/_adapters.py        │
                       └───────────────────┬───────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              ▼                            ▼                            ▼
   ┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────┐
   │ Structured tool_calls│   │ Salvage path             │   │ NEW: tail-strip      │
   │ from response.message│   │ _try_parse_text_tool_call│   │ _strip_terminal_     │
   │  ref="{idx}:{name}"  │   │  (POLISH-01: derive ref  │   │  chat_template_tokens│
   │  (line 530-534)      │   │   AT call site, not      │   │  (POLISH-04: D-13)   │
   │                      │   │   inside helper)         │   │                      │
   │                      │   │  (lines 543-547)         │   │  (after salvage,     │
   │                      │   │                          │   │   before return)     │
   └──────────┬───────────┘   └────────────┬─────────────┘   └──────────┬───────────┘
              │                            │                            │
              └────────────────────────────┼────────────────────────────┘
                                           ▼
                              ┌────────────────────────────┐
                              │  _TurnResponse(text=text,  │
                              │  tool_calls=tool_calls,    │
                              │  usage_tokens=..., raw=...) │
                              └────────────────────────────┘

                Pattern source (single source of truth, FB-C D-09):
                ┌─────────────────────────────────────────────────┐
                │ forge_bridge/_sanitize_patterns.py              │
                │ INJECTION_MARKERS: tuple = (                    │
                │   "ignore previous", "<|", "|>",                │
                │   "[INST]", "[/INST]",                          │
                │   "<|im_start|>",                               │
                │   "```", "---",                                 │
                │   "<|im_end|>",     ← POLISH-04 D-12 ADD        │
                │   "<|endoftext|>",  ← POLISH-04 D-12 ADD        │
                │ )                                                │
                └─────────────────────────────────────────────────┘

                ┌─────────────────────────────────────────────────┐
                │ tests/test_sanitize.py:177                      │
                │ assert len(INJECTION_MARKERS) == 8 → BUMP TO 10 │
                │ (in-scope for P-04; not flagged in CONTEXT)     │
                └─────────────────────────────────────────────────┘
```

### Recommended Project Structure (no changes — verifying existing layout)

```
forge_bridge/
├── llm/
│   ├── _adapters.py               # POLISH-01 + POLISH-04 production target
│   └── router.py                  # untouched
├── store/
│   └── staged_operations.py       # POLISH-02 production target (comment only)
└── _sanitize_patterns.py          # POLISH-04 marker tuple extension

tests/
├── conftest.py                    # session_factory + _phase13_postgres_available (untouched)
├── llm/
│   ├── conftest.py                # _StubAdapter (D-37) — untouched
│   └── test_ollama_adapter.py     # NATURAL home for POLISH-01 + POLISH-04 unit tests
│                                  # (already has TestOllamaToolAdapterBugDFallback class)
├── test_sanitize.py               # POLISH-04 count-lock bump (line 177)
└── test_staged_operations.py      # POLISH-02 regression test + POLISH-03 rewrite
```

### Pattern 1: Captured-fixture-grounded RED test (Phase 16.2 precedent)
**What:** Encode upstream UAT failure-mode evidence as a verbatim Python constant in the test, plus optionally a JSON sibling in `.planning/`. Use a fixture-equality assertion to catch drift.
**When to use:** When a real production failure produced a serializable artifact and the test exists primarily to prevent regression.
**Example:**
```python
# Source: tests/llm/test_ollama_adapter.py:299 (existing pattern)
async def test_text_content_tool_call_salvaged(self):
    """Captured Phase 16.2 fixture; if drift detected, equality fails first."""
    captured_content = '{"name": "forge_tools_read", "arguments": {"name": "synthesis-tools"}}'
    # ... fake response, run adapter, assert salvage outcome
```

For POLISH-04: the captured fixture (`.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json`) does NOT contain the noise-tail variant — fall back to synthetic per CONTEXT D-14, but use the **HUMAN-UAT verbatim text** as the canonical synthetic input so the test matches a real artist-observed failure.

### Pattern 2: Single-session atomicity observation (POLISH-03)
**What:** Approve, flush, observe, rollback, observe again — all within one `async with session_factory()` block.
**When to use:** Verifying SQLAlchemy/Postgres rollback semantics. Cross-session observation against the SAME committed state requires a fresh DB or a deliberate visibility test that's out-of-scope here.
**Example:** see CONTEXT D-08 for the canonical block.

### Pattern 3: Helper at call site, not in shared module
**What:** Tail-strip helper lives in `forge_bridge/llm/_adapters.py` (private to OllamaToolAdapter), not in `_sanitize_patterns.py`.
**When to use:** When stripping/replacing semantics are consumer-specific. FB-C D-09 explicitly forbids consolidating helpers.
**Example:** Module docstring at `_sanitize_patterns.py:7-12` documents this rule. POLISH-04 D-13 follows it.

### Anti-Patterns to Avoid
- **Threading a literal `idx` into `_try_parse_text_tool_call`:** Signature churn for a one-line need (CONTEXT D-02 rejected this as alternative b).
- **Stripping chat-template tokens in `chat_handler`:** Would mask issues in non-Ollama providers; CONTEXT D-11 explicitly scopes this to the adapter layer.
- **Stripping mid-content occurrences in POLISH-04:** Sanitization concern handled elsewhere; tail-only per CONTEXT D-13.
- **Landing the RED experiment for POLISH-03 as a real commit:** CONTEXT D-09 documents-only — RED evidence stays in SUMMARY.md.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mutating a dataclass field | Custom copy logic | `dataclasses.replace()` | Already in stdlib; clearer intent. CONTEXT D-02 + `code_context.reusable assets` confirms. |
| Async session rollback observation | Cross-session probe with sleeps | Single `async with` block per CONTEXT D-08 | SQLAlchemy semantics: rollback only observable in the session that called it; cross-session needs an explicit transaction-isolation contract Phase 19 isn't testing. |
| Chat-template tokens as separate const | New `CHAT_TEMPLATE_TOKENS` tuple | Extend existing `INJECTION_MARKERS` | FB-C D-09 single-source-of-truth rule; one count-lock test guards drift. |
| JSON-shaped tool-call salvage | Re-parse the entire helper | Reuse `_try_parse_text_tool_call` (already widened in v1.4 close addendum) | Helper handles 5 known qwen2.5-coder shapes per `v1.4-MILESTONE-AUDIT.md`. |

**Key insight:** Every Phase 19 fix has an existing pattern in the codebase. Do not invent new structure; mirror what Phase 16.2 / FB-C / Phase 13 already established.

## Runtime State Inventory

> Phase 19 is code-edit only. No data migrations, no service config, no OS state. Filling each category for completeness:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by review of phase scope. No DB schema changes; `staged_operations.py` change is comment-only; `_adapters.py` changes touch in-flight conversation state, not persisted records. | None |
| Live service config | None — verified. No bridge core service exists yet (per `CLAUDE.md` "designed but not yet implemented"); no n8n/Datadog/Tailscale touchpoints in this phase. | None |
| OS-registered state | None — verified. Phase 19 does not register or rename systemd/launchd/Task-Scheduler entries. | None |
| Secrets/env vars | None — verified. `FORGE_DB_URL` (Phase 18) untouched. No new env vars introduced. | None |
| Build artifacts | None — verified. No `pyproject.toml` changes; no version bumps; the `.egg-info` directory will rebuild on next `pip install -e .` if Wave 0 runs it. The cached `.pyc` files in `forge_bridge/core/__pycache__/` (currently flagged as modified in git status) are unrelated to Phase 19 — those are an existing local artifact. | None |

## Common Pitfalls

### Pitfall 1: Forgetting the count-lock assertion in `tests/test_sanitize.py:177`
**What goes wrong:** `INJECTION_MARKERS` extension lands; `tests/llm/test_ollama_adapter.py` POLISH-04 test passes; but `tests/test_sanitize.py::test_injection_markers_count_locked` fails because it asserts `len(INJECTION_MARKERS) == 8`.
**Why it happens:** The count-lock test was added by FB-C D-10 specifically to catch silent-shim drift; Phase 19's CONTEXT does not flag it.
**How to avoid:** P-04 plan MUST bump line 177 to `assert len(INJECTION_MARKERS) == 10` in the same atomic commit.
**Warning signs:** `pytest tests/test_sanitize.py -v` red after P-04.

### Pitfall 2: Off-by-3 line numbers in CONTEXT
**What goes wrong:** Plan says "edit line 363" (placeholder per CONTEXT D-08); actual placeholder is at line 360. Edit at line 363 deletes the wrong line.
**Why it happens:** CONTEXT was written from memory; current file shows `assert True  # placeholder` at line 360, contradiction-assertion at line 388.
**How to avoid:** Plans should reference the exact text to delete (e.g., `assert True  # placeholder; the meaningful check is below`) and the exact replacement block, not raw line numbers. Use grep-pattern anchors.

### Pitfall 3: Edit ordering inside `OllamaToolAdapter.send_turn` (P-01 vs. P-04 file conflict)
**What goes wrong:** P-01 edits the salvage block (lines 543-547); P-04 inserts the tail-strip call AFTER the salvage block (lines 548-549). If run in parallel, two agents conflict on the same hunk.
**Why it happens:** CONTEXT D-17 already flags this — both touch `_adapters.py`. The recommended split is Wave 1 (P-01/P-02/P-03) and Wave 2 (P-04).
**How to avoid:** Honor CONTEXT D-17. P-04 plan body should reference the post-P-01 state (i.e., the `salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.name}")` line is already present when P-04 lands).
**Warning signs:** Executor reports merge conflict in `forge_bridge/llm/_adapters.py` around line 545.

### Pitfall 4: `dataclasses.replace` import missing
**What goes wrong:** `_adapters.py` imports `dataclass` (line 28) but NOT `replace`. P-01 plan must add `replace` to the import.
**Why it happens:** Easy to overlook; the helper uses only `@dataclass` decorator currently.
**How to avoid:** P-01 plan body explicitly enumerates `from dataclasses import dataclass, replace` as the import-line edit.
**Warning signs:** `NameError: name 'replace' is not defined` at adapter import time.

### Pitfall 5: Synthetic vs. captured fixture confusion for POLISH-04
**What goes wrong:** Plan author searches `16.2-CAPTURED-OLLAMA-RESPONSE.json`, finds no `<|im_start|>`, concludes "no fixture exists" — falls back to a fabricated noise tail that doesn't match the real artifact.
**Why it happens:** Two artifacts in the same Phase 16.2 directory: the JSON capture (Plan 01 evidence) and the HUMAN-UAT markdown (Plan 04 evidence). The noise-tail evidence lives in the latter, not the former.
**How to avoid:** Plan body MUST cite `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md:106-107` as the synthetic-fixture source and replicate the exact text. See "Specific Ideas" below.

### Pitfall 6: `_phase13_postgres_available()` skips POLISH-03 silently in CI
**What goes wrong:** P-03 plan author runs `pytest tests/test_staged_operations.py::test_transition_atomicity -v` in a no-Postgres environment; sees "skipped"; assumes test passes.
**Why it happens:** Phase 18 HARNESS-03 cleaned up the gate so it skips silently when no DB is reachable — friendly for CI, hostile for "did my fix work?"
**How to avoid:** P-03 verification MUST run against live dev Postgres (`FORGE_DB_URL=postgresql://forge:...@localhost:7533/forge_bridge`) per Phase 18 precedent. Plan SUMMARY captures the run with the env var set.

## Code Examples

### Example 1: POLISH-01 ref derivation (D-02 + D-03)
```python
# forge_bridge/llm/_adapters.py:206 — INSIDE _try_parse_text_tool_call
# Before:
return _ToolCall(
    ref=f"0:{name}",  # idx is always 0 — the salvage path emits one tool call per turn
    tool_name=name,
    arguments=dict(args),
)
# After (per CONTEXT D-03):
return _ToolCall(
    ref=f"salvage:{name}",  # placeholder; call site overwrites with index-derived ref
    tool_name=name,
    arguments=dict(args),
)

# forge_bridge/llm/_adapters.py:543-547 — call site
# Before:
if not tool_calls and text:
    salvaged = _try_parse_text_tool_call(text)
    if salvaged is not None:
        tool_calls.append(salvaged)
        text = ""  # consumed — don't double-emit as terminal content (re-Bug-D risk)
# After (per CONTEXT D-02):
if not tool_calls and text:
    salvaged = _try_parse_text_tool_call(text)
    if salvaged is not None:
        # Derive ref from current tool_calls position — collision-free even if the
        # salvage guard ever loosens. Was hardcoded "0:{name}" (WR-02 closure).
        salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")
        tool_calls.append(salvaged)
        text = ""  # consumed — don't double-emit as terminal content (re-Bug-D risk)
```
*Note: `_ToolCall.tool_name` (NOT `name`) — verified at line 96.*

### Example 2: POLISH-02 comment rewrite (D-06)
```python
# forge_bridge/store/staged_operations.py:325-330 — Before:
# UUID doesn't resolve to a staged_op — distinct from illegal-transition.
# FB-B handlers (Plan 14-03 + 14-04) map `from_status is None` → HTTP 404
# `staged_op_not_found`. Sentinel string "(missing)" was the WR-01 bug; the
# None discriminator is now load-bearing for the FB-B 404/409 split.
raise StagedOpLifecycleError(
    from_status=None, to_status=new_status, op_id=op_id,

# After (per CONTEXT specifics + D-06):
# UUID doesn't resolve to a staged_op — distinct from illegal-transition.
# FB-B handlers (Plan 14-03 + 14-04) map `from_status is None` → HTTP 404
# `staged_op_not_found`. WR-01 (Phase 13 review) was closed by passing
# `from_status=None` here; the original sentinel string is no longer used
# in the codebase. POLISH-02 (Phase 19) confirmed this with a regression test.
raise StagedOpLifecycleError(
    from_status=None, to_status=new_status, op_id=op_id,
```
*Note: rewrite drops the `"(missing)"` literal so the post-fix grep returns zero matches.*

### Example 3: POLISH-02 regression test (CONTEXT D-06)
```python
# tests/test_staged_operations.py — added near other transition tests
async def test_lifecycle_error_from_status_is_optional_str_never_missing_sentinel(
    session_factory,
):
    """POLISH-02 / WR-01 regression guard: StagedOpLifecycleError.from_status
    is Optional[str], never the literal string '(missing)'. The None case
    discriminates 404 (unknown UUID) from 409 (illegal transition) at the
    FB-B handler boundary."""
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        # Unknown UUID path → from_status MUST be None
        with pytest.raises(StagedOpLifecycleError) as excinfo_unknown:
            await repo.approve(uuid.uuid4(), approver="x")
        assert excinfo_unknown.value.from_status is None
        assert excinfo_unknown.value.from_status != "(missing)"

        # Illegal transition path → from_status MUST be a non-None status string
        op = await repo.propose(operation="o", proposer="p", parameters={})
        await session.commit()
        with pytest.raises(StagedOpLifecycleError) as excinfo_illegal:
            await repo.execute_success(op.id, executor="x", result={})  # not approved
        assert isinstance(excinfo_illegal.value.from_status, str)
        assert excinfo_illegal.value.from_status != "(missing)"
        assert excinfo_illegal.value.from_status == "proposed"
```
*Note: this test partially overlaps `test_transition_unknown_uuid_raises_with_from_status_none` at line 611 — explicitly assert against the `"(missing)"` literal to make the regression intent unambiguous.*

### Example 4: POLISH-03 atomicity rewrite (CONTEXT D-08)
```python
# tests/test_staged_operations.py:323-398 — REPLACE the body wholesale (keep the
# function signature + docstring). The three sequential session blocks become a
# single observation block.
async def test_transition_atomicity(session_factory):
    """security_threat_model 'audit-trail tamper / dropped events':
    if the session rolls back, BOTH the entity status update AND the event
    append are reverted — there is no scenario where status advances without
    a matching event row.
    """
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(
            operation="op-atom", proposer="p", parameters={},
        )
        await session.commit()  # baseline: 1 entity + 1 staged.proposed event committed

        # Approve in same session, flush (push to DB), observe pre-rollback state
        await repo.approve(op.id, approver="artist")
        await session.flush()
        events_mid = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
        assert len(events_mid) == 2, "both events visible pre-rollback"

        await session.rollback()

        # Post-rollback: only the originally-committed state remains
        events_after = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
        assert len(events_after) == 1
        assert events_after[0].event_type == "staged.proposed"
        fetched = await repo.get(op.id)
        assert fetched is not None
        assert fetched.status == "proposed"
```
*Note: this is the literal block from CONTEXT D-08; verified all referenced names (`StagedOpRepo`, `EventRepo`, `session_factory`) are already imported. Drop the `select(DBEntity)` / `select(DBEvent)` raw-query block from the old test (lines 385-398) — `repo.get()` and `EventRepo.get_recent()` are higher-level and consistent with other tests in the file.*

### Example 5: POLISH-04 tail-strip helper + send_turn integration (CONTEXT D-11..D-15)
```python
# forge_bridge/llm/_adapters.py — NEW helper, place near _try_parse_text_tool_call
import re  # add to imports if not present (already present at line 26 indirectly)

# Pre-compile at module scope; uses the SHARED INJECTION_MARKERS source of truth.
from forge_bridge._sanitize_patterns import INJECTION_MARKERS

# Build a regex that matches a contiguous tail-run of any chat-template-style
# token, optionally interleaved with whitespace. Anchored at end-of-string (\Z).
# Only chat-template tokens — NOT every INJECTION_MARKER (e.g., "ignore previous"
# is a prose phrase that should never appear in a real assistant response, and
# stripping it from a tail context might mask other issues).
_CHAT_TEMPLATE_TAIL_TOKENS: tuple[str, ...] = (
    "<|im_start|>",
    "<|im_end|>",
    "<|endoftext|>",
)
_CHAT_TEMPLATE_TAIL_RE: re.Pattern[str] = re.compile(
    r"(?:" + "|".join(re.escape(t) for t in _CHAT_TEMPLATE_TAIL_TOKENS) + r"|\s)+\Z"
)


def _strip_terminal_chat_template_tokens(text: str) -> str:
    """Strip a contiguous tail-run of chat-template special tokens from `text`.

    Phase 16.2 UAT (HUMAN-UAT.md:106-107) recorded qwen2.5-coder occasionally
    appending `<|im_start|><|im_start|>...` chat-template noise after the real
    answer prose. This helper removes that tail; mid-content occurrences are
    a sanitization concern handled by `_sanitize_tool_result()` (FB-C D-09).
    """
    if not text:
        return text
    return _CHAT_TEMPLATE_TAIL_RE.sub("", text)


# In OllamaToolAdapter.send_turn(), after the salvage block (post-P-01 state):
if not tool_calls and text:
    salvaged = _try_parse_text_tool_call(text)
    if salvaged is not None:
        salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")
        tool_calls.append(salvaged)
        text = ""

# NEW (POLISH-04 D-15 step 3):
text = _strip_terminal_chat_template_tokens(text)

# ... return _TurnResponse(text=text, ...) — unchanged structurally
```
*Note: regex uses non-capturing group + alternation + `\s` to consume "any chat-template token OR whitespace" greedily, anchored at `\Z`. Greedy mode handles the canonical noise tail `<|im_start|><|im_start|>\n<|im_start|><|im_start|>{...}` from HUMAN-UAT.md:106-107 — though the embedded `{...}` JSON would NOT match the regex and would survive. That is BY DESIGN: if the model emits `<|im_start|>{tool_call_json}` at the tail, the stripping reveals JSON that the salvage path can re-process on a future turn (or that the regex-reject in chat-handler would still flag). The strip is for the trailing token noise alone, not for embedded JSON.*

### Example 6: POLISH-04 unit test pattern (synthetic from HUMAN-UAT)
```python
# tests/llm/test_ollama_adapter.py — extend with new test class
# (or add to existing TestOllamaToolAdapterBugDFallback per CONTEXT discretion)

class TestOllamaToolAdapterChatTemplateTailStrip:
    """POLISH-04: qwen2.5-coder occasionally appends `<|im_start|>` chat-template
    tokens at the tail of synthesized prose. Verify the strip in send_turn().

    Synthetic fixture mirrors HUMAN-UAT.md:106-107 verbatim (no captured JSON
    artifact preserved the noise tail; using the prose+token fragment from
    the live UAT log)."""

    NOISE_TAIL_PROSE = (
        "It seems there are no synthesis tools registered this week. "
        "If you meant to check for staged operations or something else "
        "related to this week's activity, please specify.\n"
        "<|im_start|><|im_start|>\n"
        "<|im_start|><|im_start|>"
        # Note: omit the embedded second-tool-call JSON — that is a separate
        # model-quality artifact orthogonal to the tail-token strip.
    )

    async def test_terminal_chat_template_tokens_stripped(self):
        # Use existing _fake_response_dict + a mocked AsyncClient.chat to feed
        # NOISE_TAIL_PROSE into send_turn(); assert returned text ends with
        # "please specify." and contains no "<|im_start|>" substring.
        ...

    async def test_clean_prose_passes_through_unchanged(self):
        clean = "No synthesis tools were created this week."
        # send_turn() with content=clean → _TurnResponse.text == clean
        ...
```
*Note: existing test patterns in `tests/llm/test_ollama_adapter.py:55-65` (`_fake_response_dict`) and at line 299 (`test_text_content_tool_call_salvaged`) provide the mock-AsyncClient template.*

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_phase13_postgres_available()` gated by `FORGE_TEST_DB=1` | Gated by `FORGE_DB_URL` only; silent skip if no DB | Phase 18 HARNESS-03 (2026-04-29) | POLISH-03 verification MUST set `FORGE_DB_URL` to actually exercise the test. |
| `starlette.TestClient` for staged-handler HTTP tests | `httpx.AsyncClient(transport=ASGITransport)` | Phase 18 HARNESS-01 (2026-04-29) | Not directly relevant to Phase 19 (no console-handler edits), but informs the test-async pattern. |
| `_try_parse_text_tool_call` strict `json.loads(content)` | `json.JSONDecoder().raw_decode()` + markdown-fence stripping | v1.4 close addendum (WR-01 widening) | Helper now handles 5 known qwen2.5-coder shapes; POLISH-01 only changes the ref construction, not the parsing. |
| `INJECTION_MARKERS` count: 7 (FB-C ship) | 8 (current — `---` added Phase 7 / FB-C boundary work) | FB-C / Phase 7 consolidation | POLISH-04 bumps to 10. Count-lock test at `tests/test_sanitize.py:177` enforces deliberate updates. |

**Deprecated/outdated:** None for Phase 19 — every API touched is current as of v1.4.0.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| (none) | All factual claims in this research are `[VERIFIED]` against current source files, `[CITED]` from CONTEXT.md / REQUIREMENTS.md / v1.4-MILESTONE-AUDIT.md, or directly observed via grep / `npm view`. No `[ASSUMED]` claims remain. | — | — |

## Open Questions

1. **Should POLISH-01's unit test live in `tests/llm/test_ollama_adapter.py` (existing file with `TestOllamaToolAdapterBugDFallback` class) or a new `tests/llm/test_adapters_salvage_ref.py`?**
   - What we know: CONTEXT marks this as Claude's Discretion. `tests/llm/test_ollama_adapter.py` already has the right scaffolding (fake-tool/fake-response helpers, BugD-fallback test class).
   - What's unclear: whether the planner prefers test-file granularity (1 polish requirement = 1 test file) or test-class clustering (all OllamaToolAdapter tests in one file).
   - Recommendation: **add to existing file** — `TestOllamaToolAdapterBugDFallback` is the natural home (same class can absorb both POLISH-01 ref derivation AND POLISH-04 tail-strip tests under sibling sub-classes). Reduces file proliferation and keeps the salvage-path test surface co-located.

2. **Is `<|im_sep|>` worth adding defensively (CONTEXT D-12 marks it optional)?**
   - What we know: Not present in HUMAN-UAT artifact; not seen in any captured response.
   - What's unclear: whether qwen2.5-coder's chat template uses `<|im_sep|>` in any code path we haven't probed.
   - Recommendation: **skip** — yagni; only the two tokens with evidence (`<|im_end|>`, `<|endoftext|>` are common qwen template tokens documented widely; CONTEXT explicitly cited these). Keeps the count-lock bump auditable (8 → 10, not 8 → 11).

3. **Should the `salvaged.tool_name` (not `salvaged.name`) attribute be flagged in P-01 plan?**
   - What we know: `_ToolCall.tool_name` is the actual field (verified at line 96); `name` is the local variable inside the helper. CONTEXT D-02's example uses `salvaged.name` which would `AttributeError`.
   - What's unclear: whether the executor will catch this from CONTEXT alone.
   - Recommendation: **plan body MUST cite the correct attribute** — `salvaged.tool_name` — explicitly to avoid a 1-character bug. (This is one of those discretionary attention checks that planners need to surface; the research notes it here so it doesn't get lost.)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `pytest` + `pytest-asyncio` | All four POLISH unit tests | ✓ (per `pyproject.toml`) | bundled in dev extra | — |
| Postgres at `FORGE_DB_URL` | POLISH-03 atomicity test | unverified at research time | — | If unavailable, test skips silently per Phase 18 HARNESS-03; verification gate FAILS to capture green evidence — must run on dev workstation with Postgres at `:7533/forge_bridge`. |
| Ollama at `localhost:11434` | NOT required — POLISH-04 uses mocked `AsyncClient.chat` per existing `tests/llm/test_ollama_adapter.py` pattern | ✓ (mocked) | — | — |
| `dataclasses.replace` (stdlib) | POLISH-01 | ✓ | Python 3.10+ | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Postgres for POLISH-03 — falls back to silent skip but that defeats the purpose. Plan SUMMARY for P-03 MUST cite a green run with `FORGE_DB_URL` set.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` + `pytest-asyncio` (auto mode) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options] asyncio_mode = "auto"`) |
| Quick run command | `pytest tests/llm/test_ollama_adapter.py tests/test_sanitize.py tests/test_staged_operations.py::test_transition_atomicity tests/test_staged_operations.py::test_lifecycle_error_from_status_is_optional_str_never_missing_sentinel -v` |
| Full suite command | `FORGE_DB_URL=postgresql://forge:...@localhost:7533/forge_bridge pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POLISH-01 | Salvaged tool-call ref derives from current `tool_calls` length, never literal `"0:"` | unit | `pytest tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback -v` (extended with new sub-class or test method) | ✅ existing file; ❌ new test method |
| POLISH-01 (guard) | No literal `"0:"` string remains in salvage helper or call site | grep guard | `! grep -nE '"0:"\|f"0:\{' forge_bridge/llm/_adapters.py \| grep -v '^\s*#'` | ✅ |
| POLISH-02 | `StagedOpLifecycleError.from_status` is `None` for unknown-UUID, non-None str for illegal transitions; never `"(missing)"` | unit | `pytest tests/test_staged_operations.py::test_lifecycle_error_from_status_is_optional_str_never_missing_sentinel -v` | ❌ new test (Wave 0) |
| POLISH-02 (guard) | No `"(missing)"` literal anywhere in source/tests post-fix | grep guard | `! grep -rn '"(missing)"' forge_bridge/ tests/` | ✅ |
| POLISH-03 | Single-session approve+flush+rollback observation: 2 events visible mid, 1 event + status='proposed' post-rollback | unit (live Postgres) | `FORGE_DB_URL=... pytest tests/test_staged_operations.py::test_transition_atomicity -v` | ✅ existing test (rewrite) |
| POLISH-04 | Tail-only strip of `<\|im_start\|>` / `<\|im_end\|>` / `<\|endoftext\|>` runs from `_TurnResponse.text` | unit | `pytest tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterChatTemplateTailStrip -v` (new sub-class) | ❌ new test (Wave 0) |
| POLISH-04 | Clean prose without trailing tokens passes through unchanged | unit | same command, sibling test method | ❌ new test (Wave 0) |
| POLISH-04 (count-lock) | `len(INJECTION_MARKERS) == 10` | unit | `pytest tests/test_sanitize.py::test_injection_markers_count_locked -v` | ✅ existing test (assertion bump) |

### Sampling Rate
- **Per task commit:** `pytest tests/llm/test_ollama_adapter.py tests/test_sanitize.py tests/test_staged_operations.py -v` (~5–15s without DB; ~30–60s with DB)
- **Per wave merge:** Full suite, with `FORGE_DB_URL` set so POLISH-03 actually runs
- **Phase gate:** Full suite green; manual confirmation that the four `! grep` guards return zero matches

### Wave 0 Gaps
- [x] No new fixture files needed — `session_factory` (Phase 13/18) and `_fake_response_dict` (Phase 16.2) already in place
- [x] No new framework install — `pytest`/`pytest-asyncio` already in dev extras
- [ ] Plan author MUST verify dev Postgres is reachable BEFORE running P-03 verification (`pg_isready -h localhost -p 7533` or equivalent)
- [ ] No new test files strictly required, but planner may choose to create `tests/llm/test_adapters_salvage_ref.py` and/or `tests/llm/test_adapters_tail_strip.py` for granularity (CONTEXT discretion). Default recommendation: extend existing `tests/llm/test_ollama_adapter.py` with new test classes.

## Security Domain

> Phase 19 is internal-quality work; no new authentication, authorization, session, or input-validation surfaces. Tail-strip of qwen2.5-coder noise is closer to a sanitization-adjacent concern but does not change the trust boundary.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — auth deferred to v1.5 (per `CLAUDE.md`) |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | partial | POLISH-04 strips chat-template tokens at the adapter boundary. The "input" here is the LLM's own response text, not external input. The strip is a model-quality polish, not a defense-in-depth control. The actual prompt-injection defense lives in `_sanitize_tool_result()` (FB-C LLMTOOL-06) and is unchanged. |
| V6 Cryptography | no | n/a |

### Known Threat Patterns for forge-bridge LLM adapter layer

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Audit-trail tamper / dropped events | Repudiation | Atomicity contract: status update + event append in same session; rollback reverts both. POLISH-03 strengthens the regression test for this. |
| Tool-call ref collision masking distinct calls | Tampering | Composite ref `{idx}:{name}` already used on structured path (line 531); POLISH-01 extends this discipline to the salvage path so the ref-collision-via-loosened-guard scenario can never silently merge two tool calls. |
| Prompt injection via tool result | Tampering | `_sanitize_tool_result()` (FB-C) — UNTOUCHED by Phase 19. POLISH-04's tail-strip is NOT a sanitization helper; FB-C D-09 explicitly rejects consolidating helpers across consumers. |

## Sources

### Primary (HIGH confidence)
- **CONTEXT.md** (`.planning/phases/19-code-quality-polish/19-CONTEXT.md`) — D-01..D-17 lock implementation choices; baseline measurements landed during context discussion
- **REQUIREMENTS.md** (`.planning/REQUIREMENTS.md`) — POLISH-01..04 acceptance criteria
- **v1.4-MILESTONE-AUDIT.md** — original WR-01/WR-02 findings; addendum noting WR-01 widened in v1.4 close
- **`forge_bridge/llm/_adapters.py`** (lines 1-594, current source) — `_try_parse_text_tool_call` at 122-209; salvage call site at 543-547; `_ToolCall` dataclass at 85-97
- **`forge_bridge/_sanitize_patterns.py`** (lines 1-32, current source) — `INJECTION_MARKERS` tuple of 8 at lines 19-28
- **`forge_bridge/store/staged_operations.py`** (lines 60-340, current source) — type signature at 74; comment to rewrite at 326; raise sites at 328-330 + 333-335
- **`tests/test_staged_operations.py`** (lines 1-400, current source) — atomicity test 323-398; placeholder at 360; contradiction-assertion at 388
- **`tests/test_sanitize.py`** (lines 170-181, current source) — count-lock assertion at line 177
- **`tests/llm/test_ollama_adapter.py`** (lines 1-433, current source) — existing `TestOllamaToolAdapterBugDFallback` class at 284-433
- **`.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md`** lines 100-113 — verbatim noise-tail evidence for POLISH-04 synthetic fixture
- **`.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json`** — Phase 16.2 captured fixture; verified to NOT contain noise-tail variant (zero `im_start`/`im_end`/`endoftext` matches)
- **pyproject.toml** — pytest config (`asyncio_mode = "auto"`); ollama pin (`>=0.6.1,<1`); dev extras

### Secondary (MEDIUM confidence)
- **npm view ollama version** → 0.6.3 (latest as of 2026-04-29); within pin

### Tertiary (LOW confidence)
- None — all claims are verified or cited.

## Project Constraints (from CLAUDE.md)

- forge-bridge is **middleware** — protocol-agnostic. Phase 19 must not introduce Flame-specific coupling. (Trivially satisfied — no Flame surfaces touched.)
- Vocabulary spec lives in `docs/VOCABULARY.md` but is not yet implemented. Phase 19 does not touch the vocabulary engine.
- "Don't break the working flame hook + MCP server" — Phase 19 does not touch `flame_hooks/` or the MCP server tool registration. Verified: targets are `forge_bridge/llm/`, `forge_bridge/store/`, `forge_bridge/_sanitize_patterns.py`, `tests/`. None overlap with flame hook scripts.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency verified against current `pyproject.toml` + source imports; no new deps
- Architecture: HIGH — every line number checked against the live source tree; CONTEXT decisions verified compatible with current code
- Pitfalls: HIGH — Pitfall 1 (count-lock) and Pitfall 4 (`replace` import) and Pitfall 5 (HUMAN-UAT vs JSON capture confusion) are NEW findings from this research not pre-flagged in CONTEXT; Pitfalls 2, 3, 6 reinforce CONTEXT-noted concerns

**Research date:** 2026-04-29
**Valid until:** 2026-05-29 (30 days — surgical fixes against stable v1.4 source; main risk is Phase 18-style follow-up changes to `tests/conftest.py` or staged-handler tests, neither expected in this window)
