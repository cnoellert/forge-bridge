# Lighting the live cross-peer generation join — three rungs

DT grounding 2026-06-09. "Live cross-peer generation join" (#24(c)) is **not** one wiring call. The daemon runs an execution-runtime *skeleton* (dispatch consumer + poller + event consumer, bootstrap Step 5) but the *planning* half is test-only, and the driver registry is empty by design. Decomposed into three independent rungs so "wired" can't launder into "works".

| Rung | What | Status |
|---|---|---|
| **A** | `register_all_siblings` at bootstrap → populates the live driver + tool registry | ✅ **DONE** — PR for #26 |
| **B** | `forge-generators` installed in the bridge `forge` env (declares the entry point; not pip-installed here) | ⬜ env/deploy |
| **C** | A live path that constructs `Planner` + runs `.plan()` + persists the ExecutionPlan for dispatch | ⬜ **needs framing** (mutating surface) |

Evidence: `Planner(...)` / `ToolRegistry()` are constructed **nowhere outside tests**; the Step-5 comment says the driver registry "starts empty and degrades to `dispatch_no_driver` until a later adapter rung registers real generation drivers" — rung A is that rung.

---

## Rung A — DONE (#26)

Wired `register_all_siblings` into bootstrap Step 5, feeding the live `generation_driver_registry` the dispatch consumer reads, published as `_canonical_tool_registry`. Honest effect today: with only vision/pipeline/flow installed, the tool registry gets vision's perception declarations and the driver registry stays empty (no generation sibling) — the path is wired; **B lights the drivers.**

---

## Rung B — install generators in the bridge env (deploy note, not code)

`forge-generators` declares `[project.entry-points."forge_bridge.siblings"] forge_generators = "...contract_registry:register_bridge_adapters"` but is **not pip-installed** in the bridge `forge` env (only `forge_vision`/`forge_pipeline`/`forge_flow` resolve). Until it's installed, rung A discovers no generation siblings and the driver registry stays empty. This is an environment/deploy action on the operator workstation, gated behind the daemon two-job restart ([[project_daemon_two_job_split_ws_server]]).

**Done when:** `forge-generators` is installed in the bridge env and a daemon restart shows its drivers reachable in `_canonical_tool_registry._generation_driver_registry`.

---

## Rung C — live planner-invocation path (NEEDS FRAMING — do not bolt on)

**The actual missing consumer.** Today nothing constructs a `Planner` against the live `_canonical_tool_registry` and calls `.plan()`; even with rungs A+B, no live request builds an `ExecutionPlan` for the dispatch consumer to pick up.

**Why this is framing-grade, not execution:** a planner that selects backends and would dispatch generations is a **mutating** path. Per the #24/operation-front authority doctrine it cannot be silently attached to an endpoint — it must either ride **preview → ratify → apply** (assent stays the operator's) or be deliberately scoped out of it. The open questions are product/architecture, not mechanical:

1. **Entry surface** — where does planning enter live? A new MCP tool (`forge_plan_*`)? An HTTP route? The chat compile path? Each has different authority implications.
2. **Authority placement** — planning + dispatch is a mutation. Does it emit a `preview_emitted` + `graph_intent_id` and require ratify before any backend is invoked, mirroring create-reel? (Strong prior: yes — generations cost money/compute; assent must gate them.)
3. **Plan persistence seam** — `.plan()` produces an `ExecutionPlan`; who persists it to the store the dispatch consumer polls, and at which authority step (post-ratify)?
4. **Failure/atomicity** — the operation-front carry-forward (mid-mutation atomicity, unanswered before destructive ops) applies doubly to a multi-step generation dispatch.

**Recommendation:** treat C as its own framing → discuss → plan cycle, not a same-push add. It is milestone-shaped (it puts the phase-4b planner on a live, assent-gated surface for the first time). File as a framing stub; do not spec the endpoint until the authority placement (Q2) is decided.

**Dependencies:** A (registry) + B (drivers) must be live for C to do anything observable end-to-end.
