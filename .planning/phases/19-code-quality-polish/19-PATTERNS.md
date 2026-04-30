# Phase 19: Code-quality polish - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 6 (all modifications — no new files)
**Analogs found:** 6 / 6 (every edit has an in-tree precedent)

---

## File Classification

Phase 19 is purely surgical — no new files. Every target is a modification with an existing analog in the same file or sibling file. Classification reflects the tier each edit lives in (per RESEARCH.md "Architectural Responsibility Map").

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `forge_bridge/llm/_adapters.py` (POLISH-01: salvage call site lines 543-547 + helper return line 206 + import line 28) | adapter (LLM tool-call) | request-response (transform) | structured-path tool_call construction at `forge_bridge/llm/_adapters.py:530-534` (same file, same function) | **exact** |
| `forge_bridge/llm/_adapters.py` (POLISH-04: new module-scope tail-strip helper + send_turn integration after salvage block) | adapter helper (private to OllamaToolAdapter) | transform | `forge_bridge/_sanitize_patterns.py:31` (precompiled module-scope regex pattern) + `_try_parse_text_tool_call` at `_adapters.py:122-209` (private helper colocated with consumer) | **role-match** (regex-helper template; no existing tail-strip helper) |
| `forge_bridge/store/staged_operations.py` (POLISH-02: rewrite comment at line 326) | store (staged-ops repo) | comment-only | n/a — pure documentation rewrite | **n/a** |
| `forge_bridge/_sanitize_patterns.py` (POLISH-04: extend `INJECTION_MARKERS` tuple at lines 19-28) | shared pattern source | constant extension | the tuple itself — append two entries in the same shape (string literals) | **exact** |
| `tests/test_staged_operations.py` (POLISH-02 new test method + POLISH-03 rewrite of `test_transition_atomicity` lines 323-398) | test (store-layer pytest-asyncio) | test (CRUD via repo + session_factory) | `test_transition_unknown_uuid_raises_with_from_status_none` at line 611 (POLISH-02 mirror); `test_audit_replay` / propose-approve patterns earlier in same file (POLISH-03 mirror) | **exact** |
| `tests/test_sanitize.py` (POLISH-04: bump count assertion at line 177) | test (count-lock guard) | constant assertion | line 177 itself — change `8` to `10` | **exact** |
| `tests/llm/test_ollama_adapter.py` (POLISH-01 new test method + POLISH-04 new test class) | test (adapter unit tests) | test (mocked AsyncClient.chat) | `TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_salvaged` at line 299 + `_fake_response_dict` at lines 55-65 | **exact** |

---

## Pattern Assignments

### `forge_bridge/llm/_adapters.py` — POLISH-01 ref derivation (call site + helper)

**Analog:** structured tool-call construction in the **same file, same function** (`OllamaToolAdapter.send_turn`) at lines 530-534.

**Imports pattern** (line 28, current state):
```python
from dataclasses import dataclass
```

**Imports pattern** (post-POLISH-01, expand to multi-name):
```python
from dataclasses import dataclass, replace
```
*Trivial textual edit. No "expand single-name import" analog needed in this codebase — the canonical post-state matches every standard Python import expansion.*

**Existing `dataclasses.replace` usage in the codebase** (closest analog for the replace call itself):
```python
# forge_bridge/learning/execution_log.py:342
rec = dataclasses.replace(rec, promoted=True)
```
*Note: this analog uses the qualified `dataclasses.replace(...)` form. POLISH-01 uses the bare `replace(...)` form per CONTEXT D-02 (since `replace` is added to the `from dataclasses import` line). Both are correct; POLISH-01's choice keeps the call site terse.*

**Structured-path ref construction** (the analog the salvage path mirrors), `_adapters.py:530-534`:
```python
tool_calls.append(_ToolCall(
    ref=f"{idx}:{name}",  # composite ref (research §5.2)
    tool_name=name,
    arguments=dict(args) if args else {},
))
```

**Current salvage call site** (`_adapters.py:543-547`):
```python
if not tool_calls and text:
    salvaged = _try_parse_text_tool_call(text)
    if salvaged is not None:
        tool_calls.append(salvaged)
        text = ""  # consumed — don't double-emit as terminal content (re-Bug-D risk)
```

**Current helper return** (`_adapters.py:205-209`):
```python
return _ToolCall(
    ref=f"0:{name}",  # idx is always 0 — the salvage path emits one tool call per turn
    tool_name=name,
    arguments=dict(args),
)
```

**Pattern to apply** (per CONTEXT D-02/D-03):
- Helper return uses placeholder `ref=f"salvage:{name}"` (string `"0:"` removed entirely from helper).
- Call site composes ref via `replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")` BEFORE `tool_calls.append(salvaged)`.
- Field is `salvaged.tool_name` (NOT `salvaged.name`) — verified at `_ToolCall` definition line 95-97. This is RESEARCH.md Open Question #3.

**`_ToolCall` dataclass** (`_adapters.py:85-97`) — reference for the `tool_name` field:
```python
@dataclass
class _ToolCall:
    ref: str
    tool_name: str
    arguments: dict
```
*Mutable (NOT frozen) — direct mutation `salvaged.ref = ...` would also work; CONTEXT D-02 picks `replace()` for immutability discipline, mirroring `learning/execution_log.py:342`.*

---

### `forge_bridge/llm/_adapters.py` — POLISH-04 tail-strip helper

**Analog 1 (regex template):** `forge_bridge/_sanitize_patterns.py:30-31`:
```python
# Control characters: \x00-\x1f plus \x7f (DEL)
_CONTROL_CHAR_RE: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")
```
*Pattern: module-scope precompiled regex with a typed annotation (`re.Pattern[str]`) and a brief comment naming the input class. POLISH-04's `_CHAT_TEMPLATE_TAIL_RE` follows this template verbatim.*

**Analog 2 (private helper colocated with consumer):** `_try_parse_text_tool_call` at `_adapters.py:122-209` is the canonical "private helper colocated with the consumer" example for the OllamaToolAdapter. POLISH-04's `_strip_terminal_chat_template_tokens` lives in the same file, near the same docstring conventions, with a Phase-tagged commit reference in its first paragraph (mirror the Phase 16.2 attribution style used in `_try_parse_text_tool_call`).

**Helper docstring style** (mirror this from `_try_parse_text_tool_call:122-155`):
```
"""<one-line behavioral summary>

<paragraph context with provenance: which model, which Phase artifact>

<one-paragraph contract: what the helper does NOT do (boundary)>

See <Phase artifact path> for the original failure-mode evidence trail.
"""
```

**Send_turn integration ordering** — surface the existing structure at `_adapters.py:543-561`:
```python
# (post-POLISH-01 state — assumes Wave 1 has already landed)
if not tool_calls and text:
    salvaged = _try_parse_text_tool_call(text)
    if salvaged is not None:
        salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")
        tool_calls.append(salvaged)
        text = ""

# NEW (POLISH-04 D-15 step 3) — inserted here:
text = _strip_terminal_chat_template_tokens(text)

if isinstance(response, dict):
    prompt_tokens = response.get("prompt_eval_count", 0) or 0
    ...
return _TurnResponse(text=text, tool_calls=tool_calls, ...)
```
*Order matters per CONTEXT D-15: salvage runs first (so the salvage path sees the FULL original text including any tail noise that might be hiding JSON), then strip runs on the residual text. If the salvage path emits a tool call, `text` is already `""` and the strip is a no-op (helper short-circuits on empty).*

---

### `forge_bridge/store/staged_operations.py` — POLISH-02 comment rewrite

**Analog:** none — this is a pure documentation rewrite. The surrounding code at `staged_operations.py:322-335` is the context.

**Current comment to rewrite** (`staged_operations.py:324-327`):
```python
# UUID doesn't resolve to a staged_op — distinct from illegal-transition.
# FB-B handlers (Plan 14-03 + 14-04) map `from_status is None` → HTTP 404
# `staged_op_not_found`. Sentinel string "(missing)" was the WR-01 bug; the
# None discriminator is now load-bearing for the FB-B 404/409 split.
```

**Rewrite target** (per CONTEXT specifics + D-06):
```python
# UUID doesn't resolve to a staged_op — distinct from illegal-transition.
# FB-B handlers (Plan 14-03 + 14-04) map `from_status is None` → HTTP 404
# `staged_op_not_found`. WR-01 (Phase 13 review) was closed by passing
# `from_status=None` here; the original sentinel string is no longer used
# in the codebase. POLISH-02 (Phase 19) confirmed this with a regression test.
```
*Acceptance criterion: post-fix, `grep -rn '"(missing)"' forge_bridge/ tests/` returns zero matches. The literal `"(missing)"` MUST disappear from the comment so the grep guard is unambiguous.*

**Type signature reference** (`staged_operations.py:74` — already correct, no edit):
```python
def __init__(
    self,
    from_status: str | None,
    to_status: str,
    op_id: uuid.UUID,
):
```

---

### `forge_bridge/_sanitize_patterns.py` — POLISH-04 tuple extension

**Analog:** the tuple itself at lines 19-28 — append two entries in matching style.

**Current state**:
```python
INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous",
    "<|",
    "|>",
    "[INST]",
    "[/INST]",
    "<|im_start|>",
    "```",  # triple backtick — markdown code fence
    "---",  # yaml document separator
)
```

**Post-POLISH-04 state** (per CONTEXT D-12):
```python
INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous",
    "<|",
    "|>",
    "[INST]",
    "[/INST]",
    "<|im_start|>",
    "```",  # triple backtick — markdown code fence
    "---",  # yaml document separator
    "<|im_end|>",     # qwen chat template — terminal token
    "<|endoftext|>",  # qwen chat template — sequence terminator
)
```
*Skip `<|im_sep|>` per RESEARCH.md Open Question #2 (yagni; no UAT evidence). Adding only the two CONTEXT-locked tokens keeps the count-lock bump 8→10 auditable.*

---

### `tests/test_staged_operations.py` — POLISH-02 new regression test

**Analog:** `test_transition_unknown_uuid_raises_with_from_status_none` at `tests/test_staged_operations.py:611-620`:
```python
async def test_transition_unknown_uuid_raises_with_from_status_none(session_factory):
    """WR-01: approve(bogus_uuid) raises StagedOpLifecycleError with from_status is None."""
    bogus = uuid.uuid4()
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        with pytest.raises(StagedOpLifecycleError) as exc_info:
            await repo.approve(bogus, approver="x")
        assert exc_info.value.from_status is None, (
            f"WR-01: not-found must use None discriminator, got {exc_info.value.from_status!r}"
        )
```

**Pattern to mirror in the new POLISH-02 regression test:**
- File location: same file (`tests/test_staged_operations.py`), placed near the existing WR-01 regression cluster (after line 656 or wherever the cluster ends).
- Fixture: `session_factory` (pytest-asyncio auto mode — no decorator).
- Imports: already in place at the top of the file (`StagedOpLifecycleError`, `StagedOpRepo`, `EventRepo`, `pytest`, `uuid`).
- Shape: `async with session_factory() as session:` → `with pytest.raises(...) as exc_info:` → assert on `exc_info.value.from_status`.
- New invariant per CONTEXT D-06: assert against the literal `"(missing)"` explicitly (e.g., `assert exc_info.value.from_status != "(missing)"`) so the regression intent is unambiguous and named in the test source.
- See RESEARCH.md Code Example 3 for the canonical block (covers BOTH unknown-UUID and illegal-transition paths in one test method).

**Imports already available** (`tests/test_staged_operations.py:22-33`):
```python
import uuid

import pytest
from sqlalchemy import select, text

from forge_bridge.core.staged import StagedOperation
from forge_bridge.store import (
    EventRepo,
    StagedOpLifecycleError,
    StagedOpRepo,
)
from forge_bridge.store.models import DBEntity, DBEvent, DBProject
```

---

### `tests/test_staged_operations.py` — POLISH-03 atomicity rewrite

**Analog:** the function body's own first 14 lines (`tests/test_staged_operations.py:329-347`) — already uses the correct `propose+commit+approve+flush+rollback` pattern. The rewrite drops the broken assertion-block tail (lines 348-398) and consolidates into a single observation block per CONTEXT D-08.

**Current body to replace** (`tests/test_staged_operations.py:323-398`):
- Lines 329-337: first `async with session_factory()` block — propose, commit, save `op_id`. **KEEP the intent**, fold into single block per D-08.
- Lines 342-347: second `async with session_factory()` block — approve, flush, rollback. **KEEP the intent**, fold into single block per D-08.
- Lines 351-360: third `async with session_factory()` block — `assert True  # placeholder` at line 360 (CONTEXT said 363 — RESEARCH.md Pitfall #2 corrects this off-by-3). **DROP entirely**.
- Lines 363-398: fourth `async with session_factory()` block — `assert row is None` at line 388 contradicts SQLAlchemy/Postgres rollback semantics for a previously-committed entity. **DROP entirely; replace with corrected single-session observation per CONTEXT D-08**.

**Replacement body** — see RESEARCH.md Code Example 4 (literal block from CONTEXT D-08). Uses only existing APIs:
- `StagedOpRepo.propose(...)` — already used in the file (e.g., line 365)
- `session.commit()`, `session.flush()`, `session.rollback()` — SQLAlchemy session APIs already used
- `EventRepo(session).get_recent(entity_id=..., limit=...)` — already used in current test at line 368
- `repo.get(op.id)` — already used elsewhere (e.g., line 56)
- `repo.approve(op.id, approver=...)` — already used elsewhere (e.g., line 344)

**No new APIs required.** All imports already at the top of the file. The rewrite is a body-only edit to one function.

**RED experiment per CONTEXT D-09** — captured in PLAN-03 SUMMARY.md only, NOT committed:
- Temporarily delete `await session.rollback()` line.
- Confirm `assert len(events_after) == 1` fails with `assert 2 == 1`.
- Restore line; confirm GREEN.

---

### `tests/test_sanitize.py` — POLISH-04 count-lock bump

**Analog:** the assertion itself at `tests/test_sanitize.py:173-181`:
```python
def test_injection_markers_count_locked(self):
    """If new markers are added, they MUST be added to _sanitize_patterns.py
    (the single source of truth), not to a fork in learning/sanitize.py."""
    from forge_bridge._sanitize_patterns import INJECTION_MARKERS
    assert len(INJECTION_MARKERS) == 8, (
        f"INJECTION_MARKERS currently has {len(INJECTION_MARKERS)} entries; "
        "if you intentionally added a new marker, update this assertion AND "
        "the shim source-of-truth comment in learning/sanitize.py."
    )
```

**Pattern to apply:** change `== 8` to `== 10` at line 177. No other text change needed. RESEARCH.md Pitfall #1 flags that this edit is in-scope for P-04 even though CONTEXT.md doesn't mention it.

---

### `tests/llm/test_ollama_adapter.py` — POLISH-01 new test method

**Analog:** `TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_salvaged` at `tests/llm/test_ollama_adapter.py:298-329`:
```python
@pytest.mark.asyncio
async def test_text_content_tool_call_salvaged(self):
    """qwen2.5-coder:32b emits {"name": ..., "arguments": ...} as text
    with empty structured tool_calls. The salvage path must produce a
    non-empty _ToolCall list so router.py:435 keeps iterating instead
    of terminating with the JSON-text as terminal content (Bug D).
    """
    client = MagicMock()
    client.chat = AsyncMock(return_value=_fake_response_dict(
        content=_OLLAMA_BUG_D_RESPONSE_CONTENT,
        tool_calls=None,  # Bug D shape: structured field empty
    ))
    adapter = OllamaToolAdapter(client, "qwen2.5-coder:32b")
    state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
    resp = await adapter.send_turn(state)

    # Core fix: non-empty tool_calls keeps router.py:435 iterating.
    assert len(resp.tool_calls) >= 1, ...
    # Tool name + args extracted from the salvaged JSON.
    assert resp.tool_calls[0].tool_name == "forge_tools_read"
    assert resp.tool_calls[0].arguments == {"name": "synthesis-tools"}
```

**Pattern to apply** (per CONTEXT D-04 + RESEARCH.md Open Question #1 recommendation):
- Add a new test method to the SAME class (`TestOllamaToolAdapterBugDFallback`).
- Use the `_fake_response_dict` helper at lines 55-65 (already in scope).
- Use `MagicMock()` + `client.chat = AsyncMock(return_value=...)` mock pattern.
- Use `OllamaToolAdapter(client, "qwen2.5-coder:32b")` + `adapter.init_state(...)` + `adapter.send_turn(state)` invocation chain.
- New assertion: `assert resp.tool_calls[0].ref == "0:forge_tools_read"` (current empirical behavior — POLISH-01 derives the same string via `f"{len(tool_calls)}:{salvaged.tool_name}"` since `tool_calls` is empty when salvage runs).
- Test name suggestion: `test_text_content_tool_call_salvaged_ref_derived_from_position` or `test_salvaged_tool_call_ref_uses_index_zero_when_first_call`.

**Mock helpers already in scope** (`tests/llm/test_ollama_adapter.py:48-65`):
```python
class _FakeTool:
    def __init__(self, name: str, description: str, input_schema: dict):
        ...

def _fake_response_dict(content: str = "", tool_calls: list | None = None,
                       prompt_eval_count: int = 0, eval_count: int = 0) -> dict:
    msg: dict = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "message": msg,
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
        "done": True,
    }
```

---

### `tests/llm/test_ollama_adapter.py` — POLISH-04 new test class

**Analog (mock pattern):** same `_fake_response_dict` + `AsyncMock(return_value=...)` template documented above.

**Analog (assertion style):** `tests/test_sanitize.py:61-62` — chat-template token recognition style:
```python
def test_sanitize_rejects_im_start(self):
    assert _sanitize_tag("<|im_start|>user") is None
```
*Mirror this concise-assertion shape: the test name embeds the token, the body asserts a single observable outcome.*

**Synthetic fixture source** (per CONTEXT D-14 + RESEARCH.md Pitfall #5):
- `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md:101-107` — verbatim noise-tail evidence from fresh-operator UAT.
- Captured JSON fixture (`16.2-CAPTURED-OLLAMA-RESPONSE.json`) does NOT contain the noise tail (verified by RESEARCH.md grep). Use the HUMAN-UAT prose+token text as the synthetic fixture.

**Pattern to apply** (per CONTEXT D-14):
- Add a NEW test class `TestOllamaToolAdapterChatTemplateTailStrip` to the same file.
- Class-level constant `NOISE_TAIL_PROSE` mirrors `_OLLAMA_BUG_D_RESPONSE_CONTENT` at line 40 (module-scope captured fixture pattern).
- Two test methods:
  1. `test_terminal_chat_template_tokens_stripped` — feeds noise-tail prose; asserts `resp.text` ends with "please specify." and `"<|im_start|>" not in resp.text`.
  2. `test_clean_prose_passes_through_unchanged` — feeds clean prose; asserts `resp.text == clean_input`.
- Both use the same `MagicMock + AsyncMock + adapter.init_state + adapter.send_turn` chain as POLISH-01's analog test.

See RESEARCH.md Code Example 6 for the canonical class skeleton.

---

## Shared Patterns

### Captured-fixture-grounded RED test (Phase 16.2 precedent)
**Source:** `tests/llm/test_ollama_adapter.py:30-40` (module-scope `_OLLAMA_BUG_D_RESPONSE_CONTENT` constant with provenance comment).
**Apply to:** POLISH-04 test class — declare `NOISE_TAIL_PROSE` as a class-level constant with a docstring citing `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md:106-107` as the synthetic-fixture source.
```python
# Source: tests/llm/test_ollama_adapter.py:30-40
# Captured 2026-04-27 from assist-01 reproducing Bug D against
# qwen2.5-coder:32b on Ollama 0.21.0. The model emits the tool call as
# JSON-shaped text in message.content instead of in the structured
# tool_calls field — see Phase 16.2 D-03 + D-04. Operator-readable
# artifact with full capture metadata lives at:
#   .planning/phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json
# Prompt: "what synthesis tools were created this week?"
_OLLAMA_BUG_D_RESPONSE_CONTENT = '{"name": "forge_tools_read", "arguments": {"name": "synthesis-tools"}}'
```

### Pytest-asyncio auto mode (no decorator on top-level async tests)
**Source:** `tests/test_staged_operations.py:17` (module-level docstring) + `pyproject.toml` (`asyncio_mode = "auto"`).
**Apply to:** POLISH-02 new regression test, POLISH-03 atomicity rewrite. NO `@pytest.mark.asyncio` decorator on top-level functions in `tests/test_staged_operations.py`.
**Caveat:** `tests/llm/test_ollama_adapter.py` DOES use `@pytest.mark.asyncio` on class methods (e.g., line 298). Mirror the surrounding file's existing convention — for class-method async tests, keep the decorator.

### Module-scope precompiled regex with typed annotation
**Source:** `forge_bridge/_sanitize_patterns.py:30-31`:
```python
# Control characters: \x00-\x1f plus \x7f (DEL)
_CONTROL_CHAR_RE: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")
```
**Apply to:** POLISH-04 `_CHAT_TEMPLATE_TAIL_RE` in `_adapters.py`. Use the same `re.Pattern[str]` annotation and a one-line context comment.

### Helper colocation with consumer (FB-C D-09)
**Source:** `forge_bridge/_sanitize_patterns.py:1-12` (module docstring spelling out the convention) + `forge_bridge/llm/_adapters.py:122-209` (`_try_parse_text_tool_call` example).
**Apply to:** POLISH-04 — `_strip_terminal_chat_template_tokens` lives in `_adapters.py`, NOT `_sanitize_patterns.py`. The shared module hosts patterns; consumers host helpers.

### Single-session atomicity observation (SQLAlchemy semantics)
**Source:** RESEARCH.md Code Example 4 (CONTEXT D-08 verbatim block) — derived from existing repo + session_factory usage at `tests/test_staged_operations.py:42-56` (round-trip test) and `:344-379` (current atomicity test's correct-but-incomplete first half).
**Apply to:** POLISH-03 atomicity test rewrite. Single `async with session_factory() as session:` block; observe pre-rollback (flush) and post-rollback states without crossing session boundaries.

---

## No Analog Found

| File | Reason |
|------|--------|
| (none) | Every Phase 19 edit has an in-tree analog. POLISH-04's tail-strip helper is the closest thing to "no exact analog," but the regex template at `_sanitize_patterns.py:31` and the colocated-private-helper template at `_adapters.py:122-209` together fully cover the shape. |

---

## Metadata

**Analog search scope:**
- `forge_bridge/llm/_adapters.py` (full file)
- `forge_bridge/_sanitize_patterns.py` (full file)
- `forge_bridge/store/staged_operations.py` (lines 60-340)
- `forge_bridge/learning/execution_log.py` (`dataclasses.replace` grep result)
- `tests/test_staged_operations.py` (lines 1-660)
- `tests/test_sanitize.py` (lines 1-181)
- `tests/llm/test_ollama_adapter.py` (lines 1-433)
- `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md` (lines 95-115)

**Files scanned:** 8 source files + 1 UAT artifact

**Pattern extraction date:** 2026-04-29

**Phase:** 19-code-quality-polish

**Downstream consumer:** `gsd-planner` for Phase 19 plan generation (P-01..P-04, two waves per CONTEXT D-17).
