---
name: SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+
description: Forward-looking methodology artifact capturing the discipline used in Phase A, A.4, and A.5/A.6 reliability work. Two distinct categories — procedural mechanics + reliability character. Promotion to formal methodology gated on additional successful reliability phases.
type: forward-looking-idea + framing-artifact
planted_during: 2026-05-06 (Phase A.6 closure)
trigger_when: Three or more reliability phases have shipped using these patterns successfully, OR a new contributor needs orientation on how reliability work is approached in this project, OR a future phase asks "should we formalize this as docs/methodology/reliability-phase.md?"
---

# SEED-RELIABILITY-PHASE-METHODOLOGY: Reliability discipline — procedure + character

## What this seed is

A forward-looking record of the reliability-work patterns that emerged across Phase A (truthful chat contract), A.4 (startup-path unification), and A.5/A.6 (chain-execution reliability + daemon-runtime integrity).

It is NOT a methodology spec yet. The procedural patterns are sample-size 3; the character observation is sample-size 1. Promotion to a formal `docs/methodology/reliability-phase.md` is **gated on additional reliability phases** producing the same patterns under genuinely independent conditions. Premature formalization is itself a failure mode this seed exists to avoid.

## Two categories — distinguished deliberately

The patterns split into two categories that protect against different failure modes:

| Category | Protects against | Sample size |
|----------|-------------------|-------------|
| **Procedural mechanics** — what to do | Doing reliability work in a sequence that compounds errors | 3 |
| **Reliability character** — how to behave when doing it gets hard | Abandoning the procedure under pressure or emotional momentum | 1 |

These are intentionally separate. A team can know the procedure and still fail to apply it under stress. A team can have the right instincts and still produce shallow work without the procedure. Both are needed; neither subsumes the other.

---

## Category 1 — Procedural mechanics

Three observations, each captured during A.6, each independent of the others.

### 1.1 Map first, probe second

**What it means.** Before instrumenting a runtime to find a defect, statically map the runtime: identify entry points, loop ownership, lifecycle ordering, where suspect resources are constructed and consumed. Use that map to compress the hypothesis space *before* the probe runs.

**Why it works.** A static map is cheap (hours of reading), refutes structurally implausible hypotheses without instrumentation, and tells you *where* to instrument so that the probe answers the actual question. Probing without a map produces clean traces that explain nothing — because the probe was placed in the wrong code path.

**Concrete instance (Phase A.6).** The Step 1 lifecycle map's lazy-allocation finding (router clients allocated only at first use, not at construction) downgraded "wrong-loop affinity" from a top hypothesis to structurally implausible *before* the Step 2 probe ran. The map's masking-relationship subsection identified the failing surface as the lazy-allocation LLM-loop path specifically — which directly determined where the probe was placed. Probing the wrong path (the PR20 short-circuit) would have produced clean traces and told us nothing.

**Forward rule.** When a runtime defect needs investigation, write the lifecycle map before writing the probe. If the map cannot be written confidently, that is itself a finding — the runtime may be too tangled to investigate without redesign.

### 1.2 Verify the bisect is causal, not co-incident

**What it means.** A bisect window can identify a commit that is *temporally* co-located with a regression without that commit being the *cause* of the regression. Before committing to deep-runtime investigation of a bisect-identified commit, run a cheap environmental ruleout pass: network reachability, environment variables, host resolution, dependency availability.

**Why it works.** Bisects are powerful when the regression is in code. They mislead silently when the regression is environmental and a code change happens to land in the same time window. Two minutes of `ping` / `nc` / `curl` against the suspected dependency rules out the most common environmental cause. That ruleout is far cheaper than a multi-step runtime audit.

**Concrete instance (Phase A.5.1 → A.6).** A.5.1's bisect window contained exactly one substantive commit (Phase A.4's `bootstrap_daemon`), and the commit's diff matched every named hard-elevate trigger phrase in the spec verbatim. The bisect was diagnostically correct discipline, but it ran on circumstantial evidence: commit timing plus symbol overlap. The actual cause was an unreachable cross-host LLM endpoint — the Phase A.4 commit landed approximately 90 seconds *after* the last-healthy session and was co-incident with a network state change, not its source. A 2-minute reachability check would have caught it before A.6 opened.

**Forward rule.** When a hard-elevate condition triggers on a bisect window, run a cheap environmental-cause ruleout pass *before* committing to the elevated phase's full diagnostic sequence. This is **not** a reason to skip the elevate — the discipline of evidence-before-patching remains correct. It is a reason to bound the elevated phase tighter and discover environmental causes in seconds rather than steps.

### 1.3 A reliability phase's substantive output is not always a fix

**What it means.** A reliability phase that opens to investigate a suspected defect is doing its job whether it ends in a fix, in structural confirmation that no defect exists, or in environmental remediation that touches no code. The output is *evidence about the system*, not necessarily a code change.

**Why it works.** Phases that measure their success by "did we ship a fix?" implicitly pressure the team toward finding something to fix even when the substrate is correct. That bias compounds across phases. Phases that measure their success by "did we produce structural evidence?" let the system tell the truth — which sometimes is "this is fine; the problem is elsewhere."

**Concrete instance (Phase A.6).** A.4 entered A.6 as the prime suspect. The investigation produced a durable lifecycle map, three independent lines of evidence about the runtime, and a confirmed-environmental classification. No A.4 code was modified. A.4's startup-path unification is now structurally confirmed correct, in a stronger sense than "still appears to work." The phase shipped value despite touching no production code.

**Forward rule.** A reliability phase's exit criteria should include "structural evidence captured, classification documented" alongside (or instead of) "fix landed." Future runtime work can reason against captured maps and findings as verified baselines rather than reading code fresh every time.

---

## Category 2 — Reliability character

One observation, captured during A.6 and worth distinguishing from the procedural three.

### 2.1 Discipline vindicated before evidence existed

**What it means.** The hardest part of reliability work is not knowing the procedure. It is *holding* the procedure when the symptoms are emotionally compelling and the temptation to patch is strong. Evidence-before-patching is a *behavior*, not a mechanic.

**Why this is categorically different from the procedural observations.** Items 1.1, 1.2, and 1.3 describe what a team *does*. This describes how a team *behaves when doing it gets hard*. Procedure tells you to map the runtime before probing. Character is what keeps you mapping the runtime when the codebase has a recent commit that *looks like* the obvious cause and your instincts are screaming "just look there."

**Concrete instance (Phase A.5.1 → A.6).** A.5.1 elevated to A.6 when the bisect window matched named trigger phrases verbatim. The emotional-narrative pull at that moment was *very strong*: "the recent commit is the cause; we know what to do; just look at `bootstrap_daemon`." Two factors held the procedure under that pull:

1. The phase spec had been written to make hard-elevate **mandatory** when triggers matched — not optional, not subject to override on instinct.
2. The discipline of *not patching during diagnosis* was bound at the spec level, not at the implementer's discretion.

The procedure was vindicated three steps later, when Step 3's environmental probe revealed the real cause was network reachability, not code. If the elevate had been treated as advisory, or if Step 1-2's diagnostic-only authorization had been negotiable, the team would have been hours into refactoring `bootstrap_daemon` before discovering the actual cause was external.

**The protective value was structural, not procedural.** The spec did not just describe what to do; it removed the option of doing something else under pressure. That removal is what character looks like as code.

**Forward rule.** Reliability phase specs should explicitly remove patching authority during diagnostic phases — not as guidance but as a hard boundary. The boundary protects against the team's own future emotional state, not against incompetence. A team that knows the procedure and respects it in calm conditions will still default to "just look there" when the suspect is obvious. The spec must be the thing that says no.

---

## Why distinguish these two categories

Each protects against a different failure mode. A team that has internalized the procedural mechanics but lacks reliability character will skip the procedure the moment the bisect "obviously" points somewhere. A team that has reliability character but no procedural mechanics will resist patching impulsively but produce shallow analysis because they don't know how to map a runtime or how to verify a bisect.

The distinction also matters for hiring, onboarding, and review:

- Procedural patterns can be taught from a doc.
- Character has to be modeled, written into specs as binding constraints, and reinforced by the project's accumulated decision history.

A docs/methodology document can capture the procedural patterns directly. The character observation has to be captured as the kind of *constraint* that shows up in phase specs ("STOP if X; do not patch around it") and in retrospectives that ask "what kept us honest when the procedure got hard?"

---

## Promotion gate

This seed becomes `docs/methodology/reliability-phase.md` when:

1. At least **two more reliability phases** ship with the procedural patterns applied successfully under genuinely independent conditions (different subsystem, different failure mode, different team-state pressure).
2. The character observation has been tested in at least **one phase where the bisect or symptom pull was genuinely misleading** and the discipline held — otherwise the character observation is sample-size 1 and could be artifact-of-circumstance.
3. The promotion is itself decided in a phase or retrospective that asks the question explicitly — not as a side-effect of someone deciding the project should have a methodology doc.

Until those conditions hold, this seed is the durable form. It can be referenced in phase specs (e.g. "see SEED-RELIABILITY-PHASE-METHODOLOGY for the discipline this phase inherits") without being elevated to formal methodology.

---

## Cross-references

- `docs/learnings/a4-runtime-integrity-confirmed.md` — concrete instance of pattern 1.3 (reliability output is structural confirmation, not code change).
- `.planning/phases/A.6-daemon-runtime-integrity/RUNTIME-MAP.md` — concrete instance of pattern 1.1 (map first).
- `.planning/phases/A.6-daemon-runtime-integrity/STEP-3-FINDINGS.md` — concrete instance of pattern 1.2 (bisect causal verification).
- `.planning/phases/A.6-daemon-runtime-integrity/A.6-CLOSE.md` — synthesis across patterns 1.1–1.3.
- `.planning/phases/A.5-chain-execution-reliability-audit/PHASE-A.5-SPEC.md` and `A.5.1-ELEVATE.md` — concrete instance of character observation 2.1 (mandatory hard-elevate, removal of patching authority during diagnosis).
- `docs/learnings/2026-05-06-phase-transition.md` — project-level framing of the operational-adulthood transition that surfaced these patterns.
