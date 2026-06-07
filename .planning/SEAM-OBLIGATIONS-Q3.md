# Seam Obligations — Q3 grounded enumeration (forge-core ↔ bridge)

**Date:** 2026-06-06
**Status:** Q3 COMPLETE (grounded). Feeds Q4 (allocation convergence).
**Frontier:** harden the forge-core↔bridge seam contract — *decide together, fix distinctly.*
**Method:** grounded against forge-contracts `@v0.1` source (`~/GitHub/forge-contracts`,
read at the `v0.1` tag — checkout HEAD is `v0.1-7-g00e1555`; only `references.py`
drifted, 6 lines, immaterial to this map) + bridge import/dispatch sites.

---

## What forge-contracts v0.1 actually is

A **capability-federation + referent** vocabulary. Module layout is only
`base / capabilities / references / registration` — **no entity, relationship,
role, or transport module exists.** `ContractModel` is `extra="allow", frozen=True`
(open, immutable). `CONTRACT_VERSION = "v0.1"`.

Public surface (`__all__` @ v0.1): `ArtifactLocation, ArtifactRef,
BridgeRegistrationContext, CAPABILITY_FAMILY_{EXECUTION,GENERATION,MATTE,PACKAGING,
PERCEPTION,VALIDATION}, CONTRACT_VERSION, KNOWN_CAPABILITY_FAMILIES,
CapabilityDeclaration, CapabilityFamily, CapabilityRegistration, Reference,
ReferenceResolution, RegisterCapabilityCallable, ResolutionStatus`.

Decisive field-level finding for invocation-binding:
- `CapabilityDeclaration{contract_version, capability_id, family, owner, summary,
  payload_family, input_schema, output_schema, metadata}` — declarative identity only.
- `CapabilityRegistration{declaration, handler: Any = None}` — **`handler: Any = None`
  is the entire declaration→executable bridge.** Untyped, optional.
- The executable identity (`backend_identity_triple`) lives in
  `forge_bridge/orchestration/drivers.py`, **not** the contract.

---

## Obligation map

| # | Seam obligation | What the seam needs | v0.1 coverage | Owner today (improvisation point) |
|---|---|---|---|---|
| 1 | **Capability-routing** | which declared capability satisfies a step | ✅ COVERED — `CapabilityDeclaration`, `KNOWN_CAPABILITY_FAMILIES` (6) | Contract. Reconciled Phase 6A. |
| 2 | **Referent vocabulary** | what does "this" point to | ✅ COVERED — `Reference`, `ReferenceResolution`, `ResolutionStatus`, `ArtifactRef` | Contract — **but bridge-internal axis (Phase X), NOT the consumer-producer seam.** Off-frontier. |
| 3 | **Invocation-binding** | declaration-identity → executable-identity | ⚠️ PARTIAL — declaration identity specified; binding is just `handler: Any = None`; `backend_identity_triple` is bridge-side | **Bridge-improvised.** Nobody wrote how `capability_id` maps to an executable backend, or who asserts it. |
| 4 | **Entity + relationship ownership** | `version_of(version→shot\|asset)`, `member_of`, `references` | ❌ ABSENT — no entity/relationship types | **Producer-omitted.** Version-linkage gap's true home + owner-type-polymorphism deliverable. |
| 5 | **Role vocabulary** | media roles (raw…render) / track roles (primary…) | ❌ ABSENT | **Each repo defines independently** → render-role skew. |
| 6 | **Wire/transport envelope** | correlation id / `msg_id` / `ref_msg_id` | ❌ ABSENT — no transport module | **Bridge-improvised** (bilingual shim). Don't retire the shim until both sides speak a contract envelope. |

---

## Sharpening (what the map establishes)

- **v0.1 is a capability contract, not a data/binding/transport contract.** The
  seam-frontier work is exactly the layer v0.1 lacks. The cursor's
  "contract-vocabulary reconciliation" milestone = **{#3 invocation-binding,
  #4 entity/relationship-ownership, #5 role vocabulary, #6 wire envelope}** — now
  grounded as the precise scope.
- **Axis distinction confirmed in the data:** the two COVERED obligations are
  capability (#1) + referent (#2), and #2 is bridge-internal (Phase X), explicitly
  *off* the consumer-producer seam. Everything on the seam frontier is partial or
  absent. The seam frontier, Phase 7, and Phase X are three different axes.
- **Each absent obligation has a different current owner** — bridge-improvised
  (#3, #6), producer-omitted (#4), independently-defined (#5). The "who should own
  it" allocation is **non-uniform** → Q4 cannot be answered with one rule. This is
  why the ruling is *decide together, fix distinctly.*

---

## Cross-refs
- Live cursor: `memory/project_passoff_2026_06_06_seam_frontier_phase7_orthogonal.md`
- Version-linkage (obligation #4): `.planning/GAP-VERSION-OWNERSHIP-LINKAGE.md`
- Ownership ruling (owner-type polymorphism, #4): `.planning/RULING-DURABLE-OWNERSHIP-VS-CONTEXTUAL-PLACEMENT.md`
- Role vocabulary (#5): render-role commit `496ae8c`; bridge media roles = 7
- Wire envelope (#6): `.planning/STATE-WS-CORRELATION-CONTRACT.md`
- Capability routing (#1): `.planning/PHASE-6A-DISCOVERY-ALIGNMENT.md`

## Next: Q4 — allocation
For each of #3–#6: does the obligation belong in **contracts** / **bridge** /
**consumer**? Non-uniform answers expected. Convergence-ready; this table is the input.
