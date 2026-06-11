# VISION-COMPOSITION-SEAM

**Date:** 2026-06-10
**Authors:** forge-bridge (DT) ↔ forge-vision
**Status:** Grounded inquiry response — durable reference for the federation / rung-C (#31) and chain-engine lanes
**Subject:** The greenscreen→roto chain as a forcing case for the bridge's internal composition graph

---

## TL;DR

The composition graph forge-vision wants **exists and is live — but it is not the layer the inquiry points at.** There are **two** composition surfaces in the bridge; naming them resolves the whole question.

| Surface | Module | State | Role |
|---|---|---|---|
| **Chain engine** | `console/_engine.py` + `_step.py` + `graph/ports.py` | **LIVE, production** (backs `/api/v1/exec` + chat-compile mutating preview) | composition + structural logic |
| **Federation planner** | `orchestration/planner.py` + `planner_passes.py` | **test-only demonstrator** (imported nowhere outside `tests/`) | would auto-route capability→capability — **rung-C / #31, deferred** |

**greenscreen→roto can be built today** as an *authored chain* over vision's Q→A MCP tools, wired by the chain engine. It does **not** need the federation planner (#31), and it does **not** need typed-Evidence binding. The two things that would require *building* — typed-Evidence binding in the chain layer, and live generation-artifact auto-carry (rung-D) — are real work but are **not** on the critical path for a first authored greenscreen→roto.

---

## The reframe: two composition surfaces

### 1. Chain engine — LIVE
- `forge_bridge/console/_engine.py`, `forge_bridge/console/_step.py`, `forge_bridge/graph/ports.py`.
- Backs the deterministic `/api/v1/exec` path and the chat-compile mutating-preview path — **in production use**.
- Wires step-A-output → step-B-input and has real branching primitives: `foreach`, `collect`, `select`, `filter`, `if_gate`, `commit`.
- This is the "composition + logic" layer. It **executes** authored logic; it does not **author** semantics.

### 2. Federation planner — DEMONSTRATOR (rung-C / #31)
- `forge_bridge/orchestration/planner.py`, `planner_passes.py`.
- Six passes, but `pass_5_rank_and_predict` builds a single-operator sequence with `inputs: []` **always empty** (`planner_passes.py:368`) — **zero inter-step wiring**.
- `Planner(...)` is constructed only in `tests/smoke_helpers.py:439`; imported nowhere outside `tests/`.
- This is **rung-C** — GitHub **#31** ("Live planner-invocation path (rung C — NEEDS FRAMING, mutating surface)", OPEN).
- Doctrinally deferred (`.planning/LIVE-GENERATION-JOIN-RUNGS.md:51-62`): bridge will not *originate* generation intents until a named consumer demands bridge-as-producer **and** mid-mutation atomicity is solved. Building it live would invert the substrate-not-producer doctrine.

> When vision says "the workflow lives in the bridge's internal graph," that is **true today via the chain engine** — not via the federation planner, which is the deferred part.

---

## The four asks, answered

### Ask 1 — Does a composition layer wire operator output → input through logic today? Where does rung-C/#31 stand?

**Yes — the chain engine, live.** It carries one operator's result into the next and gates on it (`if_gate`, `select`, `filter`).

What it does **not** do is *author* the semantic decision ("because greenscreen, now ask roto"). That branch content is **authored** — by a consumer's chain text or by the LLM compile path — then executed deterministically. The thing that would *auto-derive* "because greenscreen → ask roto" is the federation planner = **#31, OPEN, deferred**.

**Recommendation: do not wait for #31.** The authored-chain version is the correct v1 and runs now.

### Ask 2 — Contract for primitive→primitive: how does A's Evidence become B's typed input?

Today the binding is **untyped payload + typed *topology*** — NOT typed Evidence:

- Payload flows as a raw dict: `context["__previous_result__"]` (`_engine.py:35`).
- A `PortTopology{kind, item_type, cardinality}` is **inferred** from that result (`ports.py:181`) and validated at the next dispatch edge against the consuming node's `PortContract.accepts` (`validate_chain_wire`, `_step.py:459`). Mismatch → `CHAIN_WIRE_COMPATIBILITY_ERROR`.
- **`forge_contracts` Evidence types do NOT participate in the chain layer.** `Evidence` / `ArtifactRef` / `GenerationCapabilityFacts` live only in the orchestration (federation) layer. The chain engine has zero `forge_contracts` imports.

So there is **no typed Evidence→input binding** today. `is_greenscreen`'s region-Evidence becoming `what_needs_roto`'s geometry-input would be validated **structurally** (a list of regions, cardinality N), **not semantically**.

**The design fork for vision:** keep the seam **structural** (topology — exists now, cheap, compose by shaping outputs) or build **semantic-typed Evidence binding** (new work — and it belongs in the *chain* layer, not the federation layer). **Bridge lean: ship structural first; it is enough to make greenscreen→roto real.**

### Ask 3 — Media artifact carriage between steps and to Flame — by-reference?

**Confirmed, by-reference.** *"The DB carries identity + metadata + path; the filesystem carries bytes"* (`.planning/PHASE-4B-ORCHESTRATION-DESIGN.md:109`). Two layers:

- **Entity layer (LIVE):** `Locatable` trait + `location_add`; `register_publish` attaches an `output_path` as a Version location (`tools.py:1372`); Flame consumes via openclip/path (`copy_to_media_panel`, `publish.py:430`). A matte today = a media entity (`role=roto`/`matte`, `member_of` its Shot) + a location path; Flame reads the path. A matte-producing cousin already attaches: `forge_derive_holdout_mattes`.
- **Orchestration layer (DEMONSTRATOR):** the `orch_generation_artifact` envelope `{platform_locators, content_provenance, execution_provenance}` with `ArtifactRef.locator` as the reference currency (`dispatcher.py:205`). But `platform_locators` starts `{}` and **no live driver populates it** — generators are schema-only, **rung-D adapter unbuilt**. By-reference is designed + fixture-tested here, not lit end-to-end.

**Net:** emit the matte **by-reference** (path/URI, `role=roto`/`matte`) and the **entity-layer** path to Flame is live now. The auto-carry through a generation-artifact envelope is demonstrator-grade, waiting on rung-D.

### Ask 4 — Where does routing logic live, who authors it?

Live: **the chain text is the routing logic**, authored by either a human consumer (projekt-forge writes/compiles the chain) or the LLM compile path (planner-front for reads; chat-compile for mutating previews). The graph **executes**; it does not author semantics. The standing auto-router is the federation planner = #31, deferred + test-only.

**Doctrine agreement worth stating plainly:** vision's *"agency stays in the graph; vision answers, the graph decides what to ask next, vision never self-chains"* is **exactly** bridge's substrate-not-producer doctrine. We are aligned on the seam. The only delta is *where* "decide what to ask next" is realized — today it is **authored** (human/LLM chain), not a standing planner. The standing planner is the deferred #31.

---

## What this means for forge-vision (the teeth, back)

1. **Ship the three operators as stateless Q→A MCP tools.** Vision already attaches as a sibling — `forge_classify_shot`, `forge_detect_planes`, `forge_derive_holdout_mattes` et al. are live in the registry. They are invocable and wireable **today**.
2. **Shape outputs as clean topologies** (a list of segments; a manifest; a matte-by-reference) so they compose through the chain engine's structural validation — no semantic-type contract needed for v1.
3. **Treat "because greenscreen → ask roto" as an authored chain** for now (human or LLM-compiled), not auto-planner agency. That works today; #31 is the deferral, not the blocker.
4. **Emit the matte by-reference** (path + `role=roto`/`matte`, `member_of` Shot); the entity→Flame reference path is live.

**The chain only becomes real where bridge composes it — and that surface (the chain engine) is the live one.** Land the primitives as clean-topology MCP tools and greenscreen→roto wires as an authored chain **without** waiting on rung-C/#31 or rung-D.

---

## What would require building (off the critical path)

- **Typed-Evidence binding in the chain layer** (Ask 2) — if the structural/topology seam proves insufficient and vision wants `Evidence`-typed output→input contracts. Belongs in the chain layer (`graph/ports.py` neighborhood), **not** the federation layer.
- **Live generation-artifact auto-carry** (rung-D) — a real `BridgeGenerationDriver` adapter via the `handler=` slot that populates `platform_locators` from a real backend. Buildable, but doctrinally must be **paired with a plan-producer** (a lit driver registry with no plan-producer is "wired ≠ works"). See `.planning/LIVE-GENERATION-JOIN-RUNGS.md`.

Neither is on the critical path for a first authored greenscreen→roto.

---

## Cross-references

- `.planning/LIVE-GENERATION-JOIN-RUNGS.md` — rung A/B/C/D framing; rung-C deferral disposition (redline-confirmed).
- `.planning/PHASE-4B-ORCHESTRATION-DESIGN.md` — semantic-vs-operational storage cut; by-reference media doctrine (`:109`).
- **#31** — Live planner-invocation path (rung C — NEEDS FRAMING, mutating surface). OPEN.
- Chain engine: `forge_bridge/console/_engine.py`, `_step.py`; `forge_bridge/graph/ports.py`.
- Federation planner: `forge_bridge/orchestration/planner.py`, `planner_passes.py`.
- Media-by-reference: `forge_bridge/core/traits.py` (`Locatable`), `forge_bridge/tools/publish.py`, `register_publish` (`tools.py:1285-1387`), `orchestration/dispatcher.py:205`.
