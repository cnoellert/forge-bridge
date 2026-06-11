# MEMO — forge-flow propagation-driver conformance review

**Date:** 2026-06-10
**From:** forge-bridge (DT) · **To:** forge-flow
**Re:** Conformance review of "forge-flow as a Bridge propagation driver" (UC-1: flow + reference-recommendation)
**Contract pin:** forge_contracts v0.3
**Companions:** `.planning/VISION-COMPOSITION-SEAM.md` (#45), `.planning/memos/MEMO-perception-land-dispatch.md` (#47/#49)

---

## TL;DR verdict

5 of 7 asks ratify as-proposed; 1 ratifies with a substrate caveat; 1 is a gap forge-flow has already designed around. forge-flow's choice to have `auto_propagate` own the composition forge-flow-side is exactly right — it sidesteps the one hard gap. The async-lifecycle question (ask 2) **converges objectively on B0 — consumer-driven polling** — with in-chain polling ruled out by the 60s exec bound and autonomous bridge polling deferred as future infrastructure.

| Ask | Verdict |
|---|---|
| 1. Tool-attach contract stable | ✅ **RATIFY** |
| 2. Async submit/poll lifecycle | ✅ **RATIFY — B0 (consumer-driven) is the v1 lifecycle** |
| 3. Output-supplied-parameter routing (3a→3b) | ⛔ **GAP — not built; auto_propagate sidesteps it (endorsed)** |
| 4. Clip-relative offset convention | ✅ **RATIFY** |
| 5. Ref/locator I/O contract | ✅ **RATIFY the contract** · ⚠️ live location-granting is substrate-deferred |
| 6. family "propagation" + payload_family ".draft" | ✅ **RATIFY** |
| 7. Routing metadata keys | ✅ **NAMED** (caveat: planner is a demonstrator) |

The seam splits cleanly: **contract / attach / convention / v1-lifecycle ratify now** (1, 2-as-B0, 4, 5-contract, 6, 7); only **output→input routing** (3) and the live location-granting substrate (5-live) touch the deferred federation frontier (rung-C / #31, the demonstrator planner). v1 needs none of it.

---

## 1 — Tool-attach contract. RATIFY.

forge-flow's `forgeflow.bridge.registry:register_with(mcp)` matches the bridge's contract exactly. Discovery: `forge_bridge.siblings` EP group → imports `<pkg>.bridge.registry` → calls `register_with(mcp)` (`discovery.py:61-118`). It runs at **module load, before `mcp.run()`** — the D-14 guard (`_server_started`) blocks `register_tools()` only after lifespan startup (`server.py:536`; guard `registry.py:172-176`). Per-sibling failures isolated by try/except → `attached` / `no_register_with` / `error` (`discovery.py:107-116`; test `test_sibling_tool_attach.py`). `register_tools(mcp, [...], prefix="forge_")` is documented public API; `forge_` is valid (`_VALID_PREFIXES = {flame_, forge_, format_, synth_}`). The `no_register_with` in today's boot log flips to `attached` the moment the module exists.

## 2 — Async submit/poll. RATIFY — B0 (consumer-driven) is the supported v1 lifecycle.

**The v1 answer:** attach the two tools, emit the declarations, return job ids, make `poll` idempotent — **the bridge drives the lifecycle from the caller.** `forge_submit_propagation` is one fast call (returns a job id); `forge_poll_propagation` is a fast idempotent call the **consumer/operator repeats until a terminal status**. Both are plain synchronous MCP tools (attach ratified in ask 1); nothing new is required of the bridge. This is precisely the idempotent-poll shape forge-flow already designed. UC-1's acceptance ("Bridge calls submit … polling eventually returns complete") is satisfied — "Bridge" = the attached tools; the loop is driven by the caller.

**In-chain polling is rejected.** A single authored chain cannot sit and poll for a multi-minute job: `/api/v1/exec` is hard-bounded at **60s** (`_EXEC_HTTP_TIMEOUT = 60.0`, `handlers.py:442`), and the deterministic chain engine has no poll-until/await-job primitive anyway (primitives are foreach/collect/filter/if_gate/select/commit only, `forge_bridge/graph/`). Do **not** model the loop as one chain execution.

**Autonomous bridge-driven polling is future infrastructure, not a flow requirement.** The bridge *does* run a live async-job loop — `GenerationPoller` + the dispatch consumer, wired in `server.py`, driving a driver `submit()/poll()` protocol via `GenerationDriverRegistry` (`orchestration/worker.py`, `dispatcher.py`). But that is generation-artifact-shaped substrate whose originating dispatch is the deferred rung-C / **#31** producer. Generalizing it into a durable, caller-out-of-loop async-job orchestrator is a **future capability** (right for fire-and-forget jobs that must survive restarts) — it is **not** required for forge-flow's UC-1 and must not be built under the banner of "just polling."

## 3 — Output-supplied-parameter routing. GAP — already solved by design.

Neither path supports it: the demonstrator planner hardcodes `operator_sequence[].inputs = []` (`planner_passes.py:372`) — zero output→input wiring; and the live chain engine binds a body tool's args from public context + standard-ID extraction (`project_id`/`shot_id`/`version_id`), **not** arbitrary fields (`_step.py:248-257, 651-656`). So a `recommend_references → propagate_stmap` chain feeding the recommended offset into `reference_index` is **not routable** today (same seam as forge-vision's greenscreen→roto, `MEMO-perception-land-dispatch.md`). **→ Endorse v1: `auto_propagate` owns the 3a→3b composition forge-flow-side; the bridge calls one tool.** Separately ✅ confirmed: **a capability with no `reference_index` input is NOT gated out** — discovery registers any declaration, no input-schema gate (`discovery.py:212-218`; family open).

## 4 — Clip-relative offset convention. RATIFY.

Nothing in the bridge blocks it; it aligns with bridge doctrine (the bridge owns the offset↔absolute-frame mapping; forge-flow stays source-agnostic). Honored: 0-based offsets from the submitted clip's first frame; `clip_start_frame` echoed-not-interpreted by forge-flow; `absolute = clip_start_frame + offset` computed bridge-side. Freeze it as the seam contract — agreed.

## 5 — Ref/locator I/O. RATIFY the contract; one honesty flag.

forge-flow's shape maps directly to forge_contracts v0.3: `ArtifactRef{artifact_id, artifact_type, payload_id, locator: Reference, metadata}` + `Reference{reference_id, kind, …}` + `ArtifactLocation{uri, …}` (`references.py:14-57`). Bytes by-reference (`uri`), never inlined — correct. **Caveat:** the *contract* is ratified; the **live machinery for the bridge to resolve a readable input location and grant a writable `output_location` for an out-of-process job** is orchestration substrate, currently demonstrator-grade (same driver/dispatch layer as ask 2). The §5 division of responsibility is the right target; the bridge-side "grant a writable location" step lands with the ask-2 driver decision.

## 6 — family + payload_family on v0.3. RATIFY.

`CapabilityDeclaration.family` is `TypeAlias = str`, open-world by design ("known constants … not a closed-world enum", `capabilities.py:36-37`); `KNOWN_CAPABILITY_FAMILIES` is a soft observability set, not a gate. Discovery is **request-all**; unknown families are **registered, not rejected**, surfaced in `off_contract_families` (PHASE-6A fix `190d71d`, live). `payload_family: str | None` unconstrained; `.draft` fine. `family="propagation"` + `payload_family="flow.stmap_sequence.draft"` accepted on v0.3; older pins ignore-not-reject.

## 7 — Routing metadata keys. NAMED (caveat).

The planner reads, from a capability's `capabilities` dict: `estimated_cost`/`cost`, `chain_depth`, `acceptance_score`, `backend_identity_triple` (synthesized from `tool_id` if absent), plus deliverable-constraint gates `first_frame_guarantee` / `identity_lock_support` / `upload_support` (`planner_passes.py:117, 175-182, 223, 229-244`). **Emit:** `estimated_cost`, `chain_depth`, `acceptance_score`, `backend_identity_triple`. Proposed `est_runtime_per_frame` / `gpu_required` / `max_references_supported` are **not consumed today** (harmless to emit; forward-looking). **Caveat:** this planner is the demonstrator — these are keys it *would* route on, not a live production router yet. `metadata.invocation_style="async_submit_poll"` + `submit_tool`/`poll_tool` is the right place to declare the lifecycle for the caller that drives it (ask 2 / B0).

## §8 / torch constraint

The bridge only ever imports forge-flow's `register_with` — the commitment to keep the attach + declaration surfaces torch-free is the load-bearing guarantee, and nothing the bridge does forces a torch import. The UC-1 end-to-end (submit→poll→artifacts, never importing torch) is satisfiable today under B0 (ask 2): the caller drives the idempotent poll loop over the attached sync tools; no new bridge subsystem is involved, so no path can pull torch in.

---

## v1 lifecycle ruling (converged — the 60s exec bound settles it)

**How does a heavy async sibling capability get its submit→poll→complete loop driven?** The runtime constraint converges the answer; this is a ruling, not an open decision:

- **B0 — consumer-driven polling. RATIFIED as the v1 lifecycle.** Attach the tools, return job ids, make `poll` idempotent; the **caller** drives submit→poll→terminal. Zero new bridge machinery. This is the supported pattern for heavy async siblings today.
- **B (in-chain `poll-until` primitive) — REJECTED.** `/api/v1/exec` is hard-bounded at 60s (`_EXEC_HTTP_TIMEOUT = 60.0`); a minutes-long propagation cannot complete inside one chain execution. Do not model the loop as a single chain.
- **A (autonomous bridge-driven polling via a generalized `GenerationPoller`) — FUTURE INFRASTRUCTURE, not a flow requirement.** Right for durable, caller-out-of-loop, survive-restart jobs; couples to the generation-artifact substrate and the deferred rung-C / #31 originator. Build it when a producer/consumer demands bridge-as-orchestrator — **not** under the banner of "just polling," and not on forge-flow's critical path.

Everything in this review is ratified and unblocked. The reply to forge-flow is precise: *attach the tools, emit the declarations, return job ids, make poll idempotent — we drive the lifecycle from the caller for v1.*
