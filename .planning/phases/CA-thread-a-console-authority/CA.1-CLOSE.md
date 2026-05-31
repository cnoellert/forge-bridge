---
milestone: v1.8
thread: A
phase: CA.1
type: phase-close
status: closed-narrow-bugfix
closed: 2026-05-30
honest_scope: "Shipped ONE real thing: the destructive transcript-blank is fixed. Everything else CA.1 framed as delivered (preview projection, ratify affordance as a usable authority surface) is code that exists but was never confirmed usable by a human, because the surface it projects onto is not chat."
---

# CA.1 — Close (honest, narrow)

> This close deliberately rejects the victory framing the plan carried
> ("preview projection + ratify affordance completes the Console authority
> chain"). That framing is not what shipped. What shipped is one correct
> bugfix on a surface that does not work for a human. Recording that
> plainly is the only useful thing this artifact does.

## What actually shipped

**One real fix:** `1598917` — the chat transcript no longer blanks when a
`/api/v1/chat` response lacks a `messages` key. Pre-CA.1, 8 of 9 non-SSE
regimes wiped the screen via an unconditional `this.messages = (body.messages
|| [])`. Now the transcript is preserved. This is a genuine, narrow,
correct bugfix and it is verified live in the browser (operator dogfood
2026-05-30: multi-turn transcript stayed populated across `tool_unresolved`,
tool-not-registered, and `ToolError` responses).

**Code that exists but is NOT confirmed usable:** `1692a74` (preview
card), `4399486` (ratify button), `92c0106` (outcome card), `523356f`
(styling). The Python contract was read and the JS bindings are correct
*as code*. But a live `preview_emitted` was **never once produced** — not
in the browser, not on the wire — across the entire dogfood. The preview /
ratify path is therefore **unverified-live**. It is not "done." It is
"written, never seen working."

Substrate facts held: 3 files changed, zero Python, `__all__` == 19,
version 1.4.1.

## The finding that matters (the real v1.8 learning)

**The chat is not chat. It is a command console, and has been since A.1.**

The operator named this directly, and it is correct. A.1 ("compile before
execute") replaced the agentic loop — where the model *talks*: calls a
tool, reads the result, writes a human sentence — with deterministic
compile-and-dispatch. The one regime that still returns `messages`
(regime #4, forced single-tool) is the *old* talking loop. Every regime
A.1+ added returns an **envelope** — `tool_unresolved`, `apply_complete`,
`chain_aborted`, `preview_emitted` — which is a dispatch record, not an
answer.

CA.1 put an amber card on one envelope. It did not make the chat answer a
human. **No phase since A.1 has, and each has drifted further**, because
each tightened the verbatim-projection discipline (x-text not x-html,
"orchestrator owns control flow not meaning," "no synthesis," "LLM never
owns assent"). Those were canonized as virtues. But **a human chat answer
IS synthesis** — taking a raw envelope and writing prose a person can
read. The architecture's central law structurally guarantees the chat can
never become conversational. That is why it drifts away from chat every
phase, not toward it.

## On the UAT (recorded honestly)

The `UAT-CA1.md` runbook is **not a usable human gate** and should not be
treated as one. Every response a real user elicited in this surface —
`tool_unresolved`, "tool not registered", `ToolError` — a user would read
as a failure. They would be right. A UAT whose pass condition is "the
screen of unreadable errors didn't blank" is not testing a product; it is
testing that a broken surface fails less violently. The de-blank fix is
real; the UAT around it is theater. The single honest UAT result is:
**transcript-preservation confirmed; chat usability: fails for a human.**

## What this close does NOT do

- Does not claim the authority chain is "Console-complete."
- Does not seed the six unrendered regimes as a tidy "v1.9 governance"
  item. That labeling — debt dressed as deferral — is part of what made
  this drift invisible. The six regimes are not a backlog ticket; they are
  evidence the surface isn't conversational.
- Does not open CA.2 / CA.3. The premise of the CA thread (project the
  substrate onto the Console) assumes the substrate is worth projecting to
  a human. That assumption is now in question and belongs at the milestone
  level, not in a phase plan.

## The real decision (milestone-level, deferred to the operator)

v1.9's actual question is not "project more of the substrate." It is:
**should the chat synthesize — i.e., should the no-synthesis law be
deliberately reversed for the human-facing answer?** Making chat answer a
person is *substrate* work (the envelope→prose layer the framing declared
out of scope), and it runs directly against the architectural law the last
several milestones canonized. That is a framing decision for a rested
operator, not something to engineer tonight.

## Process failure, named

The writing-room machine ran cleanly end to end — grounded citations,
three-voice convergence, Stage-1b catch (B-1), ratified plan, atomic
commits. None of it noticed the output doesn't answer a human. The machine
is substrate-shaped: it grounds in "what the daemon emits," plans "project
the substrate," constrains to "byte-equivalent." It is structurally
incapable of asking "would a person understand this response?" That blind
spot — not any single commit — is the failure of this phase.

Methodology candidate (the only one worth keeping from CA.1): **a phase
whose output is human-facing needs a human-legibility gate that the
substrate-grounding machine cannot supply.** "Does the daemon emit the
right shape" passed at every stage; "can a person read the result" was
never asked until dogfood, and failed immediately.

## Status

**CA.1 CLOSED as a narrow bugfix.** Transcript-blank: fixed, verified
live. Preview/ratify: code exists, unverified-live. Chat-is-a-console:
named as the real v1.8 finding. CA.2/CA.3: not opened. v1.9 framing
question (chat synthesis vs. the no-synthesis law): handed to the operator.

---

*Closed 2026-05-30. No victory framing. The one shipped fix is real and
narrow; the rest is recorded as what it is.*
