# #104 — Admit `traffik.editorial.apply_steps` into Bridge graph dispatch — Orch Framing

**Date:** 2026-06-22 · **Status:** FRAMING (Orch positions + grounded; awaiting DT redline on fresh context → Creative → converge → pass-to-code).
**Base:** main `1cc3b4c`. **Tracks:** issue **#104** (cross-repo handoff from forge-pipeline PR #13, proof commit `c2685dea`). **Parents:** [[project_passoff_2026_06_22_dt_m2_arc_on_main]] (DT's M2 cursor — load-bearing doctrine) · #92 (the seam note this concretizes) · [[project_federation_facts_judgment_spine]] · [[project_roadmap_finish_m2_then_first_graph_vertical_66]].
**Why now:** first **real federation peer** composing GraphSpecs against Bridge's executor — the real-consumer substrate pressure the roadmap calls for, and the **pattern-setter for #66** (admit a federation operator into `UnifiedDispatch` via a boundary).

**Note for DT (fresh context):** §1 is the grounded dispatch surface (already mapped — don't re-ground). **§0.5 is the PRIMARY framing question (operator-elevated 2026-06-22) and governs everything below — read it first.** §2 carries Orch positions, revised under §0.5; **Q-B changed** (an earlier draft proposed `dispatch_kind="pipeline"` + `PipelineOperationBoundary` — that was the silo error, now corrected).

---

## 0.5 PRIMARY framing question (operator-elevated — the invariant that governs #104)

**Can a single `GraphSpec` freely compose operators implemented by multiple federation peers?** The answer must be **yes**. A "no" violates the north star (compose arbitrary atomic capabilities into ONE workflow). See [[project_federation_implementation_not_composition_boundary]].

**Invariant: federation boundaries are IMPLEMENTATION boundaries, not COMPOSITION boundaries.** From the graph's perspective there are no "Pipeline nodes" or "Vision nodes" — only operators whose implementations live in different places. The target is ONE graph like:
```
read_plate → detect_edit_points(Vision) → apply_editorial_steps(Pipeline)
           → generate_inbetween(Generators) → validate_continuity(Vision) → publish_sequence(Bridge)
```
The anti-goal we must not drift into: a Pipeline graph + a Vision graph + a Generators graph (re-created silos).

**Three INDEPENDENT ownership axes — keep them independent:**
1. **Graph ownership** — Bridge owns the `GraphSpec` + execution substrate. Always Bridge.
2. **Operator ownership** — the peer that *implements* the capability (Pipeline implements editorial; Vision perception; Generators generation).
3. **State authority** — whoever owns the *state being mutated* enforces authority. Bridge ratifies only Bridge-host (Flame) state; a peer mutating its own state enforces its own.

Pipeline owning editorial operators does **not** imply Pipeline owns an editorial graph — it owns the *implementation* of those operators. **Evidence the invariant already holds in code:** Vision's `forge_roto_ref` is admitted `dispatch_kind="mcp"` (`admission.py:66-73`) and composes beside forge-core operators in one graph today. There is no vision dispatch lane. #104 must **extend** that path, not fork a Pipeline lane.

**Mechanism the invariant implies:** Bridge owns graph + orchestration → `UnifiedDispatch` resolves operator → owning peer → boundary *delegates* execution → owning peer enforces its own authority → `NodeResult` returns into the same graph.

**Creative's tightening (the last abstraction layer — locked):** *the graph composes CAPABILITIES, not transports.* Transport (local / sibling-MCP / injected client / HTTP / future) is an **implementation detail of the operator, declared by the capability — not part of the graph model.** The graph must stay oblivious: no "MCP nodes" / "local nodes" / "Vision nodes," only capabilities. This makes **four concerns fully orthogonal:**
1. **Composition** — the `GraphSpec` (knows only capability identity / `operator_id`).
2. **Capability resolution** — the registry (capability → implementation).
3. **Invocation** — dispatch (reads the capability's *declared* invocation mechanism, honors it).
4. **Authority** — the state owner.

So the question is **not** "MCP operator or Pipeline boundary?" (transport-first). It is **"what invocation mechanism does the `apply_steps` capability *declare*?"** — dispatch resolves it; the graph never knows. Today's `dispatch_kind` enum is Bridge *hardcoding* the invocation mechanism per-operator — a **stand-in** for capability-declared invocation; the seam is to resolve invocation *from the declaration* (touches #24).

---

## 0. What #104 asks (one paragraph)

Pipeline has banked the Traffik editorial substrate and **proven Bridge's real `GraphExecutor`** runs a two-node `GraphSpec` over it — using a *test-local dispatch adapter*. Bridge must now admit `traffik.editorial.apply_steps` into the **real `UnifiedDispatch`** so ordinary GraphSpecs run Traffik editorial work without the shim. Pipeline is Bridge-ready; Bridge is not yet Traffik-aware in production dispatch. Bridge must **not** become Traffik-aware in its *internals* — Traffik stays a Pipeline execution capability that consumes/emits plain packets; Bridge only learns to *route* to it.

---

## 1. Grounded dispatch surface (mapped 2026-06-22, file:line)

- **`DispatchKind`** = `Literal["mcp","primitive","foreach","commit"]` (`admission.py:18`). Adding a route = widen this Literal + add a boundary + one `UnifiedDispatch` field + one routing branch.
- **`AdmissionRecord`** (`admission.py:25-52`, frozen): `operator_id` · `resolved_class` · `dispatch_kind` · `synchronous` · `returns_reference` · `no_state_mutation` · `idempotent_result`. Table = `_ADMISSION_RECORDS` tuple → `ADMISSION_TABLE` MappingProxy (`:135-137`). `admit_operator()` fail-closes with `AdmissionRejected` (`:140-146`).
- **`UnifiedDispatch`** (`dispatch.py:21-53`, dataclass): boundary fields `mcp_boundary`/`primitive_boundary`/`foreach_boundary`/`commit_boundary` + `assent_record: Any|None`. `dispatch(node, resolved_inputs) -> NodeResult` routes by `dispatch_kind` (`:36-53`). **Only `commit` receives `assent_record`** (`:47-52`) — every other kind never sees assent.
- **Boundary protocol** (`boundary.py`): `async def dispatch(self, node: NodeSpec, resolved_inputs: dict[str, NodeResult]) -> NodeResult`. `commit_boundary` adds keyword-only `*, assent_record`. **`MCPToolBoundary.__init__(*, mcp=None, run_id=None, artifact_id_factory=uuid4)`** — the **dependency-injection precedent**: the external client is constructor-injected.
- **`NodeResult`** (`node_result.py:26-45`, frozen): `status` ∈ `("ok","partial","abstained","error")` (`:22-23`) · `run_id` · `artifact_id|None` · `output` · `output_topology` · `artifact_type` · `fidelity` (partial) · `reason_code`/`message` (abstained/error) · `candidates` · `source_artifact_ids` (lineage) · `resolved_class` · `control_signal`. `has_usable_output` = status ∈ {ok,partial} (`:55-62`).
- **`NodeSpec`** (`graph_spec.py:20-32`): `node_id` · `operator_id` · `input_ports: dict[str,PortContract]` · `output_port: PortTopology` · `backend_id` · `config: dict`. `resolved_inputs` = `{edge.to_port: NodeResult}` (`executor.py:114-117`); upstream value = `.output`, upstream lineage id = `.artifact_id`.
- **Lineage pattern** (every boundary): `source_artifact_ids = tuple(r.artifact_id for r in resolved_inputs.values() if r.artifact_id is not None)`.
- **Ports** (`graph/ports.py`): `PortContract.manifest_gate()` (`:87-88`) accepts/emits `PortTopology.manifest()` — the issue's suggested input port for `step_plan`. Real.
- **Edge-or-config dual-source precedent:** `CommitBoundary` reads `held` from `node.config["held"]` *or* `resolved_inputs[single].output` (`commit_boundary.py:62-69,196-204`) — slice-4 held-from-edge. #104's `step_plan` reuses exactly this.

---

## 2. Orch positions

### Q-A — Authority (THE CRUX): peer-owned mutation, **no Bridge ratify gate.**

`traffik.editorial.apply_steps` is declared `no_state_mutation=False` — it mutates state. Bridge's slice-3 doctrine puts host mutations behind `CommitBoundary` + a ratified `AssentRecord`. **It must NOT route through `commit`.** Reasoning:

- Bridge's `commit`/`CommitBoundary` authority is specifically for **Bridge-host (Flame) mutations** — Bridge verifies held-vs-fresh and requires *operator* assent because Bridge is the authority over Flame state. `apply_steps` mutates **Pipeline's own editorial/timeline state**, carries **Pipeline's own `idempotency_key` + execution receipt**, and Pipeline owns the proof. Bridge is *not* the authority here.
- Within #104's scope, `apply_steps` mutates Pipeline editorial state and **returns `TimelineDelta` payloads for a host adapter to apply later** — and applying those deltas to Flame is **explicitly out of scope** (non-goal: "Do not require Flame/live DCC state"). So nothing in #104 touches Bridge-host state.
- This is the **federation facts/judgment spine** ([[project_federation_facts_judgment_spine]]): peers own disposition over their own domain. "Do not make Traffik part of the Bridge graph runtime."

**Position:** route through a **new non-commit boundary that mints a `NodeResult` but never touches `AssentRecord`.** Structurally clean — only `commit` ever sees assent (`dispatch.py:47-52`), so a non-commit kind *cannot* accidentally acquire a ratify gate.

**This sharpens #86's unresolved `no_state_mutation` semantics — a genuine contribution back:** the flag conflates two orthogonal axes. (1) *Does it change state?* (`no_state_mutation`) and (2) *Whose authority gates the change?* `apply_steps` is `no_state_mutation=False` (axis 1: yes) AND peer-authority (axis 2: Pipeline's receipt/idempotency, no Bridge ratify). Bridge ratify-gates **only Bridge-host** mutations. Recommend recording this two-axis split on #86.

**Forward-pointer (draw the line now to prevent a future mistake):** when the `TimelineDelta → Flame` application eventually lands (future work, not #104), *that* step IS Bridge-host mutation territory and WOULD need `commit`/ratify. The authority boundary is: **`apply_steps` (peer editorial mutation) = peer-owned, no ratify; future delta→Flame application = Bridge-host, ratified.** Don't let anyone route the Flame application without a ratify gate later.

### Q-B — Invocation resolution: **dispatch honors the mechanism the capability DECLARES; the graph stays oblivious to transport.** [REVISED under §0.5 + Creative]

> Two superseded drafts: (1) `dispatch_kind="pipeline"` + `PipelineOperationBoundary` — the silo error; (2) "admit over the MCP transport vs add a kind" — *still transport-first*. Both smuggle transport into the graph model. Corrected: the graph composes capabilities; **invocation mechanism is a property the capability declares, resolved at dispatch.**

**Position:** `apply_steps` carries an invocation declaration (it's already published via `forge_core.bridge.contract_registry.iter_capability_declarations(["editorial"])`). Bridge admits the capability and **dispatch resolves invocation from that declaration** — whether the declared mechanism is sibling-MCP (as `forge_roto_ref` already is) or an injected execution client, *the graph and the GraphSpec are identical either way.* No Pipeline lane, no transport category at the graph level.

**The load-bearing grounding question for DT (operationalizes Creative's model):** *Does the `editorial` capability declaration carry an invocation-mechanism contract that dispatch can resolve — or does Bridge today only have the hardcoded `dispatch_kind` enum?* Two implementation paths, both consistent with the locked model:

- **Path A — declaration already carries (or trivially can carry) the invocation mechanism.** Then #104 is the **first capability whose invocation is resolved from its declaration**, not hardcoded — a real, minimal step toward the four-concern model, demonstrated on one operator. Strongly preferred: it instantiates the invariant instead of just preserving it.
- **Path B — only the hardcoded `dispatch_kind` enum exists today, and the declaration doesn't yet carry invocation metadata.** Then #104 admits `apply_steps` with its current invocation mechanism (most likely the same sibling-MCP path roto uses → `dispatch_kind="mcp"`, no new machinery), **and records the gap**: `dispatch_kind` is a stand-in for capability-declared invocation, and resolving-from-declaration is the seam to close next (the #24 arc). Bridge must NOT add a transport-named-by-peer kind under any path.

**Horizon (named, not built):** the end-state is dispatch resolving `capability → implementation → invocation mechanism` entirely from the registry/declaration, so Bridge never hardcodes a transport. #104 stays minimal; Path A takes the first real step toward it, Path B at minimum must not foreclose it.

### Q-C — Executor invariant (CONSTRAINT, not a question): `executor.py` byte-stable.

DT's banked doctrine: *"executor interprets nothing; control-flow + topology + authority + capture all ride in dispatch/boundaries; `executor.py` byte-untouched since #87 across the WHOLE M2 arc."* The new kind lands in **`admission.py`** (one record + widen the Literal), **`dispatch.py`** (one `UnifiedDispatch` field + one routing branch), and a **new `pipeline_boundary.py`**. The executor routes generically via `dispatch.dispatch(node, resolved_inputs)` — untouched. **The issue lists `executor.py` as "likely involved" — that's the one correction to send back to Pipeline: it must NOT be.** Verify byte-stability post-build (a tested invariant, same as every M2 slice).

### Q-D — NodeResult / packet-identity shape: **preserve the banked Pipeline-proof shape.**

The proof returns full operation data as `NodeResult.output`, with the receipt packet at `output["step_plan_result"]`, plus `final_state`/`steps`/`deltas`. The issue allows preserve-or-deliberately-change (Pipeline will mirror a change). **Position: preserve** — captured-not-assembled ([[feedback_captured_not_assembled]]); match what the banked proof already produces, don't redesign the contract mid-admission. Mapping:
- Pipeline success → `NodeResult(status="ok", output=<full op data dict>, artifact_type="traffik.editorial_step_plan_result")` (preserves packet identity; `artifact_type` advisory in M1).
- Pipeline partial → `status="partial"`, `fidelity=...`.
- Pipeline failure → `status="error"`, `reason_code=<Pipeline error_code or stable fallback>`, `message=<Pipeline error>`, `output=None`.
- Lineage → `source_artifact_ids` from upstream `NodeResult.artifact_id` (the established pattern).
- Any future "output the result packet directly, store full data elsewhere" is a **deliberate, documented** contract change Pipeline mirrors — out of scope here.

### Q-E — Dependency injection: **injected Pipeline client; zero Traffik import in Bridge.**

`PipelineOperationBoundary.__init__(*, pipeline_client=None, run_id=None, artifact_id_factory=uuid4)` — same shape as `MCPToolBoundary(*, mcp=...)`. Bridge composition imports **no** Pipeline/Traffik code; the boundary holds an injected callable with a narrow signature `(operation_type, state, step_plan, **metadata) -> result`. Tests inject a fake client. The **real** client is wired at the daemon / `UnifiedDispatch` construction edge (where the env has Pipeline installed), never in composition modules. Satisfies "no Traffik graph-runtime import" + "acceptable deps = injected callable/client."

### Input resolution + failure discipline (mechanical, follows precedent)
- `step_plan` from `resolved_inputs["step_plan"].output` (edge, preferred) **or** `node.config["arguments"]["step_plan"]` (single-node) — the `CommitBoundary` held dual-source pattern.
- `state` from `node.config["arguments"]["state"]`; optional `bridge_asset_ids`/`idempotency_key`/`project_id`/`requested_by` from `node.config["arguments"]`; optional receipt path from `node.config["receipt_path"]`.
- **Missing/invalid `state` or `step_plan` → a deterministic error `NodeResult` (status="error", reason_code), never raise through `GraphExecutor`** (acceptance criterion).
- Input port `{"step_plan": PortContract.manifest_gate()}`, output `PortTopology.manifest()`.

---

## 3. The decisions the room must settle — in order

1. **§0.5 invariant (PRIMARY, operator-locked):** one GraphSpec, freely-mixed operators; federation = implementation boundary. Not up for debate — it's the north star. Everything below serves it.
2. **Q-B invocation resolution (the live crux):** does the `editorial` capability declaration carry an invocation-mechanism contract dispatch can resolve (Path A — #104 becomes the first capability invoked-from-declaration), or only the hardcoded `dispatch_kind` enum today (Path B — admit with current mechanism, record the gap)? Either way the graph stays oblivious to transport; no peer-named kind. DT resolves against the capability declaration + sibling-attach path.
3. **Q-A state-authority (clean under §0.5):** the *State authority* axis. `apply_steps` mutates Pipeline's own state → Pipeline enforces → Bridge does not ratify (never route through `commit`). If `apply_steps` were routed through `commit`, Bridge would demand an `AssentRecord` for state it has no authority over; if a *future* delta→Flame step were routed *without* `commit`, Bridge would apply host mutations unratified. Draw the line now.
4. **Q-C executor invariant:** confirm a new route (whichever outcome) is absorbable without touching `executor.py`.

## 4. Non-goals (binding — from the issue + carried)
- Do not make Traffik part of the Bridge graph runtime; no Traffik/Flame/DCC/conform-internal imports in Bridge composition.
- Do not add more Traffik editorial atoms in Bridge.
- Do not solve delta→Flame application or 2-pop/reference-picture conform sync here.
- `executor.py` byte-stable; `forge_bridge.__all__` stays 19; new package work carries its own surface.

## 5. Pass-to-code shape (after convergence)
Files: `admission.py` (one record + widen `DispatchKind`) · `dispatch.py` (one field + one branch) · **new `composition/pipeline_boundary.py`** (`PipelineOperationBoundary`) · `tests/composition/` (admission · boundary-with-fake-client · real `GraphExecutor`+`UnifiedDispatch` integration · failure-maps-to-error-NodeResult · executor-byte-stable assertion). Mirror the issue's unit + graph-integration + (Pipeline-side) cross-repo acceptance test plan. Cross-reference #86 (two-axis `no_state_mutation`) and reply on #104 with the executor-stability correction + the authority position so Pipeline knows Bridge will *not* ratify-gate `apply_steps`.

## 6. First moves for DT (fresh context)
1. Read **§0.5 first** (the invariant), then §1 (don't re-ground) + the issue's "Required Bridge work" + the Pipeline proof fixture `forge_core/traffik/tests/test_editing_federation.py::test_bridge_graph_executor_composes_editorial_packet_nodes`.
2. **Resolve Q-B (the crux):** does the `editorial` **capability declaration** carry an invocation-mechanism contract dispatch can resolve (Path A — invoked-from-declaration), or does Bridge only have the hardcoded `dispatch_kind` enum today (Path B — admit with current mechanism + record the gap)? Ground the *declaration* shape (`forge_core.bridge.contract_registry.iter_capability_declarations(["editorial"])` / `forge_core.traffik.editorial_packets`) AND Bridge's resolution side (`admission.py` + the `forge_bridge.siblings` / `orchestration/discovery.py` attach path — how does roto's invocation get resolved today?). The graph must stay oblivious to transport under either path; never a peer-named kind.
3. Pressure-test **Q-A** — any reading where Bridge IS the authority over the editorial mutation? (What does `TimelineDelta` mutate; is the receipt Pipeline-owned?) Confirm `apply_steps` must not route through `commit`.
4. Confirm **Q-C** — the chosen route is absorbable without touching `executor.py`.
5. Sanity-check **Q-D** — exact proof output shape against `forge_core/traffik/editorial_packets.py`.
6. Redline → Creative (does the chosen transport shape scale to the §0.5 five-peer graph?) → converge → pass-to-code. Then reply on #104 with the transport decision + the `executor.py` correction + the authority position.
