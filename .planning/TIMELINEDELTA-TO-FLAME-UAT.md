# ① TimelineDelta → Flame — Live-Flame Manual UAT Checklist

**Purpose:** prove the whole ① vertical drives a real Flame mutation on a live workstation — the one gate a real-shape CI double can't clear. Manual, operator-run, cross-repo (Pipeline produces the real delta; Bridge applies).
**Bridge under test:** `v1.8.0` (host_resolve slice 1 + 1.5). **Maps to:** BRIDGE39 acceptance #1–#7 · Pipeline `67-traffik-real-fixture-uat`.
**Scope today:** steps 1–6 run on `v1.8.0`. Step 7 (idempotency) + operator-facing preview richness ride slice 1.6 — run a fuller pass then.

> **LIVE UAT STATUS — GATES A + B PASSED (forge-bridge#109, 2026-06-24, Bridge `v1.8.1`).** Gate A (discover/host-resolve, non-mutating): host_resolve returned a `mutation_manifest` on a Pipeline-projected real delta; temporal deltas correctly stayed review-only (`host_payload_delta_count:0`). Gate B (commit/ratify apply): ratified commit performed a **real Flame segment rename** (`apply_result.results:[{ok:true,attribute:name,new_value:…}]`) and a ratified revert restored it cleanly; disposable sequence left residue-free. The Gate-B deadlock/false-positive fix (six inline-write tools + honest-result guard) is live-verified. **Gate C (temporal `frame_in`/`frame_out` executor) = future/Pipeline-side.** Contract note: Pipeline normalizes top-level `sequence_id`→Flame sequence *name* (Pipeline id preserved in `metadata.source_delta_sequence_id`).
> **DISCOVERY-CLEAN STATUS — Pipeline `v2.1.1` unblocks `FORGE_PLUGINS=traffik`.** Bridge now carries an optional cross-repo proof that `build_operation_runner()` can dispatch `traffik.editorial.apply_steps` and `traffik.flame_delta.host_resolve` from the forge-core default registry without manual `registry.register(...)`. The deterministic test patches only the entry-point source while using the real Traffik plugin factory; the deployment test runs against installed `forge_core.plugins` metadata and skips unless a v2.1.1+ Pipeline distribution is present.

---

## Preconditions

- [ ] Live Flame workstation (portofino / flame-01) with the bridge hook serving on `:9999`.
- [ ] Bridge daemon up (`:9996`); `fbridge doctor` green (Console, MCP, Flame probe, State WS, postgres, graph_store).
- [ ] forge-core MCP tools sibling-attached — confirm **`forge_apply_segment_delta`** AND `rename_shots` are in the live registry (`forge_tools_read` / doctor).
- [ ] Pipeline `v2.1.1+` installed in the Bridge runtime, with `FORGE_PLUGINS=traffik` so `traffik.editorial.apply_steps` and `traffik.flame_delta.host_resolve` register through forge-core plugin discovery.
- [ ] A real Flame project + sequence with known segments; record the target `sequence_name` and the target segment's current name.
- [ ] Pipeline can produce a real `TimelineDelta` for an `updated` segment-name change with `metadata` carrying the live Flame identity envelope (`track_idx/record_in/seg_name/source_name/sequence_name`). ← cross-repo dependency.
- [ ] Baseline captured: `flame_get_sequence_segments(<sequence_name>)` → before-state.

## Happy path

1. [ ] **Produce the proposal (Phase A).** Run `traffik.editorial.apply_steps` over a real rename intent → `output["deltas"]` with enriched metadata. **Assert: Flame unchanged** (`flame_get_sequence_segments` == baseline). *(BRIDGE39 #1)*
2. [ ] **Preview / discover (unratified).** `apply_editorial_delta(spec, assent_record=<unratified>)` over `operation → host_resolve → commit`. host_resolve calls `forge_apply_segment_delta(mode=discover)` against live Flame → real held `MutationManifest`. **Assert: commit fails closed → `ASSENT_INVALID`, Flame unchanged.** *(BRIDGE39 #2, #4)*
3. [ ] **Ratify.** Operator reviews the preview/manifest → produce a ratified `AssentRecord`.
4. [ ] **Apply.** Re-run with ratified assent → discover → commit verify (held vs fresh-from-Flame) matches → apply. **Assert: segment renamed in Flame** (`flame_get_sequence_segments` shows the new name; confirm in the Flame UI). *(BRIDGE39 #6)*

## Safety / negative cases (fail-closed against live state)

5. [ ] **Drift.** Between a fresh preview and apply, manually rename/move the target segment *in Flame*. Re-run apply → **Assert: `PLAN_STATE_DRIFT`, no mutation.** *(BRIDGE39 #5)*
6. [ ] **Stale identity.** Craft a delta whose `metadata` doesn't resolve to a live segment (wrong `seg_name`). Run → **Assert: `UNRESOLVED_TARGET`** (the `missing_flame_identity` path) — *distinct from drift*. This is the diagnostic split the taxonomy was built for.
7. [ ] *(slice 1.6)* **Idempotency.** Re-apply the same ratified delta → **Assert: duplicate-detected, no double-mutation.** *(BRIDGE39 #7 receipt linkage)*

## Capture (attach to the UAT record)

- [ ] Before/after `flame_get_sequence_segments`.
- [ ] The held `MutationManifest` (preview).
- [ ] The `AssentRecord` (id + ratified state).
- [ ] The apply `NodeResult` / `commit_applied` output (+ receipt once 1.6 lands).
- [ ] Screenshots of the Flame timeline before/after.

## Results

| # | Case | Expected | Actual | Pass |
|---|------|----------|--------|------|
| 1 | Phase A no-mutation | Flame unchanged | | ☐ |
| 2 | Unratified | `ASSENT_INVALID`, no mutation | | ☐ |
| 4 | Ratified apply | segment renamed | | ☐ |
| 5 | Drift | `PLAN_STATE_DRIFT`, no mutation | | ☐ |
| 6 | Stale identity | `UNRESOLVED_TARGET` (≠ drift) | | ☐ |
| 7 | Idempotency (1.6) | duplicate-detected | | ☐ |

## What this uniquely proves (beyond CI)

- The Bridge→Pipeline→Bridge call loop (`host_resolve → forge_apply_segment_delta → rename_shots`) drives a real Flame rename.
- Real Flame identity resolution from the metadata envelope is sufficient.
- Real drift detection against genuine Flame state changes; stale-identity ≠ drift on real data.
- Live transport end-to-end: sibling tool-attach → real executor on the daemon → Flame main-thread execution under an actual mutation (latency/timeouts).

**Cross-repo:** coordinated with forge-pipeline (they produce the real delta). Tracking issue: **forge-pipeline#19**.
