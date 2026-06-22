# M2 — Chain-corpus capture (#102) — Pass-to-Code Instruction

**Date:** 2026-06-22 · **Base:** main `e8cac71` · **Tracks:** issue **#102** · **Status:** READY FOR CODE.
**Authority:** `.planning/M2-CHAIN-CORPUS-CAPTURE-FRAMING.md` (CONVERGED — read it for the *why*; this doc is the *what/where/how*). Decisions Q1–Q5 are **locked** — do not relitigate; if the code contradicts a decision, stop and surface it, don't quietly diverge.

This builds a **dormant, env-gated, reads-only capture instrument**. It changes **no runtime behaviour**: every code path behaves identically when the gate is off, and capture failure is swallowed (never becomes chat failure). You are producing a corpus, not consuming one — there is no slice-5 work here.

---

## 0. The one grounding task to do FIRST (before writing the trace seam)

The trace seam must record **every actual tool invocation** made by the legacy chat path (`run_compile_branch → run_chain_steps → execute_chain_step`), keyed by `(tool_name, args_hash)`, order-independently. Before choosing where to hook:

**Confirm how legacy-path `foreach` reaches its per-item tool calls.** Read `forge_bridge/console/_step.py:182` (`_maybe_execute_foreach_step`) and follow it. Question: do per-item tool calls funnel through the same `mcp.call_tool(...)` site at `_step.py:445`, or through a separate call site? Also note the resolver probe calls to `mcp` at `_step.py:364/397/410`.

**Recommended seam (decide after grounding): a per-request wrapper around `mcp.call_tool`.** Wrapping the `mcp` object once in `run_compile_branch` (where `mcp` is in scope) records a trace record on *every* `call_tool`, regardless of which path invoked it — this is order-independent by construction (matches the §0.5 principle) and needs zero edits inside `_step.py`'s many return sites. The wrapper also naturally holds the per-request collision accumulator (§3). **Open sub-decision for you to resolve and document:** whether resolver-probe calls (`_step.py:364/397/410`) belong in the replay trace — they must be included **iff** the graph compiler path also issues them, else they desync the oracle. Ground this against the graph path before deciding; default to capturing all `call_tool` and tagging probe vs step if uncertain.

If the wrapper proves wrong, the fallback is the single MCP chokepoint at `_step.py:445` (`raw = await mcp.call_tool(tool_name, params)`), which already has `tool_name`, `params`, and `raw` in hand.

---

## 1. Package scaffold — `forge_bridge/chain_corpus/`

Mirror `forge_bridge/comprehension/` exactly (the lighter of the two corpus patterns). Files:

- `__init__.py` — own `__all__` (export capture fns, schema constants/validators, reader fns). **The top-level `forge_bridge.__all__` stays 19 — do not touch it.**
- `_capture.py` — env gate + atomic-append writers (one per record type).
- `_schema.py` — two distinct record schemas + validators.
- `reader.py` — validated reader + the Q5 coverage report.

**Mirror from `comprehension/_capture.py` verbatim in shape:**
- Env gate `FORGE_BRIDGE_CHAIN_CORPUS_CAPTURE` (truthy/falsy set, warn-once on unrecognized).
- Dir override `FORGE_BRIDGE_CHAIN_CORPUS_DIR`, default `~/.forge-bridge/chain-corpus/`.
- Versioned `_header` line per file; `json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"`; `mkdir(parents=True, exist_ok=True)`; append-with-`flush`.
- **Swallow-all** `except Exception` → `logger.warning` → return `None`. Capture is observational only.

⚠️ **Distinct path, distinct schema.** Do **not** write to `~/.forge-bridge/executions.jsonl` (the learning-pipeline log — the "no shared-path JSONL writers" non-goal). Do **not** import or couple to `corpus/_schema.py` (divergence) or `comprehension/_schema.py`. Distinct names forever.

---

## 2. Schemas — two records, two files, joined by `request_id`

`SCHEMA_VERSION = "1"`. Each file gets a `_header` line.

**`chain-compile-<DATE>.jsonl`** — one record per compile (written at each `run_compile_branch` regime return):
```
schema_version, captured_at, request_id, regime,
chain_steps: list[str],            # the model-emitted text — the corpus payload
salvage_applied: bool, salvage_reason: str|null,
variety_tags: list[str],           # see §4
source: "captured" | "seed",       # seeds excluded from the Q5 bar
replayable: bool                    # regime + collision verdict (§3)
```

**`chain-trace-<DATE>.jsonl`** — one record per actual tool invocation:
```
schema_version, captured_at, request_id,
tool_name: str,
args_hash: str,                    # see §2.1
result_hash: str,                  # see §2.1
result: <json>                     # the recorded tool output (the stub's return value)
```

Validators follow `comprehension/_schema.py`'s style (required-key set, type checks, `SchemaValidationError` / `SchemaVersionMismatch`). Keep them strict — a malformed record is a bug, not data.

### 2.1 Hashing — reuse the runtime's canonical identity, persist the FULL digest
The K=2 trigger canonicalizes args as (`router.py:1132-1135`):
```python
args_canonical = json.dumps(arguments, sort_keys=True)
args_hash = hashlib.sha256(args_canonical.encode("utf-8")).hexdigest()  # NOT [:8]
```
Reuse this exact canonicalization for **both** `args_hash` and `result_hash` (canonicalize the result the same way). Router truncates to `[:8]` **for log lines only**; the corpus persists the **full hex digest** to make `(tool_name, args_hash)` collision-safe at corpus scale. This is the runtime's established canonical-call identity (`{tool_name, args_hash, result_hash}`, `router.py:101-103`) — inherit it, do not invent a parallel scheme.

---

## 3. Replay key + collision detection (the load-bearing rule)

The stub key is **`(tool_name, args_hash)`** — order-independent, survives `foreach` re-entry today and #88 concurrent dispatch tomorrow. **No ordinal component** (`step_index` / `item_index` / `nth_occurrence`) — those bake in a call-order assumption the graph already violates.

**Per-request collision detection (fail-loud → honest exclusion):**
- Maintain a per-`request_id` map `(tool_name, args_hash) → result_hash` as trace records are emitted (the mcp-wrapper from §0 is the natural home).
- If the *same* `(tool_name, args_hash)` is ever seen with a *different* `result_hash` in one request, that chain is **non-deterministic → not faithfully replayable**. Mark the compile record `replayable=false` (→ Tier-0 only). **Never** silently keep one result.
- Ordering note: in the non-mutating path, `run_chain_steps` (execution) runs at `_chat_compile.py:244` *before* the regime return at line 261 — so all trace records precede the compile-record write. The collision verdict is therefore known when the compile record is written. Confirm this ordering holds for every captured regime.

Worked cases to keep correct (from DT, use as test fixtures): static-arg `foreach` (N identical calls, identical results → no ambiguity); varying-arg `foreach` (distinct args → distinct keys); non-deterministic body (collision → Tier-0).

---

## 4. Variety tagging + Q5 coverage report

Tag each compile record at capture from facts already in hand — **no model call, no guessing**:
- `regime` (from `CompileBranchOutcome.regime`).
- `salvage` (from `salvage_applied`).
- token presence in `chain_steps`: `foreach`, `if_gate`, `commit`, `filter`, `collect`, `select`; multi-step (`len(steps) >= 3`); empty/degenerate.

Required classes for the Q5 bar (each present `>= k` in the **`source=="captured"`** subset): multi-step reads · op mix `filter→foreach→collect` · `if_gate` both branches · `foreach` N>1 · Bug-D salvage · clarification re-entry · empty/degenerate · mutating-preview structural (`filter→…→commit`).

`reader.py` provides the **coverage report**: per-tag counts over `captured` records vs a floor. This is the machine-checked gate slice 5 reads — **stated limit:** it certifies coverage of *known structural classes at real-captured volume*, not the model's full behavioural range. Name that limit in the report output.

---

## 5. Hook wiring (both env-gated, both swallowed)

1. **Compile record** — in `run_compile_branch` (`forge_bridge/console/_chat_compile.py:172`), emit at each regime return (lines ~230, ~261, and the `compile_error`/clarification returns). Set `replayable` from regime (`compiled_non_mutating` → candidate-true, then ANDed with the collision verdict; `compiled_mutating_preview` / clarification / abort → false/structure-only). `source="captured"`.
2. **Tool-trace records** — via the §0 seam (recommended: per-request `mcp` wrapper installed in `run_compile_branch`), one record per `call_tool`.
3. **`executor.py` stays byte-stable** — the trace seam lives on the legacy chat path, never in `composition/executor.py` or `UnifiedDispatch`.

---

## 6. Constraints (binding — verify each before you call it done)

- `forge_bridge.__all__` **== 19**, byte-unchanged. New package carries its own `__all__`.
- No new external libraries (stdlib `json` / `hashlib` / `os` / `pathlib` / `datetime` only — same as `comprehension/`).
- Env gate **off by default** → zero records, zero behaviour change, every existing test still green.
- All capture errors swallowed to `logger.warning`.
- No write to the learning-pipeline log path; no schema coupling to `corpus/` or `comprehension/`.
- `ruff` clean.

---

## 7. Verification bar (DT posture)

- **Unit:** collision detector flips `replayable=false` on a synthetic stub returning two results for one `(tool_name, args_hash)`. `(tool_name, args_hash)` resolves a static-arg `foreach` (slice-2b shape) with no ambiguity. Variety tagger emits correct tags for hand-built `chain_steps` covering each Q5 class. Schema validators reject malformed records. Reader round-trips header + records; coverage report counts `captured`-only.
- **Integration (one specimen, as a smoke test):** with the gate on, drive one real non-mutating chat read; assert both a compile record and its trace records are written and join on `request_id`; replay the captured trace through a `(tool_name, args_hash)`-keyed stub MCP and assert legacy `run_chain_steps` and `chain_compiler → GraphExecutor` agree on the result (this *is* the slice-5 Tier-1 oracle, exercised once here to prove the captured data is sufficient to replay).
- **Gate-off:** identical behaviour, zero files written. Run the existing console/composition suites green.

---

## 8. Commit shape

Small, reviewable commits: (1) scaffold + schemas + reader (no hooks), (2) capture seams wired, (3) tests. Conventional-commit prefixes (`feat(chain_corpus): …`). Reference #102. Co-author trailer per repo convention. Do **not** turn on the env gate anywhere in committed config — activation happens later in the projekt-forge dogfood (shared gate with CR.1).
