# A.5.3.2 — Framing (binding pre-spec scope artifact)

**Status:** framing locked 2026-05-06. Spec not yet drafted.
**Predecessor:** A.5.3.1 closed (commit `d15c00e`); narrower fail-open guard
shipped for the verb-only-overlap case.
**Successor (when this phase closes):** the second entry of
`docs/learnings/2026-05-06-narrowing-vocabulary.md`, plus the divergence
corpus itself as durable artifact.

This document is a **scope contract**. The eventual `PHASE-A.5.3.2-SPEC.md`
must derive from it. Deviations from the framing below must be raised
explicitly and decided against this document, not absorbed silently into
the spec.

---

## Architectural threshold

The project has crossed from substrate stabilization into deliberate
shaping of execution-arbitration behavior. This is no longer:

- lifecycle correctness
- truthful contracts
- startup-path integrity
- environmental diagnosis
- deterministic execution correctness

Those layers are sufficiently stable and observable to support a
higher-order concern:

> **The boundary between deterministic systems and planner intelligence.**

A.5.3.2 is the first phase that lives entirely on that boundary.

---

## Three architectural layers (frame for all future work)

| Layer | Concern | Status |
|-------|---------|--------|
| 1. Runtime substrate | truthful, observable, reliable execution | sufficiently stable |
| 2. Execution arbitration | deterministic-vs-planner boundary | **the current frontier** |
| 3. User surfaces | Ask / schematic / foundry workflows | downstream of Layer 2 |

Layer 2 is where determinism, ambiguity, operator trust, graceful
degradation, planner behavior, and automation ergonomics all converge.
That is the work now.

It is **not** "making the model smarter." It is **making the arbitration
operationally trustworthy.**

---

## Phase shape (sequential, non-fungible)

A.5.3.2 has three steps in strict order. Step N+1 cannot start until
Step N produces its artifact:

1. **Observation-and-classification.**
   Build the comparison instrument. Run it. Produce a divergence corpus.
   No narrowing semantics change in this step.

2. **Heuristic-tuning.**
   ONLY after the corpus is large enough to support a defensible
   classification. Tuning targets are derived from corpus categories,
   not invented from intuition.

3. **Spec close + learnings entry.**
   Document what changed, why, and against what evidence. Append the
   second entry of `docs/learnings/2026-05-06-narrowing-vocabulary.md`.

The phase is **explicitly NOT** a planner-reimplementation phase. If
Step 2 begins drifting toward "the narrower needs to understand intent /
plan / track conversational context," **STOP and re-scope.** That work,
if it ever happens, is its own phase with its own framing.

---

## Primary deliverable

The **divergence corpus** is the most important artifact this phase
produces — more important than any heuristic change that follows.

For each captured prompt, the comparison instrument records:

- **prompt** (verbatim)
- **candidate set** (post-reachability, post-`filter_tools_by_message`)
- **topology state** (which backends were reachable at the time)
- **narrower decision** (output of `deterministic_narrow`)
- **PR20 fired?** (boolean)
- **collapse occurred?** (single-survivor → forced execution)
- **LLM-selected tool(s)** (given the unfiltered post-reachability set)
- **LLM declined tool usage?** (boolean — chose to answer conversationally)
- **ambiguity state** (>1 survivor, 0 survivors, single survivor)
- **timing** (narrower latency, LLM latency, total)
- **prompt classification** (see categories below — initial taxonomy)

The corpus design must allow:
- replay (deterministic re-runs against changed narrower)
- categorical analysis (which prompt families diverge)
- regression tests later (specific divergences become test fixtures)

---

## Objective lock — Optimize for C (minimize harmful hijacking)

Three candidate objectives were considered:

- **A. Maximize deterministic execution** — collapse aggressively; let
  the narrower decide whenever possible.
- **B. Maximize planner freedom** — let the LLM see everything; the
  narrower exists only as a reachability filter.
- **C. Minimize harmful hijacking** — deterministic only when confidence
  is structurally high; ambiguity escalates upward; conversational
  prompts remain conversational; multi-intent prompts remain plannable;
  degradation behavior remains truthful and explainable.

**This phase optimizes for C.** A and B are recorded for completeness
but are NOT the chosen objective. Future phases may revisit if evidence
warrants.

The A.5.3.1 fix (verb-only-overlap guard) was already an instance of C:
when confidence was structurally low, the narrower fell open. A.5.3.2
extends the same posture — confidence-gated determinism, with explicit
ambiguity escalation.

---

## Boundary discipline (the load-bearing constraint)

| Subsystem | What it is | What it must NEVER become |
|-----------|------------|---------------------------|
| narrower (`_tool_filter`) | deterministic confidence gate | semantic orchestrator |
| narrower (`_tool_filter`) | lexical, explainable | conversational interpreter |
| narrower (`_tool_filter`) | topology-aware | multi-step planner |
| narrower (`_tool_filter`) | confidence-oriented | hidden reasoning logic |
| narrower (`_tool_filter`) | cheap to reason about | a second accidental planner |
| LLM (planner role) | plans + interprets + summarizes | a deterministic dispatch shortcut |

The healthy separation is:

```
narrower  =  deterministic confidence gate
LLM       =  planner
```

Preserve this **aggressively**. Every proposed heuristic during Step 2
must be checked against this table. If a proposal blurs the line, it
must be rejected — not "compromised on" — and the underlying need
re-examined for whether it actually belongs in the LLM's seat.

---

## Anti-patterns (named, blocked)

- **"Just one more heuristic"** — produces implicit planner behavior,
  invisible semantic drift, non-explainable arbitration, accidental
  complexity. The system's current legibility exists precisely because
  deterministic systems stay deterministic and planners stay planners.
- **Heuristic invented before evidence** — any narrowing rule change
  proposed before the divergence corpus exists is rejected by default.
- **Conversational interpretation in the narrower** — the narrower
  must not "understand" the prompt. It can lex it.
- **Multi-step state in the narrower** — single-step decision only.
  Cross-step planning is the LLM's seat.
- **Implicit confidence floors** — any "narrower picks this when
  confidence > X" rule must surface X as a documented, observable
  threshold. No magic numbers.

---

## Prompt-family taxonomy (initial — refine with corpus)

Prompts are not a flat space. Different families legitimately want
different arbitration behavior:

| Family | Example | Expected arbitration |
|--------|---------|----------------------|
| Conversational | "explain forge-bridge in one sentence" | LLM, no tools |
| Single-intent deterministic | "list flame libraries" | narrower collapses, PR20 fires |
| Ambiguous operational | "list projects" (Flame down) | escalate (A.5.3.1 outcome) |
| Multi-intent planning | "what projects exist and how many staged ops are pending?" | LLM, multi-tool loop |
| Foundry/orchestration (future) | (TBD) | TBD — out of scope here |

The taxonomy is a starting point, not a contract. The corpus is what
turns it into a contract — categories that don't appear in the corpus
should be questioned; categories that do appear and don't fit the table
should expand it.

---

## Out of scope (explicit)

- Maya / editorial endpoint adapters
- Auth (SEED-AUTH-V1.5, deferred)
- Streaming / SSE
- Foundry / Ask UI (their own seeds, downstream of Layer 2)
- LLM model bumps (own seeds)
- Reachability filter ↔ narrower coupling redesign (mentioned as a
  follow-up in the A.5.3.1 learnings note; out of scope here unless
  the corpus shows it's load-bearing for arbitration trust)
- The 4 pre-existing test failures (stdio_cleanliness ×2 +
  typer_entrypoint ×2) — confirmed unrelated to A.5 work; tracked
  separately.

---

## Phase-end conditions

| Trigger | Response |
|---------|----------|
| Step 1 corpus shows the narrower is mostly correct and divergences are isolated | Smaller fix scope; document the corpus; close. |
| Step 1 corpus shows systemic narrower brittleness | Step 2 still applies, but each heuristic must clear the boundary-discipline table above. |
| Step 1 corpus shows the narrower's domain is semantically wrong (e.g., needs to understand prompt intent, not just match tokens) | **STOP. Do NOT add planner-shaped heuristics.** Plant a v1.6 vocabulary-redesign seed and close A.5.3.2 with the corpus + learnings note alone. |
| Step 2 begins drifting toward planner-reimplementation | **STOP and re-scope.** Capture the drift trigger as a learnings note. |

---

## Next concrete decision point (NOT this document — next conversation)

Before the spec is drafted, the comparison instrument's contract has to
be designed:

- where it lives (test-time? runtime opt-in?)
- what it captures (the list above is a starting point, not final)
- what it does NOT capture (avoiding "instrument is also another
  heuristic in disguise")
- how the corpus is stored (JSONL? per-run files? annotated?)
- how the LLM-selection comparison signal is obtained (inject into
  `complete_with_tools`? side-channel via a dry-run wrapper?)
- how the instrument survives changing models (today's qwen2.5-coder
  → tomorrow's something-else)

That conversation is the gate to the spec. Until it produces a written
contract, the spec stays unwritten.
