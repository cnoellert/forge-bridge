# M2 Slice 4 — Orch Framing (chain-text → GraphSpec / first production caller) — positions for the room

**Date:** 2026-06-20 · **Status:** CONVERGED (Orch + DT + Creative) → **Option A with DT's broad-corpus refinement.** Operator confirm pending → pass-to-code.
**Base:** main `d753d41`. **Parents:** [[M2-SLICE-4-FRAMING-SEED]] · `M2-PARITY-AND-CUTOVER-FRAMING.md` (slice 4 = first cutover slice) · `M2-SLICE-3-FRAMING.md`.
**Grounded against live reads (2026-06-20):** `console/_step.py::_maybe_execute_commit_step`, `console/_engine.py::run_chain_steps`, `console/_chat_compile.py::{run_compile_branch, run_apply_branch, build_preview_from_steps}`, `composition/compiler.py`, `composition/commit_boundary.py`.

> **Caution flag:** this is the **first slice that touches the production apply path**. `run_apply_branch` is live in the chat surface. The default posture below keeps the **live path on legacy `run_chain_steps`** and proves graph-apply in parallel — surfacing any "flip it live now" desire as an explicit decision, not a default.

---

## Thesis

The legacy commit path (`_maybe_execute_commit_step`) and `CommitBoundary` are **twins** — both do held → verify-fresh → `CommitNode.verify(held, fresh, assent)` → apply-once. Slice 4 is therefore **not** new authority logic; it's a **compiler + a held-source extension + a parity harness**:

1. a **text `chain_steps` → `GraphSpec`** compiler (the missing front-end), and
2. teaching `CommitBoundary` to read `held` from an **upstream edge** (production) as well as `config` (specimens), and
3. proving graph-apply is byte-equivalent to legacy replay on a real ratified chain — **offline, live path untouched.**

The ratified mutation chain `[rename (discover) → commit]` compiles to the graph `[rename node] --edge--> [commit node]`, where the rename node's manifest output flows to the commit node's `held` input. That's the whole shape.

---

## Q2 — scope — **DECIDED (operator): apply-path-first**

Slice 4 compiles the **ratified-apply** chain (`AssentRecord.chain_steps`) → `GraphSpec` and exercises it via `GraphExecutor`. Read / non-mutating chain compilation is a **follow-on**, not this slice. Rationale: highest parity stakes, smallest slice that gives the engine a real production caller, and it isolates the authority seam.

---

## Q1 — the text→GraphSpec compiler

**Position:** new **`composition/chain_compiler.py`**, a *sibling* to `compile_operator_sequence` — **not** an extension of it. They take different inputs: `compile_operator_sequence` consumes structured `operator_sequence` dicts (`operator_id`/`inputs`/`output_artifact_id`); slice 4 consumes **text `chain_steps`**. Forcing one function to do both muddies the structural compiler.

`chain_compiler` classifies each `step_text` by **reusing the existing `graph/` step-predicates** (`is_commit_step`, `is_foreach_step`, `is_filter_step`, `is_collect_step`, `is_if_step`, …) plus the `admission.py` table — the **same predicates `run_chain_steps`/`_step.py` already dispatch on**. That shared predicate set *is* the parse boundary: legacy and graph classify steps through one grammar, so they cannot drift. Wire **linear edges** (step N's output → step N+1's input port), mirroring the `__previous_result__` threading the chain engine uses today. **Do not duplicate `_step.py`'s parsing.**

---

## Q3 — `held` provenance + drift window — **GROUNDED**

Confirmed in `_maybe_execute_commit_step`: `held = inherited_context["__previous_result__"]` (the prior **discover** step's manifest), `fresh` = a verify-mode recompute, `CommitNode.verify(held, fresh, assent)`, then apply. **The operator ratifies *text*; `held` is recomputed at apply time.** The drift window is **discover→verify within one apply-time run** (a TOCTOU check), *not* preview→apply.

**Position: the graph preserves exactly this window.** Compile `[discover node] --edge--> [commit node]`; `held` flows from the discover node's output; `CommitBoundary` recomputes `fresh`. Same semantics → parity holds. **Do NOT introduce a preview→apply anchor** in this slice — it would change what "drift" means and break parity with legacy. (Tightening the window to span preview→apply is a separate, deliberate hardening if ever wanted — out of scope here.)

---

## Q4 — `CommitBoundary` held-from-edge

**Position:** extend `_held_manifest` to read `held` from `resolved_inputs` (the single upstream node's output) when `config` carries no `held`/`manifest`; **keep the config path** for hand-authored specimens (slice-3 tests stay green). The upstream discover node's output *is* a `mutation_plan` manifest, so the extension is a source-of-held change, not a verify-logic change. **Parity test:** held-from-edge and held-from-config yield identical `CommitNode.verify` outcomes on the same captured manifest. This is the only change to slice-3 code; keep it minimal and additive.

---

## Q5 — parity oracle (production-vs-production)

**Position:** the oracle is **graph-apply vs legacy `run_chain_steps` replay of the same `chain_steps`** — both apply once, so it's the slice-3 shape (plan-equivalence + post-state) lifted to compare the **two production paths** on one ratified chain. Reuse the `compare.py` harness (terminal envelope + status vector, with the mutation-manifest normalization slice 3 added). Fixture: the captured `30sec_edit 21` chain extends here — the ratified `chain_steps` text + the held/fresh/post-state already captured. Captured-not-assembled. **Offline in slice 4**; live real-traffic dual-path is slice 5.

---

## Q6 — full pre-commit vocabulary + liveness boundary

**Position:** a ratified chain may carry reads + `if`-gates before `commit`; the compiler emits those as their boundary node kinds (MCP / filter / if_gate / foreach — all exist from slices 1/2a/2b). The **admission table is the gate**: a step whose first token isn't admitted → **fail-closed** (compile rejects; the live path stays on legacy, so a reject is safe, not a user-facing failure). `_strip_commit_for_exact_read_graph` (commit-containing-but-all-reads) is a read-path concern → defers with the read-path scope.

**The liveness boundary (slice 4 vs 5) — see the converged decision below.**

---

## Q-exec — executor-untouched + the wiring

The graph-apply entry point: compile `record.chain_steps` → `GraphSpec` → `GraphExecutor(UnifiedDispatch(assent_record=record).dispatch).run(graph)` → map the terminal `NodeResult` to the apply outcome (`mark_applied` / `mark_failed`). **`executor.py` stays byte-untouched**; assent enters via `UnifiedDispatch.assent_record` (never the executor, never a `NodeResult`); the `AssentRecord` state-machine transition stays in `run_apply_branch`. The assent-token-ban and byte-lock invariants must stay green — verify after wiring.

---

## CONVERGED — liveness boundary + the broad-corpus success bar (DT + Creative + Orch)

**Decision: Option A. Live `run_apply_branch` stays legacy this slice. Option B (live compile+verify shadow) rejected.**

*Why B is rejected (DT, grounded):* B's live shadow still fires a real `flame_rename_shots(mode=verify)` round-trip to live Flame **inside the authority handler** — latency + a failure surface threaded into the exact seam the caution flag guards; "doesn't mutate" undersells that it touches live Flame and enlarges `run_apply_branch`. And its signal accrues **glacially**: the execution log shows **~13 of 18,018 executions** touch rename/apply/ratify (mutations are ~1000:1 rare), so a live shadow would learn chain-variety at a trickle while carrying the live-handler hazard continuously. *Creative:* B also blurs the milestone boundary — live shadow wiring is still a change to the live authority surface and risks the false perception that "graph apply is running live." Slice 4 proves the mechanism on captured chains; slice 5 exposes it to real traffic; slice 6 flips. Keep each milestone honest.

**The load-bearing refinement (DT) — A's corpus must be BROAD, or A is the n=1 trap again.** "Replay captured *ratified* chains" today means replaying ~a handful (the `30sec_edit 21` rename + a few). The compiler's entire risk is **chain variety** — multi-step chains, op mixes (`filter→foreach→commit`), Bug-D salvage text forms, clarification re-entries, empty/edge plans. A handful hides all of it (specimen-size-masks-divergence, now a 4th time after 2a n=1 · 2b n=1 · 2c independent-sink). **The dissolving move:** the compiler's input is `chain_steps`, which come from `compile_intent` — **non-mutating and abundant** (most of the 18k). So capture a **broad corpus of real model-emitted `chain_steps` offline** by driving `compile_intent` over many real intents — B's "compiler firing on real chains" signal, in A's safe offline posture. It's faithful because the live compiler input in `run_apply_branch` is a persisted ratified chain, which is a `compile_intent` output — the compile-capture corpus is a **superset**.

### Slice-4 success bar (converged — explicit)
1. **`chain_compiler` round-trips a BROAD corpus** of real model-emitted `chain_steps` (captured offline via `compile_intent`, non-mutating) — *not* "the `30sec_edit 21` chain round-trips." This is the bar; shipping on the ratified handful = the n=1 trap on the one component whose entire risk is input variety.
2. **The ratified handful** (`30sec_edit 21` +) proves **end-to-end** ratify → compile → graph-apply (`held` from edge) → `CommitNode.verify` → apply-once → **expected post-state**, parity-equal to legacy `run_chain_steps` replay.
3. **Live `run_apply_branch` unchanged** (legacy authoritative); `executor.py` byte-untouched; assent-token-ban green; `__all__` 19.

### Build delta from the seed's pass-to-code
- Add: **assemble the broad `compile_intent`-derived chain corpus** (extract real `chain_steps` from the execution log / drive `compile_intent` over logged intents; captured-not-assembled) — this is now a first-class slice-4 deliverable, not an afterthought.
- The two-tier oracle: corpus-wide **compiler round-trip parity** (does the compiled `GraphSpec` execute equivalently to legacy per chain) + the ratified handful's **end-to-end apply fidelity**.

### Remaining for DT at pass-to-code (mechanical, not open questions)
- Confirm the `[discover node] → commit node` edge faithfully carries the `mutation_plan` the way legacy threads `__previous_result__`; confirm `[rename → commit]` is the honest *minimal* end-to-end specimen while the broad corpus carries variety.
- Confirm held-from-edge keeps the assent-token-ban + executor byte-lock green after wiring the graph-apply entry point.
