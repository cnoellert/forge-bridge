---
milestone: v1.10
phase: DI.2
phase_name: Eligibility Arbitration — make routing resolve instead of hard-stop
type: phase-framing
status: cycle-3-draft
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
**Correction (DT cycle-3, same over-claim family as the 9-match):** the resolver is
a *dominant* failure, **not the universal one.** Against the original dogfood ledger
only **3 of 11** reads died at the resolver (R8/R9/R10); R1/R2 reached tools and
returned data, R4/R5 reached the mutating preview, R6 executed
`forge_get_batch_iterations` (got `6`) before its injected step, R11 executed
`flame_set_start_frames`. My earlier "*every* request died at the resolver" was a
**degraded-model session** observation (today's daemon compiled everything to the
same staged-tool ambiguity), not the corpus — corrected here. The sharpest valid
evidence stands: the exact step `flame_set_start_frames` matched **9 tools**. So:

- DI.1's safety value is **partly** latent until DI.2 lets *more* requests reach the
  dispatch edge. DI.2 lowers a dominant wall in front of the gate — not the only one.
- Resolver paralysis intercepts ordinary reads *and exact tool names* — a real,
  dominant class, but ~3/9 of the live failures, not all of them (see §Sizing).

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

## Sizing — DI.2's reachable win is ≤3 of 9 (DT ledger + Creative reframe, cycle-3)

The room now has **a number**, and it reframes the whole milestone. Classifying the
9 live dogfood failures by whether DI.2's resolver work can move them:

| Class | Reads | DI.2-reachable? |
|---|---|---|
| (a) resolver-overmatch — "matched N tools" paralysis | R8, R9, R10 | **Yes** — DI.2's target |
| (b) bad-compile — `__commit__`/mutation injected, broken step, or wrong single tool picked | R4, R5, R6, R11 | No (compile/model; R4/R5/R11 also DI.1-owned) |
| other-seam — answer-pass fabrication / session scope | R3, R7 | No (different layers; R7 is a ranked item) |

**DI.2's reachable win = up to 3 of 9 (~33%), and 3/9 is an *upper bound*, not a
point estimate** — DI.2's selection only reaches the answer if the correct read
tool is actually in the tied candidate set; if a too-narrow compile excluded it,
that read is really (b) even though it presents as "matched N." Which it is can't be
told yet — *the candidate sets were never captured* (see §Measurement).

**Scope-discipline vindicated by the numbers (DT):** R6 (broken `format_result`)
and R11 (wrong tool forced) *look* like resolver failures but are compile failures.
"Fix the aborts" would silently annex them — the model-fixing drift the boundary
exists to prevent.

**The reframe that matters (Creative):** the rough proportions — **~33% resolver
(DI.2), ~44% compile/model, ~22% other-seam** — show *resolver quality is not even
the majority problem.* DI.2 is no longer unconsciously asked to solve "make chat
useful." It materially improves ~1/3 of the observed corpus; it does **not** solve
compile quality, session scope, or answer fidelity. That is a worthwhile milestone
*provided the room stops treating it as the whole answer* — and ≤3/9 must not become
a reason to *weaken* DI.2 either (one-third of real pain is meaningful). **"Make chat
useful" is now evidenced to be several milestones, not one** — and the
**compile-quality class (~44%) is the larger hill behind DI.2** (seed:
`SEED-COMPILE-QUALITY-V1.10+`).

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
- **Q-DI2.5 — measurement (sequence FIRST; DT cycle-3).** The (a)/(b) proportion is
  currently **ledger-grounded, not corpus-reproducible** — *neither corpus captured
  the compiled step + candidate set* for the live aborts (comprehension recorded
  only `{outcome,answer:""}`; divergence holds only fixtures, `divergence_capture`
  was off during the dogfood). The cheap fix is **not new code**: the divergence
  instrument already records `prompt` + `candidate_set_post_pr14` +
  `narrower_decision` on the multi-match rejection path (`_step.py:310-324`).
  *Enable `divergence_capture` on the DI.2 baseline re-run* to harvest candidate
  sets directly — **reading the existing instrument for measurement, not merging it
  into the comprehension schema** (respects the CLAUDE.md don't-couple constraint).
  Then "3 of 9" is confirmed against real sets, and DI.2's win is measurable.
  **So Q-DI4-style capture lands first in DI.2; plan to a stated ceiling of ≤3/9,
  explicitly contingent, until then.**

## Status

**Cycle-3 phase-framing draft, 2026-06-01** (DT class-proportion grounding + Creative
reframe folded). Cycle-3 changes:

- **DI.2 is SIZED: ≤3 of 9 live failures (~33%), an upper bound, contingent** on the
  right tool being in the tied candidate set (DT). The room finally has a number;
  resolver quality is **not the majority problem** (~44% compile, ~22% other-seam —
  Creative). DI.2 is no longer asked to be "make chat useful."
- **Over-claim corrected:** "every request died at the resolver" was a degraded-model
  session, not the corpus (3/11 actually did). Dominant ≠ universal.
- **Measurement-debt pattern named (DT+Creative):** this is the **3rd** time this
  milestone the live instruments couldn't substantiate a load-bearing claim (CR.1
  abort-blindness → DI.1 gate-not-live-demonstrable → DI.2 sizing-not-reproducible).
  That's dogfood *success* (it found where instrumentation doesn't observe pain) and
  convergence, not drift — **carry into the v1.10 close.** Q-DI2.5 sequences the
  capture fix first so the sizing becomes reproducible.
- **Roadmap seed:** the compile-quality class (~44%, the larger hill behind DI.2;
  the Python-fallback thread) → `SEED-COMPILE-QUALITY-V1.10+`.

Cycle-2 changes (retained):

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
