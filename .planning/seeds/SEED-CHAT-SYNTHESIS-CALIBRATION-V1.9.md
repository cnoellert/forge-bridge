---
name: chat-synthesis-calibration
description: "The 'no-synthesis law' for chat is a category error. Provenance dig (this session) shows there is NO general no-synthesis principle — there is a narrow, correct 24.4 orchestrator-impersonation guard that got rhetorically stretched into 'chat must never synthesize.' v1.9 recalibrates: the system may synthesize EXPLANATIONS of facts that exist in substrate; it may not synthesize FACTS that don't. Two-axis chat gate: grounded AND understandable. Keep orchestrator-non-impersonation; restore the model answer-pass A.1 dropped for cost."
type: strategic-framing
planted: 2026-05-30
planted_during: "CA.1 close (bb109e6). Operator named 'the chat is a console, not chat'; the CA thread (project the preview envelope onto the Console) was correct as bugfix but did not and structurally could not make chat answer a human. This seed is the v1.9 framing that resulted from the operator+Creative exchange + the orchestrator-impersonation provenance dig."
trigger_when: "v1.9 framing, OR any phase that touches the chat/answer surface. This is the milestone-level decision CA.1 close deferred. Do NOT open another 'project more substrate' phase before resolving this."
relates_to:
  - .planning/phases/CA-thread-a-console-authority/CA.1-CLOSE.md
  - memory: project-chat-is-a-console-not-chat
  - memory: feedback-orchestrator-control-flow-not-meaning
---

# Seed — Forge Chat Synthesis Calibration (v1.9)

> **This is the honest correction to a multi-milestone drift.** The chat
> stopped answering humans and each phase drifted further. The cause is not
> a principle that needs reversing — it is a fake principle that needs
> dissolving, plus a performance decision that needs un-making.

## Part 1 — Provenance: there is no no-synthesis law (the category error)

Traced from git this session. Two unrelated decisions got fused into a
principle that was never actually adopted:

1. **A.1 (v1.7) dropped the model answer-pass** — "compile before execute"
   replaced the agentic talking loop (model calls tool → reads result →
   **writes a human sentence**) with deterministic compile-and-dispatch.
   This was done for **determinism + token/latency budget**, not on
   principle. It made the chat emit envelopes instead of answers.

2. **24.4 (v1.6) coined the orchestrator-impersonation guard** —
   commit `34bc31a`: "orchestrator may terminate but does not impersonate
   the model." This was narrow and CORRECT: the *deterministic control
   layer* had just gained authority to terminate a model loop (K=2), and
   the guard says it must not then fabricate model output and pass it off
   as the model's. 24.5 (`c89af65`) extended it to consumer projection
   ("legibility without synthesis").

**The fusion:** the 24.4 *orchestrator*-impersonation rule got
rhetorically stretched to retroactively justify the model also staying
silent — two different actors, two different decisions, welded into "chat
must never synthesize." The compression "control flow not meaning" that
gets cited as ancient doctrine **first appears in `bb109e6` — the CA.1
close written THIS session.** It was never established law; it was a
late-coined generalization treated as inherited constraint. That is the
drift, named at its source.

**Consequence:** there is no principle to "reverse." There is a real guard
to KEEP (orchestrator non-impersonation) and a performance decision to
UN-MAKE (restore the model answer-pass).

## Part 2 — The calibration (operator + Creative, ratified framing)

The room spent several milestones correctly tightening substrate authority,
traceability, ratification, and state ownership. **Those remain sound and
are not reopened.** What recalibrates is the *scope* of "no synthesis."

**The cut line:**

- The system MAY synthesize **explanations of facts that exist** in the substrate.
- The system MAY NOT synthesize **facts that do not exist** in the substrate.

**Allowed (communication):**
- Summarizing a graph plan into plain language.
- Explaining why an apply failed.
- Grouping related evidence into a human-readable conclusion.
- Describing the practical effect of a sequence of actions.
- Translating technical output (envelopes) into operator language.

**Not allowed (fabrication):**
- Inventing state.
- Inventing execution results.
- Inventing authority decisions.
- Inventing provenance.
- Presenting future/predicted outcomes as facts.

**The objective restated:** the system's objective is **understanding**, not
projection. Projection is a mechanism; understanding is the outcome.

    Substrate Truth → Grounded Interpretation → Human Understanding

NOT merely `Substrate Truth → Projection`. An operator must never have to
perform the final interpretation step by hand simply because the system can
explain its own evidence but chooses not to. (That choosing-not-to is
exactly what CA.1 shipped.)

## Part 3 — The two-axis gate (the human-legibility gate CA.1 lacked)

Every chat response is evaluated on TWO independent questions:

1. **Is it grounded?** (every claim traceable to substrate evidence)
2. **Is it understandable?** (a human, specifically a non-developer artist, reads it as an answer)

- Grounded but not understandable = **incomplete** (this is today's console).
- Understandable but not grounded = **unsafe** (hallucination).
- Forge requires **both.**

This is the gate the substrate-grounding writing-room machine structurally
could not supply (it only ever asked #1, never #2 — see
`project-chat-is-a-console-not-chat`). v1.9 makes #2 a first-class,
framing-time acceptance criterion for any human-facing phase.

## Part 4 — WHO synthesizes (the guard that keeps this safe)

Creative's calibration answers *what* may be synthesized. The 24.4
provenance answers *who* — and both clauses are required, because the
"who" is the exact thing the surviving guard protects:

- **The model** may synthesize its own answer from real results. This is
  the model talking. It is the product. It was never the danger.
- **The orchestrator** (deterministic control layer) may NOT fabricate
  model output or pass its own words off as the model's. The 24.4 guard.
  KEEP IT.

So v1.9 = keep orchestrator-non-impersonation **+** restore the model
answer-pass. The model narrates; the orchestrator never impersonates; and
**assent stays the operator's** — the answer pass may *describe* a mutating
preview ("this would rename 3 shots…") but the ratify click is never the
model's. Narration is not assent.

## Part 5 — Open seam to resolve at framing (Orch's flag, not yet decided)

The traceability test ("can every sentence trace to substrate evidence?")
is necessary but **not sufficient.** The dangerous failure it misses:
synthesis that IS traceable but **mischaracterizes** — overstating
confidence, implying causation the data doesn't support, or describing a
*preview* in language that reads as if it already *happened*. That last one
is an assent-boundary hazard: a perfectly grounded sentence can still
mislead an operator into thinking a mutation applied.

So the gate likely needs a **fidelity** clause beyond traceability:
*not only does every claim trace to evidence, but no claim overstates the
evidence's certainty, tense, or causality.* Especially load-bearing at the
preview/apply boundary. Resolve at v1.9 framing.

## Part 6 — The cost question (the REAL decision, not philosophy)

A.1 dropped the answer-pass for token/latency budget — the same qwen budget
the entire 24.x arc fought to protect. Restoring it has a real price.
Likely two-tier:

- **Tier 1 — deterministic envelope rendering (cheap, mandatory, ships first).**
  `tool_unresolved {candidates:[...]}` → "I couldn't find that sequence —
  did you mean `30sec_21`?" is *templating of known envelope shapes*. No
  model turn. Violates none of the guards. This is what the six
  "seeded-for-v1.9" regimes should always have been — not raw projection
  (CA.1's mistake), not a model pass, just human formatting of known
  fields. Indefensible that it was ever called "synthesis."
- **Tier 2 — the model answer-pass (the real reversal, priced deliberately).**
  Envelope(s) → model → human answer. Costs a turn. Scope against the
  latency/token budget, probably starting with the content regimes where
  templating can't carry meaning.

**Strong lean:** Tier 1 is nearly free and ships first; Tier 2 is the real
v1.9 spine and gets priced, not assumed. The decision v1.9 actually turns
on is the Tier-2 cost envelope, not the principle — the principle is
settled by this seed.

## What v1.9 must NOT do

- Must not reopen substrate authority / ratification / state ownership.
- Must not let the orchestrator synthesize (keep the 24.4 guard).
- Must not ship another "project more substrate" phase before this lands.
- Must not treat traceability alone as the gate (see Part 5 fidelity seam).
- Must not let the model own assent (narration ≠ assent).
