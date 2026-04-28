---
name: SEED-DEFAULT-MODEL-BUMP-V1.4.x
description: Bump default Ollama tool-call model qwen2.5-coder:32b → qwen3:32b in v1.5 (deferred from v1.4.x Phase 17 — see empirical evidence below)
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: A v1.5 milestone planning session AND one of (a) the default complete_with_tools `max_seconds` budget has been bumped to ≥120s, (b) `OllamaToolAdapter` gains a per-model `think=False` / qwen3 `/no_think` directive, OR (c) router-init adds a warmup-ping path that absorbs cold-start cost
---

# SEED-DEFAULT-MODEL-BUMP-V1.4.x: Default Ollama tool-call model bump

## Idea

FB-C ships with `_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"` (the v1.0 default — known-good baseline). Research §3.5 indicates `qwen3:32b` has stronger tool-calling reliability per Ollama community signal. After FB-C ships and the assist-01 UAT empirically validates qwen2.5-coder:32b as the production baseline, run the same UAT against qwen3:32b. If it matches or beats the baseline, bump the default in an isolated commit.

## Why This Matters

- **qwen3 has better-trained tool calling** — community reports qwen3 family converges faster on multi-step loops and produces fewer hallucinated tool names.
- **qwen2.5-coder will eventually be retired** from the Ollama registry — staying on the older default risks discovery cliff.
- **Conservative-bump-first pattern** — research §8 Q1 explicitly recommends shipping the known-good and bumping after empirical UAT. Decoupled risk.

## When to Surface

- A v1.4.x patch milestone opens for polish work AFTER FB-C ships
- An operator reports a tool-call reliability issue against qwen2.5-coder:32b (early bump trigger)
- Any planning session for a phase that touches `forge_bridge/llm/router.py` defaults

This seed should NOT resurface during the v1.4 FB-C ship itself — the conservative-bump sequence requires the baseline to be established empirically before changing the default.

## How to Apply

1. Pull qwen3:32b on assist-01: `ollama pull qwen3:32b`.
2. Re-run the FB-C UAT against qwen3:32b: `FORGE_LOCAL_MODEL=qwen3:32b FB_INTEGRATION_TESTS=1 pytest tests/integration/test_complete_with_tools_live.py::test_ollama_tool_call_loop_live`. Pass = sentinel substring present in terminal response.
3. Run a representative artist-prompt batch (≥5 real Web UI chat panel prompts) and compare subjective response quality to the qwen2.5-coder:32b baseline.
4. If both pass: bump `_DEFAULT_LOCAL_MODEL = "qwen3:32b"` in `forge_bridge/llm/router.py` in an ISOLATED commit (mirror the D-30 cloud-bump precedent — do NOT couple to other v1.4.x changes).
5. Add a regression test asserting the default has been bumped in `tests/test_llm.py`.
6. Update v1.4.x release notes mentioning the model default bump and any operator-visible behavior changes.

## Cross-References

- FB-C CONTEXT.md D-28 — "Stay on qwen2.5-coder:32b for FB-C ship. Open SEED-DEFAULT-MODEL-BUMP-V1.4.x.md for the qwen3:32b bump after assist-01 UAT."
- FB-C research §3.5 — Ollama model allow-list and reliability rationale.
- FB-C research §8 Q1 — open question + recommendation rationale.
- REQUIREMENTS.md Out of Scope row "Default Ollama tool model bump".
- forge_bridge/llm/router.py:90 — current `_DEFAULT_LOCAL_MODEL` value.
- forge_bridge/llm/_adapters.py — `_OLLAMA_TOOL_MODELS` allow-list (qwen3:32b already present per D-29; only the default changes).

## Empirical Evidence (Phase 17 pre-run UAT, 2026-04-28)

Per CONTEXT.md D-02, the qwen3:32b live UAT was run on assist-01 BEFORE
Phase 17 plan-phase locked. The empirical result was non-deterministic
against the v1.4.x default `max_seconds=60` budget, so MODEL-02 took
acceptance branch (b) — defer with a phase-17 SUMMARY note.

**Test:** `test_ollama_tool_call_loop_live` against
`FORGE_LOCAL_MODEL=qwen3:32b` on assist-01 (M-series GPU, 32 GB) at HEAD
`fad8615` (v1.4.0; identical source as current main for `forge_bridge/`
and `tests/`).

### Run 1 — cold start, default 60 s budget

- iter 1: 55.2 s, 522 completion tokens, `status=continuing` (tool dispatched correctly)
- iter 2: never reached — `LLMLoopBudgetExceeded reason=max_seconds`
- Sentinel `FORGE-INTEGRATION-SENTINEL-XJK29Q`: NOT returned

### Run 2 — warm start, extended 180 s budget (`tmp/qwen3_extended_uat.py` script, same prompt + tools + executor as the test, `max_seconds=180`)

- iter 1: 39.6 s, 445 completion tokens, `status=continuing`
- iter 2: 18.4 s, 195 completion tokens, `status=terminal`
- Total elapsed: 58.0 s
- Sentinel returned verbatim: `FORGE-INTEGRATION-SENTINEL-XJK29Q` ✅

### Diagnosis

The salvage helper (`forge_bridge/llm/_adapters.py::_try_parse_text_tool_call`)
handles the qwen3 tool-call shape correctly — **no 6th shape, no widening
required**. The 2-step LLMTOOL-01 loop completes end-to-end on qwen3:32b
when given enough wall-clock budget.

The failure mode is **completion-token verbosity**: qwen3 thinking-mode
emits 400-525 tokens per turn (vs ~50 for qwen2.5-coder). At ~10-11 tok/s
on assist-01, iter 1 alone consumes 40-55 s. This puts the total run at
55-75 s — borderline against the 60 s default, with cold-start sensitivity
pushing the cold path past budget.

**Bottom line:** zero regression risk to MODEL-02 itself (mechanics work);
the bump is gated on either widening the budget or quieting qwen3's
thinking-mode emit.

## Candidate v1.5 Fixes (pick one or stack)

1. **Bump default `max_seconds`** in `forge_bridge/llm/router.py`
   `complete_with_tools` from 60 → ~120 s. Decision is whether the same
   budget bump is acceptable for the cloud (Anthropic) path too. Lowest-
   implementation-cost option; trades latency budget for model coverage.

2. **Add qwen3 `/no_think` (or `think=False`) directive support** in
   `forge_bridge/llm/_adapters.py::OllamaToolAdapter`. qwen3 supports a
   directive that suppresses chain-of-thought emit. Cleanest fix —
   removes the verbosity at the source — but requires per-model adapter
   awareness similar to the cloud-side `temperature`-elision pattern in
   SEED-OPUS-4-7-TEMPERATURE-V1.5.

3. **Router-init warmup ping**. Cold start dominates the borderline cases
   (Run 1 vs Run 2). A small warmup request at `LLMRouter` instantiation
   (or first `acomplete()` call) absorbs the cold cost out of the
   tool-call loop's measured budget. Lightest behavioral change; doesn't
   solve the verbosity issue but materially reduces cold-path failure
   rate.

Pick during v1.5 planning based on whether a default-budget bump is
acceptable for the cloud path too.

## Phase 17 Closure (2026-04-28)

- MODEL-02 closed against acceptance branch (b): "bump deferred with a
  phase-17 SUMMARY note citing specific qwen3:32b failure modes that
  block the conservative-bump-first pattern."
- `forge_bridge/llm/router.py` `_DEFAULT_LOCAL_MODEL` remains
  `qwen2.5-coder:32b` (preserved through Phase 17 P-01 + P-03).
- This seed is the durable home for the empirical evidence; the Phase 17
  SUMMARY references this section.
