# FRAMING — Rung 2B + Step-2.1: stop shadowing the contract

**Status:** FRAMING — OPEN (not ratified, not started). This is the deferred motion (2) from `PHASE-6A-DISCOVERY-ALIGNMENT.md` § "RATIFIED FRAMING — Rung 2." Grounded against `main @ b5fb79b` (Rung 2A landed `a9ca444`, F841 cleared `b5fb79b`). Opened by Orch 2026-06-05.

**What the room deferred:** Rung 2 split two motions hiding inside "registry-type separation" — (1) decomposition [LANDED as 2A], (2) **contract-shadow elimination**, itself two pieces: **Rung B** (store `CapabilityDeclaration` directly, retire the bridge-owned `ToolRegistration` record) + **Step-2.1** (adopt the published `BridgeRegistrationContext` / `RegisterCapabilityCallable`, retire the bridge-local shadows). Both deferred together as "the stop-shadowing convergence rung."

---

## Grounding headline (live reads 2026-06-05) — the bundle should not survive contact with the code

Three findings reshape the deferred rung. **The framing's first job is to decide whether "motion 2" is still one rung.**

### Finding 1 — B and Step-2.1 have ASYMMETRIC ripple. They are not one change.
- **Step-2.1 is a contained, low-risk de-shadow.** Bridge already imports `CapabilityDeclaration` + `CapabilityRegistration` from `forge_contracts` (`registration.py:10`). It only *shadows* two things: `RegisterCapabilityCallable` (local alias, `registration.py:22`) and `BridgeRegistrationContext` (local frozen dataclass, `registration.py:27`). The published `forge_contracts.registration.BridgeRegistrationContext` carries `{bridge_version, contract_version, requested_families, dry_run, config}` — a **superset** of what bridge actually constructs at `discovery.py:144` (`{bridge_version, requested_families, dry_run, config}`). The only behavioral nuance is `frozenset` (bridge) → `list[str]` (published), and request-all passes empty so it's near-moot. **Ripple: `registration.py` + one construction site in `discovery.py`. The planner never sees it.**
- **Rung B re-ripples the planner.** It is the only piece that crosses the consumer side. See Finding 2.

⇒ Bundling them repeats the exact decompose-vs-de-shadow scope-bleed Rung 2 *just* resisted. [[feedback_explicitly_unbound_vs_implicitly_rejected]]

### Finding 2 — `CapabilityDeclaration` is a 9-field superset; B is a field-rename ripple across the planner, not a swap
Field mapping (bridge `ToolRegistration` → contract `CapabilityDeclaration`):

| bridge `ToolRegistration` (5) | contract `CapabilityDeclaration` (9) |
|---|---|
| `tool_id` | `capability_id` |
| `family` | `family` ✓ |
| `payload_family` | `payload_family` ✓ |
| `schema` | `input_schema` |
| `capabilities` | `metadata` |
| — | `contract_version`, `owner`, `summary`, `output_schema` (4 bridge does not consume) |

Every planner read of the record shape must be retargeted (`tool.tool_id` → `.capability_id`, `tool.capabilities` → `.metadata`). Grounded read sites (the ripple surface):
- `planner_passes.py:84` `by_family("generation")`, `:85` `tool.capabilities`, `:87`+`:93` `tool.tool_id`
- `planner_passes.py:248-249` `by_family("perceptual")` / `by_family("matte")`, `:259`+`:262` `provider.tool_id`
- plus `ToolRegistry.by_family` itself (reads `.family`)

### Finding 3 — a LATENT LIVE DEFECT sits in B's blast radius (independent of B; surfaced by this grounding)
`planner_passes.py:248` queries `by_family("perceptual")` — **dead bridge vocab.** The registry stores `declaration.family` verbatim (`registration.py:70`), which for contract-conformant Vision is **`perception`** (`KNOWN_CAPABILITY_FAMILIES = {execution, generation, matte, packaging, perception, validation}`). So `by_family("perceptual")` returns **empty against real Vision today** — pass_3 transform-insertion for perception providers is silently inert in production.

Why it stayed invisible (twin masks):
1. **Fixture-mirrors-bug:** `test_planner.py:483` builds its synthetic provider with `family="perceptual"` — the dead vocab — so the unit test passes against the divergence. [[feedback_fixture_shape_mirrors_production]]
2. **Proof gap:** the live proof (`test_sibling_discovery_live.py`) exercises a capability *query* only (`by_family("execution")` + dispatch-id assertion), never the planner's pass_3. So the divergence is uncovered end-to-end.

This is the **second member of the family-reconcile equivalence class**: the thin vertical fixed the discovery *filter* vocab (request-all) but the *consumer-side* `by_family` queries and the test fixtures still carry dead `perceptual`. [[feedback_sibling_check_before_fix_scope]]

---

## Open decisions (Orch leans stated; structural ones flagged for convergence)

### D1 — Sequencing: is motion (2) one rung or two? **[Orch lean: SPLIT]**
Step-2.1 is a contained de-shadow with no planner ripple; B re-ripples the planner. Do **Step-2.1 first** (cheap, pure, low-risk), then frame B on its own evidence. Bundling re-conflates the two axes Rung 2 separated. *One change per seam.* [[feedback_arbitration_boundary_discipline]]

### D2 — Step-2.1 adoption: clean swap to published types? **[Orch lean: YES, low-risk]**
Published `BridgeRegistrationContext` ⊇ bridge's constructed fields; `RegisterCapabilityCallable` is a type alias. Swap is contained to `registration.py` + `discovery.py:144`. **Open sub-question (DT grounding):** does any bridge-side reader depend on `requested_families` being a `frozenset` (set ops / membership semantics), or on the absence of `contract_version`? Request-all passes empty, so likely moot — confirm, don't assume.

### D3 — Rung B: is it worth doing at all — and if so, raw `CapabilityDeclaration` or a bridge-owned record mirroring contract field *names*? **[Orch lean: CONVERGENCE — genuinely balanced]**
Apply the room's own A-now-B-later test — *which smell has positive evidence?*
- We have **no** grounded evidence the bridge-owned record is *harmful* (it duck-types; downstream is declaration-pure post-2A). The "stop shadowing" thesis is an aesthetic/coupling preference, not a proven-defect fix — same posture that deferred B in the first place.
- Storing `CapabilityDeclaration` **raw** imports 4 unconsumed fields and removes the insulation seam against contract churn (every contract field rename then ripples straight into the planner).
- A **bridge-owned record that mirrors contract field *names*** (`capability_id`/`input_schema`/`metadata`) buys the planner-readability win *and* keeps an adapter seam — arguably the best of both, and closest to what `tool_registration_from_capability` already is.

So B's real payload may reduce to "rename bridge fields to match the contract + fix the vocab" — which can be had **without** coupling the registry to the contract type. **This is the convergence question:** does the room want true type-adoption (accept the coupling) or name-alignment-with-insulation? And is either worth a planner re-ripple absent a proven defect? [[feedback_deferral_first_class_governance]]

### D4 — The latent `perceptual` defect: fix independently, or fold into B? **[Orch lean: FIX NOW, independently]**
It is a **live bug**, exists regardless of B (both record shapes carry `declaration.family`), and is a one-line vocab correction + a regression test that exercises pass_3 against a real `perception` provider (and de-masks the `test_planner.py:483` fixture). Gating it behind the B convergence leaves a production defect latent for an aesthetic rung. Recommend a **small standalone fix-rung BEFORE B**, scanned for the full `by_family(...)` equivalence class (grep all consumer-side family-string literals against `KNOWN_CAPABILITY_FAMILIES`). [[feedback_grep_c_completion_invariant]]

---

## DT grounding items — RESOLVED (live reads 2026-06-05 @ `b5fb79b`)
1. **D2 — context-field inventory → Step-2.1 LOW-RISK, confirmed.** Bridge only *constructs and passes* the context (`discovery.py:144`; field default `:110`, assignment `:146`) — it never reads the fields back (the `ctx: BridgeRegistrationContext` param at `:96` is forwarded to `_invoke_sibling`, not inspected). `contract_version` is referenced **NOWHERE** in bridge. `requested_families` is never set-op'd bridge-side; siblings coerce via `frozenset(requested_families or ())`, so `list[str]` (published) vs `frozenset` (local) is **moot**. ⇒ swap contained to `registration.py` + `discovery.py:144`; D2 lean YES grounded.
2. **D4 — equivalence class COMPLETE = 1 divergent literal + 1 mask.** Consumer-side `by_family` literals are exactly: `:84 "generation"` ✓, **`:248 "perceptual"` ✗** (dead; contract = `perception`), `:249 "matte"` ✓. **`perceptual` is the ONLY divergent literal** across all of `forge_bridge/`. Mask confirmed at `test_planner.py:483`. (`editorial` in tests is the intentional rung-1 off-contract-classification fixture, not a consumer query — excluded.) **Behavioral teeth (grounded):** `pass_3` does `provider = perceptual[0] if perceptual else (matte[0] if matte else None)`; since `by_family("perceptual")` is always empty against real Vision, perception providers are **never selected — content-policy-bypass transforms MIS-ROUTE to matte** (or refuse) where perception should win. Not merely inert. ⇒ D4 = fix `:248` + de-mask `:483` + a regression test with a real `perception` provider; **standalone fix-rung BEFORE B** confirmed (live bug, don't gate behind an aesthetic convergence).
3. **B snapshot interaction → NONE (Orch lean confirmed).** `pass_1` builds the snapshot from `by_family("generation")` reading `tool.capabilities` + `tool.tool_id` (`:84-96`). B renames those *accessors* (`.metadata`/`.capability_id`) but does **not** change which families populate the snapshot — the generation-only fallback caveat **survives B unchanged**. Snapshot completeness stays its own out-of-scope rung.

---

## Scope guard (CANDIDATE — to be ratified at discuss)
- **IS (proposed order):** (D4) standalone `perceptual`→`perception` consumer-vocab fix + de-masked test → (Step-2.1) adopt published `BridgeRegistrationContext`/`RegisterCapabilityCallable` → (B, convergence-gated) decide adoption-vs-name-alignment, then execute if ratified.
- **IS NOT:** ❌ build the invocation/dispatch path or capability→driver resolver (still Phase 7) · ❌ fill the named `backend_id` reconciliation seam · ❌ widen the generation-only snapshot to family-complete · ❌ introduce a uniform `InvocationHandler` abstraction (invocation is family-shaped — no evidence two families need the same one).

## Convergence recommendation
**D3 is the convergence-worthy decision** (true type-adoption vs name-alignment-with-insulation; and whether B earns a planner re-ripple at all without a proven defect). D1/D2/D4 have strong enough leans to ratify at discuss without a full convergence. Suggested move: **land D4 now (it's a bug), do Step-2.1 (D2) as a clean de-shadow, then run convergence on D3 (B) on its own merits** — rather than carrying B as a foregone conclusion.
