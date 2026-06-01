---
milestone: v1.9
phase: CR.1
type: phase-close
status: closed-mechanism-shipped-corpus-frozen
closed: 2026-06-01
honest_scope: "Shipped the mechanism CR.1 promised — the (b) answer-pass on successful reads + structured passthrough on aborted reads — and ran the author-driven dogfood that produced the comprehension corpus. The dogfood's finding is that the mechanism is attached at the wrong seam for the real failure distribution: mildly-complex reads fail UPSTREAM of chain_complete, so the answer-pass never fires on them. Non-developer artist UAT did NOT happen and stays open; this close makes no artist-comprehension-fidelity claim."
grounding: "Live dogfood 2026-06-01 against the projekt_forge consumer surface (76 tools) on bridge's own :9996 (stdio-held-open, current main). 11 reads, wire captured. Findings: UAT/CR.1-dogfood-findings.md (committed 24c2de5) + 2 screenshots."
supersedes_question_from: .planning/phases/CA-thread-a-console-authority/CA.1-CLOSE.md (the milestone question "should the chat synthesize?")
---

# CR.1 — Close (mechanism shipped, corpus frozen, seam named)

> CA.1-CLOSE handed v1.9 one question: **should the chat synthesize — should the
> no-synthesis law be reversed for the human-facing answer?** CR.1 answered *yes,
> on reads* — it added the (b) `acomplete` answer-pass at `chain_complete`. This
> close records what shipped, and what the dogfood revealed: synthesis was the
> right answer to the wrong half of the problem. The chat now *can* answer a human
> when a read succeeds — but mildly-complex reads mostly fail before they ever
> reach the seam where the answer-pass lives.

## What shipped (goal-backward against CR.1-FRAMING's three deliverables)

1. **(b) answer-pass on successful reads — DONE, live-confirmed.** At the
   `compiled_non_mutating` / `chain_complete` seam, a single `acomplete` turn
   synthesizes the `[{step, result}]` chain + the user's question into plain,
   attributed prose (`messages` assistant turn; zero-JS Console render via the CA.1
   de-blank guard). The forced-tool amendment (`a95bf0d`) extended both the answer
   and the capture to the PR20 single-result short-circuit. Confirmed live:
   `list the projects` → *"The projects listed are: 1. 013_13_13… 2. chatTest"*,
   plus an L4 corpus record. `__all__` == 19; version 1.5.1; rides existing
   `LLMRouter.acomplete`; no new public symbol.
2. **Structured failure-indication passthrough on aborted reads — SHIPPED as
   specified.** `chain_aborted` carries `code` / `original_error` / `step_index`
   through to the consumer with no model prose (orchestrator-mute held). Confirmed
   in the dogfood wire (e.g. `CHAIN_STEP_FAILED` + `original_error` + `step_index`).
   **But the spec under-served the human** (see §The finding): the passthrough is
   structurally correct and still developer-facing — *"Step matched 4 tools; use a
   more specific verb"* is not an artist-readable message. CR.1 explicitly deferred
   rich failure legibility to a corpus-ranked tier; that deferral now has its
   evidence.
3. **The comprehension corpus — PRODUCED (author-driven), FROZEN at 11 reads.**
   The dogfood ran (`24c2de5`); the wire ledger + taxonomy live in
   `UAT/CR.1-dogfood-findings.md`. **The non-developer artist UAT the framing named
   (per `project-forge-bridge-ux-philosophy`) did NOT happen.** This was
   author-driven. Artist UAT is an explicit open carry-forward, and this close does
   not claim artist-comprehension fidelity
   (`feedback-operational-maturity-not-completeness`).

## The finding that matters (the real v1.9-CR.1 learning)

**The answer-pass is attached at the wrong seam for the real failure distribution.**

The (b) pass humanizes `chain_complete` — success only. But across 11 reads,
**mildly-complex reads overwhelmingly fail _upstream_** — at intent compilation and
tool resolution — so the humanization layer never runs on them. Every tool that
*executed* returned correct, well-structured data (iteration `6`, batch groups,
reels). The legibility bottleneck is in the compile layer, **before the model is
allowed to speak.** Counts: 11 reads · 2 correct · 9 failed · only 3 wrote corpus
records.

This **extends CA.1's finding rather than refuting it.** CA.1: "the chat is a
console; a human answer IS synthesis; the architecture drifts away from chat every
phase." CR.1 added the synthesis — and proved it necessary-but-insufficient: A.1's
"compile before execute" moved the conversational burden from the model to a
deterministic compiler, and **that compiler is now the thing that can't talk to a
human.** Adding prose at the end doesn't help a sentence the compiler couldn't
route.

### Failure taxonomy (ranked; full wire in the UAT doc)

- **Compile/resolution layer — DOMINANT (7 of 9):**
  1. **Reads miscompiled into the mutating branch (3×) — DOCTRINE BREACH.** A
     `__commit__` step injected onto reads, or `flame_set_start_frames` *forced* on
     *"duration in frames"*. The reads-vs-mutations split CR.1-FRAMING calls
     *structural* was crossed by the compiler. Highest severity: a read must never
     reach the mutating branch. (This is the same family the framing's structural
     guard was meant to make impossible — the guard holds for the *answer-pass*, but
     not for *tool selection*.)
  2. **Resolver paralysis (3×).** A step matching N>1 tools → exact-match resolver
     refuses → internal hint leaked to the artist. The documented
     `pre-orchestration-resolution-paralysis` shape, live on ordinary reads.
  3. **Compiler-injected broken step (1×).** A complete read (iteration `6`) killed
     by an appended malformed `format_result`.
  4. **No session/project scope (1×).** Every project-scoped read is ambiguous
     (`MULTIPLE_PROJECTS`), answered with a raw error instead of "which project?".
- **Answer-pass layer — SECONDARY (2 of 9):**
  5. **Fabrication from missing field.** `flame_list_desktop` had no desktop-name
     field; the pass invented *"Untitled Batch"* from an adjacent value — a breach
     of the cut line (*"MAY NOT synthesize facts that do not exist"*).
  6. **Raw error envelope as prose.** A `ToolError` stringified as the answer; the
     pass doesn't triage error envelopes.

## The corpus-instrument blindspot (a finding about the instrument)

Capture writes only on success / forced-success. **Of 11 reads, 3 wrote records;
the 8 silent ones are exactly the compile/resolver/mutation/abort/error failures
that dominate.** A ranking driven by the JSONL alone would systematically
under-weight the compile-layer class that *is* the problem. The manual wire ledger
in the UAT doc exists because the automated instrument could not see most of what
happened. Fixing capture to record the `preview_emitted` / `chain_aborted` / error
seams (with an outcome tag) is itself ranked work — distinct from the known
two-path (compile-reaching vs forced-tool) limitation.

## What this close does NOT do

- Does **not** claim artist-comprehension fidelity. Author-driven only; non-developer
  UAT stays open.
- Does **not** fix anything in the substrate. Zero substrate-data failures were
  found; per `project-substrate-to-usability-crossing`, these failures are *meant*
  to be human/legibility — the crossing is working as designed. "Fixing" the
  compile-layer findings tonight would be the documented trap.
- Does **not** open the next legibility milestone. The ranking (below) is
  milestone-framing input, not a phase backlog.

## Ranked input to the next legibility milestone

Per `UAT/CR.1-dogfood-findings.md §7`: ① stop reads compiling into the mutating
branch (doctrine breach) → ② kill resolver paralysis / never leak "matched N tools"
→ ③ move or duplicate the legibility seam upstream of `chain_complete` → ④ session /
project scope → ⑤ answer-pass refuse-on-missing-field + error-envelope triage → ⑥
fix the corpus instrument to capture failure seams.

## Methodology

- **CA.1's lone candidate is corroborated → promotion-grade.** CA.1 named: *a phase
  whose output is human-facing needs a human-legibility gate the substrate-grounding
  machine cannot supply.* CR.1 *supplied that gate* (the dogfood) and it worked
  exactly as the candidate predicted — the writing-room machine had ratified the
  mechanism cleanly (grounded citations, DT/Creative fold, live `acomplete` probe at
  2.5 s), and none of that noticed the answer-pass sits downstream of where reads
  fail. Only driving real reads surfaced it. **The human-legibility gate is not
  optional ceremony for human-facing phases; it is the only stage that sees the real
  failure distribution.**
- **The corpus-blindspot is a second instance of the same shape:** the automated
  instrument (capture-on-success) is substrate-shaped and blind to the failures that
  matter; the human-driven ledger caught them. Sibling to
  `feedback-failure-shape-stability-as-disposition-evidence` and the
  `ground-specs-in-actual-files` family.

## Status

**CR.1 CLOSED.** Mechanism (b) answer-pass + structured-abort passthrough: shipped,
live-confirmed. Author-driven comprehension corpus: produced, frozen at 11 reads,
findings committed (`24c2de5`). Non-developer artist UAT: **open carry-forward.**
Headline finding — answer-pass attached at the wrong seam; compile layer is the
legibility bottleneck — handed to the next milestone as ranked framing input. No
substrate fix; crossing working as designed.

---

*Closed 2026-06-01. Mechanism is real and shipped; the corpus is real and frozen;
the artist UAT is honestly still owed. The seam finding is the asset — it tells the
next milestone where to aim.*
