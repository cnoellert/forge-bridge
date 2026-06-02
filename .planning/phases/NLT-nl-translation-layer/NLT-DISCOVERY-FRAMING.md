# Natural-Language Translation Layer — Discovery & Framing

**Type:** discovery + framing motion → produces a decomposed, ranked, measure-first-gated set of slices.
**Origin:** the E2E-01 param-resolution defect (live on `013_…portofino`), reframed by the room.
**Status:** framing — DT + Creative ratified the reframe (this revision folds both). Cadence: writing-room
authors framing/discuss/plan; operator implements.

---

## Thesis (revised per DT + Creative — formalize, do NOT build)

C2's live E2E proof relocated the frontier: the substrate is trustworthy, execution is solved (Layer C),
and the weak point is the path from human language into the substrate. **But the translation layer is not
missing — it already exists, scattered and implicit, and is running today.** `compile_intent` (NL→graph),
`filter_tools_by_message` + `deterministic_narrow` (capability), `resolve_query_entities` (entity),
`extract_explicit_params` (param), `apply_source_routing` / `apply_executor_routing` (routing) — those *are*
the translation layer. We accidentally built one without recognizing it as a first-class subsystem.

So the motion is **promote the existing scattered machinery to first-class — name it, bound it, give it an
output contract, validate it independently** — NOT a greenfield Intent-Translation-Layer build. The
distinction is load-bearing: "introduce a new component" invites a rewrite of battle-tested pieces (the most
respectable form of infra regression — `[[feedback-brief-examples-as-behavioral-reference-shapes]]`);
"formalize what's there" keeps the working topology and hardens the weak spots.

The trap to avoid is the inverse symmetric error: a "param-resolution patch" that fixes `noise` and leaves
wrong-sequence / wrong-version / wrong-shot / wrong-asset standing — same disease, different symptoms.

---

## The boundary object already exists — formalize it, don't invent an IR

The "Resolved Intent" artifact does not need inventing: it is the **compiled chain-step graph**
(`compile_intent` output → what `run_chain_steps` consumes → what the `AssentRecord` stores/replays).

> **Translation** = Natural Language → chain-step graph.  **Substrate** = chain-step graph → execution.

E2E-01 validated the substrate side and exposed the translation side across **exactly that seam** (the graph
shape `forge_apply_rename → commit` was correct; the substrate executed faithfully; the defect lived in how
the graph was produced). Introducing a new `ResolvedIntent`/`IntentIR` between translation and the graph
would mint a second boundary to maintain with no evidence we need it (Creative). **Don't.**

**⚠ The seam is a HYPOTHESIS, not yet a fact — the lead Phase-1 question (grounded).** The chain-step graph
currently *straddles* the boundary: entity resolution runs both **pre-compile** (`handlers.py:1655` enrich)
AND **at dispatch** — `_step.py:568` does `resolved_entity_params(resolve_query_entities(step_text))` on the
*stored* step text. So the graph carries *unresolved* references that resolve at execution. If defect #3
(sequence mangle) occurs at dispatch-time resolution, it is a **translation-class failure on the substrate
side of the proposed seam** — which would falsify "graph-correct ⇒ translation-passed." Phase 1 must confirm
the graph *is* the contract, or define where resolution completes (consolidate-up vs contract-at-each-site —
DT's caution 1, made precise). **Defect #3's pin (D2) is the probe.**

---

## Layer reconciliation (fold into the existing model, don't mint a parallel one)

Translation **subsumes** the "arbitration" layer that `[[project-three-architectural-layers]]` already names
as the frontier (Translation ⊃ arbitration: it adds the NL front-end + entity resolution + grounding on top
of tool-arbitration). The reconciled model is one widening, not a competitor:

> **surfaces → translation (incl. arbitration) → substrate**

(The A/B/C cut from the prior draft — entity resolution / intent translation / deterministic execution —
becomes *substructure within translation*, useful for sorting failures, not a separate scheme.)

---

## Existing translation machinery (Phase-1 inventory seed, grounded)

| Activity | Where | 
|---|---|
| NL → chain-step graph | `router.compile_intent` (`router.py:647`) |
| capability resolution | `filter_tools_by_message` + `deterministic_narrow` (`_tool_filter.py`) |
| entity resolution | `resolve_query_entities` (`resolver.py:59`); enrich `handlers.py:1655`; **also dispatch `_step.py:568/925/999/1064`** |
| param extraction | `extract_explicit_params` (`_param_extract.py:87`) + dispatch resolver |
| routing | `apply_source_routing` (SR.1) · `apply_executor_routing` (C2) |
| forced-execution (pre-compile) | PR20 path (`handlers.py:1794`) — resolution *before* compile |

This is what Phase 1 names and bounds. (Note: resolution appears at ≥3 lifecycle points — the distribution
DT's caution 1 flags.)

---

## Translation failure taxonomy (recursive triad; Phase-2 seed)

Apply `[[feedback-routing-vs-implementation-vs-reachability]]` *inside* translation. E2E-01 already exhibits
distinct classes that do NOT share a fix:

| E2E-01 defect | Class | Sub-finding |
|---|---|---|
| explicit `"prefix 013" → tool_unresolved` | **failed to translate at all** (compile-binding) | sub-layer UNCONFIRMED → **D1 log-glance** |
| `prefix → "noise"` | **translated to the wrong thing** (grounding / example-salience) | LLM lifted `timeline.py:215/243` field example; `[[feedback-rhetorical-position-as-architectural-control-surface]]` |
| `30sec_edit 21_publish → 30sec_21` | **translated to the wrong thing** (entity-resolution) | ⚠ grounding-flip: SR.1 hardened the *shared* resolver (`4912e3b`/`9f24fde` touched `llm/resolver.py`), so "reuse SR.1's resolver" is a false premise → routing-gap vs uncovered-case → **D2** |

Candidate full taxonomy: binding · grounding · entity-resolution · extraction · routing failures (Creative).

---

## Verification doctrine — RATIFIED by the room, adoptable now (the free half)

> **"substrate-pass + translation-open"** — emit translation-pass and substrate-pass as *simultaneous,
> independent* verdicts; stop auto-interpreting chat failures as substrate/architectural failures.

E2E-01 is the cleanest proof: old reading "rename failed"; accurate reading "translation failed, substrate
passed." A coarser generalization of the routing/impl/reachability triad; costs nothing; removes enormous
noise from every future investigation. DT + Creative both ratify *now*. → candidate methodology memory
(promotion-grade; pending operator go-ahead, see end).

---

## Motion shape (Creative's 4 phases; measure-first-gated)

1. **Formalize** — inventory the existing translation machinery (table above) + establish the chain-step
   graph as the translation/substrate contract boundary. **Lead question: does the graph hold as the
   boundary, or does resolution straddle it?** (D2 / defect #3 is the probe.)
2. **Taxonomy** — define the translation failure taxonomy (binding / grounding / entity-resolution /
   extraction / routing). Don't assume the three E2E-01 defects share a fix.
3. **Validation** — independent translation-pass / substrate-pass as *separately measurable* outcomes
   against the graph contract. **Gates Phase 4** (can't improve what you can't measure — measure-first).
4. **Quality** — improve translation using the taxonomy + validation, shipped as **evidence-ranked smallest
   slices**, not a layer rebuild. (E.g. strip liftable examples; extend/wire the resolver per D2's verdict.)

**Discipline guardrail (binding):** decompose → rank → measure-first-gate; smallest useful slices; reject the
monolith. The room's record is that grounding *shrinks* scope (C2 got smaller; DI.2 T4 gated out). The
failure mode of a grand framing is that it never lands — Phase 3 before Phase 4 is the antidote.

---

## Discovery's first actions (grounding before scoping — feed Phase 1)

- **D1 — log-glance** the E2E-01 run: pin defect #2's sub-layer (compile-binding vs filter vs validation).
- **D2 — pin defect #3 + the seam:** trace the mutation compile sequence-binding path. Does resolution run
  at compile or dispatch? Routing-gap vs uncovered-resolver-case? **This also answers whether the chain-step
  graph holds as the boundary object.**
- **D3 — example-salience inventory:** enumerate liftable examples across the mutation tool field
  descriptions (defect #1 is one instance of a class).

D1/D2 live on the host/infra surface (E2E-01 logs + live source) — DT's grounding lane.

---

## Scope boundaries

- **IN:** formalize + validate the existing translation layer against the chain-graph contract (Phases 1–3);
  evidence-ranked quality slices (Phase 4).
- **DEFERRED:** **Shape B** (manifest-ratification, Window-2 drift) — live evidence now exists to rank it;
  language→substrate correctness is the more pressing pain. Likely demoted below NLT — confirm at decomp.
- **OUT:** Layer C / substrate (done); bootstrap-console-executor-gap (operational, separate); publish
  executor (own motion).

---

## Open framing questions

- **Q0 — milestone placement.** Milestone-scale; reshapes the roadmap. Lean: opens a **new milestone (NL
  Translation)** with v1.12 closing on C2 delivered + Shape B deferred forward — decide after Phase-1
  inventory sizes it (don't pre-commit the milestone to unmeasured scope).
- **Q1 — contextual/stateful resolution as a distinct sub-class.** "currently open sequence", "last 013
  shot" need *world state*, not just NL — distinct from static entity resolution, and adjacent to the R7
  session-scope carry-forward + DI.2's dormant context-eligibility seam. Does the taxonomy (Phase 2) carry a
  **contextual-resolution** class? (Creative's "Layer A = world-model construction" lives here.)
- **Q2 — uncertainty representation depth.** Today the *only* uncertainty surface is the preview/ratify gate
  (it caught `noise`). Is "represent uncertainty / carry candidate meanings *before* preview" a first-
  milestone slice or a later maturation? This is where the monolith risk concentrates — keep it gated.
