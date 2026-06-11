# MEMO — perception-land dispatch (greenscreen→roto, slice 2)

**Date:** 2026-06-10
**From:** forge-bridge (DT) · **To:** forge-vision
**Re:** Next slice — turn the CONTRACT-proven greenscreen→roto into a CAPABILITY-proven one
**Predecessors:** contract+wire shipped (forge-vision `5f02c17`); bridge composition seam `.planning/VISION-COMPOSITION-SEAM.md` (#45); v1 answers `.planning/memos/MEMO-bridge-reply-v1-plan.md` (#46)

---

## Status: the wire is live, the pixels are mock

The live round-trip ran end-to-end through the **deployed** bridge daemon (registry 95→97, MCP session against `:9997/mcp`):

| Step | Result |
|---|---|
| `forge_is_greenscreen` (true-green chroma) | `is_greenscreen: True`, "grounded greenscreen", 1 green region, `shots:[{id}]` |
| `filter(is_greenscreen == true)` (real bridge primitive) | shot routed through |
| `forge_roto_ref` (routed shot) | `DerivedHoldoutsArtifact` by-reference — locator `…/tst_010_roto.####.exr`, sha256 `payload_id`, `foreground_alpha` |
| abstain control (ambiguous chroma) | token **omitted** → "abstained" → did **not** route |

**Honesty flag (carried from vision's handoff):** the matte locator is `mock://roto_ref/…` and `is_greenscreen`'s chroma logic was exercised only on synthetic 8-bit stats (`GREEN_FLOOR=90`, `GREEN_DOMINANCE_MARGIN=40`). This is **CONTRACT-proven, not CAPABILITY-proven.** That's the whole point of this slice.

---

## The frozen surface (do NOT touch — it's now the regression gate)

The chain-wire contract is proven and must stay byte-stable as perception lands underneath it. Per vision's own doctrine — *operator = the deterministic merge; the detector/matte are swappable evidence providers* — the perception swap happens **under** these, not **to** them:

- `forge_is_greenscreen` → top-level `is_greenscreen: bool` (**omit on abstain**), `items` (green regions), `shots: [{id}]`.
- `forge_roto_ref` → `DerivedHoldoutsArtifact` **by-reference** (`locator` + sha256 `payload_id` + `foreground_alpha`).
- The bridge routes on `filter(is_greenscreen == true)` over the top-level scalar (`filter.py:205`) — nested Evidence stays invisible to routing.

**Acceptance backstop:** after the perception land, re-run the exact live round-trip above; it must produce the *same wire shape* — only the locator changes from `mock://` to a real path. If the wire shape moves, the chain breaks; treat that as a regression, not progress.

---

## The dispatch — three deliverables (forge-vision)

1. **Real greenscreen detection.** Validate the chroma path on a **real greenscreen plate** (not synthetic stats). Grounds *true* on a real green plate, *abstains/false* honestly on non-green / blue / partial-screen. **Close-grade the green region** — the `items` region must actually bound the green. Re-check `GREEN_FLOOR`/`GREEN_DOMINANCE_MARGIN`/`BLUE_FLOOR` against real plate chroma; synthetic-tuned thresholds are a known risk.

   **⚠ Operator-signature change — build to this from the start (surfaced by the bridge-side chain prototype, #48).** The current operator is `is_greenscreen(frame_stats, shot_id)` — it consumes **pre-computed** 8-bit chroma. That signature **cannot bind in the authored chain.** The bridge's `foreach(forge_is_greenscreen)` binds a body tool's args from public context + standard id-extraction (`project_id`/`shot_id`/`version_id`), **not** arbitrary arrays (`forge_bridge/console/_step.py:248-257, 651-656`); and Flame segments **do not carry chroma**. So there is no provenance for per-segment `frame_stats` inside the chain.
   → **The real operator should take a plate-reading signature** — `(shot_id, media_locator)` — and **read the chroma itself** from the segment's plate, so the `foreach` body binds per-segment from the segment's own media reference. Keep the *output* contract frozen (top-level `is_greenscreen` bool omit-on-abstain + `items` + `shots`); change only the **input** from pre-computed stats to a plate reference. (In the prototype, synthetic `frame_stats` stand in for exactly this read — that stand-in is what the plate-reading signature removes.)

2. **Real matte substrate.** Wire the **First Light ViTMatte / GroundedSAM2** substrate into `roto_ref`, replacing the mock matte bytes with a real soft-alpha foreground matte EXR, emitted **by-reference** (real `locator` path + real sha256). **Reuse the `DerivedHoldoutsArtifact` contract unchanged.** Acceptance: **eyeball the soft-alpha edge** on a real plate.

3. **Real-footage witness.** The e2e on real footage: real plate → `is_greenscreen` grounds → bridge routes → `roto_ref` emits a real matte → witness the matte (the artifact, not the report). Per the verify-on-the-artifact rule, the witness is the proof, not the summary.

**Verification (vision-side):** deployed==committed; re-run the bridge live round-trip post-redeploy (the direct JSON-RPC drive against `:9997/mcp`); witness on real footage.

---

## Bridge-side, deferred until perception is real

The **authored chain** (bridge's half) lands after the perception land and needs Flame connected:

```
flame_get_sequence_segments
  -> foreach(forge_is_greenscreen) -> collect
  -> filter(is_greenscreen == true)
  -> foreach(forge_roto_ref) -> collect
  -> foreach(forge_register_publish …) -> commit
```

The perception→filter→roto core is already verified manually (above); what's outstanding bridge-side is the segment fan-out front and the `register_publish`/`import_clips`/tag tail (all bridge-authored — vision never decides the attach). I can prototype the chain against the mock operators now (perception-agnostic, routes on the frozen contract) so it's ready the moment real mattes land — say the word.

**Parked (vision trunk debt, not lost):** generalize `describe_shot_record` merge off tst_020's shape (#2); carve `ground_subject`/`recognize_entity` (#3 — `ground_subject` also serves the general cinematic-component tagging consumer; two-consumer rule). Resume when the consumption thread loops back to richer tagging.
