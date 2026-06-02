# TF.1 — Formalize (PLAN)

**Milestone:** v1.13 Translation Fidelity, Phase 1 of 4. **Discuss:** `TF.1-DISCUSS-reads-contract.md`
(resolved — compile-resolved vs context-resolved axis; Shape-A coupling; integrity invariant).
**Foundation:** `NLT-DISCOVERY-CLOSE.md`. **Handoff:** writing-room authors the contract/inventory docs;
operator implements the audit's lock test.
**Invariants:** `forge_bridge.__all__` stays **19**; no new external libraries; ruff clean. Formalize phase —
near-zero production code (one regression test at most); **no behavior change**.

---

## What Phase 1 delivers

Formalization, not fixes: the contract Phases 2–4 build on. Three deliverables — two authored docs + one
grounded audit that locks an invariant. Discovery pre-delivered the substance (inventory, axis, taxonomy
seeds); TF.1 ratifies it into a contract and verifies the one integrity claim that keeps "graph IS the
contract" honest under dispatch-time resolution.

---

## Tasks

### T1 — Ratification-integrity audit (the load-bearing verification)

**Invariant to verify:** *dispatch may resolve refs the graph left unresolved (contextual → concrete); it
may NEVER override a param the operator explicitly ratified.*

**Grounded starting point (already read):** the dispatch merge is `merged = {**public_inherited,
**semantic_params, **user_params}` (`_step.py:261`), where `user_params = extract_explicit_params(step_text)`
(`:253`, the explicit step args) and `semantic_params = _extract_semantic_step_params(step_text)` (`:254`,
the resolver projections). **user_params is last → explicit wins.** So the invariant *appears to hold by
merge order*: semantic resolution fills only keys the explicit text omitted; explicit-ratified params are
not overridden. T1 confirms the full picture and locks it.

**Audit method (confirm, don't assume — `[[feedback-ground-specs-in-actual-files]]`):**
1. Precise the definition: **"explicitly ratified" ≡ `extract_explicit_params(ratified_step_text)`** at
   apply (run_apply_branch replays the ratified `chain_steps`). Verify that's the set that occupies the
   winning `user_params` position on the replay path, not just the live-chat path.
2. Check the **`project_name` special-case** (`:262-263`: pulled out of `merged`, `resolver_input` excludes
   it) — does it follow the same explicit-wins rule, or is it an exception that could let a resolved
   project_name override a ratified one?
3. Check edge shapes: dict/nested params (e.g. `role_overrides`), and any key where `semantic_params` and
   `user_params` could collide on a sub-structure rather than a whole key.
4. **Verdict + lock:** if the invariant holds (expected), the operator adds a regression test —
   `tests/console/` — constructing a ratified step with an explicit param `P=X` **and** a
   semantic-resolvable unresolved ref, replaying it, asserting `P==X` (explicit wins) **and** the ref
   resolved (unresolved filled). If it does NOT hold for some shape, **document the gap** as a Phase-4 fix +
   flag the Shape-A integrity risk — do not fix in TF.1 (formalize phase).

*(Audit = grounding, writing-room/Orch can run it; the lock test = operator code. Audit gates the contract's
integrity clause — run it before T2 finalizes that clause.)*

### T2 — `TF.1-CONTRACT.md` (writing-room authors)

The formal translation/substrate contract Phases 2–4 reference:
- **Axis:** compile-resolved (chain-step graph IS the full contract) vs context-resolved (two-point: graph
  captures intent + dispatch resolves), cutting across reads **and** mutations.
- **Context-resolved two-point contract:** what each point owns; how a context-resolved param is recognized
  *as* unresolved at compile (definition only — *detection mechanism is Phase 2/4, not here*).
- **Shape-A coupling clause:** resolving a contextual mutation target post-ratify is Shape A; a
  contextual-mutation preview shows an unresolved ref; desktop-at-compile is the Shape-B-era prerequisite.
- **Integrity invariant clause:** the T1 invariant, with its grounded definition ("explicitly ratified" =
  `extract_explicit_params` output) and the `:261` merge as its enforcement point.
- Refines (does not rewrite) the `NLT-DISCOVERY-CLOSE.md` reads/mutations framing → contextuality-based.

### T3 — `TF.1-INVENTORY.md` (writing-room authors)

Bound the translation layer: name each component, its role, its resolution lifecycle point, and its axis
side. Grounded seed (confirm counts — archaeology-grade):
`compile_intent` (`router.py:647`) · `filter_tools_by_message` + `deterministic_narrow` (`_tool_filter.py`)
· `resolve_query_entities` (`resolver.py:59`; enrich `handlers.py:1657` + dispatch `_step.py:568`) ·
`extract_explicit_params` (`_param_extract.py:87`) · `apply_source_routing` (SR.1) · `apply_executor_routing`
(C2). Mark which resolution points are compile vs dispatch (the straddle map), and the unwired `desktop`
param (`resolver.py:61`) as the context-resolution enablement gap.

---

## Acceptance (goal-backward)

- `TF.1-CONTRACT.md` + `TF.1-INVENTORY.md` exist and are room-reviewed; the contract is organized on the
  compile/context axis with the Shape-A + integrity clauses first-class.
- T1 audit has a **verdict**: invariant holds → regression test locks it (suite green, `__all__`==19); or a
  gap is documented + routed to Phase 4 with the Shape-A risk flagged.
- No behavior change; no fixes shipped (those are Phase 4); no detection mechanism built (Phase 2/4).

## What this plan does NOT do

- **No contextual-reference detection / handling** — defining the axis is TF.1; *recognizing* a param as
  context-resolved and *wiring `desktop`* is Phase 2 (taxonomy) / Phase 4 (the fix).
- **No oracle, no corpus, no example-fill detector** — Phase 3a.
- **No quality fixes** (example-strip, PR20-shadow, contextual injection, provenance signal) — Phase 4.
- **No Shape B** (desktop-at-compile / ratify-concrete-target) — deferred future motion; TF.1 only records
  the coupling so Shape B inherits it.
