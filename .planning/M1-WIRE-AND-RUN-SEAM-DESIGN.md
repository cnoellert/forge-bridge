# Milestone 1 — "Wire-and-Run v0" — Seam Design (converged)

**Date:** 2026-06-17 · **Status:** seam design converged (Orch draft → DT + Creative redline → folded). Ready for the verification vertical + phase plan.
**Parent:** [[GRAPH-NATIVE-COMPOSITION-CONVERGENCE]] · **Demonstrator-later:** [[AUTHOR-STILL-VIDEO-LOOP-FRAMING]] (#66, the cyclic milestone).

## M1 boundary (locked)

The minimal engine that takes a **persisted node-id'd DAG (`GraphSpec`)** containing a **fan-in**, runs it through a **new topological executor** that resolves each node's inputs from **named edges**, carries a typed **`NodeResult`** on every edge, validates every edge, and records forward-only lineage — proven on **cheap vision nodes**, **acyclic-enforced**.

**Out of M1 (deliberate):** cycles + the cycle→runs compiler (→ #66 milestone); generators' billable/async process-node semantics (→ M2); the artist canvas; NL compilation; competence-declaration + liveness gate.

---

## Forcing function

A **fan-in node** — one node with two+ *named* upstream inputs converging — is what `run_chain_steps` (single `__previous_result__` slot) structurally cannot express. Vision already ships one: `validate_perspective(CameraMotionEstimate, DepthEstimate, PlaneEstimate)`. The moment a fan-in GraphSpec runs, the linear-pipe era is over.

---

## Seam A — `NodeResult` (the typed thing every node emits)

Mirrors the proven abstention template `ReferenceResolution` (which lives in **forge-contracts** — so NodeResult *echoes a contracts shape*; see A-home).

```
NodeResult:
  status: "ok" | "partial" | "abstained" | "error"   # discriminator
  output:        <payload>            # present for ok/partial
  output_topology: {kind,item_type}   # inferred at emit (infer_topology) or declared
  artifact_type: str                  # rich type name — ADVISORY in M1 (contracts validates later)
  fidelity:      {compromises[], remediation[]}   # present for partial
  reason_code:   str                  # machine token (abstained/error); per-register vocab
  message:       str                  # human (abstained/error)
  candidates:    [...]                # abstained (à la ReferenceResolution)
  run_id:        uuid                 # lineage anchor — MANDATORY
  source_artifact_ids: [uuid]         # forward-only lineage edge
```

**A1 — 4 variants (`ok|partial|abstained|error`). RESOLVED: 4.** `partial` (a make that succeeded *with declared compromises*) is terminal; collapsing it into `ok+fidelity` forces every downstream to re-parse fidelity to recover the branch — the "island" anti-pattern.
**Crispness invariant (DT/Creative):** *"is there a usable output?" must be derivable from the discriminator ALONE* — `ok|partial → yes`, `abstained|error → no`. Downstream nodes must never inspect payload or fidelity to find branch semantics.

**A2 — RESOLVED: payload + emit-time `infer_topology`; `artifact_type` advisory.** Topology validated at the edge now; contracts validates `artifact_type` after promotion. Don't block M1 on rich typing.

**A3 — RESOLVED: one envelope, per-register `reason_code` vocab.** `abstained` means "couldn't ground" (measurement) / "lack conditioning surface" (operand); `partial` is the make register's honesty. Uniform shape, register-specific reason codes. No structural fork.

**A-home (THE synthesis — A-home + the cross-cutting gap are ONE seam):**
Siblings (vision/generators/…) keep emitting their **native MCP results**. At the **bridge boundary** (`drivers.py` / rung-D `BridgeGenerationDriver`), a single **boundary adapter does two jobs**: (1) **derive a `PortContract`** for the semantic operator, and (2) **mint the `NodeResult`** by wrapping the sibling's native result. **The sibling never emits `NodeResult`; bridge mints it.** Consequences: `NodeResult` stays **bridge-internal for M1** (promotion to contracts = an internal refactor, not a federation-breaking migration), and the derived contract is **permissive-by-default** (feeds the B2 invariant). Plan A-home and the operator-contract gap as the **same** work item.

---

## Seam B — `GraphSpec` (the persisted node-id'd DAG)

```
GraphSpec:
  nodes: [ NodeSpec ]
  edges: [ Edge ]

NodeSpec:
  node_id:   str
  operator_id: str
  backend_id: str?
  input_ports:  { port_name: PortContract }   # NAMED — the fan-in unlock (reuses ports.py PortContract per port)
  output_port:  PortTopology
  config: {...}

Edge:
  from: { node_id, output_port: "out" }
  to:   { node_id, input_port: "<name>" }
```

**B1 — named multi-input ports via additive `input_ports: dict[name, PortContract]`. RESOLVED: additive (option B).** Zero break to `ports.py`; each port's `PortContract.accepts` keeps its current meaning ("shapes this *one* port accepts"); `accepts_topology` runs per named edge unchanged.

**B2 — new `GraphSpec` + compiler (`operator_sequence → GraphSpec`); graph is the IR-of-record. RESOLVED: new GraphSpec (option B).** A linear plan compiles to a degenerate single-path graph. *[structural seam — the fossilizing call.]*
**Migration invariant (DT/Creative — MANDATORY):** semantic operators are **unvalidated today** (`_port_contract_for_step()` → `None` → validation skipped, `_step.py:492-493`). M1-derived contracts must be **permissive-by-default (`PortContract.any()`)**. New validation must **not fail an edge that is unvalidated today** — introducing validation must not regress currently-green workflows. Tightening comes later.

**B3 — topological executor over a `node_id → NodeResult` map; reject cycles. RESOLVED, with three refinements:**
- (a) **Validate each edge with `PortContract.accepts_topology(actual)` directly, NOT `validate_chain_wire()`** (chain-identity machinery). Wrap failures in a **graph-native edge error** carrying `from_node`/`to_node`/`port`.
- (b) **ONE executor.** `operator_sequence → GraphSpec → graph executor` is the runtime path for *everything*; `run_chain_steps` is **replaced wholesale, not kept beside** (two executors = divergence + violates "graph is the view of record"). The `__previous_result__` single-slot model is threaded through `_engine.py` (3 sites) + `_step.py` (5 sites) — the new executor supersedes that model, it does not extend it.
- (c) **Acyclic-enforced** in M1: the executor topo-sorts and rejects cycles. This is where the no-back-edge invariant lives in the IR.

**B4 — `GraphSpec` is the IR-of-record; `graph_emit.py` stays observability. RESOLVED: B4.** GraphSpec = intent (a persisted DAG definition); the JSONL emit-log = observation (OTel-shape event stream). The emit-log's own docstring anticipated a "runtime primitive later" role — B4 resolves that the runtime role goes to **GraphSpec**, not to promoting the event log.

---

## The two-graphs closure (banked, not deferred-as-fight)

M1's `GraphSpec` (authoring graph) is **acyclic**. Loop-authoring arrives **later** as a compiler that lowers an authored cycle to **immutable re-mint** (new run + `remediates_run` edge) — keeping run-history acyclic. This operationalizes the convergence's two-graphs split: cyclic authoring view ⇒ acyclic run-lineage. It honors **#31** (no-back-edge DAG) and the composition manifesto **in one IR**. The design **banks the resolution**; it does not carry the unresolved fight forward.

---

## Verification vertical (the green-bar target — cut the phase plan against THIS, not prose)

A self-contained, daemon-free test: **three stub perception nodes emit `NodeResult`s that converge on one consumer node's three named input ports**, run through the `GraphSpec` executor. Asserts:
1. **Named-port fan-in** — the consumer receives each upstream on the correct named input port (not a single slot).
2. **Per-edge validation** — every edge validated via `accepts_topology`; an intentionally mis-typed edge raises the graph-native edge error (`from_node`/`to_node`/`port`).
3. **Permissive-by-default** — a semantic-operator node with a derived `any()` contract does **not** fail an edge that is unvalidated today.
4. **Acyclic enforcement** — a GraphSpec with a back-edge is rejected before execution.
5. **Discriminator branch rule** — "usable output?" derivable from `status` alone (`ok|partial` vs `abstained|error`), without reading payload/fidelity.
6. **Lineage** — each node's `NodeResult.source_artifact_ids` + `run_id` record the forward-only edge; the converged consumer's lineage names its three upstreams.

This proof — *capabilities composing through named ports, every edge validated, NodeResults flowing, acyclic-enforced, lineage recorded* — is the first evidence that composition works. It is more important than any individual node implementation; the phase plan's task 1 is **make this test green**.

---

## Resolved forks summary

| Fork | Resolution |
|---|---|
| A1 variants | **4** (`ok\|partial\|abstained\|error`) + discriminator-derivable usable-output rule |
| A2 output typing | payload + `infer_topology`; `artifact_type` advisory in M1 |
| A3 honesty registers | one envelope, per-register `reason_code` vocab |
| A-home | **adapter mints NodeResult at the bridge boundary** (= the operator-contract gap, one seam); bridge-internal for M1 |
| B1 named ports | additive `input_ports: dict[name, PortContract]`; no `ports.py` break |
| B2 IR-of-record | new `GraphSpec` + `operator_sequence→GraphSpec` compiler; **permissive-by-default validation invariant** |
| B3 executor | one executor; `accepts_topology` (not `validate_chain_wire`) + graph-native edge error; acyclic-enforced; replaces `run_chain_steps` wholesale |
| B4 persistence | `GraphSpec` is IR-of-record; emit-log stays observability |

## Fossilizing choices that survived pressure
**A1** (4 variants), **B2** (GraphSpec as IR-of-record + permissive migration invariant), **B4** (GraphSpec ≠ emit-log). All three survived the DT + Creative redline unchanged in direction.
