---
name: SEED-OPUS-4-7-TEMPERATURE-V1.5
description: AnthropicAdapter must elide `temperature` for claude-opus-4-7 before any opus-4-7 default bump becomes viable
type: forward-looking-idea
planted_during: v1.4.x Phase 17 P-02 (MODEL-01 cloud bump, 2026-04-28)
trigger_when: A v1.5 cloud-model bump consideration (claude-opus-4-7 or successor) AND/OR Anthropic deprecation of claude-sonnet-4-6
---

# SEED-OPUS-4-7-TEMPERATURE-V1.5: Per-model `temperature` elision in AnthropicAdapter

## Idea

`claude-opus-4-7` rejects the `temperature` parameter — the live API returns
"temperature is deprecated for this model" (captured in the v1.4 milestone
audit, line 273). `forge_bridge/llm/_adapters.py::AnthropicAdapter` currently
sends `temperature` on every request unconditionally. Phase 17 MODEL-01
therefore targets `claude-sonnet-4-6` (which still accepts temperature), not
`claude-opus-4-7`, even though the original SEED-CLOUD-MODEL-BUMP-V1.4.x seed
called for opus-4-7. Before any future bump to opus-4-7 (or any successor
that rejects temperature), AnthropicAdapter must elide the parameter for the
affected model(s).

## Why This Matters

- **Phase 17 deliberately stops short of opus-4-7** — the "isolated default-
  only change" boundary in Phase 15 D-30 forbids coupling an adapter change
  to a default-bump commit.
- **Anthropic deprecation cadence** — sonnet-4-6 will eventually be replaced
  by an opus-4-7-style model that also rejects `temperature`. The adapter
  change has to land before the bump, not alongside it.
- **Determinism contract preserved** — current call sites pass
  `temperature=0.1` for deterministic pipeline-code generation. The fix is
  per-model elision, not unconditional removal.

## Two Facts to Carry Forward

1. **`claude-opus-4-7` rejects `temperature`** — verified during v1.4 close-
   out (audit line 273). Live API response: `temperature is deprecated for
   this model`.
2. **`AnthropicAdapter` always sends `temperature`** — see
   `forge_bridge/llm/_adapters.py` (the adapter's request-payload assembly
   path). No model-aware conditional today.

## When to Surface

- A v1.5 milestone planning session that proposes bumping the cloud default
  to claude-opus-4-7 (or any model published after sonnet-4-6 that rejects
  `temperature`).
- Anthropic announces deprecation of claude-sonnet-4-6 (forces the bump and
  therefore forces this seed's resolution).
- Any v1.5 phase that touches `AnthropicAdapter` request assembly — fold this
  into the same change while you're already in the file.

## How to Apply

1. Identify the set of Anthropic models that reject `temperature` (likely
   `claude-opus-4-7` and successors; confirm against current Anthropic API
   docs at apply time).
2. Add a model-aware conditional in `forge_bridge/llm/_adapters.py`
   AnthropicAdapter request assembly — elide `temperature` when the target
   model is in the rejection set; pass-through otherwise. Default behavior
   for sonnet-4-6 and earlier MUST NOT change.
3. Add a unit test that constructs the adapter for an opus-4-7-style model
   and asserts the request payload contains no `temperature` key. Add a
   parallel positive test for sonnet-4-6 confirming `temperature` is still
   sent.
4. Re-run LLMTOOL-02 (`test_anthropic_tool_call_loop_live`) against the
   newer model to confirm tool-call loops still pass after the elision.
5. Now — and only now — bump `_DEFAULT_CLOUD_MODEL` in
   `forge_bridge/llm/router.py` in an isolated commit (mirror the Phase 17
   P-02 commit shape).

## Cross-References

- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` line 273 — empirical capture
  of the opus-4-7 temperature-rejection error.
- `.planning/seeds/SEED-CLOUD-MODEL-BUMP-V1.4.x.md` — the seed Phase 17
  MODEL-01 closes; this seed is its v1.5 successor for the opus-4-7 path.
- `forge_bridge/llm/_adapters.py` — `AnthropicAdapter` (the file to edit).
- `forge_bridge/llm/router.py` `_DEFAULT_CLOUD_MODEL` — the constant the
  eventual v1.5 bump touches.
- Phase 15 D-30 — decoupled-commit mandate (still binding for the v1.5
  bump; the adapter change and the default flip are separate commits).
