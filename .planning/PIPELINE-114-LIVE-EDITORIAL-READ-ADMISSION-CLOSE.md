# Pipeline 114 Live Editorial Read Admission Close

Date: 2026-07-19
Status: Complete for Bridge code; live host UAT remains Pipeline Phase 114

## Decision

Bridge admits two read-only Pipeline operations:

- `flame.editorial.read_edit_state`, the Flame-owned live extraction whose
  primary data is an unwrapped Traffik `EditState`; and
- `traffik.editorial.step_capabilities`, the read-only discover/verify/apply
  authorization surface for an exact editorial step plan.

The former declares `state_owner="dcc_host"` because it observes live Flame
state while remaining mutation-free and idempotent. The old
`traffik.flame_sequence.ingest_edit_state` row remains admitted, but its comment
now correctly describes pure conversion of supplied extraction data rather
than a live host read.

## Composition

`authorize_live_flame_step_plan()` is the Bridge-owned policy gate. It performs
Pipeline capability discovery, holds the three fingerprints, requests
read-only apply authorization, and refuses drift, provisional trust, blocked
semantics, or a changed source plan.

`build_live_flame_rename_preview_spec()` accepts only that trusted held
authorization for the exact one-step `rename_segment` plan and emits:

```text
read_edit_state -> apply_steps -> select_delta -> host_resolve -> delta_to_manifest
```

The authorization is persisted in the `apply_steps` node config while the
primary read output is routed whole to `apply_steps.state`. There is no
`from_port` interpretation, extraction node, executor change, commit node, or
implicit assent.

The result is directly consumable by Bridge's existing
`preview_editorial_delta_for_ratification()`. Ratification and commit remain on
their established assent-required rail.

## Proof

- Admission tests lock operation class, dispatch kind, idempotency, mutation,
  and state-owner declarations.
- Authorization tests prove discover-to-apply fingerprint holding and drift
  refusal.
- Graph tests prove exact topology and whole-output `EditState` routing through
  a normalized rename delta to a held `forge_apply_segment_delta` manifest.
- 21 focused tests pass with targeted Ruff and diff checks.

## External Contract

Pipeline implementation checkpoint: `62d2d2da` on
`codex/phase114-live-editorial-read-vertical`.

Live read-only and ratified apply/revert evidence remain unclaimed until the
active Flame execution worker responds. Bridge does not replace those host
proofs with fixtures.
