# Phase 6A — Bridge Discovery Alignment Report

**Status:** SCOPING (plan artifact for the thin discovery vertical). No implementation in this doc.
**Grounded against (live reads, 2026-06-05):** `forge-contracts` v0.1 (`src/forge_contracts/capabilities.py`, `references.py`), `forge_bridge/orchestration/{discovery,registration,planner_passes}.py` + `store/orch_capability_snapshot_repo.py`, `forge-vision/forge_vision/bridge/contract_registry.py`, `forge-pipeline/forge_core/bridge/contract_registry.py`. Base: forge-bridge `main` (clean).
**Pin:** this is the proof-sequence's **Bridge Discovery** milestone — Phase 5 in `forge-contracts/docs/FEDERATION-PROOF-SEQUENCE.md` (ADR-000 = Phase 0), "Phase 6" in offset numbering. Use the name.

## Why this is the move
Two parallel bridge workstreams: Phase X context-pressure (referent resolution, **dogfood-gated** — can't be forced) ⟂ Bridge Discovery (capability-family routing, **unblocked**). The federation proof sequence has Vision/Pipeline/Contract-stability done; **Bridge Discovery is bridge's deliverable and gates the Phase 7 E2E demonstrator.** Vision and Pipeline can only harden their base dependency once bridge discovers. One milestone, four unblocks (Vision + Pipeline + Generators + Contracts confirming v0.1 against its primary consumer). Ratified by the room + operator 2026-06-05.

## Verdict: reconcile, not rebuild — and bridge is the laggard
The siblings already conform to the published contract; **bridge never imported `forge_contracts`** and built its own `ToolRegistration` shape under phase-4b. The discovery *mechanics* are sound and reusable; the registration *protocol* diverged. Direction of alignment is **toward the contract** (ADR-000: "Bridge adapts to real sibling declarations," not the reverse).

### It does not work end-to-end today — two hard breaks at the wire
1. **Context field.** Siblings read `ctx.requested_families` (`list[str]`); bridge's `BridgeRegistrationContext` provides `capability_kinds: frozenset[str]` + `required_capability_kinds`. Missing attribute → `AttributeError` (also a `list`-vs-`frozenset` type mismatch).
2. **Registration payload.** Siblings call `register_capability(CapabilityRegistration(declaration=CapabilityDeclaration(...)))` — **declaration-only**. Bridge's callback is `register_tool(ToolRegistration(tool_id, family: str, payload_family, schema, handler, capabilities))` — **handler-carrying**, with `_validate_generation_handler` asserting `backend_id` + async `poll`. Different class; different concern.

## The load-bearing finding: gate-vs-open is RESOLVED, and it reframes the family fix
**Bridge's registry is OPEN.** `ToolRegistry.register` (registration.py:60) rejects nothing on family — it only special-cases `family == "generation"` (handler validation). `DEFAULT_CAPABILITY_KINDS` is **not** a closed allowlist.

**The gate is caller-driven, applied sibling-side, via `requested_families` — and empty ⇒ all.** Both siblings do `requested = frozenset(requested_families or ()); if requested and family not in requested: skip` (`forge_vision/.../contract_registry.py:41`, `forge_core/.../contract_registry.py:29`). So:
- bridge passes **empty/None** `requested_families` → siblings register **everything** (open path);
- bridge passes a **non-empty** set → siblings filter to it (gate path).

**Consequence (the trap a naive vertical falls into):** if bridge passes its local `DEFAULT_CAPABILITY_KINDS = {perceptual, validation, generation, matte, editorial}` as `requested_families`, it **silently sinks both primaries** — Vision's `perception` is filtered out by the `perceptual` typo, Pipeline's `execution` is filtered out by omission. A vertical scoped as "rename `perceptual`→`perception`" would pass Vision and **face-plant at Pipeline** with a false-positive success.

**So the correct fix is not a rename — it is: bridge requests-all (empty `requested_families`) and classifies received declarations against the contract vocabulary.** Discovery must not be gated by bridge's local family list.

## Family vocabulary divergence (not isomorphic)
- **Contract** `KNOWN_CAPABILITY_FAMILIES` = `{perception, validation, generation, matte, packaging, execution}`
- **Bridge** `DEFAULT_CAPABILITY_KINDS` = `{perceptual, validation, generation, matte, editorial}`
- Exact matches: `validation`, `generation`, `matte`. Divergences: `perceptual`≠`perception` (sinks Vision); bridge **missing** `execution` (Pipeline's own family — `_EXECUTION_CAPABILITY_ID = "forge_pipeline.execution.dispatch"`, declared `family="execution"`) **and** `packaging`; bridge carries non-contract `editorial` (no sibling declares it).
- **`CapabilityFamily` is a `str` TypeAlias** (not an enum) with `KNOWN_CAPABILITY_FAMILIES` as a soft frozenset — so the contract treats families as open strings with a known-set, reinforcing "request-all + classify" over "closed allowlist."

## Classification
| Surface | Verdict | Note |
|---|---|---|
| Entry-point enumeration + `resolve_siblings` config (disabled/additional/required) | **Reusable** | correct group `forge_bridge.siblings`, sound config layering |
| `RegistrationOutcome` accounting + event emission + degraded-mode | **Reusable** | protocol-agnostic counting |
| `CapabilitySnapshotRepo` (content-addressed store) | **Reusable** as a store | record shape (`DBOrchCapabilitySnapshot`) needs field alignment |
| Six-pass planner *structure* (snapshot→filter→transforms→rules→rank→verdict) | **Reusable** | sound capability-routing spine |
| `BridgeRegistrationContext` | **Adapter** | add `requested_families`; reconcile `list` vs `frozenset` |
| Snapshot record shape | **Adapter** | map to `CapabilityDeclaration` fields |
| Family-vocabulary gating | **Divergent** | request-all + adopt `KNOWN_CAPABILITY_FAMILIES`; retire local `DEFAULT_CAPABILITY_KINDS` as a filter |
| **Register callback contract** | **Divergent (conceptual)** | discovery/invocation conflation — see below |

## The architectural target (more important than any single rename): declaration-first discovery
Bridge's registration **conflates discovery with invocation**. The contract asks *"what exists?"* (`CapabilityDeclaration`, zero behavior). Bridge currently asks *"what exists and how do I execute it?"* (`ToolRegistration.handler` + generation-driver validation). **Phase 6A should move bridge to declaration-first discovery with execution-time invocation as a separate concern** — split registration into (a) capability declaration/snapshot [→ contract] + (b) handler/driver binding [bridge-local, invocation-time, e.g. via `drivers.py`]. This eliminates a future coupling, brings bridge into the contract model, and is exactly the separation that one-spine-two-resolvers needs (discovery yields declarations; invocation is drivers). Reconciling wire incompatibilities without this split would be repairing symptoms.

## Planner seam check (one-spine-two-resolvers)
The six-pass planner (`planner_passes.py`) is **pure capability-routing**: `pass_1` resolves the capability snapshot, `pass_2` filters candidates from it, `pass_3` inserts transforms, `pass_4` shape-rules, `pass_5` rank/predict, `pass_6` feasibility verdict. **No referent-resolution stage exists**; `PlanningContext` carries `capability_snapshot`, not desktop world-state. Verdict: the spine is sound and the referent seam is **addable but not reserved** (a referent pass would slot before `pass_2`, resolving deixis→entity before capability filtering). **Phase-6A constraint:** do not let wired discovery assume plan steps arrive with referents pre-resolved — leave `PlanningContext` room for a future referent pass. Cheap now, expensive retrofit later.

## Packaging hole (close first)
`forge-contracts` is installed in the env but **not declared in bridge `pyproject.toml`**. Pin `forge-contracts @ git+https://github.com/cnoellert/forge-contracts.git@v0.1` (as Vision/Pipeline do) before importing it in bridge code.

## Creative's five questions — answered from the code
1. **Is bridge's family vocabulary authoritative / advisory / filtering?** → It becomes a *filter only if bridge passes it as `requested_families`*. It should be **advisory** at most; the contract vocab is authoritative. Recommendation: request-all, don't pass the local set.
2. **Does discovery reject unknown families or merely classify?** → **Open** — the registry accepts any family; filtering is opt-in caller-driven, sibling-side. No rejection of unknowns.
3. **Migration path for `editorial`?** → `editorial` is bridge-only with no contract counterpart and no sibling declarant; **retire it from the discovery path.** A real editorial capability would be a contract proposal, not a local filter token.
4. **How do `packaging`/`execution` enter bridge vocab?** → They don't need to "enter a bridge allowlist." Request-all means bridge **receives** them; bridge's local vocab should mirror `KNOWN_CAPABILITY_FAMILIES` for classification/required-gating, not act as a discovery filter.
5. **End-state: contract- / bridge- / adapter-authoritative?** → **Contract-authoritative.** `KNOWN_CAPABILITY_FAMILIES` is the source of truth; bridge classifies against it; `DEFAULT_CAPABILITY_KINDS` is retired or re-derived from the contract.

## The thin Phase-6A vertical (scoped by this report)
1. **Pin `forge-contracts @v0.1`** in `pyproject.toml` (close packaging hole).
2. **Align the registration protocol:** `BridgeRegistrationContext.requested_families`; callback → `register_capability(CapabilityRegistration)`; **split handler-binding out of declaration-registration** (declaration-first).
3. **Family reconcile (first-class, not a rename):** request-all (empty `requested_families`); classify against `KNOWN_CAPABILITY_FAMILIES`; retire `DEFAULT_CAPABILITY_KINDS` as a filter; drop `editorial`; ensure `execution` + `packaging` flow through.
4. **PROOF (the proof-sequence's minimal bar):** bridge discovers **Vision AND Pipeline** live via the real entry points → builds a capability snapshot → answers ONE capability query (e.g. "which capability satisfies `execution`?" → `forge_pipeline.execution.dispatch`). **Pipeline in the proof is mandatory** — Vision-only would mask the `execution` gap.
5. **Leave the planner referent seam explicitly open** (deferral comment in `PlanningContext` / `planner_passes`).

## Out of scope (stays where it is)
Phase X measurement (dogfood-gated), the blind Q3 gate, the Phase X referent resolver (gated behind Q3), the full discovery runtime beyond the thin vertical, the generation-driver/invocation layer beyond the declaration/binding split. Prove the seam, then widen.
