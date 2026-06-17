# Graph-Native Composition — Federation Convergence

**Date:** 2026-06-16 · **Status:** converged (5-voice federation convergence; redlined; operator-recorded).
**Scope:** federation-spanning architecture decision. Pressure-tests the operator's standing priority — *the GRAPH is the primary deliverable, above NL; an artist-only graph tool first is acceptable; NL/chat is secondary and may wait.* See [[feedback_graph_is_the_goal_not_cli]], [[project_graph_first_priority_nl_can_wait]].

**Voices (each grounded in its real repo, not cursors):** forge-vision · forge-contracts · forge-generators · forge-bridge · forge-pipeline/consumer.

---

## Verdict up front

The thesis is **right and broadly endorsed — all five voices lean YES on the substrate.** **Do not start over** — starting over is strictly worse (the expensive, correct layers already exist; the missing piece is new construction either way). But the honest gap is **large, specific, and is the *composition middle*** — a multi-milestone build, not a canvas over existing primitives. One objection survives at full strength (the producer cost) and **bounds** rather than kills graph-first.

The single most dangerous shared illusion to kill: that `ports.py` + `run_chain_steps` + `graph_emit.py` already *are* the graph. They are a validator with no graph, a linear pipe, and a log file that says in its own header it is not an executor.

---

## The central question

Is Forge a graph-native composition system in which CLI / NL / planner / federation are authoring **lenses over ONE node-graph** — and if so, what must each peer change so its capabilities become independently-dispatchable, typed-port composable nodes? Where does the thesis cost more than it's worth, and what is the strongest case *against* graph-first?

---

## The redline — what each voice attacked, what survived

### bridge turned its knife on itself (the load-bearing honest fact)
Bridge — the peer with most to gain from over-claiming — said plainly: **"We are NOT a graph engine. We are a linear chain interpreter."**
- Executor is `run_chain_steps` over a **`list[str]`** with a **single** `__previous_result__` slot (`forge_bridge/console/_engine.py:17`; `_step.py:106-110`). No node-id space, no adjacency, no fan-in, no DAG.
- "Nodes" are regex-sniffed `_maybe_execute_*` branches (`_step.py:604-1198`); `foreach` rejects `->` in its body (`graph/foreach.py:94`) — can't even nest a sub-chain.
- `ports.py` (`PortTopology`/`PortContract`/`validate_chain_wire`, lines 13-245) is **real and good**, but validates edge *n→n+1* lazily at dispatch — there is no whole-graph preflight because there is no whole graph.
- `graph_emit.py` ("graph_store") docstring: *"Not a graph executor. Not a graph reconstruction helper. Not a type registry."* It is an OTel-shape flat JSONL log keyed by `graph_id`.

Bridge has the **bottom third** — typed-port algebra (`ports.py`), shared dispatch (`_execute_python_core`, `utility.py:182`), immutable forward-only run-lineage (`replay.py`: `ReplayEngine.reconstruct:180` mints a new `PipelineRun`, writes back-pointing `replays_run`/`remediates_run`/`amends_run` edges via `_create_lineage_edge:520`/`RUN_LINEAGE_REL_KEYS:44`). It has **none of the middle**. Survived unchallenged.

### contracts claimed the critical path — and won it
Bridge's instinct is to treat the graph as an internal refactor. Contracts' redline: **every peer already has *part* of a node and assumes the whole exists; the typed *edge* is missing and it's mine.**
- `CapabilityDeclaration` (`capabilities.py:33`) carries **untyped** `input_schema`/`output_schema` dict-bags (default `{}`) — a discovery filter, not a wireable port.
- `ArtifactRef` (`references.py:50`) has `artifact_type: str` — an **open, unvalidated** string; two peers can both emit `"matte"` meaning different things (lexicon fracture relocated from family names to artifact types).
- **There is no node-result envelope at all.** Abstention is bolted on: first-class only for references (`ReferenceResolution`, `references.py:34` — `status`/`reason_code`/`message`/`candidates`, normative per ADR-000 §6), and a bare `None`-convention for storyboard fields (`storyboard.py:94`, carries no reason).

Survived — bridge agreed it's missing the middle. **Bridge and contracts co-block, not compete:** contracts types the edges, bridge runs the graph; neither alone unblocks graph-first.

### generators landed the hardest constraint — unbroken
**Don't model nodes as cheap pure functions.** Generators' nodes are async (submit/poll, multi-minute), **billable** (re-running spends real money — `CostRecord`), partial-success-capable (`PartialFidelityReport`), and **non-deterministic by backend** (a seed may not exist — ADR-001 `determinism` fact). A graph engine that re-evaluates on invalidation *bills the client and corrupts on non-determinism*. Becomes a hard requirement on bridge's unbuilt executor: **node eval = submit+poll, completed nodes immutable/superseded never recomputed, cache keys on `backend_identity_triple + inputs + pinned_seed` (disabled when no seed).**

### vision is the vindicated peer (~85% node-shaped) — and amended the axiom
Accepts graph-first enthusiastically (`PortItemType`, `SemanticOperatorSpec`, the `honesty_core.py` determination kernel are real), but corrected **"the graph is the view of record"**: for vision the **immutable Evidence + supersedes lineage is the record; the graph is a lens that compiles to it.** Proved honesty is **necessary but not sufficient** with a real scar (`SUBJECT_PRESENCE_FLOOR=0.70`, `d6ca5bb`): an *honest* node reported a count that *meant* less than it claimed. So the typed port needs **three invariants**, only one fully built:
1. port-type match + **explicit artifact-id, never recency-resolution** (auto-resolving a port by "latest" silently breaks vision's no-auto-traverse-supersedes constitution);
2. per-node **honesty determination** at emit (built — `PASS/NO_DESCRIPTION/FAIL`, `downgrade_observed_to_abstained`);
3. per-node **competence declaration** — which disposition a node may *assert* (flag vs *clear*; the asymmetric-loss "never falsely clear" rule). **Exists nowhere.**

### pipeline threw the punch that connects (see "strongest objection" below)

---

## Strongest surviving objection (full strength)

**Graph-first optimizes the wrong layer and strands half the users.** Grounded in *shipped consumer code*:
- The consumer already built the artist surface and it is **not a node graph** — it's `CommandSurface.tsx`'s **Discover → Review → Apply**, principle *"the LLM populates, the human reviews, the hook executes"* (`forge-pipeline/.planning/FORGE_LLM_ARCHITECTURE.md`).
- Capabilities are **already** independently-dispatchable typed nodes (`flame_rename_shots(sequence, prefix, start, increment, padding)` *is* a typed-port node), composed via review-gated menus + 25 MCP tools — **already satisfying the load-bearing half of the thesis without anyone drawing a graph.**
- The "artists love node graphs" instinct **confuses two surfaces**: the **composition** layer (pixels, one shot, exploratory — Nuke/Houdini node graphs win) and the **orchestration** layer (state, hundreds of shots, repeatable — *nobody wires a graph to rename 40 segments*). Forge's daily driver lives in the latter (`PROJECT.md`: "owns the pipeline layer... not the pixels").
- `PROJECT.md` names the **producer first** in "producer/artist-facing." A producer cannot wire typed ports and can *only* speak NL. **"NL may wait" picks the technical artist and drops the named producer persona.**

**Why it survives and how it bounds (not kills):** it's grounded in what shipped and in the persona doc. But the operator's graph vision is about the **composition layer** (the composer's toolkit — author→still→caption→QC→video, roto pipelines), where pipeline itself **concedes node graphs are the right artist tool.** Pipeline's evidence is about the **orchestration layer**, where graphs lose. Resolution the room converges to: **the graph is the right surface for composition and the substrate-of-record for everything; it is the wrong *mandatory human surface* for orchestration; and parking NL is a real, named cost (the producer) — a known cost with a re-open trigger, not a free win.**

---

## Per-peer change-list (to become node-shaped)

- **contracts (critical path):** typed artifact-type/PortType vocab (open names, **closed connectability** — the proven `vocabulary.py` `role_class` pattern); an edge/binding contract (the compatibility relation `ArtifactRef` lacks); and **`NodeResult = Success | Abstain | Error` carrying `run_id`**, `Abstain` first-class (modeled on `ReferenceResolution`). Stay behavior-free (ADR-000 §1): own the edge *type*, never the decision that edges connect (that's bridge's orchestration lane).
- **bridge (heaviest build):** a **graph IR** (node-id'd persisted DAG, not an ephemeral `list[str]`); a **topological executor** with named multi-input wiring + fan-in/out (replaces `run_chain_steps`, must handle process-nodes per generators); a **node registry/composer** projecting the MCP manifest into wireable descriptors; **whole-graph preflight** (lift `validate_chain_wire`); the **cycle→runs compiler** (the lowering pass — today a comment at `manual_qc.py:134/218`); replace `InMemoryLineageGraph` (`lineage_graph.py:20`, "v0.1 stub", `anchors_of → []`) with a real store; land `GenerationGrant`/#31 enforcement.
- **generators (most ready):** promote `conditioning_surface`/`ReferenceArchitectureSpec` from "advisory facts the planner reads" to **the typed port schema the wire is validated against** (kill `_operator_invocation_from_envelope` metadata-scraping). Make boundary stays **opaque** — refuse flattening the internal comfy graph (the TRELLIS2 failure).
- **vision (most node-ready):** extend `PortItemType` to all 14 artifact schemas (`contracts/versions.py:21-33` outran `operators.py:12-23`); re-type Phase-6 operators; promote `clip_ref`/`render_media_id` from raw paths to typed media ports; move backend selection out of the executor-internal import; **add the competence declaration**.
- **pipeline (consumer):** nothing forced. The graph lights up existing typed ops as nodes for free; adoption is incremental through menus/NL/MCP, **never a migration mandate**. Every drawn iteration must still surface as a **named run → reviewable version with intact lineage** (hide compilation; never hide provenance).

---

## Cyclic composition-graph vs acyclic run-lineage (sub-tension 1)

**The split is architecturally sound; all five agree on the shape** — a cycle in the *authoring view* compiles to **forward-only superseding runs** in lineage (vision's `supersedes` chain; generators' `source_artifact_ids` + `chain_depth`; bridge's `replay.py` edges). Bright lines:
- **generators:** the real cut is **observability, not acyclicity** — inside-a-make = opaque arbitrary topology (cycles allowed, sealed behind submit/poll); composition graph = forward-only DAG. The back-edge that closes a cycle is bridge's **only when a vision-measurement/QC or human gate sits on the edge**; each iteration mints a **new superseding artifact**, never a mutation.
- **vision:** loop **termination must never compile into a vision node** (`clean` is descriptive, not a stop-condition).
- **contracts:** two **typed objects**, not one graph with a `cyclic: bool`. The cycle **must not leak across the peer boundary** — a peer must be blind to "you are iteration 3"; `run_id` on the envelope lets acyclic lineage be reconstructed without exposing the cycle.
- **bridge (load-bearing caveat):** the acyclic run-lineage **target is real and built**; the cyclic authoring **source** and the **compile step** between them **do not exist.** The split is sound in design, unbuilt in fact.

---

## Per-node honesty (sub-tension 3) — one envelope, typed semantics

Not a single uniform rule (rejected as a category error) and not pure convention. The layered answer:
- **contracts** gives the structural mechanism: `NodeResult` with a first-class `Abstain` variant **forces abstention to be representable** at the port. Enforces the **shape** of honesty; **cannot** enforce **content/truth** (a node can construct a fake `Success` — domain-truth has no oracle at the boundary).
- **generators**: honesty is **typed per output register** — measurement (abstain-on-ungrounded), operand/prompt (disclose-provenance + capability-abstain; a prompt is prescriptive, *never falsifiable*), make (declare `PartialFidelityReport`). Uniform envelope, typed meaning.
- **vision**: even honest nodes need a **competence declaration** (flag vs clear) and a **liveness/coverage gate** (abstention-cascade detection).
- **pipeline**: **abstention is *the* load-bearing property** — fabrication is the only failure that ships (rides the `master`/stable pointer downstream to the client). Abstention must be honest **and specific** ("I can't, because no alpha + no greenscreen detected" routes a fix; a bare "I can't" is nearly as useless as a lie).

---

## Viability verdict — and the start-over question

**Build forward. Starting over is strictly worse.** The expensive, hard-won, *correct* layers already exist — bridge's typed-port algebra + immutable run-lineage, vision's honesty kernel + 85%-node-shaped operators, generators' driver/supersedes shape, contracts' abstention template. The missing piece is the **composition middle (executor + typed edges + registry + compiler) — new construction either way.** Starting over pays to rebuild the correct foundation and arrives at the *same* missing middle. **It is viable. It is multi-milestone. Budget it as a composition-engine build, not a veneer.**

---

## Intentionally unbound (with re-open triggers)
- **NL-parking's producer cost** — accepted as a *known* cost. Re-opens the moment the producer persona goes active: NL is then the producer's only lens and stops being deferrable.
- **Cross-peer artifact-type promotion** — vision resists blanket promotion (two-consumer rule); contracts needs typed cross-peer edges. Trigger: an artifact type becoming an *edge between two peers* in a composed graph **is** the second consumer — **promote at the crossing, not preemptively.**

## Rejected (with reason)
- **Graph as the mandatory human orchestration surface** — shipped Discover→Review→Apply + bulk menu ops prove a canvas is worse for state-ops-at-scale.
- **Uniform "pure-function" node semantics** — generators' billable/async/non-deterministic nodes are the design center, not the special case.
- **Uniform single honesty rule** — one *envelope* (`NodeResult`), *typed semantics per register*.

## Structural seams (fossilize fast — design deliberately, surface before committing)
1. **The `NodeResult` envelope shape** (contracts) — a schema that fossilizes federation-wide.
2. **The cycle→runs compile boundary** (bridge) — where the lowering pass lives, between the graph IR and `ReplayEngine`/planner.
3. **The port-type connectability relation** (contracts) — what makes two ports connectable (closed-class).

---

## Sequencing implication (not yet decided — next conversation)

If graph-first proceeds, the first composition-engine milestone is gated by the **co-block**: contracts' `NodeResult` envelope + typed edge, and bridge's graph IR + topological executor, are the two things without which "an artist wires nodes and it runs" stays vapor. #66's author→still→video loop is the natural **first artist-wired graph** (a composition-graph cycle that compiles to acyclic runs) — the demonstrator that exercises the executor, the compiler, the typed edge, and all three honesty registers at once.
