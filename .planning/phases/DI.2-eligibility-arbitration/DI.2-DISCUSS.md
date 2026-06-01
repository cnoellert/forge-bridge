---
milestone: v1.10
phase: DI.2
phase_name: Eligibility Arbitration — make routing resolve instead of hard-stop
type: phase-discuss
status: ratified
drafted: 2026-06-01
derives_from: .planning/phases/DI.2-eligibility-arbitration/DI.2-FRAMING.md (cycle-3, sized ≤3/9) + .planning/milestones/v1.10-DISCUSS.md (Q-DI2 → concrete hook)
artifact_role: resolves the framing's Q-DI2.1..Q-DI2.5 against live code; sequences the capture fix FIRST; reduces the five framing deliverables to a buildable, measurement-gated ladder. Feeds DI.2-PLAN.
grounding: live reads 2026-06-01 — _tool_filter.py:338-362 (exact/other buckets + cap-combine return :362; substring-exact :344, token-complete-subset :349); _step.py:255 (filter call) → :263-266 (deterministic_narrow) → :314-328 (divergence emit, fires BEFORE) → :330-341 (tool_selection_ambiguous + candidate leak) → :342 tool_name → :415 dispatch_authority (DI.1 gate); handlers.py:1752 (chat-handler capture site); corpus/_capture.py:197 (FORGE_BRIDGE_DIVERGENCE_CAPTURE) + :221 (enabled(), read at call time, daemon-restart to flip)
---

# DI.2 — Eligibility Arbitration — Discuss (resolutions + buildable ladder)

> Compact per [[feedback-cadence-artifacts-shrink-to-load-bearing]]. The framing
> ratified the boundary (arbitration, not recompilation) and *sized* the phase
> (≤3/9, contingent). This artifact grounds the five Q-DI2.x against live code,
> sequences the capture fix first, and collapses the five framing deliverables
> into one measurement-gated ladder so the plan builds only what the data
> justifies.

## The enabling finding (grounded this session)

**The capture fix is flip-and-rerun, not code — and the divergence instrument
already records exactly the field that classifies (a) vs (b).** `_step.py:314-328`
emits `emit_divergence_capture(prompt=step_text, candidate_set_post_pr14=…,
narrower_decision=filtered, …)` whenever `divergence_capture_enabled()`, and it
fires **before** the `tool_selection_ambiguous` return at `:330` — the comment
block (`:298-312`) states ambiguity rejection is recorded verbatim, including the
multi-match path. The gate is a single env var (`FORGE_BRIDGE_DIVERGENCE_CAPTURE`,
`corpus/_capture.py:197/221`, read at call time → daemon restart flips it). The
chat-handler call site (`handlers.py:1752`) covers the forced/preview routes the
chain-step site doesn't. So harvesting real candidate sets needs **zero new
code** — and `(compiled step_text, candidate_set)` per row is precisely the pair
that tells resolver-overmatch (a: right operation, N tools) from bad-compile
(b: wrong operation) apart.

## Resolutions

- **Q-DI2.5 — measurement. RESOLVED: sequence FIRST, flip-and-rerun, zero code.**
  Set `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1` (+ `FORGE_BRIDGE_CORPUS_DIR`) on a
  **non-degraded** `:9996` daemon (the cursor's degraded-model caveat — record
  model + daemon provenance alongside, [[feedback-provenance-precedes-behavioral-interpretation]])
  and re-run the 11 dogfood reads. Harvest `candidate_set_post_pr14` +
  `narrower_decision` from the **divergence** corpus only — *read the existing
  instrument for measurement, never merge it into the comprehension schema* (the
  CLAUDE.md don't-couple constraint holds: two instruments, named distinctly
  forever). Output: the (a)/(b)/other split becomes reproducible against real
  sets, "≤3/9" stops being ledger-grounded. **This is task 1 of DI.2 and it
  *gates* deliverable 3 below** — we do not build an LLM-in-resolver path until
  the data shows deterministic rules can't reach the residual (a) cases. *This is
  the measurement-debt pattern finally paying forward instead of in retrospect.*

- **Q-DI2.1 — exact-name-wins. RESOLVED + grounded to a ~3-line change.** In
  `filter_tools_by_message`, before the cap-combine at `:359-362`:
  `if len(exact_matches) == 1: return exact_matches` (drop `other_matches`
  entirely). Today `:362` returns `exact_matches + other_matches[:remaining]` —
  exact matches have *survival* precedence but not *exclusivity*, which is why
  typing `flame_set_start_frames` yields 1 substring-exact + ~8 token-overlap
  others = the 9. **Multi-exact (≥2) falls through** to the current combine →
  `deterministic_narrow` → ranking (genuine ambiguity, arbitrate; do not
  collapse). **Plan-time flag (DT):** the `exact_matches` bucket conflates two
  match kinds — substring-exact (`:344`, the "operator typed the literal name"
  *trust* case) and token-complete-subset (`:349`, the NL "set start frames"
  case). The exclusivity rule covers both; the test matrix must prove **both
  kinds resolve exclusively when unique AND both fall through when ≥2.** This is
  the highest-leverage fix and it is what unblocks DI.1's live demo (the request
  now reaches `_step.py:415`'s gate instead of dying at `:330`).

- **Q-DI2.2 — LLM selection budget. RESOLVED (operator-ratified cycle-2):
  contingent, kept — not fully deferred.** *Why kept (operator/Creative): a
  pure-deterministic DI.2 reads clean but risks another "we protected the boundary
  and left the user stuck" milestone. A bounded LLM pick among already-resolved
  candidates is still **arbitration**, not recompilation — it belongs in an
  eligibility-arbitration phase.* **The governing invariant:** *the LLM may choose
  among known candidates; it may not create a new candidate.* It is a
  *pick-one-from-set* selection, **not** the orchestration loop — control-flow,
  never meaning ([[feedback-orchestrator-control-flow-not-meaning]]). The seven
  guardrails (binding, all must hold):
  1. Fires **only after rungs 2+3 fail** to resolve (runtime ordering).
  2. **Only** when the candidate set is bounded (≤5).
  3. **Only** over candidate tools the resolver already produced.
  4. **No new tool invention.**
  5. **No fresh interpretation** of the original request beyond choosing among
     the candidates.
  6. **Timeout-bounded** (reuse the existing router per-tool cap; no new knobs).
  7. **Captured for corpus review** — the selection is itself a new arbitration
     decision and must emit to the **divergence** corpus (a versioned schema
     extension to `narrower_decision`/`ambiguity_state`, *not* a comprehension
     touch — don't-couple preserved). *Plan-time: this bumps `SCHEMA_VERSION`.*

  Two distinct gates, not one (separated cycle-2): the **build-time gate**
  (*does rung 4 ship at all?*) is decided by the Q-DI2.5 baseline — if rungs 2+3
  eliminate the reachable (a) class, rung 4 never ships. The **runtime gate**
  (guardrail 1, *when it fires if shipped*) is the 2..5-after-deterministic
  condition. Site is between `_step.py:266` and the `:330` ambiguous return; it
  needs router/mcp access so it lives in a console-layer helper, **not** pure
  `_tool_filter.py` (I/O-free by contract). Exact module deferred to plan.

- **Q-DI2.3 — task-term surface. RESOLVED: terminal fallback, outcomes-not-tools,
  best-effort labels.** Replaces the `:330-341` `"Step matched N tools… use a
  more specific verb"` + `candidates:[tool names]` leak when arbitration genuinely
  can't resolve. Labels derived from **tool descriptions, not names**; generic
  ambiguity explanation when descriptions are poor (*don't invent clarity that
  isn't present* — the cut line one layer up). **Never** leak tool identifiers
  (`flame_get_clip` vs `forge_get_shot`); the artist never learns the ontology
  ([[project-forge-bridge-ux-philosophy]]). Build after the resolver improvements;
  minimal. Whether this fires often at all depends on Q-DI2.5 (exact-name-wins +
  narrow may resolve most of the (a) class).

- **Q-DI2.4 — deliverable 5 (mis-selected read). RESOLVED: it is the *boundary*,
  not a separate mechanism.** Framing deliverables 3/4/5 collapse into one ladder:
  *deterministic resolve → (contingent) bounded select → (fallback) task-term
  choose-among-candidates.* Deliverable 5's rule — **re-select among known
  candidates: yes; generate a new interpretation: no** — is the *constraint* on
  that ladder, not an after-the-fact "let me reinterpret what you meant" path.
  Adding such a path is the shadow-compiler drift the framing's boundary exists to
  prevent (the mirror of DI.1's "don't let safety become usability"). Re-compilation
  stays **intentionally unbound pending a future compile-quality milestone**
  (`SEED-COMPILE-QUALITY-V1.10+`), not rejected ([[feedback-explicitly-unbound-vs-implicitly-rejected]]).

## The buildable ladder (what the plan builds)

One arbitration ladder, sequenced; each rung is measurement-gated by the rung's
own justification, not built speculatively:

1. **Task 1 — capture baseline (Q-DI2.5).** Flip the flag, re-run, classify
   (a)/(b)/other against real candidate sets. Zero code. **Gates rung 4.**
2. **Exact-name-wins exclusivity (Q-DI2.1).** ~3 lines in `filter_tools_by_message`.
   Unconditional. Unblocks DI.1's live demo.
3. **Strengthen `deterministic_narrow` (framing del. 2).** Close the N>1 gap for
   ordinary task phrasings, deterministically. Unconditional; scope sized by the
   capture data.
4. **Bounded LLM selection (Q-DI2.2).** Single capped pick-one call, 2..5
   candidates, after rungs 2+3, timeout-bounded, captured. **Contingent** —
   ships only if task 1 shows residual (a) the deterministic rungs can't reach.
   Governed by the seven guardrails; invariant: *choose among known candidates,
   never create a new one.*
5. **Task-term fallback surface (Q-DI2.3).** Replaces the "matched N tools" leak;
   outcomes not tools; best-effort labels with generic fallback. Terminal rung.

**Boundary (constrains every rung, not a rung itself — Q-DI2.4 + the rung-4
invariant):** *choose among known candidates; never create a new candidate.*
Re-select among the resolver's set: yes; re-interpret the request or invent a
tool: no. No prose, no authority decisions; reads-side only — a resolved mutation
still hits DI.1's `:415` gate.

## Carry-forward honesty (into DI.2-PLAN)

- **The win is ≤3/9 and contingent, and that is the point** — DI.2 materially
  improves ~1/3 of the corpus and explicitly does **not** solve compile quality
  (~44%, `SEED-COMPILE-QUALITY-V1.10+`), session scope, or answer fidelity.
  ≤3/9 must not be read as license to *weaken* DI.2 (one-third of real pain is
  meaningful) nor to *widen* it into recompilation.
- **Rungs 4/5 may not get built.** If the capture data shows rungs 2+3 resolve the
  reachable (a) class, that is a *smaller successful phase*, not an underdelivery —
  log what the data dropped, don't pad scope ([[feedback-operational-maturity-not-completeness]]).

## Status

**Cycle-2 phase-discuss, 2026-06-01** (operator ruling on Q-DI2.2 folded). All
five Q-DI2.x resolved against live code. Cycle-2 changes:

- **Q-DI2.2 ratified — rung 4 contingent, kept (NOT fully deferred).** Operator
  rationale elevated: pure-deterministic DI.2 risks a "protected the boundary,
  left the user stuck" milestone; bounded LLM pick among resolved candidates is
  arbitration, not recompilation. **Governing invariant added:** *choose among
  known candidates; never create a new candidate.* Seven binding guardrails
  enumerated. Two gates separated: build-time (ship rung 4 at all? — Q-DI2.5
  baseline decides) vs runtime (fires only after rungs 2+3 leave 2..5).
- **Guardrail 7 is new + load-bearing:** rung 4's selection emits to the
  divergence corpus (versioned `SCHEMA_VERSION` bump, not a comprehension touch) —
  instrument the new decision surface rather than add a blind path. Consistent
  with this milestone's measurement-debt lesson.

Cycle-1 rulings (retained):

- **Q-DI2.5 sequenced first and proven zero-code** — the divergence instrument
  (`_step.py:314` + `handlers.py:1752`) already captures the classifying field;
  env-var flip + non-degraded re-run. *Gates* rung 4's build decision.
- **Q-DI2.1 grounded to ~3 lines** (`filter_tools_by_message` exclusivity-when-unique),
  substring-vs-token-complete distinction flagged for the plan's test matrix.
- **Five framing deliverables collapsed to one measurement-gated ladder;**
  deliverable 5 reclassified as the boundary that constrains the ladder.

**RATIFIED 2026-06-01** (operator). All five Q-DI2.x closed; rung 4 invariant +
guardrails binding. Proceed to DI.2-PLAN — task 1 (capture baseline) plans first
so the rest is sized against real candidate sets.
