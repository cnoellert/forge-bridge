# Author→Still→Video Loop — Framing (#66)

**Status:** framing converged (cross-voice: Orch synthesis · DT grounding · Operator north-star · generators-side DONE). Slice-1 defined below. Next: probe-first.

**Companions:** generators boundary doc `forge-generators/.planning/CONVERGENCE-TEXT-GENERATION-BOUNDARY.md`; spike `forge-generators/.planning/spikes/sim_storyboard_loop.py`; vision perception `forge-vision#1`; bridge GH issue #66.

---

## The three-way boundary (settled in the 5-seat convergence)

- **Vision** owns *falsifiable* text — captions, panel reads, beat perception, QC measurement. Checked **for faithfulness to its input**.
- **Generators** owns the prescriptive `author_prompt(intent, target, context?)` operator behind an LLM driver (anthropic-api billed / ollama-api free). Emits a **prompt** — a render directive, **never checked against an input**, only by what it yields. *Done, live-proven.*
- **Bridge** owns the loop, plan composition (intent → `operator_sequence`, wiring not prose), lineage/state across makes, the QC→re-author **decision**, and **typing/routing the wire**. **Bridge authors nothing.**

**Wire is HARD-typed.** caption ≠ prompt — opposite QC tests. Typing that wire is the unoccupied territory #66 claims.

**Self-feeding-loop bright line:** generators may chain makes *inside one artifact's production*; the instant a vision measurement/QC sits between two makes, **that edge is bridge's**. Still→re-prompt has vision-QC between → bridge's.

---

## Reference model — the composer's toolkit (operator, 2026-06-16)

We are **not** writing one-off process macros ("pass a greenscreen function"). We are building a **composer's toolkit** — compositing tools **and** AI generative pieces — as atomic, individually-meaningful, independently-dispatchable nodes that compose. The greenscreen→roto pipeline is the grain:

| Operator's words | Atom class | Real node today | Standalone-dispatchable? |
|---|---|---|---|
| "look at the picture — is this a greenscreen?" | perception | `forge_is_greenscreen` | ✅ (live-verified #60) |
| "yes, that is a greenscreen" | measurement (a typed fact) | `is_greenscreen` token output | ✅ |
| "report back: that's a greenscreen" | fact on a typed edge | input artifact on next step | ✅ |
| "do we need roto, since it's greenscreen?" | **judgment / decision** | `FilterNode` predicate (`filter(is_greenscreen == true)`) | ✅ in-process graph node |
| "yes — and here's how we produce roto" | disposition / plan | operator_sequence step selection | ✅ |
| "generate a roto frame" | make | `forge_roto_ref(target_spec)` | ✅ (live-verified #60) |

**This pipeline already exists as composed atomic nodes** (`forge_is_greenscreen → FilterNode → forge_roto_ref`), each independently dispatchable, wired by typed ports — verified composing live for #60 an hour ago. That is the direction; #66 extends the *same* model into the generative loop.

**The atom class most at risk of collapsing into a macro is the *middle judgment*** ("do we need roto?" / "does this render match the beat → re-author?"). Those are **nodes**, not Python `if` statements. In #66 the QC→re-author decision is the judgment node: **human-review node now** (`stage`/`awaiting_decision`), **automated-judgment node later** — same typed-port contract, swapped, not rewritten.

**Honest gap (the real frontier, bigger than #66):** a unified *composition surface* — where CLI, NL, and Graph all wire the **same** node set — does not fully exist yet. The atoms are forming and increasingly compose; the planner turns intent→operator_sequence and `fbridge run/exec` invokes nodes, but chains are still partly hand-authored in scripts (no declarative composer / chain registry — confirmed in the substrate map). #66 slice-1 delivers atoms + a thin *proof* they compose; it is a step toward the composer, **not** the composer itself. We must not let slice-1's thinness read as "the toolkit is done."

---

## Crux finding (grounded against live code)

The bridge graph is a **strictly single-pass, no-back-edge DAG**:
- `foreach.py:94` — `->` in a body raises `FOREACH_CHAIN_BODY_NOT_SUPPORTED` (one-step bodies only, structural).
- `if_gate.py:73` — gates by marking `execution_state` (`passed`/`skipped`); never forks, never loops back.
- `dispatcher.py` — processes one generation step.
- `lineage_graph.py:21` — `v0.1 stub`; `anchors_of → []` (traversal inert).

There is **no loop-back primitive, and there must not be one** — a graph cycle would violate the **`#31` no-back-edge DAG** invariant the grant↔run cardinality pin rests on (`[[project_31_grant_run_cardinality_pinned_1_to_many]]`).

**∴ "the loop" is not a graph cycle — it is a sequence of immutable runs linked by run-lineage.** That shape already shipped: `manual_qc.py` `start_author`/`revise` (PR#75) = one QC→re-author iteration via `ReplayEngine.reconstruct(kind="remediation")` + a typed `qc_correction` input + `remediates_run` edge. No cycle.

---

## The binding guardrail (operator north-star — `[[feedback_graph_is_the_goal_not_cli]]`)

The end-goal is an **operator-drivable graph of atomic typed-port nodes**; CLI / NL / Graph are three front-ends onto ONE node set. Therefore:

- The **ONLY** thing allowed to be imperative is the **cross-run lineage controller** (iteration = mint a new immutable run + `remediates_run` edge). "Imperative loop" = loop-back ONLY; **never** license to inline composition.
- **Intra-step composition** (author→still→caption→video) stays **typed-port graph nodes / `operator_sequence` edges**, never Python statements.
- **The atoms chain into a graph — and the graph is the view of record. CLI / NL / Graph are three lenses on that one view**, not three runtimes. CLI invokes a node directly; NL compiles *to* the same node-graph; the visual graph wires the same nodes. If any lens produces a different execution path, we've failed.
- **Acceptance test for every slice (3-lens):** each atom must be (1) **independently dispatchable** standalone (CLI lens), (2) **addressable by the planner** as an operator_sequence step (NL lens), and (3) **representable as a typed-port node with edges** (Graph lens) — the *same* node under three projections. If a step is reachable by only one lens, or can't be lifted out and dispatched standalone, it's not a node yet — it's a macro, and it fails.

**Convergence:** DT's "caption = typed *input artifact* on the plan step, not a function arg" and the operator's "composition a graph edge could express must not be inlined" are the **same rule** — a typed input artifact on an `operator_sequence` step *is* a graph edge. `_plan_body_with_qc` (manual_qc.py:474-507) already implements this append for `qc_correction`; the caption wire is the identical append with `artifact_type="caption"`.

---

## #66, disambiguated into its two halves

| Half | Shape | Mechanism |
|---|---|---|
| **Forward composition** still→caption→video | **Graph edges** (typed input artifacts on `operator_sequence` steps) | extend `_plan_body_with_qc` append: `artifact_type="caption"` carrying the still's caption + source artifact ref |
| **QC re-author iteration** (re-author on fail) | **Imperative lineage controller** (run-lineage, no cycle) | reuse `manual_qc.revise` → derived run + `qc_correction` + `remediates_run` |

---

## Slice 1 (thin vertical)

**Single beat, end-to-end, one QC iteration, typed caption-input wire, edges recorded.**

- **Reuse untouched:** `manual_qc` derived-run machinery; `GenerationDriverRegistry` submit/poll; `author_prompt` driver (ollama-api free); `ReplayEngine` remediation.
- **New (the real `STUB[bridge]`):**
  1. After a still is authored + **human-approved**, author a video prompt whose `operator_sequence` step carries the still's caption as a typed `artifact_type="caption"` input (graph edge), not folded into the intent string.
  2. Record beat→still→caption→video as run-lineage edges via existing `RUN_LINEAGE_REL_KEYS` / `content_provenance` (**record now, traverse later** — `anchors_of` stays stubbed).
- **QC trigger = HUMAN-gated in slice 1.** Bridge plumbs vision's `(ok, note)` into the `awaiting_decision` block payload as evidence; the operator reads it and calls `revise`/`approve`. This keeps slice 1 honest to "reuse manual_qc untouched" and is *also* where the comprehension corpus wants a human generating pressure.

## Deferred (with re-open triggers)

- **Autonomous QC thresholding** (bridge auto-decides ok/fail and auto-fires re-author) — its own slice; the self-feeding-autonomy bright line.
- **Multi-beat iteration** over a storyboard — after single-beat proves out.
- **Lineage-graph traversal** (`anchors_of`/reachability) — re-opens when a consumer needs "is this video derived from that caption."
- **`grant_id` inheritance** — manual_qc carries two marked D6 points (lines 134, 217). The loop mints derived runs at the same seam, so slice-1's re-author path inherits `grant_id` the moment GenerationGrant (`forge-vision#1`) lands. **Sequence #66 slice-1 with GenerationGrant** so the loop isn't retrofitted.

---

## Next

Probe-first (project cadence): a regression test asserting the slice-1 builder produces a video-authoring plan step whose `inputs` include a typed `artifact_type="caption"` artifact (carrying the still caption + source ref), and that the beat→still→caption→video lineage edge is recorded — mirroring the shipped `qc_correction` probe shape. Then implement to green.
