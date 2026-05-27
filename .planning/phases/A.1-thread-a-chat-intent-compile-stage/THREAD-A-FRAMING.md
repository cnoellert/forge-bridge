---
milestone: v1.7
thread: A
thread_name: Chat intent-compile stage — inferential authority under constitutional discipline
status: phase-framing
drafted: 2026-05-26
type: thread-framing
derives_from: .planning/milestones/v1.7-ARTIST-READINESS-FRAMING.md
preceded_by: Thread B (exec discoverability) — CLOSED, b73facd
grounding: G1/G2/G3 (SEED-ARTIST-READINESS-OPERATOR-SURFACES-V1.7+) + this-session reads of llm/router.py, console/handlers.py, graph/commit.py, graph/mutation.py, console/_engine.py
artifact_role: load-bearing — the A.1/A.2/A.3 phase plans derive from this
---

# Thread A — Chat intent-compile stage

> **What this artifact is.** The thread-level framing for Thread A, the
> v1.7 milestone's main arc. It records converged room doctrine and the
> five resolved rulings (Q5 + four framing-grade gaps). The A.1/A.2/A.3
> phase plans derive from it. It is filed in the opening phase's
> directory and filename-signalled as thread-scope: per-thread framing
> co-locates with the opening phase.
>
> **Two frontmatter axes.** `status` is lifecycle position
> (phase-framing -> phase-plan -> phase-execution -> phase-close);
> `type` is artifact category (thread-framing vs phase-framing vs
> close-cursor). They are distinct axes despite both carrying a
> "framing" token.
>
> **Directory slug.** Intentionally descriptive, following the existing
> descriptive-slug convention in phases/ (A.5-..., A.6-...). Thread B
> set no phases/ precedent; the A.1 prefix is the dotted form already
> in use, not a new numbering scheme.
>
> **What this artifact is not.** Not a phase plan. The per-phase specs
> land downstream.

## Thesis

Thread B exposed ontology. Thread A exposes authority. Phase N+ proved
the substrate *can* cross the host-mutation authority boundary safely
(the commit primitive, the preview->apply seam). Thread A answers the
next question: who is allowed to cross it, under what ratification
model, and how the crossing becomes observable.

Chat is half-doctrined — its output lens honors operator intent (the
render layer), its input lens does not. chat_handler validates a
request and delegates to LLMRouter.complete_with_tools, a generic
agentic executor with no compile or graph concept; the model
improvises tool use, and nothing compels it through the preview->apply
seam.

Thread A is enhancement, not correction — but the enhancement is
enforcement of an existing seam. The substrate is correct; chat's
failure is not using the correctness. Thread A gives chat a genuine
compile stage — NL -> graph-intent -> preview -> ratification -> apply
— and makes it structurally impossible for inferential compilation to
bypass the seam exact compilation already respects.

## The three authority layers

Thread A establishes a stratification that explains every decision
below. This section is a derivation of the five rulings — articulated
by the creative seat during convergence — not new framing material;
it stratifies what Q1-Q5 + the four gaps already ruled.

1. Inference authority — the compiler may infer operator intent.
2. Structural authority — only graphs (chain-step sequences) execute.
3. Human authority — only ratified graphs may cross the host-mutation
   boundary.

Compile != execute; graph-intent exists; preview exists; ratification
exists; chat cannot directly mutate; the router stays an executor, not
a sovereign. Each follows from the stratification.

## Grounding (read, recorded)

- G1 — LLMRouter.complete_with_tools (llm/router.py:422): a generic
  agentic executor — parse tool calls, dispatch via a pluggable
  tool_executor, feed back, repeat to a budget cap. Owns control flow
  / termination (Phase 24.4 K=2). No compile or graph concept.
- G2 — the graph lens is fbridge graph list/show only, a read-only
  debug surface. Backgrounded for Thread A.
- G3 — the preview->apply seam is real and chat-reachable (it lives in
  the mutation tool) but available, not enforced, at the chat layer.
- chat_handler (console/handlers.py:1206): a request handler —
  rate-limit, body validation, delegate to the router. No compile
  stage. Note: a _tool_enforcement module exists but is PR15
  tool-calling determinism — a different concern; Thread A naming must
  not collide with it.
- commit primitive (graph/commit.py): CommitNode.verify(held, fresh)
  checks plan *drift* — it does not check operator *assent*.
  MutationManifest (graph/mutation.py) is a frozen 5-field dataclass
  with no assent record. "Ratified" does not exist as substrate state.
- chain executor (console/_engine.py): run_chain_steps executes a
  list[str] of chain-step texts — sequential, abort-on-first-error,
  context via extracted_context. This IS the post-compile executor;
  no new executor component is needed.

## Converged architecture

**Q1 — compile stage location: compiler-before-loop, insertion (i).**
A compile stage sits between chat_handler and the router; the router
stays the agentic executor it already is and keeps its Phase 24.4
control-flow authority. Compile runs *before* the loop, so graph-intent
is a clean derived artifact, not entangled with LLM-loop state.

**Q2 — graph-intent is the same substrate-shape as exec output.**
Graph-intent is not a parallel graph type and not a separate
representation universe — it is a state-bearing lifecycle form of the
existing graph substrate. Grounding confirms exec's real output-shape
is list[str] chain-step text; graph-intent is therefore validated
chain-step text, the same representation run_chain_steps already
executes. The lifecycle states (unratified -> preview -> ratified ->
executable) are states of one graph, not distinct artifacts. The
"preview artifact" an operator inspects and the "graph-intent" the
compiler emits are the same substrate object in different lifecycle
states — never two representations. Any later phase introducing a
second graph representation is a doctrine violation (reconstructed
shape).

**Q3 — seam enforcement is compile-time via substrate-primitive
composition.** Chat compile produces graphs containing commit
primitives at every host-mutation boundary; the commit primitive
already enforces the authority transition. Chat does not reimplement
the seam — it composes with it. Router interception and tool-wrapper
layers are reconstructed (policy riding on substrate); compile-time
composition is derived.

## The five rulings

**Q5 — ratification is substrate state.** Not UI, router, or
conversational state. A preview artifact carries a stable identifier;
operator assent is recorded against it as a separate, attributable
record; commit.verify() checks both drift validity and assent
validity. The LLM never owns assent — that is the constitutional line.
A.2 introduces the substrate-side ratify motion + a CLI operator
surface; Console is later; a conversational affordance, if ever, is
only thin verbatim transport to the substrate motion, never an
interpreted "yes."

**Gap #1 — compile failure is a typed structural outcome.** A
CompileError family (sibling to CommitError / MutationManifestError),
including seam-violation-at-compile-time as a first-class taxon. Failed
compilation produces no executable graph-intent artifact — no partial
execution, no speculative lowering, and no silent fallback to raw
router tool-execution. The preview surface may render compile
diagnostics; the execution path stays closed.

**Gap #2 — additive transport, unconditional compile.** A.1 preserves
the transport and orchestration contracts (request/response envelopes,
K=2 termination, orchestration_terminated taxa, the router loop) 24.x
byte-equivalence-style. AND compile is unconditional: every chat turn
passes through the compile stage; "no-graph-intent" is a structural
outcome; there is no un-compiled path to host mutation.

**Gap #3 — the existing chain executor is the post-compile executor.**
run_chain_steps (console/_engine.py) executes list[str] chain-step
texts. Thread A formalizes graph-intent and inserts compile + ratify
in front; it routes into the executor that already exists. No new
substrate executor component. Thread A is orchestration, not substrate
expansion.

**Gap #4 — per-turn output, history-aware input.** Compile runs once
per user message and emits a stateless per-turn graph-intent artifact.
The compiler may read conversation history to compile the current
turn, but graph-intent carries no multi-turn accumulation state.
Multi-turn intent persistence is a different system, deferred.

## Phase decomposition

- **A.1 — the compile stage.** NL -> graph-intent -> preview. The
  compile stage (insertion point (i)), the CompileError family, the
  preview surface over graph-intent. Ratification stubbed. Preserves
  the chat transport contract; compile is unconditional.
- **A.2 — ratification + enforced apply.** The substrate ratify motion
  (assent as a substrate record on the preview artifact), commit.verify
  extended to check assent, the CLI ratify surface. The authority
  transition closes end-to-end.
- **A.3 — hardening.** Surfaced once A.1/A.2 land.

## Out of scope

- Multi-turn graph-intent persistence (Gap #4).
- Console / conversational ratification surfaces (Q5 — A.2 ships CLI;
  these are later).
- New graph primitives or a new executor component (Gap #3).
- Thread A does not modify exec — both lenses target one substrate.

## Architectural law (inherited, binding)

Substrate self-views are first-class operator surfaces — derived, not
reconstructed. Thread A inherits it: graph-intent is derived (Q2),
enforcement is substrate composition (Q3), the ratification surface is
derived substrate state (Q5). Thread A and Thread B converge on one
ontology — the discover introspection layer Thread B built is the
semantic-grounding source Thread A's compiler consumes.

## Status

Phase framing. Converged 2026-05-26 — room (creative + dt) + operator
rulings on Q1/Q2/Q3 and the five questions (Q5 + four gaps). The A.1
phase plan is the next motion.
