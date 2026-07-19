# Pipeline 114 Live Editorial Apply/Revert Runbook

Date: 2026-07-19
Status: Harness complete; live Flame execution pending

## Purpose

`scripts/live_flame_editorial_rename_vertical_uat.py` runs the complete
operator-driven vertical against one caller-selected live Flame sequence:

```text
read -> capability authorize -> apply_steps -> select_delta
     -> host_resolve -> delta_to_manifest -> proposed assent
     -> ratified commit -> independent read
```

It then runs the same path for the inverse rename and requires the final live
`EditState` fingerprint to equal the initial fingerprint.

## Safety Contract

- The CLI will not run without explicit `--apply`.
- Sequence, reel, segment, temporary name, actor, and evidence paths are caller
  inputs; no production path is encoded.
- Both forward and inverse intents are first replayed while proposed and must
  fail with `assent_illegal_state` before either can be ratified.
- Every apply uses Bridge's persisted held-manifest replay, including fresh
  executor verify before host apply.
- Independent live reads verify both the temporary name and restored name.
- Segment identity must remain unchanged across the rename.
- Final state fingerprint must equal the initial live fingerprint.
- Any exception after initial observation triggers best-effort governed
  recovery to the original name. Recovery is called residue-free only when its
  independent final fingerprint also matches the initial state.

## Command

With Flame running, its Bridge hook loaded, the dedicated test sequence open,
and Pipeline Phase 114 installed:

```bash
cd /Users/cnoellert/GitHub/forge-bridge
FORGE_PLUGINS=flame,traffik \
  /Users/cnoellert/miniconda3/envs/forge/bin/python \
  scripts/live_flame_editorial_rename_vertical_uat.py \
  --apply \
  --sequence-name FORGE_UAT_HOST_APPLY_20260624 \
  --reel-name Testing \
  --actor phase114-uat \
  --receipt-dir .planning/evidence/114-live-editorial-rename \
  --json-out .planning/evidence/114-live-editorial-rename/live-apply-revert.json \
  --quiet
```

## Current Verification

- Synthetic success proves two proposed-assent refusals, two ratified applies,
  independent forward/final reads, stable segment identity, and exact final
  state restoration.
- Synthetic inverse-failure proof performs a separately governed recovery and
  restores the initial state.
- Focused Bridge authorization, graph replay, and UAT suite: 11 passed.
- Live proof remains unclaimed while Flame is not running.
