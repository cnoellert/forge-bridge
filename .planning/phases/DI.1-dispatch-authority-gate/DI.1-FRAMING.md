---
milestone: v1.10
phase: DI.1
phase_name: The Dispatch-Authority Gate — one invariant at three execution edges
type: phase-framing
status: cycle-2-draft
drafted: 2026-06-01
derives_from: .planning/milestones/v1.10-AUTHORITY-INVARIANCE-FRAMING.md (ratified + cycle-5) + .planning/milestones/v1.10-DISCUSS.md (cycle-2, DI.1 decomposition)
artifact_role: load-bearing — the DI.1 discuss + plan derive from this. The non-negotiable safety half of v1.10.
grounding: live reads 2026-06-01 — _chat_compile.py:158 (commit-route 1A) + graph/commit.py:75/93; handlers.py:720-722 (forced dispatch 1B; param stops :603/:678); _step.py:409 (chain dispatch 1C); registry.py:65/132 (annotations→add_tool), :127 (PROV-04), :140/180 (register_tools user-taught), :716 (flame_set_start_frames readOnlyHint:False); cli/discover.py:95-110 (annotations readable off the tool object)
---

# DI.1 — The Dispatch-Authority Gate

> **What this is.** Cycle-1 phase-framing for the load-bearing, non-negotiable
> half of v1.10. Derives from the ratified milestone framing; inherits its
> invariant (*operator authority and execution eligibility must not depend on
> routing path*), its consistency reframe (*the system already knows which tools
> mutate; make dispatch act on it*), and its acceptance criteria.
>
> **What this is not.** Not DI.2 (eligibility arbitration — separate phase). Not a
> change to the mutating path itself (preview→ratify→apply is untouched; DI.1
> *prevents reads from entering it* and *prevents mutations from skipping it*).
> Not a classifier (the classification exists — `readOnlyHint`).
>
> **The one-line thesis.** Three execution edges decide a tool's fate without ever
> consulting its declared authority class. DI.1 makes all three consult it —
> **one invariant, uniformly applied** — so a mutation cannot execute outside the
> authority chain by *any* route, and a read is never mis-presented as one.

## The invariant is uniform; the action per site is not — and 1A is not a peer (cycle-2, DT+Creative)

The milestone names "one invariant at three sites." Spelled out, the **invariant**
is *every dispatch decision consults `readOnlyHint` (fail-closed: absent/non-read
⇒ mutating)*. But DT's grounding refined the *delivery*: **the three sites are not
peers.** 1B/1C sit **post-resolution** (a resolved, annotated tool object in hand);
1A sits **pre-resolution** (it reads step *text*, not tools). They fail in
different directions and carry different obligations.

> **The load-bearing sentence (room-confirmed):** *the safety guarantee is carried
> entirely by 1B/1C at the dispatch edge; 1A is a correctness layer that 1C makes
> unfalsifiable as a safety risk.*

| Site | File | When | Today's failure | Guard action |
|---|---|---|---|---|
| **1B — forced dispatch** | `handlers.py:720-722` | post-resolution | a **mutation** executes directly, no ratify | **hard block** at the dispatch edge — shared reader on the resolved tool. *Safety floor.* |
| **1C — chain dispatch** | `_step.py:409` | post-resolution | a **mutation** in a non-commit chain executes, no ratify | **hard block** — same gate, `filtered[0]`. *Safety floor.* |
| 1A — commit-route | `_chat_compile.py:158` | pre-resolution | a **read** chain gets a spurious `commit` → mis-presented as "Ratify & Apply" | **best-effort correctness:** strip-and-execute *only when it can cheaply confirm all non-commit steps are reads*; else leave the preview (annoying-but-safe status quo) |

**Why 1A is demoted, not dropped.** DT traced the worst case: if 1A *wrongly*
strips a commit guarding a real mutation, the chain goes to `run_chain_steps` →
the mutation hits **1C** (`_step.py:409`) → the shared reader sees
`readOnlyHint=False` → **blocked.** A wrong 1A strip degrades to "1C blocks"
(safe) or "preview shown unnecessarily" (annoying) — **never** "unratified
mutation executes." So 1A cannot compromise safety; it only affects experience.

**Why 1A must stay out of the narrowing region (the real fracture).** To classify
its steps, 1A would need the step→tool resolution that lives in `_step.py:251/260`
(`filter_tools_by_message` → `deterministic_narrow`) — **DI.2's machinery.** If 1A
reaches in, DI.1 starts editing the functions DI.2 owns and the fracture we
rejected at the milestone level reappears at the phase level. So 1A is best-effort
*only when cheaply knowable*, and **never reaches into the narrowing functions.**
The clean dispatch-edge split survives precisely because 1B/1C (`:720-722`, `:409`)
are post-resolution edges that need no narrowing.

**The phase boundary this produces:** **DI.1 = nothing dangerous can happen
(trustworthiness); DI.2 = more useful things happen (usefulness).** DI.1 ships its
non-negotiable without secretly solving DI.2's problem first.

## What DI.1 delivers

1. **The shared authority reader.** One helper — *lean: a single
   `dispatch_authority(tool) -> {read|mutating}` reading `tool.annotations.readOnlyHint`
   fail-closed* — called at all three sites. Making the invariant *literally one
   function* is what lets the regression-lock be uniform and what stops the three
   sites from drifting apart later. (Q-DI1.1.)
2. **The registration-boundary close** (`registry.py:127`, Decision 2). Extend
   PROV-04's fail-safe to `user-taught` so consumer tools default
   mutating-until-annotated → the absent set is ∅ universally → fail-closed has no
   flag-day. One line, lands first (substrate-before-consumer).
3. **The three site gates** (the table above), each calling the shared reader.
4. **Fail toward understanding — DETERMINISTIC** (acceptance criterion, not
   implementation detail; **resolved cycle-2, no `acomplete`/CR.1 dependency**).
   *Tight definition (Creative):* fail toward understanding = **explain why
   execution stopped and what class of action would be required to proceed** —
   NOT "help the user accomplish their goal" (that is DI.2). The block path has
   the resolved tool in hand, so the explanation is a deterministic template that
   names the tool's declared class precisely — no model call:
   > Request stopped before execution. · Tool: `flame_set_start_frames` ·
   > Classification: mutating · This path permits read operations only. · Use a
   > ratified operation if you intend to modify project state.
   This *inherits the determinism of the authority substrate it explains* — it is
   auditable, instantaneous, and **available even when the model is down** (DI.1
   is a trust milestone; a trust system explains itself without another AI call).
   The artist leaves with "I understand why nothing happened," not "I got my
   answer." (CR.1-style "let me explain what I think you meant" is a later phase.)
5. **Enabling tooling:** the baseline (re-run the 11 dogfood reads on current
   `main` for a contemporaneous failure-shape record, before any change) and the
   corpus capture-seam extension (fire on `preview_emitted` / `chain_aborted` /
   forced-error with an outcome tag) — so DI.1's effect is measurable.
6. **The regression-lock:** a test asserting **no mutation tool executes via any
   of the three edges without authority** — the tested acceptance criterion.

## Grounding (live, 2026-06-01)

- The classification is **read off an object already in hand**: `cli/discover.py:95-110`
  reads `readOnlyHint` from `getattr(tool, "annotations", …)`; the forced `tool`
  and the chain `filtered[0]` are the same annotated objects `mcp.list_tools()`
  returns. No new accessor, no plumbing — DI.1 is enforcement.
- `flame_set_start_frames` (the breach tool) is registered `readOnlyHint:False`
  at `registry.py:716`. The gate reads what the registry already declares.
- The forced path's only current stops are param-resolution failures
  (`handlers.py:603/678`) — not safety guards; the gate is a *new* check before
  `:720-722`.

## Resolved by the room (cycle-2)

- **Q-DI1.1 — RESOLVED.** One shared reader `dispatch_authority(tool)`, used at
  **1B/1C** (post-resolution, the resolved tool / `filtered[0]` — clean drop-in,
  the whole safety guarantee). **1A is not a drop-in** — it is pre-resolution and
  must NOT reach the narrowing functions (`_step.py:251/260`, DI.2's region) to
  classify its steps. 1A uses the shared reader only on whatever it can *cheaply*
  resolve; otherwise it leaves the preview.
- **Q-DI1.2 — RESOLVED: deterministic template, no `acomplete`.** See deliverable
  #4. A trust guarantee explains itself without a model call.
- **Q-DI1.3 — RESOLVED: strip-safety from the resolved tools, and not
  safety-critical.** `would_mutate`/`requires_ratification` derive purely from the
  bare `commit` token (`_chat_compile.py:102/112`), which carries **no** signal
  about tool mutation-ness (it false-positives *and* false-negatives) — so strip
  safety must come from `dispatch_authority(resolved_tool)` over the non-commit
  steps, NOT from commit semantics. Mechanically the strip is trivial (`commit` is
  a standalone bare node). Crucially: a wrong strip cannot execute an unratified
  mutation — **1C backstops it** — so 1A's strip is best-effort, not safety-load-bearing.

## Open question for DI.1-discuss

- **Q-DI1.4 — regression-lock surface.** Unit (the shared reader fail-closed) +
  integration (each of 1B/1C blocks a known mutation tool at the dispatch edge)?
  *Lean: both; the integration test is the real invariant lock, and it targets
  1B/1C — the safety floor — not 1A.*

## Constraints (binding, inherited)

- `forge_bridge.__all__` stays **19**; no new external libraries.
- The mutating path (preview→ratify→apply, `AssentRecord`) is **untouched** —
  DI.1 gates entry to it, does not modify it.
- **No new model authority.** The redirect explains a block; it never authors
  facts or assent (cut line + 24.4 guard hold).
- Fail-closed everywhere: absent/non-read `readOnlyHint` ⇒ mutating.
- No regression of the CR.1 answer-pass or correctly-routed reads.

## Status

**Cycle-2 phase-framing draft, 2026-06-01** (DT + Creative cycle-1 folded). The
phase tightened into a clean trust/usefulness boundary. Cycle-2 changes:

- **DT — 1A is not a peer of 1B/1C.** 1B/1C are post-resolution dispatch edges
  (clean drop-in, the entire safety guarantee); 1A is pre-resolution and cannot
  reach a resolved tool without invoking DI.2's narrowing. Demoted to a
  **best-effort correctness layer, backstopped by 1C** — and barred from the
  narrowing region (that's where the real fracture lived, not `:409`). Load-bearing
  sentence absorbed: *the safety guarantee is carried entirely by 1B/1C; 1C makes
  1A unfalsifiable as a safety risk.*
- **DT — Q-DI1.3:** commit semantics carry no mutation signal (`would_mutate` is
  the bare token); strip-safety comes from the resolved tool, and a wrong strip
  degrades to "1C blocks," never an unratified mutation.
- **Creative — Q-DI1.2 flipped to DETERMINISTIC.** No `acomplete`/CR.1 in DI.1: a
  trust guarantee explains itself without a model call. "Fail toward understanding"
  tightened to *explain why it stopped + what class would proceed* — not *help
  accomplish the goal* (DI.2). Phase boundary: **DI.1 = nothing dangerous; DI.2 =
  more useful** — with the standing caution that DI.2 must follow immediately and
  land (the project's historic over-investment in trust without usefulness).

One open question (Q-DI1.4, regression-lock surface). Ready for DI.1-discuss.
