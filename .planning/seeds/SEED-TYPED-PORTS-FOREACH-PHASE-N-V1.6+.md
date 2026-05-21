---
name: SEED-TYPED-PORTS-FOREACH-PHASE-N-V1.6+
description: Preserve the structural argument that foreach + collect open Phase N because foreach is the first graph primitive whose correctness depends on typed ports, step-body grammar, and per-iteration trace rendering.
type: strategic-framing
planted_during: Phase 25.3 close, 2026-05-20 — positional resolver stabilization + generic select proved interpretation boundaries; foreach pressure clarified as typed-topology pressure
trigger_when: Phase N framing opens OR a future contributor proposes shipping foreach/collect before typed ports OR v1.6-FRAMING.md foreach kind/schema entries are used as current implementation guidance
---

# SEED-TYPED-PORTS-FOREACH-PHASE-N-V1.6+: foreach forces typed ports

## Idea

foreach + collect should not land as a late 25.x primitive. It opens
Phase N because foreach is the first graph primitive whose correctness
depends on typed topology contracts.

25.1 proved topology-preserving filtering. 25.2 proved manifest-level
execution gating. 25.3 proved positional resolver stabilization and
generic identity selection. Those primitives stabilize interpretation
boundaries. foreach crosses a different threshold: topology expansion.

Without typed ports, foreach collapses into one of three unacceptable
shapes:

1. **magic** — infer item shape dynamically and hope
2. **rigid** — hard-code supported upstream collection types
3. **fragile** — fail unpredictably on unfamiliar upstream topology

None satisfy the substrate discipline established in 25.x.

## The Phase N Forcing Function

```bash
fbridge chat "get segments on 30sec 21
  -> foreach(rename with prefix genesis)
  -> collect
  -> commit"
```

Pass criterion: all 24 segments renamed independently inside foreach
iterations; collect produces a unified result; commit lands.
`--trace` shows the foreach step plus per-iteration scoped lines for
each body execution.

This probe cannot be cleanly written against a substrate without typed
ports, step-body grammar, AND per-iteration trace rendering. All three
must be present for the probe to be meaningful.

## The Sequencing Argument

```text
25.3
  positional resolver maturation (Item 18)
  generic select (Item 12)
  interpretation boundaries stabilize

Phase N opens:
  foreach + collect
  typed ports (forced by foreach)
  chat/exec split (made meaningful by typed ports)
  step-body grammar
  per-iteration trace render
  port compatibility
  macro bridge semantics
```

This is more stable than shipping foreach in 25.x then figuring out
typing later — because foreach is where typing stops being optional.

## Breadcrumbs

- `forge_bridge/graph/` — filter (25.1), if_gate (25.2), select (25.3)
  landed here. foreach and collect land here in Phase N.
- `forge_bridge/console/_engine.py` — chain engine; foreach requires
  a scoped execution loop, not just sequential step dispatch.
- `forge_bridge/console/_step.py` — `_maybe_execute_*` dispatch pattern;
  foreach follows the same shape but with iteration-scoped context.
  `_maybe_execute_foreach_step` will parse `foreach(<step>)` body syntax.
- `forge_bridge/cli/chat.py` — `_write_chain_trace` / `_maybe_render_*`;
  per-iteration trace rendering lands here in Phase N.
- `forge_bridge/llm/resolver.py` — 25.3 positional anchoring stabilizes
  the resolver before Phase N extends it to typed-port resolution.
- `.planning/milestones/v1.6-FRAMING.md` §4.2 item 7 — **SUPERSEDED.**
  foreach originally listed as in-v1.6-scope kind. 25.x empirical
  discovery (topology-expanding requires typed ports) reverses that
  position. Annotation in §4.2 points here. The original entry is
  preserved as archaeology; this seed carries the revised position.
- `.planning/milestones/v1.6-FRAMING.md` §5.1 / §5.2 — foreach in the
  kind enum and schema field definitions. Also superseded; annotation
  points here. Schema definition will be redone with typed-port
  substrate underneath in Phase N.
- `SEED-NODE-SCHEMATIC-V1.6+` — renders the typed-port substrate
  visually at v2.0. The two seeds compose, do not overlap: this seed
  establishes the runtime substrate; SEED-NODE-SCHEMATIC renders it.

## Why Plant Now

The foreach deferral in v1.6-FRAMING.md was stated as timing ("v1.7")
without the structural argument. The structural argument emerged clearly
during the 25.3 writer's room and is now fermented enough to carry
forward without re-derivation.

The risk without this seed: a future contributor reads v1.6-FRAMING.md
§4.2 and attempts to ship foreach as a v1.6 kind — exactly the failure
mode the seed is meant to prevent. The annotation in v1.6-FRAMING.md
points here; this seed provides the structural argument for why that
attempt would produce magic, rigid, or fragile substrate.

The three typed-port questions foreach forces — item type, loop-scoped
context, collect merge validation — will not get simpler between now and
Phase N. Preserving them here means Phase N framing opens by answering
them, not re-discovering them.
