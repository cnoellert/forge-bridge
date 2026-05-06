# Phase transition: from "can this work?" to "how does this fail?"

**Captured:** 2026-05-06
**Audience:** future contributors (and future-me) opening this repository for the first time
**Self-contained:** yes — readable cold, no need to follow links or read the conversation that produced it

This document records a conceptual transition the project went through during Phase A, A.4, and A.5/A.6. It is not a phase artifact. It is project-level orientation: how decisions get made now, and why.

---

## What changed

For most of forge-bridge's first year (v1.0 through v1.4), the dominant question was:

> **Can this work?**

Can a single canonical vocabulary span Flame, projekt-forge, an LLM, and editorial systems? Can a learning pipeline observe execution and synthesize tools? Can chat agentically call MCP tools and synthesize useful answers? Can a single daemon co-host four user-facing surfaces? Each phase shipped because the answer was yes — feasibility-first, with operational behavior treated as a secondary concern.

By Phase A, the cumulative weight of those affirmative answers shifted the dominant question to:

> **How does this fail?**

Not because the system stopped working — it works — but because feasibility-era behaviors (a chat call that hangs 75 seconds when its dependency is unreachable; a forced-tool wrapper that passes `{}` to a schema requiring `params`; a narrower that picks the wrong tool by keyword) become production-grade liabilities the moment a real operator depends on them daily.

That shift is the transition this document records. The project is moving from feasibility into operational adulthood.

---

## What "operational adulthood" means here

Three concrete commitments, each established in a recent phase:

1. **Truthful contracts** (Phase A): the chat endpoint round-trips the full execution history. The shape of a successful response and the shape of a failed response are both legible and consistent. No hidden state.
2. **Startup-path integrity** (Phase A.4): every entry point — Claude Desktop's stdio, direct HTTP daemon, `fbridge up`, launchd plist — funnels through one bootstrap with one set of initialization invariants. No entry-point-specific behavior.
3. **Reliability methodology** (Phase A.5 / A.6): when something fails, classify the failure before patching. Map the runtime statically before instrumenting it. Verify a bisect is *causal*, not *co-incident*, before committing to a deep investigation. Ship environmental ruleouts cheap before elevating.

These commitments are infrastructure-grade. They cost discipline up front; they earn trust over time. They are what lets the system stay viable once real production pressure arrives.

---

## Intelligence availability as infrastructure

A specific instance of the same shift, worth naming:

The chat endpoint, the synthesized tools, the LLM-driven narrowing — all of these depend on an LLM endpoint being reachable. Through v1.4, that dependency was treated as ambient: it works because Ollama is up. Phase A.6 surfaced a 75-second failure mode caused by the LLM being unreachable from inside the daemon — and the lesson was not "Ollama broke" but "we have not yet treated intelligence availability the way infrastructure is treated."

Infrastructure-grade dependencies have:
- explicit reachability surfaces (preflight probes, fast-fail timeouts, doctor checks),
- bounded failure behavior (a connect failure surfaces in seconds, not the OS default),
- graceful degradation paths (the system keeps doing the work that doesn't require that dependency),
- observable health that an operator can inspect without grep'ing logs.

The chat path has none of these for its LLM dependency yet. The path forward is not "make the LLM more reliable" — it is "treat LLM availability as infrastructure, with the same discipline applied to databases, message buses, and network reachability." That framing is what carries the project from "we use an LLM" to "intelligence is a runtime resource our system manages."

---

## Surfaces vs. moat — Layer 1 and Layer 2

There is a temptation, after a sequence of disciplined reliability phases, to start describing the operational discipline itself as the project's differentiator. That temptation is wrong, and worth flagging explicitly so it does not steer future decisions.

**Operational discipline creates trust. It does not create initial pull.**

Operators do not adopt a tool because its runtime map is elegant or its bisect discipline is rigorous. They adopt because the tool materially improves their day-to-day work. For forge-bridge specifically, that means the surfaces:

### Layer 1 — consumer-facing differentiation (the hook)

- Flame surfaces (right-click, contextual commands, batch helpers)
- The schematic
- The Ask dialog
- Foundry workflows
- Notes routing
- Operational acceleration that shows up in the artist's day

These are what get people to install forge-bridge. These are what survive a fresh-eyes evaluation by an artist who has never read a phase spec.

### Layer 2 — operational differentiation (the moat)

- Truthful contracts
- Graceful degradation
- Runtime observability
- Bounded failure behavior
- Evidence-driven reliability work
- Infrastructure-grade operational discipline

These are what keep forge-bridge in production after adoption. These are what let the project survive a real outage, a real misconfiguration, a real production-pressure moment without cratering operator trust.

**Both are load-bearing. They operate at different layers.**

Layer 1 gets people in. Layer 2 keeps the system viable once they are in. A project with Layer 2 only is theoretically pure and practically irrelevant. A project with Layer 1 only earns adoption and then loses it the first time production pressure breaks an undisciplined assumption. The healthy long-term shape is *consumer-facing ambition built on operationally trustworthy substrate*, not operational purity replacing consumer-facing ambition.

---

## How decisions get made now

The transition concretely changes how phases get scoped:

| Pre-transition framing | Post-transition framing |
|------------------------|--------------------------|
| Can we add this feature? | What's the failure mode if we add this feature? |
| Does this code work? | How does this code behave when its dependency is down? |
| Is the change correct? | Is the contract preserved across the change? |
| Did the test pass? | Does the test prove the invariant we care about? |
| Move fast and ship | Move with discipline so we don't have to re-ship |

This does not mean every change needs a runtime map and a 6-step diagnostic methodology. It means the project now has the discipline available when work warrants it — and uses it when the substrate is load-bearing or the failure surface is real. Trivial changes still ship trivially.

---

## What this document is NOT

- It is not a methodology spec. The procedural observations (map first, probe second; verify bisect is causal; reliability output is not always a fix) are kept in `.planning/seeds/SEED-RELIABILITY-PHASE-METHODOLOGY*.md` as forward-looking process artifacts. Promotion to formal methodology is gated on additional reliability phases.
- It is not a roadmap. Layer 1 surfaces (schematic, Ask, foundry, notes routing) ship in their own dedicated phases under their own seeds.
- It is not a manifesto. It is a snapshot of how the project's center of gravity moved between two questions, and what that means for the people who pick the work up next.

---

## One-line summary

forge-bridge is now a project that ships consumer-facing ambition on an operationally trustworthy substrate, knows the difference between the two, and decides accordingly.
