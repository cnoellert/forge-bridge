# #104 — Admit `traffik.editorial.apply_steps` into Bridge graph dispatch — Orch Framing

**Date:** 2026-06-22 · **Status:** CONVERGED (Orch framing + operator §0.5 invariant + Creative four-concern split + DT code-grounded crux resolution; Q-A–Q-E settled → pass-to-code in §5).
**Base:** main `1cc3b4c`. **Tracks:** issue **#104** (cross-repo handoff from forge-pipeline PR #13, proof commit `c2685dea`). **Parents:** [[project_passoff_2026_06_22_dt_m2_arc_on_main]] (DT's M2 cursor — load-bearing doctrine) · [[project_federation_implementation_not_composition_boundary]] (the §0.5 invariant) · #92 (the seam note this concretizes) · [[project_federation_facts_judgment_spine]] · [[project_roadmap_finish_m2_then_first_graph_vertical_66]].
**Why now:** first **real federation peer** composing GraphSpecs against Bridge's executor — the real-consumer substrate pressure the roadmap calls for, and the **pattern-setter for #66**.

**CONVERGENCE SUMMARY:** §0.5 invariant locked (graph composes capabilities, not transports — four orthogonal concerns). **Crux (Q-B) resolved by DT against code: Outcome A is CLOSED** (Pipeline attaches zero MCP tools; `apply_steps` is a `forge_core` `PipelineOperator`, not an MCP tool; the MCP shim would discard receipt/idempotency/packet identity). **Answer = a new `dispatch_kind="operation"`** routing the **forge_core operation-dispatch** mechanism — which is **already multi-peer in production** (Blender/render/probe route through the same `forge_core.operations.dispatch`), so this is a clean *second federation transport*, not a Pipeline lane. Q-A/Q-C/Q-D/Q-E confirmed against the proof. #104 collapses to: one admission row + one `UnifiedDispatch` field/branch + `composition/operation_boundary.py` (injected dispatch callable) + tests; `executor.py` byte-stable.

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

**Position (DT-confirmed against code):** route through the **new non-commit `operation` boundary that mints a `NodeResult` but never touches `AssentRecord`.** Structurally clean — only `commit` ever sees assent (`dispatch.py:47-52`), so a non-commit kind *cannot* accidentally acquire a ratify gate. DT evidence: `apply_steps` mints a Pipeline-owned receipt (`forge_core.operations.receipts`) under its own `idempotency_key`, mutates Pipeline editorial state, returns `TimelineDelta` for later host application (out of scope).

**This sharpens #86's unresolved `no_state_mutation` semantics — a genuine contribution back:** the flag conflates two orthogonal axes. (1) *Does it change state?* (`no_state_mutation`) and (2) *Whose authority gates the change?* `apply_steps` is `no_state_mutation=False` (axis 1: yes) AND peer-authority (axis 2: Pipeline's receipt/idempotency, no Bridge ratify). Bridge ratify-gates **only Bridge-host** mutations. Recommend recording this two-axis split on #86.

**Forward-pointer (draw the line now to prevent a future mistake):** when the `TimelineDelta → Flame` application eventually lands (future work, not #104), *that* step IS Bridge-host mutation territory and WOULD need `commit`/ratify. The authority boundary is: **`apply_steps` (peer editorial mutation) = peer-owned, no ratify; future delta→Flame application = Bridge-host, ratified.** Don't let anyone route the Flame application without a ratify gate later.

### Q-B — Invocation resolution: **new `dispatch_kind="operation"` (the forge_core operation-dispatch transport). RESOLVED by DT against code.** [CONVERGED]

> Superseded drafts: (1) `dispatch_kind="pipeline"` + `PipelineOperationBoundary` — the silo error; (2) "admit over the MCP transport" — transport-first and, per DT, factually closed. Corrected: the graph composes capabilities; the **invocation mechanism lives in the admission/resolution layer, never in the `GraphSpec`.**

**Outcome A (MCP) is CLOSED — DT, three decisive facts against `origin/codex/traffik-editorial-conform` @ `c2685dea`:**
1. **Pipeline attaches zero MCP tools.** Its `forge_bridge.siblings` entry point targets `forge_core.bridge.contract_registry:register_bridge_adapters` (forge-pipeline `pyproject.toml:60`) — the *declaration/planner* path (`register_all_siblings`), never the tool-attach path (`discovery.py:112-176` derives `<pkg>.bridge.registry:register_with`). No `register_with` exists in Pipeline (`git grep "def register_with"` → empty); no `@mcp.tool`/`add_tool`/`call_tool` in any non-test module. So `mcp.call_tool("traffik.editorial.apply_steps", …)` fails closed today.
2. **`apply_steps` is a `PipelineOperator`, not an MCP tool.** It implements `forge_core.operations.protocol:PipelineOperator` (`operation_type` + `async execute(OperationRequest) -> OperationResult`), resolved by `OperatorRegistry.get(operation_type)` and run through `forge_core.operations.dispatch:dispatch(request, registry, receipt_path=…)`. The proof's `bridge_dispatch` (`test_editing_federation.py:1182-1222`) builds an `OperationRequest` and calls *that* dispatch — a typed envelope (`operation_type`, `state`, `step_plan`, idempotency/project metadata, `receipt_path`) → typed `OperationResult`, **not** `mcp.call_tool`.
3. **The MCP shim would discard exactly what Q-D preserves.** `MCPToolBoundary` flattens through `_extract_payload`/`_status_for_payload` (read-result heuristics) — no receipt sink, no `idempotency_key` semantics, no typed-packet identity. "Thin MCP registration" is not just unavailable, it's the **wrong contract.** → **Correction to send Pipeline: do NOT expose it as MCP.**

**Answer = new `dispatch_kind="operation"`** + `OperationDispatchBoundary`, holding an **injected dispatch callable** (+ `OperatorRegistry`) wired at the daemon edge (Q-E: zero `forge_core`/`traffik` import in composition).

**Why this is §0.5-compliant, not a silo (the Creative reconciliation — load-bearing, don't relitigate):** the **`GraphSpec`/`NodeSpec` carries only `operator_id`** — never the transport. The transport lives in the **admission record** (Bridge's resolution layer = concern 2/3), not the graph (concern 1). So composition stays capability-pure; `mcp` and `operation` are *invocation mechanisms in the resolution layer*, not graph categories. In the five-peer graph, Vision's roto routes via `mcp`, Pipeline's editorial via `operation`, and they compose in one `GraphSpec` **because each node is routed by its admission record's transport, not by who implements it.** Transport multiplicity ≠ peer lanes. And `operation` is **already peer-agnostic in production** — `forge_blender` operators, `render_client.publish`, `forge_core.operations.probe:ProbeOperator` all implement `PipelineOperator` through the same dispatch. We're adding a *second federation transport*, not a Pipeline lane. The §0.5 evidence (roto-as-`mcp`) holds verbatim; nothing forks.

**The declaration-gap (the #24 seam, recorded not closed):** today the admission record *hardcodes* the transport — it's a stand-in for capability-declared invocation. The clean end-state resolves `operation` vs `mcp` *from the capability declaration* rather than the admission enum. #104 stays minimal (admission carries it) and does not foreclose that — closing the gap is the #24 "consume capability facts" arc.

**Naming:** `dispatch_kind="operation"` (terse, matches the existing `mcp`/`primitive`/`foreach`/`commit` register and the `OperationRequest`/`PipelineOperator` protocol). Alt `"federated_operation"` if the room wants it explicit — a low-stakes naming call for code.

**Horizon (named, not built):** the end-state is dispatch resolving `capability → implementation → invocation mechanism` entirely from the registry/declaration, so Bridge never hardcodes a transport. #104 stays minimal; Path A takes the first real step toward it, Path B at minimum must not foreclose it.

### Q-C — Executor invariant (CONSTRAINT, not a question): `executor.py` byte-stable.

DT's banked doctrine: *"executor interprets nothing; control-flow + topology + authority + capture all ride in dispatch/boundaries; `executor.py` byte-untouched since #87 across the WHOLE M2 arc."* The new kind lands in **`admission.py`** (one record + widen the Literal), **`dispatch.py`** (one `UnifiedDispatch` field + one routing branch), and a **new `pipeline_boundary.py`**. The executor routes generically via `dispatch.dispatch(node, resolved_inputs)` — untouched. **The issue lists `executor.py` as "likely involved" — that's the one correction to send back to Pipeline: it must NOT be.** Verify byte-stability post-build (a tested invariant, same as every M2 slice).

### Q-D — NodeResult / packet-identity shape: **preserve the banked Pipeline-proof shape.** [DT-confirmed]

Preserve — captured-not-assembled ([[feedback_captured_not_assembled]]). **Build the boundary against the captured proof fixtures (`test_editing_federation.py:866-893` "Bridge-shaped caller" + `:1129-1253` GraphExecutor proof), not a reconstructed dict.** Mapping (DT-verified against the proof):
- Pipeline success → `NodeResult(status="ok", output=<full op data dict>, resolved_class="pipeline.traffik.editorial.apply_steps")` — the proof sets exactly this `resolved_class` (matches the admission record's `resolved_class`); receipt packet at `output["step_plan_result"]`, plus `final_state`/`steps`/`deltas`.
- Pipeline partial → `status="partial"`, `fidelity=...`.
- Pipeline failure → `status="error"`, `reason_code=<Pipeline error_code or stable fallback>`, `message=<Pipeline error>`, `output=None`.
- Lineage → `source_artifact_ids` from upstream `NodeResult.artifact_id` (the established pattern).
- Any future "output the result packet directly" is a **deliberate, documented** contract change Pipeline mirrors — out of scope.

### Q-E — Dependency injection: **injected operation-dispatch callable; zero forge_core/Traffik import in Bridge.** [confirmed]

`OperationDispatchBoundary.__init__(*, run_operation=None, run_id=None, artifact_id_factory=uuid4)` — same shape as `MCPToolBoundary(*, mcp=...)`. The injected `run_operation` callable encapsulates request-building + `OperatorRegistry` + `forge_core.operations.dispatch` behind a narrow signature `async (operation_type: str, *, state, step_plan, receipt_path=None, **metadata) -> OperationResult-shaped`. Composition imports **no** `forge_core`/`traffik` code; the registry + real dispatch live inside the injected callable's closure, **wired at the daemon / `UnifiedDispatch` construction edge** (where Pipeline is installed). Tests inject a fake `run_operation`. (DT phrased this as "dispatch-callable + `OperatorRegistry`"; collapsing both behind one injected `run_operation` keeps composition fully import-free — a small refinement for code to confirm.)

### Input resolution + failure discipline (mechanical, follows precedent)
- `step_plan` from `resolved_inputs["step_plan"].output` (edge, preferred) **or** `node.config["arguments"]["step_plan"]` (single-node) — the `CommitBoundary` held dual-source pattern.
- `state` from `node.config["arguments"]["state"]`; optional `bridge_asset_ids`/`idempotency_key`/`project_id`/`requested_by` from `node.config["arguments"]`; optional receipt path from `node.config["receipt_path"]`.
- **Missing/invalid `state` or `step_plan` → a deterministic error `NodeResult` (status="error", reason_code), never raise through `GraphExecutor`** (acceptance criterion).
- Input port `{"step_plan": PortContract.manifest_gate()}`, output `PortTopology.manifest()`.

---

## 3. Decisions — SETTLED
1. **§0.5 invariant** — one GraphSpec, freely-mixed operators; federation = implementation boundary; four orthogonal concerns. Locked.
2. **Q-B** — new `dispatch_kind="operation"` (forge_core operation-dispatch transport; Outcome A/MCP closed). DT-resolved.
3. **Q-A** — `operation` is non-commit; `apply_steps` never gets `assent_record`; Bridge does not ratify a peer's state mutation. Confirmed.
4. **Q-C** — `executor.py` byte-stable; the new route is one Literal widening + one field + one branch + one boundary module. Confirmed by the proof (`GraphExecutor(bridge_dispatch).run(graph)`, `test_editing_federation.py:1253` — real executor, only the dispatch callable swapped).
5. **Q-D/Q-E** — preserve proof shape (build against captured fixtures); inject `run_operation`, zero forge_core import in composition.

## 4. Non-goals (binding)
- Do not make Traffik part of the Bridge graph runtime; no `forge_core`/`traffik`/Flame/DCC import in Bridge composition (injected `run_operation` only).
- Do not add more Traffik editorial atoms; do not solve delta→Flame application or 2-pop/reference conform sync here.
- `executor.py` byte-stable; `forge_bridge.__all__` stays 19.
- Do **not** route `operation` through `commit`/assent. Do **not** name a dispatch kind for a peer.

## 5. Pass-to-code brief (CONVERGED — ready)

**Scope:** one admission row + one `UnifiedDispatch` field/branch + one new boundary module + tests. `executor.py` untouched.

1. **`admission.py`** — widen `DispatchKind` Literal to include `"operation"`; add:
   ```python
   AdmissionRecord(
       operator_id="traffik.editorial.apply_steps",
       resolved_class="pipeline.traffik.editorial.apply_steps",  # matches the proof's NodeResult.resolved_class
       dispatch_kind="operation",
       synchronous=True,
       returns_reference=False,
       no_state_mutation=False,   # mutates Pipeline editorial state
       idempotent_result=False,   # carries idempotency_key, but the result mutates target state
   )
   ```
2. **`dispatch.py`** — add `operation_boundary: OperationDispatchBoundary = field(default_factory=OperationDispatchBoundary)` + a routing branch `elif record.dispatch_kind == "operation": return await self.operation_boundary.dispatch(node, resolved_inputs)`. **No `assent_record` passed** (structurally enforces Q-A).
3. **new `composition/operation_boundary.py`** — `OperationDispatchBoundary`:
   - `__init__(*, run_operation=None, run_id=None, artifact_id_factory=uuid4)` (Q-E).
   - `async def dispatch(self, node, resolved_inputs) -> NodeResult`: `admit_operator(node.operator_id)` (assert `dispatch_kind=="operation"`); resolve `step_plan` from `resolved_inputs["step_plan"].output` **or** `node.config["arguments"]["step_plan"]` (CommitBoundary dual-source); `state` from `node.config["arguments"]["state"]`; optional `bridge_asset_ids`/`idempotency_key`/`project_id`/`requested_by` from `config["arguments"]`, `receipt_path` from `config["receipt_path"]`; call injected `run_operation(...)`; map per Q-D; `source_artifact_ids` from upstream `.artifact_id`; **missing/invalid `state`/`step_plan` → deterministic error `NodeResult`, never raise.** Input port `{"step_plan": PortContract.manifest_gate()}`, output `PortTopology.manifest()`.
4. **`tests/composition/`** — admission (record fields + unknown-traffik-op fails closed) · boundary with fake `run_operation` (edge step_plan → correct call; success→ok w/ packet identity + `resolved_class`; lineage copied; failure→error w/ reason_code/message/no output; missing input→deterministic error, not raise) · real `GraphExecutor`+`UnifiedDispatch` integration routing the `operation` node (fake `run_operation`) — the proof through *real* dispatch, no test-local shim · **`executor.py` byte-stable assertion**. Build against captured fixtures (`test_editing_federation.py:866-893`, `:1129-1253`).
5. **Verify:** `__all__`==19, ruff clean, composition suite green, `git diff` shows `executor.py` empty.

## 6. Reply to #104 (for the operator to send — cross-repo handoff)
- **Decision:** Bridge admits `apply_steps` as a **new `dispatch_kind="operation"`** (the forge_core operation-dispatch transport), via `OperationDispatchBoundary` holding an injected `run_operation` callable. It composes in any GraphSpec beside `mcp` operators (roto) — routed by admission transport, not by peer.
- **Correction 1:** **do NOT expose `apply_steps` as an MCP tool / add a `register_with(mcp)` wrapper** — `MCPToolBoundary` would discard the receipt sink, `idempotency_key`, and typed-packet identity. The `operation` transport is the right contract.
- **Correction 2:** the issue lists `executor.py` as "likely involved" — **it must NOT be**; the new route is absorbed in admission/dispatch + a boundary.
- **Authority:** Bridge will **not** ratify `apply_steps` (peer-owned editorial mutation + Pipeline receipt/idempotency; never routes through `commit`). **Forward-pointer:** a future `TimelineDelta → Flame` application IS Bridge-host territory and *would* need `commit`/ratify — keep that boundary.
- **Contract:** Bridge mirrors the proof's `NodeResult` (`resolved_class="pipeline.traffik.editorial.apply_steps"`, `output`=full op data w/ `step_plan_result`). If Pipeline changes that shape, tell us.
- **Acceptance:** after Bridge lands, Pipeline removes the test-local adapter and runs real `UnifiedDispatch`.
- **Note for #86:** `no_state_mutation` = *does it change state* (descriptive), orthogonal to *whose authority gates it* (peer vs Bridge-host) — the two-axis split.
