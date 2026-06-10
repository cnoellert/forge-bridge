# Lighting the live cross-peer generation join — converged framing (C + D)

DT grounding 2026-06-09, **converged via two cross-team convergences + a 3-agent redline round** (bridge / generators / contracts views, then adversarial redline). The "live cross-peer generation join" splits into THREE surfaces, and the two execution rungs are **not peers**: rung D is **substrate**, rung C is **producer**. That doctrine line resolves the whole question.

## The three surfaces

| Surface | What it is | Status |
|---|---|---|
| **Declaration / capability** | 17 generator capabilities + typed `generation_facts`, discoverable in the live tool registry — the real #24 win | ✅ **lit by A+B (verified)** |
| **Driver / dispatch** | a protocol-conforming driver so the (already-running) dispatch consumer reaches a backend | ⛏ **HOW settled (rung D) — thin in-process adapter** |
| **Planner invocation** | bridge constructs a `Planner`, runs `.plan()`, originates a generation intent | ⛔ **producer-side — DEFER (rung C)** |

---

## Rung A — DONE (#26 / PR #30) · Rung B — DONE + VERIFIED (generators installed)

A wired `register_all_siblings` at bootstrap (publishes `_canonical_tool_registry`, bound to the live `generation_driver_registry`). B installed generators. Verified: **17 generation declarations + `generation_facts` are live-discoverable; 0 drivers** (generators is schema-only — `register_capability(CapabilityRegistration(declaration=...))`, no handler). A+B light the **declaration surface**, not dispatch.

---

## Rung D — driver wiring: **HOW SETTLED — thin in-process adapter, NOT a process boundary**

**Converged shape (both convergences + redline 1 agree):** generators ship a stateless `BridgeGenerationDriver` protocol-conformance adapter, registered via the existing `handler=` slot. **Bridge owns lifecycle/dispatch/poller/persistence; generators ship the adapter code; bridge injects credentials. Eager registration, lazy credentials.**

```python
# forge_generators/bridge/driver_adapter.py  (behavioral; lazy-imports drivers; NOT in contract_registry)
class BridgeGenerationDriver:                # satisfies bridge GenerationDriverProtocol
    backend_id: str
    backend_identity_triple: dict            # == the capability's declared triple (stamped by construction)
    async def submit(self, envelope) -> DriverSubmitResult   # ArtifactRef→PlatformLocator,
        ...                                                   # InvocationEnvelope→OperatorInvocation;
                                                              # builds credentialed client lazily; NO persist
    async def poll(self, artifact) -> DriverPollResult        # request_id from execution_provenance;
        ...                                                   # NO internal loop — bridge owns the poller
```

**Why an adapter, not a factory/service:** generators' `BackendDriver` does NOT satisfy bridge's `GenerationDriverProtocol` — signature mismatch (`submit(operator_id, OperatorInvocation)→(str,datetime)` vs `submit(InvocationEnvelope)→DriverSubmitResult`) + pydantic-triple-vs-dict. So the unit of work is protocol conformance, one adapter per `(surface, path)`. One generators surface (comfyui) fans out to N adapters.

**Lifecycle ownership (redline-confirmed double-drive hazard):** the adapter must NEVER invoke generators' `LifecycleController` / `LifecyclePoller` / `persist_artifact` / `*_and_wait` operators. Bridge already persists its own `GenerationArtifactRepo` row and runs its own `GenerationPoller`; a second poller would drive one `request_id` across two stores and stall bridge's DB artifact. The adapter is a pure translator.

**`backend_id` reconciliation = by construction.** The adapter stamps `backend_identity_triple == the declared triple`; bridge keys via `backend_id_from_identity_triple → "surface.path"`. The `registration.py` "named-not-filled" reconciler seam is **deleted, not built**.

**Process boundary — REJECTED for now (redline 1).** In-process is the already-wired `registration.py → GenerationDriverRegistry → dispatcher.py:203` path: owes no new contract type, adds no deployable, reversible behind the single `submit` site. A process service is a new deployable + activates a deferred contract type to ship the *first* generation. Re-open trigger: **multi-tenant secret isolation / independent deploy cadence / a generation workload that must outlive the bridge process.**

**Credential blast-radius — genuine unbound item (redline 2).** The adapter's credentialed `submit()` runs on bridge's event loop → the secret IS in bridge's heap at call time. Bridge's "credentials stay out of bridge's process" framing was false. **Accepted for v1** as a marginal widening on a single-operator workstation (bridge already holds `ANTHROPIC_API_KEY` + the Postgres DSN — one trust domain). The delivery *mechanism* (env vs config object vs `BridgeRegistrationContext`) is an implementation detail to settle at build time. Re-open trigger: **multi-tenant** flips the acceptance.

**Build disposition:** D is **substrate** — doctrinally clean to build. BUT build it **paired with its first exerciser** (a consumer inserting `ExecutionPlan`s, or a minimal dogfood harness). A lit driver registry with no plan-producer is "wired ≠ works" one level up — don't build it in a vacuum.

---

## Rung C — live planner invocation: **authority SETTLED-if-built; whether-to-build → DEFER**

**Authority placement (if/when built) — settled:** assent gate at the engine's `routing→execution` transition (the single irreversible edge; `dispatcher.py:203` is the only `submit()`); rides the **chat compile path's mutating-preview**; ratify before any backend invoke; authorizes a **spend envelope, not per-call**. A `forge_plan_*` MCP tool is **rejected** (the model could reach it on a read turn → violates assent-stays-with-operator). `.plan()` persists pre-ratify (inert); the lifecycle advance to `execution` is ratify's only side-effect; the `AssentRecord` must bind the `run_id`/`plan_id` it authorizes (today `graph_intent_id ≠ plan_id` — that fusion is the seam).

**Whether to build now — DEFER (redline 3, load-bearing):**
- **projekt-forge (the named production consumer) does not import `forge_bridge`'s orchestration at all.** `Planner(...)` is constructed only in `tests/smoke_helpers.py:439`.
- Bridge's own docs call this path the **"federation E2E demonstrator / capstone of the federation proof,"** with stub-driver acceptance. It's a proof, not a runtime.
- Building it live makes bridge **originate** generation intents → inverts substrate-not-producer (the propose-side, like the staged-ops propose tools that live downstream).
- Mid-mutation atomicity is **unsolved** (operation-front carry-forward) and bites a paid multi-step dispatch hardest. Active milestone is **v1.9 Conversational Reads** — dogfood reads before paid mutations.

**Re-open trigger:** a named consumer calls bridge's planner/dispatch path (grep flips non-empty), OR a scheduled artist workflow needs bridge-as-producer **AND** mid-mutation atomicity is resolved.

---

## Contract ruling — **no new generation-boundary fact**

`BackendIdentityTriple` (`surface`/`path`/`auth_mechanism`/`revision`) is the complete boundary identity; `handler` is constitutionally opaque (`Any`). Drivers, credentials, backend selection, and assent are all consumer-internal by standing doctrine (ADR-005 / ADR-000 §1). `auth_mechanism` is the *name* of the mechanism (a fact); the secret is not. The only deferred contract seam — the execution-family **invocation envelope + receipt** — is activated *only* by the process boundary, which we reject, so it stays unbound.

---

## Dispositions

### Intentionally unbound (with re-open triggers)
- **Credential-delivery mechanism** (D) — settle at D build time; multi-tenant flips the marginal-blast-radius acceptance.
- **Process boundary** (D) — multi-tenant / independent deploy cadence / detached workload.
- **Execution-family invocation envelope** (contract) — a second peer exchanges a dispatch envelope (Pipeline's driver surface lights up).
- **Rung C build** — a named consumer calls the planner/dispatch path, or a scheduled artist workflow needs bridge-as-producer + atomicity resolved.

### Rejected (closed)
- Process boundary as the *first* move (YAGNI; in-process is already wired + reversible).
- Position B: bridge constructs generators' drivers (breaks thinness + can't satisfy the protocol without importing internals).
- New `forge_bridge.sibling_drivers` entry-point group (the opaque `handler=` slot already does it).
- Eager all-driver construction at boot (strawman — `handler=None` today = zero drivers built).
- Planner-as-MCP-tool (model-reachable on a read turn).
- Any driver / credential / assent / selection field in the contract.

---

## Where it stands

- **Declarations: LIT** (A+B) — the real #24 win; a planner *would* now see 17 real generator capabilities with typed facts.
- **Drivers (D): substrate, HOW settled** (thin adapter) — buildable when paired with a plan-producer.
- **Planner (C): producer, deferred** — until a consumer demands bridge-as-producer + atomicity is solved.

The doctrine line — **D is substrate, C is producer** — is what keeps "wired" from reading as "works."
