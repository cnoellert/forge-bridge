---
milestone: v1.10
phase: DI.2
phase_name: Eligibility Arbitration — make routing resolve instead of hard-stop
type: phase-framing
status: cycle-1-draft
drafted: 2026-06-01
derives_from: .planning/milestones/v1.10-AUTHORITY-INVARIANCE-FRAMING.md (ratified) + v1.10-DISCUSS.md (Q-DI2) + .planning/phases/DI.1-dispatch-authority-gate/DI.1-CLOSE.md (the meta-finding that makes DI.2 the priority)
artifact_role: load-bearing — the usefulness half of v1.10. The framing's standing commitment: DI.2 follows DI.1 immediately and actually lands.
grounding: live reads 2026-06-01 — _tool_filter.py:292 (filter_tools_by_message — rule-c token-overlap match is why an exact name pulls 9 tools; PR17/PR18 exact bucket exists but lacks precedence) + :425 (deterministic_narrow); _step.py:251 (filter call site) → :326-337 (exactly-one-or-die hard-stop; candidates at :334); DI.1 live confirmation (exact `flame_set_start_frames` matched 9 tools and aborted before the gate)
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

## The boundary DI.2 must defend (Creative, cycle-2 — the milestone's success criterion)

DI.1's lesson was *don't let safety work secretly become usability work.* **DI.2's
lesson: don't let arbitration work secretly become compilation work.** DI.2 owns
*"choose correctly among available candidates"*; it **explicitly refuses** *"figure
out what the user really meant."* Those are different jobs — arbitration vs intent
reconstruction. The live corpus has both failure classes; DI.2 scopes to the first
and treats the second as evidence the *next* problem exists, not as its own work:

- **Resolver failure = DI.2 territory.** The system understood the request well
  enough to produce the *correct operation*, but candidate selection failed (exact
  name → 9 tools; near-identical candidates; overlapping descriptions; narrowing
  can't choose among a small set). Intent is already present; the resolver just
  failed to select. Fixing these makes the tool feel smarter.
- **Compile failure = NOT DI.2.** The system produced the *wrong operation* ("list
  the projects" → matched staged tools). No arbitration rescues a bad understanding
  — asking the resolver to fix it makes DI.2 a **shadow compiler**, repeating the
  exact boundary erosion DI.1 escaped. That's a compile/model problem for a future
  milestone. **DI.2 succeeds if the system chooses better among plausible
  interpretations; it fails if it becomes responsible for creating new ones.**

## What DI.2 delivers (leans given)

1. **Exact-name-wins (the highest-leverage fix — grounded + sharpened, cycle-2).**
   *Why it matters (Creative): exact-name failure is a **trust** hit, not just an
   accuracy one.* When an operator types `flame_set_start_frames` and gets "9
   candidates," the reaction is *"the system ignored what I typed."* **Grounded fix
   shape (Orch read of `_tool_filter.py:292`):** the matcher already has an
   exact-match bucket (PR17/PR18) — but it returns it **alongside** token-overlap
   matches (rule c: any name-token in the message → `flame_set_start_frames`'s
   tokens `flame/set/start/frames` pull in every `flame_*`/`set`/`frames` tool =
   the 9). So this is **not** "add a path that doesn't exist" — it is *"when a
   unique exact-name match exists, return **only** it, dropping the token-overlap
   others."* Precedence/exclusivity, a smaller change than assumed. Removes a
   category of failures that feel irrational, and unblocks DI.1's live demo.
2. **Strengthen `deterministic_narrow`** (`:260`) — close the gap that leaves N>1
   for ordinary task phrasings, deterministically where possible.
3. **Bounded candidate-selection** before the `:326` hard-stop — deterministic
   ranking first; **one** LLM selection among the ≤5 candidates only if needed.
   *Selection is control-flow, not meaning* ([[feedback-orchestrator-control-flow-not-meaning]]):
   it picks from the provided set, never invents a tool, never authors prose.
4. **Task-term disambiguation as the fallback, not the default** (Creative,
   sharpened). Ask the operator to choose an **outcome, not a tool** — *"Show
   assets used by this shot" / "Show versions in this shot's stack"*, never *"Did
   you mean `forge_list_assets` or `forge_get_shot_stack`?"* (the artist must never
   learn the ontology). **Task-label generation is itself best-effort:** derive
   labels from tool descriptions where they're good enough; **fall back to a
   generic ambiguity explanation when they're poor.** *Don't invent clarity that
   isn't present* (the cut line, one layer up). Never the "matched N tools" leak.
5. **The usefulness redirect DI.1 punted — with a hard boundary** (Creative). DI.2
   re-selects among *known candidates* and may *ask the user to choose among
   candidate intentions*. It MUST NOT **generate a new interpretation** of the
   original request — the moment it says *"maybe you actually meant …"* and
   synthesizes a fresh operation, it has crossed from arbitration into
   recompilation (a future milestone, if anywhere). Re-select: yes. Re-interpret:
   no.

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

- **Q-DI2.1 — exact-name-wins placement. GROUNDED (cycle-2):** the exact bucket
  already exists in `filter_tools_by_message` (`_tool_filter.py:292`, PR17/PR18) —
  it just lacks *precedence*. So the fix is exclusivity, not a new path: *when the
  exact bucket has exactly one member, return `[that]` and drop `other_matches`.*
  Smallest change is inside `filter_tools_by_message` (the bucket logic), not a new
  pre-filter. *Remaining for discuss:* the multi-exact case (≥2 exact matches) —
  fall through to ranking, not collapse.
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

**Cycle-2 phase-framing draft, 2026-06-01** (Creative pass + Orch matcher grounding
folded). Cycle-2 changes:

- **The boundary section added (Creative — the milestone's success criterion):**
  DI.2 owns arbitration (resolver-overmatch class), explicitly refuses
  recompilation (bad-compile class). *DI.2's lesson: don't let arbitration secretly
  become compilation* — the mirror of DI.1's discipline.
- **Exact-name-wins sharpened + grounded (Orch read of `_tool_filter.py:292`):** the
  exact bucket exists but lacks precedence; the fix is exclusivity-when-unique, a
  smaller change than the "no path exists" assumption. Trust framing (Creative):
  exact-name failure reads as *"the system ignored what I typed."*
- **Did-you-mean → outcome-not-tool, best-effort task labels** with a generic
  fallback when descriptions are poor ("don't invent clarity that isn't present").
- **Deliverable 5 hard boundary:** re-select among candidates / ask among candidate
  intentions = allowed; generate a new interpretation = NOT (recompilation, future
  milestone).

Five discuss questions (Q-DI2.1 now grounded). Ready for DI.2-discuss — pending only
DT's class-proportion grounding (how much of live Symptom 2 is resolver-overmatch
(a) vs bad-compile (b)), which sizes DI.2's reachable win.
