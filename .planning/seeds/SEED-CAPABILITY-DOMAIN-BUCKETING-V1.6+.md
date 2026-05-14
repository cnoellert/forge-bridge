---
seed: SEED-CAPABILITY-DOMAIN-BUCKETING
status: pending
created: 2026-05-14
trigger: "When the v1.6.x graph-native runtime work or v1.7 taxonomy pass produces a stable substrate-identity layer separate from MCP transport naming."
target_milestone: v1.6.x or v1.7
---

# Capability-domain bucketing requires taxonomy substrate that doesn't yet exist

## Context

Phase 24.1 Commit 5 attempted to introduce coarse, stable operational-
context buckets (``flame`` and ``generic``) BETWEEN the reachability
filter and the PR14/PR21 semantic-intent narrowing chain. The bucket
layer would have stabilized the outer envelope of the
``{system, tools}`` prefix Ollama sees, collapsing N per-message cache
slots to two bucket-defined slots — delivering the cache-locality wins
documented in ``.planning/COLD-START-INVESTIGATION.md`` recommendation
#1 (~3.5s/call after the first when prefix stays cache-resident).

Implementation reached working code: 29 green tests against the bucket
helper functions themselves (selection determinism, intersection
discipline, byte-identical bucket-layer prefix). The architectural
revert happened during the broader test suite: 80 of the 81 net-new
failures were **bucket-boundary failures**, not narrowing failures.
Path B (layered bucket-then-PR14, preserving PR14/PR21/PR20/PR22)
produced 85 total failures vs the initial bad rewire's 86 — improvement
of exactly 1.

The 80 failures were not an implementation problem. They were an
architectural one.

## The architectural finding

**Tool naming today conflates multiple orthogonal axes:**

- substrate / runtime dependency (Flame backend vs in-process)
- product namespace (``flame_*`` vs ``forge_*`` vs ``synth_*``)
- operational domain (introspection, mutation, staged ops, pipeline, …)
- deployment locality (which process actually executes the call)

Because all four axes are mixed into a single name, no keyword-based
bucket rule can cleanly partition the tool universe into stable
capability domains. The failing tests demonstrated this concretely.
Messages like ``"forge fetch versions"`` / ``"list shots in project
X"`` / ``"show project info"`` carry Flame-backed ``forge_*`` intent
but contain **zero flame-bucket keywords** — because the substrate-
level operational keywords (``clip``, ``reel``, ``sequence``,
``timeline``, ``batch``, ``shot``, ``segment``, ``render``,
``publish``, ``conform``, ``flame``, ``media``) don't match the
user-facing pipeline vocabulary (``version``, ``project``, ``list``,
``fetch``, ``show``).

The broader pipeline-vocabulary terms (``project``, ``version``,
``library``, ``ocio``, ``grade``) were deliberately excluded from the
flame keyword set to prevent semantic-classification drift —
correct architectural choice in isolation, but means
those messages route to the generic bucket, which intersects against
the seven in-process ``forge_*`` tools only.

Result: Flame-backed ``forge_*`` tools **fall in a gap between
buckets**:

- not matched by flame-bucket substrate keywords
- not in the in-process generic set
- PR14 would have matched them on the unbucketed reachable list
- the bucket layer drops them BEFORE PR14 can

**Diagnosis:** the bucket boundary depended on an axis (substrate
identity) that the current tool naming system does not cleanly encode.
Capability-domain bucketing requires a taxonomy substrate the project
does not yet have.

## Why this isn't a v1.6.0 fix

The natural taxonomy substrate is downstream of v1.6's graph-native
runtime work. ``v1.6-FRAMING.md`` §3 (Two-Graph Model) + §4 (Closed
Node-Kind Enumeration) + §5 (Node Schema) collectively introduce
substrate-level identity that's distinct from MCP transport naming.
Phase 24.1 Commit 2.5 (commit ``b66ceef``) already encoded the
substrate-vs-surface distinction at ``node_kind`` for graph emission —
that's the same architectural axis that capability-domain bucketing
needs at a finer granularity.

Once the taxonomy substrate exists, capability-domain bucketing has a
real anchor:

- ``node_kind`` (substrate-level, closed enumeration) drives bucket
  selection
- a declared per-tool ``runtime_dependency`` or ``execution_substrate``
  cleanly partitions Flame-backed vs in-process regardless of name
- an ``operational_domain`` field (introspection / mutation / pipeline
  / diagnostic) could form a richer bucket taxonomy if needed

Attempting bucketing before the substrate exists requires either:

(a) extending bucket keywords until they collide with semantic
classification (explicitly excluded by Commit 5 operator direction),
OR

(b) inventing a side-channel substrate-identity layer just for
bucketing (structural duplication that v1.6's taxonomy work will
obsolete).

Both are bad investments at v1.6.0.

## Operational impact of the deferral

Phase 24.1 still ships meaningful KV-cache improvements without
bucketing:

- **Commit 4 (``fbf4b56``)** — deterministic alphabetical tool ordering
  at ``OllamaToolAdapter._compile_tools``. Stops upstream filter-chain
  ordering variance from busting the cache. ~3.5s/call savings after
  the first call when the prefix stays cache-resident.
- **Commit 6 (next)** — reachability probe TTL bump from 5s to ~60s on
  the chat hot path. Stops sub-5s reachability re-probes from flipping
  the compiled prefix mid-conversation.

The bucketing residual is the remaining N-cache-slots-per-message
problem (PR14 narrowing produces a different subset per distinct
message). This is real but not blocking — the canonical operational
regression query (``"What are the clips on Reel 1"`` per
``tests/fixtures/canonical_queries.py``) still benefits from Commit 4
+ Commit 6 stabilization on repeated invocations, and PR14/PR21/PR20/
PR22 arbitration semantics remain intact for the test surface that
already covers them.

## Trigger conditions

Surface this seed when ANY of the following becomes true:

- v1.6.x graph-native runtime work introduces ``node_kind`` (or
  equivalent) as a first-class field on each tool/operation, with a
  closed enumeration
- v1.6.x or v1.7 introduces a declared per-tool
  ``runtime_dependency`` or ``execution_substrate`` field separate
  from name
- COLD-START remeasurement after Commit 6 reveals that bucketing's
  cache-locality win would be operationally significant enough to
  justify revisiting the architecture
- The non-author UAT (Phase 24 forcing function) surfaces operator
  friction patterns that bucketing would directly address

## What to do when triggered

1. Re-read ``.planning/COLD-START-INVESTIGATION.md`` (canonical
   measurement substrate; still valid).
2. Re-read this seed's "architectural finding" section — the
   keyword-vs-substrate diagnosis still applies. The fix is to use the
   new typed substrate as the bucket selector, NOT to expand the
   keyword set.
3. Re-read the Phase 24.1 Commit 5 revert archaeology in the operator's
   prior `Path B` direction — the 80 failing tests are the regression
   surface to verify against (they should pass under the new
   substrate-typed bucketing).
4. Use the new substrate-identity layer (``node_kind`` /
   ``runtime_dependency`` / whatever the taxonomy work introduces) as
   the bucket selector. The keyword-based selector was the wrong
   substrate; the typed substrate is the right one.
5. Update ``v1.6-FRAMING.md`` if the bucketing design ends up
   load-bearing for §8 (Surface-by-Surface Implications) — the chat
   surface is the primary consumer.
6. Mark this seed ``status: resolved`` with a one-line summary of the
   resolution path taken.

## Why this isn't urgent

Phase 24.1 Commits 4 + 6 deliver the highest-yield cache-locality wins
(per-call prompt-eval savings on stable-prefix calls + cache-survival
across reachability flips). The remaining bucketing residual is the
per-message variance within a reachability state, which is
operationally less painful than the cache-busting sources Commits 4 +
6 close.

Bucketing is also strictly additive to the existing PR14/PR21/PR20/
PR22 arbitration contracts — those continue to function correctly
without it. Deferring bucketing does not break anything; it just
leaves a known cache-locality residual in place until the substrate
exists for a clean fix.

The architectural finding itself is the valuable artifact: future
bucketing work will not need to re-derive that keyword-based
substrate-identity inference is structurally insufficient. The
revert preserved that durable insight.

## Cross-references

- ``.planning/COLD-START-INVESTIGATION.md`` — original cache-locality
  measurement work; load-bearing input to the Commit 5 design that
  was reverted.
- ``.planning/milestones/v1.6-PHASE-24-CONVERGENCE.md`` §5.4 — the
  convergence position on minimal graph record shape (substrate-level
  ``node_kind``) is the upstream taxonomy work this seed depends on.
- ``.planning/milestones/v1.6-FRAMING.md`` §3-§4 — the two-graph model
  and closed node-kind enumeration that will provide the substrate
  for capability-domain bucketing.
- Commit ``fbf4b56`` — Phase 24.1 Commit 4 (deterministic tool
  ordering; the prefix-stability win that did ship).
- Commit ``b66ceef`` — Phase 24.1 Commit 2.5 (substrate vs surface
  identity at ``node_kind``; the architectural distinction that
  capability-domain bucketing also depends on at a finer granularity).
