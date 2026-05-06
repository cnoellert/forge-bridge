# 2026-05-06 — Interlocking architecture as a durability property

A short observation captured during the A.5.3.2 instrument-contract
landing. Worth surfacing as a worked example because the pattern is
generalizable.

---

## The observation, in one sentence

**Architectural contracts resist drift not when each rule is
individually strong, but when the rules interlock — each rule
reinforcing others such that removing any single one weakens the
protection that others depend on.**

The opposite property — rules that merely coexist without
reinforcing each other — is what produces contracts that "look
sound" but corrode under contributor pressure: any one rule can be
relaxed in isolation without obviously breaking the others, so each
relaxation looks locally defensible until the whole structure is
gone.

Interlocking is not a stylistic preference; it is the **durability
property** of an architectural contract. Worth checking for
explicitly during contract review.

---

## Worked example: A.5.3.2 instrument contract

Six interlocking pairs landed in the A.5.3.2 instrument contract.
Each pair is two rules that together protect against the same
class of drift, where removing either side substantially weakens
the other:

| # | Pair | What it protects against | Why removing either side weakens both |
|---|------|--------------------------|----------------------------------------|
| 1 | I-1 (Layer 1 append-only / immutable) ↔ §8.10 (no retroactive enrichment exclusion) | Comparator output silently merging back into the observational record | Without I-1, "let's just enrich the file" is technically allowed — exclusion alone doesn't enforce anything. Without §8.10, the immutability is a convention, not a contract surface — easily walked back. |
| 2 | I-2 (no outcome labeling in Layer 1) ↔ §8.11 (no outcome labeling exclusion) | Classification creep into the observational layer | Without I-2, the schema admits interpretive fields. Without §8.11, the schema's purity has no documented rationale future contributors can cite when rejecting "just one classification field." |
| 3 | I-3 (comparator runs in separate process) ↔ §8.8 (live correlation architecturally prohibited) | Live LLM-call coupling under the guise of "convenience" or "performance" | Without I-3, "make it a daemon background task" is ergonomic. Without §8.8, the process boundary alone could be relaxed for "small optimizations" that re-introduce coupling. |
| 4 | §5 AMBIGUOUS bucket ↔ §8.9 (no automatic heuristic synthesis) | The corpus learning to lie about its own ambiguity | Without AMBIGUOUS, every record is forced into one of four buckets — including ones that don't fit, corrupting distributions. Without §8.9, even an honest classifier becomes a feedback signal that auto-tunes the narrower toward planner-agreement frequency (the named threat in §1). |
| 5 | §3 source field ↔ §6c source-aware analysis discipline | Threshold decisions computed against mixed fixture/runtime data | Without the field, segmentation is impossible. Without the analysis discipline, the field is decorative — present in records but ignored in queries, producing noise. |
| 6 | §3 identity fields (narrower hash, tools-snapshot hash, daemon SHA) ↔ §9 identity-mismatch soft-warn handling | Replay across drifted environments producing silent miscomparisons | Without identity capture, there's nothing to detect drift against. Without the soft-warn handling, captured fingerprints are dead data — looked at by humans occasionally, never gating analyses. |

For each pair, removing either side leaves a contract that *appears*
to still cover its concern. Both sides together are what make the
protection contributor-resistant.

---

## Generalization

The recognition pattern: **when reviewing an architectural contract,
check whether boundaries interlock vs. merely coexist.**

- **Interlocking** boundaries = each rule has at least one other rule
  whose protection depends on it. Removing rule X exposes a flaw in
  rule Y. The contract structure is meshed.
- **Coexisting** boundaries = each rule stands alone. Removing rule
  X leaves rule Y's protection intact (or appearing intact). The
  contract is a list, not a structure.

Lists rot under contributor pressure because each item can be
debated in isolation, and "this one rule isn't doing much on its own"
is an easy local argument. Structures resist rot because removing
one rule visibly degrades others, making the local argument harder
to make.

This is not a claim that every rule must interlock with every other
— some rules legitimately cover concerns nothing else touches. It is
a claim that **the load-bearing protections** in a contract should
interlock, and that interlock is detectable at review time by the
"removing X weakens Y" check.

---

## When this matters most

The interlock check matters most for contracts that protect against
**slow-drift failure modes** — failures that don't surface in any
single PR but accumulate across many. The A.5.3.2 contract protects
against the narrower-becomes-planner drift, which is exactly that
shape: no single change blurs the boundary; many small changes do.
A list-shaped contract would fall to that drift; a structure-shaped
contract resists it.

For tactical contracts (one-off fixes, single-PR features), the
interlock property is less load-bearing. The pattern shows its value
on contracts that have to survive many years of contributor turnover
and many incremental amendments.

---

## Cross-references

- `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-INSTRUMENT-CONTRACT.md` —
  the worked example.
- `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-FRAMING.md` —
  the framing the contract operationalizes.
- `.planning/seeds/SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` —
  the methodology seed where this recognition pattern is appended
  under "Reliability character."
