# MEMO — forge-flow propagation-driver conformance review

**Date:** 2026-06-10
**From:** forge-bridge (DT) · **To:** forge-flow
**Re:** Conformance review of "forge-flow as a Bridge propagation driver" (UC-1: flow + reference-recommendation)
**Contract pin:** forge_contracts v0.3
**Companions:** `.planning/VISION-COMPOSITION-SEAM.md` (#45), `.planning/memos/MEMO-perception-land-dispatch.md` (#47/#49)

---

## TL;DR verdict

4 of 7 asks ratify as-proposed; 2 are gaps forge-flow has already designed around; 1 needs a bridge-side execution decision. forge-flow's choice to have `auto_propagate` own the composition forge-flow-side is exactly right — it sidesteps the one hard gap.

| Ask | Verdict |
|---|---|
| 1. Tool-attach contract stable | ✅ **RATIFY** |
| 2. Async submit/poll lifecycle | ⚠️ **RATIFY-THE-SHAPE — driving mechanism needs a bridge decision** |
| 3. Output-supplied-parameter routing (3a→3b) | ⛔ **GAP — not built; auto_propagate sidesteps it (endorsed)** |
| 4. Clip-relative offset convention | ✅ **RATIFY** |
| 5. Ref/locator I/O contract | ✅ **RATIFY the contract** · ⚠️ live location-granting is substrate-deferred |
| 6. family "propagation" + payload_family ".draft" | ✅ **RATIFY** |
| 7. Routing metadata keys | ✅ **NAMED** (caveat: planner is a demonstrator) |

The seam splits cleanly: **contract / attach / convention ratify now** (1, 4, 5-contract, 6, 7); **execution-driving** (2, 3, 5-live) lands on the deferred federation frontier (rung-C / #31, the demonstrator planner, the no-poll-primitive chain engine).

---

## 1 — Tool-attach contract. RATIFY.

forge-flow's `forgeflow.bridge.registry:register_with(mcp)` matches the bridge's contract exactly. Discovery: `forge_bridge.siblings` EP group → imports `<pkg>.bridge.registry` → calls `register_with(mcp)` (`discovery.py:61-118`). It runs at **module load, before `mcp.run()`** — the D-14 guard (`_server_started`) blocks `register_tools()` only after lifespan startup (`server.py:536`; guard `registry.py:172-176`). Per-sibling failures isolated by try/except → `attached` / `no_register_with` / `error` (`discovery.py:107-116`; test `test_sibling_tool_attach.py`). `register_tools(mcp, [...], prefix="forge_")` is documented public API; `forge_` is valid (`_VALID_PREFIXES = {flame_, forge_, format_, synth_}`). The `no_register_with` in today's boot log flips to `attached` the moment the module exists.

## 2 — Async submit/poll. RATIFY-THE-SHAPE; pick the driving path.

Two truths to separate:
- *Invoking* `forge_submit_propagation` / `forge_poll_propagation` as individual MCP tools works today — each is a fast synchronous call.
- *Driving the submit→poll→complete loop automatically* is specific. The deterministic chain engine has **no poll-until/await-job primitive** — primitives are foreach/collect/filter/if_gate/select/commit only (`forge_bridge/graph/`); it cannot express "poll until complete." **But** the bridge already runs a **live** async-job lifecycle: `GenerationPoller` + the dispatch consumer, wired as asyncio tasks in `server.py`, driving a driver `submit()/poll()` protocol via `GenerationDriverRegistry` (`orchestration/worker.py`, `dispatcher.py`). That's a real production submit→poll loop — but it's the **forge-generators driver substrate** (generation-artifact shaped), and the *planner* that routes to it is the test-only demonstrator (rung-C / **#31**, deferred).

→ **Bridge-side decision (ours — see "Open decision" below):** land forge-flow as a **driver on that live lifecycle** (generalizing it to a generic async-job lifecycle, `GenerationPoller` then drives the loop), **or** keep the two sync tools and add a `poll-until-terminal` chain primitive. We owe this decision before forge-flow wires the runner integration.

## 3 — Output-supplied-parameter routing. GAP — already solved by design.

Neither path supports it: the demonstrator planner hardcodes `operator_sequence[].inputs = []` (`planner_passes.py:372`) — zero output→input wiring; and the live chain engine binds a body tool's args from public context + standard-ID extraction (`project_id`/`shot_id`/`version_id`), **not** arbitrary fields (`_step.py:248-257, 651-656`). So a `recommend_references → propagate_stmap` chain feeding the recommended offset into `reference_index` is **not routable** today (same seam as forge-vision's greenscreen→roto, `MEMO-perception-land-dispatch.md`). **→ Endorse v1: `auto_propagate` owns the 3a→3b composition forge-flow-side; the bridge calls one tool.** Separately ✅ confirmed: **a capability with no `reference_index` input is NOT gated out** — discovery registers any declaration, no input-schema gate (`discovery.py:212-218`; family open).

## 4 — Clip-relative offset convention. RATIFY.

Nothing in the bridge blocks it; it aligns with bridge doctrine (the bridge owns the offset↔absolute-frame mapping; forge-flow stays source-agnostic). Honored: 0-based offsets from the submitted clip's first frame; `clip_start_frame` echoed-not-interpreted by forge-flow; `absolute = clip_start_frame + offset` computed bridge-side. Freeze it as the seam contract — agreed.

## 5 — Ref/locator I/O. RATIFY the contract; one honesty flag.

forge-flow's shape maps directly to forge_contracts v0.3: `ArtifactRef{artifact_id, artifact_type, payload_id, locator: Reference, metadata}` + `Reference{reference_id, kind, …}` + `ArtifactLocation{uri, …}` (`references.py:14-57`). Bytes by-reference (`uri`), never inlined — correct. **Caveat:** the *contract* is ratified; the **live machinery for the bridge to resolve a readable input location and grant a writable `output_location` for an out-of-process job** is orchestration substrate, currently demonstrator-grade (same driver/dispatch layer as ask 2). The §5 division of responsibility is the right target; the bridge-side "grant a writable location" step lands with the ask-2 driver decision.

## 6 — family + payload_family on v0.3. RATIFY.

`CapabilityDeclaration.family` is `TypeAlias = str`, open-world by design ("known constants … not a closed-world enum", `capabilities.py:36-37`); `KNOWN_CAPABILITY_FAMILIES` is a soft observability set, not a gate. Discovery is **request-all**; unknown families are **registered, not rejected**, surfaced in `off_contract_families` (PHASE-6A fix `190d71d`, live). `payload_family: str | None` unconstrained; `.draft` fine. `family="propagation"` + `payload_family="flow.stmap_sequence.draft"` accepted on v0.3; older pins ignore-not-reject.

## 7 — Routing metadata keys. NAMED (caveat).

The planner reads, from a capability's `capabilities` dict: `estimated_cost`/`cost`, `chain_depth`, `acceptance_score`, `backend_identity_triple` (synthesized from `tool_id` if absent), plus deliverable-constraint gates `first_frame_guarantee` / `identity_lock_support` / `upload_support` (`planner_passes.py:117, 175-182, 223, 229-244`). **Emit:** `estimated_cost`, `chain_depth`, `acceptance_score`, `backend_identity_triple`. Proposed `est_runtime_per_frame` / `gpu_required` / `max_references_supported` are **not consumed today** (harmless to emit; forward-looking). **Caveat:** this planner is the demonstrator — these are keys it *would* route on, not a live production router yet. `metadata.invocation_style="async_submit_poll"` + `submit_tool`/`poll_tool` is the right place to declare the lifecycle for whoever drives ask 2.

## §8 / torch constraint

The bridge only ever imports forge-flow's `register_with` — the commitment to keep the attach + declaration surfaces torch-free is the load-bearing guarantee, and nothing the bridge does forces a torch import. The UC-1 *automated* end-to-end (submit→poll→artifacts, never importing torch) is gated only on the ask-2 driving decision; everything else in §8 is satisfiable today.

---

## Open bridge-side decision (owed to forge-flow before runner integration)

**How does a heavy async sibling capability get its submit→poll→complete loop driven?** Two options:

- **Option A — ride the live generation lifecycle.** Generalize `GenerationPoller` + dispatch + `GenerationDriverRegistry` from generation-artifact-specific into a generic async-job lifecycle; forge-flow implements the driver `submit()/poll()` protocol and plugs in. **Pro:** reuses live, wired-in machinery (the poller already runs). **Con:** the substrate is `orch_generation_artifact`-shaped (family=generation); generalizing it to propagation is real schema/abstraction work, and the *originating* dispatch still wants a producer (rung-C / #31, deferred) or a consumer to kick it off.
- **Option B — sync tools + a `poll-until-terminal` chain primitive.** Keep `forge_submit_propagation` / `forge_poll_propagation` as plain MCP tools; add one new graph primitive that submits then polls until a terminal status, expressible in an authored chain. **Pro:** propagation-agnostic, small, composes with the existing chain engine; no coupling to the generation substrate. **Con:** a new primitive to design/test (backoff, timeout, terminal-status vocabulary), and it's a second async mechanism alongside the generation poller.

Recommend the room converge on A-vs-B before replying to forge-flow's ask 2; everything else in this review is ratified and unblocked.
