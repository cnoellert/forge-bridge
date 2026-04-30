---
phase: 19-code-quality-polish
plan: 04
subsystem: llm
tags: [ollama, qwen2.5-coder, chat-template, sanitization, polish, regex, adapter]

requires:
  - phase: 19-01
    provides: "post-P-01 salvage block shape (`replace(salvaged, ref=f'{len(tool_calls)}:{salvaged.tool_name}')`) — the new tail-strip call is inserted directly after this block"
  - phase: 16.2
    provides: "OllamaToolAdapter.send_turn salvage path + `_try_parse_text_tool_call` helper colocation"
  - phase: 7
    provides: "INJECTION_MARKERS single-source-of-truth tuple in forge_bridge/_sanitize_patterns.py + count-lock test"
provides:
  - "`_strip_terminal_chat_template_tokens(text)` private helper in `forge_bridge/llm/_adapters.py`"
  - "`_CHAT_TEMPLATE_TAIL_TOKENS` private tuple — subset of INJECTION_MARKERS scoped to chat-template noise tail"
  - "`_CHAT_TEMPLATE_TAIL_RE` precompiled module-scope regex anchored at end-of-string"
  - "`OllamaToolAdapter.send_turn` invokes the helper after the salvage block, before `_TurnResponse` construction"
  - "INJECTION_MARKERS extended 8 → 10 (`<|im_end|>`, `<|endoftext|>`)"
  - "TestOllamaToolAdapterChatTemplateTailStrip class — 2 test methods (noise-tail strip, clean-prose passthrough)"
affects: [llm-adapters, ollama, qwen2.5-coder, chat-handler]

tech-stack:
  added: []
  patterns:
    - "Adapter-layer model-quality polish — provider-scoped strip helper colocated with consumer (FB-C D-09); subset tuple kept private to consumer"
    - "Greedy `\\Z`-anchored regex for contiguous-tail-token strip — leaves mid-content occurrences alone (sanitization concern, not strip concern)"
    - "Synthetic-fixture provenance — class docstring cites `HUMAN-UAT.md:106-107` (NOT `16.2-CAPTURED-OLLAMA-RESPONSE.json`, which lacks the tail) per RESEARCH Pitfall 5"
    - "Atomic count-lock + tuple-extension commit — both edits land together to avoid breaking `test_injection_markers_count_locked` between commits (RESEARCH Pitfall 1)"

key-files:
  created: []
  modified:
    - "forge_bridge/_sanitize_patterns.py — INJECTION_MARKERS extended 8 → 10"
    - "forge_bridge/llm/_adapters.py — `import re` added; new `_CHAT_TEMPLATE_TAIL_TOKENS`, `_CHAT_TEMPLATE_TAIL_RE`, `_strip_terminal_chat_template_tokens`; integration in `OllamaToolAdapter.send_turn`"
    - "tests/llm/test_ollama_adapter.py — new `TestOllamaToolAdapterChatTemplateTailStrip` class with two methods"
    - "tests/test_sanitize.py — count-lock assertion bumped 8 → 10 (line 177)"

key-decisions:
  - "Helper lives in `_adapters.py`, NOT in `_sanitize_patterns.py` (CONTEXT D-13 / FB-C D-09): patterns hoist to single-source-of-truth, helpers stay per-consumer"
  - "Helper uses a private `_CHAT_TEMPLATE_TAIL_TOKENS` subset (3 tokens), NOT `INJECTION_MARKERS` (10 entries): the wider tuple contains prose phrases (`ignore previous`) and bare fragments (`<|`, `|>`) that would over-strip at the tail; the two collections share intent but not membership"
  - "Strip is invoked AFTER the salvage block and BEFORE `_TurnResponse` return (CONTEXT D-15) so the salvage path sees the full original text including any noise tail"
  - "Skip `<|im_sep|>` (RESEARCH Open Q #2): no UAT evidence; keeps the 8 → 10 count bump auditable"
  - "Provider-scoped to OllamaToolAdapter (CONTEXT D-11): Anthropic adapter untouched, so any provider-specific quirks surface as bugs rather than being silently masked"
  - "All four edits land in ONE atomic commit (RESEARCH Pitfall 1): the count-lock test breaks immediately if the tuple extension and assertion bump are split across commits"

patterns-established:
  - "Pattern 1: Adapter-layer tail-strip — module-scope precompiled regex `(?:tok1|tok2|tok3|\\s)+\\Z` consumes contiguous tail token-runs; mid-content occurrences pass through"
  - "Pattern 2: Atomic count-lock + extension — when a count-locked tuple grows, the assertion must change in the same commit (CI breaks otherwise)"
  - "Pattern 3: Synthetic-fixture provenance citation — class docstring records the canonical UAT artifact source line range so future readers can audit fidelity"

requirements-completed: [POLISH-04]

duration: ~12min
completed: 2026-04-30
---

# Phase 19 Plan 04: POLISH-04 — qwen2.5-coder chat-template tail-token strip Summary

**Provider-scoped tail-token strip in OllamaToolAdapter removes contiguous `<|im_start|>` / `<|im_end|>` / `<|endoftext|>` runs at the end of `_TurnResponse.text`, recovering clean prose for the chat surface while leaving mid-content occurrences and other adapters untouched.**

## Performance

- **Duration:** ~12 min (worktree base reset overhead + index-lock recovery factored out: net edits + tests ~7 min)
- **Started:** 2026-04-30T11:24:00Z (approx, post-init)
- **Completed:** 2026-04-30T11:36:25Z
- **Tasks:** 3 (all in single atomic commit per plan mandate)
- **Files modified:** 4

## Accomplishments

- Closed POLISH-04 — qwen2.5-coder noise tail (HUMAN-UAT.md:106-107) is stripped at adapter layer; T-19-04 disposition `mitigate` realized in code with regression tests.
- INJECTION_MARKERS single-source-of-truth tuple aligned with the new tokens (now 10 entries — adds `<|im_end|>` and `<|endoftext|>`); count-lock kept atomic with the extension.
- New `TestOllamaToolAdapterChatTemplateTailStrip` class pins both behaviors: noise-tail strip (positive) + clean-prose passthrough (negative). Synthetic fixture cites the canonical UAT artifact in the class docstring.

## Task Commits

All four edits across the three tasks land in ONE atomic commit per the plan's `<success_criteria>` mandate (RESEARCH Pitfall 1):

1. **Tasks 1+2+3 atomic:** `1b4e525` — `feat(19-04): close POLISH-04 — qwen2.5-coder chat-template tail-token strip`

_(No metadata commit yet — that commit will be added with this SUMMARY.md.)_

## Files Created/Modified

- `forge_bridge/_sanitize_patterns.py` — INJECTION_MARKERS tuple grew 8 → 10 (`<|im_end|>` + `<|endoftext|>`).
- `forge_bridge/llm/_adapters.py` — added `import re`; new POLISH-04 section after `_try_parse_text_tool_call` containing `_CHAT_TEMPLATE_TAIL_TOKENS` tuple, `_CHAT_TEMPLATE_TAIL_RE` precompiled regex, and `_strip_terminal_chat_template_tokens` helper. Integration: one new line + comment in `OllamaToolAdapter.send_turn` after the salvage block, before `_TurnResponse(text=text, ...)` return.
- `tests/llm/test_ollama_adapter.py` — appended `TestOllamaToolAdapterChatTemplateTailStrip` class (2 test methods + class-level `NOISE_TAIL_PROSE` fixture).
- `tests/test_sanitize.py` — line 177 assertion bumped `len(INJECTION_MARKERS) == 8` → `== 10` (assertion message text unchanged — interpolates the new count correctly).

## Verbatim Diff Applied

Four hunks across four files (matches plan's `<success_criteria>` exactly):

```diff
diff --git a/forge_bridge/_sanitize_patterns.py b/forge_bridge/_sanitize_patterns.py
@@ -25,6 +25,8 @@ INJECTION_MARKERS: tuple[str, ...] = (
     "<|im_start|>",
     "```",  # triple backtick — markdown code fence
     "---",  # yaml document separator
+    "<|im_end|>",     # qwen chat template — terminal token (POLISH-04)
+    "<|endoftext|>",  # qwen chat template — sequence terminator (POLISH-04)
 )
```

```diff
diff --git a/forge_bridge/llm/_adapters.py b/forge_bridge/llm/_adapters.py
@@ -25,6 +25,7 @@ from __future__ import annotations
 import json
 import logging
+import re
 from dataclasses import dataclass, replace

@@ -209,6 +210,47 @@ def _try_parse_text_tool_call(text: str) -> Optional[_ToolCall]:
     )


+# ---------------------------------------------------------------------------
+# POLISH-04: terminal chat-template token strip (qwen2.5-coder noise tail)
+# ---------------------------------------------------------------------------
+
+
+_CHAT_TEMPLATE_TAIL_TOKENS: tuple[str, ...] = (
+    "<|im_start|>",
+    "<|im_end|>",
+    "<|endoftext|>",
+)
+
+_CHAT_TEMPLATE_TAIL_RE: re.Pattern[str] = re.compile(
+    r"(?:" + "|".join(re.escape(t) for t in _CHAT_TEMPLATE_TAIL_TOKENS) + r"|\s)+\Z"
+)
+
+
+def _strip_terminal_chat_template_tokens(text: str) -> str:
+    """Strip a contiguous tail-run of chat-template special tokens from `text`. ..."""
+    if not text:
+        return text
+    return _CHAT_TEMPLATE_TAIL_RE.sub("", text)
+
+
@@ -550,6 +592,11 @@ class OllamaToolAdapter:
                 tool_calls.append(salvaged)
                 text = ""  # consumed — don't double-emit as terminal content (re-Bug-D risk)

+        # POLISH-04: strip qwen2.5-coder chat-template noise tail (HUMAN-UAT.md:106-107).
+        # Runs AFTER salvage so the salvage path sees the full original text; if
+        # salvage emitted a tool call, `text` is already "" and this is a no-op.
+        text = _strip_terminal_chat_template_tokens(text)
+
         if isinstance(response, dict):
             prompt_tokens = response.get("prompt_eval_count", 0) or 0
```

```diff
diff --git a/tests/llm/test_ollama_adapter.py b/tests/llm/test_ollama_adapter.py
@@ -467,3 +467,84 @@ class TestOllamaToolAdapterBugDFallback:
+
+# ---------------------------------------------------------------------------
+# POLISH-04 — qwen2.5-coder chat-template tail-token strip (Phase 19)
+# ---------------------------------------------------------------------------
+
+
+class TestOllamaToolAdapterChatTemplateTailStrip:
+    """POLISH-04: ... see 16.2-HUMAN-UAT.md:106-107 ..."""
+
+    NOISE_TAIL_PROSE = (
+        "It seems there are no synthesis tools registered this week. ... please specify.\n"
+        "<|im_start|><|im_start|>\n"
+        "<|im_start|><|im_start|>"
+    )
+
+    @pytest.mark.asyncio
+    async def test_terminal_chat_template_tokens_stripped(self):
+        ...
+
+    @pytest.mark.asyncio
+    async def test_clean_prose_passes_through_unchanged(self):
+        ...
```

```diff
diff --git a/tests/test_sanitize.py b/tests/test_sanitize.py
@@ -174,7 +174,7 @@ class TestSanitizePatternsShim:
-        assert len(INJECTION_MARKERS) == 8, (
+        assert len(INJECTION_MARKERS) == 10, (
             f"INJECTION_MARKERS currently has {len(INJECTION_MARKERS)} entries; "
```

## Pytest Output

```text
$ pytest -v tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterChatTemplateTailStrip
collected 2 items

tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterChatTemplateTailStrip::test_terminal_chat_template_tokens_stripped PASSED [ 50%]
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterChatTemplateTailStrip::test_clean_prose_passes_through_unchanged PASSED [100%]

========================= 2 passed, 1 warning in 0.02s =========================
```

```text
$ pytest -v tests/test_sanitize.py::TestSanitizePatternsShim::test_injection_markers_count_locked
collected 1 item

tests/test_sanitize.py::TestSanitizePatternsShim::test_injection_markers_count_locked PASSED [100%]

========================= 1 passed, 1 warning in 0.02s =========================
```

```text
$ pytest -v tests/llm/test_ollama_adapter.py tests/test_sanitize.py
======================== 52 passed, 1 warning in 0.04s =========================
```

(All 21 ollama-adapter tests including Wave 1's `test_salvaged_tool_call_ref_uses_index_zero_when_first_call` + 29 sanitize tests + 2 new POLISH-04 tests = 52 green.)

## Smoke-Test Output

Behavioral checks for `_strip_terminal_chat_template_tokens` (token tail strip, clean passthrough, empty short-circuit, mid-content unchanged):

```text
$ python -c "from forge_bridge.llm._adapters import _strip_terminal_chat_template_tokens
assert _strip_terminal_chat_template_tokens('hello <|im_start|>') == 'hello'
assert _strip_terminal_chat_template_tokens('hello') == 'hello'
assert _strip_terminal_chat_template_tokens('') == ''
got = _strip_terminal_chat_template_tokens('hello\n<|im_start|><|im_start|>\n<|im_start|><|im_start|>')
assert got == 'hello', repr(got)
assert _strip_terminal_chat_template_tokens('<|im_start|>mid prose') == '<|im_start|>mid prose'
print('OK')"
OK
```

INJECTION_MARKERS extension verification:

```text
$ python -c "from forge_bridge._sanitize_patterns import INJECTION_MARKERS
assert len(INJECTION_MARKERS) == 10
assert '<|im_end|>' in INJECTION_MARKERS
assert '<|endoftext|>' in INJECTION_MARKERS
assert '<|im_sep|>' not in INJECTION_MARKERS
print('OK')"
OK
```

## Synthetic-Fixture Provenance Citation

Per RESEARCH Pitfall 5, the `NOISE_TAIL_PROSE` fixture in `TestOllamaToolAdapterChatTemplateTailStrip` mirrors the verbatim noise tail captured during Phase 16.2 fresh-operator UAT — see:

- **Canonical source:** `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md:106-107`
- **NOT the captured JSON:** `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json` does NOT contain the noise tail (the JSON capture pre-dates the noise-tail emission); HUMAN-UAT is the authoritative artifact.

The class docstring records this provenance so future readers can audit fidelity.

The embedded second-tool-call JSON `{"name": "forge_list_staged", "arguments": {"status": "proposed"}}` from HUMAN-UAT.md:107 is intentionally OMITTED from the fixture per CONTEXT D-15 + RESEARCH Example 5: that JSON would survive the strip (helper consumes the contiguous tail-token run, not embedded JSON) and is a separate model-quality artifact orthogonal to the tail-token strip.

## Decisions Made

See frontmatter `key-decisions`. Summary:

1. Helper colocated in `_adapters.py`, NOT in `_sanitize_patterns.py` — patterns hoist, helpers stay per-consumer (FB-C D-09).
2. Private `_CHAT_TEMPLATE_TAIL_TOKENS` subset (3 tokens) used by the helper, NOT `INJECTION_MARKERS` (10 entries) — wider tuple contains prose / bare fragments that would over-strip at the tail.
3. Strip invoked AFTER salvage block, BEFORE `_TurnResponse` return — salvage path sees full original text.
4. Skip `<|im_sep|>` (no UAT evidence) — keeps 8 → 10 count bump auditable.
5. Provider-scoped to OllamaToolAdapter — Anthropic untouched, surfacing future quirks rather than masking them.
6. ALL four edits in ONE atomic commit — count-lock test breaks if split.

## Deviations from Plan

None — plan executed exactly as written.

The only out-of-band action during execution was a stale `index.lock` cleanup at `/Users/cnoellert/Documents/GitHub/forge-bridge/.git/worktrees/agent-ac83c4c802dafe09e/index.lock` (left by a prior worktree-init step before the executor was spawned), which had emptied the index and made `git status` report the entire tree as deleted. Removed the stale lock and ran `git read-tree HEAD` to rebuild the index. No source files or commits affected — this was strictly index-state recovery before any add/commit. Documenting here for transparency; not a code-deviation.

## Auth Gates

None — purely local code edits and unit tests; no external API/auth involved.

## Threat Flags

None — POLISH-04 is the explicit mitigation for T-19-04 (Information Disclosure) declared in the plan's `<threat_model>`, not a new surface. The strip removes contiguous chat-template noise; mid-content occurrences are intentionally untouched (sanitization concern handled by `_sanitize_tool_result()` per FB-C D-09). No new network, auth, file-access, or schema surface introduced.

## Known Stubs

None — all code paths are wired with real data sources (`message.content` → strip → `_TurnResponse.text`). No placeholder text, no hardcoded empty values, no TODOs introduced.

## Self-Check: PASSED

- File exists: `forge_bridge/_sanitize_patterns.py` — FOUND (modified)
- File exists: `forge_bridge/llm/_adapters.py` — FOUND (modified)
- File exists: `tests/llm/test_ollama_adapter.py` — FOUND (modified)
- File exists: `tests/test_sanitize.py` — FOUND (modified)
- Commit `1b4e525` exists in `git log --oneline` — FOUND
- New helper `_strip_terminal_chat_template_tokens` reachable via `from forge_bridge.llm._adapters import _strip_terminal_chat_template_tokens` — FOUND
- New test class `TestOllamaToolAdapterChatTemplateTailStrip` discovered by pytest — FOUND (2 tests collected, both PASSED)
- INJECTION_MARKERS length == 10 — VERIFIED
- Count-lock assertion bumped to `== 10` — VERIFIED
- Helper NOT present in `_sanitize_patterns.py` (colocation guard) — VERIFIED (no match)
