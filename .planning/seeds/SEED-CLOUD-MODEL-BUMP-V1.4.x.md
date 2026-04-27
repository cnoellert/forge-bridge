---
name: SEED-CLOUD-MODEL-BUMP-V1.4.x
description: Bump default cloud model claude-opus-4-6 → claude-opus-4-7 after FB-C UAT
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: A v1.4.x patch milestone opens after FB-C ships AND ANTHROPIC_API_KEY is available for live LLMTOOL-02 verification
---

# SEED-CLOUD-MODEL-BUMP-V1.4.x: Default Anthropic cloud model bump

## Idea

FB-C ships with `_DEFAULT_CLOUD_MODEL = "claude-opus-4-6"` (the v1.0 default — one minor behind current). Research §2 paragraph 2 indicates `claude-opus-4-7` matches the current "latest" examples in upstream docs. After FB-C ships and the live LLMTOOL-02 test passes against claude-opus-4-6 baseline, run the same test against claude-opus-4-7. If it matches behavior, bump the default in an ISOLATED commit (must NOT be coupled to loop-logic changes per the D-30 mandate).

## Why This Matters

- **Stay current with Anthropic's latest** — Opus 4.7 has the most-recent tool-use system prompt overhead values + strict-mode behavior validated in the FB-C research.
- **Anthropic deprecates older models** — staying on 4.6 risks API-side deprecation surfacing as a 410 mid-loop.
- **Decoupled commit pattern** — research §2 paragraph 2 explicitly says "Make this a separate, isolated commit in FB-C that touches only `_DEFAULT_*` constants — it must NOT be coupled to the loop logic." This seed enforces that boundary.

## When to Surface

- A v1.4.x patch milestone opens for polish work AFTER FB-C ships
- Anthropic announces deprecation of claude-opus-4-6 (early bump trigger)
- A v1.4 chat-endpoint operator (FB-D) reports cloud-path quality issues that may resolve with the newer model

## How to Apply

1. Set `FORGE_CLOUD_MODEL=claude-opus-4-7` and run `FB_INTEGRATION_TESTS=1 ANTHROPIC_API_KEY=... pytest tests/integration/test_complete_with_tools_live.py::test_anthropic_tool_call_loop_live`. Pass = sentinel substring in terminal response.
2. Run a representative prompt batch via the chat endpoint (Phase 16 / FB-D) and compare subjective response quality + token-usage cost vs. baseline.
3. If both pass: bump `_DEFAULT_CLOUD_MODEL = "claude-opus-4-7"` in `forge_bridge/llm/router.py` in an ISOLATED commit (the D-30 mandate).
4. Update the existing AnthropicToolAdapter tool-use system-prompt-overhead table reference in research §2.1 if upstream docs show a delta for opus-4-7 vs 4-6.
5. Update v1.4.x release notes.

## Cross-References

- FB-C CONTEXT.md D-30 — "Stay on `claude-opus-4-6` for FB-C ship. Plant `SEED-CLOUD-MODEL-BUMP-V1.4.x.md` for the `claude-opus-4-7` bump as an isolated commit after FB-C UAT."
- FB-C research §2 paragraph 2 — model-pin recommendation + isolated-commit mandate.
- forge_bridge/llm/router.py:93 — current `_DEFAULT_CLOUD_MODEL` value.
- tests/integration/test_complete_with_tools_live.py — LLMTOOL-02 verification path.
