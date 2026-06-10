# Lighting the live cross-peer generation join — the rungs (corrected by B verification)

DT grounding 2026-06-09, **corrected after rung-B verification**. "Live cross-peer generation join" (#24(c)) is **not** one wiring call. It splits into THREE distinct surfaces, and a rung-B sandbox probe (register_all_siblings against the real entry-point group, generators installed) falsified the original framing: **generators is a schema-only sibling** — it registers capability *declarations*, never driver *handlers*.

## The three surfaces

| Surface | What it is | Status |
|---|---|---|
| **Declaration / capability** | 17 generator capabilities + typed `generation_facts`, discoverable in the live tool registry — what a planner reads | ✅ **lit by A+B (verified)** |
| **Driver / dispatch** | live, credentialed handlers so dispatch executes to real backends | ❌ dark — generators schema-only; handlers come from nowhere yet |
| **Planner invocation** | a live path that builds an `ExecutionPlan` from declarations | ❌ not live (rung C) |

Evidence: `Planner(...)` / `ToolRegistry()` are constructed **nowhere outside tests**. Generators' `register_bridge_adapters` calls `register_capability(CapabilityRegistration(declaration=declaration))` — **no handler** (confirmed in source). Probe result: 4 siblings registered, 36 tools, **17 generation declarations**, **0 of 16 drivers reachable**.

---

## Rung A — DONE (#26 / PR #30, merged)

Wired `register_all_siblings` into bootstrap Step 5; publishes `_canonical_tool_registry`, bound to the live `generation_driver_registry`, before the dispatch consumer starts.

**Corrected effect:** A populates the **declaration registry**. It feeds the driver registry *only for siblings that register a handler*. The boot-wiring test proves that routing with a stub driver — but **real generators register no handler**, so A's concrete live effect is the declaration surface, not dispatch. (The PR/issue line "dispatch stops returning `dispatch_no_driver`" over-claimed; corrected on issue #26.)

---

## Rung B — DONE + VERIFIED (generators installed in the bridge env)

`forge-generators` (local clone @ `82698f9`) installed editable into the bridge `forge` env — clean, zero dep churn. Sandbox probe confirms **17 generation declarations now live-discoverable** with their `generation_facts`. This is the substrate #24's facts-consumption targets, and what rung C's planner reads.

**What B does NOT do:** populate the driver registry. Generators is schema-only by design (`pyproject` comment: "schema-only sibling"). Dispatch stays dark.

**Done when (corrected):** a daemon restart shows the 17 generator declarations in `_canonical_tool_registry` (NOT drivers reachable — that's the driver-wiring rung below).

---

## Rung D (NEW) — live driver/handler wiring (parallel to C, NEEDS FRAMING)

The gap B revealed. For dispatch to execute against real backends, live **driver handlers** (the `comfyui` / `fal` / `runway` / `higgsfield` / `magnific` clients) must be registered into the `GenerationDriverRegistry`, keyed by `backend_identity_triple`. Generators ships these drivers in its package but **does not register them as bridge sibling handlers** — it publishes declarations only.

This is the `registration.py` "backend_id reconciliation" seam, named-and-deferred: *"Materialize the reconciler only when a plan step first needs to EXECUTE a selected capability."* Open product/credentials questions:

1. **Where do live drivers live at runtime** — does generators register handlers in `register_bridge_adapters` (couples bridge bootstrap to generators' driver stack + credentials), or does bridge construct drivers from declarations on demand?
2. **Credentials** — the drivers call paid APIs; their keys/config must be present in the bridge env at registration or invocation time. Bootstrap-time construction means bootstrap needs the secrets.
3. **Lazy vs eager** — construct all 16 drivers at bootstrap, or only the selected backend at dispatch time (the reconciler-on-demand the comment suggests)?

**Recommendation:** own framing pass. Couples to C (a plan must select a backend before its driver matters) but is a distinct decision (credentials + driver lifecycle vs. authority placement).

---

## Rung C — live planner-invocation path (NEEDS FRAMING — do not bolt on)

**The missing consumer.** Nothing constructs a `Planner` against the live `_canonical_tool_registry` and calls `.plan()`. This puts the phase-4b planner on a live surface for the **first time**.

A planner that selects backends and would dispatch generations is a **mutating** path. Per the #24 / operation-front authority doctrine it must either ride **preview → ratify → apply** (assent stays the operator's) or be deliberately scoped out. Open questions:

1. **Entry surface** — new MCP tool (`forge_plan_*`)? HTTP route? The chat compile path?
2. **Authority placement** — does it emit `preview_emitted` + `graph_intent_id` and require ratify before any backend is invoked, mirroring create-reel? (Strong prior: yes — generations cost money/compute; assent must gate them.)
3. **Plan persistence seam** — who persists the `ExecutionPlan` to the store the dispatch consumer polls, at which authority step (post-ratify)?
4. **Failure/atomicity** — mid-mutation atomicity (operation-front carry-forward) applies doubly to a multi-step generation dispatch.

**Recommendation:** own framing → discuss → plan cycle. Milestone-shaped. Don't spec the endpoint until authority placement (Q2) is decided.

---

## Where it stands

- **Declarations: LIT** (A done, B done+verified). A planner would now see 17 real generator capabilities with typed facts. This is the genuine win.
- **Drivers: dark** → rung D (driver/credentials framing).
- **Planner: not live** → rung C (authority framing).

C + D are both required for end-to-end execution, and both are framing-grade, not same-push adds. The declaration surface — which is what #24 was about — is real and live.
