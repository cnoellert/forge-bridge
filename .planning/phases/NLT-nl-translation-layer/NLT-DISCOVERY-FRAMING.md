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

**✅ The seam HOLDS — path-dependent (D1/D2 grounded, DT; the spine survived).** The straddle caveat was
right, and it does not threaten the spine:
- **Mutations: graph-as-boundary HOLDS — LOCK IT.** D2 confirmed defect #3's wrong value (`30sec_21`) was
  in the *compiled graph* before ratification; the dispatch resolver (`_step.py:568`) never ran (we never
  ratified). Resolution + compile complete *pre-graph* for the mutation/preview path, so the chain-step
  graph IS the translation/substrate contract — exactly what E2E-01 demonstrated (wrong values visible at
  the seam, substrate would have executed faithfully).
- **Reads: the boundary straddles — DOCUMENT the completion point.** Reads carry unresolved `step_text` and
  resolve at dispatch (`_step.py:568`), so for reads the graph is *not* fully resolved. Phase 1 defines the
  reads completion point rather than pretending the graph is the whole contract.

Don't force one rule across two execution models. The reframe survives for the path C2 exercises.

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

Apply `[[feedback-routing-vs-implementation-vs-reachability]]` *inside* translation. E2E-01's three defects
landed in **three different classes** (D1/D2 grounded) — strong vindication of "don't assume they share a fix":

| E2E-01 defect | Class (post-grounding) | Grounded finding |
|---|---|---|
| `prefix → "noise"` | **grounding / example-salience** (translated-wrong) | LLM lifted `timeline.py:215/243` field example; `[[feedback-rhetorical-position-as-architectural-control-surface]]`. (Unchanged — the only defect that stayed where framed.) |
| explicit `"prefix 013" → tool_unresolved` | **routing + extraction** (NOT compile-binding) | D1: log shows `tool_forced` `tools_filtered=1`, `wall_clock_ms=0`, *no ollama-compile* — "prefix" narrowed to 1 tool → **PR20 forced-execution shadowed compile** (`compile_intent` never ran) → `extract_explicit_params` couldn't parse space-separated `"prefix 013"` (key, no value). The "compile-binding" cell is **vacated**. (PR20-shadows-compile = the same seam DT flagged as the C2-reachability risk.) |
| `30sec_edit 21_publish → 30sec_21` | **contextual-resolution gap** (NOT entity-resolution / NOT SR.1-reuse) | D2: the mangle is at COMPILE time (in the graph; `_step.py:568` never ran). Not a resolver mangle and not "reuse SR.1's resolver" (the shared resolver parses *text*, and the open-sequence name is never *in* the text). Nothing injects the currently-open Flame sequence into compile context → LLM fills `sequence_name` from the docstring example. **= Q1, confirmed real + distinct + load-bearing.** |

Candidate full taxonomy: grounding · **routing** · **extraction** · entity-resolution · **contextual/stateful
resolution** failures. (Phase 2 formalizes; the three E2E-01 defects already populate three cells.)

---

## Verification doctrine — RATIFIED by the room, adoptable now (the free half)

> **"substrate-pass + translation-open"** — emit translation-pass and substrate-pass as *simultaneous,
> independent* verdicts; stop auto-interpreting chat failures as substrate/architectural failures.

E2E-01 is the cleanest proof: old reading "rename failed"; accurate reading "translation failed, substrate
passed." A coarser generalization of the routing/impl/reachability triad; costs nothing; removes enormous
noise from every future investigation. DT + Creative ratified; **PROMOTED to methodology memory**
`[[feedback-substrate-pass-translation-open]]` (2026-06-02).

---

## Motion shape (Creative's 4 phases; measure-first-gated)

1. **Formalize** — inventory the existing translation machinery (table above) + establish the contract
   boundary. **Lead question RESOLVED (D2):** chain-step graph IS the boundary for **mutations** (lock);
   for **reads** it straddles → document the dispatch completion point. Don't force one rule across both.
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

## Discovery's first actions

- **D1 — DONE (DT).** Defect #2 = PR20-shadows-compile (routing) + `extract_explicit_params` parse fail
  (extraction); NOT compile-binding. Log: `tool_forced` `tools_filtered=1` `wall_clock_ms=0`, no compile line.
- **D2 — DONE (DT).** Defect #3 = contextual-resolution gap at compile time; graph-as-boundary holds for
  mutations, straddles for reads. Spine confirmed. (Enriched compile-input = optional later evidence for the
  *fix*, NOT a Phase-1 blocker — room consensus.)
- **D3 — PENDING (bridge-side, Orch lane):** example-salience inventory — enumerate liftable examples across
  the mutation tool field descriptions (defect #1 is one instance of a class). Feeds Phase 4's grounding slice.

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
- **Q1 — ANSWERED (D2): yes, a distinct class.** Contextual/stateful resolution ("currently open sequence",
  "last 013 shot", "the current project", "the active timeline") = *state-reference* problems needing
  runtime world-state injected into compile *before* graph formation — distinct from grounding / routing /
  extraction / static entity-resolution. Defect #3 is its evidence (moved theory → grounded). Gets its own
  taxonomy cell + a resolution site that feeds compile. Adjacent to the R7 session-scope carry-forward +
  DI.2's dormant context-eligibility seam. (Creative's "Layer A = world-model construction" lives here.)
- **Q2 — uncertainty representation depth.** Today the *only* uncertainty surface is the preview/ratify gate
  (it caught `noise`). Is "represent uncertainty / carry candidate meanings *before* preview" a first-
  milestone slice or a later maturation? This is where the monolith risk concentrates — keep it gated.
