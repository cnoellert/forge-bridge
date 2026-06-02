---
milestone: v1.11
phase: SR.1
phase_name: Source-of-Truth Routing — coarse, by substrate (reads)
type: phase-plan
status: cycle-1-draft
drafted: 2026-06-01
derives_from: v1.11-SOURCE-ROUTING-FRAMING.md (ratified) + v1.11-DISCUSS.md (mechanism: sequence-ref-signal routing) + UAT/SR.1-T1-substrate-confirm.md (2/3 locked, candidate-set grounding)
mechanism: Door-(b) post-compile deterministic source-routing pass — operator-confirmed
grounding: live reads 2026-06-01 — _chat_compile.py:147-221 (run_compile_branch: user_prompt + compile_intent :166 + commit-node mutating branch :180-202 returns early + reads-execution run_chain_steps :203) ; router.py:647 (compile_intent → list[str] step strings) ; _step.py:148 (execute_chain_step sees step_text only, NOT the original prompt) ; _step.py:344 (resolve_required_params(message=step_text) — sequence_name resolves from step text) ; _tool_chain.py:216 (_resolve_sequence_name via 24.11) ; _tool_filter.py:264 (_NAMESPACE_PREFIXES flame/forge — the substrate axis)
---

# SR.1 — Plan (coarse source-routing for reads)

> Make a timeline-attribute read reach the substrate that holds its answer. T1 proved
> R8 (path) + R10 (duration) are answerable by `flame_get_sequence_segments` and that the
> dogfood mis-selected `forge_get_shot`. SR.1 adds a **deterministic post-compile pass**
> that, when the read carries a **sequence reference**, rewrites a forge-entity shot/segment
> step to the Flame timeline tool. Reads-only; DI.1 untouched; no model change; no map.

## What's done / what's out (from discuss + T1)

- **T1 DONE** — `UAT/SR.1-T1-substrate-confirm.md`. 2/3 reachable (R8/R10 via
  `flame_get_sequence_segments`; R9 timewarp = capability gap, carry-forward).
- **Mechanism (grounded, why not the discuss's "filter/narrow bias"):** the compiled step
  is `forge_get_shot`; `flame_get_sequence_segments` is dropped from the narrowed
  candidate set (and absent from the filter for natural phrasing). It is **not a candidate
  to prefer** — the mismatch is lexical. The signal is the **sequence reference**, which
  lives in the **original prompt**, not the compiled step (`execute_chain_step` never sees
  the prompt). So the fix is a **post-compile rewrite at the handler**, where both
  `user_prompt` and `steps` exist.
- **OUT of SR.1 (surface, don't resolve):** ordinal "shot 10" → which segment, and layer
  multiplicity (`tst_010` on L01+L02 …). `flame_get_sequence_segments` returns all
  segments; the answer-pass gets the data; segment-selection is a separate concern.

## Tasks

### T2 — the source-routing pass *(CODE — hand off)*

**File:** `forge_bridge/console/_chat_compile.py` (new helper) + a one-line hook in
`run_compile_branch`. Likely a new pure helper module `forge_bridge/console/_source_route.py`
(keep `_chat_compile` thin), exported for testing.

**New function (deterministic, pure, no LLM):**
```
def apply_source_routing(user_prompt: str, steps: list[str], tools: list) -> list[str]
```
Contract:
1. **Signal:** detect a **sequence reference** in `user_prompt`. Reuse the existing 24.11
   detection (`_resolve_sequence_name` / `resolve_query_entities`) in a *detect-and-extract*
   capacity — return the sequence reference substring/name if present, else `None`.
   *If `None` → return `steps` unchanged (fail-safe to current behavior).*
2. **Target steps:** for each step whose selected tool is a **forge-entity shot/segment
   read** (`forge_get_shot`, `forge_get_shot_stack/versions/lineage/deps`, `forge_list_shots`
   — `forge_*` namespace, shot/segment nouns), **rewrite** that step to a
   `flame_get_sequence_segments` step **that carries the sequence reference** (so the
   downstream `resolve_required_params(message=step_text)` resolves `sequence_name`). e.g.
   `"forge_get_shot"` → `"flame_get_sequence_segments <sequence_ref>"`. **Load-bearing:**
   the rewritten step text MUST contain the sequence reference, or `sequence_name`
   resolution fails (the step sees only its own text, not the prompt).
3. **Coarse, no map:** keyed on (sequence-ref present) × (forge-entity shot/segment tool).
   No per-attribute logic. `flame_*`/`forge_*` is the substrate axis (`_tool_filter.py:264`).
4. **Reads-only / boundary:** rewrite swaps one read tool for another read tool; it does
   NOT touch mutating tools, does NOT reinterpret intent, does NOT resolve which segment.

**Hook (one line):** in `run_compile_branch`, **immediately before** the reads execution at
`_chat_compile.py:203`:
```
steps = apply_source_routing(user_prompt, steps, tools)
chain_body = await run_chain_steps(steps=steps, ...)
```
Placed *after* the `if graph_contains_commit_node(steps): … return` block (`:180-202`), so
it is **reads-path only** — mutating/preview/ratify (Door C / ADR-003 territory) is
untouched.

### T3 — tests *(CODE — hand off)*

`tests/console/test_sr1_source_routing.py` (new). Unit (pure `apply_source_routing`):
1. sequence ref present + `forge_get_shot` step → rewritten to
   `flame_get_sequence_segments <ref>` (and `<ref>` present in the step text).
2. sequence ref present + `forge_list_shots` step → rewritten likewise.
3. **no sequence ref** in prompt → steps unchanged (fail-safe).
4. sequence ref present + a non-shot/non-forge step (e.g. `flame_list_desktop`) → unchanged.
5. **boundary:** a mutating step is never rewritten (reads-only).
Integration (optional, daemon): "what is the path to shot 10 on 30sec_edit 21" routes to
`flame_get_sequence_segments` and returns segments (R8/R10 reach the substrate).

### T4 — acceptance / live verify *(operator-driven, daemon)*

Re-drive R8/R10 against the loaded `30sec_edit 21`: they should route to
`flame_get_sequence_segments` and **return segment data** (answer-pass then summarizes),
instead of aborting at `forge_get_shot`'s `shot_id`. R9 still fails honestly (capability
gap). Record in `UAT/SR.1-acceptance.md`.

## Constraints (binding)

`__all__` stays **19** (the new helper is internal). No new libraries. **Reads-only** —
DI.1's gate untouched; mutating path (Door C) not entered. **Deterministic, no LLM, no
answerability map.** Fail-safe: no sequence ref → no rewrite → current behavior. Coarse
by substrate (`flame_*` vs `forge_*`), not per-attribute.

## Shape-locks (grounded, do not re-derive)

- Hook site = `_chat_compile.py:203` (reads path), after the commit-node branch (`:180-202`).
- `apply_source_routing` operates on `(user_prompt, steps, tools)`; `user_prompt` is the
  `run_compile_branch` arg (`:150`); `steps` is the compile output (`:166`).
- The rewritten step MUST carry the sequence reference (`resolve_required_params` resolves
  `sequence_name` from `step_text`, `_step.py:344`).
- Sequence detection reuses 24.11 (`_resolve_sequence_name` / `resolve_query_entities`,
  `_tool_chain.py:216`).

## Open implementation choices (operator's call while coding)

- **Sequence detection: sync vs async.** `_resolve_sequence_name` is async (may probe).
  If a lighter sync token-pattern detector suffices to *detect* a sequence reference
  (extraction can be coarse), prefer it to keep `apply_source_routing` pure; else thread
  the async detection. *Lean: sync detect-and-extract; the exact `sequence_name` still
  resolves downstream.*
- **Which forge-entity tools trigger rewrite.** Start with the `forge_get_shot` family +
  `forge_list_shots`; widen only if a read demonstrably needs it (measure-first).

## Status

**Cycle-1 plan, 2026-06-01.** Mechanism grounded to a deterministic post-compile pass at
`_chat_compile.py:203` (reads-only). T1 done; T2 (pass + hook) + T3 (tests) are the code
handoff; T4 is operator live-verify. Boundary held: reads-only, no map, no reinterpretation,
DI.1 untouched, segment-selection out of scope. Ready for code implementation.
