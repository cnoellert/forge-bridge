# A.3 UAT Catalog

| # | UAT item | Trigger | Pass criterion |
|---|---|---|---|
| 1 | Drift-invalidation live smoke | propose mutating chain -> modify substrate so held_hash != fresh_hash -> ratify | exit 1; envelope `error.code = CHAIN_STEP_FAILED` with `original_error.type = PLAN_STATE_DRIFT` (drift_count + first_drift_index populated); assent record transitions to `status='failed'` with `apply_failure_reason='drift_invalid'` |
| 2 | Happy-path full chain | NL -> compile -> preview -> ratify -> apply against live Flame project | exit 0, `assent.applied` event emitted, assent_record status='applied' |
| 3 | Recovery: assent_record_not_found | ratify a graph_intent_id that resolves to no row | exit 1, envelope code `assent_record_not_found` |
| 4 | Recovery: assent_illegal_state | ratify an already-applied graph_intent_id | exit 1, envelope code `assent_illegal_state`, current_status populated |
| 5 | Recovery: chain_aborted | propose chain with a deliberately failing step -> ratify -> apply | exit 1, envelope code `chain_aborted`, step_index + step_text populated |
| 6 | Recovery: daemon_unreachable | stop daemon -> ratify | exit 2, envelope code `daemon_unreachable`, url + reason populated |
| 7 | Multi-cycle ratification cadence | sequence 5 sequential propose-ratify-apply cycles | all 5 succeed, doctor row chip stays `ok` throughout |
