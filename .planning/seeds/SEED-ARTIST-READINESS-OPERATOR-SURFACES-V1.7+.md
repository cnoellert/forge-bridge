---
name: artist-readiness-operator-surfaces
description: The forge-bridge substrate matured through Phase N+ (host-mutating commit primitive, preview→apply seam). The operator-facing lenses have not kept pace. Converged room doctrine (2026-05-25) — one substrate, two authoring lenses (exec, chat) plus the graph as the substrate's canonical self-view; chat owes a genuine NL→graph-intent compile stage; exec owes discoverability. Next milestone candidate — "Artist Readiness".
type: strategic-framing
planted_during: "Post-Phase-N+ writing-room discussion on the operator-facing surface layer. Operator observation — chat behaves like scripting syntax, not conversation; exec lacks discoverability. Grounding (G1/G2/G3) confirmed the diagnosis and sharpened it. Creative + dt converged on doctrine. Recorded as a seed per operator ruling (capture forward-pressure now; promote to milestone framing stub when the opening phase, Thread B, closes)."
trigger_when: "Thread B (exec discoverability) closes — at which point the milestone formally opens and this seed promotes to a v1.7+ milestone framing stub. OR a future contributor picks up operator-facing surface work and needs the converged doctrine."
---

# Seed — Artist Readiness: the operator-facing surface layer

## The transition this names

Phase N+ answered "can the substrate mutate reality safely?" — the
commit primitive and the preview→apply seam. The next era is a
different question: "how does a human safely ask it to?" The substrate
is mature; the operator-facing surfaces are not yet realized to the
intent they were built to serve. This is a transition from substrate
construction to human-authority orchestration — not a UI/UX milestone.

## Converged doctrine (writing room, 2026-05-25)

One substrate. Two authoring lenses, plus the graph:

- **exec** — the typed-graph lens. The exact compiler: the operator
  specifies the graph directly through chain syntax; the compile step
  is deterministic grammar parsing. Stays precise, explicit, stable.
- **chat** — the spoken-graph lens. The inferential compiler: the
  operator describes intent, the compiler infers a graph. Because
  inference can be wrong, preview is mandatory. Becomes interpretive,
  assistive, preview-oriented, operator-mediated.
- **graph** — not a third authoring lens. It is the substrate's
  canonical self-view; exec and chat are compilers targeting it.
  Currently a read-only debug surface (fbridge graph list/show); it
  owes no authoring realization and stays backgrounded.

Both authoring lenses produce the same substrate-shape and honor the
same preview→apply seam. The difference is only the compile step:
exact for exec, inferential for chat. Chat must never silently collapse
into exec — the operator always sees what intent became what graph.
That visibility is the constitutional seam.

## The diagnosis (grounded, G1/G2/G3)

Chat is half-doctrined. Its output lens has explicit intent — the CLI
render layer surfaces the terminal step's operator-meaningful output
and hides execution structure (cli/chat.py docstring). Its input lens
has none — chat_handler validates roles, keyword-filters the tool list,
matches a few exact-string commands, and passes through to a generic
agentic executor loop in the LLMRouter. The model improvises tool use.

- G1 — the LLMRouter is a generic agentic executor: parse tool calls,
  dispatch via invoke_tool, feed back, repeat to a budget cap. Five
  executor-side safety nets. No compile or graph concept. Thread A
  shifts the router's role toward compiler; the existing dispatch
  substrate executes the produced graph.
- G2 — the graph lens is fbridge graph list/show only; self-described
  "read-only debug surface for Phase 24 proto-node records." Confirms
  graph is the substrate's self-view, not an authoring lens.
- G3 — the load-bearing finding. The preview→apply seam is real and
  chat-reachable: it lives in the mutation tool (flame_rename_shots
  carries discover/verify/apply modes). But nothing compels the LLM to
  use it — the model can pass dry_run=False and go straight to apply,
  mutating the host with no preview, no operator ratification. The
  seam is available, not enforced, at the chat layer.

## What this opens — three threads, NOT one motion

- Thread A — chat input intent-layer. A genuine compile stage:
  NL → graph-intent → preview → ratification → apply. Not prompt
  shaping. Forced by Phase N+ host-mutation discipline. Because G3
  found the preview seam already exists in the substrate, Thread A is
  enhancement, not correction — but the enhancement is enforcement of
  an existing seam: compile NL to a graph-intent AND compel
  host-mutating steps through discover→operator-preview→apply rather
  than leaving the choice to model discretion. Milestone-scale,
  multi-phase, the milestone's main arc.
- Thread B — exec discoverability/introspection. A CLI surface over
  cli/exec.py to browse primitives, modifiers (if/collect/foreach),
  and tools, so an operator can compose without having memorized the
  grammar.
  Operator-literacy infrastructure, not UX polish — and it sharpens
  the primitive ontology Thread A's compiler needs. Contained,
  separable, shippable independently. The milestone's opening phase.
  Does NOT wait on Thread A.
- Thread C — Artist Readiness milestone. The container, not a
  separate thread: the milestone name. Thread B opens it; Thread A is
  its load-bearing arc.

## Grounding already done

G1/G2/G3 reads complete as of 2026-05-25 (this seed records their
result). Thread B can frame on existing grounding — cli/exec.py plus
an introspection-shape sketch against the tool and primitive
registries. Thread A's framing inherits the G1/G2/G3 findings recorded
above.

## Status

Parked as forward-pressure. Not blocking. The converged doctrine is
recorded here so it survives between sessions. Promotes to a v1.7+
milestone framing stub when Thread B closes.
