---
milestone: v1.7
thread: C
thread_name: Asset operability — make a quiet substrate entity speak
status: phase-framing
drafted: 2026-05-27
converged: 2026-05-27 (room — operator R-1..R-6 + Creative + DT R-7..R-10)
type: thread-framing
derives_from: .planning/milestones/v1.7-ARTIST-READINESS-FRAMING.md
grounded_by: .planning/ASSET-SUBSTRATE-AUDIT.md (this-cycle audit, evidence-grounded layer-by-layer); .planning/seeds/SEED-ASSET-FIRST-CLASS-ENTITY-V1.7+.md (operator brief, verbatim)
preceded_by: Thread B (exec discoverability) — CLOSED, b73facd
parallel_with: Thread A (chat intent-compile stage) — phase-framing, f559218
artifact_role: load-bearing — the C.1/C.2/C.3 phase plans derive from this
---

# Thread C — Asset operability

> **What this artifact is.** The thread-level framing for Thread C,
> the third thread in the v1.7 Artist Readiness milestone. It records
> ten converged room rulings (R-1..R-10) from the 2026-05-27 cycle —
> R-1..R-6 from operator ratification of the substrate audit;
> R-7..R-10 from room convergence (Creative + DT). The C.1/C.2/C.3
> phase plans derive from it.
>
> **Frontmatter axes.** `status: phase-framing` (lifecycle position)
> matches Thread A. `type: thread-framing` (artifact category) is
> the per-thread framing artifact that co-locates with the opening
> phase. Converged in a single cycle: drafted as writing-room
> proposal at this commit's predecessor; promoted to phase-framing
> at this commit after Creative + DT signed off and the Q1 prose
> and Q4 contract were tightened per DT's Stage 1a finding.
>
> **Directory slug.** `C.1-thread-c-asset-operability` mirrors
> Thread A's `A.1-thread-a-...` precedent: per-thread framing
> co-locates with the opening phase; the slug is descriptive of the
> thread thesis, not the C.1-specific deliverable.
>
> **Grounding artifacts (read, do not duplicate).** The audit at
> `.planning/ASSET-SUBSTRATE-AUDIT.md` carries the load-bearing
> layer-by-layer evidence (file paths, line numbers, gap map). This
> framing references it rather than reproducing it. The seed at
> `.planning/seeds/SEED-ASSET-FIRST-CLASS-ENTITY-V1.7+.md` carries
> the operator brief verbatim.

## Thesis

**Asset is not missing from Bridge. Asset is quiet. Thread C makes it
speak.** *(Operator coinage, 2026-05-27.)*

The audit grounds the thesis: `Asset` is in the canonical vocabulary
(`forge_bridge/core/entities.py:244`), round-trips through Postgres +
JSONB attributes, participates in the generic relationship + location
+ event substrate, and is constructable over the WebSocket protocol.
Six of the brief's seven layers (vocabulary, DB schema, repository,
WS protocol, server router, clients) already pass the substrate's own
generic-entity contracts. The seventh layer — operator surfaces (MCP
tools, CLI, tests, docs) — is empty. That emptiness is the silence.

Thread C is operationalization, not greenfield. It is sibling to
Thread B in shape (operator-facing surfaces over generic substrate)
and narrower in scope (one entity class, not the substrate's full
menu). Thread A and Thread C are orthogonal — they share no
substrate-modification surface and can proceed in parallel.

## Position in the three-thread arc

- **Thread B** — operator visibility of the substrate's menu
  (discover sub-app, primitive enumeration, tool-title surfaces).
  **CLOSED.**
- **Thread A** — operator authority at the chat compile boundary
  (NL → graph-intent → preview → ratification → apply). Phase
  framing, A.1 plan pending.
- **Thread C** — operator drive of one specific entity class. Same
  surface-discipline as Thread B, narrowed to Asset. Operator can
  create, list, query, locate, relate, and version assets through
  the same dispatch substrate that already serves every other
  entity. **This proposal.**

The three threads converge on one ontology — Thread B's discover
introspection surfaces are how Thread C's operator-facing tools
become legible to chat; Thread A's compile stage is how chat could
later author assets through the same preview→apply seam without
Thread C reimplementing the seam at its layer.

## Ratified rulings (2026-05-27)

Ten converged rulings govern Thread C's shape. R-1..R-6 landed as
operator ratification of the substrate audit (commit `9f0cdd4`).
R-7..R-10 landed from room convergence (Creative + DT) on the four
scoping questions that had been left open in the writing-room
proposal.

**R-1. Headline.** *"Asset is not missing from Bridge. Asset is
quiet. Thread C makes it speak."* — load-bearing thesis; carries
through to phase plans and close cursors.

**R-2. Scope discipline — no schema philosophy war.** `asset_type`
stays as an open string field on the Asset entity, queryable through
the existing JSONB + GIN index path. **Promotion to a structured
column with B-tree index, or registry-backed treatment analogous to
Role, is explicitly out of Thread C scope.** It is a follow-on
motion that opens only if repeated operator/API usage produces
evidence that JSONB query guarantees are insufficient. Per
`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`: this is
deferral, not rejection — preserves maneuverability when evidence
arrives.

**R-3. C.1 — Bridge MCP asset tools.** Create, list, get/show,
update (status + attributes), attach location, relate asset.
Behavioral tests cover create/read/update/list and relationship
traversal. Docs at `docs/ASSET.md` + VOCABULARY.md cross-link. No
consumer impact.

**R-4. C.2 — Bridge CLI asset surface.** Same operations as C.1,
operator-friendly Typer subgroup under `fbridge asset`. **`--json`
mode preserved** per the P-01 stdout-purity constraint already
binding on `fbridge`. Dogfood-tested against the C.1 surface
(matches the Thread B B-2 dogfooding pattern).

**R-5. C.3 — Projekt Forge consumer proof — investigation-first.**
The load-bearing question is *whether projekt-forge needs DBAsset*,
or whether it should consume Bridge's generic entity-asset directly
through commands + project conventions. The first-draft default of
"obvious parallel-table" is **rejected** — substrate/consumer
pattern (see `[[project_forge_bridge_substrate_not_producer]]`)
says the room has to prove duplication is warranted before any
schema lands downstream. C.3 ships either:
- a projekt-forge command + project-convention surface over
  Bridge's substrate (no DBAsset, no migration), OR
- DBAsset + alembic migration + repo + CLI, with evidence about
  why duplication is warranted.

**R-6. Sequencing.** C.1 → C.2 → C.3 in that order. C.3 opens only
after Bridge surfaces exist (substrate-before-consumer discipline).

**R-7. Status semantics — inherit canonical `Status` enum; add
aliases as cosmetic surface.** `Status` lives in
`forge_bridge/core/vocabulary.py:21` as the canonical lifecycle enum
shared by every entity (Shot, Asset, Version, Media). Its nine
values are `PENDING, IN_PROGRESS, REVIEW, APPROVED, REJECTED,
DELIVERED, ARCHIVED, VERIFIED, FAILED`. The brief's verbs map onto
existing values: `approve` → `APPROVED` (exact), `invalidate` →
`ARCHIVED` (canonical; the `omit → ARCHIVED` alias precedent at
`vocabulary.py:50` already exists). C.1 may add operator-friendly
aliases to `from_string()` if helpful (`proposed → PENDING`,
`published → DELIVERED`, `invalidated → ARCHIVED`) — one-line
cosmetic surface that costs nothing and keeps the wire shape
canonical. No new states; no Asset-specific state machine. Per
`[[feedback-distinct-success-criteria-per-adjacent-layer]]`:
state-transition validation, if ever needed, is a substrate-wide
concern not an Asset-specific motion — out of Thread C scope.

> **Burden of proof on future state expansion.** New states require
> proof of irreducible semantic difference, not workflow
> convenience. The distinction *"can an operator reason about this
> asset"* vs *"has the organization socially approved this asset"*
> is not automatically the same ontology — Thread C declines to
> conflate them at this layer.

**R-8. MCP tool granularity — dedicated `forge_*_asset` tools.**
Grounded: `forge_bridge/mcp/tools.py` has zero generic
`forge_create_entity` / `forge_list_entities` surface today. Every
entity surfaces through dedicated tools (`forge_list_shots`,
`forge_get_shot`, `forge_create_shot`, `forge_update_shot_status`,
etc.). Inventing a generic surface alongside Asset would be scope
creep dressed as elegance — gains the LLM one generic verb with one
consumer, loses the named-affordance signal the description layer
carries. Per
`[[feedback-rhetorical-position-as-architectural-control-surface]]`:
the tool name itself is an affordance-selection signal that
dominates generic verbs at selection time across the 58+ tool
catalogue. **Six dedicated Asset tools** in C.1: `create`, `list`,
`get`, `update`, `attach_location`, `relate`.

**R-9. Asset → Version surface in C.1 — entity-level only; defer
`forge_publish_asset_version`.** Strongest of the room dispositions
because there is no precedent to follow: there is no
`forge_publish_version` tool today for **any** entity. The Shot
publish path goes through `register_publish` + the staged-ops +
manifest-synthesis flow — a much heavier surface than C.1 should
bite off. Inventing `forge_publish_asset_version` in C.1 would mean
designing a Version-publish surface that doesn't exist anywhere —
a Version-layer architectural motion masquerading as Asset
operability. Substrate already works: `parent_type="asset"`
round-trips through Version today (`entities.py:307`); consumer
code can call existing generic Version surfaces. If a consumer
ever needs a publish flow specifically for asset versions, that's
its own future motion against the Version subsystem — the right
architectural seam for it. **C.1 ships entity-level only.**

**R-10. C.3 forcing-criterion contract — three buckets, evidence
required.** Replaces what was a candidate-list in the writing-room
proposal. The contract:

> **DBAsset is warranted iff projekt-forge has a NAMED, GROUNDED
> workflow with at least one of these properties:**
>
> 1. **Latency-bound.** A query pattern with a measured latency
>    budget that Bridge's WS+JSONB+GIN substrate empirically cannot
>    meet. *Requires:* named query shape + named latency target +
>    measurement against the actual substrate.
> 2. **Atomicity-bound.** A write that must commit-or-rollback
>    atomically across projekt-forge's domain AND the Asset entity,
>    with no acceptable saga / eventual-consistency / event-driven
>    shape. *Requires:* named operation + named consistency
>    requirement + explanation of why eventual-consistency fails.
> 3. **Availability-bound.** A workflow that must succeed when
>    Bridge is unreachable. *Requires:* named workflow + named
>    availability target + evidence the workflow is mission-critical
>    at the consumer surface.
>
> **Does NOT count as evidence:**
> - "We might someday need offline asset operations."
> - "It would be convenient to have local query access."
> - "Other consumers in the future might need this."
> - "Parallel-table convention already exists for Shot/Version/Media."
>
> **Does count:**
> - A projekt-forge command that exists today and demonstrably
>   can't be served by consume-directly.
> - A workflow named in projekt-forge's roadmap / open issues /
>   current pain points that fails one of the three buckets when
>   modeled against consume-directly.
>
> **C.3 procedure.** Enumerate projekt-forge workflows-that-touch-
> assets. Stress-test each against the three buckets. If zero
> workflows fire any bucket → consume-directly is the C.3 outcome.
> If one or more fire → DBAsset, scoped exactly to the workflows
> that force it (not "DBAsset because parallel-table").

Per `[[feedback-explicitly-unbound-vs-implicitly-rejected]]`: the
three buckets define what's bound-by-future-evidence; everything
else is deferred not rejected; if a fourth bucket emerges from C.3
investigation the room ratifies it as an addition. Convenience and
parallel-structure are not just unscored — they are explicitly
rejected as warrant. Per `[[project-forge-bridge-substrate-not-producer]]`:
substrate is not duplicated absent demonstrable substrate
insufficiency.

## Phase decomposition

**C.1 — Bridge MCP asset tools.** Per R-3 + R-7 + R-8 + R-9. Six
dedicated tools (`create`, `list`, `get`, `update`,
`attach_location`, `relate`); inherit canonical `Status` with
optional alias additions; entity-level only — no
`forge_publish_asset_version`. Behavioral tests grounded against
the substrate's existing entity-test patterns. Docs at
`docs/ASSET.md` + VOCABULARY.md cross-link.

**C.2 — Bridge CLI asset surface.** Per R-4. Typer subgroup +
`--json` mode preserved + dogfood pass per Thread B B-2 pattern.

**C.3 — Projekt Forge consumer proof.** Per R-5 + R-10. Investigation
runs the R-10 contract: enumerate workflows-that-touch-assets,
stress-test against the three buckets, deliver against the ruling.

> **Brief-vs-R-5 tension — named explicitly.** The operator brief at
> `.planning/seeds/SEED-ASSET-FIRST-CLASS-ENTITY-V1.7+.md` says
> *"Add or update Projekt-side asset registry support"* — phrasing
> that presumes DBAsset by default. **R-5 supersedes that phrasing.**
> The seed is the operator-intent capture, preserved verbatim as
> archaeology; R-5 + R-10 are the room's ratified position after
> grounding the audit and applying substrate/consumer discipline.
> A future reader of the seed should not assume DBAsset was the
> converged position — the converged position is the R-10 contract.

A.1/A.2/A.3 (Thread A) proceed in parallel; no substrate overlap.

## Out of scope (explicitly deferred)

Per R-2 and the audit's "Explicitly deferred" subsection:

- **`asset_type` structural promotion.** Stays JSONB+GIN for v1;
  follow-on motion if query evidence warrants.
- **`asset_type` registry-backed classifier.** Same disposition.
- **Cross-repo coordination tactics.** projekt-forge maintainer
  ruling on pinning policy, editable-install vs tagged-release
  adoption — lives downstream of C.3.
- **Asset-as-DAM features.** The brief explicitly bans (Non-Goals
  section in the seed): no SPECID logic, no USD/OTIO/Comfy/QC/
  render-queue orchestration, no full-DAM features. C.3's surface
  stays generic.
- **Flame-specific Asset behavior.** Per brief: "Keep Flame-specific
  behavior out of the generic asset model." Asset stays endpoint-
  parity-shaped.

## Architectural law (inherited, binding)

Substrate self-views are first-class operator surfaces — derived,
not reconstructed. Thread C inherits the v1.7 milestone law:

- Asset's operator surface (C.1 + C.2) is derived from the existing
  substrate, not a parallel reimplementation. Same dispatch path as
  every other entity. No special-case shot-of-asset machinery; if
  Asset needs something the substrate can't already do, the gap is
  in the substrate, not in Asset.
- C.3's investigation honors the same law from the consumer side.
  projekt-forge consuming Bridge's substrate is the substrate-self-
  view extending to the consumer surface; duplicating into DBAsset
  is reconstruction, which requires the room to prove warrant.

**Through-line to Thread A** *(Creative, 2026-05-27):* "Derive
first, duplicate only under proven pressure" is the same
constitutional doctrine Thread A converged on with graph-intent and
ratification surfaces. Thread A refuses to reconstruct authority
state into a parallel artifact when the substrate already carries
it; Thread C refuses to reconstruct entity persistence into a
parallel table when the substrate already carries it. The two
threads instantiate one architectural law on different surfaces —
authority for A, persistence for C — and the milestone's coherence
is that both threads enforce the same discipline.

## Status

**Phase framing.** Converged 2026-05-27 — R-1..R-6 from operator
ratification of the substrate audit (commit `9f0cdd4`); R-7..R-10
from room convergence (Creative + DT). DT's two required edits
applied (Q1 prose correction on the canonical Status enum;
Q4 candidate-list upgraded to forcing-criterion contract). The
C.1 phase plan is the next motion — drafted in code-handoff format
and Stage 1b reviewed before implementation hands off.
