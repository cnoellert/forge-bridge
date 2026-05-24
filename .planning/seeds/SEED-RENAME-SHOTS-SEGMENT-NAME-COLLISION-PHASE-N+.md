---
name: rename-shots-segment-name-collision
description: Under whole-sequence selection, flame_rename_shots asset-track segments can resolve to colliding shot names. Observed in the Phase N+ C4 canonical probe (evidence artifact Part 6). Not a seam defect — verify matched and apply succeeded; the collision is a tool-grain naming property, not a commit/preview failure.
type: strategic-framing
planted_during: "Phase N+ canonical probe firing (C4 evidence, Part 6) — flame_rename_shots selection/propagation under whole-sequence input produced two asset-track segments resolving to a colliding genesis_0200 shot name. The commit seam behaved correctly: verify matched, drift-guard passed, apply succeeded. The collision is in the tool's name-derivation under whole-sequence grain, not in the preview→apply substrate."
trigger_when: "Phase N++ opens, OR a future contributor reports duplicate shot-name output from a flame_rename_shots whole-sequence run."
---

# Seed — flame_rename_shots segment-name collision under whole-sequence selection

## What was observed

During the Phase N+ C4 canonical probe firing against the real 30sec 21
sequence, `flame_rename_shots` under whole-sequence selection produced
two asset-track segments that resolved to the same shot name
(`genesis_0200`). The commit primitive behaved correctly throughout:
verify mode re-dispatched cleanly, the drift-guard structural comparison
matched, and apply succeeded. The collision was visible in the resulting
manifest, not as a substrate error.

## Why this is not a seam defect

The preview→apply seam is verify-only/pure and did exactly what it is
contracted to do. The colliding name is a property of how
`flame_rename_shots` derives shot names from asset-track segments when
the selection grain is the whole sequence — `_resolve_group` is
sequence-global by grain, and two distinct asset-track segments can
legitimately carry attributes that derive to the same shot name. The
substrate faithfully carried and applied what the tool emitted.

## What a future phase should consider

- Whether `flame_rename_shots` should detect and disambiguate
  colliding derived names at discover/verify time, or whether collision
  is a legitimate operator-visible outcome to be surfaced rather than
  auto-resolved.
- The relationship to `_seg_key_tuple` stable identity (Finding C):
  segments are distinct under the stable key even when their derived
  shot names collide — so this is specifically a name-derivation
  question, not an identity-resolution question.
- This is a sibling concern to the foreach + collect + commit
  body-tool-grain deferral in the §11 register: both are tool-grain
  properties surfaced by the C4 probe, not substrate defects.

## Status

Parked. Not blocking. Recorded so the observation is not lost between
phases.
