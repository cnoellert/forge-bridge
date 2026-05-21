---
name: SEED-COMMIT-PRIMITIVE-PHASE-N+
description: Preserve the structural argument that `commit` is a chain-finalization primitive distinct from collect, surfaced empirically by Phase N canonical probe as a substrate gap.
type: strategic-framing
planted_during: Phase N canonical probe (2026-05-21) — narrowed isolation probe (Step B) validated substrate through if-gate; bare `commit` step matched 70 tools, revealing chain-finalization is not yet a substrate primitive
trigger_when: Phase N+ framing opens OR a future contributor proposes shipping `commit` as a chain-terminal step before it lands as a typed primitive
---

# SEED-COMMIT-PRIMITIVE-PHASE-N+: commit as chain-finalization

## Idea

`commit` is a chain-finalization primitive, semantically distinct from
`collect`. collect converges iteration results into a reconciled substrate
object. commit applies a completed chain output back into the domain.

Phase N validates typed ports, foreach, collect, and per-iteration trace
rendering. It does not ship a standalone chain-terminal commit primitive.
Commit remains expressible as a directive on body tools, such as
`rename shots with prefix genesis commit`, but bare `commit` as its own
chain step is future substrate work.

## Empirical Evidence

Phase N narrowed isolation probe, rerun 2026-05-21:

```bash
fbridge chat --trace "get sequence segments on 30sec 21 -> select genesis_0010_source_L01 -> foreach(rename shots with prefix genesis dry_run) -> collect -> if(proposed_changes exists) -> commit"
```

The probe validated substrate execution through the if-gate: enumeration,
select, single-iteration foreach, collect, and gate decision all executed.
The terminal bare `commit` step then fell through to tool selection and
matched 70 tools:

```text
Step matched 70 tools; chain steps must select exactly one. Use a more
specific verb/noun (e.g. 'list versions' instead of just 'list').
```

That failure shape is not a bad synonym or a resolver wording defect. It
shows that standalone `commit` is not currently a substrate primitive.

## Why This Is Its Own Primitive

collect converges iterations. commit applies chain output.

Those are different responsibilities. A collect step can produce a valid
reconciled manifest without mutating Flame. A commit step must decide how
that manifest maps back to a domain mutation. Treating commit as "just
another collect behavior" would hide chain-finalization semantics inside
reconciliation and blur the topology boundary Phase N exists to clarify.

Commit-as-standalone therefore belongs in `forge_bridge/graph/` as a
first-class chain primitive when Phase N+ opens it.

## The Three Load-Bearing Phase N+ Questions

1. What does commit dispatch internally?
   Does it re-invoke the upstream body tool with `dry_run=false`, or does
   it call a domain-specific apply tool?

2. Does commit require typed-port input matching?
   Must collect's reconciled output topology be compatible with commit's
   expected input topology?

3. Does commit require a domain-specific "apply" capability per body tool?
   For example, does commit need to know that `rename_shots` has an
   apply-counterpart, or is apply implicit via `dry_run=false`?

## Sequencing Argument

This follows the same shape as the foreach deferral from 25.3 to Phase N:
probe pressure surfaced a substrate primitive, the current phase narrowed
its pass criterion honestly, and the next phase receives a named seed
with the structural questions preserved.

Phase N should not smuggle chain-finalization into collect, foreach, or
the resolver. Phase N+ should land commit only when the typed input
contract, dispatch target, and domain-apply semantics are explicit.

## Breadcrumbs

- `forge_bridge/graph/` — commit lands here in Phase N+ as a chain
  substrate primitive.
- `forge_bridge/console/_step.py` — `_maybe_execute_commit_step` should
  follow the established `_maybe_execute_*` dispatch pattern.
- `forge_bridge/graph/foreach.py` and `forge_bridge/graph/collect.py` —
  sibling chain-substrate primitives whose output may feed commit.
- `.planning/milestones/v1.6-PHASE-N-FRAMING.md` canonical probe section
  — **SUPERSEDED**; it now points here for the chain-finalization gap.
