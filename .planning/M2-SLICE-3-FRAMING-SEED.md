# M2 Slice 3 — Framing Seed (mutations / authority) — grounding for a cold draft

**Date:** 2026-06-18/19 · **Status:** SEED (grounding + open questions; the Orch *framing draft* with positions comes next, post-`/clear`).
**Base:** main `0d7fb61` (arc 2a/2b/2c closed). **Parents:** [[M2-SLICE-2-SEAM-DESIGN]] (slice 3 = "mutations/authority", deferred there) · the 2a/2b/2c pass-to-code docs.
**Purpose:** front-loaded grounding so a fresh context can draft the slice-3 framing immediately without re-grounding from zero. Read the cursor [[project_passoff_2026_06_19_a_m2_slice2c_merged]] first, then this.

## What slice 3 is
Bring **mutations** into the composition dispatch substrate **with the authority chain intact** — the same shape as 2a–2c (the graph primitive already exists; the slice admits/dispatches it through the composition executor + comparator), but mutations cross authority, so the careful part is preserving **preview → ratify → apply** and keeping **assent out of the executor**.

## Grounded surface map (what exists, where — verified 2026-06-18)
- **`graph/commit.py` — `CommitNode`**: "the substrate's first **host-mutating** primitive... the operator-ratified boundary where a previewed mutation may become applied. Verifies a **held** mutation manifest against a **freshly recomputed** one before the underlying mutation tool is allowed to apply." The tool's discover/verify/apply modes live underneath (e.g. `flame_rename_shots`); Commit ratifies that previewed == fresh at the authority crossing. **This is the slice-3 seam object.**
- **`graph/stage.py` — `StageNode`**: human-review terminus; collapses an assessment into a staged item; **never** emits a mutation manifest, never implies approval triggers action.
- **`graph/mutation.py` — `ChangeRecord`**: mutation manifest wire contract (`identity` + `payload`).
- **`core/assent.py`** — `AssentRecord` (the assent substrate). **`store/assent_record_repo.py`** — persistence.
- **`console/_chat_compile.py`** — `compile_intent()` → preview chain. **Ratify endpoint:** `POST /api/v1/ratify` + `fbridge ratify` (`cli/main.py`). Chain: NL → compile → `preview_emitted` → `AssentRecord` (proposed→ratified) → store-and-replay apply (v1.7 authority chain, shipped).
- **`tests/composition/test_m2_executor_invariants.py`** — the **assent-token-ban** invariant (executor source must contain no assent conduit) + the byte-untouched lock. Already green across 2a–2c. **Load-bearing for slice 3.**
- **Composition admission** (`composition/admission.py`): every op admitted so far is `no_state_mutation=True`, `idempotent_result=True`. **No mutating op is admitted yet** — slice 3 is the first.

## Inherited binding constraints
- **Executor untouched** — held across 2a/2b/2c. Question whether it holds for mutations (likely yes: Commit does verify-then-apply in a boundary; the executor just dispatches).
- **Assent-token-ban** — the executor must carry **no** assent conduit (already a tested invariant). Slice 3 is where this becomes load-bearing: ratify/assent lives in a boundary/harness **outside** the executor.
- **Doctrine (CLAUDE.md):** "mutations stay deterministic preview → ratify → apply with **no model prose anywhere near `AssentRecord`**." Reads may carry a model answer-pass; mutations may not. Assent stays the operator's.
- **Value-blind edges** (#86 unbound) — still holds.
- `len(forge_bridge.__all__)` stays **19**; writer's-room cadence; captured-not-assembled.

## Open framing questions (for the post-clear Orch draft to take positions on)
- **Q1 — authority chain ↔ graph dispatch.** How does preview→ratify→apply compose into the composition substrate? Does `CommitNode` dispatch through `UnifiedDispatch`, and **where does the ratify gate sit** so the orchestrator/model cannot cross it? (Commit's verify-held-vs-fresh is the mechanical gate; `AssentRecord` is the authority.)
- **Q2 — the parity oracle for a mutation.** You **cannot double-exec** a mutation (applying a rename twice isn't idempotent). So `compare_strategy_for` → **record_replay**, and the oracle is likely **self-consistency**, not cross-path double-exec: preview-determinism (held manifest == fresh recompute = Commit's verify) + apply-once. Probable third oracle-wall application — legacy has the preview/ratify/apply chain; graph must match it, but the *comparison* shape differs from reads.
- **Q3 — admission profile for a mutating op.** First op with `no_state_mutation=False`, `idempotent_result=False`. This breaks slice-1 admission assumptions (all current ops idempotent reads) — `compare_strategy_for` and the admission table must handle a mutating op. **Connects to #86** (side-effect-as-mutation): slice 3 makes `no_state_mutation` *real*, where 2c's deliverable op only flagged it provisionally.
- **Q4 — does executor-untouched hold?** Verify Commit's verify-then-apply lives in a boundary, not the executor; the assent-token-ban stays green. If a mutation forces an executor change, that's the first crack in the slice-2 reframe — surface it loudly.
- **Q5 — forcing specimen.** A real mutation op (`flame_rename_shots` is named in `commit.py`) through preview → ratify → apply. Captured-not-assembled. The "held vs fresh" verify needs a real previewed manifest + a real fresh recompute.

## First moves for the post-clear draft
1. Read `graph/commit.py` + `graph/stage.py` + `graph/mutation.py` in full (the seam objects).
2. Read the ratify chain end-to-end: `console/_chat_compile.py`, `core/assent.py`, `store/assent_record_repo.py`, the `/api/v1/ratify` handler, `cli/main.py ratify`.
3. Read `tests/composition/test_m2_executor_invariants.py` (the assent-ban + byte-untouched locks).
4. Read `composition/admission.py` + `composition/compare.py` `compare_strategy_for` (the record_replay path is selected-but-untested per slice-1 note — slice 3 likely exercises it for real).
5. Then draft the Orch framing with positions on Q1–Q5, lead with views, hand to the room (DT grounding / Creative experience) to redline. **Caution at this seam — it's where the operator's assent lives.**
