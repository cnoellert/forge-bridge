# TimelineDelta to Flame - select_delta bridge slice

## Status

Implemented and focused verification passed.

## Purpose

Remove the last config-supplied raw-delta shortcut from the live editorial apply
graph. `traffik.editorial.apply_steps` now feeds a Bridge primitive that selects
one emitted `TimelineDelta`, and that selected delta becomes `params.delta` for
`traffik.flame_delta.host_resolve`.

## Implemented

- Added admitted primitive operator `select_delta`.
- `select_delta` consumes one upstream manifest with `deltas[]`, selects
  `config.index` or `0`, and emits the selected delta as a manifest.
- Added full-chain tests:
  - `apply_steps -> select_delta -> traffik.flame_delta.host_resolve`
  - `host_resolve -> delta_to_manifest -> commit`
  - production `apply_editorial_delta(...)` rail uses the same chain.

## Verification

- `python -m pytest tests/composition/test_m2_admission.py tests/composition/test_m2_primitive_boundary.py tests/composition/test_m2_host_resolve_boundary.py -q`
  - `49 passed, 11 warnings`
- `python -m pytest tests/composition/test_m2_admission.py tests/composition/test_m2_primitive_boundary.py tests/composition/test_m2_unified_dispatch.py tests/composition/test_m2_operation_boundary.py tests/composition/test_m2_host_resolve_boundary.py tests/composition/test_host_resolve_operation_contract.py tests/orchestration/test_operation_runner.py tests/orchestration/test_run_graph.py tests/console/test_graph_replay_ratify.py -q`
  - `88 passed, 2 skipped, 12 warnings`
- `python -m compileall -q forge_bridge tests/composition tests/orchestration tests/console`
- `git diff --check`
