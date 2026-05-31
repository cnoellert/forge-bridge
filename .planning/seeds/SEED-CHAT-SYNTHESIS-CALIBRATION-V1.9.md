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

## Part 4 — WHO synthesizes (DT's sharpening: the operative axis)

Creative's calibration answers *what* may be synthesized (explanations of
real facts, not invented facts). DT's contribution — adopted — is that this
is necessary but **not the operative recalibration.** The traceability test
is a *grounding* test; it is blind to a second axis the constitution
actually turns on: **authorship.** Same grounded fact, different emitter,
different verdict.

> *"The apply failed because the assent record was already in 'applied'
> state."* — perfectly grounded, traces straight to the 409.
> - **Model**, in its turn → fine. Always was.
> - **Consumer template**, rendering a structured reason code → fine.
> - **Handler/orchestrator**, authoring free prose → the 24.4 violation.

Same sentence, three authorships, two fine and one breaks the invariant —
because the three terminal taxa (`done` / `orchestration_terminated` /
`error`) exist so consumers can branch on **who decided**, and that only
survives if the orchestrator stays mute. So the operative gate is:

**Grounding (every claim traces to substrate) AND authorship (the emitting
layer is entitled to author the text).**

DT's reframe of *why* the chat is silent today is the unlock: the compile
path lacks explanation **not because a rule forbids it, but because there
is no author at the end of it.** 24.x built the operational runtime to be
LLM-free *after* compile — the model compiles the plan and leaves. So the
operator sees raw output because the path has no author, not because
explanation is banned. The question is therefore not "may the system
synthesize" but **"who should author the understanding, and are they
entitled to."**

### The three legitimate authors (increasing cost)

1. **Consumer rendering** — deterministic template of structured substrate
   into human-readable form (grouping, labelling, "Status: already
   applied" from an error code). This is *rendering, not synthesis*, already
   allowed, and badly **under-used**. A large fraction of Creative's
   "Allowed" list is achievable here today with no model turn.
2. **Substrate enrichment — the real unlock.** Make the substrate *emit
   structured reasons* — `{reason_code, human_reason}`, plan summaries,
   effect descriptors — so "understanding" becomes a *rendering of
   structured truth*, not generation of free prose. Fully grounded, fully
   understandable, **no author question at all** (nobody synthesized; the
   operator understands). This gives Creative the outcome and costs the
   authorship guard nothing. This is the substrate-shaped machine doing
   what it is good at, *in service of* understanding instead of against it.
3. **Model synthesis, attributed** — the LLM-loop's model-authored
   `final_text`, taxon-stamped `done` = model-decided. The path the rules
   already bless. The genuine design decision, because it has a real cost
   (Part 6).

The surviving guard, unchanged: the **orchestrator** may NOT author prose
answers — keep 24.4. And **assent stays the operator's**: an answer may
*describe* a mutating preview but never assents. Narration ≠ assent.

## Part 5 — The reads/writes division (DT's proposal, adopted)

Map the authorship axis onto the read/write boundary:

- **Reads → model synthesis** (LLM-loop path), rendered as attributed
  `final_text`. Understanding, model-authored, taxon-proven. This is the
  surface where understanding bites and where there is **no authority
  record to corrupt.**
- **Mutations → deterministic preview + ratify**, structurally rendered
  (enrichment + consumer render), **no model prose** — because the modal
  boundary (would/did) and the authority record matter most here.

This gives Creative the understanding objective exactly where it bites
(reads) and preserves the authority discipline exactly where it is
constitutional (mutations).

## Part 6 — Fidelity beyond traceability (Orch flag; refined by DT)

Traceability is necessary but not sufficient: a sentence can be perfectly
traceable and still **mischaracterize** — overstating confidence, implying
causation, or describing a *preview* as if it *happened*. DT's correction:
on the **enrichment + preview** paths this is already policed structurally —
the preview carries `would_mutate` / `mutating_steps`, intent framed as
intent with the modal marker intact. The danger is the *slide* from "this
**would** rename 40 shots" (intent, hedged, structural) to "this **renames**
40 shots" (asserted outcome). **Keep the modal marker.** The preview's
structured form is the safe version of "describe the practical effect."

So the fidelity clause is **scoped**: it is a *model-synthesis* (Part 4 #3)
concern, not an enrichment concern. Enrichment renders structured truth and
*cannot* overstate tense/certainty; model prose can. Therefore: on the
reads→model path, the gate needs *not only* traceability *but also* no
overstatement of certainty/tense/causality. On the enrichment path, the
structure carries the fidelity for free. Resolve the model-path clause at
v1.9 framing.

## Part 7 — The cost question, restructured around the three authors

A.1 dropped the model answer-pass for token/latency budget — the same qwen
budget the whole 24.x arc fought to protect. The three authors price out as:

- **Consumer rendering + substrate enrichment (Part 4 #1+#2): cheap, ship first.**
  No model turn. `tool_unresolved {candidates:[...]}` → "I couldn't find
  that sequence — did you mean `30sec_21`?" is templating; "explain why the
  apply failed" → the outcome carries `{reason_code, human_reason}`,
  rendered. This is what the six "seeded-for-v1.9" regimes should always
  have been — not raw projection (CA.1's mistake), not a model pass, just
  human rendering of structured truth. Most of Creative's "Allowed" list
  lands here, grounded, understandable, no author question.
- **Model synthesis on reads (Part 4 #3): the real decision, priced.**
  Routing Console **reads** through the LLM-loop path gives plain-language,
  model-authored, taxon-attributed answers — exactly Creative's objective,
  by the entitled author. **But it re-inherits the exact problem 24.x was
  chasing:** local-model latency + convergence under the tool prefix in the
  operator's hot path. Architecturally cleanest; not free; gated on the
  convergence evidence we never fully closed.

### The genuine open question (Orch's sharpening — for Creative to push on)

DT framed it as: *is reads-via-LLM-loop worth its reliability cost, or does
enrichment+rendering alone get us far enough on reads without a model turn?*

**My sharper version, and the warning I want on record:** enrichment is
seductive *because the substrate-shaped machine is good at it* — and that is
exactly how the last drift happened. Enrichment + rendering will make the
console **legible**; it will not make it **answer an open question** the
operator didn't pre-structure ("what changed on this sequence since
yesterday, and does any of it affect the hero shot?"). That requires
reasoning over multiple results — model synthesis, #3, the gated one. The
risk: ship the cheap tier, watch the two-axis gate go green on the easy
queries, and call it chat — when the part that needs the model to *talk*
never arrives. **Enrichment is necessary and not chat.**

So the reliability cost of the model read-path is not a cost to weigh
*against* the objective — for open-ended reads it **is** the gating fact
*of* the objective. The right question is therefore not "is it worth it" but
**"what convergence evidence would close it"** — making the 24.x reliability
work the v1.9 spine, not a deferred side-quest. That is the real decision,
and it is an evidence question, not a principle one.

## Example corrections (DT, adopted)

Two items from Creative's "Allowed" list were imprecise and are resolved by
the authorship axis:

- **"Explain why an apply failed"** — the one genuinely contested item. NOT
  handler prose. Resolve by **enrichment (#2)**: the apply outcome carries
  `{reason_code, human_reason}`; the consumer renders it. Nobody
  synthesizes; the operator understands.
- **"Describe the practical effect of a sequence of actions"** — sits on the
  soft spot. The practical effect of a *not-yet-ratified* plan is a future
  outcome, which the "not allowed" list bans. The **preview already polices
  this** via `would_mutate` / `mutating_steps` — intent as intent. Keep the
  modal marker; the preview's structured form IS the safe version.

## What v1.9 must NOT do

- Must not reopen substrate authority / ratification / state ownership.
- Must not let the **orchestrator/handler** author prose (keep 24.4). Authors
  are: consumer-render, substrate-enrich, model-synth. Not the control layer.
- Must not ship another "project more substrate" phase before this lands.
- Must not treat traceability alone as the gate (grounding AND authorship;
  plus the model-path fidelity clause, Part 6).
- Must not let the model own assent (narration ≠ assent; mutations stay
  deterministic preview + ratify, Part 5).
- **Must not let cheap enrichment masquerade as chat** (Part 7): legible ≠
  answering. The model read-path is the part that actually makes it chat;
  do not let the easy tier's green gate hide that the hard tier never shipped.
