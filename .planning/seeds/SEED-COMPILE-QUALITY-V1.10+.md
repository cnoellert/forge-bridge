---
name: compile-quality
description: "The dominant slice of the dogfood failure corpus is COMPILE quality, not arbitration or authority. DI.2's measurement (DT + Creative, 2026-06-01) sized the 9 live failures at ~33% resolver-overmatch (DI.2-fixable), ~44% bad-compile (the model produced the WRONG operation — injected commit/mutation, broken step, wrong single tool), ~22% other-seam. The ~44% bad-compile class is the larger hill behind DI.2: no amount of arbitration or authority gating rescues a step that doesn't represent the request. This is the 'make chat useful' problem's biggest single class, and it is neither DI.1 (authority) nor DI.2 (arbitration) — it is compile/model quality. The operator has been circling this as the 'Python-fallback' idea (let the model emit Python against the substrate rather than compile to a single tool-step, or otherwise raise compile fidelity)."
type: roadmap
planted: 2026-06-01
planted_during: "v1.10 DI.2 framing, cycle-3. Surfaced when DT's class-proportion grounding put a number on the corpus for the first time and Creative named the consequence: 'make chat useful' is several milestones, not one; DI.2 is one slice; compile quality is the larger one behind it."
trigger_when: "After v1.10 (DI.1 + DI.2) closes. It is the natural successor milestone IF the v1.10 measurement (Q-DI2.5 capture re-run) confirms compile-quality dominates the residual corpus. Do NOT pull it into DI.2 — that is exactly the arbitration-becomes-compilation drift DI.2's boundary exists to prevent."
relates_to:
  - .planning/phases/DI.2-eligibility-arbitration/DI.2-FRAMING.md (§Sizing — the ~44% number + the boundary that keeps DI.2 out of this)
  - UAT/CR.1-dogfood-findings.md (the corpus the proportions were read from; R4/R5/R6/R11 = the bad-compile class)
  - forge_bridge/console/_chat_compile.py (compile_intent / build_compile_system_prompt — the compile surface)
  - .planning/milestones/v1.10-AUTHORITY-INVARIANCE-FRAMING.md (Q-DI3 prompt-mitigation — the small compile lever v1.10 allows; this seed is the large one)
---

# Seed — compile quality is the larger hill behind v1.10

## The finding (numbers, 2026-06-01)

DI.2's sizing put a number on the dogfood corpus for the first time. Of 9 live
failures: **~33% resolver-overmatch** (DI.2's target), **~44% bad-compile**, **~22%
other-seam**. The bad-compile class (R4/R5/R6/R11) is the system producing the
*wrong operation entirely* — a commit on a read, a mutation tool for a duration
question, a broken injected step. **It is the single largest class, and neither
DI.1 nor DI.2 touches it.**

## Why it's neither DI.1 nor DI.2

- DI.1 (authority) gates *whether* a resolved tool may execute. It cannot fix a
  step that resolved to the wrong tool with authority intact.
- DI.2 (arbitration) chooses *among candidates*. It cannot fix a step whose
  candidate set never contained the right tool — that is intent reconstruction,
  the boundary DI.2 explicitly refuses (or it becomes a shadow compiler).

So compile quality is a distinct problem requiring a distinct milestone. The
operator's standing intuition — the **"Python-fallback"** thread (let the model
express intent as Python against the substrate, or otherwise raise compile
fidelity, rather than force a brittle single-tool-step compile) — is the candidate
direction.

## The discipline this seed protects

The v1.10 arc's repeated lesson: each milestone's boundary erodes when it
quietly absorbs the next problem (CR.1 answer-pass → DI.1 authority → DI.2
arbitration). **Do not let v1.10 absorb compile quality.** v1.10 allows only the
*small* compile lever (Q-DI3 prompt-hardening, a mitigation). The large lever is
this seed, deliberately held for after v1.10 measures the residual.

## Trigger

After v1.10 closes, and after Q-DI2.5's capture re-run confirms compile-quality
dominates the residual corpus against *real* candidate sets (not the current
ledger inference). Then this is the natural successor milestone.
