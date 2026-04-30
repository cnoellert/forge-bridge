---
phase: 19-code-quality-polish
reviewed: 2026-04-30T11:41:28Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - forge_bridge/_sanitize_patterns.py
  - forge_bridge/llm/_adapters.py
  - forge_bridge/store/staged_operations.py
  - tests/llm/test_ollama_adapter.py
  - tests/test_sanitize.py
  - tests/test_staged_operations.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-04-30T11:41:28Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found (info-only; no blockers)

## Summary

Phase 19 closes four surgical polish items (POLISH-01..04) carried over from
v1.4 close-out review artifacts. All four touch a single concern each and the
diffs are appropriately small. The implementation is consistent with the
plan-level decisions in `19-CONTEXT.md` (D-02..D-15) and the patterns in
`docs/VOCABULARY.md` / `CLAUDE.md`.

Correctness assessment:

- **POLISH-01** (`_adapters.py` salvage ref) — correct. The helper returns
  `ref="salvage:{name}"` as a benign placeholder and the call site overrides
  via `dataclasses.replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")`
  before `tool_calls.append`. The literal `"0:"` prefix no longer appears
  inside the helper. Test `test_salvaged_tool_call_ref_uses_index_zero_when_first_call`
  pins the empirical `"0:forge_tools_read"` ref AND asserts the
  `"salvage:"` placeholder does not leak through.
- **POLISH-02** (`staged_operations.py:325-330` comment refresh + regression
  test) — correct. Production code already passed `from_status=None`; only
  the historical comment was misleading. New regression test
  `test_lifecycle_error_from_status_is_optional_str_never_missing_sentinel`
  reconstructs the legacy sentinel `"(missing)"` at runtime via
  `"(" + "missing" + ")"` so a static grep stays at zero matches in `tests/`
  while the assertions remain byte-equivalent — this is an unusually
  thoughtful guard against the grep-based POLISH-02 acceptance check.
- **POLISH-03** (`test_transition_atomicity` rewrite) — correct. Replaces the
  `assert True  # placeholder` and the contradictory `assert row is None`
  block with a single-session observation: commit a baseline (1 entity + 1
  event), approve+flush in the same session (2 events visible), rollback,
  observe that only the originally-committed proposed event survives. This
  matches Postgres/SQLAlchemy semantics correctly: the pre-rollback `commit()`
  draws a savepoint boundary that the rollback respects.
- **POLISH-04** (qwen2.5-coder tail-token strip) — correct for documented
  scenarios. The regex `(?:<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|\s)+\Z`
  anchored at end-of-string strips a contiguous tail run; mid-content
  occurrences are intentionally left for `_sanitize_tool_result()` per FB-C
  D-09 layering. `INJECTION_MARKERS` extension to 10 entries propagates to
  both consumers (`forge_bridge.llm._sanitize._INJECTION_RE` rebuilt at
  module-load time; `forge_bridge.learning.sanitize._sanitize_tag` iterates
  the tuple). Both consumers were verified against the new count.

Security assessment:

- No untrusted input enters production code without sanitization. All polish
  changes operate on LLM-generated content, which is bounded by Ollama's
  max-tokens setting (~8KB typical for the deployed qwen models).
- The new `_CHAT_TEMPLATE_TAIL_RE` has a theoretical quadratic-backtracking
  worst case on adversarial inputs (see IN-01 below), but realistic
  LLM-output sizes show <20ms runtime — well within budget. Flagged as Info
  rather than Warning because the path is operator-controlled (Ollama only,
  no external/multi-tenant exposure).
- No hardcoded secrets, no unsafe deserialization (`json.JSONDecoder().raw_decode`
  remains the entry point for salvage JSON parsing; behavior unchanged from
  the pre-Phase-19 code), no shell/SQL injection paths touched.

Maintainability assessment:

- All four diffs honor the project conventions: docstrings cite the originating
  decision (D-XX), historical context (Phase 16.2 D-03/D-04, v1.4 LLMTOOL-01,
  WR-01/WR-02), and file:line cross-references. This is consistent with the
  documented project style in `CLAUDE.md`.
- The `_CHAT_TEMPLATE_TAIL_TOKENS` tuple in `_adapters.py` is intentionally a
  separate constant from `INJECTION_MARKERS` per D-13 ("helpers are NOT
  centralized — each consumer owns its own rejection semantics"). This is
  defensible but introduces a small drift risk (see IN-02).
- The use of `dataclasses.replace` on the mutable `_ToolCall` dataclass is
  stylistically slightly heavyweight (see IN-03) but not incorrect.

No critical or warning-level issues were identified.

## Info

### IN-01: Quadratic-backtracking worst-case on `_CHAT_TEMPLATE_TAIL_RE` for adversarial inputs

**File:** `forge_bridge/llm/_adapters.py:233-235`

**Issue:** The regex
`(?:<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|\s)+\Z` is anchored to end-of-
string with `\Z`, but Python's `re` engine still backtracks across the entire
input on a non-match. Empirically:

- Realistic input (500 leading tokens + 10K text suffix): ~18ms
- Adversarial input (5000 alternating `<|im_start|> ` + non-token suffix):
  ~1430ms

The path is reachable from any Ollama response content, but Ollama responses
are bounded by `num_predict` / `max_tokens` (~8KB typical for the deployed
qwen3:32b / qwen2.5-coder:32b models), so realistic exposure is well under
20ms. There is no external/multi-tenant attacker who can craft worst-case
inputs — the LLM is the only source.

**Fix:** No change required for v1.4.x; if a future ReDoS hardening pass is
done across the codebase, two practical mitigations are available:

1. **Right-to-left scan** (preferred — preserves regex shape):
   ```python
   def _strip_terminal_chat_template_tokens(text: str) -> str:
       if not text:
           return text
       i = len(text)
       # Walk backward from end-of-string until we hit a non-token, non-whitespace char.
       while i > 0:
           if text[i - 1].isspace():
               i -= 1
               continue
           matched = False
           for tok in _CHAT_TEMPLATE_TAIL_TOKENS:
               if text.endswith(tok, 0, i):
                   i -= len(tok)
                   matched = True
                   break
           if not matched:
               break
       return text[:i]
   ```

2. **Anchor at start of tail by reversing search**: scan for the first
   non-token-non-whitespace from the right via `re.search` on a reversed
   alternation — equivalent linear bound.

Documenting this as Info per the v1 review scope's "performance issues
out of scope unless also correctness issues" rule. Recommend adding a
comment near the regex citing the empirical 18ms realistic bound and the
1.4s adversarial bound so a future maintainer doesn't accidentally feed
the helper unbounded operator input without re-evaluating.

### IN-02: Token list duplication between `INJECTION_MARKERS` and `_CHAT_TEMPLATE_TAIL_TOKENS`

**File:** `forge_bridge/llm/_adapters.py:224-228` (vs `forge_bridge/_sanitize_patterns.py:19-30`)

**Issue:** Three qwen chat-template tokens (`<|im_start|>`, `<|im_end|>`,
`<|endoftext|>`) now appear in two places:

- `forge_bridge/_sanitize_patterns.INJECTION_MARKERS` (10 entries, including
  the 3 qwen tokens for inline-replacement / tag-rejection).
- `forge_bridge/llm/_adapters._CHAT_TEMPLATE_TAIL_TOKENS` (3 entries, used to
  build the tail-strip regex).

This duplication is INTENTIONAL per the Phase 19 plan (D-13: "helpers are NOT
centralized — each consumer owns its own rejection semantics") and the
`_sanitize_patterns.py` module docstring explicitly limits itself to shared
patterns rather than consumer-specific helpers.

The drift risk is real but bounded: if a future operator adds e.g.
`<|im_sep|>` to `INJECTION_MARKERS` (because it appears mid-content in a
prompt-injection capture), the tail-strip helper will silently miss it. The
inverse is also possible — a new tail-only token added to
`_CHAT_TEMPLATE_TAIL_TOKENS` won't be rejected by `_sanitize_tag()`.

**Fix:** Optional. If you want to seal the drift now without violating D-13
(helpers stay separate), add a mechanical link:

```python
# forge_bridge/llm/_adapters.py
from forge_bridge._sanitize_patterns import INJECTION_MARKERS

# Tail-strip subset: only the qwen chat-template tokens, derived from the
# canonical INJECTION_MARKERS source. If a future operator adds another
# chat-template token to INJECTION_MARKERS, add it to this filter as well.
_CHAT_TEMPLATE_TAIL_TOKENS: tuple[str, ...] = tuple(
    m for m in INJECTION_MARKERS
    if m.startswith("<|") and m.endswith("|>")
)
```

This keeps D-13's two-helper separation while collapsing the source of
truth. Acceptable to defer to v1.5; flag a TODO if punting.

### IN-03: `dataclasses.replace` on a mutable dataclass is heavier than necessary

**File:** `forge_bridge/llm/_adapters.py:591`

**Issue:** `_ToolCall` is declared `@dataclass` (line 86, NOT frozen), so
mutation is permitted. The new salvage call site uses
`dataclasses.replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")`
which constructs a NEW `_ToolCall` instance and rebinds `salvaged`. A direct
attribute assignment would be one allocation cheaper:

```python
salvaged.ref = f"{len(tool_calls)}:{salvaged.tool_name}"
```

The current form is defensible (it's idiomatic, works regardless of frozen
status, and explicitly signals "this is a derived value, not a hot-path
mutation"). It also matches `ToolCallResult` (which IS frozen) for
consistency. No functional issue.

**Fix:** Leave as-is unless `_ToolCall` is later frozen for thread-safety
reasons (in which case `replace()` becomes mandatory and this Info note
becomes a "good — future-proofed" note). If you do choose to simplify:

```python
if not tool_calls and text:
    salvaged = _try_parse_text_tool_call(text)
    if salvaged is not None:
        salvaged.ref = f"{len(tool_calls)}:{salvaged.tool_name}"
        tool_calls.append(salvaged)
        text = ""
```

Then drop the `replace` import from line 29.

---

_Reviewed: 2026-04-30T11:41:28Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
