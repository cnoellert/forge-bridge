# Slice-3 mutation fixture — live controlled-rename capture

Documents `commit_rename_held.json` in this directory and the procedure to regenerate it.

**Captured:** 2026-06-19, DT, against live Flame (`013_13_13_2026_2_1_portofino`, Flame 2026.2.2) via the running daemon (`:9996`).
**Subject:** sequence `30sec_edit 21` — a real **genesis** client edit (`/mnt/projects/1248_genesis_built_to_thrill/...`, shots `DATA_010`–`DATA_200`, 25 segments across 3 track layers).
**Authorized** by operator (had a backup). **Fully reverted** — post-reset state is byte-identical to pre-state; source media never touched (rename relabels timeline segments only).

This is **captured-not-assembled**: every value below came from the live `flame_*` MCP tools, not reconstructed.

## The capture cycle (exact, in order — proven safe + reversible)

| # | fixture | call | mutating? |
|---|---------|------|-----------|
| 1 | **pre-state** | `flame_get_sequence_segments(sequence_name="30sec_edit 21")` → 25 `DATA_*` segments | no |
| 2 | **held** | `flame_rename_shots(sequence_name="30sec_edit 21", prefix="dt", dry_run=true, mode="discover")` → `mutation_plan`, 25 ChangeRecords `DATA_*→dt_*` | no |
| 3 | **fresh** (no-drift) | same call again → **byte-identical to held** (preview-determinism, `matched=True`, `drift_count=0`) | no |
| 4 | **apply** | `flame_rename_shots(sequence_name="30sec_edit 21", prefix="dt")` → `{renamed:25, shots_assigned:20, propagated:5, skipped:6, changes:[...]}` | **YES** |
| 5 | **post-state** | `flame_get_sequence_segments(...)` → 25 `dt_*` segments | no |
| 6 | **drift** | `flame_rename_shots(..., prefix="dt", dry_run=true, mode="discover")` on the `dt_*` world → identities now `dt_*_graded_L01`; vs `held`'s `DATA_*` identities ⇒ **every item drifts, `matched=False`** | no |
| 7 | **reset** | `flame_rename_shots(sequence_name="30sec_edit 21", prefix="DATA")` → `{renamed:25, changes: dt_*→DATA_*}` | **YES** |
| 8 | **verify** | `flame_get_sequence_segments(...)` → **byte-identical to pre-state (#1)** | no |

`commit_rename_held.json` (this dir) is the captured #2 as a reference. The rest live verbatim in the capture session transcript.

## Verified facts (load-bearing for the slice-3 tests)

- **`held == fresh`** → `CommitNode.verify(held, fresh)` = `matched=True, drift_count=0`. The clean apply path.
- **`held` vs `drift`** → `matched=False`. The drift identities are `dt_*` (state moved post-apply); held's are `DATA_*`. This is the genuine "you ratified but state moved" case — captured, not synthesized.
- **Payload shape differs by need:** `held` payloads carry `{shot_name, segment_name}` (full rename); `drift` payloads carry `{shot_name}` only (segments already named `dt_*`, only shot-name reassignment remains). Real captured nuance — don't normalize it away.
- **Round-trip is exact** — apply (`DATA→dt`, 25) then reset (`dt→DATA`, 25) restores the edit byte-for-byte.

## MutationManifest shape (matches `graph/mutation.py` + `CommitNode.verify`)

```
{ type: "mutation_plan",
  intent_parameters: {sequence_name, prefix, increment, padding, start, role_overrides, qualifier_overrides},
  resolved_plan: [ {identity: {track_idx, record_in, seg_name, source_name, sequence_name},
                    payload:  {shot_name [, segment_name]}}, ... ],
  originating_capability: "flame_rename_shots",
  apply_counterpart: {tool: "flame_rename_shots", parameter_overrides: {mode: "apply"}} }
```

`CommitNode.verify` compares `held.resolved_plan` vs `fresh.resolved_plan` item-by-item → `drift_count` / `first_drift_index`.

## The `ratified` fixture (NOT captured here)

`AssentRecord` is **bridge-internal**, not a flame-tool payload — the exec route gates it behind `clarification_needed`. Per the existing `run_apply_branch` tests (`test_tf1_ratification_integrity`), mint a **ratified** `AssentRecord` in-test rather than capturing one. That is the operator-authored fact and is legitimately constructed, not "theater" — the *external* tool payloads (held/fresh/drift/states) are the captured-not-assembled artifacts.

## To re-capture byte-exact on the branch

Re-run the cycle above (it is reversible and verified). Segment states can be captured byte-exact via the daemon exec endpoint, e.g.:

```
curl -s -X POST http://localhost:9996/api/v1/exec -H 'Content-Type: application/json' \
  -d '{"text":"flame_get_sequence_segments sequence_name=\"30sec_edit 21\""}'  # → .chain[0].result
```

The rename plans (held/drift) must come from the **MCP tool directly** (`flame_rename_shots ... dry_run=true mode=discover`) — exec gates the mutation behind the authority chain.
