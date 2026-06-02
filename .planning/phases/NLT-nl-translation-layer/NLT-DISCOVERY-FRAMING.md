# Natural-Language Translation Layer — Discovery & Framing

**Type:** discovery + framing motion (produces a decomposed, ranked set of slices — NOT a build plan).
**Origin:** the E2E-01 param-resolution defect (live on `013_…portofino`), reframed by the room from
"param fix" to "getting human language into the substrate correctly."
**Cadence:** writing-room authors framing/discuss/plan; operator implements. This doc opens the motion.

---

## Thesis

C2's live E2E proof (E2E-01: real timeline, zero mutation, ratify gate held) relocated the frontier.
**The substrate is now trustworthy; execution is solved (Layer C); the weak point is the path from
human language into the substrate.** The room reads E2E-01 not as "rename failed" but as: C2 succeeded,
safety succeeded, ratification succeeded, routing succeeded, preview succeeded — **only param resolution
failed, and the preview caught it and refused.** That is the machinery working as designed.

The trap is to fix the three E2E-01 symptoms as a local "param-resolution patch." They are three faces of
one class — turning a sentence into a correct, grounded substrate operation — and patching the noise bug
alone leaves wrong-sequence / wrong-version / wrong-shot / wrong-asset standing: the same disease, different
symptoms. This motion frames the **class**, then decomposes and ranks it. (Operator/Creative reframe.)

---

## The three layers (grounded to live code)

| Layer | What | Where it lives today | Status |
|---|---|---|---|
| **A — Entity resolution** (world-model construction) | "013" → project; "last 013 shot" → highest matching; `30sec_edit 21` → the real sequence | `llm/resolver.py::resolve_query_entities` (`:59`) + `enrich_messages_with_resolved_entities`; wired at `handlers.py:1655-1663` and `_step.py:564/925/999/1064` | **machinery exists, partially hardened by SR.1; coverage at mutation-compile UNVERIFIED** |
| **B — Intent translation** (interpretation) | "rename with prefix 013, start next" → `forge_apply_rename prefix=013 start=N` | `router.compile_intent` (`router.py:647`) + `_param_extract.extract_explicit_params` (`:87`); param values authored by the LLM from tool field descriptions | **the dominant E2E-01 failure surface** |
| **C — Deterministic execution** | `forge_apply_rename → commit → ratify → apply` | C2 (`_executor_route.py`, `_step.py:771-899`) | **SOLVED — E2E-01 proved it** |

The motion's working hypothesis: **A and B have been collapsed into one "param-resolution" bucket; they
fail differently and want different fixes.** Discovery's first job is to separate them on evidence.

---

## The E2E-01 defects mapped (grounded; one premise flagged for pinning)

1. **`prefix → "noise"`** — Layer **B**. The LLM lifted a tool field-description *example*
   (`timeline.py:215` / `:243` `prefix: Field(..., "e.g. 'noise', 'tst'")`; reinforced by the literal
   operator-query example at `:286`) instead of deriving from intent. Surface = description-layer
   example-salience (`[[feedback-rhetorical-position-as-architectural-control-surface]]`).
2. **explicit `"prefix 013"` → `tool_unresolved`** — Layer **B**, sub-layer UNCONFIRMED. The literal word
   "prefix" flips compile from bind → bind-nothing → likely a `compile_intent`-binding failure, distinct
   from param-fill. **Pin via log-glance** (compile-output vs filter-ambiguity vs validation-reject;
   `tools_filtered=2` on the resolving turn) before scoping.
3. **`30sec_edit 21_publish → 30sec_21`** — Layer **A**. ⚠ **GROUNDING-FLIP CAUGHT:** DT's cursor framed
   this as "mutation didn't inherit SR.1's resolver → reuse it." But SR.1's qualified-name fixes
   (`4912e3b`, `9f24fde`) touched **both `_source_route.py` AND the shared `llm/resolver.py`** — and the
   mutation compile path *does* use that shared resolver. So the resolver was hardened; "reuse SR.1's
   resolver" rests on a false premise. The real gap is either **routing** (mutation compile binds the
   sequence without calling the resolver at that point — `[[feedback-routing-vs-implementation-vs-reachability]]`)
   or an **uncovered case** (the `_publish`-suffix / mixed-separator mangle SR.1 didn't cover). **Pin
   which before scoping** — this is the canonical "even the obvious fix flips under grounding" case.

So the defects already distribute across **A and B**, validating "class, not patch."

---

## Discovery questions (the room's 7 — each pointed at where it gets answered)

1. **What must be extracted before deterministic routing begins?** — inventory against `compile_intent`
   inputs + `resolve_query_entities` output shape.
2. **What belongs to entity resolution (A)?** — vs B; the boundary the resolver already draws.
3. **What belongs to intent interpretation (B)?** — vs A; what the LLM authors vs what's resolved.
4. **What belongs to deterministic execution (C)?** — closed (C2); the boundary is the contract.
5. **Where do examples and descriptions participate?** — defect #1; inventory liftable examples across
   tool field descriptions (`timeline.py`, `publish.py`, `staged.py`, …).
6. **How do candidate meanings get represented?** — does the system carry alternatives, or commit early?
   (`resolve_query_entities` returns `{value, source}` — single, not ranked.)
7. **How does Bridge know uncertainty exists?** — the deepest question: today the preview/ratify gate is
   the *only* uncertainty surface (it caught noise). Is uncertainty representable *before* preview?

---

## Discipline guardrail (what keeps "highest leverage" from becoming "never ships")

This motion **decomposes → ranks → measure-first-gates** (DI.2 pattern), producing the **smallest useful
slices** with evidence behind each. It does NOT authorize a monolithic "build the translation layer." The
room's track record is that grounding *shrinks* scope (C2 got smaller; DI.2 T4 was gated out). The failure
mode of a grand framing is that it never lands — the antidote is shipping slices ranked by the live defect
distribution. Candidate smallest-first slice (pending the #3 grounding): if it's an uncovered resolver
case, extend the shared resolver; if it's a routing gap, wire the resolver into the mutation compile
binding — either is a contained slice, not a layer rebuild.

---

## Discovery's first actions (grounding before scoping)

- **D1 — log-glance** the E2E-01 run to pin defect #2's sub-layer (compile-binding vs filter vs validation).
- **D2 — pin defect #3:** trace the mutation compile sequence-binding path — does it call
  `resolve_query_entities` at the binding point? Is `_publish`/mixed-separator an uncovered resolver case?
  (Routing-gap vs uncovered-case decides the fix.)
- **D3 — example-salience inventory:** enumerate liftable examples in tool field descriptions across the
  mutation tool surface (defect #1 is one instance of a class).

These three produce the evidence; the evidence produces the ranked decomposition.

---

## Scope boundaries

- **IN:** Layers A + B discovery, grounded against the E2E-01 defects → ranked slice decomposition.
- **DEFERRED:** **Shape B** (manifest-ratification, Window-2 drift). E2E-01 gives live evidence to rank it,
  and getting language→substrate correct is the more pressing pain than preview→apply drift. Likely
  demoted below NLT slices — confirm at decomposition.
- **OUT:** Layer C (done); the bootstrap-console-executor-gap (operational, separate); publish executor
  (own motion).

---

## Open framing questions

- **Q0 — milestone placement.** This is milestone-scale and reshapes the roadmap. Options: (a) opens a new
  milestone (NL Translation), with v1.12 closing on C2 as delivered + Shape B deferred forward; (b) folds
  into v1.12 alongside Shape B. Lean: (a) — NLT is the dominant frontier and Shape B's deferral wants to be
  explicit, not buried. Decide after discovery ranks the slices (don't pre-commit the milestone shape to an
  unmeasured scope).
- **Q1 — uncertainty representation (question 6/7) depth:** is "carry candidate meanings + surface
  uncertainty pre-preview" in scope for the first milestone, or a later maturation? (Risks the monolith if
  taken whole.)
