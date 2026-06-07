# Q4 — Seam-obligation allocation & freeze-timing (converged)

**Date:** 2026-06-06
**Status:** CONVERGED (not reopened). Rationale for #4a/#4b amended 2026-06-06 after
corrected storage analysis (`VERSION-LINKAGE-CORRECTED.md`) — **decisions unchanged; the
evidence changed, and for #4a got substantially stronger.**
**Input:** `SEAM-OBLIGATIONS-Q3.md`. **Frontier:** harden the forge-core↔bridge seam —
*decide together, fix distinctly.*

---

## Central fork — one clock vs N clocks → ONE contract package now

Lean: **one contract package, additive semver, module boundaries for rate-separation;**
the N-clock split is **explicitly unbound**, not the day-one design.

- Technical kill (verified): `ContractModel` is `extra="allow", frozen=True`. A new role
  member / field is a **non-breaking minor** — a transport-only peer pinned at a floor is
  already satisfied and re-pins only when it *wants* new vocab. The "a role bump
  force-re-pins every peer" fear is an additive-semver category error.
- Meta-move (load-bearing, two lenses converging): the clock-count is **second-order** — "a
  clock is a versioning container, not a ripeness decision" / "the clock is not the decision;
  the surface is." Premature until ≥2 vocabularies are frozen and their cadences actually
  diverge.
- So: start unified (atomic-consistency + scalar-pin win at one frozen vocab), keep module
  seams so a later split is additive, don't build N-clock machinery you can't yet justify.

## Converged ripeness-sequenced allocation

| # | Obligation | Owner | Freeze-timing | Trigger to advance |
|---|---|---|---|---|
| **#5** | Role vocab (media + track) | contracts defines (**open registry**: classes + known members + extension rule) · consumer tags · bridge persists | **FREEZE NOW** | re-opens only on a new `role_class` (a third stratum), never on new members |
| **#4a** | Relationship edges (`version_of`/`member_of`/`references`) | contracts defines · consumer emits · bridge validates | **FREEZE NOW** (rides #5's cycle) | — (see strengthened evidence below) |
| **#4b** | Owner-type enum (`parent_type` membership) | contracts defines · consumer emits · bridge validates | **DEFER** (staged) | non-default `parent_type` written (asset/sequence/…), THEN ≥3 structurally-distinct DCC owner cases (USD assembly · HIP sim cache · material library · multi-ref hero asset) resolve additively; any case forcing a structural change to `version_of` = stay open |
| **#3** | Invocation-binding | **bridge-sovereign** (`handler: Any` stays); contracts = nothing | **DEFER / zero-vocab** | a 2nd peer needs to reason about another peer's binding (cross-peer introspection/routing) → add a thin optional declarative discriminator, additively |
| **#6** | Wire/transport envelope | bridge (bilingual shim, held); contracts = eventual home | **DEFER (last)** | N≥3 transport peers, OR shim tolerance fails to absorb a new key, OR correlation needed over non-WS transport |

**Net cycle-1 surface:** two vocabularies (role registry + relationship edges) on one
additive contract bump. Everything dispatch-shaped, transport-shaped, or
not-yet-pressure-testable stays out, with falsifiable triggers.

### Per-cell rationale (with the 2026-06-06 evidence correction)

- **#5 — freeze as OPEN REGISTRY, not closed enum.** Live `role: plate` already exists on a
  production media row and is in no registry; a closed enum would make it a day-one
  violation. Freeze the two role-classes + known members + an open-extension rule (validate
  the *class*, not membership). Ripest obligation; anchor of the cycle.
- **#4a — freeze now. EVIDENCE STRENGTHENED (correction).** Originally the softest cell (a
  3-1 override weighting active-consumer coordination — forge_core is building the producer
  write-path now). The corrected storage analysis makes it **well-grounded, not soft**:
  `version_of` (20), `member_of` (2), `produces` (45), `derived_from` (2) are **live, in
  active production use** — the nouns are proven, not aspirational. The names are settled by
  the durable-ownership ruling (`render_of` rejected; `member_of`+role chosen).
- **#4b — defer. RATIONALE CORRECTED.** Original rationale "zero owner edges → freezing
  against fiction" was a bad-join false negative (there are 20 `version_of` edges).
  **Corrected:** all 20 owners are default `shot`-type → **no owner-type diversity** to
  pressure-test the enum. Stage-1 trigger ("real `version_of` edges exist") is **met**; the
  unmet condition is **non-default `parent_type`** + the ≥3-DCC-case test. Conclusion (defer)
  unchanged.
- **#3 — bridge-sovereign, zero added contract vocab.** Falsification that held: #3 has
  produced **zero cross-repo failures** — unlike #5 (render skew, on disk) and #6 (state_ws
  hang). Contract what's bleeding; #3 isn't. Typing the handshake from N=1 binding risks
  leaking bridge's Flame-shaped dispatch into siblings (the `parent_type` worldview-leak,
  repeated).
- **#6 — defer, hold the bilingual shim; eventual home contracts, freeze last.** The shim's
  existence is the not-yet-ripe signal; freezing now encodes the accident of which two
  dialects collided. The tolerant reader is a Postel's-law boundary (absorbs skew), not a
  skew-factory — it already delivers the benefit (correlation works) without the cost.
  Highest blast radius + weakest signal = freeze last.

## Intentionally unbound (live, with re-open triggers)
- **Clock topology (one vs N)** — pending ≥2 frozen vocabularies whose release cadences
  demonstrably diverge. Start unified; module seams keep the split additive.
- **#4b owner-type enum** — pending non-default `parent_type` + the ≥3-DCC trigger.
- **#3 contract participation** — pending a 2nd peer needing cross-peer binding introspection.
- **#6 transport envelope** — pending N≥3 (or shim-tolerance failure / non-WS need).

## Rejected (closed, with reason)
- Promoting `backend_identity_triple` / typing dispatch into contracts — zero cross-repo
  failures; freezes bridge's contextual dispatch substrate into a foundation (projection-as-
  foundation inversion).
- Freezing the owner-type enum now — no owner-type diversity yet (all owners default `shot`);
  nothing to validate diversity against.
- Contracting the transport envelope now — freezing mid-negotiation at N=2 with a working
  reversible shim; highest blast radius, weakest signal.
- Freezing #5 as a closed enum — live `role: plate` would be an instant violation; open
  registry instead.

## Read-layer follow-up unblocked by the correction (not part of Q4 freeze)
`shot_id`-reading version tools (`get_shot_versions`, lineage, published-plates) should
migrate onto the canonical `version_of`/`parent_id` — the link is present in edges; those
tools read an unpopulated denormalization. See `VERSION-LINKAGE-CORRECTED.md`.
