# ① `TimelineDelta → Flame` host application — Orch Framing

**Date:** 2026-06-23 · **Status:** CONVERGED (3-view grounded convergence + operator seam-lock + DT 3-correction grounding + forge-pipeline#14 resolved + tool-surface reconciled). Design locked; **zero code yet.**
**Base:** main `b945815` (tag `v1.7.0`). **Tracks:** **forge-pipeline#14** (cross-repo, https://github.com/cnoellert/forge-pipeline/issues/14) — successor to the #104 forward-pointer (closed `PIPELINE-104-TRAFFIK-EDITORIAL-ADMISSION-FRAMING.md` §2 Q-A).
**Parents:** [[live-head-2026-06-22-dt-run-graph-first-production-caller]] (LIVE head — unchanged by this) · [[project_federation_implementation_not_composition_boundary]] · [[project_federation_facts_judgment_spine]] · [[feedback_adapter_translates_never_synthesizes]] · [[project_roadmap_finish_m2_then_first_graph_vertical_66]].

---

## 0. What ① is (one paragraph)

`traffik.editorial.apply_steps` (the `operation` transport, live since v1.7.0) mutates *Pipeline's own* editorial state and returns host-applicable `TimelineDelta` payloads in `NodeResult.output["deltas"]`. ① is the path that **applies those deltas to Flame under Bridge-host authority** — `commit`/ratify, **not** the operation route. This is the #104 forward-pointer made real: *a peer mutating its own state = operation/no-ratify; a peer's proposal becoming a mutation of a Bridge-governed HOST (Flame) = commit/ratify.*

**Authority frame (host-agnostic): peers propose, Bridge translates, hosts commit.** `TimelineDelta` is a proposal → `MutationManifest` is **still** a proposal → `CommitBoundary` is the single point where a proposal becomes a host mutation. **Bridge ratifies host MUTATIONS, not peer PROPOSALS.** The pattern generalizes past Flame to Houdini/Blender/Nuke/Resolve.

---

## 0.5 Locked principles (operator-articulated — the architectural win)

1. **Peers propose, Bridge translates, hosts commit.** Pipeline is no longer framed as "executing editorial against Flame." It authors an editorial *proposal*; Bridge does a representation transform; the host mutates under its own authority.
2. **Exactly one canonical author of every representation.** Two independent authors of the same semantic object always drift. The adapter must NOT hand-author the `MutationManifest`; the Flame executor's discover pass is the canonical author.
3. **Representation transforms are first-class graph nodes**, not hidden glue. `delta_to_manifest` is the same species as caption→prompt, OCR→tokens, segmentation→matte-request — visible, typed, replayable, lineage-bearing.

---

## 1. Grounded surface (file:line, verified 2026-06-23)

**Bridge:**
- `forge_bridge/composition/commit_boundary.py` — `CommitBoundary`: reads `held.apply_counterpart["tool"]` (`:71`), fails closed `APPLY_COUNTERPART_NOT_DECLARED` if the tool isn't registered (`:74-79`), calls the tool `mode="verify"` (`:81-86`) → `MutationManifest.from_dict` (`:88`) → `CommitNode().verify(held, fresh, assent=assent_record)` (`:97`) → on drift `PLAN_STATE_DRIFT` (`:104-111`), unratified → `ASSENT_INVALID` (`:112-117`), else `mode="apply"` exactly once (`:119-124`). Assent is a **call-time arg**, never in executor/`NodeResult`.
- `_default_mcp()` → `forge_bridge.mcp.server.mcp` (`:180-183`). **That server registers NO tools directly** — only sibling-registered (`mcp/server.py:550,562` `register_sibling_mcp_tools`/`register_sibling_in_process_tools`). **⇒ the production apply surface is forge-core's sibling executors, NOT Bridge `timeline.py`.**
- `forge_bridge/graph/mutation.py` — `MutationManifest{type:"mutation_plan", intent_parameters, resolved_plan: tuple[ChangeRecord{identity,payload}], originating_capability, apply_counterpart:{tool, parameter_overrides}}`. Single-tool-homogeneous by construction.
- `forge_bridge/orchestration/run_graph.py` — only prod graph caller; deliberately **never threads assent** (`:25-37`) → commit fails closed through it. ①'s entrypoint is a sibling that DOES thread assent (the narrow gate-crossing).
- `forge_bridge/composition/dispatch.py` — `UnifiedDispatch`: only `commit` receives `assent_record`; `assent_record` is a single field (the fan would need a `node_id→AssentRecord` map — deferred to slice 2).
- `forge_bridge/composition/admission.py` — `DispatchKind` Literal + `AdmissionRecord`; `delta_to_manifest` admits as `dispatch_kind="primitive"`, `no_state_mutation=True`.
- `forge_bridge/composition/operation_boundary.py` — operation node emits `output_topology={"kind":"manifest"}`, `output` carries `apply_steps` data incl. `deltas`.
- Flame identity space: `track_idx, record_in, seg_name, source_name, sequence_name` (`tools/timeline.py:381-390`).

**Pipeline (forge-pipeline main, `forge_core/`):**
- `traffik/editing/models.py` — `TimelineDelta.entries: list[DeltaEntry]` (`:620`); `DeltaEntry{action, object_type, object_id, before, after, metadata}` (`:583-601`). Object types: `segment/track/bin/edit_session`. Host-neutral by construction.
- `traffik/editing/delta_adapter.py` — `InMemoryTimelineDeltaAdapter`, docstring "**Fake** delta adapter proving host-facing TimelineDelta consumption." One producer + one fake consumer ⇒ below the forge-contracts earned-by-use bar.
- `traffik/execution.py:90` — `apply_steps` → `OperationResult.data["deltas"] = [TimelineDelta.to_dict(), …]` (chain aggregates one delta per step; per-step `EditResult.delta` singular). **The `delta_to_manifest` input contract.**
- Protocol executors present: `forge_apply_rename`/`forge_apply_publish` in `forge_flame.tools.executors` via `forge_core.session.shell_command_server`. **No segment-level executor exists** (Pipeline confirmed on #14).

---

## 2. Decisions Q1–Q5 (leans; full reasoning in [[timelinedelta-to-flame-convergence]])

- **Q1 — Bridge owns `apply_counterpart`; never peer-populated.** The delta is host-neutral; the Flame executor's discover pass emits `apply_counterpart` itself. The peer authors the *proposal*; it must not name Flame tools.
- **Q2 — Fan.** One delta → N manifests → N commit nodes when heterogeneous. **Pipeline confirmed real deltas ARE heterogeneous** (#14 ask 4) → fan is required design for slice 2. Per-commit-node assent (one assent must not authorize N distinct host mutations; apply is eager+exactly-once → partial-apply hazard). Slice 1 sidesteps this with a homogeneous synthetic delta (one commit, one assent).
- **Q3 — New admitted `delta_to_manifest` node, topology `operation(apply_steps) → delta_to_manifest → commit`.** Room-corrected: it is **NOT a primitive** (primitives are pure value-transforms; this does host discover I/O) — it is a **dedicated boundary** (`dispatch_kind="host_resolve"`, `HostResolveBoundary`, injects `run_discover`). REJECTED: a 4-node `primitive → mcp(discover)` shape (needs MCPToolBoundary to accept edge-fed kwargs, which it refuses by documented contract — wrong thing to touch on the parity path); widening `CommitBoundary._held_manifest`; the `run_graph` construction edge. **Structural seam — one-way door once #66 ships persisted specs naming the node.**
- **Q4 — verify/fresh = the Flame executor's discover pass recomputes from LIVE Flame at commit time.** `DeltaEntry.before` is informational ONLY (it's Pipeline's stale snapshot; trusting it would let a stale view authorize a Flame mutation). Reuse `CommitNode.verify` unchanged.
- **Q5 — Bridge-private, firmly.** Nothing enters forge-contracts (v0.6, vocabulary-not-behavior, earned-by-use; `MutationManifest` correctly never promoted). `TimelineDelta` stays Pipeline-owned; Bridge imports `forge_core.traffik.editing.models` only at the daemon edge. Revisit promotion only on a 2nd independent (non-fake) consumer.

---

## 3. The (a)/(b) sub-seam — LOCKED (b)

The `delta_to_manifest` node **lowers the delta into the Flame executor's discover-mode INPUT and lets the executor's discover pass ORIGINATE the canonical `MutationManifest`** — the adapter authors the *request*, the executor authors the *manifest*.

```
TimelineDelta → construct discover request → call Flame discover → MutationManifest
   (adapter authors the request)              (executor authors the manifest)
```

Decisive rationale (stronger than "avoid hand-authoring `resolved_plan`"): the discover pass is the one place that owns the Flame identity space (`timeline.py:381-390`). Letting it originate the manifest co-locates identity reconciliation where the identity knowledge already lives. Option (a) would force the adapter to re-implement identity logic to build Flame-canonical `ChangeRecord`s — brittle, and it's *synthesis* (the line we hold).

**Coupling: (b) ⊃ identity-reconciliation.** To lower a delta into discover input, the adapter needs enough identity for discover to find the segment in live Flame. So the metadata enrichment is (b)'s hard prerequisite — they land together. This is exactly forge-core's new segment executor's discover pass consuming Pipeline's enriched `DeltaEntry.metadata`.

**Coherence catch (DT, load-bearing): `run_discover` must call the SAME apply tool's discover mode that `CommitBoundary` calls in verify mode** (`commit_boundary.py:84-85`). `held` (discover@host_resolve) and `fresh` (verify@commit) are only comparable if produced by the same tool. So `run_discover` is *not* a generic executor discover — it is "the resolved apply tool's discover mode," and `tool_name` carries it. The node resolves `(action, object_type) → apply_tool` (the irreducible Bridge-host binding, convergence-Q1) **before** building the discover request, since `run_discover` needs `tool_name`.

---

## 4. Prerequisites (3 stacked) + forge-pipeline#14 resolution

1. **Protocol-compliant segment executor.** No segment-level executor speaks discover/verify/apply + `mutation_plan` today (Bridge `timeline.py`'s protocol tools — `rename_shots`/`create_reel`/`create_reel_group`/`create_library` — are NOT the production apply surface; that's forge-core's sibling executors). **#14 resolution: Pipeline adds one.**
2. **Identity reconciliation (THE gate).** delta `object_id` ≠ Flame identity key space. **#14 resolution: Pipeline populates the EXISTING `DeltaEntry.metadata` with the Flame identity envelope** (`track_idx/record_in/seg_name/source_name/sequence_name` + keep `step_id`/`node_id`) — a populate-field ask, tested as a first-class contract. Coupled with #1 as one Pipeline slice.
3. **Action vocabulary.** Emitted: `inserted/removed/updated/shifted`; **`moved` NOT emitted** (`move_segment`→`shifted`). **#14 resolution: Pipeline freezes a versioned vocab, `moved` reserved.** Bridge lowers only the four.

**Synthetic-specimen honesty:** the demo `_bridge_authored_steps` chain is insert/split/trim (no Flame apply tool), and #4 confirms real deltas are heterogeneous. So **no real `apply_steps` output is end-to-end ratifiable today.** Slice 1 proves the machinery against a hand-authored homogeneous `updated` delta (as #104's example was explicitly not the canonical demo). A real end-to-end demo waits on Pipeline's coupled slice.

---

## 5. Slice plan

**Slice 1 — Bridge-alone machinery (Pipeline-independent, proceed NOW). ROOM-CONVERGED 2026-06-23 (Orch draft + Creative + DT):**
- **`delta_to_manifest` node via a dedicated `HostResolveBoundary`** (`dispatch_kind="host_resolve"`, `no_state_mutation=True`, injects `run_discover`). Consumes operation `output["deltas"]`; **narrowed to exactly `(action="updated", object_type="segment")`** (reject any other class loudly — homogeneity is structural, not behavioral, until a real executor exists). Sequence: homogeneity check → resolve `(action,object_type)→apply_tool` → build discover request `{identity from metadata, intent from after}` (`before` unused) → call `run_discover(tool_name, *, request) -> manifest_dict` → emit the executor-authored `MutationManifest` on a `manifest` output port.
- **Error taxonomy (all deterministic NodeResult, never raise; all distinct):** `HETEROGENEOUS_DELTA` (mixed class → slice 2 fan) · `UNSUPPORTED_DELTA_ACTION` (no map entry — Blocker 3 scope wall; insert/split/trim/move land here) · `UNRESOLVED_TARGET` (discover signalled the #16 discriminator `identity_unresolved` — stale Pipeline identity, *before* compare) · `HOST_DISCOVER_FAILED` (any OTHER discover failure — preserves the #16 split; also returned when the discover manifest's `apply_counterpart.tool` ≠ the resolved `apply_tool`, enforcing the Bridge-host binding map). Distinct from commit-time `PLAN_STATE_DRIFT` (Flame moved between discover and apply) and `ASSENT_INVALID`. Discriminator read from both top-level `code`/`error_code`/`reason_code` and nested `error.{…}` (matches #16's shape).
- **`run_discover` calls the SAME apply tool's discover mode** that `CommitBoundary` calls in verify mode (held↔fresh comparability — DT catch #1). Contextual deps (project_id/run context) inject at boundary **construction** time (like the operation runner takes `data_root`/`registry`), keeping the per-call signature stable while the `request` payload stays provisional/fake-driven until forge-core's executor discover input is captured.
- **The ①-entrypoint: a DISTINCT named assent-requiring sibling of `run_graph`** — NOT `run_graph(assent_record=…)`. `run_graph` stays structurally no-assent (greppable, auditable commit-fail-closed). Two surfaces: `run_graph` (no assent, read/operation) + the ①-entrypoint (assent-required, can apply). This is the first production assent-threading caller; single `assent_record` field suffices (one commit node).
- **Tests against a fake `run_discover` that names a REAL protocol tool (`rename_shots`)** so the `APPLY_COUNTERPART_NOT_DECLARED` registry guard is genuinely exercised and the fake mcp's verify returns a valid `MutationManifest` (DT catch #3).
- Invariants: `executor.py` byte-stable; `forge_bridge.__all__` stays 19; assent only at the commit node; no `forge_core`/`traffik`/Flame import in `composition/`.
- **Honest caveat (DT):** slice-1-green ≠ "deltas apply to Flame." No protocol-compliant segment-update apply tool is confirmed to exist (Blocker 1); the real Flame apply is downstream-blocked on forge-core's executor. Slice 1 proves the *mechanism*, not an end-to-end Flame mutation.

**Slice 2 — the fan (gated on Pipeline's coupled slice + real heterogeneous deltas):**
- Partition delta entries by `(action, object_type)` → apply-tool class → N `delta_to_manifest`→`commit` chains.
- Per-commit-node assent: `UnifiedDispatch` grows a `node_id→AssentRecord` map (the one dispatch-spine touch; additive, executor untouched).
- Partial-apply policy (node 1 applied eager, node 2 drift-aborts): ordered commits + drift-abort, NOT a multi-tool manifest. Refuse heterogeneous coalescing into a single assent.

---

## 6. Non-goals / constraints (binding)

- `executor.py` byte-stable; `forge_bridge.__all__` == 19; no new external libs.
- The `operation` route never acquires assent; the delta must never name a Flame tool.
- No `forge_core`/`traffik`/Flame import in `composition/` (daemon-edge injection only, as `run_graph`/`operation_boundary` already do).
- Do NOT widen `CommitBoundary` to understand deltas; do NOT translate at the `run_graph` construction edge.
- Nothing promoted to `forge-contracts`.

---

## 7. Pass-to-code brief — Slice 1 (ROOM-CONVERGED, ready to plan)

1. **`admission.py`** — widen `DispatchKind` Literal with `"host_resolve"`; add `AdmissionRecord(operator_id="delta_to_manifest", resolved_class="host.resolve.delta_to_manifest" (provisional), dispatch_kind="host_resolve", synchronous=True, returns_reference=False, no_state_mutation=True, idempotent_result=False)`.
2. **`dispatch.py`** — add `host_resolve_boundary: HostResolveBoundary = field(default_factory=HostResolveBoundary)` + a routing branch `elif record.dispatch_kind == "host_resolve": return await self.host_resolve_boundary.dispatch(node, resolved_inputs)`. **No `assent_record` passed** (only `commit` ever sees assent).
3. **new `composition/host_resolve_boundary.py`** — `HostResolveBoundary.__init__(*, run_discover=None, run_id=None, artifact_id_factory=uuid4, **context_deps)` (inject `run_discover` + any construction-time context; composition stays `forge_core`/`traffik`-import-free). `async def dispatch(node, resolved_inputs)`:
   - read `deltas` from upstream `operation` `NodeResult.output["deltas"]`;
   - **homogeneity gate** — all entries share one `(action, object_type)`, else `HETEROGENEOUS_DELTA` error NodeResult; **slice-1 admits ONLY `(action="updated", object_type="segment")`**;
   - **resolve `(action, object_type) → apply_tool`** (the Bridge-host binding map); unmapped → `UNSUPPORTED_DELTA_ACTION`;
   - build the discover `request` = `{identity: <from each entry's metadata>, intent: <from each entry's after>}` (`before` unused); batch the homogeneous entries into one request;
   - call `run_discover(apply_tool, request=request) -> manifest_dict`; if discover cannot resolve the live host target → `UNRESOLVED_TARGET`;
   - emit the executor-authored `MutationManifest` on a `manifest` output port; `source_artifact_ids` from upstream `.artifact_id`; **never raise through the executor.**
4. **the ①-entrypoint** — a NEW named sibling of `run_graph` (e.g. `apply_editorial_delta(spec, *, assent_record, registry=None, …)`), **not** an `assent_record` param on `run_graph`. Builds `UnifiedDispatch(operation_boundary=…, host_resolve_boundary=HostResolveBoundary(run_discover=…), commit_boundary=…, assent_record=<operator's ratified AssentRecord>)` and runs the `operation→delta_to_manifest→commit` spec. Fail-closed when assent absent (commit emits `ASSENT_INVALID`). `run_graph` stays no-assent (greppable guarantee preserved).
5. **tests/composition/** — admission row (fields; unknown op fails closed); `HostResolveBoundary` with a fake `run_discover` that **names a real protocol tool (`rename_shots`)** and a fake mcp whose verify returns a valid `MutationManifest`: homogeneous `(updated,segment)` → correct discover `request` `{identity,intent}` → manifest forwarded, `before` ignored, lineage copied; heterogeneous → `HETEROGENEOUS_DELTA` not raise; unmapped action → `UNSUPPORTED_DELTA_ACTION`; discover-unresolved → `UNRESOLVED_TARGET`; real `GraphExecutor`+`UnifiedDispatch` over the 3-node spec + ratified assent → `commit_applied`; unratified → `ASSENT_INVALID`; drift → `PLAN_STATE_DRIFT`; **`executor.py` byte-stable assertion**. (DT to draft the failing held↔fresh-same-tool test once the boundary lands.)
6. **Verify:** `__all__`==19, ruff clean, composition suite green, `git diff` shows `executor.py` empty.

**Naming residual:** `dispatch_kind="host_resolve"` (Orch+DT lean) vs `"host_translate"` (Creative) — one-word operator call, settle at code.

---

## 8. Cross-repo status

- **forge-pipeline#14** — filed + resolved (2026-06-23). Pipeline committed to one coupled slice: segment `DeltaEntry.metadata` Flame-identity enrichment + a protocol-compliant segment executor + frozen/versioned action vocab. Bridge owns translation/commit; `TimelineDelta` stays Pipeline-owned and host-neutral.
- **Division of labor:** Bridge slice 1 (machinery, fake executor) and Pipeline's coupled slice proceed in parallel. Real end-to-end demo = Bridge slice 1 wired to forge-core's real segment executor + enriched metadata.

---

## 9. Real-wiring (Phase B) — Orch framing (2026-06-23)

**Status:** slice 1 MERGED to Bridge main (machinery proven vs a fake). Pipeline's #14 coupled slice LANDED on `forge-pipeline origin/main`. This section frames wiring slice-1's `host_resolve` to the **real** executor. Grounded against `origin/main` refs (operator's local pipeline checkout is a dirty diverged feature branch — NOT pulled; read via `git show origin/main:…`).

**What landed on Pipeline `origin/main`** (grounded, file-exact):
- **`forge_apply_segment_delta`** (`forge_flame/tools/executors.py`) — first protocol-compliant segment executor (discover/verify/apply 3-mode), registered, emits `apply_counterpart.tool="forge_apply_segment_delta"`. Input `ApplySegmentDeltaInput{sequence_name (REQUIRED), entry|entries:[DeltaEntry-shaped dicts], mode, resolved_plan}`. **Narrowed to homogeneous `updated` segment, applied field = `name` ONLY**; unsupported → `SegmentDeltaContractError(code,…)`.
- **`flame_apply.py`** — pure host-neutral classifier `classify_delta_for_flame_apply(delta)` + `flame_delta_apply_classifier_contract()` (exposes `required_segment_identity_fields`); identity issues → `missing_flame_identity` / `invalid_flame_identity`.
- Segment `DeltaEntry.metadata` now carries Flame identity (track_idx/record_in/seg_name/source_name/sequence_name).
- Design contract: `.planning/phases/67-traffik-real-fixture-uat/67-40-STAGE39-HOST-AUTHORIZED-DELTA-APPLICATION-DESIGN.md` (Pipeline) — confirms our graph shape verbatim (step 2 = "host mutation manifest producer", name flexible = our `host_resolve`), and adds preview + receipt + idempotency scope.

**Concrete wiring deltas (slice-1 was built vs a fake — these are the real-shape corrections):**
1. **Wire key `changes`, not `entries` (BUG vs real wire).** `TimelineDelta.to_dict()` on origin/main emits the change-list under **`"changes"`** (`models.py:16`); `from_dict` reads `changes` then `entries` fallback. Bridge `host_resolve._delta_entries` currently reads only `entries` → finds 0 entries on real deltas → false `HETEROGENEOUS_DELTA`. **Fix:** read `delta.get("changes", delta.get("entries", []))`; add a `changes`-keyed fixture (slice-1 fixtures used `entries`).
2. **Real tool name.** `_APPLY_TOOL_BY_DELTA_CLASS[(updated,segment)]` → `"forge_apply_segment_delta"` (slice-1 stand-in was `flame_rename_shots`).
3. **Thin the request — pass DeltaEntry dicts through.** Real executor takes `{sequence_name, entries:[raw DeltaEntry dicts], mode}` and extracts identity/intent ITSELF (it owns the Flame identity space = the (b) principle). **Drop** Bridge's `{identity, intent}` reshape; the adapter gets *thinner*.
4. **Thread `sequence_name`.** Required by the executor; source from the delta's top-level `sequence_id` (present in the wire). host_resolve currently doesn't pass it.
5. **Real `run_discover` = MCP call.** `run_discover(tool, *, request)` wraps `mcp.call_tool("forge_apply_segment_delta", {…request, "mode":"discover"})` → extract manifest. Injected at `apply_editorial_delta`. This is the SAME registered tool `CommitBoundary` calls for verify/apply → DT catch #1 (held↔fresh same-tool) holds in production.
6. **Narrowing.** Executor is narrower than Bridge's class (name-only). Bridge map stays `(updated,segment)`; the executor's `SegmentDeltaContractError` for unsupported → map to `UNSUPPORTED_DELTA_ACTION` (or surface in preview).
7. **Drift-signal alignment — RESOLVED (DT-grounded), no CommitBoundary touch.** The real executor (`executors.py:675`) emits `{"drift": True, "error_code": "plan_state_drift", "reason_code": "plan_state_drift"}` on apply-drift; `CommitBoundary:125` already checks `drift is True` → existing check suffices. *Deferred hardening (unbound, re-open trigger = a host executor that signals drift only via `reason_code`):* normalize CommitBoundary to recognize both encodings (Creative). Out of 1.5.
8. **Discover-error taxonomy re-ground (DT finding — captured-not-assembled, one layer over the wire-key).** The fake emitted `identity_unresolved`; the **real classifier (`flame_apply.py`) does NOT**. Map against the real vocabulary: `missing_flame_identity`/`invalid_flame_identity` → `UNRESOLVED_TARGET`; `unknown_delta_action`/`*_requires_future_executor`/`unknown_segment_fields`/`no_segment_fields_changed` → `UNSUPPORTED_DELTA_ACTION`; else → `HOST_DISCOVER_FAILED`. Capture exact strings from `flame_apply.py`; final set pending DT's grep of the executor's discover return.

**Classifier reuse (optional, aligns with BRIDGE39 preview):** `classify_delta_for_flame_apply` + the contract function let Bridge pre-validate lowerability + identity presence *before* discover — clean sources for `UNSUPPORTED_DELTA_ACTION` and missing-identity warnings.

**Scope split (ponytail — ship the minimal real apply first, layer maturity):**
- **Slice 1.5 — real-wiring CORE (NEXT):** deltas #1–#5 + #7. Repoint to `forge_apply_segment_delta`, fix the `changes` wire key, thin the request, thread `sequence_name`, real `run_discover` via `mcp.call_tool`. Integration test: `operation → host_resolve → commit` end-to-end against the real registered executor + a ratified assent. **Delivers the first real peer-proposal → ratified Flame mutation — the ① payoff.** Covers BRIDGE39 acceptance #1–#6.
- **Slice 1.6 — apply maturity:** operator-facing **preview** payload (BRIDGE39 preview reqs) + **receipt** linking the three evidence layers (Pipeline op receipt + Bridge assent record + host apply result) + **idempotency/duplicate-key** on apply + classifier-driven warnings. BRIDGE39 acceptance #7.
- **Slice 2 — the fan:** heterogeneous deltas → N manifests / N commit nodes / per-node assent (`node_id→AssentRecord` map). Now unblocked (real executor exists). Confirmed-required (#14 ask 4: real deltas are heterogeneous).

**Invariants unchanged:** `executor.py` byte-stable; `__all__`==19; assent only at commit; no `forge_core`/`traffik` import in `composition/` — the real `run_discover` MCP wrapper lives at the `apply_editorial_delta` orchestration edge, not in the boundary (BRIDGE39 import-boundary rule, acceptance #8).

**Cross-repo:** this is the Bridge half of BRIDGE39; Pipeline's half (executor + classifier + metadata) has landed. No new issue needed yet — the contract is the design doc; open one only if the wire shape or executor input drifts from what's grounded above.

### 9.1 Slice-1.5 room convergence (2026-06-23, Orch + Creative + DT)

- **Q1 drift — RESOLVED, CommitBoundary untouched** (executor emits `drift:True`; Creative's both-encoding normalization deferred-unbound).
- **Q2 test fidelity** — registered protocol-faithful double for CI (live Flame = manual UAT, matching Pipeline's `67-traffik-real-fixture-uat`). **Load-bearing condition: the double must mirror the REAL contract** — the `changes` wire key, the real classifier reason codes (delta #8), `drift:True` on apply-drift — captured from `flame_apply.py`+`executors.py`, NOT the fake's vocabulary. A double that repeats the fake re-hides the bugs.
- **Q3 run_discover** — default to the live MCP (like `CommitBoundary._default_mcp`), overridable. Load-bearing for catch #1: same `mcp` ⇒ discover and verify/apply hit the same registered `forge_apply_segment_delta`.
- **Q4 sequence gate** — `sequence_id` is **top-level per `TimelineDelta`**; gate at the *delta* level ("all deltas in `output["deltas"]` share one `sequence_id`") **before flattening** → else `HETEROGENEOUS_DELTA` (multi-sequence = fan, slice 2).
- **Layering guardrail (Creative, binding):** `host_resolve_boundary` stays translator/orchestrator ONLY — (1) validate delta shape, (2) choose host resolver, (3) invoke discover, (4) return the host-authored manifest. Never interprets editorial intent or authors mutation plans; all "how delta→Flame mutation" stays inside `forge_apply_segment_delta`.
- **CODE-START GATE — CLOSED (DT, grounded).** Supported-path discover returns a real manifest via `_build_manifest` (`executors.py:82`): `{type:"mutation_plan", intent_parameters, resolved_plan:[{identity,payload}], originating_capability, apply_counterpart:{tool:"forge_apply_segment_delta", parameter_overrides:{"mode":"apply"}}}` — satisfies `MutationManifest.from_dict` in full; catch #1's tool-match guard passes on the happy path. **Blocker 1 RESOLVED by design:** the executor's discover delegates to `forge_bridge.tools.timeline.rename_shots(mode='discover')` to build `resolved_plan`, then re-wraps with `apply_counterpart.tool="forge_apply_segment_delta"` — segment-name updates apply via Bridge's existing rename machinery (note the Bridge→Pipeline→Bridge call loop; the apply tool calls back into Bridge code). Catch #1 is honored both directions (Bridge enforces the guard; Pipeline `executors.py:42-46` designed the tool name to satisfy it). **Slice 1.5 ready for code.**
