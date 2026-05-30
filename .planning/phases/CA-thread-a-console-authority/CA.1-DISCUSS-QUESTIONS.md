---
milestone: v1.8
thread: A
phase: CA.1
phase_name: preview projection + ratify affordance + JSON preview-branch fix
status: discuss-questions-cycle-1
drafted: 2026-05-30
type: discuss-questions
derives_from: .planning/phases/CA-thread-a-console-authority/CA-THREAD-A-FRAMING.md (cycle-2, a4bfa1a)
grounding: this-session live reads — handlers.py JSON returns (preview_emitted :1954, chain_complete :1977), forge-chat.js (messages-replace :169, orchestration_terminated :183), panel.html (orchestration-termination sibling :59), _chat_compile.py (conditional graph_intent_id :161-171)
---

# CA.1 — Discuss questions

> Compact per [[feedback-cadence-artifacts-shrink-to-load-bearing]].
> Derives from the cycle-2 framing. CA-Q2 (outcome card) is already a
> binding constraint and is **not** re-litigated here. Q1 below is the
> framing's grounding-obligation #1 — it must resolve first because it
> sets CA.1's true scope (bug-close vs new-taxon ordering). The rest pose
> CA.1's open UI decisions with leans.

## Q1 — What does `/api/v1/chat` actually return to the Console, per regime? (BLOCKER — grounding obligation #1)

The framing flagged a transcript-blank risk as *hypothesis-to-confirm*.
Cycle-2 grounding sharpened it rather than settling it:

- **Both** compiled JSON returns lack a `messages` key —
  `preview_emitted` (`handlers.py:1954`) and `chain_complete`
  (`handlers.py:1977`).
- `forge-chat.js:169` runs `this.messages = (body.messages || [])`
  **unconditionally** on every 2xx, *before* the `stop_reason` check
  (`:183`).
- Therefore, in the compiled regime, the Console replaces the transcript
  with `[]` on **both** branches — not just preview.

This widens DT's "can't be right" catch. The question is no longer "does
preview blank the transcript" — it's: **does the compiled-chat regime
ever return `messages` to the Console?**

Two live hypotheses (discuss must ground which is true):
- **(H1) Compiled chat already blanks every turn via the Console UI** —
  a pre-existing latent bug CA.1 inherits, and the preview branch is one
  visible face of it. If so, CA.1's fix is broader: the JS must stop
  unconditionally trusting `body.messages` for compiled responses.
- **(H2) There is a separate non-compiled / legacy `/api/v1/chat` return
  path that *does* echo `messages`**, and the compile path simply was
  never exercised through the Console UI (CLI/`fbridge chat` only). If so,
  CA.1's fix is narrower: render preview/chain from their own keys and
  guard the `messages` replace.

*Lean:* (H2)-shaped — the `messages`-echo contract (`forge-chat.js:167`
comment "replace local state with the echoed history") predates the
compile regime (v1.7 Thread A), so the compile returns likely never
carried `messages` and the Console preview path is genuinely unexercised.
But this is the one thing CA.1-discuss must **prove by reading the chat
handler's full regime tree**, not assert. Resolution decides whether the
CA.1 commit is titled "fix" or "add."

## Q2 — Ratify button: states + placement

The button POSTs `{graph_intent_id, actor}` to `/api/v1/ratify` and the
outcome renders as a distinct authority card (CA-Q2 constraint). Open: the
button's own states and where it sits.

*Lean:*
- **Absent-id guard:** `graph_intent_id` is conditional
  (`_chat_compile.py:161-171`) — if `preview.graph_intent_id` is missing,
  render the button **disabled** with a one-line "no persisted intent —
  ratification unavailable" note. Never POST a missing id.
- **In-flight:** disable + spinner during the POST (reuse the existing
  `inflight` pattern in `forge-chat.js`).
- **Placement:** the ratify control belongs **on the preview card** (it
  acts on that intent); the outcome card renders as a **sibling below**,
  matching the `orchestration-termination` sibling shape (`panel.html:59`)
  the CA-Q2 constraint already points at.

## Q3 — Render fidelity (CA-Q1 lean, near-settled)

*Lean (confirmed-strengthened in framing):* condensed summary + expandable
per-step `<details>`, matching the existing tool-trace collapsed pattern.
`args_preview` is `extract_explicit_params` → today only
`{project_id}` / `{project_name}` / `{}`, so per-step args are usually
empty; full-fidelity rendering is low-value. Open detail for discuss:
which summary fields lead the collapsed view — `total_steps`,
`mutating_steps`, `requires_ratification`? *Lean: all three as a one-line
badge row; the mutating count is the operator's decision-relevant number.*

## Q4 — Actor value (CA-Q3 lean, settled)

*Lean (settled):* send `actor="local"`, identical to the CLI ratify
default (endpoint defaults `"local"` `handlers.py:1242`; CLI defaults
`"local"` `cli/main.py:300`). No browser-supplied label pre-auth.
Forward-pointer only (NOT CA.1 scope): SEED-AUTH-V1.5 is a milestone-wide
three-convention unification (CLI ratify, Console ratify, staged-ops
`_resolve_actor` D-06) — overlaps
SEED-POST-A1-ENVELOPE-CONTRACT-RECONCILIATION. CA.1 changes nothing here;
it just must not invent a *fourth* actor convention.

## Parked (not CA.1)

- **CA.3 grounding obligation:** does `read_api.py`'s health mirror re-run
  the `runtime_doctor` checklist or maintain its own? Determines whether
  the `_check_ratification` mirror is rendering-only. Carried to CA.3, not
  resolved here.

## Status

**Discuss-questions cycle-1.** Q1 is the blocker — it must ground before
the CA.1 plan, because H1 vs H2 sets the phase's true scope. Q2–Q4 carry
leans ready to confirm. Room reviews Q1's two hypotheses + the leans, then
this routes to CA.1-PLAN.
