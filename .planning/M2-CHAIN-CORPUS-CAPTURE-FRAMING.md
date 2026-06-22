# M2 — Chain-corpus capture (issue #102, slice-5 prerequisite) — Orch Framing

**Date:** 2026-06-22 · **Status:** CONVERGED (Orch positions + DT grounding + Creative redline; Q1–Q5 locked → ready for pass-to-code).
**Base:** main `0ba274c`. **Tracks:** issue **#102**. **Parents:** [[project_passoff_2026_06_22_m2_slice4_compiler_shipped]] · `M2-CHAIN-CORPUS-CAPTURE-SEED.md` (grounding seed; read first) · `M2-SLICE-4-FRAMING.md` (the slice this gates).
**Cadence:** Orch drafts positions → DT grounds the load-bearing pair (replay-completeness + intent-source) → Creative weighs experience → converge → pass-to-code → DT-verify → ship.

---

## 0. What this builds (one paragraph)

A **reads-only, env-gated capture instrument** that persists *replayable* `chain_steps` produced by the real model, so M2 slice 5 can validate the chain compiler against the **distribution the model actually emits** rather than the slice-4 hand-authored set. It changes **no runtime behaviour** — it observes the existing chat-compile path, mirrors the comprehension/divergence atomic-append-JSONL pattern, writes to its own distinct artifact path, and swallows every error (capture failure must never become chat failure). It produces a corpus; it does not consume one.

---

## 0.5 Architectural principle (Creative, elevated to load-bearing)

**Replay identity is execution-order invariant.** The thing that identifies a recorded tool call must describe the *invocation* (`tool_name` + canonical `args_hash`), never the *scheduling* (`step_index`, `item_index`, `nth_occurrence`). This single principle explains the whole design: why `step_index`/`nth_occurrence` die as keys, why `request_id` *joins* records rather than ordering them, and why future concurrent dispatch (#88) doesn't invalidate the corpus. It is the same transition `GraphExecutor` has been making everywhere — *compare semantics not order, graph not linear chain, invocation not scheduling*. The corpus inherits that philosophy rather than inventing a parallel one.

## 1. The reframe that drives everything (grounded 2026-06-22)

**The seed's Q1 lean — "wrap `compile_intent` in the router so the corpus catches every caller" — does not survive grounding.** Here is why:

- `LLMRouter.compile_intent` (`forge_bridge/llm/router.py:730`) returns **only `list[str]`** — the chain-step *text*. It has no tool I/O, no execution results, nothing replayable.
- The per-step tool results that deterministic replay requires are produced **downstream**, when `run_chain_steps` (`forge_bridge/console/_engine.py:17`) executes each step and accumulates a `chain_trace` of `{"step": step_text, "result": <tool output>}` (`_engine.py:101-104`).
- `chain_trace` only exists at the `run_compile_branch` level (`forge_bridge/console/_chat_compile.py:172`), **after** `run_chain_steps` runs (line 244).

**Therefore the corpus cannot be a single router-level hook.** The text and the replay fixtures are produced at two different seams. This is the load-bearing structural fact, and it answers Q1 and Q2 together.

**Second grounded fact that shapes Q5:** mutating chains **never execute in chat**. `run_compile_branch` routes a chain containing a commit node to `compiled_mutating_preview` and returns at line 230 *before* `run_chain_steps` — execution only happens later via the ratify path (`run_apply_branch`). So mutating chains yield **text but no read-execution trace**. Any claim that the corpus "replays `filter→foreach→commit` end-to-end offline" would be false for the commit leg.

---

## 2. Orch positions

### Q1 — Capture hook location → **branch-level, two seams, not the router.**

Capture in the chat-compile path, not inside `compile_intent`:

1. **Compile record** — emitted in `run_compile_branch` once the regime is known (after line 215 routing, at each return). Carries the model-emitted `chain_steps` text, the regime, salvage flags, and variety tags.
2. **Tool-trace record** — emitted from `execute_chain_step`'s successful return (the natural per-invocation seam where `tool_name` / args / `outcome["result"]` are all in hand), **not** deep inside `UnifiedDispatch` or the graph `executor.py` (which stays byte-stable). Each carries `(request_id, step_index, tool_name, args, result)`.

The two are **joined by `request_id`**. Rationale: only the chat path matters (the live compiler input in `run_apply_branch` is a persisted *ratified* chain — a strict subset of compiled output, so a compile-capture corpus is a faithful superset). Router-level capture buys "all callers" but loses replayability, which is the whole point.

> ⚠️ **DT to ground:** is `execute_chain_step`'s return the right seam, or does re-entrant `foreach` dispatch invoke tools below it (so a step-level hook misses per-item calls)? See Q2.

### Q2 — Replay completeness (the crux) → **LOCKED: stub keyed on `(tool_name, args_hash)` + result-hash collision detection.**

**Convergence (DT-grounded, Creative-affirmed):** the stub MCP keys on `(tool_name, args_hash)` — **not** `step_index`, **not** `item_index`, **not** `nth_occurrence` — paired with capture-time `result_hash` collision detection. This is **the runtime's own canonical-call identity reused, not a new scheme:** the K=2 canonical-recurrence trigger already keys on `{tool_name, args_hash, result_hash}` (documented at `router.py:101-103`, the `accumulated_results` entry shape). The corpus inherits the identity the runtime already trusts.

**Why every ordinal key is rejected (the decisive reason):** the graph re-enters dispatch per `foreach` item *today*, and **#88 roadmaps concurrent independent-node dispatch** ("the M2 optimization"). Any key with an ordinal component bakes in a call-order assumption the graph *already* violates (foreach re-entry) and *will* violate by design (#88 concurrency). `nth_occurrence` looks more precise but is false precision — it plants a landmine under the exact optimization #88 exists to track. The keys align with *current implementation*; `(tool_name, args_hash)` aligns with the *architectural direction*. Per §0.5, identity must survive the disappearance of execution order.

**The sole failure mode → honest exclusion, not silent corruption:** `(tool_name, args_hash)` breaks only if the *same* invocation returns *different* results in one run (a stateful/non-deterministic tool). The fix is not positional disambiguation — it is **fail-loud detection**: record `result_hash` per call (already computed by the runtime); if one `(tool_name, args_hash)` ever sees two different `result_hash` values in a capture, flag the chain **non-replayable → Tier-0**, never silently keep one. This converts the only failure mode from silent oracle corruption into honest exclusion — and a non-deterministic tool *cannot* be faithfully replayed anyway, so excluding it is correct, not a gap.

**Worked against the real cases (DT):**
- *Static-arg foreach* (what slice 2b actually produced — N identical roto calls, identical results): same key, N identical `result_hash` → no ambiguity → replays correctly.
- *Varying-arg foreach* (#86 future — per-item args): different args → different keys → each replays correctly.
- *Non-deterministic body*: collision detected → Tier-0 exclusion.

The rest of the position (two joined records; replayability as a first-class per-chain property; the Tier-0/Tier-1 split) stands as below — the split is **forced by the execution paths**, not a convenience.

---

**Original framing (retained for archaeology):** two joined records; stub MCP keyed on the invocation, not step-index.

For Tier-1 parity, slice 5 replays each chain through **both** legacy `run_chain_steps` and `chain_compiler → GraphExecutor` on identical inputs. Neither path can call live Flame/MCP offline, so replay needs a **stub MCP** that returns the recorded result for each tool call.

**Position: key the stub on `(tool_name, args_hash)`, not step-index.** The graph path re-enters dispatch per `foreach` item and may order calls differently than the legacy linear loop; an index-keyed stub would mis-resolve. A content-keyed stub resolves identically regardless of traversal order — which is exactly the property a parity oracle needs.

This means the tool-trace record must capture **args**, not just results. `chain_trace` (`_engine.py`) records only `step` + `result` — **insufficient**. Hence the dedicated tool-trace seam at `execute_chain_step` (Q1.2), which has the args.

**Honest scope of replayability** — record it as a first-class property per chain, never assume it:
- **Reads / non-mutating** (`compiled_non_mutating`): execute fully → full trace → **replayable end-to-end.** The bulk of the corpus and the real-distribution proof.
- **Mutating** (`compiled_mutating_preview`): text captured at preview, **no execution trace** → **structure-only.** Replayable through compile + structural round-trip (text→`GraphSpec`→serialize) and up to the `CommitBoundary` gate, **not** through apply. (Apply was already DT-verified end-to-end in slice 4 against the captured fixture — slice 5 does not need to re-prove apply over the whole corpus.)
- **Clarification / abort / empty**: text captured, partial/no trace → tagged accordingly.

So slice 5 runs **two tiers** over the corpus: **Tier-0** (compile + structural round-trip) over *every* record — proves the compiler ingests the real distribution without choking; **Tier-1** (full both-path execution parity) over the **replayable read subset**. This is the honest decomposition — it neither pretends mutations replay end-to-end nor drops their structural variety.

> ✅ **Resolved (see Q2 lock above):** `(tool_name, args_hash)` + result-hash collision detection. The "does order matter / needs nth-occurrence" worry is exactly the trap #88 makes unsafe — rejected.

### Q3 — Intent source (the gap that bit slice 4) → **live-accumulate from dogfood traffic; seed list only bootstraps structural breadth, tagged distinctly.**

There is no offline real-intent source (grounding confirmed: the 18k-row execution log is code records, no NL intents). You **cannot manufacture a real distribution** — so:

1. **Build the instrument now** (this issue) — env-gated, dormant by default.
2. **Turn it on in the projekt-forge re-pin dogfood** — the same dogfood that is already the CR.1 carry-forward dependency. Real chat intents accrue as the tool is driven. *Slice 5 and CR.1 share this gate* — worth stating: neither opens until dogfood traffic exists.
3. **A curated real-intent seed list** may bootstrap *structural* breadth (to exercise the known variety classes early), **but every seeded record is tagged `source=seed` vs `source=captured`** and the acceptance bar (Q5) counts only `captured`. This honors *captured-not-assembled* ([[feedback_captured_not_assembled]]) — seeds prime the instrument; they never satisfy the bar.

**Consequence to surface plainly:** this couples slice 5's open date to dogfood volume. That is correct, not a defect — the deferral that bit slice 4 was precisely the absence of a real distribution, and the fix is to capture one, not to fabricate one.

### Q4 — Schema + versioning → **new `forge_bridge/chain_corpus/` package, own `__all__`, two distinct schemas, mirror the comprehension lighter pattern.**

- New package `forge_bridge/chain_corpus/` — `_capture.py` · `_schema.py` · `reader.py`, own `__all__`, **does not touch the top-level 19**.
- Mirror `forge_bridge/comprehension/_capture.py` exactly: env gate `FORGE_BRIDGE_CHAIN_CORPUS_CAPTURE`, dir override `FORGE_BRIDGE_CHAIN_CORPUS_DIR`, default `~/.forge-bridge/chain-corpus/`, versioned `_header` line, `json.dumps(sort_keys=True)`, append-with-flush, **swallow-all**.
- **Two files, joined by `request_id`:** `chain-compile-<DATE>.jsonl` (compile records) + `chain-trace-<DATE>.jsonl` (tool-I/O records). Each gets its own validated schema in `_schema.py`.
- **Never couple** to `corpus/_schema.py` (divergence) or `comprehension/_schema.py` — same standing rule CLAUDE.md states for those two. Distinct names forever.
- ⚠️ **Not** a shared-path JSONL writer ([[project_learning_pipeline_non_goals]]): distinct artifact path, distinct schema, no write to `~/.forge-bridge/executions.jsonl`. The non-goal forbids adding writers to the *learning-pipeline log*, not new corpora at their own paths.

### Q5 — "Broad enough" acceptance → **coverage report over variety tags, volume floor, each class present ≥k; certify by tag-coverage, not author judgment.**

Required variety classes (each must appear in the **`captured`** subset before slice 5 opens):
1. multi-step reads (n≥3)
2. op mixes (`filter` → `foreach` → `collect`)
3. `if_gate` — both taken and pruned branches
4. `foreach` with N>1 (the slice-2b n=1 trap)
5. Bug-D salvage forms (`normalize_chain_shape` `salvage_applied=true`)
6. clarification re-entries
7. empty / degenerate plans
8. mutating-preview structural forms (`filter→…→commit`) — structure-only

**Certify by a `reader.py` coverage report** that counts captured records per variety tag against a floor — not by anyone eyeballing the set. The instrument tags each record at capture from facts already in hand (regime, salvage flag, presence of `foreach`/`if_gate`/`commit` tokens). **Stated limit:** tag-coverage proves the corpus spans the *known structural classes* at real-captured volume; it cannot prove it covers the model's *full* behavioural range. We claim the former and name the latter — same honesty posture as the slice-4 deferral ([[feedback_audit_before_overfit]], [[feedback_wellformedness_precedes_content]]).

---

## 3. The load-bearing decision — SETTLED

**Q2's stub-key correctness** was the one load-bearing item; it is now resolved (see Q2 lock + §0.5): **`(tool_name, args_hash)` + result-hash collision detection**, reusing the runtime's canonical-call identity (`router.py:101-103`), rejecting every ordinal key because #88's roadmapped concurrency makes call-order an unsafe thing to key on. Both voices converged; no open questions remain. Everything else is mechanical mirroring of the proven `comprehension/` pattern.

## 4. Non-goals (binding)

- No runtime behaviour change; capture is observational, env-gated, dormant by default, errors swallowed.
- No write to the learning-pipeline log path; no coupling to divergence/comprehension schemas.
- No hand-authored chains in the `captured` subset (seeds tagged separately, excluded from the bar).
- `executor.py` stays byte-stable; the tool-trace hook lives at `execute_chain_step`, off the graph executor's path.
- No top-level `__all__` change (stays 19).

## 5. Pass-to-code brief (CONVERGED — ready for the code agent)

Q2 grounding is done; no open design questions. Build order:

1. **Scaffold `forge_bridge/chain_corpus/`** mirroring `forge_bridge/comprehension/` (`_capture.py` · `_schema.py` · `reader.py`, own `__all__`, top-level 19 untouched). Env gate `FORGE_BRIDGE_CHAIN_CORPUS_CAPTURE`, dir `FORGE_BRIDGE_CHAIN_CORPUS_DIR`, default `~/.forge-bridge/chain-corpus/`, versioned `_header`, `sort_keys=True`, append-flush, **swallow-all**.
2. **Two schemas, two files, joined by `request_id`:**
   - `chain-compile-<DATE>.jsonl` — `{schema_version, captured_at, request_id, regime, chain_steps:list[str], salvage_applied, salvage_reason, variety_tags:list[str], source:"captured"|"seed", replayable:bool}`.
   - `chain-trace-<DATE>.jsonl` — one record per *actual tool invocation*: `{schema_version, captured_at, request_id, tool_name, args_hash, result_hash, result, item_index?}`. `args_hash`/`result_hash` computed the **same way** the K=2 trigger computes them (reuse, don't reinvent — cross-check `router.py` canonical identity).
3. **Two capture seams, both env-gated + swallowed:**
   - *Compile record* — in `run_compile_branch` (`_chat_compile.py`), at each regime return, once the regime + salvage + variety are known. Set `replayable` from the regime (`compiled_non_mutating` → true; `compiled_mutating_preview`/clarification/abort → false/structure-only).
   - *Tool-trace record* — at `execute_chain_step`'s successful return (has `tool_name`, args, `outcome["result"]`). **Not** in `UnifiedDispatch` or `executor.py` — keep the graph executor byte-stable.
4. **Result-hash collision detection** at capture: if one `(tool_name, args_hash)` within a `request_id` sees two distinct `result_hash`, mark that chain's compile record `replayable=false` (Tier-0). Fail-loud, never silently keep one.
5. **`reader.py` coverage report** — per-variety-tag counts vs a floor, `source=="captured"` only; this is the Q5 gate slice 5 reads.
6. **Turn on in the projekt-forge dogfood** (shared gate with CR.1); accumulate; certify against the Q5 floor; *then* slice 5 opens.

**Verification posture (DT, at build):** unit — collision detector flips `replayable` on a synthetic non-deterministic stub; `(tool_name, args_hash)` resolves a static-arg `foreach` (slice-2b shape, N identical calls) with no ambiguity. Integration — capture a real non-mutating chat read end-to-end, replay the captured trace through a stub MCP, assert legacy `run_chain_steps` and `chain_compiler → GraphExecutor` agree (the slice-5 Tier-1 oracle, exercised on one captured specimen as a smoke test). Env-off → zero records written, zero behaviour change.
