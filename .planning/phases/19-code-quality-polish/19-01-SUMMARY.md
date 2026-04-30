---
phase: 19
plan: 01
subsystem: llm-adapter
tags:
  - polish-01
  - wr-02-closure
  - tool-call-salvage
  - ref-derivation
  - threat-mitigation
dependency_graph:
  requires:
    - "Phase 16.2: _try_parse_text_tool_call helper (forge_bridge/llm/_adapters.py:122-209)"
    - "Phase 16.2: TestOllamaToolAdapterBugDFallback class (tests/llm/test_ollama_adapter.py:284)"
  provides:
    - "POLISH-01: ref derivation moved from helper literal to call-site composition"
    - "T-19-01 mitigation: composite ref discipline extended to salvage path"
    - "Regression test pinning empirical Bug D fixture ref behavior"
  affects:
    - forge_bridge/llm/_adapters.py
    - tests/llm/test_ollama_adapter.py
tech_stack:
  added:
    - "dataclasses.replace (stdlib import)"
  patterns:
    - "call-site index-derived composite ref (mirrors structured-path pattern at _adapters.py:530-534)"
    - "helper-emits-placeholder + caller-overrides (immutable update via dataclasses.replace)"
key_files:
  created: []
  modified:
    - forge_bridge/llm/_adapters.py
    - tests/llm/test_ollama_adapter.py
decisions:
  - "Helper returns `f\"salvage:{name}\"` placeholder (NOT raises, NOT returns sentinel) — call site overrides via dataclasses.replace. Keeps the helper independently testable and avoids leaking 'unfinished' state into the call-site contract."
  - "Use `dataclasses.replace` for the override (not direct `salvaged.ref = ...` mutation) — discipline-preserving even though `_ToolCall` is unfrozen. Future tightening to `frozen=True` won't require a second edit."
  - "Use `salvaged.tool_name` (not `salvaged.name`) at the call site — the `_ToolCall` dataclass field is `tool_name`; the helper-local `name` variable is not in scope at the caller. Verified at planning time as RESEARCH Open Q #3."
metrics:
  duration_min: 4
  completed: 2026-04-30T04:12:09Z
  tasks_executed: 2
  files_modified: 2
  tests_added: 1
  tests_passing_in_module: 21
  tests_passing_in_llm_suite: 96
---

# Phase 19 Plan 01: POLISH-01 Salvage Ref Derivation Summary

**One-liner:** Moved tool-call ref derivation for the Bug-D salvage path from a hardcoded `f"0:{name}"` literal inside `_try_parse_text_tool_call` to a derived composition at the salvage call site (`replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")`), mirroring the structured-path discipline at `_adapters.py:530-534` and pinning the empirical first-call ref behavior with a new regression test — closes WR-02 / threat T-19-01 with one atomic commit.

## What Changed

### Production change (forge_bridge/llm/_adapters.py)

Three hunks, all on the Ollama adapter's salvage path. Verbatim diff:

```diff
diff --git a/forge_bridge/llm/_adapters.py b/forge_bridge/llm/_adapters.py
index 8d96695..3ac2c14 100644
--- a/forge_bridge/llm/_adapters.py
+++ b/forge_bridge/llm/_adapters.py
@@ -25,7 +25,7 @@ from __future__ import annotations

 import json
 import logging
-from dataclasses import dataclass
+from dataclasses import dataclass, replace
 from typing import TYPE_CHECKING, Any, Optional, Protocol

 from forge_bridge.llm.router import LLMToolError
@@ -203,7 +203,7 @@ def _try_parse_text_tool_call(text: str) -> Optional[_ToolCall]:
     if not isinstance(args, dict):
         args = {}
     return _ToolCall(
-        ref=f"0:{name}",  # idx is always 0 — the salvage path emits one tool call per turn
+        ref=f"salvage:{name}",  # placeholder; call site overwrites with f"{idx}:{name}" (POLISH-01)
         tool_name=name,
         arguments=dict(args),
     )
@@ -543,6 +543,10 @@ class OllamaToolAdapter:
         if not tool_calls and text:
             salvaged = _try_parse_text_tool_call(text)
             if salvaged is not None:
+                # Derive ref from current tool_calls position — collision-free even if
+                # the salvage guard ever loosens. Was hardcoded "0:{name}" inside the
+                # helper (WR-02 closure / POLISH-01).
+                salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")
                 tool_calls.append(salvaged)
                 text = ""  # consumed — don't double-emit as terminal content (re-Bug-D risk)
```

### Test change (tests/llm/test_ollama_adapter.py)

One new method appended to the existing `TestOllamaToolAdapterBugDFallback` class — no new class, no new file.

```python
@pytest.mark.asyncio
async def test_salvaged_tool_call_ref_uses_index_zero_when_first_call(self):
    """POLISH-01 (WR-02 closure): the salvage path's tool-call ref is derived
    at the call site from the current `tool_calls` length, not hardcoded
    inside the helper. When salvage is the first (and only) tool call of
    the turn, the empirical ref is `"0:{tool_name}"` — pinned here so a
    future loosening of the salvage guard that emits a 2nd salvaged call
    cannot silently collide with structured-path refs.
    """
    client = MagicMock()
    client.chat = AsyncMock(return_value=_fake_response_dict(
        content=_OLLAMA_BUG_D_RESPONSE_CONTENT,
        tool_calls=None,  # Bug D shape: structured field empty, salvage runs
    ))
    adapter = OllamaToolAdapter(client, "qwen2.5-coder:32b")
    state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
    resp = await adapter.send_turn(state)

    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].ref == "0:forge_tools_read"
    assert not resp.tool_calls[0].ref.startswith("salvage:")
```

## Why

POLISH-01 closes WR-02 review-mark from Phase 16.2: the original Bug-D salvage helper baked an idx-zero literal into its return ref because the salvage path emits exactly one tool call per turn under the current guard. That invariant is structurally fragile — any future code that loosens the `if not tool_calls` guard to handle multi-tool-call salvage would silently produce ref collisions with the structured-path's `f"{idx}:{name}"` refs (T-19-01: tampering at the adapter→coordinator boundary). The fix makes the salvage path self-consistent with the structured path at `_adapters.py:530-534`: both compose the ref at the call site from the current `tool_calls` length. The helper becomes index-agnostic; collision-resistance becomes a property of the call site, not a per-helper invariant.

The placeholder `"salvage:{name}"` ref the helper now returns is intentionally weird — if it ever leaked through to a consumer (i.e., the call site forgot to override), the regression test asserts on the absence of the `"salvage:"` prefix to fail fast.

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 (atomic) | POLISH-01 production fix + regression test | `47133b0` | `forge_bridge/llm/_adapters.py`, `tests/llm/test_ollama_adapter.py` |

The plan defined Tasks 1 and 2 as separate logical units (production change + unit test) but explicitly mandated **one atomic commit** in the success criteria (`feat(19-01): close POLISH-01 — derive salvage ref at call site (WR-02 closure)`). Both tasks landed in commit `47133b0`.

## Verification

### Acceptance criteria (Task 1)

| Criterion | Result |
|-----------|--------|
| `grep -n "from dataclasses import" forge_bridge/llm/_adapters.py` returns line with `replace` | PASS — `28:from dataclasses import dataclass, replace` |
| `grep -nE 'ref=f"0:' forge_bridge/llm/_adapters.py \| grep -v '^\s*#'` returns NO matches | PASS — zero matches |
| `grep -n 'ref=f"salvage:' forge_bridge/llm/_adapters.py` returns exactly one match | PASS — `206:        ref=f"salvage:{name}",  # placeholder; call site overwrites with f"{idx}:{name}" (POLISH-01)` |
| `grep -n 'replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")' forge_bridge/llm/_adapters.py` returns exactly one match | PASS — `549:                salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")` |
| `python -c "from forge_bridge.llm import _adapters"` exits 0 | PASS — `OK` |
| `pytest TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_salvaged` exits 0 | PASS |
| `pytest TestOllamaToolAdapterBugDFallback::test_plain_text_terminal_response_not_misclassified` exits 0 | PASS |

### Acceptance criteria (Task 2)

| Criterion | Result |
|-----------|--------|
| `grep -n "test_salvaged_tool_call_ref_uses_index_zero_when_first_call"` returns exactly one match | PASS — `436:    async def test_salvaged_tool_call_ref_uses_index_zero_when_first_call(self):` |
| `grep -nE 'class TestOllamaToolAdapterBugDFallback'` STILL returns exactly one match (no new class created) | PASS — `284:class TestOllamaToolAdapterBugDFallback:` (unchanged) |
| `pytest test_salvaged_tool_call_ref_uses_index_zero_when_first_call` exits 0 with 1 passed | PASS |
| `pytest tests/llm/test_ollama_adapter.py -v` reports zero failures | PASS — 21 passed |

### Test output — TestOllamaToolAdapterBugDFallback class

```
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_salvaged PASSED
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_plain_text_terminal_response_not_misclassified PASSED
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_with_trailing_prose PASSED
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_with_leading_prose PASSED
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_in_markdown_fence PASSED
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_natural_prose_with_brace_not_misclassified PASSED
tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_salvaged_tool_call_ref_uses_index_zero_when_first_call PASSED
======================== 7 passed in 0.02s ========================
```

### Test output — full LLM suite

```
tests/llm/test_anthropic_adapter.py ..............                       [ 14%]
tests/llm/test_complete_with_tools.py ...........................        [ 42%]
tests/llm/test_ollama_adapter.py .....................                   [ 64%]
tests/llm/test_recursive_guard.py ..........                             [ 75%]
tests/llm/test_sanitize_tool_result.py ........................          [100%]
======================== 96 passed, 1 warning in 1.23s ========================
```

### Grep-guard outputs (POLISH-01 acceptance, post-commit)

```
=== POLISH-01 grep guard 1: literal '0:' removed from non-comment lines ===
ZERO matches (PASS)

=== POLISH-01 grep guard 2: salvage placeholder present ===
206:        ref=f"salvage:{name}",  # placeholder; call site overwrites with f"{idx}:{name}" (POLISH-01)

=== POLISH-01 grep guard 3: call-site override present ===
549:                salvaged = replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")

=== POLISH-01 grep guard 4: replace imported ===
28:from dataclasses import dataclass, replace

=== POLISH-01 grep guard 5: import does not raise ===
OK

=== POLISH-01 grep guard 6: regression test added ===
436:    async def test_salvaged_tool_call_ref_uses_index_zero_when_first_call(self):
```

## Threat Model — T-19-01 Disposition

T-19-01 (Tampering: ref-collision-via-loosened-guard between salvage path and structured path → coordinator dispatches the wrong tool action) is now mitigated. The salvage path emits a placeholder ref the call site unconditionally overrides with `f"{len(tool_calls)}:{salvaged.tool_name}"`. Even if a future refactor loosens the `if not tool_calls` guard to allow multi-tool-call salvage, the second salvaged call would receive `ref="1:..."`, the third `"2:..."`, etc. — guaranteed disjoint from any pre-existing structured-path ref because both paths share the same `len(tool_calls)`-indexed namespace.

The new regression test pins the empirical first-call ref to `"0:forge_tools_read"` so any drift from the discipline (e.g., a refactor that accidentally hardcoded the literal back into the helper, or a refactor that forgot to override at the call site, leaving the `"salvage:"` placeholder leaked through) flips the test red.

## Deviations from Plan

None — plan executed exactly as written. The plan's `<verification>` and acceptance criteria all pass on the first run. No Rule 1/2/3 fixes needed; no Rule 4 architectural decisions surfaced.

The only execution-environment friction was unrelated to plan content: this conda env has `pytest-blender` installed globally as a pytest plugin, which auto-loads on every pytest invocation and aborts when the `blender` executable is not on PATH. Worked around with `-p no:pytest_blender` (no plan-level deviation; this is a system-environment issue not specific to the plan).

## Authentication Gates

None.

## Known Stubs

None — no new placeholder values introduced. The `f"salvage:{name}"` placeholder ref returned by the helper is overwritten by the call site before any consumer ever observes it, and the regression test asserts the placeholder never leaks through.

## Threat Flags

None — no new security-relevant surface introduced. The change is a refactor of an existing trust boundary (LLM provider → adapter → coordinator) that strengthens the existing T-19-01 mitigation.

## TDD Gate Compliance

The plan declared `tdd="true"` on both tasks but the success criteria explicitly mandated **one atomic commit** for production change + regression test combined (rather than the canonical RED-then-GREEN two-commit cycle). This is the plan-level intentional override of the per-task TDD gate sequence — captured here for the record. Both the production change and the test landed in commit `47133b0`. Pre-commit verification on the production change (Task 1 acceptance criteria) ran via the existing 6 Bug-D regression tests, all green; the new test (Task 2) ran post-edit and passed; the atomic commit then captured both edits together.

## Self-Check: PASSED

- File `forge_bridge/llm/_adapters.py`: FOUND, modified at line 28 (import), line 206 (helper return), lines 543-549 (salvage call site).
- File `tests/llm/test_ollama_adapter.py`: FOUND, new test method at line 436 inside existing `TestOllamaToolAdapterBugDFallback` class at line 284.
- Commit `47133b0`: FOUND (`git log --oneline -3` confirms).
- Plan SUMMARY.md: written (this file).

Atomic commit `47133b0` lands both production change + regression test as required by the plan's `<success_criteria>`. POLISH-01 closed; WR-02 closure recorded.
