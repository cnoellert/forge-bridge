---
milestone: v1.9
phase: CR.1
type: phase-amendment
status: ratified
opened: 2026-05-31
amends:
  - .planning/phases/CR.1-conversational-reads-answer-pass-spike/CR.1-PLAN.md (2bfd167) — L1, OBL-1, OBL-2, L-UAT
  - .planning/phases/CR.1-conversational-reads-answer-pass-spike/CR.1-FRAMING.md — the "continuity insight"
grounding: independent grounding against a56b93b by orchestrator + DT — handlers.py:1973-1975 (sole (b)+capture call site, compiled_non_mutating) + _execute_forced_tool final_text:"" + trace-envelope messages + PR20 early-return at :1716/:782 (before compile dispatch) + _answer.py:_synthesize_answer/_build_synthesis_prompt contract (chain=[{step,result}], result rendered deserialized) + _engine.py:85-86 (compiled-path result is parsed dict)
artifact_role: framing correction — CR.1 execution amendment, blocks the dogfood until landed
---

# CR.1 amendment — the PR20 forced-tool path bypasses the conversational-read seam

**Disposition: CONFIRMED. Framing correction required before CR.1 execution
completes.** Discovered by a pre-dogfood pipeline check; grounded three ways
(orchestrator + DT + Creative) against `a56b93b`. CR.1 remains
architecturally sound — synthesis is not wrong; it is attached to only **one
of two** read-completion paths.

## Confirmed structural facts (provable from code alone)

1. **The CR.1 seam exists only on the compile path.** `_synthesize_answer`
   (`handlers.py:1973`) + `emit_comprehension_capture` (`:1975`) are inside
   the `compiled_non_mutating` branch. Grep confirms **zero** other call
   sites.
2. **The forced-tool path produces a *trace* envelope, not an *answer*
   envelope.** `_execute_forced_tool` returns `final_text: ""` (Phase-A
   design) and `messages` = a synthetic `{assistant, content:"", tool_calls}`
   turn + a `{tool, raw result}` turn. The Console renders that as a
   tool-trace, not a reply. It calls neither CR.1 function.
3. **The forced path is reached for the dogfood query set.** PR20
   (`:1716`) fires when `tools_filtered_count == 1 and < tools_available_count`
   and returns from `_execute_forced_tool` (`~:782`) **before** the compile
   dispatch. A single-tool-resolving read never reaches `:1973`.

This chain is pure code structure. The finding is independent of the
3-day-stale daemon that first surfaced it (that daemon ran `5e78f623`,
`docs(A.2)`, pre-CR.1 — its behavior was correctly discarded; the finding
was re-grounded against current disk).

## Precision 1 — the falsified clause: envelope-shape conflation

The CR.1-FRAMING "continuity insight" claimed the `tool_forced` regime
*"already renders an answer via `messages` + `final_text`."* **Both halves
are false on that path:** `final_text` is deliberately `""`, and `messages`
is a tool-call *trace* pair whose assistant turn has `content:""`. The
framing did not merely "miss that a field is empty" — it **mistook the
forced-tool trace envelope for an answer envelope.** They are different
shapes sharing key names (`messages`, `final_text`).

This is the **third instance of manifestation-4 (envelope-shape grounding
failure) this milestone arc** — after CA.1's SSE/JSON shape conflation and
the A.3 L4 envelope. It is now a *pattern*, not a one-off:
`[[feedback-substrate-shape-grounding-at-plan-stage]]`. The fix-forward
discipline, sharpened by DT: **ground the value on the path, not the field
in the type.** A key existing in a response is not evidence of what it
carries on the *specific* execution route.

## Precision 2 — structural-certain vs empirical-near-total (don't overclaim)

- **Structural (certain):** any read resolving through the forced-tool path
  bypasses synthesis and capture.
- **Empirical (runtime-dependent):** *which* questions resolve there is a
  property of `filter_tools_by_message` + `deterministic_narrow` against the
  live ~58-tool surface — not provable from code.

So the defensible claim is **not** "CR.1 cannot be populated by single-result
reads" (absolute). It is:

> **OBL-1 is intentionally dominated by single-result reads; most such reads
> narrow to a single tool and therefore bypass (b) and capture. The dogfood
> corpus would be empty or near-empty.**

(OBL-1 scenario 7, already split to two tools, *might* not narrow to one and
could capture — which is exactly why the absolute claim would look falsified
when the mechanism is in fact certain.) Ground the mechanism as certain;
state corpus-coverage as empirical-and-near-total.

## Ruling — Option A: extend the seam to the forced-tool path

**Adopted.** Not merely "smallest change" — it restores the project's
load-bearing substrate-discipline invariant: **operator/execution surfaces
are projections onto one substrate, not parallel paths** (the
`_execute_python_core` / Phase-24 invariant). Today the answer-pass lives on
one of two read-completion routes — exactly the parallel-path divergence that
refactor exists to prevent. The answer-pass belongs at **both**
read-completion seams **or neither**. A makes them consistent.

**Shape adaptation (A1 — preferred, grounded):** the forced path has a
*single tool result as a JSON string* (`tool_content`), not a
`[{step, result}]` chain. So wrap before calling, and **`json.loads` the
result** so it matches the compiled path's *deserialized* shape
(`_engine.py:85-86`; `_build_synthesis_prompt` renders `result` via
`_compact_json` — a raw string would double-encode):

```python
chain = [{
    "step": f"{tool_name} {compact_args}",      # resolved invocation, mirrors compiled `step`
    "result": json.loads(tool_content),          # parsed, NOT the raw JSON string
}]
answer, answer_ms = await _synthesize_answer(router, messages, chain)
if comprehension_capture_enabled():
    emit_comprehension_capture(question=..., chain=chain, answer=answer,
                               wall_clock_ms=answer_ms, model=...)
# attach messages:[{role:"assistant", content: answer}] when answer truthy;
# preserve the existing final_text/trace return otherwise (graceful degrade).
```

A1 keeps **one** synthesis contract (`_synthesize_answer` unchanged) — A2
(teach the synth fn two shapes) is rejected for spreading the contract.
Guard the `json.loads` (a non-JSON tool result degrades to no-answer, never
raises into the read — the constitutional rule holds on this path too).

**Rejected:**
- **B (stop PR20 short-circuiting reads):** touches the tuned
  PR14→PR21→PR20 narrowing stack; re-inherits convergence-wall risk. Wrong
  tool for a pressure-instrument spike.
- **C (dogfood only compile-reaching queries):** unreliable (can't predict
  which narrow) **and** biases the corpus toward non-representative queries —
  corrupts the comprehension study's purpose. C risks a *misleading* corpus,
  not just an empty one.

## What this amends in the plan

- **L1** gains a second seam: the forced-tool path calls `_synthesize_answer`
  + `emit_comprehension_capture` via the A1 wrap, and attaches
  `messages:[{assistant, content:answer}]` on success (graceful-degrade to
  the existing trace return otherwise). Reads-only structural guard still
  holds (forced tools on reads).
- **OBL-1 / L-UAT:** the dogfood is **non-viable until A lands** — the
  daemon and corpus run wait on this amendment, not on `:9996`.
- **OBL-2:** capture coverage now spans both read-completion regimes.
- **Constitutional rule** (synthesis may fail but not block the read) extends
  to the forced path: the `wait_for` bound + exception/`json.loads` swallow
  apply at the new seam too.

## Dogfood note — corpus does not distinguish the two read paths (DT, known limitation)

With A landed, comprehension records now arrive from **both** read-completion
paths — compiled-chain reads and forced single-tool reads — and
`emit_comprehension_capture` gets the same field shape from both sites, so the
captured record **cannot tell them apart**. For answer-fidelity (did the
answer help?) this is fine — path-agnostic by design, and the corpus is a
pressure instrument, not a product. But the dogfood writeup should record it
as a **known limitation**: the corpus can't later answer "do forced-path
answers read differently than compile-path answers?" without a schema field.
Not worth a schema change now; flagged so it's a known limitation, not a later
surprise.

## Status

CR.1 architecture sound; correction is scope-completing, not redirecting.
**Adopted: Option A (A1 shape). IMPLEMENTED + verified** at `a95bf0d`
(`feat(CR.1): answer forced-tool conversational reads`; diff matches A1 —
guarded `json.loads`, parsed-result wrap, `_synthesize_answer` reused
unchanged, graceful trace-envelope degrade; 41 + 490 tests green;
independently re-verified by DT). The structural-discipline invariant is
restored: the answer-pass lives at **both** read-completion seams, not a
parallel path. Remaining: re-run the live pipeline check against a current-code
daemon — single-result reads should now answer + capture.
