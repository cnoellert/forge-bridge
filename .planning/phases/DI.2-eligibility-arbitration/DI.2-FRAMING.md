---
milestone: v1.10
phase: DI.2
phase_name: Eligibility Arbitration — make routing resolve instead of hard-stop
type: phase-framing
status: cycle-1-draft
drafted: 2026-06-01
derives_from: .planning/milestones/v1.10-AUTHORITY-INVARIANCE-FRAMING.md (ratified) + v1.10-DISCUSS.md (Q-DI2) + .planning/phases/DI.1-dispatch-authority-gate/DI.1-CLOSE.md (the meta-finding that makes DI.2 the priority)
artifact_role: load-bearing — the usefulness half of v1.10. The framing's standing commitment: DI.2 follows DI.1 immediately and actually lands.
grounding: live reads 2026-06-01 — _step.py:251 (filter_tools_by_message) → :260 (deterministic_narrow) → :326-337 (exactly-one-or-die hard-stop; candidates at :334); DI.1 live confirmation (exact `flame_set_start_frames` matched 9 tools at the resolver and aborted before the gate)
---

# DI.2 — Eligibility Arbitration

> **What this is.** Cycle-1 phase-framing for the **usefulness** half of v1.10:
> DI.1 made *nothing dangerous happen*; DI.2 makes *more useful things happen*.
> Where DI.1 asked "may this tool execute?", DI.2 asks "which tool should
> execute?" — and answers it instead of hard-stopping.
>
> **What this is not.** Not a safety phase — DI.1 owns the authority guarantee and
> is untouched. DI.2 is **best-effort**; it may legitimately still miss. It does
> not author meaning (selection is control-flow), and it stays reads-side
> (mutations remain DI.1-gated + ratified).
>
> **The one-line thesis.** Symptom 2: *eligibility depends on routing confidence.*
> When the resolver can't narrow to exactly one tool it **hard-stops and leaks
> internals** (`"Step matched N tools… use a more specific verb"`), instead of
> arbitrating with the candidate list it already holds. DI.2 makes routing
> **resolve** — and that is also what lets requests reach DI.1's gate at all.

## Why DI.2 is now the priority (DI.1's meta-finding)

DI.1 closed with a load-bearing finding: **its gate sits downstream of Symptom 2.**
In live confirmation, *every* request — chat and deterministic `fbridge exec` —
died at the resolver before reaching the gate. The sharpest evidence: the **exact**
step `flame_set_start_frames` matched **9 tools** and aborted at
`tool_selection_ambiguous`. So:

- DI.1's safety value is **latent** until DI.2 lets requests reach the dispatch
  edge. DI.2 is the wall standing between DI.1's gate and the requests it guards.
- Resolver paralysis is not a rare edge — it intercepts ordinary reads *and exact
  tool names*. It is the dominant live failure.

## What DI.2 delivers (leans given)

1. **Exact-name-wins narrowing (the cheapest, highest-value fix — grounded in the
   live finding).** A step whose first token is an **exact** registered tool name
   must resolve to *that* tool, before any fuzzy matching. Today
   `flame_set_start_frames` fuzzy-matches 9 tools; an exact-name short-circuit
   fixes that class outright — and it directly unblocks DI.1's live demonstration.
   *Lean: add exact-name resolution at the top of the narrowing path
   (`_step.py:251` region), ahead of `filter_tools_by_message`.*
2. **Strengthen `deterministic_narrow`** (`:260`) — close the gap that leaves N>1
   for ordinary task phrasings, deterministically where possible.
3. **Bounded candidate-selection** before the `:326` hard-stop — deterministic
   ranking first; **one** LLM selection among the ≤5 candidates only if needed.
   *Selection is control-flow, not meaning* ([[feedback-orchestrator-control-flow-not-meaning]]):
   it picks from the provided set, never invents a tool, never authors prose.
4. **Task-term disambiguation as the fallback, not the default.** If it still
   can't resolve, ask the operator a **task-term** "did you mean?" — **never** the
   "matched N tools" leak nor tool identifiers (`flame_get_clip` vs
   `forge_get_shot`); that is the same developer-facing disease one layer up.
5. **The usefulness redirect DI.1 punted** — *answering a mis-selected read.* DI.1
   blocks `flame_set_start_frames` picked for "duration in frames"; DI.2 is where
   the system **re-selects the correct read tool and actually answers the
   duration** (this needs the narrowing DI.1 was barred from). This is DI.2's win
   column, explicitly.

## Constraints (inherited, binding)

- **Best-effort, not a guarantee** — DI.2 measurably reduces dead-ends; it is held
  to a usability bar, not a safety one. The safety invariant is DI.1's and is
  untouched.
- **Control-flow, not meaning.** Arbitration selects among candidates; no prose, no
  invented tools, no authority decisions.
- **Reads-side.** DI.2 does not weaken DI.1's gate — a mutation that resolves to a
  single tool still hits the gate. DI.2 just makes resolution *succeed* more often;
  DI.1 still decides *may it execute*.
- `forge_bridge.__all__` stays **19**; no new external libraries.

## Open questions for DI.2-discuss (leans given)

- **Q-DI2.1 — exact-name-wins placement.** Top of `narrow_step` before
  `filter_tools_by_message`, or inside it? *Lean: a pre-filter exact-name check —
  smallest, most legible.* Confirm no existing exact-name path already exists
  (the live 9-match says it doesn't, but ground it).
- **Q-DI2.2 — the LLM selection budget.** When does the ≤5-candidate LLM
  selection fire, and what's its cap/latency? *Lean: only when deterministic
  ranking is genuinely tied; reuse the existing router caps.*
- **Q-DI2.3 — the task-term "did you mean?" surface.** Shape of the operator
  prompt without leaking tool identifiers — needs a task-term description per
  candidate. *Lean: derive from tool descriptions, not names.*
- **Q-DI2.4 — the mis-selected-read answer (deliverable 5).** How much re-selection
  is in scope vs deferred? *Lean: re-select among the candidate reads for the
  user's intent; do not attempt full intent re-compilation.*
- **Q-DI2.5 — measurement.** Re-run the DI.1 baseline reads post-DI.2; the win is
  "fewer dead-ends / more reads reach an answer (or DI.1's gate)."

## Status

**Cycle-1 phase-framing draft, 2026-06-01.** Thesis (routing must resolve, not
hard-stop), the exact-name-wins lead (grounded in DI.1's live 9-match finding), and
the control-flow boundary are the load-bearing claims. Five discuss questions carry
leans. Open for cross-voice review, then DI.2-discuss.
