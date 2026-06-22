# M2 — Chain-corpus capture (issue #102, slice-5 prerequisite) — Framing Seed

**Date:** 2026-06-22 · **Status:** SEED (grounding + open questions; the Orch framing-with-positions comes next, post-`/clear`).
**Base:** main `4625d90`. **Tracks:** issue **#102**. **Parents:** [[project_passoff_2026_06_22_m2_slice4_compiler_shipped]] · `M2-SLICE-4-FRAMING.md` (as-built; this is the named slice-5 gate) · `M2-PARITY-AND-CUTOVER-FRAMING.md`.
**Purpose:** front-loaded grounding so a fresh context drafts the #102 framing immediately without re-grounding. Issue #102 carries the *why/requirement/acceptance*; this adds the grounded *seam map* + the open framing questions. Read #102 first, then this.

## What this is
Build a capture source that **persists replayable `chain_steps`** — the gate on slice 5 opening (slice 5 must validate the compiler on the real model-emitted distribution, not the slice-4 hand-authored set; otherwise the n=1 trap springs). Reads-only/non-mutating capture; produces a corpus, changes no runtime behaviour.

## Grounded seam map (verified 2026-06-22)
- **`compile_intent`** — `forge_bridge/llm/router.py:730` (def, `LLMRouter.compile_intent`), called at `forge_bridge/console/_chat_compile.py:193` (in `run_compile_branch`). Its output is the `chain_steps` text — the thing to capture. Two candidate hook points: inside the router (catches every caller) vs at the `run_compile_branch` call site (narrower, chat-only).
- **Corpus packages to mirror** — `forge_bridge/corpus/` (divergence: `_capture.py` · `_schema.py` · `_compare.py` · `_identity.py` · `_seed.py` · `_sources.py` · `_topology.py` · `reader.py`) and `forge_bridge/comprehension/` (CR.1: `_capture.py` · `_schema.py` · `reader.py`). Both = **atomic-append-JSONL + versioned-schema, own `__all__`**. The new chain corpus mirrors this shape (likely `forge_bridge/chain_corpus/`), **schema kept distinct — never coupled** to the divergence/comprehension schemas (same rule CLAUDE.md states for those two).
- **Hard constraint** — ⚠️ **no shared-path JSONL writers** ([[project_learning_pipeline_non_goals]]). Do **not** write to the learning-pipeline log (`~/.forge-bridge/executions.jsonl`); distinct artifact path. (That log is also the wrong shape — it's code-execution records, no NL intents — which is *why* slice 4 deferred this.)
- **Replay target** — Tier-1 parity (slice-4 oracle) replays each corpus chain through **both** legacy `run_chain_steps` and `chain_compiler → GraphExecutor` on identical inputs. So the corpus must persist enough to replay **deterministically**.

## Open framing questions (for the post-clear Orch draft to take positions on)
- **Q1 — capture hook.** Wrap `compile_intent` in the router (all callers) or capture at the `run_compile_branch` call site (chat-only)? Lean: router, so the corpus reflects every real compile.
- **Q2 — replay completeness (the crux).** `chain_steps` text alone does **not** replay — Tier-1 parity runs the chain, which calls tools. So the corpus must also persist the **per-step tool I/O** (recorded results, or a stub MCP keyed on them). *Where* does that get captured — `compile_intent` only emits the text; the tool results come from downstream `execute_chain_step`. Does capture span both compile **and** execution, or is the execution trace a separate capture joined by request_id? This is the hardest design question.
- **Q3 — intent source (the gap that bit slice 4).** Live-accumulate from real chat traffic (needs traffic + time) vs drive `compile_intent` over a seed set of real intents (needs a real-intent corpus — *where from?*; the execution log has none). Resolve this or slice 5 stays blocked. Candidate sources: projekt-forge dogfood traffic · a curated real-intent seed list · live accumulation gated on a volume threshold.
- **Q4 — schema + versioning.** Mirror `corpus/_schema.py`'s versioned pattern; new distinct schema (`chain_corpus/_schema.py`); never couple to divergence/comprehension.
- **Q5 — "broad enough" acceptance.** Which variety classes must be present (multi-step · op mixes `filter→foreach→commit` · Bug-D salvage forms · clarification re-entries · empty/edge plans) and how to certify representativeness rather than re-running the n=1 trap one level up.

## First moves for the post-clear draft
1. Read `router.py::compile_intent` + `_chat_compile.py::run_compile_branch` (the capture hook + where chain_steps + downstream results flow).
2. Read `forge_bridge/corpus/_capture.py` + `_schema.py` + `reader.py` (the pattern to mirror) and `comprehension/` (the lighter variant).
3. Resolve Q2 (replay completeness) and Q3 (intent source) — these are load-bearing; the rest follows.
4. Draft the Orch framing with positions on Q1–Q5, lead with views, hand to DT (grounding the replay-completeness + intent-source) / Creative. Then it feeds slice 5.
