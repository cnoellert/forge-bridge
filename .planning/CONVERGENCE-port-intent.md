# Convergence: per-port intent — surface, consumer, and build-now-vs-defer

**Date:** 2026-06-28
**Subject:** Where/how should forge-bridge surface `CapabilityDeclaration.input_port_intent`/`output_port_intent` (forge-contracts v0.7 / ADR-009), who consumes it, and is it worth building now?
**Method:** 4 independent views (Creative / DT-technical / Pipeline-consumer / Contracts-peer) → redline → converged lean.
**Outcome:** **DEFER everything (including the carry).** Re-open trigger recorded below.

---

## Context at the time of this convergence

- The artist-description seam shipped this session (PRs #125, #127): forge-bridge consumes peer-authored `CapabilityDeclaration.summary` + `label` onto `ToolRegistration`, resolves via `artist_description()`/`artist_label()` (prefer peer value, else derived fallback), and displays both in the Console tools view (`/ui/tools` + `/api/v1/tools`, resolved in-daemon) and in `fbridge discover tools` (read-API consumer).
- forge-contracts **v0.7 / ADR-009** added `input_port_intent: dict[str,str]` + `output_port_intent: dict[str,str]` — a one-line human meaning per port, **keyed by schema-property name**, split into two maps to mirror `input_schema`/`output_schema` and avoid passthrough name collisions (`plate` in == `plate` out).
- forge-bridge **deferred** consuming port-intent: no per-port display surface exists, so consuming it would be an inert carry (the consume-with-nowhere-to-display trap previously hit and corrected with `summary`).

---

## Converged positions

### 1. WHERE does port-intent display?
**Lean: never artist-facing; eventual home is the developer/integrator tool-detail surface (`fbridge discover tool <name>` first, Console tools detail second), and only once that surface renders an operator's schema property names.**

- Unanimous on the principle (Creative carried it): showing an artist "what this port consumes/produces" re-introduces the node-graph mental model that the prior DAG-editor rejection already killed — the same category error one size down.
- DT carried the placement with decisive grounding: **no surface renders an operator's ports today.** Console tools detail = provenance only; discover detail = name/label/origin; `ToolRecord` has **no schema field at all**. Intent cannot render until ports (= schema properties) render first.
- The verb/Actions/chat flow is the **wrong** home: verbs are Bridge-internal operators with no peer `CapabilityDeclaration`, so wiring intent there = Bridge authoring port meaning (forbidden).

### 2. WHO consumes it, and the fallback shape — **[STRUCTURAL SEAM]**
**Lean: integrator + (aspirational) NL-planner as a disambiguation hint + bridge-dev debugging — never the artist; PEER-ONLY with NO derived fallback; display prose, not machine-routing.**

- **The seam (fossilizes fast, expensive to reverse):** port-intent mechanically resembles summary/label (peer-authored optional prose), tempting a clone of the `artist_description` humanize fallback. **Rejected.** summary/label describe an operator's *purpose* — a humanized id is an honest degraded guess. port-intent describes *what crosses a wire* — a peer's **contract**. A Bridge-fabricated port meaning synthesizes a fact that does not exist (the v1.9 cut line) and violates one-canonical-author. Carried by Contracts + DT past the symmetry objection.
- **Resulting rule:** absent intent → render the bare port/property name, no gloss. The de-blank guard that is correct for `label` is **wrong** here — absence is information, not a blank to paper over.
- **Not machine-routing** (unanimous): routing stays on `PortTopology`/family/schemas. Branching a planner on intent strings is the literal-string-coupling anti-pattern Bridge already forbids ("graph represents work not decisions"). At most, a planner reads it as a *disambiguation hint* among already-topology-compatible candidates.
- **HOW (when built):** two flat `dict[str,str]` carried verbatim onto `ToolRegistration` (mirror the summary/label carry). **Do not** model a `Port` struct; **do not** couple to the graph's `NodeSpec.input_ports` names — those are compile-time-derived (`"input"`/`"deltas"`/`"item"`), a *different naming space* from the peer's schema-property keys.

### 3. BUILD-NOW vs DEFER
**Lean: DEFER everything, including the carry.**

- This was the live disagreement. **Pipeline argued carry-now** (thread the maps onto `ToolRegistration`, "nearly free," keeps Bridge non-blocking). **DT's redline broke it:** substrate-before-consumer landing requires a *testable, meaningful* primitive — summary/label landed because a reader was ready. Port-intent has no reader, no display field, no behavioral test → dead-field accretion = the inert-carry trap.
- It isn't even "nearly free": `ToolRegistration` **drops `output_schema` today** (carries `input_schema` as `schema` only), so `output_port_intent` keys map to data Bridge throws away — incoherent to carry without more plumbing.
- Bridge is **already non-blocking**: an unconsumed `CapabilityDeclaration` field blocks nothing. Carry-now buys nothing now.

---

## Intentionally unbound (with re-open trigger)

- **Port-intent consumption** — unbound pending BOTH:
  1. a tool-detail surface renders an operator's **input/output schema property names** (the real prerequisite — and that slice must also carry `output_schema` onto `ToolRegistration`, which is dropped today), AND
  2. a peer ships a `CapabilityDeclaration` with **non-empty** port-intent.
  When both hold, it is one small slice: carry both maps + `output_schema` onto `ToolRegistration`, resolve daemon-side, display **peer-only** on tool-detail.

## Rejected (with reason)

- **Carry-now onto `ToolRegistration`** — no testable consumer, incomplete without `output_schema`, Bridge already non-blocking. Inert-carry trap, not substrate landing.
- **Artist-facing port-intent (verb shell / Actions / chat)** — wrong audience and wrong author (verbs are Bridge-internal; the DAG-editor category error one size down).
- **Port-intent as machine-routing input** — free-text wiring decisions violate "graph represents work not decisions"; routing stays on topology.
- **Derived fallback for absent port-intent** — fabricates a peer's wiring contract; the one fallback "one canonical author" + the v1.9 synthesis cut line forbid.

---

## Load-bearing principle this convergence set

**Bridge never fabricates a peer's wiring contract — port-intent is peer-only, no fallback.** This is broader than port-intent: it fixes that Bridge does not synthesize a peer's contract semantics, only explains facts the peer authored.

## Useful spinoff (separable, more valuable than port-intent itself)

Render an operator's **input/output schema (what it consumes/produces) on the dev tool-detail surface** — valuable on its own, independent of port-intent, and the genuine next buildable thing. It also fixes a real latent gap DT surfaced: **`ToolRegistration` drops `output_schema`.** Port-intent then rides that surface for free once a peer populates it.
