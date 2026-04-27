---
name: SEED-DEFAULT-MODEL-BUMP-V1.4.x
description: Bump default Ollama tool-call model qwen2.5-coder:32b → qwen3:32b after assist-01 UAT
type: forward-looking-idea
planted_during: v1.4 FB-C planning (2026-04-26)
trigger_when: A v1.4.x patch milestone opens after FB-C ships AND the assist-01 UAT for the FB-C tool-call loop on qwen2.5-coder:32b has produced a baseline reading
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
